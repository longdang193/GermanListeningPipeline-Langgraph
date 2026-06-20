---
aliases: []
time: 2026-04-07-23-35-00
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

## Paths

* **Transcript file (Windows)**: Use the selected JSON file in `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Transcripts`
* **Source audio file (Windows)**: Use the selected merged audio file in `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Audios`
* **Output file (Windows)**: Save the generated Markdown in `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Outputs`
* **Template file (Windows)**: `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Templates\Listening_2.md`

Typical example for this workflow:

* Audio: `Audios\Lektion-6.mp3`
* Transcript: `Transcripts\2026-04-07-23-18-20-transcript.json`

### About the transcript JSON file

The transcript `.json` file is the detailed word-level transcript for the merged audio. It contains a `segments` array; each segment has a `text` field and a `words` array with per-word `start` / `end` timestamps in seconds. These timestamps are used for:

* `data-start` / `data-end` in `de_1`
* `de_1_start`
* `de_1_end`

## Extraction model for merged audio

This B1-4 workflow is for **marker-based merged audio**. The audio is expected to contain explicit boundaries like:

* `Teil eins`
* `Teil zwei`
* ...
* `Ende des Teil eins`
* `Ende des Teil zwei`

Each `Teil X ... Ende des Teil X` span defines **one content block**.

## Critical skip rules

### 1. Skip merged marker speech

The synthetic or inserted merge markers are **boundary markers only**. They are **not content** and must never appear inside the final `de_1`, `en_1`, or `note_1`.

Skip all spoken marker phrases created by merging, including:

* `Teil eins`
* `Teil zwei`
* `Teil drei`
* ...
* `Ende des Teil eins`
* `Ende des Teil zwei`
* `Ende des Teil drei`

### 2. Skip instruction audio already inside the original track

Some source tracks already contain their own internal announcements or instructions immediately after the merged `Teil X` marker. These must also be skipped if they are not part of the target listening content.

Example:

```text
Teil eins.

Beratungsgespräch, Teil eins.
```

In this example:

* the first `Teil eins.` is the **merged marker** and must be skipped
* `Beratungsgespräch, Teil eins.` is also **instruction/introduction audio** and must be skipped if it is only an announcement and not part of the actual listening passage

### 3. Start extraction only at the real content

Inside each `Teil X ... Ende des Teil X` region:

* find the first sentence that belongs to the actual listening passage
* set `de_1_start` to the first word of that actual content
* exclude any marker and non-content introduction before it

### 4. End extraction before the closing marker

For each block:

* end at the last word of the real listening content
* do **not** include `Ende des Teil X`

### 5. Skip repeated content

If the same listening content is repeated later in the same merged audio, only extract the **first occurrence** unless the task explicitly says otherwise.

## Output overview

* The output file **must begin** with this metadata block exactly:

```
TARGET DECK: TEST
```

* Create **one Markdown file** containing all `SSTART ... EEND` blocks
* Each block must use the **Listening_2** note type and follow `Templates\Listening_2.md`
* Add `Listening_2` at the top of every block
* Wrap every block from `SSTART` to `EEND` in triple backticks
* The top metadata remains outside any code fence

Before each block, insert a heading using one of these formats:

```text
## Teil X
## Teil X.Y
```

Use `## Teil X` when the entire marker-based part fits in a single block.
Use `## Teil X.Y` (e.g. `Teil 1.1`, `Teil 1.2`) when a long part has been split into sub-blocks (see **Sub-block splitting** below).

## Field reference

| Field | Description |
|---|---|
| `de_1` | German text as `<span>` words with `data-start` / `data-end` timestamps, one sentence per line separated by `<br>` |
| `en_1` | Sentence-by-sentence translation, one sentence per line: `<b>German sentence.</b> — English translation.<br>` |
| `note_1` | `Key Words and Phrases` + `Grammar to Remember` in HTML |
| `de_1_audio` | `[sound:filename.mp3]` using the selected merged audio filename |
| `de_1_wave` | plain merged audio filename, no `[sound:]` wrapper |
| `de_1_start` | start timestamp of the first word of the real content |
| `de_1_end` | end timestamp of the last word of the real content |

## Notes section format

```text
<b>Key Words and Phrases</b><br>
• <b>word/phrase</b> — gloss<br>
• <b>word/phrase</b> — gloss<br>
• (at least 5 total)<br>
<br>
<b>Grammar to Remember</b><br>
• <b>grammar point</b> — short explanation/example<br>
• (at least 3 total)
```

## Translation section format

```text
<b>German sentence 1.</b> — English translation 1.<br>
<b>German sentence 2.</b> — English translation 2.<br>
...
```

## Deliverable layout

Each marker-based part becomes one block:

```text
SSTART

Listening_2

de_1: <span data-start="ss.ss" data-end="ss.ss">Word1</span> <span ...>Word2</span> ... <br><span ...>Word3</span> ...
en_1: <b>Sentence DE 1.</b> — Translation EN 1.<br><b>Sentence DE 2.</b> — Translation EN 2.
note_1: <b>Key Words and Phrases</b><br>• <b>...</b> — ...<br>...<br><br><b>Grammar to Remember</b><br>• <b>...</b> — ...
de_1_audio: [sound:merged-audio-file.mp3]
de_1_wave: merged-audio-file.mp3
de_1_start: <start time of first real content word>
de_1_end: <end time of last real content word>
EEND
```

## Sub-block splitting

Each `SSTART ... EEND` block should be **at most 60 seconds** of audio content (measured as `de_1_end − de_1_start`).

If a Teil's cleaned content exceeds 60 seconds, split it into sub-blocks.

### Splitting rules

1. **Split at natural Q-A pair boundaries**
   * Identify places where one question-and-answer exchange ends and the next topic begins
   * A good split point is after a complete response, before the next question or topic shift
   * Never split in the middle of a sentence, a question, or a direct answer

2. **Each sub-block must be self-contained**
   * A sub-block should make sense on its own — it must contain at least one complete conversational exchange or topical unit
   * Avoid orphan sentences (e.g. a lone follow-up without its question)

3. **Target 30–60 seconds per sub-block**
   * Prefer ~45 seconds as the sweet spot
   * A block may be slightly shorter than 30 seconds if the conversational unit is naturally short
   * Never exceed 60 seconds

4. **Numbering**
   * If a Teil is not split: use `## Teil X` (unchanged)
   * If a Teil is split: use `## Teil X.1`, `## Teil X.2`, etc.
   * Each sub-block gets its own full `SSTART ... EEND` block with independent `de_1_start`, `de_1_end`, translations, and notes

### Example

Teil 2 (91 seconds) might split into:

* `## Teil 2.1` — Timeline discussion and payment question (≈45 s)
* `## Teil 2.2` — Two quotes explanation and farewell (≈46 s)

## Block construction rule

For each visible `Teil X` in the merged audio:

1. Use the merged markers only to find the region boundaries
2. Remove the inserted opening marker from the content
3. Remove the inserted closing marker from the content
4. Remove built-in non-content intro or instruction speech inside that region
5. Keep only the real listening passage
6. If the cleaned content is ≤ 60 seconds, build one `SSTART ... EEND` block
7. If the cleaned content exceeds 60 seconds, apply **sub-block splitting** and build multiple blocks
