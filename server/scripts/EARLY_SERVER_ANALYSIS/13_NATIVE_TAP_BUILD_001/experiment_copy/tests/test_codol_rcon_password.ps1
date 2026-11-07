$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$helper = Join-Path $root 'tools\codol_rcon_password.ps1'
$launcher = Join-Path $root 'bin\START-CODOL-SERVER.cmd'
$fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("codol-rcon's test " + [guid]::NewGuid().ToString('N'))
$stateDir = Join-Path $fixtureRoot 'lobby state'
$passwordFile = Join-Path $stateDir 'native_server_rcon.txt'

function Assert-Run([string] $path, [int] $expectedExit) {
    # Invalid credentials are expected to write stderr. Capture that output
    # before asserting the helper's exit code under Windows PowerShell 5.
    $priorErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $helper -Path $path 2>&1
    } finally {
        $ErrorActionPreference = $priorErrorAction
    }
    if ($LASTEXITCODE -ne $expectedExit) {
        throw "RCON helper exited $LASTEXITCODE; expected $expectedExit"
    }
    if ($expectedExit -eq 0 -and $output) {
        throw 'RCON helper printed output on success'
    }
    if ($output -match 'known-test-credential') {
        throw 'RCON helper exposed a credential in error output'
    }
}

try {
    [System.IO.Directory]::CreateDirectory($stateDir) | Out-Null
    Assert-Run $passwordFile 0
    $first = [System.IO.File]::ReadAllText($passwordFile)
    if ($first -cnotmatch '^[0-9a-f]{32}$') {
        throw 'Generated credential is not 16 random bytes encoded as lowercase hex'
    }
    Assert-Run $passwordFile 0
    if ([System.IO.File]::ReadAllText($passwordFile) -cne $first) {
        throw 'RCON helper replaced an existing credential'
    }

    [System.IO.File]::WriteAllText($passwordFile, 'known-test-credential')
    Assert-Run $passwordFile 0
    if ([System.IO.File]::ReadAllText($passwordFile) -cne 'known-test-credential') {
        throw 'RCON helper changed a valid existing credential'
    }

    [System.IO.File]::WriteAllText($passwordFile, 'known-test-credential" & echo bad')
    Assert-Run $passwordFile 1
    Assert-Run (Join-Path $fixtureRoot 'missing\native_server_rcon.txt') 1

    [System.IO.File]::Delete($passwordFile)
    $env:CODOL_INSTALL = Join-Path $fixtureRoot 'absent install'
    $env:CODOL_REFERENCE = $stateDir
    $env:CODOL_STATE_DIR = $stateDir
    $env:CODOL_SCRIPTS = Join-Path $root 'bin\home\codol_rawfiles'
    $env:CODOL_MAP = 'mp_rust'
    $launchOutput = & $launcher 2>&1
    if ($LASTEXITCODE -ne 1 -or -not ($launchOutput -match 'C1\.exe not found')) {
        throw 'Launcher did not reject a missing game install before credential creation'
    }
    if ([System.IO.File]::Exists($passwordFile)) {
        throw 'Launcher created a credential for an invalid game install'
    }

    [System.IO.Directory]::CreateDirectory($env:CODOL_INSTALL) | Out-Null
    [System.IO.File]::WriteAllBytes((Join-Path $env:CODOL_INSTALL 'C1.exe'), [byte[]] @(0))
    $isolatedBin = Join-Path $fixtureRoot 'isolated launcher\bin'
    [System.IO.Directory]::CreateDirectory($isolatedBin) | Out-Null
    $isolatedLauncher = Join-Path $isolatedBin 'START-CODOL-SERVER.cmd'
    Copy-Item -LiteralPath $launcher -Destination $isolatedLauncher
    $launchOutput = & $isolatedLauncher 2>&1
    if ($LASTEXITCODE -ne 1 -or -not ($launchOutput -match 'Native server executable not found')) {
        throw 'Launcher did not reject a missing native server executable before credential creation'
    }
    if ([System.IO.File]::Exists($passwordFile)) {
        throw 'Launcher created a credential without a native server executable'
    }

    $batch = [System.IO.File]::ReadAllText($launcher)
    if ($batch -notmatch '(?m)^powershell\.exe .* -File "%~dp0\.\.\\tools\\codol_rcon_password\.ps1" -Path "%CODOL_RCON_FILE%"\r?$') {
        throw 'Launcher does not call the credential helper with a quoted path'
    }
    $credentialCall = $batch.IndexOf('codol_rcon_password.ps1')
    foreach ($required in @('CODOL_STATE_DIR%\', 'CODOL_INSTALL%\C1.exe', 'codol_dedrun_next.exe', 'CODOL_SCRIPTS%\maps', 'CODOL_REFERENCE%')) {
        if ($batch.IndexOf($required) -lt 0 -or $batch.IndexOf($required) -gt $credentialCall) {
            throw 'Launcher credential generation precedes an installation prerequisite'
        }
    }
} finally {
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $resolvedFixture = [System.IO.Path]::GetFullPath($fixtureRoot)
    if (-not $resolvedFixture.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Fixture cleanup path escaped the temporary directory'
    }
    Remove-Item -LiteralPath $resolvedFixture -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output 'CoDOL launcher RCON credential and preflight: OK'
