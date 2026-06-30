---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cli-wording-progress-clarity
parent_spec: docs/superpowers/specs/2026-06-29-18-38-cli-wording-progress-clarity-spec.md
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

# CLI Wording and Progress Clarity Implementation Plan

## Goal
Implement focused CLI UX improvements for Action 1 so users can see what mode they selected, which generator route ran, why that route was chosen, and whether long-running work is still progressing.

## Key Deliverables
- User-facing mode prompt uses `Guided review` as primary label instead of `agent suggestions`.
- Numeric and short-text mode aliases work without breaking old inputs.
- Guided review flow prints route, route reason, and deterministic-count clarification.
- Postprocess/enrichment prints visible start/end progress markers.
- Regenerate path prints same-route clarification.
- Focused CLI tests cover alias handling and progress output.

## Task/Wave Breakdown

### Task 1 — Finish mode prompt wording cleanup
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Keep internal `hitl` mode untouched.
- Keep old aliases valid.

**Steps**
1. Replace primary Action 1 mode wording with numbered choices and `Guided review` label.
2. Keep helper-based alias resolution in one place.
3. Ensure prompt accepts `1`, `2`, `3`, `daf`, `telc`, `agent`, `suggestions`, and old full phrases.
4. Print selected mode after successful parsing.

**Verification**
- Inspect prompt text and alias map in `Tools/src/glist_pipeline/cli.py`.
- Run focused alias tests in `Tools/tests/test_mode_router.py`.

### Task 2 — Add route explanation prints at Action 1 runtime
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Reuse existing router output from `route_mode()`.
- Do not change routing rules.

**Steps**
1. Add transcript-profile check print before route resolution.
2. Add helper or inline mapping from routed internal mode to user-facing route label.
3. Print route selected and reason:
   - marker-based: marker anchors found
   - classic-based: classic mode explicitly chosen
   - semantic fallback: no marker anchors, timing/sentence-based split used
4. For guided review mode, print explicit note that block count is generator-based, not LLM-decided.

**Verification**
- Inspect route messages against `Tools/src/glist_pipeline/mode_router.py`.
- Manual dry read of Action 1 control flow in `Tools/src/glist_pipeline/cli.py`.

### Task 3 — Add visible progress around generation and postprocess
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Touch `Tools/src/glist_pipeline/semantic_generate.py` only if needed for one or two user-facing summary prints.
- No algorithm changes.

**Steps**
1. Print generation start before calling routed generator.
2. Keep or add draft/result summary after generator returns.
3. Print enrichment/postprocess start marker.
4. Print enrichment/postprocess end marker and placeholder-check start marker.
5. Print completion marker after postprocess success.

**Verification**
- Add/assert output coverage in `Tools/tests/test_enrich_llm.py` or adjacent CLI-oriented test.
- Run focused pytest subset.

### Task 4 — Clarify guided review prompt and regenerate output
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Do not change HITL decision semantics.

**Steps**
1. Rename review header from `Agent suggestion for block creation review:` to `Review generated block plan:`.
2. On regenerate, print that same route is being rerun once.
3. Print note that unchanged transcript/timing may keep same block count.
4. Preserve existing `accept`, `regenerate`, `discard`, `manual_select` behavior.

**Verification**
- Inspect branch handling around `DecisionAction.REGENERATE`.
- If practical, add small output assertion test; otherwise cover by code inspection and manual command reasoning.

### Task 5 — Run focused validation and capture proof
**Scope**
- No product code changes beyond prior tasks.
- Verification only.

**Steps**
1. Run focused tests with repo `PYTHONPATH` set to `Tools/src`.
2. Confirm alias tests pass.
3. Confirm postprocess progress-output tests pass.
4. Confirm no unintended mode-routing logic changes slipped in.

**Verification**
- Command:
  - `PYTHONPATH=$PWD\Tools\src python -m pytest Tools/tests/test_mode_router.py Tools/tests/test_enrich_llm.py -q`
- Evidence:
  - passing pytest output

## Design Constraints
- Shortest diff wins.
- No new config files.
- No new dependencies.
- No new abstraction unless shared helper clearly reduces duplicated prints.
- No change to semantic split thresholds or transcript-profile logic.
- No claim that LLM decides block count in guided review mode.

## Risks and Mitigations
- **Risk:** prompt wording updated in one place but stale wording remains elsewhere.
  - **Mitigation:** grep for `agent suggestions` and update only user-facing primary labels that should change, while preserving alias parsing.
- **Risk:** route messaging drifts from actual router logic.
  - **Mitigation:** derive wording directly from routed mode and transcript profile conditions already in code.
- **Risk:** extra logging becomes noisy.
  - **Mitigation:** only print at step boundaries and decision points.

## Verification
- proof target: guided review label replaces old primary menu label
  - method: inspection
  - evidence: updated strings in `Tools/src/glist_pipeline/cli.py`

- proof target: alias handling remains backward compatible
  - method: test
  - evidence: passing focused tests in `Tools/tests/test_mode_router.py`

- proof target: postprocess progress is visible
  - method: test
  - evidence: passing output assertions in `Tools/tests/test_enrich_llm.py`

- proof target: route explanation matches live routing logic
  - method: inspection
  - evidence: code review against `Tools/src/glist_pipeline/mode_router.py` and `Tools/src/glist_pipeline/cli.py`

- proof target: implementation stays bounded to wording/progress scope
  - method: diff review
  - evidence: changed files limited to CLI/generator messaging and focused tests

## Completion Criteria
- `Guided review` is primary user-facing label in Action 1 mode prompt.
- Old mode phrases remain accepted as aliases.
- Action 1 prints route and route reason before generation.
- Guided review prints deterministic-count clarification.
- Postprocess/enrichment prints visible progress boundaries.
- Regenerate path prints clearer same-route message.
- Focused pytest subset passes.

## Rollback Note
If new wording causes confusion or breaks tests, revert only user-facing print changes and alias additions first; do not touch routing logic or generator behavior.

## Next Handoff
After approval, execute with `skill-executing-plans` or implement directly in small bounded diff.
