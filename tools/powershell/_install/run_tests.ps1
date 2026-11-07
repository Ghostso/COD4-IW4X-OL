$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_run_tests.log'
$done = Join-Path $ws '_run_tests.done'
$repo = 'F:\桌面\ol\ol-mod-olfinal'
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value '=== BUILD+RUN TEST SUITES ===' -Encoding UTF8
function L($m) { Add-Content -LiteralPath $log -Value $m -Encoding UTF8 }
$env:VCPKG_ROOT = 'E:\vcpkg'
$env:XMAKE_ROOT = 'y'
$env:HTTP_PROXY = 'http://127.0.0.1:10090'
$env:HTTPS_PROXY = 'http://127.0.0.1:10090'
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
$env:Path = 'D:\Program Files\xmake\xmake;C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:Path
$xm = 'D:\Program Files\xmake\xmake\xmake.exe'
Set-Location $repo
foreach ($t in @('ol_game_server_tests','ol_dedicated_control_tests','ol_playerdata_def_tests')) {
    L ('=== BUILD ' + $t + ' ===')
    & $xm build $t 2>&1 | Select-Object -Last 4 | ForEach-Object { L ('  ' + $_) }
    L ('build exit=' + $LASTEXITCODE)
    $exe = Join-Path $repo ('build\bin\release\' + $t + '.exe')
    L ('exe=' + $exe + ' exists=' + (Test-Path $exe))
    if (Test-Path $exe) {
        L ('=== RUN ' + $t + ' (cwd=repo root) ===')
        $out = (& $exe 2>&1 | Out-String)
        L ('run exit=' + $LASTEXITCODE)
        L (($out.Trim() -split "`n" | Select-Object -Last 25) -join "`n")
    }
}
L '=== DONE ==='
Set-Content -LiteralPath $done -Value 'ok' -Encoding UTF8
