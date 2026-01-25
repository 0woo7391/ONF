Webcam Focus Tracker – 웹캠 기반 집중도 측정 프로그램

이 프로젝트는 Python, OpenCV, MediaPipe, Pillow를 활용하여
웹캠 영상에서 얼굴 랜드마크를 추출하고, 사용자의 머리 방향·시선·눈 감김 여부 등을 바탕으로
집중 상태를 실시간으로 판정하고 시각화하는 프로그램입니다. 

main

교육·연구·개인 생산성 분석을 목적으로 설계되었으며,
세션 단위 집중 비율을 1분 단위 그래프로 표현하고, 세션 종료 시 대시보드 이미지를 자동으로 저장합니다. 

main

1. 프로젝트 개요

웹캠 영상에서 MediaPipe FaceMesh를 이용해 얼굴 랜드마크를 검출합니다. 

judge

사용자가 기준 자세를 등록(캘리브레이션)하면, 이후 프레임마다 기준 대비 yaw(좌우), pitch(상하), 동공 위치(iris)를 계산합니다. 

judge

특정 임계값을 기준으로 집중 상태/시선 이탈/측면/휴식/눈 감김 등을 분류합니다. 

config

1초 단위로 상태를 요약한 뒤, 60초(1분) 단위로 묶어 집중 비율 그래프를 생성합니다. 

main

세션 종료 시, 해당 세션의 집중도 그래프와 요약 정보를 담은 대시보드 이미지를 result/ 폴더에 PNG로 저장합니다. 

main

2. 주요 기능

실시간 집중 상태 판정

MediaPipe FaceMesh로 얼굴 특징점(랜드마크)을 추적하고,
코 위치·눈 위치·동공 위치를 기반으로 사용자의 시선 및 머리 방향을 분석합니다. 

judge

눈 감김 지속 시간을 감지해, 일정 시간 이상 눈을 감고 있으면 EYES_LOST 상태로 판정합니다. 

judge

모드(민감도) 설정

세 가지 모드 제공: WEAK(1), NORMAL(2), STRONG(3). 

config

각 모드에 따라 yaw/pitch 허용 범위와 시선(iris) 허용 범위가 다르게 설정되어,
집중 판정 민감도를 조정할 수 있습니다. 

config

세션 관리 및 자동 종료

세션 시작 전 5초 카운트다운 후 본격적인 RUNNING 상태에 진입합니다. 

config

얼굴이 일정 시간 이상 인식되지 않으면 자동으로 휴식(BREAK) 상태로 전환됩니다.

휴식 상태가 10분 이상 지속되면 세션이 자동 종료되며, 대시보드가 고정됩니다. 

config

 

main

대시보드 시각화

Pillow로 별도의 대시보드 이미지를 생성하여,
현재 상태, 경과 시간, 총 휴식 시간, 세션 결과(평균 집중 비율), 1분 단위 집중 그래프, 단축키 안내를 한 화면에서 제공합니다. 

main

결과 저장

세션이 종료되면 최종 대시보드 이미지를 result/focus_result_YYYYMMDD_HHMMSS.png 형태로 자동 저장합니다. 

main

추후 세션별 집중 경향을 이미지로 비교·분석할 수 있습니다.

CSV 로거 클래스 (확장용)

1분 단위로 집중 비율을 CSV로 저장하기 위한 FocusLogger 클래스가 포함되어 있으며,
타임스탬프, 모드, 초 단위 집중 비율 요약을 기록할 수 있도록 설계되어 있습니다. 

logger

3. 집중 상태 정의

config.py에서 집중 상태는 FocusState enum으로 정의됩니다. 

config

NOT_CALIBRATED (0) : 기준 자세(캘리브레이션)가 아직 설정되지 않은 상태

NO_FACE (1) : 얼굴이 화면에서 인식되지 않음

EYES_LOST (2) : 일정 시간 이상 눈을 감고 있는 상태

SIDE (3) : 머리를 좌우로 돌려 기준 yaw에서 크게 벗어난 상태

FOCUS (4) : 기준 자세와 시선 범위 안에 있는 집중 상태

NO_FOCUS (5) : 모니터에서 시선이 벗어난 상태(동공 위치가 기준 범위를 벗어남)

DOWN (6) : 머리를 아래로 숙인 상태(현재는 예비 상태로 남겨둔 값)

BREAK (7) : 휴식 상태(수동/자동 휴식 포함)

이 값들은 1초 요약, 1분 요약, 그래프 색상 결정에 사용됩니다. 

main

4. 모드(Mode) 및 민감도 설정

Mode는 다음과 같이 세 가지 단계로 정의됩니다. 

config

MODE_1 (WEAK) : 기준에 가장 관대함(집중 판정이 느슨함)

MODE_2 (NORMAL) : 기본 모드(일반적인 환경에 적합)

MODE_3 (STRONG) : 기준에 가장 엄격함(조금만 자세가 흐트러져도 NO_FOCUS/SIDE로 판단)

각 모드별 설정 예시: 

config

yaw_side_thresh : 좌우 머리 회전에 대한 허용 오차

pitch_thresh : 상하 머리 움직임에 대한 허용 오차

iris_center_range : 눈동자 위치 허용 범위 (0~1 비율로 표현)

실행 중 1, 2, 3 키로 모드를 변경하면 즉시 FocusJudge 설정에 반영됩니다. 

main

5. 세션 흐름

main.py에서는 세션을 다음과 같은 상태로 관리합니다. 

main

PREVIEW

웹캠과 대시보드를 미리 확인하는 대기 상태

C 키로 기준 자세(Origin)를 설정할 수 있습니다.

이 상태에서 S 키를 누르면 캘리브레이션을 거쳐 RUNNING으로 진입합니다.

CALIBRATING

세션 시작 전 5초 카운트다운 상태 

config

사용자에게 자세 고정을 유도하며, 카운트다운이 끝나면 RUNNING 상태가 시작됩니다.

RUNNING

실제 집중 상태 측정이 진행되는 구간입니다. 

main

1초 단위로 상태를 요약해 minute_buffer에 쌓고, 60초마다 1분 요약을 생성해 그래프용 데이터로 사용합니다.

NO_FACE가 일정 시간 이상 지속되면 자동으로 BREAK 상태로 간주합니다. 

config

SESSION_ENDED

사용자가 Q를 눌러 세션을 종료하거나, 휴식이 10분 이상 지속되어 자동 종료된 상태입니다. 

main

이 상태에서는 그래프와 요약 정보가 고정되며, 마지막 대시보드 이미지가 파일로 저장됩니다. 

main

6. UI 구성

프로그램은 OpenCV 창 두 개를 사용합니다. 

main

FOCUS CAM

실제 웹캠 영상이 표시되는 창입니다.

왼쪽 상단에 반투명 패널 형태로 다음 정보가 표시됩니다. 

main

FOCUS 상태 (FOCUS / BREAK / NO FACE / SIDE / DOWN / NOT CALIBRATED / EYES LOST)

현재 모드 (WEAK / NORMAL / STRONG)

ORIGIN 설정 여부 (READY / NOT SET)

캘리브레이션 중일 경우 카운트다운 텍스트

FOCUS DASHBOARD

Pillow로 그려진 대시보드를 OpenCV 이미지로 변환해 띄우는 창입니다. 

main

상단 좌측:

현재 상태(STATE), 모드(MODE), 세션 경과 시간, 총 휴식 시간, 마지막 에러 메시지 등을 표시합니다. 

main

상단 우측:

세션 종료 후, 전체 세션에 대한 평균 집중 비율(Avg focus ratio)을 가중 평균으로 계산하여 표시합니다. 

main

중앙:

1분 단위 집중도 그래프

x축: 경과 시간(분)

y축: 0~100% 집중 비율

가로 그리드와 축, 눈금 값 표시

분당 집중 비율에 따라 바 색상 구분:

낮은 집중: 빨강

보통: 주황

양호: 연초록

매우 좋음: 진한 초록

전체가 휴식에 해당하는 구간: 회색(BREAK 바) 

main

하단:

단축키(Shortcuts)를 2열 레이아웃으로 정리하여 표시합니다. 

main

7. 로그 및 결과 파일

세션 로그 (향후 확장용)

FocusLogger는 1분 단위 집중 요약을 CSV 파일로 기록하기 위한 클래스입니다. 

logger

기본 컬럼:

timestamp : 기록 시각

mode : 모드 값(1, 2, 3)

focus_ratio : 해당 구간 집중 비율 (0~1)

elapsed_sec : 세션 경과 시간(초)

대시보드 이미지

세션이 종료되면, 마지막으로 생성된 Pillow 대시보드 이미지를 PNG로 저장합니다. 

main

저장 경로 예:

result/focus_result_20260125_213045.png

8. 실행 환경

Python 3.9 이상 권장

필수 라이브러리(예시):

opencv-python

mediapipe

numpy

pillow

웹캠이 연결된 환경 (노트북 내장 카메라 또는 외장 웹캠)

9. 설치 방법

저장소 클론

git clone https://github.com/your-username/your-repository.git

cd your-repository

가상환경 생성 및 활성화 (선택 권장)

Windows:

python -m venv venv

venv\Scripts\activate

macOS / Linux:

python -m venv venv

source venv/bin/activate

의존성 설치

pip install -r requirements.txt

10. 실행 방법

가상환경(선택)을 활성화한 후, 다음 명령으로 프로그램을 실행합니다.

python main.py

프로그램이 실행되면:

FOCUS CAM 창: 웹캠 영상 + 상단 상태 패널

FOCUS DASHBOARD 창: 현재 세션 상태, 그래프, 단축키 정보

가 동시에 표시됩니다. 

main

11. 키보드 단축키

실행 중 사용 가능한 주요 단축키는 다음과 같습니다. 

main

C : 기준 자세(Origin) 캘리브레이션

현재 프레임의 얼굴 위치를 기준으로 yaw, pitch, iris 기준값을 저장합니다. 

judge

S : 세션 시작

PREVIEW 또는 SESSION_ENDED 상태에서, Origin이 설정된 경우 세션을 시작하고 5초 카운트다운 후 RUNNING으로 진입합니다.

R : 수동 휴식 토글

RUNNING 상태에서 수동으로 휴식 상태를 켜거나 끕니다.

Q : 세션 종료

RUNNING 상태에서 세션을 종료하고 SESSION_ENDED 상태로 전환합니다.

ESC :

PREVIEW / SESSION_ENDED 상태에서 프로그램 종료

RUNNING 상태에서는 바로 종료되지 않고, 먼저 Q로 세션을 종료해야 합니다.

1 / 2 / 3 :

모드 변경 (WEAK / NORMAL / STRONG)

12. 제한 사항 및 주의 사항

본 프로그램의 집중 판정은 카메라 기반 휴리스틱(경험적 기준)에 의존하며,
실제 집중 여부를 100% 정확하게 판단할 수 없습니다.

조명, 카메라 위치, 해상도, 배경, 안경 착용 여부 등에 따라 인식 품질이 달라질 수 있습니다.

이 프로그램은 의료적·심리학적 진단 도구가 아니며,
학습/연구/자기 관리용 보조 도구로 사용하는 것을 권장합니다.
