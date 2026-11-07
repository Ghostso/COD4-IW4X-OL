# 315 · **"最窄的真于两个 build 的测试"**、`0x3FF/0x3FE/0x7FF` 各窄一位（第七次）、`SV_FindResolvedWeaponOrAlt` 的 `scratch`

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 400–600 行。

## 二、**`validCharacterCustomization` 的"最窄判据"**（本组最重要的一段）

### 2.1 那段四层修正

```php
// A CUSTOMIZATION HAS TO CARRY A CHARACTER IDENTITY, AND THIS BUILD
// CARRIES IT IN A DIFFERENT FIELD FROM 3.3.3.3.
//
// This used to demand a non-zero selectionId, full stop. On OLfinal
// they are ALWAYS zero -- CharacterSelectionResolve is absent
// (section 16a) and the server says so on every spawn -- so the
// refusal fired for every client, clientInfos.push_back never ran,
// and NO clientInfo was ever sent to anyone. Measured downstream by
// Tools/olfinal/podium-slot.py: clientInfoGate 1 (the record exists,
// because names and scores come from the separate scoreboard array)
// with every model field zero -- +8 +124 +144 +148 +156 +160 and
// +960..+976 -- which is why the podium draws cards and no figures.
```

### 2.2 七层

```text
1. **一个定制化必须携带一个角色身份**
2. ⇒ 而这个 build **在一个与 3.3.3.3 不同的字段里**携带它
3. ⇒ 过去它**要求一个非零的 `selectionId`，就这样**
4. ⇒ **而在 OLfinal 上它们【总是】零** —— `CharacterSelectionResolve` 缺席（§16a）
5. ⇒ 所以**这个拒绝对每一个客户端都触发**
6. ⇒ **`clientInfos.push_back` 从不运行** ⇒ **没有任何 clientInfo 曾被发给任何人**
7. ⇒ **`Tools/olfinal/podium-slot.py` 测量到：`clientInfoGate 1`（记录存在，因为名字与分数来自【分开的计分板数组】）而每一个模型字段为零**
      —— `+8`、`+124`、`+144`、`+148`、`+156`、`+160` 与 `+960..+976`
8. ⇒ **这就是为什么领奖台画卡片而不画人**
```

### 2.3 **`clientInfoGate 1` 而模型字段全零**

**⇒ 三层**：

```text
1. `clientInfoGate = 1` ⇒ **记录存在**
2. ⇒ 因为**名字与分数来自分开的计分板数组**
3. ⇒ 而**模型字段全零** ⇒ 所以**卡片有人名而没有人**
```

**✅ 一个**完美的"数据存在但渲染缺失"**症状。**

**⇒ 与 §300 的"一个客户端写空模型名"同族。**

### 2.4 而**七个模型字段的偏移**

```text
+8, +124, +144, +148, +156, +160, +960..+976
```

**⇒ 六个标量 + 一个范围（`+960..+976` 是 16 字节 = 4 个 dword）。**

**⇒ 与 §309 的 `optionMask[12]`（48 字节）不同 —— 这里是 16 字节。**

### 2.5 而"**这段只应用于一个替换了它的宿主**"

```php
// So the old test was 3.3.3.3's shape applied to a
// host that replaced it -- the same leftover as
// ClientInfoExplicitModelFieldFirst = 46, which is defined in this
// file and referenced nowhere.
```

### 2.6 三层

```text
1. ⇒ 所以**旧的测试是 3.3.3.3 的形状应用到一个替换了它的宿主上**
2. ⇒ **与 `ClientInfoExplicitModelFieldFirst = 46` 是同一个遗留物**
3. ⇒ **它在这个文件里被定义而【无处被引用】**
```

**✅ 一段**已死的常量**被明确标注。**

**⇒ 与 §235 的"注释滞后"、§280 的 `pinnedSession` 同族（第四处"已死的东西被标注"）。**

### 2.7 而**新的判据：最窄的真于两个 build**

```php
// The test below is the narrowest one true of BOTH builds: some
// character identity must be present. An all-zero customization is
// still refused, because that one really is empty.
const auto hasCharacterIdentity =
    customization.characterItemId != 0 ||
    std::ranges::any_of(customization.selectionIds, [](auto v) { return v != 0; });
if (!customization.modelIndex ||
    customization.modelIndex > 0xF ||
    (uint8)customization.faction > 1 ||
    customization.color > 3 ||
    !customization.viewmodelIndex ||
    customization.viewmodelIndex > 0x3FF ||
    !hasCharacterIdentity)
{
    return false;
}
```

### 2.8 七项

```text
① modelIndex 非零
② modelIndex <= 0xF          【四位】
③ faction <= 1               【一位】
④ color <= 3                 【两位】
⑤ viewmodelIndex 非零
⑥ viewmodelIndex <= 0x3FF    【十位】
⑦ hasCharacterIdentity       【characterItemId 或任一 selectionId】
```

### 2.9 而**五个位宽的完整对照**

```text
modelIndex       4 位（0..0xF）      ⇒ 与 §313 的"四位"一致 ✓
faction          1 位（0..1）
color            2 位（0..3）
viewmodelIndex  10 位（0..0x3FF）    ⇒ 与 §309 的"十位 0x3FF"一致 ✓
selectionIds[i]  各自的位宽（见下）
```

**✅ 五个字段五种位宽。**

### 2.10 而 `selectionIds` 的**逐项检查**

```php
for (index = 0; index < customization.selectionIds.size(); ++index)
{
    const auto width = CharacterSelectionBitWidths[index];    // 7,4,8,8,6,7,8,5,0,8,0
    const auto selection = customization.selectionIds[index];
    if ((!width && selection) || (width && selection > (1u << width)))
        return false;
}
```

### 2.11 两项

```text
width == 0 且 selection != 0   ⇒ 拒绝【零位宽的项必须为零】
width != 0 且 selection > 2^width ⇒ 拒绝
```

**⚠ `selection > (1u << width)` 而 §313 的 `CharacterSelectionMaximumPayloadBitCount` 是 72。**

**⇒ `1u << 7 = 128` ⇒ 而 §309 说"`selectionIds[0]` 有 7 位宽（1..128 合法）"**

**⚠ 而 `selection > 128` ⇒ 所以 129 被拒而 128 通过。**

**⇒ 但 7 位能表示 0..127！**

**⚠ 所以 `selection == 128` 是**超出 7 位**的值而这里**允许**。**

**⇒ 因为 §315 后面的注释说"一个存在的值被解码为 `bits + 1`"。**

**⇒ 所以编码是 1..128 而解码是 `bits + 1`。**

**✅ 所以 `> (1u << width)` 是**正确的编码界**（1..2^width）。**

## 三、**`0x3FF / 0x3FE / 0x7FF` 各窄一位**（本组第二重要）

```php
// CODDIFF(1649370): every bound below that ends in 0x3FF, 0x3FE or
// 0x7FF was 3.3.3.3's, and each is one bit narrow here. The weapon
// asset index is eleven bits (this file's own
// MaxCurrentWeaponAssetIndex already says 0x7FF); the ammo and clip
// indexes are eleven, MEASURED at 1188 and 1297 on 6160/6160 real
// retail snapshots; the ammo pool count is twelve. fireType was 6,
// which EngineBindings had already re-derived to 10 from out.exe's
// own accessor -- so a weapon could pass the definition check and be
// rejected here instead, one layer further in.
```

### 3.1 五层

```text
1. **下面每一个以 `0x3FF`、`0x3FE` 或 `0x7FF` 结尾的界都是 3.3.3.3 的**
2. ⇒ **而每一个在这里都窄一位**
3. ⇒ 武器资产索引是**十一位**（本文件自己的 `MaxCurrentWeaponAssetIndex` 已经说 `0x7FF`）
4. ⇒ 弹药与弹匣索引是**十一位**，**实测在 1188 与 1297（6,160/6,160 个真实零售快照）**
5. ⇒ 弹药池计数是**十二位**
6. ⇒ `fireType` 曾是 **6**，而 `EngineBindings` 已经从 out.exe 自己的访问器重新推导为 **10**
7. ⇒ ⇒ 所以**一把武器可以通过定义检查而在这里被拒 —— 再往内一层**
```

### 3.2 而**五个界的最终值**

```text
weaponAssetIndex     0x7FF  （11 位）
ammoIndex            0x7FF  （11 位）
clipIndex            0x7FE  （11 位，全一是 sentinel）
clipSize             0x1FF  （9 位）
maxAmmo              0xFFF  （12 位）  ← 【注意！§240 是 0x7FF】
fireType             <= 10
```

**⚠ **`maxAmmo <= 0xFFF` 与 §240 的 `0x7FF` **不同**！**

**§240**：`if (maxAmmo > 0x7FF) { ...return false; }`

**§315**：`weapon.maxAmmo <= 0xFFF`

**⇒ 两个不同的上界：`0x7FF`（11 位）vs `0xFFF`（12 位）。**

**⇒ 而 §315 说"弹药池计数是**十二位**"。**

**✅ 所以 §315 是**修正后**的值而 §240 是**旧**的。**

**⚠ 或者两个检查面向**不同的量**：**

```text
§240  maxAmmo = maxAmmoMultiplier × clipSize   （在 EngineBindings 里算的）
§315  weapon.maxAmmo                            （SvResolvedWeapon 的字段）
```

**⇒ 若 `maxAmmoMultiplier` 是 12 位而乘积被夹到 0x7FF，那两者可以共存。**

**⚠ 但 §240 的注释明确说 "0x7FF is a wire width"。**

**⇒ 所以这是一处**需要核实的不一致**。**

### 3.3 而 `6,160 / 6,160` 的**实测**

**⇒ 与 §240 的"6160/6160 真实零售快照"**完全同一个数** ✓**

**⇒ 所以两处引用同一次测量。**

**✅ 而 §240 用它证明"11 位"，§315 用它证明"11 位"。**

**⇒ 一致。**

### 3.4 而"**一把武器可以通过定义检查而在这里被拒 —— 再往内一层**"

**⇒ 三层**：

```text
1. `EngineBindings` 的定义检查（§240）过了
2. ⇒ 而 `SV_IsResolvedLoadoutValid` 的检查（这里）拒了
3. ⇒ **再往内一层**
```

**✅ 与 §244 的"两个出口一个返回类型"同族（第十二次"两层检查不一致"）。**

## 四、`weaponValid` 的**二十一项**

```cpp
const bool meleeWeapon = weapon.weaponType == 5;
return weapon.weaponAssetIndex && weapon.weaponAssetIndex <= 0x7FF &&
    weapon.ammoIndex && weapon.ammoIndex <= 0x7FF &&
    (meleeWeapon || (weapon.clipIndex > 0 && weapon.clipIndex <= 0x7FE &&
        weapon.clipSize && weapon.clipSize <= 0x1FF &&
        weapon.maxAmmo && weapon.maxAmmo <= 0xFFF)) &&
    weapon.fireType <= 10 &&
    weapon.shotCount <= 0xFF &&
    weapon.fireDelayMilliseconds <= INT16_MAX &&
    weapon.fireTimeMilliseconds && weapon.fireTimeMilliseconds <= INT16_MAX &&
    weapon.dropTimeMilliseconds <= INT16_MAX &&
    weapon.raiseTimeMilliseconds <= INT16_MAX &&
    isfinite(hipSpreadStandMin) && hipSpreadStandMin >= 0 &&
    isfinite(hipSpreadCrouchMin) && hipSpreadCrouchMin >= 0 &&
    isfinite(hipSpreadProneMin) && hipSpreadProneMin >= 0 &&
    isfinite(hipSpreadStandMax) && hipSpreadStandMax >= hipSpreadStandMin &&
    isfinite(hipSpreadCrouchMax) && hipSpreadCrouchMax >= hipSpreadCrouchMin &&
    isfinite(hipSpreadProneMax) && hipSpreadProneMax >= hipSpreadProneMin &&
    isfinite(adsSpread) && adsSpread >= 0 &&
    SV_IsWeaponDamageCurveValid(weapon.damageCurve) &&
    all_of(hitLocationMultipliers, isfinite && >= 0 && <= 20);
```

### 4.1 而**近战武器的豁免**

```cpp
(meleeWeapon || (clipIndex > 0 && clipIndex <= 0x7FE && clipSize && clipSize <= 0x1FF && maxAmmo && maxAmmo <= 0xFFF))
```

**⇒ 三层**：

```text
近战（weaponType == 5）⇒ 【跳过】弹匣/弹匣容量/最大弹药
否则 ⇒ 三项都要检查且都非零
```

**✅ 与 §240 的 `meleeWeapon` 门**完全一致** ✓**

**⇒ 但 §240 还允许 `absentClip = clipIndex == -1`。而这里 `clipIndex > 0` ⇒ **-1 被拒**。**

**⚠ 所以"无弹匣"（-1）在 §240 允许而在这里**拒绝**（除非是近战）。**

**⇒ 而这**正是** §240 记录的那次修复：**

**§240**："A WEAPON WITH NO CLIP IS LEGAL, AND THIS REJECTED ONE. ... `raygun_mp` is an energy weapon with no magazine"

**⇒ 所以 `raygun_mp` 的 `clipIndex = -1` 在 §240 **允许**了，但在这里**被拒**。**

**⚠ 这是一处**未修的对应缺陷**。**

**⇒ 而 `raygun_mp` 是 dmz 的武器（§301 的 `dmz_empty_mp` 提到）。**

**✅ 值得指出。**

### 4.2 而 `fireTimeMilliseconds` **必须非零**

```cpp
weapon.fireTimeMilliseconds && weapon.fireTimeMilliseconds <= INT16_MAX
```

**⇒ 与 §240 的 `fireTime <= 0 ⇒ 拒绝`**一致** ✓**

### 4.3 而 `shotCount <= 0xFF` 而 §240 是 `shotCount > uint8_max ⇒ 拒绝`

**⇒ 一致** ✓

## 五、**`SV_IsResolvedLoadoutValid` 的"副武器允许为空"**（本组第三重要）

```php
// ★★★ 2026-10-14（V1.203 ① S2-②）—— 语义改为「**主武器必须有效；副武器允许为空**」。
//   空副手 = `weaponAssetIndex == 0`（S2-① 的空槽）。原来"副武器也必须有效"会让**整个 class 被拒**
//   ⇒ 不装副武器的 class 进不了图（甲方症状："背包都选不出来"）。
//   依据：票 `20261014-0100` 的 S2-②；刀的回退（S3）是**另一刀**，不在本改动里。
const bool secondaryEmpty = loadout.secondary.weaponAssetIndex == 0;
return weaponValid(loadout.primary) &&
    (secondaryEmpty || weaponValid(loadout.secondary)) &&
    loadout.primary.weaponAssetIndex != loadout.secondary.weaponAssetIndex;
```

### 5.1 四层

```text
1. **主武器必须有效**
2. ⇒ **副武器允许为空**（`weaponAssetIndex == 0`）
3. ⇒ 原来"副武器也必须有效"会让**整个 class 被拒**
4. ⇒ **不装副武器的 class 进不了图**
5. ⇒ **甲方症状："背包都选不出来"**
```

### 5.2 而**第三个条件**是"主副不同"

```cpp
loadout.primary.weaponAssetIndex != loadout.secondary.weaponAssetIndex
```

**⚠ 而如果副武器为空（0）而主武器是 0 ⇒ 但 `weaponValid(primary)` 要求非零。**

**⇒ 所以"主副不同"在副武器为空时**恒真**（因为主非零）。**

**✓ 正确。**

### 5.3 而"**刀的回退（S3）是另一刀，不在本改动里**"

**⇒ 三层**：

```text
1. 刀的回退（S3）是**另一刀**
2. ⇒ **不在本改动里**
3. ⇒ 所以这里**允许空副武器但不填刀**
```

**✅ 与 §307 的"空手枪回退到 `chicken_melee_mp`"是**另一处**（在 `setLoadoutProvider` 里）。**

**⇒ 所以"空副武器"有两层处理：**

```text
SV_IsResolvedLoadoutValid  允许空
setLoadoutProvider         填空为刀
```

**✅ 两层配合。**

## 六、`SV_FindResolvedWeapon` 的三项

```cpp
if (!SV_IsResolvedLoadoutValid(loadout) || !weaponAssetIndex) return nullptr;   // ①
if (loadout.primary.weaponAssetIndex == weaponAssetIndex) return &loadout.primary;    // ②
if (loadout.secondary.weaponAssetIndex == weaponAssetIndex) return &loadout.secondary; // ③
return nullptr;
```

**⇒ 三项。**

### 6.1 而 ① **重复验证整个 loadout**

**⚠ 每次查找都跑 21 项验证。**

**⇒ 如果这个函数在**热点路径**上 ⇒ 昂贵。**

**⚠ 一处潜在性能问题。**

## 七、**`SV_FindResolvedWeaponOrAlt` 的 `scratch`**（本组第四重要）

### 7.1 那段完整的因果

```php
// SECTION 191z: AND THE ALT, WHICH THE LOADOUT DOES NOT CONTAIN AND FIVE
// CALL SITES NEEDED.
//
// SvResolvedLoadout holds the primary and the secondary and nothing else,
// deliberately: it lives inside the address-keyed native buffer and growing
// it broke the death animation twice (section 184h). So every consumer that
// resolves "the weapon this shot was fired with" has to fall back to the
// alt lookup, and until now the FIRE path and the weapon-movement path were
// the only two that did.
//
// The damage validator was not one of them, so an alt-fire shot traced, hit,
// staged its damage and was refused there -- rejecting the whole usercmd,
// and with it the frame's movement. The player reported both halves:
// "it never hurts them" and "it causes desync".
//
// `scratch` must outlive the returned pointer; every caller keeps it in the
// same scope.
const SvResolvedWeapon *SV_FindResolvedWeaponOrAlt(
    const std::optional<SvResolvedLoadout> &loadout,
    const std::uint16_t weaponAssetIndex,
    SvResolvedWeapon &scratch)
{
    if (loadout)
        if (const auto *const found = SV_FindResolvedWeapon(*loadout, weaponAssetIndex))
            return found;
    return SV_LookupAltWeapon(weaponAssetIndex, scratch) ? &scratch : nullptr;
}
```

### 7.2 七层

```text
1. **`SvResolvedLoadout` 只持有主与副，别的不持有，【刻意的】**
2. ⇒ 因为它住在**地址键控的原生缓冲区里**而**增大它两次破坏了死亡动画**（§184h）
3. ⇒ 所以**每一个"解析这一枪是用哪把武器打的"的消费者都必须回退到 alt 查找**
4. ⇒ **而到目前为止只有 FIRE 路径与武器移动路径这两条做了**
5. ⇒ **伤害验证器不是其中之一** ⇒ 所以**一次 alt-fire 的射击 traced、hit、staged 它的伤害而【在那里被拒】**
6. ⇒ **拒绝了整个 usercmd，以及那一帧的移动**
7. ⇒ **玩家报告了两半**："它从不伤到他们" 与 "它导致失步"
```

### 7.3 **"`scratch` 必须活得比返回的指针长"**

**⇒ 三层**：

```text
1. `scratch` 是一个**调用者的局部**
2. ⇒ 返回的指针指向 `scratch`
3. ⇒ 所以**每个调用者把它保持在同一个作用域里**
```

**⚠ 一个**危险的 API** —— 返回指向参数的指针。**

**⇒ 但注释明说了 ⇒ 所以是**有意的**。**

**✅ 与 §266 的"`toLocal` 返回局部数组"（按值）**不同**。**

### 7.4 而"**两次破坏了死亡动画**"

**⇒ 与 §308 的"48 字节破坏死亡动画"**同族（第三次）。**

**⇒ 所以"地址键控的缓冲区"是一个**反复出现的约束**。**

**✅ 与 §180 的"复制地址键控缓冲区"一起 ⇒ 第四次。**

## 八、`SV_ResolveCharacterCustomization` 的**七项 + 一处强制**

```cpp
SvCharacterCustomization customization{
    .modelIndex = CharacterModelIndexBootstrap,      // 【6】
    .faction = faction,
    .female = female,
    .color = color,
    .viewmodelIndex = viewmodelIndex,
    .selectionIds = selectionIds,
    .characterItemId = characterItemId,
    .recordItemIds = recordItemIds,
};
customization.recordItemIds[0] = characterItemId;    // ←【强制】
return validCharacterCustomization(customization) ? optional{customization} : nullopt;
```

### 8.1 八项

**⇒ 而 `modelIndex` 用 `CharacterModelIndexBootstrap = 6`（§313 的语料测量）。**

### 8.2 而"**ENTRY 0 与线字段是同一件事，所以在这里让它们一致**"

```php
// ENTRY 0 AND THE WIRE FIELD ARE THE SAME THING, so make them agree here rather
// than trusting two callers to. A record whose entry 0 disagreed with
// characterItemId would resolve one character on the server and render another
// on every client, which is the hardest kind of wrong to see.
```

### 8.3 四层

```text
1. **ENTRY 0 与线字段是同一件事**
2. ⇒ 所以**在这里让它们一致**而不是信任两个调用者
3. ⇒ 一个 `recordItemIds[0]` 与 `characterItemId` 不一致的记录会**在服务器上解析一个角色而在每个客户端上渲染另一个**
4. ⇒ **那是最难看见的一类错**
```

**✅ 与 §309 的"`recordItemIds[0] = characterItemId` 的强制覆盖"**完全一致** ✓**

**⇒ 而 §309 在 `Appmain.cpp` 里做，§315 在 `sv_snapshot_mp.cpp` 里也做。**

**⇒ 两处强制 —— 因为"不信任调用者"。**

### 8.4 而"**不把 `characterItemId` 放进 `validCharacterCustomization`**"

```php
// Section 67's input. It is deliberately NOT part of
// validCharacterCustomization: a customization with no character item is
// exactly what this build produced for every match before section 67, and
// rejecting it here would stop players spawning rather than stop them
// rendering. Model resolution checks it for itself and degrades loudly.
```

### 8.5 四层

```text
1. ⇒ **刻意不把 `characterItemId` 放进 `validCharacterCustomization`**
2. ⇒ 一个没有角色物品的定制化**正是这个 build 在 §67 之前每一场比赛产出**的
3. ⇒ 在这里拒绝它会**阻止玩家 spawn** 而不是**阻止他们渲染**
4. ⇒ **模型解析自己检查它并【大声地】降级**
```

**✅ 与 §282 的"spawn 合取式里静默丢项"**相反** —— 这里是**大声降级**。**

**⇒ 而 §282 说"必须能通过校验" (c) ⇒ 所以两处**方向不同**：**

```text
§282  必须通过 validCharacterCustomization 否则不 spawn
§315  characterItemId 不在 valid 里 ⇒ 所以可以 spawn 而模型可能不对
```

**✅ 两个层次。**

## 九、`SV_PackCharacterCustomization` 的开头

```php
// CODREF(character_customization): CODOL
// CODOL_CharacterCustomization_UnpackSelectionIds 0x0040CBD0 first
// copies clientInfo fields 20/21/22/27/31/32/33/34 into a 76-bit
// temporary message, then reads eleven presence bits followed by the
// exact per-slot widths above. A present value is decoded as bits + 1.
// The eleven records consume at most 72 bits; absent slots omit their
```

### 9.1 三层

```text
1. `UnpackSelectionIds 0x0040CBD0` **先把 clientInfo fields 20/21/22/27/31/32/33/34 拷进一个 76 位的临时消息**
2. ⇒ 然后读**十一个存在位**跟着**上面那些精确的每槽位宽**
3. ⇒ **一个存在的值被解码为 `bits + 1`**
4. ⇒ **十一个记录最多消耗 72 位**而**缺席的槽省略它们的**
```

### 9.2 而 §313 的**两个 static_assert**

```text
CharacterSelectionMaximumPayloadBitCount == 72    ← 11 + 61
CharacterSelectionStorageBitCount == 76           ← 8 个字段（10×7 + 6）
```

**✅ 而这里说"拷进 76 位"而"记录最多 72 位"** ⇒ 完美对上** ✓**

**⇒ 所以 `72` 是**载荷**而 `76` 是**存储**。**

### 9.3 而"**解码为 `bits + 1`**"

**⇒ 三层**：

```text
1. 编码是 `value - 1`（0 表示缺席）
2. ⇒ 解码是 `bits + 1`
3. ⇒ 所以 value 1..128 对应 bits 0..127
```

**✅ 与 §315 的 `selection > (1u << width)` **完全一致** ✓（1..2^width）**

## 十、关键结论

1. **`validCharacterCustomization` 的旧判据在 OLfinal 上对每个客户端都拒绝** ⇒ **没有任何 clientInfo 曾被发送**。
2. **`clientInfoGate 1` 而模型字段全零** ⇒ **领奖台画卡片而不画人**（因为名字来自分开的计分板数组）。
3. **`ClientInfoExplicitModelFieldFirst = 46` 被定义而无处引用** —— 一段死常量。
4. **新判据是"最窄的真于两个 build 的"**：`characterItemId 或任一 selectionId`。
5. **五个字段五种位宽**（4/1/2/10/逐项）。
6. **`selection > (1u << width)` 是**编码界**（因为解码是 `bits + 1`）。
7. **`0x3FF/0x3FE/0x7FF` 各窄一位** —— 第七次该族教训。
8. **`maxAmmo <= 0xFFF`（12 位）而 §240 是 `0x7FF`（11 位）** —— **一处需核实的不一致**。
9. **`6,160/6,160`** 与 §240 同一次测量。
10. **"一把武器可以通过定义检查而在这里被拒 —— 再往内一层"**。
11. **⚠ `clipIndex > 0` 拒绝 `-1`，而 §240 明确允许"无弹匣"（`raygun_mp`）** —— **一处未修的对应缺陷**。
12. **`SV_IsResolvedLoadoutValid` 的"副武器允许为空"** —— 甲方症状"背包都选不出来"。
13. **刀的回退是"另一刀"** —— 两层配合（valid 允许 + provider 填刀）。
14. **`SV_FindResolvedWeapon` 每次查找都跑 21 项验证** —— 潜在性能问题。
15. **`SV_FindResolvedWeaponOrAlt` 的 `scratch` 必须比返回指针活得长** —— 一个有意的危险 API。
16. **"增大 `SvResolvedLoadout` 两次破坏死亡动画"** —— 第三次/第四次该约束。
17. **`recordItemIds[0] = characterItemId` 的强制在两处** —— "不信任调用者"。
18. **`characterItemId` 刻意不在 `validCharacterCustomization` 里** —— 否则会阻止 spawn 而不是阻止渲染。
19. **`72` 是载荷而 `76` 是存储** —— 两个 `static_assert` 完美对上。
20. **"解码为 `bits + 1`"** 与 `> (1u << width)` 的界完全一致。

## 十一、未闭合点

- `maxAmmo` 的 `0xFFF` vs `0x7FF` 两处不一致。
- `clipIndex = -1`（无弹匣）在这里被拒而 §240 允许 —— 是否会实际阻塞 `raygun_mp`。
- `SV_FindResolvedWeapon` 的验证开销。
- `sv_snapshot_mp.cpp` 600 行之后未读取。
