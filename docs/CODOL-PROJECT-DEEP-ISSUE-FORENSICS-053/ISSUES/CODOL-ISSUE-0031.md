# CODOL-ISSUE-0031 — 合成靶子血量不重置，长跑后所有命中都打在 0 血实体上

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

ensure_damage_target() 只在不存在时生成；codol_damage_apply 把 health 夹到 0；无复活/重置路径。33 伤害 ×4 次后归零，此后 HIT 日志仍打印但 health 不再变化。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：src/battle/battle_service.c`）
- **最近验证**：2026-10-29
- **所属系统**：`combat`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码复核 ensure_damage_target / damage_apply | 确认 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0031-01 | source | `battle/battle_service.c` | 53-74 | ensure_damage_target | — |
| EV-0031-02 | source | `world/combat.c` | 58-61 | health 夹到 0 | — |
| EV-0031-03 | location | `battle/battle_service.c` | 76-102 | apply_test_hit | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 53-74 | ensure_damage_target |
| `world/combat.c` | 58-61 | health 夹到 0 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 76-102 | apply_test_hit |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0031，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0031，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
开火 → damage_apply → health→0 后不再变化
```

## 10. 第一条未闭合调用边

**无重置路径。**

## 11. 已确认事实

- health 夹到 0 且无重置

## 12. 尚未确认的假设

- 实机长 run 是否真的出现（无自动测试）

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

无重置。

## 16. 最小复现条件

连打 5 次，观察第 5 次 health。

## 17. 最小验证实验

**实验 B31**

| 项 | 内容 |
|---|---|
| 步骤 | 1. probe_world_damage 连打 6 次并打印每次 health |
| 通过判据 | health 归零后能被重置 |
| 失败判据 | 恒 0 |
| 成本 | 离线 20 分钟 |

## 18. 条件式修复方案

**方案A：命中后重置，或按地图 actor 的复活规则处理。**

**方案B：靶子改为 cannot_die 并单独计数。**

## 19. 修改影响分析

可能把'没有伤害变化'误读为逻辑失效。

## 20. 可测量的验收标准

1. 连续 10 次命中后目标仍可被伤害（或按规则死亡并复活）。

## 21. 回归测试方案

probe_world_damage 增加连续命中用例。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 apply_test_hit 后重置或复活靶子。
- **上游依赖**：`CODOL-ISSUE-0030`

---