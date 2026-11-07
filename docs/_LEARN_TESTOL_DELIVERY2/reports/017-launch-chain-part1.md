# 学习报告 017（重开）— `launch_chain.py` 第 1–150 行逐字节

**学习范围**：`bundle\launch_chain.py`（25,009 B / 445 行）的 docstring + 常量 + 工具函数
**性质**：全实测
**★★★ 本报告逐字收录 docstring 的**五条设计论证**与**全部端口/API 常量**

---

## 一、★★★ 文件头（第 1–9 行）

```python
# -*- coding: utf-8 -*-
r"""launch_chain.py -- integrate the battle server into OUR launch path.

FIX 2026-10-05 22:41 -- this docstring became a raw string.  Non-raw, the
`Ayria\Injector32.exe` on line 26 raised
    SyntaxWarning: "\I" is an invalid escape sequence
on EVERY run, and because the warning goes to stderr, PowerShell wraps the whole
invocation in a NativeCommandError and reports a non-zero exit even when the
script succeeded -- which is exactly what `--stop` just did.  Content unchanged.
```

★★★ **⇒ 一个**极其具体的踩坑记录**：**
```
docstring 里写 `Ayria\Injector32.exe`
        ↓  \I 是无效转义序列
Python 抛 SyntaxWarning 到 stderr
        ↓
PowerShell 把 stderr 有输出 ⇒ 包成 NativeCommandError
        ↓
★ 脚本明明成功，退出码却是非零
        ↓
修复：docstring 改成 raw string（r"""..."""）
```

★★★ **⇒ 这是**Python + PowerShell 交互的经典陷阱**：**
**任何写到 stderr 的内容（包括 warning）都会被 PS 当成错误。**

★ **⇒ 影响范围：`run.cmd:106` 用 `cmd /k` 启动，不走 PS；**
**但 `launch_chain.py --stop` 如果被 PS 调用，就会误报失败。**

---

## 二、★★★★ `WHY THIS EXISTS`（第 12–29 行）—— 五条论证

### 2.1 ★★★ 为什么不用上游的 `CodolGame.py launch-dedicated`（第 13–19 行）

> `olmod-merge/tools/runtime/CodolGame.py launch-dedicated` starts the three
> processes (`ol_room_owner.exe` + client + dedicated), but **its client goes
> straight through `Injector32.exe` with NO `nt10.py`**. That **breaks LSG for us**
> (see `docs/LSG-移植差异清单.md:164-173`): **the session keys are NOT derivable
> server-side -- 1499 x 336 = 503,664 combinations, 0 hits**, and the real keys do
> **not appear anywhere in the 16,514-byte client stream**.
> **The ONLY source is `nt10.py` reading the client's process memory into `secrets.txt`.**

★★★★ **⇒ 这是**全包最重要的技术论断**：**
```
1499 × 336 = 503,664 种组合
穷举结果：★ 0 命中
真实密钥不出现在 16,514 字节的客户端流中
        ↓
★ 会话密钥**无法在服务端推导**
        ↓
唯一来源：nt10.py 读客户端进程内存 → secrets.txt
```

★★★ **⇒ 两个精确数字：**
```
1499 × 336 = 503,664        组合数
16,514 字节                 客户端流大小
```

★ **⇒ 出处：`docs/LSG-移植差异清单.md:164-173`。**

### 2.2 ★★★ 因此客户端**必须**由 `nt10.py` 拉起（第 21–22 行）

> So **the client MUST come from `nt10.py`**. Everything else (room owner +
> dedicated) **only consumes `SessionStart`**, so it can use the upstream path.

★★★ **⇒ 职责划分：**
```
client      →  必须 nt10.py 拉起（为了读密钥）
room owner  →  可用上游路径（只消费 SessionStart）
dedicated   →  可用上游路径（同上）
```

### 2.3 ★★★ 为什么不用 `relaunch.py`（第 24–29 行）

> **WHY NOT `relaunch.py`**: its `kill_game()` is
> ```
> Get-Process codoMP_client_shipRetail | Stop-Process -Force
> ```
> and **the dedicated is THE SAME EXE**, so every relaunch **silently kills the
> dedicated too**. Measured **2026-10-05 20:02**: `ol_room_owner.exe` pid **22072**
> (parent = the desktop launcher pid **8724**) was still alive, but **only ONE
> `codoMP_client_shipRetail.exe` remained**.

★★★ **⇒ 一个**架构性的坑**：**
```
client 与 dedicated 是**同一个 EXE**（codoMP_client_shipRetail.exe）
        ↓
按进程名杀 client ⇒ 把 dedicated 也杀了
```

★★ **⇒ 实测证据（2026-10-05 20:02）：**
```
ol_room_owner.exe       pid 22072  （父 = 桌面启动器 pid 8724）  存活
codoMP_client_shipRetail.exe        ★ 只剩 1 个（本该 2 个）
```

★★★ **⇒ 这就是为什么本包**固定 `--no-dedicated`**（`run.cmd:106`）——**
**避免同 EXE 双进程的杀进程问题。**

★ **⇒ 但代价是**没有独立战斗服**（报告 014 已记录）。**

### 2.4 ★★★ `WHAT THIS DOES`（第 31–38 行）—— 五步

```
1. stop client + nt10 watcher
2. start ol_room_owner.exe            (OLMOD_ROOM_OWNER_PORT=28970)
3. run nt10.py -> launches the client through Ayria\Injector32.exe -qa,
   inheriting the chain environment (nt10.py never touches these keys:
   it only sets 8 OLMOD_* of its own -- measured 2026-10-05)
4. start the dedicated: same exe, OLMOD_PROCESS_ROLE=dedicated
5. report the three listeners
```

★★★ **⇒ 第 3 步的括号是关键：**
> **`nt10.py` never touches these keys: it only sets 8 OLMOD_* of its own
> -- measured 2026-10-05**

★★★ **⇒ **`nt10.py` 只设 8 个 `OLMOD_*`**，不动 `launch_chain.py` 设的 9 个。**

★ **⇒ 这是**环境变量不冲突**的实测依据。**

★★★ **⇒ 但注意：第 3 步说的是"through `Ayria\Injector32.exe -qa`" ——
**这与 `nt10.py:1373` 的默认 `_inject = False` **矛盾**（报告 011 已记录）。**

### 2.5 ★★★ 环境变量（第 40–50 行）—— 引自 `CodolGame.py:297-319`

```
OLMOD_PROCESS_ROLE           client | dedicated | combined
OLMOD_DEDICATED_CONTROL_PORT 28961
OLMOD_CLIENT_BRIDGE_PORT     28962
OLMOD_ROOM_OWNER_PORT        28970
OLMOD_CLIENT_INSTANCE        1
OLMOD_CLAIM_LOBBY=1          REQUIRED
```

★★★ **⇒ `OLMOD_CLAIM_LOBBY` 的逐字引用（`CodolGame.py:311-314`）：**
> "route `lobby.codol.localhost` to **this process's own backend** instead of
>  the C# LobbyServer, so **MatchmakingService runs** and can send
>  `ConfigureSession` to the game server. Without it `QueryEndpoint` reports
>  **`sessionConfigured=false / bound=false`** and **no match can start**."

★★★ **⇒ 这是**大厅归属的唯一开关**，且明确标 `REQUIRED`。**

---

## 三、★★★ 路径常量（第 65–76 行）

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("OLMOD_BASE") or _HERE
# ★ 2026-10-20：客户端根目录可被 OLMOD_GAME_ROOT 覆盖（旧基线 TESTOL 仍是默认）。
#   这样「Final 版启动器」只需设这个环境变量即可复用整条启动链。
GAME = os.environ.get("OLMOD_GAME_ROOT") or r"D:\repo\03-live\client\TESTOL"
if not os.path.isdir(GAME):
    raise SystemExit("set OLMOD_GAME_ROOT to the client root (got %r)" % GAME)
PY = r"C:\Program Files\Python314\python.exe"
BASE_TOOLS = os.environ.get("OLMOD_BASE_TOOLS") or _HERE
INJ = os.path.join(GAME, r"Ayria\Injector32.exe")
TGT = os.path.join(GAME, "codoMP_client_shipRetail.exe")
ROOM = os.path.join(GAME, r"Ayria\ol_room_owner.exe")
```

### ★★★ 五个路径 + 三处作者机器泄漏

| 常量 | 值 | 可覆盖 |
|---|---|---|
| `_HERE` | 脚本所在目录 | — |
| `BASE` | `OLMOD_BASE` 或 `_HERE` | ✓ |
| **`GAME`** | **`D:\repo\03-live\client\TESTOL`** | ✓ `OLMOD_GAME_ROOT` |
| **`PY`** | **`C:\Program Files\Python314\python.exe`** | ★ **不可覆盖** |
| `BASE_TOOLS` | `OLMOD_BASE_TOOLS` 或 `_HERE` | ✓ |
| `INJ` | `<GAME>\Ayria\Injector32.exe` | 派生 |
| `TGT` | `<GAME>\codoMP_client_shipRetail.exe` | 派生 |
| `ROOM` | `<GAME>\Ayria\ol_room_owner.exe` | 派生 |

★★★ **⇒ **`PY` 是唯一**不可覆盖**的路径** —— 与 `run.cmd:21` 的硬编码**完全相同**。**
**⇒ 两处都要改才能换 Python 路径。**

★★★ **⇒ `GAME` 的默认 `D:\repo\03-live\client\TESTOL` 会在第 70 行抛 `SystemExit`。**
**⇒ `run.cmd:99` 设 `OLMOD_GAME_ROOT` 绕开（报告 014 已记录）。**

### ★★ 第 67–68 行注释揭示的"Final 版启动器"

> ★ 2026-10-20：客户端根目录可被 `OLMOD_GAME_ROOT` 覆盖（**旧基线 TESTOL 仍是默认**）。
>   这样「**Final 版启动器**」只需设这个环境变量即可复用整条启动链。

★★★ **⇒ "Final 版启动器" 是**另一个未交付的组件**（可能对应 `ol_launcher` target）。**

---

## 四、★★★★ 端口常量（第 78–97 行）—— 含 STUN 的完整踩坑史

```python
AUTH_PORT = 3074       # fake_auth_tls.py, TCP 127.0.0.1 -- see main() step 0
DEDICATED_PORT = 28961
BRIDGE_PORT = 28962
ROOM_PORT = 28970
```

### 4.1 ★★★ STUN 的第一段注释（第 82–86 行）

```python
# ★★ 2026-10-07 02:1x -- 本地 STUN 应答器（UDP）。hosts 里
#    `# CODOL-STUN-LOCAL-BEGIN … 127.0.0.1 stun1/2/3-tub.codol.qq.com` 就是为它准备的；
#    它不在跑时客户端 `getPublicAddr` 失败 ⇒ 遥测 `Address Fail|result = -3`
#    ⇒ `@SF_UI_DW_LIVE_DISCONNECTED` ⇒ 卡「连接中」（坏启动）。
#    以前没人负责启动它（本文件与冻结底座脚本里 0 引用），2026-10-07 02:02 就因此坏了一轮。
STUN_PORT = 3478
STUN_PORT2 = 19302
```

★★★ **⇒ 四个精确的遥测字符串：**
```
`Address Fail|result = -3`
`@SF_UI_DW_LIVE_DISCONNECTED`
卡「连接中」
```

★★ **⇒ 且**承认了一个疏漏**：**
> 以前没人负责启动它（**本文件与冻结底座脚本里 0 引用**），
> **2026-10-07 02:02 就因此坏了一轮**。

### 4.2 ★★★★★ STUN 的第二段注释（第 89–96 行）—— 抓包定因

```python
# ★★★ 2026-10-07 03:0x -- 客户端真正用的那一个口。抓包（`99-Tmp\cap-stun-d5.pcapng` 回环、
#    `99-Tmp\cap-nic-d6.pcapng` 网卡）显示 CODOL 的 `getPublicAddr` 发的是 **Demonware 私有 STUN**
#    （`14 02 00 00` / `1e 03 00`）到 **UDP 3074**，不是 RFC5389 的 3478/19302：
#      * 好轮：客户端 -> 185.34.107.128:3074，真服 200 ms 内回 15 字节 ⇒ 开局正常；
#      * 坏轮：同样两发 -> 127.0.0.1:3074（hosts 把 stunN-tub 指到 127.0.0.1），**0 回复**
#              ⇒ `71/3 Address Fail|result = -3` ⇒ `t≈54s 致命错误`。
#    ⇒ 只听 3478/19302 等于一个探针都收不到（这正是「STUN 假设被否证」的真因）。
STUN_PORT_DW = 3074
STUN_SCRIPT = os.environ.get("OLMOD_STUN") or os.path.join(_HERE, "stun_local.py")
```

★★★★★ **⇒ 完整的抓包证据链（逐字）：**

| 项 | 值 |
|---|---|
| 抓包文件（回环） | `99-Tmp\cap-stun-d5.pcapng` |
| 抓包文件（网卡） | `99-Tmp\cap-nic-d6.pcapng` |
| 请求字节 | **`14 02 00 00`** / **`1e 03 00`** |
| 目标端口 | **UDP 3074**（不是 3478/19302） |
| 好轮真服 | **`185.34.107.128:3074`** |
| 真服应答 | **15 字节**，**200 ms 内** |
| 坏轮 | 发到 `127.0.0.1:3074`，**0 回复** |
| 坏轮后果 | **`71/3 Address Fail\|result = -3`** ⇒ **`t≈54s 致命错误`** |
| 结论 | **"STUN 假设被否证"** |

★★★ **⇒ **这是全包最完整的"假设→实测→否证→修正"记录**（与 `stun_local.py` 的注释同源）。**

★ **⇒ `185.34.107.128` 是一台**还活着的真实 STUN 服务器**（好轮能通）。**

---

## 五、★★★★ `API` 常量（第 99–100 行）—— 要 hook 的 10 个函数

```python
API = ("OpenFileMappingW,CreateFileMappingW,MapViewOfFile,connect,sendto,"
       "WinHttpConnect,WinHttpOpenRequest,WinHttpSendRequest,z1,z2")
```

### ★★★ 逐个分类

| # | API | 类别 | 用途 |
|---|---|---|---|
| 1 | `OpenFileMappingW` | kernel32 | ★ **打开 TCLS 共享内存** |
| 2 | `CreateFileMappingW` | kernel32 | 创建映射 |
| 3 | `MapViewOfFile` | kernel32 | 映射视图 |
| 4 | `connect` | ws2_32 | TCP 连接 |
| 5 | `sendto` | ws2_32 | ★ UDP 发送 |
| 6 | `WinHttpConnect` | winhttp | HTTP |
| 7 | `WinHttpOpenRequest` | winhttp | HTTP |
| 8 | `WinHttpSendRequest` | winhttp | HTTP |
| 9 | **`z1`** | — | ★★★ **占位符** |
| 10 | **`z2`** | — | ★★★ **占位符** |

★★★ **⇒ `z1` / `z2` 是**占位符**，`nt10.py` 会过滤掉（`re.fullmatch(r"z\d+", x)`）。**
**用途：**保持代码洞/槽位编号稳定**（上一轮报告 007 已分析）。**

★★★ **⇒ 三组 API：**
```
kernel32  × 3  →  TCLS 共享内存（★ 关键：读登录票据）
ws2_32    × 2  →  网络
winhttp   × 3  →  HTTP（auth 走 HTTP over TLS）
```

★ **⇒ **注意：没有 `gethostbyname`！**
**但 `nt10.py:1335` 的默认 `--apis` 是 `connect,sendto,gethostbyname`。**
**⇒ `launch_chain.py` **覆盖了默认值**，**去掉了 `gethostbyname`**。**

★★ **⇒ 这是一个重要差异：**
```
nt10.py 默认    : connect, sendto, gethostbyname
launch_chain.py : OpenFileMappingW, CreateFileMappingW, MapViewOfFile,
                  connect, sendto, WinHttp*, z1, z2      ← 无 gethostbyname
```

★★★ **⇒ 因为 hosts 已经做了域名映射，不需要 hook `gethostbyname`。**

---

## 六、★★★ 工具函数（第 103–147 行）

```python
def say(m):
    print("  " + m, flush=True)

def ps(cmd):
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=True, text=True, errors="replace").stdout.strip()
```

### ★★★ `ps()` 的三个设计要点

```python
"-NoProfile"        ← 不加载用户 profile（★ 避免污染）
"-NonInteractive"   ← 不交互（★ 避免挂起）
"errors="replace""  ← ★ 解码错误不抛异常（避免中文路径问题）
```

★★★ **⇒ `errors="replace"` 是**关键的健壮性措施**（中文路径/输出不会崩）。**

### ★★★ 四个进程查询函数

```python
def client_pids():   # Get-Process codoMP_client_shipRetail
def nt10_pids():     # Get-CimInstance Win32_Process + CommandLine -match 'nt10'
def room_pids():     # Get-Process ol_room_owner
def listening():     # Get-NetTCPConnection -State Listen
```

★★★ **⇒ `nt10_pids()` 用**命令行正则**（不是进程名）：**
```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'nt10' }
```

★★ **⇒ 这印证了 `stop.cmd:6` 的 `taskkill /F /IM nt10.exe` 是**死代码**（报告 002 已记录）。**

### ★★★ `wait_port()`（第 138–147 行）

```python
def wait_port(port, seconds, label):
    """Bounded wait for a listener. CodolGame.py uses the same shape."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if any(p.endswith(":" + str(port)) for p in listening()):
            say("%s listening on %d" % (label, port))
            return True
        time.sleep(0.25)
    say("!! %s did NOT bind %d within %gs" % (label, port, seconds))
    return False
```

★★★ **⇒ 三个要点：**
```
① time.monotonic()      ← ★ 不受系统时间调整影响（正确做法）
② 轮询间隔 0.25s        ← 4 次/秒
③ 有界等待（seconds）    ← 不无限等
```

★ **⇒ `p.endswith(":" + str(port))` —— 只看端口，不看 IP。**
**⇒ 任何 IP 上该端口在监听就算通过。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 文件编码 | `# -*- coding: utf-8 -*-` |
| 2 | ★★★ docstring 是 raw string | `r"""` （修 `\I` 转义警告） |
| 3 | ★★★ 组合数 | **1499 × 336 = 503,664，0 命中** |
| 4 | ★★★ 客户端流大小 | **16,514 字节** |
| 5 | ★★ 密钥唯一来源 | `nt10.py` → `secrets.txt` |
| 6 | ★★★ 同 EXE 双进程 | client 与 dedicated 是**同一个 EXE** |
| 7 | ★ 实测 pid | room_owner 22072（父 8724） |
| 8 | ★★ `nt10.py` 只设 | **8 个 `OLMOD_*`** |
| 9 | 六个环境变量 | 引自 `CodolGame.py:297-319` |
| 10 | ★★★ `GAME` 默认 | **`D:\repo\03-live\client\TESTOL`** |
| 11 | ★★★ `PY` | **`C:\Program Files\Python314\python.exe`**（不可覆盖） |
| 12 | 端口 | 3074 / 28961 / 28962 / 28970 / 3478 / 19302 |
| 13 | ★★★ STUN 真端口 | **UDP 3074**（`STUN_PORT_DW`） |
| 14 | ★★★ STUN 请求字节 | **`14 02 00 00`** / **`1e 03 00`** |
| 15 | ★★ 好轮真服 | **`185.34.107.128:3074`**，15 字节，200 ms |
| 16 | ★★ 坏轮后果 | **`71/3 Address Fail\|result = -3`** ⇒ **`t≈54s 致命错误`** |
| 17 | ★★★ **hook 的 10 个 API** | 3 kernel32 + 2 ws2_32 + 3 winhttp + 2 占位 |
| 18 | ★★★ **无 `gethostbyname`** | 与 `nt10.py` 默认不同 |
| 19 | ★★ `ps()` 健壮性 | `-NoProfile` / `-NonInteractive` / `errors="replace"` |
| 20 | ★★ `wait_port()` | `time.monotonic()` + 0.25s 轮询 + 有界 |

---

## 八、结论

### 1. ★★★★★ `WHY THIS EXISTS` 的五条论证**全部有实测依据**

★★ **尤其第 1 条（503,664 组合 0 命中）和第 3 条（同 EXE 双进程）是**架构级的发现**。**

### 2. ★★★ 会话密钥的**不可推导性**是本包的**第一性原理**

```
密钥每会话随机 → 服务端推不出 → 只能读客户端内存 → 客户端必须由 nt10.py 拉起
```

### 3. ★★★ `--no-dedicated` 的根因是**同 EXE 双进程**

★ **⇒ 不是"不需要战斗服"，而是"不能安全地同时跑两个"。**

### 4. ★★★ `launch_chain.py` 的 `API` 列表**去掉了 `gethostbyname`**

★ **⇒ 因为 hosts 已做映射。**

### 5. ★★ STUN 的完整踩坑史（两段注释 + 抓包文件名 + 字节）

★★★ **⇒ 与 `stun_local.py` 的注释**互相印证**，构成完整的证据链。**

---

## 九、下一步

- `launch_chain.py` 第 150–445 行（`chain_env` / `stop_all` / `status` / `main`）
- `nt10.py`（146,765 B）—— 全包最大脚本
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
