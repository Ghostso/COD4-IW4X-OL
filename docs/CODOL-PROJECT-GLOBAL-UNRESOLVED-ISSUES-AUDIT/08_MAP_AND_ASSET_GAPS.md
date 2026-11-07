# 08 — 地图与资源缺口（IIPS / IFS / Fastfile / Clipmap）

---

## 1. 资源容器现状

| 容器 | 数量/大小 | 状态 |
|---|---|---|
| `.ifs` | 974 个 | 头部/清单/尾部已逆向；**载荷加密**（971/974） |
| `.ff`（Fastfile） | 多份 | `mp_firingrange.ff` 31,332,485 B；`ui_mp.ff` 29,224,001 B **整体加密** |
| `.zone`（解包产物） | `coop_train_zone.bin` 6.3 MB；`mp_firingrange_zone.bin` 57.9 MB；`common_mp.zone` 107.7 MB | 已解出 |

### 1.1 Fastfile 版本不匹配
`ui_mp.ff` 头部 `IWff0100` + version=461，现有加载工具不认这个版本。
→ 见 `docs/UI_FF_ENCRYPTED_20261028.md`。

### 1.2 `.ifs` 载荷加密
项目既有结论：971/974 的载荷是加密（不是压缩）。
→ 意味着**地图几何不能从 `.ifs` 里现取**，只能依赖已解包的 `.zone`。

---

## 2. Clipmap（碰撞几何）

### 2.1 coop_train（当前唯一在用的图）

```
zone 大小      6.3 MB
平面           27 个，normal.z 全为 0（纯垂直墙）
brush          30（brush[0] 是世界自身）
brushside      27
朝上平面       0          ← 没有地板
script_brushmodel 29
覆盖范围       x -824..-177；出生点 (48,-572) 在所有碰撞体之外
```

**结论**：coop_train 的碰撞是"稀疏 clip 体积"，不是封闭世界几何。
服务端写死 `z = -116` 是因为数据里确实没有地板可算。

> 注意：`normal.z 全为 0` **不是数据缺失**。按 CoD4X `cm_load_obj.cpp`，
> 轴向 6 面由引擎隐含、不存盘；每个 brush 的 AABB 是完整已知的。
> 问题在**覆盖范围**，不在平面数据。

### 2.2 mp_firingrange（对战版靶场，已部分解出）

```
zone 大小      57.9 MB
plane 表       5,001,523 .. 5,153,263（7,587 项 × 20 B）
brushside 表   42,720,480（18,770 项 × 8 B）
材质字符串表   42,716,679 .. 42,720,473（285 项）
指针 delta     0x2FE4FC1E（plane_ptr = DELTA + file_offset）
验证           brushside 指针解析 失败 0 / 18770；最大平面索引 7577/7587
朝上平面       1104 个（真实地板）
```

**未完成**：`cbrush_t`(36 B) / `brushBounds`(24 B) / `brushContents`(4 B) 表位置。
报告自述"候选过多，需用 brushContents/brushBounds 反向约束"。

→ **ISSUE-0029 的修复前提就是这个**。

### 2.3 mp_raid（当前大厅选中的图）

- 本地有资源（10-28 日志：`playlist=50 命中本地可用图 mp_raid`）
- **但没有任何 clipmap 提取**
- 服务端加载 `--map mp_raid` 时用的是 coop_train 的 29 个碰撞体（本次审计确认）

→ ISSUE-0022。

---

## 3. 地图实体表（MAP_ENTS）

`include/codol_mapents_coop_train.inc`：334 条，由 `tools/gen_mapents_inc.py`
从 `_map_extract/coop_train_entities.txt` 生成。

| 类型 | 数量 | 说明 |
|---|---|---|
| `script_model` / `script_struct` / `script_origin` | 333 | 纯装饰（轮胎墙、折叠桌、软木板…） |
| `script_brushmodel` | 29 | 已并入 clipmap，不重复生成 |
| `trigger_*` | 16 | 触发体，非实体 |
| `actor_ally_hero_quartermaster_so` | **1** | 这张图唯一的 actor，(-80,-384,-124)，血量 100 |

**关键**：用户报"训练模式没有 BOT"**不是配置问题**，是这张图就这么设计的（ISSUE-0068）。
要演一遍战斗结算必须换图。

**缺口**：
- 表里没有 `model_index`（只有模型名字符串）⇒ 服务端无法给客户端发模型引用（ISSUE-0024）
- 没有 mins/maxs（用"人形大小"占位：-16..16 × 0..64）
- 只有 coop_train 一张图的表

---

## 4. 出生点

| 来源 | 值 | 状态 |
|---|---|---|
| coop 附加层 `info_player_start_so` | (48, -572, -116) | **这张图唯一的设计出生点**，但在所有碰撞体之外 |
| 基础图 `mp_firingrange` zone | 50 个 spawn，z ∈ -88..0 | 已挖出存档（`HANDOFF_20261025_BINARY_BISECT.md §11.2`） |
| 服务端常量 | `codol_ground_z = -116` | 写死的无限平面 |

**三种"出生点"并存**：
1. 客户端 `info_player_start_so` = (48,-572,-116)
2. 服务端 `codol_player_init(48,-572,-116)`（`battle_service.c:170`）
3. 服务端 `codol_world_spawn_player` 里又是字面量 `(48,-572,-116)`（`world.c:128`）

三处相同但**没有共享常量**（ISSUE-0036 类）。

**根本问题**：服务端推不动客户端位置（ISSUE-0025），所以这些值对客户端没有影响。

---

## 5. 资源相关的未解问题清单

| # | 问题 | Issue |
|---|---|---|
| 1 | `mp_firingrange` 的 cbrush_t/brushBounds/brushContents 表位置 | ISSUE-0029 |
| 2 | `mp_raid` 无任何 clipmap 提取 | ISSUE-0022 |
| 3 | `ui_mp.ff` 加密 + 版本 461 不被工具识别 | ISSUE-0046 |
| 4 | `.ifs` 载荷加密（971/974） | — |
| 5 | 实体表只有一张图，且无模型索引 | ISSUE-0024 |
| 6 | `export_clipmap_zone.py` 写死 `coop_train_zone.bin`（PLANE_DELTA 是该 zone 的重定位常数），换图会 fail closed | `HANDOFF_20261025_BINARY_BISECT.md §11.2` |
| 7 | 出生点表在"基础图"与"coop 附加层"两份里，不能混用 | 同上 |
| 8 | `mp_firingrange_zone.bin` 里唯一的 `IBSP` 在 30,854,846 偏移，version 非法（1179472203），不是真实 BSP 头 | `docs/CLIPMAP_EXTRACTION_20261026.md` |

---

## 6. 结论

**当前项目能用的地图碰撞只有一张：coop_train 的 29 个稀疏 clip 体积，且没有地板。**

要让"人物站得住"这条链真实成立，必须完成 `mp_firingrange` 的 brush 表定位
（那是目前唯一已经验证出 1104 个朝上平面的图）。

在此之前：
- 服务端任何"地面"都是 `z = -116` 的常数
- 任何换图（`--map mp_raid`）都不会改变碰撞
- 任何"出生点修复"都会被 ISSUE-0025 抵消
