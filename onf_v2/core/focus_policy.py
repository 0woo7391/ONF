from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import (
    EffectiveState,
    FocusDecision,
    MODE_THRESHOLDS,
    Mode,
    ObservationState,
    RelativeMetrics,
)


RAW_REASON = {
    ObservationState.NORMAL_VIEW: "Screen attention is stable",
    ObservationState.GAZE_AWAY: "Gaze moved outside the calibrated work area",
    ObservationState.HEAD_SIDE: "Head direction moved sideways",
    ObservationState.HEAD_DOWN: "Head moved downward",
    ObservationState.HEAD_UP: "Head moved upward",
    ObservationState.EYES_CLOSED: "Eyes are closed beyond blink tolerance",
    ObservationState.NO_FACE: "No face detected",
    ObservationState.MULTIPLE_FACES: "Multiple faces detected",
    ObservationState.LOW_CONFIDENCE: "Tracking confidence is low",
    ObservationState.PROCESSING_ERROR: "Face analysis failed",
    ObservationState.CAMERA_ERROR: "Camera frame is unavailable",
    ObservationState.NOT_CALIBRATED: "Calibration is required",
}


@dataclass
class StateStabilizer:
    min_focus_return_seconds: float = 0.35
    min_gaze_away_seconds: float = 0.70
    min_head_away_seconds: float = 0.70
    min_head_down_seconds: float = 1.00
    min_eyes_closed_seconds: float = 1.00
    min_no_face_seconds: float = 1.00
    current: ObservationState = ObservationState.NOT_CALIBRATED
    candidate: Optional[ObservationState] = None
    candidate_started_at: Optional[float] = None
    current_started_at: Optional[float] = None

    def reset(self) -> None:
        self.current = ObservationState.NOT_CALIBRATED
        self.candidate = None
        self.candidate_started_at = None
        self.current_started_at = None

    def update(self, raw: ObservationState, timestamp: float) -> ObservationState:
        if self.current_started_at is None:
            immediate_states = {
                ObservationState.NORMAL_VIEW,
                ObservationState.NOT_CALIBRATED,
                ObservationState.CAMERA_ERROR,
                ObservationState.PROCESSING_ERROR,
                ObservationState.LOW_CONFIDENCE,
                ObservationState.MULTIPLE_FACES,
            }
            if raw in immediate_states:
                self.current = raw
                self.candidate = None
                self.candidate_started_at = None
            else:
                self.current = ObservationState.LOW_CONFIDENCE
                self.candidate = raw
                self.candidate_started_at = timestamp
            self.current_started_at = timestamp
            return self.current

        if raw == self.current:
            self.candidate = None
            self.candidate_started_at = None
            return self.current

        if self.candidate != raw:
            self.candidate = raw
            self.candidate_started_at = timestamp
            return self.current

        candidate_started_at = (
            timestamp if self.candidate_started_at is None else self.candidate_started_at
        )
        elapsed = timestamp - candidate_started_at
        if elapsed >= self._required_duration(raw):
            self.current = raw
            self.current_started_at = timestamp
            self.candidate = None
            self.candidate_started_at = None
        return self.current

    def _required_duration(self, raw: ObservationState) -> float:
        if raw == ObservationState.NORMAL_VIEW:
            return self.min_focus_return_seconds
        if raw == ObservationState.GAZE_AWAY:
            return self.min_gaze_away_seconds
        if raw == ObservationState.EYES_CLOSED:
            return self.min_eyes_closed_seconds
        if raw == ObservationState.NO_FACE:
            return self.min_no_face_seconds
        if raw in (ObservationState.HEAD_DOWN, ObservationState.HEAD_UP):
            return self.min_head_down_seconds
        if raw == ObservationState.HEAD_SIDE:
            return self.min_head_away_seconds
        return 0.0


@dataclass
class FocusPolicy:
    mode: Mode = Mode.NORMAL
    absence_to_break_seconds: float = 5 * 60
    stabilizer: StateStabilizer = field(default_factory=StateStabilizer)
    no_face_started_at: Optional[float] = None

    def reset(self) -> None:
        self.stabilizer.reset()
        self.no_face_started_at = None

    def classify_metrics(self, metrics: RelativeMetrics) -> ObservationState:
        thresholds = MODE_THRESHOLDS[self.mode]
        current = self.stabilizer.current
        if metrics.confidence < thresholds.min_confidence:
            return ObservationState.LOW_CONFIDENCE
        if metrics.face_scale_delta > thresholds.max_face_scale_delta:
            return ObservationState.LOW_CONFIDENCE
        if (
            metrics.left_eye_open_norm < thresholds.eye_closed_ratio
            and metrics.right_eye_open_norm < thresholds.eye_closed_ratio
        ):
            return ObservationState.EYES_CLOSED
        yaw_limit = (
            thresholds.yaw_exit_deg
            if current == ObservationState.HEAD_SIDE
            else thresholds.yaw_enter_deg
        )
        roll_limit = (
            thresholds.roll_exit_deg
            if current == ObservationState.HEAD_SIDE
            else thresholds.roll_enter_deg
        )
        pitch_down_limit = (
            thresholds.pitch_down_exit_deg
            if current == ObservationState.HEAD_DOWN
            else thresholds.pitch_down_enter_deg
        )
        pitch_up_limit = (
            thresholds.pitch_up_exit_deg
            if current == ObservationState.HEAD_UP
            else thresholds.pitch_up_enter_deg
        )
        gaze_x_limit = (
            thresholds.gaze_x_exit
            if current == ObservationState.GAZE_AWAY
            else thresholds.gaze_x_enter
        )
        gaze_y_limit = (
            thresholds.gaze_y_exit
            if current == ObservationState.GAZE_AWAY
            else thresholds.gaze_y_enter
        )
        if abs(metrics.yaw_delta_deg) > yaw_limit:
            return ObservationState.HEAD_SIDE
        if metrics.pitch_delta_deg > pitch_down_limit:
            return ObservationState.HEAD_DOWN
        if metrics.pitch_delta_deg < -pitch_up_limit:
            return ObservationState.HEAD_UP
        if abs(metrics.roll_delta_deg) > roll_limit:
            return ObservationState.HEAD_SIDE
        if (
            abs(metrics.gaze_x_delta) > gaze_x_limit
            or abs(metrics.gaze_y_delta) > gaze_y_limit
        ):
            return ObservationState.GAZE_AWAY
        return ObservationState.NORMAL_VIEW

    def decide(
        self,
        raw_state: ObservationState,
        timestamp: float,
        manual_break: bool = False,
        metrics: Optional[RelativeMetrics] = None,
        confidence: float = 0.0,
    ) -> FocusDecision:
        confirmed = self.stabilizer.update(raw_state, timestamp)
        effective = self._to_effective(confirmed, timestamp, manual_break)
        duration = 0.0
        if self.stabilizer.current_started_at is not None:
            duration = timestamp - self.stabilizer.current_started_at
        return FocusDecision(
            timestamp=timestamp,
            raw_state=confirmed,
            effective_state=effective,
            reason=RAW_REASON.get(confirmed, confirmed.value),
            confidence=confidence,
            duration=max(0.0, duration),
            metrics=metrics,
        )

    def _to_effective(
        self, raw_state: ObservationState, timestamp: float, manual_break: bool
    ) -> EffectiveState:
        if manual_break:
            self.no_face_started_at = None
            return EffectiveState.BREAK

        if raw_state == ObservationState.NORMAL_VIEW:
            self.no_face_started_at = None
            return EffectiveState.FOCUS
        if raw_state == ObservationState.NO_FACE:
            if self.no_face_started_at is None:
                self.no_face_started_at = timestamp
            if timestamp - self.no_face_started_at >= self.absence_to_break_seconds:
                return EffectiveState.BREAK
            return EffectiveState.ABSENT_PENDING
        self.no_face_started_at = None
        if raw_state in (
            ObservationState.GAZE_AWAY,
            ObservationState.HEAD_SIDE,
            ObservationState.HEAD_DOWN,
            ObservationState.HEAD_UP,
            ObservationState.EYES_CLOSED,
        ):
            return EffectiveState.NON_FOCUS
        return EffectiveState.UNSCORED
