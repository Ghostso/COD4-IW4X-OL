# Move memory-dump artifacts from D: to E:, leaving pointers behind.
# NOTE: no non-ASCII literals in this file - PowerShell would decode a UTF-8
# script as ANSI and mangle Chinese paths. Root is derived from the script path.
$ErrorActionPreference = 'Stop'
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path   # ...\<proj>\CODOL-LOBBY-...\RUNS
$patchDir   = Split-Path -Parent $scriptDir                     # ...\<proj>\CODOL-LOBBY-...
$root       = Split-Path -Parent $patchDir                      # ...\<proj>
$dest       = 'E:\codol_dumps'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Write-Output "root=$root"
Write-Output "dest=$dest"

$runs = Join-Path $root 'run_codol_001\runs'
$jobs = @(
  @{ Src = Join-Path $runs 'EARLIEST2_20261027_132645'; Dst = Join-Path $dest 'EARLIEST2_20261027_132645' },
  @{ Src = Join-Path $runs 'EARLIEST_20261027_123806';  Dst = Join-Path $dest 'EARLIEST_20261027_123806'  },
  @{ Src = Join-Path $runs 'FIXMC_20261027_140146';     Dst = Join-Path $dest 'FIXMC_20261027_140146'     },
  @{ Src = Join-Path $runs 'E1_20261029_103001\dump';   Dst = Join-Path $dest 'E1_20261029_103001_dump'   },
  @{ Src = Join-Path $runs 'MEMDUMP_20261027_v4';       Dst = Join-Path $dest 'MEMDUMP_20261027_v4'       }
)

foreach ($j in $jobs) {
  if (-not (Test-Path -LiteralPath $j.Src)) { Write-Output "SKIP (missing): $($j.Src)"; continue }
  Write-Output "MOVE: $($j.Src)  ->  $($j.Dst)"
  robocopy $j.Src $j.Dst /MOVE /E /NFL /NDL /NJH /NJS /R:1 /W:1 | Out-Null
  $code = $LASTEXITCODE
  Write-Output "  robocopy exit=$code"
  if ($code -lt 8) {
    $note = Join-Path (Split-Path -Parent $j.Src) ((Split-Path -Leaf $j.Src) + '_MOVED_TO_E.txt')
    Set-Content -LiteralPath $note -Encoding UTF8 -Value @(
      "moved to: $($j.Dst)",
      "by: 056 maintenance, 2026-10-29",
      "reason: D: was full (about 75 GB of full-memory dump artifacts, 2 GB per snapshot)"
    )
    Write-Output "  pointer written: $note"
  } else {
    Write-Output "  !! robocopy failed, source left in place"
  }
}

Write-Output "--- free space now ---"
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Name -in @('C','D','E') } |
  Select-Object Name, @{n='FreeGB';e={[math]::Round($_.Free/1GB,2)}} | Format-Table -AutoSize | Out-String | Write-Output
