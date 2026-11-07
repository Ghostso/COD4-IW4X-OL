# COMBAT_SERVER_RECOVERY_BASELINE — 纯战斗服务器研发基准

**日期**：2026-10-10
**基准工作树 F**：`F:\桌面\ol\ol-mod-olfinal`（分支 `OLfinal-live`，HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`）
**运行时现场**：`E:\CODOL_SANDBOX\RUN001`
**本轮性质**：**纯只读研究**。未修改任何既有文件、未构建、未部署、未提交；未启动/附加/注入/终止任何进程（本轮开始时沙箱内 0 个 CODOL 进程，结束时仍为 0）。
**本轮新增文件**：仅本报告与 `_combat_baseline/` 下的只读测量脚本与日志。

> **一句话结论**：战斗服务器的**代码已经写好**（`src/game_server` 约 13.9 万行、8 个测试目标可构建），但**它在本机上从未成功初始化过一次**。2026-10-10 的三次真实启动（本项目历史上**首次**产出战斗服务器运行日志）全部停在同一步：
> `[combined/game-server] engine binding failed`。
> 根因是**宿主映像身份门禁**：`EngineBindings::bind()` 要求宿主 exe 的 `SizeOfImage == 0x0E5D6000`（去壳 `out.exe`），而本机唯一存在的客户端映像是 `0x0E659000`（TenProtect 加壳零售件）。**这是当前唯一的硬阻塞点，且它一条就阻断了整条战斗链。**

---

## 1. 项目当前真实状态

### 1.1 代码与工作区（实测）

| 项 | 实测值 | 来源 |
| --- | --- | --- |
| 分支 / HEAD | `OLfinal-live` / `2a75bdd8872bb9f54006382a924c3006ec9affc2` | `git rev-parse` |
| `git status -uall` | **17** 条（12 M + 5 ??），与 T-2.3/T-2.5 基线一致，无漂移 | `git status` |
| 未提交修改 | `src/game_server/{Appmain,FrameHook,sv_network_mp,win_net}.*`、`xmake.lua`、`tools/runtime/*` | 同上 |
| 后端 / 游戏服务器规模 | `src/game_server` 173 文件 / **139,300 行**；其中 `server_mp` 134 文件 / 95,729 行 | CODOL_SERVER_PROGRESS_20261009.md §1.1 |
| 引擎绑定层 | `EngineBindings.cpp` **18,029 行**；`EngineBindings.hpp` **146 个 RVA 常量**、82 个前缀守卫 | 同上 §4；本报告独立复核见 §3 |
| 构建目标 | 16 个：4 插件 + `ol_room_owner` + 8 测试 + fixture + probe + `ol_deploy` | xmake.lua:140-402 |

### 1.2 目标客户端身份（本轮独立重算）

| 字段 | 实测值 |
| --- | --- |
| 路径 | `E:\CODOL_SANDBOX\RUN001\codoMP_client_shipRetail.exe` |
| 长度 / SHA-256 | **7,841,344 B** / **`36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`** |
| FileVersion | 1649370 |
| PE | machine `0x014c` (x86/PE32)、ImageBase `0x400000`、EntryRva `0x0E5DC690`、7 个段（`.tp3` ×6 + `.tvm0`） |
| **TimeDateStamp** | **`0x6096930A`**（2021-05-08 13:32:58 UTC） |
| **SizeOfImage** | **`0x0E659000`** |
| 加壳特征 | TenProtect TP3 / VM0 段名 |

### 1.3 部署状态（**关键：部署件 ≠ 当前源码产物**）

`E:\CODOL_SANDBOX\RUN001\ol-mod-runtime-manifest.json` 记录 44 个条目，`gameExecutable = codoMP_client_shipRetail.exe`。逐件比对构建产物与部署件：

| 制品 | 比较 | build SHA-256（前缀） | deployed SHA-256（前缀） | 部署 mtime |
| --- | --- | --- | --- | --- |
| Localnetworking.Ayria32 | **SAME** | `8F1BC5D424EADEC6` | 同 | 2026-10-09 16:59:35 |
| Platformwrapper.Ayria32 | **SAME** | `A7420E17E3831744` | 同 | 2026-10-09 16:59:36 |
| Alwaysoffline.Localnet32 | **SAME** | `D2B9CA407CCB99B8` | 同 | 2026-10-09 16:59:39 |
| ol_room_owner.exe | **SAME** | `354D5B29834D1FFD` | 同 | — |
| **CodolGameServer.Localnet32** | **DIFF** | `DBA7273A0C9DD31C…`（6,559,232 B，2026-10-10 12:52:50） | `6D493B820E84A21B…`（6,556,672 B，2026-10-09 13:49:42） | 2026-10-09 13:49:42 |

> **含义**：5 个运行时制品里**只有战斗服务器本体是旧的**。当前源码树对 `src/game_server` 的任何修改**从未落到沙箱**。任何"改源码后直接跑"的验证都是无效的——必须先部署（`ol_deploy` 被禁止，需替代落盘流程，且属单独审批）。

### 1.4 被"批准"的目标与引擎绑定的目标互相矛盾

| 定义者 | 目标 | 证据 |
| --- | --- | --- |
| T-2.3 批准的目标构建 | `codoMP_client_shipRetail.exe`，7,841,344 B，`36997674…`，插件 `6D493B82…` | `config/codol-target-build.json` |
| 部署清单 | `gameExecutable = codoMP_client_shipRetail.exe` | `ol-mod-runtime-manifest.json` |
| **引擎绑定目录** | **`out.exe`**，`SizeOfImage=0x0E5D6000`，SHA-256 **`044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9`** | EngineBindings.hpp:438-439；ReplayEngineBindings.py:23-27 |

**`out.exe` 在本机不存在**：
- 本项目已登记为制品门禁 **B1–B4（全部 BLOCKED）**：ARTIFACT_BLOCKERS.md §1-§4。
- 本轮独立有界扫描（根：`E:\CODOL_SANDBOX`、`C:\Games`、`F:\桌面\ol`、`D:\BaiduNetdiskDownload\使命召唤OL`）**未发现任何 out.exe**，也**未发现任何 SizeOfImage = 0x0E5D6000 的 PE 文件**；命中的 `codoMP_client_shipRetail.exe` 副本（沙箱 1 份 + D 盘多份备份/实验目录）**全部为 0x0E659000**。
- 证据脚本：`_combat_baseline/find_matching_client.py`、`pe_identity.py`、日志同名 `.log`。

### 1.5 运行现场（不可触碰的固化成果）

| 项 | 状态 |
| --- | --- |
| 当前 CODOL 进程 | **0 个**（本轮开始与结束均为 0；我没有任何终止动作） |
| 28960 / 28961 / 28962 / 28970 | 全部无监听、无占用 |
| `E:\CODOL_SANDBOX\RUN001` | 冻结，本轮只读 |
| 沙箱 `Ayria\Logs\` | **本日新增 6 个日志**（见 §1.6），此前该目录**不存在** |

### 1.6 战斗服务器**首次**真实运行证据（本项目历史第一次）

三次启动（15:47:48 / 15:48:28 / 15:50:14）产出的日志，创建时间 2026-10-10 15:47:48：

| 日志 | 关键内容 | 意义 |
| --- | --- | --- |
| `Localnetworking.log` | `Loaded Localnet32 plugin Alwaysoffline.Localnet32.`<br>**`Loaded Localnet32 plugin CodolGameServer.Localnet32.`**<br>`Localnetworking backend listening on 127.0.0.1:4200.` | **战斗服务器插件确实被加载了**，调用约定问题（G-D1/E-4）**已回答** |
| **`CodolGameServer.log`** | **`[combined/game-server] engine binding failed`** ×3 | **初始化在引擎绑定处失败**，三次完全一致 |
| `AlwaysofflineRe.Localnet32.log` | `Refused to apply CODOL startup patches to an unknown executable image.` ×3 | **按设计如此**，不是故障（CodolClientPatches.cpp:19-28） |
| `Bootstrapper32.log` | 2 个 `.Ayria32` 插件 | `.Localnet32` 由 Localnetworking 加载，故此日志不含战斗服务器属正常 |

> 这三次运行是本项目第一次拿到战斗服务器的**运行时**输出。此前记录状态是"搜索 `client frame hook installed` / `engine binding validation failed` **0 命中**"（FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md:382）。
> **注意**：这三次运行的启动方式**不是** `CodolGame.py launch`（该入口调用注入器时因参数形式不符而失败，属辅助工具问题），而是照搬出货启动器 `Launch_OLMod.bat` 的调用形式。**辅助启动器不在本基线范围内**，仅登记事实。

---

## 2. 纯战斗服务器架构（有证据，不靠模块名猜）

### 2.1 架构图

`~
E:\CODOL_SANDBOX\RUN001\
│
├─ codoMP_client_shipRetail.exe   ← 零售客户端（TenProtect 加壳，SizeOfImage 0x0E659000）
│    │  被 Ayria\Injector32.exe 注入 Bootstrapper32.dll
│    │
│    ├─ Bootstrapper32.dll ──► 载入 Ayria\Plugins\*.Ayria32
│    │      ├─ Localnetworking.Ayria32
│    │      └─ Platformwrapper.Ayria32
│    │
│    ├─ Localnetworking.Ayria32
│    │      ├─ Winsock hooks（改道客户端自身网络）
│    │      ├─ backend TCP 监听 127.0.0.1:4200
│    │      └─ 枚举 Ayria\Plugins\*.Localnet32 → LoadLibraryW → GetProcAddress("Createserver")
│    │             ├─ Alwaysoffline.Localnet32 ──► DW3 后端模拟（认领 hostname）
│    │             └─ CodolGameServer.Localnet32
│    │
│    └─ CodolGameServer.Localnet32  ★★★ 这就是纯战斗服务器本体 ★★★
│           （进程内模块；32 位 DLL；导出 onStartup/onInitialized/Createserver）
│            │
│            ├─ initialize()
│            │     └─ Bindings.bind()  ◄── 宿主映像身份门禁【当前失败点】
│            │             └─ installFrameHook(Com_Frame @ RVA 0x0FEA20)
│            │
│            ├─ 每帧 onServerFrame()（由被 hook 的 Com_Frame 调用，游戏线程）
│            │     ├─ 权威模拟：entity / playerstate / snapshot / gamestate / 伤害 / 武器 …
│            │     ├─ SvUdpTransport  UDP 0.0.0.0:28960（自定义 DTLS，非明文 UDP）
│            │     └─ ClientSessionBridge TCP 127.0.0.1:28962（loadout 捕获）
│            │
│            └─ DedicatedControl TCP 127.0.0.1:28961（后端下发 ConfigureSession / SessionStart）
│
└─ Ayria\ol_room_owner.exe   ← 独立进程：房间名册/令牌 owner（端口 28970），**不是**战斗模拟
`~

### 2.2 组件职责表

| 组件 | 职责 | 证据 |
| --- | --- | --- |
| **CodolGameServer.Localnet32** | **权威战斗服务器**：帧调度、实体/玩家/快照/对局状态、UDP 传输、netchan | xmake.lua:191-212（`shared`，源含 `src/game_server/**`） |
| Localnetworking.Ayria32 | 载入 `.Localnet32` 插件、Winsock 改道、后端 loopback 监听 | Localnetworking.cpp:367-386、:400-412；RuntimePaths.cpp:20-33 |
| Alwaysoffline.Localnet32 | DW3 控制面（Auth3/匹配/booking/持久化） | xmake.lua:162-171 |
| `ol_room_owner.exe` | 共享房间 owner（display name / bridge port / token / ready） | xmake.lua:173-189（只链 SharedRoom* + DedicatedControl，**不含任何 game_server 源**） |
| 零售客户端引擎 | 提供权威模拟所需的原生函数与全局（DB/Msg/CCS/Trace/Pmove…） | EngineBindings.hpp:146 个 RVA |

### 2.3 B3 的明确答案：战斗服务器**不是独立进程**

结论：**客户端进程内嵌模块**（in-client embedded module），通过 **hook 客户端自己的帧函数** 在其游戏线程上跑权威服务器；**同时**存在一个独立的 `ol_room_owner.exe`，但它只做房间/会话归属，**不承载战斗模拟**。

证据链（四条独立）：
1. `xmake.lua:191-194`：`ol_game_server` 是 `set_kind("shared")`、文件名为 `CodolGameServer.Localnet32` —— 是 DLL，不是 exe。
2. `Appmain.cpp:3654`（经 EngineBindings.cpp:3654）：`module_ = GetModuleHandleW(nullptr)` —— 绑定的是**宿主进程自己的主映像**。
3. `Appmain.cpp:8169-8172`：`Createserver` **故意返回 nullptr**；注释写明该导出只为"让 Localnetworking 加载器保留本模块"，真正的服务不通过 IServer 接口。
4. `FrameHook.cpp:59-113` + `Appmain.cpp:8135-8146`：服务逻辑挂载在 `Com_Frame`（RVA 0x0FEA20）的 5 字节相对跳转上。
5. `ProcessRole.hpp:47-50`：`runsGameServer(role) = role != Client` ⇒ **`combined`（默认）与 `dedicated` 都跑战斗服务器**，即"同进程自带服务器"（listen-server）形态。

---

## 3. 已确认的初始化与战斗调用链

### 3.1 初始化链（自 DllMain 至帧钩子）

| # | 步骤 | 位置 |
| --- | --- | --- |
| 1 | `DllMain(DLL_PROCESS_ATTACH)` → `initialize()` | Appmain.cpp:9538-9544 |
| 2 | `role = OlMod::processRole()`（读 `OLMOD_PROCESS_ROLE`，未设/未知 ⇒ Combined） | Appmain.cpp:7017；ProcessRole.hpp:17-40 |
| 3 | 角色分支：`Dedicated` 必须先 `installDedicatedProcessPatches()` 成功，否则 return | Appmain.cpp:7111-7131 |
| 4 | **`Bindings.bind()` —— 失败即 `logGameServer("engine binding failed")` 并 return** | **Appmain.cpp:7133-7137** |
| 5 | `installFrameHook(Bindings, onServerFrame)` | Appmain.cpp:8135-8146；FrameHook.cpp:59-113 |
| 6 | `installClientInputPatches(role)`（仅新装钩子时） | Appmain.cpp:8141-8142 |
| 7 | 引擎每帧调用被 hook 的 `Com_Frame` → `runServerFrame()` → `onServerFrame(GetTickCount())` | FrameHook.cpp:31-48 |

### 3.2 战斗链（bind 成功之后才会发生）

`~
onServerFrame(now)                                  Appmain.cpp:6437
 ├ if (!runsGameServer(role)) return                 Appmain.cpp:6603-6604   ← Client 角色到此为止
 ├ ensureDedicatedControlServer()                    Appmain.cpp:6606 → DedicatedControl.cpp:201-258
 ├ processDedicatedControlMessages()                 Appmain.cpp:6607
 └ Network.NET_Frame(Server, now)                    Appmain.cpp:6633 → sv_network_mp.cpp:100
       ├ NET_GetPacket (recvfrom)                    win_net.cpp:183-215
       ├ ++status_.packetsReceived                   sv_network_mp.cpp:121
       └ ServerCore::NET_DtlsPacket(...)             sv_network_mp.cpp:139 → net_dtls_cod.cpp:544
             INIT(0x01) → INIT_ACK(0x02) → COOKIE_ECHO(0x03) → COOKIE_ACK(0x04) → DATA(0x06)
             解密后：0xFFFFFFFF 前缀 ⇒ SV_ConnectionlessPacket
                     getchallenge → challengeResponse → connect → connectResponse
                     在册 XUID 校验 ⇒ ClientState::Connected → ClientLoading → Active
`~

启动 UDP 监听的实际触发者是后端下发的会话配置，**不是**插件加载：

`backend ──ConfigureSession──► DedicatedControl:28961 ──► Server.configureSessionDescriptor()（sv_main_mp.cpp:1563）──► Network.start()（sv_network_mp.cpp:20）──► bind(0.0.0.0:28960)（win_net.cpp:113）──► Server.setEnabled(true)（sv_main_mp.cpp:1166）`

> 因此：**没有后端会话配置，端口 28960 不会监听**。端口监听是结果，不是目标。

---

## 4. 已有实现 vs 缺失实现对照表

判定口径：✅ 有源码实现 + 有离线测试通过；🟡 有源码实现但**无独立测试目标**或无运行证据；❌ 缺失；⬛ **从未运行过**（被门禁阻断）。

### 4.1 战斗服务器核心（`src/game_server/server_mp/`，134 文件）

| 能力 | 实现位置 | 测试覆盖 | 真实运行证据 |
| --- | --- | --- | --- |
| 帧调度 / 每帧 tick | Appmain.cpp:6437 `onServerFrame` | 🟡 经 ServerCoreTests | ⬛ |
| client ingress / netchan | sv_client_mp.cpp:643 `SV_PacketEvent` | ✅ ServerCoreTests | ⬛ |
| connectionless 命令 | sv_client_mp.cpp:492-520（getchallenge/connect/gamestateupdate/heartbeat） | ✅ | ⬛ |
| DTLS 握手（P-224/AES-CTR/HMAC-SHA1） | net_dtls_cod.cpp:544-710 | ✅ 固定向量 ServerCoreTests.cpp:27411-27494 | ⬛ |
| UDP socket 生命周期 | win_net.cpp / sv_network_mp.cpp | ✅ **ol_transport_lifecycle_tests**（真 socket，124/0） | ⬛ |
| 玩家状态（native playerstate/entitystate/characterinfo） | sv_native_*_mp.cpp | ✅ | ⬛ |
| 快照 / delta / baselines | sv_snapshot_mp / sv_const_baselines_mp | ✅ | ⬛ |
| gamestate / 对局状态 | sv_gamestate_mp | ✅ | ⬛ |
| 武器开火 / 弹道 / 命中 | sv_weapon_fire_mp / sv_bullet_mp / sv_trajectory_mp | ✅ | ⬛ |
| 伤害 / 死亡 / 半径伤害 | sv_damage_mp / sv_radius_damage_mp | ✅（通用 `G_Damage` 仍标 partial，缺 9 依赖） | ⬛ |
| 手雷全链（发射/飞行/接触/引爆/爆炸） | sv_grenade_*_mp | ✅ | ⬛ |
| 近战 / 导弹 / 装备 / 奖励 / 记分板 | sv_melee_mp / sv_missile_mp / sv_equipment_mp / sv_rewards_mp / sv_scoreboard_mp | ✅ | ⬛ |
| 实体模拟 / 碰撞 | sv_entity_mp / sv_collision_mp | ✅ | ⬛ |
| 出生 / 消失 / 断开 | sv_client_spawn_mp / sv_client_events_mp / DisconnectWitness.cpp | ✅ | ⬛ |
| 反延迟 / 可破坏物 / 地图触发器 / MapEnts | sv_antilag_mp / sv_destructible_mp / sv_map_triggers_mp / sv_mapents_mp | ✅ | ⛔ |
| 游戏模式（playlist） | sv_playlist_mp / CodolPlaylist | ✅（SD 回合状态机自述"未闭环"） | ⬛ |
| Lua 5.4 脚本层 | sv_script_lua_mp / sv_script_builtin_mp / sv_script_source_mp | ✅ **ol_lua_runtime_tests**（82 KB） | ⬛ |
| 僵尸 / Factory 内容 | sv_zm_*_mp | ✅ | ⬛ |

### 4.2 桥接层（**最大单点风险**）

| 能力 | 实现 | 测试覆盖 | 真实运行证据 |
| --- | --- | --- | --- |
| **EngineBindings**（146 RVA + 82 前缀守卫 + 4 门禁点） | 18,029 行 | ❌ **不在任何测试目标内** | ⬛（本日首次执行，止于门禁） |
| 帧钩子 FrameHook | FrameHook.cpp | ❌ 无 | ⬛ |
| ClientProcessPatches / DedicatedProcessPatches | 各自文件 | ❌ 无 | ⬛ |
| 9 个插件专属文件（31,953 行） | — | ❌ 无 | ⬛ |

### 4.3 会话与房间

| 能力 | 实现 | 测试 | 真实运行证据 |
| --- | --- | --- | --- |
| DedicatedControl（TCP 28961） | DedicatedControl.cpp | ✅ ol_dedicated_control_tests | ⬛ |
| ClientSessionBridge（TCP 28962） | ClientSessionBridge.cpp | ✅ ClientSessionBridgeTests | ⬛ |
| `ol_room_owner.exe`（28970） | SharedRoom* | 📄 自述 | ⬛ |
| 多成员 SessionStart（schema v5） | DedicatedBookingDispatcher.cpp | ✅ | ⬛（自述"两个真实客户端的自然验证未发生"） |

### 4.4 缺失实现（相对"玩家真正进对局"）

| 缺口 | 状态 | 依据 |
| --- | --- | --- |
| 通用 `G_Damage` 完整语义 | ❌ 缺 9 依赖 | codol_server_function_matrix.json（⚠️ 该目录已过期，参考构建指向 3.3.3.3） |
| `g_run_frame_for_entity` | ❌ missing | 同上 |
| Lua thread / wait / endon / 通用 notify | ❌ 无 | gsc.md（经进度报告 §3.5） |
| CODOL per-client PVS 可见性策略 | ❌ 未恢复 | game_server_coverage.md |
| SD 模式回合状态机 / 炸弹 / 安装拆除 / objective | ❌ 未闭环 | game_server_coverage.md |
| 世界模型缩放 producer | ❌ 未定位 | 同上 |
| 后端独立 daemon | ❌ 仍是进程内 bridge | backend.md:7 |
| launcher 多实例清单 | ❌ 未完成 | 进度报告 §2.2 |

---

## 5. 从当前状态到真实对局的最短路径（按依赖排序）

| 序 | 阻塞点 | 类别 | 性质 |
| --- | --- | --- | --- |
| **P0** | **宿主映像身份门禁**：`bind()` 要求 `SizeOfImage == 0x0E5D6000`（`out.exe`），本机客户端为 `0x0E659000` | **原版与项目接口不兼容** + **实现存在但初始化条件不满足** | **硬阻塞。它一条就阻断 100% 的战斗链**（无绑定 ⇒ 无钩子 ⇒ 无 NET_Frame ⇒ 无 28960 监听 ⇒ 无对局） |
| P1 | 部署件陈旧（`build DBA7273A` ≠ `deployed 6D493B82`） | 工程流程缺口 | 阻断"改源码后验证"，不阻断现状复现 |
| P2 | 后端下发 `ConfigureSession` 未在真实环境接通（28961 ← backend） | 网络/会话未打通 | 端口 28960 因此从不监听 |
| P3 | 两个真实客户端的 room→ready→capture→connect→snapshot 自然闭环未发生 | 已具备实现但缺真实运行证据 | 需 P0 先解除 |
| P4 | 通用 `G_Damage` / Lua thread / PVS / SD 回合机 | 缺少实现 | 影响"可玩"，但不阻断"能进对局" |

**判定说明（严格区分）**
- P0 属"**接口不兼容 + 初始化条件不满足**"，不是"缺实现"：18,029 行绑定代码、146 个 RVA、82 条守卫**全部已写**，只是门禁不放行。
- P0 之下的传输/会话/模拟**全部已实现且有离线测试**，一旦 P0 解除即可直接观察。
- **不能把"端口监听成功"当成"进入对局"**：本基线中 28960 从未监听，因为会话配置链路本身也没跑通过。

### 5.1 P0 的两种处置路线（二选一，需用户裁定）

| 路线 | 内容 | 优点 | 代价/风险 |
| --- | --- | --- | --- |
| **R-A：取得去壳 `out.exe` 本体** | 用户提供本体或"来源说明 + 完整 SHA-256"（解除 B1/B2/B3） | 零代码风险；146 个 RVA 与 82 条守卫**原样成立** | 依赖外部制品；本机不存在，本项目已登记 BLOCKED |
| **R-B：把目录移植到现有加壳客户端** | 在受控试验下越过 `SizeOfImage` 门禁，让 82 条守卫**实际执行**，据结果决定是否重标定 | 不需要缺失制品；结果**决定性**：要么守卫全过（战斗服务器立即可用），要么精确指出第一处不匹配 | 若加壳映像运行时代码与目录布局不同，则需大规模重标定（146 RVA）；**必须一次只放宽一项，且保留全部守卫** |

> **关键未知（本轮禁止用运行时实验消除）**：TenProtect 在内存中解包后，`0x0FEA20` 等 RVA 处的**运行时代码字节**是否等于 `out.exe` 的期望值。文件级测量（B4 已做）**不能**回答，因为加壳映像的文件字节必然被替换（ARTIFACT_BLOCKERS §4）。这正是下一步要设计的最小实验。

---

## 6. 下一项具体研发任务（仅提案，本轮不实施）

### 6.1 任务 T-3.0：让战斗服务器的引擎绑定门禁**可诊断**并对现有宿主做**受控受试**

**要解决的具体问题**
`bind()` 在宿主身份门禁处**静默** `return false`（无任何日志），导致：
1. 无法从日志判断失败发生在门禁还是 82 条守卫中的某一条；
2. 82 条前缀守卫**从未在真实目标上执行过一次**，因此"现有加壳客户端是否与 `out.exe` 目录兼容"这个决定性问题始终无法回答（离线工具 ReplayEngineBindings.py 已证明静态文件 **INSUFFICIENT_EVIDENCE**）。

**对应代码与调用链**
- 门禁：`EngineBindings.cpp:3647-3667`（`GetModuleHandleW(nullptr)` ⇒ 校验 `TimeDateStamp`/`SizeOfImage`，**无日志**）。
- 已具名守卫：`EngineBindings.cpp:3669-3693`（`native entity binding prefix mismatch function=X`）、`3695-3742`（`player DObj binding prefix mismatch function=X`）。
- **未具名复合守卫**：`EngineBindings.cpp:3744-4023` 的约 80 条 `||` 链，失败只写 `engine binding validation failed stage=function_prefixes`（**不指出是哪一条**）。
- 消费点：`Appmain.cpp:7133-7137`；`FrameHook.cpp:63-67`（`!bindings.valid()` ⇒ reject）。

**最小必要改动（三项，互不耦合）**
1. **门禁具名化**：把 `3647-3667` 的两项比较拆为独立判定，失败时写 `stage=host_image_timestamp effective=0x… expected=0x…` / `stage=host_image_size effective=0x… expected=0x…`。**纯日志，不改变任何判定语义。**
2. **复合守卫首失败者具名**：把 `3744-4023` 的 `||` 链改为"逐条判定并在首个失败处记录 `name=<符号> rva=0x…`"。**判定结果（真/假）逐位不变。**
3. **受控旁路（默认关闭）**：新增显式环境开关（建议 `OLMOD_BINDING_IMAGE_SIZE_TOLERANCE=1`），**只跳过 SizeOfImage 相等判定**；`TimeDateStamp` 与**全部 82 条前缀守卫保持强制**。未设置该变量时，行为与现状**逐位相同**。

**可能影响的模块**
- 必改：`src/game_server/EngineBindings.{hpp,cpp}`。
- 不改：`Appmain.cpp` 主流程、`FrameHook.cpp`、传输层、`ClientProcessPatches`/`DedicatedProcessPatches` 的既有门禁（但会因新的日志分级而更易诊断）。
- 风险面：仅初始化路径；不改动任何已通过测试的行为。

**回归测试方案**
- 复用既有：`tools/reverse/ReplayEngineBindings.py` + `ReplayEngineBindingsTests.py`（68 断言 / 16 用例 / 0 失败）必须保持通过。
- 新增（本任务的核心回归价值）：把 `EngineBindings` 纳入**一个最小测试目标**（当前 0 覆盖，是本项目最大工程风险）。用例至少覆盖：
  1. 时间戳不符 ⇒ 门禁拒绝且日志 stage 正确；
  2. 尺寸不符 + 容差关闭 ⇒ 拒绝（与现状等价）；
  3. 尺寸不符 + 容差开启 ⇒ 门禁放行、守卫继续执行；
  4. 守卫全过 ⇒ `valid()==true`；任一守卫不符 ⇒ `valid()==false` 且**日志给出正确符号名**；
  5. 容差关闭时，新代码与旧代码在同一输入上**判定一致**（差异仅日志）。
- 必须保持：`ol_game_server_tests`、`ol_transport_lifecycle_tests`（124/0）、`ol_playerdata_def_tests`、`ol_dedicated_control_tests`、`ol_lua_runtime_tests` 全部通过，失败数为 0。

**真实运行验证条件（需单独审批）**
- 前置：先解决 P1 部署陈旧（把新构建的 `CodolGameServer.Localnet32` 落到沙箱；`ol_deploy` 禁用，需替代落盘流程）。
- 动作：启动 **1 个** 沙箱客户端（`combined` 或 `dedicated`），**只读** `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\CodolGameServer.log`。**不需要附加、注入或 Frida**——这是本任务相对"读进程内存"方案的关键优势（本机 Frida 注入到该客户端曾被拒，见 §7）。
- 判定（三者必居其一，均为决定性结果）：
  | 日志结果 | 含义 | 后续 |
  | --- | --- | --- |
  | `stage=host_image_size effective=0x0E659000 expected=0x0E5D6000`（容差关闭） | 门禁确实是唯一拦截点 | 开容差重跑 |
  | 出现 `name=<符号> rva=0x…` | 加壳映像运行时代码**与目录不符** | **P0 判为硬阻塞，`out.exe` 成为必需**（B1 结论升级为"已证"） |
  | `game server frame hook installed` 且无 stage 失败 | 目录**可移植到现有客户端** | 战斗服务器首次真正初始化 → 立即进入 P2（会话配置）验证 |

**尚需单独审批的操作**
1. 修改 `src/game_server/EngineBindings.{hpp,cpp}`（代码变更）；
2. 新增/修改测试目标（`xmake.lua`）；
3. **构建**；
4. **部署**到 `E:\CODOL_SANDBOX\RUN001`（`ol_deploy` 禁止，需替代流程）；
5. 启动 1 个沙箱客户端并读取其日志。

### 6.2 验收标准（T-3.0）

1. 三项改动完成，且**容差关闭时判定语义与改前逐位一致**（有对照用例证明）；
2. 新增门禁/守卫单元用例全部通过，且 `EngineBindings` 首次进入测试目标；
3. 既有 5 套测试 + ReplayEngineBindings 68 断言全部通过，**无新增失败**；
4. 真实运行产生**可判定的日志**，落入 §6.1 三张结果之一，并附原始日志与哈希；
5. 全程未附加、未注入、未终止任何进程，未触碰 28960/28961/28962/28970 的释放探测。

---

## 7. 未知项与证据引用

### 7.1 UNKNOWN（本轮无法由只读证据判定）

| # | 未知项 | 说明 | 影响 |
| --- | --- | --- | --- |
| U1 | 加壳映像**运行时**在 `0x0FEA20` / `0x8371A` 等 RVA 处的字节是否等于目录期望 | 文件级测量必然不符（加壳）；离线重放判定 `INSUFFICIENT_EVIDENCE` | **决定 R-A 还是 R-B**，是 P0 的核心未知 |
| U2 | `out.exe`（`044c396c…257f9`）本体是否存在与任何地方 | 本机有界扫描 0 命中；全盘 0 来自上游审计，本轮未独立重跑全盘 | 决定 R-A 可行性 |
| U3 | `E3823FD6…F37B` 归属（OLfinal 目标 vs 3.3.3.3 QA 客户端） | 三份文档互相矛盾，未裁定 | 影响可接受制品集合 |
| U4 | 生产环境是否设置 `OLMOD_PROCESS_ROLE=dedicated` / `OLMOD_HOST_ADDRESS` | 只有读取方在树内，无启动脚本在范围内 | 影响对局形态（listen-server vs dedicated） |
| U5 | 后端下发 `ConfigureSession` 的真实 Demonware 描述符字节（含 16 字节会话密钥） | 解析器在 net_dtls_cod.cpp:163-178，无可读实例 | 阻断 28960 监听 |
| U6 | 沙箱 `Alwaysoffline` 的 44 项 overlay 是否与当前源码一致 | 本轮只比对了 5 个二进制，未逐项比对 overlay 资产 | 影响后端行为 |
| U7 | Frida 为何无法注入该客户端 | 本日 1 次尝试 `ProcessNotRespondingError`（进程存活）；同机 32 位对照进程注入成功 | 影响未来"读运行时映像"手段的可行性（**T-3.0 刻意不依赖它**） |

### 7.2 证据引用一览

| 主题 | 证据位置 |
| --- | --- |
| 门禁常量 | `src/game_server/EngineBindings.hpp:438-439` |
| 门禁实现（静默失败） | `src/game_server/EngineBindings.cpp:3647-3667` |
| 具名守卫 | `src/game_server/EngineBindings.cpp:3669-3742` |
| 未具名复合守卫 | `src/game_server/EngineBindings.cpp:3744-4023` |
| 绑定失败消费点 | `src/game_server/Appmain.cpp:7133-7137` |
| 帧钩子安装 | `src/game_server/Appmain.cpp:8135-8146`；`FrameHook.cpp:59-113` |
| 插件 ABI（Createserver 故意空实现） | `src/game_server/Appmain.cpp:8156-8172` |
| 角色判定 | `src/shared/ProcessRole.hpp:10-50` |
| UDP socket 参数 | `src/game_server/win32/win_net.cpp:71-138` |
| DTLS 状态机 | `src/game_server/qcommon/net_dtls_cod.cpp:544-710` |
| 会话配置 → 监听 | `src/game_server/Appmain.cpp:2086-2111`；`sv_network_mp.cpp:20` |
| 构建目标 | `xmake.lua:140-402` |
| 运行时日志（本日首次） | `E:\CODOL_SANDBOX\RUN001\Ayria\Logs\{CodolGameServer,Localnetworking,Bootstrapper32,AlwaysofflineRe.Localnet32}.log` |
| 部署清单 | `E:\CODOL_SANDBOX\RUN001\ol-mod-runtime-manifest.json`（44 项；插件 `6D493B82…`） |
| 批准的目标构建 | `config/codol-target-build.json` |
| 制品门禁 B1–B6 | `ARTIFACT_BLOCKERS.md` |
| 服务端进度与覆盖评级 | `CODOL_SERVER_PROGRESS_20261009.md` §3-§6 |
| 离线绑定重放工具 | `tools/reverse/ReplayEngineBindings.py`（42,867 B）；`OFFLINE_BINDING_REPLAY_REPORT.md` |
| 本轮只读测量脚本/日志 | `_combat_baseline/{pe_identity,find_matching_client,manifest_check,manifest_check2}.py` 及同名 `.log` |

### 7.3 本轮**未**做的事（纪律声明）

- 未修改、未创建、未删除任何工程文件（仅新增本报告与 `_combat_baseline/` 只读测量产物）。
- 未构建、未部署、未提交、未推送。
- **未启动、未附加、未注入、未终止任何进程**（本轮 0 次；沙箱进程数始终为 0）。
- 未执行任何运行时实验来消除 U1/U2/U3（按任务要求不做）。
- 未重做已有审计：制品门禁直接引用 `ARTIFACT_BLOCKERS.md`，服务端盘点直接引用 `CODOL_SERVER_PROGRESS_20261009.md`，本轮只做**独立复核 + 新增运行时事实**。

---

**下一步**：等待确认。建议确认两项——
1. P0 处置路线选 **R-A（取得去壳 out.exe）** 还是 **R-B（受控试验 + 目录移植）**；
2. 是否批准实施 **T-3.0**（仅诊断与容差开关，不含部署与运行）。
