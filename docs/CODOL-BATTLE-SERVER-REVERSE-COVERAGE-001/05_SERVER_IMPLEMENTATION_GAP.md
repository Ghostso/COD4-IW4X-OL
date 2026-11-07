# 05 — 现有服务端工程与参考实现差距 / SERVER IMPLEMENTATION GAP

**任务**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001` 第四阶段
**目标版本**：2.6.9.7（兼容目标）；参考实现覆盖 1.1.1.13 / 3.3.3.3。
**每个缺口格式**：①证据表明什么行为 → ②现有服务端实现了什么 → ③差在哪里 → ④解决方式 → ⑤完成后解锁哪个战斗功能。

---

## 0. 现有服务端资产总览

| 工程 | 语言 | 目标版本 | 规模 | 定位 | 仓库状态 |
|---|---|---|---|---|---|
| ol-mod `src/game_server` | C++ 插件(DLL) | 3.3.3.3 QA | 173 文件 / ~139,300 行（`server_mp` 95,729） | 最完整 CODOL 原生服务端**参考** | 本工作区存在（`_e1_regression\ol-mod-olfinal`） |
| ol-mod `src/backend` | C++ 插件 | 3.3.3.3 | 61 文件 / 10,458 行 | DW3 控制面 + booking + DedicatedControl | 同上 |
| C# Combat Server v0.1 | C# | 未标 2697 | 22 源文件 | 可 `csc` 构建的**实验底座** | 存在；122 项离线自测 |
| REF_LOBBY_KIT `battle_server.py` | Python | 3.3.3.3 | 69,019 B | **唯一有真实大厅→战斗握手**的实现 | 存在；有 `battle_srv.log` |
| OLD/1113（CoD4x fork） | C | 1.1.1.13 | `src\codol\net`+`snapshot` | 网络/引擎/消息层**算法参考** | 源码存在；无 PDB/MAP |
| CoD4x_Server | C | COD4 | — | 骨架模板（HIGH）/ 协议模板（LOW） | 外部参考 |
| iw4x-client | C++ | MW2 | — | OOB/发现/认证信封参考（LOW） | **无服务器源码**（REFUTED） |

---

## 1. 版本目标差距（最高层的战略缺口）

| # | 项 | 内容 |
|---|---|---|
| **G-00** | 现有服务端实现的是 **3.3.3.3 / 1.1.1.13**，而目标是 **2.6.9.7** | ①证据：目标客户端 `35375404…`（2.6.9.7）；2697 服务端 `80816711…` 唯一含 2697 协议层。②现有：ol-mod=3.3.3.3、OLD/1113=1.1.1.13。③差距：无任何工程以 2.6.9.7 为目标完成。④解决：先把 ol-mod（3.3.3.3）作为**行为参考**，字段/布局全部以 2697 服务端 + C-2697 客户端证据重验；或评估 2697 原生服务端（路线 A）。⑤解锁：决定 MVP 是「先在 3.3.3.3 打通闭环、再移植」还是「直接对 2697」。 |

> **禁止**：把 3.3.3.3 的 loadout、netfields、weapon IDs、snapshot 字段直接当成 2697。

---

## 2. 协议 / 网络缺口

### G-01 2697 记录层（bdDTLS 风格 DATA 记录）
- ①**证据表明**：战斗通道使用 `06 02 tag counter mac8 len cipher` 16B 头 + AES 流 + HMAC-SHA1 截断 8B；密钥来自 P-224 ECDH ‖ securityKey；`serverTag=cookie[14:16]`（真实抓包 + `codol_crypto.py`）。
- ②**现有**：C# `CodolProtocol.cs` 实现该记录层；OLD `codol_handshake.c`/`codol_crypto.c` 有源码级实现。
- ③**差距**：**对 C-2697 从未观测**；`COOKIE_ECHO` 189 vs 219 冲突（CONFLICT-01/BQ-10）；记录层加密原语在旧源与 C# 间存在 AES192/Tiger192 vs AES128/SHA1 描述冲突（BQ-11）。
- ④**解决**：以 2697 服务端字节为准做**离线对照**；取得一条 C-2697 记录即闭合；先参数化 COOKIE_ECHO 长度与密码套件。
- ⑤**解锁**：客户端能连上并进入握手后阶段（MVP 的 M1）。

### G-02 客户端 opcode `0x02` 分派
- ①**证据表明**：2697 服务端写 `0x02 | long | short | payload`（上限 0x3FC）；客户端 `0xA2E50` 读 `long+short+payload`（上限 0x3FC）——**字段形状一致**。
- ②**现有**：C# `ClientCommandReader.cs`、ol-mod `_SV_WriteReliableCommand` 对应实现。
- ③**差距**：**opcode→0xA2E50 的控制流未定位**；`.text` 线性扫描 0 命中（可靠性 95.1%），`.tvm0` 未解码，`.data` 99.86% 缺失。这是**最高业务价值的兼容性障碍**（BQ-21）。
- ④**解决**：**先解码 `.tvm0`** 再搜索分派；或从客户端运行时 dump 取 `0xA2E50` 的调用栈/回调注册。**不得**靠字段形状强行推进。
- ⑤**解锁**：usercmd/可靠命令的实际消费与分发（M4）。

### G-03 客户端 `0x06`（EOF/EOS）语义与外层分帧器
- ①**证据表明**：2697 服务端在 gamestate/configstring/snapshot 内部用 `0x06` 作终止；位游标在字节边界强制重同步。
- ②**现有**：服务端写入侧闭合（`_WriteConfigstrings`/`_WriteGamestate`）。
- ③**差距**：客户端读取/终止判断 = `NOT-OBSERVED`；`0x06` 的 EOF 与子段/阶段结束分工不明（BLK-3/BLK-8/BQ-18/22）；configstring **外层消息分派器未定位**（BLK-7）。
- ④**解决**：2697 configstring body 已逐指令还原（`0xA0807..0xA0997`），沿调用者向上定位外层分派；纯静态可推进。
- ⑤**解锁**：gamestate/configstring/snapshot 的正确分帧与终止（M5）。

### G-04 Snapshot 帧边界与 delta 基准
- ①**证据表明**：2697 快照写入链 `_CODOL2697_WriteSnapshot 0xA4FA0 → _WriteSnapshotReached 0xA4860`；区域拼接常量 `0x728 / 0x2C38 / count*0x1F8 / count*0x13C / count*0x5C`；3.3.3.3 抓包快照字段序列 **29/29 对齐**、124B/帧。
- ②**现有**：C# `MotionSnapshot.cs` 位级快照；ol-mod `sv_snapshot_mp`；OLD `SV_WriteSnapshotToClient`（仍用 IW3 序列化器）。
- ③**差距**：**帧边界未定**（BLK-5/BQ-17）；delta 基准与实体字段范围未闭合；客户端 delta 解码 `0x6E060`/`0x6D340` 未绑定（BQ-25）。
- ④**解决**：取一条真实 snapshot 帧作帧边界判据；或从客户端解码函数反向还原。
- ⑤**解锁**：世界状态同步与首个可解析快照（M6）。

### G-05 2697 注册门控 5 字段业务语义
- ①**证据表明**：注册文件格式链闭合（3 变体格式串 + `sscanf==3` + `kind∈{1,2}` + CRC32 + `+0x6408`）；`client-registration2697.txt` 首行 `codol2697-registration 2 6b6fb5d0 180 139 f78302fe`。
- ②**现有**：C# `SessionDescriptor`/注册校验器（格式层）。
- ③**差距**：5 个字段（kind/id/180/139/CRC 等）的**业务语义**未知（BLK-4/BQ-31）；合法放行路径（`+0x78F4`/`+0x6408`）未完全闭合。
- ④**解决**：2697 服务端**指令级**还原门控放行分支（纯静态）；生成合法注册文件做离线校验。
- ⑤**解锁**：在合法门控下发布 gamestate（M5）。

---

## 3. 大厅→战斗接线缺口（本审计最高价值项）

### G-06 booking / DedicatedControl 接线
- ①**证据表明**：`room ready(event 8) → FIND_SERVERS(0x15/5) → mmbook(0x06/14) → event 21 accepted → mmstart → BookingSink → DedicatedBookingDispatcher`；DedicatedControl 协议（ProtocolVersion 2、28961/28962、`OLDC`、24B 头、MessageType 1–20）**已完整定义**。
- ②**现有**：**ol-mod 已实现全部这些组件**（`DedicatedControl.hpp/.cpp`、`Servers.cpp`、`SharedRoomClient`、`DedicatedBookingDispatcher`、`ol_room_owner.exe`）。REF_LOBBY_KIT（唯一能进大厅的组件）**没有**这些。
- ③**差距**：**两个世界未接线**——冻洁大厅基线（REF_LOBBY_KIT）不加载 ol-mod 插件；ol-mod 的 booking 应答从未与冻洁客户端对接。早期「ol-mod 源码 BLOCKED」因源码现已到位而**消解**（P0-2 结论过时）。
- ④**解决**：在冻洁大厅基线上新增 booking/DedicatedControl 接线（**只读 Golden 用副本**），按已定义的 6/14 → DedicatedControl → booking accepted 建桥；用 `battle_selftest.py` 做离线回归。
- ⑤**解锁**：**Lobby→Booking→Battle 第一条闭环**（M2）；这是从「进大厅」推进到「进战斗」的关键一步。

### G-07 对局地址真实下发来源
- ①**证据表明**：战斗端点来自 21/5 findSessions 的 session 对象；C# 已能导出 258B 记录 + 16B securityKey + endpoint。
- ②**现有**：C# `SessionDescriptor`/`SessionExporter` 可导出；REF_LOBBY_KIT 有 21/5 与 6/14 的抓包。
- ③**差距**：实测客户端把对局流量送 **外部腾讯 `101.67.36.18:10035`**（`gcloudvoice.dll`），`28960` 出现 **0 次**（CS-D10）；地址下发来源**未定位**（U-7）。
- ④**解决**：隔离运行 + 抓包，证明客户端对局流量确实到达我方 28960（`battle_srv.log` 出现 `RX #1 16B`，且非离线自测写入）；必要时用客户端 socket 钩子 `[edi+0x1B8]` 接管端点。
- ⑤**解锁**：客户端真正连上我方战斗服（M2→M3）。

### G-08 ol-mod L1 引擎绑定宿主身份门禁
- ①**证据表明**：`EngineBindings::bind()` 要求宿主 exe `SizeOfImage==0x0E5D6000` + `TimeDateStamp==0x6096930A`（去壳 `out.exe` `044c396c…257f9`）；门禁依赖 146 个 RVA/82 条前缀守卫。
- ②**现有**：`EngineBindings.cpp` 18,029 行已完成绑定；部署 44/44 就位；插件被成功 `LoadLibraryW`；`initialize()` 确实被调用。
- ③**差距**：本机唯一客户端映像 `SizeOfImage=0x0E659000`（加壳零售件）≠ 期望；三次真实启动均 `engine binding failed`，**无 stage 日志**（P0-a 不可区分是时间戳/尺寸/签名哪一项）。**一条阻断 100% 战斗链**。
- ④**解决**：取得 `out.exe`（或来源说明 + SHA-256）；或经授权在插件内**只读**读取自身模块头与 `0x0FEA20`/`0x8371A` 字节（**先取证、后判门禁**，禁止直接放宽 SizeOfImage 检查 CS-A12）。
- ⑤**解锁**：ol-mod 线进入帧循环并监听 28960（M1）。

---

## 4. 世界 / 战斗逻辑缺口（ol-mod，3.3.3.3，文档自述为主）

| # | 功能 | ①证据表明 | ②现有实现 | ③差距 | ④解决 | ⑤解锁 |
|---|---|---|---|---|---|---|
| G-09 | 帧循环 | 20Hz 编排 beginFrame→ClientThink→endFrame | `ServerCore::runFrame`（sv_main_mp.cpp:8376） | 从未真实运行 | 解除 G-08 后运行 | 权威帧推进 |
| G-10 | 移动/Pmove | 玩家移动/视角 | `NativePmoveBindings`、shared Pmove、`usercmd delta 0x005A1BE0` | 2697 state layout 未重验；无真实碰撞 | 版本重验 + BSP/Clip | M4 移动 |
| G-11 | 伤害 | 命中/伤害/死亡 | `g_damage`（缺 9 依赖）、`client_impacts`、`bullet_process` | 通用 `G_Damage` 未完成 | 补 9 依赖 | M4 战斗 |
| G-12 | 死亡/复活 | pain/view kick/respawn | `player_die`（缺 7 依赖） | 未闭环 | 补齐 | M4 |
| G-13 | 记分/击杀 | 记分板玩家行闭环高；killfeed 未解码 | 部分实现 | killfeed wire 未解码 | 定向解码/回放 | M5 事件 |
| G-14 | SD 模式 | 分队出生/击杀失能 | 部分 | 回合不结束/重开、炸弹不能 plant/defuse、HUD 未闭环 | 补模式状态机 | M4/M5 |
| G-15 | GSC/Lua | 脚本按 common→gametypes→maps 加载 | Lua 5.4.8 VM + builtin registry | 无 thread/wait/notify/生产 loader | 补脚本层 | 模式逻辑 |
| G-16 | 武器 | 武器/弹药 | 部分实现 | 世界武器模型 append 未闭；2697 recipe 语义未知 | 补齐 | M4 |

> **注**：G-09..G-16 的目标是 **3.3.3.3**；全部 `.runtime/` 自然实机证据在本工作区**不存在**（R5），以上均只能标注为**文档自述**，不构成可复核事实。

---

## 5. 资源 / 地图缺口

| # | 功能 | ①证据表明 | ②现有 | ③差距 | ④解决 | ⑤解锁 |
|---|---|---|---|---|---|---|
| G-17 | 地图加载 | `_CODOL_MountTarget2697Archives 0x1400C3`；archive 激活判 `[edx+0x34]==0x16D` | 2697 runtime-assets 就位 | 资源加载器/目录索引未还原 | 指令级还原 | M6 进图 |
| G-18 | BSP/Clip 碰撞 | 真实碰撞与视线 | 未实现（C# 缺；ol-mod 部分） | BSP 解析/碰撞数据缺失 | 解析地图数据 | M4 移动/射击 |
| G-19 | runtime-assets 格式 | 11,033 文件 / 1.797 GB | 未逐文件解析 | 是否含协议表/资源索引未知（BQ-36） | 静态盘点 | 资源约束 |

---

## 6. 工程风险缺口

| # | 项 | 内容 | 解决 | 影响 |
|---|---|---|---|---|
| G-20 | 插件边界零测试 | 9 个插件专属文件 **31,953 行**（`Appmain`/`EngineBindings`/`FrameHook` 等）不在任何测试目标 | 纳入测试目标（至少导出面/生命周期冒烟） | 当前最大工程风险 |
| G-21 | 文档漂移 | `codol_server_function_matrix.json`（8-16，指向 3.3.3.3）、`game_server_coverage.md`、`game_server.md` 落后于 10-09 代码 | 修正参考构建与默认哈希；标注过期 | 评估失真 |
| G-22 | 后端非独立 daemon + launcher 多实例 | client 角色仍是进程内 socket bridge | 完成 launcher 多实例 | 多客户端对局 |
| G-23 | 重连/退出/关闭清理 | 无实现（BQ-09） | 定向实现 + 测试 | MVP 健壮性 |

---

## 7. 差距优先级总表

| 优先级 | 缺口 | 类型 | 完成后解锁 |
|---|---|---|---|
| **P0** | G-01 记录层（对 C-2697） | 静态+测试 | M1 连接 |
| **P0** | G-02 客户端 0x02 分派 | 静态（tvm0/dump） | M4 usercmd |
| **P0** | G-03 0x06 / 外层分帧 | 静态 | M5 解析终止 |
| **P0** | G-04 snapshot 帧边界 | 静态+抓包 | M6 世界同步 |
| **P0** | G-06 booking 接线（源码已到位） | 实现+测试 | M2 进战斗 |
| **P0** | G-07 对局地址下发 | 测试 | M2→M3 |
| **P0** | G-08 引擎绑定门禁 | 取证/授权 | M1 L1 帧循环 |
| P1 | G-05 注册 5 字段语义 | 静态 | M5 gamestate |
| P1 | G-20 插件测试覆盖 | 工程 | 边界正确性 |
| P1 | G-09..G-16 战斗逻辑 | 实现 | M4/M5 可玩 |
| P2 | G-17/G-18/G-19 资源 | 静态+实现 | M6 进图 |
| P2 | G-21/G-22/G-23 工程 | 工程 | 稳定性 |

---

## 8. 复用 / 适配 / 重实现 / 阻塞（结论）

- **REUSE**：C# 基础传输/密码原语/会话描述符/离线回归；OLD 消息游标与 netchan 结构；2697 `runtime-assets`；ol-mod `DedicatedControl`。
- **ADAPT**：Handshake、netchan、reliable command、gamestate/configstring/snapshot 的 2697 字段/分支；ol-mod game_server 模块边界/测试方法。
- **REIMPLEMENT**：2697 专属客户端兼容层、未闭合的 opcode 消费链、缺失的资源/脚本桥。
- **BLOCKED**：客户端 `0x02` 分派、`0x06` 语义、2697 注册门控的合法运行路径、snapshot 帧边界、任何端到端互通。
- **OPTIONAL / NOT_REQUIRED**（本目标范围外）：完整武器子系统、PvE booking、结算、持久化、反作弊/平台生产依赖、完整 Demonware 互通。
