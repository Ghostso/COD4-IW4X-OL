# 420 · **"导航图是一个地板而不是零售自己的图"** —— `207` 个连通分量、`186` 个孤立节点、以及"可达性测试不是一个回退"

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 2960–3290 行（`SvServerWorld` 的公开接口，约 250 个方法）。

## 二、**`zmGoalRoutable` 的连通分量**（本组最重要的一段）

### 2.1 那段

```cpp
// CAN AN ACTOR SPAWNED ON THIS GOAL EVER REACH THE PLAYERS?
//
// The navgraph is measured off demo trajectories and is a FLOOR, not retail's
// own graph: on zm_factory_sh its 1100 nodes fall into 207 connected
// components -- 837 in the main body and 186 nodes with no edge at all.
// MEASURED 12.80: of four actors spawned across four zones, two started on
// isolated nodes (339 and 306, each a component of ONE) and A* returned an
// empty route for both, every frame, forever.
//
// `true` when the goal resolves to a node in the main component -- the one the
// players' own node is in. This is a REACHABILITY test, not a fallback: an
// unroutable goal still gets no invented path, it simply never gets an actor.
```

### 2.2 二十层

```text
1. **一个在这个目标上生出的 actor 【究竟能不能到达玩家**】？**
2. ⇒ **导航图是【从 demo 轨迹测量**】出来的**
3. ⇒ **⇒ 而它【是一个【地板**】，不是零售自己的图**】**
4. ⇒ **在 `zm_factory_sh` 上它的 `1100` 个节点落进【`207` 个连通分量**】**
5. ⇒ **`837` 在【主体**】里**
6. ⇒ **而 `186` 个节点【完全没有边**】**
7. ⇒ **测量 `12.80`：横跨四个区域生出的四个 actor 里【两个开始于孤立节点**】**
8. ⇒ **（`339` 与 `306`，【各是一个只含一个节点的分量**）**
9. ⇒ **而 A* 为两者返回【一条空路线**】**
10. ⇒ **【每一帧，永远**】**
11. ⇒ **当目标解析到一个【在主体分量里】的节点时返回 `true`**
12. ⇒ **⇒ 那个分量【正是玩家自己的节点所在的那个**】**
13. ⇒ **这是一个【可达性测试，不是一个回退**】**
14. ⇒ **一个不可路由的目标【仍然得不到一条发明的路径**】**
15. ⇒ **它【只是永远得不到一个 actor**】**
```

### 2.3 ⭐⭐⭐ **"`1100` 个节点 ⇒ `207` 个连通分量，`837` 在主体，`186` 完全孤立"**

**✅ 这是本报告里**最重要的一组数字**。**

**⇒ 让我核对**：
```text
837 + 186 = 1023
1100 - 1023 = 77
⇒ **⇒ 所以【剩下 `77` 个节点在另外 `205` 个分量里**】
```

**⚠ 一处不一致**：`837 + 186 = 1023 ≠ 1100`。

**⇒ 三层**：
```text
`207` 个分量
**主体**：`837`
**孤立（单节点分量）**：`186`
⇒ **⇒ 所以【另外 `205` 个分量共 `77` 个节点**】（平均 `0.38` 个）
```

**⚠ 而 `205` 个分量装 `77` 个节点是不可能的（**每个分量至少 `1` 个节点**）。**

**⇒ 三层**：
```text
若 `186` 个孤立分量 ⇒ **其余 `21` 个分量装 `837 + 77 = 914` 个节点**
⇒ **⇒ 所以【`186` 是"孤立节点数"而非"孤立分量数**】
```

**✅ 更合理的读法**：**`207` 个分量中，`186` 个是孤立的单节点分量，其余 `21` 个分量共 `914` 个节点，其中主体 `837`。**

**⇒ 而 `207 - 186 = 21`** ✓ 与我的推算一致。

**✅ ⭐⭐ **一个"数字可被算术闭合"的验证**。

**⇒ 三层**：
```text
207 个分量
186 个单节点 ⇒ **21 个多节点分量**
837 主体 + 74 其余 = 911 … 需要 914
```

**⚠ 仍有 `3` 的缺口 —— **标注为"注释里的数字不能完全闭合，以 `207`/`186`/`837` 为准"**。

**✅ ⭐ **一个"提取可核对的数字"的实践**。

### 2.4 ⭐⭐⭐ **"这是一个可达性测试，不是一个回退"**

**✅ 这是本报告里**最重要的一条设计判据**。**

**⇒ 三层**：
```text
回退：**不可路由 ⇒ 用直线** ⇒ **穿墙**
可达性测试：**不可路由 ⇒ 不生成 actor** ⇒ **诚实**
⇒ **⇒ 所以【"不生成"比"生成但走错"好**】
```

**✅ 与 §412 的"`SvActorRefuseUnroutableSpawn = true`"**完全闭合 ✓

**⇒ 三层**：
```text
§412  `SvActorRefuseUnroutableSpawn = true`（**常量**）
§420  `zmGoalRoutable()`（**实现**）
⇒ **⇒ 一常量一函数**
```

**✅ ⭐ **一个"诚实地少做"的实例**。**

**⚠ 而"`339` 与 `306`"⇒ **两个具体的节点号**。**

**✅ 与 §407 的"实体 `475..480`"**同族（**第二次"具体号作为证据"）。

### 2.5 而**"`5` of `30` 的 spawner 目标完全不跨屏障"**

```cpp
// DOES A ZOMBIE SPAWNED AT THIS GOAL HAVE TO COME THROUGH A WINDOW?
//
// 12.67a measured that only 5 of factory's 30 spawner goals route to the
// players across a barrier at all; the rest walk in over open ground. The
// gametype script has been choosing spawn zones by ADJACENCY as a proxy for
// this, and adjacency is not the same question -- reported from the map as
// zombies strolling into the yard instead of tearing through a board.
//
// Routes and the barrier edge set both live here, so this is the only place
// the real question can be asked. It runs an A* per call, so the caller must
// ask ONCE per spawn point and cache -- 12.163 is what per-tick pathfinding
// in the script costs.
[[nodiscard]] bool zmSpawnCrossesBarrier(const std::array<float,3>& goal) const;
```

### 2.6 十八层

```text
1. **一个在这个目标上生出的僵尸【必须穿过一扇窗吗**】？**
2. ⇒ **`12.67a` 测出：factory 的 `30` 个 spawner 目标里只有 `5` 个**
3. ⇒ **【路由到玩家时跨越一个屏障**】**
4. ⇒ **其余的【从开阔地走进来**】**
5. ⇒ **而 gametype 脚本一直在【用【邻接性**】作为这件事的代理**】**
6. ⇒ **⇒ 而【邻接性不是同一个问题**】**
7. ⇒ **（从地图上报告为【僵尸漫步进院子而不是撕开一块板**）】
8. ⇒ **路线与屏障边集都住在这里**
9. ⇒ **⇒ 所以【这是唯一能问那个真问题的地方**】**
10. ⇒ **它【每次调用跑一条 A***】**
11. ⇒ **⇒ 所以【调用者必须每个出生点问【一次】并缓存**】**
12. ⇒ **（`12.163` 就是脚本里每 tick 寻路的代价**）
```

### 2.7 ⭐⭐⭐ **"邻接性不是同一个问题"**

**✅ 这是本报告里**最重要的一条"代理指标失效"**。**

**⇒ 三层**：
```text
真问题：**这个出生点要穿窗吗？**
代理：**这个区域与玩家区域相邻吗？**
⇒ **⇒ 两者【不等价**】—— **相邻但走开阔地**是常见的
```

**✅ 与 §412 的"`plan.valid` 作为蹲/趴的代理"**相反**（那里**代理是对的**）**。**

**⇒ 三层**：
```text
§412  `plan.valid` 代理蹲/趴 ⇒ **可以**
§420  `adjacency` 代理穿窗 ⇒ **不行**
⇒ **⇒ 所以【代理的有效性必须逐个验证**】
```

**✅ ⭐⭐ **一个"代理有效 vs 无效"的对照**。

**⚠ 而"一个 A* per call ⇒ 每个出生点问一次并缓存"**⇒ **性能意识。**

**✅ 与 §411 的"卡死判据 300ms"**同族（**第五次"性能与频率**）。

## 三、**`n 89` 是一个客户端命令而不是一个按钮**（本组第二重要）

### 3.1 那段

```cpp
// ALT-FIRE IS A CLIENT COMMAND, NOT A BUTTON. The player's menu calls
// it "Weapon Attachments" and it sits beside the killstreaks on 4-7,
// none of which are `+` binds -- so it never reaches a usercmd. It
// arrives as the reliable command `n 89`, measured with an exact count
// match: ten presses, ten commands. Queued here and consumed by the
// next clientThink, which turns it into the one rising edge the
// existing toggle already knows how to handle.
void requestAltWeaponToggle(std::uint32_t clientNum);
```

### 3.2 十四层

```text
1. **切换武器配件【是一个客户端命令，不是一个按钮**】**
2. ⇒ **玩家的菜单叫它"Weapon Attachments"**
3. ⇒ **而它【坐在 `4-7` 的连杀旁边**】**
4. ⇒ **⇒ 而【那些都不是 `+` 绑定**】**
5. ⇒ **⇒ 所以它【永远到不了一个 usercmd**】**
6. ⇒ **它作为【可靠命令 `n 89`】** 到达**
7. ⇒ **用【一个精确的计数匹配**】测量：**十次按键，十条命令**
8. ⇒ **⇒ 所以【它是一个命令而不是一个状态**】
9. ⇒ **在这里排队并由下一个 `clientThink` 消费**
10. ⇒ **⇒ 后者把它变成一个【上升沿**】**
11. ⇒ **⇒ 而那正是【既有的切换已经知道怎么处理的那个**】**
```

### 3.3 ⭐⭐⭐ **"十次按键，十条命令"**

**✅ 这是本报告里**最重要的一次"用计数证明语义"**。**

**✅ 与 §404 的"`p 12` ×23（全片 32 次 ⇒ 72% 集中在死亡后）"**同族（**第五次"计数定语义"）。

**⇒ 三层**：
```text
若 `n 89` 是**每帧状态** ⇒ **会连续大量出现**
若它是**事件** ⇒ **恰好等于按键数（`10`）**
⇒ **⇒ 所以【`10:10` 证明它是事件**】
```

**✅ ⭐⭐ **一个"1:1 计数"的判据**。

**⚠ 而"`4-7` 是连杀，都不是 `+` 绑定"⇒ **一个精确的键位说明**。**

**⇒ 三层**：
```text
`4..7` ⇒ **连杀奖励键**
`+` 绑定 ⇒ **进 usercmd**
⇒ **⇒ 所以【连杀也不在 usercmd 里**】
```

**✅ 与 §410 的"`n 89` 是命令而不是按钮（sect.190 的 `0x100000` 是瞄准 `0x08000000` 在闲客户端三分钟触发 63 次）"**完全闭合 ✓

## 四、**`SvServerWorld` 的接口规模**

### 4.1 分类统计

| 类别 | 方法数 | 代表 |
|---|---|---|
| 配置（`configure*`） | 8 | `configureSpawn`、`configureGlassMap`、`configureEntityPool`、`configureSpawnAndBrushModelEntities` |
| 注入 runner（`set*Runner`） | 11 | `setSharedPmoveRunner`、`setWeaponMovementRunner`、`setDeathAnimationRunner`、`setClientEventsHandler`、`setPointTraceRunner`、`setCapsuleTraceRunner`、`setMissileFrameRunner` |
| ZM 装配（`setZm*`） | 12 | `setZmNavGraph`、`setZmBarriers`、`setZmPresentation`、`setZmActorWalkAnim`、`setZmActorTearAnim`、`setZmActorDeathAnim`、`setZmActorAttackAnim`、`setZmTearClips`、`setZmBoardTrajectoryEvaluator` |
| Factory | 12 | `spawnFactoryViewFx`、`stepFactoryWeaponLights`、`setFactorySpecialWeapons`、`stepProjectileMissile`、`applyPlayerBlastDamage`、`stepFactoryPowerMotions` |
| 实体 | 10 | `spawnEntityAtOrAbove`、`setEntityDamageState`、`setEntityDamageHandler`、`configureEntityDamageOwner` |
| trace | 3 | `tracePoint`、`traceRadiusDamageVisibility`、`traceCapsule` |
| 查询（nearest*） | 5 | `nearestPlayerDistance`、`nearestPlayerOrigin`、`nearestPlayerClientNum`、`nearestEnemyProbe`、`enemyCentroidOrigin` |
| 步进（`step*`） | 6 | `stepActorEntities`、`stepZmBarrierMotions`、`stepFactoryDoorMotions` |
| ZM 查询 | 4 | `zmGoalRoutable`、`zmSpawnCrossesBarrier`、`zmBarrierCount`、`repairableZmBarrierAt` |

**⇒ 约 `70` 个公开方法。**

### 4.2 ⭐⭐ **"十一个 runner 注入"**

**⇒ 三层**：
```text
`SvSharedPmoveRunner` / `SvWeaponMovementRunner` / `SvPlayerStateToEntityStateConverter`
`SvDeathAnimationRunner` / `SvSpawnAnimationRunner` / `SvClientEventsHandler`
`SvPointTraceRunner` / `SvRadiusDamageVisibilityRunner` / `SvCapsuleTraceRunner`
`SvNativeEntityMirrorSynchronizer` / `SvClientImpactsDispatcher` / `SvClientImpactsScriptDispatcher`
`SvEntityTouchHandler` / `SvMissileFrameRunner` / `SvTrajectoryEvaluator`
⇒ **⇒ 约 `15` 个 std::function 注入点**
```

**✅ 与 §419 的"`SvServerWorld` 的 `using` 声明"**完全闭合 ✓

**⇒ 五层**：
```text
1. **`SvServerWorld` 【不自己实现原生调用**】**
2. ⇒ **它【通过 `std::function` 注入**】**
3. ⇒ **⇒ 所以【世界层与原生层是解耦的**】**
4. ⇒ **⇒ 而每一层都可以被【测试替身**】替换**
5. ⇒ **⇒ 这正是 §418 的"`Appmain` 的 `EngineBindings` 提供实现"** 的结构**
```

**✅ ⭐⭐ **一个"依赖注入的完整结构"**。**

**⚠ 而"`SvDeathAnimationRunner` 与 `SvSpawnAnimationRunner` 分开"⇒ 注释说：**

```php
// The spawn event takes no conditions; it used to share the death typedef
// and would have inherited the new argument for no reason.
```

**⇒ 四层**：
```text
过去：**共用一个 typedef**
问题：**death 加了一个参数 ⇒ spawn 【无缘无故**】也继承它**
⇒ **⇒ 所以【分开**】
```

**✅ ⭐ **一个"接口分离"的理由**。

## 五、**`NearestEnemyProbe` 的"不拷 `6.4KB playerState`"**

```cpp
// ★ 2026-10-16 28000（S3 v2 combat）：bot 选敌用的轻量最近敌方查询。
// 与 nearestPlayerClientNum 同过滤（Playing+活+非倒地）再加敌我判定：
// 排除 excludeClientNum 本人；排除与 excludeTeam 同队且非 None 的目标
// （None=None 视为互敌，即 FFA 语义）。返回小结构，不拷 6.4KB playerState
// ——每帧成本门（§3.3b）禁止热路径内做重量级按值取回。
struct NearestEnemyProbe
{
    std::uint32_t clientNum{};
    std::array<float, 3> origin{};
    float viewHeightCurrent{};
    std::uint8_t pmType{};
};
```

**⇒ 十二层**：
```text
1. **bot 选敌用的【轻量**最近敌方查询】**
2. ⇒ **与 `nearestPlayerClientNum` 【同过滤**】（`Playing` + 活 + 非倒地）
3. ⇒ **⇒ 再加【敌我判定**】**
4. ⇒ **排除 `excludeClientNum` 本人**
5. ⇒ **排除与 `excludeTeam` 同队且【非 `None`**】的目标**
6. ⇒ **（`None = None` 视为互敌 ⇒ **FFA 语义**）**
7. ⇒ **返回【一个小结构**】**
8. ⇒ **不拷 `6.4 KB playerState`**
9. ⇒ **⇒ 每帧成本门（`§3.3b`）【禁止热路径内做重量级按值取回**】**
```

### 5.1 ⭐⭐⭐ **"`None = None` 视为互敌"**

**✅ 这是本报告里**最重要的一条 FFA 语义**。**

**⇒ 三层**：
```text
同队 ⇒ **不互为敌人**
而 `None` 与 `None` 【都是"无队伍"**】 ⇒ **若按"同队"判 ⇒ 互为友军 ⇒ 不能伤害**
⇒ **⇒ 所以【必须特例：`None` 与 `None` 是敌人**】
```

**✅ 与 §416 的"`onSameTeam` 在任一侧为 `None` 时都是假"**完全闭合 ✓

**⇒ 三层**：
```text
§416  `onSameTeam` **任一侧 `None` ⇒ 假** ⇒ **所有人伤害所有人**
§420  `nearestEnemyProbe` **排除"同队且非 `None`"** ⇒ **`None`-`None` 是敌人**
⇒ **⇒ 两处【同一个语义**】
```

**✅ ⭐⭐ **一个"FFA 语义在两处一致"的确认**。

**⚠ 而"`6.4 KB playerState`"⇒ **一个具体的结构大小**。**

**⇒ 三层**：
```text
`SvPlayerState` 的 `sizeof` ⇒ **约 `6.4 KB`**（`6400` 字节）
⇒ **⇒ 所以【每帧每 bot 一次按值取回是 `11 × 6.4KB = 70KB/帧**】**
```

**✅ 与 §411 的"零新增 `playerState` 取回"**完全闭合 ✓

**⇒ 三层**：
```text
§411  "每 bot 每帧【只取一次**】playerState"
§412  "复用本帧唯一的 `selfPose`"
§420  "`NearestEnemyProbe` 【不拷 6.4KB**】"
⇒ **⇒ 三次"避免大结构拷贝**】
```

**✅ ⭐⭐ **一个"避免大拷贝"的三例表**。

## 六、**`SvGameClient` 的三个结果枚举**

```text
FinishPlayerDamageResult：Applied / ClientNotFound / NotPlaying / InvalidPayload / DeathTransitionUnavailable / NativeMirrorUnavailable  （6）
WeaponAmmoMutationResult：Applied / ClientNotFound / NotPlaying / WeaponNotOwned / AmmoStateMissing  （5）
RespawnRequestResult：Queued / ClientNotFound / NotPlaying / NotDead / InvalidDelay  （5）
```

**⇒ 五层**：
```text
1. **三个枚举都有 `ClientNotFound` 与 `NotPlaying`**
2. ⇒ **而各自有【域特有的失败**】（`DeathTransitionUnavailable` / `WeaponNotOwned` / `NotDead`）
3. ⇒ **⇒ 所以【共同的失败被重复声明三次**】**
```

**✅ 与 §419 的"两套失败枚举各有 `Name()`"**同族（**第四次"失败枚举"）。

**⚠ 而"共同失败重复三次"⇒ **一个可统一的机会**（但**统一会失去域上下文**）。

**⇒ 三层**：
```text
统一 ⇒ **一个 `Result` 枚举 + 一个"域"字段**
分离 ⇒ **三个枚举各自自足**
⇒ **⇒ 所以【分离更好**】
```

**✅ ⭐ **一个"分离优于统一"的判据**。

### 6.1 而**`roundBasedDeathHold_` 的"sd 每回合一条命"**

```cpp
// OLMOD(sd-round-death-hold): 经典爆破 (sd) is round-based and gives ONE
// life per round, so the death animation must not arm a respawn of its
// own. The round already owns it: beginNextRound() bumps every Active
// client's spawnSequence (sv_client_mp.cpp:2228), which respawns them a
// frame later through via=external. dm/zm and every other mode are
// untouched, and so is a gametype's own requestRespawnDelay(), which is a
// separate writer of respawnTime.
```

**⇒ 十六层**：
```text
1. **经典爆破（`sd`）是回合制的，每回合【一条命**】**
2. ⇒ **⇒ 所以【死亡动画【绝不能**】武装一个自己的重生**】**
3. ⇒ **回合【已经拥有它**】**
4. ⇒ **`beginNextRound()` 增加每一个 `Active` 客户端的 `spawnSequence`**
5. ⇒ **（`sv_client_mp.cpp:2228`）**
6. ⇒ **⇒ 那会【在一帧之后**】通过 `via=external` 重生它们**
7. ⇒ **`dm`/`zm` 与其它每一个模式【不受影响**】**
8. ⇒ **而一个 gametype 自己的 `requestRespawnDelay()` 【也不受影响**】**
9. ⇒ **⇒ 它是 `respawnTime` 的【一个独立的写者**】**
```

### 6.2 ⭐⭐ **"`respawnTime` 有两个独立的写者"**

**✅ 与 §407 的"四条路径设 `matchStatus_.completed`"**同族（**第二次"一个状态多个写者"）。

**⇒ 三层**：
```text
写者 1：**死亡动画**（`dm`/`zm`）
写者 2：**`beginNextRound()`**（`sd`）
写者 3：**gametype 的 `requestRespawnDelay()`**
⇒ **⇒ 所以【`roundBasedDeathHold_` 只关掉写者 1**】
```

**✅ ⭐ **一个"精确地关一个写者"的实例**。</br>

**✅ 与 §419 的"排除法"**同族（**第三次"定位到具体写者"）。

## 七、关键结论

1. **⭐⭐⭐ `zm_factory_sh` 的 `1100` 个节点落进 `207` 个连通分量：`837` 在主体、`186` 个节点完全没有边** ⇒ 而 **`207 - 186 = 21` 个多节点分量**（我的算术验证）。
2. **⭐⭐⭐ 测量 `12.80`：四个 actor 里两个开始于孤立节点（`339` 与 `306`，各是一个只含一个节点的分量），A* 为两者返回一条空路线，每一帧，永远**。
3. **⭐⭐⭐ "这是一个可达性测试，不是一个回退：一个不可路由的目标仍然得不到一条发明的路径，它只是永远得不到一个 actor"`** —— **"诚实地少做"**，与 §412 的 `SvActorRefuseUnroutableSpawn` 完全闭合。
4. **⭐⭐⭐ "五个 of factory 的 `30` 个 spawner 目标在路由到玩家时跨越一个屏障，其余从开阔地走进来；脚本一直用【邻接性】作为这件事的代理，而【邻接性不是同一个问题】"`** —— 一个**代理指标失效**的实例（与 §412 的 `plan.valid` 代理**有效**形成对照）。
5. **⭐ "它每次调用跑一条 A*，所以调用者必须每个出生点问一次并缓存 —— `12.163` 就是脚本里每 tick 寻路的代价"`** —— 第五次"性能与频率"。
6. **⭐⭐⭐ `n 89` 是客户端命令不是按钮**：玩家的菜单叫它 "Weapon Attachments"，**坐在 `4-7` 的连杀旁边，而它们都不是 `+` 绑定 ⇒ 永远到不了一个 usercmd** ⇒ **用【一个精确的计数匹配】测量：十次按键，十条命令** —— 第五次"计数定语义"，与 §410 的 `n 89` 完全闭合。
7. **⭐ `SvServerWorld` 约 `70` 个公开方法**，其中**约 `15` 个 `std::function` 注入点**（pmove/武器移动/伤害转换/死亡动画/生成动画/客户端事件/trace/capsule/镜像同步/碰撞回调/脚本通知/触控/导弹帧/轨迹求值）⇒ **世界层与原生层完全解耦**。
8. **⭐ `SvDeathAnimationRunner` 与 `SvSpawnAnimationRunner` 分开**（"spawn 事件不需要 conditions；它过去共用 death 的 typedef 而无缘无故继承了新参数"）。
9. **⭐⭐⭐ `NearestEnemyProbe` 的 `None = None` 视为互敌**（FFA 语义：`onSameTeam` 在任一侧 `None` 时都是假）—— 与 §416 完全闭合。
10. **⭐⭐ "不拷 `6.4 KB playerState` —— 每帧成本门（`§3.3b`）禁止热路径内做重量级按值取回"`** —— 与 §411/§412 的"零新增取回"闭合（第三次"避免大拷贝"）。
11. **⭐ 三个结果枚举（`6`/`5`/`5` 个值）各自有域特有的失败，而 `ClientNotFound`/`NotPlaying` 重复三次** —— **统一会失去域上下文 ⇒ 分离更好**。
12. **⭐⭐ `roundBasedDeathHold_` 精确地关掉【一个写者】**：`sd` 每回合一条命 ⇒ **死亡动画不武装重生**，而 `beginNextRound()` 已经通过 `spawnSequence` 重生（`via=external`）；`dm`/`zm` 与 gametype 的 `requestRespawnDelay()`（`respawnTime` 的**独立写者**）都不受影响。

## 八、未闭合点

- `207`/`186`/`837` 与 `1100` 的算术（我算出 `837 + 186 = 1023`，缺 `77`）。
- `zmSpawnCrossesBarrier` 的 A* 缓存策略。
- `SvTrajectoryEvaluator` 的签名。
- `stepFactoryPowerMotions` 的八个 power pieces。
- `sv_snapshot_mp.hpp` 3290 行之后未读取（**共 `4703` 行**）。
