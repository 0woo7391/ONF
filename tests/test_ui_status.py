import os
import tempfile
import time
import unittest
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from onf_v2.app.camera_service import CameraFrame
from onf_v2.app.pomodoro import PomodoroConfig, PomodoroPhase
from onf_v2.app.session_manager import SessionManager
from onf_v2.app.session_recorder import SessionRecorder
from onf_v2.core.calibration import CalibrationProgress
from onf_v2.core.models import (
    AppState,
    CalibrationProfile,
    CalibrationStatus,
    EffectiveState,
    FocusDecision,
    ObservationState,
)
from onf_v2.ui.main_window import (
    MainWindow,
    PeriodTrendChart,
    PlannerScheduleEditor,
)


class PersistentStatusPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_pomodoro_keeps_calibration_status_visible(self):
        window = MainWindow()
        row = window.session_mode_combo.findData("pomodoro")
        window.session_mode_combo.blockSignals(True)
        window.session_mode_combo.setCurrentIndex(row)
        window.session_mode_combo.blockSignals(False)
        window._refresh_labels(None)
        window.session.app_state = AppState.CALIBRATING
        window.engine.active_calibration_target = "screen"

        window._refresh_calibration(
            CalibrationProgress(
                status=CalibrationStatus.COLLECTING,
                progress=0.45,
                valid_samples=18,
                target_samples=40,
                message="얼굴 전체와 양쪽 눈이 보이게 해주세요.",
            )
        )

        self.assertFalse(window.status_surface.isHidden())
        self.assertTrue(window.standard_dashboard.isHidden())
        self.assertFalse(window.pomodoro_dial.isHidden())
        self.assertIn("45%", window.reason_label.text())
        self.assertIn("양쪽 눈", window.reason_label.text())
        self.assertEqual(window.screen_calibration_button.progress, 0.45)
        self.assertIn("45%", window.screen_calibration_button.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_calibration_progress_stays_visible_on_settings_tab(self):
        window = MainWindow()
        window.tabs.setCurrentIndex(3)
        window.session.app_state = AppState.CALIBRATING
        window.engine.active_calibration_target = "writing"
        window.engine.set_work_mode("screen_writing")

        window._refresh_calibration(
            CalibrationProgress(
                status=CalibrationStatus.COLLECTING,
                progress=0.72,
                valid_samples=29,
                target_samples=40,
                message="필기 자세를 유지하세요.",
            )
        )

        self.assertEqual(window.tabs.currentIndex(), 3)
        self.assertFalse(window.writing_calibration_button.isHidden())
        self.assertEqual(window.writing_calibration_button.progress, 0.72)
        self.assertIn("72%", window.writing_calibration_button.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_calibration_result_plays_sound_for_success_and_failure(self):
        window = MainWindow()
        window.session.app_state = AppState.CALIBRATING
        window.engine.active_calibration_target = "screen"
        with patch.object(window, "_play_alert_sound") as play_sound:
            window._refresh_calibration(
                CalibrationProgress(
                    status=CalibrationStatus.READY,
                    progress=1.0,
                    valid_samples=40,
                    target_samples=40,
                    message="저장되었습니다.",
                )
            )
            window._refresh_calibration(
                CalibrationProgress(
                    status=CalibrationStatus.FAILED,
                    progress=0.0,
                    valid_samples=8,
                    target_samples=40,
                    message="움직임이 너무 큽니다.",
                )
            )

        self.assertEqual(play_sound.call_count, 2)
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_camera_change_runs_without_blocking_ui_thread(self):
        window = MainWindow()
        window._persist_settings = lambda: True

        def slow_open(index):
            time.sleep(0.08)
            window.camera.backend_name = "테스트 카메라"
            return True

        window.camera.open = slow_open
        started = time.perf_counter()
        window._start_camera_open(4, automatic=False)
        returned_in = time.perf_counter() - started

        self.assertLess(returned_in, 0.04)
        deadline = time.monotonic() + 1.0
        while not window.camera_open_future.done() and time.monotonic() < deadline:
            time.sleep(0.01)
        window._consume_camera_open_result()

        self.assertTrue(window.camera_available)
        self.assertEqual(window.settings.camera_index, 4)
        self.assertIn("연결됨", window.camera_caption.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_writing_calibration_button_only_shows_in_dual_mode(self):
        window = MainWindow()

        window.engine.set_work_mode("screen")
        window._update_calibration_controls()
        self.assertTrue(window.writing_calibration_button.isHidden())

        window.engine.set_work_mode("screen_writing")
        window._update_calibration_controls()
        self.assertFalse(window.writing_calibration_button.isHidden())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_dual_calibration_buttons_show_independent_status(self):
        window = MainWindow()
        baseline = CalibrationProfile(
            yaw_center=0.0,
            pitch_center=0.0,
            roll_center=0.0,
            gaze_x_center=0.5,
            gaze_y_center=0.5,
            left_eye_open_baseline=0.25,
            right_eye_open_baseline=0.25,
            face_scale_center=0.4,
            face_center=(0.5, 0.5),
            sample_count=40,
            quality_score=1.0,
        )
        window.engine.calibration.profile = baseline
        window.engine.calibration.status = CalibrationStatus.READY
        window.engine.set_work_mode("screen_writing")

        window._update_calibration_controls()

        self.assertEqual(
            window.screen_calibration_button.property("calibrationState"),
            "complete",
        )
        self.assertIn("✓", window.screen_calibration_button.text())
        self.assertEqual(
            window.writing_calibration_button.property("calibrationState"),
            "pending",
        )
        self.assertNotIn("✓", window.writing_calibration_button.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_dual_mode_explains_missing_writing_baseline(self):
        window = MainWindow()
        baseline = CalibrationProfile(
            yaw_center=0.0,
            pitch_center=0.0,
            roll_center=0.0,
            gaze_x_center=0.5,
            gaze_y_center=0.5,
            left_eye_open_baseline=0.25,
            right_eye_open_baseline=0.25,
            face_scale_center=0.4,
            face_center=(0.5, 0.5),
            sample_count=40,
            quality_score=1.0,
        )
        window.engine.calibration.profile = baseline
        window.engine.calibration.status = CalibrationStatus.READY
        window.engine.set_work_mode("screen_writing")
        window.camera_available = True
        window.session.app_state = AppState.READY
        decision = FocusDecision(
            timestamp=0.0,
            raw_state=ObservationState.NOT_CALIBRATED,
            effective_state=EffectiveState.UNSCORED,
            reason="test",
            confidence=0.9,
        )

        window._refresh_labels(decision)

        self.assertFalse(window.start_button.isEnabled())
        self.assertEqual(window.status_label.text(), "필기 기준 필요")
        self.assertIn("필기", window.app_state_label.text())
        self.assertIn("필기 자세", window.reason_label.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_camera_failure_starts_reconnect_without_ending_session(self):
        window = MainWindow()
        window._persist_settings = lambda: True

        class DummyAnalyzer:
            @staticmethod
            def close():
                return None

        window.analyzer = DummyAnalyzer()
        window.session.app_state = AppState.RUNNING
        window.camera_open_index = 2
        window.camera.read = lambda: CameraFrame(
            ok=False,
            timestamp=time.monotonic(),
            error="Camera frames stopped",
        )
        window.camera.open = lambda index: True

        window._tick()

        self.assertEqual(window.session.app_state, AppState.RUNNING)
        self.assertIsNotNone(window.camera_open_future)
        self.assertFalse(window.camera_available)
        self.assertIn("재연결", window.status_label.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_active_session_blocks_manual_camera_change(self):
        window = MainWindow()
        window.session.app_state = AppState.RUNNING
        window.camera_open_index = 0
        window.camera_combo.addItem("Camera 0", 0)
        window.camera_combo.addItem("Camera 1", 1)
        target_index = window.camera_combo.findData(1)
        window.camera_combo.blockSignals(True)
        window.camera_combo.setCurrentIndex(target_index)
        window.camera_combo.blockSignals(False)

        with patch.object(window, "_start_camera_open") as start_open:
            window._change_camera()

        start_open.assert_not_called()
        self.assertEqual(window.camera_combo.currentData(), 0)
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_records_dashboard_uses_study_metrics(self):
        window = MainWindow()
        today = datetime.now().strftime("%Y-%m-%d")
        rows = [
            SimpleNamespace(
                id=1,
                started_at_wall=f"{today} 09:00:00",
                ended_at_wall=f"{today} 09:30:00",
                focus_seconds=1200.0,
                non_focus_seconds=300.0,
                break_seconds=300.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=0.8,
                coverage_ratio=1.0,
                longest_focus_seconds=720.0,
                event_count=2,
                session_dir="ignored",
                session_mode="free",
                pomodoro_cycles_completed=0,
                pomodoro_cycles_planned=0,
            ),
            SimpleNamespace(
                id=2,
                started_at_wall=f"{today} 14:00:00",
                ended_at_wall=f"{today} 14:25:00",
                focus_seconds=900.0,
                non_focus_seconds=300.0,
                break_seconds=300.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=0.75,
                coverage_ratio=1.0,
                longest_focus_seconds=600.0,
                event_count=1,
                session_dir="ignored",
                session_mode="pomodoro",
                pomodoro_cycles_completed=1,
                pomodoro_cycles_planned=4,
            ),
        ]

        window.records_period = "day"
        window._refresh_records_dashboard(rows)

        self.assertEqual(window.records_focus_time.text(), "35분")
        self.assertEqual(window.records_study_time.text(), "45분")
        self.assertEqual(window.records_longest_focus.text(), "12분")
        self.assertEqual(window.records_focus_ratio.text(), "78%")
        self.assertIn("2회", window.records_average_session.text())
        self.assertIn("1회", window.records_pomodoro.text())

        window.records_period = "month"
        window._refresh_records_dashboard(rows)
        self.assertTrue(window.records_trend_chart.isHidden())
        self.assertFalse(window.records_activity_chart.isHidden())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_records_table_only_shows_user_facing_columns(self):
        window = MainWindow()
        headers = [
            window.records_table.horizontalHeaderItem(column).text()
            for column in range(window.records_table.columnCount())
        ]

        self.assertEqual(
            headers,
            ["날짜", "학습 방식", "공부 시간", "순공 시간", "집중률", "최장 집중"],
        )
        self.assertNotIn("측정 성공률", headers)
        self.assertFalse(hasattr(window, "db_summary_view"))
        self.assertFalse(hasattr(window, "event_view"))
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_ending_session_stops_all_session_timers(self):
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow()
            window.session = SessionManager(recorder=SessionRecorder(tmp))
            window.database = window.session.recorder.database
            window.session.start(
                session_mode="pomodoro",
                pomodoro_cycles_planned=4,
            )
            window.pomodoro.configure(PomodoroConfig(focus_minutes=25, cycles=4))
            window.pomodoro.start(100.0)
            window.pomodoro.completed_cycles = 2
            window.break_timer.start(100.0)
            window.pomodoro_action_button.setVisible(True)

            window._end_session()

            self.assertEqual(window.session.app_state, AppState.RESULT)
            self.assertEqual(window.session.summary.pomodoro_cycles_completed, 2)
            self.assertEqual(window.pomodoro.phase, PomodoroPhase.IDLE)
            self.assertFalse(window.pomodoro.active)
            self.assertTrue(window.pomodoro_dial.session_ended)
            self.assertEqual(window.pomodoro_dial.remaining_seconds, 0.0)
            self.assertFalse(window.break_timer.active)
            self.assertTrue(window.pomodoro_action_button.isHidden())
            self.assertFalse(window.end_button.isEnabled())

            window.pomodoro.configure(PomodoroConfig(focus_minutes=30, cycles=2))
            restarted = window.pomodoro.start(200.0)
            self.assertEqual(restarted.phase, PomodoroPhase.FOCUS)
            window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_completed_pomodoro_ends_session_and_stops_timer(self):
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow()
            window.settings.sound_enabled = False
            window.session = SessionManager(recorder=SessionRecorder(tmp))
            window.database = window.session.recorder.database
            config = PomodoroConfig(
                focus_minutes=1,
                short_break_minutes=1,
                long_break_minutes=1,
                cycles=1,
            )
            window.pomodoro.configure(config)
            window.pomodoro.start(0.0)
            window.session.start(
                session_mode="pomodoro",
                pomodoro_cycles_planned=1,
            )

            window._update_pomodoro(60.0)
            self.assertEqual(window.session.app_state, AppState.BREAK)
            window._update_pomodoro(120.0)

            self.assertEqual(window.session.app_state, AppState.RESULT)
            self.assertEqual(window.pomodoro.phase, PomodoroPhase.IDLE)
            self.assertTrue(window.pomodoro_dial.session_ended)
            self.assertEqual(window.session.summary.pomodoro_cycles_completed, 1)
            window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_settings_offer_multiple_alert_sounds(self):
        window = MainWindow()
        sound_keys = {
            window.alert_sound_combo.itemData(index)
            for index in range(window.alert_sound_combo.count())
        }

        self.assertEqual(sound_keys, {"impact", "chime", "digital", "soft"})
        self.assertEqual(
            window.alert_sound_combo.currentData(),
            window.settings.alert_sound,
        )
        digital_index = window.alert_sound_combo.findData("digital")
        with patch.object(window, "_play_sound") as play_sound:
            window.alert_sound_combo.setCurrentIndex(digital_index)
            play_sound.assert_called_once_with(window.volume_slider.value())
        window._persist_settings = lambda: True
        window._save_settings()
        self.assertEqual(window.settings.alert_sound, "digital")
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_active_session_keeps_judgement_settings_until_next_session(self):
        window = MainWindow()
        window._persist_settings = lambda: True
        window.session.app_state = AppState.RUNNING
        original_mode = window.settings.mode
        original_absence = window.settings.absence_to_break_minutes
        requested_mode = "lenient" if original_mode == "strict" else "strict"
        requested_absence = 9 if original_absence != 9 else 8
        window.settings_mode_combo.setCurrentIndex(
            window.settings_mode_combo.findData(requested_mode)
        )
        window.absence_minutes_spin.setValue(requested_absence)

        window._save_settings()

        self.assertEqual(window.settings.mode, original_mode)
        self.assertEqual(window.settings_mode_combo.currentData(), original_mode)
        self.assertEqual(window.settings.absence_to_break_minutes, original_absence)
        self.assertEqual(window.absence_minutes_spin.value(), original_absence)
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_automatic_absence_is_shown_as_excluded_time_not_manual_break(self):
        window = MainWindow()
        window.session.app_state = AppState.RUNNING
        decision = FocusDecision(
            timestamp=300.0,
            raw_state=ObservationState.NO_FACE,
            effective_state=EffectiveState.BREAK,
            reason="test",
            confidence=0.0,
        )

        window._refresh_labels(decision)

        self.assertEqual(window.status_label.text(), "장시간 자리 비움")
        self.assertIn("자동으로 제외", window.reason_label.text())
        self.assertIn("측정", window.app_state_label.text())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_sound_preview_waits_until_audio_is_ready(self):
        window = MainWindow()

        class LoadingSound:
            def __init__(self):
                self.current_status = QSoundEffect.Status.Loading
                self.volume = 0.0
                self.play_count = 0

            def status(self):
                return self.current_status

            def setVolume(self, volume):
                self.volume = volume

            @staticmethod
            def isPlaying():
                return False

            @staticmethod
            def stop():
                return None

            def play(self):
                self.play_count += 1

        sound = LoadingSound()
        window.sound_effect = sound

        window._play_sound(85)
        self.assertEqual(sound.play_count, 0)
        self.assertEqual(window.pending_sound_volume, 85)

        sound.current_status = QSoundEffect.Status.Ready
        window._sound_effect_status_changed(sound)
        self.assertEqual(sound.play_count, 1)
        self.assertEqual(sound.volume, 0.85)
        self.assertIsNone(window.pending_sound_volume)
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_records_use_calendar_and_saved_study_day_start(self):
        window = MainWindow()

        self.assertTrue(window.records_date_edit.calendarPopup())
        self.assertEqual(window.records_day_start_combo.count(), 24)
        self.assertEqual(
            window.records_day_start_combo.currentData(),
            window.settings.study_day_start_hour,
        )
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_four_am_boundary_assigns_after_midnight_to_previous_study_day(self):
        window = MainWindow()
        selected = datetime.now().date()
        window.records_selected_date = selected
        window.settings.study_day_start_hour = 4

        def record(identifier, started, ended):
            return SimpleNamespace(
                id=identifier,
                started_at_wall=started.strftime("%Y-%m-%d %H:%M:%S"),
                ended_at_wall=ended.strftime("%Y-%m-%d %H:%M:%S"),
                focus_seconds=1200.0,
                non_focus_seconds=300.0,
                break_seconds=0.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=0.8,
                coverage_ratio=1.0,
                longest_focus_seconds=600.0,
                event_count=1,
                session_dir="ignored",
                session_mode="free",
                pomodoro_cycles_completed=0,
                pomodoro_cycles_planned=0,
            )

        included = record(
            1,
            datetime.combine(selected + timedelta(days=1), datetime.min.time()).replace(hour=2),
            datetime.combine(selected + timedelta(days=1), datetime.min.time()).replace(hour=3),
        )
        excluded = record(
            2,
            datetime.combine(selected, datetime.min.time()).replace(hour=2),
            datetime.combine(selected, datetime.min.time()).replace(hour=3),
        )

        filtered = window._filter_record_rows([included, excluded])

        self.assertEqual([row.id for row in filtered], [1])
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_daily_hour_graph_splits_session_across_clock_hours(self):
        window = MainWindow()
        selected = datetime.now().date()
        window.records_selected_date = selected
        window.settings.study_day_start_hour = 4
        row = SimpleNamespace(
            started_at_wall=f"{selected:%Y-%m-%d} 09:30:00",
            ended_at_wall=f"{selected:%Y-%m-%d} 10:30:00",
            focus_seconds=1800.0,
            non_focus_seconds=1800.0,
            break_seconds=0.0,
            unscored_seconds=0.0,
            absent_pending_seconds=0.0,
        )

        points = window._build_daily_hour_points([row])
        by_hour = {point[0]: point for point in points}

        self.assertAlmostEqual(by_hour["09"][1], 1800.0)
        self.assertAlmostEqual(by_hour["10"][1], 1800.0)
        self.assertAlmostEqual(by_hour["09"][2], 0.5)
        self.assertAlmostEqual(by_hour["10"][2], 0.5)
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_weekly_totals_split_session_at_study_day_boundary(self):
        window = MainWindow()
        window.settings.study_day_start_hour = 4
        window.records_period = "week"
        window.records_selected_date = datetime(2026, 7, 19).date()
        row = SimpleNamespace(
            id=1,
            started_at_wall="2026-07-19 03:30:00",
            ended_at_wall="2026-07-19 04:30:00",
            focus_seconds=3600.0,
            non_focus_seconds=0.0,
            break_seconds=0.0,
            unscored_seconds=0.0,
            absent_pending_seconds=0.0,
            focus_ratio=1.0,
            coverage_ratio=1.0,
            longest_focus_seconds=3600.0,
            event_count=0,
            session_dir="ignored",
            session_mode="free",
            pomodoro_cycles_completed=0,
            pomodoro_cycles_planned=0,
        )

        window._refresh_records_dashboard([row])

        self.assertEqual(window.records_study_time.text(), "30분")
        self.assertEqual(window.records_focus_time.text(), "30분")
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_week_graph_labels_include_date_and_weekday(self):
        window = MainWindow()
        window.records_period = "week"
        window.records_selected_date = datetime(2026, 7, 15).date()

        points = window._build_period_points([])

        self.assertEqual(
            [label for label, _rate in points],
            [
                "7/12\n일",
                "7/13\n월",
                "7/14\n화",
                "7/15\n수",
                "7/16\n목",
                "7/17\n금",
                "7/18\n토",
            ],
        )
        window.close()

    def test_week_chart_spreads_fixed_width_bars_across_available_width(self):
        layout = PeriodTrendChart._bar_layout(18.0, 664.0, 7)
        centers = [x + width / 2.0 for x, width in layout]

        self.assertEqual(len(layout), 7)
        self.assertTrue(all(width <= 18.0 for _x, width in layout))
        self.assertGreater(centers[-1] - centers[0], 500.0)
        gaps = [right - left for left, right in zip(centers, centers[1:])]
        self.assertAlmostEqual(max(gaps), min(gaps), places=5)

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_record_header_shows_week_range_or_year_month(self):
        window = MainWindow()
        window.records_selected_date = datetime(2026, 7, 15).date()

        window.records_period = "week"
        window._update_records_period_buttons()
        self.assertEqual(
            window.records_period_label.text(),
            "2026년 7월 12일 ~ 7월 18일",
        )
        self.assertTrue(window.records_date_edit.isHidden())

        window.records_period = "month"
        window._update_records_period_buttons()
        self.assertEqual(window.records_period_label.text(), "2026년 7월")
        self.assertTrue(window.records_date_edit.isHidden())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_today_is_home_and_deadline_labels_are_actionable(self):
        window = MainWindow()

        self.assertEqual(window.tabs.tabText(0), "오늘")
        self.assertEqual(window._format_d_day("2026-07-19", datetime(2026, 7, 19).date()), "D-Day")
        self.assertEqual(window._format_d_day("2026-07-22", datetime(2026, 7, 19).date()), "D-3")
        self.assertEqual(window._format_d_day("2026-07-18", datetime(2026, 7, 19).date()), "1일 지남")
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_today_uses_same_study_day_boundary_as_records(self):
        window = MainWindow()
        window.settings.study_day_start_hour = 4

        self.assertEqual(
            window._study_date_for_datetime(datetime(2026, 7, 20, 2, 30)),
            datetime(2026, 7, 19).date(),
        )
        self.assertEqual(
            window._study_date_for_datetime(datetime(2026, 7, 20, 5, 0)),
            datetime(2026, 7, 20).date(),
        )
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_today_planner_uses_daily_layout_without_subject_management(self):
        window = MainWindow()

        self.assertFalse(hasattr(window, "add_subject_button"))
        self.assertTrue(hasattr(window, "planner_timetable"))
        self.assertTrue(hasattr(window, "planner_quick_title"))
        self.assertTrue(hasattr(window, "planner_calendar_button"))
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_quick_add_creates_plain_daily_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow()
            window.session = SessionManager(recorder=SessionRecorder(tmp))
            window.database = window.session.recorder.database
            window.planner_selected_date = datetime(2026, 7, 20).date()
            window.planner_quick_title.setText("영어 지문 3개")

            window._quick_add_planner_task()

            tasks = window.database.list_planner_tasks()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].title, "영어 지문 3개")
            self.assertIsNone(tasks[0].subject_id)
            self.assertEqual(tasks[0].task_type, "study")
            self.assertEqual(tasks[0].planned_date, "2026-07-20")
            self.assertEqual(tasks[0].estimated_minutes, 0)
            self.assertIsNone(tasks[0].planned_start_minute)
            self.assertIsNone(tasks[0].planned_end_minute)
            self.assertFalse(hasattr(window, "planner_quick_minutes"))
            window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_quick_add_accepts_start_end_and_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow()
            window.session = SessionManager(recorder=SessionRecorder(tmp))
            window.database = window.session.recorder.database
            window.planner_selected_date = datetime(2026, 7, 20).date()
            window.planner_quick_title.setText("과학 개념 복습")
            window.planner_quick_schedule.set_values(
                9 * 60 + 35,
                11 * 60 + 5,
                90,
            )

            window._quick_add_planner_task()

            task = window.database.list_planner_tasks()[0]
            self.assertEqual(task.planned_start_minute, 9 * 60 + 35)
            self.assertEqual(task.planned_end_minute, 11 * 60 + 5)
            self.assertEqual(task.estimated_minutes, 90)
            self.assertEqual(window.planner_quick_title.text(), "")
            values, invalid = window.planner_quick_schedule.values()
            self.assertFalse(invalid)
            self.assertEqual(values, {"start": None, "end": None, "duration": None})
            window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_planner_item_edits_title_and_schedule_inline(self):
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow()
            window.session = SessionManager(recorder=SessionRecorder(tmp))
            window.database = window.session.recorder.database
            task_id = window.database.add_planner_task(
                title="수학 오답 정리",
                subject_id=None,
                planned_date="2026-07-20",
                deadline_date=None,
                estimated_minutes=0,
                task_type="study",
            )
            task = window.database.list_planner_tasks()[0]
            row = window._planner_task_row(task)
            button_texts = {
                button.text() for button in row.findChildren(QPushButton)
            }

            self.assertIn("×", button_texts)
            self.assertNotIn("⋯", button_texts)
            self.assertNotIn("시작", button_texts)
            schedule = row.findChild(PlannerScheduleEditor)
            self.assertIsNotNone(schedule)
            schedule.set_values(9 * 60 + 30, 10 * 60 + 15, 45)
            schedule._commit_current_values()
            title_edit = row.findChild(QLineEdit, "PlannerTaskTitleEdit")
            title_edit.setText("수학 오답 다시 풀기")
            title_edit.editingFinished.emit()
            updated = window.database.list_planner_tasks()[0]
            self.assertEqual(updated.title, "수학 오답 다시 풀기")
            self.assertEqual(updated.planned_start_minute, 9 * 60 + 30)
            self.assertEqual(updated.estimated_minutes, 45)
            self.assertEqual(updated.planned_end_minute, 10 * 60 + 15)
            window.close()

    def test_inline_schedule_calculates_missing_end_as_provisional(self):
        editor = PlannerScheduleEditor()
        start_hour = editor.groups["start"][1]
        duration_hour = editor.groups["duration"][1]
        duration_minute = editor.groups["duration"][2]
        start_hour.setText("9")
        start_hour.textEdited.emit("9")
        duration_hour.setText("1")
        duration_hour.textEdited.emit("1")
        duration_minute.setText("30")
        duration_minute.textEdited.emit("30")

        values, invalid = editor.values()
        self.assertFalse(invalid)
        self.assertEqual(values["end"], 10 * 60 + 30)
        self.assertTrue(editor.groups["end"][1].property("calculated"))

        duration_minute.editingFinished.emit()
        self.assertFalse(editor.groups["end"][1].property("calculated"))

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_planner_time_calculates_the_missing_value(self):
        window = MainWindow()
        self.assertEqual(window._parse_planner_clock_parts("9", ""), 9 * 60)
        self.assertEqual(
            window._parse_planner_duration_parts("1", "30"),
            90,
        )
        values = {"start": 23 * 60 + 30, "end": None, "duration": 90}
        self.assertEqual(
            window._calculate_planner_time_value("end", values),
            60,
        )
        values = {"start": 9 * 60, "end": 10 * 60 + 20, "duration": None}
        self.assertEqual(
            window._calculate_planner_time_value("duration", values),
            80,
        )
        values = {"start": None, "end": 8 * 60, "duration": 45}
        self.assertEqual(
            window._calculate_planner_time_value("start", values),
            7 * 60 + 15,
        )
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_planned_time_range_marks_timetable_slots(self):
        window = MainWindow()
        window.settings.study_day_start_hour = 4
        task = SimpleNamespace(
            planned_date="2026-07-20",
            planned_start_minute=9 * 60 + 30,
            planned_end_minute=10 * 60 + 15,
            estimated_minutes=45,
        )

        slots = window._build_planned_timetable_slots(
            [task],
            datetime(2026, 7, 20).date(),
        )

        self.assertEqual(slots, {33, 34, 35, 36, 37})
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_ten_minute_timeline_marks_actual_session_slots(self):
        window = MainWindow()
        selected = datetime(2026, 7, 20).date()
        window.settings.study_day_start_hour = 4
        row = SimpleNamespace(
            started_at_wall="2026-07-20 09:00:00",
            ended_at_wall="2026-07-20 09:20:00",
            focus_seconds=1200.0,
            non_focus_seconds=0.0,
            break_seconds=0.0,
            unscored_seconds=0.0,
            absent_pending_seconds=0.0,
        )

        slots = window._build_ten_minute_timetable_slots([row], selected)

        self.assertEqual(len(slots), 144)
        self.assertEqual(slots[30], (1.0, EffectiveState.FOCUS))
        self.assertEqual(slots[31], (1.0, EffectiveState.FOCUS))
        self.assertEqual(slots[32], (None, None))
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_ten_minute_timeline_uses_each_slots_own_focus_ratio(self):
        window = MainWindow()
        selected = datetime(2026, 7, 20).date()
        window.settings.study_day_start_hour = 4
        row = SimpleNamespace(
            started_at_wall="2026-07-20 09:00:00",
            ended_at_wall="2026-07-20 09:20:00",
            focus_seconds=600.0,
            non_focus_seconds=600.0,
            break_seconds=0.0,
            unscored_seconds=0.0,
            absent_pending_seconds=0.0,
            timeline_json=json.dumps(
                [{"focus": 60.0}] * 10
                + [{"non_focus": 60.0}] * 10
            ),
        )

        slots = window._build_ten_minute_timetable_slots([row], selected)

        self.assertEqual(slots[30], (1.0, EffectiveState.FOCUS))
        self.assertEqual(slots[31], (0.0, EffectiveState.NON_FOCUS))
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_planner_status_button_cycles_blank_complete_and_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow()
            window.session = SessionManager(recorder=SessionRecorder(tmp))
            window.database = window.session.recorder.database
            task_id = window.database.add_planner_task(
                title="수학 오답 정리",
                subject_id=None,
                planned_date="2026-07-20",
                deadline_date=None,
                estimated_minutes=30,
                task_type="study",
            )

            window._cycle_planner_task_status(task_id, "pending")
            self.assertEqual(
                window.database.list_planner_tasks()[0].status,
                "completed",
            )
            window._cycle_planner_task_status(task_id, "completed")
            self.assertEqual(
                window.database.list_planner_tasks()[0].status,
                "deferred",
            )
            window._cycle_planner_task_status(task_id, "deferred")
            self.assertEqual(
                window.database.list_planner_tasks()[0].status,
                "pending",
            )
            window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_planner_date_navigation_changes_selected_date(self):
        window = MainWindow()
        window.planner_selected_date = datetime(2026, 7, 20).date()

        window._move_planner_date(-1)

        self.assertEqual(
            window.planner_selected_date,
            datetime(2026, 7, 19).date(),
        )
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_active_planner_task_cannot_be_deleted(self):
        window = MainWindow()
        window.session.app_state = AppState.RUNNING
        window.active_task_id = 7

        with patch.object(window.database, "delete_planner_task") as delete_task:
            window._delete_planner_task(7, "자료구조 복습")

        delete_task.assert_not_called()
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_active_task_stays_in_status_panel_without_crowding_top_controls(self):
        window = MainWindow()
        window.resize(1020, 680)
        window.active_task_label.setText("자료구조 기말고사 범위 복습 학습 중")
        window.active_task_label.setVisible(True)
        window.show()
        self.app.processEvents()

        self.assertIs(window.active_task_label.parentWidget(), window.status_surface)
        self.assertLess(window.end_button.geometry().right(), window.app_state_label.geometry().left())
        window.close()

    @patch.object(MainWindow, "_open_camera_and_model", lambda self: None)
    def test_record_arrows_move_by_week_or_month(self):
        window = MainWindow()
        window.records_date_edit.setDate(QDate(2026, 7, 15))

        window.records_period = "week"
        window._move_records_date(-1)
        self.assertEqual(window.records_date_edit.date(), QDate(2026, 7, 8))

        window.records_period = "month"
        window._move_records_date(-1)
        self.assertEqual(window.records_date_edit.date(), QDate(2026, 6, 8))
        window.close()


if __name__ == "__main__":
    unittest.main()
