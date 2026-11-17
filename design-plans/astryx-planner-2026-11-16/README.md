# Isolated Astryx planner preview

> Documentation reconciliation (2026-11-16): Isolated reference experiment; no desktop runtime migration approved. [Documentation map](../../docs/README.md).

This is a React/Astryx design experiment, not the ONF application.
No database, camera, Python bridge, settings or EXE is used or modified.
All data is fictional, resets on reload, and uses 2026-11-16 as the demo day.
Actual study intervals are independent of planned tasks.

Run: `npm.cmd run dev`
Build: `npm.cmd run build`
Logic tests: `npm.cmd test`

Task status cycles pending, completed, deferred. Times are optional.
Two schedule values calculate the third on field commit.
The calendar changes the visible date. Repeated tasks are a UI preview only.
Astryx components provide buttons, text fields, calendar, popover and theme.
The font is SUIT; its license is included in public/fonts.
