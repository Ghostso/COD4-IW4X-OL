# 232 · 六处"回滚后再报"、`stagedMirror` 的两种提交、`baseline` 的保留

## 一、范围

本报告学习 `EngineBindings.cpp` 7502–7701 行（`synchronizeNativeServerEntities` 全部结束）。

## 二、正向流程的六处失败

### 2.1 完整清单

```text
"missing_owner"                    stagedMirror 里找不到旧 owner
"script_model_dobj"                createScriptModelDObj 失败
"link_condition_context"           installServerAnimConditionStorage 失败
"native_link ..."                  invokeSVLinkEntity 抛异常【带 512 字节详情】
"link_condition_context_restore"   restore 失败
"post_link_validation"             SV_ValidateNativeServerEntityLinkResult 失败
```

**六处，每一处都是**：

```cpp
if (!rollback()) return failed("rollback_after_XXX", entityNum);
return failed("XXX", entityNum);
```

**双重返回** —— 见下。

### 2.2 那六对阶段名

```text
"missing_owner"                    / "rollback_after_owner"
"script_model_dobj"                / "rollback_after_dobj"
"link_condition_context"           / "rollback_after_link_condition_context"
"native_link ..."                  / "rollback_after_native_link ..."
"link_condition_context_restore"   / "rollback_after_link_condition_context_restore"
"post_link_validation"             / "rollback_after_validation"
```

**每一对区分"回滚成功"与"回滚也失败"**。

### 2.3 `missing_owner` 的意义

```cpp
const auto old = stagedMirror.find(entry.entityNum);
if (old == stagedMirror.end())
{
    if (!rollback()) return failed("rollback_after_owner", entry.entityNum);
    return failed("missing_owner", entry.entityNum);
}
```

**增量模式下 `stagedMirror` 从空开始** —— 所以"已镜像的实体的 owner 不在 `stagedMirror` 里"是**正常的**。

**但这段代码要求它必须在** —— 所以**增量模式下，`touched` 里 `previouslyOwned` 的条目会走这个分支**？

**等等** —— 增量模式下 `stagedMirror` 是空的，而第一个循环只往 `stagedMirror` 加"新建的"。

**所以 `previouslyOwned=true` 的条目（来自第一个 `touched` 循环）在增量模式下 `stagedMirror.find` 会失败。**

**这是一个潜在缺陷** —— 除非增量模式下 `touched` 里的条目都是 `previouslyOwned=false`。

**从 §231 的分类看**：

```text
A. 已镜像 + 变了 ⇒ touched，previouslyOwned = true
C. 未镜像 ⇒ touched，previouslyOwned = false
```

**而 `incrementalCollision` 只跳过"`!target`"的** —— **不跳过"已镜像但变了"的**。

**所以增量模式下 `previouslyOwned=true` 的条目确实会出现，而 `stagedMirror` 从空开始 ⇒ `missing_owner`。**

**这是一个需要指出的潜在缺陷** —— 除非增量模式的调用方保证 `desired` 里的实体都未镜像过。

（注：也可能是设计意图——增量模式只用于"新玩家进入"的场景。但它会导致"已镜像玩家的更新"报 `missing_owner`。）

## 三、`native_link` 的 512 字节详情

```cpp
char stage[512]{};
snprintf(stage, sizeof(stage),
    "native_link code=0x%08lX address=%p access=%lu fault=%p "
    "shape=%u origin=%.3f,%.3f,%.3f "
    "bounds=%.3f,%.3f,%.3f contents=0x%08lX "
    "eax=%p ecx=%p edx=%p esi=%p edi=%p",
    linkException.code, linkException.address,
    linkException.accessType, linkException.faultAddress,
    entry.desired->source.shape,
    origin[0], origin[1], origin[2],
    bounds.midpoint[0], bounds.halfSize[0], bounds.halfSize[2],
    source.contents,
    (void*)eax, (void*)ecx, (void*)edx, (void*)esi, (void*)edi);
```

### 3.1 十四个字段

```text
异常      code / address / access / fault
输入      shape / origin / bounds(三个，但只取 midpoint[0] + halfSize[0] + halfSize[2]) / contents
寄存器    eax / ecx / edx / esi / edi
```

### 3.2 bounds 的取法很特殊

```cpp
bounds.midpoint[0], bounds.halfSize[0], bounds.halfSize[2]
```

**取了 midpoint[0]、halfSize[0]、halfSize[2]** —— **不是 `bounds[0], bounds[1], bounds[2]`**。

**因为 `TraceBounds` 有 6 个 float** —— 而日志只打印三个。**选了"一个中点 + 两个半尺寸"** —— 可能因为 X 与 Z 是玩家胶囊的关键维度。

### 3.3 五个寄存器

**`eax/ecx/edx/esi/edi`** —— 与 §192 里 `NativeExceptionDetails` 的九个字段（含 ebx/ebp/esp）相比**少了四个**。

**所以这个日志不打印 `ebx`** —— 而 §193 里那个 `zhunt` 崩溃案例正是靠 `ebx` 定位的。

**这是一处可以指出的不足。**

### 3.4 用作 `failed` 的阶段名

```cpp
return failed(stage, entry.entityNum);
```

**整个 512 字节的串成了阶段名** —— 而 `failed` 内部：

```cpp
auto details = std::string(stage);
if (entityNum) details += " entity=" + to_string(*entityNum);
if (details != nativeServerEntityMirrorFailure_) { log(...); ... }
```

**所以日志行会是**：

```text
"native entity mirror failed stage=native_link code=... address=... ... entity=N"
```

**这是本文件里最长的阶段名。**

## 四、`stagedMirror` 的两种提交

### 4.1 增量：逐条插入

```cpp
if (incrementalCollision)
{
    for (auto &[entityNum, mirror] : stagedMirror)
        nativeServerEntityMirror_.insert_or_assign(entityNum, std::move(mirror));
}
else
{
    nativeServerEntityMirror_ = std::move(stagedMirror);
}
```

**增量：遍历 `stagedMirror` 逐条 `insert_or_assign`**（保留 `nativeServerEntityMirror_` 里其它条目）。

**全量：整体替换**（`std::move`）。

### 4.2 但增量模式的 `stagedMirror` 只含"新/touched"的

**所以 `nativeServerEntityMirror_` 里"未触碰"的条目原样保留** —— 这正是增量的意义。

### 4.3 那两种查找方式

```cpp
// 增量：
auto mirror = nativeServerEntityMirror_.at(entityNum);   // ← 拷贝
mirror.source = ...;
stagedMirror.insert_or_assign(entityNum, std::move(mirror));

// 全量：
auto& mirror = stagedMirror.at(entityNum);               // ← 引用
mirror.source = ...;
```

**增量用 `nativeServerEntityMirror_`（因为 staged 里没有），全量用 `stagedMirror`（因为它已经是副本）。**

**这里有一个不一致**：增量模式从 `nativeServerEntityMirror_` 取旧值 —— **所以 `stagedMirror` 在增量模式下是"变更集"，而全量模式下是"完整副本"**。

## 五、`baseline` 的三源保留

```cpp
stagedMirror[entry.entityNum] = {
    .source = entry.desired->source,
    .baseline = old != nativeServerEntityMirror_.end()
        ? old->second.baseline          // ← 已镜像过 ⇒ 保留原 baseline
        : entry.backup,                 // ← 新占用 ⇒ 用读到的槽字节
    .sourceProjection = entry.desired->projection,
    .linkedImage = linkedImage,
};
```

### 5.1 `baseline` 必须保留原值

**`baseline` 是"这个槽在【我们第一次占用之前】的样子"** —— 所以后续更新不能覆盖它。

**否则回滚会回到"上次的状态"而不是"最初的状态"。**

### 5.2 三个字段的更新

```text
source             ← desired（新）
sourceProjection   ← desired（新）
linkedImage        ← 刚读回（新）
baseline           ← 【保留原值】
```

## 六、`entityStateUpdates` 的内层回滚

```cpp
for (index = 0; index < entityStateUpdates.size(); ++index)
{
    const auto& entry = entityStateUpdates[index];
    SV_CopyNativeEntityStateToServerEntity(*slot, *entry.desired->entityState);
    const auto linkedImage = readSlot(entityNum);
    if (!SV_ValidateNativeServerEntityLinkResult(linkedImage, entry.desired->source))
    {
        // 内层回滚：恢复 [0, index] 所有
        for (restoreIndex = 0; restoreIndex <= index; ++restoreIndex)
        {
            const auto& restore = entityStateUpdates[restoreIndex];
            *(SvNativeServerEntity*)nativeSlot(restore.entityNum) = restore.backup;
        }
        if (!rollback()) return failed("rollback_after_state_update", ...);
        return failed("state_update_validation", ...);
    }
    ...更新 mirror...
}
```

### 6.1 **两层回滚**

```text
内层：只恢复 entityStateUpdates[0..index]
外层：rollback() 恢复所有 touched
```

### 6.2 为什么需要内层

**`touched` 的 `rollback()` 不覆盖 `entityStateUpdates` 的槽** —— 因为那是**另一条路径**。

**所以 `entityStateUpdates` 必须自己回滚。**

**`<= index` 而不是 `< index`** —— 因为**当前这个（index）也已经写进去了**。

### 6.3 与 `touched` 回滚的区别

```text
touched：先 unlink 再 free DObj 再写字节再重建再重链 —— 五步
entityStateUpdates：直接写回 backup —— 一步
```

**因为 `entityStateUpdates` 只改了 `entityState` 部分，没动链接与 DObj。**

## 七、`synchronized()` 的两处调用

```cpp
// 快速路径（无变更）
return synchronized();

// 完整路径（末尾）
if (phase == Presentation && !ensurePlayerDObjs())
    return playerDObjFailed();
if (phase == Presentation)
    synchronizeActorHitPoses(entities, serverTime);
return synchronized();
```

**两处都会调到 `synchronized()`** —— 而它会"清失败记录、返回 true"。

**但完整路径里 `ensurePlayerDObjs` 失败会先返回 `playerDObjFailed()`** —— 所以不会到 `synchronized()`。

## 八、`initializeMantleAnimations`：`mantleAnims_` 的两个槽

```cpp
const auto validOutput = [this] {
    return mantleAnims_[0] && mantleAnims_[1] &&
        readableSpan(mantleAnims_[0], sizeof(uint32)) &&
        readableSpan(mantleAnims_[1], sizeof(uint32));
};
if (mantleAnims_[0])
    return validOutput();

if (!invokeNoArgument(mantleCreateAnims_))
    ...
```

### 8.1 `mantleAnims_` 是 `void**`（指向两个指针的数组）

**§190 里**：

```cpp
void **mantleAnims_{};
```

**而 `runtime_slots` 检查里**（§215）：

```cpp
!writableBytes(mantleAnims_, sizeof(void*) * 2)
```

**所以它是一个"两个指针的数组"。**

### 8.2 幂等

```cpp
if (mantleAnims_[0]) return validOutput();
```

**第一个槽非空 ⇒ 已经初始化过** —— 所以只验证不再创建。

**"CODOL `sub_445730` 在武器注册表重建与玩家动画脚本解析【之前】做这个进程生命期初始化。"**

## 九、关键结论

1. **六处失败、六对阶段名**，每对区分"回滚成功/失败"。
2. **`native_link` 的 512 字节详情**含异常、输入、五个寄存器（**缺 ebx**）。
3. **`baseline` 必须保留原值** —— 否则回滚回到上次而不是最初。
4. **`stagedMirror` 在两种模式下语义不同**：增量是"变更集"，全量是"完整副本"。
5. **`entityStateUpdates` 有自己的内层回滚**（`<= index`）。
6. **增量模式下 `previouslyOwned` 的条目可能报 `missing_owner`** —— 潜在缺陷。
7. **`mantleAnims_[0]` 非空即已初始化** —— 幂等验证。

## 十、未闭合点

- **增量模式下 `missing_owner` 的触发条件需要核对**（`stagedMirror` 从空开始 vs `previouslyOwned=true`）。
- `native_link` 详情缺 `ebx`，而 §193 的案例正靠 `ebx` 定位。
- `EngineBindings.cpp` 7701 行之后未读取。
