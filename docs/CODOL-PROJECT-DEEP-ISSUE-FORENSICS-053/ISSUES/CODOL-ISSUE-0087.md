# CODOL-ISSUE-0087 — layer-2 世界资产（CLIPMAP_MP / MAP_ENTS / ComWorld）从未导出

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

FF 容器已解出 block-0 布局，但 layer-2 世界资产从未导出；mp_firingrange 的 cbrush_t 表未定位。

## 2. 历史首次发现过程

- **首次发现**：2026-10-21（`THIRD_ROUND_PREREQUISITES.md R3-A07`）
- **最近验证**：2026-10-29
- **所属系统**：`map`　**优先级**：P1　**登记状态**：`NOT_IMPLEMENTED`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-26 | MP_FIRINGRANGE_CLIPMAP 解出 plane(7587)/brushside(18770) | brush 表未完成 |
| 2026-10-29 | 无进展 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0087-01 | source | `—` | — | 资产提取工具 | — |
| EV-0087-02 | location | `tools/export_mp_firingrange_clipmap.py` | — | plane/sides 已完成 | — |
| EV-0087-03 | location | `include/codol_clipmap_coop_train.inc` | — | 当前唯一可用的 29 个 box | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

`NOT_APPLICABLE` — 该问题不在本仓库源码内（客户端二进制 / 环境 / 文档问题）。

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `tools/export_mp_firingrange_clipmap.py` | — | plane/sides 已完成 |
| `include/codol_clipmap_coop_train.inc` | — | 当前唯一可用的 29 个 box |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0087，系统 `map`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0087，系统 `map`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
.ff (block-0) → layer-2 资产 → clipmap / map_ents
```

## 10. 第一条未闭合调用边

**cbrush_t(36B) / brushBounds(24B) / brushContents(4B) 的表位置。**

## 11. 已确认事实

- mp_firingrange 有 1104 个朝上平面
- brushside 指针解析 18770/18770 全对（delta 0x2FE4FC1E）

## 12. 尚未确认的假设

- brush 表布局

## 13. 已排除的假设

- 'IBSP 头可用'——mp_firingrange_zone.bin 里那个 IBSP version 非法

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-26 | 提取 plane/brushside | 成功 |

## 15. 当前代码状态

不适用。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B87**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 用 brushContents/brushBounds 反向约束 brush 表位置<br>2. 导出后与已知 1104 个朝上平面交叉验证 |
| 通过判据 | brush 数与材质表可对齐 |
| 失败判据 | 约束不唯一 |
| 成本 | 离线数小时 |

## 18. 条件式修复方案

**方案A：完成 brush 表定位并生成完整 clipmap。**

**方案B：先用 plane 表做近似碰撞。**

## 19. 修改影响分析

决定真实地图几何能否使用（支撑 0022/0029）。

## 20. 可测量的验收标准

1. mp_firingrange 的完整 clipmap 可导出并用于 trace。

## 21. 回归测试方案

导出物附哈希与平面/brush 计数。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B87：brush 表定位。
- **上游依赖**：`CODOL-ISSUE-0029`

---