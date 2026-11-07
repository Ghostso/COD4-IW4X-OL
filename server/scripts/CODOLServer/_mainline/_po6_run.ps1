param(
    [int]$Seconds = 200,
    [double]$Step = 1.2,
    [string]$Tag = ''
)
$ErrorActionPreference = 'Continue'

# POP6 orchestrator: run the FROZEN launch chain and watch the popup live.
#
# It must run ELEVATED (launched through the elevated agent), because:
#   * the game chain itself needs admin,
#   * only an elevated process reliably brings the DirectX window forward so
#     the desktop BitBlt actually captures the game instead of the occluder.
#
# What it does, in order:
#   1. writes the popup-watcher script next to the launcher (pure ASCII),
#   2. starts the popup watcher (writes jsonl + saves a bmp on every hit),
#   3. runs the frozen direct chain: run_direct_iips1_elevated.ps1,
#   4. waits, then collects both logs and kills the tree.

$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$runBase = Join-Path $root 'run_codol_001'
$chain = Join-Path $runBase 'run_direct_iips1_elevated.ps1'
$sandbox = Join-Path $runBase 'sandbox_ifs1_20260923'
$mainline = Join-Path $here ''

if (-not $Tag) { $Tag = Get-Date -Format 'yyyyMMdd_HHmmss' }
$outRoot = Join-Path $mainline ('_po6_run_' + $Tag)
$liveDir = Join-Path $outRoot 'live'
$chainDir = Join-Path $outRoot 'chain'
New-Item -ItemType Directory -Force -Path $liveDir | Out-Null
New-Item -ItemType Directory -Force -Path $chainDir | Out-Null

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Output ('OUT=' + $outRoot)
Write-Output ('ADMIN=' + $isAdmin)

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw 'python not found on PATH' }
$watcher = Join-Path $mainline '_po5_live_pop.py'

# tear down any previous run first
Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 1) popup watcher first, so it is already polling when the window appears
$wArgs = @('-X', 'utf8', '-u', $watcher,
           '--out', $liveDir, '--seconds', "$Seconds", '--step', "$Step",
           '--save-on-panel', '1')
$wProc = Start-Process -FilePath $py -ArgumentList $wArgs `
    -WorkingDirectory $mainline -PassThru `
    -RedirectStandardOutput (Join-Path $outRoot 'watch_stdout.txt') `
    -RedirectStandardError  (Join-Path $outRoot 'watch_stderr.txt') `
    -WindowStyle Hidden
Write-Output ('WATCH_PID=' + $wProc.Id)
Start-Sleep -Seconds 2

# 2) frozen chain
$cArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $chain,
           '-Sandbox', $sandbox, '-DurationSeconds', "$Seconds",
           '-RunDir', $chainDir)
$cProc = Start-Process -FilePath 'powershell.exe' -ArgumentList $cArgs `
    -WorkingDirectory $runBase -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outRoot 'chain_stdout.txt') `
    -RedirectStandardError  (Join-Path $outRoot 'chain_stderr.txt')
Write-Output ('CHAIN_PID=' + $cProc.Id)

# 3) live commentary: print popup hits as they happen
$jsonl = Join-Path $liveDir 'live_pop.jsonl'
$deadline = (Get-Date).AddSeconds($Seconds + 30)
$lastN = 0
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if (Test-Path $jsonl) {
        $lines = @(Get-Content -LiteralPath $jsonl -ErrorAction SilentlyContinue)
        if ($lines.Count -gt $lastN) {
            for ($i = $lastN; $i -lt $lines.Count; $i++) {
                $ln = $lines[$i]
                if ($ln -match '"panel": true' -or $ln -match 'PANEL_') {
                    Write-Output ('HIT ' + $ln)
                }
            }
            $lastN = $lines.Count
        }
    }
    # stop early once the chain process is gone and the game is gone
    $cProc.Refresh()
    $game = Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue
    if ($cProc.HasExited -and -not $game) { break }
}

# 4) teardown + collect
Write-Output 'TASKKILL_BEGIN'
& taskkill.exe /F /IM codoMP_client_shipRetail.exe /T 2>&1 | Out-String | Write-Output
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
try { $wProc.WaitForExit(20000) | Out-Null } catch { }
try { $cProc.WaitForExit(8000) | Out-Null } catch { }
Write-Output 'TASKKILL_END'
Write-Output ('DONE=' + $outRoot)
