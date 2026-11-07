# 学习报告 018（重开）— `launch_chain.py` 第 150–269 行逐字节

**学习范围**：`chain_env()` / `stop_all()` / `status()` / `main()` 的参数与前置检查
**性质**：全实测
**★★★ 本报告逐字收录 `chain_env` 的**四段完整踩坑史**与**`--combined` 的唯一实测记录**

---

## 一、★★★★★ `chain_env(role)`（第 150–187 行）—— 九个环境变量

```python
def chain_env(role):
    env = os.environ.copy()
    env["OLMOD_PROCESS_ROLE"] = role
    env["OLMOD_DEDICATED_CONTROL_PORT"] = str(DEDICATED_PORT)   # 28961
    env["OLMOD_CLIENT_BRIDGE_PORT"] = str(BRIDGE_PORT)          # 28962
    env["OLMOD_ROOM_OWNER_PORT"] = str(ROOM_PORT)               # 28970
    env["OLMOD_CLIENT_INSTANCE"] = "1"
    env["OLMOD_CLAIM_LOBBY"] = "1"
    env["OLMOD_CONSOLE_LOG"] = os.environ.get("OLMOD_CONSOLE_LOG", "0")
    env["CODOL_FORCE_RECORD_VALIDATOR"] = "1"
    env["OLMOD_STATS_NAME_UTF8"] = "1"
    return env
```

### ★★★ 九个变量的最终值

| # | 变量 | 值 | 可被外部覆盖 |
|---|---|---|---|
| 1 | `OLMOD_PROCESS_ROLE` | `role` 参数（`client` / `combined`） | ✗ |
| 2 | `OLMOD_DEDICATED_CONTROL_PORT` | `28961` | ✗ |
| 3 | `OLMOD_CLIENT_BRIDGE_PORT` | `28962` | ✗ |
| 4 | `OLMOD_ROOM_OWNER_PORT` | `28970` | ✗ |
| 5 | `OLMOD_CLIENT_INSTANCE` | `1` | ✗ |
| 6 | **`OLMOD_CLAIM_LOBBY`** | **`1`** | ✗ ★★★ |
| 7 | `OLMOD_CONSOLE_LOG` | 默认 `0` | ★ **✓ 唯一可覆盖** |
| 8 | `CODOL_FORCE_RECORD_VALIDATOR` | `1` | ✗ |
| 9 | `OLMOD_STATS_NAME_UTF8` | `1` | ✗ |

★★★ **⇒ **只有 `OLMOD_CONSOLE_LOG` 可被外部覆盖**（`os.environ.get(..., "0")`），**
**其余八个是硬编码。**

★★★ **⇒ **没有 `NT10_INJECT`** —— 这是上一轮报告 009 的核心结论（`nt10.py` 因此不注入）。**

---

## 二、★★★★ `OLMOD_CONSOLE_LOG` 的**四段完整踩坑史**（第 158–174 行，逐字）

### 2.1 第一段：来源（第 158–159 行）

```python
# CodolLauncher.cs:380-397 sets OLMOD_CONSOLE_LOG=1 for the room owner and
# the dedicated, so match the proven configuration.
```

★ **⇒ 原始值 `1` 来自 `CodolLauncher.cs:380-397`（上游 C# 启动器）。**

### 2.2 第二段：★★★ 实测的阻塞证据（第 160–165 行）

```python
# OLMOD(console-log-configurable) 2026-10-12: the hard "1" made every game-server log
# line a synchronous write to CONOUT$, and CodolGameServer.log measured those writes
# itself -- LOGSTALL consoleDebugUs=28710 and consoleDebugUs=90836, i.e. 28.7-90.8 ms
# PER LINE. At ~18 lines/s the frame thread spent most of each frame blocked in
# WriteFile instead of computing, which is exactly what the frame telemetry shows:
# FRAMESTALL wallUs=50697..95377 with threadCpuUs=0..46875 (blocked, not busy), and the
```

★★★★ **⇒ 极其精确的性能实测数据：**

| 指标 | 值 |
|---|---|
| `LOGSTALL consoleDebugUs` | **28,710** 与 **90,836** |
| 换算 | **28.7 – 90.8 ms / 行** |
| 日志速率 | **~18 行/秒** |
| `FRAMESTALL wallUs` | **50,697 – 95,377**（50.7 – 95.4 ms） |
| `threadCpuUs` | **0 – 46,875** |
| 结论 | ★★★ **"blocked, not busy"**（阻塞，不是忙） |

★★★ **⇒ 论证链完整：**
```
每行日志同步写 CONOUT$
        ↓
28.7–90.8 ms/行 × 18 行/秒
        ↓
帧线程大部分时间阻塞在 WriteFile
        ↓
FRAMESTALL 的 wallUs 远大于 threadCpuUs
        ⇒ ★ "blocked, not busy" —— 阻塞而非计算
```

### 2.3 第三段：★★★ 甲方指令与默认值变更（第 166–168 行）

```python
# OLMOD(S8a console-default-off) 2026-10-12 甲方令「调0吧」：默认 '1' -> '0'。
# 理由：桌面快捷方式（restart_chain.ps1）从不导出这个变量，于是默认 '1' 一直生效；
# 显式外部值仍然优先（`$env:OLMOD_CONSOLE_LOG='1'` 可做带控制台的诊断运行）。
```

★★★ **⇒ 三条信息：**
```
① 甲方令「调0吧」（中文，2026-10-12）
② 桌面快捷方式 restart_chain.ps1 从不导出这个变量
   ⇒ 所以默认 '1' 一直生效（这是问题的根源）
③ 显式外部值仍优先（诊断时可设 '1'）
```

### 2.4 ★★★★★ 第四段：**自我纠偏**（第 169–173 行，逐字）

```python
# ★ 纠偏（第 61 轮实测，勿把本改动当结案）：console 开关**尚未被证明**是"进图卡顿"主因 ——
#   甲方 14:16 那次（他称"流畅"）进程环境仍是 OLMOD_CONSOLE_LOG=1，而 FRAMESTALL 与
#   "是否正在进图"强相关：14:17/14:18 各 2 次（max 0.09s）/ 14:19 进图 35 次（max 3.44s）/
#   14:20 32 次（max 1.74s）。本改动只是"让干净对照成为默认"。
#   判据与两条分支见 01-docs\30-topics\findings\交付-进图内存转储两进程3.43GB与console定因自我更正-20261012-73000.md §4
```

★★★★★ **⇒ 这是一段**极其罕见的、完整的自我否证**：**

| 时间 | `OLMOD_CONSOLE_LOG` | FRAMESTALL 次数 | max |
|---|---|---|---|
| **14:16**（甲方称"流畅"） | **仍是 `1`** | — | — |
| 14:17 | — | 2 | 0.09 s |
| 14:18 | — | 2 | 0.09 s |
| **14:19（进图）** | — | **35** | **3.44 s** |
| **14:20（进图）** | — | **32** | **1.74 s** |

★★★ **⇒ 结论（逐字）：**
> **console 开关尚未被证明是"进图卡顿"主因**
> **本改动只是"让干净对照成为默认"**

★★★ **⇒ 真实的相关变量是 **"是否正在进图"**，不是 console 输出。**

★ **⇒ 证据文件（含中文路径）：**
```
01-docs\30-topics\findings\交付-进图内存转储两进程3.43GB与console定因自我更正-20261012-73000.md §4
```

★★ **⇒ 该文件**不在交付包里**（`01-docs\` 是作者的证据目录）。**

### 2.5 ★★★ 四段注释的**方法论价值**

★★★ **⇒ 这是全包**最诚实**的一段记录：**
```
① 发现现象（日志慢）
② 实测量化（28.7-90.8 ms/行）
③ 提出假设（console 是卡顿主因）
④ 改默认值
⑤ ★★★ 用对照实验**否证**自己（14:16 流畅那轮 console 仍是 1）
⑥ 保留改动但**明确说明"不是结案"**
```

---

## 三、★★★★★ `CODOL_FORCE_RECORD_VALIDATOR`（第 175–181 行，逐字）

```python
# ★★★ 2026-10-07 04:5x -- 探针开关（甲方批准"把错的强制改成对的"）：
#   让进程内插件把**候选记录校验器** `sub_806F20`(RVA 0x406F20) 改成 `mov al,1; ret 4`，
#   于是客户端自己的成功路径跑起来：容器状态 2 → 门写 `ctx+4=1` → `AllocResultHandler(ok=1)`
#   → `server_index=0` → 进 `mmbook/mmstart`。**不再依赖 frida**（客户端虚拟空间 ~2 GB，注入进不去）。
#   依据与边界见 `01-docs\30-topics\findings\成果-A生效kind3带候选与D2首次触发及房间不再10秒被踢-20261007-0255.md` §11.4。
#   关掉：把这个键去掉或设成 "0" 即可（插件侧只在 == "1" 时打补丁）。
env["CODOL_FORCE_RECORD_VALIDATOR"] = "1"
```

### ★★★ 五条关键技术信息

| # | 信息 | 值 |
|---|---|---|
| 1 | 目标函数 | **`sub_806F20`**（RVA **`0x406F20`**） |
| 2 | 改成的字节 | **`mov al,1; ret 4`** |
| 3 | 触发链 | 容器状态 2 → 门写 `ctx+4=1` → `AllocResultHandler(ok=1)` → **`server_index=0`** → `mmbook/mmstart` |
| 4 | ★★★ 为什么不用 frida | **客户端虚拟空间 ~2 GB，注入进不去** |
| 5 | 关闭方式 | 去掉键或设 `"0"`（插件侧只在 `== "1"` 时打补丁） |

★★★ **⇒ 第 4 条是**架构级约束**：**
```
CODOL 是 32 位进程 ⇒ 虚拟地址空间上限 ~2 GB
        ↓
frida 注入需要额外内存 + 映射 ⇒ 进不去
        ↓
★ 所有内存修改必须在**进程内插件**里做
```

★★★ **⇒ 这解释了为什么整个方案要注入 4 个插件，而不是用 frida 外挂。**

★ **⇒ 依据文件（含中文路径）：**
```
01-docs\30-topics\findings\成果-A生效kind3带候选与D2首次触发及房间不再10秒被踢-20261007-0255.md §11.4
```

★★ **⇒ 标题揭示了两个现象：**
```
"成果-A生效"                → A 路线（注入式）成功
"kind3带候选"                → kind 3 类型 + 候选
"D2首次触发"                 → D2 场景
"房间不再10秒被踢"           → ★ 修复了"10 秒被踢"
```

---

## 四、★★★ `OLMOD_STATS_NAME_UTF8`（第 182–186 行）

```python
# ★★ 2026-10-07 15:2x -- 排行榜/好友名字编码切换到 **UTF-8**（单变量测试）。
#   实测：GBK 的 `Lifetime丷`（81 52）在大厅生涯榜渲染成「▮R」= 逐字节回退 ⇒ 该渲染管线
#   不是 GBK 解码。假设它按 UTF-8 解：UTF-8 的 丷（E4 B8 B7）应显示正确。
#   （StatsService/Friends2Service 读这个键，进程内 static 缓存，重启才生效。）
env["OLMOD_STATS_NAME_UTF8"] = "1"
```

★★★ **⇒ 完整的编码判定证据：**
```
GBK 的 丷 = 81 52
    ↓ 在生涯榜渲染成「▮R」
    ↓ 逐字节回退
⇒ 该渲染管线**不是** GBK 解码
    ↓ 假设按 UTF-8 解
UTF-8 的 丷 = E4 B8 B7 ⇒ 应正确
```

★★ **⇒ 且明确"进程内 static 缓存，重启才生效"** ——
**改这个值**必须重启客户端**。**

---

## 五、★★★ `stop_all()`（第 190–197 行）

```python
def stop_all():
    say("stopping client / nt10 / room owner / fake auth / local STUN ...")
    ps("Get-Process codoMP_client_shipRetail -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue")
    ps("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
       "Where-Object { $_.CommandLine -match 'nt10|fake_auth|stun_local' } | "
       "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }")
    ps("Get-Process ol_room_owner -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue")
    time.sleep(1.0)
```

### ★★★ 三个层次 + 一个刻意遗漏

| # | 目标 | 方式 |
|---|---|---|
| 1 | `codoMP_client_shipRetail` | 按**进程名** |
| 2 | Python 脚本 | 按**命令行正则** `nt10\|fake_auth\|stun_local` |
| 3 | `ol_room_owner` | 按**进程名** |

★★★ **⇒ 正则里**没有 `launch_chain`**（与 `stop.cmd:9` 的 `'nt10|fake_auth|stun_local|launch_chain'` 不同）。**

★★ **⇒ 这是**正确的差异**：`stop_all()` 是 `launch_chain` **自己**调用的，不能自杀。**
**（报告 002 已记录）**

★ **⇒ `time.sleep(1.0)` —— 给系统 1 秒回收句柄/端口。**

★★ **⇒ 注意：**没有杀 `Injector32.exe`** —— 与 `stop.cmd` 同样的遗漏（报告 002）。**

---

## 六、★★★ `status()`（第 200–209 行）

```python
def status():
    say("client pids      = %s" % (client_pids() or "none"))
    say("nt10 pids        = %s" % (nt10_pids() or "none"))
    say("room owner pids  = %s" % (room_pids() or "none"))
    L = listening()
    for port, name in ((AUTH_PORT, "fake auth"),
                       (ROOM_PORT, "room owner"), (BRIDGE_PORT, "client bridge"),
                       (DEDICATED_PORT, "dedicated control")):
        say("%-17s %d : %s" % (name, port, "LISTEN" if any(
            p.endswith(":" + str(port)) for p in L) else "-"))
```

★★★ **⇒ 报告**三个进程 + 四个端口**：**
```
进程：client / nt10 / room owner
端口：3074 (fake auth) / 28970 (room owner) / 28962 (client bridge) / 28961 (dedicated control)
```

★ **⇒ **没有报告 STUN 的 UDP 端口（3074/3478/19302）** —— 因为 `listening()` 用 `Get-NetTCPConnection`（只查 TCP）。**

★★★ **⇒ 这是一个**盲区**：STUN 是 UDP，`status()` 看不到它。**

---

## 七、★★★ `main()` 的参数（第 212–251 行）

```python
ap.add_argument("--check", action="store_true")
ap.add_argument("--stop", action="store_true")
ap.add_argument("--no-dedicated", action="store_true",
                help="skip step 3 (client reaches the lobby by itself)")
ap.add_argument("--combined", action="store_true",
                help="run the client as OLMOD_PROCESS_ROLE=combined (game server in-process)")
ap.add_argument("--tag", default=time.strftime("%Y%m%d-%H%M%S"))
```

### ★★★ 五个参数

| 参数 | 默认 | 作用 |
|---|---|---|
| `--check` | false | 只报告状态 |
| `--stop` | false | 停止所有 |
| `--no-dedicated` | false | ★ **跳过第 3 步（dedicated）** |
| `--combined` | false | ★★ **role=combined（战斗服进程内）** |
| `--tag` | 时间戳 | 日志文件名后缀 |

---

## 八、★★★★★ `--no-dedicated` 的**实测时间线**（第 220–224 行）

```python
# Single-variable isolation switch: the 20:17 round reached the lobby with the
# dedicated starting 4.5 minutes LATER, while 20:45/20:48/20:50 all had it up
# before the client's LSG connect and all died with
#   致命错误 / 与大厅服务失去连接
# after serving exactly one frame (`71/4`). `--no-dedicated` separates the two.
```

★★★★ **⇒ 精确的对照实验：**

| 轮次 | dedicated 启动时机 | 结果 |
|---|---|---|
| **20:17** | 客户端进大厅后 **4.5 分钟** | ★ **进大厅成功** |
| 20:45 | 客户端 LSG 连接**之前** | ★ 死：**`致命错误 / 与大厅服务失去连接`** |
| 20:48 | 同上 | 同上 |
| 20:50 | 同上 | 同上 |

★★★ **⇒ 失败特征（逐字）：**
```
致命错误 / 与大厅服务失去连接
after serving exactly one frame (`71/4`)
```

★★★ **⇒ 结论：**dedicated 起得太早会杀死会话。****

★ **⇒ 失败点精确到 **`71/4`（第 4 个任务后）**。**

★★ **⇒ 可能的机制：dedicated 起来后抢先占用端口/资源，导致客户端的 LSG 连接失败。**

★★★ **⇒ `--no-dedicated` 是**隔离变量**的临时开关，不是最终方案。**

---

## 九、★★★★★ `--combined` 的唯一实测记录（第 227–247 行，逐字）

```python
# ★★ 2026-10-05 22:3x -- THE ONLY ROLE THAT ACTUALLY SERVES GAMEPLAY IN THIS CLIENT.
#
# `game_server.md:197` verbatim:
#   默认 `combined` 保留旧部署；`client` 只安装最小 `Com_Frame` hook 服务 session capture，
#   **不运行 gameplay server**；`dedicated` 安装 gameplay hook、监听控制端口并在游戏线程
#   消费 `SessionStart`
# So under `OLMOD_PROCESS_ROLE=client` -- what our chain has been using -- the CLIENT PROCESS
# RUNS NO GAME SERVER AT ALL.  The game server lives only in the second (dedicated) process,
# which this client never talks to.
```

### ★★★★★ 三种 role 的**权威定义**（引自 `game_server.md:197`，中文原文）

| role | 行为 |
|---|---|
| **`combined`** | ★★★ **默认，保留旧部署（一个进程里全有）** |
| **`client`** | ★ **只安装最小 `Com_Frame` hook 服务 session capture，不运行 gameplay server** |
| **`dedicated`** | 安装 gameplay hook、监听控制端口并在游戏线程消费 `SessionStart` |

★★★ **⇒ 结论（逐字）：**
> So under `OLMOD_PROCESS_ROLE=client` -- **what our chain has been using** --
> the **CLIENT PROCESS RUNS NO GAME SERVER AT ALL**.
> The game server lives **only in the second (dedicated) process**,
> **which this client never talks to.**

★★★ **⇒ 这是**致命发现**：**
```
run.cmd 用 --no-dedicated
        ↓
role = client
        ↓
★ 客户端进程**完全不运行战斗服**
        ↓
★ 且 dedicated 进程**客户端从不与它通信**
        ↓
★ 结果：根本没有战斗服在跑
```

★★★ **⇒ 这解释了为什么"进大厅但打不了局"** —— 不是战斗服坏了，是**根本没起**。**

### 9.1 ★★★★★ 唯一一次客户端拨 UDP 28960 的实测（第 237–243 行）

```python
# MEASURED 2026-10-05 14:57:53, the ONLY time today the client ever dialled UDP 28960
# (`CodolGameServer.log`):
#   14:50:06 [combined/game-server] game server frame hook installed
#   14:54:19 [combined/game-server] ConfigureSession accepted bytes=22 endpoint=28960
#   14:57:53 [combined/game-server] udp packet peer=2130706433:22011 bytes=29 type=13
#   14:57:53 [combined/game-server] dtls peer=... packetType=3 state=established replyBytes=114
#   14:57:54 [combined/game-server] dtls rejected ... DTLS data authentication failed
```

★★★ **⇒ 五行日志，逐条解析：**

| 时间 | 日志 | 含义 |
|---|---|---|
| 14:50:06 | `[combined/game-server] game server frame hook installed` | ★ **role=combined** |
| 14:54:19 | `ConfigureSession accepted bytes=22 endpoint=28960` | 配置被接受 |
| **14:57:53** | `udp packet peer=2130706433:22011 bytes=29 type=13` | ★★★ **客户端拨号！** |
| 14:57:53 | `dtls ... packetType=3 state=established replyBytes=114` | ★ **DTLS 建立** |
| 14:57:54 | `dtls rejected ... DTLS data authentication failed` | ★★★ **认证失败** |

★★★ **⇒ `peer=2130706433` = `0x7F000001` = `127.0.0.1`**（十进制换算）**

★★★ **⇒ 这是**唯一一次**客户端真的拨了 UDP 28960（战斗服端口）。**

### 9.2 ★★★ 作者对这次失败的分析（第 244–247 行）

```python
# Note: role `combined`, a ONE-process deployment -- and the client dialled with NO
# `mmbook`/`mmstart`/`SessionStart` anywhere in that log.  The only thing wrong there was the
# key (`bytes=22` was a hand-made descriptor, `keyFingerprint=216:97:33:218`), and our backend
# now forwards the CLIENT's own descriptor, so the keys match.
```

★★★ **⇒ 三条结论：**
```
① role=combined，**单进程部署** ⇒ 客户端拨了号
② 日志里**没有** mmbook / mmstart / SessionStart
③ ★ 唯一的问题是**密钥**（bytes=22 是手工造的描述符，keyFingerprint=216:97:33:218）
```

★★★ **⇒ 且作者声称"现在已经修复"：**
> our backend **now forwards the CLIENT's own descriptor**, so **the keys match**.

★★★ **⇒ 这与上一轮报告 012 的 `LobbyProtocol.cpp:63-90` 注释**完全吻合**：**
> **THE SESSION KEY IS IN THE CLIENT'S OWN AUTH FRAME.**
> It is not minted here and it is not looked up: the auth server issues a 128-byte
> server ticket whose first 24 bytes are the key, and **the client forwards that
> ticket verbatim**.

★★★ **⇒ 两处独立记录指向同一个修复：后端转发客户端自己的描述符。**

---

## 十、★★★ 前置文件检查（第 262–267 行）

```python
for p, what in ((INJ, "Injector32"), (TGT, "client exe"), (ROOM, "ol_room_owner")):
    if not os.path.isfile(p):
        say("!! missing %s: %s" % (what, p))
        return 2
```

★★★ **⇒ 只检查**3 个文件**：**
```
<GAME>\Ayria\Injector32.exe
<GAME>\codoMP_client_shipRetail.exe
<GAME>\Ayria\ol_room_owner.exe
```

★★ **⇒ 与 `run.cmd` 的 11 项检查相比，这里**少了很多**（但 `run.cmd` 先跑）。**

---

## 十一、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `chain_env` 变量数 | **9 个** |
| 2 | ★★★ 唯一可覆盖 | **`OLMOD_CONSOLE_LOG`** |
| 3 | ★★★ **无 `NT10_INJECT`** | 确认（报告 009 结论） |
| 4 | ★★★ console 实测 | **28.7–90.8 ms/行**，18 行/秒 |
| 5 | ★★★ FRAMESTALL | **wallUs 50,697–95,377** vs **threadCpuUs 0–46,875** |
| 6 | ★★★★★ 自我纠偏 | **14:16"流畅"那轮 console 仍是 1** |
| 7 | ★ 真实相关变量 | **"是否正在进图"**（14:19 进图 35 次 max 3.44s） |
| 8 | ★★★ `sub_806F20` | RVA **`0x406F20`**，改 `mov al,1; ret 4` |
| 9 | ★★★ 触发链 | 容器状态2 → `ctx+4=1` → `AllocResultHandler(ok=1)` → **`server_index=0`** → `mmbook/mmstart` |
| 10 | ★★★ **frida 不可用** | **客户端虚拟空间 ~2 GB，注入进不去** |
| 11 | ★ GBK 证据 | `81 52` → `▮R`（逐字节回退） |
| 12 | ★ UTF-8 方案 | `E4 B8 B7` |
| 13 | `stop_all` 正则 | `nt10\|fake_auth\|stun_local`（**无 `launch_chain`**） |
| 14 | ★★ `status()` 盲区 | 用 `Get-NetTCPConnection` ⇒ **看不到 UDP STUN** |
| 15 | ★★★ dedicated 对照实验 | **20:17（晚 4.5 分钟）成功** / 20:45,48,50（早）全死 |
| 16 | ★★★ 失败特征 | **`致命错误 / 与大厅服务失去连接`**，`71/4` 后 |
| 17 | ★★★★★ **三种 role 定义** | `combined` 全有 / **`client` 不运行 gameplay server** / `dedicated` 只消费 SessionStart |
| 18 | ★★★ `--no-dedicated` 后果 | **客户端进程完全不运行战斗服** |
| 19 | ★★★ 唯一拨号实测 | 2026-10-05 **14:57:53**，UDP 28960 |
| 20 | ★★ `peer=2130706433` | = **`127.0.0.1`** |
| 21 | ★★★ DTLS 失败 | **`DTLS data authentication failed`** |
| 22 | ★★ 失败原因 | **密钥**（`bytes=22` 手工描述符，`keyFingerprint=216:97:33:218`） |
| 23 | ★★★ 修复 | **后端转发客户端自己的描述符** |
| 24 | 前置检查 | **3 个文件** |

---

## 十二、结论

### 1. ★★★★★ **最关键的一条**：`--no-dedicated` ⇒ 根本没有战斗服

```
run.cmd 固定 --no-dedicated
        ↓
role = client
        ↓
★ 客户端进程不运行 gameplay server（game_server.md:197）
★ 且客户端从不与 dedicated 进程通信
        ↓
★★★ 结果：**没有任何战斗服在跑**
```

★★★ **⇒ 这解释了"进大厅但打不了局"** —— 不是 bug，是**配置结果**。**

★ **⇒ 唯一让战斗服在进程内运行的 role 是 **`--combined`**。**

### 2. ★★★★★ `--combined` 是唯一成功拨号过的配置

★★ **实测 2026-10-05 14:57:53，客户端拨了 UDP 28960 并建立 DTLS。**
**唯一失败是**密钥**（`keyFingerprint=216:97:33:218`），且**作者声称已修**。**

### 3. ★★★★ `chain_env` 里有**四段完整的踩坑史**，质量极高

★ **尤其 `OLMOD_CONSOLE_LOG` 那段**自我纠偏**（14:16 流畅那轮 console 仍是 1），**
**是"假设→实测→否证"的典范。**

### 4. ★★★ **frida 不可用**是架构级约束（32 位进程 ~2 GB）

★ **⇒ 所有内存修改必须在**进程内插件**里做。**

### 5. ★★ `status()` 看不到 UDP STUN（只查 TCP）

---

## 十三、下一步

- `launch_chain.py` 第 269–445 行（`main()` 的实际执行流程）
- `nt10.py`（146,765 B）
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
