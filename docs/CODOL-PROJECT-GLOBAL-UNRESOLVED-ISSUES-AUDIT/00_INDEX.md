# 00 — CODOL 复活项目 全历史未解决问题与技术债总审计 · 入口

> 任务编号 `CODOL-PROJECT-GLOBAL-UNRESOLVED-ISSUES-AUDIT`
> 审计日期：2026-10-29
> 目标版本：CODOL 3.19.26.22 / build 1649370
> 审计范围：`D:\BaiduNetdiskDownload\使命召唤OL` 全树（189 个顶层目录 / 367,244 个文件）

---

## 一、一句话结论

项目已经**能进大厅、能建房、能解析 usercmd、快照能被客户端确认**，
但截至 2026-10-29，**客户端根本不向战斗服发起连接**（BOT 房间入口），
因此"进入地图"这一历史成绩**当前无法复现**，完整对局 0/6 门槛。

---

## 二、关键数字（全部由 `MASTER_ISSUES.json` 计算，可复算）

- 发现问题总数 **92**
- 未解决问题总数为 **86**（不含 `RESOLVED_VERIFIED` / `OBSOLETE`）
- 直接阻塞"出现可操控游戏画面"的问题：**25**
- 其中 P0 **7** 项

| 优先级 | 数量 |
| --- | --- |
| P0 | 7 |
| P1 | 29 |
| P2 | 41 |
| P3 | 9 |
| NONE（已作废/已解决） | 6 |

状态分布：

| 状态 | 数量 |
|---|---|
| OPEN | 45 |
| CONTRADICTORY_EVIDENCE | 11 |
| BLOCKED | 8 |
| NOT_IMPLEMENTED | 7 |
| UNVERIFIED | 8 |
| PARTIALLY_RESOLVED | 6 |
| UNKNOWN | 1 |
| OBSOLETE | 5 |
| RESOLVED_VERIFIED | 1 |

> 这些数字由 `build_deliverables.py` 从 `MASTER_ISSUES.json` 计算，
> `verify_audit.py` 会检查本文件里的数字与数据一致。

---

## 三、七个 P0

| Issue | 标题 |
|---|---|
| [CODOL-ISSUE-0020](03_MASTER_UNRESOLVED_ISSUES.md) | BOT 房间场景下战斗服零收包（客户端从不 connect） |
| [CODOL-ISSUE-0021](03_MASTER_UNRESOLVED_ISSUES.md) | `mmstart` 不带 map/gametype，playlist 语义未定 |
| [CODOL-ISSUE-0074](03_MASTER_UNRESOLVED_ISSUES.md) | `102/7` playerdata 回全 0 清空玩家选图/选模式 |
| [CODOL-ISSUE-0012](03_MASTER_UNRESOLVED_ISSUES.md) | `dwRoomMatch::Init` 从未被调用（MyEventHandler 零实例） |
| [CODOL-ISSUE-0009](03_MASTER_UNRESOLVED_ISSUES.md) | 准备按钮点击不产生任何上行，根因未定 |
| [CODOL-ISSUE-0010](03_MASTER_UNRESOLVED_ISSUES.md) | 房间下行推送格式反复反转，最终未定死 |
| [CODOL-ISSUE-0041](03_MASTER_UNRESOLVED_ISSUES.md) | recv 缓冲 → `0x7765A0` 读取器的边未闭合（最小未闭合边） |

**最小根阻塞集合 = `{0020, 0021, 0074}`**（见 `11_ISSUE_DEPENDENCY_GRAPH.md §4`）。
`{0009, 0010, 0012}` 是房间入口的根阻塞；`{0041}` 是所有"客户端会解析我们的包"类结论的共同前提。

---

## 四、文档导航

| 文件 | 内容 | 读者 |
|---|---|---|
| **00_INDEX.md** | 本文件：入口与关键数字 | 所有人 |
| **01_PROJECT_HISTORY_TIMELINE.md** | 从黑箱到现在的完整技术演进时间线（9 个阶段） | 新 agent 第一份要读的 |
| **02_ALL_HISTORICAL_ISSUES.md** | 全部历史结论，分 CLOSED / OBSOLETE / WRONG / UNVERIFIED 四类 | **避免重复调查** |
| **03_MASTER_UNRESOLVED_ISSUES.md** | ★ 主台账：86 项未解决问题逐项详情 | 开发者 |
| **04_P0_CRITICAL_BLOCKERS.md** | 7 项 P0 的深度分析 | 决策者 |
| **05_PROTOCOL_GAPS.md** | UDP/DTLS/ECDH/OOB/GameState/Configstring/Reliable/Snapshot/Usercmd | 协议开发者 |
| **06_CLIENT_REVERSE_ENGINEERING_GAPS.md** | 未闭合的调用链、数据流、状态机 | 逆向 |
| **07_SERVER_IMPLEMENTATION_GAPS.md** | 战斗服"写了/接线了/有缺陷"三分表 | 服务端开发者 |
| **08_MAP_AND_ASSET_GAPS.md** | IIPS/IFS/Fastfile/Clipmap/实体表 | 资产 |
| **09_MOVEMENT_AND_COMBAT_GAPS.md** | 移动、预测、碰撞、射击、生命值、死亡复活 | 玩法 |
| **10_CONTRADICTIONS_AND_FALSE_CLOSURES.md** | 9 个典型假闭合 + 措辞陷阱 + 数字冲突 | **必读**，防重复踩坑 |
| **11_ISSUE_DEPENDENCY_GRAPH.md** | 依赖图与关键路径 | 项目管理 |
| **12_PRIORITIZED_DEVELOPMENT_ROADMAP.md** | 路线 A（最短可操控）/ B（完整战斗服）/ C（工程化） | 排期 |
| **13_PROJECT_READINESS_ASSESSMENT.md** | L0–L4 五级完成度评估 | 决策者 |
| **14_AUDIT_COVERAGE_AND_MISSING_SOURCES.md** | 扫描覆盖、找不到的资料、可信度声明 | 复核者 |
| **MASTER_ISSUES.json** | 机器可读问题数据库（唯一事实来源） | 工具 |
| **MASTER_ISSUES.csv** | Excel 可筛选清单 | 人 |
| **SHA256SUMS.txt** | 全部交付物的哈希 | 完整性 |
| **verify_audit.py** | 自动校验脚本 | CI |

辅助脚本（生成用，可复跑）：

| 脚本 | 作用 |
|---|---|
| `build_register.py` | 从结构化定义生成 `MASTER_ISSUES.json` |
| `build_deliverables.py` | 生成 `MASTER_ISSUES.csv` 并校验 |
| `build_docs.py` | 从 JSON 生成 `03`/`04`（保证计数不脱节） |
| `make_sums.py` | 生成 `SHA256SUMS.txt` |
| `verify_audit.py` | 全量自检 |

原始扫描中间产物：`_work/`（三个历史语料扫描器的原始输出 + 本次源码审计笔记）。

---

## 五、给"完全不了解项目历史的新 Agent"的阅读顺序

1. `01_PROJECT_HISTORY_TIMELINE.md` — 知道发生过什么
2. `10_CONTRADICTIONS_AND_FALSE_CLOSURES.md` — 知道哪些结论不能信
3. `02_ALL_HISTORICAL_ISSUES.md` — 知道哪些别再重做
4. `03_MASTER_UNRESOLVED_ISSUES.md` — 知道现在还剩什么
5. `12_PRIORITIZED_DEVELOPMENT_ROADMAP.md` — 知道下一步做什么

**特别注意三条纪律**（来自本审计与项目既有的教训）：

- **"代码写好了" ≠ "代码被调用"**（`bind_world` 曾从未被调用）
- **"与参照一致" ≠ "客户端接受"**（141B 黄金向量在本客户端上是死路）
- **"服务端发送成功" ≠ "客户端消费成功"**（实体段、房间推送都栽在这）
