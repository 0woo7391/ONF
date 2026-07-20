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

    def test_profile_stores_robust_feature_spread(self):
        manager = CalibrationManager(
            duration_seconds=1.0,
            max_yaw_stdev=10.0,
            max_pitch_stdev=10.0,
        )
        manager.start(0.0)
        for idx in range(20):
            sample = observation(
                idx * 0.06,
                yaw=float((idx % 5) - 2),
                pitch=2.0 + float((idx % 5) - 2) * 2.0,
            )
            sample.gaze_x = 0.5 + float((idx % 3) - 1) * 0.03
            sample.gaze_y = 0.5 + float((idx % 3) - 1) * 0.04
            progress = manager.update(sample)

        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertGreater(progress.profile.feature_spread["yaw"], 0.0)
        self.assertGreater(progress.profile.feature_spread["pitch"], 0.0)
        self.assertGreater(progress.profile.feature_spread["gaze_x"], 0.0)
        self.assertGreater(progress.profile.feature_spread["gaze_y"], 0.0)

    def test_guided_calibration_collects_direction_centers(self):
        manager = CalibrationManager(
            guided_targets=("center", "left", "right", "up", "down", "natural"),
            samples_per_target=2,
            natural_samples=2,
            max_guided_seconds=10.0,
            target_settle_seconds=0.0,
        )
        manager.start(0.0)
        values = {
            "center": (0.0, 0.0, 0.50, 0.50),
            "left": (-5.0, 0.0, 0.40, 0.50),
            "right": (5.0, 0.0, 0.60, 0.50),
            "up": (0.0, -5.0, 0.50, 0.40),
            "down": (0.0, 5.0, 0.50, 0.60),
            "natural": (1.0, 1.0, 0.52, 0.52),
        }
        progress = None
        timestamp = 0.0
        for target in manager.guided_targets:
            yaw, pitch, gaze_x, gaze_y = values[target]
            for _ in range(2):
                sample = observation(timestamp, yaw=yaw, pitch=pitch)
                sample.gaze_x = gaze_x
                sample.gaze_y = gaze_y
                progress = manager.update(sample)
                timestamp += 0.1

        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertEqual(set(progress.profile.target_centers), set(manager.guided_targets))
        self.assertLess(
            progress.profile.target_centers["left"]["gaze_x"],
            progress.profile.target_centers["right"]["gaze_x"],
        )

    def test_guided_calibration_pauses_on_invalid_sample(self):
        manager = CalibrationManager(
            guided_targets=("center", "left", "right", "up", "down"),
            samples_per_target=2,
            target_settle_seconds=0.0,
        )
        manager.start(0.0)

        progress = manager.update(
            FrameObservation(timestamp=0.2, camera_ok=True, face_detected=False)
        )

        self.assertEqual(progress.target_key, "center")
        self.assertEqual(progress.target_progress, 0.0)
        self.assertEqual(progress.valid_samples, 0)

    def test_guided_calibration_rejects_missing_direction_change(self):
        manager = CalibrationManager(
            guided_targets=("center", "left", "right", "up", "down"),
            samples_per_target=2,
            max_guided_seconds=10.0,
            target_settle_seconds=0.0,
        )
        manager.start(0.0)
        progress = None
        timestamp = 0.0
        for _target in manager.guided_targets:
            for _ in range(2):
                progress = manager.update(observation(timestamp, yaw=0.0, pitch=0.0))
                timestamp += 0.1

        self.assertEqual(progress.status, CalibrationStatus.FAILED)
        self.assertIn("시선 방향 변화", progress.message)

    def test_guided_calibration_waits_after_target_change(self):
        manager = CalibrationManager(
            guided_targets=("center", "left"),
            samples_per_target=1,
            target_settle_seconds=0.5,
        )
        manager.start(10.0)

        waiting = manager.update(observation(10.2))
        center_done = manager.update(observation(10.6))
        moving = manager.update(observation(10.8, yaw=-5.0))

        self.assertEqual(waiting.valid_samples, 0)
        self.assertEqual(center_done.target_key, "left")
        self.assertEqual(moving.target_key, "left")
        self.assertEqual(moving.target_progress, 0.0)

    def test_guided_calibration_accepts_intentional_vertical_range(self):
        manager = CalibrationManager(
            guided_targets=("center", "left", "right", "up", "down"),
            samples_per_target=2,
            max_pitch_stdev=4.0,
            target_settle_seconds=0.0,
        )
        manager.start(0.0)
        values = {
            "center": (0.0, 0.50, 0.50),
            "left": (0.0, 0.35, 0.50),
            "right": (0.0, 0.65, 0.50),
            "up": (-18.0, 0.50, 0.35),
            "down": (18.0, 0.50, 0.65),
        }
        progress = None
        timestamp = 0.0
        for target in manager.guided_targets:
            pitch, gaze_x, gaze_y = values[target]
            for _ in range(2):
                sample = observation(timestamp, pitch=pitch)
                sample.gaze_x = gaze_x
                sample.gaze_y = gaze_y
                progress = manager.update(sample)
                timestamp += 0.1

        self.assertEqual(progress.status, CalibrationStatus.READY)


if __name__ == "__main__":
    unittest.main()
