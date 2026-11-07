# CODOL-ISSUE-0064 — gamestate 尾部 44 字节未解析，configstring index_bits 未知

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

gamestate 有 44 字节尾未解析；configstring 的 incremental index 编码未知。

## 2. 历史首次发现过程

- **首次发现**：2026-10-23（`docs/PHASE2_GAMESTATE_CONFIGSTRING_DONE_20261023.md §6`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-snapshot`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-23 | PHASE2 记录 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0064-01 | source | `battle/battle_service.c` | 302-372 | _gs_adapt_dynamic 只改首部 | — |
| EV-0064-02 | location | `firingrange-gamestate.bin` | — | 283 B 样本（注意：旧记录写 259 B，不是同一份） | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 302-372 | _gs_adapt_dynamic 只改首部 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `firingrange-gamestate.bin` | — | 283 B 样本（注意：旧记录写 259 B，不是同一份） |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0064，系统 `battle-snapshot`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `firingrange-gamestate.bin`，以及 `05_PROTOCOL_GAPS.md` 中 battle-snapshot 对应小节。

## 9. 完整数据流

```
模板 gamestate → 只改 header → 下发
```

## 10. 第一条未闭合调用边

**客户端读取路径。**

## 11. 已确认事实

- 尾部 44 B 未解析
- 样本从 259 B 变为 283 B（两份不同）

## 12. 尚未确认的假设

- 尾部字段含义

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

_gs_adapt_dynamic 只改 map/gametype 字符串。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B64**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 逐字节改尾部，观察客户端行为 |
| 通过判据 | 能定位字段边界 |
| 失败判据 | 无反应 |
| 成本 | 多轮 |

## 18. 条件式修复方案

**方案A：先解尾再改。**

**方案B：只在首部做改动（当前做法）。**

## 19. 修改影响分析

动态房间适配只改首部，尾部语义不明。

## 20. 可测量的验收标准

1. 尾部字段有名且有实测。

## 21. 回归测试方案

—

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 ISSUE-0020。
- **上游依赖**：`CODOL-ISSUE-0020`

---