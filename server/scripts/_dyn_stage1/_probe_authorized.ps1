$ErrorActionPreference='Stop'
$exe=(Resolve-Path 'COD OL\codoMP_client_shipRetail.exe').Path
$wd=(Resolve-Path 'COD OL').Path
$out='_dyn_stage1\direct_authorized_probe'
if(Test-Path $out){ Remove-Item -LiteralPath $out -Recurse -Force }
New-Item -ItemType Directory -Path $out | Out-Null
$before=@(Get-Process codoMP_client_shipRetail,tgp_daemon,wegame,launcher,TP3Helper -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime)
$p=Start-Process -FilePath $exe -WorkingDirectory $wd -PassThru
$start=Get-Date
$samples=@()
for($i=0;$i -lt 60;$i++){
  Start-Sleep -Milliseconds 500
  $q=Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  $mods=@()
  if($q){ try{$mods=@($q.Modules | Select-Object -ExpandProperty ModuleName)}catch{} }
  $children=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ParentProcessId -eq $p.Id } | Select-Object ProcessId,Name,CommandLine)
  $samples += [pscustomobject]@{t=((Get-Date)-$start).TotalSeconds; alive=[bool]$q; modules=($mods -join ','); children=($children | ForEach-Object { "$($_.ProcessId):$($_.Name):$($_.CommandLine)" }) -join ' || '}
  if(-not $q){break}
}
$exit=$null; try{$p.Refresh(); $exit=$p.ExitCode}catch{}
$after=@(Get-Process codoMP_client_shipRetail,tgp_daemon,wegame,launcher,TP3Helper -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime)
$samples | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out\samples.json" -Encoding UTF8
[pscustomobject]@{pid=$p.Id;started=$start;exited=(-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue));exitcode=$exit;before=$before;after=$after} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out\summary.json" -Encoding UTF8
Get-Content -LiteralPath "$out\summary.json"
