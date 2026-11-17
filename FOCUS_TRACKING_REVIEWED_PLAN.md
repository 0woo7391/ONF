# ONF 포커스 판정·자세 추적 개선 설계

> Documentation reconciliation (2026-11-16): Retained detailed tracking contract and historical checkpoints. Current status and hardware acceptance are consolidated in the documentation map; unchecked old tasks are not automatically new work. [Documentation map](docs/README.md).

작성일: 2026-09-29  
근거: 2026-09-28 소스 검토 및 독립적인 숫자 입력 재현 검사  
상태: 검토를 반영한 구현 계획. 이 문서 작성으로 코드를 수정하거나 빌드하지 않았다.

## 1. 문서의 적용 범위

이 문서는 눈·머리 측정, 화면/필기 보정, 주의 판정, 관측 공백의 시간 집계를 다룬다. 해당 범위에서는 이전 `ATTENTION_AREA_IMPROVEMENT_PLAN.md`보다 이 문서를 우선한다. 이전 문서의 UI 전환 계획은 현재 구현 상태를 다시 확인한 뒤 참고한다.

`NEXT_FIXES_AND_UI_DIRECTION.md`의 플래너·기록·일반 UI 항목은 별도 작업이다. 이번 작업에 섞지 않는다.

### 상태 구분

- **확인됨:** 현재 소스에서 확인한 동작 또는 숫자 입력으로 재현한 현상.
- **수정 설계:** 확인된 문제를 해결하기 위한 변경안. 구현 완료를 뜻하지 않는다.
- **검증 후보:** 실제 관측과 비교하기 전에는 개선 여부를 확정하지 않는 알고리즘.
- **정책 미정:** 사용자와 의미를 확정하기 전까지 현재 동작을 유지할 항목.

### 유지할 것

- 기존 MediaPipe, OpenCV, NumPy, PySide6/QML과 현재 모듈 구조.
- 화면·필기 프로필의 독립성, 같은 측정 방식 안에서 새 보정 실패·취소 시 이전 프로필 보존.
- 수동 휴식 우선, 기존 얼굴 없음의 자동 휴식 정책, 사용자 설정의 이탈 알림 시간.
- 플래너·뽀모도로·프로그램 사용 추적·기록 DB의 기존 기능과 데이터.
- 미리보기 숨김과 실제 분석 중단의 구분. 미리보기를 숨겨도 분석은 계속한다.

### 제외할 것

- EXE 빌드·교체, 커밋·푸시, 전체 UI 재작성, 새 의존성 도입.
- 전신·손·휴대폰 감시, 인지적 집중의 직접 측정 주장.
- 무제한 자동 기준 갱신, 임계값을 무조건 넓히는 보정.
- 필수 녹화 영상 수집, 대규모 학습 모델 교체, 관련 없는 코드 정리.

## 2. 목표와 측정의 한계

목표는 특정 자세를 유지하는지 감시하는 것이 아니라, 관측 가능한 범위에서 설정한 화면 또는 필기 영역을 향한 시각적 주의를 추정하는 것이다.

카메라 기종·설치 위치·화각이 달라도 사용자의 실제 작업 환경에서 보정한다. 물리적인 카메라 좌표나 모니터 위치를 숫자로 입력하게 하지 않는다. 단, 어떤 위치에서도 동작한다고 보장하지 않는다.

- 눈 가림, 반사, 작은 얼굴, 극단적인 측면 촬영은 보정만으로 복구할 수 없다.
- 홍채 랜드마크는 모니터의 응시 좌표 자체가 아니다.
- 자세 추정은 카메라 내부값과 일반 얼굴 모델의 근사 오차를 가진다.
- 휴대폰과 종이가 같은 방향에 있으면 이 관측만으로 구분하지 못한다.
- 측정 불가를 늘려 집중률만 높이는 것은 정확도 개선으로 인정하지 않는다.

## 3. 현재 구현과 확인된 문제

현재도 양쪽 눈 측정, 화면/필기 프로필, 중앙값·MAD 변동 폭, 프로필 전환 히스테리시스, 프로필별 필터가 있다. 이 기능을 없는 것으로 보고 다시 만들지 않는다.

### 3.1 P1: 오류와 연속 이탈의 상태 유지

위치: `onf_v2/core/focus_policy.py`, `StateStabilizer.update()`.

- 집중 상태 다음에 처리 오류를 한 번 전달하면 기존 집중 상태가 남았다.
- `GAZE_AWAY`와 `HEAD_SIDE`를 0.2초마다 번갈아 전달하면 4초 후에도 집중으로 남았다.
- 원인 enum이 바뀔 때마다 후보 시작 시각을 초기화하는 구조가 원인이다.

### 3.2 P1: 관측 공백과 역순 시각

위치: `onf_v2/ui_qml/measurement_bridge.py`, `onf_v2/core/metrics.py`.

- 카메라 읽기 실패 시 UI만 오류로 바꾸고 반환하는 경로가 있다. 세션에 오류 상태가 전달되지 않으면 다음 집계 또는 종료까지 이전 상태가 적용될 수 있다.
- `DurationAccumulator.update()`는 음수 시간 차이를 0으로 만들지만 기준 시각은 과거로 갱신한다.
- 직접 `0, 10, 8, 11`초 입력을 전달한 재현에서 경과 11초가 합계 13초로 누적됐다.
- 역순 입력 검사는 집계기의 결함을 재현한 것이다. 실제 카메라 경로에서 같은 순서가 발생했다고 확인한 것은 아니다. 새 공백 처리와 비동기 분석을 연결할 때 반드시 막아야 한다.

### 3.3 P1: 홍채 유효성 검사와 눈 감김의 충돌

위치: `quality_gate.py`, `calibration.py`의 `normalize()`, `focus_policy.py`.

- 일부 홍채값이 없으면 눈 감김 판정보다 먼저 `LOW_CONFIDENCE`가 반환된다.
- 정규화도 시선값과 눈 열림값을 모두 요구한다. 눈꺼풀만 유효한 관측으로 눈 감김을 판단하기 어렵다.
- 눈꺼풀 추적 실패와 실제 눈 감김도 구분해야 한다. 홍채 미검출을 눈 감김으로 바로 치환하면 안 된다.

### 3.4 P1: 측정 단위와 기준값의 결합

위치: `face_analyzer.py`, `models.py`, `quality_gate.py`, `calibration.py`.

- 눈 거리와 기울기를 가로·세로 정규화 좌표에서 계산해 영상 종횡비의 영향을 받을 수 있다.
- 수직 시선을 눈꺼풀 벌어진 높이로 나눠 눈 열림 변화에 민감하다. 범위를 벗어난 시선은 `0~1`로 잘라 사용한다.
- yaw는 눈 중심 대비 코 위치 비율에 90을 곱하고, pitch는 `solvePnP` 결과를 사용한다.
- 계산식을 바꾸면 시선 허용 폭·눈 간 불일치·눈 열림 기준도 같이 검증해야 한다. 재보정만 하면 기존 고정 임계값까지 자동으로 맞아지는 것은 아니다.

### 3.5 P2: 보정 품질과 진단 기록의 의미

- `CalibrationManager`의 품질 점수는 표본 수 충족률이다. 실제 판정 정확도가 아니다.
- `FocusDecision.raw_state`에는 현재 안정화 후 상태가 들어간다. 기존 CSV만 보고 이를 프레임 원시 상태라고 해석하면 안 된다.
- 기존 CSV에는 모든 원시 랜드마크와 양쪽 눈 정보가 없다. 새 기하 계산을 그 CSV만으로 완전히 재현할 수는 없다.

### 3.6 P2: 공부시간 산식

위치: `onf_v2/app/session_database.py`의 계획별 `actual_study_seconds` 등.

일부 집계는 `FOCUS + NON_FOCUS`를 공부시간으로 사용한다. 측정 불가 시간을 포함하는 새 산식으로 바꾸면 DB 원본을 보존해도 과거 표시 수치가 달라진다. 이 변경은 버그 수정에 묶어 몰래 적용하지 않는다.

## 4. 1차 구현: 상태와 시간 정확성

### 4.1 상태 판정의 책임 분리

새 대형 상태 관리 모듈을 만들지 않고 기존 `FocusPolicy`와 `StateStabilizer`를 수정한다.

1. 수동 휴식은 최종 상태에서 계속 최우선이다.
2. 카메라·처리 오류, 유효기간이 지난 관측은 즉시 측정 불가로 전환한다. 집중 상태를 유지하는 유예를 적용하지 않는다.
3. 얼굴 없음은 기존 별도 정책으로 전달한다. 처리 오류를 얼굴 없음으로 취급하지 않는다.
4. 눈꺼풀이 유효하면 눈 감김을 먼저 판단한다. 눈이 열린 경우에 시선 유효성과 작업 영역을 판단한다.
5. 깜빡임 유예와 주의 이탈 확정은 별도로 관리한다. 눈꺼풀 품질이 나쁜 구간에 깜빡임 유예를 무조건 적용하지 않는다.

`HEAD_SIDE`, `HEAD_DOWN`, `HEAD_UP`, `GAZE_AWAY` 사이에서 원인만 바뀌면 최초 이탈 후보 시각을 유지한다. 원인별 기존 확인 시간을 적용하더라도 경과시간 계산의 시작점은 다시 잡지 않는다. 눈 감김은 별도의 눈 감김 지속 조건을 충족해야 한다.

원인 표시와 최종 집중 상태의 확정 시점을 분리한다. 휴식·측정 불가 구간을 건너뛰면서 연속 이탈이나 연속 집중을 주장하지 않는다. 이탈 알림 1분 등 기존 사용자 설정은 그대로 사용한다.

오류 후 정상 복귀에도 기존 정상 복귀 확인 시간을 적용한다. 새 유효 관측 한 프레임만으로 이전 장시간 집중을 이어 붙이지 않는다.

### 4.2 시각과 관측 신선도

- 프레임의 `timestamp`는 기존 단조 증가 시계를 유지한다. 벽시계는 날짜·저장 이름에만 사용한다.
- 프레임 촬영 시각과 결과 도착 시각을 구분해 관측 나이를 검사한다.
- 같은 프레임의 중복 결과, 마지막 반영 관측보다 오래된 결과, 이미 확정한 구간보다 과거인 결과를 배제한다.
- 누적기에 역순 시각이 들어오면 시간과 상태 모두 변경하지 않는다. `max(0, delta)`만 적용한 뒤 기준 시각을 되돌리는 처리는 금지한다.
- 정상 분석의 프레임 시각과 UI 현재 시각을 무작정 섞지 않는다. 매 UI 틱마다 집계 기준을 현재로 밀면 정상적인 분석 지연 결과까지 모두 오래된 결과가 된다.

관측 유효기간은 분석 지연을 확인해 정하는 내부 값이다. 카메라 FPS와 분석 FPS를 구분한다. 이 문서에서는 검증되지 않은 고정 초 값을 확정하지 않는다.

### 4.3 공백 구간 배분

정상 관측이 끊겼을 때 마지막 유효 상태는 정해진 유효기간까지만 유지한다. 그 이후 구간은 `UNSCORED`로 전환한다. 명시적인 카메라·처리 오류를 알게 되면 더 일찍 전환할 수 있다.

공백 시작 상태 전이는 한 번만 기록한다. 화면 갱신마다 동일 상태 전이를 추가하거나 과거 구간을 반복 집계하지 않는다. 새 유효 관측 또는 세션 종료 시 남은 측정 불가 구간을 마감한다.

세션 종료·휴식·재개·카메라 변경 이후 완료된 이전 분석 결과가 새 상태나 새 보정에 적용되지 않도록 현재 작업에 속한 결과인지 확인한다. 대기 작업은 가능하면 취소하고, 취소 불가 결과는 버린다.

성공 조건:

- 상태별 누적 합계, 분 버킷 합계, 타임라인 버킷 합계가 같은 세션 경과시간과 일치한다.
- 측정 공백이 집중으로 길게 누적되지 않는다.
- 기존 자동 휴식 소급 처리와 마지막 미완성 버킷 저장이 유지된다.
- 일반 UI 갱신과 늦은 분석 결과 때문에 이중 누적이 생기지 않는다.

### 4.4 시간 필터와 재획득

시간 누적 수정과 수치 평활화 변경은 별도 검증한다. 기존 `TemporalFilter`를 재사용하며 새 필터 계층은 만들지 않는다.

- EMA는 고정 계수 대신 `alpha = 1 - exp(-dt / tau)` 방식의 시간 기반 계수를 검증한다. `tau`는 반응 지연 비교 후 정하며 검증되지 않은 기본값을 사용자 설정에 추가하지 않는다.
- 시선 중앙값 창은 일정 프레임 수 대신 타임스탬프가 있는 최근 시간 구간으로 관리한다. 중복·역순 표본은 넣지 않는다.
- 화면·필기 필터 각각의 마지막 유효 표본 시각을 확인한다. 오래 비활성화된 프로필로 복귀하면 오래된 창을 버린다. 짧은 영역 전환마다 모든 필터를 초기화하지는 않는다.
- 눈 감김의 시작·지속시간은 유효한 눈꺼풀 관측으로 따로 확인한다. 시선 평활화 때문에 눈 감김이 계속 정상으로 남으면 안 된다.
- 같은 동작을 다른 분석 간격으로 입력해 판정 시각과 지연을 비교한다. 부드럽게 보인다는 이유만으로 느려진 필터를 채택하지 않는다.

## 5. 2차 구현: 눈 측정과 품질 검사

### 5.1 좌표 계산

정규화 랜드마크를 원본 영상의 픽셀 좌표로 변환한다. 표시용 미러링은 분석에 적용하지 않는다.

- `u`: 눈꼬리 두 점을 연결한 단위 축. 양쪽 눈이 같은 방향 규칙을 갖게 한다.
- `v`: `u`에 수직인 축. 아래쪽이 양수가 되도록 부호를 통일한다.
- `w`: 눈 가로폭, `C`: 눈꼬리 중점, `I`: 홍채 중심.
- 시선은 `dot(I - C, u) / w`, `dot(I - C, v) / w`로 계산하는 방식을 검증한다.
- 눈 열림은 여러 눈꺼풀 쌍의 평균 간격을 눈 가로폭으로 나눠 계산한다.

홍채 좌표와 눈 열림은 서로 다른 측정값이다. 새 시선값이 기존처럼 항상 `0~1`이어야 한다고 가정하지 않는다. 눈꺼풀 경계 밖이라는 이유 하나만으로 모든 홍채값을 오류로 처리하지도 않는다.

### 5.2 단계별 품질 검사

좌우 눈 각각의 좌표 유한성, 눈 가로폭, 눈꺼풀 기하, 급격한 이상치, 양안 일치도를 확인한다. 실제로 관측하지 못한 수치는 `None` 등 명시적인 누락으로 전달하고 정상값 0으로 대체하지 않는다.

얼굴·눈꺼풀·홍채의 유효성을 구분한다. 홍채가 유효하지 않아도 신뢰할 수 있는 눈꺼풀 관측으로 눈 감김을 판단할 수 있어야 한다. 반대로 눈꺼풀까지 불안정하면 눈 감김으로 단정하지 않는다.

검증되지 않은 단안 fallback은 이번 기본 판정에 넣지 않는다. 품질 점수는 모델 정확도나 실제 집중 확률로 표시하지 않는다.

### 5.3 함께 변경할 기준

좌표 계산, 프로필 기준값, 양안 불일치 임계값, 수직 시선 임계값, 눈 열림 기준은 하나의 검증 묶음이다. 새 좌표만 넣고 나머지 기준을 그대로 둔 상태로 사용자에게 적용하지 않는다.

새 측정 방식과 기존 보정은 호환되지 않는다. 새 방식 적용 시 재설정하며, 새 보정 실패 때도 구 방식 프로필을 새 방식의 대체값으로 사용하지 않는다. 같은 방식·환경에서의 실패·취소는 기존 프로필을 계속 보존한다.

## 6. 3차 검증: 머리 자세와 결합 판정

이 단계는 개선 후보 비교다. `solvePnP` 전면 채택이나 상관관계 모델 도입을 이미 확정한 것으로 해석하지 않는다.

### 6.1 머리 자세 후보

- 기존 OpenCV에서 일관된 회전행렬을 얻고 기준 회전 대비 상대회전을 계산한다.
- 좌표계, 회전 순서, 부호, 정면에서의 큰 회전값, 뒤집힌 해, 각도 경계의 연속성을 검증한다.
- 재투영 오차는 얼굴 크기에 상대적으로 평가한다. 낮은 재투영 오차만으로 실제 각도가 정확하다고 판정하지 않는다.
- 얼굴 이동·크기 변화는 회전과 분리한다. 영상 내 위치가 바뀌었다는 이유만으로 주의 이탈을 만들지 않는다.
- 원본 랜드마크 한 세트로 기존 계산과 후보 계산을 비교한다. 비교를 위해 얼굴 검출기를 두 번 돌리지 않는다.

합성 투영 검사와 실제 사용 검사를 구분한다. 합성 검사는 좌표·부호·연속성 오류를 찾지만, 실제 얼굴 형태와 카메라 오차까지 보증하지 않는다. 개선 근거가 없으면 기존 경로를 무조건 교체하지 않는다.

### 6.2 작업 영역 결합 후보

머리 각도가 기준을 넘었다는 이유만으로 먼저 탈락시키는 방식의 대안을 검증한다. 좌우 눈 방향과 상대 머리 회전을 함께 비교하되, 얼굴 위치·크기는 측정 가능한 환경의 범위를 판단하는 데 사용한다.

- 화면과 필기 영역을 모두 평가한 후 주의 상태를 결정한다.
- 유효하게 확인된 영역이 하나라도 있으면 그 영역의 판정을 사용한다. 영역 이름의 전환 유예가 집중 판정을 막지 않게 한다.
- 두 영역 모두 허용되면 영역 이름은 직전 값을 유지할 수 있다. 어느 쪽에도 가깝지 않은데 단지 더 가까운 하나를 골랐다고 집중으로 처리하지 않는다.
- 관측 품질이 충분하고 허용 영역 밖이라는 근거가 지속될 때만 이탈로 확정한다. 미학습 자세나 영역 구분 불확실성은 측정 불가로 분리한다.

상관관계를 반영한 정규화 거리 등은 후보일 뿐이다. 5개 표적의 비슷한 연속 프레임이 많다는 이유로 충분한 학습 자료라고 판단하지 않는다. 분포 중첩·표본 부족·과적합이 확인되면 허용 범위를 넓혀 숨기지 않는다.

검증 표본은 보정 때 바로 옆 프레임을 임의로 나누는 방식이 아니라 별도 동작에서 얻는다. 작업 중 비집중 오판, 실제 이탈을 집중으로 보는 오판, 측정 불가 비율, 반응 지연을 함께 비교한다. 채택 기준의 수치는 실제 비교 전 별도로 합의한다.

## 7. 보정 절차와 필요한 UI

### 화면 영역

1. 선택한 모니터에 전체화면 보정 창을 연다. 카메라 미리보기 중앙을 기준으로 삼지 않는다.
2. 현재 단계 안내와 표적 위치를 표시한다. 표적의 실제 표시·위치 이동 완료를 확인한 뒤 수집 대기를 시작한다.
3. QML의 벽시계를 분석 시각과 섞지 않는다. 현재 보정·단계에 대한 표시 완료 신호를 받은 Python 브리지가 단조 시각을 기록한다. 취소한 보정의 늦은 신호는 무시한다.
4. 표적 표시 전 촬영된 프레임, 오래된 결과, 눈 감김·가림 표본은 기준 수집에서 제외한다.
5. 기본 5점 수집을 유지하되, 같은 지점을 보며 고개를 조금 움직이는 추가 단계는 자세 보상 검증에 필요한 경우에만 도입한다. 5점만으로 모든 자세를 지원한다고 표시하지 않는다.

### 필기 영역

- 실제 종이·책·태블릿을 보며 문장을 쓰는 동안 수집한다. 일정한 자세를 계속 유지하도록 요구하지 않는다.
- 자연스러운 자세 변화 전체를 이상치로 제거하지 않고, 유효하지 않은 추적값과 구분한다.
- 중간 알림음은 사용하지 않는다. 시작·완료·실패 피드백은 기존 사용자 설정을 존중한다.
- 눈이 계속 보이지 않으면 시선 기반 필기 보정 성공으로 처리하지 않는다. 카메라 조정 또는 화면 모드 선택을 안내하며, 임의로 모드를 바꾸지 않는다.

### 공통

- 단계 진행률은 수집 상태이고 판정 정확도가 아니다. 표본 수만으로 품질 100%를 표시하지 않는다.
- 관측이 오지 않아도 제한시간을 확인한다. 실패 원인과 재시도할 단계를 보여주고 무한 대기를 막는다.
- 실패한 부분만 재시도하되, 재시도 사이 카메라·화각이 바뀌었다면 서로 다른 환경의 표본을 섞지 않는다.
- 카메라 교체·크롭·선택 모니터 변경은 기준 호환성을 확인한다. 실제 카메라 이동과 몸 이동을 항상 자동 구별할 수 있다는 전제를 두지 않는다.
- 측정 탭은 설정 상태·진행·실패 원인·필요 행동을 담당한다. 학습 탭은 타이머·할 일·작은 현재 상태 중심을 유지한다.
- 동일한 지시를 상태창·알림·패널에 반복하지 않는다. 전체 디자인·버튼 애니메이션 개편은 기능 검증 뒤 별도 작업으로 남긴다.

## 8. 기록과 데이터 호환성

### 진단 기록

기존 `FocusDecision.raw_state`를 갑자기 원시 관측으로 바꾸면 이벤트·부재 처리 등 기존 소비자가 영향을 받을 수 있다. 실제 관측 상태와 안정화 후 상태를 명시적으로 구분하고, 관련 호출부와 CSV 테스트를 함께 변경한다.

기존 관측 CSV를 확장하는 방식으로 원시/확정 상태, 품질 실패 이유, 관측 지연, 선택 영역, 비교에 필요한 측정값만 기록한다. 옛 CSV에 없는 정보를 있다고 가정하지 않는다. 영상 저장이나 별도 로그 대시보드는 만들지 않는다.

### 공부시간 정책: 구현 전 결정 필요

- 카메라로 측정된 시간: `FOCUS + NON_FOCUS`.
- 시각적 주의로 분류된 시간: `FOCUS`. 실제 인지적 집중의 진실값은 아니다.
- 학습 세션 시간: 세션의 경과시간에서 확정 휴식을 제외한 시간이라는 정의가 가능하다. 이 경우 측정 불가도 포함될 수 있다.
- 집중률은 유효 측정 시간에 대한 비율이다. 분모가 0이면 비집중 0%가 아니라 측정값 없음으로 표시하는 안을 적용한다.

어느 값을 기존 `공부시간`으로 표시할지, 과거 기록에도 같은 산식을 적용할지 확정하기 전에는 현재 조회 산식을 유지한다. 학습·플래너·기록 화면에 서로 다른 의미를 같은 이름으로 표시하지 않는다. 표시 정책 변경과 저장된 원본의 재분류는 별개이며, 과거 원본 상태를 새 알고리즘으로 추정해 덮어쓰지 않는다.

## 9. 파일별 변경 범위

| 묶음 | 기존 파일 | 변경 책임 |
| --- | --- | --- |
| 상태·시간 | `core/focus_policy.py`, `core/metrics.py`, `ui_qml/measurement_bridge.py` | 오류 즉시 반영, 이탈 타이머, 신선도·역순·공백 처리 |
| 세션 경계 | `app/session_manager.py` | 종료·휴식·재개 연동이 필요한 부분만 수정 |
| 눈 측정 | `core/face_analyzer.py`, `core/quality_gate.py` | 좌표·눈 열림·부분 유효성 검사 |
| 기준 호환성 | `core/calibration.py`, `core/models.py` | 측정 단위, 프로필, 진단 상태의 최소 데이터 변경 |
| 후보 검증 | `core/attention_engine.py`, `core/temporal_filter.py` | 영역 판정, 시간 기반 필터, 재획득 처리 |
| 진단 저장 | `app/session_recorder.py` | 기존 CSV의 구분 가능한 관측·확정 상태 |
| 보정 UI | `ui_qml/measurement_bridge.py`, `ui_qml/qml/components/ScreenCalibrationWindow.qml`, `ui_qml/qml/pages/MeasurementPage.qml` | 표시 완료와 수집 동기화, 진행·실패·재시도 |
| 시간 표시 | `app/session_database.py`, `ui_qml/app_bridge.py`, 해당 QML | 정책 확정 후에만 집계·표시 의미 통일 |

위 경로는 `onf_v2/` 기준이다. 새 추상 계층이나 단일 구현용 인터페이스를 만들지 않는다. 목록에 있다는 이유로 모든 파일을 수정하지 말고, 실제 공통 호출 경로에 필요한 최소 변경만 한다.

## 10. 실행 순서와 통과 조건

V3 Stage A source update (2026-09-29): immediate error/quality states, continuous head/gaze-away entry timing, ordered time accumulation, and camera/analysis-gap propagation are implemented. Session start, break/resume, and end boundaries now account for elapsed time without fresh frames. The 2-second observation ceiling reuses the existing camera stale-frame cutoff as a provisional value; tune it from real capture and analysis latency. Focused synthetic and offscreen tests passed. Live camera behavior, EXE, and study-time display policy remain unverified.

### A. 확정 버그

- [x] 첫 오류가 즉시 측정 불가가 되는 회귀 테스트와 수정.
- [x] 이탈 원인이 교대해도 연속 이탈이 확정되는 회귀 테스트와 수정.
- [ ] 역순·중복 입력, 카메라 단절, 지연 결과, 종료 직전 공백 검사. Synthetic tests cover these paths; camera switching and live latency still need verification.
- [x] 수동 휴식·기존 자동 휴식·버킷 합계 회귀 검사 (synthetic tests).

주요 테스트: `test_focus_policy.py`, `test_metrics.py`, `test_qml_measurement_bridge.py`, `test_absence_policy.py`.

### B. 눈 측정

- [x] Synthetic size, translation, aspect-ratio, and eye-tilt checks.
- [x] Synthetic missing-iris/valid-lids, invalid-lids, and binocular-disagreement checks.
- [ ] Eye-width gaze units, calibration, and thresholds updated together; real-camera tuning still pending. Existing calibration profiles are in memory only, so restart requires a new baseline; failed same-run recalibration preserves the current profile.

주요 테스트: `test_face_analyzer.py`, `test_quality_gate.py`, `test_calibration.py`, `test_attention_engine.py`.

### C. 후보 채택 판단

- [x] Synthetic landmark projection compares existing head output with a relative-rotation candidate (`tests/test_head_pose_candidate.py`). A pure lateral camera-space translation changed legacy yaw by about 2.9 degrees while the candidate stayed at zero in this exact-model fixture. Translation, scale, axis signs, reprojection, and angle-wrap checks passed. This does not establish accuracy on a real face or camera.
- [ ] 몸만 이동, 고개를 움직이며 화면 보기, 눈만 이탈, 실제 필기, 가림 후 복귀를 짧게 확인.
- [ ] 오탐·미탐·측정 불가·지연을 함께 비교해 채택 또는 보류 결정.
- [x] Candidate remains test-only; default head pose and focus decisions are unchanged pending real-use evidence.

실제 사용 확인은 별도 단계다. 단위 테스트 통과를 카메라 정확도 검증 완료로 보고하지 않는다. 기존 숫자 로그를 활용하되 새 계산에 정보가 부족하면 같은 프레임에서 비교값만 수집한다. 녹화는 필수가 아니다.

### D. 보정·UI·저장 연결

- [x] 표적 표시 전 프레임 제외, 늦은 단계 신호 무시, 무관측 제한시간 확인 (합성 입력·오프스크린 QML 검증). 실제 카메라 검증은 미완료.
- [x] Same-camera profile preservation on cancel/failure/retry and independent screen/writing profiles verified with synthetic tests (2026-10-04). Camera selection clears incompatible acquisition and profiles; physical-camera verification remains pending.
- [ ] 진행·오류 안내 중복, 창 잘림, 미리보기 숨김 시 분석 유지 확인.
- [ ] CSV 새 필드와 기존 세션 저장 호환성 확인.

Screen acquisition feedback checkpoint (2026-10-04): direction-specific usable dwell, pause/reason, selective retry, rendered-frame acknowledgment, and compact-layout bounds verified. See `design-plans/calibration-feedback.md` for 72 focused checks and offscreen captures. Screen-coordinate mapping, independent gaze accuracy, native mixed-DPI/monitor switching, and live calibration success remain pending; existing focus decisions and EXE are unchanged.

Screen mapping diagnostic checkpoint (2026-10-04): shadow affine eye-to-screen candidate and optional fresh validation pass implemented. Actual rendered coordinates and monitor/capture compatibility are recorded; median/P90 diagonal errors, prediction spread, and valid processed-frame fraction are shown separately. 86 focused synthetic/offscreen tests passed in 17.850 seconds. No automatic accuracy acceptance or attention-policy adoption; live camera comparison, head/writing upgrades, native mixed-DPI switching, and EXE remain pending. See `design-plans/calibration-feedback.md`, stage 2 checkpoint.

변경한 경로 중심으로 테스트한다. 공통 데이터 계약을 변경한 경우에만 직접 영향을 받는 소비자 테스트까지 넓힌다. 전체 테스트·빌드·장시간 벤치마크를 관성적으로 반복하지 않는다.

## 11. 결정되지 않은 항목과 금지된 가정

1. **시간 정의:** 측정 불가를 기존 공부시간에 포함할지, 별도 세션 시간으로만 보여줄지. 과거 표시 변경 여부도 함께 결정한다.
2. **알고리즘 채택:** 새 3D 자세와 결합 판정의 성능은 아직 미검증이다. 방식과 임계값을 확정된 정확도 개선으로 표현하지 않는다.
3. **허용 범위:** 자연스러운 자세 변화 중 실제로 검증한 범위만 지원한다고 본다. 이를 넘어선 값에 자동 적응하지 않는다.
4. **검증 부담:** 추가 보정 단계와 실제 확인 항목은 최소화한다. 사용자에게 새 동작을 요구한다면 목적과 소요를 먼저 설명한다.

첫 작업 묶음은 A다. 그다음 B를 검증하고 C의 채택 여부를 판단한다. D는 필요한 기능 연결만 수행하며, 디자인 확대는 별도 승인 뒤 진행한다.

## 12. 검토 이력과 참고 자료

- [x] 기존 구현과 수정안의 충돌 검토.
- [x] 첫 처리 오류, 교대 이탈 원인, 역순 시각 입력을 독립적인 Python 검사로 재현.
- [x] 눈 감김 관측에서 일부 홍채가 없을 때 품질 게이트가 측정 불가를 반환하는 경로 확인.
- [ ] 위 회귀 검사를 저장소 테스트로 추가하고 수정 완료.
- [ ] 실제 카메라 정확도·보정 성공률·UI 동작 검증.
- [ ] EXE 검증. 이번 작업 범위에서는 수행하지 않음.

참고:

- [MediaPipe Iris 공식 문서](https://chuoling.github.io/mediapipe/solutions/iris.html): 홍채 추적은 응시 위치나 인지적 집중의 직접 판정이 아님.
- [OpenCV solvePnP 공식 문서](https://docs.opencv.org/4.13.0/d5/d1f/calib3d_solvePnP.html): 대응점·카메라 내부값·왜곡을 사용하는 자세 추정과 재투영 오차.
- `ATTENTION_AREA_IMPROVEMENT_PLAN.md`: 이전 방향 및 UI 설계 배경. 현재 구현 진단과 실행 순서는 이 문서를 우선.
- `NEXT_FIXES_AND_UI_DIRECTION.md`: 플래너·일반 UI 등 별도 보완 사항. 과거 테스트 통과 기록은 이번 변경의 검증 결과가 아님.
