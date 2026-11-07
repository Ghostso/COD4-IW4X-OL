# CODOL-ISSUE-0029 — 服务端地面是写死的无限平面 z=-116，与任何地图无关

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

collision.c:11 `const float codol_ground_z = -116.0f;`；trace 里 delta[2]<0 一律在 codol_ground_z 截断（:93-104）。coop clipmap 的 30 个 brush 覆盖 x -824..-177，出生点 (48,-572) 在所有碰撞体之外。

## 2. 历史首次发现过程

- **首次发现**：2026-10-26（`docs/CLIPMAP_EXTRACTION_20261026.md + 源码`）
- **最近验证**：2026-10-29
- **所属系统**：`movement`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-26 | CLIPMAP_EXTRACTION 证明 coop 层 27 平面全垂直、零地板 | 确认数据缺失 |
| 2026-10-26 | MP_FIRINGRANGE_CLIPMAP 解出 1104 个朝上平面 | 但 cbrush_t 表未定位 |
| 2026-10-29 | 源码复核 codol_ground_z 仍在 | 未变 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0029-01 | source | `world/collision.c` | 11 | codol_ground_z | — |
| EV-0029-02 | source | `world/collision.c` | 93-104 | ground plane 截断 | — |
| EV-0029-03 | location | `world/collision.c` | 25-29 | codol_static_boxes[] ← codol_clipmap_coop_train.inc | — |
| EV-0029-04 | location | `include/codol_clipmap_coop_train.inc` | 1-29 | 29 个 AABB | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `world/collision.c` | 11 | codol_ground_z |
| `world/collision.c` | 93-104 | ground plane 截断 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `world/collision.c` | 25-29 | codol_static_boxes[] ← codol_clipmap_coop_train.inc |
| `include/codol_clipmap_coop_train.inc` | 1-29 | 29 个 AABB |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0029，系统 `movement`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0029，系统 `movement`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
trace(start,end) → 遍历 29 个 box → 若 delta.z<0 则按 -116 截断
```

## 10. 第一条未闭合调用边

**mp_firingrange 的 cbrush_t(36B)/brushBounds(24B)/brushContents(4B) 表位置。**

## 11. 已确认事实

- -116 是常数不是算出来的（18404 帧 z 恒 -116）
- coop 层零地板面
- mp_firingrange 有 1104 朝上平面

## 12. 尚未确认的假设

- mp_firingrange brush 表布局

## 13. 已排除的假设

- '地板在 -128..-124'——HANDOFF §9 已用 clipmap 数据否证

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-26 | 提取 mp_firingrange plane/brushside 表 | 成功；brush 表未完成 |

## 15. 当前代码状态

常数平面仍在。

## 16. 最小复现条件

probe_world_damage：从 (48,-572,-50) 向下 trace，看是否停在 -116。

## 17. 最小验证实验

**实验 B29**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 用已解出的 plane/brushside 表 + 反推的 brush 边界，生成完整 clipmap<br>2. 替换 codol_clipmap_coop_train.inc，重跑 probe_world_damage |
| 通过判据 | trace 落在真实 brush 面上而非 -116 |
| 失败判据 | 仍落到 -116 ⇒ brush 表仍不对 |
| 成本 | 离线数小时 |

## 18. 条件式修复方案

**方案A：完成 mp_firingrange brush 表定位（用 brushContents/brushBounds 反向约束）。**

**方案B：短期用 plane 表做无限平面集合（忽略 brush 边界）。**

## 19. 修改影响分析

决定移动/命中/出生是否有物理基础。

## 20. 可测量的验收标准

1. 任意出生点下方有真实地板面，trace 落到地图几何上。

## 21. 回归测试方案

probe_world_damage 的 fraction/normal 与手算一致。

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 CODOL-ISSUE-0087。
- **上游依赖**：`CODOL-ISSUE-0022`, `CODOL-ISSUE-0087`

---