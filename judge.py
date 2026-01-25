import time
from typing import Optional, Sequence, Tuple, Any

import cv2
import mediapipe as mp
import numpy as np

from config import FocusState, Mode, MODE_CONFIG


class Calibration:
    def __init__(self) -> None:
        # 코 기준 yaw / pitch / iris 기준값
        self.yaw: Optional[float] = None
        self.pitch: Optional[float] = None
        self.iris_center: Optional[float] = None

    @property
    def ready(self) -> bool:
        return (
            self.yaw is not None
            and self.pitch is not None
            and self.iris_center is not None
        )


class FocusJudge:
    """
    Mediapipe FaceMesh 기반 집중 판정 클래스.

    main 에서는:
        state, info, err = judge.update(frame)
        judge.calibrate_from_last()
    이런 식으로 사용.
    """

    def __init__(self, mode: Mode) -> None:
        self.mode: Mode = mode
        self.config = MODE_CONFIG.get(mode, MODE_CONFIG[Mode.MODE_2])

        self.calib = Calibration()
        self.last_landmarks: Optional[Sequence] = None

        self._mp_face = mp.solutions.face_mesh
        self._face_mesh = self._mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # 눈 감김 지속 시간 체크용
        self.eyes_lost_start: Optional[float] = None
        # 마지막 계산값 (디버그용)
        self._last_yaw: float = 0.0
        self._last_pitch: float = 0.0
        self._last_iris: float = 0.5

    # ----------------- 모드 변경 -----------------

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode
        self.config = MODE_CONFIG.get(mode, self.config)
        print(
            f"[MODE] {int(mode)} -> yaw_th={self.config['yaw_side_thresh']:.3f}, "
            f"pitch_th={self.config['pitch_thresh']:.3f}"
        )

    # ----------------- 캘리브레이션 -----------------

    def calibrate_from_last(self) -> bool:
        """
        C 키 눌렀을 때 호출.
        마지막으로 검출한 얼굴을 기준으로 yaw/pitch/iris 기준값을 저장.
        """
        if self.last_landmarks is None:
            print("[CALIB] last_landmarks 없음 → 기준 갱신 실패")
            return False

        yaw, pitch = self._calc_yaw_pitch(self.last_landmarks)
        iris = self._calc_iris_ratio(self.last_landmarks)

        self.calib.yaw = yaw
        self.calib.pitch = pitch
        self.calib.iris_center = iris

        self.eyes_lost_start = None

        print(f"[CALIB] 기준 갱신 → yaw={yaw:.3f}, pitch={pitch:.3f}, iris={iris:.3f}")
        return True

    # ----------------- 메인 진입점 -----------------

    def update(self, frame: Any):
        """
        BGR frame 을 받아서:
        - 현재 FocusState
        - 디버그용 info(dict)
        - error_msg(str 또는 None)
        를 반환.
        """
        error_msg: Optional[str] = None

        landmarks = None
        try:
            landmarks = self._process_frame(frame)
        except Exception as e:
            error_msg = f"FaceMesh error: {e}"

        if landmarks is not None:
            self.last_landmarks = landmarks

        # 얼굴이 전혀 안 잡힌 경우
        if landmarks is None:
            self.eyes_lost_start = None
            state = FocusState.NO_FACE
            info = {
                "mode": int(self.mode),
                "reason": "no_face",
            }
            return state, info, error_msg

        # 캘리브레이션 안 되어 있으면
        if not self.calib.ready:
            state = FocusState.NOT_CALIBRATED
            info = {
                "mode": int(self.mode),
                "reason": "not_calibrated",
            }
            return state, info, error_msg

        # yaw / pitch / iris 계산
        yaw, pitch = self._calc_yaw_pitch(landmarks)
        iris = self._calc_iris_ratio(landmarks)
        self._last_yaw = yaw
        self._last_pitch = pitch
        self._last_iris = iris

        dyaw = yaw - (self.calib.yaw or 0.0)
        dpitch = pitch - (self.calib.pitch or 0.0)
        diris = iris - (self.calib.iris_center or 0.5)

        cfg = self.config
        yaw_th = cfg["yaw_side_thresh"]
        pitch_th = cfg["pitch_thresh"]
        iris_low, iris_high = cfg["iris_center_range"]

        # 눈 떠있는지 체크
        eyes_ok = self._eyes_open(landmarks)

        # 1) 눈을 오래 감고 있으면 EYES_LOST
        if not eyes_ok:
            if self.eyes_lost_start is None:
                self.eyes_lost_start = time.time()
            else:
                if time.time() - self.eyes_lost_start >= 60.0:
                    state = FocusState.EYES_LOST
                    info = {
                        "mode": int(self.mode),
                        "reason": "eyes_lost",
                        "yaw": float(yaw),
                        "pitch": float(pitch),
                        "iris": float(iris),
                    }
                    return state, info, error_msg
        else:
            self.eyes_lost_start = None

        # 2) 코 기준 고개 회전: yaw/pitch 기준에서 많이 벗어났으면 SIDE
        if abs(dyaw) > yaw_th or abs(dpitch) > pitch_th:
            state = FocusState.SIDE
        # 3) 동공 위치가 기준 범위에서 벗어나면 NO_FOCUS
        elif iris < iris_low or iris > iris_high:
            state = FocusState.NO_FOCUS
        # 4) 나머지는 FOCUS
        else:
            state = FocusState.FOCUS

        info = {
            "mode": int(self.mode),
            "yaw": float(yaw),
            "pitch": float(pitch),
            "iris": float(iris),
            "dyaw": float(dyaw),
            "dpitch": float(dpitch),
            "diris": float(diris),
        }
        return state, info, error_msg

    # ----------------- 내부: 프레임 → 랜드마크 -----------------

    def _process_frame(self, frame: np.ndarray) -> Optional[Sequence]:
        if frame is None or frame.size == 0:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        landmarks = result.multi_face_landmarks[0].landmark
        return landmarks

    # ----------------- 내부: yaw/pitch 계산 -----------------

    def _calc_yaw_pitch(self, landmarks: Sequence) -> Tuple[float, float]:
        """
        코 위치 자체를 기준으로 yaw/pitch 계산.
        - yaw  : nose.x
        - pitch: nose.y
        """
        NOSE_TIP = 1  # MediaPipe FaceMesh nose tip index
        nose = landmarks[NOSE_TIP]
        yaw = nose.x
        pitch = nose.y
        return yaw, pitch

    # ----------------- 내부: iris 위치 계산 -----------------

    def _calc_iris_ratio(self, landmarks: Sequence) -> float:
        """
        왼쪽 눈 기준 동공 x 위치 비율(0~1).
        """
        LEFT_EYE_OUTER = 33
        LEFT_EYE_INNER = 133
        LEFT_IRIS_CENTER = 468  # refine_landmarks=True일 때

        eye_left = landmarks[LEFT_EYE_OUTER].x
        eye_right = landmarks[LEFT_EYE_INNER].x
        iris_x = landmarks[LEFT_IRIS_CENTER].x

        eye_width = eye_right - eye_left
        if abs(eye_width) < 1e-6:
            return 0.5

        ratio = (iris_x - eye_left) / eye_width
        if ratio < 0.0:
            ratio = 0.0
        elif ratio > 1.0:
            ratio = 1.0
        return ratio

    # ----------------- 내부: 눈 떠 있는지 판정 -----------------

    def _eyes_open(self, landmarks: Sequence) -> bool:
        """
        간단한 눈 뜸/감김 판정:
        위/아래 눈꺼풀 사이 거리 합이 일정 이상이면 "눈을 뜬 상태"로 본다.
        """
        # 왼쪽 눈 (위/아래)
        left_eye = (159, 145)
        # 오른쪽 눈 (위/아래)
        right_eye = (386, 374)

        def gap(a: int, b: int) -> float:
            return abs(landmarks[a].y - landmarks[b].y)

        gap_sum = gap(*left_eye) + gap(*right_eye)
        return gap_sum > 0.02

    # ----------------- 리소스 해제 -----------------

    def close(self) -> None:
        try:
            if self._face_mesh is not None:
                self._face_mesh.close()
        except Exception:
            pass
