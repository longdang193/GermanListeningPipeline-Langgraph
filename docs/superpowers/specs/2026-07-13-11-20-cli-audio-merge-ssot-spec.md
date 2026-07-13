---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cli-audio-merge-ssot
parent_workstream: none
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

# CLI Audio Merge SSOT Spec

## Goal
Add one user-facing audio merge function to `GermanListeningCLI.exe` that supports both admissible merge modes:
- merge with Teil markers
- merge without markers

The implementation must be SSOT, symmetry-driven, and native-first:
- one shared merge engine
- one shared segment staging path
- one shared ffmpeg concat path
- mode differences expressed as input-plan data, not duplicated merge logic

## Key Deliverables
1. `GermanListeningCLI.exe` exposes one new menu action for audio merge.
2. One Python merge engine handles both marker and no-marker merges.
3. Marker prompts remain supported in both generated and recorded forms.
4. One authoritative non-interactive command contract exists for merge.
5. Existing PowerShell marker script becomes compatibility surface only, not merge SSOT.
6. Focused tests prove uniform behavior over all admissible cases and prove compatibility delegation.

## Admissible Cases
This patch must work uniformly for all of these cases:
- one source file, without markers
- one source file, with markers
- many source files, without markers
- many source files, with markers
- source files with admissible extensions `.mp3`, `.wav`, `.m4a`
- marker prompt mode `generated`
- marker prompt mode `recorded`
- existing output path already present
- input folder contains non-audio files beside admissible audio files

This patch does not support:
- empty input folder as success case
- source extensions outside `.mp3`, `.wav`, `.m4a`
- silent fallback from generated prompts to English voice output

## User Experience
### New Menu Action
Add one new main-menu option:
- `MERGE AUDIOS`

Recommended updated menu:
1. `CREATE LISTENING BLOCKS for ANKI`
2. `CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS`
3. `MERGE AUDIOS`
4. `EXIT`

### Merge Prompt Flow
When user selects merge action, CLI prompts for:
1. input folder path
2. output file path
3. merge mode: `with markers` or `without markers`
4. if `with markers`: prompt mode: `generated` or `recorded`
5. if `generated`: optional voice name override
6. if `recorded`: optional prompt folder path override

Defaults should remain friendly and match current behavior where possible:
- input folder default: `Audios/Merge`
- output folder default: `Outputs/Merge`
- marker output default: `Outputs/Merge/merged-with-markers.mp3`
- no-marker output default: `Outputs/Merge/merged.mp3`
- prompt mode default for marker merge: `generated`
- prompt folder default: `Audios/MergePrompts`
- intro template default: `Teil {0}`
- outro template default: `Ende des Teil {0}`
- bitrate default: `192`

## Authoritative Command Contract
One non-interactive parser contract must be mandatory. Menu flow and compatibility wrapper must delegate to same merge engine semantics through this contract.

Required subcommand:
- `glist merge`

Required arguments:
- `--input-dir`
- `--output-file`
- `--markers` with values `with` or `without`

Conditional arguments:
- `--prompt-mode` with values `generated` or `recorded`; valid only when `--markers with`
- `--prompt-dir`; valid only when `--markers with --prompt-mode recorded`
- `--voice-name`; valid only when `--markers with --prompt-mode generated`

Optional arguments:
- `--bitrate-kbps`
- `--keep-temp-files`
- `--list-voices`

Contract rules:
- `glist merge` is SSOT command surface for merge behavior outside menu prompts.
- menu action 3 may gather values interactively, but must call same merge engine and preserve same defaults and errors.
- `Requirement/merge_audio_with_markers.ps1` must delegate to `glist merge` with marker defaults or equivalent direct Python CLI invocation.
- no second non-interactive merge interface may be introduced in app code.

## SSOT Design
### Core Principle
Native merge behavior belongs to `ffmpeg`, not custom Python concatenation logic.
Python layer only:
- collects inputs
- validates inputs
- builds ordered segment plan
- normalizes each segment to common mp3 staging format
- writes concat manifest
- invokes `ffmpeg`

### One Shared Merge Engine
Create one module:
- `Tools/src/glist_pipeline/merge_audio.py`

This module becomes SSOT for merge behavior.
No second merge implementation may exist in app code.

### One Shared Execution Shape
Merge flow must be:
1. resolve and validate paths
2. collect source audio files from input folder
3. sort files in Windows logical filename order at collection boundary
4. convert request into ordered segment plan
5. stage each segment to common mp3 format
6. write concat manifest
7. call `ffmpeg -f concat`
8. emit final output path
9. cleanup temp files unless keep-temp requested

### Segment Plan as Data
Mode-specific behavior must compile to one ordered list of segments.
Recommended segment kinds:
- `source`
- `prompt_intro`
- `prompt_outro`

Recommended shape:
- `Segment(kind, source_path, part_number, text=None)`

Examples:

#### Merge Without Markers
Input files:
- `CD1_Tr47.mp3`
- `CD1_Tr48.mp3`

Plan:
- `source(CD1_Tr47.mp3, part=1)`
- `source(CD1_Tr48.mp3, part=2)`

#### Merge With Markers
Input files:
- `CD1_Tr47.mp3`
- `CD1_Tr48.mp3`

Plan:
- `prompt_intro(part=1, text="Teil 1")`
- `source(CD1_Tr47.mp3, part=1)`
- `prompt_outro(part=1, text="Ende des Teil 1")`
- `prompt_intro(part=2, text="Teil 2")`
- `source(CD1_Tr48.mp3, part=2)`
- `prompt_outro(part=2, text="Ende des Teil 2")`

Executor must not care which plan builder produced list.
It only stages and concatenates ordered segments.

## Design Decisions
1. **One engine, two plan builders**
   - Use one merge executor and small plan builders for marker vs no-marker.
   - Reason: symmetry and shortest safe diff.

2. **Reuse current native boundary**
   - Reuse current `ffmpeg`-based normalization and concat shape from `Requirement/merge_audio_with_markers.ps1`.
   - Reason: already proven, native-first, no new dependency.

3. **Prompt generation remains boundary adapter**
   - Generated and recorded prompts are two ways to obtain audio clips.
   - They must converge to same staged segment path before concat.
   - Reason: prompt source is boundary concern, not merge concern.

4. **Sort by Windows logical filename order only**
   - Input ordering remains Windows logical filename order by filename.
   - Native Windows ordering is reused instead of chapter-specific parsing.
   - Reason: native-first, one boundary sorter, no custom semantic reordering.

5. **Thin CLI, thick engine**
   - `cli.py` owns user prompts only.
   - `merge_audio.py` owns merge behavior.
   - Reason: keeps exe UX separate from merge SSOT.

6. **Compatibility wrapper, not second implementation**
   - `Requirement/merge_audio_with_markers.ps1` may call Python entrypoint or remain as legacy shim.
   - It must not remain canonical merge logic after this patch.
   - Reason: prevent merge drift between exe and script.

## Contracts and Failure Semantics
### Input Collection Contract
- Source audio collection scans input folder only, not subdirectories.
- Only `.mp3`, `.wav`, `.m4a` files participate in merge.
- Non-audio files in input folder are ignored.
- If no admissible audio files exist, merge fails before temp staging.

### Ordering Contract
- Ordering is Windows logical filename order from collected admissible files.
- No chapter-specific or regex-based reorder rule is applied in this patch.

### Output Contract
- Output artifact is one `.mp3` file.
- Existing output file is overwritten.
- Overwrite behavior must match current native path by using `ffmpeg -y` or equivalent explicit overwrite contract.

### Generated Prompt Contract
- Generated prompts require `ffmpeg` and Windows SAPI voice access.
- If `--voice-name` is provided and no matching SAPI voice exists, merge fails with available voice names in error.
- If `--voice-name` is omitted, generated mode auto-selects first German-capable SAPI voice using same match family as current script.
- If no German-capable SAPI voice exists, generated mode fails fast.
- Generated mode must not silently fall back to English voice output.
- Failure message must direct user to recorded mode or German voice installation.

### Recorded Prompt Contract
- Recorded mode requires prompt files named `teil_N.mp3` and `ende_des_teil_N.mp3` in prompt dir.
- Missing required prompt clip fails merge before final concat.

### Shared Native Dependency Contract
- If `ffmpeg` is unavailable on `PATH`, merge fails before temp staging.
- Temp staging cleanup runs on both success and failure unless keep-temp is enabled.

## Invariants
- Both merge modes use same executor.
- Both merge modes use same temp staging layout.
- Both merge modes use same ffmpeg concat strategy.
- Marker prompts always wrap each source clip in marker mode.
- No-marker mode never inserts prompts.
- Input files are always merged in Windows logical filename order.
- Mixed admissible source formats supported today by current script remain supported: `.mp3`, `.wav`, `.m4a`.
- Output is one mp3 file.
- If no source files exist, merge fails before temp staging.
- If required recorded prompt clip is missing, marker merge fails before final concat.
- If generated prompt prerequisites fail, merge fails before final concat.
- Menu flow, `glist merge`, and PowerShell compatibility wrapper expose same merge semantics.

## Acceptance Criteria
1. CLI menu displays new `MERGE AUDIOS` action.
2. User can create merged output from `Audios/Merge` without leaving exe flow.
3. `glist merge` exists as non-interactive SSOT command surface.
4. No-marker merge produces one merged mp3 containing only source clips in Windows logical filename order.
5. Marker merge produces one merged mp3 with intro and outro around every source clip in Windows logical filename order.
6. Generated and recorded prompt modes both work through same merge executor.
7. One input file works in both modes.
8. Empty input folder fails with clear error.
9. Mixed admissible input extensions still merge successfully.
10. Existing output file is overwritten deterministically.
11. Existing marker PowerShell entrypoint remains usable by delegation, not duplicate logic.
12. Focused tests pass.

## Non-Goals
- No GUI.
- No waveform editing.
- No silence insertion feature.
- No chapter metadata embedding.
- No custom audio concatenation library.
- No new dependency for TTS or media processing.
- No automatic German voice installation flow.
- No reordering rule beyond Windows logical filename order.

## Risks and Mitigations
### Risk 1 — Drift between exe merge and PowerShell merge
- Mitigation:
  - move merge SSOT into Python module
  - require `glist merge` as shared non-interactive contract
  - reduce PowerShell script to wrapper or deprecate it

### Risk 2 — Prompt generation path complicates no-marker flow
- Mitigation:
  - keep prompt logic outside executor
  - no-marker plan emits source segments only

### Risk 3 — ffmpeg staging inconsistency across segment types
- Mitigation:
  - one shared stage-to-mp3 helper for source and prompt clips
  - one shared bitrate/sample-rate/channel policy

### Risk 4 — Menu complexity grows
- Mitigation:
  - keep prompts linear
  - keep defaults populated
  - only ask prompt-specific questions in marker mode

## Validation Plan
- proof target: no-marker mode emits source-only plan
  - method: test
  - evidence: exact ordered segment kinds for two-file input

- proof target: marker mode emits intro/source/outro symmetry
  - method: test
  - evidence: exact ordered segment kinds and part numbers for two-file input

- proof target: merge sorting follows Windows logical filename order
  - method: test
  - evidence: unsorted input filenames produce Windows logical filename order such as Kapitel 3, Kapitel 10, Kapitel 26

- proof target: generated prompt mode preserves current prerequisite semantics
  - method: test
  - evidence: missing requested voice, missing German auto voice, and missing ffmpeg each fail with expected error

- proof target: recorded prompt mode fails on missing prompt file
  - method: test
  - evidence: exact raised error for missing `teil_N.mp3` or `ende_des_teil_N.mp3`

- proof target: executor writes shared concat order and cleanup behavior
  - method: test with mocked subprocess/native calls
  - evidence: concat manifest order, overwrite flag, and cleanup behavior assertions

- proof target: CLI menu exposes merge action
  - method: test
  - evidence: menu output assertion and merge action dispatch assertion

- proof target: `glist merge` owns non-interactive semantics
  - method: test
  - evidence: parser/dispatch assertions for marker and no-marker forms

- proof target: PowerShell compatibility path delegates instead of duplicating logic
  - method: test or smoke assertion on wrapper command path
  - evidence: wrapper calls Python CLI merge contract rather than local merge implementation

## Completion Criteria
- Merge behavior lives in one Python SSOT module.
- `glist merge` exists and owns non-interactive merge semantics.
- CLI exposes merge flow inside exe path.
- Marker and no-marker modes differ only by plan construction and prompt resolution.
- Existing PowerShell marker script no longer owns canonical merge logic.
- Focused tests for plan building, executor behavior, parser dispatch, CLI menu, and compatibility delegation pass.
- `GermanListeningCLI.exe` can be rebuilt from existing spec with new merge function included.

## Suggested Patch Shape
- `Tools/src/glist_pipeline/merge_audio.py`
  - add path resolution helpers
  - add source file collection helper
  - add prompt clip resolver for generated/recorded marker prompts
  - add shared `stage_to_mp3()` helper
  - add `build_merge_plan()` SSOT
  - add `merge_audio()` executor

- `Tools/src/glist_pipeline/cli.py`
  - add `merge` subcommand with required argument contract
  - add menu action 3 for merge
  - add prompt flow for merge options
  - call shared merge engine
  - renumber exit to 4

- `Tools/tests/test_merge_audio.py`
  - add plan-order tests
  - add marker symmetry tests
  - add generated-prompt prerequisite tests
  - add missing-recorded-prompt failure test
  - add executor manifest/cleanup test

- `Tools/tests/test_cli_menu.py`
  - add merge menu rendering test
  - add merge selection dispatch test
  - add parser/dispatch tests for `glist merge`

- `Requirement/merge_audio_with_markers.ps1`
  - reduce to compatibility wrapper or explicit legacy entrypoint
  - delegate to Python CLI merge contract with marker defaults
  - preserve `ListVoices`-style utility only if delegated cleanly to Python command

- `GermanListeningCLI.spec`
  - verify no extra packaging changes required beyond module inclusion

## Open Questions
- Should `--list-voices` remain subcommand-only rather than menu-visible?
  - recommended now: yes

- Should keep-temp remain subcommand-only rather than menu-visible?
  - recommended now: yes

## Handoff
After approval, hand off to implementation-plan drafting. Do not implement from this spec directly in this skill.
