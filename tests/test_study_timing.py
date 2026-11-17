import os
import tempfile
import unittest
from concurrent.futures import Future
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QDateTime, QMetaObject, QObject, QPointF, Qt, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QImage
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression, qmlContext
from onf_v2.ui_qml.study_appearance import StudyIconProvider
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from onf_v2.app.camera_service import CameraFrame
from onf_v2.app.pomodoro import PomodoroPhase
from onf_v2.app.session_database import SessionDatabase
from onf_v2.app.settings_store import SettingsStore
from onf_v2.core.metrics import DurationAccumulator, study_seconds
from onf_v2.core.models import EffectiveState, FocusDecision, ObservationState, SessionSummary
from onf_v2.ui_qml.app_bridge import AppBridge
from onf_v2.ui_qml.measurement_bridge import CameraImageProvider, MeasurementBridge


class StudyTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("malgun.ttf", "seguisym.ttf", "segoeui.ttf"):
            font_path = font_directory / name
            if font_path.exists():
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                families = QFontDatabase.applicationFontFamilies(font_id)
                if name == "malgun.ttf" and families:
                    cls.app.setFont(QFont(families[0]))

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = SessionDatabase(self.root / "onf.sqlite3")
        self.store = SettingsStore(self.root / "settings.json")
        self.measurement = MeasurementBridge(
            CameraImageProvider(), self.store, self.database, auto_start=False
        )
        self.measurement.timer.stop()
        self.measurement.app_usage_tracker = Mock()
        self.measurement.app_usage_tracker.finish.return_value = {}
        self.now = 100.0
        self.wall_start = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        clock = patch(
            "onf_v2.ui_qml.measurement_bridge.time.monotonic", side_effect=lambda: self.now
        )
        clock.start()
        self.addCleanup(clock.stop)
        ready = patch.object(
            type(self.measurement.engine), "ready_for_session",
            new_callable=PropertyMock, return_value=True,
        )
        ready.start()
        self.addCleanup(ready.stop)
        wall_now = patch.object(
            self.measurement.session.recorder, "wall_now",
            side_effect=lambda: (self.wall_start + timedelta(seconds=self.now - 100)).isoformat(sep=" "),
        )
        wall_now.start()
        self.addCleanup(wall_now.stop)
        for module in ("measurement_bridge", "app_bridge"):
            wall_clock = patch(f"onf_v2.ui_qml.{module}.datetime", wraps=datetime)
            mocked = wall_clock.start()
            mocked.now.side_effect = lambda: self.wall_start + timedelta(seconds=self.now - 100)
            self.addCleanup(wall_clock.stop)
        self.measurement.camera_connected = True
        self.addCleanup(self.measurement.shutdown)

    def test_state_totals_define_study_and_keep_scoring_denominators(self):
        metrics = DurationAccumulator()
        metrics.update(EffectiveState.FOCUS, 0)
        metrics.update(EffectiveState.NON_FOCUS, 1800)
        metrics.update(EffectiveState.UNSCORED, 2400)
        metrics.update(EffectiveState.BREAK, 3000)
        metrics.update(EffectiveState.BREAK, 3600)

        self.assertEqual(study_seconds(metrics.snapshot()), 3000)
        self.assertEqual(metrics.durations[EffectiveState.FOCUS], 1800)
        self.assertEqual(metrics.focus_ratio(), 0.75)
        self.assertEqual(metrics.coverage_ratio(), 0.8)

    def test_live_snapshot_and_minute_projection_do_not_modify_recorded_time(self):
        metrics = DurationAccumulator()
        metrics.update(EffectiveState.FOCUS, 0)
        metrics.update(EffectiveState.BREAK, 50)
        snapshot = metrics.snapshot(70)

        self.assertEqual(study_seconds(snapshot), 50)
        self.assertEqual(snapshot[EffectiveState.BREAK], 20)
        self.assertEqual([sum(bucket.values()) for bucket in metrics.minute_snapshot(snapshot)], [60, 10])
        self.assertEqual(sum(metrics.durations.values()), 50)
        self.assertEqual(sum(sum(bucket.values()) for bucket in metrics.minute_buckets), 50)
        self.assertEqual(study_seconds(DurationAccumulator().snapshot(120, 100)), 20)

    def test_free_study_rest_resume_end_and_today_save_do_not_double_count(self):
        measurement = self.measurement
        backend = AppBridge(self.database, self.store)
        measurement.recordsChanged.connect(backend.refresh)
        self.assertTrue(measurement.startSession("free", -1, "", ""))
        self.now = 120
        self.assertEqual(measurement.elapsedSeconds, 20)
        measurement.toggleBreak()
        self.now = 180
        self.assertEqual(measurement.elapsedSeconds, 20)
        self.assertEqual(measurement.breakRemainingSeconds, 240)
        self.assertIn("\ud734\uc2dd \uc2dc\uac04", measurement.statusDetail)
        self.assertNotIn("\ubd88\uc548\uc815", measurement.statusDetail)
        measurement.toggleBreak()
        self.now = 200
        measurement.toggleBreak()
        self.now = 230
        self.assertEqual(measurement.elapsedSeconds, 40)
        self.assertEqual(backend.todayStudySeconds + measurement.todayStudySeconds, 40)
        measurement.endSession()
        self.assertEqual(measurement.elapsedSeconds, 40)
        self.assertEqual(measurement.todayStudySeconds, 0)
        self.assertEqual(backend.todayStudySeconds, 40)
        self.assertEqual(measurement.session.summary.break_seconds, 90)

        self.now = 300
        self.assertTrue(measurement.startSession("free", -1, "", ""))
        self.assertEqual(measurement.elapsedSeconds, 0)
        self.assertEqual(measurement.breakRemainingSeconds, 0)
        self.now = 315
        self.assertEqual(backend.todayStudySeconds + measurement.todayStudySeconds, 55)
        measurement.endSession()
        measurement.endSession()
        self.now = 500
        self.assertEqual(measurement.elapsedSeconds, 15)
        self.assertEqual(backend.todayStudySeconds, 55)
        self.assertEqual(len(self.database.list_sessions()), 2)

    def test_camera_and_analysis_failure_do_not_stop_study_or_invent_focus(self):
        measurement = self.measurement
        measurement.camera = Mock()
        measurement.camera.read.return_value = CameraFrame(False, 110, error="lost")
        self.assertTrue(measurement.startSession("free", -1, "", ""))
        self.now = 101
        measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
        ))
        self.now = 110
        self.assertEqual(measurement.durations["focus"], 2)
        self.assertEqual(measurement.elapsedSeconds, 10)
        measurement._tick()
        self.now = 120
        measurement._tick()
        self.assertEqual(measurement.elapsedSeconds, 20)
        self.assertEqual(measurement.durations["focus"], 2)
        self.assertEqual(measurement.durations["unscored"], 18)
        self.assertEqual(measurement.coveragePercent, 10)
        self.assertEqual(measurement.focusPercent, 100)
        measurement._record_unavailable(ObservationState.PROCESSING_ERROR, self.now)
        self.now = 125
        measurement.endSession()
        self.assertEqual(measurement.elapsedSeconds, 25)
        self.assertEqual(measurement.session.summary.focus_seconds, 2)
        self.assertEqual(measurement.session.summary.unscored_seconds, 23)

    def test_pomodoro_break_waiting_manual_pause_and_completion_share_clock(self):
        measurement = self.measurement
        measurement.settings.pomodoro_focus_minutes = 1
        measurement.settings.pomodoro_short_break_minutes = 1
        measurement.settings.pomodoro_long_break_minutes = 2
        measurement.settings.pomodoro_cycles = 2
        self.assertTrue(measurement.startSession("pomodoro", -1, "", ""))
        self.now = 160
        measurement._update_pomodoro(self.now)
        self.assertTrue(measurement.sessionPaused)
        self.now = 190
        self.assertEqual(measurement.elapsedSeconds, 60)
        self.assertEqual(measurement.breakRemainingSeconds, 30)
        self.now = 220
        measurement._update_pomodoro(self.now)
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.WAITING_NEXT)
        self.now = 230
        measurement.toggleBreak()
        self.assertFalse(measurement.sessionPaused)
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.FOCUS)
        self.now = 250
        measurement.toggleBreak()
        self.now = 300
        self.assertEqual(measurement.elapsedSeconds, 80)
        self.assertEqual(measurement.pomodoroRemainingSeconds, 40)
        measurement.toggleBreak()
        self.now = 340
        measurement._update_pomodoro(self.now)
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.LONG_BREAK)
        self.assertEqual(measurement.elapsedSeconds, 120)
        self.now = 460
        measurement._update_pomodoro(self.now)
        self.assertFalse(measurement.sessionRunning)
        self.assertEqual(measurement.elapsedSeconds, 120)
        self.assertEqual(measurement.pomodoroRemainingSeconds, 0)
        self.assertEqual(measurement.session.summary.break_seconds, 240)

    def test_today_total_matches_saved_record_across_study_day_boundary(self):
        self.wall_start = self.wall_start.replace(hour=3, minute=59, second=30)
        measurement = self.measurement
        self.assertTrue(measurement.startSession("free", -1, "", ""))
        self.now = 160
        measurement.toggleBreak()
        self.now = 190
        self.assertEqual(measurement.elapsedSeconds, 60)
        self.assertEqual(measurement.todayStudySeconds, 30)
        measurement.endSession()
        backend = AppBridge(self.database, self.store)
        self.assertEqual(backend.todayStudySeconds, 30)

    def test_today_focus_keeps_day_boundary_and_saved_live_handoff(self):
        self.wall_start = self.wall_start.replace(hour=3, minute=59, second=30)
        backend = AppBridge(self.database, self.store)
        self.measurement.recordsChanged.connect(backend.refresh)
        self.assertTrue(self.measurement.startSession("free", -1, "", ""))
        self.measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
        ))
        self.now = 160
        backend.refreshToday()
        self.measurement.toggleBreak()
        self.now = 190
        self.assertEqual(self.measurement.todayFocusSeconds, 30)
        self.assertEqual(backend.todayFocusSeconds, 0)
        self.measurement.endSession()
        self.assertEqual(self.measurement.todayFocusSeconds, 0)
        self.assertEqual(backend.todayFocusSeconds, 30)
        self.assertEqual(backend.todayStudySeconds, 30)
        backend.saveStudyRecord(-1, -1, -1, "Offline", 0, 10)
        self.assertEqual(backend.todayFocusSeconds, 30)

    def test_pomodoro_waits_for_manual_break_start_without_counting_study(self):
        measurement = self.measurement
        measurement.settings.pomodoro_focus_minutes = 1
        measurement.settings.pomodoro_short_break_minutes = 1
        measurement.settings.pomodoro_cycles = 2
        measurement.settings.pomodoro_auto_start_break = False
        self.assertTrue(measurement.startSession("pomodoro", -1, "", ""))
        self.now = 160
        measurement._update_pomodoro(self.now)
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.WAITING_NEXT)
        self.now = 180
        measurement.toggleBreak()
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.SHORT_BREAK)
        self.now = 190
        self.assertEqual(measurement.elapsedSeconds, 60)
        self.assertEqual(measurement.breakRemainingSeconds, 50)
        self.now = 240
        measurement._update_pomodoro(self.now)
        self.now = 250
        measurement.toggleBreak()
        self.assertFalse(measurement.sessionPaused)
        self.now = 270
        measurement.endSession()
        self.assertEqual(measurement.elapsedSeconds, 80)
        self.assertEqual(measurement.session.summary.break_seconds, 90)

    def test_record_and_planner_totals_include_unscored_but_not_breaks(self):
        task = self.database.add_planner_task(
            "study", None, self.wall_start.date().isoformat(), None, 0, "study"
        )
        self.database.add_session(SessionSummary(
            started_at_wall=self.wall_start.isoformat(sep=" "),
            ended_at_wall=(self.wall_start + timedelta(hours=1)).isoformat(sep=" "),
            focus_seconds=1800, non_focus_seconds=600, unscored_seconds=600,
            break_seconds=600, absent_pending_seconds=0, focus_ratio=0.75,
            coverage_ratio=0.8, longest_focus_seconds=1800, events=[],
        ), self.root / "example", task_id=task)
        backend = AppBridge(self.database, self.store)
        self.assertEqual(backend.todayStudySeconds, 3000)
        self.assertEqual(backend.dailySummary["study"], "50\ubd84")
        self.assertEqual(backend.dailySummary["ratio"], 75)
        self.assertEqual(sum(row["study"] for row in backend.weeklyRecords), 50)
        self.assertEqual(next(row["focus"] for row in backend.weeklyRecords if row["study"]), 75)
        self.assertEqual(backend.monthlySummary["study"], "50\ubd84")
        self.assertEqual(backend.monthlySummary["ratio"], 75)
        self.assertEqual(self.database.list_planner_tasks()[0].actual_study_seconds, 3000)
        self.assertEqual(self.database.list_planner_tasks()[0].actual_focus_seconds, 1800)

    def test_qml_timer_uses_measurement_time_and_preserves_final_value(self):
        measurement = self.measurement
        backend = AppBridge(self.database, self.store)
        engine = QQmlApplicationEngine()
        engine.addImageProvider("study-icons", StudyIconProvider())
        frame = QImage(640, 480, QImage.Format_RGB32)
        frame.fill(0xffe5e7eb)
        measurement.image_provider.set_image(frame)
        engine.addImageProvider("camera", measurement.image_provider)
        self.addCleanup(lambda: [window.close() for window in engine.rootObjects()])
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        engine.load(QUrl.fromLocalFile(str(
            Path(__file__).parents[1] / "onf_v2/ui_qml/qml/Main.qml"
        )))
        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        window.setProperty("backendObject", backend)
        window.setProperty("measurementObject", measurement)
        window.setProperty("pomodoroMode", False)
        self.assertTrue(measurement.startSession("free", -1, "", ""))
        self.now = 142
        measurement.stateChanged.emit()
        QTest.qWait(1100)
        self.assertEqual(window.property("elapsedSeconds"), 42)
        value = window.findChild(QObject, "studyTimeValue")
        self.assertEqual(value.property("text"), "00:00:42")
        self._capture(window, "study-running")
        self.now = 162
        measurement.toggleBreak()
        self.now = 210
        measurement.stateChanged.emit()
        QTest.qWait(1100)
        self.assertEqual(value.property("text"), "00:01:02")
        self.assertEqual(window.property("todayStudySeconds"), 62)
        rest_value = window.findChild(QObject, "studyBreakRemainingValue")
        self.assertTrue(rest_value.property("visible"))
        self.assertEqual(rest_value.property("text"), "04:12")
        self._capture(window, "study-break")
        measurement.endSession()
        self.app.processEvents()
        self.assertEqual(value.property("text"), "00:01:02")
        self.assertEqual(window.property("todayStudySeconds"), 62)
        self.assertFalse(rest_value.property("visible"))
        self.assertIn("\ud559\uc2b5 \uc885\ub8cc", window.findChild(QObject, "sessionStatusLabel").property("text"))
        self._capture(window, "study-ended")
        self.now = 300
        measurement.startSession("free", -1, "", "")
        self.app.processEvents()
        self.assertEqual(value.property("text"), "00:00:00")
        self.assertEqual(window.property("todayStudySeconds"), 62)
        self.assertEqual(warnings, [])
        measurement.endSession()

    def test_weekly_average_uses_scored_seconds_not_study_minutes(self):
        start = self.wall_start - timedelta(days=(self.wall_start.weekday() + 1) % 7)
        for offset, (focus, non_focus, unscored) in enumerate(((600, 0, 5400), (0, 600, 0))):
            moment = start + timedelta(days=offset)
            self.database.add_session(SessionSummary(
                started_at_wall=moment.isoformat(sep=" "),
                ended_at_wall=(moment + timedelta(seconds=focus + non_focus + unscored)).isoformat(sep=" "),
                focus_seconds=focus, non_focus_seconds=non_focus,
                unscored_seconds=unscored, break_seconds=0, absent_pending_seconds=0,
                focus_ratio=focus / (focus + non_focus),
                coverage_ratio=(focus + non_focus) / (focus + non_focus + unscored),
                longest_focus_seconds=focus, events=[],
            ), self.root / str(offset))
        backend = AppBridge(self.database, self.store)
        backend._records_date = start.date()
        backend.refresh()
        engine = QQmlApplicationEngine()
        engine.addImageProvider("study-icons", StudyIconProvider())
        self.addCleanup(lambda: [window.close() for window in engine.rootObjects()])
        engine.load(QUrl.fromLocalFile(str(
            Path(__file__).parents[1] / "onf_v2/ui_qml/qml/Main.qml"
        )))
        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        window.setProperty("backendObject", backend)
        window.setProperty("currentTabIndex", 3)
        self.app.processEvents()
        label = window.findChild(QObject, "recordsSummaryLabel")
        self.assertIn("50%", label.property("text"))
        self.assertEqual(sum(row["study"] for row in backend.weeklyRecords), 110)

    def test_active_free_study_rest_navigation_end_and_restart(self):
        window, backend, warnings = self._study_window("free")
        window.setProperty("currentTabIndex", 4)
        self.assertTrue(QMetaObject.invokeMethod(window, "startStudySession"))
        self.app.processEvents()
        self.assertEqual(window.property("currentTabIndex"), 0)
        self.assertEqual(window.property("studyViewState"), "study")
        self.assertFalse(window.findChild(QObject, "studyModeSelector").property("visible"))
        self.assertEqual(window.findChild(QObject, "studyPrimaryAction").property("text"), "\ud734\uc2dd")
        self.assertTrue(window.findChild(QObject, "studyEndAction").property("visible"))
        self.assertFalse(window.findChild(QObject, "appFeedbackOverlay").property("visible"))
        self.assertIsNone(self.measurement.session.task_id)

        self.measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
        ))
        self.now = 120
        self.measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
        ))
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        for name in ("todayStudyTimeValue", "studyTimeValue", "studyFocusTimeValue"):
            self.assertEqual(window.findChild(QObject, name).property("text"), "00:00:20")
        for index in (1, 2, 3, 4, 0):
            window.setProperty("currentTabIndex", index)
            self.app.processEvents()
            self.assertTrue(self.measurement.sessionRunning)
            self.assertEqual(window.property("elapsedSeconds"), 20)

        self._click_study_item(window, "studyPrimaryAction")
        self.now = 150
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(window.property("studyViewState"), "break")
        self.assertEqual(window.property("elapsedSeconds"), 20)
        self.assertEqual(window.property("todayStudySeconds"), 20)
        self.assertEqual(window.findChild(QObject, "studyPrimaryAction").property("text"), "\ud559\uc2b5 \uc7ac\uac1c")
        self.assertEqual(window.findChild(QObject, "studyBreakRemainingValue").property("text"), "04:30")
        self._click_study_item(window, "studyPrimaryAction")
        self.now = 170
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(window.property("elapsedSeconds"), 40)
        self._click_study_item(window, "studyEndAction")
        self.assertEqual(window.property("studyViewState"), "result")
        self.assertEqual(window.property("elapsedSeconds"), 40)
        self.assertEqual(backend.todayStudySeconds, 40)
        self.assertFalse(window.findChild(QObject, "studyEndAction").property("visible"))
        self.assertFalse(window.findChild(QObject, "studyModeSelector").property("visible"))
        self.now = 250
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(window.findChild(QObject, "studyTimeValue").property("text"), "00:00:40")
        self._click_study_item(window, "studyPrimaryAction")
        self.assertTrue(window.findChild(QObject, "preparationView").property("visible"))
        self._click_study_item(window, "studyPrimaryAction")
        self.assertEqual(window.property("elapsedSeconds"), 0)
        self.assertEqual(window.property("todayStudySeconds"), 40)
        self.assertEqual(window.findChild(QObject, "studyFocusTimeValue").property("text"), "00:00:00")
        self.assertEqual(warnings, [])

    def test_rejected_start_does_not_enter_active_study(self):
        window, _, warnings = self._study_window("free")
        self.measurement.camera_connected = False
        self.measurement.stateChanged.emit()
        self.assertTrue(QMetaObject.invokeMethod(window, "startStudySession"))
        self.app.processEvents()
        self.assertFalse(self.measurement.sessionRunning)
        self.assertFalse(window.property("sessionRunning"))
        self.assertEqual(window.property("studyViewState"), "ready")
        self.assertEqual(window.property("currentTabIndex"), 1)
        self.assertEqual(self.database.list_sessions(), [])
        self.assertEqual(warnings, [])

    def test_repeated_start_preserves_active_session_and_pomodoro(self):
        measurement = self.measurement
        for mode, other_mode in (("free", "pomodoro"), ("pomodoro", "free")):
            with self.subTest(mode=mode):
                self.assertTrue(measurement.startSession(mode, -1, "", ""))
                directory = measurement.session.recorder.session_dir
                started_at = measurement.session_started_at
                phase = measurement.pomodoro.phase
                self.now += 20
                self.assertFalse(measurement.startSession(other_mode, -1, "", ""))
                self.assertEqual(measurement.session.recorder.session_dir, directory)
                self.assertEqual(measurement.session_started_at, started_at)
                self.assertEqual(measurement.session.session_mode, mode)
                self.assertEqual(measurement.pomodoro.phase, phase)
                self.assertEqual(measurement.elapsedSeconds, 20)
                measurement.endSession()
                self.now += 10

    def test_pomodoro_break_action_at_deadline_does_not_pause_zero_time_phase(self):
        measurement = self.measurement
        measurement.settings.pomodoro_focus_minutes = 1
        measurement.settings.pomodoro_short_break_minutes = 1
        measurement.settings.pomodoro_long_break_minutes = 1
        measurement.settings.pomodoro_cycles = 2
        self.assertTrue(measurement.startSession("pomodoro", -1, "", ""))
        self.now = 160
        measurement.toggleBreak()
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.SHORT_BREAK)
        self.assertEqual(measurement.pomodoroRemainingSeconds, 60)
        self.assertEqual(measurement.pomodoro.completed_cycles, 1)
        self.assertEqual(measurement.elapsedSeconds, 60)
        self.now = 220
        measurement.toggleBreak()
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.WAITING_NEXT)
        self.now = 225
        measurement.toggleBreak()
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.FOCUS)
        self.now = 285
        measurement.toggleBreak()
        self.assertEqual(measurement.pomodoro.phase, PomodoroPhase.LONG_BREAK)
        self.now = 345
        measurement.toggleBreak()
        self.assertFalse(measurement.sessionRunning)
        self.assertEqual(measurement.elapsedSeconds, 120)
        self.assertEqual(measurement.session.summary.pomodoro_cycles_completed, 2)
        self.assertEqual(len(self.database.list_sessions()), 1)
        measurement.endSession()
        self.assertEqual(len(self.database.list_sessions()), 1)

    def test_pomodoro_settings_and_hidden_preview_preserve_active_round(self):
        window, backend, warnings = self._study_window("pomodoro")
        window.setProperty("focusMinutes", 2)
        window.setProperty("breakMinutes", 1)
        window.setProperty("targetRounds", 2)
        self._click_study_item(window, "studyPrimaryAction")
        self.assertEqual(self.measurement.pomodoro.config.focus_minutes, 2)
        self.assertEqual(self.measurement.pomodoro.config.short_break_minutes, 1)
        self.assertEqual(self.store.load().pomodoro_cycles, 2)
        self.now = 130
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(window.property("pomodoroSeconds"), 90)
        ring = window.findChild(QObject, "pomodoroRing")
        self.assertAlmostEqual(ring.property("progress"), 0.25)
        footprint = self._camera_footprint(window)
        self._click_study_item(window, "studyCameraToggle")
        self.assertFalse(window.property("cameraVisible"))
        self.assertTrue(self.measurement.cameraConnected)
        self.assertEqual(self._camera_footprint(window), footprint)
        self.assertEqual(window.property("pomodoroSeconds"), 90)
        backend.saveSettings({"pomodoro_focus_minutes": 30, "pomodoro_cycles": 6, "session_mode": "free"})
        self.measurement.reloadSettings()
        self.app.processEvents()
        self.assertTrue(window.property("pomodoroMode"))
        self.assertEqual(window.property("focusMinutes"), 2)
        self.assertEqual(window.property("targetRounds"), 2)
        self.assertEqual(window.property("pomodoroSeconds"), 90)
        self.assertEqual(self.measurement.pomodoro.config.focus_minutes, 2)
        self._click_study_item(window, "studyEndAction")
        self.assertFalse(window.property("pomodoroMode"))
        self.assertEqual(window.property("focusMinutes"), 30)
        self.assertEqual(window.property("targetRounds"), 6)
        self.assertEqual(warnings, [])

    def test_rest_navigation_and_end_from_measurement_preserve_result(self):
        window, backend, warnings = self._study_window("free")
        for mode in ("free", "pomodoro"):
            with self.subTest(mode=mode):
                window.setProperty("pomodoroMode", mode == "pomodoro")
                if window.property("sessionEnded"):
                    self._click_study_item(window, "studyPrimaryAction")
                self._click_study_item(window, "studyPrimaryAction")
                self.now += 20
                self.measurement.stateChanged.emit()
                self._click_study_item(window, "studyPrimaryAction")
                self.now += 30
                for index in (1, 2, 3, 4, 0):
                    self._click_study_item(window, f"navigationButton{index}")
                    self.measurement.stateChanged.emit()
                    self.app.processEvents()
                    self.assertEqual(window.property("currentTabIndex"), index)
                    self.assertEqual(window.property("studyViewState"), "break")
                    self.assertEqual(window.property("elapsedSeconds"), 20)
                    self.assertTrue(self.measurement.sessionPaused)
                self._click_study_item(window, "navigationButton1")
                self._click_study_item(window, "measurementEndAction")
                self.assertEqual(window.property("currentTabIndex"), 1)
                self.assertFalse(self.measurement.sessionRunning)
                self.assertFalse(self._study_item(window, "measurementEndAction").property("enabled"))
                self.assertEqual(self.measurement.session.summary.break_seconds, 30)
                self._click_study_item(window, "navigationButton0")
                self.assertEqual(window.property("studyViewState"), "result")
                self.assertEqual(window.property("elapsedSeconds"), 20)
                self._click_study_item(window, "studyPrimaryAction")
                self._click_study_item(window, "studyPrimaryAction")
                self.assertEqual(window.property("studyViewState"), "study")
                self.assertEqual(window.property("elapsedSeconds"), 0)
                self.measurement.endSession()
                self.assertEqual(warnings, [])
                self.now += 10

    def test_repeated_qml_start_and_native_double_click_preserve_study(self):
        window, backend, warnings = self._study_window("free")
        item = self._study_item(window, "studyPrimaryAction")
        point = item.mapToScene(QPointF(item.property("width") / 2, item.property("height") / 2)).toPoint()
        QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, point)
        self.app.processEvents()
        self.assertTrue(self.measurement.sessionRunning)
        self.assertFalse(self.measurement.sessionPaused)
        directory = self.measurement.session.recorder.session_dir
        self.now += 20
        self.measurement.stateChanged.emit()
        self._click_study_item(window, "navigationButton3")
        self.assertTrue(QMetaObject.invokeMethod(window, "startStudySession"))
        self.assertEqual(window.property("currentTabIndex"), 3)
        self.assertEqual(window.property("elapsedSeconds"), 20)
        self._click_study_item(window, "navigationButton0")
        item = self._study_item(window, "studyPrimaryAction")
        point = item.mapToScene(QPointF(item.property("width") / 2, item.property("height") / 2)).toPoint()
        QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, point)
        self.app.processEvents()
        self.assertTrue(self.measurement.sessionRunning)
        self.assertTrue(self.measurement.sessionPaused)
        self.assertEqual(self.measurement.session.recorder.session_dir, directory)
        self.assertEqual(warnings, [])

        item.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Space)
        self.assertFalse(self.measurement.sessionPaused)
        QTest.keyClick(window, Qt.Key_Space)
        self.assertTrue(self.measurement.sessionPaused)
        self.assertEqual(self.measurement.session.recorder.session_dir, directory)

    def test_measurement_break_button_matches_pomodoro_phase(self):
        window, backend, warnings = self._study_window("pomodoro")
        window.setProperty("focusMinutes", 1)
        window.setProperty("breakMinutes", 1)
        window.setProperty("targetRounds", 2)
        self._click_study_item(window, "studyPrimaryAction")
        self._click_study_item(window, "navigationButton1")
        self.now = 160
        self.measurement._update_pomodoro(self.now)
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        button = self._study_item(window, "measurementBreakAction")
        self.assertEqual(button.property("text"), "\ud734\uc2dd \uc77c\uc2dc\uc815\uc9c0")
        self._click_study_item(window, "measurementBreakAction")
        self.assertEqual(button.property("text"), "\ud734\uc2dd \uc7ac\uac1c")
        self.now = 180
        self._click_study_item(window, "measurementBreakAction")
        self.now = 240
        self.measurement._update_pomodoro(self.now)
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(button.property("text"), "\ub2e4\uc74c \ud559\uc2b5 \uc2dc\uc791")
        self.assertEqual(self.measurement.elapsedSeconds, 60)
        self.assertEqual(warnings, [])

    def test_app_quit_saves_study_and_rest_once_in_both_modes(self):
        from onf_v2.ui_qml import preview

        for index, (mode, resting) in enumerate((("free", False), ("free", True), ("pomodoro", False), ("pomodoro", True))):
            with self.subTest(mode=mode, resting=resting):
                measurement = MeasurementBridge(CameraImageProvider(), self.store, self.database, auto_start=False)
                measurement.timer.stop()
                self.addCleanup(measurement.shutdown)
                measurement.camera = Mock()
                measurement.camera_connected = True
                measurement.app_usage_tracker = Mock()
                measurement.app_usage_tracker.finish.return_value = {}
                self.now = 100 + index * 100
                self.assertTrue(measurement.startSession(mode, -1, "", ""))
                self.now += 20
                if resting:
                    measurement.toggleBreak()
                    self.now += 30
                app = Mock()
                app.exec.side_effect = lambda: app.aboutToQuit.connect.call_args.args[0]() or 0
                engine = Mock()
                engine.rootObjects.return_value = [Mock()]
                with patch.object(preview, "QGuiApplication", return_value=app), patch.object(preview, "QQmlApplicationEngine", return_value=engine), patch.object(preview, "AppBridge", return_value=AppBridge(self.database, self.store)), patch.object(preview, "MeasurementBridge", return_value=measurement):
                    self.assertEqual(preview.run(), 0)
                self.assertFalse(measurement.sessionRunning)
                self.assertFalse(measurement.timer.isActive())
                self.assertEqual(measurement.elapsedSeconds, 20)
                self.assertEqual(measurement.session.summary.break_seconds, 30 if resting else 0)
                directory = measurement.session.recorder.session_dir
                for name in ("observations.csv", "events.csv", "summary.json", "result.png"):
                    self.assertTrue((directory / name).is_file(), name)
                measurement.shutdown()
                measurement.endSession()
                self.assertFalse(measurement.startSession("free", -1, "", ""))
                measurement.camera.release.assert_called_once()
                self.assertEqual(len(self.database.list_sessions()), index + 1)

    def test_shutdown_closes_model_after_running_analysis_finishes(self):
        measurement = self.measurement
        measurement.analyzer = Mock()
        analyzer = measurement.analyzer
        pending = Future()
        pending.set_running_or_notify_cancel()
        measurement.analysis_future = pending
        measurement.shutdown()
        analyzer.close.assert_not_called()
        pending.set_result(None)
        analyzer.close.assert_called_once()

    def test_shutdown_releases_resources_from_late_setup(self):
        measurement = self.measurement
        measurement.camera = Mock()
        pending = Future()
        pending.set_running_or_notify_cancel()
        measurement.setup_future = pending
        measurement.shutdown()
        analyzer = Mock()
        pending.set_result((True, analyzer, ""))
        analyzer.close.assert_called_once()
        self.assertEqual(measurement.camera.release.call_count, 2)

    def test_shutdown_releases_late_camera_open(self):
        measurement = self.measurement
        measurement.camera = Mock()
        pending = Future()
        pending.set_running_or_notify_cancel()
        measurement.camera_future = pending
        measurement.shutdown()
        measurement.camera.release.assert_called_once()
        pending.set_result(True)
        self.assertEqual(measurement.camera.release.call_count, 2)

    def test_shutdown_cancels_queued_work_and_ignores_late_ticks(self):
        measurement = self.measurement
        measurement.camera = Mock()
        measurement.setup_future = Future()
        measurement.camera_future = Future()
        measurement.analysis_future = Future()
        measurement.shutdown()
        for pending in (measurement.setup_future, measurement.camera_future, measurement.analysis_future):
            self.assertTrue(pending.cancelled())
        measurement._tick()
        measurement.camera.read.assert_not_called()
        measurement.camera.release.assert_called_once()

    def test_pomodoro_actions_and_ring_use_current_phase_and_keep_progress_on_resume(self):
        window, backend, warnings = self._study_window("pomodoro")
        backend.saveSettings({"pomodoro_long_break_minutes": 3})
        window.setProperty("focusMinutes", 2)
        window.setProperty("breakMinutes", 1)
        window.setProperty("targetRounds", 2)
        self._click_study_item(window, "studyPrimaryAction")
        ring = window.findChild(QObject, "pomodoroRing")
        action = window.findChild(QObject, "studyPrimaryAction")
        self.now = 190
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertAlmostEqual(ring.property("progress"), 0.75)
        QTest.qWait(25)
        ring_size = (ring.property("width"), ring.property("height"))
        self._click_study_item(window, "studyPrimaryAction")
        self.now = 250
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(window.property("elapsedSeconds"), 90)
        self.assertEqual(window.property("pomodoroSeconds"), 30)
        self.assertTrue(window.findChild(QObject, "studyBreakRemainingValue").property("visible"))
        self.assertEqual(action.property("text"), "\ud559\uc2b5 \uc7ac\uac1c")
        QTest.qWait(25)
        self.assertEqual((ring.property("width"), ring.property("height")), ring_size)
        self._click_study_item(window, "studyPrimaryAction")
        self.assertAlmostEqual(ring.property("progress"), 0.75)
        self.now = 280
        self.measurement._update_pomodoro(self.now)
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(action.property("text"), "\ud734\uc2dd \uc77c\uc2dc\uc815\uc9c0")
        self.assertEqual(window.property("pomodoroSeconds"), 60)
        self.assertAlmostEqual(ring.property("progress"), 0)
        self.now = 310
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertAlmostEqual(ring.property("progress"), 0.5)
        self._click_study_item(window, "studyPrimaryAction")
        self.now = 340
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(action.property("text"), "\ud734\uc2dd \uc7ac\uac1c")
        self.assertEqual(window.property("pomodoroSeconds"), 30)
        self.assertAlmostEqual(ring.property("progress"), 0.5)
        self._click_study_item(window, "studyPrimaryAction")
        self.assertAlmostEqual(ring.property("progress"), 0.5)
        self.now = 370
        self.measurement._update_pomodoro(self.now)
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(self.measurement.pomodoroPhase, "waiting_next")
        self.assertEqual(action.property("text"), "\ub2e4\uc74c \ud559\uc2b5 \uc2dc\uc791")
        self.assertEqual(window.property("elapsedSeconds"), 120)
        self.assertAlmostEqual(ring.property("progress"), 0)
        self._click_study_item(window, "studyPrimaryAction")
        self.assertEqual(self.measurement.pomodoroPhase, "focus")
        self.now = 490
        self.measurement._update_pomodoro(self.now)
        self.now = 580
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(self.measurement.pomodoroPhase, "long_break")
        self.assertAlmostEqual(ring.property("progress"), 0.5)
        self.assertEqual(window.property("elapsedSeconds"), 240)
        self.now = 670
        self.measurement._update_pomodoro(self.now)
        self.app.processEvents()
        self.assertEqual(window.property("studyViewState"), "result")
        self.assertFalse(ring.property("visible"))
        self.assertEqual(window.property("elapsedSeconds"), 240)
        self.assertEqual(warnings, [])

    def test_hidden_preview_keeps_camera_failure_visible_and_focus_time_separate(self):
        window, _, warnings = self._study_window("free")
        self._click_study_item(window, "studyPrimaryAction")
        self.measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
        ))
        self.now = 110
        self.measurement.camera_connected = False
        self.measurement._expire_observation(self.now)
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self._click_study_item(window, "studyCameraToggle")
        self.assertEqual(self.measurement.effectiveState, "unscored")
        label = window.findChild(QObject, "studyMeasurementStatusLabel")
        self.assertEqual(label.property("text"), "\uce74\uba54\ub77c \uc5f0\uacb0 \ud655\uc778")
        self.assertEqual(label.property("color").name(), "#946311")
        self.assertEqual(window.findChild(QObject, "studyTimeValue").property("text"), "00:00:10")
        self.assertEqual(window.findChild(QObject, "studyFocusTimeValue").property("text"), "00:00:02")
        self.now = 120
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self.assertEqual(window.property("elapsedSeconds"), 20)
        self.assertEqual(window.findChild(QObject, "studyFocusTimeValue").property("text"), "00:00:02")
        self.assertEqual(warnings, [])

    def test_zero_time_break_boundary_does_not_accept_duplicate_camera_states(self):
        self.assertTrue(self.measurement.startSession("free", -1, "", ""))
        self.measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
        ))
        self.measurement.session.update(FocusDecision(
            self.now, ObservationState.GAZE_AWAY, EffectiveState.NON_FOCUS, "duplicate"
        ))
        self.assertEqual(self.measurement.session.metrics.last_effective_state, EffectiveState.FOCUS)
        self.measurement.toggleBreak()
        self.assertEqual(self.measurement.session.metrics.last_effective_state, EffectiveState.BREAK)
        self.measurement.session.update(FocusDecision(
            self.now - 1, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "old"
        ))
        self.assertEqual(self.measurement.session.metrics.last_effective_state, EffectiveState.BREAK)
        self.now += 30
        self.assertEqual(self.measurement.elapsedSeconds, 0)
        self.measurement.toggleBreak()
        self.measurement.toggleBreak()
        self.assertEqual(self.measurement.session.metrics.last_effective_state, EffectiveState.BREAK)
        self.now += 20
        self.assertEqual(self.measurement.elapsedSeconds, 0)
        self.assertEqual(self.measurement.durations["break"], 50)
        self.measurement.endSession()
        self.assertEqual(self.measurement.session.summary.focus_seconds, 0)
        self.assertEqual(self.measurement.session.summary.break_seconds, 50)

    def test_active_tasks_select_exact_id_and_cycle_status_without_resetting_study(self):
        window, backend, warnings = self._study_window("free")
        backend.addPlannerTask("Same task", "", "", "")
        backend.addPlannerTask("Same task", "", "", "")
        first, second = self.database.list_planner_tasks()
        self.app.processEvents()
        self._click_study_item(window, f"learningTaskSelect{second.id}")
        self.assertEqual(window.property("currentTaskId"), second.id)
        self.assertNotEqual(
            self._study_item(window, f"learningTaskRow{first.id}").property("color"),
            self._study_item(window, f"learningTaskRow{second.id}").property("color"),
        )
        self._click_study_item(window, "studyPrimaryAction")
        self.assertEqual(self.measurement.session.task_id, second.id)
        self.now = 120
        self.measurement.stateChanged.emit()
        self.app.processEvents()
        self._click_study_item(window, f"learningTaskStateButton{second.id}")
        self.app.processEvents()
        self.assertEqual(self.database.list_planner_tasks()[1].status, "completed")
        self._click_study_item(window, f"learningTaskStateButton{second.id}")
        self.app.processEvents()
        self.assertEqual(self.database.list_planner_tasks()[1].status, "deferred")
        self.assertTrue(self.measurement.sessionRunning)
        self.assertEqual(window.property("elapsedSeconds"), 20)
        self.assertEqual(self.measurement.session.task_id, second.id)
        self.assertEqual(self.measurement.selectedTaskId, -1)
        self.assertEqual(self.measurement.session.metrics.task_records()[0]["study_seconds"], 20)
        backend.cyclePlannerTask(first.id)
        backend.cyclePlannerTask(second.id)
        backend.cyclePlannerTask(second.id)
        self.app.processEvents()
        self.assertEqual(window.property("currentTask"), "\ubaa8\ub4e0 \ubaa9\ud45c\ub97c \uc644\ub8cc\ud588\uc2b5\ub2c8\ub2e4!")
        self.assertTrue(self.measurement.sessionRunning)
        self.assertEqual(warnings, [])

    def test_study_views_render_and_fit_at_both_supported_sizes(self):
        self.wall_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        window, backend, warnings = self._study_window("free")
        backend.addPlannerTask("\uc601\uc5b4 \ub3c5\ud574\uc640 \uc624\ub2f5 \uc815\ub9ac \u00b7 \uc624\ub298 \ud559\uc2b5 \uacc4\ud68d", "", "", "")
        task = self.database.list_planner_tasks()[0]
        self.app.processEvents()
        self._click_study_item(window, f"learningTaskSelect{task.id}")
        for mode in ("free", "pomodoro"):
            for width, height in ((1280, 720), (1024, 680)):
                window.setWidth(width)
                window.setHeight(height)
                window.setProperty("pomodoroMode", mode == "pomodoro")
                if window.property("sessionEnded") and not window.property("studyPreparation"):
                    self._click_study_item(window, "studyPrimaryAction")
                self._click_study_item(window, "studyPrimaryAction")
                self.measurement._apply_decision(FocusDecision(
                    self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
                ))
                self.now += 40
                self.measurement._apply_decision(FocusDecision(
                    self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"
                ))
                self.measurement.stateChanged.emit()
                QTest.qWait(220)
                for name in ("learningPage", "studyPrimaryAction", "studyEndAction", "studyStatusStrip", "compactTasks"):
                    self._assert_study_item_fits(window, name)
                if mode == "pomodoro":
                    self._assert_study_item_fits(window, "pomodoroRing")
                    ring = window.findChild(QObject, "pomodoroRing")
                    self.assertAlmostEqual(ring.property("width"), ring.property("height"), delta=0.5)
                else:
                    self._assert_study_item_fits(window, "todayStudyTimeValue")
                    self._assert_study_item_fits(window, "todayFocusTimeValue")
                self._capture(window, f"{mode}-study-{width}x{height}")
                footprint = self._camera_footprint(window)
                self._click_study_item(window, "studyCameraToggle")
                self.assertEqual(self._camera_footprint(window), footprint)
                self._assert_study_item_fits(window, "cameraPanel")
                self._assert_study_item_fits(window, "studyCameraPreview")
                self._capture(window, f"{mode}-camera-{width}x{height}")
                self._click_study_item(window, "studyPrimaryAction")
                self.now += 15
                self.measurement.stateChanged.emit()
                QTest.qWait(220)
                self._assert_study_item_fits(window, "learningPage")
                self._assert_study_item_fits(window, "studyPrimaryAction")
                self._assert_study_item_fits(window, "studyEndAction")
                self._assert_study_item_fits(window, "breakRing")
                self._capture(window, f"{mode}-break-{width}x{height}")
                self._click_study_item(window, "studyEndAction")
                self.now += 20
                QTest.qWait(40)
                self._capture(window, f"{mode}-result-{width}x{height}")
        self.assertEqual(warnings, [])

    def test_explicit_task_switch_and_completion_use_one_session_clock(self):
        window, backend, warnings = self._study_window("free")
        backend.addPlannerTask("Math", "", "", "")
        backend.addPlannerTask("English", "", "", "")
        first, second = self.database.list_planner_tasks()
        self._click_study_item(window, f"learningTaskSelect{first.id}")
        self._click_study_item(window, "studyPrimaryAction")
        self.now = 160
        self._click_study_item(window, f"learningTaskSelect{second.id}")
        self.assertEqual(self.measurement.session_started_at, 100)
        self.assertEqual(self.measurement.elapsedSeconds, 60)
        self.now = 190
        self._click_study_item(window, f"learningTaskStateButton{second.id}")
        self.assertEqual(self.measurement.selectedTaskId, -1)
        self.assertTrue(self.measurement.sessionRunning)
        self.assertEqual(self.database.list_planner_tasks()[0].status, "pending")
        self.measurement.toggleBreak()
        self.now = 210
        self.measurement.endSession()
        rows = self.database.list_study_records()
        self.assertEqual({row.task_id: row.study_seconds for row in rows}, {first.id: 60, second.id: 30})
        self.assertEqual(len(self.database.list_sessions()), 1)
        self.assertEqual(backend.todayStudySeconds, 90)
        self.assertEqual(self.database.list_sessions()[0].break_seconds, 20)
        self.assertEqual(warnings, [])

    def test_schedule_only_recommends_and_keeps_explicit_selection(self):
        window, backend, warnings = self._study_window("free")
        backend.addPlannerTask("Scheduled", "10:00", "11:00", "")
        backend.addPlannerTask("Chosen", "", "", "")
        scheduled, chosen = self.database.list_planner_tasks()
        window.setProperty("currentDateTime", QDateTime(self.wall_start))
        self.assertTrue(QMetaObject.invokeMethod(window, "refreshScheduledTask"))
        self.assertEqual(window.property("recommendedTaskId"), scheduled.id)
        self.assertEqual(window.property("currentTaskId"), -1)
        self._click_study_item(window, f"learningTaskSelect{chosen.id}")
        self._click_study_item(window, "studyPrimaryAction")
        self.now = 160
        backend.refresh()
        self.assertEqual(window.property("currentTaskId"), chosen.id)
        self.assertEqual(self.measurement.selectedTaskId, chosen.id)
        self._click_study_item(window, "selectRecommendedTaskButton")
        self.assertEqual(self.measurement.selectedTaskId, scheduled.id)
        self.now = 190
        self.measurement.endSession()
        self.assertEqual({row.task_id: row.study_seconds for row in self.database.list_study_records()}, {chosen.id: 60, scheduled.id: 30})
        self.assertEqual(warnings, [])

    def test_live_hourly_projection_hands_off_once_and_keeps_breaks_empty(self):
        backend = AppBridge(self.database, self.store)
        backend.addPlannerTask("Disable samples", "", "", "")
        self.measurement.recordsChanged.connect(backend.refresh)
        self.assertTrue(self.measurement.startSession("free", -1, "", ""))
        self.measurement._apply_decision(FocusDecision(self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"))
        self.now = 160
        self.measurement._apply_decision(FocusDecision(self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "test"))
        before = dict(self.measurement.session.metrics.durations)
        live = self.measurement.liveSessionData
        hourly = backend.learningHourlyData(live)
        self.assertEqual(hourly[0]["values"][0], 100)
        self.assertTrue(hourly[0]["present"][0])
        self.assertEqual(self.database.list_sessions(), [])
        self.assertEqual(self.measurement.session.metrics.durations, before)
        backend.shiftRecords(0, -1)
        backend.shiftPlannerDate(1)
        self.assertEqual(backend.learningHourlyData(live), hourly)
        self.measurement.toggleBreak()
        self.now = 760
        self.assertEqual(backend.learningHourlyData(self.measurement.liveSessionData)[0]["present"], [True, False, False, False, False, False])
        self.measurement.endSession()
        self.assertEqual(self.measurement.liveSessionData, {})
        self.assertEqual(backend.learningHourlyData({}), hourly)
        self.assertEqual(backend.todayStudySeconds, 60)
        self.assertEqual(len(self.database.list_sessions()), 1)

    def test_study_record_popup_saves_edits_allocates_and_confirms_delete(self):
        window, backend, warnings = self._study_window("free")
        session_id = self.database.add_session(SessionSummary(
            self.wall_start.isoformat(sep=" "), (self.wall_start + timedelta(minutes=90)).isoformat(sep=" "),
            3600, 1800, 0, 0, 0, 2 / 3, 1, 600, []), self.root / "measured", task_records=[])
        backend.refresh()
        window.setProperty("currentTabIndex", 3)
        records_page = self._study_item(window, "recordsPage")
        for period, name in enumerate(("daily", "weekly", "monthly")):
            records_page.setProperty("periodIndex", period)
            QTest.qWait(50)
            self._capture(window, f"records-{name}-1280x720")
        records_page.setProperty("periodIndex", 0)
        self._click_study_item(window, "openStudyRecordsButton")
        popup = self._study_item(window, "studyRecordDialog")
        self.assertTrue(popup.property("visible"))
        for width, height in ((1280, 720), (1024, 680)):
            window.setWidth(width)
            window.setHeight(height)
            QTest.qWait(70)
            for name in ("recordTitleInput", "recordHours", "recordMinutes", "saveStudyRecordButton", "studyRecordList"):
                self._assert_study_item_fits(window, name)
            self._capture(window, f"study-record-entry-{width}x{height}")
        self._click_study_item(window, "recordDateButton")
        picker = self._study_item(window, "studyRecordDatePicker")
        self.assertTrue(picker.property("visible"))
        self._capture(window, "study-record-date-picker-1024x680")
        self.assertTrue(QMetaObject.invokeMethod(picker, "close"))
        title = self._study_item(window, "recordTitleInput")
        title.setProperty("text", "Offline reading")
        self._click_study_item(window, "saveStudyRecordButton")
        self.assertTrue(popup.property("visible"))
        self.assertNotEqual(popup.property("errorText"), "")
        self.assertEqual(title.property("text"), "Offline reading")
        minute_input = self._study_item(window, "recordMinutes").property("contentItem")
        minute_input.setProperty("text", "30")
        self._click_study_item(window, "saveStudyRecordButton")
        self.assertFalse(popup.property("visible"))
        manual = self.database.list_study_records()[0]
        self.assertEqual(manual.study_seconds, 1800)
        self.assertIsNone(manual.focus_seconds)
        self.assertEqual(backend.todayStudySeconds, 7200)
        self._click_study_item(window, "openStudyRecordsButton")
        self._click_study_item(window, f"editStudyRecord{manual.id}")
        self._study_item(window, "recordMinutes").setProperty("value", 20)
        self._click_study_item(window, "saveStudyRecordButton")
        self.assertEqual(len(self.database.list_study_records()), 1)
        self.assertEqual(backend.todayStudySeconds, 6600)
        self._click_study_item(window, "openStudyRecordsButton")
        self._study_item(window, "recordKindChoice").setProperty("currentIndex", 1)
        popup.setProperty("sessionId", session_id)
        title.setProperty("text", "Measured Math")
        self._study_item(window, "recordHours").setProperty("value", 1)
        self._study_item(window, "recordMinutes").setProperty("value", 10)
        self.app.processEvents()
        self._capture(window, "study-record-allocation-1024x680")
        self._click_study_item(window, "saveStudyRecordButton")
        self.assertFalse(popup.property("visible"))
        allocated = next(row for row in self.database.list_study_records() if row.source == "allocated")
        self.assertEqual(self.database.remaining_study_seconds(session_id), 1200)
        self.assertEqual(backend.todayStudySeconds, 6600)
        self._click_study_item(window, "openStudyRecordsButton")
        self._click_study_item(window, f"editStudyRecord{allocated.id}")
        self._study_item(window, "recordMinutes").setProperty("value", 40)
        self._click_study_item(window, "saveStudyRecordButton")
        self.assertTrue(popup.property("visible"))
        self.assertNotEqual(popup.property("errorText"), "")
        self.assertEqual(title.property("text"), "Measured Math")
        self._capture(window, "study-record-validation-1024x680")
        self._click_study_item(window, "deleteStudyRecordButton")
        self.assertTrue(self._study_item(window, "deleteStudyRecordConfirmation").property("visible"))
        self._click_study_item(window, "confirmDeleteStudyRecordButton")
        self.assertEqual(self.database.remaining_study_seconds(session_id), 5400)
        self.assertEqual(len(self.database.list_study_records()), 1)
        self.assertEqual(backend.todayStudySeconds, 6600)
        self.assertTrue(QMetaObject.invokeMethod(popup, "close"))
        self.database.delete_session(session_id)
        backend.refresh()
        for period, name in enumerate(("daily", "weekly", "monthly")):
            records_page.setProperty("periodIndex", period)
            QTest.qWait(60)
            self._capture(window, f"manual-only-{name}-1024x680")
            if period < 2:
                self.assertIn("미측정", self._study_item(window, "recordsSummaryLabel").property("text"))
            if period == 2:
                self._assert_study_item_fits(window, f"monthlyDay{backend.monthlyDayCount}")
        backend.selectRecordsDate("2026-08-01")
        QTest.qWait(50)
        self._assert_study_item_fits(window, "monthlyDay31")
        self._capture(window, "monthly-six-rows-1024x680")
        self.assertEqual(warnings, [])

    def test_approved_layout_return_tools_and_tasks_preserve_one_session(self):
        window, backend, warnings = self._study_window("free")
        backend.addPlannerTask("English", "", "", "")
        backend.addPlannerTask("Math", "", "", "")
        self._click_study_item(window, "studyPrimaryAction")
        page = self._study_item(window, "learningPage")
        self.assertFalse(self._study_item(window, "studyTools").property("visible"))
        self.assertTrue(self._study_item(window, "compactTasks").property("visible"))
        clock = self._study_item(window, "todayStudyTimeValue")
        clock_position = clock.mapToScene(QPointF(0, 0))
        directory = self.measurement.session.recorder.session_dir
        self.now += 20
        self.measurement.stateChanged.emit()
        self._click_study_item(window, "compactTask0")
        first = self.database.list_planner_tasks()[0]
        self.assertEqual(self.measurement.selectedTaskId, first.id)
        self._click_study_item(window, "compactTask0")
        self.assertEqual(self.measurement.selectedTaskId, -1)
        self.assertEqual(self.database.list_planner_tasks()[0].status, "pending")
        self._click_study_item(window, "compactTask1")
        self._click_study_item(window, "openStudyTools")
        self.assertTrue(self._study_item(window, "studyTools").property("visible"))
        self.assertFalse(self._study_item(window, "compactTasks").property("visible"))
        self.assertEqual(clock.mapToScene(QPointF(0, 0)), clock_position)
        self._click_study_item(window, "closeStudyTools")
        QTest.qWait(170)
        self._click_study_item(window, "returnPreparation")
        self.assertTrue(page.property("preparation"))
        self.assertTrue(self.measurement.sessionRunning)
        self.assertEqual(self.measurement.elapsedSeconds, 20)
        self._click_study_item(window, "studyPrimaryAction")
        self.assertFalse(page.property("preparation"))
        self.assertEqual(self.measurement.session.recorder.session_dir, directory)
        self._click_study_item(window, "studyPrimaryAction")
        self.now += 30
        self.measurement.stateChanged.emit()
        self._click_study_item(window, "returnPreparation")
        self._click_study_item(window, "studyPrimaryAction")
        self.assertTrue(page.property("resting"))
        self.assertTrue(self.measurement.sessionPaused)
        self.assertEqual(self.measurement.elapsedSeconds, 20)
        self._click_study_item(window, "studyEndAction")
        self._click_study_item(window, "reviewStudyRecord")
        self.assertEqual(window.property("currentTabIndex"), 3)
        self.assertTrue(self._study_item(window, "studyRecordDialog").property("visible"))
        self.assertEqual(warnings, [])

    def test_summary_record_shortcut_uses_configured_study_day_before_midnight_boundary(self):
        self.wall_start = self.wall_start.replace(hour=3, minute=50)
        window, backend, warnings = self._study_window("free")
        self._click_study_item(window, "studyPrimaryAction")
        self.now += 20
        self.measurement.stateChanged.emit()
        self._click_study_item(window, "studyEndAction")
        self._click_study_item(window, "reviewStudyRecord")
        self.assertEqual(backend.recordsDateIso, (self.wall_start - timedelta(hours=4)).date().isoformat())
        self.assertTrue(self._study_item(window, "studyRecordDialog").property("visible"))
        self.assertEqual(warnings, [])

    def test_preparation_modes_validate_and_persist_existing_pomodoro_settings(self):
        window, backend, warnings = self._study_window("free")
        self.assertTrue(self._study_item(window, "preparationView").property("visible"))
        for width, height in ((1280, 720), (1024, 680)):
            window.setWidth(width); window.setHeight(height)
            self._capture(window, f"ready-general-{width}x{height}")
        self._click_study_item(window, "choosePomodoro")
        self._click_study_item(window, "autoStartNextSwitch")
        self.assertTrue(window.property("autoStartNext"))
        for width, height in ((1280, 720), (1024, 680)):
            window.setWidth(width); window.setHeight(height)
            QTest.qWait(220)
            for name in ("focusMinutesField", "breakMinutesField", "longBreakMinutesField", "roundsField", "calibrationShortcut", "studyPrimaryAction"):
                self._assert_study_item_fits(window, name)
            self._capture(window, f"ready-pomodoro-{width}x{height}")
        field = self._study_item(window, "focusMinutesField")
        field.setProperty("text", "")
        self._click_study_item(window, "studyPrimaryAction")
        self.assertFalse(self.measurement.sessionRunning)
        self.assertTrue(self._study_item(window, "preparationView").property("visible"))
        field.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_3)
        QTest.keyClick(window, Qt.Key_0)
        self.assertEqual(window.property("focusMinutes"), 30)
        self._click_study_item(window, "studyPrimaryAction")
        self.assertTrue(self.measurement.sessionRunning)
        self.assertEqual(self.store.load().pomodoro_focus_minutes, 30)
        self.assertTrue(self.store.load().pomodoro_auto_start_next)
        self.assertEqual(self.measurement.pomodoro.config.focus_minutes, 30)
        self.assertEqual(warnings, [])

    def test_approved_study_render_uses_real_saved_and_live_totals(self):
        self.wall_start = self.wall_start.replace(hour=12, minute=45)
        earlier = self.wall_start - timedelta(hours=2)
        self.database.add_session(SessionSummary(
            earlier.isoformat(sep=" "), (earlier + timedelta(minutes=100)).isoformat(sep=" "),
            5400, 420, 0, 180, 0, 5400 / 5820, 0.97, 5400, []
        ), self.root / "previous")
        window, backend, warnings = self._study_window("free")
        for title in ("English reading", "Math review", "History questions"):
            backend.addPlannerTask(title, "", "", "")
        backend.cyclePlannerTask(self.database.list_planner_tasks()[2].id)
        self._click_study_item(window, "studyPrimaryAction")
        self.measurement._apply_decision(FocusDecision(100, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "fixture"))
        self._click_study_item(window, "compactTask0")
        self.now = 1540
        self.measurement._apply_decision(FocusDecision(self.now, ObservationState.GAZE_AWAY, EffectiveState.NON_FOCUS, "fixture"))
        self.now = 1600
        self.measurement.toggleBreak()
        self.now = 1900
        self.measurement.toggleBreak()
        self.now = 2020
        self.measurement._apply_decision(FocusDecision(self.now, ObservationState.LOW_CONFIDENCE, EffectiveState.UNSCORED, "fixture"))
        self.now = 2140
        self.measurement._apply_decision(FocusDecision(self.now, ObservationState.GAZE_AWAY, EffectiveState.NON_FOCUS, "fixture"))
        self.now = 2500
        self.measurement.stateChanged.emit()
        self.assertEqual(window.property("todayStudySeconds"), 8100)
        self.assertEqual(window.property("todayFocusSeconds"), 6840)
        window.findChild(QObject, "wallClockTimer").setProperty("running", False)
        window.setProperty("currentDateTime", QDateTime(self.wall_start + timedelta(minutes=40)))
        for mode in ("free", "pomodoro"):
            window.setProperty("pomodoroMode", mode == "pomodoro")
            if mode == "pomodoro":
                self.measurement.pomodoro.start(1900)
                self.measurement.pomodoro.completed_cycles = 1
                self.measurement.stateChanged.emit()
            for width, height in ((1280, 720), (1024, 680)):
                window.setWidth(width); window.setHeight(height)
                self._capture(window, f"approved-{mode}-{width}x{height}")
                for tab, label in ((0, "tasks"), (1, "timeline"), (2, "camera")):
                    self.assertTrue(QMetaObject.invokeMethod(self._study_item(window, "learningPage"), "openTools", Qt.DirectConnection, Q_ARG("QVariant", tab)))
                    self._capture(window, f"approved-{mode}-{label}-{width}x{height}")
                    self.assertTrue(QMetaObject.invokeMethod(self._study_item(window, "learningPage"), "closeTools"))
                    QTest.qWait(170)
        self.assertEqual(warnings, [])

    def test_native_study_rail_and_actions_stay_separate_at_supported_sizes(self):
        window, backend, warnings = self._study_window("free")
        for title in (
            "영어 독해 지문 2개", "수학 오답 다시 풀기", "한국사 개념 정리",
            "과학 문제 복습", "읽고 싶은 책 20쪽", "내일 공부 준비",
        ):
            backend.addPlannerTask(title, "", "", "")
        event_id = backend.addCalendarEvent(
            "기말고사", (self.wall_start + timedelta(days=25)).date().isoformat()
        )
        backend.setPrimaryCalendarEvent(event_id)
        self._click_study_item(window, "studyPrimaryAction")
        window.findChild(QObject, "wallClockTimer").setProperty("running", False)
        self.measurement._apply_decision(FocusDecision(
            self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "fixture"
        ))
        for _ in range(1200):
            self.now += 1
            self.measurement._apply_decision(FocusDecision(
                self.now, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS, "fixture"
            ))
        self.measurement.stateChanged.emit()
        self._click_study_item(window, "compactTask0")
        for mode in ("free", "pomodoro"):
            window.setProperty("pomodoroMode", mode == "pomodoro")
            if mode == "pomodoro":
                self.measurement.pomodoro.start(self.now - 1200)
                self.measurement.stateChanged.emit()
            for width, height in ((1024, 680), (1280, 720), (1366, 768)):
                window.setWidth(width)
                window.setHeight(height)
                QTest.qWait(220)
                for name in (
                    "studyMainArea", "compactTasks", "studyActions",
                    "studyPrimaryAction", "studyEndAction", "currentSessionTime",
                    "navigationButton4", "primaryDdayButton", "openStudyTools",
                ):
                    self._assert_study_item_fits(window, name)
                main = self._study_item(window, "studyMainArea")
                rail = self._study_item(window, "compactTasks")
                right = main.mapToScene(QPointF(main.width(), 0)).x()
                self.assertLessEqual(right + 16, rail.mapToScene(QPointF()).x())
                last_tab = self._study_item(window, "navigationButton4")
                back = self._study_item(window, "returnPreparation")
                self.assertLessEqual(
                    last_tab.mapToScene(QPointF(last_tab.width(), 0)).x(),
                    back.mapToScene(QPointF()).x(),
                )
                self._capture(window, f"native-{mode}-{width}x{height}")
        self.assertEqual(warnings, [])

    def test_compact_status_is_independent_of_selection_and_session_time(self):
        window, backend, warnings = self._study_window("free")
        backend.addPlannerTask("복습", "", "", "")
        task_id = self.database.list_planner_tasks()[0].id
        self._click_study_item(window, "studyPrimaryAction")
        self._click_study_item(window, "compactTask0")
        self.now += 20
        self.measurement.stateChanged.emit()
        self._click_study_item(window, "compactTask0")
        self.assertEqual(self.database.list_planner_tasks()[0].status, "pending")
        self.assertEqual(self.measurement.selectedTaskId, -1)
        for status in ("completed", "deferred", "pending"):
            self._click_study_item(window, "compactTaskState0")
            self.assertEqual(self.database.list_planner_tasks()[0].status, status)
            self.assertEqual(self.measurement.selectedTaskId, -1)
            self.assertTrue(self.measurement.sessionRunning)
            self.assertEqual(self.measurement.elapsedSeconds, 20)
        state_button = self._study_item(window, "compactTaskState0")
        state_button.forceActiveFocus(Qt.TabFocusReason)
        QTest.keyClick(window, Qt.Key_Space)
        self.app.processEvents()
        self.assertEqual(self.database.list_planner_tasks()[0].status, "completed")
        self.assertEqual(self.measurement.session.metrics.task_records()[0]["task_id"], task_id)
        self.assertEqual(self.measurement.session.metrics.task_records()[0]["study_seconds"], 20)
        self.assertTrue(self._study_item(window, "compactTaskState0").property("activeFocus"))
        QTest.keyClick(window, Qt.Key_Space)
        self.app.processEvents()
        self.assertEqual(self.database.list_planner_tasks()[0].status, "deferred")
        self.assertEqual(warnings, [])

    def test_preparation_error_feedback_has_its_own_space_and_remains_visible(self):
        window, backend, warnings = self._study_window("pomodoro")
        window.setWidth(1024)
        window.setHeight(680)
        field = self._study_item(window, "focusMinutesField")
        field.setProperty("text", "")
        self._click_study_item(window, "studyPrimaryAction")
        feedback = self._study_item(window, "studyFeedback")
        self.assertTrue(feedback.property("visible"))
        self.assertIn("1~120", feedback.property("text"))
        self.assertFalse(self._study_item(window, "calibrationShortcut").property("visible"))
        QTest.qWait(1900)
        self.assertTrue(feedback.property("visible"))
        self._assert_study_item_fits(window, "studyFeedback")
        bottom = feedback.mapToScene(QPointF(0, feedback.height())).y()
        action = self._study_item(window, "studyActions")
        self.assertLess(bottom, action.mapToScene(QPointF()).y())
        self._capture(window, "native-preparation-error-1024x680")
        field.setProperty("text", "25")
        self._click_study_item(window, "studyPrimaryAction")
        self.assertTrue(self.measurement.sessionRunning)
        self.assertFalse(self._study_item(window, "learningPage").property("feedbackIsError"))
        self.assertNotIn("시간과 반복", feedback.property("text"))
        self.assertEqual(warnings, [])

    def test_study_controls_remain_immediate_with_motion_disabled(self):
        window, backend, warnings = self._study_window("free")
        context = qmlContext(window)
        toggle = QQmlExpression(context, window, "StudyStyle.motionEnabled = false")
        toggle.evaluate()
        self.assertFalse(toggle.hasError(), toggle.error().toString())
        try:
            for expression in ("StudyStyle.fast", "StudyStyle.normal"):
                value = QQmlExpression(context, window, expression).evaluate()[0]
                self.assertEqual(value, 0)
            button = self._study_item(window, "navigationButton4")
            point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
            QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, point)
            self.app.processEvents()
            self.assertAlmostEqual(button.property("background").property("scale"), 0.96)
            QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, point)
            self.app.processEvents()
            self.assertEqual(window.property("currentTabIndex"), 4)
            self.assertEqual(self._study_item(window, "navigationIndicator").property("x"), 320)
        finally:
            QQmlExpression(context, window, "StudyStyle.motionEnabled = true").evaluate()
        self.assertEqual(warnings, [])

    def test_study_button_hover_has_no_dark_intermediate_frame(self):
        window, backend, warnings = self._study_window("free")
        self._click_study_item(window, "studyPrimaryAction")
        for name in ("openStudyTools", "studyPrimaryAction"):
            button = self._study_item(window, name)
            background = button.property("background")
            original_size = (button.width(), button.height())
            point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
            for _ in range(2):
                for position in (QPointF(0, 0).toPoint(), point):
                    QTest.mouseMove(window, position)
                    for delay in (20, 35, 60):
                        QTest.qWait(delay)
                        color = background.property("color")
                        alpha = color.alphaF()
                        for channel in (color.red(), color.green(), color.blue()):
                            self.assertGreaterEqual(
                                channel * alpha + 250 * (1 - alpha), 235,
                                f"{name} dark hover frame: {color.getRgb()}",
                            )
                        self.assertEqual((button.width(), button.height()), original_size)
        self.assertEqual(warnings, [])

    def test_rest_control_uses_coffee_and_resume_uses_play(self):
        window, backend, warnings = self._study_window("free")
        self._click_study_item(window, "studyPrimaryAction")
        button = self._study_item(window, "studyPrimaryAction")
        self.assertEqual(button.property("symbol"), "coffee")
        self._capture(window, "study-coffee-control")
        self.now += 20
        self._click_study_item(window, "studyPrimaryAction")
        self.assertTrue(self.measurement.sessionPaused)
        self.assertEqual(button.property("symbol"), "play")
        self.assertEqual(self.measurement.elapsedSeconds, 20)
        self._capture(window, "study-resume-control")
        self.now += 10
        self._click_study_item(window, "studyPrimaryAction")
        self.assertEqual(button.property("symbol"), "coffee")
        self.assertEqual(self.measurement.elapsedSeconds, 20)
        self.assertEqual(warnings, [])

    def _study_window(self, mode):
        backend = AppBridge(self.database, self.store)
        backend.saveSettings({"session_mode": mode})
        engine = QQmlApplicationEngine()
        engine.addImageProvider("study-icons", StudyIconProvider())
        frame = QImage(640, 480, QImage.Format_RGB32)
        frame.fill(0xffe5e7eb)
        self.measurement.image_provider.set_image(frame)
        engine.addImageProvider("camera", self.measurement.image_provider)
        self.addCleanup(lambda: [window.close() for window in engine.rootObjects()])
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
        engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[1] / "onf_v2/ui_qml/qml/Main.qml")))
        self.assertEqual(len(engine.rootObjects()), 1)
        window = engine.rootObjects()[0]
        window.setProperty("backendObject", backend)
        window.setProperty("measurementObject", self.measurement)
        window.setProperty("pomodoroMode", mode == "pomodoro")
        self.app.processEvents()
        return window, backend, warnings

    def _click_study_item(self, window, name):
        self.app.processEvents()
        QTest.qWait(25)
        page = self._study_item(window, "learningPage")
        if name.startswith("learningTask"):
            self.assertTrue(QMetaObject.invokeMethod(page, "openTools", Qt.DirectConnection, Q_ARG("QVariant", 0)))
            QTest.qWait(220)
        elif name == "studyCameraToggle":
            self.assertTrue(QMetaObject.invokeMethod(page, "openTools", Qt.DirectConnection, Q_ARG("QVariant", 2)))
            QTest.qWait(220)
        elif name.startswith("navigationButton") and not self._study_item(window, name).property("visible"):
            self._click_study_item(window, "returnPreparation")
            QTest.qWait(220)
        item = self._study_item(window, name)
        self.assertIsNotNone(item, name)
        self.assertTrue(item.property("visible"), name)
        if item.property("enabled") is not None:
            self.assertTrue(item.property("enabled"), name)
        point = item.mapToScene(QPointF(item.property("width") / 2, item.property("height") / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
        self.app.processEvents()
        if name == "navigationButton0" and window.property("sessionRunning") and window.property("studyPreparation"):
            self._click_study_item(window, "studyPrimaryAction")
        if name == "studyPrimaryAction":
            QTest.qWait(220)

    def _camera_footprint(self, window):
        return tuple(
            self._study_item(window, name).property(dimension)
            for name in ("cameraPanel", "studyCameraPreview")
            for dimension in ("width", "height")
        )

    def _assert_study_item_fits(self, window, name):
        item = self._study_item(window, name)
        self.assertIsNotNone(item, name)
        self.assertTrue(item.property("visible"), name)
        position = item.mapToScene(QPointF(0, 0))
        self.assertGreater(item.property("width"), 0, name)
        self.assertGreater(item.property("height"), 0, name)
        self.assertGreaterEqual(position.x(), -0.5, name)
        self.assertGreaterEqual(position.y(), -0.5, name)
        self.assertLessEqual(position.x() + item.property("width"), window.width() + 0.5, name)
        self.assertLessEqual(position.y() + item.property("height"), window.height() + 0.5, name)

    def _study_item(self, window, name):
        item = window.findChild(QObject, name)
        if item is not None:
            return item
        remaining = list(window.contentItem().childItems())
        while remaining:
            item = remaining.pop()
            if item.objectName() == name:
                return item
            remaining.extend(item.childItems())
        return None

    def _capture(self, window, name):
        QTest.qWait(220)
        image = window.grabWindow()
        self.assertFalse(image.isNull())
        capture_dir = os.environ.get("ONF_UI_CAPTURE_DIR")
        if capture_dir:
            directory = Path(capture_dir)
            directory.mkdir(parents=True, exist_ok=True)
            self.assertTrue(image.save(str(directory / f"{name}.png")))


if __name__ == "__main__":
    unittest.main()
