Write-Output "restarting CryptSvc..."
Restart-Service CryptSvc -Force -ErrorAction Stop
Write-Output "CryptSvc restarted"
Get-Service CryptSvc | Select-Object Name,Status