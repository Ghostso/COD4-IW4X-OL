function Format-Pl($c) {
    $gts = ($c.gametypes.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Key)x$($_.Value)" }) -join '+'
    "PL {0,-4} line{1,-5} cat={2,-3} ord={3,-3} maps={4,-3} rules={5,-3} bv='{6}' flags=[{7}] gt={8} | EN={9} | CN={10}" -f `
        $c.id, $c.line, $c.cat, $c.order, $c.maps, $c.rules, $c.bv, ($c.flags -join ','), $gts, $c.en, $c.cn
}

$f = 'D:\BaiduNetdiskDownload\使命召唤OL\_LEARN_TESTOL_DELIVERY2\decoded\mp_playlists_shipRetail_release.utf8.txt'
$l = [IO.File]::ReadAllLines($f)
$out = New-Object System.Collections.Generic.List[string]

$out.Add('=== PLAYLIST INDEX ===')
$cur = $null
for ($i = 0; $i -lt $l.Count; $i++) {
    $line = $l[$i]
    if ($line -match '^playlist\s+(\d+)\s*$') {
        if ($cur) { $out.Add((Format-Pl $cur)) }
        $cur = [ordered]@{ id = $matches[1]; line = $i + 1; en = ''; cn = ''; cat = ''; order = ''; gametypes = @{}; maps = 0; flags = @(); rules = 0; bv = '' }
    }
    elseif ($cur) {
        if ($line -match '^name english\s+"(.*)"\s*$') { $cur.en = $matches[1] }
        elseif ($line -match '^name chinese\s+"(.*)"\s*$') { $cur.cn = $matches[1] }
        elseif ($line -match '^category\s+(\d+)') { $cur.cat = $matches[1] }
        elseif ($line -match '^displayorder\s+(\d+)') { $cur.order = $matches[1] }
        elseif ($line -match '^buildversion\s*(.*)$') { $cur.bv = $matches[1].Trim() }
        elseif ($line -match '^\s*(ranked|teambased|combattraining|onboardbonus|noteamsplitting|offline)\s*$') { $cur.flags += $matches[1] }
        elseif ($line -match '^rule\s+') { $cur.rules++ }
        elseif ($line -match '^\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*,\s*(-?[\d.]+)') {
            $cur.maps++
            $gt = $matches[2]
            if (-not $cur.gametypes.ContainsKey($gt)) { $cur.gametypes[$gt] = 0 }
            $cur.gametypes[$gt]++
        }
    }
}
if ($cur) { $out.Add((Format-Pl $cur)) }

$out.Add('')
$out.Add('=== GAMETYPE USAGE ACROSS PLAYLISTS ===')
$gtCount = @{}
$mapCount = @{}
foreach ($line in $l) {
    if ($line -match '^\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*,\s*(-?[\d.]+)') {
        $m = $matches[1]; $g = $matches[2]
        if (-not $gtCount.ContainsKey($g)) { $gtCount[$g] = 0 }
        $gtCount[$g]++
        if (-not $mapCount.ContainsKey($m)) { $mapCount[$m] = 0 }
        $mapCount[$m]++
    }
}
foreach ($k in ($gtCount.Keys | Sort-Object)) { $out.Add(("gt {0,-10} {1}" -f $k, $gtCount[$k])) }
$out.Add("distinct maps used: $($mapCount.Count)")
$out.Add('=== MAP USAGE ===')
foreach ($k in ($mapCount.Keys | Sort-Object { -$mapCount[$_] })) { $out.Add(("map {0,-46} {1}" -f $k, $mapCount[$k])) }

$dst = 'D:\BaiduNetdiskDownload\使命召唤OL\_LEARN_TESTOL_DELIVERY2\decoded\playlist-index.txt'
[IO.File]::WriteAllLines($dst, $out, (New-Object Text.UTF8Encoding($false)))
"wrote $($out.Count) lines to $dst"
