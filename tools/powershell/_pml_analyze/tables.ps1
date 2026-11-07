param([string]$Path,[string]$Tag)
$fs=[System.IO.File]::OpenRead($Path)
$br=New-Object System.IO.BinaryReader($fs)
$len=$fs.Length
Write-Output "########## $Tag  ($Path)"

function Dump([long]$off,[int]$n,[string]$label){
  if($off -lt 0 -or $off+$n -gt $len){ Write-Output "  [$label] off 0x$($off.ToString('X')) out of range"; return }
  $fs.Position=$off
  $b=$br.ReadBytes($n)
  Write-Output ("--- $label @ 0x{0:X} ({0}) ---" -f $off)
  for($i=0;$i -lt $b.Length;$i+=32){
    $e=[Math]::Min($i+31,$b.Length-1)
    $row=$b[$i..$e]
    Write-Output ("{0:X8}  {1,-95}  {2}" -f ($off+$i),(($row|%{$_.ToString('X2')}) -join ' '),(-join($row|%{if($_ -ge 32 -and $_ -lt 127){[char]$_}else{'.'}})))
  }
}

$fs.Position=0x248
$b=$br.ReadBytes(32)
$offs=@()
0..3 | ForEach-Object { $offs += [BitConverter]::ToUInt64($b,$_*8) }
Write-Output ("table offsets: " + (($offs | ForEach-Object { "0x{0:X}" -f $_ }) -join ', '))

Dump $offs[0] 96 "table[0]"
Dump $offs[1] 96 "table[1]"
Dump $offs[2] 96 "table[2]"
Dump ($len-0x400) 0x400 "tail-0x400"

$fs.Close()
