[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Executable,
 [Parameter(Mandatory=$true)][string]$ArgumentLine,
 [string]$WorkingDirectory = (Split-Path -Parent $Executable),
 [int]$Seconds = 180
)
$log = Join-Path $PSScriptRoot 'launch_watch.csv'
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $Executable
$psi.Arguments = $ArgumentLine
$psi.WorkingDirectory = $WorkingDirectory
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
"launcher_start pid=$($p.Id) name=$($p.ProcessName) time=$([DateTime]::Now.ToString('o'))" | Set-Content -LiteralPath $log -Encoding UTF8
$seen = @{}
$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end) {
 try {
  Get-CimInstance Win32_Process -ErrorAction Stop | ForEach-Object {
   if ($_.Name -match '^(codoMP_client_shipRetail|TP3Helper|client_launcher|tcls_core|Assistant|wegame|tgp_daemon|TQMCenter|Client)\.exe$') {
    $key = "{0}|{1}|{2}" -f $_.ProcessId,$_.ParentProcessId,$_.CommandLine
    if (-not $seen.ContainsKey($key)) {
     $seen[$key] = $true
     $line = [pscustomobject]@{ time=(Get-Date).ToString('o'); pid=$_.ProcessId; ppid=$_.ParentProcessId; name=$_.Name; path=$_.ExecutablePath; cmdline=$_.CommandLine }
     $line | Export-Csv -LiteralPath $log -Append -NoTypeInformation -Encoding UTF8
    }
   }
  }
 } catch { Start-Sleep -Milliseconds 20 }
 Start-Sleep -Milliseconds 50
}
