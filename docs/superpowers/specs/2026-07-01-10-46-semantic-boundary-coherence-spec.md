---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: semantic-boundary-coherence
parent_workstream: none
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

# Semantic Boundary and Coherence Patch Spec

## Goal
Fix semantic-route block coherence by removing replayed second-pass transcript content before block formation, preserving abbreviation-safe sentence boundaries, and rejecting draft output when adjacent block overlap shows replay leakage still survived cleanup.

## Key Deliverables
1. Semantic sentence preparation becomes deterministic for abbreviations, instruction stripping, and replay cleanup.
2. Semantic block generation keeps current time thresholds, but receives cleaned sentences only.
3. Quality gate fails on exact adjacent overlap of 2 or more consecutive normalized sentences.
4. Focused tests prove replay cleanup and overlap detection on transcript-derived fixtures.

## Design Decisions
1. **Semantic-local fix, not cross-lane refactor yet**
   - This patch keeps cleanup logic local to semantic lane.
   - Reason: shortest safe diff for active bug.

2. **Explicit replay markers only**
   - Replay cleanup starts only after exact normalized replay markers.
   - Reason: avoid deleting authentic repeated content outside replay phase.

3. **Reuse existing time splitter first**
   - Do not add new split heuristics unless replay cleanup leaves failing regressions.
   - Reason: current bug source is replay leakage, not proven threshold math failure.

4. **Deterministic validator extension**
   - Use exact normalized sentence overlap against adjacent blocks only.
   - Reason: cheap, reproducible, and directly tied to observed failure.

## Invariants
- Semantic final output must not contain replayed second-pass content from earlier accepted sentences after explicit replay markers.
- Semantic cleanup must not drop duplicate sentences outside replay windows.
- Single-sentence adjacent overlap does not fail quality gate.
- Valid short content titles like `Der Wetterbericht.` remain allowed.
- Classic and marker lanes remain unchanged in this patch.

## Acceptance Criteria
1. `Praxis Dr. Becker.` is preserved as one sentence in semantic preparation tests.
2. Replay marker plus repeated `Hallo Jan ...` content is removed before later block formation in transcript-derived tests.
3. Semantic output for transcript `Transcripts/Modellsatz Erwachsene - Hören, Teil 1 bis 4 - Goethe Zertifikat B1 - 1.json` no longer mixes Jan dialogue replay with later Frau Stein dialogue in Abschnitt 2.
4. Quality gate fails on adjacent 2-sentence overlap and passes on 1-sentence overlap.
5. Focused semantic and quality-gate tests pass.

## Non-Goals
- No prompt changes.
- No LLM-based coherence verifier.
- No broad duplicate-content pruning outside replay windows.
- No classic/marker refactor.
- No new timing heuristics unless replay cleanup alone fails tests.

## Validation Plan
- proof target: abbreviation-safe sentence splitting
  - method: test
  - evidence: `Dr. Becker` regression

- proof target: replay-window cleanup removes duplicated second-pass sentences only
  - method: test
  - evidence: transcript-derived replay cleanup fixture

- proof target: adjacent-overlap validator catches replay leakage
  - method: test
  - evidence: 2-sentence overlap failure fixture

- proof target: validator avoids false positives on light overlap
  - method: test
  - evidence: 1-sentence overlap pass fixture and `Der Wetterbericht.` pass fixture
