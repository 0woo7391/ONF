from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Optional

import cv2
from PySide6.QtCore import QObject, Property, QSize, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

from onf_v2.app.camera_service import CameraService
from onf_v2.app.alert_controller import AttentionAlertController
from onf_v2.app.foreground_app_tracker import ForegroundAppTracker
from onf_v2.app.session_manager import SessionManager
from onf_v2.app.session_recorder import SessionRecorder
from onf_v2.app.settings_store import SettingsStore
from onf_v2.core.attention_engine import AttentionEngine
from onf_v2.core.face_analyzer import FaceAnalyzer
from onf_v2.core.screen_gaze import ScreenGazeContext
from onf_v2.core.metrics import study_seconds
from onf_v2.core.models import (
    AppState,
    CalibrationStatus,
    EffectiveState,
    FrameObservation,
    Mode,
    ObservationState,
)
from onf_v2.app.pomodoro import PomodoroConfig, PomodoroController, PomodoroPhase


OBSERVATION_MAX_AGE_SECONDS = 2.0


STATE_TEXT = {
    EffectiveState.FOCUS: ("집중 중", "화면 또는 필기 영역을 안정적으로 보고 있습니다."),
    EffectiveState.NON_FOCUS: ("주의 이탈", "시선이나 자세가 설정한 작업 영역을 벗어났습니다."),
    EffectiveState.BREAK: ("휴식 중", "휴식 시간은 학습시간과 집중률 계산에서 제외됩니다."),
    EffectiveState.UNSCORED: ("측정 불안정", "얼굴과 양쪽 눈이 잘 보이도록 위치와 조명을 확인하세요."),
    EffectiveState.ABSENT_PENDING: ("자리 비움", "얼굴을 찾지 못했습니다."),
}

RAW_TEXT = {
    ObservationState.GAZE_AWAY: "시선이 작업 영역을 벗어났습니다.",
    ObservationState.HEAD_SIDE: "고개 방향이 작업 영역을 벗어났습니다.",
    ObservationState.HEAD_DOWN: "고개가 기준보다 아래를 향하고 있습니다.",
    ObservationState.HEAD_UP: "고개가 기준보다 위를 향하고 있습니다.",
    ObservationState.EYES_CLOSED: "눈 감김이 지속되고 있습니다.",
    ObservationState.NO_FACE: "얼굴을 찾지 못했습니다.",
    ObservationState.MULTIPLE_FACES: "여러 얼굴이 보입니다. 한 사람만 화면에 남아 주세요.",
    ObservationState.LOW_CONFIDENCE: "얼굴 추적이 불안정합니다.",
    ObservationState.PROCESSING_ERROR: "얼굴 분석 중 오류가 발생했습니다.",
    ObservationState.CAMERA_ERROR: "카메라 영상을 받지 못하고 있습니다.",
    ObservationState.NOT_CALIBRATED: "세션 시작 전에 기준 자세를 설정하세요.",
}


class CameraImageProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.Image)
        self._image = QImage()
        self._lock = Lock()

    def set_image(self, image: QImage) -> None:
        with self._lock:
            self._image = image.copy()

    def requestImage(self, _id: str, size: QSize, requested_size: QSize) -> QImage:  # noqa: N802
        with self._lock:
            image = self._image.copy()
        if image.isNull():
            return QImage()
        if requested_size.isValid():
            image = image.scaled(
                requested_size,
                aspectMode=Qt.KeepAspectRatio,
                mode=Qt.SmoothTransformation,
            )
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


class MeasurementBridge(QObject):
    stateChanged = Signal()
    frameChanged = Signal()
    sessionFinished = Signal()
    recordsChanged = Signal()
    feedback = Signal(str)
    alertRequested = Signal()
    calibrationCueRequested = Signal()
    screenCalibrationRequested = Signal()
    screenValidationFinished = Signal()

    def __init__(
        self,
        image_provider: CameraImageProvider,
        settings_store: SettingsStore,
        database,
        parent: Optional[QObject] = None,
        auto_start: bool = True,
    ) -> None:
        super().__init__(parent)
        self.image_provider = image_provider
        self.settings_store = settings_store
        self.settings = settings_store.load()
        self.camera = CameraService(index=self.settings.camera_index)
        self.analyzer: Optional[FaceAnalyzer] = None
        self.engine = AttentionEngine(mode=Mode(self.settings.mode))
        self.engine.calibration.require_display_ack = True
        self.engine.set_work_mode(self.settings.work_mode)
        self.engine.policy.absence_to_break_seconds = self.settings.absence_to_break_minutes * 60.0
        recorder = SessionRecorder(str(database.path.parent))
        recorder.database = database
        self.session = SessionManager(recorder=recorder)
        self.app_usage_tracker = ForegroundAppTracker()
        self.alert_controller = AttentionAlertController(
            threshold_seconds=float(self.settings.attention_alert_seconds)
        )
        self.pomodoro = PomodoroController(self._pomodoro_config())
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="onf-qml")
        self.setup_future: Optional[Future] = None
        self.analysis_future: Optional[Future] = None
        self.camera_future: Optional[Future] = None
        self.latest_observation: Optional[FrameObservation] = None
        self.latest_decision = None
        self.observation_generation = 0
        self.analysis_generation = 0
        self.minimum_observation_timestamp = 0.0
        self.last_sequence = -1
        self.last_analysis_at = 0.0
        self.last_preview_at = 0.0
        self.frame_version = 0
        self.raw_frame_size = (0, 0)
        self.camera_connected = False
        self.camera_backend = ""
        self.camera_message = "카메라와 분석기를 준비하고 있습니다."
        self.status_text = "준비 중"
        self.status_detail = "카메라 연결을 확인하고 있습니다."
        self.calibration_message = "화면 자세를 먼저 설정하세요."
        self.screen_progress = 0.0
        self.writing_progress = 0.0
        self.calibration_target = ""
        self.calibration_guide = ""
        self.calibration_run_id = 0
        self.session_started_at: Optional[float] = None
        self.break_started_at: Optional[float] = None
        self.break_remaining = 0
        self.next_camera_retry_at = 0.0
        self._live_session_key = None
        self._live_session_data = {}
        self._closed = False
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        if auto_start:
            self.initialize()

    @Property(bool, notify=stateChanged)
    def cameraConnected(self) -> bool:
        return self.camera_connected

    @Property(str, notify=stateChanged)
    def cameraBackend(self) -> str:
        return self.camera_backend

    @Property(str, notify=stateChanged)
    def cameraMessage(self) -> str:
        return self.camera_message

    @Property("QVariantList", constant=True)
    def cameraOptions(self):
        return [{"label": f"Camera {index}", "value": index} for index in CameraService.list_candidate_cameras()]

    @Property(int, notify=stateChanged)
    def cameraIndex(self) -> int:
        return self.settings.camera_index

    @Property(str, notify=frameChanged)
    def frameSource(self) -> str:
        return f"image://camera/frame?v={self.frame_version}"

    @Property(str, notify=stateChanged)
    def statusText(self) -> str:
        return self.status_text

    @Property(str, notify=stateChanged)
    def statusDetail(self) -> str:
        return self.status_detail

    @Property(str, notify=stateChanged)
    def appState(self) -> str:
        return self.session.app_state.value

    @Property(bool, notify=stateChanged)
    def sessionRunning(self) -> bool:
        return self.session.app_state in (AppState.RUNNING, AppState.BREAK)

    @Property(bool, notify=stateChanged)
    def sessionPaused(self) -> bool:
        return self.session.app_state == AppState.BREAK

    @Property(str, notify=stateChanged)
    def sessionMode(self) -> str:
        return self.session.session_mode

    @Property(int, notify=stateChanged)
    def selectedTaskId(self) -> int:
        return self.session.metrics.task_id or -1

    @Slot(int, str, result=bool)
    def selectTask(self, task_id: int, title: str) -> bool:
        if self._closed or not self.sessionRunning:
            return False
        selected_id = task_id if task_id > 0 else None
        if selected_id is not None:
            task = next((row for row in self.session.recorder.database.list_planner_tasks() if row.id == selected_id), None)
            if task is None or task.status != "pending":
                self.feedback.emit("진행할 수 있는 할 일을 선택하세요.")
                return False
            title = task.title
        now = time.monotonic()
        if self.session.session_mode == "pomodoro":
            self._update_pomodoro(now)
            if not self.sessionRunning:
                return False
        self._expire_observation(now)
        metrics = self.session.metrics
        if metrics.last_timestamp is None and self.session_started_at is not None:
            metrics.update(EffectiveState.UNSCORED, self.session_started_at)
        if not metrics.set_task(selected_id, title, now):
            return False
        self.stateChanged.emit()
        return True

    @Property(str, notify=stateChanged)
    def effectiveState(self) -> str:
        if self.sessionPaused:
            return EffectiveState.BREAK.value
        if not self.sessionRunning:
            return ""
        if self.latest_decision is None:
            return EffectiveState.UNSCORED.value
        if time.monotonic() - self.latest_decision.timestamp > OBSERVATION_MAX_AGE_SECONDS:
            return EffectiveState.UNSCORED.value
        return self.latest_decision.effective_state.value

    @Property(bool, notify=stateChanged)
    def screenReady(self) -> bool:
        return self.engine.calibrated

    @Property(bool, notify=stateChanged)
    def writingReady(self) -> bool:
        return self.engine.writing_calibrated

    @Property(bool, notify=stateChanged)
    def writingRequired(self) -> bool:
        return self.engine.work_mode == "screen_writing"

    @Property(float, notify=stateChanged)
    def screenCalibrationProgress(self) -> float:
        return self.screen_progress

    @Property(float, notify=stateChanged)
    def writingCalibrationProgress(self) -> float:
        return self.writing_progress

    @Property(str, notify=stateChanged)
    def calibrationMessage(self) -> str:
        return self.calibration_message

    @Property(str, notify=stateChanged)
    def calibrationTarget(self) -> str:
        return self.calibration_target

    @Property(str, notify=stateChanged)
    def calibrationGuide(self) -> str:
        return self.calibration_guide

    @Property(int, notify=stateChanged)
    def calibrationRunId(self) -> int:
        return self.calibration_run_id

    @Property(int, notify=stateChanged)
    def calibrationStageIndex(self) -> int:
        return self.engine.screen_collection.target_index

    @Property("QVariantList", notify=stateChanged)
    def calibrationTargets(self):
        return self.engine.screen_collection.target_states

    @Property(str, notify=stateChanged)
    def screenTargetState(self) -> str:
        return self.engine.screen_collection.target_state

    @Property(bool, notify=stateChanged)
    def screenTargetStable(self) -> bool:
        return self.engine.screen_collection.collection_stable

    @Property(float, notify=stateChanged)
    def screenTargetProgress(self) -> float:
        manager = self.engine.screen_collection
        return manager.target_states[manager.target_index]["progress"]

    @Property(bool, notify=stateChanged)
    def screenCalibrationFailed(self) -> bool:
        return self.engine.screen_collection.status == CalibrationStatus.FAILED

    @Property(bool, notify=stateChanged)
    def screenValidationActive(self) -> bool:
        return self.engine.validating_gaze

    @Property("QVariantMap", notify=stateChanged)
    def validationTargetPositions(self):
        mapping = self.engine.screen_gaze_mapping
        return {key: list(point) for key, point in mapping.validation_positions.items()} if mapping is not None else {}

    @Property(str, notify=stateChanged)
    def gazeMappingMessage(self) -> str:
        return self.engine.gaze_mapping_message

    @Property("QVariantList", notify=stateChanged)
    def gazeValidationRows(self):
        return [
            {
                "key": region.key,
                "median": round(region.median_error * 100, 1),
                "p90": round(region.p90_error * 100, 1),
                "spread": round(region.prediction_spread * 100, 1),
                "valid": round(region.valid_fraction * 100),
                "samples": region.valid_count,
                "attempts": region.attempted_count,
            }
            for region in self.engine.gaze_validation_result
        ]

    @Property(float, notify=stateChanged)
    def baselineCenterX(self) -> float:
        profile = self.engine.guide_profile
        return profile.face_center[0] if profile is not None else 0.5

    @Property(float, notify=stateChanged)
    def baselineCenterY(self) -> float:
        profile = self.engine.guide_profile
        return profile.face_center[1] if profile is not None else 0.5

    @Property(int, notify=stateChanged)
    def elapsedSeconds(self) -> int:
        return int(study_seconds(self._current_durations()))

    def _current_durations(self):
        metrics = self.session.metrics
        if not self.sessionRunning:
            return metrics.snapshot()
        now = time.monotonic()
        sample_time = now
        if (
            metrics.last_timestamp is not None
            and metrics.last_effective_state in (EffectiveState.FOCUS, EffectiveState.NON_FOCUS)
        ):
            sample_time = min(now, metrics.last_timestamp + OBSERVATION_MAX_AGE_SECONDS)
        values = metrics.snapshot(sample_time, self.session_started_at)
        values[EffectiveState.UNSCORED] += max(0.0, now - sample_time)
        return values

    @Property("QVariantMap", notify=stateChanged)
    def liveSessionData(self):
        if not self.sessionRunning or self.session.started_at_wall is None:
            return {}
        key = (self.session_started_at, int(time.monotonic()), self.session.metrics.last_effective_state)
        if key != self._live_session_key:
            values = self._current_durations()
            started = datetime.fromisoformat(self.session.started_at_wall)
            self._live_session_data = {
                "revision": str(key),
                "started": self.session.started_at_wall,
                "ended": (started + timedelta(seconds=sum(values.values()))).isoformat(sep=" "),
                "durations": {state.value: seconds for state, seconds in values.items()},
                "timeline": json.dumps([
                    {state.value: seconds for state, seconds in bucket.items()}
                    for bucket in self.session.metrics.minute_snapshot(values)
                ]),
            }
            self._live_session_key = key
        return self._live_session_data

    @Property(int, notify=stateChanged)
    def todayStudySeconds(self) -> int:
        return self._today_seconds(study_seconds)

    @Property(int, notify=stateChanged)
    def todayFocusSeconds(self) -> int:
        return self._today_seconds(lambda values: values[EffectiveState.FOCUS])

    def _today_seconds(self, select_seconds) -> int:
        if not self.sessionRunning or self.session.started_at_wall is None:
            return 0
        started = datetime.fromisoformat(self.session.started_at_wall)
        now = datetime.now()
        study_date = (now - timedelta(hours=self.settings.study_day_start_hour)).date()
        day_start = datetime.combine(study_date, datetime.min.time()) + timedelta(hours=self.settings.study_day_start_hour)
        day_end = day_start + timedelta(days=1)
        metrics = self.session.metrics
        values = self._current_durations()
        if started >= day_start:
            return int(select_seconds(values))
        total = 0.0
        for index, bucket in enumerate(metrics.minute_snapshot(values)):
            moment = started + timedelta(minutes=index)
            duration = sum(bucket.values())
            included = max(0.0, (min(moment + timedelta(seconds=duration), day_end) - max(moment, day_start)).total_seconds())
            if duration > 0 and included > 0:
                total += select_seconds(bucket) * included / duration
        return int(total)

    @Property(int, notify=stateChanged)
    def breakRemainingSeconds(self) -> int:
        if self.pomodoro.phase in (PomodoroPhase.SHORT_BREAK, PomodoroPhase.LONG_BREAK):
            return int(self.pomodoro.remaining(time.monotonic()))
        if (
            self.pomodoro.phase == PomodoroPhase.PAUSED
            and self.pomodoro.paused_from in (PomodoroPhase.SHORT_BREAK, PomodoroPhase.LONG_BREAK)
        ):
            return int(self.pomodoro.remaining(time.monotonic()))
        if self.pomodoro.phase == PomodoroPhase.WAITING_NEXT:
            return 0
        if self.break_started_at is not None:
            return max(0, self.settings.break_duration_minutes * 60 - int(time.monotonic() - self.break_started_at))
        return self.break_remaining

    @Property(int, notify=stateChanged)
    def focusPercent(self) -> int:
        values = self._current_durations()
        scored = values[EffectiveState.FOCUS] + values[EffectiveState.NON_FOCUS]
        return round(values[EffectiveState.FOCUS] / scored * 100) if scored > 0 else 0

    @Property(int, notify=stateChanged)
    def coveragePercent(self) -> int:
        values = self._current_durations()
        study = study_seconds(values)
        scored = values[EffectiveState.FOCUS] + values[EffectiveState.NON_FOCUS]
        return round(scored / study * 100) if study > 0 else 0

    @Property("QVariantMap", notify=stateChanged)
    def durations(self):
        values = self._current_durations()
        return {state.value: int(values.get(state, 0.0)) for state in EffectiveState}

    @Property(int, notify=stateChanged)
    def pomodoroRemainingSeconds(self) -> int:
        return int(self.pomodoro.remaining(time.monotonic())) if self.pomodoro.active else 0

    @Property(float, notify=stateChanged)
    def pomodoroProgress(self) -> float:
        if self.pomodoro.phase in (PomodoroPhase.IDLE, PomodoroPhase.WAITING_NEXT):
            return 0.0
        if self.pomodoro.phase == PomodoroPhase.COMPLETED:
            return 1.0
        phase = self.pomodoro.paused_from if self.pomodoro.phase == PomodoroPhase.PAUSED else self.pomodoro.phase
        config = self.pomodoro.config
        minutes = {
            PomodoroPhase.FOCUS: config.focus_minutes,
            PomodoroPhase.SHORT_BREAK: config.short_break_minutes,
            PomodoroPhase.LONG_BREAK: config.long_break_minutes,
        }.get(phase, 0)
        if minutes <= 0:
            return 0.0
        return min(1.0, max(0.0, 1.0 - self.pomodoro.remaining(time.monotonic()) / (minutes * 60.0)))

    @Property(str, notify=stateChanged)
    def breakActionText(self) -> str:
        if self.session.session_mode != "pomodoro":
            return "학습 재개" if self.sessionPaused else "휴식"
        phase = self.pomodoro.phase
        if phase == PomodoroPhase.WAITING_NEXT:
            return "다음 학습 시작" if self.pomodoro.paused_from == PomodoroPhase.FOCUS else "휴식 시작"
        if phase == PomodoroPhase.PAUSED:
            return "학습 재개" if self.pomodoro.paused_from == PomodoroPhase.FOCUS else "휴식 재개"
        if phase in (PomodoroPhase.SHORT_BREAK, PomodoroPhase.LONG_BREAK):
            return "휴식 일시정지"
        return "휴식"

    @Property(int, notify=stateChanged)
    def pomodoroCompletedRounds(self) -> int:
        return self.pomodoro.completed_cycles

    @Property(str, notify=stateChanged)
    def pomodoroPhase(self) -> str:
        return self.pomodoro.phase.value

    @Property(str, notify=stateChanged)
    def pomodoroPausedFrom(self) -> str:
        return self.pomodoro.paused_from.value if self.pomodoro.paused_from else ""

    @Property(str, notify=stateChanged)
    def pomodoroPhaseLabel(self) -> str:
        labels = {
            PomodoroPhase.FOCUS: "집중",
            PomodoroPhase.SHORT_BREAK: "짧은 휴식",
            PomodoroPhase.LONG_BREAK: "긴 휴식",
            PomodoroPhase.PAUSED: "일시정지",
            PomodoroPhase.WAITING_NEXT: "다음 단계 대기",
            PomodoroPhase.COMPLETED: "완료",
        }
        return labels.get(self.pomodoro.phase, "준비")

    @Slot()
    def initialize(self) -> None:
        if self.setup_future is not None:
            return
        self.camera_message = "카메라와 얼굴 분석기를 준비하고 있습니다."
        self.stateChanged.emit()
        self.setup_future = self.executor.submit(self._initialize_devices, self.settings.camera_index)

    def _initialize_devices(self, index: int):
        opened = self.camera.open(index)
        try:
            analyzer = FaceAnalyzer()
            error = "" if opened else f"Camera {index}를 열 수 없습니다. 다른 카메라를 선택해 주세요."
            return opened, analyzer, error
        except Exception as exc:
            return opened, None, f"얼굴 분석기를 준비하지 못했습니다: {exc}"

    @Slot(int)
    def selectCamera(self, index: int) -> None:
        if self.sessionRunning or self.camera_future is not None:
            self.feedback.emit("카메라는 학습 종료 후 변경할 수 있습니다.")
            return
        self.settings.camera_index = max(0, index)
        self.settings_store.save(self.settings)
        self.cancelCalibration()
        self._invalidate_observation(time.monotonic())
        self.engine.clear_calibrations()
        self.raw_frame_size = (0, 0)
        self.camera_connected = False
        self.camera_message = f"Camera {index}에 연결하고 있습니다."
        self.camera_future = self.executor.submit(self.camera.open, index)
        self.next_camera_retry_at = 0.0
        self.stateChanged.emit()

    @Slot()
    def refreshCamera(self) -> None:
        self.selectCamera(self.settings.camera_index)

    @Slot()
    def reloadSettings(self) -> None:
        self.settings = self.settings_store.load()
        self.engine.set_mode(Mode(self.settings.mode))
        self.engine.set_work_mode(self.settings.work_mode)
        self.engine.policy.absence_to_break_seconds = self.settings.absence_to_break_minutes * 60.0
        self.alert_controller.threshold_seconds = float(self.settings.attention_alert_seconds)
        self.stateChanged.emit()

    @Slot(str, result=bool)
    def startCalibration(self, target: str) -> bool:
        if not self.camera_connected or self.analyzer is None:
            self.feedback.emit("카메라가 연결된 뒤 다시 시도하세요.")
            return False
        if self.sessionRunning:
            self.feedback.emit("학습을 종료한 뒤 기준 자세를 다시 설정하세요.")
            return False
        if target == "writing" and not self.writingRequired:
            self.feedback.emit("설정에서 화면 + 필기 모드를 선택하세요.")
            return False
        if target == "writing" and not self.engine.calibrated:
            self.feedback.emit("화면 자세를 먼저 설정하세요.")
            return False
        now = time.monotonic()
        self._invalidate_observation(now)
        self.calibration_run_id += 1
        self.engine.start_calibration(now, target)
        if target == "screen":
            self.screen_progress = 0.0
        else:
            self.writing_progress = 0.0
        self.session.app_state = AppState.CALIBRATING
        self.calibration_target = target
        self.calibration_guide = "center" if target == "screen" else ""
        self.calibration_message = "안내 위치를 자연스럽게 바라봐 주세요."
        self.status_text = "필기 자세 설정 중" if target == "writing" else "화면 자세 설정 중"
        self.status_detail = self.calibration_message
        if target == "screen":
            self.screenCalibrationRequested.emit()
        else:
            self.calibrationCueRequested.emit()
        self.stateChanged.emit()
        return True

    @Slot(result=bool)
    def startScreenValidation(self) -> bool:
        if self.sessionRunning or self.calibration_target:
            self.feedback.emit("학습이나 자세 설정을 마친 뒤 시선을 검증하세요.")
            return False
        if not self.camera_connected or self.analyzer is None:
            self.feedback.emit("카메라 연결을 확인하세요.")
            return False
        now = time.monotonic()
        if not self.engine.start_gaze_validation(now):
            self.feedback.emit(self.engine.gaze_mapping_message)
            return False
        self._invalidate_observation(now)
        self.calibration_run_id += 1
        self.calibration_target = "validation"
        self.calibration_guide = "center"
        self.session.app_state = AppState.CALIBRATING
        self.status_text = "시선 검증 중"
        self.calibration_message = "표시된 점을 보세요. 기존 집중 판정은 바뀌지 않습니다."
        self.status_detail = self.calibration_message
        self.screenCalibrationRequested.emit()
        self.stateChanged.emit()
        return True

    @Slot()
    def cancelCalibration(self) -> None:
        target = self.calibration_target
        if not target and (self.screenCalibrationFailed or self.engine.validating_gaze):
            target = "validation" if self.engine.validating_gaze else "screen"
        if not target:
            return
        self._invalidate_observation(time.monotonic())
        manager = self.engine.writing_calibration if target == "writing" else self.engine.screen_collection
        manager.cancel()
        self.engine.validating_gaze = False
        if target == "writing":
            self.writing_progress = 0.0
        else:
            self.screen_progress = 0.0
        self.calibration_target = ""
        self.calibration_guide = ""
        self.calibration_message = "시선 검증을 닫았습니다." if target == "validation" else "기준 자세 설정을 취소했습니다."
        self.session.app_state = AppState.READY if self.engine.ready_for_session else AppState.PREVIEW
        self.status_text = "기준 자세 필요" if not self.engine.ready_for_session else "학습 시작 가능"
        self.status_detail = self.calibration_message
        self.feedback.emit(self.calibration_message)
        self.stateChanged.emit()

    @Slot(result=bool)
    def retryScreenCalibration(self) -> bool:
        if not self.camera_connected or self.analyzer is None or self.sessionRunning:
            self.calibration_message = (
                "학습을 종료한 뒤 기준 자세를 다시 설정하세요."
                if self.sessionRunning
                else "카메라 연결을 확인하세요. 취소 후 설정에서 카메라를 새로고침할 수 있습니다."
            )
            self.status_detail = self.calibration_message
            self.feedback.emit(self.calibration_message)
            self.stateChanged.emit()
            return False
        now = time.monotonic()
        manager = self.engine.screen_collection
        if not manager.retry_failed(now):
            return False
        self._invalidate_observation(now)
        self.calibration_run_id += 1
        self.engine.active_calibration_target = "screen"
        self.engine.reset_runtime_state()
        self.session.app_state = AppState.CALIBRATING
        self.calibration_target = "validation" if self.engine.validating_gaze else "screen"
        self.calibration_guide = manager.current_target
        targets = manager.target_states
        if not self.engine.validating_gaze:
            self.screen_progress = sum(item["progress"] for item in targets) / len(targets)
        self.calibration_message = "부족한 방향의 표본을 다시 수집합니다."
        self.status_text = "시선 다시 검증 중" if self.engine.validating_gaze else "화면 자세 다시 설정 중"
        self.status_detail = self.calibration_message
        self.screenCalibrationRequested.emit()
        self.stateChanged.emit()
        return True

    @Slot(int, int, str, result=bool)
    @Slot(int, int, str, "QVariantMap", result=bool)
    def screenTargetDisplayed(self, run_id: int, stage_index: int, key: str, display=None) -> bool:
        if self.calibration_target not in {"screen", "validation"} or run_id != self.calibration_run_id:
            return False
        manager = self.engine.screen_collection
        if manager.status != CalibrationStatus.COLLECTING or stage_index != manager.target_index or key != manager.current_target:
            return False
        position = context = None
        if display is not None:
            try:
                position = (float(display["u"]), float(display["v"]))
                if not all(0 <= value <= 1 for value in position):
                    raise ValueError("Invalid target position")
                context = ScreenGazeContext(
                    camera_index=self.settings.camera_index,
                    frame_size=self.raw_frame_size,
                    screen_name=str(display["screenName"]),
                    screen_rect=tuple(float(display[name]) for name in ("screenX", "screenY", "screenWidth", "screenHeight")),
                    window_size=(float(display["width"]), float(display["height"])),
                    device_pixel_ratio=float(display["dpr"]),
                )
            except (KeyError, TypeError, ValueError):
                position = context = None
                self.engine.screen_collection.mapping_context_valid = False
        mapping = self.engine.screen_gaze_mapping
        if self.engine.validating_gaze and (mapping is None or context != mapping.context):
            manager = self.engine.gaze_validation
            manager.status = CalibrationStatus.FAILED
            manager.target_state = "failed"
            manager.failed_targets = (manager.current_target,)
            manager.failure_reason = "화면 또는 카메라 구성이 달라졌습니다. 검증을 닫고 화면 자세를 다시 설정하세요."
            self._apply_calibration_progress(manager._guided_progress(manager.failure_reason))
            self.stateChanged.emit()
            return False
        return self.engine.confirm_screen_target(time.monotonic(), stage_index, key, position, context)

    @Slot(str, int, str, str, result=bool)
    def startSession(self, mode: str = "free", task_id: int = -1, task_title: str = "", _unused: str = "") -> bool:
        if self._closed or self.sessionRunning:
            return False
        if self.calibration_target or self.screenCalibrationFailed:
            self.feedback.emit("자세 설정이나 시선 검증을 마치거나 닫은 뒤 학습을 시작하세요.")
            return False
        if not self.camera_connected:
            self.feedback.emit("카메라 연결을 확인하세요.")
            return False
        if not self.engine.ready_for_session:
            missing = "필기 자세" if self.engine.calibrated else "화면 자세"
            self.feedback.emit(f"{missing} 설정이 필요합니다.")
            return False
        self.engine.reset_runtime_state()
        self.alert_controller.reset()
        now = time.monotonic()
        self._invalidate_observation(now)
        self.latest_decision = None
        session_mode = "pomodoro" if mode == "pomodoro" else "free"
        if session_mode == "pomodoro":
            self.pomodoro.configure(self._pomodoro_config())
            self.pomodoro.start(now)
        else:
            self.pomodoro.stop()
        self.session.start(
            session_mode=session_mode,
            pomodoro_cycles_planned=self.settings.pomodoro_cycles if session_mode == "pomodoro" else 0,
            task_id=task_id if task_id > 0 else None,
            started_at_monotonic=now,
            task_title=task_title,
        )
        self.app_usage_tracker.reset()
        self.app_usage_tracker.set_active(True, now)
        self.session_started_at = now
        self.break_started_at = None
        self.break_remaining = 0
        self.status_text = "측정 시작"
        self.status_detail = f"{task_title} 학습을 측정합니다." if task_title else "시각적 집중 측정을 시작했습니다."
        self.feedback.emit("학습을 시작했습니다.")
        self.stateChanged.emit()
        return True

    @Slot()
    def toggleBreak(self) -> None:
        if not self.sessionRunning:
            return
        if self.session.session_mode == "pomodoro" and self.pomodoro.active:
            now = time.monotonic()
            previous_phase = self.pomodoro.phase
            self._update_pomodoro(now)
            if not self.sessionRunning or self.pomodoro.phase != previous_phase:
                self.stateChanged.emit()
                return
            if self.pomodoro.phase == PomodoroPhase.WAITING_NEXT:
                update = self.pomodoro.start_next(now)
                self._set_session_break(update.phase != PomodoroPhase.FOCUS, now)
                self.break_started_at = None
                self.break_remaining = 0
                self.feedback.emit(self.pomodoroPhaseLabel + " 단계를 시작했습니다.")
            elif self.pomodoro.phase == PomodoroPhase.PAUSED:
                update = self.pomodoro.resume(now)
                self._set_session_break(update.phase != PomodoroPhase.FOCUS, now)
                self.break_started_at = None
                self.break_remaining = 0
                self.feedback.emit("뽀모도로를 재개했습니다.")
            else:
                self.pomodoro.pause(now)
                self._set_session_break(True, now)
                self.break_started_at = now
                self.feedback.emit("뽀모도로를 일시정지했습니다.")
            self.alert_controller.reset()
            self.stateChanged.emit()
            return
        now = time.monotonic()
        self._set_session_break(self.session.app_state != AppState.BREAK, now)
        if self.session.app_state == AppState.BREAK:
            self.break_started_at = now
            self.break_remaining = self.settings.break_duration_minutes * 60
            self.feedback.emit("휴식을 시작했습니다.")
        else:
            self.break_started_at = None
            self.break_remaining = 0
            self.feedback.emit("측정을 재개했습니다.")
        self.stateChanged.emit()

    @Slot()
    def endSession(self) -> None:
        if not self.sessionRunning:
            return
        now = time.monotonic()
        self._expire_observation(now)
        app_usage_seconds = self.app_usage_tracker.finish(now)
        if self.session.session_mode == "pomodoro":
            self.session.pomodoro_cycles_completed = self.pomodoro.completed_cycles
            self.pomodoro.stop()
        self.session.finish(now, app_usage_seconds=app_usage_seconds)
        self._invalidate_observation(now)
        self.session_started_at = None
        self.break_started_at = None
        self.break_remaining = 0
        self.status_text = "학습 종료"
        self.status_detail = "세션 기록을 저장했습니다."
        self.sessionFinished.emit()
        self.recordsChanged.emit()
        self.feedback.emit("학습 기록을 저장했습니다.")
        self.stateChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        if self.sessionRunning:
            self.endSession()
        if self.analysis_future is not None:
            self.analysis_future.cancel()
        self.camera.release()
        if self.analyzer is not None:
            analyzer = self.analyzer
            if self.analysis_future is not None and not self.analysis_future.done():
                self.analysis_future.add_done_callback(lambda _: analyzer.close())
            else:
                analyzer.close()

        def close_setup(future: Future) -> None:
            try:
                if future.exception() is None:
                    _, analyzer, _ = future.result()
                    if analyzer is not None:
                        analyzer.close()
            finally:
                self.camera.release()

        for future in (self.setup_future, self.camera_future):
            if future is not None and not future.cancel():
                future.add_done_callback(
                    close_setup if future is self.setup_future else lambda _: self.camera.release()
                )
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _tick(self) -> None:
        if self._closed:
            return
        now = time.monotonic()
        self._consume_setup()
        self._consume_camera_open()
        self._expire_observation(now)
        self._consume_analysis()
        self._check_calibration_timeout(now)
        self.app_usage_tracker.update(now)
        self._update_pomodoro(now)
        if self.break_started_at is not None:
            self.break_remaining = max(0, self.settings.break_duration_minutes * 60 - int(now - self.break_started_at))
        if not self.camera_connected:
            if self.sessionRunning and (
                self.latest_decision is None
                or self.latest_decision.raw_state != ObservationState.CAMERA_ERROR
            ):
                self._record_unavailable(ObservationState.CAMERA_ERROR, now)
            if (
                self.analyzer is not None
                and self.setup_future is None
                and self.camera_future is None
                and now >= self.next_camera_retry_at
            ):
                self.camera_message = f"Camera {self.settings.camera_index}에 다시 연결하고 있습니다."
                self.camera_future = self.executor.submit(
                    self.camera.open,
                    self.settings.camera_index,
                )
                self.next_camera_retry_at = now + 5.0
            self.stateChanged.emit()
            return
        camera_frame = self.camera.read()
        if not camera_frame.ok or camera_frame.frame is None:
            self.camera_connected = False
            self._invalidate_observation(now)
            if self.sessionRunning:
                self._record_unavailable(ObservationState.CAMERA_ERROR, now)
            self.camera_message = camera_frame.error or "카메라 프레임을 받지 못했습니다."
            self.status_text = "카메라 연결 확인"
            self.status_detail = "설정에서 카메라를 새로고침하거나 다른 장치를 선택하세요."
            self.stateChanged.emit()
            return
        shape = getattr(camera_frame.frame, "shape", ())
        if len(shape) >= 2:
            frame_size = (int(shape[1]), int(shape[0]))
            if self.raw_frame_size != (0, 0) and frame_size != self.raw_frame_size:
                self._invalidate_observation(now)
                self.engine.clear_screen_gaze()
                self.engine.screen_collection.mapping_context_valid = False
            self.raw_frame_size = frame_size
        if now - self.last_preview_at >= 0.05:
            self.last_preview_at = now
            self._publish_frame(camera_frame.frame)
        if (
            self.analyzer is not None
            and self.analysis_future is None
            and camera_frame.sequence != self.last_sequence
            and now - self.last_analysis_at >= 1.0 / 15.0
        ):
            self.last_sequence = camera_frame.sequence
            self.last_analysis_at = now
            self.analysis_generation = self.observation_generation
            self.analysis_future = self.executor.submit(
                self.analyzer.analyze,
                camera_frame.frame.copy(),
                camera_frame.timestamp,
            )
        self.stateChanged.emit()

    def _consume_setup(self) -> None:
        future = self.setup_future
        if future is None or not future.done():
            return
        self.setup_future = None
        try:
            opened, analyzer, error = future.result()
        except Exception as exc:
            opened, analyzer, error = False, None, str(exc)
        self.analyzer = analyzer
        self.camera_connected = bool(opened and analyzer is not None)
        self.camera_backend = self.camera.backend_name
        self.camera_message = (
            f"Camera {self.settings.camera_index} · {self.camera_backend} 연결됨"
            if self.camera_connected
            else error or "카메라를 준비하지 못했습니다."
        )
        self.next_camera_retry_at = 0.0 if self.camera_connected else time.monotonic() + 2.0
        self.status_text = "기준 자세 필요" if self.camera_connected else "준비 오류"
        self.status_detail = "화면 자세를 설정하세요." if self.camera_connected else self.camera_message
        self.stateChanged.emit()

    def _consume_camera_open(self) -> None:
        future = self.camera_future
        if future is None or not future.done():
            return
        self.camera_future = None
        try:
            self.camera_connected = bool(future.result())
        except Exception:
            self.camera_connected = False
        self.camera_backend = self.camera.backend_name
        self.camera_message = (
            f"Camera {self.settings.camera_index} · {self.camera_backend} 연결됨"
            if self.camera_connected
            else f"Camera {self.settings.camera_index}를 열 수 없습니다."
        )
        self.next_camera_retry_at = 0.0 if self.camera_connected else time.monotonic() + 5.0
        self.status_text = "기준 자세 필요" if self.camera_connected else "카메라 연결 실패"
        self.status_detail = "화면 자세를 설정하세요." if self.camera_connected else "다른 카메라를 선택하거나 사용 중인 앱을 닫아 주세요."
        self.stateChanged.emit()

    def _consume_analysis(self) -> None:
        future = self.analysis_future
        if future is None or not future.done():
            return
        self.analysis_future = None
        if self.analysis_generation != self.observation_generation:
            return
        try:
            observation = future.result()
        except Exception as exc:
            observation = FrameObservation(
                timestamp=time.monotonic(),
                error=str(exc),
                quality_reason=ObservationState.PROCESSING_ERROR.value,
            )
        max_age = (
            self.engine.screen_collection.max_sample_gap_seconds
            if self.calibration_target in {"screen", "validation"}
            else OBSERVATION_MAX_AGE_SECONDS
        )
        if (
            time.monotonic() - observation.timestamp > max_age
            or observation.timestamp < self.minimum_observation_timestamp
            or (
                self.latest_decision is not None
                and observation.timestamp <= self.latest_decision.timestamp
            )
        ):
            return
        self.latest_observation = observation
        if self.session.app_state == AppState.CALIBRATING:
            self._update_calibration(observation)
        decision = self.engine.decide(observation, self.session.manual_break)
        self._apply_decision(decision)

    def _apply_decision(self, decision) -> None:
        self.latest_decision = decision
        if self.sessionRunning:
            self.session.update(decision)
            self.app_usage_tracker.set_active(
                self.session.app_state == AppState.RUNNING
                and decision.effective_state != EffectiveState.BREAK,
                decision.timestamp,
            )
            alert = self.alert_controller.update(decision.effective_state, decision.timestamp)
            if alert.just_triggered:
                self.alertRequested.emit()
                self.feedback.emit(
                    f"주의 이탈이 {int(self.alert_controller.threshold_seconds)}초 이상 지속되고 있습니다."
                )
        self._update_status(decision)

    def _invalidate_observation(self, timestamp: float) -> None:
        self.observation_generation += 1
        self.minimum_observation_timestamp = timestamp

    def _record_unavailable(self, raw_state: ObservationState, timestamp: float) -> None:
        decision = self.engine.policy.decide(
            raw_state, timestamp, manual_break=self.session.manual_break
        )
        self._apply_decision(decision)

    def _expire_observation(self, timestamp: float) -> None:
        if not self.sessionRunning:
            return
        if self.latest_decision is None:
            if (
                self.session_started_at is None
                or timestamp < self.session_started_at + OBSERVATION_MAX_AGE_SECONDS
            ):
                return
            cutoff = self.session_started_at + OBSERVATION_MAX_AGE_SECONDS
        else:
            if self.latest_decision.effective_state in (EffectiveState.BREAK, EffectiveState.UNSCORED):
                return
            cutoff = self.latest_decision.timestamp + OBSERVATION_MAX_AGE_SECONDS
            if timestamp < cutoff:
                return
        self._invalidate_observation(cutoff)
        raw_state = (
            ObservationState.LOW_CONFIDENCE
            if self.camera_connected
            else ObservationState.CAMERA_ERROR
        )
        self._record_unavailable(raw_state, cutoff)

    def _update_calibration(self, observation: FrameObservation) -> None:
        progress = (
            self.engine.update_gaze_validation(observation)
            if self.calibration_target == "validation"
            else self.engine.update_calibration(observation)
        )
        self._apply_calibration_progress(progress)

    def _check_calibration_timeout(self, timestamp: float) -> None:
        if not self.calibration_target:
            return
        manager = (
            self.engine.writing_calibration
            if self.calibration_target == "writing"
            else self.engine.screen_collection
        )
        progress = manager.check_timeout(timestamp)
        if progress is not None:
            self._apply_calibration_progress(progress)

    def _apply_calibration_progress(self, progress) -> None:
        validating = self.calibration_target == "validation"
        if self.calibration_target == "writing":
            self.writing_progress = progress.progress
        elif not validating:
            self.screen_progress = progress.progress
        self.calibration_message = progress.message
        self.calibration_guide = progress.target_key
        self.status_detail = progress.message
        if progress.stage_changed:
            self.calibrationCueRequested.emit()
        if progress.status == CalibrationStatus.READY:
            self.session.app_state = AppState.READY
            if validating:
                self.session.app_state = AppState.READY if self.engine.ready_for_session else AppState.PREVIEW
                self.status_text = "시선 검증 완료"
                self.status_detail = self.engine.gaze_mapping_message
                self.calibration_target = ""
                self.feedback.emit("시선 검증 결과를 확인하세요. 기존 집중 판정은 유지합니다.")
                self.calibrationCueRequested.emit()
                QTimer.singleShot(0, self.screenValidationFinished.emit)
                return
            label = "필기" if self.calibration_target == "writing" else "화면"
            self.status_text = f"{label} 자세 설정 완료"
            self.status_detail = "필요한 기준 자세가 모두 준비되었습니다." if self.engine.ready_for_session else "필기 자세도 설정하세요."
            self.calibration_target = ""
            self.calibrationCueRequested.emit()
            self.feedback.emit(f"{label} 자세 설정을 완료했습니다.")
        elif progress.status == CalibrationStatus.FAILED:
            if validating:
                self.session.app_state = AppState.READY if self.engine.ready_for_session else AppState.PREVIEW
                self.status_text = "시선 검증 중단 · 기준 유지"
                self.status_detail = progress.message
                self.calibration_target = ""
                self.feedback.emit("시선 검증을 마치지 못했습니다. 기존 기준 자세는 유지합니다.")
                return
            label = "필기" if self.calibration_target == "writing" else "화면"
            manager = (
                self.engine.writing_calibration
                if self.calibration_target == "writing"
                else self.engine.calibration
            )
            previous_profile_kept = manager.profile is not None
            self.session.app_state = (
                AppState.READY if self.engine.ready_for_session else AppState.PREVIEW
            )
            self.status_text = (
                "보정 실패 · 기존 기준 유지"
                if previous_profile_kept
                else f"{label} 자세 설정 실패"
            )
            self.status_detail = (
                f"기존 기준 자세로 학습 가능합니다. {progress.message}"
                if previous_profile_kept
                else progress.message
            )
            self.calibration_target = ""
            self.calibrationCueRequested.emit()
            self.feedback.emit(
                f"{label} 새 자세 설정에 실패했습니다. 기존 기준 자세를 유지했습니다."
                if previous_profile_kept
                else f"{label} 자세를 설정하지 못했습니다. 안내를 확인하세요."
            )

    def _update_status(self, decision) -> None:
        if self.session.app_state == AppState.CALIBRATING:
            return
        if self.session.app_state == AppState.READY and not self.sessionRunning:
            if self.status_text == "보정 실패 · 기존 기준 유지":
                return
            self.status_text = "학습 시작 가능"
            self.status_detail = "기준 자세 설정이 완료되었습니다."
            return
        if not self.sessionRunning:
            if self.engine.ready_for_session:
                self.status_text = "학습 시작 가능"
                self.status_detail = "기준 자세 설정이 완료되었습니다."
            return
        label, detail = STATE_TEXT.get(decision.effective_state, ("측정 중", ""))
        self.status_text = label
        self.status_detail = detail if decision.effective_state == EffectiveState.BREAK else RAW_TEXT.get(decision.raw_state, detail)

    def _publish_frame(self, frame) -> None:
        rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
        height, width, channels = rgb.shape
        image = QImage(rgb.data, width, height, channels * width, QImage.Format_RGB888).copy()
        self.image_provider.set_image(image)
        self.frame_version += 1
        self.frameChanged.emit()

    def _pomodoro_config(self) -> PomodoroConfig:
        return PomodoroConfig(
            focus_minutes=self.settings.pomodoro_focus_minutes,
            short_break_minutes=self.settings.pomodoro_short_break_minutes,
            long_break_minutes=self.settings.pomodoro_long_break_minutes,
            cycles=self.settings.pomodoro_cycles,
            auto_start_break=self.settings.pomodoro_auto_start_break,
            auto_start_next_focus=self.settings.pomodoro_auto_start_next,
        )

    def _set_session_break(
        self,
        should_break: bool,
        timestamp: Optional[float] = None,
    ) -> None:
        changed = False
        if should_break and self.session.app_state == AppState.RUNNING:
            self.session.toggle_break()
            changed = True
        elif not should_break and self.session.app_state == AppState.BREAK:
            self.session.toggle_break()
            changed = True
        now = time.monotonic() if timestamp is None else timestamp
        if changed:
            self._invalidate_observation(now)
            self._record_unavailable(ObservationState.LOW_CONFIDENCE, now)
        self.app_usage_tracker.set_active(
            self.session.app_state == AppState.RUNNING,
            now,
        )
        self.engine.reset_runtime_state()

    def _update_pomodoro(self, timestamp: float) -> None:
        if self.session.session_mode != "pomodoro" or not self.sessionRunning:
            return
        update = self.pomodoro.update(timestamp)
        if update.just_changed:
            self.session.pomodoro_cycles_completed = update.completed_cycles
            self._set_session_break(update.phase != PomodoroPhase.FOCUS, timestamp)
            self.break_started_at = None
            self.break_remaining = 0
            self.alertRequested.emit()
            if update.phase == PomodoroPhase.COMPLETED:
                self.feedback.emit("뽀모도로를 완료했습니다.")
                self.endSession()
                return
            self.feedback.emit(self.pomodoroPhaseLabel + " 단계로 전환했습니다.")
