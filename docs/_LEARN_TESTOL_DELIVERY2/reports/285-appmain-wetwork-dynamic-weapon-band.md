# 285 · **Wetwork 的 52 条动态武器串（实测）**、`chicken_melee_mp` 必须留在基址 1154

## 一、范围

本报告学习 `Appmain.cpp` 3240–3460 行。

## 二、`makeWorldPlayerSampleV1` 的**两个 optional 段**

```php
if (sample.lastReceivedUserCmd)
{
    result.userCmdValid = 1;
    result.userCmdCommandTime = ...;
    ... 九个字段 ...
}
if (sample.weapon)
{
    result.weaponValid = 1;
    result.currentWeaponAssetIndex = ...;
    ... 十个字段 ...
}
```

### 2.1 两个 `valid` 标志

```text
userCmdValid     有 lastReceivedUserCmd 时 = 1
weaponValid      有 weapon 时 = 1
```

**⇒ 两个 optional 用**显式标志**表示而不是魔数。**

**✓ 与 §278 的 `optionalClient`（`0xFFFFFFFF`）**不同做法**。**

### 2.2 而 `viewHeightLerpDown ? 1u : 0u`

**⇒ 一个 `bool` 被转成 `uint32` 的 0/1。**

**⇒ 因为结构要求 4 字节对齐。**

## 三、`toResolvedWeapon` 的**二十八个字段**

```php
{
    .weaponAssetIndex = (uint16)weapon.weaponAssetIndex,
    .ammoIndex = (uint16)weapon.ammoIndex,
    .clipIndex = (int16)weapon.clipIndex,           // ← 【有符号！】
    .clipSize = (uint16)weapon.clipSize,
    .maxAmmo = (uint16)weapon.maxAmmo,
    .weaponType = (uint8)weapon.weaponType,
    .weaponClass = (uint8)weapon.weaponClass,
    .penetrateType = (uint8)weapon.penetrateType,
    .impactType = (uint8)weapon.impactType,
    .fireType = (uint8)weapon.fireType,
    .shotCount = (uint8)weapon.shotCount,
    .fireDelayMilliseconds = (uint16)...,
    .fireTimeMilliseconds = (uint16)...,
    .dropTimeMilliseconds = (uint16)...,
    .raiseTimeMilliseconds = (uint16)...,
    .hipSpreadStandMin ... .adsSpread,          // 7 个 float
    .damageCurve, .hitLocationMultipliers,
    .aimDownSight = weapon.aimDownSight != 0,   // bool
    .hasOverlayReticle = ... != 0,
    .rifleBullet = ... != 0,
    .bulletExplosiveDamage = ... != 0,
    .dualWieldCapable = weapon.dualWieldCapable,
    .fmjPenetration = weapon.fmjPenetration,
    .weaponName = weapon.weaponName,
}
```

### 3.1 **`clipIndex` 是 `int16`**

**⇒ 唯一**有符号**的数值字段。**

**⇒ 因为 `-1` 是"无弹匣"的哨兵**（§240 的 `absentClip = clipIndex == -1`）✓

**⇒ 而其它字段都是无符号。**

### 3.2 而 `weaponType`/`weaponClass`/`penetrateType`/`impactType`/`fireType`/`shotCount` 都是 `uint8`

**⇒ 六个 8 位字段。**

**⇒ 与 §240 的界 `<= numeric_limits<uint8_t>::max()` 一致** ✓

### 3.3 而 `fireDelay`/`fireTime`/`dropTime`/`raiseTime` 是 `uint16`

**⇒ 四个 16 位。**

**⇒ 与 §240 的界 `<= numeric_limits<int16_t>::max()` 一致** ✓

### 3.4 而 `ammoIndex`/`clipSize`/`maxAmmo` 是 `uint16`

**⇒ 三个 16 位。**

**⇒ 与 §240 的 `0x7FF`/`0x1FF`/`0x7FF` 界一致** ✓

## 四、**Wetwork 的 52 条动态武器串**（本组最重要的一段）

### 4.1 那段注释

```php
// CODREF(C-2021-7-25[22-11-33]coop.demo): Wetwork's complete dynamic
// weapon band. The numbers on the left are recording-local and are kept
// only to make later traces readable. Every raw definition is registered
// through CODOL before the outgoing gamestate is assembled, because the
// player's own five classes change where this dense tail begins.
```

### 4.2 三层

```text
1. 5 的 52 条来自 `C-2021-7-25[22-11-33]coop.demo`
2. 左边的数字（1163..1213）是【录制本地】的，只为让后续 trace 可读
3. 每条原始定义都在出站 gamestate 组装之前通过 CODOL 注册
4. 因为【玩家自己的五个职业会改变这条密集尾部从哪里开始】
```

### 4.3 **52 条记录 / 51 个索引**

```text
1163..1213 = 51 个
而记录数 = 51（我数）
```

**让我数一下**：1163, 1164, ..., 1213。

**⇒ 1213 - 1163 + 1 = 51 条。**

### 4.4 而**索引是连续的 1163..1213**

**⇒ 51 个连续索引。**

**⇒ 与 §259 的"模块化记录按资产索引"相关。**

### 4.5 而**两条有不同的第三字段**

```text
1168  ** 1038 140 0 ...      ← 【140，不是 0】
1177  ** 810 72 0 ...        ← 【72，不是 0】
1204  ** 348 11 0 ...        ← 【11，不是 0】
```

**⇒ 三条的第二个数字不是 0。**

**⇒ 而 §253 说"格式是 `** <weapon> <n> <n> <attachment...>`"。**

**⇒ 所以那两个 `<n>` 字段**有时非零**。**

**⇒ 1168 的 `140`、1177 的 `72`、1204 的 `11`。**

**⇒ 这三个数字的语义未知。**

**⚠ 而 §253 里我们自己写 `** <weapon> 0 0 <ids>` 恒为 `0 0`。**

**⇒ 所以**零售会非零而我们不会**。**

**⇒ 这可能是一个**功能缺口**（那两个字段可能控制某种武器状态）。**

### 4.6 而**大部分串以 `9321` 或 `8738` 结尾**

**⇒ 这两个 id 出现最频繁。**

**⇒ 从 §253 的"cs 7184 = `** 646 0 0 8738 9321`" ⇒ 所以 `8738` 与 `9321` 是**默认附件**。**

### 4.7 而**`6825`、`6747`、`6690`、`10545`、`9930`** 也频繁

**⇒ 五个高频 id。**

**从 §253**：`** 682 0 0 9930 8738 6747 10545 9321 6690 6825`

**⇒ 与 1170 的 `** 670 0 0 9930 8738 6747 10545 9321 6690 6825` **几乎相同**（只是 682 vs 670）。**

**⇒ 所以 9930/8738/6747/10545/9321/6690/6825 是**同一套七个附件的固定序列**。**

### 4.8 而 `1164 ** 249 0 0` 与 `1169 ** 225 0 0` 与 `1190 ** 633 0 0` 与 `1203 ** 1155 0 0`

**⇒ 四条**无附件**的武器。**

**⇒ 与 §253 的 `** 249 0 0`（"a weapon with no attachments"）**同一条** ✓**

### 4.9 而 1163 是 `** 646 0 0 8738 9321` = retail cs 7184

**⇒ 与 §253 的"我们的 `** 646 0 0 8738 9321` 与零售 cs 7184 逐字节相同"**完全一致** ✓

**⇒ 所以这**就是**那个串的来源。**

### 4.10 而 `1197 ** 992 0 0 6206 9321`

**⇒ 与 §253 的"零售的 `** 992 0 0 6206 9321`"**完全一致** ✓

**⇒ 而 `6206` 是 TMP 的红点（§252）。**

**⇒ 所以**零售的这个变体就在这条带里**。**

### 4.11 而 1182 是 `** 992 0 0 9321` = retail cs 7204

**⇒ 与 §253 的"我们的 `** 992 0 0 9321` = retail cs 7204"**完全一致** ✓

**⇒ 所以 1197 与 1182 是同一武器（992）的**两个附件变体**。**

**⇒ 完美印证 §253 的"每一种附件组合都是它自己的武器串"。**

### 4.12 而 `13351`、`13199`、`15202`、`1178`、`2795`、`2592`、`14255`、`3282`、`5188`、`15612`、`7978`、`6945`、`4945`、`9840`、`10975`、`1691`、`25`、`1676`、`9416`、`4170`、`15297`、`652`、`5414`、`4274`、`8539`

**⇒ 一批低频 id。**

**⇒ 这些是**更多附件**（更高编号 = 更新的武器/附件）。**

## 五、`chicken_melee_mp` 必须留在基址 1154（本组第二重要）

```php
// `chicken_melee_mp` is the native simple knife definition, not a
// modular weapon. Its verified WeaponDef has no clip/ammo magazine and
// must stay at its base registry index (1154); placing it in the dynamic
// modular table makes simple/melee class registration fail.
if (weapon.weaponName == "chicken_melee_mp")
{
    const auto baseWeaponAssetIndex = weapon.baseWeaponAssetIndex
        ? weapon.baseWeaponAssetIndex : weapon.weaponAssetIndex;
    if (weapon.weaponAssetIndex != baseWeaponAssetIndex ||
        weapon.attachmentCount || !weapon.modularDependencies.empty() ||
        !CodolGameServer::SV_AddSimpleWeaponConfigString(gameState,
            (uint16)weapon.weaponAssetIndex, (uint16)baseWeaponAssetIndex))
    {
        logGameServer("simple knife configstring registration failed index=" + N + " base=" + N);
        return WeaponConfigRegistrationFailure::Weapon;
    }
    return WeaponConfigRegistrationFailure::None;
}
```

### 5.1 四层

```text
1. `chicken_melee_mp` 是【原生简单刀定义】，不是模块化武器
2. 它验证过的 WeaponDef **没有弹匣/弹药**
3. ⇒ 必须留在基址注册表索引（1154）
4. ⇒ 放进动态模块化表会让【简单/近战职业注册失败】
```

### 5.2 而 1154 与 §253 的 `1154` **完全相同**

**§253**："专用服 reset 后 `barrett_mp` = 1154" 与 "客户端 `chicken_melee_mp` = 1154"

**⇒ 所以 1154 在两个进程里是**不同的武器**（Barrett vs 刀）。**

**⇒ 而这里说 `chicken_melee_mp` **必须留在 1154**。**

**⚠ §253 说"专用服 reset 后 barrett_mp = 1154"。**

**⇒ 那么专用服的 1154 是 Barrett 还是刀？**

**⇒ 冲突。**

**可能的解释**：`registerWeaponConfigString` 在**客户端**路径上跑，而客户端的 1154 是刀；专用服 reset 后是 Barrett。

**⚠ 这是一处需要核对的 1154 语义冲突。**

### 5.3 而**四个拒绝条件**

```text
weapon.weaponAssetIndex != baseWeaponAssetIndex   ⇒ 拒绝
weapon.attachmentCount                            ⇒ 拒绝（刀不能有附件）
!modularDependencies.empty()                      ⇒ 拒绝（刀不能有依赖）
SV_AddSimpleWeaponConfigString 失败                ⇒ 拒绝
```

**⇒ 三项前置 + 一项调用。**

**⇒ 所以"刀必须无附件无依赖且索引等于基址"。**

### 5.4 而 `baseWeaponAssetIndex ? : weaponAssetIndex` 的回退

**⇒ 如果 `baseWeaponAssetIndex` 是 0 ⇒ 用 `weaponAssetIndex`。**

**⇒ 所以"未设置基址 ⇒ 认为它就是基址"。**

## 六、`registerWeaponConfigString` 的一般路径

```php
std::vector<uint16> attachmentAssetIndexes;
attachmentAssetIndexes.reserve(weapon.attachmentCount);
for (index < weapon.attachmentCount)
    attachmentAssetIndexes.push_back((uint16)weapon.attachmentAssetIndexes[index]);
const auto originalWeaponAssetIndex = weapon.weaponAssetIndex;

for (const auto &dependency : weapon.modularDependencies)
    if (!SV_RegisterModularWeaponConfigString(gameState, firstDynamicWeaponAssetIndex, dependency))
        return WeaponConfigRegistrationFailure::Dependency;

const auto registeredWeaponAssetIndex = SV_RegisterModularWeaponConfigString(
    gameState, firstDynamicWeaponAssetIndex, ...);
```

### 6.1 三段

```text
① 收集附件索引
② 【先】注册全部依赖
③ 【后】注册武器本体
```

### 6.2 **"先依赖后本体"**

**⇒ 与 §247/§248 的"发布顺序是严格依赖链"一致** ✓

**⇒ 因为本体的模块化串可能引用依赖的索引。**

### 6.3 而 `originalWeaponAssetIndex` 被保存

**⇒ 因为注册后 `weapon.weaponAssetIndex` 会变（新索引）。**

**⇒ 所以原值必须留存以便日志/核对。**

## 七、`WeaponConfigRegistrationFailure` 的**三个值**

```cpp
enum class WeaponConfigRegistrationFailure { None, Dependency, Weapon };
```

**⇒ 三个**：

```text
None        成功
Dependency  依赖失败
Weapon      本体失败
```

**⇒ 两级失败** —— 与 §281 的 `InvalidMessage`/`Rejected` 两级同族。

## 八、关键结论

1. **两个 optional 用显式 `valid` 标志**（而不是魔数）。
2. **`clipIndex` 是唯一有符号的数值字段** —— 因为 `-1` 是"无弹匣"哨兵。
3. **Wetwork 的 52 条动态武器串**来自 `C-2021-7-25[22-11-33]coop.demo`，索引 1163..1213 是**录制本地**的。
4. **三条的第二个数字非零**（1168 的 140、1177 的 72、1204 的 11）—— 而我们恒写 `0 0`。**可能是一个功能缺口。**
5. **1163 = `** 646 0 0 8738 9321` = retail cs 7184** —— 与 §253 完全一致。
6. **1182 = `** 992 0 0 9321` = retail cs 7204** 与 **1197 = `** 992 0 0 6206 9321`** 是同一武器的两个附件变体 —— 完美印证 §253 的"每种组合是独立串"。
7. **四条无附件武器**（1164/1169/1190/1203）。
8. **`chicken_melee_mp` 必须留在 1154** —— 否则简单/近战职业注册失败。
9. **1154 的语义冲突**（§253 说专用服 reset 后是 Barrett）。
10. **"先依赖后本体"** 的注册顺序。
11. **`originalWeaponAssetIndex` 被保存**（因为注册后索引会变）。
12. **`WeaponConfigRegistrationFailure` 的两级失败**（Dependency / Weapon）。

## 九、未闭合点

- `**` 串的第二个数字（140/72/11）的语义。
- 1154 在专用服/客户端的语义冲突。
- 52 条记录的完整性与"五个职业改变尾部起点"的关系。
- `Appmain.cpp` 3460 行之后未读取。
