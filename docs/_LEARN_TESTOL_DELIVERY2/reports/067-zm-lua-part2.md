# 学习报告 067（重开）— `zm.lua` spawn 导演逻辑（240–370 行）

**学习范围**：`zm.lua` 第 240–370 行（zone 选择 + spawn 点筛选）
**性质**：全实测
**★★★ 本报告收录**两条 zone 策略**与**"创作 ≠ 已开启"的关键区分**

---

## 一、★★★★★ 两条 zone 策略（第 262–291 行）

### 1.1 ★★★ 策略 A：`cooperative-union-reconstruction`（可选实验）

```lua
-- `cooperative-union-reconstruction` is an explicit OLMOD_ZM_COOP_SPAWN_ZONES=1
-- experiment, not a recovered retail director rule. The native-side status
-- query keeps the ordinary first-player path byte-for-byte in charge unless
-- that option is enabled.
local function read_occupied_zones(observed_name)
    local source = codol.call("function:zmcooperativezonesource") or
        "legacy-first-player"
    if source == "cooperative-union-reconstruction" then
        local zones = {}
        local names = {}
        local encoded = codol.call("function:zmcooperativespawnzones") or ""
        for token in string.gmatch(encoded, "[^,]+") do
            local zone = tonumber(token)
            if zone ~= nil then
                zones[#zones + 1] = zone
                names[#names + 1] = tostring(codol.call("function:zmzonename", zone))
            end
        end
        return zones, table.concat(names, "+"), source
    end
```

★★★ **⇒ 关键声明（逐字）：**
```
"`cooperative-union-reconstruction` is an explicit OLMOD_ZM_COOP_SPAWN_ZONES=1
experiment, **not a recovered retail director rule**."
```

★★ **⇒ 即：这是**重建策略**，不是恢复的零售规则。**

★ **⇒ 且明确："The native-side status query keeps the ordinary first-player path
**byte-for-byte in charge** unless that option is enabled."**

★★★ **⇒ 默认路径**逐字节不变**（byte-for-byte in charge）——这是**极强的兼容性承诺**。**

### 1.2 ★★★ 策略 B：`legacy-first-player`（默认）

```lua
    local live_name = observed_name or codol.call("function:zmplayerzone")
    local zone = zone_index(live_name)
    if zone == nil then
        zone = home_zone
        live_name = codol.call("function:zmzonename", zone)
    end
    return {zone}, live_name, source
end
```

★★★ **⇒ 默认策略：**
```
① 取 `zmplayerzone()`（当前玩家所在 zone 名）
② `zone_index(name)` 转索引
③ ★ 若找不到 ⇒ 回退到 **`home_zone`**
④ 返回**单个** zone
```

★ **⇒ 这是**单 zone** 策略（"legacy-first-player"）。**

★★ **⇒ 两个 source 值的对比：**
```
"cooperative-union-reconstruction"  ⇒ 多 zone 并集（可选）
"legacy-first-player"               ⇒ 单 zone（默认）
```

---

## 二、★★★★★ `factory_solo` / `factory_two_player` 的**精确判据**（第 299–302 行）

```lua
factory_solo = zone_count == 12 and at == "receiver_zone" and
    player_count == 1
factory_two_player = zone_count == 12 and at == "receiver_zone" and
    player_count == 2
```

### ★★★★★ 三个条件同时成立

| 条件 | 值 |
|---|---|
| **`zone_count == 12`** | **12 个 zone** |
| **`at == "receiver_zone"`** | **`info_player_start` 在 receiver_zone** |
| **`player_count == 1`**（solo）/ **`== 2`**（two_player） | 1 或 2 人 |

★★★ **⇒ 这是**专门为 `zm_factory_sh` 硬编码的判据**：**
```
zone_count == 12
        ↓
★ 只有 zm_factory_sh 是 12 个 zone（报告 066 的四张地图数据）
        ↓
at == "receiver_zone"
        ↓
★ 该地图的 info_player_start 落在 receiver_zone
        ↓
★★★ ⇒ 两者合起来唯一标识 **zm_factory_sh**
```

★★ **⇒ 这是一个**用数据特征识别地图**的巧妙手法（不依赖地图名）。**

★ **⇒ 但**脆弱**：若地图被改（zone 数变化），判据失效。**

---

## 三、★★★★★ **"创作 ≠ 已开启"** 的关键区分（第 329–332 行，逐字）

```lua
-- Authored does not mean opened. The C++ progression owner activates
-- the start zone initially and flips exactly one more zone when the
-- purchased trigger's enter_* flag fires.
if codol.call("function:zmzoneactive", zone) ~= 1 then return end
```

### ★★★★★ 完整的机制

```
地图里**创作**了 N 个 zone
        ↓
★★★ 但**不等于已开启**
        ↓
C++ 的 progression owner：
  ① **初始只激活 start zone**
  ② 当"购买的 trigger 的 enter_* flag"触发时
     ★ **只翻转恰好一个** zone
        ↓
Lua 侧必须检查 `zmzoneactive(zone) == 1`
        ↓
★ 不是 1 ⇒ **跳过这个 zone**
```

★★★ **⇒ 这是**僵尸模式的核心玩法机制**（买门开新区域）。**

★ **⇒ 且 C++ 侧"**flips exactly one more zone**" —— 每次**只开一个**。**

★★ **⇒ 出处（第 330–331 行）："The C++ progression owner"。**

---

## 四、★★★★★ 屏障路线（第 338–353 行）

```lua
for point = 1, points do
    all_points[#all_points + 1] = point
    local crosses = codol.call(
        "function:zmspawncrossesbarrier", zone, point)
    if crosses == 1 then
        barrier_points[#barrier_points + 1] = point
    end
end
all_spawn_zones[#all_spawn_zones + 1] = {
    zone = zone, point_ids = all_points, name = name
}
if #barrier_points > 0 then
    barrier_spawn_zones[#barrier_spawn_zones + 1] = {
        zone = zone, point_ids = barrier_points, name = name
    }
end
```

### ★★★★★ 完整的 spawn 点分类

```
每个 zone 的所有 spawn 点
        ↓
逐个查询 `zmspawncrossesbarrier(zone, point)`
        ↓
若返回 1 ⇒ 该点**跨过屏障**（需要破窗/拆板才能到达）
        ↓
★★★ 分成两组：
  `all_spawn_zones`      （全部点）
  `barrier_spawn_zones`  （★ 只含跨屏障的点）
```

★★★ **⇒ 为什么要区分（第 240–242 行，逐字）：**
```
"spreads births across distinct closets, and guarantees that a boarded route
is exercised whenever the local zone layout offers one.
If a map/zone has no such route, retain the ordinary adjacent-zone pool
rather than spawning none."
```

★★ **⇒ 目的：**
```
① 把出生点**分散到不同 closet**
② ★ 保证**"被钉死的路线"（boarded route）**在布局允许时**总被使用**
③ 若没有这样的路线 ⇒ **退回普通相邻 zone 池**（不是不刷）
```

★ **⇒ "boarded route" = 玩家用木板钉住的路线？还是僵尸破板？**
**⇒ 结合 `crossesbarrier` ⇒ 应该是**僵尸需要破障才能到达的路线**。**

---

## 五、★★★ 无可用 zone 时的**暂停而非发明**（第 309–319 行，逐字）

```lua
-- A co-op frame may have no eligible living player while the player count
-- still includes a corpse or a class screen. Pause rather than inventing a
-- home-zone target. Legacy behaviour retains its existing home-zone fallback.
if #occupied_zones == 0 then
    occupied_zone_name = ""
    occupied_zone_source = source
    spawn_zones = {}
    no_eligible_cooperative_zones = true
    print("zm has no eligible cooperative zone; spawning paused")
    return false
end
```

★★★ **⇒ 一个精确的边界处理：**
```
合作帧可能**没有合格的活着的玩家**
（player_count 仍包含**尸体**或**职业选择界面**）
        ↓
★★★ **暂停，而不是发明一个 home-zone 目标**
        ↓
`spawn_zones = {}` + `no_eligible_cooperative_zones = true`
        ↓
★ 打印 "zm has no eligible cooperative zone; spawning paused"
```

★ **⇒ 且明确："Legacy behaviour retains its existing **home-zone fallback**."**

★★ **⇒ 两条路径的差异：**
```
cooperative 路径  ⇒  ★ **暂停**（不发明）
legacy 路径       ⇒  保留 **home-zone fallback**
```

---

## 六、★★★ `zone_index` 的线性查找（第 253–261 行）

```lua
local function zone_index(name)
    if name == nil or name == "" then return nil end
    for zone = 1, zone_count do
        if codol.call("function:zmzonename", zone) == name then
            return zone
        end
    end
    return nil
end
```

★★ **⇒ **O(n) 线性查找**（`zone_count` 最多 12 ⇒ 最多 12 次 `codol.call`）。**

★★★ **⇒ 这是**跨语言调用开销的代价**（每次 `codol.call` 都是跨 Lua/C++ 边界）。**
**⇒ 但 12 次可以接受。**

★ **⇒ 若 zone 数更多（如 100），应该建索引缓存。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 两条 zone 策略 | **`cooperative-union-reconstruction`**（可选）/ **`legacy-first-player`**（默认） |
| 2 | ★★★ 可选策略的性质 | **"not a recovered retail director rule"**（重建，不是恢复） |
| 3 | ★★ 默认路径承诺 | **"byte-for-byte in charge"** |
| 4 | ★★★ `factory_solo` 判据 | **`zone_count == 12`** + **`at == "receiver_zone"`** + `player_count == 1` |
| 5 | `factory_two_player` | 同上 + `player_count == 2` |
| 6 | ★ 判据性质 | **用数据特征识别地图**（不依赖地图名） |
| 7 | ★★★★★ **"Authored ≠ opened"** | 创作了 N 个 zone **不等于**已开启 |
| 8 | ★★★ C++ progression owner | **初始只激活 start zone**；trigger 触发时**只翻转恰好一个** |
| 9 | ★ 检查 | **`zmzoneactive(zone) == 1`**，否则跳过 |
| 10 | ★★★ **屏障路线** | `zmspawncrossesbarrier(zone, point)` 返回 1 ⇒ 跨屏障 |
| 11 | 两组 | `all_spawn_zones` / **`barrier_spawn_zones`** |
| 12 | ★★ 目的 | 分散到不同 closet + **保证 boarded route 被使用** |
| 13 | ★ 无路线时 | **退回普通相邻 zone 池**（不是不刷） |
| 14 | ★★★ 无可用 zone | **暂停**（不发明 home-zone 目标） |
| 15 | ★ 两条路径差异 | cooperative **暂停** / legacy **保留 home-zone fallback** |
| 16 | ★ `zone_index` | **O(n) 线性查找**（最多 12 次跨语言调用） |

---

## 八、结论

### 1. ★★★★★ **"Authored does not mean opened"** 是僵尸模式的核心机制

```
创作了 N 个 zone
        ↓
但初始只开 start zone
        ↓
★ 买门触发时**只翻转恰好一个**
```

### 2. ★★★★★ **两条 zone 策略**（可选实验 vs 默认 legacy）

★ **⇒ 默认承诺 "byte-for-byte in charge"（逐字节不变）。**

### 3. ★★★★ **`factory_solo` 用数据特征识别地图**（`zone_count==12` + `at=="receiver_zone"`）

### 4. ★★★ **屏障路线**（`crossesbarrier`）保证出生点分布

### 5. ★★★ **无可用 zone 时暂停，不发明**（cooperative 路径）

### 6. ★★ **`zone_index` 是 O(n) 线性查找**（12 次跨语言调用可接受）

---

## 九、下一步

- `zm.lua` 剩余（第 370–735 行，约 365 行）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
