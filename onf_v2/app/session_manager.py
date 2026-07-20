from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from onf_v2.app.session_recorder import SessionRecorder
from onf_v2.core.metrics import DurationAccumulator, EventTracker, build_summary
from onf_v2.core.models import AppState, FocusDecision, SessionSummary


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

    def start(
        self,
        session_mode: str = "free",
        pomodoro_cycles_planned: int = 0,
        task_id: Optional[int] = None,
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
        self.metrics.update(decision.effective_state, decision.timestamp)
        self.events.update(decision)
        self.recorder.write_decision(decision)

    def finish(self, timestamp: float) -> Optional[SessionSummary]:
        if self.summary is not None:
            return self.summary
        if self.started_at_wall is None:
            return None
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
        )
        self.recorder.finish(
            self.summary,
            timeline_buckets=self.metrics.minute_buckets,
        )
        self.app_state = AppState.RESULT
        self.manual_break = False
        return self.summary


def decisionless_state():
    from onf_v2.core.models import EffectiveState

    return EffectiveState.UNSCORED
