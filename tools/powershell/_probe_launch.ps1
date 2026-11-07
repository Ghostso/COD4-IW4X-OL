$ErrorActionPreference = 'Continue'
$root = 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL'
$exe = Join-Path $root 'codoMP_client_shipRetail.exe'
$log = Join-Path $root 'Logs\_direct_launch_probe.txt'
"start=$(Get-Date -Format o)" | Out-File -LiteralPath $log -Encoding utf8
$p = Start-Process -FilePath $exe -WorkingDirectory $root -PassThru
"pid=$($p.Id)" | Out-File -LiteralPath $log -Append -Encoding utf8
for ($i=0; $i -lt 14; $i++) {
  Start-Sleep -Milliseconds 500
  $x = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $x) { "t=$($i*0.5)s exited" | Out-File -LiteralPath $log -Append -Encoding utf8; break }
  $mods = @()
  try { $mods = $x.Modules | ForEach-Object { $_.ModuleName } } catch {}
  $want = @('codoMP_client_shipRetailBase.dll','TerSafe.dll','TenProxy.dll','TenSLX.dll','TCJ.dll')
  $found = $want | Where-Object { $mods -contains $_ }
  "t=$($i*0.5)s alive threads=$($x.Threads.Count) handles=$($x.HandleCount) mods=$($found -join ',')" | Out-File -LiteralPath $log -Append -Encoding utf8
}
$x = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($x) { "still alive" | Out-File -LiteralPath $log -Append -Encoding utf8; $null = $x.CloseMainWindow(); Start-Sleep -Seconds 2; if (Get-Process -Id $p.Id -ErrorAction SilentlyContinue) { Stop-Process -Id $p.Id } }
