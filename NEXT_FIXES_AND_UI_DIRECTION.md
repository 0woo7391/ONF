# ONF Fixes and UI/UX Plan

> Documentation reconciliation (2026-11-16): Retained approved planner/record contracts and historical fix checkpoints. Current implementation and remaining gates are consolidated in the documentation map. [Documentation map](docs/README.md).

Updated: 2026-10-05. New planning notes use concise English; user-facing discussion stays Korean. Preserve historical implementation notes below. Fix behavior before visual polish; no build, commit, or EXE replacement in this scope.

## Current Checkpoint: Approved UI/Planner Fixes

- Reject nonblank invalid start/end times through both Add/Enter and saved-row editing; retain editable input instead of silently dropping it.
- Learning uses independent today data, not the selected planner date. Today-plan edit now really navigates to today's planner.
- All three timetables distinguish measured0% from missing data. Legacy break-only sessions no longer create false red study cells.
- Planner exposes all24 hours in configured study-day order.
- Today total combines persisted scored-study time and the active session, excluding break/unscored and respecting the configured day boundary. Saved/live handoff does not count the ended session twice. Boundary attribution uses available minute aggregates, not reconstructed per-second events.
- Verification: 24 focused QML/bridge/regression tests passed; offscreen pixel checks distinguish red0% from empty cells in all three timetables. Temporary DB only, no camera opened. Not native DPI/EXE/audio verification.
- Current-session timeline overlay, demo-data policy, recurring edit/delete scope, task switching attribution, and changing the state cycle remain separate unapproved work.

Full redesign proposal: [V3 UI Redesign: Clear Desk](design-plans/ui-v3-redesign.md). Layout, font/icon assets, animation, and visual tokens are proposed, not applied to product QML.

> 2026-09-29: 포커스·보정·추적·관측 공백 집계는 [FOCUS_TRACKING_REVIEWED_PLAN.md](FOCUS_TRACKING_REVIEWED_PLAN.md)의 검토와 단계별 설계를 우선한다. 이 문서의 플래너·일반 UI 항목은 별도 범위이며, 아래 테스트 결과는 당시 기록이다.

작성일: 2026-09-28  
범위: 현재 `refactor/v2-attention-engine` 소스 점검. 아래 P1 네 항목은 구현했고, UI 개편과 추가 기능은 보류한다.

기존 자세 추적 계획과 일반 UI 원칙은 [ATTENTION_AREA_IMPROVEMENT_PLAN.md](ATTENTION_AREA_IMPROVEMENT_PLAN.md)의 16~19장을 기준으로 한다. 이 문서는 현재 구현에서 확인한 보완점과 실제 적용 방향만 추가한다.

## 점검 기준

- 플래너 브리지/QML 관련 테스트: 13개 통과.
- 전체 테스트: 135개 통과, 종료 코드 0.
- 오프스크린 렌더에서 항목 아래 실적 줄 배치 확인. 한글 글꼴 대체가 발생해 실제 Windows 글꼴 가독성은 미검증.
- 현재 작업 트리에 기존 변경 및 미추적 파일이 있다. 이 계획 작업에서는 정리·되돌리기 하지 않았다.
- 오프스크린 캡처는 한글 폰트가 정상 표시되지 않아 실제 Windows 가독성 검증으로 인정하지 않는다.

## 우선 수정 후보

### P1: 보정 프로필 보존과 독립성 — 완료

`measurement_bridge.py`에서 화면 보정을 시작할 때 듀얼 모드의 필기 보정까지 초기화하는 경로가 있다. `CalibrationManager.start()`도 해당 프로필을 새 보정 성공 전에 비운다. 보정 실패나 취소 시 기존 기준까지 잃을 수 있다.

수정 방향:

- 화면·필기 프로필을 서로 독립적으로 유지한다.
- 새 프로필이 품질 검사를 통과해 확정될 때만 기존 프로필을 교체한다.
- 브리지 수준 테스트로 화면 재보정 후 필기 프로필이 그대로 남는지 확인한다.

관련 코드: `onf_v2/ui_qml/measurement_bridge.py`, `onf_v2/core/calibration.py`.

### P1: 계획 시간의 계산 기준 보존 — 완료

플래너는 시작·종료·예상 시간 중 두 값을 입력하면 나머지를 계산한다. 하지만 저장 후에는 세 값이 모두 남고, 처음 입력한 두 값 정보는 보존되지 않는다. 다시 열어 편집하면 QML이 입력 기준을 추정해 원래 의도와 다른 칸을 다시 계산할 수 있다.

수정 방향:

- 계산된 칸을 식별할 수 있는 최소 정보만 저장한다.
- 기존 일정은 명확한 기본 규칙으로 불러오고, 새 입력·편집은 계산 결과와 저장 결과가 일치하는지 테스트한다.
- 시작과 종료가 같은 경우 현재처럼 24시간으로 볼지, 잘못된 입력으로 막을지 정책을 정한다.

관련 코드: `onf_v2/ui_qml/qml/pages/PlannerPage.qml`, `onf_v2/ui_qml/app_bridge.py`의 `_resolve_planner_edit()`.

### P1: 선택한 할 일 식별 — 완료

세션 시작 때 제목 문자열로 플래너 항목을 다시 찾는다. 제목이 같은 일정이 여러 개면 다른 항목에 세션이 연결될 수 있다.

수정 방향: 선택한 `taskId`를 상태로 보관하고 세션에 직접 전달한다. 중복 제목 두 개를 둔 회귀 테스트를 추가한다.

관련 코드: `onf_v2/ui_qml/qml/Main.qml`의 `startStudySession()`.

### P1: 학습일 경계 일관성 — 완료

설정에는 학습일 시작 시각이 있지만 현재 QML 기록 집계는 자정 기준 날짜 비교를 사용한다. 새벽 학습이 설정한 학습일과 다르게 일간·주간 기록에 들어갈 수 있다. 구형 QWidget 화면의 기존 테스트만으로 현재 QML 동작을 보증할 수 없다.

수정 방향: 설정된 경계를 공통 날짜 계산에 적용하고, 자정 전후 및 주 경계 사례를 QML 브리지 테스트로 확인한다.

관련 코드: `onf_v2/ui_qml/app_bridge.py`, `onf_v2/app/settings_store.py`.

### P2: 예시 데이터의 날짜·삭제 동작

빈 DB에서 예시 계획이 보이고, 예시 목록은 선택한 날짜마다 공유된다. 마지막 실제 기록을 지운 뒤 DB가 다시 초기 상태로 판단되면 예시가 다시 나타날 수도 있다.

수정 방향: 예시 데이터를 날짜별로 일관되게 만들고 실제 데이터 삭제 후 재등장하지 않게 한다. 예시를 빈 DB에 자동 표시할지, 명시적 미리보기로 둘지는 구현 전에 결정한다.

관련 코드: `onf_v2/ui_qml/app_bridge.py`의 `refresh()`와 `_load_planner_tasks()`.

### P2: 자세 판정은 로그 기반으로 조정

양쪽 눈 시선·평활화·화면/필기 프로필은 이미 구현돼 있다. 그러나 yaw는 랜드마크 비율 기반 추정이고, 자세 추정도 실제 카메라 내부 파라미터를 보정한 물리 각도로 볼 수 없다. 작업 영역 선택은 머리·시선·얼굴 크기 지표를 합산한다. 그러므로 허용 범위를 직감으로 넓히면 오탐이 줄기보다 집중 오판이 늘 수 있다.

수정 방향:

- 기존 관측 CSV에서 실제 이탈 구간의 시선, 자세, 선택 프로필, 최종 판정을 먼저 비교한다. 영상 녹화는 기본 요구로 두지 않는다.
- 보정은 눈 비율의 존재 여부뿐 아니라 눈이 열린 유효 기준인지 확인한다.
- 실제 로그 근거가 있는 임계값·전환 로직만 수정한다. 이 시스템은 인지적 집중이 아닌 화면/작업 영역에 대한 시각적 주의 추정으로 표현한다.

관련 코드: `onf_v2/core/face_analyzer.py`, `onf_v2/core/calibration.py`, `onf_v2/core/attention_engine.py`.

## UI/Planner Review: 2026-09-29

### Evidence and limits

- Inspected current QML and rendered five pages plus daily/weekly/monthly records at 1280x720; learning/planner/weekly records also at 1024x680.
- Isolated temporary DB, built-in demo data, offscreen software rendering, explicitly loaded Windows fonts. No real records or camera accessed. Native preview stalled and was stopped; packaged EXE, live interaction, DPI, and motion remain unverified.
- Temporary captures: `%TEMP%/onf-ui-audit-pages-5wbtlhcn/`. Regenerate if removed. Demo values are not evidence of measurement accuracy.
- Confirmed UI findings: planner timeline omits 00:00-05:59 (`DailyPlannerTimeline.qml`: `startHour=6`, `rows=18`); planner add/header/item columns do not align; learning shows multiple no-selection prompts and truncates the main prompt at minimum width.
- Source-confirmed behavior risks: `update_fixed_schedule_from_task()` changes other incomplete occurrences, including past dates; deleting one recurring task removes its recurrence rule. Displayed current task can change while `SessionManager.task_id` remains the start-time task.
- Old weekly left-clustered bars did not reproduce. Settings volume already uses dark fill/light empty track; preserve it. Do not report these as outstanding defects.

### Boundaries

- Task, planned time, and measured study are separate. Completion does not manufacture study time; moving a plan must not move historical measurements.
- Learning shows now/today; planner and daily records show the full selected study day; records browse all dates. Retain the learning timeline's current-hour emphasis and rolling window.
- Reuse QML, `Theme.qml`, `ActionButton.qml`, `ClockEntry.qml`, current bridges and DB. No framework migration, new home page, mandatory subject management, or unrelated refactor.
- Camera preview hiding must preserve layout and analysis. Keep full-monitor screen calibration, independent screen/writing profiles, and no intermediate writing-calibration beeps.

### Target interaction flows

- Add plan: title only + Enter. Start/end/duration stay visible, optional, initially blank. Tab/Shift+Tab traverse fields; Enter from any add-row field adds, while Enter in an existing row commits edits.
- Keep split hour/minute entry. Two explicit time values derive the third; show the derived value muted until confirmed by Enter/focus change. Preserve calculation provenance when reopening. Invalid input stays editable.
- Proposed clear action: small icon, normal hit area, clear all three time fields but retain title. No separate edit screen.
- Start study: one primary action when ready; task selection optional, unassigned time remains in overall totals. Keep last mode/settings. If calibration is missing, show the required action in context and return to learning after setup.
- Proposed task controls: body selects, checkbox toggles complete/incomplete, separate control defers. Current three-state cycle remains until this change is approved.
- Proposed task switch: explicit selection during study changes attribution from that instant without resetting the overall timer. Scheduled transitions only suggest the next task; never silently rewrite attribution. Policy and interval accounting require approval first.
- Main control stays in a stable slot for start/break/resume; end remains separate. End keeps the last elapsed time and compact saved result on the same page; next start resets to zero.
- Prefer local feedback over repeated toasts. Keep one message for each distinct empty state: no plans, none selected, all complete, deferred-only. Hide selection-method labels when nothing is selected.
- Ordinary deletion should offer undo; recurring edits/deletes require occurrence scope. Overlaps warn without blocking or auto-moving plans. Neither behavior is implemented by this document.

### Page changes

| Page | Proposed change | Preserve |
| --- | --- | --- |
| Learning | Reduce oversized empty-state banner; consolidate session/camera notices; improve task/timeline label size and balance. | Today tasks, current task, timer, optional camera, rolling timeline; stable controls and preview footprint. |
| Planner | Align add/header/item columns; readable actual-time subline; contain long timeline titles; render all 24 hours from configured study-day start. | Inline start/end/duration editing; untimed tasks; planned vs actual distinction. |
| Measurement | Prioritize connection, screen/writing calibration, progress, and actionable failure; compact duplicate study statistics. | Large useful camera preview; required calibration controls and retry/cancel. |
| Records | Bring daily totals closer to donut; enlarge chart labels/legends; rebalance monthly cell proportions and summary spacing. | Daily full-day timeline; combined weekly chart + daily totals; monthly calendar; period navigation. |
| Settings | Match dropdowns, inputs, switches, and buttons; group camera/measurement, timer, alerts/sound, and record-day settings. | Scrolling, visible save feedback, persistent settings, correct volume fill direction. |

### Visual direction: light study desk

- Proposed palette: background `#F6F7F9`, surface `#FFFFFF`, text `#191F28`, secondary `#6B7684`, divider `#E3E8EF`; action/selection `#2563EB` with `#EAF2FF`; success text `#15803D`, warning `#F59E0B`, danger `#F04452`.
- Focus charts retain red/yellow/green; break gray, unscored distinct. Planned outlines dotted, completed outlines solid. Do not rely on color alone.
- Proposed type: body 14-15px, secondary 12-13px, headings 20-24px; D-day label/title both 17px, same color and vertical alignment. Fixed timer dimensions, no viewport-scaled fonts.
- Use spacing, rows, and separators instead of large nested cards. Radius 6-8px; shadows only for floating UI. No decorative imagery, glass blur, extra themes, or gradient backgrounds.
- Hover/press feedback about 80-110ms; tab/content transitions 150-190ms; current-hour emphasis transition about 190ms. Animate ring progress, not timer digits; no periodic bounce/pulse or full-chart replay on every update.
- State changes apply immediately; motion is interruptible and optional decoration, never a processing delay. Preserve keyboard focus and loading/success/error feedback. Live-camera smoothness requires separate measurement.

### Feature candidates: pending approval

- Move selected unfinished tasks to today/another date; no automatic daily pile-up. Preserve original measurement dates.
- Extend the existing pin with weekday recurrence, one-day exceptions, and this-occurrence/future scope; keep past records unchanged.
- Daily/weekly planner views inside the same tab; weekly planning remains distinct from weekly results. Untimed work stays a list, not an invented time block.
- Nonblocking overlap hints, delete undo, and simple ordering of untimed tasks. Do not add priority taxonomies, AI scheduling, Kanban, badges, or rankings now.
- Optional weekly app totals and partial-session recovery remain separate candidates below, not part of visual polish.

## 추가 기능 후보 점검

### A: 계획별 실제 학습시간 표시 — 완료

DB는 할 일에 연결된 세션의 `actual_study_seconds`와 `actual_focus_seconds`를 이미 계산한다. 하지만 `AppBridge._load_planner_tasks()`가 두 값을 QML로 전달하지 않아 플래너에서 계획별 실제 시간을 볼 수 없다. 즉 새 추적 엔진보다 저장된 데이터를 유저에게 보여주는 보완이다.

표시: 각 할 일 제목 아래 `실제 42분 · 집중 36분` 형식으로 표시한다. 예상시간은 기존 `예상` 입력 칸에 그대로 둔다. 시간이 비어 있으면 예상 비교를 만들지 않는다. 세션을 특정 할 일과 연결하지 않고 시작한 경우 그 시간은 할 일별 수치에 넣지 않는다.

구현: DB의 기존 `actual_study_seconds`와 `actual_focus_seconds` 집계를 브리지로 전달한다. 세션 종료 후 기존 `recordsChanged` 갱신 신호가 플래너 값을 새로 읽는다. DB 스키마나 추적 로직은 바꾸지 않았다.

검증: 연결된 세션 복수 합산, 미연결 세션 제외, 휴식 제외, 예상 미지정, 브리지 재조회와 QML 로드를 테스트했다.

### B: 주간 프로그램 사용시간 — 선택적 추가

전경 프로그램 사용 기록은 세션별 DB에 저장된다. 현재 기록 화면은 선택 날짜의 상위 4개 앱만 보여주며, 주간 합계는 노출하지 않는다. 추적은 약 1초 간격의 실행 파일명 기준이라 브라우저 안의 사이트·탭이나 실제 집중 여부는 알 수 없다.

권장: 필요성이 확인되면 주간 기록에 프로그램별 총 사용시간을 보조 지표로 추가한다. 집중도 점수나 생산성 판정으로 해석하지 않는다. 웹사이트·창 제목 감시는 범위와 개인정보 부담이 커서 현재는 추가하지 않는다.

검증: 주간 기간 이동, 프로그램별 합계, 빈 주간 데이터 표시를 확인한다.

### C: 강제 종료 후 부분 세션 복구 — 유용하지만 후순위

일반 창 종료는 `shutdown()`에서 `endSession()`을 호출해 요약·이벤트·이미지·DB를 저장한다. 반면 강제 종료나 전원 종료는 마무리 저장에 도달하지 않는다. 관측 CSV는 15행마다 flush되지만 DB 세션 요약은 종료 시에만 기록된다. 따라서 강제 종료 시 CSV 일부만 남고 기록 탭에는 세션이 없을 수 있다.

권장: 도입한다면 다음 실행 때 미완료 세션을 감지해 `부분 기록으로 복구` 또는 `무시`를 선택하게 한다. 복구 기록은 완료 세션과 구분하고, 저장되지 않은 앱 사용시간·할 일 연결을 추정해서 채우지 않는다.

판단: 데이터 보호에는 유용하지만 시작 시 복구 흐름과 부분 기록 처리까지 필요하다. 우선순위 오류 수정 뒤에 실제 강제 종료 위험을 고려해 결정한다.

## 기능 우선순위 판정

- **먼저 보완:** 보정 프로필 보존, 계획 시간 재편집 일관성, 할 일 ID 연결, 학습일 경계.
- **완료:** DB에 있던 계획별 실제 학습시간을 플래너에서 표시.
- **조건부 추가:** 주간 프로그램 사용시간. 유저가 주간 비교를 실제로 활용할 때만 추가.
- **후순위:** 강제 종료 후 부분 세션 복구. 부분 기록의 표시·복구 정책까지 포함해 설계할 때 추가.
- **현재 제외:** 웹사이트·브라우저 탭 추적, AI 계획 생성, 배지·랭킹. 핵심 학습 흐름 대비 복잡도·개인정보·주의 분산 비용이 크다.

## Delivery and acceptance

Historical completion: independent calibration profiles, persisted derived time field, task-ID binding at session start, study-day aggregation, and per-task actual-time display. Reported 13 focused / 135 total tests passed on 2026-09-28; not rerun for this documentation update. This does not resolve the newly identified task-switch attribution risk.

Implementation order, after scope approval:

1. Correctness first: follow the separate focus/tracking plan; for planner/UI, restore 24-hour coverage, align input columns, and remove duplicate empty-state copy.
2. Resolve policy gates below before task-state, recurrence, or attribution changes. Reuse existing data; no silent migration of historical measurements.
3. Implement selected interaction improvements only, then static layouts using existing QML components.
4. Apply approved typography/colors and motion last. No new features hidden inside a styling change.

Focused checks:

- Timeline: 24 unique hours from the configured day start; midnight/cross-day plans and 00:00-05:59 actual data remain visible. Plan edits must not change recorded totals.
- Planner: add/edit Enter from title/hour/minute/duration; forward/backward Tab; blank/partial/invalid times; two-field derivation and reload; clear-time behavior after approval.
- State/records: selection is not completion; empty/completed/deferred-only states remain distinct. Approved task switching preserves total time and splits attribution without overlap. Recurrence exceptions cannot rewrite unrelated or historical occurrences.
- Visual: 1280x720 and 1024x680, real Korean fonts, long titles, empty/loading/error states; aligned columns, readable labels, no essential control clipping. Verify native Windows 125%/150% DPI separately.
- Motion: inspect with live analysis enabled; no delayed actions, timer drift, focus loss, or layout change when preview is hidden. Static captures prove none of these.
- Preservation: keep user data and existing EXE; targeted tests for touched paths first. No build or full-suite rerun for docs-only work.

## Decisions required before implementation

1. Checkbox: binary completion + separate defer control (recommended), or retain the existing three-state cycle?
2. Task attribution: explicit selection switches from that instant without an extra modal (recommended)? Scheduled changes only suggest the next task (recommended), or also switch actual attribution?
3. Clear input: clear all time fields and keep title (recommended)?
4. Equal start/end: retain current 24-hour meaning, or reject as ambiguous? Do not silently change it.
5. Demo data: explicit preview only (recommended), or automatic on an empty DB? Never confuse sample and real records.
6. Recurrence: approve weekday/exception support and this-occurrence/future edit scope. Unfinished-task carryover should be user-selected, not automatic.
7. Camera unavailable: keep calibration-required start, or permit timer-only study? Separate policy; unmeasured time must not be presented as measured focus.
8. Approve visual values and optional feature subset separately. Updating this MD does not approve product changes.

## 이번 구현 범위와 남은 한계

- 보정은 새 수집이 성공하기 전까지 기존 프로필을 유지한다. 보정 중에는 세션 시작을 막고, 취소·실패 시 기존 프로필을 사용할 수 있다.
- 플래너는 계산된 시간 칸을 DB에 보존한다. 새 컬럼은 nullable로 추가해 기존 DB 내용을 지우지 않는다. 시작·종료가 같은 입력의 의미는 기존 24시간 처리 규칙 그대로 두었으며, 별도 정책 결정은 하지 않았다.
- 기록은 학습일 경계에 맞춰 세션 시간을 구간 길이 비율로 나눈다. 세션별 총계만 있는 옛 데이터는 분할값이 근사치다. 앱 사용량과 최장 집중 구간은 저장 시각 세부 정보가 없어 학습일 경계 양쪽으로 정확히 나눌 수 없다.
- 선택된 할 일은 제목이 아니라 ID로 세션에 전달한다.
- 플래너 실적은 `_duration_text()` 기준 분 단위로 표시한다. 활성 세션은 DB 저장 전까지 반영되지 않고, 세션 종료 뒤 갱신된다.
- 예시 데이터 정책, 빈 상태 문구 정리, 부분 세션 복구, UI 디자인/애니메이션은 미처리다.

## Verified Study Stage: 2026-10-07

- The current clock/accounting contract supersedes older scored-only study notes: study = F + N + U + pending absence; break excluded. Focus ratio and coverage retain their separate denominators.
- Learning now has ready/study/break/result views for free study and Pomodoro, without a second session or timer. Start enters the study view; setup controls disappear during a session. Today's total is primary in free study; current-session and focus times remain separate.
- One break/resume action plus end; final session time remains visible until the next start. Preview hiding and tab/settings changes preserve active timing. Phase progress and same-timestamp manual break boundaries have regression coverage.
- Learning feedback uses its fixed status strip instead of covering controls. Both supported sizes were rendered and inspected with temporary DB/settings and a synthetic camera image. 38 scoped tests passed.
- Task attribution, recurring-task semantics, demo policy, calibration-required start, and classifier/calibration behavior are unchanged. The rolling chart is saved history, not a live-session overlay. Global styling/motion, other page redesigns, and actual camera/DPI/performance validation remain separate stages. No build/commit.
- Details and captures: [functional study view](design-plans/ui-v3-redesign.md#16-functional-study-view-2026-10-07).

## Verified Navigation and Shutdown Stage: 2026-10-08

- Scope: active-study navigation, repeated commands, break transitions, and normal application shutdown. No attribution policy, classifier, calibration, theme, schema, build, or commit changes.
- Duplicate start is rejected before engine/controller resets; the QML start handler also preserves an already active view. Native double-click handling was checked without adding a debounce delay.
- Pomodoro break commands settle an expired phase before acting. A click at the transition does not pause a zero-second phase or accidentally act on the new phase. Measurement and Learning use the same phase-aware action label.
- Actual navigation-button clicks cover all five tabs during rest in free study and Pomodoro. Ending from Measurement keeps that tab; returning to Learning shows the final time. The next start resets session time without deleting saved totals.
- Normal quit saves CSV, JSON, PNG, and one DB session in both modes, including rest. Running analysis closes its model only after completion; late setup/camera-open results release resources. Queued work is cancelled, and a queued tick cannot reopen devices after shutdown.
- Checks: 49 affected tests passed together, plus 2 focused camera-shutdown checks. A separate offscreen run used the real Qt event loop and main-window close event: study 20 seconds, break 30 seconds, one saved session. All used temporary data and mocked hardware; no actual camera or Windows DPI verification.
- Crash/power-loss recovery and failed-write recovery are not verified by these normal-quit checks. Long-running native camera/model calls still depend on their drivers returning; no forced worker termination was introduced.
- Next: resolve task-switch attribution before changing it, then connect the live-session timeline without double counting. Global visual redesign and packaged EXE checks remain separate stages.

## Approved Learning Records Contract: 2026-10-08

This replaces the earlier task-switch proposal. Plans are intentions, not evidence of actual study. Scheduled tasks are suggestions only and cannot replace an explicit selection or assign measured time.

- Live selection is optional. An explicit task change closes the old attribution interval without restarting the session. Completion closes the task interval, not the study session; selecting another task does not complete the previous one.
- Unassigned measured time remains in session/day totals. Break is excluded from task study time. Existing absence reclassification and stale-observation limits must also apply to task totals.
- Post-session allocation assigns already measured study time to user-chosen tasks without increasing session/day totals. Duration-only allocation has unknown task focus, never a proportional fabricated focus value.
- Separate manual study records cover study outside measurement. Date, title, and duration are explicit; focus is unknown. Records without actual clock times are not placed in hourly charts. Manual records and measured records remain distinguishable.
- Additive storage only: preserve legacy task/session links and original measurements. New sessions use explicit attribution records instead of assigning their whole duration to the initial task.
- Record edits/deletes must update totals once; validation failures retain the user's input. Do not alter planned start/end/estimate when recording actual study.
- Learning's timeline merges saved history with the active session once, while daily records retain the whole selected day. Task/plan data must not manufacture measured chart colors.
- Recurrence edit/delete scope, camera calibration, global typography/motion, EXE build, and commits remain separate.

Delivery checklist:

- [x] Contract and implementation scope approved by the user.
- [x] Storage and duration attribution, including backward-compatible reads.
- [x] Explicit live task changes/completion and scheduled suggestions.
- [x] Post-session allocations and separate manual record UI.
- [x] Daily/weekly/monthly/manual totals and live timeline handoff.
- [x] Focused regression checks, rendered UI, and original-data hashes.

Acceptance: A 10 minutes + B 5 minutes + break 5 minutes produces one session and 15 study minutes. Allocating 70 of 90 measured minutes leaves 20 unassigned and still totals 90. Adding 30 manual minutes creates 30 additional study minutes, no additional measured focus. Missing/invalid task IDs and over-allocation cannot corrupt saved totals. No camera or packaged-EXE claim from synthetic checks.

### Verified Implementation

- Additive `study_records` storage distinguishes tracked, allocated, and manual entries. A version marker preserves legacy whole-session task links; new sessions use explicit intervals. Measured entries remain immutable in the manual editor. Deleting a plan preserves record titles and durations; deleting a measured session removes only its dependent entries.
- Learning keeps explicit task selection. Scheduled tasks have a separate recommendation and selection action. Switching/completing/defering closes attribution without restarting study or completing another task. Unassigned time remains in session totals; rest and automatic absence reclassification also apply to task intervals.
- Records > Study records opens the editor. Pick a calendar date, optional plan, title, and actual duration. Measured-time allocation shows available capacity; separate study adds to learning totals. Edit replaces the existing entry; delete requires confirmation. Invalid inputs retain the form. Later allocations do not rewrite original measurement JSON/CSV files; the DB stores these annotations.
- Daily/weekly/monthly/today totals include manual study once and never add allocations again. Duration-only entries have no fabricated focus or hourly position. Wholly unscored tracked intervals also retain unknown focus. Missing measurement displays as unmeasured, not 0 percent. Monthly weekly-focus bars now use actual data instead of fixed figures.
- The rolling Learning chart reads a cached live projection from the existing accumulator, at most once per second during stable states. No second timer, accumulator, or per-frame DB write. Session end removes the live projection before refreshing saved history. Daily Records still show the selected 24-hour learning day.
- 75 scoped regression checks passed together. Final unknown-focus/layout/rollback changes were rechecked with 16 affected tests, all passed. Real Qt click tests cover save/edit/allocation/invalid input/delete, explicit task changes, scheduled recommendations, and live-to-saved handoff. Static captures inspected at 1280x720 and 1024x680 include Learning, all Records periods, the editor/date picker, manual-only days, and a six-row month. Numeric input clipping and a new delete-dialog binding loop were repaired. Captures: `design-plans/captures/study-records-2026-10-08/`.
- SHA-256 matches the pre-change baseline for `sessions/onf.sqlite3` and the original user settings. All tests use temporary storage and synthetic camera images. No actual camera, native DPI, packaged EXE, sustained performance, build, or commit validation in this stage.

Limits: duration-only manual records cannot be automatically checked for overlap with measured sessions. Users must choose allocation for time already measured, and separate study only for additional study. Task-record entries are currently grouped by their stored date, not split into exact per-task cross-day intervals; session/day totals retain the existing learning-day aggregation. Legacy linked sessions are not silently reallocated. Partial/crash recovery, recurrence scope, demo policy, classifier/calibration changes, and global design/motion remain separate approvals.

Next: review and approve the global visual redesign independently, then implement it without changing these accounting rules. Hardware calibration and EXE work remain separate.
