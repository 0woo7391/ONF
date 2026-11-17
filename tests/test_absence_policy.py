import unittest

from onf_v2.app.session_manager import SessionManager
from onf_v2.core.models import EffectiveState, FocusDecision, ObservationState


class MemoryRecorder:
    def __init__(self):
        self.summary = None
        self.timeline_buckets = None
        self.decisions = []

    @staticmethod
    def wall_now():
        return "2026-09-28 10:00:00"

    def start(self, _started_at, task_id=None):
        pass

    def write_decision(self, decision):
        self.decisions.append(decision)

    def finish(self, summary, timeline_buckets=None, task_records=None):
        self.summary = summary
        self.timeline_buckets = timeline_buckets


class AbsencePolicyTests(unittest.TestCase):
    def test_session_start_counts_wait_for_first_observation_as_unscored(self):
        session = SessionManager(recorder=MemoryRecorder())
        session.start(started_at_monotonic=0.0)
        session.update(self._decision(0.4, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS))
        summary = session.finish(1.4)

        self.assertAlmostEqual(summary.unscored_seconds, 0.4)
        self.assertAlmostEqual(summary.focus_seconds, 1.0)

    def test_observation_at_session_start_is_not_discarded(self):
        session = SessionManager(recorder=MemoryRecorder())
        session.start(started_at_monotonic=0.0)
        session.update(self._decision(0.0, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS))
        summary = session.finish(1.0)

        self.assertEqual(summary.focus_seconds, 1.0)
        self.assertEqual(summary.unscored_seconds, 0.0)

    def test_session_without_observations_is_unscored(self):
        session = SessionManager(recorder=MemoryRecorder())
        session.start(started_at_monotonic=0.0)
        summary = session.finish(1.0)

        self.assertEqual(summary.unscored_seconds, 1.0)
        self.assertEqual(summary.focus_seconds, 0.0)

    def test_old_decision_does_not_rewrite_session_events_or_log(self):
        recorder = MemoryRecorder()
        session = SessionManager(recorder=recorder)
        session.start()
        session.update(self._decision(0.0, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS))
        session.update(self._decision(1.0, ObservationState.GAZE_AWAY, EffectiveState.NON_FOCUS))
        session.update(self._decision(0.5, ObservationState.NO_FACE, EffectiveState.ABSENT_PENDING))
        summary = session.finish(2.0)

        self.assertEqual(len(recorder.decisions), 2)
        self.assertEqual(summary.focus_seconds, 1.0)
        self.assertEqual(summary.non_focus_seconds, 1.0)
        self.assertEqual(summary.absent_pending_seconds, 0.0)

    def test_five_minute_absence_is_reclassified_from_its_start(self):
        recorder = MemoryRecorder()
        session = SessionManager(recorder=recorder)
        session.start()
        session.update(self._decision(0.0, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS))
        session.update(self._decision(10.0, ObservationState.NO_FACE, EffectiveState.ABSENT_PENDING))
        session.update(self._decision(310.0, ObservationState.NO_FACE, EffectiveState.BREAK))
        summary = session.finish(311.0)

        self.assertEqual(summary.focus_seconds, 10.0)
        self.assertEqual(summary.absent_pending_seconds, 0.0)
        self.assertEqual(summary.break_seconds, 301.0)
        self.assertEqual(
            session.metrics.timeline_snapshot()[-1][1],
            EffectiveState.BREAK,
        )
        self.assertEqual(sum(bucket[EffectiveState.BREAK] for bucket in recorder.timeline_buckets), 301.0)

    def test_manual_break_does_not_reclassify_short_absence(self):
        session = SessionManager(recorder=MemoryRecorder())
        session.start()
        session.update(self._decision(0.0, ObservationState.NORMAL_VIEW, EffectiveState.FOCUS))
        session.update(self._decision(10.0, ObservationState.NO_FACE, EffectiveState.ABSENT_PENDING))
        session.toggle_break()
        session.update(self._decision(30.0, ObservationState.NO_FACE, EffectiveState.BREAK))
        summary = session.finish(31.0)

        self.assertEqual(summary.absent_pending_seconds, 20.0)
        self.assertEqual(summary.break_seconds, 1.0)

    @staticmethod
    def _decision(timestamp, raw_state, effective_state):
        return FocusDecision(
            timestamp=timestamp,
            raw_state=raw_state,
            effective_state=effective_state,
            reason="test",
        )


if __name__ == "__main__":
    unittest.main()
