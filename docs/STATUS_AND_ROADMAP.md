# Status and Roadmap

Snapshot: 2026-11-16 local working tree based on f7b6baf.
No percentage-complete or release-certification claim.

## Evidence

Implemented means connected source exists. Automated means fixture evidence,
not hardware proof. Historical means a previous plan records checks not rerun
during this documentation pass. Pending acceptance needs live use or approval.

| Area | Source/test evidence | Remaining boundary |
| --- | --- | --- |
| Native shell/study | Main.qml, LearningPage.qml; test_study_timing, test_qml_learning_ui | Phase A implemented, later page redesign pending |
| Planner | PlannerPage.qml, app_bridge, session_database; test_qml_planner_regressions | Optional two-of-three times, direct edits/status/calendar exist; title/layout complaint requires clarification |
| Records | RecordsPage, StudyRecordDialog; test_learning_records | Measured, allocated and manual records remain separate |
| Session/time | metrics, session_manager; test_time_accumulator, test_metrics | Monotonic duration/rest/task spans, not crash recovery |
| Pomodoro | pomodoro, measurement_bridge; test_pomodoro | Optional mode and phase lifecycle |
| Camera | camera_service, measurement_bridge; matching tests | Physical Camo/USB/reconnect/stalls remain hardware acceptance |
| Eye/policy | face_analyzer, quality/policy/filter; matching tests | Synthetic geometry/state checks are not live accuracy |
| Baselines | calibration, ScreenCalibrationWindow; calibration/bridge tests | Stable acquisition is not direction validation |
| Mapping | screen_gaze, engine diagnostics; test_screen_gaze | Optional validation only, NOT active classifier |
| Head candidate | test_head_pose_candidate | Test-only, not adopted |
| Alerts/settings/apps | Corresponding app modules/tests | Real sound/device behavior unverified here |
| Storage | recorder/database and matching tests | Existing persistence; no schema change in docs pass |
| EXE | build_onf scripts/spec | Fixed dist/ONF.exe, no build performed here |

Test module names are under tests/; source owners are indexed in Architecture.

## Latest Approved UI Follow-Up

Study rest uses Lucide coffee; resume uses play. Deferred task status is not a
rest action and was not changed to coffee. StudyButton no longer animates
transparent-to-opaque color through dark intermediate frames; press/focus remain.

The preceding UI work recorded four targeted passes covering hover samples,
coffee/play, Pomodoro actions and motion-disabled controls.
That is synthetic/offscreen evidence, not physical display/audio acceptance.

## Next Gates

1. Documentation: verify links, source owners, Graphify exclusions and no
   personal data in public docs; retain original specifications.
2. Native Study review: preparation/general/Pomodoro/rest/result on the actual
   display; SUIT retained, stable actions and readable contrast.
   Clarify planner-title intent before renaming or restructuring.
3. Hardware when available: full-screen target visibility, collection feedback,
   retry/cancel, writing posture, off-axis limits and recovery. Compare false
   alerts, missed departures, unscored time and latency together.
4. Candidate adoption: agree independent-validation limits and supported head
   range before changing classifier/head logic; requires separate approval.
5. Other page-specific UI: Planner/Records/Measurement/Settings, following the
   current native application plan and per-page rendered regression checks.
   Shared token changes do not mean those redesigns are complete.
6. Packaging on request: stage, startup-check, replace fixed target, then
   separately accept camera/audio/DPI in the installed app.

No mandatory recording, web migration or automatic schedule-based attribution
is authorized by this roadmap.

## Known Limits

- Severe eye occlusion/off-axis views cannot be fixed by widening thresholds.
- Baselines are not persisted across restarts.
- Duration-only manual records cannot automatically detect overlap with
  measured time; use allocation for already measured study.
- Task entries retain stored-date grouping, not exact reconstructed cross-day
  per-task intervals.
- Partial/crash recovery is not certified.
- Old test counts are not a current full-suite result.
- Native mixed-DPI, actual audio/camera and packaged behavior remain separate.

## Publication

Pre-publication verification on 2026-11-17: all 263 tests passed in 104.446s.
Obsolete calibration color assertions were aligned with the approved theme.
The native double-click test now checks the real role of the control: starting
creates one session, while an active Rest action pauses once; keyboard Space
remains functional. No product-code double-click workaround was retained.
Launcher dependency and diff whitespace checks also passed.
These remain automated/offscreen checks, not camera/audio/EXE acceptance.

Substantial uncommitted source/assets/tests remain. Review exact files before
upload and exclude records/settings/images/builds/dependencies. Docs describing
local features must not imply remote availability without matching source.
Push requires separate approval; pushing the feature branch does not merge main.
