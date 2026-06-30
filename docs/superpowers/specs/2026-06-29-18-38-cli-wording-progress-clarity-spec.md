---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: cli-wording-progress-clarity
parent_workstream: none
targets:
  - Tools/src/glist_pipeline/cli.py
  - Tools/src/glist_pipeline/semantic_generate.py
  - Tools/tests/test_mode_router.py
  - Tools/tests/test_enrich_llm.py
related_features:
  - cli-ux-clarity
related_stages:
  - action1-block-generation
---

# CLI Wording and Progress Clarity Patch Spec

## Goal
Improve Action 1 CLI wording and progress output so users can understand:
- what each mode actually does
- which generator route was selected
- whether block count is deterministic or LLM-driven
- whether process is still running during long enrichment/postprocess steps

## Key Deliverables
1. Replace confusing primary label `agent suggestions` with clearer user-facing label `Guided review`.
2. Keep backward-compatible aliases for old inputs.
3. Print selected route and reason before generation starts.
4. Print clear note when block count is deterministic.
5. Print start/end progress around long-running generation and enrichment steps.
6. Clarify regenerate behavior in guided review lane.
7. Add focused tests for aliases and progress wording.

## Task/Wave Breakdown

### Wave 1 — Mode Prompt Clarity
- Update menu wording for Action 1 mode selection.
- Accept numeric shortcuts and short aliases.
- Preserve existing internal mode values (`marker`, `classic`, `hitl`).
- Preserve old text aliases for backward compatibility.

### Wave 2 — Route Explanation
- Print chosen mode after user input.
- Print transcript profile check start.
- Print final routed generator:
  - `marker-based`
  - `classic-based`
  - `semantic fallback`
- Print route reason in plain language.

### Wave 3 — Progress Visibility
- Add progress prints before generator call.
- Add progress prints before and after enrichment/postprocess.
- Add regenerate progress print with reminder that unchanged input may produce same block count.

### Wave 4 — Focused Verification
- Add/adjust tests for:
  - mode aliases
  - mode prompt helper
  - progress prints in shared postprocess
- Run focused pytest subset.

## Design Decisions
1. **Rename only user-facing label**
   - Keep internal mode `hitl`.
   - Change displayed primary label from `agent suggestions` to `Guided review`.
   - Reason: shortest diff, least code churn.

2. **Backward compatibility stays**
   - Old inputs still accepted:
     - `agent suggestions`
     - `agent suggestion`
     - `agent`
     - `suggestions`
     - `hitl`
   - New shortcuts added:
     - `1`, `2`, `3`
     - `daf`, `telc`

3. **No fake LLM framing**
   - Guided review must not imply LLM decides total block count.
   - Route explanation must state when count is deterministic.

4. **Progress prints at boundaries, not spam**
   - Start/end prints for long steps.
   - No per-token or deep heartbeat logic in this patch.
   - Reason: enough visibility without noisy console output.

5. **No block-splitting algorithm change**
   - Semantic splitter logic and thresholds remain unchanged.
   - This patch is wording/visibility only.

## Invariants
- Internal routing behavior must stay unchanged.
- Existing mode router logic remains source of truth.
- Semantic route must still be described honestly as fallback when marker anchors absent.
- Old mode text inputs must continue to work.
- Tests must pass without introducing new dependencies.

## Acceptance Criteria
1. User can enter `1`, `2`, or `3` for mode selection.
2. Primary mode prompt no longer presents `agent suggestions` as main label.
3. Guided review mode prints that app chooses best available generator and then asks user to review result.
4. Guided review flow prints that block count is generator-based/deterministic, not LLM-decided.
5. Semantic fallback flow prints why fallback happened.
6. Postprocess/enrichment prints visible start/end progress markers.
7. Regenerate action prints that same route is being rerun and output may remain same.
8. Focused tests for alias handling and progress output pass.

## Non-Goals
- No new LLM-based block planner.
- No changes to semantic block thresholds.
- No change to transcript-profile detection logic.
- No redesign of HITL state machine.
- No fix in this patch for semantic generator’s current latest-file resolution behavior.
- No new config surface or abstraction layer.

## Risks and Mitigations

### Risk 1 — Wording still too ambiguous
- Mitigation:
  - explicitly say `Guided review chooses best available generator`
  - explicitly say `block count is not LLM-decided`

### Risk 2 — Console gets noisy
- Mitigation:
  - only print route, reason, step starts, and step ends
  - avoid line-by-line generator chatter

### Risk 3 — User sees route honesty and notices deeper path inconsistency
- Mitigation:
  - allow exact-file messaging where cheap
  - treat direct path wiring as follow-up patch, not hidden behavior

## Validation Plan

- proof target: numeric shortcuts select expected internal mode
  - method: test
  - evidence: focused pytest on mode prompt helper

- proof target: short aliases still work
  - method: test
  - evidence: focused pytest on mode prompt helper

- proof target: postprocess progress is visible
  - method: test
  - evidence: focused pytest asserting printed progress strings

- proof target: patch does not break existing targeted behavior
  - method: test
  - evidence: passing focused pytest subset for CLI-related tests

- proof target: route wording matches actual routing model
  - method: inspection
  - evidence: code review against `Tools/src/glist_pipeline/mode_router.py`

## Completion Criteria
- User-facing label updated to `Guided review`.
- Old aliases remain supported.
- Route and reason prints added.
- Deterministic-count clarification added.
- Enrichment/postprocess progress prints added.
- Focused tests added or updated.
- Focused pytest subset passes.

## Suggested User-Facing Strings

### Mode Prompt
- `Choose block generation mode:`
- `1) DAF B1`
- `2) TELC B1`
- `3) Guided review`
- `Mode [1/2/3 or name]:`

### Guided Review Explanation
- `Selected mode: Guided review`
- `Guided review chooses best available generator, then asks you to review result.`
- `Block count is generator-based, not LLM-decided in this mode.`

### Route Prints
- Marker:
  - `Route selected: marker-based`
  - `Reason: transcript contains marker anchors.`
- Classic:
  - `Route selected: classic-based`
  - `Reason: classic mode chosen.`
- Semantic:
  - `Route selected: semantic fallback`
  - `Reason: transcript has no marker anchors, so app uses timing/sentence-based splitting.`

### Progress Prints
- `Generating listening blocks...`
- `Enrichment started...`
- `LLM translations and notes may take a while.`
- `Enrichment complete. Running placeholder check...`
- `Postprocess complete.`

### Review Step
- `Review generated block plan:`
- `1) accept  2) regenerate  3) discard  4) manual_select`

### Regenerate
- `Regenerating once with same route...`
- `Route remains: <route>`
- `If transcript and timing are unchanged, block count may stay same.`

## Follow-Up Notes
- Separate follow-up should wire semantic generation directly to selected transcript/audio path.
- Separate follow-up may add richer split-summary diagnostics if still needed.
