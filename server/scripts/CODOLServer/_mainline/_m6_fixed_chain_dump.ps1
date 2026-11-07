param(
    [int]$ChainSeconds = 26,
    [int]$DumpSeconds = 24,
    [double]$DumpStep = 2.0
)
$ErrorActionPreference = 'Continue'

$drive = 'D:'
$rootLeaf = [string]::Join('', @(
    [char]0x4F7F, [char]0x547D, [char]0x53EC, [char]0x5524, 'OL'
))
$root = Join-Path ($drive + '\BaiduNetdiskDownload') $rootLeaf

$runBase = Join-Path $root 'run_codol_001'
$sandbox = Join-Path $runBase 'sandbox_ifs1_20260923'
$chain = Join-Path $runBase 'capture_elevated_network.ps1'

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$runDir = Join-Path $root ("run_codol_001\runs\CHAINIMAGE_" + $stamp)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$dumpDir = Join-Path $runDir 'full'
New-Item -ItemType Directory -Force -Path $dumpDir | Out-Null

$py = 'C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe'
$scriptDir = $PSScriptRoot

Write-Output ("RUN=" + $runDir)
Write-Output ("ADMIN=" + ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator))

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 1) run the fixed chain in the background so it owns the TCLS handoff
$chainArgs = @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass',
    '-File', $chain,
    '-DurationSeconds', "$ChainSeconds"
)
$chainProc = Start-Process -FilePath 'powershell.exe' -ArgumentList $chainArgs `
    -WorkingDirectory $runBase -WindowStyle Hidden -PassThru
Write-Output ("CHAIN_PID=" + $chainProc.Id)

# 2) hunt for the game process and dump it as soon as it appears
$armed = $false
$deadline = (Get-Date).AddSeconds($ChainSeconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    $g = Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
        Sort-Object StartTime -Descending | Select-Object -First 1
    if (-not $g) { continue }
    Write-Output ("GAME_PID=" + $g.Id + "  t=" + (Get-Date -Format 'HH:mm:ss.fff'))

    $dumpOut = Join-Path $dumpDir ('image_' + $g.Id)
    & $py -X utf8 -u (Join-Path $scriptDir '_m4_full_image.py') $g.Id `
        --out $dumpOut --seconds $DumpSeconds --step $DumpStep 2>&1 |
        Tee-Object -FilePath (Join-Path $runDir 'fullimage_stdout.txt')

    $armed = $true
    break
}

if (-not $armed) {
    Write-Output 'GAME_NEVER_APPEARED'
}

try { $chainProc.WaitForExit(8000) } catch { }
Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }

Write-Output ("DONE=" + $runDir)
