import unittest

from onf_v2.core.attention_engine import AttentionEngine
from onf_v2.core.models import (
    CalibrationProfile,
    CalibrationStatus,
    EffectiveState,
    FrameObservation,
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

        decision = self.engine.decide(observation(0.0, 28.0, 0.78))

        self.assertEqual(decision.effective_state, EffectiveState.FOCUS)
        self.assertEqual(self.engine.last_matched_profile, "writing")

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


if __name__ == "__main__":
    unittest.main()
