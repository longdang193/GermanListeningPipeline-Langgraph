# Boundary HITL + Apply Lane Evidence (2026-05-29)

## Scope
- Added `suggest_boundaries` + `apply_boundaries` LangGraph nodes in marker flow.
- Added Action 1 boundary HITL review for uncertain suggestions.
- Added focused tests for apply invariants.

## Runtime Flow Verified
Marker live-run command:
- `python -m glist_pipeline.cli live-run --mode marker`

Observed step outputs:
- `Boundary suggestions written: Outputs\review_logs\boundary_suggestions.jsonl`
- `Boundary apply: no block changed`
- Quality gate PASS
- Marker validator PASS
- Splitter PASS (`23 audio clips + 23 subtitle files`)

## Action 1 HITL Verified
Menu-driven run executed with `agent suggestions` mode.
Boundary HITL event persisted:
- `Outputs/review_logs/boundary_hitl.jsonl`
- latest event: `{"event":"boundary_hitl_decision","action":"discard","uncertain_count":23,"selected_headings":[]}`

Label HITL event persisted:
- `Outputs/review_logs/labels.jsonl`
- latest event includes `block_id=action1_block_creation`, `action=accept`.

## Test Evidence
Command:
- `python -m pytest tests -q`

Result:
- `15 passed`

Focused boundary tests include:
- split apply on eligible block
- heading renumber after split
- de/en line parity preservation
- no-op behavior when ineligible

## Invariance Snapshot
- `blocks=23`
- `mp3=23`
- `srt=23`
- marker validation: all checks passed

## Update: CLI Env Autoload + Boundary Method Stats
- `glist_pipeline.cli` now auto-loads `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\.env` at startup when variables are not already in process env.
- Boundary HITL log now includes method statistics from suggestion evidence (`llm`, `rule_fallback`, `unknown`).

Verification run (menu path, no pre-set `OPENAI_API_KEY` in shell):
- boundary summary: `blocks=23, uncertain=4`
- latest boundary HITL log entry includes:
  - `uncertain_count=4`
  - `method_stats={"llm":92,"rule_fallback":23,"unknown":0}`

Interpretation:
- Previous `uncertain=23` behavior was environment-path artifact.
- After env autoload, boundary suggestion quality in Action 1 path aligns with live-run path.
