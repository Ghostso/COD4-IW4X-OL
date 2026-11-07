# 501 · **"去重键【是那个**附件的名字**，而【不是【它的**槽位**"** —— `sv_weapon_loadout_mp.cpp` 的 `mag_extclip`/`mag_fmj` 同槽、`** <weapon> 0 0 <attachment...>` 的顺序即变体键、以及"1073 tag_reticle_red_dot"

## 一、范围

本报告学习 `sv_weapon_loadout_mp.cpp`（**`130` 行**）全文件：`SV_MergeWeaponAttachments` 的三段（defaults 去重 / equipped 去重 / 合并 + 排序）、两个 `std::nullopt`、以及那个 `stable_sort` 的完整理由。

## 二、**"去重键是那个附件的名字，而不是它的槽位"**（本组最重要的一段）

### 2.1 那段

```cpp
// THE DEDUPLICATION KEY IS THE ATTACHMENT'S NAME, NOT ITS SLOT.
//
// This used to keep one entry per native slot per list, and that rule is
// what the live report is about: `mag_extclip*` (扩容弹夹) and `mag_fmj*`
// (金属披甲弹) both resolve to slot 11 (`mag`, EngineBindings.cpp:3536-3538
// SlotNames), so whichever came second was dropped -- the FMJ never
// reached the weapon string and the player entered the match with the
// extended mag only. Retail puts several same-slot attachments in one
// string: m4a1techsd_mp with EQUIPPED=3 carries
//   mag_extclipm4a1techsd sto_stalkerm4a1techsd mag_fmjm4a1techsd
// and the client honours both. Section 113
// (`定因-M4实测-贴纸dec不在槽表里slot=none-且同槽去重现场复现-20261010-2930.md`).
```

### 2.2 二十四层

```text
1. **那个去重键【是【那个附件的**名字**】⇒ **⇒ 而【不是【它的**槽位**
2. ⇒ **⇒ 而这【曾【是【"每列【一个原生槽【一个条目**"**
3. ⇒ **⇒ 而那【正是【那个【现场报告的**主题**】
4. ⇒ **⇒ `mag_extclip*`（**扩容弹夹**）与 `mag_fmj*`（**金属披甲弹**）【都【解析到**槽 `11`**（`mag`）**
5. ⇒ **⇒ 所以【无论哪个【后来**都被【丢掉**】
6. ⇒ **⇒ 而那个 FMJ 【从未【到达**那个武器串**】⇒ **⇒ 而【那个玩家【进比赛时【只【有**扩容弹夹**
7. ⇒ **⇒ 而【零售【把【几个**同槽的附件【放进【一个串**】
8. ⇒ **⇒ `m4a1techsd_mp` 带 `EQUIPPED=3` ⇒ `mag_extclipm4a1techsd sto_stalkerm4a1techsd mag_fmjm4a1techsd`**
9. ⇒ **⇒ 而那个客户端【**两个都【承认**】
```

### 2.3 ⭐⭐⭐ **"mag_extclip 与 mag_fmj 都解析到槽 11，所以无论哪个后来都被丢掉"**

**✅ 这是本报告里**最重要的一条"**一个**槽位的**唯一性假设【是**错的**"**。**

**✅ 与 §471 的"打不死人 + 穿透仍无效是同一刀的两个症状"**、§483 的"`SV_LookupAltWeapon` 递了 HOST"**——**同族** ✓

**⇒ 三层**：
```text
假设 ⇒ **一个槽【一个附件**】（**⇒ 那【是【一个**直觉**的假设**）
而实际 ⇒ **一个槽【可以【有多个**】（**⇒ `mag_extclip` 与 `mag_fmj` 都【是** `mag`**）
⇒ **⇒ 所以【那个去重【丢掉了【一个**真的**附件**
```

**✅ ⭐⭐⭐ **"那个去重丢掉了一个真的附件"**。

**⚠ 而那个**现场的症状**】**。**

**⇒ 十层**：
```text
"the player entered the match with the extended mag only"
⇒ **⇒ 一个**极具体的**用户可见的症状**
⇒ **⇒ 而【它【指向【一个**去重键【的选择**
```

**✅ ⭐⭐⭐ **"一个极具体的用户可见的症状指向一个去重键的选择"** —— 与 §494 的"一个可听见的、可报告的症状指向一个名字的语义"**同族**（**第三次**）。

### 2.4 而**"强制每槽一个【从来【不是【那个保护**"**"**

```cpp
// FORCING ONE PER SLOT WAS NEVER THE PROTECTION. The protection is that a
// bad attachment costs an ATTACHMENT, never the weapon -- that is the
// `std::nullopt` the caller treats as fatal, and an exact repeat (the same
// name twice) is still dropped and counted.
```

**⇒ 十六层**：
```text
1. **"强制每槽一个"【从来【不是【那个**保护**】
2. ⇒ **⇒ 那个保护【是】：一个**坏的**附件【花掉【一个**附件**】⇒ **⇒ 而【从不【花掉【那个**武器**
3. ⇒ **⇒ 而那【就是【那个 `std::nullopt`【那个调用者【当成**致命**
4. ⇒ **⇒ 而【一个【精确的**重复**（同一个名字两次）【仍然【被丢弃【并被**计数**
```

**✅ ⭐⭐⭐ **"一个坏的附件花掉一个附件，而从不花掉那个武器"** —— 一个**极清晰的**保护**的定义**。

**✅ 与 §495 的"那个 `> 0` 是一个终止性的条件"**——**不同**，但与 §493 的"fail closed 并重试，绝不把玩家放进几何体"**同族**（**第四次"一个**成本【的**上限**"**）。

**⚠ 而"一个重复的名字【也【不是【一个**失败**"**】**。**

**⇒ 十层**：
```cpp
// A duplicate NAME is not a failure either: the first is kept, the rest are
// dropped, and `skippedDuplicateSlots` counts them.
```
```text
1. **一个重复的名字【不是**失败**】
2. ⇒ **⇒ 第一个【被**保留**】⇒ **⇒ 其余【被**丢弃**
3. ⇒ **⇒ 而 `skippedDuplicateSlots` 【计数**它们**
⇒ **⇒ 所以【三种**行为**：
     · 一个**坏**的附件 ⇒ `nullopt`（**致命**）
     · 一个**重复的名字** ⇒ 丢弃 + 计数
     · 一个**同槽但不同名** ⇒ **保留**
```

**✅ ⭐⭐⭐ **"三种行为"** —— 一个**极清晰的分级**。

**✅ 与 §496 的"杂散 token 跳过、重复名字拒绝"**——**相反**（那里**重复是拒绝**，这里**重复是计数**）**。**

**⇒ 三层**：
```text
§496  **一个命令列表的重复名字 ⇒ **拒绝**（malformed）**
§501  **一个附件的重复名字 ⇒ **丢弃 + 计数**
⇒ **⇒ 所以【同一个"重复"【两个**不同的**处理** —— **由**那个输入的语义决定**
```

**✅ ⭐⭐⭐ **"同一个『重复』两个不同的处理，由那个输入的语义决定"** —— 与 §467 的"由那个计数的用途决定"**同族**（**第三次**）。

## 三、**"按槽排序，因为那个字符串【就是【那个变体键**"**（本组第二重要）

### 3.1 那段

```cpp
// ORDERED BY SLOT, BECAUSE THE STRING IS THE VARIANT KEY.
//
// `** <weapon> 0 0 <attachment...>` is not a set -- the engine resolves the
// whole string to a weapon and builds its DObj from the order it reads. Retail
// says so directly: weapon 992's default is `** 992 0 0 9321`, and the same
// weapon with a red dot is `** 992 0 0 6206 9321` -- 6206 INSERTED BEFORE 9321,
// not appended. Weapon 646 does the same, `14268 8738 9321` against a default
// of `8738 9321`.
```

### 3.2 二十四层

```text
1. **那个字符串【不是【一个**集合**】
2. ⇒ **⇒ 因为【那个引擎【把【整个串【解析成【一个**武器**】⇒ **⇒ 并从【它【读到的**顺序【构造**那个 DObj**
3. ⇒ **⇒ 而【零售【直接**这么说**】：
4. ⇒ **⇒ 武器 `992` 的默认【是 `** 992 0 0 9321`**】
5. ⇒ **⇒ 而【同一个武器【带【一个红点【是 `** 992 0 0 6206 9321`**】
6. ⇒ **⇒ ⚠ 【`6206` 被**插入【在 `9321` 之前**】⇒ **⇒ 而【不是**追加**
7. ⇒ **⇒ 武器 `646` 【也一样**】⇒ **⇒ `14268 8738 9321` 对【一个【`8738 9321`**的默认**
```

### 3.3 ⭐⭐⭐ **"6206 被插入在 9321 之前，而不是追加"**

**✅ 这是本报告里**最精确的一条**"一个**顺序【是【那个**键**"**。**

**✅ 与 §470 的"那个顺序也被保留（`1D 1C 22 16` 不是升序）"**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **服务端专属事件表【的顺序【被**保留**】（**⇒ 一个**重排【会【破坏那个对应**）
§501  **附件串【的**顺序【是【那个**变体键**】（**⇒ 一个**追加【会【构造一个**不同的变体**
⇒ **⇒ 两次"一个**顺序【是【一个**语义**"**
```

**✅ ⭐⭐⭐ **"一个顺序是一个语义"两例**。

**⚠ 而那个**失败的模式**】**。**

**⇒ 十六层**：
```cpp
// Appending put the equipped attachment last, which built a different variant
// and bound its model to the wrong DObj part: the client faulted at spawn with
// `1073 tag_reticle_red_dot fja_bountyhunter_kitty_sc_f_vmchar` -- looking for
// the sight's tag on the VIEWMODEL CHARACTER, the player's jacket, instead of
// the weapon. Section 187.
```
```text
1. **追加【把那个装备的附件【放在**最后**】
2. ⇒ **⇒ 而【那【构造了【一个**不同的变体**】
3. ⇒ **⇒ 而【把【它的模型【绑到【一个**错的 DObj 部件**
4. ⇒ **⇒ 而【客户端【在**生成时【故障**】⇒ **⇒ `1073 tag_reticle_red_dot fja_bountyhunter_kitty_sc_f_vmchar`**
5. ⇒ **⇒ 而【那【是在【那个**视图模型角色**（**那个玩家的夹克**）上【找那个瞄具的 tag**】⇒ **⇒ 而不是【在【那个**武器**上**
```

**✅ ⭐⭐⭐ **"在那个视图模型角色（那个玩家的夹克）上找那个瞄具的 tag，而不是在那个武器上"** —— 一个**极精确的故障**。

**✅ 与 §471 的"那个武器索引走进了一个事件字段"**、§489 的"一个动态实体号走进了一个尸体槽"**——**同族** ✓

**⇒ 三层**：
```text
§481  **一个武器索引【走进【一个**事件字段**
§489  **一个动态实体号【走进【一个**尸体槽**
§501  **一个瞄具的 tag【被【在【一个**夹克**上【找**
⇒ **⇒ 三次"一个**错的值【在【一个错的**主体【上【但【仍然**合法**
```

**✅ ⭐⭐⭐ **"一个错的值在一个错的主体上但仍然合法"三例表**。

**⚠ 而"`stable_sort` 而不是 `sort`"**】**。**

**⇒ 十层**：
```cpp
// Sorting the merged list rather than only the equipped half, so defaults and
// equipped share one rule and the answer does not depend on which half a
// given attachment arrived in.
std::stable_sort(result.begin(), result.end(),
    [](const NamedWeaponAttachment &left, const NamedWeaponAttachment &right) {
        return left.slot < right.slot;
    });
```
```text
1. **`stable_sort` 【保持【同槽【的**原始顺序**】
2. ⇒ **⇒ 所以【两个**同槽的附件（`mag_extclip` 与 `mag_fmj`）【保持【它们【在 defaults/equipped 里的**相对顺序**
3. ⇒ **⇒ 而 `sort` 【会【让【那个顺序【不**确定**
```

**✅ ⭐⭐⭐ **"stable_sort 保持同槽的原始顺序"** —— 而**那【是【那个 `mag_extclip`/`mag_fmj` 场景【的**关键**（**两个都【在槽 `11`**）**。**

**✅ 与 §470 的"`std::ranges::sort` 用于 label"**——**不同**（那里**不需要稳定**，因为**唯一**）**。**

**⇒ 三层**：
```text
§466  **`std::ranges::sort(result, {}, &SvSdBombSite::label)`**（**⇒ 唯一 ⇒ 不需要稳定**）
§501  **`std::stable_sort`**（**⇒ 同槽重号 ⇒ 需要稳定**）
⇒ **⇒ 所以【那个**选择【是【由【那个**键的唯一性**决定的**
```

**✅ ⭐⭐⭐ **"那个选择是由那个键的唯一性决定的"**。

## 四、那个 `equippedSlots` 的"仍然按槽追踪"

### 4.1 那段

```cpp
// STILL TRACKED PER SLOT, because this set -- not the name list -- is
// what suppresses the weapon's own default in that slot below.
equippedSlots[attachment.slot] = true;
```

### 4.2 二十四层

```text
1. **那个 `equippedSlots` 【仍然【被【按槽**追踪**
2. ⇒ **⇒ 因为【那个集合【（**不是【那个名字表**）【是【抑制【那个武器【自己的**默认【在那个槽上**的东西**
3. ⇒ **⇒ 所以【一个**装备的枪口【仍然【替换【那个武器【自己的**枪口**】⇒ **⇒ 即使【两个名字**不同**
```

### 4.3 ⭐⭐⭐ **"一个装备的枪口仍然替换那个武器自己的枪口，即使两个名字不同"**

**✅ 与 §501 二 的"去重键是名字而不是槽位"**——**一个精确的**分工** ✓

**⇒ 三层**：
```text
去重 ⇒ **按名字**（**⇒ 同名的丢掉**）
抑制默认 ⇒ **按槽**（**⇒ 同槽的替换掉那个默认**）
⇒ **⇒ 所以【两个**不同的**规则【用在【两个**不同的**目的上**
```

**✅ ⭐⭐⭐ **"两个不同的规则用在两个不同的目的上"** —— 而**那【是【那个**正确的**设计**。**

**✅ 与 §467 的"一个映射两种用法"**——**同族**（**第四次"一个**同一份数据【的**两个规则**"**）。

## 五、两个 `std::nullopt`

### 5.1 两个

```text
① `!validate(attachment)` ⇒ `nullopt`（**⇒ 一个坏槽位或一个空名字**）
② `result.size() > MaximumModularWeaponAttachmentCount` ⇒ `nullopt`
```

### 5.2 二十四层

```text
1. **两个**致命**【两种情况**】
2. ⇒ **⇒ ① 一个**坏**的附件【（**槽位【不在 `1..15`**，或【名字**空**）**
3. ⇒ **⇒ ② 那个合并后的列表【超过**那个上限**
4. ⇒ **⇒ 所以【那个"一个坏的附件【花掉【一个**附件**"的保护【是【在【那个**调用者**那层**】（**不是【这里**）
```

### 5.3 ⭐⭐⭐ **"那个保护是在那个调用者那层，不是这里"**

**✅ 与 §499 的"那个 `Missed` 是一个独立的返回值，而那个调用者【把它【当成**正常**"**——**同族** ✓

**⇒ 三层**：
```text
这里 ⇒ **`nullopt` ⇒ 那个调用者【当成**致命**
而【那个"一个坏的附件【花掉【一个**附件"【的细节【在【那个**调用者【（`sv_client_spawn` 的 `equipResolvedLoadout`？**）
⇒ **⇒ 所以【那一层【的契约【是【"全有全无**"**
```

**✅ ⭐⭐⭐ **"那一层的契约是全有全无"** —— 而**§501 二 的注释【说的"`std::nullopt` 那个调用者【当成**致命**"**】正是它**。**

**⚠ 而那个 `validate` 的 `slot > 0 && slot < WeaponAttachmentSlotCount`**】**。**

**⇒ 十层**：
```text
`slot > 0` ⇒ **⇒ 所以 `slot 0` 【是【无效的**】（**一个**保留**的槽**）
`slot < WeaponAttachmentSlotCount` ⇒ **⇒ 所以【那个上界【是【那个**数组大小**
⇒ **⇒ 而【那【正是【§476 的"`16383` 是一个保留值"**同族**（**第五次"一个**0 【是【一个**保留**的值**））
```

**✅ ⭐⭐⭐ **"slot 0 是一个保留的值"**。

## 六、关键结论

1. **⭐⭐⭐ "那个去重键是那个**附件的名字**，而不是它的**槽位**"`**：**"`mag_extclip*`（扩容弹夹）与 `mag_fmj*`（金属披甲弹）都解析到槽 11（`mag`），所以无论哪个后来都被丢掉 —— 那个 FMJ 从未到达那个武器串，而那个玩家进比赛时只有扩容弹夹"** ⇒ **"那个去重丢掉了一个真的附件"**；而**零售把几个同槽的附件放进一个串**（`m4a1techsd_mp` 带 `EQUIPPED=3` ⇒ `mag_extclipm4a1techsd sto_stalkerm4a1techsd mag_fmjm4a1techsd`）。
2. **⭐⭐⭐ "强制每槽一个从来不是那个保护。那个保护是：一个**坏的附件花掉一个附件，而从不花掉那个武器** —— 那就是那个 `std::nullopt` 那个调用者当成致命"`** ⇒ 而**那个保护是在那个调用者那层，不是这里**（这里**`nullopt` 就是一个全有全无的契约**）。
3. **⭐⭐⭐ 三种行为**：**一个坏的附件 ⇒ `nullopt`（致命）；一个重复的名字 ⇒ 丢弃 + 计数（`skippedDuplicateSlots`）；一个同槽但不同名 ⇒ 保留** ⇒ 与 §496 的"重复名字拒绝"**相反**（**"同一个『重复』两个不同的处理，由那个输入的语义决定"**）。
4. **⭐⭐⭐ "按槽排序，因为那个字符串就是那个变体键 —— `** <weapon> 0 0 <attachment...>` 不是一个集合，那个引擎把整个串解析成一个武器并从它读到的顺序构造那个 DObj；武器 `992` 的默认是 `** 992 0 0 9321`，而同一个武器带一个红点是 `** 992 0 0 6206 9321` —— **`6206` 被插入在 `9321` 之前，而不是追加**；武器 `646` 也一样（`14268 8738 9321` 对一个 `8738 9321` 的默认）"`** ⇒ **"一个顺序是一个语义"**（与 §470 同族）。
5. **⭐⭐⭐ 那个失败的模式**：**"追加把那个装备的附件放在最后，构造了一个不同的变体，而把它的模型绑到一个错的 DObj 部件：客户端在生成时故障 `1073 tag_reticle_red_dot fja_bountyhunter_kitty_sc_f_vmchar` —— **在那个视图模型角色（那个玩家的夹克）上找那个瞄具的 tag，而不是在那个武器上**"`** ⇒ **"一个错的值在一个错的主体上但仍然合法"**（第三次，与 §481/§489 同族）。
6. **⭐⭐⭐ `std::stable_sort` 而不是 `sort`** ⇒ **"stable_sort 保持同槽的原始顺序"** —— 而那正是 `mag_extclip`/`mag_fmj` 场景的关键（**两个都在槽 11**）⇒ **"那个选择是由那个键的唯一性决定的"**（与 §466 的 `ranges::sort` 对照：那里 label 唯一所以不需要稳定）。
7. **⭐⭐⭐ "排序合并后的列表而不是只排装备的那一半，所以 defaults 与 equipped 共享一个规则，而那个答案不依赖给定附件从哪一半到达"`** ⇒ 一个**极重要的对称性**。
8. **⭐⭐⭐ `equippedSlots` 仍然被按槽追踪**：**"因为这个集合（不是那个名字表）是抑制那个武器自己的默认在那个槽上的东西"`** ⇒ **"一个装备的枪口仍然替换那个武器自己的枪口，即使两个名字不同"** ⇒ **"两个不同的规则用在两个不同的目的上"**（去重按名字，抑制默认按槽）。
9. **⭐⭐ `validate` 的 `slot > 0`** ⇒ **"slot 0 是一个保留的值"**（与 §476 的"`16383` 是一个保留值"同族）。

## 七、`sv_weapon_loadout_mp.cpp` 全文件总览

**`130` 行。**

**`1` 个函数**：`SV_MergeWeaponAttachments`。

**`5` 步**：defaults 校验 + 名字去重 ⇒ equipped 校验 + 名字去重 + 槽标记 ⇒ 合并（抑制同槽默认）⇒ `stable_sort` 按槽 ⇒ 上限检查。

**`3` 个锚点**：
```text
EngineBindings.cpp:3536-3538  SlotNames（slot 11 = mag）
m4a1techsd_mp EQUIPPED=3 的实际串
weapon 992 / 646 的默认串与带红点的串
1073 tag_reticle_red_dot fja_bountyhunter_kitty_sc_f_vmchar
```

**`1` 个中文源文件名**：`定因-M4实测-贴纸dec不在槽表里slot=none-且同槽去重现场复现-20261010-2930.md`（**§113**）。

## 八、未闭合点

- `WeaponAttachmentSlotCount` 的值（`slot 0` 保留 ⇒ 至少 `16`）。
- `MaximumModularWeaponAttachmentCount` 的值。
- 那个 `validate` 失败时的 `nullopt` 是在哪个调用者处变成"一个坏附件花掉一个附件"的。
- 下一个文件：`sv_native_pmove_mp.cpp/.hpp`（`5,902` / `5,911`）。
