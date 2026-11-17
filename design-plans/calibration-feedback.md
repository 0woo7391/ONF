# Calibration feedback: acquisition, validation, and selective retry

> Documentation reconciliation (2026-11-16): Retained detailed calibration specification and historical evidence. Stable acquisition and independent validation remain distinct; current status is consolidated in the documentation map. [Documentation map](../docs/README.md).

Date: 2026-09-30
Updated: 2026-10-04
Status: stages 1-2 implemented as acquisition feedback plus a shadow screen-mapping candidate and optional independent diagnostics. Live accuracy, acceptance limits, and attention-policy adoption remain pending.
Written against: `f7b6baf76b57837b09bdd86a04c80f9c02a74b29` plus the existing dirty working tree on `refactor/v2-attention-engine`.

## Decision

Replace the single prominent percentage with per-target acquisition state and a separate validation result. Do not present sample count, tracking heuristics, or a fitted training error as gaze accuracy.

Before fitting a camera/user/screen mapping, ONF cannot determine whether a gaze estimate is close to a screen target. Acquisition colors must describe usable tracking and sample stability, not invented target proximity. A pretrained gaze-direction model would not, by itself, establish the chosen monitor's screen coordinates.

Keep the current MediaPipe/OpenCV/NumPy/PySide6 stack and its single camera owner. Evaluate a small screen-mapping candidate separately before connecting it to attention decisions. No mandatory videos, new dependencies, EXE build, global redesign, planner changes, or session-statistics changes.

This is a focused supplement to `FOCUS_TRACKING_REVIEWED_PLAN.md`, sections 6-7. That plan still governs observation quality, head-pose candidate adoption, time accounting, and screen/writing independence. It is not a replacement or a claim that those stages passed live testing.

## Implementation checkpoint

- Screen acquisition now requires both 2 usable seconds and 12 distinct frames per direction, after the existing 2-second settling allowance. These are provisional trial settings. The permitted sample gap is 0.5 seconds; per-direction timeout is 12 seconds and overall timeout remains 45 seconds.
- Duplicate, reversed, pre-display, nonfinite, and stale timestamps cannot advance acquisition. Invalid eyes or an analysis stall pause usable time without erasing accepted observations. Low cadence produces a performance reason rather than an instruction to move the face.
- Per-direction states are waiting, settling, collecting, paused, sampled, and failed. Existing local head-dispersion and coarse direction-coverage checks are retained. They are not an eye-to-screen accuracy test.
- A failed direction can be recollected without discarding completed directions. Failed/canceled recalibration preserves the previous same-camera profile; camera selection clears pending acquisition and both profiles. Writing remains independent, with no new intermediate writing cue.
- The full-screen window uses an acquisition ring, nearby guidance/reason, and five direction states. No large accuracy-looking percentage, duplicated remote instruction, moving-target sampling, or perpetual pulse. Display acknowledgment waits for a rendered, fully visible stationary target.
- Failure remains visible with retry/cancel. Retry restarts at the first missing direction and rejects callbacks from the earlier run. Both actions were invoked through the QML buttons in tests.
- Verified: 72 focused tests in 16.968 seconds; `start_onf.bat --check` passed. No camera was opened. No EXE, DB, dependency, or focus-policy change was made in this stage.
- Visual fixture: collection/pause/failure at all five directions and six logical window sizes: 1366x768, 1093x614, 911x512, 1920x1080, 1536x864, and 1280x720. Bounds, target/instruction separation, rendered pixels, state colors, and QML warnings checked. Windows fonts were loaded for the offscreen fixture. The three logical sizes per resolution approximate 100/125/150% available space; this is not native mixed-DPI or physical monitor-switch verification.
- Captures: [collecting](captures/calibration/calibration-1366x768-collecting.png), [paused](captures/calibration/calibration-1920x1080-paused.png), [compact failure](captures/calibration/calibration-911x512-failed.png).
- Stage 1 remaining scope: writing usable-dwell redesign and head-compensation adoption. Stage 2 mapping/validation checkpoint follows. No claim of improved live gaze accuracy or calibration success rate yet.

### Stage 2 checkpoint (2026-10-04)

- User chose a separate optional validation button, not an automatic extra pass. Workflow: Measurement > screen posture setup > gaze validation. Existing coarse posture readiness remains independent of the mapping fit; no new focus classifier or adoption gate was added.
- Render acknowledgment transfers actual target centers in window-local logical coordinates, selected screen geometry/name/DPR, camera index, raw frame size, and the eye-feature version. Guidance changes no longer move a collecting target. Old run/stage callbacks cannot relabel observations. Changed geometry during collection invalidates that candidate; camera selection clears candidates, and raw capture-size changes invalidate mapping/old analysis without replacing posture profiles.
- `core/screen_gaze.py`: immutable two-eye-feature affine ridge candidate, acquisition-only standardization, equally weighted target medians, numerical scale floor, rank check, augmented NumPy least squares. Head motion cannot rescue constant eye features. The numerical floor and ridge penalty are not accuracy thresholds. Noise-relative direction separation and practical limits still need live tuning.
- Validation freezes the candidate and collects a fresh center repeat plus intermediate directional points. It uses the same displayed-target acknowledgment, settling/usable-dwell rules, stale-result protection, and face/eye quality gate, but does not build a posture profile or reject observations for prediction error or head dispersion.
- Result dialog reports each region's median/P90 diagonal-normalized error, P90 prediction spread around its median, and valid processed-frame fraction. Invalid timely observations count as attempts; duplicate/pre-display/settling/stale frames do not. This fraction is not elapsed-time session coverage. Large and off-screen residuals are retained; predictions are not clipped or used to refit.
- Validation targets stay neutral. No red/yellow/green accuracy indicator or automatic pass/fail until useful error limits are approved. Failed/canceled validation retains the candidate and previous result; successful refitting clears old validation results. Failed fitting preserves only a compatible prior candidate. Screen/writing posture profiles and current attention decisions remain independent.
- Verified: 86 focused tests in 17.850 seconds; source launcher dependency check passed. Synthetic math/quality/stale-data/lifecycle checks and actual QML button > rendered-coordinate transfer > independent pass > result dialog were exercised. No camera opened; no new dependency, DB change, recording, EXE build, or commit.
- Captures: [neutral validation target](captures/calibration/screen-gaze-validation-target.png), [synthetic result dialog](captures/calibration/screen-gaze-validation-report.png). Six-size acquisition bounds checks were rerun. Native mixed-DPI/monitor switching and live-camera accuracy remain unverified; a physical camera move or device substitution at the same index cannot always be detected.
- Next gate: short live diagnostic comparison when a camera is available, then agree useful residual/coverage limits and supported head range. Do not feed this candidate into attention decisions yet.

## Evidence chain

- Runtime: `qml/Main.qml` connects `screenCalibrationRequested` to `ScreenCalibrationWindow.openOn(window.screen)` and injects the existing measurement bridge.
- Collection owner: `core/calibration.py::_update_guided`, `_guided_progress`, `_build_profile`.
- Display synchronization: `ui_qml/measurement_bridge.py::screenTargetDisplayed` checks the current run and delegates stage/key validation to the manager using a Python monotonic timestamp.
- Presentation owner: `ui_qml/qml/components/ScreenCalibrationWindow.qml`; button consumer: `pages/MeasurementPage.qml` and `components/CalibrationButton.qml`.
- Existing progress is collected sample count divided by the required count. `quality_score` is also a count ratio, not validation accuracy.
- `_has_guided_coverage` already checks horizontal/vertical changes. However, it adds gaze change and scaled head change: head movement can satisfy it without distinguishable eye responses. This can check coarse posture coverage, not establish an eye-to-screen mapping.
- A read-only synthetic probe confirmed this: all target `gaze_x/gaze_y` values were zero, left/right yaw differed by 3.0 and up/down pitch differed by 3.0 in the current degree-labelled fields, and `_has_guided_coverage` returned `True`. This is a predicate check, not a live gaze-accuracy test.
- `face_analyzer.py::_eye_metrics` already uses pixel-space eye axes and eye-width normalization. Reuse this; do not implement a second landmark extractor.
- `_head_pose` uses a landmark-ratio yaw proxy, PnP pitch, and eye-line roll. Do not label a screen region's collection state as calibrated degrees, or assume the tested relative-rotation candidate is already in production.
- Original inspection found no screen-coordinate regression or independent gaze validation. Stage 2 adds `screen_gaze.py` and a separate collector owned by `AttentionEngine`; the existing feature summaries still govern attention thresholds.
- Original proposal evidence was source inspection. The implementation checkpoint adds offscreen UI/test evidence, not a camera-accuracy benchmark.

## Design language

- Audited surface: full-screen screen calibration and the two calibration controls on the measurement page.
- Design sources: current QML owners, `Theme.qml`, accepted screen/writing workflow in the reviewed tracking plan, and the user's request for meaningful per-direction feedback.
- Documented decisions: use the actual monitor, keep writing independent, report actionable failure, no intermediate writing sound, no duplicated guidance, preserve a compatible previous profile on failure/cancel.
- Governing owners: `CalibrationManager` owns progress/result; `MeasurementBridge` exposes it; QML presents it. QML must not calculate readiness independently.
- Explicit exceptions: none documented.

### Presentation findings

| # | Problem | Evidence | Proposed change | Scope | Confidence |
| --- | --- | --- | --- | --- | --- |
| 1 | The visible percentage cannot answer which requested direction is usable. | The window renders only `screenCalibrationProgress`; `_guided_progress` has target counts but no independent validation result. | Show named target states, keeping acquisition separate from validation. | Screen window and measurement calibration controls | High, source + explicit user request |
| 2 | The same target instruction appears near the target and again in a remote bottom panel. | `promptLabel(target.key)` and `targetLabel(displayedTargetKey)` reach the same visible window; the accepted plan excludes repeated instructions. | Keep one instruction and one actionable reason next to the current target. | Screen window | High, source |

Improve first: finding 1. Changing colors/animations without changing what progress means would leave the main problem intact.

## 1. Values to compute

Do not collapse these into a weighted, seemingly scientific score:

| Value | Meaning | User presentation |
| --- | --- | --- |
| Tracking validity | Face/eyes/frame can be used now | One short reason when unavailable |
| Valid acquisition duration | Usable time collected for this target | Target ring, not accuracy percentage |
| Within-target dispersion | Repeatability of eye features during a short dwell | Stable / gathering / retry |
| Direction separation | Different targets produce distinguishable features | Internal check; actionable failure |
| Validation residual | Estimated gaze versus an instructed target in a separate pass | Confirmed / needs retry; detailed error only in diagnostics |
| Valid observation fraction | How much of the attempted interval could be evaluated | Diagnostic coverage, separate from error |

Even validation uses an instructed target as a reference. Without an independent eye tracker, it does not prove that the user actually followed it. Report measured consistency with the instruction, not a guarantee of true gaze or cognitive focus.

## 2. Acquisition calculations

### Existing eye features

For each eye, retain the current pixel-space formula:

```text
w = distance(outer_corner, inner_corner)
u = unit eye-corner axis; v = perpendicular axis, positive downward
C = eye-corner midpoint; I = iris center
g_x = dot(I - C, u) / w
g_y = dot(I - C, v) / w
EAR = mean(projected eyelid gaps) / w
```

Keep left/right values for validity checks. Use their mean only when both eyes are valid. These features are not gaze angles. Do not clamp them to 0..1 or feed preview mirroring into analysis.

### Frame acceptance and time

Accept only a distinct, finite observation from the current run/stage, captured after target arrival and settling, with one visible face, usable open eyes, and acceptable binocular consistency. For screen-target acquisition, interval eligibility additionally requires the local stable-dwell condition described below. Reject stale/duplicate/out-of-order results. A blink pauses acquisition; a missing iris is not automatically a closed eye.

Use frame timestamps rather than UI ticks or arrival times:

```text
dt_i = t_i - t_(i-1)
d_i = dt_i, if both adjacent observations are eligible and 0 < dt_i <= gap_limit
d_i = 0, otherwise
T_valid = sum(d_i)
acquisition_fill = min(1, T_valid / T_required, distinct_samples / N_required)
```

This is a bounded approximation between observations, not evidence that an unobserved gap was valid. An invalid observation clears the interval anchor; recovery cannot credit the missing interval. Count neither animation time nor the initial settling time.

Start evaluation with the existing 2-second settling allowance, then test a 2-second usable dwell and at least 12 distinct frames per target. These are provisional trial settings, not validated production defaults. Choose the gap limit from capture/analysis cadence; very low FPS must produce a performance reason, not an instruction to move the face. Keep a finite per-target timeout and overall limit, without silently retrying forever.

### Stability and direction separation

For each feature over a timestamp-bounded recent window:

```text
center = median(feature)
robust_spread = 1.4826 * median(abs(feature - center))
```

Use short-window gaze dispersion and binocular agreement to distinguish a usable dwell from tracking spikes. Small natural movements are not automatically errors. Evaluate collection at each target, not only after every target has finished. Do not pool deliberate changes between targets into a single instability score.

For horizontal and vertical target pairs, compare feature-center separation to their within-target spread:

```text
separation_x = abs(center_left.g_x - center_right.g_x)
              / max(spread_left.g_x + spread_right.g_x, noise_floor_x)
separation_y = abs(center_up.g_y - center_down.g_y)
              / max(spread_up.g_y + spread_down.g_y, noise_floor_y)
```

The required separation and noise floors need real-camera tuning. Missing/constant feature dimensions fail; tiny numerical spread must not create artificial confidence. Check the two-dimensional design rank as well: large one-dimensional motion is not adequate two-axis coverage. Do not assume universal raw left/right signs across cameras.

For the screen-gaze candidate, head variation cannot substitute for missing eye separation. Explain an insufficient signal as an observation limitation, not proof that the user failed to look correctly. Do not impose this eye-specific rule on the existing coarse posture policy without its own comparison tests.

## 3. Screen mapping candidate

### Targets and labels

Reuse the existing center/up/down/left/right targets for the first candidate. At display acknowledgement, send their actual normalized monitor-local coordinates `(u, v)` in addition to run/stage/key. The current key alone is insufficient: top/bottom positions are clamped by window height.

Use QML logical coordinates consistently: `u = targetCenterX / windowWidth`, `v = targetCenterY / windowHeight`. Store the selected screen geometry and capture/preprocessing signature with the candidate. Do not mix physical pixels, global desktop origins, and QML logical units. Geometry or camera changes invalidate compatibility; camera motion cannot always be detected automatically.

### Minimum model

First candidate: affine ridge mapping from binocular mean eye features:

```text
X_row = [1, standardized(g_x), standardized(g_y)]
Y_row = [target_u, target_v]
B = argmin_B sum_j w_j * ||X_j B - Y_j||^2 + lambda * ||B_without_intercept||^2
prediction = X_current B
```

Use equally weighted target summaries or equally weighted temporal blocks per target. Higher FPS must not give one direction greater influence. Standardization is fitted on acquisition only and has nonzero scale floors. Solve with the existing NumPy least-squares facilities; no manual inverse, new ML framework, polynomial basis, or generic model registry.

Five repeated labels are not hundreds of independent calibration conditions. Start with two features, not yaw/pitch/roll/translation plus many landmark coordinates. A rich head-compensation model needs independently varied head poses while viewing the same target, followed by separate validation. Adding head features without that data can learn that head movement means gaze movement, recreating the current complaint.

This candidate is locally useful only if validation passes. Five cross-shaped samples do not establish reliable full-screen corner coverage. If corner use is required, test additional corner targets; expand to nine acquisition targets only when that evidence warrants the extra burden. Do not silently demand nine targets from every user.

### Integration boundary

Evaluate this candidate without changing `FOCUS`/`NON_FOCUS` decisions first. Do not certify the candidate based on agreement with the current attention algorithm. Head-pose upgrades remain the separate candidate in section 6 of the reviewed plan.

If adopted later, consume gaze and its validity through the existing attention engine and temporal policy; do not add a second UI-owned focus classifier. Out-of-domain head position or missing eyes means unknown, not the nearest target and not automatic focus. Never widen acceptance indefinitely to manufacture a successful calibration.

## 4. Independent validation and color

Freeze the fitted candidate before validation. Do not split neighboring acquisition frames randomly into train/test, retrain on validation, exclude frames because their prediction is far from the target, or clip predictions to the screen before scoring.

Use a fresh short pass at separate locations within the sampled area, for example center repeated plus left/right/up/down positions partway between the center and acquisition targets. The center repeat tests repeatability; the other positions test interpolation. A camera/head-motion trial and corner coverage remain separate checks, not claims justified by this pass.

For each eligible validation observation:

```text
e = sqrt(((u_hat-u_target)*W)^2 + ((v_hat-v_target)*H)^2) / sqrt(W^2 + H^2)
```

`W,H` use the same coordinate units. Report median and 90th-percentile residual per region, prediction spread, and valid fraction separately. This is screen-diagonal-normalized error, not angular error in degrees. A stable but wrong estimate has low spread and high residual; it must fail.

Define acceptable and unacceptable residual radii before the trial. They must reflect useful screen-region resolution, not grow with a failing model's observed error. For a feedback preview only:

```text
t = clamp((display_error - acceptable_radius) / (unacceptable_radius - acceptable_radius), 0, 1)
t: 0 -> green, 0.5 -> yellow, 1 -> red
```

Keep exact radii unapproved until live comparison. Smooth the visual indicator over time, but calculate and retain validation metrics from all eligible observations, including large residuals. Missing tracking is gray with a reason, never red "wrong gaze".

During the independent pass, keep the target appearance neutral so the user is not trained to chase model error. Show the residual color/result after each measured interval. Optional continuous distance-color preview belongs after validation and must not count as independent validation data. This separation is necessary even if a live color game looks more responsive.

A target can be `sampled` before it is `validated`. Only label validation complete when every required check passes. Retry only the failed region's acquisition, refit, then revalidate the affected mapping; a changed global fit does not retain previous validation as current proof. Failed/canceled candidates do not replace a compatible active profile.

## 5. Writing calibration

Writing is not a point on the monitor. Do not display a moving screen target while asking someone to look at a notebook, and do not describe its result as pixel gaze accuracy.

Reuse the independent writing profile and actual eye/head observations while the user writes normally. Track valid observed time, eye visibility, and stable local segments across natural posture variation. Changes between valid segments are not themselves tracking failures. Retain bounded feature distributions; do not use "more movement" as a completion target.

Feedback: collecting / eyes obscured / sufficient observations / unable to distinguish. No intermediate audio. Brief return to the screen before/after writing can check that the two work areas are distinguishable, but cannot establish phone-versus-paper detection. An eye-obscured camera angle needs physical adjustment; software cannot recover invisible eye direction reliably.

## 6. Screen composition and motion

Preserve the existing light theme. Reuse `Theme.background`, `surface`, `text`, `muted`, `primary`, `success`, `warning`, `danger`, `border`, `radius`, `fast`, and `normal`. Do not introduce another theme or browser/HTML runtime.

```text
[ Screen calibration ]           [ Acquisition / Checking ]       [ Cancel ]


                              fixed target dot
                          acquisition ring outside
                         one short instruction/reason


[ Center: sampled ] [ Up: gathering ] [ Down: waiting ] [ Left ] [ Right ]
```

- Top: fixed-height, quiet header with phase and cancel. No large overall accuracy-looking percentage.
- Main: one stationary target with a small center mark. During acquisition, the ring fills from usable duration. Green means usable acquisition, yellow means settling/unstable, gray means unavailable; persistent failure uses a warning/error symbol and concrete reason. No claim of target alignment yet.
- Bottom: compact per-region strip with distinct pending, collecting, sampled, validated, and retry states. Use shape/icon plus label, not color alone. Measurement-page buttons summarize the same manager state.
- Put the current instruction immediately below the target, or above it near the bottom edge. Reserve its full multiline bounds; clamping only the target center does not prevent overflow. Do not require looking away to read a distant footer.
- Remove perpetual scale pulsing. Fade/change state using `Theme.fast`/`Theme.normal`; short target relocation is allowed only outside acquisition. Do not sample a moving target or a disappearing instruction.
- Acknowledge the settled target in its final geometry after a rendered frame, then apply the settling allowance. Retain the existing run/stage checks. A stale callback cannot advance or relabel samples.
- Pause fill on a blink or temporary interruption; do not erase already accepted samples. Never retain them after camera/preprocessing/screen compatibility changes.
- On failure: name the missing condition and offer retry/cancel. Do not show an endless spinner or automatic repeated restart. No UI gauge based only on elapsed countdown.
- Fit within the selected monitor with no scrollbars. Verify 1366x768 and 1920x1080 at 100/125/150% scaling, negative desktop origins, and a changed monitor. Font sizes come from explicit styles, not viewport-width scaling.
- Acquisition and optional validation-result UI were rendered and inspected with hardware-free QML fixtures. Real-camera accuracy remains unverified; the dialog reports diagnostics, not a certification.

## 7. Libraries and repositories reviewed

Checked against their public source/docs on 2026-09-30. No package was installed or benchmarked here; project claims are not ONF measurements.

| Candidate | Relevant evidence | Decision |
| --- | --- | --- |
| [MediaPipe Iris](https://chuoling.github.io/mediapipe/solutions/iris.html) / [Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python) | Iris/face landmarks; Iris docs explicitly distinguish tracking from knowing where someone looks. | Keep the current extractor first. Migrating legacy FaceMesh to Tasks is a separate compatibility change, not required to redesign feedback. |
| [EyeTrax](https://github.com/ck-zhang/EyeTrax) | Python, MIT; [ridge implementation](https://github.com/ck-zhang/EyeTrax/blob/master/src/eyetrax/models/ridge.py), several calibration workflows. Current source uses MediaPipe Tasks. | Best small Python comparison candidate, not an automatic replacement. Its [dependencies](https://github.com/ck-zhang/EyeTrax/blob/master/pyproject.toml) include scikit-learn, SciPy, screeninfo, pyvirtualcam, and opencv-python. ONF already uses opencv-contrib-python: avoid mixing two cv2 wheels or upgrading the app environment for a trial. |
| [GazeFollower](https://github.com/GanchengZhu/GazeFollower) | Python deep-learning gaze framework; CC BY-NC-SA 4.0 in its README. [Requirements](https://github.com/GanchengZhu/GazeFollower/blob/main/requirements.txt) include MediaPipe 0.10.10, MNN, and pygame. | Reference/isolated comparison only. Current ONF pins MediaPipe 0.10.21; dependencies, model terms, and GUI/camera ownership need separate evaluation. No evidence here that it is more accurate on this setup. |
| [WebGazer](https://github.com/brownhci/WebGazer) | Browser JavaScript, ridge mapping and calibration examples. [Official site](https://webgazer.cs.brown.edu/) lists GPLv3 and says updates are no longer guaranteed as of 2026-02-24. | Algorithm/interaction reference; do not add a web runtime just to use it. |

[Pupil Labs calibration guidance](https://docs.pupil-labs.com/core/best-practices/) supports separating calibration from validation and checking different validation points. Its headset performance figures must not be applied to an ordinary webcam. Its recording recommendation is not adopted as a mandatory ONF requirement.

Do not download arbitrary saved pickle models. If a comparison needs a model, use verified official assets and an isolated environment, never the installed app's runtime. Recheck licenses/dependencies at an actual adoption revision.

## 8. Minimal implementation boundaries

Stage 1 acquisition and stage 2 shadow mapping/optional diagnostics are approved and implemented. Attention adoption, new accuracy colors/limits, writing redesign, and wider changes remain pending; do not broaden scope without approval.

1. `core/calibration.py`: extend existing target state with usable duration, explicit failure reason, local dispersion, and sampled/validated distinction; preserve old profile transaction semantics.
2. `core/models.py`: only add data required by the candidate/results. Current profiles are in-memory; persistence, new DB tables, and settings controls are not needed for this change.
3. `ui_qml/measurement_bridge.py`: expose per-target state and actual display geometry, keep stale-result defenses and one camera/analyzer. No numeric validation in QML.
4. `ScreenCalibrationWindow.qml`: replace the overall-progress-first composition; reuse its full-screen routing, cancel behavior, and theme. Adjust the existing calibration buttons only to reflect truthful state.
5. Mapping candidate: independently testable math lives in one small `core/screen_gaze.py` module; `AttentionEngine` owns candidate/result lifecycle and the separate collection-only manager. No estimator service hierarchy. Using predictions in focus decisions still needs a separate positive validation decision.

The wider learning page, planner, records, Pomodoro, alerts, database, study-time formula, and packaged executable are excluded.

## 9. Verification and adoption gates

### Targeted automated checks

- Same monotonic input durations at 5/10/30 FPS yield comparable collection time. Dropped frames, duplicate timestamps, and stale-stage frames cannot fill a ring.
- Temporary invalid eyes pause collection. No-data timeout fires without observation callbacks. Cancel or failed retry retains only a compatible previous profile.
- Constant eye features across all targets cannot qualify the screen-gaze candidate through head motion alone. Rank-deficient input and nonfinite values fail explicitly.
- Synthetic affine features recover known screen coordinates on separately generated positions; perturbations and out-of-range predictions remain visible to validation. This tests math, not webcam accuracy.
- Validation observations cannot enter fitting or be discarded because of high residual. A stable wrong prediction retains high residual despite low jitter; unavailable timely observations reduce the valid processed-frame fraction. Automatic acceptance remains unimplemented.
- Display acknowledgement includes current run/stage/final target position; old animation completion signals cannot start sampling.
- Retry/refit invalidates stale validation results. Camera or monitor changes cannot combine incompatible samples.

Use the existing unittest style and only directly affected modules, for example after implementation:

```powershell
python -B -m unittest tests.test_screen_gaze tests.test_calibration tests.test_qml_measurement_bridge tests.test_attention_engine tests.test_face_analyzer tests.test_quality_gate tests.test_qml_learning_ui
```

Stage 1 passed 72 focused tests. Stage 2 ran the command above: 86 passed, including mapping/rank/independent-diagnostic and QML flow checks. These are synthetic/offscreen checks, not a live accuracy benchmark. Add only focused regressions; do not rebuild or run every unrelated test by default.

### Visual check without camera

Drive waiting, collecting, sampled, validating, retry, success, and cancel states through a QML fixture. Verify the three-way distinction between capture quantity, live tracking, and validation; text/target bounds at each monitor/DPI setting; no duplicate guidance or perpetual motion. This proves rendering and state presentation only.

### Brief live check when a camera is available

Use the user's current webcam/Camo through the same camera service, without requiring a video recording. Compare fixed head + eye motion, small head motion while looking at one target, translation/distance change, normal blinking, actual writing, and eye occlusion. Record only the necessary numeric diagnostics.

Compare calibration completion/retry rate, independent per-region residuals, false-away during valid work, false-focus during actual deviation, unscored fraction, and decision latency. Lower error obtained by discarding difficult frames is not automatically an improvement. Do not claim robustness to arbitrary head/camera positions.

## 10. Order, risks, and stop conditions

1. Truthful per-target data and feedback first; verify sample accounting and pause/retry without changing attention decisions.
2. Small mapping candidate and independent validation next; compare with the existing behavior. No production replacement if data cannot distinguish targets.
3. Head-movement compensation only when independent head/eye trials justify the extra samples/features. Screen mapping alone is not a solution to arbitrary posture changes.
4. Final motion/polish after the states and meaning are verified. Product build remains a separate request.

Stop or ask before broadening scope if nine-point sampling becomes mandatory, a pretrained model/dependency is needed, the prior head candidate must become production, new disk persistence is needed, or focus-policy behavior must change.

Unresolved adoption parameters: tolerable screen-region error, maximum acceptable calibration burden, and supported head/translation range. These need a short real-use comparison, not invented percentages. A model that cannot meet them should remain unadopted; do not camouflage it with smoother animation or looser thresholds.

After acceptance and successful validation, the executor should reconcile section 7 and stage D of `FOCUS_TRACKING_REVIEWED_PLAN.md` with the implemented behavior. This proposal does not edit or supersede that document's status checkboxes.
