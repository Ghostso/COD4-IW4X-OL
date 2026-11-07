param(
    [int]$Seconds = 70,
    [double]$Step = 2.0,
    [int]$ChainSeconds = 70,
    [int]$ShotSeconds = 40,
    [string]$Tag = ''
)
$ErrorActionPreference = 'Continue'

# Pure ASCII orchestrator.  Assumes it is already running ELEVATED (it is
# launched through the elevated agent).  It:
#   1) starts the read-only explorer before the game so the target PID is
#      captured as soon as it exists (the game PID churns once),
#   2) starts the frozen launch chain (capture_elevated_network.ps1),
#   3) takes short desktop screenshots of the in-game UI,
#   4) tears everything down.

$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$mainline = Join-Path $root 'CODOLServer\_mainline'
$runBase = Join-Path $root 'run_codol_001'
$chain = Join-Path $runBase 'capture_elevated_network.ps1'

if (-not $Tag) { $Tag = Get-Date -Format 'yyyyMMdd_HHmmss' }
$outRoot = Join-Path $mainline ('_pop3_run_' + $Tag)
$outDir = Join-Path $outRoot 'live'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Output ("OUT=" + $outRoot)
Write-Output ("ADMIN=" + $isAdmin)

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw 'python not found on PATH' }
$dumper = Join-Path $mainline '_pop3_live_dump.py'
$shotter = Join-Path $mainline '_pop_desktop_shot.py'

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 1) explorer first: it waits for the game to appear, then dumps it
$dmpArgs = @('-X', 'utf8', '-u', $dumper,
             '--out', $outDir, '--seconds', "$Seconds", '--step', "$Step")
$dmpProc = Start-Process -FilePath $py -ArgumentList $dmpArgs `
    -WorkingDirectory $mainline -PassThru `
    -RedirectStandardOutput (Join-Path $outRoot 'dump_stdout.txt') `
    -RedirectStandardError (Join-Path $outRoot 'dump_stderr.txt') `
    -WindowStyle Hidden
Write-Output ("DUMP_PID=" + $dmpProc.Id)

# 2) frozen launch chain
$chainArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass',
               '-File', $chain, '-DurationSeconds', "$ChainSeconds")
$chainProc = Start-Process -FilePath 'powershell.exe' -ArgumentList $chainArgs `
    -WorkingDirectory $runBase -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outRoot 'chain_stdout.txt') `
    -RedirectStandardError (Join-Path $outRoot 'chain_stderr.txt')
Write-Output ("CHAIN_PID=" + $chainProc.Id)

# 3) short screenshot series of the in-game UI
$shotDir = Join-Path $outRoot 'shots'
New-Item -ItemType Directory -Force -Path $shotDir | Out-Null
$shotEnd = (Get-Date).AddSeconds($ShotSeconds)
$n = 0
while ((Get-Date) -lt $shotEnd) {
    Start-Sleep -Seconds 3
    $n++
    $name = 'shot_{0:d2}.png' -f $n
    $p = Join-Path $shotDir $name
    try { & $py -X utf8 $shotter $p 2>&1 | Out-Null } catch { }
}
Write-Output ("SHOTS=" + $n)

# 4) wait for the explorer, then tear down
try { $dmpProc.WaitForExit(120000) | Out-Null } catch { }
Write-Output ("DUMP_EXITED=" + $dmpProc.HasExited)

Write-Output 'TASKKILL_BEGIN'
& taskkill.exe /F /IM codoMP_client_shipRetail.exe /T 2>&1 | Out-String | Write-Output
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
try { $chainProc.WaitForExit(8000) | Out-Null } catch { }
Write-Output 'TASKKILL_END'
Write-Output ("DONE=" + $outRoot)
