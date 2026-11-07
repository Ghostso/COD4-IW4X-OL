param([string]$Root,[string]$Pattern)
$rx=[regex]$Pattern
Get-ChildItem -LiteralPath $Root -Recurse -File -Include *.c,*.h |
  ForEach-Object {
    $p=$_.FullName
    $ln=0
    foreach($line in [System.IO.File]::ReadAllLines($p)){
      $ln++
      if($rx.IsMatch($line)){ '{0}:{1}: {2}' -f $p,$ln,$line.Trim() }
    }
  }
