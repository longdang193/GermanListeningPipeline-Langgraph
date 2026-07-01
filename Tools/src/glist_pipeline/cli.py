from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
import unicodedata
import json
from typing import Literal

from . import langgraph_app
from .hitl import DecisionAction, HitlEngine, append_review_log
from .labels import load_taxonomy
from .models import LabelSuggestion
from .modes import classic, marker
from .suggest_boundaries import suggest_boundaries
from .apply_boundary_suggestions import apply_boundary_suggestions, load_latest_suggestions
from .mode_router import append_router_run_record, detect_transcript_profile, route_mode
from .semantic_generate import OUTPUT_DRAFT as SEMANTIC_DRAFT_MD, OUTPUT_FINAL as SEMANTIC_FINAL_MD, generate_semantic
from .enrich_llm import enrich_file_in_place
from .quality_gate import BANNED, find_quality_issues
from .markdown import parse_markdown, render_document
from .runtime_paths import get_repo_root

REPO_ROOT = get_repo_root()
OUTPUT_MD = SEMANTIC_FINAL_MD

Mode = Literal["marker", "classic", "hitl"]

MODE_ALIASES: dict[str, Mode] = {
    "1": "marker",
    "daf": "marker",
    "daf b1": "marker",
    "marker-based": "marker",
    "marker": "marker",
    "2": "classic",
    "telc": "classic",
    "telc b1": "classic",
    "classic-based": "classic",
    "classic": "classic",
    "3": "hitl",
    "agent": "hitl",
    "agentic": "hitl",
    "agent suggestion": "hitl",
    "agent suggestions": "hitl",
    "guided review": "hitl",
    "guided": "hitl",
    "suggestions": "hitl",
    "hitl": "hitl",
}


def _load_env_file_if_present(path: Path) -> None:
    if not path.exists():
        return
    import os

    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def _mode_impl(mode: str):
    return classic if mode == "classic" else marker


def _display_mode_name(mode: Mode) -> str:
    if mode == "marker":
        return "DAF B1"
    if mode == "classic":
        return "TELC B1"
    return "Guided review"


def _route_label(routed: str) -> str:
    labels = {
        "marker": "marker-based",
        "classic": "classic-based",
        "semantic": "semantic fallback",
    }
    return labels.get(routed, routed)


def _route_reason(selected_mode: Mode, routed: str, profile_reason: str) -> str:
    if routed == "marker":
        return "transcript contains marker anchors."
    if routed == "classic":
        return "classic mode chosen."
    if routed == "semantic":
        return "transcript has no marker anchors, so app uses timing/sentence-based splitting."
    return profile_reason


def _set_latest(path: Path) -> None:
    from datetime import datetime
    import os

    ts = datetime.now().timestamp()
    path.touch(exist_ok=True)
    path.chmod(path.stat().st_mode)
    os.utime(path, (ts, ts))


def _append_boundary_hitl_log(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _boundary_method_stats(evidence_path: Path) -> dict[str, int]:
    if not evidence_path.exists():
        return {"llm": 0, "rule_fallback": 0, "unknown": 0}
    llm = 0
    fallback = 0
    unknown = 0
    for line in evidence_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            method = ((row.get("selected") or {}).get("method") or "unknown").strip()
            if method == "llm":
                llm += 1
            elif method == "rule_fallback":
                fallback += 1
            else:
                unknown += 1
        except Exception:
            unknown += 1
    return {"llm": llm, "rule_fallback": fallback, "unknown": unknown}


def _run_boundary_hitl_for_uncertain(md_path: Path, evidence_path: Path) -> int:
    rows = load_latest_suggestions(evidence_path)
    uncertain = sorted([h for h, row in rows.items() if row.uncertain and row.selected_index is not None])
    if not uncertain:
        print("Boundary HITL: no uncertain boundary suggestions")
        return 0

    print(f"Boundary HITL: uncertain blocks found = {len(uncertain)}")
    print("1) accept (apply uncertain suggestions)")
    print("2) regenerate (rerun suggestion once)")
    print("3) discard (keep deterministic boundaries)")
    print("4) manual_select (choose headings to apply)")
    choice = input("Choose [1/2/3/4]: ").strip()

    action_map = {"1": "accept", "2": "regenerate", "3": "discard", "4": "manual_select"}
    action = action_map.get(choice)
    if action is None:
        print("Boundary HITL: invalid choice")
        return 1

    selected_headings: set[str] = set()
    if action == "manual_select":
        print("Uncertain headings:", ", ".join(uncertain))
        raw = input("Enter headings to apply (comma-separated): ").strip()
        selected_headings = {x.strip() for x in raw.split(",") if x.strip()}
        unknown = sorted(selected_headings - set(uncertain))
        if unknown:
            print(f"Boundary HITL: unknown heading(s): {', '.join(unknown)}")
            return 1

    if action == "regenerate":
        suggest_boundaries(md_path, evidence_path=evidence_path)
        rows = load_latest_suggestions(evidence_path)
        uncertain = sorted([h for h, row in rows.items() if row.uncertain and row.selected_index is not None])
        print(f"Boundary HITL: regenerate complete, uncertain={len(uncertain)}")
        action = "discard"

    if action == "accept":
        apply_boundary_suggestions(md_path, evidence_path=evidence_path, apply_uncertain=True)
    elif action == "manual_select":
        apply_boundary_suggestions(md_path, evidence_path=evidence_path, apply_headings=selected_headings)

    method_stats = _boundary_method_stats(evidence_path)
    _append_boundary_hitl_log(
        REPO_ROOT / "Outputs" / "review_logs" / "boundary_hitl.jsonl",
        {
            "event": "boundary_hitl_decision",
            "action": action,
            "uncertain_count": len(uncertain),
            "selected_headings": sorted(selected_headings),
            "method_stats": method_stats,
        },
    )
    return 0


def _detect_blocks_mode(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    if "Teil 2 — Q&A" in text or "Aufgabe 41" in text or "Aufgabe 56" in text:
        return "classic"
    if re.search(r"^## Abschnitt \d+\s+—\s+", text, flags=re.MULTILINE):
        return "semantic"
    return "marker"


def _split_mode_for_blocks_mode(mode: str) -> str:
    return "classic" if mode in {"classic", "semantic"} else "marker"

def _ensure_repo_audio(source: Path) -> Path:
    target = REPO_ROOT / "Audios" / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target

def _get_first_block_wave_name(md_path: Path) -> str:
    doc = parse_markdown(md_path.read_text(encoding="utf-8"))
    if not doc.blocks:
        return ""
    return Path(doc.blocks[0].fields.get("de_1_wave", "").strip()).name

def _prompt_optional_path(prompt: str) -> Path | None:
    raw = input(prompt).strip()
    if not raw:
        return None
    return _repair_console_path(raw)

def _ensure_blocks_audio_available(blocks_path: Path) -> int:
    wave_name = _get_first_block_wave_name(blocks_path)
    if not wave_name:
        return 0
    target = REPO_ROOT / "Audios" / wave_name
    if target.exists():
        return 0
    print(f"Audio source missing: {target}")
    source = _prompt_optional_path("Original audio path [blank=cancel]: ")
    if source is None:
        print("Action cancelled.")
        return 1
    if not source.exists():
        print(f"Audio not found: {source}")
        return 1
    shutil.copyfile(source, target)
    print(f"Copied audio into repo cache: {target}")
    return 0

def _run_shared_postprocess(md_path: Path) -> int:
    print("Enrichment started...")
    print("LLM translations and notes may take a while.")
    print(f"Postprocess: enriching {md_path.name}...")
    enrich_file_in_place(md_path)
    print("Enrichment complete. Running placeholder check...")
    print("Postprocess: enrichment complete. Running placeholder check...")
    hits = find_quality_issues(md_path)
    if hits:
        print("Postprocess failed: placeholder content remains")
        for pattern, value in hits:
            print(f" - {pattern}: {value}")
        return 2
    return 0

def _promote_output(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

_SPAN_RE = re.compile(r"<span\s+data-start=\"[\d.]+\"\s+data-end=\"[\d.]+\">([^<]*)</span>")


def _extract_de_sentences_from_de1(de_1: str) -> list[str]:
    lines = [x.strip() for x in re.split(r"\s*<br>\s*", de_1.strip()) if x.strip()]
    out: list[str] = []
    for line in lines:
        tokens = [m.group(1).strip() for m in _SPAN_RE.finditer(line)]
        if tokens:
            out.append(" ".join(tokens).strip())
    return out


def _normalize_telc_blocks_from_de_ssot(md_path: Path) -> None:
    doc = parse_markdown(md_path.read_text(encoding="utf-8"))
    changed = False
    placeholder_note = (
        "<b>Key Words and Phrases</b><br>"
        "• <b>TODO_TERM_1</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_2</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_3</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_4</b> — Add glossary note.<br>"
        "• <b>TODO_TERM_5</b> — Add glossary note.<br><br>"
        "<b>Grammar to Remember</b><br>"
        "• <b>TODO_GRAMMAR_1</b> — Add grammar explanation.<br>"
        "• <b>TODO_GRAMMAR_2</b> — Add grammar explanation.<br>"
        "• <b>TODO_GRAMMAR_3</b> — Add grammar explanation."
    )

    for block in doc.blocks:
        de_sentences = _extract_de_sentences_from_de1(block.fields.get("de_1", ""))
        if not de_sentences:
            continue
        block.fields["en_1"] = "<br>".join(
            f"<b>{s}</b> — TODO: add English translation." for s in de_sentences
        )
        block.fields["note_1"] = placeholder_note
        changed = True

    if changed:
        md_path.write_text(render_document(doc.blocks), encoding="utf-8")
def _run_action_create_blocks(transcript_path: Path, audio_path: Path, mode: Mode) -> int:
    if not transcript_path.exists():
        print(f"Transcript not found: {transcript_path}")
        return 1
    if not audio_path.exists():
        print(f"Audio not found: {audio_path}")
        return 1

    print(f"Transcript file: {transcript_path}")
    print(f"Audio file: {audio_path}")

    repo_audio = _ensure_repo_audio(audio_path)
    if repo_audio != audio_path:
        print(f"Cached audio for later splitting: {repo_audio}")

    _set_latest(transcript_path)
    _set_latest(repo_audio)

    print("Checking transcript profile...")
    profile = detect_transcript_profile(transcript_path)
    requested_mode = "guided_review" if mode == "hitl" else mode

    try:
        routed = route_mode(mode, profile)
    except ValueError as exc:
        msg = str(exc)
        if msg == "marker_mode_unavailable_for_transcript":
            print("Mode router: DAF B1 mode unavailable for this transcript (no marker anchors).")
            print("Use TELC B1 or Guided review mode.")
        else:
            print(f"Mode router failed: {msg}")
        append_router_run_record(
            REPO_ROOT / "Outputs" / "review_logs" / "mode_router_runs.jsonl",
            {
                "requested_mode": requested_mode,
                "routed_mode": None,
                "profile": profile.__dict__,
                "outcome": "route_error",
                "transcript": str(transcript_path),
                "audio": str(audio_path),
            },
        )
        return 1

    print(f"Route selected: {_route_label(routed)}")
    print(f"Reason: {_route_reason(mode, routed, profile.reason)}")
    print("Generating listening blocks...")

    if routed == "marker":
        rc = marker.generate()
    elif routed == "classic":
        rc = classic.generate()
    else:
        rc = generate_semantic(transcript_path=transcript_path, audio_name=audio_path.name, output_path=SEMANTIC_DRAFT_MD)

    append_router_run_record(
        REPO_ROOT / "Outputs" / "review_logs" / "mode_router_runs.jsonl",
        {
            "requested_mode": requested_mode,
            "routed_mode": routed,
            "profile": profile.__dict__,
            "outcome": "ok" if rc == 0 else f"generate_failed:{rc}",
            "transcript": str(transcript_path),
            "audio": str(audio_path),
            "output": str(SEMANTIC_DRAFT_MD if routed == "semantic" else OUTPUT_MD),
        },
    )

    if rc != 0:
        return rc

    if routed == "classic":
        _normalize_telc_blocks_from_de_ssot(OUTPUT_MD)

    if mode != "hitl":
        post = _run_shared_postprocess(OUTPUT_MD)
        if post != 0:
            append_router_run_record(
                REPO_ROOT / "Outputs" / "review_logs" / "mode_router_runs.jsonl",
                {
                    "requested_mode": requested_mode,
                    "routed_mode": routed,
                    "profile": profile.__dict__,
                    "outcome": f"postprocess_failed:{post}",
                    "transcript": str(transcript_path),
                    "audio": str(audio_path),
                    "output": str(OUTPUT_MD),
                    "quality_gate_pass": False,
                },
            )
            return post
        append_router_run_record(
            REPO_ROOT / "Outputs" / "review_logs" / "mode_router_runs.jsonl",
            {
                "requested_mode": requested_mode,
                "routed_mode": routed,
                "profile": profile.__dict__,
                "outcome": "postprocess_ok",
                "transcript": str(transcript_path),
                "audio": str(audio_path),
                "output": str(OUTPUT_MD),
                "quality_gate_pass": True,
            },
        )
        print("Postprocess complete.")
        return 0

    allowed = load_taxonomy(REPO_ROOT / "configs" / "labels.toml")
    engine = HitlEngine(allowed_ids=allowed, max_regenerations=2)
    suggestions = [
        LabelSuggestion(
            label_id="topic_daily_life",
            confidence=0.72,
            rationale="detected conversational daily scenario",
        )
    ]

    print("Review generated block plan:")
    print("1) accept  2) regenerate  3) discard  4) manual_select")
    choice = input("Choose [1/2/3/4]: ").strip()
    mapping = {
        "1": DecisionAction.ACCEPT,
        "2": DecisionAction.REGENERATE,
        "3": DecisionAction.DISCARD,
        "4": DecisionAction.MANUAL_SELECT,
    }
    action = mapping.get(choice)
    if action is None:
        print("Invalid choice. Exiting HITL step.")
        return 1

    manual_labels = None
    if action is DecisionAction.MANUAL_SELECT:
        manual_raw = input("Enter taxonomy labels (comma-separated): ").strip()
        manual_labels = [x.strip() for x in manual_raw.split(",") if x.strip()]

    decision = engine.decide(
        block_id="action1_block_creation",
        action=action,
        suggestions=suggestions,
        manual_labels=manual_labels,
        regenerate_count=0,
    )
    append_review_log(REPO_ROOT / "Outputs" / "review_logs" / "labels.jsonl", decision)

    if action is DecisionAction.REGENERATE:
        print("Regenerating once with same route...")
        print(f"Route remains: {_route_label(routed)}")
        print("If transcript and timing are unchanged, block count may stay same.")
        if routed == "marker":
            rc = marker.generate()
        elif routed == "classic":
            rc = classic.generate()
            _normalize_telc_blocks_from_de_ssot(OUTPUT_MD)
        else:
            rc = generate_semantic(transcript_path=transcript_path, audio_name=audio_path.name, output_path=SEMANTIC_DRAFT_MD)
        if rc != 0:
            return rc

    if routed == "marker":
        evidence = REPO_ROOT / "Outputs" / "review_logs" / "boundary_suggestions.jsonl"
        suggest_boundaries(OUTPUT_MD, evidence_path=evidence)
        rc = _run_boundary_hitl_for_uncertain(OUTPUT_MD, evidence)
        if rc != 0:
            return rc

    post_path = SEMANTIC_DRAFT_MD if routed == "semantic" else OUTPUT_MD
    if routed == "semantic":
        print(f"Draft path: {SEMANTIC_DRAFT_MD}")
        print(f"Final path: {OUTPUT_MD}")
    post = _run_shared_postprocess(post_path)
    if post != 0:
        append_router_run_record(
            REPO_ROOT / "Outputs" / "review_logs" / "mode_router_runs.jsonl",
            {
                "requested_mode": requested_mode,
                "routed_mode": routed,
                "profile": profile.__dict__,
                "outcome": f"postprocess_failed:{post}",
                "transcript": str(transcript_path),
                "audio": str(audio_path),
                "output": str(post_path),
                "quality_gate_pass": False,
            },
        )
        return post

    if routed == "semantic":
        _promote_output(SEMANTIC_DRAFT_MD, OUTPUT_MD)

    append_router_run_record(
        REPO_ROOT / "Outputs" / "review_logs" / "mode_router_runs.jsonl",
        {
            "requested_mode": requested_mode,
            "routed_mode": routed,
            "profile": profile.__dict__,
            "outcome": "postprocess_ok",
            "transcript": str(transcript_path),
            "audio": str(audio_path),
            "output": str(post_path),
            "quality_gate_pass": True,
        },
    )

    print("Postprocess complete.")
    print(f"HITL decision recorded: {decision.action}")
    return 0


def _run_action_create_audios_from_blocks(blocks_path: Path) -> int:
    if not blocks_path.exists():
        print("Listening blocks file not found.")
        print("1) create new listening blocks now")
        print("2) exit")
        c = input("Choose [1/2]: ").strip()
        if c == "1":
            return run_menu_action_1()
        return 0

    mode = _detect_blocks_mode(blocks_path)
    split_mode = _split_mode_for_blocks_mode(mode)
    print(f"Detected blocks mode: {mode}")
    if split_mode != mode:
        print(f"Using deterministic splitter: {split_mode}")
    audio_ready = _ensure_blocks_audio_available(blocks_path)
    if audio_ready != 0:
        return audio_ready
    return _mode_impl(split_mode).split(blocks_path)

def _repair_console_path(raw: str) -> Path:
    value = raw.strip().strip('"')
    base = Path(value)
    if not value or base.exists():
        return base

    candidates: list[str] = [value]
    for source_encoding in ("cp1252", "latin-1"):
        try:
            repaired = value.encode(source_encoding).decode("utf-8")
        except UnicodeError:
            continue
        if repaired not in candidates:
            candidates.append(repaired)

    normalized_candidates: list[str] = []
    for candidate in candidates:
        for form in ("NFC", "NFD"):
            normalized = unicodedata.normalize(form, candidate)
            if normalized not in normalized_candidates:
                normalized_candidates.append(normalized)

    for candidate in normalized_candidates:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path

    return base


def _prompt_path(prompt: str, default: Path | None = None) -> Path:
    raw = input(prompt).strip()
    if not raw and default is not None:
        return default
    return _repair_console_path(raw)

def _prompt_mode() -> Mode | None:
    print("Choose block generation mode:")
    print("1) DAF B1")
    print("2) TELC B1")
    print("3) Guided review")
    raw_mode = input("Mode [1/2/3 or name]: ").strip().lower()
    return MODE_ALIASES.get(raw_mode)


def run_menu_action_1() -> int:
    transcript = _prompt_path("Input transcript path: ")
    audio = _prompt_path("Input audio path: ")
    mode = _prompt_mode()
    if mode is None:
        print("Invalid mode.")
        return 1
    print(f"Selected mode: {_display_mode_name(mode)}")
    if mode == "hitl":
        print("Guided review chooses best available generator, then asks you to review result.")
        print("Block count is generator-based, not LLM-decided in this mode.")
    return _run_action_create_blocks(transcript, audio, mode)


def run_menu_action_2() -> int:
    default_path = OUTPUT_MD
    path = _prompt_path(f"Listening blocks path [{default_path}]: ", default_path)
    return _run_action_create_audios_from_blocks(path)


def run_menu() -> int:
    while True:
        print("German_Listening MVP")
        print("1) CREATE LISTENING BLOCKS for ANKI")
        print("2) CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS")
        print("3) EXIT")
        choice = input("Select [1/2/3]: ").strip()
        if choice == "1":
            rc = run_menu_action_1()
            if rc == 0:
                print("Action complete. Choose next action or exit.")
            else:
                print(f"Action ended with code {rc}. Choose next action or exit.")
            continue
        if choice == "2":
            rc = run_menu_action_2()
            if rc == 0:
                print("Action complete. Choose next action or exit.")
            else:
                print(f"Action ended with code {rc}. Choose next action or exit.")
            continue
        if choice == "3":
            return 0
        print("Invalid selection")


def cmd_generate(args: argparse.Namespace) -> int:
    return _mode_impl(args.mode).generate()


def cmd_validate(args: argparse.Namespace) -> int:
    return _mode_impl(args.mode).validate()


def cmd_split(args: argparse.Namespace) -> int:
    return _mode_impl(args.mode).split()


def cmd_run_all(args: argparse.Namespace) -> int:
    if cmd_generate(args) != 0:
        return 1
    if cmd_validate(args) != 0:
        print("Validation failed. Stop before split.")
        return 1
    return cmd_split(args)


def cmd_live_run(args: argparse.Namespace) -> int:
    try:
        langgraph_app.run(root=REPO_ROOT, mode=args.mode)
        return 0
    except ModuleNotFoundError as exc:
        if "langgraph" in str(exc):
            print("Missing dependency: langgraph. Install with: pip install langgraph")
            return 2
        raise


def cmd_labels(args: argparse.Namespace) -> int:
    allowed = load_taxonomy(REPO_ROOT / "configs" / "labels.toml")
    engine = HitlEngine(allowed_ids=allowed, max_regenerations=2)
    suggestions = [
        LabelSuggestion(
            label_id="topic_daily_life",
            confidence=0.9,
            rationale="contains routine dialogue",
        )
    ]
    action = DecisionAction(args.action)
    manual_labels = args.labels.split(",") if args.labels else None
    decision = engine.decide(
        block_id=args.block_id,
        action=action,
        suggestions=suggestions,
        manual_labels=manual_labels,
        regenerate_count=args.regenerate_count,
    )
    append_review_log(REPO_ROOT / "Outputs" / "review_logs" / "labels.jsonl", decision)
    print(f"Decision saved: {decision.action} for {decision.block_id} => {decision.final_labels}")
    return 0


def cmd_menu(_: argparse.Namespace) -> int:
    return run_menu()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glist")
    sub = parser.add_subparsers(dest="command", required=False)

    for name, func in (
        ("menu", cmd_menu),
        ("generate", cmd_generate),
        ("validate", cmd_validate),
        ("split", cmd_split),
        ("run-all", cmd_run_all),
        ("live-run", cmd_live_run),
    ):
        p = sub.add_parser(name)
        if name in {"generate", "validate", "split", "run-all", "live-run"}:
            p.add_argument("--mode", choices=["classic", "marker"], required=True)
        p.set_defaults(func=func)

    labels = sub.add_parser("labels")
    labels.add_argument("--action", choices=[x.value for x in DecisionAction], required=True)
    labels.add_argument("--block-id", required=True)
    labels.add_argument("--labels", default="")
    labels.add_argument("--regenerate-count", type=int, default=0)
    labels.set_defaults(func=cmd_labels)

    return parser


def main() -> None:
    _load_env_file_if_present(REPO_ROOT / ".env")
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        raise SystemExit(run_menu())
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()






