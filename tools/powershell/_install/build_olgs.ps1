$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_build_olgs.log'
$done = Join-Path $ws '_build_olgs.done'
$repo = 'F:\桌面\ol\ol-mod-olfinal'
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value '=== START BUILD ol_game_server ===' -Encoding UTF8
function L($m) { Add-Content -LiteralPath $log -Value $m -Encoding UTF8 }
L ('whoami=' + (whoami))
L ('time=' + (Get-Date -Format o))
$env:VCPKG_ROOT = 'E:\vcpkg'
$env:XMAKE_ROOT = 'y'
$env:HTTP_PROXY = 'http://127.0.0.1:10090'
$env:HTTPS_PROXY = 'http://127.0.0.1:10090'
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$env:Path = 'D:\Program Files\xmake\xmake;C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:Path
$xm = 'D:\Program Files\xmake\xmake\xmake.exe'
L ('xmake=' + ((& $xm --version 2>&1 | Out-String).Trim()))
Set-Location $repo
L '=== CONFIGURE: xmake f -p windows -a x86 -m release -y ==='
& $xm f -p windows -a x86 -m release -y 2>&1 | ForEach-Object { L ('  ' + $_) }
$cfgrc = $LASTEXITCODE
L ('CONFIGURE exit=' + $cfgrc)
if ($cfgrc -eq 0) {
    L '=== BUILD: xmake build ol_game_server ==='
    & $xm build ol_game_server 2>&1 | ForEach-Object { L ('  ' + $_) }
    L ('BUILD exit=' + $LASTEXITCODE)
} else {
    L 'configure failed; skipping build'
}
$art = Join-Path $repo 'build\bin\release\CodolGameServer.Localnet32'
L ('artifact exists=' + (Test-Path $art))
if (Test-Path $art) {
    $f = Get-Item $art
    L ('artifact path=' + $f.FullName)
    L ('artifact size=' + $f.Length)
    L ('artifact sha256=' + (Get-FileHash $art -Algorithm SHA256).Hash)
}
Set-Content -LiteralPath $done -Value ('CONFIG=' + $cfgrc) -Encoding UTF8
L '=== DONE ==='
