import os
import time
import collections
from typing import List, Tuple, Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import (
    FocusState,
    Mode,
    MODE_NAME,
    INTERVAL_SECONDS,
    COUNTDOWN_SECONDS,
    NO_FACE_TO_BREAK_SECONDS,
    BREAK_SESSION_END_SECONDS,
    MAX_MINUTES,
)
from judge import FocusJudge
from logger import FocusLogger

# 대시보드 캔버스 해상도
DASH_W = 640   # 가로
DASH_H = 460   # 세로

# 그래프 바 사이 간격 (픽셀)
BAR_GAP = 2

# ----- 색상 팔레트 (BGR 기준, Pillow에서는 RGB로 변환해서 사용) -----
DASH_BG_COLOR = (248, 250, 253)      # 전체 배경
GRAPH_BG_COLOR = (255, 255, 255)     # 그래프 박스 내부 배경

TEXT_MAIN = (60, 60, 60)             # 기본 진한 회색 텍스트
TEXT_MUTED = (120, 120, 120)         # 보조 텍스트
TEXT_HIGHLIGHT = (40, 80, 160)       # 포인트 텍스트 (파란 계열)
TEXT_ERROR = (0, 0, 200)             # 에러 (빨강계열)

GRID_LIGHT = (225, 225, 225)         # 얇은 그리드
GRID_BOLD = (200, 200, 200)          # 0,50,100% 기준 그리드
AXIS_COLOR = (170, 170, 170)         # 축선

BAR_BREAK = (210, 210, 210)          # 완전 휴식(회색 바)

BAR_RED = (0, 0, 230)                # 낮은 집중 (빨강)
BAR_ORANGE = (0, 160, 255)           # 보통 (주황)
BAR_GREEN_LIGHT = (120, 200, 120)    # 양호 (연초록)
BAR_GREEN_DARK = (0, 140, 0)         # 매우 좋음 (진한 초록)


def bgr_to_rgb(c: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return (c[2], c[1], c[0])


def format_elapsed(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def mode_to_label(mode: Mode) -> str:
    return MODE_NAME.get(mode, str(mode))


def summarize_second(buffer: List[FocusState]) -> Optional[FocusState]:
    if not buffer:
        return None
    counter = collections.Counter(buffer)
    return counter.most_common(1)[0][0]


def summarize_minute(
    seconds_states: List[FocusState],
) -> Tuple[FocusState, float, float, int]:
    """
    1분(최대 60개 초) 동안의 상태 리스트를 받아서:
    - 우세 상태
    - 집중 비율 (BREAK 제외)
    - BREAK 비율
    - 총 초 수
    """
    if not seconds_states:
        return FocusState.BREAK, 0.0, 1.0, 0

    total_seconds = len(seconds_states)
    counter = collections.Counter(seconds_states)
    dominant_state, _ = counter.most_common(1)[0]

    break_seconds = sum(1 for st in seconds_states if st == FocusState.BREAK)
    break_ratio = break_seconds / float(total_seconds)

    effective_seconds = total_seconds - break_seconds
    if effective_seconds <= 0:
        focus_ratio = 0.0
    else:
        focus_seconds = sum(1 for st in seconds_states if st == FocusState.FOCUS)
        focus_ratio = focus_seconds / float(effective_seconds)

    return dominant_state, focus_ratio, break_ratio, total_seconds


def draw_camera_overlay(
    frame: np.ndarray,
    focus_state: FocusState,
    mode: Mode,
    has_origin: bool,
    countdown_text: Optional[str] = None,
) -> np.ndarray:
    """
    카메라 화면 오버레이:
    - 상단 상태 패널: FOCUS / MODE / ORIGIN (+ 필요시 카운트다운)
    (중앙 집중 사각형은 제거)
    """
    h, w, _ = frame.shape

    # 상태별 색 + 텍스트
    if focus_state == FocusState.FOCUS:
        color = (0, 255, 0)
        status = "FOCUS"
    elif focus_state == FocusState.BREAK:
        color = (180, 180, 180)
        status = "BREAK"
    elif focus_state == FocusState.NO_FACE:
        color = (0, 255, 255)
        status = "NO FACE"
    elif focus_state == FocusState.SIDE:
        color = (0, 165, 255)
        status = "SIDE"
    elif focus_state == FocusState.DOWN:
        color = (0, 140, 255)
        status = "DOWN"
    elif focus_state == FocusState.NOT_CALIBRATED:
        color = (255, 255, 255)
        status = "NOT CALIBRATED"
    elif focus_state == FocusState.EYES_LOST:
        color = (255, 0, 255)
        status = "EYES LOST"
    else:
        color = (0, 0, 255)
        status = "NO FOCUS"

    # 상단 상태 패널 (반투명 박스)
    overlay = frame.copy()
    panel_x1, panel_y1 = 15, 15
    panel_x2, panel_y2 = 340, 150
    cv2.rectangle(
        overlay,
        (panel_x1, panel_y1),
        (panel_x2, panel_y2),
        (0, 0, 0),
        -1,
    )
    alpha = 0.45
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    # 텍스트: FOCUS / MODE / ORIGIN (+ countdown)
    line_h = 26
    tx = panel_x1 + 12
    ty = panel_y1 + 25

    cv2.putText(
        frame,
        f"FOCUS : {status}",
        (tx, ty),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
    )
    ty += line_h

    cv2.putText(
        frame,
        f"MODE  : {mode_to_label(mode)}",
        (tx, ty),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (240, 240, 240),
        2,
    )
    ty += line_h

    origin_text = "READY" if has_origin else "NOT SET"
    origin_color = (0, 220, 0) if has_origin else (0, 0, 255)
    cv2.putText(
        frame,
        f"ORIGIN: {origin_text}",
        (tx, ty),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        origin_color,
        2,
    )
    ty += line_h

    if countdown_text is not None:
        cv2.putText(
            frame,
            countdown_text,
            (tx, ty),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )

    return frame


def _load_fonts():
    """Pillow용 폰트 세트 로딩 (안 되면 기본 폰트로 fallback)."""
    try:
        # 윈도우 기준, Arial 있으면 쓸만함
        font_big = ImageFont.truetype("arial.ttf", 18)
        font_med = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        font_big = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()
    return font_big, font_med, font_small


def draw_dashboard_image(
    state: str,
    mode: Mode,
    elapsed_seconds: int,
    total_break_seconds: int,
    minute_results: List[Tuple[int, float, float, int]],
    last_error: Optional[str],
    session_ended: bool,
) -> Tuple[np.ndarray, Image.Image]:
    """
    Pillow로 대시보드를 그려서:
    - OpenCV용 BGR ndarray
    - 원본 Pillow Image
    둘 다 리턴한다.
    """
    font_big, font_med, font_small = _load_fonts()

    # PIL Image (RGB) 생성
    img_pil = Image.new(
        "RGB",
        (DASH_W, DASH_H),
        bgr_to_rgb(DASH_BG_COLOR),
    )
    draw = ImageDraw.Draw(img_pil)

    # ----- 세션 종료 시 평균 ratio 계산 (가중 평균) -----
    avg_focus_pct: Optional[float] = None
    if session_ended and minute_results:
        sum_focus_sec = 0.0
        sum_eff_sec = 0.0
        for _idx, focus_ratio, break_ratio, total_sec in minute_results:
            eff = total_sec * (1.0 - break_ratio)  # 쉬는 시간 제외 유효 초
            if eff <= 0:
                continue
            sum_eff_sec += eff
            sum_focus_sec += focus_ratio * eff
        if sum_eff_sec > 0:
            avg_focus_pct = (sum_focus_sec / sum_eff_sec) * 100.0

    # ----- 상단 레이아웃: 2열 ----- #
    margin = 40
    line_h = 24

    # 왼쪽 컬럼(현재 상태)
    left_x = margin
    left_y = margin + 10

    draw.text(
        (left_x, left_y),
        f"STATE : {state}",
        font=font_big,
        fill=bgr_to_rgb(TEXT_MAIN),
    )
    left_y += line_h
    draw.text(
        (left_x, left_y),
        f"MODE  : {mode_to_label(mode)}",
        font=font_med,
        fill=bgr_to_rgb(TEXT_MUTED),
    )
    left_y += line_h
    draw.text(
        (left_x, left_y),
        f"Elapsed session : {format_elapsed(elapsed_seconds)}",
        font=font_med,
        fill=bgr_to_rgb(TEXT_MUTED),
    )
    left_y += line_h
    draw.text(
        (left_x, left_y),
        f"Total rest time : {format_elapsed(total_break_seconds)}",
        font=font_med,
        fill=bgr_to_rgb(TEXT_HIGHLIGHT),
    )
    left_y += line_h

    if last_error:
        draw.text(
            (left_x, left_y),
            f"ERROR : {last_error}",
            font=font_small,
            fill=bgr_to_rgb(TEXT_ERROR),
        )
        left_y += line_h

    # 오른쪽 컬럼(세션 결과 – 종료 후에만)
    right_x = DASH_W // 2 + 10
    right_y = margin + 10

    if session_ended:
        draw.text(
            (right_x, right_y),
            "SESSION RESULT",
            font=font_med,
            fill=bgr_to_rgb(TEXT_MAIN),
        )
        right_y += line_h

        if avg_focus_pct is not None:
            draw.text(
                (right_x, right_y),
                f"Avg focus ratio : {avg_focus_pct:5.1f}%",
                font=font_med,
                fill=bgr_to_rgb(TEXT_HIGHLIGHT),
            )
            right_y += line_h

    # 그래프 시작 y는 양쪽 중 더 아래쪽 기준
    top_after_header = max(left_y, right_y)

    # ---- 그래프 영역 설정 ----
    graph_top = top_after_header + 10
    graph_bottom = DASH_H - 150
    graph_left = margin
    graph_right = DASH_W - margin
    graph_height = graph_bottom - graph_top
    graph_width = graph_right - graph_left

    # 그래프 배경
    draw.rectangle(
        [graph_left, graph_top, graph_right, graph_bottom],
        fill=bgr_to_rgb(GRAPH_BG_COLOR),
        outline=None,
    )

    # 가로 그리드
    for pct in range(0, 101, 10):
        yy = int(graph_bottom - (pct / 100.0) * graph_height)
        grid_color = GRID_BOLD if pct in (0, 50, 100) else GRID_LIGHT
        draw.line(
            [graph_left, yy, graph_right, yy],
            fill=bgr_to_rgb(grid_color),
            width=1,
        )

    # 축
    draw.line(
        [graph_left, graph_top, graph_left, graph_bottom],
        fill=bgr_to_rgb(AXIS_COLOR),
        width=1,
    )
    draw.line(
        [graph_left, graph_bottom, graph_right, graph_bottom],
        fill=bgr_to_rgb(AXIS_COLOR),
        width=1,
    )

    # y축 눈금
    for pct in (0, 50, 100):
        yy = int(graph_bottom - (pct / 100.0) * graph_height)
        draw.line(
            [graph_left - 5, yy, graph_left + 5, yy],
            fill=bgr_to_rgb(AXIS_COLOR),
            width=1,
        )
        draw.text(
            (graph_left - 35, yy - 7),
            f"{pct}",
            font=font_small,
            fill=bgr_to_rgb(TEXT_MAIN),
        )

    # x축 범위
    if minute_results:
        max_index = max(m for (m, *_rest) in minute_results)
        max_minutes = max(MAX_MINUTES, max_index + 1)
    else:
        max_minutes = MAX_MINUTES

    if max_minutes <= 0:
        max_minutes = 1

    bar_width = graph_width / max_minutes
    bar_origin = graph_left + int(bar_width * 0.5)

    # x축 눈금
    step = 10 if max_minutes >= 10 else max_minutes
    if step <= 0:
        step = 1
    for m in range(0, max_minutes + 1, step):
        xx = int(graph_left + (m / max_minutes) * graph_width)
        draw.line(
            [xx, graph_bottom - 4, xx, graph_bottom + 4],
            fill=bgr_to_rgb(AXIS_COLOR),
            width=1,
        )
        draw.text(
            (xx - 8, graph_bottom + 6),
            f"{m}",
            font=font_small,
            fill=bgr_to_rgb(TEXT_MAIN),
        )

    # 바 그리기
    for minute_index, focus_ratio, break_ratio, total_seconds in minute_results:
        if minute_index < 0:
            continue

        x0 = int(bar_origin + minute_index * bar_width)
        x1 = int(bar_origin + (minute_index + 1) * bar_width) - 1

        x0 += BAR_GAP
        x1 -= BAR_GAP
        if x1 <= x0:
            x1 = x0 + 1

        if total_seconds == 0 or break_ratio >= 0.999:
            bar_pct = 100.0
            color = BAR_BREAK
        else:
            focus_pct = focus_ratio * 100.0
            bar_pct = max(0.0, min(100.0, focus_pct))

            if bar_pct < 33.0:
                color = BAR_RED
            elif bar_pct < 66.0:
                color = BAR_ORANGE
            elif bar_pct < 85.0:
                color = BAR_GREEN_LIGHT
            else:
                color = BAR_GREEN_DARK

        bar_height_px = int((bar_pct / 100.0) * graph_height)
        y0 = graph_bottom - bar_height_px
        y1 = graph_bottom

        draw.rectangle(
            [x0, y0, x1, y1],
            fill=bgr_to_rgb(color),
            outline=None,
        )

    # SHORTCUTS 영역
    title_y = graph_bottom + 40
    draw.text(
        (margin, title_y),
        "SHORTCUTS",
        font=font_med,
        fill=bgr_to_rgb(TEXT_MAIN),
    )

    line_gap = 16
    start_y = title_y + 18

    shortcuts = [
        "S : Start session (5s calibration)",
        "C : Origin / re-calibration",
        "R : Toggle break (manual rest)",
        "Q : End session (freeze graph)",
        "ESC : Exit program (from PREVIEW/ENDED)",
        "1/2/3 : Mode WEAK / NORMAL / STRONG",
    ]

    half = (len(shortcuts) + 1) // 2
    col1_x = margin
    col2_x = DASH_W // 2

    for i, line in enumerate(shortcuts):
        if i < half:
            tx = col1_x
            ty = start_y + i * line_gap
        else:
            tx = col2_x
            ty = start_y + (i - half) * line_gap

        draw.text(
            (tx, ty),
            line,
            font=font_small,
            fill=bgr_to_rgb(TEXT_MUTED),
        )

    # Pillow → OpenCV(BGR) 변환
    dash_rgb = np.array(img_pil)
    dash_bgr = cv2.cvtColor(dash_rgb, cv2.COLOR_RGB2BGR)

    return dash_bgr, img_pil


def main() -> None:
    # logs 폴더 보장
    if not os.path.exists("logs"):
        os.makedirs("logs", exist_ok=True)

    mode = Mode.MODE_2
    log_path = time.strftime("logs/focus_%Y%m%d_%H%M.csv")
    judge = FocusJudge(mode)
    logger = FocusLogger(log_path, mode)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera open failed.")
        return

    # 창 설정
    cv2.namedWindow("FOCUS CAM", cv2.WINDOW_NORMAL)
    cv2.namedWindow("FOCUS DASHBOARD", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("FOCUS DASHBOARD", DASH_W, DASH_H)

    state = "PREVIEW"  # PREVIEW / CALIBRATING / RUNNING / SESSION_ENDED
    has_origin = False

    session_start_time = time.time()
    run_start_time: Optional[float] = None
    calib_start_time: Optional[float] = None
    session_duration_sec: Optional[int] = None

    current_second = int(time.time())
    second_raw_buffer: List[FocusState] = []
    minute_buffer: List[FocusState] = []
    minute_index = -1
    minute_results: List[Tuple[int, float, float, int]] = []

    total_break_seconds = 0
    last_error_msg: Optional[str] = None

    manual_break = False
    no_face_consec_secs = 0
    break_consec_secs = 0
    session_ended = False

    last_dashboard_pil: Optional[Image.Image] = None

    def finalize_minute_buffer() -> None:
        nonlocal minute_index, minute_buffer, minute_results
        if not minute_buffer:
            return
        minute_index += 1
        dom_state, focus_ratio, break_ratio, total_seconds = summarize_minute(
            minute_buffer
        )
        minute_results.append((minute_index, focus_ratio, break_ratio, total_seconds))
        if len(minute_results) > 240:
            minute_results[:] = minute_results[-240:]
        minute_buffer.clear()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                last_error_msg = "Camera read failed"
                break

            now_ts = time.time()
            now_sec = int(now_ts)
            key = cv2.waitKey(1) & 0xFF

            # ESC
            if key == 27:
                if state in ("PREVIEW", "SESSION_ENDED"):
                    break
                else:
                    last_error_msg = "Press Q to end session before ESC."

            # 모드 변경
            if key == ord("1"):
                mode = Mode.MODE_1
                judge.set_mode(mode)
                logger.mode = mode
            elif key == ord("2"):
                mode = Mode.MODE_2
                judge.set_mode(mode)
                logger.mode = mode
            elif key == ord("3"):
                mode = Mode.MODE_3
                judge.set_mode(mode)
                logger.mode = mode

            # C : 원점
            if key in (ord("c"), ord("C")):
                ok = judge.calibrate_from_last()
                if ok:
                    has_origin = True
                    last_error_msg = None
                    print("Origin set.")

            # S : 세션 시작
            if (
                key in (ord("s"), ord("S"))
                and has_origin
                and state in ("PREVIEW", "SESSION_ENDED")
            ):
                state = "CALIBRATING"
                calib_start_time = time.time()
                current_second = int(time.time())
                second_raw_buffer.clear()
                minute_buffer.clear()
                minute_index = -1
                minute_results.clear()
                total_break_seconds = 0
                manual_break = False
                no_face_consec_secs = 0
                break_consec_secs = 0
                session_start_time = time.time()
                session_duration_sec = None
                session_ended = False
                print("Start requested. CALIBRATING for 5 seconds.")

            # R : 수동 휴식 토글
            if key in (ord("r"), ord("R")) and state == "RUNNING":
                manual_break = not manual_break
                if manual_break:
                    print("Manual break ON")
                else:
                    print("Manual break OFF")
                    no_face_consec_secs = 0
                    break_consec_secs = 0

            # Q : 세션 종료
            if key in (ord("q"), ord("Q")) and state == "RUNNING":
                finalize_minute_buffer()
                session_duration_sec = int(now_ts - (run_start_time or session_start_time))
                state = "SESSION_ENDED"
                session_ended = True
                manual_break = False
                print("Session ended by user.")

            # 경과 시간
            if state in ("RUNNING", "CALIBRATING"):
                elapsed_session = int(now_ts - (run_start_time or session_start_time))
            elif state == "SESSION_ENDED" and session_duration_sec is not None:
                elapsed_session = session_duration_sec
            else:
                elapsed_session = 0

            # PREVIEW / SESSION_ENDED
            if state in ("PREVIEW", "SESSION_ENDED"):
                focus_state_raw, _info, _err = judge.update(frame)
                cam_state = focus_state_raw
                cam_frame = draw_camera_overlay(
                    frame.copy(), cam_state, mode, has_origin
                )
                dash_img, dash_pil = draw_dashboard_image(
                    state=state,
                    mode=mode,
                    elapsed_seconds=elapsed_session,
                    total_break_seconds=total_break_seconds,
                    minute_results=minute_results,
                    last_error=last_error_msg,
                    session_ended=session_ended,
                )
                last_dashboard_pil = dash_pil
                cv2.imshow("FOCUS CAM", cam_frame)
                cv2.imshow("FOCUS DASHBOARD", dash_img)
                continue

            # CALIBRATING
            if state == "CALIBRATING":
                focus_state_raw, _info, _err = judge.update(frame)

                waited = int(now_ts - (calib_start_time or now_ts))
                remain = max(0, COUNTDOWN_SECONDS - waited)
                if remain <= 0:
                    state = "RUNNING"
                    run_start_time = time.time()
                    no_face_consec_secs = 0
                    break_consec_secs = 0
                    manual_break = False
                    print("RUNNING started.")

                countdown_text = f"Starting in {remain} sec..."
                cam_frame = draw_camera_overlay(
                    frame.copy(),
                    focus_state_raw,
                    mode,
                    has_origin,
                    countdown_text=countdown_text,
                )
                dash_img, dash_pil = draw_dashboard_image(
                    state=state,
                    mode=mode,
                    elapsed_seconds=elapsed_session,
                    total_break_seconds=total_break_seconds,
                    minute_results=minute_results,
                    last_error=last_error_msg,
                    session_ended=False,
                )
                last_dashboard_pil = dash_pil
                cv2.imshow("FOCUS CAM", cam_frame)
                cv2.imshow("FOCUS DASHBOARD", dash_img)
                continue

            # RUNNING
            focus_state_raw, _info, _err = judge.update(frame)
            second_raw_buffer.append(focus_state_raw)

            # 초 단위 요약
            if now_sec != current_second:
                sec_raw = summarize_second(second_raw_buffer)
                second_raw_buffer.clear()
                current_second = now_sec

                if sec_raw == FocusState.NO_FACE and not manual_break:
                    no_face_consec_secs += 1
                else:
                    if not manual_break:
                        no_face_consec_secs = 0

                auto_break = (
                    not manual_break and no_face_consec_secs >= NO_FACE_TO_BREAK_SECONDS
                )

                if manual_break or auto_break:
                    sec_eff = FocusState.BREAK
                else:
                    sec_eff = sec_raw or FocusState.BREAK

                minute_buffer.append(sec_eff)

                if sec_eff == FocusState.BREAK:
                    total_break_seconds += 1
                    break_consec_secs += 1
                else:
                    break_consec_secs = 0

                if len(minute_buffer) >= INTERVAL_SECONDS:
                    finalize_minute_buffer()

                # 자동 세션 종료
                if (
                    break_consec_secs >= BREAK_SESSION_END_SECONDS
                    and not session_ended
                ):
                    finalize_minute_buffer()
                    session_duration_sec = int(
                        now_ts - (run_start_time or session_start_time)
                    )
                    state = "SESSION_ENDED"
                    session_ended = True
                    manual_break = False
                    print("Session ended automatically (rest >= 10min).")

            # 카메라 오버레이 상태
            if manual_break or (
                not manual_break and no_face_consec_secs >= NO_FACE_TO_BREAK_SECONDS
            ):
                cam_state = FocusState.BREAK
            else:
                cam_state = focus_state_raw

            cam_frame = draw_camera_overlay(
                frame.copy(), cam_state, mode, has_origin
            )
            dash_img, dash_pil = draw_dashboard_image(
                state=state,
                mode=mode,
                elapsed_seconds=elapsed_session,
                total_break_seconds=total_break_seconds,
                minute_results=minute_results,
                last_error=last_error_msg,
                session_ended=session_ended,
            )
            last_dashboard_pil = dash_pil
            cv2.imshow("FOCUS CAM", cam_frame)
            cv2.imshow("FOCUS DASHBOARD", dash_img)

    finally:
        cap.release()
        try:
            judge.close()
        except Exception:
            pass
        cv2.destroyAllWindows()

        # ---- 세션 종료 후 대시보드 결과 이미지 저장 ----
        if session_ended and last_dashboard_pil is not None:
            if not os.path.exists("result"):
                os.makedirs("result", exist_ok=True)
            out_path = time.strftime("result/focus_result_%Y%m%d_%H%M%S.png")
            last_dashboard_pil.save(out_path)
            print(f"Session dashboard saved to: {out_path}")


if __name__ == "__main__":
    main()
