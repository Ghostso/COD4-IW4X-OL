# 223 · lerp 帧选择子的两个错误、去重键里混进三个时钟

## 一、范围

本报告学习 `EngineBindings.cpp` 5710–5910 行。

## 二、lerp 帧初始化的两个独立错误

### 2.1 第一个：**范围是 0..32 不是 0..33**

```cpp
// CODDIFF(1649370): the initializer accepts 0..32, not 0..33 -- its own
// `cmp ebx, 0x20; ja` says so, on both builds. Picking modulo 34 handed it an
// out-of-range selector about one spawn in thirty-four,
```

**`cmp ebx, 0x20; ja`** —— `0x20 = 32`，**`ja` 是"大于则跳"** ⇒ **接受 0..32**（33 个值）。

而 `SvNativeLerpFrameSelectorCount = 33`（§154）—— **数量是 33，索引是 0..32** ✓

**用 `% 34` 会给出 33 这个越界值，约每 34 次重生一次。**

### 2.2 第二个：**随机数本身是错的**

```cpp
// AND THE RANDOMNESS ITSELF WAS WRONG, not just its range. sub_403C70's
// selector chooses which of 34 accessor VARIANTS to install, and each variant
// has its own key triple and its own permutation of the object's address
// bytes -- so ciphertext written by one is noise to another.
```

**"34 个访问器变体，每个有自己的密钥三元组和自己的地址字节置换 —— 所以一个写的密文对另一个是噪声。"**

### 2.3 但不同对象可以不同

```text
Two different objects may legitimately use different variants, which is why
legs and torso differ here; what must never vary is the variant used for ONE
object across its lifetime.
```

**"两个不同的对象可以合法地使用不同的变体 —— 这就是腿和躯干在这里不同的原因；但绝不能变的是【一个对象】在其生命期内使用的变体。"**

**这是本节最重要的一句**：**不变量是"同一对象跨时间稳定"，不是"所有对象相同"**。

### 2.4 所以固定值

```cpp
constexpr std::uint32_t selector = 0;
constexpr std::uint32_t TorsoSelectorOffset = 17;
static_assert(selector < SvNativeLerpFrameSelectorCount);
```

**腿用 0、躯干用 17** —— 两个常量。

**而躯干用 `(0 + 17) % 33 = 17`** ✓

### 2.5 为什么 `QueryPerformanceCounter` 不行

```text
Fixed values make that guarantee and make a failure reproducible,
which a QueryPerformanceCounter never can.
```

**"固定值做出那个保证，并让失败可复现 —— 而 `QueryPerformanceCounter` 永远做不到。"**

### 2.6 那次"间歇性失败无法归因"

```text
Picking modulo 34 handed it an out-of-range selector about one spawn in
thirty-four, and the torso call below rolled the same dice again, so the DObj
bring-up failed intermittently for a reason nothing in the log could point at.
```

**"躯干那次调用又掷了同样的骰子，所以 DObj 启动间歇性失败，而日志里没有任何东西能指向原因。"**

**两个独立的 1/34 概率叠加** —— 所以失败率约 `1-(33/34)² ≈ 5.8%`。

## 三、三次尝试的完整序列

```cpp
failureStage = "lerp_frame_legs_initialize";
if (!invokeNativeLerpFrameAccessorInitialize(..., characterInfo + Legs(0x17C), selector=0, ...))
{
    snprintf(details, 112, "lerp_frame_legs_initialize code=0x%08lX address=%p",
        exception.code, exception.address);
    failureStage = details;
    return false;
}

failureStage = "lerp_frame_torso_initialize";
if (!invokeNativeLerpFrameAccessorInitialize(..., characterInfo + Torso(0x1BC), selector=17, ...))
{
    snprintf(details, 112, "lerp_frame_torso_initialize code=0x%08lX address=%p", ...);
    failureStage = details;
    return false;
}

failureStage = "lerp_frame_accessor_validation";
if (!SV_AreNativeLerpFrameAccessorsValid(
        characterInfoBytes,
        (uint32)(uintptr_t)characterInfo,
        (uint32)(uintptr_t)module_,
        *nativeLerpFrameSetKey_,
        *nativeLerpFrameGetKey_))
    return false;
```

### 3.1 `failureStage` 被写成**动态字符串**

```cpp
failureStage = details;    // 含 code 与 address
```

**这是 `std::string&` 输出参数的价值** —— 它可以携带**运行时拼出的详情**，而不只是阶段名。

### 3.2 `details[112]` 的大小

```text
"lerp_frame_legs_initialize code=0x%08lX address=%p"
```

```text
"lerp_frame_legs_initialize "  25
"code=0x" + 8              15
" address=0x" + 8          19
= 59 + NUL                  60
```

**112 是宽裕的** ✓

### 3.3 验证函数的四个参数

```cpp
SV_AreNativeLerpFrameAccessorsValid(
    characterInfoBytes,                    // 缓冲
    (uint32)characterInfo,                 // 缓冲地址
    (uint32)module_,                       // 模块基址
    *nativeLerpFrameSetKey_,               // set key
    *nativeLerpFrameGetKey_)               // get key
```

**五个参数** —— 而 §154 里记过"这个守卫解码的是 ol-mod 自己写的东西，所以偏移错了它照样通过"。

**所以这一步只能验证"我们写的东西读得回来"，不能验证"引擎在同一位置读"**。

## 四、`SV_ProjectNativePlayerAnimationToCharacterInfo`

```cpp
failureStage = "animation_projection";
SvNativeEntityState nativeEntityStateImage;
std::memcpy(nativeEntityStateImage.bytes.data(), entity, SvNativeEntityState::Size);
if (!SV_ProjectNativePlayerAnimationToCharacterInfo(nativeEntityStateImage, characterInfoBytes))
    return false;
```

### 4.1 那条"只导入原生镜像"

```cpp
// CODDIFF(bg_update_player_dobj): gentity_s embeds entityState_s as
// its first 0x110 bytes, but SvNativeEntityState also carries ol-mod
// address-ownership metadata. Import only the native image here;
// animation projection reads opaque animation words and must not treat
// gentity_s +0x110 (isLinked) as that source-side metadata.
```

**`SvNativeEntityState` 有 `secureOriginAddressBound`（§176）** —— 而 `gentry_s +0x110` 是 `isLinked`。

**所以直接从原生内存 `memcpy` 会把 `isLinked` 当成"地址绑定标志"。**

**解法是先 `memcpy` 到干净的 `SvNativeEntityState`**（它的 `secureOriginAddressBound` 是默认 false）—— **只导入 0x118 字节的原生镜像**。

**注意 `SvNativeEntityState::Size = 0x118`** —— 而注释里写 `0x110`（3.3.3.3 的值）。

## 五、`irreversibleMutationStarted = true` 的位置

```cpp
NativeExceptionDetails updateException{};
irreversibleMutationStarted = true;
const auto updated = invokeBGUpdatePlayerDObj(
    bgUpdatePlayerDObj_, existingDObj, entity, characterInfo, &updateException);
```

### 5.1 为什么在**调用之前**

```text
CODREF(bg_update_player_dobj): CODOL 0x0040B700, BO1 0x0040F700
and Ghosts 0x140070070 are void-style native updates. Once entered,
DObj map, characterInfo and model ownership may already differ even
when the SEH adapter reports an exception.
```

**"一旦进入，DObj 映射、characterInfo 与模型所有权即使 SEH 适配器报告异常也可能已经不同。"**

**"void 风格的更新"** —— 没有返回值，没有失败协议。

**所以"可能已经改了"要在调用【前】就声明** —— 这是保守但正确的。

### 5.2 三步

```text
1. installServerAnimConditionStorage(previousContext)   ← 失败则 return false（此时未变异）
2. irreversibleMutationStarted = true                     ← 在此之前声明变异不可逆
3. invokeBGUpdatePlayerDObj(...)
4. animated = updated && invokeBGPlayerAnimation(...)
```

**第 4 步的 `updated &&`** —— 前一步失败就不调下一步。

## 六、那段"一条日志答完所有问题"的诊断

```cpp
// TODO(CODOL): the animation state itself, read straight out of
// characterInfo the instant BG_PlayerAnimation returns, while the
// condition storage is still installed. This answers, in one line,
// every question the pose measurements cannot:
```

### 6.1 四个问题

```text
1. XAnim 树是否曾经获得一个节点（word[tree+4] —— 每个遍历器都从它开始的根，
   由 0x0064BBC0 按需创建，只有在 BG_SetLerpFrameAnimation 【没有】在
   0x00409C2E 早退 时才能到达）
2. lerp 帧是否根本持有动画号与资产
3. fraction 是否仍然被钉在 VA 0x0040A4AE 写的 1.0
4. 时钟是否到达那个块
```

**"用一行回答姿态测量无法回答的每一个问题"**

### 6.2 `treeRoot` 的读法

```cpp
const auto treeRoot = reportedTree && readableSpan(reportedTree, 8)
    ? *(const uint16*)((const std::byte*)reportedTree + 4)
    : 0xFFFFu;
```

**`tree + 4` 是根节点** —— 与 §205/§206 里"树头 `{anims, children}`"一致。

**`0xFFFF` 是"读不出"的哨兵** —— 因为 `uint16` 的合法值域是 0..0xFFFE（节点索引）。

### 6.3 十二个字段的日志

```text
"server animation state entity=%lu treeRoot=%u
 wantLegs=%lu wantTorso=%lu
 legs{num=%lu asset=0x%08lX frac=%.3f t=%lu}
 torso{num=%lu asset=0x%08lX frac=%.3f t=%lu}
 clock=%lu"
```

**十三个值**：

```text
entity        ← 实体
treeRoot      ← 树根节点
wantLegs      ← u32(0x1F4)   —— characterInfo + 500
wantTorso     ← u32(0x1F8)   —— characterInfo + 504
legs.num      ← u32(Legs + 0x10)    = +0x18C
legs.asset    ← u32(Legs + 0x14)    = +0x190
legs.frac     ← f32(Legs + 0x34)    = +0x1B0
legs.t        ← u32(Legs + 0x38)    = +0x1B4
torso.num     ← u32(Torso + 0x10)   = +0x1CC
torso.asset   ← u32(Torso + 0x14)   = +0x1D0
torso.frac    ← f32(Torso + 0x34)   = +0x1F0
torso.t       ← u32(Torso + 0x38)   = +0x1F4
clock         ← storage + AnimSnapshotTimeOffset
```

### 6.4 六个 lerp 帧字段的偏移

```text
+0x10  动画号（`& 0x3FF` 掩码）
+0x14  anim-def 指针（其 +0x50 是标志字，+0x44 是时长）
+0x34  lerp 速率（钳到 0.1..4.0）
+0x38  与全局帧时间比较的时间戳
```

**与 §154 里 `sub_408A70` 的分析完全一致** —— 四个字段都在。

**而这里多读了 `+0x10` 与 `+0x14`** —— 那两个是"动画号与资产"。

### 6.5 `wantLegs` / `wantTorso` 在 `+0x1F4` / `+0x1F8`

**这两个偏移是 `characterInfo + 500` / `+504`** —— 而 §154 里 `sub_40A9D7` 用 `ecx=[edi+0x258]`（torso）与 `edi+0x25C`（legs）。

**`0x258 = 600`、`0x25C = 604`** —— **不是 500/504**。

**所以 `+0x1F4`/`+0x1F8` 是另外两个字段**（可能是 3.3.3.3 的偏移）。

**这是一处需要指出的不一致**：注释与 §154 的实测偏移不同。

## 七、去重键里混进三个时钟（本组最重要的一段）

### 7.1 第一次尝试

```text
THE DEDUPE KEY MUST NOT CONTAIN THE CLOCK. `clock=` is the anim
snapshot time and it advances every frame, so the comparison
below could never match and this line was written on EVERY
frame, for every animated entity, for the life of the match --
a state report that only means anything when the state CHANGES.

Measured 2026-08-24: with the server console on, the flood cost
~17ms of a ~72ms frame against a 50ms budget.
```

**"~72 ms 的帧里 17 ms 花在这个洪水上，而预算只有 50 ms。"**

### 7.2 修法：在 `" clock="` 处截断

```text
Compare the state without the clock; still print the clock,
because when the state does change the time it changed at is
the useful half.
```

**"比较时不带时钟；但仍然打印它，因为当状态真的变化时，变化发生的时刻是有用的那一半。"**

### 7.3 但截断不够——**有三个时钟**

```text
AND CUTTING AT " clock=" WAS NOT ENOUGH -- THERE ARE THREE CLOCKS,
NOT ONE. `legs{... t=%lu}` and `torso{... t=%lu}` are the lerp
frame times and they advance every frame exactly as clock= does,
and both sit INSIDE the prefix that cut kept. So the key still
changed every frame, the comparison still never matched, and the
flood this comment describes was still running:
measured 2026-08-25 with two players, 206 of 237 log lines
in a ten second window were this line, symmetric across both entities.
```

**三个时钟**：

```text
clock=   ← AnimSnapshotTimeOffset
legs.t   ← u32(Legs + 0x38)
torso.t  ← u32(Torso + 0x38)
```

**后两个在截断点的【前面】** —— 所以截断无效。

### 7.4 实测数字

```text
2026-08-24   一次洪水 ~17 ms / 72 ms 帧
2026-08-25   两个玩家，10 秒窗口内 237 行日志里 206 行是这一行
```

**"206/237 = 87%"** —— 而且**两个实体对称**。

### 7.5 最终解法：**从状态字段构建键**

```cpp
// Build the key from the state fields instead of slicing the
// formatted line, so a later field addition cannot silently
// reintroduce a clock into it.
```

**"从状态字段构建键，而不是切分格式化后的行，这样以后添加字段不能悄悄把时钟重新引入。"**

**这是一个关于"防御性设计"的精确论证**：

```text
切分行：依赖【格式】，加字段就会破坏
构建键：显式列出【哪些字段参与】，加字段不会自动进入
```

## 八、关键结论

1. **选择子范围是 0..32（33 个），`% 34` 会给出越界值**。
2. **不变式是"同一对象跨时间稳定"，不是"所有对象相同"** —— 腿 0、躯干 17 是合法的。
3. **两个独立的 1/34 概率叠加 ⇒ 约 5.8% 的间歇性失败，而日志无法指向原因**。
4. **`failureStage` 可以携带运行时详情**（异常码 + 地址），因为它是一个 `std::string&`。
5. **`irreversibleMutationStarted = true` 在调用【前】**，因为 void 风格更新没有失败协议。
6. **`+0x1F4`/`+0x1F8` 与 §154 的 `+0x258`/`+0x25C` 不一致** —— 需核对。
7. **"切分格式化行"作为去重键会随字段增加而失效** —— 必须从状态字段显式构建。

## 九、未闭合点

- `wantLegs`/`wantTorso` 的 `+0x1F4`/`+0x1F8` 与 §154 的 `+0x258`/`+0x25C` 存在差异。
- `SV_AreNativeLerpFrameAccessorsValid` 的自证式验证缺陷（§154 记过）仍未改。
- `EngineBindings.cpp` 5910 行之后未读取。
