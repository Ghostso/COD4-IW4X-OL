# 学习报告 068（重开）— `zm.lua` round director（540–660 行）

**学习范围**：`zm.lua` 第 540–660 行（spawn 拒绝计数 + 回合开始/结束）
**性质**：全实测
**★★★ 本报告收录**回合间隔的精确实测（35.8s / 41.6s）**与**拒绝计数机制**

---

## 一、★★★★★ 回合节奏的**精确实测**（第 646–654 行，逐字）

```lua
-- THE PAUSE BETWEEN ROUNDS IS REAL AND IT IS LONG. Measured at 35.8 s and
-- 41.6 s between rounds on the demo; the mode used to begin the next wave
-- on the same tick the last one cleared.
if round_cleared_at == nil then
    round_cleared_at = now
    print("zm round cleared", round, "in",
        (now - round_started_at) / 1000, "s", "pausing",
        ROUND_PAUSE / 1000)
end
```

### ★★★★★ 两个精确的实测数据

| # | 回合间隔 |
|---|---|
| **1** | **35.8 秒** |
| **2** | **41.6 秒** |

★★★ **⇒ 且明确："THE PAUSE BETWEEN ROUNDS IS REAL AND IT IS LONG."**

★ **⇒ 而**旧实现**："the mode used to begin the next wave on the same tick
the last one cleared" —— **同一 tick 就开下一波**（**错误**）。**

★★ **⇒ 这是一个**时序还原的关键发现**：**
```
旧：最后一波清完的**同一 tick** ⇒ 立刻开下一波（★ 错误）
        ↓
实测：间隔 **35.8 / 41.6 秒**
        ↓
★ 修复：`ROUND_PAUSE` 常量
```

---

## 二、★★★★★ 回合结束的**双重判据**（第 639–648 行，逐字）

```lua
-- THE ROUND ENDS WHEN THE WAVE IS DEAD, which is what retail does, with a
-- timer only as a backstop. `alive` is decremented by the entity_killed
-- handler below; the timer catches a wave that can never be cleared -- one
-- whose last zombie is stuck behind geometry, say -- rather than hanging the
-- match on it.
local want_now = wave_size(round)
if spawned_this_round >= want_now and alive <= 0 then
```

### ★★★★★ 完整的回合结束逻辑

```
主判据：**本波已刷够**（`spawned_this_round >= wave_size(round)`）
        且 **存活数 <= 0**（`alive <= 0`）
        ↓
★★★ 这才是 retail 的行为
        ↓
★ 定时器只是 **backstop**（兜底）
        ↓
兜底场景："last zombie is stuck behind geometry"（最后一只卡在几何体后）
        ↓
★★★ 避免"hang the match on it"（比赛永远卡住）
```

★★★ **⇒ 这是**极其成熟的边界设计**：**
```
正常路径：靠 `alive <= 0`（精确）
兜底路径：靠定时器（防止永久卡住）
```

★ **⇒ 且 `alive` 由 `entity_killed` 处理器递减（本文件底部）。**

---

## 三、★★★★★ spawn 拒绝计数机制（第 540–569 行）

### 3.1 ★★★ 轮转式选择 spawn 点（第 541–547 行）

```lua
local zone_at = ((cursor - 1) % #spawn_zones) + 1
local c = spawn_zones[zone_at]
local zone, name = c.zone, c.name
point_cursors[zone] = (point_cursors[zone] or 0) + 1
local point_at =
    ((point_cursors[zone] - 1) % #c.point_ids) + 1
local point = c.point_ids[point_at]
```

★★★ **⇒ 两级轮转（zone 轮转 + point 轮转）：**
```
zone_at  = ((cursor - 1) % #spawn_zones) + 1          ← zone 轮转
point_at = ((point_cursors[zone] - 1) % #point_ids) + 1  ← 该 zone 内 point 轮转
```

★ **⇒ 这是**均匀分布**算法（每个 zone / 每个点轮流用）。**

★★ **⇒ `% N + 1` 是 Lua 的 1-based 取模惯例。**

### 3.2 ★★★★★ 拒绝计数（第 548–563 行）

```lua
local key = refusal_key(zone, point)
if (refusals[key] or 0) >= 2 then
    skipped = skipped + 1
else
    local actor, actor_error, actor_code = codol.call(
        "function:zmspawnactor", zone, point,
        zm_actor_model, zm_actor_head)
    if actor ~= nil then
        refusals[key] = nil                  -- ★ 成功 ⇒ 清除计数
        return actor, name, point
    end
    refusals[key] = (refusals[key] or 0) + 1  -- 失败 ⇒ +1
    if actor_code == nil then
        print("zm spawn refused with no code", actor_error)
    end
end
```

### ★★★★★ 完整的拒绝逻辑

```
① 查该点的拒绝计数
② 若已拒绝 >= **2 次** ⇒ 跳过（`skipped += 1`）
③ 否则尝试 `zmspawnactor(zone, point, model, head)`
④ 成功 ⇒ **清除计数**（`refusals[key] = nil`）+ 返回
⑤ 失败 ⇒ 计数 **+1**
⑥ ★ 若 `actor_code == nil`（没有错误码）⇒ 打印警告
```

★★★ **⇒ 三个要点：**
```
① 阈值 = **2 次**（不是 1，也不是无限）
② 成功 ⇒ **清除计数**（该点恢复可用）
③ ★ 无错误码 ⇒ 特殊警告
```

★ **⇒ 第 ② 条是**自愈机制**（点恢复后可以再用）。**

### 3.3 ★★★ 全部拒绝时的**清零重置**（第 565–568 行）

```lua
if skipped >= count and count > 0 and alive < alive_cap(round) then
    print("zm every spawn point struck out, clearing refusal counts")
    refusals = {}
end
return nil
```

★★★ **⇒ 一个关键的**死锁解除**机制：**
```
所有点都被拒绝（`skipped >= count`）
        且 还有余量（`alive < alive_cap(round)`）
        ↓
★★★ **清零所有拒绝计数**（`refusals = {}`）
        ↓
下一轮重试
```

★★ **⇒ 理由：若不清零，一旦所有点都达到 2 次拒绝，就**永远刷不出**。**

★ **⇒ 条件 `alive < alive_cap(round)` 确保**只在"该刷但刷不出"时清零**（不是无脑清）。**

---

## 四、★★★ `begin_round` 的完整实现（第 572–584 行）

```lua
local function begin_round(now)
    round = round + 1
    round_started_at = now
    round_cleared_at = nil
    next_spawn_at = now + round_opening_delay(round)
    spawned_this_round = 0
    local _, round_error = codol.call("function:zmsetround", round, ROUND_GOAL)
    if round_error ~= nil then
        print("zm round hud refused", round_error)
    end
    print("zm round begin", round, "wave", wave_size(round), "zones", #spawn_zones)
end
```

### ★★★ 六个动作

| # | 动作 |
|---|---|
| **1** | `round = round + 1` |
| **2** | `round_started_at = now` |
| **3** | `round_cleared_at = nil` |
| **4** | ★ `next_spawn_at = now + round_opening_delay(round)` |
| **5** | `spawned_this_round = 0` |
| **6** | ★★ **`zmsetround(round, ROUND_GOAL)`**（HUD） |

★★ **⇒ 第 6 条是**唯一的新 API**：`function:zmsetround(round, goal)`。**

★ **⇒ 第 4 条 `round_opening_delay(round)` —— **每回合开场的延迟**（随回合变化）。**

---

## 五、★★★★ `zm_round_tick` 的完整逻辑（第 586–659 行）

### 5.1 ★★★ 首次 tick 的诊断（第 588–597 行）

```lua
if first_director_tick then
    first_director_tick = false
    local observed_players, player_error, player_code =
        codol.call("function:zmplayercount")
    local observed_zone, zone_error, zone_code =
        codol.call("function:zmplayerzone")
    print("zm director first tick", now,
        "players", observed_players, player_error, player_code,
        "zone", observed_zone, zone_error, zone_code)
end
```

★★ **⇒ 首次 tick 打印**玩家数 + zone + 各自的错误码**（完整诊断）。**

### 5.2 ★★★ 1 秒的 zone 跟随（第 602–633 行，逐字）

```lua
-- Follow the player during the round. One second is quick beside the demo's
-- 1.5-second late-round cadence, while avoiding a full zone-model copy on
-- every 100 ms director tick. Empty means the player is between volumes;
-- retain the last valid set until another volume contains them.
if now >= next_zone_check_at then
    next_zone_check_at = now + 1000
```

### ★★★★★ 三个精确的时间参数

| # | 项 | 值 |
|---|---|---|
| **1** | zone 检查间隔 | **1000 ms（1 秒）** |
| **2** | ★ demo 的 late-round cadence | **1.5 秒** |
| **3** | director tick 间隔 | **100 ms** |

★★★ **⇒ 为什么选 1 秒（逐字）：**
```
"One second is quick beside the demo's 1.5-second late-round cadence,
while avoiding a full zone-model copy on every 100 ms director tick."
        ↓
★ 1 秒 = **比 1.5 秒的节奏快**，又**避免每 100 ms 全量复制 zone 模型**
```

### 5.3 ★★★ 空 zone 的保留策略（第 625–626 行，逐字）

```lua
-- Preserve the legacy guard exactly: an empty player-zone answer means
-- that the player is between authored volumes, so retain the last set.
elseif observed_zone ~= nil and observed_zone ~= "" and
    (observed_zone ~= occupied_zone_name or
        observed_players ~= player_count or
        observed_active ~= active_zone_count) then
    configure_spawn_zones(observed_zone, observed_players)
end
```

★★★ **⇒ 关键：空 zone 名的处理：**
```
`zmplayerzone()` 返回空
        ↓
★★★ **意味着玩家在两个 volume 之间**（不是"没有 zone"）
        ↓
★ **保留上一组有效 spawn zones**（不重建）
```

★★ **⇒ 且条件是 **`observed_zone ~= nil and observed_zone ~= ""`** —— 双检查。**

### 5.4 ★★★ 三种变化触发重建（第 628–630 行）

```lua
(observed_zone ~= occupied_zone_name or
    observed_players ~= player_count or
    observed_active ~= active_zone_count)
```

★★★ **⇒ 三个变化中任一 ⇒ 重建 spawn zones：**
```
① zone 名变了
② 玩家数变了
③ 激活 zone 数变了（★ 买门开新区）
```

★ **⇒ 第 ③ 条是**僵尸模式的核心**（买门后需要重建 spawn 池）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **回合间隔实测** | **35.8 秒** / **41.6 秒** |
| 2 | ★★★ 旧实现错误 | **同一 tick 就开下一波** |
| 3 | ★★★★ **回合结束双重判据** | `spawned >= wave_size` **且** `alive <= 0`；定时器**兜底** |
| 4 | ★ 兜底场景 | **最后一只卡在几何体后** |
| 5 | ★★★ spawn 点选择 | **两级轮转**（zone + point） |
| 6 | ★★★ 拒绝阈值 | **2 次** ⇒ 跳过 |
| 7 | ★ 成功处理 | **清除计数**（自愈） |
| 8 | ★★★ **全部拒绝时** | **清零所有计数**（解除死锁） |
| 9 | 清零条件 | `skipped >= count` **且** `alive < alive_cap` |
| 10 | ★ `begin_round` 六动作 | 含 **`zmsetround(round, ROUND_GOAL)`** |
| 11 | ★ 开场延迟 | **`round_opening_delay(round)`**（随回合变） |
| 12 | ★★★ zone 检查间隔 | **1000 ms** |
| 13 | ★ demo late-round cadence | **1.5 秒** |
| 14 | director tick | **100 ms** |
| 15 | ★★★ 空 zone 名 | 玩家在**两个 volume 之间** ⇒ **保留上一组** |
| 16 | ★★ 三种重建触发 | zone 变 / 玩家数变 / **激活 zone 数变** |

---

## 七、结论

### 1. ★★★★★ **回合间隔 35.8s / 41.6s** 是精确的实测还原

★ **⇒ 旧实现"同一 tick 开下一波"是**错误**的。**

### 2. ★★★★★ **回合结束是双重判据**（`alive<=0` 为主 + 定时器兜底）

★ **⇒ 防止"最后一只卡住导致比赛永久卡住"。**

### 3. ★★★★ **spawn 拒绝的阈值 + 自愈 + 死锁解除**三层机制

```
拒绝 >= 2 次 ⇒ 跳过
成功 ⇒ 清除计数（自愈）
全部拒绝 ⇒ 清零重置（解除死锁）
```

### 4. ★★★ **zone 检查 1 秒**的取舍有精确依据（快于 1.5s 节奏，慢于 100ms tick）

### 5. ★★★ **空 zone 名 ≠ 无 zone**（玩家在两个 volume 之间）⇒ 保留上一组

### 6. ★★ **三种变化触发重建**（含"激活 zone 数变"= 买门）

---

## 八、下一步

- `zm.lua` 最后部分（第 660–735 行：`entity_killed` / `player_killed`）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
