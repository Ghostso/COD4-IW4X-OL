[CmdletBinding()]
param(
    [int]$DurationSeconds = 75
)

$ErrorActionPreference = 'Stop'
$runRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $runRoot
$tag = 'NET_CAPTURE_ELEVATED_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$captureRoot = Join-Path $runRoot ('runs\' + $tag)
$afdEtl = Join-Path $captureRoot 'afd.etl'
$afdXml = Join-Path $captureRoot 'afd.xml'
$rtJsonl = Join-Path $captureRoot 'game_etw.jsonl'
$rtAllJsonl = Join-Path $captureRoot 'all_etw.jsonl'
$rtReport = Join-Path $captureRoot 'game_rt_report.md'
$pktEtl = Join-Path $captureRoot 'pktmon.etl'
$pktText = Join-Path $captureRoot 'pktmon.txt'
$observerLog = Join-Path $captureRoot 'observer_wrapper.log'
$errorLog = Join-Path $captureRoot 'capture_error.txt'
$session = 'codol_capture_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$observer = Join-Path $runRoot 'elevated_ifs1_observer.ps1'

New-Item -ItemType Directory -Path $captureRoot -Force | Out-Null

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'capture_elevated_network.ps1 must run elevated.'
}

function Invoke-Native([string]$FilePath, [string[]]$Arguments, [string]$OutputPath = $null) {
    $outPath = $OutputPath
    $errPath = $null
    $temporary = @()
    if (-not $outPath) {
        $outPath = Join-Path $captureRoot ('native_' + [IO.Path]::GetRandomFileName() + '.out')
        $errPath = Join-Path $captureRoot ('native_' + [IO.Path]::GetRandomFileName() + '.err')
        $temporary += $outPath
        $temporary += $errPath
    } else {
        $errPath = Join-Path $captureRoot ('native_' + [IO.Path]::GetRandomFileName() + '.err')
        $temporary += $errPath
    }
    try {
        $child = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WindowStyle Hidden `
            -RedirectStandardOutput $outPath -RedirectStandardError $errPath -PassThru -Wait
        return [int]$child.ExitCode
    } finally {
        foreach ($path in $temporary) {
            if (Test-Path -LiteralPath $path) {
                Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Stop-Afd {
    try { Invoke-Native 'logman.exe' @('stop', $session, '-ets') | Out-Null } catch { }
    try { Invoke-Native 'logman.exe' @('delete', $session) | Out-Null } catch { }
}

function Stop-Pktmon {
    try { & pktmon stop 2>$null | Out-Null } catch { }
    try { & pktmon filter remove 2>$null | Out-Null } catch { }
}

$pktmonStarted = $false
try {
    try { Invoke-Native 'logman.exe' @('stop', $session, '-ets') | Out-Null } catch { }
    try { Invoke-Native 'logman.exe' @('delete', $session) | Out-Null } catch { }
    $afdStart = Invoke-Native 'logman.exe' @('start', $session, '-p', '{E53C6823-7BB8-44BB-90DC-3F86090D48A6}', '-o', $afdEtl, '-ets')
    if ($afdStart -ne 0 -or -not (Test-Path -LiteralPath $afdEtl)) {
        throw "AFD ETW start failed with exit code $afdStart"
    }

    # PktMon is optional. A missing driver must never prevent the core
    # ETW+observer reproduction from running.
    $pktmonStartLog = Join-Path $captureRoot 'pktmon_start.log'
    'PktMon capture disabled for this run; AFD ETW remains authoritative.' |
        Set-Content -LiteralPath $pktmonStartLog -Encoding UTF8

    @(
        'TAG=' + $tag
        'START=' + (Get-Date).ToString('o')
        'SESSION=' + $session
        'AFD_ETL=' + $afdEtl
        'PKTMON_ETL=' + $pktEtl
        'PKTMON_STARTED=' + $pktmonStarted
        'DURATION=' + $DurationSeconds
    ) | Set-Content -LiteralPath (Join-Path $captureRoot 'capture_start.txt') -Encoding UTF8

    & $observer -DurationSeconds $DurationSeconds *>&1 |
        Tee-Object -FilePath $observerLog

    @(
        'OBSERVER_EXIT=' + $LASTEXITCODE
        'OBSERVER_END=' + (Get-Date).ToString('o')
    ) | Add-Content -LiteralPath (Join-Path $captureRoot 'capture_start.txt') -Encoding UTF8
} catch {
    $_ | Out-File -LiteralPath $errorLog -Encoding UTF8
    throw
} finally {
    Stop-Afd
    if ($pktmonStarted) {
        Stop-Pktmon
        if (Test-Path -LiteralPath $pktEtl) {
            & pktmon etl2txt $pktEtl --out $pktText --hex --verbose 1 2> (Join-Path $captureRoot 'pktmon_decode.log') | Out-Null
        }
    }
}

if (-not (Test-Path -LiteralPath $observerLog)) {
    throw "Observer did not run; see $pktmonStartLog and $errorLog"
}

$gamePid = $null
$innerRun = $null
$runLine = Select-String -LiteralPath $observerLog -Pattern '^RUN=(.+)$' | Select-Object -Last 1
if ($runLine -and $runLine.Matches.Count -gt 0) {
    $innerRun = $runLine.Matches[0].Groups[1].Value.Trim()
}
$probeStdout = if ($innerRun) { Join-Path $innerRun 'aboprobe.stdout' } else { $null }
$processLine = $null
if ($probeStdout -and (Test-Path -LiteralPath $probeStdout)) {
    # Read the completed probe output as a whole. Select-String's MatchInfo
    # shape is not stable enough here for the nested .Matches check below.
    $probeText = [IO.File]::ReadAllText($probeStdout)
    $processMatches = [regex]::Matches($probeText, 'PROCESS_CREATED,pid=(\d+)')
    if ($processMatches.Count -gt 0) {
        $gamePid = [int]$processMatches[$processMatches.Count - 1].Groups[1].Value
    }
}
if (-not $gamePid) {
    $processLine = Select-String -LiteralPath $observerLog -Pattern 'PROCESS_CREATED,pid=(\d+)' | Select-Object -Last 1
    if ($processLine -and $processLine.Matches.Count -gt 0) {
        $gamePid = [int]$processLine.Matches[0].Groups[1].Value
    }
}
@(
    'GAME_PID=' + ($gamePid | ForEach-Object { $_ })
    'INNER_RUN=' + $innerRun
    'END=' + (Get-Date).ToString('o')
) | Add-Content -LiteralPath (Join-Path $captureRoot 'capture_end.txt') -Encoding UTF8

$etwConsole = Join-Path $captureRoot 'rt_etw_console.txt'
$reparseArgs = @('--reparse', '--etl', $afdEtl, '--out', $rtAllJsonl, '--xml', $afdXml, '--keep-xml')
if ($gamePid) {
    $reparseArgs += @('--pid', [string]$gamePid)
    $reparseArgs += @('--out', $rtJsonl)
}
& python (Join-Path $projectRoot 'COD OL\scripts\rt_etw.py') @reparseArgs *> $etwConsole
if ($gamePid -and (Test-Path -LiteralPath $rtJsonl)) {
    & python (Join-Path $projectRoot 'COD OL\scripts\rt_summary.py') $rtJsonl --out $rtReport --names '122.96.96.225=tqos.gamesafe.qq.com' *> (Join-Path $captureRoot 'rt_summary_console.txt')
}

Get-ChildItem -LiteralPath $captureRoot -File | Select-Object Name,Length,LastWriteTime | Sort-Object Name | Format-Table -AutoSize
