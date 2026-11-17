# V3 Design Approval: Study Workspace

> Documentation reconciliation (2026-11-16): Historical composition proposal; retain contracts, not obsolete implementation status. [Documentation map](../../docs/README.md).

Date: 2026-10-08
Status: awaiting user approval. No production UI changes, build, commit, or DB/settings writes.

This is a new composition, not a repaint of the existing three-card layout.
It supersedes the earlier Clear Desk composition for this approval discussion.

## 1. Intent And Boundaries

- Bright, quiet, precise desktop study tool. No marketing screen, illustrations, glass, decorative gradients, or animated ornaments.
- Learning before start is about today's plans and choosing a study mode.
- Active Learning is about the current task, study time, and one primary action.
- Planner separates intended work from measured activity. No per-task start button or forced subject taxonomy.
- Keep Python/PySide6/QML. A web migration is unnecessary for the proposed motion and adds runtime/packaging boundaries.
- A color cannot be promised to improve concentration. The practical goals are legibility, restrained motion, less competing information, and predictable controls.
- Mockups use fictional, in-memory data. Closing the preview discards edits. They do not connect to ONF, a camera, a DB, audio, or the executable.

## 2. New Composition

Shared shell:
- Replace the horizontal tab slab with an 80 px icon-and-label navigation rail.
- Retain the existing five routes. No sixth home/dashboard route.
- Route heading, date/time, and optional user-chosen D-day share one quiet header.
- D-day number/title are both 17 px, same color, vertically aligned. No chosen event means no badge. Long titles elide with a tooltip in rollout.
- White workspace, structural dividers, no page-sized cards or nested cards.
- Default 1280x720, minimum 1024x680. Also review 1440x900.
- Main actions never sit behind a page scrollbar. Dense task lists may scroll locally.

Learning:
- Two regions, not the old left-task / middle-timer / right-monitor card trio.
- Broad main region: current task, study mode, dominant timer, actions, compact status, today's editable/selectable agenda.
- Narrow supporting region: fixed 16:9 preview footprint, compact measurement state, rolling seven-hour actual/plan timeline.
- During study, mode setup is replaced with a small mode label. Ending reveals mode controls again.
- Free study emphasizes today's accumulated study. Current-session study and measured focus are smaller, explicitly labeled values.
- Pomodoro uses a large, stationary ring and remaining phase time. Today's study remains a secondary value.
- Break has remaining rest time and a resume action; the study clock remains paused.
- End retains the final current-session time. Next start resets the current session, not today's accumulation.
- No selected task is a valid free-study state, with one label only.
- Camera hide/show changes neither the reserved footprint nor analysis behavior. Actual video uses aspect-fit/letterboxing, not distortion/cropping.
- Current-hour number is 22 px/bold; its row is 1.55x normal. Other actual fills are softened, not their text. No six-cell focus outline.

Planner:
- Date/arrows/calendar above a single flat plan list.
- Add row: title plus optional start, end, duration, small clear-time icon, plus action.
- All three time fields remain editable. Hour and minute are separate subfields.
- Enter from title/hour/minute/duration submits. Tab/Shift+Tab retain logical field order.
- Two explicit valid values produce the third in muted text, then existing confirmation behavior restores normal text.
- Preserve existing time provenance/calculation rules. Do not infer scheduling behavior from styling.
- Each item: three-state status, editable title, editable time fields, pin, delete.
- Desktop rows are 68 px. At narrow widths, fields wrap under the title instead of shrinking/colliding.
- Timetable is an independent 24-hour view of measured data and planned outlines.
- Planned outline: thin dashed. Completed plan: solid. Completion is not proof of actual study.
- Delete keeps confirmation; recurrence/edit/delete scope is not redesigned silently.

Measurement:
- Wide camera surface and unframed setup/status region.
- Screen and writing calibration are independent rows with completed/missing/busy/error states.
- The row itself must expose progress, cancellation, retry, and actionable failure feedback.
- Preserve separate full-monitor screen calibration. Do not relocate targets into the small preview.
- Optional validation remains opt-in. Writing keeps its existing no-intermediate-beep requirement.
- No fixed camera-center face oval. Only useful stored-baseline/current measurements belong in overlays.
- Developer measurements stay out of the default view.

Records:
- One period/date bar with arrows/calendar. Daily, weekly, monthly are one route.
- Daily: study/focus/ratio/coverage overview, a time-composition ring, and the entire selected study day.
- Ring slices divide ALL recorded time, including breaks and unscored time. Its percentages are NOT the focus-rate formula.
- Weekly candidate: study-time bars plus one focus-rate line, separate axes, all seven date/weekday labels, and a right-side daily total breakdown.
- This series choice requires approval: focus rate and a duplicate pure-study ratio should not be plotted twice as distinct facts.
- Monthly: duration-based calendar intensity, selected-day outline, average/best-day context. Selection must not corrupt heat intensity.
- User records/manual additions/allocations and app usage remain available behind compact actions. No DB/debug summary as the main dashboard.
- Duration-only manual records have no invented time position or focus score. Allocation never increases total study.

Settings:
- Camera/measurement, study, alerts, records are lightweight sections within Settings.
- Save stays reachable. Preserve explicit save and unsaved-edit behavior; do not introduce auto-save.
- Shared white inputs, clear arrow menus, readable steppers, and stateful toggles.
- Volume uses dark filled track, light-gray remainder, and synchronized numeric input.
- Playback/volume test requires actual audio verification after implementation; the mockup does not play sound.
- Camera selection remains automatic/selectable, never Camo-only.
- Settings/detail content may scroll; Learning does not get a page scrollbar.

## 3. Color Tokens

| Role | Value | Use |
|---|---|---|
| Workspace | #FFFFFF | Main study surface |
| Rail | #F6F8F8 | Navigation separation |
| Recessed | #EFF3F3 | Preview/inactive tool surfaces |
| Ink | #223036 | Primary text |
| Muted | #66767D | Secondary text, not tiny pale gray |
| Divider | #DCE3E6 | Structural lines |
| Action | #137B76 | Main command, focus, selected route |
| Selection | #EAF5F2 | Local selected row |
| Success | #16834B | Confirmed state, not every positive number |
| Warning | #855C12 | Missing/setup warning |
| Danger | #C3424E | Errors/destructive confirmation |
| Focus low/mid/high | #E95D69 / #EBB838 / #24AD6E | Continuous actual-focus scale |
| Break | #BFCBD0 | Neutral rest |
| Unscored | #E3E8EA + #87969D hatch | Distinct from 0% and rest |

Calculated white-background contrast:
- Ink: 13.60:1.
- Muted body text: 4.72:1.
- White on action: 5.09:1.
- Danger text: 4.99:1.
Chart fills are data encodings, not text. Numeric tooltips and outline/hatch distinctions remain necessary.

No purple/blue gradient theme, cream/brown theme, bokeh, glow, or giant colored cards.
Teal is an action color, not the whole screen.

## 4. Type And Geometry

Locally registered Pretendard, release v1.3.9, weights 400/500/600/700.
Fallback: Malgun Gothic, then Segoe UI. Bundled assets are approval-folder-only for now.

| Element | Size / weight |
|---|---|
| Route heading | 25 px / 700 |
| Current task | 27 px / 600, stable elision or two-line slot |
| Section heading | 15-22 px / 600 |
| Body/input | 14 px / 400-500 |
| Supporting label | 12-13 px / 400 |
| D-day number and title | 17 px / 600 |
| Free-study main timer | 70 px / 600 |
| Pomodoro digits | 48 px / 600 |
| Current hour | 22 px / 700 |

- Tabular numerals for timers and comparable values. No negative letter spacing or viewport-scaled font size.
- Main buttons: 44 px tall, at least 88 px wide. Icon actions: 40x40; dense state controls: 36x36 in preview, 40x40 preferred for rollout.
- Lucide icons: 18-21 px; stable hit target; named hover tooltip and accessible name.
- Controls radius 6 px; preview/dialog radius at most 8 px. No page shadows. Popup shadow only if needed.
- 4/8/12/16/24/32 spacing scale, optical icon alignment, stable field widths.
- Input/focus outline: 2 px teal. Invalid input: error outline plus an inline reason; raw text remains correctable.
- Placeholder is not the only field label. Compact planner still identifies start/end/duration.
- No blind widening of the main window to hide overflow. Use intrinsic sizes and local wrapping/scrolling.

## 5. Feedback And Motion

| Interaction | Proposed response |
|---|---|
| Hover | Color/border change, 100-110 ms |
| Press | Background scale 1 to 0.97, 70 ms |
| Release | Return in 110 ms, OutCubic |
| Command | Runs on normal clicked/accepted event, never waits for animation |
| Route change | 55 ms outgoing + 125 ms incoming, opacity and max 4 px movement |
| Busy command | Same button becomes pending, duplicate click disabled, layout unchanged |
| Success/failure | Local durable label or inline error; no repeated global toast |
| Toggle | Thumb movement 120 ms |
| Task status | Small icon/color change, 120-140 ms |
| Add/remove row | Local height/opacity, 160 ms; do not replay entire list |
| Derived time | Muted proposed value, color confirmation 110 ms; no rolling digits |
| Pomodoro | Arc interpolation 250 ms on aggregate updates; digits change directly |
| Hour rollover | 190 ms reflow/scroll only at hour change |
| Popup/dialog | 150 ms opacity + max 4 px; bounds/focus restoration |
| Camera hide/show | Same aspect-ratio footprint; short fade only |
| Reduced motion | No positional/scale motion; static focus and state feedback remain |

- Learning must stay still while reading/studying. No breathing timer, blinking score, particle celebration, or animated graph on each camera frame.
- Rapid navigation retargets; no queued route transitions or reset of the analysis/session.
- One message owner: blocking error > calibration > session feedback > routine status. Do not show the same notice in header, camera, panel, and toast.
- Live chart updates use aggregate data cadence, not camera FPS.
- Reduced-motion rollout needs a verified platform preference or separately approved persisted setting. The preview does not add a product setting.

## 6. Existing Contracts That Must Not Change

- Planned times recommend only. They never automatically reassign measured study.
- Direct selection/switch closes attribution interval only; it does not restart the session.
- Complete/defer clears attribution without stopping study.
- Study = focused + non-focused + unscored active time; break excluded.
- Measured focus time is F only. Focus rate = F / (F + N); coverage = (F + N) / (F + N + U).
- Post-session allocation does not add study. Separate manual duration adds once and is unscored.
- Saved/live timeline handoff does not duplicate duration.
- Camera hide is not camera stop. Calibration/start requirements remain unchanged.
- Root session/bridge objects stay above page components/loaders.
- Original EXE, DB, settings, logs, models, and working launchers are preserved.
- No classifier, gaze thresholds, DB schema, recurrence policy, demo policy, build, or packaging change in this design task.

## 7. Sample Data Consistency

All dates and totals in the preview are fictional:
- Selected study day: 2026-10-08, starts at 04:00.
- D-day: selected example event on 2026-11-07, D-30.
- Today: F=114 min, N=16 min, U=5 min, break=20 min.
- Study=135 min; whole recorded=155 min; focus rate=88%, coverage=96% after rounding.
- Daily ring: 74% F, 10% N, 3% U, 13% break; rounded slices sum to 100%.
- Seven study-day minutes: 95,120,0,165,135,0,0. Sum 515 min (8h35m); no future activity.
- October 1-8 minutes: 80,120,90,95,120,0,165,135. Sum 805 min (13h25m), 7 active days; mean 1h55m.
- Free-study session example: 12:45-13:25, 35 active minutes, 5 rest; focus=24 min.
- Pomodoro example: first work 12:50-13:15, break 13:15-13:20, second work through 13:25. Second phase has 20:00 left.
- Sample edits affect memory only. Calendar navigation and per-row time editing are visual sketches, not claims of completed app functionality.

## 8. Approval And Rollout

Approval requested for:
1. New rail + two-region Learning + flat planner composition.
2. White/neutral-gray/teal system, Pretendard, icon/control dimensions.
3. Daily ring meaning, weekly series selection, monthly duration intensity.
4. Feedback/motion rules, with motion delivered after functional layout.

Implementation after approval:
1. Shared tokens/fonts/icons/controls; verify license notices, contrast, focus, long Korean text.
2. Learning + Planner; retain current bridges, time-input APIs, key order, session attribution.
3. Measurement + Records + Settings; preserve full-screen calibration and save boundaries.
4. Motion last; verify interruption, reduced motion, focus retention, no clock/engine reset.
5. Separate hardware/DPI/performance validation when available. EXE build only when explicitly requested.

Success criteria:
- All five routes render at the three stated sizes; no fixed action clipping, overlapping text, or nested section cards.
- Learning has no page scrollbar. Preview toggle retains size. Large plan lists stay manageable without hiding actions.
- Existing scoped behavior tests remain green. Add targeted QML checks for affected layout/control states only.
- Enter/Tab, gray calculation confirmation, invalid-time recovery, delete confirmation, recurring items, and manual/allocated records keep their existing semantics.
- Save pending/success/error, unavailable camera, calibration errors, and empty agenda each have one visible useful response.
- Native 125/150% DPI, actual audio, camera cadence, and packaged startup are separate acceptance items, not proven by offscreen screenshots.

## 9. Prototype Verification

See captures/verification.json for the current captured checks.
Thirty state/page images were rendered across 1024x680,1280x720,1440x900.
The capture driver checks nonblank rendering, main action bounds, camera footprint, prototype start/rest/end, title-only Enter, Tab between clock subfields, two-value calculation preview, Enter from a minute field, save pending/success, and navigation settling.
It also captures REAL native page-transition frames into a GIF.

Not verified: production integration, per-row edit calculations, real camera, sound, native DPI, hardware smoothness, EXE.
The launcher opens a standalone native QML preview, not a replacement app.

## 10. References

- [Pretendard](https://github.com/orioncactus/pretendard), v1.3.9, SIL OFL; font license included.
- [Lucide](https://lucide.dev/guide/static), commit b56741cf30c08fc7248bf41ddd3a261367aa9579; icon license included.
- [Qt Quick performance](https://doc.qt.io/qt-6/qtquick-performance.html); installed runtime tested here is Qt6.11.1. Newer documentation is not proof of API compatibility.

