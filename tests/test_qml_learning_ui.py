import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate, QDateTime, QMetaObject, QObject, QTime, QUrl
from PySide6.QtQml import QQmlApplicationEngine
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
        self.assertEqual(window.property("currentTask"), "영어 독해 지문 2개")
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
        full_day_timeline = window.findChild(QObject, "fullDayTimeline")
        weekly_charts = window.findChild(QObject, "weeklyRecordCharts")
        self.assertIsNotNone(timeline)
        self.assertIsNotNone(pomodoro_ring)
        self.assertIsNotNone(camera_panel)
        self.assertIsNotNone(planner_page)
        self.assertIsNotNone(records_page)
        self.assertIsNotNone(settings_page)
        self.assertIsNotNone(full_day_timeline)
        self.assertIsNotNone(weekly_charts)

        window.setProperty(
            "currentDateTime",
            QDateTime(QDate(2026, 7, 20), QTime(9, 15)),
        )
        self.assertTrue(QMetaObject.invokeMethod(window, "refreshScheduledTask"))
        self.assertEqual(window.property("currentTask"), "영어 독해 지문 2개")
        self.assertTrue(window.property("currentTaskAutoSelected"))

        for tab_index in range(4):
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


if __name__ == "__main__":
    unittest.main()
