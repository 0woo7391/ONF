from __future__ import annotations

from dataclasses import dataclass

from .models import FrameObservation, MODE_THRESHOLDS, Mode, ObservationState


@dataclass
class QualityGate:
    mode: Mode = Mode.NORMAL

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
        return ObservationState.NORMAL_VIEW

