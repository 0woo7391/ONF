import csv
import time
from typing import List, Optional, Tuple

from config import FocusState, Mode


class FocusLogger:
    """
    1분 단위 요약을 CSV로 저장하는 로거.
    """

    def __init__(self, csv_path: str, mode: Mode) -> None:
        self.csv_path = csv_path
        self.mode = mode
        self._sec_states: List[FocusState] = []
        self._header_written = False

    # ----------------- 내부 유틸 -----------------

    def _ensure_header(self) -> None:
        if self._header_written:
            return
        try:
            with open(self.csv_path, mode="x", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "mode",
                        "focus_ratio",
                        "elapsed_sec",
                    ]
                )
        except FileExistsError:
            # 이미 있으면 헤더 추가 안 함
            pass
        self._header_written = True

    # ----------------- 매 프레임 -----------------

    def add_state(self, state: FocusState) -> None:
        """초 단위 요약에서 사용하기 위해 raw state를 모아 둔다."""
        self._sec_states.append(state)

    # ----------------- 1분 요약 -----------------

    def flush_minute(self, elapsed_sec: int) -> Tuple[Optional[float], Optional[Mode]]:
        """
        1분이 끝났을 때 호출해서,
        - 그 1분 동안의 집중 비율(focus_ratio)과 현재 모드(mode)를 반환하고
        - CSV에 한 줄 기록.

        반환:
            (ratio, mode)
            - ratio: 0~1, 데이터 없으면 None
            - mode: 현재 모드, 데이터 없으면 None
        """
        self._ensure_header()

        if not self._sec_states:
            # 이 1분 동안 기록이 없으면 "휴식"으로 보고 빈 바 취급
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([ts, "", "", elapsed_sec])
            return None, None

        total = len(self._sec_states)
        focus_frames = sum(1 for s in self._sec_states if s == FocusState.FOCUS)
        ratio = focus_frames / float(total)

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([ts, int(self.mode), round(ratio, 3), elapsed_sec])

        # 버퍼 비우기
        self._sec_states.clear()
        return ratio, self.mode
