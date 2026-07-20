from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_OBSENSOR", "0")

import cv2

try:
    cv2.setLogLevel(0)
except Exception:
    pass


@dataclass
class CameraFrame:
    ok: bool
    timestamp: float
    frame: Optional[object] = None
    error: Optional[str] = None
    sequence: int = 0


class CameraService:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.capture: Optional[cv2.VideoCapture] = None
        self.backend_name = ""
        self._warmup_frame: Optional[object] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[object] = None
        self._latest_timestamp = 0.0
        self._latest_error: Optional[str] = None
        self._sequence = 0

    def open(self, index: Optional[int] = None) -> bool:
        if index is not None:
            self.index = index
        self.release()
        self.capture = self._open_capture(self.index)
        if self.capture is None or not self.capture.isOpened():
            self.backend_name = ""
            return False
        with self._lock:
            self._latest_frame = self._warmup_frame
            self._latest_timestamp = (
                time.monotonic() if self._warmup_frame is not None else 0.0
            )
            self._latest_error = None
            self._sequence = 1 if self._warmup_frame is not None else 0
        self._warmup_frame = None
        self._stop_event.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            name="onf-camera-capture",
            daemon=True,
        )
        self._capture_thread.start()
        return True

    def read(self) -> CameraFrame:
        now = time.monotonic()
        capture = self.capture
        if capture is None or not capture.isOpened():
            return CameraFrame(False, now, error="Camera is not open")
        with self._lock:
            frame = self._latest_frame
            timestamp = self._latest_timestamp
            error = self._latest_error
            sequence = self._sequence
        if frame is None:
            return CameraFrame(
                False,
                now,
                error=error or "Camera is warming up",
                sequence=sequence,
            )
        if now - timestamp > 2.0:
            return CameraFrame(
                False,
                now,
                error=error or "Camera frames stopped",
                sequence=sequence,
            )
        return CameraFrame(
            True,
            timestamp,
            frame=frame,
            sequence=sequence,
        )

    def release(self) -> None:
        self._stop_event.set()
        capture = self.capture
        self.capture = None
        if capture is not None:
            capture.release()
        thread = self._capture_thread
        self._capture_thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
        with self._lock:
            self._latest_frame = None
            self._latest_timestamp = 0.0
            self._latest_error = None
            self._sequence = 0
        self.backend_name = ""
        self._warmup_frame = None

    @staticmethod
    def list_candidate_cameras(limit: int = 8) -> Tuple[int, ...]:
        return tuple(range(limit))

    def _capture_loop(self) -> None:
        capture = self.capture
        if capture is None:
            return
        while not self._stop_event.is_set():
            ok, frame = capture.read()
            timestamp = time.monotonic()
            if not ok or frame is None:
                with self._lock:
                    self._latest_error = "Camera read failed"
                time.sleep(0.05)
                continue
            with self._lock:
                self._latest_frame = frame
                self._latest_timestamp = timestamp
                self._latest_error = None
                self._sequence += 1

    def _open_capture(self, index: int):
        backends = [
            ("Media Foundation", cv2.CAP_MSMF, 0.0),
            ("Media Foundation", cv2.CAP_MSMF, 0.45),
            ("Windows 기본", cv2.CAP_ANY, 0.15),
            ("DirectShow", cv2.CAP_DSHOW, 0.15),
        ]

        for name, backend, retry_delay in backends:
            if retry_delay > 0:
                time.sleep(retry_delay)
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_FPS, 30)
                warmup_frame = None
                successful_reads = 0
                for _attempt in range(4):
                    ok, frame = cap.read()
                    if ok and frame is not None:
                        warmup_frame = frame
                        successful_reads += 1
                        if successful_reads >= 2:
                            break
                if successful_reads >= 2:
                    self.backend_name = name
                    self._warmup_frame = warmup_frame
                    return cap
            cap.release()
        return None
