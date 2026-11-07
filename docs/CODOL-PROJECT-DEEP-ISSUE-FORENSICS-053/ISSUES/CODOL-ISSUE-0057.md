# CODOL-ISSUE-0057 — 动态武器索引无静态全表，且 firstDynamicWeapon 每图不同（1224 vs 1147）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

客户端在 CL_ParseGamestate 第二遍分配武器索引；不同地图起点不同（1224 vs 1147）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-25（`_weapon_table_20261025/codol_dynamic_index_model.md`）
- **最近验证**：2026-10-25
- **所属系统**：`combat`　**优先级**：P2　**登记状态**：`NOT_IMPLEMENTED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-25 | _weapon_table 记录两图起点差异 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0057-01 | source | `battle/weapondefs.c` | 11 | codol_weapondef_find | — |
| EV-0057-02 | location | `_weapon_table_20261025/codol_dynamic_index_model.md` | — | 分析 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/weapondefs.c` | 11 | codol_weapondef_find |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `_weapon_table_20261025/codol_dynamic_index_model.md` | — | 分析 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0057，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0057，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
gamestate 武器表 → 客户端两遍分配 → 动态索引
```

## 10. 第一条未闭合调用边

**第一遍/第二遍分配规则的完整定义。**

## 11. 已确认事实

- 两图 firstDynamicWeapon 不同（1224/1147）
- 无静态全表

## 12. 尚未确认的假设

- 分配规则

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

服务端用固定武器号（实机武器号 1156 一直正常）。

## 16. 最小复现条件

换图，对比 firstDynamicWeapon。

## 17. 最小验证实验

**实验 B57**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 对 mp_raid 与 coop_train 各导出一次武器表<br>2. 比较索引偏移 |
| 通过判据 | 能推出偏移公式 |
| 失败判据 | 每图都不同且无规律 |
| 成本 | 离线数小时 |

## 18. 条件式修复方案

**方案A：按 gamestate 的武器表现场构造映射。**

**方案B：只支持已验证的图。**

## 19. 修改影响分析

换图时武器号可能错位。

## 20. 可测量的验收标准

1. 任意地图上服务端武器号与客户端一致。

## 21. 回归测试方案

—

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B57：两图武器表对照。
- **上游依赖**：`CODOL-ISSUE-0087`

---