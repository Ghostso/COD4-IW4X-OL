param([string]$Path,[string]$Tag)
$fs=[System.IO.File]::OpenRead($Path)
$br=New-Object System.IO.BinaryReader($fs)
$len=$fs.Length
Write-Output "########## $Tag"

function HexRow([long]$off,[byte[]]$b){
  for($i=0;$i -lt $b.Length;$i+=32){
    $e=[Math]::Min($i+31,$b.Length-1)
    $row=$b[$i..$e]
    Write-Output ("{0:X8}  {1,-95}  {2}" -f ($off+$i),(($row|%{$_.ToString('X2')}) -join ' '),(-join($row|%{if($_ -ge 32 -and $_ -lt 127){[char]$_}else{'.'}})))
  }
}
function Dump([long]$off,[int]$n){ if($off+$n -gt $len){return}; $fs.Position=$off; HexRow $off ($br.ReadBytes($n)) }

# last 0x60 bytes
Write-Output "--- LAST 0x60 bytes ---"
Dump ($len-0x60) 0x60

# find where the final entry record starts: it is preceded by 01 EB 01 00 0C 00 00 00 UTF16 "60161"
Write-Output ""
Write-Output "--- 0x120 bytes ending at file end ---"
Dump ($len-0x120) 0x120

# search for the ASCII/UTF16 marker of "60161" and print surrounding
$needle = [System.Text.Encoding]::Unicode.GetBytes("60161")
$searchStart = [Math]::Max(0,$len-0x40000)
$fs.Position=$searchStart
$buf=$br.ReadBytes([int]($len-$searchStart))
$hits=@()
for($i=0;$i -le $buf.Length-$needle.Length;$i++){
  $ok=$true
  for($j=0;$j -lt $needle.Length;$j++){ if($buf[$i+$j] -ne $needle[$j]){$ok=$false;break} }
  if($ok){ $hits += ($searchStart+$i) }
}
Write-Output ""
Write-Output ("hits for UTF16 '60161' (last 0x40000): " + (($hits|%{"0x{0:X}" -f $_}) -join ', '))

$fs.Close()
