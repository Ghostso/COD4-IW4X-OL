param([string]$tag, [int]$duration, [string]$mode, [switch]$clickok, [string]$gamedir = '')
$ErrorActionPreference = 'SilentlyContinue'
# kill leftover game instances from previous runs (observer orphans; death can lag)
Get-Process | Where-Object { $_.ProcessName -match 'codoMP' } | Stop-Process -Force
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 2
    if (-not (Get-Process | Where-Object { $_.ProcessName -match 'codoMP' })) { break }
}
$exe = Join-Path $PSScriptRoot 'bin\Release\net8.0\EBO1.exe'
$argstr = "--duration $duration --mode $mode --tag $tag"
if ($clickok) { $argstr += ' --clickok' }
if ($gamedir -ne '') { $argstr += " --gamedir `"$gamedir`"" }
$p = Start-Process -FilePath $exe -ArgumentList $argstr -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot "out\$tag`_console.txt") -RedirectStandardError (Join-Path $PSScriptRoot "out\$tag`_console_err.txt")
$null = $p.WaitForExit(($duration + 25) * 1000)
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
Get-Process | Where-Object { $_.ProcessName -match 'codoMP' } | Stop-Process -Force
Write-Output "RUN $tag done"
