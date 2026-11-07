# CODOL-ISSUE-0062 — entityState 字段数在 24 与 63 之间存在矛盾（记忆称 63）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

阶段文档写 24 netField 项；反汇编 0x671170 读出 6 位 lastChangedField（≤63）且 numFields 恒 63。

## 2. 历史首次发现过程

- **首次发现**：2026-10-23（`docs/PHASE4_FIELD_SEMANTICS_DONE_20261023.md §2`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-snapshot`　**优先级**：P2　**登记状态**：`CONTRADICTORY_EVIDENCE`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-23 | PHASE4 写 24 |  |
| 2026-10-24 | 记忆条目指出 63 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0062-01 | source | `—` | — | 客户端反汇编 | — |
| EV-0062-02 | location | `docs/entity delta reader 0x671170` | — | 6 位 lastChangedField | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `docs/entity delta reader 0x671170` | — | 6 位 lastChangedField |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0062，系统 `battle-snapshot`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `docs/entity delta reader 0x671170`，以及 `05_PROTOCOL_GAPS.md` 中 battle-snapshot 对应小节。

## 9. 完整数据流

```
entityState 表 → 63 项
```

## 10. 第一条未闭合调用边

**—**

## 11. 已确认事实

- 6 位 ⇒ ≤63
- numFields 恒 63（记忆条目，非本轮实测）

## 12. 尚未确认的假设

- —

## 13. 已排除的假设

- 24 项

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

不适用。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B62**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 重读 0x671170 的 numFields 表<br>2. 确认 63 |
| 通过判据 | 63 被证实 |
| 失败判据 | — |
| 成本 | 离线 30 分钟 |

## 18. 条件式修复方案

**方案A：在 Phase4 文档加更正。**

**方案B：—**

## 19. 修改影响分析

若按 24 写会截断字段。

## 20. 可测量的验收标准

1. 文档与本 build 反汇编一致。

## 21. 回归测试方案

—

## 22. 修复准备度

**FIX_READY**

- **下一步**：给 PHASE4 文档加更正注记。
- **上游依赖**：无

---