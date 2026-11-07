# 01 — CODOL 复活项目技术演进时间线

> 生成方式：按本地目录、报告文件的 LastWriteTime 与报告内自述日期重建。
> 每条注明证据来源文件。无法确定的事项标注 `UNKNOWN`。

---

## 阶段 0 — 黑盒与平台依赖（2026-09 中旬）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-09-16 | 启动引导报告：EXE 入口、依赖 | `CODOL_BOOTSTRAP_REPORT_2026-09-16.md` |
| 2026-09-18..21 | `_dyn_stage1`、`_ich*_observer` 系列：ICH001–ICH059 共 ~30 轮观测，逐个确认 IIPS/IFS2 的初始化契约 | 根目录 `ICH0*.md` |
| 2026-09 | 结论：主程序拒绝启动是因为读不到 TCLS 命名共享内存 | `CODOL_TCLS_*`、记忆 `codol-tcls-launcher-gate` |

**本阶段产出**：确认"游戏本体通过 TCLS/IIPS/IFS 平台层启动"；
`CODOL_EX001..EX068` 逐层把 IIPS 初始化链拆到函数级。

**未解决（当时遗留至今）**：IIPS 契约的"正规"实现始终未完成；
只能靠冻结的 REF_LOBBY_KIT 复现。→ 见 Issue（启动链不可复现）。

---

## 阶段 1 — 独立启动与大厅（2026-10-05 → 10-09）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-05 | 大厅首次到达；REF_LOBBY_KIT 可用；推送进大厅；大厅 bug 清单 | `HANDOFF_20261005_LOBBY_REACHED.md`、`_PUSH_TO_LOBBY.md`、`_LOBBY_BUGS.md`、`_REFKIT_WORKS.md`、`_TAKEOVER_NO_ADVANCE.md` |
| 2026-10-09 | 运行时阻塞清除 | `CODOL_RUNTIME_BLOCKER_CLEARANCE_20261009.md` |
| 2026-10-09 | ol-mod 审计 | `CODOL_OLMOD_AUDIT_20261009_094312` |

**关键成果**：`REF_LOBBY_KIT` 七件套冻结，成为受保护基线。
**关键问题**：`HANDOFF_20261005_LOBBY_BUGS.md` 列出的问题从未系统收敛；
其中一部分在 2026-10-28 以"准备按钮无反应"形式重新暴露。

---

## 阶段 2 — Demonware 密钥流与协议（2026-10-12 → 10-13）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-12 | `CLIENT-DEMONWARE-CODEC-KEYFLOW-001` 最终裁决；`E21`–`E27` 完成服务端握手对端发现 | `CLIENT-DEMONWARE-CODEC-KEYFLOW-001/05_FINAL_VERDICT.md`、`E2*/` |
| 2026-10-12 | 四个 Keyflow 专项：独立复核 / G3 帧校验 / 计数器边界 / 长度兼容 | `CODOL-KEYFLOW-*/` |
| 2026-10-13 | 任务 005–050 批次：战斗服协议边界、OOB 状态机、快照/传输缺口、客户端接收路径 | `CODOL-BATTLE-*`、`CODOL-TARGET-*` |

**重要口径分歧（本审计确认）**：`E26_PROTOCOL_CONFLICTS_AND_BLOCKERS.md`
自述存在协议冲突；`CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001/CODOL_G3_STATUS_RECONCILIATION_001.md`
是一份"状态对账"，说明同一批结论在不同报告里被不同状态描述过。

---

## 阶段 3 — 战斗服立项与首次突破（2026-10-13 → 10-16）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-13 | `CODOL-BATTLE-SERVER-IMPLEMENTATION-FOUNDATION-047` 建立 C# 基础工程 | 该目录 `src/` |
| 2026-10-13 | `CODOL-Combat-Server-v0.1` INTEGRATION-004 | `CODOL-Combat-Server-v0.1/INTEGRATION-004_REPORT.md` |
| 2026-10-14 | **3.19 突破报告**：首次客户端 ↔ 自研战斗服链路 | `COMBAT_SERVER_3.19_BREAKTHROUGH_AND_PROGRESS_REPORT.md` |
| 2026-10-15 | firingrange 起来 | `HANDOFF_20261015_FIRINGRANGE_BRINGUP.md` |
| 2026-10-16 | 消费链 / 入口转储 | `HANDOFF_20261016_CONSUMER_CHAIN.md`、`CONSUMER_CHAIN_FINDINGS_20261016.md`、`ENTRY_DUMP_20261016_FINDINGS.md` |

---

## 阶段 4 — 原生对局与"黄金"基线（2026-10-17 → 10-21）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-17 | 进度总账 | `PROGRESS_20261017.md` |
| 2026-10-19 | 原生对局交接；`CODOL_VERIFIED_GOLDEN_20261019` 建立 | `HANDOFF_20261019_NATIVE_MATCH.md`、`TAKEOVER_STATUS_20261019.md` |
| 2026-10-20 | 独立审计批次：IW4X / CoD4X / C 服全栈 / 世界碰撞 | `CODOL_ANALYSIS_20261020/*.md` |
| 2026-10-21 | C 战斗服 `CODOL_SERVER_319_20261021` 成型 | 该目录 |

**审计注记**：`CODOL_ANALYSIS_20261020/THIRD_ROUND_*` 已做过一次"阻断项状态审计"，
其中 `THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md` 是本次审计的重要前置。

---

## 阶段 5 — 对局内完成度与快照协议（2026-10-22 → 10-24）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-22 | `HANDOFF_20261022_PAUSE.md` 暂停；`CODEC_SPEC`、`BITORDER_6701D0` | `CODOL_SERVER_319_20261021/docs/` |
| 2026-10-23 | `INMATCH_COMPLETENESS_GAP_MATRIX`（域级 DONE/PARTIAL/TODO） | 同目录 |
| 2026-10-23 | 动态首试失败（10 秒退出，未加载 iips.dll/ifs2.dll） | 同上 §"动态首试" |
| 2026-10-24 | 快照字段级对照；**发现 11 字段错用 XOR、idx61 恒 2047** | `docs/SNAPSHOT_FIELD_DIFF_20261024.md` |
| 2026-10-24 | 实体段首次实机：收得下但看不见 | `HANDOFF_20261025_BINARY_BISECT.md` §17 |

---

## 阶段 6 — 二分定位与"能进图"回归（2026-10-25）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-25 | 三二进制对照：**10-23 那批源码本身让客户端进不了图** | `HANDOFF_20261025_BINARY_BISECT.md` §1 |
| 2026-10-25 | **根因 = 索引 run 编码必须 4 位一组 / 步长 15**，改回即进图 | 同上 §8 |
| 2026-10-25 | 实机验收：messageAck 0→4272、19022 条 usercmd、武器号 1156 | 同上 §8.1 |
| 2026-10-25 | **反例**：按参照逐字节重写编码器 → 客户端反而卡住（已回退） | 同上 §15 |
| 2026-10-25 | `codol_battle_service_bind_world` 一行接线，实体层激活 | 同上 §16 |
| 2026-10-25 | 出生点三种坐标 × 两种频率全部无效（服务端推不动客户端位置） | 同上 §13 |

---

## 阶段 7 — 剧情模式开局卡点（2026-10-26 → 10-27）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-26 | PvE"战斗开始"卡点实机：客户端从不连 28960 | `docs/PVE_STARTGAME_BLOCKER_20261026.md` |
| 2026-10-26 | 71/3 的 CreateRoom 被证明是 **TLog 统计**，不是开局请求 | 同上 |
| 2026-10-26 | clipmap 提取：coop 层只有 27 个垂直平面、零地板 | `docs/CLIPMAP_EXTRACTION_20261026.md`、`MP_FIRINGRANGE_CLIPMAP_20261026.md` |
| 2026-10-27 | **本体 6 秒必崩根因 = `iips.ini` 的 `enable_iips=0`**，改 1 后进大厅 | `docs/PVE_BATTLESTART_STATUS_20261027_1220.md` §0 |
| 2026-10-27 | 闸门 B = dvar"3291" 派生，恒 0；且**与 0x63C5E0 属不同类** | `docs/GATE_B_INIT_PATH_20261027.md` |
| 2026-10-27 | **A/B：`11/13 createRoom` 的 memberCount 0→1 ⇒ `dwRoomMatchUber` 首次出现** | `docs/AB_MEMBERCOUNT_RESULT_20261027.md` |
| 2026-10-27 | 修复转正到正式 kit 并复跑验证 | `docs/FIX_MEMBERCOUNT_APPLIED_20261027.md` |
| 2026-10-27 | 状态机停在状态 1；计时器从未启动 | 同上 |

---

## 阶段 8 — 房间协议与运行时取证封死（2026-10-28）

| 日期 | 事件 | 证据 |
|---|---|---|
| 2026-10-28 | 房间协议三层结构解出（209 条样本，`declared == innerLen-4` 100%） | `docs/ROOM_PROTOCOL_COMPLETE_20261028.md` |
| 2026-10-28 | 上下行格式不同：上行走容器、下行走位流 | `docs/ROOM_DIRECTION_SPLIT_20261028.md` |
| 2026-10-28 | type 0x02 = `dwRoomMessageText`（不是通用分发） | `docs/TYPE02_IS_TEXT_20261028.md` |
| 2026-10-28 | 下行位流重编后**首次出现可观测行为差异**（任务数 85→71） | `docs/DOWNLINK_STREAM_RUN_20261028.md` |
| 2026-10-28 | **ACE 内核驱动封死活进程读取**：t+0.01s 起 RPM err=5，ALL_ACCESS 也一样 | `docs/ACE_BLOCKS_EVERYTHING_20261028.md` |
| 2026-10-28 | `ui_mp.ff` 加密（熵 7.95~8.00），Flash 资源不可达 | `docs/UI_FF_ENCRYPTED_20261028.md` |
| 2026-10-28 | 准备按钮：点击不产生任何上行；`AS_*` 类无 COL / 零引用 | `docs/READY_BUTTON_NO_*_20261028.md`、`AS_CLASSES_INVENTORY_20261028.md` |
| 2026-10-28 | 战斗服零收包根因候选：`mmstart` 无 map / `102/7` 回全 0 / StartGame 推送 | `docs/BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md`、`BATTLE_CONNECT_DIVERGENCE_20261028.md` |

---

## 阶段 9 — 现状（2026-10-29）

| 时间 | 事件 | 证据 |
|---|---|---|
| 2026-10-29 | `RE_FULL_20261029`：EXE 全量 RTTI，163 个 `AS_*` 类 | `run_codol_001/runs/RE_FULL_20261029/rtti_full.md` |
| 2026-10-29 00:21 | 最新一轮 `ONCE_20261029_002046`：findSessions→mp_raid、createRoom 成功、mmstart 选图 `?`、战斗服仍零收包 | 该 run 的 `kit/lobby_srv.log`、`kit/_battle_out.txt` |

**★ 本审计直接读取该轮产物得到的两条新事实**：
1. `_battle_out.txt` 只有 7 行初始化，**没有任何 RX**（与 10-26 成功轮对比）。
2. `world "mp_raid" assets loaded (29 clip volumes)` —— 即使 `--map mp_raid`，
   加载的仍是 coop_train 的 29 个碰撞体（见 S-24）。

---

## 未被任何报告覆盖的时间段

- 2026-09-22 → 2026-10-04：本地无报告文件（`_ich*` 目录止于 09-21，`HANDOFF` 始于 10-05）。`UNKNOWN`。
- 2026-10-06 → 10-08：仅有 `codol_crypto.py` 内嵌注释（2026-10-07 firingrange 抓包）。
- 2026-10-11 → 10-12：`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011` 之外无记录。
