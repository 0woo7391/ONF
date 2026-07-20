from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BreakTimerUpdate:
    remaining_seconds: float
    expired: bool
    just_expired: bool


@dataclass
class BreakTimer:
    duration_seconds: float = 5 * 60
    started_at: Optional[float] = None
    expired_notified: bool = False

    @property
    def active(self) -> bool:
        return self.started_at is not None

    def start(self, timestamp: float) -> None:
        self.started_at = timestamp
        self.expired_notified = False

    def stop(self) -> None:
        self.started_at = None
        self.expired_notified = False

    def extend(self, seconds: float, timestamp: Optional[float] = None) -> None:
        if not self.active:
            return
        extension = max(0.0, seconds)
        if timestamp is not None and self.started_at is not None:
            elapsed = max(0.0, timestamp - self.started_at)
            if elapsed >= self.duration_seconds:
                self.started_at = timestamp
                self.duration_seconds = extension
                self.expired_notified = False
                return
        self.duration_seconds += extension
        self.expired_notified = False

    def update(self, timestamp: float) -> BreakTimerUpdate:
        if self.started_at is None:
            return BreakTimerUpdate(self.duration_seconds, False, False)
        elapsed = max(0.0, timestamp - self.started_at)
        remaining = max(0.0, self.duration_seconds - elapsed)
        expired = remaining <= 0.0
        just_expired = expired and not self.expired_notified
        if just_expired:
            self.expired_notified = True
        return BreakTimerUpdate(remaining, expired, just_expired)
