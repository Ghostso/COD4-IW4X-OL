$ErrorActionPreference='Continue'
$py='C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe'
"marker: start $(Get-Date -Format o)" | Out-File -Encoding utf8 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\_work\preflight\elev_marker.txt'
if (-not (Test-Path $py)) { "NO PYTHON: $py" | Out-File -Append -Encoding utf8 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\_work\preflight\elev_marker.txt'; exit 1 }
"python ok" | Out-File -Append -Encoding utf8 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\_work\preflight\elev_marker.txt'
$p = Start-Process -FilePath $py -ArgumentList @('-X','utf8','-u','D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\elevated_agent.py') -WorkingDirectory 'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline' -WindowStyle Hidden -PassThru
"started pid=$($p.Id)" | Out-File -Append -Encoding utf8 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\_work\preflight\elev_marker.txt'
Start-Sleep -Seconds 3
"alive=$(-not $p.HasExited)" | Out-File -Append -Encoding utf8 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION\_work\preflight\elev_marker.txt'
