$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_vcpkg3.log'
$done = Join-Path $ws '_install_vcpkg3.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-VCPKG3' -Encoding UTF8
$rc = 1
try {
    $cmakeBin = 'E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin'
    $ninjaBin = 'E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja'
    $env:Path = 'C:\Program Files\Git\cmd;' + $cmakeBin + ';' + $ninjaBin + ';' + $env:Path
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    $env:HTTP_PROXY  = 'http://127.0.0.1:10090'
    $env:HTTPS_PROXY = 'http://127.0.0.1:10090'
    $env:NO_PROXY    = 'localhost,127.0.0.1,::1'
    $env:VCPKG_KEEP_ENV_VARS = 'HTTP_PROXY;HTTPS_PROXY;NO_PROXY;http_proxy;https_proxy'
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    L ('ninja in path = ' + (((Get-Command ninja -ErrorAction SilentlyContinue).Source)))
    L ('cmake in path = ' + (((Get-Command cmake -ErrorAction SilentlyContinue).Source)))
    L ('KEEP_ENV_VARS=' + $env:VCPKG_KEEP_ENV_VARS)
    L 'installing openssl + mhook (x86-windows-static)...'
    & (Join-Path $vc 'vcpkg.exe') install 'openssl:x86-windows-static' 'mhook:x86-windows-static' --clean-after-build 2>&1 | ForEach-Object { L ('  ' + $_) }
    $irc = $LASTEXITCODE
    L ('vcpkg install exit=' + $irc)
    $inst = Join-Path $vc 'installed\x86-windows-static'
    L ('ssl.h exists=' + (Test-Path (Join-Path $inst 'include\openssl\ssl.h')))
    L ('mhook.h exists=' + (Test-Path (Join-Path $inst 'include\mhook.h')))
    L ('libcrypto.lib exists=' + (Test-Path (Join-Path $inst 'lib\libcrypto.lib')))
    L ('libssl.lib exists=' + (Test-Path (Join-Path $inst 'lib\libssl.lib')))
    if ($irc -eq 0) { $rc = 0 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
