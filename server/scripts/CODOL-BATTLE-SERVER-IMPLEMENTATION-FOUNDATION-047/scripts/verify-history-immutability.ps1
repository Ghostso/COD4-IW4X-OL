# Verify that 040-046 deliverables and the original v0.1 source were not modified by 047.
# Baseline hashes were taken before 047 code work started.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$hashFile = Join-Path $root 'evidence\040_046_BASELINE_SHA256.tsv'
if (-not (Test-Path -LiteralPath $hashFile)) { throw "missing $hashFile" }
$workspace = Split-Path -Parent $root
$failures = 0
$checked = 0
foreach ($line in Get-Content -LiteralPath $hashFile) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) { continue }
    $parts = $line -split "`t", 2
    if ($parts.Count -ne 2) { throw "malformed hash line: $line" }
    $expected = $parts[0]
    $relative = $parts[1]
    $full = Join-Path $workspace $relative
    if (-not (Test-Path -LiteralPath $full)) { Write-Host "MISSING $relative"; $failures++; continue }
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $full).Hash
    $checked++
    if ($actual -ne $expected) { Write-Host "CHANGED $relative"; $failures++ }
}
Write-Host "checked=$checked failures=$failures"
if ($failures -ne 0) { exit 1 }
Write-Host 'HISTORY_IMMUTABLE_OK'
