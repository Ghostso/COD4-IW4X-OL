# COMBAT_P0_VALIDATION_PLAN — 引擎绑定首个真实失败条件的最小验证方案

**性质**：**方案，不执行。** 本阶段（COMBAT-P0 只读调查）**未启动任何进程、未做任何运行时实验**。
**目标**：在不改动 `GOLDEN-LOBBY-001` 大厅基线的前提下，用**插件自身的只读日志**逐步判定：宿主映像身份 → 关键 RVA 运行时字节 → 引擎绑定是否通过 → 首个失败守卫 → 帧钩子 → 网络初始化 → 实际监听 → 客户端是否进入战斗。
**配套**：`COMBAT_P0_ENGINE_BINDING_ANALYSIS.md`、`COMBAT_P0_FAILURE_PATHS.json`、`COMBAT_P0_SHA256_MANIFEST.txt`。

---

## 0. 方案原则与保护边界

| # | 原则 |
|---|---|
| P-1 | **不用 Frida**、**不从外部读进程内存**、**不修改运行映像**。一切观测来自插件自身的只读自省 + 插件自己写的 `CodolGameServer.log`。 |
| P-2 | **不放宽 `SizeOfImage`**、**不删除/绕过任何门禁**。所有诊断改动必须是**纯日志**或**默认关闭**且逐位等价。 |
| P-3 | **每次运行只回答一个问题**。一次运行里的多个结论会互相耦合。 |
| P-4 | **一次只改一项**，每项改动可单独回滚；改动前记录哈希。 |
| P-5 | **不动 `GOLDEN-LOBBY-001`**：不写入 `GOLDEN-LOBBY-001/REF_LOBBY_KIT/`，不改 `_golden_hashes.json`，不在冻结目录内运行。验证只在沙箱 `E:\CODOL_SANDBOX\RUN001` 或活动开发副本中进行。 |
| P-6 | **不动启动器 / TCLS / Ayria / 大厅链**：不修改 `Launch_OLMod.bat`、`Injector32.exe`、`Bootstrapper32.dll`、`Localnetworking.Ayria32`、`Platformwrapper.Ayria32`、`nt10.py`、`lobby_server.py`、`fake_auth_tls.py`、hosts、`dwauth.ini`、`iips.ini`。 |
| P-7 | **每一步都必须可停**：任何一步失败立即停止，不进入下一阶段，**不得**以"先把门禁弄绿"作为继续条件。 |
| P-8 | **判据是日志中的具体串**，不是"进程没崩"或"端口开了"。 |

**关键前提（必须先解决，否则后续一切日志都可能被误读）**：历史实机运行使用的是**部署件** `6D493B82…`（2026-10-09 13:49），而当前源码树构建产物是 `DBA7273A…`（2026-10-10 12:52）。两者**不是同一产物**。在源级比对（或重新部署一份与源码一致的插件）之前，任何"日志里没有 stage 行"的推断都可能是**旧插件的日志行为**造成的。

---

## 1. 前置条件（不属于 8 步，但不满足则 8 步无意义）

| 前置 | 内容 | 需要的证据 | 是否需单独授权 |
|---|---|---|---|
| **PRE-1** | 确认部署件与源码的一致性 | 对 `src/game_server/EngineBindings.cpp`、`EngineBindings.hpp`、`Appmain.cpp`、`FrameHook.cpp` 的**构建时哈希**与当前源码哈希的比对记录；或直接给出部署件的构建日志/来源 | **是**（涉及构建/部署） |
| **PRE-2** | 确定要观测的是 `combined` 还是 `dedicated` | 明确 `OLMOD_PROCESS_ROLE` 取值；历史三次为 `combined` | **是**（启动参数） |
| **PRE-3** | 备份并冻结沙箱现场 | `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\` 现有 6 个日志的 SHA-256（见 `COMBAT_P0_FAILURE_PATHS.json` 与 `COMBAT_P0_SHA256_MANIFEST.txt`）；运行前清空或改名，保证**逐次运行可隔离**（历史三次共用同一组日志，靠时间戳区分，隔离性不足） | 否（只读+改名） |

> **PRE-3 的重要性**：历史三次运行共用同一组日志文件，是"逐次运行证据不足"的直接原因（见 `COMBAT_SERVER_BLOCKERS.md` §8 G-5）。

---

## 2. 八步验证方案

### S1 — 宿主映像身份（运行时 PE 头）

| 项 | 内容 |
|---|---|
| **目的** | 取得**运行时映像**（O-4）的 `TimeDateStamp` / `SizeOfImage` / `Machine` / 段数，判定历史磁盘测量（`0x0E659000`）是否等于运行时值 |
| **需要的证据** | `CodolGameServer.log` 中出现形如 `engine binding failed stage=host_image_size effective=0x…… expected=0x0E5D6000` 或 `stage=host_image_timestamp …`（依赖 §3.1 的纯日志改动） |
| **实现前提** | 落地诊断层第 1 层（`COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §3.1）；**纯日志，判定语义逐位不变** |
| **可能副作用** | **无行为副作用**（只多写几行日志）。唯一影响是启动期多写一次文件（历史 `LOGSTALL consoleDebugUs≈140 ms` 已存在） |
| **失败时如何停止** | 若日志仍只有 `engine binding failed` 而无 `stage=host_image_*` ⇒ 部署的不是新插件（回到 PRE-1），**立即停止** |
| **是否需单独授权** | **是**：① 修改 `src/game_server/EngineBindings.cpp`；② 构建；③ 部署到沙箱；④ 启动 1 个客户端并只读日志 |
| **成功后进入** | 若为 `stage=host_image_size`（尺寸不符）⇒ **S2**；若为 `stage=host_image_timestamp` ⇒ 说明时间戳不符，**结论改变**（宿主根本不是 1649370 族），停止并回报；若三项均通过而仍失败 ⇒ 直接跳到 **S4**（首个失败守卫） |

### S2 — 关键 RVA 的运行时字节（只读采样，**不经过门禁**）

| 项 | 内容 |
|---|---|
| **目的** | 回答 P0 的核心未知：运行时代码字节是否等于 `out.exe` 的期望值。取 `module_+0x0FEA20`（期望 `55 8B EC 56 57`）与 `module_+0x8371A`（期望 `83 7C 24 08 01 0F 94 C0`） |
| **需要的证据** | 日志中出现例如 `host_image_rva rva=0x0FEA20 expected=55 8B EC 56 57 effective=55 8B EC 56 57 match=1` 与 `rva=0x8371A … match=0/1` |
| **实现前提** | 在 `bind()` **门禁之前**加一段**只读**采样 + 日志（不比较、不改变流程、不发布指针）。**不启用任何容差** |
| **可能副作用** | **无**（纯读内存映射，与门禁同一模块） |
| **失败时如何停止** | 若采样本身触发异常 ⇒ 立即停止并回报（说明读该 RVA 不可行），**不得**改为外部读内存或 Frida |
| **是否需单独授权** | **是**（同 S1：改码/构建/部署/启动） |
| **成功后进入** | 与 S1 联合判定：**α 情形**（运行时尺寸=0x0E5D6000 且 RVA 字节匹配）⇒ 门禁本应通过，回到 S4 查守卫；**β 情形**（运行时尺寸=0x0E659000 且 RVA 字节匹配）⇒ 证明"代码正确、常量描述的是去壳布局"，此时才允许**提出**常量修订方案（**仍需单独授权**，且必须附 S2 证据）；**γ 情形**（RVA 字节不匹配）⇒ 该客户端运行时代码与目录不符，**不得**改常量，停止并回报 |

> **这是本方案中信息量最大的一步**：它在**完全不触碰门禁语义**的前提下，把"门禁要不要放宽"这个二选一变成可判定事实。

### S3 — 引擎绑定是否通过

| 项 | 内容 |
|---|---|
| **目的** | 确认 `bind()` 是否整体成功 |
| **需要的证据** | `CodolGameServer.log` **不出现**任何 `engine binding failed` / `engine binding validation failed stage=*`；且出现 `game server frame hook installed` |
| **可能副作用** | **若绑定通过，`bind()` 会发布函数指针并安装帧钩子** —— 这是**功能性副作用**（写 `0xE9` 跳转、改页保护），非只读 |
| **失败时如何停止** | 出现任何 `engine binding failed` ⇒ 停止，进入 **S4** |
| **是否需单独授权** | **是**（运行阶段；且此步已具备"改变进程行为"的性质） |
| **成功后进入** | S5 |

### S4 — 首个失败守卫

| 项 | 内容 |
|---|---|
| **目的** | 若门禁通过而后续失败，定位**第一个**失败的守卫/阶段 |
| **需要的证据** | `engine binding validation failed stage=function_prefixes guard=<id> index=<n> rva=0x…… expected=<bytes> effective=<bytes>`，或 `stage=runtime_slots|message_bindings|glass_bridge`，或具名的 `… prefix mismatch function=<name>` |
| **实现前提** | 诊断层第 2 层（`COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §3.2）；顺序与短路语义与现状**逐位等价** |
| **可能副作用** | **无**（只读比较 + 日志） |
| **失败时如何停止** | 若日志仍只有 `stage=function_prefixes` 而无 `guard=` ⇒ 部署件不是新插件，停止 |
| **是否需单独授权** | **是**（同 S1） |
| **成功后进入** | 按首个失败守卫逐条评估：代码前缀不匹配 ⇒ 该 RVA 在本映像上不成立（**不得**改 RVA，先回报）；数据守卫（`ByteDirections`）不匹配 ⇒ 说明是数据布局差异，单独评估 |

### S5 — 帧钩子是否安装

| 项 | 内容 |
|---|---|
| **目的** | 确认 `installFrameHook` 的四个前置条件全部满足并成功写入跳转 |
| **需要的证据** | `game server frame hook installed`（`Appmain.cpp:8131` 文案）；**不得**出现 `frame hook install rejected op=installFrameHook reason=…` |
| **可能副作用** | **功能性**：每帧执行 `onServerFrame`（含 `NET_Frame`、控制面轮询） |
| **失败时如何停止** | 出现 `reason=invalid-bindings|null-callback|already-installed|trampoline-allocation-failed|protect-failed` ⇒ 按 reason 分类停止（`already-installed` 为良性） |
| **是否需单独授权** | **是**（运行） |
| **成功后进入** | S6 |

### S6 — 服务器网络初始化是否继续

| 项 | 内容 |
|---|---|
| **目的** | 确认控制面起来、且后端（或显式 API）下发了会话配置 |
| **需要的证据** | `client session bridge listening port=…` / DedicatedControl 监听；`ConfigureSession accepted bytes=<n> endpoint=<port>`；以及后续 `game server frame hook installed` **之后**的每帧活动 |
| **可能副作用** | 打开 28961/28962 监听；接受后端连接 |
| **失败时如何停止** | 只出现 `ConfigureSession rejected` 或完全无该行 ⇒ 停止（说明后端未接通，属 P2，不是门禁问题） |
| **是否需单独授权** | **是**（运行 + 需要后端/booking 侧配套；后端在 `combined` 下与插件同进程） |
| **成功后进入** | S7 |

### S7 — 是否产生实际监听

| 项 | 内容 |
|---|---|
| **目的** | 确认 UDP 28960 真的绑定 |
| **需要的证据** | 优先**插件自身状态**：`CODOL_GameServerGetTransportStatus` 报 `bound=1` 且 `port≠0`（需一个读取该导出的手段）；辅以 OS 层 `netstat` 只读快照 |
| **可能副作用** | 绑定 UDP 端口 |
| **失败时如何停止** | `bound=0` 或 `port=0` ⇒ 停止；**不得**把"端口开了"当作战斗创建成功 |
| **是否需单独授权** | **是**（运行 + 读取端口的只读命令） |
| **成功后进入** | S8 |

### S8 — 客户端是否进入真实战斗

| 项 | 内容 |
|---|---|
| **目的** | 判定是否真的进图并对局（**唯一有意义的成功判据**） |
| **需要的证据** | 按顺序（全部为日志/客户端侧可观测）：`SessionStart accepted request=…`；`world initialized map=<map>`；gamestate 被客户端接受；`snapshot …` 持续推进；`client timeout` 未出现；客户端侧进入地图（**需要客户端证据**，不是服务器自述） |
| **可能副作用** | 完整对局负载；地图加载；可能触发客户端崩溃（历史上有过） |
| **失败时如何停止** | 任一环节的 `failSession(…)` / `world initialization failed` / 客户端异常退出 ⇒ 停止；保留日志与崩溃现场，不重试超过 1 次 |
| **是否需单独授权** | **是**（多进程运行 + 客户端交互；**用户拥有 UI**，本轮不代点） |
| **成功后进入** | 可冻结 `GOLDEN-BATTLE-001`（另立任务） |

---

## 3. 统一停止条件与回滚

| 场景 | 动作 |
|---|---|
| 任一步未出现**预期日志串** | 立即停止，回报"预期串未出现"，**不得**进入下一步 |
| 出现**非预期**的守卫/阶段失败 | 停止；保留日志；把该守卫 ID 与 RVA 登记为新的 UNKNOWN |
| 客户端崩溃 / 异常退出 | 停止；保留 `Ayria\Logs\*` 与客户端崩溃现场；**不重试**超过 1 次 |
| 需要"放宽门禁才能继续" | **停止。** 这是本方案的明确禁止项 |
| 回滚 | ① 停止客户端与 all mod 进程；② 用 PRE-3 备份恢复/移除沙箱 `Ayria`；③ 源码改动 `git checkout --` 对应文件（由获授权者执行）；④ 重新部署旧插件哈希（若有备份） |

---

## 4. 授权分级

| 级别 | 包含 | 说明 |
|---|---|---|
| **A. 只读（无需新授权）** | 读源码、hash、日志、`netstat` 快照、备份/改名沙箱日志 | 本方案阶段已用 |
| **B. 需授权（改码）** | 诊断层第 1 层（门禁具名化，纯日志）；诊断层第 2 层（守卫 ID，纯日志/等价改写）；诊断层第 3 层（纯数据判定层 + 测试目标） | 每项单独授权；每项都要附**语义等价性证明** |
| **C. 需授权（构建/部署）** | 构建 `ol_game_server`；把新插件落到沙箱 | `ol_deploy` 禁用；需替代落盘流程 + PRE-1 |
| **D. 需授权（运行）** | 启动 1 个沙箱客户端（`combined` 或 `dedicated`）；注入（`Injector32.exe`） | 一次一个目标，一次一个问题 |
| **E. 明确禁止（本方案不申请）** | 放宽/删除 `SizeOfImage`；改 RVA/前缀/ABI/协议常量；Frida 附加；外部读进程内存；改启动器/TCLS/Ayria/大厅链；在 `GOLDEN-LOBBY-001` 内运行 | — |

---

## 5. 判定矩阵（S1+S2 联合）

| S1 运行时 `SizeOfImage` | S2 `0x0FEA20`/`0x8371A` 运行时字节 | 判定 | 允许的下一步 |
|---|---|---|---|
| `0x0E5D6000` | 匹配 | **α**：门禁本应通过 ⇒ 失败另有原因 | 直接 S4（查守卫） |
| `0x0E659000` | 匹配 | **β**：代码正确，常量描述的是去壳布局 | **提出**常量修订方案（**需再次授权**），同时 S4 预演守卫 |
| 任意 | **不匹配** | **γ**：运行时代码与目录不符 | **停止**；不得改常量；回报"需要正确的运行对象（去壳 out.exe）" |
| 读不到 / 异常 | — | 观测手段不成立 | 停止；回报；**不得**改用 Frida 或外部读内存 |

---

## 6. 明确排除的方案（本方案不采用）

1. **Frida 附加**该客户端（历史 2 次尝试 0 成功：`ProcessNotFoundError`、`ProcessNotRespondingError`）。
2. **外部进程内存读取**（`ReadProcessMemory` 等）。
3. **修改运行映像**（运行时打补丁以"让门禁通过"）。
4. **默认或无条件启用 `SizeOfImage` 容差**。
5. **删除/绕过映像身份门禁**或任何前缀守卫。
6. 在 `GOLDEN-LOBBY-001` 冻结目录内运行或写入。
7. 以"端口监听成功"或"工具运行成功"作为阶段成果。

---

## 7. 基线不变更的机械核对清单（每步执行前后各一次）

| 项 | 核对方式 | 期望 |
|---|---|---|
| `GOLDEN-LOBBY-001/REF_LOBBY_KIT/` | 目录内文件 mtime 与 SHA-256（对照 `_golden_hashes.json`） | **未变化** |
| `REF_LOBBY_KIT/` | `lobby_server.py`、`nt10.py` 等 9 个核心文件哈希 | 与 `_golden_hashes.json` 一致 |
| `hosts` / `dwauth.ini` / `iips.ini` | 哈希 | **未变化** |
| `Launch_OLMod.bat` / `Injector32.exe` / `Bootstrapper32.dll` / `*.Ayria32` | 哈希 | **未变化** |
| F / D 两树 `git status --porcelain` | 与运行时对比 | 仅本次授权的源码改动；D 树 **0** 改动 |
| 沙箱 `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\` | 逐次运行后归档并记录哈希 | 每次运行有独立日志集 |

---

## 8. 成功/失败判据（一句话）

- **本阶段成功** = 取得 `stage=host_image_*` 的实际值与 `0x0FEA20`/`0x8371A` 的运行时字节，并据此把"α / β / γ"确定为**三者之一**。
- **本阶段失败** = 仍未取得上述任一证据，或被迫以放宽门禁换取"绿"。
- **"进对局"不属于本阶段判据**；它只在 S8 且必须由**客户端侧证据**确认。
