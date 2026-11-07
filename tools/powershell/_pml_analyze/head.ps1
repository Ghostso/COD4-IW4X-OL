param([string]$Path,[string]$Tag)
$fs=[System.IO.File]::OpenRead($Path)
$br=New-Object System.IO.BinaryReader($fs)
$len=$fs.Length
Write-Output "=== $Tag  $Path"
Write-Output ("len = $len  (0x{0:X})" -f $len)

$fs.Position=0
$b=$br.ReadBytes(0x40)
Write-Output ("magic      : " + [System.Text.Encoding]::ASCII.GetString($b,0,4))
Write-Output ("u32 @0x04  : " + [BitConverter]::ToUInt32($b,4))
Write-Output ("u32 @0x08  : " + [BitConverter]::ToUInt32($b,8))

$s=New-Object System.Text.StringBuilder
for($i=12;$i -lt 0x28;$i+=2){
  $c=[BitConverter]::ToUInt16($b,$i)
  if($c -eq 0){break}
  [void]$s.Append([char]$c)
}
Write-Output ("hostname   : '" + $s.ToString() + "'")

$fs.Position=0x28
$b2=$br.ReadBytes(0xE0)
$s2=New-Object System.Text.StringBuilder
$started=$false
for($i=0;$i -lt 0xE0;$i+=2){
  $c=[BitConverter]::ToUInt16($b2,$i)
  if($c -eq 0){ if($started){break} else {continue} }
  $started=$true
  [void]$s2.Append([char]$c)
}
Write-Output ("path       : '" + $s2.ToString() + "'")

$fs.Position=0x230
$b3=$br.ReadBytes(0x60)
Write-Output ("@0x230     : " + (($b3|%{$_.ToString('X2')}) -join ' '))
Write-Output ("  u32@0x230= " + [BitConverter]::ToUInt32($b3,0))
Write-Output ("  u32@0x234= " + [BitConverter]::ToUInt32($b3,4))
Write-Output ("  q@0x238   = " + [BitConverter]::ToUInt64($b3,8))
Write-Output ("  q@0x240   = " + [BitConverter]::ToUInt64($b3,16))
Write-Output ("  q@0x248   = " + [BitConverter]::ToUInt64($b3,24))
Write-Output ("  q@0x250   = " + [BitConverter]::ToUInt64($b3,32))
Write-Output ("  q@0x258   = " + [BitConverter]::ToUInt64($b3,40))
Write-Output ("  u32@0x260= " + [BitConverter]::ToUInt32($b3,0x30))
Write-Output ("  u32@0x264= " + [BitConverter]::ToUInt32($b3,0x34))
Write-Output ("  u64@0x268= " + [BitConverter]::ToUInt64($b3,0x38))
Write-Output ("  u32@0x270= " + [BitConverter]::ToUInt32($b3,0x40))
Write-Output ("  u32@0x274= " + [BitConverter]::ToUInt32($b3,0x44))
Write-Output ("  u32@0x278= " + [BitConverter]::ToUInt32($b3,0x48))
Write-Output ("  u64@0x280= " + [BitConverter]::ToUInt64($b3,0x50))

$fs.Close()
