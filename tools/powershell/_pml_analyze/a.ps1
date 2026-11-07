param([string]$Path,[string]$Tag)
$fs=[System.IO.File]::OpenRead($Path)
$len=$fs.Length
$br=New-Object System.IO.BinaryReader($fs)
function H([int]$off,[int]$n){ $fs.Position=$off; $b=$br.ReadBytes($n); ($b|%{$_.ToString('X2')}) -join ' ' }
Write-Output "=== $Tag  $Path  len=$len (0x$($len.ToString('X'))) ==="
# header
$fs.Position=0; $b=$br.ReadBytes(0x40)
Write-Output ("magic=" + ([System.Text.Encoding]::ASCII.GetString($b,0,4)))
Write-Output ("u32@4=" + [BitConverter]::ToUInt32($b,4) + "  u32@8=" + [BitConverter]::ToUInt32($b,8))
$s=New-Object System.Text.StringBuilder
for($i=12;$i -lt 40;$i+=2){ $c=[BitConverter]::ToUInt16($b,$i); if($c -eq 0){break}; [void]$s.Append([char]$c) }
Write-Output ("name='" + $s.ToString() + "'")
$s2=New-Object System.Text.StringBuilder
for($i=0x28;$i -lt 0x110;$i+=2){ $c=[BitConverter]::ToUInt16($b2=@(),0) }
$fs.Position=0x28; $b=$br.ReadBytes(0xE8)
$s2=New-Object System.Text.StringBuilder
for($i=0;$i -lt 0xE8;$i+=2){ $c=[BitConverter]::ToUInt16($b,$i); if($c -eq 0){ if($s2.Length -gt 0){break} else {continue} }; if($c -ge 32 -and $c -lt 0x10000){[void]$s2.Append([char]$c)} }
Write-Output ("path='" + $s2.ToString() + "'")
Write-Output ("@0x234: " + (H 0x234 64))
Write-Output ("@0x240: " + (H 0x240 64))
$fs.Close()
