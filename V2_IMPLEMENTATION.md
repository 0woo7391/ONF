# ONF V2 Implementation Notes

## Scope

ONF V2 keeps the repository and prototype tag, but replaces the runtime with a
new visual-attention pipeline:

1. Camera frame
2. Face landmark observation
3. Quality gate
4. Calibration profile
5. Temporal filtering
6. Focus policy
7. Duration accumulator
8. Session recorder
9. PySide6 single-window UI

## Success Criteria

- `v0.1-prototype` preserves the cloned prototype state.
- `refactor/v2-attention-engine` contains the V2 implementation.
- Focus metrics use elapsed monotonic time, not frame majority voting.
- Calibration collects multi-frame samples and validates stability.
- Face analysis estimates head pose with `solvePnP`.
- Gaze uses both eyes and stores horizontal and vertical ratios.
- Eye openness is normalized by eye width.
- `LOW_CONFIDENCE`, processing errors, and camera errors map to unscored time.
- Sessions save `observations.csv`, `events.csv`, `summary.json`, and `result.png`
  when a session ends.
- Sessions are also indexed in `sessions/onf.sqlite3`; the Records tab reads
  from that database and can remove selected DB records.
- The default UI is one PySide6 window with camera, state, controls, and metrics.
- Windows camera opening tries DirectShow/MSMF and the UI lets the user switch
  camera indexes for virtual cameras such as Camo.

## Verification

Run unit checks without a camera:

```bash
python -m unittest discover -s tests
```

Run the desktop app on Windows:

```bash
python main.py
```

The first screen should open one ONF V2 window. Use `Set baseline`, wait for
calibration to finish, then use `Start session`.
