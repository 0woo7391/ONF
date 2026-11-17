from __future__ import annotations

import math
from dataclasses import dataclass

from .models import FrameObservation, MODE_THRESHOLDS, Mode, ObservationState


@dataclass
class QualityGate:
    mode: Mode = Mode.NORMAL
    max_horizontal_gaze_disagreement: float = 0.28
    max_vertical_gaze_disagreement: float = 0.10

    def evaluate(
        self, observation: FrameObservation, eyes_closed: bool = False
    ) -> ObservationState:
        thresholds = MODE_THRESHOLDS[self.mode]
        if not observation.camera_ok:
            return ObservationState.CAMERA_ERROR
        if observation.error:
            return ObservationState.PROCESSING_ERROR
        if not observation.face_detected:
            return ObservationState.NO_FACE
        if observation.face_count > 1:
            return ObservationState.MULTIPLE_FACES
        if (
            observation.face_scale is None
            or not math.isfinite(observation.face_scale)
            or observation.face_scale < thresholds.min_face_scale
        ):
            return ObservationState.LOW_CONFIDENCE
        if observation.face_bbox:
            x0, y0, x1, y1 = observation.face_bbox
            if (
                not all(math.isfinite(value) for value in observation.face_bbox)
                or x0 < 0.01 or y0 < 0.01 or x1 > 0.99 or y1 > 0.99
            ):
                return ObservationState.LOW_CONFIDENCE
        if (
            not math.isfinite(observation.tracking_confidence)
            or observation.tracking_confidence < thresholds.min_confidence
        ):
            return ObservationState.LOW_CONFIDENCE
        lid_values = (
            observation.left_eye_open_ratio,
            observation.right_eye_open_ratio,
        )
        if any(
            value is None or not math.isfinite(value) or not 0.0 <= value <= 0.7
            for value in lid_values
        ):
            return ObservationState.LOW_CONFIDENCE

        if eyes_closed:
            return ObservationState.NORMAL_VIEW

        gaze_values = (
            observation.left_gaze_x,
            observation.right_gaze_x,
            observation.left_gaze_y,
            observation.right_gaze_y,
        )
        if any(
            value is None or not math.isfinite(value) or abs(value) > 1.25
            for value in gaze_values
        ):
            return ObservationState.LOW_CONFIDENCE
        if (
            abs(observation.left_gaze_x - observation.right_gaze_x)
            > self.max_horizontal_gaze_disagreement
            or abs(observation.left_gaze_y - observation.right_gaze_y)
            > self.max_vertical_gaze_disagreement
        ):
            return ObservationState.LOW_CONFIDENCE
        return ObservationState.NORMAL_VIEW
