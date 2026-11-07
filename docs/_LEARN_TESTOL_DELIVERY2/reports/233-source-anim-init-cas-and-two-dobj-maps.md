# 233 · 动画初始化的 CAS 状态机、两个 DObj 表的最终解释

## 一、范围

本报告学习 `EngineBindings.cpp` 7701–7900 行。

## 二、`initializeServerAnimationContext`：三态 CAS

```cpp
auto status = serverAnimationInitializationStatus_.load(acquire);
if (status != NotInitialized) return status;

if (!compare_exchange_strong(status, ContextBusy, acq_rel, acquire))
    return status;        // ← 别人抢先了，返回【它设的】状态
```

### 2.1 三段

```text
1. 读当前状态
2. 非 NotInitialized ⇒ 直接返回（已有人跑过/在跑/失败过）
3. CAS(NotInitialized → ContextBusy) 失败 ⇒ 返回失败后的值
```

### 2.2 `status` 是**输入兼输出**

```cpp
compare_exchange_strong(status, ContextBusy, ...)
```

**`status` 传引用** —— 失败时被写成**当前实际值**。**所以 `return status` 返回的是"谁抢先设的值"**。

### 2.3 但失败后状态停在 `ContextBusy` 还是别的

**如果 CAS 失败**，说明在两次原子操作之间别人改了 —— **而那个别人可能是另一个线程正在跑（`ContextBusy`），也可能是已经失败（某个 `_Failed`）**。

**所以返回值能区分"别人在跑"与"别人失败了"**。

### 2.4 一旦失败就永久失败

```cpp
const auto fail = [this](status) {
    serverAnimationInitializationStatus_.store(status, release);
    return status;
};
```

**失败后状态不再是 `NotInitialized`** —— 所以**后续调用直接返回那个失败状态，不会重试**。

**这是"一次性初始化"的语义** —— 与 §198 里"关卡世界初始化是唯一被证实的恢复边界"一致。

## 三、`armVectoredFaultWitnessImpl` 的位置

```cpp
// Arm the witness for the whole of this function. Everything from here
// to the end is native code that has never completed in this process,
// and one of those calls has already killed it without a word.
armVectoredFaultWitnessImpl(module_);
```

**"从这里到结尾全是原生代码，而其中一次调用已经无声地杀死了它。"**

**注意 `armVectoredFaultWitnessImpl` 内部有 `if (VectoredWitnessHandle) return;`** —— 所以重复调用无副作用。

## 四、`anim-condition` 初始化的七步

```cpp
serverAnimConditionStorage_.fill(std::byte{});
serverLoadAnimStorage_.fill(std::byte{});

auto* serverContext = serverAnimConditionStorage_.data();
*(int32*)(serverContext + AnimUserOffset) = 0;              // 0xAF314

const auto* deathFxOptIn = getenv("OLMOD_FACTORY_DEATH_FX");
const bool loadActorHitTree = mapName == "zm_factory_sh" &&
    deathFxOptIn && string_view(deathFxOptIn) == "1";

*(uint32*)(serverContext + AnimTreeMaskOffset) = loadActorHitTree ? 8u : 0u;   // 0xAF318
*(uint8*)(serverContext + AsymmetricAnimScriptFlagOffset) = 0;                // 0xAF31C

for (const auto [offset, rva] : ServerAnimationCallbackRvas)
    *(void**)(serverContext + offset) = module_ + rva;

*(void**)(serverContext + ServerGetDObjCallbackOffset) = (void*)&serverDObjGetAdapter;
```

### 4.1 四个标量/标志

```text
AnimUserOffset                    = 0xAF314  ← 0
AnimTreeMaskOffset                = 0xAF318  ← 8 或 0
AsymmetricAnimScriptFlagOffset    = 0xAF31C  ← 0
ServerGetDObjCallbackOffset       = 0xAF334  ← 换成我们的 adapter
```

### 4.2 `AnimTreeMaskOffset = 8` 的条件

```cpp
mapName == "zm_factory_sh" && OLMOD_FACTORY_DEATH_FX == "1"
```

**"Family3 是原生演员客户端里的 `generic_human`。FFA 保持 mask0 不变。"**

**所以 `8 = 1 << 3`** —— 第 3 位。

## 五、那段"stock callback 读错表"的完整解释

这是本组最重要的一段。

### 5.1 两个表的确切地址与写入者

```text
一个 0xCC 步长的 DObj 池在 VA 0x02E8E850，
通过两个独立的 map 到达：

ServerDObjCreate VA 0x0059E740 只把 server DObj 注册进 VA 0x02E8D050
    —— 它唯一的 map 写入在 0x0059E755，并在 0x0059E7B6 返回，
    所以 0x0059E7EE 的那个 0x02EF4858 写入属于【另一个函数】。

但 CODOL 这个槽的 stock callback（RVA 0x0455D0）索引【另一张】表：
    `movzx eax, word [eax*2 + 0x02EF4858]` 在 0x004455D6，当那个字为零时返回 null。
```

**关键**：

```text
ServerDObjCreate 写 0x02E8D050
stock callback 读 0x02EF4858
```

**两个【不同】的表** —— 而 `0x02EF4858` 的写入者"属于另一个函数"（未被本项目调用）。

### 5.2 后果链

```text
BG_SetLerpFrameAnimation VA 0x00409BF0 在 0x00409C24 调这个槽，
并在返回 null 时于 0x00409C2E 早退 ——
所以 stock 函数装着时，【任何玩家在任何帧都从未设置过动画】，
而摆好的骨架就是 DObjCalcSkel 在没有任何东西驱动时产出的样子。
```

### 5.3 实测证据

```text
MEASURED live 2026-08-17: at a respawn this project logged
`animMap=0 srvMap=278` for a player whose DObj was present and healthy
- present in the server map, absent from the one the stock callback reads.
```

**`animMap=0 srvMap=278`** —— **精确的两个数字**：

```text
animMap = 0    ← stock callback 读的那张表里没有
srvMap  = 278  ← 我们的表里有
```

**这是 §222 里那条日志的实际输出** —— 而那两条 `animMap`/`srvMap` 诊断正是为了抓这个。

### 5.4 替换

```cpp
*(void**)(serverContext + ServerGetDObjCallbackOffset) = (void*)&serverDObjGetAdapter;
```

**用 `serverDObjGetAdapter` 替换。**

### 5.5 ABI 兼容性论证

```text
serverDObjGetAdapter 接受原生调用者传的同一个实体号（`[entity+0]`，entityState.number），
并通过 ServerDObjGet VA 0x0059E570 对着【服务端那张表】解析它，
而本项目的 DObj 实际上就住在那儿。

The native call site pushes two arguments and cleans 8 bytes itself,
so a one-argument __cdecl adapter is ABI-compatible with the slot.
```

**"原生调用点压两个参数并自己清理 8 字节，所以一个参数的 `__cdecl` 适配器与该槽在 ABI 上兼容。"**

**两个参数 vs 一个参数** —— 因为多压的参数不影响 `__cdecl` 的被调用者（它只读第一个，调用者清理全部）。

### 5.6 那次"0xCC 步长"的残留

**注释里两次写 `0xCC`** —— 而 §192 已确认本 build 是 **`0xD8`**。

**这是一处过时的注释**（`0xCC` 是 3.3.3.3 的）。

## 六、`animScriptDataPointer_` 的双重占用检查

```cpp
std::byte* previousConditionBase{};
if (!installServerAnimConditionStorage(previousConditionBase))
    return fail(ContextBusy);

auto* scriptSlot = (void* volatile*)animScriptDataPointer_;
auto* previousScriptData = (std::byte*)InterlockedCompareExchangePointer(scriptSlot, nullptr, nullptr);
if (previousScriptData && previousScriptData != serverContext)
{
    restoreServerAnimConditionStorage(previousConditionBase);
    return fail(ContextBusy);
}
```

### 6.1 两个"别人占着"的检查

```text
1. installServerAnimConditionStorage 失败 ⇒ 别人占着 animConditionBasePointer_
2. previousScriptData 非空且不是我们 ⇒ 别人占着 animScriptDataPointer_
```

**第二个检查是"读而不写"**：

```cpp
InterlockedCompareExchangePointer(scriptSlot, nullptr, nullptr)
```

**CAS(slot, 期望=nullptr, 新值=nullptr)** —— 比较交换成同一个值等于纯原子读。

### 6.2 但**没有真正写 `animScriptDataPointer_`**

**注意这段只【读】了 `scriptSlot`，没有写 `serverContext` 进去。**

**而 `restoreFailedContext` 里有**：

```cpp
InterlockedCompareExchangePointer(scriptSlot, previousScriptData, serverContext);
```

**CAS(slot, 期望=serverContext, 新值=previousScriptData)** —— **只有当前是 `serverContext` 才恢复。**

**所以"写"发生在别处**（7900 行之后，本组未读到）。

## 七、`restoreFailedContext` 的四步

```cpp
logStage("failure_cleanup_begin");
if (scriptLoadingBegun)
{
    logStage("failure_end_load_anim_trees_begin");
    invokeScrEndLoadAnimTrees(module_);
    scriptLoadingBegun = false;
    logStage("failure_end_load_anim_trees_complete");
}
logStage("failure_globals_restore_begin");
InterlockedCompareExchangePointer(scriptSlot, previousScriptData, serverContext);
restoreServerAnimConditionStorage(previousConditionBase);
logStage("failure_globals_restore_complete");
```

### 7.1 六条日志

```text
"failure_cleanup_begin"
"failure_end_load_anim_trees_begin"
"failure_end_load_anim_trees_complete"
"failure_globals_restore_begin"
"failure_globals_restore_complete"
```

**五条** —— 而每一条都是"我到这里了"的标记。

**如果日志停在 `_begin` 而没有 `_complete`，就说明那一步崩了。**

## 八、九个 `logStage` 的进度追踪

```text
"begin_load_anim_trees_begin" / "_complete"
"load_anim_trees_begin" / "_complete"
"find_anims_begin" / "_complete"
"parse_anim_script_begin"（本组刚到这里）
```

**每一对都是"进入"与"完成"** —— 所以**卡在哪一步一目了然**。

## 九、两个 rawfile 的检查

```cpp
constexpr std::array animationScriptAssets{
    "mp/playeranim_defines.script",
    "mp/playeranim.script",
};
for (const auto* assetName : animationScriptAssets)
{
    const auto asset = findXAsset(AssetTypeRawFile, assetName, false);
    const auto isDefault = dbIsXAssetDefault_(AssetTypeRawFile, assetName);
    log("server animation rawfile=" + assetName +
        " present=" + (asset.data && !isDefault ? "true" : "false") +
        " default=" + (isDefault ? "true" : "false"));
    if (!asset.data || isDefault)
    {
        restoreFailedContext();
        return fail(AnimationScriptAssetsUnavailable);
    }
}
```

### 9.1 **两个条件都要**

```text
asset.data 非空
且 isDefault 为假
```

**与 §182/§212 里"`allowDefault=false` 不够"完全一致** —— 存在但未加载的资产仍回默认值。

### 9.2 日志打印两个布尔

**`present=` 与 `default=` 分开** —— 因为三种情况：

```text
present=true  default=false  ⇒ 好
present=true  default=true   ⇒ 存在但未加载
present=false default=*      ⇒ 不存在
```

## 十、`animationCount` 的初值与日志

```cpp
auto animationCount = MaximumPlayerAnimations;    // 1024
char details[192];
snprintf(details, sizeof(details),
    "server animation parser input scratch=%p context=%p count=%u thread=%lu",
    serverLoadAnimStorage_.data(), serverContext, animationCount,
    GetCurrentThreadId());
```

**四个字段** —— 把"解析器的三个输入 + 线程"都记下来。

**`MaximumPlayerAnimations = 1024`**（§184）—— 与 `ServerLoadAnimStorageSize = 0x12000 = 1024*72` 一致。

## 十一、关键结论

1. **三态 CAS + 失败即永久** —— 一次性初始化，不重试。
2. **`compare_exchange_strong` 的第二参数是输入兼输出** —— 失败时得到"谁抢先"。
3. **`AnimTreeMaskOffset = 8` 只在 `zm_factory_sh` + 环境变量时**。
4. **stock callback 读 `0x02EF4858` 而 `ServerDObjCreate` 写 `0x02E8D050`** —— 两个不同的表。
5. **`animMap=0 srvMap=278` 是那条诊断的实际输出**。
6. **一参数 `__cdecl` 适配器与两参数调用点 ABI 兼容**（调用者清理）。
7. **注释里的 `0xCC` 已过时**（本 build 是 `0xD8`）。
8. **每个原生步骤都有 `_begin`/`_complete` 日志对** —— 卡在哪一步一目了然。
9. **两个 rawfile 必须 `present && !default`** —— `allowDefault=false` 不够。

## 十二、未闭合点

- `animScriptDataPointer_` 的"写"在 7900 行之后。
- 注释里的 `0xCC` 需更新为 `0xD8`。
- `EngineBindings.cpp` 7900 行之后未读取。
