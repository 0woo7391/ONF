from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from onf_v2.app.session_recorder import SessionRecorder
from onf_v2.core.metrics import DurationAccumulator, EventTracker, build_summary
from onf_v2.core.models import (
    AppState,
    EffectiveState,
    FocusDecision,
    ObservationState,
    SessionSummary,
)


@dataclass
class SessionManager:
    recorder: SessionRecorder = field(default_factory=SessionRecorder)
    metrics: DurationAccumulator = field(default_factory=DurationAccumulator)
    events: EventTracker = field(default_factory=EventTracker)
    app_state: AppState = AppState.PREVIEW
    manual_break: bool = False
    started_at_wall: Optional[str] = None
    ended_at_wall: Optional[str] = None
    summary: Optional[SessionSummary] = None
    session_mode: str = "free"
    pomodoro_cycles_completed: int = 0
    pomodoro_cycles_planned: int = 0
    task_id: Optional[int] = None
    _absence_pending_started_at: Optional[float] = None
    _started_at_monotonic: Optional[float] = None

    def start(
        self,
        session_mode: str = "free",
        pomodoro_cycles_planned: int = 0,
        task_id: Optional[int] = None,
        started_at_monotonic: Optional[float] = None,
        task_title: str = "",
    ) -> None:
        if self.app_state in (AppState.RUNNING, AppState.BREAK):
            raise RuntimeError("An active session must be finished before starting another.")
        self.metrics.reset()
        self.events.reset()
        self.manual_break = False
        self.started_at_wall = self.recorder.wall_now()
        self.ended_at_wall = None
        self.summary = None
        self.session_mode = session_mode
        self.pomodoro_cycles_completed = 0
        self.pomodoro_cycles_planned = pomodoro_cycles_planned
        self.task_id = task_id
        self.metrics.set_task(task_id, task_title, started_at_monotonic or 0.0)
        self._absence_pending_started_at = None
        self._started_at_monotonic = started_at_monotonic
        self.recorder.start(self.started_at_wall, task_id=task_id)
        self.app_state = AppState.RUNNING

    def toggle_break(self) -> None:
        if self.app_state not in (AppState.RUNNING, AppState.BREAK):
            return
        self.manual_break = not self.manual_break
        self.app_state = AppState.BREAK if self.manual_break else AppState.RUNNING

    def update(self, decision: FocusDecision) -> None:
        if self.app_state not in (AppState.RUNNING, AppState.BREAK):
            return
        if self.metrics.last_timestamp is None and self._started_at_monotonic is not None:
            if decision.timestamp < self._started_at_monotonic:
                return
            if decision.timestamp > self._started_at_monotonic:
                self.metrics.update(EffectiveState.UNSCORED, self._started_at_monotonic)
        elif self.metrics.last_timestamp is not None and decision.timestamp <= self.metrics.last_timestamp:
            boundary_state = EffectiveState.BREAK if self.manual_break else EffectiveState.UNSCORED
            if (
                decision.timestamp < self.metrics.last_timestamp
                or decision.effective_state != boundary_state
                or (self.metrics.last_effective_state == EffectiveState.BREAK) == self.manual_break
            ):
                return
            # A break button may share the last frame's timestamp without adding time.
            self.metrics.last_effective_state = boundary_state
        previous_state = self.metrics.last_effective_state
        pending_started_at = self._absence_pending_started_at
        self.metrics.update(decision.effective_state, decision.timestamp)
        if decision.effective_state == EffectiveState.ABSENT_PENDING:
            if pending_started_at is None:
                self._absence_pending_started_at = decision.timestamp
        elif (
            decision.effective_state == EffectiveState.BREAK
            and previous_state == EffectiveState.ABSENT_PENDING
            and pending_started_at is not None
            and decision.raw_state == ObservationState.NO_FACE
            and not self.manual_break
        ):
            self.metrics.reclassify_recent_state(
                EffectiveState.ABSENT_PENDING,
                EffectiveState.BREAK,
                decision.timestamp - pending_started_at,
            )
            self._absence_pending_started_at = None
        else:
            self._absence_pending_started_at = None
        self.events.update(decision)
        self.recorder.write_decision(decision)

    def finish(
        self,
        timestamp: float,
        app_usage_seconds: Optional[dict[str, float]] = None,
    ) -> Optional[SessionSummary]:
        if self.summary is not None:
            return self.summary
        if self.started_at_wall is None:
            return None
        if self.metrics.last_timestamp is None and self._started_at_monotonic is not None:
            self.metrics.update(EffectiveState.UNSCORED, self._started_at_monotonic)
        self.metrics.update(self.metrics.last_effective_state or decisionless_state(), timestamp)
        self.events.close(timestamp)
        self.ended_at_wall = self.recorder.wall_now()
        self.summary = build_summary(
            self.started_at_wall,
            self.ended_at_wall,
            self.metrics,
            list(self.events.events),
            session_mode=self.session_mode,
            pomodoro_cycles_completed=self.pomodoro_cycles_completed,
            pomodoro_cycles_planned=self.pomodoro_cycles_planned,
            app_usage_seconds=app_usage_seconds or {},
        )
        self.recorder.finish(
            self.summary,
            timeline_buckets=self.metrics.minute_buckets,
            task_records=self.metrics.task_records(),
        )
        self.app_state = AppState.RESULT
        self.manual_break = False
        return self.summary


def decisionless_state():
    from onf_v2.core.models import EffectiveState

    return EffectiveState.UNSCORED
