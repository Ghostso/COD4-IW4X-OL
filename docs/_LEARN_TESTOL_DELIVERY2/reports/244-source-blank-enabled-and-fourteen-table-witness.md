# 244 · 空白 `enabled` 的三次判定、十四个表的 `-?.y` 见证、七个 dvar 块各自 faults

## 一、范围

本报告学习 `EngineBindings.cpp` 11023–11213 行。

## 二、那八个出口的 `refuse` lambda

```cpp
// SAY WHICH EXIT FIRED. There are eight ways out of this function and the caller
// reports `default_attachments` for every one of them, so a weapon that is simply
// missing from the table is indistinguishable from a table that is not loaded or a
// cell that would not read. readAttachmentModelSlot below already solved this with
// a per-table outcome string; this is the same idea, edge-triggered on the message
// so a healthy weapon says nothing.
const auto refuse = [this, weaponName](const char *why)
    -> std::optional<std::vector<NamedWeaponAttachment>>
{
    auto message = "default attachments unavailable for '" + std::string(weaponName) +
        "': " + why;
    if (message != lastDefaultAttachmentRefusal_)
    {
        lastDefaultAttachmentRefusal_ = message;
        write(GameServer, message);
    }
    return std::nullopt;
};
```

### 2.1 三个要素

```text
1. 八个出口一个返回类型（都是 nullopt）⇒ 调用方无法区分
2. ⇒ 把【原因串】放进 lambda，每条出口必须给
3. 【边沿触发】：只在消息变化时打 ⇒ 健康武器一声不响
```

### 2.2 边沿触发的一个副作用

```cpp
if (message != lastDefaultAttachmentRefusal_)
```

**比较的是**整个消息**（含武器名）** —— 所以**两个不同武器的同一原因会各打一次**，但**同一武器的同一原因只打一次**。

**这正是想要的** —— 与 §240 里 `ordinalReported` 对整行去重同族。

### 2.3 八条出口的清单

```text
1. !dbFindXAssetHeader_                  "DB_FindXAssetHeader unbound"
2. !validBookingName(weaponName)         "the weapon name is not a usable identifier"
3. !table                                 "the weapon items table is not loaded"
4. !foundRow || !*foundRow                "no row for this weapon..."
5. !slotName || !defaultName || !enabled  "a slot/default/enabled cell would not read"
6. *enabled 非 y 非 n                     "an 'enabled' cell is neither y nor n..."
7. !validBookingName(*defaultName)        "default attachment name is not usable..."
8. （成功）                                —— 
```

**实际是七条失败 + 一条成功** —— 注释说"八个出口"，把成功也算了一个出口。

### 2.4 两个 `.c_str()` 的陷阱

```cpp
return refuse(("an 'enabled' cell is neither y nor n: '" + shown + ... ).c_str());
return refuse(("default attachment name is not usable: '" + shown + ...).c_str());
```

**`std::string(...).c_str()` 传给一个 `const char*` 参数** —— 临时 `std::string` 在**完整表达式结束时**销毁。

**而 `refuse` 内部**立刻**用 `why` 构造 `std::string`** ⇒ **在这个调用点安全**（临时活到 `refuse` 返回）。

**但这是一个极易变成悬垂指针的写法** —— 如果 `refuse` 改成保存 `const char*` 就崩。

## 三、**空白 `enabled` 的三次判定**（本组最重要的一段）

### 3.1 三次判定在代码里的顺序

```cpp
if (slotName->empty() && defaultName->empty() && enabled->empty())
    continue;                                           // ① 整三元组空
if (!slotName->empty() && defaultName->empty() && enabled->empty())
    continue;                                           // ② 只有槽名
if (*enabled == "n") continue;                          // ③ 显式禁用
if (enabled->empty()) { ...note...; continue; }          // ④ 空白 + 有默认
if (*enabled != "y") return refuse(...);                 // ⑤ 既非 y 亦非 n
if (defaultName->empty()) continue;                      // ⑥ y 但无默认 ⇒ 合法槽
if (!validBookingName(*defaultName)) return refuse(...); // ⑦ 默认名不可用
```

### 3.2 关键在于 ④ 的位置

**④ 在 ⑤ 之前** —— 因为空串 `""` 既不是 `"y"` 也不是 `"n"`，如果不先拦就会被 ⑤ 拒绝。

### 3.3 那次事故

```text
A BLANK `enabled` BESIDE A REAL DEFAULT IS NOT ENABLED. This dropped the whole
class for 19 of the table's 838 weapons -- every type95 variant INCLUDING the base
type95_mp, plus ak47ornate, akbpcoral, famasnya and famasnyb -- and a dropped
class is a player who edits his loadout, spawns, and finds the gun he picked is
simply not there.
```

**"这个把 838 个武器里的 19 个的整个职业丢掉了 —— 每一个 type95 变体【包括基础的 `type95_mp`】，还有 `ak47ornate`/`akbpcoral`/`famasnya`/`famasnyb`"**

### 3.4 那段"往哪个方向读是一种判断"

```text
WHICH WAY TO READ A BLANK IS A JUDGEMENT, so it is made in the direction that
cannot build a wrong gun. Reading it as ENABLED would add a default attachment
nobody asked for, and a wrong attachment id names a tag the model does not have
and faults the client at spawn (section 187). Reading it as NOT enabled can at
worst omit one built-in component, and the row immediately above already treats
an empty third cell as "not enabled" when the default is empty too.
```

### 3.5 两个方向的**代价不对称**

```text
读作 ENABLED       ⇒ 加一个没人要的默认附件 ⇒ 错误的附件 id 命名一个模型没有的 tag
                    ⇒ 【在 spawn 时让客户端 fault】（§187）
读作 NOT enabled   ⇒ 至多漏掉一个内建部件
```

**"在不能造出一把错枪的方向上做判断"** —— 这是**代价不对称下的决策原则**。

**与 §243 里"`first > count` 时返回空表"是同一条**：两个错误里选代价小的那个。

### 3.6 三次判定的完整矩阵

| slotName | defaultName | enabled | 结果 |
|---|---|---|---|
| 空 | 空 | 空 | ① 跳过 |
| 非空 | 空 | 空 | ② 跳过（可选槽） |
| * | * | "n" | ③ 跳过 |
| * | 非空 | 空 | ④ **记录 + 跳过**（本条修复） |
| * | * | 其它 | ⑤ **拒绝**（含字节显示） |
| * | 空 | "y" | ⑥ 跳过（`tmp_mp`） |
| * | 非空 | "y" | ⑦ 正常加入 |

**七种组合**（`slotName` 空 + 其它非空的情况未在此列出）。

## 四、`tmp_mp` 那个"启用的槽但没有默认"（⑥）

```cpp
// AN ENABLED SLOT WITH NO DEFAULT IS A SLOT, NOT A FAILURE. The case above
// only covers a row that leaves `enabled` blank; tmp_mp marks the slot "y"
// and still names no built-in component. Refusing the whole weapon for that
// skipped the entire class, and a class with no weapons is a SessionStart
// that queues and never commits -- which is what kept a player at active=0.
```

**五层**：

```text
1. tmp_mp 把槽标 "y" 却没有内建部件
2. 为那个拒绝整个武器 ⇒ 跳过整个职业
3. 没有武器的职业 ⇒ SessionStart 【排队永不提交】
4. ⇒ 玩家停在 active=0
5. ⇒ 这解释了 §241 里"单 class 的排队永不提交"的另一条来源
```

**§241 说的是"一个 class 的"排队永不提交；这里是"零 class 的"** —— 同一个下游症状，两个不同的上游原因。

## 五、"SHOW THE BYTES" 的三处（本组的方法论）

### 5.1 三处

```cpp
// ⑤ enabled 非 y 非 n
// SHOW THE BYTES, for the same reason the defaultName case below does:
// "neither y nor n" is a verdict and a verdict cannot be checked. It cost
// a player his class on type95techslime_mp and there was no way to tell
// from the log whether the cell was empty, localised, or something the
// reader mis-sliced ...

// ⑦ defaultName 不可用
// SHOW THE BYTES rather than calling it unusable. "not an identifier" is
// a verdict, and a verdict cannot be checked; the value can.
```

### 5.2 那句核心

**"`neither y nor n` 是一个判定，而判定无法核对"**

**"`not an identifier` 是一个判定，而判定无法核对；值可以。"**

### 5.3 三种可能被"不可核对"掩盖的原因

```text
1. 单元格为空
2. 被本地化了（"是"/"否"）
3. 读取器切错了
```

**三个完全不同的原因，一个"既非 y 亦非 n"的判定全都盖住。**

### 5.4 `show` 的写法

```cpp
shown += (character >= 32 && character < 127)
    ? std::string(1, character)
    : "<" + std::to_string((unsigned char)character) + ">";
```

**可打印 ASCII 原样；其它一律 `<N>`** —— 所以**空格、NUL、全角字符、UTF-8 多字节都可见**。

**这与 §243 里 `auditWeaponItemsTable` 的 `show` 是同一个实现的**第二份拷贝**。

### 5.5 而"57% 的字符串池回引"在这里被第二次引用

```text
and the OFFLINE copy of this table cannot settle it either, because the extractor
resolves only 57% of its string-pool back-references and prints another weapon's
text for the rest.
```

**§243 里已经是"57% + 另一个武器的文本"** —— 这里是同一事实的**第二次引用**（在另一个函数里）。

**所以离线表不可信这件事在代码里有两条独立记录。**

## 六、`readAttachmentModelSlot`：**十四个表**的 `-?.y` 见证（本组第二重要）

### 6.1 那句"十四个查找和一个 nullopt"

```text
FOURTEEN TABLE LOOKUPS AND ONE `std::nullopt`. Absent table, absent row, ambiguous
row and "in none of them" all leave by the same return, and the caller reports
`equipped_attachment_slot` for every one of them - so record a character per table
and let the log say which of the four it was.
```

### 6.2 四个字符的语义

```text
'-'  表缺失
'?'  行读取失败
'.'  行不存在
'y'  匹配
```

### 6.3 实现

```cpp
for (const auto &[tableName, slot] : AttachmentSlotTables)
{
    const auto *table = readStringTable(..., tableName, 1);
    if (!table) { outcome += '-'; continue; }
    const auto row = findStringTableRow(*table, attachmentName);
    if (!row)   { outcome += '?'; continue; }
    if (!*row)  { outcome += '.'; continue; }
    outcome += 'y';
    if (result) ambiguous = true; else result = slot;
}
```

### 6.4 **"这个见证字符串的位置就是表的位置"**

**`outcome` 按 `AttachmentSlotTables` 的顺序拼接** ⇒ **第 N 个字符就是第 N 张表**。

**"十四个字符"** ⇒ `AttachmentSlotTables.size() == 14`。

**所以这条日志同时给出了"哪张表命中"与"哪张表读失败"** —— 一个字符串承载 14 个布尔。

**与 §243 的"行数就是答案"是同一种"把信息编码进形状"的手法。**

### 6.5 **歧义不是"多命中"而是"多个不同槽"**

```cpp
if (result) ambiguous = true;      // 第二次命中就算歧义
```

**注意：这里**不比较 `slot` 是否相同** —— 只要第二次命中就算歧义。

**所以即使两张表都报同一个槽号，也被判为歧义。**

**这可能是一处过保守** —— 如果两张表（例如"attachment 表"与"shared attachment 表"）合法地重叠，就会永远判歧义。

### 6.6 三个拒绝条件

```cpp
if (!result || ambiguous || outcome.find_first_of("-?") != npos)
```

```text
!result                     没命中任何表
ambiguous                   多个命中
outcome 含 '-' 或 '?'        有表缺失或有行读失败
```

**第三项是最严格的** —— **哪怕命中了，只要有任何一张表缺失或读失败，整个解析失败**。

**注意 `.`（行不存在）【不】导致失败** —— 因为那是正常情形（这个附件不在那张表里）。

### 6.7 三个条件对应 §243 的"十四个出口"

**这里把 14 × 4 = 56 种局面压缩成 3 个判据** —— 而见证字符串保留了全部 14 位细节。

## 七、`registerGameplayDvars`：**七个块各自 fault**

### 7.1 七个块

```cpp
constexpr std::array Blocks{
    GameplayDvarsRegisterRva,
    GameLogDvarsRegisterRva,
    VehicleDvarsRegisterRva,
    PlayerDvarsRegisterRva,
    ActorDvarsRegisterRva,
    MiscDvarsRegisterRva,
    ScoreDvarsRegisterRva,
};
```

**七块，顺序固定** —— 而注释说"CG_Init's own seven, in its own order"。

### 7.2 与 §192–213 里"整块重定位"的对照

**§192–213 学的是 `callback table whole-block relocation (op=8 target=0)`** —— 那里是**整块搬**。

**而这里是**逐块调用 + 逐块 fault** —— 因为：

```cpp
// each one faulting on its own so a bad block names itself instead of taking
// the other six with it.
```

**"各自 fault 以便一个坏块命名自己而不是把其它六个带走"**

### 7.3 `break` 而不是 `continue`

```cpp
if (!tryCallVoid(module_ + rva, fault)) { ...log...; break; }
++registered;
```

**失败即 `break`** —— 不继续尝试后面的块。

**理由**：dvar 注册有顺序依赖（后面的块可能引用前面块的 dvar）。

**而 `registered` 返回值就是"成功到第几个"** —— 所以 `registered == 7` 才全成。

### 7.4 失败日志的五个字段

```cpp
"gameplay dvar block faulted block=0x%07X at rva=0x%07X op=%u target=0x%08X code=0x%08X"
```

```text
block      块 RVA（原值）
rva        fault.address 转成 RVA（若在模块内）否则保留绝对
op         VEH 的操作码
target     VEH 的目标地址
code       异常码
```

### 7.5 那个三元表达式

```cpp
fault.address >= (uint32)module_ ? fault.address - (uint32)module_ : fault.address
```

**在模块内 ⇒ 转 RVA；否则保留绝对地址。**

**这是"fault 可能发生在模块外"的承认** —— 如果 RVA 错了，可能跳到任意地址。

## 八、`characterPresentationResolverAvailable`

```cpp
bool EngineBindings::characterPresentationResolverAvailable() const
{
    return characterSelectionResolve_ != nullptr;
}
```

**一行** —— 只是"这个函数绑定了没有"。

**注意名字**：`Available` 而不是 `Bound` —— 因为"绑定"与"可用"在这里等价（没有更深的检查）。

## 九、`weaponRegistryInitialized` 的五项检查

```cpp
constexpr auto BaseWeaponCount = BaseWeaponAssetCount;
if (!module_) return false;
...
if (!readableSpan(weaponCount, 4) || !readableSpan(attachmentModelCount, 2) ||
    !readableSpan(mappingCounts, BaseWeaponCount) || !*weaponCount ||
    *weaponCount >= WeaponConfigStringCount || *attachmentModelCount <= 2)
    return false;
return std::any_of(mappingCounts, mappingCounts + std::min(*weaponCount, BaseWeaponCount),
                   [](const std::uint8_t count) { return count != 0; });
```

### 9.1 六项

```text
1. module_ 非空
2. weaponCount 可读
3. attachmentModelCount 可读
4. mappingCounts 可读（BaseWeaponCount 字节）
5. *weaponCount 非零 且 < WeaponConfigStringCount(1700)
6. *attachmentModelCount > 2
```

### 9.2 第七项是**内容判据**

```cpp
std::any_of(mappingCounts, ... + min(*weaponCount, BaseWeaponCount), [](c){ return c != 0; });
```

**"至少有一个武器有非零的附件数"** —— 这是"注册表真的被填过"的证据。

**`*attachmentModelCount <= 2` 是第二道** —— 因为附件模型计数在空表时可能是 0 或 1 或 2（哨兵）。

### 9.3 **`min(*weaponCount, BaseWeaponCount)`**

**因为 `mappingCounts` 只保证 `BaseWeaponCount` 字节可读** —— 而 `*weaponCount` 可能更大（动态武器）。

**这与 §236 里 `first > count` 的夹紧是同一类**。

## 十、两个常量名的关系

```cpp
constexpr auto BaseWeaponCount = BaseWeaponAssetCount;
```

**为什么要别名** —— 因为 `BaseWeaponAssetCount` 是"武器资产数"，而这里用作"映射表的长度"。

**两个语义不同但值相同** —— 别名承认了这一点。

## 十一、关键结论

1. **八个出口一个返回类型 ⇒ 必须用 `refuse` 的原因串区分**，边沿触发。
2. **空白 `enabled` 的三次判定** 是有序的，④ 必须在 ⑤ 之前。
3. **两个方向的代价不对称** ⇒ 在"不能造出错枪"的方向上判断。
4. **`tmp_mp` 的"y + 无默认"是合法槽，不是失败** —— 拒绝它会丢掉整个职业 ⇒ `active=0`。
5. **"判定无法核对，值可以"** —— 三处 SHOW THE BYTES。
6. **十四个表压成一个 14 字符的见证串** —— 位置就是表的位置。
7. **歧义判据不比较槽号** —— 第二次命中即歧义，可能过保守。
8. **`.`（行不存在）不算失败，`-`/`?` 算** —— 一个有意的区分。
9. **七个 dvar 块逐块 fault + `break`** —— 顺序依赖，返回值即进度。
10. **`weaponRegistryInitialized` 的第七项是内容判据**（至少一个非零附件数）。

## 十二、未闭合点

- 两张表合法重叠时会被永久判为歧义（`AttachmentSlotTables` 是否真的互斥未证）。
- `readDefaultWeaponAttachments` 里两处 `.c_str()` 传临时 `std::string` 的安全性依赖 `refuse` 的实现细节。
- `EngineBindings.cpp` 11213 行之后未读取（本批已续读到 11460）。
