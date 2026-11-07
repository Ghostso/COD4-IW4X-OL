# 502 · **"那两层布局【都由【一个**`static_assert`【钉住**"** —— `sv_native_pmove_mp.*` 的 `0x2C`/`0x12C`、`15` 种失败、以及 `numTouch` 的 `0..32`

## 一、范围

本报告学习 `sv_native_pmove_mp.cpp`（**`142` 行**）+ `.hpp`：`SvNativeUserCmd`/`SvNativePmove` 两个 `static_assert`、`15` 种 `SvNativePmoveFailure`、`SV_ReadNativePmoveOutput` 的五道 + `SV_IsNativePmoveOutputValid` 的八道。

## 二、**"两层布局都由一个 static_assert 钉住"**（本组最重要的一段）

### 2.1 那两个 `static_assert`

```cpp
static_assert(sizeof(SvNativeUserCmd) == 0x2C);
static_assert(sizeof(SvNativePmove) == 0x12C);
```

### 2.2 二十四层

```text
1. **`usercmd_s = 0x2C` 与 `pmove_t = 0x12C` 【两个**尺寸**
2. ⇒ **⇒ 而【两者【都【被【一个 `static_assert` 【钉住**】
3. ⇒ **⇒ 所以【一个**字段的增删【会【在**编译期【失败**】
4. ⇒ **⇒ 而【不是【在【运行时【产生【一个**错的偏移**
```

### 2.3 ⭐⭐⭐ **"一个字段的增删会在编译期失败，而不是在运行时产生一个错的偏移"**

**✅ 与 §468 的"`static_assert(sizeof(void*) == 4)`"**、§489 的"`static_assert(SvCorpseSettleRespawnSeparationMs > 0)`"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **`sizeof(void*) == 4`**（**⇒ 一个**位数**的保证**）
§489  **`SvCorpseSettleRespawnSeparationMs > 0`**（**⇒ 一个**不变式**的保证**）
§502  **`sizeof(SvNativeUserCmd) == 0x2C`**（**⇒ 一个**布局**的保证**）
⇒ **⇒ 三次"一个 `static_assert` 是一个行为"**
```

**✅ ⭐⭐⭐ **"一个 static_assert 是一个行为"三例表**。

**⚠ 而那个**注释的推导链**】**。**

**⇒ 十六层**：
```cpp
// CODREF(pmove): CODOL usercmd_s=0x2C and pmove_t=0x12C are confirmed by
// ...
// of a 0x12C struct, and 0x1E is cmd + 0x1A = forwardMove, so both layouts
// ... 0x28/0x2C/0x30 -> 0x3C/0x40/0x44 -- which the netfield
```
```text
1. **`0x1E` 是 `cmd + 0x1A` = `forwardMove`**】⇒ **⇒ 所以【那【给出了【一个**锚点**
2. ⇒ **⇒ 而 `0x28/0x2C/0x30 → 0x3C/0x40/0x44`**】⇒ **⇒ 而【那【是那个**网络字段**的对齐**
3. ⇒ **⇒ 所以【那个布局【被【**两**条独立的路径**验证**】：**指令**与【网络字段表**
```

**✅ ⭐⭐⭐ **"那个布局被两条独立的路径验证"** —— 与 §481 的"两张 `ET_PLAYER` 网络字段表按 `(bits, codec)` 对齐 + `BG_PlayerStateToEntityState` 逐指令"**完全同族** ✓

**⇒ 三层**：
```text
§481  **`(bits, codec)` 对齐 + 一个拷贝器**
§502  **`cmd + 0x1A` + 网络字段对齐**
⇒ **⇒ 两次"一个**布局【由【两条独立的路径**"**
```

**✅ ⭐⭐⭐ **"一个布局由两条独立的路径"两例**。

## 三、`15` 种失败与"一个名字（不是 `WrongThread` 那种死状态）"（本组第二重要）

### 3.1 十五种

```text
None / InvalidBinding / InvalidCommand / WrongThread / ReentrantCall
HandlerSlotBusy / AnimConditionInstallFailed / NonIncreasingCommandTime
SliceLimitExceeded / CommandTimeNotAdvanced / NativeException
HandlerRestoreFailed / TraceFailed / AnimConditionRestoreFailed / InvalidOutput
```

### 3.2 二十四层

```text
1. **`14` 个失败 + `None`**
2. ⇒ **⇒ 而【那个 `WrongThread` 【在这里【是【一个**真的**状态**】（**与 §468 的 `SvForgeXAnimStatus::WrongThread` **相反**）
3. ⇒ **⇒ 而【那【是【因为【这个模块【真的【检查【线程**
```

### 3.3 ⭐⭐⭐ **"`WrongThread` 在这里是一个真的状态，与 §468 的相反"**

**✅ 与 §468 的"`SvForgeXAnimStatus::WrongThread` 全文件没有生产者"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§468  **`SvForgeXAnimStatus::WrongThread` 【没有生产者**】（**⇒ 一个**死状态**）
§502  **`SvNativePmoveFailure::WrongThread`**（**⇒ 而【这个模块【真的【检查【线程**）
⇒ **⇒ 所以【同一个名字【两处【一个死一个活**
```

**✅ ⭐⭐⭐ **"同一个名字两处一个死一个活"** —— 一个**极重要的**分辨**（**⇒ 那验证了 §468 的那个观察【是【一个**真的**缺陷**）**。**

**⚠ 而那个**八种"安装/恢复"的对称**】**。**

**⇒ 十层**：
```text
`AnimConditionInstallFailed`  ⇄  `AnimConditionRestoreFailed`
`HandlerSlotBusy`             ⇄  `HandlerRestoreFailed`
⇒ **⇒ 所以【那个模块【**安装**一个东西【然后【必须**恢复**它**】⇒ **⇒ 而【两者【各自【一个**失败**
```

**✅ ⭐⭐⭐ **"安装与恢复各自一个失败"** —— 而**那【是【一个**对称的**契约**（**与 §471 的 `GlassCommandRollback`**同族**）**。**

**⇒ 三层**：
```text
§471  **`~GlassCommandRollback` 【在【失败时【恢复**】
§502  **`AnimConditionRestoreFailed` / `HandlerRestoreFailed`**（**⇒ 两个**恢复的失败**
⇒ **⇒ 两次"一个**恢复【可以【自己**失败**
```

**✅ ⭐⭐⭐ **"一个恢复可以自己失败"两例**。

**⚠ 而"`CommandTimeNotAdvanced`"**】**。**

**⇒ 三层**：
```text
`NonIncreasingCommandTime` ⇒ **那个输入【不递增**】
`CommandTimeNotAdvanced` ⇒ **那个原生阶段【没有**推进**它**
⇒ **⇒ 两个**不同的**判据**（**⇒ 一个**输入**，一个**输出**）
```

**✅ ⭐⭐⭐ **"两个不同的判据：一个输入，一个输出"**。

## 四、`numTouch` 的 `0..32`

### 4.1 那道

```cpp
if (pmove.numTouch < 0 || pmove.numTouch > 32 || pmove.handler != 0 || pmove.mantleStarted > 1)
    return std::nullopt;
```

### 4.2 二十四层

```text
1. **`numTouch ∈ [0, 32]`**】
2. ⇒ **⇒ 而 `handler == 0`**】（**⇒ 一个**必须是 NULL** 的字段**）
3. ⇒ **⇒ 而 `mantleStarted ∈ {0, 1}`**】（**⇒ 一个**布尔**
```

### 4.3 ⭐⭐⭐ **"`handler == 0` —— 一个必须是 NULL 的字段"**

**✅ 与 §468 的"一个已发布的资产永不释放，因为引擎持有指针"**——**不同**（那里**必须保留**，这里**必须为空**）但**同族**（**第七次"一个**指针【的**生命周期**"**）。

**⇒ 三层**：
```text
§468  **`published` 的 `unique_ptr` 【永不释放**
§502  **`pmove.handler != 0 ⇒ 拒绝**】（**⇒ 一个**必须是空**的指针**）
⇒ **⇒ 两个**相反的**要求，【都【是【为了**所有权**】
```

**✅ ⭐⭐⭐ **"两个相反的要求，都是为了所有权"**。

**⚠ 而那个**八道的 `SV_IsNativePmoveOutputValid`**】**。**

**⇒ 十层**：
```text
① `numTouch > touchEntities.size()`
② `bounds.midpoint` 有限
③ `bounds.halfSize` 有限
④ `halfSize >= 0`
⑤ `xySpeed` 有限且 `>= 0`
⑥ `mantleEndPosition` 有限
⑦ `viewChange` / `torsoPitch` / `waistPitch` 有限
⑧ 前 `numTouch` 个 `touchEntities <= 2047`
⇒ **⇒ 八道**
```

**✅ ⭐⭐⭐ **"八道，而第 ⑧ 道只看前 numTouch 个"** —— 与 §471 的 `SV_ShouldClipToEntity`**同族**。

**⇒ 三层**：
```text
`.begin()` 到 `.begin() + numTouch` ⇒ **⇒ 只【遍历那个**有效的**前缀**
⇒ **⇒ 而【那个 `numTouch > size()` 的检查【保证【那个**前缀【在界内**
⇒ **⇒ 所以【两道【联合【保证【安全**
```

**✅ ⭐⭐⭐ **"两道联合保证安全"** —— 与 §498 的"三条减法之前都有检查"**同族**（**第八次"一个**界【的守卫**"**）。

## 五、`32` 与 §472 的 `MaximumGameClients = 18`

### 5.1 那道

**⇒ 十层**：
```text
`numTouch <= 32` ⇒ **⇒ 而【§446 的 `SvAgentSlotCount = 32`**】⇒ **⇒ 一个**共享的**数**
而 `MaximumGameClients = 18` ⇒ **另一个**
⇒ **⇒ 所以【两个**不同的**上界**（**`32` = 那个触摸列表**，`18` = 那个玩家数**）
```

**✅ ⭐⭐⭐ **"32 = 那个触摸列表，18 = 那个玩家数"**。

**✅ 与 §446 的"`spawnActor` 的槽 `0..23` 而 `SvAgentSlotCount = 32`"**——**同族**（**第二次"一个**32【与【一个**更小的**界**"**）。

## 六、"那三个字段的语义【还没有【被证明**"**

### 6.1 那段

```cpp
// TODO(CODOL): prove proneChange, mantleDuration and viewChangeTime
// sentinel/range semantics from CODOL write and consumer sites. Exit
// when current i64 field xrefs or disassembly plus BO1/Ghosts control
// flow establish their exact domains and fixed regressions cover them.
```

### 6.2 二十四层

```text
1. **三个字段【还没有【被**证明**】：`proneChange` / `mantleDuration` / `viewChangeTime`
2. ⇒ **⇒ 而【那个退出条件【是**三个**：
3. ⇒ **⇒ ① 当前的 i64 字段 xref
4. ⇒ **⇒ ② 或【反汇编 + BO1/Ghosts 的控制流
5. ⇒ **⇒ ③ 而【固定的**回归【覆盖**它们
```

### 6.3 ⭐⭐⭐ **"三个字段还没有被证明 —— 而那个退出条件是三个"**

**✅ 与 §492 的"那个 `TODO` 的退出条件需要四个参考全部被证明不存在"**——**同族** ✓

**⇒ 三层**：
```text
§492  **一个 `TODO` 的退出条件【需要【四个**参考**
§502  **一个 `TODO` 的退出条件【需要【三个**证据**
⇒ **⇒ 两次"一个** TODO 有【一个**可判定的**退出条件**"**
```

**✅ ⭐⭐⭐ **"一个 TODO 有一个可判定的退出条件"两例**。

**✅ 而那三个字段【仍然【被【**读【并【传递**】】（**不是【被【拒绝**）**。**

**⇒ 十层**：
```text
`proneChange` ⇒ **被读并传出**（**而不【被【校验**）
`mantleDuration` ⇒ **同上**
`viewChangeTime` ⇒ **同上**
⇒ **⇒ 所以【那个"未证明"【只【影响【那个**完整性的检查**，不【阻止【传递**
```

**✅ ⭐⭐⭐ **"'未证明'只影响那个完整性的检查，不阻止传递"** —— 与 §485 的"`view.velocity = {}`"**同族**（**一个**有意的**不检验**）**。**

**⚠ 而"`mantleStarted > 1` ⇒ 拒绝"**⇒ **⇒ 那【一个【**有界**的字段【被【校验了**）**。**

**⇒ 三层**：
```text
`mantleStarted` ⇒ **有界（`0..1`）⇒ **被校验**
`proneChange` / `mantleDuration` / `viewChangeTime` ⇒ **无界 ⇒ **不被校验**
⇒ **⇒ 所以【那个**分界【是【"有界性【是否【被证明**"
```

**✅ ⭐⭐⭐ **"那个分界是『有界性是否被证明』"**。

## 七、关键结论

1. **⭐⭐⭐ 那两个 `static_assert`（`sizeof(SvNativeUserCmd) == 0x2C` 与 `sizeof(SvNativePmove) == 0x12C`）** ⇒ **"一个字段的增删会在编译期失败，而不是在运行时产生一个错的偏移"** —— **第三次"一个 `static_assert` 是一个行为"**（与 §468/§489 同族）。
2. **⭐⭐⭐ 那个布局被两条独立的路径验证**：`0x1E` 是 `cmd + 0x1A` = `forwardMove`（**一个指令锚点**）与 `0x28/0x2C/0x30 → 0x3C/0x40/0x44`（**那个网络字段的对齐**）⇒ 与 §481 的"`(bits, codec)` 对齐 + 一个拷贝器"**完全同族**。
3. **⭐⭐⭐ `15` 种失败（`14` 个 + `None`）**，其中 **`WrongThread` 在这里是一个真的状态，与 §468 的相反**（那里"全文件没有生产者"）⇒ **"同一个名字两处一个死一个活"** —— **而那验证了 §468 的那个观察是一个真的缺陷**。
4. **⭐⭐⭐ 八种"安装/恢复"的对称**：`AnimConditionInstallFailed` ⇄ `AnimConditionRestoreFailed`、`HandlerSlotBusy` ⇄ `HandlerRestoreFailed` ⇒ **"安装与恢复各自一个失败"**（与 §471 的 `GlassCommandRollback` 同族）。
5. **⭐⭐⭐ `NonIncreasingCommandTime` 与 `CommandTimeNotAdvanced`** ⇒ **"两个不同的判据：一个输入，一个输出"**。
6. **⭐⭐⭐ `handler == 0` 是一个必须是 NULL 的字段** ⇒ **"两个相反的要求，都是为了所有权"**（与 §468 的"一个已发布的资产永不释放"对照）。
7. **⭐⭐⭐ `SV_IsNativePmoveOutputValid` 的八道，而第 ⑧ 道只看前 `numTouch` 个** ⇒ **"两道联合保证安全"**（`numTouch > size()` 的检查 + 只遍历那个前缀）—— 与 §498 同族。
8. **⭐⭐ `numTouch <= 32` 与 §446 的 `SvAgentSlotCount = 32` 是同一个数**，而 `MaximumGameClients = 18` 是**另一个** ⇒ **"32 = 那个触摸列表，18 = 那个玩家数"**。
9. **⭐⭐⭐ `TODO(CODOL)` 的三个未证字段**（`proneChange`/`mantleDuration`/`viewChangeTime`）与**三个退出条件**（i64 xref / 反汇编 + BO1/Ghosts 控制流 / 固定回归）⇒ **"一个 TODO 有一个可判定的退出条件"**（与 §492 同族）；而 **"'未证明'只影响那个完整性的检查，不阻止传递"** ⇒ **"那个分界是『有界性是否被证明』"**（`mantleStarted` 有界 ⇒ 被校验；那三个无界 ⇒ 不被校验）。

## 八、`sv_native_pmove_mp` 全文件总览

**`.cpp`：`142` 行。**

**`2` 个 `static_assert`**：`0x2C`（usercmd_s）/ `0x12C`（pmove_t）。

**`15` 种 `SvNativePmoveFailure`**。

**`2` 个函数**：`SV_ToNativeUserCmd` / `SV_NativePmoveFailureName` / `SV_ReadNativePmoveOutput` / `SV_IsNativePmoveOutputValid`。

**`11` 个输出字段**：`numTouch` / `bounds` / `xySpeed` / `proneChange` / `mantleStarted` / `mantleEndPosition` / `mantleDuration` / `viewChangeTime` / `viewChange` / `torsoPitch` / `waistPitch`。

**`12` 个 `SvNativeUserCmd` 字段**：`commandTime` / `buttons` / `angles[3]` / `weapon` / `offHandIndex` / `lastWeaponAltModeSwitch` / `forwardMove` / `rightMove` / `conditionalAngle` / `conditionalByte` / `conditionalElevenBits` / `selectedLocation` / `selectedDirection`。

**`4` 个反汇编锚点**：`Pmove 0x0041E860`（CODOL）/ BO1 `0x004385F0` / Ghosts `0x140082BE0`。

## 九、未闭合点

- `proneChange` / `mantleDuration` / `viewChangeTime` 的语义（注释明说未证明）。
- `SvNativePmove::Size` 与那几个 `static_assert` 之外的布局。
- `handle != 0` 的实际消费者。
- 下一个文件：`sv_trajectory_mp.cpp/.hpp`（`2,038` / `1,502`）。
