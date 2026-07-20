import time
import unittest

import numpy as np

from onf_v2.app.camera_service import CameraService


class FakeCapture:
    def __init__(self) -> None:
        self.opened = True
        self.counter = 0

    def isOpened(self) -> bool:  # noqa: N802
        return self.opened

    def read(self):
        if not self.opened:
            return False, None
        time.sleep(0.005)
        self.counter += 1
        return True, np.full((8, 8, 3), self.counter % 255, dtype=np.uint8)

    def release(self) -> None:
        self.opened = False


class CameraServiceTests(unittest.TestCase):
    def test_capture_runs_in_background_and_read_returns_latest_frame(self):
        capture = FakeCapture()
        service = CameraService()
        service._open_capture = lambda index: capture

        self.assertTrue(service.open(2))
        deadline = time.monotonic() + 1.0
        frame = service.read()
        while not frame.ok and time.monotonic() < deadline:
            time.sleep(0.01)
            frame = service.read()

        self.assertTrue(frame.ok)
        self.assertIsNotNone(frame.frame)
        first_sequence = frame.sequence
        time.sleep(0.02)
        newer = service.read()
        self.assertGreater(newer.sequence, first_sequence)

        service.release()
        self.assertIsNone(service.capture)
        self.assertFalse(capture.opened)

    def test_stopped_frames_are_reported_without_blocking_read(self):
        capture = FakeCapture()
        service = CameraService()
        service.capture = capture
        service._latest_frame = np.zeros((8, 8, 3), dtype=np.uint8)
        service._latest_timestamp = time.monotonic() - 3.0

        started = time.perf_counter()
        frame = service.read()

        self.assertFalse(frame.ok)
        self.assertEqual(frame.error, "Camera frames stopped")
        self.assertLess(time.perf_counter() - started, 0.05)
        service.release()


if __name__ == "__main__":
    unittest.main()
