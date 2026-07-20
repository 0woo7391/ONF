import json
import tempfile
import unittest
import wave
from pathlib import Path

from onf_v2.app.alert_controller import AttentionAlertController
from onf_v2.app.alert_sounds import ALERT_SOUND_KEYS, ensure_alert_sound_files
from onf_v2.app.break_timer import BreakTimer
from onf_v2.app.settings_store import SettingsStore, UserSettings
from onf_v2.core.models import EffectiveState, Mode


class SettingsStoreTests(unittest.TestCase):
    def test_round_trips_user_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingsStore(Path(tmp) / "settings.json")
            expected = UserSettings(
                attention_alert_seconds=90,
                break_duration_minutes=7,
                absence_to_break_minutes=8,
                sound_enabled=False,
                alert_volume=35,
                alert_sound="chime",
                study_day_start_hour=3,
                mode=Mode.STRICT.value,
                work_mode="screen_writing",
                camera_index=3,
                camera_preview_hidden=True,
                session_mode="pomodoro",
                pomodoro_focus_minutes=40,
                pomodoro_short_break_minutes=8,
                pomodoro_long_break_minutes=20,
                pomodoro_cycles=3,
                pomodoro_auto_start_break=True,
                pomodoro_auto_start_next=False,
            )

            store.save(expected)

            self.assertEqual(store.load(), expected)

    def test_invalid_values_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "attention_alert_seconds": 9999,
                        "break_duration_minutes": 0,
                        "absence_to_break_minutes": "invalid",
                        "alert_volume": -20,
                        "alert_sound": "unknown",
                        "study_day_start_hour": 99,
                        "mode": "unknown",
                        "session_mode": "invalid",
                        "pomodoro_focus_minutes": 0,
                        "pomodoro_cycles": 99,
                    }
                ),
                encoding="utf-8",
            )

            settings = SettingsStore(path).load()

            self.assertEqual(settings.attention_alert_seconds, 600)
            self.assertEqual(settings.break_duration_minutes, 1)
            self.assertEqual(settings.absence_to_break_minutes, 5)
            self.assertEqual(settings.alert_volume, 0)
            self.assertEqual(settings.alert_sound, "impact")
            self.assertEqual(settings.study_day_start_hour, 23)
            self.assertEqual(settings.mode, Mode.NORMAL.value)
            self.assertEqual(settings.work_mode, "screen")
            self.assertEqual(settings.session_mode, "free")
            self.assertEqual(settings.pomodoro_focus_minutes, 1)
            self.assertEqual(settings.pomodoro_cycles, 12)

    def test_generates_distinct_builtin_alert_sounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = ensure_alert_sound_files(Path(tmp))

            self.assertEqual(set(paths), ALERT_SOUND_KEYS)
            payloads = set()
            for path in paths.values():
                self.assertGreater(path.stat().st_size, 1_000)
                with wave.open(str(path), "rb") as sound:
                    self.assertEqual(sound.getframerate(), 44_100)
                    self.assertEqual(sound.getnchannels(), 1)
                payloads.add(path.read_bytes())
            self.assertEqual(len(payloads), len(ALERT_SOUND_KEYS))


class AttentionAlertControllerTests(unittest.TestCase):
    def test_alerts_once_after_one_minute_and_resets_after_recovery(self):
        controller = AttentionAlertController(
            threshold_seconds=60.0,
            recovery_seconds=3.0,
        )

        self.assertFalse(controller.update(EffectiveState.NON_FOCUS, 0.0).active)
        self.assertFalse(controller.update(EffectiveState.NON_FOCUS, 59.0).active)
        first_alert = controller.update(EffectiveState.NON_FOCUS, 60.0)
        self.assertTrue(first_alert.active)
        self.assertTrue(first_alert.just_triggered)
        self.assertFalse(
            controller.update(EffectiveState.NON_FOCUS, 70.0).just_triggered
        )

        self.assertTrue(controller.update(EffectiveState.FOCUS, 70.0).active)
        recovered = controller.update(EffectiveState.FOCUS, 73.0)
        self.assertFalse(recovered.active)
        self.assertTrue(recovered.just_cleared)

    def test_unscored_time_never_triggers_attention_alert(self):
        controller = AttentionAlertController(threshold_seconds=60.0)
        controller.update(EffectiveState.NON_FOCUS, 0.0)

        update = controller.update(EffectiveState.UNSCORED, 61.0)

        self.assertFalse(update.active)
        self.assertFalse(update.just_triggered)


class BreakTimerTests(unittest.TestCase):
    def test_five_minute_countdown_notifies_once_and_can_extend(self):
        timer = BreakTimer(duration_seconds=300.0)
        timer.start(10.0)

        self.assertEqual(timer.update(10.0).remaining_seconds, 300.0)
        self.assertEqual(timer.update(309.0).remaining_seconds, 1.0)
        expired = timer.update(310.0)
        self.assertTrue(expired.expired)
        self.assertTrue(expired.just_expired)
        self.assertFalse(timer.update(311.0).just_expired)

        timer.extend(60.0, 311.0)
        extended = timer.update(311.0)
        self.assertFalse(extended.expired)
        self.assertEqual(extended.remaining_seconds, 60.0)

        timer.update(371.0)
        timer.extend(60.0, 450.0)
        self.assertEqual(timer.update(450.0).remaining_seconds, 60.0)


if __name__ == "__main__":
    unittest.main()
