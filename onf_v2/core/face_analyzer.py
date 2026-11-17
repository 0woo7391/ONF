from __future__ import annotations

import math
import os
from typing import Any, Optional, Sequence, Tuple

import cv2
import numpy as np
from mediapipe.python.solutions import face_mesh

from .models import FrameObservation, ObservationState


class FaceAnalyzer:
    """MediaPipe FaceMesh based observation extractor.

    It produces visual-attention proxy measurements only. It does not identify
    the user and should not be described as face recognition.
    """

    def __init__(self, max_num_faces: int = 2) -> None:
        os.environ.setdefault(
            "MPLCONFIGDIR",
            os.path.join(os.getcwd(), ".cache", "matplotlib"),
        )
        self._mp_face = face_mesh
        self._face_mesh = self._mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=max_num_faces,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def analyze(self, frame: Any, timestamp: float) -> FrameObservation:
        if frame is None or getattr(frame, "size", 0) == 0:
            return FrameObservation(
                timestamp=timestamp,
                camera_ok=False,
                quality_reason=ObservationState.CAMERA_ERROR.value,
            )

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self._face_mesh.process(rgb)
        except Exception as exc:
            return FrameObservation(
                timestamp=timestamp,
                camera_ok=True,
                quality_reason=ObservationState.PROCESSING_ERROR.value,
                error=str(exc),
            )

        face_landmarks = result.multi_face_landmarks or []
        if not face_landmarks:
            return FrameObservation(
                timestamp=timestamp,
                camera_ok=True,
                face_detected=False,
                face_count=0,
                quality_reason=ObservationState.NO_FACE.value,
            )

        if len(face_landmarks) > 1:
            return FrameObservation(
                timestamp=timestamp,
                camera_ok=True,
                face_detected=True,
                face_count=len(face_landmarks),
                tracking_confidence=0.4,
                quality_reason=ObservationState.MULTIPLE_FACES.value,
            )

        h, w = frame.shape[:2]
        landmarks = face_landmarks[0].landmark
        bbox = self._bbox(landmarks)
        face_scale = max(bbox[2] - bbox[0], bbox[3] - bbox[1])
        face_center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
        yaw, pitch, roll = self._head_pose(landmarks, w, h)
        left_gaze_x, left_gaze_y, left_eye_open = self._eye_metrics(
            landmarks,
            w,
            h,
            corner_a=33,
            corner_b=133,
            lid_pairs=((159, 145), (160, 144), (158, 153)),
            iris=468,
        )
        right_gaze_x, right_gaze_y, right_eye_open = self._eye_metrics(
            landmarks,
            w,
            h,
            corner_a=362,
            corner_b=263,
            lid_pairs=((386, 374), (385, 380), (387, 373)),
            iris=473,
        )
        if all(value is not None for value in (
            left_gaze_x, right_gaze_x, left_gaze_y, right_gaze_y
        )):
            gaze_x = (left_gaze_x + right_gaze_x) / 2.0
            gaze_y = (left_gaze_y + right_gaze_y) / 2.0
        else:
            gaze_x = gaze_y = None

        confidence = self._estimate_confidence(
            face_scale=face_scale,
            bbox=bbox,
            yaw=yaw,
            pitch=pitch,
            left_eye_open=left_eye_open,
            right_eye_open=right_eye_open,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
        )

        return FrameObservation(
            timestamp=timestamp,
            camera_ok=True,
            face_detected=True,
            face_count=1,
            tracking_confidence=confidence,
            face_bbox=bbox,
            face_scale=face_scale,
            face_center=face_center,
            head_yaw_deg=yaw,
            head_pitch_deg=pitch,
            head_roll_deg=roll,
            left_gaze_x=left_gaze_x,
            right_gaze_x=right_gaze_x,
            left_gaze_y=left_gaze_y,
            right_gaze_y=right_gaze_y,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            left_eye_open_ratio=left_eye_open,
            right_eye_open_ratio=right_eye_open,
            quality_reason=None,
        )

    def close(self) -> None:
        try:
            self._face_mesh.close()
        except Exception:
            pass

    @staticmethod
    def _bbox(landmarks: Sequence) -> Tuple[float, float, float, float]:
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _eye_metrics(
        landmarks: Sequence,
        width: int,
        height: int,
        corner_a: int,
        corner_b: int,
        lid_pairs: Sequence[Tuple[int, int]],
        iris: int,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        def point(index: int) -> Optional[Tuple[float, float]]:
            if index >= len(landmarks):
                return None
            x, y = landmarks[index].x * width, landmarks[index].y * height
            return (x, y) if math.isfinite(x) and math.isfinite(y) else None

        start, end = point(corner_a), point(corner_b)
        if start is None or end is None:
            return None, None, None
        if start[0] > end[0]:
            start, end = end, start
        dx, dy = end[0] - start[0], end[1] - start[1]
        eye_width = math.hypot(dx, dy)
        if eye_width < 3.0 or dx < eye_width * 0.2:
            return None, None, None
        ux, uy = dx / eye_width, dy / eye_width
        vx, vy = -uy, ux

        gaps = []
        for top_index, bottom_index in lid_pairs:
            top, bottom = point(top_index), point(bottom_index)
            if top is None or bottom is None:
                return None, None, None
            gap = (bottom[0] - top[0]) * vx + (bottom[1] - top[1]) * vy
            if gap < 0 or gap > eye_width * 0.7:
                return None, None, None
            gaps.append(gap)
        eye_open = sum(gaps) / len(gaps) / eye_width

        iris_point = point(iris)
        if iris_point is None:
            return None, None, eye_open
        cx, cy = (start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0
        ix, iy = iris_point[0] - cx, iris_point[1] - cy
        return (
            (ix * ux + iy * uy) / eye_width,
            (ix * vx + iy * vy) / eye_width,
            eye_open,
        )

    @staticmethod
    def _head_pose(landmarks: Sequence, width: int, height: int) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        indices = {
            "nose_tip": 1,
            "chin": 152,
            "left_eye_outer": 33,
            "right_eye_outer": 263,
            "left_mouth": 61,
            "right_mouth": 291,
        }
        image_points = np.array(
            [
                (landmarks[indices["nose_tip"]].x * width, landmarks[indices["nose_tip"]].y * height),
                (landmarks[indices["chin"]].x * width, landmarks[indices["chin"]].y * height),
                (
                    landmarks[indices["left_eye_outer"]].x * width,
                    landmarks[indices["left_eye_outer"]].y * height,
                ),
                (
                    landmarks[indices["right_eye_outer"]].x * width,
                    landmarks[indices["right_eye_outer"]].y * height,
                ),
                (landmarks[indices["left_mouth"]].x * width, landmarks[indices["left_mouth"]].y * height),
                (
                    landmarks[indices["right_mouth"]].x * width,
                    landmarks[indices["right_mouth"]].y * height,
                ),
            ],
            dtype=np.float64,
        )
        model_points = np.array(
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
        focal_length = float(width)
        camera_matrix = np.array(
            [
                [focal_length, 0.0, width / 2.0],
                [0.0, focal_length, height / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)
        ok, rotation_vec, _translation_vec = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            return None, None, None
        rotation_mat, _jacobian = cv2.Rodrigues(rotation_vec)
        proj_mat = np.hstack((rotation_mat, np.zeros((3, 1))))
        _camera, _rot, _trans, _rx, _ry, _rz, euler = cv2.decomposeProjectionMatrix(proj_mat)
        pitch = FaceAnalyzer._fold_pose_angle(float(euler[0][0]))
        yaw = FaceAnalyzer._landmark_yaw(
            landmarks[indices["nose_tip"]],
            landmarks[indices["left_eye_outer"]],
            landmarks[indices["right_eye_outer"]],
        )
        roll = FaceAnalyzer._eye_line_roll(
            landmarks[indices["left_eye_outer"]],
            landmarks[indices["right_eye_outer"]],
        )
        return yaw, pitch, roll

    @staticmethod
    def _fold_pose_angle(angle: float) -> float:
        normalized = (angle + 180.0) % 360.0 - 180.0
        if normalized > 90.0:
            return 180.0 - normalized
        if normalized < -90.0:
            return -180.0 - normalized
        return normalized

    @staticmethod
    def _eye_line_roll(left_eye: Any, right_eye: Any) -> float:
        angle = math.degrees(
            math.atan2(right_eye.y - left_eye.y, right_eye.x - left_eye.x)
        )
        if angle > 90.0:
            angle -= 180.0
        elif angle <= -90.0:
            angle += 180.0
        return float(angle)

    @staticmethod
    def _landmark_yaw(nose: Any, left_eye: Any, right_eye: Any) -> float:
        eye_span = abs(right_eye.x - left_eye.x)
        if eye_span < 1e-6:
            return 0.0
        eye_mid_x = (left_eye.x + right_eye.x) / 2.0
        return float((nose.x - eye_mid_x) / eye_span * 90.0)

    @staticmethod
    def _estimate_confidence(
        face_scale: float,
        bbox: Tuple[float, float, float, float],
        yaw: Optional[float],
        pitch: Optional[float],
        left_eye_open: Optional[float],
        right_eye_open: Optional[float],
        gaze_x: Optional[float],
        gaze_y: Optional[float],
    ) -> float:
        score = 1.0
        if face_scale < 0.12:
            score -= 0.35
        if bbox[0] < 0.02 or bbox[1] < 0.02 or bbox[2] > 0.98 or bbox[3] > 0.98:
            score -= 0.25
        if yaw is None or pitch is None:
            score -= 0.35
        if left_eye_open is None or right_eye_open is None:
            score -= 0.20
        if gaze_x is None or gaze_y is None:
            score -= 0.20
        return float(max(0.0, min(1.0, score)))
