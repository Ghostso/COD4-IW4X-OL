$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_vcpkg4.log'
$done = Join-Path $ws '_install_vcpkg4.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-VCPKG4' -Encoding UTF8
$rc = 1
try {
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    $env:Path = 'C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;' + $env:Path
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    L ('ProxyOverride=[' + (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyOverride -ErrorAction SilentlyContinue).ProxyOverride + ']')
    $ninjaSrc = 'E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
    $toolDir = Join-Path $vc 'downloads\tools\ninja-1.13.2-windows'
    New-Item -ItemType Directory -Force -Path $toolDir | Out-Null
    Copy-Item $ninjaSrc (Join-Path $toolDir 'ninja.exe') -Force
    L ('seeded ' + (Join-Path $toolDir 'ninja.exe') + ' = ' + (Test-Path (Join-Path $toolDir 'ninja.exe')))
    L '--- vcpkg fetch ninja (as-is) ---'
    $o = (& (Join-Path $vc 'vcpkg.exe') fetch ninja --x-stderr-status 2>&1 | Out-String).Trim()
    L ('  fetch exit=' + $LASTEXITCODE + ' out=' + ($o -replace '\r?\n',' | '))
    if ($LASTEXITCODE -ne 0) {
        L '--- vcpkg fetch ninja with explicit proxy env ---'
        $env:HTTP_PROXY='http://127.0.0.1:10090'; $env:HTTPS_PROXY='http://127.0.0.1:10090'
        $o2 = (& (Join-Path $vc 'vcpkg.exe') fetch ninja --x-stderr-status 2>&1 | Out-String).Trim()
        L ('  fetch exit=' + $LASTEXITCODE + ' out=' + ($o2 -replace '\r?\n',' | '))
    }
    L '--- installing openssl + mhook ---'
    & (Join-Path $vc 'vcpkg.exe') install 'openssl:x86-windows-static' 'mhook:x86-windows-static' --clean-after-build 2>&1 | ForEach-Object { L ('  ' + $_) }
    $irc = $LASTEXITCODE
    L ('vcpkg install exit=' + $irc)
    $inst = Join-Path $vc 'installed\x86-windows-static'
    L ('ssl.h exists=' + (Test-Path (Join-Path $inst 'include\openssl\ssl.h')))
    L ('mhook.h exists=' + (Test-Path (Join-Path $inst 'include\mhook.h')))
    L ('libcrypto.lib exists=' + (Test-Path (Join-Path $inst 'lib\libcrypto.lib')))
    if ($irc -eq 0) { $rc = 0 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
