# CODOL Combat Server v0.1 -- reproducible build script (ASCII only: works under any console codepage)
#
# Why csc.exe: this machine has no usable C++ toolchain. Evidence: docs/TOOLCHAIN_ENVIRONMENT.md.
# This script does not use the network, does not write outside the repo, and does not touch
# any frozen baseline.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1 -Configuration debug
param(
    [ValidateSet('release','debug')]
    [string]$Configuration = 'release',
    [string]$OutDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrEmpty($OutDir)) { $OutDir = Join-Path $root 'build\bin' }

$cscCandidates = @(
    "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
    "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)
$csc = $cscCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $csc) { throw "csc.exe (.NET Framework 4.0) not found. candidates: $($cscCandidates -join ', ')" }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
# ---- Optional pre-build: regenerate session-descriptor golden vectors ----
# Those are fixed bytes copied from the frozen reference implementation
# (REF_LOBBY_KIT/codol_crypto.py). Regenerate only when you intend to realign,
# because it overwrites src/Codol/SessionGolden.cs (a tracked source file):
#   $env:CODOL_REGEN_GOLDEN = '1'
$srcDir = Join-Path $root 'src'
if ($env:CODOL_REGEN_GOLDEN -eq '1') {
    $gen = Join-Path $root 'testsgen_session_golden.py'
    if (Test-Path $gen) {
        Write-Host '  [preflight] regenerating session golden vectors...'
        & python -X utf8 $gen
        if ($LASTEXITCODE -ne 0) { throw 'golden vector regeneration failed' }
    } else {
        Write-Warning "  [preflight] $gen not found - skipping golden regeneration"
    }
}
$sources = Get-ChildItem -Path $srcDir -Recurse -Filter '*.cs' | ForEach-Object { $_.FullName }
if ($sources.Count -eq 0) { throw "no .cs sources under src" }

$outExe = Join-Path $OutDir 'CODOLCombatServer.exe'

$cscArgs = @('/nologo', '/target:exe', '/platform:x86', '/warn:4', ("/out:" + $outExe))
if ($Configuration -eq 'release') { $cscArgs += '/optimize+' } else { $cscArgs += '/define:DEBUG' }
$cscArgs += $sources

Write-Host "== CODOL Combat Server v0.1 build =="
Write-Host "  csc        : $csc"
Write-Host "  config     : $Configuration"
Write-Host "  sources    : $($sources.Count)"
Write-Host "  output     : $outExe"

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$out = & $csc @cscArgs 2>&1
$code = $LASTEXITCODE
$sw.Stop()

$out | ForEach-Object { Write-Host $_ }

$logDir = Join-Path $root 'build\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir ("build_" + $Configuration + "_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".log")
@(
    "command: $csc $($cscArgs -join ' ')",
    "exit: $code",
    "elapsed_ms: $($sw.ElapsedMilliseconds)",
    "---- output ----"
) + $out | Set-Content -Encoding utf8 $logPath
Write-Host "  build log  : $logPath"

if ($code -ne 0) { throw "build failed, exit=$code (see $logPath)" }

$h = Get-FileHash -Algorithm SHA256 $outExe

# ---- Source fingerprint (MUST be computed AFTER a successful build) ----
# The local csc (.NET Framework 4.0) does NOT support /deterministic, so the exe
# SHA-256 changes on every compile (fresh MVID) while the size stays constant.
# Reproducibility is therefore pinned to the SOURCE instead:
#   fingerprint = SHA256( per source file: relative-path + 0x00 + content,
#                         sorted by path ordinal )
# It depends only on source content, not on time, order or machine. The self-test
# recomputes it and asserts equality -> proves this exe came from this source.
# NOTE: computing it BEFORE the build would describe new source with the OLD exe.
$fingerprint = & $outExe --fingerprint
# --fingerprint prints "SOURCE_SHA256=<hex>"; take that line
$fpLine = ($fingerprint | Where-Object { $_ -like 'SOURCE_SHA256=*' } | Select-Object -First 1)
$fp = if ($fpLine) { $fpLine.Substring('SOURCE_SHA256='.Length) } else { 'unavailable' }
$srcList = $sources | ForEach-Object { "$([System.IO.Path]::GetFileName($_)) $((Get-FileHash -Algorithm SHA256 $_).Hash)" }
Write-Host "  src fp     : $fp"

$manifest = Join-Path $OutDir 'BUILD_MANIFEST.txt'
@(
    "artifact: $outExe",
    "size: $((Get-Item $outExe).Length)",
    "sha256: $($h.Hash)",
    "source_sha256: $fp",
    "configuration: $Configuration",
    "csc: $csc",
    "sources: $($sources.Count)",
    "built_at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
) + $srcList | Set-Content -Encoding utf8 $manifest
Write-Host "  manifest   : $manifest"
Write-Host "  SHA-256    : $($h.Hash)"
Write-Host "BUILD OK"
