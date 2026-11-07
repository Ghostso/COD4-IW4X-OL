# 04 — 路线 B：基于旧源码/独立实现改造

> 旧源码目标不是 2.6.9.7；必须显式区分版本。本文比较三个候选底座。

## 1. 三个候选底座

| 底座 | 路径 | 目标版本 | 源码/实现 | 优势 | 主要缺陷 |
|---|---|---|---|---|---|
| B1 CoD4x fork | `EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy` | CoDOL 1.1.1.13 | `netchan.c`、`msg.c`、`sv_*.c`、`codol/net`、`codol/snapshot` | 原生服务端骨架、完整初始化/帧循环/网络/快照 | 目标版本旧；序列化器未收敛；AGPL-3.0 |
| B2 ol-mod | `_e1_regression\ol-mod-olfinal` | CODOL 3.3.3.3 QA | backend + game_server + server_mp + Demonware | 最完整的 CODOL 原生源码/测试/工具 | 版本更高；GPL-3.0；当前工具链缺失；不能直接套 2697 |
| B3 C# Combat Server | `CODOL-Combat-Server-v0.1` | 未标 2697 | 22 文件：UdpTransport、CodolProtocol、MotionSnapshot、SessionDescriptor、ClientLogic、ServerHost、GameWorld | 可用 Windows `csc.exe` 构建；122 项离线自测；协议字节来自真实抓包 | 真实客户端未连接；仅实现最小战斗子集 |

## 2. B1 CoD4x fork

**已有模块**
- `netchan.c`: `Netchan_Init/Setup/Process/Transmit`，以及 `NET_SendPacket`。
- `msg.c`: `MSG_Init/BeginReading/WriteByte/Short/Long/Data/String/Bits`。
- `sv_main.c`、`sv_client.c`、`sv_snapshot.c`：初始化、客户端、快照主框架。
- `codol/net/*`：握手、association、ECDH、crypto、wire、netchan、连接文本、准入、命令队列。
- `codol/snapshot/*`：configstrings、player/entity、delta、events、frame builder、snapshot。

**结论**：
- 网络/状态机/消息基元：REUSE/ADAPT。
- gamestate/configstrings/snapshot 的 2697 收敛：ADAPT/BLOCKED。
- 不适合直接作为 2.6.9.7 成品，但适合作为算法与协议对照。

## 3. B2 ol-mod

**已有模块**
- `src/backend/Demonware`: Auth、ByteBuffer、booking、控制面。
- `src/game_server/server_mp`: gamestate、snapshot、network、client、entity、pmove、weapon、collision、script 等大量文件。
- `src/game_server/qcommon`: `msg_mp.cpp`、`net_chan_mp.cpp`、`net_dtls_cod.cpp`。
- 测试覆盖大量 CODOL 模块；handoff 记录已运行到玩家、武器、snapshot 等边界。

**结论**：
- 作为 3.3.3.3 源码实现，架构和细节价值最高：ADAPT/参考。
- 不能把 3.3.3.3 的 loadout、netfields、weapon IDs、snapshot 字段直接当成 2697。
- 适合提取模块边界/测试方法，不适合直接改版本号后复用。

## 4. B3 C# Combat Server

**已有模块**
- `Net/UdpTransport.cs`：UDP 传输。
- `Codol/CodolProtocol.cs`：握手、cookie、P224/EC DH、DATA、OOB。
- `Codol/MotionSnapshot.cs`：位级快照。
- `Codol/SessionDescriptor.cs`、`SessionGolden.cs`：会话描述符/黄金向量。
- `Engine/ClientLogic.cs`：connect/heartbeat/gamestateupdate 命令处理。
- `Engine/ServerHost.cs`、`GameWorld.cs`、`ServerConfig.cs`：阶段初始化、世界、配置。
- `SelfTest.cs`：122 项断言。

**已验证**：离线构建、密码学 KAT、P-224、会话描述符、黄金向量、协议自测：VERIFIED。
**未验证**：真实客户端连接、进图、PvE booking、实际战斗：NOT-OBSERVED。
**许可**：报告明确说未复制 AGPL/GPL 代码，只参考架构；仍需在真正复制源码时单独处理许可。

## 5. 路线 B 的差异集中点

1. **版本差异**：1.1.1.13 / 3.3.3.3 / 未标版本，均不是 2.6.9.7。
2. **密码学冲突**：旧源 A/B 报告指出 AES192/Tiger192 vs AES128/SHA1、COOKIE_ECHO 189 vs 219 尚未离线判定。
3. **序列化器**：旧 B1 仍用 IW3 snapshot/configstrings 逻辑；2697 客户端消费链未闭合。
4. **握手/会话**：旧源码有实现，但 2697 客户端实际使用路径未验证。
5. **大厅/匹配**：Python lobby 与 C# session descriptor 可用，但目标客户端版本/字段需重新对齐。
6. **工具链**：C# 可构建；B1/B2 当前缺 xmake/nasm/make/gcc/cl/msbuild。

## 6. 路线 B 判定

**推荐采用 B3 + B1/B2 参考的混合路线，而不是直接 fork 任一旧版：**

- 用 B3 做可执行实验骨架（传输、协议测试、快照、会话描述符）。
- 用 B1 做 netchan/状态机/消息层算法参考。
- 用 B2 做模块划界、测试设计和 CODOL 原生行为参考。
- 所有 2697 字段以 2697 服务端 E1/E2/E3 和后续客户端证据为准。

分类：
- B3：REUSE（实验骨架）。
- B1：ADAPT（运输/状态机/消息）。
- B2：参考/ADAPT（架构和模块）。
- 2697 客户端消费链：REIMPLEMENT/BLOCKED。
