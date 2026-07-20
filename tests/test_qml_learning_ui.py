import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication


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
        self.assertEqual(window.objectName(), "learningWindow")
        self.assertEqual(window.property("minimumWidth"), 1024)
        self.assertEqual(window.property("minimumHeight"), 680)
        self.assertEqual(window.property("currentTask"), "영어 독해 지문 2개")
        self.assertTrue(window.property("pomodoroMode"))
        self.assertTrue(window.property("cameraVisible"))

        timeline = window.findChild(QObject, "studyTimeline")
        pomodoro_ring = window.findChild(QObject, "pomodoroRing")
        camera_panel = window.findChild(QObject, "cameraPanel")
        planner_page = window.findChild(QObject, "plannerPage")
        records_page = window.findChild(QObject, "recordsPage")
        settings_page = window.findChild(QObject, "settingsPage")
        self.assertIsNotNone(timeline)
        self.assertIsNotNone(pomodoro_ring)
        self.assertIsNotNone(camera_panel)
        self.assertIsNotNone(planner_page)
        self.assertIsNotNone(records_page)
        self.assertIsNotNone(settings_page)

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
