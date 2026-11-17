# ONF

Windows study records and visual-attention estimation with Python and
PySide6 / Qt Quick (QML). General study is the base workflow; Pomodoro is an
optional mode. ONF estimates visual attention, not cognitive concentration.

## Checkout Status

Reviewed against the **local working tree on 2026-11-16**, including uncommitted
files. This does not certify GitHub main or the existing EXE.
Current branch: `refactor/v2-attention-engine`.
Prototype reference: `v0.1-prototype`.

## Run

Use Python 3.11 on Windows, from the repository root:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Or double-click `start_onf.bat`. To check launcher dependencies without
opening a camera: `.\start_onf.bat --check`.

`main.py` starts the QML app through `onf_v2/ui_qml/preview.py`.
`legacy_main.py` retains the old QWidget UI for comparison.
An existing `dist/ONF.exe` can be older than the source.

## Workflow

1. Settings: choose camera, screen-only or screen-and-writing mode; Save the form.
2. Measurement: collect the screen baseline with the full-screen guide.
   Collect the separate writing baseline when required.
3. Study: choose general study or configure Pomodoro, optionally select a task,
   then start. Rest/resume and end operate on the same session.
4. Planner: tasks, optional start/end/duration, completion/defer status,
   pinned schedules, calendar events and representative D-day.
5. Records: selected day/week/month, measured-time allocation and separate
   manually entered study.

Planned times are not measured study. Scheduled tasks recommend; explicit user
selection changes live attribution. Allocating measured time does not add to
session totals. Separate manual study adds time without inventing focus data.

Rest is excluded from study time. Ending retains the final session duration;
starting a new session resets that session's clock.

## Measurement Limits

- Both-eye horizontal/vertical features and normalized lid opening are used.
- Current head features mix a landmark-ratio yaw proxy, PnP pitch and eye-line
  roll. They are not three calibrated physical rotation angles.
- Screen/writing profiles are independent and currently in memory only.
  Recalibrate after restart or incompatible camera/context changes.
- Green during baseline collection means stable usable sample collection,
  not proof of looking at the target.
- Optional gaze validation evaluates a separate screen-mapping candidate;
  it does not replace the active attention policy.
- Occlusion, reflections, small faces and extreme side placement can prevent
  usable tracking. Calibration cannot recover invisible eye features.
- Hiding the camera preview does not stop analysis.

For Camo, connect the iPad in Camo Studio, then select its camera in Settings.
ONF is not fixed to Camo; built-in, USB and other virtual cameras use the same
selection workflow. Actual hardware compatibility still requires testing.

## Data

- Database: project-root `sessions/onf.sqlite3` in source mode.
- Completed session: `sessions/<timestamp>/observations.csv`, `events.csv`,
  `summary.json`, and `result.png`.
- Preferences: `%LOCALAPPDATA%/ONF/settings.json`.
- Foreground tracking aggregates Windows executable names and active-use time,
  not keystrokes or browser history.
- Do not publish personal records, settings, camera images or build output.
  Back up the database before maintenance.

## Checks and Build

Start with tests affected by a change:

```powershell
python -m unittest tests.test_time_accumulator tests.test_metrics
python -m unittest tests.test_screen_gaze
python -m unittest tests.test_study_timing
```

Fixtures do not certify real camera/audio, native mixed-DPI or packaged behavior.
See [status and acceptance gates](docs/STATUS_AND_ROADMAP.md).

When separately requested, `build_onf.bat` stages a build, checks startup and
replaces the fixed `dist/ONF.exe`. Build dependencies are in
`requirements-build.txt`. No build was performed during this documentation pass.

## Documentation

- [Document index and precedence](docs/README.md)
- [Architecture and ownership](docs/ARCHITECTURE.md)
- [Status and remaining work](docs/STATUS_AND_ROADMAP.md)
- [Graphify scope and findings](docs/GRAPHIFY_ANALYSIS.md)
