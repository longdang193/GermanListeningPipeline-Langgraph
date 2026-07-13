param(
    [string]$InputDir = "Audios/Merge",
    [string]$OutputFile = "Outputs/Merge/merged-with-markers.mp3",
    [ValidateSet("Generated", "Recorded")]
    [string]$PromptMode = "Generated",
    [string]$PromptDir = "Audios/MergePrompts",
    [string]$VoiceName = "",
    [string]$IntroTemplate = "Teil {0}",
    [string]$OutroTemplate = "Ende des Teil {0}",
    [int]$BitrateKbps = 192,
    [switch]$ListVoices,
    [switch]$KeepTempFiles
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$toolsSrc = Join-Path $repoRoot "Tools\src"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$toolsSrc;$env:PYTHONPATH" } else { $toolsSrc }

$argsList = @("-m", "glist_pipeline.cli", "merge")

if ($ListVoices) {
    $argsList += @(
        "--input-dir", $InputDir,
        "--output-file", $OutputFile,
        "--markers", "with",
        "--list-voices"
    )
}
else {
    $argsList += @(
        "--input-dir", $InputDir,
        "--output-file", $OutputFile,
        "--markers", "with",
        "--prompt-mode", $PromptMode.ToLowerInvariant(),
        "--bitrate-kbps", "$BitrateKbps"
    )

    if ($KeepTempFiles) {
        $argsList += "--keep-temp-files"
    }
    if ($PromptMode -eq "Recorded") {
        $argsList += @("--prompt-dir", $PromptDir)
    }
    elseif ($VoiceName) {
        $argsList += @("--voice-name", $VoiceName)
    }
}

# ponytail: templates kept for compatibility only; wire through when merge engine owns custom text templates.
if ($IntroTemplate -ne "Teil {0}" -or $OutroTemplate -ne "Ende des Teil {0}") {
    Write-Warning "Custom IntroTemplate/OutroTemplate are not supported by delegated wrapper yet. Using CLI defaults."
}

& python @argsList
exit $LASTEXITCODE
