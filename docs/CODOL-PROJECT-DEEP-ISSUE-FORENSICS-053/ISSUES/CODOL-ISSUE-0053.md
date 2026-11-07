# CODOL-ISSUE-0053 — ol-mod EngineBindings 宿主映像门禁永不通过（SizeOfImage 不匹配）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

EngineBindings::bind() 要求 SizeOfImage==0x0E5D6000 且 TimeDateStamp==0x6096930A；实测客户端为 0x0E659000。三次实机运行只打印 'engine binding failed'，无阶段日志。

## 2. 历史首次发现过程

- **首次发现**：2026-10-14（`COMBAT_SERVER_BLOCKERS.md §0`）
- **最近验证**：2026-10-14
- **所属系统**：`combat`　**优先级**：P3　**登记状态**：`BLOCKED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-14 | 三次实机 | 均失败 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0053-01 | source | `—` | — | ol-mod 插件（外部） | — |
| EV-0053-02 | location | `COMBAT_SERVER_BLOCKERS.md` | — |  | — |
| EV-0053-03 | location | `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` | — |  | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `COMBAT_SERVER_BLOCKERS.md` | — |  |
| `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` | — |  |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0053，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0053，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
ol-mod 插件 → bind() 门禁 → 失败
```

## 10. 第一条未闭合调用边

**—**

## 11. 已确认事实

- 客户端 SizeOfImage=0x0E659000（E1 转储实测）
- 门禁要求 0x0E5D6000

## 12. 尚未确认的假设

- —

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

不适用。

## 16. 最小复现条件

加载 ol-mod 插件。

## 17. 最小验证实验

**实验 B53**

| 项 | 内容 |
|---|---|
| 步骤 | 1. — |
| 通过判据 | — |
| 失败判据 | — |
| 成本 | — |

## 18. 条件式修复方案

**方案A：不修 ol-mod；只把它当同类参考。**

**方案B：—**

## 19. 修改影响分析

ol-mod 路线整体不可用；不影响自研战斗服。

## 20. 可测量的验收标准

1. —

## 21. 回归测试方案

—

## 22. 修复准备度

**OBSOLETE**

- **下一步**：不处理（AGENTS.md 规定 ol-mod 非权威）。
- **上游依赖**：无

---