$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_openssl4.log'
$done = Join-Path $ws '_install_openssl4.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-OPENSSL4' -Encoding UTF8
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
        @{ f='jom_1_1_6.zip'; u='https://download.qt.io/official_releases/jom/jom_1_1_6.zip'; s='6fd99ad144e715cfdfe222b3999edcec0e1b82cfe216d79fedfd404942c56cfdd1827e445b8f7112148f75c02802d345f4b435321fc1530ac4b46e77bb9909b3' }
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
