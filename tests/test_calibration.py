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
    def test_live_collection_feedback_requires_consecutive_valid_stable_samples(self):
        manager = CalibrationManager(
            guided_targets=("center", "up"), samples_per_target=12,
            target_settle_seconds=0.2, target_valid_seconds=2.0,
        )
        manager.start(100.0)
        self.assertFalse(manager.collection_stable)
        manager.update(observation(100.1))
        self.assertFalse(manager.collection_stable)
        manager.update(observation(100.3))
        self.assertFalse(manager.collection_stable)
        manager.update(observation(100.4))
        self.assertTrue(manager.collection_stable)
        closed = observation(100.5)
        closed.left_eye_open_ratio = closed.right_eye_open_ratio = 0.02
        manager.update(closed)
        self.assertFalse(manager.collection_stable)
        manager.update(observation(100.6))
        self.assertFalse(manager.collection_stable)
        manager.update(observation(100.7))
        self.assertTrue(manager.collection_stable)
        collected = manager.valid_seconds_by_target["center"]
        manager.check_timeout(101.3)
        self.assertFalse(manager.collection_stable)
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], collected)
        manager.update(observation(101.4))
        self.assertFalse(manager.collection_stable)
        manager.update(observation(101.5))
        self.assertTrue(manager.collection_stable)
        manager.cancel()
        self.assertFalse(manager.collection_stable)
        manager.start(102.0)
        self.assertFalse(manager.collection_stable)

    def test_live_feedback_does_not_change_sampling_or_completion_time(self):
        manager = CalibrationManager(
            guided_targets=("center", "up"), samples_per_target=3,
            target_settle_seconds=0, target_valid_seconds=0.2,
        )
        manager.start(100.0)
        manager.update(observation(100.0))
        manager.update(observation(100.1))
        self.assertTrue(manager.collection_stable)
        progress = manager.update(observation(100.2))
        self.assertTrue(progress.stage_changed)
        self.assertEqual(manager.current_target, "up")
        self.assertFalse(manager.collection_stable)
        self.assertEqual(len(manager.samples_by_target["center"]), 3)
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.2)
        self.assertEqual(manager.target_states[0]["state"], "sampled")

    def test_unstable_head_samples_are_collected_without_green_feedback(self):
        manager = CalibrationManager(
            guided_targets=("center", "up"), samples_per_target=12,
            target_settle_seconds=0, target_valid_seconds=2.0,
            max_yaw_stdev=0.5,
        )
        manager.start(100.0)
        manager.update(observation(100.0, yaw=0))
        manager.update(observation(100.1, yaw=0))
        self.assertTrue(manager.collection_stable)
        manager.update(observation(100.2, yaw=3))
        self.assertFalse(manager.collection_stable)
        self.assertEqual(manager.target_state, "collecting")
        self.assertEqual(len(manager.samples), 3)
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.2)

    def test_guided_dwell_is_comparable_at_different_frame_rates(self):
        for fps in (5, 10, 30):
            with self.subTest(fps=fps):
                manager = CalibrationManager(
                    guided_targets=("center", "left"),
                    samples_per_target=12,
                    target_settle_seconds=2.0,
                    target_valid_seconds=2.0,
                )
                manager.start(100.0)
                for index in range(fps * 6):
                    timestamp = 100.0 + index / fps
                    progress = manager.update(observation(timestamp))
                    if progress.stage_changed:
                        break
                self.assertEqual(manager.current_target, "left")
                self.assertAlmostEqual(timestamp - 102.0, 2.0, delta=1 / fps + 1e-9)
                self.assertGreaterEqual(len(manager.samples_by_target["center"]), 12)
                self.assertEqual([item["state"] for item in manager.target_states], ["sampled", "waiting"])
                self.assertAlmostEqual(progress.progress, 0.5)

    def test_duplicate_out_of_order_and_nonfinite_timestamps_do_not_fill_ring(self):
        manager = CalibrationManager(
            guided_targets=("center", "left"), samples_per_target=12,
            target_settle_seconds=0.0, target_valid_seconds=2.0,
        )
        manager.start(10.0)
        manager.update(observation(10.0))
        before = manager.update(observation(10.1))
        for timestamp in (10.1, 10.05, float("nan"), float("inf")):
            progress = manager.update(observation(timestamp))
            self.assertEqual(progress.valid_samples, 2)
            self.assertEqual(progress.target_progress, before.target_progress)
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.1)

    def test_invalid_eyes_and_frame_gaps_pause_without_erasing_collected_time(self):
        manager = CalibrationManager(
            guided_targets=("center", "left"), samples_per_target=12,
            target_settle_seconds=0.0, target_valid_seconds=2.0,
        )
        manager.start(10.0)
        manager.update(observation(10.0))
        manager.update(observation(10.1))
        closed = observation(10.2)
        closed.left_eye_open_ratio = closed.right_eye_open_ratio = 0.02
        paused = manager.update(closed)
        self.assertEqual(paused.target_state, "paused")
        self.assertIn("눈", paused.message)
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.1)
        manager.update(observation(10.3))
        manager.update(observation(10.4))
        manager.update(observation(11.0))
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.2)
        manager.update(observation(11.1))
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.3)

    def test_analysis_stall_pauses_then_times_out_without_callbacks(self):
        manager = CalibrationManager(
            guided_targets=("center", "left"), samples_per_target=12,
            target_settle_seconds=0.0, target_valid_seconds=2.0,
            max_target_seconds=3.0,
        )
        previous_profile = object()
        manager.profile = previous_profile
        manager.start(10.0)
        manager.update(observation(10.0))
        manager.update(observation(10.1))
        paused = manager.check_timeout(10.7)
        self.assertEqual(paused.target_state, "paused")
        self.assertIn("분석값", paused.message)
        self.assertIsNone(manager.check_timeout(10.8))
        manager.update(observation(11.0))
        self.assertAlmostEqual(manager.valid_seconds_by_target["center"], 0.1)
        failed = manager.check_timeout(13.0)
        self.assertEqual(failed.status, CalibrationStatus.FAILED)
        self.assertEqual(manager.failed_targets, ("center",))
        self.assertIs(manager.profile, previous_profile)

    def test_unstable_direction_retry_keeps_completed_directions_and_previous_profile(self):
        manager = CalibrationManager(
            guided_targets=("center", "up", "down", "left", "right"),
            samples_per_target=4, target_settle_seconds=0.0,
            target_valid_seconds=0.3, max_yaw_stdev=0.5,
        )
        previous_profile = object()
        manager.profile = previous_profile
        manager.start(0.0)
        for index in range(4):
            manager.update(observation(index * 0.1, yaw=0.0))
        center_samples = list(manager.samples_by_target["center"])
        for index in range(4):
            failed = manager.update(observation(0.4 + index * 0.1, yaw=10.0 if index % 2 else -10.0))
        self.assertEqual(failed.status, CalibrationStatus.FAILED)
        self.assertEqual(manager.failed_targets, ("up",))
        self.assertTrue(manager.retry_failed(2.0))
        self.assertIs(manager.profile, previous_profile)
        self.assertEqual(manager.current_target, "up")
        self.assertEqual(manager.samples_by_target["center"], center_samples)
        self.assertEqual(manager.samples_by_target["up"], [])
        self.assertEqual(manager.completed_targets, {"center"})
        manager.cancel()
        self.assertIs(manager.profile, previous_profile)
        self.assertEqual(manager.status, CalibrationStatus.READY)
        self.assertFalse(manager.retry_failed(3.0))

    def test_insufficient_horizontal_coverage_retries_only_left_and_right(self):
        manager = CalibrationManager(
            guided_targets=("center", "up", "down", "left", "right"),
            samples_per_target=2, target_settle_seconds=0.0,
        )
        manager.start(0.0)
        timestamp = 0.0
        for target in manager.guided_targets:
            pitch = -5.0 if target == "up" else 5.0 if target == "down" else 0.0
            for _ in range(2):
                failed = manager.update(observation(timestamp, yaw=0.0, pitch=pitch))
                timestamp += 0.1
        self.assertEqual(failed.status, CalibrationStatus.FAILED)
        self.assertEqual(manager.failed_targets, ("left", "right"))
        kept = {key: list(manager.samples_by_target[key]) for key in ("center", "up", "down")}
        self.assertTrue(manager.retry_failed(2.0))
        self.assertEqual(manager.current_target, "left")
        self.assertEqual(manager.completed_targets, set(kept))
        timestamp = 2.0
        for target in ("left", "right"):
            for _ in range(2):
                progress = manager.update(observation(timestamp, yaw=-5.0 if target == "left" else 5.0, pitch=0.0))
                timestamp += 0.1
        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertEqual(progress.quality_score, progress.profile.quality_score)
        self.assertTrue(all(item["state"] == "sampled" for item in manager.target_states))
        for key, samples in kept.items():
            self.assertEqual(manager.samples_by_target[key], samples)

    def test_nonfinite_head_metrics_are_rejected_before_profile_build(self):
        manager = CalibrationManager(
            guided_targets=("center",), target_settle_seconds=0.0,
        )
        manager.start(0.0)
        for index, value in enumerate((float("nan"), float("inf"))):
            progress = manager.update(observation(0.1 + index * 0.1, yaw=value))
            self.assertEqual(progress.valid_samples, 0)
            self.assertEqual(progress.target_state, "paused")
            self.assertIn("고개 방향", progress.message)

    def test_guided_samples_wait_for_displayed_target_and_reject_old_frames(self):
        manager = CalibrationManager(
            guided_targets=("center", "left"),
            samples_per_target=1,
            target_settle_seconds=0.5,
            require_display_ack=True,
        )
        manager.start(10.0)
        self.assertEqual(manager.update(observation(11.0)).valid_samples, 0)
        self.assertTrue(manager.confirm_target_displayed(11.5, 0, "center"))
        self.assertEqual(manager.update(observation(11.4)).valid_samples, 0)
        self.assertEqual(manager.update(observation(11.8)).valid_samples, 0)
        center = manager.update(observation(12.1))
        self.assertEqual(center.target_key, "left")
        self.assertEqual(center.valid_samples, 1)
        self.assertEqual(manager.update(observation(13.0)).valid_samples, 1)
        self.assertFalse(manager.confirm_target_displayed(13.0, 0, "center"))
        self.assertTrue(manager.confirm_target_displayed(13.1, 1, "left"))
        self.assertEqual(manager.update(observation(13.0)).valid_samples, 1)

    def test_calibration_times_out_without_observations_and_preserves_profile(self):
        guided = CalibrationManager(
            guided_targets=("center",), max_guided_seconds=3.0,
            require_display_ack=True,
        )
        guided.profile = object()
        guided.start(10.0)
        self.assertIsNone(guided.check_timeout(12.9))
        failed = guided.check_timeout(13.1)
        self.assertEqual(failed.status, CalibrationStatus.FAILED)
        self.assertIn("표적", failed.message)
        self.assertIsNotNone(guided.profile)

        writing = CalibrationManager(
            duration_seconds=12.0,
            progress_by_valid_samples=True,
            max_collection_seconds=30.0,
        )
        writing.start(0.0)
        self.assertIsNone(writing.check_timeout(29.9))
        failed = writing.check_timeout(30.1)
        self.assertEqual(failed.status, CalibrationStatus.FAILED)
        self.assertIn("분석", failed.message)

    def test_eye_width_gaze_calibration_keeps_signed_vertical_delta(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)
        for index in range(20):
            sample = observation(index * 0.06)
            sample.gaze_x = 0.15
            sample.gaze_y = -0.05
            progress = manager.update(sample)
        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertAlmostEqual(progress.profile.gaze_y_center, -0.05)

        current = observation(2.0)
        current.gaze_x = 0.20
        current.gaze_y = -0.01
        relative = manager.normalize(current)
        self.assertAlmostEqual(relative.gaze_x_delta, 0.05)
        self.assertAlmostEqual(relative.gaze_y_delta, 0.04)

    def test_rejects_closed_or_conflicting_eye_samples(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)

        closed = observation(0.1)
        closed.left_eye_open_ratio = closed.right_eye_open_ratio = 0.02
        progress = manager.update(closed)
        self.assertEqual(progress.valid_samples, 0)

        conflicting = observation(0.2)
        conflicting.left_gaze_x = -0.3
        conflicting.right_gaze_x = 0.3
        conflicting.left_gaze_y = conflicting.right_gaze_y = 0.0
        progress = manager.update(conflicting)
        self.assertEqual(progress.valid_samples, 0)

        valid = observation(0.3)
        valid.left_gaze_x = valid.right_gaze_x = 0.0
        valid.left_gaze_y = valid.right_gaze_y = 0.0
        progress = manager.update(valid)
        self.assertEqual(progress.valid_samples, 1)

    def test_recalibration_failure_and_cancel_keep_previous_profile(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)
        for idx in range(20):
            progress = manager.update(observation(idx * 0.06))
        self.assertEqual(progress.status, CalibrationStatus.READY)
        previous_profile = manager.profile

        manager.start(2.0)
        self.assertIs(manager.profile, previous_profile)
        failed = manager.update(
            FrameObservation(timestamp=3.1, camera_ok=True, face_detected=False)
        )
        self.assertEqual(failed.status, CalibrationStatus.FAILED)
        self.assertIs(manager.profile, previous_profile)
        self.assertTrue(manager.ready)

        manager.start(4.0)
        manager.cancel()
        self.assertIs(manager.profile, previous_profile)
        self.assertTrue(manager.ready)

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

    def test_natural_range_calibration_accepts_posture_changes(self):
        manager = CalibrationManager(
            duration_seconds=1.0,
            max_yaw_stdev=0.5,
            max_pitch_stdev=0.5,
            enforce_stability=False,
        )
        manager.start(0.0)
        for idx in range(20):
            progress = manager.update(
                observation(idx * 0.06, yaw=float(idx), pitch=float(idx * 2))
            )

        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertGreater(progress.profile.feature_spread["yaw"], 0.5)
        self.assertGreater(progress.profile.feature_spread["pitch"], 0.5)

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

    def test_normalize_uses_shortest_angle_across_wrap_boundary(self):
        manager = CalibrationManager(duration_seconds=1.0)
        manager.start(0.0)
        for idx in range(20):
            sample = observation(idx * 0.06, yaw=179.0, pitch=-179.0)
            sample.head_roll_deg = 179.0
            progress = manager.update(sample)

        current = observation(2.0, yaw=-179.0, pitch=179.0)
        current.head_roll_deg = -179.0
        relative = manager.normalize(current)

        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertAlmostEqual(relative.yaw_delta_deg, 2.0)
        self.assertAlmostEqual(relative.pitch_delta_deg, -2.0)
        self.assertAlmostEqual(relative.roll_delta_deg, 2.0)

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

    def test_guided_baseline_uses_center_target_not_pooled_screen_positions(self):
        manager = CalibrationManager(
            guided_targets=("center", "left", "right", "up", "down"),
            samples_per_target=2,
            max_guided_seconds=10.0,
            target_settle_seconds=0.0,
        )
        manager.start(0.0)
        values = {
            "center": (0.0, 0.0, 0.50, 0.50),
            "left": (-22.0, 0.0, 0.20, 0.50),
            "right": (24.0, 0.0, 0.80, 0.50),
            "up": (0.0, -15.0, 0.50, 0.25),
            "down": (0.0, 19.0, 0.50, 0.75),
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
        self.assertAlmostEqual(progress.profile.yaw_center, 0.0)
        self.assertAlmostEqual(progress.profile.pitch_center, 0.0)
        self.assertAlmostEqual(progress.profile.gaze_x_center, 0.5)
        self.assertAlmostEqual(progress.profile.gaze_y_center, 0.5)
        self.assertAlmostEqual(progress.profile.feature_spread["yaw"], 0.0)
        self.assertAlmostEqual(progress.profile.feature_spread["gaze_x"], 0.0)

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

    def test_valid_sample_progress_does_not_advance_for_missing_face(self):
        manager = CalibrationManager(
            duration_seconds=2.0,
            target_sample_rate=2.0,
            progress_by_valid_samples=True,
            max_collection_seconds=8.0,
        )
        manager.start(0.0)

        first = manager.update(observation(0.5))
        missing = manager.update(
            FrameObservation(timestamp=1.5, camera_ok=True, face_detected=False)
        )

        self.assertEqual(first.valid_samples, 1)
        self.assertEqual(missing.valid_samples, 1)
        self.assertEqual(missing.progress, first.progress)
        self.assertEqual(missing.status, CalibrationStatus.COLLECTING)

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
