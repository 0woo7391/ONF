from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
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
    Thresholds,
)
from .quality_gate import QualityGate
from .screen_gaze import (
    GazeValidationRegion, ScreenGazeContext, ScreenGazeMapping,
    fit_screen_gaze, validate_screen_gaze,
)
from .temporal_filter import TemporalFilter


@dataclass
class AttentionEngine:
    mode: Mode = Mode.NORMAL
    calibration: CalibrationManager = field(
        default_factory=lambda: CalibrationManager(
            duration_seconds=5.0,
            max_yaw_stdev=7.0,
            max_pitch_stdev=7.0,
            guided_targets=("center", "up", "down", "left", "right"),
            samples_per_target=12,
            natural_samples=30,
            max_guided_seconds=45.0,
            target_settle_seconds=2.0,
            target_valid_seconds=2.0,
            max_target_seconds=12.0,
            instruction="표시된 원을 눈으로 따라가며 바라봐 주세요.",
            movement_failure_message=(
                "화면 영역 밖의 움직임이 너무 많았습니다. 화면을 보며 다시 설정하세요."
            ),
        )
    )
    writing_calibration: CalibrationManager = field(
        default_factory=lambda: CalibrationManager(
            duration_seconds=12.0,
            target_sample_rate=10.0,
            max_yaw_stdev=16.0,
            max_pitch_stdev=20.0,
            guided_targets=(),
            progress_by_valid_samples=True,
            max_collection_seconds=30.0,
            enforce_stability=False,
            instruction="종이나 태블릿에 평소처럼 문장 두 줄을 작성하세요.",
        )
    )
    gaze_validation: CalibrationManager = field(
        default_factory=lambda: CalibrationManager(
            guided_targets=("center", "up", "down", "left", "right"),
            samples_per_target=12,
            target_settle_seconds=2.0,
            target_valid_seconds=2.0,
            max_target_seconds=12.0,
            max_guided_seconds=45.0,
            require_display_ack=True,
            collection_only=True,
        )
    )
    screen_gaze_mapping: Optional[ScreenGazeMapping] = None
    gaze_validation_result: Tuple[GazeValidationRegion, ...] = ()
    gaze_mapping_message: str = "화면 자세 설정 후 시선을 검증할 수 있습니다."
    validating_gaze: bool = False
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
        self.validating_gaze = False
        self.gaze_validation.cancel()
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
        self.clear_screen_gaze()
        self.gaze_validation.reset()
        self.validating_gaze = False
        self.reset_runtime_state()

    def clear_screen_gaze(self) -> None:
        self.screen_gaze_mapping = None
        self.gaze_validation_result = ()
        self.gaze_mapping_message = "화면 자세를 다시 설정한 뒤 시선을 검증하세요."

    @property
    def screen_collection(self) -> CalibrationManager:
        return self.gaze_validation if self.validating_gaze else self.calibration

    def start_gaze_validation(self, timestamp: float) -> bool:
        if self.screen_gaze_mapping is None:
            return False
        self.validating_gaze = True
        self.gaze_validation.start(timestamp)
        self.reset_runtime_state()
        return True

    def confirm_screen_target(
        self, timestamp: float, index: int, key: str,
        position: Optional[Tuple[float, float]] = None,
        context: Optional[ScreenGazeContext] = None,
    ) -> bool:
        manager = self.screen_collection
        if (
            manager.status != CalibrationStatus.COLLECTING
            or manager.started_at is None or not math.isfinite(timestamp) or timestamp < manager.started_at
            or index != manager.target_index or key != manager.current_target
        ):
            return False
        if context is not None:
            if manager.display_context is not None and context != manager.display_context:
                manager.mapping_context_valid = False
            if key in manager.target_positions and position != manager.target_positions[key]:
                manager.mapping_context_valid = False
        if not manager.confirm_target_displayed(timestamp, index, key):
            return False
        if position is not None and context is not None:
            manager.display_context = manager.display_context or context
            manager.target_positions[key] = position
        return True

    def update_gaze_validation(self, observation: FrameObservation) -> CalibrationProgress:
        progress = self.gaze_validation.update(observation)
        if progress.status == CalibrationStatus.READY:
            manager = self.gaze_validation
            try:
                if not manager.mapping_context_valid or self.screen_gaze_mapping is None:
                    raise ValueError("Validation configuration changed")
                self.gaze_validation_result = validate_screen_gaze(
                    self.screen_gaze_mapping, manager.display_context,
                    manager.samples_by_target, manager.target_positions,
                    manager.attempted_samples_by_target,
                )
                self.gaze_mapping_message = "검증 결과입니다. 집중 판정에는 아직 사용하지 않습니다."
            except ValueError:
                self.gaze_mapping_message = "검증 환경이 바뀌었습니다. 화면 자세를 다시 설정하세요."
                progress.status = CalibrationStatus.FAILED
                progress.message = self.gaze_mapping_message
                manager.status = CalibrationStatus.FAILED
                manager.failure_reason = progress.message
                manager.failed_targets = manager.guided_targets
        return progress

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
            if self.active_calibration_target == "screen":
                manager = self.calibration
                try:
                    if manager.display_context is None or not manager.mapping_context_valid:
                        raise ValueError("Actual target context is missing or changed")
                    candidate = fit_screen_gaze(
                        manager.display_context, manager.samples_by_target, manager.target_positions
                    )
                except ValueError:
                    previous = self.screen_gaze_mapping
                    if previous is not None and manager.display_context is not None and previous.context != manager.display_context:
                        self.clear_screen_gaze()
                    self.gaze_mapping_message = (
                        "새 시선 매핑을 만들지 못했습니다. 기존 검증 후보를 유지합니다."
                        if self.screen_gaze_mapping is not None else
                        "눈의 방향 변화나 표적 정보를 확인하지 못했습니다. 화면 자세를 다시 설정하세요."
                    )
                else:
                    self.screen_gaze_mapping = candidate
                    self.gaze_validation_result = ()
                    self.gaze_mapping_message = "새 시선 매핑 후보입니다. 별도 검증이 필요합니다."
        return progress

    def decide(self, observation: FrameObservation, manual_break: bool = False) -> FocusDecision:
        eyes_closed = self._eyes_closed(observation)
        quality_state = self.quality_gate.evaluate(observation, eyes_closed=eyes_closed)
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

        if eyes_closed:
            self._clear_profile_switch_candidate()
            self.filter.reset()
            self.writing_filter.reset()
            return self.policy.decide(
                ObservationState.EYES_CLOSED,
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

        raw = self.policy.classify_metrics(
            relative,
            thresholds=self._profile_thresholds(matched_profile),
        )
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

    def _eyes_closed(self, observation: FrameObservation) -> bool:
        left, right = observation.left_eye_open_ratio, observation.right_eye_open_ratio
        if (
            left is None or right is None
            or not math.isfinite(left) or not math.isfinite(right)
        ):
            return False
        profiles = [self.calibration.profile]
        if self.work_mode == "screen_writing":
            profiles.append(self.writing_calibration.profile)
        valid_profiles = [
            profile for profile in profiles
            if profile is not None
            and math.isfinite(profile.left_eye_open_baseline)
            and math.isfinite(profile.right_eye_open_baseline)
            and profile.left_eye_open_baseline > 0
            and profile.right_eye_open_baseline > 0
        ]
        if not valid_profiles:
            return False
        limit = MODE_THRESHOLDS[self.mode].eye_closed_ratio
        return (
            left < min(profile.left_eye_open_baseline for profile in valid_profiles) * limit
            and right < min(profile.right_eye_open_baseline for profile in valid_profiles) * limit
        )

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
            profile: self._profile_distance(profile, metrics)
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

    def _profile_distance(
        self,
        _profile_name: str,
        metrics: RelativeMetrics,
    ) -> float:
        # Profile selection stays center-based so a naturally wider writing
        # range does not absorb nearby screen observations.
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

    def _profile_thresholds(self, profile_name: str) -> Thresholds:
        base = MODE_THRESHOLDS[self.mode]
        profile = (
            self.writing_calibration.profile
            if profile_name == "writing"
            else self.calibration.profile
        )
        if profile is None or not (profile.feature_spread or profile.target_centers):
            return base

        spread = profile.feature_spread
        yaw_enter = self._expanded_limit(
            base.yaw_enter_deg, spread.get("yaw", 0.0), 3.0, 1.6
        )
        pitch_down_enter = self._expanded_limit(
            base.pitch_down_enter_deg, spread.get("pitch", 0.0), 3.0, 1.8
        )
        pitch_up_enter = self._expanded_limit(
            base.pitch_up_enter_deg, spread.get("pitch", 0.0), 3.0, 1.8
        )
        roll_enter = self._expanded_limit(
            base.roll_enter_deg, spread.get("roll", 0.0), 3.0, 1.5
        )
        gaze_x_enter = self._expanded_limit(
            base.gaze_x_enter, spread.get("gaze_x", 0.0), 3.0, 1.5
        )
        gaze_y_enter = self._expanded_limit(
            base.gaze_y_enter, spread.get("gaze_y", 0.0), 3.0, 1.5
        )
        yaw_exit = self._exit_limit(
            base.yaw_exit_deg, yaw_enter, spread.get("yaw", 0.0)
        )
        pitch_down_exit = self._exit_limit(
            base.pitch_down_exit_deg, pitch_down_enter, spread.get("pitch", 0.0)
        )
        pitch_up_exit = self._exit_limit(
            base.pitch_up_exit_deg, pitch_up_enter, spread.get("pitch", 0.0)
        )
        gaze_x_exit = self._exit_limit(
            base.gaze_x_exit, gaze_x_enter, spread.get("gaze_x", 0.0)
        )
        gaze_y_exit = self._exit_limit(
            base.gaze_y_exit, gaze_y_enter, spread.get("gaze_y", 0.0)
        )
        targets = profile.target_centers
        center = targets.get("center")
        if profile_name == "screen" and center is not None:
            left, right = targets.get("left"), targets.get("right")
            if left is not None and right is not None:
                yaw_reach = max(
                    abs(left["yaw"] - center["yaw"]),
                    abs(right["yaw"] - center["yaw"]),
                )
                gaze_x_reach = max(
                    abs(left["gaze_x"] - center["gaze_x"]),
                    abs(right["gaze_x"] - center["gaze_x"]),
                )
                yaw_enter = max(yaw_enter, yaw_reach + 2.0)
                yaw_exit = max(base.yaw_exit_deg, yaw_reach)
                gaze_x_enter = max(gaze_x_enter, gaze_x_reach + 0.04)
                gaze_x_exit = max(base.gaze_x_exit, gaze_x_reach)

            up, down = targets.get("up"), targets.get("down")
            if up is not None and down is not None:
                pitch_up_reach = abs(up["pitch"] - center["pitch"])
                pitch_down_reach = abs(down["pitch"] - center["pitch"])
                gaze_y_reach = max(
                    abs(up["gaze_y"] - center["gaze_y"]),
                    abs(down["gaze_y"] - center["gaze_y"]),
                )
                pitch_up_enter = max(pitch_up_enter, pitch_up_reach + 2.0)
                pitch_up_exit = max(base.pitch_up_exit_deg, pitch_up_reach)
                pitch_down_enter = max(pitch_down_enter, pitch_down_reach + 2.0)
                pitch_down_exit = max(base.pitch_down_exit_deg, pitch_down_reach)
                gaze_y_enter = max(gaze_y_enter, gaze_y_reach + 0.02)
                gaze_y_exit = max(base.gaze_y_exit, gaze_y_reach)
        scale_spread = spread.get("face_scale", 0.0) / max(
            profile.face_scale_center, 1e-6
        )
        face_scale_limit = self._expanded_limit(
            base.max_face_scale_delta, scale_spread, 3.0, 1.4
        )

        return replace(
            base,
            yaw_enter_deg=yaw_enter,
            yaw_exit_deg=yaw_exit,
            pitch_down_enter_deg=pitch_down_enter,
            pitch_down_exit_deg=pitch_down_exit,
            pitch_up_enter_deg=pitch_up_enter,
            pitch_up_exit_deg=pitch_up_exit,
            roll_enter_deg=roll_enter,
            roll_exit_deg=self._exit_limit(
                base.roll_exit_deg, roll_enter, spread.get("roll", 0.0)
            ),
            gaze_x_enter=gaze_x_enter,
            gaze_x_exit=gaze_x_exit,
            gaze_y_enter=gaze_y_enter,
            gaze_y_exit=gaze_y_exit,
            max_face_scale_delta=face_scale_limit,
        )

    @staticmethod
    def _expanded_limit(
        base: float,
        spread: float,
        spread_multiplier: float,
        maximum_multiplier: float,
    ) -> float:
        learned = max(0.0, spread) * spread_multiplier
        return max(base, min(base * maximum_multiplier, learned))

    @staticmethod
    def _exit_limit(base: float, enter: float, spread: float) -> float:
        learned = max(0.0, spread) * 2.0
        return min(enter * 0.85, max(base, learned))
