$ROOT = 'D:\BaiduNetdiskDownload\使命召唤OL'
$OFFLINE = Join-Path $ROOT 'OfflineServer'
$LOBBY = Join-Path $OFFLINE 'lobby_server'
$SBX = Join-Path $ROOT 'run_codol_001\sandbox_ifs1_20260923'
$LAUNCH = Join-Path $ROOT 'run_codol_001\launch.ps1'
$LOG = Join-Path $OFFLINE 'logs'

if (-not (Test-Path $LOG)) { New-Item -ItemType Directory -Path $LOG | Out-Null }

# start probe server
$probe = Start-Process python -ArgumentList '-X','utf8', (Join-Path $LOBBY 'lobby_probe_server.py'), '--cert-dir',$LOBBY,'--bind','127.0.0.1','--port','8443','--log',(Join-Path $LOG 'lobby_probe.jsonl') -PassThru -WindowStyle Hidden

# start socket server
$sock = Start-Process python -ArgumentList '-X','utf8', (Join-Path $LOBBY 'lobby_socket_server.py'), '--cert-dir',$LOBBY,'--bind','127.0.0.2','--port','8444','--log',(Join-Path $LOG 'lobby_socket.jsonl') -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3

# launch game via fixed chain with long observation window (180 seconds)
$game = Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$LAUNCH,'-Sandbox',$SBX,'-ObserveSeconds','180' -PassThru -WindowStyle Hidden

# wait up to 130 seconds, checking logs every 5 seconds
$kw = @('tls_ok','http','roundtrip','auth_task')
$probeOk = $false
$sockOk = $false
$elapsed = 0
$maxWait = 130
$interval = 5

while ($elapsed -lt $maxWait -and -not ($probeOk -and $sockOk)) {
    Start-Sleep -Seconds $interval
    $elapsed += $interval

    if (Test-Path (Join-Path $LOG 'lobby_probe.jsonl')) {
        $txt = Get-Content (Join-Path $LOG 'lobby_probe.jsonl') -Raw
        if ($kw | Where-Object { $txt -match $_ }) { $probeOk = $true }
    }
    if (Test-Path (Join-Path $LOG 'lobby_socket.jsonl')) {
        $txt = Get-Content (Join-Path $LOG 'lobby_socket.jsonl') -Raw
        if ($kw | Where-Object { $txt -match $_ }) { $sockOk = $true }
    }
    if (-not $game.HasExited) { continue }
    # game exited early
    break
}

# stop processes
$probe,$sock,$game | Where-Object { $_ -and -not $_.HasExited } | Stop-Process -Force

Write-Host "[===] Result"
Write-Host ("Probe log has interaction: " + (('Yes','No')[[int](-not $probeOk)]))
Write-Host ("Socket log has interaction: " + (('Yes','No')[[int](-not $sockOk)]))
Write-Host ("Game exit code: " + $(if ($game.HasExited) { $game.ExitCode } else { 'running' }))

exit $(if ($probeOk -and $sockOk) {0} else {2})