$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_build_plugins.log'
$done = Join-Path $ws '_build_plugins.done'
$repo = 'F:\桌面\ol\ol-mod-olfinal'
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value '=== BUILD plugins group ===' -Encoding UTF8
function L($m) { Add-Content -LiteralPath $log -Value $m -Encoding UTF8 }
$env:VCPKG_ROOT = 'E:\vcpkg'
$env:XMAKE_ROOT = 'y'
$env:HTTP_PROXY = 'http://127.0.0.1:10090'
$env:HTTPS_PROXY = 'http://127.0.0.1:10090'
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$env:Path = 'D:\Program Files\xmake\xmake;C:\Program Files\Git\cmd;' + $env:Path
$xm = 'D:\Program Files\xmake\xmake\xmake.exe'
Set-Location $repo
L ('time=' + (Get-Date -Format o))
& $xm --group=plugins 2>&1 | Select-Object -Last 25 | ForEach-Object { L ('  ' + $_) }
L ('plugins build exit=' + $LASTEXITCODE)
L '=== release outputs ==='
Get-ChildItem (Join-Path $repo 'build\bin\release') -File | ForEach-Object { L ('  {0,10}  {1}' -f $_.Length, $_.Name) }
L '=== staging ==='
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'tools\distribution\StageCodolRuntime.ps1') -Mode release -SkipBuild 2>&1 | Select-Object -Last 15 | ForEach-Object { L ('  ' + $_) }
L ('stage exit=' + $LASTEXITCODE)
$stage = Join-Path $repo 'build\stage\codol'
L ('stage root exists=' + (Test-Path $stage))
if (Test-Path $stage) {
    foreach ($f in @('Ayria\Injector32.exe','Ayria\Bootstrapper32.dll','Ayria\Plugins\Localnetworking.Ayria32','Ayria\Plugins\Platformwrapper.Ayria32','Ayria\Plugins\Alwaysoffline.Localnet32','Ayria\Plugins\CodolGameServer.Localnet32','Ayria\ol-mod-runtime-manifest.json')) {
        L ('  ' + $f + ' = ' + (Test-Path (Join-Path $stage $f)))
    }
}
Set-Content -LiteralPath $done -Value 'ok' -Encoding UTF8
L '=== DONE ==='
