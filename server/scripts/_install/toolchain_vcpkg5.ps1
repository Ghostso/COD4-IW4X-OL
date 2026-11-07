$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_vcpkg5.log'
$done = Join-Path $ws '_install_vcpkg5.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-VCPKG5' -Encoding UTF8
$rc = 1
try {
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    $env:Path = 'C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;' + $env:Path
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    $dl = Join-Path $vc 'downloads'
    New-Item -ItemType Directory -Force -Path $dl | Out-Null
    $specs = @(
        @{ url='https://github.com/apriorit/mhook/archive/2.5.1.tar.gz'; file='apriorit-mhook-2.5.1.tar.gz'; sha='914f198417b1e30301a42463af5cfbf9269dc64bcf1be87d3d6d2943fd72b3536f48eb4bfb25a51dd0bbe0f8f099777b2d49c9d58cb2e2eeb517d998917ae976' },
        @{ url='https://github.com/openssl/openssl/archive/openssl-3.6.1.tar.gz'; file='openssl-openssl-openssl-3.6.1.tar.gz'; sha='07cfcc71336ece71e713aab8be4a05e2b474bfab175d4c7a4ebcf378f4b1478bcf0e4a46ec88fc6163454fdf7fdf375ab856a5de1c444a41420a02510ae1ac7b' }
    )
    foreach ($s in $specs) {
        $dst = Join-Path $dl $s.file
        & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 600 -o $dst $s.url 2>&1 | Select-Object -Last 2 | ForEach-Object { L ('  curl: ' + $_) }
        $h = (Get-FileHash $dst -Algorithm SHA512).Hash.ToLower()
        L ($s.file + ' bytes=' + (Get-Item $dst).Length + ' sha512match=' + ($h -eq $s.sha) + ' found=' + $h.Substring(0,16) + '...')
    }
    L '--- vcpkg install ---'
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
