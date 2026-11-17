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
        left_gaze_x=-0.02,
        right_gaze_x=0.02,
        left_gaze_y=0.00,
        right_gaze_y=0.03,
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
                observation(left_gaze_x=-0.35, right_gaze_x=0.35)
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
                    left_gaze_y=-0.30,
                    right_gaze_y=0.30,
                    left_eye_open_ratio=0.04,
                    right_eye_open_ratio=0.04,
                ),
                eyes_closed=True,
            ),
            ObservationState.NORMAL_VIEW,
        )

    def test_missing_iris_is_unscored_when_eyes_are_open(self):
        self.assertEqual(
            QualityGate().evaluate(
                observation(
                    left_gaze_x=None,
                    right_gaze_x=None,
                    left_gaze_y=None,
                    right_gaze_y=None,
                )
            ),
            ObservationState.LOW_CONFIDENCE,
        )

    def test_valid_closed_lids_do_not_require_iris(self):
        closed = observation(
            left_gaze_x=None, right_gaze_x=None,
            left_gaze_y=None, right_gaze_y=None,
            left_eye_open_ratio=0.02, right_eye_open_ratio=0.02,
        )
        self.assertEqual(
            QualityGate().evaluate(closed, eyes_closed=True),
            ObservationState.NORMAL_VIEW,
        )
        closed.left_eye_open_ratio = None
        self.assertEqual(
            QualityGate().evaluate(closed, eyes_closed=True),
            ObservationState.LOW_CONFIDENCE,
        )

    def test_rejects_nonfinite_and_implausible_eye_measurements(self):
        gate = QualityGate()
        for bad in (
            observation(left_eye_open_ratio=float("nan")),
            observation(right_eye_open_ratio=0.9),
            observation(left_gaze_y=float("inf")),
            observation(left_gaze_x=2.0),
        ):
            self.assertEqual(gate.evaluate(bad), ObservationState.LOW_CONFIDENCE)


if __name__ == "__main__":
    unittest.main()
