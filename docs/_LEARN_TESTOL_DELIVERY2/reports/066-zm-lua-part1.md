# 学习报告 066（重开）— `zm.lua` 前段（1–134 行）：zone 模型与致命实验

**学习范围**：`payload\Ayria\Assets\OlMod\GameScripts\gametypes\zm.lua`（37,359 B / 735 行）第 1–134 行
**性质**：全实测（**最大的 gametype**）
**★★★ 本报告收录**一次"写 configstring 直接杀死客户端"的完整实验**与**僵尸 zone 模型的四张地图数据**

---

## 一、★★★★★ 一个**致命的实验**（第 62–79 行，逐字）

```lua
-- DISABLED, AND THE RESULT IS THE POINT: publishing this configstring KILLS THE
-- CLIENT. Measured 2026-09-02 00:40 --
--     actor model PUBLISHED index=308 cs=2876 name=c_zom_ger_body1
--     zm actor model precached c_zom_ger_body1
--     clients=1 active=1 snapshots=139   then   client timeout client=0
-- The client connected AFTER the publish, ran ~15 s and timed out.
--
-- This was the careful version: the configstring ALONE, no `|` precache, at script
-- load rather than at spawn. So neither the precache command nor the timing is the
-- cause -- writing cs 2876 is by itself fatal. Both earlier theories (12.21, 12.22)
-- are therefore wrong, and the remaining suspects are the INDEX (308 is the
-- dedicated band's, and may simply not be the client's slot for this model) and
-- SV_SetConfigString into the model band at all.
--
-- The builtin stays registered and works; only this call is off. Re-enable it when
-- there is a reason to believe the index, not before.
-- local precached, precache_error, precache_code =
--     codol.call("function:precachemodel", zm_actor_model)
```

### ★★★★★ 完整的实验记录

| 项 | 值 |
|---|---|
| **时间** | **2026-09-02 00:40** |
| **操作** | 发布 configstring **index=308 / cs=2876 / name=`c_zom_ger_body1`** |
| **随后** | `zm actor model precached c_zom_ger_body1` |
| **状态** | `clients=1 active=1 snapshots=139` |
| **★ 然后** | ★★★ **`client timeout client=0`** |
| **★ 存活** | **~15 秒后超时** |

### ★★★★★ 三个被逐一排除的假设

```
① "precache 命令导致的"
   ⇒ 排除：本次**只用 configstring，没有 `|` precache**
② "时机导致的（spawn 时）"
   ⇒ 排除：本次在**脚本加载时**（不是 spawn 时）
③ "客户端在 publish 之前就连上了"
   ⇒ 排除：客户端在 publish **之后**才连上
        ↓
★★★ **结论：写 cs 2876 本身就足以致命**
```

★★★ **⇒ 这是**极其严谨的排除法**（三个假设逐一证伪）。**

### ★★★★★ 剩余的两个嫌疑（逐字）

```
remaining suspects are
  ① the **INDEX**（308 是 dedicated band 的，可能不是客户端的槽位）
  ② **SV_SetConfigString into the model band at all**（写 model band 本身有问题）
```

★★★ **⇒ 第 ① 条与上一轮报告 008 的"configstring band 缺 index 308"**直接呼应**：**
```
记忆/报告 008：zm.lua 的"僵尸在线但不可见"根因是 **index 308 在客户端 band 里是空的**
        ↓
本报告：**写 cs 2876（index 308）会直接杀死客户端**
        ↓
★★★ **两者指向同一个 index 308**
```

★ **⇒ 而 `cs 2876` 与 `index 308` 的关系：**
```
2876 = 308 + 2568
        ↓
★ 而报告 063（game_server.md）说：主体 configstring **+517**：2037→2554
        ↓
★★ 2876 - 2554 = 322 ？需核对
```

★★ **⇒ 但更可能：`cs 2876` 是**3.19 build 的 index**（3.3.3.3 是另一个值）。**

### ★★★ 三个"earlier theories"（12.21 / 12.22）被推翻

```
"Both earlier theories (12.21, 12.22) are therefore wrong"
```

★ **⇒ 出处：`re/demo-re/` 文档的第 12.21 与 12.22 节。**

---

## 二、★★★★★ 僵尸 zone 模型的**四张地图实测数据**（第 90–95 行，逐字）

```lua
-- The numbers to expect, measured off the shipped maps in
-- re/demo-re/21-zm-zones-and-spawners.md:
--     zm_factory_sh   12 zones / 63 spawn points
--     zm_sumpf_sh     11 zones / 74
--     zm_prototype_sh  3 zones / 41
--     zm_asylum_sh     9 zones / 38
```

### ★★★★★ 四张僵尸地图的精确数据

| 地图 | zones | spawn points |
|---|---|---|
| **`zm_factory_sh`** | **12** | **63** |
| **`zm_sumpf_sh`** | **11** | **74** |
| **`zm_prototype_sh`** | **3** | **41** |
| **`zm_asylum_sh`** | **9** | **38** |

★★★ **⇒ 四张地图，zones 从 3 到 12，spawn points 从 38 到 74。**

★ **⇒ 出处：`re/demo-re/21-zm-zones-and-spawners.md`。**

---

## 三、★★★★ `zm*` 原生 API 的**完整清单**

### 3.1 ★★★ 从第 101–133 行提取的七个 API

| # | API | 签名 |
|---|---|---|
| **1** | **`function:zmzonecount`** | `() → count` |
| **2** | **`function:zmzonename`** | `(zone) → name` |
| **3** | **`function:zmzonespawncount`** | `(zone) → points` |
| **4** | **`function:zmspawnorigin`** | `(zone, point) → {x,y,z}` |
| **5** | **`function:zmspawngoal`** | `(zone, point) → goal` |
| **6** | **`function:zmzoneat`** | `({x,y,z}) → zone_name` |
| **7** | **`function:precachemodel`** | `(model) → ok`（**已禁用**） |

### 3.2 ★★★ 后续出现的（第 256–371 行）

| # | API |
|---|---|
| **8** | `function:zmcooperativezonesource` |
| **9** | `function:zmcooperativespawnzones` |
| **10** | `function:zmplayerzone` |
| **11** | `function:zmplayercount` |
| **12** | `function:zmactivezonecount` |
| **13** | `function:zmzoneactive` |
| **14** | `function:zmzoneadjacentcount` |

### 3.3 ★★★ 后段的（第 552–578 行）

| # | API |
|---|---|
| **15** | （第 552 行的 `codol.call`，需读上下文） |
| **16** | **`function:zmsetround`** |

★★★ **⇒ 至少 **16 个 `zm*` 原生 API** —— 这是**僵尸模式专属的完整 API 面**。**

---

## 四、★★★★★ 一个**极其重要的设计约束**（第 86–88 行，逐字）

```lua
-- INDEX-BASED AND ONE-BASED. A builtin cannot hand Lua a structure -- the value type
-- has no table variant -- so the model is walked with counts and indices instead.
-- Zones are ordered by name, so an index is stable for a given map.
```

### ★★★★★ 三条约束

| # | 约束 | 内容 |
|---|---|---|
| **1** | **INDEX-BASED** | 用计数 + 索引遍历（**不能传结构体**） |
| **2** | ★★★ **原因** | **"A builtin cannot hand Lua a structure -- the value type has no table variant"** |
| **3** | **ONE-BASED** | 索引从 **1** 开始（Lua 惯例） |
| **4** | ★ 稳定性 | **Zones 按名字排序** ⇒ 同一地图的索引**稳定** |

★★★ **⇒ 第 2 条是**跨语言 ABI 的根本限制**：**
```
C++ builtin 的返回值类型**没有 table 变体**
        ↓
★★★ 所以不能返回结构体/数组
        ↓
必须用 **count + index** 逐项查询
```

★ **⇒ 这与报告 065 的 `playfxat` 类型契约**同源**（都是跨语言 ABI 限制）。**

★★ **⇒ 且"Zones 按名字排序"保证**索引稳定**（同一地图每次运行都一样）。**

---

## 五、★★★★★ `zmzoneat` 的**精确验证点**（第 122–132 行）

```lua
-- POINT-IN-ZONE, AGAINST A POINT PREDICTED BEFORE THIS EVER RAN.
-- zm_factory_sh's info_player_start is at (16, 122, 131). Both the exact k-DOP
-- test and the AABB the server actually uses put it in receiver_zone and in NO
-- other zone (re/demo-re/21-zm-zones-and-spawners.md section 21b). Anything else
-- printed here means the bounds resolution is wrong, not that the map is odd.
-- The point is factory-specific; on another map this line is meaningless.
local at = codol.call("function:zmzoneat", {16, 122, 131})
-- EXPECTED: receiver_zone. The volume shapes now come out of MapEnts.trigger
-- exactly, hulls and slab planes included, so this is the true k-DOP answer and
-- not a bounding box. Anything else means the trigger arrays were misread.
print("zm zone at factory info_player_start", at)
```

### ★★★★★ 一个**可预测的验证点**

| 项 | 值 |
|---|---|
| **测试点** | **`(16, 122, 131)`**（`zm_factory_sh` 的 `info_player_start`） |
| **期望结果** | **`receiver_zone`** |
| ★★★ **判据** | **且不在任何其他 zone** |
| ★★ 两种算法一致 | **精确 k-DOP 测试** 与 **服务器实际用的 AABB** |
| ★★★ 失败含义 | **bounds resolution 错了**（不是地图奇怪） |

### ★★★★★ 关键技术说明（逐字）

```
The volume shapes now come out of MapEnts.trigger exactly,
hulls and slab planes included,
so this is the true k-DOP answer and not a bounding box.
Anything else means the trigger arrays were misread.
```

★★★ **⇒ 三个精确的几何概念：**
```
① **MapEnts.trigger** 精确解析
② **hulls + slab planes**（凸包 + 板平面）
③ ★★★ **true k-DOP answer, not a bounding box**
```

★★ **⇒ k-DOP = k-Discrete Oriented Polytope（离散定向多面体）——**比 AABB 精确的碰撞体**。**

★ **⇒ 而"服务器实际用的 AABB"也给出同样答案 ⇒ **两种算法交叉验证**。**

★★★ **⇒ 这是一个**极高质量的验证设计**：**
```
用一个**已知答案**的点（info_player_start）
        ↓
两种独立算法（k-DOP + AABB）都应返回同一个 zone
        ↓
★ 若不一致 ⇒ **trigger 数组被误读**
```

---

## 六、★★★ `zm_actor_head` 与 `zm_actor_model`（第 60–61 行）

```lua
-- alongside it because its default is 1317 and retail clears it. 12.25 / 12.29.
zm_actor_head = "c_zom_ger_head"
```

★★ **⇒ 模型名：**
```
zm_actor_head  = "c_zom_ger_head"
zm_actor_model = "c_zom_ger_body1"（第 64 行提到）
```

★★ **⇒ 且提到"its default is 1317 and retail clears it" —— 某个配置项默认 1317，零售版清零。**

★ **⇒ 出处：`12.25 / 12.29`（`re/demo-re/` 的节号）。**

---

## 七、★★★ `codol_friendly_fire_mode = 0`（第 19 行）

```lua
codol_friendly_fire_mode = 0
```

★★ **⇒ 与报告 065 的 `sd.lua` 一致（都是 0 = 无伤害）。**

★ **⇒ 僵尸是**合作模式**，所以队友无伤害是正确的。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `zm.lua` 行数 | **735**（最大 gametype） |
| 2 | ★★★★★ **致命实验** | 写 **`cs 2876`（index 308）** ⇒ **客户端 15 秒后 timeout** |
| 3 | ★★★ 三个被排除的假设 | precache 命令 / spawn 时机 / 客户端早连 |
| 4 | ★★★ 剩余两嫌疑 | **INDEX 308** 可能不是客户端槽位 / **写 model band 本身有问题** |
| 5 | ★★ 与报告 008 呼应 | 同一 **index 308**（客户端 band 里为空） |
| 6 | ★★ 被推翻的理论 | **12.21 / 12.22** |
| 7 | ★★★★★ **四张地图数据** | factory **12/63** / sumpf **11/74** / prototype **3/41** / asylum **9/38** |
| 8 | ★★★ `zm*` API 数 | **至少 16 个** |
| 9 | ★★★★★ **ABI 限制** | **"value type has no table variant"** ⇒ 必须 count+index |
| 10 | ★ 索引稳定性 | **Zones 按名字排序** |
| 11 | ★★★★★ **验证点** | 点 **`(16, 122, 131)`** ⇒ 期望 **`receiver_zone`** |
| 12 | ★★★ 几何精度 | **true k-DOP**（hulls + slab planes），**不是 bounding box** |
| 13 | ★ 交叉验证 | k-DOP 与 AABB 应一致；不一致 ⇒ **trigger 误读** |
| 14 | ★ 模型名 | `c_zom_ger_head` / `c_zom_ger_body1` |
| 15 | ★ 配置默认 | **1317**，零售版清零（节 `12.25/12.29`） |
| 16 | ★ 友好伤害 | **0**（合作模式） |

---

## 九、结论

### 1. ★★★★★ **"写 cs 2876 直接杀死客户端"** 是极重要的负面发现

★★★ **⇒ 三个假设全部排除 ⇒ 写 model band 本身可能是致命的。**

### 2. ★★★★★ **`zm.lua` 的验证设计极其严谨**

```
已知点 (16,122,131)
        ↓
两种独立算法（k-DOP + AABB）
        ↓
★ 都应返回 receiver_zone
```

### 3. ★★★★ **跨语言 ABI 限制**：builtin 不能返回结构体（无 table 变体）

★ **⇒ 必须 count + index 逐项查询。**

### 4. ★★★ **四张僵尸地图的精确 zone/spawn 数据**已记录

### 5. ★★ **至少 16 个 `zm*` 原生 API**

---

## 十、下一步

- `zm.lua` 剩余（第 134–735 行，约 600 行）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
