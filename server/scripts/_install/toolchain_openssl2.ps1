$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_openssl2.log'
$done = Join-Path $ws '_install_openssl2.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-OPENSSL2' -Encoding UTF8
$rc = 1
try {
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    $env:Path = 'C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:Path
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    $dl = Join-Path $vc 'downloads'
    New-Item -ItemType Directory -Force -Path $dl | Out-Null
    $seeds = @(
        @{ u='https://github.com/openssl/openssl/archive/openssl-3.6.1.tar.gz'; f='openssl-openssl-openssl-3.6.1.tar.gz'; s='07cfcc71336ece71e713aab8be4a05e2b474bfab175d4c7a4ebcf378f4b1478bcf0e4a46ec88fc6163454fdf7fdf375ab856a5de1c444a41420a02510ae1ac7b' },
        @{ u='https://github.com/StrawberryPerl/Perl-Dist-Strawberry/releases/download/SP_54201_64bit/strawberry-perl-5.42.0.1-64bit-portable.zip'; f='strawberry-perl-5.42.0.1-64bit-portable.zip'; s='e78fc86eb76dc34f2fd8a911537b20378e1ce486a3ea1a167001fd040c2468e8db5e711a895314e7ead3511f3caafccc1ffbfd0bd4096c0360d712a9668fe69b' }
    )
    foreach ($sd in $seeds) {
        $dst = Join-Path $dl $sd.f
        if (-not (Test-Path $dst)) {
            L ('downloading ' + $sd.f)
            & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 900 -o $dst $sd.u 2>&1 | Select-Object -Last 2 | ForEach-Object { L ('  curl: ' + $_) }
        }
        $h = (Get-FileHash $dst -Algorithm SHA512).Hash.ToLower()
        L ($sd.f + ' bytes=' + (Get-Item $dst).Length + ' sha512match=' + ($h -eq $sd.s))
    }
    L '--- vcpkg install openssl (no clean-after-build) ---'
    & (Join-Path $vc 'vcpkg.exe') install 'openssl:x86-windows-static' 2>&1 | ForEach-Object { L ('  ' + $_) }
    $irc = $LASTEXITCODE
    L ('vcpkg install exit=' + $irc)
    $inst = Join-Path $vc 'installed\x86-windows-static'
    L ('ssl.h      = ' + (Test-Path (Join-Path $inst 'include\openssl\ssl.h')))
    L ('libcrypto  = ' + (Test-Path (Join-Path $inst 'lib\libcrypto.lib')))
    L ('libssl     = ' + (Test-Path (Join-Path $inst 'lib\libssl.lib')))
    L ('mhook.lib  = ' + (Test-Path (Join-Path $inst 'lib\mhook.lib')))
    if ($irc -eq 0) { $rc = 0 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
