# 332 · **`delta-yaw publish` 诊断** —— "分划被拉回"的缺失链、`zero times in a 640-row window`

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 3785–3990 行。

## 二、`delta-yaw publish` 诊断（本组最重要的一段）

### 2.1 那段完整因果

```php
// OLMOD(delta-yaw-quantifier 2026-10-09): ONE LINE PER CHANGE,
// never per frame. Measured 2026-10-09: this branch fires only
// when the native pmove rewrote delta_angles.yaw (take-off /
// landing), which in a 640-row window happened zero times --
// so the cost is a comparison, and the payoff is the exact
// millisecond and magnitude of every server-side yaw rewrite
// the client is about to receive. That is the missing link in
// "the reticle is pulled back": the read-back feeds this value
// (sv_native_playerstate_mp.cpp:1208) and this writer puts it
// on the wire (sv_snapshot_mp.cpp:3837/3847).
```

### 2.2 八层

```text
1. **每次变化一行，绝不每帧**
2. ⇒ 实测 2026-10-09：**这个分支只在 native pmove 重写 `delta_angles.yaw` 时触发**（起飞/落地）
3. ⇒ **而在一个 640 行的窗口里它发生了【零次】**
4. ⇒ 所以**成本是一个比较**
5. ⇒ 而**收益是每一个客户端即将收到的服务端 yaw 重写的精确毫秒与幅度**
6. ⇒ **那正是"分划被拉回"里的缺失环节**
7. ⇒ **回读喂这个值（`sv_native_playerstate_mp.cpp:1208`）**
8. ⇒ **而这个写入器把它放上线（`sv_snapshot_mp.cpp:3837/3847`）**
```

### 2.3 **两个具体行号**

```text
sv_native_playerstate_mp.cpp:1208    回读
sv_snapshot_mp.cpp:3837/3847         写入
```

**✅ 而本段在 3943/3944 —— **与注释里的行号不符**。**

**⚠ 注释说 3837/3847 而实际是 3943/3944。**

**⇒ 一处**行号漂移**（因为文件增长了）。**

**✅ 与 §235 的"注释里的偏移已过时"同族**（第五次）。

### 2.4 而"**在一个 640 行窗口里它发生了零次**"

**⇒ 三层**：

```text
1. 640 行的日志窗口
2. ⇒ delta_angles.yaw 重写**零次**
3. ⇒ 所以这个分支**几乎从不触发**
```

**⚠ 而"分划被拉回"的问题是**存在的**。**

**⇒ 所以 `delta_angles.yaw` 可能**不是**那个问题的原因。**

**⚠ 或者说，注释认为它是但实测从未触发 ⇒ **矛盾**。**

**⇒ 一个**未闭合的判断**。**

### 2.5 而实现的**五项**

```php
static std::array<float, MaximumGameClients> lastPublishedYaw{};
static std::array<uint32, MaximumGameClients> lastPublishedAt{};
const auto publishSlot = (size_t)state.clientNum;
if (publishSlot < lastPublishedYaw.size())
{
    write("delta-yaw publish client=" + publishSlot +
        " from=" + lastPublishedYaw[publishSlot] +
        " to=" + state.deltaAngles[1] +
        " dtMs=" + (state.commandTime - lastPublishedAt[publishSlot]) +
        " t=" + state.commandTime);
    lastPublishedYaw[publishSlot] = state.deltaAngles[1];
    lastPublishedAt[publishSlot] = state.commandTime;
}
```

### 2.6 五个字段

```text
client
from       （上次）
to         （本次）
dtMs       （与上次的 commandTime 差）
t          （本次 commandTime）
```

**✅ 一个**完整的发布记录**。**

**⇒ 而 `dtMs` 用 `commandTime` 差 ⇒ 所以是**命令时间**而不是墙钟。**

## 三、`writeDeltaAngleFull(message, state.deltaAngles[1])`

**⇒ 三层**：

```text
1. 用 `writeDeltaAngleFull`（§323 的"两个 0 位 + 16 位角度"）
2. ⇒ 所以 **delta-yaw 是 16 位角度**
3. ⇒ 而**没有基线**（`writeDeltaAngleFull` 只接受一个 angle）
```

**✅ 与 §323 的 `writeDeltaAngleFull` 签名一致。**

## 四、`viewAngleChanged[2]`（roll）的写入

```php
if (viewAngleChanged[2])
{
    writePlayerStateFieldIndex(message, 29, lastFieldIndex);
    writeAngle16(message, state.viewAngles[2]);
}
```

**⇒ 三层**：

```text
1. 字段 29
2. ⇒ 用 `writeAngle16`
3. ⇒ 所以 roll 是 16 位角度
```

**⚠ 而 §331 说 yaw(18) 与 pitch(19) 也用 `writeAngle16`。**

**⇒ 所以三个视角分量**都用 16 位角度**。**

## 五、`eFlagsChanged` 用 `write30BitFlagDelta`

```php
if (eFlagsChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateEFlagsField, lastFieldIndex);
    write30BitFlagDelta(message, state.eFlags, baselineEFlags);
}
```

**⇒ 三层**：

```text
1. `eFlags` 用 `write30BitFlagDelta`
2. ⇒ 所以**单一位变化时 6 位，否则 31 位**
3. ⇒ 与 §323 的"6 位 vs 31 位"一致
```

**✅ 与 §148 的"`0x80000`/`0xA0000`/`0x20000` corpse flags"配合 —— 那些是**单一位**。**

**⇒ 所以单一位变化的优化对尸体旗标**特别有效**。**

## 六、`viewHeightTarget` 用 `writeSignedDelta(..., 8)`

```php
if (viewHeightTargetChanged)
{
    writePlayerStateFieldIndex(message, 38, lastFieldIndex);
    writeSignedDelta(message, state.viewHeightTarget, baselineViewHeightTarget, 8);
}
```

**⇒ 三层**：

```text
1. 字段 38
2. ⇒ `writeSignedDelta`（**有符号**）
3. ⇒ 8 位
```

**✅ 与本文件反复的"高度函数"配合 —— 而 8 位能表示 -128..127。**

**⇒ 与记忆里"seven adjacent height functions (15/70/50/30/60/40/11)"配合 —— 那些都在 8 位范围内。**

## 七、`viewHeightCurrent` 用 `writeRawFloatDelta`

```php
if (viewHeightCurrentChanged)
{
    writePlayerStateFieldIndex(message, 34, lastFieldIndex);
    writeRawFloatDelta(message, state.viewHeightCurrent, baselineViewHeightCurrent);
}
```

**⇒ 三层**：

```text
1. 字段 34
2. ⇒ `writeRawFloatDelta`（**【有基线】**）
3. ⇒ 所以是 **XOR 增量**
```

**⚠ 而 `viewHeightTarget`（38）用 `writeSignedDelta`（8 位整数）而 `viewHeightCurrent`（34）用**浮点 XOR**。**

**⇒ 两个高度一个浮点一个整数。**

**✅ 与记忆里"`viewHeightCurrent` 是 float 而 `viewHeightTarget` 是 int32"配合。**

## 八、`currentWeaponAssetIndex` 的 **11 位**

```php
if (currentWeaponChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateCurrentWeaponField, lastFieldIndex);
    writeUnsignedDelta(message, state.currentWeaponAssetIndex, baselineCurrentWeaponAssetIndex, 11);
}
```

**✅ 与 §317 的"`MaxCurrentWeaponAssetIndex = 0x7FF`（11 位）"**完全一致** ✓**

## 九、`otherFlagsChanged` 的 **CODEC 改变**（本组第二重要）

```php
if (otherFlagsChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateOtherFlagsField, lastFieldIndex);
    // CODDIFF(1649370): this field CHANGED CODEC, not just width.
```

**（后续待读）**

### 9.1 而"**这个字段改变了 CODEC，不只是宽度**"

**⇒ 三层**：

```text
1. 大部分差异是**宽度**（10→11 位等）
2. ⇒ 而 `otherFlags` **改变了 codec**
3. ⇒ **所以不只是位数而是编码方式**
```

**✅ 一个**更严重的变化**。**

**⇒ 待读具体是哪个 codec 变成哪个。**

## 十、`pmTime` 用 `writeSignedDelta(..., 16)`

```php
if (pmTimeChanged)
{
    writePlayerStateFieldIndex(message, PlayerStatePmTimeField, lastFieldIndex);
    writeSignedDelta(message, (int32)state.pmTime, (int32)baselinePmTime, 16);
}
```

**⇒ 三层**：

```text
1. `pmTime` 是 `uint32` 而**强转 `int32`**
2. ⇒ 用 `writeSignedDelta`
3. ⇒ 16 位
```

**⚠ 一个 `uint32` 强转成 `int32` 再当 16 位有符号 ⇒ **高 16 位丢失**。**

**⇒ 但 `pmTime` 大概是**相对时间** ⇒ 16 位够。**

## 十一、`weaponPositionFraction` 用 `writeRawFloatDelta`

```php
if (weaponPositionFractionChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateWeaponPositionFractionField, lastFieldIndex);
    writeRawFloatDelta(message, state.weaponPositionFraction, baselineWeaponPositionFraction);
}
```

**⇒ 三层**：

```text
1. 字段 41
2. ⇒ `writeRawFloatDelta`（**有基线**）
3. ⇒ 所以是 **XOR 增量**
```

**✅ 与 §329 的"`sendUnk04A4Time = weaponPositionFraction != 0`"配合。**

**⇒ 所以 `weaponPositionFraction` 既是**字段 41 的值**又是**字段 4 的触发条件**。**

## 十二、`damageTimer` 的 **10 位**

```php
if (damageTimerChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateDamageTimerField, lastFieldIndex);
    writeUnsignedDelta(message, state.damageTimer, baselineDamageTimer, 10);
}
```

**✅ 与 §317 的七字段表里 `42 +0x0F0 10 damageTimer`**完全一致** ✓**

## 十三、`sprintStartMaxLength` 的 **16 位**

```php
if (sprintStartMaxLengthChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateSprintStartMaxLengthField, lastFieldIndex);
    writeUnsignedDelta(message, state.sprintStartMaxLength, baselineSprintStartMaxLength, 16);
}
```

**⇒ 三层**：

```text
1. 字段 43
2. ⇒ 16 位无符号
3. ⇒ 与 §317 的 `PlayerStateSprintStartMaxLengthField = 43` 一致
```

## 十四、`weaponDelay[0]` 用 `writeSignedDelta(..., 16)`

```php
if (weaponDelayChanged[0])
{
    writePlayerStateFieldIndex(message, PlayerStateRightWeaponDelayField, lastFieldIndex);
    writeSignedDelta(message, state.weaponDelay[0], baselineWeaponDelay[0], 16);
}
```

**⇒ 三层**：

```text
1. 字段 44
2. ⇒ `writeSignedDelta`（**有符号**）
3. ⇒ 16 位
```

**✅ 与 §317 的 `PlayerStateRightWeaponDelayField = 44` 一致。**

## 十五、`groundEntityNum` 的 **11 位**

```php
if (groundEntityChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateGroundEntityField, lastFieldIndex);
    writeUnsignedDelta(message, state.groundEntityNum, baselineGroundEntityNum, 11);
}
```

**✅ 与 §318 的"`EntityStateGroundEntityField = 16` 的 `+0x088`"配合 —— 但那是 entityState 而这是 playerState。**

**⇒ 两个不同的 `groundEntity` 字段。**

## 十六、`offhandWeaponAssetIndex` 的 **11 位**

```php
if (offhandWeaponChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateOffhandWeaponField, lastFieldIndex);
    writeUnsignedDelta(message, state.offhandWeaponAssetIndex, baselineOffhandWeaponAssetIndex, 11);
}
```

**✅ 与 §317 的 `PlayerStateOffhandWeaponField = 53` 一致。**

## 十七、关键结论

1. **⭐ `delta-yaw publish` 诊断** —— "分划被拉回"的缺失环节（`sv_native_playerstate_mp.cpp:1208` → `sv_snapshot_mp.cpp:3837/3847`）。
2. **"在一个 640 行窗口里发生了零次"** —— 所以这个分支**几乎从不触发**。
3. **⚠ 注释里的行号 3837/3847 与实际 3943/3944 不符** —— 行号漂移。
4. **五个字段的发布记录**（client / from / to / dtMs / t）。
5. **三个视角分量（yaw 18 / pitch 19 / roll 29）都用 `writeAngle16`。**
6. **`eFlags` 用 `write30BitFlagDelta`**（6 位或 31 位）。
7. **`viewHeightTarget`(38) 是 8 位有符号整数而 `viewHeightCurrent`(34) 是浮点 XOR** —— 两个高度两种类型。
8. **`currentWeaponAssetIndex` 11 位。**
9. **`otherFlags` "改变了 CODEC，不只是宽度"** —— 一个更严重的变化（待读）。
10. **`pmTime` 的 `uint32 → int32 → 16 位`** 强转。
11. **`weaponPositionFraction`(41) 用 XOR 而它也是字段 4 的触发条件。**
12. **`damageTimer` 10 位**，与 §317 的七字段表一致。
13. **`sprintStartMaxLength` 16 位、`weaponDelay` 16 位有符号。**
14. **`groundEntityNum` 11 位。**

## 十八、未闭合点

- `otherFlags` 的 codec 变化具体是什么。
- `delta_angles.yaw` 是否真是"分划被拉回"的原因（零次触发与问题存在矛盾）。
- 注释行号漂移的其他位置。
- `sv_snapshot_mp.cpp` 3990 行之后未读取（1.47 MB，进度 27%）。
