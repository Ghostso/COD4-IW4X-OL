param([int]$Seconds = 600)
$ErrorActionPreference = "Stop"
$Chain = Split-Path -Parent $PSScriptRoot
python -X utf8 (Join-Path $Chain "scripts\frozen_entry.py") $Seconds
