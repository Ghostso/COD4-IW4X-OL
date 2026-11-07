# 272 · **"命中不是伤害"：每颗子弹都报 `hitEntity=none`**、自伤探针的两个改动、九个注入点

## 一、范围

本报告学习 `Appmain.cpp` 380–600 行。

## 二、`PendingWorldAssetRequest` 与 `SpawnGroundTraceDistance`

```php
struct PendingWorldAssetRequest
{
    std::string mapName;
    std::string gameType;
    std::optional<std::vector<SvMapEntity>> mapEntities;
    std::string lastFailureStage;
    std::uint32_t lastAttemptMilliseconds{};
    bool attempted{};
};
constexpr float SpawnGroundTraceDistance = 8192.0f;
```

### 2.1 `8192.0f` 与记忆

**记忆里**："`StandardBulletRange = 8192.0f`" ✓

**⇒ 所以出生点地面 trace 用的是**与子弹相同的射程**。**

**⇒ 一个"从高空向下打到地面"的 trace** —— 8192 单位足够覆盖任何地图高度。

## 三、**九个客户端补丁的槽**

```php
std::optional<DedicatedProcessPatchResult> DedicatedProcessPatch;
std::optional<ClientProcessPatchResult>    ClientProcessPatch;
std::optional<ClientProcessPatchResult>    ClientLoopFxPatch;
std::optional<ClientProcessPatchResult>    ClientRecordValidatorPatch;   // CODOL_FORCE_RECORD_VALIDATOR=1
std::optional<ClientProcessPatchResult>    ClientEntityEventWeaponPatch;
std::optional<ClientProcessPatchResult>    ClientEntityEventRangePatch;
std::optional<ClientProcessPatchResult>    ClientAmmoLookupWeaponPatch;
std::optional<ClientProcessPatchResult>    ClientUiOperatorResolverPatch;
std::optional<ClientProcessPatchResult>    ClientWeaponInventoryPatch;
std::optional<UnsignedFastfilePatchResult> UnsignedFastfilePatch;
bool UnsignedFastfilePatchAttempted{};
bool ClientProcessPatchAttempted{};
```

### 3.1 十一个槽 + 两个 attempted 标志

```text
1  DedicatedProcessPatch
2  ClientProcessPatch
3  ClientLoopFxPatch
4  ClientRecordValidatorPatch     ← 探针（默认关）
5  ClientEntityEventWeaponPatch
6  ClientEntityEventRangePatch
7  ClientAmmoLookupWeaponPatch
8  ClientUiOperatorResolverPatch
9  ClientWeaponInventoryPatch
10 UnsignedFastfilePatch
11 （两个 attempted 标志）
```

### 3.2 **九个是 `ClientProcessPatchResult`**

**⇒ 所以 `ClientProcessPatches.cpp`（82 KB）里做了九处补丁。**

**⇒ 与记忆里"11 patch sites but 3 are not 5 bytes (6/10/6)"相关。**

### 3.3 而 `ClientRecordValidatorPatch` 是**探针**

```cpp
// ★★★ 2026-10-07 04:5x -- 候选记录校验器强制放行（探针；`CODOL_FORCE_RECORD_VALIDATOR=1` 才生效）
```

**⇒ 中文注释** —— 一个后来加入的诊断。

## 四、**"命中不是伤害"**（本组最重要的一段）

### 4.1 那段完整论证

```php
// OLMOD(section-94): A HIT IS NOT DAMAGE, and the reason is the pass filter.
//
// Section 73g item 4 has been open since a player could first be shot: sv_bullet_mp turns
// partGroup into a hit location and a multiplier, builds an SvPlayerDamagePayload, appends a
// player-damage world event and hands it to the gametype script -- and NOT ONE LINE of that
// has ever run, because every bullet this server fires reports hitEntity=none. It is not
// that the path is wrong. It is that SV_BulletTrace passes the SHOOTER, correctly, and with
// one client in the map the shooter is the only collision entity there is.
//
// Section 74 hit exactly this shape on the capsule path and section 73h's "this needs a
// second player and a person at the screen" was RETRACTED: the question was reachable, and
// every existing caller just excluded the answer. Same here.
```

### 4.2 六层

```text
1. `sv_bullet_mp` 把 partGroup 变成命中位置与倍率、构造 damage payload、追加世界事件、交给 gametype 脚本
2. 而【那些行一行都没跑过】
3. 因为本服务器发的每一颗子弹都报 `hitEntity=none`
4. 【不是】路径错
5. 而是 `SV_BulletTrace` 正确地传了【射击者】，而单人地图里射击者是唯一的碰撞实体
6. ⇒ 所以它自己把自己排除了
```

### 4.3 而 §73h 的**撤回**

```text
§73h 说"这需要第二个玩家和一个人坐在屏幕前" → 【已撤回】
因为问题可达，只是每一个现有调用者都排除了答案
```

**⇒ 这是一个"问题被误判为不可测"的自我更正。**

**⇒ 与记忆里"我上一轮说需要两个人"这类判断的撤回同族。**

### 4.4 而 §265 的"实体半边死了"是**另一个**层

```text
§265  服务端 clip 被删除 ⇒ 实体碰撞整体不可用
§272  射击者被 pass 过滤 ⇒ 即使碰撞可用也打不到自己
```

**⇒ 两个独立缺陷，同一个症状。**

## 五、**自伤探针只改两件事**

```php
// The probe changes TWO things and nothing else:
//   * passFiringEntity = false, so the shooter is a legal candidate
//   * the BASIS is replaced with a line that has already been measured to hit him --
//     section 73's locational probe segment 1, from origin - 64 on Y at z + 42, aimed +Y,
//     which reports fraction=0.437363 partGroup=5 on every cycle. Firing from the real
//     muzzle with no pass filter would start INSIDE his own capsule, which is section 74's
//     other lesson: aim a server-side probe at a line you have already measured clear.
```

### 5.1 两个改动

```text
① passFiringEntity = false        ⇒ 射击者成为合法候选
② basis 替换成【已经测量过能打中他】的那条线
```

### 5.2 而那条线的**四个数**

```text
muzzleTrace = origin + (0, -64, +42)
forward     = (0, 1, 0)
fraction    = 0.437363     ← 实测
partGroup   = 5            ← 实测
```

**⇒ 而"每一个周期都报 `fraction=0.437363 partGroup=5`"** —— 一个**极其稳定**的测量。

**⇒ 所以这是一条**已经完全确定的**射线。**

### 5.3 而"从真实枪口发射且不 pass 过滤会从**他自己的胶囊内部**开始"

```php
// Firing from the real muzzle with no pass filter would start INSIDE his own capsule,
// which is section 74's other lesson: aim a server-side probe at a line you have already
// measured clear.
```

### 5.4 三层

```text
1. 真实枪口 + 不过滤 ⇒ 起点在【自己胶囊内部】
2. ⇒ trace 立即 `startSolid` ⇒ 无有效结果
3. ⇒ 所以必须用一条【已经测量过起点是空的】的线
```

**⇒ "§74 的另一课：把服务端探针瞄向一条你已经测量过是空的行。"**

**⇒ 这是一个**方法学**原则** —— 探针的输入必须是已知的。

### 5.5 而"其余全是真实路径"

```php
// Bullet_Endpos, SV_BulletTrace, the damage curve, the hit-location multiplier, the payload
// build, the event append and the script dispatch are all the real path, untouched.
```

**⇒ 六项未改动**：

```text
Bullet_Endpos
SV_BulletTrace
damage curve
hit-location multiplier
payload build
event append
script dispatch
```

**⇒ 所以探针**只改输入，不改被测对象**。**

**⇒ 这是一个正确的实验设计** ✓

## 六、`executeServerBulletFire` 的**十一项输入**

```php
SvFireWeaponResult executeServerBulletFire(
    uint32 serverTime,
    SvGlassState &glassState,
    SvGlassDamageState &glassDamageState,
    const SvGlassMapMetadata &glassMetadata,
    span<const SvCollisionEntity> collisionEntities,
    span<const SvDamageablePlayerView> damageablePlayers,
    SvPlayerState &playerState,
    SvGameEntity &entity,
    const SvResolvedWeapon &weapon,
    const SvWeaponFireBasis &basis,
    const SvWeaponSpreadResult &spread,
    const SvFireWeaponEvent &event)
```

### 6.1 **四个 const 引用 + 两个 span + 五个引用/值**

```text
const 引用    glassMetadata, weapon, basis, spread, event
可变引用      glassState, glassDamageState, playerState, entity
span         collisionEntities, damageablePlayers
值            serverTime
```

**⇒ 八项 + 两个 span + 一个值 = 十一项。**

### 6.2 而 `entity` 与 `playerState` **都是可变**

**⇒ 因为开火会改它们的待定 payload。**

**⇒ 与 `entity.pendingPlayerDamagePayloads` / `entity.pendingEntityDamagePayloads` 一致。**

## 七、`SV_BuildBulletFirePlan` 的**十个字段**

```php
const auto plan = SV_BuildBulletFirePlan({
    .commandTime = playerState.commandTime,
    .hand = event.hand,
    .weaponType = weapon.weaponType,
    .weaponClass = weapon.weaponClass,
    .penetrateType = weapon.penetrateType,
    .shotCount = weapon.shotCount,
    .damageCurve = weapon.damageCurve,
    .rifleBullet = weapon.rifleBullet != 0,
    .bulletExplosiveDamage = weapon.bulletExplosiveDamage != 0,
});
if (!plan) return SvFireWeaponResult::Failed;
```

### 7.1 **九项**

### 7.2 而全部来自 `weapon` + `event.hand` + `playerState.commandTime`

**⇒ 所以 plan 是**纯函数**于武器与事件。**

**✓ 无副作用。**

## 八、`SV_ExecuteBulletFire` 的**十五项 + 六个回调**

### 8.1 配置结构（十五项）

```php
{
    .commandTime, .plan, .basis, .spread, .damageCurve,
    .hitLocationMultipliers, .weaponAssetIndex, .firingEntityNum,
    .levelTime, .rifleBullet, .fmjPenetration, .passFiringEntity,
}
```

**⇒ 十二项。而 `basis = probeBasis`（可能是替换的）。**

**⇒ 而 `passFiringEntity = !selfDamageProbe`** ✓

### 8.2 六个回调

```text
① calculateBulletEndpos
② traceServerPoint（含穿透诊断）
③ 无穿透续接（返回 false 的 TODO 桩）
④ directionToByte
⑤ surfacePenetrationDepth
⑥ （加上 damageablePlayers / entity.damageableEntityViews 等参数）
```

### 8.3 **③ 是一个 TODO 桩**

```php
[](const SvBulletTraceInput &, const TraceResult &, std::uint32_t) -> std::optional<bool> {
    // TODO(CODOL): Replace the no-penetration continuation stub
    // after reverse trace, material depth loss and recursive
    // Bullet_Process ownership are recovered.
    return false;
}
```

**⇒ 三项未恢复**：

```text
reverse trace
material depth loss
recursive Bullet_Process ownership
```

**⇒ 所以**穿透的续接**未实现 ⇒ 返回 `false`。**

**⇒ 而 §253 的"FMJ 加倍材质深度"只在第一层生效。**

## 九、穿透诊断的**九个量**

```php
"bullet-penetration-trace mode=%s start=%.2f,%.2f,%.2f end=%.2f,%.2f,%.2f "
"result=%s hitType=%u hitId=%u fraction=%.4f startSolid=%d allSolid=%d surface=%u"
```

### 9.1 九项

```text
mode          entities / world / initial
start (x3)
end (x3)
result        ok / unavailable
hitType / hitId / fraction / startSolid / allSolid / surface
```

### 9.2 而 `surface = (surfaceFlags >> 20) & 0x1F`

**⇒ 5 位的表面类型** —— 与记忆里"bullet surface types = 31 (0..30)"一致 ✓

### 9.3 而 `mode` 的三个值来自 `entitiesOnly` / `worldOnly`

```php
request.entitiesOnly ? "entities" : request.worldOnly ? "world" : "initial"
```

**⇒ 与 §267 的四种 mode 的三种对应**（`CollisionOnly` 不在这条路径）。**

### 9.4 而 96 条上限

```php
static std::uint32_t reports{};
if (reports++ < 96)
```

**⇒ 与 §266 的 128、§268 的 12 不同。**

## 十、关键结论

1. **`SpawnGroundTraceDistance = 8192.0f`** 与 `StandardBulletRange` 同一个数。
2. **九个 `ClientProcessPatchResult`** + 一个 `DedicatedProcessPatchResult` + 一个 `UnsignedFastfilePatchResult`。
3. **`ClientRecordValidatorPatch` 是探针**（`CODOL_FORCE_RECORD_VALIDATOR=1`）。
4. **"命中不是伤害"的根因是 `passFiringEntity`**，而单人地图里射击者是唯一碰撞实体。
5. **§73h 的"需要第二个玩家"被撤回** —— 问题可达，只是调用者排除了答案。
6. **自伤探针只改两个输入**（`passFiringEntity` 与 `basis`），六项被测路径不动。
7. **那条线的四个实测值**：`origin+(0,-64,+42)`、`forward=(0,1,0)`、`fraction=0.437363`、`partGroup=5`。
8. **"真实枪口不过滤会从自己胶囊内部开始"** —— §74 的另一课。
9. **"探针输入必须是已知的"** —— 一个方法学原则。
10. **`SV_BuildBulletFirePlan` 是纯函数**（九项输入）。
11. **穿透续接是 TODO 桩（返回 `false`）** —— 三项未恢复。
12. **`surface = (surfaceFlags >> 20) & 0x1F`** 是 5 位表面类型。
13. **诊断上限各不相同**（96 / 128 / 12 / 16）。

## 十一、未闭合点

- `ClientProcessPatches.cpp` 的九处补丁具体位置。
- 穿透续接的三项未恢复的具体后果。
- `Appmain.cpp` 600 行之后未读取。
