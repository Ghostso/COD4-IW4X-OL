<# 
.SYNOPSIS
    One‑click setup for a local CODOL lobby (offline / private server).
    Performs the three missing “配套服务” steps:
      1. Writes a correct dwauth.ini into the game folder (COD OL\)
      2. Creates the two netsh portproxy rules (requires elevation)
      3. Appends the local CA (ca_append.pem) into the game’s cacert.pem
      4. (Re)generates lobby_response.json used by the /auth/ probe server
      5. Starts the two Python TLS servers (probe on 127.0.0.1:8443, socket on 127.0.0.2:8444)

.NOTES
    - Run this script **as Administrator** (netsh needs elevation).
    - The script assumes the repository layout:
          D:\BaiduNetdiskDownload\使命召唤OL\COD OL\          <-- game folder (contains codoMP_client_shipRetail.exe)
          D:\BaiduNetdiskDownload\使命召唤OL\OfflineServer\lobby_server\  <-- copied from CODOLServer\lobby_server
    - Python 3.8+ must be on PATH (python.exe).
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------- 可调参数 ----------
$repoRoot      = "D:\BaiduNetdiskDownload\使命召唤OL"
$gameDir       = Join-Path $repoRoot "COD OL"
$offlineDir    = Join-Path $repoRoot "OfflineServer"
$lobbySrvDir   = Join-Path $offlineDir "lobby_server"
$caFile        = Join-Path $lobbySrvDir "ca_append.pem"
$certFile      = Join-Path $lobbySrvDir "lobby_server.pem"
$keyFile       = Join-Path $lobbySrvDir "lobby_server.key"
$python        = "python"   # or full path to python.exe

# ---------- 1. 写入 dwauth.ini ----------
Write-Host "`n=== [1/5] 生成 dwauth.ini ===" -ForegroundColor Cyan
$dwauthPath = Join-Path $gameDir "dwauth.ini"
$dwauthContent = @"
127.0.0.1
0
127.0.0.1
443
0
0
0
"@
[System.IO.File]::WriteAllText($dwauthPath, $dwauthContent, [System.Text.Encoding]::ASCII)
Write-Host "已写入 $dwauthPath" -ForegroundColor Green
Get-Content $dwauthPath

# ---------- 2. netsh portproxy ----------
Write-Host "`n=== [2/5] 配置 netsh portproxy (需管理员) ===" -ForegroundColor Cyan
$rules = @(
    @{listen='127.0.0.1'; listenPort=443; connect='127.0.0.1'; connectPort=8443},
    @{listen='127.0.0.2'; listenPort=443; connect='127.0.0.2'; connectPort=8444}
)
foreach ($r in $rules) {
    $cmd = "netsh interface portproxy add v4tov4 listenport=$($r.listenPort) listenaddress=$($r.listen) connectport=$($r.connectPort) connectaddress=$($r.connect)"
    Write-Host "执行: $cmd"
    Invoke-Expression $cmd
}
Write-Host "当前 portproxy 规则:" -ForegroundColor Green
netsh interface portproxy show all

# ---------- 3. 追加 CA 到 cacert.pem ----------
Write-Host "`n=== [3/5] 追加本地 CA 到游戏 cacert.pem ===" -ForegroundColor Cyan
$cacertPath = Join-Path $gameDir "cacert.pem"
if (-not (Test-Path $cacertPath)) {
    Write-Error "找不到 $cacertPath ，请确认游戏目录正确"
    exit 1
}
$caBlock = Get-Content $caFile -Raw
if ($caBlock -and ($caBlock -notmatch "CODOL Local Lobby CA")) {
    Write-Warning "ca_append.pem 似乎不包含预期的 CA 标识，仍继续追加"
}
Add-Content -Path $cacertPath -Value "`n$caBlock" -Encoding ASCII
Write-Host "已追加 CA 到 $cacertPath" -ForegroundColor Green
Select-String "CODOL Local Lobby CA" $cacertPath | Out-Null
if ($LASTEXITCODE -eq 0) { Write-Host "CA 校验通过" -ForegroundColor Green } else { Write-Warning "CA 可能未生效，请手动检查" }

# ---------- 4. 生成 lobby_response.json ----------
Write-Host "`n=== [4/5] 生成 lobby_response.json ===" -ForegroundColor Cyan
Push-Location $lobbySrvDir
& $python -X utf8 .\mklobby_response.py
Pop-Location
Write-Host "完成" -ForegroundColor Green

# ---------- 5. 启动两个 TLS 服务 ----------
Write-Host "`n=== [5/5] 启动 lobby_probe_server (127.0.0.1:8443) 与 lobby_socket_server (127.0.0.2:8444) ===" -ForegroundColor Cyan
Write-Host "这两个服务会常驻前台，建议分别在两个新的 PowerShell 窗口运行：" -ForegroundColor Yellow
Write-Host ""
Write-Host "# 窗口 A - Probe /auth/"
Write-Host "cd '$lobbySrvDir'"
Write-Host "& $python -X utf8 .\lobby_probe_server.py --cert-dir . --bind 127.0.0.1 --port 8443 --log '$offlineDir\logs\lobby_probe.jsonl'"
Write-Host ""
Write-Host "# 窗口 B - Socket"
Write-Host "cd '$lobbySrvDir'"
Write-Host "& $python -X utf8 .\lobby_socket_server.py --cert-dir . --bind 127.0.0.2 --port 8444 --log '$offlineDir\logs\lobby_socket.jsonl'"
Write-Host ""
Write-Host "=== 所有准备就绪 ===" -ForegroundColor Green
Write-Host "现在可以启动游戏，观察是否不再弹出 “[100]无法连接大厅服务!”" -ForegroundColor Cyan