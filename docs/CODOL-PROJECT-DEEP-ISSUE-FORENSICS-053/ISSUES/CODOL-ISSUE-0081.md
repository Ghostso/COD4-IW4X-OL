# CODOL-ISSUE-0081 — ResourceManager ABI 大部分是虚构的；GetResourceManagerII 从未被调用

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

9 次运行、两套 provider 下 GetResourceManagerII 被调用 0 次；ICH-027 的 IIPS_IsPackReady 契约在运行时被否定；早期'ResourceManager ABI'描述大部分虚构；LocalRM_v3 导出目录错位 4 字节；对象尺寸 0x480 vs 0x410 矛盾。

## 2. 历史首次发现过程

- **首次发现**：2026-09-21（`RESTORE_LOCALRM_006_DECISION.md / RESTORE_ENGINE_BRIDGE_003`）
- **最近验证**：2026-09-21
- **所属系统**：`startup`　**优先级**：P2　**登记状态**：`CONTRADICTORY_EVIDENCE`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-09-21 | 连续多轮自我证伪 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0081-01 | source | `—` | — | 客户端 | — |
| EV-0081-02 | location | `RESTORE_LOCALRM_006_DECISION.md` | — |  | — |
| EV-0081-03 | location | `RESTORE_ENGINE_BRIDGE_003_DECISION.md` | — |  | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `RESTORE_LOCALRM_006_DECISION.md` | — |  |
| `RESTORE_ENGINE_BRIDGE_003_DECISION.md` | — |  |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0081，系统 `startup`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0081，系统 `startup`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
引擎 → ResourceManager（实际不调用）
```

## 10. 第一条未闭合调用边

**真实 ABI。**

## 11. 已确认事实

- GetResourceManagerII 调用 0 次（9 次运行）
- 自建 ABI 描述不可信

## 12. 尚未确认的假设

- 真实 ABI

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-09 | 自建 LocalRM 替身 | 失败 |

## 15. 当前代码状态

不适用。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B81**

| 项 | 内容 |
|---|---|
| 步骤 | 1. — |
| 通过判据 | — |
| 失败判据 | — |
| 成本 | — |

## 18. 条件式修复方案

**方案A：不再按虚构 ABI 设计；只能走 kit。**

**方案B：—**

## 19. 修改影响分析

'自研资源层'这条路线全部设计前提不可信。

## 20. 可测量的验收标准

1. 任何资源层替代方案有运行时调用证据。

## 21. 回归测试方案

—

## 22. 修复准备度

**BLOCKED_BY_EVIDENCE**

- **下一步**：暂不投入。
- **上游依赖**：`CODOL-ISSUE-0006`

---