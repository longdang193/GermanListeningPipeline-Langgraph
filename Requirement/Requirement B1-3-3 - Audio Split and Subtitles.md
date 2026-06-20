---
aliases: []
time: 2026-04-07-12-23-45
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

This requirement runs **after** the Markdown output file has been validated per **Requirement B1-3-2**.

It uses a Python tool (`split_and_subtitle.py`) to **split the source audio** into per-block clips and **generate SRT subtitle files** with sentence-level entries.

## Prerequisites

* **Requirement B1-3-1** completed — `Outputs\Listening-generated.md` exists with all fields populated (including `de_1_audio`, `de_1_wave`, `de_1_start`, `de_1_end`).
* **Requirement B1-3-2** passed — the validation check confirms the generated file is correct.
* **ffmpeg** installed and available on PATH.

---

## B1-3-3.1 — Run the validator first

Before splitting, confirm the generated file passes all checks:

```powershell
cd "C:\Users\HOANG PHI LONG DANG\repos\German_Listening"
.venv\Scripts\python.exe Requirement\check_listening_2.py Outputs\Listening-generated.md
```

**Proceed only if all checks PASS.** Fix any failures before continuing.

---

## B1-3-3.2 — Split audio and generate subtitles

Run the splitter tool:

```powershell
.venv\Scripts\python.exe Requirement\split_and_subtitle.py Outputs\Listening-generated.md
```

### What the tool does

1. **Parses** all `SSTART ... EEND` blocks from the generated Markdown.
2. **Detects** the source audio file from the `de_1_wave` field (resolved under `Audios\`).
3. **Splits** the audio into one `.mp3` clip per block using `de_1_start` / `de_1_end` as cut points (via ffmpeg).
4. **Generates** one `.srt` subtitle file per block with sentence-level entries:
   * Sentences are derived from `<br>`-separated segments in `de_1`.
   * Each sentence's start/end comes from the `data-start` / `data-end` of its first/last `<span>`.
   * Timestamps are **relative to the clip** (starting from `00:00:00`), not the original audio.

### Output location

All files are written to `Outputs\Youtube\`.

### Output naming convention

Files are numbered sequentially with a descriptive suffix derived from the heading:

| Block range | Naming pattern | Example |
|---|---|---|
| Teil 1 (Aufgabe 41–45) | `NN_Teil1_AufgabeXX` | `01_Teil1_Aufgabe41.mp3` / `.srt` |
| Teil 2 (Q&A 1–N) | `NN_Teil2_QandA_X` | `06_Teil2_QandA_1.mp3` / `.srt` |
| Teil 3 (Aufgabe 56–60) | `NN_Teil3_AufgabeXX` | `16_Teil3_Aufgabe56.mp3` / `.srt` |

### Expected output

For 20 blocks: **40 files** total — 20 `.mp3` audio clips + 20 `.srt` subtitle files.

The tool prints progress for each block and a final summary:

```
🎉 ALL DONE — 20 audio clips + 20 subtitle files
```

**FAIL** if ffmpeg errors occur or no sentences can be extracted from any block.

---

## B1-3-3.3 — Verify output

After the tool completes, confirm:

1. **File count**: `Outputs\Youtube\` contains the expected number of `.mp3` and `.srt` files (equal to the number of blocks × 2).
2. **Audio playback**: spot-check at least one clip from each Teil to confirm the audio content matches the block.
3. **Subtitle alignment**: open a `.srt` file alongside its `.mp3` clip and verify that sentence timestamps align with the spoken audio.
