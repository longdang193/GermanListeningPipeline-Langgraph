---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: semantic-boundary-coherence
parent_spec: docs/superpowers/specs/2026-07-01-10-46-semantic-boundary-coherence-spec.md
targets:
  - Tools/src/glist_pipeline/semantic_generate.py
  - Tools/src/glist_pipeline/quality_gate.py
  - Tools/tests/test_semantic_generate.py
  - Tools/tests/test_quality_gate.py
related_features:
  - semantic-output-quality
  - semantic-block-coherence
related_stages:
  - action1-block-generation
---

# Semantic Boundary and Coherence Patch Plan

## Goal
Fix semantic-route output so generated blocks stop carrying replayed second-pass content into later blocks, preserve abbreviation-safe sentence boundaries, and fail promotion when adjacent block overlap still indicates leaked replay content.

## Key Deliverables
- One authoritative semantic-lane cleanup path owns sentence splitting, instruction stripping, and replay cleanup before block formation.
- Semantic output no longer mixes repeated `Hallo Jan ...` content with later `Hallo Frau Stein ...` content in transcript `Transcripts/Modellsatz Erwachsene - Hören, Teil 1 bis 4 - Goethe Zertifikat B1 - 1.json`.
- Abbreviation-safe sentence splitting prevents false sentence breaks such as `Praxis Dr. Becker.`.
- Quality gate rejects draft output when adjacent blocks share an exact normalized sentence-run overlap of 2 or more consecutive sentences.
- Focused regression tests cover replay cleanup, abbreviation handling, and overlap-based gate failures.

## Task/Wave Breakdown

### Task 1 — Make semantic sentence preparation deterministic
**Scope**
- Touch `Tools/src/glist_pipeline/semantic_generate.py`.
- Touch `Tools/tests/test_semantic_generate.py`.
- Keep logic semantic-local in this patch; do not claim cross-lane SSOT yet.

**Steps**
1. Borrow minimum proven legacy behavior for abbreviation-safe sentence splitting.
2. Keep anchored instruction filtering narrow and deterministic.
3. Define one normalized-sentence helper used by both replay cleanup and tests.
4. Add focused tests for `Dr.` abbreviation handling and instruction stripping.

**Verification**
- Add regression proving `Hallo Frau Stein, hier ist die Praxis Dr. Becker.` stays one sentence unit.
- Add regression proving existing scaffold markers still drop before block formation.

### Task 2 — Remove replayed second-pass content before block split
**Scope**
- Touch `Tools/src/glist_pipeline/semantic_generate.py`.
- Touch `Tools/tests/test_semantic_generate.py`.
- Keep implementation deterministic and bounded.

**Rules**
- Replay-marker sentences are explicit normalized matches only:
  - `sie horen jetzt den text noch einmal`
  - `sie horen den text noch einmal`
  - `nun horen sie den text noch einmal`
- A replay window starts immediately after one of those markers.
- Inside replay window, drop sentences while their normalized text already appeared earlier in accepted content.
- Replay window ends at first unseen normalized sentence.
- Outside replay window, never drop content for duplicate-text reasons alone.

**Steps**
1. Build cleaned sentence stream after instruction stripping and before block splitting.
2. Apply replay-window logic using the explicit rules above.
3. Feed only cleaned sentences into existing time-based `split_into_blocks()`.
4. Do not add extra split heuristics unless a failing regression remains after replay cleanup.

**Verification**
- Add transcript-derived regression showing repeated `Hallo Jan ...` playback is removed from later cleaned sentence stream.
- Add regression showing authentic later dialogue `Hallo Frau Stein ...` remains.
- Add regression showing the current Abschnitt 2 failure no longer occurs.

### Task 3 — Extend quality gate with exact adjacent-overlap check
**Scope**
- Touch `Tools/src/glist_pipeline/quality_gate.py`.
- Touch `Tools/tests/test_quality_gate.py`.
- Keep gate deterministic; no LLM judge.

**Rules**
- Normalize block sentence text with same helper semantics used in semantic cleanup.
- Compare each block only with immediately previous block.
- Fail when previous-block suffix and current-block prefix share 2 or more consecutive normalized sentences.
- Do not fail on single-sentence overlap.

**Steps**
1. Add helper to extract normalized sentence lists from rendered `de_1`.
2. Add exact adjacent-overlap detection using the threshold above.
3. Keep placeholder/translation/gloss checks unchanged.
4. Ensure semantic final promotion fails when overlap issues are present.

**Verification**
- Add fixture with 2-sentence adjacent overlap that must fail gate.
- Add fixture with 1-sentence overlap that must pass gate.
- Add fixture with valid short title line such as `Der Wetterbericht.` that must pass.

### Task 4 — Run focused transcript and gate verification
**Scope**
- Verification only.

**Steps**
1. Run focused semantic tests.
2. Run quality-gate tests.
3. Regenerate semantic draft for transcript `Transcripts/Modellsatz Erwachsene - Hören, Teil 1 bis 4 - Goethe Zertifikat B1 - 1.json`.
4. Inspect cleaned draft around current bad zones: Abschnitt 1/2, 5/6, 6/7, 9/10.
5. Run quality gate on draft before final promotion path.
6. Rebuild exe only after tests and transcript smoke pass.

**Verification**
- Commands:
  - `$env:PYTHONPATH = (Join-Path $PWD 'Tools/src'); python -m pytest Tools/tests/test_semantic_generate.py Tools/tests/test_quality_gate.py -q`
  - `$env:PYTHONPATH = (Join-Path $PWD 'Tools/src'); python -m glist_pipeline.semantic_generate --help`
  - exact semantic regeneration command with transcript/audio path passed explicitly
  - `$env:PYTHONPATH = (Join-Path $PWD 'Tools/src'); python -m glist_pipeline.quality_gate Outputs/Listening-generated.draft.md`
- Evidence:
  - passing pytest output
  - no leaked replay overlap in inspected draft
  - quality gate pass on cleaned draft

## Design Constraints
- Shortest safe diff wins.
- No new dependencies.
- No LLM verifier.
- No prompt changes in this patch.
- No classic/marker behavior change in this patch.
- Preserve valid short content titles such as `Der Wetterbericht.`.
- Do not add new split heuristics unless replay cleanup alone leaves a failing regression.

## Risks and Mitigations
- **Risk:** replay cleanup deletes authentic repeated content.
  - **Mitigation:** duplicate dropping happens only inside explicit replay windows.
- **Risk:** abbreviation fix drifts again from legacy behavior.
  - **Mitigation:** copy only minimum proven cases and lock with regression tests.
- **Risk:** overlap gate blocks valid content.
  - **Mitigation:** threshold is 2 consecutive sentences, with explicit 1-sentence pass fixture.

## Verification
- proof target: semantic sentence splitting no longer breaks abbreviations
  - method: test
  - evidence: `Dr. Becker` regression passes

- proof target: replayed second-pass content is removed before block formation
  - method: test
  - evidence: transcript-derived replay cleanup regression passes

- proof target: block 2 no longer mixes Jan dialogue and Frau Stein dialogue
  - method: test and smoke inspection
  - evidence: regression assertion plus cleaned draft inspection

- proof target: quality gate fails on adjacent replay overlap of 2 or more consecutive sentences
  - method: test
  - evidence: failing fixture in `Tools/tests/test_quality_gate.py`

- proof target: quality gate does not fail on single-sentence overlap or valid title lines
  - method: test
  - evidence: passing fixtures in `Tools/tests/test_quality_gate.py`

## Completion Criteria
- Semantic cleanup path has one authoritative semantic-lane sentence-prep and replay-cleanup flow.
- Abschnitt 2 no longer mixes repeated Jan content with Frau Stein dialogue.
- No current bad adjacent replay leakage remains in transcript `...B1 - 1.json` draft smoke run.
- Quality gate catches adjacent-overlap regressions.
- Focused tests pass.
- Exe rebuild happens only after transcript smoke and gate pass.

## Rollback Note
If replay cleanup proves too aggressive, keep abbreviation fix and gate visibility, then roll back only replay-window sentence dropping while preserving failing regressions.

## Next Handoff
After approval, execute with `skill-executing-plans`.
