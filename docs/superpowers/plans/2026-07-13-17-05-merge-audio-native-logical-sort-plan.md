---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: merge-audio-native-logical-sort
parent_spec: docs/superpowers/specs/2026-07-13-11-20-cli-audio-merge-ssot-spec.md
targets:
  - docs/superpowers/specs/2026-07-13-11-20-cli-audio-merge-ssot-spec.md
  - Tools/src/glist_pipeline/merge_audio.py
  - Tools/tests/test_merge_audio.py
related_features:
  - audio-merge
  - ssot-audio-pipeline
  - native-windows-order
related_stages:
  - standalone-audio-merge
---

# Merge Audio Native Logical Sort Patch Plan

## Goal
Fix merge order so audio files follow native Windows logical filename order instead of plain lexical string order. Keep one SSOT ordering rule, shared uniformly by marker and no-marker merge paths.

## Key Deliverables
- Merge order contract updated from plain A-Z string sort to Windows logical filename order.
- One authoritative sorter in Tools/src/glist_pipeline/merge_audio.py.
- collect_source_files() owns ordering.
- uild_merge_plan() stops re-sorting and trusts incoming ordered files.
- Focused tests prove Kapitel 3 ... Kapitel 26 sorts as Windows users expect.
- Rebuilt exe preserves corrected order.

## Task/Wave Breakdown

### Task 1 — Patch contract drift in spec
**Scope**
- Touch docs/superpowers/specs/2026-07-13-11-20-cli-audio-merge-ssot-spec.md.

**Steps**
1. Patch user-facing examples and phrases that currently say ambiguous ilename order so they say Windows logical filename order.
2. Patch execution-shape wording that currently says source files are sorted in deterministic A-Z order.
3. Patch design-decision wording that currently justifies plain filename sort.
4. Patch ordering-contract wording that currently defines exact A-Z ordering.
5. Patch invariant wording that currently says files are always merged in deterministic filename order without clarifying logical sort.
6. Patch non-goal wording that currently forbids reordering beyond filename sort.
7. Patch validation wording that currently expects A-Z outcomes from unsorted filenames.
8. Replace all of those with one rule: Windows logical filename order at collection boundary, shared by both merge modes.

**Verification**
- Spec names one ordering owner only.
- Spec no longer contradicts expected Kapitel 3 ... Kapitel 26 order.
- No remaining lexical-order clauses survive in parent spec.

### Task 2 — Add one native Windows sorter in merge engine
**Scope**
- Touch Tools/src/glist_pipeline/merge_audio.py.
- Keep diff minimal.

**Steps**
1. Add one helper such as sort_audio_files(paths).
2. On Windows, use native StrCmpLogicalW via stdlib ctypes plus unctools.cmp_to_key.
3. Add explicit fallback inside same helper: when runtime is not Windows, use stable plain-name sort.
4. Use helper inside collect_source_files().
5. Remove second sorted(...) call from uild_merge_plan().
6. Do not add regex chapter-specific sorting.

**Rules**
- One ordering rule owner only.
- No mode-specific ordering.
- No Kapitel special-case.
- Boundary owns order; merge executor stays order-agnostic.
- Platform difference is explicit and isolated inside one helper only.

**Verification**
- Exactly one sorter remains in merge pipeline.
- uild_merge_plan() preserves caller-provided order.
- Non-Windows fallback behavior is explicit and executable.

### Task 3 — Lock behavior with focused tests
**Scope**
- Touch Tools/tests/test_merge_audio.py.

**Steps**
1. Replace lexical-order expectation tests with logical-order expectation tests.
2. Add regression fixture for names like:
   - Kapitel 3
   - Kapitel 10
   - Kapitel 26
3. Add regression proving collect_source_files() returns Windows-logical order.
4. Add regression proving uild_merge_plan() does not re-sort input.
5. Add regression for non-Windows fallback by monkeypatching platform detection if branch is reachable without real non-Windows runtime.

**Verification**
- Test proves Kapitel 3 comes before Kapitel 10.
- Test proves final item becomes Kapitel 26 for supplied sample set.
- Test proves fallback branch remains stable and centralized.

### Task 4 — Rebuild and smoke-test corrected merge order
**Scope**
- Verification only unless build scripts need touch.

**Steps**
1. Run focused merge tests.
2. Rebuild onedir exe.
3. Run merge smoke on representative chapter filenames.
4. Preserve order evidence explicitly during smoke:
   - run with --keep-temp-files, or
   - use test seam that keeps concat.txt long enough to inspect
5. Confirm order from retained concat.txt manifest, not by listening guesswork.

**Verification**
- Focused pytest passes.
- Rebuilt dist/GermanListeningCLI/GermanListeningCLI.exe launches.
- Retained concat.txt shows Kapitel 26 last when expected.

## Design Constraints
- Use native Windows ordering before custom heuristics.
- Keep one sorter only.
- No chapter-specific parser.
- No broad refactor outside merge order boundary.
- Smallest safe diff wins.

## Risks and Mitigations
- **Risk:** logical sort exists in two places after patch.
  - **Mitigation:** order only in collect_source_files(), never in plan builder.

- **Risk:** tests still lock lexical behavior by accident.
  - **Mitigation:** replace old assumptions with native logical-order assertions.

- **Risk:** non-Windows environments differ or crash on native API access.
  - **Mitigation:** keep platform branch explicit inside one helper and provide stable plain-name fallback there.

- **Risk:** smoke check loses evidence because stage files auto-delete.
  - **Mitigation:** retain concat.txt intentionally during smoke and inspect artifact directly.

## Verification
- proof target: spec and code agree on one ordering rule
  - method: review and test
  - evidence: one sorter helper and updated spec wording across lexical-order clauses

- proof target: filenames sort in native Windows logical order
  - method: test
  - evidence: Kapitel 3, Kapitel 10, Kapitel 26 regression

- proof target: marker and no-marker paths share same order
  - method: test
  - evidence: plan-builder test preserves incoming order for both modes

- proof target: non-Windows branch is explicit and safe
  - method: test
  - evidence: single helper fallback path with stable plain-name behavior

- proof target: rebuilt exe preserves corrected behavior
  - method: smoke
  - evidence: retained concat.txt manifest shows expected final order

## Completion Criteria
- Spec says Windows logical filename order at boundary.
- Merge engine has one SSOT sorter.
- Duplicate sort removed.
- Tests lock natural order.
- Rebuilt exe passes merge-order smoke with retained manifest evidence.

## Rollback Note
If native logical sort call proves unstable, keep single helper boundary and swap implementation there only. Do not reintroduce duplicate lexical sorting in plan builder.

## Next Handoff
Execute patch directly.
