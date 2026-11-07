# 326 · **`+7.00649e-044`** —— "把一个浮点当整数写"的屏幕后果、三个时间字段共用 `-97`、`flags` 从 18 到 25 位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 2594–2795 行。

## 二、**`+7.00649e-044`**（本组最重要的一段）

### 2.1 那段三层

```php
// with sprintf("%g", *(float *)&value), so writing the
// integer 50 put `+7.00649e-044` on screen -- which is
// precisely 50 reinterpreted as a float, and was even
// computed while arguing for the change.
//
// The decoder's `50` is a DELTA against its baseline,
// not an absolute value; the two demos were not being
// compared like for like. The popup rendered `+50`
// correctly before and does again.
//
// A player watching the screen settled this in one
// frame, and no amount of re-reading the decode would
// have: the number on screen IS the oracle for a thing
// a person is supposed to see.
writeFullFloatDelta(message, hudValue(elem), hudValue(old));
```

### 2.2 七层

```text
1. **写整数 50 在屏幕上打出 `+7.00649e-044`**
2. ⇒ **那正是 50 被重新解释成一个浮点数**
3. ⇒ **而它甚至在为那个改变辩护时就已经被计算出来了**
4. ⇒ **解码器的 `50` 是相对它基线的【增量】，不是一个绝对值**
5. ⇒ **两个 demo 没有被【像对像】地比较**
6. ⇒ 那个弹窗**之前正确地渲染 `+50` 而现在又是**
7. ⇒ **一个看着屏幕的玩家在一帧内解决了它，而再多的重读解码都不会** ——
8. ⇒ **屏幕上的数字就是一个本该由人看见的东西的【预言机】**
```

### 2.3 **`50` 的 IEEE 754 位模式**

**⇒ `50` 作为一个整数（`0x00000032`）被当成 float 解：**

```text
0x00000032 = 位模式
符号 0
指数 0（非规格化）
尾数 50
⇒ 50 × 2^-149 ≈ 7.00649e-44
```

**✅ 完全正确的 IEEE 754 非规格化数计算。**

**⇒ `2^-149 ≈ 1.401298e-45`，而 `50 × 1.401298e-45 = 7.00649e-44` ✓**

### 2.4 而**"它甚至在为那个改变辩护时就已经被计算出来了"**

**✅ 一句**极强的自我批评**。**

**⇒ 与 §341（§277）的"我瞄的正是那堵墙"同族（第二十四次）。**

### 2.5 而"**解码器的 `50` 是相对它基线的增量**"

**⇒ 三层**：

```text
1. 零售的 `50` 是**增量**
2. ⇒ 而我们的 `1112014848` 是**绝对值**（float 50.0 的位）
3. ⇒ **所以两个 demo 没有被像对像地比较**
```

**✅ 一个**极隐蔽的比较错误**。**

### 2.6 而"**屏幕上的数字就是预言机**"

**✅ 与 §271 的"用自己的解码器作预言机"**同族但**不同层**：**

```text
§271  codol_snapshot.py 是客户端读取器的转写 ⇒ 作 oracle
§326  屏幕上的数字是人类可见的结果 ⇒ 作 oracle
```

**⇒ 两个不同层次的 oracle。**

## 三、**三个时间字段共用 `-97`**（本组第二重要）

### 3.1 `HudElemFadeStartField`

```php
// CODREF: descriptors 10 and 17 carry codec -97, whose reader at
// 0x00C420C0 is "one bit; if clear an 8-bit count BACK from
// serverTime, else a full long". That is byte for byte the
// command-time codec already here.
writeCommandTime(message, fadeStart(elem), serverTime);
```

**⇒ 四层**：

```text
1. **描述符 10 与 17 携带 codec `-97`**
2. ⇒ 其读取器在 **`0x00C420C0`** 是"一位；若清零则一个从 `serverTime` **往回**的 8 位计数，否则一个完整 long"
3. ⇒ **那与这里已有的 command-time codec 逐字节相同**
4. ⇒ 所以复用 `writeCommandTime`
```

**✅ 与 §323 的 `writeCommandTime` 的"9 位 vs 33 位"**完全一致** ✓**

### 3.2 而三个字段用同一个 codec

```text
HudElemFadeStartField        writeCommandTime(...)
HudElemScaleStartField       writeCommandTime(...)
HudElemFxBirthTimeField      writeCommandTime(...)
```

**⇒ 三个。**

**✅ 与那段注释"descriptors 10 and 17 carry codec -97"**部分对应（10 与 17 是 fadeStart 与 scaleStart）。**

**⇒ 而 fxBirth（28）也用它 —— 所以**三个描述符共用一个 codec**。**

### 3.3 而"**同一个 -97 时间 codec 作为 `fadeStartTime` 与 `scaleStartTime`**"

```php
// Same -97 time codec as fadeStartTime and
// scaleStartTime: compact backwards delta when the
// birth is close to this snapshot, otherwise full time.
writeCommandTime(message, fxBirth(elem), serverTime);
```

**⇒ 三层**：

```text
1. **同一个 `-97` 时间 codec**
2. ⇒ **当出生接近这个快照时紧凑的【往回】增量**
3. ⇒ **否则完整时间**
```

**✅ 一个**正确的复用**。**

## 四、`HudElemFlagsField` 从 **18 到 25 位**（本组第三重要）

```php
case HudElemFlagsField:
    // CODDIFF(1649370): 18 -> 25 bits.
    writeUnsignedDelta(message, elem.flags, old.flags, 25);
    break;
```

**⇒ 三层**：

```text
1. **3.3.3.3 是 18 位**
2. ⇒ **本 build 是 25 位**
3. ⇒ **七位的差异**
```

**✅ 而 §316 说"`HudElem` 的第 14 行是 `flags {0xA4, 18}`"** —— 那是 **3.3.3.3 的值**。**

**⚠ 所以 §316 的表也是 3.3.3.3 的。**

**⇒ 而这里是**本 build 的 25 位**。**

**✅ 第五次"一位/几位的差异"。**

## 五、`HudElemFxDecayStartTimeField` 的**无变化前缀**

```php
case HudElemFxDecayStartTimeField:
    // Codec -65 has no change prefix: ten raw bits in
    // hundred-millisecond units.
    message.MSG_WriteBits(
        fxDecayStart(elem) / HudElemFxDecayQuantumMilliseconds,
        HudElemFxDecayBits);
    break;
```

### 5.1 四层

```text
1. **codec `-65` 没有变化前缀**
2. ⇒ **十位原始位**
3. ⇒ **以百毫秒为单位**
4. ⇒ 所以 `fxDecayStart / 100` 写 10 位
```

**✅ 与 §324 的 `writeHudFontScale` 的"`-86` 无变化前缀"同族**（第二次"无变化前缀的 codec"）。**

### 5.2 而 `-65` 是**第九个负 codec**

```text
-7, -8, -57, -58, -65, -75, -86, -94, -97, -100    （十个）
```

**✅ 十个负 codec。**

### 5.3 而 `HudElemFxDecayQuantumMilliseconds = 100`

**⇒ 与 §317 的 `HudElemFxDecayQuantumMilliseconds = 100`**一致** ✓**

**⇒ 而 `HudElemFxDecayBits = 10`**

**⇒ 所以 10 位 / 100ms ⇒ 最大 102.3 秒。**

## 六、`HudElemAlignScreenBits = 8` 与 `AlignOrgBits = 4`

```php
case HudElemAlignScreenField: writeUnsignedDelta(..., HudElemAlignScreenBits); break;
case HudElemAlignOrgField:    writeUnsignedDelta(..., HudElemAlignOrgBits); break;
```

**⇒ 8 位与 4 位。**

**✅ 与 §316 的"第 11 行是 `{0x2C, 8}` 而第 15 行是 `{0x28, 4}`"**完全一致** ✓**

**⇒ 而 `0x2C` 与 `0x28` 是两个不同的偏移。**

**✅ 所以 `alignScreen` 在 `+0x2C` 而 `alignOrg` 在 `+0x28` —— 顺序**与索引相反**。**

**⚠ 第五次"索引顺序不是偏移顺序"。**

## 七、`HudElemLabelBits = 11` 用在**两处**

```php
case HudElemTextField:  writeUnsignedDelta(..., HudElemLabelBits); break;
case HudElemLabelField: writeUnsignedDelta(..., HudElemLabelBits); break;
```

**⇒ 字段 22（`text`）与字段 33（`label`）**都用 11 位**。**

**✅ 与 §317 的"`HudElemLabelBits = 11` 而非 10"**完全一致** ✓**

**⇒ 所以那个 11 位同时适用于 `text` 与 `label`。**

## 八、`HudElemSortField` 的 **`writeFullFloatDelta`**

```php
case HudElemSortField:
    writeFullFloatDelta(message, elem.sort, old.sort);
    break;
```

**⚠ `sort` 是一个**浮点**？**

**⇒ 而 §316 的 `HudElemSortField = 21` 没有说类型。**

**⇒ 所以 `sort` 是 **float** 而名字看起来像整数。**

**✅ 与 §325 的 `value` 是 float 的教训同族。**

## 九、`case 23/24/25/26` 与 `case 34/41` 的**字面量**

```php
case 23: writeCommandTime(message, sizeStart(elem), serverTime); break;
case 24: writeUnsignedDelta(message, sizeTime(elem), sizeTime(old), 16); break;
case 25: writeUnsignedDelta(message, fromWidth(elem), fromWidth(old), 10); break;
case 34: writeCommandTime(message, elem.isClock()?elem.scaleStartTime:0u, serverTime); break;
case 41: writeUnsignedDelta(message, elem.isClock()?elem.scaleTime:0u, old.isClock()?old.scaleTime:0u, 32); break;
case 26: writeUnsignedDelta(message, fromHeight(elem), fromHeight(old), 10); break;
```

### 9.1 而 **`case 23..26` 与 `case 34/41` 用字面量**

**⚠ 而其它都用 `HudElemXxxField` 常量。**

**⇒ 所以**六个 case 用字面量**而其余用具名常量。**

**⚠ 一处不一致**（与 §316 的"`HudElem` 只到字段 33"配合 —— 34..41 与 23..26 可能是后加的）。**

### 9.2 而 **`case 41` 用 32 位**

```cpp
case 41: writeUnsignedDelta(..., 32); break;
```

**⇒ 而 `writePackedBits(32)` ⇒ `MSG_WriteLong`。**

**✓ 所以是**满宽 32 位**。**

### 9.3 而 `case 26` 在 `case 41` 之后

**⚠ 顺序 23, 24, 25, 34, 41, 26 —— **不是升序**。**

**⇒ 而 `switch` 里的 case 顺序与**逻辑无关**，所以只是**可读性问题**。**

**✓ 无功能影响。**

### 9.4 而 `34` 与 `41` 是**时钟的 `scaleStartTime` / `scaleTime`**

```text
34  ⇒ isClock ? scaleStartTime : 0    （-97 时间）
41  ⇒ isClock ? scaleTime : 0         （32 位）
```

**⇒ 三层**：

```text
1. 一个时钟 HUD 元素用**两个额外的字段**装它的时间
2. ⇒ 34 用 `-97` codec（`writeCommandTime`）
3. ⇒ 41 用 32 位
```

**✅ 一个**时钟专用的字段对**。**

## 十、`writePlayerState` 的**十二项参数**（本组第四重要）

```cpp
void writePlayerState(MsgWriter &message,
    const SvPlayerState &state,
    const SvPlayerState *baseline,
    const SvHoldBreathState *holdBreathState,
    const SvHoldBreathState *baselineHoldBreathState,
    const uint32 serverTime,
    const std::array<float, 3> &mapCenter,
    const SvClientPrediction *const clientPrediction = nullptr,
    PlayerStatePredictedModeReport *const modeReport = nullptr,
    const SvDamageNumberRing *numbers = nullptr,
    const SvDamageNumberRing *baselineNumbers = nullptr,
    const SvZombieInjuryRing *injuries = nullptr,
    const SvZombieInjuryRing *baselineInjuries = nullptr)
```

### 10.1 十三项

```text
state / baseline
holdBreathState / baselineHoldBreathState
serverTime / mapCenter
clientPrediction
modeReport（输出）
numbers / baselineNumbers
injuries / baselineInjuries
```

### 10.2 而 **六个可选（默认 `nullptr`）**

```text
clientPrediction
modeReport
numbers / baselineNumbers
injuries / baselineInjuries
```

**⇒ 六个。**

### 10.3 而 `mapCenter` 是**必需**（无默认）

**⇒ 所以 `writePlayerState` 总是相对于地图中心。**

**✅ 与 §325 的 `writeEntityOrigin(..., mapCenter[..])` 配合。**

## 十一、**"没有 `baselineOrigin` / `baselineVelocity`"**

```cpp
const std::array<float, 3> zeroOrigin{};
// NO baselineOrigin / baselineVelocity: origin and velocity are
// changeHint==3, so the baseline never enters their decision.
```

### 11.1 三层

```text
1. **没有 `baselineOrigin` / `baselineVelocity`**
2. ⇒ 因为 **origin 与 velocity 是 `changeHint == 3`**
3. ⇒ **所以基线从不进入它们的决策**
```

**✅ 与 §319 的"`changeHint`"（`{u32 offset, s32 bits, u32 changeHint}`）配合。**

**⇒ 所以 `changeHint == 3` 意味着"总是发绝对值"。**

**✅ 与记忆里"11 个字段我们写 XOR 增量，三份参照全写裸值"**相关**——**

**⇒ 而这里 `origin`/`velocity` 是**裸值**（不 XOR）。**

### 11.2 而 **19 个 `baseline*` 局部**

```text
baselineDeltaAngles / baselineViewAngles
baselineCommandTime / baselinePmType / baselinePmTime / baselinePmFlags
baselineEFlags
baselineHoldBreathSwayScale / baselineHoldBreathTimer
baselineOtherFlags / baselineGravity / baselineSpeed
baselineMoveSpeedScaleMultiplier / baselineClientNum
```

**⇒ 十四个。**

**⇒ 所以 `writePlayerState` 的**大量字段有基线**。**

## 十二、关键结论

1. **⭐ `+7.00649e-044`** —— 整数 50 被当 float 解，而 **`50 × 2^-149`** 精确闭合。
2. **"它甚至在为那个改变辩护时就已经被计算出来了"** —— 一句极强的自我批评。
3. **"解码器的 `50` 是相对基线的**增量**"** ⇒ 两个 demo 没被像对像地比较。
4. **"屏幕上的数字是一个本该由人看见的东西的预言机"** —— 与 §271 的"解码器作 oracle"不同层。
5. **三个时间字段共用 `-97` codec**（`0x00C420C0`），复用 `writeCommandTime`。
6. **`HudElemFlagsField` 从 18 到 25 位** —— 七位差异，而 §316 的表也是 3.3.3.3 的。
7. **`-65` codec 无变化前缀** —— 十位以百毫秒为单位。
8. **十个负 codec**（`-7/-8/-57/-58/-65/-75/-86/-94/-97/-100`）。
9. **`alignScreen`(8) 在 `+0x2C` 而 `alignOrg`(4) 在 `+0x28`** —— 索引与偏移顺序相反。
10. **`HudElemLabelBits = 11` 同时用于 `text`(22) 与 `label`(33)**。
11. **`sort` 是一个浮点** —— 名字像整数。
12. **六个 case 用字面量**（23/24/25/26/34/41）而其余具名。
13. **`case 41` 用 32 位满宽**。
14. **时钟用两个额外字段**（34 的 `-97` 与 41 的 32 位）。
15. **`writePlayerState` 十三项参数，六个可选**。
16. **`mapCenter` 必需** ⇒ 总是相对于地图中心。
17. **"origin 与 velocity 是 `changeHint == 3` ⇒ 基线从不进入决策"** ⇒ 它们**发裸值**。

## 十三、未闭合点

- `writeEntityOrigin` 的完整实现（仍是一个前向声明）。
- `sort` 为何是浮点。
- 35..40 六项保留。
- `sv_snapshot_mp.cpp` 2795 行之后未读取（1.47 MB，进度 19%）。
