---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cli-audio-merge-ssot
parent_spec: docs/superpowers/specs/2026-07-13-11-20-cli-audio-merge-ssot-spec.md
targets:
  - Tools/src/glist_pipeline/cli.py
  - Tools/src/glist_pipeline/merge_audio.py
  - Tools/tests/test_cli_menu.py
  - Tools/tests/test_merge_audio.py
  - GermanListeningCLI.spec
  - Requirement/merge_audio_with_markers.ps1
related_features:
  - audio-merge
  - exe-usability
  - ssot-audio-pipeline
related_stages:
  - action2-audio-output
  - standalone-audio-merge
---

# CLI Audio Merge SSOT Plan

## Goal
Add one SSOT audio-merge path to `GermanListeningCLI.exe` and `glist merge`, with marker and no-marker behavior differing only by plan construction and prompt resolution, while keeping `ffmpeg` as native merge backend and reducing the PowerShell script to compatibility delegation.

## Key Deliverables
- One authoritative merge engine in `Tools/src/glist_pipeline/merge_audio.py`.
- One authoritative non-interactive command contract: `glist merge`.
- One new interactive menu action: `MERGE AUDIOS`.
- One compatibility wrapper path from `Requirement/merge_audio_with_markers.ps1` into Python CLI merge contract.
- Focused tests for plan building, executor behavior, parser/menu dispatch, prerequisite failures, and compatibility delegation.

## Task/Wave Breakdown

### Task 1 — Build merge-engine SSOT module
**Scope**
- Touch `Tools/src/glist_pipeline/merge_audio.py`.
- Touch `Tools/tests/test_merge_audio.py`.
- Keep `ffmpeg` as native backend; no new media dependency.

**Steps**
1. Port minimum proven helpers from `Requirement/merge_audio_with_markers.ps1` for path resolution, source filtering, prompt resolution, mp3 staging, concat manifest generation, and cleanup.
2. Define one segment data shape that covers both modes.
3. Add one authoritative `build_merge_plan(...)` that returns source-only segments for no-marker mode and intro/source/outro symmetry for marker mode.
4. Add one authoritative `merge_audio(...)` executor that stages plan items, writes concat manifest, invokes `ffmpeg -f concat`, and cleans temp files.
5. Keep prompt-generation logic outside executor core; it may resolve prompt clips before or during staging, but executor still consumes one ordered plan.

**Rules**
- Sorting is exact filename A-Z order.
- Input scan is non-recursive.
- Only `.mp3`, `.wav`, `.m4a` participate.
- Output overwrite is explicit and deterministic.
- No silent English-voice fallback in generated mode.

**Verification**
- Add plan-order regression for unsorted input names.
- Add marker-symmetry regression for two-file input.
- Add one-file regression for marker and no-marker paths.
- Add executor test with mocked subprocess/native calls that proves concat manifest order, overwrite flag, and cleanup behavior.

### Task 2 — Lock prerequisite and failure contracts
**Scope**
- Touch `Tools/src/glist_pipeline/merge_audio.py`.
- Touch `Tools/tests/test_merge_audio.py`.
- Keep behavior aligned with current script where already defined.

**Steps**
1. Add `ffmpeg` presence check before temp staging.
2. Add generated-mode voice selection contract:
   - explicit `--voice-name` must resolve or fail with available voice names
   - implicit voice selection must find German-capable SAPI voice or fail
3. Add recorded-mode prompt-path contract for `teil_N.mp3` and `ende_des_teil_N.mp3`.
4. Add output overwrite contract matching current native behavior.
5. Keep failure messages actionable and mode-specific.

**Verification**
- Add missing-ffmpeg failure test.
- Add missing-requested-voice failure test.
- Add missing-German-auto-voice failure test.
- Add missing-recorded-prompt failure test.
- Add output-overwrite assertion in executor test.

### Task 3 — Expose authoritative `glist merge` command
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Touch `Tools/tests/test_cli_menu.py`.
- Keep parser changes minimal and local.

**Steps**
1. Add `merge` subparser with required `--input-dir`, `--output-file`, and `--markers` contract.
2. Add conditional handling for `--prompt-mode`, `--prompt-dir`, `--voice-name`, `--bitrate-kbps`, `--keep-temp-files`, and `--list-voices`.
3. Add one command handler that validates arg combinations and delegates to shared merge engine.
4. Do not add second non-interactive merge entrypoint.

**Verification**
- Add parser/dispatch tests for marker and no-marker forms.
- Add invalid-arg-combination tests such as `--markers without --prompt-mode recorded`.
- Add `--list-voices` dispatch test if kept in contract.

### Task 4 — Add interactive menu flow without new semantics
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Touch `Tools/tests/test_cli_menu.py`.
- Keep menu flow a thin prompt adapter.

**Steps**
1. Add menu action 3: `MERGE AUDIOS`.
2. Renumber exit to 4.
3. Prompt for merge values with spec defaults.
4. Convert menu answers into same engine call semantics as `glist merge`.
5. Keep prompt-specific questions conditional on marker mode only.

**Verification**
- Add menu-rendering regression.
- Add merge-selection dispatch regression.
- Keep existing menu persistence behavior after successful action.

### Task 5 — Reduce PowerShell script to compatibility delegation
**Scope**
- Touch `Requirement/merge_audio_with_markers.ps1`.
- Touch `Tools/tests/test_merge_audio.py` or adjacent wrapper-focused test.
- Do not leave local merge logic in script.

**Steps**
1. Replace script-owned merge implementation with delegation into Python CLI merge contract using marker defaults.
2. Preserve compatibility parameters only where they map directly to CLI contract.
3. Preserve voice-list utility only if it delegates cleanly to Python path; otherwise drop it and update usage text.
4. Ensure wrapper still feels usable for existing callers while no longer owning merge semantics.

**Verification**
- Add wrapper-delegation test or smoke assertion that wrapper command path targets Python CLI contract rather than script-local concat logic.
- Manually inspect wrapper for absence of canonical merge implementation.

### Task 6 — Rebuild and verify executable path
**Scope**
- Touch `GermanListeningCLI.spec` only if packaging requires it.
- Verification only if no spec file change is needed.

**Steps**
1. Confirm `GermanListeningCLI.spec` already includes package entrypoint and does not need extra hidden imports for `merge_audio.py`.
2. Run focused tests first.
3. Rebuild exe from existing spec.
4. Run one smoke path through menu-driven merge and one smoke path through `glist merge`.

**Verification**
- Focused pytest subset passes.
- Executable rebuild succeeds.
- Smoke run proves menu path and command path both reach merge engine.

## Design Constraints
- Shortest safe diff wins.
- No new dependencies.
- `ffmpeg` remains native merge backend.
- No second merge implementation.
- No GUI work.
- No broad CLI restructuring unrelated to merge.
- Preserve current script semantics where already explicit unless spec now tightens them.

## Risks and Mitigations
- **Risk:** interactive and non-interactive paths drift.
  - **Mitigation:** define `glist merge` first, then let menu gather values into same contract.

- **Risk:** PowerShell wrapper keeps hidden duplicate behavior.
  - **Mitigation:** strip wrapper to delegation and test that delegation path exists.

- **Risk:** generated-mode environment differences make tests flaky.
  - **Mitigation:** mock SAPI/command discovery in tests; test contract, not host machine state.

- **Risk:** executor tests become brittle by over-locking temp filenames.
  - **Mitigation:** assert ordered manifest semantics and cleanup outcomes, not incidental file naming.

## Verification
- proof target: one authoritative merge plan covers marker and no-marker modes
  - method: test
  - evidence: plan-order and marker-symmetry regressions in `Tools/tests/test_merge_audio.py`

- proof target: generated and recorded prerequisite failures are deterministic
  - method: test
  - evidence: explicit failure regressions for ffmpeg, voice selection, and missing prompt clips

- proof target: `glist merge` owns non-interactive semantics
  - method: test
  - evidence: parser/dispatch regressions in `Tools/tests/test_cli_menu.py`

- proof target: menu action is thin adapter over same semantics
  - method: test
  - evidence: merge menu rendering and dispatch regression

- proof target: PowerShell path delegates rather than duplicates merge logic
  - method: test or smoke assertion
  - evidence: wrapper delegation check and script inspection

- proof target: executable path includes merge feature
  - method: rebuild and smoke
  - evidence: successful `GermanListeningCLI.exe` build and one merge smoke run

## Completion Criteria
- `merge_audio.py` is SSOT for merge behavior.
- `glist merge` exists and is authoritative for non-interactive use.
- Menu action 3 exists and uses same semantics.
- PowerShell marker script delegates to Python contract and no longer owns merge logic.
- Focused tests for engine, parser, menu, and wrapper pass.
- `GermanListeningCLI.exe` rebuild succeeds with merge feature included.

## Rollback Note
If wrapper delegation proves risky late in patch, keep Python merge engine and CLI/menu path, but retain script as thin temporary adapter with explicit TODO to remove duplicate code immediately after exe rollout. Do not accept long-term dual-logic state.

## Next Handoff
After approval, execute with `skill-executing-plans`.
