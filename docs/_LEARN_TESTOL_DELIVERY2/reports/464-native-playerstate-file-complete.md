# 464 · **`sv_native_playerstate_mp.cpp` 全文件收尾** —— "线缆送的是环，不是批"、`8` 位游标的裂缝修复、以及一个 appender 只能走一步

## 一、范围

本报告学习 `sv_native_playerstate_mp.cpp` 1500–1687 行（四个 `Scripted*` 写者、可预测事件的三读一写、`SV_ReadNativeOffhandState`、`SV_ClearNativeGrenadeTimer`、`SV_ReadNativePlayerStateActionDiagnostics`），并收尾整个文件（**共 `1,687` 行**）。

## 二、**"线缆送的是环，不是批"**（本组最重要的一段）

### 2.1 那段

```cpp
// THE WIRE SENDS THE RING, NOT THE BATCH. Netfield indices 21..24 are
// playerState +0x10C, +0x114, +0x11C and +0x124 -- ring slots 0..3 --
// and the client indexes them by `sequence & 3` exactly as
// SV_ReadNativePredictableEvents does. Copying the batch reader's
// output in batch order would put the right events in the wrong slots
// whenever fewer than four fired.
std::array<SvNativePredictableEvent, 4> SV_ReadNativePredictableEventRing(
    const SvNativePlayerState &source)
{
    for (std::size_t index = 0; index < ring.size(); ++index)
        ring[index] = readValue<SvNativePredictableEvent>(
            source, PredictableEventsOffset + index * sizeof(SvNativePredictableEvent));
    return ring;
}
```

### 2.2 二十四层

```text
1. **线缆送的是【环**，不是【批**】**
2. ⇒ **网络字段索引 `21..24` 是 `playerState +0x10C`、`+0x114`、`+0x11C`、`+0x124`**
3. ⇒ **⇒ 【环槽 `0..3`**】】
4. ⇒ **而【客户端【按 `sequence & 3`**】索引它们**
5. ⇒ **⇒ 与 `SV_ReadNativePredictableEvents` 【完全一样**】
6. ⇒ **⚠ 【按【批的顺序**复制那个读器的输出**
7. ⇒ **会【在【少于四个**触发时】【把对的**事件【放进错的槽**】】】
```

### 2.3 ⭐⭐⭐ **"按批的顺序复制会把对的『事件』放进错的『槽』"**

**✅ 这是本报告里**最重要的一条"批与环的两个空间**。**

**✅ 与 §416 的"`predictableEvents` 是一个 `4` 槽环，而 `sequence & 3` 索引"**——**完全闭合** ✓

**⇒ 三层**：
```text
批 ⇒ **`result.events[0..count)` 按【时间序**】
环 ⇒ **`ring[sequence & 3]` 按【槽号**】
⇒ **⇒ 所以【两者【只在 `count == 4`**时重合**】
```

**✅ ⭐⭐⭐ **"两者只在 `count == 4` 时重合"** —— 一个**极精确的条件**。

**⚠ 而"`+0x10C`/`+0x114`/`+0x11C`/`+0x124`"⇒ **四个偏移，步长 `8`**。**

**⇒ 三层**：
```text
`0x114 - 0x10C = 8`
`0x11C - 0x114 = 8`
`0x124 - 0x11C = 8`
⇒ **⇒ 所以【`sizeof(SvNativePredictableEvent) = 8`**】
```

**✅ ⭐⭐ **一个"步长 `8`"的推导** —— 而**一个事件是 `{int32 event, int32 parameter}`** = `8` 字节 ✓

### 2.4 而**"`8` 位游标的裂缝修复"**

```cpp
// CODREF(client_events): Ghosts ClientEvents 0x140114940 and BO1
// 0x005F82E0 clamp to the newest four events, repair the 8-bit cursor
// discontinuity when old > current + 64, then consume sequence & 3.
// CODDIFF(client_events): unlike the native void loop, the source
// adapter rejects a future or oversized cursor before dispatch.
const auto current = ...;
auto first = static_cast<std::int64_t>(oldEventSequence);
if (first < current - 4) first = current - 4;
if (first > current + 64) first -= 256;
if (first > current || current - first > 4) return std::nullopt;
```

**⇒ 二十层**：
```text
1. **`ClientEvents`（Ghosts `0x140114940` / BO1 `0x005F82E0`）【夹到最新四个**事件**】**
2. ⇒ **修复【那个 `8` 位游标的【不连续**】**
3. ⇒ **当 `old > current + 64`**】
4. ⇒ **⇒ 然后【消费 `sequence & 3`**】**
5. ⇒ **⚠ 与那个原生的 `void` 循环不同**
6. ⇒ **⇒ 【这个源适配器【在 dispatch 之前**拒绝【一个未来或过大的游标**】】**
7. ⇒ **⇒ 所以【三层夹**】】
```

### 2.5 ⭐⭐⭐ **"修复那个 `8` 位游标的不连续：当 `old > current + 64` 时 `-= 256`"**

**✅ 这是本报告里**最漂亮的一条"一个 `8` 位游标的回绕修复**。**

**⇒ 三层**：
```text
`old > current + 64` ⇒ **一个回绕**（**`old` 是 `250` 而 `current` 是 `2`**）
⇒ **`first -= 256`** ⇒ **`250 - 256 = -6`** ⇒ **而现在 `-6 <= 2`** ✓
⇒ **⇒ 所以【那个 `-256` 【正是**一个模 `256` 的减法**
```

**✅ ⭐⭐⭐ **"那个 `-256` 正是一个模 256 的减法"**。

**✅ 与 §417 的"`slot = sequence & 3`"**同族（**第三次"模运算**）。

**⇒ 三层**：
```text
§417  **`sequence & 3`**（**模 `4`**）
§432  **`written.fetch_add(1)` 与 `index > budget`**（**一个计数**）
§464  **`first -= 256`**（**模 `256`**）
⇒ **⇒ 三次"模运算**】
```

**✅ ⭐⭐ **"模运算"三例表**。

**⚠ 而"`64` 是一个中间值"**⇒ **为什么 `64` 而不是 `128`**？**

**⇒ 三层**：
```text
`old > current + 64` ⇒ **一个"过半**"的判据**（**`256/2 = 128`**）
⇒ **⇒ 所以 `64` 是【`128` 的一半**】
```

**⚠ 一个**可推导的观察**（**`64` 可能是从一个更保守的经验来**）。

**✅ 而"`old < current - 4 ⇒ first = current - 4`"⇒ **一个"夹到最新四**"的先决**。**

**⇒ 三层**：
```text
若 `first < current - 4` ⇒ **它太旧** ⇒ **夹到 `current - 4`**
⇒ **⇒ 所以【最多四个**】
```

**✅ ⭐⭐ **"最多四个"**。

## 三、**"一个 appender 只能走一步，绝不能更多"**（本组第二重要）

### 3.1 那段

```cpp
// The cursor is 8-bit in effect -- the batch reader repairs a discontinuity by
// subtracting 256 -- and the ring is indexed by `cursor & 3`, so the slot to
// write is the one the CURRENT cursor names and the cursor moves after it.
const auto sequence = SV_ReadNativePredictableEventSequence(destination);
const auto ringIndex = static_cast<std::uint32_t>(sequence) & 3u;
writeValue(destination, PredictableEventsOffset + ringIndex * sizeof(SvNativePredictableEvent),
    SvNativePredictableEvent{ .event = event, .parameter = parameter });
// ONE STEP, NEVER MORE. SV_ReadNativePredictableEvents refuses a batch wider
// than four and that refusal fails the whole client think, so an appender that
// could jump the cursor would be a way to freeze the player.
writeValue(destination, PredictableEventSequenceOffset, sequence + 1);
```

### 3.2 二十四层

```text
1. **那个游标【在效果上是 `8` 位**】**
2. ⇒ **而【环按 `cursor & 3`**】索引**
3. ⇒ **⇒ 所以【要写的那个槽【是【当前游标**命名的那个**】
4. ⇒ **⇒ 而【那个游标【在它【之后**】移动**
5. ⇒ **⚠【一步，绝不能更多**】**
6. ⇒ **⇒ 因为【`SV_ReadNativePredictableEvents` **拒绝**一个【宽于四**的批**】**
7. ⇒ **⇒ 而【那个拒绝【让整个客户端 think 失败**】**
8. ⇒ **⇒ 所以【一个【能跳游标**的 appender【会是一种【把玩家冻住**】的方式】
```

### 3.3 ⭐⭐⭐ **"一个能跳游标的 appender 会是一种把玩家冻住的方式"**

**✅ 这是本报告里**最重要的一条"一个 API 的滥用面**。**

**✅ 与 §462 的"一个项失败不意味着那个值是坏的"**不同（这是**一个设计约束的防御**）。

**⇒ 三层**：
```text
若【一个 appender 能前进 `N > 1`**】⇒ **下一个批的 `current - first > 4`** ⇒ **拒绝** ⇒ **think 失败** ⇒ **玩家冻结**
⇒ **⇒ 所以【appender 【必须**只走一步**】
```

**✅ ⭐⭐⭐ **"appender 必须只走一步"** —— 一个**极清晰的约束**。

**⚠ 而"`sequence + 1` 而不是 `(sequence + 1) & 0xFF`"**⇒ **`sequence` 是 `int32` 而【它不会被截到 `8` 位**】。**

**⇒ 三层**：
```text
`sequence` 是 `int32` ⇒ **`sequence + 1` 可以到 `21 亿**】
而【那个批读者【修复回绕**】⇒ **所以 `int32` 是【足够的**】
⇒ **⇒ 所以【不需要一个显式的 `& 0xFF`**】
```

**✅ ⭐⭐ **"`int32` 足够所以不需要显式的 `& 0xFF`"**。

**⚠ 而 §462 的 `PredictableEventSequenceOffset` 是一个 `int32`**（`0x108`）✓

## 四、`SV_ReadNativeOffhandState` 的五个字段

```cpp
// CODREF(1649370): 429450 sets +4C=2047 on offhand entry; 4297D0
// loads WeaponDef+2284 into +48 while +4C=2047. 429DA0 separately
// tests the throwback timer +50 and selects its weapon from +54.
return {
    .weaponAssetIndex       = readValue<std::uint32_t>(source, 0x3E4),
    .grenadeTimeLeft        = readValue<std::int32_t>(source, 0x48),
    .field004C              = readValue<std::uint32_t>(source, 0x4C),
    .throwbackTimeLeft      = readValue<std::int32_t>(source, 0x50),
    .throwbackWeaponAssetIndex = readValue<std::uint32_t>(source, 0x54),
};
```

**⇒ 十层**：
```text
1. **`0x3E4` ⇒ 选中的副武器**（**§462 的 field `53`**）
2. ⇒ **`0x48` ⇒ 手雷的剩余时间**（**`4297D0` 从 `WeaponDef+2284` 加载**）
3. ⇒ **`0x4C` ⇒ `2047` 表示 offhand 入口**（**`429450` 设它**）
4. ⇒ **`0x50` ⇒ throwback 的剩余时间**（**`429DA0` 测它**）
5. ⇒ **`0x54` ⇒ throwback 的武器**（**`429DA0` 从它选**）
6. ⇒ **⇒ 五个字段，五个函数**
```

### 4.1 ⭐⭐⭐ **"`+0x4C = 2047` 表示 offhand 入口"**

**✅ 与 §464 二 的"`0x4C` 在 `Overlay` 里是 `grenadeEntityNum`"**——**一个双义**。

**⇒ 三层**：
```text
`SvPlayerState::grenadeEntityNum` ⇒ **`0x4C`**
而【`429450` 设 `+0x4C = 2047`** ⇒ **`EntityNumNone`** ⇒ **"没有手雷实体**"
⇒ **⇒ 所以【`2047` 是一个"没有**的哨兵**】
```

**✅ 与 §416 的"`EntityNumNone = 2047`"**——**第五次"`2047` 是哨兵** ✓

**⇒ 三层**：
```text
§414  **`field0058 = 2047`**
§416  **`EntityNumNone = 2047`**
§461  **`0x7FF = 2047` 是 `-1` 的位模式**
§464  **`+0x4C = 2047` 表示 offhand 入口**
⇒ **⇒ 四次"`2047`**】
```

**✅ ⭐⭐ **"`2047`"四例表**。

**⚠ 而"`429DA0` 在 `+4C = 2047` 时【加载 `WeaponDef+2284` 到 `+48`**"⇒ **一个三字段的交互**。**

**⇒ 三层**：
```text
`+0x4C == 2047` ⇒ **一个"入口**"状态**
而【在那个状态里 `+0x48` 是【一个从 `WeaponDef` 加载的值**】
⇒ **⇒ 所以【三个字段【必须一起读**】
```

**✅ ⭐⭐ **"三个字段必须一起读"** —— 而 **`SV_ReadNativeOffhandState` 正是那个"一起读"**。

## 五、四个 `Scripted*` 的"Pmove 之后重新应用"

### 5.1 `SV_SetNativePlayerStateScriptedMotion`

```cpp
writeValue(destination, PmTypeOffset, static_cast<std::int32_t>(pmType));
writeValue(destination, PmFlagsOffset, pmFlags);
writeFloatArray(destination, OriginOffset, origin);
writeFloatArray(destination, VelocityOffset, std::array<float, 3>{});
writeValue(destination, GroundEntityOffset, static_cast<std::int32_t>(groundEntityNum));
writeValue(destination, SpeedOffset, std::uint32_t{});
writeValue(destination, BobCycleOffset, std::uint32_t{});
writeValue(destination, MovementDirOffset, std::int32_t{});
```

**⇒ 十层**：
```text
1. **`pmType`/`pmFlags`/`origin` ⇒ 三个"设置**"**
2. ⇒ **`velocity` ⇒ 【零**】
3. ⇒ **`groundEntityNum` ⇒ 一个设置**
4. ⇒ **`speed`/`bobCycle`/`movementDir` ⇒ 【三个零**】**
5. ⇒ **⇒ 所以【一个"冻结**"的运动状态**（**速度零、步态零、方向零**）**
```

**✅ 与 §422 的"`setPlayerScriptedPosition` 在 Pmove 之后重新应用"**完全闭合 ✓

**⇒ 三层**：
```text
§422  **`setPlayerScriptedPosition` 在 Pmove 之后重新应用**
§464  **`SV_SetNativePlayerStateScriptedMotion` 是一个原生写者**
⇒ **⇒ 一写一调用的两个层次**
```

**✅ ⭐⭐ **"两个层次"**。

**⚠ 而"`+0x180`/`+0x188` 的 `ViewAngleClampBase/Range`"**⇒ **一个"相机夹**"**。

**⇒ 三层**：
```text
`ViewAngleClampBaseOffset = 0x180`（**`2` 个 `float`**）
`ViewAngleClampRangeOffset = 0x188`（**`2` 个 `float`**）
⇒ **⇒ 所以【两个 `float[2]` 的夹**】
```

**✅ 与 §417 的"`PlayerViewLinkState` 的 `clampBase`/`clampRange` 各 `float[2]`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§417  **`PlayerViewLinkState{ clampBase[2], clampRange[2], linkAngles[3], linkFlags }`**
§464  **`SV_SetNativePlayerStateScriptedViewLink(clampBase[2], clampRange[2], linkAngles[3], linkFlags)`**
⇒ **⇒ 一个一对一的写者**
```

**✅ ⭐⭐⭐ **"一个一对一的写者"** —— 而 **§417 的 `PlayerViewLinkState` 是那个原生结构的【一个源投影**】**。

## 六、`SV_ClearNativeGrenadeTimer` 的"清那个熟的计时器，不清 throwback"

```cpp
void SV_ClearNativeGrenadeTimer(SvNativePlayerState &candidate)
{
    // CODREF(grenade_timer): BO1 InitGrenadeTimer / Ghosts 140137E60
    // consume the cooked timer when the grenade becomes server-owned.
    // CODOL owns the offset; do not clear the distinct throwback state.
    writeValue(candidate, 0x48, std::int32_t{});
}
```

**⇒ 八层**：
```text
1. **只清 `0x48`（手雷的剩余时间**）**
2. ⇒ **理由：BO1 的 `InitGrenadeTimer` / Ghosts 的 `140137E60` 【在手雷变成服务器拥有时【消费那个熟的计时器**】】**
3. ⇒ **⚠ 而【不要清【那个【不同的** throwback 状态**】**
4. ⇒ **⇒ 所以【一个"精确的清除**"**
```

### 6.1 ⭐⭐⭐ **"不要清那个不同的 throwback 状态"**

**✅ 与 §464 四 的"`+0x48` 与 `+0x50` 是两个不同的计时器"**完全闭合 ✓

**⇒ 三层**：
```text
`+0x48` ⇒ **手雷（被烹饪的**）
`+0x50` ⇒ **throwback（扔回去**的）**
⇒ **⇒ 所以【两个计时器【不共用一个清除**】
```

**✅ ⭐⭐⭐ **"两个计时器不共用一个清除"** —— 与 §409 的"`NotPlaying` 与 `NotDead` 是同一个前提的两半"**相反**（**这里它们是不同的**）。

**⇒ 三层**：
```text
§440  **`NotPlaying`/`NotDead` ⇒ 同一前提 ⇒ 【可以合并**】
§464  **`+0x48`/`+0x50` ⇒ 不同计时器 ⇒ 【不可共用**】
⇒ **⇒ 一个精确的对照**
```

**✅ ⭐⭐ **"一个精确的对照"**。

## 七、`SV_ReadNativePlayerStateActionDiagnostics` 的九个字段

```cpp
return {
    .pmType, .clientNum, .viewmodelIndex, .currentWeaponAssetIndex,
    .weaponAnimation = { right, left },
    .weaponState = { right, left },
    .weaponShotCount = { right, left },
};
```

**⇒ 八层**：
```text
1. **四个标量 + 三个 `2` 元组 = `10` 个字段**
2. ⇒ **⇒ 所以【`pmType`/`clientNum`/`viewmodelIndex`/`currentWeaponAssetIndex` 四个**
3. ⇒ **而【`weaponAnimation`/`weaponState`/`weaponShotCount` 三个 `2` 元组**
4. ⇒ **⇒ 所以【`4 + 6 = 10` 个值**】
```

### 7.1 ⭐⭐⭐ **"原始的只读值解释投影的拒绝，而不创建另一个状态所有者"**

```cpp
// OLMOD(native-playerstate-action-diagnostics): raw read-only values
// explain projection rejection without creating another state owner.
```

**✅ 与 §459 的"`pmFlagsLogged` 只用于打到日志的去重，不参与任何游戏逻辑"**完全同族（**第五次"一个只读诊断**）。

**⇒ 三层**：
```text
§402  **`PMFLAGS|` 一个只读观测**
§459  **`pmFlagsLogged` 一个取证字段**
§462  **四十个 `refuse` 的命名**
§464  **`SV_ReadNativePlayerStateActionDiagnostics`**
⇒ **⇒ 四次"只读诊断**】
```

**✅ ⭐⭐ **"只读诊断"四例表**。</br>

**✅ 而"不创建另一个状态所有者"⇒ **一个与 §462 三 的"填它们服务端侧不能单独工作"**同族（**那里**创建了一个写者而失败**，这里**只读所以不会**）。

**⇒ 三层**：
```text
写 ⇒ **一个"状态所有者**" ⇒ **会失同步**
只读 ⇒ **一个"诊断**" ⇒ **无害**
⇒ **⇒ 所以【只读是【安全**的取证方式**
```

**✅ ⭐⭐⭐ **"只读是安全的取证方式"**。

## 八、关键结论

1. **⭐⭐⭐ "线缆送的是【环】，不是【批】：网络字段索引 `21..24` 是 `playerState +0x10C/+0x114/+0x11C/+0x124`（环槽 `0..3`），而客户端按 `sequence & 3` 索引它们，与 `SV_ReadNativePredictableEvents` 完全一样 ⇒ 【按批的顺序复制那个读器的输出会把对的事件放进错的槽，只要少于四个触发】**"` —— 而 **`0x114 - 0x10C = 8` 给出 `sizeof(SvNativePredictableEvent) = 8`**（`{int32 event, int32 parameter}`）。
2. **⭐⭐⭐ "修复那个 `8` 位游标的不连续：当 `old > current + 64` 时 `-= 256`"`** ⇒ **"那个 `-256` 正是一个模 `256` 的减法"** —— 第三次"模运算"（与 §417、§432 同族）；而 **`64` 是 `128` 的一半**（一个可能的保守选择）。
3. **⭐⭐ "`old < current - 4 ⇒ first = current - 4`"`** ⇒ **"最多四个"`**。
4. **⭐⭐ "与那个原生的 `void` 循环不同，这个源适配器【在 dispatch 之前】拒绝一个未来或过大的游标"`** —— 一个 **`CODDIFF(client_events)`**。
5. **⭐⭐⭐ "一个 appender 只能走【一步，绝不能更多**】：`SV_ReadNativePredictableEvents` 拒绝一个宽于四的批，而那个拒绝让整个客户端 think 失败 ⇒ 【一个能跳游标的 appender 会是一种把玩家冻住的方式**】"` —— 一个极清晰的 API 滥用面。
6. **⭐ "`sequence + 1` 而不是 `(sequence + 1) & 0xFF`，因为 `sequence` 是 `int32` 而那个批读者修复回绕，所以不需要一个显式的截断"`**。
7. **⭐⭐ `SV_ReadNativeOffhandState` 的五个字段**（`0x3E4` 选中的副武器 / `0x48` 手雷剩余时间 / `0x4C` offhand 入口哨兵 / `0x50` throwback 时间 / `0x54` throwback 武器），而 **`429450` 设 `+0x4C = 2047`（`EntityNumNone`）表示"没有手雷实体"** —— 第五次"`2047` 是哨兵"。
8. **⭐⭐ "`429DA0` 在 `+4C = 2047` 时从 `WeaponDef+2284` 加载 `+0x48`"`** ⇒ **"三个字段必须一起读"** —— 而 **`SV_ReadNativeOffhandState` 正是那个"一起读"**。
9. **⭐ 四个 `Scripted*` 写者**：`SV_SetNativePlayerStateScriptedMotion` 写 `pmType`/`pmFlags`/`origin`/`groundEntityNum` 并把 `velocity`/`speed`/`bobCycle`/`movementDir` **置零** ⇒ **一个"冻结"的运动状态**；`ScriptedViewLink` 与 §417 的 `PlayerViewLinkState`（`clampBase[2]`/`clampRange[2]`/`linkAngles[3]`/`linkFlags`）**一对一的写者**。
10. **⭐⭐ "清那个熟的计时器，但【不要清那个不同的 throwback 状态**】"` ⇒ **`+0x48`（被烹饪的）与 `+0x50`（扔回去的）是两个计时器** ⇒ **"两个计时器不共用一个清除"`** —— 与 §440 的"`NotPlaying`/`NotDead` 同一前提可合并"**一个精确的对照**。
11. **⭐⭐ `SV_ReadNativePlayerStateActionDiagnostics` 的"原始的只读值解释投影的拒绝，而【不创建另一个状态所有者**】"`** ⇒ **"只读是安全的取证方式"`** —— 第四次"只读诊断"（与 §402/§459/§462 同族），也是与"§462 的 `altWeaponSlots` 填了而失同步"**的一个精确对照**（**写会失同步，只读无害**）。

## 九、`sv_native_playerstate_mp.cpp` 全文件总览

**行数：`1,687`**。

**`105` 个偏移常量**（从 `CommandTimeOffset = 0x000` 到 `ObjectiveIconOffset = 0x20`），**`0x3564` → `0x3BBC`**。

**十一个结构区**：
```text
0x000..0x010  头部          commandTime / pmType / pmTime / pmFlags / otherFlags
0x028..0x0D4  运动          linkFlags / origin / velocity / gravity / speed / deltaAngles
0x0D8..0x104  动画/状态     legsTimer / legsAnim / torsoTimer / torsoAnim / movementDir / eFlags
0x108..0x158  事件/身份     predictableEventSequence / predictableEvents / clientNum
0x15C..0x238  视角          viewmodelIndex / viewAngles / clampBase / clampRange / linkAngles
0x1A4..0x214  生命          healthStat / deadYaw / maxHealthStat / spawnCount / health / maxHealth
0x284..0x2F0  冲刺/攀爬     sprint* / mantle*
0x2F4..0x330  武器列表      heldWeaponIndexes / heldWeaponStates
0x3E4..0x418  副武器/双持   offhandWeapon / currentWeapon / weaponPositionFraction / dualWield
0x41C..0x548  弹药          ammoPools / ammoClips
0x568..0x6C8  杂项/目标     unk04A4Time / shellshock* / objectives
```

**八个 `static_assert`**（§461），全部**钉在数组的末端**。

**六个 `SV_ReadNative*` / 八个 `SV_SetNative*` / 两个 `SV_Overlay*`**。

## 十、未闭合点

- `SV_NativePredictableEvent` 的 `sizeof = 8` 的确认。
- `unknownState[1..3]` 的语义。
- `0x568` 与 `+0x4A4` **两个数的差**（`Unk04A4TimeOffset = 0x568` 而注释说 `+0x4A4`）。
- `HostBreath` 的 `0x298`/`0x29C` 与 §418 的 `SvHoldBreathState` 的对应。
- **下一步**：`sv_map_triggers_mp.cpp`（`73,990` 字节）。
