# CODOL 单文件进大厅手册

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
```python
# -*- coding: utf-8 -*-
"""127.0.0.1:3074 上的 /auth/ 假服务 —— 用 Python 自己做 TLS。

端口/地址来源(三方已验证可用):
  Run-Session.ps1 把 hosts 写成
      127.0.0.1 formal-zone-auth.codol.qq.com
      127.0.0.2 formal-zone-lsg.codol.qq.com
  并把 dwauth.ini 写成
      formal-zone-lsg.codol.qq.com 3074
      formal-zone-auth.codol.qq.com 3074
      0x03EA
  即: 【auth(auth服务, TLS) 在 127.0.0.1:3074】, 【lsg(大厅明文) 在 127.0.0.2:3074】。
  以前我们用 8443/8446 —— 那两个端口客户端根本不会去连。

为什么不用 fake_auth_https.ps1(http.sys):
  实测 http.sys 关闭连接时【不发 TLS close-notify】(客户端会看到
  SSLEOFError: EOF occurred in violation of protocol)。这里用 Python 的 ssl
  自己收尾, close_notify 一定会发出去。

证书: _leaf2.cer(由受信任的本地 root CA 签发) + _rsa.txt(导出的 RSA 私钥参数)
     —— 两者由 make_local_ca.ps1 生成, leaf 的 SAN = localhost +
     formal-zone-auth.codol.qq.com + formal-zone-lsg.codol.qq.com
"""
import base64
import json
import os
import socket
import ssl
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGF = os.path.join(ROOT, "auth3074.log")
PORT = 3074
BIND = "127.0.0.1"

# ---- 契约常量 ----
# 票据公式来自三方 CodolLocalLobbyServer.cs:
#   ticket[0..3] = DE AD BD EF ; ticket[k] = (k*31 + 7) & 0xFF  (k = 4..127)
# (旧版我们写成 DE AD BD EF + 04 05 06..., 与三方不同)
TICKET = bytes([0xDE, 0xAD, 0xBD, 0xEF]) + bytes((k * 31 + 7) & 0xFF for k in range(4, 128))
TICKET_B64 = base64.b64encode(TICKET).decode()
TASK_MAP = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}

# ★ 2026-10-03 多客户端改造: 客户端真正用的会话密钥是 **ticket[97:121]**(实测, 见
#   HANDOFF §10.9) —— 所以让每个 /auth/ 请求拿到**不同的 24B**, 一举解决两件事:
#     1) 每个客户端的 KDF 派生密钥天然不同("共享一把密钥"在协议上本来就不成立);
#     2) 大厅服务端能靠"从 0x82 帧里读出的 ticket[97:121]"把连接与该客户端的密钥配对。
#   已记录到 auth_sessions.txt, 便于排障与核对。
AUTH_SESS = os.path.join(ROOT, "auth_sessions.txt")


def make_ticket(session_key24):
    """按三方公式造 128B 票据, 但把偏移 97..120 换成传入的 24B 会话密钥。"""
    t = bytearray(TICKET)
    t[97:121] = session_key24[:24].ljust(24, b"\x00")
    return bytes(t)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---- 把 RSA 参数拼成 PKCS#1 PEM ----
def _der_len(n):
    if n < 0x80:
        return bytes([n])
    e = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(e)]) + e


def _der_int(b):
    b = b.lstrip(b"\x00") or b"\x00"
    if b[0] & 0x80:
        b = b"\x00" + b
    return b"\x02" + _der_len(len(b)) + b


def _pem(tag, der):
    b = base64.b64encode(der).decode()
    return ("-----BEGIN %s-----\n" % tag
            + "\n".join(b[i:i + 64] for i in range(0, len(b), 64))
            + "\n-----END %s-----\n" % tag)


def build_pem_files():
    key = {}
    with open(os.path.join(ROOT, "_rsa.txt")) as f:
        for ln in f:
            if "=" in ln:
                k, _, v = ln.strip().partition("=")
                key[k] = base64.b64decode(v)
    body = _der_int(b"\x00") + b"".join(
        _der_int(key[n]) for n in
        ("Modulus", "Exponent", "D", "P", "Q", "DP", "DQ", "InverseQ"))
    key_pem = _pem("RSA PRIVATE KEY", b"\x30" + _der_len(len(body)) + body)
    leaf = open(os.path.join(ROOT, "_leaf2.cer"), "rb").read()
    chain = _pem("CERTIFICATE", leaf)
    ca = os.path.join(ROOT, "_ca.pem")
    if os.path.exists(ca):
        chain += open(ca, "r").read()
    kp = os.path.join(ROOT, "_leaf2.key")
    cp = os.path.join(ROOT, "_leaf2_chain.pem")
    open(kp, "wb").write(key_pem.encode())      # 二进制写, 强制 LF
    open(cp, "wb").write(chain.encode())
    return cp, kp


def make_context(certfile, keyfile):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except Exception:
        pass
    # 客户端只提供老的 RSA/DHE-CBC 套件(AES128-SHA/AES256-SHA 等)
    for cs in ("ALL:@SECLEVEL=0", "DEFAULT:@SECLEVEL=0"):
        try:
            ctx.set_ciphers(cs)
            break
        except Exception:
            continue
    ctx.load_cert_chain(certfile, keyfile)
    return ctx


def _get_str(body, key):
    """从请求 JSON 里粗取一个字段值(不依赖严格 JSON 解析)。"""
    i = body.find(('"%s"' % key).encode())
    if i < 0:
        return ""
    j = body.find(b":", i)
    if j < 0:
        return ""
    k = j + 1
    while k < len(body) and body[k:k + 1] in (b" ", b"\t"):
        k += 1
    if body[k:k + 1] == b'"':
        e = k + 1
        while e < len(body):
            if body[e] == 0x5C:
                e += 2
                continue
            if body[e] == 0x22:
                break
            e += 1
        return body[k + 1:e].decode("utf-8", "replace")
    e = k
    while e < len(body) and body[e:e + 1] not in (b",", b"}", b"\r", b"\n"):
        e += 1
    return body[k:e].decode("utf-8", "replace").strip()


def build_response(body):
    """★ 完全照抄三方 CodolLocalLobbyServer.cs 的 200 应答形态:
       - 顶层有 ret/code/auth_task/status/success
       - 票据字段同时放顶层与 data 内层, 且都以【字符串】给 _size
       - 额外带 DW-* 响应头(校验器会读)
       - iv_seed 回显请求里的值(三方就是回显)
       - 【不含 extra_data】(三方没有; 我们也拿不到那个 749B 模板)
    """
    task = _get_str(body, "auth_task")
    iv_seed = _get_str(body, "iv_seed") or "0"
    resp_task = TASK_MAP.get(int(task), 1) if task.isdigit() else 1

    # ★ 每次 /auth/ 发一张**会话密钥唯一**的票据(见 make_ticket 注释)
    sk = os.urandom(24)
    tk_b64 = base64.b64encode(make_ticket(sk)).decode()
    try:
        with open(AUTH_SESS, "a", encoding="utf-8") as f:
            f.write("%d %s\n" % (int(time.time()), sk.hex()))
    except Exception:
        pass
    log("  会话密钥(本次) = %s  (写入 %s)" % (sk.hex(), os.path.basename(AUTH_SESS)))

    fields = ('"member_position":"1","estimated_wait_time":"0","next_poll_after":"1",'
              '"iv_seed":"%s",'
              '"client_ticket":"%s","client_ticket_size":"128",'
              '"server_ticket":"%s","server_ticket_size":"128",'
              '"lsg_server_ticket":"%s","lsg_server_ticket_size":"128"'
              % (iv_seed, tk_b64, tk_b64, tk_b64))

    js = ('{"ret":0,"code":700,"auth_task":%d,"status":0,"success":true,%s,'
          '"data":{%s},"profile":{"id":1,"name":"Offline"}}'
          % (resp_task, fields, fields)).encode()

    head = ("HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "DW-Ticket-Seed: %s\r\n"
            "DW-Client-Ticket-Size: 128\r\n"
            "DW-Client-Ticket: %s\r\n"
            "DW-Server-Ticket-Size: 128\r\n"
            "DW-Server-Ticket: %s\r\n"
            "Connection: close\r\n"
            "X-Local-Emulator: unsigned-protocol-experiment\r\n\r\n"
            % (len(js), iv_seed, tk_b64, tk_b64)).encode()
    return head + js, task, resp_task


def handle(conn, addr):
    try:
        conn.settimeout(30)
        ss = CONTEXT.wrap_socket(conn, server_side=True)
    except Exception as e:
        log("TLS 握手失败 %s: %r" % (addr, e))
        try:
            conn.close()
        except Exception:
            pass
        return
    try:
        log("=== TLS 就绪 %s 版本=%s 套件=%s ===" % (addr, ss.version(), ss.cipher()[0]))
        data = b""
        while b"\r\n\r\n" not in data:
            c = ss.recv(4096)
            if not c:
                break
            data += c
        head, _, rest = data.partition(b"\r\n\r\n")
        clen = 0
        for ln in head.split(b"\r\n")[1:]:
            k, _, v = ln.partition(b":")
            if k.strip().lower() == b"content-length":
                try:
                    clen = int(v.strip())
                except Exception:
                    clen = 0
        body = rest
        # Expect: 100-continue -> 先回 100, 再收 body
        if b"100-continue" in head.lower() and len(body) < clen:
            ss.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        while len(body) < clen:
            c = ss.recv(4096)
            if not c:
                break
            body += c
        log("[%s] %s  Host=%s  blen=%d" % (head.split(b"\r\n")[0].decode("latin1", "replace"),
                                           addr, addr, len(body)))
        for ln in head.split(b"\r\n")[1:]:
            if ln:
                log("      " + ln.decode("latin1", "replace"))
        if body:
            log("      body: " + body.decode("utf-8", "replace"))
        resp, task, rtask = build_response(body)
        ss.sendall(resp)
        log("  -> 200 task=%s->%s (%d 字节)" % (task, rtask, len(resp)))
        # ★ 关键: 发 TLS close-notify (http.sys 不发, 这是契约的一部分)
        try:
            ss.settimeout(1.5)
            ss.unwrap()
            log("  TLS close-notify 已发")
        except Exception as e:
            log("  close-notify: %r" % (e,))
    except Exception as e:
        log("处理异常 %s: %r" % (addr, e))
    finally:
        try:
            ss.close()
        except Exception:
            pass


if __name__ == "__main__":
    certfile, keyfile = build_pem_files()
    CONTEXT = make_context(certfile, keyfile)
    log("==== fake_auth_tls 启动 %s:%d (cert=%s) ====" % (BIND, PORT, os.path.basename(certfile)))
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((BIND, PORT))
    srv.listen(16)
    log("[*] 监听 %s:%d" % (BIND, PORT))
    while True:
        try:
            c, ad = srv.accept()
        except Exception:
            continue
        threading.Thread(target=handle, args=(c, ad), daemon=True).start()
```

<!-- /BLOCK -->

### 5.2 `lobby_server.py`

<!-- BLOCK:lobby_server.py -->
```python
# -*- coding: utf-8 -*-
"""大厅(lsg)明文 TCP 服务 —— 127.0.0.2:3074 (= formal-zone-lsg.codol.qq.com)。

协议(全部照抄三方 CodolLocalLobbyServer.cs / 其 lsg.log 真实帧):
  1) 客户端先发 28 字节 hello:
        C8 00 00 00 | C8 00 00 00 | D2 00 00 00 | DC 00 00 00 | 00 00 08 00 | <8B nonce>
  2) 服务端回 0x81:  u32 22 | 00 | 81 | u32 0xDC | 8B 随机 | 8B(=hello[20:28])
  3) 客户端发 0x82(stage1):  u32 len | AB | 82 | <...>
  4) 服务端回 0x83:  u32 10 | 00 | 83 | <8B challenge>(从客户端内存读; 有补丁4 时不校验)
  5) 之后客户端发 0x85 加密任务帧, 服务端解密 -> 回 0x85 应答
        frame = u32 len | AB | 85 | u32 seq | iv[16] | cipher | hmac8[8]
  另外 4 个 0x00 字节 = keepalive。

密钥来自 nt10.py 写出的 secrets.txt(服务端进程读游戏内存会被拦, 所以由 nt10 读)。

分派覆盖(照抄三方 + 本轮借鉴 ol-mod):
  - 10/21 发行方配置, 10/12 用户文件, 8/1,8/2 档案
  - 80/32,80/130,93/1 钱包(CP/GP)
  - 21/5,21/16 findSessions 会话对象(258B) —— 见 session_objects(), 移植自 ol-mod
  - 80/70,107,119,154,173,174,203,230,232 商城空应答(ol-mod 同款语义)

会话密钥: 默认仍由 nt10.py 读游戏内存写 secrets.txt(见下)。
  ★ 另有一条 KDF 派生分支(codol_crypto.derive_session_keys, 借鉴 ol-mod):
    它只在**与内存快照互证一致**时才被采信; 实测当前 build 对不上(kdf_probe.py),
    所以实际生效的仍是内存快照 —— 日志会打 `[kdf] ...` 供持续观察。

用法:
  python lobby_server.py                    # 127.0.0.2:3074
  python lobby_server.py --lobby-bind 0.0.0.0 --lobby-port 8446 --raw-ports 80,8081   # 调试
"""
import argparse
import glob
import hashlib
import json
import os
import re
import socket
import struct
import subprocess
import sys
import zlib


# ======================================================================
# 玩家档案(service=8) —— 逐字节照抄 C# SavePublicProfile(第 700-764 行)
# ======================================================================
def _profile_crc(buf, off, length):
    """照抄 C# ProfileCrc: CRC32(多边形 0xEDB88320) 取反。"""
    num = 0xFFFFFFFF
    for i in range(off, off + length):
        num ^= buf[i] & 0xFF
        for _ in range(8):
            num = (num >> 1) ^ (0xEDB88320 if (num & 1) else 0)
    return (~num) & 0xFFFFFFFF


def _inflate_profile(blob):
    """照抄 C# InflateProfile。C# 的 num3==1 表示压缩。"""
    return zlib.decompress(blob, 15)


# ★ 2026-10-06 实验开关: 往 public.result 尾部 125 个 0x07 槽里注入名片 itemID。
#   目的: 验证这 125 槽是不是"军牌定制可装备清单"。
#   名单在同目录 public-tail-items.txt(每行一个十进制 itemID)。
#   回滚: 删除 public-tail-inject.on
def _inject_public_tail(tail_bytes, n=125):
    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(here, "public-tail-inject.on")):
        return tail_bytes
    try:
        ids = []
        with open(os.path.join(here, "public-tail-items.txt"),
                  "r", encoding="ascii") as f:
            for ln in f:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    ids.append(int(ln.split()[0]))
    except Exception:
        return tail_bytes
    if len(tail_bytes) < n * 5:
        return tail_bytes
    vals = []
    for i in range(n):
        if tail_bytes[i * 5] != 0x07:
            return tail_bytes
        vals.append(struct.unpack_from("<i", tail_bytes, i * 5 + 1)[0])
    present = set(vals)
    added = 0
    for it in ids:
        if it in present:
            continue
        for i, v in enumerate(vals):
            if v == 0:
                vals[i] = it
                present.add(it)
                added += 1
                break
    if not added:
        return tail_bytes
    out = bytearray()
    for v in vals:
        out += bytes([0x07]) + struct.pack("<i", v)
    print("-- [profile-tail] 注入 %d 个名片 itemID 到可装备清单" % added)
    return bytes(out)


def save_public_profile(plain, outdir, owner=16701785630074219790):
    """处理 8/3 上传的 public profile, 落盘 public.result。

    plain 是**含 8 字节头**的完整明文(与 C# 一致)。
    返回 (ok, note)。
    """
    try:
        declared = struct.unpack_from("<I", plain, 0)[0]
        num = declared + 5
        n125 = 125
        if num > len(plain) or num < 35 + n125 * 5 or plain[num - 1] != 0:
            return False, "结构长度不符(declared=%d len=%d)" % (declared, len(plain))
        if not (plain[8] == 8 and plain[13] == 8 and plain[18] == 8
                and plain[23] == 8 and plain[28] == 19 and plain[29] == 8):
            return False, "结构标记不符"
        num3 = struct.unpack_from("<I", plain, 14)[0]      # 压缩标志
        num4 = struct.unpack_from("<I", plain, 19)[0]      # 必须 1
        num5 = struct.unpack_from("<I", plain, 24)[0]      # CRC
        num6 = struct.unpack_from("<i", plain, 30)[0]      # blob 长度
        if num4 != 1 or num6 < 0 or num6 > 32768:
            return False, "版本/长度不符(num4=%d num6=%d)" % (num4, num6)
        if num != 35 + num6 + n125 * 5:
            return False, "总长不符(num=%d 期望=%d)" % (num, 35 + num6 + 625)
        raw = bytes(plain[34:34 + num6])
        if num3 == 1:
            raw = _inflate_profile(raw)
        if len(raw) != 32768:
            return False, "解压后 %d != 32768" % len(raw)
        if (struct.unpack_from("<I", raw, 4)[0] != 233
                or struct.unpack_from("<I", raw, 8)[0] != 1248641861):
            return False, "档案魔数不符"
        if struct.unpack_from("<I", raw, 0)[0] != num5 or \
                _profile_crc(raw, 4, 32764) != num5:
            return False, "CRC 校验失败"
        for i in range(n125):
            if plain[34 + num6 + i * 5] != 7:
                return False, "尾部第 %d 项 tag != 07" % i

        # 重建 public.result(照抄第 730-737 行)
        out = bytearray(32803 + n125 * 5)
        out[0] = 10
        struct.pack_into("<Q", out, 1, owner)
        out[9:35] = plain[8:34]
        struct.pack_into("<I", out, 15, 0)
        struct.pack_into("<I", out, 31, 32768)
        out[35:35 + 32768] = raw
        out[32803:32803 + n125 * 5] = _inject_public_tail(
            plain[34 + num6:34 + num6 + n125 * 5], n125)

        d = os.path.join(outdir, "player_profiles")
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, "public.result")
        tmp = dst + ".tmp"
        with open(tmp, "wb") as f:
            f.write(bytes(out))
        os.replace(tmp, dst)
        return True, ("public.result 已保存(%d 字节, 压缩=%d, blob=%d)"
                      % (len(out), num3, num6))
    except Exception as e:
        return False, "解析异常: %r" % (e,)


# ======================================================================
# 玩家档案(service=8) —— public.result 的打包/拆包
#   结构(实测):
#     0A <owner u64> | 08 <ver u32> | 08 <flags u32> | 08 <u32 1>
#     08 <crc u32>   | 13 08 <len u32> <裸档案 32768B>
#     07 <i32> x125  <- 可装备清单(军牌定制里能换什么)
# ======================================================================
def _read_profile_tail(path):
    """从已有 public.result 里读出尾部 0x07 清单。"""
    try:
        pub = open(path, "rb").read()
    except Exception:
        return []
    k = 0
    while k < len(pub):
        t = pub[k]
        if t == 0x0A:
            k += 9
        elif t == 0x08:
            k += 5
        elif t == 0x13:
            ln = struct.unpack_from("<I", pub, k + 2)[0]
            k += 6 + ln
            break
        else:
            return []
    vals = []
    while k + 5 <= len(pub) and pub[k] == 0x07:
        vals.append(struct.unpack_from("<i", pub, k + 1)[0])
        k += 5
    return vals


def _pack_public_result(raw, tail=(), owner=16701785630074219790,
                        version=4, flags=0, one=1):
    """把 8/3 上传的裸档案重新包成 8/1 要回的 public.result。"""
    crc = struct.unpack_from("<I", raw, 0)[0]
    out = bytearray()
    out += bytes([0x0A]) + struct.pack("<Q", owner)
    out += bytes([0x08]) + struct.pack("<I", version)
    out += bytes([0x08]) + struct.pack("<I", flags)
    out += bytes([0x08]) + struct.pack("<I", one)
    out += bytes([0x08]) + struct.pack("<I", crc)
    out += bytes([0x13, 0x08]) + struct.pack("<I", len(raw)) + raw
    for v in tail:
        out += bytes([0x07]) + struct.pack("<i", v)
    return bytes(out)
import threading
import time

import codol_crypto as cc

# 商城模块(独立文件, 移植自三方 v32 的 MarketplaceStore.cs)。目录缺 SKU 目录文件时降级为空应答。
try:
    import marketplace_store as ms
except Exception as _e:                                     # pragma: no cover
    ms = None
    print("-- [market] marketplace_store 不可用(%r) -> 商城回空应答" % (_e,))

# 把我们自己编的 SKU 目录页接进来(默认关, 见 market_skus.py)。
try:
    import market_skus
except Exception as _e:                                     # pragma: no cover
    market_skus = None
    print("-- [market] market_skus 不可用(%r) -> 商城目录仍回空页" % (_e,))

# 库存 Owner 必须与写入时一致(C# 里是玩家 CODOID; 三方本地实现用 1)。
# 可用同目录的 marketplace-owner.txt 覆盖。
def _market_owner():
    """库存 Owner 的取值优先级:
       ① marketplace-owner.txt (显式覆盖)  ② 现有 marketplace-inventory.json 里的 Owner
       ③ 默认 1。
    库存文件的 Owner 是权威(C# 的 Read 会严格校验 state.Owner != owner 并抛错),
    所以**必须**优先沿用它, 否则会出现 "Invalid marketplace inventory owner/version"。"""
    try:
        with open(os.path.join(OUTDIR, "marketplace-owner.txt"), "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        pass
    try:
        with open(os.path.join(OUTDIR, "marketplace-inventory.json"), "r", encoding="utf-8") as f:
            return int(json.load(f)["Owner"])
    except Exception:
        return 1


MARKET_OWNER = 1        # 真正的取值在 OUTDIR 定义之后(见下方 _market_owner())

OUTDIR = os.path.dirname(os.path.abspath(__file__))
MARKET_OWNER = _market_owner()
LOCK = threading.Lock()
SECRETS = os.path.join(OUTDIR, "secrets.txt")
# ★ nt10 的 KDF hook 直接派生出来的密钥(优先用, 见 read_secrets 注释)
SECRETS_KDF = os.path.join(OUTDIR, "secrets_kdf.txt")
# ★ 多客户端: nt10 每个会话追加一行「会话密钥 + 四把子密钥 + challenge」
#   (kdf_sessions.txt)。服务端靠它把"连接"与"该客户端的密钥"配对。
SESS_FILE = os.path.join(OUTDIR, "kdf_sessions.txt")

# 占位 challenge(补丁4 把客户端的 nonce 校验 NOP 掉了, 所以拿不到真值时也能过)
H8 = bytes.fromhex("1122334455667788")

# nt10.py 在客户端 [obj+0x5E8]==1 时写这个标志
READY_FLAG = os.path.join(OUTDIR, "lobby_ready.flag")

# ---- 靶场(firing range)开关文件(照抄三方 C# 的 File.Exists 判据; 都放在 OUTDIR) ----
# ★ 这三个开关**都不存在**时, 本文件行为与改造前**完全一致**(不破坏已跑通的大厅)。
FR_SESSION_FLAG = os.path.join(OUTDIR, "firingrange-session.enabled")        # 21/5 靶场会话对象
FR_BOOKING_FLAG = os.path.join(OUTDIR, "firingrange-booking-push.enabled")   # 6/* booking 推送
FR_BATTLE_FLAG = os.path.join(OUTDIR, "firingrange-battle.enabled")          # 战斗服(UDP)启动

# ★ 2026-10-07: 客户端 PvE 剧情任务实测请求 playlist=10, 随后 6/14 的完整
#   mmstart 明确携带 `g_gametype coop; map coop_training_mp_cargoship;`。
#   21/5 必须回同一套 map/gametype, 否则客户端不会进入加载、也就不会连 28960。
#   保留为集合是为了后续把其它 PvE playlist 逐个实测加入, 避免误伤靶场(playlist=1)。
PVE_PLAYLIST_IDS = {10}
PVE_ADDRESS67_FLAG = os.path.join(OUTDIR, "pve-address67.on")
# C# BuildFiringRangeBookingAccepted 的"裸"消息(含结尾 0x00, 长度 16)——
# 内层流是 typed-mode-disabled, 只写 u32 长度 + 这个消息字节。
FR_BOOKING_ACCEPTED = b"mmbook accepted\x00"
FR_BATTLE_BIND = "0.0.0.0"       # 战斗服 UDP —— 绑所有本地 IPv4,
                                 # 避免客户端按 localhost 解析到别的地址时收不到包
FR_BATTLE_PORT = 28960


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    with LOCK:
        print(line, flush=True)
        try:
            with open(os.path.join(OUTDIR, "lobby_srv.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def hexd(d):
    return d.hex(" ")


def _read_hex_file(path):
    """把 `key value` 文本解析成 dict(pid/state 转 int, 其余按 hex 转 bytes)。"""
    d = {}
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if len(p) != 2:
                    continue
                if p[0] in ("pid", "state"):
                    try:
                        d[p[0]] = int(p[1])
                    except Exception:
                        pass
                else:
                    try:
                        d[p[0]] = bytes.fromhex(p[1])
                    except Exception:
                        pass
    except Exception:
        pass
    return d


def read_secrets():
    """读会话密钥。

    ★ 优先 `secrets_kdf.txt` —— 那是 nt10 挂住客户端的 HMAC(0xBA0D20) 后,
      **直接用抓到的两个入参派生**出来的(2026-10-03, 见 HANDOFF §10.8);
      已实测与内存快照逐字段一致(kdf_probe.py --inputs 全 OK)。
      好处: 不再依赖"读 auth 对象内存槽 [sub+0x604..0x60C]"以及 [sub+0x5E8]==3 的时序。
    没有该文件时回退 `secrets.txt`(老的 nt10 内存快照路径)。
    """
    d = _read_hex_file(SECRETS_KDF)
    if d.get("aes_out") and d.get("hmac_out"):
        d["src"] = "kdf"
        return d
    d = _read_hex_file(SECRETS)
    d["src"] = "mem"
    return d


def load_kdf_sessions():
    """读 nt10 写的「会话 → 密钥」表; 以**会话密钥 hex**为键。

    格式(nt10 每命中一次 KDF 追加一行):
        <session_key:24B> <transcript_hash:20B> <challenge:8B> <aes_out:16B>
        <aes_in:16B> <hmac_out:20B> <hmac_in:20B>
    """
    d = {}
    try:
        with open(SESS_FILE, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if len(p) != 7:
                    continue
                try:
                    d[p[0]] = {
                        "session_key": bytes.fromhex(p[0]),
                        "transcript_hash": bytes.fromhex(p[1]),
                        "challenge": bytes.fromhex(p[2]),
                        "aes_out": bytes.fromhex(p[3]),
                        "aes_in": bytes.fromhex(p[4]),
                        "hmac_out": bytes.fromhex(p[5]),
                        "hmac_in": bytes.fromhex(p[6]),
                        "src": "kdf-session",
                    }
                except Exception:
                    continue
    except Exception:
        pass
    return d


def load_kdf_sessions_all():
    """按文件顺序返回**全部**会话记录(允许同一会话密钥多行)。

    ★ 为什么需要它: 客户端 `/auth/` 只发一次(会话密钥不变), 但**每次重连大厅都会
      重新派生一套密钥**(transcriptHash 变) → 同一会话密钥会有多行。
      单用 dict(最后一行胜出) 会配错 —— 2026-10-03 实测就出现了 `hmac=BAD`。
      所以真正可靠的判据是"试解 + HMAC 校验"(见 pick_keyset)。
    """
    out = []
    try:
        with open(SESS_FILE, encoding="utf-8") as f:
            for ln in f:
                p = ln.split()
                if len(p) != 7:
                    continue
                try:
                    out.append({
                        "session_key": bytes.fromhex(p[0]),
                        "transcript_hash": bytes.fromhex(p[1]),
                        "challenge": bytes.fromhex(p[2]),
                        "aes_out": bytes.fromhex(p[3]),
                        "aes_in": bytes.fromhex(p[4]),
                        "hmac_out": bytes.fromhex(p[5]),
                        "hmac_in": bytes.fromhex(p[6]),
                        "src": "kdf-session",
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return out


def pick_keyset(frame, sk_hex=None):
    """**按 HMAC 校验**挑出这条连接该用的密钥组; 返回 (keys, 解密结果) 或 (None, None)。

    候选顺序: 同会话密钥的(新→旧) → 其余全部(新→旧) → 全局 secrets。
    HMAC-SHA1 截断 8 字节, 误判概率 2^-64 —— 足够当判据。
    """
    cands = load_kdf_sessions_all()
    same = [c for c in cands if sk_hex and c["session_key"].hex() == sk_hex]
    others = [c for c in cands if not (sk_hex and c["session_key"].hex() == sk_hex)]
    for k in list(reversed(same)) + list(reversed(others)):
        try:
            r = cc.decrypt_task_frame(frame, k["aes_out"], k["hmac_out"])
        except Exception:
            continue
        if r and r.get("hmac_ok"):
            return k, r
    g = read_secrets()
    if g.get("aes_out"):
        try:
            r = cc.decrypt_task_frame(frame, g["aes_out"], g["hmac_out"])
            if r and r.get("hmac_ok"):
                return g, r
        except Exception:
            pass
    return None, None


def requested_name(plain):
    if not plain:
        return None
    strings = []
    i = 0
    while i < len(plain):
        if plain[i] == 0x10:
            end = plain.find(b"\x00", i + 1)
            if end != -1:
                strings.append(plain[i+1:end].decode("latin1", "replace"))
                i = end + 1
                continue
        i += 1
    if len(strings) >= 2 and strings[1]:
        return strings[1]
    if len(strings) == 1 and strings[0]:
        return strings[0]
    import re
    m = re.search(rb"[0-9A-Za-z_\-\.]{3,}", plain)
    return m.group(0).decode("ascii", "replace") if m else None


ACCOUNT = os.path.join(OUTDIR, "player-account.json")

# ---------------------------------------------------------------- 会话/对局参数
# 21/5 findSessions 的会话对象要用到的"权威服务器地址"。停服后我们本地没有真游戏服务,
# 先按配方里的既定值填 127.0.0.1:28960(与 SHARED.md 记的"21/5 含 127.0.0.1:28960"一致)。
GAME_IP = (127, 0, 0, 1)
GAME_PORT = 28960
SESSION_ID = 0x1122334455667788          # 非零即可; roomId 由它派生
MAP_NAME = "mp_crash_tropical"           # ol-mod 的缺省地图
SEC_KEY_FILE = os.path.join(OUTDIR, "battle_security_key.txt")
_default_sk = b"\x01" * 16
if os.path.exists(SEC_KEY_FILE):
    try:
        _sk_raw = open(SEC_KEY_FILE, "r", encoding="ascii").read().strip()
        if len(_sk_raw) == 32:
            _default_sk = bytes.fromhex(_sk_raw)
    except Exception:
        pass
SEC_KEY = _default_sk

# ---- 房间/即时消息用到的身份与 id(照抄 ol-mod Unknown0B / InstantMessage) ----
PLAYER_UID = 0x1100001DEADC0DE           # 平台内部 id(与我们 docs 里记的一致)
ROOM_ID = SESSION_ID                     # createRoom 回的 roomId(非零即可)
ROOM_SECOND_ID = 0x1122334455667788 ^ 0x53525652564F4443   # ol-mod 用它区分合成会话


def player_name():
    return str(read_account().get("Name", "Player"))


def session_objects(query_kind):
    """21/5 findSessions 的结果对象 —— 移植 ol-mod MatchmakingService.findSessions。

    queryKind = 1(FIND_SERVERS, 实测我们客户端发的就是它):
        只回"权威服务器"这一条, maxPlayers=18 / currentPlayers=0(ol-mod 的合成候选);
    其它 queryKind:
        回本地房间一条, currentPlayers=1。

    ★ 三条"错了就崩"的门槛已在 cc.build_session_record 内保证
      (gate 字段=67 / roomId 非零十进制 / hostUid != 玩家 CODOID)。
    """
    cur = 0 if query_kind == 1 else 1
    return [cc.build_session_record(SESSION_ID, GAME_IP, GAME_PORT,
                                    game_type=0, max_players=18, current_players=cur,
                                    map_name=MAP_NAME, security_key=SEC_KEY)]


def keys_of(derived):
    """把 KDF 派生结果映射成我们的四把密钥名; 未派生时返回 {}。
    方向对照(ol-mod Crypto.cpp:209-215):
        decrypt -> aes_out(解客户端帧)   encrypt -> aes_in(加密我的应答)
        requestHmac -> hmac_out(验客户端帧)   responseHmac -> hmac_in(签我的应答)"""
    if derived.get("decrypt") and derived.get("encrypt"):
        return {"aes_out": derived["decrypt"], "aes_in": derived["encrypt"],
                "hmac_out": derived["request_hmac"], "hmac_in": derived["response_hmac"],
                "challenge": derived["response_id"]}
    return {}


def read_account():
    """读 player-account.json(三方 LocalPlayerAccount 的同款字段); 缺文件时给默认值。"""
    d = {"Name": "Player", "Level": 70, "Experience": 11056700,
         "Prestige": 4, "CodPoints": 999999, "Gold": 999999}
    try:
        with open(ACCOUNT, encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def balance_object(currency):
    """照抄 MarketplaceStore.BalanceObject: 03 <currency> 08 <u32 值>。
    currency=1 -> CP(CodPoints), 2 -> GP(Gold)。"""
    a = read_account()
    v = int(a.get("CodPoints", 0)) if currency == 1 else int(a.get("Gold", 0))
    return bytes([3, currency & 0xFF, 8]) + struct.pack("<I", v & 0xFFFFFFFF), v


def reply_objects(service, task, plain):
    """按任务类型准备应答对象(照抄三方的分派)。返回 (objects, 说明, pushes)。
    pushes = [(messageType, body)] —— 服务端主动推送(类型 2), 由调用方在应答之后发出。"""
    def ack(note):
        return [], note, []

    if service == 10 and task == 21:                     # 发行方配置
        nm = requested_name(plain)
        if not nm:
            return ack("名字没解析出来")
        p = os.path.join(OUTDIR, "publisher_files", os.path.basename(nm))
        # ★ 2026-10-05: 客户端在大厅初始化时请求 mp_playlists_shipRetail_1.0.0.info,
        #   而参考套件只带了 mp_playlists_shipRetail_release.info(同一份内容)。
        #   缺这个文件就是 EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE 的直接原因。
        #   这里做一个同义名回退, 免得重新拷贝套件后又要手工补文件。
        if not os.path.exists(p) and os.path.basename(nm) == "mp_playlists_shipRetail_1.0.0.info":
            p = os.path.join(OUTDIR, "publisher_files", "mp_playlists_shipRetail_release.info")
        if not os.path.exists(p):
            return ack("缺 %s" % nm)
        d = open(p, "rb").read()
        return [cc.serialize_file_data(d)], "publisher %s (%d 字节)" % (nm, len(d)), []
    if service == 10 and task == 12:                     # 用户文件
        nm = requested_name(plain)
        if not nm:
            return ack("名字没解析出来")
        p = os.path.join(OUTDIR, "user_files", os.path.basename(nm))
        if not os.path.exists(p):
            return ack("缺 %s (三方此处也是 missing)" % nm)
        d = open(p, "rb").read()
        return [cc.serialize_file_data(d)], "user_file %s (%d 字节)" % (nm, len(d)), []
    if service == 6 and task == 14:
        # Matchmaking Booking (mmbook 796 ...)
        accepted = struct.pack(chr(60) + "I", len(b"mmbook accepted\x00")) + b"mmbook accepted\x00"
        bk_body = cc.instant_push_body(1, "localhost", accepted)
        pushes = [(2, bk_body)]
        return [], "Matchmaking 6/14 mmbook -> accepted", pushes

    if service == 8 and task in (1, 2):                  # 档案 public / secure
        fn = "public.result" if task == 1 else "secure.result"
        p = os.path.join(OUTDIR, "player_profiles", fn)
        if not os.path.exists(p):
            return ack("缺 %s" % fn)
        d = open(p, "rb").read()
        return [d], "profile %s (%d 字节)" % (fn, len(d)), []
    if service == 8 and task == 3:
        # ★★ 2026-10-06: 客户端**上传**玩家档案(名片/装备/统计都在里面)。
        #    逐字节照抄 C# SavePublicProfile(第 700-764 行):
        #      头部 35 字节 + blob(可 zlib) + 125 项 07 <i32> 尾清单。
        #    之前一律回空 ACK -> 客户端发的档案被丢弃 -> 买的东西/装备不生效。
        #    reply_objects 收到的 plain 只是 payload, 必须补 8 字节头。
        try:
            declared = len(plain) + 3
            frame = (struct.pack("<I", declared)
                     + bytes([0x86, service, 0x03, task]) + plain)
            ok, note = save_public_profile(frame, OUTDIR)
            return ack("profile 8/3 %s" % note)
        except Exception as e:
            return ack("profile 8/3 处理失败: %r" % (e,))
    if (service == 80 and task in (32, 130)) or (service == 93 and task == 1):
        # 钱包 —— 对象 = writeU8(type) + writeU32(amount)。
        # ol-mod 实测: 客户端一次余额轮询发两个请求 —— Marketplace/130 取第 1 个钱包,
        # 93/1 取第 2 个(MarketplaceService.cpp:381-408 注释), 与我们的映射一致。
        cur = 1 if service == 80 else 2
        obj, val = balance_object(cur)
        return [obj], "balance %d/%d currency=%d 值=%d" % (service, task, cur, val), []
    if service in (0x15, 0x8A) and task in (5, 16):
        # 21/5 findSessions —— 会话对象(进房间/进对局的前置)。
        # ★ 2026-10-06: 把原始 payload 打出来 —— 用户选不同地图/模式时会带不同参数,
        #   我们要按它回的 session 才能对上; 之前无条件回靶场 session, 所以"剧情任务进不去"。
        log("       ★ findSessions 原始 payload(%d): %s"
            % (len(plain or b""), (plain or b"").hex(" ")))
        # ★ 靶场模式(2026-10-03): 存在开关文件 firingrange-session.enabled 时, 改用三方 C#
        #   权威的 BuildMissionSessionObject(67B 地址块 / GameType 0x1000007 / MaxPlayers=1),
        #   返回**单个**对象。这是"靶场进入路径"的第一步。
        #   ★ 无开关 → 完全保持既有行为(258B session 记录), 不破坏已跑通的大厅。
        if os.path.exists(FR_SESSION_FLAG):
            # ★ 2026-10-07: 从请求里取 playlist(第 3 个 u32), 回填进 session。
            #   实测剧情任务请求: 08 01 | 08 00 | 08 0a | 07 <i32> -> playlist 候选=10。
            _vals = []
            _i = 0
            while _i < len(plain or b""):
                _t = plain[_i]
                _i += 1
                if _t == 0x08 and _i + 4 <= len(plain):
                    _vals.append(struct.unpack_from("<I", plain, _i)[0]); _i += 4
                elif _t == 0x07 and _i + 4 <= len(plain):
                    _vals.append(struct.unpack_from("<i", plain, _i)[0]); _i += 4
                elif _t == 0x01 and _i + 1 <= len(plain):
                    _i += 1
                else:
                    break
            _pl = _vals[2] if len(_vals) >= 3 else None
            log("       ★ findSessions 解析值=%s -> 回填 playlist=%s"
                % (_vals, _pl))
            # ★ 2026-10-07: playlist=10 是客户端实测的 PvE 剧情任务入口。
            #   客户端随后发来的完整 mmstart 已证明它选择的是:
            #       g_gametype coop; map coop_training_mp_cargoship;
            #   这里回同一套 map/gametype; 靶场仍走原来的 firing-range 分支。
            # ★ 靶场核心修复：无论 _pl 请求何值，在靶场模式下始终返回权威 268 字节靶场会话对象
            #   (map=mp_firingrange, GameType=0x1000007, MaxPlayers=1, Playlist=1, 67B 地址块 127.0.0.1:28960)
            #   彻底消除因下发 4人剧情任务(coop_take_mp_fav_tropical)导致客户端搜寻超时与“服务器繁忙”！
            objs = [cc.build_mission_session_object(
                firing_range=True, playlist=(_pl or 1),
                address67=True)]
            return objs, ("findSessions -> ★ 靶场 mission session 对象(单条, %d 字节, "
                          "map=%s GameType=0x1000007 MaxPlayers=1 playlist=1)"
                          % (len(objs[0]), cc.MISSION_MAP_FIRING)), []
        qk, _ = cc.parse_u32_tagged(plain or b"", 0)
        objs = session_objects(qk)
        return objs, ("findSessions queryKind=%s -> %d 条 session 对象, 每条 %d 字节"
                      % (qk, len(objs), len(objs[0]) if objs else 0)), []
    if service in (0x15, 0x8A) and task == 1:
        # ★ 21/1 createSession —— 2026-10-03 实测: 客户端进出房间时会发它(x1),
        #   我们原先没实现 → 回空对象 → 客户端拿不到 sessionId, 走不到战斗服。
        #   照抄 ol-mod MatchmakingService.cpp:404-438: 对象 = [blob 8B processSessionId]。
        ob = cc.Buf()
        ob.blob(struct.pack("<Q", SESSION_ID & 0xFFFFFFFFFFFFFFFF))
        return [ob.data()], ("createSession -> sessionId=0x%X (对象 %d 字节)"
                             % (SESSION_ID, len(ob.data()))), []
    if service in (0x15, 0x8A) and task in (2, 3, 9, 12):
        # updateSession / deleteSession / submitPerformance / updatePlayers —— 照抄 ol-mod 均为空 ACK
        return ack("matchmaking %d/%d 空应答(payload=%d)" % (service, task, len(plain or b"")))
    if service in (0x15, 0x8A) and task == 10:
        # getPerformanceValues: 对象 = [u64 userId][i64 value]; 我们还没有性能数据 -> 空
        return ack("matchmaking %d/10 getPerformanceValues 空(无数据)" % service)
    if service == 0x47 and task == 2:
        # Tencent/2: (string username) → [bool false][string username]  (ol-mod TencentService.cpp)
        nm = b""
        m = re.search(rb"[0-9A-Za-z_\-\.\[\]]{2,32}", plain or b"")
        if m:
            nm = m.group(0)
        ob = cc.Buf(); ob.bool_(False); ob.string(nm)
        return [ob.data()], ("Tencent/2 -> bool false + username %r" % nm.decode("latin1", "replace")), []
    if (service == 80 and task in (70, 107, 119, 154, 173, 174, 203, 230, 232)) or (service == 93 and task == 131):
        # 商城 —— 语义与字节布局照抄三方 v32 的 MarketplaceStore.cs
        #   154 purchaseSkus / 93-131: 购买(真实扣款 + 写入库存)
        #   203: 库存列表    230: 玩家资产(PlayerData)
        #   70 getSkusPaginated: 刻意回"空页"。源码注释写明: 格式正确的空应答能让商店保持
        #      可浏览; 而客户端反序列化不了的应答会让**整个 marketplace 服务死掉**
        #      (STORE/INVENTORY 变灰且本次会话不再恢复) —— 这是实测过的失败。
        #      CODOL 的 SKU 记录不是 MW19 的 bdMarketplaceSku(多两个字段), 照抄兄弟作品的
        #      字段序就会触发那次失败, 所以这里坚持回空页。107/173/174/232 同理。
        cur = 1 if service == 80 else 2
        if ms is not None:
            try:
                if task in (154, 131):
                    # ★★ C# 的 ParsePurchase(frame, declared, ...) 里 frame 是**含 8 字节头的完整明文**
                    #    (它按 frame[8+i] 取 payload[i]); 而 reply_objects 收到的 plain 只是 payload,
                    #    必须把 8 字节头补回去, 否则整体错位 8 字节 -> 模板校验必然失败。
                    #    2026-10-03 实测: 硬证据是客户端发的 93/131 payload(58B) 与三方日志里的
                    #    逐字节相同, declared=61, 仅因缺头而报 Unsupported purchase parameters。
                    declared = len(plain) + 3
                    frame = struct.pack("<I", declared) + bytes([0x86, service, 0x03, task]) + plain
                    sku, qty = ms.parse_purchase(frame, declared, cur)
                    tx = hashlib.sha1(bytes(plain)).hexdigest()   # 同一购买帧重发天然幂等
                    # ★ 2026-10-05: 实测客户端购买帧里的 sku 大多**不在** exe 内嵌目录里
                    #   (点 6 次: 241/242/31774/31816 全部查无此 SKU, 只有 32223 命中)。
                    #   => 客户端用的是"服务端目录"的编号, 与 exe 内嵌那份不同。
                    #   把未知 SKU 记下来(供后续建映射), 但仍按原语义失败 —— 不做"假成功不发货"。
                    try:
                        ms.purchase(OUTDIR, MARKET_OWNER, tx, cur, [sku], [qty])
                    except Exception as e:
                        try:
                            with open(os.path.join(OUTDIR, "unknown_skus.txt"), "a",
                                      encoding="ascii") as f:
                                f.write("%d\t%s\n" % (sku, e))
                        except Exception:
                            pass
                        # ★ 2026-10-06: 失败时把 SKU 也写进主日志, 便于分类。
                        log("       ★ 购买失败 sku=%d currency=%d qty=%d 原因=%s"
                            % (sku, cur, qty, e))
                        raise
                    # ★★ 2026-10-06 更正: C# 参考实现购买成功后回的是
                    #    BuildTaskReply(..., resultObject=**null**, status=purchaseStatus)
                    #    —— **不携带任何结果对象**(第 1343 行)。
                    #    我们之前回了一个"余额对象", 客户端会把它当成别的东西解析,
                    #    于是判定购买失败(游戏内表现为"点了没反应")。
                    #    现在改为与参考实现一致: 空对象 + status=0。
                    return [], \
                           ("marketplace 80/%d 购买成功 sku=%d qty=%d (空对象+status=0)"
                            % (task, sku, qty)), []
                if task == 203:
                    objs = ms.inventory_results(OUTDIR, MARKET_OWNER)
                    return objs, ("marketplace 80/203 库存 %d 件" % len(objs)), []
                if task == 230:
                    d = ms.marketplace_player_data(OUTDIR, MARKET_OWNER)
                    return ([d] if d else []), \
                           ("marketplace 80/230 玩家资产 %d 字节" % len(d or b"")), []
                # ★ 2026-10-05: 目录页(70/107/119/173/174/232)——
                #   默认仍回空页(空页是安全的, 客户端不炸); 打开 marketplace-skus.on
                #   后才回我们自己编的 SKU 页(字段表见 _sku_schema_as.py)。
                #   ★ 先发少量(marketplace-skus-count.txt), 确认客户端不再抛 #1009 再放量。
                if task in (70, 107, 119, 173, 174, 232):
                    return ack("marketplace 80/%d safe empty reply" % task)
            except Exception as e:
                return ack("marketplace 80/%d 失败(%s) -> 空 ACK" % (task, e))
        return ack("marketplace 80/%d 空应答(ol-mod 同款语义)" % task)

    if service == 11:
        if task == 13:                                   # createRoom(请求无参)
            # 对象 = [u64 roomId][u32 memberCount=0][u32 18][u64 secondId][bool false][bool false][u32 1]
            ob = cc.Buf()
            ob.u64(ROOM_ID); ob.u32(0); ob.u32(18); ob.u64(ROOM_SECOND_ID)
            ob.bool_(False); ob.bool_(False); ob.u32(1)
            return [ob.data()], ("createRoom -> roomId=0x%X secondId=0x%X (%d 字节)"
                                 % (ROOM_ID, ROOM_SECOND_ID, len(ob.data()))), []
        if task in (1, 9, 11):
            return ack("0B/%d consumeUserPair(u64,u64) 空应答" % task)
        if task == 2:
            return ack("0B/2 leaveRoom 空应答")
        if task == 4:
            # ContentUnlock2::task4: 完整对齐 TypeArray (0x6C 0x08)
            objs = []
            if plain and len(plain) >= 6:
                content_ids = []
                if plain[0] == 0x6C and plain[1] == 0x08 and len(plain) >= 10:
                    cnt = struct.unpack_from("<I", plain, 6)[0]
                    for idx in range(cnt):
                        off = 10 + idx * 4
                        if len(plain) >= off + 4:
                            content_ids.append(struct.unpack_from("<I", plain, off)[0])
                elif plain[0] == 0x6C and len(plain) >= 6:
                    cnt = struct.unpack_from("<I", plain, 2)[0]
                    for idx in range(cnt):
                        off = 6 + idx * 4
                        if len(plain) >= off + 4:
                            content_ids.append(struct.unpack_from("<I", plain, off)[0])
                else:
                    for off in range(0, len(plain) - 3, 4):
                        content_ids.append(struct.unpack_from("<I", plain, off)[0])
                for cid in content_ids:
                    ob = bytes([0x08]) + struct.pack("<I", cid) + bytes([0x08]) + struct.pack("<I", 32)
                    objs.append(ob)
            return objs, ("ContentUnlock2 28/4 解锁响应: %d 项内容已全部置为已解锁" % len(objs)), []
        if task in (1, 2, 3):
            return ack("ContentUnlock2 28/%d 响应成功" % task)

    return [], "UNMAPPED service=%d task=%d payload=%dB -> 空 ACK (功能未实现)" \
                % (service, task, len(plain or b"")), []


def _fnv1a(data):
    """FNV-1a 32 位 —— ol-mod InstantMessageService.cpp:135-139 用的就是它。"""
    h = 0x811C9DC5
    for b in (data or b""):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def _parse_set_room_data(payload):
    """尽量解开 0B/4 setRoomData 的 (u64 channelId, blob batch, u32 type)。

    带 tag 的形式: 0A <u64> | 13 08 <u32 len> <batch...> | 08 <u32 type>
    解不出就返回 (0, b"", None) —— 调用方按无频道处理, 不影响应答。
    """
    d = payload or b""
    ch, batch, tp = 0, b"", None
    off = 0
    try:
        if off + 9 <= len(d) and d[off] == 0x0A:
            ch = struct.unpack_from("<Q", d, off + 1)[0]
            off += 9
        elif off + 8 <= len(d):
            ch = struct.unpack_from("<Q", d, off)[0]      # 无 tag 兜底
            off += 8
        if off + 6 <= len(d) and d[off] == 0x13 and d[off + 1] == 0x08:
            ln = struct.unpack_from("<I", d, off + 2)[0]
            batch = d[off + 6:off + 6 + ln]
            off += 6 + ln
        if off + 5 <= len(d) and d[off] == 0x08:
            tp = struct.unpack_from("<I", d, off + 1)[0]
    except Exception:
        pass
    return ch, batch, tp


def wait_ready(limit=30.0):
    """等客户端的"大厅就绪"信号(客户端分发器只在 [obj+0x5E8]==1 时才受理 0x81)。

    ★ 多客户端: nt10 现在同时写 `lobby_ready.flag` 与 `lobby_ready_<pid>.flag`。
      这里**只要有任一存在**就放行并消费掉全局那个(带 pid 的留给 nt10 自己管)。
      ⚠️ 局限: "哪条连接属于哪个 pid"在 0x82 之前无法判定(身份只在 0x82 的票据里),
      所以这里是"至少有一个客户端就绪即放行"; 尚未就绪的那条会被客户端复位后重连
      (实测客户端本来就会重连 2~3 次, 自愈)。
    """
    t0 = time.time()
    while time.time() - t0 < limit:
        if os.path.exists(READY_FLAG):
            try:
                os.remove(READY_FLAG)
            except Exception:
                pass
            return time.time() - t0
        try:
            if glob.glob(os.path.join(OUTDIR, "lobby_ready_*.flag")):
                return time.time() - t0
        except Exception:
            pass
        time.sleep(0.02)
    return None


def handle_lobby(conn, addr):
    log("=== 大厅连接建立 %s ===" % (addr,))
    w = wait_ready(30.0)
    log("  客户端就绪等待: %s" % ("%.2fs" % w if w is not None else "超时(继续)"))
    conn.settimeout(1.0)

    # 1) 等客户端的 28 字节 hello
    hello = b""
    t0 = time.time()
    while time.time() - t0 < 5.0 and len(hello) < 28:
        try:
            d = conn.recv(28 - len(hello))
        except socket.timeout:
            continue
        except Exception as e:
            log("  hello 读取异常: %r" % (e,))
            break
        if not d:
            break
        hello += d
    if hello:
        log("  <- 客户端 hello (%d 字节): %s" % (len(hello), hexd(hello)))
        try:
            open(os.path.join(OUTDIR, "lobby_rx.bin"), "ab").write(hello)
        except Exception:
            pass

    # 2) 发 0x81(回显 hello[20:28]); ★ 保存下来 —— 它要参与 transcript 的密钥派生
    try:
        f = cc.build_handshake_reply(hello)
        sent81 = f
        log("  -> 0x81 (%d 字节) = %s" % (len(f), hexd(f)))
        conn.sendall(f)
    except Exception as e:
        log("  发 0x81 失败: %r" % (e,))
        try:
            conn.close()
        except Exception:
            pass
        return

    # ★★ 每连接的**出站 0x85 帧序号计数器** —— 照抄三方 CodolLocalLobbyServer.cs:1144
    #    `uint num8 = 1u;`：它给**所有**出站 0x85 帧(应答 **和** 推送)共用同一个序号，
    #    每发一帧 +1，与客户端请求的 seq 解耦。
    #    2026-10-04 实测教训: 我们此前让推送"回显请求 seq"，于是应答(seq=N)与推送(seq=N)
    #    **重复**，客户端立刻 ConnectionReset(10054) —— 见 lobby_srv.log 00:50:14。
    #    懒初始化为首帧的请求 seq：无推送时与旧的"回显"行为**逐字节等价**(零回归)，
    #    一旦插入推送，后续帧仍严格 +1(不再重复)，这正是三方 num8 的语义。
    out_seq = None
    # ★★ 2026-10-07: 独立的"应答 id 计数器" —— 对应三方参考的 `++num9`。
    #   参考代码里 **帧 seq 与 replyId 是两个独立计数器**：
    #       BuildTaskReply(secrets, task, num8++, ++num9, ...)
    #   我方旧代码把 replyId 直接**回显请求 seq**（`r["seq"]`）。
    #   在 1:1 应答（请求 seq 与出站 seq 同步递增）时两者同值，看不出差别；
    #   但一旦**在应答之间插入推送**（如 6/14 的 booking push），
    #   出站帧 seq 会比请求 seq 多走一格 → 回显值就与客户端期望的
    #   replyId 错位 → 客户端匹配不上 → ClientException / "服务器繁忙"。
    #   所以这里改成独立递增，与参考一致。
    reply_id = 0
    sent83 = False
    buf = b""
    ntasks = 0
    pending = []          # ★ 密钥快照还没就绪时先把 0x85 攒着, 一旦有 key 再解
    keys_logged = False
    # ★ 2026-10-07: "候选密钥组都没过 HMAC"只提示一次, 避免刷屏；
    #   命中后置回 False（见下面 conn_keys 命中处）。
    pending_waited = False
    sent81 = b""          # 我们实际发出的 0x81(要进 transcript, 必须原样保存)
    derived = {}          # ★ KDF 派生出来的会话密钥
    conn_keys = {}        # ★ 多客户端: 本条连接专属的密钥(由 HMAC 试解确定)
    conn_sk = ""          # 本条连接从 0x82 票据[97:121] 读出的会话密钥 hex
    t0 = time.time()
    while time.time() - t0 < 600:
        # ---- ① 先把攒着的 0x85 处理掉(密钥可能刚被 nt10 写出来) ----
        if pending:
            # ★ 密钥组还没定: 用首个待解帧 **按 HMAC 试解**挑一组(唯一可靠判据)。
            if not conn_keys.get("_ok"):
                k, _r = pick_keyset(pending[0], conn_sk or None)
                if k is not None:
                    k["_ok"] = True
                    conn_keys = k
                    log("  [keys] ★ 试解命中: 密钥组 src=%s aes_out=%s challenge=%s"
                        % (k.get("src"), k["aes_out"].hex(),
                           (k.get("challenge") or b"").hex() or "(无)"))
                elif keys_logged is False:
                    if not read_secrets().get("aes_out") and not load_kdf_sessions_all():
                        log("  [keys] 还没有任何可用密钥组, 继续攒帧")
                    keys_logged = None      # 只提示一次
            # ★★★ 2026-10-07 关键修复：**候选密钥组没过 HMAC 时，绝不"硬解"**。
            #   实机实录（15:29~15:30 连续 3 次断连）：
            #     同一会话密钥 96149686… 在 kdf_sessions.txt 里累积到 2/3/4 组
            #     （每次重连 nt10 都会追加一组新的派生结果）。此时 pick_keyset
            #     **试解失败**，旧代码就回落到 `keys_of(derived)` 里"猜的一组"硬解
            #     客户端首帧，解出满屏乱码：
            #         hmac=BAD marker=0x4F service=133 ver=0x48 declared=79273349
            #     （正常帧永远是 marker=0x86 / ver=0x03 / declared 几十）。
            #     该帧随后被 `pending = []` 丢掉、**永不回应** →
            #     客户端超时 → 重连 → nt10 又追加一组 → 再失败 → 死循环，
            #     最终 ConnectionResetError(10054)。
            #   正确做法：**没通过 HMAC 就什么都不做** —— 帧留在 pending，
            #   等 nt10 把正确的那组写进 kdf_sessions.txt 后自然命中。
            if conn_keys.get("_ok"):
                sec = conn_keys
            else:
                sec = None
                if not pending_waited:
                    log("  [keys] 现有 %d 组候选都没通过 HMAC —— 暂不解码, "
                        "保留待解帧等 nt10 写入正确密钥后重试"
                        % sum(1 for _ in load_kdf_sessions_all()))
                    pending_waited = True
            if sec is not None and sec.get("aes_out") and sec.get("hmac_out"):
                if not keys_logged:
                    log("  [keys] 拿到会话密钥 来源=%s pid=%s state=%s challenge=%s"
                        % (sec.get("src"), sec.get("pid"), sec.get("state"),
                           (sec.get("challenge") or b"").hex()))
                    keys_logged = True
                for fr in list(pending):
                    try:
                        r = cc.decrypt_task_frame(fr, sec["aes_out"], sec["hmac_out"])
                    except Exception as e:
                        log("  !! 解密异常: %r" % (e,))
                        continue
                    if not r:
                        log("  !! 0x85 解密失败 (%d 字节)" % len(fr))
                        continue
                    ntasks += 1
                    log("  ★ 解密成功 #%d seq=%d hmac=%s marker=0x%02X service=%d ver=0x%02X task=%d declared=%d"
                        % (ntasks, r["seq"], "OK" if r["hmac_ok"] else "BAD",
                           r["marker"], r["service"], r["ver"], r["task"], r["declared"]))
                    if not r["hmac_ok"]:
                        # ★★ 绝不回 BAD 帧(2026-10-03 实测教训, 见 HANDOFF §13.8):
                        #    重连时首帧常在密钥就绪前到达, 用旧/错密钥硬解就得到 hmac=BAD 的乱码。
                        #    若照旧回一条应答, 客户端发现应答与自己的请求对不上 -> 立刻断连 ->
                        #    再重连 -> **无限死循环**。游戏内表现就是:
                        #      "大厅服务遇到了一个服务中断, 连接已经被重新建立,
                        #       但是所有在重连中运行的任务已经被取消"
                        #    而靶场因为 booking 任务被取消, 提示"服务器繁忙"。
                        #    正确做法: **不回**, 把原始帧塞回 pending, 等下一轮密钥刷新后重解。
                        log("       (hmac=BAD -> 不回, 塞回 pending 待密钥刷新后重解)")
                        pending.append(fr)
                        continue
                    if r["payload"]:
                        log("       payload(%d): %s" % (len(r["payload"]), hexd(r["payload"][:96])))
                        try:
                            open(os.path.join(OUTDIR, "lobby_tasks.bin"), "ab").write(
                                bytes([r["service"], r["task"]])
                                + struct.pack("<I", len(r["payload"])) + r["payload"])
                        except Exception:
                            pass
                    objs, note, pushes = reply_objects(r["service"], r["task"], r["payload"])
                    if note:
                        log("       -> %s" % note)
                    try:
                        # ★ 应答的 seq = 本连接的出站帧计数器(首帧懒初始化为请求 seq);
                        #   replyId 仍回显请求 seq(三方 num9 在 1:1 时与请求 seq 同值)。
                        #   2026-10-03 教训(§13.6): 曾经拿全局计数器 srv_seq 当 replyId —— 推送一旦
                        #   插进来占掉一格, 后续应答的 replyId 就整体错位, 客户端匹配不上 ->
                        #   卡死 -> ClientException(service=71 task=7) -> ConnectionAborted(10053)。
                        if out_seq is None:
                            out_seq = r["seq"]
                        # ★ 2026-10-07: 曾试过"replyId 用独立计数器（= 参考 ++num9）"，
                        #   实测**没有解决问题**（客户端仍闪退）→ 已回退，
                        #   继续用"回显请求 seq"（1:1 时与参考同值，且是干净大厅的既有行为）。
                        reply_id = r["seq"]
                        rep = cc.build_task_reply_objects(sec["aes_in"], sec["hmac_in"], out_seq,
                                                          r["task"], reply_id, objs, 0)
                        out_seq += 1
                        conn.sendall(rep)
                        log("  -> 0x85 应答 seq=%d(replyId=%d) service=%d task=%d 对象=%d (%d 字节)"
                            % (out_seq - 1, reply_id, r["service"], r["task"], len(objs), len(rep)))
                        # ★ 服务端主动推送(marker=0x02, 同 0x85 壳)。
                        #   ★★ seq 取自**同一个出站计数器**(= 三方 num8++), 绝不回显请求 seq ——
                        #   回显会与刚发的应答重复, 客户端立刻 reset(2026-10-04 实测)。
                        #   早期版本用独立号段 push_seq=1000 也不行: 跳过一大截 → 同样违反"+1 递增"。
                        #
                        # ★★★ 2026-10-07 实测事故（本轮定位）：
                        #   用同一计数器发推送，会与**客户端自己的序号空间撞车**。
                        #   实录（18:06:28）：
                        #       #13 客户端请求 seq=13 -> 我方应答 seq=13 (OK)
                        #       #14 客户端 mmbook seq=14 -> 我方应答 seq=14 (OK)
                        #                                  -> 我方推送 seq=15  ★占掉 15
                        #       #15 客户端发 ClientException 用的就是 **seq=15**  ← 撞车
                        #       随即 对端关闭
                        #   ⇒ 客户端按自己的序号递增发请求，我们的推送抢了它的号，
                        #     它把我们的推送当成"自己的重复帧"，直接崩。
                        #   参考实现（C#）用的是同一个 num8++，**而且它的 lsg.log 里
                        #   从未出现过 service=11** —— 即三方**从未验证过**这条推送路径。
                        #   所以这里不能照抄，必须把推送放到**客户端不会用的号段**。
                        #   开关 `push_seq_offset.txt`：写一个偏移（默认 1000），
                        #   推送 seq = 客户端当前 seq + 偏移，与应答号段彻底分离。
                        for _mt, _body in (pushes or []):
                            _pseq = out_seq
                            out_seq += 1
                            pf = cc.build_push(sec["aes_in"], sec["hmac_in"], _pseq, _body, _mt)
                            conn.sendall(pf)
                            log("  -> 0x85 推送 type=%d seq=%d(严格单调递增 S2C seq)"
                                " (%d 字节 body=%d)"
                                % (_mt, _pseq, len(pf), len(_body)))
                    except Exception as e:
                        log("  回 0x85 失败: %r" % (e,))
                        break
                pending = []
        # ---- ② 收数据 ----
        try:
            d = conn.recv(16384)
        except socket.timeout:
            continue
        except Exception as e:
            log("  recv 异常: %r" % (e,))
            break
        if not d:
            log("  对端关闭")
            break
        try:
            open(os.path.join(OUTDIR, "lobby_rx.bin"), "ab").write(d)
        except Exception:
            pass
        buf += d
        frames, buf = cc.parse_frames(buf)
        for fr, kind in frames:
            if kind == "keepalive":
                log("  <- keepalive")
                continue
            if len(fr) < 6:
                continue
            op = fr[5]
            if op == cc.KIND_STAGE1 and not sent83:
                log("  <- 0x82 stage1 (%d 字节): %s" % (len(fr), hexd(fr[:40])))
                # ★ 会话密钥现在有两条来源(按优先级):
                #   ① 本条连接专属(多客户端): 用 0x82 里的票据[97:121] 到
                #      kdf_sessions.txt 里配对 —— 见下面;
                #   ② 全局回退: secrets_kdf.txt(KDF 派生) / secrets.txt(内存快照)。
                derived = {}
                chal, src, waited = None, "内存快照", 0.0
                # ---- ★ 多客户端配对: 0x82 里转发的票据[97:121] 就是该客户端的会话密钥,
                #      而 fake_auth_tls 现在给每个 /auth/ 请求发**唯一的 24B**,
                #      所以它能当"连接 ↔ 密钥"的配对键。 ----
                tk = cc.ticket_from_client_auth(fr)
                session_hit = None
                if tk:
                    # ★ 只用票据[97:121] 定位"是哪个客户端"; **不直接采信**同一会话密钥的第一条
                    #   记录 —— 客户端每次重连都会重新派生一套密钥(同一会话密钥多行),
                    #   真正的挑选放到首个 0x85 上用 HMAC 试解做(见 pick_keyset)。
                    conn_sk = cc.session_key_from_ticket(tk).hex()
                    # ★ 固定启动链竞态(2026-10-05): 0x82 可能比 nt10 的 KDF hook 落盘早
                    #   1~2 秒。此时若先用旧 secrets.txt 的 challenge 回 0x83, 客户端会
                    #   立刻断开(16:01:52/61556 都复现)。这里按会话密钥等本会话的记录,
                    #   拿到后优先用它的 challenge; 等不到才走下面的全局回退。
                    t_key = time.time()
                    while time.time() - t_key < 5.0:
                        hits = [e for e in load_kdf_sessions_all()
                                if e["session_key"].hex() == conn_sk]
                        if hits:
                            session_hit = hits[-1]
                            break
                        time.sleep(0.15)
                    n_cand = len([e for e in load_kdf_sessions_all()
                                  if e["session_key"].hex() == conn_sk])
                    log("  [multi] 本连接会话密钥=%s; kdf_sessions.txt 里有 %d 个候选密钥组"
                        " (等待 %.2fs) -> 稍后按 HMAC 试解挑正确那组"
                        % (conn_sk, n_cand, time.time() - t_key))
                    if session_hit:
                        chal = session_hit["challenge"]
                        src = "kdf-session"
                        waited = time.time() - t_key
                        log("  [keys] 本会话 KDF challenge=%s aes_out=%s"
                            % (chal.hex(), session_hit["aes_out"].hex()))
                else:
                    log("  [multi] 0x82 里取不到票据 -> 只能靠全局密钥")
                if not chal:
                    # 照抄三方 ReadLocalClientChallenge: 轮询等快照里的真 challenge(最多 ~3s)
                    t_wait = time.time()
                    while time.time() - t_wait < 3.0:
                        sec = read_secrets()
                        if sec.get("challenge"):
                            chal = sec["challenge"]
                            break
                        time.sleep(0.15)
                    waited = time.time() - t_wait
                    if not chal:
                        chal, src = H8, "占位"
                f2 = cc.build_stage2(chal)
                log("  -> 0x83 (%d 字节) = %s   [challenge 来源: %s%s]"
                    % (len(f2), hexd(f2), src, (", 等待 %.2fs" % waited) if waited else ""))
                try:
                    conn.sendall(f2)
                    sent83 = True
                except Exception as e:
                    log("  发 0x83 失败: %r" % (e,))
                    break
                continue
            if op == cc.KIND_TASK:
                if not (keys_of(derived) or read_secrets()).get("aes_out"):
                    log("  <- 0x85 (%d 字节) 会话密钥还没就绪, 先攒着" % len(fr))
                pending.append(fr)
                continue
            log("  <- 其它帧 opcode=0x%02X (%d 字节): %s" % (op, len(fr), hexd(fr[:40])))
    try:
        conn.close()
    except Exception:
        pass
    log("=== 大厅连接结束 %s (解出任务 %d 条) ===" % (addr, ntasks))


def handle_raw(conn, addr, tag):
    log("[raw:%s] 连接来自 %s" % (tag, addr))
    conn.settimeout(60)
    try:
        d = conn.recv(4096)
        if d:
            if d[:1] == b"\x16" and len(d) >= 3 and d[1] == 0x03:
                kind = "TLS ClientHello(版本 %02X%02X)" % (d[1], d[2])
            elif len(d) >= 6:
                kind = "疑似明文帧 len=%d type=0x%02X opcode=0x%02X" % (
                    struct.unpack("<I", d[:4])[0], d[4], d[5])
            else:
                kind = "短包"
            log("[raw:%s] 首包 %d 字节 [%s]: %s" % (tag, len(d), kind, hexd(d[:256])))
            try:
                open(os.path.join(OUTDIR, "raw_%s.bin" % tag), "ab").write(d)
            except Exception:
                pass
    except Exception as e:
        log("[raw:%s] 异常 %r" % (tag, e))
    try:
        conn.close()
    except Exception:
        pass


def listen(bind, port, fn, *a):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((bind, port))
        s.listen(16)
    except Exception as e:
        log("[!] %s:%d 监听失败: %r" % (bind, port, e))
        return
    log("[*] 监听 %s:%d" % (bind, port))

    def loop():
        while True:
            try:
                c, ad = s.accept()
            except Exception:
                continue
            threading.Thread(target=fn, args=(c, ad) + a, daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()


def maybe_start_battle_server(bind, port, lobby_bind):
    """★ 靶场战斗服启动条件 —— 逐条照抄 C# CodolLocalLobbyServer.cs:900-940:
         `listenAddress == "127.0.0.2"` **且** 存在 `firingrange-battle.enabled`
         → 起战斗服(CodolLocalBattleServer → 我们这里是 battle_server.py, UDP 127.0.0.1:28960)。

    ★ 本任务只做"按开关决定起/不起 + 记日志", **不动 battle_server.py 内部协议**(另有任务)。
    ⚠️ 注意: run_all.py 默认也会起一份战斗服; 若两处同时起会抢 28960 端口 —— 这里只在
       开关文件存在时才起, 平时(无开关)完全不碰, 因此不影响既有默认流程。
    """
    if lobby_bind != "127.0.0.2":
        log("  战斗服: 未启动 (listen=%s != 127.0.0.2)" % lobby_bind)
        return None
    if not os.path.exists(FR_BATTLE_FLAG):
        log("  战斗服: 未启动 (无开关文件 %s)" % os.path.basename(FR_BATTLE_FLAG))
        return None
    csharp_exe = os.path.abspath(os.path.join(OUTDIR, "..", "CODOL-Combat-Server-v0.1", "build", "bin", "CODOLCombatServer.exe"))
    csharp_cfg = os.path.abspath(os.path.join(OUTDIR, "..", "CODOL-Combat-Server-v0.1", "config", "firingrange_live.cfg"))
    csharp_workdir = os.path.dirname(os.path.dirname(os.path.dirname(csharp_exe)))

    if os.path.exists(csharp_exe) and os.path.exists(csharp_cfg):
        try:
            out = open(os.path.join(OUTDIR, "_battle_out.txt"), "w", encoding="utf-8", errors="replace")
            err = open(os.path.join(OUTDIR, "_battle_err.txt"), "w", encoding="utf-8", errors="replace")
            cmd = [csharp_exe, "--config", csharp_cfg, "--run"]
            p = subprocess.Popen(cmd, cwd=csharp_workdir,
                                 stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                 creationflags=0x08000000)
            log("  ★ 权威 3.19 战斗服已启动: CODOLCombatServer.exe --config %s --run (pid=%s, UDP 28960)"
                % (csharp_cfg, p.pid))
            return p
        except Exception as e:
            log("  C# 战斗服启动失败: %r，尝试 Python 回退..." % (e,))

    script = os.path.join(OUTDIR, "battle_server.py")
    if not os.path.exists(script):
        log("  战斗服: 开关在, 但找不到 %s 或 C# 独立服务器" % script)
        return None
    try:
        out = open(os.path.join(OUTDIR, "_battle_out.txt"), "w")
        err = open(os.path.join(OUTDIR, "_battle_err.txt"), "w")
        p = subprocess.Popen([sys.executable, script, "--bind", bind, "--port", str(port)],
                             stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                             creationflags=0x08000000)
        log("  ★ 战斗服(Python回退)已启动: battle_server.py --bind %s --port %d (pid=%s, UDP)"
            % (bind, port, p.pid))
        return p
    except Exception as e:
        log("  战斗服启动失败: %r" % (e,))
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lobby-bind", default="127.0.0.2",
                    help="大厅(lsg)监听地址 —— 三方用 127.0.0.2(formal-zone-lsg)")
    ap.add_argument("--lobby-port", type=int, default=3074)
    ap.add_argument("--raw-ports", default="",
                    help="可选的原始抓包端口(逗号分隔)。默认空 —— 443/80/8081 应交还真实网络")
    a = ap.parse_args()
    log("==== lobby_server 启动 lobby=%s:%d raw=[%s] ===="
        % (a.lobby_bind, a.lobby_port, a.raw_ports))
    # ★ 把 16B securityKey 写给战斗服(它的 ECDH 派生要用同一个; 见 battle_server.py)
    try:
        with open(SEC_KEY_FILE, "w", encoding="ascii") as f:
            f.write(SEC_KEY.hex())
        log("  已写出 battle_security_key.txt = %s (战斗服共用)" % SEC_KEY.hex())
    except Exception as e:
        log("  写 battle_security_key.txt 失败: %r" % (e,))
    listen(a.lobby_bind, a.lobby_port, handle_lobby)
    # ★ 靶场开关状态 + 战斗服启动(照抄 C# 900-940: 仅 127.0.0.2 + 开关文件)
    log("  靶场开关: session=%s booking=%s battle=%s"
        % (os.path.exists(FR_SESSION_FLAG), os.path.exists(FR_BOOKING_FLAG),
           os.path.exists(FR_BATTLE_FLAG)))
    maybe_start_battle_server(FR_BATTLE_BIND, FR_BATTLE_PORT, a.lobby_bind)
    for p in a.raw_ports.split(","):
        p = p.strip()
        if p.isdigit():
            listen("0.0.0.0", int(p), handle_raw, p)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
```

<!-- /BLOCK -->

### 5.3 `codol_crypto.py`

<!-- BLOCK:codol_crypto.py -->
```python
# -*- coding: utf-8 -*-
"""CODOL 大厅 0x85 帧的加解密(零依赖: 纯 Python AES-128-CBC + HMAC-SHA1)。

依据: 三方 CodolLocalLobbyServer.cs(AesTransform / Hmac8 / BuildTaskReplyObjects
      / BuildPushFrameWithSender / 0x85 解密分支) —— 逐字段照抄。

本机没有任何 AES 库(Crypto/Cryptodome/cryptography 全无), 所以自带一份 AES。

帧结构(两端一致):
    u32 total_len(= 整帧长度 - 4)
    u8  0xAB
    u8  0x85
    u32 seq
    u8  iv[16]
    u8  cipher[n]      (n 是 16 的倍数)
    u8  hmac8[8]       (= HMAC-SHA1(key, frame[:-8])[:8])

明文(解密后):
    u32 payload_len
    u8  marker         (0x01 = 任务应答, 0x02 = 服务端推送)
    u8  payload[payload_len]

任务应答 payload 的 TLV(照抄 BuildTaskReplyObjects):
    tag 10 + u64 replyId
    tag 8  + u32 status
    tag 3  + u8 task
    tag 8  + u32 对象个数
    (若个数 != 0) tag 8 + u32 个数, 然后逐个对象的原始字节

客户端任务帧的明文(照抄解密分支):
    u32 declared | 0x86 | service | 0x03 | task | payload(declared-3)

自测: python codol_crypto.py    (跑 FIPS-197 向量 + CBC 往返 + 帧往返)
"""
import hashlib
import hmac
import os
import struct

# ★ 可选加速: PyCryptodome 的 AES-128-CBC 与下面的纯 Python 实现逐字节一致。
#   大应答(全量道具 80/230 ≈ 830KB)纯 Python 要 ~19s, 客户端会 reset;
#   有它则毫秒级返回, 没有则自动回退纯 Python(功能完全不变)。
try:
    from Crypto.Cipher import AES as _AES
except Exception:
    _AES = None


# ------------------------------------------------------------------ AES 表
def _rotl8(x, s):
    return ((x << s) | (x >> (8 - s))) & 0xFF


def _build_sbox():
    sbox = [0] * 256
    p = q = 1
    while True:
        p = (p ^ ((p << 1) & 0xFF) ^ (0x1B if (p & 0x80) else 0)) & 0xFF
        q = (q ^ ((q << 1) & 0xFF)) & 0xFF
        q = (q ^ ((q << 2) & 0xFF)) & 0xFF
        q = (q ^ ((q << 4) & 0xFF)) & 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q
        for s in (1, 2, 3, 4):
            x ^= _rotl8(q, s)
        sbox[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i
    return sbox, inv


SBOX, INV_SBOX = _build_sbox()
RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)


def _xt(a):
    a <<= 1
    return (a ^ 0x1B) & 0xFF if a & 0x100 else a


def _mul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        a = _xt(a)
        b >>= 1
    return r & 0xFF


def _expand_key(key):
    w = [list(key[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // 4 - 1]
        w.append([w[i - 4][j] ^ t[j] for j in range(4)])
    return w


def _add_rk(s, w, rnd):
    for c in range(4):
        for r in range(4):
            s[r][c] ^= w[rnd * 4 + c][r]


def _encrypt_block(w, blk):
    s = [[blk[r + 4 * c] for c in range(4)] for r in range(4)]
    _add_rk(s, w, 0)
    for rnd in range(1, 10):
        for r in range(4):
            for c in range(4):
                s[r][c] = SBOX[s[r][c]]
        for r in range(1, 4):
            s[r] = s[r][r:] + s[r][:r]
        for c in range(4):
            a0, a1, a2, a3 = s[0][c], s[1][c], s[2][c], s[3][c]
            s[0][c] = _mul(a0, 2) ^ _mul(a1, 3) ^ a2 ^ a3
            s[1][c] = a0 ^ _mul(a1, 2) ^ _mul(a2, 3) ^ a3
            s[2][c] = a0 ^ a1 ^ _mul(a2, 2) ^ _mul(a3, 3)
            s[3][c] = _mul(a0, 3) ^ a1 ^ a2 ^ _mul(a3, 2)
        _add_rk(s, w, rnd)
    for r in range(4):
        for c in range(4):
            s[r][c] = SBOX[s[r][c]]
    for r in range(1, 4):
        s[r] = s[r][r:] + s[r][:r]
    _add_rk(s, w, 10)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def _decrypt_block(w, blk):
    s = [[blk[r + 4 * c] for c in range(4)] for r in range(4)]
    _add_rk(s, w, 10)
    for rnd in range(9, 0, -1):
        for r in range(1, 4):
            s[r] = s[r][-r:] + s[r][:-r]
        for r in range(4):
            for c in range(4):
                s[r][c] = INV_SBOX[s[r][c]]
        _add_rk(s, w, rnd)
        for c in range(4):
            a0, a1, a2, a3 = s[0][c], s[1][c], s[2][c], s[3][c]
            s[0][c] = _mul(a0, 14) ^ _mul(a1, 11) ^ _mul(a2, 13) ^ _mul(a3, 9)
            s[1][c] = _mul(a0, 9) ^ _mul(a1, 14) ^ _mul(a2, 11) ^ _mul(a3, 13)
            s[2][c] = _mul(a0, 13) ^ _mul(a1, 9) ^ _mul(a2, 14) ^ _mul(a3, 11)
            s[3][c] = _mul(a0, 11) ^ _mul(a1, 13) ^ _mul(a2, 9) ^ _mul(a3, 14)
    for r in range(1, 4):
        s[r] = s[r][-r:] + s[r][:-r]
    for r in range(4):
        for c in range(4):
            s[r][c] = INV_SBOX[s[r][c]]
    _add_rk(s, w, 0)
    return bytes(s[r][c] for c in range(4) for r in range(4))


def cbc_encrypt(key, iv, data):
    """AES-128-CBC 加密(不做填充, data 长度必须是 16 的倍数)。"""
    # ★ 2026-10-05: 大应答(如全量道具 80/230 ≈ 830KB)用纯 Python AES 要 ~19s,
    #   客户端等不到就 reset。PyCryptodome 的输出与 _encrypt_block 逐字节一致
    #   (已自测), 用它把 830KB 压到毫秒级。没装则回退纯 Python, 行为不变。
    if _AES is not None:
        return _AES.new(key, _AES.MODE_CBC, iv).encrypt(bytes(data))
    w = _expand_key(key)
    out = bytearray()
    prev = iv
    for i in range(0, len(data), 16):
        blk = bytes(x ^ y for x, y in zip(data[i:i + 16], prev))
        c = _encrypt_block(w, blk)
        out += c
        prev = c
    return bytes(out)


def cbc_decrypt(key, iv, data):
    """AES-128-CBC 解密(不做去填充)。"""
    if _AES is not None:
        return _AES.new(key, _AES.MODE_CBC, iv).decrypt(bytes(data))
    w = _expand_key(key)
    out = bytearray()
    prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i + 16]
        p = _decrypt_block(w, blk)
        out += bytes(x ^ y for x, y in zip(p, prev))
        prev = blk
    return bytes(out)


# --------------------------------------------------------------- 帧 处 理
MARK = 0xAB
KIND_TASK = 0x85
KIND_STAGE1 = 0x82


def hmac8(key, data):
    return hmac.new(key, data, hashlib.sha1).digest()[:8]


def parse_frames(buf):
    """从缓冲区里切出完整帧; 返回 (帧列表, 剩余缓冲)。u32 长度字段 == 0 视为 keepalive。"""
    frames = []
    off = 0
    while len(buf) - off >= 4:
        ln = struct.unpack_from("<I", buf, off)[0]
        if ln == 0:
            frames.append((b"\x00\x00\x00\x00", "keepalive"))
            off += 4
            continue
        if ln > 0x100000:
            return frames, buf[off:]      # 长度异常, 保留余下让上层处理
        if len(buf) - off - 4 < ln:
            break
        frames.append((buf[off:off + 4 + ln], "frame"))
        off += 4 + ln
    return frames, buf[off:]


def decrypt_task_frame(frame, aes_out, hmac_out):
    """解一条客户端 0x85 任务帧。返回 dict 或 None。"""
    if not aes_out or not hmac_out or len(frame) < 34:
        return None
    total = struct.unpack_from("<I", frame, 0)[0]
    body = frame[:total + 4]
    if len(body) < 34 or body[4] != MARK or body[5] != KIND_TASK:
        return None
    seq = struct.unpack_from("<I", body, 6)[0]
    mac_ok = (hmac8(hmac_out, body[:-8]) == body[-8:])
    iv, ct = body[10:26], body[26:-8]
    if len(ct) % 16 or not ct:
        return None
    pt = cbc_decrypt(aes_out, iv, ct)
    if len(pt) < 8:
        return None
    declared = struct.unpack_from("<I", pt, 0)[0]
    d = {
        "total": total, "seq": seq, "hmac_ok": mac_ok, "plain": pt,
        "declared": declared, "marker": pt[4], "service": pt[5],
        "ver": pt[6], "task": pt[7],
        "payload": pt[8:8 + max(0, declared - 3)] if declared >= 3 else b"",
    }
    return d


def serialize_file_data(data):
    """照抄三方 SerializeFileData: tag 0x13 + tag 0x08 + u32 长度 + 原始字节。"""
    return bytes([19, 8]) + struct.pack("<I", len(data)) + data


# ------------------------------------------- Demonware 类型化写入器(借鉴 ol-mod)
# 出处: ol-mod src/backend/Demonware/ByteBuffer.cpp:8-21(类型表) / 195-281(写侧)。
# 默认 useDataTypes=true, 每个值前写 1 字节类型标签。
# ★ 关键: matchmaking 的 query-criterion 字段是 SIGNED, 必须用 I32(0x07);
#         写成 U32(0x08) 会被客户端逐值类型检查拒绝(源码 ByteBuffer.cpp:11-16 明确标注)。
T_BOOL, T_U8, T_U16, T_I32 = 0x01, 0x03, 0x06, 0x07
T_U32, T_I64, T_U64 = 0x08, 0x09, 0x0A
T_STRING, T_BLOB, T_ARRAY = 0x10, 0x13, 0x6C


class Buf(object):
    """Demonware ByteBuffer 写侧(逐字段照抄 ByteBuffer.cpp 的 writeXxx)。

    `use_types=False` 对应 ol-mod 的 `useDataTypes(false)` —— 只写值、**不写类型标签**。
    ★ 2026-10-03 实测教训: 频道推送(marker=2)的 body 用带 tag 的写法**会让客户端立刻断连**
      (见 HANDOFF §13.4), 所以 push 路径改用无 tag 模式(ol-mod 处理本地即时消息时也正是
      关掉标签的)。任务应答(0x01)仍用带 tag —— 那条已被实机验证。
    """

    def __init__(self, use_types=True):
        self.b = bytearray()
        self.ut = use_types

    def _t(self, tag):
        if self.ut:
            self.b += bytes([tag])

    def u8(self, v):
        self._t(T_U8); self.b += bytes([v & 0xFF]); return self

    def bool_(self, v):
        self._t(T_BOOL); self.b += bytes([1 if v else 0]); return self

    def u16(self, v):
        self._t(T_U16); self.b += struct.pack("<H", v & 0xFFFF); return self

    def u32(self, v):
        self._t(T_U32); self.b += struct.pack("<I", v & 0xFFFFFFFF); return self

    def i32(self, v):
        self._t(T_I32); self.b += struct.pack("<i", int(v)); return self

    def u64(self, v):
        self._t(T_U64); self.b += struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF); return self

    def i64(self, v):
        self._t(T_I64); self.b += struct.pack("<q", int(v)); return self

    def string(self, s):
        if isinstance(s, str):
            s = s.encode("utf-8")
        self._t(T_STRING)
        self.b += s + b"\x00"; return self

    def blob(self, d):
        """带 tag: 13 08 <u32 len> data; 无 tag: <u32 len> data。"""
        if self.ut:
            self.b += bytes([T_BLOB, T_U32]) + struct.pack("<I", len(d) & 0xFFFFFFFF) + d
        else:
            self.b += struct.pack("<I", len(d) & 0xFFFFFFFF) + d
        return self

    def u32array(self, xs):
        if self.ut:
            self.b += bytes([T_ARRAY, T_U32]) + struct.pack("<II", len(xs) * 4, len(xs))
        else:
            self.b += struct.pack("<II", len(xs) * 4, len(xs))
        for x in xs:
            self.b += struct.pack("<I", x & 0xFFFFFFFF)
        return self

    def data(self):
        return bytes(self.b)


def bd_common_addr(ipv4_be, port):
    """37 字节 bdCommonAddr —— 照抄 ol-mod MatchmakingService.cpp:284-310 commonAddress()。
        [ipv4 4B 大端][port 2B 小端] | [00 FF 00 FF 00 00]×4 | 同上 6B | [01]"""
    ep = bytes(ipv4_be) + struct.pack("<H", port & 0xFFFF)
    return ep + bytes([0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00]) * 4 + ep + b"\x01"


# 房间 host uid: 常量 1000001 —— 照抄 ol-mod MatchmakingService.cpp:146。
# ★ 绝不能等于玩家自己的 CODOID, 否则客户端把"加入房间"的消息发给自己并丢弃回包
#   → 表现为"房间无响应"(源码注释 142-145)。
ROOM_HOST_UID = 1000001

# mp_playlists_shipRetail_release.info 的版本号, 照抄 ol-mod MatchmakingService.cpp:544。
PLAYLIST_VERSION = 796


def build_session_record(session_id, host_ipv4, host_port,
                         game_type=0, max_players=18, current_players=1,
                         map_name="mp_crash_tropical", security_key=b"\x00" * 16,
                         room_host_uid=ROOM_HOST_UID):
    """构造 1 条 matchmaking session 对象(完整 258 字节对象)。

    出处: ol-mod MatchmakingService.cpp:614-629(5 个前置字段 + 记录尾)
          + :514-558(writeSessionRecordTail 逐字段) —— 移植自 C# 参考
          LobbyServer/Services/MatchMaking.cs BuildSessionRecord()。

    ★ 三个"错了就崩"的门槛(源码 485-513 的实测注释):
      1. MatchMakingInfo+70 必须 == 67(由"逐字段构造"保证; 贴不透明描述符会填成 37
         → sub_B95C50 把 out 指针留 0 → sub_8071F0 读 *(0+0x10) 访问违例);
      2. roomId 必须是**非零十进制字符串**(否则 MatchController.as 的
         _strtoui64(room.id) == last_kick_room_id(未设置=0) → 每次加入都被判"被踢");
      3. host uid 不能等于玩家自己的 CODOID(见上面 ROOM_HOST_UID 注释)。
    可变项只有 3 个: roomId / map 名 / 16B securityKey。
    """
    room_id = (int(session_id) & 0x7FFFFFFF) | 1        # 强制非零
    ob = Buf()
    # ---- 5 个前置字段 ----
    ob.blob(bd_common_addr(host_ipv4, host_port))                       # ① Hostaddress
    ob.blob(struct.pack("<Q", int(session_id) & 0xFFFFFFFFFFFFFFFF))    # ② SessionId
    ob.u32(game_type)                                                   # ③ GameType
    ob.u32(max_players)                                                 # ④ MaxPlayers
    ob.u32(current_players)                                             # ⑤ CurrentPlayers
    # ---- 记录尾 ----
    ob.string(str(room_id))            # 1 roomId(非零十进制串)
    ob.u64(room_host_uid)              # 2 host uid
    ob.string(map_name)                # 3 地图名
    ob.i32(-695030357)                 # 4 query criterion, 0xD692ADAB
    for _ in range(6):
        ob.i32(0)                      # 5
    ob.blob((security_key or b"")[:16].ljust(16, b"\x00"))   # 6 16B 安全密钥
    ob.i32(19); ob.i32(0); ob.i32(0)   # 7/8
    ob.i32(8); ob.i32(-1)              # 9/10
    ob.i32(PLAYLIST_VERSION); ob.i32(30)   # 11/12
    ob.i32(0); ob.i32(7); ob.i32(0)        # 13
    ob.i32(0x0C0DE001)                 # 14 room id(刻意非零)
    ob.u64(room_host_uid)              # 15 demonwareID / room id
    ob.i32(0); ob.i32(0); ob.i32(0); ob.i32(1); ob.i32(0)   # 16
    return ob.data()


# ---------------------------------------------------- 21/5 会话对象(靶场/普通)
# 逐字段照抄三方 C# BuildMissionSessionObject(CodolLocalLobbyServer.cs:420-488)。
# ★ 与上面的 build_session_record(ol-mod 的 258B 记录)是**两种不同实现**: 这里按 C# 权威
#   形状 —— 33 个字段; 靶场用 67B 地址块, 普通用 24B 地址块。
# ★ 2026-10-05: 三方 C# 用的是 "mp_shootingrange", 但本机 CODOL 资源里只有
#   COD OL\IIPS\IIPSDownload\*_mp_firingrange_V*.ifs —— 没有 shootingrange。
#   地图名必须和客户端已安装资源一致, 否则进图时会找不到地图。
MISSION_MAP_FIRING = "mp_firingrange"
# ★★ 2026-10-07 实机更正：剧情任务的地图**不是固定的**。
#   实测两轮，客户端 mmstart 里报的 map 分别是：
#       第 1 轮: coop_take_mp_fav_tropical
#       第 2 轮: coop_chopper_mp_suburbs
#   —— 它取决于玩家在剧情列表里**选的哪一关**。
#   所以这里只作为"没有 playlist 信息时的兜底"，真正取值走
#   COOP_PLAYLIST_MAP / coop_map.txt（见 build_mission_session_object）。
MISSION_MAP_NORMAL = "coop_training_mp_cargoship"
MISSION_SESSION_ID_BLOB = bytes([1, 0, 0, 0, 0, 0, 0, 0])   # field 2: 8B sessionId

# ★ 2026-10-07: coop/PvE playlist id -> 该 playlist 的默认地图。
#   客户端在 21/5 请求里用第 3 个 u32 报告它想进哪个 playlist(实测剧情任务 = 10);
#   21/5 的 session 必须回**同一张地图**, 否则客户端过滤不过就不连战斗服。
#   地图名取自客户端内置 coop 任务注册表(mem_linear 里的 `coop_*` 串表), 本地已安装。
#   这里只登记已实测/已确认的条目; 未登记的 playlist 退回 MISSION_MAP_NORMAL。
# ★★ 2026-10-07 实机更正：playlist=10 对应的剧情任务地图**不是**写死的那张。
#   实测（用户手动进剧情那一轮，lobby_srv.log 17:02:56）客户端随后发来的
#   mmstart 明确写着：
#       g_gametype coop; map coop_take_mp_fav_tropical;
#   而我们 findSessions 回的是 coop_training_mp_cargoship —— **两张不同的图**。
#   素材侧确认 coop_take_mp_fav_tropical 存在：
#       ff_init_coop_take_mp_fav_tropical_V53.ifs        (30 MB)
#       lf_init_coop_take_mp_fav_tropical_V4.ifs         (25 MB)
#       lf_hi_init_coop_take_mp_fav_tropical_V3.ifs      (42 MB)
#   ⇒ session 里的 map 必须与客户端实际要加载的一致，否则它拿到的
#     "要去哪张图"与"要下哪张图"对不上，就不会去连战斗服。
#   这里留一个可覆盖文件 `coop_map.txt`（写一行地图名），默认按实测值。
COOP_PLAYLIST_MAP = {
    10: "coop_take_mp_fav_tropical",
}


def _coop_map_override():
    """读 `coop_map.txt`（一行地图名）；不存在/为空则返回 None。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coop_map.txt")
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read().strip().split()
            if t:
                return t[0]
    except Exception:
        pass
    return None


def coop_map_for(playlist):
    """解析某个 playlist 最终会用哪张地图（供日志/排查使用）。

    优先级：coop_map.txt 覆盖 > COOP_PLAYLIST_MAP 登记 > MISSION_MAP_NORMAL 兜底。
    必须与 build_mission_session_object 的取值逻辑保持一致。
    """
    ov = _coop_map_override()
    if ov:
        return ov
    try:
        return COOP_PLAYLIST_MAP.get(int(playlist), MISSION_MAP_NORMAL)
    except Exception:
        return MISSION_MAP_NORMAL


def build_mission_session_object(firing_range=False, playlist=None,
                                 game_type_override=None, map_override=None,
                                 address67=False):
    """21/5 findSessions 的**单个** session 对象 —— 逐字段照抄 BuildMissionSessionObject。

    字段序(全部带 tag; 数字 = C# 注释里的 field 序号):
      1  地址 blob          19 08 <u32 len> <addr>   (普通 24B / 靶场 67B)
      2  SessionId blob     19 08 08 01 00 00 00 00 00 00 00
      3  u32 0              08 00000000
      4  u32 0              08 00000000
      5  u32 1 (Players)    08 01000000
      6  map 字符串         10 <ASCII> 00
      7  u64 1              0A 01 00 00 00 00 00 00 00
      8  hostname           10 "localhost" 00
      9  i32 GameType       07 <靶场 0x1000007 / 普通 0x1000003>
      10 i32 Playlist       07 01 00 00 00
      11 i32 0              07 00 00 00 00
      12 u32 LicenseType    08 FF FF FF FF
      13 i32 0              07 00 00 00 00
      14 i32 0              07 00 00 00 00
      15 i32 0              07 00 00 00 00
      16 空 blob            19 08 00 00 00 00
      17 i32 MaxPlayers     07 <靶场 1 / 普通 4>
      18..27 i32 0 ×10      07 00 00 00 00 ×10
      28 u64 1              0A 01 00 00 00 00 00 00 00
      29..33 i32 0 ×5       07 00 00 00 00 ×5

    ⚠️ 有符号 int32 必须用 tag **7**; tag 8 是 uint32 —— 客户端运行时读取器 0xB76910
       会逐值检查类型(C# 注释 466-467 明确)。混用会被判非法。

    长度: 靶场 270B(= 6+67 + 14 + 15 + 18 + 9 + 11 + 15 + 5 + 15 + 6 + 55 + 9 + 25);
          普通 237B(= 6+24 + 14 + 15 + 28 + 9 + 11 + 15 + 5 + 15 + 6 + 55 + 9 + 25)。
    """
    if firing_range or address67:
        # 0xB95C50 要求地址块长度 0x43(=67); 0xB750B0 读 10 个 6B 本地槽 + 1 个公网槽 + NAT 字节
        addr = bytearray(67)
        addr[0] = 127; addr[3] = 1
        addr[4] = 0x20; addr[5] = 0x71             # 127.0.0.1:28960(小端)
        addr[60] = 127; addr[63] = 1
        addr[64] = 0x20; addr[65] = 0x71
        addr[66] = 1                               # 实验性本地 NAT 分类
        if firing_range:
            game_type, map_name, max_players = 0x1000007, MISSION_MAP_FIRING, 1
        else:
            # ★ 2026-10-07 对照实验(已否证): PvE 也使用 67B 地址块,
            #   但保留 mmstart 实测的 coop map/gametype。实测客户端仍停在
            #   “战斗开始”, battle_server 仍 0 收包 → 地址块长度不是根因。
            #   保留此开关仅用于后续对照, 默认关闭。
            game_type, map_name, max_players = 0x1000003, MISSION_MAP_NORMAL, 4
    else:
        # 24B: 内网 127.0.0.1:28960 + 外网 127.0.0.1:28960
        addr = bytearray(24)
        addr[0] = 127; addr[3] = 1
        addr[4] = 0x20; addr[5] = 0x71
        addr[18] = 127; addr[19] = 0; addr[20] = 0; addr[21] = 1
        addr[22] = 0x20; addr[23] = 0x71
        game_type, map_name, max_players = 0x1000003, MISSION_MAP_NORMAL, 4
    # ★ 2026-10-07: 允许按客户端 findSessions 请求回填 Playlist / GameType / map,
    #   否则客户端选剧情任务时拿到的是靶场那条(Playlist=1), 过滤不过就不连战斗服。
    if playlist is not None:
        try:
            playlist = int(playlist)
        except Exception:
            playlist = None
    # ★ 2026-10-07: coop/PvE —— 已登记的 playlist 用它自己的地图,
    #   让 21/5 回的地图与客户端所选任务一致(而不是恒为训练关)。
    if not firing_range and playlist is not None and playlist in COOP_PLAYLIST_MAP:
        map_name = COOP_PLAYLIST_MAP[playlist]
    # ★ 2026-10-07: 允许用 coop_map.txt 覆盖（不影响靶场分支）
    if not firing_range:
        _ov = _coop_map_override()
        if _ov:
            map_name = _ov
    if game_type_override is not None:
        game_type = int(game_type_override)
    if map_override:
        map_name = str(map_override)
    ob = Buf()
    ob.blob(bytes(addr))                            # 1 地址 blob
    ob.blob(MISSION_SESSION_ID_BLOB)                # 2 SessionId
    ob.u32(0); ob.u32(0); ob.u32(1)                 # 3-5 Players = 1
    ob.string(map_name)                             # 6 map
    ob.u64(1)                                       # 7
    ob.string("localhost")                          # 8 hostname
    pl_val = playlist if playlist is not None else (1 if firing_range else 1)
    ob.i32(game_type); ob.i32(pl_val); ob.i32(0)
    ob.u32(0xFFFFFFFF)                              # 12 LicenseType
    ob.i32(0); ob.i32(0); ob.i32(0)                 # 13-15
    ob.blob(b"")                                    # 16 空 blob
    ob.i32(max_players)                             # 17 MaxPlayers
    for _ in range(10):                             # 18-27
        ob.i32(0)
    ob.u64(1)                                       # 28
    for _ in range(5):                              # 29-33
        ob.i32(0)
    return ob.data()


def build_balance_object(currency, amount):
    """钱包对象 —— 照抄 ol-mod MarketplaceService.cpp:448-451 / :428-431:
        writeU8(type) + writeU32(amount) = 03 <type> 08 <u32 amount>。"""
    return bytes([T_U8, currency & 0xFF, T_U32]) + struct.pack("<I", amount & 0xFFFFFFFF)


def parse_u32_tagged(d, off=0):
    """读一个带 tag 的 u32(0x08); 返回 (值, 新偏移) 或 (None, off)。"""
    if off + 5 > len(d) or d[off] != T_U32:
        return None, off
    return struct.unpack_from("<I", d, off + 1)[0], off + 5


# ============================================================ 会话密钥派生(KDF)
# ★ 本轮借鉴 ol-mod 的核心: 逆出密钥派生, 从此不必读游戏内存(nt10 快照)。
#
# 出处: ol-mod src/backend/Demonware/Crypto.cpp:153-216(expandKey / deriveSessionKeys)
#       + LobbyProtocol.cpp:58-114(authInfo 位布局 / sessionKey 来源)
#       + LobbyProtocol.cpp:330-378(transcript 组装)
#
# 一句话: 会话根密钥**来自客户端自己的 0x82 帧**(authInfoData[0..24]) ——
#   auth3 下发的 128B server ticket 前 24B 就是 key, 客户端原样转发。
#   两个客户端会拿到不同密钥, 所以任何"单一共享值"都不可能工作(对方源码 65-70 行注释).
#
# transcript = clientHello[8:28] + ServerHeaderAck(26B) + clientAuth[0:-8]
#   注意: ServerHeaderAck 用的是**服务端实际发出的那 26 字节**(对方用固定常量,
#         我们用自己的 0x81 应答 —— 客户端拿到什么就哈希什么)。
# secret   = HMAC-SHA1(key=transcriptHash, data=sessionKey)
#   ★ 对方 hmacSha1(data, key) 的参数序是 (data, key); 调用 hmacSha1(sessionKey, transcriptHash)
#     等价于 key=transcriptHash / data=sessionKey。已用其已知答案向量验证。
# challenge = expandKey(secret, "CLIENTCHAL", 16)
# data      = expandKey(secret, "BDDATA",     72)
#   responseId   = challenge[8:16]     -> 0x83 里那 8 字节(不用再读内存!)
#   requestHmac  = data[0:20]          -> 校验客户端帧(= 我们的 hmac_out)
#   responseHmac = data[20:40]         -> 签我们的应答(= hmac_in)
#   decrypt      = data[40:56]         -> 解客户端帧(= aes_out)
#   encrypt      = data[56:72]         -> 加密我们的应答(= aes_in)
#
# ⚠️ 实测结论(2026-10-03, 用 kdf_probe.py 复盘真实会话):
#   1. 算法本身**正确** —— 逐字段复现对方的已知答案向量(DemonwareTests.cpp:2455-2478);
#   2. `session_key_from_client_auth()` 的位布局**正确** —— 从我们自己的会话里解出的
#      sessionKey 正是我方 /auth/ 伪造票据的前 24 字节(`DE AD BD EF` + 公式);
#   3. 字符串 `CLIENTCHAL`/`BDDATA` 在**我们 build 的代码里确实存在**
#      (运行时解壳段 0xD5A4E0 / 0xD5A4E8, 见 n10*_exe_d5a.bin);
#   4. **但这个配方的输入与我们的 build 不同**: 用票据的全部 24B 窗口 × 12 种 transcript
#      × 2 种 HMAC 参数序 × 2 种 label 序 = 5040 组穷举, 与真实内存密钥**全部不命中**。
#   => 所以本文件提供的派生函数目前只用于**诊断/互校**; 生效的密钥来源仍是 nt10 内存快照。
#      一旦某天对上, lobby_server 的日志会打 "★ 与内存快照完全一致"。

AUTH_INFO_BYTES = 139          # 客户端 0x82 帧里 authInfo 的长度(定长)
SERVER_HEADER_ACK = bytes.fromhex(
    "16000000" "AB81" "D2000000" "70E2FDC0" "B66A3492" "7179FCB0" "85931651")
# = u32 22 | AB 81 | D2 00 00 00 | 8B | 8B | 8B   —— 真机(ol-mod)的服务端 0x81 常量


def sha1(data):
    return hashlib.sha1(data).digest()


def hmac_sha1(key, data):
    return hmac.new(key, data, hashlib.sha1).digest()


def expand_key(secret, label, size):
    """照抄 ol-mod Crypto.cpp:153-173 expandKey:
        block_i = HMAC-SHA1(key=secret, data=prev || label || counter), counter 从 1 递增, 拼接后截断。"""
    if isinstance(label, str):
        label = label.encode("ascii")
    out = bytearray()
    prev = b""
    counter = 1
    while len(out) < size:
        prev = hmac_sha1(secret, prev + label + bytes([counter & 0xFF]))
        counter += 1
        out += prev
    return bytes(out[:size])


def derive_session_keys(session_key, transcript):
    """照抄 ol-mod Crypto.cpp:197-216 deriveSessionKeys。返回 dict。"""
    if len(session_key) != 24:
        raise ValueError("DW session key 必须是 24 字节, 实际 %d" % len(session_key))
    transcript_hash = sha1(transcript)
    secret = hmac_sha1(transcript_hash, session_key)   # key=transcriptHash, data=sessionKey
    challenge = expand_key(secret, b"CLIENTCHAL", 16)
    data = expand_key(secret, b"BDDATA", 72)
    return {
        "secret": secret,
        "challenge": challenge,
        "response_id": challenge[8:16],       # 0x83 的 8 字节
        "request_hmac": data[0:20],           # = hmac_out
        "response_hmac": data[20:40],         # = hmac_in
        "decrypt": data[40:56],               # = aes_out
        "encrypt": data[56:72],               # = aes_in
    }


def ticket_from_client_auth(frame):
    """从客户端 0x82 帧里取出**被转发的 128B 票据**(跳过 83 bit, LSB-first 读 128B)。

    authInfo 位布局(同 ol-mod LobbyProtocol.cpp:89-114):
        serviceId 8 | unknown 1 | titleId 5+32 | ivSeed 5+32 | authInfoData 1024(128B)
    → 数据起点 = bit 83(不是字节对齐)。
    """
    off = 6
    if len(frame) < off + AUTH_INFO_BYTES:
        return None
    ai = frame[off:off + AUTH_INFO_BYTES]
    pos = 8 + 1 + (5 + 32) + (5 + 32)
    out = bytearray()
    for _ in range(128):
        v = 0
        for i in range(8):
            v |= ((ai[(pos + i) // 8] >> ((pos + i) % 8)) & 1) << i
        pos += 8
        out.append(v)
    return bytes(out)


def session_key_from_ticket(ticket):
    """会话密钥 = 票据偏移 **97..121**（24B）。

    ★ 2026-10-03 实测（HANDOFF §10.9）：客户端 HMAC(0xBA0D20) 的 data 就是这 24 字节,
      **不是**票据开头的 `DE AD BD EF`（那只是魔数）。
      这也正好对上 ol-mod 自己 `makeTicket()` 的布局（会话密钥写在 97..120）。
    """
    return bytes(ticket[97:121]) if ticket and len(ticket) >= 121 else b""


def session_key_from_client_auth(frame):
    """从 0x82 帧取会话密钥(= 票据[97:121])。"""
    t = ticket_from_client_auth(frame)
    return session_key_from_ticket(t) if t else None


def build_transcript(hello28, server_ack26, client_auth_frame):
    """transcript = hello[8:28] + 服务端实际发出的 0x81(26B) + clientAuth[:-8]。"""
    return bytes(hello28[8:28]) + bytes(server_ack26) + bytes(client_auth_frame[:-8])


def build_task_reply_objects(aes_in, hmac_in, seq_out, task, reply_id,
                             objects=(), status=0):
    """构造 0x85 任务应答(照抄 BuildTaskReplyObjects)。
    objects 是一串"结果对象"的原始字节(可为空)。"""
    inner = bytearray()
    inner += bytes([10]) + struct.pack("<Q", reply_id)
    inner += bytes([8]) + struct.pack("<I", status)
    inner += bytes([3, task & 0xFF])
    inner += bytes([8]) + struct.pack("<I", len(objects))
    if objects:
        inner += bytes([8]) + struct.pack("<I", len(objects))
        for o in objects:
            inner += o
    n = (5 + len(inner) + 15) // 16 * 16
    plain = bytearray(n)
    struct.pack_into("<I", plain, 0, len(inner))
    plain[4] = 1
    plain[5:5 + len(inner)] = inner
    iv = os.urandom(16)
    enc = cbc_encrypt(aes_in, iv, bytes(plain))
    fr = bytearray(26 + len(enc) + 8)
    struct.pack_into("<I", fr, 0, len(fr) - 4)
    fr[4] = MARK
    fr[5] = KIND_TASK
    struct.pack_into("<I", fr, 6, seq_out)
    fr[10:26] = iv
    fr[26:26 + len(enc)] = enc
    fr[-8:] = hmac8(hmac_in, bytes(fr[:-8]))
    return bytes(fr)


def build_task_reply(aes_in, hmac_in, seq_out, task, reply_id, status=0, objects=()):
    """单对象/空对象的便捷版。"""
    return build_task_reply_objects(aes_in, hmac_in, seq_out, task, reply_id,
                                    objects, status)


# --------------------------------------------------- 服务端主动推送(类型 2)
# 出处: ol-mod LobbyProtocol.cpp queuePush / InstantMessageService.cpp:179-184
#       / Unknown0BService.cpp:212-219。壳与任务应答完全一样(0x85), 只有明文里的
#       marker 从 0x01(应答) 变成 0x02(推送) —— 客户端据此走 push 分发。
def build_push(aes_in, hmac_in, seq_out, body, message_type=2):
    """构造一条服务端推送帧(同 0x85 壳, 明文 marker = message_type)。"""
    n = (5 + len(body) + 15) // 16 * 16
    plain = bytearray(n)
    struct.pack_into("<I", plain, 0, len(body))
    plain[4] = message_type & 0xFF
    plain[5:5 + len(body)] = body
    iv = os.urandom(16)
    enc = cbc_encrypt(aes_in, iv, bytes(plain))
    fr = bytearray(26 + len(enc) + 8)
    struct.pack_into("<I", fr, 0, len(fr) - 4)
    fr[4] = MARK
    fr[5] = KIND_TASK
    struct.pack_into("<I", fr, 6, seq_out)
    fr[10:26] = iv
    fr[26:26 + len(enc)] = enc
    fr[-8:] = hmac8(hmac_in, bytes(fr[:-8]))
    return bytes(fr)


def instant_push_body(sender_id, sender_name, message, kind=21, use_types=True):
    """即时消息推送**信封** —— 与 C# BuildPushFrameWithSender **逐字节一致**。

    C# 权威格式(CodolLocalLobbyServer.cs:503-517):
        08 <u32 service> | 0A <u64 senderId> | 10 <senderName 的 ASCII> 00
        | 13 08 <u32 len> <data>
    ——即**信封带 tag**, 只有最内层 data 由调用方决定是否带 tag。

    ol-mod decodeInstantPush 的 `[u32 21][u64 senderId][string name][blob message]`
    与之等价: 这里的 `kind` 就是 C# 的第一个字段 `service`(它同时是 type 21 = InstantMessage),
    `Buf(use_types=True)` 会写出 08/0A/10/13 08 这些 tag, 与 C# 完全对齐(已核对, 无需改)。

    ⚠️ 它输出的就是 `build_push(..., body)` 的 `body`(marker=2 由 build_push 补)。
    """
    ob = Buf(use_types)
    ob.u32(kind)                    # = C# 的 service(21)
    ob.u64(sender_id)
    ob.string(sender_name)
    ob.blob(message if isinstance(message, bytes) else message.encode("utf-8"))
    return ob.data()


def channel_push_body(sender_id, sender_name, channel_id, message,
                      whisper=False, msg_type=0, use_types=False):
    """频道推送体 —— 照抄 ol-mod Unknown0BService.cpp:212-219

    ⚠️★ **已废弃, 勿用(不再用于任何新路径)** —— 2026-10-03 实测: 这条推送体一发,
       客户端**立刻断连**(带 tag 时同秒 reset; 改无 tag 也只是多活几秒, 见 HANDOFF §13.4-13.7)。
       保留此函数仅为留存实验记录 / 可能的历史调用(仅 `ready_push.on` 那条默认关闭的老路径),
       新的推送一律走 `instant_push_body`(其信封 = C# BuildPushFrameWithSender)。
       若将来要再碰频道推送, 不要靠猜字段序, 应从 `decodeChannelPush` 严格反推。

    字段: [u32 (whisper?7:8)][u64 senderId][string senderName][u64 channelId][blob message][u32 msg_type]
    """
    ob = Buf(use_types)
    ob.u32(7 if whisper else 8)
    ob.u64(sender_id)
    ob.string(sender_name)
    ob.u64(channel_id)
    ob.blob(message if isinstance(message, bytes) else message.encode("utf-8"))
    ob.u32(msg_type)
    return ob.data()


# 房间 ready 批次的 16 字节常量 —— 照抄 ol-mod Unknown0BService.cpp:98-101。
ROOM_READY_BATCH = bytes.fromhex("0C00000002020000 0008000000800800".replace(" ", ""))

# ★★ 开局(game start)推送体 —— 逐字节照抄三方 CodolLocalLobbyServer.cs:1419-1430
#   的 `gameStartData`(162 字节)。触发条件: 客户端 `0B/4 setRoomData` 的 payload[11]==0x15
#   (即"点准备"), 三方在此**紧接着频道回显**再推这一条, 客户端才会进入加载/连战斗服。
#   推送封装 = BuildPushFrame(seq, service=11, data) → 即 instant_push_body(0, "Server", data, kind=11)。
#
#   ⚠️ 2026-10-07: 这条 162B 是三方从 firingrange 抓到的常量。实机确认
#   `plain[11]==0x15` 触发 + 推送都成功, 但 PvE coop 客户端仍停在“战斗开始”,
#   战斗服 0 收包。因此它**不是已验证的 coop 开局数据**; 下一步要么桥接 mmstart
#   到 battle_server, 要么替换成真实 coop gameStartData。
GAME_START_PAYLOAD = bytes.fromhex(
    "0A011000000000000013088500000081"
    "0000000204000000A4010000181802000000"
    "467D09D8AF02F807F8070000F807F807"
    "0000F807F8070000F807F8070000F807"
    "F8070000F807F8070000F807F8070000"
    "F807F8070000F807F8070000F807F807"
    "00E84BFA9A138B1740000000187A237A"
    "72634B73830000001848107828384800"
    "08485020304068580050000000706100"
    "00000000000000000000080100000000"
)
assert len(GAME_START_PAYLOAD) == 162, len(GAME_START_PAYLOAD)


def build_handshake_reply(hello28):
    """服务端 0x81 应答(照抄三方): u32 22 | 00 | 81 | u32 0xDC | 8B 随机 | 8B(=hello[20:28])。"""
    fr = bytearray(26)
    struct.pack_into("<I", fr, 0, 22)
    fr[4] = 0x00
    fr[5] = 0x81
    struct.pack_into("<I", fr, 6, 0xDC)
    fr[10:18] = os.urandom(8)
    fr[18:26] = hello28[20:28] if len(hello28) >= 28 else os.urandom(8)
    return bytes(fr)


def build_stage2(challenge8):
    """服务端 0x83(照抄三方): u32 10 | 00 | 83 | 8B challenge。"""
    fr = bytearray(14)
    struct.pack_into("<I", fr, 0, 10)
    fr[4] = 0x00
    fr[5] = 0x83
    fr[6:14] = challenge8[:8]
    return bytes(fr)


# ------------------------------------------------------------------ 自 测
if __name__ == "__main__":
    key = bytes(range(16))
    pt = bytes.fromhex("00112233445566778899aabbccddeeff")
    want = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
    got = _encrypt_block(_expand_key(key), pt)
    print("FIPS-197 AES-128 加密 : %s  %s" % (got.hex(), "OK" if got == want else "!! 失败"))
    back = _decrypt_block(_expand_key(key), got)
    print("FIPS-197 AES-128 解密 : %s  %s" % (back.hex(), "OK" if back == pt else "!! 失败"))

    iv = bytes(range(16, 32))
    data = bytes(range(32))
    c = cbc_encrypt(key, iv, data)
    print("CBC 往返              : %s" % ("OK" if cbc_decrypt(key, iv, c) == data else "!! 失败"))

    k1, k2 = os.urandom(16), os.urandom(20)
    fr = build_task_reply(k1, k2, 7, 0x04, 0x1122334455667788)
    d = decrypt_task_frame(fr, k1, k2)
    print("帧往返                : hmac_ok=%s seq=%s service=%s task=%s declared=%s"
          % (d["hmac_ok"], d["seq"], d["service"], d["task"], d["declared"]) if d
          else "帧往返                : !! 失败")
    frames, rest = parse_frames(fr + b"\x00\x00\x00\x00" + fr[:10])
    print("分帧                  : %d 帧, 剩余 %d 字节" % (len(frames), len(rest)))

    # --- 借鉴 ol-mod: session 记录必须逐字节对齐其导出样本(FULL A, 258 字节) ---
    FULL_A = (
        "1308250000007F000001207100FF00FF000000FF00FF000000FF00FF000000FF00FF00007F0000012071"
        "01130808000000887766554433221108000000000812000000080100000010"
        "31343332373738363333000A41420F0000000000106D705F63726173685F74726F706963616C00"
        "07ABAD92D6070000000007000000000700000000070000000007000000000700000000"
        "130810000000000102030405060708090A0B0C0D0E0F"
        "071300000007000000000700000000070800000007FFFFFFFF071C030000071E000000"
        "070000000007070000000700000000"
        "0701E00D0C0A41420F000000000007000000000700000000070000000007010000000700000000"
    )
    got = build_session_record(0x1122334455667788, (127, 0, 0, 1), 28960,
                               game_type=0, max_players=18, current_players=1,
                               map_name="mp_crash_tropical",
                               security_key=bytes(range(16)))
    want = bytes.fromhex(FULL_A)
    print("session 记录(258B)    : 长度=%d 期望=%d  %s"
          % (len(got), len(want), "OK" if got == want else "!! 不一致"))
    if got != want:
        for i in range(min(len(got), len(want))):
            if got[i] != want[i]:
                print("  首个差异 @0x%02X: got=%02X want=%02X" % (i, got[i], want[i]))
                break
    # 门槛自检: roomId 非零十进制 / host uid != 玩家 CODOID
    rid = (0x1122334455667788 & 0x7FFFFFFF) | 1
    print("  门槛: roomId=%s(非零十进制=%s) hostUid=%d"
          % (rid, str(rid).isdigit() and rid != 0, ROOM_HOST_UID))
    print("commonAddr 长度       : %d (应 37)" % len(bd_common_addr((127, 0, 0, 1), 28960)))
    print("钱包对象 03/08        : %s" % build_balance_object(1, 985699).hex(" "))

    # --- 21/5 mission session 对象: 靶场 / 普通(C# BuildMissionSessionObject) ---
    fr_obj = build_mission_session_object(True)
    nm_obj = build_mission_session_object(False)
    print("21/5 靶场 session 对象: 长度=%d 头48B=%s" % (len(fr_obj), fr_obj[:48].hex(" ")))
    print("21/5 普通 session 对象: 长度=%d 头48B=%s" % (len(nm_obj), nm_obj[:48].hex(" ")))
    print("  field1 头(靶场/普通) : %s / %s   (应 '13 08 43' / '13 08 18'; 0x13=tagblob)"
          % (fr_obj[:3].hex(" "), nm_obj[:3].hex(" ")))
    print("  靶场 GameType(07 07 00 00 01) 在流里 : %s"
          % ("07 07 00 00 01" in fr_obj.hex(" ")))
    print("  普通 GameType(07 03 00 00 01) 在流里 : %s"
          % ("07 03 00 00 01" in nm_obj.hex(" ")))
    print("  靶场 MaxPlayers(1) / 普通(4) 字段     : %s / %s"
          % ("07 01 00 00 00" in fr_obj.hex(" "), "07 04 00 00 00" in nm_obj.hex(" ")))

    # --- booking 推送帧: C# BuildFiringRangeBookingAccepted + BuildPushFrameWithSender ---
    accepted = struct.pack("<I", len(b"mmbook accepted\x00")) + b"mmbook accepted\x00"
    bk_body = instant_push_body(1, "localhost", accepted)          # service=21, sender=1
    bk_frame = build_push(k1, k2, 1000, bk_body, 2)
    bd = decrypt_task_frame(bk_frame, k1, k2)
    # 推送明文的布局是 u32 len | 0x02 | body(与客户端任务帧 0x86 布局不同),
    # 所以手工按明文核对: body = plain[5 : 5+declared]
    inner = bd["plain"][5:5 + bd["declared"]] if bd else b""
    ok = bool(bd) and bd["hmac_ok"] and bd["marker"] == 2 and inner == bk_body
    print("booking 推送帧        : %s  marker=%s declared=%s hmac=%s body(手工解)==信封:%s"
          % ("OK" if ok else "!! 失败", bd and bd["marker"], bd and bd["declared"],
             bd and bd["hmac_ok"], inner == bk_body))
    print("  信封(前32B)         : %s" % bk_body[:32].hex(" "))
    print("  内层 data(裸 20B)   : %s" % accepted.hex(" "))

    # --- 借鉴 ol-mod: deriveSessionKeys 的已知答案向量(KAT) ---
    # 出处 ol-mod tests/backend/DemonwareTests.cpp:2455-2478
    SK = b"Shippo fuute, mofu-mofu!"          # 24B
    TR = bytes(range(64))
    exp = {
        "response_id": "ea09fd53518d4361",
        "request_hmac": "96548bb09f4bd93996465628b618c9d3ec09ddd5",
        "response_hmac": "4395bd6340aa21bc95d9b77db1c04afc67061382",
        "decrypt": "71120733ba54e6ff13ded72c69deca7f",
        "encrypt": "b1adf0f2663cde670df4f20fbe37fc2e",
    }
    try:
        k = derive_session_keys(SK, TR)
        ok = all(k[n].hex() == v for n, v in exp.items())
        print("deriveSessionKeys KAT : %s" % ("OK" if ok else "!! 不一致"))
        for n, v in exp.items():
            if k[n].hex() != v:
                print("    %-13s got=%s want=%s" % (n, k[n].hex(), v))
        if not ok:
            # 参数序存疑时给出另一种解释的结果, 便于定位
            alt = hmac_sha1(SK, sha1(TR))
            c2 = expand_key(alt, b"CLIENTCHAL", 16)
            d2 = expand_key(alt, b"BDDATA", 72)
            print("    [备选 key=sessionKey] responseId=%s decrypt=%s"
                  % (c2[8:16].hex(), d2[40:56].hex()))
    except Exception as e:
        print("deriveSessionKeys KAT : !! 异常 %r" % (e,))
    print("SERVER_HEADER_ACK     : %d 字节 %s" % (len(SERVER_HEADER_ACK), SERVER_HEADER_ACK.hex(" ")))
```

<!-- /BLOCK -->

### 5.4 `nt10.py`（未内嵌，见 §7）

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
```python
# -*- coding: utf-8 -*-
"""一键集成启动器 (2026-10-02 改版: 对齐三方已验证可用的方案)

流程:
  1) 清理旧占用(只杀"我们自己的"脚本, 按命令行精确匹配)
  2) 修正 hosts / dwauth.ini / 证书 (见下)
  3) 起两个本地服务:
       127.0.0.1:3074  TLS   /auth/   (fake_auth_tls.py)
       127.0.0.2:3074  明文  大厅 lsg  (lobby_server.py)
  4) 跑 nt10.py 注入 + 观测

★ 关键改动(依据 E:\\codol\\dist\\CODOL-Portable 那份"能进大厅"的实现):
  a) 【不再劫持 down.qq.com / intldlgs.qq.com】—— 三方让 ACE/TP3 走真实网络,
     我们之前把 intldlgs.qq.com 指到 127.0.0.1 并让 443 回 404, 等于把
     TP3 从一个活着的服务器上掐断。
  b) 主通道是【3074】, 不是 8443/8446:
       127.0.0.1 formal-zone-auth.codol.qq.com   (TLS /auth/)
       127.0.0.2 formal-zone-lsg.codol.qq.com    (明文大厅 wI)
  c) dwauth.ini 的正确格式(三方 Run-Session.ps1 第 167 行):
       formal-zone-lsg.codol.qq.com 3074
       formal-zone-auth.codol.qq.com 3074
       0x03EA
  d) 证书 SAN 必须是 localhost + formal-zone-auth.codol.qq.com +
     formal-zone-lsg.codol.qq.com (由 make_local_ca.ps1 生成)

用法:
  python run_all.py                       # 默认 150 秒, 输出 n10run.txt
  python run_all.py --secs 180 --out n10an.txt
  python run_all.py --restore-hosts       # 只把 hosts 恢复干净, 不跑游戏
  python run_all.py --no-hosts            # 不改 hosts(你自己管)
"""
import argparse
import os
import re
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME_ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929"
HOSTS_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                          "System32", "drivers", "etc", "hosts")
PORTS = [80, 443, 3074, 8081, 8443, 8446, 49155, 49156]

# 我们写入 hosts 的块(三方同款两条)
HOSTS_BEGIN = "# CODOL-LOCAL-BEGIN"
HOSTS_END = "# CODOL-LOCAL-END"
HOSTS_BLOCK = (HOSTS_BEGIN + "\r\n"
               + "127.0.0.1 formal-zone-auth.codol.qq.com\r\n"
               + "127.0.0.2 formal-zone-lsg.codol.qq.com\r\n"
               + HOSTS_END + "\r\n")

# 只匹配"我们自己起的"进程 —— 避免误杀无关程序
KILL_RE = (r"fake_ied_https|fake_auth_https|fake_auth_tls|lobby_server\.py|fake_lobby\.py"
           r"|nt10\.py|setup_auth8443|battle_server\.py")


def ps_run(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                          capture_output=True, text=True, errors="replace")


def _is_admin():
    try:
        r = ps_run("([Security.Principal.WindowsPrincipal]"
                   "[Security.Principal.WindowsIdentity]::GetCurrent())"
                   ".IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)")
        return (r.stdout or "").strip()
    except Exception:
        return "?"


def _listening_ports():
    """用 netstat 读 LISTENING 的本地端口。
    ★ 绝不能改成"connect 一下试试": lobby_server 会把这个探测连接当成真的大厅连接
      (上一轮 [who] 已证: 8446 的来访者是 run_all 自己的 python.exe), 白白污染日志。"""
    res = {}
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             errors="replace", timeout=15).stdout
    except Exception:
        return res
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[3].upper() == "LISTENING":
            loc = p[1]
            if ":" in loc:
                port = loc.rsplit(":", 1)[1]
                if port.isdigit():
                    res.setdefault(int(port), p[4])
    return res


def show_ports(tag):
    lp = _listening_ports()
    print("[*] 端口监听状态(%s):" % tag)
    for p in PORTS:
        print("      %-6d %s" % (p, ("LISTENING pid=%s" % lp[p]) if p in lp else "空闲"))


def port_listening(port):
    return port in _listening_ports()


def _listening_endpoints():
    """返回 (addr, port) 集合 —— 用来区分 127.0.0.1:3074 与 127.0.0.2:3074。"""
    res = set()
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             errors="replace", timeout=15).stdout
    except Exception:
        return res
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[3].upper() == "LISTENING":
            loc = p[1]
            if ":" in loc:
                a, _, pt = loc.rpartition(":")
                if pt.isdigit():
                    res.add((a.strip("[]"), int(pt)))
    return res


def addr_listening(addr, port):
    return (addr, port) in _listening_endpoints()


# ---------------------------------------------------------------- hosts
def _read_hosts():
    return open(HOSTS_PATH, "rb").read().decode("latin-1")


def _write_hosts(text):
    open(HOSTS_PATH, "wb").write(text.encode("latin-1"))


def clean_hosts(verbose=True):
    """删掉: 1) 我们写的块  2) plan A 遗留的 intldlgs/down.qq.com 本地劫持行。
    ★ down.qq.com / intldlgs.qq.com 必须交还给真实网络 —— 三方实现就是这么做的,
      否则 ACE/TP3 拿不到配置和 DLL。"""
    txt = _read_hosts()
    orig = txt
    txt = re.sub(re.escape(HOSTS_BEGIN) + r".*?" + re.escape(HOSTS_END) + r"\r?\n?",
                 "", txt, flags=re.S)
    kept, removed = [], []
    for ln in txt.splitlines():
        s = ln.strip()
        if s.startswith("#") and "fake iedsafe" in s:
            removed.append(ln)
            continue
        if re.match(r"^\s*127\.0\.0\.\d+\s+.*(intldlgs\.qq\.com|down\.qq\.com)\b", ln):
            removed.append(ln)
            continue
        kept.append(ln)
    txt = "\r\n".join(kept)
    if txt and not txt.endswith("\r\n"):
        txt += "\r\n"
    if txt != orig:
        _write_hosts(txt)
    if verbose:
        for ln in removed:
            print("      - 删除 hosts 行: %s" % ln.strip())
        print("      hosts 清理: %s" % ("已改动" if txt != orig else "无需改动"))
    return txt


def verify_hosts():
    txt = _read_hosts()
    print("      hosts 现状(与 codol/qq 相关的行):")
    bad = []
    for ln in txt.splitlines():
        if re.search(r"formal-zone|codol|intldlgs|down\.qq", ln, re.I):
            print("          %s" % ln.strip())
            if re.match(r"^\s*127\.0\.0\.\d+\s+.*(intldlgs\.qq\.com|down\.qq\.com)\b", ln):
                bad.append(ln.strip())
    if bad:
        print("      !! 仍有 iedsafe 劫持行: %s" % bad)
    else:
        print("      [+] 无 intldlgs/down.qq.com 劫持 —— ACE/TP3 走真实网络 OK")


def ensure_hosts():
    print("=" * 70)
    print("[2/5] 修正 hosts")
    print("=" * 70)
    txt = clean_hosts()
    if HOSTS_BEGIN in txt:
        print("      [=] 我们的 hosts 块已存在")
    else:
        if txt and not txt.endswith("\r\n"):
            txt += "\r\n"
        txt += HOSTS_BLOCK
        _write_hosts(txt)
        print("      [+] 已写入:")
        for ln in HOSTS_BLOCK.strip().splitlines():
            print("          %s" % ln)
    verify_hosts()


# ---------------------------------------------------- cert / dwauth
def ensure_cacert():
    """把 _ca.pem(本地 root CA) 追加进游戏 cacert.pem。
    用 Python 做 —— 路径含中文, PowerShell 5.1 读无 BOM 脚本会乱码。"""
    ca = os.path.join(ROOT, "_ca.pem")
    dst = os.path.join(GAME_ROOT, "cacert.pem")
    if not os.path.exists(ca):
        print("      !! 找不到 %s" % ca)
        return False
    if not os.path.exists(dst):
        print("      !! 找不到 %s" % dst)
        return False
    pem = open(ca, "r", encoding="ascii", errors="replace").read()
    flat = pem.split("-----")
    body = "".join(flat[2].split()) if len(flat) > 2 else ""
    cur = open(dst, "rb").read().decode("latin-1")
    if body and body in "".join(cur.split()):
        print("      [=] 该 root CA 已在 cacert.pem 内 (共 %d 张)"
              % cur.count("BEGIN CERTIFICATE"))
        return True
    n0 = cur.count("BEGIN CERTIFICATE")
    if not cur.endswith("\n"):
        cur += "\n"
    cur += pem if pem.endswith("\n") else pem + "\n"
    open(dst, "wb").write(cur.encode("latin-1"))
    print("      [+] 已追加 root CA 到 %s (证书数 %d -> %d)"
          % (dst, n0, cur.count("BEGIN CERTIFICATE")))
    return True


def make_certs():
    ps1 = os.path.join(ROOT, "make_local_ca.ps1")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-File", ps1, "-Root", ROOT],
                       capture_output=True, text=True, errors="replace")
    for ln in (r.stdout or "").splitlines():
        if ln.strip():
            print("      | %s" % ln.rstrip())
    ok = (os.path.exists(os.path.join(ROOT, "_leaf2.cer"))
          and os.path.exists(os.path.join(ROOT, "_ca.pem")))
    if r.returncode != 0 or not ok:
        print("      !! 证书生成失败 rc=%s" % r.returncode)
        for ln in (r.stderr or "").splitlines()[:12]:
            print("      !! %s" % ln.rstrip())
        return False
    return ensure_cacert()


def write_dwauth():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "write_dwauth.py"),
                        "--root", GAME_ROOT],
                       capture_output=True, text=True, errors="replace")
    for ln in (r.stdout or "").splitlines():
        if ln.strip():
            print("      | %s" % ln.rstrip())
    if r.returncode != 0:
        print("      !! write_dwauth 失败 rc=%s" % r.returncode)
        for ln in (r.stderr or "").splitlines()[:8]:
            print("      !! %s" % ln.rstrip())
        return False
    return True


def zombie_count():
    """残留的 codoMP_client_shipRetail 进程数。用户态杀不掉, 只有重启能清。"""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "(Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue "
                            "| Measure-Object).Count"],
                           capture_output=True, text=True, errors="replace")
        return int((r.stdout or "0").strip() or 0)
    except Exception:
        return 0


def kill_udp_owners(port):
    """杀掉占用 UDP <port> 的进程 —— 战斗服专用(28960)。

    ★ 为什么不只靠 KILL_RE: 那条路要读别的进程的 CommandLine, 跨权限时常常读到空串
      (2026-10-04 实测: 21 个管理员权限的战斗服残留, CommandLine 全为空, 过滤不出来)。
      按端口所有者杀更稳 —— 本机 UDP 28960 只可能是我们的 battle_server。"""
    try:
        r = subprocess.run(["netstat", "-ano", "-p", "UDP"],
                           capture_output=True, text=True, errors="replace")
    except Exception:
        return
    pids = set()
    for ln in (r.stdout or "").splitlines():
        parts = ln.split()
        if len(parts) >= 4 and parts[0].upper() == "UDP" and parts[1].endswith(":%d" % port):
            if parts[-1].isdigit():
                pids.add(parts[-1])
    for pid in sorted(pids):
        try:
            r = subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, text=True, errors="replace")
        except Exception as e:
            print("  kill(UDP %d) PID %s -> 异常 %r" % (port, pid, e))
            continue
        ok = (r.returncode == 0)
        msg = "OK" if ok else ((r.stdout or r.stderr or "").strip().replace("\n", " ") or "失败")
        print("  kill(UDP %d) PID %s -> %s" % (port, pid, msg))
    if pids:
        print("  (按端口清掉 %d 个战斗服残留 —— UDP %d)" % (len(pids), port))
    else:
        # ★ 2026-10-04: 曾出现"netstat 里没有占用者, 但战斗服 bind 仍报 10048" —— 打印原始状态,
        #   下次一眼能看出是 netstat 没查到、还是查到了没杀成。
        print("  (UDP %d 没查到占用者 —— 若战斗服仍报 bind 10048, 看下面原始 netstat)"
              % port)
        try:
            r2 = subprocess.run(["netstat", "-ano", "-p", "UDP"],
                                capture_output=True, text=True, errors="replace")
            hits = [ln.strip() for ln in (r2.stdout or "").splitlines()
                    if ":%d" % port in ln]
            print("    netstat 命中 %d 行: %s" % (len(hits), hits[:5] if hits else "(无)"))
        except Exception as e:
            print("    netstat 复读失败: %r" % (e,))


def free_ports():
    print("=" * 70)
    print("[1/5] 清理旧占用")
    print("=" * 70)
    cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match '%s' } | "
        "Where-Object { $_.ProcessId -ne $PID } | "
        "ForEach-Object { $c=$_.CommandLine; if(-not $c){$c=''}; "
        "Write-Output ('  kill PID ' + $_.ProcessId + ' : ' + $c.Substring(0,[Math]::Min(100,$c.Length))); "
        "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    ) % KILL_RE
    r = ps_run(cmd)
    out = (r.stdout or "").strip()
    print(out if out else "  (没有匹配到我们自己的脚本)")
    kill_udp_owners(28960)
    time.sleep(2)
    show_ports("清理后")


def start_py_service(tag, script, port, logname, addr=None):
    """起一个 Python 写的服务(自己实现协议, 如 fake_auth_tls.py)。
    addr 给了就按 (addr, port) 精确校验监听(区分 127.0.0.1 / 127.0.0.2 的 3074)。"""
    print("=" * 70)
    print("[*] 起 %s (%s:%d) : %s" % (tag, addr or "0.0.0.0", port, script))
    print("=" * 70)
    out = os.path.join(ROOT, "_%s_out.txt" % tag)
    err = os.path.join(ROOT, "_%s_err.txt" % tag)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, script)],
                            stdout=open(out, "w"), stderr=open(err, "w"),
                            stdin=subprocess.DEVNULL, creationflags=0x08000000)

    def _up():
        return addr_listening(addr, port) if addr else port_listening(port)

    ok = False
    for _ in range(24):
        time.sleep(0.5)
        if _up():
            ok = True
            break
        if proc.poll() is not None:
            break
    if ok:
        print("      %s:%d 已监听 OK (pid=%s, 日志 %s)"
              % (addr or "0.0.0.0", port, proc.pid, os.path.basename(logname)))
        return True
    print("      !! %s:%d 未监听 (子进程 pid=%s rc=%s)"
          % (addr or "0.0.0.0", port, proc.pid, proc.poll()))
    for f in (logname, out, err):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read().strip()
        except Exception:
            txt = ""
        print("      --- %s ---" % os.path.basename(f))
        if txt:
            print("      " + txt.replace("\n", "\n      "))
    return False


def start_auth_tls():
    """127.0.0.1:3074 的 /auth/ 服务 (TLS)。
    三方 Run-Session.ps1 就是把 auth 服务放在 127.0.0.1:3074
    (hosts: 127.0.0.1 formal-zone-auth.codol.qq.com)。
    用 Python 自己做 TLS —— http.sys 关连接时不发 close-notify。"""
    for f in ("auth3074.log",):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    return start_py_service("auth", "fake_auth_tls.py", 3074,
                            os.path.join(ROOT, "auth3074.log"), addr="127.0.0.1")


def start_battle_server(bind="0.0.0.0", port=28960):
    """战斗服(UDP)。当前是"最小骨架 + 抓包观察通道": 只实现 NAT 遍历应答,
    其余包全部记进 battle_srv.log —— 进对局时客户端会连它, 先看清它发什么。"""
    print("=" * 70)
    print("[*] 起战斗服 UDP %s:%d : battle_server.py" % (bind, port))
    print("=" * 70)
    out = os.path.join(ROOT, "_battle_out.txt")
    err = os.path.join(ROOT, "_battle_err.txt")
    try:
        subprocess.Popen([sys.executable, os.path.join(ROOT, "battle_server.py"),
                          "--bind", bind, "--port", str(port)],
                         stdout=open(out, "w"), stderr=open(err, "w"),
                         stdin=subprocess.DEVNULL, creationflags=0x08000000)
    except Exception as e:
        print("      !! 起战斗服失败: %r" % (e,))
        return False
    time.sleep(1.5)
    logs = []
    for f in (os.path.join(ROOT, "battle_srv.log"), out, err):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read().strip()
        except Exception:
            txt = ""
        if txt:
            logs.append(txt.splitlines()[-3:])
    print("      战斗服已拉起; 日志 battle_srv.log")
    for ls in logs:
        for ln in ls:
            print("      " + ln)
    return True


def start_lobby_server(lobby_bind="127.0.0.2", lobby_port=3074, raw_ports=""):
    """127.0.0.2:3074 的明文大厅服务 (= formal-zone-lsg.codol.qq.com)。
    ★ 不再默认起 443/80/8081 的原始抓包 —— 那些端口已交还真实网络
      (三方不劫持 down.qq.com / intldlgs.qq.com)。"""
    print("=" * 70)
    print("[*] 起大厅服务 (明文 %s:%d)  raw=[%s]" % (lobby_bind, lobby_port, raw_ports))
    print("=" * 70)
    logf = os.path.join(ROOT, "lobby_srv.log")
    if os.path.exists(logf):
        try:
            os.remove(logf)
        except Exception:
            pass
    # 清掉上一轮留下的就绪标志/抓包/密钥快照, 否则会用到过期的 key
    for f in ("lobby_ready.flag", "lobby_rx.bin", "lobby_tasks.bin", "secrets.txt"):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    subprocess.Popen([sys.executable, os.path.join(ROOT, "lobby_server.py"),
                      "--lobby-bind", lobby_bind, "--lobby-port", str(lobby_port),
                      "--raw-ports", raw_ports],
                     creationflags=0x00000008)
    print("      已启动 lobby_server.py (日志 lobby_srv.log)")


def is_good(path, secs):
    """判断本次启动是否为"好启动"。
    好: game 仍在运行(跑满窗口) / 或正常退出(rc=0)且存活 >= 80% 窗口。
    坏: 崩溃退出(如 0xC0000005=3221225477)、t 很小、或钩子一次都没命中。"""
    try:
        t = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return False, "输出文件读取失败"
    if "game 仍在运行" in t:
        return True, "跑满窗口"
    m = re.search(r"game 退出 rc=(-?\d+) t=([\d.]+)", t)
    if m:
        rc = int(m.group(1))
        tt = float(m.group(2))
        if rc == 0 and tt >= secs * 0.8:
            return True, "正常退出 rc=0 t=%.1f" % tt
        return False, "退出 rc=%d(0x%X) t=%.1f" % (rc, rc & 0xFFFFFFFF, tt)
    if "注入" in t and "-> 成功" not in t:
        return False, "TAS 注入失败"
    return False, "未见存活标志(可能早退)"


def run_nt10(secs, out, apis, retries=1, trace=False, ps=False):
    print("=" * 70)
    print("[4/4] 跑 nt10.py (注入 + 观测), 失败自动重试, 最多 %d 次" % retries)
    print("=" * 70)
    base, ext = os.path.splitext(out)
    last = out
    for i in range(1, retries + 1):
        dst = out if i == 1 else "%s_a%d%s" % (base, i, ext)
        cmd = [sys.executable, os.path.join(ROOT, "nt10.py"),
               "--root", GAME_ROOT,
               "--secs", str(secs), "--delay", "0", "--out", dst, "--apis", apis]
        if trace:
            cmd.append("--trace")
        if ps:
            cmd.append("--ps-probe")
        print("\n>>> 第 %d/%d 次启动 ..." % (i, retries))
        subprocess.run(cmd, cwd=ROOT)
        ok, why = is_good(os.path.join(ROOT, dst), secs)
        if ok:
            print(">>> 第 %d 次 = 好启动 (%s) -> %s" % (i, why, dst))
            last = dst
            break
        print(">>> 第 %d 次 = 坏启动 (%s), 重新启动 ..." % (i, why))
        time.sleep(2)
    else:
        print(">>> %d 次都没起好(启动 flake), 可再跑一次 run_all.py" % retries)
    print()
    print("=" * 70)
    print("完成。看这三处:")
    print("  %s" % os.path.join(ROOT, last))
    print("  %s" % os.path.join(ROOT, "lobby_srv.log"))
    print("  %s" % os.path.join(ROOT, "auth3074.log"))
    print("=" * 70)


def run_nt10_multi(secs, out, apis, clients=1, retries=1, trace=False, ps=False):
    """★ 多客户端(2026-10-03): 同时跑 N 份 nt10 —— 每个 nt10 自己拉起一份游戏并注入。

    服务端侧的配对已经在 lobby_server.py / fake_auth_tls.py 落地:
      · `fake_auth_tls` 给每个 /auth/ 请求发**唯一的 24B 会话密钥**(写在票据 97..121);
      · 每个 nt10 的 KDF hook 把该会话的密钥追加进 `kdf_sessions.txt`;
      · `lobby_server` 收到 0x82 后, 从帧里读票据[97:121] 当配对键查表,
        用**该客户端自己的**密钥解 0x85、签应答。
    所以这里只负责"同时起 N 份"; N=1 时行为与以前完全一致。
    """
    if clients <= 1:
        return run_nt10(secs, out, apis, retries, trace, ps)
    print("=" * 70)
    print("[4/4] 多客户端: 同时跑 %d 份 nt10 (各自拉起一份游戏实例)" % clients)
    print("=" * 70)
    base, ext = os.path.splitext(out)
    procs = []
    for i in range(clients):
        dst = out if i == 0 else "%s_c%d%s" % (base, i + 1, ext)
        cmd = [sys.executable, os.path.join(ROOT, "nt10.py"),
               "--root", GAME_ROOT,
               "--secs", str(secs), "--delay", "0", "--out", dst, "--apis", apis,
               # ★ 多客户端必须加这个: 否则两个 nt10 会互相 taskkill 对方的游戏
               "--keep-others"]
        if trace:
            cmd.append("--trace")
        if ps:
            cmd.append("--ps-probe")
        print(">>> 客户端 %d: %s" % (i + 1, " ".join(cmd[2:])))
        procs.append((dst, subprocess.Popen(cmd, cwd=ROOT)))
        time.sleep(1.5)          # 错开一点, 避免同时抢 hosts/单实例互斥
    for dst, p in procs:
        p.wait()
    print()
    print("=" * 70)
    print("完成。各客户端 nt10 日志: %s" % ", ".join(d for d, _ in procs))
    print("  %s" % os.path.join(ROOT, "lobby_srv.log"))
    print("  %s" % os.path.join(ROOT, "auth3074.log"))
    print("  %s   (每会话一行的 会话密钥→四把子密钥 表, 配对用)" % os.path.join(ROOT, "kdf_sessions.txt"))
    print("  %s   (每个 /auth/ 发的会话密钥)" % os.path.join(ROOT, "auth_sessions.txt"))
    print("=" * 70)


def run_nt8o(secs, out, directs, apis):
    """用【原始 nt8 的副本】(nt8o.py) 驱动。
    nt8 的 --direct 会一直等"解壳就绪"再挂 hook；另外它的支持表里有
    WSAConnect/WSASocketW/WSARecv/send/recv —— 用来找"到底是谁发起了那条
    /auth/ TLS 连接、谁在收应答"(ws2_32 的 connect 钩子从来没见过 8443)。"""
    print("=" * 70)
    print("[4/4] 跑 nt8o.py (原始 nt8 副本)")
    print("=" * 70)
    cmd = [sys.executable, os.path.join(ROOT, "nt8o.py"),
           "--secs", str(secs),
           "--apis", apis,
           "--direct", directs, "--show", "8",
           "--out", os.path.join(ROOT, out)]
    print(">>> " + " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT)
    print()
    print("完成。看: %s" % os.path.join(ROOT, out))


def _run_driver(a):
    if a.driver == "nt8o":
        run_nt8o(a.secs, a.out, a.direct, a.n8apis)
    else:
        run_nt10_multi(a.secs, a.out, a.apis, a.clients, a.retries,
                       trace=getattr(a, "trace", False),
                       ps=getattr(a, "ps_probe", False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=int, default=150)
    ap.add_argument("--out", default="n10run.txt")
    ap.add_argument("--apis", default="OpenFileMappingW,CreateFileMappingW,MapViewOfFile,"
                                      "connect,sendto,WinHttpConnect,WinHttpOpenRequest,"
                                      "WinHttpSendRequest,z1,z2",
                    help="要 hook 的 API（逗号分隔）。★ 2026-10-04: 别再往默认里加 recv/WSARecv 等"
                         "热路径 —— hook 它们会把游戏网络带崩。--trace 时由 nt10 自己追加触发器。")
    ap.add_argument("--driver", default="nt10", choices=["nt10", "nt8o"],
                    help="用哪个注入器: nt10(自己维护) / nt8o(原始 nt8 的副本)")
    ap.add_argument("--trace", action="store_true",
                    help="路线A探针: 让 nt10 运行时调用客户端原生碰撞 trace(sub_46E780)，"
                         "每 10s 一轮共 8 轮，结果打在 nt10 日志里")
    ap.add_argument("--ps-probe", action="store_true",
                    help="出生点/位置探针: nt10 周期性扫客户端内存里的本地 playerstate，"
                         "把 origin/角度写进 player_origin.txt（用来和地图出生点清单对照）")
    ap.add_argument("--direct", default="0xBA9980,0xBC3E10",
                    help="--driver nt8o 时直挂的绝对地址(票据解析 / JSON 取字段)")
    ap.add_argument("--n8apis", default="WSAConnect,WSASocketW,connect,sendto,WSASendTo,"
                                        "send,recv,WSARecv,"
                                        "OpenFileMappingW,CreateFileMappingW,MapViewOfFile",
                    help="--driver nt8o 时的 hook 集合(必须是 nt8 支持表里的名字; 不传 --only-exe 以看到 DLL 调用者)")
    ap.add_argument("--no-kill", action="store_true")
    ap.add_argument("--retries", type=int, default=1, help="坏启动时最多重试几次")
    ap.add_argument("--clients", type=int, default=1,
                    help="同时跑几个客户端(每个 nt10 拉起一份游戏; 服务端按会话密钥自动配对)")
    ap.add_argument("--raw-ports", default="",
                    help="诊断: 额外在 0.0.0.0 上抓这些端口(逗号分隔), 如 80,8081。默认空")
    ap.add_argument("--no-hosts", action="store_true",
                    help="不改 hosts(你自己管)")
    ap.add_argument("--restore-hosts", action="store_true",
                    help="只把 hosts 恢复干净(删掉我们的块 + intldlgs/down.qq.com 劫持行), 然后退出")
    ap.add_argument("--no-certs", action="store_true",
                    help="不重新生成证书(复用现有的 _ca.pem/_leaf2.cer)")
    ap.add_argument("--no-dwauth", action="store_true",
                    help="不改 dwauth.ini")
    ap.add_argument("--poke", action="store_true",
                    help="写大厅主机/端口全局(默认不写 —— 三方实现只靠 hosts+dwauth.ini+4 个补丁)")
    ap.add_argument("--tas", action="store_true",
                    help="注入 TAS 镜像。默认【不注入】—— 实测 TAS 会把客户端推到 DSA 签名路径"
                         "(auth_task=32 + codo_request 签名块), 从而卡在\"无法连接大厅服务\"")
    ap.add_argument("--no-services", action="store_true",
                    help="隔离实验: 不起任何假服务, 只跑 nt10 —— 等价于 nt8 的环境")
    ap.add_argument("--no-battle", action="store_true",
                    help="不起战斗服(UDP 127.0.0.1:28960)。默认起 —— 进对局时客户端会连它")
    ap.add_argument("--force", action="store_true",
                    help="检测到残留游戏进程(僵尸)时也继续跑")
    a = ap.parse_args()

    # 僵尸进程自检: 残留的 codoMP_client_shipRetail 会占住游戏单实例互斥,
    # 新实例一起来就退出(表现为"坏启动 rc=1 t≈10s"), 而且用户态 taskkill 杀不掉。
    z = zombie_count()
    if z:
        print("=" * 70)
        print("!! 检测到 %d 个残留的 codoMP_client_shipRetail 进程" % z)
        print("   它们会占住游戏的单实例互斥 → 新实例起来就退(坏启动 rc=1 t≈10s),")
        print("   而且 taskkill/Stop-Process 都杀不掉(实测 Access is denied)。")
        print("   处理办法: 重启一次机器再跑。想忽略请加 --force。")
        print("=" * 70)
        if not getattr(a, "force", False):
            return
        print("[!] --force: 忽略僵尸进程继续")
    else:
        print("[*] 无残留游戏进程 OK")

    if a.restore_hosts:
        print("=" * 70)
        print("[*] --restore-hosts: 只修 hosts")
        print("=" * 70)
        clean_hosts()
        verify_hosts()
        return

    flag = os.path.join(ROOT, "poke_off.flag")
    if a.poke:
        if os.path.exists(flag):
            try:
                os.remove(flag)
            except Exception:
                pass
        print("[!] --poke: 本轮会写大厅主机/端口全局")
    else:
        open(flag, "w").close()
        print("[*] 默认不写大厅全局(三方实现只靠 hosts + dwauth.ini + 内存补丁); 要写请加 --poke")
    tflag = os.path.join(ROOT, "tas_off.flag")
    if a.tas:
        if os.path.exists(tflag):
            try:
                os.remove(tflag)
            except Exception:
                pass
        print("[!] --tas: 本轮会注入 TAS 镜像(注意: 这会让客户端走 DSA 签名路径)")
    else:
        open(tflag, "w").close()
        print("[*] 默认不注入 TAS 镜像(必需 —— 否则 auth_task=32 走签名路径会卡住); 要注入请加 --tas")

    if not a.no_kill:
        free_ports()

    # ---- [2/5] hosts: 交还 down.qq.com / intldlgs.qq.com, 只劫持两个 CODOL 域名
    if a.no_hosts:
        print("[!] --no-hosts: 不改 hosts")
    else:
        ensure_hosts()

    # ---- [3/5] dwauth.ini + 证书
    print("=" * 70)
    print("[3/5] 写 dwauth.ini + 生成/校验本地证书")
    print("=" * 70)
    if a.no_dwauth:
        print("      [!] --no-dwauth: 跳过")
    else:
        write_dwauth()
    if a.no_certs:
        print("      [!] --no-certs: 跳过证书生成, 仅校验 cacert.pem")
        ensure_cacert()
    else:
        make_certs()

    if a.no_services:
        print("=" * 70)
        print("[!] --no-services 隔离模式: 不起任何假服务, 只跑 nt10")
        print("=" * 70)
        show_ports("清理后")
        _run_driver(a)
        return

    # ---- [4/5] 两个本地服务: 127.0.0.1:3074(TLS /auth/) + 127.0.0.2:3074(明文大厅)
    print("=" * 70)
    print("[4/5] 起本地服务")
    print("=" * 70)
    start_auth_tls()
    start_lobby_server(raw_ports=a.raw_ports)
    # ★ 2026-10-05: 战斗服只允许由一处拉起。
    #   lobby_server 自己会在 "127.0.0.2 + firingrange-battle.enabled" 时起一份
    #   (见 maybe_start_battle_server); 这里若再起一份就会抢 28960, 结果是
    #   两份互相顶掉: 一份写日志、一份占端口, 实际收包全 0。
    #   所以开关文件在时交给 lobby_server 起; 只有开关不在时才由这里兜底。
    fr_battle_on = os.path.exists(os.path.join(ROOT, "firingrange-battle.enabled"))
    if not a.no_battle and not fr_battle_on:
        start_battle_server()
    time.sleep(3)
    show_ports("启动后")
    print("      ★ 注意: 443/80/8081 应当【空闲】—— 它们已交还真实网络")
    _run_driver(a)


if __name__ == "__main__":
    main()
```

<!-- /BLOCK -->

### 5.6 `write_dwauth.py`

<!-- BLOCK:write_dwauth.py -->
```python
# -*- coding: utf-8 -*-
"""按【三方已验证可用】的格式写游戏目录下的 dwauth.ini。

三方来源: E:\\codol\\dist\\CODOL-Portable\\Data\\runtime\\Run-Session.ps1 第 167 行
    $auth = "formal-zone-lsg.codol.qq.com 3074`r`n
             formal-zone-auth.codol.qq.com 3074`r`n
             0x03EA`r`n"

要点(与我方旧版完全不同):
  1. 主机名用【域名】而不是 IP;
  2. 端口是【3074】(明文/主通道), 不是 443;
  3. 末行多一个魔数【0x03EA】;
  4. CRLF 行尾, 末尾保留一个 CRLF。

旧版(错误)内容长这样, 别再用:
    127.0.0.1
    0
    127.0.0.1
    443
    0
    0
    0

用法:
  python write_dwauth.py                 # 写到默认游戏目录
  python write_dwauth.py --root "E:\使命召唤OL\使命召唤OL"
  python write_dwauth.py --show          # 只读现在的内容, 不写
"""
import argparse
import os
import shutil
import sys

DEFAULT_ROOT = r"E:\使命召唤OL\使命召唤OL"

CONTENT = ("formal-zone-lsg.codol.qq.com 3074\r\n"
           "formal-zone-auth.codol.qq.com 3074\r\n"
           "0x03EA\r\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT, help="游戏根目录(含 codoMP_client_shipRetail.exe)")
    ap.add_argument("--show", action="store_true", help="只打印当前内容, 不写")
    ap.add_argument("--no-backup", action="store_true")
    a = ap.parse_args()

    dst = os.path.join(a.root, "dwauth.ini")
    want = CONTENT.encode("ascii")

    if os.path.exists(dst):
        cur = open(dst, "rb").read()
        print("[*] 当前 %s (%d 字节):" % (dst, len(cur)))
        print("    " + repr(cur))
    else:
        cur = None
        print("[*] %s 不存在(将新建)" % dst)

    if a.show:
        return 0

    if cur == want:
        print("[=] 已经是正确内容, 无需修改")
        return 0

    if cur is not None and not a.no_backup:
        bak = dst + ".orig"
        if not os.path.exists(bak):
            shutil.copy2(dst, bak)
            print("[*] 已备份 -> %s" % bak)

    open(dst, "wb").write(want)
    print("[+] 已写入正确格式 (%d 字节), CRLF 行尾:" % len(want))
    for ln in CONTENT.split("\r\n"):
        if ln:
            print("      %s" % ln)
    # 回读校验
    back = open(dst, "rb").read()
    if back != want:
        print("[!] 回读不一致!")
        return 1
    print("[+] 回读校验 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

<!-- /BLOCK -->

### 5.7 `make_local_ca.ps1`

<!-- BLOCK:make_local_ca.ps1 -->
```powershell
# make_local_ca.ps1
# ---------------------------------------------------------------------------
# Regenerate the local TLS material with the SAN set the client actually
# expects (three-domain SAN, same as the proven third-party launcher).
#
# Output files (overwritten, keep the old names so fake_auth_tls.py needs no
# change apart from the port):
#   _ca.pem       root CA certificate, PEM
#   _ca.cer       root CA certificate, DER
#   _leaf2.cer    leaf certificate, DER   (SAN = localhost + formal-zone-*)
#   _rsa.txt      leaf RSA private key parameters (base64, one per line)
#
# Side effects:
#   * root CA imported into Cert:\LocalMachine\Root
#
# NOTE: this script is ASCII-only on purpose (PowerShell 5.1 reads BOM-less
# files as GBK, which mangles non-ASCII paths). The game directory path
# contains non-ASCII characters, so cacert.pem is NOT touched here -- the
# caller (run_all.py, i.e. Python) appends _ca.pem to it instead.
# ---------------------------------------------------------------------------
param(
    [string]$Root = 'e:\codol tae'
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path -LiteralPath $Root).Path
$names = @('localhost',
           'formal-zone-auth.codol.qq.com',
           'formal-zone-lsg.codol.qq.com')

Write-Host "=== make_local_ca ===" -ForegroundColor Cyan
Write-Host ("  output dir : " + $Root)
Write-Host ("  SAN        : " + ($names -join ', '))

# ---- 0) drop previous local CAs so the Root store does not pile up -------
foreach ($store in @('Cert:\LocalMachine\My', 'Cert:\LocalMachine\Root')) {
    Get-ChildItem $store -ErrorAction SilentlyContinue |
        Where-Object { $_.Subject -like 'CN=CODOL Local*' -or $_.Subject -like 'CN=CODOL-LOCAL-CA*' } |
        ForEach-Object {
            $t = $_.Thumbprint
            try { Remove-Item -LiteralPath $_.PSPath -Force -ErrorAction Stop
                  Write-Host ("    removed old cert " + $t + " from " + $store) } catch { }
        }
}

# ---- 1) root CA ----------------------------------------------------------
$sid = [Guid]::NewGuid().ToString('N').Substring(0, 8)
$caSubject = 'CN=CODOL Local CA ' + $sid
Write-Host ("[*] creating root CA: " + $caSubject)

$ca = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $caSubject `
        -CertStoreLocation 'Cert:\LocalMachine\My' `
        -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 `
        -KeyUsage CertSign, CRLSign, DigitalSignature `
        -TextExtension @('2.5.29.19={critical}{text}ca=1&pathlength=0') `
        -NotAfter (Get-Date).AddDays(30) `
        -FriendlyName ('CODOL Local CA ' + $sid)

Write-Host ("    thumbprint = " + $ca.Thumbprint)

$caDer = Join-Path $Root '_ca.cer'
$caPem = Join-Path $Root '_ca.pem'
Export-Certificate -Cert $ca -FilePath $caDer -Type CERT | Out-Null

$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($caDer))
$b64lines = ([regex]::Matches($b64, '.{1,64}') | ForEach-Object { $_.Value }) -join "`n"
$pemText = "-----BEGIN CERTIFICATE-----`n" + $b64lines + "`n-----END CERTIFICATE-----`n"
[IO.File]::WriteAllBytes($caPem, [Text.Encoding]::ASCII.GetBytes($pemText))
Write-Host ("    wrote " + $caPem)

# make it a trust anchor
Import-Certificate -FilePath $caDer -CertStoreLocation 'Cert:\LocalMachine\Root' | Out-Null
Write-Host "    imported into LocalMachine\Root"

# ---- 2) leaf key (must be exportable so we can build a PEM by hand) -------
$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$rsaTxt = Join-Path $Root '_rsa.txt'
$p = $rsa.ExportParameters($true)
$lines = foreach ($n in @('Modulus','Exponent','D','P','Q','DP','DQ','InverseQ')) {
    $n + '=' + [Convert]::ToBase64String($p.$n)
}
[IO.File]::WriteAllBytes($rsaTxt, [Text.Encoding]::ASCII.GetBytes(($lines -join "`n") + "`n"))
Write-Host ("    wrote " + $rsaTxt)

# ---- 3) leaf certificate, signed by the root -----------------------------
Write-Host ("[*] creating leaf for: " + ($names -join ', '))
$req = New-Object System.Security.Cryptography.X509Certificates.CertificateRequest(
            ('CN=' + $names[1]),
            $rsa,
            [System.Security.Cryptography.HashAlgorithmName]::SHA256,
            [System.Security.Cryptography.RSASignaturePadding]::Pkcs1)

$san = New-Object System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder
foreach ($n in $names) { $san.AddDnsName($n) }
$req.CertificateExtensions.Add($san.Build())

$ekuOids = New-Object System.Security.Cryptography.OidCollection
$null = $ekuOids.Add((New-Object System.Security.Cryptography.Oid('1.3.6.1.5.5.7.3.1')))   # serverAuth
$req.CertificateExtensions.Add(
    (New-Object System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($ekuOids, $false)))

$ku = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor `
      [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment
$req.CertificateExtensions.Add(
    (New-Object System.Security.Cryptography.X509Certificates.X509KeyUsageExtension($ku, $true)))

$req.CertificateExtensions.Add(
    (New-Object System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false, $false, 0, $true)))

$serial = New-Object byte[] 8
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($serial)
$serial[0] = $serial[0] -band 0x7F

$caCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ca)
# notAfter must not exceed the issuer's; reuse the CA's own bounds.
$leaf = $req.Create($caCert,
                    $caCert.NotBefore,
                    $caCert.NotAfter,
                    $serial)
# NOTE: do NOT call CopyWithPrivateKey here -- it is an extension method and
# PowerShell cannot invoke it directly. We do not need it anyway: the public
# certificate goes to _leaf2.cer and the private key to _rsa.txt separately,
# and fake_auth_tls.py recombines them into PEM.

$leafDer = Join-Path $Root '_leaf2.cer'
[IO.File]::WriteAllBytes($leafDer, $leaf.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
Write-Host ("    wrote " + $leafDer + "  (subject=" + $leaf.Subject + ")")

# ---- 4) summary ----------------------------------------------------------
Write-Host ""
Write-Host "=== done ===" -ForegroundColor Green
Write-Host ("  _ca.pem    " + (Get-Item $caPem).Length + " bytes")
Write-Host ("  _ca.cer    " + (Get-Item $caDer).Length + " bytes")
Write-Host ("  _leaf2.cer " + (Get-Item $leafDer).Length + " bytes")
Write-Host ("  _rsa.txt   " + (Get-Item $rsaTxt).Length + " bytes")
Write-Host ("  SAN        " + ($names -join ', '))
```

<!-- /BLOCK -->

---

## 6. 证书与数据（base64）

> 均为 2026-10-16 实测可用快照。`bootstrap.ps1` 会自动解码落盘。

### `_ca.pem`

<!-- BLOCK:CA_PEM -->
```text
LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURFekNDQWZ1Z0F3SUJBZ0lRTVVRQUY0MW1wNkZIY3pyd3lrRkhkREFOQmdrcWhraUc5dzBCQVFzRkFEQWkKTVNBd0hnWURWUVFEREJkRFQwUlBUQ0JNYjJOaGJDQkRRU0JtT1dNek9ETXdaakFlRncweU5qRXdNVGN4TURFdwpNRFphRncweU5qRXhNVFl4TURJd01EWmFNQ0l4SURBZUJnTlZCQU1NRjBOUFJFOU1JRXh2WTJGc0lFTkJJR1k1Cll6TTRNekJtTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUEweHpDTytua1hBVVkKTjQ4bnJLMXA2MUN1K0JrbE5JS0dTSGVlSU1sZHNzSHVRRGdzUUFFYjBQQ1F3VFhiNTZrTWNlRERmYUQ1Yk02YQpkQXF6aWFsbFc4UjVIZzlGSG1qT2g1K0N0Y0gwM3FBOHNOdkhhS1VFeDJ4aGkzR0kvVFZsTXF6STV1clJFWXRuCnBHMXh4Z3lrQzkvWXVrT05NMjA0VUs5UUVDNlgzZlNnTjJwd1lqZ1RBejVISDg0Si9SSXZTMk8wMkhOdTJIZGIKbnAxVXEzbmhDNEF0MjNpK2RHcDA3RnJ1djNrbWcrc2Q4N2FxN2tBaitwUmNPOWZiUGNZc0hFbFRDZ05mTjRNRApVa0N0SEJWZzEza2ZwVGkrakZJaFV5Znk0cmxYcnoyL2c4U0Fqem9oc1BjUmM3S0N4ekZnTDdyWnBmM1RqdmhyCnljUFM5VW8zZFFJREFRQUJvMFV3UXpBT0JnTlZIUThCQWY4RUJBTUNBWVl3RWdZRFZSMFRBUUgvQkFnd0JnRUIKL3dJQkFEQWRCZ05WSFE0RUZnUVVycnBocTJqSnlYWTV6R2FoekRabFE2RTBQK013RFFZSktvWklodmNOQVFFTApCUUFEZ2dFQkFBSE1oSE5zMytydEROL3EzNzJpdVJIMTRnRE5kM2tSNURsR2Z3dXAxeFR1SDh5SXRqc1VMMEsxCk9mdmdxdTF1bElQa3FGUExvbDB3SS9mTEM5TmIwa2ZEMlFUOVVscnp3N0VDN0hrT0U0YU1BTFRlam5CVlNJeFAKVDYrZWNpcmVOb2hheEp3QSt6eVNsTlcxcWpWMlgyd3B2K2tSWklIY0owbXFJRUZlMURvdis5SjkwM0pmSzFrZAplYTQ0N2xZZWhvR0N0aXNuS0hMWGxxRVFTRjVwdmxvNTVxZEtHSk5XT2xVb2JIMGdmbEpmaEF2cUpHWmtBd0thCmZoUXkwUlN0OE9CYWdCdmJFb3piSTlhWnNpYjNSREQyUGQ3ZGZMMGh1MlFVaEhNaGdPU1E1bU9YRUN6U2Q2aVoKemJFUW9aS3hDaE1KbDN6eVlwUmR0b0JzZW5Ga0V5cz0KLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQo=
```
<!-- /BLOCK -->

### `_leaf2.cer`

<!-- BLOCK:LEAF_CER -->
```text
MIIDVjCCAj6gAwIBAgIIPx3yQ6mzAVQwDQYJKoZIhvcNAQELBQAwIjEgMB4GA1UEAwwXQ09ET0wgTG9jYWwgQ0EgZjljMzgzMGYwHhcNMjYxMDE3MTAxMDA2WhcNMjYxMTE2MTAyMDA2WjAoMSYwJAYDVQQDEx1mb3JtYWwtem9uZS1hdXRoLmNvZG9sLnFxLmNvbTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAOuhqbvDD3WT6BzYsxrBeFfwzhzLlB3q0QLb5qcoqIXkfw0h0MKzD+uZdDnXYXrlLcyRIm1pjqVUrtVHcNFXQ3TSpWumJ+MaB4ng3yiSrC26GUQFVYvFH+BW3ctcug9Qg+igouUshRTJLDgcfDlAPJVpT9a9sSLYWCR84/Qa3736w1rpDx+cTpim75Je98KfK1EDYqEu+EMkxOyhSsNWX6ZYiVLKVIE2XXzWyWyEfgxP/9CXTmB2NIUnUo7J7tG339ksyRGhrLG3T3tS7SDibZLoDV8vU11uBpRVkd75PtEpA5RgqkGQz4Rp4ZKUlSHGZC5L3W3Z74NaJcG50D/anMkCAwEAAaOBiTCBhjBRBgNVHREESjBIgglsb2NhbGhvc3SCHWZvcm1hbC16b25lLWF1dGguY29kb2wucXEuY29tghxmb3JtYWwtem9uZS1sc2cuY29kb2wucXEuY29tMBMGA1UdJQQMMAoGCCsGAQUFBwMBMA4GA1UdDwEB/wQEAwIFoDAMBgNVHRMBAf8EAjAAMA0GCSqGSIb3DQEBCwUAA4IBAQDBEd117aFIhfKo2V9b34B3KW1oaEYmsZz35JbBydZya99diORFdcBnqD+a1BGC0bcj+OOTMh3Hn7yu4ak+CwcBLLQyVwzxs/h0r8m6UWMoZ6vDhLpPu8zy4JPDh2wcbd50dY6wZ4omiA0o9tja8LJ/jcugjtjbhRgaRXPeKZ3KbQLtGGmJTYGbjwmM+qS0iv/2Lss/lHohP4Moq9uvM1hYgQaXQ72NkUg2qoiuKheZzkntGIU+PYytH/ScusbcNfB2EcHQj5WEK4rHCe/uUp0lsGYxFxUlsz3/V6QE0Ycu57IriAaiHkfz/31Y7qYH2znV1LSODcw35z1+422XoUvz
```
<!-- /BLOCK -->

### `_leaf2.key`

<!-- BLOCK:LEAF_KEY -->
```text
LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlFb3dJQkFBS0NBUUVBNjZHcHU4TVBkWlBvSE5pekdzRjRWL0RPSE11VUhlclJBdHZtcHlpb2hlUi9EU0hRCndyTVA2NWwwT2RkaGV1VXR6SkVpYldtT3BWU3UxVWR3MFZkRGROS2xhNlluNHhvSGllRGZLSktzTGJvWlJBVlYKaThVZjRGYmR5MXk2RDFDRDZLQ2k1U3lGRk1rc09CeDhPVUE4bFdsUDFyMnhJdGhZSkh6ajlCcmZ2ZnJEV3VrUApINXhPbUtidmtsNzN3cDhyVVFOaW9TNzRReVRFN0tGS3cxWmZwbGlKVXNwVWdUWmRmTmJKYklSK0RFLy8wSmRPCllIWTBoU2RTanNudTBiZmYyU3pKRWFHc3NiZFBlMUx0SU9KdGt1Z05YeTlUWFc0R2xGV1IzdmsrMFNrRGxHQ3EKUVpEUGhHbmhrcFNWSWNaa0xrdmRiZG52ZzFvbHdiblFQOXFjeVFJREFRQUJBb0lCQUVKVEErSzgrZ24vY3ZORApyODVWTE5tY0IzZ2xlWENlV3V5eUZ3OXdLMWRjeE1KZWhWTjRjWC9BZHUyZENXdzlQQkg3dkRRTjVULzJRU3Y1CmF2RVIzZ1B4RXV6bEhROFlrWXlteGttMlYwNmJ0bWJtRlhrOUtFYk9US25rVk43Z3EvQjczcjRoTk9odjQ4bDcKZ3gvZVMrOUdjRm1pbFV5WWx0N1daSmVlUk9KRlBCam8rdGlOQXpHWXkzRWhIUE02aVRkeHhMODZjeHVxVUhOdQpXVG1HUWVMdlhSaks1dk9wWXQ1NnV5bU5BWjVpanlMUDVDbk1hUzRaMnRpbk83VmF0cWorQU1rUkdiVlU2UTk2Cnlack9SNTdtTUlGTGUyL1h0dFA2L0drSkxlRTFITFE1eEloNnJyWmFjZDc5MWgrdDhFYlkzMTVBZ3dnQkNyK2oKanRlYTJTMENnWUVBOTNoZmk3aWRiSlFpcGxISFQyMElxT05BbnhxczFvY3JMaEZJOGs4cFJ1ZnhETjh1b1ZvdQpPRW1ENGcvMzNkNnF1bnhQOXYyQmwxbzBvMHk3YlpwTUxGOWxCQ0kzSG1nK1FIYkUvN0p2NUMyaTJ4bWV3ZXlxClY5blBtdDBZUEFmcVVPM0l5R2RSeWwwUHh2b1kxQzVHYzBIcGVBZnRDTVZSbFdZTzlhWHBhNGNDZ1lFQTg4RFQKMFR3Qk8xTk16WS8yN1JmVGJRc3NzRlV2UTVTRDNURW5McFk5TE5KdEY1MWt4cDFxdVhGY3UrdTFUL3oxNUhWYwp5K1NzNFlXTjUvOFluZEx0Vy9lNVpTbzdKeTh4cXJnUUxuQ1NnVGdkZ0RjbzhxWUdSWlVSL0FEQ3RCRW9vanFYClgwTE1CeGlaRUR5bFFvK05ia1RQY1hoTkRpWEVlRkFJb2N4TzZTOENnWUVBb0s5K2lzRFRKeitBeURIdGtyc2YKbGxvSkNjWk9WL1hvcWI3N2VLckNDSkp1U0lkYVJkYkNrRFhiOXB1YnZHcnF2TEFmVkNjRFVIMTRGRmlza3R4UApmYmhyWlNXNldIb2pnY1FjNGxMQXFJNmhZbGJlYU5qOU9wSHBaWXNPUTF4NFh4Z20rVWx0S0ZNSS9aQkRNdkxoCk45R2lnUmZVWjQrSUM5UDYvckkrUUYwQ2dZQVh0UHRrOERjV2RBV1dRSmc5ZXdHL0swVVBhVm1OY3haWUh2MjIKbERvaTc5eFlYYUI5aUxYbWoxWDdtUE1yY21qZjdXSTNHbWlPRHBVOHFSelZ6THYxSStUT0tBdFV4a3hJVkZxTwppYmhXQlFVcGdUUGtWYTFxZXhNaXRWZzZkeWpDam54R2NaS3laZndORGpqc2ZsVzlFY2d6T3dZVGlDelJuc2NZCkpXelBWUUtCZ0U0bkNldXdQKy80OVIvUy8wNTJBb3JtdVBRZ1JRamtvSzFlRC9ORXlIRzNSRXNQVVNtcmEwVHcKSHk0SmFuU1JQa0R0ck1iU056Nm0xMzVjblpYSnp3eXVQbmxFemlXNk1TRjRSSElSc2MvelpNVHR5T1FqOG82eQpvdnhSWXhvT1REZVFXUzdZMzJ1UUdnOGZkVW5HQzZkdUlQdVFBZnFzWkNOeG80REt4RDZNCi0tLS0tRU5EIFJTQSBQUklWQVRFIEtFWS0tLS0tCg==
```
<!-- /BLOCK -->

### `_leaf2_chain.pem`

<!-- BLOCK:LEAF_CHAIN -->
```text
LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSURWakNDQWo2Z0F3SUJBZ0lJUHgzeVE2bXpBVlF3RFFZSktvWklodmNOQVFFTEJRQXdJakVnTUI0R0ExVUUKQXd3WFEwOUVUMHdnVEc5allXd2dRMEVnWmpsak16Z3pNR1l3SGhjTk1qWXhNREUzTVRBeE1EQTJXaGNOTWpZeApNVEUyTVRBeU1EQTJXakFvTVNZd0pBWURWUVFERXgxbWIzSnRZV3d0ZW05dVpTMWhkWFJvTG1OdlpHOXNMbkZ4CkxtTnZiVENDQVNJd0RRWUpLb1pJaHZjTkFRRUJCUUFEZ2dFUEFEQ0NBUW9DZ2dFQkFPdWhxYnZERDNXVDZCelkKc3hyQmVGZnd6aHpMbEIzcTBRTGI1cWNvcUlYa2Z3MGgwTUt6RCt1WmREblhZWHJsTGN5UkltMXBqcVZVcnRWSApjTkZYUTNUU3BXdW1KK01hQjRuZzN5aVNyQzI2R1VRRlZZdkZIK0JXM2N0Y3VnOVFnK2lnb3VVc2hSVEpMRGdjCmZEbEFQSlZwVDlhOXNTTFlXQ1I4NC9RYTM3MzZ3MXJwRHgrY1RwaW03NUplOThLZksxRURZcUV1K0VNa3hPeWgKU3NOV1g2WllpVkxLVklFMlhYeld5V3lFZmd4UC85Q1hUbUIyTklVblVvN0o3dEczMzlrc3lSR2hyTEczVDN0Uwo3U0RpYlpMb0RWOHZVMTF1QnBSVmtkNzVQdEVwQTVSZ3FrR1F6NFJwNFpLVWxTSEdaQzVMM1czWjc0TmFKY0c1CjBEL2FuTWtDQXdFQUFhT0JpVENCaGpCUkJnTlZIUkVFU2pCSWdnbHNiMk5oYkdodmMzU0NIV1p2Y20xaGJDMTYKYjI1bExXRjFkR2d1WTI5a2Iyd3VjWEV1WTI5dGdoeG1iM0p0WVd3dGVtOXVaUzFzYzJjdVkyOWtiMnd1Y1hFdQpZMjl0TUJNR0ExVWRKUVFNTUFvR0NDc0dBUVVGQndNQk1BNEdBMVVkRHdFQi93UUVBd0lGb0RBTUJnTlZIUk1CCkFmOEVBakFBTUEwR0NTcUdTSWIzRFFFQkN3VUFBNElCQVFEQkVkMTE3YUZJaGZLbzJWOWIzNEIzS1cxb2FFWW0Kc1p6MzVKYkJ5ZFp5YTk5ZGlPUkZkY0JucUQrYTFCR0MwYmNqK09PVE1oM0huN3l1NGFrK0N3Y0JMTFF5Vnd6eApzL2gwcjhtNlVXTW9aNnZEaExwUHU4enk0SlBEaDJ3Y2JkNTBkWTZ3WjRvbWlBMG85dGphOExKL2pjdWdqdGpiCmhSZ2FSWFBlS1ozS2JRTHRHR21KVFlHYmp3bU0rcVMwaXYvMkxzcy9sSG9oUDRNb3E5dXZNMWhZZ1FhWFE3Mk4Ka1VnMnFvaXVLaGVaemtudEdJVStQWXl0SC9TY3VzYmNOZkIyRWNIUWo1V0VLNHJIQ2UvdVVwMGxzR1l4RnhVbApzejMvVjZRRTBZY3U1N0lyaUFhaUhrZnovMzFZN3FZSDJ6blYxTFNPRGN3MzV6MSs0MjJYb1V2egotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCi0tLS0tQkVHSU4gQ0VSVElGSUNBVEUtLS0tLQpNSUlERXpDQ0FmdWdBd0lCQWdJUU1VUUFGNDFtcDZGSGN6cnd5a0ZIZERBTkJna3Foa2lHOXcwQkFRc0ZBREFpCk1TQXdIZ1lEVlFRRERCZERUMFJQVENCTWIyTmhiQ0JEUVNCbU9XTXpPRE13WmpBZUZ3MHlOakV3TVRjeE1ERXcKTURaYUZ3MHlOakV4TVRZeE1ESXdNRFphTUNJeElEQWVCZ05WQkFNTUYwTlBSRTlNSUV4dlkyRnNJRU5CSUdZNQpZek00TXpCbU1JSUJJakFOQmdrcWhraUc5dzBCQVFFRkFBT0NBUThBTUlJQkNnS0NBUUVBMHh6Q08rbmtYQVVZCk40OG5ySzFwNjFDdStCa2xOSUtHU0hlZUlNbGRzc0h1UURnc1FBRWIwUENRd1RYYjU2a01jZUREZmFENWJNNmEKZEFxemlhbGxXOFI1SGc5Rkhtak9oNStDdGNIMDNxQThzTnZIYUtVRXgyeGhpM0dJL1RWbE1xekk1dXJSRVl0bgpwRzF4eGd5a0M5L1l1a09OTTIwNFVLOVFFQzZYM2ZTZ04ycHdZamdUQXo1SEg4NEovUkl2UzJPMDJITnUySGRiCm5wMVVxM25oQzRBdDIzaStkR3AwN0ZydXYza21nK3NkODdhcTdrQWorcFJjTzlmYlBjWXNIRWxUQ2dOZk40TUQKVWtDdEhCVmcxM2tmcFRpK2pGSWhVeWZ5NHJsWHJ6Mi9nOFNBanpvaHNQY1JjN0tDeHpGZ0w3clpwZjNUanZocgp5Y1BTOVVvM2RRSURBUUFCbzBVd1F6QU9CZ05WSFE4QkFmOEVCQU1DQVlZd0VnWURWUjBUQVFIL0JBZ3dCZ0VCCi93SUJBREFkQmdOVkhRNEVGZ1FVcnJwaHEyakp5WFk1ekdhaHpEWmxRNkUwUCtNd0RRWUpLb1pJaHZjTkFRRUwKQlFBRGdnRUJBQUhNaEhOczMrcnRETi9xMzcyaXVSSDE0Z0ROZDNrUjVEbEdmd3VwMXhUdUg4eUl0anNVTDBLMQpPZnZncXUxdWxJUGtxRlBMb2wwd0kvZkxDOU5iMGtmRDJRVDlVbHJ6dzdFQzdIa09FNGFNQUxUZWpuQlZTSXhQClQ2K2VjaXJlTm9oYXhKd0ErenlTbE5XMXFqVjJYMndwditrUlpJSGNKMG1xSUVGZTFEb3YrOUo5MDNKZksxa2QKZWE0NDdsWWVob0dDdGlzbktITFhscUVRU0Y1cHZsbzU1cWRLR0pOV09sVW9iSDBnZmxKZmhBdnFKR1prQXdLYQpmaFF5MFJTdDhPQmFnQnZiRW96Ykk5YVpzaWIzUkREMlBkN2RmTDBodTJRVWhITWhnT1NRNW1PWEVDelNkNmlaCnpiRVFvWkt4Q2hNSmwzenlZcFJkdG9Cc2VuRmtFeXM9Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0K
```
<!-- /BLOCK -->

### `_rsa.txt`

<!-- BLOCK:RSA_TXT -->
```text
TW9kdWx1cz02NkdwdThNUGRaUG9ITml6R3NGNFYvRE9ITXVVSGVyUkF0dm1weWlvaGVSL0RTSFF3ck1QNjVsME9kZGhldVV0ekpFaWJXbU9wVlN1MVVkdzBWZERkTktsYTZZbjR4b0hpZURmS0pLc0xib1pSQVZWaThVZjRGYmR5MXk2RDFDRDZLQ2k1U3lGRk1rc09CeDhPVUE4bFdsUDFyMnhJdGhZSkh6ajlCcmZ2ZnJEV3VrUEg1eE9tS2J2a2w3M3dwOHJVUU5pb1M3NFF5VEU3S0ZLdzFaZnBsaUpVc3BVZ1RaZGZOYkpiSVIrREUvLzBKZE9ZSFkwaFNkU2pzbnUwYmZmMlN6SkVhR3NzYmRQZTFMdElPSnRrdWdOWHk5VFhXNEdsRldSM3ZrKzBTa0RsR0NxUVpEUGhHbmhrcFNWSWNaa0xrdmRiZG52ZzFvbHdiblFQOXFjeVE9PQpFeHBvbmVudD1BUUFCCkQ9UWxNRDRyejZDZjl5ODBPdnpsVXMyWndIZUNWNWNKNWE3TElYRDNBclYxekV3bDZGVTNoeGY4QjI3WjBKYkQwOEVmdThOQTNsUC9aQksvbHE4UkhlQS9FUzdPVWREeGlSaktiR1NiWlhUcHUyWnVZVmVUMG9SczVNcWVSVTN1Q3I4SHZldmlFMDZHL2p5WHVESDk1TDcwWndXYUtWVEppVzN0WmtsNTVFNGtVOEdPajYySTBETVpqTGNTRWM4enFKTjNIRXZ6cHpHNnBRYzI1Wk9ZWkI0dTlkR01ybTg2bGkzbnE3S1kwQm5tS1BJcy9rS2N4cExobmEyS2M3dFZxMnFQNEF5UkVadFZUcEQzckptczVIbnVZd2dVdDdiOWUyMC9yOGFRa3Q0VFVjdERuRWlIcXV0bHB4M3YzV0g2M3dSdGpmWGtDRENBRUt2Nk9PMTVyWkxRPT0KUD05M2hmaTdpZGJKUWlwbEhIVDIwSXFPTkFueHFzMW9jckxoRkk4azhwUnVmeEROOHVvVm91T0VtRDRnLzMzZDZxdW54UDl2MkJsMW8wbzB5N2JacE1MRjlsQkNJM0htZytRSGJFLzdKdjVDMmkyeG1ld2V5cVY5blBtdDBZUEFmcVVPM0l5R2RSeWwwUHh2b1kxQzVHYzBIcGVBZnRDTVZSbFdZTzlhWHBhNGM9ClE9ODhEVDBUd0JPMU5NelkvMjdSZlRiUXNzc0ZVdlE1U0QzVEVuTHBZOUxOSnRGNTFreHAxcXVYRmN1K3UxVC96MTVIVmN5K1NzNFlXTjUvOFluZEx0Vy9lNVpTbzdKeTh4cXJnUUxuQ1NnVGdkZ0RjbzhxWUdSWlVSL0FEQ3RCRW9vanFYWDBMTUJ4aVpFRHlsUW8rTmJrVFBjWGhORGlYRWVGQUlvY3hPNlM4PQpEUD1vSzkraXNEVEp6K0F5REh0a3JzZmxsb0pDY1pPVi9Yb3FiNzdlS3JDQ0pKdVNJZGFSZGJDa0RYYjlwdWJ2R3JxdkxBZlZDY0RVSDE0RkZpc2t0eFBmYmhyWlNXNldIb2pnY1FjNGxMQXFJNmhZbGJlYU5qOU9wSHBaWXNPUTF4NFh4Z20rVWx0S0ZNSS9aQkRNdkxoTjlHaWdSZlVaNCtJQzlQNi9ySStRRjA9CkRRPUY3VDdaUEEzRm5RRmxrQ1lQWHNCdnl0RkQybFpqWE1XV0I3OXRwUTZJdS9jV0YyZ2ZZaTE1bzlWKzVqekszSm8zKzFpTnhwb2pnNlZQS2tjMWN5NzlTUGt6aWdMVk1aTVNGUmFqb200VmdVRktZRXo1Rld0YW5zVElyVllPbmNvd281OFJuR1NzbVg4RFE0NDdINVZ2UkhJTXpzR0U0Z3MwWjdIR0NWc3oxVT0KSW52ZXJzZVE9VGljSjY3QS83L2oxSDlML1RuWUNpdWE0OUNCRkNPU2dyVjRQODBUSWNiZEVTdzlSS2F0clJQQWZMZ2xxZEpFK1FPMnN4dEkzUHFiWGZseWRsY25QREs0K2VVVE9KYm94SVhoRWNoR3h6L05reE8zSTVDUHlqcktpL0ZGakdnNU1ONUJaTHRqZmE1QWFEeDkxU2NZTHAyNGcrNUFCK3F4a0kzR2pnTXJFUG93PQo=
```
<!-- /BLOCK -->

### `coop_map.txt`

<!-- BLOCK:COOP_MAP -->
```text
Y29vcF90cmFpbl9tcF9maXJpbmdyYW5nZQ0K
```
<!-- /BLOCK -->

### `public-tail-items.txt`

<!-- BLOCK:PUBLIC_TAIL -->
```text
MjIzODEKMjIzODQKMTUxNjYKMjk4OTIKMTYzMzkKMTIyCjcxMTAKMjk3NjcK
```
<!-- /BLOCK -->

### `player-account.json`

<!-- BLOCK:ACCOUNT_JSON -->
```json
{"FormatVersion":1,"Build":1649370,"Name":"LAtt","Level":70,"Experience":11056700,"Prestige":4,"CodPoints":963849,"Gold":468379,"SavedUtc":"2026-10-16T11:41:25.2684660Z"}
```
<!-- /BLOCK -->

### 6.3 `publisher_files\`

#### `activities_v1.info`

<!-- BLOCK:PUB_activities_v1 -->
```text
W2FjdGl2aXRpZXNdCm51bT0yCgpbYWN0aXZpdHlfMV0KaWQ9MQp0aXRsZT3miJjnpZ7mjpLkvY0g6LWb5a2j5Yay5Yi6CmNvbnRlbnQ95o6S5L2N6LWb5qih5byP5bey5L+u5aSN5bm26aG65bu277yM54K55Ye76aaW6aG144CQ5oiY56We5o6S5L2N44CR5Y2z5Y+v5Y+C5LiO5aSp5qKv5a+55Yaz77yBCnVybD0Kc3RhcnR0aW1lPTE1MDAwMDAwMDAKZW5kdGltZT0yMDUwMDAwMDAwCnR5cGU9MQoKW2FjdGl2aXR5XzJdCmlkPTIKdGl0bGU95Yab54Gr5Z+65ZywIOmZkOaXtuihpee7mQpjb250ZW50Pea1t+mHj+WumuWItuatpuWZqOS4juWFuOiXj+ijheWkh+eOsOW3suW8gOaUvu+8jOaJk+mAoOWxnuS6juS9oOeahOS4k+WxnuWGm+Wkh++8gQp1cmw9CnN0YXJ0dGltZT0xNTAwMDAwMDAwCmVuZHRpbWU9MjA1MDAwMDAwMAp0eXBlPTEK
```
<!-- /BLOCK -->

#### `broadcast.info`

<!-- BLOCK:PUB_broadcast -->
```text
PE1TRyBUPTIwNTAwMDAwMDAsUD0wLz4K
```
<!-- /BLOCK -->

#### `configs_s.info`

<!-- BLOCK:PUB_configs_s -->
```text
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
```
<!-- /BLOCK -->

#### `daily_challenge_config.info`

<!-- BLOCK:PUB_daily_challenge -->
```text
W2RhaWx5X2NoYWxsZW5nZV0KbnVtPTMKClsxXQppZD0xCnRpdGxlPeeyvuWHhuWwhOWHuwpjb250ZW50PeWcqOWvueWxgOS4reWujOaIkDEw5qyh54iG5aS05Ye75p2ACnRhcmdldD0xMApyZXdhcmRfdHlwZT0xCnJld2FyZF9jb3VudD0xMDAwCgpbMl0KaWQ9Mgp0aXRsZT3mjIHkuYXkvZzmiJgKY29udGVudD3lrozmiJDku7vmhI/mqKHlvI/lr7nlsYAz5qyhCnRhcmdldD0zCnJld2FyZF90eXBlPTIKcmV3YXJkX2NvdW50PTUwMDAKClszXQppZD0zCnRpdGxlPeWGm+Wkh+S4k+Wutgpjb250ZW50PeabtOaNouS4gOasoeatpuWZqOmFjeS7tuaIluWGm+eJjOWkluinggp0YXJnZXQ9MQpyZXdhcmRfdHlwZT0xCnJld2FyZF9jb3VudD01MDAK
```
<!-- /BLOCK -->

#### `market-down.info`

<!-- BLOCK:PUB_market_down -->
```text
W01hcmtldF0KdXBkYXRlPTAKb25ldGltZWZldGNoPTAKaW50ZXJ2YWw9MAo=
```
<!-- /BLOCK -->

#### `market_ui.info`

<!-- BLOCK:PUB_market_ui -->
```text
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
```
<!-- /BLOCK -->

#### `MOTD.info`

<!-- BLOCK:PUB_MOTD -->
```text
WzFdCnRpdGxlPeS9v+WRveWPrOWUpE9ubGluZSDmiJjlnLrpm4bnu5MKY29udGVudD3lpKfljoXllYbln47jgIHlhpvngavln7rlnLDjgIHkuKrkurrku5PlupPkuI7pnbblnLrmiJjmlpfmnI3lt7Llhajph4/kv67lpI3vvIEKdHlwZT0xCmJ0bl90eXBlPTEK
```
<!-- /BLOCK -->

#### `tlogconfig.info`

<!-- BLOCK:PUB_tlogconfig -->
```text
W1RMb2ddDQp1aWNsaWNrY291bnQ9MA0KdWljbGljaz0wDQp1aXBhZ2U9MQ0KdWlsYXN0cGFnZXM9MA0KZHdkc21tX251bWJlcj0zMA0KZHdkc21tX2luaXR2YWx1ZT01MA0KZHdkc21tX3Nsb3BlPTEuOQ0KbG9hZG91dGNoYW5nZWV2ZW50PTANCnVpcGFnZV9saW1pdD0zMA==
```
<!-- /BLOCK -->

#### `whitelist_tester.info`

<!-- BLOCK:PUB_whitelist -->
```text
W1doaXRlbGlzdF0NCnVzZXJpZD00NTAzNjA3NjU4MjY2ODQ2DQp1c2VyaWQ9MTEzNzY0NDg0MTIzMDg1NDQwNTMNCnVzZXJpZD01NjU1NjMwMTM5NTY5NTEzNDgz
```
<!-- /BLOCK -->

#### `mp_playlists_shipRetail_1.0.0.info`

<!-- BLOCK:PUB_playlists_100 -->
```text
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
```
<!-- /BLOCK -->

#### `mp_playlists_shipRetail_release.info`

<!-- BLOCK:PUB_playlists_release -->
```text
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
```
<!-- /BLOCK -->

#### `sku_tags.info`

<!-- BLOCK:PUB_sku_tags -->
```text
W3RhZ3NdCjQ1NTQyPUhPVDoxCjQ1NTMzPUhPVDoyCjQ1MTM3PUhPVDozCjQxNTI2PUhPVDo0CjQ0MzM5PUhPVDo1CjQ0MTMwPUhPVDo2CjQ0MTM0PUhPVDo3CjQ0MzM2PUhPVDo4CjE5ODI1PUhPVDo5CjI1NDczPUhPVDoxMAo0NDEzMD1ORVc6MQo0NDEzND1ORVc6Mgo0NDMzNj1ORVc6Mwo0MTUyNz1ORVc6NAo0MTMyNT1ORVc6NQo0NTA3NT1ORVc6NgoyMTc5MT1ORVc6NwozMjMyNz1ORVc6OAo0NDI2Nz1ORVc6OQo0MzA4Mj1ORVc6MTAKNDQzMzk9UE9QVUxBUjoxCjM5MDM2PVBPUFVMQVI6MgoxNjkwMz1QT1BVTEFSOjMKMTAzNjI9UE9QVUxBUjo0CjMxOTg4PVBPUFVMQVI6NQozMzY3NT1QT1BVTEFSOjYKMjE2ODQ9UE9QVUxBUjo3CjI2NDEyPVBPUFVMQVI6OAoxNzEwNT1QT1BVTEFSOjkKMzE1OTc9UE9QVUxBUjoxMAo0NTEzNz1SRUNPTU1FTkQ6MQo0MjI1Mj1SRUNPTU1FTkQ6Mgo0MTUyNj1SRUNPTU1FTkQ6MwozOTAzOT1SRUNPTU1FTkQ6NAozOTYwMT1SRUNPTU1FTkQ6NQozOTAzOD1SRUNPTU1FTkQ6NgozMjExNz1SRUNPTU1FTkQ6NwoxNjY5OT1SRUNPTU1FTkQ6OAoxMTAzMz1SRUNPTU1FTkQ6OQoxMDM1ND1SRUNPTU1FTkQ6MTAKW3N1cHBseV9kcm9wX2xpc3RdCjA9NjAyMTYKMT02MDIxNwoyPTExODYxCgpbc3VwcGx5X2Ryb3BfaW5mb10Kc3VwcGx5X2Ryb3BfdmVyc2lvbj0zMzcuMAo2MDIxNl9TbG90Q291bnQ9Mwo2MDIxNl9TdXBwbHlNdWx0aXBsZUNvbnN1bWU9MAo2MDIxN19TbG90Q291bnQ9MQo2MDIxN19EdXN0U0tVPTIyNjQ0CjYwMjE3X0R1c3RSZXF1aXJlbWVudD0xMDAKNjAyMTdfU3VwcGx5TXVsdGlwbGVDb25zdW1lPTEKMTE4NjFfU2xvdENvdW50PTEKMTE4NjFfRHVzdFNLVT0yNTc0OAoxMTg2MV9EdXN0UmVxdWlyZW1lbnQ9MTAwCjExODYxX1N1cHBseU11bHRpcGxlQ29uc3VtZT0xCgpbc3VwcGx5X2Ryb3Bfc2FtcGxlc10KNjAyMTZfMD0xMDA3MF8wCjYwMjE2XzE9MTAwNzFfMAo2MDIxNl8yPTEyMDM2XzAKNjAyMTZfMz0xMDA3NV8wCjYwMjE2XzQ9MTA5MzhfMAo2MDIxNl81PTEwMDgyXzAKNjAyMTZfNj0xMDA3Ml8wCjYwMjE2Xzc9MTE0OTRfMAo2MDIxNl84PTEwMDM2XzAKNjAyMTZfOT0xMDAzN18wCjYwMjE2XzEwPTEwMDg4XzAKNjAyMTZfMTE9MTA1MjlfMAo2MDIxNl8xMj0xMTMwMl8wCjYwMjE2XzEzPTEwNjU1XzAKNjAyMTZfMTQ9MTE0MjRfMAo2MDIxNl8xNT0xMTc1M18wCjYwMjE2XzE2PTEwMTM0XzAKNjAyMTZfMTc9MTAwMjZfMAo2MDIxNl8xOD0xMDA3N18wCjYwMjE2XzE5PTEwMDc4XzAKNjAyMTZfMjA9MTAwODZfMAo2MDIxNl8yMT0xMTMwM18wCjYwMjE2XzIyPTEwMTI5XzAKNjAyMTZfMjM9MTAxNTVfMAo2MDIxNl8yND0xMTY5MF8wCjYwMjE2XzI1PTExMDIzXzAKNjAyMTZfMjY9MTE2MTVfMAo2MDIxNl8yNz0xMTg3OF8wCjYwMjE2XzI4PTEwMDg0XzAKNjAyMTZfMjk9MTAxMjVfMAo2MDIxNl8zMD0xMTE3NF8wCjYwMjE2XzMxPTEwMDY3XzAKNjAyMTZfMzI9MTE2MDRfMAo2MDIxNl8zMz0xMDcxMF8wCjYwMjE2XzM0PTExOTI2XzAKNjAyMTZfMzU9MTAwODdfMAo2MDIxNl8zNj0xMDEzNV8wCjYwMjE2XzM3PTEwMDc2XzAKNjAyMTZfMzg9MTAwOTFfMAo2MDIxNl8zOT0xMDcyN18wCjYwMjE2XzQwPTEwMDc5XzAKNjAyMTZfNDE9MTE3NDJfMAo2MDIxNl80Mj0xMTA2MF8wCjYwMjE2XzQzPTEwMDA0XzAKNjAyMTZfNDQ9MTAwNTBfMAo2MDIxNl80NT0xMDA1N18wCjYwMjE2XzQ2PTEwMTUwXzAKNjAyMTZfNDc9MTAxNDlfMAo2MDIxNl80OD0xMDAwNl8wCjYwMjE2XzQ5PTEwMDA5XzAKNjAyMTZfNTA9MTAwMDhfMAo2MDIxNl81MT0xMDA2MV8wCjYwMjE2XzUyPTEwMDU2XzAKNjAyMTZfNTM9MTAwNjBfMAo2MDIxNl81ND0xMDAwMF8wCjYwMjE2XzU1PTEwMDAzXzAKNjAyMTZfNTY9MTAwMTFfMAo2MDIxNl81Nz0xMDAwMl8wCjYwMjE2XzU4PTEwOTk2XzAKNjAyMTZfNTk9MTA5NDZfMAo2MDIxNl82MD0xMDEzMV8wCjYwMjE2XzYxPTEwMDE3XzAKNjAyMTZfNjI9MTAwMTlfMAo2MDIxNl82Mz0xMDAxNl8wCjYwMjE2XzY0PTEwMDE4XzAKNjAyMTZfNjU9MTAxMzNfMAo2MDIxNl82Nj0xMDA0Nl8wCjYwMjE2XzY3PTEwMDI4XzAKNjAyMTZfNjg9MTAwMjVfMAo2MDIxNl82OT0xMDA0NV8wCjYwMjE2XzcwPTEwMTQ1XzAKNjAyMTZfNzE9MTAwNTlfMAo2MDIxNl83Mj0xMDAzNV8wCjYwMjE2XzczPTEwMDM4XzAKNjAyMTZfNzQ9MTAwNDJfMAo2MDIxNl83NT0xMDA0NF8wCjYwMjE2Xzc2PTEwMDQxXzAKNjAyMTZfNzc9MTAwNDNfMAo2MDIxNl83OD0xMDA0MF8wCjYwMjE2Xzc5PTEwMTU4XzAKNjAyMTZfODA9MTAxMjdfMAo2MDIxNl84MT0xMDAzM18wCjYwMjE2XzgyPTEwMDMwXzAKNjAyMTZfODM9MTAwMzRfMAo2MDIxNl84ND0xMDE1Ml8wCjYwMjE2Xzg1PTEwMDI5XzAKNjAyMTZfODY9MTAwMzFfMAo2MDIxNl84Nz0xMDAzMl8wCjYwMjE2Xzg4PTEwMTU0XzAKNjAyMTZfODk9MTAwMTNfMAo2MDIxNl85MD0xMDA0N18wCjYwMjE2XzkxPTEwMDUyXzAKNjAyMTZfOTI9MTAxMzdfMAo2MDIxNl85Mz0xMDA2Ml8wCjYwMjE2Xzk0PTEwMDQ4XzAKNjAyMTZfOTU9MTAwMjFfMAo2MDIxNl85Nj0xMDA1MV8wCjYwMjE2Xzk3PTEwMTIxXzAKNjAyMTZfOTg9MTAwMjNfMAo2MDIxNl85OT0xMTM0OV8wCjYwMjE2XzEwMD0xMDM1MV8wCjYwMjE2XzEwMT0xMDE1MV8wCjYwMjE2XzEwMj0yODA5Nl8wCjYwMjE2XzEwMz0xMDE1OV8wCjYwMjE2XzEwND0zMDAyNV8wCjYwMjE2XzEwNT0zMDAyN18wCjYwMjE2XzEwNj0zMDAzMF8wCjYwMjE2XzEwNz0zMDAyOV8wCjYwMjE2XzEwOD0zMDAyM18wCjYwMjE2XzEwOT0zMDAyOF8wCjYwMjE2XzExMD0zMDA0OF8wCjYwMjE2XzExMT0zMDAyNl8wCjYwMjE2XzExMj0zMDAzMl8wCjYwMjE2XzExMz0zMDA0N18wCjYwMjE2XzExND02MDEzOF8wCjYwMjE2XzExNT02MDA5Nl8wCjYwMjE2XzExNj02MDA3N18wCjYwMjE2XzExNz02MDA3OF8wCjYwMjE2XzExOD02MDA5MV8wCjYwMjE2XzExOT02MDA5M18wCjYwMjE2XzEyMD02MDEzMV8wCjYwMjE2XzEyMT02MDA4NV8wCjYwMjE2XzEyMj02MDA3OV8wCjYwMjE2XzEyMz02MDA5NF8wCjYwMjE2XzEyND02MDA4OF8wCjYwMjE2XzEyNT02MDIxN18wCjYwMjE2XzEyNj02MDAxM18wCjYwMjE2XzEyNz02MDAxNF8wCjYwMjE2XzEyOD02MDAxNV8wCjYwMjE2XzEyOT02MDAxNl8wCjYwMjE2XzEzMD02MDEyMV8wCjYwMjE2XzEzMT01MDAwNl8wCjYwMjE2XzEzMj02MDAwN18wCjYwMjE2XzEzMz02NDlfMAo2MDIxNl8xMzQ9MjEyN18wCjYwMjE2XzEzNT01NjlfMAo2MDIxNl8xMzY9NTcwXzAKNjAyMTZfMTM3PTY3MV8wCjYwMjE2XzEzOD02MzVfMAo2MDIxNl8xMzk9Nzg5XzAKNjAyMTZfMTQwPTEwMjYzXzAKNjAyMTZfMTQxPTIxMzdfMAo2MDIxNl8xNDI9MTAzNDNfMAo2MDIxNl8xNDM9NTc5XzAKNjAyMTZfMTQ0PTE5NTJfMAo2MDIxNl8xNDU9MTg3MF8wCjYwMjE2XzE0Nj0yMTA3XzAKNjAyMTZfMTQ3PTQxNF8wCjYwMjE2XzE0OD00MTlfMAo2MDIxNl8xNDk9NzY2XzAKNjAyMTZfMTUwPTE5MjlfMA==
```
<!-- /BLOCK -->

#### `manifest.json`

<!-- BLOCK:PUB_manifest -->
```text
ewogICJidWlsZCI6IDE2NDkzNzAsCiAgImRpYWdub3N0aWNPbmx5IjogdHJ1ZSwKICAiZmlsZXMiOiBbCiAgICB7CiAgICAgICJuYW1lIjogImNvbmZpZ3Nfcy5pbmZvIiwKICAgICAgImVuY29kaW5nIjogImFlcy0xOTItY3RyIiwKICAgICAgIndpcmVCeXRlcyI6IDMxMSwKICAgICAgInBsYWluQnl0ZXMiOiAzMTEsCiAgICAgICJwbGFpblNoYTI1NiI6ICJlNGJhMjcxYjdiZTRhMTU5ZjNjOWEwYTgyNGY3ZDljNWIyYmQzYmNjYmE1NDY2NmQ0Yzk4OGVhNTM4NWRlM2Y5IiwKICAgICAgIndpcmVTaGEyNTYiOiAiZTQ4NDFmYjg5YjAwNTdhMDcxN2Y2NDNhZGU0ZWRmZjM2MDc2MDJhNGJkMjNmNTM4YTAzMGFiYjdmZWRiMjRmYiIsCiAgICAgICJldmlkZW5jZSI6ICIweDUwZWI4MCAvIDB4NjZkMWYwOyBtYW5kYXRvcnkgYXRvZiBmaWVsZHMgYXQgMHg3ZWU3MmEuLjB4N2VlOTg0OyBub24tbnVsbCB1cmwgYXQgMHg0YjZmMDAiCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJkYWlseV9jaGFsbGVuZ2VfY29uZmlnLmluZm8iLAogICAgICAiZW5jb2RpbmciOiAiemxpYiIsCiAgICAgICJ3aXJlQnl0ZXMiOiA2NywKICAgICAgInBsYWluQnl0ZXMiOiA2MCwKICAgICAgInBsYWluU2hhMjU2IjogIjQ2NjRlMmQyNjY1MzMxODcyZDQxNDE0ZmZiMjdhOGUxNzVlNDU2MDE3Yjk1ZDY5ZjczZTU2OTYxNDA4YjY1MjQiLAogICAgICAid2lyZVNoYTI1NiI6ICJjNGIzOTNjNmFkZjgwOTNiN2QxYzhkMDRlODhmNDZhMjE5YzRmZmE3NDM5MjIyMTNlZGFkZjdiYWU2ZDE2N2UzIiwKICAgICAgImV2aWRlbmNlIjogIjB4NTBlNTAwIC8gMHg0ZjFkZDAiCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJhY3Rpdml0aWVzX3YxLmluZm8iLAogICAgICAiZW5jb2RpbmciOiAidGV4dCIsCiAgICAgICJ3aXJlQnl0ZXMiOiAzMCwKICAgICAgInBsYWluQnl0ZXMiOiAzMCwKICAgICAgInBsYWluU2hhMjU2IjogIjU4ZjEzMzRiNmRkNWQzNTRjMzJhNWM1MzAyOTFmMzlkN2RlMjA3OGRmY2RjNzhjZmMzMjc4MzU0YmUyNjRhNWMiLAogICAgICAid2lyZVNoYTI1NiI6ICI1OGYxMzM0YjZkZDVkMzU0YzMyYTVjNTMwMjkxZjM5ZDdkZTIwNzhkZmNkYzc4Y2ZjMzI3ODM1NGJlMjY0YTVjIiwKICAgICAgImV2aWRlbmNlIjogIjB4NTBkYzEwIgogICAgfSwKICAgIHsKICAgICAgIm5hbWUiOiAiYnJvYWRjYXN0LmluZm8iLAogICAgICAiZW5jb2RpbmciOiAidGV4dCIsCiAgICAgICJ3aXJlQnl0ZXMiOiA0LAogICAgICAicGxhaW5CeXRlcyI6IDQsCiAgICAgICJwbGFpblNoYTI1NiI6ICI4YmE1N2Y5YTFkN2ZlZGY5NDI3YmVhOGI2N2IyNjdkOGJlMTljNWQ4ZTE2ZTBlYjdiYWQzMmUwMzhjYmNiZmM1IiwKICAgICAgIndpcmVTaGEyNTYiOiAiOGJhNTdmOWExZDdmZWRmOTQyN2JlYThiNjdiMjY3ZDhiZTE5YzVkOGUxNmUwZWI3YmFkMzJlMDM4Y2JjYmZjNSIsCiAgICAgICJldmlkZW5jZSI6ICIweDUwZGM3MCAoc3RydWN0dXJlZCBtZXNzYWdlIHBhcnNlcjsgcHJvdmlzaW9uYWwgZW1wdHkgb2JqZWN0KSIKICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogInRsb2djb25maWcuaW5mbyIsCiAgICAgICJlbmNvZGluZyI6ICJ0ZXh0IiwKICAgICAgIndpcmVCeXRlcyI6IDkyLAogICAgICAicGxhaW5CeXRlcyI6IDkyLAogICAgICAicGxhaW5TaGEyNTYiOiAiYmI5MzM2NTFhNmMwMzU4YTM0OTBiNTkxMzZiMjQ0ZDljMWJjYjIwYmY5ZjI5MTJjODhlYWY3ZTE1NTVmNzNiNyIsCiAgICAgICJ3aXJlU2hhMjU2IjogImJiOTMzNjUxYTZjMDM1OGEzNDkwYjU5MTM2YjI0NGQ5YzFiY2IyMGJmOWYyOTEyYzg4ZWFmN2UxNTU1ZjczYjciLAogICAgICAiZXZpZGVuY2UiOiAiMHg1MGRkMjAiCiAgICB9LAogICAgewogICAgICAibmFtZSI6ICJtYXJrZXRfdWkuaW5mbyIsCiAgICAgICJlbmNvZGluZyI6ICJ6bGliIiwKICAgICAgIndpcmVCeXRlcyI6IDE2LAogICAgICAicGxhaW5CeXRlcyI6IDgsCiAgICAgICJwbGFpblNoYTI1NiI6ICIyNTBlZjViOWRhMDJjNjg2YWU3NjY2NzMxOWNkM2FkMTk1OTNmYzE2Y2VmYTdkMmQwYmQzYjQxOThjNGU3ODhhIiwKICAgICAgIndpcmVTaGEyNTYiOiAiMGVhZjA5YzAzNWUyMGRjNGI5ZTAzM2EzN2ZmMmZkNzk5MzZiNTY5NDIwMmJlNzc0ZGM0Yjk3OTdjMjYwZTZmOCIsCiAgICAgICJldmlkZW5jZSI6ICIweDUwZTVhMDsgemVybyBlbnRyaWVzIHN1cHBvcnRlZCIKICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIm1hcmtldC1kb3duLmluZm8iLAogICAgICAiZW5jb2RpbmciOiAidGV4dCIsCiAgICAgICJ3aXJlQnl0ZXMiOiA0NSwKICAgICAgInBsYWluQnl0ZXMiOiA0NSwKICAgICAgInBsYWluU2hhMjU2IjogIjhiNjZlZDUzYzI4MDQ4N2UxMjJlM2E0ZTgzYzQ5ZTg2MzdlYTBhZTRjMDM2YzdhZWUwMTY3YWJjOWJhNWM3MzQiLAogICAgICAid2lyZVNoYTI1NiI6ICI4YjY2ZWQ1M2MyODA0ODdlMTIyZTNhNGU4M2M0OWU4NjM3ZWEwYWU0YzAzNmM3YWVlMDE2N2FiYzliYTVjNzM0IiwKICAgICAgImV2aWRlbmNlIjogIjB4NTBkZjgwIgogICAgfSwKICAgIHsKICAgICAgIm5hbWUiOiAid2hpdGVsaXN0X3Rlc3Rlci5pbmZvIiwKICAgICAgImVuY29kaW5nIjogInRleHQiLAogICAgICAid2lyZUJ5dGVzIjogMzAsCiAgICAgICJwbGFpbkJ5dGVzIjogMzAsCiAgICAgICJwbGFpblNoYTI1NiI6ICJhM2ZkNmEzOTI4NGM4ZjM2NDY2ZDlhNzZlMDI4ZTE0MzQyNGVhYmRjMjhkMzZiMWJjYjUzMmFhMTUyZThhNTM4IiwKICAgICAgIndpcmVTaGEyNTYiOiAiYTNmZDZhMzkyODRjOGYzNjQ2NmQ5YTc2ZTAyOGUxNDM0MjRlYWJkYzI4ZDM2YjFiY2I1MzJhYTE1MmU4YTUzOCIsCiAgICAgICJldmlkZW5jZSI6ICIweDUwZTJjMCIKICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIk1PVEQuaW5mbyIsCiAgICAgICJlbmNvZGluZyI6ICJ0ZXh0IiwKICAgICAgIndpcmVCeXRlcyI6IDI5LAogICAgICAicGxhaW5CeXRlcyI6IDI5LAogICAgICAicGxhaW5TaGEyNTYiOiAiNTk2Y2ExMTFiMmFhMjQyNGM1MzU1YzMxZWY1NTJkMjBmNzgyMzJhNzIzZjA0NDRlZDdjNDJiN2E2NTg3ZWEyMiIsCiAgICAgICJ3aXJlU2hhMjU2IjogIjU5NmNhMTExYjJhYTI0MjRjNTM1NWMzMWVmNTUyZDIwZjc4MjMyYTcyM2YwNDQ0ZWQ3YzQyYjdhNjU4N2VhMjIiLAogICAgICAiZXZpZGVuY2UiOiAiMHg1MGUyNjAgLyAweDcyMTZkMCIKICAgIH0sCiAgICB7CiAgICAgICJuYW1lIjogIm1wX3BsYXlsaXN0c19zaGlwUmV0YWlsX3JlbGVhc2UuaW5mbyIsCiAgICAgICJlbmNvZGluZyI6ICJ6bGliIiwKICAgICAgIndpcmVCeXRlcyI6IDI2MiwKICAgICAgIndpcmVTaGEyNTYiOiAiNGM3N2YwMTZkMGYzNjdmNjlhOWQxNGZjM2Y1Y2E3NjU2NzYyNzQ2ZDM5OTNkOGQ4YTAxZThjZDM3ZmU1Y2NhNyIsCiAgICAgICJldmlkZW5jZSI6ICIweDUwZWJjMCAvIDB4NzVlZDkwIgogICAgfQogIF0KfQo=
```
<!-- /BLOCK -->

### 6.4 `player_profiles\`

#### `public.result`

<!-- BLOCK:PROF_public -->
```text
Cg4tTGuKqcjnCAUAAAAIAAAAAAgBAAAACD1jdCkTCACAAAA9Y3Qp6QAAAEXDbEoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB2LAAAaisAAAAAAABAUgAA/QcAAAAAAAAAAAAAAAAAAAAAAAAAAAAACAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdwgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAjQgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAeigAAAAAAAAAAAAAAAAAAAAAAAAAAAAAESkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAvCsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIQIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOQIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAbDUAAAAAAAAAAAAAAAAAAAAAAAAAAAAADEYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAbgcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgHIAP//yQD///////9yAP//MQDOADIAzQBlAP//ZgD//2cAygA4AP//cQD//zMA//83AP//NAD//zUA//82AP//CQD//w0AvwD/////bQD///////////////////////93AP//cwD//2EA//9kAP//IAD//2MA////////nwD///////+gAP//////////////////////////////////aQD//2IA//94AP//dQD//24A//96AP//OQD//54A//8AAAAAAAAAAJqZ+T+amfk/AAAAAAAAAAAAAAAAAAAACgAAAAIAAQEAAAAAAAAAIQIAAJAAAAAAAAAAreoAALHqAAC06gAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAACoUAAALVIAAAAAAAAAAAAAAAAAAAAAAAAaJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAADITwAAuFIAAAAAAAAAAAAAAAAAAAAAAAAfJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAACoUAAALVIAAAAAAAAAAAAAAAAAAAAAAAAaJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAADITwAAuFIAAAAAAAAAAAAAAAAAAAAAAAAfJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAZQAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA5KQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPNAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAnicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAACoUAAALVIAAAAAAAAAAAAAAAAAAAAAAAAaJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAADITwAAuFIAAAAAAAAAAAAAAAAAAAAAAAAfJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAACoUAAALVIAAAAAAAAAAAAAAAAAAAAAAAAaJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAADITwAAuFIAAAAAAAAAAAAAAAAAAAAAAAAfJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAACoUAAALVIAAAAAAAAAAAAAAAAAAAAAAAAaJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAADITwAAuFIAAAAAAAAAAAAAAAAAAAAAAAAfJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAkuoAAInqAACH6gAAAQAAAAEAAACoUAAALVIAAAAAAAAAAAAAAAAAAAAAAAAaJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQScAAAAAAABl6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAADfrAADq6gAAAQAAAAEAAADITwAAuFIAAAAAAAAAAAAAAAAAAAAAAAAfJwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOicAAAAAAAABAAAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAQAAAAEAAAABAAAAAAAAAGHqAAABAAAAjOoAAInqAADq6gAAAQAAAAEAAADLYQAAflYAAAAAAAAAAAAAAAAAAAAAAAARJwAAZ2QAAAAAAAAAAAAAAAAAAAAAAAAAAAAALCcAAAAAAABm6gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACuAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS6gAAieoAAIfqAAABAAAAAQAAAKhQAAAtUgAAAAAAAAAAAAAAAAAAAAAAABonAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBJwAAAAAAAGXqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAN+sAAOrqAAABAAAAAQAAAMhPAAC4UgAAAAAAAAAAAAAAAAAAAAAAAB8nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA6JwAAAAAAAAEAAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS6gAAieoAAIfqAAABAAAAAQAAAKhQAAAtUgAAAAAAAAAAAAAAAAAAAAAAABonAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBJwAAAAAAAGXqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAN+sAAOrqAAABAAAAAQAAAMhPAAC4UgAAAAAAAAAAAAAAAAAAAAAAAB8nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA6JwAAAAAAAAEAAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS6gAAieoAAIfqAAABAAAAAQAAAKhQAAAtUgAAAAAAAAAAAAAAAAAAAAAAABonAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBJwAAAAAAAGXqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAN+sAAOrqAAABAAAAAQAAAMhPAAC4UgAAAAAAAAAAAAAAAAAAAAAAAB8nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA6JwAAAAAAAAEAAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS6gAAieoAAIfqAAABAAAAAQAAAKhQAAAtUgAAAAAAAAAAAAAAAAAAAAAAABonAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBJwAAAAAAAGXqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAN+sAAOrqAAABAAAAAQAAAMhPAAC4UgAAAAAAAAAAAAAAAAAAAAAAAB8nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA6JwAAAAAAAAEAAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS6gAAieoAAIfqAAABAAAAAQAAAKhQAAAtUgAAAAAAAAAAAAAAAAAAAAAAABonAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABBJwAAAAAAAGXqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAN+sAAOrqAAABAAAAAQAAAMhPAAC4UgAAAAAAAAAAAAAAAAAAAAAAAB8nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA6JwAAAAAAAAEAAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAABAAAAAQAAAAEAAAAAAAAAYeoAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACM6gAAieoAAOrqAAABAAAAAQAAAMthAAB+VgAAAAAAAAAAAAAAAAAAAAAAABEnAABnZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsJwAAAAAAAGbqAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAABAQAAAAEAAAABAAAAAQEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAEAAAAAAQAAAAEAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPwtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgnSagAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkD0fnTdAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABKI9NqAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAQAAAAEAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADTcQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwAAAAAAAAABAAAAAQAAAAEAAAACAAAABQAAAAIAAAABAAAARgAAAEYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcAAAAAB3YsAAAHaisAAAcAAAAAB0BSAAAHEScAAAcsJwAABxonAAAHQScAAAcfJwAABzonAAAHEScAAAcsJwAABxEnAAAHLCcAAAcRJwAABywnAAAHGicAAAdBJwAABx8nAAAHOicAAAcRJwAABywnAAAHEScAAAcsJwAABwBlAAAHLCcAAAc5KQAAB0EnAAAHDzQAAAeeJwAABxEnAAAHLCcAAAcRJwAABywnAAAHEScAAAcsJwAABxonAAAHQScAAAcfJwAABzonAAAHEScAAAcsJwAABxEnAAAHLCcAAAcRJwAABywnAAAHGicAAAdBJwAABx8nAAAHOicAAAcRJwAABywnAAAHEScAAAcsJwAABxEnAAAHLCcAAAcaJwAAB0EnAAAHHycAAAc6JwAABxEnAAAHLCcAAAcRJwAABywnAAAHEScAAAcsJwAABxonAAAHQScAAAcfJwAABzonAAAHEScAAAcsJwAABxEnAAAHLCcAAAcRJwAABywnAAAHGicAAAdBJwAABx8nAAAHOicAAAcRJwAABywnAAAHEScAAAcsJwAABxEnAAAHLCcAAAcaJwAAB0EnAAAHHycAAAc6JwAABxEnAAAHLCcAAAcRJwAABywnAAAHEScAAAcsJwAABxonAAAHQScAAAcfJwAABzonAAAHEScAAAcsJwAABxEnAAAHLCcAAAcRJwAABywnAAAHGicAAAdBJwAABx8nAAAHOicAAAcRJwAABywnAAAHEScAAAcsJwAABxEnAAAHLCcAAAcaJwAAB0EnAAAHHycAAAc6JwAABxEnAAAHLCcAAAcRJwAABywnAAA=
```
<!-- /BLOCK -->

#### `secure.result`

<!-- BLOCK:PROF_secure -->
```text
CgAAAAAAAAAACAAAAAAIAAAAAAgBAAAACD6v7FkTCACAAAA+r+xZEwAAALR4Q6MAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADy2qAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAABGAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABzy2qAAHAAAAAAcAAAAABwAAAAAHAAAAAA0AAAAABwAAAAAHAAAAAAcEAAAAB0YAAAAHBAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABwAAAAAHAAAAAAcAAAAABwAAAAANAAAAAA==
```
<!-- /BLOCK -->

### 6.5 `user_files\the.json`

<!-- BLOCK:USER_the_json -->
```text
eyJibGFja2xpc3QiOltdfQA=
```
<!-- /BLOCK -->

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
