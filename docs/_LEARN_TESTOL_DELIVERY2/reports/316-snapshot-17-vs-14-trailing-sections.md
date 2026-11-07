# 316 · **17 vs 14 尾部段**、**9 vs 6 目标字段**、`0x20` 的均匀数据位移与"逐函数重找"的代码

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 600–800 行。

## 二、`SV_PackCharacterCustomization` 的**三层游标**（本组第二重要）

### 2.1 那段

```php
// The storage cursor advances through the recovered clientInfo
// descriptor entries themselves; it deliberately has no second
// hard-coded 10/6-bit chunk layout.
std::array<std::uint16_t, 8> chunks{};
std::size_t storageFieldIndex{};
std::uint8_t storageFieldBit{};
std::size_t payloadBitCount{};
const auto appendBit = [&](bool value) {
    if (storageFieldIndex >= ClientInfoCustomizationStorageFields.size()) return false;
    if (value) chunks[storageFieldIndex] |= (uint16_t)(1u << storageFieldBit);
    ++payloadBitCount;
    ++storageFieldBit;
    if (storageFieldBit == ClientInfoCustomizationStorageFields[storageFieldIndex].bitCount)
    {
        ++storageFieldIndex;
        storageFieldBit = 0;
    }
    return true;
};
```

### 2.2 三层

```text
① 位写入当前 storage field（按 bitCount 推进）
② 满则进下一个 field
③ payloadBitCount 独立计数
```

### 2.3 而"**它刻意没有第二个硬编码的 10/6 位块布局**"

**⇒ 三层**：

```text
1. 游标**穿过恢复的 clientInfo 描述符条目本身**
2. ⇒ **刻意没有第二个硬编码的 10/6 位块布局**
3. ⇒ 所以只有一个真源（`ClientInfoCustomizationStorageFields`）
```

**✅ 一个**正确的单一真源**设计。**

**⇒ 与 §310 的"`netfields 21..32` = 12 = `optionMask[12]`"不同 —— 这里是**8 个字段 76 位**。**

**⚠ 而两个布局**并存**（`72` 载荷 vs `76` 存储）。**

### 2.4 而 `chunks` 是 **8 个 uint16 = 16 字节 = 128 位**

**⇒ 而存储需要 76 位 ⇒ 所以 52 位是**padding**。**

**✅ 与 §315 的"每一个未消耗的存储位保持为零填充"一致。**

### 2.5 而编码循环

```php
for (index = 0; index < selectionIds.size(); ++index)
{
    const auto selection = selectionIds[index];
    const auto width = CharacterSelectionBitWidths[index];
    if (!selection)
    {
        if (!appendBit(false)) return {};      // ← 【缺席 ⇒ 一个 0 位】
        continue;
    }
    if (!width || selection > (1u << width) || !appendBit(true)) return {};
    const auto encoded = (uint32)(selection - 1);      // ← 【-1】
    for (bit = 0; bit < width; ++bit)
        if (!appendBit((encoded & (1u << bit)) != 0)) return {};
}
return payloadBitCount <= CharacterSelectionMaximumPayloadBitCount(72) ? chunks : {};
```

### 2.6 四层

```text
① 缺席 ⇒ 一个 0 存在位
② 存在 ⇒ 一个 1 存在位 + width 个值位
③ 值编码为 `selection - 1`
④ 总位 <= 72
```

**✅ 与 §315 的"解码为 `bits + 1`"**完全互逆** ✓**

### 2.7 而"**当 `!width`（零位宽）⇒ 拒绝**"

**⚠ 所以零位宽的两项（索引 8 与 10）在**存在时**被拒绝。**

**⇒ 因为它们的存在位为 1 但没有值位 ⇒ 那是一个**无法解码的状态**。**

**✓ 正确。**

## 三、**`17 vs 14` 尾部段**（本组最重要的一段）

### 3.1 那段六层

```php
// CODOL MSG_ReadDeltaPlayerstate reads stats, ammo clips, held weapons,
// and ammo pools first, then a run of independent auxiliary presence
// bits before the objective table.
//
// CODDIFF(1649370): 3.3.3.3 has FOURTEEN trailing sections with
// objectives at 8 and hudElems at 9; OLfinal has SEVENTEEN, with
// objectives at 11 and hudElems at 12, so the run before the objective
// table is seven bits rather than four. 3.3.3.3's shape is written down
// in CODOL-main re/demo-re/02-snapshot-wire-spec.md sec 5 ("The 14
// trailing sections", T9 objectives, T10 HUD elems) and this build's in
// Tools/demo-re/codol_snapshot.py's ps_trailing, transcribed from
// MSG_ReadDeltaPlayerstate's disassembly and validated on 6160/6160 real
// retail OLfinal snapshots (T12 objectives, T13 hudElems).
```

### 3.2 七层

```text
1. `MSG_ReadDeltaPlayerstate` 读 **stats、ammo clips、held weapons、ammo pools** 先
2. ⇒ 然后**一串独立的存在位**在目标表之前
3. ⇒ **3.3.3.3 有【十四个】尾部段，objectives 在 8、hudElems 在 9**
4. ⇒ **OLfinal 有【十七个】，objectives 在 11、hudElems 在 12**
5. ⇒ 所以**目标表之前的那一串是七位而不是四位**
6. ⇒ 3.3.3.3 的形状写在 `CODOL-main re/demo-re/02-snapshot-wire-spec.md` 第 5 节
7. ⇒ 而本 build 的写在 `Tools/demo-re/codol_snapshot.py` 的 `ps_trailing`
8. ⇒ **从 `MSG_ReadDeltaPlayerstate` 的反汇编转写，并在 6160/6160 个真实零售 OLfinal 快照上验证**
```

### 3.3 而**五个数字的对照**

```text
              3.3.3.3        OLfinal
总段数         14             17
objectives     8              11
hudElems       9              12
目标表前        4 位           7 位
```

**⇒ 而 `11 - 4 = 7` 与 `12 - 5 = 7` ⇒ 所以"七位"是一致的。**

**⚠ 而从 8→11 是 +3 而 9→12 是 +3 ⇒ 一致的 +3 位移。**

**✅ 所以 `14 → 17` 是 +3 而所有索引 +3。**

### 3.4 而"**每一个段都由恰好一位引入**"

```php
// Every section is introduced by exactly one bit, so three missing bits move
// everything after the ammo pools -- including the entity list -- out of phase.
```

### 3.5 三层

```text
1. **每一个段由恰好一位引入**
2. ⇒ **所以三个缺失的位移动 ammo pools 之后的一切**
3. ⇒ **包括实体列表** ⇒ **失相位**
```

**✅ 与 §292 的"`first > count` ⇒ 整局起不来"、§295 的"三个零向量 ⇒ 全部 trace 在原点"同族**（第十四次"一个位宽错位毁掉整个消息"）。

### 3.6 而 `sub_671E60` vs `sub_671D80`

```php
// OLMOD(section-84): that function is `sub_671E60` in OL.exe and
// **`sub_671D80` in out.exe** -- same body, 98.6% byte-identical, and the
// residue is the moved data operands.
```

**⇒ 三层**：

```text
1. `sub_671E60`（OL.exe）与 `sub_671D80`（out.exe）
2. ⇒ **同一个体，98.6% 逐字节相同**
3. ⇒ 而残差是**移动的数据操作数**
```

**✅ 与 §266 的"`0x00661C50` 与 3.3.3.3 的 `0x005851F0` 逐指令相同，只差一个操作数"同族**（第十四次"同体不同操作数"）。

### 3.7 而"**所以它们不可互换**"

```php
// See the note above ObjectiveFieldCount for why the two are not interchangeable.
```

**⇒ 三层**：

```text
1. 98.6% 相同
2. ⇒ 但**不可互换**
3. ⇒ 因为**残差是数据操作数**而那是**语义**
```

**⚠ 一个重要的警告。**

## 四、**`0x20` 的均匀数据位移与"逐函数重找"的代码**（本组第三重要）

### 4.1 那段

```php
// OLMOD(section-84): THE ADDRESSES IN re/demo-re/netfields-ol/ ARE OL.exe's,
// build 1608541 -- `dump-ol-netfields.py` says so on its first line and the
// filenames kept it. OL.exe is the same game as the host and is REFERENCE
// ONLY. Both facts were measured, and they do not behave the same way:
//
//   DATA   every one of the 25 tables is 0x20 LOWER on out.exe, uniformly,
//          and the 19,656-byte netfield region is BYTE-IDENTICAL between the
//          two builds at that shift. The first byte that differs is the eType
//          dispatch, which holds POINTERS to what moved.
//   CODE   NOT uniform. sub_671E60 -> sub_671D80 is -0xE0 and sub_678390 ->
//          sub_6782A0 is -0xF0, so a .text address has to be re-found per
//          function. Tools/demo-re/verify-netfield-addresses.py re-checks the
//          data half on every run.
//
// So a transcription made from OL.exe describes THIS build's wire exactly --
// that is what makes the 2021-08-30 demos usable -- while the addresses in it
// describe the other binary.
```

### 4.2 八层

```text
1. `re/demo-re/netfields-ol/` 的地址是 **OL.exe（build 1608541）**的
2. ⇒ **OL.exe 是与宿主（out.exe）同一个游戏，而【只作参照】**
3. ⇒ **两个事实都是测量的，而它们行为不同**：
4. **数据**：25 张表在 out.exe 上**均匀低 `0x20`**，而**19,656 字节的 netfield 区域在两个 build 之间在该位移上【逐字节相同】**
5. ⇒ **第一个不同的字节是 eType 分派，它持有指向移动了的东西的指针**
6. **代码**：**不均匀** —— `sub_671E60 → sub_671D80` 是 **-0xE0**，`sub_678390 → sub_6782A0` 是 **-0xF0**
7. ⇒ **所以一个 `.text` 地址必须逐函数重找**
8. ⇒ `verify-netfield-addresses.py` 每次都重新检查数据那一半
```

### 4.3 **"数据均匀 -0x20 而代码不均匀"**

**✅ 这是本文件里**最精密的一段位移分析**。**

**⇒ 而结论是**分层的**：**

```text
数据       -0x20 均匀 ⇒ 19,656 字节逐字节相同
代码       逐函数（-0xE0 / -0xF0）⇒ 必须重找
```

**✅ 与 §245 的"三种 trace 三种 ABI"同族（第十五次"不能假设同构"）。**

### 4.4 而"**从 OL.exe 做的转写精确描述【本 build】的线**"

**⇒ 三层**：

```text
1. 从 OL.exe 做的转写**精确描述本 build 的线**
2. ⇒ **那正是为什么 2021-08-30 的 demo 可用**
3. ⇒ 而**其中的地址描述另一个二进制**
```

**✅ 一个**精确区分"线语义"与"地址"**的论证。**

**⇒ 与 §314 的"单侧是必然的"同族。**

### 4.5 而"**eType 分派持有指向移动了的东西的指针**"

**⇒ 三层**：

```text
1. 数据区在 -0x20 上逐字节相同
2. ⇒ **除了第一个不同的字节：eType 分派**
3. ⇒ 而它**持有指针**
```

**✅ 因为**指针**会随移位变化而**数据**不会。**

**✓ 一个正确的解释。**

## 五、**`9 vs 6` 目标字段**（本组第四重要）

### 5.1 那段七层

```php
// CODDIFF(1649370): THE OBJECTIVE TABLE GAINED THREE FIELDS.
// re/demo-re/netfields-ol/objective-0x00DA90C8.tsv -- 0x00DA90A8 on the host --
// has NINE rows where
// 3.3.3.3's objective-0xC56A78.tsv has six: index 6 = offset 0x24
// codec -97 (a time), index 7 = offset 0x1C four bits, index 8 =
// offset 0x28 codec -57 (a bool). The generic array delta reads its
// lastChanged index with bit_length(fieldCount) bits -- OL.exe's
// sub_6710D0, which is **sub_670FF0 on out.exe** (99.0% byte-identical,
// same 384-byte body), transcribed as array_delta(count, gap) in CODOL-main
// Tools/demo-re/codol_snapshot.py and called there with count 9 and
// gap 1 for this table -- so the width is FOUR on this build and
// THREE on 3.3.3.3.
```

### 5.2 八层

```text
1. **目标表【增加了三个字段】**
2. ⇒ `objective-0x00DA90C8.tsv`（OL.exe）—— 宿主上是 `0x00DA90A8`
3. ⇒ **有【九行】** 而 3.3.3.3 的 `objective-0xC56A78.tsv` 有**六行**
4. ⇒ 三个新增：**index 6 = offset `0x24` codec `-97`（一个时间）**、**index 7 = offset `0x1C` 四位**、**index 8 = offset `0x28` codec `-57`（一个 bool）**
5. ⇒ 通用数组 delta 用 **`bit_length(fieldCount)` 位**读它的 `lastChanged` 索引
6. ⇒ 那是 OL.exe 的 `sub_6710D0`，**out.exe 上是 `sub_670FF0`**（**99.0% 逐字节相同，同样的 384 字节体**）
7. ⇒ 转写为 `array_delta(count, gap)` 而在那里用 **count 9、gap 1** 调用
8. ⇒ **所以宽度在本 build 上是【四】而在 3.3.3.3 上是【三】**
```

### 5.3 而**三个新增字段的编码**

```text
index 6    offset 0x24    codec -97    一个时间
index 7    offset 0x1C    四位          
index 8    offset 0x28    codec -57    一个 bool
```

**⇒ 而 `-97` 与 `-57` 与 §313 的 `AgentStateFieldCodecs` **同一套 codec** ✓**

**⇒ 所以 codec 空间是**跨表共享**的。**

### 5.4 而 `0x24 → 0x2C` 的**步长增长**

```php
// The NATIVE side of the same growth was ported already: the objective
// record's stride is 0x24 on 3.3.3.3 and 0x2C here
// (sv_native_playerstate_mp.cpp ObjectiveStride), which is the same
// eight bytes. Only the wire was left behind.
```

### 5.5 三层

```text
1. **同一个增长的原生那侧已经移植了**
2. ⇒ 目标记录的步长在 3.3.3.3 上是 `0x24` 而这里是 `0x2C`
3. ⇒ **那正是同样的八字节**
4. ⇒ **只有【线】被落下了**
```

### 5.6 **"只有线被落下了"** —— 一个精确的诊断

**⇒ 三层**：

```text
1. 原生侧 `0x24 → 0x2C`（+8）
2. ⇒ 而线侧的宽度 `3 → 4` 位
3. ⇒ 两者是**同一件事的两半**
4. ⇒ 而**只移植了原生那一半**
```

**✅ 与 §299 的"两路索引完全配套"**相反** —— 这里**只配了一半**。**

### 5.7 而那三个 `static_assert` 的**"钉住宽度而不只是界它"**

```php
static_assert(ObjectiveFieldCount < (1u << ObjectiveLastChangedBits));          // 9 < 16
static_assert(ObjectiveFieldCount >= (1u << (ObjectiveLastChangedBits - 1)));   // 9 >= 8
static_assert(ObjectiveProducedFieldCount <= ObjectiveFieldCount);              // 6 <= 9
static_assert(ObjectiveTeamNumField < ObjectiveProducedFieldCount);             // 5 < 6
```

### 5.8 四层

```text
① 9 < 16        （4 位够）
② 9 >= 8        （【3 位不够】）
③ 6 <= 9        （产出的不超过表的）
④ 5 < 6         （team 字段在产出范围内）
```

### 5.9 而**"只界它上界是让三个位在一个九行表上活下来的原因"**

```php
// pin the width to the COUNT rather than merely bounding it: the upper
// assert alone is what let three bits survive a nine-row table.
```

**⇒ 三层**：

```text
1. **把宽度钉到计数**而不只是界它
2. ⇒ **只有上界断言是让三个位在一个九行表上活下来的原因**
3. ⇒ 所以**第二个断言（下界）是修复**
```

**✅ "一个只用上界的断言会放过窄宽度"** —— 一个精确的 `static_assert` 写法教训。

**⇒ 与 §313 的 `CharacterSelectionMaximumPayloadBitCount == 72`（精确相等）**不同。**

## 六、`ObjectiveFieldCount = 9` 而 **`PlayerStateObjectiveAuxiliarySection = 11`**

```cpp
constexpr std::uint32_t ObjectiveFieldCount = 9;
constexpr std::uint32_t ObjectiveLastChangedBits = 4;
constexpr std::uint32_t ObjectiveStateBits = 3;
constexpr std::uint32_t ObjectiveOriginXField = 0;
constexpr std::uint32_t ObjectiveOriginYField = 1;
constexpr std::uint32_t ObjectiveOriginZField = 2;
constexpr std::uint32_t ObjectiveIconField = 3;
constexpr std::uint32_t ObjectiveEntityNumField = 4;
constexpr std::uint32_t ObjectiveTeamNumField = 5;
constexpr std::uint32_t ObjectiveProducedFieldCount = 6;
```

### 6.1 六个产出字段

```text
0  originX
1  originY
2  originZ
3  icon
4  entityNum
5  teamNum
```

**⇒ 六项，与 3.3.3.3 的六行**一一对应** ✓**

### 6.2 而三个新字段（6/7/8）**从不写**

```php
// This server produces the six fields dest1yo's produces. 6..8 are
// never changed, so they are never indexed and never written, and that
// is legal. The WIDTH is not optional: it is written on every objective
// that carries any change at all, and three bits where the client reads
// four puts everything after it -- the hudElem arrays, the entity list,
// the whole rest of the message -- out of phase.
```

### 6.3 四层

```text
1. **本服务器产出 3.3.3.3 产出的那六个字段**
2. ⇒ **6..8 从不改变 ⇒ 从不被索引也从不被写 ⇒ 而那是合法的**
3. ⇒ **但【宽度】不是可选的**：它写在**每一个携带任何变化的目标上**
4. ⇒ **而客户端读四位时三位会把之后的一切 —— hudElem 数组、实体列表、消息的其余全部 —— 弄失相位**
```

**✅ 一个**关键的区别**：数据可以少写而宽度不可少。**

**⇒ 与 §316 的"三个缺失的位移动一切"**完全同族。**

## 七、`HudElemFieldCount = 42` 与**九个基础字段 + 十一个扩展**

```cpp
constexpr std::uint32_t HudElemFieldCount = 42;
constexpr std::uint32_t HudElemLastChangedBits = 6;        // 42 < 64 ✓
constexpr std::uint32_t HudElemFieldSkipBits = 3;
constexpr std::uint32_t HudElemColorField = 0;
constexpr std::uint32_t HudElemYField = 1;
constexpr std::uint32_t HudElemXField = 2;
constexpr std::uint32_t HudElemTypeField = 3;
constexpr std::uint32_t HudElemMaterialField = 4;
constexpr std::uint32_t HudElemHeightField = 5;
constexpr std::uint32_t HudElemWidthField = 6;
constexpr std::uint32_t HudElemTargetEntField = 7;
constexpr std::uint32_t HudElemZField = 8;
constexpr std::uint32_t HudElemValueField = 9;
constexpr std::uint32_t HudElemFadeStartField = 10;
constexpr std::uint32_t HudElemAlignScreenField = 11;
constexpr std::uint32_t HudElemFromColorField = 12;
constexpr std::uint32_t HudElemFadeTimeField = 13;
constexpr std::uint32_t HudElemAlignOrgField = 15;
constexpr std::uint32_t HudElemFontScaleField = 16;
constexpr std::uint32_t HudElemScaleStartField = 17;
constexpr std::uint32_t HudElemScaleTimeField = 18;
constexpr std::uint32_t HudElemFromFontScaleField = 19;
constexpr std::uint32_t HudElemFontField = 20;
constexpr std::uint32_t HudElemSortField = 21;
```

### 7.1 而**字段 14 缺失**

**⚠ 从 0..21 里**没有 14**。**

**⇒ 所以 14 是**未命名的**。**

### 7.2 而**那张表的三元组**

```php
// CODREF: the client's HudElem descriptor table at 0x012F6AC0, stride
// 12 as {u32 offset, s32 bits, u32 changeHint} - the same table his
// CodolHudElemState.py reads at RVA 0x856AC0. Row 11 is
// {0x2C, 8} and row 15 is {0x28, 4}, matching the alignScreen /
// alignOrg loads in sub_BB4780. Every field index already written here
// agrees with that table, including flags {0xA4, 18} at row 14.
```

### 7.3 五层

```text
1. 客户端的 HudElem 描述符表在 **`0x012F6AC0`**，步长 **12**，布局 `{u32 offset, s32 bits, u32 changeHint}`
2. ⇒ 与 `CodolHudElemState.py` 在 **RVA `0x856AC0`** 读的同一张表
3. ⇒ **第 11 行是 `{0x2C, 8}`** 而**第 15 行是 `{0x28, 4}`**
4. ⇒ 与 `sub_BB4780` 里的 `alignScreen`/`alignOrg` 加载匹配
5. ⇒ **这里已写的每一个字段索引都与那张表同意**，包括**第 14 行的 flags `{0xA4, 18}`**
```

### 7.4 而 `0x012F6AC0` 与 `0x856AC0`

**⇒ `0x012F6AC0 - 0x856AC0 = 0xA9FF ...`**

**⇒ 让我算：`0x12F6AC0 - 0x856AC0 = 0xA9C000`。**

**⚠ 而 `0xA9C000` 与 `0x400000` 不同。**

**⇒ 所以这张表在**另一个模块**里（不是 out.exe 的 `0x400000` 基址）。**

**⇒ 可能是一个 DLL。**

**✅ 一个跨模块的地址。**

### 7.5 而 `HudElemFieldCount = 42` 与 `LastChangedBits = 6`

**⇒ 42 < 64 ⇒ 6 位够。**

**✅ 而按 §5.9 的教训，应该也钉下界：`42 >= 32`。**

**⚠ 而这里**只有上界** —— 所以如果 `FieldCount` 降到 32 以下，6 位仍然"合法"而实际过宽。**

**⇒ 与 §5.9 的教训**未应用到 hudElem**。**

## 八、关键结论

1. **`appendBit` 穿过描述符条目本身** —— 刻意没有第二个硬编码布局。
2. **`chunks` 8 个 uint16 = 128 位而存储只需 76 位** ⇒ 52 位 padding。
3. **编码是 `-1` 而解码是 `+1`** —— 完全互逆。
4. **零位宽的两项在存在时被拒绝** —— 因为存在但无值位是无法解码的状态。
5. **⭐ `17 vs 14` 尾部段**：`objectives 11 vs 8`、`hudElems 12 vs 9` ⇒ 目标表前**七位 vs 四位**。
6. **"每一个段由恰好一位引入 ⇒ 三个缺失的位移动之后的一切（含实体列表）失相位"**。
7. **`sub_671E60` vs `sub_671D80`：98.6% 逐字节相同而残差是移动的数据操作数** ⇒ **不可互换**。
8. **⭐ 数据均匀 `-0x20` 而代码不均匀（`-0xE0` / `-0xF0`）** —— 必须逐函数重找。
9. **"19,656 字节的 netfield 区域在位移上逐字节相同"**，唯一不同的是 eType 分派（它持有指针）。
10. **"从 OL.exe 做的转写精确描述本 build 的线，而其中的地址描述另一个二进制"**。
11. **⭐ `9 vs 6` 目标字段**：三个新增（`0x24` 时间 / `0x1C` 四位 / `0x28` bool）。
12. **宽度 `4` vs `3`** —— 由 `bit_length(fieldCount)` 决定。
13. **原生侧 `0x24 → 0x2C`（+8）已移植而"只有线被落下了"**。
14. **"6..8 从不写是合法的，但宽度不是可选的"**。
15. **`static_assert` 必须钉下界** —— "只有上界断言是让三个位在一个九行表上活下来的原因"。
16. **HudElem 表在 `0x012F6AC0`（另一个模块），步长 12，`{offset, bits, changeHint}`**。
17. **字段 14 未命名**（而表第 14 行是 flags `{0xA4, 18}`）。
18. **⚠ `HudElemFieldCount = 42` 只有上界** ⇒ §5.9 的教训未应用到 hudElem。

## 九、未闭合点

- `HudElem` 字段 14 的语义（表说 flags）。
- `0x012F6AC0` 在哪个模块。
- 三个新增目标字段（6/7/8）的实际用途。
- `sv_snapshot_mp.cpp` 800 行之后未读取（1.47 MB）。
