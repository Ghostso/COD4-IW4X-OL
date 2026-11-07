$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$dir = Join-Path $ws '_install'
$log = Join-Path $ws '_net_probe.log'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Set-Content -LiteralPath $log -Value 'START-NETPROBE' -Encoding UTF8
$targets = @(
  'https://github.com/xmake-io/xmake/releases/download/v3.1.1/xmake-v3.1.1.win64.zip',
  'https://objects.githubusercontent.com/',
  'https://codeload.github.com/xmake-io/xmake/zip/refs/heads/master',
  'https://xmake.io/psget.text'
)
foreach ($t in $targets) {
    L ('=== ' + $t)
    foreach ($mode in @('noproxy','proxy')) {
        $pfx = @(); if ($mode -eq 'proxy') { $pfx = @('--proxy','http://127.0.0.1:10090') } else { $pfx = @('--noproxy','*') }
        $args = @('-sS','-L','-o','NUL','-w','"%{http_code} %{size_download} %{time_total}"','--max-time','60') + $pfx + @($t)
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $out = (& curl.exe @args 2>&1 | Out-String).Trim()
        $sw.Stop()
        L ('  ' + $mode + ' -> ' + $out + '  exit=' + $LASTEXITCODE + ' wall=' + [math]::Round($sw.Elapsed.TotalSeconds,1) + 's')
    }
}
L 'DONE'
