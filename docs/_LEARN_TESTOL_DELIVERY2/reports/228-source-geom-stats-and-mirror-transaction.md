# 228 · 逐模型的几何统计、镜像事务的三个结构

## 一、范围

本报告学习 `EngineBindings.cpp` 6706–6905 行。

## 二、逐模型的七个统计量

```cpp
uint32 geometryCount{};              // 有几何的骨骼数
uint32 activeGeometryCount{};        // 未隐藏且有几何
uint32 priorityEligibleCount{};      // 上面再加 priority >= 2
uint32 hiddenBoneCount{};            // 被骨骼隐藏位标记
uint32 unknownClassificationCount{}; // 分类 >= 20
uint8  maximumClassification{};      // 最大分类索引
uint8  maximumPriority{};            // 最大优先级
```

### 2.1 `globalBoneIndex` 的跨模型累加

```cpp
const auto absoluteBoneIndex = globalBoneIndex + boneIndex;
...
globalBoneIndex += boneCount;    // 【在模型循环末尾】
```

**骨骼隐藏位是一个跨模型的全局位图** —— 所以索引要跨模型累加。

### 2.2 骨骼隐藏位的位序是 **MSB 优先**

```cpp
const auto boneHidden = absoluteBoneIndex >= 256 ||
    (hideWord & (uint32{0x80000000} >> (absoluteBoneIndex & 31))) != 0;
```

**`0x80000000 >> (index & 31)`** —— **最高位对应索引 0**。

**与 §`sv_perks_mp.hpp` 的 `SV_HasAbility` 完全同一规则**（ability 位也是 MSB 优先）。

**而 §`sv_zm_injury_mp.hpp` 等用的是 LSB 优先** —— 所以这个项目里两种位序都存在。

### 2.3 `absoluteBoneIndex >= 256` 视为隐藏

```cpp
const auto hideWord = absoluteBoneIndex < 256
    ? *(const uint32*)(dobj + DObjBoneHideBitsOffset + 4*(absoluteBoneIndex >> 5))
    : 0xFFFFFFFF;
```

**超过 256 根骨骼 ⇒ 全部视为隐藏**。

**`DObjBoneHideBitsOffset = 160`** —— 而 `256 / 32 = 8` 个字 = 32 字节 ⇒ **`0xA0..0xBF`**。

**所以隐藏位图是 8 个 dword、256 位。**

**"超过 256 就全隐藏"** 是一个保守策略 —— 因为位图只有 256 位，超出部分无法表达。

### 2.4 `priority >= 2` 的意义

```cpp
if (!modelHidden && !boneHidden && geometryPresent)
{
    ++activeGeometryCount;
    if (priority >= 2) ++priorityEligibleCount;
}
```

**`priority` 来自 `priorityMap[classification]`** —— 而 §`sv_collision_mp.cpp` 里：

```text
BulletPriorityMap{ 1, 3, 3, 3, ... }
RiflePriorityMap{ 1, 9, 9, 9, 8, 7, ... }
```

**索引 0 的值都是 1**（`none`），而 1..18 都是 ≥3。

**所以 `priority >= 2` 排除了 `none` 和未知（0）** —— 即"至少是一个真实部位"。

### 2.5 `unknownClassificationCount` 用 `KnownLocationalPriorityCount = 20`

```cpp
if (classification >= KnownLocationalPriorityCount)
    ++unknownClassificationCount;
```

**分类 >= 20 算未知** —— 与 §`sv_collision_mp.hpp` 里"20 是实际表长"一致。

## 三、日志的十三个字段

```text
"DObj geom model entity=%lu model=%zu ptr=%p name=%s bones=%u
 modelHidden=%u classifications=%p readable=%u maxIndex=%u
 unknownIndexes=%lu geometry=%p readable=%u nonNull=%lu
 hiddenBones=%lu activeGeometry=%lu priorityEligible=%lu maxPriority=%u"
```

**十六个字段**（我数错了），分五组：

```text
身份      entity / model / ptr / name / bones
模型级    modelHidden
分类      classifications(指针) / readable / maxIndex / unknownIndexes
几何      geometry(指针) / readable / nonNull
骨骼级    hiddenBones / activeGeometry / priorityEligible / maxPriority
```

**把指针值打印出来** —— 因为"指针是否为 null"本身就是诊断信息。

## 四、`synchronizeNativeServerEntities`：事务的三个结构

### 4.1 `DesiredEntity`

```cpp
struct DesiredEntity
{
    SvCollisionEntity source;
    SvNativeServerEntity projection;
    const SvNativeEntityState* entityState{};
    const SvCharacterCustomization* customization{};
    uint8 spawnGeneration{};
};
```

**五个字段** —— 源、投影、两个指针、代际。

### 4.2 `TouchedEntity`

```cpp
struct TouchedEntity
{
    uint32 entityNum{};
    SvNativeServerEntity backup;
    const DesiredEntity* desired{};
    bool previouslyOwned{};
};
```

**"触碰过的实体 + 它的备份"** —— **用于回滚**。

**`previouslyOwned`** —— 区分"我们之前发布过它"与"这是新占用的槽"。

### 4.3 `EntityStateUpdate`

```cpp
struct EntityStateUpdate
{
    const DesiredEntity* desired{};
    SvNativeServerEntity backup;
};
```

**比 `TouchedEntity` 少两个字段** —— 因为它用于**另一条路径**（entityState 更新）。

**注意两个结构都有 `SvNativeServerEntity backup`** —— 但**分别属于不同的更新路径**。

## 五、三个 lambda：`failed` / `synchronized` / 后续

### 5.1 `failed`：去重记录

```cpp
const auto failed = [this](string_view stage, optional<uint32> entityNum = nullopt) {
    auto details = std::string(stage);
    if (entityNum) details += " entity=" + to_string(*entityNum);
    if (details != nativeServerEntityMirrorFailure_)
    {
        log("native entity mirror failed stage=" + details);
        nativeServerEntityMirrorFailure_ = std::move(details);
    }
    return false;
};
```

**三个要点**：

1. **可选的实体号** —— 所以既能报"阶段失败"也能报"某实体失败"；
2. **按详情串去重** —— 只有变化才记；
3. **返回 `false`** —— 让调用点写成 `return failed(...)`。

**与 §218 里 `report` lambda 是同一模式** —— "先报告再返回"。

### 5.2 `synchronized`：只在状态变化时记录

```cpp
const auto synchronized = [this, entities] {
    if (!entities.empty() &&
        (!nativeServerEntityMirrorObservedSuccess_ ||
         !nativeServerEntityMirrorFailure_.empty()))
    {
        log("native entity mirror synchronized entities=" + to_string(entities.size()));
        nativeServerEntityMirrorObservedSuccess_ = true;
    }
    nativeServerEntityMirrorFailure_.clear();
    return true;
};
```

**三个条件**：

```text
非空
且（从未成功过 或 有过失败）
⇒ 才记
```

**所以"一直成功"是沉默的** —— 与 §225 里"仪器健康时必须沉默"一致。

**而 `nativeServerEntityMirrorFailure_.clear()` 是无条件的** —— 因为成功路径必须清掉失败记录。

## 六、`serverAnimationTimeMilliseconds_` 的赋值

```cpp
// Take the clock before anything can install the block. A server frame
// always runs a mirror phase before any native animation call, so this
// is the earliest point the time is both known and current.
serverAnimationTimeMilliseconds_ = serverTime;
```

**"在任何一个可以安装那个块的东西之前取时钟。一个服务端帧总是在任何原生动画调用之前跑一个镜像阶段，所以这是时间既已知又最新的最早点。"**

**这回答了 §216 里我标为未闭合的"`serverAnimationTimeMilliseconds_` 由谁更新"。**

**答案：`synchronizeNativeServerEntities` 的第一行。**

## 七、源顺序的严格递增检查

```cpp
std::optional<uint32> previousEntityNum;
for (const auto& entity : entities)
{
    if (previousEntityNum && entity.entityNum <= *previousEntityNum)
        return failed("source_order", entity.entityNum);
    ...
    previousEntityNum = entity.entityNum;
}
```

**`<=`** —— **必须【严格】递增，不允许重复**。

**"源顺序"是后续所有确定性操作的前提** —— 与 §`sv_snapshot` 里"实体必须按号排序"对应。

## 八、`incrementalCollision` 标志

```cpp
const bool incrementalCollision =
    phase == SvNativeEntityMirrorPhase::IncrementalCollision;
```

**三种阶段**（§176）：`Collision` / `IncrementalCollision` / `Presentation`。

**而这个函数只区分"是否增量碰撞"** —— 后面会用它决定是否复用上一次的镜像。

## 九、关键结论

1. **七个统计量**：几何数 / 活跃几何 / 优先合格 / 隐藏骨 / 未知分类 / 最大分类 / 最大优先。
2. **骨骼隐藏位是跨模型全局位图，MSB 优先，256 位**；超出视为全隐藏。
3. **`priority >= 2` 排除 `none`（值 1）与未知（值 0）**。
4. **三个事务结构**：`DesiredEntity`（目标）、`TouchedEntity`（含备份+是否曾拥有）、`EntityStateUpdate`。
5. **`failed` lambda 按详情串去重并返回 false**。
6. **`synchronized` 只在"首次成功或曾失败过"时记录**。
7. **`serverAnimationTimeMilliseconds_` 由 `synchronizeNativeServerEntities` 第一行更新** —— 解决了 §216 的未闭合点。
8. **源实体必须严格递增**（`<=` 即失败）。

## 十、未闭合点

- `svFlags` 的 `0x112` vs `0x11A` 矛盾仍未解决。
- `EngineBindings.cpp` 6905 行之后未读取。
