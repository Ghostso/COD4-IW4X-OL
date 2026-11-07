$root = 'F:\桌面\ol\TESTOL 完整交付版\payload\Ayria'
$files = @(
    "$root\Injector32.exe",
    "$root\Bootstrapper32.dll",
    "$root\Bootstrapper64.dll",
    "$root\ol_room_owner.exe",
    "$root\Plugins\Localnetworking.Ayria32",
    "$root\Plugins\Platformwrapper.Ayria32",
    "$root\Plugins\Alwaysoffline.Localnet32",
    "$root\Plugins\CodolGameServer.Localnet32"
)

function R16($b, $o) { [BitConverter]::ToUInt16($b, $o) }
function R32($b, $o) { [BitConverter]::ToUInt32($b, $o) }

foreach ($f in $files) {
    if (-not (Test-Path $f)) { "MISSING: $f"; continue }
    $b = [IO.File]::ReadAllBytes($f)
    "=================================================================="
    "FILE: $($f.Substring($root.Length+1))   size=$($b.Length)"
    if ($b[0] -ne 0x4D -or $b[1] -ne 0x5A) { "  NOT MZ"; continue }
    $pe = [int](R32 $b 0x3C)
    if ($b[$pe] -ne 0x50 -or $b[$pe+1] -ne 0x45) { "  no PE sig at 0x$($pe.ToString('X'))"; continue }
    $machine = R16 $b ($pe + 4)
    $nsec = R16 $b ($pe + 6)
    $tds = R32 $b ($pe + 8)
    $pdb = R32 $b ($pe + 12)
    $optSize = R16 $b ($pe + 20)
    $chars = R16 $b ($pe + 22)
    $opt = $pe + 24
    $magic = R16 $b $opt
    $is64 = ($magic -eq 0x20B)
    $subsys = R16 $b ($opt + 68)
    if ($is64) {
        $imageBase = [BitConverter]::ToUInt64($b, $opt + 24)
        $sizeOfImage = R32 $b ($opt + 56)
        $entry = R32 $b ($opt + 16)
        $ddOff = $opt + 112
    } else {
        $imageBase = R32 $b ($opt + 28)
        $sizeOfImage = R32 $b ($opt + 56)
        $entry = R32 $b ($opt + 16)
        $ddOff = $opt + 96
    }
    $dllChar = R32 $b ($ddOff + 12 * 8)
    $expRva = R32 $b ($ddOff + 0)
    $expSize = R32 $b ($ddOff + 4)
    $machStr = switch ($machine) { 0x14c { 'x86' } 0x8664 { 'x64' } default { "0x$($machine.ToString('X'))" } }
    $ssStr = switch ($subsys) { 2 { 'GUI' } 3 { 'CUI' } default { "$subsys" } }
    "  machine=$machStr  magic=0x$($magic.ToString('X'))  sections=$nsec  optHdr=$optSize"
    "  TimeDateStamp=$tds  ($([DateTimeOffset]::FromUnixTimeSeconds($tds).UtcDateTime.ToString('yyyy-MM-dd HH:mm:ss')) UTC)"
    "  ImageBase=0x$($imageBase.ToString('X'))  SizeOfImage=0x$($sizeOfImage.ToString('X'))  EntryPoint=0x$($entry.ToString('X'))"
    "  Subsystem=$ssStr  Characteristics=0x$($chars.ToString('X'))  DllCharacteristics=0x$($dllChar.ToString('X'))"
    "  Export dir: RVA=0x$($expRva.ToString('X')) size=$expSize"
    "  --- sections ---"
    $sh = $pe + 24 + $optSize
    for ($i = 0; $i -lt $nsec; $i++) {
        $o = $sh + $i * 40
        $nm = [Text.Encoding]::ASCII.GetString($b, $o, 8).TrimEnd([char]0)
        $vs = R32 $b ($o + 8); $va = R32 $b ($o + 12)
        $rs = R32 $b ($o + 16); $pr = R32 $b ($o + 20)
        $sc = R32 $b ($o + 36)
        "    {0,-9} VA=0x{1:X8} vsize={2,-9} raw=0x{3:X8} rsize={4,-9} chars=0x{5:X8}" -f $nm, $va, $vs, $pr, $rs, $sc
    }
    # export names
    if ($expRva -ne 0 -and $expSize -ne 0) {
        $eo = $null
        for ($i = 0; $i -lt $nsec; $i++) {
            $o = $sh + $i * 40
            $vs = R32 $b ($o + 8); $va = R32 $b ($o + 12); $pr = R32 $b ($o + 20)
            if ($expRva -ge $va -and $expRva -lt ($va + $vs)) { $eo = $pr + ($expRva - $va); break }
        }
        if ($eo -ne $null) {
            $nfun = R32 $b ($eo + 20)
            $nname = R32 $b ($eo + 24)
            $anames = R32 $b ($eo + 32)
            $anOff = $null
            for ($i = 0; $i -lt $nsec; $i++) {
                $o = $sh + $i * 40
                $vs = R32 $b ($o + 8); $va = R32 $b ($o + 12); $pr = R32 $b ($o + 20)
                if ($anames -ge $va -and $anames -lt ($va + $vs)) { $anOff = $pr + ($anames - $va); break }
            }
            "  --- exports: numFunctions=$nfun numNames=$nname ---"
            $names = @()
            for ($i = 0; $i -lt [Math]::Min($nname, 400); $i++) {
                $nr = R32 $b ($anOff + $i * 4)
                $no = $null
                for ($j = 0; $j -lt $nsec; $j++) {
                    $o = $sh + $j * 40
                    $vs = R32 $b ($o + 8); $va = R32 $b ($o + 12); $pr = R32 $b ($o + 20)
                    if ($nr -ge $va -and $nr -lt ($va + $vs)) { $no = $pr + ($nr - $va); break }
                }
                if ($no -ne $null) {
                    $end = $no
                    while ($end -lt $b.Length -and $b[$end] -ne 0) { $end++ }
                    $names += [Text.Encoding]::ASCII.GetString($b, $no, $end - $no)
                }
            }
            $names -join ', '
        }
    }
    ""
}
