# OfflineServer —— 本地离线大厅一键部署

> 目标：在**不依赖官方服务器**的前提下，让《使命召唤OL》客户端通过 **DNS → TLS → /auth/ → 大厅 Socket** 完整流程，消除 “[100]无法连接大厅服务!” 弹窗。

---

## 目录结构
```
OfflineServer/
├─ lobby_server/            ← 从 CODOLServer/lobby_server 完整复制而来
│   ├─ ca_append.pem        ← 本地自签 CA（含 “CODOL Local Lobby CA”）
│   ├─ lobby_server.pem/.key← 服务端 TLS 证书/私钥（由 mklobby_cert.py 生成）
│   ├─ mklobby_response.py  ← 生成 /auth/ 固定 JSON 模板（含 auth_task 映射）
│   ├─ lobby_probe_server.py← 监听 127.0.0.1:8443，处理 /auth/ 探针
│   └─ lobby_socket_server.py← 监听 127.0.0.2:8444，真正的大厅长连接
├─ setup_offline_server.ps1 ← **核心一键脚本**（需管理员）
├─ run_setup_as_admin.bat   ← 双击即可提权运行上述 ps1
└─ README.md                ← 本文件
```

---

## 先决条件
| 项 | 说明 |
|---|---|
| **Windows 10/11** | `netsh interface portproxy` 仅在 Windows 支持 |
| **Python 3.8+** | `python.exe` 在 PATH 中（或在脚本里改 `$python` 变量） |
| **游戏安装目录** | `D:\BaiduNetdiskDownload\使命召唤OL\COD OL\` （含 `codoMP_client_shipRetail.exe`） |
| **管理员权限** | `netsh`、写入 `cacert.pem`、监听 443 端口均需提权 |

---

## 使用步骤（三合一）

### 1️⃣ 双击 `run_setup_as_admin.bat` （或右键 “以管理员身份运行”）
脚本会自动完成：
1. **生成 `dwauth.ini`** → 写入游戏目录，指向 `127.0.0.1:443`
2. **创建两条 portproxy 规则**  
   - `127.0.0.1:443 → 127.0.0.1:8443`  （probe /auth/）  
   - `127.0.0.2:443 → 127.0.0.2:8444` （大厅 Socket）
3. **把 `ca_append.pem` 追加进游戏的 `cacert.pem`** → 客户端信任自签证书
4. **重新生成 `lobby_response.json`** → 包含正确的 `auth_task` 映射与 `DE AD BD EF` ticket tag
5. **在控制台打印启动两个 Python 服务的命令**（见下文）

> **注意**：脚本只负责“准备环境”，**不会常驻后台运行两个 TLS 服务**，请按第 2 步手动启动。

---

### 2️⃣ 启动两个 TLS 服务（各开一个新的 PowerShell / CMD 窗口）

#### 窗口 A — Probe /auth/
```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\OfflineServer\lobby_server
python -X utf8 .\lobby_probe_server.py --cert-dir . --bind 127.0.0.1 --port 8443 --log ..\logs\lobby_probe.jsonl
```

#### 窗口 B — 大厅 Socket
```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\OfflineServer\lobby_server
python -X utf8 .\lobby_socket_server.py --cert-dir . --bind 127.0.0.2 --port 8444 --log ..\logs\lobby_socket.jsonl
```

> 两个窗口保持开启，日志会实时滚动。`logs/` 目录会在首次运行时自动创建。

---

### 3️⃣ 启动游戏
- 直接双击 `COD OL\codoMP_client_shipRetail.exe` 或用原有启动器。
- 进入多人大厅，**不应再出现 “[100]无法连接大厅服务!”**。
- 在两个服务窗口可看到 TLS 握手成功、HTTP `/auth/` 请求/响应、后续 Socket 消息。

---

## 常见问题排查
| 现象 | 可能原因 | 解决 |
|------|----------|------|
| 游戏仍弹窗 | `dwauth.ini` 未生成或端口不是 443 | 用记事本打开 `COD OL\dwauth.ini` 确认第 4 行为 `443` |
| TLS 握手失败 (`tlsv1 alert decrypt error`) | CA 未导入或证书不匹配 | 确认 `cacert.pem` 含 “CODOL Local Lobby CA”；重新运行 `setup_offline_server.ps1` |
| `netsh` 报 “拒绝访问” | 未以管理员运行 | 右键 `run_setup_as_admin.bat` → “以管理员身份运行” |
| 端口被占用 | 已有进程监听 8443/8444 | `netstat -ano | findstr :844` 找到 PID → `taskkill /PID xxx /F` |
| 日志里出现 `tls_fail` 但随后又 `tls_ok` | 客户端首次连接发空包，属正常重试 | 忽略第一次 `tls_fail`，以第二次 `tls_ok` 为准 |

---

## 进阶：自定义参数
编辑 `setup_offline_server.ps1` 顶部变量：
```powershell
$repoRoot   = "D:\BaiduNetdiskDownload\使命召唤OL"
$gameDir    = Join-Path $repoRoot "COD OL"
$offlineDir = Join-Path $repoRoot "OfflineServer"
$python     = "python"   # 若 python 不在 PATH，改为完整路径
```

---

## 目录说明（供二次开发）
| 文件/目录 | 作用 |
|-----------|------|
| `lobby_server/mklobby_response.py` | 定义 `TASK_ANSWER` 映射、`NULL_REF` tag、生成 `lobby_response.json` |
| `lobby_server/lobby_probe_server.py` | HTTP/TLS 服务，处理 `GET /`、`POST /auth/`，记录完整请求/响应 |
| `lobby_server/lobby_socket_server.py` | 第二阶段长连接，验证 `client_ticket` 前 4 字节 `DE AD BD EF` |
| `logs/*.jsonl` | 每次连接的结构化日志（event, peer, tls_version, auth_task …） |

---

## 后续扩展建议
1. **systemd / NSSM** 将两个 Python 服务注册为 Windows 服务，开机自启。  
2. **Docker/WSL2** 封装整套环境，实现真正“一键部署”。  
3. **集成测试**：用 `pytest + requests` 对 `/auth/` 做自动化回归。  
4. **协议逆向**：继续补全 LSG、队列、匹配等下游协议（当前标记为 UNKNOWN）。

---

**Enjoy your private lobby!** 🎮🚀