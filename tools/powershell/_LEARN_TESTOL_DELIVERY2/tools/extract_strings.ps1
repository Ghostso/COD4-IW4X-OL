param([string]$File, [string]$Out, [int]$MinLen = 6)
$b = [IO.File]::ReadAllBytes($File)
$sb = New-Object System.Text.StringBuilder
$cur = New-Object System.Text.StringBuilder
$list = New-Object System.Collections.Generic.List[string]
# ASCII strings
for ($i = 0; $i -lt $b.Length; $i++) {
    $c = $b[$i]
    if ($c -ge 32 -and $c -le 126) { [void]$cur.Append([char]$c) }
    else {
        if ($cur.Length -ge $MinLen) { $list.Add($cur.ToString()) }
        [void]$cur.Clear()
    }
}
if ($cur.Length -ge $MinLen) { $list.Add($cur.ToString()) }
$list | Sort-Object -Unique | Set-Content -LiteralPath $Out -Encoding UTF8
"ASCII strings (>= $MinLen): $($list.Count) total, $(( $list | Sort-Object -Unique ).Count) unique -> $Out"
