# 335 · **`perks` 的三个 32 位"演示值用 bit 24"**、`offhandSlots` 的 32 位、`rewardTargets` 的 5 位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 4388–4590 行。

## 二、**`perks` 的三个 32 位**（本组最重要的一段）

### 2.1 那段

```php
// Full 32-bit values: the descriptor gives all three `bits 32`,
// and the demo's own values use bit 24, so nothing narrower would
// carry them.
if (perksChanged[0])
{
    writePlayerStateFieldIndex(message, PlayerStatePerkField0, lastFieldIndex);
    writeUnsignedDelta(message, state.perks[0], baselinePerks[0], 32);
}
... 同样两份 for [1] 与 [2] ...
```

### 2.2 四层

```text
1. **完整的 32 位值**
2. ⇒ **描述符给全部三个 `bits 32`**
3. ⇒ **而 demo 自己的值使用 bit 24**
4. ⇒ **所以没有任何更窄的宽度能携带它们**
```

### 2.3 **"演示值使用 bit 24"**

**⇒ 三层**：

```text
1. `perks[0..2]` 是三个 `uint32`
2. ⇒ 而 **demo 的值用到了 bit 24**（即 `0x01000000`）
3. ⇒ **所以至少需要 25 位**
4. ⇒ 而描述符说 32 ⇒ **所以用 32**
```

**✅ 一个**由实测数据决定的宽度**。**

**⇒ 与 §321 的"界是线的宽度"同族。**

**⚠ 而 §254 说"技能是 192 位掩码"而这里是**三个 32 位**。**

**⇒ 所以 `perks[0..2]` 是**三个 32 位字段** = 96 位。**

**⚠ 而 §254 的 `abilities.mask` 是**六个 uint32** = 192 位。**

**⇒ 两个不同的东西：**

```text
perks[0..2]           3 × 32 = 96 位    （playerState 的三个 netfield）
abilities.mask[0..5]  6 × 32 = 192 位   （能力的修饰符掩码）
```

**✅ 与 §317 的"技能是三个 netfield 而能力掩码是六个 uint32"**完全一致** ✓**

## 三、**`offhandSlots` 的 32 位**（本组第二重要）

```cpp
for (uint32 slot = 0; slot < offhandSlots.size(); ++slot)
{
    if (offhandSlots[slot] == baselineOffhandSlots[slot]) continue;
    writePlayerStateFieldIndex(message,
        PlayerStateOffhandSlotFirstField + slot, lastFieldIndex);
    writeUnsignedDelta(message, offhandSlots[slot], baselineOffhandSlots[slot], 32);
}
```

### 3.1 而 **32 位**而值是**武器索引**

**✅ 与 §317 的"`out.exe 0xDA8520` 字段 109..111 是 `ps+3E8..3F0`，每个 `{bits=32, type=0}`，**尽管它们的值域是武器索引**"**完全一致** ✓**

**✅ 三次确认。**

### 3.2 而 `offhandSlots.size()` 是 3

**✅ 与 §330 的"`offhandSlots` 3 个，字段 109..111"一致。**

## 四、`perkHudVisible` 的**一位直写**

```php
if (perkHudVisibleChanged && lastChangedFieldIndex == PlayerStatePerkHudVisibleField)
{
    writePlayerStateFieldIndex(message, PlayerStatePerkHudVisibleField, lastFieldIndex);
    message.MSG_WriteBits(state.perkHudVisible ? 1u : 0u, 1);
}
```

### 4.1 而**这是唯一一个直写 1 位的**

**⇒ 三层**：

```text
1. 其它 1 位字段都用 `writeUnsignedDelta(..., 1)`
2. ⇒ 而 `perkHudVisible` 直写 `MSG_WriteBits(..., 1)`
3. ⇒ **因为 codec `-57` 是"一位，绝对，无基线 xor"**
```

**✅ 与 §317 的"codec `-57`：一位，绝对，无基线 xor"**完全一致** ✓**

**⚠ 一个重要区别**：`writeUnsignedDelta` 会写一个**存在位 + 一位**（2 位），而这里只写 **1 位**。

### 4.2 而那段注释

```php
// Like every type-2 field, 122 is written here only when it is the
// highest changed field. Otherwise the client consumes it positionally
// in the second pass. Fabricating a later bound leaves the indexed pass
// without its advertised endpoint and shifts every following section.
```

**⇒ 四层**：

```text
1. **像每一个 type-2 字段，122 只在它是最高变化字段时在这里写**
2. ⇒ 否则客户端在第二 pass 里按位置消费它
3. ⇒ **伪造一个更晚的上界会让索引 pass 失去它宣告的端点**
4. ⇒ **并移动每一个后续段**
```

**✅ "伪造一个更晚的上界会让索引 pass 失去端点"** —— 与 §334 的"86 不在线上导致跑出缓冲区"**同一机制**（第三十一次）。

## 五、`rewardIds` 的 **8 位**与 `rewardTargets` 的 **5 位**

```cpp
for (uint32 slot = 0; slot < 5; ++slot)
{
    if (rewardIds[slot] == oldRewardIds[slot]) continue;
    writePlayerStateFieldIndex(message, PlayerStateRewardIdFirstField + slot, lastFieldIndex);
    writeUnsignedDelta(message, rewardIds[slot], oldRewardIds[slot], 8);       // 8 位
}
for (uint32 slot = 0; slot < 5; ++slot)
{
    if (rewardTargets[slot] == oldRewardTargets[slot]) continue;
    writePlayerStateFieldIndex(message, PlayerStateRewardTargetFirstField + slot, lastFieldIndex);
    writeUnsignedDelta(message, rewardTargets[slot], oldRewardTargets[slot], 5);  // 5 位
}
```

### 5.1 而**两个不同的宽度**

```text
rewardIds      8 位（0..255）
rewardTargets  5 位（0..31）
```

**✅ 三层**：

```text
1. `rewardIds` 是**奖励 id**（8 位）
2. ⇒ `rewardTargets` 是**目标编号**（5 位）
3. ⇒ 因为目标最多 31 个
```

**⚠ 而 `MaximumGameClients = 18` ⇒ 5 位（0..31）够。**

## 六、`killCam` 的三个用 **11/11/8**

```cpp
writeUnsignedDelta(message, state.killCamEntityNum, baselineKillCamEntityNum, 11);        // 136
writeUnsignedDelta(message, state.killCamLookAtEntityNum, baselineKillCamLookAtEntityNum, 11);  // 137
writeUnsignedDelta(message, state.killCamClientNum, baselineKillCamClientNum, 8);          // 138
```

**⇒ 三个：**entity 11 / lookAt 11 / clientNum 8**。**

**✅ 与 §317 的"136/137/138 连续"配合。**

### 6.1 而那段注释

```php
// THE KILLCAM'S THREE ENTITY/CLIENT FIELDS, IN TABLE ORDER. 136, 137
// and 138 are consecutive and must be written between the perks
// (125) and LeftWeaponShotCount (140); writePlayerStateFieldIndex
// encodes the gap from the previous index and walks FORWARD ONLY.
```

**⇒ 四层**：

```text
1. **136/137/138 连续**
2. ⇒ 必须在 **`perks`(125) 与 `LeftWeaponShotCount`(140) 之间**写
3. ⇒ 因为 `writePlayerStateFieldIndex` **从前一个索引编码间隔**
4. ⇒ **而只向前走**
```

**✅ 与 §319 的"写序必须递增"**第五次**。**

## 七、`killCamDeltaTime` 的 **32 位**

```cpp
writeUnsignedDelta(message, state.killCamDeltaTime, baselineKillCamDeltaTime, 32);
```

**⇒ 字段 142，32 位。**

## 八、`ladderVector[0]` 用 `writeFullFloatDelta`

```cpp
if (ladderVectorChanged[0])
{
    writePlayerStateFieldIndex(message, PlayerStateLadderVectorXField, lastFieldIndex);
    writeFullFloatDelta(message, state.ladderVector[0], baselineLadderVector[0]);
}
```

**⇒ 字段 161，浮点。**

**✅ 而 §317 的 `PlayerStateLadderVectorXField = 161`、`Y = 177`、`Z = 188`。**

**⇒ 三个**极不连续**（161、177、188）。**

## 九、`mantleTimer` 的 **32 位**与 `mantleTransitionIndex` 的 **4 位**

```cpp
writeUnsignedDelta(message, state.mantleTimer, baselineMantleTimer, 32);                       // 108
writeUnsignedDelta(message, state.mantleTransitionIndex, baselineMantleTransitionIndex, 4);    // 113
```

**⇒ 两个：32 / 4。**

**✅ 与 §284 的 `CodolWorldPlayerSampleV2` 的 `mantleTimer`（uint32）与 `mantleTransitionIndex`（uint32）配合。**

**⇒ 而线格式是 4 位（0..15）而采样是 32 位。**

## 十、`jumpOriginZ` 与 `mantleYaw` 用 `writeFullFloatDelta`

```cpp
writeFullFloatDelta(message, state.jumpOriginZ, baselineJumpOriginZ);    // 114
writeFullFloatDelta(message, state.mantleYaw, baselineMantleYaw);        // 115
```

**⇒ 两个浮点。**

**✅ 与 §284 的 `jumpOriginZ`（float）与 `mantleYaw`（float）配合。**

## 十一、`weaponHandFlags` 的 **3 位**

```cpp
writeUnsignedDelta(message, state.weaponHandFlags[0], baselineWeaponHandFlags[0], 3);   // 121
writeUnsignedDelta(message, state.weaponHandFlags[1], baselineWeaponHandFlags[1], 3);   // 163
```

**⇒ 两个 3 位。**

**✓ 与 `weaponShotCount` 的 3 位**同样的宽度**。**

## 十二、`weaponTime` 的 **16 位有符号**

```cpp
writeSignedDelta(message, state.weaponTime[1], baselineWeaponTime[1], 16);   // 162
```

**⚠ 而 `weaponTime[0]` 在 §331 也用 `writeSignedDelta(..., 16)`。**

**⇒ 两个都是 16 位有符号。**

## 十三、`weaponDelay` 的 **16 位有符号**（两处）

```cpp
writeSignedDelta(message, state.weaponDelay[1], baselineWeaponDelay[1], 16);   // 107
```

**⚠ 而 `weaponDelay[0]` 在 §332 用 16 位有符号（字段 44）。**

**⇒ 两个都是 16 位有符号，而**字段号差 63**（44 vs 107）。**

## 十四、`remoteTurretEntity` 的写入

```cpp
if (remoteTurretEntityChanged)
{
    writePlayerStateFieldIndex(message, PlayerStateRemoteTurretEntityField, lastFieldIndex);
    writeUnsignedDelta(message, state.remoteTurretEntityNum, baselineRemoteTurretEntityNum, ...
```

**⇒ 字段 168（待读宽度）。**

## 十五、关键结论

1. **`perks` 的三个 32 位** —— "描述符说 `bits 32` 而 demo 用 bit 24" ⇒ **没有更窄的宽度能携带**。
2. **`perks[0..2]` = 96 位** 而 **`abilities.mask[0..5]` = 192 位** —— 两个不同的东西（第三次确认）。
3. **`offhandSlots` 的 32 位** 而值是武器索引 —— 与 §317 的三次一致。
4. **`perkHudVisible` 是唯一**直写 1 位**的**（codec `-57` = 一位绝对无 xor）。
5. **`writeUnsignedDelta(..., 1)` 会写 2 位（存在位 + 1 位）而直写只 1 位。**
6. **"伪造一个更晚的上界会让索引 pass 失去端点并移动每一个后续段"**。
7. **`rewardIds` 8 位 / `rewardTargets` 5 位** —— 两个不同宽度。
8. **`killCam` 的三个 11/11/8**，且"必须在 `perks`(125) 与 `LeftWeaponShotCount`(140) 之间"。
9. **`killCamDeltaTime` 32 位。**
10. **`ladderVector` 的三个索引 161/177/188 极不连续。**
11. **`mantleTimer` 32 位线格式而 `mantleTransitionIndex` 4 位。**
12. **`jumpOriginZ` 与 `mantleYaw` 用 `writeFullFloatDelta`。**
13. **`weaponHandFlags` 3 位（两个）同 `weaponShotCount` 的 3 位。**
14. **`weaponTime` 与 `weaponDelay` 都是 16 位有符号，而字段号差 63（44 vs 107）。**

## 十六、未闭合点

- `perks[0..2]` 的 bit 24 具体是什么。
- `remoteTurretEntity` 的宽度。
- `ladderVector` 为何 161/177/188。
- `sv_snapshot_mp.cpp` 4590 行之后未读取（1.47 MB，进度 31%）。
