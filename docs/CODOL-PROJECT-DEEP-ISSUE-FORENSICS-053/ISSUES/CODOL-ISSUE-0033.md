# CODOL-ISSUE-0033 — 战斗服 struct 是单客户端设计，多客户端不可表达

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

一个 svc 里只有一份 player / equip / snap_from / snap_cur / input_baselines；send_snapshot 只写本地客户端状态。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：battle_service.c`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码复核 codol_battle_service.h 字段 | 确认单客户端 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0033-01 | source | `include/codol_battle_service.h` | — | svc 结构定义 | — |
| EV-0033-02 | source | `battle/battle_service.c` | 421-591 | send_snapshot 只写 svc->player | — |
| EV-0033-03 | location | `battle/battle.c` | 61 | codol_battle_find_or_alloc 有 per-peer assoc，但状态没放进去 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `include/codol_battle_service.h` | — | svc 结构定义 |
| `battle/battle_service.c` | 421-591 | send_snapshot 只写 svc->player |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle.c` | 61 | codol_battle_find_or_alloc 有 per-peer assoc，但状态没放进去 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0033，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
多个 peer → 共享一个 svc 状态
```

## 10. 第一条未闭合调用边

**per-client 状态没有存在于 assoc 里。**

## 11. 已确认事实

- svc 内只有一份 player/equip/baselines

## 12. 尚未确认的假设

- —

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

单客户端结构。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B33**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把 player/equip/baselines 移进 codol_battle_assoc_t<br>2. 模拟两个 peer 各自发 usercmd |
| 通过判据 | 两个 peer 各自收到以自己为视角的快照 |
| 失败判据 | — |
| 成本 | 离线 1 天 |

## 18. 条件式修复方案

**方案A：per-client 状态移进 assoc。**

**方案B：长期再改（当前单客户端都没跑通）。**

## 19. 修改影响分析

多人同步在本架构下不可实现（与 TX 缓冲并列）。

## 20. 可测量的验收标准

1. 两个 peer 各自收到以自己为视角的快照。

## 21. 回归测试方案

test_session 增加双客户端用例。

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 ISSUE-0023（缓冲）与 0020（连接）。
- **上游依赖**：`CODOL-ISSUE-0023`, `CODOL-ISSUE-0020`

---