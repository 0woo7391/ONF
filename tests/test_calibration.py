import unittest

from onf_v2.core.calibration import CalibrationManager
from onf_v2.core.models import CalibrationStatus, FrameObservation


def observation(timestamp, yaw=1.0, pitch=2.0, face_center=(0.5, 0.5)):
    return FrameObservation(
        timestamp=timestamp,
        camera_ok=True,
        face_detected=True,
        face_count=1,
        tracking_confidence=0.95,
        face_scale=0.4,
        face_center=face_center,
        head_yaw_deg=yaw,
        head_pitch_deg=pitch,
        head_roll_deg=0.0,
        gaze_x=0.5,
        gaze_y=0.5,
        left_eye_open_ratio=0.25,
        right_eye_open_ratio=0.25,
    )


class CalibrationManagerTest(unittest.TestCase):
    def test_builds_profile_from_stable_samples(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)
        for idx in range(20):
            progress = manager.update(observation(idx * 0.06))

        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertIsNotNone(progress.profile)
        self.assertAlmostEqual(progress.profile.yaw_center, 1.0)

    def test_fails_when_samples_move_too_much(self):
        manager = CalibrationManager(duration_seconds=1.0, max_yaw_stdev=0.5)
        manager.start(0.0)
        for idx in range(20):
            progress = manager.update(observation(idx * 0.06, yaw=float(idx)))

        self.assertEqual(progress.status, CalibrationStatus.FAILED)

    def test_builds_profile_at_users_actual_off_center_position(self):
        manager = CalibrationManager(duration_seconds=4.0)
        manager.start(0.0)
        for idx in range(41):
            progress = manager.update(
                observation(idx * 0.1, face_center=(0.24, 0.68))
            )

        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertIsNotNone(progress.profile)
        self.assertEqual(progress.profile.face_center, (0.24, 0.68))
        self.assertEqual(progress.target_samples, 40)

    def test_reports_actionable_feedback_while_face_is_missing(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)

        progress = manager.update(
            FrameObservation(timestamp=0.2, camera_ok=True, face_detected=False)
        )

        self.assertEqual(progress.status, CalibrationStatus.COLLECTING)
        self.assertIn("얼굴을 찾지 못했습니다", progress.message)
        self.assertIn("양쪽 눈", progress.message)

    def test_failure_uses_most_frequent_actionable_reason(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)
        for idx in range(12):
            progress = manager.update(
                FrameObservation(
                    timestamp=idx * 0.1,
                    camera_ok=True,
                    face_detected=False,
                )
            )

        self.assertEqual(progress.status, CalibrationStatus.FAILED)
        self.assertIn("얼굴을 찾지 못했습니다", progress.message)


if __name__ == "__main__":
    unittest.main()
