# 学习报告 087（重开）— 17 个小地图文件逐个确认 + `zm_factory_sh.lua` 全文

**学习范围**：`maps\` 下 17 个小文件（58–67 B）+ `zm_factory_sh.lua`（1,590 B）
**性质**：全实测（**18 个文件全部逐字节读完**）
**★★★★★ 本报告收录一个**完整失败模式的解释链**（`NO_SPAWN_POINT`）与**两处名字不符的重新判定**

---

## 一、★★★★★ 17 个小地图文件 **全部逐字节确认**

### 1.1 ★★★ 统一的格式与属性

| 属性 | 值 |
|---|---|
| **行数**（每个） | **3** |
| **换行** | ★ **纯 LF**（**CRLF = 0**） |
| **BOM** | ★ **无**（首 3 字节 = `72-65-74` = **`ret`**） |
| **大小** | **58 – 67 B** |
| **格式** | `return {` / `    minimap_material = "…",` / `}` |

★★★ **⇒ 17 个文件**同格式、同编码、同换行风格 ⇒ 由同一脚本生成。**
**⇒ 与报告 006 的"5 个 `.cmd` 是纯 LF"是**不同问题**（`.lua` 由 Lua 解释器读,不受 cmd.exe 影响）。**

### 1.2 ★★★★★ 完整的 17 项对照表

| # | 文件 | 字节 | **`minimap_material`** | 是否自名 |
|---|---|---|---|---|
| 1 | `mp_arkaden_sh.lua` | **63** | `compass_map_mp_arkaden_sh` | ✓ |
| 2 | `mp_backlot_sh.lua` | **63** | `compass_map_mp_backlot_sh` | ✓ |
| 3 | **`mp_crash_tropical.lua`** | **62** | ★★ **`compass_map_mp_crash_dlc`** | ★ **✗** |
| 4 | `mp_derail_sh.lua` | **62** | `compass_map_mp_derail_sh` | ✓ |
| 5 | `mp_fallen_sh.lua` | **62** | `compass_map_mp_fallen_sh` | ✓ |
| 6 | `mp_foundation_sh.lua` | **66** | `compass_map_mp_foundation_sh` | ✓ |
| 7 | `mp_interchange_sh.lua` | **67** | `compass_map_mp_interchange_sh` | ✓ |
| 8 | `mp_lockdown_sh.lua` | **64** | `compass_map_mp_lockdown_sh` | ✓ |
| 9 | `mp_lookout_sh.lua` | **63** | `compass_map_mp_lookout_sh` | ✓ |
| 10 | `mp_mission_sh.lua` | **63** | `compass_map_mp_mission_sh` | ✓ |
| 11 | `mp_nuked.lua` | **58** | `compass_map_mp_nuked` | ✓ |
| 12 | `mp_offshore.lua` | **61** | `compass_map_mp_offshore` | ✓ |
| 13 | **`mp_overwatch_sh.lua`** | **58** | ★★ **`compass_map_mp_ov_02`** | ★ **✗** |
| 14 | `mp_showdown.lua` | **61** | `compass_map_mp_showdown` | ✓ |
| 15 | `mp_tunisia.lua` | **60** | `compass_map_mp_tunisia` | ✓ |
| 16 | `mp_underground_sh.lua` | **67** | `compass_map_mp_underground_sh` | ✓ |
| 17 | `mp_wasteland_sh.lua` | **65** | `compass_map_mp_wasteland_sh` | ✓ |

★★★ **⇒ 15 个"自名"（`compass_map_<地图名>`）+ 2 个"异名"。**

---

## 二、★★★★★ **两处异名的重新判定**

### 2.1 ★★★★★ **`mp_crash_tropical` → `compass_map_mp_crash_dlc`：这不是错误**

```
`mp_crash_tropical.lua` 声明 `compass_map_mp_crash_dlc`
        ↓
★★★ 包外交叉核对（`Grep` 全包时命中,★ **`source\` 不在学习范围,仅作核对记录**）：
   `source\tests\game_server\ServerCoreTests.cpp` 有 **3 处**命中：
     :7334   `.material = "compass_map_mp_crash_dlc",`
     :7341   "\"compass_map_mp_crash_dlc\" -1200.000000 2528.000000 "
     :14900  std::optional<std::string>{ "compass_map_mp_crash_dlc" } &&
     :14902  std::optional<std::string>{ "compass_map_mp_nuked" } &&
        ↓
★★★★★ ⇒ **测试套件明确断言 `compass_map_mp_crash_dlc`**
   ⇒ 即 **`compass_map_mp_crash_dlc` 是**预期的正确值**,不是笔误**
```

★★★ **⇒ 更正报告 054 的措辞：**
```
报告 054 记："两处 name mismatch：`mp_crash_tropical.lua`→`compass_map_mp_crash_dlc`,
              `mp_overwatch_sh.lua`→`compass_map_mp_ov_02`"
        ↓
★ 现判定：
  `mp_crash_tropical` ⇒ **不是 mismatch**（有断言支持,是"该地图的材质名与地图名不同"）
  `mp_overwatch_sh`   ⇒ **仍在"无断言支持"状态**（`compass_map_mp_ov_02` 只有本文件一处命中）
```

### 2.2 ★★★ 两处的**共同解释**

```
`mp_crash_tropical`  ⇒ `mp_crash_dlc`      （★ Crash 是 DLC 地图,材质名沿用 DLC 命名）
`mp_overwatch_sh`    ⇒ `mp_ov_02`          （★ Overwatch 的内部代号是 `ov_02`）
        ↓
★★★ ⇒ 两处都不是"照抄地图名",而是**零售内部代号**
   ⇒ 即：**材质名 ≠ 地图名是常态,只要材质真实存在就对**
        ↓
★ 而 `zm_factory_sh.lua` 的注释给出了判据（逐字）：
  "the per-map materials **live in fastfiles**,
   and there is no zombies one to name"
   ⇒ ★★★ **材质在 fastfile（包外）里** ⇒ **无法从交付包内验证存在性**
```

★★ **⇒ 结论（保持报告 054 的立场）：不要"发明"材质名。**
**⇒ 但 `crash_dlc` 现在有断言背书,性质与 `ov_02` 不同。**

---

## 三、★★★★★ `zm_factory_sh.lua` 全文（1,590 B / 25 行）——**一个完整失败模式的解释**

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

### ★★★★★ 三个层次的声明

#### ① **为什么不写 `minimap_material`（MEASURED,不是遗漏）**

```
★★★ 证据一：**三份**零售 `zm_factory_sh` 录像（在 `zombie demos\` 里）
            **完全没有 compass 配置串**
★★★ 证据二：而零售 dm gamestate **有**：
            `2555 "compass_map_mp_cross_fire" 8288 1280 640 -6368`
★★★ 证据三：`out.exe` 里**唯一的** `compass_map_*` 串是
            **`compass_map_awareness_radar` @ `0xDB1D0C`**
        ↓
★★★ 结论（逐字）："**Zombies maps do not use the MP compass.**"
   "the per-map materials **live in fastfiles**,
    and **there is no zombies one to name**"
```

★★★★★ **⇒ `0xDB1D0C` 是 `out.exe` 里唯一 `compass_map_*` 串的位置 —— 一个**极精确的 EXE 级事实**。**

#### ② ★★★★★ **为什么必须返回空表（引擎的硬要求）**

```
`SV_LoadMapScriptMetadata` **必须返回一个值**
        ↓
★★★ 因为 `Appmain.cpp` 在
   **`mapScriptExists != mapMetadata.has_value()`** 时**直接让会话配置失败**
        ↓
★ 空表满足这个条件；
**返回 nothing 的脚本,或根本没有脚本,都不满足**
```

★★ **⇒ 这是一个**"空表 ≠ 无脚本"的精确区分** ⇒ 与报告 083 的清单条目呼应
（`zm_factory_sh.lua` 在清单里,`size: 1590` ✓）。**

#### ③ ★★★★★ **已知后果（`NO_SPAWN_POINT`）—— 本报告最重要的部分**

```
`Appmain.cpp` **只在**
   `if (mapMetadata && mapMetadata->miniMapMaterial)` 里
**读地图实体串**
        ↓
★★★ ⇒ `miniMapMaterial` 为 nil ⇒ **同时跳过出生点加载**
        ↓
★★★★★ ⇒ **会话死在 `initial_spawn_ground_trace` / `NO_SPAWN_POINT`**
```

★★★★★ **⇒ 作者的定义（逐字）：**
```
"That coupling is an **MP-only assumption** --
 **a compass and a spawn list have nothing to do with each other** --
 and **decoupling them is what zombies needs from the engine side**."
        ↓
★★★★★ **"Do NOT 'fix' this by inventing a material name here;
  that would trade a clean failure for a wrong one."**
```

★★ **⇒ 这是一个**"耦合缺陷"的完整诊断**：**
```
罗盘材质 与 出生点列表 **在引擎里被错误耦合**
（`if (miniMapMaterial)` 同时门控两件事）
        ↓
★★★ 僵尸地图**没有罗盘材质**（本来就不该有）
        ↓
⇒ 连带**失去出生点** ⇒ `NO_SPAWN_POINT`
        ↓
★★★ 正确的修法是**在引擎侧解耦**,不是**在 Lua 侧编一个材质名**
```

### ★★★ 零售出生点坐标

```
"Retail spawn origin for this map, **from the demos and byte-identical across all three**:
     **-73.000000 -54.000000 8.000000**"
        ↓
★★★ 三份录像**逐字节相同** ⇒ 高可信
```

---

## 四、★★★★★ 与既有 memory 的呼应

### 4.1 ★★★ `NO_SPAWN_POINT` 与"服务端权威位置"

```
memory「出生点: 服务端权威位置」：
  "用户确认「Python 版人物出生点正确」"
  "我们的 `omit=1` 语义上 = 参照的 `spawn_from_map.on`,而那份注释写明症状:
   客户机在地图自带的几十个 mp_tdm_spawn 里自己挑,
   **会挑到几何体/屋顶里 → 卡住走不动**"
        ↓
★★★ 本报告：`zm_factory_sh` 因为**无罗盘材质** ⇒ **引擎侧跳过出生点加载**
   ⇒ `NO_SPAWN_POINT`
        ↓
★ 两者都是"**出生点没到位**"这一类问题,但**机制不同**：
   一个是**我们没发位置**（服务端权威位置）
   一个是**引擎没加载出生点**（罗盘耦合）
```

★★ **⇒ 记录为**两条独立的出生点故障路径**,不要混为一谈（**未实测验证二者关系**）。**

### 4.2 ★★★ `zm_factory_sh` 的 zone 数据（与报告 066/070/079 呼应）

```
报告 066/070：factory 有 **12 个 zone** / **63 个 spawner**
报告 079：`mp_playlists` 里 `zm_factory_sh` 出现 **4 次**
本报告：`zm_factory_sh.lua` 返回 `{}`（**无罗盘材质**）
        ↓
★★★ ⇒ 三者一致：**这是一张"已建模但罗盘耦合未解"的地图**
```

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 17 个小文件 | **全 3 行 / 纯 LF（CRLF=0）/ 无 BOM（首 3 字节 `72-65-74`）/ 58–67 B** |
| 2 | ★★ 统一格式 | `return {` + `    minimap_material = "…",` + `}` |
| 3 | ★★★ 15 个"自名" | `compass_map_<地图名>` |
| 4 | ★★★★★ **异名 1** | **`mp_crash_tropical` → `compass_map_mp_crash_dlc`** |
| 5 | ★★★★★ **异名 1 的判定** | ★ **不是错误** —— 包外 `ServerCoreTests.cpp` **3 处断言**该值（`:7334` / `:7341` / `:14900`） |
| 6 | ★★★ 异名 2 | **`mp_overwatch_sh` → `compass_map_mp_ov_02`** |
| 7 | ★★ 异名 2 的状态 | **无断言支持**（全包仅本文件一处命中） |
| 8 | ★★★ 共同解释 | 两处都是**零售内部代号**（`crash` 是 DLC 地图 / `overwatch` 内部代号 `ov_02`） |
| 9 | ★★★ 验证边界 | 材质**在 fastfile 里**（包外）⇒ **交付包内无法验证存在性** |
| 10 | ★★★★★ **`zm_factory_sh.lua`** | **1,590 B / 25 行 / 返回 `{}`** |
| 11 | ★★★★★ 不写材质的**三条证据** | ① 三份零售录像**无** compass 串 ② 零售 dm **有** `2555 "compass_map_mp_cross_fire" …` ③ `out.exe` 唯一 compass 串 = **`compass_map_awareness_radar` @ `0xDB1D0C`** |
| 12 | ★★★★★ **必须返回空表的引擎条件** | **`mapScriptExists != mapMetadata.has_value()`** ⇒ 会话配置**直接失败** |
| 13 | ★★★ "空表 ≠ 无脚本" | 空表满足;**返回 nothing 或没有脚本都不满足** |
| 14 | ★★★★★ **`NO_SPAWN_POINT` 因果链** | `Appmain.cpp` 只在 **`if (mapMetadata && mapMetadata->miniMapMaterial)`** 里读地图实体串 ⇒ nil ⇒ **跳过出生点加载** ⇒ 会话死在 **`initial_spawn_ground_trace` / `NO_SPAWN_POINT`** |
| 15 | ★★★★★ 作者定性 | "**MP-only assumption**" / "**a compass and a spawn list have nothing to do with each other**" / **"decoupling them is what zombies needs from the engine side"** |
| 16 | ★★★★★ 最高价值的一句 | **"Do NOT 'fix' this by inventing a material name here; that would trade a clean failure for a wrong one."** |
| 17 | ★★★ 零售出生点 | **`-73.000000 -54.000000 8.000000`**（三份录像**逐字节相同**） |

---

## 六、结论

### 1. ★★★★★ **`zm_factory_sh.lua` 解释了一条完整的失败模式**（罗盘 × 出生点耦合）

```
僵尸地图无罗盘材质（本来就不该有）
        ↓
★★★ 但引擎 `if (miniMapMaterial)` **同时门控**了出生点加载
        ↓
⇒ `NO_SPAWN_POINT`
        ↓
★★★ 正确修法在**引擎侧解耦**,不是**编一个材质名**（"that would trade a clean failure for a wrong one"）
```

### 2. ★★★★★ **两处"名字不符"要区别对待**

```
`mp_crash_tropical → compass_map_mp_crash_dlc`  ⇒ ★ **有断言背书,不是错误**（更正报告 054）
`mp_overwatch_sh   → compass_map_mp_ov_02`      ⇒ **仍无外部支持**
        ↓
★★★ 共同点：材质名 ≠ 地图名是**常态**（零售内部代号）；材质存在性**在 fastfile 里,包内不可验**
```

### 3. ★★★ **17 个小文件完全同质**（3 行 / LF / 无 BOM / 58–67 B）

### 4. ★★★ **`0xDB1D0C` 是 `out.exe` 里唯一的 `compass_map_*` 串位置**（一个新的精确 EXE 事实）

### 5. ★★ **`mapScriptExists != mapMetadata.has_value()`** 是一个可直接引用的引擎约束

---

## 七、下一步

- `enemy_recorded_path_by_spawner` 剩余行（已提取**全量**逐 spawner 统计,见报告 088）
- `MarketplaceSkus.json` 逐条
- 两个插件的完整字符串面清单
