from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from .models import AttentionEvent, EffectiveState, FocusDecision, SessionSummary


@dataclass
class DurationAccumulator:
    durations: Dict[EffectiveState, float] = field(
        default_factory=lambda: {state: 0.0 for state in EffectiveState}
    )
    last_timestamp: Optional[float] = None
    last_effective_state: Optional[EffectiveState] = None
    longest_focus_seconds: float = 0.0
    _focus_run_seconds: float = 0.0
    minute_buckets: List[Dict[EffectiveState, float]] = field(default_factory=list)
    timeline_slot_seconds: float = 5.0
    timeline_slots: List[Tuple[Optional[float], EffectiveState]] = field(default_factory=list)
    timeline_slot_buckets: List[Dict[EffectiveState, float]] = field(default_factory=list)
    _timeline_slot_elapsed: float = 0.0
    _timeline_slot_durations: Dict[EffectiveState, float] = field(
        default_factory=lambda: {state: 0.0 for state in EffectiveState}
    )
    task_id: Optional[int] = None
    task_title: str = ""
    task_spans: List[dict] = field(default_factory=list)

    def reset(self) -> None:
        self.durations = {state: 0.0 for state in EffectiveState}
        self.last_timestamp = None
        self.last_effective_state = None
        self.longest_focus_seconds = 0.0
        self._focus_run_seconds = 0.0
        self.minute_buckets.clear()
        self.timeline_slots.clear()
        self.timeline_slot_buckets.clear()
        self._timeline_slot_elapsed = 0.0
        self._timeline_slot_durations = {state: 0.0 for state in EffectiveState}
        self.task_id = None
        self.task_title = ""
        self.task_spans.clear()

    def update(self, state: EffectiveState, timestamp: float) -> None:
        if self.last_timestamp is None:
            self.last_timestamp = timestamp
            self.last_effective_state = state
            self.task_spans.append(self._new_task_span(timestamp))
            return
        if timestamp <= self.last_timestamp:
            return
        delta = timestamp - self.last_timestamp
        previous_state = self.last_effective_state or state
        self.durations[previous_state] += delta
        self.task_spans[-1]["durations"][previous_state] += delta
        self.task_spans[-1]["ended_at"] = timestamp
        self._add_to_minute_buckets(previous_state, delta)
        self._add_to_timeline_slots(previous_state, delta)
        if previous_state == EffectiveState.FOCUS:
            self._focus_run_seconds += delta
            self.longest_focus_seconds = max(
                self.longest_focus_seconds, self._focus_run_seconds
            )
        else:
            self._focus_run_seconds = 0.0
        self.last_timestamp = timestamp
        self.last_effective_state = state

    def _new_task_span(self, timestamp: float) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.task_title,
            "started_at": timestamp,
            "ended_at": timestamp,
            "durations": {state: 0.0 for state in EffectiveState},
        }

    def set_task(self, task_id: Optional[int], title: str, timestamp: float) -> bool:
        if self.last_timestamp is not None and timestamp < self.last_timestamp:
            return False
        if self.last_timestamp is not None:
            self.update(self.last_effective_state or EffectiveState.UNSCORED, timestamp)
        changed = task_id != self.task_id
        self.task_id = task_id
        self.task_title = title if task_id is not None else ""
        if self.task_spans:
            if changed:
                self.task_spans.append(self._new_task_span(timestamp))
            else:
                self.task_spans[-1]["title"] = self.task_title
        return True

    def task_records(self) -> List[dict]:
        return [
            {
                "task_id": span["task_id"],
                "title": span["title"],
                "study_seconds": study_seconds(span["durations"]),
                "focus_seconds": (
                    span["durations"][EffectiveState.FOCUS]
                    if span["durations"][EffectiveState.FOCUS] + span["durations"][EffectiveState.NON_FOCUS] > 0
                    else None
                ),
                "started_at": span["started_at"],
                "ended_at": span["ended_at"],
            }
            for span in self.task_spans
            if span["task_id"] is not None and study_seconds(span["durations"]) > 0
        ]

    def reclassify_recent_state(
        self,
        source: EffectiveState,
        target: EffectiveState,
        seconds: float,
    ) -> None:
        amount = min(max(0.0, seconds), self.durations[source])
        if amount <= 0.0:
            return
        self.durations[source] -= amount
        self.durations[target] += amount

        remaining = amount
        for span in reversed(self.task_spans):
            moved = min(span["durations"][source], remaining)
            span["durations"][source] -= moved
            span["durations"][target] += moved
            remaining -= moved
            if remaining <= 1e-6:
                break

        remaining = amount
        for bucket in reversed(self.minute_buckets):
            moved = min(bucket[source], remaining)
            bucket[source] -= moved
            bucket[target] += moved
            remaining -= moved
            if remaining <= 1e-6:
                break

        remaining = amount
        moved = min(self._timeline_slot_durations[source], remaining)
        self._timeline_slot_durations[source] -= moved
        self._timeline_slot_durations[target] += moved
        remaining -= moved
        for bucket in reversed(self.timeline_slot_buckets):
            moved = min(bucket[source], remaining)
            bucket[source] -= moved
            bucket[target] += moved
            remaining -= moved
            if remaining <= 1e-6:
                break
        self.timeline_slots = [
            self._timeline_slot_value(bucket)
            for bucket in self.timeline_slot_buckets
        ]

    def snapshot(
        self,
        timestamp: Optional[float] = None,
        started_at: Optional[float] = None,
    ) -> Dict[EffectiveState, float]:
        values = dict(self.durations)
        previous = self.last_timestamp if self.last_timestamp is not None else started_at
        if timestamp is not None and previous is not None:
            state = self.last_effective_state or EffectiveState.UNSCORED
            values[state] += max(0.0, timestamp - previous)
        return values

    def minute_snapshot(
        self, durations: Dict[EffectiveState, float]
    ) -> List[Dict[EffectiveState, float]]:
        buckets = [dict(bucket) for bucket in self.minute_buckets]
        for state in EffectiveState:
            pending = max(0.0, durations[state] - self.durations[state])
            if pending > 0:
                self._append_minute_duration(buckets, state, pending)
        return buckets

    def focus_ratio(self) -> float:
        focus = self.durations[EffectiveState.FOCUS]
        non_focus = self.durations[EffectiveState.NON_FOCUS]
        denominator = focus + non_focus
        return 0.0 if denominator <= 0 else focus / denominator

    def coverage_ratio(self) -> float:
        scored = self.durations[EffectiveState.FOCUS] + self.durations[EffectiveState.NON_FOCUS]
        unscored = (
            self.durations[EffectiveState.UNSCORED]
            + self.durations[EffectiveState.ABSENT_PENDING]
        )
        denominator = scored + unscored
        return 0.0 if denominator <= 0 else scored / denominator

    def _add_to_minute_buckets(self, state: EffectiveState, delta: float) -> None:
        self._append_minute_duration(self.minute_buckets, state, delta)

    @staticmethod
    def _append_minute_duration(
        buckets: List[Dict[EffectiveState, float]], state: EffectiveState, delta: float
    ) -> None:
        if not buckets:
            buckets.append({s: 0.0 for s in EffectiveState})
        remaining = delta
        while remaining > 0:
            bucket = buckets[-1]
            used = sum(bucket.values())
            room = max(0.0, 60.0 - used)
            if room <= 1e-6:
                buckets.append({s: 0.0 for s in EffectiveState})
                continue
            take = min(room, remaining)
            bucket[state] += take
            remaining -= take

    def timeline_snapshot(
        self, limit: Optional[int] = None
    ) -> List[Tuple[Optional[float], EffectiveState]]:
        if limit is not None and limit > 0:
            slots = list(self.timeline_slots[-limit:])
        else:
            slots = list(self.timeline_slots)
        if self._timeline_slot_elapsed > 0:
            slots.append(self._timeline_slot_value())
            if limit is not None and limit > 0:
                slots = slots[-limit:]
        return slots

    def _add_to_timeline_slots(self, state: EffectiveState, delta: float) -> None:
        remaining = delta
        while remaining > 0:
            room = max(0.0, self.timeline_slot_seconds - self._timeline_slot_elapsed)
            if room <= 1e-6:
                self._close_timeline_slot()
                continue
            take = min(room, remaining)
            self._timeline_slot_durations[state] += take
            self._timeline_slot_elapsed += take
            remaining -= take
            if self._timeline_slot_elapsed >= self.timeline_slot_seconds - 1e-6:
                self._close_timeline_slot()

    def _close_timeline_slot(self) -> None:
        bucket = dict(self._timeline_slot_durations)
        self.timeline_slot_buckets.append(bucket)
        self.timeline_slots.append(self._timeline_slot_value(bucket))
        self._timeline_slot_elapsed = 0.0
        self._timeline_slot_durations = {state: 0.0 for state in EffectiveState}

    def _timeline_slot_value(
        self,
        bucket: Optional[Dict[EffectiveState, float]] = None,
    ) -> Tuple[Optional[float], EffectiveState]:
        values = bucket if bucket is not None else self._timeline_slot_durations
        focus = values[EffectiveState.FOCUS]
        non_focus = values[EffectiveState.NON_FOCUS]
        scored = focus + non_focus
        break_seconds = values[EffectiveState.BREAK]
        unscored = (
            values[EffectiveState.UNSCORED]
            + values[EffectiveState.ABSENT_PENDING]
        )
        if break_seconds >= scored and break_seconds >= unscored and break_seconds > 0:
            return None, EffectiveState.BREAK
        if unscored > scored:
            return None, EffectiveState.UNSCORED
        if scored <= 0:
            return None, EffectiveState.UNSCORED
        state = EffectiveState.FOCUS if focus >= non_focus else EffectiveState.NON_FOCUS
        return focus / scored, state


@dataclass
class EventTracker:
    min_event_seconds: float = 0.5
    active_type: Optional[str] = None
    active_started_at: Optional[float] = None
    max_deviation: float = 0.0
    events: List[AttentionEvent] = field(default_factory=list)

    def reset(self) -> None:
        self.active_type = None
        self.active_started_at = None
        self.max_deviation = 0.0
        self.events.clear()

    def update(self, decision: FocusDecision) -> None:
        event_type = None
        if decision.effective_state == EffectiveState.NON_FOCUS:
            event_type = decision.raw_state.value
        deviation = self._deviation(decision)
        if event_type != self.active_type:
            self._close(decision.timestamp)
            self.active_type = event_type
            self.active_started_at = decision.timestamp if event_type else None
            self.max_deviation = deviation
            return
        self.max_deviation = max(self.max_deviation, deviation)

    def close(self, timestamp: float) -> None:
        self._close(timestamp)

    def _close(self, timestamp: float) -> None:
        if not self.active_type or self.active_started_at is None:
            return
        duration = max(0.0, timestamp - self.active_started_at)
        if duration >= self.min_event_seconds:
            self.events.append(
                AttentionEvent(
                    type=self.active_type,
                    started_at=self.active_started_at,
                    ended_at=timestamp,
                    duration=duration,
                    max_deviation=self.max_deviation,
                )
            )
        self.active_type = None
        self.active_started_at = None
        self.max_deviation = 0.0

    @staticmethod
    def _deviation(decision: FocusDecision) -> float:
        metrics = decision.metrics
        if metrics is None:
            return 0.0
        return max(
            abs(metrics.yaw_delta_deg),
            abs(metrics.pitch_delta_deg),
            abs(metrics.roll_delta_deg),
            abs(metrics.gaze_x_delta) * 100.0,
            abs(metrics.gaze_y_delta) * 100.0,
        )


def study_seconds(durations: Mapping[str, float]) -> float:
    return sum(
        durations.get(state, 0.0)
        for state in (
            EffectiveState.FOCUS,
            EffectiveState.NON_FOCUS,
            EffectiveState.UNSCORED,
            EffectiveState.ABSENT_PENDING,
        )
    )


def build_summary(
    started_at_wall: str,
    ended_at_wall: str,
    accumulator: DurationAccumulator,
    events: List[AttentionEvent],
    session_mode: str = "free",
    pomodoro_cycles_completed: int = 0,
    pomodoro_cycles_planned: int = 0,
    app_usage_seconds: Optional[Dict[str, float]] = None,
) -> SessionSummary:
    durations = accumulator.snapshot()
    return SessionSummary(
        started_at_wall=started_at_wall,
        ended_at_wall=ended_at_wall,
        focus_seconds=durations[EffectiveState.FOCUS],
        non_focus_seconds=durations[EffectiveState.NON_FOCUS],
        break_seconds=durations[EffectiveState.BREAK],
        unscored_seconds=durations[EffectiveState.UNSCORED],
        absent_pending_seconds=durations[EffectiveState.ABSENT_PENDING],
        focus_ratio=accumulator.focus_ratio(),
        coverage_ratio=accumulator.coverage_ratio(),
        longest_focus_seconds=accumulator.longest_focus_seconds,
        events=events,
        session_mode=session_mode,
        pomodoro_cycles_completed=pomodoro_cycles_completed,
        pomodoro_cycles_planned=pomodoro_cycles_planned,
        app_usage_seconds=dict(app_usage_seconds or {}),
    )
