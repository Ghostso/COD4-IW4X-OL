# Isolated sh1x server probe: boots a private server, runs rcon commands,
# copies its log out, and stops it. Never touches the live server (udp/17733).
#
#   powershell -File tools\codol_probe.ps1 -Port 17741 -Name w1 -Scripts <rawfiles root>
#       -Map zm_prototype_sh -Zone zm -Gametype zm -Boot 100 -Tail 20
#       -Commands 'set scr_codol_equiptest "addbots 2"','sleep 15','...'
#
# -Commands: each entry is an rcon command, or "sleep <seconds>".
# The log lands in -Out (default: $env:TEMP\codol-probe-<Name>.log).
# Bot waypoints are copied into the private home so MP bots can spawn.
param(
    [Parameter(Mandatory=$true)][int]$Port,
    [Parameter(Mandatory=$true)][string]$Name,
    [string]$Scripts = "$PSScriptRoot\..\bin\home\codol_rawfiles",
    [string]$Exe = "$PSScriptRoot\..\bin\codol_dedrun.exe",
    [string[]]$Commands = @(),
    [string]$Map = "mp_rust",
    [string]$Zone = "mp",
    [string]$Gametype = "war",
    [int]$Boot = 100,
    [int]$Tail = 5,
    [string]$Extra = "",
    [string]$Out = ""
)
$ErrorActionPreference = "Continue"
if ($Port -eq 17733) { throw "17733 is the live server" }
$install = "D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13"
$ref = "$install\CODOL\1.1.1.13_server\alpha0022"
$home2 = "$env:TEMP\codol-probe-$Name"
if (-not $Out) { $Out = "$env:TEMP\codol-probe-$Name.log" }
$pw = (Get-Content -LiteralPath "$ref\native_server_rcon.txt" -Raw).Trim()
New-Item -ItemType Directory -Force "$home2\main" | Out-Null
Copy-Item "$PSScriptRoot\..\bin\home\main\waypoints" "$home2\main\" -Recurse -Force -ErrorAction SilentlyContinue
# Bot loadouts and characters come from mp/botclasstable.csv in the home. A
# bot without one has no character, so no server DObj, and the retained
# player_die (like C1's) refuses to kill a client without a DObj.
New-Item -ItemType Directory -Force "$home2\main\mp" | Out-Null
Copy-Item "$PSScriptRoot\..\bin\home\main\mp\botclasstable.csv" "$home2\main\mp\" -Force -ErrorAction SilentlyContinue
Remove-Item "$home2\main\qconsole.log" -ErrorAction SilentlyContinue
$a = @("+set","dedicated","2","+set","fs_basepath","`"$install`"","+set","fs_homepath","`"$home2`"",
  "+set","net_port","$Port","+set","net_ip","127.0.0.1","+set","rcon_password","`"$pw`"","+set","logfile","2","+set","logrcon","1",
  "+set","developer","1","+set","sv_fps","60","+set","codol_scriptPath","`"$Scripts`"","+set","codol_scriptOverlay","`"$Scripts`"",
  "+set","codol_scriptNativeOverlay","`"$Scripts`"","+set","codol_securityKeyPath","`"$ref\securitykey.bin`"",
  "+set","codol_profilePath","`"$ref\resources`"","+set","codol_zoneType",$Zone,"+set","codol_sessionMap",$Map,
  "+set","g_gametype",$Gametype)
if ($Extra) { $a += ($Extra -split " ") }
$a += @("+map",$Map)
$p = Start-Process -FilePath $Exe -ArgumentList $a -WorkingDirectory (Split-Path $Exe) -WindowStyle Minimized -PassThru
function rc($cmd) {
    $payload = [byte[]](0xff,0xff,0xff,0xff) + [System.Text.Encoding]::ASCII.GetBytes("rcon $pw $cmd")
    try { $u = New-Object System.Net.Sockets.UdpClient; $u.Client.ReceiveTimeout = 5000; $u.Connect("127.0.0.1",$Port)
      [void]$u.Send($payload,$payload.Length); $ep = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any,0)
      $d = $u.Receive([ref]$ep); return [System.Text.Encoding]::ASCII.GetString($d) } catch { return "NO REPLY" } finally { if ($u) { $u.Close() } }
}
Start-Sleep -Seconds $Boot
foreach ($c in $Commands) {
    if ($c -match "^sleep (\d+)$") { Start-Sleep -Seconds ([int]$Matches[1]) }
    else { rc $c | Out-Null; Start-Sleep -Milliseconds 700 }
}
Start-Sleep -Seconds $Tail
$alive = if (Get-Process -Id $p.Id -ErrorAction SilentlyContinue) { "alive" } else { "EXITED" }
Copy-Item "$home2\main\qconsole.log" $Out -Force -ErrorAction SilentlyContinue
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
"probe $Name on $Port done ($alive at end); log: $Out"
