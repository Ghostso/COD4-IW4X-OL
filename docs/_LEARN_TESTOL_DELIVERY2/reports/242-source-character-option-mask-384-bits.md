# 242 · 角色选项掩码的 384 位上限、"不是列表里的就没有位"、`__usercall` 探针

## 一、范围

本报告学习 `EngineBindings.cpp` 10038–10320 行。

## 二、`readItemDefinition`：**桶式查找**的四级

```cpp
const auto bucket = itemId / 1000;
const auto lookupIndex = itemId % 1000 + bucketOffsets[bucket];
const auto definitionIndex = lookup[lookupIndex];
definition = definitions + definitionIndex * ItemDefinitionSize;
```

### 2.1 一句概括

```text
bucket    = id / 1000
偏移      = bucketOffsets[bucket]
查找下标  = id % 1000 + 偏移
定义下标  = lookup[查找下标]
定义      = definitions + 定义下标 * ItemDefinitionSize(52)
```

**这是一个"分桶 + 段内取模"的稀疏表** —— 所以 `id % 1000` 不必连续，桶偏移把每个桶的起点隔开。

### 2.2 五处 `readableSpan`

```text
1. 四个全局槽（definitions / definitionCount / lookup / lookupCount）
2. bucketOffsets + bucket*2
3. lookup + lookupIndex
4. definitions + definitionIndex * 52
```

**第 2 步验证了 `bucket` 不越界** —— 与 §239 里 `readIndex` 用 `offsetTable[index]` 验证 index 同族。

### 2.3 `bucket` 无上界检查**是安全的**

```cpp
const auto bucket = itemId / 1000;      // itemId <= 0xFFFF ⇒ bucket <= 65
```

**因为入口已检查 `itemId > 0xFFFF ⇒ nullptr`** ⇒ `bucket` 最多 65。

**而 `readableSpan` 会拒绝 65 号桶之外的范围。**

### 2.4 三次零值拒绝

```text
definitionIndex == 0        ⇒ 空槽
definitionCount == 0        ⇒ 表未初始化
lookupCount == 0            ⇒ 同上
```

**`definitionIndex == 0` 视为空** —— 因为定义 0 是保留的（与 §241 里 `sub_7C5BA0` 的"0 = 空"一致）。

## 三、`characterOptionSelectionMask` 的两步开启

```cpp
const auto *const characterItem = readItemDefinition(characterItemId);
if (!characterItem || characterItem[5] != 2)
    return false;
```

### 3.1 `characterItem[5] != 2` 是**类型字节**

```text
+5 == 2   ⇒ 这是一个"角色"物品
```

**注释说"the item registry gives a definition whose type byte at +5 must be 2, and its u16 at +2 indexes CharacterItemDefinitionTable at stride 52"** ✓

### 3.2 三个不同的表

```text
ItemDefinitions              (定义表, stride 52)
CharacterItemDefinitionTable (角色定义表, stride 52)
```

**两个都是 stride 52** —— 而 **`characterItem+2`（u16）是角色定义表的下标**。

**这是"物品定义的 +2 指向角色定义"** —— 与 §239 里 `CharacterItemDefinitionSize = 52` 一致，但**这是第二个 stride 52 的表**。

### 3.3 两个 52 的混淆风险

**`ItemDefinitionSize` 与 `CharacterItemDefinitionSize` 都可能是 52** —— 若两者恰好相同，**互换它们不会越界但会读错内容**。

**这是本文件第三次记录的"两个数组恰好同宽"**（§239 的 9/12、§241 的 1 个 class vs 5 个）。

## 四、选项表的两个字段

```cpp
const auto optionCount = *(const uint32*)(definition + 36);
const auto *const options = *(uint16*const*)(definition + 40);
```

### 4.1 都在 52 字节内

```text
+36  optionCount  (uint32)  → 36..39
+40  options      (指针)    → 40..43
```

**而 `CharacterItemDefinitionSize = 52`** ⇒ 都在界内 ✓

**注释**："Both live inside the 52-byte definition this file already reads for `female` and the colour selector, so no new stride or table is being guessed here."

**"没有新的 stride 或表在被猜"** —— 这是一个"复用已验证布局"的声明。

### 4.2 选项是 **u16 数组**

```cpp
*reinterpret_cast<std::uint16_t *const *>(definition + 40)
```

**所以每个选项是一个 `uint16`** —— 而物品 id 最大 0xFFFF ✓

## 五、**384 位上限**（本组最重要的一段）

### 5.1 常量

```cpp
constexpr std::uint32_t MaskBitCount = 384;
const auto addressable = std::min<std::uint32_t>(optionCount, MaskBitCount);
```

**12 个 dword = 384 位** —— 而 `mask` 是 `std::array<std::uint32_t, 12>`。

### 5.2 那句"这是边界不是检查"

```text
A BOUND, NOT A CHECK, IF IT WERE SILENT. Twelve dwords address 384 options and no
more; a character with a longer list can still be dressed in anything inside the
first 384, and the witness says so rather than the count being quietly clamped.
The engine reads the same twelve dwords, so this is its limit too, not ours.
```

**三层**：

```text
1. 十二个 dword 只能寻址 384 个选项
2. 更长的列表 ⇒ 仍然可以穿前 384 里的任何东西
3. 【见证文本会说出来】而不是 quietly clamped
```

**"引擎读的是同样那十二个 dword，所以这也是它的上限，不是我们的。"**

**这是一个"限制来自对端格式"的论证** —— 与 §238 里 `slotCount` 取 `min` 同族。

### 5.3 `addressable` 的两用

```cpp
std::uint32_t index = addressable;          // 哨兵
for (candidate = 0; candidate != addressable; ++candidate) ...
if (index == addressable) { ... unmatched ... }
```

**用 `addressable` 本身作"没找到"的哨兵** —— 因为合法的 candidate 一定 `< addressable`。

**这与 §235 里 `INT32_MIN` 作哨兵不同** —— 这里不需要不可能的值，因为**循环上界本身就排除了它**。

## 六、**"不在列表里就不置位"**

```cpp
if (index == addressable)
{
    // NOT IN THE LIST, SO NO BIT. Setting a bit for an id the option list
    // does not hold would select whatever option happens to sit at that
    // index -- which is exactly the failure section 182 measured when the
    // raw item ids were sent as the mask and the client drew pieces
    // unrelated to the loadout.
    unmatched += " " + std::to_string(itemId);
    continue;
}
```

### 6.1 §182 的那次实测

**"把原始物品 id 当掩码发过去，客户端画出了与 loadout 无关的部件"**

**这是把 id 当 **下标** 用** —— 所以 25703 号物品会选中 25703 号选项（而选项只有几十个）⇒ 越界或被截断 ⇒ 随机部件。

### 6.2 所以"位置"是唯一的语义

```text
掩码的一位 = 选项列表里的一个位置
不是"物品 id 的一位"
```

**这是 §240 里"变体索引客户端不共享 ⇒ 拒绝每颗子弹"的同族问题** —— **索引必须来自对方的表**。

## 七、`index / 32` 与 `index % 32`

```cpp
mask[index / 32] |= std::uint32_t{1} << (index % 32);
```

**标准的位图写法** —— 而 `index < addressable <= 384` ⇒ `index/32 <= 11` ⇒ **不越界** ✓

## 八、**"名字能显示的，数字不能"**

```cpp
// NAME IT. sub_80E600 classifies each selected option into one of twelve
// slots by its resolved model NAME, and OVERWRITES -- ascending option
// index, last writer wins. So two pieces whose names classify the same way
// silently collide and the higher index is what the player sees. Numbers
// cannot show that; names can.
```

### 8.1 完整机制

```text
1. sub_80E600 把每个选中选项按【解析后的模型名】分类到十二个槽之一
2. 而且是【覆盖】—— 升序索引，最后写的赢
3. ⇒ 两件名字归类相同的部件【静默碰撞】，玩家看到的是更高的索引
```

### 8.2 为什么这需要名字

**"数字无法显示这一点；名字可以。"**

**因为碰撞发生在"名字归类"层面** —— 两个不同的 id 归到同一类，日志里只有 id 是看不出来的。

### 8.3 "twelve slots" 与 384 位

```text
384 位   可寻址的选项数
12 槽    分类后的最终位置数
```

**两个 12 是不同的 12** —— 一个是 mask 的 dword 数（12 × 32 = 384），一个是 `sub_80E600` 的槽数。

**这是本文件第四次"两个数字恰好相同"**。

## 九、`witness` 的三段

```cpp
*witness = "character option mask character=" + characterItemId +
    " options=" + optionCount +
    (optionCount > 384 ? " (ONLY THE FIRST 384 ARE ADDRESSABLE)" : "") +
    " selected=" + selected +
    " bits=" + (matched.empty() ? " none" : matched) +
    " NOT AN OPTION FOR THIS CHARACTER=" + (unmatched.empty() ? " none" : unmatched);
```

### 9.1 五个量

```text
character   角色物品 id
options     选项总数（可能 > 384）
selected    匹配上的数量
bits        每个：id@index(name)
NOT AN OPTION  每个：id（无 index，因为没匹配）
```

### 9.2 **匹配的带 index，不匹配的只带 id**

**这个不对称是有意的** —— 匹配的 index 是**要核对的**（"这个部件落到了哪个位置"），不匹配的没有 index。

## 十、**"那这个表里到底有什么"**

```cpp
if (!selected)
{
    *witness += " -- THE LIST STARTS";
    for (index = 0; index != std::min(addressable, 16); ++index)
        *witness += " " + std::to_string(options[index]);
    if (addressable > 16) *witness += " ...";
}
```

### 10.1 那句方法论

```text
AND WHEN NOTHING MATCHED, SAY WHAT THE LIST ACTUALLY HOLDS. A line that only
reports "your ids are not in it" costs a whole second cycle to ask the obvious
follow-up; this one answers "then what IS in it" the first time. Section 183g:
ask what the instrument would have printed had something been there.
```

**"一行只报告『你的 id 不在里面』要花掉整个第二轮去问那个显然的后续问题；这一行第一次就回答『那里面到底有什么』。"**

### 10.2 §183g 的那句话

**"ask what the instrument would have printed had something been there"**

**"假设那里有东西，仪器会打印什么"** —— 这是一个**主动设计日志内容**的方法。

**这与 §241 里"SHOW THE BYTES"（转储 record 前 32 字）是同一原则** —— 失败时把输入摆出来。

## 十一、`placeCharacterItemsByRecordEntry` 的 `static_assert`

```cpp
static_assert(CharacterItemCount == SvCharacterRecordEntryCount,
    "the session record and the character record must be the same twelve "
    "entries, or an outfit lands in the wrong slot");
```

### 11.1 两个名字同一个 12

```text
CharacterItemCount         （DedicatedSession）
SvCharacterRecordEntryCount（Sv 侧）
```

**`static_assert` 保证它们相等** —— 而理由写得明确：**"否则一套服装会落到错误的槽里"**。

### 11.2 那个"规则在头文件里"的分层

```cpp
// The placement rule itself lives in sv_snapshot_mp.hpp so it can be tested
// without an engine; this side supplies the one thing only a live process has,
// which is the item table.
```

**"放位规则在 `sv_snapshot_mp.hpp` 里，这样它可以不依赖引擎被测试；这一侧提供只有活进程才有的东西 —— 物品表。"**

**这是一个干净的依赖注入**：

```cpp
SV_PlaceCharacterItemsByRecordEntry(profileSlots, [this](itemId) {
    return characterItemRecordEntry(itemId);
}, record);
```

**回调是唯一的引擎依赖。**

## 十二、`characterItemRecordEntry` 的两个类别

```cpp
switch (flags >> 8)
{
case ItemCategoryCharacter:       return 0u;     // 【无论 recordEntry 说什么】
case ItemCategoryCharacterPiece:
    if (!recordEntry || recordEntry >= CharacterItemCount) return nullopt;
    return recordEntry;
default:                          return nullopt;
}
```

### 12.1 三条

```text
角色         ⇒ 永远是 0
角色部件     ⇒ 自己的 recordEntry，但 0 与越界都拒绝
其它         ⇒ nullopt
```

**"A character IS entry 0, whatever its own recordEntry field says."** —— **忽略自报的字段**。

**"Entry 0 is reserved for the character, so a piece claiming it is a misread rather than a piece; refuse instead of overwriting the character."** —— **一个声称 0 的部件是误读，拒绝而不是覆盖角色。**

### 12.2 那句"沉默是正确答案"

```text
Silence is the right answer for a weapon or an emblem: the caller is placing a
character record and must not guess an entry for an item the engine would never
put in one.
```

**"对一个武器或徽章，沉默是正确答案"** —— 而这是**唯一**一类"沉默是对的"的情形（对比 §225/§234/§235/§239 的"沉默读起来像健康"）。

## 十三、`readItemInternalName` 的两次拒绝

```cpp
const auto internalName = readCString(name, 128);
if (!internalName || !validBookingName(*internalName))
    return std::nullopt;
```

**`validBookingName` 也用在内部名上** —— 因为它**要拼路径**（§237）。

**所以内部名与 map/gametype 名共用同一个合法性谓词** —— 这是一处跨用途复用。

## 十四、`invokeOwnershipResolver` 的两个不寻常

### 14.1 `__try` 必须住在**没有析构函数**的函数里（C2712）

```text
THE __try MUST LIVE SOMEWHERE WITHOUT DESTRUCTORS (C2712), and the register
arguments mean inline asm rather than a function pointer: sub_5E3760 is
__usercall with the item in EAX and the out-record in EDI, which no C++
calling convention expresses.
```

**两个约束**：

```text
1. MSVC C2712：含 __try 的函数不能有需要展开的对象 ⇒ 必须是裸的、无析构的
2. __usercall（EAX + EDI）⇒ 任何 C++ 调用约定都表达不了 ⇒ 只能内联汇编
```

### 14.2 `pushad` / `popad` 包裹

```asm
pushad
mov  eax, itemId
mov  edi, destination
call function
mov  value, eax
popad
```

**`pushad` 保护全部通用寄存器** —— 因为 `__usercall` 可能不改调用约定但会乱动寄存器，而编译器假设内联汇编写了的东西它不管。

**注意 `mov value, eax` 在 `popad` 【之前】** —— 而 `value` 是栈局部变量，`popad` 不会碰它 ✓

### 14.3 那句"错误的 RVA 不返回错答案，它执行那个地址上的任何字节"

```text
Guarded because a wrong RVA here does not return a wrong answer, it executes
whatever bytes are at that address. A fault must be reported as "the probe is
broken", never mistaken for "the item is not owned".
```

**"一个错误的 RVA 在这里不返回错答案，它执行那个地址上的任何字节。一次故障必须报告为『探针坏了』，绝不能被误认为『物品未拥有』。"**

**这是 §235 "沉默读起来像健康"的第四个变体**：**这次用 `__try` 把"探针坏了"与"答案是假"分开。**

## 十五、关键结论

1. **`readItemDefinition` 是"分桶 + 段内取模"**，五处 `readableSpan`，`bucket <= 65` 由入口的 `> 0xFFFF` 保证。
2. **两个 stride 52 的表**（物品定义、角色定义）—— 互换不越界但读错内容。
3. **384 位上限来自"引擎读同样十二个 dword"** —— 不是我们的选择。
4. **`addressable` 自身作哨兵** —— 不需要不可能的值。
5. **"不在列表里就不置位"** —— §182 的实测：把 id 当下标会画出无关部件。
6. **碰撞发生在"名字归类"层面** —— 数字看不出来，名字能。
7. **失败时把列表前 16 项打出来** —— "假设那里有东西，仪器会打印什么"。
8. **`sub_5E3760` 是 `__usercall`（EAX + EDI）** ⇒ 只能内联汇编 + `pushad`。
9. **`__try` 把"探针坏了"与"答案是假"分开** —— 第四次"沉默读起来像健康"的防御。
10. **角色的 entry 永远是 0，忽略自报字段**；声称 0 的部件是误读。

## 十六、未闭合点

- `ItemDefinitionSize` 与 `CharacterItemDefinitionSize` 是否真的都是 52（若是，互换风险无编译期保护）。
- `sub_80E600` 的十二个槽与 mask 的十二个 dword 是两套 12。
- `EngineBindings.cpp` 10320 行之后未读取（本批已续读到 10640）。
