$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$reader = Join-Path $root 'tools\codol_map_handoff.ps1'
$launcher = Join-Path $root 'bin\START-CODOL-SERVER.cmd'
$fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('codol-handoff-' + [guid]::NewGuid().ToString('N'))
$stateDir = Join-Path $fixtureRoot 'lobby-state'
$referenceDir = Join-Path $fixtureRoot 'reference'
$fixture = Join-Path $stateDir 'startgame.txt'

function Assert-Read([string] $content, [string] $expected, [int] $expectedExit = 0) {
    [System.IO.File]::WriteAllText($fixture, $content)
    $output = & powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $reader -Path $fixture
    if ($LASTEXITCODE -ne $expectedExit) {
        throw "exit $LASTEXITCODE, expected $expectedExit for: $content"
    }
    if (($output -join '') -ne $expected) {
        throw "output '$output', expected '$expected'"
    }
}

try {
    New-Item -ItemType Directory -Path $stateDir, $referenceDir | Out-Null
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $fresh = "$now 1813179697 1177862437"

    # The launcher must take the stamp and RCON credential from the same lobby
    # state directory as the session key, even when the reference is elsewhere.
    $batch = [System.IO.File]::ReadAllText($launcher)
    if ($batch -notmatch '(?m)^set "CODOL_HANDOFF=%CODOL_STATE_DIR%\\startgame\.txt"\r?$' -or
        $batch -notmatch '(?m)^set "CODOL_RCON_FILE=%CODOL_STATE_DIR%\\native_server_rcon\.txt"\r?$' -or
        $batch -notmatch '(?m)^  \+set codol_securityKeyPath "%CODOL_STATE_DIR%\\securitykey\.bin" \^\r?$' -or
        $batch -notmatch '(?m)^  \+set codol_admissionPath "%CODOL_STATE_DIR%\\game_admissions\.txt" \^\r?$' -or
        $batch -notmatch '(?m)^  \+set codol_admissionRequired %CODOL_ADMISSION_REQUIRED% \^\r?$' -or
        $batch -notmatch '(?m)^if not defined CODOL_ADMISSION_REQUIRED set "CODOL_ADMISSION_REQUIRED=1"\r?$' -or
        $batch -notmatch '(?m)^set "CODOL_PROFILE_DIR=%CODOL_REFERENCE%\\resources"\r?$' -or
        $batch -notmatch '(?m)^  \+set codol_profilePath "%CODOL_PROFILE_DIR%" \^\r?$') {
        throw 'launcher must use lobby state for handoff, RCON, key and required admission, and a configurable profile directory'
    }

    [System.IO.File]::WriteAllText(
        (Join-Path $referenceDir 'startgame.txt'),
        "$fresh map=mp_rust type=mp gametype=dm session_map=mp_rust resolved=1")
    Assert-Read "$fresh map=mp_cargoship_sh type=mp gametype=war session_map=mp_cargoship_sh resolved=1" 'mp_cargoship_sh|war|mp|mp_cargoship_sh'
    Assert-Read "$fresh map=mp_killhouse_sh type=mp gametype=war resolved=1" 'mp_killhouse_sh|war|mp|mp_killhouse_sh'
    Assert-Read "$fresh map=mp_killhouse_sh type=bad gametype=war resolved=1" '' 1
    Assert-Read "$fresh map=mp_killhouse_sh&amp;calc type=mp gametype=war resolved=1" '' 1
    Assert-Read "$fresh map=mp_rust type=mp gametype=dm session_map=mp_rust`n0 1 2 map=mp_cargoship_sh type=mp gametype=war session_map=mp_cargoship_sh" '' 1
    Assert-Read "$fresh map=mp_rust type=mp gametype=dm session_map=mp_rust`r`n" 'mp_rust|dm|mp|mp_rust'
    Assert-Read 'not-a-stamp 1 2 map=mp_killhouse_sh type=mp gametype=war resolved=1' '' 1
    Assert-Read "$($now - 601) 1 2 map=mp_killhouse_sh type=mp gametype=war resolved=1" '' 1
    Assert-Read "$($now + 120) 1 2 map=mp_killhouse_sh type=mp gametype=war resolved=1" '' 1

    # Exercise the real launcher with conflicting inherited settings. A lobby
    # handoff must select its map, playlist, zone and session as one decision.
    $isolatedRoot = Join-Path $fixtureRoot 'isolated launcher'
    $isolatedBin = Join-Path $isolatedRoot 'bin'
    $isolatedTools = Join-Path $isolatedRoot 'tools'
    $isolatedInstall = Join-Path $fixtureRoot 'game install'
    $isolatedScripts = Join-Path $fixtureRoot 'scripts'
    [System.IO.Directory]::CreateDirectory($isolatedBin) | Out-Null
    [System.IO.Directory]::CreateDirectory($isolatedTools) | Out-Null
    [System.IO.Directory]::CreateDirectory($isolatedInstall) | Out-Null
    [System.IO.Directory]::CreateDirectory((Join-Path $isolatedScripts 'maps\mp\gametypes')) | Out-Null
    Copy-Item -LiteralPath $launcher -Destination (Join-Path $isolatedBin 'START-CODOL-SERVER.cmd')
    Copy-Item -LiteralPath $reader -Destination (Join-Path $isolatedTools 'codol_map_handoff.ps1')
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_rcon_password.ps1') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_stage_server_pack.py') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_package.py') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_export_c1_keys.py') -Destination $isolatedTools
    [System.IO.File]::WriteAllBytes((Join-Path $isolatedInstall 'C1.exe'), [byte[]]@())
    # A real, quick-exiting Windows program avoids an invalid-EXE popup while
    # still exercising every launcher decision before the server command.
    Copy-Item -LiteralPath (Join-Path $env:SystemRoot 'System32\whoami.exe') -Destination (Join-Path $isolatedBin 'codol_dedrun_next.exe')
    [System.IO.File]::WriteAllText((Join-Path $isolatedScripts 'maps\mp\gametypes\_callbacksetup.gsc'), '')
    [System.IO.File]::WriteAllText($fixture,
        "$fresh map=mp_cargoship_sh type=mp gametype=war session_map=mp_cargoship_sh resolved=1")

    $names = @('CODOL_INSTALL', 'CODOL_REFERENCE', 'CODOL_PROFILE_DIR', 'CODOL_PACK_SOURCE', 'CODOL_HOME', 'CODOL_STATE_DIR',
               'CODOL_SCRIPTS', 'CODOL_MAP', 'CODOL_GAMETYPE', 'CODOL_ZONE_TYPE',
               'CODOL_SESSION_MAP')
    $saved = @{}
    foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name) }
    try {
        $env:CODOL_INSTALL = $isolatedInstall
        $env:CODOL_REFERENCE = $referenceDir
        [Environment]::SetEnvironmentVariable('CODOL_PROFILE_DIR', $null)
        $env:CODOL_HOME = Join-Path $fixtureRoot 'server home'
        $env:CODOL_STATE_DIR = $stateDir
        $env:CODOL_SCRIPTS = $isolatedScripts
        $env:CODOL_PACK_SOURCE = $root
        [Environment]::SetEnvironmentVariable('CODOL_MAP', $null)
        $env:CODOL_GAMETYPE = 'dm'
        $env:CODOL_ZONE_TYPE = 'zm'
        $env:CODOL_SESSION_MAP = 'old_session'
        $priorErrorAction = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $output = & (Join-Path $isolatedBin 'START-CODOL-SERVER.cmd') 2>&1
        } finally {
            $ErrorActionPreference = $priorErrorAction
        }
        $outputText = $output -join "`n"
        if ($outputText -notmatch 'sh1x server: mp_cargoship_sh war \(mp\)' -or
            $outputText -notmatch '(?m)^  session   mp_cargoship_sh\r?$') {
            throw ('Launcher did not apply the lobby map, gametype, zone and session together. Output: ' +
                (($outputText -split "`n" | Select-Object -Last 10) -join ' | '))
        }
        $env:CODOL_MAP = 'mp_rust'
        $env:CODOL_GAMETYPE = 'dm'
        $env:CODOL_ZONE_TYPE = 'mp'
        $env:CODOL_SESSION_MAP = 'mp_rust'
        $ErrorActionPreference = 'Continue'
        try {
            $pinnedOutput = & (Join-Path $isolatedBin 'START-CODOL-SERVER.cmd') 2>&1
        } finally {
            $ErrorActionPreference = $priorErrorAction
        }
        $pinnedText = $pinnedOutput -join "`n"
        if ($pinnedText -notmatch 'sh1x server: mp_rust dm \(mp\)' -or
            $pinnedText -notmatch '(?m)^  session   mp_rust\r?$') {
            throw 'Explicit CODOL_MAP did not keep the manual match selection.'
        }
    } finally {
        foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name]) }
    }
} finally {
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $resolvedFixture = [System.IO.Path]::GetFullPath($fixtureRoot)
    if (-not $resolvedFixture.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Fixture cleanup path escaped the temporary directory'
    }
    Remove-Item -LiteralPath $resolvedFixture -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output 'CoDOL map handoff reader and launcher state paths: OK'
