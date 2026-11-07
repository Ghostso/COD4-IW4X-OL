# 302 · **"这个服务器完全不发布 brush model"**、`uk`/`ab` 的 TF/SC 映射、`34 of 238`

## 一、范围

本报告学习 `Appmain.cpp` 6980–7200 行。

## 二、`configureWorldSpawn` 的**八个参数**

```cpp
Server.configureWorldSpawn(
    worldSpawnPoints,
    brushModels,
    scriptModels,
    scriptModelDamageOwners,
    SvWorldSpawnPoint{ .origin = connectionSpawn->origin, .angles = connectionSpawn->angles },
    request->mapName,
    request->gameType,
    *logicalMapEntities);
```

**⇒ 八项。**

### 2.1 而 `logicalMapEntities` 是**第九个阶段**

```cpp
const auto logicalMapEntities = SV_SelectLogicalMapEntities(*entities);
if (!logicalMapEntities) { reportFailure("logical_map_entity_parse"); return; }
logGameServer("logical map entities map=" + mapName + " count=" + size);
```

**⇒ 所以世界准备有**九个阶段**（加上 §294 的六个与 §295 的两个 ⇒ 但有些重叠）。**

## 三、**`dmz_empty_mp` 的空手**（本组第二重要）

```php
// EMPTY HANDS ARE A WEAPON. Resolved here because this is where the
// weapon band is live and the asset owner is reachable; the mode decision
// itself was made at gametype configure. `dmz_empty_mp` sits at 1137 on
// mp_battlecity, in the dmz cluster next to dmz_gas_mp and dmzhealneedle_mp,
// but it is looked up BY NAME because the band is per-map.
if (request->gameType == "dmz")
{
    constexpr std::string_view EmptyHandsWeapon = "dmz_empty_mp";
    const auto emptyHands = Bindings.resolveWeaponConfigStringIndex(EmptyHandsWeapon);
    if (emptyHands)
    {
        Server.setUnarmedSpawnWeapon(*emptyHands);
        logGameServer("dmz empty hands weapon " + name + " = " + *emptyHands);
    }
    else
    {
        // Not fatal: the spawn falls back to index 0, which is armless but
        // still unarmed. Say so, because "no hands" is the symptom.
        logGameServer("dmz empty hands weapon " + name + " NOT FOUND in the weapon band -- "
            "spawning with index 0, which draws no viewmodel and so no hands");
    }
}
```

### 3.1 五层

```text
1. **空手是一个武器**
2. 在这里解析因为**武器带是活的**且资产所有者可达，而**模式决定已在 gametype 配置时做出**
3. `dmz_empty_mp` 在 `mp_battlecity` 上是 **1137**，与 `dmz_gas_mp`/`dmzhealneedle_mp` 相邻
4. ⇒ 但**按名字查**因为**带是每地图的**
5. ⇒ 缺失**不致命**：回退到索引 0（无臂但仍无武装）且明说
```

### 3.2 而"按名字查因为带是每地图的"

**⇒ 与 §285/§290 的"索引是加载顺序"**第五次**同族。**

**⇒ 而 1137 是**这个地图上的**索引 —— 所以不可移植。**

### 3.3 而**"索引 0 画不出 viewmodel 所以没有手"**

**⇒ 与 §301 的"武器索引 0 没有 viewmodel ⇒ 没有武器与没有手是同一个状态"**完全一致** ✓**

### 3.4 而 `dmz_empty_mp` 与 §148 的记忆

**记忆**："`dmz_empty_mp` for unarmed"

**✓ 完全一致。**

## 四、**`uk`/`ab` 的 TF/SC 映射**（本组第三重要）

### 4.1 那段

```php
// Crash inherits the COD4/IW4 SAS-versus-OpFor faction pairing.
// TF consumes the allies spawn set and SC consumes the axis set in
// this server, so their loaded CODOL leader packs are uk/ab.
// TODO(CODOL): Resolve these prefixes from CODOL's map faction
// owner before enabling SD presentation on additional maps.
if (request->mapName == "mp_crash" || request->mapName == "mp_crash_tropical")
{
    constexpr std::array<std::string_view, 14> TeamSuffixes{
        "search_destroy", "obj_destroy", "obj_defend",
        "bomb_taken", "bomb_lost", "bomb_planted",
        "bomb_defused", "lastalive", "encourage_win",
        "encourage_lost", "mission_success", "mission_fail",
        "draw", "switching",
    };
    std::vector<std::string> aliases{
        "mp_war_objective_lost", "mp_war_objective_taken",
    };
    for (const auto prefix : { "uk", "ab" })
        for (const auto suffix : TeamSuffixes)
            aliases.push_back(std::string(prefix) + "_1mc_" + std::string(suffix));
    ...
}
```

### 4.2 五层

```text
1. `mp_crash` **继承 COD4/IW4 的 SAS vs OpFor 阵营配对**
2. **TF 消费 allies 出生集而 SC 消费 axis 集**在这个服务器里
3. ⇒ 他们加载的 CODOL 领队语音包是 **`uk`/`ab`**
4. 14 个后缀 × 2 个前缀 = **28 个** + 2 个通用 = **30 个**
5. ⇒ `TODO`：在启用**更多地图**的 SD 表现之前，从 CODOL 的地图阵营所有者解析这些前缀
```

### 4.3 而 14 个后缀

```text
search_destroy / obj_destroy / obj_defend
bomb_taken / bomb_lost / bomb_planted / bomb_defused
lastalive
encourage_win / encourage_lost
mission_success / mission_fail
draw / switching
```

**⇒ 14 个。**

### 4.4 而 `resolveTeam(offset)` 的**十四项**

```cpp
const auto resolveTeam = [&](size_t offset) {
    return SvSdTeamSoundPresentation{
        .searchDestroy = parameter(offset),
        .objectiveDestroy = parameter(offset + 1),
        .objectiveDefend = parameter(offset + 2),
        .bombTaken = parameter(offset + 3),
        .bombLost = parameter(offset + 4),
        .bombPlanted = parameter(offset + 5),
        .bombDefused = parameter(offset + 6),
        .lastAlive = parameter(offset + 7),
        .roundWon = parameter(offset + 8),
        .roundLost = parameter(offset + 9),
        .matchWon = parameter(offset + 10),
        .matchLost = parameter(offset + 11),
        .draw = parameter(offset + 12),
        .sideSwitch = parameter(offset + 13),
    };
};
```

**⇒ 14 项，与 14 个后缀**一一对应** ✓

### 4.5 而 `suffix` 与 `field` 的**语义映射**

```text
suffix                  field
search_destroy          searchDestroy
obj_destroy             objectiveDestroy
obj_defend              objectiveDefend
bomb_taken              bombTaken
bomb_lost               bombLost
bomb_planted            bombPlanted
bomb_defused            bombDefused
lastalive               lastAlive
encourage_win           roundWon          ← 【语义偏移】
encourage_lost          roundLost         ← 【语义偏移】
mission_success         matchWon          ← 【语义偏移】
mission_fail            matchLost         ← 【语义偏移】
draw                    draw              ✓
switching               sideSwitch        ✓
```

**⚠ 中间四个是**语义偏移**（`encourage` → `round`，`mission` → `match`）。**

**⇒ 可能因为**CODOL 的措辞与内部字段名不同**。**

**✓ 合理的。**

### 4.6 而那个**顺序的修正**

```php
// The map's TF side is the UK voice pack and SC is AB.
// Keep the presentation fields aligned with the faction
// assignment above; the previous order inverted pickup/lost
// announcements for every SD bomb event.
.tf = resolveTeam(2),
.sc = resolveTeam(2 + TeamSuffixes.size()),
```

**⇒ 四层**：

```text
1. TF 侧是 **UK** 语音包而 SC 是 **AB**
2. ⇒ 保持表现字段与上面的阵营分配对齐
3. ⇒ **之前的顺序把每一个 SD 炸弹事件的拾取/丢失播报都反转了**
4. ⇒ 所以 `tf = resolveTeam(2)` 而 `sc = resolveTeam(2 + 14)` = `resolveTeam(16)`
```

### 4.7 而**索引的算术**

```text
aliases[0] = mp_war_objective_lost
aliases[1] = mp_war_objective_taken
aliases[2..15]  = uk_1mc_* (14 个)
aliases[16..29] = ab_1mc_* (14 个)
```

**⇒ 而 `tf = resolveTeam(2)` ⇒ uk 的 14 个，`sc = resolveTeam(16)` ⇒ ab 的 14 个。**

**✅ 算术闭合。**

### 4.8 而"TF 是 UK 而 SC 是 AB"

**⚠ 而 §288 的 `ab_1mc_lead_taken_01` 与 `uk_1mc_lead_lost_01` 的**混用**。**

**⇒ 如果 TF 是 UK 而 SC 是 AB，那 lead_taken 用 ab_ 而 lead_lost 用 uk_ 就是**反的**。**

**⇒ 与 §288 指出的"不一致"**互相印证** —— 那可能是一个真实的 bug。**

## 五、**"这个服务器完全不发布 brush model"**（本组最重要的一段）

### 5.1 那段完整的诊断

```php
// OLMOD(brushmodel-census): one-shot inventory of what the map actually carries.
//
// The doors do not render because this server publishes NO brush models at all: the
// model configstring band (ModelConfigStringBase 2568) never receives a `* N` entry,
// and retail's zm_factory_sh gamestate carries 34 of them (`* 1159`..`* 1192`, demo
// C-2021-7-31[15-32-16]zm cs 2979/2980 and 2995..3026). `clipHandle` below IS the N.
// Retail publishes 34 of the 238, so the open question is WHICH -- and a door is
// identifiable by its targetname / script_gameobjectname, which the parser already
// keeps. Printed once per world spawn so the selection can be made from data.
```

### 5.2 七层

```text
1. **门不渲染是因为这个服务器完全不发布 brush model**
2. 模型配置串带（**`ModelConfigStringBase 2568`**）**从不收到一个 `* N` 条目**
3. 而零售的 `zm_factory_sh` gamestate **携带 34 个**（`* 1159`..`* 1192`）
4. 位置：demo `C-2021-7-31[15-32-16]zm` 的 **cs 2979/2980 与 2995..3026**
5. ⇒ **下面的 `clipHandle` 就是那个 N**
6. 零售发布 **34 / 238** ⇒ 所以开放问题是**哪些**
7. ⇒ 一扇门可以被它的 `targetname`/`script_gameobjectname` 识别，而解析器**已经保留**了它们
```

### 5.3 而三个数

```text
34          零售发布的 brush model
238         地图实际携带的
34 / 238    比例（14%）
```

### 5.4 而 **cs 2979/2980 与 2995..3026**

```text
2979 / 2980       两个（可能是 `* N` 的两个控制项）
2995..3026        32 个（3026 - 2995 + 1 = 32）
⇒ 2 + 32 = 34 ✓
```

**✅ 算术闭合。**

### 5.5 而 `* N` 的格式

**⇒ 所以模型配置串的值是 `"* <N>"` 形式。**

**⇒ 而 `clipHandle` **就是**那个 N。**

**✅ 一个关键的格式确认。**

### 5.6 而"门不渲染"是**症状**

**⇒ 与 §295 的"表存在而图不存在 ⇒ 每个 actor 都停住"同族**（第五次"一个缺失导致一个可观测症状"）。

### 5.7 而 34 与 §285/§290 的 51/34 条武器串

**⚠ `34` 出现了三次：**

```text
§285  34   zm 零售武器串（1159..1192）
§290  34   同一个
§302  34   零售发布的 brush model（`* 1159`..`* 1192`）
```

**⇒ **同一个索引范围 `1159..1192`！**

**⇒ 所以武器配置串与 brush model 配置串**共用索引范围**？**

**⚠ 而这里是**模型**配置串（基址 2568）而 §285 是**武器**配置串（基址 5960）。**

**⇒ 所以两个不同的带，但**都从 1159 开始**，且都是 34 个。**

**⚠ 这可能是**巧合**或**同一个零售发行的编号约定**。**

**⇒ 值得指出。**

## 六、`sd` 的**炸弹表现**（本组第四重要）

```php
if (sdBombPickup)
{
    constexpr std::string_view SdBombPresentationModel = "prop_suitcase_bomb";
    const auto sourceModelIndex = resolveModelConfigStringIndex(sdBombPickup->visualModelName);
    const auto presentationModelIndex = resolveModelConfigStringIndex(SdBombPresentationModel);
    const SvScriptModelEntityDefinition visualDefinition{
        .origin = visualOrigin, .angles = visualAngles,
        .modelIndex = sourceModelIndex.value_or(0),
        .modelName = visualModelName,
        .scale = 1.0f,
        .scriptGameObjectName = "sd",
        .targetName = visualTargetName,
        .mapModeEligible = true,
        .gameplayActive = false,                    // ← 【false】
    };
    if (!sourceModelIndex || !presentationModelIndex ||
        !Server.configureSdBombPresentation(visualDefinition, *presentationModelIndex, SdBombPresentationModel))
    {
        reportFailure("sd_bomb_presentation_commit");
        return;
    }
```

### 6.1 两个模型

```text
visualModelName          地图自己的（sourceModelIndex）
prop_suitcase_bomb       表现用的（presentationModelIndex）
```

### 6.2 而 `gameplayActive = false`

**⇒ 所以炸弹的视觉实体**不参与游戏逻辑**。**

**⇒ 因为它是纯表现。**

**✓ 与 §302 的 `logicalMapEntities` 分离一致。**

### 6.3 而 `scriptGameObjectName = "sd"`

**⇒ 一个**标记**而不是真实的脚本对象名。**

**⚠ 可能是一个伪造值。**

## 七、`gameplay script` 的**四个阶段**

```php
const auto script = SV_LoadGameplaySource(gameplayScriptRoot(), mapName, gameType);
if (!script.succeeded())
{
    logGameServer("gameplay script unavailable map=... error=" + errorName + " detail=" + detail);
}
else if (!Server.loadGameplayScript(script.gameplaySource.sourceName, script.gameplaySource.source))
{
    logGameServer("gameplay script rejected map=...");
}
else
{
    const auto scriptStatus = Server.gameplayScriptStatus();
    const auto brushStatus = Server.worldBrushModelActivationStatus();
    ...
    logGameServer("gameplay script loaded generation=" + generation + " source=" + sourceName +
        " files=" + files + " brushModels=" + total + " taggedBrushModels=" + tagged +
        " activeBrushModels=" + active);
}
```

### 7.1 三个分支

```text
加载失败 ⇒ "unavailable" + error + detail
被拒绝   ⇒ "rejected"
成功     ⇒ "loaded" + generation + source + files + 三个 brushModels 计数
```

### 7.2 而**三个 brush model 状态**

```text
brushModels          总数
taggedBrushModels    带脚本标签的
activeBrushModels    游戏激活的
```

**⇒ 与 §299 的 `activeBrushModels` 与 §302 的"不发布 brush model"**直接相关**。**

**⇒ 所以**有脚本标签的** brush model 是**候选**，而**没有一个 active**。**

**⚠ 这可能就是"门不渲染"的**根因链**。** 

### 7.3 而失败**不致命**

**⇒ 三个分支都只记日志。**

**⇒ 与 §295 的"解析失败记录并故意忽略"同族。**

## 八、关键结论

1. **`dmz_empty_mp` 在 `mp_battlecity` 上是 1137**，但**按名字查**因为带是每地图的。
2. **"缺失不致命：回退到索引 0（无臂但仍无武装）"**。
3. **"索引 0 画不出 viewmodel 所以没有手"** —— 与 §301 一致。
4. **`mp_crash` 继承 COD4/IW4 的 SAS vs OpFor 配对**，而 **TF = UK、SC = AB**。
5. **14 个后缀 × 2 前缀 + 2 通用 = 30 个别名**，索引算术闭合（`resolveTeam(2)` 与 `resolveTeam(16)`）。
6. **"之前的顺序把每一个 SD 炸弹事件的拾取/丢失播报都反转了"** —— 一次已修的 bug。
7. **而 §288 的 `ab_/uk_` 混用可能与这个 TF/SC 映射矛盾** —— **互相印证一个真实 bug**。
8. **"这个服务器完全不发布 brush model"** —— 门不渲染的根因。
9. **`ModelConfigStringBase 2568` 从不收到 `* N` 条目**。
10. **零售 `zm_factory_sh` 携带 34 个（cs 2979/2980 + 2995..3026）** —— 算术闭合（2 + 32 = 34）。
11. **`clipHandle` **就是**那个 N**。
12. **零售发布 34 / 238（14%）** —— 开放问题是"哪些"。
13. **一扇门可由 `targetname`/`script_gameobjectName` 识别，而解析器已保留。**
14. **⚠ `34` 与索引 `1159..1192` 在武器带与模型带**同时出现** —— 可能是编号约定或巧合。
15. **`sd` 炸弹有两个模型**（地图自己的 + `prop_suitcase_bomb`），且 `gameplayActive = false`。
16. **`scriptGameObjectName = "sd"` 可能是一个伪造标记**。
17. **三个 brush model 状态**（total / tagged / active）—— `active` 为 0 是"门不渲染"的链条。

## 九、未闭合点

- `34` 与 `1159..1192` 在两个带的重复是否是编号约定。
- `activeBrushModels` 是否为 0（未实测）。
- `scriptGameObjectName = "sd"` 是否是伪造值。
- `Appmain.cpp` 7200 行之后未读取。
