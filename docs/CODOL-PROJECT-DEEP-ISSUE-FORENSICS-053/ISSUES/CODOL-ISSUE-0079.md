# CODOL-ISSUE-0079 — IIPS 的 Stage-1 前置门（QoS helper）从未被跨过

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

分叉点 iips.dll+0x98D2 `test al,al` 是静态已证；AL 的来源是 QoS helper（tqos_create → WSOCK32!select() → 负值 → AL=0）。该 helper 检查什么、返回什么，自评 DEPENDENCY_CAUSALITY = CANDIDATE。

## 2. 历史首次发现过程

- **首次发现**：2026-09-19（`ICH017_IIPS_BOUNDARY_SYNTHESIS.md`）
- **最近验证**：2026-10-29
- **所属系统**：`startup`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-09-18..21 | ICH013-ICH021 约 8 轮 | 绕开而非解决 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0079-01 | source | `—` | — | 客户端 + 系统 | — |
| EV-0079-02 | location | `ICH017_IIPS_BOUNDARY_SYNTHESIS.md` | — |  | — |
| EV-0079-03 | location | `ICH018_QOS_RETURN_VALUE_ATTRIBUTION.md` | — |  | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `ICH017_IIPS_BOUNDARY_SYNTHESIS.md` | — |  |
| `ICH018_QOS_RETURN_VALUE_ATTRIBUTION.md` | — |  |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0079，系统 `startup`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0079，系统 `startup`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
IIPS init → QoS helper → select() → AL
```

## 10. 第一条未闭合调用边

**QoS helper 的检查对象与返回值。**

## 11. 已确认事实

- 分叉点 iips.dll+0x98D2 静态已证
- 成功路径从未运行时观测

## 12. 尚未确认的假设

- QoS 检查条件与返回值

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-09 | 用 kit 绕过 |  |

## 15. 当前代码状态

不适用。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B79**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 用 EX060-065 契约写最小替身并观测 AL |
| 通过判据 | AL 值可解释 |
| 失败判据 | — |
| 成本 | 高 |

## 18. 条件式修复方案

**方案A：与 ISSUE-0006 合并，低优先。**

**方案B：—**

## 19. 修改影响分析

启动链的'正规'实现不可能；只能依赖 kit。

## 20. 可测量的验收标准

1. IIPS 成功路径被运行时观测一次。

## 21. 回归测试方案

—

## 22. 修复准备度

**BLOCKED_BY_EVIDENCE**

- **下一步**：暂不投入（kit 可用）。
- **上游依赖**：`CODOL-ISSUE-0006`

---