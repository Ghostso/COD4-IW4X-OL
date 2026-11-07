# 256 · 两级捕获的 `source=profile` / `record-mirror`、九个槽与十二宽的 `static_assert`、`CharacterRecordToSelectionName` 的十一项映射

## 一、范围

本报告学习 `EngineBindings.cpp` 15437–15850 行。

## 二、`reportProfileCharacterSlots` 的**九个**

```cpp
// NINE, not CharacterItemCount's twelve -- see CharacterProfileSlotCount.
for (std::size_t index = 0; index < CharacterProfileSlotCount; ++index)
{
    const auto value = invokeCharacterSlotGet(characterSlotGet_, *characterIndex, index);
    slots += (index ? "," : "") + (value ? std::to_string(*value) : "x");
    if (value && *value) ++nonZero;
}
```

### 2.1 `"x"` 是"读不出"的表示

**而不是 0** —— 因为 0 是合法的"空槽"。

**与 §235 里 `INT32_MIN` 作哨兵、§242 里 `addressable` 作哨兵同族。**

### 2.2 那段"两个来源"的问题

```cpp
// The question this exists to answer: the roster's twelve item handles and the
// profile's characterClasses[<character>].slots[0..11] are two sources for what
// might be the same twelve ids. If they agree, there is one source. If they do
// not, they are different things and only one of them is section 48's input.
```

**三个数**

```text
roster 的十二个 item handle     （§255 的 SessionMemberItemHandleCount）
profile 的 slots                （【注释说 0..11】但代码用 9）
```

**⚠ 注释说 "slots[0..11]"，而代码用 `CharacterProfileSlotCount = 9`。**

**这是一处注释与实现的不一致** —— 而 §239 已经确立"9 不是 12"。

## 三、`captureClientLoadoutRequest` 的**两级来源**（本组最重要的一段）

### 3.1 第一级：profile（五个真职业）

```cpp
// THE FIVE REAL CLASSES, FIRST, AND WITH NO ROOM. The profile document
// holds all five per character and is loaded whenever the client is
// logged in, so this answers even a client sitting at the menu -- which
// is what lets a player join through the dev panel instead of being
// driven in. It is the source that makes an in-match class switch change
// the weapon; the record path below only ever held the one selected
// class and needs the room cache besides.
OlMod::DedicatedSession::LoadoutRequest fromProfile{};
if (readProfileWeaponClasses(fromProfile) && valid(fromProfile))
{
    reportLoadoutClasses(fromProfile, "profile");
    lastLoadoutRefusal_ = nullptr;
    return fromProfile;
}
```

### 3.2 三个优势

```text
1. profile 文档持有每个角色的全部五个职业，且客户端登录时【就】加载
2. ⇒ 即使客户停在菜单也能回答 ⇒ 允许玩家【通过开发面板加入】而不是被驱入
3. ⇒ 是【比赛内换职业能改变武器】的来源
```

### 3.3 第二级：record-mirror（一个职业镜像到五个）

```cpp
// FALLBACK: the one-class record, mirrored. Needs the room cache, and
// makes a switch a no-op, but one correct class still beats none.
if (readLoadoutRecord(fromClientRecord) && valid(fromClientRecord))
{
    reportLoadoutClasses(fromClientRecord, "record-mirror");
    lastLoadoutRefusal_ = nullptr;
    return fromClientRecord;
}
```

### 3.4 三个劣势

```text
1. 需要 room cache
2. 换职业是 no-op
3. 但"一个正确的职业仍胜过没有"
```

### 3.5 那句 `source=` 的判据

```cpp
// ONE LINE THAT SAYS WHAT WAS SERVED AND FROM WHERE. `profile` = the five
// real classes; `record-mirror` = the fallback one class copied across all
// five. When two clients hold different classes and a switch changes the gun
// this must read `profile`; if it says `record-mirror`, the switch is a no-op
// and the profile read failed -- exactly the difference the party needs.
```

**⇒ 一行日志直接分开两个世界** ✓

**与 §241 里 `index` + `record0`、§240 里"同一 id 是否跨 class"同族。**

### 3.6 **这两级都在 `refuse` lambda 之前**

```cpp
{
    // ... profile ...
    // ... record ...
}

// NAME THE GATE THAT CLOSED.
const auto refuse = [...](...)
```

**所以这两级是"无需任何门控"的** ✓

**那段注释解释了为什么**：

```cpp
// THE CLIENT'S OWN RECORD FIRST, AND IT NEEDS NONE OF THE GATES BELOW.
//
// Everything after this point runs through sub_50FF30, and sub_50FF30 is switched
// OFF BY DEFAULT ... That gate sits inside currentCharacterIndex(), so the very
// first thing this function did was refuse -- which is why binding the record
// changed nothing until now, and why the failure read as
// "currentCharacterIndex unavailable" rather than as a disabled probe.
//
// sub_7C5BA0 is not that function. It is the record builder the client runs for
// itself, it carries the character item ids as well as the weapons, and it needs
// neither the probe nor our character index.
```

### 3.7 那条因果链

```text
1. 门控在 currentCharacterIndex() 里
2. ⇒ 函数第一件事就是拒绝
3. ⇒ 而失败信息读成 "currentCharacterIndex unavailable"
4. ⇒ 而不是 "probe disabled"
```

**"这就是为什么绑定记录直到现在都没改变什么，以及为什么失败读成一个不可用的索引而不是一个被禁用的探针。"**

**这是"沉默/误导读起来像健康"的**第七次**。**

### 3.8 `sub_7C5BA0` 的三个性质

```text
是客户端【为自己】运行的记录构建器
携带角色物品 id 【以及】武器
不需要探针也【不需要】我们的 character index
```

## 四、`refuse` 的**边沿触发**

```cpp
const auto refuse = [this](const char *reason) -> optional<LoadoutRequest> {
    if (lastLoadoutRefusal_ != reason)
    {
        lastLoadoutRefusal_ = reason;
        write("client loadout capture refused: " + reason);
    }
    return nullopt;
};
```

### 4.1 七个具名原因（从代码可数）

```text
"currentCharacterIndex unavailable"
"character item bindings unavailable"
"characterSlotGet unbound"
"public profile not ready"
"profile slot probe disabled"
"character slot out of range"
"character index moved mid-read"
"character slot 0 is empty"
"character index moved during the class walk"
"request invalid despite the client record"
"request invalid and the client record was empty"
```

**十一个**（我列出来的）。

### 4.2 那句

```cpp
// Every return below used to be a bare nullopt, so the
// only thing a capture failure could say was "NO_LOADOUT" -- which is the outcome,
// not the cause, and it is what made a fix look like it had not run when the truth
// was that the function returned four gates earlier.
```

**"一个捕获失败唯一能说的是 `NO_LOADOUT` —— 那是结果而不是原因，而正是它让一个修复看起来像没跑，而真相是函数在四个门之前就返回了。"**

**⇒ "四个门之前"** —— 明确量化了误导的距离。

## 五、**九个槽 vs 十二宽**的 `static_assert`（本组第二重要）

```cpp
// NINE. request.characterItemIds is twelve wide because the RECORD is; the
// PROFILE's slots array is not, and reading its tenth entry is a fault.
static_assert(CharacterProfileSlotCount <= OlMod::DedicatedSession::CharacterItemCount);

std::array<std::uint32_t, CharacterProfileSlotCount> profileSlots{};   // ← 9
for (index = 0; index < CharacterProfileSlotCount; ++index)
{
    const auto slot = invokeCharacterSlotGet(characterSlotGet_, *characterIndex, index);
    if (!slot) continue;
    if (*slot < 0 || *slot > 0xFFFF) return refuse("character slot out of range");
    profileSlots[index] = (uint32)*slot;
}
```

### 5.1 三层

```text
1. `profileSlots` 是【九】宽
2. `request.characterItemIds` 是【十二】宽（因为记录是）
3. "读它的第十项是一个 fault"
```

### 5.2 那句"读第十项是一个 fault"

**"reading its tenth entry is a fault"** —— 所以 `invokeCharacterSlotGet` 的第 9 项会崩。

**这是一个**硬**约束** —— 而不是"返回垃圾"。

### 5.3 `static_assert` 只是单向

```cpp
static_assert(CharacterProfileSlotCount <= CharacterItemCount);
```

**只保证 `9 <= 12`** —— 而**不**保证"九就是正确的"。

**⇒ 如果 `CharacterProfileSlotCount` 被改成 13，编译失败；如果是 12，编译通过但读第 12 项会 fault。**

**这是一个**不完整**的保护** —— 因为 12 是上限而不是 9。

## 六、`character capture:` 的**整元组去重**（本组第三重要）

```cpp
// SAY WHICH CHARACTER THIS IS AND WHAT ITS TWELVE SLOTS HOLD.
//
// Every model request this server has ever made carries item=545 and resolves
// to fpa_goose_ss_m_15 -- one item and one model across every session in 30 MB
// of log -- and the only character index ever printed is 0, from the
// presentation stub. That is consistent with TWO different worlds: the player
// really is on character 0, or currentCharacterGet_ is not reading their
// selection at all. Nothing currently logged separates them, because the index
// is only ever printed when it is OUT OF RANGE.
//
// Deduped on the whole tuple, so a player who never changes character prints
// one line and a player who does prints a second. That is the measurement:
// pick a different character in the menu and see whether this moves.
```

### 6.1 三个事实

```text
item=545 → fpa_goose_ss_m_15    30 MB 日志里每个会话都是【一个物品一个模型】
唯一打印过的 character index 是 0（来自 presentation stub）
⇒ 而索引只在【越界时】才打印
```

### 6.2 两个世界

```text
A. 玩家真的在角色 0 上
B. currentCharacterGet_ 根本没在读他们的选择
```

**"没有现行的日志能分开它们。"**

### 6.3 而解法是**整元组去重**

```cpp
std::string line = "character capture: index=" + index + " slots=" + 九项;
static std::string reported;
if (reported != line) { reported = line; write(line); }
```

### 6.4 为什么整元组去重能分开

```text
玩家不换角色  ⇒ 打一行
玩家换角色    ⇒ 打第二行
```

**⇒ 一个**操作性实验**："在菜单里选一个不同的角色，看这行是否动。"**

**这是本文件里少有的"把测量设计成一个玩家动作"的地方** ✓

### 6.5 而 `item=545` 与 §239 的"545 for everyone before that"

**§239**："房间名册携带真实的、每个玩家不同的角色物品（一个周期里 2056 和 686），而【在那之前所有人都是 545】"

**⇒ 545 是"从未解析成功"的默认值。**

**现在这里给出了它的来源**：

```text
item=545 → fpa_goose_ss_m_15
```

**`fpa_goose_ss_m_15`** —— 一个具体的模型名（女性、鹅？、SS?、m=?、15=编号）。

## 七、`placeCharacterItemsByRecordEntry` 的复用

```cpp
// Same packing as the document path, same placer.
placeCharacterItemsByRecordEntry(profileSlots, request.characterItemIds);
```

**九项 → 十二项** ✓ 与 §242 的 `placeCharacterItemsByRecordEntry` 一致

**"与文档路径相同的打包、相同的放置器"** —— **一次实现两处使用** ✓

## 八、**两次索引变更检查**

```cpp
if (currentCharacterIndex() != characterIndex)
    return refuse("character index moved mid-read");
...
if (currentCharacterIndex() != characterIndex)
    return refuse("character index moved during the class walk");
```

### 8.1 两个不同的时机

```text
第一次   读完九个槽之后
第二次   class 遍历之后
```

### 8.2 **这是 TOCTOU 的防御**

**"character index moved"** —— 如果玩家在读取过程中换了角色，两个来源就不一致。

**⇒ 所以拒绝而不是返回部分一致的数据。**

**与 §255 里"读不到不是竞态"形成对照：那里排除竞态，这里**防御**竞态。**

## 九、`character slot 0 is empty` 的拒绝

```cpp
if (!request.characterItemIds.front())
    return refuse("character slot 0 is empty");
```

### 9.1 为什么 slot 0 特殊

**§242 里 `characterItemRecordEntry` 说："A character IS entry 0, whatever its own recordEntry field says."**

**⇒ slot 0 是**角色本身**，不是部件。**

**⇒ 如果它为空，这个角色记录就没有角色。**

**⇒ 而这正是 §255 里 `NULL`/`EMPTY` 的祖先。**

## 十、`firstSlot = *characterIndex * 10 + classIndex * 2`

```cpp
const auto firstSlot = *characterIndex * 10 + classIndex * 2;
const auto primary =
    readProfileWeaponRequest(classIndex, false, loadoutClass.weapons[0]) ||
    readStagedWeaponRequest(firstSlot, loadoutClass.weapons[0]);
...
if (!readProfileWeaponRequest(classIndex, true, loadoutClass.weapons[1]))
    static_cast<void>(readStagedWeaponRequest(firstSlot + 1, loadoutClass.weapons[1]));
```

### 10.1 两个排布

```text
staged 路径：  characterIndex * 10 + classIndex * 2 + (0|1)
profile 路径： readProfileWeaponRequest(classIndex, secondary)
```

### 10.2 **`* 10` 与 `* 2`**

```text
每角色 10 个槽（5 职业 × 2 武器）
每职业 2 个槽（主 + 副）
```

**⇒ 所以 staged 数组是 `12 角色 × 10` 或类似的布局。**

### 10.3 `firstSlot >= 120` 的界

**§242 里 `readStagedWeaponRequest` 有 `slotIndex >= 120` 的检查** ⇒ **12 × 10 = 120** ✓

**这是一处交叉确认。**

### 10.4 主武器 `||`、副武器 `if (!..)`

```text
主武器：  profile || staged      （两者都试）
副武器：  profile，失败则 staged  （也是两者都试）
```

**但 `||` 与"if (!x) y"的语义相同** —— 一处用短路运算符，一处用 if。

**风格不一致但语义一致。**

## 十一、`resolveClientCharacterPresentation` 的**两次索引检查**

```cpp
const auto request = captureClientLoadoutRequest();
if (!request || request->characterIndex != characterIndex) return nullopt;
const auto presentation = resolveSessionCharacterPresentation(*request);
if (currentCharacterIndex() != characterIndex) return nullopt;
return presentation;
```

### 11.1 三处检查

```text
1. 请求的 characterIndex 等于参数
2. 解析之后再查一次 currentCharacterIndex
```

**这是**第三次**索引一致性检查**（前两次在 `captureClientLoadoutRequest` 里）。

**⇒ 一个完整的读取事务里共四次。**

## 十二、`resolveSessionCharacterPresentation` 的**十一项映射**（本组第四重要）

```cpp
// CODREF(character_customization): CODOL
// CopyCurrentItems 0x00568860, BuildClientInfo 0x00569B90 and
// ResolveSelectionIds 0x0040CA30 establish the item-name -> eleven
// selection-ID pipeline below. BO1/Ghosts have no marketplace-derived
// equivalent; they constrain server presentation ownership only.
std::array<std::string, 11> internalNames{};
std::array<const char *, 11> internalNamePointers{};
for (recordIndex < request.characterItemIds.size())          // ← 【12 项】
{
    const auto nameIndex = CharacterRecordToSelectionName[recordIndex];
    const auto itemId = request.characterItemIds[recordIndex];
    if (nameIndex == internalNames.size() || !itemId) continue;      // ← 【>= 11 跳过】
    const auto internalName = readItemInternalName(itemId);
    ...
    internalNames[nameIndex] = *internalName;
    internalNamePointers[nameIndex] = internalNames[nameIndex].c_str();
}
```

### 12.1 **十二项记录 → 十一项选择名**

```text
characterItemIds 有 12 项
internalNames    有 11 项
CharacterRecordToSelectionName[]  把 12 映射到 11（可能有一项映射到 11 ⇒ 跳过）
```

### 12.2 那个"跳过"的判据

```cpp
if (nameIndex == internalNames.size() || !itemId) continue;
```

**`nameIndex == 11` ⇒ 跳过。**

**⇒ 所以 `CharacterRecordToSelectionName` 里**有一项是 11**（表示"无对应"）。**

**这与 §202 里 `{11,0,1,2,3,4,5,6,7,8,11,9}` 是同一个表** ✓

**记忆里的"。`{11,0,1,2,3,4,5,6,7,8,11,9}` semantics resolved"** —— 而这个表**有两个 11**（下标 0 与 10）。

**⇒ 所以记录的第 0 项与第 10 项都**不映射**到选择名。**

### 12.3 而第 0 项是**角色本身**

**§242**："A character IS entry 0"

**⇒ 角色本身不进选择名列表** ✓ 合理（因为角色是整体而不是部件）

### 12.4 那种"两种 11"

```text
internalNames 的宽度  11
第 0 项与第 10 项     映射到 11（即无效）
其余 9 项            映射到 0..9
```

**等等：`{11,0,1,2,3,4,5,6,7,8,11,9}` 里 9 在最后一位（第 11 位）⇒ 映射到 9。**

**所以有效的 nameIndex 是 0..9（十个），而 11 是哨兵。**

**⇒ 但 `internalNames` 是 11 宽（0..10）⇒ 第 10 项**永远不会被填**。**

**⇒ 所以实际上只有 10 项被用。**

**这可能是一处冗余。**

## 十三、那个**内联汇编调用**

```cpp
const auto selectionResolver = characterSelectionResolve_;
const auto *names = internalNamePointers.data();
auto *selectionIds = presentation.selectionIds.data();
__asm
{
    mov eax, names
    push selectionIds
    call selectionResolver
    add esp, 4
}
```

### 13.1 **又是 `__usercall`**

```text
EAX    names 数组指针
栈      selectionIds 输出指针
```

**与 §242 的 `__usercall`（EAX + EDI）不同** —— 这次是 **EAX + 栈**。

**⇒ 本 build 里有多种非标准调用约定。**

### 13.2 `add esp, 4` ⇒ 调用者清栈

**所以是 `__cdecl` 的栈清法 + EAX 传参。**

### 13.3 而 `names` 是 `const char**` 的 `data()`

**`internalNames` 是 `array<std::string, 11>` 而 `internalNamePointers` 是 `array<const char*, 11>`。**

**⚠ `internalNames` 在循环里被赋值，而 `internalNamePointers[nameIndex] = internalNames[nameIndex].c_str()`。**

**如果 `internalNames` 的 `std::string` 之后被重新赋值（不会，因为只看一次）—— 安全。**

**但 `std::string` 的 `c_str()` 在**短字符串优化**下指向对象内部** ⇒ 对象必须存活且不移动 ⇒ `array` 是固定大小的，所以稳定 ✓

## 十四、`none_of(selectionIds, value != 0)` 的拒绝

```cpp
if (none_of(presentation.selectionIds, [](auto v) { return v != 0; }))
{
    store(Selection);
    return nullopt;
}
```

**⇒ "全零 ⇒ 失败"** —— 与 §241 里 `if (!classMask) return false` 同族。

## 十五、`characterDefinition[2] <= 1` 的性别

```cpp
if (!readableSpan(characterDefinition, CharacterItemDefinitionSize) ||
    characterDefinition[2] > 1)
{
    store(CharacterDefinition);
    return nullopt;
}
presentation.female = characterDefinition[2] != 0;
```

### 15.1 `+2` 在**两个结构里是两回事**

```text
item definition +2       ⇒ 角色定义表的下标（§242）
character definition +2  ⇒ female 标志
```

**同一个偏移，两种语义** —— 因为它们是两个不同的结构。

### 15.2 `+3` 是**颜色选择器的值**

```cpp
const auto colorSelector = CODOL_CharacterColorSelectorFromDefinitionValue(characterDefinition[3]);
```

**⇒ 所以 `characterDefinition` 的前四个字节是**：

```text
+0  ?
+1  ?
+2  female（0/1）
+3  color selector 值
```

**与 §255 里"`charDef+36` 是 option count、`+40` 是 option list"互补。**

## 十六、`viewmodelIndex` 的**按名线性搜索**

```cpp
// OLMOD(character-viewhands-bootstrap): resolving a CCS index by
// the fixed tf141 name avoids a numeric index, but is still a
// character-specific recovery fallback. It is deliberately kept
// separate from the proven selection parser above.
for (std::uint16_t index = 1; index <= MaximumWeaponAssetIndex; ++index)
{
    const auto name = readCString(nativeConfigString(ModelConfigStringBase + index), 128);
    if (name && *name == GenericCharacterViewhands)
    {
        presentation.viewmodelIndex = index;
        break;
    }
}
```

### 16.1 五层

```text
1. 按【固定 tf141 名】解析一个 CCS 索引而不是硬编码数字
2. 但这仍是【角色特定的恢复回退】
3. 故意与上面【已验证的】选择解析器分开
4. 线性搜索 1..MaximumWeaponAssetIndex
5. 找到第一个名字等于 GenericCharacterViewhands 的
```

### 16.2 `GenericCharacterViewhands` 是**固定的 tf141 名**

**"tf141" 是 COD:MW2 的特遣队名** —— 所以这是从 MW2 沿用的资源。

### 16.3 而 `ModelConfigStringBase + index` 与 §236 的 `WeaponConfigStringBase` 是**两个不同的基址**

```text
WeaponConfigStringBase   5960      武器
ModelConfigStringBase    ?          模型
```

**所以模型名有自己的配置串区间。**

## 十七、关键结论

1. **`"x"` 表示"读不出"**，因为 0 是合法的空槽。
2. **注释说 `slots[0..11]` 而代码用 9** —— 一处不一致。
3. **两级来源 `profile` / `record-mirror`，而 `source=` 一行分开两个世界**。
4. **门控在 `currentCharacterIndex()` 里 ⇒ 失败读成"索引不可用"而不是"探针禁用"** —— 第七次"误导读起来像健康"。
5. **十一个具名拒绝原因**取代一个 `NO_LOADOUT`。
6. **九个槽 vs 十二宽，而 `static_assert` 只保证 `<=`** —— 不完整保护。
7. **`item=545 → fpa_goose_ss_m_15`** 是"从未解析成功"的默认值（§239 的 545）。
8. **整元组去重让"换角色"成为一个可执行的测量**。
9. **两次索引变更检查 + `resolveClientCharacterPresentation` 的第三次** = 一个事务里四次。
10. **`character slot 0` 是角色本身，为空则无角色。**
11. **`firstSlot = characterIndex * 10 + classIndex * 2`** 与 §242 的 `>= 120` 界一致（12 × 10）。
12. **十二项记录 → 十一项选择名，其中第 0 与第 10 项映射到哨兵 11**。
13. **`CharacterRecordToSelectionName = {11,0,1,2,3,4,5,6,7,8,11,9}`** ⇒ 只有 10 项被用，`internalNames[10]` 永不填。
14. **`__usercall` 的第二种形态（EAX + 栈）**，与 §242 的 EAX + EDI 不同。
15. **`characterDefinition +2` = female、`+3` = color** —— 与 `item definition +2`（下标）同名不同义。
16. **`viewmodelIndex` 是按名线性搜索的恢复回退**，与已验证的解析器分开。

## 十八、未闭合点

- `internalNames` 11 宽但只有 10 项被用（冗余或遗漏）。
- `characterDefinition +0/+1` 未解。
- `GenericCharacterViewhands` 的具体字符串值。
- `EngineBindings.cpp` 15850 行之后未读取。
