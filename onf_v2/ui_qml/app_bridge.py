from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtMultimedia import QSoundEffect

from onf_v2.app.alert_sounds import ALERT_SOUND_KEYS, ensure_alert_sound_files
from onf_v2.app.session_database import SessionDatabase, SessionRow
from onf_v2.app.settings_store import SettingsStore, UserSettings


class AppBridge(QObject):
    dataChanged = Signal()
    settingsChanged = Signal()

    def __init__(
        self,
        database: Optional[SessionDatabase] = None,
        settings_store: Optional[SettingsStore] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.database = database or SessionDatabase(Path("sessions") / "onf.sqlite3")
        self.settings_store = settings_store or SettingsStore()
        self._settings = self.settings_store.load()
        self._records_date = date.today()
        self._planner_date = date.today()
        self._planner_tasks: List[Dict[str, Any]] = []
        self._daily_summary: Dict[str, Any] = {}
        self._daily_hourly_data: List[Dict[str, Any]] = []
        self._weekly_records: List[Dict[str, Any]] = []
        self._monthly_levels: List[int] = []
        self._monthly_summary: Dict[str, Any] = {}
        self._sound_effect = QSoundEffect(self)
        self._sound_paths = ensure_alert_sound_files(self.settings_store.path.parent / "sounds")
        self.refresh()

    @Property("QVariantList", notify=dataChanged)
    def plannerTasks(self) -> List[Dict[str, Any]]:
        return self._planner_tasks

    @Property("QVariantMap", notify=dataChanged)
    def dailySummary(self) -> Dict[str, Any]:
        return self._daily_summary

    @Property("QVariantList", notify=dataChanged)
    def dailyHourlyData(self) -> List[Dict[str, Any]]:
        return self._daily_hourly_data

    @Property("QVariantList", notify=dataChanged)
    def weeklyRecords(self) -> List[Dict[str, Any]]:
        return self._weekly_records

    @Property("QVariantList", notify=dataChanged)
    def monthlyLevels(self) -> List[int]:
        return self._monthly_levels

    @Property("QVariantMap", notify=dataChanged)
    def monthlySummary(self) -> Dict[str, Any]:
        return self._monthly_summary

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self) -> Dict[str, Any]:
        return asdict(self._settings)

    @Property(str, notify=dataChanged)
    def dayLabel(self) -> str:
        return _date_label(self._records_date)

    @Property(str, notify=dataChanged)
    def plannerDayLabel(self) -> str:
        return _date_label(self._planner_date)

    @Property(str, notify=dataChanged)
    def weekLabel(self) -> str:
        start = self._records_date - timedelta(days=self._records_date.weekday())
        end = start + timedelta(days=6)
        return f"{start.year}년 {start.month}월 {start.day}일 ~ {end.month}월 {end.day}일"

    @Property(str, notify=dataChanged)
    def monthLabel(self) -> str:
        return f"{self._records_date.year}년 {self._records_date.month}월"

    @Slot()
    def refresh(self) -> None:
        rows = self.database.list_sessions(None)
        self._planner_tasks = self._load_planner_tasks()
        self._daily_summary, self._daily_hourly_data = self._build_daily(rows)
        self._weekly_records = self._build_weekly(rows)
        self._monthly_levels, self._monthly_summary = self._build_monthly(rows)
        self.dataChanged.emit()

    @Slot(int, int)
    def shiftRecords(self, period_index: int, direction: int) -> None:
        direction = -1 if direction < 0 else 1
        if period_index == 2:
            month = self._records_date.month + direction
            year = self._records_date.year
            if month < 1:
                month, year = 12, year - 1
            elif month > 12:
                month, year = 1, year + 1
            self._records_date = date(year, month, 1)
        elif period_index == 1:
            self._records_date += timedelta(days=7 * direction)
        else:
            self._records_date += timedelta(days=direction)
        self.refresh()

    @Slot(int)
    def shiftPlannerDate(self, direction: int) -> None:
        self._planner_date += timedelta(days=-1 if direction < 0 else 1)
        self.refresh()

    @Slot(str, str, str, str, result=bool)
    def addPlannerTask(self, title: str, start: str, end: str, duration: str) -> bool:
        clean_title = title.strip()
        if not clean_title:
            return False
        start_minute = _parse_time(start)
        end_minute = _parse_time(end)
        duration_minutes = _parse_duration(duration)
        if duration_minutes == 0 and start_minute is not None and end_minute is not None:
            duration_minutes = (end_minute - start_minute) % (24 * 60)
        self.database.add_planner_task(
            title=clean_title,
            subject_id=None,
            planned_date=self._planner_date.isoformat(),
            deadline_date=None,
            estimated_minutes=duration_minutes,
            task_type="study",
            planned_start_minute=start_minute,
            planned_end_minute=end_minute,
        )
        self.refresh()
        return True

    @Slot(int)
    def cyclePlannerTask(self, task_id: int) -> None:
        if task_id < 0:
            return
        rows = {row.id: row for row in self.database.list_planner_tasks()}
        row = rows.get(task_id)
        if row is None:
            return
        next_status = {"pending": "completed", "completed": "deferred", "deferred": "pending"}[row.status]
        self.database.set_planner_task_status(task_id, next_status)
        self.refresh()

    @Slot(int)
    def deletePlannerTask(self, task_id: int) -> None:
        if task_id >= 0:
            self.database.delete_planner_task(task_id)
            self.refresh()

    @Slot(int, str, str, str, str)
    def updatePlannerTask(self, task_id: int, title: str, start: str, end: str, duration: str) -> None:
        if task_id < 0 or not title.strip():
            return
        start_minute = _parse_time(start)
        end_minute = _parse_time(end)
        duration_minutes = _parse_duration(duration)
        self.database.update_planner_task(
            task_id=task_id,
            title=title.strip(),
            subject_id=None,
            planned_date=self._planner_date.isoformat(),
            deadline_date=None,
            estimated_minutes=duration_minutes,
            task_type="study",
        )
        self.database.set_planner_task_time(
            task_id,
            start_minute,
            duration_minutes,
            end_minute,
        )
        self.refresh()

    @Slot("QVariantMap")
    def saveSettings(self, values: Dict[str, Any]) -> None:
        merged = asdict(self._settings)
        merged.update(dict(values))
        self._settings = UserSettings.from_dict(merged)
        self.settings_store.save(self._settings)
        self.settingsChanged.emit()

    @Slot(int, str)
    def testAlert(self, volume: int, sound_key: str) -> None:
        key = sound_key if sound_key in ALERT_SOUND_KEYS else self._settings.alert_sound
        path = self._sound_paths.get(key)
        if path is None:
            return
        self._sound_effect.stop()
        self._sound_effect.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self._sound_effect.setVolume(max(0.0, min(1.0, volume / 100.0)))
        self._sound_effect.play()

    def _load_planner_tasks(self) -> List[Dict[str, Any]]:
        rows = [row for row in self.database.list_planner_tasks() if row.planned_date == self._planner_date.isoformat()]
        if not rows:
            return _demo_planner_tasks()
        status_values = {"pending": 0, "completed": 1, "deferred": 2}
        return [
            {
                "taskId": row.id,
                "taskState": status_values.get(row.status, 0),
                "title": row.title,
                "start": _format_minute(row.planned_start_minute),
                "end": _format_minute(row.planned_end_minute),
                "duration": f"{row.estimated_minutes}분" if row.estimated_minutes else "",
                "detail": _task_detail(row.planned_start_minute, row.planned_end_minute, row.estimated_minutes),
                "done": row.status == "completed",
            }
            for row in rows
        ]

    def _build_daily(self, rows: List[SessionRow]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        selected = [row for row in rows if _row_datetime(row).date() == self._records_date]
        if not selected:
            return _demo_daily_summary(), _demo_hourly_data()
        focus = sum(row.focus_seconds for row in selected)
        non_focus = sum(row.non_focus_seconds for row in selected)
        breaks = sum(row.break_seconds for row in selected)
        unscored = sum(row.unscored_seconds + row.absent_pending_seconds for row in selected)
        scored = focus + non_focus
        summary = {
            "study": _duration_text(scored),
            "focus": _duration_text(focus),
            "away": _duration_text(non_focus),
            "break": _duration_text(breaks),
            "unscored": _duration_text(unscored),
            "ratio": round(focus / scored * 100) if scored else 0,
            "longest": _duration_text(max((row.longest_focus_seconds for row in selected), default=0)),
        }
        return summary, _hourly_from_rows(selected)

    def _build_weekly(self, rows: List[SessionRow]) -> List[Dict[str, Any]]:
        start = self._records_date - timedelta(days=self._records_date.weekday())
        result = []
        has_data = False
        weekdays = "월화수목금토일"
        for offset in range(7):
            current = start + timedelta(days=offset)
            day_rows = [row for row in rows if _row_datetime(row).date() == current]
            focus = sum(row.focus_seconds for row in day_rows)
            non_focus = sum(row.non_focus_seconds for row in day_rows)
            breaks = sum(row.break_seconds for row in day_rows)
            study = focus + non_focus
            has_data = has_data or study > 0
            result.append(
                {
                    "label": f"{current.month}/{current.day} {weekdays[offset]}",
                    "study": round(study / 60),
                    "focus": round(focus / study * 100) if study else 0,
                    "pure": round(focus / (study + breaks) * 100) if study + breaks else 0,
                    "away": round(non_focus / study * 100) if study else 0,
                }
            )
        return result if has_data else _demo_weekly(start)

    def _build_monthly(self, rows: List[SessionRow]) -> tuple[List[int], Dict[str, Any]]:
        month_rows = [
            row
            for row in rows
            if (_row_datetime(row).year, _row_datetime(row).month)
            == (self._records_date.year, self._records_date.month)
        ]
        if not month_rows:
            return (
                [0, 1, 2, 3, 2, 0, 1, 1, 2, 4, 3, 2, 1, 0, 2, 3, 4, 4, 3, 2, 1, 0, 1, 3, 4, 2, 1, 0, 1, 2, 2],
                {"study":"46시간 20분","focus":"38시간 12분","ratio":82,"days":19,"longest":"8일"},
            )
        days = [0.0] * 31
        for row in month_rows:
            day_index = _row_datetime(row).day - 1
            days[day_index] += row.focus_seconds
        focus = sum(row.focus_seconds for row in month_rows)
        non_focus = sum(row.non_focus_seconds for row in month_rows)
        study = focus + non_focus
        studied_dates = {_row_datetime(row).date() for row in month_rows if row.focus_seconds + row.non_focus_seconds > 0}
        summary = {
            "study": _duration_text(study),
            "focus": _duration_text(focus),
            "ratio": round(focus / study * 100) if study else 0,
            "days": len(studied_dates),
            "longest": f"{_longest_streak(studied_dates)}일",
        }
        return [0 if seconds <= 0 else min(4, max(1, round(seconds / 7200))) for seconds in days], summary


def _row_datetime(row: SessionRow) -> datetime:
    try:
        return datetime.fromisoformat(row.started_at_wall)
    except ValueError:
        return datetime.now()


def _hourly_from_rows(rows: List[SessionRow]) -> List[Dict[str, Any]]:
    slots = [[[] for _ in range(6)] for _ in range(24)]
    for row in rows:
        started = _row_datetime(row)
        try:
            buckets = json.loads(row.timeline_json or "[]")
        except json.JSONDecodeError:
            buckets = []
        if buckets:
            for index, bucket in enumerate(buckets):
                moment = started + timedelta(minutes=index)
                focus = float(bucket.get("focus", 0))
                non_focus = float(bucket.get("non_focus", 0))
                scored = focus + non_focus
                if scored > 0:
                    slots[moment.hour][moment.minute // 10].append(focus / scored * 100)
        else:
            ratio = row.focus_ratio * 100
            duration_minutes = max(1, round((row.focus_seconds + row.non_focus_seconds) / 60))
            for minute in range(0, duration_minutes, 10):
                moment = started + timedelta(minutes=minute)
                slots[moment.hour][moment.minute // 10].append(ratio)
    result = []
    for hour, values in enumerate(slots):
        averaged = [round(sum(slot) / len(slot)) if slot else 0 for slot in values]
        if any(averaged):
            result.append({"hour": hour, "values": averaged})
    return result


def _parse_time(value: str) -> Optional[int]:
    clean = value.strip().replace(" ", "")
    if not clean or ":" not in clean:
        return None
    try:
        hour, minute = (int(part) for part in clean.split(":", 1))
    except ValueError:
        return None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return hour * 60 + minute


def _parse_duration(value: str) -> int:
    digits = "".join(character for character in value if character.isdigit())
    return int(digits) if digits else 0


def _format_minute(value: Optional[int]) -> str:
    if value is None:
        return ""
    return f"{value // 60:02d}:{value % 60:02d}"


def _task_detail(start: Optional[int], end: Optional[int], duration: int) -> str:
    if start is not None and end is not None:
        return f"{_format_minute(start)} - {_format_minute(end)}"
    if start is not None:
        return f"{_format_minute(start)} 시작"
    if duration:
        return f"예상 {duration}분"
    return "시간 미지정"


def _duration_text(seconds: float) -> str:
    minutes = max(0, round(seconds / 60))
    if minutes < 60:
        return f"{minutes}분"
    return f"{minutes // 60}시간 {minutes % 60}분"


def _longest_streak(studied_dates: set[date]) -> int:
    longest = 0
    current = 0
    previous: Optional[date] = None
    for studied_date in sorted(studied_dates):
        current = current + 1 if previous and studied_date == previous + timedelta(days=1) else 1
        longest = max(longest, current)
        previous = studied_date
    return longest


def _date_label(value: date) -> str:
    return f"{value.year}년 {value.month}월 {value.day}일"


def _demo_planner_tasks() -> List[Dict[str, Any]]:
    return [
        {"taskId": -1, "taskState": 0, "title": "영어 독해 지문 2개", "start": "09:00", "end": "09:45", "duration": "45분", "detail": "09:00 - 09:45", "done": False},
        {"taskId": -2, "taskState": 1, "title": "수학 오답노트 정리", "start": "11:00", "end": "", "duration": "60분", "detail": "11:00 시작", "done": True},
        {"taskId": -3, "taskState": 2, "title": "한국사 4강 복습", "start": "", "end": "", "duration": "30분", "detail": "예상 30분", "done": False},
        {"taskId": -4, "taskState": 0, "title": "과학 개념 문제 20개", "start": "20:00", "end": "21:00", "duration": "60분", "detail": "20:00 - 21:00", "done": False},
    ]


def _demo_daily_summary() -> Dict[str, Any]:
    return {"study": "4시간 32분", "focus": "3시간 42분", "away": "38분", "break": "12분", "unscored": "4분", "ratio": 82, "longest": "54분"}


def _demo_hourly_data() -> List[Dict[str, Any]]:
    return [
        {"hour": 8, "values": [0, 82, 88, 91, 0, 0]},
        {"hour": 10, "values": [72, 76, 84, 89, 81, 0]},
        {"hour": 13, "values": [0, 0, 64, 71, 78, 83]},
        {"hour": 19, "values": [86, 92, 88, 79, 84, 0]},
    ]


def _demo_weekly(start: date) -> List[Dict[str, Any]]:
    study = [190, 245, 150, 280, 225, 330, 175]
    focus = [78, 84, 72, 88, 81, 91, 76]
    pure = [70, 77, 65, 82, 74, 87, 69]
    away = [18, 12, 24, 8, 16, 6, 20]
    weekdays = "월화수목금토일"
    return [
        {"label": f"{(start + timedelta(days=i)).month}/{(start + timedelta(days=i)).day} {weekdays[i]}", "study": study[i], "focus": focus[i], "pure": pure[i], "away": away[i]}
        for i in range(7)
    ]
