# 224 · DObj 布局校验的三层、骨骼 arena 的分配、`requestedBones` 早退

## 一、范围

本报告学习 `EngineBindings.cpp` 5910–6109 行。

## 二、`stateKey` 的最终形态

```cpp
char stateLine[256]{};
std::snprintf(stateLine, sizeof(stateLine),
    "%lu/%u/%lu/%lu/%lu/%08lX/%.3f/%lu/%08lX/%.3f",
    (unsigned long)entityNum,
    (unsigned int)treeRoot,
    (unsigned long)u32(0x1F4),          // wantLegs
    (unsigned long)u32(0x1F8),          // wantTorso
    (unsigned long)u32(Legs + 0x10),    // legs.num
    (unsigned long)u32(Legs + 0x14),    // legs.asset
    f32(Legs + 0x34),                   // legs.frac
    (unsigned long)u32(Torso + 0x10),   // torso.num
    (unsigned long)u32(Torso + 0x14),   // torso.asset
    f32(Torso + 0x34));                 // torso.frac
const std::string_view stateKey(stateLine);
auto& previous = nativeServerAnimationReport_[entityNum];
if (previous != stateKey) { previous = stateKey; log(line); }
```

### 2.1 十个字段，**没有时间**

**对比日志行的十三个字段**：

```text
stateKey：10 个（去掉了 clock / legs.t / torso.t）
日志行：  13 个（全含）
```

**"比较时不带时钟；但仍然打印它"** —— 这正是 §223 里那条原则的实现。

### 2.2 `%.3f` 在键里的风险

```cpp
f32(Legs + 0x34)    ← 用 %.3f 格式化进键
```

**浮点用三位小数进键** —— 所以 `1.0001` 与 `1.0004` 会被认为相同。

**对于"fraction 是钉在 1.0"的诊断，这是可接受的**（因为只关心"是否还是 1.0"）。但它是一个隐含的精度截断。

### 2.3 `nativeServerAnimationReport_` 是 `array<string, 64>`

```cpp
mutable std::array<std::string, 64> nativeServerAnimationReport_{};
```

**64 项** —— 而不是 18。

**因为它是按 `entityNum` 索引的**，而 `entityNum` 可达 2045。

**`entityNum < nativeServerAnimationReport_.size()` 的检查限制了只能记 0..63** —— 所以实体号 ≥ 64 的玩家不会被记录（也不会崩）。

**这是可以指出的不足**：`array<string,64>` 对 `entityNum` 上限 2045 来说太小。

## 三、结果的四段处理

```cpp
const auto restored = restoreServerAnimConditionStorage(previousContext);

failureStage = "native_update";
if (!updated) { ... "native_update code=... address=..." ... return false; }

failureStage = "native_animation";
if (!animated) { ... return false; }

failureStage = "condition_context_restore";
if (!restored) return false;

failureStage = "server_dobj_missing";
const auto* createdDObj = serverDObjGetAdapter((int32)entityNum);
if (!createdDObj) return false;
```

### 3.1 顺序

```text
1. restore（无条件执行）
2. 检查 updated
3. 检查 animated
4. 检查 restored
5. 检查 createdDObj
```

**`restore` 先执行但最后检查** —— 因为**恢复必须发生**，而"是否成功"可以后报。

### 3.2 四个新阶段名

```text
"native_update"
"native_animation"
"condition_context_restore"
"server_dobj_missing"
```

**加上前面的六个（binding_or_thread / animation_not_ready / empty_selection / model_resolution_unported_olfinal / animation_tree_source / animation_tree_allocation / lerp_frame_*），共十四个**。

## 四、DObj 布局校验的三层

### 4.1 第一层：模型数

```cpp
failureStage = "server_dobj_layout";
const auto dobjCount = readableSpan(createdDObj,
        DObjModelPointersOffset + sizeof(const void*))
    ? (uint32)*(const uint8*)(createdDObj + DObjModelCountOffset)
    : 0xFFFFFFFFu;

if (dobjCount != resolvedModelCount)
{
    // SAY BOTH NUMBERS. "server_dobj_layout" alone cannot distinguish a
    // model the engine refused to register from a names array this side
    // built wrong, and those want opposite fixes.
    static std::array<uint64_t, 64> reportedLayout{};
    const auto key = ((uint64_t)dobjCount << 32) | resolvedModelCount;
    if (entityNum < reportedLayout.size() && reportedLayout[entityNum] != key)
    {
        reportedLayout[entityNum] = key;
        log("player DObj layout mismatch entity=N dobjModels=D resolvedNames=R"
            + (dobjCount == 0xFFFFFFFF ? " (dobj unreadable)" : ""));
    }
    return false;
}
```

#### 4.1.1 两种相反的缺陷

```text
A. 引擎拒绝注册某个模型 ⇒ dobjCount < resolvedModelCount
B. 本侧的名字数组建错了 ⇒ 也可能不等，但方向不同
```

**"它们要相反的修法"** —— 所以必须两个数都给。

#### 4.1.2 `0xFFFFFFFF` 哨兵

```cpp
readableSpan(...) ? count : 0xFFFFFFFFu
```

**读不出时用 `0xFFFFFFFF`** —— 而 `uint8` 的合法值域是 0..255，所以 `0xFFFFFFFF` 不可能合法。

**日志里也标注 `" (dobj unreadable)"`**。

#### 4.1.3 键的构造

```cpp
const auto key = ((uint64_t)dobjCount << 32) | resolvedModelCount;
```

**两个 32 位压成一个 64 位** —— 所以 `map<entity, pair<D,R>>` 被压成一个 64 位整数。

### 4.2 第二层：模型指针数组可读

```cpp
const auto* modelPointers = *(void* const* const*)(createdDObj + DObjModelPointersOffset);
if (!modelPointers ||
    !readableSpan(modelPointers, sizeof(*modelPointers) * resolvedModelCount))
    return false;
```

**两级**：指针非空 + 整个数组可读。

### 4.3 第三层：逐个模型比对

```cpp
for (index = 0; index < resolvedModelCount; ++index)
{
    failureStage = "server_dobj_model";
    const auto expectedModel = findXAsset(AssetTypeXModel, modelNames[index], false).data;
    if (!expectedModel || modelPointers[index] != expectedModel)
        return false;
}
```

#### 4.3.1 **每帧每模型一次 `findXAsset`**

**这与 §219 里那个"被移除的回归"是同一个模式！**

§219 里：

> **每帧每玩家 11 次 × 2 个 DB 调用 + 一个 `std::string`** ⇒ 帧停顿 1.24 秒，控制口超时，比赛按钮失效。

**而这里又是 `resolvedModelCount` 次 `findXAsset`** —— 但**只在 `updateNativeServerPlayerDObj` 里**，而那个函数**每帧每个玩家都被调用**（`Presentation` 阶段）。

**所以这可能是同一类问题的残留** —— 除非有前置的快速路径让大部分调用提前返回。

**从 §222 看，重建块只在六项条件之一为真时执行** —— 而 `server_dobj_layout` 校验在重建块之外。

**所以这段每帧都跑** —— 这是一处应当指出的性能风险。

#### 4.3.2 `failureStage` 在循环内被设置

```cpp
for (...) { failureStage = "server_dobj_model"; ... }
```

**每次迭代都设** —— 因为只有失败时才需要它，而失败的可能是任意一次迭代。

### 4.4 成功路径

```cpp
failureStage = {};
return true;
```

**清空 `failureStage`** —— 所以调用方看到空串就是成功。

## 五、`prepareNativeServerDObjPose`：`requestedBones` 早退

```cpp
const auto requestedBones = std::ranges::any_of(
    partBits, [](const uint32 bits) { return bits != 0; });
if (!requestedBones)
    return true;
```

### 5.1 这条早退**返回 true**

**"没有请求任何骨骼 ⇒ 成功（无需摆姿）"**

**而 §221 里那个"第五项"说**：

> **在重生之后，`prepareNativeServerDObjPose` 走它的 `requestedBones` 早退，所以玩家不摆任何骨架而 `DObjTraceline` 没有东西可测。**

**所以这条早退本身是合理的**（无请求 = 无需工作），**但重生后"无请求"是一个异常状态**。

### 5.2 `partBits` 的来源

**来自 `invokeDObjGeomTracelinePartBits`**（§221）：

```cpp
std::array<uint32_t, 8> existingPartBits{};
tracelineBonesAvailable = invokeDObjGeomTracelinePartBits(
    dobjGeomTracelinePartBits_, presentDObj, existingPartBits, ...);
```

**所以 `partBits` 是"这个 DObj 需要哪些骨骼"** —— 由引擎自己算。

## 六、骨骼 arena 的分配

```cpp
const auto epoch = *(const uint32*)(dobj + DObjSkelEpochOffset);        // +148
const auto* matrices = *(void* const*)(dobj + DObjPoseMatricesOffset);  // +152
const auto currentEpoch = epoch == nativeServerDObjSkelEpoch_ && matrices;

if (currentEpoch)
{
    const auto* calculated = (const uint32*)(dobj + DObjSkelPartBitsOffset);   // +116
    const auto upToDate = equal(partBits, span(calculated, 8),
        [](requested, available) { return (requested & ~available) == 0; });
    if (upToDate) return true;
}
else
{
    const auto boneCount = *(const uint8*)(dobj + DObjBoneCountOffset);       // +10
    if (!boneCount) return false;
    const auto allocationSize = (boneCount * 32 + 15) & ~size_t{15};
    const auto allocationOffset = (nativeServerDObjSkelArenaUsed_ + 15) & ~size_t{15};
    if (allocationOffset > arena_.size() ||
        allocationSize > arena_.size() - allocationOffset)
        return false;

    memset(dobj + DObjSkelStateOffset, 0, DObjSkelStateSize);     // +20, 136 字节
    auto* allocation = arena_.data() + allocationOffset;
    memset(allocation, 0, allocationSize);
    *(uint32*)(dobj + DObjSkelEpochOffset) = nativeServerDObjSkelEpoch_;
    *(void**)(dobj + DObjPoseMatricesOffset) = allocation;
    nativeServerDObjSkelArenaUsed_ = allocationOffset + allocationSize;
}
```

### 6.1 两个分支

```text
currentEpoch（代际相同且矩阵非空）
    ⇒ 检查"已算的部分是否覆盖请求的部分"
    ⇒ 覆盖则早退 true

否则（新代际）
    ⇒ 从 arena 分配 boneCount*32 字节
    ⇒ 清 skel 状态
    ⇒ 记录代际与矩阵指针
```

### 6.2 `boneCount * 32`

**每根骨骼 32 字节** —— 与 §184 里 `DObjAnimMat` 是 32 字节一致。

### 6.3 对齐

```cpp
const auto allocationSize = (boneCount * 32 + 15) & ~size_t{15};
const auto allocationOffset = (nativeServerDObjSkelArenaUsed_ + 15) & ~size_t{15};
```

**两个都按 16 字节对齐** —— 因为矩阵运算可能需要 SIMD 对齐。

### 6.4 溢出检查

```cpp
if (allocationOffset > arena_.size() ||
    allocationSize > arena_.size() - allocationOffset)
    return false;
```

**先判 `offset > size`（防下溢），再判 `size - offset`** —— 与 §179 里"索引累加用减法比较"同一条纪律。

### 6.5 `partBits` 的位掩码比较

```cpp
[](const uint32 requested, const uint32 available) {
    return (requested & ~available) == 0;
}
```

**"请求的所有位都已在可用集合里"** —— 而不是"相等"。

**所以"已算的比请求的多"也算 up-to-date** ✓

### 6.6 arena 只增不减

```cpp
nativeServerDObjSkelArenaUsed_ = allocationOffset + allocationSize;
```

**从不回收** —— 直到 `nativeServerDObjSkelEpoch_` 变化（重置 `nativeServerDObjSkelArenaUsed_`，但那不在本段）。

**`NativeServerDObjSkelArenaSize = 18 * 256 * 32 = 147,456`**（§190）—— 而每实体最多 256 骨 × 32 = 8192 字节 ⇒ **18 个实体刚好用完**。

## 七、`prepareNativeServerDObjPose` 的结尾

```cpp
if (!invokeDObjCalcSkel(dobjCalcSkel_, dobj, partBits, &exceptionDetails))
    return false;

const auto* calculated = (const uint32*)(dobj + DObjSkelPartBitsOffset);
if (hitboxDiagnosticsEnabled())
    logNativeServerDObjSkeleton(dobj, poseEntityNum);
return equal(partBits, span(calculated, 8),
    [](requested, available) { return (requested & ~available) == 0; });
```

### 7.1 **调用后必须验证**

**`invokeDObjCalcSkel` 返回成功不代表骨架真的算了** —— 所以再比一次 `partBits`。

**与 §204 里 `DObjTraceline` 的 `fraction` 预置是同一族**：**原生函数"成功返回"不等于"做了它该做的事"**。

## 八、关键结论

1. **`stateKey` 用十个字段、日志用十三个** —— 比较去时钟、打印留时钟。
2. **`array<string,64>` 对 `entityNum` 上限 2045 太小**。
3. **DObj 布局校验三层**：模型数 / 指针数组可读 / 逐模型比对。
4. **`dobjModels` 与 `resolvedNames` 必须都给** —— 因为它们要相反的修法。
5. **`0xFFFFFFFF` 是"读不出"的哨兵**（`uint8` 合法域 0..255）。
6. **每帧每模型一次 `findXAsset`** —— 与 §219 那个"付出整场比赛"的回归是同一模式，需关注。
7. **`requestedBones` 早退返回 true** 是合理的，但重生后"无请求"是异常状态。
8. **arena 按 16 字节对齐、只增不减**，18×256×32 刚好用完。
9. **原生函数成功返回后必须再验证**（`partBits` 再比一次）。

## 九、未闭合点

- 每帧 `findXAsset` 的循环是否真的每帧执行，取决于调用链。
- `nativeServerDObjSkelEpoch_` 何时递增未在本组。
- `EngineBindings.cpp` 6109 行之后未读取。
