# 00 — 轮次报告 / ROUND REPORT — CODOL 最终版战斗服务器：玩家状态与战斗世界（游戏逻辑）003

**任务**：`CODOL-BATTLE-SERVER-GAMEPLAY-003` — 检查正式服务器中玩家状态与战斗世界的实际实现，把"服务器该负责任么"变成**逐项有证据、可离线复算**的代码与测试
**目标版本**：CODOL 3.9.9.7 / 2.6.9.7（本地逆向事实源不变；本轮未引入任何未验证版本字段）
**日期**：2026-10-13（Asia/Shanghai）
**本轮性质**：**正式服务器代码实现 + 构建 + 自动化测试**（非研究文档）
**工程基准**：`CODOL-Combat-Server-v0.1`（可 `csc` 构建的最小战斗服底座，唯一工程主线）
**上游依据**：`CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001`（M3/M4/M5；G-10/G-11/G-12/G-18）、`CODOL-COMBAT-LIFECYCLE-001`（G-23）、`CODOL-COMBAT-RECONNECT-STATE-001`
**主要证据源**：`REF_LOBBY_KIT/battle_server.py`（唯一有真实大厅→战斗握手抓包的参考实现）+ `CODOL-Combat-Server-v0.1/src/Codol/MotionSnapshot.cs`（位级快照，已与 Python 基准逐字节对齐）
**冻结基线**：未触碰任何冻结物（`GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、`_e1_regression/ol-mod-olfinal`、`tests/golden_*.hex` 原文全未修改）

---

## 0. 本轮一句话

把"战斗世界"里**服务器该做的**从模糊描述收窄成**有实录依据、且能离线复算**的实现与测试：

- **服务端权威**（本轮实现/加固并测试）：玩家实体生命周期、usercmd 输入 → 权威水平运动学、武器状态机、战斗事件环形缓冲、玩家退出清理。
- **客户端权威**（不实现）：真实碰撞/可见性（BSP/Clip）、命中检测的几何与射线、第一人称表现。
- **未证部分**（明确阻塞，本轮**不实现、不伪造**）：水平碰撞、命中判定、伤害公式、死亡/复活规则（见 §6）。

> 纪律（承接审计 §2）：**"服务端能算" ≠ "客户端能读"**；**"字段形状一致" ≠ "opcode 兼容"**；**"离线通过" ≠ "客户端互通"**。本轮全部结论均为**服务端自证**，不构成"客户端可互通"主张。

---

## 1. 服务器 / 客户端责任划分（依据本地证据）

| 模块 | 归属 | 本地依据 | 本轮动作 |
|---|---|---|---|
| 玩家实体生命周期（连接→在建实体→退出摘除） | **服务端** | `GameWorld._entities`（唯一权威源）+ `ClientLogic.DropSession` | 已实现；新增/保留回归断言 |
| usercmd 收包与解码（14B 实录） | 服务端 | `ClientCommandReader.ReadInput` + `CodolClientReplay.RealUserCmd14` | 已实现；回归保持通过 |
| 权威水平运动学（方向/速度/对角归一） | **服务端** | `battle_server.py:679-699`（实录换算） | **重写为实录等价（默认）**；新增 7 项断言 |
| 竖直运动（重力/跳跃） | **客户端**（实录不模拟） | `battle_server.py:696-699` **只改 pos_x/pos_y，从不改 pos_z** | **默认关闭**；非实录积分改为显式实验开关 |
| 武器状态机（开火/射速/半自动/换弹/背包装备） | 服务端 | `battle_server.py:954-1055`（实录参数） | 已实现；新增 8 项断言 |
| 战斗事件（开枪 0x24 / 换弹 0x19 / 空仓换弹 0x1A） | 服务端 | `battle_server.py:990-1051` + 快照 idx21..24 | 已实现；新增环形缓冲断言 |
| 玩家退出清理（槽位回收/实体摘除/世代防误删） | 服务端 | `GameWorld.DespawnPlayer` + `ClientLogic.DropSession` | 已实现；新增下线不再被推进断言 |
| 水平碰撞 / 视线（BSP / Clip） | 服务端（数据缺失） | 见 §6 BLK-COLLISION | **阻塞**，未实现 |
| 命中判定（射线/命中盒） | 服务端（数据缺失） | 见 §6 BLK-HITSCAN | **阻塞**，未实现 |
| 伤害（`G_Damage`）/ 死亡 / 复活 | 服务端（公式与规则缺失） | 见 §6 BLK-DAMAGE / BLK-DEATH | **阻塞**，未实现 |

---

## 2. 实际修改了哪些代码

| 文件 | 变更 | 类型 |
|---|---|---|
| `CODOL-Combat-Server-v0.1/src/Engine/ServerConfig.cs` | 新增配置 `movement_model`(默认 `captured`) 与 `vertical_sim`(默认 `0`) 及其解析；新增只读属性 `CapturedMovement`；恢复/保留 `Spawn/WalkSpeed/Gravity/JumpVelocity` | 配置 |
| `CODOL-Combat-Server-v0.1/src/Engine/GameWorld.cs` | 重写 `IntegratePlayer`：默认走**实录水平运动学**（瞬时速度、无惯性、对角归一）；旧一阶逼近改为 `movement_model=smooth` 实验路径；重力/跳跃抽到 `IntegrateVertical` 且**仅** `vertical_sim=on` 时调用；更新类头能力边界注释 | **核心功能** |
| `CODOL-Combat-Server-v0.1/src/SelfTest.cs` | 修正实体表 C1（权威推进改为真入力下才发生）；新增第 12 节"战斗世界"（移动/竖直/武器/事件/生命周期，共 24 项断言）；注册分节 | **测试** |
| `CODOL-Combat-Server-v0.1/config/combat_server.cfg` | 文档化 `movement_model` / `vertical_sim` 两个新键及其实录/非实录含义 | 配置 |

> 变更前基线：源码指纹 `b62204a6…fa0000`（23 源文件，2026-10-13 首次构建）。
> 变更后：源码指纹 `d042d83c…6198698`，未新增/删除任何源文件（仍 23 个）。
> 说明：本报告 `§2` 表格中 "23 源文件" = `src/**.cs` 全量；本轮只改其中 3 个 `.cs` + 1 个 `.cfg`，无新增源文件。

---

## 3. 新增/修复了哪些服务器功能（逐项，带证据）

1. **水平运动学对齐实录（默认路径）**。旧实现用 `accel=10.0` 的一阶逼近（源码自注"工程取值，非引擎常数"）——这是**没有实录依据**的行为，且与参考实现不一致。参考实现（`battle_server.py:679-699`）每输入直接 `vel=(cos,sin 组合)*190*norm`、`pos+=vel*dt`，**没有**加速/摩擦项。本轮把默认改为该瞬时运动学：`move=0` 时速度立即为 0（无惯性漂移），对角（前后+左右）归一到 `1/√2` 使速度大小恒为 `WalkSpeed`。
2. **竖直模拟与实录解耦**。参考实现只改 `pos_x`/`pos_y`，**从不**写 `pos_z`。旧的 C# 默认对每个实体做重力积分并用 `Spawn[2]` 兜底——其中的 `gravity=800`/`jump_velocity=270` 是**非实录常数**。本轮改为 `vertical_sim=off`（默认，与实录一致：不动 Z/VZ），只有显式开启才走非实录积分。
3. **旧模型降级为显式实验开关**（`movement_model=smooth`）。保留可回退路径，但默认禁用、且在配置/代码里明确标注"非实录常数"。
4. **权威实体表语义保持**：本轮未改实体生命周期实现（`Spawn`/`DespawnPlayer`/`Frame`/`IsCurrent`），只新增回归断言证明"下线实体不再被 `Frame` 推进、不再进快照"。
5. **武器状态机与战斗事件**：`Equipment.Step`/`AddEvent` 的实录参数（1156/1157/1158 的弹匣/射速/换弹/ADS、事件 0x24/0x19/0x1A、4 槽环形缓冲）本轮**首次**被系统化为可离线复算的断言（此前只有背包切换 1 条）。

---

## 4. 实际执行的构建与测试

| # | 项目 | 命令 | 结果 |
|---|---|---|---|
| B-1 | 可重复构建 (release) | `powershell -NoProfile -ExecutionPolicy Bypass -File build/build.ps1` | **BUILD OK**（`sources: 23`，`/platform:x86 /warn:4`；1 条既有告警 `ClientCommandReader.cs(213) CS0675`） |
| T-1 | 离线自测（全 12 节） | `build/bin/CODOLCombatServer.exe --selftest` | **通过 228 项，失败 0 项，exit=0**（基线 204 项 → 本轮 +24） |
| T-2 | 来源指纹 | `--fingerprint`（由 `BUILD_MANIFEST.txt` 复核） | `SOURCE_SHA256=d042d83c1af9344014388f67ea3531021d4d61a2243c20b93ed5aef286198698 == manifest.source_sha256`（证明 exe 由当前源码编译） |
| R-1 | 运行时冒烟 (`--run`) | 后台 `--run +set port 28966 +set log_file ""`，约 4s | **成功**：`已监听 UDP 127.0.0.1:28966` → `初始化完成，进入主循环（128 Hz）`；**无**"未知配置项已忽略"告警（证明 `movement_model`/`vertical_sim` 已被识别） |

**NOT_RUN（明确标注，未以离线测试替代）**
- `NOT_RUN` — **真实 CODOL 客户端端到端兼容**：本服仍从未被真实客户端连接（本工作区无同 SHA-256 客户端运行时镜像）。
- `NOT_RUN` — 交互式 Ctrl+C 停机（本机非控制台会话无法投递控制事件）。
- `NOT_RUN` — 移动在"客户端真实 tick 节奏"下的观感/延迟（需实机）。

原始日志：`V0_4_BUILD_LOG.txt`、`V0_4_SELFTEST_FULL.txt`、`V0_4_RUN_SMOKE_28966.txt`。

---

## 5. 新增自动化测试（第 12 节，共 24 项，全部通过）

| 组 | 覆盖 | 项数 |
|---|---|---|
| **A** | 实录水平运动学：yaw 0/90/180/270 的位移方向与大小（各 190/秒）、对角归一（大小恒 190）、`move=0` 立即停（无惯性）、`smooth` 为非实录 opt-in | 7 |
| **B** | 竖直模型：默认 `off` 时 JUMP 不改 Z/VZ；`on` 时 JUMP 离地后落回出生平面 | 2 |
| **C** | 武器状态机：开火耗弹+state 6+事件 0x24、射速门控、冷却后可再开火、半自动(1158)按住只发一发/松开可再发、换弹 state 8 + WeaponDelay 后补弹扣备弹、空仓自动换弹、custom2 实录装备表、换槽重置计时 | 8 |
| **D** | 战斗事件环形缓冲：4 槽 idx=seq&3 覆盖与 EventSequence 递增 | 1 |
| **E** | 生命周期：在册实体被 `Frame` 推进、下线清零并 `Connected=false`、下线实体不再被推进 | 3 |

**原有第 1–11 节 204 项全部保持通过**（其中实体表 C1 因默认运动学改为"瞬时"而同步修正：权威推进改由真入力 `Move=1` 驱动，语义不变）。

---

## 6. 具体阻塞（代码级定位，本轮不实现、不伪造）

| # | 阻塞 | 精确位置 / 缺失物 | 为什么不能凭经验编造 |
|---|---|---|---|
| **BLK-COLLISION** | 水平碰撞、视线 | `GameWorld.Initialize`→`RegisterAssetFile` 只把 `.ff` 文件名**登记**进 `_maps`，**从不解析** BSP/Clip 几何；`GameWorld` 无 AABB/凸体/射线；`IntegrateVertical` 只能以 `_cfg.Spawn[2]` 兜底（已注释为"占位"）。 | 碰撞规则（Brush/Clip 语义、玩家包围盒尺寸）在本地文档中标 UNKNOWN；没有可复算的几何就没有可验证的规则。 |
| **BLK-HITSCAN** | 命中判定（射线/命中盒） | `Equipment.Step` 只产出**本地**武器事件（0x24 开火），不产生任何弹道/射线；工程内无 `bullet_process`/`client_impacts` 等价物，也无骨骼/命中盒数据。 | 命中盒与弹道需要引擎战斗实体表；猜测的射线会让"命中"变成错觉。 |
| **BLK-DAMAGE** | 伤害公式（`G_Damage`） | 工程无伤害函数、无伤害表、无护甲/命中部位字段；`battle_server.py` **也没有**伤害实现（它同样只有握手+运动+武器状态）。参考的 ol-mod `g_damage` 属 **3.3.3.3** 且自述缺 9 个依赖 —— **不可**当 2697 实现。 | 审计 `05_SERVER_IMPLEMENTATION_GAP.md` G-11 记为需"补 9 依赖"；规则未闭合。 |
| **BLK-DEATH-RESPAWN** | 死亡 / 复活 | `PlayerState` **无** Health/Alive 字段；工程无 `player_die`/respawn 状态机；复活计时与模式（SD/FFA/Factory）规则未指定（审计 B-7）。 | 没有伤害就没有死亡触发，没有模式裁定就没有复活语义。 |
| **BLK-PERINPUT-TIMING** | 运动应用时机 | `ClientLogic.HandleNetchan` 对武器/瞄准用 usercmd 的 `elapsed`，而水平位移在 `GameWorld.Frame` 按**服务端 tick** 用最近输入积分（参考实现是**按输入**积分）。稳态输入下总位移一致，差异只在输入间隔内。 | 这是"服务端 tick 驱动 vs 输入驱动"的工程选择；本轮**未**用未证假设替换，仅如实记录。 |

---

## 7. 哈希

- 改动文件与产物 SHA-256：见 `CHANGED_FILES.tsv`。
- 构建/自测/冒烟原始日志：`V0_4_BUILD_LOG.txt`、`V0_4_SELFTEST_FULL.txt`、`V0_4_RUN_SMOKE_28966.txt`。
- 本目录交付物哈希：见 `SHA256SUMS.txt`。
