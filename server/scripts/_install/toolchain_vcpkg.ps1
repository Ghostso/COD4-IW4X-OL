$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_vcpkg.log'
$done = Join-Path $ws '_install_vcpkg.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-VCPKG' -Encoding UTF8
$rc = 1
$baseline = 'aa2d37682e3318d93aef87efa7b0e88e81cd3d59'
try {
    $env:Path = 'C:\Program Files\Git\cmd;' + $env:Path
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    L ('git=' + ((& git --version 2>&1) -join ' '))
    if (-not (Test-Path (Join-Path $vc '.git'))) {
        L 'cloning vcpkg (full, for baseline checkout)...'
        & git clone https://github.com/microsoft/vcpkg.git $vc 2>&1 | Select-Object -Last 5 | ForEach-Object { L ('  ' + $_) }
    } else { L 'vcpkg dir already present' }
    L ('clone exit=' + $LASTEXITCODE)
    $head = (& git -C $vc rev-parse HEAD 2>&1) -join ''
    L ('vcpkg HEAD=' + $head)
    if ($head -ne $baseline) {
        L ('checking out pinned baseline ' + $baseline)
        & git -C $vc fetch --depth 1 origin $baseline 2>&1 | Select-Object -Last 3 | ForEach-Object { L ('  ' + $_) }
        & git -C $vc checkout --detach $baseline 2>&1 | Select-Object -Last 3 | ForEach-Object { L ('  ' + $_) }
        $head2 = (& git -C $vc rev-parse HEAD 2>&1) -join ''
        L ('vcpkg HEAD after checkout=' + $head2)
    }
    L 'bootstrapping vcpkg...'
    & cmd.exe /c (([char]34 + (Join-Path $vc 'bootstrap-vcpkg.bat') + [char]34) + ' -disableMetrics') 2>&1 | Select-Object -Last 6 | ForEach-Object { L ('  ' + $_) }
    L ('vcpkg.exe exists=' + (Test-Path (Join-Path $vc 'vcpkg.exe')))
    if (-not (Test-Path (Join-Path $vc 'vcpkg.exe'))) { throw 'bootstrap failed' }
    L ('vcpkg version=' + (((& (Join-Path $vc 'vcpkg.exe') version 2>&1) -join ' ').Trim()))
    L 'installing openssl + mhook (x86-windows-static)...'
    & (Join-Path $vc 'vcpkg.exe') install 'openssl:x86-windows-static' 'mhook:x86-windows-static' --clean-after-build 2>&1 | Select-Object -Last 25 | ForEach-Object { L ('  ' + $_) }
    $irc = $LASTEXITCODE
    L ('vcpkg install exit=' + $irc)
    $inst = Join-Path $vc 'installed\x86-windows-static'
    L ('ssl.h exists=' + (Test-Path (Join-Path $inst 'include\openssl\ssl.h')))
    L ('mhook exists=' + (Test-Path (Join-Path $inst 'include\mhook.h')))
    L ('libcrypto.lib exists=' + (Test-Path (Join-Path $inst 'lib\libcrypto.lib')))
    if ($irc -eq 0) { $rc = 0 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
