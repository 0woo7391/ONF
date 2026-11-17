# Approved Study UI Integration

> Documentation reconciliation (2026-11-16): Historical integration checkpoint. Test counts below are from that checkpoint, not a current full-suite result. [Documentation map](../docs/README.md).

## Scope
- Applied the approved white / neutral / restrained teal study concept to the real QML app.
- Bundled SUIT fonts and Lucide icons with their licenses; no system installation.
- Kept measurement, planner, records, settings, and their existing backend contracts.
- No EXE build, new application, camera test, user-data migration, or commit.

## Completed
1. Preparation and mode selection: existing Pomodoro values and automatic transitions persist on start.
2. General study: primary daily study total; secondary measured daily focus total.
3. Pomodoro: primary 280px countdown ring; secondary daily totals.
4. Quiet compact tasks and a closed-by-default tasks / timeline / camera drawer.
5. Explicit task selection / deselection / completion / next; schedules only recommend.
6. Rest / resume / summary / return-to-preparation retain the real session and record clock.
7. Summary record shortcut reuses the existing records dialog and configured study-day boundary.
8. Short press / hover / switch / view transitions; action positions stay stable across rest / resume.

## Verification
- 90 focused tests passed; no QML load/binding errors in the integration checks.
- Native QML captures at 1280x720 and 1024x680; no camera access.
- Tests use temporary databases/settings and mocked hardware / controlled clocks.
- Covered live-to-saved totals, day boundaries, task attribution, repeated clicks, return during break,
  settings persistence, record editing, and tool-panel bounds.
- Core attention, calibration, analysis, session, storage files and original DB/settings hash-checked unchanged.
- Python compilation and existing launcher dependency check passed.
- Production launch: `start_onf.bat` or `python main.py`. Existing EXE remains unchanged.

Not verified: real camera / sound, native Windows DPI, packaged EXE.
Timeline keeps the existing ten-minute aggregation; break/unscored-only slots remain blank.
Planner / records / measurement / settings visual redesign remains outside this phase.

## Rendered App
Captures below use isolated test data, not the user's study records.

![General study](captures/study-integration-2026-10-15/approved-free-1280x720.png)
![Pomodoro](captures/study-integration-2026-10-15/approved-pomodoro-1280x720.png)
![Compact Pomodoro with timeline](captures/study-integration-2026-10-15/approved-pomodoro-timeline-1024x680.png)
![Pomodoro preparation](captures/study-integration-2026-10-15/ready-pomodoro-1024x680.png)
