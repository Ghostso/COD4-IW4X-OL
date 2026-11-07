# CODOL-ISSUE-0030 — 子弹命中不是射线：距离公式 + 固定假目标 + 固定武器

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

apply_test_hit()（:76-102）用 |target.origin - player.origin| 作为 distance，武器写死 "m4a1tech_mp"，命中部位写死 CODOL_HITLOC_TORSO_UPPER；无方向、无 trace、无 miss。ensure_damage_target() 在 (0,0,-116) 生成 owner=1001 的合成 actor。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：src/battle/battle_service.c`）
- **最近验证**：2026-10-29
- **所属系统**：`combat`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-25 | probe_world_damage 离线验证 damage=33 / trace fraction=0.292 | 但那用的是 movement_trace，不是伤害路径 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0030-01 | source | `battle/battle_service.c` | 53-74 | ensure_damage_target | — |
| EV-0030-02 | source | `battle/battle_service.c` | 76-102 | apply_test_hit | — |
| EV-0030-03 | source | `world/combat.c` | 21-63 | codol_damage_apply | — |
| EV-0030-04 | location | `movement/movement.c` | 143-189 | codol_movement_trace（存在但伤害路径未调用） | — |
| EV-0030-05 | location | `world/combat.c` | 52-56 | codol_weapondef_damage_for_hit | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 53-74 | ensure_damage_target |
| `battle/battle_service.c` | 76-102 | apply_test_hit |
| `world/combat.c` | 21-63 | codol_damage_apply |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `movement/movement.c` | 143-189 | codol_movement_trace（存在但伤害路径未调用） |
| `world/combat.c` | 52-56 | codol_weapondef_damage_for_hit |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0030，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0030，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
开火(equipment_step) → apply_test_hit → distance 公式 → codol_damage_apply → health--
```

## 10. 第一条未闭合调用边

**没有 bullet trace；codol_movement_trace 已有且有测试，但没接进伤害路径。**

## 11. 已确认事实

- 伤害数值层可用（33 damage, 100→67）
- apply_test_hit 无 trace 调用

## 12. 尚未确认的假设

- 真实射击在线上到底走哪条消息（开火位 bit0 从未出现）

## 13. 已排除的假设

- '伤害系统没实现'——实现存在，只是调用方式不是射击

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

合成靶 + 距离公式仍在（:53-102）。

## 16. 最小复现条件

probe_world_damage：在目标与玩家之间放一个障碍盒，看伤害是否仍生效。

## 17. 最小验证实验

**实验 B30**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在 probe_world_damage 里加'目标在障碍后应打不中'的用例<br>2. 用 codol_movement_trace 从玩家眼位朝目标方向 trace，fraction<1 则不结算 |
| 通过判据 | 有遮挡时伤害为 0 |
| 失败判据 | 仍扣血 ⇒ 未接 trace |
| 成本 | 离线 1 小时 |

## 18. 条件式修复方案

**方案A：用 codol_movement_trace() 替换距离公式，命中点决定 hitloc。**

**方案B：保留合成靶用于自动化回归，另建真实射击路径。**

## 19. 修改影响分析

'命中/伤害已闭合'的结论只在合成目标上成立。

## 20. 可测量的验收标准

1. 有遮挡时命中失败，无遮挡时命中，伤害随距离衰减。

## 21. 回归测试方案

test_static_closure 增加遮挡用例。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 apply_test_hit 里改为 trace 后再调 codol_damage_apply。
- **上游依赖**：`CODOL-ISSUE-0029`

---