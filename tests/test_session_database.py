import tempfile
import unittest
import sqlite3
import json
from pathlib import Path

from onf_v2.app.session_database import SessionDatabase
from onf_v2.core.models import AttentionEvent, SessionSummary


class SessionDatabaseTest(unittest.TestCase):
    def test_add_list_events_and_delete_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            summary = SessionSummary(
                started_at_wall="2026-07-19 10:00:00",
                ended_at_wall="2026-07-19 10:10:00",
                focus_seconds=500.0,
                non_focus_seconds=80.0,
                break_seconds=20.0,
                unscored_seconds=5.0,
                absent_pending_seconds=0.0,
                focus_ratio=500.0 / 580.0,
                coverage_ratio=580.0 / 585.0,
                longest_focus_seconds=120.0,
                events=[
                    AttentionEvent(
                        type="gaze_away",
                        started_at=20.0,
                        ended_at=25.0,
                        duration=5.0,
                        max_deviation=24.0,
                    )
                ],
                app_usage_seconds={"Code.exe": 300.0, "chrome.exe": 120.0},
            )

            session_id = db.add_session(summary, Path(tmp) / "session")

            self.assertEqual(len(db.list_sessions()), 1)
            self.assertEqual(len(db.list_events(session_id)), 1)
            usage = db.list_app_usage([session_id])
            self.assertEqual(usage[0].process_name, "Code.exe")
            self.assertEqual(usage[0].duration_seconds, 300.0)

            db.delete_session(session_id)

            self.assertEqual(db.list_sessions(), [])
            self.assertEqual(db.list_events(session_id), [])
            self.assertEqual(db.list_app_usage([session_id]), [])

    def test_existing_database_is_migrated_for_pomodoro_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "onf.sqlite3"
            conn = sqlite3.connect(path)
            try:
                conn.execute(
                    """
                    CREATE TABLE sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        started_at_wall TEXT NOT NULL,
                        ended_at_wall TEXT NOT NULL,
                        focus_seconds REAL NOT NULL,
                        non_focus_seconds REAL NOT NULL,
                        break_seconds REAL NOT NULL,
                        unscored_seconds REAL NOT NULL,
                        absent_pending_seconds REAL NOT NULL,
                        focus_ratio REAL NOT NULL,
                        coverage_ratio REAL NOT NULL,
                        longest_focus_seconds REAL NOT NULL,
                        event_count INTEGER NOT NULL,
                        session_dir TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        started_at REAL NOT NULL,
                        ended_at REAL NOT NULL,
                        duration REAL NOT NULL,
                        max_deviation REAL NOT NULL
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

            SessionDatabase(path)

            conn = sqlite3.connect(path)
            try:
                columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
                }
            finally:
                conn.close()
            self.assertIn("session_mode", columns)
            self.assertIn("pomodoro_cycles_completed", columns)
            self.assertIn("pomodoro_cycles_planned", columns)
            self.assertIn("task_id", columns)

    def test_planner_task_tracks_deadline_completion_and_linked_study_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            subject_id = db.add_subject("수학", "#3182F6")
            task_id = db.add_planner_task(
                title="미적분 문제 20개",
                subject_id=subject_id,
                planned_date="2026-07-19",
                deadline_date="2026-07-22",
                estimated_minutes=50,
                task_type="assignment",
            )
            summary = SessionSummary(
                started_at_wall="2026-07-19 10:00:00",
                ended_at_wall="2026-07-19 10:45:00",
                focus_seconds=2100.0,
                non_focus_seconds=600.0,
                break_seconds=0.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=2100.0 / 2700.0,
                coverage_ratio=1.0,
                longest_focus_seconds=900.0,
                events=[],
            )

            session_id = db.add_session(
                summary,
                Path(tmp) / "session",
                task_id=task_id,
            )
            task = db.list_planner_tasks()[0]

            self.assertEqual(task.title, "미적분 문제 20개")
            self.assertEqual(task.subject_name, "수학")
            self.assertEqual(task.deadline_date, "2026-07-22")
            self.assertEqual(task.actual_focus_seconds, 2100.0)
            self.assertEqual(task.actual_study_seconds, 2700.0)
            self.assertEqual(db.list_sessions(1)[0].task_id, task_id)

            db.set_planner_task_completed(task_id, True)
            self.assertIsNotNone(db.list_planner_tasks()[0].completed_at)
            db.set_planner_task_completed(task_id, False)
            self.assertIsNone(db.list_planner_tasks()[0].completed_at)

            db.delete_session(session_id)
            self.assertEqual(
                db.list_planner_tasks()[0].actual_study_seconds,
                0.0,
            )

    def test_planner_task_can_be_rescheduled_and_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            task_id = db.add_planner_task(
                title="영어 단어 복습",
                subject_id=None,
                planned_date="2026-07-19",
                deadline_date=None,
                estimated_minutes=25,
                task_type="study",
            )

            db.reschedule_planner_task(task_id, "2026-07-20")
            self.assertEqual(
                db.list_planner_tasks()[0].planned_date,
                "2026-07-20",
            )

            db.update_planner_task(
                task_id=task_id,
                title="영어 단어 100개 복습",
                subject_id=None,
                planned_date="2026-07-21",
                deadline_date="2026-07-23",
                estimated_minutes=40,
                task_type="exam",
            )
            updated = db.list_planner_tasks()[0]
            self.assertEqual(updated.title, "영어 단어 100개 복습")
            self.assertEqual(updated.planned_date, "2026-07-21")
            self.assertEqual(updated.deadline_date, "2026-07-23")
            self.assertEqual(updated.estimated_minutes, 40)
            self.assertEqual(updated.task_type, "exam")

            db.delete_planner_task(task_id)
            self.assertEqual(db.list_planner_tasks(), [])

    def test_planner_task_cycles_between_pending_completed_and_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            task_id = db.add_planner_task(
                title="국어 비문학 3지문",
                subject_id=None,
                planned_date="2026-07-20",
                deadline_date=None,
                estimated_minutes=0,
                task_type="study",
            )

            task = db.list_planner_tasks()[0]
            self.assertEqual(task.status, "pending")
            self.assertEqual(task.estimated_minutes, 0)
            self.assertIsNone(task.planned_start_minute)
            self.assertIsNone(task.planned_end_minute)

            db.set_planner_task_time(task_id, 9 * 60 + 30, 40)
            scheduled = db.list_planner_tasks()[0]
            self.assertEqual(scheduled.planned_start_minute, 9 * 60 + 30)
            self.assertEqual(scheduled.estimated_minutes, 40)
            self.assertEqual(scheduled.planned_end_minute, 10 * 60 + 10)

            db.set_planner_task_time(task_id, None, 0)
            cleared = db.list_planner_tasks()[0]
            self.assertIsNone(cleared.planned_start_minute)
            self.assertEqual(cleared.estimated_minutes, 0)
            self.assertIsNone(cleared.planned_end_minute)

            db.set_planner_task_time(task_id, None, 0, 10 * 60 + 25)
            end_only = db.list_planner_tasks()[0]
            self.assertIsNone(end_only.planned_start_minute)
            self.assertEqual(end_only.estimated_minutes, 0)
            self.assertEqual(end_only.planned_end_minute, 10 * 60 + 25)

            db.set_planner_task_status(task_id, "completed")
            completed = db.list_planner_tasks()[0]
            self.assertEqual(completed.status, "completed")
            self.assertIsNotNone(completed.completed_at)

            db.set_planner_task_status(task_id, "deferred")
            deferred = db.list_planner_tasks()[0]
            self.assertEqual(deferred.status, "deferred")
            self.assertIsNone(deferred.completed_at)

            db.set_planner_task_status(task_id, "pending")
            self.assertEqual(db.list_planner_tasks()[0].status, "pending")

    def test_fixed_schedule_repeats_daily_with_independent_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            task_id = db.add_planner_task(
                title="Lunch",
                subject_id=None,
                planned_date="2026-07-20",
                deadline_date=None,
                estimated_minutes=60,
                task_type="study",
                planned_start_minute=12 * 60,
                planned_end_minute=13 * 60,
            )

            self.assertTrue(db.toggle_planner_task_fixed(task_id))
            db.set_planner_task_completed(task_id, True)
            db.ensure_fixed_schedule_occurrences("2026-07-21")

            rows = {row.planned_date: row for row in db.list_planner_tasks()}
            self.assertEqual(set(rows), {"2026-07-20", "2026-07-21"})
            self.assertEqual(rows["2026-07-20"].status, "completed")
            self.assertEqual(rows["2026-07-21"].status, "pending")
            self.assertEqual(rows["2026-07-21"].planned_start_minute, 12 * 60)
            self.assertEqual(rows["2026-07-21"].planned_end_minute, 13 * 60)
            self.assertEqual(rows["2026-07-21"].estimated_minutes, 60)
            self.assertEqual(
                rows["2026-07-20"].fixed_schedule_id,
                rows["2026-07-21"].fixed_schedule_id,
            )

            self.assertFalse(
                db.toggle_planner_task_fixed(rows["2026-07-21"].id)
            )
            db.ensure_fixed_schedule_occurrences("2026-07-22")
            self.assertNotIn(
                "2026-07-22",
                {row.planned_date for row in db.list_planner_tasks()},
            )

    def test_session_keeps_minute_focus_buckets_for_daily_timeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            summary = SessionSummary(
                started_at_wall="2026-07-20 09:00:00",
                ended_at_wall="2026-07-20 09:02:00",
                focus_seconds=60.0,
                non_focus_seconds=60.0,
                break_seconds=0.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=0.5,
                coverage_ratio=1.0,
                longest_focus_seconds=60.0,
                events=[],
            )

            db.add_session(
                summary,
                Path(tmp) / "session",
                timeline_buckets=[
                    {"focus": 60.0},
                    {"non_focus": 60.0},
                ],
            )

            buckets = json.loads(db.list_sessions(1)[0].timeline_json)
            self.assertEqual(buckets[0]["focus"], 60.0)
            self.assertEqual(buckets[1]["non_focus"], 60.0)

    def test_missing_planner_task_is_not_saved_as_orphan_session_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            summary = SessionSummary(
                started_at_wall="2026-07-19 10:00:00",
                ended_at_wall="2026-07-19 10:10:00",
                focus_seconds=600.0,
                non_focus_seconds=0.0,
                break_seconds=0.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=1.0,
                coverage_ratio=1.0,
                longest_focus_seconds=600.0,
                events=[],
            )

            db.add_session(summary, Path(tmp) / "session", task_id=999)

            self.assertIsNone(db.list_sessions(1)[0].task_id)

    def test_list_sessions_can_return_complete_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            summary = SessionSummary(
                started_at_wall="2026-07-19 10:00:00",
                ended_at_wall="2026-07-19 10:10:00",
                focus_seconds=600.0,
                non_focus_seconds=0.0,
                break_seconds=0.0,
                unscored_seconds=0.0,
                absent_pending_seconds=0.0,
                focus_ratio=1.0,
                coverage_ratio=1.0,
                longest_focus_seconds=600.0,
                events=[],
            )
            for index in range(3):
                db.add_session(summary, Path(tmp) / f"session-{index}")

            self.assertEqual(len(db.list_sessions(2)), 2)
            self.assertEqual(len(db.list_sessions(None)), 3)

    def test_calendar_events_keep_only_one_primary_dday(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SessionDatabase(Path(tmp) / "onf.sqlite3")
            first_id = db.add_calendar_event("중간고사", "2026-08-10")
            second_id = db.add_calendar_event("모의고사", "2026-08-20")

            db.set_primary_calendar_event(first_id)
            events = db.list_calendar_events()
            self.assertTrue(next(row for row in events if row.id == first_id).is_primary)

            db.set_primary_calendar_event(second_id)
            events = db.list_calendar_events()
            self.assertFalse(next(row for row in events if row.id == first_id).is_primary)
            self.assertTrue(next(row for row in events if row.id == second_id).is_primary)

            db.delete_calendar_event(second_id)
            self.assertEqual([row.id for row in db.list_calendar_events()], [first_id])


if __name__ == "__main__":
    unittest.main()
