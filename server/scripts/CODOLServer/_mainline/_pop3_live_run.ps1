param(
    [int]$Seconds = 55,
    [double]$Step = 2.0,
    [int]$ChainSeconds = 55
)
$ErrorActionPreference = 'Continue'

# Pure ASCII.  The project root contains CJK, so it is derived from the
# script location instead of being written literally (PowerShell 5.1 reads
# .ps1 files as GBK).
$here = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $here)

$mainline = Join-Path $root 'CODOLServer\_mainline'
$runBase = Join-Path $root 'run_codol_001'
$chain = Join-Path $runBase 'capture_elevated_network.ps1'

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outRoot = Join-Path $here ('_pop3_run_' + $stamp)
$outDir = Join-Path $outRoot 'live'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Output ("OUT=" + $outRoot)
Write-Output ("ADMIN=" + ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator))

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw 'python not found on PATH' }
$dumper = Join-Path $mainline '_pop3_live_dump.py'
if (-not (Test-Path -LiteralPath $dumper)) { throw ('dumper missing: ' + $dumper) }

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 1) start the read-only live dumper; it waits for the game itself
$dmpArgs = @('-X', 'utf8', '-u', $dumper, '--out', $outDir,
             '--seconds', "$Seconds", '--step', "$Step")
$dmpProc = Start-Process -FilePath $py -ArgumentList $dmpArgs `
    -WorkingDirectory $mainline -PassThru `
    -RedirectStandardOutput (Join-Path $outRoot 'dump_stdout.txt') `
    -RedirectStandardError (Join-Path $outRoot 'dump_stderr.txt') `
    -WindowStyle Hidden
Write-Output ("DUMP_PID=" + $dmpProc.Id)

# 2) start the frozen launch chain (owns the TCLS handoff)
$chainArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass',
               '-File', $chain, '-DurationSeconds', "$ChainSeconds")
$chainProc = Start-Process -FilePath 'powershell.exe' -ArgumentList $chainArgs `
    -WorkingDirectory $runBase -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $outRoot 'chain_stdout.txt') `
    -RedirectStandardError (Join-Path $outRoot 'chain_stderr.txt')
Write-Output ("CHAIN_PID=" + $chainProc.Id)

# 3) take screenshots of the in-game UI for the record (40s budget)
$shotDir = Join-Path $outRoot 'shots'
New-Item -ItemType Directory -Force -Path $shotDir | Out-Null
$shotter = Join-Path $mainline '_pop_desktop_shot.py'
$shotEnd = (Get-Date).AddSeconds(40)
$n = 0
while ((Get-Date) -lt $shotEnd) {
    Start-Sleep -Seconds 2
    $n++
    $p = Join-Path $shotDir ('shot_%02d.png' % $n)
    try {
        & $py -X utf8 $shotter $p 2>&1 | Out-Null
    } catch { }
}

# 4) let the dumper finish, then clean everything up
try { $dmpProc.WaitForExit(90000) | Out-Null } catch { }

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("KILL " + $_.Id); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
try { $chainProc.WaitForExit(5000) | Out-Null } catch { }

# taskkill the whole tree as required by the task discipline
& taskkill.exe /F /IM codoMP_client_shipRetail.exe /T 2>&1 | Out-Null

Write-Output ("DONE=" + $outRoot)
