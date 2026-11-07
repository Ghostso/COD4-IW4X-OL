$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$dir = Join-Path $ws '_install'
$log = Join-Path $ws '_install_xmake.log'
$done = Join-Path $ws '_install_xmake.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-XMAKE2' -Encoding UTF8
$rc = 1
try {
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    $v = '3.1.1'
    $name = 'xmake-v' + $v + '.win64.zip'
    $url = 'https://github.com/xmake-io/xmake/releases/download/v' + $v + '/' + $name
    $dl = Join-Path $dir $name
    L ('downloading ' + $url + ' via proxy')
    & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 300 -o $dl $url 2>&1 | Select-Object -Last 2 | ForEach-Object { L ('  ' + $_) }
    L ('download exit=' + $LASTEXITCODE + ' bytes=' + $(if (Test-Path $dl) { (Get-Item $dl).Length } else { -1 }))
    L ('sha256=' + (Get-FileHash $dl -Algorithm SHA256).Hash)
    $dest = 'D:\Program Files\xmake'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Expand-Archive -LiteralPath $dl -DestinationPath $dest -Force
    L ('expanded to ' + $dest)
    $exe = Get-ChildItem $dest -Filter 'xmake.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    L ('xmake.exe = ' + $(if ($exe) { $exe.FullName } else { 'NOT FOUND' }))
    if ($exe) {
        $vout = (& $exe.FullName --version 2>&1 | Out-String).Trim()
        L ('xmake --version -> ' + ($vout -replace '\r?\n',' | '))
        $xdir = $exe.DirectoryName
        $cur = [Environment]::GetEnvironmentVariable('Path','Machine')
        if ($cur -notlike ('*' + $xdir + '*')) {
            [Environment]::SetEnvironmentVariable('Path', ($xdir + ';' + $cur), 'Machine')
            L ('added to machine PATH: ' + $xdir)
        } else { L 'already in machine PATH' }
        $rc = 0
    } else { $rc = 97 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
