# EB-003 - build an isolated game tree for condition B.
#
# The real install is never written to. Every top-level entry is junctioned (dirs)
# or hardlinked (files) back to the original, EXCEPT IIPS\, which is a real
# directory whose contents are copies of the originals with one substitution:
# iips.dll is replaced by LocalRM_v3.dll.
#
# Result: A and B differ in exactly one file (IIPS\iips.dll), so any behavioural
# difference is attributable to the provider module, not to the environment.
#
# Usage: & restore003\mk_sandbox.ps1 -Sandbox '<workspace>\restore003\sandbox_B'
param(
    [Parameter(Mandatory = $true)][string]$Sandbox,
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference = 'Stop'

$src = Join-Path $Root 'COD OL'
$v3 = Join-Path $Root 'LocalRM_v3.dll'
if (-not (Test-Path -LiteralPath $src)) { throw "source game dir missing: $src" }
if (-not (Test-Path -LiteralPath $v3)) { throw "provider missing: $v3" }

$sbx = [System.IO.Path]::GetFullPath($Sandbox)
Write-Output "sandbox = $sbx"

if (Test-Path -LiteralPath $sbx) {
    Write-Output "removing pre-existing sandbox"
    # Only ever remove the explicitly-named sandbox directory.
    if ($sbx -notlike "$Root\restore003\*") { throw "refusing to remove outside restore003: $sbx" }
    Remove-Item -LiteralPath $sbx -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $sbx | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $sbx 'IIPS') | Out-Null

foreach ($e in Get-ChildItem -LiteralPath $src -Force) {
    if ($e.Name -eq 'IIPS') { continue }
    $target = Join-Path $sbx $e.Name
    if ($e.PSIsContainer) {
        cmd /c mklink /J "`"$target`"" "`"$($e.FullName)`"" | Out-Null
    } else {
        cmd /c mklink /H "`"$target`"" "`"$($e.FullName)`"" | Out-Null
    }
}

# IIPS: subdirs junctioned, files copied -- except iips.dll which becomes LocalRM_v3.
$srcIIPS = Join-Path $src 'IIPS'
foreach ($e in Get-ChildItem -LiteralPath $srcIIPS -Force) {
    $target = Join-Path (Join-Path $sbx 'IIPS') $e.Name
    if ($e.PSIsContainer) {
        cmd /c mklink /J "`"$target`"" "`"$e.FullName`"" | Out-Null
    } else {
        if ($e.Name -eq 'iips.dll') { continue }
        Copy-Item -LiteralPath $e.FullName -Destination $target -Force
    }
}

# The single substitution.
Copy-Item -LiteralPath $v3 -Destination (Join-Path $sbx 'IIPS\iips.dll') -Force

$b = Join-Path $sbx 'IIPS\iips.dll'
Write-Output ""
Write-Output "sandbox ready"
Write-Output ("  IIPS\iips.dll = {0} bytes  sha256 {1}" -f (Get-Item -LiteralPath $b).Length,
    (Get-FileHash -LiteralPath $b -Algorithm SHA256).Hash)
Write-Output ("  original      = {0} bytes  sha256 {1}" -f
    (Get-Item -LiteralPath (Join-Path $srcIIPS 'iips.dll')).Length,
    (Get-FileHash -LiteralPath (Join-Path $srcIIPS 'iips.dll') -Algorithm SHA256).Hash)
