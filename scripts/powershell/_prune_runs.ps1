$root = (Resolve-Path -LiteralPath "D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs").Path
$cutoff = [datetime]"2026-10-04"
$targets = @(Get-ChildItem -LiteralPath $root -Directory | Where-Object { $_.LastWriteTime -lt $cutoff })
Write-Output ("root=" + $root)
Write-Output ("count=" + $targets.Count)
foreach ($t in $targets) {
    $full = [System.IO.Path]::GetFullPath($t.FullName)
    if (-not $full.StartsWith($root + "\", [StringComparison]::OrdinalIgnoreCase)) {
        Write-Output ("SKIP_OUTSIDE " + $full)
        continue
    }
    if (Test-Path -LiteralPath $full) {
        [System.IO.Directory]::Delete($full, $true)
    }
}
Write-Output ("remaining=" + (Get-ChildItem -LiteralPath $root -Directory).Count)
$d = Get-PSDrive D
Write-Output ("freeGB=" + [math]::Round($d.Free/1GB, 2))