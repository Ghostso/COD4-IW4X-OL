# 复用代码与许可证说明（任务 §二.8 / §四.3）

## 1. 核实结果

| 上游 | 许可证 | 工作树 / HEAD | 核实方式 |
|---|---|---|---|
| **CoD4x_Server** (`callofduty4x/CoD4x_Server`) | **AGPL-3.0** | `DEV-BOOKING\_lineage021\CoD4x_Server` @ `ddd65fc`，`git status` 干净 | `License.md` 第 1-2 行即 `GNU AFFERO GENERAL PUBLIC LICENSE / Version 3, 19 November 2007` |
| **iw4x-client** (`IW4x/iw4x-client`) | **GPL-3.0**（★ 本版更正） | `DEV-BOOKING\_lineage021\iw4x-client` @ `d1b175d` 与 `IW4X\Client核心代码\iw4x-client` @ `0699a7e5`，均干净 | `LICENSE` 第 1-2 行即 `GNU GENERAL PUBLIC LICENSE / Version 3, 29 June 2007` |

> ★ **本版修正**：上一版把 iw4x-client 写成"上游自带 LICENSE（未明示）"。
> 实测其 `LICENSE` 正文是 **GPL-3.0**（不是 AGPL）。这个区分是任务 §二.8 明确要求的，
> 因此在此更正：**CoD4x_Server = AGPL-3.0，iw4x-client = GPL-3.0，两者不同。**

## 2. 本版实际复用了什么（逐项）

### 2.1 从 CoD4x_Server（AGPL-3.0）复用的内容 —— **仅为架构与分层，不复制源代码**

本版 `CODOL Combat Server v0.1` 对 CoD4x_Server 的复用是**工程结构层面**的，具体为：

| CoD4x_Server 中的事实 | 本版对应实现 | 是否复制代码 |
|---|---|---|
| dedicated 服务端是独立进程，`Sys_Initialize`→`Com_Init`→`SV_Init`→主循环 的初始化顺序 | `ServerHost.Initialize()` 的显式阶段机（`InitPhase` 枚举 + 每阶段日志） | 否，仅照搬**顺序与阶段划分**思路 |
| `SV_Frame` 时间步进 + `SV_MasterHeartbeat` 定时任务 | `GameLoop` 固定步长 128 Hz 累加器 + `ScheduledTasks` | 否，仅照搬**固定步长累加器的调度模型** |
| `sv_client.c` 的 client 槽位生命周期（CS_FREE/CS_ZOMBIE/CS_CONNECTED/CS_ACTIVE） | `ClientSession` 的 `SessionState` 枚举与状态迁移 | 否，仅照搬**状态机形态** |
| `sv_snapshot.c` 的 "baseline + delta 快照" | `MotionSnapshot` 的 index-skip 增量编码 | 否；本版编码格式是 **CODOL 实测格式**，非 COD4x 格式 |
| `sv_main.c` 的 `SV_Map`（地图/游戏模式初始化） | `GameWorld.Initialize(map, gametype)` | 否 |

**没有任何一行 CoD4x_Server 源代码被复制、翻译或粘贴进本版。** 上面每条都是"先阅读其结构，再用本版语言独立实现"。

### 2.2 从 iw4x-client（客户端工程）复用的内容

**无代码复用。** 仅用于确认「CODOL 属 IW4 系谱、IW4x dedicated 依赖 iw4x.dll 与特定 MW2 ABI」这一否定性结论（见 `CODOLServer/IW4X_CODOL_REUSE_REPORT.md`），从而排除"直接加载 iw4x.dll"的路线。

### 2.3 从本仓库既有成果复用的内容（本仓库自研，非上游）

| 来源 | 内容 | 许可证影响 |
|---|---|---|
| `REF_LOBBY_KIT/battle_server.py` | CODOL 战斗服协议实现（NAT / DTLS-like 握手 / 数据帧 / netchan / usercmd / 快照） | 本仓库自研资产；本版为其**独立 C# 重实现**，并用它作为字节级对照 oracle |
| `REF_LOBBY_KIT/battle_selftest.py` | 11+3 步离线复放自测 | 同上；本版测试套件为对应移植 |
| `REF_LOBBY_KIT/codol_crypto.py` | AES/HMAC-SHA1 参考 | 同上；本版自实现 |
| `REF_LOBBY_KIT/codol_crypto.py` 的 `bd_common_addr` / `build_session_record` / `build_mission_session_object` | 权威会话描述符（战斗地址下发通道） | 本仓库自研资产；**本版为其 C# 逐字节移植**（`src/Codol/SessionDescriptor.cs`） |
| `REF_LOBBY_KIT/battle_server.py` 的会话/快照调度 | `ClientLogic.PumpGameState/PumpSnapshot` | 同上 |
| `DEV-BOOKING` 静态审计结论（`OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030`、`MVP-PVE-MATCH-ENTRY-009`、`CLIENT-BOOKING-BATTLE-TRIGGER-014`） | 会话描述符的**必要性论证**与"端点来源"结论 | 本仓库自研分析文档，非上游代码 |

### 2.4 本版新移植的会话描述符溯源链（任务 §四.3）

```
ol-mod  MatchmakingService.cpp:284-310       commonAddress()            -> 37B bdCommonAddr
ol-mod  MatchmakingService.cpp:514-558       writeSessionRecordTail()   -> 258B session 记录
ol-mod  MatchmakingService.cpp:614-629       5 个前置字段
三方 C# CodolLocalLobbyServer.cs:420-488     BuildMissionSessionObject  -> 268B / 237B 对象
        |
        v  REF_LOBBY_KIT/codol_crypto.py（已冻结参考实现，可本机执行）
        |
        v  tests/gen_session_golden.py（黄金向量生成器）
        |
        v  CODOL Combat Server v0.1  src/Codol/SessionDescriptor.cs（C# 逐字节移植，零代码复制）
```

★ 注意：ol-mod 与三方 C# 的源码**不在本机**（ol-mod 原始包 `E:\handoff2\ol-mod-olfinal.zip` 已不存在）。
本版移植的是 **`codol_crypto.py` 里那份已被冻结、可在本机执行的参考实现**，
而不是直接读 ol-mod 源码。黄金向量的可重复生成见 `tests/gen_session_golden.py`。

## 3. AGPL 与 GPL 的区分（任务明确要求不得混淆）

- **AGPL-3.0（CoD4x_Server 用的）**比 GPL-3.0 多一条 §13：**通过网络提供服务**（network interaction）时，必须向该服务的用户提供 Corresponding Source。
- **GPL-3.0** 只在**分发**时触发源码义务，SaaS 形态不触发 §13。
- 结论：
  1. 本版**没有链接、没有嵌入、没有翻译**任何 AGPL 代码 → 本版不因此成为 AGPL 的派生作品。
  2. 若将来要把 CoD4x_Server 的**源代码片段**真正编译进本服务端，则整个服务端必须按 AGPL-3.0 §5 以 AGPL-3.0 发布，且按 §13 对网络用户提供源码 —— 这一点**必须在动手前单独决策**，不在本版范围内。
  3. 本版新增代码的许可证由仓库所有者决定；本版**未**擅自附加许可证头或提交。

## 4. 上游义务遵守情况

- 未修改 `CoD4x_Server` / `iw4x-client` 工作树（`git status --porcelain` 为空）。
- 未复制其 LICENSE 之外的文件。
- 未把任一上游的版权声明改写或移除。
- 未提交、未推送任何内容。
