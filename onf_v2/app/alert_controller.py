from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from onf_v2.core.models import EffectiveState


@dataclass(frozen=True)
class AttentionAlertUpdate:
    active: bool
    just_triggered: bool
    just_cleared: bool
    elapsed_seconds: float


@dataclass
class AttentionAlertController:
    threshold_seconds: float = 60.0
    recovery_seconds: float = 3.0
    non_focus_started_at: Optional[float] = None
    recovery_started_at: Optional[float] = None
    alerted: bool = False

    def reset(self) -> None:
        self.non_focus_started_at = None
        self.recovery_started_at = None
        self.alerted = False

    def update(self, state: EffectiveState, timestamp: float) -> AttentionAlertUpdate:
        if state == EffectiveState.NON_FOCUS:
            self.recovery_started_at = None
            if self.non_focus_started_at is None:
                self.non_focus_started_at = timestamp
            elapsed = max(0.0, timestamp - self.non_focus_started_at)
            just_triggered = not self.alerted and elapsed >= self.threshold_seconds
            if just_triggered:
                self.alerted = True
            return AttentionAlertUpdate(self.alerted, just_triggered, False, elapsed)

        if state == EffectiveState.FOCUS and self.non_focus_started_at is not None:
            if self.recovery_started_at is None:
                self.recovery_started_at = timestamp
            recovered = timestamp - self.recovery_started_at >= self.recovery_seconds
            elapsed = max(0.0, timestamp - self.non_focus_started_at)
            was_active = self.alerted
            if recovered:
                self.reset()
                return AttentionAlertUpdate(False, False, was_active, 0.0)
            return AttentionAlertUpdate(self.alerted, False, False, elapsed)

        was_active = self.alerted
        self.reset()
        return AttentionAlertUpdate(False, False, was_active, 0.0)
