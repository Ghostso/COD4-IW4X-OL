# 321 · **"用观测范围作界会拒绝第一个未观测到的值"**、`CG_Obituary` 的完整规范、`394/1419` 的实测

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1599–1800 行。

## 二、`validGeneralBrushModelEntity` 的**十项零约束**（续 §320）

```cpp
entity.eventParm == 0 && entity.otherEntityNum == 0 &&
entity.groundEntityNum == 0 &&
entity.impactSurfaceType == 0 && entity.impactFlags == 0 &&
entity.modelScale == 0.0f && entity.movementDir == 0 &&
entity.eventSequence == 0 && entity.weaponAssetIndex == 0 &&
entity.presentationWeaponAssetIndex == 0 &&
entity.offhandWeaponAssetIndex == 0 &&
entity.coKnifeStatsIndex == 0 && entity.unk00E0 == 0 &&
entity.legsAnim == 0 && entity.torsoAnim == 0 &&
entity.unk00A0 == 0 &&
entity.positionTrajectoryType == 0 && entity.positionTrajectoryTime == 0 &&
entity.positionTrajectoryDuration == 0 &&
entity.angleTrajectoryType == 0 && entity.angleTrajectoryTime == 0 &&
entity.angleTrajectoryDuration == 0 &&
all_of(entity.events, == SvEntityEvent{}) &&
all_of(entity.origin, isfinite) &&
all_of(entity.angles, isfinite) &&
all_of(entity.positionTrajectoryDelta, == 0.0f) &&
all_of(entity.angleTrajectoryDelta, == 0.0f);
```

### 2.1 六个轨迹字段全零

```text
positionTrajectoryType / Time / Duration   全 0
angleTrajectoryType / Time / Duration      全 0
positionTrajectoryDelta[3]                 全 0.0f
angleTrajectoryDelta[3]                    全 0.0f
```

**⇒ 所以 `ET_GENERAL` 的 brush model **没有轨迹**。**

**✓ 因为它是**静态几何**。**

### 2.2 而 `origin`/`angles` 只要求**有限**

**⇒ 所以它们**可以是任意值**（只要有限）。**

**✅ 与 §320 的 `ET_SCRIPTMOVER` 的"轨迹类型 1 或 13"**不同 —— 那是**动态的**。**

## 三、**`OLMOD_FLESH_IMPACT` 的 "清除方式是测量而不是论证"**（本组第二重要）

### 3.1 那段

```php
// ON BY DEFAULT NOW; OLMOD_FLESH_IMPACT=0 turns it off.
//
// It shipped opt-in because it REPLACES an event that already works, and
// the first live run put it next to T-posed deaths -- which is exactly
// the situation the opt-in existed for. It was then bisected on the SAME
// binary with the variable unset: the deaths still returned
// durationMs=-1, and the T-pose turned out to predate this branch by
// weeks (see the death-anim commit). Cleared by measurement, not by
// argument.
//
// WHAT IS CONFIRMED IS THE SOUND. 41 EV_BULLET_HIT_CLIENT_SMALL reached
// the wire in one match and the player heard the flesh impact; they
// reported no VISIBLE difference, so whether the case-86 block draws
// anything here is still open. The event is correct against the demo
// either way, and a wrong-looking impact is still better evidence than
// no impact.
bool fleshImpactEnabled()
{
    static const bool enabled = [] {
        const char *const value = std::getenv("OLMOD_FLESH_IMPACT");
        return !(value && value[0] == '0' && !value[1]);
    }();
    return enabled;
}
```

### 3.2 七层

```text
1. **现在默认开**
2. ⇒ 它以 opt-in 出货因为**它替换一个已经工作的事件**
3. ⇒ 而**第一次实机运行把它放在 T-pose 死亡旁边** —— 那正是 opt-in 存在的理由
4. ⇒ 然后**在同一个二进制上把变量取消设置做二分**：
     · **死亡仍然返回 `durationMs=-1`**
     · **而 T-pose 结果比这个分支【早了数周】**（见 death-anim 提交）
5. ⇒ **用测量清除，而不是用论证**
6. ⇒ **确认的是声音**：41 个 `EV_BULLET_HIT_CLIENT_SMALL` 在一场比赛里到线上而玩家听到了肉质撞击
7. ⇒ **他们报告没有可见差异** ⇒ 所以 case-86 块在这里是否画出任何东西**仍然是开放的**
8. ⇒ **事件对 demo 无论如何是对的**，而**一个看起来错的撞击仍然是比没有撞击更好的证据**
```

### 3.3 **"用测量清除，而不是用论证"**

**✅ 这是本文件里**最重要的一句方法论**之一。**

**⇒ 与 §311 的"一个不匹配的计数是窗口在告诉我它被污染了"同族**（第十七次）。**

### 3.4 而"**T-pose 比这个分支早了数周**"

**⇒ 三层**：

```text
1. 第一次运行看到 T-pose 就在新分支旁边
2. ⇒ 所以怀疑新分支
3. ⇒ 而**二分证明 T-pose 早了数周**
```

**✅ 一个**完美的"时间先后的排除"**。**

### 3.5 而"**一个看起来错的撞击仍然是比没有撞击更好的证据**"

**✅ 与 §288 的"发一个错误的声音比没有更糟"**相反**！**

**⚠ 两处**相反**的判断：**

```text
§288  声音    错误的比没有更糟 ⇒ 留空
§321  撞击    看起来错的比没有好 ⇒ 发
```

**⇒ 区别**：

```text
声音    玩家会听到错的（负面体验）
撞击    玩家会看到一个标记（至少知道打中了）
```

**✓ 语义不同。**

## 四、**`impactFlags` 的"用观测范围作界会拒绝第一个未观测值"**（本组最重要的一段）

### 4.1 那段

```php
// `impactFlags == 0` WOULD REFUSE REAL TRAFFIC. Measured on the
// retail dm demo: of 1419 EV_BULLET_HIT field assertions, 394
// carry this field NON-ZERO, 1..3. The field is 8 bits wide in
// OLfinal's ET_EVENTS table, so the bound is the WIRE WIDTH --
// a bound taken from an observed range refuses the first value
// the observation happened not to contain.
entity.impactFlags <= 0xFF && entity.weaponAssetIndex > 0 &&
```

### 4.2 五层

```text
1. **`impactFlags == 0` 会拒绝真实流量**
2. ⇒ 在零售 dm demo 上测量：**1419 个 `EV_BULLET_HIT` 字段断言里，394 个携带这个字段【非零】，值 1..3**
3. ⇒ **这个字段在 OLfinal 的 `ET_EVENTS` 表里是 8 位宽**
4. ⇒ 所以**界是【线的宽度】**
5. ⇒ **一个从观测范围取的界会拒绝观测恰好未包含的第一个值**
```

### 4.3 **这是本文件里最重要的方法论原则**

**"一个从观测范围取的界会拒绝观测恰好未包含的第一个值。"**

**✅ 与 §319 的"界是测量的宽度不是值域"**完全一致** ✓**

**⇒ **第三次该原则**：**

```text
§319  validActorEntity 的"界是测量的宽度"
§320  validScriptMoverEntity 的"界是测量的宽度"
§321  validBulletImpactEntity 的"界是线的宽度"
```

### 4.4 而三个数字

```text
1419   EV_BULLET_HIT 字段断言总数
394    其中 impactFlags 非零
1..3   非零的取值范围
0xFF   8 位宽度
```

**⇒ 所以 `394 / 1419 = 27.8%` 非零。**

## 五、**两种撞击实体的不同要求**（本组第三重要）

### 5.1 那段

```php
// THE FLESH HIT CARRIES ONE FIELD THE WORLD HIT MUST NOT, AND THE
// WORLD HIT CARRIES THREE THE FLESH HIT MUST NOT. Both are pinned
// to what the retail demo asserts rather than to what the wire
// could hold: EV_BULLET_HIT_CLIENT_SMALL sends origin, the shooter,
// the weapon, the constant 7 in field 6 and the surface 6 in field
// 15 -- and asserts NO eventParm (its parameter width is 0 in
// EntityEventParameterBits), NO impactFlags and NO hit entity, in
// 294 of 294 assertions.
// EV_MELEE_HIT asserts eventParm 1 and nothing else the bullet
// forms carry -- 36 of 36 in the demo.
const auto meleeHit = entity.eType == EntityTypeMeleeHit;
if (meleeHit &&
    (entity.eventParm != MeleeHitEventParameter ||
        entity.impactSurfaceType != 0 || entity.impactFlags != 0 ||
        entity.groundEntityNum != 0 || entity.unk00A0 != 0))
{
    return false;
}
const auto fleshHit = entity.eType == EntityTypeBulletHitClient;
if (fleshHit &&
    (entity.eventParm != 0 || entity.impactFlags != 0 ||
        entity.groundEntityNum != 0 ||
        entity.unk00A0 != ClientBulletImpactSurface ||
        entity.impactSurfaceType != ClientBulletImpactSurfaceType))
{
    return false;
}
```

### 5.2 两种实体的对照

```text
ET_MELEE_HIT                （36/36）
  eventParm == MeleeHitEventParameter  （1）
  impactSurfaceType == 0
  impactFlags == 0
  groundEntityNum == 0
  unk00A0 == 0

ET_BULLET_HIT_CLIENT_SMALL  （294/294）
  eventParm == 0
  impactFlags == 0
  groundEntityNum == 0
  unk00A0 == ClientBulletImpactSurface      （6）
  impactSurfaceType == ClientBulletImpactSurfaceType
```

### 5.3 而`fleshHit` 的**五个精确值**

```text
eventParm == 0
impactFlags == 0
groundEntityNum == 0
unk00A0 == ClientBulletImpactSurface
impactSurfaceType == ClientBulletImpactSurfaceType
```

**⇒ 三层**：

```text
1. `unk00A0` 与 `impactSurfaceType` 都设成**那个表面值**
2. ⇒ 因为 §319 说"字段 15（`es+0x00A0`）骑在 `unk00A0` 里"
3. ⇒ **两个字段承载同一个值**
```

**✅ 与 §319 的"骑在 `unk00A0` 里"**完全一致** ✓**

### 5.4 而 `MELEE_HIT` 在 demo 里 **36/36**

**⇒ 与 §274 的"零售一局发 `EV_MELEE_HIT` **36 次**"**完全一致** ✓**

**✅ 跨报告闭环 —— §274 说 36 次而我们一次没发，§321 说 demo 里 36/36 断言。**

## 六、`eType` 的**三种白名单**

```php
return (entity.eType == EntityTypeBulletHit || fleshHit || meleeHit) &&
    entity.number >= FirstDynamicServerEntityNum &&
    entity.clientNum == 0 && entity.eFlags == 0 &&
    entity.otherEntityNum <= EntityNumNone &&
    entity.groundEntityNum <= EntityNumNone &&
    entity.impactSurfaceType < BulletSurfaceTypeCount &&
    entity.impactFlags <= 0xFF && entity.weaponAssetIndex > 0 &&
    entity.weaponAssetIndex <= MaxCurrentWeaponAssetIndex &&
    entity.presentationWeaponAssetIndex == 0 &&
    entity.offhandWeaponAssetIndex == 0 &&
    entity.coKnifeStatsIndex == 0 && entity.unk00E0 == 0 &&
    entity.modelIndex == 0 && entity.modelScale == 0.0f &&
    entity.movementDir == 0 && entity.solid == 0 &&
    entity.eventSequence == 0 && entity.legsAnim == 0 &&
    entity.torsoAnim == 0 &&
    (fleshHit || entity.unk00A0 == 0) &&
    entity.positionTrajectoryType == 0 && ...
```

### 6.1 而 `impactSurfaceType < BulletSurfaceTypeCount`

**⇒ 与记忆里"bullet surface types = 31 (0..30)"**完全一致** ✓**

### 6.2 而 `weaponAssetIndex > 0` 是**必须**

**⇒ 所以一个撞击**必须**有一个武器。**

**✓ 因为撞击需要材质/穿透计算。**

## 七、`validSimpleEventEntity` 的**五种 eType**

```php
if (entity.eType != EntityTypeSoundAlias &&
    entity.eType != EntityTypeSoundAliasAsMaster &&
    entity.eType != EntityTypePlayFx &&
    entity.eType != EntityTypeEventBase + 117 &&
    entity.eType != EntityTypeExploder)
{
    return false;
}
const auto event = (size_t)(entity.eType - EntityTypeEventBase);
const auto parameterBits = EntityEventParameterBits[event];
const auto validParameter = parameterBits == 32 ||
    entity.eventParm < (std::uint32_t{1} << parameterBits);
```

### 7.1 五种

```text
EntityTypeSoundAlias
EntityTypeSoundAliasAsMaster
EntityTypePlayFx
EntityTypeEventBase + 117
EntityTypeExploder
```

**⇒ 五种。**

### 7.2 而 `parameterBits == 32` 的**特殊情况**

```cpp
const auto validParameter = parameterBits == 32 ||
    entity.eventParm < (std::uint32_t{1} << parameterBits);
```

**⇒ 三层**：

```text
1. `parameterBits == 32` ⇒ **无需检查**（因为 32 位无上界）
2. ⇒ 否则 `eventParm < (1 << bits)`
3. ⇒ 而 `bits == 0` ⇒ `eventParm < 1` ⇒ **必须为 0**
```

**✅ 与 §317 的"`EntityEventParameterBits` 有多个 0"配合 —— 那些事件没有参数。**

### 7.3 ⚠ **`EntityTypeEventBase + 117` 是一个硬编码的偏移**

**⇒ 三层**：

```text
1. 用 `EntityTypeEventBase + 117` 而不是一个具名常量
2. ⇒ 一个**魔法数字**
3. ⇒ 而其它四个都是具名的
```

**⚠ 一处不一致。**

## 八、**`CG_Obituary` 的完整规范**（本组第四重要）

### 8.1 那段

```php
// CG_Obituary, out.exe 0x00531080, is the whole specification:
//
//   v5  = *(es + 132)   field 9  / +0x84   VICTIM
//         if (v5 > 0x12) Com_Error -- so the victim is a REAL client
//   v39 = *(es + 136)   field 13 / +0x88   ATTACKER
//         if (v39 > 0x12) v39 = 2046, no name, colour '7'
//   cx  = eventParm     field 5  / +0xB0, 12 bits
//         (cx & 0xFFF) >= 1700 -> means-of-death icon for
//         (cx - 1700); otherwise the weapon's own kill icon.
//
// The victim bound is the client's OWN Com_Error, not a guess, and
```

### 8.2 八层

```text
1. **`CG_Obituary`，out.exe `0x00531080`，是【整个规范】**
2. `v5 = *(es + 132)` → **字段 9 / `+0x84`** → **VICTIM**
3. ⇒ **`if (v5 > 0x12) Com_Error`** ⇒ 所以**受害者是一个真的客户端**
4. `v39 = *(es + 136)` → **字段 13 / `+0x88`** → **ATTACKER**
5. ⇒ **`if (v39 > 0x12) v39 = 2046`，无名字，颜色 `'7'`**
6. `cx = eventParm` → **字段 5 / `+0xB0`，12 位**
7. ⇒ **`(cx & 0xFFF) >= 1700` ⇒ `(cx - 1700)` 的死因图标**
8. ⇒ **否则用武器自己的击杀图标**
```

### 8.3 而**四个具体数字**

```text
0x12 = 18          客户端编号上界
2046               「无攻击者」的哨兵
0xFFF = 4095       参数掩码（12 位）
1700               死因图标的基址
```

**✅ 与记忆里"`obituary (1700 + MOD)`"**完全一致** ✓**

**⇒ 而"`(cx & 0xFFF) >= 1700` ⇒ `cx - 1700`"是**那个公式的实现**。**

### 8.4 而 `2046` 与 `0x7FF (2047)`

**⚠ `2046` 而不是 `2047`。**

**⇒ 而 §264/§318 的 `2047` 是 `ENTITYNUM_NONE`。**

**⇒ 所以 `2046` 是**另一个哨兵**（`ENTITYNUM_NONE - 1`）。**

**⚠ 一处需要核对的差一。**

### 8.5 而"**受害者的界是客户端自己的 `Com_Error`，不是猜的**"

**✅ 与 §321 的"界是线的宽度"**不同** —— 这里界来自**客户端自己的代码**。**

**⇒ 更强的证据源。**

## 九、`validObituaryEventEntity` 的**位置**

**⇒ 在第 1786 行开始，本报告只读到 1800 行。**

**⇒ 后续待读。**

## 十、关键结论

1. **`ET_GENERAL` 的 brush model 六个轨迹字段全零** —— 静态几何。
2. **`OLMOD_FLESH_IMPACT` 默认开** —— "用测量清除而不是用论证"。
3. **"T-pose 比这个分支早了数周"** —— 二分排除的实例。
4. **"一个看起来错的撞击仍然是比没有撞击更好的证据"** —— 与 §288 **相反**（声音 vs 撞击语义不同）。
5. **⭐ "一个从观测范围取的界会拒绝观测恰好未包含的第一个值"** —— 本文件最重要的方法论原则。
6. **`1419` 个断言里 `394` 个 `impactFlags` 非零（`1..3`）而界是 `0xFF`（8 位）**。
7. **两种撞击实体的精确对照**（`ET_MELEE_HIT` 36/36 vs `ET_BULLET_HIT_CLIENT` 294/294）。
8. **`fleshHit` 的 `unk00A0` 与 `impactSurfaceType` 都设成表面值** —— 与 §319 的"骑在 `unk00A0` 里"一致。
9. **⚠ `ET_MELEE_HIT` 的 36/36 与 §274 的"零售一局 36 次"**完全一致 ✓
10. **`impactSurfaceType < BulletSurfaceTypeCount`（31）**。
11. **`validSimpleEventEntity` 五种 eType**，其中一个是**硬编码的 `EntityTypeEventBase + 117`**。
12. **`parameterBits == 32` ⇒ 无检查；`== 0` ⇒ 必须为 0**。
13. **`CG_Obituary 0x00531080` 是整个规范** —— 三个字段（victim 9 / attacker 13 / eventParm 5）。
14. **`0x12 = 18` 是客户端上界**，而 `if (v5 > 0x12) Com_Error` ⇒ **受害者必须是真客户端**。
15. **`2046` 是"无攻击者"的哨兵而不是 `2047`** —— 一处差一。
16. **`(cx & 0xFFF) >= 1700` ⇒ `cx - 1700` 的死因图标** —— `obituary (1700 + MOD)` 的实现。
17. **"受害者的界是客户端自己的 `Com_Error`"** —— 比"线的宽度"更强的证据源。

## 十一、未闭合点

- `2046` vs `2047` 的哨兵差一。
- `EntityTypeEventBase + 117` 的语义。
- `validObituaryEventEntity` 的完整实现（待读）。
- `sv_snapshot_mp.cpp` 1800 行之后未读取。
