# 381 · **"拒绝而不是钳制"（REFUSE RATHER THAN CLAMP）三处** —— `+856` 的 configstring、`x624` 的 centity、`-4` 的武器表、`1147..1154` 八把 vs `1148..1211` 六十四把

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 24000–24400 行。

## 二、**三处"拒绝而不是钳制"**（本组最重要的一段）

### 2.1 第一处：`setPlayerCursorHint`

```php
// REFUSE RATHER THAN CLAMP. A hint string index outside the band and an
// entity number outside the array are both values the client will use
// arithmetically -- +856 into a configstring, x624 into its centity
// array -- so the failure mode of a bad one is a stranger's text or a
// stranger's entity, not a missing prompt. Same reason the const
// baseline lookups return nullopt instead of guessing.
if (hint != SvCursorHint::None &&
    (hintStringIndex < 0 || hintStringIndex >= HintStringConfigStringCount))
    return false;
if (hintEntityNum > SvNoHintEntityNum) return false;
```

### 2.2 第二处：`setPlayerWeaponCursorHint`

```php
// REFUSE RATHER THAN CLAMP, for the reason setPlayerCursorHint gives: the
// client subtracts 4 and indexes its weapon table with the result, so a value
// past the end of the band draws a stranger's gun rather than nothing.
if (!weaponAssetIndex || weaponAssetIndex > SvCursorHintMaximum - SvCursorHintWeaponBase)
    return false;
```

### 2.3 第三处：`registerLootItem`（隐含）

```php
if (!weaponAssetIndex || weaponAssetIndex >= WeaponConfigStringCount) return false;
if (!weaponDefinitionResolver_ || !weaponDefinitionResolver_(weaponAssetIndex, probe)) return false;
```

### 2.4 十一层

```text
1. **拒绝而不是钳制**
2. ⇒ **一个提示字符串索引越界**
3. ⇒ **与一个实体号越界**
4. ⇒ **都是客户端【按算术使用】的值**：
     · **`+856` 进一个 configstring**
     · **`×624` 进它的 centity 数组**
5. ⇒ **所以一个坏值的失败模式是【一个陌生人的文本】或【一个陌生人的实体】**
6. ⇒ **不是【一个缺失的提示】**
7. ⇒ **与 const 基线查找返回 `nullopt` 而不是猜测【同一个理由】**
8. ⇒ **武器提示：客户端【减 `4`】** 然后用结果索引它的武器表
9. ⇒ **所以一个越过带尾的值【画出别人的枪】** 而不是什么都不画
```

### 2.5 ⭐ **两个具体的算术：`+856` 与 `×624`**

**✅ 与 §338 的"`add esi, 1708h = 5896`"**同族（**第二次"具体的算术偏移"）。**

**⚠ 而 `+856` 与 `+5896` 是**两个不同的带**：**

```text
5896   标签带（§310/§338）
856    **提示字符串带**
```

**✅ 一个**新的带**。**

**⚠ 而 `×624`⇒ **centity 的 stride 是 624 字节**。**

**⇒ 与 §341 的 `352`（clientInfo）、§345 的 `280`（entityState）、§350 的 `60`（bmodel）、§361 的 `684`（agent 记录）**第五个尺寸。**

**✅ **五个结构尺寸**：**

```text
60    bmodel
280   entityState
352   clientInfo
624   centity
684   agent 记录
```

**✅ 一个**清晰的谱**。**

### 2.6 而**"不是缺失而是陌生人的"**

**✅ 与 §351 的"控制台成了僵尸身体"**同族（**第十次"错的而不是缺的"）。**

**⇒ 三层**：

```text
一个坏索引 ⇒ **不是"什么都不显示"**
⇒ **而是"显示别人的东西"**
⇒ **⇒ 更难诊断**
```

**✅ **一个极重要的失败分类**。**

## 三、**`1147..1154` 八把 vs `1148..1211` 六十四把**（本组第二重要）

### 3.1 那段

```php
// AND THE WEAPON HAS TO EXIST, checked here rather than at the pickup.
//
// MEASURED: this server registers its modular weapons CONTIGUOUSLY from
// firstDynamicWeapon, and it registered eight of them -- so 1147..1154 exist on
// mp_battlecity and nothing above does. The dmz loot band, which is a verbatim
// replay of a RETAIL capture, advertises 1148..1211, and retail had those
// because retail registered them. Most of that band names nothing here.
//
// A crate holding a weapon that does not resolve is a crate that prompts, takes
// the press, and hands over nothing. Refusing it at registration turns a silent
// dud into one line in the script log naming the crate and the index.
```

### 3.2 十四层

```text
1. **而那个武器必须【存在】，检查在这里而不是在拾取时**
2. ⇒ **测量：这个服务器从 `firstDynamicWeapon` 【连续】注册它的模块化武器**
3. ⇒ **而它注册了【八把】** ——
4. ⇒ **所以 `1147..1154` 在 `mp_battlecity` 上存在而上面什么都没有**
5. ⇒ **dmz 的战利品带，那是【一个零售捕获的逐字重放】**
6. ⇒ **宣告 `1148..1211`**
7. ⇒ **而零售有那些因为它们注册了它们**
8. ⇒ **那个带的大部分在这里【什么也不命名】**
9. ⇒ **一个装着不解析武器的箱子**
10. ⇒ **是一个提示、接受按键、而【什么都不给】的箱子**
11. ⇒ **在注册时拒绝它把一个【静默的哑弹】变成脚本日志里的一行**
12. ⇒ **那行【命名箱子和索引】**
```

### 3.3 ⭐⭐ **"八把 vs 六十四把"与"逐字重放"**

**✅ 与 §352 的"空手是一个保持状态"**不同**。**

**⇒ 三层**：

```text
零售：注册了 `1148..1211`（64 把）
我们：注册了 `1147..1154`（8 把）
⇒ **而 dmz 的战利品带是【逐字重放】** ⇒ 所以它宣告 64 把
⇒ **⇒ 56 把在本服务器上【什么也不解析】**
```

**✅ **一个"逐字重放一个捕获"的经典陷阱**。**

**⚠ 而"`1147` 是第一个模块化索引"⇒ 与 §374 的"捡起 `1147`（第一个模块化索引，也是这个职业自己的主武器）"**完全一致 ✓

**⇒ **第二次确认 `1147`。**

### 3.4 而**"一个静默的哑弹"**

**✅ 与 §350 的"接收了、存储了、而从未被画"**同族（**第十一次"静默的失败"）。**

**⇒ 三层**：

```text
箱子存在、提示出现、按键被接受
⇒ **而【什么都不给】**
⇒ **⇒ 一个静默的哑弹**
```

**✅ 与 §361 的"`frameReject=none:0` 说被发布的实体验证了"**同族。

### 3.5 而**"按实体号而不是按句柄"**

```php
// BY ENTITY NUMBER, not by handle: a re-registration of the same slot after a
// free is a NEW crate, and leaving the old generation in the table would offer
// a gun from an entity that no longer exists.
const auto existing = std::ranges::find(lootItems_, handle.entityNum,
    [](const SvLootItem &candidate) { return candidate.handle.entityNum; });
if (existing != lootItems_.end()) *existing = item;
else lootItems_.push_back(item);
```

**⇒ 六层**：

```text
1. **按实体号，不是按句柄**
2. ⇒ **因为一次 free 之后对同一个槽的重新注册是一个【新箱子】**
3. ⇒ **而在表里留着旧的代际会【提供一把来自一个不再存在的实体的枪】**
4. ⇒ **所以查号、覆盖**
```

**✅ 与 §363 的"代际拥有"**相反**（那里**必须**按代际，这里**必须不**按代际）。**

**⚠ 所以**两个相反的需求**：**

```text
实体释放   ⇒ **必须**按代际（防释放新实体）
战利品表   ⇒ **必须不**按代际（覆盖旧箱子）
```

**✅ 一个**精确的区分**。

## 四、**`shuffleKillStreaksFILO` 与 `setPlayerEquippedRewards` 的槽位**

```php
// CODREF(1649370): demo @43100 IDs fields127..129, targets132..134.
// Three equipped slots are runtime 1..3; slots 0/4 have
// separate owners and must not be overwritten by a loadout refresh.
std::copy(ids.begin(), ids.end(), allIds.begin() + 1);
std::copy(targets.begin(), targets.end(), allTargets.begin() + 1);
state.setRewardSlots(allIds, allTargets);
```

### 4.1 七层

```text
1. **demo 在 `43100` 上 ID 字段 `127..129`、目标 `132..134`**
2. ⇒ **三个装备槽是 runtime `1..3`**
3. ⇒ **槽 `0` 与 `4` 有【独立的所有者】**
4. ⇒ **而绝不能由一次装备刷新覆盖**
5. ⇒ **所以 `std::copy(..., begin() + 1)`**（从索引 1 开始）
6. ⇒ **所以 0 与 4 保持**
```

**✅ 与 §345 的"`rewardTargets` 的 `> 31`"**配合。**

**⚠ 而"槽 0 与 4 有独立所有者"⇒ **所以一个有五个槽的数组。****

**✅ 与 §380 的"`rewardActionType`/`rewardActionWeapon`"**配合。**

### 4.2 而**"`fields127..129` 与 `132..134`"**

**⇒ 三层**：

```text
IDs      字段 127..129（三个）
targets  字段 132..134（三个）
⇒ **所以两组各三个，间隔 5**
```

**✅ 与 §346 的"`rewardTargets()` 返回五个"**配合（**槽 0..4**）。

## 五、**`effectivePlayerAbilities` 的四层叠加**（本组第三重要）

### 5.1 那段

```cpp
auto effective = base->second.modifiers;
SV_ApplySideRollingExpert(effective);
if (factoryPerkMachinesEnabled_) {
    const auto owned = factoryPurchasedPerks_.find(clientNum);
    if (owned != end && owned->second.generation == spawnGeneration)
        SV_ApplyFactoryPurchasedPerks(effective, owned->second.mask);
}
const auto painted = paintedPlayers_.find(clientNum);
if (painted != end && painted->second.spawnGeneration == spawnGeneration &&
    (int32)(snapshot_.serverTime - painted->second.expireTime) < 0)
{
    SV_ApplyRadarArrow(effective);
}
return effective;
```

### 5.2 八层

```text
1. **四层叠加**（按顺序）：
     ① **基础修饰符**
     ② **`SV_ApplySideRollingExpert`**（一个内置技能）
     ③ **工厂购买的技能**（若开关且代际匹配）
     ④ **`SV_ApplyRadarArrow`**（若被标记且未过期）
2. ⇒ **所以是一个【可重建的叠加链】**
3. ⇒ **每一层都有自己的过期/代际条件**
```

**✅ 与 §367 的"购买的效果是当前职业上的【一个叠加】"**完全闭合 ✓

**⇒ **第二次确认那个架构。**

**⚠ 而"四层"⇒ **所以一个 `effective` 值从不被存储，而是【每次计算】。**

**✅ 与 §349 的"每帧保持而不是写一次"**同族（**第六次"重推导而不是存储"）。**

### 5.3 而**"`markPlayerPainted` 的 `insert_or_assign` 创建基"**

```cpp
auto base = playerAbilities_.find(clientNum);
if (base == playerAbilities_.end() || base->second.spawnGeneration != generation) {
    base = playerAbilities_.insert_or_assign(clientNum, AbilityLife{generation, {}}).first;
}
paintedPlayers_[clientNum] = { generation, snapshot_.serverTime + SvAbilityRadarArrowDurationMilliseconds };
auto effective = effectivePlayerAbilities(clientNum, generation).value_or(base->second.modifiers);
SV_ApplyRadarArrow(effective);
SV_SetNativeAbilityModifiers(client->second.client.nativePlayerState, effective);
```

**⇒ 六层**：

```text
1. **若基不存在或代际不符 ⇒ 【创建一个空的】**
2. ⇒ **然后设 `paintedPlayers_[clientNum]`**
3. ⇒ **然后**再**调 `effectivePlayerAbilities`**
4. ⇒ **所以叠加链包含了刚设的 paint**
5. ⇒ **然后写入原生**
6. ⇒ **所以"设 paint"与"写原生"是【一步】**
```

**✅ 一个**正确的顺序**（先设，后计算，再写）。

**⚠ 而 `value_or(base->second.modifiers)`⇒ **若 `effectivePlayerAbilities` 返回 `nullopt`（代际不符）⇒ 用基。****

**⇒ 所以**有一个兜底**。**

**✅ 与 §368 的"六种具名结果"**不同（这是**静默兜底**）。

## 六、**`setPlayerPerks` 的"一个地方同时设两个"**

```php
// The visibility bit and the perks it reveals are set in ONE place on
// purpose. A player with no perks and a visible empty sidebar, or perks
// with the sidebar off, are both states nothing should be able to reach
// by editing one of the two and forgetting the other.
client->second.client.playerState.perkHudVisible =
    (combined[0] || combined[1] || combined[2]) ? 1u : 0u;
```

### 6.1 六层

```text
1. **可见位与它所揭示的技能在【一个地方】被设**【故意】**
2. ⇒ **一个玩家没有技能而一个可见的空侧栏**
3. ⇒ **或技能而侧栏关**
4. ⇒ **都是【不应该能通过编辑两个之一而忘记另一个】到达的状态**
5. ⇒ **所以 `perkHudVisible = 任何一位 ? 1 : 0`**
6. ⇒ **一个"不变式在一个函数里"的设计**
```

**✅ 与 §351 的"一个遍历器必须引用那张表"**同族（**第二次"结构必然性"）。**

**⚠ 而"故意的"⇒ **一个有意的设计决策**。**

**✅ 与 §365 的"`solid` 与 `brushModelIndex` 必须一起动"**同族（**第三次"配对的字段"）。**

## 七、`setPlayerAbilities` 的**五项验证**

```cpp
if (client == end ||
    !std::isfinite(abilities.moveSpeedScale) || abilities.moveSpeedScale < 0 ||
    !std::isfinite(abilities.fallDamageScale) || abilities.fallDamageScale < 0 ||
    !std::ranges::all_of(abilities.values, [](float v) { return std::isfinite(v); }) ||
    !std::ranges::all_of(abilities.resolvedValues, [](float v) { return std::isfinite(v); }))
    return false;
```

**⇒ 六项**：

```text
① 客户端存在
② `moveSpeedScale` 有限且 >= 0
③ `fallDamageScale` 有限且 >= 0
④ `values` 全有限
⑤ `resolvedValues` 全有限
```

**✅ 与 §346 的"七十五项合取"**不同（这是**五项 + 两个"全有限"**）。

**⚠ 而"两个 scale 的 `>= 0`"⇒ **两个不同上限**？**

**⇒ 注释只说 `< 0` 拒绝，没说上限。**

**⚠ 所以**一个负的移动速度或摔落倍率被拒。****

**✅ 与 §353 的"`modelScale > 0`"**不同**（那里**必须正**，这里**可以零**）。**

**⚠ 所以**零速度是合法的**（一个冻结的玩家）。**

## 八、关键结论

1. **⭐⭐ "拒绝而不是钳制"三处**，而**两个具体的算术**：**`+856` 进 configstring** 与 **`×624` 进 centity 数组**。
2. **"所以一个坏值的失败模式是【一个陌生人的文本】或【一个陌生人的实体】，不是【一个缺失的提示】"`** —— 第十次"错的而不是缺的"。
3. **"客户端【减 `4`】然后用结果索引它的武器表 ⇒ 一个越过带尾的值【画出别人的枪】"`**。
4. **⭐ **五个结构尺寸**：`60`（bmodel）/ `280`（entityState）/ `352`（clientInfo）/ **`624`（centity）**/ `684`（agent 记录）。
5. **⭐ "`+856`（提示字符串带）"与"`+5896`（标签带）"是两个不同的带**。
6. **⭐⭐ `1147..1154`（八把）vs `1148..1211`（六十四把）** —— 而 **dmz 的战利品带是【一个零售捕获的逐字重放】** ⇒ **56 把在本服务器上什么也不解析**。
7. **"一个装着不解析武器的箱子是一个提示、接受按键、而【什么都不给】的箱子"`** —— 第十一次"静默的失败"。
8. **"在注册时拒绝把它（一个静默的哑弹）变成脚本日志里的一行，那行命名箱子和索引"`**。
9. **⭐ "按实体号而不是按句柄，因为一次 free 之后对同一个槽的重新注册是一个新箱子"`** —— 与 §363 的"代际拥有"**相反的需求**（一个必须按代际，一个必须不）。
10. **`setPlayerEquippedRewards` 的槽位**：**三个装备槽是 runtime `1..3`，而槽 `0` 与 `4` 有独立所有者**（`std::copy(..., begin()+1)`）。
11. **`fields127..129`（IDs）与 `132..134`（targets）** —— 各三个，间隔 5。
12. **⭐ `effectivePlayerAbilities` 的四层叠加**（基础 / SideRollingExpert / 工厂购买 / RadarArrow）—— 第二次确认那个架构。
13. **"四层 ⇒ 一个 `effective` 值从不被存储，而是【每次计算】"`** —— 第六次"重推导而不是存储"。
14. **`markPlayerPainted` 的"先设 paint、后计算、再写原生"与 `value_or` 兜底**。
15. **⭐ "可见位与它所揭示的技能在【一个地方】被设 —— 一个没有技能而可见的空侧栏，或技能而侧栏关，都是不应该能通过编辑两个之一而忘记另一个到达的状态"`** —— 第二次"结构必然性"、第三次"配对的字段"。
16. **`setPlayerAbilities` 的五项验证**，而**零速度是合法的**（与 §353 的 `modelScale > 0`**不同**）。

## 九、未闭合点

- `HintStringConfigStringCount` 与提示字符串带 856 的关系。
- `SvCursorHintWeaponBase` / `SvCursorHintMaximum` 的值。
- `centity` 的 `624` 字节布局。
- `SV_ApplySideRollingExpert` / `SV_ApplyFactoryPurchasedPerks` / `SV_ApplyRadarArrow` 各自改哪些 `values[]`。
- `firstDynamicWeapon` 与 `1147` 的关系。
- `sv_snapshot_mp.cpp` 24400 行之后未读取（27,016 行，进度 90%）。
