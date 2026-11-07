Get-CimInstance Win32_Process -Filter "Name='cef_process.exe'" | Where-Object { $_.CommandLine -match 'a20210427unite' } | ForEach-Object {
  Write-Output ("killing " + $_.ProcessId)
  Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
Get-Process cef_process -ErrorAction SilentlyContinue | ForEach-Object { Write-Output ("still: " + $_.Id + " " + $_.MainWindowTitle) }