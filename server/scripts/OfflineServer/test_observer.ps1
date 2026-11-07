$runRoot = 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001'
$projectRoot = Split-Path -Parent $runRoot
$restoreRoot = Join-Path $projectRoot 'restore_iips_contract_001'
$sandbox = Join-Path $runRoot 'sandbox_ifs1_20260923'
$probe = Join-Path $restoreRoot 'observer2\out\AboProbe.exe'
$restoreRuns = Join-Path $restoreRoot 'runs'
$installRoot = Join-Path $projectRoot 'COD OL'
$iips = Join-Path $sandbox 'IIPS'
$tag = 'IFS1_ELEVATED_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$run = Join-Path $runRoot ('runs\' + $tag)
$startUtc = (Get-Date).ToUniversalTime()
$samplePath = Join-Path $run 'observer.jsonl'
$processPath = Join-Path $run 'processes_final.json'
$hostPidPath = Join-Path $iips 'HostPid'

New-Item -ItemType Directory -Path $run -Force | Out-Null

if (-not (Test-Path -LiteralPath $sandbox)) { throw "Sandbox missing: $sandbox" }
if (-not (Test-Path -LiteralPath $probe)) { throw "Probe missing: $probe" }
if (-not (Test-Path -LiteralPath (Join-Path $sandbox 'codoMP_client_shipRetail.exe'))) { throw 'Sandbox game executable missing' }

Write-Host "Starting AboProbe..."
$abo = Start-Process -FilePath $probe -ArgumentList @('--duration','10','--sandbox',$sandbox,'--out',(Join-Path $run 'aboprobe.stdout')) -WindowStyle Hidden -PassThru
Write-Host "AboProbe PID: $($abo.Id)"
$abo.WaitForExit()
Write-Host "AboProbe exited with code: $($abo.ExitCode)"

if (Test-Path (Join-Path $run 'aboprobe.stdout')) {
    Get-Content (Join-Path $run 'aboprobe.stdout')
}