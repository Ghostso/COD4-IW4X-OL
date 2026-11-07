# CODOL-ISSUE-0090 — TESTOL 交付包：1/769 哈希不符、缺 inject_ayria.on、deploy 只比大小

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

清单 769 条里 1 条哈希不符（Localnetworking.Ayria32）；缺 inject_ayria.on ⇒ 插件不加载；deploy.ps1 只比大小 ⇒ 同大小替换永远部署不进去。

## 2. 历史首次发现过程

- **首次发现**：2026-10-25（`_LEARN_TESTOL_DELIVERY2/reports/010, 013`）
- **最近验证**：2026-10-25
- **所属系统**：`external`　**优先级**：P3　**登记状态**：`OPEN`　**严重度**：low
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-25 | _LEARN_TESTOL_DELIVERY 系列记录 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0090-01 | source | `—` | — | 外部交付包 | — |
| EV-0090-02 | location | `_LEARN_TESTOL_DELIVERY2/reports/010-manifest-verify-result.md` | — |  | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `_LEARN_TESTOL_DELIVERY2/reports/010-manifest-verify-result.md` | — |  |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0090，系统 `external`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0090，系统 `external`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
不适用
```

## 10. 第一条未闭合调用边

**原版 Localnetworking.Ayria32 无法恢复。**

## 11. 已确认事实

- 三处缺陷（文档 + 哈希复算）

## 12. 尚未确认的假设

- 原版文件

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

不适用。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B90**

| 项 | 内容 |
|---|---|
| 步骤 | 1. — |
| 通过判据 | — |
| 失败判据 | — |
| 成本 | — |

## 18. 条件式修复方案

**方案A：只读参考；不作为主线。**

**方案B：—**

## 19. 修改影响分析

该包不能作为独立路线。

## 20. 可测量的验收标准

1. —

## 21. 回归测试方案

—

## 22. 修复准备度

**OBSOLETE**

- **下一步**：不处理。
- **上游依赖**：无

---