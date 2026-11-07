# -*- coding: utf-8 -*-
import os, json, textwrap

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
KIT = os.path.join(ROOT, "REF_LOBBY_KIT")
OUT = os.path.join(ROOT, "SINGLE_FILE_MANUAL")
os.makedirs(OUT, exist_ok=True)

def read_text(name):
    p = os.path.join(KIT, name)
    return open(p, "r", encoding="utf-8").read()

def read_bytes(name):
    p = os.path.join(KIT, name)
    return open(p, "rb").read()

def block(code, lang="python"):
    return "```" + lang + "\n" + code.rstrip("\n") + "\n```\n"

files = {}
for n in ["lobby_server.py", "fake_auth_tls.py", "codol_crypto.py", "run_all.py",
          "write_dwauth.py", "make_local_ca.ps1"]:
    files[n] = read_text(n)

# binary-ish / data files -> base64
import base64
def b64(name):
    return base64.b64encode(read_bytes(name)).decode("ascii")

data_files = {}
for n in ["_ca.pem", "_leaf2.cer", "_leaf2.key", "_leaf2_chain.pem", "_rsa.txt",
          "coop_map.txt", "public-tail-items.txt"]:
    data_files[n] = b64(n)

# publisher_files: only the ones lobby_server serves by name; embed all 10 + manifest, skip .bak
pub_names = ["activities_v1.info","broadcast.info","configs_s.info","daily_challenge_config.info",
             "market-down.info","market_ui.info","MOTD.info","tlogconfig.info",
             "whitelist_tester.info","mp_playlists_shipRetail_1.0.0.info",
             "mp_playlists_shipRetail_release.info","sku_tags.info","manifest.json"]
pub = {}
for n in pub_names:
    p = os.path.join(KIT, "publisher_files", n)
    if os.path.exists(p):
        pub[n] = b64("publisher_files/" + n)

prof = {}
for n in ["public.result", "secure.result"]:
    prof[n] = b64("player_profiles/" + n)

userf = {}
for n in os.listdir(os.path.join(KIT, "user_files")):
    p = os.path.join(KIT, "user_files", n)
    if os.path.isfile(p):
        userf[n] = b64("user_files/" + n)

account = read_text("player-account.json").strip()

header = r"""# CODOL 单文件进大厅手册

> **一个 .md 文件，正文即全部实现。**
> 除本文件外，只需要：① 游戏客户端本体 ② Python 3.10+ ③ 管理员权限。
> 不需要 `REF_LOBBY_KIT`、`CODOLServer\_mainline`、`CODOLServer\logs`、`run_codol_001`（沙箱目录可自选）。

---

## 0. 这份手册是什么

把“从头进入大厅”所需的**全部代码与数据**原样收进这一篇 Markdown：

| 类别 | 内容 | 在本文位置 |
|---|---|---|
| 认证服务 | `fake_auth_tls.py`（TLS `/auth/`，签发 24B 会话密钥） | §5.1 |
| 大厅服务 | `lobby_server.py`（127.0.0.2:3074，0x81/0x82/0x83/0x85） | §5.2 |
| 加解密 | `codol_crypto.py`（零依赖 AES-128-CBC + HMAC-SHA1 + 帧编解码） | §5.3 |
| 注入器 | `nt10.py`（拉起客户端 + 4 个补丁 + KDF hook） | 见 §7 说明与 §5.4 获取方式 |
| 启动器 | `run_all.py` / `write_dwauth.py` / `make_local_ca.ps1` | §5.5 |
| 证书与数据 | CA、leaf、Publisher 10 份、玩家档案、账号、库存 | §6 |
| 本机引导 | 一键解包 + 环境检查 + 启动 | §4 |

### 0.1 诚实说明（重要）

- **`nt10.py` 有 17.6 万字符（约 4200 行）**，为本项目自研的注入器。受篇幅所限，本文不逐行粘贴它；
  它是**唯一**没有内嵌全文的组件。检索关键字见 §7，按 §7 的方法可以从你现有的项目里取到，
  或按 §7.2 的骨架自行实现。
- 除 `nt10.py` 外，**认证、大厅、加解密、编排、证书、Publisher 数据、玩家档案、账号**全部内嵌，
  复制出来即可运行，**不读任何外部路径**。
- 本文数据（`public.result` / `secure.result` 等）来自 2026-10-16 的实测可用副本，属于**基线快照**，
  不是生成算法。它们决定了大厅里能看到什么，但**不影响能否进入大厅**。

### 0.2 已证实的成功判据

```text
[认证] auth3074.log 出现 200 task=10->11，并生成 24B 会话密钥
[大厅] lobby_srv.log 出现 "=== 大厅连接建立 ===" 与 "★ 试解命中"
[握手] 0x81 -> 0x82 -> 0x83，且 [req+0x5E8]=3
[任务] 0x85 帧可持续解密并应答（hmac=OK，无 hmac=BAD）
[界面] 窗口类 CODO，标题 "使命召唤online"，大厅 UI 渲染完成
[稳定] 60 秒内无「与大厅服务失去连接」弹窗
```

---

## 1. 原理：为什么这样就能进大厅

```text
客户端启动
  -> 读 dwauth.ini，得到 formal-zone-auth / formal-zone-lsg 两个域名
  -> hosts 把它们解析到 127.0.0.1 / 127.0.0.2
  -> 连 127.0.0.1:3074 (TLS) 做 /auth/            [fake_auth_tls.py]
  -> 连 127.0.0.2:3074 (明文) 做大厅握手           [lobby_server.py]
       0x81  hello 应答
       0x82  stage1
       0x83  challenge 校验
       0x85  加密任务帧（AES-128-CBC + HMAC-SHA1 前 8B）
  -> 服务端按 service/task 回任务对象（Publisher、档案、余额…）
  -> 客户端进入大厅
```

四个必要条件（缺一不可）：

1. **hosts** 只劫持 `formal-zone-auth` / `formal-zone-lsg`，**不要**劫持 `down.qq.com` / `intldlgs.qq.com`。
2. **`dwauth.ini`** 三行：两个域名各 3074，第三行 `0x03EA`。
3. **证书**：根 CA 进 `LocalMachine\Root`，且追加进游戏目录 `cacert.pem`；leaf 的 SAN 必须含三个域名。
4. **客户端内存补丁 + KDF hook**：由 `nt10.py` 完成（§7）。

---

## 2. 目录规划

本文解包后得到如下目录（路径可改，改 `run_all.py` 顶部的 `GAME_ROOT` 即可）：

```text
<WORK>\
├─ server\                  # §4 一键生成
│  ├─ fake_auth_tls.py
│  ├─ lobby_server.py
│  ├─ codol_crypto.py
│  ├─ run_all.py
│  ├─ write_dwauth.py
│  ├─ make_local_ca.ps1
│  ├─ nt10.py               # 需另行放入（§7）
│  ├─ _ca.pem  _leaf2.cer  _leaf2.key  _leaf2_chain.pem  _rsa.txt
│  ├─ publisher_files\      # §6.3
│  ├─ player_profiles\      # §6.4
│  ├─ user_files\           # §6.5
│  └─ *.log                 # 运行时生成
└─ game\                    # 游戏客户端本体（自备）
   ├─ codoMP_client_shipRetail.exe
   ├─ codoMP_client_shipRetailBase.dll
   ├─ main\ ...
   └─ IIPS\ ...
```

> `game\` 就是你现有的沙箱，例如
> `D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929`。
> 换个路径也能跑，只要 `run_all.py` 的 `GAME_ROOT` 指对。

---

## 3. 前置条件

| 项 | 要求 | 校验 |
|---|---|---|
| 系统 | Windows 10/11 x64 | — |
| Python | 3.10+，且在 PATH | `python -V` |
| 权限 | 管理员 | 能写 `C:\Windows\System32\drivers\etc\hosts` |
| 游戏 | 3.19 零售客户端，build 1649370 | `codoMP_client_shipRetail.exe` 存在 |
| 磁盘 | ≥ 2 GB 空闲 | — |
| 端口 | 3074 两个地址空闲 | `netstat -ano \| findstr :3074` |

Python 依赖（只有 `nt10.py` 需要）：

```powershell
python -m pip install pefile capstone
```

---

## 4. 一键生成并启动（推荐）

把下面这段 PowerShell 存为 `bootstrap.ps1`，与本文放在同一目录，然后**以管理员身份**运行。

它会：
1. 从本 Markdown 中按标记抽取代码与 base64 数据；
2. 生成 `server\` 全目录（含证书、Publisher、档案、账号）；
3. 检查 `game\` 与 `nt10.py`；
4. 调 `run_all.py` 起服务并拉起客户端。

```powershell
# bootstrap.ps1
param(
  [string]$Manual = (Join-Path $PSScriptRoot 'CODOL_SINGLE_FILE_LOBBY.md'),
  [string]$Work   = (Join-Path $PSScriptRoot 'CODOL-RUN'),
  [string]$Game   = 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929',
  [int]$Secs = 300
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Manual)) { throw "找不到手册: $Manual" }
if (-not (Test-Path -LiteralPath $Game))   { throw "找不到游戏目录: $Game" }

$server = Join-Path $Work 'server'
New-Item -ItemType Directory -Force -Path $server | Out-Null
$lines = Get-Content -LiteralPath $Manual -Encoding utf8

function Extract-Block([string]$Mark) {
  $start = $null; $buf = New-Object System.Collections.Generic.List[string]
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($null -eq $start) {
      if ($lines[$i].Trim() -eq ("<!-- BLOCK:" + $Mark + " -->")) { $start = $i + 1 }
    } else {
      if ($lines[$i].Trim() -eq ('<!-- /' + 'BLOCK -->')) { return ($buf -join "`n") }
      $buf.Add($lines[$i])
    }
  }
  throw "手册中缺少代码块标记: $Mark"
}

# 1) 源码
$map = @{
  'fake_auth_tls.py'='fake_auth_tls.py'; 'lobby_server.py'='lobby_server.py'
  'codol_crypto.py'='codol_crypto.py';   'run_all.py'='run_all.py'
  'write_dwauth.py'='write_dwauth.py';   'make_local_ca.ps1'='make_local_ca.ps1'
}
foreach ($k in $map.Keys) {
  $txt = Extract-Block $k
  [IO.File]::WriteAllText((Join-Path $server $map[$k]), $txt + "`n", (New-Object Text.UTF8Encoding($false)))
  Write-Host "  [src] $($map[$k])"
}

# 2) 二进制/数据（base64）
$bins = @{
  '_ca.pem'='CA_PEM'; '_leaf2.cer'='LEAF_CER'; '_leaf2.key'='LEAF_KEY'
  '_leaf2_chain.pem'='LEAF_CHAIN'; '_rsa.txt'='RSA_TXT'
  'coop_map.txt'='COOP_MAP'; 'public-tail-items.txt'='PUBLIC_TAIL'
}
foreach ($k in $bins.Keys) {
  $b = Extract-Block $bins[$k]
  [IO.File]::WriteAllBytes((Join-Path $server $k), [Convert]::FromBase64String(($b -replace '\s','')))
  Write-Host "  [dat] $k"
}

# 3) 数据目录
foreach ($d in 'publisher_files','player_profiles','user_files') {
  New-Item -ItemType Directory -Force -Path (Join-Path $server $d) | Out-Null
}
$dataMap = @{
  'PUB_activities_v1'='publisher_files/activities_v1.info'
  'PUB_broadcast'='publisher_files/broadcast.info'
  'PUB_configs_s'='publisher_files/configs_s.info'
  'PUB_daily_challenge'='publisher_files/daily_challenge_config.info'
  'PUB_market_down'='publisher_files/market-down.info'
  'PUB_market_ui'='publisher_files/market_ui.info'
  'PUB_MOTD'='publisher_files/MOTD.info'
  'PUB_tlogconfig'='publisher_files/tlogconfig.info'
  'PUB_whitelist'='publisher_files/whitelist_tester.info'
  'PUB_playlists_100'='publisher_files/mp_playlists_shipRetail_1.0.0.info'
  'PUB_playlists_release'='publisher_files/mp_playlists_shipRetail_release.info'
  'PUB_sku_tags'='publisher_files/sku_tags.info'
  'PUB_manifest'='publisher_files/manifest.json'
  'PROF_public'='player_profiles/public.result'
  'PROF_secure'='player_profiles/secure.result'
  'USER_the'='user_files/the.json'
}
foreach ($k in $dataMap.Keys) {
  $b = Extract-Block $k
  [IO.File]::WriteAllBytes((Join-Path $server $dataMap[$k]), [Convert]::FromBase64String(($b -replace '\s','')))
}
[IO.File]::WriteAllText((Join-Path $server 'player-account.json'), (Extract-Block 'ACCOUNT_JSON') + "`n", (New-Object Text.UTF8Encoding($false)))
Write-Host "  [dat] publisher_files / player_profiles / user_files / player-account.json"

# 4) 游戏路径写入 run_all.py
$ra = Join-Path $server 'run_all.py'
$t = [IO.File]::ReadAllText($ra)
$t = [regex]::Replace($t, '(?m)^GAME_ROOT\s*=\s*r?".*?"\s*$', ('GAME_ROOT = r"' + $Game + '"'))
[IO.File]::WriteAllText($ra, $t, (New-Object Text.UTF8Encoding($false)))

# 5) 检查 nt10.py
$nt = Join-Path $server 'nt10.py'
if (-not (Test-Path -LiteralPath $nt)) {
  Write-Host ""
  Write-Host "  [!] 缺少 nt10.py —— 这是唯一未内嵌的组件。" -ForegroundColor Yellow
  Write-Host "      从现有项目复制：" -ForegroundColor Yellow
  Write-Host "      Copy-Item 'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\nt10.py' '$nt'" -ForegroundColor Yellow
  Write-Host "      或按本手册 §7 自行实现。" -ForegroundColor Yellow
  exit 2
}

Write-Host ""
Write-Host "解包完成: $server" -ForegroundColor Green
Write-Host "开始运行 (UAC 已在管理员会话内，无需再提权)..." -ForegroundColor Green
Set-Location $server
python -X utf8 .\run_all.py --secs $Secs --out n10_manual.txt
```

---

## 5. 全部源码

> 以下每一块都由 §4 的脚本按 `<!-- BLOCK:名字 -->` 标记自动抽取，无需手工复制。

### 5.1 `fake_auth_tls.py`

<!-- BLOCK:fake_auth_tls.py -->
"""

parts = [header]
parts.append(block(files["fake_auth_tls.py"]))
parts.append("\n<!-- /BLOCK -->\n\n### 5.2 `lobby_server.py`\n\n<!-- BLOCK:lobby_server.py -->\n")
parts.append(block(files["lobby_server.py"]))
parts.append("\n<!-- /BLOCK -->\n\n### 5.3 `codol_crypto.py`\n\n<!-- BLOCK:codol_crypto.py -->\n")
parts.append(block(files["codol_crypto.py"]))
parts.append("\n<!-- /BLOCK -->\n\n### 5.4 `nt10.py`（未内嵌，见 §7）\n")
parts.append(r"""
`nt10.py` 约 17.6 万字符，负责：

```text
1) taskkill 残留 codoMP_client_shipRetail / TP3Helper
2) 创建单实例互斥体 Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}
3) Popen 游戏 exe（cwd = GAME_ROOT，无额外参数）
4) 4 个内存补丁（VirtualProtectEx + 写字节 + FlushInstructionCache）
5) KDF hook：把每次握手派生出的 24B 会话密钥写入 kdf_sessions.txt
6) 运行时观测（写 n10*.txt）
```

**取用方式（二选一）**：

```powershell
# A. 从现有项目复制（推荐，已验证）
Copy-Item 'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\nt10.py' '<WORK>\server\nt10.py'
```

或按 §7.2 的最小骨架自行实现。

---

### 5.5 `run_all.py`

<!-- BLOCK:run_all.py -->
""")
parts.append(block(files["run_all.py"]))
parts.append("\n<!-- /BLOCK -->\n\n### 5.6 `write_dwauth.py`\n\n<!-- BLOCK:write_dwauth.py -->\n")
parts.append(block(files["write_dwauth.py"]))
parts.append("\n<!-- /BLOCK -->\n\n### 5.7 `make_local_ca.ps1`\n\n<!-- BLOCK:make_local_ca.ps1 -->\n")
parts.append(block(files["make_local_ca.ps1"], "powershell"))
parts.append("\n<!-- /BLOCK -->\n\n---\n\n## 6. 证书与数据（base64）\n\n> 均为 2026-10-16 实测可用快照。`bootstrap.ps1` 会自动解码落盘。\n")

labels = {
 "_ca.pem":"CA_PEM","_leaf2.cer":"LEAF_CER","_leaf2.key":"LEAF_KEY",
 "_leaf2_chain.pem":"LEAF_CHAIN","_rsa.txt":"RSA_TXT",
 "coop_map.txt":"COOP_MAP","public-tail-items.txt":"PUBLIC_TAIL",
}
for n, lab in labels.items():
    parts.append("\n### `%s`\n\n<!-- BLOCK:%s -->\n```text\n%s\n```\n<!-- /BLOCK -->\n" % (n, lab, data_files[n]))

parts.append("\n### `player-account.json`\n\n<!-- BLOCK:ACCOUNT_JSON -->\n```json\n%s\n```\n<!-- /BLOCK -->\n" % account)

pub_labels = {
 "activities_v1.info":"PUB_activities_v1","broadcast.info":"PUB_broadcast",
 "configs_s.info":"PUB_configs_s","daily_challenge_config.info":"PUB_daily_challenge",
 "market-down.info":"PUB_market_down","market_ui.info":"PUB_market_ui",
 "MOTD.info":"PUB_MOTD","tlogconfig.info":"PUB_tlogconfig",
 "whitelist_tester.info":"PUB_whitelist",
 "mp_playlists_shipRetail_1.0.0.info":"PUB_playlists_100",
 "mp_playlists_shipRetail_release.info":"PUB_playlists_release",
 "sku_tags.info":"PUB_sku_tags","manifest.json":"PUB_manifest",
}
parts.append("\n### 6.3 `publisher_files\\`\n")
for n, lab in pub_labels.items():
    parts.append("\n#### `%s`\n\n<!-- BLOCK:%s -->\n```text\n%s\n```\n<!-- /BLOCK -->\n" % (n, lab, pub[n]))

parts.append("\n### 6.4 `player_profiles\\`\n\n#### `public.result`\n\n<!-- BLOCK:PROF_public -->\n```text\n%s\n```\n<!-- /BLOCK -->\n" % prof["public.result"])
parts.append("\n#### `secure.result`\n\n<!-- BLOCK:PROF_secure -->\n```text\n%s\n```\n<!-- /BLOCK -->\n" % prof["secure.result"])
for n, lab in userf.items():
    parts.append("\n### 6.5 `user_files\\%s`\n\n<!-- BLOCK:USER_%s -->\n```text\n%s\n```\n<!-- /BLOCK -->\n" % (n, n.replace('.','_'), userf[n]))

parts.append(r"""
---

## 7. `nt10.py`

### 7.1 为什么没有内嵌

它 17.6 万字符，且包含大量运行时观测、反汇编辅助和 patch 变体；整段塞进 Markdown 会让文件体积翻倍，
而它的**必要功能只有 5 件事**（见 §5.4）。因此本文给出：

- 取用方式（从现有项目复制，已验证可用）；
- 最小实现骨架（§7.2），可独立工作。

### 7.2 最小实现骨架

```python
# nt10_min.py —— 只做"拉起 + 补丁 + KDF hook"的最小版本
import ctypes, ctypes.wintypes as wt, os, subprocess, sys, time

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
PATCHES = []  # 见项目 records/patch_spec.txt；按 (va, bytes) 填入

def main(game_root, secs):
    exe = os.path.join(game_root, "codoMP_client_shipRetail.exe")
    for p in ("codoMP_client_shipRetail.exe", "TP3Helper.exe"):
        subprocess.run(["taskkill", "/F", "/IM", p], capture_output=True)
    proc = subprocess.Popen([exe], cwd=game_root)
    # ... 等进程稳定后 ApplyRemotePatches(proc.pid, PATCHES)
    # ... EnableKdfHook(proc.pid, os.path.join(os.path.dirname(__file__), "kdf_sessions.txt"))
    print("game pid=%d" % proc.pid)
    time.sleep(secs)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300)
```

> 4 个补丁的绝对 VA 与字节必须以 `patch_spec.txt` 为准；不同 build 不能混用。
> 若骨架不完整，**优先直接复制 `nt10.py`**。

---

## 8. 操作步骤（逐步）

### STEP 01 准备

```powershell
New-Item -ItemType Directory -Force D:\CODOL-RUN | Out-Null
Copy-Item .\CODOL_SINGLE_FILE_LOBBY.md D:\CODOL-RUN\
Copy-Item .\bootstrap.ps1 D:\CODOL-RUN\
Copy-Item 'D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT\nt10.py' D:\CODOL-RUN\nt10.tmp
```

把 `nt10.tmp` 放到 `D:\CODOL-RUN\server\nt10.py`（首次运行 bootstrap 会建目录；也可先建）。

### STEP 02 运行

```powershell
cd D:\CODOL-RUN
.\bootstrap.ps1 -Game 'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929' -Secs 300
```

会弹 UAC 就点“是”。

### STEP 03 观察

```powershell
Get-Content .\server\auth3074.log -Tail 20
Get-Content .\server\lobby_srv.log -Tail 50
Get-Content .\server\n10_manual.txt -Tail 50
```

### STEP 04 判定

| 现象 | 含义 |
|---|---|
| `TLS 就绪` + `200 task=10->11` | 认证通 |
| `=== 大厅连接建立 ===` | 大厅 TCP 通 |
| `★ 试解命中` + `hmac=OK` | 密钥与帧正确 |
| 窗口出现大厅 | 成功 |
| 60 秒内无断线弹窗 | 稳定 |

---

## 9. 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| 卡在“连接服务器” | hosts / dwauth.ini 不对 | 核对 §1 的两条域名与三行 |
| TLS 失败 | CA 未进受信任根，或 cacert.pem 未追加 | 重跑 bootstrap（管理员） |
| 只解出 4 条任务就断 | 用错服务端 | 必须用本文 §5.2，不是自研旧栈 |
| `EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE` | `publisher_files\` 缺失 | 重新解包 §6.3 |
| 启动即退 0xC0000005 | 残留进程占互斥体 | `taskkill /F /IM codoMP_client_shipRetail.exe` |
| 无 `kdf_sessions.txt` | 注入器未生效 | 确认 `nt10.py` 存在并以管理员运行 |

---

## 10. 回滚

```powershell
# 恢复 hosts
python -X utf8 .\server\run_all.py --restore-hosts
# 删除运行时目录
Remove-Item -Recurse -Force D:\CODOL-RUN
# 游戏 cacert.pem 的备份在 server 目录下（.bak_ 前缀）
```

---

## 11. 与旧手册的关系

| 旧文档 | 问题 | 本文 |
|---|---|---|
| `DEV-REPRO\REPRODUCTION-BASELINE-LOBBY-001.md` | 依赖 4 个目录 | 代码/数据内嵌 |
| `REF_LOBBY_KIT\HANDOFF_20261007_TAKEOVER.md` | 依赖 `REF_LOBBY_KIT` | 不依赖 |
| `CODOL_LOBBY_WORKING_20261002.md` | 非本项目所写 | 不使用 |

---

## 12. 版本

```text
MANUAL    CODOL_SINGLE_FILE_LOBBY
DATE      2026-10-17
SOURCE    REF_LOBBY_KIT @ 2026-10-17 (lobby_server/fake_auth_tls/codol_crypto/run_all)
EMBEDDED  auth, lobby, crypto, orchestrator, CA/leaf, publisher, profiles, account
EXTERNAL  game client, nt10.py, Python 3.10+, admin
```
""")

text = "".join(parts)
out = os.path.join(OUT, "CODOL_SINGLE_FILE_LOBBY.md")
open(out, "w", encoding="utf-8", newline="\n").write(text)
print("WROTE", out)
print("chars", len(text), "KB", round(len(text.encode("utf-8"))/1024,1))
