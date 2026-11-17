# Graphify Analysis

2026-11-16. Installed CLI: 0.9.97.
Upstream: [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify).

## Safe Local Scope

A staging tree copied only main.py and .py/.qml files from onf_v2/ and tests/.
No DB, settings, sessions, media, builds, virtualenvs, node_modules, isolated
web previews or Git metadata were copied.

```powershell
graphify extract .cache/docs-graphify-2026-11-16/source --code-only --no-cluster --max-workers 2 --out .cache/docs-graphify-2026-11-16
graphify explain "SessionManager" --graph .cache/docs-graphify-2026-11-16/graphify-out/graph.json
```

- 53 Python code files; 1,116 nodes, 4,200 edges.
- 27 QML files unsupported and skipped.
- Zero docs, papers or images sent for semantic extraction.
- No semantic API/cloud pass, installer, labeling, hooks or global config changes.
- main.py and two package initializers emitted no symbols; that does not prove
  they are unused.

Raw output and staged source remain under local .cache/, not public docs.
They may contain local paths. Refresh the staging snapshot before rerunning.

## Interpretation

SessionManager's neighborhood identifies MeasurementBridge and legacy
MainWindow consumers, accumulator, recorder, models and tests.
Imports/calls carry EXTRACTED labels; some uses/type links carry INFERRED labels.
AST inference is not runtime tracing.

Entry points, QML signal wiring, diagnostic-policy boundaries and critical
accounting were checked directly. Markdown roles/checkpoints/contracts were
reconciled manually; Graphify did not semantically analyze Markdown.
This is documentation reconciliation, not an exhaustive code audit, full-suite
rerun or hardware benchmark.

## Corrections

| Old ambiguity | Correct account |
| --- | --- |
| QWidget tree presented as current UI | QML active entry; separate legacy UI |
| All head angles described as PnP | Landmark yaw proxy, PnP pitch, eye-line roll |
| Settings universally auto-saved | Explicit Save on Settings form; some interaction preferences persist separately |
| Many equally current plans | Index separates current rollout, detailed contracts and history |
| Green collection implies accuracy | Stable collection only; validation separate |
| Mapping class implies policy adoption | Diagnostic candidate only |
| Plan time implies actual study | Explicit attribution/allocation/manual contracts |
| Historical tests imply current release proof | Separate source/fixture/hardware/EXE evidence |

Do not run Graphify install, hook install, global merge or cloud semantic
extraction for this task. Local flags differ from newer online docs; inspect
graphify --help before changing commands.

## Verification of This Documentation Pass

- Checked 217 local Markdown links across the 19 changed/new documents;
  all targets exist in this checkout. This is not a remote HTTP-link check.
- Converted 36 PC-absolute gallery links to document-relative paths.
- `git diff --check` passed; `start_onf.bat --check` passed without camera access.
- Confirmed the prototype tag and active refactor branch still exist.
- No application source, user data, settings, dependency, executable, rule file,
  commit or push was changed by this documentation pass.
- Existing captures stay local under the approved media exclusion. Relative
  links do not make unpublished captures available on GitHub; historical
  galleries need a separate sanitized-media publication decision if shared.
