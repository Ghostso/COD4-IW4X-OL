Get-Item -LiteralPath "COD OL\WeGameLauncher\log\WegameLauncher.20260913-184748.18620" | Format-List FullName,Length,LastWriteTime
Get-Content -LiteralPath "COD OL\WeGameLauncher\log\WegameLauncher.20260913-184748.18620" -Encoding UTF8
Get-CimInstance Win32_Process | Where-Object { $_.Name -match "tcls|tgp|wegame|launcher|Client|TQMCenter|TP3|codoMP|Tenio|TPSvc" } | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | Format-List
wevtutil el | Select-String -Pattern "Kernel-Process|Process|Win32|Sysmon|Security|Application"
