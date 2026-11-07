# 00 — CODOL 大厅全链路取证 · 入口

> 任务 `CODOL-LOBBY-FULL-LIFECYCLE-FORENSICS-055` · 2026-10-29
> 范围：**大厅业务流程**。不涉及战斗服内部（GameState/Snapshot/移动/碰撞/武器/伤害/实体）。
> 方法：静态分析 + 历史证据整理。**未启动客户端、未改任何文件。**

---

## 一、一句话结论

**大厅的 bootstrap 段 56/56 完全正常；断裂全部发生在 `mmstart` 之后，
以及房间 UI 内部。唯一有成功证据的路径是 PvE 剧情入口。**

---

## 二、最重要的三个数字

| 数字 | 含义 |
|---|---|
| **56/56** | 有解密记录的 run 里，bootstrap **前 20 个请求的集合**完全相同 |
| **8 / 32** | 走到战斗连接的 run 数 / 进入房间路径的 run 数（房间路径 **0 成功**） |
| **0 包** | E1 抓包在 `127.0.0.1:28960` 上收到的数据包数 |

---

## 三、真实状态机（详见 `02_`）

```
S1 bootstrap（35 请求，恒定）
  → S2 档案确认
  → S3 21/5 findSessions（playlist=10 或 50）
  → S4 分叉
       ├─ A  PvE: mmbook → mmstart(map)        → 连战斗服 ✅（10-26 八轮）
       └─ B  房间: createRoom → setRoomData×N
               ├─ B1: (→ mmbook → mmstart(playlist37)) → ❌ 从未连上
               └─ B2: 停在房间                        → ❌
```

---

## 四、八个断裂点（详见 `14_`）

| BP | 阶段 | 类型 |
|---|---|---|
| BP-01 | 准备按钮 | 功能未实现 |
| BP-02 | 房间下行解析 | 流程阻塞 |
| BP-03 | 成员同步 | 功能未实现 |
| BP-04 | MyEventHandler 注册 | UNKNOWN |
| BP-05 | 自动开局状态机 | 流程阻塞（PvE 可绕过） |
| **BP-06** | **mmstart → 连战斗服** | **流程阻塞（总开关）** |
| BP-07 | 20 个事件推送 | 功能未实现 |
| BP-08 | 12 个 bootstrap 服务 | UNKNOWN |

---

## 五、文档导航

| 文件 | 内容 |
|---|---|
| `01_LOBBY_CURRENT_STATE.md` | 当前状态总览 |
| `02_LOBBY_COMPLETE_STATE_MACHINE.md` | ★ 真实状态机（含与任务书候选的差异更正） |
| `03_LOBBY_PROTOCOL_INVENTORY.md` | ★ 54 个协议的逐条业务作用 |
| `04_ROOM_CREATION_AND_INITIALIZATION.md` | 建房与初始化 |
| `05_ROOM_MEMBER_SYNCHRONIZATION.md` | 成员同步（含 memberCount A/B） |
| `06_ROOM_READY_AND_START_FLOW.md` | 准备与开始 |
| `07_ROOM_EVENT_DISPATCH.md` | 房间下行分派 |
| `08_PLAYLIST_AND_MODE_ENTRY_PATHS.md` | PvE vs BOT 路径 |
| `09_MATCHMAKING_AND_BOOKING.md` | mmbook |
| `10_MMSTART_AND_BATTLE_HANDOFF.md` | ★ mmstart 与交接边界 |
| `11_HISTORICAL_SUCCESS_FAILURE_TIMELINES.md` | ★ 5 个关键 run 的独立时间线 |
| `12_CLIENT_FUNCTION_CALL_GRAPH.md` | 客户端函数图 |
| `13_SERVER_FUNCTION_CALL_GRAPH.md` | 服务端函数图 |
| `14_LOBBY_BREAKPOINT_REGISTER.md` | ★ 断裂点登记 |
| `15_LOBBY_COMPLETENESS_MATRIX.md` | 完整性矩阵说明 |
| `16_LOBBY_EVIDENCE_INDEX.md` | 证据索引说明 |
| `17_LOBBY_UNKNOWN_FIELDS.md` | 未知字段清单 |
| `18_LOBBY_HISTORICAL_CONTRADICTIONS.md` | 历史矛盾 |
| `19_LOBBY_ROOT_CAUSE_ANALYSIS.md` | 根因分析 |
| `20_FINAL_LOBBY_TECHNICAL_ASSESSMENT.md` | 最终评估 |
| **`CODOL_LOBBY_ALL_UNRESOLVED_PROBLEMS.md`** | ★★★ 主交付物：全部未解决问题 |
| `LOBBY_COMPLETENESS_MATRIX.csv` / `LOBBY_BREAKPOINTS.json` / `LOBBY_PROTOCOLS.json` / `LOBBY_EVIDENCE_INDEX.json` | 机器可读 |
| `verify_lobby_forensics.py` | 自检 |

---

## 六、给接手者的三条最短路径

1. **只想让客户端连上战斗服** → 只需 `CODOL_LOBBY_ALL_UNRESOLVED_PROBLEMS.md` 的问题 7
2. **想走通房间路径** → 问题 1 → 4 → 3 → 2 → 7（严格顺序）
3. **想弄清成员/多人** → 问题 5
