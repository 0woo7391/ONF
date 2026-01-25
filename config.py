from enum import IntEnum

# -------------------------
# 집중 상태(enum)
# -------------------------


class FocusState(IntEnum):
    NOT_CALIBRATED = 0   # 아직 원점(캘리브레이션) 안됨
    NO_FACE = 1          # 얼굴 없음
    EYES_LOST = 2        # 눈을 오래 감고 있음
    SIDE = 3             # 고개를 옆으로 돌림
    FOCUS = 4            # 집중 상태
    NO_FOCUS = 5         # 딴짓 / 시선 이탈
    DOWN = 6             # 고개를 아래로 숙임 (지금은 안 써도 남겨둠)
    BREAK = 7            # 휴식 상태


# -------------------------
# 모드(enum)
# -------------------------


class Mode(IntEnum):
    MODE_1 = 1  # WEAK
    MODE_2 = 2  # NORMAL
    MODE_3 = 3  # STRONG


MODE_NAME = {
    Mode.MODE_1: "WEAK",
    Mode.MODE_2: "NORMAL",
    Mode.MODE_3: "STRONG",
}

# -------------------------
# 모드별 설정값 (임계값은 예시값, 실제 환경 맞춰 튜닝)
# -------------------------

MODE_CONFIG = {
    Mode.MODE_1: {  # WEAK
        "yaw_side_thresh": 0.08,   # 코 x 기준 허용 오차
        "pitch_thresh": 0.10,      # 코 y 기준 허용 오차
        "iris_center_range": (0.27, 0.75),
    },
    Mode.MODE_2: {  # NORMAL
        "yaw_side_thresh": 0.05,
        "pitch_thresh": 0.06,
        "iris_center_range": (0.30, 0.73),
    },
    Mode.MODE_3: {  # STRONG
        "yaw_side_thresh": 0.02,
        "pitch_thresh": 0.03,
        "iris_center_range": (0.32, 0.68),
    },
}

# -------------------------
# 공통 상수
# -------------------------

# 1분 요약 간격(초)
INTERVAL_SECONDS = 60

# 측정 시작 전 카운트다운(초)
COUNTDOWN_SECONDS = 5

# NO_FACE 5분 연속 → 쉬는시간 진입
NO_FACE_TO_BREAK_SECONDS = 5 * 60

# 쉬는시간(BREAK) 10분 연속 → 세션 자동 종료
BREAK_SESSION_END_SECONDS = 10 * 60

# 그래프 기본 x축 기준 (분)
MAX_MINUTES = 60

