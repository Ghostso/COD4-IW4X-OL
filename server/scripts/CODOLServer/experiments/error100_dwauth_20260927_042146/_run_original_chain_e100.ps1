[CmdletBinding()]
param(
    [int]$DurationSeconds = 150
)

# Runs the project's ORIGINAL fixed launch chain
# (run_codol_001\capture_elevated_network.ps1) against the ORIGINAL, known-good
# sandbox (run_codol_001\sandbox_ifs1_20260923), while a read-only sampler and a
# socket observer attach to the game process that the chain creates.
#
# dwauth.ini is replaced for the duration and restored afterwards. No EXE/DLL
# is modified.

$ErrorActionPreference = 'Stop'

# The elevated host may run under a non-Unicode code page, so any CJK path
# literal (including $PSScriptRoot) can round-trip as mojibake. Resolve the
# project root through the 8.3 short name, which is pure ASCII.
$shortRoot = (& cmd.exe /c 'for %I in ("D:\BaiduNetdiskDownload\使命召唤OL") do @echo %~sI').Trim()
if (-not $shortRoot) { throw 'could not resolve 8.3 short path for project root' }
$projectRoot = $shortRoot            # e.g. D:\BAIDUN~1\使命召~1
$sandbox = Join-Path $projectRoot 'run_codol_001\sandbox_ifs1_20260923'
$chain = Join-Path $projectRoot 'run_codol_001\capture_elevated_network.ps1'
$expRoot = Join-Path $projectRoot 'CODOLServer\experiments\error100_dwauth_20260927_042146'
$sampler = Join-Path $expRoot '_watch_e100.py'
$netSide = Join-Path $expRoot '_net_side_e100.py'
$tag = 'E100_ORIG_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$run = Join-Path $expRoot ('runs\' + $tag)
New-Item -ItemType Directory -Path $run -Force | Out-Null

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
@(
    'User=' + $identity.Name
    'Admin=' + $isAdmin
    'Sandbox=' + $sandbox
    'Chain=' + $chain
    'RunDir=' + $run
    'Start=' + (Get-Date).ToString('o')
) | Set-Content -LiteralPath (Join-Path $run 'identity.txt') -Encoding UTF8
if (-not $isAdmin) { throw 'must run elevated' }

$dwauth = Join-Path $sandbox 'dwauth.ini'
$backup = Join-Path $expRoot '_PRE\dwauth_sandboxifs1_ORIGINAL.ini'
if (-not (Test-Path -LiteralPath $backup)) {
    throw "original dwauth backup missing: $backup"
}
Copy-Item -LiteralPath $dwauth -Destination (Join-Path $run 'dwauth_active_before.ini') -Force
Get-FileHash -LiteralPath (Join-Path $sandbox 'codoMP_client_shipRetail.exe'),
    (Join-Path $sandbox 'codoMP_client_shipRetailBase.dll') -Algorithm SHA256 |
    Select-Object Path, Hash | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $run 'modules_before.json') -Encoding UTF8

# --- observation sidecars --------------------------------------------------
$samplerOut = Join-Path $run 'sampler'
New-Item -ItemType Directory -Path $samplerOut -Force | Out-Null
$samplerProc = Start-Process -FilePath 'python.exe' `
    -ArgumentList @('-X', 'utf8', '-u', $sampler, '--cwd', $sandbox,
                    '--out', $samplerOut, '--seconds', "$($DurationSeconds + 60)",
                    '--step', '0.25', '--attach-wait',
                    '--attach-timeout', '180') `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $samplerOut 'stdout.txt') `
    -RedirectStandardError (Join-Path $samplerOut 'stderr.txt')

$netOut = Join-Path $run 'netside'
New-Item -ItemType Directory -Path $netOut -Force | Out-Null
# The chain's own game PID is discovered by the sampler; the socket observer
# follows every codoMP_client_shipRetail.exe created during the window.
$netProc = Start-Process -FilePath 'python.exe' `
    -ArgumentList @('-X', 'utf8', '-u', $netSide, '--pid', '0',
                    '--out', $netOut, '--seconds', "$DurationSeconds",
                    '--follow-image', 'codoMP_client_shipRetail.exe') `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $netOut 'stdout.txt') `
    -RedirectStandardError (Join-Path $netOut 'stderr.txt')

Write-Output ('SAMPLER_PID=' + $samplerProc.Id)
Write-Output ('NETSIDE_PID=' + $netProc.Id)

try {
    & $chain -DurationSeconds $DurationSeconds 2>&1 |
        Tee-Object -FilePath (Join-Path $run 'chain_console.txt')
} finally {
    Copy-Item -LiteralPath $backup -Destination $dwauth -Force
    try { if (-not $samplerProc.HasExited) { $samplerProc.Kill() } } catch { }
    try { if (-not $netProc.HasExited) { $netProc.Kill() } } catch { }
    Get-FileHash -LiteralPath (Join-Path $sandbox 'codoMP_client_shipRetail.exe'),
        (Join-Path $sandbox 'codoMP_client_shipRetailBase.dll') -Algorithm SHA256 |
        Select-Object Path, Hash | ConvertTo-Json -Depth 3 |
        Set-Content -LiteralPath (Join-Path $run 'modules_after.json') -Encoding UTF8
    Get-Content -LiteralPath $dwauth -Raw |
        Set-Content -LiteralPath (Join-Path $run 'dwauth_after_restore.txt') -Encoding UTF8
}

Write-Output ('RUN=' + $run)
Write-Output 'COMPLETE'
