param([string]$Path,[string]$Tag)
$fs=[System.IO.File]::OpenRead($Path)
$len=$fs.Length
$bufSize=8MB
$needles=@(
  @{N="Sandbox"; B=[System.Text.Encoding]::Unicode.GetBytes("Sandbox")},
  @{N="WEGAME"; B=[System.Text.Encoding]::Unicode.GetBytes("WEGAME")},
  @{N="M7-E8S6"; B=[System.Text.Encoding]::Unicode.GetBytes("M7-E8S6")},
  @{N="CallOfDuty"; B=[System.Text.Encoding]::Unicode.GetBytes("CallOfDuty")},
  @{N="Tencent"; B=[System.Text.Encoding]::Unicode.GetBytes("Tencent")},
  @{N="SandboxASCII"; B=[System.Text.Encoding]::ASCII.GetBytes("Sandbox")},
  @{N="WEGAMEASCII"; B=[System.Text.Encoding]::ASCII.GetBytes("WEGAME")}
)
$counts=@{}; $first=@{}
foreach($n in $needles){ $counts[$n.N]=0; $first[$n.N]=-1 }
$pos=0
$buf=New-Object byte[] $bufSize
$overlap=256
$tail=New-Object byte[] 0
while(($read=$fs.Read($buf,0,$bufSize)) -gt 0){
  $seg=New-Object byte[] ($tail.Length+$read)
  [Array]::Copy($tail,0,$seg,0,$tail.Length)
  [Array]::Copy($buf,0,$seg,$tail.Length,$read)
  $segStart=$pos-$tail.Length
  foreach($n in $needles){
    $nd=$n.B
    for($i=0;$i -le $seg.Length-$nd.Length;$i++){
      $ok=$true
      for($j=0;$j -lt $nd.Length;$j++){ if($seg[$i+$j] -ne $nd[$j]){$ok=$false;break} }
      if($ok){
        $counts[$n.N]++
        if($first[$n.N] -lt 0){ $first[$n.N]=$segStart+$i }
      }
    }
  }
  $tl=[Math]::Min($overlap,$seg.Length)
  $tail=New-Object byte[] $tl
  [Array]::Copy($seg,$seg.Length-$tl,$tail,0,$tl)
  $pos+=$read
}
$fs.Close()
Write-Host "===== $Tag ====="
foreach($n in $needles){ if($counts[$n.N] -gt 0){ Write-Host ("{0,-14} count={1,-6} first=0x{2:X}" -f $n.N,$counts[$n.N],$first[$n.N]) } else { Write-Host ("{0,-14} count=0" -f $n.N) } }
