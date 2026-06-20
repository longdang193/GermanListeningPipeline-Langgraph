---
aliases: []
time: 2026-04-07-23-05-00
tags:
  - "#language-german"
status: []
TARGET DECK: []
---

This requirement creates one merged listening file from `Audios\Merge\`, sorted in A-Z order, with spoken markers around every source clip:

* before each file: `Teil N`
* after each file: `Ende des Teil N`

Example:

* `CD1_Tr47.mp3` -> `Teil 1` + audio + `Ende des Teil 1`
* `CD1_Tr48.mp3` -> `Teil 2` + audio + `Ende des Teil 2`

## Tool

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\Requirement\merge_audio_with_markers.ps1
```

## Output filename rule

When prompting for a merge:

* If the user gives a merged output name, use that exact name for the final file.
* If the user does not give a merged output name, ask for the desired output filename before merging.

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\Requirement\merge_audio_with_markers.ps1 -OutputFile "Outputs\Merge\My-Merged-CD1.mp3"
```

Current script defaults:

* input folder: `Audios\Merge`
* output file: `Outputs\Merge\merged-with-markers.mp3`
* prompt source: generated speech

## Important note about German voice

The script can generate prompts with Windows SAPI voices, but this PC currently only shows English desktop voices. If you want the labels to sound properly German, use one of these options:

1. Install a real German Windows voice, then run:

Windows 11:

* Open `Settings`
* Go to `Time & language`
* Open `Language & region`
* Click `Add a language`
* Search for `Deutsch (Deutschland)` or another German variant
* Install it
* Open the German language options
* Make sure `Speech` is installed if that option appears

Windows 10:

* Open `Settings`
* Go to `Time & Language`
* Open `Language`
* Click `Add a preferred language`
* Add `Deutsch`
* Open `Options`
* Install speech or voice components if available

After installation, restart Windows and check the available voices:

```powershell
powershell -ExecutionPolicy Bypass -File .\Requirement\merge_audio_with_markers.ps1 -ListVoices
```

Then choose a German voice:

```powershell
powershell -ExecutionPolicy Bypass -File .\Requirement\merge_audio_with_markers.ps1 -VoiceName "Your German Voice Name"
```

Important:

* Some Windows installs add German language support but do not add a SAPI text-to-speech desktop voice.
* If `-ListVoices` still only shows `David` or `Zira`, Windows has not installed a usable German SAPI voice for this script yet.

2. Or use your own recorded prompt clips in `Audios\MergePrompts`:

* `teil_1.mp3`
* `ende_des_teil_1.mp3`
* `teil_2.mp3`
* `ende_des_teil_2.mp3`
* etc.

Then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\Requirement\merge_audio_with_markers.ps1 -PromptMode Recorded
```

## Optional arguments

```powershell
-InputDir "Audios/Merge"
-OutputFile "Outputs/Merge/cd1-with-markers.mp3"
-PromptMode Generated
-PromptDir "Audios/MergePrompts"
-VoiceName "Microsoft Hedda"
-IntroTemplate "Teil {0}"
-OutroTemplate "Ende des Teil {0}"
-BitrateKbps 192
-KeepTempFiles
```

## What the script does

1. Reads all audio files in `Audios\Merge`
2. Sorts them by filename
3. Creates intro and outro prompt clips for each part
4. Re-encodes all segments to a consistent MP3 format
5. Concatenates everything into one final MP3
