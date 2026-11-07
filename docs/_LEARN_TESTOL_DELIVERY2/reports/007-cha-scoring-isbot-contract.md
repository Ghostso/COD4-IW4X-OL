# 学习报告 007（重开）— `cha.lua` 计分段 + `dm.lua` 对照

**学习范围**：`gametypes\cha.lua`（21,493 B，行 114–175）+ `gametypes\dm.lua`（4,618 B，行 1–30）
**性质**：全实测
**★★★ 本报告补全 Lua → 原生的**全部方法名**，并发现 `method:isbot` 的**版本契约**

---

## 一、★★★ `cha.lua` 的完整结构（按行号定位）

```
行 1–18    头部注释（击杀特效表的论证）
行 19–113  KILL_FX_BY_WEAPON = { ... }   ← ★★★ 92 项武器→特效映射
行 114     KILL_FX_FALLBACK = nil
行 116–119 头部注释（bot 门禁的 DLL 版本契约）
行 119     KILL_FX_ISBOT_WARNED = false
行 121–124 codol.call("function:setmapgameobjects", "cha", "airdrop_pallet")
行 125–127 assert(error_message == nil, ...)
行 129     print("gametype map gameobjects activated", "cha")
行 131–133 头部注释（Charge = TDM 变体）
行 134+    assert(codol.on("player_killed", ...))   ← 计分主体
```

★★★ **⇒ 21,493 字节里，**前 113 行（特效表）占大头**，计分逻辑在后面。**

---

## 二、★★★★ `function:setmapgameobjects` —— **地图游戏对象注册**（行 121–129）

```lua
local _, error_message, error_code = codol.call(
    "function:setmapgameobjects",
    "cha",
    "airdrop_pallet")
assert(
    error_message == nil,
    tostring(error_message) .. ":" .. tostring(error_code))

print("gametype map gameobjects activated", "cha")
```

### ★★★ 语义

| 参数 | 值 | 含义 |
|---|---|---|
| 第 1 | `"cha"` | **gametype 名** |
| 第 2 | `"airdrop_pallet"` | ★★★ **游戏对象的脚本类名** |

★★★ **⇒ `codol.call("function:<name>", ...)` 与 `codol.call("method:<name>", ...)` 是**两类不同的调用**：**
```
function:<name>   →  全局函数（静态环境）
method:<name>     →  对象方法（第一个参数是 receiver）
```

★ **`cha` 注册了一个游戏对象 `airdrop_pallet`（空投托盘）。**

★★★ **⇒ 这解释了其余 gametype 里的 `print("gametype has no map gameobjects", "<gt>")`：**
```
有对象：cha  →  调 setmapgameobjects，不打印那句
无对象：dm / conf / war / coop  →  只打印 "gametype has no map gameobjects"
```

★ **`error_message == nil` 用 `assert`** ——
★★ **⇒ 与 "FAIL-SOFT" 原则一致：`setmapgameobjects` **只在加载时跑一次**，
所以**允许抛**（同 `codol.on`）。**

---

## 三、★★★★ `method:isbot` 的**版本契约**（行 116–119，逐字）

> **28800: the bot gate needs the DLL half (`method:isbot`). While an older DLL is
> still loaded every call reports `"unknown builtin"`; say it ONCE instead of on
> every kill, so a stale deploy is visible without flooding the log.**

```lua
local KILL_FX_ISBOT_WARNED = false
```

★★★ **⇒ 这是 Lua 与 DLL（插件二进制）之间的**版本契约**：**

```
Lua 期望 DLL 实现 method:isbot
        ↓
旧 DLL  ⇒  每次调用返回错误串 "unknown builtin"
        ↓
不能每杀一次就打印（刷屏）
        ↓
用 KILL_FX_ISBOT_WARNED 标志，只打印一次
```

★★★ **⇒ 新增错误串：`"unknown builtin"`。**

★ **⇒ 这是**交付包内 Lua 与插件必须版本匹配**的直接证据。**
**（Lua 在 `payload\Ayria\Assets\OlMod\`，插件在 `payload\Ayria\Plugins\`）**

★★ **⇒ 如果 `CodolGameServer.Localnet32` 是旧版，`cha.lua` 只会在第一次击杀时打印一次警告。**

---

## 四、★★★ `cha.lua` 的完整计分链（行 134–175）

### 4.1 注册

```lua
assert(codol.on("player_killed", function(player, event)
    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        local attacker = codol.player(event.attacker_entity_num)
        local same_team, team_error = codol.call(
            "method:issameteam", player, attacker)
        if team_error == nil and not same_team then
```

★★ **三重守卫**：
```
① attacker_entity_num ~= nil           攻击者存在
② attacker_entity_num ~= target_client_num   不是自杀
③ not same_team                        不是队友
```

### 4.2 ★★★ 四连加分（逐条）

```lua
            -- TODO(CODOL): source these defaults from the authoritative
            -- playlist/game-rule teamScorePerKill and rank score owners.
            local _, score_error, score_error_code = codol.call(
                "method:addscore", attacker, 100)          ← 显示分 +100
            local _, team_score_error, team_score_error_code = codol.call(
                "method:addteamscore", attacker, 1)        ← ★ 队伍分 +1
            ...
            local _, xp_error, xp_error_code = codol.call(
                "method:addxp", attacker, 50)              ← XP +50
```

**完整的四连**（含 `addkill`，见下段）：

| 方法 | 参数 | 值 | 作用 |
|---|---|---|---|
| `method:addscore` | attacker, 100 | **100** | 显示分 |
| `method:addteamscore` | attacker, 1 | **1** | ★ 队伍分（限分读它） |
| `method:addkill` | attacker, 1 | **1** | 击杀列 |
| `method:addxp` | attacker, 50 | **50** | 经验 |

★★★ **⇒ 与 `dm.lua` 的对照：**
```
dm   （FFA）：addscore 50 + addkill 1 + addxp 50          （无 addteamscore）
cha  （TDM）：addscore 100 + addteamscore 1 + addkill 1 + addxp 50
war  （TDM）：addscore 100 + addteamscore 1 + addkill 1   （无 addxp）
conf （KC） ：addscore 100 + addteamscore 1 + addkill 1   （无 addxp）
```

### 4.3 ★★★ `addkill` 的论证（行 156–162，逐字）

> V1.9 (V19-H). **cha had NO `method:addkill` producer**, so the scoreboard **kill
> column stayed 0** while the per-kill display score grew. The counter is written by
> **`addClientKills` (`sv_client_mp.cpp:2243`)** and a **gametype script has to call it**,
> exactly as `dm.lua:49` and `war.lua:78-82` already do.
> **`addkill` does NOT feed the match limit** (that path reads the display score and
> the team score), so **adding it cannot end a match early**.

★★★ **⇒ 关键：`addkill` **不影响比赛结束**，所以加它是**安全**的。**

★★ **⇒ 三个计数器的作用域：**
```
addscore      显示分（UI）+ ★ 也是限分读取的两个之一
addteamscore  队伍分（限分读取的另一个）
addkill       仅计分板的击杀列（不影响限分）
```

### 4.4 ★★ XP 论证**逐字重复**（行 163–172）

★★ **与 `td.lua:30-39` **完全相同**的一段注释**（ticket `20261011-22000`）。**
**⇒ 批量复制粘贴的证据。**

### 4.5 ★★ 未完成标记（行 141–142）

```lua
-- TODO(CODOL): source these defaults from the authoritative
-- playlist/game-rule teamScorePerKill and rank score owners.
```

★★ **⇒ `100` / `1` / `50` 是**硬编码**，本应从播放列表规则读。**

---

## 五、★★ `dm.lua` 头部（行 1–30）—— 与 `td.lua` 的**逐字对照**

### 5.1 ★★★ `dm.lua` 与 `td.lua` 的差异（同一段文字）

| 行 | `dm.lua` | `td.lua` |
|---|---|---|
| 1–2 | 同 | 同 |
| 4 | "playlist **23**" | "playlist **23**" |
| 8 | `print("gametype has no map gameobjects", "dm")` | 同 |
| 12 | "There is deliberately **no addteamscore** here - that is the one line that separates this from cha." | **无此句** |
| 14 | `assert(codol.on("player_killed", ...))` | 同 |
| 18–24 | 计分说明 + `ui_DMKillScore "50"` | 同 |
| 25–26 | `codol.call("method:addscore", attacker, 50)` | 同 |
| 30 | `-- CODREF: IW4 _rank.gsc registers 50 XP for a teamless kill and 50` | 见 `td.lua:35` 的**不同措辞** |

★★★ **⇒ 两者**高度相似但不同**（清单哈希也不同：`E3E113EA…` vs `5D4D2734…`）。**

★ **`dm.lua` 4,618 B vs `td.lua` 3,595 B（差 1,023 B）。**
**⇒ `dm.lua` 多了 1 KB 的内容（可能正是那段"no addteamscore"论证 + 更多注释）。**

★★★ **⇒ `war.lua:18-21` 说 "td.lua is a copy of dm.lua"** ——
**方向对，但**不是逐字复制**（哈希不同）。**

### 5.2 ★ `dm.lua` 的播放列表号

```
dm   → playlist 23   （FFA）
cha  → （未读到）
conf → （未读到）
war  → playlist 30   （TDM）
```

★ **`dm.lua:4` 与 `td.lua:4` 都是 "playlist 23"。**

---

## 六、★★★★ 累计的 Lua → 原生 API 全表（重开版汇总）

### 6.1 `codol.*` 四个入口

```lua
codol.entity(num)          → 实体对象
codol.player(num)          → 玩家对象
codol.on(event, fn)        → 注册回调（返回值可 assert）
codol.call(name, ...)      → → (ret, err_msg, err_code)
```

### 6.2 `method:*`（对象方法，第 1 参是 receiver）

```
method:issameteam
method:finishplayerdamage
method:finishsharedplayerdamage
method:addscore
method:addteamscore
method:addkill
method:addxp
method:respawn
method:isbot                ← ★★★ 需要新版 DLL
```

### 6.3 `function:*`（全局函数）

```
function:setmapgameobjects   ← ★★★ 参数 (gametype名, 对象类名)
```

### 6.4 事件

```
player_damage    （common.lua）
player_killed    （dm/td/cha/conf/war）
```

### 6.5 全局变量

```
codol_friendly_fire_mode   （0/1/2/3）
```

### 6.6 已知错误串

```
"unknown builtin"           ← ★★★ 旧 DLL 缺 method 时返回
```

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `cha.lua` 结构 | 1–18 注释 / 19–113 特效表 / 114–175 计分 |
| 2 | `KILL_FX_BY_WEAPON` | **92 项** |
| 3 | `KILL_FX_FALLBACK` | `nil` |
| 4 | ★★★ 新 API | `function:setmapgameobjects("cha", "airdrop_pallet")` |
| 5 | ★★★ 新 API | `method:isbot` |
| 6 | ★★★ 新错误串 | **`"unknown builtin"`** |
| 7 | ★★ 版本契约 | Lua 期望新 DLL，旧 DLL 报 unknown builtin，**只警告一次** |
| 8 | cha 计分 | `addscore 100` + `addteamscore 1` + `addkill 1` + `addxp 50` |
| 9 | dm 计分 | `addscore 50` + `addkill 1` + `addxp 50`（**无 addteamscore**） |
| 10 | ★ `addkill` 语义 | **不影响限分**，只填计分板击杀列 |
| 11 | `addkill` 写入者 | `addClientKills` @ `sv_client_mp.cpp:2243` |
| 12 | ★★ TODO | `cha.lua:141-142`（分数本应从播放列表读） |
| 13 | ★★ 重复注释 | XP 论证段在 `cha.lua` 与 `td.lua` **逐字相同** |
| 14 | cha 播放列表 | （未读到，`war`=30，`dm`=23） |

---

## 八、结论

### 1. ★★★★ 交付包里 Lua 与插件是**版本耦合**的（`method:isbot` / `"unknown builtin"`）

★★★ **⇒ 换战斗服（`CodolGameServer.Localnet32`）时，必须实现 Lua 期望的所有 `method:*`，
否则 Lua 侧静默降级（只打印一次警告）。**

### 2. ★★★ `cha.lua` 的主体是**特效表**（92 项），计分只占一小部分

### 3. ★★★ 四连加分的作用域不同，`addkill` 是安全的

```
addscore      →  显示 + ★ 参与限分
addteamscore  →  ★ 参与限分
addkill       →  仅计分板（不影响限分）
addxp         →  仅经验
```

### 4. ★★ 五个 gametype 的计分**互不相同**，且都有据可查

### 5. ★★ 未完成的 TODO 仍在（分数硬编码，未从播放列表读）

---

## 九、下一步

- `gametypes\sd.lua`(20,121) / `zm.lua`(37,359) / `dmz.lua`(9,552) 头部
- `maps\coop_training_mp_cargoship.lua`(201,269) 头部
- `cha.lua` 行 175–末尾（计分剩余）
- ★ **全量核对 `MANIFEST.sha256`**（PowerShell 分类器恢复后立即做）
- ★★ **清理我上次留下的 6 个 `.bak` 文件**
