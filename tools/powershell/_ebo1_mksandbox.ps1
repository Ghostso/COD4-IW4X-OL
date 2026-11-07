# EB1 sandbox: isolated game tree - all entries junctioned to the ORIGINAL game dir
# except IIPS\, which is a real copy carrying the disk-level Local RM proxy iips.dll.
# Originals are never modified. Usage:
#   & <this script> -Sandbox '<workspace>\工具\EB1_SANDBOX'
param([Parameter(Mandatory=$true)][string]$Sandbox)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$src = Join-Path $root 'COD OL'
$sbx = $Sandbox
New-Item -ItemType Directory -Force -Path $sbx | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $sbx 'IIPS') | Out-Null

foreach ($e in Get-ChildItem -LiteralPath $src -Force) {
    $target = Join-Path $sbx $e.Name
    if ($e.Name -eq 'IIPS') { continue }
    if (Test-Path -LiteralPath $target) { continue }
    if ($e.PSIsContainer) {
        cmd /c mklink /J "`"$target`"" "`"$($e.FullName)`"" | Out-Null
    } else {
        cmd /c mklink /H "`"$target`"" "`"$($e.FullName)`"" | Out-Null
    }
}

# IIPS: copy every file, junction every subdirectory (keeps the patched iips.dll)
$srcIIPS = Join-Path $src 'IIPS'
foreach ($e in Get-ChildItem -LiteralPath $srcIIPS -Force) {
    $target = Join-Path $sbx ('IIPS\' + $e.Name)
    if ($e.PSIsContainer) {
        if (-not (Test-Path -LiteralPath $target)) { cmd /c mklink /J "`"$target`"" "`"$($e.FullName)`"" | Out-Null }
    } else {
        if ($e.Name -eq 'iips.dll') { continue }   # keep disk proxy version
        if (-not (Test-Path -LiteralPath $target)) { Copy-Item -LiteralPath $e.FullName -Destination $target }
    }
}
Write-Output ('sandbox ready: ' + $sbx)
(Get-Item (Join-Path $sbx 'IIPS\iips.dll')).Length
(Get-FileHash (Join-Path $src 'IIPS\iips.dll') -Algorithm MD5).Hash
