import tempfile
import unittest
import os
import calendar
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from onf_v2.app.session_database import SessionDatabase
from onf_v2.app.settings_store import SettingsStore
from onf_v2.core.models import SessionSummary
from onf_v2.ui_qml.app_bridge import AppBridge, _parse_time, _resolve_planner_times


class QmlAppBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_planner_records_and_settings_use_existing_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            settings_store = SettingsStore(root / "settings.json")
            bridge = AppBridge(database, settings_store)

            self.assertGreater(len(bridge.plannerTasks), 0)
            self.assertEqual(len(bridge.weeklyRecords), 7)
            expected_days = calendar.monthrange(datetime.now().year, datetime.now().month)[1]
            self.assertEqual(len(bridge.monthlyLevels), expected_days)

            self.assertTrue(bridge.addPlannerTask("물리 문제", "14:00", "15:00", "60분"))
            tasks = database.list_planner_tasks()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].planned_start_minute, 14 * 60)
            self.assertEqual(tasks[0].planned_end_minute, 15 * 60)
            self.assertEqual(bridge.todayPlannerTasks[0]["title"], "물리 문제")

            bridge.shiftPlannerDate(1)
            self.assertNotEqual(bridge.plannerDayLabel, bridge.dayLabel)
            self.assertEqual(bridge.todayPlannerTasks[0]["title"], "물리 문제")

            bridge.cyclePlannerTask(tasks[0].id)
            self.assertEqual(database.list_planner_tasks()[0].status, "completed")

            now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
            database.add_session(
                SessionSummary(
                    started_at_wall=now.isoformat(sep=" "),
                    ended_at_wall=now.replace(hour=11).isoformat(sep=" "),
                    focus_seconds=2700,
                    non_focus_seconds=900,
                    break_seconds=300,
                    unscored_seconds=0,
                    absent_pending_seconds=0,
                    focus_ratio=0.75,
                    coverage_ratio=1.0,
                    longest_focus_seconds=1200,
                    events=[],
                ),
                root / "session",
                timeline_buckets=[{"focus": 45, "non_focus": 15}] * 60,
            )
            bridge.refresh()
            self.assertEqual(bridge.dailySummary["ratio"], 75)
            self.assertEqual(bridge.dailySummary["study"], "1시간 0분")
            self.assertEqual(bridge.dailyHourlyData[0]["hour"], 10)

            bridge.saveSettings({"alert_volume": 37, "work_mode": "screen_writing"})
            saved = settings_store.load()
            self.assertEqual(saved.alert_volume, 37)
            self.assertEqual(saved.work_mode, "screen_writing")

    def test_daily_records_show_foreground_app_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            today = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
            database.add_session(
                SessionSummary(
                    started_at_wall=today.isoformat(sep=" "),
                    ended_at_wall=today.replace(hour=11).isoformat(sep=" "),
                    focus_seconds=1800,
                    non_focus_seconds=0,
                    break_seconds=0,
                    unscored_seconds=0,
                    absent_pending_seconds=0,
                    focus_ratio=1.0,
                    coverage_ratio=1.0,
                    longest_focus_seconds=1800,
                    events=[],
                    app_usage_seconds={"Code.exe": 900, "chrome.exe": 300},
                ),
                root / "session",
            )
            bridge = AppBridge(database, SettingsStore(root / "settings.json"))

            self.assertEqual(
                bridge.dailyAppUsage,
                [
                    {"processName": "Code.exe", "duration": "15분", "seconds": 900},
                    {"processName": "chrome.exe", "duration": "5분", "seconds": 300},
                ],
            )

    def test_planner_rows_show_saved_task_study_and_focus_totals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            settings = SettingsStore(root / "settings.json")
            bridge = AppBridge(database, settings)
            self.assertTrue(bridge.addPlannerTask("영어 복습", "", "", ""))
            task = database.list_planner_tasks()[0]
            now = datetime.now().replace(second=0, microsecond=0)

            for index, (focus, non_focus, breaks, task_id) in enumerate(
                (
                    (1200, 600, 300, task.id),
                    (1200, 1200, 0, task.id),
                    (9000, 9000, 0, None),
                )
            ):
                started = now + timedelta(hours=index)
                summary = SessionSummary(
                    started_at_wall=started.isoformat(sep=" "),
                    ended_at_wall=(started + timedelta(minutes=30)).isoformat(sep=" "),
                    focus_seconds=focus,
                    non_focus_seconds=non_focus,
                    break_seconds=breaks,
                    unscored_seconds=0,
                    absent_pending_seconds=0,
                    focus_ratio=focus / max(1, focus + non_focus),
                    coverage_ratio=1.0,
                    longest_focus_seconds=focus,
                    events=[],
                )
                database.add_session(summary, root / f"session-{index}", task_id=task_id)

            bridge.refresh()
            planner_row = next(row for row in bridge.plannerTasks if row["taskId"] == task.id)
            self.assertEqual(planner_row["duration"], "")
            self.assertEqual(planner_row["actualStudy"], "1시간 10분")
            self.assertEqual(planner_row["actualFocus"], "40분")

            reloaded = AppBridge(database, settings)
            planner_row = next(row for row in reloaded.plannerTasks if row["taskId"] == task.id)
            self.assertEqual(planner_row["actualStudy"], "1시간 10분")
            self.assertEqual(planner_row["actualFocus"], "40분")

    def test_demo_tasks_are_interactive_and_month_length_is_dynamic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = AppBridge(
                SessionDatabase(root / "onf.sqlite3"),
                SettingsStore(root / "settings.json"),
            )
            first_id = bridge.plannerTasks[0]["taskId"]
            bridge.cyclePlannerTask(first_id)
            self.assertEqual(bridge.plannerTasks[0]["taskState"], 1)
            bridge.cyclePlannerTask(first_id)
            self.assertEqual(bridge.plannerTasks[0]["taskState"], 2)
            self.assertFalse(bridge.plannerTasks[0]["done"])
            bridge.cyclePlannerTask(first_id)
            self.assertEqual(bridge.plannerTasks[0]["taskState"], 0)
            initial_count = len(bridge.plannerTasks)
            bridge.deletePlannerTask(first_id)
            self.assertEqual(len(bridge.plannerTasks), initial_count - 1)

            while bridge.monthLabel != "2026년 2월":
                bridge.shiftRecords(2, -1)
            self.assertEqual(bridge.monthlyDayCount, 28)
            self.assertEqual(len(bridge.monthlyLevels), 28)

    def test_planner_time_values_normalize_and_calculate_missing_value(self):
        self.assertEqual(_parse_time("9"), 9 * 60)
        self.assertEqual(_parse_time("9:"), 9 * 60)
        self.assertEqual(_parse_time("0930"), 9 * 60 + 30)
        self.assertEqual(
            _resolve_planner_times(9 * 60, None, 45),
            (9 * 60, 9 * 60 + 45, 45),
        )
        self.assertEqual(
            _resolve_planner_times(None, 10 * 60, 45),
            (9 * 60 + 15, 10 * 60, 45),
        )
        self.assertEqual(
            _resolve_planner_times(23 * 60 + 30, 30, 0),
            (23 * 60 + 30, 30, 60),
        )

    def test_existing_planner_time_edit_recalculates_and_persists_third_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            bridge = AppBridge(database, SettingsStore(root / "settings.json"))
            self.assertTrue(
                bridge.addPlannerTask("수학 복습", "09:00", "10:00", "60분")
            )
            task_id = database.list_planner_tasks()[0].id

            bridge.updatePlannerTask(
                task_id, "수학 복습", "09:00", "10:00", "90분", "duration"
            )
            updated = database.list_planner_tasks()[0]
            self.assertEqual(updated.planned_start_minute, 9 * 60)
            self.assertEqual(updated.estimated_minutes, 90)
            self.assertEqual(updated.planned_end_minute, 10 * 60 + 30)

            bridge.updatePlannerTask(
                task_id, "수학 복습", "09:00", "11:00", "90분", "end"
            )
            updated = database.list_planner_tasks()[0]
            self.assertEqual(updated.planned_start_minute, 9 * 60)
            self.assertEqual(updated.planned_end_minute, 11 * 60)
            self.assertEqual(updated.estimated_minutes, 120)

    def test_planner_calculated_field_survives_reload_and_fixed_schedule_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            bridge = AppBridge(database, SettingsStore(root / "settings.json"))
            self.assertTrue(
                bridge.addPlannerTask("수학 복습", "09:00", "10:00", "60분", "start")
            )
            task = database.list_planner_tasks()[0]
            self.assertEqual(task.generated_field, "start")
            self.assertEqual(bridge.plannerTasks[0]["generatedField"], "start")

            bridge.updatePlannerTask(
                task.id,
                "수학 복습",
                "09:00",
                "11:00",
                "90분",
                "duration",
                "start",
            )
            updated = database.list_planner_tasks()[0]
            self.assertEqual(updated.planned_start_minute, 9 * 60 + 30)
            self.assertEqual(updated.planned_end_minute, 11 * 60)
            self.assertEqual(updated.estimated_minutes, 90)

            database.toggle_planner_task_fixed(task.id)
            database.ensure_fixed_schedule_occurrences("2026-09-29")
            occurrence = next(
                row
                for row in database.list_planner_tasks()
                if row.planned_date == "2026-09-29"
            )
            self.assertEqual(occurrence.generated_field, "start")

    def test_records_split_sessions_at_configured_study_day_boundary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            settings = SettingsStore(root / "settings.json")
            database.add_session(
                SessionSummary(
                    started_at_wall="2026-07-20 03:30:00",
                    ended_at_wall="2026-07-20 04:30:00",
                    focus_seconds=3600,
                    non_focus_seconds=0,
                    break_seconds=0,
                    unscored_seconds=0,
                    absent_pending_seconds=0,
                    focus_ratio=1.0,
                    coverage_ratio=1.0,
                    longest_focus_seconds=1800,
                    events=[],
                ),
                root / "session",
                timeline_buckets=[{"focus": 60}] * 60,
            )
            bridge = AppBridge(database, settings)
            bridge._records_date = date(2026, 7, 19)
            bridge.refresh()

            self.assertEqual(bridge.weekLabel, "2026년 7월 19일 ~ 7월 25일")
            self.assertEqual(bridge.dailySummary["focus"], "30분")
            self.assertEqual(bridge.dailyHourlyData[0]["hour"], 3)
            self.assertEqual(bridge.weeklyRecords[0]["study"], 30)
            self.assertEqual(bridge.weeklyRecords[1]["study"], 30)
            self.assertEqual(bridge.monthlySummary["focus"], "1시간 0분")
            self.assertEqual(bridge.monthlySummary["days"], 2)
            self.assertEqual(bridge.monthlyLevels[18:20], [1, 1])

            bridge._records_date = date(2026, 7, 20)
            bridge.refresh()
            self.assertEqual(bridge.dailySummary["focus"], "30분")
            self.assertEqual(bridge.dailyHourlyData[0]["hour"], 4)

    def test_sample_planner_timeline_and_summaries_describe_one_day(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = AppBridge(
                SessionDatabase(root / "onf.sqlite3"),
                SettingsStore(root / "settings.json"),
            )
            self.assertTrue(bridge.plannerUsesSampleData)
            self.assertTrue(bridge.recordsUseSampleData)
            self.assertEqual(bridge.plannerDailySummary["study"], "1시간 40분")
            self.assertEqual(bridge.plannerDailySummary["focus"], "1시간 22분")
            self.assertEqual(bridge.plannerDailySummary["away"], "18분")
            self.assertEqual(bridge.plannerDailySummary["ratio"], 82)

            scored_slots = sum(
                1
                for hour in bridge.plannerHourlyData
                for value in hour["values"]
                if value > 0
            )
            focus_points = sum(
                value
                for hour in bridge.plannerHourlyData
                for value in hour["values"]
                if value > 0
            )
            self.assertEqual(scored_slots * 10, 100)
            self.assertEqual(round(focus_points / 100 * 10), 82)

            selected_weekday = (datetime.now().date().weekday() + 1) % 7
            self.assertEqual(bridge.weeklyRecords[selected_weekday]["study"], 100)
            self.assertEqual(bridge.weeklyRecords[selected_weekday]["focus"], 82)
            self.assertEqual(bridge.weeklyRecords[selected_weekday]["away"], 18)

            self.assertTrue(bridge.addPlannerTask("생물 복습", "18", "19", ""))
            self.assertFalse(bridge.plannerUsesSampleData)
            self.assertFalse(bridge.recordsUseSampleData)
            self.assertEqual(bridge.dailySummary["study"], "0분")

    def test_calendar_event_can_be_selected_as_primary_dday(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = AppBridge(
                SessionDatabase(root / "onf.sqlite3"),
                SettingsStore(root / "settings.json"),
            )
            event_id = bridge.addCalendarEvent("기말고사", "2026-08-15")
            self.assertGreater(event_id, 0)
            self.assertEqual(bridge.primaryDday, {})
            self.assertEqual(bridge.calendarEvents[0]["title"], "기말고사")

            bridge.setPrimaryCalendarEvent(event_id)
            self.assertEqual(bridge.primaryDday["eventId"], event_id)
            self.assertEqual(bridge.primaryDday["title"], "기말고사")
            self.assertTrue(bridge.hasPrimaryDday)
            self.assertEqual(bridge.primaryDdayTitle, "기말고사")

            reloaded = AppBridge(
                SessionDatabase(root / "onf.sqlite3"),
                SettingsStore(root / "settings.json"),
            )
            self.assertEqual(reloaded.primaryDday["eventId"], event_id)

            reloaded.deleteCalendarEvent(event_id)
            self.assertEqual(reloaded.primaryDday, {})
            self.assertFalse(reloaded.hasPrimaryDday)
            self.assertEqual(reloaded.primaryDdayLabel, "")
            self.assertEqual(reloaded.primaryDdayTitle, "")
            self.assertEqual(reloaded.primaryDdayDate, "")


    def test_manual_and_allocated_records_keep_all_period_totals_distinct(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            bridge = AppBridge(database, SettingsStore(root / "settings.json"))
            bridge.addPlannerTask("Math", "", "", "")
            task = database.list_planner_tasks()[0]
            started = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
            session_id = database.add_session(SessionSummary(
                started.isoformat(sep=" "), (started + timedelta(minutes=90)).isoformat(sep=" "),
                3600, 1800, 0, 0, 0, 2 / 3, 1, 600, []), root / "measured", task_records=[])
            bridge.refresh()
            result = bridge.saveStudyRecord(-1, session_id, task.id, "Math", 1, 10)
            self.assertTrue(result["ok"])
            self.assertEqual(bridge.todayStudySeconds, 5400)
            self.assertEqual(bridge.recordSessions[0]["remaining"], 1200)
            result = bridge.saveStudyRecord(-1, -1, task.id, "Offline", 0, 30)
            self.assertTrue(result["ok"])
            self.assertEqual(bridge.todayStudySeconds, 7200)
            self.assertEqual(bridge.dailySummary["study"], "2시간 0분")
            self.assertEqual(bridge.dailySummary["focus"], "1시간 0분")
            self.assertEqual(bridge.dailySummary["ratio"], 67)
            self.assertEqual(sum(row["study"] for row in bridge.weeklyRecords), 120)
            self.assertEqual(bridge.monthlySummary["study"], "2시간 0분")
            self.assertEqual(bridge.monthlySummary["focus"], "1시간 0분")
            self.assertEqual(bridge.plannerTasks[0]["actualFocus"], "미측정")
            self.assertTrue(all(row["focus_seconds"] is None for row in bridge.studyRecords))
            self.assertFalse(bridge.saveStudyRecord(-1, session_id, task.id, "Too much", 0, 30)["ok"])
            manual_id = result["id"]
            self.assertTrue(bridge.saveStudyRecord(manual_id, -1, task.id, "Offline", 0, 20)["ok"])
            self.assertEqual(bridge.todayStudySeconds, 6600)
            self.assertEqual(len(bridge.studyRecords), 2)
            self.assertTrue(bridge.deleteStudyRecord(manual_id)["ok"])
            self.assertEqual(bridge.todayStudySeconds, 5400)
            self.assertEqual(len(bridge.dailyHourlyData), 2)

    def test_duration_only_manual_record_has_no_invented_focus_or_hourly_position(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            bridge = AppBridge(database, SettingsStore(root / "settings.json"))
            self.assertTrue(bridge.saveStudyRecord(-1, -1, -1, "Offline reading", 0, 30)["ok"])
            self.assertFalse(bridge.recordsUseSampleData)
            self.assertEqual(bridge.plannerTasks, [])
            self.assertEqual(bridge.todayStudySeconds, 1800)
            self.assertEqual(bridge.dailySummary["manual"], "30분")
            self.assertFalse(bridge.dailySummary["hasMeasurement"])
            self.assertEqual(bridge.todayHourlyData, [])
            self.assertEqual(bridge.dailyHourlyData, [])
            self.assertFalse(bridge.monthlySummary["hasMeasurement"])
            self.assertEqual(bridge.monthlySummary["days"], 1)
            self.assertTrue(all(row["time"] == "미측정" for row in bridge.monthlySummary["weeks"]))
            self.assertEqual(sum(row["study"] for row in bridge.weeklyRecords), 30)
            self.assertTrue(all(not row["hasMeasurement"] for row in bridge.weeklyRecords))
            record_id = bridge.studyRecords[0]["id"]
            previous = date.today() - timedelta(days=1)
            bridge.selectRecordsDate(previous.isoformat())
            self.assertTrue(bridge.saveStudyRecord(record_id, -1, -1, "Offline reading", 0, 30)["ok"])
            self.assertEqual(bridge.todayStudySeconds, 0)
            self.assertEqual(bridge.dailySummary["study"], "30분")
            self.assertFalse(bridge.saveStudyRecord(-1, -1, -1, "Bad duration", 24, 1)["ok"])
            self.assertFalse(bridge.saveStudyRecord(-1, -1, 999, "Missing task", 0, 30)["ok"])

if __name__ == "__main__":
    unittest.main()
