import tempfile
import unittest
import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from onf_v2.app.session_database import SessionDatabase
from onf_v2.app.settings_store import SettingsStore
from onf_v2.core.models import SessionSummary
from onf_v2.ui_qml.app_bridge import AppBridge


class QmlAppBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_planner_records_and_settings_use_existing_storage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            database = SessionDatabase(root / "onf.sqlite3")
            settings_store = SettingsStore(root / "settings.json")
            bridge = AppBridge(database, settings_store)

            self.assertGreater(len(bridge.plannerTasks), 0)
            self.assertEqual(len(bridge.weeklyRecords), 7)
            self.assertEqual(len(bridge.monthlyLevels), 31)

            self.assertTrue(bridge.addPlannerTask("물리 문제", "14:00", "15:00", "60분"))
            tasks = database.list_planner_tasks()
            self.assertEqual(len(tasks), 1)
            self.assertEqual(tasks[0].planned_start_minute, 14 * 60)
            self.assertEqual(tasks[0].planned_end_minute, 15 * 60)

            bridge.cyclePlannerTask(tasks[0].id)
            self.assertEqual(database.list_planner_tasks()[0].status, "completed")

            now = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
            database.add_session(
                SessionSummary(
                    started_at_wall=now.isoformat(sep=" "),
                    ended_at_wall=now.replace(hour=11).isoformat(sep=" "),
                    focus_seconds=2700,
                    non_focus_seconds=900,
                    break_seconds=300,
                    unscored_seconds=0,
                    absent_pending_seconds=0,
                    focus_ratio=0.75,
                    coverage_ratio=1.0,
                    longest_focus_seconds=1200,
                    events=[],
                ),
                root / "session",
                timeline_buckets=[{"focus": 45, "non_focus": 15}] * 60,
            )
            bridge.refresh()
            self.assertEqual(bridge.dailySummary["ratio"], 75)
            self.assertEqual(bridge.dailySummary["study"], "1시간 0분")
            self.assertEqual(bridge.dailyHourlyData[0]["hour"], 10)

            bridge.saveSettings({"alert_volume": 37, "work_mode": "screen_writing"})
            saved = settings_store.load()
            self.assertEqual(saved.alert_volume, 37)
            self.assertEqual(saved.work_mode, "screen_writing")


if __name__ == "__main__":
    unittest.main()
