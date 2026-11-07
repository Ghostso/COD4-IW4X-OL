$ErrorActionPreference='Continue'
$out='D:\BaiduNetdiskDownload\使命召唤OL\_dyn_stage1\tcls_etw.etl'
if (Test-Path -LiteralPath $out) { Remove-Item -LiteralPath $out -Force }
Write-Host 'STARTING'
& wpr.exe -start GeneralProfile -start FileIO -start Registry -start Handle -filemode
$startCode=$LASTEXITCODE
Write-Host ('STARTCODE='+$startCode)
if ($startCode -ne 0) { exit $startCode }
Start-Sleep -Seconds 2
$before=@(Get-Process -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$p=Start-Process -FilePath 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS\Client.exe' -WorkingDirectory 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS' -PassThru
Write-Host ('TCLS_PID='+$p.Id)
Start-Sleep -Seconds 75
$procs=Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'Client|launcher|codoMP|TQMCenter|Tenio|tgp|WeGame|wegame_env|tcls|TPSvc|wegame' }
$procs | Select-Object Id,ProcessName,StartTime,Path | Sort-Object StartTime | Format-Table -AutoSize
& wpr.exe -stop $out
Write-Host ('STOPCODE='+$LASTEXITCODE)
Get-Item -LiteralPath $out | Select-Object FullName,Length,LastWriteTime | Format-List
