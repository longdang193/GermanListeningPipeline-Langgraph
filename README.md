# German Listening Pipeline LangGraph

LangGraph-based German listening MVP for generating Anki-ready listening blocks, then deterministically splitting audio and subtitles from those blocks.

## What It Does

This repo provides one CLI app with 3 actions:

1. `CREATE LISTENING BLOCKS for ANKI`
2. `CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS`
3. `EXIT`

The app supports 3 generation modes during Action 1:

- `DAF B1`
- `TELC B1`
- `agent suggestions`

`agent suggestions` is HITL lane. It lets pipeline generate suggestions and then route human review/acceptance in app flow.

## Current MVP Flow

Action 1:
- input transcript path
- input audio path
- choose mode
- generate `Outputs/Listening-generated.md`
- enrich content with LLM-backed translations/notes plus deterministic safety fallbacks

Action 2:
- read existing `Outputs/Listening-generated.md`
- split source audio into per-block `.mp3`
- generate matching `.srt`
- write outputs to `Outputs/Youtube/`

## Requirements

- Python `3.11+`
- Windows PowerShell tested
- ffmpeg available on `PATH`
- OpenAI-compatible API endpoint for enrichment

## Install

```powershell
cd Tools
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
pip install -e .
```

If you prefer explicit editable install from repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .\Tools
```

## Environment

Copy `.env.example` to `.env` and fill values:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=http://127.0.0.1:20128/v1
OPENAI_MODEL=cx/gpt-5.2
```

Notes:
- `OPENAI_BASE_URL` can point to any OpenAI-compatible endpoint
- `.env` is local only and must not be committed

## Run From Source

From repo root:

```powershell
$env:PYTHONPATH="$PWD\Tools\src"
.\.venv\Scripts\python.exe -m glist_pipeline.cli
```

Direct split commands also exist:

```powershell
$env:PYTHONPATH="$PWD\Tools\src"
.\.venv\Scripts\python.exe -m glist_pipeline.cli split --mode marker
.\.venv\Scripts\python.exe -m glist_pipeline.cli split --mode classic
```

## Build Exe

```powershell
$env:PYTHONPATH="$PWD\Tools\src"
.\.venv\Scripts\pyinstaller.exe --clean .\GermanListeningCLI.spec
```

Built app:

```text
dist/GermanListeningCLI.exe
```

## Example Menu

```text
German_Listening MVP
1) CREATE LISTENING BLOCKS for ANKI
2) CREATE AUDIOS and TRANSCRIPTS from CREATED LISTENING BLOCKS
3) EXIT
```

## Input Expectations

Transcript input:
- standard transcript JSON used by this project
- TELC B1 and DAF B1 lanes normalize from same transcript family but use different orchestration

Audio input:
- `.mp3` tested
- Unicode filenames are supported in current console flow

## Output Files

Primary generated markdown:

```text
Outputs/Listening-generated.md
```

Split artifacts:

```text
Outputs/Youtube/*.mp3
Outputs/Youtube/*.srt
```

## Repo Layout

```text
Tools/src/glist_pipeline/   main pipeline code
Requirement/                compatibility wrappers and legacy bridge scripts
configs/                    shared policy/config
docs/                       spec, plans, evidence
GermanListeningCLI.spec     PyInstaller build spec
```

## Tests

Run focused tests:

```powershell
$env:PYTHONPATH="$PWD\Tools\src"
.\.venv\Scripts\pytest.exe tests	est_generate_listening_4.py tests	est_split_run_summary.py tests	est_cli_path_repair.py tests	est_enrich_translation_fallback.py -q
```

## Notes For Fresh Clones

This public repo excludes local runtime data by design:

- `.env`
- `.venv/`
- `Audios/`
- `Transcripts/`
- `Outputs/`
- local temp logs

Add your own transcript/audio inputs locally before running Action 1.

## Status

Current public MVP includes:
- LangGraph-based listening block generation
- HITL-capable suggestion lane
- deterministic audio/subtitle split step
- Unicode console path repair
- deterministic keyword/translation safety fallbacks
