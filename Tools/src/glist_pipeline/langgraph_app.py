from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import runpy
import subprocess
import sys
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    root: str
    mode: str
    last_step: str


@dataclass(frozen=True)
class CommandStep:
    name: str
    cmd: list[str]


def _run_module_in_process(module_name: str, argv: list[str]) -> int:
    old_argv = sys.argv[:]
    try:
        sys.argv = [module_name, *argv]
        runpy.run_module(module_name, run_name="__main__")
        return 0
    except SystemExit as exc:
        code = exc.code
        if isinstance(code, int):
            return code
        return 1 if code else 0
    finally:
        sys.argv = old_argv


def _run_step(state: PipelineState, step: CommandStep) -> PipelineState:
    root = Path(state["root"])
    env = dict(__import__("os").environ)
    src_path = str(root / "Tools" / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path};{env['PYTHONPATH']}"

    if len(step.cmd) >= 3 and step.cmd[0] == sys.executable and step.cmd[1] == "-m":
        code = _run_module_in_process(step.cmd[2], step.cmd[3:])
    else:
        proc = subprocess.run(step.cmd, cwd=str(root), env=env)
        code = proc.returncode

    if code != 0:
        raise RuntimeError(f"step failed: {step.name} exit={code}")
    state["last_step"] = step.name
    return state


def _steps_for_mode(mode: str) -> list[CommandStep]:
    output_md = "Outputs/Listening-generated.md"

    if mode == "classic":
        return [
            CommandStep("classic_generate", [sys.executable, "-m", "glist_pipeline.legacy.generate_listening_2"]),
            CommandStep("classic_validate", [sys.executable, "-m", "glist_pipeline.legacy.check_listening_2", output_md]),
            CommandStep("classic_split", [sys.executable, "-m", "glist_pipeline.legacy.split_and_subtitle", output_md]),
        ]

    return [
        CommandStep("marker_generate", [sys.executable, "-m", "glist_pipeline.legacy.generate_listening_4"]),
        CommandStep("marker_suggest_boundaries", [sys.executable, "-m", "glist_pipeline.suggest_boundaries_cli", output_md]),
        CommandStep("marker_apply_boundaries", [sys.executable, "-m", "glist_pipeline.apply_boundaries_cli", output_md]),
        CommandStep("marker_enrich_llm", [sys.executable, "-m", "glist_pipeline.enrich_cli", output_md]),
        CommandStep("marker_quality_gate", [sys.executable, "-m", "glist_pipeline.quality_gate", output_md]),
        CommandStep("marker_validate", [sys.executable, "-m", "glist_pipeline.legacy.check_listening_4", output_md]),
        CommandStep("marker_split", [sys.executable, "-m", "glist_pipeline.legacy.split_and_subtitle_4", output_md]),
    ]


def build_graph(mode: str) -> Any:
    from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]

    graph = StateGraph(PipelineState)
    steps = _steps_for_mode(mode)

    for i, step in enumerate(steps):
        node_name = step.name

        def make_fn(s: CommandStep):
            def fn(st: PipelineState):
                return _run_step(st, s)

            return fn

        graph.add_node(node_name, make_fn(step))
        if i == 0:
            graph.set_entry_point(node_name)
        else:
            graph.add_edge(steps[i - 1].name, node_name)

    graph.add_edge(steps[-1].name, END)
    return graph.compile()


def run(*, root: Path, mode: str) -> None:
    app = build_graph(mode)
    init: PipelineState = {"root": str(root), "mode": mode}
    app.invoke(init)
