import unittest
from dataclasses import replace

import numpy as np

from onf_v2.core.attention_engine import AttentionEngine
from onf_v2.core.calibration import CalibrationManager
from onf_v2.core.models import CalibrationStatus, FrameObservation
from onf_v2.core.screen_gaze import (
    ScreenGazeContext, fit_screen_gaze, validate_screen_gaze,
)


CONTEXT = ScreenGazeContext(0, (1280, 720), "monitor", (-1920, -100, 1920, 1080), (1920, 1080), 1.25)
POSITIONS = {
    "center": (0.5, 0.5), "up": (0.5, 0.22), "down": (0.5, 0.82),
    "left": (0.16, 0.5), "right": (0.84, 0.5),
}


def gaze_observation(timestamp, point):
    u, v = point
    return FrameObservation(
        timestamp=timestamp, camera_ok=True, face_detected=True, face_count=1,
        tracking_confidence=0.95, face_scale=0.4, face_center=(0.5, 0.5),
        head_yaw_deg=0.0, head_pitch_deg=0.0, head_roll_deg=0.0,
        gaze_x=-0.04 + 0.2 * u + 0.03 * v,
        gaze_y=0.02 - 0.02 * u + 0.18 * v,
        left_eye_open_ratio=0.25, right_eye_open_ratio=0.25,
    )


def samples_at(positions, start=0.0, count=15):
    return {
        key: [gaze_observation(start + index * 10 + frame * 0.1, point) for frame in range(count)]
        for index, (key, point) in enumerate(positions.items())
    }


class ScreenGazeTests(unittest.TestCase):
    def setUp(self):
        self.mapping = fit_screen_gaze(CONTEXT, samples_at(POSITIONS), POSITIONS)

    def test_affine_mapping_and_fresh_intermediate_validation(self):
        positions = self.mapping.validation_positions
        samples = samples_at(positions, start=100.0)
        attempts = {key: 20 for key in positions}
        coefficients = self.mapping.coefficients

        report = validate_screen_gaze(self.mapping, CONTEXT, samples, positions, attempts)

        self.assertEqual(self.mapping.coefficients, coefficients)
        self.assertEqual(len(report), 5)
        for region in report:
            self.assertLess(region.p90_error, 0.001)
            self.assertEqual(region.prediction_spread, 0.0)
            self.assertEqual(region.valid_fraction, 0.75)
        self.assertNotEqual(positions["up"], POSITIONS["up"])
        self.assertEqual(positions["center"], POSITIONS["center"])

    def test_high_fps_direction_has_no_extra_fit_weight(self):
        samples = samples_at(POSITIONS)
        samples["up"] *= 100
        mapping = fit_screen_gaze(CONTEXT, samples, POSITIONS)
        np.testing.assert_allclose(mapping.coefficients, self.mapping.coefficients)

    def test_constant_eyes_cannot_be_rescued_by_head_movement(self):
        samples = samples_at(POSITIONS)
        for index, observations in enumerate(samples.values()):
            for sample in observations:
                sample.gaze_x = 0.0
                sample.gaze_y = 0.0
                sample.head_yaw_deg = index * 15.0
                sample.head_pitch_deg = index * 12.0
        with self.assertRaisesRegex(ValueError, "too small"):
            fit_screen_gaze(CONTEXT, samples, POSITIONS)

    def test_collinear_nonfinite_or_missing_eye_data_rejected(self):
        samples = samples_at(POSITIONS)
        for observations in samples.values():
            for sample in observations:
                sample.gaze_y = sample.gaze_x * 2
        with self.assertRaisesRegex(ValueError, "independent axes"):
            fit_screen_gaze(CONTEXT, samples, POSITIONS)
        for value in (float("nan"), float("inf"), None):
            samples = samples_at(POSITIONS)
            samples["center"][0].gaze_x = value
            with self.assertRaises(ValueError):
                fit_screen_gaze(CONTEXT, samples, POSITIONS)

    def test_stable_wrong_predictions_stay_wrong_and_unclipped(self):
        positions = self.mapping.validation_positions
        samples = samples_at(positions, start=100.0)
        for observations in samples.values():
            for sample in observations:
                sample.gaze_x += 0.6
        report = validate_screen_gaze(
            self.mapping, CONTEXT, samples, positions, {key: 15 for key in positions}
        )
        self.assertGreater(self.mapping.predict(samples["center"][0])[0], 1)
        for region in report:
            self.assertGreater(region.median_error, 1.0)
            self.assertEqual(region.prediction_spread, 0.0)

    def test_large_residuals_are_kept_in_p90_and_spread(self):
        positions = self.mapping.validation_positions
        samples = samples_at(positions, start=100.0)
        for sample in samples["up"][-4:]:
            sample.gaze_y += 0.8
        report = validate_screen_gaze(
            self.mapping, CONTEXT, samples, positions, {key: 15 for key in positions}
        )
        up = next(region for region in report if region.key == "up")
        self.assertEqual(up.valid_count, 15)
        self.assertEqual(up.valid_fraction, 1.0)
        self.assertLess(up.median_error, 0.001)
        self.assertGreater(up.p90_error, 1.0)
        self.assertGreater(up.prediction_spread, 1.0)

    def test_training_positions_and_old_duplicate_reversed_frames_are_not_validation(self):
        positions = self.mapping.validation_positions
        attempts = {key: 15 for key in positions}
        with self.assertRaises(ValueError):
            validate_screen_gaze(self.mapping, CONTEXT, samples_at(POSITIONS, 100), POSITIONS, attempts)
        cases = [samples_at(positions), samples_at(positions, 100), samples_at(positions, 100)]
        cases[1]["up"][0].timestamp = cases[1]["center"][0].timestamp
        cases[2]["center"].reverse()
        for samples in cases:
            with self.assertRaises(ValueError):
                validate_screen_gaze(self.mapping, CONTEXT, samples, positions, attempts)

    def test_geometry_dpi_capture_or_camera_change_is_incompatible(self):
        positions = self.mapping.validation_positions
        samples = samples_at(positions, 100)
        for context in (
            replace(CONTEXT, window_size=(1280, 720)),
            replace(CONTEXT, screen_rect=(0, 0, 1920, 1080)),
            replace(CONTEXT, device_pixel_ratio=1.5),
            replace(CONTEXT, camera_index=1),
            replace(CONTEXT, frame_size=(640, 480)),
            replace(CONTEXT, feature_version="changed"),
        ):
            with self.assertRaisesRegex(ValueError, "configuration changed"):
                validate_screen_gaze(self.mapping, context, samples, positions, {key: 15 for key in positions})
        with self.assertRaises(ValueError):
            replace(CONTEXT, device_pixel_ratio=0)

    def test_validation_collector_counts_invalid_frames_without_building_posture(self):
        manager = CalibrationManager(
            guided_targets=("center",), samples_per_target=2, target_settle_seconds=0,
            collection_only=True,
        )
        manager.start(100)
        manager.update(gaze_observation(100, (0.5, 0.5)))
        closed = gaze_observation(100.1, (0.5, 0.5))
        closed.left_eye_open_ratio = 0.01
        manager.update(closed)
        manager.update(closed)
        progress = manager.update(gaze_observation(100.2, (0.5, 0.5)))
        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertIsNone(manager.profile)
        self.assertEqual(manager.attempted_samples_by_target["center"], 3)
        self.assertEqual(len(manager.samples_by_target["center"]), 2)

    def test_shadow_fit_failure_does_not_reject_coarse_posture(self):
        engine = AttentionEngine()
        engine.screen_gaze_mapping = self.mapping
        previous_result = (object(),)
        engine.gaze_validation_result = previous_result
        manager = engine.calibration
        manager.samples_per_target = 2
        manager.target_settle_seconds = manager.target_valid_seconds = 0
        engine.start_calibration(0)
        manager.display_context = CONTEXT
        manager.target_positions = POSITIONS.copy()
        manager.mapping_context_valid = False
        timestamp = 0.0
        for key in manager.guided_targets:
            for _ in range(2):
                sample = gaze_observation(timestamp, (0.5, 0.5))
                sample.head_yaw_deg = {"left": -8, "right": 8}.get(key, 0)
                sample.head_pitch_deg = {"up": -8, "down": 8}.get(key, 0)
                progress = engine.update_calibration(sample)
                timestamp += 0.1
        self.assertEqual(progress.status, CalibrationStatus.READY)
        self.assertTrue(engine.ready_for_session)
        self.assertIs(engine.screen_gaze_mapping, self.mapping)
        self.assertIs(engine.gaze_validation_result, previous_result)
        engine.start_calibration(100)
        manager.display_context = CONTEXT
        manager.target_positions = POSITIONS.copy()
        timestamp = 100.0
        for key in manager.guided_targets:
            for _ in range(2):
                engine.update_calibration(gaze_observation(timestamp, POSITIONS[key]))
                timestamp += 0.1
        self.assertIsNot(engine.screen_gaze_mapping, self.mapping)
        self.assertEqual(engine.gaze_validation_result, ())


if __name__ == "__main__":
    unittest.main()
