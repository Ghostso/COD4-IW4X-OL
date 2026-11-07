# CODOL-ISSUE-0036 — gamestate 只尝试 5 次，且不随 usercmd 重试

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

if (... gamestate_attempts < 5) 才发送；失败后 gamestate_due_ms += 2000 但 attempts 继续累加。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：battle_service.c:610-613`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码复核 606-615 | 确认 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0036-01 | source | `battle/battle_service.c` | 606-615 | 发送调度与上限 | — |
| EV-0036-02 | location | `battle/battle_service.c` | 609 | if (svc->gamestate_loading) continue; | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 606-615 | 发送调度与上限 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 609 | if (svc->gamestate_loading) continue; |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0036，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
tick → gamestate_due → 最多 5 次
```

## 10. 第一条未闭合调用边

**无'超限'告警，只有 TX_GAMESTATE 计数。**

## 11. 已确认事实

- 上限 5 写死在源码

## 12. 尚未确认的假设

- 客户端在什么条件下才 ack gamestate

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

上限 5 未改。

## 16. 最小复现条件

让前 5 次 gamestate 都不被处理，观察后续是否停发。

## 17. 最小验证实验

**实验 B36**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把上限改成无限，并在超限时打 WARN<br>2. 跑一轮对比 |
| 通过判据 | gamestate 持续重发且日志可区分 |
| 失败判据 | — |
| 成本 | 1 轮 |

## 18. 条件式修复方案

**方案A：改为按状态（未收到 gamestateupdate）持续重试，并加告警。**

**方案B：保持 5 次但加显式 WARN。**

## 19. 修改影响分析

会话可能静默失败。

## 20. 可测量的验收标准

1. gamestate 未确认时会持续重发且日志可区分'已确认/超限'。

## 21. 回归测试方案

—

## 22. 修复准备度

**FIX_READY**

- **下一步**：把 :611 的上限改为状态驱动并加 WARN。
- **上游依赖**：无

---