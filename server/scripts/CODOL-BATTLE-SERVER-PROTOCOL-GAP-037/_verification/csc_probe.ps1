$csc='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$args=@('/nologo','/target:exe','/out:D:\BaiduNetdiskDownload\}ì$OL\CODOL-BATTLE-SERVER-PROTOCOL-GAP-037\_verification\csc_probe.exe','D:\BaiduNetdiskDownload\}ì$OL\CODOL-BATTLE-SERVER-PROTOCOL-GAP-037\_verification\csc_probe.cs')
Write-Host ('ARGS=' + ($args -join '|'))
$out = & $csc @args 2>&1
$code = $LASTEXITCODE
Write-Host ('OUT=' + ($out -join ' / '))
Write-Host ('CODE=' + $code)
Write-Host ('Q=' + $?)
