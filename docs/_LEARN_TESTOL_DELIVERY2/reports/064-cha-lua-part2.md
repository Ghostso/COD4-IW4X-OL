# 学习报告 064（重开）— `cha.lua` 后半（175–378 行）：击杀特效与死亡计分

**学习范围**：`payload\Ayria\Assets\OlMod\GameScripts\gametypes\cha.lua` 第 175–378 行
**性质**：全实测（**`cha.lua` 377 行全文完成**）
**★★★ 本报告收录**12 个击杀特效的两类划分**与**五个新原生 API**

---

## 一、★★★ `cha.lua` 的完整结构（377 行）

| 行范围 | 内容 |
|---|---|
| **1–18** | 头部注释（特效表的两代论证） |
| **19–113** | `KILL_FX_BY_WEAPON`（**92 项**） |
| **114** | `KILL_FX_FALLBACK = nil` |
| **116–119** | `KILL_FX_ISBOT_WARNED = false` |
| **121–129** | `codol.call("function:setmapgameobjects", "cha", "airdrop_pallet")` |
| **134–192** | 计分主体（`addscore`/`addteamscore`/`addxp`/`addkill`） |
| **194–202** | ★★★ **`adddeath`（新增）** |
| **204–236** | ★★★ **特殊击杀音（`playsound`）** |
| **238–369** | ★★★ **击杀特效（12 个家族，两类）** |
| **370–375** | `respawn(player, 3000)` |
| **377** | `codol_friendly_fire_mode = 0` |

---

## 二、★★★★★ `adddeath`：计分板死亡列（第 194–202 行）

```lua
-- ★★ 28100 刀AB（甲方：「把 cha/spy/sd 模式的字段表加回来」）——
--   `deaths` 列：计分板一直有位置（FieldDeaths@137）、底层 `addClientDeaths` 也早已实现，
--   **只是没有脚本调用** ⇒ 这一列恒为 0。这里在死亡事件里给死者 +1。
--   判据：TAB 计分板的死亡列不再全 0。**纯服务端，不碰任何客户端下发。**
local _, death_error, death_error_code = codol.call(
    "method:adddeath", player, 1)
if death_error ~= nil then
    print("player death deferred", death_error, death_error_code)
end
```

### ★★★★★ 一个"写好了但没接线"的实例

```
计分板位置：**FieldDeaths @ 137**  ✓ 存在
底层实现：**addClientDeaths**     ✓ 已实现
        ↓
★★★ **只是没有脚本调用** ⇒ deaths 列恒为 0
        ↓
修复：在死亡事件里 `adddeath(player, 1)`
```

★★★ **⇒ 这与记忆里的教训**完全同源**：**
> 记忆 `codol-battle-server-world-binding`：
> "**'代码写好了但没接线'比'缺数据'更常见**"

★ **⇒ 第 2 个"没接线"实例（第 1 个是 `bind_world`）。**

★★ **⇒ 且明确：**"纯服务端，不碰任何客户端下发"。**

### ★★★ 新增 API

```
method:adddeath(player, 1)
```

---

## 三、★★★★★ 特殊击杀音（第 204–236 行）

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

### ★★★★★ 三条关键信息

| # | 信息 | 内容 |
|---|---|---|
| **1** | 通用击杀音 | **`mp_hit_kill`**，由**服务端 C++** 按 `killFeedbackSound_` 发（**一直在**） |
| **2** | 特殊击杀音 | 只给 **`tank`** / **`police`** 两类武器 |
| **3** | 音效名 | **`wpn_kill_tank_special`** |
| **4** | ★★★ 注册位置 | **别名槽 62**（**cs 3686**） |

### ★★★★★ 两条硬规矩（"上一轮 P0 的教训"）

```
① **必须在 `adddeath` 之后**
   ⇒ 表现层绝不许挡住计分
② **整段包 `pcall`**
   ⇒ 若 method:playsound 不可用，只打 skipped，绝不让 player_killed 中断
```

★★★ **⇒ 第 ① 条是**顺序依赖**（计分优先于表现）。**
**⇒ 第 ② 条是**fail-soft 的第二次应用**（报告 004 已记录 gametype 的 fail-soft 要求）。**

### ★★★ 三层 pcall 的精确实现（第 212–235 行）

```lua
if event.weapon_name ~= nil then
    pcall(function()                                    -- ① 外层 pcall
        local seriesList = { "tank", "police" }
        for _, series in ipairs(seriesList) do
            if string.find(event.weapon_name, series, 1, true) ~= nil then
                -- 刀CF：把**错误原文**打出来（之前只打 skipped，修了两轮才定位到参数类型，教训）
                local ok, ret, err, code = pcall(
                    codol.call, "method:playsound", 105)  -- ② 内层 pcall（★ 只传一个参数 105）
                if not ok then
                    print("kill sound special FAILED(lua) series=" .. series .. " err=" .. tostring(ret))
                elseif err ~= nil then
                    print("kill sound special FAILED(api) series=" .. series ..
                        " ret=" .. tostring(ret) .. " err=" .. tostring(err) .. " code=" .. tostring(code))
                else
                    print("kill sound special series=" .. series ..
                        " weapon=" .. tostring(event.weapon_name) .. " alias=62 ret=" .. tostring(ret))
                end
            end
        end
    end)
end
```

### ★★★★★ 三个精确细节

| # | 细节 | 值 |
|---|---|---|
| **1** | `method:playsound` 参数 | **`105`**（★ 单参数，不是槽号 62） |
| **2** | ★★★ **三层判定** | `not ok`（Lua 错）/ `err ~= nil`（API 错）/ 成功 |
| **3** | ★ 教训（逐字） | **"之前只打 skipped，修了两轮才定位到参数类型"** |

★★★ **⇒ 第 1 条揭示了一个**参数类型的坑**：**
```
注释说"音效名注册到**别名槽 62**（cs 3686）"
        ↓
但 `method:playsound` 的参数是 **105**
        ↓
★★★ **105 ≠ 62** ⇒ 说明 105 是**另一种 ID**（可能是 sound alias index）
```

★★ **⇒ 第 3 条教训："修了两轮才定位到参数类型"。**

★ **⇒ 第 2 条是**区分 Lua 错与 API 错**的关键设计：**
```
pcall(codol.call, ...) 返回 (ok, ret, err, code)
        ↓
not ok      ⇒  ★ **Lua 层异常**（如参数类型错）
err ~= nil  ⇒  ★ **API 层错误**（builtin 不可用）
两者都没有  ⇒  成功
```

★★ **⇒ 而注释明确："`codol.call` returns (ret, err, code) and **does not raise**,
so a bare `pcall()` would report success even when the builtin is absent."**

---

## 四、★★★★★ 击杀特效的**两类划分**（第 299–315 行）

```lua
-- 28800: TWO KINDS OF KILL FX, AND ONLY ONE OF THEM REPLACES THE BODY.
--
-- The operator's clips split the 12 families in two:
--   * REPLACING (body is gone, the effect IS the body):
--       misc/fx_coinkill01            coins
--       misc/fx_fish01                fish
--       misc/fx_death02/03/04         campaigner / cherryblossom / alt
--   * ON-BODY (the body stays; the effect plays at the chest):
--       env/fire/fx_fire_player_torso_dragons
--       env/smoke/fx_smoke_player_torso
--       weapon/fx_hit_death_engine01
--       weapon/fx_hit_halloween_night01
--       weapon/fx_hit_ronin01
--       weapon/fx_space_death
-- The previous build suppressed the corpse for EVERY family, so every
-- kill lost its body -- the operator's "要么全消失". Suppress only the
-- replacing set; everything else keeps its body and just gets the FX.
```

### ★★★★★ 12 个特效家族的完整分类

#### A. REPLACING（替换尸体，5 个）

| # | 特效名 | 效果 |
|---|---|---|
| **1** | **`misc/fx_coinkill01`** | **金币** |
| **2** | **`misc/fx_fish01`** | **鱼** |
| **3** | **`misc/fx_death02`** | （alt） |
| **4** | **`misc/fx_death03_cherryblossom`** | **樱花** |
| **5** | **`misc/fx_death04_campaigner`** | **campaigner** |

#### B. ON-BODY（保留尸体，在胸口播放，6 个）

| # | 特效名 |
|---|---|
| **6** | **`env/fire/fx_fire_player_torso_dragons`** |
| **7** | **`env/smoke/fx_smoke_player_torso`** |
| **8** | **`weapon/fx_hit_death_engine01`** |
| **9** | **`weapon/fx_hit_halloween_night01`** |
| **10** | **`weapon/fx_hit_ronin01`** |
| **11** | **`weapon/fx_space_death`** |

★★★ **⇒ 5 + 6 = **11 个**（注释说 12 个家族，可能有 1 个未列或已合并）。**

### ★★★★★ 一个重要的 bug 与修复（逐字）

```
The previous build suppressed the corpse for EVERY family, so every
kill lost its body -- the operator's "要么全消失".
Suppress only the replacing set; everything else keeps its body and just gets the FX.
```

★★★ **⇒ 完整的因果：**
```
上一版：**所有**家族都抑制尸体
        ↓
★★★ 每次击杀都丢尸体 ⇒ 甲方："**要么全消失**"
        ↓
修复：**只抑制 replacing 集合**（5 个）
        ↓
★ 其余保留尸体，只播特效
```

★ **⇒ "要么全消失"是甲方的**原话**（中文）。**

### ★★★ 五个 replacing 的精确判定（第 316–321 行）

```lua
local replaces_body =
    fx_name == "misc/fx_coinkill01" or
    fx_name == "misc/fx_fish01" or
    fx_name == "misc/fx_death02" or
    fx_name == "misc/fx_death03_cherryblossom" or
    fx_name == "misc/fx_death04_campaigner"
```

★ **⇒ 五个 `==` 比较，精确匹配。**

---

## 五、★★★★★ 机器人的特效抑制（第 244–280 行）

```lua
-- 28800: BOTS DO NOT GET PLAYER-SPECIFIC KILL EFFECTS.
-- The table is keyed on the killing weapon only, so every bot kill ran the
-- same cosmetic family effect a human unlock would. The operator's rule:
--   "人机本不应该触发武器专属击杀特效".
-- `method:isbot` reads SvClientSlot::isBot over the same generation-safe
-- player object the rest of this handler uses. A missing builtin (older
-- DLL) answers nil, and nil is treated as "not a bot" so the gate can never
-- silently disable the effect for humans.
```

### ★★★★★ 三条关键设计

| # | 设计 | 内容 |
|---|---|---|
| **1** | **规则来源** | 甲方原话：**"人机本不应该触发武器专属击杀特效"** |
| **2** | `method:isbot` 实现 | 读 **`SvClientSlot::isBot`** |
| **3** | ★★★ **nil 的处理** | **`nil` 视为"不是 bot"** ⇒ **绝不会静默禁用人类的特效** |

★★★ **⇒ 第 3 条是**关键的 fail-safe 设计**：**
```
旧 DLL 缺 method:isbot
        ↓
返回 nil
        ↓
★★★ 若把 nil 当 bot ⇒ 人类的特效全被禁用（**灾难**）
        ↓
★ 所以 nil ⇒ "不是 bot" ⇒ 特效**照常播放**
```

### ★★★ 只抑制特效，不抑制重生（第 259–261 行）

```lua
if attacker_is_bot == true then
    -- Only the EFFECT is suppressed here. The respawn below still runs,
    -- because the victim of a bot kill is usually a human and must come
    -- back on the same schedule as any other death.
    print("kill fx weapon=" .. tostring(event.weapon_name) .. " outcome=skipped reason=bot")
    fx_suppressed = true
end
```

★★★ **⇒ 一个精确的边界：**
```
bot 击杀 ⇒ **只抑制特效**
        ↓
★ **重生照常**（`respawn(player, 3000)`）
        ↓
理由："被 bot 杀的受害者通常是**人类**，必须按同样节奏回来"
```

### ★★★ 旧 DLL 的警告只打一次（第 266–270 行）

```lua
if bot_error ~= nil and not KILL_FX_ISBOT_WARNED then
    KILL_FX_ISBOT_WARNED = true
    print("kill fx isbot deferred " .. tostring(bot_error) ..
        " (bot gate inactive until the new DLL is loaded)")
end
```

★★ **⇒ 与报告 007 的 `KILL_FX_ISBOT_WARNED` 机制**完全对应**（只警告一次）。**

---

## 六、★★★★★ 特效的**播放实现**（第 322–368 行）

### 6.1 ★★★ 两个新 API（第 322、355 行）

```lua
local fx_index = codol.call("function:effectindex", fx_name)      -- ★ 解析特效索引
local origin = codol.call("method:getorigin", player)             -- ★ 取玩家位置
local _, fx_error, fx_code = codol.call(
    "function:playfxat", fx_index,
    fx_x, fx_y, fx_z + 40.0,
    0.0 * 1.0, 0.0 * 1.0, 0.0 * 1.0)                              -- ★ 在指定位置播放
```

### ★★★★★ 三个新 API

| # | API | 签名 |
|---|---|---|
| **1** | **`function:effectindex`** | `(fx_name) → index` |
| **2** | **`method:getorigin`** | `(player) → {x, y, z}` |
| **3** | **`function:playfxat`** | `(fx_index, x, y, z, ?, ?, ?)` |

★★★ **⇒ `playfxat` 有 **7 个参数**（fx_index + 6 个浮点）。**

★ **⇒ 后 3 个浮点全传 `0.0`（可能是角度/速度）。**

### 6.2 ★★★★★ **胸口高度 +40** 的依据（第 348–357 行，逐字）

```lua
-- 28600: chest height, not feet. `getorigin` is the FEET, and
-- every family FX that names the body (fx_*_player_torso_*,
-- fx_hit_death_*, fx_space_death) is authored around the torso;
-- 2697 `death.gsc` anchors the same class on `j_SpineUpper`.
-- 40 engine units is roughly the spine on a standing body.
local fx_x, fx_y, fx_z = origin[1] * 1.0, origin[2] * 1.0, origin[3] * 1.0
```

### ★★★★★ 精确的偏移依据

```
`getorigin` 返回的是**脚**
        ↓
所有命名身体的家族特效（fx_*_player_torso_*、fx_hit_death_*、fx_space_death）
都是**围绕躯干**制作的
        ↓
2697 `death.gsc` 把同一类锚定在 **`j_SpineUpper`**
        ↓
★★★ **40 engine units ≈ 站立身体的脊柱高度**
        ↓
所以 `fx_z + 40.0`
```

★★ **⇒ 出处：**2697 `death.gsc`**（另一个 build 的脚本，用作参照）。**

★ **⇒ `origin[i] * 1.0` —— 强制转浮点（防止整数除法）。**

### 6.3 ★★ 尸体抑制（第 338–347 行）

```lua
if replaces_body then
    local ok, sup_ret, sup_err, sup_code =
        pcall(codol.call, "method:suppresscorpse", player)
    if not ok or sup_err ~= nil then
        print("corpse suppress skipped " .. tostring(fx_name) ..
            " ok=" .. tostring(ok) .. " err=" .. tostring(sup_err) .. " code=" .. tostring(sup_code))
    end
end
```

★★ **⇒ 第四个新 API：`method:suppresscorpse(player)`。**

### 6.4 ★★★★★ 一个**关键的 pcall 陷阱说明**（第 335–337 行，逐字）

```lua
-- codol.call returns (ret, err, code) and does not raise, so a
-- bare pcall() would report success even when the builtin is
-- absent. Keep BOTH halves and name the reason in the log.
```

★★★★★ **⇒ 这是**极重要的一条 API 契约**：**
```
codol.call **不抛异常**，返回 (ret, err, code)
        ↓
★★★ 所以 `pcall(codol.call, ...)` 会**永远返回 ok=true**
        ↓
★ 必须**同时检查** `ok` **和** `err`
        ↓
★★★ **"Keep BOTH halves and name the reason in the log"**
```

★★ **⇒ 这解释了为什么本文件所有 `codol.call` 都检查 `err ~= nil`。**

---

## 七、★★★ 特效未命中时的诊断（第 283–297 行）

```lua
if fx_name == nil then
    -- 28600 diagnostic: the skipped names (cheytacwargod_mp at 12:50) are
    -- supposed to be IN this table, so print the bytes rather than the
    -- escaped form. If the length or the bytes disagree with the key, the
    -- event name is the problem, not the table.
    local shown = ""
    if kill_weapon ~= nil then
        for i = 1, string.len(kill_weapon) do
            shown = shown .. string.format("%02x", string.byte(kill_weapon, i))
        end
    end
    print("kill fx FIRST SIGHTING weapon=" .. tostring(kill_weapon) ..
        " len=" .. tostring(kill_weapon ~= nil and string.len(kill_weapon) or -1) ..
        " hex=" .. shown)
    print("kill fx weapon=" .. tostring(kill_weapon) .. " outcome=skipped")
end
```

★★★ **⇒ 打印**十六进制字节 + 长度**，而不是转义形式：**
```
理由（逐字）："If the length or the bytes disagree with the key,
              the **event name** is the problem, not the table."
        ↓
★★★ ⇒ 用 hex + len 判断是"表错了"还是"事件名错了"
```

★ **⇒ 具体案例：`cheytacwargod_mp`（12:50 时首次出现）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `cha.lua` 总行数 | **377** |
| 2 | ★★★★★ **`adddeath` 实例** | **FieldDeaths @ 137** + `addClientDeaths` 已实现，**只是没脚本调用** |
| 3 | ★ 新增 API 1 | **`method:adddeath(player, 1)`** |
| 4 | ★★ 通用击杀音 | **`mp_hit_kill`**（C++ 按 `killFeedbackSound_` 发） |
| 5 | ★★★ 特殊击杀音 | 只给 **`tank`** / **`police`**，音效名 **`wpn_kill_tank_special`** |
| 6 | ★★★ 别名槽 | **62**（cs **3686**） |
| 7 | ★★★ `playsound` 参数 | **`105`**（≠ 62） |
| 8 | ★★★ 两条硬规矩 | **必须在 `adddeath` 之后** + **整段 `pcall`** |
| 9 | ★★★ 三层判定 | `not ok`（Lua）/ `err ~= nil`（API）/ 成功 |
| 10 | ★★★ **12 家族两类** | **REPLACING 5 个** / **ON-BODY 6 个** |
| 11 | ★★★★★ **尸体 bug** | 上一版**所有**家族都抑制 ⇒ 甲方"**要么全消失**" |
| 12 | ★★★ 修复 | **只抑制 replacing 的 5 个** |
| 13 | ★★★ bot 规则 | 甲方：**"人机本不应该触发武器专属击杀特效"** |
| 14 | ★★★★★ **nil 处理** | **`nil` = "不是 bot"** ⇒ 绝不静默禁用人类特效 |
| 15 | ★★★ bot 边界 | **只抑制特效，重生照常** |
| 16 | ★★ 新 API 2/3/4 | **`function:effectindex`** / **`method:getorigin`** / **`method:suppresscorpse`** |
| 17 | ★★ 新 API 5 | **`function:playfxat`**（7 参数） |
| 18 | ★★★ **+40 依据** | `getorigin` 是**脚**；40 units ≈ **脊柱**（2697 `death.gsc` 的 `j_SpineUpper`） |
| 19 | ★★★★★ **pcall 陷阱** | **`codol.call` 不抛异常** ⇒ `pcall` 恒 `ok=true` ⇒ **必须同时查 `err`** |
| 20 | ★★ 诊断 | 未命中时打印 **hex + len**（判断是表错还是事件名错） |

---

## 九、结论

### 1. ★★★★★ **`adddeath` 是第二个"写好了但没接线"的实例**

★ **⇒ 与 `bind_world` 同类（记忆已记录）。**

### 2. ★★★★★ **尸体抑制的 bug 极典型**

```
所有家族都抑制 ⇒ 每次击杀都丢尸体 ⇒ 甲方"要么全消失"
        ↓
修复：只抑制 replacing 的 5 个
```

### 3. ★★★★★ **`codol.call` 不抛异常**是最重要的 API 契约

★ **⇒ `pcall` 会恒返回 `ok=true` ⇒ 必须同时检查 `err`。**

### 4. ★★★★ **bot 的 nil 处理是 fail-safe 的典范**

```
旧 DLL 缺 method:isbot ⇒ 返回 nil
        ↓
nil 视为"不是 bot" ⇒ 人类特效照常
```

### 5. ★★★ **胸口 +40 units** 有明确依据（2697 `death.gsc` 的 `j_SpineUpper`）

### 6. ★★ **`playsound` 的参数是 105 不是槽号 62**（参数类型的坑）

---

## 十、下一步

- `sd.lua`（334 行）
- `zm.lua`（735 行）
- `dmz.lua`（193 行）
- `dm.lua` / `war.lua` / `conf.lua` / `td.lua` 全文
- `coop.lua`（15 行，已读）
- `configs_s.info`（1,067 行）
- `mp_playlists_shipRetail_release.info`（3,970 行）
- `MarketplaceSkus.json`（22,413 行）
