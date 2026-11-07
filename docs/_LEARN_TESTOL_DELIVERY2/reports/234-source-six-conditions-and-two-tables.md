# 234 · 六个条件一种状态、两张表必须分开报、回调槽的最终安装

## 一、范围

本报告学习 `EngineBindings.cpp` 7900–8099 行。

## 二、九个步骤的完整序列

```text
begin_load_anim_trees     → BeginLoadAnimTreesFailed
load_anim_trees           → LoadAnimTreesFailed
[rawfile ×2 检查]          → AnimationScriptAssetsUnavailable
find_anims                → FindAnimsFailed
parse_anim_script         → ParseAnimScriptFailed
precache_anim_trees       → PrecacheAnimTreesFailed
find_anim_trees           → FindAnimTreesFailed
end_load_anim_trees       → EndLoadAnimTreesFailed
finalize_player_anims     → FinalizePlayerAnimsFailed
[输出校验]                 → InvalidOutput
```

**九个具名失败 + 一个输出校验** —— 与 §212 里 15 个状态的枚举完全对应。

## 三、`restoreFailedContext()` 在每一处

**九个失败点里，除了 `begin_load_anim_trees` 之外，每一处都先调 `restoreFailedContext()` 再 `fail(...)`。**

**而 `begin_load_anim_trees` 也调了**（§233 里读过）。

**所以是"十处调用 `restoreFailedContext`"** —— 而 `InvalidOutput` 那处**不调它**，而是直接：

```cpp
InterlockedCompareExchangePointer(scriptSlot, previousScriptData, serverContext);
return fail(InvalidOutput);
```

### 3.1 因为那处**已经**调过 `restoreServerAnimConditionStorage`

```cpp
if (... || !restoreServerAnimConditionStorage(previousConditionBase))
```

**`restore` 在条件里被调用了** —— 所以后面只需恢复 `scriptSlot`。

## 四、`scriptLoadingBegun` 的状态追踪

```cpp
bool scriptLoadingBegun{};

// begin 成功后：
scriptLoadingBegun = true;

// end 调用后：
const auto endLoadAnimTreesCompleted = invokeScrEndLoadAnimTrees(module_);
scriptLoadingBegun = false;      // ← 【无论成功都清】
```

### 4.1 为什么"无论成功都清"

```cpp
const auto endLoadAnimTreesCompleted = invokeScrEndLoadAnimTrees(module_);
scriptLoadingBegun = false;
if (!endLoadAnimTreesCompleted) { restoreFailedContext(); return fail(...); }
```

**因为 `invokeScrEndLoadAnimTrees` 已经被调用过了** —— 无论成功失败，`restoreFailedContext` 里不该再调一次。

**否则会重复 end。**

## 五、`actorHitPosesEnabled_` 的双重判定

```cpp
actorHitPosesEnabled_ = loadActorHitTree;
actorHitPoseLogCount_ = 0;
if (loadActorHitTree)
{
    void* actorAnims{};
    memcpy(&actorAnims, serverContext + 708228 + 3*20, sizeof(actorAnims));
    const auto nodes = actorAnims && readableSpan(actorAnims, 12)
        ? *(uint32*)actorAnims : 0u;
    actorHitPosesEnabled_ = nodes > 1 && nodes <= 4096;
    log("ZMPOSE init treeNodes=" + to_string(nodes) +
        " enabled=" + to_string(actorHitPosesEnabled_));
}
```

### 5.1 两重

```text
1. loadActorHitTree（环境变量 + 地图）
2. 树真的存在且节点数在 (1, 4096]
```

**"两重都成立才启用"** —— 与 §226 里 `synchronizeActorHitPoses` 的 `nodeCount < 2 || nodeCount > 4096` 一致。

### 5.2 同样的 `708228 + 3*20`

**与 §226 完全相同** —— 所以这段逻辑重复了。

**两处都在读同一个 family3 记录。**

## 六、六个条件一种状态（本组最重要的一段）

```cpp
if (!animationCount || animationCount > MaximumPlayerAnimations ||
    !finalAnimationCount ||
    finalAnimationCount > MaximumPlayerAnimations || !animTree ||
    *animScriptDataPointer_ != serverContext ||
    !restoreServerAnimConditionStorage(previousConditionBase))
{
    // SIX CONDITIONS, ONE STATUS. "invalid_output" was true of all of
    // them, and three of the values it reads were 3.3.3.3 offsets, so
    // say which one is unhappy rather than making the next run guess.
    snprintf(detail, sizeof(detail),
        "server animation invalid output parsed=%u final=%u "
        "animTree=0x%08X scriptData=0x%08X context=0x%08X restored=%u",
        animationCount, finalAnimationCount,
        (uint32)(uintptr_t)animTree,
        (uint32)(uintptr_t)*animScriptDataPointer_,
        (uint32)(uintptr_t)serverContext,
        restoreServerAnimConditionStorage(previousConditionBase) ? 1u : 0u);
    ...
}
```

### 6.1 六个条件

```text
1. !animationCount                        （解析产出的数量为零）
2. animationCount > MaximumPlayerAnimations（超出上限）
3. !finalAnimationCount                   （原生计数为零）
4. finalAnimationCount > MaximumPlayerAnimations
5. !animTree                              （树句柄为空）
6. *animScriptDataPointer_ != serverContext（指针没被接受）
7. !restoreServerAnimConditionStorage(...)  （恢复失败）
```

**七个，不是六个**（注释说 six，但实际是七）。

### 6.2 那句"三个值曾是 3.3.3.3 的偏移"

```text
and three of the values it reads were 3.3.3.3 offsets
```

**三个偏移**：

```text
NumberOfPlayerAnimationsOffset = 0x1A000
AnimTreeHandleOffset           = 0xACE64
AnimScriptStateTableOffset     = 0x1A004（在 logServerAnimScriptTable 里）
```

**而 §199 已确认这三个都是本 build 的正确值** —— 所以注释说的是"曾经"。

### 6.3 `restoreServerAnimConditionStorage` 被调了**两次**

```cpp
if (... || !restoreServerAnimConditionStorage(previousConditionBase))
{
    ...
    restoreServerAnimConditionStorage(previousConditionBase) ? 1u : 0u   // ← 又调一次
```

**第一次在条件里（短路求值），第二次是为了日志里的 `restored=` 字段。**

**但第二次调用时存储可能已经被恢复** ⇒ 第二次会失败 ⇒ **`restored=` 恒为 0**。

**这是一个可以指出的缺陷** —— 日志字段会误导。

（除非 `restoreServerAnimConditionStorage` 对"已经是 previousBase"的情况返回 true —— 从源码看：

```cpp
return InterlockedCompareExchangePointer(slot, previousBase, storage_.data()) == storage_.data();
```

**如果当前是 `previousBase` 而不是 `storage_.data()`，CAS 失败，返回 false。**

**所以第二次调用确实返回 false** ⇒ `restored=` 恒为 0 ⇒ **日志字段无效**。）

## 七、解析后替换四个回调槽

```cpp
// Parsing can use the client callbacks installed above. Runtime player
// updates must instead own the server DObj map.
*Create  = &serverDObjCreateAdapter;
*Append  = nullptr;                       // ← 显式置空
*Free    = &serverDObjFreeAdapter;
*Get     = &serverDObjGetAdapter;
```

### 7.1 那段关于 CODDIFF 的完整论证

```text
CODOL's retained 0x00445460 callback is client-only and marks the held model
as collidable; BO1/BO2 server callbacks exclude the ordinary held model
from collision, while Ghosts disables the callback. Keep it detached
until a CODOL server policy is recovered instead of changing native
locational traces with a presentation callback.
```

**三层**：

```text
CODOL   标记手持模型可碰撞（client-only）
BO1/BO2 排除手持模型
Ghosts  禁用回调
```

**"保持它断开，直到恢复一个 CODOL 服务端策略"** —— 所以 `Append = nullptr`。

### 7.2 为什么解析时用 client、运行时用 server

**"Parsing can use the client callbacks installed above. Runtime player updates must instead own the server DObj map."**

**两个阶段用两套回调** —— 因为：
- 解析阶段只需要"能解析"；
- 运行时需要"我们的 DObj 在服务端表里"。

## 八、`logServerAnimScriptTable`：**两张表必须分开报**

### 8.1 问题

```cpp
// THE EVENT TABLE, WHICH THIS INSTRUMENT COULD NEVER SEE. The line
// above walks the MOVETYPE state table at +0x1A004 -- the locomotion
// selector's input -- and says nothing whatever about scriptEvents at
// +0x25F80, which is the table BG_AnimScriptEvent sub_407E10 walks and
// the ONLY thing that can make a death return -1.
```

**两张表**：

```text
+0x1A004  movetype 状态表   ← locomotion 选择器的输入
+0x25F80  scriptEvents      ← BG_AnimScriptEvent 走的，唯一能让死亡返回 -1 的
```

### 8.2 那次"13 次全失败而日志健康"

```text
Every one of the thirteen runs that failed every death it saw printed
a healthy `populated=43/47` here, because the healthy half was the only
half being read. Report both, so "the parse worked" and "the parse worked
for the table the death event uses" stop being the same sentence.
```

**"十三个每一局死亡都失败的运行，每一局都打印了健康的 `populated=43/47`，因为只有健康的那一半被读了。"**

**"让'解析成功了'与'解析对死亡事件用的那张表成功了'不再是同一句话。"**

**这是本项目最核心的诊断原则的又一次应用。**

### 8.3 `numItems` 的读法

```text
Counted, not sampled: sub_407790 opens `mov eax,[eax]` / `test eax,eax`
/ `jle` on the first dword of each animScript_t, so that dword is
numItems and <= 0 there is exactly the silent -1.
```

**每个 `animScript_t` 的第一个 dword 是 `numItems`，`<= 0` 正是那个静默的 -1。**

### 8.4 两个具体事件的黄金值

```text
DEATH (1) and RAISEWEAPON (7) are named because they are the only two
events this server fires; a healthy OLfinal mp/playeranim.script gives
DEATH 24 sets and RAISEWEAPON 13.
```

```text
DEATH (1)       → 24 sets
RAISEWEAPON (7) → 13
```

**两个黄金值** —— 与 §206 里 `runServerSpawnAnimation` 触发 `RAISEWEAPON` 对应。

## 九、两个统计循环

### 9.1 movetype 表

```cpp
for (moveType = 0; moveType < AnimScriptMoveTypeCount(47); ++moveType)
{
    const auto scripts = *(const uint32*)(context + AnimScriptStateTableOffset
        + moveType * AnimScriptItemsStride(0x204));
    if (!scripts) continue;
    ++populatedCount;
    populated += ' ' + to_string(moveType) + ':' + to_string(scripts);
}
```

**遍历 47 个 movetype、每个 0x204 步长** —— 与 §199 的 `AnimScriptMoveTypeCount = 47`、`AnimScriptItemsStride = 0x204` 一致。

### 9.2 事件表

```cpp
for (event = 0; event < SvNativeAnimScriptEventCount; ++event)
{
    const auto offset = SV_NativeAnimScriptEventOffset((int32)event);
    if (!offset) continue;
    const auto items = *(const int32*)(context + *offset);
    if (!items) continue;
    ++populatedEvents;
    events += ' ' + to_string(event) + ':' + to_string(items);
}
```

**用 `SV_NativeAnimScriptEventOffset(event)` 得到偏移** —— 因为事件表的布局不是线性的（某些事件没有槽）。

**`if (!offset) continue`** —— 跳过没有槽的事件。

## 十、关键结论

1. **九个具名失败 + 一个输出校验** = 10 条路径。
2. **`scriptLoadingBegun` 在 end 调用后无条件清零** —— 否则 `restoreFailedContext` 会重复 end。
3. **`actorHitPosesEnabled_` 两重判定**：环境变量 + 树节点数在 (1,4096]。
4. **`restored=` 日志字段恒为 0** —— 因为 `restore` 被调了两次且第二次必然失败。
5. **解析用 client 回调、运行时用 server 回调** —— 两阶段两套。
6. **`Append` 槽显式置空** —— 因为三家参照行为不一致，宁可断开。
7. **两张表必须分开报** —— 否则"解析成功"与"死亡事件表可用"混为一谈。
8. **十三个运行打印 `populated=43/47` 却每局死亡都失败** —— 仪器只读了健康的那一半。

## 十一、未闭合点

- `restored=` 字段的双重调用缺陷。
- `708228 + 3*20` 的读取在 §226 与 §233 重复。
- `EngineBindings.cpp` 8099 行之后未读取。
