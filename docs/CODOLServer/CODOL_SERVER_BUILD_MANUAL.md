# CODOL 服务器搭建手册（照做即可）

版本：2026-09-26
适用机器：本项目所在的这台 Windows 电脑
工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`

---

## 阅读说明（必读，30 秒）

本手册把"让 CODOL 连上我们自己写的服务器"拆成若干**阶段**。
每个阶段都有：

1. **目的** —— 这一步是为了什么
2. **前置条件** —— 做完上一步才能做这一步
3. **操作** —— 可以直接复制粘贴的命令
4. **预期输出** —— 你屏幕上应该看到什么
5. **如果不一致怎么办** —— 排错

**不要跳步。** 阶段 1 不通过就不要做阶段 2。

**术语表**（不懂就回来看）：

| 词 | 意思 |
|---|---|
| 固化启动链 | 本项目已验证可用的游戏启动方式，游戏出窗口且能进网络层 |
| 大厅 | 游戏里的主界面（多人菜单），必须连上服务器才出现 |
| `[100]` | 游戏内文字「`[100]无法连接大厅服务!`」，是**渲染**出来的，不是弹窗 |
| `dwauth.ini` | 客户端读的配置文件，决定"连哪台大厅服务器" |
| `/auth/` | 大厅鉴权接口（HTTPS POST） |
| TQoS | 服务器发现/测速（UDP 8000） |
| GDP | 游戏服务器协议（房间/频道/匹配） |

---

## 第 0 阶段：确认前置条件

### 0.1 目的

确认这台机器上文件齐全，且你以管理员身份操作。

### 0.2 操作

打开 PowerShell（右键 → **以管理员身份运行**），然后逐段粘贴执行。

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

Write-Host '--- 1) 游戏主程序 ---'
Test-Path 'run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe'

Write-Host '--- 2) 固化启动器（观察器） ---'
Test-Path 'restore_iips_contract_001\observer2\out\AboProbe.exe'

Write-Host '--- 3) 固化启动脚本 ---'
Test-Path 'run_codol_001\capture_elevated_network.ps1'

Write-Host '--- 4) 大厅探针服务器 ---'
Test-Path 'CODOLServer\lobby_server\lobby_probe_server.py'

Write-Host '--- 5) Python ---'
(Get-Command python).Source

Write-Host '--- 6) 是否管理员 ---'
([Security.Principal.WindowsPrincipal] `
  [Security.Principal.WindowsIdentity]::GetCurrent() `
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
```

### 0.3 预期输出

```
--- 1) 游戏主程序 ---
True
--- 2) 固化启动器（观察器） ---
True
--- 3) 固化启动脚本 ---
True
--- 4) 大厅探针服务器 ---
True
--- 5) Python ---
C:\Users\<你的用户名>\AppData\Local\Programs\Python\Python311\python.exe
--- 6) 是否管理员 ---
True
```

### 0.4 如果不一致

| 看到 | 说明 | 处理 |
|---|---|---|
| 某个 `False` | 文件缺失 | 停下来告诉开发，不要继续 |
| 最后是 `False` | 不是管理员 | 关掉，重新"以管理员身份运行" |
| `python` 报错找不到 | Python 未装/未加 PATH | 用 Python 3.11 安装包重装，勾选 "Add to PATH" |

---

## 第 1 阶段：让游戏能"连到我们指定的地址"

### 1.1 目的

游戏默认要去连腾讯的服务器（已停服）。本阶段让它改去连 `127.0.0.1`
（也就是这台电脑自己）。**这一步不改系统网络设置**，只改游戏进程内的一个字符串。

### 1.2 原理（一句话）

游戏 exe 里写死了域名 `ied-tqos.qq.com`。固化启动器
`AboProbe.exe` 会在游戏启动、但还没跑起来时，把这个字符串原地改成
`127.0.0.1`。所以游戏会连本机，不会连外网。

**这件事已经实现，本阶段只是验证它确实生效。**

### 1.3 前置条件

第 0 阶段全部 `True`。

### 1.4 操作

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

$tag = 'MANUAL_P1_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
$out = "CODOLServer\_manual\$tag"
New-Item -ItemType Directory -Path $out -Force | Out-Null

& 'restore_iips_contract_001\observer2\out\AboProbe.exe' `
    --mode B `
    --tag $tag `
    --duration 60 `
    --sandbox 'run_codol_001\sandbox_ifs1_20260923' *>&1 |
  Tee-Object -FilePath "$out\aboprobe.log"
```

命令会跑约 60 秒。**这期间会弹出游戏窗口，是正常的。**

### 1.5 预期输出（关键行）

```
created suspended pid=<数字> handle=<数字>
patch ied-tqos.qq.com@0xDD98A0 -> 127.0.0.1 ok=True
suspended patch targets=<数字>
resumed
```

三条关键：
- `created suspended` —— 游戏被挂起创建（成功）
- `patch ... ok=True` —— 域名改写成功（**最关键**）
- `resumed` —— 游戏继续运行

### 1.6 如果不一致

| 看到 | 说明 | 处理 |
|---|---|---|
| `CREATE_FAIL` | 游戏 exe 路径不对 | 回到 0.2 检查第 1 项 |
| `patch ... ok=False` | 改写失败（ACE 反作弊抢先占了内存） | 多试 2 次；仍失败就停下来告诉开发 |
| 完全没有 `patch` 行 | 域名没找到 | 停下来告诉开发，说明镜像和手册不一致 |
| 游戏窗口没出现 | 启动链问题 | 确认你是管理员；确认游戏没被别的进程占用 |

### 1.7 收尾

```powershell
Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
  Select-Object Id, ProcessName
```

如果还有残留进程，**不要用 `taskkill /IM python.exe`**（会杀掉提权代理）。
只针对游戏进程：

```powershell
Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue |
  Stop-Process -Force
```

---

## 第 2 阶段：搭起"大厅鉴权服务器"（`/auth/`）

### 2.1 目的

游戏进大厅前，会先做一次 **HTTPS 鉴权**：向 `https://<大厅主机>:<端口>/auth/`
发一个 JSON，等服务器回一个 JSON。本阶段把**这个服务器**跑起来。

### 2.2 原理（一句话）

游戏 exe 用 `POST /auth/` 发请求；服务器必须回 **HTTP 200** +
`{"auth_task":<请求值+1>, "code":700, ...}`。这套契约已经从 exe 反汇编确认。

### 2.3 前置条件

第 1 阶段通过（`patch ok=True`）。

### 2.4 操作 2A：生成证书

游戏强制校验证书，用的是**自己的** `cacert.pem`。我们要生成一个自签 CA，
并把 CA 追加进游戏的 `cacert.pem`。

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

python -X utf8 CODOLServer\lobby_server\mklobby_cert.py
```

### 2.5 预期输出（2A）

```
wrote to D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\lobby_server
  lobby_ca.pem / lobby_ca.key
  lobby_server.pem / lobby_server.key  (CN=127.0.0.1, SAN IP:127.0.0.1)
  signature algorithm: SHA256
  ca_append.pem  <- append this to the game's cacert.pem
```

### 2.6 操作 2B：把 CA 装进游戏目录（**会先备份**）

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

$sandbox = 'run_codol_001\sandbox_ifs1_20260923'
$cacert  = Join-Path $sandbox 'cacert.pem'
$append  = 'CODOLServer\lobby_server\ca_append.pem'

if (-not (Test-Path $cacert)) { throw "找不到 $cacert" }
if (-not (Test-Path $append)) { throw "找不到 $append" }

$backup = "$cacert.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -LiteralPath $cacert -Destination $backup -Force
Write-Host "备份 -> $backup"

Add-Content -LiteralPath $cacert -Value (Get-Content -LiteralPath $append -Raw) -Encoding ASCII
Write-Host "已追加 CA"

Write-Host '--- 校验 ---'
(Get-Item $cacert).Length
(Get-Item $backup).Length
```

### 2.7 预期输出（2B）

```
备份 -> run_codol_001\sandbox_ifs1_20260923\cacert.pem.bak_20260926_XXXXXX
已追加 CA
--- 校验 ---
<比备份大的数字>
<原大小，例如 291449>
```

追加后的大小必须**大于**备份大小。相等说明追加失败，重做。

### 2.8 操作 2C：写 `dwauth.ini`（**会先备份**）

`dwauth.ini` 是 7 行文本，格式如下（顺序固定，不要加注释）：

```
127.0.0.1     第1行：第二个待解析主机
0             第2行：uint16
127.0.0.1     第3行：★ 大厅主机
443           第4行：★ 大厅端口（客户端内部硬校验必须是 443）
0             第5行：hex
0             第6行：hex
0             第7行：hex
```

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

$sandbox = 'run_codol_001\sandbox_ifs1_20260923'
$ini     = Join-Path $sandbox 'dwauth.ini'

if (Test-Path $ini) {
    $backup = "$ini.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item -LiteralPath $ini -Destination $backup -Force
    Write-Host "备份 -> $backup"
}

@(
    '127.0.0.1'
    '0'
    '127.0.0.1'
    '443'
    '0'
    '0'
    '0'
) | Set-Content -LiteralPath $ini -Encoding ASCII

Write-Host '--- dwauth.ini 内容 ---'
Get-Content -LiteralPath $ini
Write-Host '--- 行数（必须是 7） ---'
(Get-Content -LiteralPath $ini).Count
```

### 2.9 预期输出（2C）

```
--- dwauth.ini 内容 ---
127.0.0.1
0
127.0.0.1
443
0
0
0
--- 行数（必须是 7） ---
7
```

行数不是 7 就重做。**格式错一个字符，游戏就读不到。**

### 2.10 操作 2D：启动探针服务器

开一个**新的** PowerShell 窗口（普通权限即可，不用管理员），执行：

```powershell
Set-Location 'D:\BaiduNetdiskDownload\使命召唤OL'

python -X utf8 CODOLServer\lobby_server\lobby_probe_server.py `
  --cert-dir CODOLServer\lobby_server `
  --bind 127.0.0.1 `
  --port 8443 `
  --log CODOLServer\logs\lobby_probe.jsonl
```

### 2.11 预期输出（2D）

```
{"event": "tls_config", "min": "769", "max": "771", "ciphers": <数字>, "ts": <数字>}
{"event": "listen", "bind": "127.0.0.1", "port": 8443, "pid": <数字>, "ts": <数字>}
```

**保持这个窗口开着，不要关。**

### 2.12 如果不一致

| 看到 | 说明 | 处理 |
|---|---|---|
| `Address already in use` | 8443 被占用 | 换 `--port 8444`，然后第 3 阶段里相应改端口 |
| 没有 `listen` 行 | 服务器起不来 | 把完整报错贴给开发 |
| `DeprecationWarning: ssl.TLSVersion.TLSv1` | 只是警告 | **正常，忽略** |

---

（后续阶段见本文件续篇）
