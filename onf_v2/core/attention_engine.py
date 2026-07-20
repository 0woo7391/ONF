from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .calibration import CalibrationManager, CalibrationProgress
from .focus_policy import FocusPolicy
from .models import (
    CalibrationProfile,
    CalibrationStatus,
    FocusDecision,
    FrameObservation,
    MODE_THRESHOLDS,
    Mode,
    ObservationState,
    RelativeMetrics,
)
from .quality_gate import QualityGate
from .temporal_filter import TemporalFilter


@dataclass
class AttentionEngine:
    mode: Mode = Mode.NORMAL
    calibration: CalibrationManager = field(default_factory=CalibrationManager)
    writing_calibration: CalibrationManager = field(default_factory=CalibrationManager)
    quality_gate: QualityGate = field(default_factory=QualityGate)
    filter: TemporalFilter = field(default_factory=TemporalFilter)
    writing_filter: TemporalFilter = field(default_factory=TemporalFilter)
    policy: FocusPolicy = field(default_factory=FocusPolicy)
    work_mode: str = "screen"
    active_calibration_target: str = "screen"
    last_matched_profile: str = "screen"
    last_calibration_progress: Optional[CalibrationProgress] = None
    profile_switch_margin: float = 0.35
    profile_switch_seconds: float = 0.45
    profile_switch_candidate: Optional[str] = None
    profile_switch_started_at: Optional[float] = None

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
        self.quality_gate.mode = mode
        self.policy.mode = mode
        self._clear_profile_switch_candidate()

    def set_work_mode(self, work_mode: str) -> None:
        normalized = (
            work_mode if work_mode in {"screen", "screen_writing"} else "screen"
        )
        if normalized == self.work_mode:
            return
        self.work_mode = normalized
        self.last_matched_profile = "screen"
        self.reset_runtime_state()

    def start_calibration(self, timestamp: float, target: str = "screen") -> None:
        self.active_calibration_target = (
            target if target in {"screen", "writing"} else "screen"
        )
        self._active_calibration.start(timestamp)
        self.reset_runtime_state()

    def clear_calibrations(self) -> None:
        self.calibration.reset()
        self.writing_calibration.reset()
        self.active_calibration_target = "screen"
        self.last_matched_profile = "screen"
        self.last_calibration_progress = None
        self.reset_runtime_state()

    def reset_runtime_state(self) -> None:
        self.filter.reset()
        self.writing_filter.reset()
        self.policy.reset()
        self.profile_switch_candidate = None
        self.profile_switch_started_at = None

    @property
    def calibrated(self) -> bool:
        return self.calibration.ready

    @property
    def writing_calibrated(self) -> bool:
        return self.writing_calibration.ready

    @property
    def ready_for_session(self) -> bool:
        if not self.calibrated:
            return False
        return self.work_mode != "screen_writing" or self.writing_calibrated

    @property
    def _active_calibration(self) -> CalibrationManager:
        if self.active_calibration_target == "writing":
            return self.writing_calibration
        return self.calibration

    @property
    def guide_profile(self) -> Optional[CalibrationProfile]:
        if self._active_calibration.status == CalibrationStatus.COLLECTING:
            return self._active_calibration.profile
        if self.work_mode == "screen_writing" and self.last_matched_profile == "writing":
            return self.writing_calibration.profile
        return self.calibration.profile

    def update_calibration(self, observation: FrameObservation) -> CalibrationProgress:
        progress = self._active_calibration.update(observation)
        self.last_calibration_progress = progress
        if progress.status == CalibrationStatus.READY:
            self.reset_runtime_state()
        return progress

    def decide(self, observation: FrameObservation, manual_break: bool = False) -> FocusDecision:
        quality_state = self.quality_gate.evaluate(observation)
        confidence = observation.tracking_confidence
        if quality_state != ObservationState.NORMAL_VIEW:
            self._clear_profile_switch_candidate()
            return self.policy.decide(
                quality_state,
                observation.timestamp,
                manual_break=manual_break,
                confidence=confidence,
            )

        if not self.ready_for_session:
            self._clear_profile_switch_candidate()
            return self.policy.decide(
                ObservationState.NOT_CALIBRATED,
                observation.timestamp,
                manual_break=manual_break,
                confidence=confidence,
            )

        candidates = [("screen", self.calibration.normalize(observation))]
        if self.work_mode == "screen_writing" and self.writing_calibrated:
            candidates.append(
                ("writing", self.writing_calibration.normalize(observation))
            )
        valid_candidates = [item for item in candidates if item[1] is not None]
        if not valid_candidates:
            relative = None
            profile_distances: Dict[str, float] = {}
        else:
            matched_profile, relative, profile_distances = self._select_profile(
                valid_candidates,
                observation.timestamp,
            )
            relative = self._filtered_metrics(matched_profile, relative)
        if relative is None:
            self._clear_profile_switch_candidate()
            return self.policy.decide(
                ObservationState.LOW_CONFIDENCE,
                observation.timestamp,
                manual_break=manual_break,
                confidence=confidence,
            )

        raw = self.policy.classify_metrics(relative)
        decision = self.policy.decide(
            raw,
            observation.timestamp,
            manual_break=manual_break,
            metrics=relative,
            confidence=confidence,
        )
        decision.matched_profile = self.last_matched_profile
        decision.profile_distances = profile_distances
        decision.profile_switch_candidate = self.profile_switch_candidate
        return decision

    def _filtered_metrics(
        self,
        profile: str,
        metrics: Optional[RelativeMetrics],
    ) -> Optional[RelativeMetrics]:
        if metrics is None:
            return None
        if profile == "writing":
            return self.writing_filter.update(metrics)
        return self.filter.update(metrics)

    def _select_profile(
        self,
        candidates: List[Tuple[str, RelativeMetrics]],
        timestamp: float,
    ) -> Tuple[str, RelativeMetrics, Dict[str, float]]:
        metrics_by_profile = dict(candidates)
        distances = {
            profile: self._profile_distance(metrics)
            for profile, metrics in candidates
        }
        best_profile = min(distances, key=distances.get)
        current_profile = self.last_matched_profile
        if current_profile not in metrics_by_profile:
            current_profile = best_profile
            self.last_matched_profile = best_profile

        if best_profile == current_profile:
            self._clear_profile_switch_candidate()
        else:
            improvement = distances[current_profile] - distances[best_profile]
            if improvement < self.profile_switch_margin:
                self._clear_profile_switch_candidate()
            elif self.profile_switch_candidate != best_profile:
                self.profile_switch_candidate = best_profile
                self.profile_switch_started_at = timestamp
            elif (
                self.profile_switch_started_at is not None
                and timestamp - self.profile_switch_started_at
                >= self.profile_switch_seconds
            ):
                current_profile = best_profile
                self.last_matched_profile = best_profile
                self._clear_profile_switch_candidate()

        return current_profile, metrics_by_profile[current_profile], distances

    def _clear_profile_switch_candidate(self) -> None:
        self.profile_switch_candidate = None
        self.profile_switch_started_at = None

    def _profile_distance(self, metrics: RelativeMetrics) -> float:
        thresholds = MODE_THRESHOLDS[self.mode]
        return (
            abs(metrics.yaw_delta_deg) / max(thresholds.yaw_enter_deg, 1e-6)
            + abs(metrics.pitch_delta_deg)
            / max(thresholds.pitch_down_enter_deg, 1e-6)
            + abs(metrics.roll_delta_deg) / max(thresholds.roll_enter_deg, 1e-6)
            + abs(metrics.gaze_x_delta) / max(thresholds.gaze_x_enter, 1e-6)
            + abs(metrics.gaze_y_delta) / max(thresholds.gaze_y_enter, 1e-6)
            + metrics.face_scale_delta / max(thresholds.max_face_scale_delta, 1e-6)
        )
