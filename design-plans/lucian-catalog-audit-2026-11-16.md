# Lucian catalog audit for native ONF QML

> Documentation reconciliation (2026-11-16): Reference audit, not an application feature list or implementation-completion claim. [Documentation map](../docs/README.md).
Date: 2026-11-16
Status: review only. No implementation approval implied.

## Evidence and Limits
- Gallery: https://lucianlabs.dev/uxui-prompt/
- Current Korean catalog: https://lucianlabs.dev/uxui-prompt/api/v1/ko/catalog.tsv
- Catalog header version: 26bbe93e4d. All 400 catalog entries across 27 categories were read and classified.
- 124 candidates/comparators: original source structure, input/event handling, motion and demo assumptions inspected.
- Those 124 original snippets were browser-rendered and their 11 contact sheets were visually inspected.
- Contact sheets: ./lucian-review-captures-2026-11-16/. Original snippets and shared tokens, SUIT font override, light mode, reduced motion, scaled to fit review tiles.
- These are third-party component references, NOT proposed ONF pages. Scaling/screenshots do not establish native QML DPI quality.
- Not all interactive states, keyboard paths, dark variants or native QML ports were tested. Initial rendering is not end-to-end behavior proof.
- No camera test, application launch, database change, EXE build, install, commit or application source change.
- Product sources inspected: LearningPage.qml, PlannerPage.qml, MeasurementPage.qml, RecordsPage.qml, SettingsPage.qml, StudyStyle.qml and components/StudyText.qml.
- Current SUIT Regular/Medium/SemiBold remain. Keep QML and Python engine; no WebView/React migration.

## Outcome
- R: 45 reference patterns for existing controls and views. These overlap; NOT 45 new widgets/features.
- O: 38 optional extensions, separately approved before implementation.
- T: 10 internal design/QA references; never user-facing tools by default.
- X: 307 excluded for scope, clutter, misleading semantics or unsuitable interaction.
- Primary page identity: Study / Measurement / Planner / Records / Settings. No new Home or marketing screen.

## Consolidated UI Families
| Family | References | Native QML proposal and non-negotiable boundary |
| --- | --- | --- |
| Main navigation | 048, 373 | Persistent selected underline, fixed hit targets; hover never replaces selected state. |
| Local mode/period selection | 039, 047 | General/Pomodoro and day/week/month use compact exclusive segments; no automatic switching. |
| Study controls | 007, 295 | Explicit start/preparation, pause/resume and end states; Pomodoro options shown only for that mode. |
| Pomodoro timer | 099 | One existing countdown ring, stable SUIT numerals; no extra 24-hour/activity rings. |
| Task status and recurrence | 012, 014 | Distinct blank/done/deferred icons; pin recurrence is not task selection or completion. |
| Inline task editing | 033, 131 | Preserve row identity, IME composition, cursor and Tab; no model-rebuild-induced focus loss. |
| Optional time fields | 133, 143, 244 | Independent hour/minute fields; last two explicit values derive third, gray suggestion then commit; optional blanks remain valid. |
| Delete feedback | 071 | Visible X plus undo; persistent data restoration must be real, not just a visual reappearance. |
| Select/switch/number/volume controls | 013, 017, 018, 023, 031, 192 | Consistent fixed-size controls; keyboard support; real audio test; do not erase disabled dependent values. |
| Date and calendar | 030 | Historical dates enabled, real month lengths and day boundaries; source booking constraints must not carry over. |
| Calibration presentation | 036, 042, 082, 083, 198, 284 | Waiting, accepting samples, unstable, completed and failed use actual backend signals; green means stable collection, not verified gaze direction. |
| Errors and tooltips | 072, 076, 077, 090, 092 | One actionable error at its source, bounded popup, Escape/focus return; no repeated toast piles. |
| Records and graphs | 095, 096, 097, 151, 238, 400 | Actual durations, stable calendar order, labelled units, pointer/focus readout; missing/unscored is not zero focus. |
| Details without dashboard clutter | 200, 273, 288 | Summary first, one explicit details panel, retained selected date; primary study controls never hidden. |
| Settings and saving | 250, 275, 355 | Section navigation, real dirty/saving/saved/error states; match existing explicit-save behavior, no pretend cloud. |
| Internal visual validation | 118, 119, 120, 121, 124, 257, 303, 316 | SUIT, contrast, spacing/radii, minimum window and DPI, restrained motion; no user-facing design editor. |

## Conflicts Found in the Reference Code
1. 030 disables dates before its sample TODAY. Incompatible with browsing all historic daily/weekly/monthly records.
2. 097 excludes selected categories and renormalizes the remaining donut. Must not silently alter focus/coverage denominators.
3. 008 suppresses Clipboard API errors while changing success UI. Never show success on failed copy/save.
4. 355 uses timeouts to report saved/synced; 284 uses scripted successful stages. Neither proves local database writes or camera/model readiness.
5. 192 and 194 are visual mixers/loops without actual audio playback. A moving meter cannot fix silent alert tests.
6. 173 resets a synthetic offset. It is not a gaze/head-pose calibration algorithm; no accuracy claim from its green state.
7. 131 rebuilds its input rows. 227 periodically inserts/sorts/discards sample rows. Both conflict with stable planner input/focus and complete history.
8. 026 has a single hidden OTP input; 362 requires a scrolling clock wheel. Neither implements the approved editable hour/minute cells.
9. 110 moves a schedule automatically. ONF plans are user plans, not inferred actual records; do not auto-switch attribution or move plans.
10. 095/096/098/151/400 include sample/generated values and date assumptions. Replace every datum with actual records, not just labels.
11. Several originals use fixed square/tall footprints and large corner radii/shadows. They are component demos, not whole desktop page layouts.
12. Several originals animate for 300-750ms or keep rendering continuously. Do not copy perpetual motion or delay real state transitions.

## Product Contracts to Preserve
- General study and Pomodoro both run focus checking; neither mode replaces the other.
- Main study figure is today's study total, with focus time secondary; session/break/result semantics remain owned by existing controller.
- Pause/break stops active study accumulation. End retains the final session time; a new session starts from zero.
- Task completion, current task, pin recurrence and planned schedule are separate states.
- Plans do not prove actual task duration. Reserved time recommends only; user selection/completion/next or later manual record controls attribution.
- Actual recorded intervals must not change when the user edits/deletes a planned task.
- Day records show the whole learning day; study timeline shows the current surrounding time window.
- Break is gray/empty, unscored is distinct, focus ratio colors use the approved red/yellow/green scale.
- Camera preview hiding preserves the allocated layout; no camera-centering requirement or fake face-boundary target.
- Separate gaze verification stays optional; collection stability must not claim verified direction.
- No decorative slogans, fabricated summaries, automatic celebration, forced tutorial or new feature without approval.

## Risks and Verification Before Future Implementation
- Use native Qt Quick controls/states/transitions; the HTML/CSS/DOM code is not drop-in QML.
- Reuse existing event/controller contracts; changing view must never start a session, re-run setup or reset selection.
- Preserve local-save acknowledgement and existing save/failure semantics; one feedback owner per operation.
- Test Tab/Shift+Tab/Enter/Escape, Korean IME, partial clocks, 24/60 correction, midnight, derived-field preview/commit, delete/undo.
- Test task-state/selection independence, pinned next-day state, scheduled recommendations and manual actual attribution.
- Test preparation/general/Pomodoro/break/end/new-session navigation without camera where possible; hardware acceptance separately.
- Test record day/week/month navigation, valid date ranges, missing data, exact totals, units and no denominator mutation.
- Check minimum window, 1280x720 and 1366x768 at 100/125/150% display scaling. All pages; captions/inputs/timers must remain legible.
- Press feedback immediate. Any short motion is presentation only, interruptible, disabled with reduced motion; no per-second flip/odometer.
- Ported source code requires preserving its MIT attribution. Conceptual native adaptations must not be presented as exact ports.

## Category Coverage
| Category | Entries |
| --- | ---: |
| buttons | 12 |
| toggles-pickers | 12 |
| inputs-search | 12 |
| menus-tabs | 12 |
| cards-content | 13 |
| sign-in-sign-up | 8 |
| alerts-feedback | 9 |
| loading-progress | 9 |
| empty-error-states | 6 |
| widgets-charts | 7 |
| layout-schedule-design | 25 |
| document-data-editing | 25 |
| analytics-data | 25 |
| workflow-systems | 25 |
| sections-content | 21 |
| data-motion | 18 |
| commerce-pricing | 18 |
| text-motion | 17 |
| social-proof | 7 |
| navigation | 16 |
| forms-input | 15 |
| hero-backgrounds | 18 |
| app-screens | 20 |
| scroll-motion | 17 |
| cursor-hover | 8 |
| site-builder-tools | 16 |
| promos-rewards | 9 |

## Full 400-Entry Decision Ledger
Evidence: C = catalog description reviewed; S = candidate source reviewed; V = initial light/reduced-motion browser rendering visually inspected. V is not a full interaction test.
R = recommended reference; O = optional extension requiring approval; T = internal QA only; X = exclude.
| ID | Original element | Decision | Evidence | Application / reason |
| --- | --- | --- | --- | --- |
| [001](https://lucianlabs.dev/uxui-prompt/#001) | Liquid Glass 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [002](https://lucianlabs.dev/uxui-prompt/#002) | 자석 화살표 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [003](https://lucianlabs.dev/uxui-prompt/#003) | 길게 눌러 삭제 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [004](https://lucianlabs.dev/uxui-prompt/#004) | 진행률 다운로드 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [005](https://lucianlabs.dev/uxui-prompt/#005) | 종이비행기 전송 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [006](https://lucianlabs.dev/uxui-prompt/#006) | 구독 리플 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [007](https://lucianlabs.dev/uxui-prompt/#007) | 재생 버튼 모핑 | R | C/S/V | Study controls: State-linked play/pause glyph; no waveform, fake progress or media seeking. |
| [008](https://lucianlabs.dev/uxui-prompt/#008) | 복사 버튼 체크 전환 | O | C/S/V | Existing copy actions only: Clipboard success must come from actual success; source suppresses copy failures. |
| [009](https://lucianlabs.dev/uxui-prompt/#009) | 글자 굴림 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [010](https://lucianlabs.dev/uxui-prompt/#010) | 분할 실행 버튼 | X | C/S/V | Compare only: Split execution hides mode selection; explicit general/Pomodoro preparation is clearer. |
| [011](https://lucianlabs.dev/uxui-prompt/#011) | 부채꼴 플로팅 버튼 | X | C | buttons: Decorative or domain-specific action; no additional study operation justified. |
| [012](https://lucianlabs.dev/uxui-prompt/#012) | 북마크 리본 | R | C/S/V | Planner recurrence pin: Visible pinned/unpinned state; discard burst and unrelated bookmark counts. |
| [013](https://lucianlabs.dev/uxui-prompt/#013) | 늘어나는 스위치 | R | C/S/V | Boolean settings: Clear track and thumb state, keyboard operation; restrained motion, no explanatory filler. |
| [014](https://lucianlabs.dev/uxui-prompt/#014) | 할 일 체크리스트 | R | C/S/V | Task status: Check drawing and completed styling; retain blank/completed/deferred and separate task selection. |
| [015](https://lucianlabs.dev/uxui-prompt/#015) | 요금제 라디오 카드 | X | C/S/V | Compare only: Large pricing-style radio cards add density; compact mode segments fit two study choices. |
| [016](https://lucianlabs.dev/uxui-prompt/#016) | 별점 평가 | X | C | toggles-pickers: Unneeded selection/reward/theme behavior; keep only established settings and task states. |
| [017](https://lucianlabs.dev/uxui-prompt/#017) | 기울어지는 값 말풍선 슬라이더 | R | C/S/V | Volume slider: Filled track plus immediate numeric readout; no tilting bubble, require real audio preview. |
| [018](https://lucianlabs.dev/uxui-prompt/#018) | 굴러가는 수량 스테퍼 | R | C/S/V | Pomodoro number fields: Direct numeric input plus optional stepper; retain limits, no digit-rolling timer. |
| [019](https://lucianlabs.dev/uxui-prompt/#019) | 관심사 칩 다중 선택 | O | C/S/V | Task/history filters: Only if useful with real volume; selected chips cannot replace all primary navigation. |
| [020](https://lucianlabs.dev/uxui-prompt/#020) | 제품 색상 고르기 | X | C | toggles-pickers: Unneeded selection/reward/theme behavior; keep only established settings and task states. |
| [021](https://lucianlabs.dev/uxui-prompt/#021) | 낮·밤 하늘 스위치 | X | C | toggles-pickers: Unneeded selection/reward/theme behavior; keep only established settings and task states. |
| [022](https://lucianlabs.dev/uxui-prompt/#022) | 좋아요 하트 터짐 | X | C | toggles-pickers: Unneeded selection/reward/theme behavior; keep only established settings and task states. |
| [023](https://lucianlabs.dev/uxui-prompt/#023) | 펼쳐지는 알림 설정 | R | C/S/V | Notification settings: Reveal relevant dependent controls; disabling must not erase stored settings. |
| [024](https://lucianlabs.dev/uxui-prompt/#024) | 가격 분포 범위 필터 | X | C | toggles-pickers: Unneeded selection/reward/theme behavior; keep only established settings and task states. |
| [025](https://lucianlabs.dev/uxui-prompt/#025) | 테두리로 떠오르는 라벨 입력 | X | C/S/V | Compare only: Moving labels reduce clock-field stability; keep fixed start/end/duration labels. |
| [026](https://lucianlabs.dev/uxui-prompt/#026) | 인증번호 6자리 입력 | X | C/S/V | Compare only: OTP uses one hidden input; cannot replace independently editable hour/minute fields. |
| [027](https://lucianlabs.dev/uxui-prompt/#027) | 펼쳐지는 상단 검색 | O | C/S/V | Planner/history search: New search needs approved scope; keep a stable search field, not moving the whole header. |
| [028](https://lucianlabs.dev/uxui-prompt/#028) | 늘어나는 댓글 입력창 | O | C/S/V | Task notes: Multiline notes are a new feature; bounded height and keyboard commit rules required. |
| [029](https://lucianlabs.dev/uxui-prompt/#029) | 색 태그 입력 | X | C | inputs-search: Domain-specific input or extra workflow not required by the current planner. |
| [030](https://lucianlabs.dev/uxui-prompt/#030) | 기간 선택 달력 | R | C/S/V | Calendar and date selection: Use actual calendar dates; source blocks past days, incompatible with history browsing. |
| [031](https://lucianlabs.dev/uxui-prompt/#031) | 맞춤 선택 목록 | R | C/S/V | Camera/sound selectors: Clear current selection, keyboard arrows, popup bounded by window; real device names. |
| [032](https://lucianlabs.dev/uxui-prompt/#032) | 끌어다 놓는 업로드 | X | C | inputs-search: Domain-specific input or extra workflow not required by the current planner. |
| [033](https://lucianlabs.dev/uxui-prompt/#033) | 제목 바로 고치기 | R | C/S/V | Inline task editing: Stable text position and Enter/Escape; retain current hour/minute Tab order. |
| [034](https://lucianlabs.dev/uxui-prompt/#034) | 공항 자동완성 | O | C/S/V | Recent task suggestions: Optional, never silently complete user text or consume Tab needed for time fields. |
| [035](https://lucianlabs.dev/uxui-prompt/#035) | 송금 금액 입력 | X | C/S/V | Compare only: Currency grouping and animated digits do not fit optional clock entry. |
| [036](https://lucianlabs.dev/uxui-prompt/#036) | 비밀번호 강도 미터 | R | C/S/V | Calibration collection conditions: Use available conditions only, not a made-up confidence percentage or proof of gaze direction. |
| [037](https://lucianlabs.dev/uxui-prompt/#037) | 계정 전환 메뉴 | X | C | menus-tabs: Extra navigation hierarchy, decoration or hidden workflow exceeds the five-page desktop app. |
| [038](https://lucianlabs.dev/uxui-prompt/#038) | 우클릭 컨텍스트 메뉴 | O | C/S/V | Task context menu: Secondary shortcut only; visible delete/pin controls must remain available. |
| [039](https://lucianlabs.dev/uxui-prompt/#039) | 미끄러지는 알약 탭 | R | C/S/V | Local mode segments: Persistent selected surface; no staggered list entrance during normal study. |
| [040](https://lucianlabs.dev/uxui-prompt/#040) | 펼쳐지는 사이드 레일 | X | C/S/V | Navigation alternative rejected: Five top-level pages do not justify an expanding sidebar that shifts the study surface. |
| [041](https://lucianlabs.dev/uxui-prompt/#041) | 홈 파인 하단 탭 바 | X | C | menus-tabs: Extra navigation hierarchy, decoration or hidden workflow exceeds the five-page desktop app. |
| [042](https://lucianlabs.dev/uxui-prompt/#042) | 단계 진행 마법사 | R | C/S/V | Calibration stages: Current/completed/pending stages from actual signals, retry failed stage without fake success. |
| [043](https://lucianlabs.dev/uxui-prompt/#043) | 늘어나는 페이지 번호 | O | C/S/V | Long history pagination: Only if actual volume needs it; date arrows must remain period navigation, not page numbering. |
| [044](https://lucianlabs.dev/uxui-prompt/#044) | 자주 묻는 질문 아코디언 | O | C/S/V | Advanced settings sections: Collapse secondary tuning only; keep essential camera and alert controls discoverable. |
| [045](https://lucianlabs.dev/uxui-prompt/#045) | 버튼에서 번지는 전체 메뉴 | X | C | menus-tabs: Extra navigation hierarchy, decoration or hidden workflow exceeds the five-page desktop app. |
| [046](https://lucianlabs.dev/uxui-prompt/#046) | 커맨드 팔레트 | X | C/S/V | Command palette rejected: Adds hidden commands and shortcut burden to a small five-page app. |
| [047](https://lucianlabs.dev/uxui-prompt/#047) | 기간 세그먼트 컨트롤 | R | C/S/V | Record period selector: Day/week/month state and clear dates; preserve actual totals, no count-up from zero. |
| [048](https://lucianlabs.dev/uxui-prompt/#048) | 스와이프와 이어진 밑줄 탭 | R | C/S/V | Primary page tabs: Stable navigation with persistent underline; no mandatory swipe navigation on desktop. |
| [049](https://lucianlabs.dev/uxui-prompt/#049) | 겹겹이 움직이는 에디토리얼 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [050](https://lucianlabs.dev/uxui-prompt/#050) | 빛을 따라 기우는 뉴스 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [051](https://lucianlabs.dev/uxui-prompt/#051) | 장바구니로 날아가는 상품 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [052](https://lucianlabs.dev/uxui-prompt/#052) | 돌려 보는 멤버십 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [053](https://lucianlabs.dev/uxui-prompt/#053) | 넘겨 고르는 카드 더미 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [054](https://lucianlabs.dev/uxui-prompt/#054) | 팔로우 프로필 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [055](https://lucianlabs.dev/uxui-prompt/#055) | 레코드가 꺼내지는 플레이어 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [056](https://lucianlabs.dev/uxui-prompt/#056) | 월·연 요금 전환 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [057](https://lucianlabs.dev/uxui-prompt/#057) | 얼굴로 넘기는 후기 캐러셀 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [058](https://lucianlabs.dev/uxui-prompt/#058) | 읽기 진행 기사 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [059](https://lucianlabs.dev/uxui-prompt/#059) | 참석 응답 이벤트 카드 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [060](https://lucianlabs.dev/uxui-prompt/#060) | 낮과 밤 비교 슬라이더 | X | C | cards-content: Media, commerce, social or editorial presentation does not serve the study workflow. |
| [061](https://lucianlabs.dev/uxui-prompt/#061) | 썸네일에서 열리는 라이트박스 | O | C/S/V | Camera enlargement: Explicit enlargement only; not forced during study or tied to hidden-preview state. |
| [062](https://lucianlabs.dev/uxui-prompt/#062) | 로그인 카드 피드백 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [063](https://lucianlabs.dev/uxui-prompt/#063) | 한 문장씩 묻는 가입 폼 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [064](https://lucianlabs.dev/uxui-prompt/#064) | 봉투로 보내는 로그인 링크 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [065](https://lucianlabs.dev/uxui-prompt/#065) | 번호 맞추는 기기 승인 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [066](https://lucianlabs.dev/uxui-prompt/#066) | 소셜 로그인 버튼 묶음 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [067](https://lucianlabs.dev/uxui-prompt/#067) | 잠금 해제 카운트다운 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [068](https://lucianlabs.dev/uxui-prompt/#068) | 끝까지 읽고 동의하는 약관 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [069](https://lucianlabs.dev/uxui-prompt/#069) | 아바타 자르기 편집기 | X | C | sign-in-sign-up: No account/signup/authorization workflow requested for this local study app. |
| [070](https://lucianlabs.dev/uxui-prompt/#070) | 겹쳐 쌓이는 토스트 | X | C/S/V | Stacked alerts rejected: Conflicts with duplicate-notification complaint; prefer one contextual message. |
| [071](https://lucianlabs.dev/uxui-prompt/#071) | 밀어서 지우고 되돌리는 스낵바 | R | C/S/V | Delete and undo feedback: Visible X and undo action; no swipe-only deletion or delayed database success. |
| [072](https://lucianlabs.dev/uxui-prompt/#072) | 접히는 인라인 알림 | R | C/S/V | Actionable status banner: Persistent errors with retry/details, one occurrence; ordinary success stays subtle. |
| [073](https://lucianlabs.dev/uxui-prompt/#073) | 굴러가는 공지 배너 | X | C | alerts-feedback: Messaging or rotating announcements add noise rather than actionable local feedback. |
| [074](https://lucianlabs.dev/uxui-prompt/#074) | 알림 벨과 드롭다운 | O | C/S/V | Notification history: Only if missed alerts matter; no bell badge or notification center by default. |
| [075](https://lucianlabs.dev/uxui-prompt/#075) | 업로드 진행 패널 | O | C/S/V | Per-direction collection detail: Use actual accepted samples; avoid duplicating progress in several places. |
| [076](https://lucianlabs.dev/uxui-prompt/#076) | 미끄러지며 따라오는 툴팁 | R | C/S/V | Icon tooltips: Delayed hover and keyboard focus, window-edge fitting; essential actions also need clear names. |
| [077](https://lucianlabs.dev/uxui-prompt/#077) | 반응 고르는 팝오버 | R | C/S/V | Anchored small popup: Use native Popup positioning/Escape/focus restoration; no emoji-reaction feature. |
| [078](https://lucianlabs.dev/uxui-prompt/#078) | 밀어서 답장하는 채팅 | X | C | alerts-feedback: Messaging or rotating announcements add noise rather than actionable local feedback. |
| [079](https://lucianlabs.dev/uxui-prompt/#079) | 뼈대에서 피어나는 게시물 | O | C/S/V | Slow record loading placeholder: Only for genuine delay; do not mask empty data as loading. |
| [080](https://lucianlabs.dev/uxui-prompt/#080) | 궤도가 모이는 동기화 스피너 | X | C/S/V | Orbit spinner rejected: Continuous decorative motion gives no useful study or calibration information. |
| [081](https://lucianlabs.dev/uxui-prompt/#081) | 결제 링이 그려진 뒤 체크 | X | C | loading-progress: Decorative or simulated progress is not appropriate evidence of actual work. |
| [082](https://lucianlabs.dev/uxui-prompt/#082) | 아이콘을 채우는 설치 진행 | R | C/S/V | Calibration button progress: A single real progress indicator in the relevant setup control, no pretend installation flow. |
| [083](https://lucianlabs.dev/uxui-prompt/#083) | 대기에서 진행으로 바뀌는 막대 | R | C/S/V | Unknown versus measurable progress: Waiting is indeterminate; accepted-sample collection is determinate; no fixed fake countdown. |
| [084](https://lucianlabs.dev/uxui-prompt/#084) | 목소리에 춤추는 점 로더 | X | C | loading-progress: Decorative or simulated progress is not appropriate evidence of actual work. |
| [085](https://lucianlabs.dev/uxui-prompt/#085) | 당겨서 새로고침 | X | C | loading-progress: Decorative or simulated progress is not appropriate evidence of actual work. |
| [086](https://lucianlabs.dev/uxui-prompt/#086) | 흘러나오는 AI 답변 | X | C | loading-progress: Decorative or simulated progress is not appropriate evidence of actual work. |
| [087](https://lucianlabs.dev/uxui-prompt/#087) | 트럭이 달리는 배송 단계 | X | C | loading-progress: Decorative or simulated progress is not appropriate evidence of actual work. |
| [088](https://lucianlabs.dev/uxui-prompt/#088) | 종이를 삼키는 빈 폴더 | X | C/S/V | Animated empty folder rejected: Use a short functional empty state and add action, not floating/eating artwork. |
| [089](https://lucianlabs.dev/uxui-prompt/#089) | 오타를 고쳐 주는 404 | X | C | empty-error-states: Nonfunctional illustration or unrelated recovery scenario; prefer direct actionable state. |
| [090](https://lucianlabs.dev/uxui-prompt/#090) | 플러그가 다시 꽂히는 오류 위젯 | R | C/S/V | Camera/record failure recovery: Error, retrying and recovered states from real outcomes; no scripted retries or false success. |
| [091](https://lucianlabs.dev/uxui-prompt/#091) | 오프라인에서 쌓였다 보내지는 메시지 | X | C/S/V | Cloud/offline queue rejected: Current local database does not need a fictional cloud-sync or online/offline messaging layer. |
| [092](https://lucianlabs.dev/uxui-prompt/#092) | 필터를 풀어 주는 빈 검색 결과 | R | C/S/V | Empty records versus filtered-out data: Distinguish no records, no matching records and load failure; offer only relevant recovery. |
| [093](https://lucianlabs.dev/uxui-prompt/#093) | 할 일을 다 끝내면 터지는 축하 | X | C/S/V | Completion celebration rejected: No confetti, modal celebration or time-based auto-completion; compact completion state is enough. |
| [094](https://lucianlabs.dev/uxui-prompt/#094) | 시간을 끌어 보는 날씨 하늘 | X | C | widgets-charts: Unrelated visualization; no supporting real study metric or necessary interaction. |
| [095](https://lucianlabs.dev/uxui-prompt/#095) | 모양이 바뀌는 막대 차트 | R | C/S/V | Study-duration bars: Stable chronological slots, visible axes/date labels, actual durations and correct empty days. |
| [096](https://lucianlabs.dev/uxui-prompt/#096) | 훑으면 색이 갈리는 주가 선 | R | C/S/V | Record line interaction: Date-linked cursor/readout; no financial red/green rules or fabricated interpolation across missing data. |
| [097](https://lucianlabs.dev/uxui-prompt/#097) | 항목을 빼면 다시 나뉘는 도넛 | R | C/S/V | Daily time proportions: Read-only category highlight; source renormalizes hidden segments, which would mislead focus/coverage. |
| [098](https://lucianlabs.dev/uxui-prompt/#098) | 자리마다 굴러가는 실시간 지표 | X | C/S/V | Odometer timer rejected: Per-second rolling distracts and harms stable reading; optional summary transitions are not timer motion. |
| [099](https://lucianlabs.dev/uxui-prompt/#099) | 한 바퀴를 넘기는 활동 링 | R | C/S/V | Pomodoro ring geometry: One meaningful countdown ring; no generic 24-hour dial or extra activity rings. |
| [100](https://lucianlabs.dev/uxui-prompt/#100) | 반으로 접히는 플립 타이머 | X | C/S/V | Flip timer rejected: Per-second card flips add distraction; retain SUIT and stable numerals. |
| [101](https://lucianlabs.dev/uxui-prompt/#101) | 분할 작업창 | O | C/S/V | Planner split resizing: Only with minimum pane widths; do not let hiding the camera resize the study layout. |
| [102](https://lucianlabs.dev/uxui-prompt/#102) | 중첩 파일 트리 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [103](https://lucianlabs.dev/uxui-prompt/#103) | 경로 탐색 크럼 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [104](https://lucianlabs.dev/uxui-prompt/#104) | 캔버스 미니맵 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [105](https://lucianlabs.dev/uxui-prompt/#105) | 스튜디오 평면도 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [106](https://lucianlabs.dev/uxui-prompt/#106) | 극장 좌석 배치 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [107](https://lucianlabs.dev/uxui-prompt/#107) | 환승 노선 선택 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [108](https://lucianlabs.dev/uxui-prompt/#108) | 시간대 회의 교집합 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [109](https://lucianlabs.dev/uxui-prompt/#109) | 주간 가능 시간 칠하기 | O | C/S/V | Painting planned time: New planning interaction only; never paint or rewrite measured study intervals by clicking. |
| [110](https://lucianlabs.dev/uxui-prompt/#110) | 일정 겹침 해소 | O | C/S/V | Schedule-overlap warning: Allow overlaps and warn only; no automatic schedule or recorded-task reassignment. |
| [111](https://lucianlabs.dev/uxui-prompt/#111) | 작업 기간 편집 | O | C/S/V | Dragging planned intervals: Requires approved snapping, midnight and undo rules; actual records stay read-only here. |
| [112](https://lucianlabs.dev/uxui-prompt/#112) | 리듬 스텝 시퀀서 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [113](https://lucianlabs.dev/uxui-prompt/#113) | 픽셀 아이콘 작업대 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [114](https://lucianlabs.dev/uxui-prompt/#114) | 벡터 패스 펜 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [115](https://lucianlabs.dev/uxui-prompt/#115) | 그라디언트 스톱 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [116](https://lucianlabs.dev/uxui-prompt/#116) | 베지어 이징 곡선 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [117](https://lucianlabs.dev/uxui-prompt/#117) | 간격 측정자 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [118](https://lucianlabs.dev/uxui-prompt/#118) | 타이포그래피 견본 | T | C/S/V | Typography QA: Validate existing SUIT weights and hierarchy; no new user-facing font-weight editor. |
| [119](https://lucianlabs.dev/uxui-prompt/#119) | 다층 그림자 | T | C/S/V | Shadow QA: Restrained depth for floating popups only; no giant shadows on every section. |
| [120](https://lucianlabs.dev/uxui-prompt/#120) | 연결된 모서리 반경 | T | C/S/V | Shape QA: Consistent 6-8px native control corners; no user-facing radius editor. |
| [121](https://lucianlabs.dev/uxui-prompt/#121) | 그리드 레이아웃 구성 | T | C/S/V | Responsive QA: Derive native layouts from window space; not a user-adjustable grid builder. |
| [122](https://lucianlabs.dev/uxui-prompt/#122) | 레이어 쌓임 순서 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [123](https://lucianlabs.dev/uxui-prompt/#123) | 색 혼합 모드 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [124](https://lucianlabs.dev/uxui-prompt/#124) | 색 대비 검사 | T | C/S/V | Contrast QA: Check real text/background contrast including disabled/read-only states and chart labels. |
| [125](https://lucianlabs.dev/uxui-prompt/#125) | 스냅 정렬 가이드 | X | C | layout-schedule-design: Specialized design/spatial tool with no current study operation; no new editor. |
| [126](https://lucianlabs.dev/uxui-prompt/#126) | 마크다운 쌍둥이 노트 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [127](https://lucianlabs.dev/uxui-prompt/#127) | 변경 덩어리 검토 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [128](https://lucianlabs.dev/uxui-prompt/#128) | 문서 찾기·바꾸기 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [129](https://lucianlabs.dev/uxui-prompt/#129) | 접히는 코드 가지 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [130](https://lucianlabs.dev/uxui-prompt/#130) | CSV 필드 연결 | O | C/S/V | CSV import mapping: New data-import scope, schema validation and backup needed; not a cosmetic addition. |
| [131](https://lucianlabs.dev/uxui-prompt/#131) | 동행자 입력 묶음 | T | C/S/V | Row identity and focus QA: Source rebuilds rows; do not copy that into QML where it can destroy Tab/cursor state. |
| [132](https://lucianlabs.dev/uxui-prompt/#132) | 조건 가지 만들기 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [133](https://lucianlabs.dev/uxui-prompt/#133) | 단위 왕복 변환 | R | C/S/V | Linked schedule fields: Last two explicit fields derive the third; gray preview then commit, avoid circular updates. |
| [134](https://lucianlabs.dev/uxui-prompt/#134) | 몫을 나누는 영수증 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [135](https://lucianlabs.dev/uxui-prompt/#135) | 비율로 늘리는 레시피 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [136](https://lucianlabs.dev/uxui-prompt/#136) | 봉투 주소 조판 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [137](https://lucianlabs.dev/uxui-prompt/#137) | 카드 번호 조판 연습 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [138](https://lucianlabs.dev/uxui-prompt/#138) | 문서 가림 편집 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [139](https://lucianlabs.dev/uxui-prompt/#139) | 여백 주석 연결 | O | C/S/V | Task notes/details: New notes storage needs approval; simple optional field rather than a document-comment system. |
| [140](https://lucianlabs.dev/uxui-prompt/#140) | 선택 문장 서식 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [141](https://lucianlabs.dev/uxui-prompt/#141) | 단축키 조합 기록 | O | C/S/V | Custom shortcuts: New settings and conflict handling; ordinary Tab/Enter/Space already must work. |
| [142](https://lucianlabs.dev/uxui-prompt/#142) | 번역 구절 짝짓기 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [143](https://lucianlabs.dev/uxui-prompt/#143) | 계산하는 셀 | R | C/S/V | Editable calculated values: Preserve optional blanks and derived values; do not hijack left/right used for text editing. |
| [144](https://lucianlabs.dev/uxui-prompt/#144) | 열 순서 편집 | X | C/S/V | Column-customization panel rejected: Start/end/duration must remain directly visible; hiding them weakens the approved planner workflow. |
| [145](https://lucianlabs.dev/uxui-prompt/#145) | 단어별 받아쓰기 수정 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [146](https://lucianlabs.dev/uxui-prompt/#146) | JSON 값 가지 편집 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [147](https://lucianlabs.dev/uxui-prompt/#147) | 정규식 일치 실험 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [148](https://lucianlabs.dev/uxui-prompt/#148) | 출처 서식 조판 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [149](https://lucianlabs.dev/uxui-prompt/#149) | 충돌 문장 병합 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [150](https://lucianlabs.dev/uxui-prompt/#150) | 줄을 정리하는 활자판 | X | C | document-data-editing: Document/code/collaboration tool would introduce a separate product workflow. |
| [151](https://lucianlabs.dev/uxui-prompt/#151) | 기여가 쌓이는 주간 격자 | R | C/S/V | Monthly study heatmap: Real dates/month lengths, minutes on hover/focus, empty versus unmeasured distinguished. |
| [152](https://lucianlabs.dev/uxui-prompt/#152) | 폴더 안으로 커지는 면적 지도 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [153](https://lucianlabs.dev/uxui-prompt/#153) | 유입에서 구매까지 흐르는 길 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [154](https://lucianlabs.dev/uxui-prompt/#154) | 역량을 포개는 다각형 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [155](https://lucianlabs.dev/uxui-prompt/#155) | 점으로 고르는 실험군 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [156](https://lucianlabs.dev/uxui-prompt/#156) | 이상치를 꺼내는 상자 수염 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [157](https://lucianlabs.dev/uxui-prompt/#157) | 서비스가 층을 이루는 사용량 | O | C/S/V | App-usage composition chart: Use recorded foreground duration only; never infer distraction or concurrent total time from app identity. |
| [158](https://lucianlabs.dev/uxui-prompt/#158) | 증감을 잇는 손익 다리 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [159](https://lucianlabs.dev/uxui-prompt/#159) | 하루 거래를 펼치는 봉 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [160](https://lucianlabs.dev/uxui-prompt/#160) | 이탈을 드러내는 전환 깔때기 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [161](https://lucianlabs.dev/uxui-prompt/#161) | 주차별로 남는 고객 격자 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [162](https://lucianlabs.dev/uxui-prompt/#162) | 관계를 정렬하는 상관 행렬 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [163](https://lucianlabs.dev/uxui-prompt/#163) | 기준을 넘어가는 실적 눈금 | O | C/S/V | Study-goal progress: Requires a user-entered goal; never turn planned task duration into an automatic daily target. |
| [164](https://lucianlabs.dev/uxui-prompt/#164) | 구간을 다시 묶는 분포 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [165](https://lucianlabs.dev/uxui-prompt/#165) | 예측의 폭을 넓히는 구름 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [166](https://lucianlabs.dev/uxui-prompt/#166) | 흐름에서 고르는 오류 기록 | O | C/S/V | Technical error details: Hidden diagnostic detail only, not the main daily/weekly record experience. |
| [167](https://lucianlabs.dev/uxui-prompt/#167) | 요청 속 시간을 분해하는 스팬 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [168](https://lucianlabs.dev/uxui-prompt/#168) | 응답 시간을 조각내는 요청 목록 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [169](https://lucianlabs.dev/uxui-prompt/#169) | 테이블을 잇는 관계 지도 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [170](https://lucianlabs.dev/uxui-prompt/#170) | 장애 구간을 확대하는 시간축 | O | C/S/V | Timeline detail zoom: Explicit detail drill-down; daily record default remains the full day, study remains the live window. |
| [171](https://lucianlabs.dev/uxui-prompt/#171) | 예산 안에서 나누는 자원 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [172](https://lucianlabs.dev/uxui-prompt/#172) | 가격 벽을 드러내는 호가 깊이 | X | C | analytics-data: Additional statistic or specialized chart is unsupported or unnecessarily complex for current study records. |
| [173](https://lucianlabs.dev/uxui-prompt/#173) | 방향을 보정하는 측정 나침반 | X | C/S/V | Calibration compass rejected: A scripted offset reset is not gaze calibration; no fake measured angle or camera-position claim. |
| [174](https://lucianlabs.dev/uxui-prompt/#174) | 방향별로 펼치는 분포 장미 | X | C/S/V | Wind-rose calibration rejected: Direction-count distribution is not directional accuracy or completion; use actual per-stage indicators. |
| [175](https://lucianlabs.dev/uxui-prompt/#175) | 척도를 맞추는 비교 레일 | X | C/S/V | Normalized comparison rejected: Minutes and percentages cannot be merged into an arbitrary shared performance score. |
| [176](https://lucianlabs.dev/uxui-prompt/#176) | 버전 필름스트립 | O | C/S/V | Revision restore: Requires real stored versions and restore rules; a display-only selector cannot promise recovery. |
| [177](https://lucianlabs.dev/uxui-prompt/#177) | 작업 히스토리 분기 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [178](https://lucianlabs.dev/uxui-prompt/#178) | 묶음 선택 작업대 | O | C/S/V | Bulk task actions: Only after selection, affected count and undo rules are approved; no clutter on normal rows. |
| [179](https://lucianlabs.dev/uxui-prompt/#179) | 클립보드 선반 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [180](https://lucianlabs.dev/uxui-prompt/#180) | 승인 서명선 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [181](https://lucianlabs.dev/uxui-prompt/#181) | 업무 배분 슈트 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [182](https://lucianlabs.dev/uxui-prompt/#182) | 대기열 호출기 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [183](https://lucianlabs.dev/uxui-prompt/#183) | 순위 투표 용지 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [184](https://lucianlabs.dev/uxui-prompt/#184) | 역할 권한 매트릭스 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [185](https://lucianlabs.dev/uxui-prompt/#185) | 키 교체 금고 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [186](https://lucianlabs.dev/uxui-prompt/#186) | 기기 페어링 레이더 | X | C/S/V | Device radar rejected: Webcam enumeration has no physical direction/radar data; animation would be misleading. |
| [187](https://lucianlabs.dev/uxui-prompt/#187) | 입장권 체크인 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [188](https://lucianlabs.dev/uxui-prompt/#188) | 카나리 롤아웃 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [189](https://lucianlabs.dev/uxui-prompt/#189) | 환경 승격 게이트 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [190](https://lucianlabs.dev/uxui-prompt/#190) | 예약 발송 보관함 | R | C/S/V | Optional schedule editing: Plan times remain user input, not an automatic switch of the current recorded task. |
| [191](https://lucianlabs.dev/uxui-prompt/#191) | 이벤트 재생 테이프 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [192](https://lucianlabs.dev/uxui-prompt/#192) | 3채널 오디오 믹서 | R | C/S/V | Volume feedback: One alert-volume control with actual sound; source is visual only and has no playback. |
| [193](https://lucianlabs.dev/uxui-prompt/#193) | 호흡 페이스메이커 | O | C/S/V | Guided break breathing: Separate optional feature, not necessary for study tracking and not enabled by default. |
| [194](https://lucianlabs.dev/uxui-prompt/#194) | 오디오 루프 구간 | X | C/S/V | Audio waveform editor rejected: No actual playback in source; ringtone choice and real preview suffice without a loop editor. |
| [195](https://lucianlabs.dev/uxui-prompt/#195) | 영상 챕터 레일 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [196](https://lucianlabs.dev/uxui-prompt/#196) | 공동 작업 제어권 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [197](https://lucianlabs.dev/uxui-prompt/#197) | 화면 안내 스포트라이트 | O | C/S/V | Optional first-use guide: User-triggered and skippable, not a mandatory tour; do not confuse it with calibration targets. |
| [198](https://lucianlabs.dev/uxui-prompt/#198) | 네트워크 경로 진단 | R | C/S/V | Device readiness breakdown: Use actual camera/model/tracking states; no invented network hops or scripted recovery. |
| [199](https://lucianlabs.dev/uxui-prompt/#199) | 무결성 체크섬 | X | C | workflow-systems: Unrelated multiuser, infrastructure, security or media workflow; not a study UI requirement. |
| [200](https://lucianlabs.dev/uxui-prompt/#200) | 접히는 정산 영수증 | R | C/S/V | Expandable record detail: Summary first, detail on request; no receipt decoration or hidden important errors. |
| [201](https://lucianlabs.dev/uxui-prompt/#201) | 한 단계씩 불이 켜지는 자동화 흐름도 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [202](https://lucianlabs.dev/uxui-prompt/#202) | 블록으로 솟는 아이소메트릭 데이터 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [203](https://lucianlabs.dev/uxui-prompt/#203) | 선이 이어지는 제품 주석 핀 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [204](https://lucianlabs.dev/uxui-prompt/#204) | 기준을 바꾸면 다시 모이는 버블 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [205](https://lucianlabs.dev/uxui-prompt/#205) | 글자마다 출렁이는 파도 로고 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [206](https://lucianlabs.dev/uxui-prompt/#206) | 끌면 출렁이는 관계망 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [207](https://lucianlabs.dev/uxui-prompt/#207) | 두 줄로 흐르는 후기 벽 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [208](https://lucianlabs.dev/uxui-prompt/#208) | 커서 따라 부푸는 앱 독 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [209](https://lucianlabs.dev/uxui-prompt/#209) | 국가에 맞춰 묶이는 전화번호 입력 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [210](https://lucianlabs.dev/uxui-prompt/#210) | 참석자가 늘어나는 웨비나 신청 카드 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [211](https://lucianlabs.dev/uxui-prompt/#211) | 테두리 빛이 도는 가입 유도 버튼 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [212](https://lucianlabs.dev/uxui-prompt/#212) | 내리면 숨고 올리면 돌아오는 헤더 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [213](https://lucianlabs.dev/uxui-prompt/#213) | 저절로 넘어가는 기능 소개 탭 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [214](https://lucianlabs.dev/uxui-prompt/#214) | 칸마다 살아나는 벤토 기능 소개 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [215](https://lucianlabs.dev/uxui-prompt/#215) | 말풍선에서 펼쳐지는 상담 채팅 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [216](https://lucianlabs.dev/uxui-prompt/#216) | 차례로 올라오는 첫 화면 히어로 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [217](https://lucianlabs.dev/uxui-prompt/#217) | 차이만 남기는 요금제 비교표 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [218](https://lucianlabs.dev/uxui-prompt/#218) | 스크롤하면 아래로 붙는 미니 플레이어 | O | C/S/V | Persistent study indicator: One shared session state outside study page; avoid a second independent timer or duplicate controls. |
| [219](https://lucianlabs.dev/uxui-prompt/#219) | 누른 자리에서 원으로 번지는 다크 모드 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [220](https://lucianlabs.dev/uxui-prompt/#220) | 고른 문장 위에 뜨는 인용 공유 툴팁 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [221](https://lucianlabs.dev/uxui-prompt/#221) | 따라붙는 구매 바와 옵션 시트 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [222](https://lucianlabs.dev/uxui-prompt/#222) | 별 기록이 그려지는 오픈소스 별 버튼 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [223](https://lucianlabs.dev/uxui-prompt/#223) | 쌓이며 작아지는 스티키 카드 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [224](https://lucianlabs.dev/uxui-prompt/#224) | 출처를 짚어 보여 주는 AI 답변 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [225](https://lucianlabs.dev/uxui-prompt/#225) | 한 입 베어 무는 쿠키 동의 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [226](https://lucianlabs.dev/uxui-prompt/#226) | 격자를 따라 빛이 흐르는 히어로 배경 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [227](https://lucianlabs.dev/uxui-prompt/#227) | 새 주문이 밀고 들어오는 실시간 표 | T | C/S/V | Live-list update QA: Never insert demo orders, auto-sort editing tasks or discard records after a display cap. |
| [228](https://lucianlabs.dev/uxui-prompt/#228) | 커서 빛이 번지는 카드 테두리 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [229](https://lucianlabs.dev/uxui-prompt/#229) | 저절로 입력되는 터미널 시연 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [230](https://lucianlabs.dev/uxui-prompt/#230) | 할인 코드를 넣으면 다시 계산되는 주문 요약 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [231](https://lucianlabs.dev/uxui-prompt/#231) | 스크롤하면 펴지는 기울어진 제품 화면 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [232](https://lucianlabs.dev/uxui-prompt/#232) | 지문 한 번으로 끝나는 패스키 로그인 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [233](https://lucianlabs.dev/uxui-prompt/#233) | 예시 문장이 바뀌는 AI 프롬프트 입력창 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [234](https://lucianlabs.dev/uxui-prompt/#234) | 하나씩 바뀌는 고객사 로고 벽 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [235](https://lucianlabs.dev/uxui-prompt/#235) | 긴 글을 세 줄로 접는 AI 요약 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [236](https://lucianlabs.dev/uxui-prompt/#236) | 본문 밑에서 드러나는 푸터 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [237](https://lucianlabs.dev/uxui-prompt/#237) | 줄마다 올라오는 마스크 제목 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [238](https://lucianlabs.dev/uxui-prompt/#238) | 막대로 보는 서비스 상태 페이지 | R | C/S/V | Thin focus-history bars: Fixed width, real ratio heights/colors; break gray/empty and unmeasured not zero focus. |
| [239](https://lucianlabs.dev/uxui-prompt/#239) | 보내 보는 API 예제 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [240](https://lucianlabs.dev/uxui-prompt/#240) | 무료배송까지 채워지는 장바구니 서랍 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [241](https://lucianlabs.dev/uxui-prompt/#241) | 세로로 굴리면 가로로 흐르는 섹션 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [242](https://lucianlabs.dev/uxui-prompt/#242) | 스크롤 따라 넘어가는 카테고리 칩 바 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [243](https://lucianlabs.dev/uxui-prompt/#243) | 눌러서 확인하는 보안 인증 배지 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [244](https://lucianlabs.dev/uxui-prompt/#244) | 틀린 칸으로 데려가는 폼 검증 | R | C/S/V | Inline input validation: Relevant field, clear bounds and recoverable edits; no shaking, clearing user input or premature focus theft. |
| [245](https://lucianlabs.dev/uxui-prompt/#245) | 해독되는 스크램블 헤드라인 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [246](https://lucianlabs.dev/uxui-prompt/#246) | 순위가 뒤바뀌는 막대 경주 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [247](https://lucianlabs.dev/uxui-prompt/#247) | 스크롤하면 화면을 채우는 소개 영상 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [248](https://lucianlabs.dev/uxui-prompt/#248) | 투표하면 순위가 올라가는 기능 요청판 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [249](https://lucianlabs.dev/uxui-prompt/#249) | 쓰는 대로 보이는 검색 결과 미리보기 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [250](https://lucianlabs.dev/uxui-prompt/#250) | 바꾸면 내려오는 저장 바 | R | C/S/V | Unsaved settings state: Current explicit-save workflow only; real backend result, cancel/dirty exit rules, no extra save layer. |
| [251](https://lucianlabs.dev/uxui-prompt/#251) | 스크롤하면 차례로 떠오르는 기능 카드 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [252](https://lucianlabs.dev/uxui-prompt/#252) | 반짝 지나가며 펼쳐지는 공지 알약 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [253](https://lucianlabs.dev/uxui-prompt/#253) | 방금 구매 알림 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [254](https://lucianlabs.dev/uxui-prompt/#254) | 공개 범위를 바꾸는 공유 창 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [255](https://lucianlabs.dev/uxui-prompt/#255) | 끌어 옮기는 칸반 카드 | X | C/S/V | Kanban rejected: Adds management columns and drag workflow to a deliberately simple daily planner. |
| [256](https://lucianlabs.dev/uxui-prompt/#256) | 숫자가 차오른 뒤 걷히는 첫 로딩 화면 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [257](https://lucianlabs.dev/uxui-prompt/#257) | 폭을 끌어 보는 반응형 미리보기 | T | C/S/V | Window-size QA: Test native minimum size/DPI/layout transitions; not an extra in-app device-preview tool. |
| [258](https://lucianlabs.dev/uxui-prompt/#258) | 흐릿하게 먼저 뜨고 선명해지는 사진 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [259](https://lucianlabs.dev/uxui-prompt/#259) | 글 중간에서 열리는 멤버십 벽 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [260](https://lucianlabs.dev/uxui-prompt/#260) | 스크롤에 맞춰 채워지는 문장 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [261](https://lucianlabs.dev/uxui-prompt/#261) | 별점 막대로 걸러 보는 리뷰 | X | C | social-proof: Testimonials/customer counters are irrelevant and add unwanted marketing copy. |
| [262](https://lucianlabs.dev/uxui-prompt/#262) | 목록과 함께 움직이는 매장 찾기 지도 | O | C/S/V | Plan-list and outline cross-highlight: Highlight known planned interval only; never infer actual attribution or start recording on hover. |
| [263](https://lucianlabs.dev/uxui-prompt/#263) | 빛이 흐르는 제목과 생각 중 문구 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [264](https://lucianlabs.dev/uxui-prompt/#264) | 이메일 오타를 짚어 주는 입력 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [265](https://lucianlabs.dev/uxui-prompt/#265) | 주문 마감까지 줄어드는 도착 보장 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [266](https://lucianlabs.dev/uxui-prompt/#266) | 섞을 때마다 바뀌는 색 팔레트 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [267](https://lucianlabs.dev/uxui-prompt/#267) | 언어를 바꾸면 갈아 끼워지는 문구 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [268](https://lucianlabs.dev/uxui-prompt/#268) | @를 치면 따라 뜨는 멘션 목록 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [269](https://lucianlabs.dev/uxui-prompt/#269) | 이름을 따라 써야 지워지는 삭제 확인 | X | C/S/V | Typed-name task deletion rejected: Excessive for ordinary tasks; X plus undo, confirmation only for genuinely irreversible bulk data removal. |
| [270](https://lucianlabs.dev/uxui-prompt/#270) | 커서를 따라 흩어지는 히어로 UI 조각 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [271](https://lucianlabs.dev/uxui-prompt/#271) | 종류별로 걸러 보는 업데이트 소식 | O | C/S/V | Record status filters: Only where enough data exists; preserve original date order and explicit empty-result state. |
| [272](https://lucianlabs.dev/uxui-prompt/#272) | 패키지 도구별 설치 명령 탭 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [273](https://lucianlabs.dev/uxui-prompt/#273) | 줄을 누르면 열리는 상세 옆 패널 | R | C/S/V | Record detail side panel: Keep selected date/context and restore focus on close; narrow windows use a bounded dialog. |
| [274](https://lucianlabs.dev/uxui-prompt/#274) | 입력창으로 변신하는 버튼 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [275](https://lucianlabs.dev/uxui-prompt/#275) | 본문을 따라오는 목차 표시 | R | C/S/V | Settings section navigation: Section anchors for long settings, selected section follows scroll; no extra top-level pages. |
| [276](https://lucianlabs.dev/uxui-prompt/#276) | 사진이 따라오는 작업 목록 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [277](https://lucianlabs.dev/uxui-prompt/#277) | 바늘이 떨리는 인터넷 속도계 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [278](https://lucianlabs.dev/uxui-prompt/#278) | 인원에 따라 바뀌는 요금 계산기 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [279](https://lucianlabs.dev/uxui-prompt/#279) | 시간을 고르면 갈라지는 예약 버튼 | X | C/S/V | Fixed booking slots rejected: Conflicts with free optional start/end/duration input and arbitrary user schedules. |
| [280](https://lucianlabs.dev/uxui-prompt/#280) | 노이즈에서 떠오르는 AI 이미지 생성 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [281](https://lucianlabs.dev/uxui-prompt/#281) | 형광펜이 지나가는 문장 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [282](https://lucianlabs.dev/uxui-prompt/#282) | 넓어지며 드러나는 사진 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [283](https://lucianlabs.dev/uxui-prompt/#283) | 해지 전에 건네는 혜택 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [284](https://lucianlabs.dev/uxui-prompt/#284) | 차례로 확인되는 도메인 연결 | R | C/S/V | Setup checklist presentation: Real readiness signals only; source timed DNS/SSL success is not actual camera readiness. |
| [285](https://lucianlabs.dev/uxui-prompt/#285) | 초대하면 수락까지 이어지는 팀원 목록 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [286](https://lucianlabs.dev/uxui-prompt/#286) | 한 단계씩 들어가는 모바일 하위 메뉴 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [287](https://lucianlabs.dev/uxui-prompt/#287) | 필름처럼 지나가는 페이지 속도 측정 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [288](https://lucianlabs.dev/uxui-prompt/#288) | 상세정보 펼쳐보기 | R | C/S/V | Secondary details disclosure: Explicit expand/collapse with scroll/focus stability; never hide primary study controls. |
| [289](https://lucianlabs.dev/uxui-prompt/#289) | 바로 반영되는 보기 설정 패널 | O | C/S/V | Text scaling and reduced motion: Extra preference needs approval and layout tests; no animated font resizing during typing. |
| [290](https://lucianlabs.dev/uxui-prompt/#290) | 먼저 묻고 띄우는 알림 허용 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [291](https://lucianlabs.dev/uxui-prompt/#291) | 긴 주소가 짧게 접히는 링크 줄이기 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [292](https://lucianlabs.dev/uxui-prompt/#292) | 걸러지며 다시 앉는 갤러리 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [293](https://lucianlabs.dev/uxui-prompt/#293) | 담아서 견주는 상품 비교함 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [294](https://lucianlabs.dev/uxui-prompt/#294) | 스크롤로 조립되는 기기 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [295](https://lucianlabs.dev/uxui-prompt/#295) | 문의 종류에 따라 바뀌는 문의 폼 | R | C/S/V | Mode-specific preparation: Show Pomodoro settings only when selected; general learning remains first-class and independent. |
| [296](https://lucianlabs.dev/uxui-prompt/#296) | 훑어 넘기는 초성 색인 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [297](https://lucianlabs.dev/uxui-prompt/#297) | 블록을 쌓아 만드는 페이지 | O | C/S/V | Task reorder controls: Only explicit user reorder with stable row identity; no page-builder blocks or fake autosave. |
| [298](https://lucianlabs.dev/uxui-prompt/#298) | 뜯어서 받는 할인 쿠폰 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [299](https://lucianlabs.dev/uxui-prompt/#299) | 한도에 가까워지면 색이 바뀌는 사용량 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [300](https://lucianlabs.dev/uxui-prompt/#300) | 주소마다 확인되는 도메인 검색 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [301](https://lucianlabs.dev/uxui-prompt/#301) | 용량이 줄어드는 이미지 최적화 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [302](https://lucianlabs.dev/uxui-prompt/#302) | 화면 위에 꽂는 피드백 핀 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [303](https://lucianlabs.dev/uxui-prompt/#303) | 글꼴 짝과 크기 비율 고르기 | T | C/S/V | Type-scale QA: Keep SUIT; use size/weight hierarchy internally, not a font-picker feature. |
| [304](https://lucianlabs.dev/uxui-prompt/#304) | 검색해서 채우는 배송지 주소 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [305](https://lucianlabs.dev/uxui-prompt/#305) | 고를 때마다 개수가 바뀌는 필터 서랍 | O | C/S/V | Advanced record filters: A bounded desktop panel only when justified; preserve active filters, clear and cancel semantics. |
| [306](https://lucianlabs.dev/uxui-prompt/#306) | 궤도를 도는 연동 도구 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [307](https://lucianlabs.dev/uxui-prompt/#307) | 타자기로 바뀌는 핵심 단어 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [308](https://lucianlabs.dev/uxui-prompt/#308) | 그리드와 목록 사이 전환 | X | C/S/V | Grid/list switch rejected: Redundant second planner layout, adds settings and reflow without a demonstrated user need. |
| [309](https://lucianlabs.dev/uxui-prompt/#309) | 겹겹이 물러나는 산맥 스크롤 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [310](https://lucianlabs.dev/uxui-prompt/#310) | 글자 사이로 비치는 영상 제목 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [311](https://lucianlabs.dev/uxui-prompt/#311) | 오늘 하루 보지 않기 이벤트 팝업 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [312](https://lucianlabs.dev/uxui-prompt/#312) | 반으로 갈라지는 커튼 메뉴 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [313](https://lucianlabs.dev/uxui-prompt/#313) | 크기에 맞춰 바뀌는 커피 컵 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [314](https://lucianlabs.dev/uxui-prompt/#314) | 대상에 맞춰 모양을 바꾸는 커서 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [315](https://lucianlabs.dev/uxui-prompt/#315) | 끌어다 버리는 휴지통 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [316](https://lucianlabs.dev/uxui-prompt/#316) | 스프링 감도 조율판 | T | C/S/V | Motion QA: Internal easing comparison only; no spring-tuning panel in user settings. |
| [317](https://lucianlabs.dev/uxui-prompt/#317) | 순서가 날아가는 정렬 목록 | O | C/S/V | Explicit task ordering: Do not auto-sort on status/clock changes; editing and current-task selection must remain stable. |
| [318](https://lucianlabs.dev/uxui-prompt/#318) | 스크롤로 그려지는 여행 경로 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [319](https://lucianlabs.dev/uxui-prompt/#319) | 커서를 따라 일렁이는 오로라 배경 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [320](https://lucianlabs.dev/uxui-prompt/#320) | 동전으로 긁는 즉석 복권 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [321](https://lucianlabs.dev/uxui-prompt/#321) | 페이지를 덮고 걷히는 전환 막 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [322](https://lucianlabs.dev/uxui-prompt/#322) | 굴러가는 실시간 인기 검색어 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [323](https://lucianlabs.dev/uxui-prompt/#323) | 커서를 따라 떨어지는 사진 꼬리 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [324](https://lucianlabs.dev/uxui-prompt/#324) | 밀려 들어오는 화면 스택 | O | C/S/V | Detail navigation transition: Only where true nested navigation exists; no forced mobile-style stack for five desktop tabs. |
| [325](https://lucianlabs.dev/uxui-prompt/#325) | 코드가 비치는 엑스레이 렌즈 | X | C | site-builder-tools: Builder/developer tooling is not a user-facing study feature. |
| [326](https://lucianlabs.dev/uxui-prompt/#326) | 칸이 뒤집히며 옮겨 가는 와플 차트 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [327](https://lucianlabs.dev/uxui-prompt/#327) | 신호가 튀는 글리치 타이틀 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [328](https://lucianlabs.dev/uxui-prompt/#328) | 목록에서 펼쳐지는 상세 카드 | X | C/S/V | Expanding full-screen cards rejected: Decorative destination-page transitions obscure direct record/task editing. |
| [329](https://lucianlabs.dev/uxui-prompt/#329) | 섹션마다 물드는 배경색 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [330](https://lucianlabs.dev/uxui-prompt/#330) | 누르면 워프하는 별빛 공간 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [331](https://lucianlabs.dev/uxui-prompt/#331) | 튕겨 돌리는 경품 돌림판 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [332](https://lucianlabs.dev/uxui-prompt/#332) | 작아지며 붙는 큰 제목 | X | C/S/V | Collapsing giant title rejected: No giant headings to shrink; controls must stay predictably placed. |
| [333](https://lucianlabs.dev/uxui-prompt/#333) | 밀어서 취소하는 음성 녹음 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [334](https://lucianlabs.dev/uxui-prompt/#334) | 열면 켜지는 노트북 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [335](https://lucianlabs.dev/uxui-prompt/#335) | 들어온 쪽에서 덮이는 타일 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [336](https://lucianlabs.dev/uxui-prompt/#336) | 세 높이에 멈추는 바텀 시트 | X | C/S/V | Three-height bottom sheet rejected: Mobile map pattern is unnecessary for the current Windows-first workflow. |
| [337](https://lucianlabs.dev/uxui-prompt/#337) | 남쪽부터 물드는 벚꽃 개화 지도 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [338](https://lucianlabs.dev/uxui-prompt/#338) | 면을 굴리는 단어 큐브 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [339](https://lucianlabs.dev/uxui-prompt/#339) | 끌어 넘기는 카드 캐러셀 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [340](https://lucianlabs.dev/uxui-prompt/#340) | 열쇠구멍으로 빨려 드는 장면 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [341](https://lucianlabs.dev/uxui-prompt/#341) | 커서와 이어지는 별자리 그물 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [342](https://lucianlabs.dev/uxui-prompt/#342) | 리본을 풀고 여는 선물 상자 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [343](https://lucianlabs.dev/uxui-prompt/#343) | 로켓으로 돌아가는 맨 위 버튼 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [344](https://lucianlabs.dev/uxui-prompt/#344) | 튕기며 꽂히는 지도 핀 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [345](https://lucianlabs.dev/uxui-prompt/#345) | 돌려 보고 따는 음료 캔 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [346](https://lucianlabs.dev/uxui-prompt/#346) | 커서 안쪽에만 보이는 다른 문장 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [347](https://lucianlabs.dev/uxui-prompt/#347) | 모서리로 던지는 PiP 영상 | O | C/S/V | Floating preview/timer: New window and persistence policy need approval; preserve hidden-camera slot and existing study layout. |
| [348](https://lucianlabs.dev/uxui-prompt/#348) | 빙글 도는 원형 문구 배지 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [349](https://lucianlabs.dev/uxui-prompt/#349) | 픽셀로 흩어지는 사진 전환 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [350](https://lucianlabs.dev/uxui-prompt/#350) | 고리가 올라가는 자물쇠 토글 | X | C | Lock morph rejected: No corresponding lock/privacy action to add; pin recurrence needs a pin, not a lock metaphor. |
| [351](https://lucianlabs.dev/uxui-prompt/#351) | 속도만큼 기우는 카드 목록 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [352](https://lucianlabs.dev/uxui-prompt/#352) | 소용돌이치는 흐름장 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [353](https://lucianlabs.dev/uxui-prompt/#353) | 도장이 쌓이는 커피 쿠폰 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [354](https://lucianlabs.dev/uxui-prompt/#354) | 모양이 바뀌며 따라가는 메가 메뉴 | X | C | navigation: Decorative or website/mobile-specific navigation is unnecessary for the current desktop pages. |
| [355](https://lucianlabs.dev/uxui-prompt/#355) | 저장 상태를 알려 주는 구름 표시 | R | C/S/V | Truthful local save status: Use pending/saving/saved/error from backend completion; no fake cloud icon or timer-based success. |
| [356](https://lucianlabs.dev/uxui-prompt/#356) | 돋보기로 들여다보는 시계 | X | C | commerce-pricing: Commerce, checkout or pricing workflow is irrelevant to the local study app. |
| [357](https://lucianlabs.dev/uxui-prompt/#357) | 가까울수록 굵어지는 글자 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [358](https://lucianlabs.dev/uxui-prompt/#358) | 길게 눌러 미리 보는 메시지 | X | C | app-screens: Standalone commerce/media/collaboration screen is outside the approved app workflow. |
| [359](https://lucianlabs.dev/uxui-prompt/#359) | 점수와 순위를 오가는 기울기 차트 | O | C/S/V | Previous-period comparison: Needs meaningful same-unit metrics; no ranking or forced extra comparison page. |
| [360](https://lucianlabs.dev/uxui-prompt/#360) | 흩어졌다 모이는 글자 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [361](https://lucianlabs.dev/uxui-prompt/#361) | 블라인드처럼 돌아가는 슬라이드 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [362](https://lucianlabs.dev/uxui-prompt/#362) | 돌아가는 드럼 시간 선택 | X | C/S/V | Drum clock picker rejected: Slower than the requested independent hour/minute fields and keyboard Tab workflow. |
| [363](https://lucianlabs.dev/uxui-prompt/#363) | 커서에서 퍼지는 점 격자 파동 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [364](https://lucianlabs.dev/uxui-prompt/#364) | 하루 한 칸 여는 어드벤트 달력 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [365](https://lucianlabs.dev/uxui-prompt/#365) | 친구 초대로 앞당겨지는 대기 순번 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [366](https://lucianlabs.dev/uxui-prompt/#366) | 훑으면 넘어가는 영상 미리보기 | X | C | cursor-hover: Custom cursors, tilt or cursor-following media reduce predictable desktop interaction. |
| [367](https://lucianlabs.dev/uxui-prompt/#367) | 해마다 모양이 바뀌는 인구 피라미드 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [368](https://lucianlabs.dev/uxui-prompt/#368) | 문장을 따라가는 읽기 초점 | X | C/S/V | Cursor-driven reading blur rejected: Fading unrelated text hurts visibility; only explicit current-time row emphasis is relevant. |
| [369](https://lucianlabs.dev/uxui-prompt/#369) | 부채처럼 펼쳐지는 사진 더미 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [370](https://lucianlabs.dev/uxui-prompt/#370) | 선이 지나가며 켜지는 연혁 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [371](https://lucianlabs.dev/uxui-prompt/#371) | 솟아오르는 등고선 지도 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [372](https://lucianlabs.dev/uxui-prompt/#372) | 차오르면 레벨 업하는 경험치 | X | C | promos-rewards: Promotions, rewards and gamification are not approved study requirements. |
| [373](https://lucianlabs.dev/uxui-prompt/#373) | 다섯 가지 밑줄 호버 | R | C/S/V | Navigation feedback: One restrained persistent selected underline; hover cannot be the sole page indicator. |
| [374](https://lucianlabs.dev/uxui-prompt/#374) | 분기마다 움직이는 앱 성장 버블 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [375](https://lucianlabs.dev/uxui-prompt/#375) | 단어마다 튀어나오는 자막 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [376](https://lucianlabs.dev/uxui-prompt/#376) | 넘겨 보는 스토리 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [377](https://lucianlabs.dev/uxui-prompt/#377) | 글을 따라 바뀌는 휴대폰 화면 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [378](https://lucianlabs.dev/uxui-prompt/#378) | 입자로 모이는 글자 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [379](https://lucianlabs.dev/uxui-prompt/#379) | 이어질수록 커지는 연속 기록 불꽃 | O | C/S/V | Study streak summary: Optional small record summary only; no persistent flames, particles or guilt-inducing prompts. |
| [380](https://lucianlabs.dev/uxui-prompt/#380) | 표정이 바뀌는 만족도 슬라이더 | X | C | forms-input: Unrequested business/authentication/AI input workflow; do not add speculative features. |
| [381](https://lucianlabs.dev/uxui-prompt/#381) | 확대하면 갈라지는 지도 묶음 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [382](https://lucianlabs.dev/uxui-prompt/#382) | 물결 위를 흐르는 문구 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [383](https://lucianlabs.dev/uxui-prompt/#383) | 물결로 넘어가는 온보딩 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [384](https://lucianlabs.dev/uxui-prompt/#384) | 이어 붙는 무한 피드 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [385](https://lucianlabs.dev/uxui-prompt/#385) | 점으로 찍은 실시간 지구본 | X | C | hero-backgrounds: Hero, particles and decorative scenes compete with study and add rendering work. |
| [386](https://lucianlabs.dev/uxui-prompt/#386) | 빛나며 풀리는 업적 배지 | X | C/S/V | Achievement system rejected: New gamification/state storage and visual noise without current need. |
| [387](https://lucianlabs.dev/uxui-prompt/#387) | 축을 그어 거르는 평행 좌표 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [388](https://lucianlabs.dev/uxui-prompt/#388) | 단어마다 초점이 맞는 인용구 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [389](https://lucianlabs.dev/uxui-prompt/#389) | 옆으로 펼쳐지는 사진 패널 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [390](https://lucianlabs.dev/uxui-prompt/#390) | 장 번호가 굴러가는 스크롤 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [391](https://lucianlabs.dev/uxui-prompt/#391) | 달이 바뀌면 다시 엮이는 코드 다이어그램 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [392](https://lucianlabs.dev/uxui-prompt/#392) | 손으로 그린 강조 표시 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [393](https://lucianlabs.dev/uxui-prompt/#393) | 내 기기에 맞춘 다운로드 안내 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [394](https://lucianlabs.dev/uxui-prompt/#394) | 스크롤에 엇갈려 흐르는 문구 띠 | X | C | scroll-motion: Scroll-driven spectacle hides/repositions information; stable controls and direct navigation take priority. |
| [395](https://lucianlabs.dev/uxui-prompt/#395) | 해를 바꾸면 밀려나는 기온 리지라인 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [396](https://lucianlabs.dev/uxui-prompt/#396) | 눌러야 보이는 스포일러 가리개 | X | C | text-motion: Animated/deformed text reduces stable reading and conflicts with clear SUIT typography. |
| [397](https://lucianlabs.dev/uxui-prompt/#397) | 파도처럼 뒤집히는 타일 그림 | X | C | sections-content: Website content/marketing/gallery section is not a native study-app task. |
| [398](https://lucianlabs.dev/uxui-prompt/#398) | 점을 끌면 다시 맞는 회귀선 | X | C/S/V | Study-score regression rejected: No measured score dataset or validated causal relation; cannot infer grades from focus tracking. |
| [399](https://lucianlabs.dev/uxui-prompt/#399) | 달마다 다시 앉는 리뷰 단어 구름 | X | C | data-motion: Specialized animated data presentation lacks a justified real metric; preserve legibility and stable chronology. |
| [400](https://lucianlabs.dev/uxui-prompt/#400) | 커서를 함께 맞추는 작은 차트 묶음 | R | C/S/V | Coordinated record readout: One date cursor and exact unit-labelled values; no fake data or silent denominator changes. |

## Candidate Contact-Sheet Index
- [#007 재생 버튼 모핑](lucian-review-captures-2026-11-16/sheet-01.png)
- [#008 복사 버튼 체크 전환](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#010 분할 실행 버튼](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#012 북마크 리본](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#013 늘어나는 스위치](lucian-review-captures-2026-11-16/sheet-01.png)
- [#014 할 일 체크리스트](lucian-review-captures-2026-11-16/sheet-01.png)
- [#015 요금제 라디오 카드](lucian-review-captures-2026-11-16/sheet-01.png)
- [#017 기울어지는 값 말풍선 슬라이더](lucian-review-captures-2026-11-16/sheet-01.png)
- [#018 굴러가는 수량 스테퍼](lucian-review-captures-2026-11-16/sheet-01.png)
- [#019 관심사 칩 다중 선택](lucian-review-captures-2026-11-16/sheet-01.png)
- [#023 펼쳐지는 알림 설정](lucian-review-captures-2026-11-16/sheet-01.png)
- [#025 테두리로 떠오르는 라벨 입력](lucian-review-captures-2026-11-16/sheet-01.png)
- [#026 인증번호 6자리 입력](lucian-review-captures-2026-11-16/sheet-01.png)
- [#027 펼쳐지는 상단 검색](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#028 늘어나는 댓글 입력창](lucian-review-captures-2026-11-16/sheet-01.png)
- [#030 기간 선택 달력](lucian-review-captures-2026-11-16/sheet-01.png)
- [#031 맞춤 선택 목록](lucian-review-captures-2026-11-16/sheet-02.png)
- [#033 제목 바로 고치기](lucian-review-captures-2026-11-16/sheet-02.png)
- [#034 공항 자동완성](lucian-review-captures-2026-11-16/sheet-02.png)
- [#035 송금 금액 입력](lucian-review-captures-2026-11-16/sheet-02.png)
- [#036 비밀번호 강도 미터](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#038 우클릭 컨텍스트 메뉴](lucian-review-captures-2026-11-16/sheet-02.png)
- [#039 미끄러지는 알약 탭](lucian-review-captures-2026-11-16/sheet-02.png)
- [#040 펼쳐지는 사이드 레일](lucian-review-captures-2026-11-16/sheet-02.png)
- [#042 단계 진행 마법사](lucian-review-captures-2026-11-16/sheet-02.png)
- [#043 늘어나는 페이지 번호](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#044 자주 묻는 질문 아코디언](lucian-review-captures-2026-11-16/sheet-02.png)
- [#046 커맨드 팔레트](lucian-review-captures-2026-11-16/sheet-02.png)
- [#047 기간 세그먼트 컨트롤](lucian-review-captures-2026-11-16/sheet-02.png)
- [#048 스와이프와 이어진 밑줄 탭](lucian-review-captures-2026-11-16/sheet-02.png)
- [#061 썸네일에서 열리는 라이트박스](lucian-review-captures-2026-11-16/sheet-03.png)
- [#070 겹쳐 쌓이는 토스트](lucian-review-captures-2026-11-16/sheet-03.png)
- [#071 밀어서 지우고 되돌리는 스낵바](lucian-review-captures-2026-11-16/sheet-03.png)
- [#072 접히는 인라인 알림](lucian-review-captures-2026-11-16/sheet-03.png)
- [#074 알림 벨과 드롭다운](lucian-review-captures-2026-11-16/sheet-03.png)
- [#075 업로드 진행 패널](lucian-review-captures-2026-11-16/sheet-03.png)
- [#076 미끄러지며 따라오는 툴팁](lucian-review-captures-2026-11-16/sheet-03.png)
- [#077 반응 고르는 팝오버](lucian-review-captures-2026-11-16/sheet-03.png)
- [#079 뼈대에서 피어나는 게시물](lucian-review-captures-2026-11-16/sheet-03.png)
- [#080 궤도가 모이는 동기화 스피너](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#082 아이콘을 채우는 설치 진행](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#083 대기에서 진행으로 바뀌는 막대](lucian-review-captures-2026-11-16/sheet-03.png)
- [#088 종이를 삼키는 빈 폴더](lucian-review-captures-2026-11-16/sheet-03.png)
- [#090 플러그가 다시 꽂히는 오류 위젯](lucian-review-captures-2026-11-16/sheet-03.png)
- [#091 오프라인에서 쌓였다 보내지는 메시지](lucian-review-captures-2026-11-16/sheet-04.png)
- [#092 필터를 풀어 주는 빈 검색 결과](lucian-review-captures-2026-11-16/sheet-04.png)
- [#093 할 일을 다 끝내면 터지는 축하](lucian-review-captures-2026-11-16/sheet-04.png)
- [#095 모양이 바뀌는 막대 차트](lucian-review-captures-2026-11-16/sheet-04.png)
- [#096 훑으면 색이 갈리는 주가 선](lucian-review-captures-2026-11-16/sheet-04.png)
- [#097 항목을 빼면 다시 나뉘는 도넛](lucian-review-captures-2026-11-16/sheet-04.png)
- [#098 자리마다 굴러가는 실시간 지표](lucian-review-captures-2026-11-16/sheet-04.png)
- [#099 한 바퀴를 넘기는 활동 링](lucian-review-captures-2026-11-16/sheet-04.png)
- [#100 반으로 접히는 플립 타이머](lucian-review-captures-2026-11-16/sheet-04.png)
- [#101 분할 작업창](lucian-review-captures-2026-11-16/sheet-04.png)
- [#109 주간 가능 시간 칠하기](lucian-review-captures-2026-11-16/sheet-04.png)
- [#110 일정 겹침 해소](lucian-review-captures-2026-11-16/sheet-04.png)
- [#111 작업 기간 편집](lucian-review-captures-2026-11-16/sheet-05.png)
- [#118 타이포그래피 견본](lucian-review-captures-2026-11-16/sheet-05.png)
- [#119 다층 그림자](lucian-review-captures-2026-11-16/sheet-05.png)
- [#120 연결된 모서리 반경](lucian-review-captures-2026-11-16/sheet-05.png)
- [#121 그리드 레이아웃 구성](lucian-review-captures-2026-11-16/sheet-05.png)
- [#124 색 대비 검사](lucian-review-captures-2026-11-16/sheet-05.png)
- [#130 CSV 필드 연결](lucian-review-captures-2026-11-16/sheet-05.png)
- [#131 동행자 입력 묶음](lucian-review-captures-2026-11-16/sheet-05.png)
- [#133 단위 왕복 변환](lucian-review-captures-2026-11-16/sheet-05.png)
- [#139 여백 주석 연결](lucian-review-captures-2026-11-16/sheet-05.png)
- [#141 단축키 조합 기록](lucian-review-captures-2026-11-16/sheet-05.png)
- [#143 계산하는 셀](lucian-review-captures-2026-11-16/sheet-05.png)
- [#144 열 순서 편집](lucian-review-captures-2026-11-16/sheet-06.png)
- [#151 기여가 쌓이는 주간 격자](lucian-review-captures-2026-11-16/sheet-06.png)
- [#157 서비스가 층을 이루는 사용량](lucian-review-captures-2026-11-16/sheet-06.png)
- [#163 기준을 넘어가는 실적 눈금](lucian-review-captures-2026-11-16/sheet-06.png)
- [#166 흐름에서 고르는 오류 기록](lucian-review-captures-2026-11-16/sheet-06.png)
- [#170 장애 구간을 확대하는 시간축](lucian-review-captures-2026-11-16/sheet-06.png)
- [#173 방향을 보정하는 측정 나침반](lucian-review-captures-2026-11-16/sheet-06.png)
- [#174 방향별로 펼치는 분포 장미](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#175 척도를 맞추는 비교 레일](lucian-review-captures-2026-11-16/sheet-06.png)
- [#176 버전 필름스트립](lucian-review-captures-2026-11-16/sheet-06.png)
- [#178 묶음 선택 작업대](lucian-review-captures-2026-11-16/sheet-06.png)
- [#186 기기 페어링 레이더](lucian-review-captures-2026-11-16/sheet-06.png)
- [#190 예약 발송 보관함](lucian-review-captures-2026-11-16/sheet-06.png)
- [#192 3채널 오디오 믹서](lucian-review-captures-2026-11-16/sheet-07.png)
- [#193 호흡 페이스메이커](lucian-review-captures-2026-11-16/sheet-07.png)
- [#194 오디오 루프 구간](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#197 화면 안내 스포트라이트](lucian-review-captures-2026-11-16/sheet-07.png)
- [#198 네트워크 경로 진단](lucian-review-captures-2026-11-16/sheet-07.png)
- [#200 접히는 정산 영수증](lucian-review-captures-2026-11-16/sheet-07.png)
- [#218 스크롤하면 아래로 붙는 미니 플레이어](lucian-review-captures-2026-11-16/sheet-07.png)
- [#227 새 주문이 밀고 들어오는 실시간 표](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#238 막대로 보는 서비스 상태 페이지](lucian-review-captures-2026-11-16/sheet-07.png)
- [#244 틀린 칸으로 데려가는 폼 검증](lucian-review-captures-2026-11-16/sheet-07.png)
- [#250 바꾸면 내려오는 저장 바](lucian-review-captures-2026-11-16/sheet-07.png)
- [#255 끌어 옮기는 칸반 카드](lucian-review-captures-2026-11-16/sheet-07.png)
- [#257 폭을 끌어 보는 반응형 미리보기](lucian-review-captures-2026-11-16/sheet-07.png)
- [#262 목록과 함께 움직이는 매장 찾기 지도](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#269 이름을 따라 써야 지워지는 삭제 확인](lucian-review-captures-2026-11-16/sheet-07.png)
- [#271 종류별로 걸러 보는 업데이트 소식](lucian-review-captures-2026-11-16/sheet-08.png)
- [#273 줄을 누르면 열리는 상세 옆 패널](lucian-review-captures-2026-11-16/sheet-08.png)
- [#275 본문을 따라오는 목차 표시](lucian-review-captures-2026-11-16/sheet-extra.png)
- [#279 시간을 고르면 갈라지는 예약 버튼](lucian-review-captures-2026-11-16/sheet-08.png)
- [#284 차례로 확인되는 도메인 연결](lucian-review-captures-2026-11-16/sheet-08.png)
- [#288 상세정보 펼쳐보기](lucian-review-captures-2026-11-16/sheet-08.png)
- [#289 바로 반영되는 보기 설정 패널](lucian-review-captures-2026-11-16/sheet-08.png)
- [#295 문의 종류에 따라 바뀌는 문의 폼](lucian-review-captures-2026-11-16/sheet-08.png)
- [#297 블록을 쌓아 만드는 페이지](lucian-review-captures-2026-11-16/sheet-08.png)
- [#303 글꼴 짝과 크기 비율 고르기](lucian-review-captures-2026-11-16/sheet-08.png)
- [#305 고를 때마다 개수가 바뀌는 필터 서랍](lucian-review-captures-2026-11-16/sheet-08.png)
- [#308 그리드와 목록 사이 전환](lucian-review-captures-2026-11-16/sheet-08.png)
- [#316 스프링 감도 조율판](lucian-review-captures-2026-11-16/sheet-08.png)
- [#317 순서가 날아가는 정렬 목록](lucian-review-captures-2026-11-16/sheet-09.png)
- [#324 밀려 들어오는 화면 스택](lucian-review-captures-2026-11-16/sheet-09.png)
- [#328 목록에서 펼쳐지는 상세 카드](lucian-review-captures-2026-11-16/sheet-09.png)
- [#332 작아지며 붙는 큰 제목](lucian-review-captures-2026-11-16/sheet-09.png)
- [#336 세 높이에 멈추는 바텀 시트](lucian-review-captures-2026-11-16/sheet-09.png)
- [#347 모서리로 던지는 PiP 영상](lucian-review-captures-2026-11-16/sheet-09.png)
- [#355 저장 상태를 알려 주는 구름 표시](lucian-review-captures-2026-11-16/sheet-09.png)
- [#359 점수와 순위를 오가는 기울기 차트](lucian-review-captures-2026-11-16/sheet-09.png)
- [#362 돌아가는 드럼 시간 선택](lucian-review-captures-2026-11-16/sheet-09.png)
- [#368 문장을 따라가는 읽기 초점](lucian-review-captures-2026-11-16/sheet-09.png)
- [#373 다섯 가지 밑줄 호버](lucian-review-captures-2026-11-16/sheet-09.png)
- [#379 이어질수록 커지는 연속 기록 불꽃](lucian-review-captures-2026-11-16/sheet-09.png)
- [#386 빛나며 풀리는 업적 배지](lucian-review-captures-2026-11-16/sheet-10.png)
- [#398 점을 끌면 다시 맞는 회귀선](lucian-review-captures-2026-11-16/sheet-10.png)
- [#400 커서를 함께 맞추는 작은 차트 묶음](lucian-review-captures-2026-11-16/sheet-10.png)

