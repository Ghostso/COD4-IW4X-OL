# 00 — 轮次报告 / ROUND REPORT — CODOL 最终版战斗服务器：权威实体表 001

**任务**：`CODOL-BATTLE-SERVER-ENTITY-001` — 在 `CODOL-Combat-Server-v0.1` 内建立 `GameWorld` 的权威 `slot → PlayerState` 实体表，消除每帧从 `_logic.Sessions` 重建玩家列表导致的实体索引不稳定。
**目标版本**：CODOL 3.9.9.7 / 2.6.9.7（本地逆向事实源不变；本轮未引入任何未验证的 2697 字段）
**日期**：2026-10-13（Asia/Shanghai）
**工程基准**：`CODOL-Combat-Server-v0.1`（未另起工程）
**冻结基线**：未触碰（`GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、`_e1_regression/ol-mod-olfinal`、`tests/golden_*.hex`、`config/firingrange-gamestate.bin` 原文全未改；原始游戏文件未改）

---

## 0. 本地资料检查（强制项）

本轮开始前，在规定目录 `D:\BaiduNetdiskDownload\使命召唤OL` 内实际检查了与任务相关的资料：

| 资料 | 用途 |
|---|---|
| `CODOL-Combat-Server-v0.1/src/**`（GameWorld / ClientLogic / ClientSession / PlayerState / SelfTest） | 确认本地工程实际状态（未假设与历史报告一致：本轮核对发现 `ClientLogic`/`ServerHost` 已带上一轮的实体化改动，遂按实际状态推进） |
| `14_SERVER_KNOWLEDGE_ATLAS_001/03_SERVER_LIFECYCLE.md:78-86` | **设计依据**：`SV_DirectConnect → 分配 client_t：CS_FREE → CS_CONNECTED → CS_PRIMED → CS_ACTIVE`（`sv_client.c:750/2160/2272/1597/1631`，OLD/1113 VERIFIED，2697 同族 STATIC-INFERENCE）；`CS_ACTIVE → SV_SendClientSnapshot`（`sv_snapshot.c:759`） |
| `14_SERVER_KNOWLEDGE_ATLAS_001/08_ENTITY_AND_BUSINESS_LAYER.md` §1 | **设计依据**：client_t 状态机；实体状态在 `sv_snapshot.c` + `codol\snapshot\*`；2697 侧 `_WriteEntities`/`_WriteEntityPayload`；实体编号＝位流索引 |
| `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/02_BATTLE_ENTRY_AND_INITIALIZATION.md` | 步骤 5（身份 CONFIRMED@3.3.3.3）/ 步骤 8（断线重连语义 UNKNOWN/BQ-09）；本轮沿用其身份门控结论 |
| `CODOL-COMBAT-LIFECYCLE-001`、`CODOL-COMBAT-RECONNECT-STATE-001` | 上一轮已交付的生命周期与重连状态管理（本轮在其之上做实体化） |

**未**把其他版本（CoD4x/IW4x/1.1.1.13/3.3.3.3）的字段或规则当作 2697 已确认结论使用。

---

## 1. 实际修改了哪些代码

| 文件 | 变更 |
|---|---|
| `src/Engine/GameWorld.cs` | `PlayerState` 新增 `Slot`、`EntityId`；新增**权威实体表** `_entities` 及 `EntityCount/Entities/AllocSlot/Spawn/DespawnPlayer(slot,entityId)/DespawnPlayer(p)/TryGetEntity/GetEntity/HasEntity/IsCurrent/ClearEntities`；`Frame` 签名由 `Frame(double, IList<PlayerState>)` 改为 **`Frame(double)`**（只遍历实体表）；**删除** `NewPlayer`/`OnPlayerRemoved` 这两个脱离实体表的入口 |
| `src/Engine/ClientLogic.cs` | 建会话改为 `_world.AllocSlot()` + `_world.Spawn(slot)`；满载判定＝无空闲槽位；`DropSession` 改为**先捕获可恢复状态、再按 (slot, entityId) 精确摘除**；`PumpSnapshot` 增加**在册校验**；`AllocSlot()` 降级为转发；新增绑定不变式检查 `CheckConsistency`；`Shutdown` 追加 `_world.ClearEntities()` |
| `src/Engine/ServerHost.cs` | 主循环由"每帧 `foreach (_logic.Sessions) players.Add(s.Player)` → `Frame(dt, players)`"改为 **`_world.Frame(dt)`** |
| `src/SelfTest.cs` | `Harness.Tick` 改走 `Host.World.Frame(1.0/128.0)`；新增**第 11 节「权威实体表」27 项断言**并注册 |

源文件数保持 **23**（无新增文件）。源码指纹：上一轮 `99e98dc8…` → 本轮 `b62204a6…`。

---

## 2. 权威实体表设计（含更新时序）

### 2.1 单一权威来源
`GameWorld._entities : Dictionary<int, PlayerState>` 是玩家实体的**唯一**来源。`PlayerState.Slot` = 表键；`PlayerState.EntityId` = 单调递增的世代号（第 1、2、3…）。

### 2.2 更新时序（与本地 client_t 生命周期对齐）

| 事件 | 旧实现（问题） | 本轮实现 |
|---|---|---|
| **实体创建** | `NewPlayer(slot)` 返回值**没有**槽位字段，且槽位来自 `ClientLogic.AllocSlot()`（按会话集合算） | `_world.AllocSlot()`（按实体表算）→ `_world.Spawn(slot)`：写入 `Slot`/`EntityId` 并登记；槽位越界或已占用**抛异常**（绝不静默覆盖） |
| **会话绑定** | 会话持有实体引用，但实体不在任何表中 | 会话持有的实体 == 表在该槽位的实体（`CheckConsistency` 强制断言） |
| **实体移除** | `OnPlayerRemoved(p)`：只置 `Connected=false`，**不从任何表移除**（每帧靠过滤） | `DespawnPlayer(slot, entityId)`：先从表移除，再清零输入/速度；`PlayersRemoved++` |
| **槽位复用** | `AllocSlot()` 按会话集合找空位；移除的实体对象仍存活 | 表为空才算空位；复用后表里是新实体（新 `EntityId`） |
| **超时** | `SweepTimeouts → DropSession → OnPlayerRemoved` | `SweepTimeouts → DropSession` → 捕获记录 → 精确摘除 |
| **重连** | 恢复写入新 `PlayerState`（值恢复，对象不共享） | 不变：`PlayerRestoreRecord.ApplyTo` 只写玩法字段到**新**实体 |
| **停机** | `Shutdown` 逐个 drop | 逐个 drop + `ClearEntities()` 兜底，保证不跨停机残留 |

### 2.3 帧推进
`Frame(dt)` 按槽位 0..MaxClients-1 依次查表推进（确定性顺序、无每帧列表分配）。`ServerHost.Run` 不再构造玩家列表 —— 帧推进、快照、清理三条路径现在读的是同一张表。

---

## 3. 防错配 / 防幽灵机制（对应任务 4、5）

1. **世代号守卫**：`DespawnPlayer(slot, entityId)` 先比对表内实体的 `EntityId`；不符则**什么都不做并返回 false**。因此"持有旧实体引用的旧会话"永远无法误删复用同一槽位的新实体（测试 **B4**）。
2. **幂等**：对已移除的 (slot, entityId) 再摘除返回 false，实体数不变（测试 **B2**）。
3. **无幽灵模拟**：帧推进只遍历表，被移除实体不再被积分（测试 **C2**）。
4. **无错误快照引用**：`PumpSnapshot` 增加 `_world.IsCurrent(s.Player)` 校验；绑定失效时**拒绝下发**而不是用错误实体编码（测试 **C4**）。
5. **无重复实体**：`Spawn` 对已占用槽位抛异常，拒绝静默覆盖（源头杜绝重复）。
6. **无残留**：`Shutdown` 兜底 `ClearEntities()`（测试 **F1**）。
7. **不变式可断言**：`ClientLogic.CheckConsistency(out why)` 同时校验①每会话实体即其槽位占有者 ②`Slot` 一致 + `Connected` ③实体与会话**一一对应**（无幽灵/无重复/无残留）+ 会话数 == 实体数。测试 A5/B5/D3/E4/F2/G4 在多条路径后调用它。
8. **身份门控原则未变**：重连仍只按 `\xuid\` 恢复玩法字段，绝不按 ip:port；无 `\xuid\` 或策略 `Off` 即不建立身份连续性（测试 E 组沿用上一轮结论）。

---

## 4. 新增自动化测试（第 11 节，27 项，全部通过）

| 组 | 覆盖 | 项 |
|---|---|---|
| **A** | 3 会话 == 3 实体；槽位按最小空闲 0/1/2；会话实体 == 表实体；`EntityId` 唯一且递增；不变式 | 5 |
| **B** | 移除后无残留且 `Connected=false`；重复摘除幂等；槽位复用得到新对象/新世代；**旧世代引用无法误删新实体**；复用后不变式 | 5 |
| **C** | 在册实体被推进；已移除实体不再被推进（无幽灵）；槽位归属正确；**绑定失效时不下发快照** | 4 |
| **D** | 超时后会话与实体同时清空；不变式 | 3 |
| **E** | 重连不复用旧实体对象/世代；玩法值恢复到新实体；新实体在册且会话数==实体数==1；不变式 | 4 |
| **F** | 停机后会话与实体均为 0；不变式 | 2 |
| **G** | 满员拒收不产生实体；超时后全部回收；混合序列后会话数==实体数且不超 `sv_maxclients`；不变式 | 4 |

**原有用例全部保持通过**：第 1–10 节 177 项未变（含 §9 生命周期 14 项、§10 重连状态 40 项）。

---

## 5. 实际执行的构建与测试

| # | 项目 | 命令 | 结果 |
|---|---|---|---|
| B-1 | 可重复构建 (release) | `powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1` | **BUILD OK**，`sources: 23`（1 条既有告警 `ClientCommandReader.cs(213) CS0675`） |
| T-1 | 离线自测（全 11 节） | `build/bin/CODOLCombatServer.exe --selftest` | **通过 204 项，失败 0 项，exit=0**（177 旧 + 27 新） |
| T-2 | 来源指纹 | `--fingerprint` | `b62204a6285b9fae8dc0741501ee5a62a7b36fbc65313af3e745338578fa0000` == `BUILD_MANIFEST.txt` 的 `source_sha256` |
| R-1 | 运行时冒烟 | `--run +set port 28970`（约 33 秒） | **成功**：监听 `127.0.0.1:28970` → `初始化完成，进入主循环（128 Hz）` → `STAT … 会话=0 tick=998`；无 stderr、无异常 |

说明（如实记录）：`tick=998` 对应约 33 秒墙钟，低于 128 Hz × 33 s ≈ 4200 的期望值，原因是主循环 `Thread.Sleep(1)` 的调度粒度（上一轮已如实记录同一现象，非本轮引入）。

**NOT_RUN（明确标注，未用离线测试替代）**
- `NOT_RUN` — 真实 CODOL 客户端端到端兼容：本服仍从未被真实客户端连接（`收包=0`）。本轮全部结论均为**服务端自证**，**不构成**任何"客户端可互通"主张。
- `NOT_RUN` — 2697 客户端侧 `0x02/0x04/0x06` 消费链、snapshot 帧边界/delta 基准（T-01/T-02/T-03/T-04）、2697 战斗通道真实字节（T-05）。
- `NOT_RUN` — 交互式 Ctrl+C 停机（本机非控制台会话无法投递控制事件；`Shutdown()` 由 §11/F 与 §10/J4 直接覆盖）。
- `NOT_RUN` — ol-mod（L1）插件线与 booking/DedicatedControl 接线。

---

## 6. 未解决的具体代码问题（如实列出）

| # | 问题 | 现状与影响 |
|---|---|---|
| U-1 | `DropSession` 若 `DespawnPlayer` 返回 false（世代不符），会话已被移除而实体会**残留** | 当前不可达（实体只由 `Spawn`/`DespawnPlayer` 改变，且 `DespawnPlayer` 在同线程内不会失败），但这不是被证明的不变式。设计上**故意**选择"宁可拒绝删除也不误删新实体"；`CheckConsistency` 可检出、`Shutdown` 的 `ClearEntities()` 可兜底。**未加自动修复** |
| U-2 | `GameWorld` **无锁**，假定单线程驱动 | 当前成立（`ServerHost.Run` 单线程：收包→`Frame`→`Update`）。若将来把网络收发与模拟拆到不同线程，必须先加锁/消息队列，否则实体表与快照会竞态 |
| U-3 | 快照/游戏状态下发仍直接读 `s.Player`，而非每次从表查 | 已用绑定不变式 + `IsCurrent` 守卫保证正确；`PumpGameState` 不读玩家故未加守卫 |
| U-4 | `PlayerState` 仍无血量/武器世界模型/伤害状态 | v0.1 战斗逻辑边界（无 BSP/Clip、无 `G_Damage`）。实体表只承载已有字段 |
| U-5 | `MaxClients` 不支持热改 | 表容量在 `Spawn`/`AllocSlot`/`Frame` 中由 `_cfg.MaxClients` 现算，但运行期改配置不会重建表；需重启 |
| U-6 | 快照 delta 基准 / 帧边界仍是 UNKNOWN | 需要 2697 真实字节证据（T-04/T-05）；实体表只是提供了稳定的"实体编号＝槽位"前提 |
| U-7 | 客户端 `0x02` 分派未定位 | 客户端消费链 BLOCKED（T-03/T-10），与实体表无关但仍是端到端互通的结构性阻塞 |

---

## 7. 下一项可以直接执行的代码修改

1. **实体表接入快照实体枚举**（本工程）：`PumpSnapshot` 目前只编码"本会话玩家"。改为遍历 `GameWorld.Entities` 生成他方实体条目，使快照引用稳定实体编号（为 M6 世界同步铺路）。
2. **`--run --max-seconds N`**（本工程，约 10 行）：把本轮 R-1 的人工 kill 变成可自动化、可断言的"启动→清理"用例。
3. **booking/DedicatedControl 最小接线**（副本工程，T-07）：源码已在 `_e1_regression/ol-mod-olfinal/src/backend`，在本服侧实现 booking 六步离线回归并消费 `SessionExporter` 的端点/密钥（不动 Golden）。

---

## 8. 哈希

- 改动文件与产物 SHA-256：见 `CHANGED_FILES.tsv`。
- 构建/自测原始日志：`V0_4_BUILD_AND_TEST_LOG.txt`；运行时冒烟：`V0_4_RUN_SMOKE_28970.txt`。
- 本目录交付物哈希：见 `SHA256SUMS.txt`。
