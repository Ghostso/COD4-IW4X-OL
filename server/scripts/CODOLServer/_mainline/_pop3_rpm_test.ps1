param(
    [int]$Seconds = 14,
    [int]$LaunchDelay = 6,
    [string]$Tag = ''
)
$ErrorActionPreference = 'Continue'

# Pure ASCII.  Diagnostic: does ReadProcessMemory work on the game main module
# when the game is started from THIS elevated shell (the pattern used by the
# proven engine_dump harness) rather than from the capture chain?

$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$mainline = Join-Path $root 'CODOLServer\_mainline'
$sandbox = Join-Path $root 'run_codol_001\sandbox_ifs1_20260923'
$game = Join-Path $sandbox 'codoMP_client_shipRetail.exe'

if (-not $Tag) { $Tag = Get-Date -Format 'yyyyMMdd_HHmmss' }
$outRoot = Join-Path $mainline ('_pop3_rpm_' + $Tag)
$outDir = Join-Path $outRoot 'live'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Output ("OUT=" + $outRoot)
Write-Output ("ADMIN=" + ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator))

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
$dumper = Join-Path $mainline '_pop3_live_dump.py'

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

$gp = Start-Process -FilePath $game `
    -ArgumentList @('-q', '--disable-gpu', '--disable-gpu-compositing') `
    -WorkingDirectory $sandbox -PassThru
Write-Output ("GAME_PID=" + $gp.Id)
Start-Sleep -Seconds $LaunchDelay

& $py -X utf8 -u $dumper --pid $gp.Id --out $outDir `
    --seconds $Seconds --step 2 2>&1 |
    Tee-Object -FilePath (Join-Path $outRoot 'dump_stdout.txt')

Write-Output 'TASKKILL_BEGIN'
& taskkill.exe /F /IM codoMP_client_shipRetail.exe /T 2>&1 | Out-String | Write-Output
Write-Output 'TASKKILL_END'
Write-Output ("DONE=" + $outRoot)
