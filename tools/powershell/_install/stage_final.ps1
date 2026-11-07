$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_stage_final.log'
$done = Join-Path $ws '_stage_final.done'
$repo = 'F:\桌面\ol\ol-mod-olfinal'
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value '=== BUILD ol_room_owner + STAGE ===' -Encoding UTF8
function L($m) { Add-Content -LiteralPath $log -Value $m -Encoding UTF8 }
$env:VCPKG_ROOT = 'E:\vcpkg'
$env:XMAKE_ROOT = 'y'
$env:HTTP_PROXY = 'http://127.0.0.1:10090'
$env:HTTPS_PROXY = 'http://127.0.0.1:10090'
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$env:Path = 'D:\Program Files\xmake\xmake;C:\Program Files\Git\cmd;' + $env:Path
$xm = 'D:\Program Files\xmake\xmake\xmake.exe'
Set-Location $repo
& $xm build ol_room_owner 2>&1 | Select-Object -Last 6 | ForEach-Object { L ('  ' + $_) }
L ('ol_room_owner build exit=' + $LASTEXITCODE)
L '=== staging ==='
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo 'tools\distribution\StageCodolRuntime.ps1') -Mode release -SkipBuild 2>&1 | Select-Object -Last 12 | ForEach-Object { L ('  ' + $_) }
L ('stage exit=' + $LASTEXITCODE)
$stage = Join-Path $repo 'build\stage\codol'
L '=== staged tree verification ==='
foreach ($f in @('Ayria\Injector32.exe','Ayria\Bootstrapper32.dll','Ayria\Plugins\Localnetworking.Ayria32','Ayria\Plugins\Platformwrapper.Ayria32','Ayria\Plugins\Alwaysoffline.Localnet32','Ayria\Plugins\CodolGameServer.Localnet32','Ayria\ol_room_owner.exe','Ayria\Assets\Platformwrapper\Platform.json','Ayria\Assets\Alwaysoffline\Identity.json','Ayria\Assets\OlMod\GameScripts\common.lua','Ayria\Assets\OlMod\GameScripts\gametypes\sd.lua','Ayria\Assets\OlMod\GameScripts\maps\mp_crash_tropical.lua','Ayria\ol-mod-runtime-manifest.json','Launch_OLMod.bat')) {
    L ('  {0,-58} {1}' -f $f, (Test-Path (Join-Path $stage $f)))
}
L '=== staged plugin hashes ==='
Get-ChildItem (Join-Path $stage 'Ayria\Plugins') -File -ErrorAction SilentlyContinue | ForEach-Object { L ('  {0,10}  {1}  {2}' -f $_.Length, (Get-FileHash $_.FullName -Algorithm SHA256).Hash.Substring(0,16), $_.Name) }
Set-Content -LiteralPath $done -Value 'ok' -Encoding UTF8
L '=== DONE ==='
