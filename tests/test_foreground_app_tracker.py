import unittest

from onf_v2.app.foreground_app_tracker import ForegroundAppTracker


class ForegroundAppTrackerTests(unittest.TestCase):
    def test_groups_foreground_apps_and_excludes_paused_time(self):
        current = ["Code.exe"]
        tracker = ForegroundAppTracker(lambda: current[0])
        tracker.set_active(True, 0.0)
        tracker.update(1.0)
        current[0] = "chrome.exe"
        tracker.update(2.0)
        tracker.set_active(False, 3.0)
        tracker.update(20.0)
        current[0] = "CODE.EXE"
        tracker.set_active(True, 20.0)
        result = tracker.finish(22.0)

        self.assertEqual(result, {"Code.exe": 4.0, "chrome.exe": 1.0})

    def test_unknown_foreground_process_is_not_attributed(self):
        tracker = ForegroundAppTracker(lambda: None)
        tracker.set_active(True, 0.0)
        tracker.update(1.0)

        self.assertEqual(tracker.finish(2.0), {})


if __name__ == "__main__":
    unittest.main()
