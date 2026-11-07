# 297 · **"只在每个已加载的伤害变体都同意时才复用骨骼索引"**、`250` 的哨兵、`tag_origin` 的占位符

## 一、范围

本报告学习 `Appmain.cpp` 5880–6100 行。

## 二、`outfit` 的**十三个字段**

```cpp
CodolGameServer::SvZmOutfit outfit{body, head};
outfit.color = color;
if (deathFx == "1")
{
    outfit.torso        = lookup(stem + "_body_torso_1");
    outfit.lower        = lookup(stem + "_body_lowclean");
    outfit.behead       = lookup(stem + "_body_behead");
    outfit.neckBone     = boneIndex(stem+suffix, "j_neck").value_or(255);
    outfit.torsoBone    = boneIndex(stem+"_body_torso_1", "j_spinelower").value_or(255);
    outfit.leftArmOff   = lookup(stem+"_body_larmoff_1");
    outfit.leftArmBone  = boneIndex(stem+"_body_larmoff_1", "j_shoulder_le").value_or(255);
    outfit.rightArmOff  = lookup(stem+"_body_rarmoff_1");
    outfit.rightArmBone = boneIndex(stem+"_body_rarmoff_1", "j_shoulder_ri").value_or(255);
    outfit.shockBone    = boneIndex(stem+suffix, "j_spineupper").value_or(255);
}
```

### 2.1 十三个

```text
body / head / color          （3）
torso / lower / behead       （3）模型
leftArmOff / rightArmOff     （2）模型
neckBone / torsoBone         （2）骨骼
leftArmBone / rightArmBone   （2）骨骼
shockBone                    （1）骨骼
```

### 2.2 **`255` 是"无骨骼"的哨兵**

**⇒ 与 §242 的 `addressable`、§235 的 `INT32_MIN` 同族。**

**⇒ 而 255 是 `uint8` 的满值 ⇒ 所以骨骼索引 0..254。**

**⇒ 与 §261 的 `modelBoneIndex` 返回 `uint8` 且 `i < 255` **完全一致** ✓**

## 三、**"只在每个已加载的伤害变体都同意时才复用骨骼索引"**（本组最重要的一段）

```php
// Reuse a body-bone index only if every loaded damage variant agrees;
// never guess a composed head index.
for (const auto tail : {"_body_torso_1", "_body_rarmoff_1", "_body_larmoff_1"})
    if (lookup(stem + tail) &&
        boneIndex(stem + tail, "j_spineupper").value_or(255) != outfit.shockBone)
        outfit.shockBone = 255;
```

### 3.1 三层

```text
1. 只在**每一个已加载的伤害变体都同意**时才复用一个身体骨骼索引
2. 遍历三个变体：torso / rarmoff / larmoff
3. 任一不同 ⇒ shockBone = **255**（放弃）
```

### 3.2 **这是一个"一致性即信任"的规则**

**⇒ 与 §261 的"骨骼名用附件表会返回武器名"**完全相关** —— 因为不同模型的同编号骨骼可能不是同一个骨骼。**

**⇒ 所以"如果三个变体都说 `j_spineupper` 是同一个索引 ⇒ 可信"。**

**✓ 一个**保守且正确**的规则。**

**⇒ 与 §264 的"二义即失败"、§296 的"重复即拒绝"同族**（第七次"不一致就放弃"）。

### 3.3 而"**绝不当猜一个组合后的头索引**"

```php
// Eye attachment indices are composed-DObj indices,
// not the standalone head model's bone numbers.
// Keep absent until that composition is resolved.
```

**⇒ 三层**：

```text
1. 眼睛的附件索引是**组合后的 DObj 索引**
2. 不是**独立头模型**的骨骼编号
3. ⇒ 在组合被解析之前**保持缺失**
```

**⇒ 与 §261 的 `attachmentBoneIndex` 的"身体骨骼数 + 附件局部索引"**完全一致** ✓

**⇒ 所以"组合后的索引"= `count + local`。**

## 四、`tag` lambda 的**三层验证**

```cpp
const auto tag = [&](const char *name) {
    const auto index = attachmentIndex(stem+suffix, stem+"_head", name);
    if (!index) return std::uint8_t{255};
    for (const auto tail : {"_body_torso_1","_body_rarmoff_1","_body_larmoff_1"})
        if (lookup(stem+tail) && attachmentIndex(stem+tail, stem+"_head", name) != index)
            return std::uint8_t{255};
    return *index;
};
```

### 4.1 三层

```text
① 基础身体的附件索引
② 三个伤害变体的**同一附件**必须给**同一个索引**
③ 否则 255
```

**⇒ 与 §3 的规则**完全同构**（只是用 `attachmentIndex` 而不是 `boneIndex`）。**

### 4.2 而"记录的事件 113 目标是组合后的 `left-eye86` / `tag_mouth97`"

```php
// CODREF(actor_head_attachment): recorded event113
// targets composed left-eye86 / tag_mouth97. Resolve
// names against every supported body, not magic IDs.
```

**⇒ 三层**：

```text
1. 记录的事件 113 目标是**组合后的** `left-eye86` 与 `tag_mouth97`
2. ⇒ 按名字对着**每一个支持的身体**解析
3. ⇒ **不用魔法 ID**
```

**⇒ 所以 86 与 97 是**那个组合**的索引 —— 而这里**不硬编码**它们。**

**⇒ 与 §243 的"index 1188 是加载顺序证据不是 ABI"**第四次**同族。**

### 4.3 而 `phase` 的三色

```cpp
const char *phase = color == Blue ? "blue"
    : color == Yellow ? "yellow"
    : color == Orange ? "orange" : nullptr;
// Ordinary body-color pairing only. The original
// special red/global switch trigger is unresolved.
if (phase) { ... }
```

**⇒ 三层**：

```text
1. 只有 blue/yellow/orange 三色有 phase
2. **只做普通的身体-颜色配对**
3. ⇒ 原来的**特殊红色/全局开关触发**是**未解析的**
```

**⚠ 所以 5 色里只有 3 色有眼睛发光。**

**⇒ 而 `Base` 与 `Red` 没有** —— 一个有意的排除（因为"特殊红灯开关未解析"）。**

## 五、两个特效名的格式

```php
outfit.eyeGlow = effectParameter("maps/zombie/zm_eye_lensflare_" + std::string(phase)).value_or(0);
outfit.mouthGlow = effectParameter("zombie/mouth_glow_" + std::string(phase) + "_small").value_or(0);
```

### 5.1 两个模板

```text
maps/zombie/zm_eye_lensflare_<phase>
zombie/mouth_glow_<phase>_small
```

**⇒ 而 `_small` 只出现在嘴部。**

**⚠ 所以眼睛没有 `_small` 变体或用了另一个。**

## 六、`SvZmDeathSpecs` 的**八个字段**

```cpp
for (const auto &spec : SvZmDeathSpecs)
    if (const auto alias = resolveAnimConfigStringIndex(spec.name); alias && *alias)
        zmDeaths.push_back({*alias, spec.milliseconds, spec.weight, 0,0,0,0, spec.electrical});
```

### 6.1 八个

```text
animation        （`*alias`）
milliseconds     （`spec.milliseconds`）
weight           （`spec.weight`）
loopAnimation    （0）
downAnimation    （0）
loopMilliseconds （0）
downMilliseconds （0）
electrical       （`spec.electrical`）
```

**⇒ 前三个来自 spec，中间四个初始化为 0（待 refined 填充），最后一个来自 spec。**

### 6.2 而"解析不出就**不加入**"

**⇒ 所以 `zmDeaths` 只含解析成功的。**

**⇒ 与 §296 的"空条目保持未解析"同族**（第十次"不发明"）。

## 七、**四组 refined 对**（本组第二重要）

```cpp
// CODREF(xanim_shared_actor_blend): native 0x786E70 clock;
// original July31 demo actor808 A-loop -> E-down (850ms),
// 727 B->B (600), 799 D->B (550), 743 E->A (350).
// OLMOD(refined_fx): representative recorded pairs, not a
// recovered selection table. No verified C-loop pair here.
struct Pair { const char *base, *loop, *down; unsigned hold, settle; };
const Pair pairs[]{
    {"ai_zombie_tesla_death_a","ai_zombie_tesla_death_a_loop","ai_zombie_tesla_death_e_down",850,3250},
    {"ai_zombie_tesla_death_b","ai_zombie_tesla_death_b_loop","ai_zombie_tesla_death_b_down",600,3884},
    {"ai_zombie_tesla_death_d","ai_zombie_tesla_death_d_loop","ai_zombie_tesla_death_b_down",550,3884},
    {"ai_zombie_tesla_death_e","ai_zombie_tesla_death_e_loop","ai_zombie_tesla_death_a_down",350,3850}};
```

### 7.1 四组与四个数

```text
actor808   A-loop → E-down   850 ms   （settle 3250）
727        B → B             600 ms   （settle 3884）
799        D → B             550 ms   （settle 3884）
743        E → A             350 ms   （settle 3850）
```

**⇒ 所以 `hold` = "循环多久后切到下坠"而 `settle` = "下坠多久后稳定"。**

### 7.2 而**四个 `down` 的错配**

```text
A → E_down
B → B_down    （同字母）
D → B_down    （【D 用 B 的 down】）
E → A_down    （【E 用 A 的 down】）
```

**⇒ 所以只有 B 是同字母，其它三个都跨字母。**

**⇒ 这与注释"representative recorded pairs"一致 —— 是**录制的观测**而不是规律。**

### 7.3 而"**没有已验证的 C 循环对**"

```php
// No verified C-loop pair here.
```

**⇒ 所以 C 缺失。**

**⇒ 与 §296 的"空条目保持未解析"同族**（第十一次）。

### 7.4 而匹配是**按 base 动画名**

```cpp
for (auto &clip : zmDeaths)
    if (clip.animation == *base)
    {
        clip.loopAnimation = *loop;
        clip.downAnimation = *down;
        clip.loopMilliseconds = p.hold;
        clip.downMilliseconds = p.settle;
        logGameServer("ZMFX sequence base=" + *base + " loop=" + *loop + " down=" + *down);
    }
```

**⇒ 所以只在 `zmDeaths` 里**已有**那个 base 时才补。**

**⇒ 如果 base 解析失败而没进 `zmDeaths` ⇒ 这一对**完全不生效**，且**没有日志**。**

**⚠ 一处静默的跳过。**

### 7.5 而三个 `resolveAnimConfigStringIndex` 都成功才补

```cpp
if (!base || !loop || !down) continue;
```

**⇒ 三层全成才补。**

**⇒ 而失败时**没有日志**。**

**⚠ 与 §296 的"重复即拒绝且明说"**不同** —— 这里静默。**

## 八、`zmDeathFx` 的**四个特效**

```php
zmDeathFx.neck  = effectParameter("misc/fx_zombie_bloodspurt_codo").value_or(0);
zmDeathFx.torso = effectParameter("weapon/bullet/fx_flesh_gib_fatal_01_blue").value_or(0);
zmDeathFx.bo1Derived = (OLMOD_FACTORY_BO1_DAMAGE == "1");
zmDeathFx.refined = zmDeathFx.bo1Derived && (OLMOD_FACTORY_REFINED_FX == "1");
```

### 8.1 两个特效名

```text
misc/fx_zombie_bloodspurt_codo        脖子
weapon/bullet/fx_flesh_gib_fatal_01_blue   躯干
```

### 8.2 而"三层的开关依赖"

```text
OLMOD_FACTORY_DEATH_FX = "1"          ⇒ 基础
OLMOD_FACTORY_BO1_DAMAGE = "1"        ⇒ bo1Derived
OLMOD_FACTORY_REFINED_FX = "1" 且 bo1Derived ⇒ refined
```

**⇒ `refined` 是**三层的**（必须 BO1 也开）。**

**✓ 一个正确的依赖链。**

## 九、**`tesla` 的电气武器三 + 排除四**

```php
for (const auto name : {"tesla_gun_zm","tesla_gun_upgraded","tesla_gun_upgraded_zm"})
    if (const auto index = resolveWeaponConfigStringIndex(name); index && *index)
    {
        zmDeathFx.electricalWeapons.push_back(*index);
        logGameServer("ZMFX electrical weapon name=" + name + " index=" + *index);
    }
for (const auto name : {"m1911_zm","flamethrower_zm","freezegun_zm","freezegun_upgraded_zm"})
    if (const auto index = resolveWeaponConfigStringIndex(name); index && *index)
        zmDeathFx.excludedWeapons.push_back(*index);
```

### 9.1 三 + 四

```text
电气（触发电击死亡）  tesla_gun_zm / tesla_gun_upgraded / tesla_gun_upgraded_zm
排除（不触发电击）    m1911_zm / flamethrower_zm / freezegun_zm / freezegun_upgraded_zm
```

### 9.2 而"**字面名字存在于所供的 CODOL 僵尸 zone**"

```php
// Literal names exist in the supplied CODOL zombie zone.
// Accept only names actually resolved in this map's weapon band.
// This is BO1-derived classification, not recovered CODOL damage code.
```

**⇒ 三层**：

```text
1. 字面名字**存在于**所供的 CODOL 僵尸 zone
2. ⇒ **只接受在这个地图的武器带里实际解析出来的名字**
3. ⇒ 这是 **BO1 派生的分类**，不是恢复的 CODOL 伤害代码
```

**⇒ 与 §292 的"没有名字被发明"同族**（第十二次）。

### 9.3 而 `logs` 的三个量

```php
"ZMFX BO1 policy enabled seed=" + randomSeed +
" electricalWeapons=" + size + " shock=" + shock + " shockEyes=" + shockEyes
```

**⇒ 四个量。**

### 9.4 而 `randomSeed` 是**时间**

```cpp
zmDeathFx.randomSeed = (uint32)steady_clock::now().time_since_epoch().count();
```

**⇒ 所以每次启动不同。**

**⚠ 而 §284 的 `playerNames` 排序是**确定性**的要求 —— 这里却**故意非确定**。**

**⇒ 区别**：`playerNames` 进入 gamestate（需要确定性），而 `randomSeed` 只影响**本地**特效选择。**

**✓ 合理。**

## 十、`tag_origin` 的**占位符用法**

```cpp
const auto bone = boneIndex("tag_origin", "tag_origin");
if (bone && *bone != 255)
{
    arrivalModel = resolveModelConfigStringIndex("tag_origin").value_or(0);
    arrivalBone = *bone;
    arrivalEffects = { ... 三个特效 ... };
}
```

### 10.1 **`tag_origin` 既是模型名也是骨骼名**

**⇒ 与 §259 的"`tag_origin` 是'模型槽未替换'的指纹"**相关但不同**：**

```text
§259  世界模型是 `tag_origin` ⇒ 【拒绝】
§297  用一个 `tag_origin` 的**空模型**作特效的挂载点 ⇒ 【有意】
```

**⇒ 所以 `tag_origin` 有**两种用法**：一个是"未替换"的症状，一个是"无模型的挂载点"。**

**⚠ 这是一个**语义冲突** —— 同一个名字两种情况。**

## 十一、`SvFactoryTeleporterResources` 的**十一个字段**

```text
packModelOn      zombie_vending_packapunch_on
packGlow         misc/fx_zombie_cola_on_blue_glow
packHum          zmb_perks_packa_loop（【声音别名】）
packGlowBones[4] tag_on_glow_right1 / _left1 / _right / _left
model            tag_origin
bone             tag_origin
padStart         maps/zombie/fx_transporter_pad_start
beam             maps/zombie/fx_transporter_beam
linkSingle       maps/zombie/fx_zombie_mainframe_link_single
linkAll          maps/zombie/fx_zombie_mainframe_link_all
```

**⇒ 十一个（含四个骨骼）。**

### 11.1 而 `packHum` 用 `resolveSoundAliasEventParameter`（**单数**）

**⇒ 而 §288 用 `resolveSoundAliasEventParameters`（复数）。**

**⇒ 两个函数：单数包装复数**（§261 的 `resolveSoundAliasEventParameter` 就是那个包装）。

**✓ 所以这里用单数是正确的。**

## 十二、`boxResources` 的**九个字段**

```text
openAnimation      codo_treasure_chest_box_open
closeAnimation     codo_treasure_chest_box_close
animationTree      【从两个动画合成】
effectModel        tag_origin
effectBone         tag_origin
effects[2]         env/light/fx_ray_sun_sm_short / zombie/treasure_box2
bearModel          zombie_teddybear
ammoModel          zombie_ammocan
relocationEffect   misc/fx_zombie_couch_effect
```

**⇒ 九个。**

### 12.1 而 `resolveScriptModelAnimationTree(boxAnimations)` 是 §260 的 BST 查找

```cpp
const std::array<uint16,2> boxAnimations{ openAnimation, closeAnimation };
boxResources.animationTree = resolveScriptModelAnimationTree(boxAnimations).value_or(0);
```

**⇒ 用**两个别名**作为键 ⇒ 匹配唯一一个动画树。**

**⇒ 与 §260 的"最多 8 个 alias"一致** ✓

### 12.2 而"缺失资产只禁用 FX"

```php
// Original box carriers use resident tag_origin/root and two
// looping native definitions. Missing assets disable only FX.
```

**⇒ 三层**：

```text
1. 原版箱子载体用常驻的 `tag_origin`/root 与两个循环的原生定义
2. ⇒ 缺失的资产**只禁用 FX**
3. ⇒ 箱子本身仍然工作
```

**✓ 又一次"降级但不破坏"。**

## 十三、**神秘箱只从原生动态尾部选**

```php
// OLMOD(factory_box): offer only entries in the native dynamic
// tail which the gamestate already published before world setup.
// The old first-64 scan picked arbitrary low static WeaponDefs;
// those can be gameplay-valid while resolving only a tag_origin
// placeholder on the client. A modular record is the existing
// client assembly contract -- this path never materializes or
// broadcasts a new weapon for a box roll.
const auto firstDynamic = Bindings.firstDynamicWeaponAssetIndex();
const auto dynamicTail = firstDynamic ? Bindings.readDynamicWeaponConfigStrings(*firstDynamic) : std::nullopt;
```

### 13.1 五层

```text
1. **只提供原生动态尾部里、gamestate 在世界设置之前已经发布过**的条目
2. **旧的 first-64 扫描**挑了任意的低静态 WeaponDef
3. ⇒ 那些可以**游戏上有效**而在客户端只解析成一个 **`tag_origin` 占位符**
4. ⇒ 一个模块化记录是**现有的客户端组装契约**
5. ⇒ **这条路绝不为一次箱子抽取物化或广播一个新武器**
```

### 13.2 **"游戏上有效而客户端只解析成 `tag_origin` 占位符"**

**⇒ 与 §290 的"客户端显示 Barrett 而服务器执行一把刀"**完全同族** ✓

**⇒ 第三次"服务端有效而客户端错"。**

### 13.3 而"绝不为一次箱子抽取物化或广播一个新武器"

**⇒ 所以箱子只从**已发布**的里选。**

**✓ 与 §286 的"不广播"一致。**

## 十四、关键结论

1. **`255` 是"无骨骼"的哨兵**（`uint8` 满值，与 §261 的 `i < 255` 一致）。
2. **"只在每个已加载的伤害变体都同意时才复用骨骼索引"** —— 一致性即信任。
3. **"绝不当猜一个组合后的头索引"** —— 眼睛是 `count + local` 空间。
4. **`tag` lambda 三层验证**，与骨骼规则同构。
5. **"不用魔法 ID"** —— 86/97 不硬编码（第四次该原则）。
6. **只有 blue/yellow/orange 三色有眼睛发光**，红色因"特殊开关未解析"被排除。
7. **四组 refined 对**（A→E_down 850、B→B 600、D→B 550、E→A 350）。
8. **三个 `down` 跨字母** —— 因为它们是录制的观测而不是规律。
9. **"没有已验证的 C 循环对"** —— 第十一次"缺失即答案"。
10. **refined 对的失败是静默的**（无日志），与 §296 的"重复即拒绝且明说"不同。
11. **`refined` 是三层开关依赖**（必须 BO1 也开）。
12. **电气三 + 排除四**，且"只接受实际解析出来的名字"。
13. **`randomSeed` 故意非确定**，而 `playerNames` 需要确定 —— 区别在"是否进 gamestate"。
14. **`tag_origin` 有两种用法**（未替换的症状 vs 有意的无模型挂载点）—— 语义冲突。
15. **`packHum` 用单数 `resolveSoundAliasEventParameter`**（它包装复数）。
16. **箱子只从原生动态尾部选** —— 因为低静态 WeaponDef 会解析成 `tag_origin` 占位符。
17. **"绝不为一次箱子抽取物化或广播一个新武器"**。
18. **"缺失资产只禁用 FX"** —— 又一次降级但不破坏。

## 十五、未闭合点

- refined 对失败时的静默是否有意。
- `tag_origin` 的两种用法是否造成实际混淆。
- 箱子抽取的完整逻辑（待读）。
- `Appmain.cpp` 6100 行之后未读取。
