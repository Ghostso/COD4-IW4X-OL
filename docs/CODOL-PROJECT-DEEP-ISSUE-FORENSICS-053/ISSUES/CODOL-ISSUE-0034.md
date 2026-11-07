# CODOL-ISSUE-0034 — stats 分块状态是全局而非 per-peer，且重连时不重置

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

svc->stats_total/stats_chunks/stats_buf 在 key-exchange 重置块里没有清零；两个 peer 会互相覆盖。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：battle_service.c:680-703, 1100-1127`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P3　**登记状态**：`OPEN`　**严重度**：low
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码复核 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0034-01 | source | `battle/battle_service.c` | 680-703 | handle_stats 使用全局字段 | — |
| EV-0034-02 | source | `battle/battle_service.c` | 1100-1127 | 重置块未含 stats | — |
| EV-0034-03 | location | `battle/battle_service.c` | 654-704 | handle_stats | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 680-703 | handle_stats 使用全局字段 |
| `battle/battle_service.c` | 1100-1127 | 重置块未含 stats |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 654-704 | handle_stats |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0034，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
stats 分块 → svc->stats_buf（全局）
```

## 10. 第一条未闭合调用边

**—**

## 11. 已确认事实

- stats 字段在 svc 上而非 assoc 上
- 重置块不含它们

## 12. 尚未确认的假设

- —

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

全局单份。

## 16. 最小复现条件

单测：两次会话间 stats_chunks 应归零。

## 17. 最小验证实验

**实验 B34**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在 key-ex 重置块里加 stats 清零 |
| 通过判据 | 新会话 stats_chunks 从 0 开始 |
| 失败判据 | — |
| 成本 | 离线 10 分钟 |

## 18. 条件式修复方案

**方案A：移进 assoc 并在连接重置时清零。**

**方案B：只在重置块里补清零（最小改动）。**

## 19. 修改影响分析

极端情况下 statResponse 位掩码错误，客户端反复重传。

## 20. 可测量的验收标准

1. 新会话 stats_chunks 从 0 开始。

## 21. 回归测试方案

test_battle 增加 stats 重置用例。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 :1100 重置块补 stats_total/stats_chunks/stats_buf。
- **上游依赖**：无

---