param(
    [string]$ApplicationId = $(if ($env:CODOL_DISCORD_APP_ID) { $env:CODOL_DISCORD_APP_ID } else { '1554730441825718272' }),
    # No drive letters in any default.  Every path is derived from the stack that
    # called us -- the launchers export CODOL_STACK / CODOL_INSTALL -- so the
    # folder keeps working after it is copied to another drive.  This file used
    # to default to E:\codol-classic and a stale %TEMP% scratch tree.
    [string]$Stack = $(if ($env:CODOL_STACK) { $env:CODOL_STACK } else { Join-Path $env:TEMP 'codol-11113-presence' }),
    [string]$StateDirectory = $(if ($env:CODOL_STATE_DIR) { $env:CODOL_STATE_DIR }
                               elseif ($env:CODOL_STACK) { Join-Path $env:CODOL_STACK 'lobby' }
                               else { Join-Path $Stack 'lobby' }),
    [string]$Install = $(if ($env:CODOL_INSTALL) { $env:CODOL_INSTALL }
                         elseif ($env:CODOL_STACK) { Join-Path (Split-Path -Parent $env:CODOL_STACK) 'CODOL_Client' }
                         else { Join-Path (Split-Path -Parent $Stack) 'CODOL_Client' })
)

$ErrorActionPreference = 'Stop'
if ($ApplicationId -notmatch '^\d+$') {
    throw 'Set CODOL_DISCORD_APP_ID to the CoDOL Discord application ID.'
}

$scriptPath = Join-Path $PSScriptRoot 'codol_discord_presence.py'
$logPath = Join-Path $Install 'main\console_mp.log'
$rconPath = Join-Path $StateDirectory 'native_server_rcon.txt'
$logDirectory = Join-Path (Split-Path -Parent $StateDirectory) 'local-stack-logs'
foreach ($path in @($scriptPath, $rconPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing presence input: $path"
    }
}
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

$alreadyRunning = @(Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' OR Name = 'python.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains('codol_discord_presence.py') })
if ($alreadyRunning.Count -gt 0) {
    Write-Output "Discord presence already running (PID $($alreadyRunning[0].ProcessId))."
    return
}

# --- interpreter ------------------------------------------------------------
# Do NOT trust `Get-Command python.exe` on its own.  When the parent block
# carries BOTH 'Path' and 'PATH' (see the long note at the launch site), Win32
# resolves a case-insensitive lookup to whichever entry it meets first -- and
# the winner can be a stale value with no python on it.  The stack already pins
# an interpreter for the lobby, so try the same places first.
$python = $null
$candidates = New-Object System.Collections.Generic.List[string]
if ($env:CODOL_PYTHON) { $candidates.Add($env:CODOL_PYTHON) }
if ($env:USERPROFILE) {
    $candidates.Add((Join-Path $env:USERPROFILE '.workbuddy\binaries\python\envs\codol\Scripts\python.exe'))
    $managed = Join-Path $env:USERPROFILE '.workbuddy\binaries\python\versions'
    if (Test-Path -LiteralPath $managed) {
        Get-ChildItem -LiteralPath $managed -Directory -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending |
            ForEach-Object { $candidates.Add((Join-Path $_.FullName 'python.exe')) }
    }
}
foreach ($candidate in $candidates) {
    if ((Test-Path -LiteralPath $candidate -PathType Leaf)) { $python = $candidate; break }
}
if (-not $python) {
    $found = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($found) { $python = $found.Source }
}
if (-not $python) {
    Write-Output ("Discord presence skipped: no python.exe found (set CODOL_PYTHON to pin one)." +
                  "  -- the game server continues without it.")
    return
}

$stdoutLog = Join-Path $logDirectory 'discord-presence.stdout.log'
$stderrLog = Join-Path $logDirectory 'discord-presence.stderr.log'
$arguments = @(
    ('"' + $scriptPath + '"'), '--app-id', $ApplicationId,
    '--log', ('"' + $logPath + '"'),
    '--rcon-file', ('"' + $rconPath + '"')
)

# --- launch -----------------------------------------------------------------
# WHY THIS IS NOT Start-Process.
#
# Start-Process rebuilds the child environment by iterating
#     [Environment]::GetEnvironmentVariables()
# and calling EnvironmentVariables.Add(key, value) for each entry.  That
# collection is a case-SENSITIVE Hashtable, but the destination is a
# case-INSENSITIVE StringDictionary -- so the moment the parent block carries
# two spellings of the same variable, Add() throws
#     "Item has already been added. Key in dictionary: 'Path'
#      Key being added: 'PATH'"
# (a zh-CN host renders that as the localized "already added ... key in
#  dictionary ... key being added" wording; the exact text is recorded in
#  STACK-LAYOUT.md rather than here, so this script stays pure ASCII -- a
#  BOM-less script is read as ANSI, and a stray multi-byte byte can then
#  swallow the character that follows it).
# This machine really does produce such blocks, and the duplicate is inherited
# from whatever started the stack, so it cannot be cleaned up here: cmd's
# `set "PATH=..."` merges into the existing entry instead of removing the twin
# (verified).  Note that -UseNewEnvironment does NOT dodge the bug -- it was
# tried and throws identically.  What actually triggers the env copy is the
# redirection: -RedirectStandardOutput/-Error forces UseShellExecute=$false,
# which is what sends Start-Process down the copy path.
#
# So: use ProcessStartInfo directly and deliberately leave
# $psi.EnvironmentVariables untouched.  Untouched means .NET passes a null
# environment block to CreateProcess, and the child inherits ours verbatim --
# no copy, no dictionary, no throw, and no loss of the environment either.
# File redirection is handed to cmd.exe, which is happy to carry the duplicate.
$inner = '"{0}" {1} > "{2}" 2> "{3}"' -f $python, ($arguments -join ' '), $stdoutLog, $stderrLog
$shell = 'cmd.exe'
if ($env:SystemRoot) { $shell = Join-Path $env:SystemRoot 'System32\cmd.exe' }
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName        = $shell
$psi.Arguments       = '/d /s /c "' + $inner + '"'
$psi.UseShellExecute = $false
$psi.CreateNoWindow  = $true
$psi.WindowStyle     = 'Hidden'
$process = $null
try {
    $process = [System.Diagnostics.Process]::Start($psi)
} catch {
    Write-Output ("Discord presence could not be started: " + $_.Exception.Message +
                  "  -- the game server continues without it.")
    return
}

# The wrapper is `cmd /c`, so it stays alive exactly as long as the interpreter
# does -- which makes it a usable liveness probe.  Without this check a helper
# that dies on its first line (missing module, encoding error, ...) looks
# identical to one that started fine, and you only notice weeks later that the
# Discord presence never worked.
Start-Sleep -Milliseconds 1500
if ($process.HasExited) {
    $detail = ''
    foreach ($log in @($stderrLog, $stdoutLog)) {
        if (-not (Test-Path -LiteralPath $log)) { continue }
        $tail = (Get-Content -LiteralPath $log -Tail 3 -ErrorAction SilentlyContinue) -join ' | '
        if ($tail) { $detail = "  last output: " + $tail.Trim(); break }
    }
    Write-Output ("Discord presence exited immediately (exit code $($process.ExitCode))." + $detail +
                  "  -- the game server continues without it.")
    return
}

# Report the interpreter's pid, not the wrapper's: the direct child of cmd is
# python.exe itself (for a venv, python.exe is the stub that runs the real one).
$reportedPid = $process.Id
try {
    $child = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($process.Id)" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like 'python*' } | Select-Object -First 1
    if ($child) { $reportedPid = $child.ProcessId }
} catch { }
Write-Output "Discord presence started in the background (PID $reportedPid)."
