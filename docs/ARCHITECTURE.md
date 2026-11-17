# Architecture

Snapshot: 2026-11-16 local working tree. Graphify assisted Python navigation;
QML wiring and critical source contracts were inspected directly.

## Runtime

`main.py -> ui_qml/preview.py::run -> qml/Main.qml`.
Despite its filename, preview.py is the active source application entry.
It creates AppBridge, MeasurementBridge and camera/icon providers.

| Page | Owner under onf_v2/ui_qml/qml |
| --- | --- |
| Shell/navigation | Main.qml |
| Preparation/general/Pomodoro/rest/result | pages/LearningPage.qml |
| Camera/baselines/optional validation | pages/MeasurementPage.qml |
| Tasks/calendar/planned and actual timeline | pages/PlannerPage.qml |
| Selected day/week/month and record editing | pages/RecordsPage.qml |
| Preferences/Save/camera/alerts | pages/SettingsPage.qml |

StudyStyle.qml and compatibility Theme.qml own tokens; study_appearance.py
renders icons. SUIT and Lucide assets/licenses live under qml/assets.
The old ui/main_window.py is retained for legacy_main.py.

## Data Flow and Ownership

```text
CameraService -> frame/timestamp -> FaceAnalyzer -> FrameObservation
AttentionEngine:
  QualityGate + calibration profiles + per-profile filtering
  -> profile selection + FocusPolicy/StateStabilizer -> FocusDecision
MeasurementBridge:
  lifecycle + rest/Pomodoro + alerts + foreground sampling
  -> SessionManager -> DurationAccumulator + EventTracker + SessionRecorder
  -> QML properties/signals and live projection
SessionRecorder -> session files + SQLite
AppBridge -> saved records/plans/settings -> QML
```

| Owner | Responsibility |
| --- | --- |
| app/camera_service.py | Capture/backend fallback/reconnect |
| core/face_analyzer.py | Landmarks, both-eye features, mixed head features |
| core/quality_gate.py | Valid versus unavailable/error observation |
| core/calibration.py | Guided acquisition, stability and profiles |
| core/attention_engine.py | Screen/writing selection, filtering, policy and diagnostics |
| core/focus_policy.py, temporal_filter.py | Thresholds and temporal state |
| app/session_manager.py | Lifecycle, absence reclassification, finish once |
| core/metrics.py | Monotonic durations, buckets, task spans, events |
| app/pomodoro.py | Optional phase clock, not a second record ledger |
| app/foreground_app_tracker.py | Foreground executable duration sampling |
| app/session_database.py | SQLite plans/calendar/sessions/study records |
| app/session_recorder.py | Observations/events/summary/image and DB insertion |
| app/settings_store.py | Validated persistent preferences |
| ui_qml/app_bridge.py | Planner/records aggregation and editing |
| ui_qml/measurement_bridge.py | Camera/session lifecycle and UI-facing state |

All owner paths above are relative to onf_v2.
Capture/analysis work is asynchronous. Do not create a second camera,
accumulator or per-frame database writer in QML.

## Calibration Boundary

Current yaw is a landmark-ratio proxy, pitch uses PnP and roll the eye line.
Do not describe all three as calibrated rotation angles.

ScreenCalibrationWindow presents full-screen stationary targets, acknowledging
rendered positions through MeasurementBridge. Stable green means usable sample
collection, not target accuracy. Screen/writing profiles remain independent;
compatible profiles survive failed/canceled same-camera recalibration.

core/screen_gaze.py is an affine ridge mapping candidate. Optional validation
uses fresh targets and reports residuals/spread/valid-frame diagnostics without
silently refitting or changing the active classifier.
The relative-rotation head candidate remains test-only.

## Time and Records

F = focus; N = non-focus; U = unscored; A = absence pending; B = break.

- Study = F + N + U + A; B excluded.
- Measured focus = F.
- Focus ratio = F / (F + N).
- Coverage = (F + N) / (F + N + U + A).
- Empty denominators return zero internally; UI must not equate unavailable
  measurement with evidence of zero attention.

DurationAccumulator credits the previous state over a positive interval.
Non-increasing timestamps add no duration. Pending absence may be
retroactively reclassified as break by session policy.

Plans do not generate measured time. Explicit selection changes task attribution
without restarting study. Tracked entries describe measured intervals;
allocations annotate existing capacity without increasing totals.
Manual entries add separate study with unknown measured focus; duration-only
records have no fabricated hourly position.

Learning shows now/today. Records shows selected historical periods, including
the full configured 24-hour study day. The default day boundary is 04:00.

## Persistence and Shutdown

Source AppBridge uses project-root sessions/onf.sqlite3. Packaged resolution
uses the executable directory, or its parent when inside dist.
Settings use %LOCALAPPDATA%/ONF/settings.json, with a home fallback.
Baselines are currently in memory only.

Recorder creates a unique session folder and streams observations. Finish closes
it, writes events/JSON/PNG and inserts summary/buckets/task records into SQLite.
Later DB allocations do not rewrite original measurement CSV/JSON.

MeasurementBridge shutdown stops its timer, finishes an active session,
releases the camera and closes analyzer work. This is orderly shutdown,
not certified recovery after process termination or power loss.
