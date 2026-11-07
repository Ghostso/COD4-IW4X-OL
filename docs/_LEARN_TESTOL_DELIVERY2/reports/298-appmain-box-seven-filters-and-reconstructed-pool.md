# 298 · **神秘箱的七层过滤**、`alternateChildren` 的排除、`Ammo` 权重的重归一化

## 一、范围

本报告学习 `Appmain.cpp` 6099–6320 行。

## 二、神秘箱武器池的**七层过滤**（本组最重要的一段）

### 2.1 完整判据

```php
std::size_t rejected{};
std::vector<uint16> bases;
if (dynamicTail)
{
    bases.reserve(dynamicTail->size());
    // Read both ends of the native definition+3720 links now.
    // Child modes are not independent box rewards, even when
    // their own outgoing alt pointer is zero. Do not use the
    // process-wide cached alt table for this map's new tail.
    std::set<uint16> alternateChildren;
    for (uint32 host = 1; host < WeaponConfigStringCount; ++host)
        if (const auto alt = Bindings.altWeaponAssetIndex(host)) alternateChildren.insert(alt);
    for (offset < dynamicTail->size())
    {
        const auto asset = *firstDynamic + offset;
        if (asset >= WeaponConfigStringCount) { ++rejected; continue; }                    // ①
        const auto &config = (*dynamicTail)[offset];
        boxResources.weaponBases.emplace((uint16)asset, config.baseWeaponAssetIndex);
        if (!config.baseWeaponAssetIndex ||
            find(bases, config.baseWeaponAssetIndex) != bases.end()) { ++rejected; continue; }   // ②③
        ClientWeaponSelection selection{};
        if (!Bindings.readWeaponSelection(asset, selection)) { ++rejected; continue; }              // ④
        const auto weapon = toResolvedWeapon(selection);
        if (weapon.weaponType != WeaponTypeBullet || !weapon.clipSize || !weapon.maxAmmo)
        { ++rejected; continue; }                                                                   // ⑤
        SvResolvedWeapon alternate;
        if (SV_LookupAltWeaponForHost((uint16)asset, alternate) ||
            alternateChildren.contains((uint16)asset))
        {
            logGameServer("Factory box exclude alternate asset=" + asset);
            ++rejected; continue;                                                                    // ⑥⑦
        }
        bases.push_back(config.baseWeaponAssetIndex);
        const auto center = Bindings.weaponDisplayBodyCenter((uint16)asset);
        boxResources.weapons.push_back({(uint16)asset, "** " + baseWeaponAssetIndex, center.value_or({})});
    }
}
```

### 2.2 七层

```text
① asset < WeaponConfigStringCount（1700）
② baseWeaponAssetIndex 非零
③ baseWeaponAssetIndex 【未出现过】（去重）
④ readWeaponSelection 成功
⑤ weaponType == Bullet 且 clipSize 非零 且 maxAmmo 非零
⑥ 【不是】某个 host 的 alt 武器
⑦ 【不在】alternateChildren 集合里
```

### 2.3 **⑥ 与 ⑦ 是同一个检查的两半**

```php
SV_LookupAltWeaponForHost(asset, alternate)          // ⑥ 正向：这个 asset 是某 host 的 alt
|| alternateChildren.contains(asset)                 // ⑦ 反向：这个 asset 出现在任何 +3720 里
```

**⇒ 两个 OR ⇒ 任一为真就排除。**

### 2.4 而那句关键注释

```php
// Read both ends of the native definition+3720 links now.
// Child modes are not independent box rewards, even when
// their own outgoing alt pointer is zero. Do not use the
// process-wide cached alt table for this map's new tail.
```

### 2.5 四层

```text
1. 现在就读**原生 `definition+3720` 链接的两端**
2. **子模式不是独立的箱子奖励**
3. 即使它们自己的**出站 alt 指针是零**
4. ⇒ **不要**为这张地图的新尾部使用**进程级缓存的 alt 表**
```

### 2.6 而"子模式的出站指针是零"是关键

**⇒ 所以一个 alt 武器可能**没有自己的 alt** ⇒ 靠 ⑥ 查不到它。**

**⇒ 但 ⑦ 的 `alternateChildren` 是从**所有 host** 收集的 ⇒ 能查到。**

**✓ 两个方向互补。**

### 2.7 而**"不要用进程级缓存"**

**⇒ 与 §259 的"验证过的提示缓存"**不同** —— 那里用缓存，这里明确不用。**

**⇒ 因为"这张地图的新尾部"可能包含**旧地图的 alt 关系**。**

**⇒ 所以每地图重算。** ✓

### 2.8 而 `for (host = 1; host < 1700; ++host)` 是 **1699 次 `altWeaponAssetIndex`**

**⇒ 而每次 `altWeaponAssetIndex` 读 `+3720`。**

**⇒ 1699 次原生读 — 一次地图加载 ⇒ 可接受。**

## 三、`boxResources.weaponBases` 的**无条件填**

```cpp
boxResources.weaponBases.emplace((uint16)asset, config.baseWeaponAssetIndex);
if (!config.baseWeaponAssetIndex || find(bases, ...) != bases.end()) { ++rejected; continue; }
```

### 3.1 ⚠ **`weaponBases` 在**过滤之前**就填了**

**⇒ 所以被拒绝的 asset 也在 `weaponBases` 里。**

**⚠ 这可能是有意的（"所有 asset 的基础映射"）或一个缺陷（"只有可玩的"）。**

**⇒ 从命名看 `weaponBases` 应该覆盖所有。**

**✓ 从"`weapons` 是可玩的而 `weaponBases` 是映射表"看是**有意的**。**

## 四、`** <baseWeaponAssetIndex>` 的**字符串**

```cpp
boxResources.weapons.push_back({(uint16)asset, "** " + std::to_string(config.baseWeaponAssetIndex), center.value_or({})});
```

**⇒ 只写 `** <base>` 而**没有** `0 0` 与附件！**

**⚠ 与 §253 的 `** <weapon> 0 0 <ids>` 格式**不同**。**

**⇒ 所以这是一个**用途不同**的字符串**（用于显示/识别而不是发布配置串）。**

**⇒ 待读 `SvFactoryBoxWeapon` 的定义。**

## 五、`weaponDisplayBodyCenter` 的**失败容忍**

```cpp
const auto center = Bindings.weaponDisplayBodyCenter((uint16)asset);
boxResources.weapons.push_back({..., center.value_or(std::array<float,3>{})});
```

**⇒ 失败 ⇒ 零点。**

**⇒ 而 §259 里 `weaponDisplayBodyCenter` 有**九项验证** ⇒ 所以失败是正常的（很多武器没有可用的包围盒）。**

**✓ 与"缺失只禁用 FX"同族。**

## 六、`Factory box resources` 的**五项日志**

```php
"Factory box resources dynamic=" + (dynamicTail ? size : 0) +
" playable=" + boxResources.weapons.size() +
" duplicateOrRejected=" + rejected +
" firstDynamic=" + firstDynamic.value_or(0) +
" animations=" + openAnimation + "," + closeAnimation +
" tree=" + animationTree
```

### 6.1 六个量

```text
dynamic              尾部大小
playable             通过过滤的
duplicateOrRejected  拒绝的
firstDynamic         基址
animations           两个动画
tree                 动画树
```

**⇒ 而 `duplicateOrRejected` 把**去重**与**拒绝**合并** —— 与 §284 的"`duplicateOrRejected`"同族。**

**⚠ 合并了两个不同的原因。**

## 七、`OLMOD_FACTORY_RECONSTRUCTED_POOL` 的**重建池**（本组第二重要）

```php
// OLMOD(factory_special_reconstruction): fixed named catalogue;
// class guns remain an explicit alternate pool, never its source.
boxResources.reconstructedPool = true;
boxResources.weapons.clear();
boxResources.weaponBases.clear();
for (const auto &entry : FactoryReconstructedBoxPool)
{
    if (entry.kind == SvFactorySpecialKind::Ammo) continue;                       // ① 跳过 Ammo
    const auto asset = Bindings.resolveWeaponConfigStringIndex(entry.weapon);
    if (!asset || !*asset) { logGameServer("Factory special unavailable name=" + entry.weapon); continue; }  // ②
    if (entry.equipment)
    {
        const auto equipment = Bindings.resolveFactorySpecialEquipment(entry.weapon);
        if (!equipment || equipment->weaponAssetIndex != *asset) continue;        // ③
        boxResources.equipment.emplace(*asset, *equipment);
    }
    else
    {
        ClientWeaponSelection selection{};
        if (!Bindings.readWeaponSelection(*asset, selection) || selection.weaponType != 2) continue;  // ④ weaponType == 2
    }
    boxResources.weaponBases.emplace(*asset, *asset);
    boxResources.weapons.push_back({*asset, entry.weapon, weaponDisplayBodyCenter(*asset).value_or({}), entry.weight});
    specialWeapons.emplace(*asset, entry.kind);
    logGameServer("Factory special reconstruction name=" + entry.weapon + " asset=" + *asset + " weight=" + entry.weight);
}
logGameServer("Factory special reconstruction eligible=" + specialWeapons.size() +
    " ammoWeight=15; weights renormalized, not original CODOL odds");
```

### 7.1 五层

```text
1. **固定命名的目录**
2. 职业枪仍是**显式的备选池，绝不是它的来源**
3. ⇒ 清空 `weapons` 与 `weaponBases`（覆盖动态尾部的结果）
4. ⇒ 逐条目：`Ammo` 跳过、解析名字、装备走 `resolveFactorySpecialEquipment`、非装备走 `weaponType == 2`
5. ⇒ `weaponBases[asset] = asset`（**自己是自己的基址**）
```

### 7.2 **"`Ammo` 跳过而 `ammoWeight=15`"**

**⇒ 三层的矛盾**：

```text
1. `Ammo` 条目**被跳过**（不进 `weapons`）
2. 而日志说 `ammoWeight=15`
3. ⇒ 所以弹药权重是**在别处处理的**（箱子抽到弹药时）
```

**⇒ 而"权重被**重新归一化**，不是原版 CODOL 的概率"。**

**✓ 一个诚实的声明。**

### 7.3 而 `weaponType == 2`

**⚠ 与子弹路径的 `weaponType != Bullet`（`WeaponTypeBullet` 大概是 0 或 1）。**

**⇒ 而 §254/§255 里 `weaponType == 1` 是投掷物。**

**⇒ 所以 `weaponType == 2` 是**第三种**类型。**

**⇒ 可能是"特殊武器"（奇迹武器）。**

### 7.4 而 `entry.equipment` 的两条路

```text
设备/投掷物  ⇒ resolveFactorySpecialEquipment（§254 的五白名单）
其它         ⇒ readWeaponSelection + weaponType == 2
```

**⇒ 而 `resolveFactorySpecialEquipment` 的五个名字：**

```text
trap_fire_zm / trap_freeze_zm / trap_shock_zm / trap_shrink_zm / zombie_cymbal_monkey
```

**⇒ 五个陷阱/猴子。**

## 八、**七个手雷/战术装备**

```php
using Kind = SvFactorySpecialKind;
for (const auto &[name, kind] : std::array{
        pair{"frag_grenade_mp", Kind::Grenade}, pair{"fragshort_grenade_mp", Kind::Grenade},
        pair{"semtex_mp", Kind::Grenade}, pair{"flash_grenade_mp", Kind::Flash},
        pair{"concussion_grenade_mp", Kind::Flash}, pair{"emp_grenade_mp", Kind::Flash},
        pair{"smoke_grenade_mp", Kind::Smoke}})
{
    const auto asset = Bindings.resolveWeaponConfigStringIndex(name);
    if (!asset || !Bindings.resolveGrenadeLaunchParameters(*asset)) continue;          // ①
    const auto blast = Bindings.resolveGrenadeBlastParameters(*asset);
    if (kind == Kind::Grenade && !blast) continue;                                     // ②
    specialWeapons.emplace(*asset, kind);
    specialCombat.emplace(*asset, blast ? SvFactorySpecialCombat{radius, inner, outer, traceAlongContact}
                                        : SvFactorySpecialCombat{250, 0, 0, false});
    logGameServer("Factory offhand ready name=" + name + " asset=" + *asset);
}
```

### 8.1 七个名字

```text
frag_grenade_mp         Grenade
fragshort_grenade_mp    Grenade
semtex_mp               Grenade
flash_grenade_mp        Flash
concussion_grenade_mp   Flash
emp_grenade_mp          Flash
smoke_grenade_mp        Smoke
```

### 8.2 而 **`Grenade` 必须有 blast 而 `Flash`/`Smoke` 不必**

```cpp
if (kind == Kind::Grenade && !blast) continue;
```

**⇒ 因为闪光/烟雾**没有伤害** ⇒ `blast` 只为伤害。**

**✓ 语义正确。**

### 8.3 而 `SvFactorySpecialCombat{250, 0, 0, false}` 的**默认值**

**⇒ `radius = 250`、`inner = 0`、`outer = 0`、`traceAlongContact = false`。**

**⇒ 所以一个无 blast 的闪光/烟雾有一个**250 单位的半径**但**零伤害**。**

**⇒ 因为半径用于**效果范围**（闪光/烟雾的视觉）。**

**✓ 合理。**

## 九、**职业装备的变体**

```php
// Class equipment can be a named variant rather than the base
// grenade above. Admit only supported families and validate the
// variant's own native launch/blast fields; never replace its ID.
std::map<uint16, string> equippedNames;
{
    const lock_guard loadoutLock(LoadoutMutex);
    for (const auto &[xuid, member] : RegisteredSessionAssets.members())
        for (const auto &[loadout, equipment] : member.offhands)
            for (const auto &weapon : equipment.weapons)
                if (weapon.weaponAssetIndex)
                    equippedNames.emplace(weapon.weaponAssetIndex, weapon.weaponName);
}
for (const auto &[asset, name] : equippedNames)
{
    if (specialWeapons.contains(asset)) continue;                                     // ① 已处理
    optional<Kind> kind;
    if (name.find("frag") != npos || name.find("semtex") != npos) kind = Grenade;
    else if (name.find("flash") != npos || name.find("concussion") != npos ||
             name.find("emp_grenade") != npos) kind = Flash;
    else if (name.find("smoke") != npos) kind = Smoke;
    const auto launch = resolveGrenadeLaunchParameters(asset);
    const auto blast = resolveGrenadeBlastParameters(asset);
    if (!kind || !launch || (*kind == Grenade && !blast)) { logGameServer("... unsupported ..."); continue; }  // ②③
    specialWeapons.emplace(asset, *kind);
    specialCombat.emplace(asset, blast ? {...} : {250,0,0,false});
    logGameServer("Factory offhand variant ready name=" + name + " asset=" + asset);
}
```

### 9.1 四层

```text
① 已处理的跳过
② 按名字的 **子串** 分类（frag/semtex/flash/concussion/emp_grenade/smoke）
③ launch 必须存在，且 Grenade 还需 blast
④ **从已注册的会话资产**收集（不是硬编码）
```

### 9.2 而"**绝不在替换它的 ID**"

```php
// ... never replace its ID.
```

**⇒ 三层**：

```text
1. 变体保留**它自己的 asset id**
2. 不映射回基础手雷
3. ⇒ 因为客户端的模型/特效依赖那个 id
```

**⇒ 与 §286 的"与 SessionStart 逐字节相同是不变式"同族。**

### 9.3 ⚠ **子串匹配的顺序**

```text
frag / semtex        ⇒ Grenade
flash / concussion / emp_grenade  ⇒ Flash
smoke               ⇒ Smoke
```

**⇒ 如果一个名字同时含 `frag` 与 `smoke` ⇒ 第一个分支赢 ⇒ **Grenade**。**

**⚠ 但没有 `if/else` 的**优先注释**。**

## 十、`trapFx` 的**四个特效与猴子**

```cpp
if (boxResources.reconstructedPool) trapFx = {effectModel, effectBone, {
    effectParameter("maps/zombie/fx_zombie_fire_trap_med_sh").value_or(0),
    effectParameter("maps/zombie/fx_freeze_trap_active_loop").value_or(0),
    effectParameter("maps/zombie/fx_zombie_wire_spark").value_or(0),
    effectParameter("maps/zombie/fx_zombie_shrink_trap_looping").value_or(0)}};
if (boxResources.reconstructedPool)
{
    trapFx.monkeyModel     = resolveModelConfigStringIndex("weapon_zombie_monkey_bomb").value_or(0);
    trapFx.monkeyAnimation = resolveAnimConfigStringIndex("o_monkey_bomb").value_or(0);
    const array<uint16,1> monkeyAnimations{trapFx.monkeyAnimation};
    if (trapFx.monkeyAnimation)
        trapFx.monkeyTree = resolveScriptModelAnimationTree(monkeyAnimations).value_or(0);
    trapFx.monkeySong = resolveSoundAliasEventParameter("zmb_monkey_song").value_or(0);
}
```

### 10.1 四个陷阱特效（与 §254 的四个 trap 对应）

```text
fire     maps/zombie/fx_zombie_fire_trap_med_sh
freeze   maps/zombie/fx_freeze_trap_active_loop
shock    maps/zombie/fx_zombie_wire_spark
shrink   maps/zombie/fx_zombie_shrink_trap_looping
```

**⇒ 四个 —— 而 §254 的白名单有四个 `trap_*_zm`** ✓

### 10.2 而猴子的**四个资源**

```text
model      weapon_zombie_monkey_bomb
animation  o_monkey_bomb
tree       【从 animation 合成】
song       zmb_monkey_song
```

**⇒ 而 `monkeyTree` 只在 `monkeyAnimation` 非零时才查。**

**✓ 一个正确的依赖顺序。**

## 十一、`teslaView` 的三个

```php
const std::array names{
    "maps/zombie/fx_zombie_tesla_tube_view",
    "maps/zombie/fx_zombie_tesla_tube_view2",
    "maps/zombie/fx_zombie_tesla_tube_view3"};
for (i) boxResources.teslaViewEffects[i] = effectParameter(names[i]).value_or(0);
```

**⇒ 三个** —— 第一个无数字后缀，后两个有 `2`/`3`。

**⚠ 一个不一致的命名。**

## 十二、`ZM presentation preview` 的**三个量**

```php
logGameServer("ZM presentation preview outfits=" + zmOutfits.size() +
    " deaths=" + zmDeaths.size() + " reconstructed-selection=1");
```

**⇒ 三个** —— 而 `reconstructed-selection=1` 是一个**固定的断言**（不是从状态读）。**

**⚠ 所以它只是标注"这是重建的选择"。**

## 十三、关键结论

1. **神秘箱的七层过滤**（界、基址非零、去重、读取成功、Bullet + 有弹匣、非 alt、不在 children）。
2. **⑥⑦ 是同一个检查的两半**（正向 lookup 与反向 children 集合）。
3. **"子模式的出站 alt 指针是零"** ⇒ 所以需要反向集合。
4. **"不要用进程级缓存的 alt 表"** —— 因为新尾部可能含旧地图的关系。
5. **`weaponBases` 在过滤之前填** —— 覆盖所有 asset（有意）。
6. **箱子的 `** <base>` 字符串与 §253 的格式不同** —— 用于显示而非发布。
7. **`weaponDisplayBodyCenter` 失败容忍**（零点）。
8. **`duplicateOrRejected` 合并了两个原因**。
9. **重建池清空动态尾部的结果**，只从固定目录建。
10. **`Ammo` 跳过而 `ammoWeight=15`** —— 弹药在别处处理。
11. **"权重被重新归一化，不是原版 CODOL 的概率"** —— 一个诚实的声明。
12. **`weaponType == 2` 是第三种类型**（特殊武器）。
13. **七个手雷/战术**，而 `Grenade` 必须有 blast、`Flash`/`Smoke` 不必。
14. **`{250, 0, 0, false}` 的默认**（半径 250 但零伤害）。
15. **职业变体"绝不替换它的 ID"**。
16. **子串分类的顺序无注释**（`frag` + `smoke` 会归 Grenade）。
17. **四个陷阱特效** 与 §254 的白名单一一对应。
18. **猴子的四个资源有正确的依赖顺序**。
19. **`teslaView` 的三个命名不一致**（第一个无后缀）。

## 十四、未闭合点

- `weaponType == 2` 的确切语义。
- `SvFactoryBoxWeapon` 的 `** <base>` 字符串用途。
- 子串分类的优先级是否有意。
- `Appmain.cpp` 6320 行之后未读取。
