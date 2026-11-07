# 503 · **"拒绝**原生的 `Com_Error`/默认分支【与【那个**零时长除法**分支【在**入口之前**"** —— `sv_trajectory_mp.*` 的 `36` 字节与三个 `static_assert`、`type 4/7/8` 的除法、以及 `type 3/7/8` 的**先加后夹**

## 一、范围

本报告学习 `sv_trajectory_mp.cpp`（**`2,038` 字节**）+ `.hpp`（**`1,502` 字节**）全文：`SvNativeTrajectory` 的 `36` 字节与两个 `offsetof`、`SV_IsTrajectoryValid` 的五条、以及 `SV_EvaluateTrajectory` 的 NaN 初始化。

## 二、**"拒绝原生的 `Com_Error`/默认分支与那个零时长除法分支在入口之前"**（本组最重要的一段）

### 2.1 那段

```cpp
// Refuse the native Com_Error/default and zero-duration division branches
// before entry. An absent/failing/partial native call never publishes a point.
```

### 2.2 二十四层

```text
1. **拒绝【那两个**分支【在**入口之前**】
2. ⇒ **⇒ ① 那个**原生的 `Com_Error`/默认**分支**】
3. ⇒ **⇒ ② 那个**零时长除法**分支**】
4. ⇒ **⇒ 而【一个**缺席/失败/部分**的原生调用【从不**发布一个点**
```

### 2.3 ⭐⭐⭐ **"一个缺席/失败/部分的原生调用从不发布一个点"**

**✅ 这是本报告里**最重要的一条"**一个**部分成功【绝不【外泄**"**。**

**✅ 与 §475 的"fail closed 并重试，绝不把玩家放进几何体"**、§493 的"从不绕过碰撞去逃出一个房间"**——**完全同族** ✓

**⇒ 三层**：
```text
缺席 ⇒ **⇒ 没有 `evaluate`**
失败 ⇒ **⇒ `evaluate` 返回 `false`**
部分 ⇒ **⇒ 那个点【是** NaN**
⇒ **⇒ 而【三者【都【返回 `nullopt`**
```

**✅ ⭐⭐⭐ **"三者都返回 nullopt"** —— 而**那个"部分"【被【那个 **NaN 初始化**捕获**。】

**⚠ 而那个**证据**】**。**

**⇒ 十六层**：
```cpp
const auto input = trajectory;
const auto missing = std::numeric_limits<float>::quiet_NaN();
std::array<float, 3> point{missing, missing, missing};
if (!evaluate(input, atTime, point) ||
    !std::ranges::all_of(point, [](float f) { return std::isfinite(f); }))
    return std::nullopt;
```
```text
1. **`input = trajectory` ⇒ 一个**副本**】⇒ **⇒ 所以【一个**故障的原生被调用者【不能【修改【那个所有者的**轨迹**
2. ⇒ **⇒ 而 `point` 【被【初始化为** NaN**】
3. ⇒ **⇒ 所以【一个【`evaluate` 【没有**写那个点【就返回 `true`**】的情形【会【被【那个 `isfinite` **捕获**
4. ⇒ **⇒ 而【那【正是【"**部分**"【那个词**的意思**
```

**✅ ⭐⭐⭐ **"'部分'那个词的意思：写了一个点的一部分（或没写）"** —— 一个**极精确的设计**。

**✅ 与 §468 的"`claim` 的三态"**——**同族**（**第五次"一个**初始化【的**哨兵**"**）。

**⇒ 三层**：
```text
§468  **`0xFFFFFFFF` ⇒ 载荷内联 / `0` ⇒ NULL / 其它 ⇒ 拒绝**
§503  **NaN ⇒ 未写 / 有限 ⇒ 已写 / 混合 ⇒ 拒绝**
⇒ **⇒ 两次【一个**哨兵【的**初始化**"**
```

**✅ ⭐⭐⭐ **"一个哨兵的初始化"两例**。

**⚠ 而"`input = trajectory` 的副本"**】**。**

**⇒ 十层**：
```text
"Keep even a faulty native callee from modifying the owner's trajectory."
⇒ **⇒ 所以【那个**副本【是【一个**防线**】（**⇒ 一个**坏的**原生【不能**改【那个所有者的状态**）
```

**✅ ⭐⭐⭐ **"那个副本是一个防线"** —— 与 §471 的"三个伤害/撞击载荷是候选副本"**同族**（**第六次"一个**候选副本**"**）。

## 三、**`36` 字节与两个 `offsetof`**（本组第二重要）

### 3.1 那三个 `static_assert`

```cpp
static_assert(sizeof(SvNativeTrajectory) == 36);
static_assert(offsetof(SvNativeTrajectory, base) == 12);
static_assert(offsetof(SvNativeTrajectory, delta) == 24);
```

### 3.2 二十四层

```text
1. **`36` 字节**】⇒ **⇒ `3` 个 `int32` + `2` 个 `float[3]`（`12 + 12 + 12`**）
2. ⇒ **⇒ 而 `base` 在 `12`**】（**⇒ 那三个 `int32` 之后**）
3. ⇒ **⇒ 而 `delta` 在 `24`**】（**⇒ 那个 `base` 之后**）
4. ⇒ **⇒ 所以【那【是【一个**紧密的**布局，而【没有**填充**
```

### 3.3 ⭐⭐⭐ **"36 = 12 + 12 + 12，一个紧密的布局，没有填充"**

**✅ 与 §502 的"`0x2C` 与 `0x12C`"**——**同族** ✓

**⇒ 三层**：
```text
§502  **`sizeof(SvNativeUserCmd) == 0x2C`** / **`sizeof(SvNativePmove) == 0x12C`**
§503  **`sizeof(SvNativeTrajectory) == 36` + 两个 `offsetof`**
⇒ **⇒ 两次【一个**布局【被【钉住**
```

**✅ ⭐⭐⭐ **"一个布局被钉住"两例** —— 而**§503 【加了【两个 `offsetof`**】**（**⇒ 那【比【只有一个 `sizeof`【更强**）**。**

**⇒ 三层**：
```text
`sizeof` ⇒ **一个**总长度**的保证**
`offsetof` ⇒ **一个**内部位置**的保证**
⇒ **⇒ 所以【后者【是【一个**更强的**契约**
```

**✅ ⭐⭐⭐ **"后者是一个更强的契约"**。

**⚠ 而"一个 36 字节的 trajectory"**⇒ **与 §475 的 `SvNativeTrajectory` 同名**】**。**

**⇒ 核实**：§475 的 `sv_zm_box_mp.cpp` 用了 `SvNativeTrajectory{.type=7,.time=...,.duration=2000,.base=origin,.delta={0,0,speed}}` ⇒ **同一个类型**。

**⇒ 三层**：
```text
§475  **`SvNativeTrajectory` 的 `type 7`（**那个升起的**运动**）
§503  **`SV_IsTrajectoryValid` 的 `type 4/7/8` 需要 `duration != 0`**
⇒ **⇒ 所以【§475 的那个 `duration = 2000` 【满足**那个要求** ✓
```

**✅ ⭐⭐⭐ **"§475 的那个 duration = 2000 满足那个要求"** —— 一个**跨报告的验证**。

## 四、**`type 3/7/8` 的"先加后夹"**（本组第三重要）

### 4.1 那段

```cpp
// CODREF(1649370): 410C50/410D75/410DF7 divide by duration for 4/7/8.
if ((trajectory.type == 4 || trajectory.type == 7 || trajectory.type == 8) &&
    !trajectory.duration) return false;
...
// Native limited trajectories add signed time+duration before clamping.
if (trajectory.type == 3 || trajectory.type == 7 || trajectory.type == 8)
    return std::int64_t{trajectory.time} + trajectory.duration <=
        std::numeric_limits<std::int32_t>::max();
return true;
```

### 4.2 二十四层

```text
1. **`410C50`/`410D75`/`410DF7` 【对 `4`/`7`/`8` 【除以【那个 `duration`**】
2. ⇒ **⇒ 所以【那三种【必须有【一个**非零**的 `duration`
3. ⇒ **⇒ 而【那个**原生的有限轨迹【在夹之前【做【一个有符号的 `time + duration`**】
4. ⇒ **⇒ 所以【那三种（`3`/`7`/`8`）【必须有 `time + duration <= INT32_MAX`**
```

### 4.3 ⭐⭐⭐ **"原生的有限轨迹在夹之前做一个有符号的 time + duration"**

**✅ 与 §476 的"`wallThickness` 有一个 `1.0` 的下限"**、§489 的"`field0058 = 2047`"**——**不同**，但与 §471 的"`entryDepthValue` 的那个 `16.0f` 下限"**同族**（**第七次"一个**溢出【的**守卫**"**）。

**⇒ 三层**：
```text
`time + duration` ⇒ **一个 `int64` 的加法**】⇒ **⇒ 而【那【避免【一个**int32 的溢出**
⇒ **⇒ 然后【与 `INT32_MAX` 比较**】⇒ **⇒ 所以【那个加法【本身【在 `int64` 里【不【溢出**
```

**✅ ⭐⭐⭐ **"那个加法本身在 int64 里不溢出"** —— 与 §495 的"`remainingDamage` 是 `int64`"**同族**（**第七次"一个**更宽的中间类型**"**）。

**⚠ 而那个**两个集合的差**】**。**

**⇒ 十层**：
```text
需 `duration != 0` ⇒ **`{4, 7, 8}`**
需 `time + duration <= INT32_MAX` ⇒ **`{3, 7, 8}`**
⇒ **⇒ 交集 ⇒ `{7, 8}`**】⇒ **⇒ 所以【两种【都【需** ⇒ `{7, 8}`
⇒ **⇒ 而 `4` 【只【需第一个**】⇒ **⇒ 而 `3` 【只【需第二个**
```

**✅ ⭐⭐⭐ **"交集是 {7, 8}；4 只需第一个；3 只需第二个"** —— 一个**极精确的集合分析**。

**✅ 与 §488 的"`methodOfDeath` 的三分支"**——**同族**（**第八次"一个**集合的**分析**"**）。

**⚠ 而那个 `type ∈ [0, 12]` 的**总界**】**。**

**⇒ 三层**：
```text
`type < 0 || type > 12 ⇒ 拒绝`
⇒ **⇒ 而 §489 说**："**`sub_AB29C0` 只处理 `0..12`，其余【落到 `Com_Error(2, "90 %i", trType)`**"
⇒ **⇒ 所以【那个 `12` 【是【那个**原生 switch 的上界**
```

**✅ ⭐⭐⭐ **"那个 12 是那个原生 switch 的上界"** —— 与 §489 的"`trType 13` 在本 build 上不存在"**完全闭合** ✓

**⇒ 三层**：
```text
§489  **`trType = 13` ⇒ `Com_Error(2, "90 %i", trType)`**（**一个**活的客户端【弹了那个错误对话框**）
§503  **`type > 12 ⇒ 拒绝**】
⇒ **⇒ 所以【§503 【在【入口【就【挡住了【那个**曾【弹了错误对话框**的情形】
```

**✅ ⭐⭐⭐ **"§503 在入口就挡住了那个曾弹了错误对话框的情形"** —— 一个**跨报告的完整闭合**。

## 五、`difference` 的 `int64` 与那个 `INT32` 的界

### 5.1 那段

```cpp
const auto difference = std::int64_t{atTime} - trajectory.time;
if (difference < std::numeric_limits<std::int32_t>::min() ||
    difference > std::numeric_limits<std::int32_t>::max()) return false;
```

### 5.2 二十四层

```text
1. **`atTime - time` 用 `int64`**】⇒ **⇒ 所以【那个减法【不【溢出**
2. ⇒ **⇒ 而【然后【检查【它【是否【在【一个 `int32` 的**范围**里**
3. ⇒ **⇒ 所以【那个 `difference` 【是一个**有界的**值**
```

### 5.3 ⭐⭐⭐ **"那个减法在 int64 里，然后检查它是否在一个 int32 的范围里"**

**✅ 与 §469 的"`static_cast<std::int32_t>(serverTime - wakeServerTime) >= 0`"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§469  **用一个**有符号 `int32` 的差【处理【回绕**】
§503  **用一个**`int64` 的差【然后**检查界**
⇒ **⇒ 两个**不同的**策略，【都【是【为了**回绕/溢出**】
```

**✅ ⭐⭐⭐ **"两个不同的策略，都是为了回绕/溢出"**。

**⚠ 而那个 `difference` 【被**计算【但【从不【被用**（**除了【那个界检查**）】**。**

**⇒ 十层**：
```text
`difference` ⇒ **只【在【那个界检查里**用】
⇒ **⇒ 而【它【不被【传给【那个 `evaluate`**】
⇒ **⇒ 所以【那个检查【是【一个**纯粹的前置条件**
```

**✅ ⭐⭐⭐ **"那个检查是一个纯粹的前置条件"** —— 而**它【保护【那个**原生【会做的**同一个减法**）**。**

## 六、"`0x410EA0` 接受一个地址混淆的 base；源所有的轨迹用那个简单入口"

### 6.1 那段

```cpp
// CODREF(1649370): BG_EvaluateTrajectory 0x410BD0 reads a plain 36-byte
// trajectory: type/time/duration, base, delta. 0x410EA0 instead accepts an
// address-obfuscated base. Source-owned trajectories use the plain entry.
// This record is NOT embedded in address-bound WorldClientState.
```

### 6.2 二十四层

```text
1. **两个**入口**：`0x410BD0`（**plain 36 字节**）与 `0x410EA0`（**地址混淆的 base**）
2. ⇒ **⇒ 而【源所有的轨迹【用【那个**简单**入口**
3. ⇒ **⇒ 而【那个记录【**不【被【内嵌【在【那个**地址绑定的 `WorldClientState`** 里**
```

### 6.3 ⭐⭐⭐ **"这个记录不被内嵌在地址绑定的 WorldClientState 里"**

**✅ 与 §422 的"`static_assert(sizeof(WorldClientState) == 25184)`"**、§481 的"一个地址绑定的 entityState"**——**完全同族** ✓

**⇒ 三层**：
```text
§422  **`WorldClientState` 的 `25184` 【是一个**行为**】
§481  **一个 `entityState` 【地址绑定** ⇒ **⇒ 一个 C++ 拷贝【会【破坏它**
§503  **"This record is NOT embedded in address-bound WorldClientState"** ⇒ **⇒ 所以【那个**拷贝【是安全的**
⇒ **⇒ 三次"一个**地址绑定【的**边界**"**
```

**✅ ⭐⭐⭐ **"一个地址绑定的边界"三例表**。

**⚠ 而"两个入口"**⇒ **一个**明确的分工**。**

**⇒ 十层**：
```text
`0x410BD0` ⇒ **plain**（**⇒ 一个**简单的** base**）
`0x410EA0` ⇒ **地址混淆**（**⇒ 一个**受保护的** base**）
⇒ **⇒ 所以【那个引擎【有【两个**版本的同一函数**】
```

**✅ ⭐⭐⭐ **"那个引擎有两个版本的同一函数"** —— 与 §481 的"`ps+0x10` 的三个 dword 受保护值"**同族**。

## 七、关键结论

1. **⭐⭐⭐ "拒绝那个原生的 `Com_Error`/默认分支与那个零时长除法分支**在入口之前**。一个缺席/失败/部分的原生调用**从不发布一个点**"`** ⇒ **"三者都返回 nullopt"** ⇒ **而那个"部分"【被【那个 **NaN 初始化**捕获** —— 与 §475/§493 的"fail closed"**完全同族**。
2. **⭐⭐⭐ "`input = trajectory` 的副本 + `point` 的 NaN 初始化"** ⇒ **"那个副本是一个防线"**（一个坏的原生不能改那个所有者的状态）与 §471 的"三个候选副本"**同族**；而 **"'部分'那个词的意思：写了一个点的一部分（或没写）"** ⇒ **"一个哨兵的初始化"**（与 §468 的 `claim` 三态同族）。
3. **⭐⭐⭐ 三个 `static_assert`**（`sizeof == 36` / `offsetof(base) == 12` / `offsetof(delta) == 24`）⇒ **"36 = 12 + 12 + 12，一个紧密的布局，没有填充"** 而 **"两个 offsetof 是比一个 sizeof 更强的契约"**（与 §502 同族）；而 **那个类型与 §475 的 `SvNativeTrajectory` 是同一个**，且 **§475 的 `duration = 2000` 满足 §503 的 `duration != 0` 要求 ✓**。
4. **⭐⭐⭐⭐ 两个集合的精确分析**：需 `duration != 0` ⇒ `{4, 7, 8}`（`410C50`/`410D75`/`410DF7` 的除法）；需 `time + duration <= INT32_MAX` ⇒ `{3, 7, 8}`（**"原生的有限轨迹在夹之前做一个有符号的 `time + duration`"**）⇒ **交集是 `{7, 8}`**，`4` 只需第一个，`3` 只需第二个。
5. **⭐⭐⭐ "那个 `time + duration` 的加法在 `int64` 里，然后与 `INT32_MAX` 比较"** ⇒ **"那个加法本身在 int64 里不溢出"**（与 §495 的 `remainingDamage` 同族）。
6. **⭐⭐⭐⭐ `type > 12 ⇒ 拒绝` 与 §489 的 `trType 13` ⇒ `Com_Error(2, "90 %i", trType)` 完整闭合** ⇒ **"§503 在入口就挡住了那个曾弹了错误对话框的情形"** —— 一个**跨报告的完整闭合**（`sub_AB29C0` 只处理 `0..12`）。
7. **⭐⭐⭐ `difference` 的 `int64` 减法 + 一个 `int32` 的界检查** 与 §469 的 `static_cast<int32_t>(serverTime - wake)` **一个精确的对照**（**两个不同的策略都是为了回绕/溢出**）；而那个 `difference` **只用于那个界检查** ⇒ **"那个检查是一个纯粹的前置条件"**（它保护那个原生会做的同一个减法）。
8. **⭐⭐⭐ "`0x410BD0` 读一个简单的 `36` 字节轨迹；`0x410EA0` 反而接受一个地址混淆的 base；源所有的轨迹用那个简单入口；这个记录**不被内嵌在地址绑定的 `WorldClientState` 里**"`** ⇒ **"一个地址绑定的边界"**（第三次，与 §422/§481 同族）⇒ 而 **"那个引擎有两个版本的同一函数"**。

## 八、`sv_trajectory_mp` 全文件总览

**`.cpp`：`2,038` 字节。`.hpp`：`1,502` 字节。**

**`3` 个 `static_assert`**：`sizeof == 36` / `offsetof(base) == 12` / `offsetof(delta) == 24`。

**`5` 个 `SvNativeTrajectory` 字段**：`type` / `time` / `duration` / `base[3]` / `delta[3]`。

**`2` 个函数**：`SV_IsTrajectoryValid` / `SV_EvaluateTrajectory`。

**`5` 条有效性判据**：
```text
① type ∈ [0, 12]
② duration >= 0
③ base 与 delta 有限
④ type ∈ {4,7,8} ⇒ duration != 0
⑤ type ∈ {3,7,8} ⇒ time + duration <= INT32_MAX
   （另：atTime - time 的差必须落在一个 int32 里）
```

**`4` 个反汇编锚点**：`BG_EvaluateTrajectory 0x410BD0` / `0x410EA0`（地址混淆）/ `410C50` / `410D75` / `410DF7`（三个除法点）。

## 九、未闭合点

- `type` 的 `13` 种语义（`0..12`）。
- `0x410EA0` 那个地址混淆 base 的调用者。
- 下一个文件：`sv_radius_damage_mp.cpp/.hpp`（`7,955` / `4,047`）+ `sv_radius_visibility_mp.cpp`（`2,576`）。
