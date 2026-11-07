$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_vcpkg6.log'
$done = Join-Path $ws '_install_vcpkg6.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-VCPKG6' -Encoding UTF8
$rc = 1
try {
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    $env:Path = 'C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:Path
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    $toolDir = Join-Path $vc 'downloads\tools\ninja-1.13.2-windows'
    Remove-Item $toolDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $toolDir | Out-Null
    $zip = Join-Path $vc 'downloads\ninja-win-1.13.2.zip'
    & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 300 -o $zip 'https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip' 2>&1 | Select-Object -Last 2 | ForEach-Object { L ('  curl: ' + $_) }
    L ('zip bytes=' + (Get-Item $zip).Length + ' sha256=' + (Get-FileHash $zip -Algorithm SHA256).Hash)
    Expand-Archive -LiteralPath $zip -DestinationPath $toolDir -Force
    $nj = Join-Path $toolDir 'ninja.exe'
    L ('ninja.exe exists=' + (Test-Path $nj) + ' version=' + (& $nj --version 2>&1))
    L '--- vcpkg fetch ninja (should be suitable now) ---'
    $fo = (& (Join-Path $vc 'vcpkg.exe') fetch ninja --x-stderr-status 2>&1 | Out-String).Trim()
    L ('  fetch exit=' + $LASTEXITCODE + ' -> ' + ($fo -replace '\r?\n',' | '))
    L '--- vcpkg install openssl + mhook ---'
    & (Join-Path $vc 'vcpkg.exe') install 'openssl:x86-windows-static' 'mhook:x86-windows-static' --clean-after-build 2>&1 | ForEach-Object { L ('  ' + $_) }
    $irc = $LASTEXITCODE
    L ('vcpkg install exit=' + $irc)
    $inst = Join-Path $vc 'installed\x86-windows-static'
    L ('ssl.h      = ' + (Test-Path (Join-Path $inst 'include\openssl\ssl.h')))
    L ('mhook.h    = ' + (Test-Path (Join-Path $inst 'include\mhook.h')))
    L ('libcrypto  = ' + (Test-Path (Join-Path $inst 'lib\libcrypto.lib')))
    L ('libssl     = ' + (Test-Path (Join-Path $inst 'lib\libssl.lib')))
    if ($irc -eq 0) { $rc = 0 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
