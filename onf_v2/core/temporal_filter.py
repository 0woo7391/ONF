from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from .models import RelativeMetrics


@dataclass
class TemporalFilter:
    gaze_window: int = 7
    eye_window: int = 5
    alpha: float = 0.35
    _last: Optional[RelativeMetrics] = None
    _gaze_x: Deque[float] = field(default_factory=lambda: deque(maxlen=7))
    _gaze_y: Deque[float] = field(default_factory=lambda: deque(maxlen=7))
    _left_eye: Deque[float] = field(default_factory=lambda: deque(maxlen=5))
    _right_eye: Deque[float] = field(default_factory=lambda: deque(maxlen=5))

    def reset(self) -> None:
        self._last = None
        self._gaze_x.clear()
        self._gaze_y.clear()
        self._left_eye.clear()
        self._right_eye.clear()

    def update(self, metrics: RelativeMetrics) -> RelativeMetrics:
        if self._gaze_x.maxlen != self.gaze_window:
            self._gaze_x = deque(self._gaze_x, maxlen=self.gaze_window)
            self._gaze_y = deque(self._gaze_y, maxlen=self.gaze_window)
        if self._left_eye.maxlen != self.eye_window:
            self._left_eye = deque(self._left_eye, maxlen=self.eye_window)
            self._right_eye = deque(self._right_eye, maxlen=self.eye_window)

        self._gaze_x.append(metrics.gaze_x_delta)
        self._gaze_y.append(metrics.gaze_y_delta)
        self._left_eye.append(metrics.left_eye_open_norm)
        self._right_eye.append(metrics.right_eye_open_norm)

        if self._last is None:
            filtered = metrics
        else:
            a = self.alpha
            filtered = RelativeMetrics(
                timestamp=metrics.timestamp,
                yaw_delta_deg=self._ema(self._last.yaw_delta_deg, metrics.yaw_delta_deg, a),
                pitch_delta_deg=self._ema(
                    self._last.pitch_delta_deg, metrics.pitch_delta_deg, a
                ),
                roll_delta_deg=self._ema(
                    self._last.roll_delta_deg, metrics.roll_delta_deg, a
                ),
                gaze_x_delta=statistics.median(self._gaze_x),
                gaze_y_delta=statistics.median(self._gaze_y),
                left_eye_open_norm=statistics.median(self._left_eye),
                right_eye_open_norm=statistics.median(self._right_eye),
                face_scale_delta=metrics.face_scale_delta,
                confidence=metrics.confidence,
            )
        self._last = filtered
        return filtered

    @staticmethod
    def _ema(previous: float, current: float, alpha: float) -> float:
        return previous + alpha * (current - previous)

