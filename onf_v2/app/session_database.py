from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator, List, Optional

from onf_v2.core.models import AttentionEvent, SessionSummary


@dataclass
class SessionRow:
    id: int
    started_at_wall: str
    ended_at_wall: str
    focus_seconds: float
    non_focus_seconds: float
    break_seconds: float
    unscored_seconds: float
    absent_pending_seconds: float
    focus_ratio: float
    coverage_ratio: float
    longest_focus_seconds: float
    event_count: int
    session_dir: str
    session_mode: str
    pomodoro_cycles_completed: int
    pomodoro_cycles_planned: int
    task_id: Optional[int]
    timeline_json: str
    task_attribution_version: int = 0


@dataclass
class StudyRecordRow:
    id: int
    session_id: Optional[int]
    task_id: Optional[int]
    title: str
    study_date: str
    study_seconds: float
    focus_seconds: Optional[float]
    source: str


@dataclass
class EventRow:
    type: str
    started_at: float
    ended_at: float
    duration: float
    max_deviation: float


@dataclass
class AppUsageRow:
    process_name: str
    duration_seconds: float


@dataclass
class PlannerSubjectRow:
    id: int
    name: str
    color: str


@dataclass
class PlannerTaskRow:
    id: int
    title: str
    subject_id: Optional[int]
    subject_name: Optional[str]
    subject_color: Optional[str]
    task_type: str
    planned_date: str
    deadline_date: Optional[str]
    estimated_minutes: int
    planned_start_minute: Optional[int]
    planned_end_minute: Optional[int]
    status: str
    completed_at: Optional[str]
    created_at: str
    actual_focus_seconds: float
    actual_study_seconds: float
    generated_field: Optional[str]
    fixed_schedule_id: Optional[int]
    actual_unmeasured_seconds: float = 0.0


@dataclass
class CalendarEventRow:
    id: int
    title: str
    event_date: str
    is_primary: bool
    created_at: str


class SessionDatabase:
    def __init__(self, path: str | Path = Path("sessions") / "onf.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def add_session(
        self,
        summary: SessionSummary,
        session_dir: Path,
        task_id: Optional[int] = None,
        timeline_buckets=None,
        task_records=None,
    ) -> int:
        with self._connection() as conn:
            if task_id is not None:
                task_exists = conn.execute(
                    "SELECT 1 FROM planner_tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if task_exists is None:
                    task_id = None
            cursor = conn.execute(
                """
                INSERT INTO sessions (
                    started_at_wall,
                    ended_at_wall,
                    focus_seconds,
                    non_focus_seconds,
                    break_seconds,
                    unscored_seconds,
                    absent_pending_seconds,
                    focus_ratio,
                    coverage_ratio,
                    longest_focus_seconds,
                    event_count,
                    session_dir
                    , session_mode
                    , pomodoro_cycles_completed
                    , pomodoro_cycles_planned
                    , task_id
                    , timeline_json
                    , task_attribution_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.started_at_wall,
                    summary.ended_at_wall,
                    summary.focus_seconds,
                    summary.non_focus_seconds,
                    summary.break_seconds,
                    summary.unscored_seconds,
                    summary.absent_pending_seconds,
                    summary.focus_ratio,
                    summary.coverage_ratio,
                    summary.longest_focus_seconds,
                    len(summary.events),
                    str(session_dir),
                    summary.session_mode,
                    summary.pomodoro_cycles_completed,
                    summary.pomodoro_cycles_planned,
                    task_id,
                    self._serialize_timeline(timeline_buckets),
                    int(task_records is not None),
                ),
            )
            session_id = int(cursor.lastrowid)
            allocated = 0.0
            for record in task_records or []:
                seconds = float(record["study_seconds"])
                focus = float(record["focus_seconds"]) if record["focus_seconds"] is not None else None
                if not math.isfinite(seconds) or seconds <= 0 or (focus is not None and (not math.isfinite(focus) or not 0 <= focus <= seconds)):
                    raise ValueError("Invalid measured task record")
                allocated += seconds
                task = conn.execute("SELECT id, title FROM planner_tasks WHERE id = ?", (record["task_id"],)).fetchone()
                conn.execute(
                    """
                    INSERT INTO study_records (session_id, task_id, title, study_date, study_seconds, focus_seconds, source)
                    VALUES (?, ?, ?, ?, ?, ?, 'tracked')
                    """,
                    (session_id, task["id"] if task else None, record.get("title") or (task["title"] if task else "Deleted task"),
                     summary.started_at_wall[:10], seconds, focus),
                )
            if allocated > summary.focus_seconds + summary.non_focus_seconds + summary.unscored_seconds + summary.absent_pending_seconds + 1e-6:
                raise ValueError("Task records exceed measured study time")
            conn.executemany(
                """
                INSERT INTO session_app_usage (session_id, process_name, duration_seconds)
                VALUES (?, ?, ?)
                """,
                [
                    (session_id, name.strip(), float(seconds))
                    for name, seconds in summary.app_usage_seconds.items()
                    if name.strip() and float(seconds) > 0.0
                ],
            )
            conn.executemany(
                """
                INSERT INTO events (
                    session_id,
                    type,
                    started_at,
                    ended_at,
                    duration,
                    max_deviation
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        event.type,
                        event.started_at,
                        event.ended_at,
                        event.duration,
                        event.max_deviation,
                    )
                    for event in summary.events
                ],
            )
            return session_id

    def list_sessions(self, limit: Optional[int] = 100) -> List[SessionRow]:
        limit_clause = "LIMIT ?" if limit is not None else ""
        parameters = (max(0, int(limit)),) if limit is not None else ()
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    id,
                    started_at_wall,
                    ended_at_wall,
                    focus_seconds,
                    non_focus_seconds,
                    break_seconds,
                    unscored_seconds,
                    absent_pending_seconds,
                    focus_ratio,
                    coverage_ratio,
                    longest_focus_seconds,
                    event_count,
                    session_dir
                    , session_mode
                    , pomodoro_cycles_completed
                    , pomodoro_cycles_planned
                    , task_id
                    , timeline_json
                    , task_attribution_version
                FROM sessions
                ORDER BY id DESC
                {limit_clause}
                """,
                parameters,
            ).fetchall()
        return [SessionRow(**dict(row)) for row in rows]

    def add_subject(self, name: str, color: str) -> int:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Subject name is required")
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO planner_subjects (name, color) VALUES (?, ?)",
                (clean_name, color),
            )
            row = conn.execute(
                "SELECT id FROM planner_subjects WHERE name = ?",
                (clean_name,),
            ).fetchone()
        return int(row["id"])

    def list_subjects(self) -> List[PlannerSubjectRow]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id, name, color FROM planner_subjects ORDER BY name"
            ).fetchall()
        return [PlannerSubjectRow(**dict(row)) for row in rows]

    def add_planner_task(
        self,
        title: str,
        subject_id: Optional[int],
        planned_date: str,
        deadline_date: Optional[str],
        estimated_minutes: int,
        task_type: str,
        planned_start_minute: Optional[int] = None,
        planned_end_minute: Optional[int] = None,
        generated_field: Optional[str] = None,
    ) -> int:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title is required")
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO planner_tasks (
                    title,
                    subject_id,
                    task_type,
                    planned_date,
                    deadline_date,
                    estimated_minutes,
                    planned_start_minute,
                    planned_end_minute,
                    generated_field,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    clean_title,
                    subject_id,
                    task_type,
                    planned_date,
                    deadline_date,
                    max(0, int(estimated_minutes)),
                    self._normalize_planned_start(planned_start_minute),
                    self._normalize_planned_start(planned_end_minute),
                    self._normalize_generated_field(generated_field),
                ),
            )
            return int(cursor.lastrowid)

    def list_planner_tasks(self) -> List[PlannerTaskRow]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    task.id,
                    task.title,
                    task.subject_id,
                    subject.name AS subject_name,
                    subject.color AS subject_color,
                    task.task_type,
                    task.planned_date,
                    task.deadline_date,
                    task.estimated_minutes,
                    task.planned_start_minute,
                    task.planned_end_minute,
                    task.status,
                    task.completed_at,
                    task.created_at,
                    COALESCE(actual.focus_seconds, 0) AS actual_focus_seconds,
                    COALESCE(actual.study_seconds, 0) AS actual_study_seconds,
                    COALESCE(actual.unmeasured_seconds, 0) AS actual_unmeasured_seconds,
                    task.generated_field,
                    task.fixed_schedule_id
                FROM planner_tasks AS task
                LEFT JOIN planner_subjects AS subject
                    ON subject.id = task.subject_id
                LEFT JOIN (
                    SELECT task_id, SUM(focus_seconds) AS focus_seconds,
                           SUM(study_seconds) AS study_seconds,
                           SUM(unmeasured_seconds) AS unmeasured_seconds
                    FROM (
                        SELECT task_id, focus_seconds,
                               focus_seconds + non_focus_seconds + unscored_seconds + absent_pending_seconds AS study_seconds,
                               0 AS unmeasured_seconds
                        FROM sessions WHERE task_attribution_version = 0
                        UNION ALL
                        SELECT task_id, COALESCE(focus_seconds, 0), study_seconds,
                               CASE WHEN focus_seconds IS NULL THEN study_seconds ELSE 0 END
                        FROM study_records
                    )
                    GROUP BY task_id
                ) AS actual ON actual.task_id = task.id
                GROUP BY task.id
                ORDER BY
                    task.completed_at IS NOT NULL,
                    task.planned_date,
                    task.deadline_date,
                    task.id
                """
            ).fetchall()
        return [PlannerTaskRow(**dict(row)) for row in rows]

    def set_planner_task_completed(self, task_id: int, completed: bool) -> None:
        self.set_planner_task_status(
            task_id,
            "completed" if completed else "pending",
        )

    def set_planner_task_status(self, task_id: int, status: str) -> None:
        if status not in {"pending", "completed", "deferred"}:
            raise ValueError("Invalid planner task status")
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE planner_tasks
                SET
                    status = ?,
                    completed_at = CASE
                        WHEN ? = 'completed' THEN datetime('now', 'localtime')
                        ELSE NULL
                    END
                WHERE id = ?
                """,
                (status, status, task_id),
            )

    def toggle_planner_task_fixed(self, task_id: int) -> bool:
        with self._connection() as conn:
            task = conn.execute(
                """
                SELECT id, title, subject_id, task_type, estimated_minutes,
                       planned_start_minute, planned_end_minute, generated_field,
                       fixed_schedule_id
                FROM planner_tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
            if task is None:
                return False
            fixed_id = task["fixed_schedule_id"]
            if fixed_id is not None:
                conn.execute(
                    "UPDATE planner_tasks SET fixed_schedule_id = NULL WHERE fixed_schedule_id = ?",
                    (fixed_id,),
                )
                conn.execute("DELETE FROM fixed_schedules WHERE id = ?", (fixed_id,))
                return False
            cursor = conn.execute(
                """
                INSERT INTO fixed_schedules (
                    title, subject_id, task_type, estimated_minutes,
                    planned_start_minute, planned_end_minute, generated_field
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["title"],
                    task["subject_id"],
                    task["task_type"],
                    task["estimated_minutes"],
                    task["planned_start_minute"],
                    task["planned_end_minute"],
                    task["generated_field"],
                ),
            )
            fixed_id = int(cursor.lastrowid)
            conn.execute(
                "UPDATE planner_tasks SET fixed_schedule_id = ? WHERE id = ?",
                (fixed_id, task_id),
            )
            return True

    def ensure_fixed_schedule_occurrences(self, planned_date: str) -> None:
        with self._connection() as conn:
            schedules = conn.execute(
                """
                SELECT id, title, subject_id, task_type, estimated_minutes,
                       planned_start_minute, planned_end_minute, generated_field
                FROM fixed_schedules
                ORDER BY id
                """
            ).fetchall()
            for schedule in schedules:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO planner_tasks (
                        title, subject_id, task_type, planned_date,
                        estimated_minutes, planned_start_minute,
                        planned_end_minute, generated_field, fixed_schedule_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        schedule["title"],
                        schedule["subject_id"],
                        schedule["task_type"],
                        planned_date,
                        schedule["estimated_minutes"],
                        schedule["planned_start_minute"],
                        schedule["planned_end_minute"],
                        schedule["generated_field"],
                        schedule["id"],
                    ),
                )

    def update_fixed_schedule_from_task(self, task_id: int) -> None:
        with self._connection() as conn:
            task = conn.execute(
                """
                SELECT title, subject_id, task_type, estimated_minutes,
                       planned_start_minute, planned_end_minute, generated_field,
                       fixed_schedule_id
                FROM planner_tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
            if task is None or task["fixed_schedule_id"] is None:
                return
            fixed_id = int(task["fixed_schedule_id"])
            values = (
                task["title"],
                task["subject_id"],
                task["task_type"],
                task["estimated_minutes"],
                task["planned_start_minute"],
                task["planned_end_minute"],
                task["generated_field"],
            )
            conn.execute(
                """
                UPDATE fixed_schedules
                SET title = ?, subject_id = ?, task_type = ?,
                    estimated_minutes = ?, planned_start_minute = ?,
                    planned_end_minute = ?, generated_field = ?
                WHERE id = ?
                """,
                (*values, fixed_id),
            )
            conn.execute(
                """
                UPDATE planner_tasks
                SET title = ?, subject_id = ?, task_type = ?,
                    estimated_minutes = ?, planned_start_minute = ?,
                    planned_end_minute = ?, generated_field = ?
                WHERE fixed_schedule_id = ? AND status != 'completed' AND id != ?
                """,
                (*values, fixed_id, task_id),
            )

    def reschedule_planner_task(self, task_id: int, planned_date: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE planner_tasks SET planned_date = ? WHERE id = ?",
                (planned_date, task_id),
            )

    def set_planner_task_time(
        self,
        task_id: int,
        planned_start_minute: Optional[int],
        estimated_minutes: int,
        planned_end_minute: Optional[int] = None,
        generated_field: Optional[str] = None,
    ) -> None:
        start = self._normalize_planned_start(planned_start_minute)
        duration = max(0, int(estimated_minutes))
        end = self._normalize_planned_start(planned_end_minute)
        if end is None and start is not None and duration > 0:
            end = (start + duration) % (24 * 60)
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE planner_tasks
                SET
                    planned_start_minute = ?,
                    estimated_minutes = ?,
                    planned_end_minute = ?,
                    generated_field = ?
                WHERE id = ?
                """,
                (
                    start,
                    duration,
                    end,
                    self._normalize_generated_field(generated_field),
                    task_id,
                ),
            )

    def update_planner_task(
        self,
        task_id: int,
        title: str,
        subject_id: Optional[int],
        planned_date: str,
        deadline_date: Optional[str],
        estimated_minutes: int,
        task_type: str,
    ) -> None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title is required")
        with self._connection() as conn:
            conn.execute(
                """
                UPDATE planner_tasks
                SET
                    title = ?,
                    subject_id = ?,
                    planned_date = ?,
                    deadline_date = ?,
                    estimated_minutes = ?,
                    task_type = ?
                WHERE id = ?
                """,
                (
                    clean_title,
                    subject_id,
                    planned_date,
                    deadline_date,
                    max(0, int(estimated_minutes)),
                    task_type,
                    task_id,
                ),
            )

    def update_planner_task_title(self, task_id: int, title: str) -> None:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title is required")
        with self._connection() as conn:
            conn.execute(
                "UPDATE planner_tasks SET title = ? WHERE id = ?",
                (clean_title, task_id),
            )

    @staticmethod
    def _normalize_planned_start(value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        return min(1439, max(0, int(value)))

    @staticmethod
    def _normalize_generated_field(value: Optional[str]) -> Optional[str]:
        return value if value in {"start", "end", "duration"} else None

    def delete_planner_task(self, task_id: int) -> None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT fixed_schedule_id FROM planner_tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            if row is not None and row["fixed_schedule_id"] is not None:
                fixed_id = int(row["fixed_schedule_id"])
                conn.execute(
                    "UPDATE planner_tasks SET fixed_schedule_id = NULL WHERE fixed_schedule_id = ?",
                    (fixed_id,),
                )
                conn.execute("DELETE FROM fixed_schedules WHERE id = ?", (fixed_id,))
            conn.execute(
                "UPDATE sessions SET task_id = NULL WHERE task_id = ?",
                (task_id,),
            )
            conn.execute("DELETE FROM planner_tasks WHERE id = ?", (task_id,))
            conn.execute("UPDATE study_records SET task_id = NULL WHERE task_id = ?", (task_id,))

    def list_study_records(self, study_date: Optional[str] = None) -> List[StudyRecordRow]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM study_records " + ("WHERE study_date = ? " if study_date else "") + "ORDER BY id DESC",
                (study_date,) if study_date else (),
            ).fetchall()
        return [StudyRecordRow(**dict(row)) for row in rows]

    def remaining_study_seconds(self, session_id: int) -> float:
        with self._connection() as conn:
            return self._remaining_study_seconds(conn, session_id)

    @staticmethod
    def _remaining_study_seconds(conn, session_id: int, exclude_id: Optional[int] = None) -> float:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise ValueError("측정 기록을 찾을 수 없습니다.")
        if row["task_attribution_version"] == 0 and row["task_id"] is not None:
            return 0.0
        total = row["focus_seconds"] + row["non_focus_seconds"] + row["unscored_seconds"] + row["absent_pending_seconds"]
        used = conn.execute(
            "SELECT COALESCE(SUM(study_seconds), 0) FROM study_records WHERE session_id = ? AND (? IS NULL OR id != ?)",
            (session_id, exclude_id, exclude_id),
        ).fetchone()[0]
        return max(0.0, total - used)

    def save_study_record(
        self, study_date: str, title: str, seconds: float,
        task_id: Optional[int] = None, session_id: Optional[int] = None,
        record_id: Optional[int] = None,
    ) -> int:
        study_date = date.fromisoformat(study_date).isoformat()
        seconds = float(seconds)
        title = title.strip()
        if not title:
            raise ValueError("공부한 내용을 입력하세요.")
        if not math.isfinite(seconds) or not 0 < seconds <= 86400:
            raise ValueError("공부시간은 0분 초과, 24시간 이하로 입력하세요.")
        source = "allocated" if session_id is not None else "manual"
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if task_id is not None and conn.execute("SELECT 1 FROM planner_tasks WHERE id = ?", (task_id,)).fetchone() is None:
                raise ValueError("연결할 계획이 삭제되었습니다. 다른 항목을 선택하세요.")
            if record_id is not None:
                old = conn.execute("SELECT source FROM study_records WHERE id = ?", (record_id,)).fetchone()
                if old is None or old["source"] == "tracked" or old["source"] != source:
                    raise ValueError("자동 측정한 항목 기록은 직접 수정할 수 없습니다.")
            if session_id is not None and seconds > self._remaining_study_seconds(conn, session_id, record_id) + 1e-6:
                raise ValueError("아직 연결하지 않은 측정 시간을 초과했습니다.")
            values = (session_id, task_id, title, study_date, seconds, source)
            if record_id is None:
                cursor = conn.execute(
                    "INSERT INTO study_records (session_id, task_id, title, study_date, study_seconds, source) VALUES (?, ?, ?, ?, ?, ?)",
                    values,
                )
                return int(cursor.lastrowid)
            conn.execute(
                "UPDATE study_records SET session_id = ?, task_id = ?, title = ?, study_date = ?, study_seconds = ?, source = ? WHERE id = ?",
                (*values, record_id),
            )
            return record_id

    def delete_study_record(self, record_id: int) -> None:
        with self._connection() as conn:
            row = conn.execute("SELECT source FROM study_records WHERE id = ?", (record_id,)).fetchone()
            if row is not None and row["source"] == "tracked":
                raise ValueError("자동 측정한 기록은 측정 세션과 함께 보존됩니다.")
            conn.execute("DELETE FROM study_records WHERE id = ?", (record_id,))

    def add_calendar_event(
        self,
        title: str,
        event_date: str,
        is_primary: bool = False,
    ) -> int:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Calendar event title is required")
        with self._connection() as conn:
            if is_primary:
                conn.execute("UPDATE calendar_events SET is_primary = 0")
            cursor = conn.execute(
                """
                INSERT INTO calendar_events (title, event_date, is_primary)
                VALUES (?, ?, ?)
                """,
                (clean_title, event_date, int(is_primary)),
            )
            return int(cursor.lastrowid)

    def list_calendar_events(self) -> List[CalendarEventRow]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, event_date, is_primary, created_at
                FROM calendar_events
                ORDER BY event_date, id
                """
            ).fetchall()
        return [
            CalendarEventRow(
                id=int(row["id"]),
                title=str(row["title"]),
                event_date=str(row["event_date"]),
                is_primary=bool(row["is_primary"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def set_primary_calendar_event(self, event_id: Optional[int]) -> None:
        with self._connection() as conn:
            conn.execute("UPDATE calendar_events SET is_primary = 0")
            if event_id is not None:
                conn.execute(
                    "UPDATE calendar_events SET is_primary = 1 WHERE id = ?",
                    (int(event_id),),
                )

    def delete_calendar_event(self, event_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM calendar_events WHERE id = ?", (int(event_id),))

    def list_events(self, session_id: int) -> List[EventRow]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT type, started_at, ended_at, duration, max_deviation
                FROM events
                WHERE session_id = ?
                ORDER BY started_at
                """,
                (session_id,),
            ).fetchall()
        return [EventRow(**dict(row)) for row in rows]

    def list_app_usage(self, session_ids: List[int]) -> List[AppUsageRow]:
        ids = tuple(dict.fromkeys(int(session_id) for session_id in session_ids))
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        with self._connection() as conn:
            rows = conn.execute(
                f"""
                SELECT process_name, SUM(duration_seconds) AS duration_seconds
                FROM session_app_usage
                WHERE session_id IN ({placeholders})
                GROUP BY process_name
                ORDER BY duration_seconds DESC, process_name
                """,
                ids,
            ).fetchall()
        return [AppUsageRow(**dict(row)) for row in rows]

    def delete_session(self, session_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM study_records WHERE session_id = ?", (session_id,))
            conn.execute(
                "DELETE FROM session_app_usage WHERE session_id = ?",
                (session_id,),
            )
            conn.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def stats_text(self) -> str:
        with self._connection() as conn:
            session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            last_session = conn.execute(
                "SELECT started_at_wall FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
        last = last_session[0] if last_session else "-"
        return (
            f"DB path: {self.path}\n"
            f"Sessions: {session_count}\n"
            f"Events: {event_count}\n"
            f"Latest session: {last}"
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _serialize_timeline(timeline_buckets) -> str:
        serialized = []
        for bucket in timeline_buckets or []:
            values = {}
            for state, seconds in bucket.items():
                key = getattr(state, "value", str(state))
                if seconds > 0:
                    values[key] = float(seconds)
            serialized.append(values)
        return json.dumps(serialized, ensure_ascii=True, separators=(",", ":"))

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at_wall TEXT NOT NULL,
                    ended_at_wall TEXT NOT NULL,
                    focus_seconds REAL NOT NULL,
                    non_focus_seconds REAL NOT NULL,
                    break_seconds REAL NOT NULL,
                    unscored_seconds REAL NOT NULL,
                    absent_pending_seconds REAL NOT NULL,
                    focus_ratio REAL NOT NULL,
                    coverage_ratio REAL NOT NULL,
                    longest_focus_seconds REAL NOT NULL,
                    event_count INTEGER NOT NULL,
                    session_dir TEXT NOT NULL
                    , session_mode TEXT NOT NULL DEFAULT 'free'
                    , pomodoro_cycles_completed INTEGER NOT NULL DEFAULT 0
                    , pomodoro_cycles_planned INTEGER NOT NULL DEFAULT 0
                    , task_id INTEGER
                    , timeline_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    ended_at REAL NOT NULL,
                    duration REAL NOT NULL,
                    max_deviation REAL NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_app_usage (
                    session_id INTEGER NOT NULL,
                    process_name TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS planner_subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    task_id INTEGER,
                    title TEXT NOT NULL,
                    study_date TEXT NOT NULL,
                    study_seconds REAL NOT NULL CHECK(study_seconds > 0),
                    focus_seconds REAL,
                    source TEXT NOT NULL CHECK(source IN ('tracked', 'allocated', 'manual')),
                    FOREIGN KEY(session_id) REFERENCES sessions(id),
                    FOREIGN KEY(task_id) REFERENCES planner_tasks(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS planner_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject_id INTEGER,
                    task_type TEXT NOT NULL DEFAULT 'study',
                    planned_date TEXT NOT NULL,
                    deadline_date TEXT,
                    estimated_minutes INTEGER NOT NULL DEFAULT 0,
                    planned_start_minute INTEGER,
                    planned_end_minute INTEGER,
                    generated_field TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    completed_at TEXT,
                    fixed_schedule_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY(subject_id) REFERENCES planner_subjects(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fixed_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject_id INTEGER,
                    task_type TEXT NOT NULL DEFAULT 'study',
                    estimated_minutes INTEGER NOT NULL DEFAULT 0,
                    planned_start_minute INTEGER,
                    planned_end_minute INTEGER,
                    generated_field TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY(subject_id) REFERENCES planner_subjects(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    is_primary INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
            }
            migrations = {
                "session_mode": "TEXT NOT NULL DEFAULT 'free'",
                "pomodoro_cycles_completed": "INTEGER NOT NULL DEFAULT 0",
                "pomodoro_cycles_planned": "INTEGER NOT NULL DEFAULT 0",
                "task_id": "INTEGER",
                "timeline_json": "TEXT NOT NULL DEFAULT '[]'",
                "task_attribution_version": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, definition in migrations.items():
                if column not in columns:
                    conn.execute(
                        f"ALTER TABLE sessions ADD COLUMN {column} {definition}"
                    )
            planner_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(planner_tasks)"
                ).fetchall()
            }
            planner_migrations = {
                "planned_start_minute": "INTEGER",
                "planned_end_minute": "INTEGER",
                "status": "TEXT NOT NULL DEFAULT 'pending'",
                "generated_field": "TEXT",
                "fixed_schedule_id": "INTEGER",
            }
            for column, definition in planner_migrations.items():
                if column not in planner_columns:
                    conn.execute(
                        f"ALTER TABLE planner_tasks ADD COLUMN {column} {definition}"
                    )
            fixed_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(fixed_schedules)"
                ).fetchall()
            }
            if "generated_field" not in fixed_columns:
                conn.execute(
                    "ALTER TABLE fixed_schedules ADD COLUMN generated_field TEXT"
                )
            conn.execute(
                """
                UPDATE planner_tasks
                SET planned_end_minute =
                    (planned_start_minute + estimated_minutes) % 1440
                WHERE planned_end_minute IS NULL
                    AND planned_start_minute IS NOT NULL
                    AND estimated_minutes > 0
                """
            )
            conn.execute(
                """
                UPDATE planner_tasks
                SET status = 'completed'
                WHERE completed_at IS NOT NULL AND status = 'pending'
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_task_id ON sessions(task_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_study_records_session ON study_records(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_study_records_task ON study_records(task_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at_wall)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_planner_tasks_planned_date "
                "ON planner_tasks(planned_date)"
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_planner_fixed_occurrence
                ON planner_tasks(fixed_schedule_id, planned_date)
                WHERE fixed_schedule_id IS NOT NULL
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_calendar_events_date "
                "ON calendar_events(event_date)"
            )
