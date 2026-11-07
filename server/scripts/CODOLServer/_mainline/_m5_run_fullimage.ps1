param(
    [int]$DumpSeconds = 22,
    [double]$DumpStep = 2.0,
    [int]$DumpDelaySeconds = 8
)
$ErrorActionPreference = 'Continue'

# This script must survive being read by a GBK-decoding PowerShell, so every
# path is built from ASCII-only fragments and the Chinese root comes from the
# process environment (also ASCII-safe via [char] codes as a fallback).
$drive = 'D:'
$rootLeaf = [string]::Join('', @(
    [char]0x4F7F, [char]0x547D, [char]0x53EC, [char]0x5524, 'OL'
))
$root = Join-Path ($drive + '\BaiduNetdiskDownload') $rootLeaf

if (-not (Test-Path -LiteralPath $root)) {
    Write-Output "ROOT_MISSING=$root"
    exit 1
}

$sandbox = Join-Path $root 'run_codol_001\sandbox_ifs1_20260923'
$exe = Join-Path $sandbox 'codoMP_client_shipRetail.exe'

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$runDir = Join-Path $root ("run_codol_001\runs\FULLIMAGE_" + $stamp)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$dumpDir = Join-Path $runDir 'full'
New-Item -ItemType Directory -Force -Path $dumpDir | Out-Null

$py = 'C:\Users\Z7-CT5N1\AppData\Local\Programs\Python\Python311\python.exe'

$scriptDir = $PSScriptRoot

Write-Output ("RUN=" + $runDir)
Write-Output ("SANDBOX_OK=" + (Test-Path -LiteralPath $sandbox))
Write-Output ("EXE_OK=" + (Test-Path -LiteralPath $exe))
Write-Output ("ADMIN=" + ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator))

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("CLEAN " + $_.Id); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

$game = Start-Process -FilePath $exe -WorkingDirectory $sandbox -PassThru
Write-Output ("GAME_PID=" + $game.Id)

Start-Sleep -Seconds $DumpDelaySeconds

$dumpOut = Join-Path $dumpDir 'image'
$dumper = Join-Path $scriptDir '_m4_full_image.py'
& $py -X utf8 -u $dumper $game.Id --out $dumpOut --seconds $DumpSeconds --step $DumpStep 2>&1 |
    Tee-Object -FilePath (Join-Path $runDir 'fullimage_stdout.txt')

Start-Sleep -Seconds 2

$shotter = Join-Path $scriptDir '_pop_desktop_shot.py'
if (Test-Path -LiteralPath $shotter) {
    & $py -X utf8 -u $shotter --out (Join-Path $runDir 'shot.png') 2>&1 |
        Tee-Object -FilePath (Join-Path $runDir 'shot_stdout.txt')
}

$alive = [bool](Get-Process -Id $game.Id -ErrorAction SilentlyContinue)
Write-Output ("GAME_ALIVE=" + $alive)

Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output ("KILL " + $_.Id); Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }
Get-Process IIPSHostApp -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }

Write-Output ("DONE=" + $runDir)
