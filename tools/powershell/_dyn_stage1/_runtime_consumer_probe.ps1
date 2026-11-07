$ErrorActionPreference='Continue'
$root='D:\BaiduNetdiskDownload\使命召唤OL'
$exe=Join-Path $root 'COD OL\codoMP_client_shipRetail.exe'
$out=Join-Path $root '_dyn_stage1\runtime_consumer_probe'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$log=Join-Path $out 'trace.log'
$etl=Join-Path $out 'runtime.etl'
Remove-Item -LiteralPath $log,$etl -Force -ErrorAction SilentlyContinue
"START $(Get-Date -Format o)" | Out-File -LiteralPath $log -Encoding utf8
$p=$null
try {
  $p=Start-Process -FilePath $exe -WorkingDirectory (Split-Path -Parent $exe) -PassThru
  "PID=$($p.Id)" | Out-File -LiteralPath $log -Append -Encoding utf8
  $t0=Get-Date
  $lastMods=''
  $lastConn=''
  for($i=0;$i -lt 180;$i++){
    Start-Sleep -Milliseconds 100
    $q=Get-Process -Id $p.Id -ErrorAction SilentlyContinue
    if(-not $q){ break }
    $mods=@()
    try { $mods=@($q.Modules | ForEach-Object { $_.ModuleName }) } catch {}
    $mm=($mods | Sort-Object) -join ','
    if($mm -ne $lastMods){ "T={0:N3} MODS={1}" -f ((Get-Date)-$t0).TotalSeconds,$mm | Out-File -LiteralPath $log -Append -Encoding utf8; $lastMods=$mm }
    $title=$q.MainWindowTitle
    if($title){ "T={0:N3} WINDOW={1}" -f ((Get-Date)-$t0).TotalSeconds,$title | Out-File -LiteralPath $log -Append -Encoding utf8 }
    if($title -and $i -gt 10){ break }
  }
  try {
    $conns=Get-NetTCPConnection -OwningProcess $p.Id -ErrorAction SilentlyContinue | Select-Object State,LocalAddress,LocalPort,RemoteAddress,RemotePort
    "CONNECTIONS" | Out-File -LiteralPath $log -Append -Encoding utf8
    $conns | Format-List | Out-String | Out-File -LiteralPath $log -Append -Encoding utf8
  } catch { "CONNECT_ERR $($_.Exception.Message)" | Out-File -LiteralPath $log -Append -Encoding utf8 }
  "ALIVE=$([bool](Get-Process -Id $p.Id -ErrorAction SilentlyContinue))" | Out-File -LiteralPath $log -Append -Encoding utf8
} catch { "ERR $($_.Exception.Message)" | Out-File -LiteralPath $log -Append -Encoding utf8 }
"END $(Get-Date -Format o)" | Out-File -LiteralPath $log -Append -Encoding utf8
Get-Content -LiteralPath $log
