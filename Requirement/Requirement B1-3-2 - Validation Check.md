---
aliases: []
time: 2025-11-13-10-33-09
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

This requirement runs **after** the Markdown output file has been generated per **Requirement B1-3-1**.

It performs **six checks** on the generated file to validate structure, field completeness, HTML formatting, content minimums, timestamp validity, and sentence-by-sentence translation consistency.

## How to Run

A Python tool (`check_listening_2.py`) automates all checks. To run it:

```powershell
python check_listening_2.py <path-to-generated-file.md>
```

Example:

```powershell
python check_listening_2.py "C:\Users\HOANG PHI LONG DANG\repos\German_Listening\Outputs\Listening-generated.md"
```

The tool prints a per-check **PASS** or **FAIL** with details, then a final summary.

---

## B1-3-2.1 — Block structure

1. Parse all `SSTART ... EEND` blocks in the file (legacy `START ... END` is also accepted).
2. Verify block structure as: 5 (Teil 1) + **N** (Teil 2 Q&A pairs) + 5 (Teil 3), where **N** is dynamic and depends on the transcript.
3. Verify Teil 1 has exactly headings `## Teil 1 — Aufgabe 41` to `## Teil 1 — Aufgabe 45`.
4. Verify Teil 3 has exactly headings `## Teil 3 — Aufgabe 56` to `## Teil 3 — Aufgabe 60`.
5. Verify Teil 2 headings use `## Teil 2 — Q&A NN` and appear at least once.
6. Verify block count equals heading count (5 + N + 5).
7. Each block must contain the note-type header `Listening_2`.
8. The file must begin with `TARGET DECK: TEST` (outside code fences).

**FAIL** if any of these counts or headers are wrong.

## B1-3-2.2 — Field completeness

For every `SSTART ... EEND` block, verify these fields exist **and are non-empty**:

| Field | Must be non-empty |
|---|---|
| `de_1` | ✅ |
| `en_1` | ✅ |
| `note_1` | ✅ |
| `de_1_audio` | ✅ |
| `de_1_wave` | ✅ |
| `de_1_start` | ✅ |
| `de_1_end` | ✅ |

Additional format checks for the audio fields:

| Field | Format |
|---|---|
| `de_1_audio` | Must match `[sound:<filename>.mp3]` |
| `de_1_wave` | Must be a plain filename ending in `.mp3` (no `[sound:]` wrapper) |
| consistency | The filename inside `de_1_audio`'s `[sound:...]` must equal the value of `de_1_wave` |

**FAIL** if any required field is missing/empty or any audio field has an invalid format.

## B1-3-2.3 — HTML format validation

For every block:

1. **`de_1`** must contain `<span data-start="..." data-end="...">` tags. Every word (non-whitespace token) should be wrapped in a `<span>`.
2. **`en_1`** must contain `<b>...</b> —` patterns (bold German sentence + em-dash + translation), separated by `<br>`.
3. **`note_1`** must contain both:
   * `<b>Key Words and Phrases</b>`
   * `<b>Grammar to Remember</b>`

**FAIL** if any of these patterns are missing.

## B1-3-2.4 — Content minimums

Count bullet items (`•`) in `note_1` for each block:

| Block type | Key Words minimum | Grammar minimum |
|---|---|---|
| Teil 1 blocks (5) | ≥ 5 each | ≥ 3 each |
| Teil 2 Q&A blocks (N, dynamic) | ≥ 5 each | ≥ 3 each |
| Teil 3 blocks (5) | ≥ 5 each | ≥ 3 each |

Split `note_1` at `<b>Grammar to Remember</b>` — bullets before it count as Key Words, bullets after count as Grammar.

**FAIL** if any block is below its minimum.

## B1-3-2.5 — Timestamp validation

For every block:

1. `de_1_start` and `de_1_end` must be valid **numbers** (seconds).
2. `de_1_start` < `de_1_end`.
3. Every `<span>` in `de_1` must have valid `data-start` and `data-end` attributes that are numbers.
4. The `data-start` of the first `<span>` must equal `de_1_start`.
5. The `data-end` of the last `<span>` must equal `de_1_end`.

**FAIL** if any timestamp is invalid, out of order, or mismatched.

## B1-3-2.6 — Sentence-by-sentence translation consistency

For every block:

1. `de_1` must be formatted **sentence-per-line** using `<br>` between sentences (exactly one line per sentence).
2. Count sentences in `de_1` by sentence-ending span groups and ensure `<br>` count is exactly `sentences - 1`.
3. Count translation lines in `en_1` by counting `<br>` separators + 1.
4. The two counts must be **equal** — every German sentence needs exactly one translation line.

**FAIL** if `de_1` is not sentence-per-line, or if the sentence count in `de_1` does not match the translation count in `en_1`.
