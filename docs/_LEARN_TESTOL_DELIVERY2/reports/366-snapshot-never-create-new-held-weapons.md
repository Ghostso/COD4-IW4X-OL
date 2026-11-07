# 366 · **"永远不创建新的持有武器"** —— 补弹的三个来源、`replaceFactoryWeapon` 的十一项拒绝理由、四种共享索引组合

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 18000–18400 行。

## 二、**`factoryAmmoRefillCandidate` 的三层累积**（本组第三重要）

### 2.1 `include` 的六项

```cpp
const auto include = [&](const SvResolvedWeapon &weapon) {
    if (!weapon.weaponAssetIndex || !weapon.ammoIndex || !weapon.maxAmmo ||
        !weapon.clipSize ||
        !std::ranges::any_of(owner.playerState.heldWeapons,
            [&](const auto &held) { return held.weaponAssetIndex == weapon.weaponAssetIndex; }) ||
        !seen.insert(weapon.weaponAssetIndex).second)
        return;
    auto &capacity = maximum[weapon.ammoIndex];
    capacity = std::min<std::uint32_t>(0x7FF, capacity + weapon.maxAmmo);
    if (weapon.clipIndex > 0) {
        auto &clipCapacity = clipMaximum[weapon.clipIndex];
        clipCapacity = std::max(clipCapacity,
            static_cast<std::uint16_t>(std::min<unsigned>(0x1FF, weapon.clipSize)));
    }
};
```

### 2.2 八层

```text
1. **六项前置**：有 `weaponAssetIndex` / `ammoIndex` / `maxAmmo` / `clipSize`
     · **而玩家【实际持有】它**（`heldWeapons` 里有）
     · **而未见过**（`seen.insert` 的 `.second`）
2. ⇒ **所以"持有"是必须的** ⇒ **一把掉落的装备枪【不贡献】**
3. ⇒ **`maximum[ammoIndex] += maxAmmo`**（上限 `0x7FF`）
4. ⇒ **`clipMaximum[clipIndex] = max(old, min(0x1FF, clipSize))`**
5. ⇒ **两个不同的界**：`0x7FF`（池）/ `0x1FF`（弹匣）
6. ⇒ 而 `clipIndex > 0` 才计入（**0 是一个哨兵**）
```

**✅ 与 §362 五.2 的"`maximum` 上限 `0x7FF`"**第二次确认。**

**⚠ 而 `0x1FF = 511` 是**弹匣上限**。**

**✅ 与 §346 的"`clip.count[0] > 0x1FF`"**完全一致 ✓**

**⇒ **第二次确认那个 9 位界。**

### 2.3 而**三个来源**

```cpp
include(owner.resolvedLoadout->primary);
include(owner.resolvedLoadout->secondary);
if (clientNum < weaponGrants_.size() && weaponGrants_[clientNum].active)
    include(weaponGrants_[clientNum].weapon);
```

**⇒ 三层**：

```text
① 主武器
② 副武器
③ **DMZ 的临时授予**（若活动）
```

**✅ 与 §352 的"授予记在 `weaponGrants_` 而不编辑装备"**完全一致 ✓**

**⇒ **第二次确认那个设计。**

### 2.4 而**第四个来源（箱子的装备）**

```php
if (boxReward) {
    // CODREF(actor_grounded_adapter): original Prototype max-ammo claim at
    // 591550 updates equipment clip931 to 2 as well as reserve992 to 90.
    // IDA429AE0 consumes offhands from their own clip. Use this life's
    // verified equipment definitions, never create new held weapons.
    const auto equipment = playerEquipment_.find(clientNum);
    if (equipment != end && equipment->second.spawnGeneration == owner.playerState.spawnGeneration &&
        SV_IsEquipmentValid(equipment->second.equipment)) {
        for (const auto &item : equipment->second.equipment.weapons) {
            if (!item.weaponAssetIndex || !any_of(owner.playerState.heldWeapons, ...)) continue;
            // Full native clip capacity is the reconstructed policy for
            // equipment not yet observed in a Max Ammo transaction.
            auto &capacity = clipMaximum[(int16_t)item.clipIndex];
            capacity = std::max(capacity, item.clipCapacity);
        }
    }
}
```

**⇒ 九层**：

```text
1. **原始 Prototype 的 max-ammo 声明在 `591550`**
2. ⇒ **更新装备 `clip931` 到 `2` 以及 `reserve992` 到 `90`**
3. ⇒ **`IDA429AE0` 从它们【自己的 clip】消费副手**
4. ⇒ **用【这一条生命】已验证的装备定义**
5. ⇒ **【永远不创建新的持有武器】**
6. ⇒ **代际匹配**
7. ⇒ **`SV_IsEquipmentValid`**
8. ⇒ **仍然要求玩家持有它**
9. ⇒ **满原生的弹匣容量是"未经 Max Ammo 事务观察到的装备"的重建策略**
```

**✅ ⭐ **"永远不创建新的持有武器"** —— 与 §352 的"不编辑装备"同族（**第二次"不创造状态"**）。

### 2.5 而**两个累积循环**

```cpp
for (auto &pool : next.ammoPools) {
    const auto cap = maximum.find(pool.ammoIndex);
    if (cap != end && pool.count < cap->second) { pool.count = (uint16)cap->second; changed = true; }
}
// CODREF(actor_grounded_adapter): Factory585000/716200/880900 and
// Sumpf339750 refill magazines and reserves on the purchase snapshot.
// IDA673269..6732DD reads the independent clip array; this is not a reload
// transfer from reserves. Preserve unrelated clips and the second hand.
for (auto &clip : next.ammoClips) {
    const auto cap = clipMaximum.find(clip.clipIndex);
    if (cap != end && clip.count[0] < cap->second) { clip.count[0] = cap->second; changed = true; }
}
```

**⇒ 七层**：

```text
1. **池：补到 `maximum`**
2. ⇒ **弹匣：补到 `clipMaximum` 的 `count[0]`**（**不动 `count[1]`**）
3. ⇒ **四个具体的工厂交互点**（`585000`/`716200`/`880900`/Sumpf `339750`）
4. ⇒ **`IDA673269..6732DD` 读独立的 clip 数组**
5. ⇒ **"这不是从储备到弹匣的转移"**
6. ⇒ **保留无关的 clip 与第二只手**
7. ⇒ **所以两处独立补满**
```

**✅ ⭐ **"这不是从储备到弹匣的转移"** —— 一个**关键的语义区分**。**

**⇒ 三层**：

```text
转移语义：储备 --减少--> 弹匣 ++       （总量不变）
独立补满：储备 = 满 而 弹匣 = 满       （总量增加）
⇒ **零售是后者**
```

**✅ 与 §362 五.2 的"加一个弹匣"**不同**（那是**拾荒者**，这是**工厂补给**）。

**⇒ **两种不同的补弹语义。**

## 三、**`refillFactoryAmmo` 的往返检查**

```cpp
auto native = owner.nativePlayerState;
SV_OverlayPlayerStateToNative(next, native);
auto projected = next;
if (!SV_OverlayNativePlayerStateToPlayerState(native, projected) ||
    projected.ammoPools != next.ammoPools || projected.ammoClips != next.ammoClips)
    return false;
zombieBattery_[clientNum] -= cost;
owner.playerState = next;
owner.nativePlayerState = std::move(native);
```

### 3.1 六层

```text
1. **叠加到原生**
2. ⇒ **再投影回来**
3. ⇒ **只比较 `ammoPools` 与 `ammoClips`**（**不是整条**）
4. ⇒ **所以其它字段可以不同**
5. ⇒ **成功后扣电池并提交**
6. ⇒ **所以电池在验证之后才扣**
```

**⚠ 而 §364 的 `teleportFactoryPlayer` 比较**整条**（`roundTrip != nextPlayerState`）。**

**⇒ 两处**不同的严格程度**：**

```text
teleport   整条相等
refill     只看两个弹药数组
```

**✅ 一个**精确的适用范围**（补弹只改弹药）。**

**⚠ 但**整条相等更强**（如果可行，为什么不用？）。**

**⇒ 可能因为**原生表示对某些字段有损**（如浮点精度）。**

**✅ 一个合理的解释。**

## 四、**`replaceFactoryWeapon` 的十一项拒绝理由**（本组最重要的一段）

### 4.1 完整清单

```text
invalid_request                            输入非法
unknown_client                             客户端不存在
inactive_or_stale_selection_or_funds       状态/选择/资金
temporary_grant_active                     临时授予活动
invalid_old_loadout                        旧装备无效
selected_not_loadout                       选中不在装备里
definition_unavailable                     解析器失败
invalid_new_loadout                        新装备无效
alternate_mode                             有交替模式
selected_not_held                          选中武器未持有
old_ammo_missing                           旧弹药缺失
ammo_storage_full                          弹药存储满
shared_ammo_capacity                       共享容量
native_roundtrip                           原生往返失败
```

**⇒ 十四项。**

### 4.2 而**每一项是一个具名的拒绝理由**

**✅ 与 §346 的"七十五项合取变成一个 `return reject`"**形成**鲜明对比**。**

**⇒ 三层**：

```text
§346  **七十五项一个笼统的拒绝**  ⇒ 头号 frameReject 而不知哪一项
§366  **十四项十四个具名理由**    ⇒ 可以直接定位
```

**✅ **同一类问题的两个极端**（而 §366 是正确做法）。

**⚠ 而 `refillFactoryAmmo` 与 `factoryAmmoRefillCandidate` **没有具名理由**（返回 `nullopt`）**。

**⇒ **三种风格并存**：

```text
frame validation      十九个具名（§346/§348）
replaceFactoryWeapon  十四个具名（这里）
refill / spawn        裸 nullopt
```

**✅ 一个**渐进的成熟度谱**。

### 4.3 而**"临时授予活动 ⇒ 失败"**

```php
// A grant is a DMZ-only per-think secondary hold. Mixing that temporary
// owner with a permanent Factory exchange would let the next think
// overwrite the accepted replacement, so fail closed until its owner is
// gone rather than silently taking either weapon.
if (clientNum < weaponGrants_.size() && weaponGrants_[clientNum].active)
    return reject("temporary_grant_active");
```

**⇒ 七层**：

```text
1. **一个授予是一个【DMZ-only 的每 think 副手保持】**
2. ⇒ **把那个【临时】所有者与一个【永久】工厂交换混合**
3. ⇒ **会让下一个 think 覆盖已接受的替换**
4. ⇒ **所以【故障关闭】直到它的所有者消失**
5. ⇒ **而不是静默地取任何一把武器**
6. ⇒ **两个"临时/永久"状态的冲突**
```

**✅ 与 §352 的"每帧保持 vs 写一次"**完全同族（**第三次"临时 vs 永久"**）。

**⇒ 而这里是**两个机制不能共存**。**

**✅ 一个**正确的"故障关闭"**。

### 4.4 而**"四种共享索引组合"**

```php
const auto oldClipShared = oldLoadout.primary.clipIndex == oldLoadout.secondary.clipIndex;
const auto oldPoolShared = oldLoadout.primary.ammoIndex == oldLoadout.secondary.ammoIndex;
const auto replacementSharesClip = replacement.clipIndex == other.clipIndex;
const auto replacementSharesPool = replacement.ammoIndex == other.ammoIndex;
```

**⇒ 四个布尔 ⇒ **16 种组合**。**

**⚠ 而代码只处理其中几种。**

### 4.5 而**三个候选查找**

```cpp
// 1. 直接找 replacement 的 clipIndex
auto replacementClip = find_if(ammoClips, clipIndex == replacement.clipIndex);
// 2. 若没找到而【旧的不共享】⇒ 用旧的槽
if (replacementClip == end && !oldClipShared) replacementClip = oldClip;
// 3. 若仍没找到 ⇒ 找 clipIndex == 0 的【空槽】
if (replacementClip == end) replacementClip = find_if(ammoClips, clipIndex == 0);
```

**⇒ 三层**：

```text
① 精确匹配
② **旧槽复用**（若不共享）
③ **空槽**（`clipIndex == 0`）
```

**✅ 与 §344 的"`validItemEntity` 的 `scriptMoverBrushModelIndex > 0`"配合。**

**⇒ 所以**`clipIndex == 0` 是一个"空槽"哨兵**。**

**⚠ 而 §362 五.2 的 `include` 里"`clipIndex > 0` 才计入"**完全一致 ✓**

**⇒ **第二次确认"0 = 空槽"。**

### 4.6 而**"安装替换后才退役旧存储"**

```php
// Retire the selected weapon's old private storage only after the
// replacement is installed. Shared indexes belong to the untouched gun;
// a matching replacement index is the same logical storage and remains.
if (!oldClipShared && oldClip != replacementClip) *oldClip = {};
if (!oldPoolShared && oldPool != replacementPool) *oldPool = {};
```

**⇒ 七层**：

```text
1. **只在替换被安装【之后】才退役旧的私有存储**
2. ⇒ **共享索引属于那把未被触碰的枪**
3. ⇒ **而一个匹配的替换索引是【同一个逻辑存储】并保留**
4. ⇒ **三个条件**：不共享 / 指针不同
5. ⇒ **所以两次检查都很精确**
```

**✅ 一个**精确的所有权转移**（先装后清）。

## 五、**`alternate_mode` 的四向检查**（本组第四重要）

```php
// This selected-slot owner has no alt-fire handoff policy yet. A host
// alt occupies an additional held slot and can share clip state, so
// accepting one here would leave an old asset reachable after exchange.
// Reject incoming child modes as well: native definition+3720 links a
// host to its child, whose ammo/clip storage may belong to that host.
// Refuse either direction until exchange owns the complete pair.
SvResolvedWeapon alt;
if (SV_LookupAltWeaponForHost(expectedAssetIndex, alt) ||
    SV_LookupAltWeaponForHost(replacementAssetIndex, alt) ||
    SV_LookupAltWeapon(expectedAssetIndex, alt) ||
    SV_LookupAltWeapon(replacementAssetIndex, alt))
{
    return reject("alternate_mode");
}
```

### 5.1 九层

```text
1. **这个选中槽的所有者【还没有】交替开火交接策略**
2. ⇒ **一个宿主 alt 占【额外的持有槽】并能共享弹药状态**
3. ⇒ **所以在这里接受一个会让一个旧资产在交换后【仍可达】**
4. ⇒ **也拒绝进入的子模式**
5. ⇒ **因为原生 `definition+3720` 把一个宿主链到它的子**
6. ⇒ **而子的弹药/弹匣存储可能属于那个宿主**
7. ⇒ **在两个方向上都拒绝直到交换拥有【完整的一对】**
8. ⇒ **四次查找**：`ForHost(old)` / `ForHost(new)` / `Alt(old)` / `Alt(new)`
```

**✅ 与 §350 的"两个入口必须一致"**同族（**一个"双向"的完整性要求**）。

**⚠ 而"四个查找"覆盖**两个方向 × 两个函数**。**

**✅ 一个**穷尽的检查**。

## 六、**`shared_ammo_capacity` 的算术**

```php
const auto replacementPoolCapacity = std::min<std::uint32_t>(
    0x7FF, (uint32_t)replacement.maxAmmo + (replacementSharesPool ? other.maxAmmo : 0u));
if ((replacementSharesClip && replacementClip->count[0] > replacement.clipSize) ||
    (replacementSharesPool && replacementPool->count > replacementPoolCapacity))
{
    return reject("shared_ammo_capacity");
}
```

### 6.1 五层

```text
1. **新池容量 = `min(0x7FF, replacement.maxAmmo + (共享 ? other.maxAmmo : 0))`**
2. ⇒ **若新弹匣共享** ⇒ **其 `count[0]` 必须 `<= replacement.clipSize`**
3. ⇒ **若新池共享** ⇒ **其 `count` 必须 `<= 新池容量`**
4. ⇒ **否则拒绝**（**而不是截断**）
5. ⇒ **所以两把枪的共享容量不能超额**
```

**✅ 与 §366 四.6 的"精确的所有权转移"**同族。**

**⚠ 而"拒绝而不是截断"⇒ **与 §362 五.2 的 `min(maximum, count + clipSize)`（那是**截断**）**不同**。**

**⇒ 三层**：

```text
拾荒者补弹   截断到 maximum（`min`）
工厂武器交换  拒绝若超额
```

**✅ **两种策略各有理由**：一个补弹一个换枪。**

**⚠ 而换枪**拒绝**更好（因为不损坏另一把枪）。**

**✅ 与注释"reject a value the new two-gun capacity cannot represent rather than clipping the other gun's ammunition"**完全一致 ✓

## 七、**原生往返的完整检查**

```php
// CODREF(actor_grounded_adapter): this Factory-only source transaction
// uses the existing source/native playerstate round trip; it does not
// claim a recovered Wetwork or retail PAP weapon-owner call.
// All weapon ownership writes
// must survive source -> native -> source before publication. This keeps
// a malformed native representation from charging battery or partially
// replacing the live world loadout.
SV_OverlayPlayerStateToNative(nextPlayerState, nextNativePlayerState);
auto roundTrip = nextPlayerState;
if (!SV_OverlayNativePlayerStateToPlayerState(nextNativePlayerState, roundTrip) ||
    roundTrip != nextPlayerState)
{
    return reject("native_roundtrip");
}
auto &worldClient = client->second.client;
worldClient.playerState = std::move(nextPlayerState);
worldClient.nativePlayerState = std::move(nextNativePlayerState);
worldClient.resolvedLoadout = std::move(nextLoadout);
auto &entity = client->second.entity.networkState;
entity.weaponAssetIndex = replacementAssetIndex;
entity.presentationWeaponAssetIndex = replacementAssetIndex;
zombieBattery_[clientNum] -= costRaw;
```

### 7.1 九层

```text
1. **所有武器所有权写必须在 source → native → source 之后存活**
2. ⇒ **然后才发布**
3. ⇒ **这防止一个畸形的原生表示扣电池或部分替换活世界装备**
4. ⇒ **而这里是【整条相等】**（比 refill 严格）
5. ⇒ **成功后四处提交**：
     · `playerState`
     · `nativePlayerState`
     · `resolvedLoadout`
     · **实体的两个武器索引**
6. ⇒ **然后扣电池**
```

**✅ 与 §352 的"三个武器出现机制"**完全一致 ✓**

**⇒ **第二次确认那个三元组**（`weaponAssetIndex` / `presentationWeaponAssetIndex` / 装备）。**

**⚠ 而**实体的两个索引都要更新**。**

**✅ 与 §342 的 `packEntityWeapon`（两个 16 位）**配合。**

## 八、**`changeFactoryBattery` 的"退款必须精确"**

```php
const auto next = (int64_t)zombieBattery_[clientNum] + deltaRaw;
// A refund must be exact.  Refusing rather than saturating makes a
// failed offer rollback observable to its Factory state-machine owner.
if (next < 0 || next > std::numeric_limits<std::uint32_t>::max())
    return false;
zombieBattery_[clientNum] = (uint32_t)next;
```

### 8.1 六层

```text
1. **`int64` 中间值**（允许负的 delta）
2. ⇒ **`next < 0` 或 `> UINT32_MAX` ⇒ 【拒绝】**
3. ⇒ **"一个退款必须是精确的"**
4. ⇒ **拒绝而不是饱和让一个失败的 offer 回滚【可观察】给它的工厂状态机所有者**
5. ⇒ **所以是一个"精确记账"的模型**
```

**✅ 与 §366 六 的"拒绝而不是截断"**同族（**第二次"拒绝优于截断"**）。

**⚠ 而"可观察给它的状态机所有者"⇒ **所以状态机依赖这个返回值**。**

**✅ 与 §345 的"每个状态机阶段有名字"配合。**

### 8.2 而**"battery 是服务端快照字段，不是原生 playerstate 成员"**

```php
// OLMOD(factory_interactables): battery is a server snapshot field, not
// a native playerstate member.  Keep this exact debit/refund owner out
// of the native overlay so it cannot alter weapons, perks, or movement.
```

**⇒ 五层**：

```text
1. **电池是一个【服务端快照字段】**
2. ⇒ **不是一个原生 playerstate 成员**
3. ⇒ **把精确的记账所有者【保持在原生叠加之外】**
4. ⇒ **所以它不能改变武器、技能或移动**
5. ⇒ ⇒ **一个正确的职责分离**
```

**✅ 与 §341 的"`clientState +0x40 → characterInfo +0xA4` 是 Factory HUD 的电池/点数额"**配合。**

**⇒ 所以**电池通过 `clientInfo` 字段 1（`ClientInfoZombieBatteryField`）发送**。**

**✅ 与 §341 的"字段 5 曾被误认为僵尸电池计数，它是 ability mask word 3"**不同**。**

**⚠ 而 §341 说 `ClientInfoZombieBatteryField = 1`。**

**✅ 所以**电池在 clientInfo 的字段 1**。**

## 九、`setFactoryWeaponDisplayMotion` 的**"字段 29"**

```php
// CODREF(actor_grounded_adapter): out.exe 520263 reads centity+15C,
// i.e. entityState+68 (wire field 29), and passes the raw weapon selector
// to 51FE00 at 5202B4. Parent/tag may both be zero. The +D8/527500 path
// is a separate client override, NOT this field and NOT a -1 encoding.
// This presentation uses native world-weapon assembly, without writing
// model pointers. Box selector cycling is reconstruction: the original
// box capture cycles model field 19; PAP captures include both fields.
```

### 9.1 十层

```text
1. **`out.exe 520263` 读 `centity+15C`，即 `entityState+68`（**线上字段 29**）**
2. ⇒ **把裸武器选择子传给 `5202B4` 的 `51FE00`**
3. ⇒ **父/标签可以都是零**
4. ⇒ **`+D8`/`527500` 路径是一个【独立的客户端覆盖】**
5. ⇒ **【不是】这个字段也【不是】一个 `-1` 编码**
6. ⇒ **这个展示用原生世界武器装配，【不写模型指针】**
7. ⇒ **箱子选择子循环是重建**：原始箱子捕获循环**模型字段 19**
8. ⇒ **而 PAP 捕获【包含两个字段】**
```

**✅ 与 §361 五的"字段 29 不是外观 ⇒ 什么都不发"**不同**。**

**⇒ 三层**：

```text
§361  actor 的字段 29 ⇒ **什么都不发**（未知）
§366  weaponDisplay 的字段 29 ⇒ **发武器选择子**
```

**⚠ 所以**同一个字段在两个用途上不同**。**

**✅ 与 §343 的"`+0x09C` 第四个语义"**配合（**第八次"一偏移多语义"**）。

### 9.2 而**"箱子循环字段 19 而 PAP 包含两个"**

**⇒ 三层**：

```text
1. **原始箱子捕获循环【模型字段 19】**
2. ⇒ **而 PAP 捕获【包含两个字段】**
3. ⇒ **所以两个来源不同**
```

**✅ 与 §350 的"`modelIndex` 在 `+0x05C`（字段 19）"**配合。**

**⚠ 而这里说 `weaponDisplay` 也可能用字段 19。**

**⇒ 所以**两个字段都是武器展示的候选**。**

**✅ 一个**需要按来源区分的细节**。

## 十、关键结论

1. **`include` 的六项前置**，而**"玩家实际持有它"是必须的** ⇒ **一把掉落的装备枪不贡献**。
2. **三个界**（`0x7FF` 池 / `0x1FF` 弹匣 / `clipIndex > 0` 哨兵）。
3. **补弹的四个来源**（主 / 副 / 临时授予 / 箱子的装备），而 **"永远不创建新的持有武器"`**。
4. **⭐ "这不是从储备到弹匣的转移"`** —— 零售是**两处独立补满**（总量增加）而非转移。
5. **四个具体的工厂补给点**（`585000` / `716200` / `880900` / Sumpf `339750`）。
6. **`refillFactoryAmmo` 的往返只比较两个弹药数组**（而 `teleportFactoryPlayer` 比较整条）—— 精确的适用范围。
7. **⭐⭐ `replaceFactoryWeapon` 的十四项具名拒绝理由** —— 与 §346 的"七十五项一个笼统拒绝"**形成鲜明对比**。
8. **三种风格并存**：帧验证（19 个具名）/ 武器交换（14 个具名）/ 其它（裸 `nullopt`）—— **一个渐进的成熟度谱**。
9. **⭐ "临时授予活动 ⇒ 失败"`** —— **一个 DMZ 的每-think 副手保持与一个永久的工厂交换【不能共存】**（第三次"临时 vs 永久"）。
10. **四种共享索引组合 ⇒ 16 种，而代码只处理几种**。
11. **三个候选查找**（精确 / 旧槽复用 / **空槽 `clipIndex == 0`**）—— 第二次确认"0 = 空槽"。
12. **"只在替换被安装【之后】才退役旧的私有存储"`** —— 精确的所有权转移。
13. **⭐ `alternate_mode` 的四向检查**（两个方向 × 两个函数）—— 一个穷尽的完整性要求。
14. **`shared_ammo_capacity`**：**拒绝而不是截断**（不损坏另一把枪）—— 与拾荒者补弹的截断**不同策略**。
15. **原生往返对武器交换是【整条相等】**，而成功后**四处提交**（`playerState` / `nativePlayerState` / `resolvedLoadout` / 实体的两个武器索引）。
16. **`changeFactoryBattery` 的"拒绝而不是饱和"`** —— **让一个失败的 offer 回滚【可观察】给它的状态机所有者**（第二次"拒绝优于截断"）。
17. **"battery 是一个服务端快照字段，不是原生 playerstate 成员"`** —— 通过 `clientInfo` 的字段 1 发送（配 §341）。
18. **字段 29 在 `weaponDisplay` 上是【武器选择子】**（`out.exe 520263` 读 `centity+15C`）—— 而 §361 的 actor 字段 29 **什么都不发**（**第八次一偏移多语义**）。
19. **"箱子循环字段 19 而 PAP 包含两个字段"`** —— 两个来源不同。

## 十一、未闭合点

- `MaxCurrentWeaponAssetIndex` 的值。
- `SV_LookupAltWeapon` 与 `SV_LookupAltWeaponForHost` 的区别。
- `weaponType == 2` 的语义（特殊武器）。
- `factorySpecialWeapon(index)` 的判据。
- `resolvedLoadout` 的完整字段。
- `sv_snapshot_mp.cpp` 18400 行之后未读取（27,016 行，进度 68%）。
