# 学习报告 080（重开）— `coop_training_mp_cargoship.lua`（4,683 行 / 全包最大 Lua）

**学习范围**：`maps\coop_training_mp_cargoship.lua` 全文结构 + 关键段（1–130 / 929–990 / 2112–2156 / 2441–2500 / 3419–3480 / 4325–4404 / 4483–4683）
**性质**：全实测（**87 个函数 / 62 个 API / 31 个数据表全部清点**）
**★★★★★ 本报告收录**完整的 22 阶段任务路线**、**录像回放引擎的完整机制**、**船体倾斜（沉船）系统**、**演员槽位的精确划分**

---

## 一、★★★★★ 文件身份：**地图脚本**（不是 gametype 脚本）

### 1.1 文件头（第 1–16 行，逐字）

```lua
-- Wetwork / "Unidentified".
--
-- The returned table is consumed once by SV_LoadMapScriptMetadata before the
-- gameplay source is assembled. This campaign map has no MP-style
-- `minimap_corner` pair, so declaring compass_map_cargoship here would make the
-- existing square minimap setup reject the map. The mission controller will
-- switch compass_map_cargoship / compass_map_cargoship_2 at the measured phase
-- boundaries instead.
--
-- Mission progression is map driven. The shipped MapEnts already names every
-- major phase (bridge, deck, quarters, hallways, cargo holds, sinking escape,
-- and helicopter extraction); the server keeps those records authoritative
-- rather than copying positions out of the recording.
if codol == nil then
    return {}
end
```

### ★★★★★ 任务身份

| 项 | 值 |
|---|---|
| **关卡名** | ★ **Wetwork**（"**Unidentified**"） |
| **类型** | **战役关卡**（不是多人模式） |
| **载体** | **地图脚本**（`maps\<map>.lua`） |
| **返回表消费者** | ★★★ **`SV_LoadMapScriptMetadata`**（**在 gameplay source 组装之前,只消费一次**） |

### ★★★★★ **为什么 `return {}` 是空的**（逐字）

```
"This campaign map has **no MP-style `minimap_corner` pair**,
 so **declaring `compass_map_cargoship` here would make the existing
 square minimap setup REJECT the map**."
        ↓
★★★ ⇒ 返回空表是**故意的** ⇒ 让方形小地图设置**接受**这张地图
        ↓
★ 而任务控制器会在**测得的阶段边界**切换
  `compass_map_cargoship` / `compass_map_cargoship_2`
```

★ **⇒ 这是**又一个"故意返回空"的实例**（与报告 076 的 `coop.lua` "有意无处理器"同类）。**

### ★★★ 数据权威性声明（逐字）

```
"Mission progression is **map driven**.
 The shipped **MapEnts** already names every major phase
 (bridge, deck, quarters, hallways, cargo holds, sinking escape, and helicopter extraction);
 the server keeps **those records authoritative** rather than
 **copying positions out of the recording**."
```

★★ **⇒ 即：**MapEnts 是权威,录像只是参考**（不是把录像坐标抄出来）。**

★ **⇒ 六个主要阶段名（逐字）：`bridge` / `deck` / `quarters` / `hallways` / `cargo holds` /
`sinking escape` / `helicopter extraction`。****

### 1.2 ★★★ 规模

| 项 | 值 |
|---|---|
| **行数** | **4,683** |
| **函数数** | ★ **87 个 `local function`** |
| **API 调用种类** | ★★ **62 个**（14 个 `function:` + 48 个 `method:`） |
| **数据表** | ★ **31 个顶层表** |

---

## 二、★★★★★ **完整的 22 阶段任务路线**（第 2112–2139 行，逐字）

```lua
local route = {
    phase("bridge_standoff", "start_bridge_standoff", "targetname"),
    phase("hallways_breach", "hallways_ready_to_breach", "script_flag"),
    phase("hallways_enter", "hallways_enter", "script_flag"),
    phase("cargohold_flash", "cargohold1_flashmoment", "script_flag"),
    phase("cargohold_one", "cargoholds_1_enter", "script_flag"),
    phase("cargohold_breach", "cargohold_breach_flag", "script_flag"),
    phase("cargohold_two", "cargohold2_combat", "script_flag"),
    phase("cargohold_open", "cargohold_cargo_open", "script_flag"),
    phase("sinking", "force_explosion_start", "script_flag"),
    phase("escape_laststand", "cargohold_laststand_breach_start", "script_flag"),
    phase("escape_stairs", "escape_cargohold_stairstop_flag", "script_flag"),
    phase("escape_tilt", "escape_tilt_30", "script_flag"),
    phase("escape_hull_break", "hull_break_first", "script_flag"),
    phase("escape_jump", "cargohold_jump_flag", "script_flag"),
    phase("escape_hull_break_second", "hull_break_second", "script_flag"),
    phase("escape_hold_one", "escape_hallway_lower_enter", "script_flag"),
    phase("escape_lower_hall", "escape_hallway_lower_flag", "script_flag"),
    phase("escape_flood", "escape_hallway_lower_flood", "script_flag"),
    phase("escape_deck_one", "escape_deck1_flag", "script_flag"),
    phase("escape_deck_two", "escape_deck2_flag", "script_flag"),
    phase("escape_seaknight", "escape_seaknight_flag", "script_flag"),
    phase("extraction_jump", "escape_player_jump", "targetname"),
}
```

### ★★★★★ 完整的 22 阶段表

| # | **阶段名** | **触发点名** | **键类型** |
|---|---|---|---|
| **1** | `bridge_standoff` | `start_bridge_standoff` | ★ **`targetname`** |
| **2** | `hallways_breach` | `hallways_ready_to_breach` | `script_flag` |
| **3** | `hallways_enter` | `hallways_enter` | `script_flag` |
| **4** | `cargohold_flash` | `cargohold1_flashmoment` | `script_flag` |
| **5** | `cargohold_one` | `cargoholds_1_enter` | `script_flag` |
| **6** | `cargohold_breach` | `cargohold_breach_flag` | `script_flag` |
| **7** | `cargohold_two` | `cargohold2_combat` | `script_flag` |
| **8** | `cargohold_open` | `cargohold_cargo_open` | `script_flag` |
| **9** | ★★ **`sinking`** | ★ **`force_explosion_start`** | `script_flag` |
| **10** | `escape_laststand` | `cargohold_laststand_breach_start` | `script_flag` |
| **11** | `escape_stairs` | `escape_cargohold_stairstop_flag` | `script_flag` |
| **12** | `escape_tilt` | `escape_tilt_30` | `script_flag` |
| **13** | `escape_hull_break` | `hull_break_first` | `script_flag` |
| **14** | `escape_jump` | `cargohold_jump_flag` | `script_flag` |
| **15** | `escape_hull_break_second` | `hull_break_second` | `script_flag` |
| **16** | `escape_hold_one` | `escape_hallway_lower_enter` | `script_flag` |
| **17** | `escape_lower_hall` | `escape_hallway_lower_flag` | `script_flag` |
| **18** | `escape_flood` | `escape_hallway_lower_flood` | `script_flag` |
| **19** | `escape_deck_one` | `escape_deck1_flag` | `script_flag` |
| **20** | `escape_deck_two` | `escape_deck2_flag` | `script_flag` |
| **21** | `escape_seaknight` | `escape_seaknight_flag` | `script_flag` |
| **22** | `extraction_jump` | `escape_player_jump` | ★ **`targetname`** |

★★★ **⇒ 只有**首尾两阶段**用 `targetname`,中间 20 个全用 `script_flag`。**

★ **⇒ 结构清晰：1 个开场 + 3 个走廊 + 5 个货舱 + 1 个沉船转折 + 11 个逃生 + 1 个登机。**

### ★★★ `phase()` 的实现（第 28–33 行）

```lua
local function phase(name, value, key)
    return {
        name = name,
        triggers = entities(value, key),
    }
end
```

★ **⇒ 每阶段把触发点**一次性解析成实体数组**（`getentarray(value, key)`）。**

### ★★★ 阶段推进的实现（第 4501–4528 行）

```lua
local function run_route(player)
    print("wetwork mission route started", #route)
    for index, entry in ipairs(route) do
        if #entry.triggers == 0 then
            print("wetwork mission trigger missing", entry.name)
            return
        else
            while not touches_any(entry.triggers, player) do
                codol.wait(50)
            end
        end
        mission_phase = index
        print("wetwork mission phase", index, entry.name)
        apply_phase_presentation(player, entry.name)
        local _, checkpoint_message, checkpoint_code = codol.call(
            "method:savecheckpoint", player)
        ...
        -- Always yield at a boundary. Adjacent and overlapping volumes must not
        -- collapse into several phase changes in one server frame.
        codol.wait(0)
    end
    print("wetwork mission route complete", mission_phase)
    finish_mission(player)
end
```

★★★ **⇒ 每阶段两件事：**
```
① `apply_phase_presentation(player, phase_name)`  ⇒ **表现层**
② ★★ `method:savecheckpoint(player)`             ⇒ **存档点**（每阶段一个！）
        ↓
★★★ 且 **`codol.wait(0)` 强制让出**
   —— 理由（逐字）："Adjacent and overlapping volumes must not
    **collapse into several phase changes in one server frame**."
```

★ **⇒ 第 ③ 条是**防止同一帧内跨多阶段**的关键机制**（与报告 068 的 `zm.lua` 的 director tick 同类问题）。**

★★ **⇒ 轮询间隔 **50 ms**。**

---

## 三、★★★★★ **录像回放机制**：所有时间都是 CODREF 出来的

### 3.1 ★★★ 出处引用格式

```
CODREF(demo **187200..203850**)      ⇒ 录像的毫秒区间
CODREF(demo **221200..271050**)
CODREF(demo **11050**)
CODREF(C-2021-7-25[22-11-33]**coop.demo, 14800..16700**)
CODREF(**MapEnts**)
CODREF(demo **agentState field 13** + centered ET_ACTOR births)
```

★★★ **⇒ 四种出处：录像区间 / MapEnts / agentState 字段 / 具体 demo 名。**

### 3.2 ★★★★★ 三个**精确到毫秒**的例子

```lua
-- ① 音效交接（第 4330–4335 行）
if phase_name == "bridge_standoff" then
    -- Retail leaves the start point immediately on the authored helicopter
    -- sequence. This sound handoff is fixed inside that sequence:
    -- 181950 - 10950 = 171000 ms.
    codol.wait(171000)
    set_ambient("ambient_cargoship_ext", 100)
```

```
★★★ **181950 - 10950 = 171000 ms** ⇒ 算式直接写在注释里
        ↓
★ 且**实测：181950 - 10950 = 171000** ✓ **算术正确**
```

```lua
-- ② 走廊进入（第 4378–4384 行）
send_command(player, "s cg_miniMapHide \"0\"")
send_command(player, "s cg_weaponBarHide \"0\"")
-- The player crosses hallways_enter at 204050; the sound environment
-- and ambient configstring change three ticks later at 204350.
codol.wait(300)
send_command(player, "o 1 \"stonecorridor\" 0.9 0.3 2")
set_ambient("ambient_cargoship_int", 800)
```

```
★★★ **204050 → 204350** = **三 tick（300 ms）**
```

```lua
-- ③ 门口列队（第 4344–4346 行）
-- CODREF(demo 187200..203850): the squad stacks at the door for
-- 16.65 seconds. Preserve the exact weapon/animation handoffs during
-- that locked sequence, then begin the indoor grade.
```

```
★★★ **16.65 秒**的门口列队
```

★★ **⇒ 第 ③ 条的 16.65 s 与后面的一串 `codol.wait` 之和应对得上：**
```
3350 + 300 + 400 + 1150 + 1000 + 4250 + 600 + 100 + 3050 + 500 + 1150 + 800
= **16,650 ms** = **16.65 s** ✓
```
★★★★★ **⇒ 逐项相加**精确等于**注释里的 16.65 秒 ⇒ 数据自洽。**

### 3.3 ★★★★★ **控制台命令字符串**（`send_command`）

```lua
local function send_command(player, command)
    local _, message, code = codol.call(
        "method:sendservercommand", player, command)
    if message ~= nil then
        print("wetwork command failed", command, message, code)
        return false
    end
    return true
end
```

★★★ **⇒ `method:sendservercommand(player, <命令字符串>)` —— 服务端给客户端发一条控制台命令。**

### ★★★★★ 实测用到的**六种命令前缀**

| 前缀 | 例子 | 含义（推断） |
|---|---|---|
| **`s`** | `s 0194 ""` / `s cg_miniMapHide "0"` / `s pve_set_activated_info ""` / `s ui_match_complete "1"` | ★ **set cvar** |
| **`w`** | `w 0 10 0` | ★ **weapon / 武器槽** |
| **`u`** | `u 8` / `u 9` | ★★ **UI 动词**（`dm.lua` 提到 `u 10` = 死亡屏、`u 11` = 活着） |
| **`o`** | `o 1 "stonecorridor" 0.9 0.3 2` | ★ **音效环境** |
| **`n`** | `n 0.010000 2000` / `n 1.000000 500` | ★ **淡入淡出（时间, 时长）** |
| **`i`** | `i 3000 6.000000 0 1` | ★ **图像/过场效果** |

★★★ **⇒ `dm.lua` 注释里的 `u 10`（死亡屏）/ `u 11`（活着）现在有了同族证据：**
**`u 8` / `u 9` 在这份录像里成对出现（武器切换动画）。****

★ **⇒ `s 0194 ""` 重复出现多次**（`0194` 是一个**裸数字 cvar**，与报告 077 的 `1224=90` 同类）。**

★★ **⇒ `s pve_set_activated_info ""` 出现 **10 次**以上 ⇒ 一条被反复"清空"的 PvE 提示。****

---

## 四、★★★★★ **演员槽位的精确划分**（第 975–982 / 3419–3430 行，逐字）

```lua
-- Slots 6..10 are the five persistent squad members. Retail begins hostile
-- allocation at 13 because 0..5 hold the lead Blackhawk passengers and 11..12
-- hold its pilots. Those cinematic slots return to the common actor pool at
-- their measured removal frames.
local enemy_slot_available = {}
for slot = 13, 23 do
    enemy_slot_available[slot] = true
end
```

### ★★★★★ 完整的槽位划分（0–23）

| 槽位 | 用途 | 数量 |
|---|---|---|
| **0 – 5** | ★★ **领航 Blackhawk 的乘客** | **6** |
| **6 – 10** | ★★★ **五个常驻小队成员**（persistent squad） | **5** |
| **11 – 12** | ★★ **Blackhawk 飞行员** | **2** |
| **13 – 23** | ★★★ **敌方分配池** | **11** |

★★★ **⇒ 24 个槽位（0–23）全部分配,其中**11 个可动态给敌人**。**

★ **⇒ 与报告 071 的 `zm.lua` 记录呼应：**
```
`zm.lua`：`ACTOR_SLOT_CAP = 32`（IDA 的 `sub_471980` 确认 **5 位 / 32 槽**）
        ↓
★ 本文件用的是 **0..23**（24 个）⇒ 32 槽里的**子集**
```

★★ **⇒ 且明确"Those cinematic slots **return to the common actor pool** at
their measured removal frames" ⇒ 电影槽位是**可回收**的。****

### ★★★ `acquire_enemy_slot` 的实现（第 3419–3430 行）

```lua
local function acquire_enemy_slot()
    while true do
        for slot = 0, 23 do
            if enemy_slot_available[slot] == true and
                    enemy_slot_in_use[slot] == nil then
                enemy_slot_in_use[slot] = true
                return slot
            end
        end
        codol.wait(50)
    end
end
```

★★★ **⇒ 扫描 **0..23**（全 24 槽,不只 13..23）,取第一个既"可用"又"未占用"的槽。**
**⇒ 若无 ⇒ **等 50 ms 重试**（无限循环）。**

★★ **⇒ 两个表分工：`enemy_slot_available`（允许用）与 `enemy_slot_in_use`（正占用）。**

### ★★★ `coop.demo` 的槽位证据（第 2155–2156 行，逐字）

```lua
-- CODREF(C-2021-7-25[22-11-33]coop.demo, 14800..16700): the
-- shipping snapshot starts six extraction allies in slots 0..5, the persistent
```

★★ **⇒ 出处：**`C-2021-7-25[22-11-33]coop.demo`**，区间 **14800..16700**。**
**⇒ 印证槽位 0..5 = **六个**撤离友军。****

---

## 五、★★★★★ **船体倾斜（沉船）系统**（第 929–971 行，逐字）

```lua
local function run_sinking_ground_tilt_track(player)
    local controller = nil
    local elapsed = 0
    for index, entry in ipairs(sinking_ground_tilt_track) do
        codol.wait(entry[1] - elapsed)
        elapsed = entry[1]
        if controller == nil then
            controller = codol.call("function:spawngroundtiltcontroller")
            if controller == nil then
                print("wetwork ground tilt controller spawn failed")
                return false
            end
        end
        local _, message, code = codol.call(
            "method:setgroundtilttrajectory", controller,
            entry[2], entry[3], entry[4],
            0.0, 0.0, entry[5], 0.0, 0.0, entry[6])
        if message ~= nil then
            print("wetwork ground tilt trajectory failed", index, message, code)
            codol.call("method:playersetgroundreferenceent", player)
            codol.call("method:delete", controller)
            return false
        end
        if index == 1 then
            -- The trajectory begins at +5100; retail selects the entity 550 ms
            -- later, on the first player snapshot that carries field 231 = 100.
            codol.wait(550)
            elapsed = elapsed + 550
            _, message, code = codol.call(
                "method:playersetgroundreferenceent", player, controller)
            ...
        end
    end

    codol.wait(77300 - elapsed)
    codol.call("method:playersetgroundreferenceent", player)
    codol.call("method:delete", controller)
    return true
end
```

### ★★★★★ 三个新 API

| # | API | 作用 |
|---|---|---|
| **1** | **`function:spawngroundtiltcontroller`** | ★★ **生成地面倾斜控制器** |
| **2** | **`method:setgroundtilttrajectory(ctrl, v2,v3,v4, 0,0,v5, 0,0,v6)`** | ★★★ **设置倾斜轨迹**（**10 个数值参数**） |
| **3** | **`method:playersetgroundreferenceent(player[, ctrl])`** | ★★★ **把玩家的"地面参考实体"绑到控制器** |

### ★★★★★ 三个精确事实

```
① ★★★ **轨迹从 +5100 开始**,而 retail **550 ms 后**才选实体
   —— 判据：**"the first player snapshot that carries field 231 = 100"**
        ↓
★★★ ⇒ **`field 231 = 100`** 是一个 **playerState 快照字段条件**
   （★ 231 > 63 ⇒ 不在 entityState 的 63 字段表里 ⇒ 属 **playerState**）
        ↓
② ★★★ **整条轨道长度 = `77300 - elapsed`** ⇒ 总计 **77.3 秒**
        ↓
③ ★★★ **解绑写法：`playersetgroundreferenceent(player)` 只传 player**
   （**没有第二个参数 = 解除绑定**）
        ↓
★ 失败路径也解绑 + `method:delete(controller)` ⇒ **不变量：出错必解绑,不留悬空引用**
```

★ **⇒ 第 ③ 条是一个**"可选第二参数 = 绑定/解绑"**的 API 设计**。**

★★ **⇒ 第 ② 条的 77.3 秒 = 沉船过程的总时长。**

---

## 六、★★★★★ **`publish_vehicle_target`：配置串的车辆目标环**（第 2441–2482 行，逐字）

```lua
local function publish_vehicle_target(actor, entity_number, spawner)
    if not intro_vehicle_targets_active or
            codol.call("method:getmapfield", spawner, "script_noteworthy") ~=
                "chopper_deck_enemies" then
        return
    end
    assert(codol.thread(function()
        codol.wait(1000)
        if not intro_vehicle_targets_active or
                enemy_alive_by_entity[entity_number] ~= true then
            return
        end
        local config_index = nil
        for candidate = 792, 805 do
            if vehicle_target_entity_by_slot[candidate] == nil then
                config_index = candidate
                break
            end
        end
        if config_index == nil then
            print("wetwork vehicle target ring full", entity_number)
            return
        end
        vehicle_target_slot_by_entity[entity_number] = config_index
        vehicle_target_entity_by_slot[config_index] = entity_number
        local inactive_flags = 0
        if config_index == 798 then
            inactive_flags = 304
        elseif config_index >= 799 then
            inactive_flags = 288
        end
        local prefix = "\\ent\\" .. tostring(entity_number) ..
            "\\offs\\0 0 32\\offmat\\-1"
        set_config_string(
            config_index,
            prefix .. "\\mat\\-1\\flags\\" .. tostring(inactive_flags))
        set_config_string(
            config_index,
            prefix .. "\\mat\\188\\flags\\" ..
                tostring(inactive_flags + 8))
    end))
end
```

### ★★★★★ 完整的机制

```
① 双重门控：`intro_vehicle_targets_active` **且**
   `getmapfield(spawner, "script_noteworthy") == "chopper_deck_enemies"`
        ↓
② 开线程,先 **等 1000 ms**
        ↓
③ 再查一次门控（`enemy_alive_by_entity[entity_number] == true`）
        ↓
★★★ ④ 在 **configstring 792..805**（★ **14 个槽的"环"**）里找空位
   ⇒ 满则打印 **"wetwork vehicle target ring full"**
        ↓
★★★ ⑤ 写两条 configstring：
   格式：`\ent\<实体号>\offs\0 0 32\offmat\-1\mat\-1\flags\<inactive_flags>`
         `\ent\<实体号>\offs\0 0 32\offmat\-1\mat\188\flags\<inactive_flags+8>`
```

### ★★★★★ 四个精确值

| # | 项 | 值 |
|---|---|---|
| **1** | ★★ **车辆目标配置串区间** | **792 – 805**（**14 个槽**） |
| **2** | 偏移 | **`\offs\0 0 32`**（**向上 32 单位**） |
| **3** | ★★★ 两个材质 | **`\mat\-1`** 与 **`\mat\188`** |
| **4** | ★★★ `inactive_flags` | **798 → 304**；**≥799 → 288**；**否则 0** |

★★★ **⇒ 第 4 条是一个**按槽位分段的标志值**（798 与 799+ 不同）。**
**⇒ 且第二条 CS 的 flags 是 `inactive_flags + 8` ⇒ **8 是"激活"位**。****

★ **⇒ `set_config_string(index, value)` = `function:setconfigstring`（第 141–149 行）。**

★★ **⇒ `\ent\ / \offs\ / \offmat\ / \mat\ / \flags\` 是**反斜杠分隔的键值串格式**（与报告 077 的 `MarketplaceSkus` 无关,是引擎 CS 的惯例）。**

★ **⇒ 门控字符串 **`"chopper_deck_enemies"`** 是一个 `script_noteworthy` ⇒ 与报告 070 的 `"zombie_spawner"` **同类用法**。****

---

## 七、★★★★★ **敌方武器与附着**（第 2413 / 2487–2517 / 3432–3460 行）

### 7.1 ★★★ 轮转模式

```lua
local enemy_weapon_pattern = { 479, 479, 480, 481, 480, 479, 479, 480 }
local enemy_weapon_pattern_index = 1
```

★★ **⇒ 8 项轮转（479 出现 4 次、480 出现 3 次、481 出现 1 次）。**

### 7.2 ★★★★★ **`enemy_attachment_by_spawner`（43 项）**

```lua
-- CODREF(demo agentState field 13 + centered ET_ACTOR births): these 43 MapEnt
-- spawners account for all 47 births that can be joined unambiguously in the
-- recorded run. The value selects the exact third-person carried weapon model.
local enemy_attachment_by_spawner = {
    [64] = 479, [65] = 479, [66] = 480, [67] = 481,
    [68] = 480, [69] = 479, [70] = 479, [71] = 480,
    [83] = 463, [99] = 482, [100] = 481, [111] = 479,
    [114] = 482, [115] = 481, [119] = 481, [120] = 479,
    [121] = 480, [134] = 481, [135] = 480, [136] = 463,
    [137] = 482, [138] = 482, [139] = 480, [147] = 480,
    [148] = 482, [149] = 482, [152] = 463, [153] = 480,
    [154] = 479, [168] = 463, [169] = 463, [224] = 481,
    [346] = 482, [347] = 482, [348] = 479, [349] = 480,
    [350] = 482, [351] = 481, [352] = 481, [353] = 482,
    [441] = 484, [442] = 480, [443] = 466,
}
```

### ★★★★★ 三个精确事实

```
① ★★★ **43 个 MapEnt spawner** 覆盖录像里 **47 个**"可无歧义接入"的出生
   ⇒ 出处：**demo 的 `agentState` 字段 13 + 居中 ET_ACTOR 出生**
        ↓
② ★★★ 值 = **第三人称手持武器模型**的索引
   用到 7 个值：**463 / 466 / 479 / 480 / 481 / 482 / 484**
        ↓
③ ★ 实体号分布：**64–71**（连续 8 个）/ 83 / 99–100 / 111 / **114–121** /
   **134–139** / 147–149 / 152–154 / 168–169 / 224 / **346–353** / 441–443
```

★★ **⇒ 第 ③ 条：实体号**不连续**,但呈**簇状**（64–71、134–139、346–353 各 6–8 个）。**

### ★★★ `enemy_attachment` 的三级回退（第 3432–3450 行）

```lua
local function enemy_attachment(spawner, classname)
    local spawner_number = codol.call("method:getentitynumber", spawner)
    local recorded = enemy_attachment_by_spawner[spawner_number]
    if recorded ~= nil then
        return recorded
    end
    if string.find(classname, "_rpg_", 1, true) ~= nil then
        return 463
    end
    if string.find(classname, "_ump_", 1, true) ~= nil then
        return 466
    end
    local attachment = enemy_weapon_pattern[enemy_weapon_pattern_index]
    enemy_weapon_pattern_index = enemy_weapon_pattern_index + 1
    if enemy_weapon_pattern_index > #enemy_weapon_pattern then
        enemy_weapon_pattern_index = 1
    end
    return attachment
end
```

```
★★★ 三级回退：
① **录像表里有** ⇒ 用它（权威）
② classname 含 **`_rpg_`** ⇒ **463**
③ classname 含 **`_ump_`** ⇒ **466**
④ 都没有 ⇒ **8 项轮转模式**
```

★ **⇒ `string.find(classname, "_rpg_", 1, true)` 的第 4 个参数 `true` = **纯文本匹配**（不解释 pattern）。**
**⇒ 这是 Lua 里正确匹配含下划线字面量的写法。**

### ★★★★★ `enemy_weapon_name` 与 **RPG 未实现**（第 3452–3460 行，逐字）

```lua
local function enemy_weapon_name(classname)
    if string.find(classname, "_ump_", 1, true) ~= nil then
        return "ump45_mp"
    end
    -- Explosive projectiles remain a separate restoration pass. Until that
    -- native path is ready, RPG spawners retain their recorded third-person
    -- attachment while using the mission's ordinary rifle damage owner.
    return "ak47_mp"
end
```

★★★★★ **⇒ 又一个明确的"未实现"声明：**
```
"**Explosive projectiles remain a separate restoration pass.**
 Until that native path is ready, RPG spawners **retain their recorded
 third-person attachment** while **using the mission's ordinary rifle damage owner**."
        ↓
★★★ ⇒ 敌人手里的 RPG **看起来是 RPG,但打出来的伤害是步枪的**（`ak47_mp`）
```

★ **⇒ 这是**"视觉与行为分离"的临时折中**（与报告 073 的 `dmz.lua` 边界声明同类）。**

---

## 八、★★★★★ **武器索引重映射表**（第 45–82 行）

```lua
local campaign_weapon_definitions = {
    [1192] = "** 854 0 0 6747 9321 6825",
    [1195] = "** 730 0 0 9930 6747 9321 6690 6825",
    [1197] = "** 992 0 0 6206 9321",
    [1198] = "** 78 0 0 9930 2795 2592 6747 9321 6690 8738 6825",
    [1201] = "** 1106 0 0 6945 9321 6747 6825",
    [1203] = "** 1155 0 0",
    [1208] = "** 41 0 0 9930 1676 6690 8738 6747 9321 10545",
    [1211] = "** 41 0 0 9930 4170 6690 8738 6747 9321 10545",
    [1212] = "** 22 0 0 15297 652 5414 6690 8738 9321 6747",
}
```

### ★★★★★ 完整的九项重映射表

| 录像索引 | 定义串（`**` 前缀 + 数字序列） |
|---|---|
| **1192** | `** 854 0 0 6747 9321 6825` |
| **1195** | `** 730 0 0 9930 6747 9321 6690 6825` |
| **1197** | `** 992 0 0 6206 9321` |
| **1198** | `** 78 0 0 9930 2795 2592 6747 9321 6690 8738 6825` |
| **1201** | `** 1106 0 0 6945 9321 6747 6825` |
| **1203** | `** 1155 0 0` |
| **1208** | `** 41 0 0 9930 1676 6690 8738 6747 9321 10545` |
| **1211** | `** 41 0 0 9930 4170 6690 8738 6747 9321 10545` |
| **1212** | `** 22 0 0 15297 652 5414 6690 8738 9321 6747` |

### ★★★★★ 机制（第 59–82 行）

```lua
local function campaign_weapon_index(recorded_index)
    if recorded_index == 0 then return 0 end
    local definition = campaign_weapon_definitions[recorded_index]
    if definition == nil then return recorded_index end   -- ★ 无映射 ⇒ 原样返回
    local resolved = campaign_weapon_indexes[recorded_index]
    if resolved ~= nil then return resolved end            -- ★ 缓存
    local message, code
    resolved, message, code = codol.call("function:weaponindex", definition)
    if type(resolved) ~= "number" then
        print("wetwork weapon mapping failed", recorded_index, definition, message, code)
        return nil
    end
    campaign_weapon_indexes[recorded_index] = resolved       -- ★ 写回缓存
    print("wetwork weapon mapped", recorded_index, resolved, definition)
    return resolved
end
```

★★★ **⇒ 三级处理：**
```
① `recorded_index == 0` ⇒ 返回 **0**（空槽）
② 表里**没有** ⇒ **原样返回**（不做映射）
③ 表里有 ⇒ `codol.call("function:weaponindex", <定义串>)` 解析成**实时编号**
   ⇒ ★ **并缓存**（同一录像索引只解析一次）
   ⇒ ★ 非 number ⇒ 返回 **nil**（失败）
```

★★ **⇒ 关键：**录像里的武器索引 ≠ 本服务器的编号** ⇒ 必须经 `function:weaponindex` 翻译。**

★★★ **⇒ 与报告 073 的 `dmz.lua` 陷阱呼应：**
```
`dmz.lua`：cs 12506..12692 广播 1148..1211 是**零售回放**
本文件： 录像索引 **1192..1212** 需要**重映射**
        ↓
★★★ ⇒ 两者都是"**录像编号 ≠ 本服编号**"的同一类问题,
   但本文件**正确地做了重映射**,而 `dmz.lua` 曾踩坑（后修复）
```

★ **⇒ 注意 `[1211]` 与 `[1212]` 的定义串**前 5 项相同**（`** 41 0 0 9930`）,只有后面不同。**
**⇒ 而 `1211`/`1212` 正是 `hallways_enter` 阶段给玩家的主/副武器（第 4389 行）。**

★★ **⇒ 定义串的格式：`** <n> 0 0 <n...>` ⇒ `**` 可能是"多段定义"的分隔符。**

### ★★★ `set_campaign_weapons` 与 `setplayerweapons` 的**两个签名**（第 84–116 行）

```lua
local function set_campaign_weapons(
        player, primary, secondary, selected, supplemental)
    local mapped_primary = campaign_weapon_index(primary)
    ...
    if mapped_supplemental ~= nil then
        _, message, code = codol.call(
            "method:setplayerweapons", player,
            mapped_primary, mapped_secondary,
            mapped_supplemental, mapped_selected)     -- ★ 4 个武器参数
    else
        _, message, code = codol.call(
            "method:setplayerweapons", player,
            mapped_primary, mapped_secondary, mapped_selected)  -- ★ 3 个武器参数
    end
```

★★ **⇒ `method:setplayerweapons` 有**两种签名**（3 参 / 4 参,后者多一个 "supplemental"）。**
**⇒ 与报告 073 的 `dmz.lua` "服务器每人只持有一个 grant"呼应（supplemental = 第二个槽）。**

### ★★★ 弹药函数（第 118–131 行）

```lua
local function set_campaign_weapon_ammo(player, weapon, clip, reserve)
```
★★ **⇒ `method:setplayerweaponammo(player, weapon, clip, reserve)`。**

---

## 九、★★★★★ **任务完成与死亡处理**

### 9.1 ★★★★★ `finish_mission` 的精确时间（第 4483–4499 行，逐字）

```lua
local function finish_mission(player)
    -- MEASURED: success UI begins at 475600, the server decides the mission at
    -- 480850, and EXE_MATCHENDED follows at 481850. This 5250 ms hold belongs
    -- to Wetwork; the generic campaign end owner supplies the final one second.
    codol.call("method:setcandamage", player, false)
    send_command(player, "n 0.010000 2000")
    send_command(player, "s ui_match_complete \"1\"")
    send_command(player, "s ui_mission_success \"1\"")
    send_command(player, "s ui_skip_mission_success \"1\"")
    codol.wait(850)
    send_command(player, "i 3000 6.000000 0 1")
    codol.wait(4400)
    local _, message, code = codol.call("function:finishmission")
    if message ~= nil then
        print("wetwork mission completion failed", message, code)
    end
end
```

### ★★★★★ 四个精确时刻

| # | 事件 | 时刻（ms） |
|---|---|---|
| **1** | **成功 UI 开始** | **475600** |
| **2** | **服务端决定任务** | **480850** |
| **3** | ★★ **`EXE_MATCHENDED`** | **481850** |
| **4** | 归 Wetwork 的保持时长 | **5250 ms**（+ 通用结尾 1 秒） |

★★★ **⇒ 算术自洽：**`850 + 4400 = 5250`** ✓**
**⇒ 且 `481850 - 475600 = 6250` ms（成功 UI 到 MATCHENDED）。****

★ **⇒ `method:setcandamage(player, false)` ⇒ 先**关掉玩家受伤**（过场里不能被打死）。**

★★ **⇒ `function:finishmission` —— **无参数**的完成调用。**

### 9.2 ★★★ `player_killed` 与检查点重生（第 4566–4579 行，逐字）

```lua
assert(codol.on("player_killed", function(killed_player, event)
    if mission_started ~= true or killed_player == nil then
        return
    end
    -- The generic coop gametype deliberately owns no timed respawn. Wetwork
    -- restarts this player at the last route checkpoint while leaving the
    -- encounter and mission threads alive.
    send_command(killed_player, "n 0.010000 500")
    local _, message, code = codol.call(
        "method:respawn", killed_player, 2000)
```

★★★★★ **⇒ 与报告 076 的 `coop.lua` 注释**逐字呼应**：**
```
`coop.lua`（第 12–15 行）：
  "There is **deliberately no PvP score, kill, or timed-respawn handler here**. ...
   **Wetwork death and checkpoint restart are mission state transitions
   and will be owned by the cargoship map layer**."
        ↓
`coop_training_mp_cargoship.lua`（本文件）：
  "The generic coop gametype **deliberately owns no timed respawn**.
   **Wetwork restarts this player at the last route checkpoint**
   while leaving the encounter and mission threads alive."
        ↓
★★★★★ ⇒ **两处注释互相印证,分工明确** ✓
```

★ **⇒ 重生延迟 = **2000 ms**（★ 与 `cha`/`war`/`conf` 的 3000 不同,因为这是战役检查点重生）。**

★★ **⇒ 且强调"leaving the **encounter and mission threads alive**" ⇒ 重生**不重置任务进度**。**

### 9.3 ★★★★★ 三个**逃生死亡体积**（第 4671–4680 行）

```lua
for _, death_volume in ipairs({
        "escape_carghold1_flood_death",
        "escape_catwalk_death",
        "escape_hallway_lower_flood_death",
    }) do
    local current_death_volume = death_volume
    assert(codol.thread(function()
        run_escape_death_volume(player, current_death_volume)
    end))
end
```

### ★★★ 三个精确命名

| # | 死亡体积名 |
|---|---|
| **1** | **`escape_carghold1_flood_death`** |
| **2** | **`escape_catwalk_death`** |
| **3** | **`escape_hallway_lower_flood_death`** |

★★ **⇒ 两个是"淹死"（flood）,一个是"坠落"（catwalk）。**

★ **⇒ 且是**仅当"逃生"阶段才相关**（第 4537–4544 行的 CODREF 说明：
"these three brushes are named explicitly as flood/fall death volumes and
**become relevant only after `force_explosion_start`**"）⇒ 即阶段 9。**

### ★★★★★ `finishplayerdamage` 的 **11 个参数**（第 4548–4551 行）

```lua
local _, message, code = codol.call(
    "method:finishplayerdamage", player,
    nil, nil, 1000, 0, 16, 165,
    nil, { 0, 0, 1 }, 0, 0, 0)
```

★★★ **⇒ `method:finishplayerdamage(player, attacker, inflictor, damage, dflags, mod, weapon, direction, hitloc, ...)`：**
```
`nil`（attacker）/ `nil`（inflictor）/ **1000**（damage）/ **0**（dflags）
/ **16**（mod）/ **165**（weapon）/ `nil` / **`{0,0,1}`**（方向向量）/ 0 / 0 / 0
```

★★ **⇒ `{0,0,1}` = **竖直向下/向上**的方向。**

★ **⇒ `repeat ... until not touches_any(triggers, player)` ⇒ 一次进入只杀一次**
**（理由逐字："Re-arm only after the new life has left the brush so **one touch
cannot enqueue several deaths**"）。**

---

## 十、★★★★★ **启动时的 16+ 个线程**（第 4601–4681 行）

```lua
assert(codol.on("client_spawned", function(player, event)
    if mission_started then
        -- A checkpoint restart is a new player life, not a second mission intro.
        ...
        return
    end
    mission_started = true
    mission_player = player
    start_player_presentation(player)
    start_global_presentation()
    assert(codol.thread(function() run_intro_flight(player) end))
    assert(codol.thread(function() run_lead_blackhawk() end))
    assert(codol.thread(function() run_intro_enemy_track() end))
    assert(codol.thread(function() run_objective_track(player) end))
    assert(codol.thread(function() run_opening_command_track(player) end))
    assert(codol.thread(function() run_scripted_sound_track() end))
    assert(codol.thread(function() run_scripted_world_fx_track() end))
    assert(codol.thread(function() run_scripted_fire_magic_track() end))
    assert(codol.thread(function() run_scripted_radius_damage_track() end))
    assert(codol.thread(function() run_scripted_missile_track() end))
    assert(codol.thread(function() start_intro_cast(event.server_time) end))
    assert(codol.thread(function() run_ally_animation_track(event.server_time) end))
    assert(codol.thread(function() run_route(player) end))
    for _, encounter in ipairs(encounter_groups) do
        local current_encounter = encounter
        assert(codol.thread(function() run_encounter(current_encounter, player) end))
    end
    for _, death_volume in ipairs({ ... 3 个 ... }) do
        local current_death_volume = death_volume
        assert(codol.thread(function() run_escape_death_volume(player, current_death_volume) end))
    end
end))
```

### ★★★★★ 13 个固定线程 + 2 组循环线程

| # | 线程函数 |
|---|---|
| **1** | `run_intro_flight(player)` |
| **2** | `run_lead_blackhawk()` |
| **3** | `run_intro_enemy_track()` |
| **4** | `run_objective_track(player)` |
| **5** | `run_opening_command_track(player)` |
| **6** | `run_scripted_sound_track()` |
| **7** | `run_scripted_world_fx_track()` |
| **8** | ★ `run_scripted_fire_magic_track()` |
| **9** | `run_scripted_radius_damage_track()` |
| **10** | `run_scripted_missile_track()` |
| **11** | `start_intro_cast(event.server_time)` |
| **12** | `run_ally_animation_track(event.server_time)` |
| **13** | ★★ **`run_route(player)`**（任务主循环） |
| **N** | `run_encounter(encounter, player)` × **`#encounter_groups`** |
| **M** | `run_escape_death_volume(player, vol)` × **3** |

★★★ **⇒ 至少 **16 个并发 Lua 线程**。**

### ★★★ **Lua 闭包捕获惯用法**（第 4666 / 4676 行）

```lua
local current_encounter = encounter        -- ★ 必须在循环内复制
assert(codol.thread(function() run_encounter(current_encounter, player) end))
```

★★★ **⇒ `local current_encounter = encounter` 是**Lua 里必须的写法**：**
```
Lua 的 `for` 循环变量在**整个循环里是同一个变量**
        ↓
若直接闭包捕获 `encounter` ⇒ 所有线程看到的都是**最后一个值**
        ↓
★ 必须在循环体内 **`local` 复制一份** ⇒ 每个闭包捕获自己的副本
```

★ **⇒ 这是**Lua 闭包陷阱的经典写法**,两处都用了。****

### ★★★ `start_global_presentation`（第 4592–4599 行）

```lua
local function start_global_presentation()
    -- Admission configstrings are emitted by ServerCore at their recorded
    -- boundaries. The gameplay script owns only the later mission event.
    assert(codol.thread(function()
        codol.wait(5750)
        trigger_exploder(1, 150)
    end))
end
```

★★ **⇒ `5750 ms` 后触发爆炸器 `(1, 150)`。**

### ★★★ `start_player_presentation`（第 4581–4590 行）

```lua
local function start_player_presentation(player)
    -- CODREF(demo 11050): the first post-spawn playerState owns this pair and
    -- selects recorded weapon 1198. ...
    set_campaign_weapons(player, 1198, 1197, 1198)
    set_campaign_weapon_ammo(player, 1198, 30, 90)
    set_campaign_weapon_ammo(player, 1197, 15, 45)
end
```

★★★ **⇒ 开局武器：主 **1198** / 副 **1197** / 选中 **1198**；弹药 1198 = **30/90**、1197 = **15/45**。**
**⇒ 出处：demo **11050**。**

---

## 十一、★★★★★ **87 个函数的完整清单**（按职责分类）

### 11.1 基础工具（第 18–43 行）

| 行 | 函数 |
|---|---|
| **18** | `entities(value, key)` — `getentarray` |
| **28** | `phase(name, value, key)` |
| **35** | `send_command(player, command)` — `sendservercommand` |

### 11.2 武器系统（第 59–139 行）

`campaign_weapon_index` / `set_campaign_weapons` / `set_campaign_weapon_ammo` / `select_campaign_weapon`

### 11.3 世界表现基础（第 141–197 行）

`set_config_string` / `server_time` / `spawn_presentation_model` / `set_presentation_model` / `play_map_animation`

### 11.4 脚本化轨道（第 228–560 行）

`run_scripted_sound_track` / `run_scripted_world_fx_track` / `run_scripted_fire_magic_track` / `run_scripted_radius_damage_track` / `scripted_missile_call` / `run_scripted_missile_track` / `trigger_exploder` / `earthquake_at` / `physics_explosion_sphere_at`

### 11.5 视角与爆炸（第 832–920 行）

`interpolate_angle` / `blast_view_angles` / `run_sinking_exploder_track` / `run_sinking_earthquake_track` / `run_sinking_physics_explosion_track` / ★ `run_sinking_ground_tilt_track`

### 11.6 领航直升机（第 984–1037 / 1484–1592 行）

`release_enemy_slot` / `move_lead_blackhawk_occupants` / `remove_lead_blackhawk_occupants` / `run_lead_blackhawk` / `interpolate_intro_helicopter_yaw` / `intro_helicopter_transform` / `intro_occupant_transform` / `move_intro_occupants` / `restore_intro_squad_to_deck`

### 11.7 脚本化视角（第 1730–1903 行）

`set_scripted_position` / `set_scripted_view_angles` / `set_scripted_view_clamp` / `set_scripted_link_state` / `clear_scripted_position` / `set_shellshock` / `apply_objective` / `run_objective_track` / `run_opening_command_track` / `intro_scripted_view` / `run_intro_flight`

### 11.8 视觉与氛围（第 2068–2140 行）

`set_ambient` / `clear_ambient` / `set_vision` / `set_blast_vision` / `set_deck_vision` / `touches_any`

### 11.9 演员阵容（第 2162–2440 行）

`spawn_cast_member` / `first_entity` / `start_intro_cast` / `run_ally_animation_track` / `release_vehicle_target` / `publish_vehicle_target`

### 11.10 敌人系统（第 3419–4017 行）

`acquire_enemy_slot` / `enemy_attachment` / `enemy_weapon_name` / `squared_distance` / `run_enemy_ai` / `release_enemy_actor` / `run_recorded_enemy_path` / `run_enemy_goal` / `spawn_enemy` / `spawn_enemy_group` / `wait_for_started_groups_clear` / `run_encounter` / `retire_enemy_actor` / `retire_enemy_group` / `run_intro_enemy_track` / `run_sinking_enemy_blast` / `delete_targetname` / `run_blast_knockdown`

### 11.11 撤离与收尾（第 4085–4599 行）

`run_extraction_helicopter` / `run_extraction_flight` / `run_cargo_interaction` / `run_sinking_presentation` / `apply_phase_presentation` / `finish_mission` / `run_route` / `run_escape_death_volume` / `start_player_presentation` / `start_global_presentation`

---

## 十二、★★★★★ **31 个数据表的完整清单**

| 行 | 表名 | 性质 |
|---|---|---|
| 45 | `campaign_weapon_definitions` | 9 项武器重映射 |
| 206 | `scripted_sound_track` | 音效轨道 |
| 249 | `scripted_world_fx_track` | 世界特效轨道 |
| 313 | `scripted_radius_damage_track` | 范围伤害轨道 |
| 340 | `scripted_missile_track` | 导弹轨道 |
| 568 | `sinking_exploder_events` | 沉船爆炸器 |
| 602 | `sinking_earthquake_events` | 沉船地震 |
| 619 | `sinking_physics_explosion_events` | 沉船物理爆炸 |
| 632 | `blast_knockdown_player_path` | 冲击击倒路径 |
| 734 | `blast_knockdown_view_path` | 冲击视角路径 |
| 859 | `sinking_ground_tilt_track` | ★★ **船体倾斜轨道** |
| 988 | `lead_blackhawk_path` | 直升机路径 |
| 1001 | `lead_blackhawk_occupant_offsets` | 乘客偏移 |
| 1118 | `intro_player_path` | 开场玩家路径 |
| 1461 | `intro_helicopter_yaw_path` | 直升机偏航 |
| 1525 | `intro_occupant_local_root` | ★ 3 维向量 `{ -20.440, -66.178, -101.109 }` |
| 1594 | `extraction_player_path` | 撤离路径 |
| 1799 | `objective_track` | 目标轨道 |
| 1873 | `intro_scripted_view_track` | 开场视角轨道 |
| **2112** | ★★★ **`route`** | **22 阶段任务路线** |
| 2292 | `ally_animation_track` | 友军动画 |
| 2413 | `enemy_weapon_pattern` | 8 项轮转 |
| **2487** | ★★★★★ **`enemy_attachment_by_spawner`** | **43 项** |
| 2504 | `enemy_first_fire_delay_by_spawner` | 首发延迟 |
| 2518 | `enemy_burst_pattern_by_spawner` | 点射模式 |
| **2542** | ★★★★ **`enemy_recorded_path_by_spawner`** | **录像路径（1,200+ 行,全文件最大表）** |
| 3766 | `encounter_groups` | 交战组 |
| 3841 | `repeating_enemy_wave_offsets` | 重复波次偏移 |
| 3926 | `intro_enemy_events` | 开场敌人事件 |
| 3975 | `blast_corpse_offset_by_spawner` | 冲击尸体偏移 |

★★★ **⇒ 最大的表是 `enemy_recorded_path_by_spawner`（第 2542–3765 行,**约 1,224 行**）⇒ 占全文 **26%**。**

★ **⇒ 八个"轨道"表（`*_track`）⇒ 回放架构的核心。**

---

## 十三、★★★★ **四个 `codol.on` 注册**

| 事件 | 位置 | 作用 |
|---|---|---|
| **`player_killed`** | **4566** | ★★ **检查点重生（2000 ms）** |
| **`client_spawned`** | **4601** | ★★★ **任务启动（16+ 线程）** |
| （`codol.on` 只在两处） | — | — |

★★ **⇒ 与 gametype 文件对比：**
```
gametype 文件：注册 `player_killed` / `client_spawned` / `zm_round_tick` / `entity_killed`
本文件：     只注册 **`player_killed`** + **`client_spawned`**
```

★ **⇒ 且本文件的 `player_killed`**没有 pcall 包裹**（与报告 076 的 FAIL-SOFT 覆盖率问题同类）。**
**⇒ 但本文件大量使用 `codol.call` 的 `(ret, err, code)` 三值检查，且每个调用都 `print` 错误 ⇒ **错误处理比 gametype 更严**。****

---

## 十四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 文件规模 | **4,683 行** / **87 个函数** / **62 个 API** / **31 个数据表** |
| 2 | ★★★★★ **身份** | 关卡 **Wetwork（"Unidentified"）**,**地图脚本** |
| 3 | ★★★ 返回表消费者 | **`SV_LoadMapScriptMetadata`**（**组装 gameplay source 之前,只消费一次**） |
| 4 | ★★★★★ **`return {}` 空的理由** | **无 MP 式 `minimap_corner` 对**；声明 `compass_map_cargoship` 会让**方形小地图设置拒绝地图** |
| 5 | ★★ 数据权威 | **MapEnts 权威**,"**rather than copying positions out of the recording**" |
| 6 | ★★★★★ **22 阶段任务路线** | 1 开场 + 3 走廊 + 5 货舱 + **`sinking`** + 11 逃生 + 1 登机 |
| 7 | ★★ 键类型 | **只有首尾 2 个用 `targetname`**,其余 **20 个 `script_flag`** |
| 8 | ★★★ 每阶段两动作 | `apply_phase_presentation` + ★ **`method:savecheckpoint`** |
| 9 | ★★★★ **`codol.wait(0)` 的理由** | "Adjacent and overlapping volumes must not **collapse into several phase changes in one server frame**" |
| 10 | ★★★★★ **CODREF 出处格式** | demo 区间 / **MapEnts** / **agentState field 13** / demo 名 |
| 11 | ★★★★★ **算术自洽 ×2** | **181950 − 10950 = 171000** ✓；**850 + 4400 = 5250** ✓ |
| 12 | ★★★★★ **16.65 s 门口列队** | 12 项 `codol.wait` **逐项相加 = 16,650 ms** ✓ |
| 13 | ★★ `204050 → 204350` | **三 tick（300 ms）** |
| 14 | ★★★★★ **六种控制台命令前缀** | **`s`**（cvar）/ **`w`**（武器）/ **`u`**（UI 动词）/ **`o`**（音效环境）/ **`n`**（淡入淡出）/ **`i`**（图像） |
| 15 | ★★★ `u 8` / `u 9` | 成对出现（武器切换动画）⇒ 印证 `dm.lua` 的 `u 10`/`u 11` |
| 16 | ★★ 裸数字 cvar | **`s 0194 ""`**（与 `1224=90` 同类） |
| 17 | ★★★★★ **槽位划分（0–23）** | **0–5 直升机乘客** / **6–10 五名常驻队员** / **11–12 飞行员** / **13–23 敌方池（11）** |
| 18 | ★★ 电影槽位可回收 | "Those cinematic slots **return to the common actor pool**" |
| 19 | ★★★ `acquire_enemy_slot` | 扫 **0..23**,无则 **等 50 ms** 无限重试 |
| 20 | ★★★★★ **船体倾斜 API ×3** | `function:spawngroundtiltcontroller` / `method:setgroundtilttrajectory`（**10 个数值参**）/ **`method:playersetgroundreferenceent`** |
| 21 | ★★★ 绑定/解绑 | **传控制器 = 绑定；只传 player = 解绑** |
| 22 | ★★★★★ **`field 231 = 100`** | 轨迹从 **+5100** 开始,retail **550 ms 后**在首个携带该字段的快照上选实体 |
| 23 | ★★★ 倾斜总时长 | **77,300 ms** |
| 24 | ★★★ 出错必解绑 | 失败路径也 `playersetgroundreferenceent` + `delete` |
| 25 | ★★★★★ **车辆目标环** | **configstring 792–805**（**14 槽**）；格式 `\ent\…\offs\0 0 32\offmat\-1\mat\…\flags\…` |
| 26 | ★★★ 两个材质与 flags | **`\mat\-1`** / **`\mat\188`**；**798 → 304**,**≥799 → 288**；**+8 = 激活位** |
| 27 | ★★ 门控字段 | `script_noteworthy == **"chopper_deck_enemies"**`（与 `"zombie_spawner"` 同类） |
| 28 | ★★★★★ **`enemy_attachment_by_spawner`** | **43 个 spawner** ⇒ 覆盖录像 **47 个**可无歧义出生；值 = **第三人称武器模型**（7 种：463/466/479/480/481/482/484） |
| 29 | ★★ 实体号分布 | **簇状**（64–71 / 134–139 / 346–353 各 6–8 个） |
| 30 | ★★★ `enemy_attachment` 三级回退 | 录像表 → `_rpg_`=**463** → `_ump_`=**466** → 8 项轮转 |
| 31 | ★★★★★ **RPG 未实现** | "**Explosive projectiles remain a separate restoration pass**" ⇒ RPG **用步枪伤害**（`ak47_mp`） |
| 32 | ★★ `string.find(..., 1, **true**)` | 纯文本匹配（不下划线转义） |
| 33 | ★★★★★ **武器重映射 9 项** | 录像索引 **1192–1212** → `function:weaponindex(定义串)` → 实时编号,★ **带缓存** |
| 34 | ★ 定义串格式 | `** <n> 0 0 <n...>` |
| 35 | ★★★ 三级处理 | `0`→**0**；无映射→**原样**；有映射→**解析 + 缓存**；失败→**nil** |
| 36 | ★★ `setplayerweapons` 两签名 | **3 参**（无 supplemental）/ **4 参**（有） |
| 37 | ★★★★★ **`finish_mission` 四时刻** | 成功 UI **475600** → 决定 **480850** → **`EXE_MATCHENDED` 481850**；保持 **5250 ms** |
| 38 | ★★ `method:setcandamage(player, false)` | 过场前关受伤 |
| 39 | ★★ `function:finishmission` | **无参数** |
| 40 | ★★★★★ **与 `coop.lua` 逐字呼应** | `coop.lua`："Wetwork death and checkpoint restart … **will be owned by the cargoship map layer**" ⇒ 本文件正是那一层 ✓ |
| 41 | ★★ 战役重生延迟 | **2000 ms**（≠ gametype 的 3000） |
| 42 | ★★★ 线程不重置任务 | "leaving the **encounter and mission threads alive**" |
| 43 | ★★★★★ **三个死亡体积** | `escape_carghold1_flood_death` / **`escape_catwalk_death`** / `escape_hallway_lower_flood_death` |
| 44 | ★★ 生效条件 | **仅 `force_explosion_start` 之后**（阶段 9） |
| 45 | ★★★★★ **`finishplayerdamage` 11 参** | 1000 伤害 / dflags 0 / **mod 16** / **weapon 165** / 方向 **`{0,0,1}`** |
| 46 | ★★ 重臂条件 | "Re-arm only after the new life has left the brush so **one touch cannot enqueue several deaths**" |
| 47 | ★★★★★ **16+ 并发线程** | **13 个固定** + `encounter_groups` 组 + **3 个死亡体积** |
| 48 | ★★★ **Lua 闭包陷阱** | 两处都写 `local current_X = X` 复制循环变量 |
| 49 | ★★ `start_global_presentation` | **5750 ms** 后 `trigger_exploder(1, 150)` |
| 50 | ★★ 开局武器 | 主 **1198** / 副 **1197** / 弹药 **30/90** 与 **15/45** |
| 51 | ★★★★ 最大表 | **`enemy_recorded_path_by_spawner`（约 1,224 行 = 全文 26%）** |
| 52 | ★ 八个轨道表 | `*_track` × 8 |

---

## 十五、结论

### 1. ★★★★★ **这是"录像驱动"的战役任务重实现**

```
所有时间都 CODREF 到一个具体录像区间
        ↓
★★★ 三个算术自洽证据：
  · 181950 − 10950 = **171000 ms** ✓
  · 850 + 4400 = **5250 ms** ✓
  · 12 项 codol.wait 逐项相加 = **16,650 ms = 16.65 s** ✓
        ↓
★★★ 但数据权威仍是 **MapEnts**,而非录像
   （"**rather than copying positions out of the recording**"）
```

### 2. ★★★★★ **22 阶段的完整任务路线**（1 开场 + 3 走廊 + 5 货舱 + 沉船 + 11 逃生 + 登机）

★ **⇒ 每阶段**保存一个检查点**（`method:savecheckpoint`）。**
**★ ⇒ `codol.wait(0)` 防止同帧跨多阶段。**

### 3. ★★★★★ **船体倾斜（沉船）系统是新 API 面**

```
`function:spawngroundtiltcontroller`
`method:setgroundtilttrajectory`（**10 个数值参**）
`method:playersetgroundreferenceent`（**可选第二参数 = 绑/解绑**）
        ↓
★ 判据：**`field 231 = 100`** 的 playerState 快照
★ 总时长 **77,300 ms**
```

### 4. ★★★★★ **演员槽位划分被精确定义**

```
0–5   直升机乘客（6）
6–10  常驻队员（5）
11–12 飞行员（2）
13–23 敌方池（11）
```

### 5. ★★★★★ **`return {}` 是故意的**（无 `minimap_corner` 对 ⇒ 否则方形小地图会拒绝地图）

### 6. ★★★★ **与 `coop.lua` 的分工**被两处注释**互相印证**（战役在 map 层,不在 gametype 层）

### 7. ★★★★ **RPG 只有外观没有爆炸伤害**（明确的"未实现"声明）

### 8. ★★★ **武器索引必须重映射**（录像 1192–1212 → `function:weaponindex` → 实时编号,带缓存）

### 9. ★★★ **16+ 并发 Lua 线程** + 两处 Lua 闭包捕获陷阱的正确处理

### 10. ★★ **六种控制台命令前缀**（`s`/`w`/`u`/`o`/`n`/`i`）首次被完整记录

---

## 十六、下一步

- `enemy_recorded_path_by_spawner`（第 2542–3765 行,1,224 行）—— 全包最大的单个数据表
- `enemy_first_fire_delay_by_spawner` / `enemy_burst_pattern_by_spawner` / `encounter_groups`
- 其余 `maps\*.lua`（18 个小文件）
- `ol-mod-runtime-manifest.json`（28,209 B）
- `bundle\` 侧剩余文件与 `payload\` 剩余资源
