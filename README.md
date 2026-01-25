# 🎯 Webcam Focus Tracker  
### 웹캠 기반 실시간 집중도 측정 프로그램

Python, OpenCV, MediaPipe를 활용하여  
웹캠 영상에서 얼굴 랜드마크를 분석하고 사용자의 **집중 상태를 실시간으로 추정·시각화**하는 프로그램입니다.

본 프로젝트는 **교육·연구·개인 생산성 분석**을 목적으로 설계되었습니다.

---

## 📌 프로젝트 요약

| 항목 | 내용 |
|---|---|
| 목적 | 웹캠 기반 집중도 측정 및 시각화 |
| 입력 | 실시간 웹캠 영상 |
| 출력 | 집중 상태, 1분 단위 집중 그래프, 결과 이미지 |
| 핵심 기술 | Python, OpenCV, MediaPipe, Pillow |
| 판정 방식 | 얼굴 랜드마크 기반 휴리스틱 |
| 사용 대상 | 학습자, 연구자, 개인 생산성 관리 |

---

## 🧠 프로젝트 개요

MediaPipe FaceMesh로 얼굴 랜드마크를 실시간 추출하고,  
머리 방향(yaw, pitch), 시선 위치(iris), 눈 감김 여부를 종합 분석하여  
사용자의 **집중 상태를 휴리스틱 방식으로 판단**합니다.

> ⚠️ 본 프로젝트는 의료·심리 진단 도구가 아니며,  
> 컴퓨터 비전 기반 집중도 추정 로직의 실험·학습을 목적으로 합니다.

---

## ✨ 주요 기능

### 🔍 실시간 집중 상태 판정
- 얼굴 랜드마크 추적(FaceMesh)
- 기준 자세(Origin) 대비 머리 방향 분석
- 시선 이탈(iris 위치) 감지
- 눈 감김 지속 시간 감지

### ⚙️ 모드 기반 민감도 조절
- **WEAK / NORMAL / STRONG** 3단계
- 모드별 yaw·pitch·시선 허용 범위 차등 적용
- 실행 중 실시간 전환 가능

### 📊 대시보드 시각화
- Pillow 기반 독립 대시보드 UI
- 1분 단위 집중 비율 그래프
- 현재 상태, 세션 시간, 휴식 시간, 평균 집중도 표시
- 단축키 안내 포함

### 💾 결과 저장
- 세션 종료 시 대시보드 이미지 PNG 자동 저장
- 세션별 집중 패턴 비교 가능

---

## 🧩 집중 상태 정의

| 상태 | 설명 |
|---|---|
| NOT_CALIBRATED | 기준 자세 미설정 |
| NO_FACE | 얼굴 미인식 |
| EYES_LOST | 일정 시간 이상 눈 감김 |
| SIDE | 머리 좌우 회전 과다 |
| FOCUS | 기준 범위 내 집중 상태 |
| NO_FOCUS | 시선 이탈 |
| BREAK | 휴식 상태 |

---

## 🎛 모드(Mode) 설명

| 모드 | 설명 |
|---|---|
| WEAK | 가장 관대한 기준 |
| NORMAL | 기본(권장) |
| STRONG | 가장 엄격한 기준 |

모드에 따라 머리 회전 및 시선 허용 범위가 달라집니다.

---

## 🔄 세션 동작 흐름

1. **PREVIEW**
   - 웹캠/대시보드 미리보기
   - `C` 키로 기준 자세 설정

2. **CALIBRATING**
   - 5초 카운트다운
   - 자세 고정 유도

3. **RUNNING**
   - 실시간 집중 측정
   - 1초 요약 → 1분 집중 비율 계산
   - 얼굴 미인식 시 자동 휴식 처리

4. **SESSION_ENDED**
   - 세션 종료
   - 결과 고정 및 이미지 저장

---

## 🖥 사용자 인터페이스(UI)

### FOCUS CAM
- 웹캠 영상
- 현재 상태, 모드, 기준 설정 여부 표시

### FOCUS DASHBOARD
- Pillow 기반 대시보드
- 구성:
  - 현재 상태/모드
  - 세션 경과 시간
  - 총 휴식 시간
  - 평균 집중 비율
  - 1분 단위 집중 그래프
  - 단축키 안내

---

## ⌨️ 단축키

| 키 | 기능 |
|---|---|
| C | 기준 자세(Origin) 설정 |
| S | 세션 시작 |
| R | 휴식 토글 |
| Q | 세션 종료 |
| ESC | 프로그램 종료 |
| 1 / 2 / 3 | 모드 변경 |

---

## 🗂 프로젝트 구조
project/

├─ main.py # 프로그램 진입점

├─ judge.py # 집중 판정 로직

├─ logger.py # 로그 기록

├─ config.py # 상태/모드/임계값

├─ logs/ # 세션 로그

├─ results/ # 결과 이미지

├─ requirements.txt

├─ README.md

└─ LICENSE

---

⚠️ 제한 사항

휴리스틱 기반 추정으로 정확도 100% 보장 불가

조명/카메라 위치/안경 착용 여부에 따라 인식률 변화

의료·심리 진단 목적 사용 금지

---

🤖 AI 도구 사용 안내

본 프로젝트는 AI 도구의 도움을 받아 개발되었습니다.

AI는 구현을 보조하는 도구이며, 최종 설계·배포 책임은 프로젝트 작성자에게 있습니다.

---

## 🖥 실행 환경

- Python 3.9 이상
- 웹캠 필수
- Windows / macOS / Linux
- 주요 라이브러리:
  - opencv-python
  - mediapipe
  - numpy
  - pillow

---

## 📦 설치 방법

```bash
git clone https://github.com/your-username/your-repository.git
cd your-repository

python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows

pip install -r requirements.txt

