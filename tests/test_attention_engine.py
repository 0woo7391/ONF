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
            gaze_y_delta=0.25,
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
        self.assertLessEqual(thresholds.gaze_y_enter, 0.22 * 1.5)


if __name__ == "__main__":
    unittest.main()
