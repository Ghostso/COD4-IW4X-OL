# 253 · `** <weapon> 0 0 <ids>` 的实测对照、FMJ 的名字才是唯一来源、注册表计数前后的依赖窗口

## 一、范围

本报告学习 `EngineBindings.cpp` 14450–14755 行。

## 二、`SV_MergeWeaponAttachments` 的**重复槽**

```cpp
std::size_t skippedAttachmentDuplicates = 0;
const auto effectiveAttachments = SV_MergeWeaponAttachments(
    *defaults, equipped, &skippedAttachmentDuplicates);
if (skippedAttachmentDuplicates != 0)
{
    write("attachment merge: dropped N duplicate-slot attachment(s) weapon=W "
          "(kept the first per slot; the weapon is still registered)");
}
```

### 2.1 三句

```text
1. 重复槽【不再丢掉整个武器】
2. 每个槽【保留第一个】
3. 而且明说"武器仍然被注册"
```

### 2.2 那句"这是本可以命名『武器拿不出来』的那一行"

```cpp
// This is the line that would have named
// "the weapon cannot be taken out".
```

**"武器拿不出来"** —— 一个真实的玩家症状。

**与 §156 里"配件按名字去重而不是按槽"（`mag_extclip` + `mag_fmj` 都是 11 号槽）是同一个问题的两面：**

```text
§156  两个附件【名字】不同但【槽】相同 ⇒ 必须都保留（按名去重）
§253  两个装备附件在【同一个原生槽】⇒ 只能留一个 ⇒ 记录下来
```

**注意 §156 里"按名去重"是 `readDefaultWeaponAttachments` 层面，而这里的"按槽去重"是合并层面** —— 两个不同的去重维度。

## 三、**FMJ 的发现方式**（本组重要）

```cpp
// 28700 (FMJ): the merged attachment NAME list is the only place this
// server knows "the player attached FMJ" -- the modular string carries
// asset ids, not names, and the operator's rule is concrete:
// "普通穿透是 1，装上 FMJ 就是 2". The bullet path doubles the material
// depth when this flag is set; no second table is involved.
selection.fmjPenetration = false;
for (const auto &attachment : *effectiveAttachments)
{
    if (attachment.name.rfind("mag_fmj", 0) == 0) { selection.fmjPenetration = true; break; }
}
```

### 3.1 三层

```text
1. 模块化串只携带【资产 id】不带名字
2. ⇒ 合并后的【名字列表】是唯一知道"玩家装了 FMJ"的地方
3. 操作者的规则很具体："普通穿透是 1，装上 FMJ 就是 2"
```

### 3.2 而**子弹路径直接加倍材质深度**

**"没有第二张表参与"** —— 所以这是一个**硬编码规则**。

### 3.3 `rfind("mag_fmj", 0) == 0` 是 **starts_with**

**用 `rfind(prefix, 0) == 0` 而不是 `starts_with`** —— 这是 C++20 之前的写法。

**而 §252 里用了 `line.starts_with('#')`** ⇒ **同一个文件里两种写法并存**。

### 3.4 前缀 `mag_fmj` 的两个已知变体

**§156 学到 `mag_extclip` 与 `mag_fmj` 都是 11 号槽** —— 所以它们是**同一类附件（弹匣）的两个属性**。

**而 `mag_fmj` 前缀匹配会命中 `mag_fmj`、`mag_fmj_extclip` 等** ✓

## 四、模块化串的**三个实测样本**（本组最重要的一段）

```cpp
// THE STRING WE PUBLISH, SAID OUT LOUD, because it is the whole weapon
// attachment channel and nothing has ever printed it. Retail's own, read out
// of the dm demo at cs 7184.. (= WeaponConfigStringBase 5960 + the
// firstDynamicWeapon 1224 this server prints every match):
//
//     ** 682 0 0 9930 8738 6747 10545 9321 6690 6825
//     ** 652 0 0 8738
//     ** 249 0 0                          <- a weapon with no attachments
//
// So the format is `** <weapon> <n> <n> <attachment...>` and the question this
// line answers is whether OUR trailing numbers look like retail's. Deduped, so
// a stable loadout prints once per distinct weapon.
```

### 4.1 格式

```text
** <weapon> <n> <n> <attachment...>
```

**三个样本**：

```text
** 682 0 0 9930 8738 6747 10545 9321 6690 6825      ← 七个附件
** 652 0 0 8738                                    ← 一个附件
** 249 0 0                                         ← 无附件
```

### 4.2 **`cs 7184 = 5960 + 1224`**

```text
WeaponConfigStringBase = 5960
firstDynamicWeapon      = 1224
7184 = 5960 + 1224
```

**这是一个算术恒等式** —— 把 §236 的三个常量联系在一起 ✓

**"这个服务器每局都打印"** —— 所以 1224 是一个稳定值。

### 4.3 `0 0` 的两个零

**注释没有解释** —— 但从 §240 里 class 块的 37 序号布局看，`**` 之后的第二与第三个字段可能是 `class` 与 `slot`。

**而这里恒为 `0 0`** —— 所以我们**从不设置它们**。

### 4.4 我们的串

```cpp
std::string modularName = "** " +
    std::to_string(selection.baseWeaponAssetIndex) + " 0 0";
for (const auto &attachment : *effectiveAttachments)
    modularName += " " + std::to_string(attachmentIndex);
```

**所以我们的格式**：

```text
** <baseWeaponAssetIndex> 0 0 <attachment ids...>
```

### 4.5 **代码里那个"字节相同"的实测**

```cpp
// WHY THE SPLIT MATTERS. Our `** 646 0 0 8738 9321` and
// `** 992 0 0 9321` are BYTE-IDENTICAL to retail's cs 7184 and
// cs 7204, so the format and the ids are right. But retail also
// publishes `** 992 0 0 6206 9321`, `** 646 0 0 14268 8738 9321`
// and `** 534 0 0 9930 4415 5153 8738 6747 10545` -- EVERY
// ATTACHMENT COMBINATION IS ITS OWN WEAPON STRING, and those
// variants carry ids ours never produce. Matching retail's
// DEFAULT variant exactly is what publishing defaults-only looks
// like, so the number that decides it is EQUIPPED, not the total.
```

### 4.6 六个串

```text
我们的  ** 646 0 0 8738 9321          = retail cs 7184  【逐字节相同】
我们的  ** 992 0 0 9321               = retail cs 7204  【逐字节相同】
零售的  ** 992 0 0 6206 9321          ← 6206 是 TMP 红点（§252）
零售的  ** 646 0 0 14268 8738 9321    ← 14268 是 M9 红点（§252）
零售的  ** 534 0 0 9930 4415 5153 8738 6747 10545
```

**前两个逐字节相同** ⇒ **格式与 id 都对**。

**而后三个带着"我们从不产出"的 id** ⇒ **说明我们只发了默认，没发玩家选择。**

### 4.7 那段核心洞察

**"每一种附件组合都是它自己的武器串。"**

**⇒ 所以"与零售的默认变体逐字节相同"** 恰好是"只发默认"的样子**。**

**⇒ 决定性的数字是 `EQUIPPED` 而不是总数。**

**这是一个非常好的判据设计** —— 因为"逐字节相同"这个最强的一致性证据在这里**反而是失败的症状**。

**与记忆里的 `141 字节 = 真 Python 参照的首帧 = 让客户端卡住的那一份` 是同一类教训**：

> 「与参照逐字节一致」对这个加壳客户端是已知死路

**这里是它的第二次出现（在不同子系统）。**

### 4.8 而 `6206` 与 `14268` 正是 §252 的两个翻译例

**"6206 for a TMP's red dot, 14268 for an M9's, both model 17"**

**⇒ 零售把同一个通用红点在不同武器上写成不同的 id，而我们如果不翻译就会写错。**

## 五、`table=` 的诊断（本组第二重要）

```cpp
// THE TABLE ITSELF, AS TEXT. defaultsInTable came back 0/1, 0/4 and
// 1/3 with tableCount 10..19 -- the tables are populated and the
// weapons' OWN DEFAULTS are missing from them, which can only mean
// the key we compute is not the key they are stored under.
//
// sub_42F910 interns dword_198B8A0[model]->name -- the attachment
// MODEL's name -- so the low half is an interned name id, not an
// attachment index.
```

### 5.1 三次实测

```text
defaultsInTable = 0/1   而 tableCount = 10..19
defaultsInTable = 0/4
defaultsInTable = 1/3
```

**"表是填充的（10..19 项），而武器自己的默认附件不在里面。"**

### 5.2 结论

**"这只可能意味着我们计算的键不是它们存储时用的键。"**

### 5.3 **低半部是 interned name id 而不是附件索引**

```text
sub_42F910 interns dword_198B8A0[model]->name -- the attachment MODEL's name
⇒ 低半部 = interned name id（一个字符串 id）
不是 = attachment index（一个附件编号）
```

### 5.4 这意味着 §251/§252 的**`attachmentSupportedByWeapon` 可能一直错**

```cpp
find_if(mappings, mappings + *mappingCount, [attachmentIndex](uint32 v) {
    return (uint16)v == attachmentIndex;         // ← 比较【低半部】与 attachmentIndex
});
```

**如果低半部是 interned name id 而 `attachmentIndex` 是 `attachmentLookup_` 返回的索引，那两者是**不同空间**的数。**

**⇒ 比较永远不相等 ⇒ "不被支持" ⇒ 玩家的附件全被跳过。**

**这解释了 `defaultsInTable` 的 0/1、0/4！**

**⚠ 但注意 §252 里 `attachmentIdForWeapon` 也做同样的比较，而且它**成功过**（"translated item=... -> id ..." 日志在 §252 里被描述为会发生）。**

**所以两个可能**：

```text
A. `attachmentLookup_` 返回的【就是】interned name id（两个空间相同）
B. 低半部是 name id，但与 `attachmentIndex` 的比较是错的
```

**而注释明确说"低半部是 interned name id，不是附件索引"** —— 所以 B。

**⇒ 这是一处**已知的、未修复的**不一致** —— 而注释是"把它打印出来而不是猜"。

### 5.5 那段打印代码

```cpp
const auto *const mappings = (const uint32*)(module_ + AttachmentMappingsRva) + resolvedWeaponAssetIndex * 64;
const auto *const interned = (const char *const *)(module_ + InternedStringTableRva);
for (entry < count && entry < 12)
{
    const auto nameId = (uint16)mappings[entry];
    const auto *const slot = interned + nameId;
    text = *slot;                                  // ← 用 nameId 索引字符串表
    out += " " + nameId + ":" + text.substr(0,24) + "->" + (mappings[entry] >> 16);
}
```

### 5.6 格式

```text
<nameId>:<名字前24字符>-><model>
```

**所以这个日志**证明**"低半部确实是 interned name id"** —— 因为 `interned[nameId]` 能读到合理字符串。

**这是一个"自证"的日志** —— 它同时打印了"假设"与"验证"。

### 5.7 `entry < 12` 的封顶

**只打前 12 项** —— 因为 `count` 可能 10..19。

## 六、`defaultsInTable` 的计算

```cpp
std::size_t found = 0;
for (const auto &attachment : *defaults)
{
    const auto index = attachmentLookup_(attachment.name.c_str());
    if (index && attachmentSupportedByWeapon(resolvedWeaponAssetIndex, index)) ++found;
}
return found + "/" + defaults->size();
```

**对每个**默认附件**：`attachmentLookup_` + `attachmentSupportedByWeapon`。**

**而 §252 里 `readDefaultWeaponAttachments` 返回的是 `{slot, name}`** —— 而 `slot` 来自 `parseWeaponAttachmentSlot`。

**所以默认附件的 `slot` 是一个**槽编号**，而 `name` 是 string。**

**⇒ 两个不同的标识符在同一个结构里。**

## 七、注册表计数的**依赖窗口**（本组第三重要）

```cpp
const auto *registryCount = (const uint32*)(module_ + WeaponRegistryCountRva);
if (!readableSpan(registryCount, 4) || *registryCount >= WeaponConfigStringCount(1700))
{ store(ModularWeaponDependency); return false; }
const auto registryCountBefore = *registryCount;

// ... 构建 modularName ...

const auto modularWeaponAssetIndex = weaponResolver_(modularName.c_str(), nullptr);
if (!modularWeaponAssetIndex || modularWeaponAssetIndex > MaximumWeaponAssetIndex ||
    weaponLookup_(modularName.c_str()) != modularWeaponAssetIndex)
{ store(ModularWeaponResolver); return false; }

const auto registryCountAfter = *registryCount;
if (registryCountAfter < registryCountBefore ||
    registryCountAfter >= WeaponConfigStringCount ||
    modularWeaponAssetIndex > registryCountAfter)
{ store(ModularWeaponDependency); return false; }

std::vector<SvModularWeaponConfigString> discoveredDependencies;
for (auto index = registryCountBefore + 1; index <= registryCountAfter; ++index)
{
    if (index == modularWeaponAssetIndex) continue;
    ... readWeaponDefinitionName(index) → SV_ParseModularWeaponConfigString ...
    discoveredDependencies.push_back(*dependency);
}
```

### 7.1 四项

```text
① 注册表计数 in [0, 1700)
② 解析模块化串 ⇒ 新 index
③ 计数必须【不减】、仍在界内、且新 index <= 计数
④ (before, after] 区间里的每一个新条目都是依赖，除新 index 本身
```

### 7.2 **这是一个"副作用测量"的手法**

**解析一个模块化武器串会在注册表里**追加多个 WeaponDef**（它的附件依赖）。**

**⇒ 通过"解析前计数"与"解析后计数"的差集得到依赖列表。**

**这是本文件里唯一一处"用全局计数器的增量来发现新增项"的地方。**

### 7.3 而 ③ 的三项检查

```text
after >= before           计数不能减（减说明发生了重置）
after < 1700              仍在界内
newIndex <= after         新条目必须在计数之内
```

**"计数减少"是可能的** —— 因为 `ensureWeaponRegistryInitialized` 会 reset（§245）。

**⇒ 如果在这中间发生了 reset，`after < before` ⇒ 无依赖窗口（不可能）或重置发生（无依赖）** —— 代码把它判为**失败**。

**这是一个正确的防御** —— 因为重置意味着 `modularWeaponAssetIndex` 可能已经失效。

### 7.4 而依赖缓存

```cpp
if (!discoveredDependencies.empty())
    modularDependencyCache_.insert_or_assign(modularName, discoveredDependencies);
const auto cachedDependencies = modularDependencyCache_.find(modularName);
if (cachedDependencies != modularDependencyCache_.end())
    selection.modularDependencies = cachedDependencies->second;
```

### 7.5 **两段用一个 `modularName` 作键**

```text
写入：只在非空时
读取：无条件（所以空列表【不】覆盖缓存）
```

**这是一个有意的"空不覆盖"** —— 因为"这次没发现依赖"可能是因为它已经在注册表里了（第二次解析同一个串）。

**⇒ 缓存保留第一次的结果。** ✓ 合理。

## 八、**alpha 的 `1154 vs 1234` 分裂**（本组第四重要）

```cpp
// The dedicated's map reset moves its private barrett_mp base from
// 1234 to 1154, while the client keeps Barrett at 1234 and has
// chicken_melee_mp at 1154. Session preparation already resolved the
// canonical Barrett variant before that reset, when both processes
// agreed on 1234. Reuse that retained dynamic WeaponDef afterwards.
// Building a fresh "** 1154" is correct only inside the dedicated and
// sends the client a fully functional knife; building a new
// "** 1234" after reset would inherit the dedicated's now-unrelated
// killstreak WeaponDef. If the proven canonical variant disappeared,
// refuse the loadout instead of constructing either wrong weapon.
if (alphaNetworkAssetIndex &&
    *alphaNetworkAssetIndex != resolvedWeaponAssetIndex &&
    !weaponLookup_(modularName.c_str()))
{ ... store(ModularWeaponDependency); return false; }
```

### 8.1 四个数字与两个进程

```text
专用服 reset 前    barrett_mp = 1234
专用服 reset 后    barrett_mp = 1154
客户端             barrett_mp = 1234，chicken_melee_mp = 1154
```

### 8.2 **同一个号 1154 在两个进程里是两把枪**

```text
专用服 1154  = barrett_mp（重置后）
客户端 1154  = chicken_melee_mp（刀）
```

### 8.3 两个错误选项

```text
新建 "** 1154"  ⇒ 只在专用服里正确；发给客户端 = 【一把完全能用的刀】
新建 "** 1234"  ⇒ reset 后会继承专用服【已经不相关的】连杀 WeaponDef
```

### 8.4 而正确做法是**复用**

**"会话准备已经在 reset 之前解析了规范 Barrett 变体，当时两个进程都同意 1234。之后复用那个保留的动态 WeaponDef。"**

**⇒ 如果它消失了，就**拒绝**这个 loadout，而不是造出两把错枪之一。**

**这是"宁可失败也不造错"的第二次出现** —— 与 §244 里"读作 NOT enabled 至多漏一个部件"同族。

### 8.5 而判据是 `!weaponLookup_(modularName)`

**"那个规范变体还在吗"** —— 用名字查一次。

## 九、最终 `readWeaponDefinition` 的**重新读取**

```cpp
// The resolver above has now built the equipped modular WeaponDef.
// The fields copied before attachment assembly belong to the base
// weapon, so retaining them makes authoritative fire ignore every
// attachment modifier (spread, damage, timing, ammo, and ADS). Read
// the completed definition back from its registered slot so native
// prediction and the source server fire path use the same weapon.
if (!readWeaponDefinition(modularWeaponAssetIndex, selection))
{ store(WeaponDefinition); return false; }
selection.weaponAssetIndex = modularWeaponAssetIndex;
```

### 9.1 五类被覆盖的字段

```text
spread
damage
timing
ammo
ADS
```

**"保留它们会让权威开火忽略每一个附件修改器。"**

### 9.2 这是一个**时序正确性**问题

```text
错误顺序：读基础武器 → 组装附件 → 用基础武器的字段
正确顺序：组装附件 → 从模块化槽重新读 → 用模块化武器的字段
```

**而 `readWeaponDefinition` 在 §240 里被学过 —— 它读 25 个字段 + 边界检查。**

**所以这里**整体重读一次**而不是"合并增量"。**

### 9.3 两次读的比较

```text
第一次（§252 之前，在 resolveWeaponRequest 里）  读基础武器
第二次（这里）                                   读模块化武器
```

**而 `selection.attachmentItemIds` 在 §252 里被设为 `request.attachmentItemIds`** —— 所以附件**原始 id** 也被保留 ✓

## 十、`resolveSessionPerks` 的四项前置

```cpp
if (!valid(request) || classIndex >= request.classes.size() ||
    !(request.classMask & (1u << classIndex)))
    return nullopt;

SvResolvedPerks result;
result.itemIds = request.classes[classIndex].perkItemIds;
if (all_of(result.itemIds, [](auto item) { return item <= 1; }))
    return result;                            // ← 【全 <= 1 ⇒ 直接返回，不查表】
```

### 10.1 那个"全 <= 1 就不查表"

**"0 = 空，1 = 特殊哨兵"** —— 所以"全 <= 1"意味着"没有真技能"。

**⇒ 跳过表查找** ✓ 一个廉价的快速路径。

### 10.2 `perk` 的位集布局

```cpp
// CODREF(1649370): sub_413980 looks up column 1 (canonical name),
// reads column 0 (decimal bit index), and rejects indices >= 96.
// sub_4442E0 sets ps+0x584 + 4*(index>>5), bit (index&31).
// The row ordinal is NOT the perk index.
```

```text
sub_413980    列 1 = 规范名，列 0 = 十进制位索引，拒绝 >= 96
sub_4442E0    ps+0x584 + 4*(index>>5), bit (index&31)
```

**⇒ 3 个 uint32（96 位）的位集在 `ps+0x584`。**

### 10.3 那句"行序号不是技能索引"

**"The row ordinal is NOT the perk index."** —— 与 §144 里"表格行号不是下标"同族。

### 10.4 三个外部佐证

```text
BO1 BG_SetPerk 0x60E0E0
Ghosts PlayerCmd_SetPerk 0x14011A760
```

**"确认位集所有权；它们的技能数量与 player-state 偏移都不同。"**

**这是一个"跨 build 参照只在语义上成立"的例子** —— 而具体数值不同。

## 十一、关键结论

1. **重复槽只丢一个附件、不丢武器**，且明说"武器仍被注册"。
2. **FMJ 只能从合并后的**名字列表**发现** —— 因为模块化串只有 id。
3. **`cs 7184 = 5960 + 1224`** —— 一个把 §236 三个常量联系起来的恒等式。
4. **我们的 `** 646 0 0 8738 9321` 与零售 cs 7184 逐字节相同，而这正是"只发默认"的症状** —— "逐字节相同"在这里是失败证据。
5. **决定性的数字是 `EQUIPPED` 而不是总数**。
6. **`defaultsInTable` 的 0/1、0/4 说明表的键不是我们计算的键**。
7. **低半部是 interned name id 而不是附件索引** —— §251/§252 的 `attachmentSupportedByWeapon` 可能一直在做跨空间的比较。
8. **`table=` 日志自证了这个判断**（`interned[nameId]` 能读到合理字符串）。
9. **依赖发现靠"注册表计数的增量"** —— 本文件唯一一处这种手法。
10. **计数减少被判为失败** —— 因为 reset 意味着新索引失效。
11. **依赖缓存"空不覆盖"** —— 第二次解析无新依赖时保留第一次的。
12. **`1154` 在专用服是 Barrett、在客户端是 `chicken_melee_mp`（刀）** —— 同一个号两把枪。
13. **复用保留变体 vs 造两把错枪之一 ⇒ 选择"拒绝"**。
14. **最终必须从模块化槽**重读**整个 WeaponDef** —— 否则附件修改器全被忽略。
15. **技能的位集是 96 位在 `ps+0x584`**，而行序号不是索引。

## 十二、未闭合点

- **`attachmentSupportedByWeapon`/`attachmentIdForWeapon` 是否一直在做跨空间比较**（`attachmentLookup_` 返回的到底是什么）。
- `defaultsInTable` 的正确计算方式（若低半部是 name id，则应按 name id 比较）。
- `**` 串的 `0 0` 两个字段的语义。
- `EngineBindings.cpp` 14850 行之后未读取。
