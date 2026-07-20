from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, TextIO

from PIL import Image, ImageDraw, ImageFont

from onf_v2.app.session_database import SessionDatabase
from onf_v2.core.models import AttentionEvent, FocusDecision, SessionSummary


class SessionRecorder:
    def __init__(self, root: str = "sessions") -> None:
        self.root = Path(root)
        self.session_dir: Optional[Path] = None
        self.raw_path: Optional[Path] = None
        self.events_path: Optional[Path] = None
        self.database = SessionDatabase(self.root / "onf.sqlite3")
        self._raw_file: Optional[TextIO] = None
        self._raw_writer = None
        self._rows_since_flush = 0
        self.task_id: Optional[int] = None

    def start(self, started_at_wall: str, task_id: Optional[int] = None) -> None:
        self._close_raw_file()
        self.task_id = task_id
        safe_name = started_at_wall.replace(":", "").replace(" ", "_")
        self.session_dir = self.root / safe_name
        suffix = 2
        while self.session_dir.exists():
            self.session_dir = self.root / f"{safe_name}_{suffix}"
            suffix += 1
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.session_dir / "observations.csv"
        self.events_path = self.session_dir / "events.csv"
        self._raw_file = self.raw_path.open("w", newline="", encoding="utf-8")
        self._raw_writer = csv.writer(self._raw_file)
        self._raw_writer.writerow(
            [
                "timestamp",
                "raw_state",
                "effective_state",
                "reason",
                "confidence",
                "yaw_delta_deg",
                "pitch_delta_deg",
                "roll_delta_deg",
                "gaze_x_delta",
                "gaze_y_delta",
                "left_eye_open_norm",
                "right_eye_open_norm",
                "face_scale_delta",
            ]
        )
        self._raw_file.flush()
        self._rows_since_flush = 0

    def write_decision(self, decision: FocusDecision) -> None:
        if self._raw_writer is None:
            return
        metrics = decision.metrics
        row = [
            round(decision.timestamp, 3),
            decision.raw_state.value,
            decision.effective_state.value,
            decision.reason,
            round(decision.confidence, 3),
        ]
        if metrics is None:
            row.extend([""] * 8)
        else:
            row.extend(
                [
                    round(metrics.yaw_delta_deg, 3),
                    round(metrics.pitch_delta_deg, 3),
                    round(metrics.roll_delta_deg, 3),
                    round(metrics.gaze_x_delta, 4),
                    round(metrics.gaze_y_delta, 4),
                    round(metrics.left_eye_open_norm, 4),
                    round(metrics.right_eye_open_norm, 4),
                    round(metrics.face_scale_delta, 4),
                ]
            )
        self._raw_writer.writerow(row)
        self._rows_since_flush += 1
        if self._rows_since_flush >= 15 and self._raw_file is not None:
            self._raw_file.flush()
            self._rows_since_flush = 0

    def finish(self, summary: SessionSummary, timeline_buckets=None) -> Optional[Path]:
        if self.session_dir is None:
            return None
        self._close_raw_file()
        summary_path = self.session_dir / "summary.json"
        with summary_path.open("w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, ensure_ascii=False, indent=2)
        self._write_events(summary.events)
        self._write_result_image(summary)
        self.database.add_session(
            summary,
            self.session_dir,
            task_id=self.task_id,
            timeline_buckets=timeline_buckets,
        )
        return summary_path

    def _close_raw_file(self) -> None:
        if self._raw_file is not None:
            self._raw_file.flush()
            self._raw_file.close()
        self._raw_file = None
        self._raw_writer = None
        self._rows_since_flush = 0

    def _write_events(self, events: Iterable[AttentionEvent]) -> None:
        if self.events_path is None:
            return
        with self.events_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["type", "started_at", "ended_at", "duration", "max_deviation"])
            for event in events:
                writer.writerow(
                    [
                        event.type,
                        round(event.started_at, 3),
                        round(event.ended_at, 3),
                        round(event.duration, 3),
                        round(event.max_deviation, 3),
                    ]
                )

    def _write_result_image(self, summary: SessionSummary) -> None:
        if self.session_dir is None:
            return
        image = Image.new("RGB", (960, 540), (17, 21, 28))
        draw = ImageDraw.Draw(image)
        try:
            title_font = ImageFont.truetype("arial.ttf", 36)
            body_font = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

        draw.text((48, 42), "ONF V2 Session Result", fill=(243, 245, 247), font=title_font)
        items = [
            (
                "Study mode",
                "Pomodoro" if summary.session_mode == "pomodoro" else "Free session",
            ),
            ("Visual focus", f"{summary.focus_ratio * 100:.1f}%"),
            ("Measurement coverage", f"{summary.coverage_ratio * 100:.1f}%"),
            ("Focus time", self._fmt(summary.focus_seconds)),
            ("Non-focus time", self._fmt(summary.non_focus_seconds)),
            ("Break time", self._fmt(summary.break_seconds)),
            ("Unscored time", self._fmt(summary.unscored_seconds)),
            ("Longest focus run", self._fmt(summary.longest_focus_seconds)),
            ("Events", str(len(summary.events))),
        ]
        if summary.session_mode == "pomodoro":
            items.insert(
                1,
                (
                    "Pomodoro cycles",
                    f"{summary.pomodoro_cycles_completed} / "
                    f"{summary.pomodoro_cycles_planned}",
                ),
            )
        y = 120
        for label, value in items:
            draw.text((64, y), label, fill=(148, 158, 172), font=body_font)
            draw.text((360, y), value, fill=(243, 245, 247), font=body_font)
            y += 42
        image.save(self.session_dir / "result.png")

    @staticmethod
    def wall_now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _fmt(seconds: float) -> str:
        total = int(round(seconds))
        minutes = total // 60
        remain = total % 60
        return f"{minutes:02d}:{remain:02d}"
