---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: semantic-filter-finalize-output
parent_spec: docs/superpowers/specs/2026-06-30-14-55-semantic-filter-finalize-output-spec.md
targets:
  - Tools/src/glist_pipeline/semantic_generate.py
  - Tools/src/glist_pipeline/cli.py
  - Tools/tests/test_semantic_generate.py
  - Tools/tests/test_cli_menu.py
related_features:
  - semantic-output-quality
related_stages:
  - action1-block-generation
---

# Semantic Filter and Finalize Output Implementation Plan

## Goal
Implement bounded fixes for semantic-route output quality by separating draft from final output, filtering exam scaffold sentences before block formation, and ensuring final output is promoted only after postprocess and quality gate success.

## Key Deliverables
- Semantic draft is written to `Outputs/Listening-generated.draft.md`.
- Final `Outputs/Listening-generated.md` is updated only after successful postprocess and one authoritative quality gate on draft.
- Semantic instruction filtering is owned by one SSOT helper in semantic generation code.
- Draft and final markdown paths are owned by `Tools/src/glist_pipeline/semantic_generate.py` and reused by CLI flow and tests.
- Existing repeated real exercise content remains preserved in this patch; this patch removes only exam scaffolding, not second-playback dialogue duplication.
- Focused regression tests cover dropped instruction lines, kept dialogue lines, successful draft-to-final promotion, and failed-postprocess final preservation.

## Task/Wave Breakdown

### Task 1 — Define semantic artifact lifecycle
**Scope**
- Touch `Tools/src/glist_pipeline/semantic_generate.py`.
- Touch `Tools/src/glist_pipeline/cli.py`.
- Do not change marker/classic generation semantics.

**Steps**
1. Define fixed semantic draft path `Outputs/Listening-generated.draft.md` and final path `Outputs/Listening-generated.md` in `Tools/src/glist_pipeline/semantic_generate.py`.
2. Reuse those imported path constants from semantic generation, CLI flow, and tests.
3. Ensure each semantic run overwrites draft path only.
4. Ensure final path is updated only after successful enrichment and one authoritative quality gate on draft.
5. Ensure failed postprocess leaves final path untouched.
6. Make promotion behavior explicit and stable: copy or replace draft into final in one documented code path.

**Verification**
- Inspect semantic generation call sites in `Tools/src/glist_pipeline/cli.py`.
- Add test proving old final file survives simulated postprocess failure.

### Task 2 — Add instruction filter SSOT before splitting
**Scope**
- Touch `Tools/src/glist_pipeline/semantic_generate.py` only.
- Keep current sentence splitter and duration thresholds unchanged.

**Steps**
1. Add one helper such as `is_instruction_sentence(text: str) -> bool`.
2. Normalize full-sentence text inside helper.
3. Match only anchored known exam-scaffold openings.
4. Use an explicit starter pattern contract, for example:
   - `^zertifikat b1`
   - `^modul hören`
   - `^hören teil`
   - `^sie hören nun`
   - `^sie hören jeden text`
   - `^zu jedem text`
   - `^wählen sie`
   - `^lesen sie`
   - `^dazu haben sie`
   - `^sie hören eine`
5. Keep mixed/full-content sentences unless they begin with scaffold patterns.
6. Preserve negative example `Achtung, Autofahrer...` as content, not scaffold.
7. Filter sentence list before `split_into_blocks()`.

**Verification**
- Add fixture/test showing exact dropped instruction lines.
- Add fixture/test showing exact kept first dialogue sentence.
- Add negative example test for `Achtung, Autofahrer...` remaining in output.

### Task 3 — Run postprocess and quality gate on draft only
**Scope**
- Touch `Tools/src/glist_pipeline/cli.py`.
- Reuse existing `Tools/src/glist_pipeline/quality_gate.py` gate helper without changing its contract.

**Steps**
1. Route guided-review semantic generation to draft artifact.
2. Run `_run_shared_postprocess()` against draft artifact.
3. Use one authoritative gate function for promotion: `quality_gate.find_quality_issues(draft_path)`.
4. Evaluate placeholder bans and quality checks against draft artifact only through that gate.
5. Promote draft to final artifact only on success.
6. Print draft/final paths clearly in runtime output.
7. Ensure guided-review semantic flow reads draft artifact before promotion.

**Verification**
- Add test for successful promotion from draft to final.
- Add test for failure path leaving final untouched.

### Task 4 — Keep patch intentionally narrow
**Scope**
- Planning guardrail only.
- No extra replay dedup, no threshold tuning, no config extraction.

**Steps**
1. Preserve repeated real exercise content.
2. Do not add replayed-content dedup logic in this patch.
3. Do not introduce new config files for instruction patterns.
4. Keep helper and path wiring local to semantic lane unless shared behavior is strictly required.
5. Do not treat expected duplicated second-playback dialogue as bug scope in this patch.

**Verification**
- Diff review confirms no extra repetition heuristics or threshold changes.

### Task 5 — Run focused verification
**Scope**
- Verification only.

**Steps**
1. Run focused semantic and CLI tests with repo `PYTHONPATH` set to `Tools/src`.
2. Confirm instruction filtering tests pass.
3. Confirm draft/final promotion tests pass.
4. Confirm existing semantic-path tests still pass.

**Verification**
- Command:
  - `$env:PYTHONPATH = (Join-Path $PWD 'Tools/src'); python -m pytest Tools/tests/test_semantic_generate.py Tools/tests/test_cli_menu.py Tools/tests/test_mode_router.py Tools/tests/test_enrich_llm.py -q`
- Evidence:
  - passing pytest output

## Design Constraints
- Shortest diff wins.
- No new dependencies.
- No LLM classifier.
- No replayed-content dedup in this patch.
- No semantic threshold tuning.
- Use one SSOT quality gate and one SSOT pair of output-path constants.
- No behavior drift in marker/classic lanes except shared finalization wiring that is strictly necessary.

## Risks and Mitigations
- **Risk:** anchored instruction patterns are still too broad.
  - **Mitigation:** cover negative example `Achtung, Autofahrer...` in tests and keep explicit starter pattern contract narrow.
- **Risk:** final artifact becomes stale and misleading after failure.
  - **Mitigation:** document and test invariant that failure leaves prior successful final untouched.
- **Risk:** gate logic diverges between CLI and quality module.
  - **Mitigation:** require one authoritative gate function for promotion.
- **Risk:** draft/final logic leaks into non-semantic routes.
  - **Mitigation:** keep path promotion logic scoped to semantic guided-review branch.

## Verification
- proof target: instruction lines are excluded before block splitting
  - method: test
  - evidence: exact dropped instruction assertions in semantic test fixture

- proof target: real dialogue remains in semantic output
  - method: test
  - evidence: exact kept dialogue assertion in semantic test fixture

- proof target: negative content sentence is not misclassified as scaffold
  - method: test
  - evidence: `Achtung, Autofahrer...` remains in semantic output fixture

- proof target: final output is not populated with placeholders on successful run
  - method: test
  - evidence: banned-pattern assertion against promoted final artifact

- proof target: failed postprocess does not overwrite prior final file
  - method: test
  - evidence: pre-seeded final file unchanged after simulated failure

- proof target: guided-review semantic flow uses draft artifact before promotion
  - method: test or inspection
  - evidence: explicit runtime path assertion or CLI-branch assertion against draft path

- proof target: patch remains bounded
  - method: diff review
  - evidence: no threshold changes, no replay-dedup logic, no new config file

## Completion Criteria
- Semantic draft path exists and is used in guided-review semantic route.
- Postprocess and one authoritative quality gate run on draft, not final.
- Final artifact promotion occurs only after success.
- Draft/final path constants are owned by `Tools/src/glist_pipeline/semantic_generate.py` and imported elsewhere.
- Instruction filtering is implemented through one helper before block splitting.
- Focused regression tests pass.

## Rollback Note
If output promotion wiring causes regressions, first revert draft/final promotion changes while retaining test-only instruction filtering evidence. Do not mix rollback with threshold or repetition-logic changes.

## Next Handoff
After approval, execute with `skill-executing-plans`.
