# 学习报告 004（重开）— `GameScripts\` Lua 层（31 个文件）

**学习范围**：`payload\Ayria\Assets\OlMod\GameScripts\`
**方法**：全文读入 + 注释交叉引用
**性质**：全实测
**★★★ 这是交付包里**信息密度最高**的部分 —— 它自带设计论证与来源引用**

---

## 一、★★★ 全目录结构（含清单哈希）

```
GameScripts\
  common.lua                                2,866   A1761E1B…    ← ★★★ Lua→原生桥
  gametypes\  (11 个)
    cha.lua                                21,493   99EAB1D3…
    conf.lua                                7,082   1DE2A873…    ← ★ 最新加入
    coop.lua                                  863   A83FD6F9…
    dm.lua                                  4,618   E3E113EA…
    dmz.lua                                 9,552   975059A1…
    sd.lua                                 20,121   15705227…
    td.lua                                  3,595   5D4D2734…    ★┐
    war.lua                                 7,018   0C4BB718…     │
    zarena.lua                              3,595   5D4D2734…    ★┤ 三者**哈希相同**
    zhunt.lua                               3,595   5D4D2734…    ★┘
    zm.lua                                 37,359   93A10D97…
  maps\  (19 个)
    coop_training_mp_cargoship.lua        201,269   EFFC8BE4…    ← 最大
    <18 个 *_sh.lua>                        58–67   （各不相同）
```

### ★★★ 发现：`td.lua` / `zarena.lua` / `zhunt.lua` **字节级三胞胎**

**清单第 46/48/49 行的 SHA256 完全相同**：
```
5D4D27342AF613B0D04BE37E386B450D6B96C1733A1EAD0D73BB78AF734BEDF0
```
★ **三者都是 3,595 字节，同一哈希 ⇒ **逐字节相同**。**

★★ **⇒ 三个 gametype 共用一份实现（复制部署）。**

---

## 二、★★★★ `conf.lua` 头部注释 —— **gametype 加载契约的权威描述**

### 2.1 ★★★ 玩法加载路径（引自 `sv_script_source_mp.cpp:144-146`）

> The loader takes the gametype by string —
> **`common.lua` + `gametypes/<gametype>.lua` + `maps/<map>.lua`**

★★★ **⇒ 三个文件组成一次匹配的脚本环境：**
```
common.lua              全局（伤害处理）
gametypes/<gt>.lua      玩法规则
maps/<map>.lua          地图层
```

### 2.2 ★★★ token → gametype 映射表（引自 `CodolPlaylist.cpp:69`）

> **`CodolPlaylist.cpp:69, the authoritative token -> gametype table`**

★★ **⇒ 客户端把播放列表 token 映射到 gametype 名，然后按名加载 Lua。**

| 播放列表 token | gametype（文件名） | 依据 |
|---|---|---|
| `kc` | **`conf`** | `conf.lua:1-3` |
| `ffa` | **`dm`** | `td.lua:1-3` |
| `coop` | `coop` | `coop.lua:1` |

★★★ **⇒ **文件名 ≠ token**。`kc` 加载的是 `conf.lua`，`ffa` 加载的是 `dm.lua`。**

### 2.3 ★★★ gametype 目录清单（写 `conf.lua` 时的状态）

> before this file the directory held
> **`cha/coop/dm/dmz/sd/td/war/zm/zhunt/zarena`**（10 个）

★★ **实测有 **11 个**（多 `conf`）—— 与"conf 是后加的"一致。**

### 2.4 ★★★★ "FAIL-SOFT（硬要求）"（第 40–44 行，逐字）

> **FAIL-SOFT (hard requirement).** A Lua error escaping a world-event callback
> **tears down the gametype thread and ends a real player's match**, so the
> ENTIRE callback body runs inside **`pcall`** and the failure branch **only prints**.
> The registration keeps the family's own shape — **`assert(codol.on(...))`** —
> and is deliberately **the only line allowed to raise**, because it runs once at load.

★★★★ **⇒ 这是全包最重要的一条工程约束：**

```
世界事件回调里逃出一个 Lua 错误  ⇒  拆掉 gametype 线程  ⇒  真实玩家的一局结束
                        ↓
必须把整个回调体包在 pcall 里，失败分支只打印
                        ↓
唯一允许抛出的是 assert(codol.on(...))（只在加载时跑一次）
```

### 2.5 ★★★ 计分归属（引自 `sv_main_mp.cpp`）

> `evaluateMatchLimits()`（**`sv_main_mp.cpp:2950`**）falls through to the team branch
> （**`:2989-2993`**）for **every gametype except `zm` and `dm`**, and only
> **`addClientScore` / `addTeamScoreForClient` / `addKillForClient`** ever call it.
> **Nothing in the engine awards team score on its own — a gametype script has to**,
> which is this file's job.

★★★ **⇒ 引擎的规则**：
```
zm / dm  →  读个人分数
其他     →  读队伍分数
且 引擎自身不加分，必须由 gametype 脚本调 addscore/addteamscore/addkill
```

### 2.6 ★★ 来源引用链（逐条）

```
cha.lua:14-56   团队分支范式（attacker self-kill guard + issameteam + 三连加分）
dm.lua:14-80    同一回调的开场守卫 + method:respawn
war.lua:8-16    "had exactly this disease and was fixed the same way"
war.lua:25-36   数值来源（addscore 100 / addteamscore 1 / addkill 1 / 3000ms）
sv_main_mp.cpp:2950 / :2989-2993 / :5301 / :3587
CodolPlaylist.cpp:69
sv_script_source_mp.cpp:144-146
```

---

## 三、★★★★ `common.lua`（2,866 B）—— **Lua → 原生桥**（逐行）

### 3.1 完整结构

```lua
local function entity_reference(entity_num)
    if entity_num == nil then return nil end
    return codol.entity(entity_num)
end

assert(codol.on("player_damage", function(player, event)
    local inflictor = entity_reference(event.inflictor_entity_num)
    local attacker  = entity_reference(event.attacker_entity_num)
    local damage_target = player
    local damage = event.damage
    local builtin = "method:finishplayerdamage"
    local shared_target = nil

    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        local attacker_player = codol.player(event.attacker_entity_num)
        local same_team, team_error = codol.call(
            "method:issameteam", player, attacker_player)
        if team_error == nil and same_team then
            local mode = codol_friendly_fire_mode
            if mode == 0 then
                return
            elseif mode == 1 then
                damage_target = player
            elseif mode == 2 then
                damage_target = attacker_player
                damage = math.max(1, math.floor(damage * 0.5))
            elseif mode == 3 then
                builtin = "method:finishsharedplayerdamage"
                shared_target = attacker_player
                damage = math.max(1, math.floor(damage * 0.5))
            else
                print("player_damage deferred", "invalid friendly-fire mode", mode)
                return
            end
        end
    end

    local _, error_message, error_code
    if shared_target ~= nil then
        _, error_message, error_code = codol.call(
            builtin, damage_target, shared_target, inflictor, attacker, damage,
            event.damage_flags, event.method_of_death, event.weapon_asset_index,
            event.point, event.direction, event.hit_location,
            event.time_offset, event.bone_index)
    else
        _, error_message, error_code = codol.call(
            builtin, damage_target, inflictor, attacker, damage,
            event.damage_flags, event.method_of_death, event.weapon_asset_index,
            event.point, event.direction, event.hit_location,
            event.time_offset, event.bone_index)
    end
    if error_message ~= nil then
        print("player_damage deferred", error_message, error_code)
    end
end))
```

### 3.2 ★★★ Lua → 原生 API 面（完整）

| API | 签名 | 用途 |
|---|---|---|
| `codol.entity(num)` | `num → entity` | 按实体号取对象 |
| `codol.player(num)` | `num → player` | 按实体号取玩家 |
| `codol.on(event, fn)` | 注册回调，返回可 assert 的值 | ★ 事件订阅 |
| `codol.call(method, ...)` | `→ (ret, err_msg, err_code)` | ★★ 调原生方法 |

### ★★★ 原生方法名（字符串常量）

```
"method:issameteam"               判同队
"method:finishplayerdamage"       结算伤害（标准）
"method:finishsharedplayerdamage" 结算伤害（分担/共享）
"method:addscore"                 加显示分（td.lua）
"method:addxp"                    加经验（td.lua）
"method:addkill"                  加击杀数（td.lua）
"method:respawn"                  重生（td.lua，带 3000ms）
```

### 3.3 ★★★ 事件字段（完整）

```
event.inflictor_entity_num     伤害施加者实体号
event.attacker_entity_num      攻击者实体号
event.target_client_num        目标客户端号
event.damage                   伤害值
event.damage_flags             伤害标志
event.method_of_death          死亡方式
event.weapon_asset_index       武器资产索引
event.point                    命中点
event.direction                方向
event.hit_location             命中部位（★ 1/2 = 爆头）
event.time_offset              时间偏移
event.bone_index               骨骼索引
```

### 3.4 ★★★★ `codol_friendly_fire_mode` 的 4 种模式（逐行）

```lua
if mode == 0 then
    return                              -- ★ 完全取消伤害
elseif mode == 1 then
    damage_target = player              -- ★ 打回受害者自己（未减半）
elseif mode == 2 then
    damage_target = attacker_player     -- ★ 反弹给攻击者，伤害 ×0.5
    damage = math.max(1, math.floor(damage * 0.5))
elseif mode == 3 then
    builtin = "method:finishsharedplayerdamage"   -- ★ 共享伤害
    shared_target = attacker_player
    damage = math.max(1, math.floor(damage * 0.5))
else
    print("player_damage deferred", "invalid friendly-fire mode", mode)
    return                              -- ★ 非法值 ⇒ 取消
end
```

★★★ **⇒ 四种队友伤害策略：**
```
0 = 关闭（默认，coop 与 td 都设 0）
1 = 打回受害者
2 = 反弹攻击者（半伤）
3 = 共享伤害（半伤）
非法 = 取消 + 打日志（fail-soft）
```

★★ **`math.max(1, math.floor(damage * 0.5))`** —— **至少 1 点伤害**（不为 0）。

### 3.5 ★★★ 未完成标记（`TODO(CODOL)`，两处）

```lua
-- TODO(CODOL): apply native no-protection and producer-specific
-- exemptions once those damage flags and event classes are restored.
```
```lua
-- TODO(CODOL): last stand and producer-specific protection branches
-- remain fail-closed until their native state owners are restored.
```

★★★ **⇒ **"fail-closed"** —— 缺失的分支**拒绝**伤害，而不是放行。**
**⇒ 这是有意的安全选择（宁可不生效，不要错生效）。**

★ **⇒ `common.lua` 的伤害管线**不完整**，且**已知不完整**。**

---

## 四、★★★ `td.lua`（3,595 B）—— FFA/dm 完整实现

### 4.1 ★★★ 文件名与 token 的错位（第 1–3 行）

> Free-for-all. The client books this as the playlist token **`ffa`**; the engine
> gametype — and so this file's name — is **`dm`**, which is the stock **IW** name.

★★★ **⇒ 文件名叫 `td.lua`，内容却是 `dm`（FFA）。**
★ **`print("gametype has no map gameobjects", "dm")` —— 日志里报的是 `dm`。**

★★ **⇒ 这是**分发时的命名错误或有意映射**。**
**与 `conf.lua` 说 `kc`→`conf` 是同类的 token/gametype 错位。**

### 4.2 ★★★ 计分细节（第 18–26 行，逐字）

> Two counters, in **two different units**, exactly as cha keeps them.
> **`addscore` is the DISPLAY score at 50 a kill**; **`addkill` is the one the
> score limit reads, at 1 a kill**, and is free-for-all's stand-in for cha's `addteamscore`.
> The shipped limit is 30, so **awarding only the display score would end the match
> on the first kill**.
> **50 is MEASURED, not cha's 100**: the retail dm server sets
> `ui_DMKillScore "50"` at serverTime 0 and its score popup carries 50.

★★★ **⇒ 两个计数器，两套单位：**
```
addscore   显示分，每次击杀 +50    （UI 显示）
addkill    限分读的数，每次 +1     （决定比赛结束）
限制       30
```

★★★ **⇒ 如果只加 `addscore`（50），一杀就到 50 > 30 ⇒ 比赛立刻结束。**
**⇒ 必须**两个都加**。**

### 4.3 ★★ XP 归属的完整论证（第 30–39 行）

> V1.11 / (2) match info — XP + gp MODE COVERAGE, ticket 20261011-22000.
> Before this block **only `dm.lua` awarded XP**, so the AAR's xp row and the gp row
> that mirrors it 1:1 (**`sv_main_mp.cpp:3587`**) were empty in every other mode:
> the DM-only match-end bonus (**`sv_main_mp.cpp:5301`**) never runs here, and no
> other native producer exists (**`git grep addClientXp` = this path + that bonus**).
> **50 IS MEASURED, NOT INVENTED**: `dm.lua:30-34` records IW4 `_rank.gsc`'s
> **50 XP for a kill plus 50 more for a headshot**, and the retail dm trace confirms
> an ordinary kill moves the AAR row XP 50 farther.
> Applying the global rank rule to this mode is **RECONSTRUCTION POLICY**:
> no per-mode XP measurement exists for it.

★★★ **⇒ XP 规则来源链：**
```
IW4 的 _rank.gsc          击杀 50 XP + 爆头再 50 XP
零售 dm 实测              普通击杀让 AAR 的 XP 行前进 50
⇒ dm.lua 采用 50 / 50
⇒ 其他模式套用（"RECONSTRUCTION POLICY"，无本模式实测）
```

### 4.4 ★★ 爆头判定（第 45 行）

```lua
if event.hit_location == 1 or event.hit_location == 2 then
    codol.call("method:addxp", attacker, 50)   -- 爆头额外 50 XP
end
```

★★ **`hit_location` 的 `1` 或 `2` = 爆头。**

### 4.5 ★★ 重生（第 60–61 行）

```lua
local _, respawn_error, respawn_error_code = codol.call(
    "method:respawn", player, 3000)
```

★ **3000 ms 重生延迟。**

### 4.6 ★★ 结尾（第 67 行）

```lua
codol_friendly_fire_mode = 0
```

★ **FFA 也设 0**（虽然 FFA 没有队友，但保持一致）。

---

## 五、★ `coop.lua`（863 B）—— 战役模式

```lua
-- CODOL story missions use the engine gametype token "coop". Mission progress,
-- actors, objectives, checkpoints, and presentation belong to the map layer;
-- the gametype layer only establishes rules shared by every story mission.

print("campaign gametype initialized", "coop")

-- Story allies must not damage one another. The Wetwork map carries allied
-- Price, Nikolai, and hazmat actor spawners and places the player on their side.
-- Enemy damage remains authoritative because issameteam is false across sides.
codol_friendly_fire_mode = 0

-- There is deliberately no PvP score, kill, or timed-respawn handler here.
-- The former file was a stale copy of dm.lua and awarded FFA points before
-- respawning the player after every death. Wetwork death and checkpoint restart
-- are mission state transitions and will be owned by the cargoship map layer.
```

★★★ **⇒ 最简 gametype（863 字节）：只设 `friendly_fire_mode = 0`，无计分。**

★ **地图名 `Wetwork`**，盟友 Price / Nikolai / hazmat。
★★★ **⇒ 这是 CoD 战役关卡（"Wetwork" 是 MW 系列经典关卡）。**
**对应 `coop_training_mp_cargoship.lua`（201 KB，最大的 map 脚本）。**

★ **注释记载了一次**修复**：**
> The former file was a **stale copy of dm.lua** and awarded FFA points before
> respawning the player after every death.

★★ **⇒ 曾经 `coop.lua` 是 `dm.lua` 的陈旧副本，导致战役里每死一次加 FFA 分。**

---

## 六、★★ 19 个 `maps\*.lua`（除 cargoship）

### 18 个小文件（58–67 字节）—— **全是同一形态**

```lua
return {
    minimap_material = "compass_map_<地图名>",
}
```

**实测两例**：

| 文件 | 字节 | 内容 |
|---|---|---|
| `mp_nuked.lua` | 58 | `return { minimap_material = "compass_map_mp_nuked", }` |
| `mp_foundation_sh.lua` | 66 | `return { minimap_material = "compass_map_mp_foundation_sh", }` |

★★ **⇒ 这些是**小地图材质声明**，不是玩法逻辑。**

★ **地图清单（18 个）**：
```
mp_arkaden_sh   mp_backlot_sh    mp_crash_tropical  mp_derail_sh
mp_fallen_sh    mp_foundation_sh mp_interchange_sh  mp_lockdown_sh
mp_lookout_sh   mp_mission_sh    mp_nuked           mp_offshore
mp_overwatch_sh mp_showdown      mp_tunisia         mp_underground_sh
mp_wasteland_sh zm_factory_sh
```

### ★ `coop_training_mp_cargoship.lua`（201,269 B）

★★ **唯一的大 map 脚本** —— 对应 `coop.lua` 注释里的 **"the cargoship map layer"**。

★ **⇒ 战役（Wetwork/cargoship）的关卡逻辑在这里。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | gametype 数 | **11** |
| 2 | map 数 | **19** |
| 3 | ★★★ 同哈希三胞胎 | `td.lua` = `zarena.lua` = `zhunt.lua`（`5D4D2734…`） |
| 4 | 加载路径 | `common.lua` + `gametypes/<gt>.lua` + `maps/<map>.lua` |
| 5 | token→gt 表出处 | `CodolPlaylist.cpp:69` |
| 6 | ★ token 错位 | `kc`→`conf`，`ffa`→`dm` |
| 7 | ★★★ fail-soft 要求 | 回调体必须 `pcall`，失败只打印 |
| 8 | ★ 唯一允许抛出 | `assert(codol.on(...))` |
| 9 | Lua→原生 API | `codol.entity` / `codol.player` / `codol.on` / `codol.call` |
| 10 | 原生方法 | `issameteam` / `finishplayerdamage` / `finishsharedplayerdamage` / `addscore` / `addxp` / `addkill` / `respawn` |
| 11 | 友伤模式 | 0/1/2/3（+ 非法=取消） |
| 12 | dm 计分单位 | `addscore`=50（显示）/ `addkill`=1（限分） |
| 13 | dm 限分 | 30 |
| 14 | 爆头 | `hit_location ∈ {1,2}`，额外 +50 XP |
| 15 | 重生延迟 | 3000 ms |
| 16 | 未完成标记 | `common.lua` 两处 `TODO(CODOL)`，**fail-closed** |
| 17 | 引擎规则 | 引擎自身不加分，须脚本调 |
| 18 | 限分读法 | `zm`/`dm` 读个人；其余读队伍 |

---

## 八、结论

### 1. ★★★★ 这套 Lua 是**有据可查的重建**，不是随手写的

★★★ **每条数值都标注来源**（`sv_main_mp.cpp:2950`、`CodolPlaylist.cpp:69`、
`dm.lua:30-34`、`IW4 _rank.gsc`、零售实测）。
**且明确标出哪些是 `RECONSTRUCTION POLICY`（无实测、套用他模式）。**

### 2. ★★★★ **fail-soft 是硬要求**（最重要的工程约束）

```
回调里逃出 Lua 错误  ⇒  拆 gametype 线程  ⇒  玩家一局结束
```

★★★ **⇒ 任何自研 Lua 都必须遵守。**

### 3. ★★★ `common.lua` 的伤害管线**已知不完整**（fail-closed）

★ **这与记忆里"`bind_world` 从未绑定 ⇒ 伤害整条是死的"**方向一致但层次不同**：**
```
记忆：原生侧（C）world 未绑定 ⇒ 伤害不生效
本报告：Lua 侧有两处 TODO ⇒ 部分分支 fail-closed
```

### 4. ★★★ token ≠ 文件名（`kc`→`conf`，`ffa`→`dm`）

### 5. ★★ 三个 gametype 哈希相同（复制部署）

### 6. ★★ 19 个 map 脚本里 18 个只是小地图材质声明（58–67 字节）

---

## 九、下一步

`payload\Ayria\` 还剩：
- `Assets\Alwaysoffline\1004\MarketplaceSkus.json`（2,578,582 B）
- `ol-mod-runtime-manifest.json`（28,209 B）
- `Plugins\` 4 个插件（前一轮已做 PE，本轮可复用）
- `Injector32.exe` / `Bootstrapper32.dll` / `Bootstrapper64.dll` / `ol_room_owner.exe`
