$ErrorActionPreference = "Continue"
$root = (Resolve-Path "CODOLServer\archive").Path
$all = Get-ChildItem -LiteralPath $root -Directory | Where-Object { $_.Name -like "CONFIRMED_*" } | Sort-Object Name
$del = $all | Select-Object -First ($all.Count - 3)
foreach ($d in $del) {
  if (-not $d.FullName.StartsWith($root)) { throw "OUTSIDE ROOT: $($d.FullName)" }
}
foreach ($d in $del) {
  Remove-Item -LiteralPath $d.FullName -Recurse -Force
  Write-Output ("removed " + $d.Name)
}
Write-Output "remaining:"
Get-ChildItem -LiteralPath $root -Directory | ForEach-Object { Write-Output ("   " + $_.Name) }
$f = (Get-PSDrive D).Free
Write-Output ("free MB = " + [math]::Round($f / 1MB, 1))
