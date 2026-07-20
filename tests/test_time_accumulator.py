import unittest

from onf_v2.core.metrics import DurationAccumulator
from onf_v2.core.models import EffectiveState


class DurationAccumulatorTest(unittest.TestCase):
    def test_accumulates_elapsed_time_by_previous_state(self):
        acc = DurationAccumulator()
        acc.update(EffectiveState.FOCUS, 10.0)
        acc.update(EffectiveState.NON_FOCUS, 12.5)
        acc.update(EffectiveState.UNSCORED, 15.0)

        self.assertAlmostEqual(acc.durations[EffectiveState.FOCUS], 2.5)
        self.assertAlmostEqual(acc.durations[EffectiveState.NON_FOCUS], 2.5)
        self.assertAlmostEqual(acc.focus_ratio(), 0.5)
        self.assertAlmostEqual(acc.coverage_ratio(), 1.0)

    def test_coverage_excludes_break_and_tracks_unscored(self):
        acc = DurationAccumulator()
        acc.update(EffectiveState.FOCUS, 0.0)
        acc.update(EffectiveState.UNSCORED, 10.0)
        acc.update(EffectiveState.BREAK, 15.0)
        acc.update(EffectiveState.NON_FOCUS, 25.0)

        self.assertAlmostEqual(acc.durations[EffectiveState.FOCUS], 10.0)
        self.assertAlmostEqual(acc.durations[EffectiveState.UNSCORED], 5.0)
        self.assertAlmostEqual(acc.durations[EffectiveState.BREAK], 10.0)
        self.assertAlmostEqual(acc.coverage_ratio(), 10.0 / 15.0)

    def test_absence_pending_reduces_measurement_coverage(self):
        acc = DurationAccumulator()
        acc.update(EffectiveState.FOCUS, 0.0)
        acc.update(EffectiveState.ABSENT_PENDING, 10.0)
        acc.update(EffectiveState.UNSCORED, 15.0)

        self.assertAlmostEqual(acc.durations[EffectiveState.FOCUS], 10.0)
        self.assertAlmostEqual(
            acc.durations[EffectiveState.ABSENT_PENDING],
            5.0,
        )
        self.assertAlmostEqual(acc.coverage_ratio(), 10.0 / 15.0)


if __name__ == "__main__":
    unittest.main()
