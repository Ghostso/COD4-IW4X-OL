# COMBAT_SERVER_EVIDENCE_INDEX — 结论 ID 与原始证据索引

**配套文件**：`COMBAT_SERVER_HISTORICAL_FINDINGS.md`（结论正文）、`COMBAT_SERVER_CALLCHAIN_MAP.md`、`COMBAT_SERVER_BLOCKERS.md`、`COMBAT_SERVER_BASELINE_SHA256.txt`。
**性质**：只读归档。所有条目均为历史证据转写；**未新增运行时实验**。

**字段说明**
- **结论 ID**：稳定唯一标识。
- **证据等级**：`源码` / `静态二进制` / `离线测试` / `真实运行` / `仅历史报告`。
- **原始证据**：文件路径 + 行号 / 日志名 / 测试记录。
- **复核状态**：`已复核`（本轮直接读取原始载体）/ `历史记录`（只有文档转述）/ `待复核`。
- **适用目标**：客户端版本 / 模块 / 配置。
- **限制条件**：不能据此推出的结论。
- **对后续研发的影响**：为什么必须保留。

> 路径中未写盘符者，均相对工作区根 `D:\BaiduNetdiskDownload\使命召唤OL\`。盘符路径统一写作 `<F>\…`（活动基准 F）、`<E>SANDBOX\RUN001`（运行时沙箱）。

---

## A. 项目目标与架构决策

| 结论 ID | 结论内容 | 证据等级 | 原始证据 | 复核状态 | 适用目标 | 限制条件 | 对后续研发的影响 |
|---|---|---|---|---|---|---|---|
| **CS-A01** | 本轮任务书目标 = 在既有启动至大厅链路上直接创建战斗服务器，使客户端进入实际战斗并完成对局；不以大厅/登录/匹配/通用 DS/启动器/Frida 为最终目标 | 仅历史报告（任务书） | 本任务书第一节 | 已复核 | 项目 | 不涉及技术实现 | 所有后续工作的目标锚点 |
| **CS-A02** | `ol_game_server` 是 `set_kind("shared")`，产物名 `CodolGameServer.Localnet32`（DLL 非 exe） | 源码 | `xmake.lua:191-194` | 已复核 | ol-mod | 不证明其能被加载 | 决定"进程内模块"形态 |
| **CS-A03** | 引擎绑定对象是**宿主进程主映像** | 源码 | `EngineBindings.cpp:3654` | 已复核 | ol-mod | 不证明映像身份 | 决定门禁语义 |
| **CS-A04** | `Createserver` 故意返回 `nullptr`，只为保留模块被加载 | 源码 | `Appmain.cpp:8152-8158` | 已复核 | ol-mod | **不表示**未实现/未加载 | 排除"Createserver 是战斗入口"的误判 |
| **CS-A05** | 服务逻辑挂在 `Com_Frame`（RVA `0x0FEA20`）5 字节相对跳转上 | 源码 | `FrameHook.cpp:39-71` | 已复核 | ol-mod | 未真实运行过 | 帧循环入口 |
| **CS-A06** | `runsGameServer = role != Client` ⇒ combined/dedicated 都跑服务器（listen-server） | 源码 | `ProcessRole.hpp:47-50` | 已复核 | ol-mod | 不证明生产实际用哪个角色 | 对局形态 |
| **CS-A07** | 28960 监听由后端 `ConfigureSession` 触发，非插件加载 | 源码 | `Appmain.cpp:2084-2098`；`COMBAT_SERVER_RECOVERY_BASELINE.md:184-188` | 已复核 | ol-mod | 无真实 ConfigureSession 样本 | 否定"监听=开服"的误解 |
| **CS-A08** | CODOL 客户端无通用 GSC compiler/VM；authoritative GSC 必须自建 | 仅历史报告（源码审查结论） | `CODOL_SERVER_PROGRESS_20261009.md:175` | 历史记录 | 客户端 1649370 | 未在运行时逐项验证 | 脚本层必须由服务器承载 |
| **CS-A09** | 后端未成为独立 daemon；`client` 角色是进程内 socket bridge | 仅历史报告 | `backend.md:7`；`CODOL_SERVER_PROGRESS_20261009.md:92` | 历史记录 | ol-mod backend | — | 多进程集成方式 |
| **CS-A10** | 活动基准 F；D 冻结只读（R1–R8） | 仅历史报告 + 本轮实测（两树 HEAD 均 `2a75bdd`） | `BASELINE_ADJUDICATION.md` 第 0/2 节；本轮 git 复算 | 已复核 | 工作树 | 会话目录未锚定 F | 防止在错误副本上构建 |
| **CS-A11** | `out.exe` 从"项目级根依赖"降级为"逆向来源对象 O-1" | 仅历史报告 | `FULL_ENCRYPTED_CLIENT_TARGET_ADJUDICATION.md:26-71,135-149`；`NEXT_PHASE_PLAN.md:32-39` | 历史记录 | 项目 | 未用户裁定前不改变门禁 | 决定 P0 路线候选 |
| **CS-A12** | 禁止通过修改期望哈希/RVA/前缀/尺寸常量"让门禁变绿" | 仅历史报告 | `NEXT_PHASE_PLAN.md:41-51,132-139`；`ARTIFACT_BLOCKERS.md:8` | 历史记录 | 项目 | — | 约束一切后续修复方式 |

## B. 原版客户端与引擎

| 结论 ID | 结论内容 | 证据等级 | 原始证据 | 复核状态 | 适用目标 | 限制条件 | 对后续研发的影响 |
|---|---|---|---|---|---|---|---|
| **CS-B01** | O-3 = `codoMP_client_shipRetail.exe`，7,841,344 B，SHA-256 `36997674…B537`，FileVersion 1649370，`TimeDateStamp=0x6096930A`，`SizeOfImage=0x0E659000`，ImageBase `0x400000`，EntryRva `0x0E5DC690`，7 段 `.tp3`×6+`.tvm0` | 静态二进制 | `FULL_ENCRYPTED…:82,441-454`；`ARTIFACT_BLOCKERS.md:159-180`；`_combat_baseline/pe_identity.log` | 已复核 | 客户端 1649370 | 加壳件；**不得**当作运行时映像 | 身份基准 |
| **CS-B02** | O-1 = 去壳 `out.exe`，SHA-256 `044c396c…257f9`，build 1649370，`0x6096930A`/`0x0E5D6000` | 静态二进制（注解） | `tools/reverse/annotations/out.exe.json:3`；`EngineBindings.hpp:438-439` | 历史记录（本体不存在） | 门禁常量来源 | ImageBase/段布局 UNKNOWN | 决定 R-A 可行性 |
| **CS-B03** | O-2 = 3.3.3.3 QA 客户端，`0x57611E31`/`0x0C72A000`，无独立 SHA | 源码 | `backend/Demonware/CodolClientPatches.cpp:45-46,610-616` | 已复核 | O-2 | 不得套用到本客户端 | 解释旧基线钩子为何不安装 |
| **CS-B04** | O-5 = `E3823FD6…F37B` 归属四方互斥（见 CS-X01） | 仅历史报告 | `ARTIFACT_BLOCKERS.md:124-151` | 历史记录 | 制品集合 | 未裁定 | 影响可接受制品 |
| **CS-B05** | EXE 导入描述符恰好 1 个：仅 `codoMP_client_shipRetailBase.dll`；IAT 槽 VA `0x0E9DC665`；入口 `FF 15 65 C6 9D 0E`；无 base relocations | 静态二进制 | `_core012_artifact_summary.md:21-24`；`game-net-hunt-report.md:1854` | 已复核（转引 + 文件存在核对） | 客户端 1649370 | 不证明运行时行为 | 补丁策略基础 |
| **CS-B06** | Base.dll：60,327,992 B，`EF75220D…6A20`，ImageBase `0x10000000`，8 节，`SizeOfImage=0x03991000`；导出 3 函数 **0 具名**；真实导入表在 `.idata2`（21 DLL/748 槽） | 静态二进制 | `COD OL/docs/protocol.md:15-41,47,55-69,157` | 已复核（转引） | 客户端 1649370 | 块 6/15/17 序数块前缀不可信 | 逆向基线 |
| **CS-B07** | CODOL 游戏侧**不使用 IOCP**，进程**不监听端口**（accept/listen 全在 libcurl） | 静态二进制 | `game-net-hunt-report.md:1805-1813,1821-1823`；`net-familyAB-report.md:354-410,422-423` | 历史记录 | 客户端 1649370 | 名面/形态面结论，def-use 全零 | 支持"战斗服必须内嵌"的判断 |
| **CS-B08** | `EngineBindings.hpp` 门禁常量：`ExpectedTimestamp=0x6096930A`、`ExpectedImageSize=0x0E5D6000`、`ComFrameRva=0x0FEA20` | 源码 | `EngineBindings.hpp:438-440` | 已复核 | ol-mod | — | P0 常量 |
| **CS-B09** | `EngineBindings.hpp:434-435` 注释引用 O-2 常量，属**过期注释** | 源码 | `EngineBindings.hpp:434-435`；`FULL_ENCRYPTED…:339` D-6 | 已复核 | ol-mod | 只改注释不动常量 | 防跨构建误用 |
| **CS-B10** | 门禁实现在 `bind()` `:3647-3667`，**静默失败无日志**；`bindingCommitted_.store(false)` fail-closed `:3653` | 源码 | `EngineBindings.cpp:3647-3667` | 已复核 | ol-mod | — | P0 可诊断性缺口 |
| **CS-B11** | `bind()` 内 9 处 `return false`；仅 `:3656 / :3660 / :3666` 三处**不写日志**；其日志通道与 `logGameServer` 同为 `[role/game-server] CodolGameServer.log` | 源码 | `EngineBindings.cpp`；`RuntimeLog.cpp:60,77` | 已复核（本轮独立核实） | ol-mod | 不区分 `TimeDateStamp` vs `SizeOfImage` | **支持定位失败阶段** |
| **CS-B12** | 具名守卫 `:3669-3693`（native entity）/ `:3695-3742`（player DObj）；未具名 `||` 链 `:3744-4023`；其他阶段 `:4153 runtime_slots`、`:4203 message_bindings`、`:4210 glass_bridge` | 源码 | `EngineBindings.cpp` | 已复核 | ol-mod | — | 失败可诊断阶段划分 |
| **CS-B13** | RVA 常量数：`static constexpr … *Rva =` 实测 **145**；宽口径去重标识符 **146**（多出 `CURRENT_CHARACTER_GET_RVA`）；文档记 145/146/170 三值 | 源码（本轮实测） | `EngineBindings.hpp`；`FULL_ENCRYPTED…:480`；`CODOL_SERVER_PROGRESS_20261009.md:184` | 已复核 | ol-mod（D 树） | 计数口径不同 | 见 CS-X02 |
| **CS-B14** | 前缀守卫：`EngineBindings.cpp` 中 `std::equal(` 实测 **82**；文档另记 66 / 78–79 | 源码（本轮实测） | `EngineBindings.cpp`；`FULL_ENCRYPTED…:254`；`artifact_provenance.json:38-41` | 已复核 | ol-mod（D 树） | 78/79 是加壳不匹配数 | 见 CS-X03 |
| **CS-B15** | `ClientProcessPatches.cpp` 25 个 `*Rva`，含 `UnsignedFastfileVerificationRva=0x8371A`，期望 `83 7C 24 08 01 0F 94 C0`；打补丁点 `:811-831`、`:1254-1261` | 源码 | `ClientProcessPatches.cpp:207-211,811-831,1254-1261` | 已复核 | ol-mod | 未运行验证 | 第二处硬编码身份 |
| **CS-B16** | `Com_Frame` 期望前缀 `55 8B EC 56 57`（`EngineBindings.cpp:755-757`） | 源码 | `EngineBindings.cpp:755-757`；`ARTIFACT_BLOCKERS.md:103` | 已复核 | ol-mod | — | 守卫 #1 |
| **CS-B17** | 已确认调用约定：`PmoveSingle 0x41DBA0`(`__cdecl`)、`PM_SetPitchValues 0x41E720`(EAX+stack)、`CM_WorldTrace 0x58AFE0`(EDX/EDI)、`CM_TransformedBrushModelTrace 0x58B230`(ECX/EDX,cleanup 0x18)、`SV_Trace 0x5FB940`(ECX/EDX,cleanup 0x10)、`BG_PlayerStateToEntityState 0x4134B0`(EAX/ECX)、`QuatToAxis 0x62A5A0`(EAX/ECX) 等 | 源码 + 静态二进制 | `.agents/modules/reverse_engineering.md:134,157,163,165,171,175,183,205,211` | 历史记录（行号转引） | 客户端 1649370/3.3.3.3 | 部分条目来源构建需按对象标注 | ABI 兼容性判断基础 |
| **CS-B18** | 结构尺寸：`playerState_s=0x3564`、`usercmd_s=0x2C`、`pmove_t=0x12C`、`trace_t=0x28`、`entityState_s=0x110`、`DObj_s=0xCC`、`characterInfo_t=0x3B8`、`hudelem_s=0xA8` | 源码 + 静态二进制 | `reverse_engineering.md:197,209,211,179,183,251,271` | 历史记录 | 客户端 | 未在运行时逐项验证 | 序列化实现基础 |
| **CS-B19** | 地图/zone 加载函数族：`DB_FindXAssetHeader 0x49E7D0`、`DB_LoadXAssets 0x49F960`、`DB_AppendCommonMPZones 0x49FD00`、`DB_IsZoneLoaded 0x4A0820`、`DB_GetRawBuffer 0x4A1620`；`Com_StartHunkUsers 0x59CFE0` 完整链必须保留 | 静态二进制（i64） | `reverse_engineering.md:90-95,136`；`game_server.md:217-219` | 历史记录 | 客户端 | — | 世界/registry 初始化 |
| **CS-B20** | World 加载 ABI：`CM_LoadMap 0x585B20`（ECX=mapName，栈 bspName/gameType，EAX 返回 collision checksum）→ `CM_LinkWorld 0x58C810` → 查 `COMWORLD` | 源码 | `game_server.md:271-275` | 已复核（源码） | ol-mod + 客户端 | 未真实运行成功 | 进图前置 |
| **CS-B21** | `mp_crash_tropical` mapents：262,262 B、2,123 实体、185 `script_brushmodel`；另 3 个 `script_vehicle_collmap` | 静态二进制 | `reverse_engineering.md:257` | 历史记录 | 地图资产 | — | 碰撞/实体来源 |
| **CS-B22** | 原版引擎独立的"战斗/会话创建"函数、原版 `NET_Frame`、原版 gametype 初始化入口 = UNKNOWN | — | 见 CS-U08 | 待复核 | 客户端 | **不得**按常见架构补全 | 战斗入口判定的根本缺口 |

## C. 战斗服务器代码

| 结论 ID | 结论内容 | 证据等级 | 原始证据 | 复核状态 | 适用目标 | 限制条件 | 对后续研发的影响 |
|---|---|---|---|---|---|---|---|
| **CS-C01** | `src/game_server` 173 文件 / 134,119 行（不计空行；精确计行 139,300）；`server_mp` 134 文件 | 源码（本轮实测） | `src/game_server`；`CODOL_SERVER_PROGRESS_20261009.md:34` | 已复核 | D 树 | 行数随工作树变化 | 规模基准 |
| **CS-C02** | 初始化链：`DllMain:9511-9519 → initialize():7012 → processRole():7017 → (Dedicated patches):7111-7132 → bind():7133-7137 → installFrameHook:8128/7155` | 源码 | `Appmain.cpp` | 已复核 | D 树 | F 树行号不同 | 初始化解剖 |
| **CS-C03** | 端口：28960/UDP（`sv_network_mp.hpp:56`）、28961/TCP（`DedicatedControl.hpp:16`）、28962/TCP（`:17`）、28970/TCP（`SharedRoomControl.hpp:14`）、4200/TCP（`Localnetworking.hpp:27`） | 源码 | 同名文件 | 已复核 | ol-mod | 不代表实际监听 | 端口语义 |
| **CS-C04** | DTLS 状态机 `NET_DtlsPacket`（`net_dtls_cod.cpp:544`）；序列 INIT→INIT_ACK→COOKIE_ECHO→COOKIE_ACK→DATA(0x06) | 源码 + 离线测试 | `net_dtls_cod.cpp`；`ServerCoreTests.cpp:27411-27494` | 已复核 | ol-mod | 固定向量测试非真实客户端 | 传输闭环 |
| **CS-C05** | netchan 分片：CODOL 用 `fragmentIndex + lastFragmentIndex + stride(1154) + fragmentLength`；sequence bit 31/30/29；ACK 载 4×32-bit bitmap | 源码 | `net_chan_mp.cpp:660/1012/1061`；`game_server.md:356` | 已复核 | ol-mod（1649370） | — | 重组正确性 |
| **CS-C06** | `ClientState { Free, Connected, ClientLoading, Active }` 是**语义状态机，非原生枚举序数** | 源码 | `sv_client_mp.hpp:61-69` | 已复核 | ol-mod | — | 状态转换命名 |
| **CS-C07** | `SV_ConnectionlessPacket`（`sv_client_mp.cpp:492`）处理 getchallenge/connect；`SV_PacketEvent`（`:643`）；`SV_GetChallenge`（`:3262/3360`）；`SV_DirectConnect`（`:3384`） | 源码 | 同名文件 | 已复核 | ol-mod | 未真实运行 | 客户端连接入口 |
| **CS-C08** | `ServerCore::runFrame`（`sv_main_mp.cpp:8376`）20 Hz 编排 beginFrame→ClientThink→endFrame；`onServerFrame`（`Appmain.cpp:6437`）→ `Network.NET_Frame`（`:6633`） | 源码 | 同名文件；`game_server.md:316-318` | 已复核 | ol-mod | 未真实运行 | 帧循环内核 |
| **CS-C09** | `CodolGameServer.Localnet32` 导出实测 **54 个** | 源码 | `Appmain.cpp:8142-9499` | 已复核 | D 树 | 十处导出符号名 UNKNOWN | 插件 ABI |
| **CS-C10** | `Createserver` 调用者 = `Localnetworking.cpp:400-414 Bridge::claimsHost`；返回 nullptr 即入 `rejectedHosts` | 源码 | `Localnetworking.cpp:400-414` | 已复核 | ol-mod | — | 澄清职责 |
| **CS-C11** | 测试覆盖缺口：9 个插件专属文件共 **31,953 行**零测试（`xmake.lua:199-209`） | 源码 | `xmake.lua:199-209`；`CODOL_SERVER_PROGRESS_20261009.md:225-240` | 已复核 | ol-mod | — | 最大工程风险 |
| **CS-C12** | `ol_transport_lifecycle_tests`：**checks=106 failures=0**（T-1 验收）；T-2 口径 **124/0** | 离线测试 | `T1_ACCEPTANCE_REPORT.md:15-17,71`；`_batch10_evidence/T1_rerun_forced.log` | 已复核 | ol-mod | 无"OS 层端口已释放"反证（UV-1） | 传输可测性 |
| **CS-C13** | `ol_game_server_tests` / `ol_dedicated_control_tests` / `ol_playerdata_def_tests` 均 run exit=0 | 离线测试 | `_run_tests.log` | 已复核 | ol-mod | 纯离线 | 回归基线 |
| **CS-C14** | `CodolGameTests.py` **Ran 59 · FAILED (failures=1)**：`test_only_dedicated_uses_native_qa_launch_bypass` | 离线测试 | `_t23_caller_tests.log` | 历史记录 | 工具 | 断言 `launch_arguments("auto","client")` 实得 `['-qa']` | 工具链缺口 |
| **CS-C15** | 未实现/未闭环：`G_Damage` 缺 9 依赖；`g_run_frame_for_entity` missing；PVS 未恢复；SD 回合/炸弹/plant-defuse 未闭环；世界模型缩放 producer 未定位；后端非独立 daemon；launcher 多实例未做 | 仅历史报告 | `CODOL_SERVER_PROGRESS_20261009.md:118-126,150-152,256`；`game_server_coverage.md:24,25,28,50-59,72,74` | 历史记录 | ol-mod | 矩阵目录已漂移（见 CS-X06） | 可玩性缺口排序 |
| **CS-C16** | 服务器自身能力 vs 依赖引擎能力的分界 = **`bind()`** | 源码 + 仅历史报告 | `xmake.lua:199-209`；`COMBAT_SERVER_RECOVERY_BASELINE.md:262-264` | 已复核 | ol-mod | — | 基线判定核心 |

## D. 战斗创建链路

| 结论 ID | 结论内容 | 证据等级 | 原始证据 | 复核状态 | 适用目标 | 限制条件 | 对后续研发的影响 |
|---|---|---|---|---|---|---|---|
| **CS-D01** | ol-mod 线战斗参与点 = `Com_Frame` hook + DedicatedControl 控制面；`Createserver` 与战斗创建**无关** | 源码 | `Appmain.cpp`；`FrameHook.cpp`；`Localnetworking.cpp` | 已复核 | ol-mod | — | 排除错误入口 |
| **CS-D02** | 监听触发链：`ConfigureSession → configureSessionDescriptor()（sv_main_mp.cpp:1563）→ Network.start()（sv_network_mp.cpp:20）→ bind(0.0.0.0:28960)（win_net.cpp:113）→ setEnabled(true)（sv_main_mp.cpp:1166）` | 源码 | 同名文件 | 已复核 | ol-mod | 无真实描述符样本 | 开服前置 |
| **CS-D03** | 后端`Matchmaking`：`mmbook → mmstart → BookingSink → DedicatedBookingDispatcher` | 仅历史报告 | `CODOL_SERVER_PROGRESS_20261009.md:83` | 历史记录 | ol-mod backend | — | 请求产生侧 |
| **CS-D04** | 客户端桥在 `Com_Frame` 捕获原生 booking selection + item-ID loadout | 仅历史报告 | `CODOL_SERVER_PROGRESS_20261009.md:72` | 历史记录 | ol-mod | — | 会话数据来源 |
| **CS-D05** | 已验证的客户端房间转换（文档自述）：`ready room (event 8) → FIND_SERVERS → mmbook → event 21 accepted → mmstart → gameplay challenge` | 仅历史报告 | `playable_architecture.md:140-147` | 历史记录 | ol-mod | 原始 trace 不可复核 | 入口形态 |
| **CS-D06** | `0x15/5` query kind：1=FIND_SERVERS、3=FIND_LOBBIES_BY_PLAYLIST；忽略 discriminator 曾致 `EXE_CLIENTFAILEDTOCHALLENGE` | 仅历史报告 | `playable_architecture.md:149-159` | 历史记录 | 客户端 | — | 匹配语义 |
| **CS-D07** | 客户端侧已定位：`QuickMatch 0x6F2C10 → 0x6F0940`；`client allocation entry 0x6E4A20`（=FIND_SERVERS 路径，**非** authoritative server startup）；`mmbook accepted` 处理 `0x6E6F60`；`mmstart` 构造 `0x6E6BF0`；room ready `0x6E5320`；room singleton slot `0x078B0708` | 静态二进制 | `reverse_engineering.md:86-89,132,149` | 历史记录 | 客户端 1649370 | 未确认与战斗服的直接关系 | 入口候选 |
| **CS-D08** | 协议逆向线完整战斗握手（真实抓包逐字节）：NAT 29B → DTLS init 16B → cookie 38B → 219B → 114B ack → 数据帧 → getchallenge/connect/stats/heartbeat → usercmd(14B) → gamestate(259B) → 运动快照 | 真实运行（抓包）+ 源码 | `REF_LOBBY_KIT/BATTLE_SERVER_PROTOCOL.md` 第 1 节；`battle_server.py` | 已复核（文档 + 文件存在） | 客户端 1649370 | 见 CS-X04（日志来源冲突） | 可复用的战斗端点实现 |
| **CS-D09** | 快照字段序列 **29/29 对齐实录**；早期合成 snapshot 使客户端越过 `waiting for player data` 进入地图，但**世界全黑、玩家不在有效出生状态** | 仅历史报告 | `BATTLE_SERVER_PROTOCOL.md` 7.7 节；`playable_architecture.md:192-218` | 历史记录 | 客户端 1649370 | 不得当作"进入对局" | 进图判据 |
| **CS-D10** | **关键否证**：客户端把对局流量送到外部腾讯地址 `101.67.36.18:10035`（发送方 `gcloudvoice.dll`）；600 s 日志中 `28960` 出现 **0 次** | 真实运行（抓包/日志） | `BATTLE_SERVER_PROTOCOL.md` 8.9 节 | 已复核（文档） | 客户端 1649370 | 未定位地址下发来源 | **Lobby→Battle 的真实缺口** |
| **CS-D11** | booking 应答帧格式 = UNKNOWN；DedicatedControl 客户端桥端口/帧格式 = UNKNOWN；用靶场信封答 PvE booking → **9/9 断连** | 仅历史报告 + 离线否证实验 | `REF_LOBBY_KIT/STAGE_REPORT_BATTLE.md` P0-2 | 历史记录 | 协议逆向线 | — | 该线第一未完成节点 |
| **CS-D12** | `mmbook accepted` 推送本身会打断连接（1–2 s 内对端关闭），与 seq 号段无关；该推送是靶场专用信封 | 真实运行（实机复现 ×3） | `BATTLE_SERVER_PROTOCOL.md` 9.1–9.12 节 | 历史记录 | 协议逆向线 | — | 禁用开关依据 |
| **CS-D13** | 靶场路径（推荐端到端）：`playlist != 10 → firing_range=True, len=268, map=mp_firingrange, GameType=0x1000007, MaxPlayers=1, 地址块=127.0.0.1:28960` | 仅历史报告 | `BATTLE_SERVER_PROTOCOL.md` 8.11 节 | 历史记录 | 协议逆向线 | 与第 9 节的开关状态存在轮次差异 | 最短验证路径候选 |
| **CS-D14** | 两线关系（ol-mod ↔ 协议逆向线）= **UNKNOWN**；后者在 P0-2 记录当时**全机找不到 ol-mod 源码**，故为独立重建 | 仅历史报告 | `REF_LOBBY_KIT/STAGE_REPORT_BATTLE.md` P0-2 | 已复核（文档） | 项目 | **不得假定可互换** | 决定路线选择需用户裁定 |

## E. 启动至大厅的固化成果

| 结论 ID | 结论内容 | 证据等级 | 原始证据 | 复核状态 | 适用目标 | 限制条件 | 对后续研发的影响 |
|---|---|---|---|---|---|---|---|
| **CS-E01** | `GOLDEN-LOBBY-001` `STATUS=FROZEN`（2026-10-07），是**唯一权威复现依据** | 仅历史报告 + 文件存在 | `REF_LOBBY_KIT/GOLDEN-LOBBY-001.md`；`_golden_hashes.json` | 已复核（存在） | 大厅线 | 内容未逐行复核 | 保护边界 |
| **CS-E02** | 进大厅启动流程（提权代理 → hosts/dwauth/CA → auth 3074 → lobby 3074 → nt10 拉起 exe + 4 补丁 + KDF hook → 0x81/0x82/0x83 → 0x85） | 仅历史报告 | `GOLDEN-LOBBY-001.md` 第 2 节；`DEV-REPRO/REPRODUCTION-BASELINE-LOBBY-001.md` | 历史记录 | 大厅线 | 本轮未实跑 | 既有基础 |
| **CS-E03** | 2026-10-05 16:36 首次进大厅实机；任务 34→47；截图 `lobby_window.png`；冻结指标 `lobby_srv.log 134,649 B（建立 23/keepalive 15/hmac=OK 235/hmac=BAD 0）` | 真实运行（历史） | `HANDOFF_20261005_LOBBY_REACHED.md` 第 0/2 节 | 历史记录 | 大厅线 | 本轮未复跑 | 大厅锚点 |
| **CS-E04** | 进大厅两个真实修复：`0x83` 用本会话 KDF challenge；playlist 文件名同义名回退 | 仅历史报告 | `HANDOFF_20261005_LOBBY_REACHED.md` 第 1 节 | 历史记录 | 大厅线 | — | 不可回退项 |
| **CS-E05** | Golden 路径**不参与 TCLS**；`WIN_NO_TCLS` 判据是命令行含 `-q/-qa` | 仅历史报告 | `GOLDEN-LOBBY-001.md`；`CODOL_EX031_WIN_NO_TCLS_RUNTIME_PREDICATE.md` | 历史记录 | 大厅线 | — | 启动链关系 |
| **CS-E06** | TCLS 共享内存 `TCLS_SHAREDMEMEMORY<pid>` 512 KiB；producer `tcls_core.exe sub_7D10`，consumer `TenProxy.dll CTclsProxy::Initialize` | 仅历史报告 | `CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT.md` | 历史记录 | 大厅线 | — | 平台上下文 |
| **CS-E07** | Ayria 链：`Injector32.exe → Bootstrapper32.dll → Plugins/*.Ayria32 → Localnetworking 枚举 *.Localnet32`；backend TCP 4200 | 源码 + 真实运行 | `COMBAT_SERVER_RECOVERY_BASELINE.md` 第 2 节；`Localnetworking.cpp:367-379` | 已复核 | ol-mod | — | 战斗线载入方式 |
| **CS-E08** | 环境指纹：`dwauth.ini` 79 B；`iips.ini` 46 B（`enable_iips=1`）；hosts 两条；端口 3074/3074/28960 | 仅历史报告 | `GOLDEN-LOBBY-001.md` 1.5-1.6 节 | 历史记录 | 大厅线 | — | 复现条件 |
| **CS-E09** | 会破坏启动链的操作 15 项 | 仅历史报告 | `REPRODUCTION-BASELINE-LOBBY-001.md` 第 15/16 节；`MASTER-POST-LOBBY-FULL-HISTORY-001.md` 第 7/9 节 | 历史记录 | 大厅线 + ol-mod | — | 保护边界 |
| **CS-E10** | 隔离约束：`COD OL/` 原件只读；`REF_LOBBY_KIT/` 开发副本（26.7 GB；`mem_*` 勿删）；Golden 只读；F 活动基准；D 冻结只读 | 仅历史报告 + 本轮实测（F/D 存在） | `GOLDEN-LOBBY-001.md` 第 6 节；`BASELINE_ADJUDICATION.md` | 已复核（存在性） | 工作区 | — | 操作纪律 |
| **CS-E11** | `GOLDEN-BATTLE-001` **尚未创建** | 仅历史报告 | `STAGE_REPORT_BATTLE.md` P0-3 ⑦ | 历史记录 | 项目 | — | 尚未达成冻结条件 |
| **CS-E12** | （冲突）`REF_LOBBY_KIT/` 与 `GOLDEN-LOBBY-001/REF_LOBBY_KIT/` 9/9 命中 `_golden_hashes.json`；`DEV-PUBLISHER-RESTORE/REF_LOBBY_KIT/` 2 文件漂移 | 静态二进制（哈希） | `_golden_hashes.json`；子代理 D 盘点 9 节 C-1 | 历史记录（本轮未重算） | 大厅线 | 与 MASTER D-20 冲突 | 使用前现算现验 |

## F. 真实运行证据

| 结论 ID | 结论内容 | 证据等级 | 原始证据 | 复核状态 | 适用目标 | 限制条件 | 对后续研发的影响 |
|---|---|---|---|---|---|---|---|
| **CS-F01** | 2026-10-10 三次启动（15:47:48 / 15:48:28 / 15:50:14）产出战斗服务器**首次**运行日志 | 真实运行 | 沙箱 `Ayria\Logs\CodolGameServer.log` | **已复核（本轮直读）** | 客户端 O-3 + ol-mod 插件（deployed `6D493B82…`） | 角色 = combined | 唯一实机证据 |
| **CS-F02** | 三次日志均为 `[combined/game-server] engine binding failed`；每轮紧随 `LOGSTALL … prefix=engine binding failed` | 真实运行 | 同上（582 B） | 已复核 | 同上 | — | P0 直接证据 |
| **CS-F03** | `Localnetworking.log`：`Loaded Localnet32 plugin Alwaysoffline.Localnet32.` + **`Loaded Localnet32 plugin CodolGameServer.Localnet32.`** + `listening on 127.0.0.1:4200` | 真实运行 | 沙箱 `Ayria\Logs\Localnetworking.log`（2,356 B） | 已复核 | 同上 | 不证明后续任何阶段 | 插件加载已解决 |
| **CS-F04** | `AlwaysofflineRe.Localnet32.log`：`Refused to apply CODOL startup patches to an unknown executable image.` ×3 —— **按设计**，非故障 | 真实运行 + 源码 | 同上（339 B）；`CodolClientPatches.cpp:30-46,610-616` | 已复核 | 同上 | — | 排除误判 |
| **CS-F05** | `Bootstrapper32.log` 仅记 2 个 `.Ayria32` 插件，不含战斗服务器 | 真实运行 | 同上（110 B） | 已复核 | 同上 | — | 加载分层正确 |
| **CS-F06** | `CODOLLauncher.log` / `T25_launcher_direct.log` = `Could not create process. Error: 2` | 真实运行 | 同上（各 36 B） | 已复核 | 辅助工具 | 非战斗服务器故障 | 启动工具缺口 |
| **CS-F07** | `CodolGame.py launch` → `Injector exited with code 1`（命令 exit 3）；改照搬 `Launch_OLMod.bat` 才出日志 | 仅历史报告 | `_t2_5_stageD_evidence/stageD_launch.log`；`COMBAT_SERVER_RECOVERY_BASELINE.md` 1.6 节 | 历史记录 | 工具 | — | 复现方式 |
| **CS-F08** | 部署件陈旧：F build `DBA7273A…`(6,559,232, 10-10 12:52) ≠ deployed `6D493B82…`(6,556,672, 10-09 13:49)；D build `0EABD5F5…` | 静态二进制（哈希） | 本轮独立 SHA-256 复算；`_combat_baseline/manifest_check2.log` | **已复核（本轮实测）** | 部署 | 禁止本轮构建/部署重验 | 改源码后直接跑无效 |
| **CS-F09** | Frida 注入该客户端失败：1 次 `ProcessNotRespondingError`（进程存活）；同机 32 位对照成功（`X86_AGENT_OK`） | 仅历史报告 | `COMBAT_SERVER_RECOVERY_BASELINE.md` 7.1 节 U7；`_t2_5_stageD_evidence/x86_agent_control.json` | 历史记录 | 客户端 O-3 | 原因未定论 | 排除"读内存"捷径 |
| **CS-F10** | `REF_LOBBY_KIT/battle_srv.log` 含至少一次"完整真实会话"（21:28:19–21:28:24），另有 328 KB 累计记录 | 真实运行（存疑，见 CS-X04） | `BATTLE_SERVER_PROTOCOL.md` 第 1 节；`battle_srv.log` | 已复核（文件与命令统计） | 协议逆向线 | **逐行来源不可区分** | 不可单独作实机证据 |
| **CS-F11** | 沙箱 `Ayria\Logs\` 现有 6 日志；overlay 44/44；`mp_crash_tropical*.ff` 就位 | 静态二进制 + 本轮实测 | 沙箱目录；`CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` 2.2/3.3 节 | 已复核 | 沙箱 | — | 运行时前置条件 |
| **CS-F12** | `build/bin/release/Ayria/Logs/CodolGameServer.log`（186 KB，1,496 行，2026-10-09 13:52）是**测试进程副产物**，非真实客户端 | 离线测试 | `T1_ACCEPTANCE_REPORT.md:50`；本轮内容分析 | 已复核 | 测试 | **不得**当作实机 | 防止证据误用 |

## G. 冲突与未知

| 结论 ID | 内容 | 证据等级 | 原始证据 | 复核状态 |
|---|---|---|---|---|
| **CS-X01** | `E3823FD6…F37B` 归属四方互斥 | 仅历史报告 | `GOLDEN_COPY_SPEC.md:29`；`artifact_provenance.json:9`；`.agents/AGENTS.md:174` | 历史记录 |
| **CS-X02** | RVA 常量数 145 vs 146（本轮实测：两种口径各得其一） | 源码 | `EngineBindings.hpp`；两份报告 | 已复核 |
| **CS-X03** | 前缀守卫数 82 vs 66 vs 78/79（本轮实测 82） | 源码 | `EngineBindings.cpp`；三份报告 | 已复核 |
| **CS-X04** | `battle_srv.log` 真实会话 vs `收包=0` | 真实运行（存疑） | `BATTLE_SERVER_PROTOCOL.md` 第 1 节 vs `STAGE_REPORT_BATTLE.md` P0-1 | 未定论 |
| **CS-X05** | `EngineBindings.hpp:434-435` 过期注释 | 源码 | `EngineBindings.hpp:434-435` | 已复核 |
| **CS-X06** | `codol_server_function_matrix.json` 参考构建漂移（3.3.3.3） | 仅历史报告 | `CODOL_SERVER_PROGRESS_20261009.md:126,290` | 历史记录 |
| **CS-X07** | 磁盘 SizeOfImage≠期望 ⇒ 身份不匹配（已更正为对象错位） | 仅历史报告 | `FULL_ENCRYPTED…:147`；`NEXT_PHASE_PLAN.md:39` | 历史记录 |
| **CS-X08** | "out.exe 是项目根依赖"（已降级） | 仅历史报告 | `FULL_ENCRYPTED…:31-51` | 历史记录 |
| **CS-X09** | "时间戳相同 ⇒ 同一构建"（禁止） | 仅历史报告 | `artifact_provenance.json:81-85` | 历史记录 |
| **CS-X10** | "全盘 0 个 out.exe" 的范围不一致 | 仅历史报告 | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md:40` vs `ARTIFACT_BLOCKERS.md:36` | 历史记录 |
| **CS-X11** | 协议端口早期结论（IIPS=8000/游戏=8801）作废 | 仅历史报告 | `COD OL/docs/protocol.md:219-222,234` | 历史记录 |
| **CS-X12** | "无静态 IAT" 早期结论作废 | 仅历史报告 | `protocol.md:84-104,212` | 历史记录 |
| **CS-X13** | `FrameHook.cpp`/`Appmain.cpp` 行数差异（报告基准是 D 树） | 源码（本轮实测） | `BASELINE_ADJUDICATION.md:120-121` | 已复核 |
| **CS-X14** | E-1 回归证据从未真正产生 | 仅历史报告 | `BASELINE_ADJUDICATION.md` 第 4 节 | 历史记录 |
| **CS-X15** | REF_LOBBY_KIT 是否已漂移（二说并列） | 静态二进制 | `_golden_hashes.json` vs `MASTER…` 13 节 D-20 | 待复核 |
| **CS-X16** | "本机从未成功初始化" vs 2026-08-14 双客户端验证（两条目标线） | 仅历史报告 + 本轮 git 溯源 | `COMBAT_SERVER_RECOVERY_BASELINE.md:9`；`.agents/research/dedicated_*_20260814.md`；git `55fcdbf` | 已复核（git 日期） |
| **CS-X17** | Lua thread/wait 的两说 | 仅历史报告 | `gsc.md:69` vs `CODOL_SERVER_PROGRESS_20261009.md:173` | 历史记录 |
| **CS-X18** | 三次启动方式（实际 = combined，由日志前缀裁定） | 真实运行 | 日志前缀 vs `CODOL_RUNTIME_BLOCKER_CLEARANCE…` 第 6 节 | 已复核 |
| **CS-U01..U15** | 15 项 UNKNOWN（运行时 RVA 字节、out.exe 存在性、导出表、生产角色环境、ConfigureSession 描述符、overlay 一致性、Frida 原因、原版战斗入口、booking 帧格式、对局地址来源、两线关系、`E3823FD6` 归属、ICH059、十处导出名、清单内容） | — | 见 `COMBAT_SERVER_HISTORICAL_FINDINGS.md` 第 8 节 | 待复核 |

---

## 复核状态汇总

| 状态 | 含义 | 代表条目 |
|---|---|---|
| **已复核** | 本轮直接读取原始载体（源码/日志/哈希/沙箱目录） | CS-A02..A07、A10；B08..B16；C01..C12；D01、D02；F01..F05、F08、F11、F12 |
| **历史记录** | 只有文档转述，原始载体在本工作区不存在或未读取 | CS-A08、A09、A11、A12；C14、C15；D03..D07、D09..D13；E01..E09、E11；F07、F09 |
| **待复核** | 需要新的只读核对或运行证据 | CS-B22；CS-U01..U15；CS-X15 |
