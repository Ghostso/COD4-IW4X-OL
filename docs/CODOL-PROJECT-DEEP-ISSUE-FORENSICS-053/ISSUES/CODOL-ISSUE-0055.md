# CODOL-ISSUE-0055 — 进图后客户端从不发送开火位（bit0 缺失）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

所有抓到的 usercmd 里都没有 bit0（开火）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-22（`CODOL_SERVER_319_20261021/HANDOFF_20261022_PAUSE.md §1.3`）
- **最近验证**：2026-10-22
- **所属系统**：`combat`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-22 | HANDOFF_20261022_PAUSE §1.3 记录 bit0 缺失 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0055-01 | source | `battle/equipment.c` | 109-188 | codol_equipment_step（靠 buttons 判开火） | — |
| EV-0055-02 | source | `include/codol_usercmd.h` | — | BUTTON 位定义 | — |
| EV-0055-03 | location | `battle/battle_service.c` | 984-993 | equipment_step 返回 true 才算开火 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/equipment.c` | 109-188 | codol_equipment_step（靠 buttons 判开火） |
| `include/codol_usercmd.h` | — | BUTTON 位定义 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 984-993 | equipment_step 返回 true 才算开火 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0055，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0055，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
客户端输入 → usercmd.buttons → equipment_step
```

## 10. 第一条未闭合调用边

**开火是否根本不在 usercmd 里。**

## 11. 已确认事实

- 全部实机 usercmd 无 bit0

## 12. 尚未确认的假设

- 开火的真实载体

## 13. 已排除的假设

- '按钮位定义错'——因为整个 bit0 从未置位，不只是某一位

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

equipment_step 依赖 buttons 位；若位从不出现则永不触发。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B55**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 一次实机里只按开火，抓 keymap_cal.csv<br>2. 检查 buttons 列是否出现任何新位 |
| 通过判据 | 出现新位 ⇒ 记下该位 |
| 失败判据 | 仍为 0 ⇒ 开火不走 usercmd |
| 成本 | 1 轮 |

## 18. 条件式修复方案

**方案A（条件式）：若 B55 找到开火位 → 把它加进 equipment_step 判定。**

**方案B：若不走 usercmd → 在可靠命令里找开火。**

## 19. 修改影响分析

没有开火就无法验证命中/伤害/死亡。

## 20. 可测量的验收标准

1. 开火动作在服务端产生可识别的输入事件。

## 21. 回归测试方案

keymap_cal.csv 记录每轮按键分布。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B55：单按键录制。
- **上游依赖**：`CODOL-ISSUE-0060`

---