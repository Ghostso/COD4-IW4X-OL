$ErrorActionPreference="Continue"
$root="D:\BaiduNetdiskDownload\使命召唤OL"
$exe=Join-Path $root "COD OL\codoMP_client_shipRetail.exe"
$out=Join-Path $root "_dyn_stage1\context_diff_probe"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$result=[ordered]@{}
$result.started=Get-Date -Format o
$result.exe=$exe
$result.exe_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLower()
$pre=Get-Process -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path
$preNames=@($pre | ForEach-Object { "{0}:{1}" -f $_.ProcessName,$_.Id })
$result.pre_processes=$preNames
$beforeHandles=@(Get-ChildItem "\\.\pipe\" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name)
$result.before_pipes=$beforeHandles
$p=Start-Process -FilePath $exe -WorkingDirectory (Split-Path -Parent $exe) -PassThru
$result.pid=$p.Id
$start=Get-Date
$samples=@()
for($i=0;$i -lt 50;$i++){
  Start-Sleep -Milliseconds 200
  $pp=Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  $alive=($null -ne $pp)
  $mods=@()
  if($alive){$mods=@($pp.Modules | ForEach-Object { $_.ModuleName })}
  $win=@(Get-Process -Id $p.Id -ErrorAction SilentlyContinue | Select-Object -ExpandProperty MainWindowTitle -ErrorAction SilentlyContinue)
  $samples += [ordered]@{t=((Get-Date)-$start).TotalSeconds;alive=$alive;modules=$mods;title=$win}
  if(-not $alive){break}
  if($mods -contains "codoMP_client_shipRetailBase.dll"){Start-Sleep -Milliseconds 1000;break}
}
$result.samples=$samples
$after=Get-Process -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path
$afterNames=@($after | ForEach-Object { "{0}:{1}" -f $_.ProcessName,$_.Id })
$result.after_processes=$afterNames
$result.after_pipes=@(Get-ChildItem "\\.\pipe\" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name)
$result.windows=@(Get-Process -Id $p.Id -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,MainWindowTitle,StartTime)
$result.exit=if(Get-Process -Id $p.Id -ErrorAction SilentlyContinue){"alive"}else{"exited"}
$result.elapsed=((Get-Date)-$start).TotalSeconds
$result | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 (Join-Path $out "probe.json")
Write-Output ("PROBE pid={0} elapsed={1} exit={2} out={3}" -f $p.Id,$result.elapsed,$result.exit,$out)
