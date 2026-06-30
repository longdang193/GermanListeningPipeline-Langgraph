---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: semantic-filter-finalize-output
parent_workstream: none
targets:
  - Tools/src/glist_pipeline/semantic_generate.py
  - Tools/src/glist_pipeline/cli.py
  - Tools/src/glist_pipeline/quality_gate.py
  - Tools/tests/test_semantic_generate.py
  - Tools/tests/test_cli_menu.py
related_features:
  - semantic-output-quality
related_stages:
  - action1-block-generation
---

# Semantic Filter and Finalize Output Patch Spec

## Goal
Fix two semantic-route content failures:
- placeholder `en_1` and `note_1` content should not appear in final output file
- exam instruction and repeated playback scaffolding should not be included as learning-content sentences in generated semantic blocks

## Key Deliverables
1. Semantic route writes a reviewable draft artifact separately from final artifact.
2. Final `Outputs/Listening-generated.md` is only written after postprocess and quality gate pass.
3. Semantic route filters instruction sentences before block generation.
4. This patch preserves repeated real exercise content; it does not deduplicate replayed listening content yet.
5. Focused tests prove instruction filtering, draft/final separation, and no-placeholder finalization.

## Task/Wave Breakdown

### Wave 1 — Separate Draft From Final
- Stop treating semantic draft file as final user-facing output.
- Introduce semantic draft output path for review-stage content.
- Keep final output path as canonical postprocess output only.

### Wave 2 — Filter Non-Learning Sentences
- Add rule-based instruction sentence filter before block splitting.
- Apply filtering on full sentence units produced by existing punctuation-based sentence splitter.
- Preserve repeated real listening content in this patch.

### Wave 3 — Finalize Only On Success
- Ensure guided-review semantic route does not overwrite final file with placeholder content.
- Only promote semantic draft to final path after enrichment succeeds and quality gate passes.
- If postprocess fails, retain draft for debugging/review and leave final file untouched.

### Wave 4 — Verification
- Add focused regression tests for semantic filtering and output promotion behavior.
- Run focused pytest subset.

## Design Decisions
1. **Rule-based filter, not LLM classifier**
   - Use small deterministic instruction-pattern matching.
   - Reason: shortest diff, reproducible, no extra runtime dependency.

2. **Draft/final separation is root-cause fix**
   - Placeholder text currently exists by design in semantic draft generation.
   - User confusion happens because draft is written directly to final path too early.
   - Separate paths fix this at source.

3. **Filter before split, not after render**
   - Remove bad sentences before block formation.
   - Reason: dropping after render still leaves wrong block boundaries.

4. **Instruction filtering uses one explicit SSOT helper**
   - Filter through one helper such as `is_instruction_sentence(text: str) -> bool`.
   - Input is normalized whole-sentence text.
   - Matching is anchored to known exam-scaffold openings, not loose substring matching.
   - Reason: prevents divergent ad hoc filtering and protects real content like `Achtung, Autofahrer...`.

5. **Keep existing semantic splitter thresholds**
   - No duration-threshold changes in this patch.
   - Reason: current issue is bad input sentence set, not timing math.

## Invariants
- Final published listening markdown must not contain TODO placeholder text.
- Semantic route must continue to accept explicit transcript/audio path inputs.
- Canonical final output path remains `Outputs/Listening-generated.md`.
- Guided review may inspect draft content, but final output must only reflect passed postprocess content.
- Filtering operates on full sentence units from current punctuation splitter; mixed sentences are retained unless they begin with scaffold patterns.
- Marker/classic routes remain behaviorally unchanged except for any shared finalization wiring that is strictly required.

## Acceptance Criteria
1. After semantic guided-review run completes successfully, `Outputs/Listening-generated.md` contains no `TODO: add English translation.`, `TODO_TERM_*`, or `TODO_GRAMMAR_*` content.
2. Semantic draft content is stored at `Outputs/Listening-generated.draft.md`; final content is stored at `Outputs/Listening-generated.md`.
3. Each run overwrites draft output.
4. Final output is promoted only after enrichment and quality gate pass on the draft artifact.
5. If enrichment or quality gate fails, final output remains unchanged from prior successful run.
6. Leading exam instructions like `Zertifikat B1`, `Hören Teil eins`, `Sie hören nun ...`, `Lesen Sie ...`, `Wählen Sie ...`, `Dazu haben Sie ...` are excluded from semantic block content.
7. Repeated real exercise content is preserved in this patch.
8. Focused tests pass.

## Non-Goals
- No LLM-based instruction classifier.
- No replayed-content dedup in this patch.
- No broad repetition-dedup over whole transcript.
- No semantic duration-threshold tuning in this patch.
- No rework of marker/classic generation logic.
- No new config file for instruction patterns yet.

## Risks and Mitigations

### Risk 1 — Filter removes real content
- Mitigation:
  - keep pattern list narrow and exam-scaffold specific
  - use anchored normalized openings, not broad substring matches
  - add regression fixtures with preserved real content, including negative example `Achtung, Autofahrer...`

### Risk 2 — Draft/final split breaks review flow
- Mitigation:
  - keep guided-review stage pointed at draft artifact
  - only promote to final after postprocess success
  - print draft and final paths clearly

### Risk 3 — Shared code path accidentally changes marker/classic behavior
- Mitigation:
  - keep semantic-specific output path logic isolated where possible
  - add tests only for semantic lane and inspect unchanged routes

## Validation Plan
- proof target: semantic route filters known instruction sentences
  - method: test
  - evidence: focused pytest fixture with exact assertions that dropped instruction lines do not appear in `de_1`

- proof target: semantic route keeps real content sentences
  - method: test
  - evidence: focused pytest fixture with exact assertion that first retained dialogue sentence remains in output

- proof target: semantic route does not rely on final path for draft placeholders
  - method: test
  - evidence: focused pytest covering fixed draft path `Outputs/Listening-generated.draft.md` and separate final artifact

- proof target: final output contains no placeholder bans after success
  - method: test
  - evidence: quality-gate or direct banned-pattern assertion against final file

- proof target: failed postprocess does not overwrite final output
  - method: test
  - evidence: pre-seeded final file remains unchanged when postprocess simulated failure occurs

## Completion Criteria
- Semantic draft path exists at `Outputs/Listening-generated.draft.md` and is used for pre-postprocess review content.
- Final path promotion occurs only after successful postprocess and quality gate on draft.
- Instruction filtering is implemented before block splitting through one SSOT helper.
- Focused regression tests pass.

## Suggested Patch Shape
- `Tools/src/glist_pipeline/semantic_generate.py`
  - add `is_instruction_sentence()` helper as instruction-filter SSOT
  - add filtered sentence preparation step before `split_into_blocks()`
  - accept optional output path override for draft/final separation
- `Tools/src/glist_pipeline/cli.py`
  - direct semantic guided-review runs to fixed draft path `Outputs/Listening-generated.draft.md`
  - run postprocess and quality gate on draft
  - promote draft to final path only after success
  - keep review messaging honest about draft vs final
- `Tools/tests/test_semantic_generate.py`
  - add instruction-filter test with exact dropped/kept sentence assertions
- `Tools/tests/` adjacent CLI test
  - add draft/final promotion test
  - add failed-postprocess-keeps-old-final test

## Open Questions
- Should filtered instruction sentences be logged for audit?
  - recommended now: no, unless debugging output becomes necessary

## Handoff
After approval, hand off to implementation-plan drafting. Do not implement from this spec directly in this skill.
