param(
    [int]$DurationSeconds = 180,
    [string]$RunDir = ''
)
$ErrorActionPreference = 'Continue'

# POP7: pure launcher wrapper.  Runs the FROZEN direct chain elevated and
# leaves it running, so an external dumper can attach while the game is up.

# Derive the project root from this script's own location so the file stays
# pure ASCII: PowerShell 5.1 reads .ps1 as GBK, so a literal CJK path here
# would be mangled and the chain script would appear to "not exist".
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $here)
$runBase = Join-Path $root 'run_codol_001'
$chain = Join-Path $runBase 'run_direct_iips1_elevated.ps1'
$sandbox = Join-Path $runBase 'sandbox_ifs1_20260923'

if (-not $RunDir) {
    $RunDir = Join-Path $root ('CODOLServer\_po7_chain_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
}
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Output ('RUNDIR=' + $RunDir)
Write-Output ('ADMIN=' + $isAdmin)

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $chain `
    -Sandbox $sandbox -DurationSeconds $DurationSeconds -RunDir $RunDir
Write-Output ('CHAIN_EXIT=' + $LASTEXITCODE)
