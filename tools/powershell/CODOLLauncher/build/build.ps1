$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root 'src'
$out = Join-Path $root 'CODOLLauncher.exe'

if ((Get-Command cl.exe -ErrorAction SilentlyContinue)) {
    Push-Location $root
    try {
        cl /nologo /W3 /O2 /EHsc /DUNICODE /D_UNICODE `
            $src\main.cpp $src\Launcher.cpp $src\GameProcess.cpp `
            $src\LauncherContext.cpp $src\TCLSCompatibility.cpp `
            $src\BootstrapMonitor.cpp `
            /Fe:$out /link user32.lib shell32.lib shlwapi.lib psapi.lib advapi32.lib
        if ($LASTEXITCODE -ne 0) { throw "cl failed with $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    Write-Host "Built $out"
    exit 0
}

if ((Get-Command g++.exe -ErrorAction SilentlyContinue)) {
    Push-Location $root
    try {
        g++ -std=c++17 -O2 -municode -DUNICODE -D_UNICODE $src\main.cpp `
            $src\Launcher.cpp $src\GameProcess.cpp $src\LauncherContext.cpp `
            $src\TCLSCompatibility.cpp $src\BootstrapMonitor.cpp `
            -o $out -lshlwapi -lpsapi -ladvapi32 -lshell32 -static-libgcc -static-libstdc++
        if ($LASTEXITCODE -ne 0) { throw "g++ failed with $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
    Write-Host "Built $out"
    exit 0
}

Write-Host "No cl.exe or g++.exe found on PATH. Falling back to .NET C# launcher builder." -ForegroundColor Yellow
$csc = Get-ChildItem -Path 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe','C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $csc) {
    Write-Host "csc.exe not found either. Install MSVC or MinGW, or open build\CODOLLauncher.vcxproj in Visual Studio." -ForegroundColor Red
    exit 1
}

Push-Location $root
try {
    # Native C# launcher cannot be /target:winexe with console output easily; use exe instead.
    & $csc.FullName /nologo /optimize+ /out:$out /target:exe /platform:x86 (Join-Path $PSScriptRoot 'CODOLLauncher.cs')
    if ($LASTEXITCODE -ne 0) { throw "csc failed with $LASTEXITCODE" }
} finally {
    Pop-Location
}
Write-Host "Built managed CODOLLauncher.exe, but native C++ project remains in src/ for a real compiler build."
exit 0
