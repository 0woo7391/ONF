# Study UI Approval - 2026-10-09

> Documentation reconciliation (2026-11-16): Retained approved study concept and historical fixture; current rollout/status is in the documentation map. [Documentation map](../../docs/README.md).

Status: approved concept. Learning-page production integration completed on 2026-10-15.
This folder remains the isolated approval prototype, not the application entry point.
Integration report: ../STUDY_UI_INTEGRATION_2026-10-15.md.

## Scope
- Focus checking and study records remain central in both modes.
- Six views: preparation, Pomodoro setup, general study, Pomodoro study,
  break, session summary.
- Only Learning is interactive. Other navigation labels show placement only.
- Fictional in-memory data. Camera/status/timeline are samples.
- No production services, settings, database, or EXE access.

## Reduced Information
- Preparation: mode, conditional interval settings, readiness, start.
- General study: large daily study clock, smaller daily focus clock, current task.
- Pomodoro: primary 280px interval ring with 64px remaining time; daily study
  and focus totals are secondary below it. No 24-hour clock or double ring.
- Both study modes: quiet 220px task list on the right; 14px titles/status icons,
  no cards, planned times, or progress counts. Up to five rows, then full-list access.
- Current task: explicit selection, complete, next. No automatic attribution.
- Tools: full task list, timeline, camera; closed by default, one tab at a time.
- Compact and full task lists share selection and completion/defer state.
- Expanded tools temporarily cover/replace the compact list, not the timer.
- Opening tools never moves the clock or changes window dimensions.
- The drawer leaves the clock, task actions, and bottom actions uncovered.
- Break: remaining time and resume/end; study and focus clocks freeze.
- Summary: session study, measured focus, break, measurement coverage.

## Appearance
- White workspace; neutral ink #20262D, secondary #626B75.
- Restrained teal #137B76 for selected controls and primary actions.
- SUIT: body 16px, secondary/task list 14px, current task 24px,
  general study clock 80px, Pomodoro remaining time 64px.
- No font sizes based on viewport width. Tabular timer digits.
- Lucide outline icons; buttons have named hover tooltips and focus outlines.
- Press 0.96 scale, hover 100ms, page entrance 180ms.
- Tool drawer opens in 180ms, closes in 140ms; footer stays in place.
- Timeline retains red/yellow/green focus fills, gray break, hatched unscored,
  dashed plans, solid completed plans. Other hours are subdued.

## Clock and Task Contracts
- Break excludes time from both study and focus clocks.
- End freezes session totals; next start resets session, retains daily totals.
- Returning to preparation preserves the current study/break.
- Task completion/defer does not stop study or assign planned time as actual.
- Recorded time may remain unallocated. Record dialog is a visual stub.
- Full Pomodoro-set completion waits for continue/end.

## Fixture
2026-10-09 13:25; D-29 refers to 2026-11-07.
Prior study 100m = focus 90m + non-focus 7m + unscored 3m.
Current session 12:45-13:25: study 35m + break 5m.
Session study = focus 24m + non-focus 9m + unscored 2m.
Daily study 135m; daily focus 114m; valid-time focus rate 88%.
Pomodoro: first 25m work, 5m break, then 10m work; round 2 has 15m left.
Timeline is a fixed snapshot, not a live camera-driven record.

## Verification
20 captures: six views, three tool tabs, and the Pomodoro tools overlay
at 1280x720 and 1024x680.
Native QML screenshots reviewed. Capture runner passed with no QML errors.
Checked start feedback, compact/full selection/completion/defer, panel bounds, fixed clock,
camera footprint, break/resume, return during break, end freeze, new session.
Three fonts loaded and captured on the same study view.
Motion GIFs use actual QML render frames.

Not verified: production integration, real camera/audio, native DPI, packaged EXE.
Fonts/icons have licenses in assets. No system font installation.

## Open
Double-click Open Preview.cmd. Ctrl+1 through Ctrl+6 switch sample scenes.
Use Learning tools to open the supporting tabs.
Gallery: GALLERY.md. Machine-readable checks: captures/verification.json.
