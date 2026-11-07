[CmdletBinding()]
param(
    [ValidateSet("build", "test", "clean", "configure", "stage")]
    [string]$Action = "build",
    [ValidateSet("debug", "release")]
    [string]$Mode = "release",
    [switch]$VerboseBuild
)

$ErrorActionPreference = "Stop"
$Repository = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Xmake = Get-Command xmake -ErrorAction SilentlyContinue
if (-not $Xmake) {
    $BundledXmake = "D:\Program Files\xmake\xmake.exe"
    if (-not (Test-Path -LiteralPath $BundledXmake)) {
        throw "xmake was not found in PATH or at $BundledXmake"
    }
    $XmakePath = $BundledXmake
} else {
    $XmakePath = $Xmake.Source
}

$VcpkgRoot = $env:VCPKG_ROOT
if (-not $VcpkgRoot) {
    $KnownVcpkg = "E:\Source\Repos\Main\vcpkg"
    if (Test-Path -LiteralPath (Join-Path $KnownVcpkg "vcpkg.exe")) {
        $VcpkgRoot = $KnownVcpkg
    }
}
if (-not $VcpkgRoot -or -not (Test-Path -LiteralPath (Join-Path $VcpkgRoot "vcpkg.exe"))) {
    throw "Set VCPKG_ROOT to a vcpkg installation containing vcpkg.exe"
}

$env:VCPKG_ROOT = (Resolve-Path -LiteralPath $VcpkgRoot).Path
$env:PATH = "$env:VCPKG_ROOT;$env:PATH"
$Detail = if ($VerboseBuild) { "-vD" } else { $null }

Push-Location $Repository
try {
    if ($Action -eq "clean") {
        & $XmakePath clean --all
        exit $LASTEXITCODE
    }

    & $XmakePath f -p windows -a x86 -m $Mode -y $Detail
    if ($LASTEXITCODE -ne 0 -or $Action -eq "configure") {
        exit $LASTEXITCODE
    }

    if ($Action -eq "test") {
        & $XmakePath test $Detail
    } else {
        # Distribution callers build runtime plugins explicitly so the default
        # ol_deploy target cannot recursively invoke the installer.
        & $XmakePath --group=plugins $Detail
    }
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    if ($Action -eq "stage") {
        & (Join-Path $Repository "tools\distribution\StageCodolRuntime.ps1") -Mode $Mode -SkipBuild
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
