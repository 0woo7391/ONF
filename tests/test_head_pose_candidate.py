import math
import unittest
from types import SimpleNamespace

import cv2
import numpy as np

from onf_v2.core.face_analyzer import FaceAnalyzer


INDICES = (1, 152, 33, 263, 61, 291)
MODEL = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1),
    ],
    dtype=np.float64,
)


def projected_landmarks(rotation, translation, width=640, height=480):
    camera = np.array(
        ((width, 0, width / 2), (0, width, height / 2), (0, 0, 1)),
        dtype=np.float64,
    )
    image_points, _ = cv2.projectPoints(
        MODEL, cv2.Rodrigues(rotation)[0], translation, camera, None
    )
    landmarks = [SimpleNamespace(x=0.5, y=0.5) for _ in range(292)]
    for index, (x, y) in zip(INDICES, image_points.reshape(-1, 2)):
        landmarks[index] = SimpleNamespace(x=x / width, y=y / height)
    return landmarks, camera, image_points.reshape(-1, 2)


def solved_rotation(image_points, camera):
    ok, rotation_vector, translation_vector = cv2.solvePnP(
        MODEL, image_points, camera, np.zeros((4, 1)),
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        raise AssertionError("Synthetic pose could not be solved")
    rotation = cv2.Rodrigues(rotation_vector)[0]
    projected, _ = cv2.projectPoints(
        MODEL, rotation_vector, translation_vector, camera, None
    )
    error = np.sqrt(np.mean(np.sum((projected.reshape(-1, 2) - image_points) ** 2, axis=1)))
    eye_width = np.linalg.norm(image_points[2] - image_points[3])
    return rotation, error / eye_width


def relative_angles(reference, current):
    rotation = current @ reference.T
    return tuple(map(math.degrees, (
        math.atan2(rotation[0, 2], rotation[2, 2]),
        math.asin(-rotation[1, 2]),
        math.atan2(rotation[1, 0], rotation[1, 1]),
    )))


class HeadPoseCandidateTest(unittest.TestCase):
    def test_relative_rotation_stays_continuous_across_angle_wrap(self):
        reference = cv2.Rodrigues(
            np.array((0.0, math.radians(179), 0.0))
        )[0]
        current = cv2.Rodrigues(
            np.array((0.0, math.radians(-179), 0.0))
        )[0]
        yaw, pitch, roll = relative_angles(reference, current)
        self.assertAlmostEqual(yaw, 2.0, delta=1e-6)
        self.assertAlmostEqual(pitch, 0.0, delta=1e-6)
        self.assertAlmostEqual(roll, 0.0, delta=1e-6)

    def test_same_landmarks_compare_legacy_and_relative_rotation(self):
        front = np.diag((1.0, -1.0, -1.0))
        base_landmarks, camera, base_points = projected_landmarks(
            front, np.array((0.0, 0.0, 650.0))
        )
        base_rotation, _ = solved_rotation(base_points, camera)
        self.assertTrue(all(math.isfinite(value) for value in FaceAnalyzer._head_pose(
            base_landmarks, 640, 480
        )))

        scenarios = (
            (front, (70.0, 0.0, 650.0), (0.0, 0.0, 0.0)),
            (front, (0.0, 0.0, 520.0), (0.0, 0.0, 0.0)),
            (cv2.Rodrigues(np.array((0.0, math.radians(15), 0.0)))[0] @ front,
             (0.0, 0.0, 650.0), (15.0, 0.0, 0.0)),
            (cv2.Rodrigues(np.array((0.0, math.radians(15), 0.0)))[0] @ front,
             (70.0, 0.0, 650.0), (15.0, 0.0, 0.0)),
            (cv2.Rodrigues(np.array((math.radians(12), 0.0, 0.0)))[0] @ front,
             (0.0, 0.0, 650.0), (0.0, 12.0, 0.0)),
            (cv2.Rodrigues(np.array((0.0, 0.0, math.radians(12))))[0] @ front,
             (0.0, 0.0, 650.0), (0.0, 0.0, 12.0)),
        )
        for rotation, translation, expected in scenarios:
            landmarks, camera, points = projected_landmarks(
                rotation, np.array(translation)
            )
            legacy = FaceAnalyzer._head_pose(landmarks, 640, 480)
            candidate_rotation, reprojection_error = solved_rotation(points, camera)
            candidate = relative_angles(base_rotation, candidate_rotation)
            with self.subTest(expected=expected, translation=translation):
                self.assertTrue(all(math.isfinite(value) for value in legacy))
                self.assertLess(reprojection_error, 1e-4)
                for actual, target in zip(candidate, expected):
                    self.assertAlmostEqual(actual, target, delta=0.5)


if __name__ == "__main__":
    unittest.main()
