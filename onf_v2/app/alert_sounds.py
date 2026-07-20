from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Dict


DEFAULT_ALERT_SOUND = "impact"
ALERT_SOUND_OPTIONS = (
    ("impact", "강한 경고"),
    ("chime", "선명한 벨"),
    ("digital", "디지털 알림"),
    ("soft", "부드러운 알림"),
)
ALERT_SOUND_KEYS = {key for key, _label in ALERT_SOUND_OPTIONS}

_PRESETS = {
    "impact": (
        0.76,
        0.82,
        0.32,
        ((0.00, 0.16, 520.0), (0.20, 0.38, 760.0), (0.42, 0.76, 1040.0)),
    ),
    "chime": (
        0.84,
        0.66,
        0.20,
        ((0.00, 0.24, 784.0), (0.27, 0.52, 988.0), (0.55, 0.84, 1319.0)),
    ),
    "digital": (
        0.56,
        0.76,
        0.44,
        ((0.00, 0.11, 920.0), (0.16, 0.27, 920.0), (0.32, 0.56, 1250.0)),
    ),
    "soft": (
        0.54,
        0.50,
        0.10,
        ((0.00, 0.22, 660.0), (0.25, 0.54, 880.0)),
    ),
}


def ensure_alert_sound_files(directory: Path) -> Dict[str, Path]:
    paths: Dict[str, Path] = {}
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return paths

    for key in ALERT_SOUND_KEYS:
        path = directory / f"alert_{key}_v1.wav"
        try:
            if not path.exists() or path.stat().st_size <= 1_000:
                _write_tone(path, key)
            paths[key] = path
        except (OSError, wave.Error):
            continue
    return paths


def _write_tone(path: Path, key: str) -> None:
    duration, amplitude, harmonic, segments = _PRESETS[key]
    sample_rate = 44_100
    frame_count = int(sample_rate * duration)
    frames = bytearray()

    for index in range(frame_count):
        elapsed = index / sample_rate
        sample = 0.0
        for start, end, frequency in segments:
            if not start <= elapsed < end:
                continue
            local = elapsed - start
            attack = min(1.0, local / 0.012)
            release = min(1.0, (end - elapsed) / 0.045)
            envelope = max(0.0, min(attack, release))
            phase = 2.0 * math.pi * frequency * local
            wave_value = (
                math.sin(phase) + harmonic * math.sin(phase * 2.0)
            ) / (1.0 + harmonic)
            sample = amplitude * envelope * wave_value
            break
        frames.extend(struct.pack("<h", int(32767 * sample)))

    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames)
