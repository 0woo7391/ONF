from __future__ import annotations

import json
import calendar
import sys
import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtMultimedia import QSoundEffect

from onf_v2.app.alert_sounds import ALERT_SOUND_KEYS, ensure_alert_sound_files
from onf_v2.app.session_database import SessionDatabase, SessionRow
from onf_v2.app.settings_store import SettingsStore, UserSettings
from onf_v2.core.metrics import study_seconds


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
        self.database = database or SessionDatabase(_default_database_path())
        self.settings_store = settings_store or SettingsStore()
        self._settings = self.settings_store.load()
        self._records_date = date.today()
        self._planner_date = date.today()
        self._planner_tasks: List[Dict[str, Any]] = []
        self._today_planner_tasks: List[Dict[str, Any]] = []
        self._today_hourly_data: List[Dict[str, Any]] = []
        self._today_study_seconds = 0
        self._today_focus_seconds = 0
        self._today_calendar_date = date.today()
        self._today_study_date = _study_date_for_datetime(datetime.now(), self._settings.study_day_start_hour)
        self._demo_tasks = _demo_planner_tasks()
        self._daily_summary: Dict[str, Any] = {}
        self._daily_app_usage: List[Dict[str, Any]] = []
        self._daily_hourly_data: List[Dict[str, Any]] = []
        self._planner_daily_summary: Dict[str, Any] = {}
        self._planner_hourly_data: List[Dict[str, Any]] = []
        self._weekly_records: List[Dict[str, Any]] = []
        self._monthly_levels: List[int] = []
        self._monthly_summary: Dict[str, Any] = {}
        self._monthly_day_count = 31
        self._monthly_leading_blanks = 0
        self._calendar_events: List[Dict[str, Any]] = []
        self._primary_dday: Dict[str, Any] = {}
        self._planner_uses_sample_data = False
        self._records_use_sample_data = False
        self._study_records = []
        self._saved_rows = []
        self._manual_totals = {}
        self._today_rows = []
        self._learning_hourly_key = None
        self._learning_hourly_data = []
        self._sound_effect = QSoundEffect(self)
        self._sound_paths = ensure_alert_sound_files(self.settings_store.path.parent / "sounds")
        self.refresh()

    @Property("QVariantList", notify=dataChanged)
    def plannerTasks(self) -> List[Dict[str, Any]]:
        return self._planner_tasks

    @Property("QVariantList", notify=dataChanged)
    def todayPlannerTasks(self) -> List[Dict[str, Any]]:
        return self._today_planner_tasks

    @Property("QVariantList", notify=dataChanged)
    def todayHourlyData(self) -> List[Dict[str, Any]]:
        return self._today_hourly_data

    @Slot("QVariantMap", result="QVariantList")
    def learningHourlyData(self, live):
        if not live:
            return self._today_hourly_data
        key = (live.get("revision"), self._today_study_date)
        if key != self._learning_hourly_key:
            values = live["durations"]
            focus, non_focus = values.get("focus", 0), values.get("non_focus", 0)
            row = SessionRow(
                id=-1, started_at_wall=live["started"], ended_at_wall=live["ended"],
                focus_seconds=focus, non_focus_seconds=non_focus,
                break_seconds=values.get("break", 0), unscored_seconds=values.get("unscored", 0),
                absent_pending_seconds=values.get("absent_pending", 0),
                focus_ratio=focus / (focus + non_focus) if focus + non_focus else 0,
                coverage_ratio=0, longest_focus_seconds=0, event_count=0, session_dir="",
                session_mode="free", pomodoro_cycles_completed=0, pomodoro_cycles_planned=0,
                task_id=None, timeline_json=live["timeline"], task_attribution_version=1,
            )
            self._learning_hourly_data = _hourly_from_rows(
                self._today_rows + [row], self._settings.study_day_start_hour, self._today_study_date
            )
            self._learning_hourly_key = key
        return self._learning_hourly_data

    @Property(int, notify=dataChanged)
    def todayStudySeconds(self) -> int:
        return self._today_study_seconds

    @Property(int, notify=dataChanged)
    def todayFocusSeconds(self) -> int:
        return self._today_focus_seconds

    @Property(str, notify=dataChanged)
    def todayStudyDateIso(self) -> str:
        return self._today_study_date.isoformat()

    @Property(str, notify=dataChanged)
    def recordsDateIso(self) -> str:
        return self._records_date.isoformat()

    @Property("QVariantList", notify=dataChanged)
    def recordTasks(self):
        return self._load_planner_tasks(self._records_date)

    @Property("QVariantList", notify=dataChanged)
    def studyRecords(self):
        return [
            {**asdict(row), "duration": _app_usage_text(row.study_seconds),
             "hours": int(row.study_seconds) // 3600, "minutes": int(row.study_seconds) % 3600 // 60,
             "sourceLabel": {"tracked": "측정 중 연결", "allocated": "측정 후 연결", "manual": "직접 기록"}[row.source],
             "focusLabel": "미측정" if row.focus_seconds is None else _app_usage_text(row.focus_seconds)}
            for row in self._study_records if row.study_date == self._records_date.isoformat()
        ]

    @Property("QVariantList", notify=dataChanged)
    def recordSessions(self):
        start, end = self._study_day_bounds(self._records_date)
        used = {}
        for entry in self._study_records:
            if entry.session_id is not None:
                used[entry.session_id] = used.get(entry.session_id, 0) + entry.study_seconds
        return [
            {"id": row.id,
             "label": row.started_at_wall[11:16] + " · " + _duration_text(study_seconds(_session_state_totals(row))),
             "remaining": 0 if row.task_attribution_version == 0 and row.task_id is not None
             else max(0, study_seconds(_session_state_totals(row)) - used.get(row.id, 0))}
            for row in self._saved_rows if _session_overlaps(row, start, end)
        ]

    @Property("QVariantMap", notify=dataChanged)
    def dailySummary(self) -> Dict[str, Any]:
        return self._daily_summary

    @Property("QVariantList", notify=dataChanged)
    def dailyAppUsage(self) -> List[Dict[str, Any]]:
        return self._daily_app_usage

    @Property("QVariantList", notify=dataChanged)
    def dailyHourlyData(self) -> List[Dict[str, Any]]:
        return self._daily_hourly_data

    @Property("QVariantMap", notify=dataChanged)
    def plannerDailySummary(self) -> Dict[str, Any]:
        return self._planner_daily_summary

    @Property("QVariantList", notify=dataChanged)
    def plannerHourlyData(self) -> List[Dict[str, Any]]:
        return self._planner_hourly_data

    @Property("QVariantList", notify=dataChanged)
    def weeklyRecords(self) -> List[Dict[str, Any]]:
        return self._weekly_records

    @Property("QVariantList", notify=dataChanged)
    def monthlyLevels(self) -> List[int]:
        return self._monthly_levels

    @Property("QVariantMap", notify=dataChanged)
    def monthlySummary(self) -> Dict[str, Any]:
        return self._monthly_summary

    @Property(int, notify=dataChanged)
    def monthlyDayCount(self) -> int:
        return self._monthly_day_count

    @Property(int, notify=dataChanged)
    def monthlyLeadingBlanks(self) -> int:
        return self._monthly_leading_blanks

    @Property(bool, notify=dataChanged)
    def plannerUsesSampleData(self) -> bool:
        return self._planner_uses_sample_data

    @Property(bool, notify=dataChanged)
    def recordsUseSampleData(self) -> bool:
        return self._records_use_sample_data

    @Property("QVariantList", notify=dataChanged)
    def calendarEvents(self) -> List[Dict[str, Any]]:
        return self._calendar_events

    @Property("QVariantMap", notify=dataChanged)
    def primaryDday(self) -> Dict[str, Any]:
        return self._primary_dday

    @Property(bool, notify=dataChanged)
    def hasPrimaryDday(self) -> bool:
        return bool(self._primary_dday.get("title"))

    @Property(str, notify=dataChanged)
    def primaryDdayLabel(self) -> str:
        return str(self._primary_dday.get("dday", ""))

    @Property(str, notify=dataChanged)
    def primaryDdayTitle(self) -> str:
        return str(self._primary_dday.get("title", ""))

    @Property(str, notify=dataChanged)
    def primaryDdayDate(self) -> str:
        return str(self._primary_dday.get("date", ""))

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
    def plannerDateIso(self) -> str:
        return self._planner_date.isoformat()

    @Property(str, notify=dataChanged)
    def weekLabel(self) -> str:
        start = self._records_date - timedelta(
            days=(self._records_date.weekday() + 1) % 7
        )
        end = start + timedelta(days=6)
        return f"{start.year}년 {start.month}월 {start.day}일 ~ {end.month}월 {end.day}일"

    @Property(str, notify=dataChanged)
    def monthLabel(self) -> str:
        return f"{self._records_date.year}년 {self._records_date.month}월"

    @Slot()
    def refresh(self) -> None:
        self._today_calendar_date = date.today()
        self._today_study_date = _study_date_for_datetime(datetime.now(), self._settings.study_day_start_hour)
        self.database.ensure_fixed_schedule_occurrences(self._planner_date.isoformat())
        self.database.ensure_fixed_schedule_occurrences(date.today().isoformat())
        rows = self.database.list_sessions(None)
        self._saved_rows = rows
        self._study_records = self.database.list_study_records()
        self._manual_totals = {}
        for entry in self._study_records:
            if entry.source == "manual":
                self._manual_totals[entry.study_date] = self._manual_totals.get(entry.study_date, 0) + entry.study_seconds
        real_planner_tasks = self.database.list_planner_tasks()
        calendar_rows = self.database.list_calendar_events()
        fresh_database = not rows and not real_planner_tasks and not calendar_rows and not self._study_records
        self._planner_uses_sample_data = fresh_database
        self._records_use_sample_data = fresh_database
        self._planner_tasks = self._load_planner_tasks(self._planner_date)
        self._today_planner_tasks = self._load_planner_tasks(date.today())
        _, self._today_hourly_data = self._build_daily(rows, self._today_study_date, self._records_use_sample_data)
        today_start, today_end = self._study_day_bounds(self._today_study_date)
        self._today_rows = [row for row in rows if _session_overlaps(row, today_start, today_end)]
        self._learning_hourly_key = None
        today_totals = _state_totals_for_interval(rows, today_start, today_end)
        self._today_study_seconds = int(study_seconds(today_totals) + self._manual_totals.get(self._today_study_date.isoformat(), 0))
        self._today_focus_seconds = int(today_totals.get("focus", 0))
        self._calendar_events = [_calendar_event_dict(row) for row in calendar_rows]
        self._primary_dday = next(
            (event for event in self._calendar_events if event["isPrimary"]),
            {},
        )
        self._daily_summary, self._daily_hourly_data = self._build_daily(
            rows, self._records_date, self._records_use_sample_data
        )
        daily_rows = [
            row
            for row in rows
            if _study_date_for_datetime(
                _row_datetime(row), self._settings.study_day_start_hour
            )
            == self._records_date
        ]
        self._daily_app_usage = [
            {
                "processName": row.process_name,
                "duration": _app_usage_text(row.duration_seconds),
                "seconds": round(row.duration_seconds),
            }
            for row in self.database.list_app_usage([row.id for row in daily_rows])
        ]
        self._planner_daily_summary, self._planner_hourly_data = self._build_daily(
            rows, self._planner_date, self._records_use_sample_data
        )
        self._weekly_records = self._build_weekly(rows)
        (
            self._monthly_levels,
            self._monthly_summary,
            self._monthly_day_count,
            self._monthly_leading_blanks,
        ) = self._build_monthly(rows)
        self.dataChanged.emit()

    @Slot()
    def refreshToday(self) -> None:
        study_date = _study_date_for_datetime(datetime.now(), self._settings.study_day_start_hour)
        if study_date != self._today_study_date or date.today() != self._today_calendar_date:
            self.refresh()

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

    @Slot(str)
    def selectRecordsDate(self, value: str) -> None:
        try:
            self._records_date = date.fromisoformat(value)
        except ValueError:
            return
        self.refresh()

    @Slot(int, int, int, str, int, int, result="QVariantMap")
    def saveStudyRecord(self, record_id: int, session_id: int, task_id: int, title: str, hours: int, minutes: int):
        try:
            if not 0 <= hours <= 24 or not 0 <= minutes <= 59:
                raise ValueError("시간과 분을 확인하세요.")
            saved_id = self.database.save_study_record(
                self._records_date.isoformat(), title, hours * 3600 + minutes * 60,
                task_id if task_id > 0 else None,
                session_id if session_id > 0 else None,
                record_id if record_id > 0 else None,
            )
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}
        except (OSError, sqlite3.Error):
            return {"ok": False, "message": "기록을 저장하지 못했습니다. 다시 시도하세요."}
        self.refresh()
        return {"ok": True, "id": saved_id}

    @Slot(int, result="QVariantMap")
    def deleteStudyRecord(self, record_id: int):
        try:
            self.database.delete_study_record(record_id)
        except ValueError as exc:
            return {"ok": False, "message": str(exc)}
        except (OSError, sqlite3.Error):
            return {"ok": False, "message": "기록을 삭제하지 못했습니다. 다시 시도하세요."}
        self.refresh()
        return {"ok": True}

    @Slot(int)
    def shiftPlannerDate(self, direction: int) -> None:
        self._planner_date += timedelta(days=-1 if direction < 0 else 1)
        self.refresh()

    @Slot(str)
    def selectPlannerDate(self, value: str) -> None:
        try:
            self._planner_date = date.fromisoformat(value)
        except ValueError:
            return
        self.refresh()

    @Slot(str, str, result=int)
    def addCalendarEvent(self, title: str, event_date: str) -> int:
        try:
            date.fromisoformat(event_date)
        except ValueError:
            return -1
        if not title.strip():
            return -1
        event_id = self.database.add_calendar_event(title, event_date)
        self.refresh()
        return event_id

    @Slot(int)
    def setPrimaryCalendarEvent(self, event_id: int) -> None:
        self.database.set_primary_calendar_event(event_id if event_id > 0 else None)
        self.refresh()

    @Slot(int)
    def deleteCalendarEvent(self, event_id: int) -> None:
        self.database.delete_calendar_event(event_id)
        self.refresh()

    @Slot(str, str, str, str, str, result=bool)
    def addPlannerTask(
        self,
        title: str,
        start: str,
        end: str,
        duration: str,
        generated_field: str = "",
    ) -> bool:
        clean_title = title.strip()
        if not clean_title or any(value.strip() and _parse_time(value) is None for value in (start, end)):
            return False
        start_minute, end_minute, duration_minutes = _resolve_planner_edit(
            _parse_time(start),
            _parse_time(end),
            _parse_duration(duration),
            "",
            generated_field,
        )
        self.database.add_planner_task(
            title=clean_title,
            subject_id=None,
            planned_date=self._planner_date.isoformat(),
            deadline_date=None,
            estimated_minutes=duration_minutes,
            task_type="study",
            planned_start_minute=start_minute,
            planned_end_minute=end_minute,
            generated_field=generated_field,
        )
        self.refresh()
        return True

    @Slot(int)
    def cyclePlannerTask(self, task_id: int) -> None:
        if task_id < 0:
            for task in self._demo_tasks:
                if task["taskId"] == task_id:
                    task["taskState"] = (task["taskState"] + 1) % 3
                    task["done"] = task["taskState"] == 1
                    self.refresh()
                    break
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
        if task_id < 0:
            self._demo_tasks = [task for task in self._demo_tasks if task["taskId"] != task_id]
            self.refresh()
            return
        self.database.delete_planner_task(task_id)
        self.refresh()

    @Slot(int)
    def togglePlannerTaskFixed(self, task_id: int) -> None:
        if task_id < 0:
            for task in self._demo_tasks:
                if task["taskId"] == task_id:
                    task["pinned"] = not task.get("pinned", False)
                    self.refresh()
                    break
            return
        self.database.toggle_planner_task_fixed(task_id)
        self.refresh()

    @Slot(int, str, str, str, str, str, str, result=bool)
    def updatePlannerTask(
        self,
        task_id: int,
        title: str,
        start: str,
        end: str,
        duration: str,
        changed_field: str,
        generated_field: str = "",
    ) -> bool:
        if not title.strip() or any(value.strip() and _parse_time(value) is None for value in (start, end)):
            return False
        start_minute, end_minute, duration_minutes = _resolve_planner_edit(
            _parse_time(start),
            _parse_time(end),
            _parse_duration(duration),
            changed_field,
            generated_field,
        )
        current = next((row for row in self._planner_tasks if row["taskId"] == task_id), None)
        values = {
            "title": title.strip(), "start": _format_minute(start_minute),
            "end": _format_minute(end_minute),
            "duration": f"{duration_minutes}분" if duration_minutes > 0 else "",
            "generatedField": generated_field,
        }
        if current is not None and all(current.get(key, "") == value for key, value in values.items()):
            return True
        if task_id < 0 or not title.strip():
            if task_id < 0 and title.strip():
                for task in self._demo_tasks:
                    if task["taskId"] == task_id:
                        task.update(
                            title=title.strip(),
                            start=_format_minute(start_minute),
                            end=_format_minute(end_minute),
                            duration=(
                                f"{duration_minutes}분"
                                if duration_minutes > 0
                                else ""
                            ),
                            detail=_task_detail(
                                start_minute,
                                end_minute,
                                duration_minutes,
                            ),
                        )
                        self.refresh()
                        break
            return task_id < 0 and bool(title.strip())
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
            generated_field,
        )
        self.database.update_fixed_schedule_from_task(task_id)
        self.refresh()
        return True

    @Slot("QVariantMap")
    def saveSettings(self, values: Dict[str, Any]) -> None:
        merged = asdict(self._settings)
        merged.update(dict(values))
        self._settings = UserSettings.from_dict(merged)
        self.settings_store.save(self._settings)
        self.settingsChanged.emit()
        self.refresh()

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

    def _load_planner_tasks(self, planned_date: date) -> List[Dict[str, Any]]:
        rows = [row for row in self.database.list_planner_tasks() if row.planned_date == planned_date.isoformat()]
        if not rows:
            if self._planner_uses_sample_data:
                return [dict(task) for task in self._demo_tasks]
            return []
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
                "pinned": row.fixed_schedule_id is not None,
                "generatedField": row.generated_field or "",
                "actualStudy": _duration_text(row.actual_study_seconds),
                "actualFocus": (
                    _duration_text(row.actual_focus_seconds) if row.actual_unmeasured_seconds <= 0
                    else "미측정" if row.actual_study_seconds <= row.actual_unmeasured_seconds
                    else _duration_text(row.actual_focus_seconds) + " · 일부 미측정"
                ),
            }
            for row in rows
        ]

    def _build_daily(
        self,
        rows: List[SessionRow],
        selected_date: date,
        use_sample_data: bool,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        interval_start, interval_end = self._study_day_bounds(selected_date)
        selected = [
            row
            for row in rows
            if _session_overlaps(row, interval_start, interval_end)
        ]
        manual = self._manual_totals.get(selected_date.isoformat(), 0)
        if not selected:
            if use_sample_data and manual <= 0:
                return _demo_daily_summary(), _demo_hourly_data()
            return {**_empty_daily_summary(), "study": _duration_text(manual), "manual": _duration_text(manual), "hasMeasurement": False}, []
        totals = _state_totals_for_interval(selected, interval_start, interval_end)
        focus = totals["focus"]
        non_focus = totals["non_focus"]
        breaks = totals["break"]
        unscored = totals["unscored"]
        scored = focus + non_focus
        sessions_started_today = [
            row
            for row in selected
            if _study_date_for_datetime(
                _session_bounds(row)[0], self._settings.study_day_start_hour
            )
            == selected_date
        ]
        summary = {
            "study": _duration_text(study_seconds(totals) + manual),
            "manual": _duration_text(manual),
            "hasMeasurement": scored > 0,
            "focus": _duration_text(focus),
            "away": _duration_text(non_focus),
            "break": _duration_text(breaks),
            "unscored": _duration_text(unscored),
            "ratio": round(focus / scored * 100) if scored else 0,
            "longest": _duration_text(max((row.longest_focus_seconds for row in sessions_started_today), default=0)),
        }
        return summary, _hourly_from_rows(
            selected, self._settings.study_day_start_hour, selected_date
        )

    def _build_weekly(self, rows: List[SessionRow]) -> List[Dict[str, Any]]:
        start = self._records_date - timedelta(
            days=(self._records_date.weekday() + 1) % 7
        )
        result = []
        has_data = False
        weekdays = "일월화수목금토"
        for offset in range(7):
            current = start + timedelta(days=offset)
            interval_start, interval_end = self._study_day_bounds(current)
            totals = _state_totals_for_interval(rows, interval_start, interval_end)
            focus = totals["focus"]
            non_focus = totals["non_focus"]
            breaks = totals["break"]
            scored = focus + non_focus
            study = study_seconds(totals) + self._manual_totals.get(current.isoformat(), 0)
            has_data = has_data or study > 0
            result.append(
                {
                    "label": f"{current.month}/{current.day} {weekdays[offset]}",
                    "study": round(study / 60),
                    "focusSeconds": focus,
                    "scoredSeconds": scored,
                    "hasMeasurement": scored > 0,
                    "focus": round(focus / scored * 100) if scored else 0,
                    "pure": round(focus / (scored + breaks) * 100) if scored + breaks else 0,
                    "away": round(non_focus / scored * 100) if scored else 0,
                }
            )
        return result if has_data else (
            _demo_weekly(start, self._records_date)
            if self._records_use_sample_data
            else result
        )

    def _build_monthly(self, rows: List[SessionRow]) -> tuple[List[int], Dict[str, Any], int, int]:
        day_count = calendar.monthrange(self._records_date.year, self._records_date.month)[1]
        leading_blanks = (calendar.monthrange(self._records_date.year, self._records_date.month)[0] + 1) % 7
        month_start = date(self._records_date.year, self._records_date.month, 1)
        next_month = (
            date(self._records_date.year + 1, 1, 1)
            if self._records_date.month == 12
            else date(self._records_date.year, self._records_date.month + 1, 1)
        )
        interval_start, _ = self._study_day_bounds(month_start)
        _, interval_end = self._study_day_bounds(next_month - timedelta(days=1))
        month_rows = [
            row
            for row in rows
            if _session_overlaps(row, interval_start, interval_end)
        ]
        manual_in_month = any(value > 0 and key[:7] == month_start.isoformat()[:7] for key, value in self._manual_totals.items())
        if not month_rows and not manual_in_month:
            if not self._records_use_sample_data:
                return (
                    [0] * day_count,
                    {"study": "0분", "focus": "0분", "ratio": 0, "days": 0, "longest": "0일", "hasMeasurement": False, "weeks": []},
                    day_count,
                    leading_blanks,
                )
            demo_levels = [0, 1, 2, 3, 2, 0, 1, 1, 2, 4, 3, 2, 1, 0, 2, 3, 4, 4, 3, 2, 1, 0, 1, 3, 4, 2, 1, 0, 1, 2, 2][:day_count]
            return (
                demo_levels,
                {"study":"46시간 20분","focus":"38시간 12분","ratio":82,"days":19,"longest":"8일"},
                day_count,
                leading_blanks,
            )
        days = [0.0] * day_count
        study_dates = set()
        focus = 0.0
        non_focus = 0.0
        study = 0.0
        week_focus = [0.0] * ((leading_blanks + day_count + 6) // 7)
        week_scored = [0.0] * len(week_focus)
        for day_index in range(day_count):
            study_date = month_start + timedelta(days=day_index)
            day_start, day_end = self._study_day_bounds(study_date)
            totals = _state_totals_for_interval(month_rows, day_start, day_end)
            day_study = study_seconds(totals) + self._manual_totals.get(study_date.isoformat(), 0)
            days[day_index] = day_study
            focus += totals["focus"]
            non_focus += totals["non_focus"]
            week_index = (leading_blanks + day_index) // 7
            week_focus[week_index] += totals["focus"]
            week_scored[week_index] += totals["focus"] + totals["non_focus"]
            study += day_study
            if day_study > 0:
                study_dates.add(study_date)
        scored = focus + non_focus
        summary = {
            "study": _duration_text(study),
            "focus": _duration_text(focus),
            "ratio": round(focus / scored * 100) if scored else 0,
            "days": len(study_dates),
            "longest": f"{_longest_streak(study_dates)}일",
            "hasMeasurement": scored > 0,
            "weeks": [
                {"label": f"{index + 1}주", "value": seconds / max(1.0, max(week_focus)),
                 "time": _duration_text(seconds) if week_scored[index] > 0 else "미측정"}
                for index, seconds in enumerate(week_focus)
            ],
        }
        return (
            [0 if seconds <= 0 else min(4, max(1, round(seconds / 7200))) for seconds in days],
            summary,
            day_count,
            leading_blanks,
        )

    def _study_day_bounds(self, study_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(study_date, datetime.min.time()) + timedelta(
            hours=self._settings.study_day_start_hour
        )
        return start, start + timedelta(days=1)


def _row_datetime(row: SessionRow) -> datetime:
    try:
        return datetime.fromisoformat(row.started_at_wall)
    except ValueError:
        return datetime.now()


def _default_database_path() -> Path:
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
        if root.name.casefold() == "dist":
            root = root.parent
    else:
        root = Path(__file__).resolve().parents[2]
    return root / "sessions" / "onf.sqlite3"


def _app_usage_text(seconds: float) -> str:
    total = max(0, round(seconds))
    if total < 60:
        return f"{total}초"
    return _duration_text(total)


def _calendar_event_dict(row) -> Dict[str, Any]:
    try:
        target = date.fromisoformat(row.event_date)
    except ValueError:
        target = date.today()
    remaining = (target - date.today()).days
    if remaining > 0:
        dday = f"D-{remaining}"
        remaining_label = f"{row.title}까지 {remaining}일"
    elif remaining == 0:
        dday = "D-day"
        remaining_label = f"{row.title} 당일"
    else:
        dday = f"D+{-remaining}"
        remaining_label = f"{row.title}이 지난 지 {-remaining}일"
    return {
        "eventId": row.id,
        "title": row.title,
        "date": target.isoformat(),
        "dateLabel": f"{target.year}년 {target.month}월 {target.day}일",
        "dday": dday,
        "remainingLabel": remaining_label,
        "isPrimary": row.is_primary,
    }


def _hourly_from_rows(
    rows: List[SessionRow],
    study_start_hour: int = 0,
    study_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    slots = [[[] for _ in range(6)] for _ in range(24)]
    interval_start = (
        datetime.combine(study_date, datetime.min.time())
        + timedelta(hours=study_start_hour)
        if study_date is not None
        else None
    )
    for row in rows:
        started, ended = _session_bounds(row)
        try:
            buckets = json.loads(row.timeline_json or "[]")
        except json.JSONDecodeError:
            buckets = []
        if buckets:
            for index, bucket in enumerate(buckets):
                moment = started + timedelta(minutes=index)
                if moment >= ended:
                    break
                if interval_start is not None:
                    if not interval_start <= moment < interval_start + timedelta(days=1):
                        continue
                    offset = int((moment - interval_start).total_seconds())
                    hour_index = offset // 3600
                    minute_index = (offset % 3600) // 60
                else:
                    hour_index = moment.hour
                    minute_index = moment.minute
                focus = float(bucket.get("focus", 0))
                non_focus = float(bucket.get("non_focus", 0))
                scored = focus + non_focus
                if scored > 0:
                    slots[hour_index][minute_index // 10].append(focus / scored * 100)
        else:
            if row.focus_seconds + row.non_focus_seconds <= 0:
                continue
            ratio = row.focus_ratio * 100
            duration_minutes = max(1, round((row.focus_seconds + row.non_focus_seconds) / 60))
            for minute in range(0, duration_minutes, 10):
                moment = started + timedelta(minutes=minute)
                if moment >= ended:
                    break
                if interval_start is not None:
                    if not interval_start <= moment < interval_start + timedelta(days=1):
                        continue
                    offset = int((moment - interval_start).total_seconds())
                    hour_index = offset // 3600
                    minute_index = (offset % 3600) // 60
                else:
                    hour_index = moment.hour
                    minute_index = moment.minute
                slots[hour_index][minute_index // 10].append(ratio)
    result = []
    for hour, values in enumerate(slots):
        averaged = [round(sum(slot) / len(slot)) if slot else 0 for slot in values]
        present = [bool(slot) for slot in values]
        if any(present):
            result.append(
                {
                    "hour": (study_start_hour + hour) % 24
                    if study_date is not None
                    else hour,
                    "values": averaged,
                    "present": present,
                }
            )
    return result


def _study_date_for_datetime(value: datetime, start_hour: int) -> date:
    return (value - timedelta(hours=start_hour)).date()


def _session_bounds(row: SessionRow) -> tuple[datetime, datetime]:
    started = _row_datetime(row)
    total = sum(
        max(0.0, float(value))
        for value in (
            row.focus_seconds,
            row.non_focus_seconds,
            row.break_seconds,
            row.unscored_seconds,
            row.absent_pending_seconds,
        )
    )
    try:
        ended = datetime.fromisoformat(row.ended_at_wall)
    except (AttributeError, TypeError, ValueError):
        ended = started
    if ended <= started:
        ended = started + timedelta(seconds=max(1.0, total))
    return started, ended


def _session_state_totals(row: SessionRow) -> Dict[str, float]:
    return {
        "focus": max(0.0, float(row.focus_seconds)),
        "non_focus": max(0.0, float(row.non_focus_seconds)),
        "break": max(0.0, float(row.break_seconds)),
        "unscored": max(
            0.0,
            float(row.unscored_seconds) + float(row.absent_pending_seconds),
        ),
    }


def _session_overlaps(
    row: SessionRow, interval_start: datetime, interval_end: datetime
) -> bool:
    started, ended = _session_bounds(row)
    return started < interval_end and ended > interval_start


def _state_totals_for_interval(
    rows: List[SessionRow], interval_start: datetime, interval_end: datetime
) -> Dict[str, float]:
    totals = {"focus": 0.0, "non_focus": 0.0, "break": 0.0, "unscored": 0.0}
    for row in rows:
        started, ended = _session_bounds(row)
        overlap = max(
            0.0,
            (min(ended, interval_end) - max(started, interval_start)).total_seconds(),
        )
        if overlap <= 0:
            continue
        if started < interval_start or ended > interval_end:
            try:
                buckets = json.loads(row.timeline_json or "[]")
            except json.JSONDecodeError:
                buckets = []
            if buckets:
                for index, bucket in enumerate(buckets):
                    bucket_start = started + timedelta(minutes=index)
                    duration = sum(max(0.0, float(value)) for value in bucket.values())
                    bucket_end = min(ended, bucket_start + timedelta(seconds=duration))
                    included = max(0.0, (min(bucket_end, interval_end) - max(bucket_start, interval_start)).total_seconds())
                    if duration <= 0 or included <= 0:
                        continue
                    share = included / duration
                    for state in totals:
                        value = float(bucket.get(state, 0))
                        if state == "unscored":
                            value += float(bucket.get("absent_pending", 0))
                        totals[state] += max(0.0, value) * share
                continue
        share = overlap / max(1.0, (ended - started).total_seconds())
        for state, seconds in _session_state_totals(row).items():
            totals[state] += seconds * share
    return totals


def _parse_time(value: str) -> Optional[int]:
    clean = value.strip().replace(" ", "")
    if not clean:
        return None
    if ":" not in clean:
        if not clean.isdigit() or len(clean) > 4:
            return None
        if len(clean) <= 2:
            hour, minute = int(clean), 0
        else:
            hour, minute = int(clean[:-2]), int(clean[-2:])
        return hour * 60 + minute if 0 <= hour <= 23 and 0 <= minute <= 59 else None
    try:
        hour_text, minute_text = clean.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text) if minute_text else 0
    except ValueError:
        return None
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return hour * 60 + minute


def _parse_duration(value: str) -> int:
    digits = "".join(character for character in value if character.isdigit())
    return int(digits) if digits else 0


def _resolve_planner_times(
    start: Optional[int],
    end: Optional[int],
    duration: int,
) -> tuple[Optional[int], Optional[int], int]:
    present = sum((start is not None, end is not None, duration > 0))
    if present != 2:
        return start, end, duration
    if end is None and start is not None and duration > 0:
        end = (start + duration) % (24 * 60)
    elif start is None and end is not None and duration > 0:
        start = (end - duration) % (24 * 60)
    elif duration <= 0 and start is not None and end is not None:
        duration = (end - start) % (24 * 60) or 24 * 60
    return start, end, duration


def _resolve_planner_edit(
    start: Optional[int],
    end: Optional[int],
    duration: int,
    changed_field: str,
    generated_field: str = "",
) -> tuple[Optional[int], Optional[int], int]:
    if generated_field == "end" and start is not None and duration > 0:
        end = (start + duration) % (24 * 60)
    elif generated_field == "start" and end is not None and duration > 0:
        start = (end - duration) % (24 * 60)
    elif generated_field == "duration" and start is not None and end is not None:
        duration = (end - start) % (24 * 60) or 24 * 60
    elif changed_field == "start":
        if start is not None and duration > 0:
            end = (start + duration) % (24 * 60)
        elif start is not None and end is not None:
            duration = (end - start) % (24 * 60) or 24 * 60
    elif changed_field == "end":
        if start is not None and end is not None:
            duration = (end - start) % (24 * 60) or 24 * 60
        elif end is not None and duration > 0:
            start = (end - duration) % (24 * 60)
    elif changed_field == "duration":
        if start is not None and duration > 0:
            end = (start + duration) % (24 * 60)
        elif end is not None and duration > 0:
            start = (end - duration) % (24 * 60)
    return _resolve_planner_times(start, end, duration)


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
        {"taskId": -1, "taskState": 0, "title": "영어 독해 지문 2개", "start": "09:00", "end": "09:40", "duration": "40분", "detail": "09:00 - 09:40", "done": False, "pinned": False, "generatedField": "end", "actualStudy": "0분", "actualFocus": "0분"},
        {"taskId": -2, "taskState": 1, "title": "수학 오답노트 정리", "start": "11:00", "end": "12:00", "duration": "60분", "detail": "11:00 - 12:00", "done": True, "pinned": False, "generatedField": "end", "actualStudy": "0분", "actualFocus": "0분"},
        {"taskId": -3, "taskState": 2, "title": "한국사 4강 복습", "start": "14:20", "end": "15:00", "duration": "40분", "detail": "14:20 - 15:00", "done": False, "pinned": False, "generatedField": "end", "actualStudy": "0분", "actualFocus": "0분"},
        {"taskId": -4, "taskState": 0, "title": "과학 개념 문제 20개", "start": "20:00", "end": "21:00", "duration": "60분", "detail": "20:00 - 21:00", "done": False, "pinned": False, "generatedField": "end", "actualStudy": "0분", "actualFocus": "0분"},
    ]


def _demo_daily_summary() -> Dict[str, Any]:
    return {"study": "1시간 40분", "focus": "1시간 22분", "away": "18분", "break": "0분", "unscored": "0분", "ratio": 82, "longest": "40분"}


def _empty_daily_summary() -> Dict[str, Any]:
    return {"study": "0분", "focus": "0분", "away": "0분", "break": "0분", "unscored": "0분", "ratio": 0, "longest": "0분"}


def _demo_hourly_data() -> List[Dict[str, Any]]:
    return [
        {"hour": 9, "values": [84, 91, 78, 0, 0, 0]},
        {"hour": 11, "values": [82, 85, 88, 86, 0, 0]},
        {"hour": 14, "values": [0, 0, 72, 76, 78, 0]},
    ]


def _demo_weekly(start: date, selected_date: date) -> List[Dict[str, Any]]:
    study = [180, 210, 150, 240, 195, 260, 100]
    focus = [79, 84, 76, 87, 81, 89, 82]
    pure = [73, 79, 70, 82, 76, 84, 82]
    away = [21, 16, 24, 13, 19, 11, 18]
    selected_index = max(0, min(6, (selected_date - start).days))
    study[selected_index] = 100
    focus[selected_index] = 82
    pure[selected_index] = 82
    away[selected_index] = 18
    weekdays = "일월화수목금토"
    return [
        {"label": f"{(start + timedelta(days=i)).month}/{(start + timedelta(days=i)).day} {weekdays[i]}", "study": study[i], "focus": focus[i], "pure": pure[i], "away": away[i], "focusSeconds": study[i] * 60 * focus[i] / 100, "scoredSeconds": study[i] * 60}
        for i in range(7)
    ]
