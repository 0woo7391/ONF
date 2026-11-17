from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from onf_v2.ui_qml.app_bridge import AppBridge
from onf_v2.ui_qml.measurement_bridge import CameraImageProvider, MeasurementBridge
from onf_v2.ui_qml.study_appearance import StudyIconProvider


def run() -> int:
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("ONF V2")

    engine = QQmlApplicationEngine()
    engine.addImageProvider("study-icons", StudyIconProvider())
    bridge = AppBridge()
    camera_provider = CameraImageProvider()
    engine.addImageProvider("camera", camera_provider)
    measurement = MeasurementBridge(
        camera_provider,
        bridge.settings_store,
        bridge.database,
    )
    qml_path = Path(__file__).with_name("qml") / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))
    if not engine.rootObjects():
        measurement.shutdown()
        return 1
    root = engine.rootObjects()[0]
    root.setProperty("backendObject", bridge)
    root.setProperty("measurementObject", measurement)
    measurement.recordsChanged.connect(bridge.refresh)
    measurement.alertRequested.connect(
        lambda: bridge.testAlert(
            int(bridge.settings["alert_volume"]),
            str(bridge.settings["alert_sound"]),
        )
        if bridge.settings["sound_enabled"]
        else None
    )
    measurement.calibrationCueRequested.connect(
        lambda: bridge.testAlert(
            max(8, int(bridge.settings["alert_volume"] * 0.35)),
            "soft",
        )
        if bridge.settings["sound_enabled"]
        else None
    )
    app.aboutToQuit.connect(measurement.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
