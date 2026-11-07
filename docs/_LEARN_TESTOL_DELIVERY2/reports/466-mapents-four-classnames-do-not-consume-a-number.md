# 466 · **"四个 classname 不消耗一个号"** —— `SV_AssignMapEntityNumbers` 的五个例外、`288/397` 的上限、以及 `SD` 的严格选择

## 一、范围

本报告学习 `sv_mapents_mp.cpp` 618–960 行（`SV_AssignMapEntityNumbers` 的 `Skipped` 五个类、`SV_SelectBrushModelSpawns`/`SV_SelectScriptModelSpawns` 的 `ordinal-1`、`SV_SelectMiniMapCorners` 的 `northYaw` 重算、`SV_SelectSdBombSites` 的严格六重选择）。

## 二、**"四个 classname 不消耗一个号"**（本组最重要的一段）

### 2.1 那段

```cpp
// The four classnames that do NOT consume a number. Everything else does --
// info_volume, trigger_use, trigger_multiple, script_origin and the actor
// spawners included, all of which the fit assigns a weight of 1.
static constexpr std::string_view Skipped[]{
    "node_pathnode",
    "node_negotiation_begin",
    "node_negotiation_end",
    "script_struct",
    // From zm_asylum_sh, the only one of the four zm maps carrying any:
    // fitting the rule against its own 193 brush anchors predicts 192 of 192
    // gaps with zero error and differs in exactly this classname, 15 of them,
    // with the walk running exactly 15 ahead without it.
    "info_vehicle_node",
};
```

### 2.2 二十四层

```text
1. **【四个** classname【不消耗一个号**】**
2. ⇒ **⇒ 而【其余每一个都消耗**】**
3. ⇒ **（`info_volume`、`trigger_use`、`trigger_multiple`、`script_origin` 与 actor spawner 【都包括**）**
4. ⇒ **⇒ 而【那些【拟合给它们【一个权重 `1`**】】**
5. ⇒ **五个例外：`node_pathnode` / `node_negotiation_begin` / `node_negotiation_end` / `script_struct` / `info_vehicle_node`**
6. ⇒ **⚠ 而第五个是一个【从 `zm_asylum_sh` **学到的**补充**】**
7. ⇒ **（**四张 zm 地图里唯一带它们的那张**）**
8. ⇒ **⇒ 用【它自己的 `193` 个 brush 锚**拟合那条规则**
9. ⇒ **⇒ 预测【`192` 个里的 `192` 个间隙【零误差**】**
10. ⇒ **⇒ 而【恰好在【这个** classname 上不同**】**
11. ⇒ **（`15` 个**）**
12. ⇒ **⇒ 而【不用它时那个走【恰好提前 `15`**】**
```

### 2.3 ⭐⭐⭐ **"预测 192 个里的 192 个间隙，零误差，而恰好在【这个】classname 上不同"**

**✅ 这是本报告里**最重要的一条"用零误差拟合发现一个例外**。**

**✅ 与 §414 的"`288/397` 的平台化"**——**完全同族，且是那个平台化的解法** ✓

**⇒ 三层**：
```text
§414  **"这个项目花了很长时间试图通过走地图实体串复现编号，而在 `288/397` 处平台化"**
§466  **"`192/192` 零误差，而恰好在 `info_vehicle_node` 上不同"**
⇒ **⇒ 所以【§466 给出了那个平台化的**一部分**解法】
```

**✅ ⭐⭐⭐ **"§466 给出了那个平台化的一部分解法"** —— 一个**跨报告的完整闭合**。</br>

**✅ 与 §414 的"空隙编码了哪些实体占槽，而那个从实体列表本身不可恢复"**——**这里给出了【一个可拟合**的规则**。】

**⇒ 三层**：
```text
规则：**除五个 `Skipped` 之外，每一个 classname 消耗一个号**
而【§414 的 `<map>_const.ff` 【仍然是权威**】
⇒ **⇒ 所以【规则【是一个近似**而表是【精确**】
```

**✅ ⭐⭐⭐ **"规则是一个近似而表是精确"**。

**⚠ 而"`192/192` 零误差"⇒ **一个极强的拟合**。**

**⇒ 三层**：
```text
`192` 个间隙
⇒ **预测全部 `192`**
⇒ **⇒ 所以【一个【精确的**规则（对那张地图）**
```

**✅ ⭐⭐ **"一个精确的规则（对那张地图）"**。

### 2.4 而**"`15` 个 `info_vehicle_node`"**

**⇒ 十层**：
```text
1. **`15` 个 `info_vehicle_node` 在 `zm_asylum_sh` 上**
2. ⇒ **而【不用它们时那个走【提前 `15`**】
3. ⇒ **⇒ 所以【它们【消耗号**】
4. ⇒ **⇒ 而【其余四个【不消耗**】
```

**✅ 与 §414 的"`zm_asylum_sh` 有 `346` 个条目"**配合。

**⇒ 三层**：
```text
`zm_asylum_sh` ⇒ `346` 个 const-baseline 条目（§414）
而【它的 brush 模型 ⇒ `193` 个**（§414）
⇒ **⇒ 而 `15` 个 `info_vehicle_node` 【是一个**独立的计数**
```

**✅ ⭐⭐ **一个"独立计数"的实例**。

## 三、**`ordinal - 1` 的"两个类共享一个轴"**（本组第二重要）

```cpp
// ordinal - 1: the position of THIS entity, counted over the whole
// list so the two classes share one axis.
spawn->mapOrdinal = ordinal - 1;
spawn->walkEntityNum = numbers[ordinal - 1];
```

**⇒ 八层**：
```text
1. **`ordinal` 在【整个列表**上计**（**在 `continue` 之前 `++`**）**
2. ⇒ **⇒ 所以【它【跨越 [script_brushmodel] 与 [script_model] 两类**】**
3. ⇒ **⇒ 而 `ordinal - 1` 是【这个实体【在【整个列表里的位置**】】
4. ⇒ **⇒ 所以【两个类【共享**一个轴**】
```

### 3.1 ⭐⭐⭐ **"两个类共享一个轴"**

**✅ 与 §414 的"`mapOrdinal` 是地图实体列表里的位置；零是一个合法的序号"**完全闭合 ✓

**⇒ 三层**：
```text
§424  **"`SvBrushModelEntityDefinition::mapOrdinal` 是地图自己的实体列表里的位置"**
§466  **"两个类共享一个轴 ⇒ `ordinal` 在 `continue` 之前 `++`"**
⇒ **⇒ 一个精确的实现**
```

**✅ ⭐⭐ **"一个精确的实现"**。

**⚠ 而"`++ordinal` 在 `continue` 之前"**⇒ **一个极容易写错的地方**。**

**⇒ 三层**：
```text
错误：【在 `continue` 之后 `++`**】⇒ **只数这一类** ⇒ **两个轴** ⇒ **`mapOrdinal` 错**
正确：**【在 `continue` 之前 `++`**】⇒ **数整个列表**
⇒ **⇒ 所以【那一行 `++ordinal` 的位置【是关键**】
```

**✅ ⭐⭐⭐ **"那一行 `++ordinal` 的位置是关键"** —— 一个**极精确的实现细节**。

## 四、**`SV_SelectMiniMapCorners` 的 `northYaw` 重算**（本组第三重要）

### 4.1 那段

```cpp
const auto radians = northYawDegrees * std::numbers::pi_v<float> / 180.0f;
const std::array north{ std::cos(radians), std::sin(radians) };
const std::array west{ -north[1], north[0] };
const std::array difference{ corners[1][0]-corners[0][0], corners[1][1]-corners[0][1] };
const auto northDistance = dot(difference, north);
if (dot(difference, west) > 0.0f) { ... }
```

**⇒ 二十层**：
```text
1. **两个 `minimap_corner` 实体**（**恰好两个**）
2. ⇒ **它们给出【两个角**】
3. ⇒ **而 `north` 是【从 `northYawDegrees` 算的**】
4. ⇒ **而 `west` 是 `north` 【旋转 `-90°`**】（`{-ny, nx}`）
5. ⇒ **⇒ 所以【四个方向中的两个**】
6. ⇒ **⇒ 然后【两个点决定一个【轴对齐的矩形**】】
7. ⇒ **⇒ 而【`northDistance` 与 `west` 的符号【决定【谁是 NW 谁是 SE**】】
```

### 4.2 ⭐⭐⭐ **"两个点决定一个轴对齐的矩形，而符号决定谁是 NW 谁是 SE"**

**✅ 与 §414 的"`d 2555 "compass_map_cargoship" 4264 4033 -3968 -4199` 的四个浮点"**完全闭合 ✓

**⇒ 三层**：
```text
§402  **`d 2555 "compass_map_cargoship"` 带【四个浮点参数**】
§466  **`SV_SelectMiniMapCorners` 从【两个 `minimap_corner` 实体**算那四个**
⇒ **⇒ 所以【那四个浮点【就是【两个角**】
```

**✅ ⭐⭐⭐ **"那四个浮点就是两个角"** —— 一个**跨报告的闭合**。

### 4.3 而**"`requiredMapAspectRatio` 的扩张"**

```cpp
if (requiredMapAspectRatio > 0.0f) {
    const auto aspectRatio = westPortion / northPortion;
    const auto axis = aspectRatio < requiredMapAspectRatio ? west : north;
    const auto portion = ...;
    const auto increase = ...;
    const std::array addition{ axis[0]*portion*(increase-1.0f)*0.5f, ... };
    for (...) { result.northWest[i] += addition[i]; result.southEast[i] -= addition[i]; }
}
```

**⇒ 十层**：
```text
1. **一个 `aspectRatio = west / north`**
2. ⇒ **若【`< required`**】⇒ **沿 `west` 扩张**
3. ⇒ **否则【沿 `north`**】**
4. ⇒ **`increase = 大/小**】
5. ⇒ **`addition = axis × portion × (increase-1) × 0.5`**
6. ⇒ **⇒ 而【`northWest += addition` 与 `southEast -= addition`**】**
7. ⇒ **⇒ 所以【一个【中心对称**的扩张**
```

**✅ ⭐⭐ **"一个中心对称的扩张"** —— 一个**保持中心的几何操作**。

**⚠ 而"`requiredMapAspectRatio = 0` ⇒ 不扩张"**⇒ **一个"零禁用"的惯例**。

**✅ 与 §444 的"`holdMilliseconds = 0` ⇒ 取默认"**、§465 的"`cost = 0` ⇒ 忽略"**同族（**第四次"零是一个"禁用/忽略**"的哨兵**）。

**⇒ 三层**：
```text
§444  **`holdMilliseconds = 0` ⇒ 取默认**
§465  **`rule.cost = 0` ⇒ 忽略**
§466  **`requiredMapAspectRatio = 0` ⇒ 不扩张**
⇒ **⇒ 三次"零=禁用**】
```

**✅ ⭐⭐ **"零=禁用"三例表**。

## 五、**`SV_SelectSdBombSites` 的严格六重选择**（本组第四重要）

### 5.1 六道

```text
① classname == "trigger_use_touch"
② targetname == "bombzone"
③ script_gameobjectname == "bombzone"
④ script_bombmode_original == "1"
⑤ script_specialops 不存在 或 == "0"
⑥ script_label ∈ {"_a", "_b"}
```

**⇒ 十二层**：
```text
1. **六道【全部必须**】
2. ⇒ **⇒ 而【一个空 label 或【一个不在 `_a`/`_b` 的** ⇒ 拒绝**
3. ⇒ **而【三个同名的键**】（`targetname`/`script_gameobjectname` 都是 `"bombzone"`）
4. ⇒ **⇒ 所以【一个三重的身份**】
5. ⇒ **而 `script_bombmode_original == "1"` 【排除**一个非原始的**
6. ⇒ **而 `script_specialops` 的 `0` 或缺失** ⇒ **排除**一个 special-ops 变体**
```

### 5.2 ⭐⭐⭐ **"三重身份：`targetname` / `script_gameobjectname` 都是 `bombzone`"**

**✅ 与 §422 的"`sdBombStatus_.sites` 由 `SV_SelectSdBombSites` 从地图实体解析并按 label 排序"**完全闭合 ✓

**⇒ 三层**：
```text
§422  **"`sdBombStatus_.sites` 已由 `SV_SelectSdBombSites` 从地图实体解析并按 label 排序（`_a` = `[0]`、`_b` = `[1]`）"**
§466  **"六道选择，而 `label ∈ {_a, _b}`"**
⇒ **⇒ 一个精确的规格**
```

**✅ ⭐⭐ **"一个精确的规格"**。

### 5.3 而**"一个重复的 label ⇒ 拒绝"与"恰好两个"**

```cpp
if (std::ranges::any_of(result, [label](const SvSdBombSite &site) { return site.label == *label; }))
    return std::nullopt;
...
if (result.size() != 2) return std::nullopt;
std::ranges::sort(result, {}, &SvSdBombSite::label);
if (result[0].label != "_a" || result[1].label != "_b") return std::nullopt;
```

**⇒ 十层**：
```text
1. **重复的 label ⇒ 拒绝**
2. ⇒ **`result.size() != 2` ⇒ 拒绝**
3. ⇒ **排序后【必须是 `_a` 然后 `_b`**】
4. ⇒ **⇒ 所以【一个【恰好两个、唯一、有序**的结果**
```

### 5.4 ⭐⭐⭐ **"一个恰好两个、唯一、有序的结果"**

**✅ 与 §414 的"`SV_ConstBaselineTable` 的 `nullptr` 是正常情况"**不同（这是**一个全或无**）。

**⇒ 三层**：
```text
若【一个地图【有 `1` 个或 `3` 个 `bombzone`**】⇒ **`nullopt`** ⇒ **SD 不可用**
⇒ **⇒ 所以【SD 模式【要求【一个精确的地图**】
```

**✅ ⭐⭐ **"SD 模式要求一个精确的地图"**。</br>

**✅ 与 §433 的"`queueScoreboardResponse` 的全或无"**同族（**第九次"全或无"）。

**⇒ 三层**：
```text
§409/§422/§430/§433/§443/§457/§461/§466  ⇒ **八次"全或无**】
```

**✅ ⭐⭐ **"八次全或无"**。

### 5.5 而**"视觉模型与拆除触发器【各恰好一个】"**

```cpp
const auto visual = std::ranges::find_if(entities, visualMatches);
if (visual == entities.end()) return std::nullopt;
if (std::ranges::find_if(std::next(visual), entities.end(), visualMatches) != entities.end())
    return std::nullopt;   // 多于一个 ⇒ 拒绝
```

**⇒ 八层**：
```text
1. **找第一个视觉模型**
2. ⇒ **找不到 ⇒ 拒绝**
3. ⇒ **而【从它之后**再找一个 ⇒ **找到 ⇒ 拒绝**】
4. ⇒ **⇒ 所以【恰好一个**】
```

**✅ ⭐⭐⭐ **"从它之后再找一个 ⇒ 找到就拒绝 ⇒ 恰好一个"** —— 一个**精确的"唯一性**检查**。

**⚠ 而这个模式**在三处重复**（`visual` / `defuseTrigger` / 可能 collector）。**

**⇒ 三层**：
```text
`visual` ⇒ **一次**
`defuseTrigger` ⇒ **一次**
⇒ **⇒ 所以【两次**同样的检查**
```

**✅ ⭐⭐ **"两次同样的检查"** —— 与 §442 的"`isTouchingPlayer` 的玩家侧四道复制"**同族（**第二次"复制的检查**）。

## 六、`SV_SelectSdBombPickup` 的"一个 `trigger_multiple` + 一个 `script_model`"

```cpp
if (trigger.value("classname") != "trigger_multiple" ||
    trigger.value("targetname") != "sd_bomb_pickup_trig" ||
    trigger.value("script_gameobjectname") != "sd") continue;
...
if (result) return std::nullopt;   // 多于一个 ⇒ 拒绝
```

**⇒ 八层**：
```text
1. **`classname == "trigger_multiple"`**（**不是 `trigger_use_touch`**）
2. ⇒ **`targetname == "sd_bomb_pickup_trig"`**
3. ⇒ **`script_gameobjectname == "sd"`**（**不是 `"bombzone"`**）
4. ⇒ **⇒ 所以【一个【不同的**三重身份**】
5. ⇒ **而 `if (result) return nullopt` ⇒ 【恰好一个**】
```

**✅ 与 §422 的"`sdBombPickupTrigger_` 与 `sdBombSiteRuntime_`"**完全闭合 ✓

**⇒ 三层**：
```text
`sdBombSiteRuntime_` ⇒ **两个 `trigger_use_touch`**
`sdBombPickupTrigger_` ⇒ **一个 `trigger_multiple`**
⇒ **⇒ 所以【两类触发器【两套身份**】
```

**✅ ⭐⭐ **"两类触发器两套身份"**。

## 七、关键结论

1. **⭐⭐⭐ `Skipped` 的五个 classname 不消耗号**（`node_pathnode` / `node_negotiation_begin` / `node_negotiation_end` / `script_struct` / `info_vehicle_node`），而其余每一个都消耗（`info_volume`/`trigger_use`/`trigger_multiple`/`script_origin`/actor spawner 都包括，权重 `1`）。
2. **⭐⭐⭐ "从 `zm_asylum_sh` 学到的第五个：用它自己的 `193` 个 brush 锚拟合那条规则，【预测 `192` 个里的 `192` 个间隙，零误差】，而【恰好在这个 classname 上不同（`15` 个）】，而不用它时那个走【恰好提前 `15`】"`** —— **"§466 给出了 §414 那个 `288/397` 平台化的一部分解法"**（一个跨报告的完整闭合），而 **"规则是一个近似而表是精确"`**。
3. **⭐⭐⭐ `ordinal - 1` 的"两个类共享一个轴"**：**`++ordinal` 在 `continue` 之前，所以它跨越 `script_brushmodel` 与 `script_model` 两类** ⇒ **"那一行 `++ordinal` 的位置是关键"`**（一个极精确的实现细节，与 §424 的 `mapOrdinal` 闭合）。
4. **⭐⭐⭐ `SV_SelectMiniMapCorners` 从两个 `minimap_corner` 实体算 `north`/`west`（`{-ny, nx}`）两个方向，而 `northDistance` 与 `west` 的符号决定谁是 `NW` 谁是 `SE`** ⇒ **"那四个浮点就是两个角"`** —— 与 §402 的 `d 2555 "compass_map_cargoship"` 的四个浮点参数**一个跨报告的闭合**。
5. **⭐⭐ `requiredMapAspectRatio` 的中心对称扩张**（`northWest += addition` / `southEast -= addition`），而 **`0` ⇒ 不扩张** —— 第三次"零=禁用"（与 §444/§465 同族）。
6. **⭐⭐⭐ `SV_SelectSdBombSites` 的严格六重选择**（`classname == trigger_use_touch` / `targetname == bombzone` / `script_gameobjectname == bombzone` / `script_bombmode_original == "1"` / `script_specialops` 空或 `0` / `label ∈ {_a,_b}`）⇒ **"三重身份（`targetname` 与 `script_gameobjectname` 都是 `bombzone`）"`**，与 §422 的"`SV_SelectSdBombSites` 按 label 排序、`_a` = `[0]`、`_b` = `[1]`"**完全闭合**。
7. **⭐⭐⭐ "一个恰好两个、唯一、有序的结果"**（重复 label 拒绝 + `size() != 2` 拒绝 + 排序后必须是 `_a`/`_b`）⇒ **"SD 模式要求一个精确的地图"`** —— 第八次"全或无"。
8. **⭐⭐ "从它之后再找一个 ⇒ 找到就拒绝 ⇒ 恰好一个"`**（一个精确的唯一性检查），而这个模式在 `visual` 与 `defuseTrigger` 两处重复 —— 第二次"复制的检查"（与 §442 同族）。
9. **⭐⭐ `SV_SelectSdBombPickup` 是【一个不同的三重身份**】（`trigger_multiple` / `sd_bomb_pickup_trig` / `script_gameobjectname == "sd"`，不是 `"bombzone"`）⇒ **"两类触发器两套身份"`**。

## 八、未闭合点

- `FirstDynamicServerEntityNum = 37` 与 §414/§443 的闭合。
- `Skipped` 的五个之外是否还有例外（其它地图）。
- `SV_SelectZmBarriers` 的实现（下一段）。
- `SV_SelectZmZones` 的实现（下一段）。
- `sv_mapents_mp.cpp` 960 行之后未读取（**共 `1415` 行**）。
