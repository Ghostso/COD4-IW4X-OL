[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$GameDirectory,
    [ValidateSet("debug", "release")]
    [string]$Mode = "release",
    [switch]$SkipBuild,
    [switch]$ReplacePlayerState
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$GameRoot = (Resolve-Path -LiteralPath $GameDirectory).Path
$GameExecutable = Join-Path $GameRoot "codoMP_client_shipRetail.exe"
if (-not (Test-Path -LiteralPath $GameExecutable -PathType Leaf)) {
    throw "Not a CODOL 3.3.3.3 game directory: $GameRoot"
}

$StageScript = Join-Path $PSScriptRoot "StageCodolRuntime.ps1"
& $StageScript -Mode $Mode -SkipBuild:$SkipBuild
$StageRoot = Join-Path $Repository "build\stage\codol"
$ManifestPath = Join-Path $StageRoot "ol-mod-runtime-manifest.json"
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$Installed = 0
$Preserved = 0
$Unchanged = 0
foreach ($Entry in $Manifest.files) {
    $Source = Join-Path $StageRoot ([string]$Entry.path)
    $Destination = Join-Path $GameRoot ([string]$Entry.path)
    if ($Entry.installPolicy -eq "if-missing" -and
        -not $ReplacePlayerState -and
        (Test-Path -LiteralPath $Destination -PathType Leaf)) {
        $Preserved++
        continue
    }
    if ((Test-Path -LiteralPath $Destination -PathType Leaf) -and
        (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash -eq
            [string]$Entry.sha256) {
        $Unchanged++
        continue
    }

    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    $Installed++
}

Copy-Item -LiteralPath $ManifestPath -Destination (Join-Path $GameRoot "Ayria\ol-mod-runtime-manifest.json") -Force

Write-Host "Installed ol-mod runtime into: $GameRoot"
Write-Host "Files installed: $Installed"
Write-Host "Unchanged files skipped: $Unchanged"
Write-Host "Existing player-state files preserved: $Preserved"
