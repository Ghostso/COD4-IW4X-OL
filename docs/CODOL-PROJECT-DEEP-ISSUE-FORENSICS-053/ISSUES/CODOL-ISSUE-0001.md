# CODOL-ISSUE-0001 — 受保护基线 marketplace_store.py 哈希与清单不符（8/9）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

REF_LOBBY_KIT/_golden_hashes.json 声明 marketplace_store.py 为 46,226 B / sha256 28b4a1be…；磁盘实际 50,022 B / sha256 e44358f0eb951b62c244a136a181952c26850e841d537bcb70ebb0ffc5dd034e。其余 8 个受保护文件复算与声明一致（8/9）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-21（`CODOL_ANALYSIS_20261020/THIRD_ROUND_BLOCKER_STATUS_20261021.md §4`）
- **最近验证**：2026-10-29 (recomputed)
- **所属系统**：`baseline`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-21 | 第三轮审计记录为 preexisting_conflict（8/9） | 未处理 |
| 2026-10-27 | FIX_MEMBERCOUNT_APPLIED 再次记录'既有偏差，非本次造成' | 未处理 |
| 2026-10-29 | 本审计用 PowerShell 独立复算 9 项：8 OK / 1 mismatch | 确认仍然不符 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0001-01 | source | `—` | — | 无源码；这是基线数据问题 | — |
| EV-0001-02 | location | `REF_LOBBY_KIT/_golden_hashes.json` | 声明值 |  | — |
| EV-0001-03 | location | `run_codol_001/run_frozen_chain_once.py` | 86-118 | verify_protected_baseline() 只覆盖 launch_core 六件套 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `REF_LOBBY_KIT/_golden_hashes.json` | 声明值 |  |
| `run_codol_001/run_frozen_chain_once.py` | 86-118 | verify_protected_baseline() 只覆盖 launch_core 六件套 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0001，系统 `baseline`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0001，系统 `baseline`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
(基线数据) → preflight 校验 → 启动；marketplace_store 只影响商城模块
```

## 10. 第一条未闭合调用边

**尚未证明 50,022 B 版本相对 46,226 B 的差异内容。**

## 11. 已确认事实

- 9 项中 8 项匹配（本审计复算）
- 该文件 mtime 为 2026-10-16，非本轮造成
- --verify-only 的 launch_core 集合不含它

## 12. 尚未确认的假设

- 差异的具体内容（是否只是运行时残留）
- 是否存在第三方改动

## 13. 已排除的假设

- '本轮改坏了它'——mtime 2026-10-16，早于所有 10-27 之后的 run

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-21 | 记录但未改 | 按纪律需先批准 baseline migration |

## 15. 当前代码状态

无代码改动。存在一处**已知例外**：verify_protected_baseline() 的 launch_core 白名单刻意排除该文件。

## 16. 最小复现条件

python -I run_codol_001/run_frozen_chain_once.py --verify-only → 打印 'protected baseline: OK'（因为只查六件套）；全量复算则 8/9。

## 17. 最小验证实验

**实验 B1**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 对 46,226 B（GOLDEN-LOBBY-001 源）与 50,022 B 两份做 diff<br>2. 确认差异是否仅为日志路径/证书/会话文件等运行时残留 |
| 通过判据 | 差异全部是运行时残留 ⇒ 可走 clean migration |
| 失败判据 | 存在非残留差异 ⇒ 需要单独审计该文件 |
| 成本 | 离线 10 分钟 |

## 18. 条件式修复方案

**方案A（条件式）：若 B1 证明差异全是残留 → 提交一次显式 baseline migration（更新清单 + 记录理由），不改游戏侧文件。**

**方案B：把 marketplace_store.py 从受保护清单中移出，改由商城模块自带校验。**

## 19. 修改影响分析

不影响 IIPS/Auth/Lobby 启动路径。风险集中在商城模块与'基线完好'这一声明本身。

## 20. 可测量的验收标准

1. (1) 全量复算 9/9 匹配，或 (2) 明确记载批准例外及其范围与理由。

## 21. 回归测试方案

每次 run 的 postflight.json 应记录全量 9 项结果，而不只是 launch_core。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B1：对两份文件做 diff，判定差异性质。
- **上游依赖**：无

---