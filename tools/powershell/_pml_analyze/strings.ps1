param([string]$Path,[string]$Tag,[int]$WindowBytes=65536)
$fs=[System.IO.File]::OpenRead($Path)
$len=$fs.Length
$start=[Math]::Max(0,$len-$WindowBytes)
$fs.Position=$start
$b=New-Object byte[] ($len-$start)
[void]$fs.Read($b,0,$b.Length)
$fs.Close()

$sb=New-Object System.Text.StringBuilder
$rows=@()
$cur=New-Object System.Text.StringBuilder
$curOff=0
for($i=0;$i+1 -lt $b.Length;$i+=2){
  $c=[BitConverter]::ToUInt16($b,$i)
  $keep = ($c -ge 0x20 -and $c -lt 0x7F) -or ($c -ge 0x4E00 -and $c -le 0x9FFF) -or ($c -ge 0x3000 -and $c -le 0x30FF) -or ($c -ge 0xFF00 -and $c -le 0xFFEF)
  if($keep){
    if($cur.Length -eq 0){$curOff=$start+$i}
    [void]$cur.Append([char]$c)
  } else {
    if($cur.Length -ge 4){ $rows += ("0x{0:X8}  {1}" -f $curOff,$cur.ToString()) }
    $cur=New-Object System.Text.StringBuilder
  }
}
if($cur.Length -ge 4){ $rows += ("0x{0:X8}  {1}" -f $curOff,$cur.ToString()) }
Write-Output "=== $Tag : $($rows.Count) strings in last $WindowBytes bytes ==="
$rows | Select-Object -First 250 | ForEach-Object { Write-Output $_ }
