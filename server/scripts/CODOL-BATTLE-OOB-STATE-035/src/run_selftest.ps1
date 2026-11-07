# TASK-035 -- run the offline self-test and capture output.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe  = Join-Path (Split-Path -Parent $here) 'build\bin\OobStateMachine.exe'
if (-not (Test-Path $exe)) { throw "not built: $exe" }
& $exe
exit $LASTEXITCODE
