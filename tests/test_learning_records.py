import math
import tempfile
import unittest
from pathlib import Path

from onf_v2.app.session_database import SessionDatabase
from onf_v2.core.metrics import DurationAccumulator, study_seconds
from onf_v2.core.models import EffectiveState, SessionSummary


class LearningRecordTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.database = SessionDatabase(self.root / "onf.sqlite3")
        self.a = self.database.add_planner_task("Math", None, "2026-10-08", None, 30, "study")
        self.b = self.database.add_planner_task("English", None, "2026-10-08", None, 40, "study")

    def summary(self):
        return SessionSummary(
            "2026-10-08 10:00:00", "2026-10-08 11:30:00",
            3600, 1800, 0, 0, 0, 2 / 3, 1, 600, [],
        )

    def test_task_switch_uses_same_clock_and_excludes_break(self):
        metrics = DurationAccumulator()
        metrics.set_task(self.a, "Math", 0)
        metrics.update(EffectiveState.FOCUS, 0)
        metrics.set_task(self.b, "English", 600)
        metrics.update(EffectiveState.BREAK, 900)
        metrics.update(EffectiveState.BREAK, 1200)
        records = metrics.task_records()
        self.assertEqual(study_seconds(metrics.durations), 900)
        self.assertEqual([record["study_seconds"] for record in records], [600, 300])
        self.assertEqual([record["focus_seconds"] for record in records], [600, 300])
        self.assertEqual(metrics.durations[EffectiveState.BREAK], 300)

    def test_absence_reclassification_reaches_previous_task_intervals(self):
        metrics = DurationAccumulator()
        metrics.set_task(self.a, "Math", 0)
        metrics.update(EffectiveState.ABSENT_PENDING, 0)
        metrics.set_task(self.b, "English", 120)
        metrics.update(EffectiveState.BREAK, 300)
        metrics.reclassify_recent_state(EffectiveState.ABSENT_PENDING, EffectiveState.BREAK, 300)
        self.assertEqual(study_seconds(metrics.durations), 0)
        self.assertEqual(metrics.task_records(), [])

    def test_new_session_uses_explicit_records_and_preserves_legacy_links(self):
        old_id = self.database.add_session(self.summary(), self.root / "old", task_id=self.a)
        new_id = self.database.add_session(
            self.summary(), self.root / "new", task_id=self.a,
            task_records=[
                {"task_id": self.a, "title": "Math", "study_seconds": 600, "focus_seconds": 500},
                {"task_id": self.b, "title": "English", "study_seconds": 300, "focus_seconds": 200},
            ],
        )
        tasks = {task.id: task for task in self.database.list_planner_tasks()}
        self.assertEqual(tasks[self.a].actual_study_seconds, 5400 + 600)
        self.assertEqual(tasks[self.b].actual_study_seconds, 300)
        self.assertEqual(self.database.remaining_study_seconds(new_id), 4500)
        self.assertEqual(self.database.remaining_study_seconds(old_id), 0)
        reloaded = SessionDatabase(self.database.path)
        self.assertEqual(reloaded.list_sessions()[1].task_id, self.a)
        self.assertEqual(reloaded.list_planner_tasks()[0].actual_study_seconds, 6000)

    def test_allocations_and_manual_records_do_not_change_measured_summary(self):
        session_id = self.database.add_session(self.summary(), self.root / "session", task_records=[])
        self.database.save_study_record("2026-10-08", "Math", 1800, self.a, session_id)
        self.database.save_study_record("2026-10-08", "English", 2400, self.b, session_id)
        self.assertEqual(self.database.remaining_study_seconds(session_id), 1200)
        manual_id = self.database.save_study_record("2026-10-08", "Math", 1800, self.a)
        records = self.database.list_study_records()
        self.assertEqual(sum(row.study_seconds for row in records if row.source == "manual"), 1800)
        self.assertTrue(all(row.focus_seconds is None for row in records))
        saved = self.database.list_sessions()[0]
        self.assertEqual(saved.focus_seconds + saved.non_focus_seconds, 5400)
        self.assertEqual(saved.focus_seconds, 3600)
        self.assertEqual(len(self.database.list_sessions()), 1)
        self.assertEqual(next(row for row in records if row.id == manual_id).session_id, None)

    def test_validation_and_editing_do_not_duplicate_or_over_allocate(self):
        session_id = self.database.add_session(self.summary(), self.root / "session", task_records=[])
        record_id = self.database.save_study_record("2026-10-08", "Math", 4200, self.a, session_id)
        for seconds in (0, -1, math.nan, math.inf, 86401):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.database.save_study_record("2026-10-08", "Bad", seconds)
        with self.assertRaises(ValueError):
            self.database.save_study_record("2026-10-08", "English", 1800, self.b, session_id)
        with self.assertRaises(ValueError):
            self.database.save_study_record("not-a-date", "Bad", 60)
        with self.assertRaises(ValueError):
            self.database.save_study_record("2026-10-08", "Missing", 60, 99999)
        self.database.save_study_record("2026-10-08", "Math", 1800, self.a, session_id, record_id)
        self.assertEqual(len(self.database.list_study_records()), 1)
        self.assertEqual(self.database.remaining_study_seconds(session_id), 3600)
        self.database.delete_study_record(record_id)
        self.assertEqual(self.database.remaining_study_seconds(session_id), 5400)

    def test_tracked_records_cannot_be_manually_edited_or_deleted(self):
        session_id = self.database.add_session(self.summary(), self.root / "tracked", task_records=[
            {"task_id": self.a, "title": "Math", "study_seconds": 600, "focus_seconds": 500}])
        record = self.database.list_study_records()[0]
        with self.assertRaises(ValueError):
            self.database.save_study_record("2026-10-08", "Changed", 300, self.a, session_id, record.id)
        with self.assertRaises(ValueError):
            self.database.delete_study_record(record.id)
        self.assertEqual(self.database.list_study_records()[0].focus_seconds, 500)

    def test_unscored_task_interval_keeps_unknown_focus(self):
        metrics = DurationAccumulator()
        metrics.set_task(self.a, "Math", 0)
        metrics.update(EffectiveState.UNSCORED, 0)
        metrics.update(EffectiveState.UNSCORED, 600)
        record = metrics.task_records()[0]
        self.assertIsNone(record["focus_seconds"])
        summary = SessionSummary("2026-10-08 10:00:00", "2026-10-08 10:10:00", 0, 0, 0, 600, 0, 0, 0, 0, [])
        self.database.add_session(summary, self.root / "unknown", task_records=[record])
        self.assertIsNone(self.database.list_study_records()[0].focus_seconds)
        self.assertEqual(self.database.list_planner_tasks()[0].actual_unmeasured_seconds, 600)

    def test_invalid_tracked_records_roll_back_the_entire_session(self):
        records = [
            {"task_id": self.a, "title": "Math", "study_seconds": 600, "focus_seconds": 500},
            {"task_id": self.b, "title": "Invalid", "study_seconds": 5400, "focus_seconds": 500},
        ]
        with self.assertRaises(ValueError):
            self.database.add_session(self.summary(), self.root / "invalid", task_records=records)
        self.assertEqual(self.database.list_sessions(), [])
        self.assertEqual(self.database.list_study_records(), [])

    def test_deleting_plan_preserves_record_but_session_delete_removes_allocations(self):
        session_id = self.database.add_session(self.summary(), self.root / "session", task_records=[])
        self.database.save_study_record("2026-10-08", "Math", 600, self.a, session_id)
        self.database.save_study_record("2026-10-08", "Math offline", 600, self.a)
        self.database.delete_planner_task(self.a)
        records = self.database.list_study_records()
        self.assertTrue(all(row.task_id is None for row in records))
        self.assertEqual({row.title for row in records}, {"Math", "Math offline"})
        self.database.delete_session(session_id)
        self.assertEqual([row.source for row in self.database.list_study_records()], ["manual"])


if __name__ == "__main__":
    unittest.main()
