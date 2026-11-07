# 252 · `0x400 → 0x514` 的界、本地化键当武器名、附件的"跳过不致命"与三个门

## 一、范围

本报告学习 `EngineBindings.cpp` 14050–14450 行。

## 二、`readWeaponDefinitionName` 读 **512** 字节

```cpp
return readCString(*(const char *const *)(*slot), 512);
```

### 2.1 三个上限并存

```text
128   §248/§251 的 attachment 名 / 模型名
256   §251 的 safeName
512   武器定义名
```

**不是同一个数** —— 而 `readCString` 的第二参数是"最大长度"。

### 2.2 上界是 `WeaponConfigStringCount(1700)` 而不是 `BaseWeaponAssetCount(1300)`

```cpp
if (!module_ || weaponAssetIndex >= WeaponConfigStringCount) return nullopt;
```

**因为模块化武器（动态武器）也在同一个表里** ✓ 与 §236 一致。

## 三、`altWeaponAssetIndex` 的 **`3720` 与 `3724`**

```cpp
if (!readableSpan(*slot, 3724)) return 0;
const auto alt = *(const uint32*)(*slot + 3720);
return alt && alt <= MaximumWeaponAssetIndex ? (uint16)alt : 0;
```

### 3.1 读 `+3720` 但验证到 `3724`

**`readableSpan(*slot, 3724)` 保证 `0..3723` 可读** ⇒ `+3720` 的 4 字节在界内 ✓

### 3.2 与 §243 的 `alt3716 -> 3720` 完全一致

**§243**："THE ALT WEAPON IS +3716 -> +3720"
**§252**：读 `+3720`

**两个独立位置相互印证** ✓

### 3.3 那句"这是线上已经在用的界"

```cpp
// A BOUND, AND IT IS THE ONE THE WIRE ALREADY USES. An out-of-range
// index here would be written into the native playerState and handed
// to Pmove, which indexes dword_1988B50 with it unchecked.
```

**"一个越界的 index 会被写进原生 playerState 并交给 Pmove，而它不检查地用这个 index 去索引 `dword_1988B50`。"**

**⇒ 一个坏值会导致 `Pmove` 越界读** —— 所以这个界是**安全边界**而不只是格式边界。

## 四、`aliasedWeaponName`：**文件驱动的别名表**（本组第二重要）

```cpp
static const std::map<uint32, std::string> aliases = [] {
    std::map<uint32, std::string> loaded;
    const auto path = diagnosticPath(L"weapon-aliases.csv");
    std::ifstream file(path);
    if (!file) return loaded;                      // ← 缺文件 ⇒ 空表，零成本
    std::string line;
    while (std::getline(file, line))
    {
        const auto comma = line.find(',');
        if (comma == npos || line.starts_with('#')) continue;
        const auto id = line.substr(0, comma);
        auto name = line.substr(comma + 1);
        while (!name.empty() && (name.back() == '\r' || name.back() == ' '))
            name.pop_back();
        if (name.empty()) continue;
        try { loaded.emplace((uint32)std::stoul(id), name); }
        catch (const std::exception &) { /* 跳过坏行，不致命 */ }
    }
    write("weapon aliases: N from <path>");
    return loaded;
}();
```

### 4.1 为什么是**文件而不是常量**

```cpp
// A FILE rather than a constant so adding a weapon costs an edit and a re-host
// instead of a rebuild, and it can be empty or missing with no effect at all.
```

**"增加一把武器只需要一次编辑与一次重新托管，而不是一次重建"**

**而"可以是空的或缺失，完全无影响"** ✓

### 4.2 那三个**针对性的清洗**

```text
1. 忽略 '#' 开头的行（注释）
2. 去掉行尾的 '\r' 与 ' '（CRLF 与尾随空格）
3. 空名字 ⇒ 跳过
```

**`\r` 处理是 CSV 必需** —— 而 §241 里 `LoadoutRecord` 的解析**没有**处理 `\r`（那是二进制）。

### 4.3 `std::stoul` 的**部分消费问题**

**`std::stoul("42abc")` 返回 42 而不报错** —— 所以 `"42abc,foo"` 会被当成 id 42。

**而 §243 里 `resolveSessionRewards` 用 `std::from_chars` **并**检查 `ptr == end`** —— 这里没有。

**这是一处不一致** —— 与 §197 里"`from_chars` 必须消费整个 token"的原则相反。

### 4.4 `static` + lambda 初始化的**线程安全**

**C++11 起，静态局部变量的初始化是线程安全的（`__cxa_guard`/MSVC 的 `Init_thread_header`）** ✓

**而 `if (!file) return loaded;` 的失败也被缓存** —— 所以文件后来出现也不会重读。

### 4.5 为什么"这件事值得记一条日志"

```cpp
// SAY IT ONCE. An alias is a deliberate override of what an id means, and a
// loadout that silently carried a different weapon than its id implies would be
// unexplainable from the logs.
```

**"一个别名是对一个 id 含义的有意覆盖，而一个静默地携带了与它 id 所暗示不同的武器的 loadout 会无法从日志解释。"**

**所以每次用一个别名都打一条（去重）** —— 而不是只打"表加载了 N 条"。

## 五、那个"武器商店卖不了"的问题（本组核心洞察）

```cpp
// A WEAPON THE STORE CANNOT SELL YOU.
//
// raygun_mp and thundergun_chicken_mp are weapon assets in common_gametype_mp --
// they are LOADED IN EVERY MULTIPLAYER MATCH -- and neither has a marketplace
// item, so no id names them and the class screen can never offer one. That is
// what "missing items" meant: not unowned, unreachable.
//
// The resolver two lines below takes a NAME, not an id. The id is only how the
// name is normally found. So an alias file maps an unused id onto a weapon name
// and the rest of the path is unchanged -- registration, attachments, the
// modular string, all of it.
```

### 5.1 三个层次

```text
1. raygun_mp / thundergun_chicken_mp 是【每局都加载】的武器资产
2. 但两者都没有 marketplace item ⇒ 没有 id 命名它们 ⇒ 职业界面永远给不出
3. ⇒ "missing items" 的真正含义是【够不着】而不是【未拥有】
```

### 5.2 而解法是**绕过 id → 名字这一段**

```text
resolver 接受【名字】而不是 id
id 只是【通常】用来找名字的
⇒ 别名表把一个未使用的 id 映射到一个武器名
⇒ 其余路径全然不变
```

**这是一个"在正确的层次上注入"的例子** —— 而不是给每个环节都加特例。

### 5.3 两个武器名

```text
raygun_mp
thundergun_chicken_mp
```

**`thundergun_chicken_mp` —— "电枪鸡"** 是一个彩蛋武器名。

## 六、`0x400` → `0x514` 的界（本组最重要的一段）

```cpp
// CODDIFF(1649370): the bound was 0x400 = 1024, which is 3.3.3.3's
// base weapon table. This build's is BaseWeaponAssetCount = 0x514 =
// 1300, measured from the gap between PerWeaponAttachmentCountsRva and
// AttachmentModelCountRva, so every base weapon from 1024 up was being
// rejected as out of range by a constant from the other build.
```

### 6.1 三个数

```text
0x400 = 1024   3.3.3.3 的基础武器表大小
0x514 = 1300   本 build（BaseWeaponAssetCount）
差值 = 276
```

### 6.2 **1300 是从 RVA 间距推出来的**

```text
BaseWeaponAssetCount = AttachmentModelCountRva - PerWeaponAttachmentCountsRva
```

**这是一个"布局推论"而不是"测量的常量"** —— 与 §236 里 `firstDynamicWeaponAssetIndex` 的推导同族。

**注释没有给出两个 RVA 的具体值** —— 但差值可以验证。

### 6.3 后果

**"1024 以上的每一个基础武器都被来自另一个 build 的常量判为越界。"**

**⇒ 276 个武器全部不可用。**

**这是本项目"一个常量来自错误 build"的又一大类实例** —— 与 §240 的 `0x3FF/0x3FE` 十位界、§245 的阶段号同族。

## 七、**本地化键当武器名**（本组第三重要）

```cpp
// `sf_weapon_m4_mp_name` is a LOCALISATION KEY, not a weapon
// asset name, so ItemDefinitionNameOffset is pointing at the wrong
// field on this build - another constant carried from 3.3.3.3.
```

### 7.1 那个键的形状

```text
sf_weapon_m4_mp_name
```

**`sf_` 前缀 + `_name` 后缀** —— 这是 COD 系列的本地化键命名约定。

**而武器资产名是 `m4a1tech_mp` 这样的形式。**

### 7.2 **`ItemDefinitionNameOffset` 指向了错误的字段**

**"`ItemDefinitionNameOffset` 在这个 build 上指向了错误的字段"**

**而 §242 里 `readItemInternalName` 正是用 `ItemDefinitionNameOffset`：**

```cpp
const auto internalName = readCString(name, 128);
if (!internalName || !validBookingName(*internalName)) return nullopt;
```

**而 `validBookingName("sf_weapon_m4_mp_name")` 会通过**（它是合法标识符）⇒ **所以 `readItemInternalName` 返回本地化键而不报错。**

**⇒ `resolveWeaponItem` 用这个键去 `weaponResolver_` 会失败。**

**这是一条完整的因果链：偏移错 → 返回本地化键 → 名字合法检查通过 → resolver 失败。**

### 7.3 而解法是**转储全部可读字符串**

```cpp
for (std::size_t offset = 0; offset + 4 <= ItemDefinitionSize; offset += 4)
{
    const auto *const candidate = *(const char *const *)(definition + offset);
    const auto text = readCString(candidate, 64);
    if (text && !text->empty() && validBookingName(*text))
        fields += " +" + std::to_string(offset) + "=" + *text;
}
```

### 7.4 **每 4 字节试一次**

**`ItemDefinitionSize = 52`** ⇒ **13 个候选偏移**（0,4,8,...,48）。

**而每个都 `readCString(candidate, 64)`** —— 如果那个位置不是指针，`readCString` 会在 `readableSpan` 失败或读到垃圾后返回 nullopt ✓

### 7.5 那句方法论

```cpp
// Guessing +8 and then +16 costs two launches; this costs none.
```

**"猜 +8 然后再猜 +16 花掉两次启动；这个一次都不花。"**

**这是"一次性转储所有候选"击败"逐个假设验证"** —— 与 §244 里"SHOW THE BYTES"、§243 里"那这个表里到底有什么"是同一族。

**而 §242 里 `characterOptionSelectionMask` 的 `-- THE LIST STARTS` 也是同一手法** ✓

## 八、`weaponLookup_ != resolvedWeaponAssetIndex` 的**双向验证**

```cpp
if (weaponLookup_(internalName->c_str()) != resolvedWeaponAssetIndex)
{
    loadoutResolveFailure_.store(BaseWeaponLookup);
    return false;
}
```

**与 §236/§245/§249 同一手法** —— **resolver 与 lookup 两个不同函数必须一致。**

**这是本文件里的**第五次**出现**（§236 注册、§245 final verify、§249 port 注册、§252 这里）。

## 九、`SV_AlphaWeaponNetworkAssetIndex` 的**网络索引覆盖**

```cpp
const auto alphaNetworkAssetIndex = SV_AlphaWeaponNetworkAssetIndex(*internalName);
selection.baseWeaponAssetIndex = alphaNetworkAssetIndex ? *alphaNetworkAssetIndex : resolvedWeaponAssetIndex;
```

### 9.1 两个不同的索引

```text
resolvedWeaponAssetIndex      本地注册表索引
alphaNetworkAssetIndex        【网络】索引
```

**"网络索引"是发给客户端的那个** —— 而它可能不同。

**这与记忆里"武器号 1156"、"快照里武器索引"相关** —— 客户端与服务端的编号可能不一致。

### 9.2 而 `weaponName` 仍用 `*internalName`

**所以 `selection` 同时携带名字与两个索引** ✓

## 十、`auditWeaponItemsTable` 的**第三个 `call_once`**

```cpp
static std::once_flag audited;
std::call_once(audited, [this] {
    char *value = nullptr; size_t size = 0;
    if (_dupenv_s(&value, &size, "OLMOD_AUDIT_WEAPON_TABLE") == 0 && value)
    {
        const bool wanted = value[0] == '1';
        free(value);
        if (wanted) auditWeaponItemsTable();
    }
});
```

### 10.1 与 §239 的两个 `call_once` 是**同一族**

```text
§239  OLMOD_UNLOCK_ALL        ⇒ reportUnlockAllCoverage()
§239  OLMOD_AUDIT_ITEM_NAMES  ⇒ auditItemNames()（独立线程）
§252  OLMOD_AUDIT_WEAPON_TABLE ⇒ auditWeaponItemsTable()
```

### 10.2 为什么这里是**内联**而 §239 的 item names 要独立线程

```cpp
// This is the first point at which the weapon items table is certainly loaded
```

**§239 的 `auditItemNames` 是 60,249 次查找 ⇒ 阻塞 bridge 线程**
**§252 的 `auditWeaponItemsTable` 是 838 行 × 若干列 ⇒ 小得多**

**所以同一个模式在两种规模上用两种调度** —— 而这个区分是靠"规模"而不是靠"原则"。

### 10.3 注意那个空行的位置

```cpp
if (wanted)
    auditWeaponItemsTable();
}

});
```

**`}` 之后有一个空行再 `});`** —— 一处格式瑕疵（不影响语义）。

## 十一、**"别名武器没有 weapon-items 行不是失败"**

```cpp
// A WEAPON WITH NO ROW IN THE WEAPON ITEMS TABLE HAS NO DEFAULTS -- IT IS NOT A
// FAILURE. raygun_mp is absent from that table, which is exactly WHY it can never
// appear in a class screen, and refusing it here dropped the whole class and made
// UpdateLoadout fail: `default attachments unavailable for 'raygun_mp': no row for
// this weapon in the weapon items table`.
//
// NARROWED TO ALIASED WEAPONS ON PURPOSE. For an ordinary item a missing row is a
// real problem -- a mistyped name, a table that did not load -- and swallowing it
// would hide the failure this refusal was written to catch. An alias, by
// definition, names a weapon the tables do not carry.
if (!defaults && aliased) { ...; defaults.emplace(); }
if (!defaults) { store(DefaultAttachments); return false; }
```

### 11.1 三层

```text
1. `raygun_mp` 不在这张表里 ⇒ 【这正是】它永不出现在职业界面的原因
2. 在这里拒绝它 ⇒ 丢掉整个职业 ⇒ UpdateLoadout 失败
3. 修法：仅对【别名武器】容忍
```

### 11.2 那句"有意收窄"

**"对普通物品，缺行是真正的问题 —— 一个拼错的名字、一张没加载的表 —— 而吞掉它会掩盖这个拒绝本来要抓的失败。"**

**"而一个别名，按定义，命名一个表里不存在的武器。"**

**这是"例外必须显式限定范围"** —— 而不是"把拒绝放宽"。

**与 §244 里"读作 ENABLED 会加一个没人要的附件"同族：**两个方向选代价小的，但要**显式**。

## 十二、附件的**六级跳过**（本组第四重要）

```cpp
for (const auto attachmentItemId : attachmentItemIds)
{
    if (!attachmentItemId) continue;                                     // ① 空槽
    auto attachmentName = readItemInternalName(attachmentItemId);
    if (!attachmentName) { skip("has no internal name"); continue; }      // ②
    const auto slot = readAttachmentModelSlot(*attachmentName);
    if (!slot) { skip("has no model slot"); continue; }                   // ③
    auto equippedIndex = attachmentLookup_(attachmentName->c_str());
    if (!equippedIndex || equippedIndex >= 0x3FFF) { skip("is not in the attachment registry"); continue; }  // ④
    ... translate ...
    if (!attachmentSupportedByWeapon(resolvedWeaponAssetIndex, equippedIndex)) { skip("is not supported by this weapon"); continue; }   // ⑤
    if (!attachmentModelResolutionAvailable(resolvedWeaponAssetIndex, equippedIndex)) { skip("has no model for this weapon"); continue; }  // ⑥
    equipped.push_back({ .slot = *slot, .name = *attachmentName });
}
```

### 12.1 **六级全部是 `continue` 而不是 `return false`**

### 12.2 那句理由

```cpp
// AN ATTACHMENT THAT DOES NOT RESOLVE IS SKIPPED, NOT FATAL.
//
// Every one of these used to `return false`, which fails the WHOLE weapon
// and spawns the player holding nothing. That was survivable only while
// this list was always empty; section 186f's fix fills it from the profile,
// so one stale id in a five-class document would have cost the player their
// gun. Skipping costs them one attachment and says which.
```

### 12.3 三层

```text
1. 以前每一个都 `return false` ⇒ 整个武器失败 ⇒ 玩家空手 spawn
2. 这只在"列表永远为空"时可生存
3. 而 §186f 的修复从 profile 填充它 ⇒ 五职业文档里一个陈旧 id 就会让玩家丢掉枪
```

**"跳过让他们损失一个附件并说出是哪个。"**

### 12.4 与默认附件的**不对称**

```cpp
// AND THE FULL VALIDATION HAPPENS HERE, not in the merge below. The merged
// loop's attachmentLookup_ / attachmentModelResolutionAvailable checks are
// still fatal -- correctly, because a DEFAULT that cannot resolve means the
// weapon itself is wrong -- so an equipped attachment must clear those same
// two gates before it is allowed to join the list.
```

```text
装备的附件（玩家选的）   跳过不致命
默认附件（武器自带）     致命（因为解析不了说明武器本身错了）
```

**这是一个清晰的"谁的责任"划分** ✓

## 十三、翻译的**三条日志形态**

```cpp
const auto skip = [&](const char *why) {
    report("attachment skipped item=N weapon=W <why>");
};
// 而翻译成功时：
report("attachment translated item=N weapon=W -> id M");     // ← 【不是 skip】
```

### 13.1 那句自我更正

```cpp
// NOT a skip -- the attachment is being KEPT, under this weapon's
// own id. Reusing skip() here printed "attachment skipped ...
// translated to", which reads as the opposite of what happened.
```

**"复 `skip()` 会打印『attachment skipped ... translated to』，那读起来与发生的事相反。"**

**这是"日志措辞即语义"** —— 一个 `skip` 前缀在两种情形里含义相反。

## 十四、`0x3FFF` 与 §251 的 `0x3FFD`

```cpp
if (!equippedIndex || equippedIndex >= 0x3FFF) skip("is not in the attachment registry");
```

**`0x3FFF = 16383`** —— 而 §251 的 `internedAttachmentName` 用 `0x3FFD = 16381`。

**两个不同的上界** —— 而这里更宽松（16383 vs 16381）。

**所以 `equippedIndex == 16381` 或 `16382` 能通过这里，但 `internedAttachmentName(16381)` 会返回 nullopt。**

**⇒ 翻译后 `translatedName` 为 nullopt，`attachmentName` 保持**原名**（未经翻译的）。**

**而后面 `equipped.push_back({ .slot, .name = *attachmentName })` 会用**原名** —— 这正是 §252 开头说的"§187l 拒绝每颗子弹"的一个可能来源。

## 十五、关键结论

1. **三个字符串上限（128/256/512）并存**。
2. **`readWeaponDefinitionName` 的上界是 `1700`（含动态武器）**。
3. **`altWeaponAssetIndex` 的 `+3720` 与 §243 的 `+3716 → +3720` 吻合**，且界是安全边界（`Pmove` 不检查）。
4. **别名是文件驱动** —— 加武器只需编辑与重新托管，缺文件零成本。
5. **`std::stoul` 不检查全消费**，与 §243 的 `from_chars` 原则相反。
6. **"missing items" 的真义是"够不着"** —— `raygun_mp`/`thundergun_chicken_mp` 每局都加载但没有 marketplace item。
7. **`0x400 (1024) → 0x514 (1300)`** —— 276 个武器被另一个 build 的常量拒绝。
8. **`sf_weapon_m4_mp_name` 是本地化键** —— 而 `validBookingName` 会通过，所以偏移错不报错只是 resolver 失败。
9. **一次转储全部 13 个候选偏移** 击败逐个假设（"两次启动 vs 零次"）。
10. **第六次双向验证**（`weaponLookup_ != resolvedWeaponAssetIndex`）。
11. **`baseWeaponAssetIndex` 可能被"网络索引"覆盖** —— 本地索引与线上索引不同。
12. **别名武器的"无 weapon-items 行"被显式容忍** —— 而普通物品仍致命。
13. **附件六级全部 `continue`** —— 因为"一个陈旧 id 就让玩家丢枪"不可接受。
14. **装备附件宽松、默认附件严格** —— 责任划分清晰。
15. **`0x3FFF` 与 `0x3FFD` 的不一致** ⇒ 翻译后的名字可能取不到 ⇒ 用原名 ⇒ 可能触发 §187l。

## 十六、未闭合点

- `0x3FFF`（附件注册表）与 `0x3FFD`（内部名表）两个上界的不一致。
- `ItemDefinitionNameOffset` 的正确值（转储日志里 `+N=` 的 N 是答案，但这里没记录）。
- `BaseWeaponAssetCount = 0x514` 的两个 RVA 具体值。
- `EngineBindings.cpp` 14450 行之后未读取。
