# 学习报告 070（重开）— `zm.lua` 六常量与实测表（135–239 行）

**学习范围**：`zm.lua` 第 135–239 行（spawn 依据 + 六个时间常量 + 实测数据表）
**性质**：全实测（**全包最详尽的实测数据**）
**★★★ 本报告收录**三回合的精确实测表**与**六个时间常量**

---

## 一、★★★★★ 六个时间常量（第 205–210 行，逐字）

```lua
local ROUND_ONE_DELAY = 5500   -- first round: first actor at +5.5 s
local NEXT_ROUND_DELAY = 400   -- rounds 2-8: first actor at +0.4 s
local ROUND_PAUSE = 11000      -- measured 10.8-11.2 s
local SPAWN_BACKOFF = 10000    -- wait after a whole sweep refuses
local ROUND_SECONDS = 240000   -- backstop only
local ROUND_GOAL = 8           -- what the round HUD counts towards
```

### ★★★★★ 完整的六常量表

| # | 常量 | 值 | 说明 |
|---|---|---|---|
| **1** | **`ROUND_ONE_DELAY`** | **`5500`**（5.5 s） | 第一回合首个 actor |
| **2** | **`NEXT_ROUND_DELAY`** | **`400`**（0.4 s） | 第 2–8 回合首个 actor |
| **3** | **`ROUND_PAUSE`** | **`11000`**（11 s） | ★ 实测 **10.8–11.2 s** |
| **4** | **`SPAWN_BACKOFF`** | **`10000`**（10 s） | 整轮 sweep 失败后等待 |
| **5** | **`ROUND_SECONDS`** | **`240000`**（240 s） | ★ **仅 backstop** |
| **6** | **`ROUND_GOAL`** | **`8`** | HUD 计数目标 |

★★★ **⇒ 全部是**毫秒**（注释："Milliseconds throughout"）。**

★★ **⇒ 且给出理由（第 203–204 行）：**
```
"The server now raises this director every **100 ms**;
flooring to whole seconds made the measured **300/400 ms** timings impossible."
        ↓
★ 所以必须用毫秒（300/400 ms 无法用整秒表示）
```

---

## 二、★★★★★ 三回合的**精确实测表**（第 184–191 行，逐字）

```
-- MEASURED OFF A SOLO ZM DEMO ON THIS MAP, rounds 2-4 identified by their HUD
-- (12.165). Everything here replaces an invented value.
--
--                    round 2   round 3   round 4
--   spawned             29        34        39      +5 per round
--   peak alive          27        30        31      rises with the round
--   round length        86 s      65 s       -
--   pause before        11.8 s    10.8 s    11.5 s
```

### ★★★★★ 完整的实测数据表

| 指标 | **round 2** | **round 3** | **round 4** | 规律 |
|---|---|---|---|---|
| **spawned** | **29** | **34** | **39** | ★ **+5 每回合** |
| **peak alive** | **27** | **30** | **31** | 随回合上升 |
| **round length** | **86 s** | **65 s** | — | （无规律） |
| **pause before** | **11.8 s** | **10.8 s** | **11.5 s** | ★ **≈ 11 s** |

★★★ **⇒ 四条精确规律：**
```
① spawned = **29 / 34 / 39** ⇒ 每回合 **+5**
② peak alive = **27 / 30 / 31** ⇒ 上升但放缓
③ round length = **86 / 65** 秒
④ pause = **11.8 / 10.8 / 11.5** 秒 ⇒ **≈ 11 s**（对应 `ROUND_PAUSE = 11000`）
```

★ **⇒ 出处：`12.165`（`re/demo-re/` 的节号）。**

★★ **⇒ 且明确："Everything here replaces an invented value."**

---

## 三、★★★★★ spawn 形状的**精确描述**（第 193–196 行，逐字）

```lua
-- THE SPAWN SHAPE IS NOT A FLAT TIMER. A round opens with a fast burst up to the
-- concurrency cap -- 18 actors in about 5 s -- and then trickles at ~1.5 s to
-- replace deaths until the quota is spent. This server used to spawn at a flat
-- interval from an empty start, which is why waves took a minute to build.
```

### ★★★★★ 完整的 spawn 曲线

```
回合开始
        ↓
★★★ **快速爆发**：5 秒内刷 **18 个**（到并发上限）
        ↓
然后**缓慢滴流**：每 **~1.5 秒** 一个
        ↓
★ 只为**替换死亡**，直到配额用完
```

★★★ **⇒ 两个精确数字：**
```
爆发：**18 个 / 5 秒**  （≈ 3.6 个/秒）
滴流：**~1.5 秒/个**
```

★★ **⇒ 且明确旧实现的错误：**
```
"This server used to spawn at a **flat interval from an empty start**,
which is why waves took **a minute to build**."
        ↓
★ 旧：从 0 开始按固定间隔刷 ⇒ **一分钟才建起一波**
```

★ **⇒ 这与报告 068 的"旧实现在同一 tick 开下一波"**是**不同**的问题**：**
```
报告 068：回合**切换**的时机错（同 tick）
本报告：  回合**内部**的 spawn 曲线错（固定间隔）
```

---

## 四、★★★★★ **两个 demo 的分歧**（第 198–202 行，逐字）

```lua
-- A SECOND DEMO ON THIS MAP DISAGREES and is deliberately NOT merged in: it
-- showed 68-72 spawned per round and 36-42 s pauses. It is a different
-- recording of unknown player count. This one is solo and its rounds are
-- identified, so it is the authority for a one-player game. If a per-player
-- multiplier is ever wanted, that other capture is the second data point.
```

### ★★★★★ 两份 demo 的完整对照

| 项 | **本 demo（solo）** | **第二份 demo** |
|---|---|---|
| **spawned/round** | **29 / 34 / 39** | ★ **68–72** |
| **pause** | **10.8–11.8 s** | ★ **36–42 s** |
| **玩家数** | **solo（已知）** | ★ **未知** |
| **回合是否已识别** | ★ **是（HUD 识别）** | 否 |
| **采纳** | ★★★ **是（权威）** | **不合并** |

★★★ **⇒ 这是一个**极其严谨的数据选择**：**
```
两份 demo 数据冲突
        ↓
本 demo：solo + 回合已用 HUD 识别 ⇒ **可信**
第二份：玩家数未知 + 回合未识别 ⇒ **不可信**
        ↓
★★★ **只采纳本 demo**，第二份作为"未来 per-player 乘数的第二数据点"
```

★ **⇒ 且明确："deliberately NOT merged in"。**

★★ **⇒ 这是**"数据来源可信度"的严格区分**（与报告 057 的"免责声明"同类）。**

---

## 五、★★★★★ spawn 点的**精确依据**（第 135–142 行，逐字）

```lua
-- SPAWN ON THE MAP'S OWN ZOMBIE SPAWNERS, IN THE ZONE THE PLAYERS START IN.
--
-- MEASURED, not chosen. re/demo-re/20-zm-actor-lifecycle.md 12.31: every retail
-- actor's first asserted position in C-2021-7-31[15-32-16]zm decodes to within a
-- few units of a `script_struct` whose script_noteworthy is "zombie_spawner",
-- and factory carries exactly 63 of them -- the same 63 the zone model parses.
-- Two of the eight sampled were within SEVEN units, which is the spawn instant
-- caught exactly. So zmspawnactor(zone, point) already spawns where retail does.
```

### ★★★★★ 三个精确数据

| # | 项 | 值 |
|---|---|---|
| **1** | `script_noteworthy` | **`"zombie_spawner"`** |
| **2** | factory 的 spawner 数 | **63**（★ 与 zone 模型解析的 63 **一致**） |
| **3** | ★★★ 采样精度 | 8 个采样中 **2 个在 7 units 内** |
| **4** | demo 标识 | **`C-2021-7-31[15-32-16]zm`** |

★★★ **⇒ 第 3 条是关键证据：**
```
8 个采样
        ↓
★ 其中 **2 个在 7 units 内**
        ↓
★★★ "which is **the spawn instant caught exactly**"
        ↓
⇒ 证明 `zmspawnactor(zone, point)` 刷在**和零售一样的位置**
```

★ **⇒ 第 2 条交叉验证：**factory 63 个 spawner = zone 模型解析的 63**（报告 066 已记录）。**

★★ **⇒ 出处：`re/demo-re/20-zm-actor-lifecycle.md 12.31`。**

### ★★★ "THE RING OF FOUR IS GONE"（第 144–146 行）

```lua
-- THE RING OF FOUR IS GONE. It placed zombies 200 units around the player's own
-- spawn, which is not a thing retail ever does; it existed only to get one in
-- view before anything drew. Nothing needs it now.
```

★★★ **⇒ 一个被删除的临时方案：**
```
"环形四个"：在玩家出生点周围 **200 units** 放 4 个僵尸
        ↓
★★★ **"not a thing retail ever does"**
        ↓
它只是为了"在有任何渲染之前先让一个出现在视野里"
        ↓
★ 现在不需要了
```

---

## 六、★★★★★ `home_zone` 的**几何解析**（第 148–162 行）

```lua
-- The zone is resolved BY GEOMETRY, not by name: zmzoneat answers which volume
-- contains the map's player start, so this works on any zm map instead of only
-- the one whose start zone happens to be called receiver_zone.
local home_zone
for zone = 1, zone_count do
    if codol.call("function:zmzonename", zone) == at then
        home_zone = zone
    end
end
if home_zone == nil then
    -- Standing outside every volume is a legitimate answer (21b), so a map whose
    -- start point is not inside a zone falls back rather than spawning nothing.
    print("zm start zone unresolved, falling back to zone 1", at)
    home_zone = 1
end
```

### ★★★★★ 三个设计要点

| # | 要点 | 内容 |
|---|---|---|
| **1** | **BY GEOMETRY, not by name** | `zmzoneat` 回答"哪个 volume 包含玩家起点" |
| **2** | ★ 通用性 | **对任何 zm 地图都有效**（不只 receiver_zone 那张） |
| **3** | ★★ 兜底 | 起点**不在任何 volume 内**是**合法答案** ⇒ 回退到 **zone 1** |

★★★ **⇒ 第 1、2 条是**从"硬编码地图名"到"几何通用"的改进**：**
```
旧：只支持 start zone 叫 receiver_zone 的地图
        ↓
新：`zmzoneat(起点)` ⇒ 任何地图都能解析
```

★★ **⇒ 第 3 条引用 `21b`（`re/demo-re/21-zm-zones-and-spawners.md` 第 21b 节）。**

---

## 七、★★★★★ **`zm_actor_died` 的实现**（第 220–226 行）

```lua
zm_actor_died = function(event)
    local actor = event and event.target_entity_num
    if actor == nil or active_actors[actor] ~= true then return end
    active_actors[actor] = nil
    alive = math.max(0, alive - 1)
    print("zm actor died", actor, "round", round, "alive", alive)
end
```

★★★ **⇒ 四个步骤：**
```
① 取 `event.target_entity_num`
② ★ 若不在 `active_actors` 中 ⇒ **直接返回**（不是我们的 actor）
③ 从 `active_actors` 移除
④ `alive = max(0, alive - 1)`（★ 不会变负）
```

★★ **⇒ 第 ② 条是**关键的过滤**（`entity_killed` 会对**所有**可伤害实体触发）。**

★ **⇒ 第 ④ 条 `math.max(0, ...)` 防止计数变负。**

---

## 八、★★★★ "ROUTE-BASED, NOT ZONE-NAME WEIGHT"（第 228–239 行）

```lua
-- SPAWNER SELECTION IS ROUTE-BASED, NOT A ZONE-NAME WEIGHT.
--
-- The first-position association that produced a 17 receiver / 8 west split is
-- not strong enough to drive the live director: receiver points 7/8 and west
-- points 3/5 occupy the same two closets, only 43-63 units apart, while several
-- first complete retail positions are already 140-300 units from either map
-- struct. Treating nearest struct as an exact group made this script cycle every
-- point in receiver/west, including open routes that can never touch a board.
--
-- `zmspawncrossesbarrier` asks the world router the actual question for the
-- current player destination. Prefer those points among the occupied zone and
-- its adjacent zones. This keeps the map's own zone/spawner data authoritative,
```

### ★★★★★ 一个**精确的数据反驳**

```
旧方法：按"最近 struct"分组
        ↓
得到 **17 receiver / 8 west** 的划分
        ↓
★★★ 但证据反驳：
  · receiver 点 7/8 与 west 点 3/5 占据**同两个 closet**
    只相距 **43–63 units**
  · 而几个"第一个完整零售位置"已经距离任一 map struct **140–300 units**
        ↓
★ 所以"最近 struct = 精确分组"是**错的**
        ↓
后果：脚本遍历 receiver/west 的**每一个点**
      包括**永远碰不到板的开放路线**
        ↓
★★★ 改用 `zmspawncrossesbarrier`（问 world router 真正的问题）
```

★★★ **⇒ 四个精确数字：**
```
17 receiver / 8 west        （错误分组）
43–63 units                 （两个 closet 的距离）
140–300 units               （零售位置与 struct 的距离）
```

★ **⇒ 这是**用距离数据反驳分组假设**的典范。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **六时间常量** | `5500` / `400` / `11000` / `10000` / `240000` / `8` |
| 2 | ★★ 单位 | **全部毫秒** |
| 3 | ★ 理由 | director 每 **100 ms**；**300/400 ms 无法用整秒** |
| 4 | ★★★★★ **三回合实测** | spawned **29/34/39**（+5）/ peak **27/30/31** |
| 5 | round length | **86 s / 65 s** |
| 6 | pause | **11.8 / 10.8 / 11.5 s** |
| 7 | ★★★★★ **spawn 曲线** | **5 秒内 18 个爆发** + **~1.5 s 滴流** |
| 8 | ★★★ 旧实现错误 | **固定间隔从 0 开始** ⇒ **一分钟才建起一波** |
| 9 | ★★★★ **两份 demo 分歧** | 本 demo **29-39** vs 第二份 **68-72** |
| 10 | 采纳决定 | ★ **只采纳本 demo（solo + HUD 识别）** |
| 11 | ★★★ spawner 依据 | `script_noteworthy = "zombie_spawner"`，factory **63 个** |
| 12 | ★★★ 采样精度 | 8 个中 **2 个在 7 units 内** |
| 13 | ★ demo 标识 | **`C-2021-7-31[15-32-16]zm`** |
| 14 | ★ "RING OF FOUR" | 已删除（200 units 环绕，**零售从不这么做**） |
| 15 | ★★★ **zone 解析** | **BY GEOMETRY, not by name**（`zmzoneat`） |
| 16 | ★ 兜底 | 起点不在任何 volume ⇒ **zone 1**（合法答案） |
| 17 | ★ `zm_actor_died` | 过滤 `active_actors` + `math.max(0, ...)` |
| 18 | ★★★★ **分组反驳** | 17/8 划分错；两 closet 相距 **43–63**，零售位置距 struct **140–300** |

---

## 十、结论

### 1. ★★★★★ **三回合实测表**（29/34/39 spawned，11.8/10.8/11.5 s pause）是全包最详尽的数据

### 2. ★★★★★ **spawn 曲线是"爆发 + 滴流"**（5 秒 18 个 + 1.5 秒/个），不是固定间隔

### 3. ★★★★★ **两份 demo 数据冲突时，只采纳可信的那份**

★ **⇒ 判据：solo + 回合已用 HUD 识别。**

### 4. ★★★★ **`zmspawnactor` 已被证明刷在零售位置**（7 units 精度）

### 5. ★★★★ **zone 解析从"按名字"改为"按几何"**（`zmzoneat`）

### 6. ★★★ **距离数据反驳了"最近 struct"分组**（43–63 vs 140–300）

---

## 十一、下一步

- `zm.lua` 最后未读段（371–539 行，约 169 行）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
