# RESTORE-IIPS-CONTRACT-002 - serial matrix runner.
#
# Runs the remaining matrix cells with the fixed AboProbe002 observer.
# The observer must run outside the Codex sandbox: its restricted token
# (SeChangeNotifyPrivilege only) makes the client's pre-gate abort with
# 警告码(0; 20002; 86) before IIPS is ever reached.
param(
    [int]$Duration = 60,
    [int]$IntervalMs = 15
)
$ErrorActionPreference = 'Stop'
$root = 'D:\BaiduNetdiskDownload\使命召唤OL'
$exe  = Join-Path $root 'restore_iips_contract_002\observer002\out\AboProbe002.exe'
$sbxRoot = Join-Path $root 'restore_iips_contract_002\sandbox'

$cells = @{
    orig_noifs = @{ provider = 'original';   ifs = 'missing'; sandbox = $null }
    orig_ifs   = @{ provider = 'original';   ifs = 'present'; sandbox = (Join-Path $sbxRoot 'orig_ifs') }
    lrm_noifs  = @{ provider = 'localrm_v3'; ifs = 'missing'; sandbox = (Join-Path $sbxRoot 'lrm_noifs') }
    lrm_ifs    = @{ provider = 'localrm_v3'; ifs = 'present'; sandbox = (Join-Path $sbxRoot 'lrm_ifs') }
}

$plan = @(
    @{ tag = 'B2'; cell = 'orig_ifs' },
    @{ tag = 'B3'; cell = 'orig_ifs' },
    @{ tag = 'A2'; cell = 'orig_noifs' },
    @{ tag = 'C1'; cell = 'lrm_noifs' },
    @{ tag = 'C2'; cell = 'lrm_noifs' },
    @{ tag = 'D1'; cell = 'lrm_ifs' },
    @{ tag = 'D2'; cell = 'lrm_ifs' }
)

foreach ($p in $plan) {
    $c = $cells[$p.cell]
    $args = @('--tag', $p.tag, '--cell', $p.cell, '--provider', $c.provider,
              '--ifs', $c.ifs, '--duration', $Duration, '--interval-ms', $IntervalMs)
    if ($c.sandbox) { $args += @('--sandbox', $c.sandbox) }
    Write-Output ("===== RUN " + $p.tag + " cell=" + $p.cell + " =====")
    & $exe @args | Select-Object -Last 2
    Write-Output ("===== DONE " + $p.tag + " exit=" + $LASTEXITCODE + " =====")
    Start-Sleep -Seconds 3
}
Write-Output "MATRIX_COMPLETE"
