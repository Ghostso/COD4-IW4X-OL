$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_openssl3.log'
$done = Join-Path $ws '_install_openssl3.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-OPENSSL3' -Encoding UTF8
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
    $dst = Join-Path $dl 'nasm-3.01-win64.zip'
    $sha = '771c238ddb17c98d5736ccaba4ade1d1601d896f09e588489cb43a4f6381bc0ae14d1869f5316fe94f847f54867e65cf12665529b1e7ad88e5e7d3e162719a4f'
    if (-not (Test-Path $dst)) {
        foreach ($u in @('https://www.nasm.us/pub/nasm/releasebuilds/3.01/win64/nasm-3.01-win64.zip','https://vcpkg.github.io/assets/nasm/nasm-3.01-win64.zip')) {
            if (Test-Path $dst) { break }
            L ('trying ' + $u)
            & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 300 -o $dst $u 2>&1 | Select-Object -Last 2 | ForEach-Object { L ('  curl: ' + $_) }
            if ((Get-Item $dst -ErrorAction SilentlyContinue).Length -lt 100000) { Remove-Item $dst -Force -ErrorAction SilentlyContinue }
        }
    }
    if (Test-Path $dst) {
        $h = (Get-FileHash $dst -Algorithm SHA512).Hash.ToLower()
        L ('nasm zip bytes=' + (Get-Item $dst).Length + ' sha512match=' + ($h -eq $sha))
    } else { L 'nasm download FAILED' }
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
