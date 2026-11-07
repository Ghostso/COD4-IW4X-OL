[CmdletBinding()]
param(
    [int]$DurationSeconds = 120,
    [string]$Sandbox = '',
    [string]$TenProxyShm = '',
    [string]$PokeLobbyHost = '',
    [int]$PokeLobbyPort = 0,
    [int]$PatchLobbyResult = -1,
    [int]$PokeLobbyGlobals = 0
)

$ErrorActionPreference = 'Stop'

$runRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $runRoot
$restoreRoot = Join-Path $projectRoot 'restore_iips_contract_001'
if ($Sandbox) {
    $sandbox = (Resolve-Path -LiteralPath $Sandbox -ErrorAction Stop).Path
} else {
    $sandbox = Join-Path $runRoot 'sandbox_ifs1_20260923'
}
$probe = Join-Path $restoreRoot 'observer2\out\AboProbe.exe'
# Publishing TCLS_SHAREDMEMEMORY<pid> is what flips the client's
# cfg_applied flag (0x331C5C0) to 1 and makes it take the non-degraded
# lobby path that creates objC.  Without it the lobby stage fails right
# after DW_ACCOUNT_LOGIN_COMPLETE.  Default to the prepared image so the
# standard chain is self-sufficient; pass '' to disable.
if (-not $TenProxyShm) {
    $TenProxyShm = Join-Path $projectRoot 'CODOLServer\_subagents\_tenproxy_shm_fixed.bin'
}
$restoreRuns = Join-Path $restoreRoot 'runs'
$installRoot = Join-Path $projectRoot 'COD OL'
$iips = Join-Path $sandbox 'IIPS'
$tag = 'IFS1_ELEVATED_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$run = Join-Path $runRoot ('runs\' + $tag)
$startUtc = (Get-Date).ToUniversalTime()
$samplePath = Join-Path $run 'observer.jsonl'
$processPath = Join-Path $run 'processes_final.json'
$hostPidPath = Join-Path $iips 'HostPid'
$targetNames = @(
    'AboProbe.exe', 'codoMP_client_shipRetail.exe', 'IIPSHostApp.exe',
    'TP3Helper.exe', 'iipsinit.exe', 'tgp_daemon.exe', 'tcls_core.exe',
    'TCLSHost.exe', 'Client.exe'
)

New-Item -ItemType Directory -Path $run -Force | Out-Null

function Write-Text([string]$Path, [object]$Value) {
    $Value | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-ProcessRows {
    $rows = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -in $targetNames -or
            ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($sandbox, [StringComparison]::OrdinalIgnoreCase))
        } |
        Select-Object ProcessId, ParentProcessId, Name, CreationDate, ExecutablePath, CommandLine)
    return $rows
}

function Get-HostPidValue {
    if (-not (Test-Path -LiteralPath $hostPidPath)) { return '' }
    try {
        $raw = [IO.File]::ReadAllText($hostPidPath)
        if ($null -eq $raw) { return '' }
        return $raw.Trim()
    } catch {
        return 'READ_ERROR:' + $_.Exception.Message
    }
}

function Get-IipsFileRows {
    $rows = @()
    if (-not (Test-Path -LiteralPath $iips)) { return $rows }
    foreach ($file in @(Get-ChildItem -LiteralPath $iips -Recurse -File -Force -ErrorAction SilentlyContinue)) {
        if ($file.Name -match 'HostPid|BugTrace|Tenio|IIPS|IFS|\.log$|\.txt$') {
            $rows += [PSCustomObject]@{
                FullName = $file.FullName
                Length = $file.Length
                LastWriteTimeUtc = $file.LastWriteTimeUtc.ToString('o')
            }
        }
    }
    return $rows
}

function Get-WindowRows {
    $rows = @()
    foreach ($p in @(Get-Process -ErrorAction SilentlyContinue)) {
        try {
            if ($p.MainWindowHandle -ne 0 -and $p.MainWindowTitle) {
                $rows += [PSCustomObject]@{
                    Id = $p.Id
                    ProcessName = $p.ProcessName
                    MainWindowHandle = ('0x{0:X}' -f $p.MainWindowHandle.ToInt64())
                    MainWindowTitle = $p.MainWindowTitle
                }
            }
        } catch { }
    }
    return $rows
}

function Write-JsonLine([object]$Value) {
    ($Value | ConvertTo-Json -Compress -Depth 8) | Add-Content -LiteralPath $samplePath -Encoding UTF8
}

if (-not (Test-Path -LiteralPath $sandbox)) { throw "Sandbox missing: $sandbox" }
if (-not (Test-Path -LiteralPath $probe)) { throw "Probe missing: $probe" }
if (-not (Test-Path -LiteralPath (Join-Path $sandbox 'codoMP_client_shipRetail.exe'))) { throw 'Sandbox game executable missing' }

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$identityText = @(
    'User=' + $identity.Name
    'Admin=' + $isAdmin
    'IntegrityGroups=' + (($identity.Groups | ForEach-Object { $_.Value }) -join ';')
    'StartLocal=' + (Get-Date).ToString('o')
    'StartUtc=' + $startUtc.ToString('o')
    'Sandbox=' + $sandbox
    'Probe=' + $probe
    'Tag=' + $tag
)
Write-Text (Join-Path $run 'identity.txt') $identityText
whoami /priv | Set-Content -LiteralPath (Join-Path $run 'token_privileges.txt') -Encoding UTF8
whoami /groups | Set-Content -LiteralPath (Join-Path $run 'token_groups.txt') -Encoding UTF8
if (-not $isAdmin) { throw 'The elevated observer was not started with an administrator token.' }

$originalFiles = @(
    (Join-Path $installRoot 'iips.ini'),
    (Join-Path $installRoot 'IIPS\iips.dll'),
    (Join-Path $installRoot 'IIPS\IFS2.dll'),
    (Join-Path $installRoot 'codoMP_client_shipRetail.exe')
)
Get-FileHash -LiteralPath $originalFiles -Algorithm SHA256 |
    Select-Object Path, Hash | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $run 'original_hashes_before.json') -Encoding UTF8

$baseline = @(Get-ProcessRows)
$baseline | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'processes_before.json') -Encoding UTF8

$eventStart = (Get-Date).AddSeconds(-2)
$outFile = Join-Path $run 'aboprobe.stdout'
$errFile = Join-Path $run 'aboprobe.stderr'
$argString = '--mode B --tag "' + $tag + '" --duration ' + $DurationSeconds + ' --sandbox "' + $sandbox + '"'
if ($TenProxyShm -and (Test-Path -LiteralPath $TenProxyShm)) {
    $argString += ' --tenproxy-shm "' + $TenProxyShm + '"'
}
if ($PokeLobbyHost) {
    $argString += ' --poke-lobby-host "' + $PokeLobbyHost + '"'
}
if ($PokeLobbyPort -gt 0) {
    $argString += ' --poke-lobby-port ' + $PokeLobbyPort
}
if ($PatchLobbyResult -ge 0) {
    $argString += ' --patch-lobby-result ' + $PatchLobbyResult
}
if ($PokeLobbyGlobals -eq 1) {
    $argString += ' --poke-lobby-globals 1'
}
$probeProcess = Start-Process -FilePath $probe -ArgumentList $argString -WorkingDirectory (Split-Path -Parent $probe) -RedirectStandardOutput $outFile -RedirectStandardError $errFile -PassThru
$probePid = $probeProcess.Id
Write-Text (Join-Path $run 'launch.txt') @(
    'START=' + (Get-Date).ToString('o')
    'START_UTC=' + $startUtc.ToString('o')
    'PROBE_PID=' + $probePid
    'TAG=' + $tag
    'SANDBOX=' + $sandbox
    'ARGS=' + $argString
)

$deadline = (Get-Date).AddSeconds([Math]::Max(30, $DurationSeconds + 45))
$lastFileScan = [DateTime]::MinValue
while (-not $probeProcess.HasExited -and (Get-Date) -lt $deadline) {
    $now = Get-Date
    $fileRows = @()
    if (($now - $lastFileScan).TotalSeconds -ge 1) {
        $fileRows = @(Get-IipsFileRows)
        $lastFileScan = $now
    }
    $record = [ordered]@{
        t = ((Get-Date) - $startUtc.ToLocalTime()).TotalSeconds
        time = $now.ToString('o')
        probe_pid = $probePid
        host_pid = Get-HostPidValue
        processes = @(Get-ProcessRows)
        windows = @(Get-WindowRows)
        iips_files = $fileRows
    }
    Write-JsonLine $record
    Start-Sleep -Milliseconds 500
}

$forced = $false
if (-not $probeProcess.HasExited) {
    $forced = $true
    try { $probeProcess.Kill() } catch { }
}
try { $probeProcess.WaitForExit(10000) } catch { }
$probeExit = ''
try { $probeExit = $probeProcess.ExitCode } catch { $probeExit = 'UNKNOWN' }

Start-Sleep -Seconds 2
$finalRows = @(Get-ProcessRows)
$finalRows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $processPath -Encoding UTF8
$finalHostPid = Get-HostPidValue
$finalRecord = [ordered]@{
    t = ((Get-Date) - $startUtc.ToLocalTime()).TotalSeconds
    time = (Get-Date).ToString('o')
    final = $true
    forced = $forced
    probe_pid = $probePid
    probe_exit_code = $probeExit
    host_pid = $finalHostPid
    processes = $finalRows
    windows = @(Get-WindowRows)
    iips_files = @(Get-IipsFileRows)
}
Write-JsonLine $finalRecord

$aboDir = Join-Path $restoreRuns $tag
if (Test-Path -LiteralPath $aboDir) {
    Copy-Item -LiteralPath $aboDir -Destination (Join-Path $run 'aboprobe_run') -Recurse -Force
}

$logsDir = Join-Path $run 'iips_files'
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
foreach ($file in @(Get-ChildItem -LiteralPath $iips -Recurse -File -Force -ErrorAction SilentlyContinue)) {
    if ($file.Name -notmatch 'HostPid|BugTrace|Tenio|IIPS|IFS|\.log$|\.txt$') { continue }
    try {
        $relative = $file.FullName.Substring($iips.Length).TrimStart('\')
        $destination = Join-Path $logsDir $relative
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
        if ($file.Length -le 8MB) {
            Copy-Item -LiteralPath $file.FullName -Destination $destination -Force -ErrorAction SilentlyContinue
        }
    } catch { }
}

try {
    Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = $eventStart } -ErrorAction Stop |
        Where-Object { $_.Message -match 'codoMP|IIPSHostApp|AboProbe|iips\.dll|IFS\.dll|iipsinit|COD' } |
        Select-Object TimeCreated, ProviderName, Id, LevelDisplayName, Message |
        ConvertTo-Json -Depth 6 |
        Set-Content -LiteralPath (Join-Path $run 'application_events.json') -Encoding UTF8
} catch {
    Write-Text (Join-Path $run 'application_events_error.txt') $_.Exception.ToString()
}

# Only clean processes whose executable path is inside this sandbox. Never use
# a name-only kill, because the original installation may be running separately.
$cleanupRows = @(Get-ProcessRows | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($sandbox, [StringComparison]::OrdinalIgnoreCase) -and
    $_.Name -in @('codoMP_client_shipRetail.exe', 'IIPSHostApp.exe', 'TP3Helper.exe', 'iipsinit.exe')
})
foreach ($row in $cleanupRows) {
    try { Stop-Process -Id ([int]$row.ProcessId) -Force -ErrorAction SilentlyContinue } catch { }
}
if ($cleanupRows.Count -gt 0) {
    $cleanupRows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'cleanup_killed.json') -Encoding UTF8
}

Get-FileHash -LiteralPath $originalFiles -Algorithm SHA256 |
    Select-Object Path, Hash | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $run 'original_hashes_after.json') -Encoding UTF8

Add-Content -LiteralPath (Join-Path $run 'launch.txt') -Value @(
    'END=' + (Get-Date).ToString('o')
    'PROBE_EXIT=' + $probeExit
    'FORCED=' + $forced
    'FINAL_HOSTPID=' + $finalHostPid
    'CLEANUP_COUNT=' + $cleanupRows.Count
) -Encoding UTF8

$summary = @(
    'RUN=' + $run
    'TAG=' + $tag
    'ADMIN=' + $isAdmin
    'DURATION_SECONDS=' + $DurationSeconds
    'PROBE_PID=' + $probePid
    'PROBE_EXIT=' + $probeExit
    'FORCED=' + $forced
    'FINAL_HOSTPID=' + $finalHostPid
    'CLEANUP_COUNT=' + $cleanupRows.Count
    'ORIGINAL_HASHES_BEFORE=' + (Join-Path $run 'original_hashes_before.json')
    'ORIGINAL_HASHES_AFTER=' + (Join-Path $run 'original_hashes_after.json')
)
Write-Text (Join-Path $run 'summary.txt') $summary
Write-Output ($summary -join [Environment]::NewLine)
