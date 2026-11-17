from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from .models import FrameObservation


TARGET_KEYS = ("center", "up", "down", "left", "right")


@dataclass(frozen=True)
class ScreenGazeContext:
    camera_index: int
    frame_size: tuple[int, int]
    screen_name: str
    screen_rect: tuple[float, float, float, float]
    window_size: tuple[float, float]
    device_pixel_ratio: float
    feature_version: str = "eye-width-v1/unmirrored"

    def __post_init__(self) -> None:
        values = (*self.frame_size, *self.screen_rect, *self.window_size, self.device_pixel_ratio)
        if (
            self.camera_index < 0 or not all(math.isfinite(value) for value in values)
            or min(*self.frame_size, *self.screen_rect[2:], *self.window_size, self.device_pixel_ratio) <= 0
        ):
            raise ValueError("Screen and camera dimensions must be finite and positive")


@dataclass(frozen=True)
class GazeValidationRegion:
    key: str
    median_error: float
    p90_error: float
    prediction_spread: float
    valid_count: int
    attempted_count: int

    @property
    def valid_fraction(self) -> float:
        return self.valid_count / self.attempted_count


@dataclass(frozen=True)
class ScreenGazeMapping:
    context: ScreenGazeContext
    feature_center: tuple[float, float]
    feature_scale: tuple[float, float]
    coefficients: tuple[tuple[float, float], ...]
    target_positions: tuple[tuple[str, float, float], ...]
    acquired_until: float

    def predict(self, observation: FrameObservation) -> tuple[float, float]:
        gaze = _eye_features(observation)
        row = np.r_[1.0, (gaze - self.feature_center) / self.feature_scale]
        # Keep off-screen predictions: clipping would hide validation errors.
        return tuple(float(value) for value in row @ self.coefficients)

    @property
    def validation_positions(self) -> dict[str, tuple[float, float]]:
        positions = {key: (u, v) for key, u, v in self.target_positions}
        center = np.asarray(positions["center"])
        return {
            key: tuple(float(value) for value in (center + point) / 2)
            for key, point in positions.items()
        }


def _eye_features(observation: FrameObservation) -> np.ndarray:
    values = (observation.gaze_x, observation.gaze_y)
    if any(value is None or not math.isfinite(value) for value in values):
        raise ValueError("Finite eye features are required")
    return np.asarray(values, dtype=float)


def _positions(positions: Mapping[str, tuple[float, float]]) -> np.ndarray:
    if set(positions) != set(TARGET_KEYS):
        raise ValueError("Actual positions for all five targets are required")
    result = np.asarray([positions[key] for key in TARGET_KEYS], dtype=float)
    if result.shape != (5, 2) or not np.isfinite(result).all() or (result < 0).any() or (result > 1).any():
        raise ValueError("Target positions must be finite monitor-local coordinates")
    return result


def fit_screen_gaze(
    context: ScreenGazeContext,
    samples: Mapping[str, Sequence[FrameObservation]],
    positions: Mapping[str, tuple[float, float]],
) -> ScreenGazeMapping:
    labels = _positions(positions)
    if any(not samples.get(key) for key in TARGET_KEYS):
        raise ValueError("Eye observations for all five targets are required")
    features = np.asarray([
        np.median([_eye_features(sample) for sample in samples[key]], axis=0)
        for key in TARGET_KEYS
    ])
    center = features.mean(axis=0)
    scale = features.std(axis=0)
    # Numerical floor only; independent validation determines practical usefulness.
    if (scale <= np.sqrt(np.finfo(float).eps)).any():
        raise ValueError("Eye direction changes are too small to fit two axes")
    design = np.column_stack((np.ones(5), (features - center) / scale))
    if np.linalg.matrix_rank(design) != 3:
        raise ValueError("Eye observations do not cover two independent axes")
    timestamps = [sample.timestamp for key in TARGET_KEYS for sample in samples[key]]
    if not all(math.isfinite(timestamp) for timestamp in timestamps):
        raise ValueError("Finite acquisition timestamps are required")
    # One median per target keeps high-FPS directions from dominating the fit.
    penalty = np.diag([0.0, math.sqrt(1e-3), math.sqrt(1e-3)])
    coefficients = np.linalg.lstsq(
        np.vstack((design, penalty)), np.vstack((labels, np.zeros((3, 2)))), rcond=None
    )[0]
    return ScreenGazeMapping(
        context=context,
        feature_center=tuple(center),
        feature_scale=tuple(scale),
        coefficients=tuple(tuple(row) for row in coefficients),
        target_positions=tuple((key, *positions[key]) for key in TARGET_KEYS),
        acquired_until=max(timestamps),
    )


def validate_screen_gaze(
    mapping: ScreenGazeMapping,
    context: ScreenGazeContext,
    samples: Mapping[str, Sequence[FrameObservation]],
    positions: Mapping[str, tuple[float, float]],
    attempts: Mapping[str, int],
) -> tuple[GazeValidationRegion, ...]:
    if context != mapping.context:
        raise ValueError("Monitor or camera configuration changed; acquire a new mapping")
    labels = _positions(positions)
    original = {key: (u, v) for key, u, v in mapping.target_positions}
    if any(np.allclose(positions[key], original[key], rtol=0, atol=1e-9) for key in TARGET_KEYS[1:]):
        raise ValueError("Validation must use separate intermediate target positions")
    size = np.asarray(context.window_size)
    diagonal = np.linalg.norm(size)
    seen_timestamps = set()
    result = []
    for key, label in zip(TARGET_KEYS, labels):
        observations = samples.get(key, ())
        attempted_count = attempts.get(key, 0)
        if not observations or attempted_count < len(observations):
            raise ValueError("Independent validation observations and attempt counts are required")
        previous_timestamp = mapping.acquired_until
        for observation in observations:
            timestamp = observation.timestamp
            if not math.isfinite(timestamp) or timestamp <= previous_timestamp or timestamp in seen_timestamps:
                raise ValueError("Validation requires fresh, distinct, ordered observations")
            previous_timestamp = timestamp
            seen_timestamps.add(timestamp)
        predictions = np.asarray([mapping.predict(observation) for observation in observations])
        errors = np.linalg.norm((predictions - label) * size, axis=1) / diagonal
        spread = np.linalg.norm((predictions - np.median(predictions, axis=0)) * size, axis=1) / diagonal
        result.append(GazeValidationRegion(
            key=key,
            median_error=float(np.median(errors)),
            p90_error=float(np.percentile(errors, 90)),
            prediction_spread=float(np.percentile(spread, 90)),
            valid_count=len(observations),
            attempted_count=attempted_count,
        ))
    return tuple(result)
