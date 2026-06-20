---
aliases: []
time: 2025-11-03-10-16-41
tags:
  - "#language-german"
status: []
TARGET DECK: []
---


## Paths

* **Transcript file (Windows)**: `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Transcripts\transcript.json`
* **Output file (Windows) — save the generated Markdown `Listening-generated` here**: `C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Outputs`

## Output Overview (applies to all Teile)

* The output file **must begin** with this metadata block (exactly, no leading spaces):

	```
	TARGET DECK: TEST
	```

* Create **one Markdown file** that contains the metadata block and **all** `START ... END` blocks:
	* `START ... END` for **Teil 1**
	* `START ... END` for **Teil 2**
	* `START ... END` for **Teil 3**
* At the top of each block add:
	* A single line header: `Listening`
	* **Title** in the exact format: `YYYY-MM-DD-x-yy` (where **x** is the Teil number: 1–4 and **y** is a no. of block 01, 02, 03). **Block titles must be unique!**
	* `AUDIO:` and `wave:` values pulled from the **Transcript file**
* Inside each block, create numbered segments with the three fields below:
	1. `XX_start:` — the segment **start time** in `mm.ss` (e.g., `0:56`, `06:12`)
	2. `XX_transcript:` — the **corrected** transcript text
	3. `XX_note:` — the notes section (Breakdown, Key Words, Grammar)
* Wrap **every** output block from `START` to `END` in a fenced code block:
	* Begin with three backticks `<code>```</code>`
	* Paste the entire block from `START` to `END`
	* Close with three backticks `<code>```</code>`
* The **front-matter metadata** stays at the very top of the file, **outside** any fence.

NOTE: Before each `START ... END` block, insert a **heading section** in the following exact format:

```
## Teil X
```

where **X = 1, 2, or 3** (matching the Teil that follows).

### Transcript correction rules (all Teile)

* Fix **typos and minor errors only**.
* **Preserve** meaning and spoken structure (no unnecessary rephrasing).

### Notes section (all Teile)

* **Breakdown** — sentence-by-sentence meaning + translations.
* **Key Words and Phrases / Common phrases** — vocabulary & expressions (**at least 5** per segment).
* **Grammar to Remember** — points essential to understanding (**at least 3** per segment).

## Teil 1

**Scope:** **Aufgabe 41–45**
**Mapping:**

* Aufgabe 41 → `01_transcript`
* Aufgabe 42 → `02_transcript`
* Aufgabe 43 → `03_transcript`
* Aufgabe 44 → `04_transcript`
* Aufgabe 45 → `05_transcript`

**Deliverable layout (use exactly):**

```
START

%Listening

Title: YYYY-MM-DD-1-01/02/...

AUDIO: <value from transcript file>

wave: <value from transcript file>

01_start: mm:ss

01_transcript:

<text>

01_note:

## Breakdown

- "<sentence_DE_1>" = <translation_EN_1>
- "<sentence_DE_2>" = <translation_EN_2>
...

## Key Words and Phrases to Remember

- <word/phrase> - <gloss>
- <word/phrase> - <gloss>
- <at least 5 total>

## Grammar to Remember

- <grammar point> - <short explanation/example>
- <at least 3 total>

02_start: mm:ss

02_transcript:

<text>

02_note:

<same note structure as above>

03_start: ...

03_transcript: ...

03_note: ...

04_start: ...

04_transcript: ...

04_note: ...

05_start: ...

05_transcript: ...

05_note: ...

END
```

> **Tip:** Keep each `*_note` concise and aligned with its transcript. Use bullet points; avoid long paragraphs.

## Teil 2

**Scope & Structure:**

* Split the transcript into **6 segments per block** → labeled `01_transcript` → `06_transcript`.
* Each segment must contain **≤ 100 words**.
* If the transcript (e.g., *Teil 2*) is **not fully covered** after the first 6 segments, **start a new block** with segments again labeled from `01_transcript` → `06_transcript`. Never use `07_transcript`, `08_transcript`, etc.; create a new separate `START...END` block for the remaining Teil 2 content instead.
* Continue creating new blocks until the entire transcript is covered.

**Timing:**

* Add the **start time (mm:ss)** **above** each transcript as `XX_start:`.

**Content Requirements:** Each transcript segment must include:

* The **spoken text** (≤ 100 words)
* A **note section** with:
	* **Breakdown / summary**
	* **Key words or expressions**
	* **Grammar highlights** (if relevant)

**Deliverable layout:**

```

START

%Listening

Title: YYYY-MM-DD-HH-SS-2

AUDIO: <value from transcript file>

wave: <value from transcript file>

01_start: mm:ss

01_transcript:

<≤100 words>

01_note:

<Breakdown / Key Words / Grammar>

02_start: mm:ss

02_transcript:

<≤100 words>

02_note:

<Breakdown / Key Words / Grammar>

03_start: mm:ss

03_transcript:

<≤100 words>

03_note:

<Breakdown / Key Words / Grammar>

END

```

## Teil 3

**Scope:** **Aufgabe 56–60**
**Mapping:**

* Aufgabe 56 → `01_transcript`
* Aufgabe 57 → `02_transcript`
* Aufgabe 58 → `03_transcript`
* Aufgabe 59 → `04_transcript`
* Aufgabe 60 → `05_transcript`

**Deliverable layout:**

```

START

%Listening

Title: YYYY-MM-DD-HH-SS-3

AUDIO: <value from transcript file>

wave: <value from transcript file>

01_start: mm:ss

01_transcript:

<text>

01_note:

<Breakdown / Key Words / Grammar>

02_start: mm:ss

02_transcript:

<text>

02_note:

<Breakdown / Key Words / Grammar>

03_start: mm:ss

03_transcript:

<text>

03_note:

<Breakdown / Key Words / Grammar>

04_start: mm:ss

04_transcript:

<text>

04_note:

<Breakdown / Key Words / Grammar>

05_start: mm:ss

05_transcript:

<text>

05_note:

<Breakdown / Key Words / Grammar>

END

```

## Script Readability (applies to every `*_transcript` only)

**Goal:** one clean sentence per line, no run-on blocks.

1. **One sentence per line**

	* Break lines **only** at sentence enders: `.`, `?`, `!`, or `…` (ellipsis).
	* Keep the end punctuation **inside** any closing quote.

2. **Do not rephrase**

	* **No** splitting or joining sentences beyond the natural enders.
	* Keep word order and expressions intact; only fix typos/minor errors.

3. **Quotes**

	* Preserve opening/closing quotes exactly as in source.
	* If a quoted passage spans multiple sentences, still put **each sentence on its own line**.

4. **Speaker names (if present in source)**

	* Keep them inline with the sentence (do not move before or after).
	* Do **not** invent speaker labels.

5. **Whitespace**

	* No leading spaces at line starts.
	* A single newline between sentences (i.e., each sentence is its own line).
	* No extra blank lines inside `*_transcript`.

6. **This formatting rule applies only to** `*_transcript`.

	* Do **not** apply to `*_note`, `Breakdown`, `Key Words`, or `Grammar`.

### Example

**NOT**

```
"Du, Yannick, Ende Juli ist doch unser Schulfest. Und was organisieren wir? Die Klasse 7b hat eine Band und spielt. Das finde ich toll. Hm, ich kann kein Instrument spielen. Und ein Malwettbewerb? Wir hatten doch die Comic-Ausstellung hier. Mein Onkel ist Schauspieler im Theater. Er hilft uns sicher mit einem Stück."

```

**SHOULD BE**

```
"Du, Yannick, Ende Juli ist doch unser Schulfest. Und was organisieren wir?
Die Klasse 7b hat eine Band und spielt. Das finde ich toll.
Hm, ich kann kein Instrument spielen.
Und ein Malwettbewerb? Wir hatten doch die Comic-Ausstellung hier.
Mein Onkel ist Schauspieler im Theater. Er hilft uns sicher mit einem Stück."
```

### Optional implementation hint (regex-friendly)

* Split on `(?<=[.!?…])\s+` to create one sentence per line.
* Then apply your existing **whitespace normalization** (outside fenced blocks).

## Whitespace & formatting normalization (apply before saving)

1. **Whole-file trim:** remove any leading/trailing whitespace from the entire document.
2. **Line trim:** on every line outside fenced code blocks (`…`), remove:
	* leading spaces/tabs
	* trailing spaces/tabs
3. **Blank lines:** collapse 2+ consecutive blank lines into **one** blank line (outside code blocks).
4. **Keys & colons:** ensure exactly one space after colons and **no** space before them.
	* ✅ `01_start: 06:12`
	* ❌ `01_start : 06:12` / `01_start: 06:12`
5. **List bullets:** a single space after `-` or `*`.
	* ✅ `- Item text`
	* ❌ `- Item text`
6. **Title/AUDIO/wave lines:** no leading spaces; one space after the colon.
7. **End-of-file newline:** ensure the file ends with exactly **one** newline.
8. **Do not alter** spacing **inside** fenced code blocks.

**Quick check examples**

* Trimmed line: `* "<sentence 1>" - "<translation>"` (no trailing spaces)
* Segment keys: `02_transcript:` followed by content on the next line; no extra spaces on the key line.
* Block separation: exactly **one** blank line between sections (e.g., between `01_note:` and the next `02_start:`).
