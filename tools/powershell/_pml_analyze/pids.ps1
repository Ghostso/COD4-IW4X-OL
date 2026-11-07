param([string]$Path,[string]$Tag)
$fs=[System.IO.File]::OpenRead($Path)
$len=$fs.Length
$buf=New-Object byte[] (4MB)

# Scan whole file for pattern: <u32 pid> <u32 0x0C> <utf16 string>  == "@ pid (4) 0C 00 00 00 <utf16 name> 00 00"
# We'll detect: bytes: XX 00 00 00 0C 00 00 00  then UTF16 digit chars then 00 00
$results=@()
$pos=0
$carry=New-Object byte[] 0
$pidPattern=[byte[]](0x0C,0x00,0x00,0x00)
while(($read=$fs.Read($buf,0,$buf.Length)) -gt 0){
  $seg=New-Object byte[] ($carry.Length+$read)
  [Array]::Copy($carry,0,$seg,0,$carry.Length)
  [Array]::Copy($buf,0,$seg,$carry.Length,$read)
  $segStart=$pos-$carry.Length
  for($i=0;$i -le $seg.Length-12;$i++){
    if($seg[$i+4] -eq 0x0C -and $seg[$i+5] -eq 0 -and $seg[$i+6] -eq 0 -and $seg[$i+7] -eq 0){
      # preceding u32 pid
      $pidv=[BitConverter]::ToUInt32($seg,$i)
      if($pidv -lt 100 -or $pidv -gt 4000000){continue}
      # following should be UTF16 digits
      $j=$i+8
      $s=New-Object System.Text.StringBuilder
      while($j+1 -lt $seg.Length){
        $c=[BitConverter]::ToUInt16($seg,$j)
        if($c -eq 0){break}
        if($c -lt 0x30 -or $c -gt 0x39){ $s=New-Object System.Text.StringBuilder; break }
        [void]$s.Append([char]$c); $j+=2
      }
      if($s.Length -gt 0){
        $results += [pscustomobject]@{Off=($segStart+$i); PID=$pidv; Name=$s.ToString()}
      }
    }
  }
  $carryLen=[Math]::Min(16,$seg.Length)
  $carry=New-Object byte[] $carryLen
  [Array]::Copy($seg,$seg.Length-$carryLen,$carry,0,$carryLen)
  $pos+=$read
}
$fs.Close()
Write-Output "### $Tag : $($results.Count) PID name records found"
Write-Output ("first record offset: 0x{0:X}" -f $results[0].Off)
Write-Output ("last  record offset: 0x{0:X}" -f $results[-1].Off)
Write-Output "--- FIRST 40 ---"
$results | Select-Object -First 40 | ForEach-Object { Write-Output ("  0x{0:X8}  {1,6}  {2}" -f $_.Off,$_.PID,$_.Name) }
Write-Output "--- LAST 40 ---"
$results | Select-Object -Last 40 | ForEach-Object { Write-Output ("  0x{0:X8}  {1,6}  {2}" -f $_.Off,$_.PID,$_.Name) }
$results | Export-Csv -LiteralPath ("D:\BaiduNetdiskDownload\使命召唤OL\_pml_analyze\pids_$Tag.csv") -NoTypeInformation -Encoding UTF8
