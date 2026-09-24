from __future__ import annotations

import ctypes
from dataclasses import dataclass
from functools import cmp_to_key
import os
import shutil
import subprocess
from pathlib import Path

from .runtime_paths import get_repo_root

REPO_ROOT = get_repo_root()
ADMISSIBLE_EXTENSIONS = {".mp3", ".wav", ".m4a"}
DEFAULT_INPUT_DIR = Path("Audios") / "Merge"
DEFAULT_OUTPUT_DIR = Path("Outputs") / "Merge"
DEFAULT_MARKER_OUTPUT = DEFAULT_OUTPUT_DIR / "merged-with-markers.mp3"
DEFAULT_PLAIN_OUTPUT = DEFAULT_OUTPUT_DIR / "merged.mp3"
DEFAULT_PROMPT_DIR = Path("Audios") / "MergePrompts"
DEFAULT_INTRO_TEMPLATE = "Teil {0}"
DEFAULT_OUTRO_TEMPLATE = "Ende des Teil {0}"
DEFAULT_BITRATE_KBPS = 192
GERMAN_VOICE_PATTERNS = ("German", "Deutsch", "de-DE", "de_DE")


@dataclass(frozen=True)
class Segment:
    kind: str
    part_number: int
    source_path: Path | None = None
    text: str | None = None


def resolve_repo_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


if os.name == "nt":
    _STRCMP_LOGICAL = ctypes.windll.shlwapi.StrCmpLogicalW
    _STRCMP_LOGICAL.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    _STRCMP_LOGICAL.restype = ctypes.c_int
else:
    _STRCMP_LOGICAL = None


def _plain_name_compare(left: Path, right: Path) -> int:
    if left.name < right.name:
        return -1
    if left.name > right.name:
        return 1
    if str(left) < str(right):
        return -1
    if str(left) > str(right):
        return 1
    return 0


def _compare_audio_files(left: Path, right: Path) -> int:
    if _STRCMP_LOGICAL is None:
        return _plain_name_compare(left, right)
    result = _STRCMP_LOGICAL(left.name, right.name)
    if result != 0:
        return result
    return _plain_name_compare(left, right)


def sort_audio_files(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=cmp_to_key(_compare_audio_files))


def collect_source_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    files = sort_audio_files([
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in ADMISSIBLE_EXTENSIONS
    ])
    if not files:
        raise ValueError(f"No audio files found in {input_dir}")
    return files


def build_merge_plan(
    source_files: list[Path],
    *,
    markers: str,
    intro_template: str = DEFAULT_INTRO_TEMPLATE,
    outro_template: str = DEFAULT_OUTRO_TEMPLATE,
) -> list[Segment]:
    plan: list[Segment] = []
    for index, source_path in enumerate(source_files, start=1):
        if markers == "with":
            plan.append(Segment("prompt_intro", index, text=intro_template.format(index)))
        plan.append(Segment("source", index, source_path=source_path))
        if markers == "with":
            plan.append(Segment("prompt_outro", index, text=outro_template.format(index)))
    return plan


def resolve_recorded_prompt_clip(prompt_dir: Path, part_number: int, kind: str) -> Path:
    file_name = f"teil_{part_number}.mp3" if kind == "prompt_intro" else f"ende_des_teil_{part_number}.mp3"
    path = prompt_dir / file_name
    if not path.exists():
        raise FileNotFoundError(f"Recorded prompt file not found: {path}")
    return path


def select_sapi_voice(voices: list[str], requested_voice_name: str = "") -> str:
    if not voices:
        raise ValueError("No SAPI voices are installed.")
    if requested_voice_name:
        for voice in voices:
            if requested_voice_name.lower() in voice.lower():
                return voice
        available = "; ".join(voices)
        raise ValueError(f"Requested voice '{requested_voice_name}' was not found. Available voices: {available}")
    for voice in voices:
        if any(pattern.lower() in voice.lower() for pattern in GERMAN_VOICE_PATTERNS):
            return voice
    available = "; ".join(voices)
    raise ValueError(f"No German SAPI voice is installed. Available voices: {available}")


def powershell_command(script: str) -> list[str]:
    return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]


def list_sapi_voices() -> list[str]:
    command = powershell_command(
        ""
        "$voice = New-Object -ComObject SAPI.SpVoice;"
        "try {"
        "  foreach ($item in $voice.GetVoices()) { $item.GetDescription() }"
        "} finally {"
        "  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice)"
        "}"
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Failed to list SAPI voices."
        raise RuntimeError(message)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def assert_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("Required command 'ffmpeg' was not found on PATH.")


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"ffmpeg failed with exit code {result.returncode}"
        raise RuntimeError(message)


def write_concat_manifest(stage_dir: Path, staged_paths: list[Path]) -> Path:
    manifest = stage_dir / "concat.txt"
    lines = ["file '{}'".format(str(path).replace("'", "''")) for path in staged_paths]
    manifest.write_text("\n".join(lines) + "\n", encoding="ascii")
    return manifest


def generate_prompt_wav(target_wave: Path, text: str, requested_voice_name: str) -> None:
    requested = requested_voice_name.replace("'", "''")
    escaped_text = text.replace("'", "''")
    command = powershell_command(
        ""
        f"$requested = '{requested}';"
        f"$spoken = '{escaped_text}';"
        f"$target = '{target_wave}';"
        "$voice = New-Object -ComObject SAPI.SpVoice;"
        "try {"
        "  $voices = @($voice.GetVoices());"
        "  if ($voices.Count -eq 0) { throw 'No SAPI voices are installed.' }"
        "  $selected = $null;"
        "  if ($requested) {"
        "    foreach ($item in $voices) {"
        "      $description = $item.GetDescription();"
        "      if ($description -like \"*$requested*\") { $selected = $item; break }"
        "    }"
        "    if (-not $selected) {"
        "      $available = ($voices | ForEach-Object { $_.GetDescription() }) -join '; ';"
        "      throw \"Requested voice '$requested' was not found. Available voices: $available\""
        "    }"
        "  } else {"
        "    foreach ($item in $voices) {"
        "      $description = $item.GetDescription();"
        "      if ($description -match 'German|Deutsch|de-DE|de_DE') { $selected = $item; break }"
        "    }"
        "    if (-not $selected) {"
        "      $available = ($voices | ForEach-Object { $_.GetDescription() }) -join '; ';"
        "      throw \"No German SAPI voice is installed. Available voices: $available\""
        "    }"
        "  }"
        "  $stream = New-Object -ComObject SAPI.SpFileStream;"
        "  try {"
        "    $null = $voice.Voice = $selected;"
        "    $stream.Open($target, 3, $true);"
        "    $voice.AudioOutputStream = $stream;"
        "    $null = $voice.Speak($spoken);"
        "  } finally {"
        "    try { $stream.Close() } catch {}"
        "    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($stream)"
        "  }"
        "} finally {"
        "  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice)"
        "}"
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Failed to generate prompt audio."
        raise RuntimeError(message)


def convert_to_stage_mp3(source_file: Path, target_file: Path, bitrate_kbps: int) -> None:
    run_ffmpeg([
        "-y",
        "-i",
        str(source_file),
        "-vn",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        f"{bitrate_kbps}k",
        str(target_file),
    ])


def resolve_generated_prompt_clip(
    *,
    stage_dir: Path,
    part_number: int,
    kind: str,
    text: str,
    bitrate_kbps: int,
    requested_voice_name: str,
) -> Path:
    stem = "intro" if kind == "prompt_intro" else "outro"
    wave_path = stage_dir / f"{stem}_{part_number:02d}.wav"
    mp3_path = stage_dir / f"{stem}_{part_number:02d}.mp3"
    generate_prompt_wav(wave_path, text, requested_voice_name)
    convert_to_stage_mp3(wave_path, mp3_path, bitrate_kbps)
    wave_path.unlink(missing_ok=True)
    return mp3_path


def stage_segment(
    item: Segment,
    stage_dir: Path,
    bitrate_kbps: int,
    *,
    prompt_mode: str = "generated",
    prompt_dir: Path | None = None,
    voice_name: str = "",
) -> Path:
    if item.kind == "source":
        if item.source_path is None:
            raise ValueError("Source segment is missing source_path.")
        staged = stage_dir / f"source_{item.part_number:02d}.mp3"
        convert_to_stage_mp3(item.source_path, staged, bitrate_kbps)
        return staged
    if prompt_mode == "recorded":
        if prompt_dir is None:
            raise ValueError("Recorded prompt mode requires prompt_dir.")
        source = resolve_recorded_prompt_clip(prompt_dir, item.part_number, item.kind)
        staged = stage_dir / f"{item.kind}_{item.part_number:02d}.mp3"
        convert_to_stage_mp3(source, staged, bitrate_kbps)
        return staged
    if item.text is None:
        raise ValueError("Prompt segment is missing text.")
    return resolve_generated_prompt_clip(
        stage_dir=stage_dir,
        part_number=item.part_number,
        kind=item.kind,
        text=item.text,
        bitrate_kbps=bitrate_kbps,
        requested_voice_name=voice_name,
    )


def merge_audio(
    *,
    input_dir: Path,
    output_file: Path,
    markers: str,
    prompt_mode: str = "generated",
    prompt_dir: Path | None = None,
    voice_name: str = "",
    bitrate_kbps: int = DEFAULT_BITRATE_KBPS,
    intro_template: str = DEFAULT_INTRO_TEMPLATE,
    outro_template: str = DEFAULT_OUTRO_TEMPLATE,
    keep_temp_files: bool = False,
) -> Path:
    assert_ffmpeg_available()
    if markers not in {"with", "without"}:
        raise ValueError("markers must be 'with' or 'without'.")
    if markers == "with" and prompt_mode == "generated":
        select_sapi_voice(list_sapi_voices(), requested_voice_name=voice_name)
    resolved_input = resolve_repo_path(input_dir)
    resolved_output = resolve_repo_path(output_file)
    resolved_prompt_dir = resolve_repo_path(prompt_dir) if prompt_dir is not None else None
    sources = collect_source_files(resolved_input)
    plan = build_merge_plan(
        sources,
        markers=markers,
        intro_template=intro_template,
        outro_template=outro_template,
    )
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    stage_dir = resolved_output.parent / "_merge_stage"
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    try:
        staged_paths = [
            stage_segment(
                item,
                stage_dir,
                bitrate_kbps,
                prompt_mode=prompt_mode,
                prompt_dir=resolved_prompt_dir,
                voice_name=voice_name,
            )
            for item in plan
        ]
        manifest = write_concat_manifest(stage_dir, staged_paths)
        run_ffmpeg([
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-c",
            "copy",
            str(resolved_output),
        ])
        return resolved_output
    finally:
        if not keep_temp_files and stage_dir.exists():
            shutil.rmtree(stage_dir)


def merge_audio_from_args(args) -> Path:
    if getattr(args, "list_voices", False):
        voices = list_sapi_voices()
        for voice in voices:
            print(voice)
        return Path()
    return merge_audio(
        input_dir=Path(args.input_dir),
        output_file=Path(args.output_file),
        markers=args.markers,
        prompt_mode=args.prompt_mode,
        prompt_dir=Path(args.prompt_dir) if args.prompt_dir else None,
        voice_name=args.voice_name,
        bitrate_kbps=args.bitrate_kbps,
        keep_temp_files=args.keep_temp_files,
    )
