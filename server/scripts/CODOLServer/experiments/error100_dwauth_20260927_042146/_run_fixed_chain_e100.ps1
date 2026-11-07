[CmdletBinding()]
param(
    [int]$DurationSeconds = 150,
    [string]$Sandbox = $null,
    [string]$Tag = $null
)

# Error-100 first-blocker run, driven by the project's known-good "fixed launch
# chain" so the IIPS layer initialises instead of failing.
#
#   AboProbe.exe --mode B --sandbox <experiment dir>   (same launcher the prior
#   sessions used) + read-only global sampler + socket table observer.
#
# No EXE/DLL modification. The only new file in the experiment directory is
# dwauth.ini.

$ErrorActionPreference = 'Stop'

$expRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $expRoot))
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'COD OL'))) {
    $projectRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $expRoot)))
}

if (-not $Sandbox) { $Sandbox = $expRoot }
if (-not $Tag) { $Tag = 'E100_' + (Get-Date -Format 'yyyyMMdd_HHmmss') }

$run = Join-Path $expRoot ('runs\' + $Tag)
New-Item -ItemType Directory -Path $run -Force | Out-Null

$probe = Join-Path $projectRoot 'restore_iips_contract_001\observer2\out\AboProbe.exe'
$sampler = Join-Path $expRoot '_watch_e100.py'
$netSide = Join-Path $expRoot '_net_side_e100.py'

foreach ($required in @($probe, $sampler, $netSide)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "missing required component: $required"
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $Sandbox 'codoMP_client_shipRetail.exe'))) {
    throw "sandbox game executable missing: $Sandbox"
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
@(
    'User=' + $identity.Name
    'Admin=' + $isAdmin
    'Sandbox=' + $Sandbox
    'RunDir=' + $run
    'Duration=' + $DurationSeconds
    'Start=' + (Get-Date).ToString('o')
) | Set-Content -LiteralPath (Join-Path $run 'identity.txt') -Encoding UTF8
if (-not $isAdmin) { throw 'The fixed launch chain must run elevated.' }

# ---- pre-state ------------------------------------------------------------
$exePath = Join-Path $Sandbox 'codoMP_client_shipRetail.exe'
$basePath = Join-Path $Sandbox 'codoMP_client_shipRetailBase.dll'
Get-FileHash -LiteralPath $exePath, $basePath -Algorithm SHA256 |
    Select-Object Path, Hash |
    ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $run 'modules_before.json') -Encoding UTF8

Get-Content -LiteralPath (Join-Path $Sandbox 'dwauth.ini') -Raw -ErrorAction SilentlyContinue |
    Set-Content -LiteralPath (Join-Path $run 'dwauth_before.txt') -Encoding UTF8
Get-Content -LiteralPath (Join-Path $Sandbox 'iips.ini') -Raw -ErrorAction SilentlyContinue |
    Set-Content -LiteralPath (Join-Path $run 'iips_ini_before.txt') -Encoding UTF8

# ---- launch the fixed chain (AboProbe creates the game process) -----------
$probeOut = Join-Path $run 'aboprobe.stdout'
$probeErr = Join-Path $run 'aboprobe.stderr'
$argString = '--mode B --tag "' + $Tag + '" --duration ' + ($DurationSeconds + 30) +
             ' --sandbox "' + $Sandbox + '"'
$probeProc = Start-Process -FilePath $probe -ArgumentList $argString `
    -WorkingDirectory (Split-Path -Parent $probe) `
    -RedirectStandardOutput $probeOut -RedirectStandardError $probeErr `
    -WindowStyle Hidden -PassThru

# ---- wait for the game PID (the chain starts it) --------------------------
$gamePid = $null
$deadline = (Get-Date).AddSeconds(60)
while (-not $gamePid -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
    $match = Select-String -LiteralPath $probeOut -Pattern 'PROCESS_CREATED,pid=(\d+)' `
        -ErrorAction SilentlyContinue | Select-Object -Last 1
    if ($match -and $match.Matches.Count -gt 0) {
        $gamePid = [int]$match.Matches[0].Groups[1].Value
    }
}
@(
    'PROBE_PID=' + $probeProc.Id
    'GAME_PID=' + $gamePid
    'ARGS=' + $argString
) | Set-Content -LiteralPath (Join-Path $run 'launch.txt') -Encoding UTF8
if (-not $gamePid) { throw 'game process was not observed within 60s' }

Write-Output ('GAME_PID=' + $gamePid)

# ---- read-only state sampler (owns the suspended-handle sequencing) -------
$samplerOut = Join-Path $run 'sampler'
New-Item -ItemType Directory -Path $samplerOut -Force | Out-Null
$samplerProc = Start-Process -FilePath 'python.exe' `
    -ArgumentList @('-X', 'utf8', '-u', $sampler, '--cwd', $Sandbox,
                    '--out', $samplerOut, '--seconds', "$DurationSeconds",
                    '--step', '0.5') `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $samplerOut 'stdout.txt') `
    -RedirectStandardError (Join-Path $samplerOut 'stderr.txt')

# ---- socket table observer (NET_STAT only, no injection) ------------------
$netProc = Start-Process -FilePath 'python.exe' `
    -ArgumentList @('-X', 'utf8', '-u', $netSide, '--pid', "$gamePid",
                    '--out', $run, '--seconds', "$DurationSeconds") `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $run 'netside.stdout') `
    -RedirectStandardError (Join-Path $run 'netside.stderr')

Write-Output ('SAMPLER_PID=' + $samplerProc.Id)
Write-Output ('NETSIDE_PID=' + $netProc.Id)

$probeProc.WaitForExit()
try { $samplerProc.WaitForExit(20000) } catch { }
try { $netProc.WaitForExit(20000) } catch { }

# ---- post-state -----------------------------------------------------------
Get-FileHash -LiteralPath $exePath, $basePath -Algorithm SHA256 |
    Select-Object Path, Hash |
    ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $run 'modules_after.json') -Encoding UTF8

foreach ($p in @($samplerProc, $netProc)) {
    try { if (-not $p.HasExited) { $p.Kill() } } catch { }
}

# Only clean processes that live in this experiment sandbox.
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        $_.ExecutablePath.StartsWith($Sandbox, [StringComparison]::OrdinalIgnoreCase)
    } |
    ForEach-Object {
        try { Stop-Process -Id ([int]$_.ProcessId) -Force -ErrorAction SilentlyContinue } catch { }
    }

Write-Output ('RUN=' + $run)
Write-Output 'COMPLETE'
