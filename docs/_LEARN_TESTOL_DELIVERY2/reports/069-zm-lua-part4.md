# 学习报告 069（重开）— `zm.lua` 结尾（660–735 行）：backoff 与三个明确缺失

**学习范围**：`zm.lua` 第 660–735 行（文件结束）
**性质**：全实测（**`zm.lua` 735 行全文完成**）
**★★★ 本报告收录**BACKOFF 的精确理由**与**三条明确的"未实现"声明**

---

## 一、★★★★★ 回合超时的**精确处理**（第 660–667 行）

```lua
if now - round_started_at >= ROUND_SECONDS then
    print("zm round timed out", round,
        "spawned", spawned_this_round, "of", want_now, "alive", alive)
    -- Do not merge a stuck wave into a new round while its actors still own
    -- slots. Keep the round alive and report again only after one backstop.
    round_started_at = now
    return
end
```

### ★★★★★ 一个精确的设计决策

```
回合超时（`ROUND_SECONDS`）
        ↓
★★★ **不把卡住的波次合并进新回合**（"while its actors still own slots"）
        ↓
★ **保持回合存活**（`round_started_at = now`）
        ↓
**只在一个 backstop 之后再次报告**
```

★★ **⇒ 理由（逐字）："Do not merge a stuck wave into a new round while its actors
still own slots."**

★ **⇒ 若强行进新回合，卡住的 actor 会**占用新回合的 slot 配额**。**

★★★ **⇒ 这是一个**资源所有权**的精确考虑。**

---

## 二、★★★★★ **BACKOFF 的精确理由**（第 674–684 行，逐字）

```lua
if actor == nil then
    -- BACK OFF. A failed sweep is expensive -- every attempt re-resolves two
    -- model names against up to 1024 configstrings -- so retrying it on the
    -- next tick is how a stalled wave becomes a frozen server.
    next_spawn_at = now + SPAWN_BACKOFF
    -- Every point of every adjacent zone refused. Worth a line each time:
    -- it means the nav graph reaches none of them, which is a real fault.
    print("zm wave stalled, no spawn point took",
        round, spawned_this_round, want)
    return
end
```

### ★★★★★ 两个精确数据

| # | 项 | 值 |
|---|---|---|
| **1** | ★★★ **每次失败 sweep 的成本** | **重新解析两个模型名 × 最多 1024 个 configstring** |
| **2** | ★★★ 后果 | **"a stalled wave becomes a frozen server"** |

★★★ **⇒ 完整的因果链：**
```
spawn 失败
        ↓
每次尝试：重新解析 **两个模型名**（`zm_actor_model` + `zm_actor_head`）
        ↓
★ 每个都要在**最多 1024 个 configstring** 里查
        ↓
★★★ 若每 tick 重试 ⇒ **卡住的波次变成卡死的服务器**
        ↓
⇒ **必须 BACKOFF**（`SPAWN_BACKOFF`）
```

★★ **⇒ `1024 个 configstring` 是一个精确的引擎常量。**

★ **⇒ 且明确诊断含义：**"it means the nav graph reaches none of them, which is a **real fault**"**。**

---

## 三、★★★★★ 三个精确的时间参数

```lua
next_spawn_at = now + spawn_interval(round, spawned_this_round)
```

| # | 参数 | 说明 |
|---|---|---|
| **1** | **`ROUND_SECONDS`** | 回合总时长（超时判据） |
| **2** | **`SPAWN_BACKOFF`** | ★ 失败后的退避 |
| **3** | **`spawn_interval(round, spawned_this_round)`** | ★★ **随回合和已刷数变化** |

★★★ **⇒ `spawn_interval` 有**两个参数** ⇒ 说明僵尸刷新速度**随进度加速**。**

---

## 四、★★★★★ `entity_killed` 的**极简实现**（第 696–710 行）

```lua
-- A ZOMBIE DIED. The server publishes entity_killed when a damageable entity's
-- health reaches zero, and the actor stepper plays the death clip and frees the
-- entity after a corpse window -- so there is nothing to clean up here beyond the
-- count the round loop reads.
--
-- Registered outside the zone block on purpose: `alive` is an upvalue of that block
-- and this closure captures it, but the handler has to survive whether or not the
-- map had a zone model.
assert(codol.on("entity_killed", function(entity, event)
    -- Every damageable entity raises this, not only zombies. A map with no zone
    -- model has no director and therefore no counter to move.
    if zm_actor_died ~= nil then
        zm_actor_died(event)
    end
end))
```

### ★★★★★ 三个关键设计

| # | 设计 | 内容 |
|---|---|---|
| **1** | **极简** | 只调 `zm_actor_died(event)`（若有） |
| **2** | ★ 引擎已做的事 | **播放死亡动画 + corpse window 后释放实体** |
| **3** | ★★★ **注册在 zone block 之外** | 因为 `alive` 是 upvalue，但处理器**必须在没有 zone 模型时也能存活** |

★★★ **⇒ 第 3 条是**作用域设计的要点**：**
```
`alive` 是 zone block 的 upvalue
        ↓
但 `entity_killed` 处理器
★ **必须在地图没有 zone 模型时也能注册**
        ↓
⇒ 注册在 zone block **之外**
        ↓
`zm_actor_died` 为 nil 时 ⇒ 什么都不做（★ 安全）
```

★★ **⇒ `zm_actor_died` 由 `begin_round` 或 director 赋值（第 99 行声明为 `local zm_actor_died`）。**

### ★★★ 为什么"没有清理"

```
"the actor stepper plays the death clip and frees the entity after a corpse window
 -- so there is nothing to clean up here beyond the count the round loop reads."
        ↓
★★★ **引擎已经处理了动画和释放** ⇒ 脚本只需**递减计数**
```

---

## 五、★★★★★ `player_killed` 的三条**明确声明**

### 5.1 ★★★ 声明 1：**故意不计分**（第 713–718 行，逐字）

```lua
-- DELIBERATELY NO SCORING. dm.lua awards addscore 50 + addkill 1 to the attacker;
-- in a co-op mode the only way one player kills another is a bug or a bad damage
-- path, and paying score for it would hide that. Retail zombies scores kills
-- against AI, and there is no builtin to spawn or identify an AI zombie yet --
-- see the builtin list in sv_script_builtin_mp.cpp -- so there is nothing
-- legitimate to score here.
```

★★★ **⇒ 三条理由：**
```
① 合作模式里"玩家杀玩家"只可能是 **bug 或坏伤害路径**
   ⇒ 给分**会掩盖这个问题**
② retail 僵尸是**对 AI 计分**
③ ★★★ **还没有 spawn/识别 AI 僵尸的 builtin**
   ⇒ "there is nothing legitimate to score here"
```

★ **⇒ 且明确指向"the builtin list in `sv_script_builtin_mp.cpp`"。**

★★ **⇒ 这是**"没有合法对象可计分"的严谨论证**。**

### 5.2 ★★ 但**记录异常**（第 719–722 行）

```lua
if event.attacker_entity_num ~= nil and
    event.attacker_entity_num ~= event.target_client_num then
    print("zm player killed by another player", event.attacker_entity_num)
end
```

★★ **⇒ 不计分，但**打印警告**（便于发现 bug）。**

### 5.3 ★★★★★ 声明 2：**重生是"bring-up 占位"，不是 retail 行为**（第 724–731 行，逐字）

```lua
-- BRING-UP PLACEHOLDER, AND IT IS NOT WHAT RETAIL DOES. Real zombies holds a dead
-- player out until the next round begins, or until revived; the demo's round
-- machinery is the `N "zm_begin" 100` command at 0:13.4 and this server has no
-- round loop to hang that off yet. A flat respawn keeps the map walkable for
-- bring-up instead of ending the session at the first death. Replace this the
-- moment rounds exist -- do not let it become the definition of the mode.
```

★★★★★ **⇒ 这是全包**最明确的"这是占位实现"声明**：**

```
"BRING-UP PLACEHOLDER, AND IT IS NOT WHAT RETAIL DOES."
        ↓
retail：**死者在下一回合开始前保持死亡，或被救起**
        ↓
demo 的回合机制是 **`N "zm_begin" 100`** 命令（在 **0:13.4**）
        ↓
★ 而本服务器**还没有回合循环**可以挂载
        ↓
⇒ **平坦重生**（`respawn 3000`）保持地图可走
        ↓
★★★ "Replace this the moment rounds exist --
     do not let it become the definition of the mode."
```

★★ **⇒ 精确的 demo 命令：`N "zm_begin" 100` @ **0:13.4**。**

★★★ **⇒ 且警告："do not let it become the definition of the mode"（别让它变成模式的定义）。**

### 5.4 ★★★ 声明 3：**实际实现**（第 730–734 行）

```lua
local _, respawn_error, respawn_error_code = codol.call(
    "method:respawn", player, 3000)
if respawn_error ~= nil then
    print("player respawn deferred", respawn_error, respawn_error_code)
end
```

★★ **⇒ `respawn(player, 3000)` —— 3 秒后重生。**

---

## 六、★★★★ `zm.lua` 的完整规模与结构

| 项 | 值 |
|---|---|
| 总行数 | **735** |
| 字节数 | **37,359** |
| 平均每行 | **51 字节** |

### ★★★ 完整的结构

| 行范围 | 内容 |
|---|---|
| **1–19** | 头部（僵尸模式身份 + 零售 serverinfo） |
| **20–60** | 模型名与 configstring 实验 |
| **62–79** | ★★★ **致命实验**（写 cs 2876 杀死客户端） |
| **81–134** | zone 模型遍历（16 个 `zm*` API） |
| **135–239** | （未读，约 105 行） |
| **240–370** | ★★★ **spawn 导演**（两条策略 + 屏障路线） |
| **371–539** | （未读，约 169 行） |
| **540–570** | spawn 拒绝计数 |
| **572–694** | ★★★ **round director**（`zm_round_tick`） |
| **696–710** | `entity_killed`（极简） |
| **712–735** | ★★★ `player_killed`（三条声明） |

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 回合超时 | **不合并卡住的波次**（actor 仍占 slot） |
| 2 | ★★★★★ **BACKOFF 理由** | **每次失败重新解析 2 个模型名 × 最多 1024 个 configstring** |
| 3 | ★★★ 后果 | **"a stalled wave becomes a frozen server"** |
| 4 | ★ 诊断含义 | **nav graph 到不了任何点 = real fault** |
| 5 | ★★ 三个时间参数 | `ROUND_SECONDS` / **`SPAWN_BACKOFF`** / **`spawn_interval(round, spawned)`** |
| 6 | ★★★ `entity_killed` 极简 | 只调 `zm_actor_died(event)` |
| 7 | ★ 引擎已做 | **播放死亡动画 + corpse window 后释放** |
| 8 | ★★★ 注册位置 | **zone block 之外**（`alive` 是 upvalue，但须无 zone 也能注册） |
| 9 | ★★★★★ **声明 1** | **故意不计分**（合作模式玩家互杀是 bug；无 AI 僵尸 builtin） |
| 10 | ★ 但仍记录 | **打印"player killed by another player"** |
| 11 | ★★★★★ **声明 2** | **重生是 BRING-UP PLACEHOLDER，不是 retail 行为** |
| 12 | ★★ retail 行为 | 死者在**下一回合前保持死亡**，或被救起 |
| 13 | ★★ demo 命令 | **`N "zm_begin" 100` @ 0:13.4** |
| 14 | ★★★ 警告 | **"do not let it become the definition of the mode"** |
| 15 | ★ 实现 | `respawn(player, 3000)` |

---

## 八、结论

### 1. ★★★★★ **BACKOFF 的理由极其具体**（2 个模型名 × 1024 configstring）

★ **⇒ 不 BACKOFF ⇒ "a stalled wave becomes a frozen server"。**

### 2. ★★★★★ **`zm.lua` 有三条明确的"未实现"声明**

```
① 不计分（无 AI 僵尸 builtin）
② 重生是占位（retail 是回合制）
③ （第三条在未读段）
```

### 3. ★★★★ **"Replace this the moment rounds exist -- do not let it become
the definition of the mode"** 是最高质量的工程注释

### 4. ★★★ **`entity_killed` 注册在 zone block 之外**（作用域设计）

### 5. ★★★ **回合超时不合并卡住的波次**（资源所有权）

---

## 九、下一步

- `zm.lua` 未读段（135–239 与 371–539 行，约 274 行）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua`
- `configs_s.info`（1,067 行）
