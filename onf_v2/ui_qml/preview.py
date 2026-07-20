from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from onf_v2.ui_qml.app_bridge import AppBridge


def run() -> int:
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ONF V2")

    engine = QQmlApplicationEngine()
    bridge = AppBridge()
    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))
    if not engine.rootObjects():
        return 1
    engine.rootObjects()[0].setProperty("backendObject", bridge)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
