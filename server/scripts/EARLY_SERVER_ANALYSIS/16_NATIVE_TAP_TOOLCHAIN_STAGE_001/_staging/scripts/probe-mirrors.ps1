$ErrorActionPreference = 'Continue'
$path = 'project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z'
$mirrors = @('netcologne','gigenet','versaweb','iweb','phoenixnap','freefr','astuteinternet','cytranet')
$outdir = Join-Path $env:TEMP 'spd-probe'
New-Item -ItemType Directory -Force -Path $outdir | Out-Null
foreach ($m in $mirrors) {
  $u = "https://$m.dl.sourceforge.net/$path"
  $t = Join-Path $outdir "$m.bin"
  $sw = [Diagnostics.Stopwatch]::StartNew()
  & curl.exe --silent --show-error --location --max-time 15 --range 0-2097151 --output $t $u 2>$null
  $code = $LASTEXITCODE
  $sw.Stop()
  $len = 0
  if (Test-Path $t) { $len = (Get-Item $t).Length }
  "{0,-16} exit={1} bytes={2} secs={3} rate={4}KB/s" -f $m, $code, $len, [math]::Round($sw.Elapsed.TotalSeconds,1), [math]::Round($len / [math]::Max($sw.Elapsed.TotalSeconds,0.1) / 1KB, 1)
}
