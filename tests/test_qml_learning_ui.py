import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl
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


if __name__ == "__main__":
    unittest.main()
