import unittest

from onf_v2.core.focus_policy import FocusPolicy
from onf_v2.core.models import EffectiveState, Mode, ObservationState, RelativeMetrics


def metrics(**kwargs):
    base = dict(
        timestamp=0.0,
        yaw_delta_deg=0.0,
        pitch_delta_deg=0.0,
        roll_delta_deg=0.0,
        gaze_x_delta=0.0,
        gaze_y_delta=0.0,
        left_eye_open_norm=1.0,
        right_eye_open_norm=1.0,
        face_scale_delta=0.0,
        confidence=0.95,
    )
    base.update(kwargs)
    return RelativeMetrics(**base)


class FocusPolicyTest(unittest.TestCase):
    def test_classifies_normal_view_as_focus(self):
        policy = FocusPolicy(mode=Mode.NORMAL)
        raw = policy.classify_metrics(metrics())
        decision = policy.decide(raw, 0.0)

        self.assertEqual(raw, ObservationState.NORMAL_VIEW)
        self.assertEqual(decision.effective_state, EffectiveState.FOCUS)

    def test_classifies_gaze_away_after_stabilization(self):
        policy = FocusPolicy(mode=Mode.NORMAL)
        raw = policy.classify_metrics(metrics(gaze_x_delta=0.30))

        first = policy.decide(raw, 0.0)
        second = policy.decide(raw, 0.8)

        self.assertEqual(first.effective_state, EffectiveState.UNSCORED)
        self.assertEqual(second.raw_state, ObservationState.GAZE_AWAY)
        self.assertEqual(second.effective_state, EffectiveState.NON_FOCUS)

    def test_manual_break_overrides_raw_state(self):
        policy = FocusPolicy(mode=Mode.NORMAL)
        decision = policy.decide(ObservationState.NORMAL_VIEW, 1.0, manual_break=True)

        self.assertEqual(decision.effective_state, EffectiveState.BREAK)

    def test_gaze_away_uses_tighter_exit_threshold_until_recovered(self):
        policy = FocusPolicy(mode=Mode.NORMAL)
        borderline = metrics(gaze_x_delta=0.16)

        self.assertEqual(
            policy.classify_metrics(borderline),
            ObservationState.NORMAL_VIEW,
        )
        policy.stabilizer.current = ObservationState.GAZE_AWAY
        self.assertEqual(
            policy.classify_metrics(borderline),
            ObservationState.GAZE_AWAY,
        )

    def test_processing_error_interrupts_focus_without_delay(self):
        policy = FocusPolicy()
        policy.decide(ObservationState.NORMAL_VIEW, 0.0)

        error = policy.decide(ObservationState.PROCESSING_ERROR, 0.2)
        returning = policy.decide(ObservationState.NORMAL_VIEW, 0.3)
        recovered = policy.decide(ObservationState.NORMAL_VIEW, 0.7)

        self.assertEqual(error.effective_state, EffectiveState.UNSCORED)
        self.assertEqual(returning.effective_state, EffectiveState.UNSCORED)
        self.assertEqual(recovered.effective_state, EffectiveState.FOCUS)

    def test_alternating_head_and_gaze_keep_away_start_time(self):
        policy = FocusPolicy()
        policy.decide(ObservationState.NORMAL_VIEW, 0.0)
        states = (
            ObservationState.GAZE_AWAY,
            ObservationState.HEAD_SIDE,
            ObservationState.GAZE_AWAY,
            ObservationState.HEAD_SIDE,
            ObservationState.GAZE_AWAY,
        )
        decisions = [
            policy.decide(state, 0.2 * index)
            for index, state in enumerate(states, start=1)
        ]

        self.assertTrue(all(d.effective_state == EffectiveState.FOCUS for d in decisions[:-1]))
        self.assertEqual(decisions[-1].effective_state, EffectiveState.NON_FOCUS)

    def test_eyes_closed_requires_its_own_duration_after_gaze_away(self):
        policy = FocusPolicy()
        policy.decide(ObservationState.NORMAL_VIEW, 0.0)
        policy.decide(ObservationState.GAZE_AWAY, 0.2)

        policy.decide(ObservationState.EYES_CLOSED, 0.8)
        early = policy.decide(ObservationState.EYES_CLOSED, 1.5)
        confirmed = policy.decide(ObservationState.EYES_CLOSED, 1.9)

        self.assertEqual(early.effective_state, EffectiveState.FOCUS)
        self.assertEqual(confirmed.effective_state, EffectiveState.NON_FOCUS)

    def test_head_down_keeps_its_longer_entry_time_when_reason_changes(self):
        policy = FocusPolicy()
        policy.decide(ObservationState.NORMAL_VIEW, 0.0)
        policy.decide(ObservationState.HEAD_DOWN, 0.2)
        policy.decide(ObservationState.GAZE_AWAY, 0.8)

        early = policy.decide(ObservationState.GAZE_AWAY, 1.0)
        confirmed = policy.decide(ObservationState.GAZE_AWAY, 1.2)

        self.assertEqual(early.effective_state, EffectiveState.FOCUS)
        self.assertEqual(confirmed.effective_state, EffectiveState.NON_FOCUS)


if __name__ == "__main__":
    unittest.main()
