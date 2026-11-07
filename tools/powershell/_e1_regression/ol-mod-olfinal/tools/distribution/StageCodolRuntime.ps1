[CmdletBinding()]
param(
    [ValidateSet("debug", "release")]
    [string]$Mode = "release",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$StageRoot = Join-Path $Repository "build\stage\codol"
$BuildStageRoot = [System.IO.Path]::GetFullPath((Join-Path $Repository "build\stage"))
$StageFullPath = [System.IO.Path]::GetFullPath($StageRoot)

if (-not $StageFullPath.StartsWith($BuildStageRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean a stage directory outside $BuildStageRoot"
}

if (-not $SkipBuild) {
    $BuildScript = Join-Path $Repository "tools\build.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BuildScript -Action build -Mode $Mode
    if ($LASTEXITCODE -ne 0) {
        throw "xmake build failed with exit code $LASTEXITCODE"
    }
}

$ContractPath = Join-Path $Repository "distribution\runtime-components.json"
$Contract = Get-Content -LiteralPath $ContractPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Contract.schemaVersion -ne 1 -or $Contract.titleId -ne 1004 -or $Contract.architecture -ne "x86") {
    throw "Unsupported or invalid runtime component contract: $ContractPath"
}

if (Test-Path -LiteralPath $StageFullPath) {
    Remove-Item -LiteralPath $StageFullPath -Recurse -Force
}
New-Item -ItemType Directory -Path $StageFullPath -Force | Out-Null

$ManifestEntries = [System.Collections.Generic.List[object]]::new()

function Get-RelativePath([string]$BasePath, [string]$Path) {
    $BaseFullPath = [System.IO.Path]::GetFullPath($BasePath).TrimEnd("\") + "\"
    $FileFullPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $FileFullPath.StartsWith($BaseFullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside its expected root: $FileFullPath"
    }
    return $FileFullPath.Substring($BaseFullPath.Length).Replace("\", "/")
}

function Assert-Pe32([string]$Path) {
    $Bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($Bytes.Length -lt 0x40 -or $Bytes[0] -ne 0x4D -or $Bytes[1] -ne 0x5A) {
        throw "Expected a PE image: $Path"
    }
    $PeOffset = [BitConverter]::ToInt32($Bytes, 0x3C)
    if ($PeOffset -lt 0 -or $PeOffset + 6 -gt $Bytes.Length -or
        $Bytes[$PeOffset] -ne 0x50 -or $Bytes[$PeOffset + 1] -ne 0x45) {
        throw "Invalid PE header: $Path"
    }
    $Machine = [BitConverter]::ToUInt16($Bytes, $PeOffset + 4)
    if ($Machine -ne 0x014C) {
        throw ("Runtime component is not PE32/x86 (machine 0x{0:X4}): {1}" -f $Machine, $Path)
    }
}

function Add-ManifestEntry($Component, [string]$SourceFile, [string]$DestinationFile) {
    $RelativeDestination = Get-RelativePath $StageFullPath $DestinationFile
    $Item = Get-Item -LiteralPath $DestinationFile
    $ManifestEntries.Add([ordered]@{
        path = $RelativeDestination
        size = $Item.Length
        sha256 = (Get-FileHash -LiteralPath $DestinationFile -Algorithm SHA256).Hash
        source = Get-RelativePath $Repository $SourceFile
        kind = [string]$Component.kind
        origin = [string]$Component.origin
        role = [string]$Component.role
        installPolicy = [string]$Component.installPolicy
        mutable = [bool]$Component.mutable
    })
}

foreach ($Component in $Contract.components) {
    $SourceRelative = ([string]$Component.source).Replace('${configuration}', $Mode)
    $Source = Join-Path $Repository $SourceRelative
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Missing runtime source: $Source"
    }

    if ($Component.sha256) {
        $ActualHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
        if ($ActualHash -ne [string]$Component.sha256) {
            throw "Archived source hash mismatch: $Source"
        }
    }

    if ((Test-Path -LiteralPath $Source -PathType Container) -and $Component.hashes) {
        $SourceRoot = [System.IO.Path]::GetFullPath($Source).TrimEnd("\") + "\"
        $SourceFiles = @(Get-ChildItem -LiteralPath $Source -Recurse -File)
        $ExpectedHashes = @{}
        foreach ($Property in $Component.hashes.PSObject.Properties) {
            $ExpectedHashes[$Property.Name.Replace("\", "/")] = [string]$Property.Value
        }
        if ($SourceFiles.Count -ne $ExpectedHashes.Count) {
            throw "Archived directory file count mismatch: $Source"
        }
        foreach ($SourceFile in $SourceFiles) {
            $Relative = $SourceFile.FullName.Substring($SourceRoot.Length).Replace("\", "/")
            if (-not $ExpectedHashes.ContainsKey($Relative)) {
                throw "Unexpected file in archived directory: $($SourceFile.FullName)"
            }
            $ActualHash = (Get-FileHash -LiteralPath $SourceFile.FullName -Algorithm SHA256).Hash
            if ($ActualHash -ne $ExpectedHashes[$Relative]) {
                throw "Archived source hash mismatch: $($SourceFile.FullName)"
            }
        }
    }

    $Destination = Join-Path $StageFullPath ([string]$Component.destination)
    if (Test-Path -LiteralPath $Source -PathType Container) {
        Get-ChildItem -LiteralPath $Source -Recurse -File | ForEach-Object {
            $SourceRoot = [System.IO.Path]::GetFullPath($Source).TrimEnd("\") + "\"
            $Relative = $_.FullName.Substring($SourceRoot.Length)
            $DestinationFile = Join-Path $Destination $Relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $DestinationFile) -Force | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $DestinationFile -Force
            Add-ManifestEntry $Component $_.FullName $DestinationFile
        }
    } else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
        Add-ManifestEntry $Component $Source $Destination
    }
}

$Forbidden = Get-ChildItem -LiteralPath $StageFullPath -Recurse -File | Where-Object {
    $_.Name -match '(?i)(64|CODOLBackend)' -or
    $_.FullName -match '(?i)\\(Logs|Backups)\\'
}
if ($Forbidden) {
    throw "Forbidden files entered the CODOL x86 stage: $($Forbidden.FullName -join ', ')"
}

$TitleRoot = Join-Path $StageFullPath "Ayria\Assets\Alwaysoffline"
$UnexpectedTitles = Get-ChildItem -LiteralPath $TitleRoot -Directory | Where-Object { $_.Name -ne "1004" }
if ($UnexpectedTitles) {
    throw "Non-CODOL title assets entered the stage: $($UnexpectedTitles.Name -join ', ')"
}

$PeFiles = Get-ChildItem -LiteralPath $StageFullPath -Recurse -File | Where-Object {
    $_.Extension -in ".exe", ".dll", ".Ayria32", ".Localnet32"
}
foreach ($PeFile in $PeFiles) {
    Assert-Pe32 $PeFile.FullName
}

$Manifest = [ordered]@{
    schemaVersion = 1
    project = "ol-mod"
    titleId = 1004
    architecture = "x86"
    configuration = $Mode
    gameExecutable = [string]$Contract.gameExecutable
    files = @($ManifestEntries | Sort-Object path)
}
$ManifestPath = Join-Path $StageFullPath "ol-mod-runtime-manifest.json"
$Manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8

Write-Host "Staged CODOL runtime: $StageFullPath"
Write-Host "Files: $($ManifestEntries.Count)"
Write-Host "Manifest: $ManifestPath"
