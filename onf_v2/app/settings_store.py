from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from onf_v2.app.alert_sounds import ALERT_SOUND_KEYS, DEFAULT_ALERT_SOUND
from onf_v2.core.models import Mode


@dataclass
class UserSettings:
    attention_alert_seconds: int = 60
    break_duration_minutes: int = 5
    absence_to_break_minutes: int = 5
    sound_enabled: bool = True
    alert_volume: int = 60
    alert_sound: str = DEFAULT_ALERT_SOUND
    study_day_start_hour: int = 4
    mode: str = Mode.NORMAL.value
    work_mode: str = "screen"
    camera_index: int = 0
    camera_preview_hidden: bool = False
    session_mode: str = "free"
    pomodoro_focus_minutes: int = 25
    pomodoro_short_break_minutes: int = 5
    pomodoro_long_break_minutes: int = 15
    pomodoro_cycles: int = 4
    pomodoro_auto_start_break: bool = True
    pomodoro_auto_start_next: bool = False

    @classmethod
    def from_dict(cls, values: Dict[str, Any]) -> "UserSettings":
        defaults = cls()
        mode = str(values.get("mode", defaults.mode))
        if mode not in {item.value for item in Mode}:
            mode = defaults.mode
        return cls(
            attention_alert_seconds=_bounded_int(
                values.get("attention_alert_seconds"),
                defaults.attention_alert_seconds,
                10,
                600,
            ),
            break_duration_minutes=_bounded_int(
                values.get("break_duration_minutes"),
                defaults.break_duration_minutes,
                1,
                30,
            ),
            absence_to_break_minutes=_bounded_int(
                values.get("absence_to_break_minutes"),
                defaults.absence_to_break_minutes,
                1,
                30,
            ),
            sound_enabled=bool(values.get("sound_enabled", defaults.sound_enabled)),
            alert_volume=_bounded_int(
                values.get("alert_volume"), defaults.alert_volume, 0, 100
            ),
            alert_sound=(
                str(values.get("alert_sound"))
                if str(values.get("alert_sound")) in ALERT_SOUND_KEYS
                else defaults.alert_sound
            ),
            study_day_start_hour=_bounded_int(
                values.get("study_day_start_hour"),
                defaults.study_day_start_hour,
                0,
                23,
            ),
            mode=mode,
            work_mode=(
                str(values.get("work_mode"))
                if str(values.get("work_mode")) in {"screen", "screen_writing"}
                else defaults.work_mode
            ),
            camera_index=_bounded_int(
                values.get("camera_index"), defaults.camera_index, 0, 32
            ),
            camera_preview_hidden=bool(
                values.get(
                    "camera_preview_hidden",
                    defaults.camera_preview_hidden,
                )
            ),
            session_mode=(
                str(values.get("session_mode"))
                if str(values.get("session_mode")) in {"free", "pomodoro"}
                else defaults.session_mode
            ),
            pomodoro_focus_minutes=_bounded_int(
                values.get("pomodoro_focus_minutes"),
                defaults.pomodoro_focus_minutes,
                1,
                120,
            ),
            pomodoro_short_break_minutes=_bounded_int(
                values.get("pomodoro_short_break_minutes"),
                defaults.pomodoro_short_break_minutes,
                1,
                30,
            ),
            pomodoro_long_break_minutes=_bounded_int(
                values.get("pomodoro_long_break_minutes"),
                defaults.pomodoro_long_break_minutes,
                1,
                60,
            ),
            pomodoro_cycles=_bounded_int(
                values.get("pomodoro_cycles"), defaults.pomodoro_cycles, 1, 12
            ),
            pomodoro_auto_start_break=bool(
                values.get(
                    "pomodoro_auto_start_break",
                    defaults.pomodoro_auto_start_break,
                )
            ),
            pomodoro_auto_start_next=bool(
                values.get(
                    "pomodoro_auto_start_next",
                    defaults.pomodoro_auto_start_next,
                )
            ),
        )


class SettingsStore:
    def __init__(self, path: Optional[str | Path] = None) -> None:
        self.path = Path(path) if path is not None else self.default_path()

    @staticmethod
    def default_path() -> Path:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "ONF" / "settings.json"
        return Path.home() / ".onf" / "settings.json"

    def load(self) -> UserSettings:
        if not self.path.exists():
            return UserSettings()
        try:
            values = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserSettings()
        if not isinstance(values, dict):
            return UserSettings()
        return UserSettings.from_dict(values)

    def save(self, settings: UserSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self.path)


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(maximum, max(minimum, parsed))
