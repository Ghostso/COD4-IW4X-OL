# 学习报告 072（重开）— `zm.lua` 刷新节奏与拒绝修复（471–542 行）

**学习范围**：`zm.lua` 第 471–542 行（`spawn_interval` / `round_opening_delay` / 拒绝修复）
**性质**：全实测（**性能修复的逐字文档**）
**★★★ 本报告收录**一次 74–497 ms/tick 的性能事故的完整根因分析**与**三条精确模型解析成本**

---

## 一、★★★★★ `spawn_interval` 的**爆发 + 滴流**实现（第 472–486 行，逐字）

```lua
local function spawn_interval(round_number, spawned)
    if factory_solo then
        -- The burst applies to the first eighteen BIRTHS of each round. The
        -- previous code compared the ROUND NUMBER with 5/6, so rounds 1-5
        -- spawned their entire quota every 300 ms and dumped all 25 actors
        -- into one path before the first ones had cleared it.
        if spawned < 18 then return 300 end
        return 1500
    end
    if factory_two_player then
        if spawned < 18 then return 500 end
        return 1500
    end
    return 1500
end
```

### ★★★★★ 完整的三分支表

| 分支 | `spawned < 18` | 否则 |
|---|---|---|
| **`factory_solo`** | **300 ms** | **1500 ms** |
| **`factory_two_player`** | **500 ms** | **1500 ms** |
| **其他地图** | — | **1500 ms** |

★★★ **⇒ 爆发只对**每回合的前 18 个"出生"**（"the first eighteen **BIRTHS**"）。**

### ★★★★★ 一个精确的**实现错误**（逐字）

```lua
-- The previous code compared the ROUND NUMBER with 5/6, so rounds 1-5
-- spawned their entire quota every 300 ms and dumped all 25 actors
-- into one path before the first ones had cleared it.
```

★★★ **⇒ 错误因果链：**
```
旧代码：拿**回合号**与 5/6 比
        ↓
★ 所以回合 1–5 全部：**每 300 ms 刷一个**（整轮配额）
        ↓
★★★ **25 个 actor 全倒进同一条路**，而前面的还没清掉
```

★ **⇒ 正确做法：拿**已刷数**（`spawned`）与 18 比。**

★★ **⇒ 这是**拿错变量做比较**的经典 bug（回合号 vs 已刷数）。**

★★ **⇒ 且与报告 070 的"旧实现：固定间隔从 0 开始 ⇒ 一分钟才建起一波"**是**同一个 bug 的两次描述**：**
```
报告 070 的表述：spawn 形状错（固定间隔 ⇒ 一分钟建起）
本报告的表述：拿回合号比较 ⇒ 回合 1–5 每 300 ms 全倒完
        ↓
★ 两者都指向"没有 burst 阶段"
```

---

## 二、★★★★★ `round_opening_delay` 的**精确实测**（第 488–496 行，逐字）

```lua
local function round_opening_delay(n)
    if n == 1 then return ROUND_ONE_DELAY end
    if factory_two_player then
        -- 20-34-14 asserts the first birth 600 ms after the HUD in rounds
        -- 2..6 and 500 ms after it in rounds 7..8.
        return (n <= 6) and 600 or 500
    end
    return NEXT_ROUND_DELAY
end
```

### ★★★★★ 三分支表

| 分支 | 条件 | 值 |
|---|---|---|
| **第 1 回合** | `n == 1` | **`ROUND_ONE_DELAY` = 5500 ms** |
| **two-player 回合 2–6** | `n <= 6` | **600 ms** |
| **two-player 回合 7–8** | `n >= 7` | **500 ms** |
| **其他** | — | **`NEXT_ROUND_DELAY` = 400 ms** |

★★★ **⇒ two-player 的两个精确实测值（逐字）：**
```
"20-34-14 asserts the first birth **600 ms after the HUD** in rounds 2..6
 and **500 ms after it** in rounds 7..8."
        ↓
★ 基准点是 **HUD**（不是回合开始时刻）
★ 回合 2–6：**600 ms**；回合 7–8：**500 ms**（★ 后期更快）
```

★★ **⇒ 出处：demo `20-34-14`。**

★ **⇒ 这是一个**极其精细的还原**（连 600 → 500 ms 的加速都还原了）。**

---

## 三、★★★★★ **拒绝修复**的完整故事（第 498–506 行，逐字）

```lua
-- ONE ACTOR, TRYING EVERY POINT OF EVERY ZONE UNTIL ONE TAKES.
--
-- THE REFUSAL FIX. `spawnZombieActor` refuses a spawn point whose goal the nav
-- graph cannot walk -- 12.80, because spawning one is strictly worse than not:
-- it holds an entity number, it is drawn, and it can never move. The old loop
-- read that as "this zone is done", so bridge_zone, outside_south_zone and
-- tp_east_zone each lost their whole turn to an unroutable point 1. Every point
-- is tried now, and the cursor advances zone-major so a wave spreads across the
-- adjacent zones instead of stacking on one.
```

### ★★★★★ 完整的因果链

```
`spawnZombieActor` 拒绝"导航图走不到"的 spawn 点
        ↓
★★★ 理由（12.80，逐字）："spawning one is strictly worse than not:
   **it holds an entity number, it is drawn, and it can never move**"
        ↓
★★★ 但**旧循环把拒绝读成"这个 zone 用完了"**
        ↓
★ 结果：`bridge_zone` / `outside_south_zone` / `tp_east_zone`
   **三个 zone 各自因为"点 1 不可达"而丢掉整轮机会**
        ↓
⇒ 修复：**尝试每一个点**
        ↓
★ 且 **cursor 按 zone 为主序推进** ⇒ 波次散布在相邻 zone
```

★★★ **⇒ 三个精确命名的受害 zone：**
```
① `bridge_zone`
② `outside_south_zone`
③ `tp_east_zone`
```

★★ **⇒ 三个受害原因完全相同：**"an unroutable **point 1**"。**

★ **⇒ 出处：`12.80`。**

### ★★★ 为什么拒绝是对的（逐字）

```
"spawning one is **strictly worse** than not:
 it **holds an entity number**, it **is drawn**, and it **can never move**."
        ↓
★★★ **三个具体代价：占用实体号 + 被绘制 + 永远不能动**
```

---

## 四、★★★★★ **性能事故的完整根因**（第 508–525 行，逐字）

```lua
-- REFUSAL COUNTS PER SPAWN POINT, and this is the whole performance fix.
--
-- MEASURED with SCRIPTSLOW: one zm_round_tick event took 74-497 MILLISECONDS,
-- repeatedly, and that lands in the server's `thinkUs` window because the Lua
-- dispatch runs inside the per-command loop the think timer wraps. On screen it
-- was heavy lag and rubber-banding.
--
-- The cost is `zmspawnactor` re-resolving the body and head model BY NAME on
-- every call: `resolveModelConfigStringIndex` walks up to 1024 configstrings
-- doing string compares, plus a findXAsset, twice per attempt. Trying 22 points
-- a tick is ~45,000 configstring reads a tick.
--
-- Routability is a property of the map's nav graph and does not change during a
-- match, so a point that refuses will refuse again. Two strikes rather than one
-- because a refusal is also what an exhausted entity pool returns, and that is
-- transient -- both come back as WorldMutationFailed and the script cannot tell
-- them apart. If every point ends up struck out the counters reset, so a
-- transient wipeout heals instead of ending the mode.
```

### ★★★★★ 完整的性能数据链

```
① ★★★ **一次 `zm_round_tick` 耗时 74–497 毫秒**（反复出现）
        ↓
② 落在服务器的 **`thinkUs` 窗口**内
   （因为 Lua dispatch 跑在 think 计时器包裹的 per-command 循环里）
        ↓
③ ★★★ 屏幕上的表现：**heavy lag and rubber-banding**（严重卡顿 + 橡皮筋）
        ↓
④ ★★★ 成本来源：`zmspawnactor` **每次调用都按名字重新解析 body + head 模型**
        ↓
⑤ ★★★ 解析细节：
   `resolveModelConfigStringIndex` **最多遍历 1024 个 configstring 做字符串比较**
   **+ 一次 `findXAsset`**
   **× 每次尝试要两遍**（body + head）
        ↓
⑥ ★★★ **每 tick 试 22 个点 ⇒ 约 45,000 次 configstring 读取/tick**
```

### ★★★★★ 四个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | 单次 `zm_round_tick` 耗时 | **74–497 毫秒** |
| **2** | `resolveModelConfigStringIndex` 上限 | **1024 个 configstring** |
| **3** | 每次尝试的解析次数 | **2 次**（body + head） |
| **4** | **每 tick 的 configstring 读取** | **~45,000 次** |

★★★ **⇒ 第 4 条的算式：**
```
22 个点 × 2 次解析 × 1024 个 configstring
= 22 × 2 × 1024
= **45,056** ⇒ 约 **45,000**
```

★ **⇒ 这是一个**可以手算验证的数字**（证明作者真的量过）。**

### ★★★★★ 为什么"两次出局"而不是"一次"（逐字）

```lua
-- Two strikes rather than one because a refusal is also what an exhausted entity
-- pool returns, and that is transient -- both come back as WorldMutationFailed
-- and the script cannot tell them apart.
```

★★★ **⇒ 两种拒绝**无法区分**：**
```
① 导航图不可达  ⇒ **永久**（地图属性）
② 实体池耗尽    ⇒ ★ **暂时**（可恢复）
        ↓
★★★ 两者都返回 **`WorldMutationFailed`**
        ↓
★ 脚本**无法区分**
        ↓
⇒ 所以用 **2 次出局**（给暂时性的情况一次机会）
```

★ **⇒ 关键的引擎细节：**两种失败的返回码**完全相同**（都是 `WorldMutationFailed`）。**

★★ **⇒ 这是**在信息不足下做的保守设计**。**

### ★★★ 自愈机制（第 524–525 行）

```lua
-- If every point ends up struck out the counters reset, so a
-- transient wipeout heals instead of ending the mode.
```

★★ **⇒ 与报告 068 记录的"清零重置"**一致**（但本段给出了**更完整的理由**）。**

★ **⇒ 理由："a transient wipeout **heals** instead of **ending the mode**"。**

---

## 五、★★★ `refusal_key` 与 `spawn_one` 的开头（第 526–542 行）

```lua
local refusals = {}
local point_cursors = {}
local function refusal_key(zone, point)
    return zone * 1000 + point
end
local function spawn_one()
    local count = 0
    for i = 1, #spawn_zones do
        count = count + #spawn_zones[i].point_ids
    end
    local attempts = 0
    local skipped = 0
    while attempts < count do
        cursor = cursor + 1
        attempts = attempts + 1
        local zone_at = ((cursor - 1) % #spawn_zones) + 1
        local c = spawn_zones[zone_at]
```

### ★★★ 三个实现细节

| # | 细节 | 说明 |
|---|---|---|
| **1** | **`refusal_key(zone, point) = zone * 1000 + point`** | ★ 用乘 1000 编码复合键（point < 1000） |
| **2** | **`count`** = 所有委托 zone 的点数总和 | 循环上界 |
| **3** | **`while attempts < count`** | ★ 最多尝试 `count` 次（每点一次） |

★★ **⇒ 第 1 条是一个**Lua 里没有元组键的常见绕过**（`zone*1000+point`）。**

★ **⇒ 隐含约束：`point` 必须 < 1000（否则键冲突）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★ **`spawn_interval` 三分支** | solo **300/1500** · two-player **500/1500** · 其他 **1500** |
| 2 | ★ 爆发范围 | **每回合前 18 个"出生"** |
| 3 | ★★★★★ **旧实现错误** | 拿**回合号**与 5/6 比 ⇒ 回合 1–5 **每 300 ms 全倒完** |
| 4 | 后果 | **25 个 actor 全倒进同一条路** |
| 5 | ★★★★ **`round_opening_delay`** | 回合 1 = **5500**；two-player 2–6 = **600**，7–8 = **500**；其他 = **400** |
| 6 | ★ 基准点 | **HUD**（不是回合开始） |
| 7 | ★★★ 出处 | demo **`20-34-14`** |
| 8 | ★★★★★ **拒绝修复** | 旧循环把拒绝读成"**这个 zone 用完了**" |
| 9 | 受害 zone | **`bridge_zone` / `outside_south_zone` / `tp_east_zone`**（都因**点 1 不可达**） |
| 10 | ★ 修复 | 尝试**每一个点** + cursor **zone-major** 推进 |
| 11 | ★★★ 拒绝正确的理由 | 占用实体号 + 被绘制 + **永远不能动** |
| 12 | ★★★★★ **性能事故** | **74–497 毫秒/tick**，屏幕表现 **heavy lag + rubber-banding** |
| 13 | ★★★ 解析成本 | **1024 个 configstring** 字符串比较 + `findXAsset`，**每次 2 遍** |
| 14 | ★★★★★ **每 tick 读取数** | **~45,000**（22 × 2 × 1024） |
| 15 | ★★★★ **两次出局的理由** | 不可达（永久）与**实体池耗尽（暂时）**都返回 **`WorldMutationFailed`** |
| 16 | ★ 自愈 | 全部出局 ⇒ 清零（"heals instead of ending the mode"） |
| 17 | ★ `refusal_key` | `zone * 1000 + point` |
| 18 | ★ `spawn_one` 上界 | `while attempts < count`（每点最多一次） |

---

## 七、结论

### 1. ★★★★★ **性能事故的根因可手算验证**（22 × 2 × 1024 ≈ 45,000）

★ **⇒ 74–497 ms/tick ⇒ heavy lag + rubber-banding。**

### 2. ★★★★★ **"两次出局"的设计源于一个引擎限制**

```
导航不可达（永久）与实体池耗尽（暂时）
★ **都返回 `WorldMutationFailed`** ⇒ 脚本无法区分
        ↓
⇒ 必须给暂时性情况一次机会
```

### 3. ★★★★★ **旧循环把"点拒绝"读成"zone 用完了"**

★ **⇒ 三个 zone 各因**点 1 不可达**而丢掉整轮。**

### 4. ★★★★ **`round_opening_delay` 连 600 → 500 ms 的加速都还原了**

### 5. ★★★★ **爆发只对前 18 个"出生"**（不是前 5 回合）

★ **⇒ 旧实现拿回合号比较是**拿错变量**。**

### 6. ★★★ **`spawnZombieActor` 拒绝不可达点是**正确的**（三个具体代价）**

---

## 八、下一步

- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
- `mp_playlists_shipRetail_release.info`（3,970 行）
