import math
import unittest
from types import SimpleNamespace

from onf_v2.core.face_analyzer import FaceAnalyzer


class FaceAnalyzerPoseTest(unittest.TestCase):
    def test_eye_measurements_ignore_frame_shape_translation_and_roll(self):
        corners = (33, 133)
        lids = ((159, 145), (160, 144), (158, 153))

        def measure(frame_width, frame_height, shift, angle, scale=1.0):
            points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(474)]

            def put(index, x, y):
                c, s = math.cos(angle), math.sin(angle)
                px = shift[0] + scale * (x * c - y * s)
                py = shift[1] + scale * (x * s + y * c)
                points[index] = SimpleNamespace(x=px / frame_width, y=py / frame_height)

            put(33, -20, 0)
            put(133, 20, 0)
            for x, (top, bottom) in zip((-10, 0, 10), lids):
                put(top, x, -5)
                put(bottom, x, 5)
            put(468, 6, -2)
            return FaceAnalyzer._eye_metrics(
                points, frame_width, frame_height, *corners, lids, 468
            )

        expected = measure(640, 480, (150, 140), 0.0)
        for actual in (
            measure(1280, 480, (300, 140), 0.0),
            measure(640, 960, (150, 280), 0.0),
            measure(640, 480, (320, 240), math.radians(30)),
            measure(1280, 960, (400, 400), math.radians(-20), scale=2.0),
        ):
            for value, baseline in zip(actual, expected):
                self.assertAlmostEqual(value, baseline, places=6)
        self.assertAlmostEqual(expected[0], 0.15)
        self.assertAlmostEqual(expected[1], -0.05)
        self.assertAlmostEqual(expected[2], 0.25)

    def test_closed_lids_survive_missing_iris_but_bad_lids_do_not(self):
        points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(161)]
        for index, x, y in (
            (33, 0.25, 0.4), (133, 0.35, 0.4),
            (159, 0.30, 0.4), (145, 0.30, 0.4),
            (160, 0.29, 0.4), (144, 0.29, 0.4),
            (158, 0.31, 0.4), (153, 0.31, 0.4),
        ):
            points[index] = SimpleNamespace(x=x, y=y)
        lids = ((159, 145), (160, 144), (158, 153))
        self.assertEqual(
            FaceAnalyzer._eye_metrics(points, 640, 480, 33, 133, lids, 468),
            (None, None, 0.0),
        )
        points[159] = SimpleNamespace(x=float("nan"), y=0.4)
        self.assertEqual(
            FaceAnalyzer._eye_metrics(points, 640, 480, 33, 133, lids, 468),
            (None, None, None),
        )

    def test_both_eyes_share_axes_and_outside_lid_iris_is_not_clamped(self):
        points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(474)]

        def put(index, x, y):
            points[index] = SimpleNamespace(x=x / 640, y=y / 480)

        for corner_a, corner_b, pairs, iris, offset in (
            (33, 133, ((159, 145), (160, 144), (158, 153)), 468, 0),
            (362, 263, ((386, 374), (385, 380), (387, 373)), 473, 100),
        ):
            put(corner_a, 120 + offset, 100)
            put(corner_b, 160 + offset, 100)
            for top, bottom in pairs:
                put(top, 140 + offset, 95)
                put(bottom, 140 + offset, 105)
            put(iris, 146 + offset, 80)
            gaze_x, gaze_y, opening = FaceAnalyzer._eye_metrics(
                points, 640, 480, corner_a, corner_b, pairs, iris
            )
            self.assertAlmostEqual(gaze_x, 0.15)
            self.assertAlmostEqual(gaze_y, -0.5)
            self.assertAlmostEqual(opening, 0.25)

    def test_eye_line_roll_is_stable_when_landmark_order_is_reversed(self):
        left = SimpleNamespace(x=0.3, y=0.4)
        right = SimpleNamespace(x=0.7, y=0.5)

        forward = FaceAnalyzer._eye_line_roll(left, right)
        reversed_order = FaceAnalyzer._eye_line_roll(right, left)

        self.assertAlmostEqual(forward, reversed_order)
        self.assertGreater(forward, 0.0)
        self.assertLess(abs(forward), 20.0)

    def test_pose_angle_folds_equivalent_flipped_solution(self):
        self.assertAlmostEqual(FaceAnalyzer._fold_pose_angle(170.0), 10.0)
        self.assertAlmostEqual(FaceAnalyzer._fold_pose_angle(-170.0), -10.0)
        self.assertAlmostEqual(FaceAnalyzer._fold_pose_angle(25.0), 25.0)

    def test_landmark_yaw_is_relative_to_the_eyes(self):
        left = SimpleNamespace(x=0.3, y=0.4)
        right = SimpleNamespace(x=0.7, y=0.4)
        centered = SimpleNamespace(x=0.5, y=0.55)
        turned = SimpleNamespace(x=0.6, y=0.55)

        self.assertAlmostEqual(FaceAnalyzer._landmark_yaw(centered, left, right), 0.0)
        self.assertAlmostEqual(FaceAnalyzer._landmark_yaw(turned, left, right), 22.5)

        shifted_left = SimpleNamespace(x=0.4, y=0.4)
        shifted_right = SimpleNamespace(x=0.8, y=0.4)
        shifted_nose = SimpleNamespace(x=0.6, y=0.55)
        self.assertAlmostEqual(
            FaceAnalyzer._landmark_yaw(
                shifted_nose, shifted_left, shifted_right
            ),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
