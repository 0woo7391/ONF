import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from onf_v2.ui_qml.study_appearance import StudyIconProvider
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from onf_v2.app.session_database import SessionDatabase
from onf_v2.app.settings_store import SettingsStore
from onf_v2.core.models import AppState, EffectiveState, SessionSummary
from onf_v2.ui_qml.app_bridge import AppBridge
from onf_v2.ui_qml.measurement_bridge import CameraImageProvider, MeasurementBridge


class QmlPlannerRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = SessionDatabase(self.root / "onf.sqlite3")
        self.settings = SettingsStore(self.root / "settings.json")
        self.bridge = AppBridge(self.database, self.settings)
        self.engine = None

    def tearDown(self):
        if self.engine is not None:
            for window in self.engine.rootObjects():
                window.close()
            self.engine.deleteLater()
            self.app.processEvents()

    def load_window(self):
        self.engine = QQmlApplicationEngine()
        self.engine.addImageProvider("study-icons", StudyIconProvider())
        qml = Path(__file__).parents[1] / "onf_v2/ui_qml/qml/Main.qml"
        self.engine.load(QUrl.fromLocalFile(str(qml.resolve())))
        window = self.engine.rootObjects()[0]
        window.setProperty("backendObject", self.bridge)
        self.app.processEvents()
        return window

    def add_session(self, started, states):
        totals = {key: sum(bucket.get(key, 0) for bucket in states) for key in ("focus", "non_focus", "break", "unscored")}
        scored = totals["focus"] + totals["non_focus"]
        summary = SessionSummary(
            started_at_wall=started.isoformat(sep=" "),
            ended_at_wall=(started + timedelta(seconds=sum(totals.values()))).isoformat(sep=" "),
            focus_seconds=totals["focus"], non_focus_seconds=totals["non_focus"],
            break_seconds=totals["break"], unscored_seconds=totals["unscored"],
            absent_pending_seconds=0,
            focus_ratio=totals["focus"] / scored if scored else 0,
            coverage_ratio=1, longest_focus_seconds=totals["focus"], events=[],
        )
        self.database.add_session(summary, self.root / "session", timeline_buckets=states)

    def test_invalid_times_cannot_be_added_or_overwrite_saved_times(self):
        self.assertFalse(self.bridge.addPlannerTask("Invalid", "25:00", "", ""))
        self.assertFalse(self.bridge.addPlannerTask("Invalid", "", "12:60", ""))
        self.assertEqual(self.database.list_planner_tasks(), [])
        self.assertTrue(self.bridge.addPlannerTask("Valid", "09:00", "10:00", "60"))
        task = self.database.list_planner_tasks()[0]
        self.assertFalse(self.bridge.updatePlannerTask(task.id, "Changed", "25:00", "10:00", "60", "start"))
        saved = self.database.list_planner_tasks()[0]
        self.assertEqual((saved.title, saved.planned_start_minute, saved.planned_end_minute), ("Valid", 540, 600))

    def test_plus_button_keeps_invalid_clock_and_title_editable(self):
        window = self.load_window()
        window.setProperty("currentTabIndex", 2)
        self.app.processEvents()
        title = window.findChild(QObject, "plannerTaskInput")
        title.setProperty("text", "Keep this plan")
        hour = window.findChild(QObject, "plannerStartInputHour")
        minute = window.findChild(QObject, "plannerStartInputMinute")
        hour.forceActiveFocus()
        for key in (Qt.Key_2, Qt.Key_5):
            QTest.keyClick(window, key)
        minute.forceActiveFocus()
        for key in (Qt.Key_0, Qt.Key_0):
            QTest.keyClick(window, key)
        button = window.findChild(QQuickItem, "plannerAddButton")
        point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
        QTest.qWait(50)
        self.assertEqual(self.database.list_planner_tasks(), [])
        self.assertEqual(title.property("text"), "Keep this plan")
        self.assertEqual(hour.property("text"), "25")
        QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(window, Qt.Key_2)
        QTest.keyClick(window, Qt.Key_3)
        QTest.keyClick(window, Qt.Key_Return)
        self.app.processEvents()
        self.assertEqual(self.database.list_planner_tasks()[0].planned_start_minute, 23 * 60)

    def planner_item(self, window, name):
        pending = [window.contentItem()]
        while pending:
            item = pending.pop()
            if item.objectName() == name:
                return item
            pending.extend(item.childItems())
        self.fail(f"Missing planner item: {name}")

    def test_existing_clock_edit_preserves_tab_destination_after_save(self):
        self.bridge.addPlannerTask("Tab test", "09:00", "10:00", "60", "end")
        task_id = self.database.list_planner_tasks()[0].id
        window = self.load_window()
        window.setProperty("currentTabIndex", 2)
        QTest.qWait(80)
        hour = self.planner_item(window, f"plannerRowStart{task_id}Hour")
        hour.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(window, Qt.Key_1)
        QTest.keyClick(window, Qt.Key_1)
        QTest.keyClick(window, Qt.Key_Tab)
        QTest.keyClick(window, Qt.Key_Tab)
        QTest.qWait(100)
        destination = self.planner_item(window, f"plannerRowEnd{task_id}Hour")
        self.assertTrue(destination.property("activeFocus"))
        self.assertEqual(destination.property("selectedText"), "12")
        saved = self.database.list_planner_tasks()[0]
        self.assertEqual((saved.planned_start_minute, saved.planned_end_minute, saved.estimated_minutes), (660, 720, 60))
        capture_dir = os.environ.get("ONF_UI_CAPTURE_DIR")
        if capture_dir:
            Path(capture_dir).mkdir(parents=True, exist_ok=True)
            for width, height in ((1280, 720), (1024, 680)):
                window.setWidth(width)
                window.setHeight(height)
                QTest.qWait(220)
                self.assertTrue(window.grabWindow().save(str(Path(capture_dir) / f"planner-edit-{width}x{height}.png")))

    def test_existing_end_edit_keeps_shift_tab_on_start_minute(self):
        self.bridge.addPlannerTask("Reverse Tab", "09:00", "10:00", "60", "end")
        task_id = self.database.list_planner_tasks()[0].id
        window = self.load_window()
        window.setProperty("currentTabIndex", 2)
        QTest.qWait(80)
        hour = self.planner_item(window, f"plannerRowEnd{task_id}Hour")
        hour.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(window, Qt.Key_1)
        QTest.keyClick(window, Qt.Key_1)
        QTest.keyClick(window, Qt.Key_Backtab)
        QTest.qWait(100)
        self.assertTrue(self.planner_item(window, f"plannerRowStart{task_id}Minute").property("activeFocus"))
        saved = self.database.list_planner_tasks()[0]
        self.assertEqual((saved.planned_start_minute, saved.planned_end_minute, saved.estimated_minutes), (540, 660, 120))

    def test_unchanged_row_tab_does_not_refresh_entire_model(self):
        self.bridge.addPlannerTask("No change", "09:00", "10:00", "60", "end")
        task_id = self.database.list_planner_tasks()[0].id
        window = self.load_window()
        window.setProperty("currentTabIndex", 2)
        QTest.qWait(80)
        notifications = []
        self.bridge.dataChanged.connect(lambda: notifications.append(True))
        minute = self.planner_item(window, f"plannerRowStart{task_id}Minute")
        minute.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Tab)
        QTest.qWait(100)
        self.assertEqual(notifications, [])
        self.assertTrue(self.planner_item(window, f"plannerRowEnd{task_id}Hour").property("activeFocus"))

    def test_duration_enter_saves_recalculated_time_and_keeps_focus(self):
        self.bridge.addPlannerTask("Duration", "09:00", "10:00", "60", "end")
        task_id = self.database.list_planner_tasks()[0].id
        window = self.load_window()
        window.setProperty("currentTabIndex", 2)
        QTest.qWait(80)
        duration = self.planner_item(window, f"plannerRowDuration{task_id}")
        duration.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(window, Qt.Key_9)
        QTest.keyClick(window, Qt.Key_0)
        QTest.keyClick(window, Qt.Key_Return)
        QTest.qWait(100)
        saved = self.database.list_planner_tasks()[0]
        self.assertEqual((saved.estimated_minutes, saved.planned_end_minute), (90, 630))
        self.assertTrue(self.planner_item(window, f"plannerRowDuration{task_id}").property("activeFocus"))

    def test_pending_row_edit_can_be_flushed_synchronously_on_exit(self):
        self.bridge.addPlannerTask("Exit save", "09:00", "10:00", "60", "end")
        task_id = self.database.list_planner_tasks()[0].id
        window = self.load_window()
        window.setProperty("currentTabIndex", 2)
        QTest.qWait(80)
        duration = self.planner_item(window, f"plannerRowDuration{task_id}")
        duration.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(window, Qt.Key_9)
        QTest.keyClick(window, Qt.Key_0)
        QTest.keyClick(window, Qt.Key_Return)
        page = window.findChild(QObject, "plannerPage")
        self.assertTrue(QMetaObject.invokeMethod(page, "flushPlanEdits"))
        self.assertEqual(self.database.list_planner_tasks()[0].estimated_minutes, 90)

    def test_zero_focus_is_present_but_break_and_empty_cells_are_not_scored(self):
        day = date(2026, 10, 5)
        self.add_session(datetime(2026, 10, 5, 10), [{"non_focus": 60}] * 10 + [{"break": 60}] * 10)
        self.bridge._records_date = day
        self.bridge._planner_date = day
        self.bridge.refresh()
        hour = self.bridge.dailyHourlyData[0]
        self.assertEqual(hour["hour"], 10)
        self.assertEqual(hour["values"][0], 0)
        self.assertEqual(hour["present"], [True, False, False, False, False, False])
        self.assertEqual(self.bridge.plannerHourlyData, self.bridge.dailyHourlyData)

    def test_learning_day_is_independent_of_planner_and_record_navigation(self):
        now = datetime.now()
        study_day = (now - timedelta(hours=self.settings.load().study_day_start_hour)).date()
        current_start = datetime.combine(study_day, datetime.min.time()) + timedelta(hours=10)
        self.add_session(current_start, [{"focus": 60}] * 10)
        self.add_session(current_start - timedelta(days=1) + timedelta(hours=1), [{"focus": 60}] * 20)
        self.bridge.refresh()
        window = self.load_window()
        self.assertEqual(window.property("todayStudySeconds"), 600)
        timeline = window.findChild(QObject, "studyTimeline")
        self.assertTrue(QMetaObject.invokeMethod(window.findChild(QObject, "learningPage"), "openTools", Qt.DirectConnection, Q_ARG("QVariant", 1)))
        self.bridge.selectPlannerDate((study_day - timedelta(days=1)).isoformat())
        self.bridge.shiftRecords(0, -1)
        self.app.processEvents()
        actual = timeline.property("hourlyData")
        if hasattr(actual, "toVariant"):
            actual = actual.toVariant()
        self.assertEqual([item["hour"] for item in actual], [10])
        self.assertEqual([item["hour"] for item in self.bridge.plannerHourlyData], [11])
        self.assertEqual(window.property("todayStudySeconds"), 600)
        reloaded = AppBridge(self.database, self.settings)
        self.assertEqual(reloaded.todayStudySeconds, 600)

    def test_planner_timeline_has_24_hours_in_study_day_order(self):
        window = self.load_window()
        timeline = window.findChild(QObject, "dailyPlannerTimeline")
        self.assertIsNotNone(timeline)
        self.assertEqual(timeline.property("studyDayStartHour"), self.settings.load().study_day_start_hour)
        self.assertEqual(timeline.property("contentHeight"), 24 * 33)
        wrapped = self.engine.newQObject(timeline)
        hours = [wrapped.property("hourForRow").callWithInstance(wrapped, [index]).toInt() for index in range(24)]
        self.assertEqual(len(set(hours)), 24)
        self.assertEqual(hours[0], self.settings.load().study_day_start_hour)
        self.assertEqual(set(hours), set(range(24)))

    def test_legacy_break_only_session_does_not_create_red_study_cell(self):
        started = datetime(2026, 10, 5, 10)
        self.add_session(started, [{"break": 60}] * 10)
        with self.database._connection() as connection:
            connection.execute("UPDATE sessions SET timeline_json = '[]'")
        self.bridge._records_date = started.date()
        self.bridge.refresh()
        self.assertEqual(self.bridge.dailyHourlyData, [])

    def test_edit_today_button_really_opens_today_planner(self):
        self.bridge.shiftPlannerDate(-1)
        window = self.load_window()
        button = window.findChild(QObject, "editTodayPlanButton")
        self.assertIsNotNone(button)
        self.assertTrue(QMetaObject.invokeMethod(button, "clicked"))
        self.app.processEvents()
        self.assertEqual(window.property("currentTabIndex"), 2)
        self.assertEqual(self.bridge.plannerDateIso, date.today().isoformat())

    def test_live_study_total_excludes_break_and_previous_study_day(self):
        import time
        bridge = MeasurementBridge(CameraImageProvider(), self.settings, self.database, auto_start=False)
        bridge.timer.stop()
        self.addCleanup(bridge.shutdown)
        started = time.monotonic() - 1200
        bridge.session.app_state = AppState.RUNNING
        bridge.session.started_at_wall = "2026-10-05 03:50:00"
        metrics = bridge.session.metrics
        metrics.update(EffectiveState.FOCUS, started)
        metrics.update(EffectiveState.BREAK, started + 900)
        metrics.update(EffectiveState.FOCUS, started + 1200)
        with patch("onf_v2.ui_qml.measurement_bridge.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 5, 4, 10)
            self.assertEqual(bridge.todayStudySeconds, 300)
        bridge.session.app_state = AppState.RESULT
        self.assertEqual(bridge.todayStudySeconds, 0)

    def test_saved_study_total_uses_states_after_day_boundary(self):
        self.add_session(datetime(2026, 10, 5, 3, 50), [{"focus": 60}] * 15 + [{"break": 60}] * 5)
        with patch("onf_v2.ui_qml.app_bridge.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 5, 4, 10)
            self.bridge.refresh()
            self.assertEqual(self.bridge.todayStudySeconds, 300)

    def test_today_total_hands_live_time_to_saved_time_without_double_counting(self):
        import time
        fixed_now = datetime(2026, 10, 5, 12)
        self.add_session(fixed_now - timedelta(hours=1), [{"focus": 60}] * 10)
        with patch("onf_v2.ui_qml.app_bridge.datetime", wraps=datetime) as saved_clock, patch("onf_v2.ui_qml.measurement_bridge.datetime", wraps=datetime) as live_clock:
            saved_clock.now.return_value = fixed_now
            live_clock.now.return_value = fixed_now
            self.bridge.refresh()
            window = self.load_window()
            live = MeasurementBridge(CameraImageProvider(), self.settings, self.database, auto_start=False)
            live.timer.stop()
            self.addCleanup(live.shutdown)
            live.session.app_state = AppState.RUNNING
            live.session.started_at_wall = (fixed_now - timedelta(minutes=5)).isoformat(sep=" ")
            started = time.monotonic() - 300
            live.session.metrics.update(EffectiveState.FOCUS, started)
            live.session.metrics.update(EffectiveState.BREAK, started + 300)
            window.setProperty("measurementObject", live)
            self.app.processEvents()
            self.assertEqual(window.property("todayStudySeconds"), 900)
            live.session.app_state = AppState.RESULT
            self.add_session(fixed_now - timedelta(minutes=5), [{"focus": 60}] * 5)
            self.bridge.refresh()
            live.stateChanged.emit()
            self.app.processEvents()
            self.assertEqual(window.property("todayStudySeconds"), 900)

    def test_today_refresh_rolls_at_study_day_boundary(self):
        with patch("onf_v2.ui_qml.app_bridge.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 5, 3, 59)
            self.bridge.refresh()
            self.assertEqual(self.bridge._today_study_date, date(2026, 10, 4))
            clock.now.return_value = datetime(2026, 10, 5, 4)
            self.bridge.refreshToday()
            self.assertEqual(self.bridge._today_study_date, date(2026, 10, 5))


if __name__ == "__main__":
    unittest.main()
