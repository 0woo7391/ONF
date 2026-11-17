import unittest

from onf_v2.core.attention_engine import AttentionEngine
from onf_v2.core.models import (
    CalibrationProfile,
    CalibrationStatus,
    EffectiveState,
    FrameObservation,
    ObservationState,
    RelativeMetrics,
)


def profile(pitch: float, gaze_y: float) -> CalibrationProfile:
    return CalibrationProfile(
        yaw_center=0.0,
        pitch_center=pitch,
        roll_center=0.0,
        gaze_x_center=0.5,
        gaze_y_center=gaze_y,
        left_eye_open_baseline=0.25,
        right_eye_open_baseline=0.25,
        face_scale_center=0.4,
        face_center=(0.45, 0.55),
        sample_count=40,
        quality_score=1.0,
    )


def observation(timestamp: float, pitch: float, gaze_y: float) -> FrameObservation:
    return FrameObservation(
        timestamp=timestamp,
        camera_ok=True,
        face_detected=True,
        face_count=1,
        tracking_confidence=0.95,
        face_bbox=(0.2, 0.1, 0.7, 0.9),
        face_scale=0.4,
        face_center=(0.45, 0.55),
        head_yaw_deg=0.0,
        head_pitch_deg=pitch,
        head_roll_deg=0.0,
        left_gaze_x=0.5,
        right_gaze_x=0.5,
        left_gaze_y=gaze_y,
        right_gaze_y=gaze_y,
        gaze_x=0.5,
        gaze_y=gaze_y,
        left_eye_open_ratio=0.25,
        right_eye_open_ratio=0.25,
    )


class DualPostureAttentionEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = AttentionEngine()
        self.engine.calibration.profile = profile(0.0, 0.5)
        self.engine.calibration.status = CalibrationStatus.READY

    def test_guided_screen_profile_requires_valid_dwell_at_every_target(self):
        engine = AttentionEngine()
        manager = engine.calibration
        manager.require_display_ack = True
        engine.start_calibration(100.0, "screen")
        timestamp = 100.0
        values = {
            "center": (0.0, 0.0, 0.50, 0.50),
            "up": (0.0, -5.0, 0.50, 0.40),
            "down": (0.0, 5.0, 0.50, 0.60),
            "left": (-5.0, 0.0, 0.40, 0.50),
            "right": (5.0, 0.0, 0.60, 0.50),
        }
        for stage, target in enumerate(manager.guided_targets):
            self.assertEqual(manager.current_target, target)
            self.assertTrue(manager.confirm_target_displayed(timestamp, stage, target))
            yaw, pitch, gaze_x, gaze_y = values[target]
            for index in range(41):
                sample = observation(timestamp + index * 0.1, pitch, gaze_y)
                sample.head_yaw_deg = yaw
                sample.gaze_x = sample.left_gaze_x = sample.right_gaze_x = gaze_x
                progress = engine.update_calibration(sample)
            self.assertAlmostEqual(manager.valid_seconds_by_target[target], 2.0)
            timestamp += 5.1
        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertTrue(engine.ready_for_session)
        self.assertEqual(set(progress.profile.target_centers), set(manager.guided_targets))
        self.assertAlmostEqual(progress.profile.gaze_x_center, 0.5)
        self.assertAlmostEqual(progress.profile.gaze_y_center, 0.5)

    def test_screen_writing_mode_requires_both_profiles(self):
        self.engine.set_work_mode("screen_writing")

        self.assertFalse(self.engine.ready_for_session)

        self.engine.writing_calibration.profile = profile(28.0, 0.78)
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.assertTrue(self.engine.ready_for_session)

    def test_writing_posture_is_focus_only_in_screen_writing_mode(self):
        writing = profile(28.0, 0.78)
        self.engine.writing_calibration.profile = writing
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")

        self.engine.decide(observation(0.0, 28.0, 0.78))
        self.engine.decide(observation(0.5, 28.0, 0.78))
        decision = self.engine.decide(observation(0.9, 28.0, 0.78))

        self.assertEqual(decision.effective_state, EffectiveState.FOCUS)
        self.assertEqual(self.engine.last_matched_profile, "writing")
        self.assertEqual(decision.matched_profile, "writing")
        self.assertLess(
            decision.profile_distances["writing"],
            decision.profile_distances["screen"],
        )

        self.engine.set_work_mode("screen")
        self.engine.reset_runtime_state()
        self.engine.decide(observation(1.0, 28.0, 0.78))
        decision = self.engine.decide(observation(2.1, 28.0, 0.78))
        self.assertEqual(decision.effective_state, EffectiveState.NON_FOCUS)

    def test_recalibrating_screen_preserves_writing_profile(self):
        self.engine.writing_calibration.profile = profile(28.0, 0.78)
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")

        self.engine.start_calibration(10.0, target="screen")

        self.assertTrue(self.engine.writing_calibrated)
        self.assertFalse(self.engine.ready_for_session)

    def test_clear_calibrations_removes_both_profiles(self):
        self.engine.writing_calibration.profile = profile(28.0, 0.78)
        self.engine.writing_calibration.status = CalibrationStatus.READY

        self.engine.clear_calibrations()

        self.assertFalse(self.engine.calibrated)
        self.assertFalse(self.engine.writing_calibrated)

    def test_setting_same_work_mode_does_not_reset_runtime_filter(self):
        first = self.engine.filter.update(
            self.engine.calibration.normalize(observation(1.0, 0.0, 0.5))
        )

        self.engine.set_work_mode("screen")

        self.assertIs(self.engine.filter._last, first)

    def test_small_distance_changes_do_not_flap_between_profiles(self):
        self.engine.writing_calibration.profile = profile(10.0, 0.60)
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")
        self.engine.decide(observation(0.0, 0.0, 0.50))

        first = self.engine.decide(observation(0.1, 5.2, 0.552))
        second = self.engine.decide(observation(0.2, 4.8, 0.548))

        self.assertEqual(first.matched_profile, "screen")
        self.assertEqual(second.matched_profile, "screen")
        self.assertIsNone(self.engine.profile_switch_candidate)

    def test_profile_switch_requires_sustained_clear_improvement(self):
        self.engine.writing_calibration.profile = profile(28.0, 0.78)
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")
        self.engine.decide(observation(0.0, 0.0, 0.50))

        candidate = self.engine.decide(observation(1.0, 28.0, 0.78))
        switched = self.engine.decide(observation(1.5, 28.0, 0.78))

        self.assertEqual(candidate.matched_profile, "screen")
        self.assertEqual(candidate.profile_switch_candidate, "writing")
        self.assertEqual(switched.matched_profile, "writing")
        self.assertIsNone(switched.profile_switch_candidate)
        self.assertIsNotNone(self.engine.filter._last)
        self.assertIsNotNone(self.engine.writing_filter._last)

    def test_invalid_observation_cancels_pending_profile_switch(self):
        self.engine.writing_calibration.profile = profile(28.0, 0.78)
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")
        self.engine.decide(observation(0.0, 0.0, 0.50))
        self.engine.decide(observation(1.0, 28.0, 0.78))

        self.engine.decide(
            FrameObservation(timestamp=1.2, camera_ok=True, face_detected=False)
        )

        self.assertIsNone(self.engine.profile_switch_candidate)
        self.assertIsNone(self.engine.profile_switch_started_at)

    def test_calibrated_spread_expands_writing_tolerance_with_a_cap(self):
        writing = profile(28.0, 0.78)
        writing.feature_spread = {
            "pitch": 8.0,
            "gaze_y": 0.09,
        }
        self.engine.writing_calibration.profile = writing
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")

        thresholds = self.engine._profile_thresholds("writing")
        relative = RelativeMetrics(
            timestamp=0.0,
            yaw_delta_deg=0.0,
            pitch_delta_deg=20.0,
            roll_delta_deg=0.0,
            gaze_x_delta=0.0,
            gaze_y_delta=0.10,
            left_eye_open_norm=1.0,
            right_eye_open_norm=1.0,
            face_scale_delta=0.0,
            confidence=0.95,
        )

        self.assertEqual(
            self.engine.policy.classify_metrics(relative),
            ObservationState.HEAD_DOWN,
        )
        self.assertEqual(
            self.engine.policy.classify_metrics(relative, thresholds),
            ObservationState.NORMAL_VIEW,
        )
        self.assertLessEqual(thresholds.pitch_down_enter_deg, 16.0 * 1.8)
        self.assertLessEqual(thresholds.gaze_y_enter, 0.08 * 1.5)

    def test_closed_lids_remain_detectable_without_iris(self):
        closed = observation(0.0, 0.0, 0.5)
        closed.left_eye_open_ratio = 0.02
        closed.right_eye_open_ratio = 0.02
        closed.left_gaze_x = closed.right_gaze_x = None
        closed.left_gaze_y = closed.right_gaze_y = None
        closed.gaze_x = closed.gaze_y = None

        self.engine.decide(closed)
        closed.timestamp = 1.1
        decision = self.engine.decide(closed)
        self.assertEqual(decision.raw_state, ObservationState.EYES_CLOSED)
        self.assertEqual(decision.effective_state, EffectiveState.NON_FOCUS)

        closed.left_eye_open_ratio = None
        closed.timestamp = 1.2
        decision = self.engine.decide(closed)
        self.assertEqual(decision.effective_state, EffectiveState.UNSCORED)

    def test_open_lids_without_iris_are_unscored(self):
        missing = observation(0.0, 0.0, 0.5)
        missing.left_gaze_x = missing.right_gaze_x = None
        missing.left_gaze_y = missing.right_gaze_y = None
        missing.gaze_x = missing.gaze_y = None
        self.assertEqual(
            self.engine.decide(missing).effective_state,
            EffectiveState.UNSCORED,
        )

    def test_dual_profiles_do_not_treat_open_eyes_as_closed(self):
        writing = profile(28.0, 0.78)
        writing.left_eye_open_baseline = 0.4
        writing.right_eye_open_baseline = 0.4
        self.engine.writing_calibration.profile = writing
        self.engine.writing_calibration.status = CalibrationStatus.READY
        self.engine.set_work_mode("screen_writing")

        current = observation(0.0, 0.0, 0.5)
        current.left_eye_open_ratio = current.right_eye_open_ratio = 0.13
        self.assertFalse(self.engine._eyes_closed(current))
        self.assertNotEqual(
            self.engine.decide(current).raw_state,
            ObservationState.EYES_CLOSED,
        )

    def test_screen_thresholds_include_guided_monitor_edges(self):
        screen = profile(0.0, 0.0)
        screen.gaze_x_center = 0.0
        screen.target_centers = {
            "center": {"yaw": 0.0, "pitch": 0.0, "gaze_x": 0.0, "gaze_y": 0.0},
            "left": {"yaw": -22.0, "pitch": 0.0, "gaze_x": -0.2, "gaze_y": 0.0},
            "right": {"yaw": 24.0, "pitch": 0.0, "gaze_x": 0.2, "gaze_y": 0.0},
            "up": {"yaw": 0.0, "pitch": -15.0, "gaze_x": 0.0, "gaze_y": -0.06},
            "down": {"yaw": 0.0, "pitch": 19.0, "gaze_x": 0.0, "gaze_y": 0.06},
        }
        self.engine.calibration.profile = screen

        thresholds = self.engine._profile_thresholds("screen")
        self.engine.policy.stabilizer.current = ObservationState.HEAD_SIDE
        relative = RelativeMetrics(
            timestamp=1.0,
            yaw_delta_deg=22.0,
            pitch_delta_deg=0.0,
            roll_delta_deg=0.0,
            gaze_x_delta=0.20,
            gaze_y_delta=0.06,
            left_eye_open_norm=1.0,
            right_eye_open_norm=1.0,
            face_scale_delta=0.0,
            confidence=0.95,
        )

        self.assertGreaterEqual(thresholds.yaw_enter_deg, 26.0)
        self.assertEqual(thresholds.yaw_exit_deg, 24.0)
        self.assertGreaterEqual(thresholds.gaze_x_enter, 0.24)
        self.assertAlmostEqual(thresholds.gaze_x_exit, 0.20)
        self.assertGreaterEqual(thresholds.gaze_y_enter, 0.08)
        self.assertAlmostEqual(thresholds.gaze_y_exit, 0.06)
        self.assertEqual(
            self.engine.policy.classify_metrics(relative, thresholds),
            ObservationState.NORMAL_VIEW,
        )


if __name__ == "__main__":
    unittest.main()
