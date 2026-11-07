# 333 · **`-102` codec 从"28 位原始"变成"一位 + 31 位"**、`cursorHintString` 是三个提示里唯一有符号的、`radarFlags` 的 hint-2

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 3983–4190 行。

## 二、**`otherFlags` 的 codec 变化**（本组最重要的一段）

### 2.1 那段八层

```php
// CODDIFF(1649370): this field CHANGED CODEC, not just width.
// 3.3.3.3's descriptor reads 28 raw bits; this build's says
// codec -102, which does not exist on 3.3.3.3 at all. Its
// decode is transcribed from 0x670414 -- one present bit, then
// THIRTY-ONE bits, or literal 0 when the bit is clear -- and
// that transcription decodes 6160/6160 real retail snapshots
// to the exact endpoint, so it is measured rather than
// guessed. 28 raw bits stood here while that was still open,
// on the grounds that a guessed codec desynchronises the whole
// playerState section rather than one field; it is no longer a
// guess.
//
// -102 carries the value ABSOLUTELY: it shares a return path
// with -101, not a width, and neither XORs against the
// baseline. So this must not go through writeUnsignedDelta.
// baselineOtherFlags is still what decides whether the field is
// sent at all, one caller up.
if (state.otherFlags)
{
    message.MSG_WriteBits(1, 1);            // ← 存在位
    message.MSG_WriteBits(state.otherFlags, 31);   // ← 【31 位】
}
else
{
    message.MSG_WriteBits(0, 1);            // ← 不存在
}
```

### 2.2 十层

```text
1. **这个字段【改变了 codec】，不只是宽度**
2. ⇒ 3.3.3.3 的描述符读 **28 个原始位**
3. ⇒ **而这个 build 说 codec `-102`，它在 3.3.3.3 上根本不存在**
4. ⇒ 它的解码转写自 **`0x670414`** —— **一个存在位，然后【三十一位】，或当位清零时字面 0**
5. ⇒ **而那个转写把 6160/6160 个真实零售快照解码到精确端点**
6. ⇒ **所以它是【测量过的】而不是【猜的】**
7. ⇒ **"28 原始位"曾站在这里当那还开放时**，理由是**一个猜的 codec 会失步整个 playerState 段而不是一个字段**
8. ⇒ **它不再是一个猜**
9. ⇒ **`-102` 绝对地携带这个值**：它与 `-101` **共享一条返回路径，不是一个宽度**
10. ⇒ **而两者都不 XOR 基线** ⇒ **所以这绝不能走 `writeUnsignedDelta`**
```

### 2.3 **"一个猜的 codec 会失步整个段而不是一个字段"**

**✅ 这与本文件反复的主题一致**（第二十九次"一个错毁掉整段"）。**

**⇒ 而"所以宁可先用 28 位原始"是一个**保守的占位**。**

**✅ 与 §318 的"28 原始位"、§316 的"三个缺失位"同族。**

### 2.4 而 `-102` 与 `-101`

**⇒ 三层**：

```text
1. `-102` 与 `-101` **共享一条返回路径**
2. ⇒ 而**不是一个宽度**
3. ⇒ **两者都不 XOR 基线**
```

**✅ 所以 `-101` 与 `-102` 是**同一族**。**

### 2.5 而 `-102` 是**第十二个负 codec**

```text
-7, -8, -57, -58, -65, -70, -75, -86, -94, -97, -100, -101, -102    （十三个）
```

## 三、`cursorHintString` 是**三个提示里唯一有符号的**（本组第二重要）

### 3.1 那段

```php
// SIGNED, and this is the one field of the three that is.
// Codec -8 sign-extends from bit 7 on the client, which is what
// makes -1 expressible at all; writing it unsigned would put
// 255 on the wire and the client would read it back as -1 by
// luck for that one value and wrongly for every other.
writePlayerStateFieldIndex(message, PlayerStateCursorHintStringField, lastFieldIndex);
writeSignedDelta(message, state.cursorHintString, baselineCursorHintString, 8);
```

### 3.2 六层

```text
1. **有符号，而这是三个里唯一一个**
2. ⇒ **codec `-8` 在客户端从第 7 位符号扩展**
3. ⇒ **那正是为什么 `-1` 可表达**
4. ⇒ **无符号写会把 255 放上线**
5. ⇒ **而客户端会读回 `-1` —— 对那一个值靠运气**
6. ⇒ **而对其它每一个值都错**
```

### 3.3 **"对那一个值靠运气而对其它每一个值都错"**

**✅ 一个**极精确的表述**。**

**⇒ 因为 `255` 与 `-1` 在 8 位补码里是**同一个位模式**。**

**✓ 所以只有 `-1` 会"碰巧对"。**

### 3.4 而三个提示的**三种符号性**

```text
cursorHint          字段 67   无符号 11 位
cursorHintEntityNum 字段 78   无符号 11 位
cursorHintString    字段 80   【有符号 8 位】
```

**✅ 与 §317 的"`CursorHint` 三字段（67 `+0x24C` 11 位 / 78 `+0x254` 11 位 / 80 `+0x250` codec `-8`）"**完全一致** ✓**

**⇒ 而 §317 已说"80 是唯一有符号的而它的空闲值是 -1"。**

**✅ 三次确认。**

## 四、`radarFlags` 的 **hint-2 与"零需要显式载荷"**（本组第三重要）

### 4.1 那段

```php
// A hint-2 field that is itself last terminates the indexed pass;
// otherwise it is written without an index in the second pass.
if (radarFlagsChanged && lastChangedFieldIndex == PlayerStateRadarFlagsField)
{
    writePlayerStateFieldIndex(message, PlayerStateRadarFlagsField, lastFieldIndex);
    // CODREF(OLfinal 6702B9 -> 670C9C): absence does not invoke
    // the secure setter. A changed zero needs an explicit payload.
    message.MSG_WriteBits(1u, 1);
    message.MSG_WriteBits(state.radarFlags, 6);
```

### 4.2 六层

```text
1. **一个 hint-2 字段如果它自己是最后一个 ⇒ 终止索引 pass**
2. ⇒ 否则它**在第二 pass 里不带索引被写**
3. ⇒ 而 `radarFlags` 是 hint-2
4. ⇒ **`OLfinal 6702B9 -> 670C9C`：缺席不调用安全 setter**
5. ⇒ **所以一个变化为零需要显式载荷**
6. ⇒ 所以**总是写 `1`（存在）+ 6 位值**
```

### 4.3 **"缺席不调用安全 setter"**

**✅ 三层**：

```text
1. 如果字段**缺席** ⇒ 安全 setter 不被调用
2. ⇒ 所以一个"变化为 0"不能靠缺席表达
3. ⇒ **必须显式写 `1` + 6 位 `0`**
```

**✅ 与 §326 的"`cursorHint` 零基线不发"**相反**：**

```text
cursorHint      零 ⇒ 不发（因为零是"无提示"的默认）
radarFlags      零 ⇒ 【必须发】（因为零是新值）
```

**⇒ 两个零的两种语义。**

### 4.4 而**"hint-2"**是什么

**⇒ 与 §330 的"字段 122 是一个 `type 2` 字段"配合。**

**⇒ 所以 `type 2` = `hint 2`。**

**✅ 而 `hint 2` 的语义是"字段变化时必须显式写，包括零"。**

**⇒ 与 §328 的 `changeHint == 3`（总是发）不同。**

**⇒ 四种 hint：**

```text
hint 0   普通（零 ⇒ 不发）
hint 2   零也需要显式载荷
hint 3   总是发（不看变化）
（hint 1 ?）
```

## 五、`damageEvent` 从**索引 61/16 位**变成 **66/8 位**

```php
// 66 SITS BETWEEN GRAVITY (63) AND VIEWENTITY (68). It used to be
// written as index 61 with a SIXTEEN-bit width; the field is eight
// bits and the demo's range is 0..7.
if (damageEventChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateDamageEventField, lastFieldIndex);
    writeUnsignedDelta(message, state.damageEvent, baselineDamageEvent, 8);
}
```

**⇒ 三层**：

```text
1. **它过去被写成索引 61 而宽度十六位**
2. ⇒ 而**这个字段是八位而 demo 的范围是 0..7**
3. ⇒ 所以现在是**索引 66 + 8 位**
```

**✅ 与 §317 的"`66 +0x190 8 damageEvent`"**完全一致** ✓**

**⇒ 而 §314 说"`damageEvent` 是一个三位计数器而客户端只读变化"。**

**⚠ 三位 vs 八位。**

**⇒ 而 §317 说"8 位，244 次，范围 0..7"。**

**✅ 所以"8 位宽度但只用 0..7"。**

## 六、`damageCount` 的 **7 位**

```php
if (damageCountChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateDamageCountField, lastFieldIndex);
    writeUnsignedDelta(message, state.damageCount, baselineDamageCount, 7);
}
```

**✅ 与 §317 的"`74 +0x19C 7 damageCount`"**完全一致** ✓**

**⇒ 而 §317 说"范围 0..99"。**

**✅ 7 位能到 127 ⇒ 所以 0..99 在范围内。**

## 七、三个**注释里的顺序**

### 7.1 `66 在 gravity(63) 与 viewEntity(68) 之间`

### 7.2 `67 在 damageEvent(66) 与 viewEntity(68) 之间`

### 7.3 `73/74/75 在 deltaAngles[0](70) 与 viewHeightLerpTarget(81) 之间，按那个顺序`

### 7.4 `78 与 80 在 damageDuration(75) 与 viewHeightLerpTarget(81) 之间，按那个顺序 —— 实体先，字符串后，因为 78 < 80 而间隔编码是递增的`

**⇒ 四处**明确的顺序注释**。**

**✅ 与 §319 的"写序必须递增"同族**（第四次）。

## 八、`weaponFlags` 的 **24 位**

```php
if (weaponFlagsChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateWeaponFlagsField, lastFieldIndex);
    writeUnsignedDelta(message, state.weaponFlags(), baselineWeaponFlags, 24);
}
```

**⇒ 三层**：

```text
1. 字段 77
2. ⇒ 24 位
3. ⇒ 而 `weaponFlags()` 是一个**合成方法**
```

**⚠ 而 §317 的 `PlayerStateWeaponFlagsField = 77` 没说宽度。**

**⇒ 这里给出 24 位。**

## 九、`grenadeTimeLeft` 的 **16 位有符号**

```php
if (grenadeTimeChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateGrenadeTimeField, lastFieldIndex);
    writeSignedDelta(message, state.grenadeTimeLeft, baselineGrenadeTime, 16);
}
```

**⇒ 三层**：

```text
1. 字段 79
2. ⇒ **有符号** 16 位
3. ⇒ 所以**负值可表达**
```

**✅ 与 §324 的"`max(0, offhand.grenadeTimeLeft)`"配合 —— 所以 `grenadeTimeLeft` 可能为负。**

## 十、`viewHeightLerpTarget` 的 **8 位有符号**

```php
if (viewHeightLerpTargetChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateViewHeightLerpTargetField, lastFieldIndex);
    writeSignedDelta(message, state.viewHeightLerpTarget, baselineViewHeightLerpTarget, 8);
}
```

**✅ 与 §332 的 `viewHeightTarget`(38) 的 8 位有符号**同族。**

**⇒ 所以 `viewHeight` 家族有两个 8 位有符号 int 而一个浮点。**

## 十一、`moveSpeedScaleMultiplier` 用 `writeFullFloatDelta`

```php
if (moveSpeedScaleMultiplierChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateMoveSpeedScaleMultiplierField, lastFieldIndex);
    writeFullFloatDelta(message, state.moveSpeedScaleMultiplier, baselineMoveSpeedScaleMultiplier);
}
```

**⇒ 三层**：

```text
1. 字段 58
2. ⇒ `writeFullFloatDelta`（**两个 1 位 + 32 位**）
3. ⇒ 所以是**全浮点**
```

**✅ 与 §254 的"`modMoveSpeedScale`"配合。**

## 十二、`clientNum` 的 **8 位**

```cpp
writeUnsignedDelta(message, state.clientNum, baselineClientNum, 8)
```

**⇒ 而 §317 的 `PlayerStateClientNumField = 59` 没说宽度。**

**⇒ 8 位（0..255）而 `MaximumGameClients = 18` ⇒ 够。**

## 十三、`gravity` 与 `speed` 的 **16 位**

```cpp
writeUnsignedDelta(message, state.gravity, baselineGravity, 16)
writeUnsignedDelta(message, state.speed, baselineSpeed, 16)
```

**⇒ 两个 16 位无符号。**

**✅ 与 §286 的 `gravity`/`speed` 在 `CodolWorldPlayerSampleV1` 里是 `uint32` 配合。**

**⇒ 所以线格式是 16 位而采样是 32 位。**

## 十四、关键结论

1. **⭐ `otherFlags` 从"28 位原始"变成 codec `-102`（一位 + 31 位）**。
2. **`-102` 在 3.3.3.3 上不存在**，而转写自 `0x670414` 解码 **6160/6160** 到精确端点。
3. **"28 原始位"曾是一个**保守的占位**（因为"一个猜的 codec 会失步整个段"）。
4. **`-102` 与 `-101` 共享返回路径且都不 XOR 基线** ⇒ **不能走 `writeUnsignedDelta`**。
5. **十三个负 codec。**
6. **`cursorHintString` 是三个提示里唯一有符号的**（codec `-8` 符号扩展）。
7. **"无符号写会放 255 上线而对 `-1` 那一个值靠运气，其它每一个值都错"**。
8. **⭐ `radarFlags` 是 hint-2 ⇒ "缺席不调用安全 setter" ⇒ 一个变化为零需要显式载荷**。
9. **`cursorHint` 零 ⇒ 不发；`radarFlags` 零 ⇒ 必须发** —— 两个零的两种语义。
10. **`hint 2` = `type 2`**，与 `changeHint == 3`（总是发）不同。
11. **`damageEvent` 从索引 61/16 位变成 66/8 位**。
12. **`damageCount` 7 位**，与 §317 一致。
13. **四处明确的顺序注释**（66/67/73..75/78..80）。
14. **`weaponFlags` 24 位**、**`grenadeTimeLeft` 16 位有符号**、**`clientNum` 8 位**。
15. **`viewHeightLerpTarget` 8 位有符号** —— `viewHeight` 家族两个 int 一个浮点。
16. **`moveSpeedScaleMultiplier` 用 `writeFullFloatDelta`**。
17. **`gravity`/`speed` 线格式 16 位而采样 32 位。**

## 十五、未闭合点

- `hint 0/1/2/3` 的完整语义。
- `0x670414` 的完整转写。
- `-101` 是什么字段。
- `sv_snapshot_mp.cpp` 4190 行之后未读取（1.47 MB，进度 28%）。
