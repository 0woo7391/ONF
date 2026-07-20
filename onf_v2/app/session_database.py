from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
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


@dataclass
class EventRow:
    type: str
    started_at: float
    ended_at: float
    duration: float
    max_deviation: float


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
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )
            session_id = int(cursor.lastrowid)
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
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
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
                    COALESCE(SUM(session.focus_seconds), 0) AS actual_focus_seconds,
                    COALESCE(
                        SUM(session.focus_seconds + session.non_focus_seconds),
                        0
                    ) AS actual_study_seconds
                FROM planner_tasks AS task
                LEFT JOIN planner_subjects AS subject
                    ON subject.id = task.subject_id
                LEFT JOIN sessions AS session
                    ON session.task_id = task.id
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
                    planned_end_minute = ?
                WHERE id = ?
                """,
                (
                    start,
                    duration,
                    end,
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

    def delete_planner_task(self, task_id: int) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE sessions SET task_id = NULL WHERE task_id = ?",
                (task_id,),
            )
            conn.execute("DELETE FROM planner_tasks WHERE id = ?", (task_id,))

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

    def delete_session(self, session_id: int) -> None:
        with self._connection() as conn:
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
                CREATE TABLE IF NOT EXISTS planner_subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    color TEXT NOT NULL
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
                    status TEXT NOT NULL DEFAULT 'pending',
                    completed_at TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY(subject_id) REFERENCES planner_subjects(id)
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
            }
            for column, definition in planner_migrations.items():
                if column not in planner_columns:
                    conn.execute(
                        f"ALTER TABLE planner_tasks ADD COLUMN {column} {definition}"
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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at_wall)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_planner_tasks_planned_date "
                "ON planner_tasks(planned_date)"
            )
