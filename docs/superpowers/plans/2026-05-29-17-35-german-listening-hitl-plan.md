---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: german-listening-mvp-4layer-plan
parent_thread: codex-thread
parent_spec: C:/Users/HOANG PHI LONG DANG/repos/German_NewWords/docs/superpowers/specs/2026-05-29-17-00-german-listening-hitl-spec.md
targets:
  - C:/Users/HOANG PHI LONG DANG/repos/German_Listening
  - C:/Users/HOANG PHI LONG DANG/repos/German_Listening/Tools/src/glist_pipeline
  - C:/Users/HOANG PHI LONG DANG/repos/German_Listening/docs/superpowers/plans/evidence
related_features:
  - mvp_3_action_flow
  - langgraph_orchestration
  - hitl_in_block_creation
  - packaging_and_exe
  - action1_mode_router
related_stages:
  - app_flow
  - live_run
  - verify
  - package
---

# Goal
Implement MVP with 4-layer structure where product flow is primary: exact 3-action app contract, LangGraph runtime with `suggest_boundaries`/`apply_boundaries`, HITL in action 1, and profile-based mode router preserving SSOT/symmetry/invariance.

# Key Deliverables
1. Product flow layer complete (exact 3 menu actions + branch rules).
2. Runtime layer complete (LangGraph marker path and validation gate).
3. Action 1 mode router complete (profile-based route for marker/classic/agent suggestions).
4. HITL integrated inside action 1 (agent suggestions mode, including uncertain boundary review).
5. Packaging layer complete (CLI + documented exe build path).
6. Evidence layer complete (proof artifacts for all layers).

# SSOT, Symmetry, Invariance Enforcement
## SSOT tasks
1. Add runtime record file per run capturing transcript path, audio path, requested mode, routed mode, and output markdown path.
2. Ensure Action 2 reads only created listening blocks file as source-of-truth.
3. Validate HITL final labels only against taxonomy SSOT.
4. Store boundary scoring and selected-cut logs as SSOT evidence for semantic split decisions.
5. Store input profile artifact as SSOT for router decisions.

## Symmetry tasks
1. Implement shared Action 1 handler with routing policy table.
2. Ensure `agent suggestions` is not marker-only and remains functional on non-marker transcripts.
3. Keep verification report format identical across modes.

## Invariance tasks
1. Add tests for 3-option menu invariance.
2. Add tests for missing-block branch invariance in Action 2.
3. Add tests for count invariance (`blocks == mp3 == srt`).
4. Add tests for fail-stop invariance (no split on invalid state).
5. Add tests/guards for boundary invariance (`<=60s` for all blocks).
6. Add tests for router invariance (no marker path call when profile is non-marker).

# Task Breakdown
## Layer 1 - Product Flow (Primary)
### Task 1.1 - Implement exact 3-action menu contract
- Main menu only:
  1) CREATE LISTENING BLOCKS for ANKI
  2) CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS
  3) EXIT

Verification:
- command: run app entry and capture menu output
- evidence: menu snapshot with exact 3 options only

### Task 1.2 - Action 1 input contract + mode handling
- Prompt transcript path, audio path, mode (`marker-based`, `classic-based`, `agent suggestions`).
- Execute block creation using selected mode.

Verification:
- command: action 1 run with marker mode
- evidence: generated `Outputs/Listening-generated.md`

### Task 1.3 - Action 1 mode router
- Build transcript profile detector (`marker_capable`, `classic_capable`, `reason`).
- Build routing policy for requested mode -> routed mode.
- Add typed error for unsupported marker request on non-marker transcript.
- Add run record artifact containing requested/routed mode.

Verification:
- command: action 1 with marker transcript + non-marker transcript under `agent suggestions`
- evidence: run record artifact + no marker-anchor crash in agent-suggestions path

### Task 1.4 - Action 2 branch contract
- If no listening blocks file: prompt only `create new` or `exit`.
- If file exists: run deterministic split/subtitle path.

Verification:
- command: action 2 with missing-file scenario then existing-file scenario
- evidence: branch transcript + output files

## Layer 2 - Pipeline/Runtime
### Task 2.1 - LangGraph orchestration wiring
- Ensure output-producing runtime path is LangGraph-based.
- Ensure marker sequence: `generate -> suggest_boundaries -> apply_boundaries -> enrich_llm -> quality_gate -> validate -> split`.
- Add boundary scoring artifact contract (candidate score + selected cut + confidence).

Verification:
- command: live run trigger for marker
- evidence: ordered step completion logs

### Task 2.2 - Boundary selector constraints
- Enforce sentence-boundary-only cuts with hard max 60s.
- Optimize soft target to ~45s, allow natural-short unit below 30s only when semantic/unit boundary detected.
- Fallback deterministically when LLM confidence below threshold.

Verification:
- command: marker run with boundary debug output
- evidence: boundary selection log showing hard constraints preserved

### Task 2.3 - Validation gate enforcement
- Ensure split blocked on validation fail.

Verification:
- command: controlled failing validation scenario
- evidence: explicit gate-stop log

## Layer 3 - HITL in App
### Task 3.1 - Agent suggestions mode in action 1
- Integrate HITL decision loop into block-creation path.
- Include boundary-review HITL for uncertain LLM suggestions: accept, regenerate, discard/manual.
- Persist decision events.

Verification:
- command: action 1 with `agent suggestions` mode
- evidence: labels JSONL tail + boundary HITL log tail with method stats

## Layer 4 - Packaging
### Task 4.1 - CLI/entrypoint completeness
- Ensure app entry supports menu flow and run commands.

Verification:
- command: app help/entry run
- evidence: runnable entry + documented usage

### Task 4.2 - EXE packaging path (secondary)
- Document and verify build path for exe package.

Verification:
- command: documented build command dry-run or build run
- evidence: build log or documented reproducible path

## Layer 5 - Evidence/Closeout
### Task 5.1 - Marker verification bundle
- Capture marker validator PASS.
- Capture `blocks/mp3/srt` equality proof.
- Capture action 1 and action 2 run transcripts.
- Capture boundary suggestion evidence (scores, chosen cuts, confidence, HITL intervention if any).

Verification:
- command: validator + count commands
- evidence: PASS snapshot and count proof

### Task 5.2 - Router verification bundle
- Capture non-marker transcript run in `agent suggestions` with routed fallback path.
- Capture typed marker-mode fail on non-marker transcript.

Verification:
- command: action 1 router scenario runs
- evidence: router run records + logs

### Task 5.3 - Scope annotation
- Add marker MVP closeout note.
- Keep classic deferred note if unresolved.

Verification:
- command: list evidence files
- evidence: marker closeout + classic status notes

# Unresolved / Deferred
1. Classic parity may remain deferred if not explicitly included in current sprint.

# Completion Criteria
1. All 4 layers have passing evidence.
2. Exact 3-action contract proven.
3. Marker runtime proven end-to-end with `suggest_boundaries` and `apply_boundaries` active.
4. Agent-suggestions route proven for marker and non-marker transcripts.
5. HITL proven inside action 1 flow including uncertain-boundary branch.
6. Packaging documented; exe treated as secondary deliverable.
