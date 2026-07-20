from __future__ import annotations

import calendar
import json
import sys
import time
import math
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

import cv2
from PySide6.QtCore import (
    QDate,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Signal,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QIntValidator,
    QPainter,
    QPen,
    QPixmap,
    QTextCharFormat,
)
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGridLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from onf_v2.app.camera_service import CameraService
from onf_v2.app.alert_controller import AttentionAlertController
from onf_v2.app.alert_sounds import (
    ALERT_SOUND_OPTIONS,
    DEFAULT_ALERT_SOUND,
    ensure_alert_sound_files,
)
from onf_v2.app.break_timer import BreakTimer
from onf_v2.app.pomodoro import (
    PomodoroConfig,
    PomodoroController,
    PomodoroPhase,
)
from onf_v2.app.session_manager import SessionManager
from onf_v2.app.settings_store import SettingsStore, UserSettings
from onf_v2.core.attention_engine import AttentionEngine
from onf_v2.core.calibration import CalibrationProgress
from onf_v2.core.face_analyzer import FaceAnalyzer
from onf_v2.core.models import (
    AppState,
    CalibrationStatus,
    EffectiveState,
    FrameObservation,
    Mode,
    ObservationState,
)


STATE_LABEL = {
    EffectiveState.FOCUS: ("집중 중", "#03C75A"),
    EffectiveState.NON_FOCUS: ("주의 이탈", "#F04452"),
    EffectiveState.BREAK: ("휴식 중", "#6B7684"),
    EffectiveState.UNSCORED: ("측정 불안정", "#6D5DF7"),
    EffectiveState.ABSENT_PENDING: ("얼굴 없음", "#F59E0B"),
}


APP_STATE_BADGE = {
    AppState.PREVIEW: ("준비 중", "#6B7684", "#F2F4F6", "#E5E8EB"),
    AppState.CALIBRATING: ("기준 설정 중", "#B45309", "#FFF7E6", "#FDE1A7"),
    AppState.READY: ("시작 가능", "#03A64A", "#E9FAF1", "#BDEED1"),
    AppState.RUNNING: ("집중 측정 중", "#03A64A", "#E9FAF1", "#BDEED1"),
    AppState.BREAK: ("휴식 중", "#1B64DA", "#EAF2FF", "#CFE0FF"),
    AppState.RESULT: ("세션 저장 완료", "#1B64DA", "#EAF2FF", "#CFE0FF"),
    AppState.ERROR: ("확인 필요", "#D92D3A", "#FFF1F2", "#FFD4D8"),
}


REASON_TEXT = {
    ObservationState.NORMAL_VIEW: "화면 작업 영역을 안정적으로 보고 있습니다.",
    ObservationState.GAZE_AWAY: "시선이 작업 영역을 벗어났습니다. 평소 작업 위치를 바라봐 주세요.",
    ObservationState.HEAD_SIDE: "고개가 기준 자세에서 벗어났습니다. 화면 또는 필기 위치로 돌아와 주세요.",
    ObservationState.HEAD_DOWN: "고개가 허용된 자세보다 아래로 벗어났습니다. 기준 자세로 돌아와 주세요.",
    ObservationState.HEAD_UP: "고개가 허용된 자세보다 위로 벗어났습니다. 기준 자세로 돌아와 주세요.",
    ObservationState.EYES_CLOSED: "눈 감김이 오래 지속되고 있습니다. 눈을 뜨면 자동으로 복귀합니다.",
    ObservationState.NO_FACE: "얼굴을 찾지 못했습니다. 얼굴 전체와 양쪽 눈이 보이게 해주세요.",
    ObservationState.MULTIPLE_FACES: "여러 얼굴이 감지됐습니다. 화면에는 한 사람만 보이게 해주세요.",
    ObservationState.LOW_CONFIDENCE: "얼굴 추적이 불안정합니다. 조명과 얼굴 노출 상태를 확인하세요.",
    ObservationState.PROCESSING_ERROR: "얼굴 분석이 중단됐습니다. 카메라를 새로고침해 주세요.",
    ObservationState.CAMERA_ERROR: "카메라 프레임을 받지 못해 자동 재연결을 시도합니다.",
    ObservationState.NOT_CALIBRATED: "필요한 화면·필기 기준 자세를 설정하세요.",
}


class TimelineChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.slots: List[Tuple[Optional[float], EffectiveState]] = []
        self.setMinimumHeight(74)

    def set_slots(self, slots: List[Tuple[Optional[float], EffectiveState]]) -> None:
        self.slots = [
            (None if rate is None else min(1.0, max(0.0, rate)), state)
            for rate, state in slots
        ]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F8FAFC"))
        rect = self.rect().adjusted(12, 10, -12, -20)

        if not self.slots:
            painter.setPen(QColor("#8B95A1"))
            painter.drawText(rect, Qt.AlignCenter, "세션을 시작하면 최근 집중 흐름이 표시됩니다.")
            painter.end()
            return

        bar_width = 6
        gap = 3
        capacity = max(1, int(rect.width() / (bar_width + gap)))
        visible_slots = self.slots[-capacity:]
        x = rect.left()

        painter.setPen(QColor("#E5E8EB"))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        for rate, state in visible_slots:
            if rate is None:
                marker_height = 5.0
                marker_color = (
                    QColor("#B0B8C1")
                    if state == EffectiveState.BREAK
                    else QColor("#D3CFF4")
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(marker_color)
                painter.drawRoundedRect(
                    QRectF(x, rect.bottom() - marker_height, bar_width, marker_height),
                    2.5,
                    2.5,
                )
                x += bar_width + gap
                continue
            bar_height = max(4.0, rect.height() * rate)
            top = rect.bottom() - bar_height
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._rate_color(rate))
            painter.drawRoundedRect(QRectF(x, top, bar_width, bar_height), 3, 3)
            x += bar_width + gap

        painter.setPen(QColor("#6B7684"))
        painter.drawText(rect.left(), self.rect().bottom() - 4, "이전")
        painter.drawText(rect.right() - 28, self.rect().bottom() - 4, "현재")
        painter.end()

    @staticmethod
    def _rate_color(rate: float) -> QColor:
        red = (240, 68, 82)
        yellow = (245, 185, 66)
        green = (3, 199, 90)
        if rate < 0.5:
            t = rate / 0.5
            start, end = red, yellow
        else:
            t = (rate - 0.5) / 0.5
            start, end = yellow, green
        return QColor(
            int(start[0] + (end[0] - start[0]) * t),
            int(start[1] + (end[1] - start[1]) * t),
            int(start[2] + (end[2] - start[2]) * t),
        )


class PlannerScheduleEditor(QWidget):
    scheduleCommitted = Signal(object, int, object)

    def __init__(
        self,
        start_minute: Optional[int] = None,
        end_minute: Optional[int] = None,
        duration_minutes: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PlannerScheduleEditor")
        self.groups = {}
        self.generated_key: Optional[str] = None
        self.explicit_order: List[str] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        for key, label, duration in (
            ("start", "시작", False),
            ("end", "종료", False),
            ("duration", "소요", True),
        ):
            group = QFrame()
            group.setObjectName("PlannerInlineTimeGroup")
            group_layout = QHBoxLayout(group)
            group_layout.setContentsMargins(6, 4, 6, 4)
            group_layout.setSpacing(4)
            name = QLabel(label)
            name.setObjectName("PlannerInlineTimeLabel")
            hour = QLineEdit()
            hour.setObjectName("PlannerInlineTimeNumber")
            hour.setAlignment(Qt.AlignCenter)
            hour.setMaxLength(2)
            hour.setFixedWidth(34)
            hour.setPlaceholderText("-")
            hour.setValidator(QIntValidator(0, 24 if duration else 23, hour))
            minute = QLineEdit()
            minute.setObjectName("PlannerInlineTimeNumber")
            minute.setAlignment(Qt.AlignCenter)
            minute.setMaxLength(2)
            minute.setFixedWidth(34)
            minute.setPlaceholderText("-")
            minute.setValidator(QIntValidator(0, 59, minute))
            hour_suffix = QLabel("시간" if duration else "시")
            hour_suffix.setObjectName("PlannerInlineTimeSuffix")
            minute_suffix = QLabel("분")
            minute_suffix.setObjectName("PlannerInlineTimeSuffix")
            group_layout.addWidget(name)
            group_layout.addWidget(hour)
            group_layout.addWidget(hour_suffix)
            group_layout.addWidget(minute)
            group_layout.addWidget(minute_suffix)
            layout.addWidget(group)
            self.groups[key] = (group, hour, minute)

        self.first_field = self.groups["start"][1]
        self.last_field = self.groups["duration"][2]
        self.set_values(start_minute, end_minute, duration_minutes)
        for key, (_group, hour, minute) in self.groups.items():
            for field in (hour, minute):
                field.textEdited.connect(
                    lambda _text, field_key=key: self._user_edited(field_key)
                )
                field.editingFinished.connect(self._commit_current_values)

    def set_values(
        self,
        start_minute: Optional[int],
        end_minute: Optional[int],
        duration_minutes: int,
    ) -> None:
        self._set_group_value("start", start_minute)
        self._set_group_value("end", end_minute)
        self._set_group_value(
            "duration",
            duration_minutes if duration_minutes > 0 else None,
        )
        if start_minute is not None and duration_minutes > 0:
            self.explicit_order = ["start", "duration"]
        elif start_minute is not None and end_minute is not None:
            self.explicit_order = ["start", "end"]
        elif end_minute is not None and duration_minutes > 0:
            self.explicit_order = ["end", "duration"]
        else:
            self.explicit_order = [
                key for key in self.groups if self._group_has_text(key)
            ]
        self.generated_key = None
        self._set_calculated_style(None)
        self._set_invalid_style([])

    def clear(self) -> None:
        self.explicit_order.clear()
        self.generated_key = None
        for key in self.groups:
            self._set_group_value(key, None)
        self._set_calculated_style(None)
        self._set_invalid_style([])

    def values(self) -> tuple[dict[str, Optional[int]], List[str]]:
        values = {
            "start": self._parse_clock_parts(
                self.groups["start"][1].text(),
                self.groups["start"][2].text(),
            ),
            "end": self._parse_clock_parts(
                self.groups["end"][1].text(),
                self.groups["end"][2].text(),
            ),
            "duration": self._parse_duration_parts(
                self.groups["duration"][1].text(),
                self.groups["duration"][2].text(),
            ),
        }
        invalid = [
            key
            for key in self.groups
            if self._group_has_text(key) and values[key] is None
        ]
        return values, invalid

    def _group_has_text(self, key: str) -> bool:
        _group, hour, minute = self.groups[key]
        return bool(hour.text().strip() or minute.text().strip())

    def _set_group_value(self, key: str, value: Optional[int]) -> None:
        _group, hour, minute = self.groups[key]
        hour.blockSignals(True)
        minute.blockSignals(True)
        if value is None:
            hour.clear()
            minute.clear()
        else:
            whole_hours, remaining_minutes = divmod(value, 60)
            hour.setText(str(whole_hours))
            minute.setText(f"{remaining_minutes:02d}")
        hour.blockSignals(False)
        minute.blockSignals(False)

    def _user_edited(self, key: str) -> None:
        if key in self.explicit_order:
            self.explicit_order.remove(key)
        if self._group_has_text(key):
            self.explicit_order.append(key)
        self.generated_key = None
        self._recalculate()

    def _recalculate(self) -> None:
        values, invalid = self.values()
        self._set_invalid_style(invalid)
        valid_order = [
            key for key in self.explicit_order if values.get(key) is not None
        ]
        if len(valid_order) < 2:
            self.generated_key = None
            self._set_calculated_style(None)
            return
        source_keys = valid_order[-2:]
        target_key = next(
            key
            for key in ("start", "end", "duration")
            if key not in source_keys
        )
        calculated = self._calculate_value(target_key, values)
        if calculated is None:
            return
        self._set_group_value(target_key, calculated)
        self.generated_key = target_key
        self._set_calculated_style(target_key)
        for field in self.groups[target_key][1:]:
            field.setToolTip("자동 계산값입니다. Enter 또는 다른 칸으로 이동하면 확정됩니다.")

    def _commit_current_values(self) -> None:
        self.generated_key = None
        self._set_calculated_style(None)
        values, invalid = self.values()
        self._set_invalid_style(invalid)
        if invalid:
            return
        self.scheduleCommitted.emit(
            values["start"],
            values["duration"] or 0,
            values["end"],
        )

    def _set_calculated_style(self, key: Optional[str]) -> None:
        for field_key, (_group, hour, minute) in self.groups.items():
            for field in (hour, minute):
                field.setProperty("calculated", field_key == key)
                field.style().unpolish(field)
                field.style().polish(field)

    def _set_invalid_style(self, invalid: List[str]) -> None:
        for key, (_group, hour, minute) in self.groups.items():
            for field in (hour, minute):
                field.setProperty("invalid", key in invalid)
                field.style().unpolish(field)
                field.style().polish(field)

    @staticmethod
    def _parse_clock_parts(hour_text: str, minute_text: str) -> Optional[int]:
        hour_clean = hour_text.strip()
        minute_clean = minute_text.strip()
        if not hour_clean and not minute_clean:
            return None
        if not hour_clean or not hour_clean.isdigit():
            return None
        if minute_clean and not minute_clean.isdigit():
            return None
        hour = int(hour_clean)
        minute = int(minute_clean) if minute_clean else 0
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            return None
        return hour * 60 + minute

    @staticmethod
    def _parse_duration_parts(hour_text: str, minute_text: str) -> Optional[int]:
        hour_clean = hour_text.strip()
        minute_clean = minute_text.strip()
        if not hour_clean and not minute_clean:
            return None
        if hour_clean and not hour_clean.isdigit():
            return None
        if minute_clean and not minute_clean.isdigit():
            return None
        hour = int(hour_clean) if hour_clean else 0
        minute = int(minute_clean) if minute_clean else 0
        if not 0 <= minute <= 59:
            return None
        duration = hour * 60 + minute
        return duration if 1 <= duration <= 1440 else None

    @staticmethod
    def _calculate_value(
        target: str,
        values: dict[str, Optional[int]],
    ) -> Optional[int]:
        start = values.get("start")
        end = values.get("end")
        duration = values.get("duration")
        if target == "end" and start is not None and duration is not None:
            return (start + duration) % (24 * 60)
        if target == "start" and end is not None and duration is not None:
            return (end - duration) % (24 * 60)
        if target == "duration" and start is not None and end is not None:
            difference = (end - start) % (24 * 60)
            return difference if difference > 0 else 24 * 60
        return None


class DailyTenMinuteTimetable(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.slots: List[
            Tuple[Optional[float], Optional[EffectiveState]]
        ] = [(None, None)] * 144
        self.start_hour = 4
        self.current_slot: Optional[int] = None
        self.planned_slots: set[int] = set()
        self.setMinimumSize(250, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_slots(
        self,
        slots: List[Tuple[Optional[float], Optional[EffectiveState]]],
        start_hour: int,
        current_slot: Optional[int] = None,
        planned_slots: Optional[set[int]] = None,
    ) -> None:
        padded = list(slots[:144])
        padded.extend([(None, None)] * (144 - len(padded)))
        self.slots = padded
        self.start_hour = start_hour % 24
        self.current_slot = current_slot
        self.planned_slots = set(planned_slots or ())
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        rect = self.rect().adjusted(4, 4, -4, -4)
        label_width = 34.0
        grid_left = rect.left() + label_width
        grid_width = max(60.0, rect.width() - label_width)
        row_height = rect.height() / 24.0
        cell_width = grid_width / 6.0

        painter.setFont(QFont("Segoe UI", 8, QFont.Medium))
        for row in range(24):
            y = rect.top() + row * row_height
            hour = (self.start_hour + row) % 24
            painter.setPen(QColor("#8B95A1"))
            painter.drawText(
                QRectF(rect.left(), y, label_width - 7, row_height),
                Qt.AlignRight | Qt.AlignVCenter,
                f"{hour:02d}",
            )
            for column in range(6):
                slot_index = row * 6 + column
                rate, state = self.slots[slot_index]
                cell = QRectF(
                    grid_left + column * cell_width + 1.5,
                    y + 1.5,
                    max(2.0, cell_width - 3.0),
                    max(2.0, row_height - 3.0),
                )
                color = QColor("#F7F9FC")
                if rate is not None:
                    color = TimelineChart._rate_color(rate)
                elif state == EffectiveState.BREAK:
                    color = QColor("#B0B8C1")
                elif state == EffectiveState.UNSCORED:
                    color = QColor("#D8D2F2")
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(cell, 2.5, 2.5)
                if slot_index in self.planned_slots:
                    planned_pen = QPen(QColor("#7C8DA6"), 1.25, Qt.DashLine)
                    planned_pen.setDashPattern([2.5, 2.0])
                    painter.setPen(planned_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(
                        cell.adjusted(0.5, 0.5, -0.5, -0.5),
                        2.5,
                        2.5,
                    )
                if slot_index == self.current_slot:
                    painter.setPen(QPen(QColor("#3182F6"), 1.5))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(cell.adjusted(-0.5, -0.5, 0.5, 0.5), 3, 3)

            painter.setPen(QColor("#EEF1F4"))
            painter.drawLine(
                grid_left,
                y + row_height,
                rect.right(),
                y + row_height,
            )
        painter.end()


class MonthlyActivityHeatmap(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.days: List[tuple[int, float]] = []
        self.first_weekday = 0
        self.empty_message = "이번 달 학습 기록이 없습니다."
        self.setMinimumHeight(156)

    def set_days(
        self,
        days: List[tuple[int, float]],
        first_weekday: int,
        empty_message: str,
    ) -> None:
        self.days = days
        self.first_weekday = first_weekday
        self.empty_message = empty_message
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F8FAFC"))
        rect = self.rect().adjusted(18, 12, -18, -12)
        max_focus = max((seconds for _day, seconds in self.days), default=0.0)

        if max_focus <= 0:
            painter.setPen(QColor("#8B95A1"))
            painter.drawText(rect, Qt.AlignCenter, self.empty_message)
            painter.end()
            return

        weekdays = ("월", "화", "수", "목", "금", "토", "일")
        gap = 6.0
        label_height = 20.0
        row_count = max(1, math.ceil((self.first_weekday + len(self.days)) / 7))
        cell_width = min(76.0, (rect.width() - gap * 6) / 7)
        cell_height = min(
            23.0,
            (rect.height() - label_height - gap * (row_count - 1)) / row_count,
        )
        grid_width = cell_width * 7 + gap * 6
        left = rect.left() + max(0.0, (rect.width() - grid_width) / 2)
        top = rect.top() + label_height

        painter.setPen(QColor("#8B95A1"))
        for column, label in enumerate(weekdays):
            x = left + column * (cell_width + gap)
            painter.drawText(
                QRectF(x, rect.top(), cell_width, label_height),
                Qt.AlignCenter,
                label,
            )

        for day, focus_seconds in self.days:
            slot = self.first_weekday + day - 1
            row, column = divmod(slot, 7)
            x = left + column * (cell_width + gap)
            y = top + row * (cell_height + gap)
            intensity = focus_seconds / max_focus
            color = QColor("#EEF2F6")
            if focus_seconds > 0:
                color = self._activity_color(intensity)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(x, y, cell_width, cell_height), 5, 5)
            painter.setPen(QColor("#FFFFFF") if intensity >= 0.55 else QColor("#4E5968"))
            painter.drawText(
                QRectF(x, y, cell_width, cell_height),
                Qt.AlignCenter,
                str(day),
            )
        painter.end()

    @staticmethod
    def _activity_color(intensity: float) -> QColor:
        start = (203, 242, 220)
        end = (3, 166, 74)
        value = min(1.0, max(0.15, intensity))
        return QColor(
            int(start[0] + (end[0] - start[0]) * value),
            int(start[1] + (end[1] - start[1]) * value),
            int(start[2] + (end[2] - start[2]) * value),
        )


class PeriodTrendChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.points: List[tuple[str, float]] = []
        self.empty_message = "저장된 기록이 없습니다."
        self.setMinimumHeight(180)

    def set_points(self, points: List[tuple[str, float]], empty_message: str) -> None:
        self.points = [(label, min(1.0, max(0.0, rate))) for label, rate in points]
        self.empty_message = empty_message
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F8FAFC"))
        rect = self.rect().adjusted(18, 16, -18, -38)

        visible = [(label, rate) for label, rate in self.points if rate > 0]
        if not visible:
            painter.setPen(QColor("#8B95A1"))
            painter.drawText(rect, Qt.AlignCenter, self.empty_message)
            painter.end()
            return

        max_slots = min(len(self.points), 31)
        points = self.points[-max_slots:]
        bar_layout = self._bar_layout(
            float(rect.left()),
            float(rect.width()),
            len(points),
        )
        slot_width = rect.width() / max(1, len(points))

        painter.setPen(QColor("#E5E8EB"))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        for index, ((label, rate), (x, bar_width)) in enumerate(
            zip(points, bar_layout)
        ):
            bar_height = max(4.0, rect.height() * rate)
            top = rect.bottom() - bar_height
            painter.setPen(Qt.NoPen)
            painter.setBrush(TimelineChart._rate_color(rate))
            painter.drawRoundedRect(QRectF(x, top, bar_width, bar_height), 4, 4)
            if index == 0 or index == len(points) - 1 or len(points) <= 8:
                painter.setPen(QColor("#6B7684"))
                painter.drawText(
                    QRectF(
                        rect.left() + index * slot_width,
                        rect.bottom() + 3,
                        slot_width,
                        31,
                    ),
                    Qt.AlignCenter,
                    label,
                )

        painter.end()

    @staticmethod
    def _bar_layout(
        left: float,
        available_width: float,
        count: int,
    ) -> List[tuple[float, float]]:
        if count <= 0 or available_width <= 0:
            return []
        slot_width = available_width / count
        bar_width = min(18.0, max(4.0, slot_width * 0.72))
        return [
            (
                left + index * slot_width + (slot_width - bar_width) / 2.0,
                bar_width,
            )
            for index in range(count)
        ]


class DailySummaryDonut(QWidget):
    COLORS = ("#03C75A", "#F04452", "#B0B8C1", "#7C6EE6")

    def __init__(self) -> None:
        super().__init__()
        self.values = (0.0, 0.0, 0.0, 0.0)
        self.setMinimumHeight(185)

    def set_values(
        self,
        focus: float,
        non_focus: float,
        break_seconds: float,
        unscored: float,
    ) -> None:
        self.values = (
            max(0.0, focus),
            max(0.0, non_focus),
            max(0.0, break_seconds),
            max(0.0, unscored),
        )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        diameter = min(154.0, self.width() - 34.0, self.height() - 24.0)
        ring = QRectF(
            (self.width() - diameter) / 2,
            (self.height() - diameter) / 2,
            diameter,
            diameter,
        )
        total = sum(self.values)
        painter.setPen(QPen(QColor("#EEF2F6"), 18, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, 0, 360 * 16)
        if total > 0:
            start_angle = 90 * 16
            for value, color in zip(self.values, self.COLORS):
                if value <= 0:
                    continue
                span = int(360 * 16 * value / total)
                painter.setPen(
                    QPen(QColor(color), 18, Qt.SolidLine, Qt.RoundCap)
                )
                painter.drawArc(ring, start_angle, -span)
                start_angle -= span

        study_seconds = self.values[0] + self.values[1]
        painter.setPen(QColor("#8B95A1"))
        painter.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        painter.drawText(
            QRectF(ring.left(), ring.center().y() - 28, ring.width(), 22),
            Qt.AlignCenter,
            "공부시간",
        )
        painter.setPen(QColor("#191F28"))
        painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
        painter.drawText(
            QRectF(ring.left(), ring.center().y() - 4, ring.width(), 38),
            Qt.AlignCenter,
            self._duration(study_seconds),
        )
        painter.end()

    @staticmethod
    def _duration(seconds: float) -> str:
        minutes = int(seconds // 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}시간 {minutes}분" if hours else f"{minutes}분"


class HourlyStudyChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.points: List[tuple[str, float, float, float]] = []
        self.setMinimumHeight(185)

    def set_points(self, points: List[tuple[str, float, float, float]]) -> None:
        self.points = points
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F8FAFC"))
        rect = self.rect().adjusted(16, 14, -16, -24)
        if not any(study > 0 or rest > 0 for _label, study, _rate, rest in self.points):
            painter.setPen(QColor("#8B95A1"))
            painter.drawText(rect, Qt.AlignCenter, "선택한 날짜의 학습 기록이 없습니다.")
            painter.end()
            return

        painter.setPen(QColor("#E5E8EB"))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        count = max(1, len(self.points))
        gap = 4.0
        bar_width = max(5.0, min(14.0, (rect.width() - gap * (count - 1)) / count))
        total_width = bar_width * count + gap * (count - 1)
        x = rect.left() + max(0.0, (rect.width() - total_width) / 2)
        for index, (label, study, rate, rest) in enumerate(self.points):
            value = study if study > 0 else rest
            height = max(0.0, rect.height() * min(1.0, value / 3600.0))
            if value > 0:
                color = (
                    TimelineChart._rate_color(rate)
                    if study > 0
                    else QColor("#B0B8C1")
                )
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(
                    QRectF(x, rect.bottom() - max(4.0, height), bar_width, max(4.0, height)),
                    3,
                    3,
                )
            if index % 3 == 0:
                painter.setPen(QColor("#8B95A1"))
                painter.drawText(
                    QRectF(x - 7, rect.bottom() + 3, bar_width + 14, 18),
                    Qt.AlignCenter,
                    label,
                )
            x += bar_width + gap
        painter.end()


class PomodoroDial(QWidget):
    PHASE_TEXT = {
        PomodoroPhase.IDLE: "뽀모도로 준비",
        PomodoroPhase.FOCUS: "집중 시간",
        PomodoroPhase.PAUSED: "일시정지",
        PomodoroPhase.SHORT_BREAK: "짧은 휴식",
        PomodoroPhase.LONG_BREAK: "긴 휴식",
        PomodoroPhase.WAITING_NEXT: "다음 집중 대기",
        PomodoroPhase.COMPLETED: "오늘의 뽀모도로 완료",
    }

    def __init__(self) -> None:
        super().__init__()
        self.phase = PomodoroPhase.IDLE
        self.remaining_seconds = 25 * 60.0
        self.progress = 1.0
        self.cycle = 1
        self.total_cycles = 4
        self.completed_cycles = 0
        self.session_ended = False
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(
        self,
        phase: PomodoroPhase,
        remaining_seconds: float,
        progress: float,
        cycle: int,
        total_cycles: int,
        completed_cycles: int,
    ) -> None:
        self.phase = phase
        self.remaining_seconds = max(0.0, remaining_seconds)
        self.progress = min(1.0, max(0.0, progress))
        self.cycle = max(1, cycle)
        self.total_cycles = max(1, total_cycles)
        self.completed_cycles = max(0, completed_cycles)
        self.session_ended = False
        self.update()

    def show_stopped(self, total_cycles: int, completed_cycles: int) -> None:
        self.phase = PomodoroPhase.IDLE
        self.remaining_seconds = 0.0
        self.progress = 0.0
        self.cycle = max(1, min(total_cycles, completed_cycles + 1))
        self.total_cycles = max(1, total_cycles)
        self.completed_cycles = max(0, completed_cycles)
        self.session_ended = True
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F8FAFC"))

        diameter = min(238.0, float(self.width() - 54), float(self.height() - 92))
        ring = QRectF(
            (self.width() - diameter) / 2,
            max(18.0, (self.height() - diameter) / 2 - 20),
            diameter,
            diameter,
        )
        center = ring.center()
        color = QColor("#03C75A")
        if self.phase in (
            PomodoroPhase.SHORT_BREAK,
            PomodoroPhase.LONG_BREAK,
            PomodoroPhase.WAITING_NEXT,
        ):
            color = QColor("#3182F6")
        elif self.phase == PomodoroPhase.PAUSED:
            color = QColor("#8B95A1")
        elif self.phase == PomodoroPhase.COMPLETED:
            color = QColor("#1B64DA")

        painter.setPen(QPen(QColor("#E5E8EB"), 15, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, 0, 360 * 16)
        painter.setPen(QPen(color, 15, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(ring, 90 * 16, -int(360 * 16 * self.progress))

        total = int(math.ceil(self.remaining_seconds))
        timer_text = f"{total // 60:02d}:{total % 60:02d}"
        painter.setPen(QColor("#191F28"))
        painter.setFont(QFont("Segoe UI", 36, QFont.Bold))
        painter.drawText(
            QRectF(ring.left(), center.y() - 39, ring.width(), 60),
            Qt.AlignCenter,
            timer_text,
        )
        painter.setPen(QColor("#6B7684"))
        painter.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        painter.drawText(
            QRectF(ring.left(), center.y() + 17, ring.width(), 26),
            Qt.AlignCenter,
            "세션 종료" if self.session_ended else self.PHASE_TEXT[self.phase],
        )

        info_top = ring.bottom() + 13
        painter.setPen(QColor("#191F28"))
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(
            QRectF(12, info_top, self.width() - 24, 26),
            Qt.AlignCenter,
            f"{self.cycle} / {self.total_cycles}회차",
        )
        dots_width = max(10.0, self.total_cycles * 20.0 - 10.0)
        dot_x = (self.width() - dots_width) / 2
        dot_y = info_top + 34
        for index in range(self.total_cycles):
            dot_color = (
                QColor("#03C75A")
                if index < self.completed_cycles
                else QColor("#DDE3EA")
            )
            if index == self.cycle - 1 and self.phase != PomodoroPhase.COMPLETED:
                dot_color = color
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QRectF(dot_x + index * 20, dot_y, 10, 10))
        painter.end()


class CalibrationProgressButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.progress = 0.0

    def set_progress(self, progress: float) -> None:
        normalized = min(1.0, max(0.0, float(progress)))
        if abs(normalized - self.progress) < 1e-6:
            return
        self.progress = normalized
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self.property("calibrationState") != "collecting":
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QRectF(7, self.height() - 5, max(0, self.width() - 14), 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#CFE0FF"))
        painter.drawRoundedRect(track, 1.5, 1.5)
        if self.progress > 0:
            fill = QRectF(track.left(), track.top(), track.width() * self.progress, 3)
            painter.setBrush(QColor("#3182F6"))
            painter.drawRoundedRect(fill, 1.5, 1.5)
        painter.end()


class GuidedCalibrationOverlay(QWidget):
    TARGET_POSITIONS = {
        "center": (0.50, 0.50),
        "left": (0.20, 0.50),
        "right": (0.80, 0.50),
        "up": (0.50, 0.24),
        "down": (0.50, 0.76),
    }
    TARGET_LABELS = {
        "center": "가운데",
        "left": "왼쪽",
        "right": "오른쪽",
        "up": "위쪽",
        "down": "아래쪽",
        "natural": "자연스럽게",
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.target_key = ""
        self.target_progress = 0.0
        self.target_index = 0
        self.total_targets = 0
        self.is_writing = False
        self.target_area = QRectF()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.hide()

    def set_target_area(self, area: QRectF) -> None:
        self.target_area = area
        self.update()

    def set_stage(
        self,
        target_key: str,
        target_progress: float,
        target_index: int,
        total_targets: int,
        is_writing: bool,
    ) -> None:
        self.target_key = target_key
        self.target_progress = min(1.0, max(0.0, target_progress))
        self.target_index = target_index
        self.total_targets = total_targets
        self.is_writing = is_writing
        self.show()
        self.raise_()
        self.update()

    def clear_stage(self) -> None:
        self.target_key = ""
        self.hide()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self.target_key:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        area = self.target_area
        if area.isEmpty():
            area = QRectF(0, 0, self.width(), self.height())
        banner_width = min(560.0, max(320.0, area.width() - 36.0))
        banner = QRectF(area.center().x() - banner_width / 2, area.top() + 14, banner_width, 76)
        painter.setPen(QPen(QColor(207, 224, 255, 230), 1))
        painter.setBrush(QColor(255, 255, 255, 242))
        painter.drawRoundedRect(banner, 8, 8)

        label = self.TARGET_LABELS.get(self.target_key, "안내 위치")
        step = (
            f"{self.target_index + 1}/{self.total_targets}"
            if self.total_targets
            else ""
        )
        if self.is_writing:
            instruction = (
                "필기 영역을 평소처럼 자연스럽게 둘러봐 주세요."
                if self.target_key == "natural"
                else f"종이의 {label} 영역을 자연스럽게 바라봐 주세요."
            )
        else:
            instruction = (
                "화면 작업 영역을 평소처럼 자연스럽게 둘러봐 주세요."
                if self.target_key == "natural"
                else f"화면의 {label} 표시를 자연스럽게 바라봐 주세요."
            )
        painter.setPen(QColor("#191F28"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
        painter.drawText(
            QRectF(banner.left() + 18, banner.top() + 11, banner.width() - 36, 26),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"{step}  {label}",
        )
        painter.setPen(QColor("#4E5968"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            QRectF(banner.left() + 18, banner.top() + 39, banner.width() - 36, 24),
            Qt.AlignLeft | Qt.AlignVCenter,
            instruction,
        )

        track = QRectF(banner.left() + 18, banner.bottom() - 8, banner.width() - 36, 3)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#DDE3EA"))
        painter.drawRoundedRect(track, 1.5, 1.5)
        painter.setBrush(QColor("#3182F6"))
        painter.drawRoundedRect(
            QRectF(track.left(), track.top(), track.width() * self.target_progress, 3),
            1.5,
            1.5,
        )

        if not self.is_writing and self.target_key in self.TARGET_POSITIONS:
            x_ratio, y_ratio = self.TARGET_POSITIONS[self.target_key]
            center = QPoint(
                int(area.left() + area.width() * x_ratio),
                int(area.top() + area.height() * y_ratio),
            )
            painter.setPen(QPen(QColor(255, 255, 255, 235), 9))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(center, 24, 24)
            painter.setPen(QPen(QColor("#3182F6"), 4))
            painter.drawEllipse(center, 24, 24)
            painter.setPen(QPen(QColor("#3182F6"), 2))
            painter.drawLine(center.x() - 34, center.y(), center.x() - 12, center.y())
            painter.drawLine(center.x() + 12, center.y(), center.x() + 34, center.y())
            painter.drawLine(center.x(), center.y() - 34, center.x(), center.y() - 12)
            painter.drawLine(center.x(), center.y() + 12, center.x(), center.y() + 34)
        painter.end()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("집중 학습")
        self.resize(1280, 720)
        self.setMinimumSize(1020, 680)

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.camera = CameraService(index=self.settings.camera_index)
        self.analyzer: Optional[FaceAnalyzer] = None
        self.analysis_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="onf-face-analysis",
        )
        self.camera_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="onf-camera-open",
        )
        self.setup_future: Optional[Future] = None
        self.camera_open_future: Optional[Future] = None
        self.camera_open_index = self.settings.camera_index
        self.camera_open_automatic = False
        self.camera_reconnect_attempt = 0
        self.camera_next_reconnect_at = 0.0
        self.camera_reconnect_delays = (1.0, 2.0, 5.0)
        self.camera_available = False
        self.analysis_future: Optional[Future] = None
        self.analysis_interval_seconds = 1.0 / 15.0
        self.last_analysis_submitted_at = 0.0
        self.last_analysis_sequence = -1
        self.preview_interval_seconds = 1.0 / 20.0
        self.last_preview_rendered_at = 0.0
        self.camera_error_interval_seconds = 0.25
        self.last_camera_error_processed_at = 0.0
        self.engine = AttentionEngine(mode=Mode(self.settings.mode))
        self.engine.set_mode(Mode(self.settings.mode))
        self.engine.set_work_mode(self.settings.work_mode)
        self.engine.policy.absence_to_break_seconds = (
            self.settings.absence_to_break_minutes * 60.0
        )
        self.alert_controller = AttentionAlertController(
            threshold_seconds=float(self.settings.attention_alert_seconds)
        )
        self.break_timer = BreakTimer(
            duration_seconds=float(self.settings.break_duration_minutes * 60)
        )
        self.pomodoro = PomodoroController(self._pomodoro_config())
        self.session = SessionManager()
        self.database = self.session.recorder.database
        self.latest_frame = None
        self.latest_observation: Optional[FrameObservation] = None
        self.latest_decision = None
        self.last_logged_effective_state: Optional[EffectiveState] = None
        self.last_calibration_status_logged: Optional[CalibrationStatus] = None
        self.last_error = ""
        self.records_period = "day"
        self.records_selected_date = datetime.now().date()
        self.planner_selected_date = self._study_date_for_datetime(datetime.now())
        self.planner_highlighted_dates: set[date] = set()
        self.last_planner_timeline_refresh_at = 0.0
        self.active_task_id: Optional[int] = None
        self.active_task_title = ""
        self.sound_effect: Optional[QSoundEffect] = None
        self.sound_effects: dict[str, QSoundEffect] = {}
        self.pending_sound_volume: Optional[int] = None
        self.camera_preview_hidden = self.settings.camera_preview_hidden
        self._last_app_badge_state: Optional[Tuple[AppState, bool]] = None

        self._build_ui()
        self._connect_actions()
        self._apply_styles()
        self._update_calibration_controls()
        self._set_app_state_badge(AppState.PREVIEW)
        self.volume_preview_timer = QTimer(self)
        self.volume_preview_timer.setSingleShot(True)
        self.volume_preview_timer.setInterval(180)
        self.volume_preview_timer.timeout.connect(self._preview_alert_volume)
        self._init_sound_effect()
        self._set_camera_placeholder("카메라 미리보기가 여기에 표시됩니다.")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

        self._open_camera_and_model()
        self._refresh_records()
        self._refresh_planner()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.timer.stop()
        if self.session.app_state in (AppState.RUNNING, AppState.BREAK):
            if self.session.session_mode == "pomodoro":
                self.session.pomodoro_cycles_completed = (
                    self.pomodoro.completed_cycles
                )
            self.session.finish(time.monotonic())
            self._refresh_records()
        self._stop_session_runtime()
        self.volume_preview_timer.stop()
        if self.setup_future is not None:
            self.setup_future.cancel()
        if self.camera_open_future is not None:
            self.camera_open_future.cancel()
        if self.analysis_future is not None:
            self.analysis_future.cancel()
        self.analysis_executor.shutdown(wait=True, cancel_futures=True)
        self.camera_executor.shutdown(wait=True, cancel_futures=True)
        if (
            self.analyzer is None
            and self.setup_future is not None
            and self.setup_future.done()
            and not self.setup_future.cancelled()
        ):
            try:
                _opened, pending_analyzer, _error = self.setup_future.result()
                if pending_analyzer is not None:
                    pending_analyzer.close()
            except Exception:
                pass
        self.camera.release()
        if self.analyzer is not None:
            self.analyzer.close()
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        self._elevate(top_bar, blur=18, y=4, alpha=22)
        header = QHBoxLayout(top_bar)
        header.setContentsMargins(14, 11, 14, 11)
        header.setSpacing(9)

        header.addWidget(self._label("학습 방식", "Muted"))
        self.session_mode_combo = QComboBox()
        self.session_mode_combo.addItem("자유 측정", "free")
        self.session_mode_combo.addItem("뽀모도로", "pomodoro")
        self._set_combo_value(self.session_mode_combo, self.settings.session_mode)
        header.addWidget(self.session_mode_combo)

        self.calibration_controls = QFrame()
        self.calibration_controls.setObjectName("CalibrationControls")
        calibration_layout = QVBoxLayout(self.calibration_controls)
        calibration_layout.setContentsMargins(0, 0, 0, 0)
        calibration_layout.setSpacing(4)
        self.screen_calibration_button = CalibrationProgressButton(
            "화면 자세 설정"
        )
        self.screen_calibration_button.setObjectName("CalibrationTargetButton")
        self.screen_calibration_button.setMinimumWidth(132)
        self.writing_calibration_button = CalibrationProgressButton(
            "필기 자세 설정"
        )
        self.writing_calibration_button.setObjectName("CalibrationTargetButton")
        self.writing_calibration_button.setMinimumWidth(132)
        calibration_layout.addWidget(self.screen_calibration_button)
        calibration_layout.addWidget(self.writing_calibration_button)
        self.start_button = QPushButton("세션 시작")
        self.start_button.setObjectName("PrimaryButton")
        self.break_button = QPushButton("휴식")
        self.pomodoro_action_button = QPushButton("다음 집중 시작")
        self.pomodoro_action_button.setObjectName("GhostButton")
        self.pomodoro_action_button.setVisible(False)
        self.extend_break_button = QPushButton("1분 연장")
        self.extend_break_button.setObjectName("GhostButton")
        self.extend_break_button.setVisible(False)
        self.end_button = QPushButton("세션 종료")
        self.end_button.setObjectName("DangerButton")
        header.addWidget(self.calibration_controls)
        header.addWidget(self.start_button)
        header.addWidget(self.break_button)
        header.addWidget(self.pomodoro_action_button)
        header.addWidget(self.extend_break_button)
        header.addWidget(self.end_button)

        self.action_feedback_label = QLabel("", root)
        self.action_feedback_label.setObjectName("ActionFeedback")
        self.action_feedback_label.setVisible(False)
        self.calibration_guide_overlay = GuidedCalibrationOverlay(root)
        header.addStretch(1)

        self.app_state_label = QLabel("● 준비 중")
        self.app_state_label.setObjectName("StatePill")
        header.addWidget(self.app_state_label)
        layout.addWidget(top_bar)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.tabs.addTab(self._build_today_tab(), "오늘")
        self.tabs.addTab(self._build_monitor_tab(), "집중")
        self.tabs.addTab(self._build_records_tab(), "기록")
        self.tabs.addTab(self._build_settings_tab(), "설정")
        layout.addWidget(self.tabs, 1)

    def _build_today_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("데일리 플래너")
        title.setObjectName("SectionTitle")
        self.planner_today_label = QLabel("")
        self.planner_today_label.setObjectName("Muted")
        title_block.addWidget(title)
        title_block.addWidget(self.planner_today_label)
        toolbar.addLayout(title_block)
        toolbar.addStretch(1)

        self.previous_planner_day_button = QPushButton("‹")
        self.previous_planner_day_button.setObjectName("IconButton")
        self.previous_planner_day_button.setFixedWidth(38)
        self.previous_planner_day_button.setToolTip("이전 날")
        self.planner_calendar_button = QPushButton("날짜 선택")
        self.planner_calendar_button.setObjectName("PlannerDateButton")
        self.planner_calendar_button.setMinimumWidth(154)
        self.next_planner_day_button = QPushButton("›")
        self.next_planner_day_button.setObjectName("IconButton")
        self.next_planner_day_button.setFixedWidth(38)
        self.next_planner_day_button.setToolTip("다음 날")
        self.planner_today_button = QPushButton("오늘")
        self.planner_today_button.setObjectName("GhostButton")
        self.add_planner_task_button = QPushButton("계획 추가")
        self.add_planner_task_button.setObjectName("PrimaryButton")
        toolbar.addWidget(self.previous_planner_day_button)
        toolbar.addWidget(self.planner_calendar_button)
        toolbar.addWidget(self.next_planner_day_button)
        toolbar.addWidget(self.planner_today_button)
        toolbar.addWidget(self.add_planner_task_button)
        layout.addLayout(toolbar)

        summary = QFrame()
        summary.setObjectName("PlannerSummary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(18, 10, 18, 10)
        summary_layout.setSpacing(0)
        summary_items = (
            ("planner_deadline_value", "D-day"),
            ("planner_estimated_value", "계획 시간"),
            ("planner_actual_value", "실제 학습"),
            ("planner_focus_value", "평균 집중률"),
            ("planner_completed_value", "계획 완료"),
        )
        for index, (attribute, label_text) in enumerate(summary_items):
            block = QFrame()
            block.setObjectName("PlannerSummaryBlock")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(12, 3, 12, 3)
            block_layout.setSpacing(3)
            label = QLabel(label_text)
            label.setObjectName("PlannerSummaryLabel")
            value = QLabel("-")
            value.setObjectName("PlannerSummaryValue")
            block_layout.addWidget(label)
            block_layout.addWidget(value)
            setattr(self, attribute, value)
            summary_layout.addWidget(block, 1)
            if index < len(summary_items) - 1:
                divider = QFrame()
                divider.setObjectName("PlannerSummaryDivider")
                divider.setFixedWidth(1)
                summary_layout.addWidget(divider)
        layout.addWidget(summary)

        body = QHBoxLayout()
        body.setSpacing(12)

        timetable_panel = QFrame()
        timetable_panel.setObjectName("PlannerPanel")
        self._elevate(timetable_panel, blur=22, y=6, alpha=16)
        timetable_layout = QVBoxLayout(timetable_panel)
        timetable_layout.setContentsMargins(16, 14, 16, 14)
        timetable_layout.setSpacing(8)
        timetable_layout.addWidget(self._section_label("실제 학습 타임라인"))
        timetable_hint = QLabel(
            "칸 색은 실제 집중률, 점선 테두리는 예약한 학습 시간입니다."
        )
        timetable_hint.setObjectName("Hint")
        timetable_hint.setWordWrap(True)
        timetable_layout.addWidget(timetable_hint)
        self.planner_timetable = DailyTenMinuteTimetable()
        self.planner_timetable.setObjectName("PlannerTimetable")
        timetable_layout.addWidget(self.planner_timetable, 1)

        task_panel = QFrame()
        task_panel.setObjectName("PlannerPanel")
        self._elevate(task_panel, blur=22, y=6, alpha=16)
        task_layout = QVBoxLayout(task_panel)
        task_layout.setContentsMargins(18, 14, 18, 14)
        task_layout.setSpacing(9)
        task_header = QHBoxLayout()
        task_header.addWidget(self._section_label("학습 계획"))
        task_header.addStretch(1)
        self.planner_task_count_label = QLabel("0개")
        self.planner_task_count_label.setObjectName("Muted")
        task_header.addWidget(self.planner_task_count_label)
        task_layout.addLayout(task_header)

        quick_add = QFrame()
        quick_add.setObjectName("PlannerQuickAdd")
        quick_layout = QVBoxLayout(quick_add)
        quick_layout.setContentsMargins(9, 7, 7, 7)
        quick_layout.setSpacing(7)
        quick_title_row = QHBoxLayout()
        quick_title_row.setSpacing(7)
        self.planner_quick_title = QLineEdit()
        self.planner_quick_title.setPlaceholderText("오늘 할 공부를 입력하세요")
        self.planner_quick_add_button = QPushButton("추가")
        self.planner_quick_add_button.setObjectName("PrimaryButton")
        quick_title_row.addWidget(self.planner_quick_title, 1)
        quick_title_row.addWidget(self.planner_quick_add_button)
        quick_layout.addLayout(quick_title_row)
        self.planner_quick_schedule = PlannerScheduleEditor()
        quick_layout.addWidget(self.planner_quick_schedule)
        self.planner_quick_hour = self.planner_quick_schedule.groups["start"][1]
        self.planner_quick_minute = self.planner_quick_schedule.groups["start"][2]
        QWidget.setTabOrder(
            self.planner_quick_title,
            self.planner_quick_schedule.first_field,
        )
        QWidget.setTabOrder(
            self.planner_quick_schedule.last_field,
            self.planner_quick_add_button,
        )
        task_layout.addWidget(quick_add)

        self.planner_task_scroll = QScrollArea()
        self.planner_task_scroll.setObjectName("PlannerTaskScroll")
        self.planner_task_scroll.setWidgetResizable(True)
        self.planner_task_scroll.setFrameShape(QFrame.NoFrame)
        self.planner_task_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.planner_task_container = QWidget()
        self.planner_task_layout = QVBoxLayout(self.planner_task_container)
        self.planner_task_layout.setContentsMargins(0, 0, 3, 0)
        self.planner_task_layout.setSpacing(7)
        self.planner_task_empty = QLabel(
            "오늘 계획이 없습니다. 할 일을 추가하거나 계획 없이 집중을 시작하세요."
        )
        self.planner_task_empty.setObjectName("PlannerEmpty")
        self.planner_task_empty.setAlignment(Qt.AlignCenter)
        self.planner_task_empty.setWordWrap(True)
        self.planner_task_layout.addWidget(self.planner_task_empty, 1)
        self.planner_task_scroll.setWidget(self.planner_task_container)
        task_layout.addWidget(self.planner_task_scroll, 1)
        body.addWidget(task_panel, 3)
        body.addWidget(timetable_panel, 2)

        self.planner_calendar_dialog = QDialog(self)
        self.planner_calendar_dialog.setWindowTitle("날짜 선택")
        self.planner_calendar_dialog.setMinimumSize(390, 360)
        calendar_layout = QVBoxLayout(self.planner_calendar_dialog)
        calendar_layout.setContentsMargins(16, 16, 16, 16)
        calendar_layout.setSpacing(10)
        calendar_layout.addWidget(self._section_label("학습 날짜 선택"))
        self.planner_calendar = QCalendarWidget()
        self.planner_calendar.setObjectName("PlannerCalendar")
        self.planner_calendar.setGridVisible(False)
        self.planner_calendar.setVerticalHeaderFormat(
            QCalendarWidget.NoVerticalHeader
        )
        selected = self.planner_selected_date
        self.planner_calendar.setSelectedDate(
            QDate(selected.year, selected.month, selected.day)
        )
        calendar_layout.addWidget(self.planner_calendar, 1)
        layout.addLayout(body, 1)
        return tab

    def _build_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(14)

        camera_panel = QFrame()
        camera_panel.setObjectName("CameraPanel")
        self._elevate(camera_panel, blur=22, y=6, alpha=22)
        camera_layout = QVBoxLayout(camera_panel)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.setSpacing(0)
        self.camera_label = QLabel()
        self.camera_label.setObjectName("Camera")
        self.camera_label.setProperty(
            "previewHidden",
            self.camera_preview_hidden,
        )
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(420, 250)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        camera_layout.addWidget(self.camera_label, 1)
        camera_footer = QWidget()
        camera_footer.setObjectName("CameraFooter")
        camera_footer_layout = QHBoxLayout(camera_footer)
        camera_footer_layout.setContentsMargins(12, 7, 8, 7)
        camera_footer_layout.setSpacing(8)
        self.camera_caption = QLabel(
            "화면이 나오지 않으면 설정 탭에서 사용할 카메라를 선택하세요."
        )
        self.camera_caption.setObjectName("CameraCaption")
        self.camera_caption.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        camera_footer_layout.addWidget(self.camera_caption, 1)
        self.camera_preview_button = QPushButton(
            "화면 보기" if self.camera_preview_hidden else "화면 숨기기"
        )
        self.camera_preview_button.setObjectName("CameraToggleButton")
        self.camera_preview_button.setToolTip(
            "카메라 분석은 유지하고 영상 화면만 숨깁니다."
        )
        camera_footer_layout.addWidget(self.camera_preview_button)
        camera_layout.addWidget(camera_footer)
        body.addWidget(camera_panel, 3)

        panel = QFrame()
        panel.setObjectName("SidePanel")
        panel.setMinimumWidth(300)
        self._elevate(panel, blur=22, y=6, alpha=20)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 14, 16, 14)
        panel_layout.setSpacing(8)

        self.status_surface = QWidget()
        self.status_surface.setObjectName("LiveStatusPanel")
        status_layout = QVBoxLayout(self.status_surface)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(6)

        self.status_title = QLabel("측정 상태")
        self.status_title.setObjectName("SectionTitle")
        self.status_label = QLabel("카메라 준비 중")
        self.status_label.setObjectName("Status")
        self.calibration_badge = QLabel("기준 자세 설정 완료")
        self.calibration_badge.setObjectName("CalibrationBadge")
        self.calibration_badge.setVisible(False)
        self.reason_label = QLabel("카메라와 얼굴 분석을 준비하고 있습니다.")
        self.reason_label.setWordWrap(True)
        self.reason_label.setObjectName("Muted")
        self.tracking_label = QLabel("인식 상태를 확인하고 있습니다.")
        self.tracking_label.setObjectName("Hint")
        self.tracking_label.setWordWrap(True)
        status_layout.addWidget(self.status_title)
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(self.status_label)
        status_row.addWidget(self.calibration_badge)
        status_row.addStretch(1)
        status_layout.addLayout(status_row)
        self.active_task_label = QLabel("")
        self.active_task_label.setObjectName("ActiveTaskPill")
        self.active_task_label.setVisible(False)
        status_layout.addWidget(self.active_task_label)
        status_layout.addWidget(self.reason_label)
        status_layout.addWidget(self.tracking_label)
        panel_layout.addWidget(self.status_surface)

        self.standard_dashboard = QWidget()
        standard_layout = QVBoxLayout(self.standard_dashboard)
        standard_layout.setContentsMargins(0, 0, 0, 0)
        standard_layout.setSpacing(8)

        self.attention_warning = QFrame()
        self.attention_warning.setObjectName("AttentionWarning")
        warning_layout = QVBoxLayout(self.attention_warning)
        warning_layout.setContentsMargins(12, 9, 12, 9)
        warning_layout.setSpacing(2)
        self.attention_warning_title = QLabel("집중 이탈 알림")
        self.attention_warning_title.setObjectName("WarningTitle")
        self.attention_warning_text = QLabel("")
        self.attention_warning_text.setObjectName("WarningText")
        self.attention_warning_text.setWordWrap(True)
        warning_layout.addWidget(self.attention_warning_title)
        warning_layout.addWidget(self.attention_warning_text)
        self.attention_warning.setVisible(False)
        panel_layout.addWidget(self.attention_warning)

        self.pomodoro_dial = PomodoroDial()
        self.pomodoro_dial.setObjectName("PomodoroDial")
        self.pomodoro_dial.setVisible(self.settings.session_mode == "pomodoro")
        panel_layout.addWidget(self.pomodoro_dial)

        self.break_timer_widget = QWidget()
        break_timer_layout = QHBoxLayout(self.break_timer_widget)
        break_timer_layout.setContentsMargins(0, 2, 0, 2)
        break_timer_layout.setSpacing(12)
        break_timer_text = QVBoxLayout()
        break_timer_text.setSpacing(1)
        break_timer_text.addWidget(self._section_label("남은 휴식 시간"))
        self.break_timer_hint = QLabel("휴식 시간은 집중률 계산에서 제외됩니다.")
        self.break_timer_hint.setObjectName("Hint")
        break_timer_text.addWidget(self.break_timer_hint)
        break_timer_layout.addLayout(break_timer_text, 1)
        self.break_countdown_label = QLabel("05:00")
        self.break_countdown_label.setObjectName("BreakCountdown")
        break_timer_layout.addWidget(self.break_countdown_label)
        self.break_timer_widget.setVisible(False)
        standard_layout.addWidget(self.break_timer_widget)

        self.focus_progress = QProgressBar()
        self.focus_progress.setObjectName("FocusProgress")
        self.focus_progress.setRange(0, 100)
        self.focus_progress.setTextVisible(False)
        focus_header = QHBoxLayout()
        focus_header.addWidget(self._section_label("집중률"))
        focus_header.addStretch(1)
        self.focus_progress_value = QLabel("0%")
        self.focus_progress_value.setObjectName("ProgressValue")
        focus_header.addWidget(self.focus_progress_value)
        standard_layout.addLayout(focus_header)
        standard_layout.addWidget(self.focus_progress)

        self.coverage_progress = QProgressBar()
        self.coverage_progress.setObjectName("CoverageProgress")
        self.coverage_progress.setRange(0, 100)
        self.coverage_progress.setTextVisible(False)
        coverage_header = QHBoxLayout()
        coverage_header.addWidget(self._section_label("측정 성공률"))
        coverage_header.addStretch(1)
        self.coverage_progress_value = QLabel("0%")
        self.coverage_progress_value.setObjectName("ProgressValue")
        coverage_header.addWidget(self.coverage_progress_value)
        standard_layout.addLayout(coverage_header)
        standard_layout.addWidget(self.coverage_progress)
        self.coverage_hint = QLabel("카메라가 판정할 수 있었던 시간 비율입니다.")
        self.coverage_hint.setObjectName("Hint")
        self.coverage_hint.setWordWrap(True)
        standard_layout.addWidget(self.coverage_hint)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(18)
        metrics.setVerticalSpacing(10)
        self.focus_time = self._metric(metrics, 0, "집중 시간")
        self.non_focus_time = self._metric(metrics, 1, "이탈 시간")
        self.break_time = self._metric(metrics, 2, "휴식")
        self.unscored_time = self._metric(metrics, 3, "측정 불가")
        self.focus_ratio = self._metric(metrics, 4, "집중률")
        self.coverage_ratio = self._metric(metrics, 5, "측정 성공률")
        self.focus_ratio.setText("0%")
        self.coverage_ratio.setText("0%")
        standard_layout.addLayout(metrics)

        chart_header = QHBoxLayout()
        chart_header.addWidget(self._section_label("최근 집중 흐름"))
        chart_header.addStretch(1)
        chart_header.addWidget(self._legend("낮음", "#F04452"))
        chart_header.addWidget(self._legend("보통", "#F5B942"))
        chart_header.addWidget(self._legend("높음", "#03C75A"))
        chart_header.addWidget(self._legend("휴식", "#B0B8C1"))
        standard_layout.addLayout(chart_header)
        self.timeline_chart = TimelineChart()
        self.timeline_chart.setObjectName("TimelineChart")
        standard_layout.addWidget(self.timeline_chart)
        self.standard_dashboard.setVisible(
            self.settings.session_mode != "pomodoro"
        )
        panel_layout.addWidget(self.standard_dashboard, 1)
        body.addWidget(panel, 2)
        content_layout.addLayout(body, 1)
        layout.addWidget(content, 1)

        return tab

    def _build_records_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        title = QLabel("학습 기록")
        title.setObjectName("SectionTitle")
        toolbar.addWidget(title)
        toolbar.addStretch(1)
        self.previous_record_day_button = QPushButton("‹")
        self.previous_record_day_button.setObjectName("IconButton")
        self.previous_record_day_button.setFixedWidth(38)
        self.previous_record_day_button.setToolTip("이전 기간 보기")
        self.records_date_edit = QDateEdit(QDate.currentDate())
        self.records_date_edit.setCalendarPopup(True)
        self.records_date_edit.setDisplayFormat("yyyy년 M월 d일")
        self.records_date_edit.setMaximumDate(QDate.currentDate())
        self.records_date_edit.setMinimumWidth(150)
        self.records_date_edit.setToolTip("기록을 확인할 날짜를 선택하세요")
        self.records_period_label = QLabel("")
        self.records_period_label.setObjectName("RecordsPeriodLabel")
        self.records_period_label.setAlignment(Qt.AlignCenter)
        self.records_period_label.setMinimumWidth(250)
        self.records_period_label.setVisible(False)
        self.next_record_day_button = QPushButton("›")
        self.next_record_day_button.setObjectName("IconButton")
        self.next_record_day_button.setFixedWidth(38)
        self.next_record_day_button.setToolTip("다음 기간 보기")
        toolbar.addWidget(self.previous_record_day_button)
        toolbar.addWidget(self.records_date_edit)
        toolbar.addWidget(self.records_period_label)
        toolbar.addWidget(self.next_record_day_button)
        toolbar.addWidget(self._label("학습일 시작", "Muted"))
        self.records_day_start_combo = QComboBox()
        for hour in range(24):
            self.records_day_start_combo.addItem(f"{hour:02d}:00", hour)
        self.records_day_start_combo.setToolTip(
            "자정 이후 공부를 전날 기록에 포함할 기준 시각입니다"
        )
        for index in range(self.records_day_start_combo.count()):
            if (
                self.records_day_start_combo.itemData(index)
                == self.settings.study_day_start_hour
            ):
                self.records_day_start_combo.setCurrentIndex(index)
                break
        toolbar.addWidget(self.records_day_start_combo)
        self.day_records_button = QPushButton("일간")
        self.week_records_button = QPushButton("주간")
        self.month_records_button = QPushButton("월간")
        for button in (
            self.day_records_button,
            self.week_records_button,
            self.month_records_button,
        ):
            button.setCheckable(True)
            button.setObjectName("SegmentButton")
            toolbar.addWidget(button)
        layout.addLayout(toolbar)

        self.records_stack = QStackedWidget()

        daily_page = QWidget()
        daily_layout = QHBoxLayout(daily_page)
        daily_layout.setContentsMargins(0, 0, 0, 0)
        daily_layout.setSpacing(12)

        daily_summary_panel = QFrame()
        daily_summary_panel.setObjectName("SidePanel")
        self._elevate(daily_summary_panel, blur=22, y=6, alpha=16)
        daily_summary_layout = QVBoxLayout(daily_summary_panel)
        daily_summary_layout.setContentsMargins(18, 15, 18, 15)
        daily_summary_layout.setSpacing(7)
        daily_summary_layout.addWidget(self._section_label("오늘 학습 요약"))
        daily_legend = QHBoxLayout()
        daily_legend.addWidget(self._legend("순공", "#03C75A"))
        daily_legend.addWidget(self._legend("이탈", "#F04452"))
        daily_legend.addWidget(self._legend("휴식", "#B0B8C1"))
        daily_legend.addWidget(self._legend("측정불가", "#7C6EE6"))
        daily_legend.addStretch(1)
        daily_summary_layout.addLayout(daily_legend)
        self.daily_summary_donut = DailySummaryDonut()
        daily_summary_layout.addWidget(self.daily_summary_donut, 1)
        self.daily_study_time = self._insight_row(daily_summary_layout, "공부시간")
        self.daily_focus_time = self._insight_row(daily_summary_layout, "순공시간")
        self.daily_non_focus_time = self._insight_row(daily_summary_layout, "이탈시간")
        self.daily_break_time = self._insight_row(daily_summary_layout, "휴식시간")
        self.daily_unscored_time = self._insight_row(daily_summary_layout, "측정 불가")
        self.daily_focus_ratio = self._insight_row(daily_summary_layout, "평균 집중률")
        self.daily_longest_focus = self._insight_row(daily_summary_layout, "최장 집중")
        daily_layout.addWidget(daily_summary_panel, 2)

        hourly_panel = QFrame()
        hourly_panel.setObjectName("SidePanel")
        self._elevate(hourly_panel, blur=22, y=6, alpha=16)
        hourly_layout = QVBoxLayout(hourly_panel)
        hourly_layout.setContentsMargins(18, 15, 18, 15)
        hourly_layout.setSpacing(7)
        hourly_header = QHBoxLayout()
        hourly_header.addWidget(self._section_label("시간대별 학습 흐름"))
        hourly_header.addStretch(1)
        hourly_header.addWidget(self._legend("낮음", "#F04452"))
        hourly_header.addWidget(self._legend("보통", "#F5B942"))
        hourly_header.addWidget(self._legend("높음", "#03C75A"))
        hourly_layout.addLayout(hourly_header)
        self.daily_hour_chart = HourlyStudyChart()
        self.daily_hour_chart.setObjectName("DailyHourChart")
        hourly_layout.addWidget(self.daily_hour_chart, 1)
        self.daily_hour_focus = self._insight_row(hourly_layout, "순공시간")
        self.daily_hour_non_focus = self._insight_row(hourly_layout, "이탈시간")
        self.daily_best_focus_hour = self._insight_row(hourly_layout, "최고 집중 시간대")
        self.daily_longest_study_hour = self._insight_row(hourly_layout, "가장 오래 공부한 시간")
        daily_layout.addWidget(hourly_panel, 3)
        self.records_stack.addWidget(daily_page)

        period_page = QWidget()
        period_layout = QHBoxLayout(period_page)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(12)
        dashboard_panel = QFrame()
        dashboard_panel.setObjectName("SidePanel")
        self._elevate(dashboard_panel, blur=22, y=6, alpha=18)
        dashboard_layout = QVBoxLayout(dashboard_panel)
        dashboard_layout.setContentsMargins(18, 14, 18, 14)
        dashboard_layout.setSpacing(9)
        dashboard_header = QHBoxLayout()
        self.records_chart_title = self._section_label("최근 7일 집중률")
        dashboard_header.addWidget(self.records_chart_title)
        self.records_chart_hint = QLabel("막대 높이와 색은 집중률을 나타냅니다.")
        self.records_chart_hint.setObjectName("Hint")
        dashboard_header.addWidget(self.records_chart_hint)
        dashboard_header.addStretch(1)
        dashboard_layout.addLayout(dashboard_header)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(18)
        summary_grid.setVerticalSpacing(8)
        self.records_focus_time = self._metric(summary_grid, 0, "순공시간")
        self.records_study_time = self._metric(summary_grid, 1, "공부시간")
        self.records_focus_ratio = self._metric(summary_grid, 2, "평균 집중률")
        self.records_longest_focus = self._metric(summary_grid, 3, "최장 연속 집중")
        self.records_focus_ratio.setText("0%")
        dashboard_layout.addLayout(summary_grid)

        self.records_trend_chart = PeriodTrendChart()
        self.records_trend_chart.setObjectName("TrendChart")
        dashboard_layout.addWidget(self.records_trend_chart)
        self.records_activity_chart = MonthlyActivityHeatmap()
        self.records_activity_chart.setObjectName("ActivityChart")
        self.records_activity_chart.setVisible(False)
        dashboard_layout.addWidget(self.records_activity_chart)
        period_layout.addWidget(dashboard_panel, 3)

        insight_panel = QFrame()
        insight_panel.setObjectName("SidePanel")
        self._elevate(insight_panel, blur=22, y=6, alpha=16)
        insight_layout = QVBoxLayout(insight_panel)
        insight_layout.setContentsMargins(18, 14, 18, 14)
        insight_layout.setSpacing(9)
        insight_layout.addWidget(self._section_label("이번 기간 한눈에"))
        self.records_study_days = self._insight_row(insight_layout, "학습한 날")
        self.records_average_session = self._insight_row(insight_layout, "학습 횟수")
        self.records_best_period = self._insight_row(insight_layout, "가장 몰입한 때")
        self.records_pomodoro = self._insight_row(insight_layout, "완료한 뽀모도로")
        insight_layout.addStretch(1)
        period_layout.addWidget(insight_panel, 2)
        self.records_stack.addWidget(period_page)
        layout.addWidget(self.records_stack, 1)

        record_strip = QFrame()
        record_strip.setObjectName("RecordStrip")
        strip_layout = QHBoxLayout(record_strip)
        strip_layout.setContentsMargins(14, 8, 10, 8)
        self.records_session_summary_label = QLabel("저장된 세션이 없습니다.")
        self.records_session_summary_label.setObjectName("Muted")
        strip_layout.addWidget(self.records_session_summary_label)
        strip_layout.addStretch(1)
        self.open_records_button = QPushButton("세션 기록 보기 ›")
        self.open_records_button.setObjectName("GhostButton")
        strip_layout.addWidget(self.open_records_button)
        layout.addWidget(record_strip)

        self.records_dialog = QDialog(self)
        self.records_dialog.setWindowTitle("세션 기록")
        self.records_dialog.resize(920, 500)
        dialog_layout = QVBoxLayout(self.records_dialog)
        dialog_toolbar = QHBoxLayout()
        dialog_title = QLabel("세션 기록")
        dialog_title.setObjectName("SectionTitle")
        dialog_toolbar.addWidget(dialog_title)
        dialog_toolbar.addStretch(1)
        self.refresh_records_button = QPushButton("새로고침")
        self.delete_record_button = QPushButton("선택 기록 삭제")
        self.delete_record_button.setObjectName("DangerButton")
        self.close_records_button = QPushButton("닫기")
        dialog_toolbar.addWidget(self.refresh_records_button)
        dialog_toolbar.addWidget(self.delete_record_button)
        dialog_toolbar.addWidget(self.close_records_button)
        dialog_layout.addLayout(dialog_toolbar)
        self.records_table = QTableWidget(0, 6)
        self.records_table.setObjectName("RecordsTable")
        self.records_table.setHorizontalHeaderLabels(
            ["날짜", "학습 방식", "공부 시간", "순공 시간", "집중률", "최장 집중"]
        )
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        dialog_layout.addWidget(self.records_table, 1)
        return tab

    def _build_settings_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        panel = QFrame()
        panel.setObjectName("SettingsPanel")
        self._elevate(panel, blur=22, y=6, alpha=16)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 22, 24, 22)
        panel_layout.setSpacing(18)

        title = QLabel("집중 측정 설정")
        title.setObjectName("SectionTitle")
        description = QLabel(
            "변경한 설정은 이 PC에 저장되며 다음 실행부터 자동으로 적용됩니다."
        )
        description.setObjectName("Muted")
        panel_layout.addWidget(title)
        panel_layout.addWidget(description)

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(28)
        settings_grid.setVerticalSpacing(20)
        settings_grid.setColumnStretch(0, 1)

        def add_setting(row: int, name: str, hint: str, control: QWidget) -> None:
            text_layout = QVBoxLayout()
            text_layout.setSpacing(3)
            name_label = QLabel(name)
            name_label.setObjectName("SettingsName")
            hint_label = QLabel(hint)
            hint_label.setObjectName("Hint")
            hint_label.setWordWrap(True)
            text_layout.addWidget(name_label)
            text_layout.addWidget(hint_label)
            settings_grid.addLayout(text_layout, row, 0)
            settings_grid.addWidget(control, row, 1, alignment=Qt.AlignRight | Qt.AlignVCenter)

        camera_control = QWidget()
        camera_layout = QHBoxLayout(camera_control)
        camera_layout.setContentsMargins(0, 0, 0, 0)
        camera_layout.setSpacing(8)
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(150)
        self.refresh_camera_button = QPushButton("카메라 새로고침")
        self.refresh_camera_button.setObjectName("GhostButton")
        camera_layout.addWidget(self.camera_combo)
        camera_layout.addWidget(self.refresh_camera_button)
        add_setting(
            0,
            "카메라",
            "내장 웹캠, USB 카메라 또는 가상 카메라 중 사용할 장치를 선택하세요.",
            camera_control,
        )

        self.alert_seconds_spin = QSpinBox()
        self.alert_seconds_spin.setRange(10, 600)
        self.alert_seconds_spin.setSingleStep(10)
        self.alert_seconds_spin.setSuffix("초")
        self.alert_seconds_spin.setValue(self.settings.attention_alert_seconds)
        add_setting(
            1,
            "집중 이탈 알림",
            "연속으로 주의가 이탈한 뒤 화면 경고와 알림음을 표시할 시간입니다.",
            self.alert_seconds_spin,
        )

        self.sound_enabled_checkbox = QCheckBox("알림음 사용")
        self.sound_enabled_checkbox.setChecked(self.settings.sound_enabled)
        add_setting(
            2,
            "소리 알림",
            "집중 이탈, 휴식 종료와 뽀모도로 전환 때 알림음을 재생합니다.",
            self.sound_enabled_checkbox,
        )

        self.alert_sound_combo = QComboBox()
        self.alert_sound_combo.setMinimumWidth(180)
        for key, label in ALERT_SOUND_OPTIONS:
            self.alert_sound_combo.addItem(label, key)
        self._set_combo_value(self.alert_sound_combo, self.settings.alert_sound)
        add_setting(
            3,
            "알림음",
            "종류를 고르면 현재 볼륨으로 바로 미리 들려줍니다.",
            self.alert_sound_combo,
        )

        volume_control = QWidget()
        volume_layout = QHBoxLayout(volume_control)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.setSpacing(8)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.settings.alert_volume)
        self.volume_slider.setMinimumWidth(180)
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(0, 100)
        self.volume_spin.setSuffix("%")
        self.volume_spin.setValue(self.settings.alert_volume)
        self.test_sound_button = QPushButton("소리 테스트")
        self.test_sound_button.setObjectName("GhostButton")
        volume_layout.addWidget(self.volume_slider, 1)
        volume_layout.addWidget(self.volume_spin)
        volume_layout.addWidget(self.test_sound_button)
        add_setting(
            4,
            "알림음 크기",
            "슬라이더나 숫자를 변경하면 선택한 크기로 알림음을 미리 들려줍니다.",
            volume_control,
        )

        self.break_minutes_spin = QSpinBox()
        self.break_minutes_spin.setRange(1, 30)
        self.break_minutes_spin.setSuffix("분")
        self.break_minutes_spin.setValue(self.settings.break_duration_minutes)
        add_setting(
            5,
            "기본 휴식 시간",
            "휴식을 시작했을 때 표시되는 카운트다운 시간입니다.",
            self.break_minutes_spin,
        )

        self.absence_minutes_spin = QSpinBox()
        self.absence_minutes_spin.setRange(1, 30)
        self.absence_minutes_spin.setSuffix("분")
        self.absence_minutes_spin.setValue(self.settings.absence_to_break_minutes)
        add_setting(
            6,
            "자리 비움 자동 제외",
            "얼굴이 계속 감지되지 않으면 집중률 계산에서 자동으로 제외할 시간입니다.",
            self.absence_minutes_spin,
        )

        self.settings_mode_combo = QComboBox()
        self.settings_mode_combo.addItem("느슨함", Mode.LENIENT.value)
        self.settings_mode_combo.addItem("보통", Mode.NORMAL.value)
        self.settings_mode_combo.addItem("엄격함", Mode.STRICT.value)
        self._set_combo_value(self.settings_mode_combo, self.settings.mode)
        add_setting(
            7,
            "판정 민감도",
            "고개와 시선 이탈을 판정하는 기준을 조절합니다.",
            self.settings_mode_combo,
        )

        self.work_mode_combo = QComboBox()
        self.work_mode_combo.addItem("화면 작업", "screen")
        self.work_mode_combo.addItem("화면 + 필기", "screen_writing")
        self._set_combo_value(self.work_mode_combo, self.settings.work_mode)
        add_setting(
            8,
            "허용할 학습 자세",
            "화면과 필기를 함께 사용하면 두 자세를 각각 기준으로 설정합니다.",
            self.work_mode_combo,
        )

        pomodoro_time_control = QWidget()
        pomodoro_time_layout = QHBoxLayout(pomodoro_time_control)
        pomodoro_time_layout.setContentsMargins(0, 0, 0, 0)
        pomodoro_time_layout.setSpacing(8)
        self.pomodoro_focus_spin = QSpinBox()
        self.pomodoro_focus_spin.setRange(1, 120)
        self.pomodoro_focus_spin.setSuffix("분 집중")
        self.pomodoro_focus_spin.setValue(self.settings.pomodoro_focus_minutes)
        self.pomodoro_short_break_spin = QSpinBox()
        self.pomodoro_short_break_spin.setRange(1, 30)
        self.pomodoro_short_break_spin.setSuffix("분 휴식")
        self.pomodoro_short_break_spin.setValue(
            self.settings.pomodoro_short_break_minutes
        )
        pomodoro_time_layout.addWidget(self.pomodoro_focus_spin)
        pomodoro_time_layout.addWidget(self.pomodoro_short_break_spin)
        add_setting(
            9,
            "뽀모도로 기본 시간",
            "한 회차의 집중 시간과 짧은 휴식 시간을 정합니다.",
            pomodoro_time_control,
        )

        pomodoro_cycle_control = QWidget()
        pomodoro_cycle_layout = QHBoxLayout(pomodoro_cycle_control)
        pomodoro_cycle_layout.setContentsMargins(0, 0, 0, 0)
        pomodoro_cycle_layout.setSpacing(8)
        self.pomodoro_cycles_spin = QSpinBox()
        self.pomodoro_cycles_spin.setRange(1, 12)
        self.pomodoro_cycles_spin.setSuffix("회")
        self.pomodoro_cycles_spin.setValue(self.settings.pomodoro_cycles)
        self.pomodoro_long_break_spin = QSpinBox()
        self.pomodoro_long_break_spin.setRange(1, 60)
        self.pomodoro_long_break_spin.setSuffix("분 긴 휴식")
        self.pomodoro_long_break_spin.setValue(
            self.settings.pomodoro_long_break_minutes
        )
        pomodoro_cycle_layout.addWidget(self.pomodoro_cycles_spin)
        pomodoro_cycle_layout.addWidget(self.pomodoro_long_break_spin)
        add_setting(
            10,
            "뽀모도로 회차",
            "설정한 회차가 끝나면 긴 휴식으로 전환됩니다.",
            pomodoro_cycle_control,
        )

        pomodoro_auto_control = QWidget()
        pomodoro_auto_layout = QVBoxLayout(pomodoro_auto_control)
        pomodoro_auto_layout.setContentsMargins(0, 0, 0, 0)
        pomodoro_auto_layout.setSpacing(5)
        self.pomodoro_auto_break_checkbox = QCheckBox("집중 종료 후 휴식 자동 시작")
        self.pomodoro_auto_break_checkbox.setChecked(
            self.settings.pomodoro_auto_start_break
        )
        self.pomodoro_auto_next_checkbox = QCheckBox("휴식 종료 후 다음 집중 자동 시작")
        self.pomodoro_auto_next_checkbox.setChecked(
            self.settings.pomodoro_auto_start_next
        )
        pomodoro_auto_layout.addWidget(self.pomodoro_auto_break_checkbox)
        pomodoro_auto_layout.addWidget(self.pomodoro_auto_next_checkbox)
        add_setting(
            11,
            "자동 전환",
            "기본값은 휴식만 자동 시작하고 다음 집중은 직접 시작합니다.",
            pomodoro_auto_control,
        )

        panel_layout.addLayout(settings_grid)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.reset_settings_button = QPushButton("기본값 복원")
        self.reset_settings_button.setObjectName("GhostButton")
        self.save_settings_button = QPushButton("설정 저장")
        self.save_settings_button.setObjectName("PrimaryButton")
        buttons.addWidget(self.reset_settings_button)
        buttons.addWidget(self.save_settings_button)
        panel_layout.addLayout(buttons)

        layout.addWidget(panel)
        layout.addStretch(1)
        return self._scroll_page(tab)

    @staticmethod
    def _scroll_page(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        return scroll

    @staticmethod
    def _elevate(widget: QWidget, blur: int = 20, y: int = 5, alpha: int = 20) -> None:
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, y)
        shadow.setColor(QColor(15, 23, 42, alpha))
        widget.setGraphicsEffect(shadow)

    def _metric(self, layout: QGridLayout, row: int, label: str) -> QLabel:
        name = QLabel(label)
        name.setObjectName("MetricName")
        value = QLabel("00:00")
        value.setObjectName("Metric")
        grid_row = row // 2
        grid_col = (row % 2) * 2
        layout.addWidget(name, grid_row, grid_col)
        layout.addWidget(value, grid_row, grid_col + 1, alignment=Qt.AlignRight)
        layout.setColumnStretch(grid_col, 1)
        return value

    @staticmethod
    def _insight_row(layout: QVBoxLayout, label: str) -> QLabel:
        row = QHBoxLayout()
        name = QLabel(label)
        name.setObjectName("MetricName")
        value = QLabel("-")
        value.setObjectName("InsightValue")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(name)
        row.addStretch(1)
        row.addWidget(value)
        layout.addLayout(row)
        return value

    @staticmethod
    def _label(text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        return label

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SmallTitle")
        return label

    @staticmethod
    def _legend(text: str, color: str) -> QLabel:
        label = QLabel(f"● {text}")
        label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 700;")
        return label

    def _connect_actions(self) -> None:
        self.session_mode_combo.currentIndexChanged.connect(
            self._session_mode_changed
        )
        self.camera_combo.currentIndexChanged.connect(self._change_camera)
        self.refresh_camera_button.clicked.connect(self._refresh_camera_list)
        self.camera_preview_button.clicked.connect(self._toggle_camera_preview)
        self.screen_calibration_button.clicked.connect(
            lambda: self._start_calibration("screen")
        )
        self.writing_calibration_button.clicked.connect(
            lambda: self._start_calibration("writing")
        )
        self.start_button.clicked.connect(lambda: self._start_session())
        self.break_button.clicked.connect(self._toggle_break)
        self.pomodoro_action_button.clicked.connect(self._pomodoro_next_action)
        self.extend_break_button.clicked.connect(self._extend_break)
        self.end_button.clicked.connect(self._end_session)
        self.refresh_records_button.clicked.connect(self._refresh_records)
        self.delete_record_button.clicked.connect(self._delete_selected_record)
        self.close_records_button.clicked.connect(self.records_dialog.close)
        self.open_records_button.clicked.connect(self._open_records_dialog)
        self.previous_record_day_button.clicked.connect(
            lambda: self._move_records_date(-1)
        )
        self.next_record_day_button.clicked.connect(
            lambda: self._move_records_date(1)
        )
        self.records_date_edit.dateChanged.connect(self._records_date_changed)
        self.records_day_start_combo.currentIndexChanged.connect(
            self._records_day_start_changed
        )
        self.day_records_button.clicked.connect(lambda: self._set_records_period("day"))
        self.week_records_button.clicked.connect(lambda: self._set_records_period("week"))
        self.month_records_button.clicked.connect(lambda: self._set_records_period("month"))
        self.save_settings_button.clicked.connect(self._save_settings)
        self.reset_settings_button.clicked.connect(self._reset_settings)
        self.volume_slider.valueChanged.connect(self._volume_slider_changed)
        self.volume_spin.valueChanged.connect(self._volume_spin_changed)
        self.alert_sound_combo.currentIndexChanged.connect(
            self._alert_sound_changed
        )
        self.test_sound_button.clicked.connect(self._test_alert_sound)
        self.add_planner_task_button.clicked.connect(
            lambda: self._open_planner_task_dialog()
        )
        self.planner_quick_add_button.clicked.connect(
            self._quick_add_planner_task
        )
        self.planner_quick_title.returnPressed.connect(
            self.planner_quick_add_button.click
        )
        for _group, hour, minute in self.planner_quick_schedule.groups.values():
            hour.returnPressed.connect(self.planner_quick_add_button.click)
            minute.returnPressed.connect(self.planner_quick_add_button.click)
        self.previous_planner_day_button.clicked.connect(
            lambda: self._move_planner_date(-1)
        )
        self.next_planner_day_button.clicked.connect(
            lambda: self._move_planner_date(1)
        )
        self.planner_today_button.clicked.connect(self._go_to_today_planner)
        self.planner_calendar_button.clicked.connect(
            self._open_planner_calendar
        )
        self.planner_calendar.clicked.connect(
            self._planner_calendar_date_selected
        )
        self.tabs.currentChanged.connect(self._main_tab_changed)

    def _main_tab_changed(self, index: int) -> None:
        if index == 0:
            self._refresh_planner()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #F7F9FC; color: #191F28; }
            QWidget { font-family: "Pretendard", "Segoe UI", "Malgun Gothic"; }
            QLabel { color: #191F28; font-size: 14px; letter-spacing: 0px; }
            #TopBar {
                background: #FFFFFF;
                border: 1px solid #E9EEF5;
                border-radius: 14px;
            }
            #SectionTitle { color: #111827; font-size: 17px; font-weight: 800; }
            #SmallTitle { color: #4E5968; font-size: 13px; font-weight: 800; }
            #LiveStatusPanel {
                background: #F8FAFC;
                border: 1px solid #E8EEF6;
                border-radius: 8px;
            }
            #Status { font-size: 19px; font-weight: 850; padding-top: 1px; }
            #CalibrationBadge {
                color: #6B7684;
                background: #F2F4F6;
                border: 1px solid #E5E8EB;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 750;
            }
            #CalibrationControls { background: transparent; border: 0; }
            #CalibrationTargetButton {
                border-radius: 7px;
                padding: 5px 10px;
                min-height: 20px;
                font-size: 12px;
                font-weight: 800;
            }
            #CalibrationTargetButton[calibrationState="pending"] {
                color: #9A6700;
                background: #FFF7D6;
                border: 1px solid #F3CF67;
            }
            #CalibrationTargetButton[calibrationState="complete"] {
                color: #087A3D;
                background: #E9FAF1;
                border: 1px solid #9FE0BC;
            }
            #CalibrationTargetButton[calibrationState="collecting"] {
                color: #1B64DA;
                background: #EAF2FF;
                border: 1px solid #9FC0F5;
            }
            #CalibrationTargetButton:hover {
                border-color: #6B8FC8;
            }
            #CalibrationTargetButton:pressed {
                background: #E5E8EB;
                border-color: #8B95A1;
            }
            #CalibrationTargetButton:disabled {
                color: #A2AAB4;
                background: #F4F6F8;
                border-color: #E5E8EB;
            }
            #CalibrationTargetButton[calibrationState="collecting"]:disabled {
                color: #1B64DA;
                background: #EAF2FF;
                border-color: #9FC0F5;
            }
            #CalibrationTargetButton[calibrationState="pending"]:disabled {
                color: #9A6700;
                background: #FFF7D6;
                border-color: #F3CF67;
            }
            #CalibrationTargetButton[calibrationState="complete"]:disabled {
                color: #087A3D;
                background: #E9FAF1;
                border-color: #9FE0BC;
            }
            #AttentionWarning {
                background: #FFF1F2;
                border: 1px solid #FFD4D8;
                border-radius: 10px;
            }
            #WarningTitle { color: #D92D3A; font-size: 13px; font-weight: 850; }
            #WarningText { color: #9F2530; font-size: 12px; }
            #BreakCountdown {
                color: #1B64DA;
                font-size: 30px;
                font-weight: 850;
            }
            #MetricName { color: #8B95A1; font-size: 12px; font-weight: 650; }
            #Metric { color: #111827; font-size: 17px; font-weight: 850; }
            #InsightValue { color: #191F28; font-size: 13px; font-weight: 800; }
            #ProgressValue { color: #191F28; font-size: 13px; font-weight: 750; }
            #Muted { color: #6B7684; }
            #Hint { color: #8B95A1; font-size: 12px; }
            #StatePill {
                border-radius: 999px;
                padding: 7px 11px;
                font-size: 13px;
                font-weight: 800;
            }
            #ActionFeedback {
                color: #1B64DA;
                background: #EAF2FF;
                border: 1px solid #CFE0FF;
                border-radius: 999px;
                padding: 7px 12px;
                font-size: 13px;
                font-weight: 800;
            }
            #ActiveTaskPill {
                color: #1B64DA;
                background: #EAF2FF;
                border: 1px solid #CFE0FF;
                border-radius: 999px;
                padding: 7px 11px;
                font-size: 12px;
                font-weight: 800;
            }
            #CameraPanel, #SidePanel, #SettingsPanel {
                background: #FFFFFF;
                border: 1px solid #E9EEF5;
                border-radius: 14px;
            }
            #Camera {
                background: #0B1220;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                color: #D1D6DB;
                font-size: 16px;
            }
            #Camera[previewHidden="true"] {
                color: #6B7684;
                background: #F2F4F6;
            }
            #CameraFooter {
                color: #6B7684;
                background: #FFFFFF;
                border-top: 1px solid #EEF1F4;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
            #CameraCaption {
                color: #6B7684;
                font-size: 13px;
            }
            #CameraToggleButton {
                color: #4E5968;
                background: #F2F4F6;
                border: 1px solid #E5E8EB;
                border-radius: 8px;
                padding: 7px 10px;
                font-size: 12px;
                font-weight: 750;
            }
            #CameraToggleButton:hover {
                color: #1B64DA;
                background: #EAF2FF;
                border-color: #CFE0FF;
            }
            #CameraToggleButton:pressed {
                background: #DCE9FF;
                padding-top: 8px;
                padding-bottom: 6px;
            }
            #RecordStrip {
                background: #FFFFFF;
                border: 1px solid #E9EEF5;
                border-radius: 12px;
            }
            #PlannerSummary {
                background: #FFFFFF;
                border: 1px solid #E9EEF5;
                border-radius: 8px;
            }
            #PlannerSummaryBlock { background: transparent; border: 0; }
            #PlannerSummaryDivider { background: #EEF1F4; border: 0; }
            #PlannerSummaryLabel {
                color: #8B95A1;
                font-size: 11px;
                font-weight: 700;
            }
            #PlannerSummaryValue {
                color: #191F28;
                font-size: 18px;
                font-weight: 850;
            }
            #PlannerPanel {
                background: #FFFFFF;
                border: 1px solid #E9EEF5;
                border-radius: 8px;
            }
            #PlannerDateButton {
                color: #191F28;
                background: #FFFFFF;
                border: 1px solid #D8E0EA;
                border-radius: 8px;
                font-weight: 800;
            }
            #PlannerDateButton:hover {
                color: #1B64DA;
                border-color: #9FC0F5;
                background: #F5F9FF;
            }
            #PlannerDateButton:pressed {
                background: #EAF2FF;
                border-color: #7DA9EE;
            }
            #PlannerQuickAdd {
                background: #F7F9FC;
                border: 1px solid #E5EAF0;
                border-radius: 8px;
            }
            #PlannerQuickAdd QLineEdit {
                background: transparent;
                border: 0;
                padding: 8px 6px;
            }
            #PlannerQuickAdd #PlannerQuickTimeNumber,
            #PlannerTimeNumber {
                color: #191F28;
                background: #FFFFFF;
                border: 1px solid #D8E0EA;
                border-radius: 7px;
                padding: 7px 5px;
                font-size: 13px;
                font-weight: 750;
            }
            #PlannerQuickAdd #PlannerQuickTimeNumber:focus,
            #PlannerTimeNumber:focus {
                border-color: #3182F6;
                background: #F8FBFF;
            }
            #PlannerTimeSuffix {
                color: #6B7684;
                font-size: 12px;
                font-weight: 700;
            }
            #PlannerScheduleEditor { background: transparent; border: 0; }
            #PlannerInlineTimeGroup {
                background: #F7F9FC;
                border: 1px solid #E5EAF0;
                border-radius: 7px;
            }
            #PlannerInlineTimeLabel {
                color: #4E5968;
                font-size: 11px;
                font-weight: 800;
            }
            #PlannerInlineTimeSuffix {
                color: #8B95A1;
                font-size: 10px;
                font-weight: 700;
            }
            #PlannerQuickAdd #PlannerInlineTimeNumber,
            #PlannerInlineTimeNumber {
                color: #191F28;
                background: #FFFFFF;
                border: 1px solid #D8E0EA;
                border-radius: 5px;
                padding: 4px 2px;
                font-size: 11px;
                font-weight: 750;
            }
            #PlannerInlineTimeNumber:focus {
                background: #F8FBFF;
                border-color: #3182F6;
            }
            #PlannerInlineTimeNumber[calculated="true"] {
                color: #8B95A1;
                background: #F1F3F5;
                border-color: #D8DEE6;
            }
            #PlannerInlineTimeNumber[invalid="true"] {
                color: #D92D3A;
                background: #FFF4F5;
                border-color: #F3A7AF;
            }
            #PlannerTimetable {
                background: #FFFFFF;
                border: 0;
            }
            #PlannerTaskScroll { background: transparent; border: 0; }
            #PlannerTaskRow {
                background: #F8FAFC;
                border: 1px solid #E8EEF6;
                border-radius: 8px;
            }
            #PlannerTaskRow[status="completed"] {
                background: #F4F6F8;
                border-color: #EEF1F4;
            }
            #PlannerTaskRow[status="deferred"] {
                background: #FFFBEB;
                border-color: #FDE7B2;
            }
            #PlannerStatusButton {
                color: #6B7684;
                background: #FFFFFF;
                border: 1px solid #D8E0EA;
                border-radius: 19px;
                padding: 0;
                font-size: 18px;
                font-weight: 850;
            }
            #PlannerStatusButton[status="completed"] {
                color: #FFFFFF;
                background: #03C75A;
                border-color: #03C75A;
            }
            #PlannerStatusButton[status="deferred"] {
                color: #B45309;
                background: #FFF3CD;
                border-color: #F6C85F;
            }
            #PlannerStatusButton:pressed {
                background: #E5E8EB;
                border-color: #9AA7B5;
            }
            QLineEdit[calculated="true"],
            #PlannerTimeNumber[calculated="true"] {
                color: #8B95A1;
                background: #F4F6F8;
                border-color: #D8DEE6;
            }
            #PlannerCalculationStatus {
                color: #8B95A1;
                font-size: 12px;
                font-weight: 650;
            }
            #PlannerTaskTitle {
                color: #191F28;
                font-size: 14px;
                font-weight: 800;
            }
            #PlannerTaskTitleEdit {
                color: #191F28;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 7px;
                font-size: 14px;
                font-weight: 800;
            }
            #PlannerTaskTitleEdit:hover { background: #FFFFFF; border-color: #E5EAF0; }
            #PlannerTaskTitleEdit:focus { background: #FFFFFF; border-color: #3182F6; }
            #PlannerTaskTitleEdit[status="completed"] { color: #8B95A1; }
            #PlannerTaskTitleEdit[status="deferred"] { color: #B45309; }
            #PlannerDeleteButton {
                color: #8B95A1;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 0;
                font-size: 20px;
                font-weight: 500;
            }
            #PlannerDeleteButton:hover {
                color: #D92D3A;
                background: #FFF1F2;
                border-color: #FFD4D8;
            }
            #PlannerDeleteButton:pressed { background: #FFE4E7; }
            #PlannerTaskMeta { color: #8B95A1; font-size: 12px; }
            #PlannerDday {
                color: #D92D3A;
                background: #FFF1F2;
                border-radius: 7px;
                padding: 4px 7px;
                font-size: 11px;
                font-weight: 800;
            }
            #PlannerEmpty {
                color: #8B95A1;
                background: #F8FAFC;
                border: 1px dashed #D8E0EA;
                border-radius: 8px;
                padding: 24px;
            }
            #PlannerCalendar {
                background: #FFFFFF;
                border: 0;
            }
            #PlannerCalendar QWidget#qt_calendar_navigationbar {
                background: #F8FAFC;
                border: 1px solid #E8EEF6;
                border-radius: 8px;
            }
            #PlannerCalendar QToolButton {
                color: #191F28;
                background: transparent;
                border: 0;
                padding: 6px;
                font-weight: 800;
            }
            #PlannerCalendar QAbstractItemView {
                color: #191F28;
                background: #FFFFFF;
                selection-background-color: #03C75A;
                selection-color: #FFFFFF;
                outline: 0;
            }
            #RecordsPeriodLabel {
                color: #191F28;
                background: #FFFFFF;
                border: 1px solid #D8E0EA;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                font-weight: 750;
            }
            #IconButton {
                padding: 8px 0;
                font-size: 20px;
                font-weight: 700;
            }
            QPushButton, QComboBox, QSpinBox, QDateEdit, QLineEdit {
                background: #FFFFFF;
                color: #191F28;
                border: 1px solid #D8E0EA;
                border-radius: 10px;
                padding: 10px 15px;
                font-size: 14px;
                font-weight: 650;
            }
            QPushButton:hover, QComboBox:hover, QSpinBox:hover, QDateEdit:hover,
            QLineEdit:hover {
                background: #F8FAFC;
                border-color: #C7D2E1;
            }
            QLineEdit:focus {
                background: #FFFFFF;
                border-color: #3182F6;
            }
            QSpinBox { min-width: 92px; }
            QCheckBox { color: #191F28; font-size: 14px; font-weight: 650; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QSlider::groove:horizontal {
                height: 6px;
                background: #E5E8EB;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3182F6;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 18px;
                height: 18px;
                margin: -6px 0;
                background: #FFFFFF;
                border: 2px solid #3182F6;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover { background: #EAF2FF; }
            #SettingsName { color: #191F28; font-size: 15px; font-weight: 800; }
            QPushButton:pressed {
                background: #EEF2F7;
                border-color: #AAB7C7;
                padding-top: 11px;
                padding-bottom: 9px;
            }
            QPushButton:disabled {
                color: #B0B8C1;
                background: #F4F6F8;
                border-color: #E5E8EB;
            }
            #PrimaryButton {
                background: #03C75A;
                color: #FFFFFF;
                border-color: #03C75A;
                font-weight: 850;
            }
            #PrimaryButton:hover { background: #02B350; }
            #PrimaryButton:pressed { background: #029E47; }
            #DangerButton {
                color: #F04452;
                background: #FFFFFF;
            }
            #DangerButton:hover {
                background: #FFF3F4;
                border-color: #FFD4D8;
            }
            #DangerButton:pressed { background: #FFECEE; border-color: #FFC9CE; }
            #GhostButton { color: #4E5968; }
            #SegmentButton {
                padding: 7px 12px;
                color: #4E5968;
                background: #F2F4F6;
                border-color: #E5E8EB;
                font-weight: 700;
            }
            #SegmentButton:checked {
                color: #03A64A;
                background: #E8F8EF;
                border-color: #C9F0D8;
            }
            QProgressBar {
                background: #EEF3F8;
                border: 0;
                border-radius: 6px;
                height: 10px;
            }
            QProgressBar::chunk {
                background: #03C75A;
                border-radius: 6px;
            }
            #CoverageProgress::chunk { background: #3182F6; }
            #TimelineChart, #TrendChart, #ActivityChart, #DailyHourChart {
                background: #F8FAFC;
                border: 1px solid #E8EEF6;
                border-radius: 12px;
            }
            QDialog { background: #F7F9FC; }
            #PageScroll {
                background: transparent;
                border: 0;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: transparent;
                border: 0;
                margin: 2px;
            }
            QScrollBar:vertical { width: 10px; }
            QScrollBar:horizontal { height: 10px; }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #D1D6DB;
                border-radius: 5px;
                min-height: 28px;
                min-width: 28px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background: #B0B8C1;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                width: 0;
                height: 0;
            }
            QTabWidget::pane { border: 0; }
            QTabBar::tab {
                background: transparent;
                color: #6B7684;
                padding: 10px 18px;
                margin-right: 4px;
                border-radius: 10px;
                font-weight: 800;
            }
            QTabBar::tab:selected {
                color: #03A64A;
                background: #E9FAF1;
            }
            #RecordsTable {
                background: #FFFFFF;
                alternate-background-color: #F8FAFC;
                gridline-color: #EEF3F8;
                border: 0;
                color: #191F28;
                selection-background-color: #E9FAF1;
                selection-color: #191F28;
            }
            QHeaderView::section {
                background: #F8FAFC;
                color: #6B7684;
                border: 0;
                border-bottom: 1px solid #E8EEF6;
                padding: 8px;
                font-weight: 800;
            }
            """
        )

    def _show_action_feedback(self, message: str, color: str = "#1B64DA") -> None:
        display_text = QFontMetrics(self.action_feedback_label.font()).elidedText(
            message,
            Qt.ElideRight,
            380,
        )
        self.action_feedback_label.setText(display_text)
        self.action_feedback_label.setToolTip(message)
        self.action_feedback_label.setStyleSheet(
            f"""
            color: {color};
            background: #EAF2FF;
            border: 1px solid #CFE0FF;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 13px;
            font-weight: 700;
            """
        )
        self.action_feedback_label.adjustSize()
        self._position_action_feedback()
        self.action_feedback_label.raise_()
        self.action_feedback_label.setVisible(True)
        end_position = self.action_feedback_label.pos()
        self.action_feedback_animation = QPropertyAnimation(
            self.action_feedback_label,
            b"pos",
            self,
        )
        self.action_feedback_animation.setDuration(170)
        self.action_feedback_animation.setStartValue(
            end_position + QPoint(0, 8)
        )
        self.action_feedback_animation.setEndValue(end_position)
        self.action_feedback_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.action_feedback_animation.start()
        QTimer.singleShot(1600, lambda: self._clear_action_feedback(message))

    def _clear_action_feedback(self, message: str) -> None:
        if self.action_feedback_label.toolTip() == message:
            self.action_feedback_label.clear()
            self.action_feedback_label.setToolTip("")
            self.action_feedback_label.setVisible(False)

    def _position_action_feedback(self) -> None:
        parent = self.action_feedback_label.parentWidget()
        if parent is None:
            return
        x = max(16, (parent.width() - self.action_feedback_label.width()) // 2)
        y = max(16, parent.height() - self.action_feedback_label.height() - 72)
        self.action_feedback_label.move(x, y)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "calibration_guide_overlay"):
            parent = self.calibration_guide_overlay.parentWidget()
            if parent is not None:
                self.calibration_guide_overlay.setGeometry(parent.rect())
                self._update_calibration_guide_area()
        if hasattr(self, "action_feedback_label") and self.action_feedback_label.isVisible():
            self._position_action_feedback()

    def _open_camera_and_model(self) -> None:
        self._refresh_camera_list()
        self.camera_combo.setEnabled(False)
        self.refresh_camera_button.setEnabled(False)
        self.camera_caption.setText("카메라와 얼굴 분석기를 준비하고 있습니다.")
        self.reason_label.setText("잠시만 기다려 주세요. 화면은 준비되는 즉시 표시됩니다.")
        self.tracking_label.setText("카메라 장치와 얼굴 분석기를 확인하고 있습니다.")
        self._set_calibration_buttons_enabled(False)
        self.setup_future = self.camera_executor.submit(
            self._initialize_camera_and_model,
            self.settings.camera_index,
        )

    def _initialize_camera_and_model(
        self, camera_index: int
    ) -> Tuple[bool, Optional[FaceAnalyzer], str]:
        opened = self.camera.open(camera_index)
        try:
            analyzer = FaceAnalyzer()
        except Exception as exc:
            return opened, None, f"얼굴 분석기를 준비하지 못했습니다: {exc}"
        error = "" if opened else f"Camera {camera_index}를 열 수 없습니다."
        return opened, analyzer, error

    def _consume_setup_result(self) -> None:
        future = self.setup_future
        if future is None or not future.done():
            return
        self.setup_future = None
        self.camera_combo.setEnabled(True)
        self.refresh_camera_button.setEnabled(True)
        try:
            opened, analyzer, error = future.result()
        except Exception as exc:
            opened, analyzer, error = False, None, str(exc)
        self.analyzer = analyzer
        if analyzer is None:
            self.camera_available = False
            self.last_error = error or "카메라와 얼굴 분석기를 준비하지 못했습니다."
            self.session.app_state = AppState.ERROR
            self._set_camera_placeholder("카메라를 사용할 수 없습니다.")
            self._show_action_feedback("측정 준비 실패", "#F04452")
            return
        if not opened:
            self.camera_available = False
            self.last_error = error
            self.camera_reconnect_attempt = 0
            self.camera_next_reconnect_at = time.monotonic() + 1.0
            self._set_camera_placeholder("카메라 연결을 기다리고 있습니다.")
            self.status_label.setText("카메라 연결 대기")
            self.status_label.setStyleSheet("color: #F59E0B;")
            self.reason_label.setText(
                "선택한 카메라의 연결을 확인하세요. 앱이 자동으로 다시 연결합니다."
            )
            self.tracking_label.setText("카메라 자동 재연결 대기")
            return
        self.camera_available = True
        self.last_analysis_sequence = -1
        self.latest_observation = None
        self.last_error = ""
        if self.session.app_state == AppState.ERROR:
            self.session.app_state = AppState.PREVIEW
        backend = self.camera.backend_name or "Windows"
        self.camera_caption.setText(
            f"Camera {self.settings.camera_index} · {backend} 연결됨"
        )
        self.reason_label.setText(
            "카메라가 연결되었습니다. 세션 시작 전에 기준 자세를 설정하세요."
        )
        self.tracking_label.setText("카메라 연결 및 얼굴 분석 준비 완료")
        self._set_calibration_buttons_enabled(True)
        self._show_action_feedback(
            f"Camera {self.settings.camera_index} · {backend} 연결됨",
            "#03A64A",
        )

    def _refresh_camera_list(self) -> None:
        current = self.camera_combo.currentData()
        desired = self.settings.camera_index if current is None else int(current)
        self.camera_combo.blockSignals(True)
        self.camera_combo.clear()
        for index in CameraService.list_candidate_cameras():
            self.camera_combo.addItem(f"Camera {index}", index)
        for row in range(self.camera_combo.count()):
            if self.camera_combo.itemData(row) == desired:
                self.camera_combo.setCurrentIndex(row)
                break
        self.camera_combo.blockSignals(False)
        self.reason_label.setText(
            "카메라 목록을 새로고침했습니다. 화면이 나오지 않으면 다른 장치를 선택하세요."
        )
        self._show_action_feedback("카메라 목록 새로고침")

    def _change_camera(self) -> None:
        index = self.camera_combo.currentData()
        if index is None:
            self.last_error = "선택된 카메라가 없습니다."
            self.session.app_state = AppState.ERROR
            self._show_action_feedback("카메라를 선택하세요", "#F04452")
            return
        if self.session.app_state in (AppState.RUNNING, AppState.BREAK):
            self.camera_combo.blockSignals(True)
            current_index = self.camera_combo.findData(self.camera_open_index)
            if current_index >= 0:
                self.camera_combo.setCurrentIndex(current_index)
            self.camera_combo.blockSignals(False)
            self._show_action_feedback(
                "카메라는 세션 종료 후 변경할 수 있습니다",
                "#F59E0B",
            )
            return
        if int(index) != self.camera_open_index:
            self.engine.clear_calibrations()
            self.session.app_state = AppState.PREVIEW
            self.latest_decision = None
            self._update_calibration_controls()
        self._start_camera_open(int(index), automatic=False)

    def _start_camera_open(self, index: int, automatic: bool) -> None:
        if self.camera_open_future is not None or self.setup_future is not None:
            if not automatic:
                self._show_action_feedback("카메라 연결 작업이 진행 중입니다")
            return
        self.camera_open_index = index
        self.camera_open_automatic = automatic
        self.camera_available = False
        self.camera_combo.setEnabled(False)
        self.refresh_camera_button.setEnabled(False)
        self.camera_caption.setText(f"Camera {index} 연결을 시도하고 있습니다.")
        self.status_label.setText("카메라 재연결 중" if automatic else "카메라 변경 중")
        self.status_label.setStyleSheet("color: #F59E0B;")
        self.reason_label.setText("카메라를 준비하는 동안 측정은 잠시 보류됩니다.")
        self.tracking_label.setText("카메라 연결 작업 진행 중")
        self._set_calibration_buttons_enabled(False)
        self.camera_open_future = self.camera_executor.submit(self.camera.open, index)

    def _consume_camera_open_result(self) -> None:
        future = self.camera_open_future
        if future is None or not future.done():
            return
        self.camera_open_future = None
        self.camera_combo.setEnabled(True)
        self.refresh_camera_button.setEnabled(True)
        try:
            opened = bool(future.result())
        except Exception as exc:
            opened = False
            self.last_error = str(exc)
        index = self.camera_open_index
        if opened:
            self.camera_available = True
            self.last_analysis_sequence = -1
            self.latest_observation = None
            self.settings.camera_index = index
            self._persist_settings()
            self.last_error = ""
            self.camera_reconnect_attempt = 0
            self.camera_next_reconnect_at = 0.0
            if self.session.app_state == AppState.ERROR:
                self.session.app_state = AppState.PREVIEW
            backend = self.camera.backend_name or "Windows"
            self.camera_caption.setText(f"Camera {index} · {backend} 연결됨")
            self.status_label.setText("카메라 연결 완료")
            self.status_label.setStyleSheet("color: #03A64A;")
            self.reason_label.setText("카메라가 복구되어 집중 측정을 계속합니다.")
            self.tracking_label.setText("카메라 연결 및 얼굴 분석 재개")
            self._show_action_feedback(
                f"Camera {index} · {backend} 연결됨",
                "#03A64A",
            )
            return

        delay_index = min(
            self.camera_reconnect_attempt,
            len(self.camera_reconnect_delays) - 1,
        )
        delay = self.camera_reconnect_delays[delay_index]
        self.camera_reconnect_attempt += 1
        self.camera_available = False
        self.camera_next_reconnect_at = time.monotonic() + delay
        self.last_error = self.last_error or f"Camera {index}를 열 수 없습니다."
        self._set_camera_placeholder("카메라 연결을 기다리고 있습니다.")
        if not self.camera_open_automatic:
            self._show_action_feedback(f"Camera {index} 연결 실패", "#F04452")

    def _update_camera_reconnect_status(self, timestamp: float) -> None:
        if self.camera_open_future is not None:
            self.status_label.setText("카메라 재연결 중")
            self.status_label.setStyleSheet("color: #F59E0B;")
            self.reason_label.setText(
                "선택한 카메라에 다시 연결하고 있습니다. 세션은 유지됩니다."
            )
            self.tracking_label.setText("카메라 재연결 시도 중 · 현재 측정 불가")
            return
        remaining = max(0, int(self.camera_next_reconnect_at - timestamp + 0.999))
        self.status_label.setText("카메라 연결 대기")
        self.status_label.setStyleSheet("color: #F59E0B;")
        self.reason_label.setText(
            f"카메라 연결을 확인하세요. {remaining}초 후 자동으로 다시 시도합니다."
        )
        self.tracking_label.setText("카메라 연결 대기 · 현재 측정 불가")

    def _toggle_camera_preview(self) -> None:
        self.camera_preview_hidden = not self.camera_preview_hidden
        self.settings.camera_preview_hidden = self.camera_preview_hidden
        self.camera_label.setProperty(
            "previewHidden",
            self.camera_preview_hidden,
        )
        self.camera_label.style().unpolish(self.camera_label)
        self.camera_label.style().polish(self.camera_label)
        self.camera_preview_button.setText(
            "화면 보기" if self.camera_preview_hidden else "화면 숨기기"
        )
        if self.camera_preview_hidden:
            self._set_camera_placeholder(
                "카메라 화면을 숨겼습니다.\n집중 측정은 계속됩니다."
            )
            self.camera_caption.setText(
                "영상만 숨김 · 얼굴과 시선 분석은 계속 작동합니다."
            )
            self._show_action_feedback("카메라 화면을 숨겼습니다")
        else:
            self.camera_caption.setText("카메라 화면을 표시하고 있습니다.")
            self._show_action_feedback("카메라 화면을 다시 표시합니다", "#03A64A")
        self._persist_settings()

    def _session_mode_changed(self) -> None:
        session_mode = str(self.session_mode_combo.currentData())
        self.settings.session_mode = session_mode
        self.pomodoro_dial.setVisible(session_mode == "pomodoro")
        self.standard_dashboard.setVisible(session_mode != "pomodoro")
        self.coverage_hint.setVisible(session_mode != "pomodoro")
        if session_mode == "pomodoro" and not self.pomodoro.active:
            self.pomodoro.configure(self._pomodoro_config())
            self._refresh_pomodoro_dial(time.monotonic())
        self._persist_settings()
        label = "뽀모도로" if session_mode == "pomodoro" else "자유 측정"
        self._show_action_feedback(f"학습 방식: {label}")

    def _pomodoro_config(self) -> PomodoroConfig:
        return PomodoroConfig(
            focus_minutes=self.settings.pomodoro_focus_minutes,
            short_break_minutes=self.settings.pomodoro_short_break_minutes,
            long_break_minutes=self.settings.pomodoro_long_break_minutes,
            cycles=self.settings.pomodoro_cycles,
            auto_start_break=self.settings.pomodoro_auto_start_break,
            auto_start_next_focus=self.settings.pomodoro_auto_start_next,
        )

    def _save_settings(self) -> None:
        active_session = self.session.app_state in (AppState.RUNNING, AppState.BREAK)
        judgement_change_blocked = False
        self.settings.attention_alert_seconds = self.alert_seconds_spin.value()
        self.settings.break_duration_minutes = self.break_minutes_spin.value()
        requested_absence_minutes = self.absence_minutes_spin.value()
        if active_session and (
            requested_absence_minutes != self.settings.absence_to_break_minutes
        ):
            requested_absence_minutes = self.settings.absence_to_break_minutes
            self.absence_minutes_spin.setValue(requested_absence_minutes)
            judgement_change_blocked = True
        self.settings.absence_to_break_minutes = requested_absence_minutes
        self.settings.sound_enabled = self.sound_enabled_checkbox.isChecked()
        self.settings.alert_volume = self.volume_spin.value()
        self.settings.alert_sound = str(self.alert_sound_combo.currentData())
        requested_mode = str(self.settings_mode_combo.currentData())
        if active_session and requested_mode != self.settings.mode:
            requested_mode = self.settings.mode
            self._set_combo_value(self.settings_mode_combo, requested_mode)
            judgement_change_blocked = True
        self.settings.mode = requested_mode
        requested_work_mode = str(self.work_mode_combo.currentData())
        if active_session and requested_work_mode != self.engine.work_mode:
            requested_work_mode = self.engine.work_mode
            self._set_combo_value(self.work_mode_combo, requested_work_mode)
            judgement_change_blocked = True
        self.settings.work_mode = requested_work_mode
        self.settings.pomodoro_focus_minutes = self.pomodoro_focus_spin.value()
        self.settings.pomodoro_short_break_minutes = (
            self.pomodoro_short_break_spin.value()
        )
        self.settings.pomodoro_long_break_minutes = (
            self.pomodoro_long_break_spin.value()
        )
        self.settings.pomodoro_cycles = self.pomodoro_cycles_spin.value()
        self.settings.pomodoro_auto_start_break = (
            self.pomodoro_auto_break_checkbox.isChecked()
        )
        self.settings.pomodoro_auto_start_next = (
            self.pomodoro_auto_next_checkbox.isChecked()
        )

        self.alert_controller.threshold_seconds = float(
            self.settings.attention_alert_seconds
        )
        if not self.break_timer.active:
            self.break_timer.duration_seconds = float(
                self.settings.break_duration_minutes * 60
            )
        self.engine.policy.absence_to_break_seconds = (
            self.settings.absence_to_break_minutes * 60.0
        )
        mode = Mode(self.settings.mode)
        self.engine.set_mode(mode)
        self.engine.set_work_mode(self.settings.work_mode)
        self._update_calibration_controls()
        if self.sound_effect is not None:
            self.sound_effect.setVolume(self.settings.alert_volume / 100.0)
        self._select_alert_sound(self.settings.alert_sound)
        if not self.pomodoro.active:
            self.pomodoro.configure(self._pomodoro_config())
            self._refresh_pomodoro_dial(time.monotonic())

        if self._persist_settings():
            if judgement_change_blocked:
                self._show_action_feedback(
                    "설정을 저장했습니다. 판정 기준은 세션 종료 후 변경하세요",
                    "#F59E0B",
                )
            else:
                self._show_action_feedback("설정을 저장했습니다", "#03A64A")

    def _reset_settings(self) -> None:
        defaults = UserSettings(camera_index=self.settings.camera_index)
        self.alert_seconds_spin.setValue(defaults.attention_alert_seconds)
        self.break_minutes_spin.setValue(defaults.break_duration_minutes)
        self.absence_minutes_spin.setValue(defaults.absence_to_break_minutes)
        self.sound_enabled_checkbox.setChecked(defaults.sound_enabled)
        self._set_combo_value(self.alert_sound_combo, defaults.alert_sound)
        self.volume_slider.setValue(defaults.alert_volume)
        self.volume_spin.setValue(defaults.alert_volume)
        self._set_combo_value(self.settings_mode_combo, defaults.mode)
        self._set_combo_value(self.work_mode_combo, defaults.work_mode)
        self.pomodoro_focus_spin.setValue(defaults.pomodoro_focus_minutes)
        self.pomodoro_short_break_spin.setValue(
            defaults.pomodoro_short_break_minutes
        )
        self.pomodoro_long_break_spin.setValue(
            defaults.pomodoro_long_break_minutes
        )
        self.pomodoro_cycles_spin.setValue(defaults.pomodoro_cycles)
        self.pomodoro_auto_break_checkbox.setChecked(
            defaults.pomodoro_auto_start_break
        )
        self.pomodoro_auto_next_checkbox.setChecked(
            defaults.pomodoro_auto_start_next
        )
        self._save_settings()
        self._show_action_feedback("기본 설정으로 복원했습니다", "#03A64A")

    def _persist_settings(self) -> bool:
        try:
            self.settings_store.save(self.settings)
            return True
        except OSError as exc:
            self._show_action_feedback("설정을 저장하지 못했습니다", "#F04452")
            self.last_error = str(exc)
            return False

    def _volume_slider_changed(self, value: int) -> None:
        self.volume_spin.blockSignals(True)
        self.volume_spin.setValue(value)
        self.volume_spin.blockSignals(False)
        self.volume_preview_timer.start()

    def _volume_spin_changed(self, value: int) -> None:
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(value)
        self.volume_slider.blockSignals(False)
        self.volume_preview_timer.start()

    def _alert_sound_changed(self) -> None:
        key = str(self.alert_sound_combo.currentData() or DEFAULT_ALERT_SOUND)
        self._select_alert_sound(key)
        if self.sound_enabled_checkbox.isChecked():
            self._play_sound(self.volume_slider.value())
        self._show_action_feedback(
            f"알림음: {self.alert_sound_combo.currentText()}",
            "#1B64DA",
        )

    def _preview_alert_volume(self) -> None:
        if self.sound_enabled_checkbox.isChecked():
            self._play_sound(self.volume_slider.value())

    def _test_alert_sound(self) -> None:
        if not self.sound_enabled_checkbox.isChecked():
            self._show_action_feedback("알림음 사용을 먼저 켜주세요", "#F59E0B")
            return
        self.volume_preview_timer.stop()
        self._play_sound(self.volume_slider.value())
        self._show_action_feedback(
            f"알림음 크기 {self.volume_slider.value()}%",
            "#1B64DA",
        )

    def _start_calibration(self, target: str) -> None:
        if target == "writing" and self.engine.work_mode != "screen_writing":
            self._show_action_feedback(
                "설정에서 화면 + 필기 자세를 먼저 선택하세요",
                "#F04452",
            )
            return
        if target == "writing" and not self.engine.calibrated:
            self.reason_label.setText(
                "필기 자세보다 화면 자세를 먼저 설정해야 합니다."
            )
            self._show_action_feedback("화면 자세를 먼저 설정하세요", "#F04452")
            return
        self.tabs.setCurrentIndex(1)
        self.engine.start_calibration(time.monotonic(), target=target)
        self.last_calibration_status_logged = None
        self.session.app_state = AppState.CALIBRATING
        target_button = (
            self.writing_calibration_button
            if target == "writing"
            else self.screen_calibration_button
        )
        target_button.set_progress(0.0)
        self._set_calibration_buttons_enabled(False)
        self._update_calibration_controls()
        target_label = "필기" if target == "writing" else "화면"
        self.status_label.setText(f"{target_label} 기준 설정 중")
        self.status_label.setStyleSheet("color: #F59E0B;")
        self.reason_label.setText(
            f"안내되는 순서에 따라 평소 {target_label} 작업 영역을 자연스럽게 바라봐 주세요."
        )
        manager = (
            self.engine.writing_calibration
            if target == "writing"
            else self.engine.calibration
        )
        parent = self.calibration_guide_overlay.parentWidget()
        if parent is not None:
            self.calibration_guide_overlay.setGeometry(parent.rect())
        self._update_calibration_guide_area()
        self.calibration_guide_overlay.set_stage(
            manager.current_target,
            0.0,
            0,
            len(manager.guided_targets),
            target == "writing",
        )
        self._show_action_feedback(f"{target_label} 자세 설정 시작")

    def _update_calibration_guide_area(self) -> None:
        if not hasattr(self, "camera_label") or not hasattr(
            self, "calibration_guide_overlay"
        ):
            return
        parent = self.calibration_guide_overlay.parentWidget()
        if parent is None:
            return
        top_left = self.camera_label.mapTo(parent, QPoint(0, 0))
        self.calibration_guide_overlay.set_target_area(
            QRectF(
                top_left.x(),
                top_left.y(),
                self.camera_label.width(),
                self.camera_label.height(),
            )
        )

    def _start_session(
        self,
        task_id: Optional[int] = None,
        task_title: str = "",
    ) -> None:
        if not self.engine.ready_for_session:
            missing = "필기 자세" if self.engine.calibrated else "화면 자세"
            self.reason_label.setText(
                f"세션 시작 전에 {missing} 기준을 설정하세요."
            )
            self._show_action_feedback("기준 자세가 필요합니다", "#F04452")
            return
        self.engine.reset_runtime_state()
        self.alert_controller.reset()
        self.attention_warning.setVisible(False)
        self.break_timer.stop()
        self.break_timer_widget.setVisible(False)
        session_mode = str(self.session_mode_combo.currentData())
        if session_mode == "pomodoro":
            self.pomodoro.configure(self._pomodoro_config())
            self.pomodoro.start(time.monotonic())
            self.session.start(
                session_mode="pomodoro",
                pomodoro_cycles_planned=self.pomodoro.config.cycles,
                task_id=task_id,
            )
            self.pomodoro_dial.setVisible(True)
            self._refresh_pomodoro_dial(time.monotonic())
        else:
            self.pomodoro.stop()
            self.session.start(session_mode="free", task_id=task_id)
        self.active_task_id = task_id
        self.active_task_title = task_title if task_id is not None else ""
        display_task = QFontMetrics(self.active_task_label.font()).elidedText(
            self.active_task_title,
            Qt.ElideRight,
            240,
        )
        self.active_task_label.setText(
            f"● {display_task} 학습 중"
            if self.active_task_title
            else ""
        )
        self.active_task_label.setToolTip(self.active_task_title)
        self.active_task_label.setVisible(bool(self.active_task_title))
        self.timeline_chart.set_slots([])
        self._show_action_feedback(
            "뽀모도로 집중을 시작했습니다"
            if session_mode == "pomodoro"
            else "세션을 시작했습니다",
            "#03A64A",
        )

    def _toggle_break(self) -> None:
        if self.session.session_mode == "pomodoro" and self.pomodoro.active:
            self._toggle_pomodoro_pause()
            return
        previous_state = self.session.app_state
        self.session.toggle_break()
        if self.session.app_state == previous_state:
            return
        self.engine.reset_runtime_state()
        if self.session.app_state == AppState.BREAK:
            self.alert_controller.reset()
            self.attention_warning.setVisible(False)
            self.break_timer.duration_seconds = float(
                self.settings.break_duration_minutes * 60
            )
            self.break_timer.start(time.monotonic())
            self.break_timer_widget.setVisible(True)
            self.extend_break_button.setVisible(True)
            self._update_break_timer(time.monotonic())
            self._show_action_feedback("휴식을 시작했습니다")
        else:
            self.break_timer.stop()
            self.break_timer_widget.setVisible(False)
            self.extend_break_button.setVisible(False)
            self._show_action_feedback("측정을 재개했습니다", "#03A64A")

    def _toggle_pomodoro_pause(self) -> None:
        now = time.monotonic()
        if self.pomodoro.phase == PomodoroPhase.PAUSED:
            update = self.pomodoro.resume(now)
            self._set_pomodoro_session_break(update.phase != PomodoroPhase.FOCUS)
            self._show_action_feedback("뽀모도로를 재개했습니다", "#03A64A")
        elif self.pomodoro.phase in (
            PomodoroPhase.FOCUS,
            PomodoroPhase.SHORT_BREAK,
            PomodoroPhase.LONG_BREAK,
        ):
            self.pomodoro.pause(now)
            self._set_pomodoro_session_break(True)
            self.alert_controller.reset()
            self.attention_warning.setVisible(False)
            self._show_action_feedback("뽀모도로를 일시정지했습니다")
        self._refresh_pomodoro_dial(now)

    def _pomodoro_next_action(self) -> None:
        if self.session.session_mode != "pomodoro":
            return
        now = time.monotonic()
        if self.pomodoro.phase == PomodoroPhase.WAITING_NEXT:
            update = self.pomodoro.start_next(now)
        elif self.pomodoro.phase in (
            PomodoroPhase.SHORT_BREAK,
            PomodoroPhase.LONG_BREAK,
        ):
            update = self.pomodoro.skip_break(now)
        else:
            return
        if update.phase == PomodoroPhase.COMPLETED:
            self._end_session()
            self._show_action_feedback("뽀모도로를 완료했습니다", "#1B64DA")
            return
        self._set_pomodoro_session_break(update.phase != PomodoroPhase.FOCUS)
        self._refresh_pomodoro_dial(now)
        self._show_action_feedback(
            "다음 집중을 시작했습니다"
            if update.phase == PomodoroPhase.FOCUS
            else "휴식을 시작했습니다",
            "#03A64A",
        )

    def _set_pomodoro_session_break(self, should_break: bool) -> None:
        if should_break and self.session.app_state == AppState.RUNNING:
            self.session.toggle_break()
            self.engine.reset_runtime_state()
        elif not should_break and self.session.app_state == AppState.BREAK:
            self.session.toggle_break()
            self.engine.reset_runtime_state()

    def _update_pomodoro(self, timestamp: float) -> None:
        if self.session.session_mode != "pomodoro":
            return
        if self.session.app_state not in (AppState.RUNNING, AppState.BREAK):
            return

        update = self.pomodoro.update(timestamp)
        self.session.pomodoro_cycles_completed = update.completed_cycles
        if update.just_changed:
            if update.phase in (
                PomodoroPhase.SHORT_BREAK,
                PomodoroPhase.LONG_BREAK,
                PomodoroPhase.WAITING_NEXT,
            ):
                self._set_pomodoro_session_break(True)
                self.alert_controller.reset()
                self.attention_warning.setVisible(False)
                self._play_alert_sound()
                if update.phase == PomodoroPhase.WAITING_NEXT:
                    self._show_action_feedback(
                        "휴식이 끝났습니다. 준비되면 다음 집중을 시작하세요",
                        "#1B64DA",
                    )
                else:
                    self._show_action_feedback(
                        "집중 회차 완료, 휴식을 시작합니다",
                        "#1B64DA",
                    )
            elif update.phase == PomodoroPhase.FOCUS:
                self._set_pomodoro_session_break(False)
                self._play_alert_sound()
                self._show_action_feedback("다음 집중을 시작합니다", "#03A64A")
            elif update.phase == PomodoroPhase.COMPLETED:
                self._play_alert_sound()
                self._refresh_pomodoro_dial(timestamp)
                self._end_session()
                self._show_action_feedback("뽀모도로를 완료했습니다", "#1B64DA")
                return
        self._refresh_pomodoro_dial(timestamp)

    def _refresh_pomodoro_dial(self, timestamp: float) -> None:
        config = self.pomodoro.config
        if self.pomodoro.phase == PomodoroPhase.IDLE:
            remaining = config.focus_minutes * 60.0
            progress = 1.0
        else:
            remaining = self.pomodoro.remaining(timestamp)
            progress = self.pomodoro.progress(timestamp)
        self.pomodoro_dial.set_state(
            self.pomodoro.phase,
            remaining,
            progress,
            self.pomodoro.cycle,
            config.cycles,
            self.pomodoro.completed_cycles,
        )
        phase = self.pomodoro.phase
        self.pomodoro_action_button.setVisible(
            phase
            in (
                PomodoroPhase.SHORT_BREAK,
                PomodoroPhase.LONG_BREAK,
                PomodoroPhase.WAITING_NEXT,
            )
            and self.session.app_state in (AppState.RUNNING, AppState.BREAK)
        )
        waiting_for_break = (
            phase == PomodoroPhase.WAITING_NEXT
            and self.pomodoro.paused_from
            in (PomodoroPhase.SHORT_BREAK, PomodoroPhase.LONG_BREAK)
        )
        if waiting_for_break:
            action_text = "휴식 시작"
        elif phase == PomodoroPhase.WAITING_NEXT:
            action_text = "다음 집중 시작"
        else:
            action_text = "휴식 건너뛰기"
        self.pomodoro_action_button.setText(action_text)

    def _extend_break(self) -> None:
        if self.session.app_state != AppState.BREAK:
            return
        now = time.monotonic()
        self.break_timer.extend(60.0, now)
        self._update_break_timer(now)
        self._show_action_feedback("휴식을 1분 연장했습니다")

    def _end_session(self) -> None:
        if self.session.app_state not in (AppState.RUNNING, AppState.BREAK):
            return
        now = time.monotonic()
        completed_cycles = self.pomodoro.completed_cycles
        planned_cycles = self.pomodoro.config.cycles
        if self.session.session_mode == "pomodoro":
            self.session.pomodoro_cycles_completed = completed_cycles
        self.session.finish(now)
        self._stop_session_runtime()
        if self.session.session_mode == "pomodoro":
            self.pomodoro_dial.show_stopped(planned_cycles, completed_cycles)
        else:
            self._refresh_pomodoro_dial(now)
        self._refresh_records()
        self._refresh_planner()
        self.active_task_id = None
        self.active_task_title = ""
        self.active_task_label.clear()
        self.active_task_label.setToolTip("")
        self.active_task_label.setVisible(False)
        self._refresh_labels(self.latest_decision)
        self._show_action_feedback("세션을 저장하고 타이머를 종료했습니다", "#03A64A")

    def _stop_session_runtime(self) -> None:
        self.pending_sound_volume = None
        self.pomodoro.stop()
        self.alert_controller.reset()
        self.attention_warning.setVisible(False)
        self.break_timer.stop()
        self.break_timer_widget.setVisible(False)
        self.extend_break_button.setVisible(False)
        self.pomodoro_action_button.setVisible(False)
        if self.sound_effect is not None and self.sound_effect.isPlaying():
            self.sound_effect.stop()

    def _tick(self) -> None:
        now = time.monotonic()
        self._consume_setup_result()
        self._consume_camera_open_result()
        if self.setup_future is not None:
            return
        self._update_pomodoro(now)
        self._update_break_timer(now)
        if self.session.app_state == AppState.ERROR:
            self._refresh_labels(None)
            return
        camera_frame = self.camera.read()
        if not camera_frame.ok or camera_frame.frame is None:
            self.camera_available = False
            self._set_camera_placeholder("카메라 프레임이 없습니다.")
            if (
                now - self.last_camera_error_processed_at
                >= self.camera_error_interval_seconds
            ):
                self.last_camera_error_processed_at = now
                observation = FrameObservation(
                    timestamp=camera_frame.timestamp,
                    camera_ok=False,
                    error=camera_frame.error,
                )
                self.latest_observation = observation
                self._handle_observation(observation)
            if (
                self.analyzer is not None
                and self.camera_open_future is None
                and now >= self.camera_next_reconnect_at
            ):
                self._start_camera_open(self.camera_open_index, automatic=True)
            self._update_camera_reconnect_status(now)
            return

        self.last_camera_error_processed_at = 0.0
        self.camera_available = True
        self.latest_frame = camera_frame.frame
        if self.analyzer is None:
            return
        self._consume_analysis_result()

        display_observation = self.latest_observation or FrameObservation(
            timestamp=camera_frame.timestamp,
            camera_ok=True,
        )
        if now - self.last_preview_rendered_at >= self.preview_interval_seconds:
            self.last_preview_rendered_at = now
            self._show_frame(camera_frame.frame, display_observation)

        if (
            self.analysis_future is None
            and camera_frame.sequence != self.last_analysis_sequence
            and now - self.last_analysis_submitted_at
            >= self.analysis_interval_seconds
        ):
            self.last_analysis_sequence = camera_frame.sequence
            self.last_analysis_submitted_at = now
            analysis_frame = camera_frame.frame.copy()
            self.analysis_future = self.analysis_executor.submit(
                self.analyzer.analyze,
                analysis_frame,
                camera_frame.timestamp,
            )

    def _consume_analysis_result(self) -> None:
        future = self.analysis_future
        if future is None or not future.done():
            return
        self.analysis_future = None
        try:
            observation = future.result()
        except Exception as exc:
            observation = FrameObservation(
                timestamp=time.monotonic(),
                camera_ok=True,
                quality_reason=ObservationState.PROCESSING_ERROR.value,
                error=str(exc),
            )
        self.latest_observation = observation
        self._handle_observation(observation)

    def _handle_observation(self, observation: FrameObservation) -> None:
        if self.session.app_state == AppState.CALIBRATING:
            progress = self.engine.update_calibration(observation)
            self._refresh_calibration(progress)
            if progress.status == CalibrationStatus.READY:
                self.session.app_state = AppState.READY
                target_label = (
                    "필기"
                    if self.engine.active_calibration_target == "writing"
                    else "화면"
                )
                self._show_action_feedback(
                    f"{target_label} 자세 설정 완료",
                    "#03A64A",
                )
            elif progress.status == CalibrationStatus.FAILED:
                self.session.app_state = AppState.PREVIEW
                self._show_action_feedback("기준 자세 설정 실패", "#F04452")
            decision = self.engine.decide(observation, self.session.manual_break)
        else:
            decision = self.engine.decide(observation, self.session.manual_break)
            self.session.update(decision)
            self._update_attention_alert(decision)

        self.latest_decision = decision
        self._refresh_labels(decision)

    def _update_attention_alert(self, decision) -> None:
        if self.session.app_state != AppState.RUNNING:
            self.alert_controller.reset()
            self.attention_warning.setVisible(False)
            return
        update = self.alert_controller.update(
            decision.effective_state, decision.timestamp
        )
        if update.just_triggered:
            self._play_alert_sound()
            self._show_action_feedback(
                f"집중 이탈이 {self._fmt(self.alert_controller.threshold_seconds)} 이상 지속되고 있습니다",
                "#F04452",
            )
        self.attention_warning.setVisible(update.active)
        if update.active:
            self.attention_warning_text.setText(
                f"주의 이탈이 {self._fmt(update.elapsed_seconds)} 동안 지속되고 있습니다. "
                "작업 화면으로 돌아오면 자동으로 해제됩니다."
            )

    def _update_break_timer(self, timestamp: float) -> None:
        if self.session.app_state != AppState.BREAK or not self.break_timer.active:
            self.break_timer_widget.setVisible(False)
            self.extend_break_button.setVisible(False)
            return
        update = self.break_timer.update(timestamp)
        self.break_timer_widget.setVisible(True)
        self.extend_break_button.setVisible(True)
        self.break_countdown_label.setText(
            self._fmt_countdown(update.remaining_seconds)
        )
        if update.expired:
            self.break_timer_hint.setText("휴식 시간이 끝났습니다. 준비되면 측정을 재개하세요.")
        else:
            self.break_timer_hint.setText("휴식 시간은 집중률 계산에서 제외됩니다.")
        if update.just_expired:
            self._play_alert_sound()
            self._show_action_feedback("휴식 시간이 끝났습니다", "#1B64DA")

    def _init_sound_effect(self) -> None:
        sound_dir = self.settings_store.path.parent / "sounds"
        for key, path in ensure_alert_sound_files(sound_dir).items():
            effect = QSoundEffect(self)
            effect.setLoopCount(1)
            effect.setSource(QUrl.fromLocalFile(str(path.resolve())))
            effect.setVolume(self.settings.alert_volume / 100.0)
            effect.statusChanged.connect(
                lambda effect=effect: self._sound_effect_status_changed(effect)
            )
            self.sound_effects[key] = effect
        self._select_alert_sound(self.settings.alert_sound)

    def _select_alert_sound(self, key: str) -> None:
        self.pending_sound_volume = None
        if self.sound_effect is not None and self.sound_effect.isPlaying():
            self.sound_effect.stop()
        self.sound_effect = (
            self.sound_effects.get(key)
            or self.sound_effects.get(DEFAULT_ALERT_SOUND)
            or next(iter(self.sound_effects.values()), None)
        )
        if self.sound_effect is not None:
            self.sound_effect.setVolume(self.volume_spin.value() / 100.0)

    def _play_sound(self, volume_percent: int) -> None:
        volume = min(100, max(0, int(volume_percent)))
        if volume <= 0:
            self.pending_sound_volume = None
            if self.sound_effect is not None and self.sound_effect.isPlaying():
                self.sound_effect.stop()
            return
        if self.sound_effect is None:
            QApplication.beep()
            return
        status = self.sound_effect.status()
        if status == QSoundEffect.Status.Loading:
            self.pending_sound_volume = volume
            return
        if status == QSoundEffect.Status.Error:
            self.pending_sound_volume = None
            QApplication.beep()
            self._show_action_feedback(
                "알림음을 불러오지 못했습니다. Windows 출력 장치를 확인하세요.",
                "#F04452",
            )
            return
        self.pending_sound_volume = None
        self._play_ready_sound(self.sound_effect, volume)

    def _sound_effect_status_changed(self, effect: QSoundEffect) -> None:
        if effect is not self.sound_effect or self.pending_sound_volume is None:
            return
        if not self.sound_enabled_checkbox.isChecked():
            self.pending_sound_volume = None
            return
        if effect.status() == QSoundEffect.Status.Ready:
            volume = self.pending_sound_volume
            self.pending_sound_volume = None
            self._play_ready_sound(effect, volume)
        elif effect.status() == QSoundEffect.Status.Error:
            self.pending_sound_volume = None
            QApplication.beep()
            self._show_action_feedback(
                "알림음을 불러오지 못했습니다. Windows 출력 장치를 확인하세요.",
                "#F04452",
            )

    @staticmethod
    def _play_ready_sound(effect: QSoundEffect, volume: int) -> None:
        effect.setVolume(volume / 100.0)
        if effect.isPlaying():
            effect.stop()
        effect.play()

    def _play_alert_sound(self) -> None:
        if self.settings.sound_enabled:
            self._play_sound(self.settings.alert_volume)

    def _show_frame(self, frame, observation: FrameObservation) -> None:
        if self.camera_preview_hidden:
            if self.camera_label.text() != (
                "카메라 화면을 숨겼습니다.\n집중 측정은 계속됩니다."
            ):
                self._set_camera_placeholder(
                    "카메라 화면을 숨겼습니다.\n집중 측정은 계속됩니다."
                )
            self.camera_caption.setText(
                "영상만 숨김 · 얼굴과 시선 분석은 계속 작동합니다."
            )
            return
        guided_frame = frame.copy()
        guide_status = self._draw_camera_guide(guided_frame, observation)
        self.camera_caption.setText(guide_status)
        rgb = cv2.cvtColor(guided_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image).scaled(
            self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.camera_label.setPixmap(pixmap)

    def _draw_camera_guide(self, frame, observation: FrameObservation) -> str:
        height, width = frame.shape[:2]
        profile = self.engine.guide_profile
        screen_center = (width // 2, height // 2)
        cross_color = (196, 188, 176)
        cross = 8
        cv2.line(
            frame,
            (screen_center[0] - cross, screen_center[1]),
            (screen_center[0] + cross, screen_center[1]),
            cross_color,
            1,
            cv2.LINE_AA,
        )
        cv2.line(
            frame,
            (screen_center[0], screen_center[1] - cross),
            (screen_center[0], screen_center[1] + cross),
            cross_color,
            1,
            cv2.LINE_AA,
        )

        if profile is not None:
            target_x, target_y = profile.face_center
            target_scale = profile.face_scale_center
            baseline_center = (int(target_x * width), int(target_y * height))
            baseline_axes = (
                max(54, int(target_scale * width * 0.42)),
                max(74, int(target_scale * height * 0.56)),
            )
            cv2.ellipse(
                frame,
                baseline_center,
                baseline_axes,
                0,
                0,
                360,
                (235, 163, 65),
                2,
                cv2.LINE_AA,
            )
        aligned = False
        if (
            profile is not None
            and observation.face_detected
            and observation.face_center
            and observation.face_scale
        ):
            dx = abs(observation.face_center[0] - target_x)
            dy = abs(observation.face_center[1] - target_y)
            scale_delta = abs(observation.face_scale - target_scale) / max(target_scale, 1e-6)
            aligned = dx <= 0.10 and dy <= 0.12 and scale_delta <= 0.35

        if observation.face_bbox:
            x0, y0, x1, y1 = observation.face_bbox
            left, top = int(x0 * width), int(y0 * height)
            right, bottom = int(x1 * width), int(y1 * height)
            if profile is None:
                box_color = (235, 163, 65)
            else:
                box_color = (90, 199, 3) if aligned else (66, 185, 245)
            corner = max(12, min(right - left, bottom - top) // 8)
            for start, end in (
                ((left, top + corner), (left, top)),
                ((left, top), (left + corner, top)),
                ((right - corner, top), (right, top)),
                ((right, top), (right, top + corner)),
                ((right, bottom - corner), (right, bottom)),
                ((right, bottom), (right - corner, bottom)),
                ((left + corner, bottom), (left, bottom)),
                ((left, bottom), (left, bottom - corner)),
            ):
                cv2.line(frame, start, end, box_color, 2, cv2.LINE_AA)

        if not observation.face_detected:
            if profile is None:
                return "카메라에 얼굴과 양쪽 눈이 보이도록 앉아주세요."
            return "저장된 기준 자세 윤곽선에 얼굴을 맞춰주세요."
        if profile is None:
            return "현재 앉은 위치에서 정면을 유지하고 기준 자세 설정을 눌러주세요."
        if aligned:
            return "기준 위치에 맞게 얼굴이 안정적으로 잡혔습니다."
        if observation.face_scale is not None:
            if observation.face_scale > target_scale * 1.35:
                return "카메라에서 조금 멀어져 주세요."
            if observation.face_scale < target_scale * 0.65:
                return "카메라에 조금 가까이 와주세요."
        return "얼굴을 저장된 기준 자세 윤곽선에 맞춰주세요."

    def _set_camera_placeholder(self, text: str) -> None:
        pixmap = self.camera_label.pixmap()
        if (
            (pixmap is None or pixmap.isNull())
            and self.camera_label.text() == text
        ):
            return
        self.camera_label.clear()
        self.camera_label.setText(text)

    def _refresh_calibration(self, progress: CalibrationProgress) -> None:
        pct = int(progress.progress * 100)
        target_button = (
            self.writing_calibration_button
            if self.engine.active_calibration_target == "writing"
            else self.screen_calibration_button
        )
        target_button.set_progress(progress.progress)
        target_label = (
            "필기" if self.engine.active_calibration_target == "writing" else "화면"
        )
        if progress.status == CalibrationStatus.COLLECTING:
            self._update_calibration_controls()
            target_name = GuidedCalibrationOverlay.TARGET_LABELS.get(
                progress.target_key,
                "작업 영역",
            )
            self._update_calibration_guide_area()
            self.calibration_guide_overlay.set_stage(
                progress.target_key,
                progress.target_progress,
                progress.target_index,
                progress.total_targets,
                self.engine.active_calibration_target == "writing",
            )
            if progress.stage_changed and self.settings.sound_enabled:
                self._play_sound(max(8, int(self.settings.alert_volume * 0.35)))
            self.reason_label.setText(
                f"{target_label} 작업 영역 설정 중: {pct}% "
                f"({progress.valid_samples}/{progress.target_samples}개 유효 샘플)\n"
                f"{progress.target_index + 1}/{progress.total_targets}단계 · "
                f"{target_name} · 단계 진행 {int(progress.target_progress * 100)}%\n"
                f"{progress.message}"
            )
            self.tracking_label.setText(
                "유효한 얼굴과 양쪽 눈이 확인될 때만 진행됩니다."
            )
        elif progress.status == CalibrationStatus.READY:
            self.calibration_guide_overlay.clear_stage()
            target_button.set_progress(1.0)
            self._update_calibration_controls()
            self._play_alert_sound()
            if self.engine.ready_for_session:
                self.reason_label.setText(
                    f"{target_label} 기준 자세가 저장되었습니다. 세션을 시작할 수 있습니다."
                )
            else:
                self.reason_label.setText(
                    "화면 기준 자세가 저장되었습니다. 상단의 필기 자세 설정도 완료하세요."
                )
            self.tracking_label.setText(f"{target_label} 기준 저장 완료")
        elif progress.status == CalibrationStatus.FAILED:
            self.calibration_guide_overlay.clear_stage()
            target_button.set_progress(0.0)
            self._update_calibration_controls()
            self._play_alert_sound()
            self.reason_label.setText(
                f"{target_label} 기준 자세를 저장하지 못했습니다.\n"
                f"{progress.message}\n"
                f"안내에 맞게 조정한 뒤 {target_label} 자세 설정을 다시 눌러주세요."
            )
            self.tracking_label.setText(f"{target_label} 기준 설정 실패")

    def _update_calibration_controls(self) -> None:
        dual_mode = self.engine.work_mode == "screen_writing"
        self.writing_calibration_button.setVisible(dual_mode)
        collecting_target = (
            self.engine.active_calibration_target
            if self.session.app_state == AppState.CALIBRATING
            else None
        )
        states = {
            "screen": (
                "collecting"
                if collecting_target == "screen"
                else "complete" if self.engine.calibrated else "pending"
            ),
            "writing": (
                "collecting"
                if collecting_target == "writing"
                else "complete"
                if self.engine.writing_calibrated
                else "pending"
            ),
        }
        for target, button, label in (
            ("screen", self.screen_calibration_button, "화면 자세 설정"),
            ("writing", self.writing_calibration_button, "필기 자세 설정"),
        ):
            state = states[target]
            button.setProperty("calibrationState", state)
            if state == "complete":
                button.set_progress(1.0)
            elif state == "pending":
                button.set_progress(0.0)
            button.setText(
                f"{label} {button.progress * 100:.0f}%"
                if state == "collecting"
                else f"{label} ✓" if state == "complete" else label
            )
            button.setToolTip(
                f"{label.replace(' 설정', '')} 기준이 저장되었습니다. 다시 누르면 재설정합니다."
                if state == "complete"
                else f"{label.replace(' 설정', '')} 기준을 아직 설정하지 않았습니다."
            )
            button.style().unpolish(button)
            button.style().polish(button)
        if not self.engine.calibrated:
            self.calibration_badge.setVisible(False)
            return
        self.calibration_badge.setVisible(True)
        if dual_mode and self.engine.writing_calibrated:
            self.calibration_badge.setText("화면·필기 기준 완료")
        elif dual_mode:
            self.calibration_badge.setText("화면 기준 완료 · 필기 필요")
        else:
            self.calibration_badge.setText("화면 기준 완료")

    def _set_calibration_buttons_enabled(self, enabled: bool) -> None:
        self.screen_calibration_button.setEnabled(enabled)
        self.writing_calibration_button.setEnabled(
            enabled and self.engine.work_mode == "screen_writing"
        )

    def _set_app_state_badge(self, app_state: AppState) -> None:
        badge_key = (app_state, self.engine.ready_for_session)
        if self._last_app_badge_state == badge_key:
            return
        self._last_app_badge_state = badge_key
        text, color, background, border = APP_STATE_BADGE.get(
            app_state,
            ("상태 확인", "#6B7684", "#F2F4F6", "#E5E8EB"),
        )
        if app_state == AppState.READY and not self.engine.ready_for_session:
            text, color, background, border = (
                "필기 기준 필요",
                "#B45309",
                "#FFF7E6",
                "#FDE1A7",
            )
        self.app_state_label.setText(f"● {text}")
        self.app_state_label.setStyleSheet(
            f"""
            color: {color};
            background: {background};
            border: 1px solid {border};
            border-radius: 999px;
            padding: 7px 11px;
            font-size: 13px;
            font-weight: 800;
            """
        )

    def _refresh_labels(self, decision) -> None:
        app_state = self.session.app_state
        active_session = app_state in (AppState.RUNNING, AppState.BREAK)
        selected_session_mode = str(self.session_mode_combo.currentData())
        self.session_mode_combo.setEnabled(not active_session)
        self.camera_combo.setEnabled(
            not active_session
            and self.camera_open_future is None
            and self.setup_future is None
        )
        self.refresh_camera_button.setEnabled(
            not active_session
            and self.camera_open_future is None
            and self.setup_future is None
        )
        self.pomodoro_dial.setVisible(selected_session_mode == "pomodoro")
        self.standard_dashboard.setVisible(selected_session_mode != "pomodoro")
        self.coverage_hint.setVisible(selected_session_mode != "pomodoro")
        self._update_calibration_controls()
        self._set_app_state_badge(app_state)
        self.start_button.setEnabled(
            self.engine.ready_for_session
            and self.camera_available
            and app_state in (AppState.READY, AppState.RESULT)
        )
        self.break_button.setEnabled(app_state in (AppState.RUNNING, AppState.BREAK))
        self.end_button.setEnabled(app_state in (AppState.RUNNING, AppState.BREAK))
        calibration_enabled = (
            self.camera_available
            and app_state
            in (AppState.PREVIEW, AppState.READY, AppState.RESULT, AppState.ERROR)
        )
        self._set_calibration_buttons_enabled(calibration_enabled)
        self.work_mode_combo.setEnabled(not active_session)
        self.start_button.setText(
            "측정 중" if app_state in (AppState.RUNNING, AppState.BREAK) else "세션 시작"
        )
        self.break_button.setText("재개" if app_state == AppState.BREAK else "휴식")
        if self.session.session_mode == "pomodoro" and active_session:
            self.start_button.setText("뽀모도로 진행 중")
            self.extend_break_button.setVisible(False)
            if self.pomodoro.phase == PomodoroPhase.PAUSED:
                self.break_button.setText("재개")
            elif self.pomodoro.phase in (
                PomodoroPhase.SHORT_BREAK,
                PomodoroPhase.LONG_BREAK,
            ):
                self.break_button.setText("휴식 일시정지")
            else:
                self.break_button.setText("일시정지")
            self.break_button.setEnabled(
                self.pomodoro.phase
                not in (PomodoroPhase.WAITING_NEXT, PomodoroPhase.COMPLETED)
            )
        if app_state == AppState.ERROR:
            self.status_label.setText("카메라 확인 필요")
            self.status_label.setStyleSheet("color: #F04452;")
            self.reason_label.setText(self.last_error)
            self.tracking_label.setText("카메라 또는 얼굴 분석기를 확인하세요.")
            self.focus_progress.setValue(0)
            self.coverage_progress.setValue(0)
            self.focus_progress_value.setText("0%")
            self.coverage_progress_value.setText("0%")
            return

        if decision is None:
            if app_state == AppState.RESULT:
                self.status_label.setText("결과 저장됨")
                self.status_label.setStyleSheet("color: #03C75A;")
                self.reason_label.setText(
                    "세션과 학습 기록을 저장했습니다. 새 세션을 시작할 수 있습니다."
                )
                self.tracking_label.setText("세션 타이머 종료")
            else:
                self.status_label.setText("대기 중")
                self.status_label.setStyleSheet("color: #F59E0B;")
                self.tracking_label.setText("얼굴 인식 결과를 기다리고 있습니다.")
            return

        label, color = STATE_LABEL.get(decision.effective_state, ("Unknown", "#191F28"))
        if app_state == AppState.CALIBRATING:
            label = "기준 설정 중"
            color = "#F59E0B"
        elif app_state == AppState.READY:
            label = "시작 가능"
            color = "#03C75A"
        elif app_state == AppState.BREAK:
            label = "휴식 중"
            color = "#1B64DA"
        elif app_state == AppState.RESULT:
            label = "결과 저장됨"
            color = "#03C75A"
        elif (
            app_state == AppState.RUNNING
            and decision.raw_state == ObservationState.NO_FACE
            and decision.effective_state == EffectiveState.BREAK
        ):
            label = "장시간 자리 비움"
            color = "#6B7684"
        self.status_label.setText(label)
        self.status_label.setStyleSheet(f"color: {color};")
        posture_label = (
            "필기 자세"
            if self.engine.last_matched_profile == "writing"
            else "화면 자세"
        )
        if app_state == AppState.CALIBRATING:
            target_label = (
                "필기"
                if self.engine.active_calibration_target == "writing"
                else "화면"
            )
            self.status_label.setText(f"{target_label} 기준 설정 중")
            self.tracking_label.setText(
                f"{target_label} 자세 수집 · 인식 안정도 {decision.confidence * 100:.0f}%"
            )
        else:
            self.tracking_label.setText(
                f"인식 안정도 {decision.confidence * 100:.0f}% · {posture_label} 기준"
            )
        if app_state == AppState.READY:
            if self.engine.ready_for_session:
                self.reason_label.setText(
                    "필요한 기준 자세가 저장되었습니다. 세션을 시작할 수 있습니다."
                )
            else:
                self.status_label.setText("필기 기준 필요")
                self.status_label.setStyleSheet("color: #F59E0B;")
                self.reason_label.setText(
                    "화면 기준은 준비되었습니다. 상단의 필기 자세 설정도 완료하세요."
                )
        elif app_state == AppState.BREAK:
            if (
                self.session.session_mode == "pomodoro"
                and self.pomodoro.phase == PomodoroPhase.PAUSED
            ):
                self.reason_label.setText(
                    "뽀모도로가 일시정지되었습니다. 이 시간은 집중률에서 제외됩니다."
                )
            elif (
                self.session.session_mode == "pomodoro"
                and self.pomodoro.phase == PomodoroPhase.WAITING_NEXT
            ):
                self.reason_label.setText(
                    "다음 집중은 준비가 되었을 때 직접 시작하세요."
                )
            else:
                self.reason_label.setText("휴식 시간은 집중률 계산에서 제외됩니다.")
        elif (
            app_state == AppState.RUNNING
            and decision.raw_state == ObservationState.NO_FACE
            and decision.effective_state == EffectiveState.BREAK
        ):
            self.reason_label.setText(
                "장시간 자리 비움으로 자동으로 제외 중입니다. 얼굴이 감지되면 측정을 이어갑니다."
            )
        elif app_state != AppState.CALIBRATING:
            if (
                decision.raw_state == ObservationState.NORMAL_VIEW
                and self.engine.work_mode == "screen_writing"
            ):
                self.reason_label.setText(
                    f"{posture_label}로 학습 중입니다. 얼굴과 눈이 안정적으로 감지됩니다."
                )
            else:
                self.reason_label.setText(
                    REASON_TEXT.get(decision.raw_state, decision.reason)
                )

        durations = self.session.metrics.snapshot()
        focus_ratio = self.session.metrics.focus_ratio() * 100
        coverage_ratio = self.session.metrics.coverage_ratio() * 100
        self.focus_time.setText(self._fmt(durations[EffectiveState.FOCUS]))
        self.non_focus_time.setText(self._fmt(durations[EffectiveState.NON_FOCUS]))
        self.break_time.setText(self._fmt(durations[EffectiveState.BREAK]))
        self.unscored_time.setText(self._fmt(durations[EffectiveState.UNSCORED]))
        self.focus_ratio.setText(f"{focus_ratio:.0f}%")
        self.coverage_ratio.setText(f"{coverage_ratio:.0f}%")
        self.focus_progress.setValue(int(focus_ratio))
        self.coverage_progress.setValue(int(coverage_ratio))
        self.focus_progress_value.setText(f"{focus_ratio:.0f}%")
        self.coverage_progress_value.setText(f"{coverage_ratio:.0f}%")
        self.timeline_chart.set_slots(self.session.metrics.timeline_snapshot(limit=240))
        now = time.monotonic()
        if (
            self.tabs.currentIndex() == 0
            and self.session.app_state in (AppState.RUNNING, AppState.BREAK)
            and now - self.last_planner_timeline_refresh_at >= 2.0
        ):
            self.last_planner_timeline_refresh_at = now
            self._refresh_planner_timeline()

    def _refresh_planner(self) -> None:
        tasks = self.database.list_planner_tasks()
        selected = self.planner_selected_date
        current_study_date = self._study_date_for_datetime(datetime.now())
        weekdays = ("월", "화", "수", "목", "금", "토", "일")
        self.planner_today_label.setText(
            f"{selected.year}년 {selected.month}월 {selected.day}일 "
            f"{weekdays[selected.weekday()]}요일"
        )
        self.planner_calendar_button.setText(
            f"{selected.month}월 {selected.day}일"
        )

        visible_tasks = [
            task
            for task in tasks
            if (
                self._parse_date(task.planned_date) == selected
                or (
                    selected == current_study_date
                    and task.status != "completed"
                    and self._parse_date(task.planned_date) is not None
                    and self._parse_date(task.planned_date) < selected
                )
            )
        ]
        visible_tasks.sort(
            key=lambda task: (
                {"pending": 0, "deferred": 1, "completed": 2}.get(
                    task.status,
                    0,
                ),
                self._parse_date(task.planned_date) or selected,
                self._parse_date(task.deadline_date) or date.max,
                task.id,
            )
        )
        self._clear_layout(self.planner_task_layout)
        if visible_tasks:
            for task in visible_tasks:
                self.planner_task_layout.addWidget(
                    self._planner_task_row(task)
                )
            self.planner_task_layout.addStretch(1)
        else:
            self.planner_task_empty = QLabel(
                "이날의 학습 계획이 없습니다.\n위 입력창에서 바로 계획을 추가하세요."
            )
            self.planner_task_empty.setObjectName("PlannerEmpty")
            self.planner_task_empty.setAlignment(Qt.AlignCenter)
            self.planner_task_empty.setWordWrap(True)
            self.planner_task_layout.addWidget(self.planner_task_empty, 1)
        pending_count = sum(task.status == "pending" for task in visible_tasks)
        deferred_count = sum(task.status == "deferred" for task in visible_tasks)
        count_text = f"남은 일 {pending_count}개"
        if deferred_count:
            count_text += f" · 보류 {deferred_count}개"
        self.planner_task_count_label.setText(count_text)

        planned_for_day = [
            task
            for task in tasks
            if self._parse_date(task.planned_date) == selected
        ]
        estimated_minutes = sum(
            task.estimated_minutes for task in planned_for_day
        )
        session_rows = self.database.list_sessions(None)
        day_buckets = self._build_daily_hour_buckets(
            session_rows,
            study_date=selected,
        )
        focus_seconds = sum(bucket["focus"] for bucket in day_buckets)
        non_focus_seconds = sum(bucket["non_focus"] for bucket in day_buckets)
        actual_seconds = sum(
            bucket["focus"] + bucket["non_focus"] for bucket in day_buckets
        )
        completed_for_day = sum(
            task.status == "completed" for task in planned_for_day
        )
        self.planner_estimated_value.setText(
            self._fmt_record_duration(estimated_minutes * 60)
        )
        self.planner_actual_value.setText(
            self._fmt_record_duration(actual_seconds)
        )
        self.planner_focus_value.setText(
            f"{self._ratio(focus_seconds, non_focus_seconds) * 100:.0f}%"
            if actual_seconds > 0
            else "-"
        )
        self.planner_completed_value.setText(
            f"{completed_for_day}/{len(planned_for_day)}"
            if planned_for_day
            else "0/0"
        )
        deadlines = [
            (
                self._parse_date(task.deadline_date),
                task,
            )
            for task in tasks
            if task.status != "completed"
            and self._parse_date(task.deadline_date) is not None
        ]
        deadlines.sort(key=lambda item: (item[0], item[1].id))
        if deadlines:
            nearest_date, _nearest_task = deadlines[0]
            self.planner_deadline_value.setText(
                self._format_d_day(nearest_date.isoformat(), selected)
            )
        else:
            self.planner_deadline_value.setText("-")

        self._refresh_planner_timeline(session_rows, tasks)
        self._refresh_planner_calendar(tasks)

    def _refresh_planner_timeline(
        self,
        session_rows=None,
        planner_tasks=None,
    ) -> None:
        selected = self.planner_selected_date
        current_study_date = self._study_date_for_datetime(datetime.now())
        current_slot = None
        if selected == current_study_date:
            day_start, _day_end = self._study_day_bounds(selected)
            elapsed = (datetime.now() - day_start).total_seconds()
            if 0 <= elapsed < 24 * 60 * 60:
                current_slot = int(elapsed // 600)
        rows = (
            self.database.list_sessions(None)
            if session_rows is None
            else session_rows
        )
        tasks = (
            self.database.list_planner_tasks()
            if planner_tasks is None
            else planner_tasks
        )
        self.planner_timetable.set_slots(
            self._build_ten_minute_timetable_slots(rows, selected),
            self.settings.study_day_start_hour,
            current_slot,
            self._build_planned_timetable_slots(tasks, selected),
        )

    def _build_planned_timetable_slots(
        self,
        tasks,
        study_date: date,
    ) -> set[int]:
        planned_slots: set[int] = set()
        day_start_minute = self.settings.study_day_start_hour * 60
        for task in tasks:
            if (
                self._parse_date(task.planned_date) != study_date
                or task.planned_start_minute is None
            ):
                continue
            first_slot = (
                (task.planned_start_minute - day_start_minute) % (24 * 60)
            ) // 10
            duration = max(0, int(task.estimated_minutes))
            if (
                duration <= 0
                and task.planned_end_minute is not None
            ):
                duration = (
                    task.planned_end_minute - task.planned_start_minute
                ) % (24 * 60)
            slot_count = max(1, min(144, math.ceil(duration / 10)))
            for offset in range(slot_count):
                planned_slots.add((first_slot + offset) % 144)
        return planned_slots

    def _planner_task_row(self, task) -> QWidget:
        row = QFrame()
        row.setObjectName("PlannerTaskRow")
        status = task.status if task.status in {
            "pending",
            "completed",
            "deferred",
        } else "pending"
        row.setProperty("status", status)
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 9, 9, 9)
        layout.setSpacing(7)

        top_row = QHBoxLayout()
        top_row.setSpacing(9)

        status_button = QPushButton(
            {"pending": "○", "completed": "✓", "deferred": "Ⅱ"}[status]
        )
        status_button.setObjectName("PlannerStatusButton")
        status_button.setProperty("status", status)
        status_button.setFixedSize(34, 34)
        status_button.setAccessibleName(
            {"pending": "공란", "completed": "완료", "deferred": "보류"}[status]
        )
        status_button.setToolTip(
            {
                "pending": "공란 · 누르면 완료",
                "completed": "완료 · 누르면 보류",
                "deferred": "보류 · 누르면 공란",
            }[status]
        )
        status_button.clicked.connect(
            lambda _checked=False, task_id=task.id, current=status: (
                self._cycle_planner_task_status(task_id, current)
            )
        )
        top_row.addWidget(status_button)

        title_edit = QLineEdit(task.title)
        title_edit.setObjectName("PlannerTaskTitleEdit")
        title_edit.setProperty("status", status)
        title_edit.setToolTip("제목을 수정한 뒤 Enter를 누르거나 다른 곳을 클릭하세요")
        title_edit.editingFinished.connect(
            lambda task_id=task.id, field=title_edit, original=task.title: (
                self._save_planner_task_title(task_id, field, original)
            )
        )
        top_row.addWidget(title_edit, 1)

        planned = self._parse_date(task.planned_date)
        if (
            planned is not None
            and planned < self.planner_selected_date
            and task.completed_at is None
        ):
            meta = QLabel(f"{planned.month}/{planned.day} 미완료")
            meta.setObjectName("PlannerTaskMeta")
            top_row.addWidget(meta)

        deadline = self._parse_date(task.deadline_date)
        if deadline is not None and status != "completed":
            d_day = QLabel(self._format_d_day(task.deadline_date))
            d_day.setObjectName("PlannerDday")
            d_day.setToolTip(f"마감일 {deadline.year}년 {deadline.month}월 {deadline.day}일")
            top_row.addWidget(d_day)

        delete_button = QPushButton("×")
        delete_button.setObjectName("PlannerDeleteButton")
        delete_button.setFixedSize(32, 32)
        delete_button.setToolTip("할 일 삭제")
        delete_button.clicked.connect(
            lambda _checked=False, task_id=task.id, title=task.title: (
                self._delete_planner_task(task_id, title)
            )
        )
        top_row.addWidget(delete_button)
        layout.addLayout(top_row)

        schedule_row = QHBoxLayout()
        schedule_row.setContentsMargins(43, 0, 0, 0)
        schedule = PlannerScheduleEditor(
            task.planned_start_minute,
            task.planned_end_minute,
            task.estimated_minutes,
        )
        schedule.scheduleCommitted.connect(
            lambda start, duration, end, task_id=task.id: (
                self._save_planner_task_schedule(
                    task_id,
                    start,
                    duration,
                    end,
                )
            )
        )
        schedule_row.addWidget(schedule, 1)
        layout.addLayout(schedule_row)
        return row

    def _open_planner_task_dialog(self, task_id: Optional[int] = None) -> None:
        existing = next(
            (
                item
                for item in self.database.list_planner_tasks()
                if item.id == task_id
            ),
            None,
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("할 일 수정" if existing else "할 일 추가")
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(13)
        title = QLabel("학습 계획 수정" if existing else "새 학습 계획")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(11)
        title_edit = QLineEdit()
        title_edit.setPlaceholderText("예: 미적분 문제 20개")
        if existing:
            title_edit.setText(existing.title)
        planned_edit = QDateEdit()
        planned_edit.setCalendarPopup(True)
        planned_edit.setDisplayFormat("yyyy년 M월 d일")
        selected = (
            QDate.fromString(existing.planned_date, "yyyy-MM-dd")
            if existing
            else QDate(
                self.planner_selected_date.year,
                self.planner_selected_date.month,
                self.planner_selected_date.day,
            )
        )
        planned_edit.setDate(selected)
        deadline_check = QCheckBox("마감일 설정")
        deadline_date = (
            QDate.fromString(existing.deadline_date, "yyyy-MM-dd")
            if existing and existing.deadline_date
            else planned_edit.date()
        )
        deadline_edit = QDateEdit(deadline_date)
        deadline_edit.setCalendarPopup(True)
        deadline_edit.setDisplayFormat("yyyy년 M월 d일")
        deadline_edit.setMinimumDate(planned_edit.date())
        deadline_check.setChecked(bool(existing and existing.deadline_date))
        deadline_edit.setEnabled(deadline_check.isChecked())
        fields = (
            ("할 일", title_edit),
            ("계획일", planned_edit),
        )
        for row_index, (name, control) in enumerate(fields):
            label = QLabel(name)
            label.setObjectName("MetricName")
            form.addWidget(label, row_index, 0)
            form.addWidget(control, row_index, 1)
        deadline_row = QHBoxLayout()
        deadline_row.addWidget(deadline_check)
        deadline_row.addWidget(deadline_edit, 1)
        form.addWidget(QLabel("마감"), len(fields), 0)
        form.addLayout(deadline_row, len(fields), 1)
        form.setColumnStretch(1, 1)
        layout.addLayout(form)

        deadline_check.toggled.connect(deadline_edit.setEnabled)
        planned_edit.dateChanged.connect(deadline_edit.setMinimumDate)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("취소")
        save = QPushButton("저장" if existing else "추가")
        save.setObjectName("PrimaryButton")
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(
            lambda: self._save_planner_task_dialog(
                dialog,
                title_edit,
                planned_edit,
                deadline_check,
                deadline_edit,
                task_id,
            )
        )
        title_edit.returnPressed.connect(save.click)
        dialog.exec()

    def _save_planner_task_dialog(
        self,
        dialog: QDialog,
        title_edit: QLineEdit,
        planned_edit: QDateEdit,
        deadline_check: QCheckBox,
        deadline_edit: QDateEdit,
        task_id: Optional[int],
    ) -> None:
        title = title_edit.text().strip()
        if not title:
            self._show_action_feedback("할 일 이름을 입력하세요", "#F04452")
            title_edit.setFocus()
            return
        if deadline_check.isChecked() and deadline_edit.date() < planned_edit.date():
            self._show_action_feedback(
                "마감일은 계획일보다 빠를 수 없습니다", "#F04452"
            )
            return
        deadline = (
            deadline_edit.date().toString("yyyy-MM-dd")
            if deadline_check.isChecked()
            else None
        )
        existing = next(
            (
                item
                for item in self.database.list_planner_tasks()
                if item.id == task_id
            ),
            None,
        )
        values = {
            "title": title,
            "subject_id": existing.subject_id if existing else None,
            "planned_date": planned_edit.date().toString("yyyy-MM-dd"),
            "deadline_date": deadline,
            "estimated_minutes": existing.estimated_minutes if existing else 0,
            "task_type": existing.task_type if existing else "study",
        }
        if task_id is None:
            self.database.add_planner_task(**values)
        else:
            self.database.update_planner_task(task_id=task_id, **values)
        dialog.accept()
        self._refresh_planner()
        self._show_action_feedback(
            "학습 계획을 수정했습니다"
            if task_id is not None
            else "학습 계획을 추가했습니다",
            "#03A64A",
        )

    def _quick_add_planner_task(self) -> None:
        title = self.planner_quick_title.text().strip()
        if not title:
            self._show_action_feedback("할 일을 입력하세요", "#F04452")
            self.planner_quick_title.setFocus()
            return
        schedule, invalid = self.planner_quick_schedule.values()
        if invalid:
            label = {
                "start": "시작 시각",
                "end": "종료 시각",
                "duration": "소요 시간",
            }[invalid[0]]
            self._show_action_feedback(f"{label}을 확인하세요", "#F04452")
            self.planner_quick_schedule.groups[invalid[0]][1].setFocus()
            return
        self.database.add_planner_task(
            title=title,
            subject_id=None,
            planned_date=self.planner_selected_date.isoformat(),
            deadline_date=None,
            estimated_minutes=schedule["duration"] or 0,
            task_type="study",
            planned_start_minute=schedule["start"],
            planned_end_minute=schedule["end"],
        )
        self.planner_quick_title.clear()
        self.planner_quick_schedule.clear()
        self.planner_quick_title.setFocus()
        self._refresh_planner()
        self._show_action_feedback("학습 계획을 추가했습니다", "#03A64A")

    def _open_planner_time_dialog(self, task_id: int) -> None:
        task = next(
            (
                item
                for item in self.database.list_planner_tasks()
                if item.id == task_id
            ),
            None,
        )
        if task is None:
            self._show_action_feedback("계획을 찾을 수 없습니다", "#F04452")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("시간 설정")
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        title = QLabel(task.title)
        title.setObjectName("SectionTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        hint = QLabel(
            "모두 선택 사항입니다. 두 항목을 입력하면 나머지를 자동으로 계산합니다."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)

        def make_time_fields(duration: bool = False):
            container = QFrame()
            container.setObjectName("PlannerTimeFields")
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(7)
            hour = QLineEdit()
            hour.setObjectName("PlannerTimeNumber")
            hour.setAlignment(Qt.AlignCenter)
            hour.setMaxLength(2)
            hour.setFixedWidth(58)
            hour.setPlaceholderText("0" if duration else "--")
            hour.setValidator(QIntValidator(0, 24 if duration else 23, hour))
            minute = QLineEdit()
            minute.setObjectName("PlannerTimeNumber")
            minute.setAlignment(Qt.AlignCenter)
            minute.setMaxLength(2)
            minute.setFixedWidth(58)
            minute.setPlaceholderText("--")
            minute.setValidator(QIntValidator(0, 59, minute))
            hour_suffix = QLabel("시간" if duration else "시")
            hour_suffix.setObjectName("PlannerTimeSuffix")
            minute_suffix = QLabel("분")
            minute_suffix.setObjectName("PlannerTimeSuffix")
            row.addWidget(hour)
            row.addWidget(hour_suffix)
            row.addWidget(minute)
            row.addWidget(minute_suffix)
            row.addStretch(1)
            return container, hour, minute

        start_fields = make_time_fields()
        end_fields = make_time_fields()
        duration_fields = make_time_fields(duration=True)
        fields = {
            "start": start_fields,
            "end": end_fields,
            "duration": duration_fields,
        }

        def set_group_value(key: str, value: Optional[int]) -> None:
            _container, hour, minute = fields[key]
            hour.blockSignals(True)
            minute.blockSignals(True)
            if value is None:
                hour.clear()
                minute.clear()
            else:
                whole_hours, remaining_minutes = divmod(value, 60)
                hour.setText(str(whole_hours))
                minute.setText(f"{remaining_minutes:02d}")
            hour.blockSignals(False)
            minute.blockSignals(False)

        set_group_value("start", task.planned_start_minute)
        set_group_value("end", task.planned_end_minute)
        set_group_value(
            "duration",
            task.estimated_minutes if task.estimated_minutes > 0 else None,
        )
        labels = {
            "start": "시작 시각",
            "end": "종료 시각",
            "duration": "예상 시간",
        }
        for row_index, key in enumerate(("start", "end", "duration")):
            label = QLabel(labels[key])
            label.setObjectName("MetricName")
            form.addWidget(label, row_index, 0)
            form.addWidget(fields[key][0], row_index, 1)
        form.setColumnStretch(1, 1)
        layout.addLayout(form)

        calculation_status = QLabel("입력 전")
        calculation_status.setObjectName("PlannerCalculationStatus")
        calculation_status.setWordWrap(True)
        layout.addWidget(calculation_status)

        if (
            task.planned_start_minute is not None
            and task.estimated_minutes > 0
        ):
            explicit_order = ["start", "duration"]
        elif (
            task.planned_start_minute is not None
            and task.planned_end_minute is not None
        ):
            explicit_order = ["start", "end"]
        elif task.planned_end_minute is not None and task.estimated_minutes > 0:
            explicit_order = ["end", "duration"]
        else:
            explicit_order = [
                key
                for key, (_container, hour, minute) in fields.items()
                if hour.text().strip() or minute.text().strip()
            ]
        generated = {"key": None}

        def set_calculated_style(key: Optional[str]) -> None:
            for field_key, (_container, hour, minute) in fields.items():
                for field in (hour, minute):
                    field.setProperty("calculated", field_key == key)
                    field.style().unpolish(field)
                    field.style().polish(field)

        def parsed_values() -> dict[str, Optional[int]]:
            return {
                "start": self._parse_planner_clock_parts(
                    start_fields[1].text(), start_fields[2].text()
                ),
                "end": self._parse_planner_clock_parts(
                    end_fields[1].text(), end_fields[2].text()
                ),
                "duration": self._parse_planner_duration_parts(
                    duration_fields[1].text(), duration_fields[2].text()
                ),
            }

        def recalculate() -> None:
            values = parsed_values()
            valid_order = [
                key for key in explicit_order if values.get(key) is not None
            ]
            if len(valid_order) < 2:
                generated["key"] = None
                set_calculated_style(None)
                calculation_status.setText("필요한 값만 입력해도 저장할 수 있습니다.")
                calculation_status.setStyleSheet("color: #8B95A1;")
                return

            source_keys = valid_order[-2:]
            target_key = next(
                key
                for key in ("start", "end", "duration")
                if key not in source_keys
            )
            calculated = self._calculate_planner_time_value(
                target_key,
                values,
            )
            if calculated is None:
                generated["key"] = None
                set_calculated_style(None)
                calculation_status.setText(
                    "두 시각의 간격은 24시간 이내여야 합니다."
                )
                calculation_status.setStyleSheet("color: #F04452;")
                return

            set_group_value(target_key, calculated)
            generated["key"] = target_key
            set_calculated_style(target_key)
            calculation_status.setText(
                f"{labels[target_key]}을(를) 계산했습니다. 맞으면 Enter를 누르세요."
            )
            calculation_status.setStyleSheet("color: #8B95A1;")

        def user_edited(key: str) -> None:
            if key in explicit_order:
                explicit_order.remove(key)
            _container, hour, minute = fields[key]
            if hour.text().strip() or minute.text().strip():
                explicit_order.append(key)
            generated["key"] = None
            recalculate()

        def confirm_calculation() -> None:
            key = generated["key"]
            if key is None:
                return
            generated["key"] = None
            set_calculated_style(None)
            calculation_status.setText("계산값을 확인했습니다.")
            calculation_status.setStyleSheet("color: #03A64A;")

        for key, (_container, hour, minute) in fields.items():
            for field in (hour, minute):
                field.textEdited.connect(
                    lambda _text, field_key=key: user_edited(field_key)
                )
                field.editingFinished.connect(confirm_calculation)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("취소")
        clear = QPushButton("모두 지우기")
        save = QPushButton("저장")
        save.setObjectName("PrimaryButton")
        buttons.addWidget(clear)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        cancel.clicked.connect(dialog.reject)

        def clear_time() -> None:
            explicit_order.clear()
            generated["key"] = None
            for key in fields:
                set_group_value(key, None)
            set_calculated_style(None)
            calculation_status.setText("시간 정보를 비웠습니다.")
            calculation_status.setStyleSheet("color: #8B95A1;")

        def save_time() -> None:
            values = parsed_values()
            invalid = [
                labels[key]
                for key, (_container, hour, minute) in fields.items()
                if (hour.text().strip() or minute.text().strip())
                and values[key] is None
            ]
            if invalid:
                self._show_action_feedback(
                    f"{invalid[0]} 형식을 확인하세요", "#F04452"
                )
                return
            present = [key for key, value in values.items() if value is not None]
            if len(present) >= 2:
                target_key = next(
                    (
                        key
                        for key in ("start", "end", "duration")
                        if key not in present
                    ),
                    None,
                )
                if target_key is not None:
                    values[target_key] = self._calculate_planner_time_value(
                        target_key,
                        values,
                    )
                expected_duration = self._calculate_planner_time_value(
                    "duration",
                    values,
                )
                if expected_duration is None:
                    self._show_action_feedback(
                        "시간 범위를 확인하세요", "#F04452"
                    )
                    return
                values["duration"] = expected_duration
                values["end"] = self._calculate_planner_time_value(
                    "end",
                    values,
                )
            confirm_calculation()
            self._set_planner_task_time(
                task_id,
                values["start"],
                values["duration"] or 0,
                values["end"],
            )
            dialog.accept()

        clear.clicked.connect(clear_time)
        save.clicked.connect(save_time)
        dialog.exec()

    @staticmethod
    def _parse_planner_clock_parts(
        hour_text: str,
        minute_text: str,
    ) -> Optional[int]:
        hour_clean = hour_text.strip()
        minute_clean = minute_text.strip()
        if not hour_clean and not minute_clean:
            return None
        if not hour_clean or not hour_clean.isdigit():
            return None
        if minute_clean and not minute_clean.isdigit():
            return None
        hour = int(hour_clean)
        minute = int(minute_clean) if minute_clean else 0
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            return None
        return hour * 60 + minute

    @staticmethod
    def _parse_planner_duration_parts(
        hour_text: str,
        minute_text: str,
    ) -> Optional[int]:
        hour_clean = hour_text.strip()
        minute_clean = minute_text.strip()
        if not hour_clean and not minute_clean:
            return None
        if hour_clean and not hour_clean.isdigit():
            return None
        if minute_clean and not minute_clean.isdigit():
            return None
        hour = int(hour_clean) if hour_clean else 0
        minute = int(minute_clean) if minute_clean else 0
        if not 0 <= minute <= 59:
            return None
        duration = hour * 60 + minute
        return duration if 1 <= duration <= 1440 else None

    @staticmethod
    def _format_planner_clock(minute: int) -> str:
        hour, remainder = divmod(minute % (24 * 60), 60)
        return f"{hour:02d}:{remainder:02d}"

    @staticmethod
    def _calculate_planner_time_value(
        target: str,
        values: dict[str, Optional[int]],
    ) -> Optional[int]:
        start = values.get("start")
        end = values.get("end")
        duration = values.get("duration")
        if target == "end" and start is not None and duration is not None:
            return (start + duration) % (24 * 60)
        if target == "start" and end is not None and duration is not None:
            return (end - duration) % (24 * 60)
        if target == "duration" and start is not None and end is not None:
            difference = (end - start) % (24 * 60)
            return difference if difference > 0 else 24 * 60
        return None

    def _save_planner_task_title(
        self,
        task_id: int,
        field: QLineEdit,
        original: str,
    ) -> None:
        title = field.text().strip()
        if not title:
            field.setText(original)
            self._show_action_feedback("할 일 제목은 비워둘 수 없습니다", "#F04452")
            return
        if title == original:
            return
        self.database.update_planner_task_title(task_id, title)
        field.setText(title)
        self._show_action_feedback("할 일 제목을 저장했습니다", "#03A64A")

    def _save_planner_task_schedule(
        self,
        task_id: int,
        planned_start_minute: Optional[int],
        estimated_minutes: int,
        planned_end_minute: Optional[int],
    ) -> None:
        self.database.set_planner_task_time(
            task_id,
            planned_start_minute,
            estimated_minutes,
            planned_end_minute,
        )
        tasks = self.database.list_planner_tasks()
        estimated_for_day = sum(
            task.estimated_minutes
            for task in tasks
            if self._parse_date(task.planned_date) == self.planner_selected_date
        )
        self.planner_estimated_value.setText(
            self._fmt_record_duration(estimated_for_day * 60)
        )
        self._refresh_planner_timeline(planner_tasks=tasks)

    def _set_planner_task_time(
        self,
        task_id: int,
        planned_start_minute: Optional[int],
        estimated_minutes: int,
        planned_end_minute: Optional[int] = None,
    ) -> None:
        self.database.set_planner_task_time(
            task_id,
            planned_start_minute,
            estimated_minutes,
            planned_end_minute,
        )
        self._refresh_planner()
        self._show_action_feedback("선택 시간 정보를 저장했습니다", "#03A64A")

    def _cycle_planner_task_status(self, task_id: int, current: str) -> None:
        next_status = {
            "pending": "completed",
            "completed": "deferred",
            "deferred": "pending",
        }.get(current, "pending")
        self.database.set_planner_task_status(task_id, next_status)
        self._refresh_planner()
        message, color = {
            "pending": ("상태를 공란으로 바꿨습니다", "#1B64DA"),
            "completed": ("할 일을 완료했습니다", "#03A64A"),
            "deferred": ("할 일을 보류했습니다", "#F59E0B"),
        }[next_status]
        self._show_action_feedback(
            message,
            color,
        )

    def _delete_planner_task(self, task_id: int, title: str) -> None:
        if (
            task_id == self.active_task_id
            and self.session.app_state in (AppState.RUNNING, AppState.BREAK)
        ):
            self._show_action_feedback(
                "학습 중인 할 일은 세션 종료 후 삭제할 수 있습니다",
                "#F59E0B",
            )
            return
        answer = QMessageBox.question(
            self,
            "할 일 삭제",
            f"'{title}'을 삭제할까요?\n연결된 학습 기록은 그대로 유지됩니다.",
        )
        if answer != QMessageBox.Yes:
            return
        self.database.delete_planner_task(task_id)
        self._refresh_planner()
        self._show_action_feedback("할 일을 삭제했습니다", "#F04452")

    def _move_planner_date(self, days: int) -> None:
        self.planner_selected_date += timedelta(days=days)
        selected = self.planner_selected_date
        self.planner_calendar.setSelectedDate(
            QDate(selected.year, selected.month, selected.day)
        )
        self._refresh_planner()

    def _go_to_today_planner(self) -> None:
        self.planner_selected_date = self._study_date_for_datetime(datetime.now())
        selected = self.planner_selected_date
        self.planner_calendar.setSelectedDate(
            QDate(selected.year, selected.month, selected.day)
        )
        self._refresh_planner()

    def _open_planner_calendar(self) -> None:
        selected = self.planner_selected_date
        self.planner_calendar.setSelectedDate(
            QDate(selected.year, selected.month, selected.day)
        )
        self.planner_calendar_dialog.show()
        self.planner_calendar_dialog.raise_()
        self.planner_calendar_dialog.activateWindow()

    def _planner_calendar_date_selected(self, selected: QDate) -> None:
        self.planner_selected_date = selected.toPython()
        self.planner_calendar_dialog.hide()
        self._refresh_planner()

    def _refresh_planner_calendar(self, tasks) -> None:
        for highlighted in self.planner_highlighted_dates:
            self.planner_calendar.setDateTextFormat(
                QDate(highlighted.year, highlighted.month, highlighted.day),
                QTextCharFormat(),
            )
        self.planner_highlighted_dates.clear()
        planned_format = QTextCharFormat()
        planned_format.setBackground(QColor("#E9FAF1"))
        planned_format.setForeground(QColor("#067647"))
        deadline_format = QTextCharFormat()
        deadline_format.setBackground(QColor("#FFF1F2"))
        deadline_format.setForeground(QColor("#D92D3A"))
        deadline_format.setFontWeight(QFont.Bold)
        for task in tasks:
            if task.completed_at is not None:
                continue
            planned = self._parse_date(task.planned_date)
            deadline = self._parse_date(task.deadline_date)
            if planned is not None:
                self.planner_calendar.setDateTextFormat(
                    QDate(planned.year, planned.month, planned.day),
                    planned_format,
                )
                self.planner_highlighted_dates.add(planned)
            if deadline is not None:
                self.planner_calendar.setDateTextFormat(
                    QDate(deadline.year, deadline.month, deadline.day),
                    deadline_format,
                )
                self.planner_highlighted_dates.add(deadline)

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    @classmethod
    def _format_d_day(
        cls,
        deadline_value: Optional[str],
        today: Optional[date] = None,
    ) -> str:
        deadline = cls._parse_date(deadline_value)
        if deadline is None:
            return ""
        current = today or datetime.now().date()
        remaining = (deadline - current).days
        if remaining == 0:
            return "D-Day"
        if remaining > 0:
            return f"D-{remaining}"
        return f"{abs(remaining)}일 지남"

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            child_layout = item.layout()
            if child_layout is not None:
                MainWindow._clear_layout(child_layout)

    def _set_records_period(self, period: str) -> None:
        self.records_period = period
        self.records_stack.setCurrentIndex(0 if period == "day" else 1)
        self._update_records_period_buttons()
        self._refresh_records()
        label = {"day": "일간", "week": "주간", "month": "월간"}.get(period, period)
        self._show_action_feedback(f"기록 보기: {label}")

    def _move_records_date(self, direction: int) -> None:
        current = self.records_date_edit.date()
        if self.records_period == "month":
            target = current.addMonths(direction)
        elif self.records_period == "week":
            target = current.addDays(direction * 7)
        else:
            target = current.addDays(direction)
        if target > QDate.currentDate():
            target = QDate.currentDate()
        self.records_date_edit.setDate(target)

    def _records_date_changed(self, selected: QDate) -> None:
        self.records_selected_date = selected.toPython()
        self._refresh_records()

    def _records_day_start_changed(self) -> None:
        hour = int(self.records_day_start_combo.currentData())
        if hour == self.settings.study_day_start_hour:
            return
        self.settings.study_day_start_hour = hour
        self._persist_settings()
        self._refresh_records()
        self._show_action_feedback(f"학습일 시작: {hour:02d}:00", "#03A64A")

    def _open_records_dialog(self) -> None:
        self._refresh_records()
        self.records_dialog.show()
        self.records_dialog.raise_()
        self.records_dialog.activateWindow()

    def _update_records_period_buttons(self) -> None:
        self.day_records_button.setChecked(self.records_period == "day")
        self.week_records_button.setChecked(self.records_period == "week")
        self.month_records_button.setChecked(self.records_period == "month")
        is_day = self.records_period == "day"
        self.records_date_edit.setVisible(is_day)
        self.records_period_label.setVisible(not is_day)
        if not is_day:
            self.records_period_label.setText(self._period_name())
        today = datetime.now().date()
        if self.records_period == "month":
            can_move_next = (
                self.records_selected_date.year,
                self.records_selected_date.month,
            ) < (today.year, today.month)
        elif self.records_period == "week":
            _start, selected_end = self._week_bounds(self.records_selected_date)
            _current_start, current_end = self._week_bounds(today)
            can_move_next = selected_end < current_end
        else:
            can_move_next = self.records_selected_date < today
        self.next_record_day_button.setEnabled(can_move_next)

    def _refresh_records_dashboard(self, rows) -> None:
        self._update_records_period_buttons()
        filtered = self._filter_record_rows(rows)
        daily_buckets = self._build_daily_hour_buckets(filtered)
        if self.records_period == "day":
            focus = sum(bucket["focus"] for bucket in daily_buckets)
            non_focus = sum(bucket["non_focus"] for bucket in daily_buckets)
            break_seconds = sum(bucket["break"] for bucket in daily_buckets)
            unscored = sum(bucket["unscored"] for bucket in daily_buckets)
        else:
            period_start, period_end = self._record_period_bounds()
            totals = self._state_totals_for_interval(
                filtered,
                period_start,
                period_end,
            )
            focus = totals["focus"]
            non_focus = totals["non_focus"]
            break_seconds = totals["break"]
            unscored = totals["unscored"]
        scored = focus + non_focus
        focus_ratio = 0.0 if scored <= 0 else focus / scored
        longest_focus = min(
            focus,
            max(
                (row.longest_focus_seconds for row in filtered),
                default=0.0,
            ),
        )

        self.records_focus_ratio.setText(f"{focus_ratio * 100:.0f}%")
        self.records_focus_time.setText(self._fmt_record_duration(focus))
        self.records_study_time.setText(self._fmt_record_duration(scored))
        self.records_longest_focus.setText(
            self._fmt_record_duration(longest_focus)
        )

        self.daily_summary_donut.set_values(
            focus,
            non_focus,
            break_seconds,
            unscored,
        )
        self.daily_study_time.setText(self._fmt_record_duration(scored))
        self.daily_focus_time.setText(self._fmt_record_duration(focus))
        self.daily_non_focus_time.setText(self._fmt_record_duration(non_focus))
        self.daily_break_time.setText(self._fmt_record_duration(break_seconds))
        self.daily_unscored_time.setText(self._fmt_record_duration(unscored))
        self.daily_focus_ratio.setText(f"{focus_ratio * 100:.0f}%")
        self.daily_longest_focus.setText(
            self._fmt_record_duration(longest_focus)
        )

        daily_points = self._daily_hour_points_from_buckets(daily_buckets)
        self.daily_hour_chart.set_points(daily_points)
        self.daily_hour_focus.setText(self._fmt_record_duration(focus))
        self.daily_hour_non_focus.setText(self._fmt_record_duration(non_focus))
        active_hours = [
            (index, bucket)
            for index, bucket in enumerate(daily_buckets)
            if bucket["focus"] + bucket["non_focus"] > 0
        ]
        if active_hours:
            best_index, best_bucket = max(
                active_hours,
                key=lambda item: (
                    self._ratio(item[1]["focus"], item[1]["non_focus"]),
                    item[1]["focus"] + item[1]["non_focus"],
                ),
            )
            long_index, long_bucket = max(
                active_hours,
                key=lambda item: item[1]["focus"] + item[1]["non_focus"],
            )
            best_hour = daily_points[best_index][0]
            long_hour = daily_points[long_index][0]
            best_ratio = self._ratio(
                best_bucket["focus"], best_bucket["non_focus"]
            )
            self.daily_best_focus_hour.setText(
                f"{best_hour}시 · {best_ratio * 100:.0f}%"
            )
            self.daily_longest_study_hour.setText(
                f"{long_hour}시 · "
                f"{self._fmt_record_duration(long_bucket['focus'] + long_bucket['non_focus'])}"
            )
        else:
            self.daily_best_focus_hour.setText("-")
            self.daily_longest_study_hour.setText("-")

        is_month = self.records_period == "month"
        self.records_trend_chart.setVisible(not is_month)
        self.records_activity_chart.setVisible(is_month)
        self.records_chart_title.setText(
            self._records_period_title()
        )
        self.records_chart_hint.setText(
            "색이 진할수록 순공시간이 깁니다."
            if is_month
            else "막대 높이와 색은 집중률을 나타냅니다."
        )
        self.records_trend_chart.set_points(
            self._build_period_points(filtered),
            f"{self._period_name()} 기록이 없습니다.",
        )
        days, first_weekday = self._build_month_activity(filtered)
        self.records_activity_chart.set_days(
            days,
            first_weekday,
            "이번 달 학습 기록이 없습니다.",
        )

        study_dates = {
            study_date
            for study_date in self._record_period_dates()
            if sum(
                self._state_totals_for_interval(
                    filtered,
                    *self._study_day_bounds(study_date),
                ).values()
            )
            > 0
        }
        average_session = 0.0 if not filtered else scored / len(filtered)
        pomodoro_cycles = sum(
            row.pomodoro_cycles_completed for row in filtered
        )
        self.records_study_days.setText(f"{len(study_dates)}일")
        self.records_average_session.setText(
            f"{len(filtered)}회 · 평균 {self._fmt_record_duration(average_session)}"
        )
        self.records_best_period.setText(self._best_record_period(filtered))
        self.records_pomodoro.setText(f"{pomodoro_cycles}회")
        period_name = self._period_name()
        self.records_session_summary_label.setText(
            f"{period_name} 세션 {len(filtered)}개 · "
            f"순공 {self._fmt_record_duration(focus)} · "
            f"집중률 {focus_ratio * 100:.0f}%"
        )

    def _filter_record_rows(self, rows):
        start, end = self._record_period_bounds()
        return [row for row in rows if self._row_overlaps(row, start, end)]

    def _build_period_points(self, rows) -> List[tuple[str, float]]:
        if self.records_period == "day":
            return [
                (label, rate)
                for label, _study, rate, _rest in self._build_daily_hour_points(rows)
            ]

        if self.records_period == "week":
            start, _end = self._week_bounds(self.records_selected_date)
            days = [start + timedelta(days=offset) for offset in range(7)]
            weekdays = ("월", "화", "수", "목", "금", "토", "일")
            return [
                (
                    f"{day.month}/{day.day}\n{weekdays[day.weekday()]}",
                    self._ratio(
                        totals["focus"],
                        totals["non_focus"],
                    ),
                )
                for day in days
                for totals in [
                    self._state_totals_for_interval(
                        rows,
                        *self._study_day_bounds(day),
                    )
                ]
            ]

        first = self.records_selected_date.replace(day=1)
        day_count = calendar.monthrange(first.year, first.month)[1]
        days = [first + timedelta(days=offset) for offset in range(day_count)]
        return [
            (
                str(day.day),
                self._ratio(totals["focus"], totals["non_focus"]),
            )
            for day in days
            for totals in [
                self._state_totals_for_interval(
                    rows,
                    *self._study_day_bounds(day),
                )
            ]
        ]

    def _build_month_activity(self, rows) -> tuple[List[tuple[int, float]], int]:
        first = self.records_selected_date.replace(day=1)
        day_count = calendar.monthrange(first.year, first.month)[1]
        totals = []
        for day_number in range(1, day_count + 1):
            study_date = first.replace(day=day_number)
            values = self._state_totals_for_interval(
                rows,
                *self._study_day_bounds(study_date),
            )
            totals.append((day_number, values["focus"]))
        return totals, first.weekday()

    def _build_daily_hour_points(
        self, rows
    ) -> List[tuple[str, float, float, float]]:
        return self._daily_hour_points_from_buckets(
            self._build_daily_hour_buckets(rows)
        )

    def _build_ten_minute_timetable_slots(
        self,
        rows,
        study_date: date,
    ) -> List[Tuple[Optional[float], Optional[EffectiveState]]]:
        day_start, day_end = self._study_day_bounds(study_date)
        day_rows = [
            row for row in rows if self._row_overlaps(row, day_start, day_end)
        ]
        slot_totals = [
            {"focus": 0.0, "non_focus": 0.0, "break": 0.0, "unscored": 0.0}
            for _ in range(144)
        ]
        legacy_rows = []

        def add_minute_buckets(started: datetime, buckets) -> None:
            cursor = started
            for bucket in buckets:
                normalized = {
                    "focus": 0.0,
                    "non_focus": 0.0,
                    "break": 0.0,
                    "unscored": 0.0,
                }
                for state, seconds in bucket.items():
                    key = getattr(state, "value", str(state))
                    target = "unscored" if key == "absent_pending" else key
                    if target in normalized:
                        normalized[target] += max(0.0, float(seconds))
                duration = sum(normalized.values())
                if duration <= 0:
                    continue
                bucket_end = cursor + timedelta(seconds=duration)
                first_index = max(
                    0,
                    int((cursor - day_start).total_seconds() // 600),
                )
                last_index = min(
                    143,
                    int(
                        max(0.0, (bucket_end - day_start).total_seconds() - 1e-6)
                        // 600
                    ),
                )
                for index in range(first_index, last_index + 1):
                    slot_start = day_start + timedelta(minutes=index * 10)
                    slot_end = slot_start + timedelta(minutes=10)
                    overlap = max(
                        0.0,
                        (min(bucket_end, slot_end) - max(cursor, slot_start)).total_seconds(),
                    )
                    if overlap <= 0:
                        continue
                    share = overlap / duration
                    for state, seconds in normalized.items():
                        slot_totals[index][state] += seconds * share
                cursor = bucket_end

        for row in day_rows:
            started = self._row_started_datetime(row)
            try:
                buckets = json.loads(getattr(row, "timeline_json", "[]") or "[]")
            except (TypeError, ValueError, json.JSONDecodeError):
                buckets = []
            if started is not None and buckets:
                add_minute_buckets(started, buckets)
            else:
                legacy_rows.append(row)

        if (
            self.session.app_state in (AppState.RUNNING, AppState.BREAK)
            and self.session.started_at_wall
        ):
            try:
                active_started = datetime.strptime(
                    self.session.started_at_wall,
                    "%Y-%m-%d %H:%M:%S",
                )
            except ValueError:
                active_started = None
            if active_started is not None and active_started < day_end:
                add_minute_buckets(
                    active_started,
                    self.session.metrics.minute_buckets,
                )

        slots: List[Tuple[Optional[float], Optional[EffectiveState]]] = []
        for index in range(144):
            slot_start = day_start + timedelta(minutes=index * 10)
            slot_end = slot_start + timedelta(minutes=10)
            totals = slot_totals[index]
            legacy = self._state_totals_for_interval(
                legacy_rows,
                slot_start,
                slot_end,
            )
            for state, seconds in legacy.items():
                totals[state] += seconds
            focus = totals["focus"]
            non_focus = totals["non_focus"]
            scored = focus + non_focus
            break_seconds = totals["break"]
            unscored = totals["unscored"]
            if scored + break_seconds + unscored <= 0:
                slots.append((None, None))
            elif break_seconds >= scored and break_seconds >= unscored:
                slots.append((None, EffectiveState.BREAK))
            elif unscored > scored:
                slots.append((None, EffectiveState.UNSCORED))
            else:
                slots.append(
                    (
                        self._ratio(focus, non_focus),
                        EffectiveState.FOCUS
                        if focus >= non_focus
                        else EffectiveState.NON_FOCUS,
                    )
                )
        return slots

    def _build_daily_hour_buckets(self, rows, study_date=None):
        selected_date = study_date or self.records_selected_date
        day_start, day_end = self._study_day_bounds(selected_date)
        buckets = [
            {"focus": 0.0, "non_focus": 0.0, "break": 0.0, "unscored": 0.0}
            for _ in range(24)
        ]
        for row in rows:
            started = self._row_started_datetime(row)
            ended = self._row_ended_datetime(row)
            if started is None:
                continue
            total_state_seconds = (
                row.focus_seconds
                + row.non_focus_seconds
                + row.break_seconds
                + row.unscored_seconds
                + getattr(row, "absent_pending_seconds", 0.0)
            )
            if ended is None or ended <= started:
                ended = started + timedelta(seconds=max(1.0, total_state_seconds))
            session_seconds = max(1.0, (ended - started).total_seconds())
            overlap_start = max(started, day_start)
            overlap_end = min(ended, day_end)
            if overlap_end <= overlap_start:
                continue
            for index in range(24):
                hour_start = day_start + timedelta(hours=index)
                hour_end = hour_start + timedelta(hours=1)
                seconds = max(
                    0.0,
                    (min(overlap_end, hour_end) - max(overlap_start, hour_start)).total_seconds(),
                )
                if seconds <= 0:
                    continue
                share = seconds / session_seconds
                buckets[index]["focus"] += row.focus_seconds * share
                buckets[index]["non_focus"] += row.non_focus_seconds * share
                buckets[index]["break"] += row.break_seconds * share
                buckets[index]["unscored"] += (
                    row.unscored_seconds
                    + getattr(row, "absent_pending_seconds", 0.0)
                ) * share
        return buckets

    def _daily_hour_points_from_buckets(
        self, buckets
    ) -> List[tuple[str, float, float, float]]:
        start_hour = self.settings.study_day_start_hour
        points = []
        for index, bucket in enumerate(buckets):
            focus = bucket["focus"]
            non_focus = bucket["non_focus"]
            points.append(
                (
                    f"{(start_hour + index) % 24:02d}",
                    focus + non_focus,
                    self._ratio(focus, non_focus),
                    bucket["break"] + bucket["unscored"],
                )
            )
        return points

    def _best_record_period(self, rows) -> str:
        if not rows:
            return "-"
        if self.records_period == "day":
            buckets = self._build_daily_hour_buckets(rows)
            active = [
                (index, bucket)
                for index, bucket in enumerate(buckets)
                if bucket["focus"] > 0
            ]
            if not active:
                return "-"
            index, bucket = max(active, key=lambda item: item[1]["focus"])
            hour = (self.settings.study_day_start_hour + index) % 24
            return f"{hour:02d}시 · {self._fmt_record_duration(bucket['focus'])}"

        totals = {
            study_date: self._state_totals_for_interval(
                rows,
                *self._study_day_bounds(study_date),
            )["focus"]
            for study_date in self._record_period_dates()
        }
        if not totals:
            return "-"
        day, focus = max(totals.items(), key=lambda item: item[1])
        return f"{day.month}/{day.day} · {self._fmt_record_duration(focus)}"

    def _period_name(self) -> str:
        if self.records_period == "day":
            return (
                f"{self.records_selected_date.year}년 "
                f"{self.records_selected_date.month}월 "
                f"{self.records_selected_date.day}일"
            )
        if self.records_period == "week":
            start, end = self._week_bounds(self.records_selected_date)
            if start.year != end.year:
                return (
                    f"{start.year}년 {start.month}월 {start.day}일 ~ "
                    f"{end.year}년 {end.month}월 {end.day}일"
                )
            if start.month != end.month:
                return (
                    f"{start.year}년 {start.month}월 {start.day}일 ~ "
                    f"{end.month}월 {end.day}일"
                )
            return (
                f"{start.year}년 {start.month}월 {start.day}일 ~ "
                f"{end.month}월 {end.day}일"
            )
        if self.records_period == "month":
            return (
                f"{self.records_selected_date.year}년 "
                f"{self.records_selected_date.month}월"
            )
        return "선택 기간"

    def _records_period_title(self) -> str:
        if self.records_period == "month":
            return f"{self._period_name()} 학습 활동"
        if self.records_period == "week":
            return f"{self._period_name()} 집중률"
        return "시간대별 집중률"

    def _study_day_bounds(self, study_date) -> tuple[datetime, datetime]:
        start = datetime.combine(study_date, datetime.min.time()) + timedelta(
            hours=self.settings.study_day_start_hour
        )
        return start, start + timedelta(days=1)

    def _record_period_dates(self) -> List[date]:
        if self.records_period == "day":
            return [self.records_selected_date]
        if self.records_period == "week":
            start, _end = self._week_bounds(self.records_selected_date)
            return [start + timedelta(days=offset) for offset in range(7)]
        first = self.records_selected_date.replace(day=1)
        day_count = calendar.monthrange(first.year, first.month)[1]
        return [first + timedelta(days=offset) for offset in range(day_count)]

    def _record_period_bounds(self) -> tuple[datetime, datetime]:
        dates = self._record_period_dates()
        start, _unused = self._study_day_bounds(dates[0])
        end, _unused = self._study_day_bounds(dates[-1] + timedelta(days=1))
        return start, end

    def _state_totals_for_interval(
        self,
        rows,
        interval_start: datetime,
        interval_end: datetime,
    ) -> dict[str, float]:
        totals = {
            "focus": 0.0,
            "non_focus": 0.0,
            "break": 0.0,
            "unscored": 0.0,
        }
        for row in rows:
            started = self._row_started_datetime(row)
            if started is None:
                continue
            state_seconds = {
                "focus": max(0.0, float(row.focus_seconds)),
                "non_focus": max(0.0, float(row.non_focus_seconds)),
                "break": max(0.0, float(row.break_seconds)),
                "unscored": max(
                    0.0,
                    float(row.unscored_seconds)
                    + float(getattr(row, "absent_pending_seconds", 0.0)),
                ),
            }
            total_state_seconds = sum(state_seconds.values())
            ended = self._row_ended_datetime(row)
            if ended is None or ended <= started:
                ended = started + timedelta(seconds=max(1.0, total_state_seconds))
            session_seconds = max(1.0, (ended - started).total_seconds())
            overlap_seconds = max(
                0.0,
                (
                    min(ended, interval_end) - max(started, interval_start)
                ).total_seconds(),
            )
            if overlap_seconds <= 0:
                continue
            share = overlap_seconds / session_seconds
            for state, seconds in state_seconds.items():
                totals[state] += seconds * share
        return totals

    @staticmethod
    def _week_bounds(anchor) -> tuple:
        days_since_sunday = (anchor.weekday() + 1) % 7
        start = anchor - timedelta(days=days_since_sunday)
        return start, start + timedelta(days=6)

    def _row_study_date(self, row):
        started = self._row_started_datetime(row)
        if started is None:
            return None
        return self._study_date_for_datetime(started)

    def _study_date_for_datetime(self, value: datetime) -> date:
        return (
            value - timedelta(hours=self.settings.study_day_start_hour)
        ).date()

    def _row_overlaps(
        self,
        row,
        range_start: datetime,
        range_end: datetime,
    ) -> bool:
        started = self._row_started_datetime(row)
        if started is None:
            return False
        ended = self._row_ended_datetime(row)
        if ended is None or ended <= started:
            duration = sum(
                max(0.0, float(getattr(row, field, 0.0)))
                for field in (
                    "focus_seconds",
                    "non_focus_seconds",
                    "break_seconds",
                    "unscored_seconds",
                    "absent_pending_seconds",
                )
            )
            ended = started + timedelta(seconds=max(1.0, duration))
        return started < range_end and ended > range_start

    @staticmethod
    def _ratio(focus: float, non_focus: float) -> float:
        denominator = focus + non_focus
        return 0.0 if denominator <= 0 else focus / denominator

    @staticmethod
    def _row_started_datetime(row) -> Optional[datetime]:
        try:
            return datetime.strptime(row.started_at_wall, "%Y-%m-%d %H:%M:%S")
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _row_ended_datetime(row) -> Optional[datetime]:
        try:
            return datetime.strptime(row.ended_at_wall, "%Y-%m-%d %H:%M:%S")
        except (AttributeError, TypeError, ValueError):
            return None

    def _row_started_date(self, row):
        started = self._row_started_datetime(row)
        return started.date() if started is not None else None

    def _refresh_records(self) -> None:
        rows = self.database.list_sessions(None)
        filtered = self._filter_record_rows(rows)
        self.records_table.setRowCount(0)
        for table_row, row in enumerate(filtered):
            self.records_table.insertRow(table_row)
            started = self._row_started_datetime(row)
            started_text = (
                started.strftime("%m/%d %H:%M")
                if started is not None
                else row.started_at_wall
            )
            mode_text = "뽀모도로" if row.session_mode == "pomodoro" else "자유 학습"
            values = [
                started_text,
                mode_text,
                self._fmt_record_duration(row.focus_seconds + row.non_focus_seconds),
                self._fmt_record_duration(row.focus_seconds),
                f"{row.focus_ratio * 100:.0f}%",
                self._fmt_record_duration(row.longest_focus_seconds),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.records_table.setItem(table_row, column, item)
        self._refresh_records_dashboard(rows)
        if filtered:
            self.records_table.selectRow(0)

    def _delete_selected_record(self) -> None:
        session_id = self._selected_session_id()
        if session_id is None:
            self._show_action_feedback("삭제할 기록을 선택하세요", "#F04452")
            return
        answer = QMessageBox.question(
            self,
            "기록 삭제",
            "선택한 학습 기록을 목록에서 삭제할까요?\n저장된 결과 파일은 유지됩니다.",
        )
        if answer != QMessageBox.Yes:
            self._show_action_feedback("기록 삭제를 취소했습니다")
            return
        self.database.delete_session(session_id)
        self._refresh_records()
        self._refresh_planner()
        self._show_action_feedback("선택 기록을 삭제했습니다", "#03A64A")

    def _selected_session_id(self) -> Optional[int]:
        selected = self.records_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        item = self.records_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value is not None else None

    @staticmethod
    def _fmt(seconds: float) -> str:
        total = int(seconds)
        return f"{total // 60:02d}:{total % 60:02d}"

    @staticmethod
    def _fmt_record_duration(seconds: float) -> str:
        total_minutes = int(max(0.0, seconds) // 60)
        hours, minutes = divmod(total_minutes, 60)
        if hours and minutes:
            return f"{hours}시간 {minutes}분"
        if hours:
            return f"{hours}시간"
        return f"{minutes}분"

    @staticmethod
    def _fmt_countdown(seconds: float) -> str:
        total = int(math.ceil(max(0.0, seconds)))
        return f"{total // 60:02d}:{total % 60:02d}"


def run() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
