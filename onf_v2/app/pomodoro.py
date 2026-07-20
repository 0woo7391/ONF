from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PomodoroPhase(str, Enum):
    IDLE = "idle"
    FOCUS = "focus"
    PAUSED = "paused"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    WAITING_NEXT = "waiting_next"
    COMPLETED = "completed"


@dataclass(frozen=True)
class PomodoroConfig:
    focus_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    cycles: int = 4
    auto_start_break: bool = True
    auto_start_next_focus: bool = False


@dataclass(frozen=True)
class PomodoroUpdate:
    phase: PomodoroPhase
    remaining_seconds: float
    cycle: int
    completed_cycles: int
    just_changed: bool = False
    previous_phase: PomodoroPhase = PomodoroPhase.IDLE


class PomodoroController:
    def __init__(self, config: Optional[PomodoroConfig] = None) -> None:
        self.config = config or PomodoroConfig()
        self.phase = PomodoroPhase.IDLE
        self.cycle = 1
        self.completed_cycles = 0
        self.started_at: Optional[float] = None
        self.duration_seconds = 0.0
        self.paused_remaining = 0.0
        self.paused_from: Optional[PomodoroPhase] = None

    @property
    def active(self) -> bool:
        return self.phase not in (PomodoroPhase.IDLE, PomodoroPhase.COMPLETED)

    @property
    def is_focus_phase(self) -> bool:
        return self.phase == PomodoroPhase.FOCUS

    @property
    def is_break_phase(self) -> bool:
        return self.phase in (
            PomodoroPhase.SHORT_BREAK,
            PomodoroPhase.LONG_BREAK,
            PomodoroPhase.WAITING_NEXT,
        )

    def configure(self, config: PomodoroConfig) -> None:
        if self.active:
            raise RuntimeError("Active Pomodoro cannot be reconfigured.")
        self.config = config

    def start(self, timestamp: float) -> PomodoroUpdate:
        self.cycle = 1
        self.completed_cycles = 0
        return self._begin(
            PomodoroPhase.FOCUS,
            self.config.focus_minutes * 60.0,
            timestamp,
            PomodoroPhase.IDLE,
        )

    def update(self, timestamp: float) -> PomodoroUpdate:
        remaining = self.remaining(timestamp)
        if self.phase in (
            PomodoroPhase.IDLE,
            PomodoroPhase.PAUSED,
            PomodoroPhase.WAITING_NEXT,
            PomodoroPhase.COMPLETED,
        ):
            return self._snapshot(remaining)
        if remaining > 0:
            return self._snapshot(remaining)

        previous = self.phase
        if previous == PomodoroPhase.FOCUS:
            self.completed_cycles += 1
            break_phase = (
                PomodoroPhase.LONG_BREAK
                if self.completed_cycles >= self.config.cycles
                else PomodoroPhase.SHORT_BREAK
            )
            break_minutes = (
                self.config.long_break_minutes
                if break_phase == PomodoroPhase.LONG_BREAK
                else self.config.short_break_minutes
            )
            if self.config.auto_start_break:
                return self._begin(
                    break_phase,
                    break_minutes * 60.0,
                    timestamp,
                    previous,
                )
            self.paused_from = break_phase
            self.paused_remaining = break_minutes * 60.0
            self.phase = PomodoroPhase.WAITING_NEXT
            self.started_at = None
            return self._snapshot(self.paused_remaining, True, previous)

        if previous == PomodoroPhase.LONG_BREAK:
            self.phase = PomodoroPhase.COMPLETED
            self.started_at = None
            return self._snapshot(0.0, True, previous)

        if self.config.auto_start_next_focus:
            self.cycle = min(self.config.cycles, self.completed_cycles + 1)
            return self._begin(
                PomodoroPhase.FOCUS,
                self.config.focus_minutes * 60.0,
                timestamp,
                previous,
            )

        self.phase = PomodoroPhase.WAITING_NEXT
        self.started_at = None
        self.paused_from = PomodoroPhase.FOCUS
        self.paused_remaining = self.config.focus_minutes * 60.0
        return self._snapshot(self.paused_remaining, True, previous)

    def start_next(self, timestamp: float) -> PomodoroUpdate:
        if self.phase != PomodoroPhase.WAITING_NEXT:
            return self.update(timestamp)
        target = self.paused_from or PomodoroPhase.FOCUS
        duration = self.paused_remaining
        if target == PomodoroPhase.FOCUS:
            self.cycle = min(self.config.cycles, self.completed_cycles + 1)
        self.paused_from = None
        self.paused_remaining = 0.0
        return self._begin(target, duration, timestamp, PomodoroPhase.WAITING_NEXT)

    def pause(self, timestamp: float) -> PomodoroUpdate:
        if self.phase not in (
            PomodoroPhase.FOCUS,
            PomodoroPhase.SHORT_BREAK,
            PomodoroPhase.LONG_BREAK,
        ):
            return self.update(timestamp)
        previous = self.phase
        self.paused_remaining = self.remaining(timestamp)
        self.paused_from = previous
        self.phase = PomodoroPhase.PAUSED
        self.started_at = None
        return self._snapshot(self.paused_remaining, True, previous)

    def resume(self, timestamp: float) -> PomodoroUpdate:
        if self.phase != PomodoroPhase.PAUSED or self.paused_from is None:
            return self.update(timestamp)
        target = self.paused_from
        duration = self.paused_remaining
        self.paused_from = None
        self.paused_remaining = 0.0
        return self._begin(target, duration, timestamp, PomodoroPhase.PAUSED)

    def skip_break(self, timestamp: float) -> PomodoroUpdate:
        if self.phase not in (
            PomodoroPhase.SHORT_BREAK,
            PomodoroPhase.LONG_BREAK,
            PomodoroPhase.WAITING_NEXT,
        ):
            return self.update(timestamp)
        previous = self.phase
        if previous == PomodoroPhase.LONG_BREAK or (
            previous == PomodoroPhase.WAITING_NEXT
            and self.completed_cycles >= self.config.cycles
        ):
            self.phase = PomodoroPhase.COMPLETED
            self.started_at = None
            return self._snapshot(0.0, True, previous)
        self.paused_from = PomodoroPhase.FOCUS
        self.paused_remaining = self.config.focus_minutes * 60.0
        self.phase = PomodoroPhase.WAITING_NEXT
        self.started_at = None
        return self.start_next(timestamp)

    def stop(self) -> None:
        self.phase = PomodoroPhase.IDLE
        self.cycle = 1
        self.completed_cycles = 0
        self.started_at = None
        self.duration_seconds = 0.0
        self.paused_remaining = 0.0
        self.paused_from = None

    def remaining(self, timestamp: float) -> float:
        if self.phase in (PomodoroPhase.PAUSED, PomodoroPhase.WAITING_NEXT):
            return self.paused_remaining
        if self.started_at is None:
            return 0.0
        return max(0.0, self.duration_seconds - max(0.0, timestamp - self.started_at))

    def progress(self, timestamp: float) -> float:
        if self.duration_seconds <= 0:
            return 0.0
        return min(1.0, max(0.0, self.remaining(timestamp) / self.duration_seconds))

    def _begin(
        self,
        phase: PomodoroPhase,
        duration_seconds: float,
        timestamp: float,
        previous: PomodoroPhase,
    ) -> PomodoroUpdate:
        self.phase = phase
        self.duration_seconds = max(0.0, duration_seconds)
        self.started_at = timestamp
        return self._snapshot(self.duration_seconds, True, previous)

    def _snapshot(
        self,
        remaining: float,
        just_changed: bool = False,
        previous: Optional[PomodoroPhase] = None,
    ) -> PomodoroUpdate:
        return PomodoroUpdate(
            phase=self.phase,
            remaining_seconds=max(0.0, remaining),
            cycle=self.cycle,
            completed_cycles=self.completed_cycles,
            just_changed=just_changed,
            previous_phase=previous or self.phase,
        )
