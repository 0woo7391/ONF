from __future__ import annotations

from dataclasses import dataclass

from .models import FrameObservation, MODE_THRESHOLDS, Mode, ObservationState


@dataclass
class QualityGate:
    mode: Mode = Mode.NORMAL
    max_horizontal_gaze_disagreement: float = 0.28
    max_vertical_gaze_disagreement: float = 0.35
    visibly_open_eye_ratio: float = 0.08

    def evaluate(self, observation: FrameObservation) -> ObservationState:
        thresholds = MODE_THRESHOLDS[self.mode]
        if not observation.camera_ok:
            return ObservationState.CAMERA_ERROR
        if observation.error:
            return ObservationState.PROCESSING_ERROR
        if not observation.face_detected:
            return ObservationState.NO_FACE
        if observation.face_count > 1:
            return ObservationState.MULTIPLE_FACES
        if observation.face_scale is None or observation.face_scale < thresholds.min_face_scale:
            return ObservationState.LOW_CONFIDENCE
        if observation.face_bbox:
            x0, y0, x1, y1 = observation.face_bbox
            if x0 < 0.01 or y0 < 0.01 or x1 > 0.99 or y1 > 0.99:
                return ObservationState.LOW_CONFIDENCE
        if observation.tracking_confidence < thresholds.min_confidence:
            return ObservationState.LOW_CONFIDENCE
        gaze_values = (
            observation.left_gaze_x,
            observation.right_gaze_x,
            observation.left_gaze_y,
            observation.right_gaze_y,
        )
        if any(value is not None for value in gaze_values):
            if any(value is None for value in gaze_values):
                return ObservationState.LOW_CONFIDENCE
            eyes_visibly_open = (
                observation.left_eye_open_ratio is not None
                and observation.right_eye_open_ratio is not None
                and observation.left_eye_open_ratio > self.visibly_open_eye_ratio
                and observation.right_eye_open_ratio > self.visibly_open_eye_ratio
            )
            if eyes_visibly_open:
                horizontal_difference = abs(
                    observation.left_gaze_x - observation.right_gaze_x
                )
                vertical_difference = abs(
                    observation.left_gaze_y - observation.right_gaze_y
                )
                if (
                    horizontal_difference > self.max_horizontal_gaze_disagreement
                    or vertical_difference > self.max_vertical_gaze_disagreement
                ):
                    return ObservationState.LOW_CONFIDENCE
        return ObservationState.NORMAL_VIEW
