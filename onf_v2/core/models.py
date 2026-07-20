from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AppState(str, Enum):
    PREVIEW = "preview"
    CALIBRATING = "calibrating"
    READY = "ready"
    RUNNING = "running"
    BREAK = "break"
    RESULT = "result"
    ERROR = "error"


class Mode(str, Enum):
    LENIENT = "lenient"
    NORMAL = "normal"
    STRICT = "strict"


class ObservationState(str, Enum):
    NORMAL_VIEW = "normal_view"
    GAZE_AWAY = "gaze_away"
    HEAD_SIDE = "head_side"
    HEAD_DOWN = "head_down"
    HEAD_UP = "head_up"
    EYES_CLOSED = "eyes_closed"
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    LOW_CONFIDENCE = "low_confidence"
    PROCESSING_ERROR = "processing_error"
    CAMERA_ERROR = "camera_error"
    NOT_CALIBRATED = "not_calibrated"


class EffectiveState(str, Enum):
    FOCUS = "focus"
    NON_FOCUS = "non_focus"
    BREAK = "break"
    UNSCORED = "unscored"
    ABSENT_PENDING = "absent_pending"


class CalibrationStatus(str, Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class Thresholds:
    yaw_enter_deg: float
    yaw_exit_deg: float
    pitch_down_enter_deg: float
    pitch_down_exit_deg: float
    pitch_up_enter_deg: float
    pitch_up_exit_deg: float
    roll_enter_deg: float
    roll_exit_deg: float
    gaze_x_enter: float
    gaze_x_exit: float
    gaze_y_enter: float
    gaze_y_exit: float
    eye_closed_ratio: float
    min_confidence: float
    min_face_scale: float
    max_face_scale_delta: float


MODE_THRESHOLDS: Dict[Mode, Thresholds] = {
    Mode.LENIENT: Thresholds(
        yaw_enter_deg=22.0,
        yaw_exit_deg=14.0,
        pitch_down_enter_deg=22.0,
        pitch_down_exit_deg=14.0,
        pitch_up_enter_deg=18.0,
        pitch_up_exit_deg=12.0,
        roll_enter_deg=24.0,
        roll_exit_deg=16.0,
        gaze_x_enter=0.26,
        gaze_x_exit=0.18,
        gaze_y_enter=0.26,
        gaze_y_exit=0.18,
        eye_closed_ratio=0.45,
        min_confidence=0.55,
        min_face_scale=0.12,
        max_face_scale_delta=0.55,
    ),
    Mode.NORMAL: Thresholds(
        yaw_enter_deg=16.0,
        yaw_exit_deg=10.0,
        pitch_down_enter_deg=16.0,
        pitch_down_exit_deg=10.0,
        pitch_up_enter_deg=13.0,
        pitch_up_exit_deg=8.0,
        roll_enter_deg=20.0,
        roll_exit_deg=13.0,
        gaze_x_enter=0.20,
        gaze_x_exit=0.13,
        gaze_y_enter=0.22,
        gaze_y_exit=0.15,
        eye_closed_ratio=0.45,
        min_confidence=0.60,
        min_face_scale=0.14,
        max_face_scale_delta=0.45,
    ),
    Mode.STRICT: Thresholds(
        yaw_enter_deg=11.0,
        yaw_exit_deg=7.0,
        pitch_down_enter_deg=11.0,
        pitch_down_exit_deg=7.0,
        pitch_up_enter_deg=10.0,
        pitch_up_exit_deg=6.0,
        roll_enter_deg=15.0,
        roll_exit_deg=10.0,
        gaze_x_enter=0.14,
        gaze_x_exit=0.09,
        gaze_y_enter=0.16,
        gaze_y_exit=0.10,
        eye_closed_ratio=0.50,
        min_confidence=0.65,
        min_face_scale=0.16,
        max_face_scale_delta=0.35,
    ),
}


@dataclass
class FrameObservation:
    timestamp: float
    camera_ok: bool = True
    face_detected: bool = False
    face_count: int = 0
    tracking_confidence: float = 0.0
    face_bbox: Optional[Tuple[float, float, float, float]] = None
    face_scale: Optional[float] = None
    face_center: Optional[Tuple[float, float]] = None
    head_yaw_deg: Optional[float] = None
    head_pitch_deg: Optional[float] = None
    head_roll_deg: Optional[float] = None
    left_gaze_x: Optional[float] = None
    right_gaze_x: Optional[float] = None
    left_gaze_y: Optional[float] = None
    right_gaze_y: Optional[float] = None
    gaze_x: Optional[float] = None
    gaze_y: Optional[float] = None
    left_eye_open_ratio: Optional[float] = None
    right_eye_open_ratio: Optional[float] = None
    quality_reason: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CalibrationProfile:
    yaw_center: float
    pitch_center: float
    roll_center: float
    gaze_x_center: float
    gaze_y_center: float
    left_eye_open_baseline: float
    right_eye_open_baseline: float
    face_scale_center: float
    face_center: Tuple[float, float]
    sample_count: int
    quality_score: float
    feature_spread: Dict[str, float] = field(default_factory=dict)
    target_centers: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class RelativeMetrics:
    timestamp: float
    yaw_delta_deg: float
    pitch_delta_deg: float
    roll_delta_deg: float
    gaze_x_delta: float
    gaze_y_delta: float
    left_eye_open_norm: float
    right_eye_open_norm: float
    face_scale_delta: float
    confidence: float


@dataclass
class FocusDecision:
    timestamp: float
    raw_state: ObservationState
    effective_state: EffectiveState
    reason: str
    confidence: float = 0.0
    duration: float = 0.0
    metrics: Optional[RelativeMetrics] = None
    reasons: Dict[str, bool] = field(default_factory=dict)
    matched_profile: Optional[str] = None
    profile_distances: Dict[str, float] = field(default_factory=dict)
    profile_switch_candidate: Optional[str] = None


@dataclass
class AttentionEvent:
    type: str
    started_at: float
    ended_at: float
    duration: float
    max_deviation: float = 0.0


@dataclass
class SessionSummary:
    started_at_wall: str
    ended_at_wall: str
    focus_seconds: float
    non_focus_seconds: float
    break_seconds: float
    unscored_seconds: float
    absent_pending_seconds: float
    focus_ratio: float
    coverage_ratio: float
    longest_focus_seconds: float
    events: List[AttentionEvent]
    session_mode: str = "free"
    pomodoro_cycles_completed: int = 0
    pomodoro_cycles_planned: int = 0
