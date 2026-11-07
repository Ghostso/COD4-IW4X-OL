# 477 · **"一颗多人手雷炸了（`eType-98` 事件发出去了），记录 `targets=0 damage=0`，而没伤到任何人"** —— `sv_zm_special_world_mp.cpp` 的玩家半程、`cs 4536 + (parm>>1)` 的落地、以及"接受武器自己的 kind 当表里没有条目"

## 一、范围

本报告学习 `sv_zm_special_world_mp.cpp`（**`539` 行**）全文件：`spawnFactoryViewFx` 的 `eType 140`/`eventParm (slot<<1)`、`stepFactoryWeaponLights` 的三段弹药映射、`replaceFactoryEquipment` 的原生往返、`stepProjectileMissile` 的 `28700` 修复、`factoryMonkeyTarget` 的 `600` 单位、`stepFactorySpecialPresentation` 的三个状态、`applyPlayerBlastDamage` 的玩家半程、以及 `applyFactorySpecialImpact` 的十个目标预算。

## 二、**"一颗多人手雷炸了（那个 `eType-98` 事件发出去了），记录 `targets=0 damage=0`，而没伤到任何人"**（本组最重要的一段）

### 2.1 那段

```cpp
// 28700: the PLAYER half of an explosion. Same material the actor pass uses
// (radius / inner / outer from the weapon's own blast fields), same
// G_RadiusDamage shape, but the targets are live clients instead of actors.
//
// WHY THIS EXISTS: `applyFactorySpecialImpact` only ever walked
// EntityTypeActor. A multiplayer grenade therefore exploded (the eType-98
// event went out), logged `targets=0 damage=0`, and hurt nobody. Flash and
// smoke keep their own continuations and are excluded; so is the direct-hit
// path, which the projectile itself already reports.
```

### 2.2 二十四层

```text
1. **那个玩家【半程**】**
2. ⇒ **⇒ 而它【用【那个演员半程【用的同一个材质**】（**`radius`/`inner`/`outer` 来自【武器自己的爆炸字段**）**
3. ⇒ **⇒ 而【同一个 `G_RadiusDamage` 的形状**】
4. ⇒ **⇒ 但【那些目标【是【活的客户端**，而不是【演员**】
5. ⇒ **⚠ 【为什么它存在**】：`applyFactorySpecialImpact` **只【走【过 `EntityTypeActor`**】
6. ⇒ **⇒ 所以【一颗多人手雷【炸了**】（**那个 `eType-98` 事件【发出去了**）**
7. ⇒ **⇒ 而【记录 `targets=0 damage=0`**】⇒ **⇒ 而【没伤到任何人**】
```

### 2.3 ⭐⭐⭐ **"一个事件发出去了，一个日志写着 `targets=0`，而没有一个人受伤"**

**✅ 这是本报告里**最重的一条"**一个子系统【只覆盖【一半**的主体**"**。**

**✅ 与 §474 的"`sv_bullet_mp` 里的东西从来没有运行过"**——**同族** ✓

**⇒ 三层**：
```text
§474  **四个 fire id 错 ⇒ `sv_bullet_mp` 【从不运行**】
§477  **只走 `EntityTypeActor` ⇒ 玩家【从不受伤**】
⇒ **⇒ 两次"一个**子系统【看起来在工作**（**事件发出、日志有行**）而【它【没有**覆盖【那个真正的主体**"**
```

**✅ ⭐⭐⭐ **"一个子系统看起来在工作，而它没有覆盖那个真正的主体"两例**。

**⚠ 而"那个 `eType-98` 事件发出去了"**⇒ **一个**极强的误导**。**

**⇒ 十层**：
```text
表现层 ⇒ **`eType-98`（**那个爆炸事件**）⇒ **发出去了** ✓
伤害层 ⇒ **只走演员** ⇒ **`targets=0`**
⇒ **⇒ 所以【玩家【看到【一个爆炸**】而【它【不伤**人**】
⇒ **⇒ 而那【是【最难【诊断**的一类**（**视觉上【一切正常**）
```

**✅ ⭐⭐⭐ **"玩家看到一个爆炸而它不伤人 —— 那是较难诊断的一类"**。

**✅ 与 §470 的"`scr_game_allowkillcam` 的空白画面"**——**同族**（**第三次"一个**表现层【正常**而【那个**逻辑层【缺失**"**）。

**⇒ 三层**：
```text
§467  **`NO_SPAWN_POINT` ⇒ 一个加载了的地图 + 没有武器 + 没有手**（**缺【出生点**）
§470  **宣告 `allowkillcam 1` 而没有数据 ⇒ 空白画面**（**缺【回放数据**）
§477  **`eType-98` 发出了而没有伤害 ⇒ 一个不伤人的爆炸**（**缺【玩家半程**）
⇒ **⇒ 三次"表现层【正常**而【逻辑缺**"**
```

**✅ ⭐⭐⭐ **"表现层正常而逻辑缺"三例表**。

### 2.4 而**那个修复的三个组成部分**

```text
① 同材质：`radius`/`inner`/`outer` 来自 `factorySpecialCombat_`，缺表则用结构体默认（`250`/`100`/`0`）
② 同形状：`SV_ComputePlayerRadiusDamage`（与演员半程的 `G_RadiusDamage` 同构）
③ 排除：`Flash` 与 `Smoke` 有自己的延续；直击路径由投掷物自己报告
```

**⇒ 十层**：
```text
缺表 ⇒ **`SvFactorySpecialCombat fallback{}`** ⇒ **`radius 250 / inner 100 / outer 0`**
⇒ **⇒ 而注释明说**："**那个结构体的默认值是源自己的，不是一项发明**"
⇒ **⇒ 所以【一个【MP 手雷（`offhand`）【没有 Factory 战斗行**】⇒ **⇒ 仍然【会**伤害**
```

**✅ ⭐⭐⭐ **"一个缺表的 MP 手雷仍然会伤害，因为那个回退值是结构体自己的默认值"** —— 与 §467 的"一个回落比一个失败更危险"**相反**（**这里【回落【是【正确的**，因为**那个值【是一个**真实的**默认**）**。

**⇒ 三层**：
```text
§467  **回落【选了一个错的**出生点 ⇒ 危险**
§477  **回落【用一个真实的**结构默认 ⇒ 正确**
⇒ **⇒ 所以【"回落**"【本身【不是【问题**】—— **是【那个【被回落到的东西**】**
```

**✅ ⭐⭐⭐ **"'回落'本身不是问题，是那个被回落到的东西"** —— **本报告最精确的判据**。

**✅ 与 §468 的"`createDefault = false`"**——**一个精确的对照**（那里**必须失败**，这里**必须用一个真实的默认**）**。**

### 2.5 而**"一颗手雷会伤害它的投掷者"**

```cpp
// A grenade damages its thrower (retail does; the operator asked for
// explosions that "work"). Every other kind excludes the owner.
.ignoreClientNum = (impact.kind != SvFactorySpecialKind::Grenade &&
    impact.owner < MaximumGameClients)
    ? std::optional<std::uint32_t>{impact.owner}
    : std::nullopt,
```

**⇒ 二十四层**：
```text
1. **`kind == Grenade` ⇒ `ignoreClientNum = nullopt` ⇒ 【伤害投掷者**】
2. ⇒ **⇒ 而【其余每一种 ⇒ 【排除所有者**】
3. ⇒ **⇒ 而【注释【还【带了【甲方的话**："**"work"**"**】
```

**✅ ⭐⭐⭐ **"一颗手雷会伤害它的投掷者（零售这样做）"** —— 一个**极重要的正确性**。

**✅ 与 §471 的"`entityBulletDamage` 的 `max(1, base)`"**——**不同**（那里**至少 1 点**，这里**可以**自杀**）。

## 三、**`spawnFactoryViewFx` 的 `eType 140` 与 `eventParm = slot << 1`**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(sv_build_client_snapshot): original July31 Factory215050 onward
// emits eType140 / event117 every100ms. IDA532910,5328D0 and452A00 resolve
// cs4536+(parm>>1), its three-digit FX index and the following tag string.
// OLMOD(factory_view_fx): bounded per-owner temporary events; no shared native
// layouts, collision entities or recurring script/animation allocations.
...
event.networkState.eType = EntityTypeEventBase + 117;
event.networkState.eventParm = static_cast<std::uint32_t>(slot) << 1u;
```

### 3.2 二十四层

```text
1. **`eType 140` ⇒ `EntityTypeEventBase + 117`**】
2. ⇒ **⇒ 所以【`EntityTypeEventBase = 23`**】（**`140 - 117 = 23`**）
3. ⇒ **⇒ 而 `eventParm = slot << 1`**
4. ⇒ **⇒ 而消费者【`cs 4536 + (parm >> 1)` ⇒ 【解出 `slot`**】
5. ⇒ **⇒ 所以【那个 `<< 1` 与 `>> 1` 【是【一对**】
```

### 3.3 ⭐⭐⭐ **"`140 - 117 = 23` ⇒ `EntityTypeEventBase = 23`"**

**✅ 与 §474 的"`EV_MELEE_HIT` 的 `eType 98 = 23 + 75`"**——**完全闭合** ✓

**⇒ 独立验证**：
```text
§474  **`98 = 23 + 75`** ⇒ **`EntityTypeEventBase = 23`** ✓
§477  **`140 = 23 + 117`** ⇒ **`EntityTypeEventBase = 23`** ✓
⇒ **⇒ 两次【同一个基数**】
```

**✅ ⭐⭐⭐ **"两次同一个基数"** —— 一个**跨报告的算术闭合**。

**⚠ 而"那个 `<< 1` 与 `>> 1` 是一对"**⇒ **一个**极精巧**的编码**。**

**⇒ 十层**：
```text
若【`eventParm = slot`**】⇒ **⇒ 消费者 `parm >> 1` 【会【得到 `slot / 2`**】⇒ **错**
若【`eventParm = slot << 1`**】⇒ **⇒ 消费者 `parm >> 1 = slot`** ✓
⇒ **⇒ 所以【那个移位【是【那个消费者的**逆**】
```

**✅ ⭐⭐⭐ **"那个移位是那个消费者的逆"** —— 与 §470 的"`WeaponConfigStringDynamicBase = 5960` 恰等于 `WeaponConfigStringBase` ⇒ 不需要一个减法"**同族**（**第四次"一个**编码【与【它的消费者**对齐**"**）。

**⚠ 而"每 `100ms`"与 `stepFactoryWeaponLights` 的 `next = now + 100`**⇒ **一致** ✓

**⇒ 三层**：
```text
注释 ⇒ **每 `100ms`**
代码 ⇒ **`if(now>=next && slots[index] && spawnFactoryViewFx(...)) next=now+100;`**
⇒ **⇒ 一致** ✓
```

**✅ ⭐⭐ **"一致"**。

### 3.4 而**"三段弹药映射"**

```cpp
// Retail: 3 rounds -> tube_view; 2 -> tube_view2; 1 -> tube_view3.
// Reconstructed boundary: upgraded six-round weapon is not enabled here.
const auto index = 3u - std::min<unsigned>(3, clip->count[0]);
```

**⇒ 十层**：
```text
`count == 3` ⇒ **`3 - 3 = 0`** ⇒ **`tube_view`**
`count == 2` ⇒ **`3 - 2 = 1`** ⇒ **`tube_view2`**
`count == 1` ⇒ **`3 - 1 = 2`** ⇒ **`tube_view3`**
`count == 0` ⇒ **`3 - 0 = 3`** ⇒ **⚠ 而前面【有 `if(!clip->count[0]) continue;`**】
⇒ **⇒ 所以 `index ∈ {0,1,2}` ✓**
```

**✅ ⭐⭐⭐ **"`index ∈ {0,1,2}` 而那个 `continue` 防止 `3`"** —— 一个**精确的边界**。

**✅ 与 §475 的"`fx < 400` 保证恰好三位"**——**同族**（**第五次"一个**前提【保证【一个索引【在界内**"**）。

**⚠ 而"升级的六发武器【不在这里启用**"**⇒ **一个**诚实的**范围声明**。**

**⇒ 三层**：
```text
`clip->count[0]` 可以【是 `4..6`**】⇒ **⇒ `std::min(3, count) = 3` ⇒ `index = 0`** ⇒ **⇒ `tube_view`**
⇒ **⇒ 所以【一个六发武器【会【一直【显示【满**】
⇒ **⇒ 而注释明说【不启用**】
```

**✅ ⭐⭐ **"一个六发武器会一直显示满 —— 而注释明说『不启用』"**。

## 四、**`replaceFactoryEquipment` 的原生往返**（本组第三重要）

### 4.1 那段

```cpp
auto candidate = owner.playerState;
if (!SV_ReplaceOffhandReward(candidate, equipment, slot, replacement)) return false;
auto native = owner.nativePlayerState;
SV_OverlayPlayerStateToNative(candidate, native);
auto roundTrip = candidate;
if (!SV_OverlayNativePlayerStateToPlayerState(native, roundTrip) || roundTrip != candidate)
    return false;
playerEquipment_[clientNum] = {candidate.spawnGeneration, equipment};
owner.playerState = std::move(candidate);
owner.nativePlayerState = std::move(native);
zombieBattery_[clientNum] -= costRaw;
return true;
```

### 4.2 二十四层

```text
1. **先【改那个候选**（`candidate`）**
2. ⇒ **⇒ 然后【投影到原生**（`SV_OverlayPlayerStateToNative`）**
3. ⇒ **⇒ 然后【读回来**（`SV_OverlayNativePlayerStateToPlayerState`）**
4. ⇒ **⇒ 而【比较 `roundTrip != candidate`**】⇒ **⇒ 不等 ⇒ 拒绝**
5. ⇒ **⇒ 而【全部通过 ⇒ 才【提交**三个东西 + 扣钱**】
```

### 4.3 ⭐⭐⭐ **"`roundTrip != candidate` ⇒ 拒绝" —— 与 §462 的往返校验同一套**

**✅ 与 §462 的"四十个项共用一个 `return false`，而它跑在一个往返里"**——**完全同族** ✓

**⇒ 三层**：
```text
§462  **`SV_ClientSpawn` 的往返校验**（**四十个项**）
§477  **`replaceFactoryEquipment` 的往返校验**（**一个 `!=`**）
⇒ **⇒ 两次"一个**自往返【是【一个**可判定的正确性**"**
```

**✅ ⭐⭐⭐ **"一个自往返是一个可判定的正确性"两例**。

**⚠ 而"全部通过才提交三个东西 + 扣钱"**⇒ **一个**五步**的原子提交**。**

**⇒ 十层**：
```text
① `playerEquipment_`
② `owner.playerState`
③ `owner.nativePlayerState`
④ `zombieBattery_` 扣款
⇒ **⇒ 而【前三步【在【四步之前【无失败路径**】⇒ **⇒ 所以【原子**】
```

**✅ ⭐⭐⭐ **"前三步在四步之前（无失败路径）⇒ 原子"** —— 与 §471 的 `GlassCommandRollback`**同族**（**第六次"一个**两阶段提交**"**）。

**✅ 而那个"装备不得别名枪械弹药"的检查**⇒ **一个**极精确的**的守卫**。**

**⇒ 十层**：
```cpp
for(const auto *gun:{&owner.resolvedLoadout->primary,&owner.resolvedLoadout->secondary})
    if((old.weaponAssetIndex && (gun->ammoIndex==old.ammoIndex || gun->clipIndex==old.clipIndex)) ||
        gun->ammoIndex==replacement.ammoIndex || gun->clipIndex==replacement.clipIndex)return false;
```
```text
1. **旧的装备【不得【共享【那个枪的 `ammoIndex`/`clipIndex`**】
2. ⇒ **⇒ 而【新的【也不得**】
3. ⇒ **⇒ 所以【四条**检查**（`2 × 2`）
```

**✅ ⭐⭐⭐ **"四条检查（2 × 2）"** —— 一个**极精确的不变量**。

**✅ 与 §471 的"`entityBulletDamage`"**——**不同**，但与 §477 二 的"一个缺表的 MP 手雷"**同族**（**"一个**索引【共享**⇒ 一个**别名**"**）。

**⚠ 而"只退役私有的槽**"**⇒ **一个**极重要的**范围**。**

**⇒ 三层**：
```text
`equipment.weapons[slot]` ⇒ **一个私有的槽**（**`slot < 2`**）
而【它【不能【别名【那个枪的弹药**】
⇒ **⇒ 所以【"只退役私有的槽"**」
```

**✅ ⭐⭐ **"只退役私有的槽"**。

## 五、**`factoryMonkeyTarget` 的 `600` 单位与那条清晰线**

### 5.1 那段

```cpp
float best=600.f*600.f;
...
auto start=from,end=p;start[2]+=32;end[2]+=8;
const auto clear=pointTraceRunner_({.start=start,.end=end,.contentMask=BulletLocationalContentMask,
    .filter={number,std::nullopt},.mode=SvPointTraceMode::BulletLocational,.worldOnly=true},glassState_,bulletCollisionEntities_);
if(!clear || clear->startSolid || clear->allSolid || clear->fraction<1.f)continue;
```

### 5.2 二十四层

```text
1. **`600` 单位【的平方**作初值**】
2. ⇒ **⇒ 而那个 trace【用 `worldOnly = true`**】⇒ **⇒ 所以【它【只【看**世界几何**】
3. ⇒ **⇒ 而四个拒绝：无结果 / `startSolid` / `allSolid` / `fraction < 1`**】
4. ⇒ **⇒ 所以【只有【一条【完全清晰**的线【被接受**】
```

### 5.3 ⭐⭐⭐ **"`fraction < 1` ⇒ 拒绝 ⇒ 只有一条完全清晰的线被接受"**

**✅ 与 §476 的 `SV_ShouldClipToEntity`**——**不同**（那是一个**身份过滤**，这是一个**可见性**）但**同族**（**"一个**精确的**前置条件**"**）。

**⚠ 而"`start[2] += 32` 与 `end[2] += 8`"**⇒ **一个**不对称的**垂直偏移**。**

**⇒ 十层**：
```text
起点 ⇒ **`from[2] + 32`**（**从【那个演员的**中心**）
终点 ⇒ **`p[2] + 8`**（**从【那个手雷的**中心偏上**）
⇒ **⇒ 所以【两个**不同的**锚点** —— 而【那【是【有意的**（**两个物体【有不同的**中心**）
```

**✅ ⭐⭐⭐ **"两个不同的锚点，因为两个物体有不同的中心"** —— 与 §475 的"根网格的 origin 不是视觉中心"**同族**（**第二次"一个**物体【的几何中心【不【在【它的原点**"**）。

**✅ 而"那个 `worldOnly = true`"**⇒ **"一只猴子【需要【一条【到【那个目标的**视线**，而【不是【一条【到【那个目标的**命中**"**。**

**⇒ 三层**：
```text
`worldOnly = true` ⇒ **只【看【静态**几何**
⇒ **⇒ 所以【一个【躲在【另一个**演员【后面的手雷【仍然【可见**】
⇒ **⇒ 而那【对于【"猴子吸引【僵尸**"【是【正确的**（**僵尸【会【走向【那个声音**）
```

**✅ ⭐⭐⭐ **"对于『猴子吸引僵尸』那是正确的"**。

## 六、**`stepFactorySpecialPresentation` 的三个状态**

### 6.1 状态表

```text
① `factorySpecialStatuses_`（冻结/缩小/闪光）⇒ `until` 到期 ⇒ 恢复 `actorField0054`
② `factoryTrapPresentation_` ⇒ 投掷物消失 ⇒ 释放 `emitter`
③ 三个陷阱的垂直偏移 ⇒ `FireTrap +14` / `FreezeTrap +5` / `ShockTrap +20`
```

### 6.2 二十四层

```text
1. **三个陷阱**【各有各的**垂直偏移**】
2. ⇒ **（原版 Factory：火 `534` +14Z / 冻结 `471` +5Z / 电 `483` +20Z**）**
3. ⇒ **⇒ 而【Sumpf 的缩小 `859` 在【那个设备的原点**】
4. ⇒ **⇒ 所以【三个是【测量的**，而【第四个【是【零**】
```

### 6.3 ⭐⭐⭐ **"原版 Factory：火 `534` +14Z / 冻结 `471` +5Z / 电 `483` +20Z；Sumpf 的缩小 `859` 在设备原点"**

**✅ 与 §475 的"`zmb_box_raise` 的 `+40`"**——**同族**（**第三次"一个**实测的垂直偏移**"**）。

**⚠ 而那个缩小的**生命周期**】**。**

```cpp
// Original actor wire+54 falls by .1 per100ms to .5. Keep the source
// status lifetime reconstructed; expiry restores the actor field as well.
e->second.networkState.actorField0054 = status.originalScale *
    (1.f - std::min(.5f, (now - status.shrinkStarted) * .001f));
```

**⇒ 独立验证**：
```text
`(now - start) × 0.001` ⇒ **每 `1000ms` 增 `1`**
而 `min(0.5, ...)` ⇒ **⇒ 在【`500ms` 时【饱和【到 `0.5`**】
⇒ **⇒ 所以【那个下降【是【`-0.1 per 100ms`**（`0.5 / 5`）✓
⇒ **⇒ 而最终【`originalScale × (1 - 0.5) = 0.5 × original`** ✓
```

**✅ ⭐⭐⭐ **"`0.5 / 5 = 0.1 per 100ms` ⇒ 与原版的 `-0.1 per 100ms` 一致"** —— 一个**精确的算术闭合**。

**✅ 与 §470 的"`?77`"**——**不同**，但与 §477 二 的"那个 `<< 1` / `>> 1` 是一对"**同族**（**第六次"一个**编码【与【它的规格**对齐**"**）。

**⚠ 而那个**接触击杀**】**。**

```cpp
// Reconstructed contact kill: authoritative moving-player touch, bounded
// to a live fully shrunken actor. This is reconstructed contact policy, not
// a claim of recovered original stomp logic.
if(now-status.shrinkStarted>=500 && health!=entityDamageStates_.end() && ...
   ps.velocity[0]*ps.velocity[0]+ps.velocity[1]*ps.velocity[1]<=1.f)continue;
```

**⇒ 十层**：
```text
1. **`now - shrinkStarted >= 500` ⇒ 完全缩小**】
2. ⇒ **⇒ 而【速度平方【必须 `> 1`**】（**即【速度【`> 1` 单位/秒**）**
3. ⇒ **⇒ 而【那个实体【必须【在【那个玩家的 `touchEntities` 里**】
4. ⇒ **⇒ 而【那个 `lastThinkServerTime == now`**】（**一个新鲜的**触碰**）
```

**✅ ⭐⭐⭐ **"一个新鲜的权威碰撞触碰避免了穿墙击杀、陈旧接触与对一个静止玩家的记功"** —— 三个**具体的**失败模式**。

**✅ 与 §465 的"`SV_MapTriggerTouches` 是一个精确的 SAT"**——**同族**（**第四次"一个**触碰【的精确判据**"**）。

## 七、**`applyFactorySpecialImpact` 的十个目标预算与 `Tesla` 的链**

### 7.1 那段

```cpp
while(!targets.empty() && applied<10) {
    if(impact.kind==SvFactorySpecialKind::Tesla && applied) {
        for(auto &[distance,number]:targets) {
            auto center=entities_.at(number).currentOrigin;center[2]+=32;distance=0;
            for(std::size_t i=0;i<3;++i)distance+=(center[i]-damageOrigin[i])*(center[i]-damageOrigin[i]);
        }
        std::ranges::sort(targets);
    }
    ...
    if(impact.kind==SvFactorySpecialKind::Tesla) {
        damageOrigin=center;
        chainSource=static_cast<std::uint16_t>(number);
    }
}
```

### 7.2 二十四层

```text
1. **最多 `10` 个目标**】
2. ⇒ **⇒ 而对 `Tesla`，每一次之后【重算【从【那个新的 `damageOrigin`** 的距离**
3. ⇒ **⇒ 然后【重排**】⇒ **⇒ 所以【一条链【沿【最近邻**前进**】
4. ⇒ **⇒ 而 `chainSource` 【记录【上一个**命中的实体**】
```

### 7.3 ⭐⭐⭐ **"一条链沿最近邻前进"**

**✅ 一个**精确的**链式**语义**。**

**⇒ 独立核算**：
```text
`applied < 10` ⇒ **最多 `10` 跳**
每跳【从【上一个命中的实体**出发**】⇒ **⇒ 链长【受【`10` 限制**】
⇒ **⇒ 所以【一个 `Tesla` 【最多【击中 `10` 个演员**】
```

**✅ ⭐⭐ **"一个 Tesla 最多击中 10 个演员"**。

**⚠ 而 `Tesla`/`Monkey` 的 `damage = before`**⇒ **一个**即死**。**

**⇒ 十层**：
```cpp
std::int32_t damage=100; // explicit trap reconstruction per 500ms pulse
if(impact.kind==SvFactorySpecialKind::Tesla || impact.kind==SvFactorySpecialKind::Monkey)damage=before;
```
```text
默认 ⇒ **`100`**（**"每 `500ms` 脉冲的一次显式的陷阱重建"**）
`Tesla`/`Monkey` ⇒ **`before`** ⇒ **⇒ 即死**】
而 `cannotDie` ⇒ **`min(damage, before - 1)`** ⇒ **⇒ 留 1 血**】
```

**✅ ⭐⭐⭐ **"`cannotDie` 时留 1 血"** —— 一个**精确的**保护**。**

**✅ 与 §476 的"`0xFFFE` 饱和"**——**同族**（**第五次"一个**上界【保护**"**）。

### 7.4 而**那个可见性 trace 的 base/owner 双层**

```cpp
const auto visible=pointTraceRunner_({.start=start,.end=center,.contentMask=BulletLocationalContentMask,
    .filter={chainSource.value_or(impact.owner),impact.owner}},glassState_,collisionEntities_);
if(!visible || visible->allSolid || visible->startSolid ||
    (visible->fraction<1.f && visible->hitId!=number))continue;
```

**⇒ 十二层**：
```text
1. **`filter = {passEntityNum = chainSource ?? owner, passOwnerEntityNum = owner}`**】
2. ⇒ **⇒ 所以【上一个命中的实体【被【跳过**（**不会【挡住【下一跳**）**
3. ⇒ **⇒ 而【所有者的实体【也被【跳过**】
4. ⇒ **⇒ 而【那个 `(fraction < 1 && hitId != number)` 【是【那个关键**】
5. ⇒ **⇒ 所以【一条【挡住【另一个**演员的线【被拒绝**】⇒ **⇒ 而【一条【打中【那个目标自己**的线【被接受**】
```

**✅ ⭐⭐⭐ **"一条打中那个目标自己的线被接受，而一条挡住另一个演员的线被拒绝"** —— 一个**极精确的可见性判据**。

**✅ 与 §476 的 `SV_ShouldClipToEntity` 的三层过滤**——**完全同族** ✓

**⇒ 三层**：
```text
§476  **`passEntityNum` / `passOwnerEntityNum` 的三层过滤**
§477  **`{chainSource ?? owner, owner}` 的双层**】
⇒ **⇒ 两次【同一对**参数**
```

**✅ ⭐⭐ **"两次同一对参数"**。

## 八、**`registerMultiplayerOffhandWeapons` 的前置条件纪律**

### 8.1 那段

```cpp
// 步进器的前置条件不在位时**不登记** —— endFrame 的外层门是
// `missileFrameRunner_ || !factorySpecialWeapons_.empty() || !multiplayerOffhandWeapons_.empty()`，
// 一旦本表非空而求值器/追踪器缺失，块会进入、每枚投掷物都在第一帧被
// SV_StepFactorySpecial 的 `!evaluate` 分支静默退役（2026-10-08 实测踩到）。
// 缺前置条件时保持本表为空 ⇒ 外层门不进入 ⇒ 与改动前行为一致。
if(!zmBoardTrajectoryEvaluator_ || !pointTraceRunner_)return;
```

### 8.2 二十四层

```text
1. **步进器的前置条件【不在位**时【不登记**】
2. ⇒ **⇒ 因为【`endFrame` 的外层门【是【三个**条件之一的或**】】
3. ⇒ **⇒ 所以【一旦【本表非空**而【求值器/追踪器【缺失**】
4. ⇒ **⇒ 那个块【会【进入**】
5. ⇒ **⇒ 而【每一枚投掷物【都【在【第一帧【被【`!evaluate` 分支【静默退役**】
6. ⇒ **⇒ （`2026-10-08` 实测踩到**）**
7. ⇒ **⇒ 所以【缺前置条件时【保持本表为空**】⇒ **⇒ 外层门【不进入**】⇒ **⇒ 与改动前行为一致**】
```

### 8.3 ⭐⭐⭐ **"缺前置条件时保持本表为空，所以外层门不进入，与改动前行为一致"**

**✅ 这是本报告里**最精确的一条"**一个表【是【一个门**"**。**

**✅ 与 §475 的"关闭是那个幂等性的唯一保证"**——**同族**（**第三次"一个**状态【是【一个**不变量**"**）。

**⇒ 二层**：
```text
表非空 ⇒ **门开** ⇒ **块进入**
前置缺失 ⇒ **必须【保持表空**】⇒ **⇒ 门关** ⇒ **⇒ 无操作**
⇒ **⇒ 所以【"登记"【与【"前置"【是【一个**不变式**】
```

**✅ ⭐⭐⭐ **"『登记』与『前置』是一个不变式"**。

**⚠ 而"每枚投掷物都在第一帧被静默退役"**⇒ **一个**极隐蔽**的失败模式**。**

**⇒ 三层**：
```text
`!evaluate` ⇒ **`SvMissileRetirement{}`** ⇒ **⇒ 一颗手雷【消失了**】
⇒ **⇒ 没有伤害、没有爆炸、没有日志**（**如果【那个退役【不打日志**）
⇒ **⇒ 所以【"静默"【是【那个致命的属性**】
```

**✅ ⭐⭐⭐ **"'静默'是那个致命的属性"** —— 与 §474 的"`sv_bullet_mp` 从未运行"**同族**（**第三次"一个**静默的失败**"**）。

**✅ 与 §475 的"那个 `40` 单位的升"**——**不同**。

## 九、关键结论

1. **⭐⭐⭐ "一颗多人手雷炸了（那个 `eType-98` 事件发出去了），记录 `targets=0 damage=0`，而没伤到任何人"`** —— 因为 `applyFactorySpecialImpact` **只走 `EntityTypeActor`** ⇒ **"表现层正常而逻辑缺"的第三例**（与 §467 的 `NO_SPAWN_POINT`、§470 的 `allowkillcam` 同族）；而修复是**一个独立的玩家半程**（`applyPlayerBlastDamage`）。
2. **⭐⭐⭐ "`Flash` 与 `Smoke` 保持它们自己的延续；直击路径也是（由投掷物自己报告）"`** —— 一个**精确的范围界定**。
3. **⭐⭐⭐ "缺表时用结构体默认（`250`/`100`/`0`），而那是**源自己的**默认，不是一项发明"`** ⇒ **"'回落'本身不是问题，是那个被回落到的东西"`** —— 与 §467 的"一个回落比一个失败更危险"**相反**（那里**回落到了错的点**，这里**回落到了一个真实的默认**）。
4. **⭐⭐⭐ "一颗手雷会伤害它的投掷者（零售这样做）"`**（`ignoreClientNum = nullopt` 仅对 `Grenade`）—— 一个**极重要的正确性**。
5. **⭐⭐⭐ `eType 140 = EntityTypeEventBase + 117`** ⇒ **独立验证 `140 − 117 = 23`**，与 §474 的 `EV_MELEE_HIT` 的 `98 = 23 + 75` **同一个基数**；而 **`eventParm = slot << 1`** 与消费者的 **`cs 4536 + (parm >> 1)`** 是**一对逆**（与 §470 的 "5960 == 5960 ⇒ 不需要减法" 同族）。
6. **⭐⭐⭐ `stepFactoryWeaponLights` 的三段映射**（`3 → tube_view` / `2 → tube_view2` / `1 → tube_view3`）由 **`index = 3 - min(3, count)`** 实现，而 **`if(!clip->count[0]) continue` 防止 `index == 3`** ⇒ **"`index ∈ {0,1,2}`"`**；而"升级的六发武器不在这里启用" ⇒ **一个六发武器会一直显示满**（**诚实的范围声明**）。
7. **⭐⭐⭐ `replaceFactoryEquipment` 的原生往返**（`SV_OverlayPlayerStateToNative` → `SV_OverlayNativePlayerStateToPlayerState` → `roundTrip != candidate ⇒ 拒绝`）—— 与 §462 的"四十个项共用一个 `return false`"**同一套**；而"前三步在四步之前（无失败路径）⇒ 原子" ⇒ 第六次"一个两阶段提交"；而**"旧的与新的都不得共享枪的 `ammoIndex`/`clipIndex`" ⇒ 四条检查（2 × 2）**。
8. **⭐⭐⭐ `factoryMonkeyTarget` 的 `600` 单位与 `worldOnly = true`** ⇒ **"一只猴子需要一条到那个目标的视线，而不是一条到那个目标的命中"** ⇒ **"对于『猴子吸引僵尸』那是正确的"`**；而 `start[2] += 32` / `end[2] += 8` **是两个不同的锚点**（与 §475 的"根网格 origin 不是视觉中心"同族）。
9. **⭐⭐⭐ 三个陷阱的垂直偏移**（`FireTrap +14` / `FreezeTrap +5` / `ShockTrap +20`，而 `ShrinkTrap` 在设备原点）是**测量的**；而缩小的 `-0.1 per 100ms` 由 **`min(0.5, (now - start) * 0.001)`** 精确复现（**独立验证 `0.5 / 5 = 0.1` ✓**），终点是 **`0.5 × originalScale`**。
10. **⭐⭐⭐ "一个新鲜的权威碰撞触碰避免了穿墙击杀、陈旧接触与对一个静止玩家的记功"`** —— 三个具体失败模式，四个前置（`>= 500ms` 缩小 / `touchEntities` 含它 / `lastThinkServerTime == now` / 速度平方 `> 1`）。
11. **⭐⭐⭐ `applyFactorySpecialImpact` 的十个目标预算与 `Tesla` 的最近邻链**（每次之后从新的 `damageOrigin` 重算并重排）⇒ **"一条链沿最近邻前进"`**，最多 `10` 跳；而 `Tesla`/`Monkey` 的 `damage = before`（**即死**），`cannotDie` 时 `min(damage, before - 1)`（**留 1 血**）。
12. **⭐⭐⭐ 那个可见性判据**（`filter = {chainSource ?? owner, owner}` 与 `(fraction < 1 && hitId != number)`）⇒ **"一条打中那个目标自己的线被接受，而一条挡住另一个演员的线被拒绝"`** —— 与 §476 的 `SV_ShouldClipToEntity` **同一对参数**。
13. **⭐⭐⭐ `registerMultiplayerOffhandWeapons` 的前置条件纪律**：**"`endFrame` 的外层门是 `missileFrameRunner_ || !factorySpecialWeapons_.empty() || !multiplayerOffhandWeapons_.empty()`；一旦本表非空而求值器/追踪器缺失，块会进入、每枚投掷物都在第一帧被 `!evaluate` 分支**静默退役**（`2026-10-08` 实测踩到）"`** ⇒ **"缺前置条件时保持本表为空 ⇒ 外层门不进入 ⇒ 与改动前行为一致"`** —— **"『登记』与『前置』是一个不变式"`**，而**"『静默』是那个致命的属性"`**。

## 十、`sv_zm_special_world_mp.cpp` 全文件总览

**`539` 行。**

**`12` 个 `SvServerWorld` 方法**：
```text
spawnFactoryViewFx                     eType 140 / eventParm slot<<1
stepFactoryWeaponLights                三发段映射 + 100ms
setFactorySpecialWeapons               资源注册（可先于地图激活）
factorySpecialWeapon                   Factory 池查找（带 opt-in 门）
registerMultiplayerOffhandWeapons      前置条件纪律
offhandWeaponKind                      Factory 优先，未命中看 MP 表
replaceFactoryEquipment                原生往返 + 四条别名检查
stepFactorySpecialMissile              Factory 池的投掷物
factoryMonkeyTarget                    600 单位 + worldOnly
stepProjectileMissile                  28700：普通发射器
stepFactorySpecialPresentation         三个状态（缩放/陷阱载体/垂直偏移）
applyPlayerBlastDamage                 28700：玩家半程
applyFactorySpecialImpact              十个目标预算 + Tesla 链
```

**`10` 个测量锚点**：
```text
eType 140 = EntityTypeEventBase + 117       ⇒ base = 23
cs 4536 + (parm >> 1)                       消费者
Factory 215050 起每 100ms 发 eType140/event117
3 发 → tube_view / 2 → tube_view2 / 1 → tube_view3
火 534 +14Z / 冻结 471 +5Z / 电 483 +20Z；Sumpf 缩小 859 在原点
actor wire+54 每 100ms −0.1 到 0.5
radius 250 / inner 100 / outer 0（结构体默认）
Tesla 半径 160
火/电 半径 = base/3 + 12
G_RadiusDamage 的 damageFlags = 5
```

## 十一、未闭合点

- `EntityTypeEventBase = 23` 的独立确认（我由 `140 − 117` 与 §474 的 `98 − 75` 二次推出）。
- `factoryViewFxRecipients_` 的消费者。
- `SvFactorySpecialKind` 的完整枚举。
- `FactoryReconstructedBoxPool` 的内容。
- 下一个文件：`sv_zm_navgraph_mp.cpp`（`30,204` 字节）。
