import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate, QDateTime, QMetaObject, QObject, Property, Signal, Slot, Qt, QTime, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from onf_v2.ui_qml.study_appearance import StudyIconProvider
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from onf_v2.app.session_database import SessionDatabase
from onf_v2.app.settings_store import SettingsStore
from onf_v2.ui_qml.app_bridge import AppBridge


class QmlLearningUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_learning_page_loads_at_supported_minimum_size(self):
        engine = QQmlApplicationEngine()
        engine.addImageProvider("study-icons", StudyIconProvider())
        qml_path = (
            Path(__file__).parents[1]
            / "onf_v2"
            / "ui_qml"
            / "qml"
            / "Main.qml"
        )
        engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))

        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        temp_root = Path(temp_dir.name)
        bridge = AppBridge(
            SessionDatabase(temp_root / "onf.sqlite3"),
            SettingsStore(temp_root / "settings.json"),
        )
        window.setProperty("backendObject", bridge)
        self.app.processEvents()
        self.assertEqual(window.objectName(), "learningWindow")
        self.assertEqual(window.property("minimumWidth"), 1024)
        self.assertEqual(window.property("minimumHeight"), 680)
        self.assertNotEqual(window.property("currentTask"), "")
        self.assertEqual(
            window.property("pomodoroMode"),
            bridge.settings["session_mode"] == "pomodoro",
        )
        self.assertTrue(window.property("cameraVisible"))

        timeline = window.findChild(QObject, "studyTimeline")
        pomodoro_ring = window.findChild(QObject, "pomodoroRing")
        camera_panel = window.findChild(QObject, "cameraPanel")
        planner_page = window.findChild(QObject, "plannerPage")
        records_page = window.findChild(QObject, "recordsPage")
        settings_page = window.findChild(QObject, "settingsPage")
        measurement_page = window.findChild(QObject, "measurementPage")
        screen_calibration_window = window.findChild(QObject, "screenCalibrationWindow")
        full_day_timeline = window.findChild(QObject, "fullDayTimeline")
        weekly_charts = window.findChild(QObject, "weeklyRecordCharts")
        planner_calendar = window.findChild(QObject, "plannerCalendarPopup")
        self.assertIsNotNone(timeline)
        self.assertIsNotNone(pomodoro_ring)
        self.assertIsNotNone(camera_panel)
        self.assertIsNotNone(planner_page)
        self.assertIsNotNone(records_page)
        self.assertIsNotNone(settings_page)
        self.assertIsNotNone(measurement_page)
        self.assertIsNotNone(screen_calibration_window)
        self.assertIsNotNone(full_day_timeline)
        self.assertIsNotNone(weekly_charts)
        self.assertIsNotNone(planner_calendar)
        start_input = window.findChild(QObject, "plannerStartInput")
        start_hour = window.findChild(QObject, "plannerStartInputHour")
        start_minute = window.findChild(QObject, "plannerStartInputMinute")
        end_hour = window.findChild(QObject, "plannerEndInputHour")
        end_minute = window.findChild(QObject, "plannerEndInputMinute")
        task_input = window.findChild(QObject, "plannerTaskInput")
        duration_input = window.findChild(QObject, "plannerDurationInput")
        add_button = window.findChild(QObject, "plannerAddButton")
        self.assertIsNotNone(start_input)
        self.assertIsNotNone(start_hour)
        self.assertIsNotNone(start_minute)
        self.assertIsNotNone(end_hour)
        self.assertIsNotNone(end_minute)
        self.assertIsNotNone(task_input)
        self.assertIsNotNone(duration_input)
        self.assertIsNotNone(add_button)
        start_hour.setProperty("text", "9")
        start_minute.setProperty("text", "")
        self.assertTrue(QMetaObject.invokeMethod(start_input, "commit"))
        self.assertEqual(start_input.property("text"), "09:00")
        start_hour.setProperty("text", "25")
        start_minute.setProperty("text", "00")
        self.assertTrue(QMetaObject.invokeMethod(start_input, "commit"))
        self.assertTrue(start_input.property("invalid"))
        self.assertEqual(start_hour.property("text"), "25")
        start_hour.setProperty("text", "23")
        self.assertTrue(QMetaObject.invokeMethod(start_input, "commit"))
        self.assertFalse(start_input.property("invalid"))
        self.assertEqual(start_input.property("text"), "23:00")

        window.setProperty("currentTabIndex", 2)
        self.app.processEvents()
        task_input.forceActiveFocus()
        self.assertTrue(task_input.property("activeFocus"))
        for expected in (
            start_hour,
            start_minute,
            end_hour,
            end_minute,
            duration_input,
            add_button,
        ):
            QTest.keyClick(window, Qt.Key_Tab)
            self.app.processEvents()
            self.assertTrue(
                expected.property("activeFocus"),
                f"expected {expected.objectName()}, states="
                + str(
                    {
                        item.objectName(): item.property("activeFocus")
                        for item in (task_input, start_hour, start_minute, end_hour, end_minute, duration_input, add_button)
                    }
                ),
            )
        QTest.keyClick(window, Qt.Key_Backtab)
        self.app.processEvents()
        self.assertTrue(duration_input.property("activeFocus"))

        window.setProperty(
            "currentDateTime",
            QDateTime(QDate(2026, 7, 20), QTime(9, 15)),
        )
        self.assertTrue(QMetaObject.invokeMethod(window, "refreshScheduledTask"))
        self.assertEqual(window.property("recommendedTaskTitle"), "영어 독해 지문 2개")
        self.assertEqual(window.property("currentTaskId"), -1)
        self.assertFalse(window.property("currentTaskAutoSelected"))

        bridge.cyclePlannerTask(-1)
        bridge.cyclePlannerTask(-3)
        bridge.cyclePlannerTask(-3)
        bridge.cyclePlannerTask(-4)
        self.app.processEvents()
        self.assertEqual(window.property("currentTask"), "모든 목표를 완료했습니다!")
        self.assertEqual(window.property("currentTaskSchedule"), "-")
        self.assertFalse(window.property("currentTaskAvailable"))

        for tab_index in range(5):
            window.setProperty("currentTabIndex", tab_index)
            self.app.processEvents()
            self.assertEqual(window.property("currentTabIndex"), tab_index)

        for period_index in range(3):
            records_page.setProperty("periodIndex", period_index)
            self.app.processEvents()
            self.assertEqual(records_page.property("periodIndex"), period_index)

        window.setProperty("currentTabIndex", 0)

        timeline.setProperty("currentHour", 1)
        self.assertEqual(timeline.property("visibleRange"), "22:00 — 04:59")

        initial_camera_width = camera_panel.property("width")
        window.setProperty("cameraVisible", False)
        self.app.processEvents()
        self.assertAlmostEqual(
            camera_panel.property("width"),
            initial_camera_width,
            delta=1.0,
        )

        window.setProperty("sessionRunning", True)
        window.setProperty("elapsedSeconds", 125)
        window.setProperty("todayStudySeconds", 925)
        window.setProperty("pomodoroSeconds", 310)
        window.setProperty("completedRounds", 2)
        self.assertTrue(QMetaObject.invokeMethod(window, "endStudySession"))
        self.assertFalse(window.property("sessionRunning"))
        self.assertEqual(window.property("elapsedSeconds"), 125)
        self.assertEqual(window.property("pomodoroSeconds"), 310)
        self.assertEqual(window.property("completedRounds"), 2)
        self.assertEqual(window.property("todayStudySeconds"), 925)

        self.assertTrue(QMetaObject.invokeMethod(window, "startStudySession"))
        self.assertTrue(window.property("sessionRunning"))
        self.assertEqual(window.property("elapsedSeconds"), 0)
        self.assertEqual(window.property("pomodoroSeconds"), 25 * 60)
        self.assertEqual(window.property("completedRounds"), 0)
        self.assertEqual(window.property("todayStudySeconds"), 925)

    def test_planner_enter_adds_task_and_existing_times_recalculate(self):
        engine = QQmlApplicationEngine()
        engine.addImageProvider("study-icons", StudyIconProvider())
        qml_path = (
            Path(__file__).parents[1]
            / "onf_v2"
            / "ui_qml"
            / "qml"
            / "Main.qml"
        )
        engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))
        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        database = SessionDatabase(root / "onf.sqlite3")
        bridge = AppBridge(database, SettingsStore(root / "settings.json"))
        window.setProperty("backendObject", bridge)
        window.setProperty("currentTabIndex", 2)
        self.app.processEvents()

        task_input = window.findChild(QObject, "plannerTaskInput")
        task_input.setProperty("text", "화학 복습")
        task_input.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Return)
        self.app.processEvents()

        tasks = database.list_planner_tasks()
        self.assertEqual(len(tasks), 1)
        task_id = tasks[0].id
        self.assertEqual(tasks[0].title, "화학 복습")
        self.assertIsNone(tasks[0].planned_start_minute)

        start_hour = window.findChild(QObject, "plannerStartInputHour")
        start_minute = window.findChild(QObject, "plannerStartInputMinute")
        task_input.setProperty("text", "Lunch")
        start_hour.setProperty("text", "12")
        start_minute.setProperty("text", "30")
        start_minute.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Return)
        self.app.processEvents()

        tasks = database.list_planner_tasks()
        self.assertEqual(len(tasks), 2)
        lunch = next(task for task in tasks if task.title == "Lunch")
        self.assertEqual(lunch.planned_start_minute, 12 * 60 + 30)

    def test_selected_duplicate_title_passes_exact_task_id_to_session(self):
        class MeasurementStub(QObject):
            stateChanged = Signal()

            def __init__(self):
                super().__init__()
                self.arguments = None

            @Property(bool, notify=stateChanged)
            def sessionRunning(self):
                return False

            @Slot()
            def reloadSettings(self):
                pass

            @Slot(str, int, str, str, result=bool)
            def startSession(self, mode, task_id, title, unused):
                self.arguments = (mode, task_id, title, unused)
                return True

        engine = QQmlApplicationEngine()
        engine.addImageProvider("study-icons", StudyIconProvider())
        qml_path = (
            Path(__file__).parents[1]
            / "onf_v2"
            / "ui_qml"
            / "qml"
            / "Main.qml"
        )
        engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))
        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            bridge = AppBridge(database, SettingsStore(root / "settings.json"))
            bridge.addPlannerTask("중복 제목", "", "", "")
            bridge.addPlannerTask("중복 제목", "", "", "")
            second_id = database.list_planner_tasks()[1].id
            measurement = MeasurementStub()
            window.setProperty("backendObject", bridge)
            window.setProperty("measurementObject", measurement)
            window.setProperty("currentTask", "중복 제목")
            window.setProperty("currentTaskId", second_id)
            window.setProperty("currentTaskAvailable", True)

            self.assertTrue(QMetaObject.invokeMethod(window, "startStudySession"))

            self.assertEqual(measurement.arguments[1], second_id)
            self.assertEqual(measurement.arguments[2], "중복 제목")


if __name__ == "__main__":
    unittest.main()
