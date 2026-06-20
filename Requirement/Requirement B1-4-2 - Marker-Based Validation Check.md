---
aliases: []
time: 2026-04-07-23-36-00
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

This requirement runs **after** the Markdown output file has been generated per **Requirement B1-4-1**.

It validates the generated marker-based file for structure, field completeness, formatting, timestamps, translation consistency, and marker exclusion.

## How to run

A Python tool (`check_listening_4.py`) automates these checks.

```powershell
python Requirement\check_listening_4.py <path-to-generated-file.md>
```

Example:

```powershell
python Requirement\check_listening_4.py "C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Outputs\Listening-generated.md"
```

## B1-4-2.1 — Block structure

1. Parse all `SSTART ... EEND` blocks in the file.
2. Verify every block has a heading in the format:

```text
## Teil X
## Teil X.Y
```

3. Verify block count matches the number of detected Teil headings.
4. Verify each block contains the note-type header `Listening_2`.
5. Verify the file begins with `TARGET DECK: TEST` outside code fences.

**FAIL** if any heading, block count, or note-type header is wrong.

## B1-4-2.2 — Field completeness

For every block, verify these fields exist and are non-empty:

| Field | Must be non-empty |
|---|---|
| `de_1` | ✅ |
| `en_1` | ✅ |
| `note_1` | ✅ |
| `de_1_audio` | ✅ |
| `de_1_wave` | ✅ |
| `de_1_start` | ✅ |
| `de_1_end` | ✅ |

Additional audio checks:

| Field | Format |
|---|---|
| `de_1_audio` | `[sound:<filename>.mp3]` |
| `de_1_wave` | plain `.mp3` filename |
| consistency | filename inside `de_1_audio` must equal `de_1_wave` |

**FAIL** if any required field is missing, empty, or incorrectly formatted.

## B1-4-2.3 — HTML format validation

For every block:

1. `de_1` must contain `<span data-start="..." data-end="...">` tags.
2. `en_1` must contain `<b>...</b> —` translation lines separated by `<br>`.
3. `note_1` must contain both:
   * `<b>Key Words and Phrases</b>`
   * `<b>Grammar to Remember</b>`

**FAIL** if any required pattern is missing.

## B1-4-2.4 — Content minimums

For every block:

* `Key Words and Phrases`: at least 5 items
* `Grammar to Remember`: at least 3 items

Count bullet items (`•`) in `note_1`. Count bullets before `<b>Grammar to Remember</b>` as keywords and bullets after it as grammar.

**FAIL** if any block is below minimum.

## B1-4-2.5 — Timestamp validation

For every block:

1. `de_1_start` and `de_1_end` must be valid numbers
2. `de_1_start` must be less than `de_1_end`
3. Every `<span>` in `de_1` must have valid numeric `data-start` / `data-end`
4. The first span `data-start` must equal `de_1_start`
5. The last span `data-end` must equal `de_1_end`

**FAIL** if timestamps are invalid, reversed, or mismatched.

## B1-4-2.6 — Sentence-by-sentence translation consistency

For every block:

1. `de_1` must be sentence-per-line using `<br>`
2. `en_1` must also be sentence-per-line using `<br>`
3. The number of German sentences must equal the number of translation lines

**FAIL** if sentence counts do not match.

## B1-4-2.7 — Marker exclusion check

For every block, verify that the content fields do **not** include merge markers or boundary markers.

The following must not appear in `de_1` or as standalone translation content in `en_1`:

* `Teil eins`
* `Teil zwei`
* `Teil drei`
* `Teil vier`
* `Teil fünf`
* `Ende des Teil eins`
* `Ende des Teil zwei`
* `Ende des Teil drei`
* `Ende des Teil vier`
* `Ende des Teil fünf`

The same rule applies to numeric variants such as:

* `Teil 1`
* `Teil 2`
* `Ende des Teil 1`
* `Ende des Teil 2`

These phrases may exist in the source audio and transcript as boundary markers, but they must not survive into the final learning content blocks.

**FAIL** if a block still contains inserted merge markers.

## B1-4-2.8 — Instruction exclusion check

Within each block, verify that obvious non-content introductions or instructions have been removed when they are only labels and not the actual listening passage.

Examples to exclude when they are purely introductory:

* `Beratungsgespräch, Teil eins.`
* `Hören Sie jetzt ...`
* `Lesen Sie ...`
* other exam-style setup lines

Important:

* Only remove these when they are clearly non-content
* Do not remove a sentence if it belongs to the actual dialogue, report, or listening passage

**FAIL** if a block begins with obvious boundary-marker speech or pure setup audio instead of the real content.

## B1-4-2.9 — Block duration check

For every block:

1. Compute duration as `de_1_end − de_1_start`
2. Duration must be ≤ 60 seconds

The maximum ensures each block is a manageable Q-A pair rather than an entire multi-minute passage.

**FAIL** if any block exceeds 60 seconds.
