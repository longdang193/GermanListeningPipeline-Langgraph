## Template

```
SSTART

Listening_2

de_1: German sentences as <span> words with data-start/data-end timestamps, separated by <br>
en_1: Sentence-by-sentence English meaning + translation (one line per <br>-delimited sentence)
note_1: "Key Words and Phrases" (at least 5) + "Grammar to Remember" (at least 3) in HTML
de_1_audio: [sound:filename.mp3] — main playback audio
de_1_wave: filename.mp3 — waveform display audio (plain filename, no [sound:] wrapper)
de_1_start: timestamp (sec) of the first word in de_1
de_1_end: timestamp (sec) of the last word in de_1
<!--ID: 1779022050520-->
EEND
```

## Sample

```
SSTART

Listening_2

de_1: <span data-start="2.98" data-end="3.7">Modelltest</span> <span data-start="4.02" data-end="5.64">vier.</span><br><span data-start="5.68" data-end="6.62">Hörverstehen</span> <span data-start="6.66" data-end="6.91">Teil</span> <span data-start="7.1" data-end="7.52">eins.</span><br><span data-start="8.8" data-end="8.92">Sie</span> <span data-start="8.96" data-end="9.56">hören</span> <span data-start="9.62" data-end="9.88">fünf</span> <span data-start="10.02" data-end="10.38">kurze</span> <span data-start="10.48" data-end="10.92">Texte.</span><br><span data-start="12.1" data-end="12.22">Sie</span> <span data-start="12.26" data-end="12.58">hören</span> <span data-start="12.62" data-end="12.8">diese</span> <span data-start="12.9" data-end="13.24">Texte</span> <span data-start="13.3" data-end="13.54">nur</span> <span data-start="13.62" data-end="14.2">einmal.</span>
en_1: <b>Modelltest vier.</b> — Model test four.<br><b>Hörverstehen Teil eins.</b> — Listening comprehension part one.<br><b>Sie hören fünf kurze Texte.</b> — You will hear five short texts.<br><b>Sie hören diese Texte nur einmal.</b> — You will hear these texts only once.
note_1: <b>Key Words and Phrases</b><br>• <b>Modelltest</b> (der) — model/practice test<br>• <b>Hörverstehen</b> (das) — listening comprehension<br>• <b>hören</b> — to hear/listen<br>• <b>kurze Texte</b> — short texts (<i>kurz</i> = short)<br>• <b>nur einmal</b> — only once<br><br><b>Grammar to Remember</b><br>• <b>Sie hören</b> — formal "you" (Sie) + verb conjugation for plural/formal<br>• <b>diese Texte</b> — demonstrative pronoun <i>diese</i> agrees with plural noun <i>Texte</i><br>• <b>fünf kurze Texte</b> — adjective <i>kurz→kurze</i> takes strong plural ending after a number
de_1_audio: [sound:your_audio_file.mp3]
de_1_wave: your_audio_file.mp3
de_1_start: 2.98
de_1_end: 14.2
<!--ID: 1779022050531-->
EEND
```
