$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_openssl5.log'
$done = Join-Path $ws '_install_openssl5.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-OPENSSL5' -Encoding UTF8
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
        @{ f='mingw-w64-x86_64-pkgconf-1~2.5.1-1-any.pkg.tar.zst'; u='https://mirror.msys2.org/mingw/mingw64/mingw-w64-x86_64-pkgconf-1~2.5.1-1-any.pkg.tar.zst'; s='2e604ccb004e2afa151e870112c95cab7106e43ee3cdfe67ac8815f3ec6754ccbc25211732eec8ac9ffe491071c63c9af18c8fa2bbfd6521a1b467bb11b1da03' }
    )
    foreach ($sd in $seeds) {
        $dst = Join-Path $dl $sd.f
        if (-not (Test-Path $dst)) {
            L ('downloading ' + $sd.f)
            & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 300 -o $dst $sd.u 2>&1 | Select-Object -Last 2 | ForEach-Object { L ('  curl: ' + $_) }
        }
        $h = (Get-FileHash $dst -Algorithm SHA512).Hash.ToLower()
        L ($sd.f + ' bytes=' + (Get-Item $dst).Length + ' sha512match=' + ($h -eq $sd.s))
    }
    L '--- vcpkg install openssl ---'
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
