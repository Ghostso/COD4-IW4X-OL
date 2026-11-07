# EBO1 - run the remaining duration matrix sequentially
$ErrorActionPreference = 'SilentlyContinue'
$root = $PSScriptRoot
& (Join-Path $root 'run.ps1') -tag R4 -duration 60 -mode baseline
& (Join-Path $root 'run.ps1') -tag R5 -duration 120 -mode baseline
& (Join-Path $root 'run.ps1') -tag R6 -duration 300 -mode baseline
& (Join-Path $root 'run.ps1') -tag R8 -duration 300 -mode original
Write-Output 'MATRIX DONE'
