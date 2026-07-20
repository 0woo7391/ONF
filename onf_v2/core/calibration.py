from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import CalibrationProfile, CalibrationStatus, FrameObservation


@dataclass
class CalibrationProgress:
    status: CalibrationStatus
    progress: float
    valid_samples: int
    target_samples: int
    quality_score: float = 0.0
    message: str = ""
    profile: Optional[CalibrationProfile] = None
    target_key: str = ""
    target_index: int = 0
    total_targets: int = 0
    target_progress: float = 0.0
    stage_changed: bool = False


@dataclass
class CalibrationManager:
    duration_seconds: float = 4.0
    target_sample_rate: float = 10.0
    min_valid_ratio: float = 0.85
    max_yaw_stdev: float = 4.0
    max_pitch_stdev: float = 4.0
    instruction: str = "화면 작업 영역을 자연스럽게 바라봐 주세요."
    movement_failure_message: str = "작업 영역을 벗어난 움직임이 너무 많았습니다."
    guided_targets: Tuple[str, ...] = ()
    samples_per_target: int = 12
    natural_samples: int = 24
    max_guided_seconds: float = 30.0
    target_settle_seconds: float = 0.45
    status: CalibrationStatus = CalibrationStatus.IDLE
    started_at: Optional[float] = None
    samples: List[FrameObservation] = field(default_factory=list)
    profile: Optional[CalibrationProfile] = None
    failure_reason: str = ""
    invalid_reasons: Counter[str] = field(default_factory=Counter)
    target_index: int = 0
    target_started_at: Optional[float] = None
    samples_by_target: Dict[str, List[FrameObservation]] = field(default_factory=dict)

    def start(self, timestamp: float) -> None:
        self.status = CalibrationStatus.COLLECTING
        self.started_at = timestamp
        self.samples.clear()
        self.profile = None
        self.failure_reason = ""
        self.invalid_reasons.clear()
        self.target_index = 0
        self.target_started_at = timestamp
        self.samples_by_target = {target: [] for target in self.guided_targets}

    def reset(self) -> None:
        self.status = CalibrationStatus.IDLE
        self.started_at = None
        self.samples.clear()
        self.profile = None
        self.failure_reason = ""
        self.invalid_reasons.clear()
        self.target_index = 0
        self.target_started_at = None
        self.samples_by_target.clear()

    @property
    def ready(self) -> bool:
        return self.status == CalibrationStatus.READY and self.profile is not None

    def update(self, observation: FrameObservation) -> CalibrationProgress:
        if self.status != CalibrationStatus.COLLECTING or self.started_at is None:
            message = ""
            if self.status == CalibrationStatus.FAILED:
                message = self.failure_reason
            elif self.ready:
                message = "기준 자세가 저장되었습니다."
            return CalibrationProgress(
                status=self.status,
                progress=1.0 if self.ready else 0.0,
                valid_samples=len(self.samples),
                target_samples=1,
                message=message,
                profile=self.profile,
            )

        elapsed = max(0.0, observation.timestamp - self.started_at)
        if self.guided_targets:
            return self._update_guided(observation, elapsed)

        target_samples = max(1, int(self.duration_seconds * self.target_sample_rate))
        valid_sample, guidance = self._sample_feedback(observation)
        if valid_sample:
            self.samples.append(observation)
        else:
            self.invalid_reasons[guidance] += 1

        progress = min(1.0, elapsed / self.duration_seconds)
        if elapsed < self.duration_seconds:
            return CalibrationProgress(
                status=self.status,
                progress=progress,
                valid_samples=len(self.samples),
                target_samples=target_samples,
                message=(
                    self.instruction
                    if valid_sample
                    else guidance
                ),
            )

        profile = self._build_profile(target_samples)
        if profile is None:
            self.status = CalibrationStatus.FAILED
            return CalibrationProgress(
                status=self.status,
                progress=1.0,
                valid_samples=len(self.samples),
                target_samples=target_samples,
                message=self.failure_reason,
            )

        self.status = CalibrationStatus.READY
        self.profile = profile
        return CalibrationProgress(
            status=self.status,
            progress=1.0,
            valid_samples=len(self.samples),
            target_samples=target_samples,
            quality_score=profile.quality_score,
            message="기준 자세가 저장되었습니다.",
            profile=profile,
        )

    @property
    def current_target(self) -> str:
        if not self.guided_targets:
            return ""
        index = min(self.target_index, len(self.guided_targets) - 1)
        return self.guided_targets[index]

    def _update_guided(
        self,
        observation: FrameObservation,
        elapsed: float,
    ) -> CalibrationProgress:
        target = self.current_target
        required = self._required_samples(target)
        target_started_at = (
            self.target_started_at
            if self.target_started_at is not None
            else observation.timestamp
        )
        target_elapsed = max(0.0, observation.timestamp - target_started_at)
        if target_elapsed < self.target_settle_seconds:
            return self._guided_progress(
                message="표시가 이동했습니다. 새 위치를 자연스럽게 바라봐 주세요.",
                target=target,
                target_count=len(self.samples_by_target[target]),
                required=required,
            )
        valid_sample, guidance = self._sample_feedback(observation)
        if valid_sample:
            self.samples.append(observation)
            self.samples_by_target[target].append(observation)
        else:
            self.invalid_reasons[guidance] += 1

        stage_changed = False
        target_count = len(self.samples_by_target[target])
        if target_count >= required:
            if self.target_index + 1 < len(self.guided_targets):
                self.target_index += 1
                self.target_started_at = observation.timestamp
                target = self.current_target
                required = self._required_samples(target)
                target_count = len(self.samples_by_target[target])
                stage_changed = True
            else:
                return self._finish_guided_calibration()

        if elapsed >= self.max_guided_seconds:
            self.failure_reason = (
                self.invalid_reasons.most_common(1)[0][0]
                if self.invalid_reasons
                else "유효한 표본을 충분히 모으지 못했습니다. 안내에 따라 다시 설정하세요."
            )
            self.status = CalibrationStatus.FAILED
            return self._guided_progress(
                message=self.failure_reason,
                target=target,
                target_count=target_count,
                required=required,
                stage_changed=stage_changed,
            )

        return self._guided_progress(
            message=self.instruction if valid_sample else guidance,
            target=target,
            target_count=target_count,
            required=required,
            stage_changed=stage_changed,
        )

    def _finish_guided_calibration(self) -> CalibrationProgress:
        total_required = self._total_guided_samples()
        profile = self._build_profile(total_required)
        if profile is None:
            self.status = CalibrationStatus.FAILED
            return self._guided_progress(
                message=self.failure_reason,
                target=self.current_target,
                target_count=len(self.samples_by_target[self.current_target]),
                required=self._required_samples(self.current_target),
            )

        self.status = CalibrationStatus.READY
        self.profile = profile
        return CalibrationProgress(
            status=self.status,
            progress=1.0,
            valid_samples=len(self.samples),
            target_samples=total_required,
            quality_score=profile.quality_score,
            message="작업 영역이 저장되었습니다.",
            profile=profile,
            target_key=self.current_target,
            target_index=len(self.guided_targets) - 1,
            total_targets=len(self.guided_targets),
            target_progress=1.0,
        )

    def _guided_progress(
        self,
        message: str,
        target: str,
        target_count: int,
        required: int,
        stage_changed: bool = False,
    ) -> CalibrationProgress:
        total_required = self._total_guided_samples()
        return CalibrationProgress(
            status=self.status,
            progress=min(1.0, len(self.samples) / max(total_required, 1)),
            valid_samples=len(self.samples),
            target_samples=total_required,
            message=message,
            profile=self.profile,
            target_key=target,
            target_index=min(self.target_index, len(self.guided_targets) - 1),
            total_targets=len(self.guided_targets),
            target_progress=min(1.0, target_count / max(required, 1)),
            stage_changed=stage_changed,
        )

    def _required_samples(self, target: str) -> int:
        return self.natural_samples if target == "natural" else self.samples_per_target

    def _total_guided_samples(self) -> int:
        return sum(self._required_samples(target) for target in self.guided_targets)

    def normalize(self, observation: FrameObservation):
        from .models import RelativeMetrics

        if not self.profile:
            return None
        profile = self.profile
        if any(
            value is None
            for value in (
                observation.head_yaw_deg,
                observation.head_pitch_deg,
                observation.head_roll_deg,
                observation.gaze_x,
                observation.gaze_y,
                observation.left_eye_open_ratio,
                observation.right_eye_open_ratio,
                observation.face_scale,
            )
        ):
            return None

        left_eye = observation.left_eye_open_ratio or 0.0
        right_eye = observation.right_eye_open_ratio or 0.0
        return RelativeMetrics(
            timestamp=observation.timestamp,
            yaw_delta_deg=(observation.head_yaw_deg or 0.0) - profile.yaw_center,
            pitch_delta_deg=(observation.head_pitch_deg or 0.0) - profile.pitch_center,
            roll_delta_deg=(observation.head_roll_deg or 0.0) - profile.roll_center,
            gaze_x_delta=(observation.gaze_x or 0.0) - profile.gaze_x_center,
            gaze_y_delta=(observation.gaze_y or 0.0) - profile.gaze_y_center,
            left_eye_open_norm=left_eye / max(profile.left_eye_open_baseline, 1e-6),
            right_eye_open_norm=right_eye / max(profile.right_eye_open_baseline, 1e-6),
            face_scale_delta=abs((observation.face_scale or 0.0) - profile.face_scale_center)
            / max(profile.face_scale_center, 1e-6),
            confidence=observation.tracking_confidence,
        )

    def _sample_feedback(self, observation: FrameObservation) -> Tuple[bool, str]:
        if not observation.camera_ok:
            return False, "카메라 영상을 받지 못하고 있습니다. 카메라 연결과 장치 선택을 확인하세요."
        if observation.error:
            return False, "얼굴 분석이 일시적으로 불안정합니다. 카메라를 새로고침한 뒤 다시 시도하세요."
        if not observation.face_detected:
            return False, "얼굴을 찾지 못했습니다. 조명을 밝히고 얼굴 전체와 양쪽 눈이 보이게 해주세요."
        if observation.face_count != 1:
            return False, "여러 얼굴이 감지됐습니다. 카메라 화면에는 한 사람만 보이게 해주세요."
        if observation.face_bbox is not None:
            x0, y0, x1, y1 = observation.face_bbox
            if x0 < 0.01 or y0 < 0.01 or x1 > 0.99 or y1 > 0.99:
                return False, "얼굴 일부가 화면 밖으로 잘렸습니다. 얼굴 전체가 보이도록 위치를 조금 조정하세요."
        if observation.face_scale is None or observation.face_scale < 0.12:
            return False, "얼굴이 너무 작게 보입니다. 현재 방향을 유지한 채 카메라에 조금 가까이 와주세요."
        if observation.face_center is None:
            return False, "얼굴 위치를 안정적으로 잡지 못했습니다. 조명을 확인하고 잠시 움직이지 마세요."
        if observation.tracking_confidence < 0.5:
            return False, "얼굴 추적이 불안정합니다. 얼굴에 빛이 고르게 비치도록 조명을 조정하세요."
        if any(
            value is None
            for value in (
                observation.head_yaw_deg,
                observation.head_pitch_deg,
                observation.head_roll_deg,
            )
        ):
            return False, "고개 방향을 계산하지 못했습니다. 얼굴 전체를 보이게 하고 정면을 바라봐 주세요."
        if observation.left_eye_open_ratio is None or observation.right_eye_open_ratio is None:
            return False, "양쪽 눈을 확인하지 못했습니다. 머리카락이나 안경 반사를 줄이고 눈을 떠주세요."
        if observation.gaze_x is None or observation.gaze_y is None:
            return False, "시선을 확인하지 못했습니다. 양쪽 눈을 뜨고 평소 작업 위치를 바라봐 주세요."
        return True, "좋습니다. 안내된 위치를 자연스럽게 바라봐 주세요."

    def _build_profile(self, target_samples: int) -> Optional[CalibrationProfile]:
        if len(self.samples) < max(10, int(target_samples * self.min_valid_ratio)):
            if self.invalid_reasons:
                self.failure_reason = self.invalid_reasons.most_common(1)[0][0]
            else:
                self.failure_reason = (
                    "유효한 얼굴 샘플이 부족합니다. 얼굴과 양쪽 눈이 보이게 한 뒤 다시 시도하세요."
                )
            return None

        yaw_values = [s.head_yaw_deg or 0.0 for s in self.samples]
        pitch_values = [s.head_pitch_deg or 0.0 for s in self.samples]
        if len(yaw_values) >= 2 and not self.guided_targets:
            if statistics.pstdev(yaw_values) > self.max_yaw_stdev:
                self.failure_reason = self.movement_failure_message
                return None

        if self.guided_targets:
            for target, samples in self.samples_by_target.items():
                if target == "natural" or len(samples) < 2:
                    continue
                target_yaw = [sample.head_yaw_deg or 0.0 for sample in samples]
                target_pitch = [sample.head_pitch_deg or 0.0 for sample in samples]
                if (
                    statistics.pstdev(target_yaw) > self.max_yaw_stdev
                    or statistics.pstdev(target_pitch) > self.max_pitch_stdev
                ):
                    self.failure_reason = (
                        "한 안내 위치에서 움직임이 너무 컸습니다. "
                        "표시된 영역을 잠시 바라본 뒤 다시 설정하세요."
                    )
                    return None
        roll_values = [s.head_roll_deg or 0.0 for s in self.samples]
        gaze_x_values = [s.gaze_x or 0.0 for s in self.samples]
        gaze_y_values = [s.gaze_y or 0.0 for s in self.samples]
        face_scale_values = [s.face_scale or 0.0 for s in self.samples]
        face_x_values = [s.face_center[0] for s in self.samples if s.face_center]
        face_y_values = [s.face_center[1] for s in self.samples if s.face_center]
        quality = min(1.0, len(self.samples) / float(max(target_samples, 1)))
        target_centers = {
            target: self._target_center(samples)
            for target, samples in self.samples_by_target.items()
            if samples
        }
        if self.guided_targets and not self._has_guided_coverage(target_centers):
            return None
        return CalibrationProfile(
            yaw_center=statistics.median(yaw_values),
            pitch_center=statistics.median(pitch_values),
            roll_center=statistics.median(roll_values),
            gaze_x_center=statistics.median(gaze_x_values),
            gaze_y_center=statistics.median(gaze_y_values),
            left_eye_open_baseline=statistics.median(
                [s.left_eye_open_ratio or 0.0 for s in self.samples]
            ),
            right_eye_open_baseline=statistics.median(
                [s.right_eye_open_ratio or 0.0 for s in self.samples]
            ),
            face_scale_center=statistics.median(face_scale_values),
            face_center=(
                statistics.median(face_x_values),
                statistics.median(face_y_values),
            ),
            sample_count=len(self.samples),
            quality_score=quality,
            feature_spread={
                "yaw": self._robust_spread(yaw_values),
                "pitch": self._robust_spread(pitch_values),
                "roll": self._robust_spread(roll_values),
                "gaze_x": self._robust_spread(gaze_x_values),
                "gaze_y": self._robust_spread(gaze_y_values),
                "face_scale": self._robust_spread(face_scale_values),
                "face_x": self._robust_spread(face_x_values),
                "face_y": self._robust_spread(face_y_values),
            },
            target_centers=target_centers,
        )

    def _has_guided_coverage(
        self,
        target_centers: Dict[str, Dict[str, float]],
    ) -> bool:
        required = {"left", "right", "up", "down"}
        if not required.issubset(target_centers):
            self.failure_reason = "방향별 유효 표본이 부족합니다. 안내에 따라 다시 설정하세요."
            return False

        left = target_centers["left"]
        right = target_centers["right"]
        up = target_centers["up"]
        down = target_centers["down"]
        horizontal_change = abs(left["gaze_x"] - right["gaze_x"]) + (
            abs(left["yaw"] - right["yaw"]) / 60.0
        )
        vertical_change = abs(up["gaze_y"] - down["gaze_y"]) + (
            abs(up["pitch"] - down["pitch"]) / 60.0
        )
        if horizontal_change < 0.04 or vertical_change < 0.04:
            self.failure_reason = (
                "시선 방향 변화가 충분히 확인되지 않았습니다. "
                "안내된 좌우·위아래 영역을 눈으로 따라가며 다시 설정하세요."
            )
            return False
        return True

    @staticmethod
    def _target_center(samples: List[FrameObservation]) -> Dict[str, float]:
        return {
            "yaw": statistics.median([sample.head_yaw_deg or 0.0 for sample in samples]),
            "pitch": statistics.median(
                [sample.head_pitch_deg or 0.0 for sample in samples]
            ),
            "roll": statistics.median([sample.head_roll_deg or 0.0 for sample in samples]),
            "gaze_x": statistics.median([sample.gaze_x or 0.0 for sample in samples]),
            "gaze_y": statistics.median([sample.gaze_y or 0.0 for sample in samples]),
            "face_x": statistics.median(
                [sample.face_center[0] for sample in samples if sample.face_center]
            ),
            "face_y": statistics.median(
                [sample.face_center[1] for sample in samples if sample.face_center]
            ),
            "face_scale": statistics.median(
                [sample.face_scale or 0.0 for sample in samples]
            ),
        }

    @staticmethod
    def _robust_spread(values: List[float]) -> float:
        if not values:
            return 0.0
        center = statistics.median(values)
        mad = statistics.median([abs(value - center) for value in values])
        return float(mad * 1.4826)
