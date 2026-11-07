# 334 · **`compassRadar` 放进第二 pass 导致快照停止解码**、八项 `PlayerStateSecondPassFields`、五个 hint-1 的 `lastChangedFieldIndex ==` 门

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 4189–4390 行。

## 二、**`compassRadar` 放进第二 pass 的错误**（本组最重要的一段）

### 2.1 那段八层

```php
// FIELD 86 GOES HERE AND NOWHERE ELSE. The playerState field index is
// GAP-ENCODED (writePlayerStateFieldIndex writes fieldIndex minus the
// last one), so every write in this pass has to be in strictly
// ascending index order: 83 above, 87 below.
//
// THE FIRST ATTEMPT PUT IT IN THE SECOND-PASS LOOP and the snapshot
// stopped decoding. PlayerStateSecondPassFields is {82, 89, 93, 98,
// 101, 104, 106, 122} -- the type-2 fields -- and 86 is type 0. The
// field was therefore never emitted while includeChangedField had
// already raised lastChangedFieldIndex to 87, so the client hunted
// for a field that was not on the wire and ran off the end of the
// buffer. Tools/demo-re decoded the old bytes with residual 0 and the
// new ones not at all, which is how it was caught.
```

### 2.2 九层

```text
1. **字段 86 在这里而不在别处**
2. ⇒ playerState 字段索引是**间隔编码的**（写 `fieldIndex` 减上一个）
3. ⇒ **所以这个 pass 里每一个写都必须严格递增：83 在上，87 在下**
4. **第一次尝试把它放进第二 pass 的循环而快照停止解码**
5. ⇒ `PlayerStateSecondPassFields` 是 **`{82, 89, 93, 98, 101, 104, 106, 122}`** —— **`type-2` 字段**
6. ⇒ **而 86 是 `type 0`**
7. ⇒ **所以这个字段从未被发出，而 `includeChangedField` 已经把 `lastChangedFieldIndex` 抬到 87**
8. ⇒ **所以客户端搜寻一个不在线上的字段并跑出缓冲区末尾**
9. ⇒ **`Tools/demo-re` 用残差 0 解码旧的字节而新的完全解不出来，这就是它被抓到的方式**
```

### 2.3 **"客户端搜寻一个不在线上的字段"**

**✅ 三层**：

```text
1. `lastChangedFieldIndex` = 87 ⇒ 客户端期待到 87
2. ⇒ 而 86 从未发出
3. ⇒ **客户端搜寻"变化到 86"而永远找不到 ⇒ 跑出缓冲区**
```

**✅ 与 §318 的"`4.29e9` 的下溢 ⇒ 发出 7 个位块直到溢出"、§319 的"乱序字段失步整个快照"同族**（第三十次）。

### 2.4 而"**用残差 0 解码旧的而新的完全解不出来**"

**✅ 三层**：

```text
1. `Tools/demo-re` 对旧字节：**残差 0**（完全解码）
2. ⇒ 对新字节：**完全解不出来**
3. ⇒ **这就是它被抓到的方式**
```

**✅ 与 §271 的"用自己的解码器作预言机"同族**（第二次）。**

**⇒ 而"残差 0"是一个**精确的量**（解码后剩余的位数为 0 ⇒ 完美对齐）。**

### 2.5 而八个 `PlayerStateSecondPassFields`

```cpp
constexpr std::array PlayerStateSecondPassFields{
    82u, 89u, 93u, 98u, 101u, 104u, 106u, 122u,
};
```

**⇒ 八个：`82`、`89`、`93`、`98`、`101`、`104`、`106`、`122`。**

**✅ 与 §330 的"`PlayerStateSecondPassFields` = `{82, 89, 93, 98, 101, 104, 106, 122}`（`type-2` 字段）"完全一致。**

### 2.6 而**八个 `type-2` 字段的对照**

```text
82    RadarFlags
89    ViewHeightLerpDown
93    SprintDelay
98    CursorHintDualWield
101   SprintButtonUpRequired
104   ShellshockDuration
106   DualWieldActive
122   PerkHudVisible
```

**✅ 而 §330 说"字段 122 是一个 `type 2` 字段"。**

**✅ 八个全部对上。**

## 三、**五个 hint-1 的 `lastChangedFieldIndex ==` 门**（本组第二重要）

### 3.1 五个

```cpp
if (radarFlagsChanged && lastChangedFieldIndex == PlayerStateRadarFlagsField)        // 82
if (viewHeightLerpDownChanged && lastChangedFieldIndex == PlayerStateViewHeightLerpDownField)  // 89
if (sprintDelayChanged && lastChangedFieldIndex == PlayerStateSprintDelayField)      // 93
if (dualWieldActiveChanged && lastChangedFieldIndex == PlayerStateCursorHintDualWieldField)  // 98
if (sprintButtonUpRequiredChanged && lastChangedFieldIndex == PlayerStateSprintButtonUpRequiredField)  // 101
if (shellshockDurationChanged && lastChangedFieldIndex == PlayerStateShellshockDurationField)  // 104
if (dualWieldActiveChanged && lastChangedFieldIndex == PlayerStateDualWieldActiveField)  // 106
```

**⇒ 七个（含 106 那第二个 `dualWieldActive`）。**

### 3.2 而那段注释

```php
// A hint-2 field that is itself last terminates the indexed pass;
// otherwise it is written without an index in the second pass.
```

**⇒ 三层**：

```text
1. **一个 hint-2 字段如果它自己是【最后一个】⇒ 它【终止索引 pass】**
2. ⇒ 所以它**在主循环里被写**
3. ⇒ 否则它**在第二 pass 里不带索引被写**
```

### 3.3 而**两种路径**

```text
① 它是最后一个变化字段 ⇒ 在主循环写（带索引）
② 否则 ⇒ 在第二 pass 写（不带索引）
```

**✅ 所以 `lastChangedFieldIndex == X` 是"它是最后一个"的判据。**

**⚠ 而这意味着**每个 hint-2 字段有两个写入点**。**

**⇒ 所以代码里**两处写同一个字段**。**

### 3.4 而 `122`（`PerkHudVisible`）的注释

```php
// 122/123/124/125 sit between RightWeaponHandFlags (121) and
// LeftWeaponShotCount (140). Field 122 is a type-2 field, but it still
// contributes its REAL index to the native last-changed scan. When it
// is the highest changed field native writes it in the indexed pass;
// otherwise it is emitted positionally in the second pass below.
```

**✅ 与 §330 的原文一致。**

## 四、`compassRadar` 用 **codec 1**

```php
// Codec 1 -- a positive width, so the generic arm: a present bit
// then one bit xor'd against the baseline.
writeUnsignedDelta(message, state.compassRadarEnabled, baselineCompassRadar, 1);
```

**⇒ 三层**：

```text
1. **codec `1`** —— 一个正的宽度
2. ⇒ 所以走**通用分支**：一个存在位 + 一位
3. ⇒ 而**那一位 XOR 基线**
```

**✅ 与 §323 的 `writeUnsignedDelta` 的"XOR + 打包"一致。**

## 五、**五个 1 位字段**

```text
86    compassRadarEnabled     codec 1
89    viewHeightLerpDown      1 位
93    sprintDelay             1 位     ← 【？sprintDelay 是 1 位】
98    cursorHintDualWield     1 位
101   sprintButtonUpRequired  1 位
106   dualWieldActive         1 位
```

**⇒ 六个（含 86）。**

**⚠ 而 `sprintDelay` 是**1 位**？**

**⇒ 而 §317 的 `PlayerStateSprintDelayField = 93` 没说宽度。**

**⇒ 而 `#include` 的命令名叫 `sprintDelay` 而**只有 1 位** ⇒ 所以它是一个**布尔**。**

**✅ 与记忆里"`sprintButtonUpRequired`"（也是 1 位）配合。**

### 5.1 而 `sprintDelay` 与 `sprintButtonUpRequired` **都是 1 位**

**⇒ 三层**：

```text
1. `sprintDelay`（93）
2. ⇒ `sprintButtonUpRequired`（101）
3. ⇒ **两个都是 1 位布尔**
```

**✅ 与 §317 的 `PlayerStateSprintButtonUpRequiredField = 101` 与 `PlayerStateSprintDelayField = 93` 一致。**

## 六、`viewHeightLerpTime` 的 **32 位**

```php
writeUnsignedDelta(message, (uint32)state.viewHeightLerpTime, (uint32)baselineViewHeightLerpTime, 32);
```

**⇒ 三层**：

```text
1. `int32` 强转 `uint32`
2. ⇒ 32 位无符号
3. ⇒ 所以**能表示负值（补码）**
```

**⚠ 一个"32 位无符号"装一个 int32 ⇒ 等价于**补码传输**。**

## 七、`proneDirection` / `proneTorsoPitch` / `proneDirectionPitch` 都用 `writeFullFloatDelta`

```cpp
writeFullFloatDelta(message, state.proneDirection, baselineProneDirection);
writeFullFloatDelta(message, state.proneTorsoPitch, baselineProneTorsoPitch);
writeFullFloatDelta(message, state.proneDirectionPitch, baselineProneDirectionPitch);
```

**⇒ 三个**浮点**。**

**✅ 与 §284 的 `CodolWorldPlayerSampleV2` 的 `proneDirection`/`proneDirectionPitch`/`proneTorsoPitch` 三个 float 配合。**

## 八、`proneTransitionStartTime` 用 `writeCommandTime`

```cpp
writeCommandTime(message, state.proneTransitionStartTime, serverTime);
```

**⇒ 三层**：

```text
1. 一个**时间**
2. ⇒ 用 `-97` 类的 codec（`writeCommandTime`）
3. ⇒ 所以**近期 9 位，远期 33 位**
```

**✅ 与 §326 的"三个时间字段共用 `-97`"配合（第四次）。**

## 九、`jumpTime` 的 **32 位**

```cpp
writeUnsignedDelta(message, state.jumpTime, baselineJumpTime, 32);
```

**⚠ 而 `jumpTime` 是 32 位。**

**⇒ 与 §284 的 `jumpTime`（`uint32`）配合。**

## 十、`shellshockIndex` 的 **4 位**

```cpp
writeUnsignedDelta(message, state.shellshockIndex, baselineShellshockIndex, 4);
```

**⇒ 三层**：

```text
1. 字段 105
2. ⇒ 4 位（0..15）
3. ⇒ 所以最多 16 个 shellshock 索引
```

## 十一、`state.weaponShotCount[0]` 的 **3 位**

```cpp
writeUnsignedDelta(message, state.weaponShotCount[0], baselineWeaponShotCount[0], 3);
```

**⇒ 三层**：

```text
1. 字段 87
2. ⇒ **3 位**（0..7）
3. ⇒ 所以**每次最多 7 发**
```

**✅ 与 `shotCount` 在 §240 的界（`<= 0xFF`）不同 —— 线格式是 3 位。**

**⚠ 所以一个 8 发的霰弹枪会**截断**。**

## 十二、`mantleFlags` 的 **8 位**

```cpp
writeUnsignedDelta(message, state.mantleFlags, baselineMantleFlags, 8);
```

**✅ 8 位。**

## 十三、**`lastChangedFieldIndex == X` 的七个位置**

**⇒ 这是"hint-2 字段的两个写入点"的实现：**

```text
主循环里：if (XChanged && lastChangedFieldIndex == X)  ⇒ 写（带索引）
第二 pass：if (XChanged)                                 ⇒ 写（不带索引）
```

**⚠ 所以每个 hint-2 字段的**两个分支**散在各处。**

**⇒ 一个**维护风险**（改一处会漏另一处）。**

## 十四、关键结论

1. **⭐ `compassRadar` 放进第二 pass 导致快照停止解码** —— 因为 86 是 `type 0` 而不在 `PlayerStateSecondPassFields` 里。
2. **"客户端搜寻一个不在线上的字段并跑出缓冲区末尾"**。
3. **"`Tools/demo-re` 用残差 0 解码旧的而新的完全解不出来"** —— 它被抓到的方式。
4. **八个 `PlayerStateSecondPassFields`**（82/89/93/98/101/104/106/122 = `type-2`）。
5. **七个 `lastChangedFieldIndex == X` 门**（82/89/93/98/101/104/106）。
6. **"一个 hint-2 字段如果它自己是最后一个 ⇒ 终止索引 pass"**。
7. **每个 hint-2 字段有两个写入点** —— 一个带索引一个不带。
8. **`compassRadar` 用 codec `1`**（一位 XOR 基线）。
9. **六个 1 位字段**（86/89/93/98/101/106）。
10. **`sprintDelay` 是 1 位布尔**。
11. **`viewHeightLerpTime` 32 位无符号装 int32**（补码传输）。
12. **三个 `prone*` 用 `writeFullFloatDelta`**。
13. **`proneTransitionStartTime` 用 `writeCommandTime`**（第四次）。
14. **`jumpTime` 32 位、`shellshockIndex` 4 位、`mantleFlags` 8 位。**
15. **⚠ `weaponShotCount` 只有 3 位（0..7）** ⇒ 8 发的霰弹会截断。

## 十五、未闭合点

- `weaponShotCount` 3 位是否真的够（霰弹枪）。
- 七个 hint-2 字段的两个写入点是否都正确。
- `hint 0/1/2/3` 与 `type 0/2` 的完整对应。
- `sv_snapshot_mp.cpp` 4390 行之后未读取（1.47 MB，进度 29%）。
