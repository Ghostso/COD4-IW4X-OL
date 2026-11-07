$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcher = Join-Path $root 'bin\START-CODOL-SERVER.cmd'
$fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('codol-split-client-' + [guid]::NewGuid().ToString('N'))
$isolatedBin = Join-Path $fixtureRoot 'launcher\bin'
$isolatedTools = Join-Path $fixtureRoot 'launcher\tools'
$install = Join-Path $fixtureRoot 'game assets'
$clientExe = Join-Path $fixtureRoot 'separate client\C1.exe'
$clientKeys = Join-Path $fixtureRoot 'separate client\c1_keys.bin'
$stateDir = Join-Path $fixtureRoot 'lobby state'
$referenceDir = Join-Path $fixtureRoot 'reference'
$profileDir = Join-Path $fixtureRoot 'separate lobby resources'
$scripts = Join-Path $fixtureRoot 'scripts'
$rconFile = Join-Path $stateDir 'native_server_rcon.txt'
$names = @('CODOL_INSTALL', 'CODOL_CLIENT_EXE', 'CODOL_REFERENCE', 'CODOL_PROFILE_DIR', 'CODOL_HOME',
           'CODOL_STATE_DIR', 'CODOL_SCRIPTS', 'CODOL_PACK_SOURCE', 'CODOL_BOTS', 'CODOL_MAP')
$saved = @{}
foreach ($name in $names) { $saved[$name] = [Environment]::GetEnvironmentVariable($name) }

try {
    foreach ($directory in @($isolatedBin, $isolatedTools, $install,
                             (Split-Path -Parent $clientExe), $stateDir, $referenceDir, $profileDir,
                             (Join-Path $scripts 'maps\mp\gametypes'))) {
        [System.IO.Directory]::CreateDirectory($directory) | Out-Null
    }
    Copy-Item -LiteralPath $launcher -Destination (Join-Path $isolatedBin 'START-CODOL-SERVER.cmd')
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_map_handoff.ps1') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_rcon_password.ps1') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_stage_server_pack.py') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_package.py') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $root 'tools\codol_export_c1_keys.py') -Destination $isolatedTools
    Copy-Item -LiteralPath (Join-Path $env:SystemRoot 'System32\whoami.exe') -Destination (Join-Path $isolatedBin 'codol_dedrun_next.exe')
    [System.IO.File]::WriteAllText((Join-Path $scripts 'maps\mp\gametypes\_callbacksetup.gsc'), '')
    [System.IO.File]::WriteAllBytes($clientExe, [byte[]]@(0))

    $env:CODOL_INSTALL = $install
    $env:CODOL_REFERENCE = $referenceDir
    [Environment]::SetEnvironmentVariable('CODOL_PROFILE_DIR', $null)
    $env:CODOL_HOME = Join-Path $fixtureRoot 'server home'
    $env:CODOL_STATE_DIR = $stateDir
    $env:CODOL_SCRIPTS = $scripts
    $env:CODOL_PACK_SOURCE = $root
    $env:CODOL_MAP = 'mp_rust'
    $env:CODOL_BOTS = '2'
    $isolatedLauncher = Join-Path $isolatedBin 'START-CODOL-SERVER.cmd'

    [Environment]::SetEnvironmentVariable('CODOL_CLIENT_EXE', $null)
    $output = & $isolatedLauncher 2>&1
    if ($LASTEXITCODE -ne 1 -or -not ($output -match 'C1\.exe not found') -or
        [System.IO.File]::Exists($rconFile)) {
        throw 'Default launcher no longer requires C1.exe in the asset root before creating an RCON credential.'
    }

    $env:CODOL_CLIENT_EXE = Join-Path $fixtureRoot 'missing client\C1.exe'
    $output = & $isolatedLauncher 2>&1
    if ($LASTEXITCODE -ne 1 -or -not ($output -match 'CODOL_CLIENT_EXE') -or
        [System.IO.File]::Exists($rconFile)) {
        throw 'Launcher did not reject a missing external client before creating an RCON credential.'
    }

    $env:CODOL_CLIENT_EXE = Split-Path -Parent $clientExe
    $output = & $isolatedLauncher 2>&1
    if ($LASTEXITCODE -ne 1 -or -not ($output -match 'must be a file') -or
        [System.IO.File]::Exists($rconFile)) {
        throw 'Launcher did not reject a directory as its external client file.'
    }

    $env:CODOL_CLIENT_EXE = $clientExe
    $priorErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $output = & $isolatedLauncher 2>&1 }
    finally { $ErrorActionPreference = $priorErrorAction }
    if (($output -join "`n") -notmatch 'sh1x server: mp_rust dm \(mp\)' -or
        -not [System.IO.File]::Exists($rconFile)) {
        throw ('Launcher did not accept split asset and client paths: ' + ($output -join "`n"))
    }
    if (-not [System.IO.File]::Exists((Join-Path $env:CODOL_HOME 'main\sh1x_svr_scripts.iwd'))) {
        throw 'Launcher did not stage the server-only IWD into the active filesystem home.'
    }

    [System.IO.File]::WriteAllBytes($clientKeys, (New-Object byte[] 1447))
    $env:CODOL_CLIENT_EXE = $clientKeys
    $ErrorActionPreference = 'Continue'
    try { $output = & $isolatedLauncher 2>&1 }
    finally { $ErrorActionPreference = $priorErrorAction }
    if (($output -join "`n") -notmatch 'sh1x server: mp_rust dm \(mp\)') {
        throw 'Launcher did not accept a separate c1_keys.bin path.'
    }

    # An alternate lobby supplies state and profiles without the old alpha0022
    # source tree. Reject a bad profile path before creating its RCON file.
    $env:CODOL_REFERENCE = Join-Path $fixtureRoot 'absent alpha0022'
    [System.IO.File]::Delete($rconFile)
    $env:CODOL_PROFILE_DIR = Join-Path $fixtureRoot 'missing resources'
    $output = & $isolatedLauncher 2>&1
    if ($LASTEXITCODE -ne 1 -or -not ($output -match 'Lobby profile directory not found') -or
        [System.IO.File]::Exists($rconFile)) {
        throw 'Launcher did not reject an invalid separate lobby profile path before creating a credential.'
    }
    $env:CODOL_PROFILE_DIR = $profileDir
    $ErrorActionPreference = 'Continue'
    try { $output = & $isolatedLauncher 2>&1 }
    finally { $ErrorActionPreference = $priorErrorAction }
    if (($output -join "`n") -notmatch 'sh1x server: mp_rust dm \(mp\)' -or
        -not [System.IO.File]::Exists($rconFile)) {
        throw 'Launcher did not accept separate lobby state and profile paths without alpha0022.'
    }

    $batch = [System.IO.File]::ReadAllText($launcher)
    if ($batch -notmatch '(?m)^  \+set codol_clientExe "%CODOL_CLIENT_EXE%" \^\r?$') {
        throw 'Launcher did not pass the external client path to the native archive loader.'
    }
    if ($batch -notmatch '(?m)^  \+set codol_profilePath "%CODOL_PROFILE_DIR%" \^\r?$') {
        throw 'Launcher did not pass the separate lobby profile path to the native server.'
    }
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name, $saved[$name]) }
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $resolvedFixture = [System.IO.Path]::GetFullPath($fixtureRoot)
    if (-not $resolvedFixture.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Fixture cleanup path escaped the temporary directory'
    }
    Remove-Item -LiteralPath $resolvedFixture -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output 'CoDOL split asset/client launcher path: OK'
