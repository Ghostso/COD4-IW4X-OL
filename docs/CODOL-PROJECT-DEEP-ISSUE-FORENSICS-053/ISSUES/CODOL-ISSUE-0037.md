# CODOL-ISSUE-0037 — 两个 usercmd 处理分支重复且已出现分歧

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

handle_netchan_frame() 与 handle_plain() 的非 FAT 内联分支几乎相同；后者多了 CMD_FIELD_CHANGE 记录，keymap 表头一处是 \n 一处是字面反斜杠+n。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：battle_service.c:708-839 vs 923-1053`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P3　**登记状态**：`OPEN`　**严重度**：low
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码对照两段 | 发现两处分歧 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0037-01 | source | `battle/battle_service.c` | 708-839 | handle_netchan_frame | — |
| EV-0037-02 | source | `battle/battle_service.c` | 923-1053 | handle_plain 内联分支 | — |
| EV-0037-03 | location | `battle/battle_service.c` | 1002 | "\\n" 字面反斜杠 n | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 708-839 | handle_netchan_frame |
| `battle/battle_service.c` | 923-1053 | handle_plain 内联分支 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 1002 | "\\n" 字面反斜杠 n |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0037，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
FAT 重组路径 vs 普通帧路径 各走一份
```

## 10. 第一条未闭合调用边

**—**

## 11. 已确认事实

- 两段逻辑重复且已分歧（keymap 表头、CMD_FIELD_CHANGE）

## 12. 尚未确认的假设

- —

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

两份并存。

## 16. 最小复现条件

对比两段的 diff。

## 17. 最小验证实验

**实验 B37**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把两段合并为 handle_usercmd_body()<br>2. 两处调用 |
| 通过判据 | 只剩一个实现 |
| 失败判据 | — |
| 成本 | 离线 40 分钟 |

## 18. 条件式修复方案

**方案A：合并为一个函数。**

**方案B：保持不变但修掉 \n。**

## 19. 修改影响分析

修复需做两次，容易漏。

## 20. 可测量的验收标准

1. 只有一个 usercmd 解析实现。

## 21. 回归测试方案

ctest 全绿。

## 22. 修复准备度

**FIX_READY**

- **下一步**：抽出公共函数并替换两处。
- **上游依赖**：无

---