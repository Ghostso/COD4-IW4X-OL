# 188 · `resolveCharacterModelNames` 的失败、`ProfileLayout` 的按名解析、诊断函数的自我克制

## 一、范围

本报告学习 `EngineBindings.hpp` 1634–1893 行。

## 二、`characterOptionSelectionMask` 的完整签名

```cpp
bool characterOptionSelectionMask(
    std::uint16_t characterItemId,
    std::span<const std::uint16_t> equippedItemIds,
    std::array<std::uint32_t, 12> &mask,
    std::string *witness = nullptr) const;
```

`witness` 是**可选的一行说明**——当装备的 id 不在选项列表里时，位清零，而 `witness` 可以说明"为什么这一位没设"。**这是把"静默的默认行为"变成可观测的**。

## 三、`NativeServerCharacterInfoSlot` 的关键事实

```cpp
struct NativeServerCharacterInfoSlot {
    static constexpr std::size_t Size = SvNativeCharacterInfoSize;   // 0x450
    std::array<std::uint16_t, 11> selectionIds{};
    std::uint32_t worldModelContext{};
    std::uint8_t spawnGeneration{};
    bool lerpFramesInitialized{};
};
```

注释开头的加粗：

> **characterInfo_t 的【字节不在这里】。**

理由（反汇编）：

```text
CODOL 的 locomotion anim-script state setter sub_AA94C0（VA 0x004094C0），
由 PM_Footsteps 0x0041A680 从 PmoveSingle 内调用，【不接受 characterInfo 参数】——
它自己推导出来：
    dword_7EB7B80 + 618016 + 952 * playerState[+0x144]
```

结论：

> **所以整个 per-client 数组必须坐在本项目安装的 anim-condition 块【里面】。只有 ol-mod 的记账留在这个结构里。**

**这是一个"名字骗人"的典型**：结构叫 `NativeServerCharacterInfoSlot` 且 `Size` 是 `0x450`，但**它不持有 characterInfo 字节**，`Size` 只是记录"引擎认为那一块有多大"。

而 `952` 与 `0x3B8` 是同一个数——**3.3.3.3 的 characterInfo 尺寸**，出现在这条 3.3.3.3 的地址族反汇编里（`sub_AA94C0` 的 VA 是 0x004094C0，与 §184 里那条相同）。

## 四、`resolveCharacterModelNames`：唯一必须换函数而不是换地址的绑定

```cpp
// CODDIFF(character_customization): OLfinal replaced 3.3.3.3's
// selector/slot-base/name-table model resolution with an item-driven
// scheme, so this is the one binding in the port that must call a
// DIFFERENT function rather than the same one at another address.
// Currently returns false on 1649370 -- see the definition.
```

**"这个移植里唯一一个必须调用【不同函数】而不是同一函数在另一个地址的绑定"** —— 这一句把全部其他 CODDIFF 的性质都界定了。

### 4.1 `filledRecord` 参数的理由

```cpp
// `filledRecord`, when given, receives the TWELVE decoded ids sub_619AD0 left in
// the record -- the engine's own answer, not this side's view of it. Section 67's
// first live run produced two names from the wrong family and the names could not
// say whether the record was filled wrong or merely NAMED wrong.
```

**"两个名字来自错误的族，而名字本身说不清是记录填错了还是只是【命名】错了"** —— 所以要把**引擎的答案**取出来对照。

这是一个诊断设计原则：**当输出有两层（记录 → 名字），两层都要取**。

## 五、`prepareNativeServerDObjPoses` 的完整签名

```cpp
bool prepareNativeServerDObjPoses(
    span<const SvCollisionEntity> entities,
    uint32_t contentMask,
    NativeExceptionDetails &exceptionDetails) const;
```

**`NativeExceptionDetails` 是输出参数** —— 失败时把完整寄存器上下文交出去，而不是只返回 false。

## 六、`PlayerDObjState` 四态与"闩锁"

```cpp
enum class PlayerDObjState : uint8_t {
    Unknown, Healthy, CustomizationAbsent, DObjAbsent, NoTracelineBones
};
```

`reportPlayerDObjState(entityNum, state, detail)` 与 `releasePlayerDObjReportedState(entityNum, state)`：

```cpp
// Clears the latch ONLY if it still holds `state`, so a condition that
// has cleared stops blinding every later stage that shares the slot.
```

**"只在闩锁仍持该状态时才清"** —— 防止一个已经消失的状态继续屏蔽后来的阶段。

**这是报告节流的一种高级形式**：不是"只报一次"，而是"同一状态只报一次，但状态改变后重新可报"。

## 七、`installServerAnimConditionStorage` 的指针进指针出

```cpp
bool installServerAnimConditionStorage(std::byte *&previousBase) const noexcept;
bool restoreServerAnimConditionStorage(std::byte *previousBase) const noexcept;
```

`previousBase` 是**引用**（install 写出、restore 读入），所以这对函数是一对**保存/恢复**操作。

`noexcept` 说明它们不该抛——因为是安装全局状态，抛了没法收尾。

## 八、`readLoadoutRecord` 与 `readProfileWeaponClasses` 的分工

```cpp
// Fills classes[0] from the client's own loadout record. See LoadoutRecordBuildRva.
bool readLoadoutRecord(LoadoutRequest &request) const;

// ALL FIVE CLASSES, from the profile document rather than the one-class
// record. Fills request.classes and request.classMask for the current
// character's five loadouts; leaves request untouched and returns false if
// the document cannot be read or no class is complete. A class is complete
// only when BOTH weapons resolve, because valid() requires it.
bool readProfileWeaponClasses(LoadoutRequest &request) const;
```

**两个关键设计**：

1. **失败时 `request` 保持不变**（不是部分填充）；
2. **"完整"的定义是两把武器都解析成功**，因为 `valid()` 要求它。

## 九、`ProfileLayout`：19 个字段 + `byName` 标志

```cpp
struct ProfileLayout {
    characterSlotsBase / characterStride / characterCount / slotCount
    weaponClassBase / weaponClassStride / weaponClassCount / classesPerCharacter
    primaryBase / secondaryBase / primaryAttach / secondaryAttach / attachCount
    perksBase / perksCount / perksStride
    optional rewardsBase / rewardsStride
    optional[2] equipmentBase / equipmentDoubleAmmoBase
    bool byName;
};
```

**关键设计**：

- `rewardsBase` 与 `equipmentBase` 是 `optional` —— **允许"这个 def 没有这一项"**；
- `byName` 记录 walk 是否成功。

注释：

> 这里的每一个数字**曾经都是手工测量的本 build 常量**，而**八个里有六个在 3.3.3.3 上不同**。`resolveProfileLayout` 走 def 读它们，**所以 def 变了它们就跟着动，不需要任何人重新测量**。`byName` 说明那次 walk 是否成功；**没成功时字段带着下面 OLfinal 1649370 的常量**，而**调用方已经记录过这件事**。

**"调用方已经记录过"** 是重要细节——失败被记录在发生的地方。

### 9.1 `classesPerCharacter = weaponClassCount / characterCount`

**派生值而不是独立常量** —— 与全书反复出现的"别名不重推"是同一条纪律。

## 十、两条武器解析路径

```cpp
readProfileWeaponRequest(classIndex, secondary, request)   // 从【存储的】profile
readStagedWeaponRequest(slotIndex, request)                // 从 staged 数组（3.3.3.3 才有）
```

前者注释：

> 读 `weaponClasses[classIndex].{primary,secondary}Base` **加上那把武器的六个附件元素**，从**存储的** profile。

**六个附件**与 §185 里 `word 24..30` 的七个字（itemId + 六附件）一致。

## 十一、`aliasedWeaponName`：卖不了但必须存在的武器

```cpp
// A weapon name for an id no marketplace item names -- see the alias file. This
// is how a weapon that cannot be sold (raygun_mp, thundergun_chicken_mp, both
// loaded in every MP match) reaches a loadout.
```

**两个具体例子**：`raygun_mp`、`thundergun_chicken_mp` —— **它们在每场 MP 比赛里都被加载，但商城里没有任何物品命名它们**。

## 十二、`characterItemRecordEntry`：0 与 1..11 的分工

```cpp
// Which entry of the twelve-wide character record this item belongs in:
// 0 for a character, 1..11 for a piece, nothing for anything else.
```

**三种答案**：0（角色本体）、1..11（服装件）、`nullopt`（都不是）。

## 十三、`placeCharacterItemsByRecordEntry`

```cpp
// Turn characterClasses[N].slots -- which the profile packs densely, in equip
// order -- into the twelve-entry character record the engine addresses by slot.
```

**"密集按装备顺序打包" → "引擎按槽位寻址的十二项记录"** —— 这是一次**重排**，不是拷贝。

## 十四、三个 audit 各自的"为什么默认关"

### 14.1 武器表全表审计

```cpp
// readDefaultWeaponAttachments only ever runs for a weapon somebody EQUIPPED, so
// "which guns are broken" was answerable only by a player picking each of 838 in turn.
```

**838 把武器**。

默认关的理由：**"几万条日志行，不是因为它不安全"**。

### 14.2 解锁覆盖

```text
sub_5E3550 被强制为真时，sub_5E3760 化简成：
    一个物品是被拥有的，【除非】它在排除列表里
所以读那个列表就是全部证明，而它是一次纯内存读——没有原生调用，没有桥线程风险。
空列表意味着目录里 21,753 个 id 全部解析为已拥有；非空则精确点名哪些不是。
```

**"化简成……所以读那个列表就是全部证明"** —— 这是把一次调用替换成一次读取的典型。

### 14.3 item id → 名字全扫

```text
目录里 21,740 个物品里只有 905 个在提取出来的商城表里有可解析的名字，
而这个缺口一天之内挡住了三个不同的问题：
    elp/eye 槽的服装件是哪些
    657 把主武器里库存缺了哪些
    日志里的一个 id 到底是什么
客户端能解析它们全部；只是从没被【批量】问过。
```

**"从没被批量问过"** —— 这就是为什么要写这个工具。

## 十五、`ExcludedItemsArrayRva` 的两个地址

```cpp
// sub_5DE440 parses a comma-separated string of item ids into these: the array,
// its length, and its capacity. VA 0xC9113CC / 0xC9113D4 at image base 0x400000.
ExcludedItemsArrayRva = 0x8D113CC
ExcludedItemsCountRva = 0x8D113D4
```

**两个地址差 8 字节**，正好是"指针 + 长度"（或"长度 + 容量"）的一对。

## 十六、关键结论

1. **名字骗人的结构**：`NativeServerCharacterInfoSlot` 不持有 characterInfo 字节，`Size` 只是记录引擎认为多大。
2. **唯一必须换函数的绑定**：`resolveCharacterModelNames`，其余都是换地址。
3. **当输出有两层（记录 → 名字），两层都要取**，否则说不清是哪一层错。
4. **闩锁只在仍持该状态时才清** —— 比"只报一次"更精细。
5. **失败时 `request` 保持不变**，不部分填充。
6. **`ProfileLayout` 里用 `optional` 表达"这个 def 没有这一项"**。
7. **把一次原生调用化简成一次内存读**（解锁覆盖）。
8. **"从没被批量问过"是工具存在的理由**。

## 十七、未闭合点

- `resolveCharacterModelNames` 在 1649370 上**返回 false**（该绑定尚未完成）。
- `EngineBindings.hpp` 1893 行之后未读取。
- `EngineBindings.cpp` 全文未读取。
