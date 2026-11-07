$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_probe_fwrite.log'
Set-Content -LiteralPath $log -Value 'START' -Encoding UTF8
function L($m) { Add-Content -LiteralPath $log -Value $m -Encoding UTF8 }
$repo = 'F:\桌面\ol\ol-mod-olfinal'
L ('whoami=' + (whoami))
L ('repo exists=' + (Test-Path $repo))
try {
    New-Item -ItemType Directory -Force -Path (Join-Path $repo 'build') | Out-Null
    Set-Content -LiteralPath (Join-Path $repo 'build\_probe_elev.txt') -Value 'elev-ok' -Encoding ascii
    L ('elevated write OK: ' + (Get-Content (Join-Path $repo 'build\_probe_elev.txt')))
    Remove-Item (Join-Path $repo 'build\_probe_elev.txt') -Force -ErrorAction SilentlyContinue
} catch { L ('elevated write FAILED: ' + $_.Exception.Message) }
# xmake presence
$x = 'D:\Program Files\xmake\xmake\xmake.exe'
L ('xmake exists=' + (Test-Path $x))
if (Test-Path $x) { L ('xmake: ' + ((& $x --version 2>&1 | Out-String).Trim().Split([char]10)[0])) }
L ('vcpkg root=' + $env:VCPKG_ROOT)
L 'DONE'
