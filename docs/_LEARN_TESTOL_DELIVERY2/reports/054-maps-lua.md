# 学习报告 054（重开）— `maps\` 19 个 Lua 逐字节

**学习范围**：`payload\Ayria\Assets\OlMod\GameScripts\maps\`（19 个文件）
**方法**：逐字节读入 + 换行/BOM 检测 + 全文内容
**性质**：全实测
**★★★ 本报告收录**`zm_factory_sh.lua` 的引擎契约警告**（"不要用编造材质名来修它"）

---

## 一、★★★★★ 18 个小文件（58–67 字节）—— 全是同一形态

| 文件 | 字节 | 内容 |
|---|---|---|
| `mp_arkaden_sh.lua` | **63** | `compass_map_mp_arkaden_sh` |
| `mp_backlot_sh.lua` | **63** | `compass_map_mp_backlot_sh` |
| **`mp_crash_tropical.lua`** | **62** | ★★ **`compass_map_mp_crash_dlc`**（**不是** `_crash_tropical`！） |
| `mp_derail_sh.lua` | 62 | `compass_map_mp_derail_sh` |
| `mp_fallen_sh.lua` | 62 | `compass_map_mp_fallen_sh` |
| `mp_foundation_sh.lua` | 66 | `compass_map_mp_foundation_sh` |
| `mp_interchange_sh.lua` | 67 | `compass_map_mp_interchange_sh` |
| `mp_lockdown_sh.lua` | 64 | `compass_map_mp_lockdown_sh` |
| `mp_lookout_sh.lua` | 63 | `compass_map_mp_lookout_sh` |
| `mp_mission_sh.lua` | 63 | `compass_map_mp_mission_sh` |
| `mp_nuked.lua` | **58** | `compass_map_mp_nuked` |
| `mp_offshore.lua` | 61 | `compass_map_mp_offshore` |
| **`mp_overwatch_sh.lua`** | **58** | ★★ **`compass_map_mp_ov_02`**（**不是** `_overwatch_sh`！） |
| `mp_showdown.lua` | 61 | `compass_map_mp_showdown` |
| `mp_tunisia.lua` | 60 | `compass_map_mp_tunisia` |
| `mp_underground_sh.lua` | 67 | `compass_map_mp_underground_sh` |
| `mp_wasteland_sh.lua` | 65 | `compass_map_mp_wasteland_sh` |

### ★★★ 统一的模板

```lua
return {
    minimap_material = "compass_map_<地图名>",
}
```

★★ **⇒ 18 个文件全部是这个 3 行模板（LF 换行，无 BOM）。**

### ★★★★★ 两处**名字不一致**（重要发现）

| 文件 | 文件里的材质名 | 是否 = `compass_map_<文件名去 .lua>` |
|---|---|---|
| **`mp_crash_tropical.lua`** | **`compass_map_mp_crash_dlc`** | ★★ **否**（应为 `_crash_tropical`） |
| **`mp_overwatch_sh.lua`** | **`compass_map_mp_ov_02`** | ★★ **否**（应为 `_overwatch_sh`） |

★★★ **⇒ 这两个材质名是**真实发布文件的名字**（不是按文件名推导的）：**
```
mp_crash_tropical  →  实际材质是 "compass_map_mp_crash_dlc"
mp_overwatch_sh    →  实际材质是 "compass_map_mp_ov_02"
```

★ **⇒ 说明作者是**从真实数据抄的**（否则会按文件名推导）。**

★★ **⇒ 这也是**一个潜在陷阱**：如果按文件名推导，这两个地图的小地图会失效。**

---

## 二、★★★★★ `zm_factory_sh.lua`（1,590 字节 / 25 行）—— 完整契约

### 2.1 ★★★ 完整内容（逐字）

```lua
-- zm_factory_sh -- the zombies map this server is being brought up on.
--
-- NO minimap_material, and that is MEASURED rather than an omission. All three retail
-- zm_factory_sh captures in `zombie demos\` carry no compass configstring whatsoever,
-- while the retail dm gamestate does (`2555 "compass_map_mp_cross_fire" 8288 1280 640
-- -6368`). Zombies maps do not use the MP compass. out.exe agrees: its only
-- compass_map_* string is `compass_map_awareness_radar` @ 0xDB1D0C -- the per-map
-- materials live in fastfiles, and there is no zombies one to name.
--
-- The table itself IS required even though it is empty. SV_LoadMapScriptMetadata must
-- return a value, because Appmain.cpp fails session configuration outright when
-- `mapScriptExists != mapMetadata.has_value()`. An empty table satisfies that; a script
-- that returns nothing, or no script at all, does not.
--
-- KNOWN CONSEQUENCE, NOT AN OVERSIGHT: Appmain.cpp only reads the map entity string
-- inside `if (mapMetadata && mapMetadata->miniMapMaterial)`, so leaving this nil also
-- skips spawn-point loading, and the session then dies on
-- `initial_spawn_ground_trace` / `NO_SPAWN_POINT`. That coupling is an MP-only
-- assumption -- a compass and a spawn list have nothing to do with each other -- and
-- decoupling them is what zombies needs from the engine side. Do NOT "fix" this by
-- inventing a material name here; that would trade a clean failure for a wrong one.
--
-- Retail spawn origin for this map, from the demos and byte-identical across all three:
--     -73.000000 -54.000000 8.000000
return {}
```

### 2.2 ★★★★★ 三段完整论证

#### 段 1：为什么**没有** `minimap_material`（第 2–8 行）

```
NO minimap_material, and that is MEASURED rather than an omission.
All three retail zm_factory_sh captures in `zombie demos\` carry no compass configstring
whatsoever, while the retail dm gamestate does
(`2555 "compass_map_mp_cross_fire" 8288 1280 640 -6368`).
Zombies maps do not use the MP compass.
out.exe agrees: its only compass_map_* string is `compass_map_awareness_radar` @ 0xDB1D0C
-- the per-map materials live in fastfiles, and there is no zombies one to name.
```

★★★ **⇒ 三条独立证据：**
```
① 三份零售 zm_factory_sh 抓包**都没有** compass configstring
② 而零售 dm 有：`2555 "compass_map_mp_cross_fire" 8288 1280 640 -6368`
③ ★ exe 里唯一的 `compass_map_*` 串是 **`compass_map_awareness_radar` @ 0xDB1D0C**
```

★★ **⇒ 第 ② 条给出了**完整的 dm compass configstring 实例**：**
```
2555 "compass_map_mp_cross_fire" 8288 1280 640 -6368
     ↑ 材质名                   ↑ 四个数值（可能是 x/y/w/h）
```

★★★ **⇒ 第 ③ 条给出**精确地址 `0xDB1D0C`**（exe 里唯一的 compass 串）。**

#### 段 2：为什么**空表也必须返回**（第 10–14 行）

```
The table itself IS required even though it is empty.
SV_LoadMapScriptMetadata must return a value,
because Appmain.cpp fails session configuration outright when
`mapScriptExists != mapMetadata.has_value()`.
An empty table satisfies that; a script that returns nothing, or no script at all, does not.
```

★★★ **⇒ 精确的引擎条件：**
```cpp
// Appmain.cpp
if (mapScriptExists != mapMetadata.has_value()) {
    // ★ session configuration 直接失败
}
```

★★ **⇒ 所以：**
```
返回空表 {}  ⇒  has_value() == true  ⇒  通过 ✓
返回 nil     ⇒  has_value() == false ⇒  ★ 失败
没有脚本      ⇒  ★ 失败
```

#### 段 3：★★★ **已知后果，不是疏忽**（第 16–22 行，逐字）

```
KNOWN CONSEQUENCE, NOT AN OVERSIGHT: Appmain.cpp only reads the map entity string
inside `if (mapMetadata && mapMetadata->miniMapMaterial)`, so leaving this nil also
skips spawn-point loading, and the session then dies on
`initial_spawn_ground_trace` / `NO_SPAWN_POINT`. That coupling is an MP-only
assumption -- a compass and a spawn list have nothing to do with each other -- and
decoupling them is what zombies needs from the engine side. Do NOT "fix" this by
inventing a material name here; that would trade a clean failure for a wrong one.
```

★★★★★ **⇒ 这是全包**最重要的一段工程警告**：**

```
Appmain.cpp 只在
    if (mapMetadata && mapMetadata->miniMapMaterial)
内部读取地图实体字符串
        ↓
★ 所以留空（nil）也会**跳过 spawn-point 加载**
        ↓
session 死于 **`initial_spawn_ground_trace` / `NO_SPAWN_POINT`**
        ↓
★★★ 这个耦合是 **MP-only 假设** —— 罗盘与出生点列表**毫无关系**
        ↓
解耦是 zombies 需要引擎侧做的事
        ↓
★★★★★ **Do NOT "fix" this by inventing a material name here;
        that would trade a clean failure for a wrong one.**
```

★★★ **⇒ "不要用编造材质名来'修'它；那会用一次**错误的**成功换掉一次**干净的**失败。"**

★ **⇒ 这是**极其重要的工程哲学**：**
```
编造材质名 ⇒ 通过 has_value() 检查 ⇒ spawn 加载开始
        ↓
但材质名是假的 ⇒ 罗盘渲染错误
        ↓
★★★ **用一个新的错误换掉一个已知的失败**
```

★★ **⇒ 正确做法：在**引擎侧解耦**（`Appmain.cpp` 的条件判断）。**

### 2.3 ★★★ 零售出生点（第 24–25 行）

```
Retail spawn origin for this map, from the demos and byte-identical across all three:
    -73.000000 -54.000000 8.000000
```

★★★ **⇒ 精确的出生点坐标：**
```
x = -73.0
y = -54.0
z = 8.0
```

★★ **⇒ 且"三份 demo 逐字节相同"。**

★ **⇒ 这与记忆里的 `pos_z = -116`（另一张图）**不同** —— 说明**每张图的出生点不同**。**

---

## 三、★★★★ `coop_training_mp_cargoship.lua`（201,269 字节 / 4,683 行）

### 3.1 ★★★ 头部（已在报告 009 详述）

```lua
-- Wetwork / "Unidentified".
-- 七个阶段：bridge / deck / quarters / hallways / cargo holds / sinking escape / helicopter extraction
-- if codol == nil then return {} end
```

### 3.2 ★★★ 新增发现：`campaign_weapon_definitions`（第 30 行起）

```lua
local campaign_weapon_definitions = {
    [1192] = "** 854 0 0 6747 9321 6825",
    [1195] = "** 730 0 0 9930 6747 9321 6690 6825",
    [1197] = "** 992 0 0 6206 9321",
    [1198] = "** 78 0 0 9930 2795 2592 6747 9321 6690 8738 6825",
    [1201] = "** 1106 0 0 6945 9321 6747 6825",
    [1203] = "** 1155 0 0",
    [1208] = "** 41 0 0 9930 1676 6690 8738 6747 9321 10545",
    [1211] = "** 41 0 0 9930 4170 6690 8738 6747 9321 10545",
    [1212] = "** 22 0 0 15297 652 5414 6690 8738 9321 ...
```

★★★ **⇒ 这是一个**武器定义表**，key 是武器号（1192/1195/1197/...），**
**value 是**编码字符串**（`** <数字> 0 0 <更多数字>`）。**

★ **⇒ 格式 `** N 0 0 M1 M2 ...` —— 可能是**武器属性的紧凑编码**。**

★★ **⇒ 数字如 `9321`/`6825`/`6690`/`8738` 反复出现 ⇒ 是**属性 ID**（如 `9321` = 某类附件）。**

### 3.3 ★★ 文件规模

```
201,269 字节 / 4,683 行（LF 换行，无 BOM）
        ↓
平均每行 **43 字节**
        ↓
★ 绝大部分是**数据表**（武器定义 + 阶段触发）
```

---

## 四、★★★ 19 个 map lua 的完整统计

| 类别 | 数量 | 字节范围 |
|---|---|---|
| **单行材质声明** | **17** | **58–67** |
| ★ **特殊材质名** | **2** | 62（`crash_dlc`）/ 58（`ov_02`） |
| ★★★ **空表 + 契约说明** | **1** | **1,590**（`zm_factory_sh`） |
| ★★ **战役地图（大数据）** | **1** | **201,269**（`coop_training_mp_cargoship`） |
| **合计** | **19** | |

★★ **⇒ 全部 **LF 换行、无 BOM**。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 17 个小文件模板 | `return { minimap_material = "compass_map_<名>", }` |
| 2 | ★★ 换行 | **全部 LF，无 BOM** |
| 3 | ★★★★★ **名字不一致 1** | **`mp_crash_tropical.lua`** → **`compass_map_mp_crash_dlc`** |
| 4 | ★★★★★ **名字不一致 2** | **`mp_overwatch_sh.lua`** → **`compass_map_mp_ov_02`** |
| 5 | ★★★ 说明 | 材质名是**从真实数据抄的**（非按文件名推导） |
| 6 | ★★★★★ `zm_factory_sh` | **1,590 字节 / 25 行**，**返回空表 `{}`** |
| 7 | ★★ 证据 1 | 三份零售抓包**都没有** compass configstring |
| 8 | ★★ 证据 2 | 零售 dm 有 **`2555 "compass_map_mp_cross_fire" 8288 1280 640 -6368`** |
| 9 | ★★★ 证据 3 | exe 里唯一 compass 串是 **`compass_map_awareness_radar` @ `0xDB1D0C`** |
| 10 | ★★★ 引擎条件 | `mapScriptExists != mapMetadata.has_value()` ⇒ **失败** |
| 11 | ★★★★ 已知后果 | 留空 ⇒ **跳过 spawn 加载** ⇒ 死于 **`initial_spawn_ground_trace` / `NO_SPAWN_POINT`** |
| 12 | ★★★★★ **工程警告** | **"Do NOT fix this by inventing a material name; that would trade a clean failure for a wrong one."** |
| 13 | ★★★ 零售出生点 | **`-73.0 -54.0 8.0`** |
| 14 | ★★ `coop_training` 规模 | **201,269 字节 / 4,683 行** |
| 15 | ★ 新增发现 | **`campaign_weapon_definitions`**（武器号 → 编码串） |

---

## 六、结论

### 1. ★★★★★ **两处材质名与文件名不一致**（`crash_dlc` / `ov_02`）

★ **⇒ 证明材质名是**从真实数据抄的**，不是按文件名推导。**

★★ **⇒ 按文件名推导会让这两张图的小地图失效。**

### 2. ★★★★★ **`zm_factory_sh.lua` 的"不要编造材质名"是核心工程警告**

```
编造材质名 ⇒ 通过 has_value() ⇒ spawn 加载开始 ⇒ 但材质是假的
        ↓
★★★ **用一次错误换掉一次干净的失败**
```

★ **⇒ 正确做法：在引擎侧解耦罗盘与出生点。**

### 3. ★★★ **exe 里唯一 compass 串是 `compass_map_awareness_radar` @ `0xDB1D0C`**

### 4. ★★★ **零售 dm 的 compass configstring 格式**：`<id> "<材质名>" <x> <y> <w> <h>`

### 5. ★★ **`coop_training` 的 201 KB 主要是 `campaign_weapon_definitions` 数据表**

---

## 七、下一步

- `payload\` **`MarketplaceSkus.json`（2.5 MB）结构**
- `payload\` **`configs_s.info` 剩余节**（已读 82 节名，未读全部内容）
- `source\` 结构与关键文档
