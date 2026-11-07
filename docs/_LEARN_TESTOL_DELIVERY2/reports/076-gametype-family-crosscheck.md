# 学习报告 076（重开）— 家族对照：`td.lua` / `coop.lua` / `cha.lua` 回调 + 三处结构性发现

**学习范围**：`td.lua`（68 行）+ `coop.lua`（16 行）+ `cha.lua` 回调段（134–236 / 330–377）+ 跨文件普查
**性质**：全实测（**gametype 家族交叉验证完成**）
**★★★ 本报告收录**三处结构性发现**：①`war.lua:19` 的 sha256 是错的 ②`coop.lua` 有意不注册处理器 ③**FAIL-SOFT 硬要求只在 3/11 个文件里落实**

---

## 一、★ 更正：`war.lua:19` 引用的 sha256 **是错的**

### 1.1 实测结果（PowerShell `Get-FileHash -Algorithm SHA256`）

| 文件 | 字节 | sha256 |
|---|---|---|
| **`td.lua`** | **3,595** | **`5D4D27342AF613B0D04BE37E386B450D6B96C1733A1EAD0D73BB78AF734BEDF0`** |
| **`zarena.lua`** | **3,595** | 同上（**逐字节相同**） |
| **`zhunt.lua`** | **3,595** | 同上（**逐字节相同**） |
| `dm.lua` | 4,618 | `E3E113EA3F288871D2CF23329ED62EBBD9A52F6AB159AD4201E1C631B193AEF5` |
| `war.lua` | 7,018 | `0C4BB7186B9B1E10498B4CE621DA602A9E3F15E8A41A6E23CD9F0E794F28E8A7` |
| `conf.lua` | 7,082 | `1DE2A873B9FCBB708B6BD5A544E7020B84F0FA3B6E65156AF1F481834082C5F1` |
| `cha.lua` | 21,493 | `99EAB1D3588386BDBA91E60273895E867B8E61FF71762BD1DAF2535A0CD4C96D` |
| `dmz.lua` | 9,552 | `975059A1DBE56B880B0535F8CF4360BAC3D55396245C6BDCB9D97270897BB452` |
| `sd.lua` | 20,121 | `15705227C1D9258D750537E34BDEDCB12D118A4F07BCC5D05BBC49ED32610713` |
| `zm.lua` | 37,359 | `93A10D97848ACE838C220D23ECEEE77ED1E0E02AA858378DF1133DB74816BFE1` |

### 1.2 ★★★ 结论

```
`war.lua:19` 的注释写：
  "td.lua/zarena.lua/zhunt.lua are byte-identical (sha256 **40e1d88adb37af0f...**)"
        ↓
★★★ 实测：**5D4D27342AF613B0...**
        ↓
★ "byte-identical" 这个**事实断言是对的**（三文件确实逐字节相同）
★★★ 但引用的 **sha256 值是错的**
```

★★ **⇒ 这是**"结论对、证据错"的典型**（与报告 075 记录的头注释矛盾同类）。**

★ **⇒ 报告 075 第九节的"待核对项"**现已解决**：以 `5D4D27342AF613B0...` 为准。**
**⇒ 更早的记录是对的,`war.lua:19` 的注释是错的。****

---

## 二、★★★★★ `td.lua` 全文：**过期的 3000 未传播**

### 2.1 头注释**逐字照抄 `dm.lua`**（第 1–6 行）

```lua
-- Free-for-all. The client books this as the playlist token "ffa"; the engine
-- gametype - and so this file's name - is "dm", which is the stock IW name.
--
-- There are no map game objects: playlist 23 carries no objective of any kind,
-- and the shipped description is "Eliminate the enemies to score. First player
-- to reach the score limit wins."

print("gametype has no map gameobjects", "dm")
```

★★★ **⇒ `td.lua` 的头注释与 `print` 声称自己是 **`dm` / `ffa` / playlist 23**。**
**⇒ 而文件名 `td` 意味着 **team deathmatch**。**

★ **⇒ 这正是 `war.lua:18-21` 指出的问题（逐字）：**
```
"td.lua is **NOT the model** for this file. ... td.lua's own header still says
 'Free-for-all ... the engine gametype is dm' and prints 'dm' -
 it is **a copy of `dm.lua`** and it **never calls addteamscore**."
```

### 2.2 ★★★★★ **致命的差异：重生延迟仍是 3000**

```lua
-- td.lua 第 60-61 行
    local _, respawn_error, respawn_error_code = codol.call(
        "method:respawn", player, 3000)
```

| 文件 | 重生延迟 | 状态 |
|---|---|---|
| **`dm.lua`** | **1500** | ★ 已按 `pm_type` 实测修正 |
| **`td.lua`** | **3000** | ★★★ **仍是发明值** |
| `zarena.lua` | **3000** | ★★★ 同上 |
| `zhunt.lua` | **3000** | ★★★ 同上 |
| `dmz.lua` | **3000** | ★★★ 同上（无任何理由注释） |
| `war.lua` | **3000** | ✓ **有理由**（"cha's value ... war is scored and timed like cha"） |
| `conf.lua` | **3000** | ✓ **有理由**（"cha's and war's"） |
| `cha.lua` | **3000** | ✓ 原始出处 |

### ★★★★★ 完整的因果链

```
`dm.lua` 曾经用 **3000**
        ↓
★ `td.lua` / `zarena.lua` / `zhunt.lua` / `dmz.lua` 从**那时**的 `dm.lua` 复制
        ↓
★★★ `dm.lua` 后来实测发现 **3000 是发明的、慢一倍**，改成 **1500**
   （`dm.lua:62`："**3000 WAS INVENTED and it was twice too slow**"）
        ↓
★★★ **但修正没有传播到那四个副本**
        ↓
⇒ `td`/`zarena`/`zhunt`/`dmz` **至今仍在用被判定为错的 3000**
```

★★ **⇒ 而 `war.lua` / `conf.lua` 用 3000 是**有理由的**（按 `cha` 的方式计分与计时,`DedicatedSession.cpp:414-424`），
**但 `td`/`zarena`/`zhunt`/`dmz` 用 3000 **没有任何理由注释**。****

★ **⇒ 与报告 073 呼应：`dmz.lua` 自称"was a byte-for-byte copy of `dm.lua` until now"，
**但它的重生是 3000,而 `dm.lua` 是 1500** ⇒ 这个"copy"是**复制于修正之前**。****

### 2.3 ★★★ `td.lua` **有** V1.11 XP 块（第 30–52 行）

```lua
-- V1.11 / (2) match info -- XP + gp MODE COVERAGE, ticket 20261011-22000.
-- ...
-- 50 IS MEASURED, NOT INVENTED: dm.lua:30-34 records IW4 _rank.gsc's 50 XP for
-- a kill plus 50 more for a headshot, ...
```

★★★ **⇒ 这说明 `td.lua` 的复制发生在 **V1.11 XP 批次之后**，但**在 1500 修正之前**。**

★ **⇒ 一个精确的**时间线推断**：**
```
V1.11 XP 批次（ticket 20261011-22000） ⇒ td.lua 已包含 ✓
1500 重生修正                          ⇒ td.lua 未包含 ✗
        ↓
★★★ ⇒ **XP 批次早于 1500 修正**
```

### 2.4 ★★★ `td.lua` **没有** `dm.lua` 的 1500 实测注释块

★★ **⇒ `dm.lua` 第 55–74 行有 20 行的实测论证（n=24 / p25=median=p75 / 仪器选择），
**`td.lua` 完全没有**。**

★ **⇒ 所以 `td.lua` 的 3000 **既无实测也无理由** —— 是一个**裸的过期常量**。**

---

## 三、★★★★★ `coop.lua` 全文（16 行）：**有意不注册处理器**

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

### ★★★★★ 三层结构声明

```
① 使命进度 / actor / 目标 / 检查点 / 表现  ⇒ ★ **全归 map 层**
② gametype 层**只建立所有剧情任务共享的规则**
③ ★★★ **有意不注册任何 PvP 计分 / 击杀 / 定时重生处理器**
```

### ★★★★★ **"former file was a stale copy of `dm.lua`"**（逐字）

```
"The **former file was a stale copy of `dm.lua`** and **awarded FFA points
 before respawning the player after every death**."
        ↓
★★★ ⇒ 旧 `coop.lua` = 又一个 `dm.lua` 的过期副本
   ⇒ 后果：**在剧情任务里给 FFA 分,并在每次死亡后重生玩家**
        ↓
★ 修复：**删掉全部处理器**
        ↓
★★★ 理由："Wetwork death and checkpoint restart are **mission state transitions**
     and **will be owned by the cargoship map layer**."
```

★★ **⇒ 这是**全包第四个"过期 `dm.lua` 副本"**：**
```
① `dmz.lua`   ⇒ 自称曾是逐字节副本（已重写为 BattleCity）
② `td.lua`    ⇒ 仍是副本（自称 dm/ffa/playlist 23）
③ `zarena.lua`⇒ 仍是副本
④ `zhunt.lua` ⇒ 仍是副本
⑤ `coop.lua`  ⇒ **曾是副本,已清空处理器**
```

### ★★★ 三个精确的地图/角色名

| # | 名称 | 说明 |
|---|---|---|
| **1** | **Wetwork** | 剧情地图名 |
| **2** | **Price / Nikolai / hazmat** | ★ 友方 actor spawner 三种 |
| **3** | **cargoship map layer** | ★★ 将拥有死亡与检查点重生的那一层 |

★ **⇒ 与报告 075 的 `coop_training_mp_cargoship.lua`（4,683 行）呼应：**
```
`coop.lua` 把死亡/检查点**让给** cargoship map 层
        ↓
★ 而 `coop_training_mp_cargoship.lua` 就是那个 map 层文件
```

★★ **⇒ 且 `print("campaign gametype initialized", "coop")` 与其他文件的
`print("gametype has no map gameobjects", <gt>)` **格式不同** ——
**因为它确实有 map gameobjects（在 map 层）。****

---

## 四、★★★★★ `cha.lua` 回调的三个独有动作

### 4.1 ★★★ `adddeath`（第 194–202 行，逐字）

```lua
-- ★★ 28100 刀AB（甲方：「把 cha/spy/sd 模式的字段表加回来」）——
--   `deaths` 列：计分板一直有位置（FieldDeaths@137）、底层 `addClientDeaths` 也早已实现，
--   **只是没有脚本调用** ⇒ 这一列恒为 0。这里在死亡事件里给死者 +1。
--   判据：TAB 计分板的死亡列不再全 0。**纯服务端，不碰任何客户端下发。**
local _, death_error, death_error_code = codol.call(
    "method:adddeath", player, 1)
```

★★★ **⇒ 一个"第三次"的"写好了但没接线"实例：**
```
`FieldDeaths@137`（计分板位置）✓ 存在
`addClientDeaths`（底层实现）✓ 已实现
        ↓
★★★ **但没有脚本调用** ⇒ `deaths` 列**恒为 0**
        ↓
⇒ 修复：`adddeath(player, 1)`（★ 给**死者**加,不是击杀者）
```

★ **⇒ 出处标记：**28100 刀AB**；甲方口径："把 cha/spy/sd 模式的字段表加回来"**。

★★ **⇒ 与报告 069 记录的 `zm.lua` 的 `adddeath`**是同两个实例之一**（`FieldDeaths@137` + `addClientDeaths`）。**

★ **⇒ 判据（逐字）："TAB 计分板的死亡列不再全 0"；且"**纯服务端,不碰任何客户端下发**"。**

### 4.2 ★★★★★ `playsound` 与**别名槽 62**（第 204–236 行，逐字）

```lua
-- ★★★ 28100 刀CB（甲方：「击杀音效加回来」）——
--   **通用击杀音**（`mp_hit_kill`）由服务端 C++ 按 `killFeedbackSound_` 发，一直在；
--   **特殊击杀音**只给「坦克(tank)」「战警(police)」两类武器（甲方口径），
--   音效名 `wpn_kill_tank_special` 由服务端启动期注册到别名槽 62（cs 3686）。
--   ⚠ 两条硬规矩（上一轮 P0 的教训）：
--     ① **必须在 `adddeath` 之后**（本块就在 adddeath 之后）—— 表现层绝不许挡住计分；
--     ② **整段包 `pcall`** —— 若 `method:playsound` 在当前二进制里不可用，
--        只打一句 skipped，绝不让 `player_killed` 中断。
```

### ★★★★★ 五个精确事实

| # | 项 | 值 |
|---|---|---|
| **1** | 通用击杀音 | **`mp_hit_kill`**（服务端 C++ 按 **`killFeedbackSound_`** 发,**一直都在**） |
| **2** | 特殊击杀音武器类 | ★ **只有「坦克(tank)」「战警(police)」两类** |
| **3** | 音效名 | **`wpn_kill_tank_special`** |
| **4** | ★★ **别名槽** | **62**（对应 **cs 3686**） |
| **5** | 注册时机 | **服务端启动期** |

### ★★★★★ 两条硬规矩（逐字）

```
① ★★★ **必须在 `adddeath` 之后**
   —— "表现层绝不许挡住计分"
        ↓
② ★★★ **整段包 `pcall`**
   —— 若 `method:playsound` 在当前二进制里不可用,
      只打一句 skipped,**绝不让 `player_killed` 中断**
        ↓
★ 出处：**"上一轮 P0 的教训"**
```

★★ **⇒ 第 ① 条是**层次优先级的明确规定**：**计分 > 表现层**。**

### ★★★ 参数类型的教训（第 217–218 行，逐字）

```lua
-- 刀CF：把**错误原文**打出来（之前只打 skipped，修了两轮才定位到参数类型，教训）
local ok, ret, err, code = pcall(
    codol.call, "method:playsound", 105)
```

★★★ **⇒ 两个精确事实：**
```
① `method:playsound` 的**唯一参数是 105**（★ 别名槽 62 的对应值）
   —— 注意注释说"别名槽 62（cs 3686）",而调用传的是 **105**
② ★★★ 教训："**之前只打 skipped,修了两轮才定位到参数类型**"
   ⇒ 必须**打印错误原文**（`ret` 里的 Lua 错误）
```

★ **⇒ 第 ② 条与报告 072 的"必须打错误原文"是**同一类教训的第二次出现**。**

### 4.3 ★★★ `pcall(codol.call, ...)` 的**四元组**返回（第 218–227 行）

```lua
local ok, ret, err, code = pcall(
    codol.call, "method:playsound", 105)
if not ok then
    print("kill sound special FAILED(lua) series=" .. series ..
        " err=" .. tostring(ret))
elseif err ~= nil then
    print("kill sound special FAILED(api) series=" .. series ..
        " ret=" .. tostring(ret) ..
        " err=" .. tostring(err) ..
        " code=" .. tostring(code))
else
    print("kill sound special series=" .. series ..
        " weapon=" .. tostring(event.weapon_name) ..
        " alias=62 ret=" .. tostring(ret))
end
```

★★★ **⇒ 三种失败模态**（与报告 073 的 `dmz.lua` nil 三值同类,但这里是四元组）：**
```
① `ok == false`        ⇒ **Lua 层错误**（`ret` 是错误消息）
② `ok == true, err ≠ nil` ⇒ **API 层错误**（`ret`=返回值,`err`=错误,**`code`=错误码**）
③ `ok == true, err == nil` ⇒ **成功**（`ret` 是返回值）
```

★ **⇒ 这印证了 `codol.call` 契约的**完整形态**：**
```
`pcall(codol.call, ...)` ⇒ `(ok, ret, err, code)` **四元组**
```

★★ **⇒ 且日志里明确打出 **`alias=62`** ⇒ 印证别名槽号。**

### 4.4 ★★★ KILL FX 表的**继承语义**（第 1–18 行，逐字）

```lua
-- 28600: the 92-entry table only covered the weapons whose WeaponDef carries
-- an FX at +1464. The other 361 definitions still have one through their FAMILY
-- (resolved-fx-table.tsv, 453 rows, 12 FX names). Retail's "one series, one
-- effect" is exactly this table; a weapon with no family effect stays silent.
-- ...
-- 28800 (second knife): OWN-ONLY KILL FX.
-- The 453-row table was produced by propagating an FX along base_weapon groups in
-- BOTH directions. That gave 32 BASE weapons (ak47_mp, m4a1tech_mp, scar_mp, ...)
-- a skin variant's effect, and it is exactly the operator's "some guns have no
-- kill effect yet they trigger one".
-- Retail semantics: WeaponDef +1464 ("fx") is a property of THIS weapon asset,
-- not of its family -- `base_weapon` groups a family, `fx` describes the variant
-- (findings\步进-击杀特效系列侧核对-92武器12个特效-20261017-28100.md sec.46).
-- So only the 92 rows whose OWN definition carries an FX stay. Everything else
-- falls through to KILL_FX_FALLBACK (nil) => no effect at all, ...
```

★★★★★ **⇒ 一个**极其重要的**双向传播错误**：**
```
① 原始 **92 项**表只覆盖了 WeaponDef **+1464** 处有 FX 的武器
② 其余 **361** 个定义通过**家族**有 FX
   （`resolved-fx-table.tsv`，**453 行**,**12 个 FX 名**）
        ↓
★★★ ③ 但 "453 行表"是**沿 `base_weapon` 组双向传播**得到的
   ⇒ 这让 **32 个基础武器**（`ak47_mp` / `m4a1tech_mp` / `scar_mp` / `acr_mp` /
     `cheytac_mp` / `vepr_mp` / `rpd_mp` / `miniuzi_mp` / `mp5k_mp` /
     `deserteagle_mp` / `ump45_mp` / `aks74u_mp` / ...）**拿到了皮肤变体的特效**
        ↓
★★★ ④ 这正是甲方说的 **"some guns have no kill effect yet they trigger one"**
        ↓
⑤ **零售语义**：`WeaponDef +1464`（"fx"）是**这个武器资产自己的属性**,
   **不是家族的**
   —— `base_weapon` 分组**家族**,`fx` 描述**变体**
        ↓
★★★ ⑥ ⇒ **只有 92 行保留**；其余落到 `KILL_FX_FALLBACK`（**nil**）
   ⇒ **完全没有特效**
```

### ★★★★★ 五个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | WeaponDef 的 FX 偏移 | **`+1464`** |
| **2** | 原始表项数 | **92** |
| **3** | 其余定义数 | **361** |
| **4** | 传播后的表 | **`resolved-fx-table.tsv`，453 行，12 个 FX 名** |
| **5** | ★ 被误赋特效的**基础武器**数 | **32** |

★★★ **⇒ 92 + 361 = 453** ⇒ **数字自洽。**

★ **⇒ 出处：**`findings\步进-击杀特效系列侧核对-92武器12个特效-20261017-28100.md sec.46`**。**

★★ **⇒ 且明确"表是生成的,不要手改"（第 5–6 行，逐字）：**
```
"Generated from 01-docs\40-evidence\按武器特效基础继承-20261011-28000\
 resolved-fx-table.tsv -- **do not hand-edit; regenerate instead**."
```

### 4.5 ★★★ `suppresscorpse` 的**两次 pcall + 双检查**（第 330–347 行）

```lua
-- 28600: retail REPLACES the body. The operator's reference
-- clips (coins / fish / pixel blocks / a shatter) all show the corpse gone, and
-- 2697 `death.gsc` plays the family effect on `j_SpineUpper` instead of a blood pool.
-- Suppress only when a family effect matched, so a plain kill keeps its body.
-- codol.call returns (ret, err, code) and does not raise, so a
-- bare pcall() would report success even when the builtin is absent. Keep BOTH halves and name the reason in the log.
if replaces_body then
    local ok, sup_ret, sup_err, sup_code =
        pcall(codol.call, "method:suppresscorpse", player)
    if not ok or sup_err ~= nil then
        print("corpse suppress skipped " .. tostring(fx_name) ..
            " ok=" .. tostring(ok) ..
            " err=" .. tostring(sup_err) ..
            " code=" .. tostring(sup_code))
    end
end
```

★★★★★ **⇒ 这是 `codol.call` 契约的**最清晰表述**（逐字）：**
```
"`codol.call` returns `(ret, err, code)` and **does not raise**,
 so a **bare `pcall()` would report success even when the builtin is absent**.
 Keep **BOTH halves** and name the reason in the log."
        ↓
★★★ ⇒ 必须检查 **`not ok`** **或** **`sup_err ~= nil`**
```

★ **⇒ 条件 `replaces_body` ⇒ "**Suppress only when a family effect matched, so a plain kill keeps its body**"。**

### 4.6 ★★★ `playfxat` 的**胸腔高度**（第 348–357 行，逐字）

```lua
-- 28600: chest height, not feet. `getorigin` is the FEET, and
-- every family FX that names the body (fx_*_player_torso_*,
-- fx_hit_death_*, fx_space_death) is authored around the torso;
-- 2697 `death.gsc` anchors the same class on `j_SpineUpper`.
-- 40 engine units is roughly the spine on a standing body.
local fx_x, fx_y, fx_z = origin[1] * 1.0, origin[2] * 1.0, origin[3] * 1.0
local _, fx_error, fx_code = codol.call(
    "function:playfxat", fx_index,
    fx_x, fx_y, fx_z + 40.0,
    0.0 * 1.0, 0.0 * 1.0, 0.0 * 1.0)
```

### ★★★★★ 两个精确事实

| # | 项 | 值 |
|---|---|---|
| **1** | `getorigin` 返回的是 | ★ **脚（FEET）** |
| **2** | ★★ **胸腔高度偏移** | **`+40.0` engine units** |

★★★ **⇒ `* 1.0` 的**双重提升**写法（每一项都乘 `1.0`）：**
```
fx_x = origin[1] * 1.0
fx_z = origin[3]
0.0 * 1.0  ← 连零都乘 1.0
        ↓
★★★ ⇒ 这是**强制转成 double 的惯用写法**
   （与报告 065 的 `sd.lua` 记录一致：
    "playfxat **expects six finite transform numbers**" ⇒ 要求 double,不是 integer）
```

★ **⇒ 六个变换分量 = `(fx_x, fx_y, fx_z+40, 0, 0, 0)`（旋转全零）。**

★★ **⇒ 且注释给出**权威锚点**：`2697 death.gsc` 把同一类特效锚在 **`j_SpineUpper`****。****

---

## 五、★★★★★ **FAIL-SOFT 覆盖率普查**（重大不一致）

### 5.1 `war.lua` / `conf.lua` / `sd.lua` 的**硬要求声明**（逐字相同）

```
"FAIL-SOFT (**hard requirement**). A Lua error escaping a world-event callback
 **tears down the gametype thread** and **ends a real player's match**,
 so the **ENTIRE callback body runs inside `pcall`** and the failure branch only prints."
```

★ **⇒ `sd.lua:292` 措辞更强："FAIL-SOFT, **HARD**: every body is pcall-wrapped"。**

### 5.2 ★★★★★ 实测覆盖率（`Grep` 全目录）

| # | 文件 | 行数 | 注册的事件 | **整回调 `pcall`** |
|---|---|---|---|---|
| **1** | **`war.lua`** | 121 | `player_killed` @43 | ★✓ **有**（@44） |
| **2** | **`conf.lua`** | 124 | `player_killed` @47 | ★✓ **有**（@48） |
| **3** | **`sd.lua`** | 335 | `player_killed` @148 + **N 个 `sd_*`** @321 | ★✓ **有**（@149 / @322） |
| 4 | `dm.lua` | 83 | `player_killed` @14 | ✗ **无** |
| 5 | `dmz.lua` | 194 | `client_spawned` @137 / `player_killed` @147 | ✗ **无** |
| 6 | `td.lua` | 68 | `player_killed` @14 | ✗ **无** |
| 7 | `zarena.lua` | 68 | `player_killed` @14 | ✗ **无** |
| 8 | `zhunt.lua` | 68 | `player_killed` @14 | ✗ **无** |
| 9 | `zm.lua` | 736 | `zm_round_tick` @586 / `entity_killed` @704 / `player_killed` @712 | ✗ **无** |
| **10** | **`cha.lua`** | 377 | `player_killed` @134 | ★ **部分**（@213 只包 playsound；@340 逐调用） |
| **11** | **`coop.lua`** | 16 | ★ **无** | — |

### ★★★★★ 结论

```
声明"硬要求"的文件：**3 个**（war / conf / sd）
实际落实的文件：    **3 个**（同上）
★★★ 未落实的文件：  **7 个**（dm / dmz / td / zarena / zhunt / zm + cha 部分）
```

★★★ **⇒ "hard requirement"（硬要求）在 11 个文件里只有 3 个遵守。**

★ **⇒ 最矛盾的是 `cha.lua`：**
```
`cha` 是 `war.lua` / `conf.lua` **明确引用的范本**（"cha.lua:14-44 the team branch"）
        ↓
★★★ 但 `cha.lua` **自己不满足**那条"硬要求"
        ↓
★ 它只包了 `playsound` 子块（@213）和逐调用（@340）
★★★ ⇒ **`cha.lua:134` 的 `player_killed` 主体未被 pcall 包裹**
```

★★ **⇒ 而 `zm.lua`（736 行,最复杂）三个处理器**全部未包** —— 且 `zm.lua` 的
`player_killed` / `entity_killed` 中就有 `codol.call("method:respawn", ...)`。****

---

## 六、★★★★★ `codol_friendly_fire_mode` 的**四值语义**

```lua
-- sd.lua:331-334
-- codol_friendly_fire_mode: CODOL/COD team modes use 0=no damage, 1=target,
-- 2=half reflect, 3=half shared. Mode selection remains gametype-owned.
-- TODO(CODOL): source this default from authoritative playlist/game rules.
codol_friendly_fire_mode = 0
```

### ★★★★★ 四个值

| 值 | 语义 |
|---|---|
| **0** | ★ **no damage**（无伤害） |
| **1** | **target** |
| **2** | **half reflect**（半反射） |
| **3** | **half shared**（半共享） |

### ★★★ 各文件的赋值

| 文件 | 值 |
|---|---|
| `cha.lua` | **0** |
| `conf.lua` | **0** |
| `coop.lua` | **0** |
| `dm.lua` | **0** |
| `dmz.lua` | **0** |
| `sd.lua` | **0** |
| `td.lua` | **0** |
| `war.lua` | **0** |
| `zm.lua` | **0** |
| `zarena.lua` | **0** |
| `zhunt.lua` | **0** |

★★★ **⇒ 11 个文件**全部是 0**（无友军伤害）。**

★★ **⇒ 但 `sd.lua` 明确标注：**
```
"Mode selection **remains gametype-owned**."
"TODO(CODOL): source this default from **authoritative playlist/game rules**."
        ↓
★ ⇒ 即：0 是**当前硬编码的默认**,正确来源应是 playlist 规则（未做）
```

★ **⇒ 这是一个**第 N 个 `TODO(CODOL)`**（`war.lua` / `conf.lua` 也有同样的一句）。**

★★ **⇒ 而手雷/爆炸类模式（`sd`）与冷兵器模式（`cha`）用同一个 0 ⇒ 可能不合适,但**未被验证**。**

---

## 七、★★★★★ `sd.lua` 的 **per-KILL vs per-ROUND** 警告

```lua
-- sd.lua:285-290
-- not be attributed from a log. These handlers only OBSERVE: they emit no score
-- and mutate no state, because method:addteamscore is per KILL and awarding it
-- here would end the match after scoreLimit KILLS instead of after scoreLimit
-- ROUNDS -- the warning at the top of the player_killed handler above.
-- method:addteamscore is the real binding (sv_script_builtin_mp.cpp:4132) and
-- stays deliberately unused in this file.
```

### ★★★★★ 完整的因果链

```
`method:addteamscore` 是 **per KILL**（每次击杀）
        ↓
★★★ 但 `sd` 的比赛上限是 **per ROUND**（每回合）
        ↓
若在 `sd` 里调用它 ⇒ **比赛会在 scoreLimit 次击杀后结束,
                    而不是在 scoreLimit 个回合后**
        ↓
⇒ `sd.lua` **故意不用它**
```

★ **⇒ 权威绑定：`method:addteamscore` = **`sv_script_builtin_mp.cpp:4132`**。**

★★ **⇒ 与报告 069 的 `sd.lua` 记录呼应（"SD team score = round count from C++; must NEVER call addteamscore"）。**

★ **⇒ 观察者只打印四个字段（第 294–295 行，逐字）：**
```
"Only fields the marshaller is **known to always set** are printed
 (sequence, server_time, client_num, weapon_name -- **sv_script_lua_mp.cpp:938-952**)."
```

★★ **⇒ 四个字段 + 权威出处：**
```
`sequence` / `server_time` / `client_num` / `weapon_name`
        ↓
★ 按 `sv_script_lua_mp.cpp:938-952` 的 marshaller 保证**总会设置**
```

★ **⇒ 这是**"只依赖有保证的字段"的谨慎做法**（与 `codol.call` 的 nil 三值同类）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ **`war.lua:19` 的 sha 是错的** | 注释 **`40e1d88adb37af0f...`** vs 实测 **`5D4D27342AF613B0...`** |
| 2 | ★ 三元组确认 | `td`/`zarena`/`zhunt` **逐字节相同**（**3,595 字节**） |
| 3 | ★★★★ **`td.lua` 自称 dm** | 头注释 **`ffa` / `dm` / playlist 23**，`print("dm")` |
| 4 | ★★★★★ **过期 3000** | `td`/`zarena`/`zhunt`/`dmz` **仍用 3000**（`dm.lua` 已改 **1500**） |
| 5 | ★ 时间线推断 | `td.lua` **已含 V1.11 XP 块** ⇒ **XP 批次早于 1500 修正** |
| 6 | ★★ `td.lua` 无实测注释 | `dm.lua:55-74` 的 20 行论证**完全没有** |
| 7 | ★★★★★ **`coop.lua` 有意无处理器** | "**There is deliberately no PvP score, kill, or timed-respawn handler here**" |
| 8 | ★★★ 旧 `coop.lua` | **"a stale copy of `dm.lua`"** ⇒ 在剧情任务里给 FFA 分 + 每次死亡重生 |
| 9 | ★★ 归属 | 死亡/检查点属 **cargoship map 层** |
| 10 | ★ 友方 actor | **Wetwork** 地图有 **Price / Nikolai / hazmat** 三种 spawner |
| 11 | ★★★ `cha.lua` 的 `adddeath` | `FieldDeaths@137` + `addClientDeaths` **写好了但没接线** ⇒ deaths 列恒 0 |
| 12 | ★★ 给谁加 | ★ **给死者**（`player`,不是击杀者） |
| 13 | ★★★★ **击杀音效别名槽** | **槽 62**（**cs 3686**），音效名 `wpn_kill_tank_special` |
| 14 | ★ 特殊音效武器类 | **只有「坦克(tank)」「战警(police)」** |
| 15 | ★ 通用音效 | **`mp_hit_kill`**（服务端按 **`killFeedbackSound_`** 发,一直在） |
| 16 | ★★★★★ **两条硬规矩** | ① **必须在 `adddeath` 之后** ② **整段包 `pcall`**（"上一轮 P0 的教训"） |
| 17 | ★ `playsound` 参数 | **`105`**（注释说槽 62） |
| 18 | ★★★ 教训 | "**之前只打 skipped,修了两轮才定位到参数类型**" |
| 19 | ★★★★ **四元组** | `pcall(codol.call, ...)` ⇒ **`(ok, ret, err, code)`** |
| 20 | ★★★★★ **KILL FX 双向传播错误** | **92 项**原表 + 传播后 **453 行** ⇒ **32 个基础武器误得皮肤特效** |
| 21 | ★ WeaponDef FX 偏移 | **`+1464`** |
| 22 | ★ 其余定义数 | **361**（92 + 361 = **453**） |
| 23 | ★★ 零售语义 | `+1464` 是**该武器资产自己的**属性,不是家族的 |
| 24 | ★★ 生成物 | `resolved-fx-table.tsv`，"**do not hand-edit; regenerate instead**" |
| 25 | ★★★★★ **`codol.call` 契约** | "**does not raise**, so a **bare `pcall()` would report success even when the builtin is absent**. Keep **BOTH halves**" |
| 26 | ★★★ `playfxat` 高度 | `getorigin` 是**脚** ⇒ **`+40.0`** 到胸腔（`j_SpineUpper`） |
| 27 | ★★ `* 1.0` 惯用 | 强制 double（`playfxat` 要 6 个有限 double） |
| 28 | ★★★★★ **FAIL-SOFT 覆盖率** | 声明 **3** 个 / 落实 **3** 个 / **未落实 7 个** |
| 29 | ★★★ 最矛盾者 | `cha.lua` 是范本却**不满足**该硬要求 |
| 30 | ★★★★★ **`codol_friendly_fire_mode` 四值** | **0=no damage / 1=target / 2=half reflect / 3=half shared** |
| 31 | ★ 实际赋值 | 11 个文件**全部 = 0** |
| 32 | ★ ★ `TODO(CODOL)` | 应从 **playlist/game rules** 取,当前硬编码 |
| 33 | ★★★★★ **`sd` 的 per-KILL vs per-ROUND** | `addteamscore` 是 **per KILL**；`sd` 上限是 **per ROUND** ⇒ **故意不用** |
| 34 | ★ 权威绑定 | `sv_script_builtin_mp.cpp:4132` |
| 35 | ★★★ 观察者四字段 | `sequence` / `server_time` / `client_num` / `weapon_name`（`sv_script_lua_mp.cpp:938-952`） |

---

## 九、结论

### 1. ★★★★★ **`coop.lua` 有意不注册任何处理器**

★ **⇒ 旧的 `coop.lua` 是**又一个 `dm.lua` 过期副本**，会在剧情任务里给 FFA 分。**
**⇒ 死亡/检查点归属被明确让给 **cargoship map 层**。**

### 2. ★★★★★ **FAIL-SOFT "hard requirement" 只在 3/11 个文件里落实**

```
声明并落实：war / conf / sd
★★★ 未落实：dm / dmz / td / zarena / zhunt / zm（+ cha 部分）
```

★ **⇒ 最矛盾的不是最复杂的 `zm.lua`,而是**被当作范本的 `cha.lua`**。**

### 3. ★★★★★ **过期常量 3000 未传播**

```
`dm.lua` 已实测修正为 **1500**（"3000 WAS INVENTED and it was twice too slow"）
        ↓
★★★ 但 `td` / `zarena` / `zhunt` / `dmz` **仍是 3000**（且无任何理由注释）
```

★ **⇒ 时间线：V1.11 XP 批次 ⇒ 复制 ⇒ 1500 修正（**修正最晚**）。**

### 4. ★★★★★ **`cha.lua` 的 KILL FX 双向传播错误**（32 个基础武器误得皮肤特效）

★ **⇒ 92 项原表 + 361 项家族 = 453 行 ⇒ 但零售语义是"**只有该武器自己的 FX**"。**

### 5. ★★★★ **`codol.call` 契约的最清晰表述**（"does not raise ⇒ bare `pcall()` 会假成功"）

### 6. ★★★ **`codol_friendly_fire_mode` 四值语义**（0/1/2/3），且 11 个文件全用 0

### 7. ★★★ **`sd` 的 per-KILL vs per-ROUND**（为何故意不用 `addteamscore`）

### 8. ★★★ **击杀音效别名槽 62（cs 3686）** + 两条硬规矩（计分优先于表现层）

### 9. ★★ **`war.lua:19` 引用的 sha256 是错的**（结论对、证据错）

---

## 十、下一步

- `configs_s.info`（1,067 行）—— 82 个 section 的详细内容
- `mp_playlists_shipRetail_release.info`（3,970 行）
- `coop_training_mp_cargoship.lua`（4,683 行）—— `coop.lua` 让渡的那一层
- `ol-mod-runtime-manifest.json`（28,209 B）
- 其余 `maps\*.lua`（18 个）
