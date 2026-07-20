import unittest

from onf_v2.core.metrics import DurationAccumulator
from onf_v2.core.models import EffectiveState


class DurationAccumulatorTimelineTests(unittest.TestCase):
    def test_break_slot_is_not_reported_as_zero_focus(self):
        metrics = DurationAccumulator(timeline_slot_seconds=5.0)

        metrics.update(EffectiveState.FOCUS, 0.0)
        metrics.update(EffectiveState.BREAK, 5.0)
        metrics.update(EffectiveState.BREAK, 10.0)

        self.assertEqual(
            metrics.timeline_snapshot(),
            [
                (1.0, EffectiveState.FOCUS),
                (None, EffectiveState.BREAK),
            ],
        )

    def test_scored_slot_keeps_focus_ratio(self):
        metrics = DurationAccumulator(timeline_slot_seconds=5.0)

        metrics.update(EffectiveState.FOCUS, 0.0)
        metrics.update(EffectiveState.NON_FOCUS, 2.5)
        metrics.update(EffectiveState.FOCUS, 5.0)

        ratio, state = metrics.timeline_snapshot()[0]
        self.assertAlmostEqual(ratio or 0.0, 0.5)
        self.assertEqual(state, EffectiveState.FOCUS)

    def test_timeline_snapshot_can_limit_long_sessions(self):
        metrics = DurationAccumulator(timeline_slot_seconds=5.0)
        metrics.update(EffectiveState.FOCUS, 0.0)
        metrics.update(EffectiveState.FOCUS, 100.0)

        snapshot = metrics.timeline_snapshot(limit=3)

        self.assertEqual(len(snapshot), 3)
        self.assertTrue(all(state == EffectiveState.FOCUS for _, state in snapshot))


if __name__ == "__main__":
    unittest.main()
