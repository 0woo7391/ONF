import csv
import tempfile
import unittest
from pathlib import Path

from onf_v2.app.session_recorder import SessionRecorder
from onf_v2.core.models import (
    EffectiveState,
    FocusDecision,
    ObservationState,
    RelativeMetrics,
)


class SessionRecorderTest(unittest.TestCase):
    def test_writes_profile_match_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = SessionRecorder(tmp)
            recorder.start("2026-07-20 12:00:00")
            recorder.write_decision(
                FocusDecision(
                    timestamp=12.5,
                    raw_state=ObservationState.NORMAL_VIEW,
                    effective_state=EffectiveState.FOCUS,
                    reason="stable",
                    confidence=0.95,
                    matched_profile="writing",
                    profile_distances={"screen": 2.4, "writing": 0.3},
                    profile_switch_candidate=None,
                    metrics=RelativeMetrics(
                        timestamp=12.5,
                        yaw_delta_deg=1.0,
                        pitch_delta_deg=2.0,
                        roll_delta_deg=0.5,
                        gaze_x_delta=0.02,
                        gaze_y_delta=0.03,
                        left_eye_open_norm=0.95,
                        right_eye_open_norm=0.97,
                        face_scale_delta=0.04,
                        confidence=0.95,
                    ),
                )
            )
            recorder._close_raw_file()

            path = next(Path(tmp).glob("*/observations.csv"))
            with path.open(encoding="utf-8", newline="") as handle:
                row = next(csv.DictReader(handle))

            self.assertEqual(row["matched_profile"], "writing")
            self.assertEqual(row["profile_switch_candidate"], "")
            self.assertEqual(row["screen_distance"], "2.4")
            self.assertEqual(row["writing_distance"], "0.3")


if __name__ == "__main__":
    unittest.main()
