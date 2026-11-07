# 238 · 按名解析 schema、`weaponOrdinal - AttachmentCount` 那段 numerology

## 一、范围

本报告学习 `EngineBindings.cpp` 8698–8897 行。

## 二、那段"两个附件序号从未被测量过"

```cpp
// The eight constants below were each measured by hand off this build's def, and six
// of them are DIFFERENT on 3.3.3.3 (605/14/5 there is 576/10/1; 1607/37 is 1154/36).
// They are kept as the fallback for a def this walker cannot read, and as a
// cross-check the caller logs -- not as the answer. The two attachment ordinals were
// never measured at all: they were derived as `weaponOrdinal - AttachmentCount`,
// arithmetic the source itself called numerology after it landed on the wrong weapon
// once (sections 187g and 187m). The def NAMES them.
```

### 2.1 八个常量与六个不同

```text
本 build    3.3.3.3
605/14/5    576/10/1      （characterClasses 基址/步长/slots 序号）
1607/37     1154/36       （weaponClasses 基址/步长）
```

**四个数字两对** —— 而"六个不同"指的是 605、14、5、1607、37 以及……（第 6 个可能是 `classesPerCharacter` 或其他）。

### 2.2 两个附件序号是**纯算术**

```cpp
.primaryAttach = WeaponClassPrimaryBaseOrdinal - attachmentCount,
.secondaryAttach = WeaponClassSecondaryBaseOrdinal - attachmentCount,
```

**`22 - 6 = 16`、`29 - 6 = 23`** —— 与 §185 里"`primaryAttach` 在 16、`secondaryAttach` 在 23、宽 6"**数值一致**。

**但 `sv_gamestate_mp.hpp` 里的注释说"def 把它们命名出来"** —— 而这里是**推导**。

### 2.3 "numerology"

```text
arithmetic the source itself called numerology after it landed on the wrong weapon
once (sections 187g and 187m)
```

**"源码自己称之为 numerology，在它落错过一次武器之后"**

**所以这两个值曾是【猜的】** —— 而 §185 里明确说"问 def 既更短又按构造正确"。

## 三、`PlayerDataDef::open(def, readableSpan)`

```cpp
const auto schema = PlayerDataDef::open(def, readableSpan);
if (!schema) return layout;
```

### 3.1 `readableSpan` 作为 `Readable`

**`PlayerDataDef::Readable` 是 `std::function<bool(const void*, size_t)>`**（§179）

**而 `readableSpan` 的签名是 `bool(const void*, size_t)`** ✓ —— 所以直接传。

**这是一个干净的接口对接** —— `PlayerDataDef` 不依赖 `EngineBindings` 的任何东西，只依赖一个可读性谓词。

## 四、七条 `resolve` 调用

```cpp
const auto characters      = schema->resolve("characterClasses");
const auto slots           = schema->resolve("characterClasses[0].slots");
const auto weapons         = schema->resolve("weaponClasses");
const auto primary         = schema->resolve("weaponClasses[0].primaryBase");
const auto secondary       = schema->resolve("weaponClasses[0].secondaryBase");
const auto primaryAttach   = schema->resolve("weaponClasses[0].primaryAttach");
const auto secondaryAttach = schema->resolve("weaponClasses[0].secondaryAttach");
```

**七条** —— 与 §185 的 `resolve` 路径语法一致。

### 4.1 任一失败即回退

```cpp
if (!characters || !slots || !weapons || !primary || !secondary ||
    !primaryAttach || !secondaryAttach)
{
    return layout;      // ← 回退到手工常量
}
```

**七个全部成功才继续。**

## 五、那个"序号不能低于基址"的守卫

```cpp
// Every ordinal is measured from the class element's own base, so a class that
// moves as a whole does not move its fields. A field BELOW that base is not an
// ordinal of this struct and means the walk went somewhere unexpected.
if (primary->index < weapons->index || secondary->index < weapons->index ||
    primaryAttach->index < weapons->index ||
    secondaryAttach->index < weapons->index)
{
    return layout;
}
```

**"每一个序号都是从类元素【自己的基址】算起的，所以一个整体移动的类不会移动它的字段。一个【低于】那个基址的字段不是这个结构的序号，而意味着这次 walk 走到了意外的地方。"**

**这是一个"结构合理性"检查** —— 而不只是"值在范围内"。

### 5.1 为什么"整体移动不移动字段"重要

**因为 `primary->index - weapons->index` 是【相对位移】** —— 如果整个结构平移，相对位移不变。

**所以这个算法对"结构整体重定位"是免疫的。**

## 六、`slotCount` 的 `min`

```cpp
// THE ARRAY IS SIZED BY THE WIRE FORMAT, NOT BY THE DEF. profileSlots is
// CharacterProfileSlotCount wide because that is what a LoadoutRequest carries;
// a def declaring more would be a write past the end, so take the smaller.
layout.slotCount = std::min(
    slots->count, static_cast<uint32>(CharacterProfileSlotCount));   // 9
```

**"数组由【线格式】而不是 def 决定大小"**

**`LoadoutRequest.profileSlots` 是 9 宽** —— 所以 def 声明更多会写越界 ⇒ 取小。

**这与 §237 里"`playlistSlot` 是 uint8 而 `SvBookingCommand` 是 uint32"是同一类"线宽 vs 结构宽"问题。**

## 七、`classesPerCharacter` 的除法

```cpp
// weaponClasses is FLAT -- sixty entries that are twelve characters of five
// classes -- and the def does not say where the split is, only how long the whole
// array is. Dividing is the one honest way to get it, and a def whose two arrays
// do not divide evenly is one this partitioning does not describe, so the
// measured five stands rather than a rounded-down guess.
if (characters->count && weapons->count % characters->count == 0)
    layout.classesPerCharacter = weapons->count / characters->count;
```

### 7.1 两个条件

```text
characters->count 非零
weapons->count % characters->count == 0   ← 【必须整除】
```

**"不能整除的 def 就是这个划分不描述的 def，所以测量得到的 5 保持，而不是四舍五入的猜测。"**

**"不取整"** —— 如果除不尽就保留原值。

### 7.2 这与 §185 里"`classesPerCharacter = weaponClassCount / characterCount`"一致

**而 §185 说它是"派生值而不是独立常量"** —— 这里加了整除检查。

## 八、四个序号的减法

```cpp
layout.primaryBase      = primary->index - weapons->index;
layout.secondaryBase    = secondary->index - weapons->index;
layout.primaryAttach    = primaryAttach->index - weapons->index;
layout.secondaryAttach  = secondaryAttach->index - weapons->index;
```

**四个都用同一个表达式** —— `X->index - weapons->index`。

**所以四个都是"相对类基址的序号"** —— 与 §185 里"`primaryBase` 在 16、`secondaryAttach` 在 23"的口径一致。

## 九、`attachCount` 的三取最小

```cpp
layout.attachCount = std::min(
    { primaryAttach->count, secondaryAttach->count, attachmentCount });
```

**三个候选**：

```text
primaryAttach->count     ← def 说的
secondaryAttach->count   ← def 说的
attachmentCount          ← 线格式的（6）
```

**取最小避免越界** —— 与 `slotCount` 同一条纪律。

## 十、`perks` 的四重校验

```cpp
const auto perks = schema->resolve("weaponClasses[0].perks");
if (perks && perks->index >= weapons->index && perks->stride &&
    perks->count <= OlMod::DedicatedSession::PerkSlotCount &&
    perks->index - weapons->index + perks->count * perks->stride <=
        weapons->stride)
{
    layout.perksBase = perks->index - weapons->index;
    layout.perksCount = perks->count;
    layout.perksStride = perks->stride;
}
```

### 10.1 四项

```text
1. index >= weapons->index          （不低于基址）
2. stride 非零
3. count <= PerkSlotCount           （不超线格式）
4. base + count*stride <= weaponClassStride  ← 【必须落在类结构内】
```

**第四项是最强的** —— 它保证整个 perks 数组落在 `weaponClasses` 的一个元素内。

**这是一个"区间包含"检查** —— 与 §184 里 `static_assert(事件表末尾 <= 0xACE70)` 同族。

### 10.2 `perks` 是 `optional` 之外的额外字段

**而 `ProfileLayout::perksBase/perksCount/perksStride` 的默认值是 0** —— 所以不满足条件时保持 0。

## 十一、`rewards` 的同类校验

```cpp
const auto rewards = schema->resolve("weaponClasses[0].killstreaks");
if (rewards && rewards->index >= weapons->index && rewards->stride &&
    rewards->count >= RewardSlotCount &&
    rewards->index - weapons->index + rewards->count * rewards->stride <=
        weapons->stride)
```

### 11.1 一个**不同**的方向

```cpp
rewards->count >= RewardSlotCount      // ← 【>=】不是 <=
```

**perks 要求 `count <= PerkSlotCount`，而 rewards 要求 `count >= RewardSlotCount`。**

**为什么不同**：

```text
perks  ：线格式只有 PerkSlotCount 个槽 ⇒ def 多了会越界 ⇒ <=
rewards：需要至少 RewardSlotCount 个 ⇒ def 少了不够用 ⇒ >=
```

**但没有 `rewards->count <= 某个上限`** —— **这可能是一处不一致**。

### 11.2 `rewardsBase` 存的是**绝对 index**

```cpp
layout.rewardsBase = rewards->index;      // ← 【不减 weapons->index】
layout.rewardsStride = rewards->stride;
```

**而 `perksBase` 存的是相对值**：

```cpp
layout.perksBase = perks->index - weapons->index;
```

**这是一处明确的不一致** —— 两个字段用了两种口径。

**而 `ProfileLayout` 的声明里**：

```cpp
uint32 perksBase{};
uint32 rewardsBase{};        ← 名字没有提示差异
```

**所以调用方必须知道这个差别。**

## 十二、`equipment` 的两个字段

```cpp
constexpr std::array names{ "lethal", "tactical" };
for (slot = 0; slot < names.size(); ++slot)
{
    const auto field = schema->resolve("weaponClasses[0]." + std::string(names[slot]));
    if (field && field->category == PlayerDataDef::CategoryInt &&
        field->index >= weapons->index &&
        field->index - weapons->index < weapons->stride)
        layout.equipmentBase[slot] = field->index - weapons->index;

    const auto count = schema->resolve("weaponClasses[0]." + std::string(names[slot]) + "DoubleAmmo");
    if (count && count->category == PlayerDataDef::CategoryBool &&
        count->index >= weapons->index &&
        count->index - weapons->index < weapons->stride)
        layout.equipmentDoubleAmmoBase[slot] = count->index - weapons->index;
}
```

### 12.1 两个**类型**检查

```text
lethal/tactical         必须是 CategoryInt
...DoubleAmmo           必须是 CategoryBool
```

**这是 §179 里 `Category` 六种的实际使用** —— 而**布尔在 profile 里是"位偏移"不是"字节偏移"**（§179 的注释）。

**所以 `equipmentDoubleAmmoBase` 存的是【位偏移】** —— 而 `equipmentBase` 存的是**字节偏移**。

**两个数组同名但语义不同** —— 这是一处需要指出的隐蔽差异。

### 12.2 `+ "DoubleAmmo"` 的拼接

```cpp
"weaponClasses[0]." + std::string(names[slot]) + "DoubleAmmo"
```

**`"weaponClasses[0].lethalDoubleAmmo"`** —— 与 §211 里 `dbIsXAssetDefault` 的命名风格一致。

## 十三、关键结论

1. **八个常量里六个在 3.3.3.3 上不同**，而两个附件序号是纯算术（numerology）。
2. **`PlayerDataDef::open` 只依赖一个可读性谓词** —— 接口干净。
3. **序号从"类元素自己的基址"算起** ⇒ 对结构整体平移免疫。
4. **`slotCount` 与 `attachCount` 都取 `min`** —— 线格式优先于 def。
5. **`classesPerCharacter` 必须整除**，不整除就保留测量值。
6. **perks 与 rewards 的 `count` 检查方向相反**（`<=` vs `>=`），且 `rewards` **缺上限**。
7. **`perksBase` 是相对值而 `rewardsBase` 是绝对值** —— 同类字段两种口径。
8. **`equipmentBase` 是字节偏移而 `equipmentDoubleAmmoBase` 是位偏移** —— 同名数组语义不同。

## 十四、未闭合点

- `rewards->count` 缺上限检查。
- `rewardsBase` 与 `perksBase` 的口径不一致。
- `EngineBindings.cpp` 8897 行之后未读取。
