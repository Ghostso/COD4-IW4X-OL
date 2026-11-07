param(
    [int]$Seconds = 100,
    [double]$Step = 2.0,
    [double]$ShotEvery = 2.0
)
$ErrorActionPreference = 'Continue'

# Pure ASCII.  Project root is derived from this script's location.
$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)
$mainline = Join-Path $root 'CODOLServer\_mainline'
$sandbox = Join-Path $root 'run_codol_001\sandbox_ifs1_20260923'
$game = Join-Path $sandbox 'codoMP_client_shipRetail.exe'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outRoot = Join-Path $mainline ('_dyn100_run_' + $stamp)
$liveDir = Join-Path $outRoot 'live'
$shotDir = Join-Path $outRoot 'shots'
$windowDir = Join-Path $outRoot 'windows'
New-Item -ItemType Directory -Force -Path $liveDir, $shotDir, $windowDir | Out-Null

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw 'python not found on PATH' }
if (-not (Test-Path -LiteralPath $game)) { throw ('game missing: ' + $game) }

Write-Output ('OUT=' + $outRoot)
Write-Output ('ADMIN=' + ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator))

# Cleanup only the target game process.  ACE and network state are untouched.
Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

$mem = Join-Path $mainline '_dyn100_mem.py'
$shot = Join-Path $mainline '_pop_desktop_shot.py'
$watch = Join-Path $mainline '_popup_watch.py'
if (-not (Test-Path -LiteralPath $mem)) { throw ('memory tracer missing: ' + $mem) }
if (-not (Test-Path -LiteralPath $shot)) { throw ('screenshot tool missing: ' + $shot) }
if (-not (Test-Path -LiteralPath $watch)) { throw ('window watcher missing: ' + $watch) }

$memLog = Join-Path $outRoot 'mem_stdout.txt'
$memErr = Join-Path $outRoot 'mem_stderr.txt'
$memArgs = @('-X', 'utf8', '-u', $mem, '--exe', $game, '--cwd', $sandbox,
             '--out', $liveDir, '--seconds', "$Seconds", '--step', "$Step")
$memProc = Start-Process -FilePath $py -ArgumentList $memArgs `
    -WorkingDirectory $mainline -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $memLog -RedirectStandardError $memErr
Write-Output ('MEM_PID=' + $memProc.Id)

$winLog = Join-Path $windowDir 'watch_stdout.txt'
$winErr = Join-Path $windowDir 'watch_stderr.txt'
$winProc = Start-Process -FilePath $py `
    -ArgumentList @('-X', 'utf8', '-u', $watch, '--out', $windowDir,
                    '--seconds', "$Seconds", '--shot-every', "$ShotEvery") `
    -WorkingDirectory $mainline -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $winLog -RedirectStandardError $winErr
Write-Output ('WATCH_PID=' + $winProc.Id)

# Desktop BitBlt is the only reliable way to see the GFx-rendered panel.
$t0 = Get-Date
$n = 0
while (((Get-Date) - $t0).TotalSeconds -lt $Seconds) {
    Start-Sleep -Seconds 2
    $n++
    $p = Join-Path $shotDir ('desktop_{0:d3}.png' -f $n)
    try { & $py -X utf8 $shot $p 2>&1 | Out-Null } catch { }
}

try { $memProc.WaitForExit(30000) | Out-Null } catch { }
try { $winProc.WaitForExit(10000) | Out-Null } catch { }

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object {
        Write-Output ('KILL_GAME=' + $_.Id)
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }

Write-Output ('MEM_EXITED=' + $memProc.HasExited)
Write-Output ('WATCH_EXITED=' + $winProc.HasExited)
Write-Output ('SHOTS=' + $n)
Write-Output ('DONE=' + $outRoot)
