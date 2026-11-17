# ONF Native QML UI Application Plan

> Documentation reconciliation (2026-11-16): Current detailed visual rollout. Phase A is implemented; remaining page-specific phases are not marked complete. Consolidated status is linked below. [Documentation map](../docs/README.md).

Date: 2026-11-16
Status: user approved. Phase A (common controls and Study) implemented; awaiting visual acceptance before the remaining page redesigns.
Authority: current user requirements and lucian-catalog-audit-2026-11-16.md.
Scope: native QML presentation and existing interaction clarity, not 45 new features.

## 1. Boundaries

- Keep Python engine, QML application, SUIT font files, existing records/settings and app launch paths.
- No React/WebView migration, EXE build, commit, cleanup or camera test in this plan.
- Keep five pages: Study, Measurement, Planner, Records, Settings.
- No slogans, brand hero, greetings, motivational filler, decorative summaries or fake sample records in normal use.
- No changes to focus policy, gaze/head-pose calibration algorithm, scoring denominators or duration accounting.
- Planned times never assign measured time or switch the recorded task automatically.
- Optional enhancements from the catalog audit are not approved by this plan.
- Lucian is interaction/design reference. Native adaptations are not exact HTML/CSS ports.
- Preserve MIT attribution if actual Lucian source is translated/copied.

## 2. Observed Implementation Owners

- Main.qml owns navigation, session presentation and current-task selection.
- LearningPage.qml already has preparation/study/break/result views and a shared tools popup.
- StudyStyle.qml + StudyText.qml provide SUIT and neutral/teal styling for the study family.
- Theme.qml + ActionButton.qml provide a different blue-oriented style for other page families.
- StudyButton.qml already has press, hover and focus feedback. Reuse, do not replace with a second button engine.
- PlannerPage.qml preserves active input/cursor across backend refresh and queues edits until Tab completes.
- ClockEntry.qml owns independent hour/minute fields. Do not replace with OTP or wheel inputs.
- Existing chart/calendar owners: FocusBars, PomodoroRing, DailyPlannerTimeline, FullDayTimeline, WeeklyRecordCharts, MonthlyHeatmap, PlannerCalendarPopup.
- AppBridge.deletePlannerTask is a direct delete + refresh; no task restore API was found in the inspected bridge.
- AppBridge.saveSettings saves before settingsChanged. Settings UI must use actual completion/failure, not a simulated timer.

## 3. Common Visual System

| Property | Proposed rule |
| --- | --- |
| Typeface | Existing SUIT Regular / Medium / SemiBold; no replacement or font-picker feature. |
| Base | White surfaces, very light neutral page background; no tinted card for every section. |
| Main ink | #20262D |
| Secondary ink | #626B75; keep readable, not low-opacity fine print. |
| Divider | #E1E6E9 |
| Primary action | #137B76; light selection #EAF5F2 |
| State colors | Green success, amber warning, red error; icon/text accompanies color. |
| Type | Body 16px, controls 15-16px, secondary 13-14px, page title 22-24px. |
| Study timer | General primary time 72-80px, Pomodoro time 60-64px; stable tabular digits. |
| Dimensions | Primary buttons 42-44px high, compact fields 36-40px, icon hit areas at least 36px. |
| Shape | 6-8px corners for ordinary controls/panels; circles only for semantic rings/status controls. |
| Spacing | 8px base, 16px local gaps, 24px section gaps; 24-32px outer padding when space permits. |
| Elevation | Thin separators for normal sections, subtle shadow only for floating popup/dialog. |

Implementation: assign one owner per token. Map existing Theme and StudyStyle consumers to the same approved values without renaming public properties or changing unrelated controllers. Keep ActionButton compatibility while aligning its appearance; do not mass-rewrite all call sites.

References: #013, #018, #031, #048, #076, #118, #119, #120, #124, #303, #373.

## 4. Application Shell

### Placement

- Fixed top navigation, approximately 64px high: Study / Measurement / Planner / Records / Settings on the left.
- Current page uses a persistent underline. Hover and keyboard focus remain distinct from selected state.
- Current time and user-selected representative D-day stay compact on the right; no new brand name or subtitle.
- D-day and event name both 17px, same color and vertically centered. No event means no leftover badge.
- Study controls stay inside the fixed study action area, not inside a scrolling list.
- Do not add an expanding sidebar, hidden hamburger menu or a new Home page.

### Behavior

- Change only selected-page presentation. Navigation cannot start, reset or end a session.
- Popups fit inside the active window, Escape closes, focus returns to the invoking control.
- Main window resizing cannot destroy editing state or selected task.

References: #048, #076, #077, #373.

Owners: Main.qml, StudyStyle.qml, Theme.qml, shared control components.

## 5. Study Page

### Preparation

- Main center: compact General / Pomodoro segments, not large marketing cards.
- General: selected task or one short task-selection action, readiness state and Start.
- Pomodoro: focus time, short break and cycle count visible; long break/automatic-phase options grouped below in a compact secondary section.
- Switching modes reveals only the appropriate settings and preserves typed values.
- Readiness text next to Start is actionable: camera/setup issue opens Measurement.
- No forced task selection if the existing session policy allows studying without a task.

### Active General Study

- Main center: today's study total is the largest figure.
- Focus time is directly below, smaller. Current-session time has a separate smaller label/value.
- One short measurement status; no large focus-percentage dashboard.
- Right: a restrained Today Tasks rail, approximately 240-280px, with concise rows.
- Task row: title, optional planned time, independent status icon. Selected recording task has a clear thin accent.
- Current task and scheduled recommendation must not look identical. Recommendation never changes recording attribution.
- General study does not get a new 24-hour dial or Pomodoro-style decorative ring.

### Active Pomodoro

- Keep the same page structure and task rail.
- Replace the general main figure with the existing single Pomodoro ring: phase, remaining time, cycle number.
- Today's study/focus totals remain secondary below the ring.
- General learning remains first-class; do not turn the whole product into a Pomodoro-only UI.
- Ring dimensions fit within the existing 680px minimum window height without pushing controls offscreen.

### Fixed Actions and Auxiliary Tools

- Pause/Resume and End are fixed below the main timer.
- During a request: immediate press feedback, prevent duplicate action, then reflect actual backend state.
- Camera/timeline remain in the existing auxiliary tools flow unless a separate placement is approved.
- Camera preview on/off preserves its allocated dimensions; no timer/page resize when hidden.
- A study timeline, wherever shown, retains the current-time surrounding window and current-hour emphasis. Record views do not inherit that window.

### Break and Result

- Break shows remaining break time with a calm gray treatment and clear Resume/End.
- Active study duration stops according to existing controller semantics; no second UI-owned timer.
- End preserves the final session duration. The next new session begins at zero.
- Result has exact totals and clear next actions, no confetti or invented assessment.
- Returning from another page restores the same study/break/result state.

References: #007, #014, #039, #047, #099, #295.
Owner: LearningPage.qml, existing PomodoroRing and study components; Main.qml only for presentation bindings.

## 6. Measurement Page and Calibration

### Placement

- Left: stable-aspect camera preview, existing hide/show control.
- Right top: compact current status and one actionable explanation when intervention is needed.
- Right middle: Screen Setup and Writing Setup as two separate vertically stacked controls.
- Each setup control includes its own completed/pending state and its own real collection progress.
- Separate Gaze Verification button remains optional, below setup controls.
- Technical numerical validation details remain behind explicit details, not the default task.

### Full-Screen Setup Window

- Keep the real full-monitor target flow, not a target positioned relative to the small camera preview.
- Stage label near the target; important instruction appears before the target when required.
- Use actual waiting / accepting / unstable / completed / failed states.
- Yellow: not accepting or waiting for valid stable samples.
- Green: stable sample acceptance in the current stage, not proof that the user looked in the requested direction.
- Actual accepted-sample progress may fill the setup control; no clock-based pretend progress.
- Stationary calibration targets must not move/scale due to hover, page transition or color animation.
- Retain existing timing and audio policy. Do not reintroduce confusing middle writing alarms.
- Error text states a usable cause/action when available, not just a generic failure.
- No fake compass, radar, model accuracy percentage or new head-position boundary.

References: #036, #042, #082, #083, #090, #198, #284.
Owners: MeasurementPage.qml, CalibrationButton.qml, ScreenCalibrationWindow.qml.
Boundary: no calibration algorithm or focus threshold change.

## 7. Planner Page

### Placement

- Header: Planner title, selected date, previous/next arrows, calendar action and existing D-day entry point.
- Main left 65-70%: composer followed by editable task rows.
- Main right 30-35%: actual full-learning-day timeline, separate from the task list.
- The task list may scroll if needed. Date controls and composer do not disappear during basic entry.
- At minimum width, keep independent fields usable; let list/detail content scroll rather than clipping inputs.

### Composer

- Title plus optional Start / End / Estimated fields; no default 30 minutes or required schedule.
- Independent hour/minute inputs display __ : __ when blank.
- Tab traverses the title and actual editable time cells in a predictable order.
- Enter adds from title or any time/duration cell, except while Korean IME composition is active.
- Last two explicitly entered fields derive the third. Derived text is gray until committed.
- Invalid 24/60-style input is recoverable without locking, clearing the user's other values or stealing unrelated focus.

### Rows

- Left status icon cycles blank / completed / deferred; title remains editable in place.
- Start, end and estimated values remain directly editable without a separate edit mode.
- Right compact pin, clear-time and X actions, with tooltips and keyboard focus.
- Row selection, completion, deferral and daily recurrence are different states.
- Editing one row must not remount all input rows, auto-sort the list or lose the caret.
- Do not add task tags, notes, priorities, Kanban columns or drag interactions in this pass.

### Timeline

- Measured study colors use real focus data and the established red/yellow/green mapping.
- Planned intervals: thin dashed outline. Completed planned intervals: stronger solid outline.
- Plan text/outlines must remain readable over actual recorded colors.
- Break gray/empty; unmeasured distinct; blank future time is not non-focus.
- Plan edits/deletion cannot rewrite actual study history or switch task attribution.

### Deletion Constraint

- Keep visible X. A genuine Undo requires bridge/database restore semantics.
- Do not fake Undo by putting a row back only in a QML model.
- Implement restore only after separate approval of preservation rules, task IDs and fixed-schedule relationships.

References: #012, #014, #030, #033, #071, #133, #143, #190, #244.
Owners: PlannerPage.qml, ClockEntry.qml, PlannerCalendarPopup.qml, DailyPlannerTimeline.qml.

## 8. Records Page

### Common Header

- Day / Week / Month segments, previous/next period arrows and an unambiguous selected-period label.
- Day: complete date. Week: start and end dates. Month: year and month.
- Existing learning-day boundary setting stays separate from date navigation.
- Preserve selection when opening/closing details. No technical DB summary by default.

### Daily

- Top left: simple time-composition donut with exact category duration rows.
- The donut visualizes disjoint categories under existing metric definitions; do not add overlapping study and focus totals as separate additive slices.
- Focus ratio and coverage remain separate labelled metrics. Hover highlights cannot change their denominators.
- Top right: full-day hourly study overview.
- Below: complete learning-day timeline and user-facing record summary.
- Real app usage, if shown, uses existing foreground-duration data and does not label programs automatically as productive/distracting.
- The page can scroll; do not shrink graphs/text into illegibility just to avoid scroll.

### Weekly

- Left approximately 70%: existing combined comparison chart.
- Study duration uses bars; existing comparable time metrics use lines, with explicit unit-labelled axes.
- Percentage metrics require a clearly labelled percent axis or a separate selected metric, never a shared unlabeled minutes scale.
- Date + weekday under all seven slots. Empty days remain in chronological position.
- Right approximately 30%: selected-day detail when selected, otherwise whole-week totals.
- One crosshair/readout links the date, graph points and exact values.
- No sample curves, invented interpolation through missing data or animated value ramp from zero.

### Monthly

- Full calendar-based heatmap with actual month lengths, weekday alignment and selected year/month.
- Heatmap intensity represents an explicitly named metric, proposed study duration. Do not silently mix it with focus-ratio colors.
- Selecting a date reveals its exact figures and existing daily record route.
- Secondary details open a bounded panel; do not replace the whole page with a decorative card transition.

References: #047, #095, #096, #097, #151, #200, #238, #273, #288, #400.
Owners: RecordsPage.qml, WeeklyRecordCharts.qml, MonthlyHeatmap.qml, FullDayTimeline.qml, StudyRecordDialog.qml.

## 9. Settings Page

### Placement

- Compact section navigation on the left, settings content on the right.
- Sections: Camera and Measurement / Alerts and Sound / Pomodoro Defaults.
- Preserve existing controls and actual stored-setting keys. Do not introduce new settings merely because a reference includes them.
- Scrolling is allowed. Save action and truthful dirty/result state stay accessible.

### Controls

- Camera: real device selector and reconnect action; no Camo-only restriction or simulated radar.
- Sound: enable toggle, alert duration, sound selection, volume slider + numeric value, real Test action.
- Slider fill is the active dark/ink portion; remainder light gray. Accent may mark focus, not invert fill meaning.
- Conditional controls stay visibly grouped; disabling an option does not reset its saved values.
- Secondary tuning can be disclosed without hiding essential camera or alert choices.
- Pomodoro defaults remain defaults; session preparation can adjust the next session under existing policy.

### Save Feedback

- Dirty shows unsaved state only for the existing explicit-save workflow.
- Save completion follows the backend save; saving/saved/error cannot be timed animation fiction.
- Persistent write errors remain actionable. Do not add a second toast containing the same message.
- Any missing failure acknowledgement requires a separately reviewed bridge change, not an optimistic visual claim.

References: #013, #017, #018, #023, #031, #192, #244, #250, #275, #355.
Owners: SettingsPage.qml, existing number/stepper/switch/button components.

## 10. Motion and Feedback Specification

| Interaction | Proposal | Must not happen |
| --- | --- | --- |
| Pointer down | Immediate tone change; optional tiny background compression | Delay action until an animation finishes |
| Hover/focus | 100-140ms color/border; visible keyboard focus | Move button/text away from pointer |
| Segment selection | 160-200ms indicator translation | Move all page content or reset input |
| Page change | At most 120-180ms opacity transition | Full-screen curtain, blur or delayed interaction |
| Disclosure/details | 180-220ms bounded reveal; retain scroll position | Push fixed study actions offscreen |
| Task state | Short icon/check/styling transition | Confetti, auto-completion, list reordering |
| Timer | Instant text update, stable digit widths | Per-second flip, odometer or pulse |
| Pomodoro arc | Follow real remaining time; no interpolation across pause/end | Independent UI countdown |
| Current-time timeline row | Interruptible geometry/emphasis transition when actual hour changes | Scroll to another date or recenter record views |
| Calibration | Short color transition only | Shift target geometry or fabricate directional correctness |
| Success | Compact local state, once actual operation succeeds | Duplicate button/banner/toast messages |
| Error | Persistent inline state with relevant recovery | Auto-dismiss data-loss errors |

All motion stops with a shared reduced-motion path. Do not add a new settings option without approval; at minimum support verification with motion disabled. Catalog timings are reference evidence, not a requirement to preserve 750ms animations in a native study app.

## 11. Delivery Order and Acceptance Gates

1. Common tokens and controls.
   - Keep SUIT. Harmonize Theme/StudyStyle and both button families without changing actions.
   - Verify hover/down/focus/disabled/busy/error; labels do not move or clip.
2. Study first, including preparation, general, Pomodoro, break and result.
   - Review all states with a test backend; verify page return, fixed controls and no hidden-preview layout shift.
   - Approve rendered native screenshots before spreading the design to other pages.
3. Planner and calendar.
   - Focused tests for Enter/Tab/IME, optional clocks, derived value commit, invalid recovery, status/selection/pin independence.
   - No schema change, restore action or new planner feature in this stage.
4. Records.
   - Daily full day, weekly combined plot + day/period summaries, monthly actual calendar.
   - Compare displayed numbers to existing backend output; preserve null/unmeasured states and denominators.
5. Settings and measurement presentation.
   - Verify actual saved values, audio-test call path and setup-feedback state transitions with fixtures.
   - Camera hardware/gaze accuracy and actual sound audibility are separate live acceptance steps.
6. Cross-page integration and visual pass.
   - Session continues unchanged during navigation; no duplicate notifications or independent timers.
   - Check 1024x680, 1280x720 and 1366x768. Actual Windows scaling 100/125/150% checked separately.
   - Capture every page plus active study/break/result, opened calendar, details and error states.
   - No EXE build/commit until explicitly requested.

## 12. Not Included Without Further Approval

- New search/suggestions/notes, tags, priorities, schedule dragging/painting, overlap policy.
- Delete/Undo database extension, version history, bulk editing or task restoration.
- Extra app-usage analytics, new study goals, streak/reward/achievement system.
- New keyboard-shortcut preferences, font picker, user motion/scale settings.
- Floating windows/PiP timer, notification center, mandatory onboarding, extra Home page.
- New camera/gaze/focus algorithms or automatic actual-time attribution.

## 13. Approval Request

The user approved implementation after reviewing this plan.
Phase A contains common controls/shell and the Study page, including preparation, general, Pomodoro, break and result.
Planner/Records/Settings/Measurement page-specific redesigns remain pending. Common tokens/button styling already reach those pages.
Any data/bridge enhancement, new feature or changed product behavior remains separately approval-gated.

## 14. Phase A Checkpoint

- Unified the existing neutral/teal token owners without removing either compatibility API; SUIT files/rendering unchanged.
- Persistent five-page navigation during study, compact preparation/tools controls, existing representative D-day.
- Non-overlapping main timer and 248px Today Tasks rail; selected task and status controls separate.
- Existing optional setup/mode fields and session handlers retained; current-session time is secondary.
- Real invalid-field feedback stays visible and does not overlap readiness or fixed actions.
- Restored keyboard focus after compact task status updates; Space can cycle successive states without affecting session time.
- Shared internal motion gate, immediate static feedback, no per-second digit animation.
- No camera/engine/database/recorder/settings-store changes, no restore API, no fake Undo, no EXE build or commit.
- Scope: StudyStyle.qml, Theme.qml, Main.qml, StudyButton.qml, ActionButton.qml, StudySwitch.qml, StudyNumberInput.qml, PomodoroRing.qml, LearningPage.qml and targeted study tests.
- Targeted suite: 34 tests; initial 33 passed, one expected-color assertion updated for approved contrast change and retested successfully.
- Qt offscreen scale 1.25 and 1.5: layout + preparation tests both passed at each scale.
- Viewports checked: 1024x680, 1280x720, 1366x768; captures under captures/native-study-2026-11-16/.
- New regression coverage: rail/main/action separation, status versus selection, repeated keyboard status changes, persistent validation feedback, motion-disabled interaction.
- Capture fixtures use temporary databases and synthetic observations; user records are not populated with demo data.
- This is native Qt offscreen rendering evidence, not a physical Windows display/camera/audio acceptance claim.
