# 学习报告 019（重开）— `launch_chain.py` 第 269–445 行（`main()` 完整流程）

**学习范围**：`main()` 的六个步骤 + 退出码表
**性质**：全实测
**★★★ 本报告逐字收录**六个步骤的全部实测依据**与**七个退出码**

---

## 一、★★★ 关于 `secrets.txt` 的**一次被回滚的实验**（第 269–274 行）

```python
# NOTE 2026-10-05 20:52 -- a "delete secrets.txt first" step was tried here for ~4 minutes
# and REVERTED. It is not the discriminator:
#   20:17 (reached the lobby)   stale COMPLETE file present  -> "LSG keys taken from the client snapshot"
#   20:45 (died, 与大厅服务失去连接) stale COMPLETE file present  -> same line
#   20:48 (died, same)          file DELETED                 -> "has no challenge yet"
# Leaving the writer's file alone matches the known-good 20:17 round, so it stays untouched here.
```

★★★ **⇒ 三次对照实验：**

| 轮次 | `secrets.txt` 状态 | 日志行 | 结果 |
|---|---|---|---|
| **20:17** | ★ **存在旧的 COMPLETE 文件** | `LSG keys taken from the client snapshot` | **进大厅** ✓ |
| 20:45 | 存在旧的 COMPLETE 文件 | 同上 | **死**（与大厅服务失去连接） |
| 20:48 | **已删除** | **`has no challenge yet`** | **死**（同上） |

★★★ **⇒ 结论（逐字）：**
> **It is not the discriminator.**
> **Leaving the writer's file alone matches the known-good 20:17 round,
> so it stays untouched here.**

★★ **⇒ 关键洞察：`secrets.txt` 的**存在与否不是成败判据**。**
**删除它反而导致 `has no challenge yet`。**

---

## 二、★★★ 步骤 0：`fake_auth_tls.py`（第 276–292 行）

```python
# --- 0. auth -------------------------------------------------------------
# MEASURED 2026-10-05 20:12: without this the client's SYN to
# 127.0.0.1:3074 is never answered, it never gets to 127.0.0.2:3074, and the
# screen stops at 100.  relaunch.py:111 started `fake_auth_tls.py`; this
# script replaced relaunch.py and dropped that step.
# Evidence: 01-findings\定因-卡100是认证服务没起来-20261005-2020.md
if os.environ.get("OLMOD_SKIP_AUX") == "1":
    say("OLMOD_SKIP_AUX=1 -> skip fake_auth_tls.py and stun_local.py")
else:
    say("starting fake_auth_tls.py (auth, 127.0.0.1:%d) ..." % AUTH_PORT)
    subprocess.Popen([PY, "-u", "fake_auth_tls.py"], cwd=BASE,
                     env=dict(os.environ, PYTHONUTF8="1"),
                     stdout=open(os.path.join(BASE, "re-auth.out.log"), "w"),
                     stderr=subprocess.STDOUT, creationflags=0x08000000)
    if not wait_port(AUTH_PORT, 20.0, "fake auth"):
        return 3
```

### ★★★ 完整的因果链（第 277–280 行）

```
没有 fake_auth_tls.py
        ↓
客户端的 SYN 到 127.0.0.1:3074 **无人应答**
        ↓
永远到不了 127.0.0.2:3074（大厅）
        ↓
★ 画面停在 **100**
```

★★★ **⇒ "卡 100" 的根因就是**认证服务没起来**。**

★ **⇒ 依据文件：`01-findings\定因-卡100是认证服务没起来-20261005-2020.md`**

### ★★★ 三处实现细节

| 项 | 值 | 说明 |
|---|---|---|
| 工作目录 | `cwd=BASE` | 脚本在 `bundle\` |
| 环境 | `PYTHONUTF8="1"` | ★ 强制 UTF-8 输出 |
| stdout | `re-auth.out.log`（`"w"` 覆盖） | ★ 每次清空 |
| `creationflags` | **`0x08000000`** | ★★★ **`CREATE_NO_WINDOW`** |
| 超时 | **20 秒** | `wait_port(AUTH_PORT, 20.0, ...)` |
| 失败退出码 | **3** | |

★★★ **⇒ `0x08000000` = `CREATE_NO_WINDOW`（不弹窗）。**
**`0x00000010` = `CREATE_NEW_CONSOLE`（弹窗，用于 room owner）。**

---

## 三、★★★ 步骤 0b：`stun_local.py`（第 294–331 行）

### 3.1 ★★★ 症状签名（第 295–299 行）

```python
# ★★ 2026-10-07 02:1x -- 补这一步。症状签名：客户端遥测 `71/3` 里
#   `UserWarning|…|Address Fail|result = -3` + `71/7` 的 `@SF_UI_DW_LIVE_DISCONNECTED`，
#   后端日志只服务到第 4~5 个任务（71/4 71/3 71/7 71/9）就不再问 `8/1`。
# 依据：`定因-AddressFail第三个候选-STUN超时-20261005-0150.md`、
#       `定因-坏启动真因-地址冲突与GBK-20261005-0125.md` §2。
# 幂等：已在跑就不重启（避免打断正在进行的会话）。
```

★★★ **⇒ 精确的症状签名：**
```
客户端遥测 71/3：`UserWarning|…|Address Fail|result = -3`
客户端遥测 71/7：`@SF_UI_DW_LIVE_DISCONNECTED`
后端日志：只服务到第 4~5 个任务（71/4 71/3 71/7 71/9）
          ★ 之后**不再问 `8/1`**
```

★★ **⇒ 两个依据文件（都在 `01-findings\`，未随包交付）：**
```
定因-AddressFail第三个候选-STUN超时-20261005-0150.md
定因-坏启动真因-地址冲突与GBK-20261005-0125.md  §2
```

### 3.2 ★★★ 幂等设计（第 300–309 行）

```python
def udp_ports():
    return set(ps("(Get-NetUDPEndpoint -EA SilentlyContinue | "
                  "ForEach-Object { $_.LocalPort }) -join ','").split(","))

if os.environ.get("OLMOD_SKIP_AUX") == "1":
    pass   # 3074 归他们的大厅
elif str(STUN_PORT_DW) in udp_ports():
    say("local STUN responder already listening on UDP %d (client's DW STUN port)"
        % STUN_PORT_DW)
else:
    ...
```

★★★ **⇒ 幂等判断：**UDP 3074 已在监听就不重启**。**
**注释理由："避免打断正在进行的会话"。**

★ **⇒ `udp_ports()` 用 `Get-NetUDPEndpoint`（与 `status()` 的 TCP 查询不同）。**

### 3.3 ★★★ 为什么列三个端口（第 313–316 行）

```python
# ★ 2026-10-07 02:2x -- 显式给端口（脚本自带示例就是多口形态；10-05 那次在跑的实例
#   也是多口）。只给 3478 时客户端仍可能 Address Fail（坏法 A，见
#   `定因-坏启动真因-地址冲突与GBK-20261005-0125.md` §3.3）。
#   28960 不列：它归 dedicated（UDP 0.0.0.0:28960），绑不上会被脚本跳过。
subprocess.Popen([PY, "-u", STUN_SCRIPT, "--ports",
                  "%d,%d,%d" % (STUN_PORT_DW, STUN_PORT, STUN_PORT2)],
```

★★★ **⇒ 端口选择的三条理由：**
```
① 必须含 3074（STUN_PORT_DW）—— 客户端真正用的
② 3478 / 19302 也列（历史 + 兼容）
③ ★★★ 28960 **不列** —— 归 dedicated（UDP 0.0.0.0:28960），绑不上会被跳过
```

★★ **⇒ 注释还揭示了一个**具体的失败模式**："坏法 A"（只给 3478 仍 Address Fail）。**

### 3.4 ★★ stdout 用 `"a"`（追加）而非 `"w"`

```python
stdout=open(os.path.join(BASE, "stun_local.out.log"), "a"),
```

★★ **⇒ 与 `re-auth.out.log` 的 `"w"`（覆盖）**不同**。**
**⇒ STUN 日志**累积**，auth 日志**每次清空**。**

### 3.5 ★★ 绑定失败退出码 **7**

```python
if str(STUN_PORT_DW) in udp_ports():
    say("local STUN listening on UDP %d" % STUN_PORT_DW)
else:
    say("!! local STUN did not bind UDP %d within 20s (坏启动风险：Address Fail)"
        % STUN_PORT_DW)
    return 7
```

★★★ **⇒ 20 秒内没绑上 ⇒ `return 7`（硬失败）。**

---

## 四、★★★ 步骤 1：`ol_room_owner.exe`（第 333–344 行）

```python
if os.environ.get("OLMOD_SKIP_AUX") == "1":
    # 2026-10-21：走他们大厅时不用我们的房间/候选那套；而且 ROOM_PORT(=28970) 与他们的 DS 撞端口。
    say("OLMOD_SKIP_AUX=1 -> room owner skipped (port %d belongs to their DS)" % ROOM_PORT)
else:
    say("starting ol_room_owner.exe ...")
    ro_env = os.environ.copy()
    ro_env["OLMOD_ROOM_OWNER_PORT"] = str(ROOM_PORT)
    subprocess.Popen([ROOM], cwd=GAME, env=ro_env,
                     creationflags=0x00000010)  # CREATE_NEW_CONSOLE
    if not wait_port(ROOM_PORT, 20.0, "room owner"):
        return 4
```

★★★ **⇒ `OLMOD_SKIP_AUX` 的**第三个作用**（第 335 行注释）：**
```
ROOM_PORT (=28970) 与他们的 DS 撞端口
```

★★ **⇒ 完整的 `OLMOD_SKIP_AUX=1` 效果（三处）：**
```
① 跳过 fake_auth_tls.py（第 282 行）
② 跳过 stun_local.py（第 305 行）
③ 跳过 ol_room_owner.exe（第 334 行）
```

★ **⇒ `creationflags=0x00000010` = `CREATE_NEW_CONSOLE`（**弹窗**，与 auth/stun 的 `NO_WINDOW` 不同）。**

★ **⇒ `cwd=GAME`（不是 `BASE`）—— 因为 `ol_room_owner.exe` 在游戏根。**

---

## 五、★★★★ 步骤 2：客户端（第 346–360 行）

```python
# --- 2. client, through nt10.py (LSG secrets source) ---------------------
say("starting client through nt10.py (role=%s) ..."
    % ("combined" if a.combined else "client"))
out = os.path.join(BASE, "n10run-%s.txt" % a.tag)
env = chain_env("combined" if a.combined else "client")
env["PYTHONUTF8"] = "1"
subprocess.Popen(
    [PY, "-u", "nt10.py", "--root", GAME, "--secs", "2400",
     "--delay", "0", "--out", os.path.basename(out), "--apis", API],
    cwd=BASE, env=env,
    stdout=open(os.path.join(BASE, "re-%s-nt10.out.log" % a.tag), "w"),
    stderr=subprocess.STDOUT, creationflags=0x08000000)
if not wait_port(BRIDGE_PORT, 120.0, "client bridge"):
    say("client did not reach its bridge port; see re-%s-nt10.out.log" % a.tag)
    return 5
```

### ★★★★★ `nt10.py` 的完整命令行（逐参数）

```
python.exe -u nt10.py
    --root  <GAME>
    --secs  2400            ← ★★★ 40 分钟观测时长
    --delay 0               ← ★★★ 不等待，立即装 hook
    --out   n10run-<tag>.txt
    --apis  <API 常量>
```

★★★ **⇒ 五个参数：**

| 参数 | 值 | 含义 |
|---|---|---|
| `--root` | `<GAME>` | 客户端根目录 |
| **`--secs`** | **`2400`** | ★ 观测 **40 分钟** |
| **`--delay`** | **`0`** | ★★★ **立即装 hook（不等待）** |
| `--out` | `n10run-<tag>.txt` | 输出文件 |
| `--apis` | `API` 常量 | ★ 10 个 hook 目标 |

★★★ **⇒ `--delay 0` 是**关键的竞态设定**：**
```
--delay 0 ⇒ nt10.py 装 hook 与 Localnetworking 装 hook 几乎同时
        ↓
★ 谁先谁后不确定 ⇒ 可能是"坏启动率"的一个来源
```

★★ **⇒ 而 `--secs 2400`（40 分钟）意味着 `nt10.py` 会**持续运行 40 分钟**。**

### ★★ `--out` 的路径陷阱

```python
out = os.path.join(BASE, "n10run-%s.txt" % a.tag)          # 完整路径
...
"--out", os.path.basename(out),                            # ★ 只传文件名
```

★★★ **⇒ 传的是 `os.path.basename(out)`（只有文件名），因为 `cwd=BASE`。**
**⇒ 结果文件仍在 `BASE\n10run-<tag>.txt`。**

### ★★ 等待的是 **`BRIDGE_PORT`（28962）**，不是客户端进程

```python
if not wait_port(BRIDGE_PORT, 120.0, "client bridge"):
```

★★★ **⇒ `28962` 是 `OLMOD_CLIENT_BRIDGE_PORT` —— 客户端桥端口。**
**⇒ 它是"客户端起来了"的**可观测代理指标**。**

★ **⇒ 超时 **120 秒**（比 auth/stun/room 的 20 秒长得多）。**

---

## 六、★★★★ 步骤 2b：改名器（第 362–394 行）

### 6.1 ★★★ "为什么必须走内存"（第 363–367 行）

```python
# WHY HERE：客户端界面名是它自己**运行期**用 Windows 账户名拼的（`Administra`+`Client`），
# 服务端三个通道全被忽略（`findings\定因-名字-客户端自己造了AdministraClient-20261005-1745.md`）。
# 已验证的工具是 `force_display_name.py`：扫描可读内存里的 16 字节定长字段就地覆盖，
# `--watch` 覆盖整个启动窗口（客户端启动过程会**多次重建**该结构）。
# 挂进启动链 = 每次重拉都自动生效（固化）。
# 环境变量 `OLMOD_DISPLAY_NAME` 覆盖目标名；置空 = 跳过。
```

★★★★ **⇒ 三条关键信息：**
```
① 名字是客户端**运行期**用 Windows 账户名拼的（`Administra` + `Client`）
② **服务端三个通道全被忽略**
③ 客户端启动过程会**多次重建**该结构 ⇒ 必须 `--watch`
```

★ **⇒ 依据文件：`findings\定因-名字-客户端自己造了AdministraClient-20261005-1745.md`**

### 6.2 ★★★ 名字的**完整演变史**（第 369–376 行）

```python
# ★ 2026-10-07 15:0x -- 默认名曾是 `Lifetime丷`（**已被 2026-10-11 的 `Easily_` 取代**，见下方 :343）。含中文 ⇒ 由改名工具
#   按 **GBK** 写入 16 字节字段（`force_display_name.py` 的实现口径），
#   栈侧 `IdentityConfig.hpp DefaultUsername` 必须保持同一字节序列（connect 名校验）。
# ★ 2026-10-11（V1.101）-- 默认名 = `Easily_`（甲方指定，改自 `Lifetime丷`）。
#   纯 ASCII ⇒ 上面 §GBK/UTF-8 渲染之争本题不存在（两种编码字节序列相同），
#   但**仍必须与 src\backend\Demonware\IdentityConfig.hpp 的 DefaultUsername 同步**
#   —— connect 校验是「客户端上报 16 字节」vs「本常量」逐位相等，只改一侧即进不去服。
#   详见 rope.md §10.4（桌面启动器是唯一拉起入口，改名类需求必须连它一起改）。
```

★★★ **⇒ 完整演变：**
```
2026-10-07 15:0x   Lifetime丷（GBK，含中文）
2026-10-11         Easily_（纯 ASCII，甲方指定）
```

★★★ **⇒ 核心约束（逐字）：**
> **connect 校验是「客户端上报 16 字节」vs「本常量」逐位相等，只改一侧即进不去服。**

★ **⇒ 且注明"详见 `rope.md` §10.4（**桌面启动器是唯一拉起入口**，改名类需求必须连它一起改）"。**

★★ **⇒ `rope.md` 不在交付包里。**

### 6.3 ★★★ 当前默认值 `Easily_`（第 377 行）

```python
display_name = os.environ.get("OLMOD_DISPLAY_NAME", "Easily_")
```

★★★ **⇒ **代码里的默认值是 `Easily_`。**

★★★ **⇒ 但上一轮 PE 实测：`Alwaysoffline.Localnet32` 里的编译期常量是 **`SGamingSH0X`**（`@0x3B2F50`）。**

★★★ **⇒ 两者**不匹配** ⇒ 这是上一轮报告 015 记录的"名字三方失配"的**源头**。**

### 6.4 ★★★ 编码选择 `utf-8`（第 382–389 行）

```python
# ★★ 2026-10-07 16:5x -- 字段编码改为 **utf-8**（v13：全 UTF-8 方案）。
#   实机证据链：同一份名字被多处消费——**只有大厅右上角=GBK 渲染**，
#   房间内角色名/右侧面板/榜单/列表 = **UTF-8 渲染**（GBK 字节在这些地方显示 `▮R`）。
#   字段一份字节不可能两边都对 ⇒ 先保大头（全 UTF-8），右上角的「丷」用
#   **分缓冲定向写入**专项抢回（下一步：给不同内存拷贝写不同标签定位，再按拷贝分编码）。
#   connect 校验 = 客户端把字段原样上报 vs 名册字节（两侧同 UTF-8 即相等，v10 已证路径可通）。
[PY, "-u", RENAMER, "--watch", "150", "--apply", display_name,
 "--encoding", os.environ.get("OLMOD_DISPLAY_NAME_ENC", "utf-8")],
```

★★★ **⇒ 两个渲染管线的**精确定位**：**
```
大厅右上角           = GBK 渲染
房间内角色名         = UTF-8 渲染
右侧面板             = UTF-8 渲染
榜单                 = UTF-8 渲染
列表                 = UTF-8 渲染
```

★★★ **⇒ 取舍（逐字）：**
> **字段一份字节不可能两边都对 ⇒ 先保大头（全 UTF-8）**

★★ **⇒ 这正是 `force_display_name.py --tag` 模式（上一轮报告 014）要解决的问题。**

### 6.5 ★★ 四个参数

```
--watch 150                           ← 监控 150 秒
--apply <display_name>                ← 目标名
--encoding <utf-8 或外部覆盖>          ← 编码
```

★ **⇒ `--watch 150` 秒 —— 覆盖整个启动窗口。**

---

## 七、★★★ 步骤 3：dedicated（第 396–430 行）

### 7.1 ★★★ `--combined` 与 `--no-dedicated` 都是**提前返回**

```python
if a.combined:
    say("--combined: the game server runs INSIDE the client process; no dedicated needed")
    print(); status(); return 0

if a.no_dedicated:
    say("--no-dedicated: skipping step 3 (isolation run)")
    print(); status(); return 0
```

★★★ **⇒ **两者都 `return 0`（成功）** —— 但语义完全不同：**
```
--combined       ⇒ ★ 战斗服在客户端进程内（真的在跑）
--no-dedicated   ⇒ ★ 根本没有战斗服（role=client）
```

★★★ **⇒ 这是**最关键的区别**（报告 018 已详述）。**

### 7.2 ★★★★★ dedicated 启动失败的**完整排查史**（第 408–421 行）

```python
# MEASURED 2026-10-05 20:18-20:22.  Every python-side spawn of
#   Injector32.exe "<client>" -qa
# failed with "Could not create process. Error: 2":
#   * Popen(creationflags=CREATE_NEW_CONSOLE) under the harness background-job
#     runner  -> Error 2
#   * run(creationflags=CREATE_NO_WINDOW, stdout=<file>)  -> Error 2
#   * Popen(creationflags=CREATE_NEW_CONSOLE), no redirect, parent exits early
#     -> injector reaped before it creates the game
# What DID work (20:21:50, dedicated pid 21552, "CODOL Dedicated Server",
# 127.0.0.1:28961 listening at 20:22:04) is a plain `&` from a foreground
# PowerShell call with no creationflags and no stdout redirection.
# That is what start_dedicated.ps1 does.  Do NOT add arguments to the
# injector -- CodolGame.py:291-292 warns ERROR_FILE_NOT_FOUND follows the
# argument COUNT.
```

★★★★ **⇒ 三种失败方式 + 一种成功方式：**

| # | 方式 | 结果 |
|---|---|---|
| 1 | `Popen(creationflags=CREATE_NEW_CONSOLE)` + 后台任务运行器 | **`Could not create process. Error: 2`** |
| 2 | `run(creationflags=CREATE_NO_WINDOW, stdout=<file>)` | **Error 2** |
| 3 | `Popen(creationflags=CREATE_NEW_CONSOLE)`，无重定向，父进程早退 | **注入器被回收**（`injector reaped before it creates the game`） |
| **✓** | ★★★ **前台 PowerShell 的裸 `&`，无 creationflags、无重定向** | **成功** |

★★★ **⇒ 成功实测（20:21:50）：**
```
dedicated pid 21552
标题 "CODOL Dedicated Server"
127.0.0.1:28961 在 20:22:04 监听
```

★★★ **⇒ 关键警告（逐字）：**
> **Do NOT add arguments to the injector** --
> `CodolGame.py:291-292` warns **`ERROR_FILE_NOT_FOUND` follows the argument COUNT.**

★★★ **⇒ 这是**极其具体的坑**：给 `Injector32.exe` 加参数会导致 `ERROR_FILE_NOT_FOUND`。**

★ **⇒ 与上一轮记忆里"我加了 `-qa -q` 导致失败"**完全吻合**（记忆 `codol-frozen-chain-must-not-modify`）。**

### 7.3 ★★★ 委托给 `start_dedicated.ps1`

```python
say("delegating to start_dedicated.ps1 (plain exec, no creationflags) ...")
rc = subprocess.call(
    ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
     "-File", os.path.join(BASE_TOOLS, "start_dedicated.ps1")],
    cwd=GAME)
say("start_dedicated.ps1 exit=%d" % rc)
if not wait_port(DEDICATED_PORT, 120.0, "dedicated control"):
    say("dedicated did not bind its control port")
    return 6
```

★★★ **⇒ `start_dedicated.ps1` **不在交付包里**（上一轮已确认全包无此文件）。**

★★ **⇒ 所以**步骤 3 必然失败**（`subprocess.call` 会抛 `FileNotFoundError`）。**

★ **⇒ 但 `run.cmd` 固定 `--no-dedicated` ⇒ **不会执行到这一步**（报告 014）。**

---

## 八、★★★ 最终日志提示（第 432–440 行）

```python
print(); status(); print()
say("logs:")
say("  backend      %s" % os.path.join(GAME, r"Ayria\Logs\AlwaysofflineRe.Localnet32.log"))
say("  game server  %s" % os.path.join(GAME, r"Ayria\Logs\CodolGameServer.log"))
say("  client run   %s" % os.path.join(BASE, "n10run-%s.txt" % a.tag))
say("next: enter the lobby, open multiplayer, Quick Match")
return 0
```

★★★ **⇒ 三个日志路径，注意第一个：**
```
<GAME>\Ayria\Logs\AlwaysofflineRe.Localnet32.log    ← ★★★ 带 Re！
<GAME>\Ayria\Logs\CodolGameServer.log               ← 不带 Re
<BASE>\n10run-<tag>.txt
```

★★★ **⇒ 日志文件名 `AlwaysofflineRe.Localnet32.log` **带 `Re`** ——**
**与 `xmake.lua` 的 `set_filename` 一致（报告 015），**
**但与 `payload` 里的文件名 `Alwaysoffline.Localnet32` **不一致**。**

★★ **⇒ 说明**日志名由插件内部决定**（用 `set_filename` 的名字），**
**而**文件名可以改**（payload 里改了）。**

★ **⇒ 这是一个**重要区分**：**
```
文件名（可改）      Alwaysoffline.Localnet32
内部模块名（不可改） AlwaysofflineRe.Localnet32  ← 日志名用它
```

---

## 九、★★★★ 七个退出码（完整表）

| 码 | 含义 | 位置 |
|---|---|---|
| **0** | 成功（含 `--combined` / `--no-dedicated` 提前返回） | 多处 |
| **2** | 三个必需文件缺失（`INJ` / `TGT` / `ROOM`） | 第 265 行 |
| **3** | `fake_auth_tls.py` 20 秒内未监听 3074 | 第 292 行 |
| **4** | `ol_room_owner.exe` 20 秒内未监听 28970 | 第 344 行 |
| **5** | 客户端 120 秒内未到 bridge 端口 28962 | 第 360 行 |
| **6** | dedicated 120 秒内未监听 28961 | 第 430 行 |
| **7** | `stun_local.py` 20 秒内未绑 UDP 3074 | 第 331 行 |

★★★ **⇒ 七个退出码，每个对应一个明确的失败点。**

★ **⇒ **注意没有 `1`** —— 可能被 Python 异常占用。**

---

## 十、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `secrets.txt` 不是判据 | 删除它反而 `has no challenge yet` |
| 2 | ★★★ "卡 100" 根因 | **auth 服务没起来**（SYN 无人应答） |
| 3 | `creationflags` | auth/stun = **`0x08000000`（NO_WINDOW）**，room = **`0x10`（NEW_CONSOLE）** |
| 4 | ★★★ STUN 症状签名 | `71/3 Address Fail\|result=-3` + `71/7 @SF_UI_DW_LIVE_DISCONNECTED`，不再问 `8/1` |
| 5 | ★ STUN 幂等 | UDP 3074 在监听就不重启 |
| 6 | ★★★ 28960 **不列** | 归 dedicated（`UDP 0.0.0.0:28960`） |
| 7 | ★★ `OLMOD_SKIP_AUX` 三处 | 跳 auth / STUN / room_owner |
| 8 | ★★★ `--secs 2400` | **40 分钟**观测 |
| 9 | ★★★ `--delay 0` | **立即装 hook**（竞态源） |
| 10 | ★★ 等待 bridge 端口 | **28962**，超时 **120 s** |
| 11 | ★★★ 名字来源 | Windows 账户名 + `Client`（运行期拼） |
| 12 | ★★★ 名字演变 | `Lifetime丷`（GBK）→ **`Easily_`**（ASCII） |
| 13 | ★★★ 当前默认 | **`Easily_`**（但二进制是 `SGamingSH0X`） |
| 14 | ★★ 编码 | **`utf-8`**（`OLMOD_DISPLAY_NAME_ENC` 可覆盖） |
| 15 | ★★★ 渲染管线 | 右上角=GBK，其余=UTF-8 |
| 16 | ★★★ `--combined` vs `--no-dedicated` | 前者真跑战斗服，后者**完全没有** |
| 17 | ★★★ 注入器三种失败 | 全 `Error: 2` 或注入器被回收 |
| 18 | ★★★ 唯一成功方式 | **前台 PS 裸 `&`**（无 creationflags/重定向） |
| 19 | ★★★ 加参数的后果 | **`ERROR_FILE_NOT_FOUND`**（`CodolGame.py:291-292`） |
| 20 | ★★ `start_dedicated.ps1` | **不在交付包** ⇒ 步骤 3 必失败 |
| 21 | ★★ 日志名带 `Re` | `AlwaysofflineRe.Localnet32.log` |
| 22 | 退出码 | **0 / 2 / 3 / 4 / 5 / 6 / 7** |

---

## 十一、结论

### 1. ★★★★★ `--combined` 与 `--no-dedicated` 的**语义天差地别**

```
--combined       →  战斗服在客户端进程内，真的在跑
--no-dedicated   →  role=client，★ 完全没有战斗服
```

★★★ **⇒ 两者都 `return 0`（"成功"），但**只有 `--combined` 能打局**。**

★ **⇒ 而 `run.cmd:106` **固定 `--no-dedicated`** ⇒ 交付包默认配置**打不了局**。**

### 2. ★★★ 注入器**不能加参数**（否则 `ERROR_FILE_NOT_FOUND`）

★★ **这是上一轮我踩过的坑（加了 `-qa -q`），现在有**源码级依据**。**

### 3. ★★★ `--delay 0` 是 hook 竞态的源头

★★ **`nt10.py` 与 `Localnetworking` 几乎同时装 Winsock hook。**

### 4. ★★★ 名字的**三方失配**源头在此（`Easily_` vs `SGamingSH0X`）

### 5. ★★ `OLMOD_SKIP_AUX=1` 一次跳过三样（auth / STUN / room_owner）

### 6. ★★ 七个退出码覆盖全部失败点，**没有 1**

---

## 十二、下一步

- `nt10.py`（146,765 B）—— 全包最大脚本
- `fake_auth_tls.py` / `stun_local.py` / `force_display_name.py`
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
