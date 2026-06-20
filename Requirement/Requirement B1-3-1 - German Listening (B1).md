---
aliases: []
time: 2025-11-03-10-16-41
tags:
  - "#language-german"
status: []
TARGET DECK: []
---


## Paths

* **Transcript file (Windows)**: Use the JSON file in `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Transcripts` (filename may vary, e.g. timestamped export)
* **Output file (Windows) — save the generated Markdown here**: `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Outputs`
* **Template file (Windows) — follow this exact note template**: `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Templates\Listening_2.md`
* **Audio folder (Windows)**: `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Audios` — pick the **latest file** (by modification date) if multiple files exist

### About the transcript JSON file

The selected transcript `.json` file in the `Transcripts` folder is the **detailed word-level transcript** for the audio. It contains a `segments` array; each segment has a `text` field (full sentence) and a `words` array with per-word `start`/`end` timestamps in seconds — these are the values used for `data-start` / `data-end` in `de_1` and for `de_1_start` / `de_1_end`.

### Extraction rules

1. **Skip instruction segments.** Do not include exam instructions — only extract the actual spoken content for each Aufgabe/Teil.

   Example of an **instruction segment to skip** (segment 0 in the transcript):
   > *"Modelltest vier. Hörverstehen Teil eins. Sie hören fünf kurze Texte. Sie hören diese Texte nur einmal. Dazu sollen Sie fünf Aufgaben lösen. …"*

   Similar instruction segments appear before Teil 2 and Teil 3 — skip all of them.

2. **Skip repeated hearings.** Some segments/Aufgaben are played twice in the audio (especially in Teil 3). Only extract the **first occurrence** — skip the second time the same content is heard.

### Transcript correction rules

* Fix **typos and minor errors only**.
* **Preserve** meaning and spoken structure (no unnecessary rephrasing).

## Output Overview (applies to all Teile)

* The output file **must begin** with this metadata block (exactly, no leading spaces):

 ```
 TARGET DECK: TEST
 ```

* Create **one Markdown file** that contains the metadata block and **all** `SSTART ... EEND` blocks.
* Each `SSTART ... EEND` block uses the **Listening_2** note type and must follow `Templates\Listening_2.md`.
* At the top of each block add the note-type header: `Listening_2`
* Wrap **every** block from `SSTART` to `EEND` in a fenced code block (triple backticks).
* The **front-matter metadata** stays at the very top of the file, **outside** any fence.

NOTE: Before each `SSTART ... EEND` block, insert a **heading section** in one of the following exact formats:

```
## Teil X — Aufgabe NN
```

or (for Teil 2):

```
## Teil 2 — Q&A NN
```

### Field reference (Listening_2 template from `Templates\Listening_2.md`)

| Field | Description |
|---|---|
| `de_1` | German text as `<span>` words with `data-start` / `data-end` timestamps (seconds), **one sentence per line** separated by ` <br>` |
| `en_1` | Sentence-by-sentence translation, **one sentence per line**: `<b>German sentence.</b> — English translation.<br>` |
| `note_1` | **Key Words and Phrases** + **Grammar to Remember** in HTML (see format below) |
| `de_1_audio` | `[sound:filename.mp3]` — main playback audio. **Auto-filled**: get the latest file from `Audios/` and use `[sound:<filename>]` |
| `de_1_wave` | `filename.mp3` — waveform display, plain filename, no `[sound:]` wrapper. **Auto-filled**: same filename as `de_1_audio` without the `[sound:]` wrapper |
| `de_1_start` | Start timestamp in seconds of the first word in `de_1` |
| `de_1_end` | End timestamp in seconds of the last word in `de_1` |

### Notes section format (`note_1`)

```
<b>Key Words and Phrases</b><br>
• <b>word/phrase</b> — gloss<br>
• <b>word/phrase</b> — gloss<br>
• (at least 5 total for each block in Teil 1 and 3, at least 10 for Teil 2)<br>
<br>
<b>Grammar to Remember</b><br>
• <b>grammar point</b> — short explanation/example<br>
• (at least 3 total for each block in Teil 1 and 3, at least 6 for Teil 2)
```

### Translation section format (`en_1`)

```
<b>German sentence 1.</b> — English translation 1.<br>
<b>German sentence 2.</b> — English translation 2.<br>
...
```

## Teil 1

**Scope:** **Aufgabe 41–45**
**Mapping:** Each Aufgabe → **one separate** `SSTART ... EEND` block.

* Aufgabe 41 → block 1
* Aufgabe 42 → block 2
* Aufgabe 43 → block 3
* Aufgabe 44 → block 4
* Aufgabe 45 → block 5

**Deliverable layout (one block per Aufgabe):**

```
SSTART

Listening_2

de_1: <span data-start="ss.ss" data-end="ss.ss">Word1</span> <span ...>Word2</span> ... <br><span ...>Word3</span> ...
en_1: <b>Sentence DE 1.</b> — Translation EN 1.<br><b>Sentence DE 2.</b> — Translation EN 2.
note_1: <b>Key Words and Phrases</b><br>• <b>...</b> — ...<br>...<br><br><b>Grammar to Remember</b><br>• <b>...</b> — ...
de_1_audio: [sound:filename.mp3]
de_1_wave: filename.mp3
de_1_start: <start time of first word (sec)>
de_1_end: <end time of last word (sec)>
EEND
```

## Teil 2

**Scope & Structure:**

* Split Teil 2 into **Q&A pair blocks**: each interviewer question plus the corresponding answer in one `SSTART ... EEND` block.
* The number of Teil 2 Q&A blocks is **dynamic** and depends on the transcript (10 is common, but do not hard-code it).
* Keep conversational context natural: include opening/closing host lines with the nearest Q&A pair when needed.
* All sentences are included in `de_1`, with **sentence-per-line** separation using ` <br>`.
* `en_1` must be **sentence-per-line** with matching count to `de_1` in each block.
* `note_1` must be present in each Q&A block.

**Deliverable layout (one block per Q&A pair):**

```
SSTART

Listening_2

de_1: <all Teil 2 sentences as timestamped <span> words, one sentence per line with <br>>
en_1: <sentence-by-sentence translations for all sentences, one sentence per line>
note_1: <Key Words (at least 10) + Grammar (at least 6) covering the whole Teil 2 content>
de_1_audio: [sound:filename.mp3]
de_1_wave: filename.mp3
de_1_start: <start time of first word (sec)>
de_1_end: <end time of last word (sec)>
EEND
```

## Teil 3

**Scope:** **Aufgabe 56–60**
**Mapping:** Each Aufgabe → **one separate** `SSTART ... EEND` block.

* Aufgabe 56 → block 1
* Aufgabe 57 → block 2
* Aufgabe 58 → block 3
* Aufgabe 59 → block 4
* Aufgabe 60 → block 5

**Deliverable layout (one block per Aufgabe):**

```
SSTART

Listening_2

de_1: <span data-start="ss.ss" data-end="ss.ss">Word1</span> <span ...>Word2</span> ... <br><span ...>Word3</span> ...
en_1: <b>Sentence DE 1.</b> — Translation EN 1.<br><b>Sentence DE 2.</b> — Translation EN 2.
note_1: <b>Key Words and Phrases</b><br>• <b>...</b> — ...<br>...<br><br><b>Grammar to Remember</b><br>• <b>...</b> — ...
de_1_audio: [sound:filename.mp3]
de_1_wave: filename.mp3
de_1_start: <start time of first word (sec)>
de_1_end: <end time of last word (sec)>
EEND
```
