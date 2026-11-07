Get-CimInstance Win32_Process -Filter "Name='cef_process.exe'" | ForEach-Object {
  Write-Output ("PID=" + $_.ProcessId)
  Write-Output ("PPID=" + $_.ParentProcessId)
  Write-Output ("CMD=" + $_.CommandLine)
  Write-Output "---"
}