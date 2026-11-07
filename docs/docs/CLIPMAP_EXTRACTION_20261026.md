# 地图碰撞几何提取 — 结论报告

日期：2026-10-26
目的：解决 C 战斗服"人物悬空/穿墙/卡住"的根因——服务端没有真实地图碰撞。

## 结论摘要

**手头所有已解包资产里，都不存在完整的地图碰撞几何。**
服务端写死 `z = -116` 不是因为偷懒，而是数据里确实没有地板可算。

## 已查证的文件

| 文件 | 大小 | `IBSP` | `d3dbsp` | clipmap 标记 | material blob |
|---|---|---|---|---|---|
| `coop_train_zone.bin`（当前跑的地图） | 6.3 MB | 0 | 0 | 0 | ✅ 有 |
| `mp_firingrange_zone.bin`（对战版靶场） | 57.9 MB | 1（version 非法） | 0 | 0 | ❌ 无 |
| `common_mp.zone`（共享资产） | 107.7 MB | 0 | 0 | 0 | — |

`mp_firingrange_zone.bin` 里唯一的 `IBSP` 在偏移 30,854,846，其 `version=1179472203`
是非法值，且随后 lump 表全是乱数 —— 不是真实 BSP 头部。
`maps/mp/mp_firingrange.d3dbsp` 只是资产名字符串（偏移 3,694,392）。

## 已成功提取的内容（coop_train）

`tools/export_clipmap_zone.py` 能完整导出 clipmap 结构：

- **30 个 brush**，`brush[0]` 是世界自身，其余 29 个挂在 `script_brushmodel` 实体
- **27 个平面**，`normal.z` 全部为 0.000（纯垂直面）
- **27 个 brushside**
- 完整布局：header=2356580, planes=2356644, materials=2357184, sides=2357275,
  brushes=2358355, bounds=2359435, contents=2360155

### 关键：没有"漏掉地板"

对照 CoD4X `cm_load_obj.cpp`：

```c
unsigned int outnumsides = numinsides - 6 * brushcount;
outBrush->numsides = inBrush->numSides - 6;
```

**轴向的 6 个面是引擎隐含、不存盘的。** 我们导出的 `bounds.mid/half`
（AABB）恰好就是这 6 个隐含面构成的盒子。所以：

- 27 个平面只是"斜面"（倾斜墙）
- 每个 brush 的实体区域（AABB）是**完整已知**的
- `normal.z 全为 0` 是**正常的**，不是数据缺失

## 真正的问题：覆盖范围

```
brush[0] 世界    :  x[-88, 88]     y[-112, 112]    z[-112, 111]
出生点            :  x=48           y=-572           z=-116
29 个实体 brush   :  x -824..-177
```

**出生点 (48, -572) 的 y 坐标完全落在所有碰撞体之外。**
玩家出生在一片没有任何碰撞体覆盖的区域 —— 这就是穿墙/悬空的直接原因。

coop 训练关的碰撞是"稀疏的 clip 体积"（cqb_prone_clip、cqb_crouch_clip 等
按用途命名的小块），不是封闭的世界几何。

## 对服务端路线的含义

1. 服务端**无法**用现有数据算出玩家真实 z（没有地板面）
2. 服务端也**无法**阻止穿墙（出生点周围无碰撞体）
3. 先前几轮反复调"发不发位置"全部无效，因为服务端根本没有可信位置可发

## 待确认的下一步

- **路线 A**：换到 `mp_firingrange`（对战版，70 个 brushmodel）。但它的 zone 布局与
  coop 不同（material blob 找不到），需要先逆向它的组织方式。
- **路线 B**：接受服务端无碰撞，改"客户端权威"，另找办法让客户端出生在正确位置。

## 工具

- `tools/export_clipmap_zone.py` — 现有 clipmap 导出器（只导出实体 brush，跳过 brush[0]）
- `tools/_analyze_clipmap_brushes.py` — 本次新增，按 CoD4X 规则核对 brush 完整性
- `fixtures/coop_train_clipmap_20261023.json` — 完整结构（含 27 平面、30 brush、27 side）
