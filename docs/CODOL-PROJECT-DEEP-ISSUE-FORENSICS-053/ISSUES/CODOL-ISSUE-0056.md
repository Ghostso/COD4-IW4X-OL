# CODOL-ISSUE-0056 — idx20 (pm_flags) 写 aiming?0x10，而 0x10 可能是 PMF_SPRINTING 并挡掉开镜

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

SNAPSHOT_RAWFIX_20261024_1357 里用户报开镜失效，与 idx20 改动同期出现。0x10 在 CoD 里是 PMF_SPRINTING。

## 2. 历史首次发现过程

- **首次发现**：2026-10-24（`docs/SNAPSHOT_FIELD_DIFF_20261024.md §12.3`）
- **最近验证**：2026-10-24
- **所属系统**：`battle-snapshot`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-24 13:57 | SNAPSHOT_RAWFIX：idx20 写 aiming?0x10:0 | 开镜失效 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0056-01 | source | `battle/snapshot.c` | 532 | cur->pm_flags = aiming ? 0x10 : 0 | — |
| EV-0056-02 | location | `battle/battle_service.c` | 118 | svc->player.aiming = (buttons & CODOL_BTN_ADS) | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/snapshot.c` | 532 | cur->pm_flags = aiming ? 0x10 : 0 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 118 | svc->player.aiming = (buttons & CODOL_BTN_ADS) |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0056，系统 `battle-snapshot`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-snapshot 对应小节。

## 9. 完整数据流

```
usercmd.buttons → aiming → idx20=0x10
```

## 10. 第一条未闭合调用边

**3.19 的 pm_flags 位定义表。**

## 11. 已确认事实

- idx20 值随 aiming 变化（源码）
- 开镜失效与 idx20 改动同期

## 12. 尚未确认的假设

- 0x10 在 3.19 是否就是 PMF_SPRINTING

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-24 | idx61 回退但 idx20 保留 | 开镜失效是否仍在未单独验证 |

## 15. 当前代码状态

idx20 = aiming?0x10:0 仍在。

## 16. 最小复现条件

把 idx20 固定为 0 跑一轮，看开镜是否恢复。

## 17. 最小验证实验

**实验 B56**

| 项 | 内容 |
|---|---|
| 步骤 | 1. idx20 固定 0 vs 动态，两轮对照<br>2. 用户观察开镜 |
| 通过判据 | 固定 0 时开镜恢复 |
| 失败判据 | 仍失效 ⇒ 与 idx20 无关 |
| 成本 | 2 轮（需 0020） |

## 18. 条件式修复方案

**方案A（条件式）：若 B56 指向 idx20 → 改用正确的 ADS 位或固定 0。**

**方案B：查 3.19 的 pm_flags 定义。**

## 19. 修改影响分析

开镜功能。

## 20. 可测量的验收标准

1. 开镜可用，且 idx20 语义有本 build 证据。

## 21. 回归测试方案

—

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 ISSUE-0020。
- **上游依赖**：`CODOL-ISSUE-0020`, `CODOL-ISSUE-0027`

---