# 323 · **六种位编码原语**、`writePackedBits` 的"整字节独立推进"、`heldWeapons` 的十二位未知尾

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1998–2200 行。

## 二、`writeEmptyPlayerState` 的**三个零**

```cpp
message.MSG_WriteBits(0, 1);                              // 无字段
message.MSG_WriteBits(0, PlayerStateLastChangedBits);      // 8 位
message.MSG_WriteBits(0, PlayerStateAuxiliarySectionBits); // 17 位
```

**⇒ 三层**：

```text
1 位     无字段变化
8 位     lastChanged = 0
17 位    辅助段掩码 = 0（【十七位】）
```

**✅ 与 §316 的"OLfinal 有十七个尾部段"**完全一致** ✓**

**⇒ 所以 `writeEmptyPlayerState` 是**最小的合法 playerstate**。**

## 三、**两种字段索引编码**（本组第二重要）

### 3.1 `writePlayerStateFieldIndex` —— **4 位扩展间隔**

```cpp
void writePlayerStateFieldIndex(MsgWriter &message, uint32 fieldIndex, int32 &lastFieldIndex)
{
    const auto delta = (int32)fieldIndex - lastFieldIndex;
    if (delta == 1)
    {
        message.MSG_WriteBits(1, 1);            // ← 【1 位 = 连续】
    }
    else
    {
        message.MSG_WriteBits(0, 1);            // ← 【0 位 = 跳跃】
        auto remaining = delta - 1;
        while (remaining >= 15)
        {
            message.MSG_WriteBits(15, 4);       // ← 【15 = 继续】
            remaining -= 15;
        }
        message.MSG_WriteBits(remaining, 4);    // ← 【终止】
    }
    lastFieldIndex = (int32)fieldIndex;
}
```

### 3.2 五层

```text
① delta == 1 ⇒ 一个 1 位
② 否则 ⇒ 一个 0 位
③ 然后 `delta - 1` 用 4 位块表示
④ 每块 15 表示"继续"
⑤ 最后一块 < 15 表示"终止"
```

**✅ 一个**变长的间隔编码**。**

**⇒ 而 `delta == 1`（连续）最便宜（1 位）。**

### 3.3 `writeObjectiveFieldIndex` —— **一元编码**

```php
void writeObjectiveFieldIndex(MsgWriter &message, uint32 fieldIndex, int32 &lastFieldIndex)
{
    // CODOL sub_5A34F0 calls sub_5A3250 with indexBits=1 for the
    // six objective_t fields.  That branch is unary: delta-1 zeroes
    // followed by one.  It is not the playerstate table's 4-bit
    // extended gap encoding.
    const auto delta = (int32)fieldIndex - lastFieldIndex;
    for (auto skipped = 1; skipped < delta; ++skipped)
        message.MSG_WriteBits(0, 1);
    message.MSG_WriteBits(1, 1);
    lastFieldIndex = (int32)fieldIndex;
}
```

### 3.4 四层

```text
1. `sub_5A34F0` 对六个 `objective_t` 字段用 `indexBits=1` 调用 `sub_5A3250`
2. ⇒ 那个分支是**【一元】**：`delta - 1` 个零后跟一个一
3. ⇒ **不是** playerstate 表的 4 位扩展间隔编码
4. ⇒ 所以**两个不同的索引编码**
```

### 3.5 而**两种编码的对比**

```text
playerstate   1 位（连续）或 0 + 4 位块（跳跃）
objective     delta-1 个 0 位 + 1 个 1 位（一元）
```

**⚠ 一元编码在 `delta` 大时**非常贵**。**

**⇒ 而目标字段只有 6 个 ⇒ `delta <= 9` ⇒ 最贵 9 位。**

**✓ 可接受。**

**✅ 与 §316 的"`ObjectiveFieldCount = 9`"配合 —— 所以一元最贵 9 位。**

## 四、`writeCommandTime` 的**两种**

```cpp
void writeCommandTime(MsgWriter &message, uint32 commandTime, uint32 serverTime)
{
    if (commandTime <= serverTime && serverTime - commandTime <= 0xFF)
    {
        message.MSG_WriteBits(0, 1);
        message.MSG_WriteBits(serverTime - commandTime, 8);   // ← 9 位合计
    }
    else
    {
        message.MSG_WriteBits(1, 1);
        message.MSG_WriteLong(commandTime);                   // ← 33 位
    }
}
```

**⇒ 两种**：

```text
近期  1 位 0 + 8 位差  = 9 位
远期  1 位 1 + 32 位绝对值 = 33 位
```

**✅ 一个**经典的"最近值"压缩**。**

## 五、**`writePackedBits` 的"整字节独立推进"**（本组最重要的一段）

### 5.1 那段

```cpp
void writePackedBits(MsgWriter &message, uint32 value, uint32 bits)
{
    // CODOL's positive netfield primitive reads only the non-byte remainder
    // from the bit cursor. Whole bytes advance msg.readcount independently.
    switch (bits)
    {
    case 8:  message.MSG_WriteByte((uint8)value); break;
    case 16: message.MSG_WriteShort((uint16)value); break;
    case 32: message.MSG_WriteLong(value); break;
    default:
        const auto remainderBits = bits & 7;
        if (remainderBits)
            message.MSG_WriteBits(value, remainderBits);
        for (auto shift = remainderBits; shift < bits; shift += 8)
            message.MSG_WriteByte((uint8)(value >> shift));
        break;
    }
}
```

### 5.2 五层

```text
1. **CODOL 的正 netfield 原语只从位游标读【非整字节的余数】**
2. ⇒ **整字节独立推进 `msg.readcount`**
3. ⇒ 所以 `bits % 8` 从**位游标**写
4. ⇒ 其余**整字节**从**字节游标**写
5. ⇒ 而 8/16/32 直接走字节写（没有余数）
```

### 5.3 **这是一个极容易搞错的细节**

**⇒ 三层**：

```text
1. 大部分位流是**连续的位**
2. ⇒ 而这里**整字节独立推进**（不占位游标）
3. ⇒ 所以两者**交替**推进
```

**✅ 与记忆里"`msg_t` 0x30 with 32-bit-only asserts"**相关。**

**⇒ 而"位游标"与"字节游标"是**两个独立的位置**。**

**⚠ 这是一个非常不寻常的设计。**

### 5.4 而 `bits & 7` 与 `shift += 8`

```text
remainder = bits & 7        （1..7）
先写 remainder 位
然后从 shift = remainder 开始，每次 8 位
直到 shift >= bits
```

**⇒ 例：`bits = 13` ⇒ `remainder = 5`。**

```text
先写 5 位（位游标）
然后 shift = 5, 13 ⇒ 写 1 个字节（8 位）
⇒ 5 + 8 = 13 ✓
```

**✅ 算术闭合。**

**⇒ 例：`bits = 10` ⇒ `remainder = 2`。**

```text
先写 2 位
然后 shift = 2, 10 ⇒ 写 1 个字节
⇒ 2 + 8 = 10 ✓
```

### 5.5 而 `bits = 11` ⇒ `remainder = 3`

```text
先写 3 位
shift = 3, 11 ⇒ 1 个字节
⇒ 3 + 8 = 11 ✓
```

**⚠ 但 `value >> 3` 会**丢掉低 3 位**（它们已经写在位游标里了）✓**

**✅ 正确。**

## 六、`writeUnsignedDelta` 与 `writeSignedDelta` 的**三项**

```cpp
void writeUnsignedDelta(MsgWriter &message, uint32 value, uint32 baseline, uint32 bits)
{
    if (!value) { message.MSG_WriteBits(0, 1); return; }      // ① 零 ⇒ 一个 0 位
    message.MSG_WriteBits(1, 1);                              // ② 非零 ⇒ 一个 1 位
    const auto mask = bits == 32 ? UINT32_MAX : (1u << bits) - 1;
    writePackedBits(message, value ^ (baseline & mask), bits); // ③ XOR + 打包
}
```

### 6.1 三项

```text
① 零 ⇒ 一个 0 位（【最便宜】）
② 非零 ⇒ 一个 1 位
③ 然后 `value ^ baseline` 打包 bits 位
```

**✅ 与 §314 的"`damageCount = 0` 时最便宜"配合。**

### 6.2 而 `writeSignedDelta` 的**唯一差别**

```cpp
writePackedBits(message, (uint32)value ^ (uint32)baseline) & mask, bits);
```

**⚠ 而 `writeUnsignedDelta` 是 `value ^ (baseline & mask)` —— 先掩基线。**

**⇒ `writeSignedDelta` 是 `(value ^ baseline) & mask` —— 先 XOR 后掩。**

**⚠ **两处不同的顺序**！**

**⇒ 而结果是：**

```text
unsigned   (value ^ (baseline & mask))       基线先被掩
signed     ((value ^ baseline) & mask)      结果被掩
```

**⇒ 若 `value` 已经在 mask 内，则 `value ^ (baseline & mask)` 与 `(value ^ baseline) & mask` **等价**（因为 `value & mask == value`）。**

**✓ 所以等价 —— 但**风格不一致**。**

### 6.3 而 `writeSignedDelta` **不检查符号**

**⇒ 直接用 `(uint32)value` 转换 ⇒ 补码。**

**✓ 所以负数的位模式被直接写出。**

## 七、`write30BitFlagDelta` 的**两分支**（本组第三重要）

```cpp
void write30BitFlagDelta(MsgWriter &message, uint32 value, uint32 baseline)
{
    const auto difference = value ^ baseline;
    if (std::has_single_bit(difference))
    {
        message.MSG_WriteBits(0, 1);
        message.MSG_WriteBits(std::countr_zero(difference), 5);   // ← 5 位位置
        return;
    }
    message.MSG_WriteBits(1, 1);
    // CODOL sub_5A22E0 consumes the full branch through one
    // MSG_ReadBits(30), not the positive-netfield mixed raw cursor.
    message.MSG_WriteBits((int32)value, 30);                      // ← 30 位
}
```

### 7.1 两分支

```text
单一位差  ⇒ 1 位 0 + 5 位位置    = 6 位
否则      ⇒ 1 位 1 + 30 位全值   = 31 位
```

**✅ 一个**"单比特变化"的优化**。**

### 7.2 而 `has_single_bit` 与 `countr_zero`

**⇒ 两个 C++20 `<bit>` 函数。**

**✅ 与文件头的 `#include <bit>` 配合。**

### 7.3 而"**`sub_5A22E0` 通过一次 `MSG_ReadBits(30)` 消费全分支**"

**⇒ 三层**：

```text
1. 全分支是**一个 30 位读**
2. ⇒ **不是"正 netfield 混合原始游标"**
3. ⇒ 所以**这个字段不用 `writePackedBits`**
```

**✅ 与 §5 的 `writePackedBits` 的"整字节独立推进"**不同 —— 这里是**纯位**。**

**⇒ 所以两种打包**共存**。**

## 八、`writeHeldWeapons` 的**六层**（本组第四重要）

```cpp
void writeHeldWeapons(MsgWriter &message,
    const std::array<SvHeldWeaponState, 15> &heldWeapons,
    const std::array<SvHeldWeaponState, 15> &baseline)
{
    const auto anyChanged = heldWeapons != baseline;
    message.MSG_WriteBits(anyChanged ? 1 : 0, 1);        // ① 整体变化位
    if (!anyChanged) return;

    for (index = 0; index < 15; ++index)
    {
        const auto changed = weapon != baselineWeapon;
        message.MSG_WriteBits(changed ? 1 : 0, 1);        // ② 每槽变化位
        if (!changed) continue;

        const auto assetChanged = weapon.weaponAssetIndex != baselineWeapon.weaponAssetIndex;
        message.MSG_WriteBits(assetChanged ? 1 : 0, 1);   // ③ 资产变化位
        if (assetChanged)
            message.MSG_WriteBits(weapon.weaponAssetIndex, HeldWeaponIndexBits);   // ④ 11 位
        message.MSG_WriteBits(weapon.heldBefore ? 1 : 0, 1);                       // ⑤
        for (const auto flag : weapon.unknownState)
            message.MSG_WriteBits(flag ? 1 : 0, 1);                                // ⑥ 五个标志
        message.MSG_WriteBits(0, HeldWeaponUnknownTailBits);                       // ⑦ 12 位零
    }
}
```

### 8.1 七层

```text
① 整体变化位
② 每槽变化位
③ 资产变化位
④ 11 位资产（仅变化时）
⑤ heldBefore 一位
⑥ 五个 unknownState 位
⑦ 【12 位零】
```

### 8.2 而"**15 个槽**"

**⇒ 与记忆里"`heldWeapons` 的 `list2F4=1224,1226,0,0,0,0`"（6 个可见）**不同**。**

**⚠ §311 说 `list2F4` 有两个条目而这里是**15 槽数组**。**

**⇒ 可能 `list2F4` 只是**前几个**。**

### 8.3 而那个**十二位未知尾**

```php
// CODDIFF(1649370): a twelve-bit field 3.3.3.3 does not have,
// read after the five flag bits of every present slot. Its
// MEANING is unknown and deliberately not guessed; its width
// and position are not, and it is 0 in all 469 of its reads
// across the demo corpus, so writing 0 is what a real server
// is observed to do. Omitting it desynchronises every slot
// after the first.
message.MSG_WriteBits(0, HeldWeaponUnknownTailBits);
```

### 8.4 六层

```text
1. **一个 3.3.3.3 没有的十二位字段**
2. ⇒ 在**每一个存在槽的五个标志位之后**被读
3. ⇒ **它的含义未知而刻意不猜**
4. ⇒ 而**它的宽度与位置不是未知的**
5. ⇒ **在 demo 语料的全部 469 次读里它是 0**
6. ⇒ 所以**写 0 是一个真实服务器被观测到的行为**
7. ⇒ **省略它会失步第一个之后的每一个槽**
```

### 8.5 **"含义未知而刻意不猜，但宽芳与位置不是"**

**✅ 这是一个**精确的知识边界声明**。**

**⇒ 与 §319 的"三个未解释字段"、§318 的"不可移植"同族**（第十九次"明确知道什么不知道什么"）。

### 8.6 而 `HeldWeaponUnknownTailBits = 12`

**⇒ 与 §316 的 `HeldWeaponUnknownTailBits = 12`**完全一致** ✓**

**⇒ 而 §316 的 `AmmoPoolCountBits = 12` 也是 12。**

**⚠ 两个 12。**

## 九、`writeAmmoClips` 的开头

```cpp
void writeAmmoClips(MsgWriter &message,
    const std::array<SvAmmoClipState, 15> &ammoClips,
    const std::array<SvAmmoClipState, 15> &baseline)
{
    std::array<std::size_t, 15> changedIndexes{};
    std::size_t changedCount{};
    for (index = 0; index < ammoClips.size(); ++index)
        if (ammoClips[index] != baseline[index]) ...
```

**⇒ 先收集变化的索引。**

**⇒ 待读。**

## 十、关键结论

1. **`writeEmptyPlayerState` 的 17 位辅助段掩码** 与 §316 的"十七个尾部段"一致。
2. **两种字段索引编码**：playerstate 的 4 位扩展间隔 vs objective 的**一元编码**。
3. **一元最贵 9 位**（`ObjectiveFieldCount = 9`）。
4. **`writeCommandTime` 的 9 位 vs 33 位** 两种。
5. **⭐ `writePackedBits` 的"整字节独立推进 `readcount`"** —— **位游标与字节游标是两个独立位置**。
6. **`bits & 7` 的余数走位游标而整字节走字节游标** —— 算术闭合（13 = 5 + 8，10 = 2 + 8，11 = 3 + 8）。
7. **`writeUnsignedDelta` 零值最便宜（一个 0 位）**。
8. **`writeSignedDelta` 与 `writeUnsignedDelta` 的掩码顺序不同但等价** —— 风格不一致。
9. **`write30BitFlagDelta` 的两分支**（6 位 vs 31 位）。
10. **`sub_5A22E0` 用纯 30 位读** —— 不用 `writePackedBits`。
11. **`writeHeldWeapons` 七层**，15 个槽。
12. **十二位未知尾**在全部 469 次读里是 0 ⇒ **写 0 是观测到的行为**。
13. **"含义未知而刻意不猜，但宽度与位置不是"** —— 一个精确的知识边界。
14. **⚠ §311 的 `list2F4` 两个条目 vs 这里的 15 槽数组**。

## 十一、未闭合点

- `writeAmmoClips` 的完整实现。
- `list2F4` 与 15 槽的关系。
- `unknownState` 五个标志的语义。
- `sv_snapshot_mp.cpp` 2200 行之后未读取。
