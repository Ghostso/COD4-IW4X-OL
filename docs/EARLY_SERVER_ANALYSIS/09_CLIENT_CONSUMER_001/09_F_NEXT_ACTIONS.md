# 09 — F：下一步最小工作与最小抓包实验计划（Next Actions）

> 任务：`EARLY-SERVER-CLIENT-CONSUMER-001` 任务 E/F 的“下一步”部分。
> **本轮不执行任何抓包/启动/脚本运行**。本文件只是**实验计划**。
> 边界：不修改原始样本、既有报告、可进入大厅的版本；不补丁/反调试/反作弊绕过；不实施协议兼容层或序列化器；不输出秘密材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## F.0 结论先行

- **静态边界已到**：服务端编码账本（`09_A`）、编号体系（`09_B`）已 **CONFIRMED**；客户端解码器**存在**已 **CONFIRMED**，但**分派表**与**本仓库↔客户端逐字节互通** **INSTRUMENTATION_BLOCKED / NOT_OBSERVED**。
- **下一步唯一高价值动作**：应用 `wire_interception.md §4` 的 **game-server tap diff**，捕获**一次完整 gamestate + snapshot 会话**，回答“客户端期望的 snapshot opcode”与“本仓库流是否被接受”。
- **不需要**再重复服务端资产盘点或泛化客户端反编译。

---

## F.1 下一步最小工作（按优先级）

| # | 动作 | 目的 | 前置条件 | 预期产出 | 状态目标 |
|---|---|---|---|---|---|
| N1 | 应用 `wire_interception.md §4` 的 game-server tap diff（**diff only，尚未应用**）到 `game-server.py` | 让下行 game 层事件可见 | `wire_tap.py`/`tap_report.py` selftest 已绿；`game-server.py` 文件未被其他 agent 占用 | `layer:"game"` 事件开始写入 JSONL | 准备 |
| N2 | 用**本仓库 CODOL 服务端**（非参考 Python 服务端）与本客户端跑一次会话 | 产生“本仓库流” | 环境可启动（**本轮不做**） | `console_mp.log` 新轮转 + game 层 tap | 观察 |
| N3 | 从 tap 中读出 s2c snapshot 首字节 `op`、gamestate 首字节、EOF 字节 | 确定客户端接受的 opcode | N1+N2 | opcode 实测值 | **CONFIRMED 或 REFUTED** |
| N4 | 对照客户端 `console_mp.log` 的 `CA_*` 转换与错误行 | 判定接受/拒绝 | N2 | `CA_PRIMED->CA_ACTIVE` 或 `bad command byte`/`overflowed` | **CONFIRMED / REFUTED** |
| N5 | 若客户端拒绝，回到 `09_A` 逐字段核对布局 | 定位差异 | N3/N4 | 差异清单 | 迭代 |

> **不做**：不重跑 `08_OFFLINE_002` 的服务端资产盘点；不泛化反编译客户端。

---

## F.2 最小抓包实验计划（**本轮不得执行**）

### F.2.1 前置条件

1. `wire_interception.md §4` 的 game-server tap diff **已应用**到 `game-server.py`（当前状态：**diff only，NOT applied**）。
2. `wire_tap.py` 与 `tap_report.py` 的 `--selftest` 均为**绿**（文档记载已绿）。
3. `CODOL_TAP=1`（默认路径为 `CODOL_TAP=0`，每帧仅一次 env 查询，开销可忽略）。
4. 使用**本仓库 CODOL 服务端**（`CODOL-AlphaBuild By Antia\CODOL_Server`），**不是** lobby kit 的参考 `game-server.py` 之外的替代实现。
5. 客户端 `console_mp.log` 轮转可用（写权限），便于事后比对。
6. 环境变量/启动脚本**不记录任何认证材料**到抓包文件。

### F.2.2 观察指标（最小集）

| 指标 | 来源 | 期望 |
|---|---|---|
| s2c **snapshot** 首字节 `op` | tap `counter key=snapshot values={op}` | 确认客户端接受的 opcode（候选 `0x00`） |
| s2c **gamestate** `op`/`map`/`gametype`/`fs_crc`/`seq` | tap `kind=gamestate` | 与 `09_A` 布局一致 |
| s2c **serverCommand** 首字节 | tap `kind=server_cmd` | `0x01` |
| **EOF** 字节 | 从 snapshot/gamestate 段尾读出 | `0x05` |
| c2s `clc_packet`/`usercmd` 计数 | tap `counter key=clc_packet/usercmd` | 会话活跃 |
| 客户端 `CA_*` 转换 | `console_mp.log` | `CA_CONNECTED→LOADING→PRIMED→ACTIVE` |
| 客户端 `Received gamestate … bytes` / `configStrings: N` | `console_mp.log` | 与 tap 的 gamestate 一致 |
| 客户端错误行 | `console_mp.log` | **无** `bad command byte` / `ignoring illegible message` / `CL_GetSnapshot: truncated` / `CONFIGSTRINGMISMATCH` |

### F.2.3 停止条件

- **成功**：客户端日志出现 `CA_PRIMED -> CA_ACTIVE`，且 tap 中 snapshot `op` 稳定；→ opcode **CONFIRMED**。
- **失败**：客户端日志出现 `bad command byte` / `ignoring illegible message` / `CL_GetSnapshot: truncated`；→ 记录首个失败 opcode 与字节偏移，停止并回到 `09_A` 核对布局（**REFUTED** 当前 opcode 假设）。
- **无进展**：连续 N 次会话均无法建立 game 层事件（tap 未触发）→ 检查 diff 应用点，停止，避免无效重复。

### F.2.4 数据脱敏要求

| 允许记录 | 禁止记录 |
|---|---|
| 解密后 svc 首字节、长度、计数、EOF | 握手密钥 / 长期密钥 |
| 传输头序号（`serverMessageSequence`、`reliableAcknowledge`、`serverId` 截断 u8） | MAC / 认证令牌 / `c1_keys.bin` 内容 |
| gamestate 结构字段（map/gametype/fs_crc/seq） | 玩家账号 / 会话凭证 / XUID |
| 客户端 `CA_*` 状态行 | 任何可用于重放认证的字节串 |

- XOR key 仅保留**复算所需的 u8 分量**（头字段，非长期秘密）。
- 抓包文件写盘前**剥离**认证/密钥/MAC 字段。
- 输出目录：`09_CLIENT_CONSUMER_001\_capture\`（新建，若执行时）。

### F.2.5 预期产出（执行后）

- `_capture\game_layer_events.jsonl`（脱敏）
- `_capture\console_mp-session.log`（客户端日志副本）
- `10_CAPTURE_FINDINGS.md`（opcode 实测值与接受/拒绝裁决）

---

## F.3 本轮（静态）已完成 vs 待执行

| 项 | 状态 |
|---|---|
| 服务端编码账本 `09_A` | ✅ 完成（CONFIRMED） |
| 编号体系裁决 `09_B` | ✅ 完成（CONFIRMED） |
| 客户端候选 `09_C` | ✅ 完成（REV2，已纠错） |
| 双端矩阵 `09_D` | ✅ 完成 |
| 抓包必要性 `09_E` | ✅ 完成（判定：必要） |
| **抓包实验** | ⛔ **本轮不执行**（F.2 计划） |

---

## F.4 完成标准 7 问（本文件负责收口）

1. **`SV_WriteGameState` 的消息类型与编码路径是否已完整追踪？** → **是（CONFIRMED）**。见 `09_A`：`sv_client.c:2298` → `sv_main.c:3939/3946` → `codol_sv_state.c:119/142` → `codol_configstrings.c:288/269` → `sv_client.c:2312` → `sv_snapshot.c:642/688`。
2. **`SV_WriteSnapshotToClient` 的 opcode 是否已确认？** → **服务端侧 CONFIRMED = `0x00`**（`codol_snapshot.c:23`）；**客户端期望值 UNKNOWN**。
3. **`2/3/5/1` 与 `svc_ops_e` 的关系是否查清？** → **是（CONFIRMED）**：两套**独立**编号，**无转换函数**；`svc_ops_e` 在 CODOL 路径**不可达**（仅 `#else` 死分支）。见 `09_B`。
4. **客户端解码入口有哪些候选，最强证据是什么？** → 候选：`CL_PacketEvent@0x00497360`、`CL_Netchan_Decode@0x0049C5E0`、`CL_ParseSnapshot@0x0049D95F`、`CG_TransitionSnapshot@0x0045D180`。**最强证据** = 同构建线（1.1.1.13）+ 反汇编与 `ERRORS.md` 逐条吻合 + `console_mp` 17 次到 `CA_ACTIVE`。
5. **哪些问题已无法通过现有静态材料推进？** → 客户端 **opcode 分派表**、**本仓库↔客户端逐字节互通**、`CL_ParseGamestate`/`CL_GetSnapshot` 的**运行时调用点**（`INSTRUMENTATION_BLOCKED / NOT_OBSERVED`）。
6. **完整载荷抓包是否确实必要？** → **是**（对本仓库服务端↔本客户端互通）；但**认证秘密不必暴露**（见 `09_E`）。
7. **下一步最小工作是什么？** → **N1+N2**：应用 game-server tap diff，跑一次本仓库服务端↔客户端会话，捕获一次完整 gamestate+snapshot（见 F.1/F.2）。