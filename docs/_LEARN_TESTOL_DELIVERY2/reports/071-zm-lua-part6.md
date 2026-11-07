# 学习报告 071（重开）— `zm.lua` 波次配额与性能事故（371–470 行）

**学习范围**：`zm.lua` 第 371–470 行（zone 选择收尾 + 波次表 + 两处上限）
**性质**：全实测（**全包最严重的性能事故记录**）
**★★★ 本报告收录**一次 SCRIPTSLOW 1.0–2.3 秒/tick 的完整事故**与**两组精确波次数据**

---

## 一、★★★★★ 两组精确的波次表（第 403–416 行，逐字）

### 1.1 ★★★ solo（单人）波次表

```lua
-- THE PER-ROUND QUOTA AND THE CONCURRENCY CAP, both measured.
--
-- Full one-player factory rounds read directly from
-- C-2021-7-31[15-32-16]zm.demo. The old 24/29/34/39 extrapolation was one low
-- in every round. Round 9 is incomplete in the demo, so only its continuation
-- (+2 from the late-round curve) remains an explicit inference.
local solo_factory_waves = {25, 30, 35, 40, 45, 52, 54, 56, 58}
```

### ★★★★★ solo 的九回合完整数据

| 回合 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| **波次大小** | **25** | **30** | **35** | **40** | **45** | **52** | **54** | **56** | **58** |

★★★ **⇒ 完整的九回合数据（直接从 demo 读出）。**

★★ **⇒ 且明确纠正了旧值：**
```
旧外推：**24 / 29 / 34 / 39**
        ↓
★★★ "was **one low in every round**"
        ↓
正确：**25 / 30 / 35 / 40**
```

★ **⇒ 旧值是**每回合少 1**（典型的 off-by-one）。**

★★ **⇒ 第 9 回合 demo 不完整 ⇒ `58` 是外推（`+2 from the late-round curve`）。**

### 1.2 ★★★ two-player 波次表

```lua
-- The other two factory captures each carry two client rows. The complete
-- 20-34-14 rounds measure 36/42/48/54/64/68/73 for rounds 2..8;
-- 20-21-43 independently measures 68/72 for rounds 7/8. Round 1 (30) and
-- final-round 76 are continuations, while round 8 uses the lower of the two
-- actually observed values rather than pretending the one-actor spread does
-- not exist.
local two_player_factory_waves = {30, 36, 42, 48, 54, 64, 68, 72, 76}
```

### ★★★★★ two-player 的九回合数据

| 回合 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| **波次大小** | **30** | **36** | **42** | **48** | **54** | **64** | **68** | **72** | **76** |

★★★ **⇒ 两份 demo 交叉验证：**
```
demo `20-34-14`：36/42/48/54/64/68/73（回合 2..8）
demo `20-21-43`：68/72（回合 7/8）
        ↓
★★★ 回合 8 有分歧：**73 vs 72**
        ↓
★ 采用**较低的 72**（"rather than pretending the one-actor spread does not exist"）
```

★★ **⇒ 这是一个**保守取值**的决定（承认观测有 1 个 actor 的波动）。**

### 1.3 ★★★ 三个分支的完整实现（第 417–425 行）

```lua
local function wave_size(n)
    if factory_solo then
        return solo_factory_waves[n] or (58 + 2 * (n - 9))
    end
    if factory_two_player then
        return two_player_factory_waves[n] or (76 + 4 * (n - 9))
    end
    return 25 + 5 * (n - 1)
end
```

★★★ **⇒ 三条公式：**
```
factory_solo        ⇒ 表查（1-9），超出则 `58 + 2*(n-9)`（★ +2/回合）
factory_two_player  ⇒ 表查（1-9），超出则 `76 + 4*(n-9)`（★ +4/回合）
其他地图            ⇒ `25 + 5*(n-1)`（★ +5/回合，通用外推）
```

★ **⇒ 三个不同的斜率：solo **+2** / two-player **+4** / 通用 **+5**。**

---

## 二、★★★★★ **一次完整的性能事故**（第 426–443 行，逐字）

```lua
-- THIS SERVER CANNOT HOLD RETAIL'S NUMBER, AND PRETENDING OTHERWISE COSTS 1.6 s
-- A TICK.
--
-- Retail runs 27/30/31 concurrent at rounds 2/3/4 (12.165). This server allocates
-- an agent slot per actor from `MaximumGameClients (18) .. SvAgentSlotCount (32)`
-- -- FOURTEEN slots -- and `spawnZombieActor` refuses once they are gone.
--
-- With the cap set to the measured 26 the director believed it had room, every
-- spawn past the 14th refused, and `spawn_one` ran its whole sweep (4 barrier
-- points, then all 22) every tick with two 1024-configstring model resolves per
-- attempt. Measured: `zm wave stalled ... 14 of 24` repeating, SCRIPTSLOW 1.0-2.3
-- SECONDS per tick, thinkUs peaking at 8.3 s. The strike-out logic made it worse
-- by clearing its counters whenever everything was struck out, so it never
-- settled.
```

### ★★★★★ 完整的因果链

```
① 零售并发数：**27 / 30 / 31**（回合 2/3/4）
        ↓
② 但本服务器的 agent slot 只有 **14 个**
   （`MaximumGameClients (18) .. SvAgentSlotCount (32)`）
        ↓
③ ★ 而 cap 被设成**实测的 26** ⇒ director 以为还有空间
        ↓
④ 第 14 个之后的**每次 spawn 都被拒绝**
        ↓
⑤ `spawn_one` **每 tick 跑完整 sweep**（4 个 barrier 点 + 全部 22 个）
        ↓
⑥ ★★ 每次尝试**两次 1024-configstring 模型解析**
        ↓
⑦ ★★★ **实测：`zm wave stalled ... 14 of 24` 反复出现**
        ↓
⑧ ★★★ **SCRIPTSLOW 1.0–2.3 秒/tick**
        ↓
⑨ ★★★ **thinkUs 峰值 8.3 秒**
        ↓
⑩ ★★ strike-out 逻辑**每次全部失败就清计数** ⇒ **永不收敛**
```

★★★ **⇒ 五个精确数字：**
```
agent slot：**14 个**（18..32）
cap 错误值：**26**
sweep 大小：**4 barrier + 22 全部**
SCRIPTSLOW：**1.0–2.3 秒/tick**
thinkUs 峰值：**8.3 秒**
```

★★ **⇒ 第 ⑩ 条揭示了报告 068 的"strike-out 清零"逻辑**反而是帮凶**：**
```
全部失败 ⇒ 清计数
        ↓
下一 tick 又全部重试
        ↓
★★★ **永不收敛** ⇒ 每 tick 都跑完整 sweep
```

★ **⇒ 这是**一个"看起来正确"的机制在极端情况下变成灾难**。**

### ★★★ 修复（第 441–443 行）

```lua
-- IDA's sub_471980 confirms a separate five-bit, 32-slot ACTORS namespace.
-- The server now keeps players in CLIENTS on zm and returns a slot when an actor
-- corpse is freed, so the measured solo peaks are representable.
```

★★★ **⇒ 两个关键发现：**
```
① ★★★ IDA 的 `sub_471980` 确认存在**独立的 5 位 / 32 槽 ACTORS 命名空间**
② 修复：zm 上**玩家放 CLIENTS**，actor 尸体释放时**归还槽位**
```

★ **⇒ `5 位 = 32 槽`（`2^5 = 32`）—— 精确的位宽。**

---

## 三、★★★★★ 两处上限（第 444–470 行）

### 3.1 ★★★ `ACTOR_SLOT_CAP = 32`

```lua
local ACTOR_SLOT_CAP = 32
```

★ **⇒ 与 `sub_471980` 的 32 槽一致。**

### 3.2 ★★★★★ `IMPLEMENTATION_ALIVE_CAP = 4`（第 445–454 行，逐字）

```lua
-- Retail reaches 25 living actors in round one for only 0.6 seconds: its first
-- death follows immediately and the population then drains.  Our provisional
-- actors do not yet have retail's complete damage/death lifecycle, so allowing
-- that transient peak to become a permanent population leaves all 25 animtrees,
-- routes and snapshots active forever.  Limit the provisional implementation to
-- four live actors while pathing is validated. This is not a replacement wave
-- size: keep the retail quota below and feed replacements after entity_killed
-- until all 25 have lived. Raise this compatibility ceiling only after live actor
-- processing stays inside the server-frame budget.
local IMPLEMENTATION_ALIVE_CAP = 4
```

### ★★★★★ 完整的理由链

```
① 零售第 1 回合达到 **25 个活 actor**，但**只持续 0.6 秒**
   （第一次死亡立即跟上，population 随后排空）
        ↓
② ★★★ 我们的临时 actor **还没有完整的 damage/death 生命周期**
        ↓
③ 若允许那个瞬时峰值变成**永久 population**
        ↓
★★★ **25 个 animtree + 路线 + 快照永久活跃**
        ↓
④ ⇒ **限制为 4 个活 actor**（同时验证 pathing）
        ↓
⑤ ★★★ "This is **not a replacement wave size**"
   ⇒ 零售配额（25）保持，`entity_killed` 后补刷，直到 25 个都活过
        ↓
⑥ ★ 提升条件："only after live actor processing stays inside the server-frame budget"
```

★★★ **⇒ 第 ⑤ 条是**关键的语义区分**：**
```
`IMPLEMENTATION_ALIVE_CAP = 4`  ⇒  **同时存活**上限（不是波次大小）
`solo_factory_waves[1] = 25`    ⇒  **波次总配额**
        ↓
★★★ 两者**独立**：一次只活 4 个，但一回合总共要刷 25 个
```

★ **⇒ 这是**一个极其聪明的兼容性折中**（既能验证 pathing，又不放弃零售配额）。**

★★ **⇒ 第 ⑥ 条给出**提升条件**（server-frame budget）。**

### 3.3 ★★★ `alive_cap` 的实现（第 455–470 行）

```lua
local solo_factory_alive_caps = {25, 27, 30, 31, 31, 31, 31, 31, 31}
local function alive_cap(n)
    local cap
    if factory_solo then
        cap = solo_factory_alive_caps[n] or 31
    elseif factory_two_player then
        cap = 31
    else
        cap = 25 + n
    end
    if cap > ACTOR_SLOT_CAP then cap = ACTOR_SLOT_CAP end
    if cap > IMPLEMENTATION_ALIVE_CAP then
        cap = IMPLEMENTATION_ALIVE_CAP
    end
    return cap
end
```

★★★ **⇒ `solo_factory_alive_caps` 的九回合数据：**
```
{25, 27, 30, 31, 31, 31, 31, 31, 31}
```

★★ **⇒ 与报告 070 的实测表**完全对应**：**
```
round 2: 27 ✓
round 3: 30 ✓
round 4: 31 ✓
```

★ **⇒ 第 1 回合是 25（零售峰值）。**

★★★ **⇒ 最终 `cap` 被**两次钳制**：**
```
cap = min(cap, ACTOR_SLOT_CAP = 32)
cap = min(cap, IMPLEMENTATION_ALIVE_CAP = 4)
        ↓
★★★ **最终 cap 恒为 4**
```

★ **⇒ 所以 `alive_cap(n)` **现在恒返回 4**（除非未来提升 `IMPLEMENTATION_ALIVE_CAP`）。**

---

## 四、★★★★★ zone 选择的**最终决策**（第 378–400 行）

```lua
local selection = "adjacent fallback"
if #barrier_spawn_zones > 0 then
    spawn_zones = barrier_spawn_zones
    selection = "barrier routes"
else
    spawn_zones = all_spawn_zones
end
...
if #spawn_zones == 0 then
    -- Fail closed. Falling back to every authored zone is precisely how
    -- unopened rooms started spawning zombies before their doors were bought.
    print("zm has no active routable spawn zone; spawning paused")
end
return #spawn_zones > 0
```

### ★★★★★ 两级优先 + fail-closed

```
① 若有**屏障路线点** ⇒ 用 `barrier_spawn_zones`（selection = "barrier routes"）
② 否则 ⇒ 用 `all_spawn_zones`（selection = "adjacent fallback"）
③ ★★★ 若**空** ⇒ **fail closed**（暂停，不刷）
```

★★★ **⇒ 第 ③ 条的理由（逐字）：**
```
"Falling back to **every authored zone** is precisely how
**unopened rooms started spawning zombies before their doors were bought**."
        ↓
★★★ ⇒ 若回退到"所有创作 zone" ⇒ **未开门的房间会提前刷僵尸**
```

★★ **⇒ 这与报告 067 的"Authored ≠ opened"**完全呼应**。**

---

## 五、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **solo 波次表** | **25/30/35/40/45/52/54/56/58** |
| 2 | ★★★ 旧值纠正 | **24/29/34/39** ⇒ **每回合少 1** |
| 3 | ★★★★★ **two-player 波次表** | **30/36/42/48/54/64/68/72/76** |
| 4 | ★ 分歧处理 | 回合 8 **73 vs 72** ⇒ 取**较低 72** |
| 5 | ★★ 三条斜率 | solo **+2** / two-player **+4** / 通用 **+5** |
| 6 | ★★★★ **agent slot 数** | **14**（`MaximumGameClients 18 .. SvAgentSlotCount 32`） |
| 7 | ★★★★★ **性能事故** | cap=26 ⇒ **SCRIPTSLOW 1.0–2.3 秒/tick**，**thinkUs 峰值 8.3 秒** |
| 8 | 事故现象 | **`zm wave stalled ... 14 of 24` 反复** |
| 9 | ★★ strike-out 帮凶 | 每次全失败就清计数 ⇒ **永不收敛** |
| 10 | ★★★ **IDA 发现** | **`sub_471980` 独立 5 位 / 32 槽 ACTORS 命名空间** |
| 11 | 修复 | zm 上玩家放 **CLIENTS**，尸体释放时**归还槽位** |
| 12 | ★ `ACTOR_SLOT_CAP` | **32** |
| 13 | ★★★★★ **`IMPLEMENTATION_ALIVE_CAP`** | **4**（同时存活上限，**不是波次大小**） |
| 14 | 理由 | 零售峰值 **25 个只持续 0.6 秒**；我们没有完整死亡生命周期 |
| 15 | ★ 提升条件 | **server-frame budget** 内 |
| 16 | ★ `solo_factory_alive_caps` | **25/27/30/31/31/31/31/31/31** |
| 17 | ★★★ 两次钳制 | `min(cap, 32)` 然后 `min(cap, 4)` ⇒ **恒为 4** |
| 18 | ★★★★ **zone fail-closed** | 空 ⇒ **暂停**（否则**未开门房间会提前刷**） |

---

## 六、结论

### 1. ★★★★★ **一次完整的性能事故**（SCRIPTSLOW 1.0–2.3 秒/tick）

```
cap 设成 26（实测值）
        ↓
但实际只有 14 个 slot
        ↓
每 tick 跑完整 sweep（4+22 点 × 2 次 1024-configstring 解析）
        ↓
★★★ SCRIPTSLOW 1.0–2.3 秒/tick，thinkUs 峰值 8.3 秒
```

★ **⇒ 而 strike-out 清零逻辑**反而让问题永不收敛**。**

### 2. ★★★★★ **`IMPLEMENTATION_ALIVE_CAP = 4` 是极聪明的折中**

```
零售峰值 25 个只持续 0.6 秒
        ↓
我们没有完整死亡生命周期 ⇒ 25 个会永久活跃
        ↓
★ 限制同时存活 4 个，但**波次配额保持 25**
```

### 3. ★★★★ **两组精确波次表**（solo 25-58 / two-player 30-76）

★ **⇒ 旧值每回合少 1（off-by-one）。**

### 4. ★★★ **`sub_471980` 的 32 槽 ACTORS 命名空间**（IDA 确认）

### 5. ★★★ **zone 空时 fail-closed**（否则未开门房间会提前刷）

---

## 七、下一步

- `zm.lua` 剩余（第 470–540 行，约 70 行）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
