---
aliases: []
time: 2025-11-13-10-33-09
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

This requirement runs **after** the Markdown `Listening-generated` file has been constructed and saved.

It performs **three tasks**:

## How to Run the Consistency Check

A Python tool (`check_consistency.py`) has been created to automate this check. To run it:

1. Open a terminal in the German_Listening folder
2. Run the command:

```powershell
python check_consistency.py
```

Or with full path:

```powershell
& "C:/Users/HOANG PHI LONG DANG/AppData/Local/Programs/Python/Python313/python.exe" check_consistency.py
```

The tool will automatically:
- Count characters in all Breakdown sections
- Count characters in the raw transcript
- Calculate and validate the IoU
- Display PASS or FAIL with detailed statistics

## B1-2.1 — Count characters in all `<sentence_DE_...>` inside the Breakdown sections of each Teil

For every Teil (Teil 1, Teil 2, Teil 3):

1. Locate all entries under:

```
## Breakdown
* "<sentence_DE_...>" = <translation_EN_...>
```

2. For each `<sentence_DE_...>`:

	* Remove punctuation (`. , ; : ! ? " ' ( ) [ ] { } … - – —`)
	* Remove timestamps if present
	* Remove leading/trailing spaces
	* Count **all remaining characters**, including spaces between words

3. Sum the totals separately:

	* `T1` = total for Teil 1
	* `T2` = total for Teil 2
	* `T3` = total for Teil 3

4. Compute the final Breakdown-character total:

```
TOTAL_BREAKDOWN = T1 + 2 × (T2 + T3)
```

## B1-2.2 — Count characters in the raw transcript `German_Listening_Transcript`

1. Load the transcript file from:

```
C:\Users\HOANG PHI LONG DANG\OneDrive\OBSIDIAN 24 09 01\24 09 01 obsidian-go-obsidian_v.0.3.1\German_Listening\Transcripts\German_Listening_Transcript
```

2. For each line:

	* Remove timestamps (`mm:ss`, `h:mm`, etc.)
	* Remove punctuation (same list as B1-2.1)
	* Remove leading/trailing spaces
	* Keep spaces between words
	* Count all remaining characters

3. Compute the final transcript-character total:

```
TOTAL_TRANSCRIPT
```

## B1-2.3 — Intersection-over-Union (IoU) Validation

Calculate:

```
IoU = min(TOTAL_BREAKDOWN, TOTAL_TRANSCRIPT) 
      ÷ 
      max(TOTAL_BREAKDOWN, TOTAL_TRANSCRIPT)
```

### Failure condition

If:

```
IoU < 0.76
```

Then display this exact message:

```
Intersection over Union < 76%. Check the generated file again!
```

### Pass condition

If:

```
IoU ≥ 0.76
```

No warning; the file passes the consistency check.
