import unittest
import tempfile

from onf_v2.app.pomodoro import (
    PomodoroConfig,
    PomodoroController,
    PomodoroPhase,
)
from onf_v2.app.session_manager import SessionManager
from onf_v2.app.session_recorder import SessionRecorder
from onf_v2.core.models import (
    EffectiveState,
    FocusDecision,
    ObservationState,
)


class PomodoroControllerTests(unittest.TestCase):
    def test_focus_break_waiting_and_next_focus_flow(self):
        timer = PomodoroController(
            PomodoroConfig(
                focus_minutes=1,
                short_break_minutes=1,
                long_break_minutes=2,
                cycles=2,
            )
        )

        started = timer.start(10.0)
        self.assertEqual(started.phase, PomodoroPhase.FOCUS)
        self.assertEqual(timer.update(69.0).remaining_seconds, 1.0)

        break_started = timer.update(70.0)
        self.assertEqual(break_started.phase, PomodoroPhase.SHORT_BREAK)
        self.assertEqual(break_started.completed_cycles, 1)

        waiting = timer.update(130.0)
        self.assertEqual(waiting.phase, PomodoroPhase.WAITING_NEXT)
        self.assertEqual(waiting.remaining_seconds, 60.0)

        next_focus = timer.start_next(140.0)
        self.assertEqual(next_focus.phase, PomodoroPhase.FOCUS)
        self.assertEqual(next_focus.cycle, 2)

    def test_last_focus_uses_long_break_then_completes(self):
        timer = PomodoroController(
            PomodoroConfig(
                focus_minutes=1,
                short_break_minutes=1,
                long_break_minutes=2,
                cycles=1,
            )
        )
        timer.start(0.0)

        long_break = timer.update(60.0)
        self.assertEqual(long_break.phase, PomodoroPhase.LONG_BREAK)
        self.assertEqual(long_break.completed_cycles, 1)

        completed = timer.update(180.0)
        self.assertEqual(completed.phase, PomodoroPhase.COMPLETED)
        self.assertFalse(timer.active)

    def test_pause_preserves_remaining_time(self):
        timer = PomodoroController(PomodoroConfig(focus_minutes=1))
        timer.start(10.0)

        paused = timer.pause(35.0)
        self.assertEqual(paused.phase, PomodoroPhase.PAUSED)
        self.assertEqual(paused.remaining_seconds, 35.0)
        self.assertEqual(timer.update(100.0).remaining_seconds, 35.0)

        resumed = timer.resume(200.0)
        self.assertEqual(resumed.phase, PomodoroPhase.FOCUS)
        self.assertEqual(timer.update(234.0).remaining_seconds, 1.0)

    def test_can_skip_short_break(self):
        timer = PomodoroController(
            PomodoroConfig(
                focus_minutes=1,
                short_break_minutes=1,
                cycles=2,
            )
        )
        timer.start(0.0)
        timer.update(60.0)

        update = timer.skip_break(65.0)

        self.assertEqual(update.phase, PomodoroPhase.FOCUS)
        self.assertEqual(update.cycle, 2)

    def test_pomodoro_metadata_and_break_time_are_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = SessionManager(recorder=SessionRecorder(tmp))
            session.start(session_mode="pomodoro", pomodoro_cycles_planned=4)
            session.update(self._decision(0.0, EffectiveState.FOCUS))
            session.update(self._decision(60.0, EffectiveState.BREAK))
            session.update(self._decision(120.0, EffectiveState.FOCUS))
            session.pomodoro_cycles_completed = 1

            summary = session.finish(180.0)
            repeated = session.finish(181.0)

            self.assertIsNotNone(summary)
            self.assertEqual(summary.session_mode, "pomodoro")
            self.assertEqual(summary.pomodoro_cycles_completed, 1)
            self.assertEqual(summary.pomodoro_cycles_planned, 4)
            self.assertEqual(summary.focus_seconds, 120.0)
            self.assertEqual(summary.break_seconds, 60.0)
            self.assertIs(repeated, summary)
            row = session.recorder.database.list_sessions(1)[0]
            self.assertEqual(row.session_mode, "pomodoro")
            self.assertEqual(row.pomodoro_cycles_completed, 1)
            self.assertEqual(len(session.recorder.database.list_sessions()), 1)

    def test_session_can_be_linked_to_planner_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = SessionManager(recorder=SessionRecorder(tmp))
            task_id = session.recorder.database.add_planner_task(
                title="물리 복습",
                subject_id=None,
                planned_date="2026-07-19",
                deadline_date="2026-07-20",
                estimated_minutes=30,
                task_type="study",
            )

            session.start(task_id=task_id)
            session.update(self._decision(0.0, EffectiveState.FOCUS))
            session.finish(60.0)

            self.assertEqual(
                session.recorder.database.list_sessions(1)[0].task_id,
                task_id,
            )

    def test_active_session_cannot_be_started_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = SessionManager(recorder=SessionRecorder(tmp))
            session.start()
            first_directory = session.recorder.session_dir

            with self.assertRaises(RuntimeError):
                session.start(session_mode="pomodoro")

            self.assertEqual(session.recorder.session_dir, first_directory)
            self.assertEqual(session.session_mode, "free")
            session.finish(0.0)

    def test_sessions_started_in_same_second_use_different_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = SessionRecorder(tmp)
            recorder.start("2026-07-19 12:00:00")
            first = recorder.session_dir
            recorder._close_raw_file()

            recorder.start("2026-07-19 12:00:00")
            second = recorder.session_dir
            recorder._close_raw_file()

            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    @staticmethod
    def _decision(timestamp: float, state: EffectiveState) -> FocusDecision:
        return FocusDecision(
            timestamp=timestamp,
            raw_state=ObservationState.NORMAL_VIEW,
            effective_state=state,
            reason="test",
        )


if __name__ == "__main__":
    unittest.main()
