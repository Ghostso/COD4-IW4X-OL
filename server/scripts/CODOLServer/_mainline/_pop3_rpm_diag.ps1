param(
    [int]$LaunchDelay = 8,
    [int]$AfterSeconds = 8
)
$ErrorActionPreference = 'Continue'

# Pure ASCII diagnostic: launch the game from this elevated shell, then run
# both _pop3_rpm_diag.py (raw RPM primitives) and engine_dump.py (the harness
# that provably succeeded before) against the SAME live process.

$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$mainline = Join-Path $root 'CODOLServer\_mainline'
$sandbox = Join-Path $root 'run_codol_001\sandbox_ifs1_20260923'
$game = Join-Path $sandbox 'codoMP_client_shipRetail.exe'

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outRoot = Join-Path $mainline ('_pop3_diag_' + $stamp)
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
$outDir = Join-Path $outRoot 'live'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Output ("OUT=" + $outRoot)
Write-Output ("ADMIN=" + ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator))

$py = (Get-Command python -ErrorAction SilentlyContinue).Source

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

# A) raw primitives
Write-Output '=== RPM DIAG ==='
& $py -X utf8 -u (Join-Path $mainline '_pop3_rpm_diag.py') $gp.Id 2>&1 |
    Tee-Object -FilePath (Join-Path $outRoot 'rpm_diag.txt')

# B) engine_dump.py on the very same process, 8s window
Write-Output '=== ENGINE_DUMP (control) ==='
& $py -X utf8 -u (Join-Path $mainline 'engine_dump.py') $gp.Id `
    --out $outDir --seconds $AfterSeconds --step 2 --wait-seconds 4 2>&1 |
    Tee-Object -FilePath (Join-Path $outRoot 'engine_dump.txt')

Write-Output 'TASKKILL_BEGIN'
& taskkill.exe /F /IM codoMP_client_shipRetail.exe /T 2>&1 | Out-String | Write-Output
Write-Output 'TASKKILL_END'
Write-Output ("DONE=" + $outRoot)
