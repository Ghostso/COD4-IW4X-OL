# 341 · **"一个未变的客户端完全不提"** —— `11,048` 次/局 vs 零售**零次**、`352` 个零字节、玻璃的 21/1 位

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 5597–5800 行。

## 二、**字段表的完整顺序**（本组第三重要）

```cpp
std::vector<FieldValue> fields{
    FieldValue{ ClientInfoLivingWeaponField, ... , 11 },      // 0
    FieldValue{ ClientInfoZombieBatteryField, ... , 32 },     // 1
    FieldValue{ ClientInfoModelIndexField, ... , 4 },         // 17
    FieldValue{ ClientInfoFactionField, ..., 1 },             // 18
    FieldValue{ ClientInfoFemaleField, ..., 1 },              // 19
    FieldValue{ ClientInfoCharacterItemField, ..., 16 },      // 20
    record(0), record(1), ..., record(11),                    // 21..32
    attachModel(0), attachModel(1),                           // 34, 35
    FieldValue{ ClientInfoBodyModelField, ..., 10 },          // 40
    attachModel(2), attachModel(3),                           // 44, 45
    attachTag(0), attachTag(1), attachTag(2),                 // 46, 47, 48
    FieldValue{ ClientInfoColorField, ..., 5 },               // 56
    attachTag(3),                                             // 58
};
fields.push_back({36, state.zombieScoreboardTeam, ..., 11});   // 36
for (i < abilities.mask.size()) fields.push_back({2+i, ...});  // 2..7
for (i < abilities.values.size()) fields.push_back({i < 9 ? 8+i : 51+i, ...});  // 8..16, 51..
```

### 2.1 而**六个 abilities mask 在 2..7**

**⇒ 三层**：

```text
1. `abilities.mask` 是**六个 uint32**（§254 的 192 位）
2. ⇒ 字段 **2..7**
3. ⇒ 而 offset 是 **`+0x98..0xAC`**（六个连续 dword）
```

**✅ 与 §254 的"`ps+0x584 + 4*(index>>5)`"**不同的偏移**（`+0x98` vs `+0x584`）。**

**⚠ 所以 clientInfo 的 abilities mask 在 `+0x98` 而 playerState 的技能位集在 `+0x584`。**

**⇒ 两个不同的结构。**

### 2.2 而"**字段 5 曾被误认为僵尸电池计数，它是 ability mask word 3**"

```php
// Correction: field 5 was previously misidentified as a zombie
// battery count; it is ability mask word 3. Do not send currency here.
```

**⇒ 三层**：

```text
1. **字段 5 曾被误认为僵尸电池计数**
2. ⇒ **它是 ability mask word 3**
3. ⇒ **不要在这里发货币**
```

**✅ 与 §307 的"`+0x0A4` battery 读导致崩溃"**相关 —— 那是**同一类误解**。**

### 2.3 而 `abilities.values` 的**两个区间**

```cpp
for (i < abilities.values.size())
    fields.push_back({ i < 9 ? 8 + i : 51 + i, ..., 0 });   // ← 【bits = 0】
```

**⇒ 三层**：

```text
1. 前九个 ⇒ 字段 **8..16**
2. ⇒ 之后的 ⇒ 字段 **51+i**（即 60..86）
3. ⇒ 而 **`bits = 0`** ⇒ **浮点**
```

**✅ 与 §340 的"字段 8..16 与 60..86 是 `+0xB0..0x13C` 的 36 个 float"**完全一致** ✓**

**⇒ 9 + 27 = 36 ✓**

### 2.4 而 `bits == 0` 的分支

```cpp
if (field.bits == 0)
    writeFullFloatDelta(message, bit_cast<float>(field.value), bit_cast<float>(field.baseline));
else
    writeUnsignedDelta(message, field.value, field.baseline, field.bits);
```

**⇒ 三层**：

```text
1. **`bits == 0` 是一个【哨兵】** —— 表示"这是浮点"
2. ⇒ 用 `writeFullFloatDelta`
3. ⇒ 否则用 `writeUnsignedDelta`
```

**✅ 一个**巧妙的重载**（`bits = 0` 作类型标记）。**

**⚠ 而 §313 的 `CharacterSelectionBitWidths` 里**也有两个 0**（索引 8 与 10）。**

**⇒ 那是"零位宽"而这里是"浮点标记"。**

**⚠ 两个不同的 `bits = 0` 语义。**

## 三、**顺序的强制检查**（本组第二重要）

```cpp
// The member is the wire width. Widening either one without the
// other silently truncates a character on the wire, which renders
// the WRONG PLAYER rather than failing.
static_assert(sizeof(SvCharacterCustomization::characterItemId) * 8 ==
    ClientInfoCharacterItemBitCount);
// AND THE ORDER IS ENFORCED, not just asserted in a comment. A pair added
// out of place gap-encodes a negative skip and desyncs every clientInfo
// after it in the same message -- the whole section, not one field.
for (std::size_t index = 1; index < fields.size(); ++index)
{
    if (fields[index - 1].fieldIndex >= fields[index].fieldIndex)
        return;
}
```

### 3.1 而**两个守卫**

```text
① `static_assert(sizeof(characterItemId) * 8 == 16)`    编译期
② 一个运行期循环检查**严格递增**                          运行期【且失败就 return】
```

### 3.2 而"**顺序被【强制】而不只在注释里断言**"

**✅ 三层**：

```text
1. **一个乱加的配对会 gap-encode 一个【负的跳号】**
2. ⇒ **并失步同一个消息里之后的每一个 clientInfo**
3. ⇒ **整个段，不是一个字段**
```

**✅ 与 §319 的"写序必须递增"**第六次**。**

### 3.3 而 ② 是**运行期而不是编译期**

**⚠ 因为 `fields` 是**运行期构建**的 `std::vector`。**

**⇒ 所以只能运行期检查。**

**✅ 而"失败就 `return`" ⇒ **整个 clientInfo 不写**。**

**⚠ 这可能是一个**静默的失败**（没有日志）。**

**⇒ 与本文件反复的"拒绝要命名"**矛盾**。**

**⚠ 一处可改进点。**

### 3.4 而 `static_assert` 的**单位**

```cpp
sizeof(characterItemId) * 8 == ClientInfoCharacterItemBitCount
```

**⇒ `sizeof` 是字节 ⇒ × 8 = 位。**

**⇒ 所以 `2 * 8 = 16` ✓**

**✅ "**成员就是线宽度**"** —— 一个精确的断言。**

## 四、**`lastChangedField` 的 `-1` 初值**

```cpp
auto lastChangedField = -1;
for (const auto &field : fields)
    if (field.value != field.baseline)
        lastChangedField = (int32)field.fieldIndex;
if (lastChangedField < 0)
{
    message.MSG_WriteBits(0, 1);
    return;
}
```

**⇒ 三层**：

```text
1. 初值 `-1`
2. ⇒ 遍历找**最后**一个变化的（因为不 break）
3. ⇒ 仍为 -1 ⇒ **一个 0 位并返回**
```

**✅ 与 §331 的 `lastFieldIndex = -1` 同族（第三次）。**

## 五、**"一个未变的客户端完全不提"**（本组最重要的一段）

### 5.1 那段九层

```php
// AN UNCHANGED CLIENT IS NOT MENTIONED AT ALL, WHICH IS WHAT RETAIL DOES
// (section 169). Measured across the retail corpus: the clientInfos
// section is ENTIRELY EMPTY on 66% of dm snapshots, 46% of war and 85% of
// clash, and a live player's modelIndex is asserted once and then silent
// for six thousand snapshots. A real server writes this section ON CHANGE
// ONLY and emits the "mentioned but nothing changed" form ZERO times.
//
// This server used to emit it 11,048 times per match -- every client, every
// snapshot -- and that form is not free. CL_ParseClientInfos calls
// MSG_ReadDeltaFields unconditionally for every mentioned entry
// (0x004717A4 match arm, 0x00471886 new arm), so it does not mean "leave
// this entry alone", it means "REBUILD IT FROM THE BASE". When the base
// lacks that client number the base IS a memset-zero buffer
// (0x00471772/0x00471831), and the rebuild writes 352 zero bytes over a
// player who was fine a frame earlier. Every one of those 11,048 mentions
// was a chance to zero a clientInfo; retail never takes it, and now
// neither do we.
```

### 5.2 十层

```text
1. **一个未变的客户端【完全不提】** —— 那正是零售所做的（§169）
2. ⇒ 跨零售语料测量：**clientInfos 段在 66% 的 dm 快照上完全为空、46% 的 war、85% 的 clash**
3. ⇒ 而**一个活玩家的 `modelIndex` 被断言一次然后静默六千个快照**
4. ⇒ **一个真实服务器【只在变化时】写这个段**而**发出"提到但什么都没变"形式【零次】**
5. ⇒ **这个服务器过去每局发它 11,048 次** —— **每个客户端、每个快照**
6. ⇒ **而那个形式不是免费的**：`CL_ParseClientInfos` 对每一个被提到的条目**无条件调用 `MSG_ReadDeltaFields`**（`0x004717A4` match 分支、`0x00471886` new 分支）
7. ⇒ **所以它不是"别动这个条目"，它是"【从基线重建它】"**
8. ⇒ **当基线缺少那个客户端号时基线就是 `memset` 零缓冲区**（`0x00471772`/`0x00471831`）
9. ⇒ **而重建把 352 个零字节写到一个一帧前还好的玩家身上**
10. ⇒ **那 11,048 次提到每一个都是一次清零一个 clientInfo 的机会；零售从不取它，现在我也不取**
```

### 5.3 **`352` 个零字节**

**⇒ `352 = 0x160`。**

**✅ 与 §255 的"`clientState` stride `0x160`"**完全一致** ✓**

**⇒ **第二次确认 `0x160`。** —— 而这里是 `clientInfo` 的尺寸。**

**⚠ 而 §339 说 `clientState_s` 是 **`0x58` 字节**。**

**⇒ 所以三个尺寸：**

```text
0x58 = 88     clientState_s（§338/§339）
0x160 = 352   clientInfo（这里）
```

**✅ 两个不同的结构。**

### 5.4 而**"它不是『别动这个条目』，它是『从基线重建它』"**

**✅ 一个**极关键的语义纠正**。**

**⇒ 与 §334 的"伪造一个更晚的上界"、§340 的"定向的负面"同族**（第三十七次）。**

### 5.5 而**三个百分比**

```text
66% 的 dm 快照  ⇒ clientInfos 段完全为空
46% 的 war
85% 的 clash
```

**⚠ 而 clash 的 85% 最高而 dm 的 66% 最低。**

**⇒ 可能因为 dm 的玩家更活跃。**

**✓ 合理。**

### 5.6 而"**六千个快照静默**"

**⇒ 三层**：

```text
1. 一个活玩家的 `modelIndex` 被断言**一次**
2. ⇒ 然后**静默六千个快照**
3. ⇒ 所以**只在变化时写**
```

**✅ 一个**极强的实测**。**

## 六、**"跳过必须在 `writeClientNumber` 之前"**

```php
// THE SKIP HAS TO HAPPEN BEFORE writeClientNumber, not after it: the
// number carries the "another entry follows" bit, so mentioning a client
// and then writing nothing for it leaves the reader one bit out of phase
// and desynchronises every entry after it in the section.
const auto *const entryBaseline = baselineNum == currentNum
    ? &(*baseline)[baselineIndex] : nullptr;
if (entryBaseline && *entryBaseline == clientInfos[currentIndex])
{
    ++currentIndex;
    ++baselineIndex;
    continue;                              // ← 【在 writeClientNumber 之前】
}

writeClientNumber(message, clientNum, lastClientNum);
```

### 6.1 四层

```text
1. **跳过必须在 `writeClientNumber` 之前**
2. ⇒ 因为**编号携带"另一个条目跟随"位**
3. ⇒ 所以**提到一个客户端而什么都不为它写会让读者差一位**
4. ⇒ **并失步这个段里之后的每一个条目**
```

**✅ 与 §337 的"写 3 而客户端读 11 会让之后每个客户端解码垃圾"**同族**（第三十八次）。**

### 6.2 而**"在整个记录上比较"**

```php
// Compared on the WHOLE record, not on the wire fields: SvClientInfoState
// is equality-comparable, so a member that is not yet on the wire can only
// make this conservative -- it sends when it need not have, never the
// reverse.
```

**⇒ 四层**：

```text
1. **在整个记录上比较，不在线字段上**
2. ⇒ `SvClientInfoState` 是**可相等比较的**
3. ⇒ 所以**一个尚未上线的成员只能让这个保守**
4. ⇒ **它在不必发时发，绝不反过来**
```

**✅ 一个**代价不对称的正确选择**（第九次）。**

## 七、`validGlassPiece` 的**四项**

```cpp
bool validGlassPiece(const SvGlassPieceStateRecord &piece)
{
    const auto state = (uint8)piece.state;
    return piece.pieceIndex < SvGlassPieceCount &&
        state <= (uint8)SvGlassPieceState::Deleted &&
        piece.state != SvGlassPieceState::Pristine &&
        (!piece.impact ||
            (piece.state == SvGlassPieceState::Destroyed &&
                piece.impact->positionX <= 0x3F &&
                piece.impact->positionY <= 0x3F));
}
```

### 7.1 四项

```text
① pieceIndex < SvGlassPieceCount（1024）
② state <= Deleted
③ state != Pristine            【不收 Pristine】
④ 若有 impact ⇒ 必须是 Destroyed 且两个坐标 <= 0x3F（6 位）
```

### 7.2 而 **③ "不收 Pristine"**

**⇒ 三层**：

```text
1. `Pristine` = **未破碎**
2. ⇒ 而**未破碎的片不该出现在这个列表里**
3. ⇒ 所以拒绝
```

**✅ 与 §319 的"零断言即不发"同族（第七次"默认值不进线"）。**

### 7.3 而 `positionX/Y <= 0x3F`

**⇒ 6 位坐标。**

**✅ 与 §258 的"`SvGlassPieceCount = 1024`"配合。**

## 八、`glassImpactBitCount` 的**三值**

```cpp
uint32 glassImpactBitCount(const SvGlassPieceStateRecord &piece)
{
    if (piece.state != Destroyed) return 0;
    return piece.impact ? 21 : 1;
}
```

**⇒ 三层**：

```text
非 Destroyed ⇒ 0 位
Destroyed 且无 impact ⇒ 1 位
Destroyed 且有 impact ⇒ 21 位
```

**⚠ 而 `1` 位是**一个"无 impact"标志**。**

**⇒ 所以"没有 impact"用一个位表达。**

**✅ 与 §341 的"`bits = 0` 是浮点标记"**不同的 `0` 语义**（这里是"字段不出现"）。**

## 九、`glassPieceAt` 的**默认构造**

```cpp
return piece != pieces.end() && piece->pieceIndex == pieceIndex
    ? *piece
    : SvGlassPieceStateRecord{ .pieceIndex = (uint16)pieceIndex };
```

**⇒ 三层**：

```text
1. 找到 ⇒ 返回
2. ⇒ 否则返回**只有 pieceIndex 的默认构造**
3. ⇒ 所以"没有这条记录"= 一个默认状态的记录
```

**✅ 与 §323 的"零值最便宜"配合 —— 默认状态会编码为最少位。**

## 十、关键结论

1. **字段表含 `abilities.mask` 的六个（字段 2..7 在 `+0x98..0xAC`）**，而 playerState 的技能位集在 `+0x584` —— **两个不同结构**。
2. **"字段 5 曾被误认为僵尸电池计数，它是 ability mask word 3"**。
3. **`abilities.values` 的 36 个浮点分两个区间**（8..16 与 60..86）。
4. **`bits == 0` 是"浮点"的哨兵**。
5. **两个守卫**：`static_assert`（编译期）+ 一个运行期严格递增检查。
6. **"顺序被强制而不只在注释里断言"**，而**失败就静默 `return`**（一处可改进点）。
7. **`static_assert` 的"成员就是线宽度"**。
8. **⭐ "一个未变的客户端完全不提"** —— **11,048 次/局 vs 零售零次**。
9. **`clientInfos` 段在 66% dm / 46% war / 85% clash 快照上完全为空**。
10. **"一个活玩家的 `modelIndex` 被断言一次然后静默六千个快照"**。
11. **"它不是『别动这个条目』，它是『从基线重建它』"** —— 一个极关键的语义纠正。
12. **`352` 个零字节**（`0x160`）—— 第二次确认 `0x160`，而 `clientState_s` 是 `0x58`。
13. **"跳过必须在 `writeClientNumber` 之前"**（因为编号携带"另一个条目跟随"位）。
14. **"在整个记录上比较"的保守选择** —— 代价不对称的正确选择（第九次）。
15. **`validGlassPiece` 四项，不收 `Pristine`**。
16. **`glassImpactBitCount` 的三值（0/1/21）**。

## 十一、未闭合点

- `abilities.mask` 的 `+0x98` 与 `+0x584` 两个位置的关系。
- 运行期顺序检查失败时是否应记日志。
- `SvGlassPieceCount` 的确切值（1024）。
- `sv_snapshot_mp.cpp` 5800 行之后未读取（27,016 行，进度 21%）。
