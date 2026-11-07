# 394 · **"`botSpawnReported_` 是【按比赛】的，不是按进程的"** —— `124` 次 `SessionStart` 对 `47` 次 `spawn-applied`、一把**两把锁**（`mutex_` 与 `zmZonesMutex_`）

## 一、范围

本报告学习 `sv_main_mp.cpp` 1700–2050 行。

## 二、**`botSpawnReported_` 的完整事故**（本组最重要的一段）

### 2.1 那段

```php
// fix-G: the spawn report is per MATCH, not per process. Only setEnabled
// cleared this set, so every match after the first in one server lifetime
// logged no spawn-applied at all -- measured 2026-10-11: 124 SessionStart,
// 47 spawn-applied, strictly one YES per setEnabled cycle. The bots DID
// spawn (cmd-inject is gated on gameplayState == Playing), the log lied.
botSpawnReported_.clear();
```

### 2.2 十三层

```text
1. **`fix-G`：那个出生报告是【按比赛】的，不是按进程的**
2. ⇒ **只有 `setEnabled` 清过这个集合**
3. ⇒ **所以一个服务器生命期里第一场之后的【每一场】都完全没记 `spawn-applied`**
4. ⇒ **测量 2026-10-11**：
      · **`124` 次 `SessionStart`**
      · **`47` 次 `spawn-applied`**
      · **严格地每个 `setEnabled` 周期【一个 YES】**
5. ⇒ **那些 bot 【确实】出生了**
6. ⇒ **（`cmd-inject` 门控在 `gameplayState == Playing` 上）**
7. ⇒ **【日志在撒谎】**
```

### 2.3 ⭐⭐ **"日志在撒谎"**

**✅ 这是本文件里**最尖锐的一句自我批评**。**

**⇒ 三层**：

```text
真实：bot 出生了（cmd-inject 门控在 Playing 上 ⇒ 它必须是通过的）
日志：**只记了 47 次而实际 124 场**
⇒ **⇒ 而"没记"读起来像"没发生"**
```

**✅ 与 §372 的"从这个日志引用的每一个位置都是加载之前的"**同族（**第八次"日志误导"）。**

**⚠ 而"`124 SessionStart` vs `47 spawn-applied`"⇒ **一个 2.6 倍的缺口**。**

**✅ 与 §384 的 `73/163`、§362 的 `145`**第十四次大规模统计。

### 2.4 而**"严格地每个 `setEnabled` 周期一个 YES"**

**✅ 与 §372 的"一个服务端级的 `static` 在多客户端时退化"**同族（**第七次 static 作用域错误）。**

**⇒ 三层**：

```text
`botSpawnReported_` 只在 `setEnabled` 清
⇒ **所以它在多个比赛之间【累积】**
⇒ **而 `if (!inserted)` 的守卫 ⇒ 每个 bot 只记一次**
⇒ **⇒ 所以第一场比赛记满而之后【零】**
```

**✅ ⭐ **一个"按进程而不是按比赛"的经典作用域错误**。**

**⚠ 而注释**给出了精确的量化**（`124` vs `47`）⇒ **一个可验证的证据**。**

**✅ 与 §368 的"三层命名失败项"**同族。

### 2.5 而**"只清"**的两个函数

```text
setEnabled              ⇒ 清（进程级）
configureMatchRules     ⇒ 清（**比赛级，本报告的修复**）
```

**✅ 三层**：

```text
setEnabled       ⇒ 一个进程一次
configureMatchRules ⇒ **一场比赛一次**
⇒ **⇒ 所以放后者**
```

**✅ ⭐ **一个"作用域应该在哪里"的判断**。**

**⚠ 而 `configureMatchRules` 的清空清单有**三十七项**。**

**⇒ 与 §349 的 `reset()` 的六十八项、§392 的 `setEnabled` 的约九十项**形成**三层**。**

**✅ **三个清理范围**：

```text
setEnabled           ~90 项（进程）
configureMatchRules  ~37 项（比赛）
SvServerWorld::reset  68 项（世界/地图）
```

**✅ 一个**清晰的层次**。

## 三、**`configureGameState` 的完整清空（约 70 项）**（本组第二重要）

### 3.1 十二个 `gameState.*` 的本地拷贝

```cpp
const auto mapCenter = gameState.mapCenter;
const auto mapName = gameState.mapName;
const auto zombieMode = gameState.gameType == "zm";
const auto objectiveMaterials = gameState.sdObjectiveMaterials;
const auto factoryAmmoMaterials = gameState.factoryAmmoMaterials;
const auto factoryClockMaterials = gameState.factoryClockMaterials;
const auto zombieReviveMaterials = gameState.zombieReviveMaterials;
const auto zombieFallbackPistol = gameState.zombieFallbackPistol;
const auto damageFeedbackMaterial = gameState.damageFeedbackMaterial;
const auto killFeedbackMaterial = gameState.killFeedbackMaterial;
const auto damageFeedbackSound = gameState.damageFeedbackSound;
const auto killFeedbackSound = gameState.killFeedbackSound;
const auto scavengerBagWeaponAssetIndex = gameState.scavengerBagWeaponAssetIndex;
const auto scavengerPickupSound = gameState.scavengerPickupSound;
const auto splashSound = gameState.splashSound;
const auto uavEarnSound = gameState.uavEarnSound;
const auto uavUseSound = gameState.uavUseSound;
const auto leadTakenSound = gameState.leadTakenSound;
const auto leadLostSound = gameState.leadLostSound;
const auto winningFightSound = gameState.winningFightSound;
const auto soundAuditions = gameState.soundAuditions;
```

### 3.2 五层

```text
1. **二十一个 `gameState.*` 的本地拷贝**
2. ⇒ **因为下面 `std::move(gameState)`**
3. ⇒ **所以必须【先拷贝】再移动**
4. ⇒ **一个"移动前拷贝"的必然性**
5. ⇒ **而 `leadTakenSound` 等三个是 `optional`**（有 `if (x)` 守卫）
```

**✅ 与 §368 的"`candidateCommandState` 的 `effectiveCommand`"**同族（**第二次"移动前拷贝"）。**

**⚠ 而"`leadTakenSound_` 只在有值时设"⇒ **所以一个缺失的值保持旧值**。**

**⇒ 三层**：

```text
`if (leadTakenSound) leadTakenSound_ = *leadTakenSound;`
⇒ **所以若 `nullopt` ⇒ 【保留上场的值】**
⇒ **⚠ 一个跨地图的泄漏**
```

**⚠ 一处**潜在问题**（而 `headshotSound_.reset()` 显式清了）。**

**✅ 一个**不一致**。**

### 3.3 而 **`SV_PopulateRequiredConfigStrings(gameState)`**

```cpp
gameState.matchStartServerTime = 0;
SV_PopulateRequiredConfigStrings(gameState);
```

**⇒ 三层**：

```text
1. **先设 `matchStartServerTime = 0`**
2. ⇒ **然后填充必需的 configstring**
3. ⇒ **所以配置串【依赖那个 0】**
```

**✅ 与 §393 的"关卡开始时间在地图加载时固定"**完全闭合 ✓

**⇒ **第二次确认那个时间基。**

### 3.4 而**五个 OLMOD 环境变量在同一段**

```text
OLMOD_FACTORY_ENTRY              ⇒ factoryEntry（zm_factory_sh + zm + "1"）
OLMOD_ZM_RECONSTRUCTED_FEEDBACK  ⇒ zombieMode && "1"
OLMOD_FACTORY_INTERACTABLES      ⇒ zombieMode && zm_factory_sh && "1"
OLMOD_FACTORY_TELEPORTERS        ⇒ interactables && "1"
OLMOD_FACTORY_BO1_TELEPORT_TRAVEL ⇒ teleporters && "1"
```

**⇒ 五层，而**四个是链式的**：**

```text
interactables ⇒ teleporters ⇒ bo1Travel
⇒ **所以一个开关依赖前一个**
```

**✅ 与 §352 的"五个 OLMOD 全部要求特定地图+模式"**完全闭合 ✓

**⇒ **第二次确认那个模式。**

**⚠ 而"链式"⇒ **所以关掉 `INTERACTABLES` 就关掉后两个**。**

**✅ 一个**清晰的依赖链**。

### 3.5 而**`gameState.scriptMenus` 的三个**

```cpp
// CODDIFF(sv_send_client_gamestate): out.exe 610A30/6111E0 use
// NCS menu indexes. common_mp's 1/2/3 are changeclass/marines/opfor;
// the legacy three-slot parser table is different. This is the
// response-name lookup only; do not overwrite native menu assets.
gameState.scriptMenus[1] = "changeclass";
gameState.scriptMenus[2] = "changeclass_marines";
gameState.scriptMenus[3] = "changeclass_opfor";
```

**⇒ 六层**：

```text
1. **`out.exe 610A30/6111E0` 用 NCS 菜单索引**
2. ⇒ **`common_mp` 的 `1/2/3` 是 `changeclass`/`marines`/`opfor`**
3. ⇒ **而【遗留的三槽解析器表是【不同的】】**
4. ⇒ **这只是响应名查找**
5. ⇒ **【不要覆盖原生菜单资产】**
6. ⇒ **所以只设三个名字**
```

**✅ 与 §391 的"`changeclass_marines`"**完全闭合 ✓

**⇒ **第二次确认那个请求名。**

**⚠ 而"三槽表的索引是 1/2/3 而不是 0/1/2"⇒ **一个 1 基的索引**。**

**✅ 与 §346 的"`boardIndex` 是 1 基"**同族（**第二次"1 基"）。**

## 四、**`setZmZones` 的"从 `receiver_zone` 开始"**（本组第三重要）

### 4.1 那段

```php
// zmZonesMutex_, NOT mutex_. See the member declaration: the gametype script
// reads this while loadGameplayScript already holds mutex_.
// The player starts in receiver_zone on Factory. Every other zone is
// authored in the map but remains closed until the corresponding
// door/debris enter_* flag fires. Do not confuse geometric adjacency with
// progression: two volumes can touch while a closed door separates them.
for (auto &zone : zones)
    zone.active = zone.name == "receiver_zone";
if (!zones.empty() && std::ranges::none_of(zones, &SvZmZone::active))
{
    // Other zm maps retain a usable start until their own flag mappings are
    // measured. Factory never takes this fallback.
    zones.front().active = true;
}
```

### 4.2 十层

```text
1. **用 `zmZonesMutex_`，【不是】 `mutex_`**
2. ⇒ **因为 gametype 脚本在读它而 `loadGameplayScript` 【已经持有 `mutex_`】**
3. ⇒ **所以一个【两把锁】的设计**
4. ⇒ **玩家在 Factory 上从 `receiver_zone` 开始**
5. ⇒ **其它每个区域在地图里被创作但在对应的 door/debris 的 `enter_*` 标志之前【保持关闭】**
6. ⇒ **【不要】把几何相邻与进度混淆**
7. ⇒ **两个体积可以相触而【一扇关闭的门】把它们分开**
8. ⇒ **而若无区域被激活 ⇒ `zones.front()` 作回退**
9. ⇒ **其它 zm 地图保留一个可用的开始直到它们自己的标志映射被测量**
10. ⇒ **Factory 【从不】取这个回退**
```

### 4.3 ⭐⭐ **"两把锁"与"几何相邻不是进度"**

**✅ 这是本文件里**最重要的一个并发设计记录**。**

**⇒ 三层**：

```text
`mutex_`          ⇒ 主锁（帧、命令）
`zmZonesMutex_`   ⇒ **区域锁**
⇒ **因为 `loadGameplayScript` 持 `mutex_` 时脚本要读区域**
⇒ **⇒ 所以必须分开**
```

**✅ ⭐ **一个经典的"锁顺序问题"的解决**（**用两把锁避免重入死锁**）。**

**⚠ 而与记忆里的"一次`beginFrame` 的 `lock_guard`"**配合。**

**✅ 一个**精确的并发架构**。

### 4.4 而**"两个体积可以相触而一扇关闭的门把它们分开"**

**✅ 与 §354 的"一个屏障的 outside 与 inside 就是图里的节点"**同族（**第二次"几何 vs 拓扑"）。**

**⇒ 三层**：

```text
几何：两个体积【相触】
拓扑：**一扇门分开它们**
⇒ **⇒ 所以不能用几何相邻判定可达性**
```

**✅ ⭐ **一个极清晰的"几何 ≠ 拓扑"陈述**。**

**⚠ 而"`enter_*` 标志"⇒ **一个具体的门控命名约定**。**

**✅ 与 §356 的"`route.spawnBarrierPassed`"**配合。

## 五、**`activateZmZone` 的"返回是否变化"**

```cpp
const auto changed = !zone->active;
zone->active = true;
return changed;
```

**⇒ 四层**：

```text
1. **先记 `changed = !active`**
2. ⇒ **然后置 `active = true`**
3. ⇒ **返回【是否真的变了】**
4. ⇒ **所以调用方可以区分"新激活"与"已激活"**
```

**✅ 与 §365 的"成功后【才】设 `started`"**同族（**第五次"状态转换的可观察性"）。**

**⚠ 而"幂等"⇒ 重复调用返回 `false`。**

**✅ 一个**正确的幂等设计**。

## 六、`configureSdSoundPresentation` 的**十六项验证**

```cpp
const auto validTeam = [](const SvSdTeamSoundPresentation &team) {
    const std::array values{ searchDestroy, objectiveDestroy, objectiveDefend,
        bombTaken, bombLost, bombPlanted, bombDefused, lastAlive,
        roundWon, roundLost, matchWon, matchLost, draw, sideSwitch };
    return std::ranges::all_of(values, [](auto v) { return v <= LocalSoundEventParameterMaximum; });
};
if (matchGameType_ != "sd" || sdRoundStatus_.armed ||
    (!presentation.objectiveLost && !presentation.objectiveTaken &&
     presentation.tf == {} && presentation.sc == {}) ||
    presentation.objectiveLost > Max || presentation.objectiveTaken > Max ||
    !validTeam(presentation.tf) || !validTeam(presentation.sc))
    return false;
```

### 6.1 七层

```text
1. **每个队伍【十四个】声音**
2. ⇒ **两队 = 二十八个**
3. ⇒ **加两个全局**（`objectiveLost` / `objectiveTaken`）= **三十个**
4. ⇒ **而都在 `LocalSoundEventParameterMaximum` 内**
5. ⇒ **且必须【不是全空】**（三个都为空 ⇒ 拒绝）
6. ⇒ **且必须 `matchGameType_ == "sd"`**
7. ⇒ **且 `sdRoundStatus_` 未武装**
```

**✅ 与 §391 的"六种 `SvSdRoundEndReason`"**配合。**

**⚠ 而"十四个队伍声音"⇒ **一个完整的清单**。**

**✅ 与 §346 的"七十五项合取"**不同（这是**三十三项 + 四个前置**）。

## 七、`ServerCore` 的**十二条 setter 转发**

```text
setZmNavGraph / setZmActorWalkAnim / setZmActorTearAnim / setZmTearClips /
setZmBoardTrajectoryEvaluator / setZmPresentation / setZmDeathAnim /
setZmActorDeathAnim / setZmActorAttackAnim / setZmBarriers /
setFactoryArrivalFx / setZmActorAnim...
```

**⇒ 十二条。**

**✅ 与 §349 的"`SvServerWorld` 的十个注入点"**同族（**第二次"转发层"）。**

**⇒ 三层**：

```text
`ServerCore` 的 setter  ⇒ **持 `mutex_` 并转发**
`SvServerWorld`         ⇒ **真正实现**
⇒ **所以是两层**
```

**✅ 一个**清晰的层次**。

**⚠ 而每个都是 `const std::lock_guard lock(mutex_); world_.setXxx(...)` ⇒ **完全同构**。**

**✅ 与 §337 的"两个几乎相同的函数"**第七次。

### 7.1 而 **`zmBarrierCount()` 与 `zmZones()` 的 `const` 方法也持锁**

```cpp
std::size_t ServerCore::zmBarrierCount() const {
    const std::lock_guard lock(mutex_);
    return world_.zmBarrierCount();
}
std::vector<SvZmZone> ServerCore::zmZones() const {
    const std::lock_guard lock(zmZonesMutex_);
    ...
}
```

**⇒ 三层**：

```text
`zmBarrierCount` ⇒ **`mutex_`**
`zmZones`        ⇒ **`zmZonesMutex_`**
⇒ **所以两个 getter 用不同的锁**
```

**✅ **第二次确认两把锁的分工。**

## 八、`configureMatchRules` 的**"`dmz` 无武装"**

```php
// BATTLE ROYALE STARTS YOU WITH NOTHING. Set here rather than at the spawn
// because the world owns the spawn and has no gametype. OLMOD_DMZ_UNARMED=0
// puts the class loadout back for a session without a rebuild.
{
    const auto *const disabled = std::getenv("OLMOD_DMZ_UNARMED");
    const auto unarmed = gameType == "dmz" && !(disabled && disabled[0] == '0');
    world_.setUnarmedSpawns(unarmed);
    if (unarmed) {
        OlMod::RuntimeLog::write(..., "dmz spawns UNARMED -- loadout resolved and "
            "validated as usual, then not equipped; loot is the only way to arm");
    }
}
```

### 8.1 七层

```text
1. **大逃杀让你【什么都不带】开始**
2. ⇒ **在这里设而不是在出生处**
3. ⇒ **因为【世界拥有出生】而它【没有 gametype】**
4. ⇒ **`OLMOD_DMZ_UNARMED=0` 把一个职业装备放回来**
5. ⇒ **而不需要重编**
6. ⇒ **`unarmed = gameType == "dmz" && !(disabled 是 "0")`**
7. ⇒ **而日志说"装载解析并照常验证，然后【不装备】；战利品是唯一武装的途径"**
```

**✅ 与 §371 的"空手是一个保持状态"**完全闭合 ✓

**⇒ **第四次确认那个设计。**

**⚠ 而"世界拥有出生而它没有 gametype"⇒ **一个架构上的分层理由**。**

**✅ 与 §368 的"源/投影"**同族。

## 九、关键结论

1. **⭐⭐ "那个出生报告是【按比赛】的，不是按进程的"`** —— 只有 `setEnabled` 清过它，所以**第一场之后的每一场都完全没记 `spawn-applied`**。
2. **⭐ 精确量化：`124` 次 `SessionStart` vs `47` 次 `spawn-applied`，严格地每个 `setEnabled` 周期一个 YES`** —— **2.6 倍的缺口**。
3. **⭐⭐ "那些 bot 确实出生了（`cmd-inject` 门控在 `Playing` 上），【日志在撒谎】"`** —— 第八次"日志误导"。
4. **三个清理范围的层次**：`setEnabled`（约 90 项，进程）/ `configureMatchRules`（约 37 项，比赛）/ `SvServerWorld::reset`（68 项，世界/地图）。
5. **`configureGameState` 的二十一个 `gameState.*` 本地拷贝** —— **因为下面 `std::move`**（第二次"移动前拷贝"）。
6. **⚠ `leadTakenSound_`/`leadLostSound_`/`winningFightSound_` 只在有值时设 ⇒ 一个跨地图的泄漏**（而 `headshotSound_.reset()` 显式清了）—— 一处不一致。
7. **⭐ `matchStartServerTime = 0` **在** `SV_PopulateRequiredConfigStrings` **之前**`** —— 第二次确认那个时间基。
8. **五个 OLMOD 环境变量，而四个是【链式】的**（`interactables ⇒ teleporters ⇒ bo1Travel`）—— 第二次确认那个模式。
9. **`gameState.scriptMenus[1..3]` 的三个名字**，而**"遗留的三槽解析器表是不同的，这只是响应名查找，不要覆盖原生菜单资产"`** —— 第二次确认 `changeclass_marines`，而**1 基索引**（第二次）。
10. **⭐⭐ `setZmZones` 用 `zmZonesMutex_` 不是 `mutex_`** —— 因为 **`loadGameplayScript` 已经持有 `mutex_` 而脚本要读区域** ⇒ **一个两把锁的设计**。
11. **⭐⭐ "不要混淆几何相邻与进度：两个体积可以相触而一扇关闭的门把它们分开"`** —— 第二次"几何 ≠ 拓扑"。
12. **"玩家在 Factory 上从 `receiver_zone` 开始，其它每个区域保持关闭直到对应的 `enter_*` 标志"`**。
13. **`activateZmZone` 的"返回是否变化"** —— 第五次"状态转换的可观察性"，而**幂等**。
14. **`configureSdSoundPresentation` 的三十三个声音**（两队 × 十四 + 两个全局），而**"三个都为空 ⇒ 拒绝"`**（不发明一个空的表现）。
15. **`ServerCore` 的十二条 setter 转发完全同构**（`const std::lock_guard lock(mutex_); world_.setXxx(...)`）—— 第七次"几乎相同的函数"。
16. **两个 getter 用不同的锁**（`zmBarrierCount` ⇒ `mutex_` / `zmZones` ⇒ `zmZonesMutex_`）—— 第二次确认两把锁的分工。
17. **⭐ `configureMatchRules` 的"`dmz` 无武装：大逃杀让你什么都不带开始，而它在这里设【因为世界拥有出生而它没有 gametype】"`** —— 第四次确认那个设计，而**一个架构分层的理由**。

## 十、未闭合点

- `LocalSoundEventParameterMaximum` 的值。
- `SvSdTeamSoundPresentation` 的完整字段。
- `zmZonesMutex_` 的完整用途（除 `setZmZones`/`activateZmZone`/`zmZones`）。
- `OLMOD_DMZ_UNARMED` 之外 `dmz` 的其它开关。
- `SV_PopulateRequiredConfigStrings` 的实现。
- `sv_main_mp.cpp` 2050 行之后未读取。
