# V3 UI Redesign: Clear Desk

> Documentation reconciliation (2026-11-16): Historical visual proposal; current rollout is the native QML application plan linked from the documentation map. [Documentation map](../docs/README.md).

Current approval candidate (2026-10-08): [new composition, design system, and rollout](v3-approval-2026-10-08/DESIGN.md), [rendered gallery](v3-approval-2026-10-08/GALLERY.md). The user requested a complete recomposition rather than refinement of the old layout. The new candidate replaces the old shell/layout proposal, including its no-sidebar constraint. This older document and static examples remain historical references, not approved implementation instructions.

Updated: 2026-10-05
Status: proposal for approval. The six approved planner/display fixes are implemented separately; this document does not approve the visual rollout or adjacent behavior changes.

## 1. Decision

A bright, precise study workspace, not a monitoring dashboard or a marketing page. Borrow the clarity of modern Korean finance/product apps, not their branding. Redesign layout, typography, interaction states, charts, and motion together. Changing colors alone will not solve the current hierarchy and legibility problems.

Keep Python + PySide6/QML. Native property animations already support this direction. A web/Electron migration would add packaging, IPC, and deployment risk without addressing the current data/interaction defects. Do not promise camera performance from a static preview.

Deliver the learning and planner surfaces first. Keep the other pages coherent with those decisions, then implement them. No new home page, sidebar, mandatory subject taxonomy, or theme selector.

Static examples: [ui-v3-preview.qml](ui-v3-preview.qml). They have no engine/DB/camera connection, use fictional data, and currently render with installed Malgun Gothic, not the proposed Pretendard. They demonstrate composition, not working features or animation performance.

Rendered proposals, with Korean/symbol fonts explicitly loaded:

- [Learning, 1280x720](captures/redesign-learning-1280x720.png) / [Learning, 1024x680](captures/redesign-learning-1024x680.png).
- [Planner, 1280x720](captures/redesign-planner-1280x720.png) / [Planner, 1024x680](captures/redesign-planner-1024x680.png).
- Preview omits some production controls/icons for clarity; the implementation must retain pinning, deferred status, calibration, and date navigation. It is not an approved reduced feature set.

## 2. What Actually Changes

- Replace the five pages' repeated floating/nested containers with a white workspace, structural dividers, and small framed tools only where useful.
- Replace heavy selected-tab blocks with a quiet navigation row and a clear active underline.
- Give the current task, timer, and primary session action stable positions. Remove multiple empty-state messages and oversized state banners.
- Make planner input/header/saved-row columns share one grid. Keep all optional time fields visible and directly editable.
- Replace tiny chart labels and glyph/emoji controls with legible type and one consistent icon set.
- Introduce local, interruptible transitions. Do not animate every camera update or every timer digit.

## 3. Shell and Geometry

Five routes remain: Learning / Measurement / Planner / Records / Settings. No extra start page. Main navigation is always visible; session state lives above page loading, so switching pages cannot reset timers, capture, or calibration.

- Desktop baseline: 1280 x 720 logical pixels. Minimum target: 1024 x 680, subject to rendered acceptance before changing the current minimum.
- Header: 56 px; page padding: 20 px; section gaps: 16-24 px; control heights: 40-44 px.
- Header left: five tabs with text, 14 px/600. Right: representative D-day and clock. D-day label and event title both 17 px, same color and vertical alignment. Long titles elide with a full tooltip, not a second line that changes header height.
- Learning: left task rail 228-256 px; flexible timer center; right camera/timeline rail 256-300 px. At 1024: 40 px outer padding + 24 px gaps + 228 + 476 + 256 = 1024. No page-level scroll; task list can scroll internally. Session actions never scroll away.
- Planner: roughly 65% editable plan / 35% actual timetable. Below 1120, timetable stays 300 px and title column flexes; time and action columns remain fixed. Separate internal scroll regions are acceptable. Do not remove optional inputs to make it fit.
- Records and Settings may scroll. Date navigation, period selection, and unsaved-settings actions stay reachable.

## 4. Visual Tokens

Palette is predominantly white and neutral, with blue for commands and three independent semantic chart colors. Green does not become the color of every button.

- App surround: `#F5F6F8`; workspace: `#FFFFFF`; recessed inputs: `#F8F9FB`.
- Primary text: `#20252D`; secondary text: `#647080`; structural lines: `#E2E6EC`.
- Action/selection: `#2F5EEA`; light selection: `#EDF2FF`; focused input outline: action blue, 2 px.
- Success text: `#157344`; success fill: `#29B46D`; warning text: `#875900`; chart amber: `#EAB73E`; danger: `#E45160`.
- Break: `#CDD3DC`; unscored: neutral hatch; no activity: nearly white. These are different states, not different focus scores.
- Radius: 6 px controls, 8 px framed tools/dialogs. One quiet shadow for floating popups only. No glass blur, gradient backgrounds, decorative illustrations, or glow.
- Normal text must meet 4.5:1 contrast; large text and meaningful UI outlines 3:1. Verify real foreground/background pairs, including disabled controls and selected cells. Never use pale success fill as success text.

## 5. Type and Icons

Proposed font: locally bundled Pretendard, static 400/500/600/700 weights, SIL OFL notice included. Do not require an OS font installation or CDN. Fallback: Malgun Gothic, then Segoe UI. Assets are not downloaded or installed by this proposal.

- Body and controls: 14 px; task names: 15-16 px; secondary labels: 12-13 px; page heading: 22 px; D-day: 17 px.
- Current task title: 24 px, up to two lines in a stable-height slot. Free timer: 64 px; Pomodoro center digits: 56 px. No viewport-scaled fonts or negative tracking.
- Tabular numerals where supported, especially clocks, durations, and time inputs. QML `font.features` is available from Qt 6.6; verify `tnum` in the actual bundled font and keep fixed numeric slots as fallback.
- Proposed icons: local Lucide SVGs, 20 px, consistent strokes; 36-40 px hit areas. Include applicable ISC/Feather MIT notices. No new runtime dependency is needed for a small fixed icon set.
- Controls: play/pause/square for sessions, calendar and chevrons for dates, pin for recurrence, X for deletion, eye/eye-off for preview, rotate-ccw for clearing times. Every unfamiliar icon has a tooltip and accessible name.
- Preserve the existing blank/complete/deferred state cycle for now. A binary checkbox plus a separate defer command is a behavior decision, not an automatic visual replacement.

## 6. Learning: Now and Today

Layout:

```text
nav ------------------------------------------------ D-day / clock
Today's study --------------------------- mode / timer settings
tasks        | current task              | camera + hide control
             |                           | connection / compact state
             |       round timer         | rolling actual timetable
             |       today total         | current hour emphasized
edit today   | primary action / end      | sample-based legend
```

- Left: today's tasks, with selected, complete, and deferred visibly distinct. Match selection by `taskId`, never title. Completed tasks remain legible; use a check and restrained strike-through, not near-white text.
- Middle: one current-task block, then the mode switch and stable timer area. No separate marketing-like hero card or several competing status headlines.
- Empty states have one message: no plans, no selected task, all complete, or only deferred work. For no selection use one concise label such as "자유 학습"; do not also show "오늘 계획에서 선택하세요" in another block.
- Starting study without a task remains allowed. Missing calibration shows the required setup action locally; it does not masquerade as an inactive timer button with no explanation.
- Pomodoro ring: 260-280 px, 8-10 px track, round line caps; neutral track, blue focus phase, gray break phase. Timer digits stay still. Phase and cycle count appear once. The ring conveys time, never a claim of cognitive focus.
- During break show remaining break time; ending retains the final session time; starting a new session resets to zero. Today's accumulation remains separate.
- Primary action occupies one fixed slot: Start / Break / Resume. End is adjacent, visually secondary until active. No three simultaneously competing primary buttons.
- Right: preview keeps the same footprint when hidden. Analysis continues; "화면 숨김" is not "카메라 중지". State becomes a short icon+label with actionable error only when needed.
- Timeline keeps now +/-3 hours, current-hour label 18 px/700 and row height 1.5x. Other rows recede without making text unreadable. Do not highlight all six current-hour cells with a selection color.
- The approved fix now binds this chart to today's saved rows independently of planner navigation. It does NOT yet overlay current-session buckets. Either add a separately approved live-data merge with no double counting, or label it as saved-today history; never advertise a stored-only chart as live.

## 7. Planner: Plan Separately From Study

The reference is a usable paper planner: tasks on the left, actual study timetable on the right. Task completion does not create measured study time. No per-task Start buttons.

- Header: selected date, previous/next arrows, calendar, today shortcut, completion count. Calendar retains event creation and representative D-day selection.
- One shared column model: state 32 px / flexible title / start 84 px / end 84 px / duration 72 px / pin 32 px / delete 32 px. At minimum width, check measured text and split-entry fit before accepting these dimensions.
- Add row: title + all three optional time inputs + Add. All times start blank. Tab/Shift+Tab stay in the expected field order; Enter from title, hour, minute, or duration adds. Existing rows use Enter to commit, not add another task.
- Keep `__ : __` split hour/minute inputs. The two explicitly supplied values derive the third; pending derived text is gray until confirmation, then normal. Preserve calculation provenance across save/reload. Invalid time remains editable and visibly associated with its field.
- Proposed small clear-times icon clears only start/end/duration; it must not delete the title or task. This adjacent convenience action still needs scope approval.
- Saved rows are flat editable rows, 64-72 px high, not one floating card per cell. Actual study/focus time is a readable 12 px line under the task title; omit fake expected comparisons when duration is blank.
- Timetable: all 24 hours from the configured day boundary, 10-minute columns. Scroll within the timetable, not away from the date/input controls. Long planned titles clip to their segment, with full text in a tooltip; they cannot cross into another row.
- Planned outlines stay thin/dotted; completed planned outlines become thicker/solid. Actual study is the fill inside, independent of these outlines. Pending plans with no time never invent blocks.
- For actual measured focus, proposed color is a continuous red -> amber -> green interpolation (0 / 50 / 100%), with a numeric tooltip. This is visual mapping only; it does not change the focus classifier. Pure break is gray/empty, not red; unscored is hatched; measured 0% is red, not absent.
- Recurring edit/delete scope, last-task demo reappearance, schedule overlap warnings, reorder, and undo remain separate pending behavior work. Do not bundle them into the design rewrite.

## 8. Measurement: Setup, Not a Second Learning Page

- Useful preview about 60%; compact setup/state about 40%. Remove duplicate oversized session statistics that already belong to Learning.
- Show connection, currently actionable state, independent screen/writing calibration rows, cancel/retry, and optional validation. Complete is green with a check; incomplete is amber with a distinct icon, never color only.
- Full-monitor calibration remains separate and tracks the chosen monitor. Reuse the existing calibration-feedback design; do not substitute an attractive progress bar for actual per-target evidence.
- Writing calibration has no intermediate beeps. A failure must name what is insufficient and the next action. No unverified camera geometry or gaze-accuracy claim.
- Debug metrics remain an optional diagnostic surface, not the main user's dashboard.

## 9. Records: Understand a Day, Week, or Month

- One period toolbar: Daily / Weekly / Monthly, date range, previous/next, calendar. Week label is a real date range; month label is year+month.
- Daily: left time-composition ring and numeric rows; right full selected-day timetable. Ring slices use focus/non-focus/break/unscored over total recorded time. Center shows recorded time, not a misleading focus percentage. Focus ratio and measurement coverage are separate labeled values.
- Definitions remain explicit in data: visual focus = F/(F+N); coverage = (F+N)/(F+N+U). Total time and study time must not be silently renamed or conflated.
- Weekly: one combined plot, seven evenly spaced date+weekday labels, bars for study duration; genuine distinct measures as lines. Right: seven day summaries and period totals. No hard-coded highlighted weekday.
- Source finding: current `focus` and `pure` weekly series are the same ratio, and `away` is its complement. Three nearly redundant lines are not three useful metrics. Recommended follow-up: keep study-time bars and focus-rate line, add coverage only if approved. Do not reinterpret "pure" as another quantity just to fill a legend.
- Monthly: calendar/heatmap with visible dates and selected-day summary, navigable across months. No badges, rankings, or manufactured empty-day scores.
- Sessions/app usage move behind a compact details action when relevant. They are supporting information, not DB/debug summaries on the first screen.

## 10. Settings and Feedback

- Four readable groups: camera/measurement; study/Pomodoro; alerts/sound; record-day settings. Reuse existing persistent settings and explicit save action.
- Camera name/backend and refresh belong here, not the global header. Never hard-code Camo.
- Match field/dropdown/toggle geometry; show units next to numbers. Sound/volume test remains a clear command with local success/error feedback. Dark filled slider, light gray empty track stays unchanged.
- Show unsaved changes and local saved confirmation; no silent conversion to auto-save. Saving failure retains edits.
- Use one shared notice priority: blocking error > calibration progress > session transition > routine status. Do not duplicate the same event in header, camera overlay, banner, and toast.
- Mouse press feedback is immediate; pending work uses a busy state, then success/failure. Keyboard focus is always visible. Routine edits use inline feedback; reserve toasts for page-spanning events.

## 11. Motion Specification

- Hover: color/border only, 110 ms, OutCubic.
- Press: scale 1.00 -> 0.96, 80 ms; release 110 ms. Fixed layout/hit target; command executes immediately, not after animation.
- Tabs: outgoing/incoming opacity + at most 4 px translation, 180 ms. Rapid switching retargets; never queues transitions or unloads active engine state.
- Task add/delete: local height/opacity, 160 ms. Preserve input focus. Status icon: 140 ms crossfade; no list-wide replay.
- Pending derived time: color transition 110 ms on confirmation, no moving numbers.
- Pomodoro arc: 250 ms on the once-per-second value update. Timer digits change directly. No breathing pulse, flashing ring, or score wobble.
- Current-hour transition: 190 ms vertical easing when hour changes only; preserve row geometry and now emphasis. Ordinary incoming data updates do not restart it.
- Popover/dialog: opacity + 4 px translation, 150 ms; respects screen bounds and focus restoration. No blur, shader, or full-window screenshots for effects.
- Motion reduction must have an explicit implementation choice before rollout: use verified platform preference where supported, or approve one persisted setting. Do not guess a Qt API or silently add a settings schema field. Reduced motion removes transforms but retains static focus/status cues.
- Use native property animation for position/opacity/scale; avoid JS work per animation frame. Chart repaint rate follows new aggregate data, not the 30 FPS camera signal.

## 12. Risks and Mitigation

- Page extraction can reset session state: keep bridges/session/timer state above Loaders; assert cross-page continuity with synthetic observations.
- Fonts can clip on Windows/DPI: bundle known assets with notices after approval, test long Korean names and numeric widths at actual scales. Offscreen 1x capture is not native 150% proof.
- Changing controls can break Enter/Tab and inline calculation: preserve existing ClockEntry API and regression tests before styling. Do not infer DB policy from a checkbox icon.
- Planner date and study-day boundary can diverge: keep current definitions explicit; selected planning date must never override Learning's today data.
- Motion can increase latency/camera drops: avoid layered blur/full-window Canvas; benchmark UI cadence separately from analysis when hardware becomes available. No camera test now.
- Color-only charts are inaccessible: tooltips give numeric time/score; outlines and hatch separate plan, completion, break, and unscored. Missing data stays missing.
- Source tree is already dirty: no unrelated cleanup, dependency upgrade, EXE replacement, commit, or push. Save design candidates outside product QML until approved.

## 13. Implementation Order After Approval

1. Approve composition/type/palette/motion and identify behavior choices that stay deferred. Verify two static layouts first.
2. Add minimal shared tokens and local font/icon assets; restyle shared input/buttons/navigation without changing bridges. Verify component states, focus, contrast, licenses.
3. Learning + Planner together: stable timer/actions, one empty state, aligned inline edit grid, readable timetables. Verify existing behavior tests and new targeted layout checks.
4. Measurement + Records + Settings: same system, page-specific hierarchy. Resolve redundant weekly-series semantics only after approval.
5. Motion last: interrupted transitions, reduced motion, no focus loss or session reset. Verify start/break/end/calibration-cancel and rapid page changes.
6. Camera and real DPI/performance acceptance later, only when available. EXE rebuild is a separate requested step, never automatic.

## 14. Acceptance

- Capture all five routes and daily/weekly/monthly records at 1024x680, 1280x720, and 1440x900. No clipped controls, overlapping labels, or nested-page cards.
- Learning has no page scrollbar; actions stay visible. Hiding preview changes no column width/height and does not stop analysis.
- Every input/button has normal/hover/pressed/focus/disabled/pending/error states. Check readable Korean text and long task/D-day titles.
- Add a title-only plan with Enter; add from both clock subfields; Tab/Shift+Tab visit every field; invalid 25:00/12:60 stays correctable. Existing time provenance and deletion remain intact.
- Keep final elapsed time after end; next start resets; today's accumulated total persists and saved/live handoff does not double count.
- Planner/record navigation cannot change today's learning chart. All24 planner hours remain available. Measured0%, break, unscored, and no activity are distinct.
- A static screenshot is not proof of animation, native DPI, sound, packaged startup, or camera stability. Record these as verified/unverified separately.

Current proposal verification: both static pages rendered at 1280x720 and 1024x680 and were visually inspected. Corrected missing symbol fallback and the current-hour font shorthand in the proposal only. Motion, proposed Pretendard/Lucide assets, native DPI, and hardware performance remain unverified.

## 15. Sources

- [Pretendard](https://github.com/orioncactus/pretendard) and [SIL OFL license](https://github.com/orioncactus/pretendard/blob/main/LICENSE): proposed local Korean/Latin font and redistribution conditions.
- [Qt QML font](https://doc.qt.io/qt-6/qml-font.html): OpenType features available since Qt6.6.
- [Qt Quick performance](https://doc.qt.io/qt-6/qtquick-performance.html): native property animation and avoiding expensive per-frame work. Check installed Qt6.11.1 before using newer documentation APIs.
- [Lucide license](https://lucide.dev/license): applicable ISC and Feather-derived MIT notices.

## 16. Functional Study View: 2026-10-07

Implemented before the global visual redesign:

- One Learning route with ready / study / break / result states. A successful start enters Learning; a rejected start goes to Measurement. Both free study and Pomodoro use the existing session and clock, not another timer.
- Setup controls disappear during study. Today tasks, the current task, today's accumulated study, current-session study, measured focus time, date/time, and optional camera preview remain available. Task selection is optional; the existing three-state task control is retained.
- Study includes focus, non-focus, and unscored active time; break is excluded. Focus time is measured F only. End retains the final session value; the next start resets that value without clearing today's total.
- One primary start / break / resume action and one end action. Pomodoro break-pause, break-resume, and waiting-next labels describe the existing controller action. Phase progress uses the current controller configuration and does not reset on manual resume.
- Preview hiding keeps its footprint and does not reopen or stop capture. Unrelated settings saves cannot reset an active Pomodoro display; changed defaults are applied after ending. Ready-view duration choices are persisted and loaded before starting.
- The learning feedback uses the status strip instead of a toast over the controls. Rest text has a reserved slot; the Pomodoro ring does not shrink merely because rest text appears. Camera failure remains visible when preview is hidden.
- Fixed a same-timestamp manual break boundary without accepting old or duplicate camera-state updates. No classifier, calibration, DB schema, task-time attribution, or absence-policy change.
- The rolling chart still shows saved daily history. Its title no longer promises a live-session merge. Adding a live overlay remains separate work.

Validation: 38 scoped tests passed, including real QML button clicks, tab navigation, both modes, manual/automatic breaks, waiting-next, restart, settings, duplicate task titles, unavailable analysis, and time regressions. Learning study/break/result captures at 1280x720 and 1024x680 were inspected; capture/layout tests use temporary DB/settings and a synthetic camera image. Example: [free study](captures/active-study-2026-10-07/free-study-1024x680.png), [Pomodoro break](captures/active-study-2026-10-07/pomodoro-break-1024x680.png).

Not verified here: real camera/gaze accuracy, side-mounted camera coverage, native DPI/performance, packaged EXE, or sound. No build or commit. Global typography/icons/palette/motion and remaining page redesigns are still pending.

