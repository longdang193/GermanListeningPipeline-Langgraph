---
aliases: []
time: 2026-04-07-23-37-00
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

This requirement runs **after** the Markdown output file has been validated per **Requirement B1-4-2**.

It splits the merged source audio into one clip per `Teil X` block and generates SRT subtitle files using the cleaned timestamps from the marker-based extraction.

## Prerequisites

* **Requirement B1-4-1** completed
* **Requirement B1-4-2** passed
* **ffmpeg** installed and available on PATH

## B1-4-3.1 — Validate first

Before splitting, confirm the generated Markdown passes all B1-4-2 checks.

Proceed only if all checks pass.

Validator command:

```powershell
python Requirement\check_listening_4.py Outputs\Listening-generated.md
```

## B1-4-3.2 — Split merged audio by cleaned content timestamps

For each `## Teil X` block:

1. Read `de_1_start` and `de_1_end`
2. Split the merged source audio into one clip using those timestamps
3. Do not include the synthetic merge marker audio at the start
4. Do not include the `Ende des Teil X` marker audio at the end
5. Do not include skipped instruction-only audio that was intentionally excluded in B1-4-1

This means the output clip should contain only the actual listening content represented by the block.

Run the splitter:

```powershell
python Requirement\split_and_subtitle_4.py Outputs\Listening-generated.md
```

## B1-4-3.3 — Generate subtitles

For each `## Teil X` block:

1. Build one `.srt` file
2. Use `<br>`-separated sentences in `de_1`
3. Use the first and last `<span>` timestamps of each sentence
4. Convert timestamps to clip-relative time starting at `00:00:00`

## Output location

Write all files to:

```text
Outputs\Youtube\
```

## Output naming convention

Files should be numbered sequentially and labeled by Teil:

| Block | Naming pattern | Example |
|---|---|---|
| Teil 1 | `NN_Teil1` | `01_Teil1.mp3` / `01_Teil1.srt` |
| Teil 2 | `NN_Teil2` | `02_Teil2.mp3` / `02_Teil2.srt` |
| Teil 3 | `NN_Teil3` | `03_Teil3.mp3` / `03_Teil3.srt` |

If a more descriptive suffix is helpful, it may be appended, but the leading Teil number should stay clear and stable.

## Expected result

For **N** marker-based parts:

* **N** `.mp3` files
* **N** `.srt` files

Total: **2N files**

## Verification

After splitting:

1. Confirm the number of `.mp3` files equals the number of `## Teil X` blocks
2. Confirm the number of `.srt` files equals the number of `## Teil X` blocks
3. Spot-check the start of each clip to ensure it begins with the real content, not with `Teil X`
4. Spot-check the end of each clip to ensure it ends before `Ende des Teil X`
5. Verify subtitles align with the spoken content

**FAIL** if clips still contain merge markers, still contain excluded intro/setup speech, or if subtitle timing does not match.
