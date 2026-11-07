# sh1x server hang watchdog.
#
# Polls the native server's rcon "status" on the game port. When it stops
# answering for `MissLimit` consecutive polls while the process is still alive,
# captures every thread's stack with cdb (non-invasive attach, no process
# change) into bin/home-crash/hang-stack-<timestamp>-pid<pid>.txt, once per
# hang. Frames print as <module>+0xRVA; resolve against the build with
# i686-w64-mingw32-nm -n (image base 0x400000) as docs describe for crashes.
#
#   powershell -File tools\codol_hang_watch.ps1 [-Port 17733] [-Interval 10]
param(
    [int]$Port = 17733,
    [int]$Interval = 10,
    [int]$MissLimit = 3,
    [string]$RconFile = "D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13\CODOL\1.1.1.13_server\alpha0022\native_server_rcon.txt",
    [string]$OutDir = (Join-Path $PSScriptRoot "..\bin\home-crash"),
    [string]$Cdb = "C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe"
)
$ErrorActionPreference = "Continue"
$pw = (Get-Content -LiteralPath $RconFile -Raw).Trim()
$payload = [byte[]](0xff,0xff,0xff,0xff) + [System.Text.Encoding]::ASCII.GetBytes("rcon $pw status")
New-Item -ItemType Directory -Force $OutDir | Out-Null
$misses = 0; $captured = $false
function Get-ServerPid {
    $line = netstat -ano -p udp | Select-String ":$Port\s" | Select-Object -First 1
    if ($line) { return [int]($line.Line -split "\s+")[-1] }
    return 0
}
while ($true) {
    $ok = $false
    try {
        $udp = New-Object System.Net.Sockets.UdpClient
        $udp.Client.ReceiveTimeout = 3000
        $udp.Connect("127.0.0.1", $Port)
        [void]$udp.Send($payload, $payload.Length)
        $ep = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any, 0)
        [void]$udp.Receive([ref]$ep)
        $ok = $true
    } catch { } finally { if ($udp) { $udp.Close() } }
    if ($ok) { $misses = 0; $captured = $false }
    else {
        $misses++
        $serverPid = Get-ServerPid
        if ($misses -ge $MissLimit -and -not $captured -and $serverPid -gt 0) {
            $stamp = Get-Date -Format "yyyyMMdd-HHmm"
            $out = Join-Path $OutDir "hang-stack-$stamp-pid$serverPid.txt"
            "hang watchdog: no rcon reply for $misses polls, capturing pid $serverPid -> $out"
            & $Cdb -pv -p $serverPid -c "~*k 40; qd" 2>&1 | Out-File -Encoding ascii $out
            $captured = $true
        }
    }
    Start-Sleep -Seconds $Interval
}
