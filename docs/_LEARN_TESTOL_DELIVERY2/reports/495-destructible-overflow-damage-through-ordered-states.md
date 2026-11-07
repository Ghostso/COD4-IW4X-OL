# 495 · **"IW4 的 `destructible_state` 把**溢出的伤害【穿过【有序的状态**，而【运行【每一个【进入的状态**的动作**"** —— `sv_destructible_mp.cpp` 的 `7` 个定义、`5` 个阶段、以及"一个负数【会【让那个循环【终止"

## 一、范围

本报告学习 `sv_destructible_mp.cpp`（**`281` 行**）全文件：`7` 个 `SvDestructibleDefinition`、`5` 组阶段、`SV_ApplyDestructibleDamage` 的溢出循环、`SV_ResolveDestructiblePresentation` 的一对一校验、以及 `SV_ApplyDestructibleEntityDamage` 的事件累积。

## 二、**"IW4 的 destructible_state 把溢出的伤害穿过有序的状态，而运行每一个进入的状态的动作"**（本组最重要的一段）

### 2.1 那段

```cpp
// CODREF(g_damage): IW4 destructible_state carries overflow damage
// through ordered states and runs every entered state action.
...
auto result = SvDestructibleDamageResult{ .state = state };
auto remainingDamage = static_cast<std::int64_t>(damage);
while (remainingDamage >= result.state.health)
{
    remainingDamage -= result.state.health;
    ++result.state.stageIndex;
    if (result.state.stageIndex == definition.stages.size())
    {
        result.state.health = 0;
        result.state.destroyed = true;
        result.enteredDestroyedState = true;
        return result;
    }
    result.state.health = definition.stages[result.state.stageIndex].health;
    result.enteredStages.push_back(result.state.stageIndex);
}
result.state.health -= static_cast<std::int32_t>(remainingDamage);
```

### 2.2 二十四层

```text
1. **那个溢出伤害【穿过【有序的状态**】
2. ⇒ **⇒ 而【运行【每一个【进入的状态**的动作**】
3. ⇒ **⇒ 所以【那个 `while` 【是一个**级联**的循环**
4. ⇒ **⇒ 而【那个 `>=` 【意味着【恰好打空一个阶段 【也【推进**】
5. ⇒ **⇒ 而【那个 `enteredStages.push_back` 【记录【每一个**穿过的阶段**
```

### 2.3 ⭐⭐⭐ **"恰好打空一个阶段也推进（`>=` 而不是 `>`）"**

**✅ 这是本报告里**最精确的一条**边界**。**

**✅ 与 §488 的"`distance == scaledRanges.back()` ⇒ 回落到 `damage[0]`"**——**同族** ✓

**⇒ 三层**：
```text
若【用 `>`**】⇒ **⇒ 恰好打空【停在【阶段 `0` 而【`health = 0`**】⇒ **⇒ 那【不是【一个合法的**状态**（那个校验【要求 `health > 0`**）
若【用 `>=`**】⇒ **⇒ 推进【到【阶段 `1`**】⇒ **⇒ 正确**
⇒ **⇒ 所以【那个 `>=` 【是【被【那个不变式**要求的**
```

**✅ ⭐⭐⭐ **"那个 >= 是被那个不变式要求的"** —— 一个**极精确的论证**。

**⚠ 而那个**入口校验**】**。**

**⇒ 十层**：
```cpp
state.health <= 0 ||
state.health > definition.stages[state.stageIndex].health
```
```text
`state.health <= 0` ⇒ **拒绝**】
`state.health > stages[stageIndex].health` ⇒ **拒绝**】
⇒ **⇒ 所以【那个 `health` 【总是【在 `(0, stages[stageIndex].health]`**里】
```

**✅ ⭐⭐⭐ **"那个 health 总是在 (0, stages[stageIndex].health] 里"** —— 一个**完整的**不变式**。

**✅ 与 §495 的"那个 `>=` 是被那个不变式要求的"**——**完全闭合** ✓

**⚠ 而"那个 `remainingDamage` 是 `int64`"**⇒ **一个**防溢出**的类型**。**

**⇒ 十层**：
```text
`damage` 是 `int32` ⇒ **⇒ 而【那个循环【可能【减【多个阶段**】
⇒ **⇒ 所以 `int64` 【防止【一个【大伤害**（**`INT32_MAX`**）【在【减法中**溢出**
```

**✅ ⭐⭐⭐ **"int64 防止一个大伤害在减法中溢出"** —— 与 §476 的"`uint64` 相加 + `min`"**同族**（**第六次"一个**更宽的中间类型**"**）。

## 三、**五组阶段与 `7` 个定义**（本组第二重要）

### 3.1 那七行

```text
toy_tv_flatscreen_wallmount_01        FlatscreenStages    {1, 200}                 destroyed: (空)
toy_transformer_small01               TransformerStages   {75,75,150,250,400}      "utility_transformer_small01_dest"
toy_light_ceiling_fluorescent_single  FluorescentStages   {150}                    "me_lightfluohang_single_destroyed"
vehicle_80s_sedan1_red                SedanStages         {250,200,100,300,400}    "vehicle_80s_sedan1_red_destroyed"
vehicle_80s_sedan1_green              SedanStages         (同上)                   "vehicle_80s_sedan1_green_destroyed"
vehicle_80s_sedan1_brn                SedanStages         (同上)                   "vehicle_80s_sedan1_brn_destroyed"
vehicle_pickup                        PickupStages        {300,200,100,300,400}    "vehicle_pickup_destroyed"
```

### 3.2 二十四层

```text
1. **七行，而【那三个**轿车【共享【`SedanStages`**】
2. ⇒ **⇒ 而 `PickupStages` 【是【一个**独立的**数组**】（**尽管【数值【一样**）
3. ⇒ **⇒ 而【那个 `FlatscreenStages` 的**第一阶段是 `1`**】
4. ⇒ **⇒ 所以【一击（`damage = 1`）【就会【打空**那个 `1`】
```

### 3.3 ⭐⭐⭐ **"那个平板电视的第一阶段是 1 —— 一击就打空"**

**✅ 与 §495 二 的 `>=`**——**完全联合** ✓

**⇒ 三层**：
```text
`{1, 200}` ⇒ **⇒ 第一阶段 `1`**】⇒ **⇒ 而【`damage = 1` ⇒ `1 >= 1` ⇒ 【推进**
⇒ **⇒ 所以【一击【就【换**【那个 `ma_flatscreen_tv_wallmount_broken_01`**】
⇒ **⇒ 而【第二阶段【是 `200`**】⇒ **⇒ 所以【那个电视【被【一击【打破【然后【需要 `200` 更多**
```

**✅ ⭐⭐⭐ **"一击打破然后需要 200 更多"** —— 一个**极精确的语义**。

**⚠ 而那个**总血量的差异**】**。**

**⇒ 独立核算**：
```text
Flatscreen  ⇒ `1 + 200 = 201`
Transformer ⇒ `75 + 75 + 150 + 250 + 400 = 950`
Fluorescent ⇒ `150`
Sedan       ⇒ `250 + 200 + 100 + 300 + 400 = 1250`
Pickup      ⇒ `300 + 200 + 100 + 300 + 400 = 1300`
⇒ **⇒ 所以【五个**不同的总血量**】
```

**✅ ⭐⭐⭐ **"五个不同的总血量：201/950/150/1250/1300"** —— 一个**精确的算术**。

**✅ 与 §414 的"`373` eType-6 / `238` brush"**——**同族**（**第三次"一个**可核算的**计数**"**）。

**⚠ 而 `SedanStages` 与 `PickupStages` 的**数值相同**】**。**

**⇒ 十层**：
```text
`Sedan = {250,200,100,300,400}` / `Pickup = {300,200,100,300,400}`
⇒ **⇒ 差 `50` 在【第一个**
⇒ **⇒ 所以【两个**不是**同一个数组**】（**`Sedan` 是 `250`，`Pickup` 是 `300`**）
```

**✅ ⭐⭐⭐ **"差 50 在第一个：Sedan 是 250，Pickup 是 300"** —— 一个**极精细的观察**（**我前面写"数值一样"是错的**）**。

**⚠ 修正**：`Sedan = {250,200,100,300,400}` 总和 `1250`；`Pickup = {300,200,100,300,400}` 总和 `1300` ⇒ **差 `50`**。

**✅ 而那个**三个轿车共享一个数组**】**。**

**⇒ 三层**：
```text
`SedanStages` ⇒ **一个**数组**，`3` 个**定义【引用它
⇒ **⇒ 所以【改一处【会【改【三个**颜色**
⇒ **⇒ 那【是【一个**正确的**抽象**（**三个颜色【同一个结构**）
```

**✅ ⭐⭐⭐ **"三个颜色同一个结构"** —— 而**注释【说**"health sequences come from IW4's original `_destructible.gsc`"**。**

## 四、**一一对应的校验：`hasName != modelIndex.has_value()`**（本组第三重要）

### 4.1 那段

```cpp
for (std::size_t index{}; index < definition.stages.size(); ++index)
{
    const auto hasName = !definition.stages[index].replacementModel.empty();
    const auto modelIndex = presentation.stageModelIndexes[index];
    if (hasName != modelIndex.has_value() || (modelIndex && !*modelIndex))
    {
        return false;
    }
}
const auto hasDestroyedModel = !definition.destroyedModel.empty();
return hasDestroyedModel == presentation.destroyedModelIndex.has_value() &&
    (!presentation.destroyedModelIndex || *presentation.destroyedModelIndex != 0);
```

### 4.2 二十四层

```text
1. **每一个阶段【有一个**名字【则【必须【有一个索引**】⇒ **⇒ 而【反之**亦然**】
2. ⇒ **⇒ 所以【那个 `!=` 【是【一个**双条件**
3. ⇒ **⇒ 而 `modelIndex && !*modelIndex` ⇒ 拒绝**】（**⇒ 一个索引【为 `0` 【是【无效的**）
4. ⇒ **⇒ 而那个 destroyed 【也一样**】
```

### 4.3 ⭐⭐⭐ **"一个有名字就必须有一个非零索引，而一个没有名字就必须没有索引"**

**✅ 与 §473 的"每一个 image 必须在那 17 个里"**、§487 的"那个 bundle 不暂存的图"**——**同族** ✓

**⇒ 三层**：
```text
§473/§487  **一个**名字【必须有【一个**资产**
§495  **一个**名字【必须有【一个**索引**，而【一个索引【必须**非零**
⇒ **⇒ 三次"一个**名字【必须【有一个**非零的实现**"**
```

**✅ ⭐⭐⭐ **"一个名字必须有一个非零的实现"三例**。

**⚠ 而那个 `!=` 的**双向**】**。**

**⇒ 十层**：
```text
`hasName != modelIndex.has_value()` ⇒ **⇒ 若【`hasName == true` 而【索引**缺失**】⇒ **拒绝**
                                      ⇒ **⇒ 若【`hasName == false` 而【索引**存在**】⇒ **拒绝**
⇒ **⇒ 所以【一个**双条件**
```

**✅ ⭐⭐⭐ **"一个双条件"**。

**✅ 与 §495 二 的"一个不变式"**——**同族**（**第四次"一个**双向的**检查**"**）。

## 五、**`enteredStages` 的事件累积与"那个最后进入的模型胜"**

### 5.1 那段

```cpp
std::optional<std::uint16_t> modelIndex;
if (result->enteredDestroyedState)
{
    modelIndex = presentation.destroyedModelIndex;
}
else
{
    for (const auto enteredStage : result->enteredStages)
    {
        if (presentation.stageModelIndexes[enteredStage])
            modelIndex = presentation.stageModelIndexes[enteredStage];
    }
}
```

### 5.2 二十四层

```text
1. **`enteredDestroyedState` ⇒ 用【那个**销毁的**模型**】
2. ⇒ **⇒ 否则【遍历 `enteredStages`**】⇒ **⇒ 而【每一个**有索引的阶段【覆盖** `modelIndex`】
3. ⇒ **⇒ 所以【那个**最后进入的**阶段【胜**】
```

### 5.3 ⭐⭐⭐ **"那个最后进入的阶段胜"**

**✅ 与 §467 的"`SvMapEntity::value` 从 `rbegin()` 找 ⇒ 最后一次胜"**、§494 的"The LAST one wins"**——**完全同族** ✓

**⇒ 三层**：
```text
§467  **`rbegin()`**（**键内重复**）
§494  **"The LAST one wins"**（**模型名的性别**）
§495  **`for (enteredStage : enteredStages) modelIndex = ...`**（**阶段的事件**）
⇒ **⇒ 三次"最后胜"**
```

**✅ ⭐⭐⭐ **"最后胜"三例表**。

**⚠ 而那个**只覆盖有索引的阶段**】**。**

**⇒ 十层**：
```cpp
if (presentation.stageModelIndexes[enteredStage])
    modelIndex = presentation.stageModelIndexes[enteredStage];
```
```text
1. **只在【那个阶段【有索引**时【覆盖】
2. ⇒ **⇒ 所以【一个**无索引的**阶段【不【清除**那个 `modelIndex`**】
3. ⇒ **⇒ 而那【意味着【那个模型【保持**上一个有索引的**】
```

**✅ ⭐⭐⭐ **"一个无索引的阶段不清除那个 modelIndex —— 那意味着那个模型保持上一个有索引的"** —— 一个**极精确的语义**。

**✅ 与 §495 三 的"一个没有名字就必须没有索引"**——**完全联合** ✓

**⇒ 三层**：
```text
`{1, {}}` ⇒ **无索引**
`{200, "ma_flatscreen_..."}` ⇒ **有索引**
⇒ **⇒ 所以【那个电视【在【阶段 `0` 【保持【那个原始**模型**】⇒ **⇒ 而【在【阶段 `1` 【切【那个**破碎**的
```

**✅ ⭐⭐⭐ **"在阶段 0 保持原始模型，在阶段 1 切破碎的"**。

**⚠ 而那个**事件累积**】**。**

**⇒ 十层**：
```cpp
for (const auto enteredStage : result->enteredStages)
{
    mutation.presentationEvents.insert(
        mutation.presentationEvents.end(),
        presentation.stageEvents[enteredStage].begin(),
        presentation.stageEvents[enteredStage].end());
}
if (result->enteredDestroyedState)
{
    mutation.presentationEvents.insert(..., presentation.destroyedEvents.begin(), ...);
}
```
```text
1. **每一个进入的阶段【的事件【全部**累积**
2. ⇒ **⇒ 而【那个销毁【的事件【最后**加**
3. ⇒ **⇒ 所以【一个大伤害【会【触发【多个**阶段的事件**】
```

**✅ ⭐⭐⭐ **"一个大伤害会触发多个阶段的事件"** —— 与 §495 二 的"运行每一个进入的状态的动作"**完全闭合** ✓

**✅ 而那个**顺序**【是 `enteredStages` 的顺序**】⇒ **⇒ 一个**时间序**。**

**⇒ 三层**：
```text
`enteredStages` ⇒ **按【推进【顺序** push**】
⇒ **⇒ 所以【那个 `insert` 【保持**时间序**
⇒ **⇒ 而【那个**销毁事件【在【最后**
```

**✅ ⭐⭐⭐ **"那个销毁事件在最后"**。

## 六、`SV_IsDestructibleDefinitionValid` 的三条

### 6.1 三条

```cpp
return !definition.type.empty() && !definition.stages.empty() &&
    std::ranges::all_of(definition.stages, [](const auto &stage) {
        return stage.health > 0;
    });
```

### 6.2 二十四层

```text
1. **`type` 非空**】
2. ⇒ **⇒ `stages` 非空**】
3. ⇒ **⇒ 而【每一个 `health > 0`**】
4. ⇒ **⇒ 所以【那个 `> 0` 【是【那个 `>=` 循环【的一个**必要前提**
```

### 6.3 ⭐⭐⭐ **"每一个 health > 0"是那个 `while` 终止的必要前提**

**✅ 与 §495 二 的"那个 `>=` 是被那个不变式要求的"**——**完全联合** ✓

**⇒ 三层**：
```text
若【一个 `health == 0`**】⇒ **⇒ 那个 `while (remaining >= 0)` 【永远**真**】⇒ **⇒ 一个**无限循环**
⇒ **⇒ 所以【那个 `> 0` 【是【一个**终止性**的条件**
```

**✅ ⭐⭐⭐ **"那个 > 0 是一个终止性的条件"** —— 一个**极精确的观察**。

**✅ 与 §468 的"`p == storage.size()` 是唯一的完全理解证明"**——**不同**（那是一个**正确性**，这是一个**终止性**）但**同族**（**第七次"一个**前置条件【是【一个**可判定性**"**）。

**⚠ 而那个 `stages[stageIndex].health` 的**递增**假设**】**。**

**⇒ 十层**：
```text
`Flatscreen {1, 200}` ⇒ **递增**
`Transformer {75,75,150,250,400}` ⇒ **不递减**
`Sedan {250,200,100,300,400}` ⇒ **`250 → 200 → 100` 递减**！
⇒ **⇒ ⚠ 而那个 `while` 仍然【终止**】（**因为【每个 `> 0`**）
```

**✅ ⭐⭐⭐ **"那个 Sedan 的 250 → 200 → 100 递减，而那个 while 仍然终止"** —— 一个**极重要的观察**（**那个循环【不【要求【单调**）**。**

**✅ 与 §495 三 的"`Sedan = {250,200,100,300,400}`"**——**完全一致**。

## 七、那个 `TODO(CODOL)` 的"stage collision, part/tag mutation, animation, explosion radius damage and specialized vehicle behavior"

### 7.1 那段

```cpp
// TODO(CODOL): stage collision, part/tag mutation, animation, explosion
// radius damage and specialized vehicle behavior are not represented by
// this model/event-only plan and must not be inferred from type names.
```

### 7.2 二十四层

```text
1. **五样东西【不【被【这个"仅模型/事件"**的计划【表示**
2. ⇒ **⇒ ① stage collision**（**阶段碰撞**）
3. ⇒ **⇒ ② part/tag mutation**（**部件/骨骼标签变更**）
4. ⇒ **⇒ ③ animation**（**动画**）
5. ⇒ **⇒ ④ explosion radius damage**（**爆炸半径伤害**）
6. ⇒ **⇒ ⑤ specialized vehicle behavior**（**专用车辆行为**）
7. ⇒ **⇒ 而【它们【**不能【从类型名【推断**
```

### 7.3 ⭐⭐⭐ **"它们不能从类型名推断"**

**✅ 与 §473 的"那是一个更弱的血统证据"**、§483 的"不发明一个武器身份"**——**完全同族** ✓

**⇒ 三层**：
```text
"仅模型/事件" ⇒ **一个**显式的**范围**
⇒ **⇒ 而【那五样【必须【从【别的地方**【得到**】
⇒ **⇒ 所以【"不能从类型名推断"**是【那个**范围【的**守卫**
```

**✅ ⭐⭐⭐ **"'不能从类型名推断'是那个范围的守卫"** —— 与 §477 的"命名并过滤，而不是解码"**同族**。

**✅ 与 §468 的"没有见证的值故意缺席"**——**完全一致**（**第六次**）。

**⚠ 而那个 `"destruction"` 的**表现**】**。**

**⇒ 十层**：
```text
那个 `destroyedEvents` / `stageEvents` ⇒ **⇒ 从【`presentation` 来**】（**不是【从【定义来**）
⇒ **⇒ 所以【那个定义【只【有**健康序列 + 名字**】
⇒ **⇒ 而【事件【是【一个**外部的**注入**
```

**✅ ⭐⭐⭐ **"那个定义只有健康序列 + 名字，而事件是一个外部的注入"**。

## 八、`SV_FindIw4DestructibleDefinition` 的"一个按类型的查找"

### 8.1 那段

```cpp
const SvDestructibleDefinition *SV_FindIw4DestructibleDefinition(const std::string_view type)
{
    const auto definition = std::ranges::find(Definitions, type, &SvDestructibleDefinition::type);
    return definition != Definitions.end() ? &*definition : nullptr;
}
```

### 8.2 二十四层

```text
1. **一个线性查找**】（`std::ranges::find`**）**
2. ⇒ **⇒ 而 `7` 个定义【⇒ 最坏 `7` 次比较**】
3. ⇒ **⇒ 所以【不需要【一个**哈希表**
```

### 8.3 ⭐⭐⭐ **"七个定义，一个线性查找"**

**✅ 与 §486 的"`bones 7,5,6,4` 的一个小数组"**——**同族**（**第十次"一个**小集合【用**线性**"**）。

**⚠ 而那个**返回 `nullptr`** 的契约**】**。**

**⇒ 十层**：
```text
`definition != Definitions.end() ? &*definition : nullptr`
⇒ **⇒ 所以【一个**不在表里**的类型【得到 `nullptr`**】
⇒ **⇒ 而【那【是【一个**明确的**失败**】（**不是【一个默认**）
```

**✅ ⭐⭐⭐ **"那是一个明确的失败，不是一个默认"** —— 与 §468 的"没有见证的值故意缺席"**完全同族** ✓

**⇒ 三层**：
```text
§468  **"an unmapped string is rejected rather than defaulted"**
§494  **"it is absent below rather than substituted"**
§495  **`nullptr` for an unknown type**
⇒ **⇒ **四次**"一个**未知的类型【被【拒绝**"**
```

**✅ ⭐⭐⭐ **"一个未知的类型被拒绝"四例表**。

## 九、关键结论

1. **⭐⭐⭐ "IW4 的 `destructible_state` 把**溢出的伤害【穿过【有序的状态**，而【运行【每一个【进入的状态**的动作**"`** ⇒ **"那个 `>=` 是被那个不变式要求的"**：那个入口校验 `health > 0 && health <= stages[i].health` 意味着恰好打空一个阶段必须**推进**（否则 `health == 0` 非法）；而 `remainingDamage` 用 `int64` 防止一个大伤害在减法中溢出（**第六次"一个更宽的中间类型"**，与 §476 同族）。
2. **⭐⭐⭐ 七行定义、五组阶段**：`Flatscreen {1,200}` / `Transformer {75,75,150,250,400}` / `Fluorescent {150}` / `Sedan {250,200,100,300,400}` / `Pickup {300,200,100,300,400}` ⇒ **独立算得五个总血量 `201`/`950`/`150`/`1250`/`1300`**；而 **`Sedan` 与 `Pickup` 差 `50` 在第一个（`250` vs `300`）—— 不是同一个数组**；而 **三个轿车共享 `SedanStages`**（"三个颜色同一个结构"）。
3. **⭐⭐⭐ "那个平板电视的第一阶段是 1 —— 一击就打空"** ⇒ **"一击打破然后需要 200 更多"**（`{1, 200}`）。
4. **⭐⭐⭐ 一一对应的校验**：`hasName != modelIndex.has_value() || (modelIndex && !*modelIndex)` ⇒ **"一个双条件"**（**一个有名字就必须有一个非零索引，而一个没有名字就必须没有索引**）—— 与 §473/§487 的"一个名字必须有一个非零的实现"同族。
5. **⭐⭐⭐ `enteredStages` 的模型选择：那个最后进入的阶段胜**（与 §467 的 `rbegin()`、§494 的"The LAST one wins"**三次"最后胜"**）；而 **"一个无索引的阶段不清除那个 modelIndex —— 那意味着那个模型保持上一个有索引的"** ⇒ **"在阶段 0 保持原始模型，在阶段 1 切破碎的"`**。
6. **⭐⭐⭐ 事件累积**：每一个进入的阶段的事件全部累积（`enteredStages` 是按推进顺序 push 的 ⇒ 保持时间序），而销毁事件**最后加** ⇒ **"一个大伤害会触发多个阶段的事件"**（与 §495 二 的"运行每一个进入的状态的动作"完全闭合）。
7. **⭐⭐⭐ `SV_IsDestructibleDefinitionValid` 的"每一个 `health > 0`"是那个 `while` 终止的必要前提** ⇒ **"那个 > 0 是一个终止性的条件"**；而 **`Sedan` 的 `250 → 200 → 100` 是递减的，而那个循环仍然终止**（因为每个 `> 0`）⇒ **一个极重要的观察：那个循环不要求单调**。
8. **⭐⭐⭐ `TODO(CODOL)` 的五样**（stage collision / part/tag mutation / animation / explosion radius damage / specialized vehicle behavior）⇒ **"都是不被这个『仅模型/事件』的计划表示，且不能从类型名推断"** ⇒ **"'不能从类型名推断'是那个范围的守卫"**（与 §468/§477 同族）；而 **那个定义只有健康序列 + 名字，而事件是一个外部的注入**。
9. **⭐⭐⭐ `SV_FindIw4DestructibleDefinition` 返回 `nullptr` 而不是默认** ⇒ **"一个未知的类型被拒绝"**（**四例表**，与 §468/§494 同族）。

## 十、`sv_destructible_mp.cpp` 全文件总览

**`281` 行。**

**`5` 组阶段 + **`7` 个定义**（三个轿车共享一组）。

**`6` 个函数**：`SV_IsDestructibleDefinitionValid` / `SV_InitializeDestructible` / `SV_ApplyDestructibleDamage` / `SV_InitializeDestructibleDamageState` / `SV_IsResolvedDestructiblePresentationValid` / `SV_ResolveDestructiblePresentation` / `SV_ApplyDestructibleEntityDamage` / `SV_FindIw4DestructibleDefinition`。

**`7` 个模型名**：
```text
ma_flatscreen_tv_wallmount_broken_01
utility_transformer_small01_dest
me_lightfluohang_single_destroyed
vehicle_80s_sedan1_red_destroyed
vehicle_80s_sedan1_green_destroyed
vehicle_80s_sedan1_brn_destroyed
vehicle_pickup_destroyed
```

**`5` 个总血量**：`201` / `950` / `150` / `1250` / `1300`。

## 十一、未闭合点

- `SvDestructibleDefinition` 是否还有别的字段（`.hpp` 里）。
- `stageEvents` / `destroyedEvents` 的注入者。
- CODOL 的 `crash` MapEnts 里实际的 destructible 类型清单（那 7 个是"observed in CODOL crash MapEnts"）。
- 下一个文件：`sv_playlist_mp.cpp`（`10,509` 字节）。
