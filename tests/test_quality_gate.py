import unittest

from onf_v2.core.models import FrameObservation, ObservationState
from onf_v2.core.quality_gate import QualityGate


def observation(**changes) -> FrameObservation:
    values = dict(
        timestamp=0.0,
        camera_ok=True,
        face_detected=True,
        face_count=1,
        tracking_confidence=0.95,
        face_bbox=(0.2, 0.1, 0.7, 0.9),
        face_scale=0.4,
        left_gaze_x=0.48,
        right_gaze_x=0.52,
        left_gaze_y=0.50,
        right_gaze_y=0.53,
        left_eye_open_ratio=0.25,
        right_eye_open_ratio=0.25,
    )
    values.update(changes)
    return FrameObservation(**values)


class QualityGateTest(unittest.TestCase):
    def test_accepts_consistent_both_eye_gaze(self):
        self.assertEqual(
            QualityGate().evaluate(observation()),
            ObservationState.NORMAL_VIEW,
        )

    def test_rejects_large_both_eye_gaze_disagreement(self):
        self.assertEqual(
            QualityGate().evaluate(
                observation(left_gaze_x=0.12, right_gaze_x=0.82)
            ),
            ObservationState.LOW_CONFIDENCE,
        )

    def test_rejects_partially_missing_eye_gaze(self):
        self.assertEqual(
            QualityGate().evaluate(observation(right_gaze_y=None)),
            ObservationState.LOW_CONFIDENCE,
        )

    def test_closed_eyes_do_not_fail_on_unstable_iris_position(self):
        self.assertEqual(
            QualityGate().evaluate(
                observation(
                    left_gaze_y=0.05,
                    right_gaze_y=0.95,
                    left_eye_open_ratio=0.04,
                    right_eye_open_ratio=0.04,
                )
            ),
            ObservationState.NORMAL_VIEW,
        )

    def test_legacy_observation_without_per_eye_values_remains_supported(self):
        self.assertEqual(
            QualityGate().evaluate(
                observation(
                    left_gaze_x=None,
                    right_gaze_x=None,
                    left_gaze_y=None,
                    right_gaze_y=None,
                )
            ),
            ObservationState.NORMAL_VIEW,
        )


if __name__ == "__main__":
    unittest.main()
