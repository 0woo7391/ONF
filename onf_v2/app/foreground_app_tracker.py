from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from typing import Callable, Dict, Optional


class ForegroundAppTracker:
    def __init__(
        self,
        resolver: Optional[Callable[[], Optional[str]]] = None,
        sample_interval: float = 1.0,
    ) -> None:
        self.resolver = resolver or foreground_process_name
        self.sample_interval = sample_interval
        self.active = False
        self.last_sample_at: Optional[float] = None
        self.last_process: Optional[str] = None
        self.durations: Dict[str, float] = {}
        self._display_names: Dict[str, str] = {}

    def reset(self) -> None:
        self.active = False
        self.last_sample_at = None
        self.last_process = None
        self.durations.clear()
        self._display_names.clear()

    def set_active(self, active: bool, timestamp: float) -> None:
        if active == self.active:
            return
        if self.active:
            self._credit_until(timestamp)
        self.active = active
        self.last_sample_at = timestamp if active else None
        self.last_process = self._resolve() if active else None

    def update(self, timestamp: float) -> None:
        if not self.active or self.last_sample_at is None:
            return
        if timestamp - self.last_sample_at < self.sample_interval:
            return
        self._credit_until(timestamp)
        self.last_sample_at = timestamp
        self.last_process = self._resolve()

    def finish(self, timestamp: float) -> Dict[str, float]:
        self.set_active(False, timestamp)
        return {
            self._display_names[key]: seconds
            for key, seconds in self.durations.items()
        }

    def _credit_until(self, timestamp: float) -> None:
        if self.last_sample_at is None or self.last_process is None:
            return
        elapsed = max(0.0, timestamp - self.last_sample_at)
        key = self.last_process.casefold()
        self._display_names.setdefault(key, self.last_process)
        self.durations[key] = self.durations.get(key, 0.0) + elapsed

    def _resolve(self) -> Optional[str]:
        try:
            value = self.resolver()
        except Exception:
            return None
        if not value:
            return None
        return value.replace("/", "\\").rsplit("\\", 1)[-1]


def foreground_process_name() -> Optional[str]:
    if sys.platform != "win32":
        return None

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    window = user32.GetForegroundWindow()
    if not window:
        return None
    process_id = wintypes.DWORD()
    if not user32.GetWindowThreadProcessId(window, ctypes.byref(process_id)):
        return None
    handle = kernel32.OpenProcess(0x1000, False, process_id.value)
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            return None
        return buffer.value.rsplit("\\", 1)[-1]
    finally:
        kernel32.CloseHandle(handle)
