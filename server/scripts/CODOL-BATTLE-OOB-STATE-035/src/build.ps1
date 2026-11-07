# TASK-035 -- build the OOB state machine module + self-test EXE.
# Uses the same .NET Framework csc.exe that FREEZE-005 used for the frozen server,
# so the module is buildable in this environment without extra toolchain.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$out  = Join-Path (Split-Path -Parent $here) 'build\bin'
New-Item -ItemType Directory -Force $out | Out-Null
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) { $csc = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe' }
$srcs = Get-ChildItem $here -Filter *.cs | Sort-Object Name | ForEach-Object { $_.FullName }
Write-Host "csc      : $csc"
Write-Host "sources  : $($srcs.Count)"
$srcs | ForEach-Object { Write-Host "           $_" }
& $csc /nologo /target:exe /platform:anycpu /optimize+ /warn:4 `
       /out:"$out\OobStateMachine.exe" $srcs
if ($LASTEXITCODE -ne 0) { throw "BUILD FAILED (exit $LASTEXITCODE)" }
Write-Host "BUILD OK -> $out\OobStateMachine.exe"
