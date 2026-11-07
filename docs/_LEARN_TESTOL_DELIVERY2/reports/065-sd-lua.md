# 学习报告 065（重开）— `sd.lua` 全文（335 行）

**学习范围**：`payload\Ayria\Assets\OlMod\GameScripts\gametypes\sd.lua`（20,121 B / 335 行）
**性质**：全实测
**★★★ 本报告收录**`playfxat` 的 double 类型契约**与**十个 SD 事件观察器**

---

## 一、★★★★★ `playfxat` 的 **double 类型契约**（第 229–245 行，逐字）

```lua
-- The builtin takes the index as int64 and ALL SIX
-- transform components as doubles (sv_script_builtin_mp.cpp:
-- 2395-2415: std::get_if<double> per component, else
-- InvalidArgumentType "six finite transform numbers").
-- Integer LITERALS therefore fail the type check: the live
-- log carried exactly that --
--   kill fx failed impacts/deathfx_bloodpool_view
--   playfxat expects six finite transform numbers 3
-- so every component is forced through a float multiply
-- rather than passed as a bare literal.
local fx_x = origin[1] * 1.0
local fx_y = origin[2] * 1.0
local fx_z = origin[3] * 1.0
local _, fx_error, fx_code = codol.call(
    "function:playfxat", fx_index,
    fx_x, fx_y, fx_z,
    0.0 * 1.0, 0.0 * 1.0, 0.0 * 1.0)
```

### ★★★★★ 完整的类型契约

| 参数 | 类型 | 说明 |
|---|---|---|
| `fx_index` | **int64** | 特效索引 |
| 六个 transform 分量 | **double** | ★★★ **必须是 double** |

★★★ **⇒ 三个精确事实：**
```
① `std::get_if<double>` 逐分量检查
② 失败报 `InvalidArgumentType "six finite transform numbers"`
③ ★★★ **整数 LITERAL 会失败**（Lua 的 `3` 是 integer，不是 double）
```

### ★★★★★ 实测的错误日志（逐字）

```
kill fx failed impacts/deathfx_bloodpool_view
playfxat expects six finite transform numbers 3
```

★★★ **⇒ 错误信息里的 `3` 就是那个被拒绝的整数参数。**

★ **⇒ 这是**Lua 5.3+ 的 integer/float 区分的坑**：**
```
Lua 5.3+ 区分 integer 与 float
        ↓
`0` 是 integer，`0.0` 是 float
        ↓
★★★ C++ 的 `std::get_if<double>` 只接受 float
        ↓
所以必须 `origin[1] * 1.0`（强制转 float）
```

★★ **⇒ `0.0 * 1.0` 这个写法看起来多余，但**是为了保证结果是 float**（防止编译器优化成 integer）。**

★ **⇒ 这是**极其具体的跨语言类型契约**。**

---

## 二、★★★★★ `KILL_FX_FALLBACK = nil` 的**证伪记录**（第 123–128 行）

```lua
-- DELIBERATELY OFF. Enabling a generic fallback re-creates the exact defect this
-- ticket removes: an effect for every weapon swallows the per-weapon one. The
-- withdrawn V1.101-B build proved it in production -- all 62/62 live kills fell
-- through to the fallback (回档V1.10-否决B+C-并发写者与rope1d摘除-20261011-1556.md:13).
-- Set to an effect name only for a deliberate, single-variable experiment.
local KILL_FX_FALLBACK = nil
```

### ★★★★★ 一次生产环境的完整证伪

```
V1.101-B 版本：启用了 generic fallback
        ↓
★★★ **all 62/62 live kills fell through to the fallback**
        ↓
★ 每把武器的专属特效都被"通用兜底"吞掉
        ↓
已回档（V1.10）
```

★★★ **⇒ 62/62 = **100% 的击杀**都走了 fallback。**

★ **⇒ 出处（中文路径）：**
```
回档V1.10-否决B+C-并发写者与rope1d摘除-20261011-1556.md:13
```

★★ **⇒ 且明确："Set to an effect name only for a **deliberate, single-variable experiment**."**

★ **⇒ 这是**又一次"单变量"纪律**（与报告 057/059 一致）。**

---

## 三、★★★★★ SD 的**计分特殊性**（第 130–141 行）

```lua
-- WHY THIS CALLBACK EXISTS (V1.8).
-- Search & destroy's TEAM score is the ROUND count and is awarded in C++:
-- advanceSdRound() -> setTeamScore(winner, +1) (sv_main_mp.cpp:6825-6826), and
-- evaluateMatchLimits() reads clients_.teamScore(Tf/Sc) against rules.scoreLimit
-- (sv_main_mp.cpp:2944-2955). This file must therefore NEVER call
-- method:addteamscore -- that counter is per KILL, so awarding it in sd would end
-- the match after scoreLimit kills instead of after scoreLimit ROUNDS.
```

### ★★★★★ SD 与其他模式的**根本区别**

```
SD 的队伍分 = **回合数**
        ↓
由 C++ 的 `advanceSdRound() -> setTeamScore(winner, +1)` 给
        ↓
★★★ **脚本绝不能调 `method:addteamscore`**
        ↓
因为那是**每击杀**计数 ⇒ 会变成"scoreLimit 次**击杀**后结束"
而不是"scoreLimit 个**回合**后结束"
```

★★★ **⇒ 这是**一个极其危险的错误**：**
```
若 sd.lua 调 addteamscore
        ↓
队伍分 = 击杀数（不是回合数）
        ↓
★★★ 比赛在 scoreLimit 次击杀后结束 ⇒ **完全错误**
```

★ **⇒ 精确的两个出处：**
```
advanceSdRound() -> setTeamScore(winner, +1)   sv_main_mp.cpp:6825-6826
evaluateMatchLimits() 读 teamScore             sv_main_mp.cpp:2944-2955
```

### ★★★ 但**个人击杀**仍需脚本（第 138–141 行）

```lua
-- The PER-PLAYER side is what sd had no producer for: the HUD kill counter and
-- the scoreboard kill column, written only by addKillForClient()
-- (sv_client_mp.cpp:2253) and called by nobody before this file ("nothing awards
-- it on its own" -- the same gap war.lua:8-16 documents for team score).
```

★★★ **⇒ 分工：**
```
队伍分  →  C++ 给（回合数）
个人击杀 →  ★ 脚本给（`addKillForClient` @ `sv_client_mp.cpp:2253`）
```

★ **⇒ 且明确："nothing awards it on its own"。**

---

## 四、★★★★ SD 的完整计分实现（第 148–195 行）

```lua
assert(codol.on("player_killed", function(player, event)
    local ok, failure = pcall(function()
        if event.attacker_entity_num ~= nil and
            event.attacker_entity_num ~= event.target_client_num then
            local attacker = codol.player(event.attacker_entity_num)
            local same_team, team_error = codol.call(
                "method:issameteam", player, attacker)
            if team_error ~= nil then
                print("team check deferred", team_error)
            elseif not same_team then
                -- XP 50 + 爆头 +50
                local _, xp_error, xp_error_code = codol.call("method:addxp", attacker, 50)
                ...
                if event.hit_location == 1 or event.hit_location == 2 then
                    local _, headshot_xp_error, _ = codol.call("method:addxp", attacker, 50)
                    ...
                end
                -- addkill
                local _, kill_error, kill_error_code = codol.call("method:addkill", attacker, 1)
                ...
                -- ★★★ adddeath（第 186–195 行）
                local _, death_error, death_error_code = codol.call(
                    "method:adddeath", player, 1)
```

### ★★★★★ SD 的计分项（与 cha 对比）

| 项 | cha | **sd** |
|---|---|---|
| `addscore` | **100** | ★ **无** |
| `addteamscore` | **1** | ★★★ **绝不能有**（回合数由 C++ 给） |
| `addkill` | 1 | **1** |
| `addxp` | 50 + 爆头 50 | **50 + 爆头 50** |
| `adddeath` | 1 | **1** |

★★★ **⇒ SD **没有 `addscore`**（显示分），也**不能有 `addteamscore`**。**

★ **⇒ 这是**SD 独有的计分结构**。**

### ★★★ `adddeath` 的第二个实例（第 186–190 行，逐字）

```lua
-- ★★ 28100 刀AB（甲方：「把 cha/spy/sd 模式的字段表加回来」）——
--   sd 的 `deaths` 列同理：计分板有位置（FieldDeaths@137）、底层
--   `addClientDeaths` 早已实现，只缺脚本调用 ⇒ 这一列恒 0。
--   这里 `player` 是**死者**（回调第一个参数），所以给它 +1。
--   纯服务端，不碰任何客户端下发。
```

★★ **⇒ 与 `cha.lua` 的 `adddeath`**完全同源**（同一 ticket `28100 刀AB`）。**

★ **⇒ 且明确："`player` 是**死者**（回调第一个参数）"。**

---

## 五、★★★★★ 十个 SD 事件观察器（第 264–329 行）

### 5.1 ★★★ 完整的十个事件名（第 304–315 行）

```lua
local SD_OBSERVED_EVENTS = {
    "sd_bomb_picked_up",
    "sd_bomb_dropped",
    "sd_plant_started",
    "sd_plant_cancelled",
    "sd_bomb_planted",
    "sd_defuse_started",
    "sd_defuse_cancelled",
    "sd_bomb_defused",
    "sd_bomb_exploded",
    "sd_round_ended",
}
```

### ★★★★★ 十个 SD 事件（完整的炸弹流程）

| # | 事件 | 阶段 |
|---|---|---|
| **1** | `sd_bomb_picked_up` | 拾起炸弹 |
| **2** | `sd_bomb_dropped` | 掉落炸弹 |
| **3** | `sd_plant_started` | 开始安放 |
| **4** | `sd_plant_cancelled` | 取消安放 |
| **5** | `sd_bomb_planted` | ★ 安放完成 |
| **6** | `sd_defuse_started` | 开始拆除 |
| **7** | `sd_defuse_cancelled` | 取消拆除 |
| **8** | `sd_bomb_defused` | ★ 拆除完成 |
| **9** | `sd_bomb_exploded` | ★ 爆炸 |
| **10** | `sd_round_ended` | 回合结束 |

★★★ **⇒ 完整的炸弹生命周期（10 个事件）。**

### 5.2 ★★★★★ 明确的"只观察"声明（第 283–290 行，逐字）

```lua
-- WHAT THIS FILE DID NOT HAVE: any sd_* subscription at all. Every event below
-- existed on the wire and none of them was observed, so a 0/0 scoreboard could
-- not be attributed from a log. These handlers only OBSERVE: they emit no score
-- and mutate no state, because method:addteamscore is per KILL and awarding it
-- here would end the match after scoreLimit KILLS instead of after scoreLimit
-- ROUNDS -- the warning at the top of the player_killed handler above.
-- method:addteamscore is the real binding (sv_script_builtin_mp.cpp:4132) and
-- stays deliberately unused in this file.
```

★★★ **⇒ 三条关键信息：**
```
① ★★★ **之前没有任何 sd_* 订阅** ⇒ 0/0 计分板无法从日志归因
② ★★★ **这些处理器只观察**：不发分、不改状态
③ `method:addteamscore` 是真实 binding（`sv_script_builtin_mp.cpp:4132`）
   ★ **但本文件刻意不用**
```

★ **⇒ 第 ① 条是**又一个"写好了但没接线"的实例**（第三个）。**

★★ **⇒ 第 ② 条是**"只观察"的严格纪律**。**

### 5.3 ★★★ 观察器实现（第 296–329 行）

```lua
local function sd_log(kind, event)
    print("sdstate: " .. kind ..
        " seq=" .. tostring(event.sequence) ..
        " t=" .. tostring(event.server_time) ..
        " client=" .. tostring(event.client_num) ..
        " weapon=" .. tostring(event.weapon_name))
end

for _, sd_event_name in ipairs(SD_OBSERVED_EVENTS) do
    assert(codol.on(sd_event_name, function(player, event)
        local ok, failure = pcall(sd_log, sd_event_name, event)
        if not ok then
            print("sdstate callback deferred", sd_event_name, tostring(failure))
        end
    end))
end

print("sdstate observers registered", #SD_OBSERVED_EVENTS)
```

★★★ **⇒ 四个精确字段（第 294–295 行说明）：**
```
sequence      （序列号）
server_time   （服务器时间）
client_num    （客户端号）
weapon_name   （武器名）
```

★★ **⇒ 且注明："Only fields the marshaller is known to always set are printed
（`sv_script_lua_mp.cpp:938-952`）。"**

★ **⇒ 这是**只打印确定存在的字段**的纪律（避免 nil）。**

---

## 六、★★★ `assert(codol.on(...))` 的**双重作用**（第 318–320 行，逐字）

```lua
-- assert() is the only line allowed to raise: it runs once, at load, and it
-- is what proves the engine still resolves every name in this list
-- (sv_script_lua_mp.cpp:490-509).
assert(codol.on(sd_event_name, function(player, event)
```

★★★ **⇒ `assert` 有三个作用：**
```
① 唯一允许抛出的行（只在加载时跑一次）
② ★ 证明引擎仍能解析每个事件名（sv_script_lua_mp.cpp:490-509）
③ 注册回调
```

★★ **⇒ 第 ② 条是**自检机制**：若引擎不再支持某事件名，`codol.on` 返回 nil ⇒ `assert` 失败 ⇒ **加载时就报错**。**

★ **⇒ 这比"运行时静默不触发"好得多。**

---

## 七、★★★ 友好伤害模式的注释（第 331–334 行）

```lua
-- codol_friendly_fire_mode: CODOL/COD team modes use 0=no damage, 1=target,
-- 2=half reflect, 3=half shared. Mode selection remains gametype-owned.
-- TODO(CODOL): source this default from authoritative playlist/game rules.
codol_friendly_fire_mode = 0
```

### ★★★★★ 四种模式的**权威定义**（逐字）

| 值 | 含义 |
|---|---|
| **0** | **no damage**（无伤害） |
| **1** | **target**（打回目标） |
| **2** | **half reflect**（半反射） |
| **3** | **half shared**（半共享） |

★★★ **⇒ 这与 `common.lua` 的实现**完全一致**（报告 004）：**
```
0 ⇒ return（取消）
1 ⇒ damage_target = player
2 ⇒ damage_target = attacker_player, damage × 0.5
3 ⇒ finishsharedplayerdamage, shared_target = attacker, damage × 0.5
```

★ **⇒ 且明确："Mode selection remains **gametype-owned**."**

★★ **⇒ `TODO(CODOL)`：本应从播放列表规则读。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `sd.lua` 行数 | **335** |
| 2 | ★★★★★ **`playfxat` 类型契约** | **index = int64 / 六个分量 = double** |
| 3 | ★★★ 错误信息 | **`playfxat expects six finite transform numbers 3`** |
| 4 | ★ 修法 | **`origin[i] * 1.0`**（强制 float） |
| 5 | ★★★★★ **V1.101-B 证伪** | **all 62/62 live kills 走了 fallback** |
| 6 | ★ 出处 | `回档V1.10-否决B+C-...-20261011-1556.md:13` |
| 7 | ★★★ **SD 队伍分** | **回合数**，由 C++ `advanceSdRound()` 给（`sv_main_mp.cpp:6825-6826`） |
| 8 | ★★★ **绝不能调 `addteamscore`** | 否则变成"scoreLimit 次**击杀**后结束" |
| 9 | ★★ 个人击杀 | 由 `addKillForClient()`（`sv_client_mp.cpp:2253`） |
| 10 | ★★★ SD 计分项 | **addxp 50+50 / addkill 1 / adddeath 1**（**无 addscore / 无 addteamscore**） |
| 11 | ★★★ `adddeath` | 第二个实例（同 ticket `28100 刀AB`） |
| 12 | ★★★★★ **十个 SD 事件** | `picked_up`/`dropped`/`plant_started`/`plant_cancelled`/`bomb_planted`/`defuse_started`/`defuse_cancelled`/`bomb_defused`/`bomb_exploded`/`round_ended` |
| 13 | ★★★ **"之前没有任何 sd_* 订阅"** | 第三个"写好了没接线"实例 |
| 14 | ★★★ **只观察** | **不发分、不改状态** |
| 15 | ★★ `addteamscore` binding | `sv_script_builtin_mp.cpp:4132`，**刻意不用** |
| 16 | ★ 四个安全字段 | `sequence` / `server_time` / `client_num` / `weapon_name` |
| 17 | ★★★ `assert` 三作用 | 唯一可抛 + **自检事件名**（`sv_script_lua_mp.cpp:490-509`）+ 注册 |
| 18 | ★★★ **友好伤害四模式** | **0=no damage / 1=target / 2=half reflect / 3=half shared** |

---

## 九、结论

### 1. ★★★★★ **`playfxat` 的 double 类型契约**是极具体的跨语言坑

```
Lua 5.3+ 区分 integer 与 float
        ↓
C++ 的 std::get_if<double> 只接受 float
        ↓
★★★ 必须 `origin[i] * 1.0`
```

### 2. ★★★★★ **V1.101-B 的 fallback 证伪**（62/62 全走 fallback）

### 3. ★★★★★ **SD 的队伍分是回合数，绝不能调 `addteamscore`**

★ **⇒ 否则变成"scoreLimit 次击杀后结束"。**

### 4. ★★★ **十个 SD 事件观察器**（完整的炸弹生命周期）

★ **⇒ 之前**没有任何 `sd_*` 订阅**（第三个"没接线"实例）。**

### 5. ★★★ **`assert(codol.on(...))` 兼作事件名自检**

### 6. ★★ **友好伤害四模式的权威定义**（0/1/2/3）

---

## 十、下一步

- `zm.lua`（735 行，最大 gametype）
- `dmz.lua`（193 行）
- `dm.lua`（82 行）/ `war.lua`（120 行）/ `conf.lua`（123 行）/ `td.lua`（67 行）
- `configs_s.info`（1,067 行）
- `mp_playlists_shipRetail_release.info`（3,970 行）
- `MarketplaceSkus.json`（22,413 行）
