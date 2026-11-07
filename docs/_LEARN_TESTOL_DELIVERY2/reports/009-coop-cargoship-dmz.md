# 学习报告 009（重开）— `coop_training_mp_cargoship.lua` / `dmz.lua`

**学习范围**：`maps\coop_training_mp_cargoship.lua`(201,269) 行 1–42 + `gametypes\dmz.lua`(9,552) 行 1–26
**性质**：全实测
**★★★ 本报告揭示交付物的本质："资产在，逻辑被出版商删掉了"**

---

## 一、★★★ `coop_training_mp_cargoship.lua` —— 战役地图（201 KB，最大的脚本）

### 1.1 身份（第 1 行）

```
-- Wetwork / "Unidentified".
```

★★ **CODOL 战役关卡，代号 `Wetwork` / `Unidentified`。**
★ **对应 `coop.lua` 注释里的 "The Wetwork map carries allied Price, Nikolai, and hazmat actor spawners"。**

### 1.2 ★★★ 返回表的消费时机（第 3–8 行）

> The returned table is consumed **once** by **`SV_LoadMapScriptMetadata`** before
> the **gameplay source is assembled**. This campaign map **has no MP-style
> `minimap_corner` pair**, so declaring **`compass_map_cargoship`** here would make
> the existing **square minimap setup reject the map**. The mission controller will
> switch **`compass_map_cargoship` / `compass_map_cargoship_2`** at the **measured
> phase boundaries** instead.

★★★ **⇒ 两条重要契约：**
```
① 地图脚本的返回值由 SV_LoadMapScriptMetadata **一次性**消费
   （在 "gameplay source is assembled" 之前）
② ★ 战役地图**没有** MP 式的 minimap_corner 对
   ⇒ 在这里声明 compass_map_cargoship 会让**方形小地图装配拒绝该地图**
   ⇒ 改由 mission controller 在"实测阶段边界"切换
```

### 1.3 ★★★ MapEnts 是权威（第 10–13 行）

> Mission progression is **map driven**. **The shipped `MapEnts` already names every
> major phase** (`bridge`, `deck`, `quarters`, `hallways`, `cargo holds`,
> `sinking escape`, and `helicopter extraction`); **the server keeps those records
> authoritative rather than copying positions out of the recording.**

★★★ **⇒ 七个阶段名（逐字）：**
```
bridge / deck / quarters / hallways / cargo holds / sinking escape / helicopter extraction
```

★★ **⇒ "the server keeps those records authoritative"** ——
**服务端用 `MapEnts` 里的记录，**不**从录制里抄坐标。**
★ **这是对"从 demo 抄数据"这一诱惑的**明确拒绝**。**

### 1.4 ★★ 空环境守卫（第 14–16 行）

```lua
if codol == nil then
    return {}
end
```

★★★ **⇒ 当脚本在**游戏外**被加载（例如静态分析工具）时，`codol` 是 `nil`，直接返回空表。**

★ **⇒ 这是**唯一**如此写的地图脚本（其余只返回材质声明）。**
**也说明这个文件会被**工具**加载（用于校验）。**

### 1.5 ★★★ 新增两个原生 API（第 18–42 行）

```lua
local function entities(value, key)
    local result, message, code = codol.call(
        "function:getentarray", value, key)          ← ★★★ 取实体数组
    if result == nil then
        print("wetwork map query failed", key, value, message, code)
        return {}
    end
    return result
end

local function phase(name, value, key)
    return {
        name = name,
        triggers = entities(value, key),
    }
end

local function send_command(player, command)
    local _, message, code = codol.call(
        "method:sendservercommand", player, command) ← ★★★ 让服务端执行命令
    if message ~= nil then
        print("wetwork command failed", command, message, code)
        return false
    end
    return true
end
```

| 新 API | 形态 | 用途 |
|---|---|---|
| `function:getentarray` | `(value, key) → array` | ★ 按 classname/key 取实体数组 |
| `method:sendservercommand` | `(player, command) → (_, err, code)` | ★★★ **让服务端执行命令** |

★★★ **⇒ `sendservercommand` 是**脚本驱动服务端**的通道** ——
**战役的阶段推进靠它。**

★ **`phase(name, value, key)` 返回 `{name, triggers}`** ——
**阶段 = 名字 + 触发实体数组。**

---

## 二、★★★★ `dmz.lua` —— "资产在，逻辑被删"的完整陈述

### 2.1 身份（第 1–4 行）

> **BattleCity.** The client books this as `"dmz"`; the mode is **Brave Games / battle
> royale**, and **Activision stripped its logic when the game shut down**. This file
> was a **byte-for-byte copy of `dm.lua`** until now, which is why **the mode played
> as deathmatch**.

★★★ **⇒ 第五处"副本失真"：`dmz.lua` 曾是 `dm.lua` 的逐字节副本 ⇒ 大逃杀玩成了死斗。**

### 2.2 ★★★★★ 核心论断（第 6–10 行，逐字）

> **WHAT IS ACTUALLY MISSING IS SMALLER THAN IT LOOKS.** The **ASSETS survived the
> strip** — `mp_battlecity`'s **model band** publishes the whole **pickup set**, the
> **parachute**, the **care-package pod** and the **play-area cylinder**
> (dumped with **`OLMOD_DUMP_MODEL_BAND=1`**, **283 entries**).
> **Only the script that places them is gone.**
> This is step one of putting it back: **loot you can walk up to and see.**

★★★★★ **⇒ 这是对整个交付项目性质的**最精确陈述**：**

```
出版商（Activision）关服时**剥掉了逻辑**
        ↓
但**资产**（模型/贴图/数据）**留下来了**
        ↓
★ "缺的东西比看起来小" —— 缺的只是**放置它们的脚本**
```

★★ **实证**：
```
mp_battlecity 的 model band 有 283 项
含：pickup set / parachute / care-package pod / play-area cylinder
导出工具：OLMOD_DUMP_MODEL_BAND=1
```

★★★ **⇒ 这与报告 008 的"configstring band"是同一个概念 —— `model band` 就是那个 band。**

### 2.3 ★★★ "PRESS-USE，不是走过去捡"（第 12–16 行）

> **PICKUP IS PRESS-USE, NOT WALK-OVER**, and that is what retail does. The dmz demo
> shows **`cursorHint` going 0 → 1** with **`cursorHintEntIndex`** naming the crate
> while the player stands at it, and the weapon arriving **only afterwards** —
> so **the player asks and the server answers**. Walking over loot in a battle royale
> and having it grabbed for you would be wrong anyway.

★★ **⇒ 零售语义由 demo 实证：**
```
cursorHint          0 → 1        （玩家站到箱子旁）
cursorHintEntIndex  指向那个箱子
武器                 之后再到达   ⇒ "玩家请求，服务端应答"
```

### 2.4 ★★★ `entity_touch` 被桥**拒绝**（第 18–20 行）

> The bridge **still refuses `entity_touch`**, so none of this is done here:
> **`setloot` registers what is in a crate, and the server does the range test, the
> prompt and the grant.** See **`ServerCore::driveCursorHints` /
> `processLootCommittedCommand`**.

★★★ **⇒ 架构边界（重要）：**
```
Lua 侧：setloot      只**登记**箱子里有什么
        ↓
桥：   ★ 拒绝 entity_touch（不允许 Lua 碰触事件）
        ↓
服务端：范围判定 + 提示 + 授予
        实现：ServerCore::driveCursorHints / processLootCommittedCommand
```

★★★ **⇒ 新的原生 API：`setloot`。**

★★ **⇒ 这是"Lua 声明数据、C++ 执行动作"的**流派** ——
比 Lua 直接操纵世界更安全。**

### 2.5 ★★ "WHAT THIS DOES NOT DO YET"（第 22–26 行）

> * **the circle is not drawn.** `fx_dmz_cylinder` and `fx_dmz_intersect_ring` are in
>   the band, so **the geometry is a model rather than custom rendering**, but
>   **nothing shrinks or damages yet.**
> * a picked-up gun **replaces the last one rather than filling a second slot**,

★★ **⇒ 作者**主动列出未实现项**，防止读者"读出比实际更多的东西"：**
```
-- WHAT THIS DOES NOT DO YET, so nobody reads more into it than is here:
```

★★★ **⇒ 这是**诚实标注**的典范（与 `conf.lua` 的 "RECONSTRUCTION BOUNDARY" 同类）。**

---

## 三、★★★★ 累计的 Lua → 原生 API 全表（报告 009 更新）

### `function:*`（全局函数）

```
function:setmapgameobjects    (gt, obj1, obj2, ...)     cha 1个 / sd 3个
function:getentarray          (value, key) → array      ★ 本报告
```

### `method:*`（对象方法）

```
method:issameteam
method:finishplayerdamage
method:finishsharedplayerdamage
method:addscore
method:addteamscore
method:addkill
method:addxp
method:respawn
method:isbot
method:sendservercommand      (player, command)         ★ 本报告
```

### 配置/工具

```
setloot                       ★ 登记箱内容（dmz）
OLMOD_DUMP_MODEL_BAND=1       ★ 导出 model band（283 项）
```

---

## 四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | 战役关卡 | **Wetwork / "Unidentified"** |
| 2 | 返回表消费者 | `SV_LoadMapScriptMetadata`（**一次**） |
| 3 | ★ 战役地图限制 | **无 `minimap_corner` 对** ⇒ 禁声明 `compass_map_cargoship` |
| 4 | 小地图切换 | `compass_map_cargoship` / `_2`（阶段边界） |
| 5 | ★★★ 七个阶段名 | bridge / deck / quarters / hallways / cargo holds / sinking escape / helicopter extraction |
| 6 | ★★ 权威源 | **`MapEnts`**（不从录制抄坐标） |
| 7 | 空环境守卫 | `if codol == nil then return {} end` |
| 8 | ★ 新 API | `function:getentarray` |
| 9 | ★★ 新 API | `method:sendservercommand` |
| 10 | ★★★ dmz 身份 | **BattleCity / Brave Games / battle royale** |
| 11 | ★★★ **被剥的是逻辑** | **"Only the script that places them is gone"** |
| 12 | model band 项数 | **283**（`OLMOD_DUMP_MODEL_BAND=1`） |
| 13 | band 内容 | pickup set / parachute / care-package pod / play-area cylinder |
| 14 | ★ 拾取语义 | PRESS-USE（`cursorHint` 0→1 + `cursorHintEntIndex`） |
| 15 | ★★★ 桥拒绝 | **`entity_touch`** |
| 16 | ★ 新 API | `setloot` |
| 17 | 服务端实现 | `ServerCore::driveCursorHints` / `processLootCommittedCommand` |
| 18 | 圆环几何 | `fx_dmz_cylinder` / `fx_dmz_intersect_ring`（**模型**非自绘） |

---

## 五、结论

### 1. ★★★★★ 交付项目的**本质**已由作者自己定义

> **"The ASSETS survived the strip... Only the script that places them is gone."**
> **"WHAT IS ACTUALLY MISSING IS SMALLER THAN IT LOOKS."**

★★★ **⇒ 整个 ol-mod/TESTOL 工程是"**把出版商删掉的脚本放回去**"。**
**资产（模型/数据/cvar）都在客户端里，缺的是把它们**串起来的逻辑**。**

★ **⇒ 这也解释了为什么包里**没有游戏本体**（`README §5` 说不含 `.ff/.ifs`）——
**本体在客户端，包里只有**放回去的脚本**。**

### 2. ★★★ 架构有一条**明确的边界**：桥拒绝 `entity_touch`

```
Lua  →  只声明（setloot / setmapgameobjects / getentarray）
C++  →  执行（范围判定 / 提示 / 授予 / 光标提示）
```

### 3. ★★★ "model band" 是跨两个项目反复出现的关键概念

```
报告 008：zm.lua 的"僵尸在线但不可见"（band 里 index 308 空）
报告 009：dmz.lua 的 model band 有 283 项（资产在）
记忆：    我们项目"实体段发了但看不到"（model_index 恒 0）
```

★★★ **⇒ 三处同源：**实体的可见性取决于 model band / configstring band 是否含该 index。****

### 4. ★★★ 累计**五处"副本失真"** + 两处"完全缺失"

```
完全缺失：conf.lua / war.lua       ⇒ 整局无分
副本失真：coop.lua（陈旧 dm 副本）  ⇒ 战役每死加 FFA 分
          zm.lua（逐字节 dm 副本）  ⇒ 合作按 FFA 计分
          dmz.lua（逐字节 dm 副本） ⇒ 大逃杀玩成死斗
          td/zarena/zhunt（仍是）   ⇒ 不调 addteamscore / 打印 dm / 重生 3000≠1500
```

★★★ **⇒ 这是**整包最系统性的缺陷类**：**gametype 脚本总被 `dm.lua` 顶替。****

### 5. ★★ 作者的三重自我约束（值得记录）

```
① FAIL-SOFT      ：回调体必须 pcall，失败只打印
② RECONSTRUCTION BOUNDARY：明确标出"未实现"
③ "WHAT THIS DOES NOT DO YET"：主动列出缺口
```

---

## 六、下一步

- `cha.lua` 行 175–末尾 / `zm.lua` 行 28+ / `maps\` 其余
- 包根 `README.md` / `BUILD.md` / `preflight.ps1` / `deploy.ps1` / `run.cmd` 逐字节
- ★★ **全量核对 `MANIFEST.sha256`**（`Get-FileHash` 被分类器拦截，待恢复）
- ★ **清理我上次留下的 6 个 `.bak` 文件**（已确认仍在）
