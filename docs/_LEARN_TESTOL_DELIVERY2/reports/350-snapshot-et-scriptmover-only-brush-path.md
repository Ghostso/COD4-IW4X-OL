# 350 · **"`ET_SCRIPTMOVER` 而不是 `ET_GENERAL`，而这就是【门不可见】的原因"** —— `sub_1F2EF0` 是唯一到达 `R_AddBrushModelToScene` 的路径、`373/238` 的零售对照、`0x00FFFFFF` 的 solid

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 11600–12000 行。

## 二、**`ET_SCRIPTMOVER` 是唯一到达画笔模型的路径**（本组最重要的一段）

### 2.1 那段

```php
// ET_SCRIPTMOVER, NOT ET_GENERAL, AND THIS IS WHY THE DOORS WERE
// INVISIBLE. sub_1F2EF0 -- the ET_SCRIPTMOVER presentation handler --
// is the ONLY path that reaches R_AddBrushModelToScene (sub_1E54E0),
// and it takes it when `es.solid == 0xFFFFFF`, drawing
// `world->bmodels + 60 * modelIndex`. ET_GENERAL's handler
// (sub_1F1820) has no brush branch at all, so every brush model this
// server published was received, stored and never drawn.
//
// Retail agrees: all 373 ET_SCRIPTMOVER entries in factory's shipped
// const-baseline table are eType 6, and the 238 with a brush model
// index are exactly the 238 carrying 0x00FFFFFF.
```

### 2.2 十二层

```text
1. **`ET_SCRIPTMOVER` 而不是 `ET_GENERAL`，而这就是【门不可见】的原因**
2. ⇒ **`sub_1F2EF0` —— `ET_SCRIPTMOVER` 的表现处理器 —— 是【唯一】到达 `R_AddBrushModelToScene`（`sub_1E54E0`）的路径**
3. ⇒ **而它在 `es.solid == 0xFFFFFF` 时走它**
4. ⇒ **画 `world->bmodels + 60 * modelIndex`**
5. ⇒ **`ET_GENERAL` 的处理器（`sub_1F1820`）【根本没有画笔分支】**
6. ⇒ **所以这个服务器发布的每一个画笔模型都被接收了、存储了、而【从未被画】**
7. ⇒ **零售同意**：factory 已发货 const 基线表里的**全部 373 个 `ET_SCRIPTMOVER` 条目都是 eType 6**
8. ⇒ **而【带画笔模型索引的 238 个恰好是携带 `0x00FFFFFF` 的那 238 个】**
```

### 2.3 **"被接收了、存储了、而从未被画"**

**✅ 这是"沉默读起来像健康"的**第八次**（也是最纯粹的一次）。**

**⇒ 六层：**

```text
1. 服务端发布 ✓
2. ⇒ 客户端接收 ✓
3. ⇒ 客户端存储 ✓
4. ⇒ **客户端不画** ✗
5. ⇒ **没有错误、没有日志、快照 ack 正常**
6. ⇒ **只有"东西不在那里"这一个症状**
```

**✅ 与 §322 的"allowlist 让僵尸从不画"、§345 的"控制台成了僵尸身体"**同族。**

**⇒ **三次不同的"接收但不画"。**

### 2.4 而 `sub_1F2EF0` 与 `sub_1F1820`

```text
sub_1F2EF0    ET_SCRIPTMOVER 表现处理器    有画笔分支
sub_1F1820    ET_GENERAL 表现处理器        无画笔分支
sub_1E54E0    R_AddBrushModelToScene
```

**✅ 与 §343 的"`0x00DA6828` 是本 build 的 ET_SCRIPTMOVER 表"**配合。**

**⚠ 而两个地址在 `0x1F2EF0` / `0x1F1820` 区间 —— 与 §342 的 `0x6701D0`/`0x671170` 完全不同的地址空间。**

**⇒ 所以那两个是**渲染侧**（renderer），而 `0x67xxxx` 是**消息侧**（msg）。**

**✅ 一个清晰的分层。**

### 2.5 而 **`es.solid == 0xFFFFFF`**

**⇒ 三层**：

```text
1. **`solid == 0xFFFFFF` 是走画笔分支的条件**
2. ⇒ **24 位全一**
3. ⇒ 与 §343 的 `writeUnsignedDelta(..., solid, ..., 24)` **完全一致 ✓**
```

**✅ **第二次确认 `solid` 的 24 位。**

**⚠ 而 §342 的 `validItemEntity` 要求 `solid == 0`。**

**⇒ 所以 `0`（无碰撞）与 `0xFFFFFF`（画笔模型）是**两个极端**。**

**✅ 与 §342 的"`EntityNumWorld` 与零是两个语义"同族。**

### 2.6 而 **`world->bmodels + 60 * modelIndex`**

**⇒ 三层**：

```text
1. **`bmodels` 数组的 stride 是 60**
2. ⇒ **按 `modelIndex` 索引**
3. ⇒ **而 `modelIndex` 在这里是 `scriptMoverBrushModelIndex`（字段 26）**
```

**⚠ 而 §343 说"字段 26 是 `scriptMoverBrushModelIndex`" ✓**

**✅ 而 `60` 是**`bmodel` 结构的大小**（字节）。**

**⚠ 与 §339 的 `0x160 = 352`（clientInfo）、§345 的 `280`（entityState）**不同。**

**⇒ 三个尺寸。**

### 2.7 而 **`373` 与 `238`**

```text
373    factory const 基线表里的 ET_SCRIPTMOVER 条目（全部 eType 6）
238    带画笔模型索引的
       ⇒ 恰好是携带 0x00FFFFFF 的那 238 个
```

**✅ 一个**双向精确的对照**（373 ⊇ 238，而 238 = 携带 `0xFFFFFF` 的）。**

**⚠ 而 §343 说"237 个画笔模型一个坐标都不发而看起来正确"。**

**⇒ **237 vs 238**（差一）。**

**⚠ 一处**需要核对的差异**。**

**⇒ 可能 §343 的 237 是**本服务器**发布的，而这里的 238 是**零售表的**。**

**✅ 一个合理的解释。**

### 2.8 而**字段 26 而非字段 19**

```php
// Field 26 (+0x09C), NOT field 19 (+0x05C). A brush model has no
// XModel -- retail leaves +0x05C zero on all 238 -- so `modelIndex`
// stays unset and the clip handle goes in its own field.
entity.networkState.scriptMoverBrushModelIndex =
    definition.gameplayActive ? (uint16)definition.collision.clipHandle : 0;
```

**⇒ 五层**：

```text
1. **字段 26（`+0x09C`），不是字段 19（`+0x05C`）**
2. ⇒ **一个画笔模型没有 XModel**
3. ⇒ **零售在全部 238 个上把 `+0x05C` 留为零**
4. ⇒ **所以 `modelIndex` 保持未设**
5. ⇒ **而 clip handle 进它自己的字段**
```

**✅ 与 §344 的"`+0x9C` 在 ET_ITEM 上是武器/物品行"**完全一致 ✓**

**⇒ 而这里是 `+0x09C` 在 **ET_SCRIPTMOVER** 上是**画笔模型索引**。**

**⚠ 所以**同一个偏移三个语义**：**

```text
ET_SCRIPTMOVER  +0x09C = 画笔模型索引（clip handle）
ET_ITEM         +0x09C = 武器/物品行
（§344 只说了两个）
```

**✅ **第四次"一个成员多个语义"。**

## 三、**"一个画笔模型偏离表就推翻整帧的标志"**（本组第二重要）

### 3.1 那段

```php
// ONE BRUSH MODEL OFF THE TABLE DISQUALIFIES THE WHOLE FRAME'S FLAG.
// Bit 0x10 is set per snapshot, not per entity, so it cannot be right
// for the 237 that matched and harmless for the one that did not -- the
// odd one out would resolve against whichever entity retail put on its
// invented number.
auto everyBrushModelOnRetailNumber = constBaselines != nullptr;
```

### 3.2 七层

```text
1. **一个画笔模型偏离表就【推翻整帧的标志】**
2. ⇒ **位 `0x10` 是【按快照】设的，不是按实体**
3. ⇒ **所以它不能对匹配的 237 个是对的而对不匹配的那一个无害**
4. ⇒ **那个异类会对着零售在它【臆造的数字】上放的任何一个实体解析**
5. ⇒ 所以 `everyBrushModelOnRetailNumber` 需要**全部匹配**
```

**✅ 与 §347 五 的"基线是消息级的"**完全同族（**第三次**）。**

**⇒ **"一个全帧标志必须对全帧正确"** —— 一个**逻辑上显而易见的而实现上容易漏的**要求。**

### 3.3 而**脚本模型"被计数而不是被要求"**

```php
// Script models are counted, not required. Unlike brush models -- whose `*N` keys
// the table exactly -- some props cannot be resolved to a single row, and those
// stay on sequential numbers OUTSIDE the table, where the client resolves a zeroed
// baseline and this server deltas against zero. The two still agree, so the flag
// stays valid; only the wire cost is higher for those few.
std::size_t scriptModelsOnRetailNumbers = 0;
```

**⇒ 九层**：

```text
1. **脚本模型被【计数】，而不是被【要求】**
2. ⇒ **不像画笔模型 —— 它们的 `*N` 精确对应表**
3. ⇒ **有些道具无法解析到单独一行**
4. ⇒ **而那些留在【表外】的顺序编号上**
5. ⇒ **在那里客户端解析一个【被归零的】基线**
6. ⇒ **而这个服务器对着【零】做 delta**
7. ⇒ **两者仍一致**
8. ⇒ **所以标志保持有效**
9. ⇒ **只对那几个来说线成本更高**
```

**✅ 一个**极精细的不对称**：**

```text
画笔模型   `*N` 精确对应 ⇒ 必须全部匹配表
脚本模型   有些道具无法单行解析 ⇒ 允许表外
```

**⚠ 而"表外 ⇒ 零基线"是一个**关键推理**：**

```text
客户端对表外的号 ⇒ cl.entityBaselines[n] 未初始化 ⇒ 零
而我们对着零 delta ⇒ 一致 ✓
```

**✅ **完整闭合。**

## 四、**"零售的号对这个 `*N`，而不是下一个空闲的"**

```php
// RETAIL'S NUMBER FOR THIS `*N`, NOT THE NEXT ONE FREE. The client
// keys cl.entityBaselines by entity number, so on a map whose table
// this build ships the number IS the entity's identity and cannot be
// an allocation detail. Maps without a table fall back to sequential
// numbering: the brush model still renders, because every field its
// render path needs is written explicitly below, but the entity will
// not line up with the client's own baseline for that number.
const auto retailEntityNum = SV_ConstBaselineBrushModelEntityNum(
    constBaselines, definition.collision.clipHandle);
if (!retailEntityNum) everyBrushModelOnRetailNumber = false;
const auto handle = retailEntityNum
    ? stagedPool->spawnAt(*retailEntityNum, snapshot_.serverTime)
    : stagedPool->spawn(snapshot_.serverTime);
```

### 4.1 九层

```text
1. **零售对这个 `*N` 的号，不是下一个空闲的**
2. ⇒ **客户端按实体号键 `cl.entityBaselines`**
3. ⇒ **所以在一张本 build 发过表的图上，那个号【就是实体的身份】**
4. ⇒ **而不能是一个分配细节**
5. ⇒ **没有表的图回退到顺序编号**
6. ⇒ **画笔模型仍渲染，因为它渲染路径需要的每个字段都在下面被显式写出**
7. ⇒ **但那个实体不会与客户端自己那个号的基线对齐**
8. ⇒ 所以 `spawnAt(retailNum)` 或 `spawn()`（顺序）
```

### 4.2 而 **"号就是实体的身份"**

**✅ 这是本文件里对 `sv_const_baselines` 机制**最清晰的陈述**。**

**⇒ 三层**：

```text
1. 客户端按号索引基线
2. ⇒ **所以号 = 身份**
3. ⇒ **不是"分配细节"**
```

**✅ 与 §345 的"客户端的基线 xmodel 不是文件的 xmodel"**互补：**

```text
§345  号的意义：客户端重新解析模型进自己的 configstring 带
§350  号的身份：客户端按号索引 cl.entityBaselines
```

**✅ **两个维度都指向"号有语义"。**

### 4.3 而 **`spawnAt` vs `spawn`**

```text
spawnAt(num)  指定号（零售表里有的）
spawn()       顺序（表外的脚本模型、或没有表的图）
```

**✅ 与 §349 的 `entityPool_.reset()` **配合。**

### 4.4 而**"withhold 每一个零售表点名的号"**

```php
// WITHHOLD EVERY NUMBER RETAIL'S TABLE NAMES, not just the brush models'.
// The client resolves ANY entity carrying snapshot flag 0x10 against
// cl.entityBaselines by number, so a dynamic entity that landed on a
// script_model's or an fx's number would inherit that entity's origin
// and model. The gaps in the table are numbers nothing static occupies
// and they stay available to sequential allocation.
for (const auto &entry : constBaselines->entries) {
    if (entry.entityNum < firstDynamicEntityNum) continue;
    if (!stagedPool->reserve(entry.entityNum)) return false;
    if (entry.entityNum >= stagedActorEntityFloor) stagedActorEntityFloor = entry.entityNum + 1;
}
```

### 4.5 八层

```text
1. **扣留零售表点名的【每一个】号，不只是画笔模型的**
2. ⇒ **客户端对着 `cl.entityBaselines` 按号解析【任何】携带标志 `0x10` 的实体**
3. ⇒ **所以一个落在 script_model 或 fx 的号上的动态实体**
4. ⇒ **会【继承那个实体的 origin 与 model】**
5. ⇒ **表里的【空隙】是什么静态都不占的号**
6. ⇒ **而它们保持可用于顺序分配**
7. ⇒ 所以 `reserve(entry.entityNum)` 保留每一个表里的号
8. ⇒ **而 `stagedActorEntityFloor = max(entry.entityNum + 1)`**
```

**✅ 与 §345 的"用实体自己的 model 索引让字段等于基线"**同族（**同一机制的两个方向**）：**

```text
§345  我们不发的字段 ⇒ 客户端用自己的（对的）
§350  我们发但号错了 ⇒ 客户端用别的实体的（错的）⇒ 所以扣留
```

**✅ **两个防御方向。**

### 4.6 而 **`stagedActorEntityFloor` 的注释**

```php
// ONE PAST THE TABLE'S HIGHEST NUMBER. Retail's actors live
// above the map's static entities -- see actorEntityFloor_ for
// what that is and is not evidence of.
```

**⇒ 四层**：

```text
1. **表的最高号再加一**
2. ⇒ **零售的 actor 住在地图的静态实体之上**
3. ⇒ **见 `actorEntityFloor_` 了解那是什么、以及不是什么证据**
4. ⇒ **一个谨慎的"这不是证据"声明**
```

**✅ 与 §344 的"`488..815` 对 factory 的 `625`"**同族。**

**⚠ 而"是什么以及不是什么证据"是一个**极罕见的自我限制**。**

**⇒ 与 §340 的"定向的负面"、§347 的"这是线半"**第三次"声明证据边界"**。

## 五、`validScriptModel` 的**七项**

```cpp
const auto validScriptModel = [&finiteVector](const auto &definition) {
    return definition.modelIndex > 0 &&
        definition.modelIndex < ModelConfigStringCount &&
        !definition.modelName.empty() &&
        definition.modelName.front() != '*' &&
        definition.modelName.find('\0') == std::string::npos &&
        std::isfinite(definition.scale) && definition.scale > 0.0f &&
        finiteVector(definition.origin) &&
        finiteVector(definition.angles) &&
        (definition.mapModeEligible || !definition.gameplayActive);
};
```

### 5.1 九项

```text
① modelIndex > 0
② modelIndex < ModelConfigStringCount（1024）
③ modelName 非空
④ **modelName 首字符不是 `*`**   ← 画笔模型的前缀
⑤ modelName 不含 NUL
⑥ scale 有限且 > 0
⑦ origin 有限
⑧ angles 有限
⑨ **`mapModeEligible || !gameplayActive`**
```

### 5.2 而 ④ 的**"首字符不是 `*`"**

**✅ 一个**极强的区分**：**

```text
`*N`  = 画笔模型（内联几何）
非 `*` = xmodel
```

**✅ 与 §344 的"`*N` 精确对应表"**完全一致 ✓**

**⇒ **第二次确认 `*N` 是画笔模型前缀。**

### 5.3 而 ⑨ 的**"地图模式合格 或 不参与玩法"**

**⇒ 三层**：

```text
1. 若 `mapModeEligible` ⇒ 可以用
2. ⇒ 否则必须 `!gameplayActive`（纯装饰）
3. ⇒ **所以"参与玩法但地图模式不合格"⇒ 拒绝**
```

**✅ 与 `validScriptModel` 的**最后一项**是唯一的"策略"检查**（其它都是"数据合法性"）。**

## 六、`validLogicalMapEntity` 的**四项**

```cpp
const auto validLogicalMapEntity = [&finiteVector](const auto &definition) {
    const auto className = definition.value("classname");
    if (!className || className->empty() ||
        className->find('\0') != std::string_view::npos ||
        (definition.hasOrigin && !finiteVector(definition.origin)) ||
        (definition.hasAngles && !finiteVector(definition.angles)))
        return false;
    return std::ranges::all_of(definition.fields, [](const auto &field) {
        return !field.first.empty() && field.first.find('\0') == std::string_view::npos &&
            field.second.find('\0') == std::string_view::npos;
    });
};
```

**⇒ 六层**：

```text
① `classname` 必须存在且非空且不含 NUL
② `hasOrigin` ⇒ origin 必须有限
③ `hasAngles` ⇒ angles 必须有限
④ 每个字段的**名**非空且不含 NUL
⑤ 每个字段的**值**不含 NUL
```

**✅ 一个**字符串安全 + 数值合法性**的双重检查。**

**⚠ 而 NUL 检查出现**三次** ⇒ 说明**注入是真实威胁**（地图实体定义来自外部数据）。**

**✅ 与 AGENTS.md 的"下载的文件是不可信数据"**配合。**

## 七、`damageOwnersByModel` 的**四项检查**

```cpp
std::vector<const SvScriptModelDamageOwnerDefinition *> damageOwnersByModel(
    scriptModelDefinitions.size());
for (const auto &owner : scriptModelDamageOwners) {
    if (owner.scriptModelIndex >= scriptModelDefinitions.size() ||
        damageOwnersByModel[owner.scriptModelIndex] ||
        !SV_IsEntityDamageStateValid(owner.state) || !owner.handler)
        return false;
    const auto &model = scriptModelDefinitions[owner.scriptModelIndex];
    if (!model.gameplayActive || model.destructibleType.empty())
        return false;
    damageOwnersByModel[owner.scriptModelIndex] = &owner;
}
```

### 7.1 六层

```text
① 索引越界 ⇒ 拒
② **重复（已有非空指针）⇒ 拒**   ← 唯一性
③ state 非法 ⇒ 拒
④ handler 空 ⇒ 拒
⑤ **模型不参与玩法 ⇒ 拒**
⑥ **`destructibleType` 空 ⇒ 拒**
```

**✅ ⑥ 是一个**语义要求**："一个可破坏物的拥有者必须声明它的可破坏类型"。**

**⚠ 而 ⑤与⑥ 都要求**参与玩法**。**

**⇒ 所以"可破坏"与"参与玩法"是**同义**。**

## 八、`traceXxx` 的三个 runner 与**三个碰撞集**

```cpp
std::optional<TraceResult> tracePoint(const SvPointTraceRequest &request) const
{
    if (!pointTraceRunner_ || !SV_IsPointTraceRequestValid(request)) return std::nullopt;
    return pointTraceRunner_(request, glassState_, bulletCollisionEntities_);
}

std::optional<bool> traceRadiusDamageVisibility(const SvRadiusDamageTraceRequest &request) const
{
    if (!radiusDamageVisibilityRunner_ || !SV_IsRadiusDamageTraceRequestValid(request)) return std::nullopt;
    return radiusDamageVisibilityRunner_(request, glassState_, collisionEntities_);
}

std::optional<TraceResult> traceCapsule(const std::array<float,3> &start, ...) const
{
    if (!capsuleTraceRunner_ || !SV_IsTraceEntityFilterValid(filter)) return std::nullopt;
    return capsuleTraceRunner_(start, end, bounds, contentMask, glassState_, collisionEntities_, filter);
}
```

### 8.1 三个 trace、三个碰撞集

```text
tracePoint                 glassState_ + bulletCollisionEntities_     子弹
traceRadiusDamageVisibility glassState_ + collisionEntities_          范围伤害
traceCapsule               glassState_ + collisionEntities_ + filter  胶囊（角色）
```

**✅ 三个不同的碰撞集：**

```text
bulletCollisionEntities_          只挡子弹
collisionEntities_                挡一切（伤害/胶囊）
playerMovementCollisionEntities_  只挡移动（这里未用）
```

**✅ 与 §349 的 `reset()` 里三个都清**完全一致 ✓**

**⇒ **三个碰撞集、三个用途。**

### 8.2 而**全部先检查 runner 与 request**

**⇒ 三层**：

```text
1. runner 未注入 ⇒ nullopt
2. ⇒ request 非法 ⇒ nullopt
3. ⇒ 否则调用
```

**✅ 与 §349 的 `sharedPmoveAvailable()` 的四项检查**同族。**

### 8.3 而 `sharedPmoveAvailable` 的**四项**

```cpp
return sharedPmoveRunner_ && weaponMovementRunner_ &&
    playerStateToEntityStateConverter_ && clientEventsHandler_;
```

**⇒ 四个注入物全部存在才算可用。**

**✅ 与 §349 的十个注入点配合。**

## 九、`configureSpawnAndBrushModelEntities` 的**参数（九个）**

```text
origin / angles
firstDynamicEntityNum
brushDefinitions
scriptModelDefinitions
scriptModelDamageOwners
mapName / gameType
logicalMapEntities
```

**⇒ 九个。**

**✅ 而 `mapName`/`gameType` 用于 `SV_ConstBaselineTable(mapName, gameType)`。**

**⇒ 所以 const 基线表是**按地图 + 游戏类型**的。**

**✅ 与 §312 的"`<map>_const.ff` 是已发货的实体编号"**完全一致 ✓**

## 十、关键结论

1. **⭐⭐ "`ET_SCRIPTMOVER` 而不是 `ET_GENERAL`，而这就是【门不可见】的原因"`** —— `sub_1F2EF0` 是唯一到达 `R_AddBrushModelToScene`（`sub_1E54E0`）的路径。
2. **`ET_GENERAL` 的处理器 `sub_1F1820` 根本没有画笔分支** ⇒ 接收了、存储了、**从未被画**。
3. **零售的 373 个 `ET_SCRIPTMOVER` 全部 eType 6，而带画笔索引的 238 个恰好携带 `0x00FFFFFF`** —— 一个双向精确对照。
4. **`es.solid == 0xFFFFFF` 是走画笔分支的条件 ⇒ 第二次确认 `solid` 的 24 位**。
5. **`world->bmodels + 60 * modelIndex`** ⇒ `bmodel` stride 60。
6. **`237`（§343）vs `238`（本组）—— 可能是"本服务器发布"与"零售表"的差别**。
7. **字段 26（`+0x09C`）而非字段 19（`+0x05C`）** —— 画笔模型没有 XModel，零售在全部 238 个上把 `+0x05C` 留零。
8. **`+0x09C` 的第四个语义**（ET_SCRIPTMOVER = 画笔、ET_ITEM = 物品行）。
9. **⭐ "一个画笔模型偏离表就推翻整帧的标志"`** —— 位 `0x10` 是按快照设的。
10. **"脚本模型被计数而不是被要求"** —— 因为有些道具无法解析到单行，它们留在表外。
11. **"表外 ⇒ 客户端解析零基线而我们对着零 delta ⇒ 两者一致"** —— 完整闭合。
12. **⭐ "零售对这个 `*N` 的号，不是下一个空闲的"`** —— **在一张本 build 发过表的图上，号【就是实体的身份】而不是分配细节**。
13. **"没有表的图回退到顺序编号而画笔模型仍渲染（因为每个字段都显式写出）"`**。
14. **"扣留零售表点名的每一个号"**，不只是画笔模型的 —— 因为动态实体落在 fx/script_model 的号上会**继承那个实体的 origin 与 model**。
15. **"表里的空隙是什么静态都不占的号，保持可用于顺序分配"`**。
16. **`stagedActorEntityFloor = max(entry.entityNum + 1)`** 而注释**主动声明"这不是证据"**。
17. **`validScriptModel` 的九项**，而 **`modelName.front() != '*'`** 区分画笔与 xmodel（第二次确认）。
18. **`validLogicalMapEntity` 的 NUL 检查出现三次** ⇒ 地图实体定义来自外部数据。
19. **`damageOwnersByModel` 的六项**，而"可破坏"与"参与玩法"是同义的。
20. **三个 trace 与三个碰撞集**（bullet / collision / playerMovement）。
21. **`sharedPmoveAvailable()` 需要四个注入物全部存在**。
22. **`configureSpawnAndBrushModelEntities` 的九个参数**，其中 `mapName`/`gameType` 决定 const 基线表。

## 十一、未闭合点

- `237` vs `238` 的精确关系。
- `bmodel` stride 60 的字段布局。
- `sub_1E54E0` 的完整签名。
- `logicalMapEntities` 的来源（`.ff` 里的实体定义？）。
- `mapModeEligible` 的判定条件。
- `sv_snapshot_mp.cpp` 12000 行之后未读取（27,016 行，进度 44%）。
