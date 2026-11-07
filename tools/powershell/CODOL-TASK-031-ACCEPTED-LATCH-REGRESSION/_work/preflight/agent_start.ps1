$dir = 'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline'
$py  = 'C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe'
Start-Process -FilePath $py -ArgumentList @('-X','utf8','-u', (Join-Path $dir 'elevated_agent.py')) -WorkingDirectory $dir -WindowStyle Hidden
