$root = 'F:\桌面\ol\TESTOL 完整交付版'
$mf = Join-Path $root 'MANIFEST.sha256'
$lines = [IO.File]::ReadAllLines($mf)

$ok = 0; $bad = 0; $miss = 0; $sizemis = 0; $fmt = 0
$badList = New-Object System.Collections.ArrayList
$missList = New-Object System.Collections.ArrayList
$sizeList = New-Object System.Collections.ArrayList

foreach ($ln in $lines) {
    if ($ln.Trim() -eq '') { continue }
    $m = [regex]::Match($ln, '^([0-9A-Fa-f]{64})\s\s(.+?)\s\s(\d+)$')
    if (-not $m.Success) { $fmt++; continue }
    $h = $m.Groups[1].Value.ToUpper()
    $rel = $m.Groups[2].Value
    $sz = [int64]$m.Groups[3].Value
    $p = Join-Path $root ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $p)) { $miss++; [void]$missList.Add($rel); continue }
    $fi = Get-Item -LiteralPath $p
    if ($fi.Length -ne $sz) { $sizemis++; [void]$sizeList.Add("$rel  manifest=$sz actual=$($fi.Length)") }
    $ah = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
    if ($ah -eq $h) { $ok++ } else { $bad++; [void]$badList.Add("$rel  manifest=$($h.Substring(0,16)) actual=$($ah.Substring(0,16))") }
}

Write-Output "===== MANIFEST VERIFY ====="
Write-Output ("  ok          = " + $ok)
Write-Output ("  hash-bad    = " + $bad)
Write-Output ("  size-bad    = " + $sizemis)
Write-Output ("  missing     = " + $miss)
Write-Output ("  bad-format  = " + $fmt)
Write-Output ("  total       = " + ($ok + $bad + $sizemis + $miss + $fmt))
if ($missList.Count -gt 0) { Write-Output "--- MISSING ---"; $missList | ForEach-Object { Write-Output ("  " + $_) } }
if ($badList.Count -gt 0) { Write-Output "--- HASH-BAD ---"; $badList | ForEach-Object { Write-Output ("  " + $_) } }
if ($sizeList.Count -gt 0) { Write-Output "--- SIZE-BAD ---"; $sizeList | ForEach-Object { Write-Output ("  " + $_) } }
