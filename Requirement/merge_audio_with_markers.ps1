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

function Resolve-RepoPath {
    param([string]$PathText)

    if ([System.IO.Path]::IsPathRooted($PathText)) {
        return [System.IO.Path]::GetFullPath($PathText)
    }

    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\$PathText"))
}

function Assert-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Get-SapiVoices {
    $voice = New-Object -ComObject SAPI.SpVoice
    try {
        $descriptions = @()
        foreach ($item in $voice.GetVoices()) {
            $descriptions += $item.GetDescription()
        }
        return $descriptions
    }
    finally {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice)
    }
}

function Select-SapiVoice {
    param(
        [string]$RequestedVoiceName
    )

    $voice = New-Object -ComObject SAPI.SpVoice
    try {
        $voices = @($voice.GetVoices())
        if ($voices.Count -eq 0) {
            throw "No SAPI voices are installed."
        }

        if ($RequestedVoiceName) {
            foreach ($item in $voices) {
                $description = $item.GetDescription()
                if ($description -like "*$RequestedVoiceName*") {
                    return @{ Voice = $voice; Token = $item; Description = $description }
                }
            }

            $available = ($voices | ForEach-Object { $_.GetDescription() }) -join "; "
            throw "Requested voice '$RequestedVoiceName' was not found. Available voices: $available"
        }

        foreach ($item in $voices) {
            $description = $item.GetDescription()
            if ($description -match "German|Deutsch|de-DE|de_DE") {
                return @{ Voice = $voice; Token = $item; Description = $description }
            }
        }

        $available = ($voices | ForEach-Object { $_.GetDescription() }) -join "; "
        throw "No German SAPI voice is installed. Available voices: $available"
    }
    catch {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice)
        throw
    }
}

function Invoke-FFmpeg {
    param([string[]]$FfmpegArgs)

    & ffmpeg @FfmpegArgs
    if ($LASTEXITCODE -ne 0) {
        throw "ffmpeg failed with exit code $LASTEXITCODE"
    }
}

function Convert-ToStageMp3 {
    param(
        [string]$SourceFile,
        [string]$TargetFile,
        [int]$Bitrate
    )

    Invoke-FFmpeg -FfmpegArgs @(
        "-y",
        "-i", $SourceFile,
        "-vn",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "${Bitrate}k",
        $TargetFile
    )
}

function New-TtsWaveFile {
    param(
        [string]$Text,
        [string]$TargetWave,
        [string]$RequestedVoiceName
    )

    $selection = Select-SapiVoice -RequestedVoiceName $RequestedVoiceName
    $voice = $selection.Voice
    $stream = New-Object -ComObject SAPI.SpFileStream

    try {
        $null = $voice.Voice = $selection.Token
        $stream.Open($TargetWave, 3, $true)
        $voice.AudioOutputStream = $stream
        $null = $voice.Speak($Text)
    }
    finally {
        try {
            $stream.Close()
        }
        catch {
        }

        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($stream)
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice)
    }
}

function Get-PromptClipPath {
    param(
        [string]$Mode,
        [string]$PromptBaseDir,
        [string]$StageDir,
        [int]$PartNumber,
        [string]$TextTemplate,
        [string]$Prefix,
        [int]$Bitrate,
        [string]$RequestedVoiceName
    )

    if ($Mode -eq "Recorded") {
        $fileName = if ($Prefix -eq "intro") {
            "teil_$PartNumber.mp3"
        }
        else {
            "ende_des_teil_$PartNumber.mp3"
        }

        $path = Join-Path $PromptBaseDir $fileName
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Recorded prompt file not found: $path"
        }
        return $path
    }

    $text = [string]::Format($TextTemplate, $PartNumber)
    $wavePath = Join-Path $StageDir ("{0}_{1:00}.wav" -f $Prefix, $PartNumber)
    $mp3Path = Join-Path $StageDir ("{0}_{1:00}.mp3" -f $Prefix, $PartNumber)

    New-TtsWaveFile -Text $text -TargetWave $wavePath -RequestedVoiceName $RequestedVoiceName
    Convert-ToStageMp3 -SourceFile $wavePath -TargetFile $mp3Path -Bitrate $Bitrate
    Remove-Item -LiteralPath $wavePath -Force

    return $mp3Path
}

Assert-Command -Name "ffmpeg"

if ($ListVoices) {
    Write-Host "Installed SAPI voices:"
    Get-SapiVoices | ForEach-Object { Write-Host " - $_" }
    exit 0
}

$inputDirPath = Resolve-RepoPath -PathText $InputDir
$outputFilePath = Resolve-RepoPath -PathText $OutputFile
$promptDirPath = Resolve-RepoPath -PathText $PromptDir

if (-not (Test-Path -LiteralPath $inputDirPath)) {
    throw "Input directory not found: $inputDirPath"
}

$sourceFiles = Get-ChildItem -LiteralPath $inputDirPath -File |
    Sort-Object Name |
    Where-Object { $_.Extension -match "^\.(mp3|wav|m4a)$" }

if ($sourceFiles.Count -eq 0) {
    throw "No audio files found in $inputDirPath"
}

$outputDir = Split-Path -Path $outputFilePath -Parent
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$stageRoot = Join-Path $outputDir "_merge_stage"
if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stageRoot | Out-Null

$concatListPath = Join-Path $stageRoot "concat.txt"
$concatLines = New-Object System.Collections.Generic.List[string]

try {
    Write-Host ""
    Write-Host "Audio merge with Teil markers"
    Write-Host "Input : $inputDirPath"
    Write-Host "Output: $outputFilePath"
    Write-Host "Mode  : $PromptMode"
    Write-Host ""

    for ($index = 0; $index -lt $sourceFiles.Count; $index++) {
        $partNumber = $index + 1
        $source = $sourceFiles[$index]
        Write-Host ("[{0}/{1}] {2}" -f $partNumber, $sourceFiles.Count, $source.Name)

        $introClip = Get-PromptClipPath `
            -Mode $PromptMode `
            -PromptBaseDir $promptDirPath `
            -StageDir $stageRoot `
            -PartNumber $partNumber `
            -TextTemplate $IntroTemplate `
            -Prefix "intro" `
            -Bitrate $BitrateKbps `
            -RequestedVoiceName $VoiceName

        $stageSource = Join-Path $stageRoot ("source_{0:00}.mp3" -f $partNumber)
        Convert-ToStageMp3 -SourceFile $source.FullName -TargetFile $stageSource -Bitrate $BitrateKbps

        $outroClip = Get-PromptClipPath `
            -Mode $PromptMode `
            -PromptBaseDir $promptDirPath `
            -StageDir $stageRoot `
            -PartNumber $partNumber `
            -TextTemplate $OutroTemplate `
            -Prefix "outro" `
            -Bitrate $BitrateKbps `
            -RequestedVoiceName $VoiceName

        foreach ($segment in @($introClip, $stageSource, $outroClip)) {
            $escaped = $segment.Replace("'", "''")
            $concatLines.Add("file '$escaped'")
        }
    }

    Set-Content -LiteralPath $concatListPath -Value $concatLines -Encoding ASCII

    Invoke-FFmpeg -FfmpegArgs @(
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", $concatListPath,
        "-c", "copy",
        $outputFilePath
    )

    Write-Host ""
    Write-Host "Done."
    Write-Host "Merged file created at:"
    Write-Host "  $outputFilePath"
}
finally {
    if ($KeepTempFiles) {
        Write-Host ""
        Write-Host "Kept temp files at:"
        Write-Host "  $stageRoot"
    }
    elseif (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
