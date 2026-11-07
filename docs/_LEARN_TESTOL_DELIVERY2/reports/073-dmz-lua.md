# 学习报告 073（重开）— `dmz.lua` 全文（194 行）：BattleCity 与 loot 陷阱

**学习范围**：`dmz.lua` 第 1–194 行（文件全文）
**性质**：全实测（**`dmz.lua` 全文完成**）
**★★★ 本报告收录**全包最著名的数据陷阱**（cs 12506..12692 是零售回放）与**XP 全覆盖的完整论证**

---

## 一、★★★★★ 模式身份与"被剥离"的真相（第 1–27 行，逐字）

```lua
-- BattleCity. The client books this as "dmz"; the mode is Brave Games / battle
-- royale, and Activision stripped its logic when the game shut down. This file
-- was a byte-for-byte copy of dm.lua until now, which is why the mode played as
-- deathmatch.
--
-- WHAT IS ACTUALLY MISSING IS SMALLER THAN IT LOOKS. The ASSETS survived the
-- strip -- mp_battlecity's model band publishes the whole pickup set, the
-- parachute, the care-package pod and the play-area cylinder (dumped with
-- OLMOD_DUMP_MODEL_BAND=1, 283 entries). Only the script that places them is
-- gone. This is step one of putting it back: loot you can walk up to and see.
```

### ★★★★★ 三层身份

| 层 | 值 |
|---|---|
| **客户端登记名** | **`dmz`** |
| **模式英文名** | **BattleCity** |
| **玩法** | **Brave Games / battle royale** |

★★★ **⇒ 且明确："This file was a **byte-for-byte copy of `dm.lua`** until now,
which is why the mode played as **deathmatch**."**

★ **⇒ 即：`dmz` 曾经**逐字节等于 `dm.lua`** ⇒ 玩起来是死斗。**

### ★★★ "缺的东西比看上去少"（逐字）

```
"The **ASSETS survived** the strip --
 mp_battlecity's model band publishes:
   ① 整个 pickup 集
   ② 降落伞（parachute）
   ③ 空投舱（care-package pod）
   ④ 游戏区圆柱（play-area cylinder）
 ★ 导出于 `OLMOD_DUMP_MODEL_BAND=1`，**283 条**
 -- **Only the script that places them is gone.**"
        ↓
★★★ ⇒ 资产全在，**只有放置它们的脚本被删了**
```

★ **⇒ 精确的导出方法与条目数：`OLMOD_DUMP_MODEL_BAND=1` ⇒ **283 条**。**

---

## 二、★★★★★ 拾取是**按键使用，不是走过即拾**（第 12–20 行，逐字）

```lua
-- PICKUP IS PRESS-USE, NOT WALK-OVER, and that is what retail does. The dmz
-- demo shows `cursorHint` going 0 -> 1 with `cursorHintEntIndex` naming the crate
-- while the player stands at it, and the weapon arriving only afterwards -- so
-- the player asks and the server answers. Walking over loot in a battle royale
-- and having it grabbed for you would be wrong anyway.
--
-- The bridge still refuses entity_touch, so none of this is done here: setloot
-- registers what is in a crate, and the server does the range test, the prompt
-- and the grant. See ServerCore::driveCursorHints / processLootCommittedCommand.
```

### ★★★★★ 完整的按键使用链

```
玩家站在箱子旁
        ↓
dmz demo 显示：`cursorHint` **0 → 1**
  且 **`cursorHintEntIndex`** 指向那个箱子
        ↓
★ 武器**之后才到达**
        ↓
★★★ "so the **player asks and the server answers**"
```

### ★★★ 三个精确的引擎符号

| # | 符号 | 说明 |
|---|---|---|
| **1** | **`cursorHint`** | 从 0 变 1（提示出现） |
| **2** | **`cursorHintEntIndex`** | 指向箱子实体 |
| **3** | **`ServerCore::driveCursorHints`** | C++ 侧驱动提示 |
| **4** | **`ServerCore::processLootCommittedCommand`** | C++ 侧处理拾取 |

★★★ **⇒ 分工明确（逐字）：**
```
Lua 侧：`setloot` **只注册箱子里有什么**
C++ 侧：**范围测试 + 提示 + 授予**
        ↓
★ 原因：**"The bridge still refuses `entity_touch`"**
   （Lua 桥接层**拒绝** `entity_touch` 事件）
```

★ **⇒ 所以 Lua **不能**自己实现"走过即拾"。**

### ★★★ 两条明确的"未实现"（第 22–27 行，逐字）

```lua
-- WHAT THIS DOES NOT DO YET, so nobody reads more into it than is here:
--   * the circle is not drawn. fx_dmz_cylinder and fx_dmz_intersect_ring are in
--     the band, so the geometry is a model rather than custom rendering, but
--     nothing shrinks or damages yet.
--   * a picked-up gun replaces the last one rather than filling a second slot,
--     because the server holds exactly one grant per player.
```

| # | 未实现 | 精确细节 |
|---|---|---|
| **1** | ★ **圆圈不绘制** | `fx_dmz_cylinder` / `fx_dmz_intersect_ring` **在 band 里**（几何是模型，不是自定义渲染），但**不收缩、不伤害** |
| **2** | ★★ **捡枪替换上一把** | 不填第二个槽位，因为**服务器每个玩家只持有恰好一个 grant** |

★★ **⇒ 第 2 条揭示了服务器的**硬约束**：**每玩家仅一个 grant**。**

---

## 三、★★★★★ 九个 loot 模型（第 31–48 行）

```lua
local LOOT_MODELS = {
    "bc_pickups_mountains_ammo_pistol_sh",
    "bc_pickups_mountains_ammo_shotgun_sh",
    "bc_pickups_mountains_ammo_sniperrifle_sh",
    "bc_pickups_mountains_ammo_weapon_sh",
    "bc_pickups_mountains_attachment_sh",
    "bc_pickups_mountains_perk_sh",
    "bc_pickups_mountains_recover_sh",
    "dmz_pickups_armor",
    "orbital_carepackage_pod_01_sh",
}
```

### ★★★★★ 九个模型的完整命名规律

| # | 模型 | 类别 |
|---|---|---|
| **1** | `bc_pickups_mountains_ammo_pistol_sh` | 手枪弹药 |
| **2** | `bc_pickups_mountains_ammo_shotgun_sh` | 霰弹枪弹药 |
| **3** | `bc_pickups_mountains_ammo_sniperrifle_sh` | 狙击枪弹药 |
| **4** | `bc_pickups_mountains_ammo_weapon_sh` | 通用武器弹药 |
| **5** | `bc_pickups_mountains_attachment_sh` | 配件 |
| **6** | `bc_pickups_mountains_perk_sh` | 特长 |
| **7** | `bc_pickups_mountains_recover_sh` | 恢复 |
| **8** | `dmz_pickups_armor` | ★ 护甲（**`dmz_` 前缀**） |
| **9** | `orbital_carepackage_pod_01_sh` | ★ 空投舱（**完全不同的前缀**） |

★★★ **⇒ 命名规律：7 个 `bc_pickups_mountains_*_sh` + 1 个 `dmz_pickups_armor` + 1 个 `orbital_*`。**

★★ **⇒ 且明确警告（逐字）：**
```
"Every name here was read out of the **live model configstring band**;
 `spawnmodel` **refuses anything the map does not publish**,
 so this list is **not a guess and must not be extended by guessing**."
        ↓
★★★ ⇒ 不能靠猜扩展这个列表（`spawnmodel` 会拒绝未发布的模型）
```

★ **⇒ 这是**从活模型 band 读出**的实证列表。**

### ★★ `LOOT_RADIUS = 150`（第 46–48 行，逐字）

```lua
-- Far enough not to stand inside a crate, close enough to be on screen the
-- instant the map loads. This is a bring-up value, not a design one.
local LOOT_RADIUS = 150
```

★★ **⇒ 理由："far enough not to stand inside a crate, close enough to be on screen
the instant the map loads"，且明确 **"This is a **bring-up value, not a design one**"。**

---

## 四、★★★★★ **全包最重要的数据陷阱**（第 50–69 行，逐字）

```lua
-- WHAT IS IN EACH CRATE, one per model above and in the same order.
--
-- COUNTING UP FROM firstDynamicWeapon, WHICH IS 1147 ON THIS MAP. The server
-- registers its modular weapons contiguously from there -- see
-- SV_RegisterModularWeaponConfigString -- so the real ones are 1147, 1148, 1149
-- and so on for as many as the classes produced, and there is no way to know
-- from here how many that is.
--
-- THE LOOT BAND IS NOT THAT LIST, which is the trap this walked into. cs
-- 12506..12692 advertises 1148..1211 because it is a verbatim replay of a RETAIL
-- capture, and retail had 1211 weapons registered where this server has eight.
-- Six of the nine crates below were handing out real guns and three were naming
-- nothing at all.
--
-- setloot NOW REFUSES A WEAPON THAT DOES NOT RESOLVE, so an index past the end
-- prints "loot contents failed" against the crate that asked for it. That is the
-- measurement: whatever the last successful line says is how many this server has.
local LOOT_WEAPONS = {
    1147, 1148, 1149, 1150, 1151, 1152, 1153, 1154, 1155,
}
```

### ★★★★★ 完整的陷阱结构

```
真实情况：
  `firstDynamicWeapon` = **1147**（本图上）
  服务器**从那里连续注册**模块化武器
  （见 `SV_RegisterModularWeaponConfigString`）
  真实的是 **1147, 1148, 1149, ...**
  ★ 但**从这里无法知道有多少个**
        ↓
陷阱：
  ★★★ **cs 12506..12692 广播 1148..1211**
  原因：**它是零售捕获的逐字回放**（verbatim replay of a RETAIL capture）
  零售有 **1211** 个武器注册
  而**本服务器只有八个**
        ↓
后果（实测）：
  ★★★ **九个箱子里六个在发真枪，三个什么都没发**
```

### ★★★★★ 四个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | **`firstDynamicWeapon`** | **1147** |
| **2** | **广播用的 cs 范围** | **12506..12692** |
| **3** | **该 cs 广播的武器号** | **1148..1211** |
| **4** | **零售注册的武器数** | **1211** |
| **5** | **本服务器实际有的** | **八个** |

★★★ **⇒ 第 2、3 条揭示了**cs 12506..12692 是"零售回放"**：**
```
cs 12506..12692 里有 1148..1211 的映射
        ↓
★ 但这不是本服务器的注册结果
★★★ 而是**从零售捕获里逐字抄来的字符串表**
        ↓
⇒ 即使服务器只有 8 个武器，这段 cs 仍"声称"有 1211 个
```

★ **⇒ 这是**"数据在但语义假"的典型案例**。**

### ★★★ 修复与测量方法（逐字）

```
"`setloot` NOW **REFUSES A WEAPON THAT DOES NOT RESOLVE**,
 so an index past the end prints **"loot contents failed"** against the crate
 that asked for it. **That is the measurement**: whatever the last successful
 line says is how many this server has."
        ↓
★★★ ⇒ **用"哪一行失败"来测量服务器实际有多少个武器**
```

★ **⇒ 这是一个**绝妙的测量设计**（用失败点当标尺）。**

★★ **⇒ 与 `LOOT_WEAPONS` 表（1147..1155，9 个）呼应：**
```
若服务器真只有 8 个（1147..1154）
⇒ 第 9 个箱子（1155）会打印 "loot contents failed"
```

---

## 五、★★★★ `LOOT_PICKUP_RADIUS = 72`（第 71–74 行，逐字）

```lua
-- HOW CLOSE COUNTS. The ring puts crates about 105 units apart, so this is
-- comfortably inside "the one I am standing at" without two of them ever being
-- the nearest at once. The server picks the closest anyway if they do overlap.
local LOOT_PICKUP_RADIUS = 72
```

### ★★★ 一个精确的几何论证

```
环上箱子间距 ≈ **105 units**
        ↓
拾取半径 = **72** < 105/2 = **52.5**?  —— ★ 不，72 > 52.5
        ↓
★ 但作者说"comfortably inside 'the one I am standing at'
  without two of them ever being the nearest at once"
        ↓
★★ 理由：**"the nearest"** 的唯一性由**最近距离**决定
  不是由半径决定（半径只决定"是否触发"）
        ↓
★ 且补充："The server picks the closest anyway if they do overlap."
```

★★ **⇒ 注意：72 > 52.5 ⇒ 两个箱子**可能同时在半径内**，但服务器**取最近的**。**

★ **⇒ 所以 72 是**宽松但由"取最近"兜底**的选择。**

---

## 六、★★★★★ **只生成一次**的理由（第 76–81 行，逐字）

```lua
-- SPAWN THE LOOT EXACTLY ONCE. client_spawned fires on every respawn, and the
-- entity pool is finite -- dynamic numbers start at 37 -- so a ring per death
-- would exhaust it and then fail silently, which is the hard kind of bug to
-- read in a log.
local loot_placed = false
local loot = {}
```

### ★★★ 三个精确事实

| # | 项 | 值 |
|---|---|---|
| **1** | `client_spawned` 触发时机 | ★ **每次重生** |
| **2** | 实体池 | **有限** |
| **3** | ★★ **动态实体号起点** | **37** |

★★★ **⇒ 因果链：**
```
`client_spawned` 每次重生都触发
        ↓
★ 若每次死亡都放一圈（9 个箱子）
        ↓
★★★ 实体池耗尽 ⇒ **然后静默失败**
        ↓
★ "which is the hard kind of bug to read in a log"
```

★★ **⇒ 第 3 条 `dynamic numbers start at 37` 是**精确的引擎常量**。**

★ **⇒ 与报告 071 的 `IMPLEMENTATION_ALIVE_CAP = 4` 呼应：**实体池限额是全局瓶颈**。**

### ★★★ `ipairs` 的 1-based 陷阱（第 92–99 行，逐字）

```lua
-- ipairs is 1-based, so subtract one before dividing the circle or the
-- first and last crate land on top of each other.
local angle = (index - 1) * (2 * math.pi / #LOOT_MODELS)
local x = origin[1] + LOOT_RADIUS * math.cos(angle)
local y = origin[2] + LOOT_RADIUS * math.sin(angle)
-- Same z as the player: these are ground pickups and the player is
-- standing on the ground. There is no ground trace exposed to script,
-- so a crate on a slope will float or sink until one is.
local entity, spawn_error, spawn_error_code = codol.call(
    "function:spawnmodel", model, x, y, origin[3])
```

★★★ **⇒ 三个要点：**
```
① ★ `(index - 1)` 必须减一，否则首尾箱子重叠
② ★ z 用玩家自己的 z
③ ★★★ **"There is no ground trace exposed to script"**
   ⇒ 斜坡上的箱子会**浮空或下沉**，直到暴露一个
```

★ **⇒ 第 ③ 条是一个**明确的引擎能力缺口**声明。**

---

## 七、★★★★★ `nil` 的两种含义（第 102–109 行，逐字）

```lua
if entity == nil then
    -- nil with no error is the pool refusing, which is expected once
    -- the dynamic region fills. nil WITH an error is a real fault.
    if spawn_error ~= nil then
        print("loot spawn failed", model, spawn_error, spawn_error_code)
    else
        print("loot spawn refused, entity pool is full", model)
    end
```

### ★★★★★ 一个精确的"三值"约定

| `entity` | `spawn_error` | 含义 |
|---|---|---|
| `nil` | **`nil`** | ★ **实体池拒绝**（预期行为，池满） |
| `nil` | **非 nil** | ★★ **真实故障** |
| 非 nil | — | 成功 |

★★★ **⇒ 这与报告（`codol.call` 契约）**完全一致**：**
```
`codol.call` 返回 `(ret, err, code)`
        ↓
★★★ **必须同时检查 ret 和 err**（不能只 `pcall`）
```

★ **⇒ 这是**该契约在业务层的正确应用范例**。**

### ★★★ `setloot` 的调用（第 113–123 行）

```lua
-- AND WHAT IS IN IT. Without this the crate is scenery: the server
-- has no reason to offer it and no answer if the player presses use.
local weapon = LOOT_WEAPONS[index]
local set, set_error, set_error_code = codol.call(
    "method:setloot", entity, weapon, LOOT_PICKUP_RADIUS)
if set == nil then
    print("loot contents failed", model, weapon,
        set_error, set_error_code)
else
    print("loot contents", model, weapon, LOOT_PICKUP_RADIUS)
end
```

★★ **⇒ `setloot(entity, weapon, pickup_radius)` —— **三个参数**。**

★ **⇒ 理由（逐字）："Without this the crate is **scenery**: the server has no reason
to offer it and **no answer if the player presses use**."**

---

## 八、★★★★★ **XP 全覆盖的完整论证**（第 147–184 行，逐字）

```lua
-- V1.11 / (2) match info -- XP + gp MODE COVERAGE, ticket 20261011-22000.
-- Before this block only dm.lua awarded XP, so the AAR's xp row and the gp row
-- that mirrors it 1:1 (sv_main_mp.cpp:3587) were empty in every other mode:
-- the DM-only match-end bonus (sv_main_mp.cpp:5301) never runs here, and no
-- other native producer exists (git grep addClientXp = this path + that bonus).
-- 50 IS MEASURED, NOT INVENTED: dm.lua:30-34 records IW4 _rank.gsc's 50 XP for
-- a kill plus 50 more for a headshot, and the retail dm trace confirms an
-- ordinary kill moves the AAR row XP 50 farther. The headshot half uses the
-- same hit_location test dm.lua:40 uses. Applying the global rank rule to this
-- mode is RECONSTRUCTION POLICY: no per-mode XP measurement exists for it.
```

### ★★★★★ 完整的 XP 论证

```
① 问题：**之前只有 `dm.lua` 给 XP**
        ↓
② 后果：**AAR 的 xp 行 和 与之 1:1 镜像的 gp 行**
        （`sv_main_mp.cpp:3587`）
        **在其他所有模式里都是空的**
        ↓
③ 原因：
   · DM 专属的比赛结束奖励（`sv_main_mp.cpp:5301`）**在这里不跑**
   · 且**没有其他原生生产者**
     （`git grep addClientXp` = 这条路径 + 那个奖励）
        ↓
④ ★★★ **50 是测出来的，不是发明的**：
   `dm.lua:30-34` 记录 IW4 `_rank.gsc` 的**击杀 50 XP**
   **+ 爆头再加 50**
   零售 dm trace 确认一次普通击杀**让 AAR 行 XP 前进 50**
        ↓
⑤ 爆头半段用**与 `dm.lua:40` 相同的 `hit_location` 测试**
        ↓
⑥ ★★★ 把全局军衔规则应用到本模式是 **RECONSTRUCTION POLICY**
   （"no per-mode XP measurement exists for it"）
```

### ★★★★★ 五个精确的代码位置引用

| # | 引用 | 内容 |
|---|---|---|
| **1** | **`sv_main_mp.cpp:3587`** | gp 行与 xp 行 **1:1 镜像** |
| **2** | **`sv_main_mp.cpp:5301`** | **DM 专属**的比赛结束奖励 |
| **3** | **`dm.lua:30-34`** | IW4 `_rank.gsc` 的 50 XP 记录 |
| **4** | **`dm.lua:40`** | `hit_location` 测试 |
| **5** | `git grep addClientXp` | 只有**两个**生产者 |

★★★ **⇒ 第 5 条是**穷尽性证明**（用 `git grep` 证明没有别的生产者）。**

★ **⇒ ticket 号：**`20261011-22000`**；版本标记 **V1.11 / (2) match info**。**

### ★★★ 实际实现（第 150–183 行）

```lua
local attacker = codol.player(event.attacker_entity_num)
local _, score_error, score_error_code = codol.call("method:addscore", attacker, 50)
...
local _, xp_error, xp_error_code = codol.call("method:addxp", attacker, 50)
...
if event.hit_location == 1 or event.hit_location == 2 then
    local _, headshot_xp_error, ... = codol.call("method:addxp", attacker, 50)
end
...
local _, kill_error, kill_error_code = codol.call("method:addkill", attacker, 1)
```

★★★ **⇒ 完整的击杀奖励：**
```
addscore(attacker, 50)                          ← 分数
addxp(attacker, 50)                             ← XP
若 hit_location == 1 或 2 ⇒ addxp(attacker, 50) ← 爆头再 50
addkill(attacker, 1)                            ← 击杀数
```

★★ **⇒ 四个 API：`addscore` / `addxp` / `addkill` / `codol.player`。**

★ **⇒ 爆头用 **`hit_location == 1 or == 2`**（两个值都算爆头）。**

★★ **⇒ 与报告 069 的 `zm.lua` 对比：**
```
`zm.lua`   ⇒ **DELIBERATELY NO SCORING**（合作模式，玩家互杀是 bug）
`dmz.lua`  ⇒ 完整计分（★ 且明确说"仍是死斗的，故意保留"）
```

---

## 九、★★★★ 故意保留死斗行为（第 144–147 行，逐字）

```lua
-- Scoring and respawn are still deathmatch's, deliberately. Replacing them is a
-- separate job from proving loot reaches the world, and a battle royale with no
-- respawn and no loot to fight over is not testable.
```

★★ **⇒ 理由："a battle royale with **no respawn and no loot to fight over** is
not testable."**

★ **⇒ 这是**"先让它可测"的工程判断**（与 `zm.lua` 的 bring-up 占位同类）。**

### ★★ 被删除的临时授予（第 129–135 行，逐字）

```lua
-- THE TIMED TEST GRANT IS GONE. It existed because nothing could be picked up,
-- so a gun had to appear on its own to prove the grant survived the pmove. It
-- does, and now a crate can hand one over, so a rifle materialising five seconds
-- into every life would only get in the way of testing the real path.
--
-- `method:giveweapon` is still there and still takes either a name or a raw
-- modular index; the pickup path calls the same world function underneath.
```

★★★ **⇒ 一个**已被证明后就删除的测试手段**：**
```
"nothing could be picked up" ⇒ 每命 5 秒后自动给一把步枪
        ↓
★ 用来证明 **grant 能在 pmove 之后存活**
        ↓
★★★ 结论：**"It does."**（确实能）
        ↓
⇒ 现在箱子能给了 ⇒ **删除**（否则妨碍测试真实路径）
```

★ **⇒ 且保留 `method:giveweapon`（接受**名字或原始模块化索引**）。**

---

## 十、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 三层身份 | 登记名 **`dmz`** / **BattleCity** / **Brave Games 大逃杀** |
| 2 | ★★★ 被剥离真相 | **资产全在，只有放置脚本被删** |
| 3 | ★★ 资产导出 | `OLMOD_DUMP_MODEL_BAND=1` ⇒ **283 条** |
| 4 | ★ 旧状态 | `dmz.lua` **曾逐字节等于 `dm.lua`** |
| 5 | ★★★★★ **拾取方式** | **按键使用（press-use）**，不是走过即拾 |
| 6 | ★★ 证据 | `cursorHint` **0→1** + **`cursorHintEntIndex`** 指向箱子 |
| 7 | ★★★ 引擎符号 | **`ServerCore::driveCursorHints`** / **`processLootCommittedCommand`** |
| 8 | ★★ 桥接限制 | **Lua 拒绝 `entity_touch`** ⇒ 范围测试/提示/授予全在 C++ |
| 9 | ★★★ 两条未实现 | ① 圆圈不绘制 ② 捡枪**替换**上一把（每玩家仅一个 grant） |
| 10 | ★ 九个 loot 模型 | **7× `bc_pickups_mountains_*_sh`** + `dmz_pickups_armor` + `orbital_carepackage_pod_01_sh` |
| 11 | ★★ 警告 | `spawnmodel` **拒绝未发布模型** ⇒ 不可靠猜扩展 |
| 12 | ★ `LOOT_RADIUS` | **150**（bring-up 值） |
| 13 | ★★★★★ **`firstDynamicWeapon`** | **1147**（本图） |
| 14 | ★★★★★ **陷阱** | **cs 12506..12692 广播 1148..1211** ⇒ **零售回放** |
| 15 | ★★★ 零售武器数 | **1211**；本服务器 **8 个** |
| 16 | ★★★ 实测后果 | 九个箱子**六个发真枪、三个什么都没发** |
| 17 | ★★ 修复与测量 | `setloot` **拒绝无法解析的武器** ⇒ 用失败行测量实际数量 |
| 18 | ★ `LOOT_PICKUP_RADIUS` | **72**（箱子间距 **105**） |
| 19 | ★★★ 只生成一次 | `client_spawned` **每次重生都触发**；**动态实体号从 37 起** |
| 20 | ★★ `ipairs` 陷阱 | **必须 `index - 1`**，否则首尾箱子重叠 |
| 21 | ★★★ 引擎缺口 | **没有暴露给脚本的地面射线** ⇒ 斜坡上箱子会浮/沉 |
| 22 | ★★★★ **nil 三值约定** | `nil`+无错误 = **池满**（预期）；`nil`+有错误 = **真故障** |
| 23 | ★★ `setloot` | `(entity, weapon, pickup_radius)` 三参数 |
| 24 | ★★★★★ **XP 全覆盖** | ticket **20261011-22000**；`sv_main_mp.cpp:3587`（1:1 镜像）/`:5301`（DM 专属） |
| 25 | ★★★ **50 是测出来的** | `dm.lua:30-34` IW4 `_rank.gsc`：击杀 50 + **爆头再 50** |
| 26 | ★★ 穷尽性证明 | `git grep addClientXp` = **仅两个生产者** |
| 27 | ★★★ 政策声明 | 应用到本模式是 **RECONSTRUCTION POLICY** |
| 28 | ★ 四个 API | `addscore` / `addxp` / `addkill` / `codol.player` |
| 29 | ★★ 故意保留 | 计分与重生**仍是死斗的**（否则不可测） |
| 30 | ★★★ 已删的测试手段 | "每命 5 秒给一把步枪" —— 证明 grant 能过 pmove 后**已删** |
| 31 | ★ `codol_friendly_fire_mode` | **0** |

---

## 十一、结论

### 1. ★★★★★ **cs 12506..12692 是零售回放**——全包最重要的数据陷阱

```
cs 12506..12692 **广播 1148..1211**
        ↓
★ 但它**不是**本服务器的注册结果，而是**零售捕获的逐字回放**
        ↓
★★★ 零售有 **1211** 个武器；本服务器只有 **8** 个
        ↓
后果：**九个箱子六个发真枪、三个什么都没发**
```

★ **⇒ 修复：`setloot` 拒绝无法解析的武器 ⇒ **用失败行当尺子测量实际数量**。**

### 2. ★★★★★ **XP 论证是"证据链完整"的典范**

```
问题：AAR 的 xp/gp 行在其他模式全空
        ↓
穷尽性证明：`git grep addClientXp` ⇒ 只有两个生产者
        ↓
数值来源：`dm.lua:30-34` 的 IW4 `_rank.gsc` **实测 50**
        ↓
★ 政策声明：应用到本模式是 **RECONSTRUCTION POLICY**（无逐模式实测）
```

### 3. ★★★★ **拾取是按键使用，且 Lua 无法自己实现**（`entity_touch` 被拒）

★ **⇒ 分工：Lua 注册内容，C++ 做范围测试/提示/授予。**
**★ 三个引擎符号：`cursorHint` / `ServerCore::driveCursorHints` / `processLootCommittedCommand`。**

### 4. ★★★★ **`nil` 三值约定**（无错误=池满 / 有错误=真故障）

### 5. ★★★ **`dmz.lua` 曾逐字节等于 `dm.lua`** ⇒ 玩起来是死斗

### 6. ★★★ **两个精确的引擎常量**：**动态实体号从 37 起**、**无地面射线暴露给脚本**

---

## 十二、下一步

- `dm.lua`（82 行，`dmz.lua` 的前身 + XP 的**权威出处 `dm.lua:30-34` / `:40`**）
- `war.lua`（120 行）/ `conf.lua`（123 行）/ `td.lua`（67 行）
- `configs_s.info`（1,067 行）
- `mp_playlists_shipRetail_release.info`（3,970 行）
