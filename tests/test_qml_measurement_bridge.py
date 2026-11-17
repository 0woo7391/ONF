import os
import tempfile
import time
import unittest
import numpy as np
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMetaObject, QObject, QPointF, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QImage
from PySide6.QtQml import QQmlApplicationEngine
from onf_v2.ui_qml.study_appearance import StudyIconProvider
from PySide6.QtTest import QTest

from onf_v2.app.camera_service import CameraFrame
from onf_v2.app.session_database import SessionDatabase
from onf_v2.app.settings_store import SettingsStore
from onf_v2.core.models import (
    CalibrationStatus,
    EffectiveState,
    FocusDecision,
    FrameObservation,
    ObservationState,
)
from onf_v2.ui_qml.measurement_bridge import CameraImageProvider, MeasurementBridge
from onf_v2.ui_qml.app_bridge import AppBridge
from onf_v2.core.screen_gaze import fit_screen_gaze
from tests.test_screen_gaze import CONTEXT, POSITIONS, gaze_observation, samples_at
from tests.test_calibration import observation as calibration_observation


class QmlMeasurementBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/malgun.ttf"
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and font_path.exists():
            families = QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(str(font_path)))
            bold_font = font_path.with_name("malgunbd.ttf")
            if bold_font.exists():
                QFontDatabase.addApplicationFont(str(bold_font))
            if families:
                cls.app.setFont(QFont(families[0]))

    def test_bridge_starts_without_opening_hardware_in_unit_test(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(),
                SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            self.addCleanup(bridge.shutdown)

            self.assertFalse(bridge.cameraConnected)
            self.assertFalse(bridge.screenReady)
            self.assertFalse(bridge.writingReady)
            self.assertEqual(bridge.appState, "preview")
            self.assertEqual(len(bridge.cameraOptions), 8)
            self.assertFalse(bridge.startSession("free", -1, "", ""))

    def test_camera_failure_becomes_unscored_and_discards_old_analysis(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        bridge = MeasurementBridge(
            CameraImageProvider(),
            SettingsStore(root / "settings.json"),
            SessionDatabase(root / "onf.sqlite3"),
            auto_start=False,
        )
        self.addCleanup(bridge.shutdown)
        bridge.camera = Mock()
        bridge.camera.read.return_value = CameraFrame(False, time.monotonic(), error="lost")
        bridge.camera_connected = True
        bridge.analyzer = Mock()
        bridge.session.start()
        earlier = time.monotonic() - 0.2
        focus = FocusDecision(earlier, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test")
        bridge.session.update(focus)
        bridge.latest_decision = focus
        stale = Future()
        bridge.analysis_future = stale

        bridge._tick()

        self.assertEqual(bridge.latest_decision.effective_state, EffectiveState.UNSCORED)
        self.assertEqual(bridge.session.metrics.last_effective_state, EffectiveState.UNSCORED)
        stale.set_result(FrameObservation(timestamp=earlier + 0.05))
        bridge._consume_analysis()
        self.assertEqual(bridge.latest_decision.raw_state, ObservationState.CAMERA_ERROR)

    def test_analysis_stall_expires_focus_while_camera_still_has_frames(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        bridge = MeasurementBridge(
            CameraImageProvider(),
            SettingsStore(root / "settings.json"),
            SessionDatabase(root / "onf.sqlite3"),
            auto_start=False,
        )
        self.addCleanup(bridge.shutdown)
        bridge.camera = Mock()
        bridge.camera_connected = True
        bridge.analyzer = Mock()
        bridge.session.start()
        earlier = time.monotonic() - 3.0
        focus = FocusDecision(earlier, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test")
        bridge.session.update(focus)
        bridge.latest_decision = focus
        bridge.last_sequence = 1
        bridge.last_preview_at = time.monotonic()
        bridge.camera.read.return_value = CameraFrame(
            True, bridge.last_preview_at, frame=object(), sequence=1
        )
        pending = Future()
        pending.set_result(FrameObservation(timestamp=time.monotonic() - 0.5))
        bridge.analysis_future = pending
        bridge.analysis_generation = bridge.observation_generation

        bridge._tick()

        self.assertEqual(bridge.latest_decision.effective_state, EffectiveState.UNSCORED)
        self.assertEqual(bridge.latest_decision.raw_state, ObservationState.LOW_CONFIDENCE)
        self.assertAlmostEqual(bridge.session.metrics.durations[EffectiveState.FOCUS], 2.0, delta=0.05)

    def test_break_boundaries_are_counted_without_camera_frames(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        bridge = MeasurementBridge(
            CameraImageProvider(),
            SettingsStore(root / "settings.json"),
            SessionDatabase(root / "onf.sqlite3"),
            auto_start=False,
        )
        self.addCleanup(bridge.shutdown)
        bridge.app_usage_tracker = Mock()
        bridge.session.start(started_at_monotonic=0.0)
        bridge.session.update(
            FocusDecision(0.1, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test")
        )

        bridge._set_session_break(True, 1.0)
        bridge._set_session_break(False, 3.0)
        summary = bridge.session.finish(5.0)

        self.assertAlmostEqual(summary.focus_seconds, 0.9)
        self.assertAlmostEqual(summary.break_seconds, 2.0)
        self.assertAlmostEqual(summary.unscored_seconds, 2.1)
        self.assertAlmostEqual(
            summary.focus_seconds + summary.break_seconds + summary.unscored_seconds,
            5.0,
        )
        self.assertAlmostEqual(
            sum(sum(bucket.values()) for bucket in bridge.session.metrics.minute_buckets),
            5.0,
        )
        self.assertAlmostEqual(
            sum(sum(bucket.values()) for bucket in bridge.session.metrics.timeline_slot_buckets),
            5.0,
        )

    def test_delayed_analysis_cannot_replace_break_or_finished_session(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        bridge = MeasurementBridge(
            CameraImageProvider(),
            SettingsStore(root / "settings.json"),
            SessionDatabase(root / "onf.sqlite3"),
            auto_start=False,
        )
        self.addCleanup(bridge.shutdown)
        bridge.session.start()
        pending = Future()
        bridge.analysis_future = pending
        bridge.analysis_generation = bridge.observation_generation
        now = time.monotonic()

        bridge._set_session_break(True, now)
        pending.set_result(FrameObservation(timestamp=now + 0.1))
        bridge._consume_analysis()
        self.assertEqual(bridge.latest_decision.effective_state, EffectiveState.BREAK)

        pending_after_break = Future()
        bridge.analysis_future = pending_after_break
        bridge.analysis_generation = bridge.observation_generation
        bridge.endSession()
        pending_after_break.set_result(FrameObservation(timestamp=time.monotonic()))
        bridge._consume_analysis()
        self.assertEqual(bridge.appState, "result")
        self.assertEqual(bridge.statusText, "학습 종료")

    def test_settings_reload_updates_work_mode_and_alert_delay(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = SettingsStore(root / "settings.json")
            bridge = MeasurementBridge(
                CameraImageProvider(),
                store,
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            self.addCleanup(bridge.shutdown)
            settings = store.load()
            settings.work_mode = "screen_writing"
            settings.attention_alert_seconds = 90
            store.save(settings)

            bridge.reloadSettings()

            self.assertTrue(bridge.writingRequired)
            self.assertEqual(bridge.alert_controller.threshold_seconds, 90)

    def test_screen_calibration_can_be_cancelled_and_uses_monitor_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(),
                SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            analyzer = Mock()
            bridge.analyzer = analyzer
            bridge.camera_connected = True

            bridge.startCalibration("screen")

            self.assertEqual(bridge.calibrationTarget, "screen")
            self.assertEqual(
                bridge.engine.calibration.guided_targets,
                ("center", "up", "down", "left", "right"),
            )
            self.assertEqual(bridge.engine.calibration.target_settle_seconds, 2.0)
            self.assertEqual(bridge.engine.calibration.samples_per_target, 12)
            self.assertEqual(bridge.engine.calibration.target_valid_seconds, 2.0)
            bridge.cancelCalibration()
            self.assertEqual(bridge.calibrationTarget, "")
            self.assertEqual(bridge.appState, "preview")
            self.assertIn("취소", bridge.calibrationMessage)

            bridge.shutdown()
            analyzer.close.assert_called_once()

    def test_cancelled_calibration_rejects_old_analysis_and_display_signal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(),
                SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            self.addCleanup(bridge.shutdown)
            bridge.analyzer = Mock()
            bridge.camera_connected = True
            pending = Future()
            bridge.analysis_future = pending
            bridge.analysis_generation = bridge.observation_generation

            self.assertTrue(bridge.startCalibration("screen"))
            old_run = bridge.calibrationRunId
            pending.set_result(FrameObservation(timestamp=time.monotonic()))
            bridge._consume_analysis()
            self.assertEqual(bridge.engine.calibration.samples, [])

            late = Future()
            bridge.analysis_future = late
            bridge.analysis_generation = bridge.observation_generation
            bridge.cancelCalibration()
            self.assertFalse(bridge.screenTargetDisplayed(old_run, 0, "center"))
            self.assertTrue(bridge.startCalibration("screen"))
            late.set_result(FrameObservation(timestamp=time.monotonic()))
            bridge._consume_analysis()
            self.assertEqual(bridge.engine.calibration.samples, [])
            self.assertFalse(bridge.screenTargetDisplayed(old_run, 0, "center"))
            self.assertTrue(bridge.screenTargetDisplayed(bridge.calibrationRunId, 0, "center"))

    def test_calibration_timeout_runs_without_camera_frames(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(),
                SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            self.addCleanup(bridge.shutdown)
            bridge.analyzer = Mock()
            bridge.camera = Mock()
            bridge.camera_connected = True
            self.assertTrue(bridge.startCalibration("screen"))
            bridge.camera_connected = False
            bridge.next_camera_retry_at = float("inf")
            bridge.engine.calibration.started_at -= 46.0

            bridge._tick()

            self.assertEqual(bridge.calibrationTarget, "")
            self.assertEqual(bridge.engine.calibration.status, CalibrationStatus.FAILED)
            self.assertIn("표적", bridge.calibrationMessage)

    def test_screen_recalibration_preserves_writing_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(),
                SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            self.addCleanup(bridge.shutdown)
            bridge.engine.set_work_mode("screen_writing")
            writing = bridge.engine.writing_calibration
            previous_profile = object()
            writing.profile = previous_profile
            writing.status = CalibrationStatus.READY
            bridge.analyzer = Mock()
            bridge.camera_connected = True

            self.assertTrue(bridge.startCalibration("screen"))
            self.assertIs(writing.profile, previous_profile)
            self.assertTrue(bridge.writingReady)

            bridge.engine.calibration.status = CalibrationStatus.FAILED
            bridge.engine.calibration.failed_targets = ("center",)
            bridge.calibration_target = ""
            self.assertTrue(bridge.retryScreenCalibration())
            self.assertIs(writing.profile, previous_profile)
            self.assertTrue(bridge.writingReady)

            bridge.cancelCalibration()

            self.assertIs(writing.profile, previous_profile)
            self.assertTrue(bridge.writingReady)

    def test_writing_calibration_uses_natural_writing_samples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(),
                SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"),
                auto_start=False,
            )
            manager = bridge.engine.writing_calibration

            self.assertEqual(manager.guided_targets, ())
            self.assertEqual(manager.duration_seconds, 12.0)
            self.assertTrue(manager.progress_by_valid_samples)
            self.assertEqual(manager.max_collection_seconds, 30.0)
            self.assertFalse(manager.enforce_stability)

            bridge.shutdown()

    def test_stale_analysis_cannot_add_time_to_screen_calibration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(bridge.shutdown)
            bridge.timer.stop()
            bridge.analyzer = Mock()
            bridge.camera_connected = True
            self.assertTrue(bridge.startCalibration("screen"))
            manager = bridge.engine.calibration
            manager.started_at -= 3.0
            manager.target_started_at = time.monotonic() - 3.0
            pending = Future()
            pending.set_result(FrameObservation(timestamp=time.monotonic() - 0.6))
            bridge.analysis_future = pending
            bridge.analysis_generation = bridge.observation_generation

            bridge._consume_analysis()

            self.assertEqual(manager.samples, [])
            self.assertEqual(bridge.screenTargetProgress, 0.0)
            self.assertIsNone(bridge.latest_observation)

    def test_camera_change_discards_pending_retry_samples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bridge = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(bridge.shutdown)
            bridge.timer.stop()
            bridge.camera = Mock()
            bridge.analyzer = Mock()
            bridge.camera_connected = True
            self.assertTrue(bridge.startCalibration("screen"))
            manager = bridge.engine.calibration
            manager.status = CalibrationStatus.FAILED
            manager.failed_targets = ("up",)
            manager.samples_by_target["center"] = [FrameObservation(timestamp=time.monotonic())]
            manager.completed_targets.add("center")
            bridge.calibration_target = ""

            bridge.selectCamera(1)

            self.assertEqual(manager.status, CalibrationStatus.IDLE)
            self.assertEqual(manager.samples_by_target, {})
            self.assertFalse(bridge.retryScreenCalibration())
            bridge.camera_future.result(timeout=2.0)

    def test_screen_calibration_opens_and_closes_fullscreen_window(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = SettingsStore(root / "settings.json")
            database = SessionDatabase(root / "onf.sqlite3")
            provider = CameraImageProvider()
            measurement = MeasurementBridge(
                provider,
                store,
                database,
                auto_start=False,
            )
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera_connected = True
            backend = AppBridge(database, store)
            engine = QQmlApplicationEngine()
            engine.addImageProvider("study-icons", StudyIconProvider())
            engine.addImageProvider("camera", provider)
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
            window.setProperty("backendObject", backend)
            window.setProperty("measurementObject", measurement)
            calibration_window = window.findChild(QObject, "screenCalibrationWindow")
            self.assertIsNotNone(calibration_window)

            measurement.startCalibration("screen")
            self.app.processEvents()
            self.assertTrue(calibration_window.property("visible"))
            self.assertIsNone(measurement.engine.calibration.target_started_at)
            QTest.qWait(1400)
            self.assertIsNotNone(measurement.engine.calibration.target_started_at)
            measurement.engine.calibration.target_index = 1
            measurement.engine.calibration.target_started_at = None
            measurement.calibration_guide = "up"
            measurement.stateChanged.emit()
            self.app.processEvents()
            self.assertIsNone(measurement.engine.calibration.target_started_at)
            QTest.qWait(1400)
            self.assertEqual(calibration_window.property("displayedTargetKey"), "up")
            self.assertIsNotNone(measurement.engine.calibration.target_started_at)

            manager = measurement.engine.calibration
            center_samples = [FrameObservation(timestamp=time.monotonic() - 1.0 + i * 0.05) for i in range(12)]
            manager.samples_by_target["center"] = center_samples
            manager.samples = list(center_samples)
            manager.valid_seconds_by_target["center"] = 2.0
            manager.completed_targets.add("center")
            manager.target_requested_at = time.monotonic() - 13.0
            measurement._check_calibration_timeout(time.monotonic())
            measurement.stateChanged.emit()
            self.app.processEvents()
            self.assertTrue(calibration_window.property("visible"))
            self.assertTrue(measurement.screenCalibrationFailed)
            retry = calibration_window.findChild(QObject, "retryCalibrationButton")
            self.assertTrue(retry.property("visible"))
            old_run = measurement.calibrationRunId
            self.assertTrue(QMetaObject.invokeMethod(retry, "clicked"))
            self.app.processEvents()
            self.assertGreater(measurement.calibrationRunId, old_run)
            self.assertEqual(measurement.calibrationGuide, "up")
            self.assertEqual(manager.samples_by_target["center"], center_samples)
            self.assertAlmostEqual(measurement.screenCalibrationProgress, 0.2)
            self.assertFalse(measurement.screenTargetDisplayed(old_run, 1, "up"))
            QTest.qWait(1400)
            self.assertEqual(calibration_window.property("displayedTargetKey"), "up")
            self.assertIsNotNone(manager.target_started_at)

            manager.target_requested_at = time.monotonic() - 13.0
            measurement._check_calibration_timeout(time.monotonic())
            measurement.stateChanged.emit()
            self.app.processEvents()
            cancel = calibration_window.findChild(QObject, "cancelCalibrationButton")
            self.assertTrue(QMetaObject.invokeMethod(cancel, "clicked"))
            self.app.processEvents()
            self.assertFalse(calibration_window.property("visible"))
            self.assertEqual(manager.status, CalibrationStatus.IDLE)
            self.assertEqual(manager.completed_targets, set())
            measurement.shutdown()
            window.close()
            self.app.processEvents()

    def test_optional_validation_uses_rendered_positions_and_opens_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = SettingsStore(root / "settings.json")
            database = SessionDatabase(root / "onf.sqlite3")
            provider = CameraImageProvider()
            image = QImage(640, 480, QImage.Format_RGB888)
            image.fill("#E3E8EF")
            provider.set_image(image)
            measurement = MeasurementBridge(provider, store, database, auto_start=False)
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera_connected = True
            measurement.raw_frame_size = (1280, 720)
            backend = AppBridge(database, store)
            engine = QQmlApplicationEngine()
            engine.addImageProvider("study-icons", StudyIconProvider())
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
            engine.addImageProvider("camera", provider)
            path = Path(__file__).parents[1] / "onf_v2/ui_qml/qml/Main.qml"
            engine.load(QUrl.fromLocalFile(str(path.resolve())))
            self.assertEqual(len(engine.rootObjects()), 1)
            window = engine.rootObjects()[0]
            window.setProperty("backendObject", backend)
            window.setProperty("measurementObject", measurement)
            window.setProperty("currentTabIndex", 1)
            calibration_window = window.findChild(QObject, "screenCalibrationWindow")
            calibration_window.findChild(QObject, "calibrationStagePromptTimer").setProperty("interval", 1)
            target = calibration_window.findChild(QObject, "calibrationTarget")
            acquisition = measurement.engine.calibration
            acquisition.samples_per_target = 3
            acquisition.target_settle_seconds = acquisition.target_valid_seconds = 0
            measurement.startCalibration("screen")
            for key in acquisition.guided_targets:
                for _ in range(40):
                    QTest.qWait(25)
                    if acquisition.target_started_at is not None:
                        break
                self.assertEqual(calibration_window.property("displayedTargetKey"), key)
                self.assertIsNotNone(acquisition.target_started_at, f"{key}: {warnings}")
                center = target.mapToScene(QPointF(target.width() / 2, target.height() / 2))
                expected = (center.x() / calibration_window.width(), center.y() / calibration_window.height())
                self.assertEqual(acquisition.target_positions[key], expected)
                measurement.calibration_message = "얼굴을 찾지 못했습니다. 조명을 밝히고 얼굴 전체와 양쪽 눈이 보이게 해주세요."
                measurement.stateChanged.emit()
                QTest.qWait(20)
                self.assertEqual(target.mapToScene(QPointF(target.width() / 2, target.height() / 2)), center)
                for frame in range(3):
                    measurement._update_calibration(gaze_observation(acquisition.target_started_at + 0.01 * frame, expected))
                measurement.stateChanged.emit()
            QTest.qWait(80)
            self.assertFalse(calibration_window.property("visible"))
            mapping = measurement.engine.screen_gaze_mapping
            self.assertIsNotNone(mapping)
            self.assertEqual(mapping.context.window_size, (calibration_window.width(), calibration_window.height()))
            self.assertEqual(measurement.gazeValidationRows, [])
            profile = acquisition.profile
            coefficients = mapping.coefficients
            validation = measurement.engine.gaze_validation
            validation.samples_per_target = 3
            validation.target_settle_seconds = validation.target_valid_seconds = 0
            button = window.findChild(QObject, "screenValidationButton")
            self.assertTrue(button.property("enabled"))
            self.assertTrue(QMetaObject.invokeMethod(button, "clicked"))
            self.assertEqual(measurement.calibrationTarget, "validation")
            self.assertFalse(measurement.startSession("free", -1, "", ""))
            capture_dir = os.environ.get("ONF_UI_CAPTURE_DIR")
            for key in validation.guided_targets:
                for _ in range(40):
                    QTest.qWait(25)
                    if validation.target_started_at is not None:
                        break
                self.assertTrue(calibration_window.property("visible"))
                self.assertIsNotNone(validation.target_started_at, f"{key}: {warnings}")
                point = validation.target_positions[key]
                for actual, expected in zip(point, mapping.validation_positions[key]):
                    self.assertAlmostEqual(actual, expected, delta=0.005)
                if key != "center":
                    self.assertNotEqual(point, acquisition.target_positions[key])
                if key == "center" and capture_dir:
                    Path(capture_dir).mkdir(parents=True, exist_ok=True)
                    self.assertTrue(calibration_window.grabWindow().save(str(Path(capture_dir) / "screen-gaze-validation-target.png")))
                closed = gaze_observation(validation.target_started_at, point)
                closed.left_eye_open_ratio = 0.01
                measurement._update_calibration(closed)
                for frame in range(3):
                    measurement._update_calibration(gaze_observation(validation.target_started_at + 0.01 * (frame + 1), point))
                measurement.stateChanged.emit()
            QTest.qWait(220)
            report = window.findChild(QObject, "gazeValidationReport")
            self.assertTrue(report.property("visible"))
            self.assertFalse(calibration_window.property("visible"))
            self.assertIs(acquisition.profile, profile)
            self.assertEqual(mapping.coefficients, coefficients)
            self.assertEqual(len(measurement.gazeValidationRows), 5)
            self.assertTrue(all(row["valid"] == 75 for row in measurement.gazeValidationRows))
            self.assertTrue(all(row["p90"] < 0.1 for row in measurement.gazeValidationRows))
            self.assertLess(report.property("height"), window.height())
            if capture_dir:
                self.assertTrue(window.grabWindow().save(str(Path(capture_dir) / "screen-gaze-validation-report.png")))
            self.assertFalse(warnings, "\n".join(sorted(set(warnings))))
            window.close()
            self.app.processEvents()

    def test_cancelled_validation_keeps_candidate_and_previous_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            measurement = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera_connected = True
            mapping = fit_screen_gaze(CONTEXT, samples_at(POSITIONS), POSITIONS)
            measurement.engine.screen_gaze_mapping = mapping
            previous_result = (object(),)
            measurement.engine.gaze_validation_result = previous_result
            measurement.engine.calibration.profile = object()
            measurement.engine.calibration.status = CalibrationStatus.READY
            self.assertTrue(measurement.startScreenValidation())
            run_id = measurement.calibrationRunId
            measurement.cancelCalibration()
            self.assertIs(measurement.engine.screen_gaze_mapping, mapping)
            self.assertIs(measurement.engine.gaze_validation_result, previous_result)
            self.assertTrue(measurement.screenReady)
            self.assertEqual(measurement.appState, "ready")
            self.assertFalse(measurement.screenTargetDisplayed(run_id, 0, "center"))

    def test_validation_rejects_a_different_display_without_replacing_posture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            measurement = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera_connected = True
            measurement.raw_frame_size = CONTEXT.frame_size
            measurement.engine.screen_gaze_mapping = fit_screen_gaze(CONTEXT, samples_at(POSITIONS), POSITIONS)
            profile = object()
            measurement.engine.calibration.profile = profile
            measurement.engine.calibration.status = CalibrationStatus.READY
            self.assertTrue(measurement.startScreenValidation())
            self.assertFalse(measurement.screenTargetDisplayed(measurement.calibrationRunId, 4, "right", {}))
            self.assertTrue(measurement.engine.gaze_validation.mapping_context_valid)
            display = {
                "u": 0.5, "v": 0.5, "screenName": "another monitor", "screenX": 0,
                "screenY": 0, "screenWidth": 1920, "screenHeight": 1080,
                "width": 1920, "height": 1080, "dpr": 1.25,
            }
            self.assertFalse(measurement.screenTargetDisplayed(measurement.calibrationRunId, 0, "center", display))
            self.assertEqual(measurement.calibrationTarget, "")
            self.assertTrue(measurement.screenCalibrationFailed)
            self.assertIs(measurement.engine.calibration.profile, profile)
            self.assertIn("다시 설정", measurement.calibrationMessage)

    def test_capture_resolution_change_invalidates_gaze_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            measurement = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera = Mock()
            measurement.camera_connected = True
            measurement.raw_frame_size = CONTEXT.frame_size
            measurement.engine.screen_gaze_mapping = fit_screen_gaze(CONTEXT, samples_at(POSITIONS), POSITIONS)
            profile = object()
            measurement.engine.calibration.profile = profile
            measurement.engine.calibration.status = CalibrationStatus.READY
            measurement.last_analysis_at = time.monotonic()
            measurement.camera.read.return_value = CameraFrame(
                True, time.monotonic(), frame=np.zeros((480, 640, 3), dtype=np.uint8), sequence=1,
            )
            generation = measurement.observation_generation
            measurement._tick()
            self.assertEqual(measurement.raw_frame_size, (640, 480))
            self.assertGreater(measurement.observation_generation, generation)
            self.assertIsNone(measurement.engine.screen_gaze_mapping)
            self.assertEqual(measurement.gazeValidationRows, [])
            self.assertIs(measurement.engine.calibration.profile, profile)

    def test_upper_target_live_collection_feedback_yellow_green_and_recovery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            measurement = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera_connected = True
            self.assertTrue(measurement.startCalibration("screen"))
            manager = measurement.engine.calibration
            manager.start(100.0)
            manager.target_index = 1
            engine = QQmlApplicationEngine()
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
            path = Path(__file__).parents[1] / "onf_v2/ui_qml/qml/components/ScreenCalibrationWindow.qml"
            engine.load(QUrl.fromLocalFile(str(path.resolve())))
            self.assertEqual(len(engine.rootObjects()), 1)
            window = engine.rootObjects()[0]
            self.addCleanup(lambda: [item.close() for item in engine.rootObjects()])
            window.setProperty("measurementObject", measurement)
            window.setProperty("pendingTargetKey", "up")
            window.setProperty("displayedTargetKey", "up")
            window.setProperty("pendingRunId", measurement.calibrationRunId)
            window.setProperty("pendingStageIndex", 1)
            window.setProperty("stagePromptVisible", False)
            measurement.calibration_guide = "up"
            window.setGeometry(0, 0, 1093, 614)
            window.show()
            target = window.findChild(QObject, "calibrationTarget")

            def check_feedback(color, stable, name):
                measurement.stateChanged.emit()
                QTest.qWait(220)
                self.assertEqual(measurement.screenTargetStable, stable)
                self.assertEqual(window.property("collectionStable"), stable)
                image = window.grabWindow()
                self.assertFalse(image.isNull())
                dot = target.mapToScene(QPointF(target.width() / 2, target.height() / 2))
                self.assertEqual(image.pixelColor(round(dot.x()), round(dot.y())).name(), color)
                directory = os.environ.get("ONF_UI_CAPTURE_DIR")
                if directory:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                    self.assertTrue(image.save(str(Path(directory) / f"upper-feedback-{name}.png")))

            check_feedback("#946311", False, "waiting")
            self.assertTrue(manager.confirm_target_displayed(100.0, 1, "up"))
            measurement._update_calibration(calibration_observation(102.1))
            check_feedback("#946311", False, "first-sample")
            measurement._update_calibration(calibration_observation(102.2))
            check_feedback("#16834b", True, "stable")
            self.assertIn("수집", window.findChild(QObject, "calibrationReason").property("text"))
            collected = manager.valid_seconds_by_target["up"]
            closed = calibration_observation(102.3)
            closed.left_eye_open_ratio = closed.right_eye_open_ratio = 0.02
            measurement._update_calibration(closed)
            check_feedback("#946311", False, "eyes-lost")
            self.assertIn("눈", window.findChild(QObject, "calibrationReason").property("text"))
            self.assertAlmostEqual(manager.valid_seconds_by_target["up"], collected)
            measurement._update_calibration(calibration_observation(102.4))
            self.assertFalse(measurement.screenTargetStable)
            measurement._update_calibration(calibration_observation(102.5))
            check_feedback("#16834b", True, "recovered")
            measurement._apply_calibration_progress(manager.check_timeout(103.1))
            check_feedback("#946311", False, "stalled")
            self.assertEqual(manager.target_valid_seconds, 2.0)
            self.assertEqual(manager.guided_targets, ("center", "up", "down", "left", "right"))
            self.assertFalse(measurement.engine.validating_gaze)
            self.assertEqual(warnings, [])
            measurement.cancelCalibration()

    def test_calibration_states_fit_logical_monitor_sizes_and_render(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            measurement = MeasurementBridge(
                CameraImageProvider(), SettingsStore(root / "settings.json"),
                SessionDatabase(root / "onf.sqlite3"), auto_start=False,
            )
            self.addCleanup(measurement.shutdown)
            measurement.timer.stop()
            measurement.analyzer = Mock()
            measurement.camera_connected = True
            measurement.startCalibration("screen")
            manager = measurement.engine.calibration
            engine = QQmlApplicationEngine()
            engine.addImageProvider("study-icons", StudyIconProvider())
            warnings = []
            engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
            qml_path = Path(__file__).parents[1] / "onf_v2/ui_qml/qml/components/ScreenCalibrationWindow.qml"
            engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))
            self.assertEqual(len(engine.rootObjects()), 1)
            window = engine.rootObjects()[0]
            window.setProperty("measurementObject", measurement)
            window.setProperty("stagePromptVisible", False)
            window.show()
            area = window.findChild(QObject, "calibrationTargetArea")
            target = window.findChild(QObject, "calibrationTarget")
            instruction = window.findChild(QObject, "calibrationInstruction")
            capture_dir = os.environ.get("ONF_UI_CAPTURE_DIR")
            if capture_dir:
                Path(capture_dir).mkdir(parents=True, exist_ok=True)
            sizes = ((1366, 768), (1093, 614), (911, 512), (1920, 1080), (1536, 864), (1280, 720))
            for width, height in sizes:
                window.setGeometry(-1920, -100, width, height)
                for state in ("collecting", "paused", "failed"):
                    for index, key in enumerate(manager.guided_targets):
                        with self.subTest(size=(width, height), state=state, key=key):
                            manager.target_index = index
                            manager.target_state = state
                            manager.collection_stable = state == "collecting"
                            manager.status = CalibrationStatus.FAILED if state == "failed" else CalibrationStatus.COLLECTING
                            manager.failed_targets = (key,) if state == "failed" else ()
                            manager.samples_by_target[key] = [FrameObservation(timestamp=i) for i in range(6)]
                            manager.valid_seconds_by_target[key] = 1.0
                            measurement.calibration_guide = key
                            measurement.calibration_message = (
                                "얼굴을 찾지 못했습니다. 조명을 밝히고 얼굴 전체와 양쪽 눈이 보이게 해주세요."
                                if state != "collecting" else "정상 표본을 수집하고 있습니다."
                            )
                            window.setProperty("pendingTargetKey", key)
                            window.setProperty("displayedTargetKey", key)
                            window.setProperty("pendingRunId", measurement.calibrationRunId)
                            window.setProperty("pendingStageIndex", index)
                            measurement.stateChanged.emit()
                            QTest.qWait(30)
                            self.assertFalse(window.property("stagePromptVisible"))
                            for item in (target, instruction):
                                self.assertGreaterEqual(item.x(), -0.5)
                                self.assertGreaterEqual(item.y(), -0.5)
                                self.assertLessEqual(item.x() + item.width(), area.width() + 0.5)
                                self.assertLessEqual(item.y() + item.height(), area.height() + 0.5)
                            self.assertTrue(
                                instruction.y() + instruction.height() <= target.y()
                                or instruction.y() >= target.y() + target.height()
                            )
                            if index == 0:
                                QTest.qWait(220)
                                image = window.grabWindow()
                                self.assertFalse(image.isNull())
                                self.assertEqual(image.width(), width)
                                self.assertEqual(image.height(), height)
                                dot = target.mapToScene(QPointF(target.width() / 2, target.height() / 2))
                                self.assertEqual(
                                    image.pixelColor(round(dot.x()), round(dot.y())).name(),
                                    {"collecting": "#16834b", "paused": "#946311", "failed": "#c3424e"}[state],
                                )
                                if capture_dir:
                                    self.assertTrue(image.save(str(Path(capture_dir) / f"calibration-{width}x{height}-{state}.png")))
            self.assertEqual(warnings, [])
            measurement.cancelCalibration()
            window.close()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
