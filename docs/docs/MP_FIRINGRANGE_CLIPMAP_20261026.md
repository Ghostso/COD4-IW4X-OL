# mp_firingrange 完整 clipmap 提取成功

日期：2026-10-26
参照：**IW4X** `IW4X\iw4x-client\src\Components\Modules\AssetInterfaces\IclipMap_t.cpp`
      + `Game\Structs.hpp`（权威实现，优先级见 AGENTS.md）

## 背景

一直在跑的 `coop_train_mp_firingrange` 是**精简训练关**，其 zone 里只有 27 个平面、
29 个 brush，且**出生点 (48,-572) 完全落在所有碰撞体覆盖范围之外** ——
这是"人物悬空/穿墙/卡住"的根因，服务端写死 `z=-116` 也是因为确实没有地板数据。

用户提示：**coop 关复用了对战版靶场的资产**（`"model" "mp_firingrange_tire_wall"`），
且游戏本身是 IW4 引擎，应参照 IW4X。

## IW4X 的 clipmap 结构（权威定义）

```c
AssertSize(Game::clipMap_t, 256);
struct cplane_s      { float normal[3]; float dist; u8 type; u8 pad[3]; };  // 20B
struct cbrushside_t  { cplane_s* plane; u16 materialNum; i8 fadj; i8 ecnt; }; // 8B
struct cbrush_t      { u16 numsides; u16 glassPieceIndex; cbrushside_t* sides;
                       u8* baseAdjacentSide; u16 axialMaterialNum[2][3];
                       u8 firstAdjacentSideOffsets[2][3]; u8 edgeCount[2][3]; }; // 36B
struct Bounds        { float midPoint[3]; float halfSize[3]; };              // 24B
```

关键：`cbrush_t` 自带 `axialMaterialNum[2][3]` —— 轴向 6 面由 brush 自身描述，
平面上只存非轴向（斜面/斜面地板）。

## 提取结果（mp_firingrange_zone.bin, 57,940,660 B）

| 结构 | 位置 | 数量 |
|---|---|---|
| plane 表 | **5,001,523 .. 5,153,263** | **7,587**（20B/项） |
| brushside 表 | **42,720,480** | **18,770**（8B/项） |
| 材质字符串表 | 42,716,679 .. 42,720,473 | 285 项 |

**指针映射 delta = `0x2FE4FC1E`**
（`plane_ptr = DELTA + file_offset`）

### 验证

```
brushside 指针解析：失败 0 / 18770   ← 100% 全部正确
最大平面索引      ：7577 / 7587
```

### 地板找到了

```
平面法线 |z| > 0.5 的：2015 项
其中朝上 (z > 0.5)：1104 项      ← 这些就是真实地板
```

**coop 版的 27 个平面全部 `normal.z = 0`（纯垂直墙），一项地板都没有。**
`mp_firingrange` 有 1104 个朝上的平面 —— 这才是可以支撑玩家站立的几何。

## 与 coop_train 的对比

| | coop_train | mp_firingrange |
|---|---|---|
| zone 大小 | 6.3 MB | 57.9 MB |
| `ncs_*_level` 资产分类 | 0 | 20 |
| 材质表 | 4 项 | 285 项 |
| script_brushmodel | 29 | 70 |
| brushside | 27 | **18,770** |
| plane | 27 | **7,587** |
| 朝上平面（地板） | **0** | **1,104** |

## 工具

- `tools/export_mp_firingrange_clipmap.py` — 提取器（planes/sides 已完成，
  brush 表定位进行中：候选过多，需用 brushContents/brushBounds 反向约束）
- `tools/_verify_mp_planes.py` — 平面表与指针映射验证（全绿）

## 下一步

1. 定位 `cbrush_t` (36B) 与 `brushBounds` (24B) / `brushContents` (4B) 表
2. 生成包含 18770 个 brushside 的完整碰撞数据
3. 替换服务端 `codol_clipmap_coop_train.inc`（29 个近似 AABB）为真实几何
4. 服务端碰撞 trace 改用真实 clipmap，不再依赖 `z = -116` 常数平面
