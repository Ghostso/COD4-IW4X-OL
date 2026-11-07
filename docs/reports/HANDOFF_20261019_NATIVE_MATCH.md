# CODOL 3.19 原生对局链路 — 交接文档

> 交接时间：2026-10-19（Asia/Shanghai）
> 工作根目录：`D:\BaiduNetdiskDownload\使命召唤OL`
> 适用对话：下一轮继续本地大厅 → 原生对局 → 进入 `mp_firingrange` 的闭环
> 纪律依据：`PROJECT_CORE_DOCTRINE.md`。固化链 `REF_LOBBY_KIT\run_all.py` / `nt10.py` **不得修改**。

---

## 0. 一句话现状

**已确证客户端原生引擎可被本进程 `CodolGameServer.Localnet32` 接管并成功开出 UDP 28960 原生专用服**；
但在两种启动方式之间出现了一个**尚未裁决的时序矛盾**：

- 用 `start_native_dedicated_319.py`（`-qa`、`dedicated`、**注入 Bootstrapper32**）启动：
  FrameHook 安装成功，TCP 28961 起来，`ConfigureSession` 被接受，UDP 28960 进入监听（已真实跑通过）。
- 用 `first_complete_attempt.py` 在 `COD OL` 下直接启动（`-q`、`combined`，**脚本自己注入 Bootstrapper32**，不经过 `Injector32.exe`）时：
  大厅 61 条任务全部 `hmac=OK`，客户端能走到“正在设置游戏…”，但 `CodolGameServer.log`
  出现 `[combined/game-server] game server frame hook failed`，原生对局服务未能接管。

**下一轮第一件事不是再“补 SessionStart”，而是先决定/验证：原生 Dedicated 应该用哪条注入路径。**
在没拿到 `CodolGameServer.Localnet32` 成功安装 FrameHook 的情况下，给 28961 发什么包都不会进图。

---

## 1. 已确认事实（带证据）

### 1.1 基线基址（无 ASLR）

| 模块 | 运行时基址 | 证据 |
| --- | --- | --- |
| `codoMP_client_shipRetail.exe` | `0x00400000` | `run_codol_001\runs\LOCAL_MATCH_20261018_193343\local_entry.stdout.txt`；ABoProbe `MODULE ... base=0x400000` |
| `SizeOfImage` | `0x0E659000` | 同上 / PE 头 |
| `kernel32.dll`（SysWOW64） | 动态（实测例 `0x75730000`） | `local_entry.jsonl` |
| `LoadLibraryW` RVA | `+0x21960` | `SysWOW64\kernel32.dll` 导出表 |

> `codoMP_client_shipRetailBase.dll` 是 ASLR 模块（`DllCharacteristics` 含 `DYNAMIC_BASE`），每次启动基址不同；
> 所有依赖它的地址都**不能写死**，必须运行时枚举。

### 1.2 大厅链路（固化链）已完全通关

`REF_LOBBY_KIT\lobby_srv.log`（19:57 那一轮）：

```text
=== 大厅连接建立 ('127.0.0.1', 55148) ===
[keys] ★ 试解命中 ...
★ findSessions 原始 payload(35) ...
★ findSessions 解析值=[1, 0, 10, -695030357] -> 回填 playlist=10
-> Matchmaking 6/14 mmbook -> accepted
★ 解密成功 #61 ... service=71 ... declared=134
<- keepalive
```

- `hmac=BAD` 为 0；
- keepalive 正常；
- 客户端 UI 进入“正在设置游戏…”。

**结论：100 弹窗已被 4 处补丁解除；大厅认证/匹配/预约不是当前瓶颈。**

4 处补丁（固化链已实装，勿再手写一遍）：

```text
0x00B9A78E  74 -> 75   AuthGate
0x00B9A7C5  75 -> EB   ClientTicket
0x00B9A7C7  E8 -> E9   ParseFallback -> 0x00B9A7F1
0x00BA3C1C  85 C0 75 44 -> 85 C0 90 90  LsgNonceCheck
```

### 1.3 第二轮动态转静态（已完成）

产物：

```text
run_codol_001\runs\ROUND2_STATIC_DUMP_20261018_194200\
    CODOL_319_STATIC_DUMP_16MB.bin
    REVERSE_ANALYSIS_REPORT.json
```

- 转存范围：`0x00400000 .. 0x01400000`（16 MB）；
- 磁盘 vs 内存差异：`7,662,265` 字节（磁盘是 `.tp3` 加壳桩，绝大多数逻辑只在运行期出现）；
- **本次转存中 `Com_Frame @ 0x004FEA20` 是有效 x86 序言**：

```text
0x004FEA20 | 55                 | push ebp
0x004FEA21 | 8b ec              | mov ebp, esp
0x004FEA23 | 56                 | push esi
0x004FEA24 | 57                 | push edi
0x004FEA25 | 68 70 d9 db 00     | push 0xdbd970
0x004FEA2A | 6a ff              | push -1
0x004FEA2C | e8 ff ee 16 00     | call 0x0066d930
```

> 注意：`ROUND2_STATIC_DUMP_20261018_220513` 那份里同一地址还是加密字节
> （`03 c1 e0 06 ...`），说明该轮取样时 `.tp3` 代码段尚未完成解密。
> **做静态逆向只认 19:42 那一份（有效），22:05 那一份只能当“未解密对照”。**

### 1.4 原生 Dedicated 已真实跑通一次（唯一一次明确成功）

运行：

```powershell
python run_codol_001\start_native_dedicated_319.py
```

关键输出：

```text
[+] Unpack gate unlocked at t=4.06s!
[+] Bootstrapper32 injected! Thread exit code (HMODULE) = 0x67350000
[+] Verified in log: frame hook installed at t=0.00s!
[+] CodolGameServer.Localnet32 already present in module table: 0x51600000
[+] Connected to DedicatedControl port 28961 (attempt 11)!
[+] ConfigureSession response: status=0 (0=Accepted), payload_len=8
[UDP] 0.0.0.0:28960  PID 23220
[SUCCESS] Native Dedicated Server (PID 23220) IS LISTENING ON UDP 28960!
```

`COD OL\Ayria\Logs\CodolGameServer.log` 同时记录：

```text
[dedicated/game-server] game server frame hook installed
[dedicated/game-server] dedicated control listening port=28961
[dedicated/game-server] ConfigureSession keyFingerprint=1:1:1:1 updated=1 changed=1
[dedicated/game-server] server enabled false -> true; RESETTING every connected client, connectedClients was 0
[dedicated/game-server] native entity mirror failed stage=binding_or_thread
[dedicated/game-server] ConfigureSession accepted bytes=22 endpoint=28960
```

**这是目前唯一被日志 + netstat 双证据证实的“原生对局服务起来了”的状态。**

### 1.5 失败状态（`combined` 注入路径）

`first_complete_attempt.py` 那一轮（19:53）：

```text
[+] 4处大厅认证放行补丁已全部装实
发现窗口: ... '使命召唤online'
[!] 进程在 t=28.66s 终止，ExitCode = 0x00000000
```

`CodolGameServer.log`：

```text
[combined/game-server] game server frame hook failed
```

`AlwaysofflineRe.Localnet32.log`：

```text
[combined/backend] Refused to apply CODOL startup patches to an unknown executable image.
[combined/backend] Applied the three Auth3 client patches ... at +0x6E2961, +0x6E3D91, +0x6E3C58.
[combined/backend] Claimed lsg.qq.com as LSG/lobby.
```

**判定：`combined` 路径能过大厅，但内置 GameServer 的 FrameHook 没装上。**

### 1.6 另一条失败路径（普通外部注入）

`run_codol_001\runs\LOCAL_MATCH_20261018_193343\local_entry.stdout.txt`：

```text
Bootstrapper 注入结果: 0xFFFFFFFF
CodolGameServer 注入结果: 0xC0000005
CreateRemoteThread set_enabled 失败: err=5
```

`IFS1_ELEVATED_20261018_193344\aboprobe.stdout`：

```text
3.284,MODULE,name=CodolGameServer.Localnet32,base=0x63210000,...
4.598,PROCESS_END,exited=True,exitcode=0xC0000005,lifetime=4.6
```

**判定：`CodolGameServer.Localnet32` 被加载进模块表，随后进程在 ~1.3s 后 `0xC0000005`；
它不能证明 DLL 初始化成功，只证明映射发生过。之后 `HMODULE` 读到垃圾值（0xC01F57F5）也是进程已死后的误读。**

### 1.7 `Injector32.exe` 路径也没起来

`run_codol_001\runs\LOCAL_OBSERVER_RUN\local_observer.jsonl`：

```text
{"stage": "room_owner", "ok": true}
{"stage": "injector", "ok": true, "return_code": 0}
{"stage": "client_process", "ok": false, "pid": null}
```

`Injector32.exe` 自己返回 0，但没有留下 `codoMP_client_shipRetail.exe`。
说明它不是“稳定拉起器”，不能直接作为下一轮基线。

---

## 2. 当前阻塞点（只写已确证的部分）

### 2.1 真正的阻塞：FrameHook 是否装上

`CodolGameServer::installFrameHook()` 的源码逻辑
（`_e1_regression\ol-mod-olfinal\src\game_server\FrameHook.cpp`）：

1. `bindings.valid()`：要求主模块时间戳、`SizeOfImage`、若干函数前缀全部匹配；
2. `bindings.module() + EngineBindings::ComFrameRva`（`0xFEA20`）作为 hook 目标；
3. 目标必须可写（`VirtualProtect` 成功）；
4. 安装后 `Com_Frame` 前 5 字节变成 `E9`。

失败只可能是其中一步失败。当前日志只给 `frame hook failed`，**没有给出是哪一步**。

**下一轮不要先猜；先拿 `frame hook failed` 的具象原因。**

### 2.2 为什么不能直接发 `SessionStart`

`start_native_dedicated_319.py` 已实装：

```python
SessionStart = 3
ConfigureSession = 4
```

并发包顺序：

```text
ConfigureSession(type=4) -> SessionStart(type=3)
```

但该脚本的 `SessionStart` payload **有明确的结构错误，需要先修**。

`OlMod::DedicatedSession::valid(LoadoutRequest)` 的真实约束
（`_e1_regression\ol-mod-olfinal\src\shared\DedicatedSession.cpp:293-335`）：

```text
classMask 的每一位 == 该类是否存在；
present 类必须 weapon[0].itemId != 0 且 weapon[1].itemId != 0；
非 present 类的 weapon/item/perk/equipment 必须全 0。
```

当前 `make_session_start_payload()` 的写法：

```python
classMask = 0x03                 # 只有 class 0/1 present
for c_idx in range(5):
    ...
    b.extend(struct.pack('<6I', 1,1,1,1,1,1))   # 给 5 个类都写了 perks=1
    b.extend(struct.pack('<2IBBH', 0,0,1,0,0))  # 给 5 个类都写了 doubleAmmoMask=1
```

→ 对 class 2/3/4（`present == false`）写入了非 0 perks / equipment，
`valid()` **必然返回 false**，`SessionStart` 会被 `InvalidMessage` 拒掉。

此外还有一处不确定但**必须核实**：

```python
b.extend(struct.pack('<IIIIII', 796, 75, 10, 0, 1, 1))
```

`valid(MatchRules, "dm")` 对 `dm` 没有专门分支（`"ffa"` 才检查），
所以数值上大概率能过；但 `scoreLimit=75, timeLimitMinutes=10` 是否与
靶场 booking 一致，需要从 `lobby_server.py` 实际发给客户端的
`mmstart` / playlist 规则核对后再定。

**不要用一个必然 invalid 的 SessionStart 去判断“发 SessionStart 没用”。**

### 2.3 `ConfigureSession` payload 的来源

当前：

```python
marker = bytes([0x13, 0x08, 0x10, 0, 0, 0])
payload = marker + sec_key
```

`battle_security_key.txt` 当前为：

```text
01010101010101010101010101010101
```

`ConfigureSession` 曾返回 `status=0`，说明这个 22B 结构能过
`configureSessionDescriptor()` + `Network.start()`。
**但 `keyFingerprint=1:1:1:1` 说明服务端看到的是全 `01` 的占位 key，
不是大厅真实下发的会话 key。**

如果下一轮要真正“像客户端一样”进对局，需要回答：

- 这个 16B key 是否必须等于大厅 `battle_security_key.txt`？
- 还是必须来自客户端 KDF / `secrets_kdf.txt`？

当前没有证据证明“全 01 能进图”，只证明“全 01 能让 UDP 28960 起来”。

### 2.4 大厅已起来，但战斗服仍是另一套

`REF_LOBBY_KIT` 默认会拉起
`CODOL-Combat-Server-v0.1\build\bin\CODOLCombatServer.exe --config ...\firingrange_live.cfg --run`
（`lobby_server.py:1204-1233`），它自己绑 UDP 28960。

因此：

- 若同一时刻再跑原生 `CodolGameServer`，两者会抢 `28960`；
- 固化链的 C# 战斗服与本项目的 native `CodolGameServer` **不是同一个实现**，
  不能拿来互相验证。

**下一轮做原生对局时，必须只保留一个 28960 owner。**

---

## 3. 下一轮要做什么（按顺序，不要跳）

### 步骤 0：环境复位（5 分钟）

1. 杀掉残留：

```powershell
Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process CODOLCombatServer -ErrorAction SilentlyContinue | Stop-Process -Force
```

2. 确认大厅服务在：

```powershell
netstat -ano | findstr ":3074"
```

期望：

```text
127.0.0.1:3074 LISTENING   (fake_auth_tls)
127.0.0.2:3074 LISTENING   (lobby_server)
```

3. **确认 28960 当前没有被 C# 战斗服占住**：

```powershell
netstat -ano -p UDP | findstr ":28960"
```

做原生对局前，这条应当为空。

### 步骤 1：先解决 FrameHook 为什么 failed（P0）

> 路径歧义先澄清：`first_complete_attempt.py` 本身**不调用 `Injector32.exe`**，
> 它自己 `CreateProcessW` 后在解密门之后注入 `Bootstrapper32.dll`。
> `Injector32.exe` 只出现在 `local_observer.py`，且本轮实测未留下客户端进程（见 §1.7）。
> 下一轮以 `first_complete_attempt.py` 的 combined 路径为观察对象即可。

**目标：拿到 `bindings.valid()` 失败的具体原因，而不是只看 `frame hook failed`。**

推荐做法（只读，不改客户端）：

1. 用 `first_complete_attempt.py` 同样的启动参数（`-q`、`combined`，脚本直接创建进程并注入 Bootstrapper32），
   在客户端起来后**尽早**拿到模块基址；
2. 读 `CodolGameServer.Localnet32` 的日志/导出状态，确认：
   - `onStartup` / `onInitialized` 是否被调用；
   - `EngineBindings::bind()` 是否通过时间戳 / `SizeOfImage` / 前缀校验；
3. 若没有更细日志，用 `EngineBindings.cpp` 的校验项逐条回读：
   - `GetModuleHandleW(nullptr)` 是否等于 `0x00400000`；
   - PE `TimeDateStamp`、`OptionalHeader.SizeOfImage` 是否匹配；
   - `SV_LinkEntityPrefix` / `SV_UnlinkEntityPrefix` / `SVTracePrefix` 的前若干字节是否匹配；
   - `Com_Frame` 处 5 字节是否为可 patch 的指令边界（不是被别的 hook 改过）。

**Falsifiable criterion：**

- 如果 `bindings.valid()` 失败 → 修 binding，不要碰 SessionStart；
- 如果 binding 通过但 `VirtualProtect`/写入失败 → 这是权限/保护问题；
- 如果 hook 已写入但 `Com_Frame` 没被调用 → 再查引擎启动路径。

### 步骤 2：在原生 `dedicated` 路径下修正 `SessionStart` payload（P0）

使用唯一有效基线：`start_native_dedicated_319.py`（它能装 FrameHook、能开 28961/28960）。

修正 `make_session_start_payload()`：

1. `classMask = 0x03` 时，**只有 class 0/1 写非 0**；
2. class 2/3/4 的：
   - weapons itemId / attachments
   - perks
   - equipment
   **全部写 0**；
3. 保证每个 present 类的两把武器 itemId 都非 0；
4. `MatchRules` 与大厅实际 `mmstart` 对齐（从 `lobby_srv.log` 的 6/14 payload 或
   `lobby_server.py` 的 playlist 规则取，不要猜）。

**验证方式（不靠 UI）：**

发 `SessionStart` 后立刻读：

```text
COD OL\Ayria\Logs\CodolGameServer.log
```

期望按顺序出现：

```text
SessionStart queued request=... map=mp_firingrange gametype=dm members=1
map asset load requested map=mp_firingrange gametype=dm
world initialized map=mp_firingrange
CCS generation reset complete
```

如果只看到 `SessionStart rejected: invalid payload`，说明 payload 仍不合 schema；
如果看到 `map asset load rejected`，说明 schema 过了，卡在引擎资源加载。

### 步骤 3：等客户端进入后，再确认 gamestate

只有当步骤 2 的日志走到 `world initialized` / `configureGameState entry`，
才去看客户端 UI 是否越过“正在设置游戏…”。

期望新增证据：

- `CodolGameServer.log` 出现 `GAMESTATE` 或 `configureGameState entry ... checksum=...`；
- 客户端画面进入地图（靶场）；
- 若仍卡住，抓 `cls.state`（历史地址 `0x76446B0`，VA 口径，不加 `0x400000`）。

### 步骤 4：如果原生路径仍不可用，再考虑 C# 战斗服

不要在本轮一开始就切 C# 战斗服。C# 战斗服是另一套已验证能“进图”的实现，
但它不是 `CodolGameServer.Localnet32`，会掩盖 native 的问题。

只有步骤 1-3 都证明 native 路径结构性不可行时，才回到：

```text
REF_LOBBY_KIT + CODOLCombatServer.exe
```

并注意：这条链的 `28960` 必须由 C# 战斗服独占。

---

## 4. 不要做的事

1. **不要修改固化链**：
   - `REF_LOBBY_KIT\run_all.py`
   - `REF_LOBBY_KIT\nt10.py`
   - `REF_LOBBY_KIT\write_dwauth.py`
   - `CODOLServer\_mainline\elevated_agent.py`
2. **不要再手写 4 处大厅补丁**：
   `nt10.py` 已经做了；重复写会把已经正确的字节再次改坏。
3. **不要在 `combined` 路径没有 FrameHook 的情况下发 `SessionStart`**：
   那只会在 UDP 28960 未绑定时失败或误报。
4. **不要把 `hmac=BAD` 当成当前问题**：
   19:57 那一轮是 0 BAD；后续 reconnect 轮出现 BAD，是 KDF 候选未写回，
   不是协议本身。
5. **不要把 `0xC0000005` 当成“DLL 注入成功”**：
   模块表出现名字 ≠ 初始化成功；以 `CodolGameServer.log` 的
   `game server frame hook installed` 为唯一成功判据。
6. **不要再用 `222`/`218`/`100` 弹窗当第一指标**：
   当前第一指标是 `frame hook installed`，第二指标是 `SessionStart queued/accepted`，
   第三才是 UI 是否进图。

---

## 5. 关键文件与产物

### 5.1 启动/诊断脚本（本地链，可改）

| 文件 | 用途 | 当前状态 |
| --- | --- | --- |
| `run_codol_001\start_native_dedicated_319.py` | **原生 dedicated 唯一成功基线** | `-q -qa`、`dedicated`、注入 Bootstrapper32；已能开 28961/28960 |
| `run_codol_001\first_complete_attempt.py` | 大厅 + `combined` 注入 + 4 补丁 | 大厅通，FrameHook failed |
| `run_codol_001\launch_game_keep_alive.py` | 只拉起客户端并打 4 补丁 | 可用于观察 UI，不负责对局 |
| `run_codol_001\round2_dynamic_dump_and_reverse.py` | 动态转静态 + 反汇编报告 | 已产出 19:42 有效镜像 |
| `run_codol_001\local_observer.py` | 直接用 `Injector32.exe` 拉起链 | 本轮实测不可靠（client_process=false）；**已不用**，改用 `start_native_dedicated_319.py` 的 Bootstrapper32 early-inject 路径 |
| `run_codol_001\local_match_entry.py` | 外部 `LoadLibraryW` 注入 | 会 `0xC0000005`，**不要再当主路径** |

### 5.2 逆向证据

| 文件 | 说明 |
| --- | --- |
| `run_codol_001\runs\ROUND2_STATIC_DUMP_20261018_194200\CODOL_319_STATIC_DUMP_16MB.bin` | **唯一有效解密镜像** |
| 同目录 `REVERSE_ANALYSIS_REPORT.json` | `Com_Frame` 反汇编、模块基址、diff 计数 |
| `run_codol_001\runs\IFS1_ELEVATED_20261018_193344\aboprobe.stdout` | 实际加载顺序 + `0xC0000005` 时间点 |
| `REF_LOBBY_KIT\lobby_srv.log` | 大厅 61 条 `hmac=OK` / `mmbook` / `keepalive` |

### 5.3 关键源码（只读参考）

| 文件 | 用途 |
| --- | --- |
| `_e1_regression\ol-mod-olfinal\src\game_server\FrameHook.cpp` | FrameHook 5 字节 patch 实现 |
| `_e1_regression\ol-mod-olfinal\src\game_server\EngineBindings.cpp` | `bindings.valid()` 的全部门槛 |
| `_e1_regression\ol-mod-olfinal\src\game_server\Appmain.cpp` | `SessionStart` 队列、`configureGameState`、`map asset load` 链 |
| `_e1_regression\ol-mod-olfinal\src\shared\DedicatedControl.hpp` | `MessageType`：`SessionStart=3` / `ConfigureSession=4` |
| `_e1_regression\ol-mod-olfinal\src\shared\DedicatedSession.cpp` | `SessionStart` 负载 schema + `valid()` |

---

## 6. 当前结论摘要（可直接贴给下一轮）

1. **大厅已通**：4 补丁 + `fake_auth_tls` + `lobby_server` 能让客户端走到“正在设置游戏…”。
2. **原生对局服能起**：`dedicated` + Bootstrapper32 路径实测开出 TCP 28961 + UDP 28960。
3. **但 `combined` 路径 FrameHook 失败**：日志 `[combined/game-server] game server frame hook failed`，
   所以 `first_complete_attempt.py` 那条链不能直接进图。
4. **下一轮先修 FrameHook/绑定，不要先发 SessionStart**。
5. **SessionStart payload 当前必然 invalid**：classMask=0x03 却给 class 2/3/4 写了非 0 perks/equipment。
6. **原生路径和 C# 战斗服不要同时占 28960**。

---

## 7. 最小成功判据（下一轮验收）

顺序必须全部满足：

```text
[1] CodolGameServer.log: game server frame hook installed
[2] netstat: TCP 28961 LISTENING，且 PID == 客户端 PID
[3] ConfigureSession response status == 0
[4] CodolGameServer.log: SessionStart queued ... members=1
[5] CodolGameServer.log: world initialized map=mp_firingrange
[6] 客户端 UI 越过“正在设置游戏…”并进入地图
```

任何一步没满足，都不要把“UDP 28960 LISTENING”当作进图成功。

---

## 8. 可直接粘贴给下一对话的开场指令

```text
请先完整阅读 D:\BaiduNetdiskDownload\使命召唤OL\HANDOFF_20261019_NATIVE_MATCH.md，
再按其中“步骤 0 → 步骤 1 → 步骤 2 → 步骤 3”执行，不要跳步。

本轮目标：继续 CODOL 3.19 本地大厅 → 原生对局闭环。
硬约束：
1. 不得修改 REF_LOBBY_KIT 固化链（run_all.py / nt10.py / write_dwauth.py）。
2. 必须先取得 CodolGameServer.Localnet32 的 “game server frame hook installed”；
   仅看到 DLL 模块名、0xC0000005、或 UDP 28960 LISTENING 都不算成功。
3. 当前 start_native_dedicated_319.py 的 SessionStart payload 已知 classMask 与
   perks/equipment 不一致，必须先按 DedicatedSession.cpp::valid() 修正。
4. 同一时刻只允许一个进程占用 UDP 28960；做 native 对局前确认 C# 战斗服未占端口。
5. 每一步只允许单次受控启动，并报告准确日志行、PID、端口、地址与退出码。

第一轮请先回答：为什么 combined 路径出现
“[combined/game-server] game server frame hook failed”？
给出 bindings.valid() 具体失败项（时间戳 / SizeOfImage / 前缀 / Com_Frame 可写性），
不要先发 SessionStart。拿到结论后再进入下一步。
```


---

## 9. 本轮已发现但尚未处理的脚本级问题（供下一轮直接修）

这一节只列**已经看出来、但本轮没有改**的代码缺陷，避免下一轮重新踩：

### 9.1 `first_complete_attempt.py` 的 SessionStart 未发送
- 第 385-400 行只发 `ConfigureSession(type=4)`；
- 没有任何 `MessageType::SessionStart(type=3)` 构造。
- 即使 FrameHook 修好，这条脚本也不会触发建图。

### 9.2 `first_complete_attempt.py` 的 payload/常量未复用
- 没有 `make_session_start_payload()`；
- 因此不能指望它验证 schema。

### 9.3 `start_native_dedicated_319.py` 的启动参数
- 当前 `cmdline = f'"{exe_path}" -q -qa'`；
- `-qa` 是历史 dedicated 参数，本轮已证可起原生服；
- 若下一轮要用 `combined`（大厅+对局同进程），必须改回 `-q` 并重测，
  不要只改环境变量 `OLMOD_PROCESS_ROLE`。

### 9.4 `start_native_dedicated_319.py` 的 SessionStart payload
- 第 150-158 行：`classMask=0x03`，但 `range(5)` 给全部 5 个
  class 都写了非 0 perks 与 `doubleAmmoMask=1`；
- 这与 `DedicatedSession.cpp::valid()` 冲突；
- 先修这里，再发 `type=3`。

### 9.5 `start_native_dedicated_319.py` 的 ConfigureSession key
- 当前读 `REF_LOBBY_KIT\battle_security_key.txt`，内容为全 `01`；
- `keyFingerprint=1:1:1:1` 只是“配置成功”的指纹，不是“和大厅会话一致”；
- 下一轮若要客户端真正入场，需要核对 key 来源，不要默认全 `01` 正确。

### 9.6 端口占用
- `REF_LOBBY_KIT\lobby_server.py` 在 `firingrange-battle.enabled` 存在时
  会优先拉起 `CODOLCombatServer.exe` 并占 `UDP 28960`；
- 再做 native `CodolGameServer` 前，必须关掉 C# 战斗服或移除该开关，
  否则 native 侧 `Network.start()` 会因端口占用失败。



