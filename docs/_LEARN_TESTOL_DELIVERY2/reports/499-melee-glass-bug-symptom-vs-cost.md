# 499 · **"那个**报告的症状【是【玻璃【不碎**】；那个**实际的代价【是【整个 usercmd【被拒绝**，把那个玩家的移动【一起带走**"** —— `sv_melee_mp.cpp` 的 `glassPieceCount = 0`、近战复用子弹的追踪、以及"刀刃【到【脚【也【杀死**"

## 一、范围

本报告学习 `sv_melee_mp.cpp`（**`225` 行**）全文件：`SV_MeleeTraceEnd`、`SV_ExecuteMeleeAttack` 的七段（准入 / 追踪 / 玻璃 / 分组 / 玩家 / 实体 / 载荷）、以及那个 `glassPieceCount = 0` 的完整病历。

## 二、**"那个报告的症状是玻璃不碎；那个实际的代价是整个 usercmd 被拒绝"**（本组最重要的一段）

### 2.1 那段

```cpp
// NOT ZERO, AND THAT WAS THE GLASS BUG. SV_BulletTrace treats
// this as the bound a glass hitId must fall inside, and rejects
// the whole trace when it does not:
//
//     if (!hitId || hitId > input.glassPieceCount)
//         return std::nullopt;
//
// With the count left at 0 that condition is true for EVERY
// glass pane -- hitId is one-based -- so a swing at a window
// produced no trace at all, became SvMeleeAttackResult::Failed,
// and SV_HandleClientEventsDetailed turned that into
// SvClientEventResult::Failed. The reported symptom is that the
// glass does not break; the actual cost was that the whole
// usercmd was rejected (ClientEventsRejected), taking the
// player's movement for that command with it. Bullets were
// unaffected because SV_ExecuteBulletFire has always passed the
// real pane count.
```

### 2.2 二十四层

```text
1. **`SV_BulletTrace` 【把那个 `glassPieceCount` 【当成【一个 `hitId` 必须【落在【里面的**界**】
2. ⇒ **⇒ 而【当【它【不**时【拒绝【整个**追踪**
3. ⇒ **⇒ 而【那个 `hitId` 【是**1 基**的**
4. ⇒ **⇒ 所以【当【那个计数【被【留【在 `0` 时【那个条件【对【每一块**玻璃【都【为真**
5. ⇒ **⇒ 所以【一次【对着【一个**窗【的挥击【没有【产生【任何追踪**
6. ⇒ **⇒ 而【它【变成 `SvMeleeAttackResult::Failed`**
7. ⇒ **⇒ 而 `SV_HandleClientEventsDetailed` 【把那个【变成 `SvClientEventResult::Failed`**
8. ⇒ **⇒ ⚠ 而【那个**报告的症状【是【那个玻璃【不碎**
9. ⇒ **⇒ 而【那个**实际的代价【是【整个 `usercmd` 【被**拒绝**
10. ⇒ **⇒ 而【那【把【那个玩家的**移动【一起带走**
11. ⇒ **⇒ 而【子弹【不【受影响**】⇒ **⇒ 因为 `SV_ExecuteBulletFire` 【一直【传【那个**真实的**窗格数**
```

### 2.3 ⭐⭐⭐ **"那个报告的症状是玻璃不碎；那个实际的代价是整个 usercmd 被拒绝"**

**✅ 这是本报告里**最重要的一条"**症状【与【代价【的**分离**"**。**

**✅ 与 §474 的"一个被拒绝的事件拒绝整个 usercmd，所以那个暂存的伤害与那一帧的移动都被丢弃"**——**完全同族** ✓

**⇒ 三层**：
```text
症状 ⇒ **玻璃【不碎**】（**一个**局部的**观感**）
代价 ⇒ **整个 usercmd【被拒**】（**⇒ 移动【一起**丢**）
⇒ **⇒ 所以【那个**症状【掩盖【那个代价**】
```

**✅ ⭐⭐⭐ **"那个症状掩盖那个代价"** —— 一个**极精确的诊断纪律**。

**⚠ 而"`hitId` 是 1 基的"**】**。**

**⇒ 十层**：
```text
`hitId` ∈ `[1, glassPieceCount]` ⇒ **⇒ 所以【`0` 【是【那个"没有**"的值**】
⇒ **⇒ 而【那个检查 `!hitId || hitId > count` ⇒ 【把 `0` 与【超界【一起**拒绝**
```

**✅ ⭐⭐⭐ **"那个检查把 0 与超界一起拒绝"** —— 一个**极精确的读法**。

**✅ 与 §471 的 `SV_BulletTrace` 的 `result.glassPieceIndex = result.trace.hitId - 1`**——**完全闭合** ✓

**⇒ 三层**：
```text
§471  **`result.glassPieceIndex = result.trace.hitId - 1`**（**⇒ 所以 `hitId` 【是**1 基**的**）
§499  **"hitId is one-based"**
⇒ **⇒ 一个**跨报告的验证**
```

**✅ ⭐⭐⭐ **"一个跨报告的验证"**。

**⚠ 而"子弹不受影响，因为 `SV_ExecuteBulletFire` 一直传那个真实的窗格数"**】**。**

**⇒ 十层**：
```text
§471  **`.glassPieceCount = static_cast<std::uint32_t>(glassMetadata.initialPieces.size())`**
§499  **而【近战【曾【传 `0`**】
⇒ **⇒ 所以【一个**复制【时的省略**
```

**✅ ⭐⭐⭐ **"一个复制时的省略"**。

**✅ 而与 §485 的"那个 `SV_PlayerSnapshotView` 的三层"**——**不同**，但与 §474 的"`SV_LookupAltWeapon` 递了 HOST"**同族**（**第四次"一个**调用点【的**参数【错**"**）。

## 三、**"近战用那个攻击者【正持有的**武器**，因为 CODOL 【用【那个装备的武器【近战【而【不是【换【到一个**刀资产**"**（本组第二重要）

### 3.1 那段

```cpp
// CODDIFF(weapon_melee): the weapon here is whatever the attacker is
// holding, because CODOL melees with the equipped weapon rather than
// swapping to a knife asset. The payload validator
// (SV_IsEntityDamagePayloadValid) refuses weaponAssetIndex 0, and the
// entityState this is dispatched from carries knife=0 on this build, so
// taking the knife index instead of the held one would produce a
// payload that is silently rejected -- which is exactly the shape of
// the bug being fixed.
```

### 3.2 二十四层

```text
1. **那个武器【是【那个攻击者【正持有的**】
2. ⇒ **⇒ 因为 CODOL 【用【那个**装备的**武器【近战**】⇒ **⇒ 而不是【换【到一个**刀资产**
3. ⇒ **⇒ 而那个载荷校验器 `SV_IsEntityDamagePayloadValid` 【拒绝 `weaponAssetIndex == 0`**】
4. ⇒ **⇒ 而【那个 `entityState` 【携带 `knife = 0` 在这个 build 上**】
5. ⇒ **⇒ 所以【取【那个刀的索引【而不【是【那个持有的【会【产生【一个【被**静默拒绝**的载荷**
6. ⇒ **⇒ 而那【正是【那个**正在被修的 bug【的形状**
```

### 3.3 ⭐⭐⭐ **"取那个刀的索引会产生一个被静默拒绝的载荷 —— 那正是正在被修的 bug 的形状"**

**✅ 与 §483 的"`SV_LookupAltWeapon` 递了 HOST ⇒ 每一次都返回 false"**——**完全同族** ✓

**⇒ 三层**：
```text
§483  **一个**参数语义反【⇒ 那个循环【一次也没跑**
§499  **`knife = 0` ⇒ 那个载荷【被**静默拒绝**
⇒ **⇒ 两次"一个**静默的**拒绝"**
```

**✅ ⭐⭐⭐ **"一个静默的拒绝"两例**。

**✅ 而"那个 `knife = 0`"**⇒ **一个**关于【这个 build 的**测量**。**

**⇒ 十层**：
```text
`knife = 0` ⇒ **⇒ 所以【那个 `entityState` 的刀索引【在【这个 build 上【是**未使用**的**
⇒ **⇒ 而【一个**3.3.3.3 的**移植会【假设【它有值**
```

**✅ ⭐⭐⭐ **"那个刀索引在这个 build 上是未使用的"**。

**✅ 与 §476 的"`ES` 的 `UnknownA0`"**——**同族**（**第五次"一个**未使用的**字段**"**）。

**⚠ 而"CODOL 用那个装备的武器近战"**】**。**

**⇒ 三层**：
```text
CODOL ⇒ **装备的武器**
而【一个【传统的 CoD】⇒ **换【到一个**刀**
⇒ **⇒ 所以【那个区别【是【一个**CODOL 专属的**行为**
```

**✅ ⭐⭐⭐ **"那个区别是一个 CODOL 专属的行为"**。

## 四、**"刀刃到脚也杀死"**（本组第三重要）

### 4.1 那段

```cpp
// CODDIFF(weapon_melee): no hit-location multiplier. BO1's
// Weapon_Melee_internal damages with the weapon's melee number and
// never scales it by the part group -- a knife to the foot kills -- so
// the multiplier is 1.0 and partGroup is carried only so the obituary
// and hit feedback name the right location.
```

### 4.2 二十四层

```text
1. **没有**命中位置乘数**】
2. ⇒ **⇒ BO1 的 `Weapon_Melee_internal` 【用【那个武器的**近战数**】
3. ⇒ **⇒ 而【从不【按那个 part group**缩放**
4. ⇒ **⇒ 所以【一个**刀刃【到【脚【也【杀死**
5. ⇒ **⇒ 所以【那个乘数【是 `1.0`**】
6. ⇒ **⇒ 而【那个 part group 【被【携带【只为【那个**讣告【与【命中反馈【命名【正确的**位置**
```

### 4.3 ⭐⭐⭐ **"一个刀刃到脚也杀死"**

**✅ 与 §488 的"`BarrettTuning` 的 `hitLocationMultipliers`"**——**相反**（那里**有一个 21 项的乘数表**）但**同族**（**第六次"一个**乘数【的**有无**"**）。

**⇒ 三层**：
```text
子弹 ⇒ **一个 `hitLocationMultipliers[21]`**（**⇒ `partGroup` 【选【一个**）
近战 ⇒ **`1.0`**（**⇒ 而 `partGroup` 【只【为【那个**讣告**
⇒ **⇒ 所以【两个**不同的**伤害模型**
```

**✅ ⭐⭐⭐ **"两个不同的伤害模型"** —— 而**"刀刃到脚也杀死"**是一个**极具体的**后果**。

**✅ 而"`partGroup` 只为那个讣告与命中反馈命名"**⇒ **一个**纯表现**的字段**。**

**⇒ 十层**：
```text
`hitLocation = static_cast<std::uint8_t>(trace->trace.partGroup)`
⇒ **⇒ 而【那个 `hitLocationMultiplier = 1.0f`**】
⇒ **⇒ 所以【那个 partGroup 【不【影响【伤害**】
```

**✅ ⭐⭐⭐ **"那个 partGroup 不影响伤害"** —— 与 §477 的"`hitLocationMultiplier` 是一个纯表现的字段"**同族**。

## 五、**`BulletShieldPartGroup` 的"落在防暴盾的部件组上就不伤害"**

### 5.1 那段

```cpp
// CODREF(weapon_melee): BO1 returns without damaging when the swing
// lands on the riot shield's part group.
if (trace->trace.partGroup == BulletShieldPartGroup)
    return SvMeleeAttackResult::Missed;
```

### 5.2 二十四层

```text
1. **`partGroup == BulletShieldPartGroup`（`19`）⇒ `Missed`**】
2. ⇒ **⇒ 而 §471 的 `SV_BulletTrace` 【在【那个 `partGroup == 19` 时【设 `surfaceFlags = BulletShieldSurfaceFlags`**】
3. ⇒ **⇒ 所以【两个**不同的**消费者【对【同一个 `partGroup` 【做【不同的事**】
```

### 5.3 ⭐⭐⭐ **"两个不同的消费者对同一个 partGroup 做不同的事"**

**✅ 与 §471 的 `SV_BulletTrace` 的 `if (result.trace.partGroup == BulletShieldPartGroup) result.trace.surfaceFlags = BulletShieldSurfaceFlags;`**——**完全闭合** ✓

**⇒ 三层**：
```text
`SV_BulletTrace` ⇒ **设【一个**表面标志**】
`SV_ExecuteMeleeAttack` ⇒ **返回** `Missed`**
⇒ **⇒ 所以【同一个 `partGroup 19` 【在【两层【各自【一个**后果**
```

**✅ ⭐⭐⭐ **"同一个 partGroup 19 在两层各自一个后果"**。

**✅ 与 §476 的"`BulletShieldPartGroup = 19` 与 `BulletShieldSurfaceFlags = 0x01D00000` 来自一次读"**——**完全同族**。

## 六、`SvMeleeAttackResult` 的四个值

### 6.1 四个（从代码推）

```text
Failed    ⇒ 追踪失败 / 载荷无效 / 未准入
Glass     ⇒ 打碎玻璃
Missed    ⇒ 没命中 / 忽略 / 盾牌
Applied   ⇒ 造成伤害
```

### 6.2 二十四层

```text
1. **四个，而【只有 `Applied` 【是【一个**成功**
2. ⇒ **⇒ 而【`Glass` 【是【一个**第二个**成功**】（**而【它【不【产生【玩家伤害**）
3. ⇒ **⇒ 而【`Missed` 【是【一个**正常的**非事件**】
4. ⇒ **⇒ 而【`Failed` 【是【一个**错误**
```

### 6.3 ⭐⭐⭐ **"四个结果，两个成功、一个正常、一个错误"**

**✅ 与 §474 的 `SvFireWeaponResult` 的 `Applied`/`DeferredImpact`/`Failed`**——**同族** ✓

**⇒ 三层**：
```text
§474  **`SvFireWeaponResult`：`Applied` / `DeferredImpact` / `Failed`**（**三**）
§499  **`SvMeleeAttackResult`：`Applied` / `Glass` / `Missed` / `Failed`**（**四**）
⇒ **⇒ 而【§499 【的【那个 `Missed` 【是【一个**新的**类别**】（**"正常**的**非事件**"）
```

**✅ ⭐⭐⭐ **"§499 的 Missed 是一个新的类别"** —— 一个**极重要的**区分**（**一个**miss 【不是【一个**错误**）**。**

**✅ 而"那个调用者（§474）【说**："**A miss is the common case and commits nothing. Only a genuine execution fault rejects the candidate.**"**）**。**

**⇒ 三层**：
```text
§474  **"A miss is the common case and commits nothing"**
§499  **`Missed` 【是一个**独立的**返回值**】
⇒ **⇒ 所以【那个**miss【不【毁掉**那个命令**
```

**✅ ⭐⭐⭐ **"那个 miss 不毁掉那个命令"** —— 与 §499 二 的"`Failed` 毁掉整个 usercmd"**一个精确的对照**。

## 七、那个"没有实体的重载"

### 7.1 那段

```cpp
SvMeleeAttackResult SV_ExecuteMeleeAttack(
    const SvMeleeAttackInput &input, ...,
    std::span<const SvDamageablePlayerView> damageablePlayers,
    std::vector<SvPlayerDamagePayload> &playerDamagePayloads,
    SvGlassDamageState &glassDamageState, SvGlassState &glassState)
{
    std::vector<SvEntityDamagePayload> entityDamagePayloads;
    return SV_ExecuteMeleeAttack(input, ..., {}, playerDamagePayloads, entityDamagePayloads, ...);
}
```

### 7.2 二十四层

```text
1. **一个**简化**的重载**】⇒ **⇒ 它【传【一个**空的** `damageableEntities`**
2. ⇒ **⇒ 所以【那个实体分支【永远【走【不到**
3. ⇒ **⇒ 而【那个 `entityDamagePayloads` 【是一个**局部的**
```

### 7.3 ⭐⭐⭐ **"一个简化重载传一个空的实体列表"**

**✅ 与 §471 的 `SV_ExecuteBulletFire` 的"那个 `damageableEntities` 的兼容重载"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **`OLMOD(bullet-execution-compatibility): source-only convenience entry for callers that intentionally have no registered non-player damage targets`**
§499  **同一个模式**
⇒ **⇒ 两次【同一个**便捷重载**】
```

**✅ ⭐⭐⭐ **"同一个便捷重载"两例**。

**⚠ 而那个**局部的 `entityDamagePayloads` 【被【丢弃**】**。**

**⇒ 十层**：
```text
`std::vector<SvEntityDamagePayload> entityDamagePayloads;`（**局部**）
⇒ **⇒ 而【它【被【传给【那个主函数**】⇒ **⇒ 而【它【在【那个主函数里【被 **`push_back`**
⇒ **⇒ 而【在【重载返回后【它【被**销毁**
```

**✅ ⭐⭐⭐ **"它在重载返回后被销毁，所以实体伤害被静默丢弃"** —— 一个**可报告的疑点**（**但【那个重载【的语义【就是【"没有实体目标"**）**。**

**⚠ 标注**：如果那个重载**被【一个【有实体目标的**调用者【使用**，那个实体伤害**会【静默【丢失** —— 但那**不是**这个重载的**预期用途**（**它【是【为【"intentionally have no registered non-player damage targets" 的调用者**）**。**

## 八、关键结论

1. **⭐⭐⭐ "那个报告的症状是玻璃不碎；那个实际的代价是**整个 usercmd 被拒绝**，把那个玩家的移动一起带走"** ⇒ **"那个症状掩盖那个代价"** —— 与 §474 的"一个被拒绝的事件拒绝整个 usercmd"**完全同族**；而根因是 **`glassPieceCount` 被留 `0`** ⇒ 而 **`hitId` 是 1 基的** ⇒ **`!hitId || hitId > 0` 对每一块玻璃都为真** ⇒ **独立验证：与 §471 的 `glassPieceIndex = hitId - 1` 一致**；而**"子弹不受影响，因为 `SV_ExecuteBulletFire` 一直传那个真实的窗格数"** ⇒ **"一个复制时的省略"**（与 §483 的"`SV_LookupAltWeapon` 递了 HOST"同族）。
2. **⭐⭐⭐ "近战用那个攻击者正持有的武器，因为 CODOL 用那个装备的武器近战而不是换到一个刀资产"** ⇒ **"那个 `entityState` 在这个 build 上携带 `knife = 0`"** ⇒ **"取那个刀的索引会产生一个被静默拒绝的载荷 —— 那正是正在被修的 bug 的形状"**（与 §483 的"一个静默的拒绝"同族）；而 **"那个刀索引在这个 build 上是未使用的"**（与 §476 的 `UnknownA0` 同族）。
3. **⭐⭐⭐ "没有命中位置乘数：BO1 的 `Weapon_Melee_internal` 用那个武器的近战数而从不按那个 part group 缩放 —— **一个刀刃到脚也杀死** —— 所以那个乘数是 `1.0` 而 `partGroup` 只被携带为那个讣告与命中反馈命名正确的位置"** ⇒ **"那个 partGroup 不影响伤害"**（与 §477 的"`hitLocationMultiplier` 是一个纯表现的字段"同族）。
4. **⭐⭐⭐ `BulletShieldPartGroup`（`19`）⇒ `Missed`** ⇒ **"两个不同的消费者对同一个 partGroup 做不同的事"**（`SV_BulletTrace` 设一个表面标志，而这里返回 `Missed`）—— 与 §471/§476 **完全闭合**。
5. **⭐⭐⭐ `SvMeleeAttackResult` 的四值**（`Failed`/`Glass`/`Missed`/`Applied`）⇒ **"四个结果，两个成功、一个正常、一个错误"** —— 而 **`Missed` 是一个新的类别**（**"一个 miss 不是个错误"**，与 §474 的 `SvFireWeaponResult` 的三值对照）；而**"那个 miss 不毁掉那个命令"** 与 §499 二 的"`Failed` 毁掉整个 usercmd" **一个精确的对照**。
6. **⭐⭐ `SV_MeleeTraceEnd` 的 `muzzleTrace + forward × SvMeleeRange`** ⇒ 一个**简单的**前向推进**；而那个 `forwardLengthSquared <= 0 ⇒ Failed` **⇒ 一个**退化**的守卫**。
7. **⭐⭐ 那个"没有实体的重载"传一个空的 `damageableEntities` 而丢弃那个局部的 `entityDamagePayloads`** —— 与 §471 的"兼容重载"同族；**⚠ 但若一个有实体目标的调用者用它，那个实体伤害会静默丢失**（标注，但那不是它的预期用途）。

## 九、`sv_melee_mp.cpp` 全文件总览

**`225` 行。**

**`2` 个函数**：`SV_MeleeTraceEnd` / `SV_ExecuteMeleeAttack`（两个重载）。

**`7` 段**：准入（4 条）/ 追踪（`SV_BulletTrace` 复用）/ 玻璃（`SV_ApplyBulletGlassDamage`）/ 分组（`partGroup >= HitLocationCount` ⇒ `Failed`；`== BulletShieldPartGroup` ⇒ `Missed`）/ 玩家 / 实体 / 载荷。

**`4` 个结果**：`Applied` / `Glass` / `Missed` / `Failed`。

**`3` 个反汇编锚点**：BO1 `Melee_Trace 0x82489730` / BO1 `Weapon_Melee_internal` / `SV_BulletTrace`（本 build）。

**`1` 个测量**：`entityState` 的 `knife = 0` 在这个 build 上。

## 十、未闭合点

- `SvMeleeRange` 的值。
- `SvMethodOfDeathMelee` 的值。
- 那个便捷重载的实际调用点。
- 下一个文件：`sv_weapon_movement_mp.cpp/.hpp`（`6,906` / `9,150`）。
