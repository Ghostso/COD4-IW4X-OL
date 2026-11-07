# CODOL-ISSUE-0067 — 命中盒/护甲/穿透几何缺失；recoil/spread/ADS 公式缺失

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

20 槽 hitloc 有名字但无几何；无原生护甲表；无 FMJ 材质穿透；无 recoil/view kick/ADS 精度公式。

## 2. 历史首次发现过程

- **首次发现**：2026-10-23（`docs/INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`）
- **最近验证**：2026-10-29
- **所属系统**：`combat`　**优先级**：P2　**登记状态**：`NOT_IMPLEMENTED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-23 | INMATCH 标 PARTIAL |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0067-01 | source | `world/combat.c` | 21-63 | codol_damage_apply（通用 policy） | — |
| EV-0067-02 | location | `battle/battle_service.c` | 95-97 | 固定 TORSO_UPPER | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `world/combat.c` | 21-63 | codol_damage_apply（通用 policy） |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 95-97 | 固定 TORSO_UPPER |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0067，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0067，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
武器 → hitloc → damage_apply（无几何）
```

## 10. 第一条未闭合调用边

**原生骨骼/命中盒几何、护甲表、G_Damage 分支。**

## 11. 已确认事实

- 只有通用 AABB 与固定部位

## 12. 尚未确认的假设

- 原生几何与公式

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

通用实现。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B67**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 至少一把枪完成 trace+距离+部位+护甲/穿透 |
| 通过判据 | 四段链路可复核 |
| 失败判据 | — |
| 成本 | 多天 |

## 18. 条件式修复方案

**方案A：按 INMATCH 门槛 3 逐项补齐。**

**方案B：只做距离伤害，记录其余为未实现。**

## 19. 修改影响分析

伤害数值与原版不一致（但基础闭环可用）。

## 20. 可测量的验收标准

1. 至少一把枪完成真实命中：trace + 距离伤害 + 部位倍率 + 护甲/穿透。

## 21. 回归测试方案

probe_world_damage 扩展命中用例。

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 ISSUE-0030 与 0029。
- **上游依赖**：`CODOL-ISSUE-0030`, `CODOL-ISSUE-0029`

---