# ONF V2

ONF V2 estimates visual attention from a webcam. It does not measure cognitive
focus directly. The default definition of focus is:

> A valid face is tracked, eyes are open, and head direction plus gaze remain
> inside the calibrated screen work area for the required duration.

The original prototype is preserved by the `v0.1-prototype` tag. V2 work lives
on the `refactor/v2-attention-engine` branch.

## What Changed

- Replaced frame-majority timing with monotonic elapsed-time accumulation.
- Added multi-frame calibration with sample quality checks.
- Replaced nose-position yaw/pitch with `solvePnP` head-pose estimation.
- Added both-eye horizontal and vertical gaze ratios.
- Added eye-open ratios normalized by eye width.
- Split raw observation states from final session states.
- Added unscored time for camera/model/low-confidence cases.
- Added session recording: raw decisions, events, summary JSON, and result PNG.
- Replaced the two OpenCV windows with one PySide6 desktop window.
- Added a Pomodoro mode with a circular countdown, automatic breaks, manual
  next-focus confirmation, pause/resume, persisted timing settings, and
  completed-cycle recording.
- Added a persisted camera-preview toggle. Hiding the preview stops video
  rendering while face and gaze analysis continue in the background.
- Moved camera capture and MediaPipe analysis off the UI loop. Camera preview
  is capped at 20 FPS, attention analysis at 15 FPS, and Windows now prefers
  Media Foundation before falling back to DirectShow.
- Added non-blocking camera switching and automatic reconnection for the
  currently selected built-in, USB, or virtual camera.
- Added an optional screen-and-writing work mode with separate calibration
  profiles for the normal screen posture and the user's writing posture.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Open the baseline menu and calibrate the screen posture first. When
`Screen + writing` is selected in Settings, calibrate the writing posture as
well. `Start session` becomes available after the required profiles are ready.

The Settings tab stores user preferences automatically in
`%LOCALAPPDATA%\ONF\settings.json`. The defaults are a 60-second continuous
attention-away alert, a 5-minute break countdown, and sound notifications at
60% volume. Four built-in alert sounds can be selected and previewed, and the
volume can be adjusted with a slider or a numeric input.

Pomodoro defaults are 25 minutes of focus, a 5-minute short break, four
cycles, and a 15-minute long break. Visual-attention tracking remains active
during focus phases. Breaks, pauses, and next-cycle waiting time are excluded
from the focus-rate calculation.

## Camera Selection On Windows

Select the built-in webcam, a USB camera, or a virtual camera from the Settings
tab. If the preview is black or the wrong camera opens, press `Refresh cameras`
and try another camera index. For Camo, start Camo Studio and connect the iPad
before selecting its camera index. If the selected camera disconnects during a
session, ONF marks that interval as unscored and retries without ending the
session.

## Verify Without A Camera

```bash
python -m unittest discover -s tests
```

## Project Structure

```text
onf_v2/
  app/
    camera_service.py
    session_manager.py
    session_recorder.py
  core/
    attention_engine.py
    calibration.py
    face_analyzer.py
    focus_policy.py
    metrics.py
    models.py
    quality_gate.py
    temporal_filter.py
  ui/
    main_window.py
tests/
V2_IMPLEMENTATION.md
```

## Output

Each completed session writes files under `sessions/<timestamp>/`:

- `observations.csv`
- `events.csv`
- `summary.json`
- `result.png`
- `sessions/onf.sqlite3` stores the session database used by the Records tab.
