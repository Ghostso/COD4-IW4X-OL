# 369 · **"一次冻结也必须让手停下来"** —— `pmFlags |= 0x800` 让客户端停止推进命令时间、中性化命令而不跳过 pmove

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 19200–19600 行。

## 二、**`pmFlags |= 0x800` 的完整事故**（本组最重要的一段）

### 2.1 那段

```php
// A FREEZE HAS TO STOP THE HANDS TOO. Holding the origin while still
// feeding the player's buttons to pmove leaves them aiming, firing and
// reloading on the spot -- a player reported it as "spamming ADS like I
// was still alive and it was jittering the camera by doing that", and
// the jitter is the client predicting movement against an origin this
// server rewrites every frame.
//
// The command is neutralised rather than the pmove skipped: pmove owns
// weapon timers, animation and the native mirror, and not running it
// leaves all of that frozen mid-transition instead of settling.
//
// 28800: THE PREMATCH HOLD IS ITS OWN BRANCH AND MUST NOT TOUCH pmFlags.
//
// 28500 removed the previous attempt for a measured reason: setting
// `pmFlags |= 0x800` made the CLIENT stop advancing its own command
// time, so once the flag was cleared the server rejected every later
// command with `stage=non_increasing_command_time` and the player could
// not walk. Nothing here writes pmFlags.
//
// What it does instead is exactly what the match-end/revive path already
// does to the COMMAND -- zero buttons / forwardMove / rightMove -- while
// leaving commandTime untouched. That path is proven, and the pmove
// still runs so weapon timers and the native mirror keep settling.
```

### 2.2 十八层

```text
1. **一次冻结也必须让【手】停下来**
2. ⇒ **持有原点而仍把玩家的按钮喂给 pmove**
3. ⇒ **让他们在原地瞄准、开火、换弹**
4. ⇒ **一个玩家报告为"像我仍然活着一样狂按 ADS 而它通过那样做在抖动相机"**
5. ⇒ **而那个抖动是客户端对着一个【这个服务器每帧重写】的原点做移动预测**
6. ⇒ **命令被【中性化】而不是跳过 pmove**
7. ⇒ **因为 pmove 拥有武器计时器、动画与原生镜像**
8. ⇒ **而不跑它把那些都冻在【过渡中途】而不是落定**
9. ⇒ **28800：赛前保持是【它自己的分支】而【绝不能碰 pmFlags】**
10. ⇒ **28500 因一个【测量到的】理由移除了之前的尝试**
11. ⇒ **设 `pmFlags |= 0x800` 让【客户端】停止推进它自己的命令时间**
12. ⇒ **所以一旦那个标志被清**
13. ⇒ **服务器用 `stage=non_increasing_command_time` 拒绝之后每一条命令**
14. ⇒ **而玩家【不能走路】**
15. ⇒ **这里什么都不写 `pmFlags`**
16. ⇒ **它做的恰好是比赛末/复活路径已经对【命令】做的**
17. ⇒ **（清零 `buttons` / `forwardMove` / `rightMove`）而【不动 `commandTime`】**
18. ⇒ **那条路径是【已证明的】**
19. ⇒ **而 pmove 仍然跑，所以武器计时器与原生镜像继续落定**
```

### 2.3 ⭐⭐ **"设标志让【客户端】停止推进它自己的命令时间"**

**✅ 这是本文件里**最反直觉的一条**。**

**⇒ 三层**：

```text
1. `pmFlags |= 0x800` 是【服务端】的写
2. ⇒ **而它的效果是【客户端】停止推进命令时间**
3. ⇒ **所以清掉标志后命令时间【永不递增】**
4. ⇒ **而服务器要求【递增】⇒ 拒绝所有命令**
5. ⇒ **所以玩家永久不能走**
```

**✅ 与 §360 的"eType 21 杀死客户端"**同族（**第二次"一个字段的远端后果"**）。

**⚠ 而这里**没有崩溃**，只是**永久不能走**。**

**⇒ **一个更隐蔽的失败**。**

**✅ 与 §368 的"被拒帧花掉一个心跳"**不同**（那是**1/60**，这是**100%**）。

### 2.4 而**"那条路径是【已证明的】"**

**✅ 与 §369 的"28500 因一个测量到的理由移除"**同族。**

**⇒ 三层**：

```text
① 一次失败的尝试（`pmFlags |= 0x800`）
② **而一个【已证明的】替代（零化 usercmd 字段）**
③ **所以用后者**
```

**✅ 与 §362 的"两个极端都试过"**第**四次"多次尝试"**。

### 2.5 而**"中性化命令而不跳过 pmove"**

**✅ 三层**：

```text
跳过 pmove   ⇒ 武器计时器/动画/镜像【冻在过渡中途】
中性化命令   ⇒ **那些继续落定**
```

**✅ 与 §358 的"按住直到领导者清空接近"**同族（**第二次"不做事而是喂一个安全的输入"**）。

### 2.6 而**"保留看向角度与武器切换"**

```php
// 28800: the operator's prematch rule is "look around and switch
// your class, but do not move or shoot". So the LOOK angles survive
// untouched (they are not in this struct), and the weapon-switch
// command survives: `PM_BeginWeaponChange` is driven by the number
// keys / wheel, not by a usercmd button, so only the movement and
// fire buttons are cleared here.
frozenCommandState.currentUserCmd.buttons = 0;
frozenCommandState.currentUserCmd.forwardMove = 0;
frozenCommandState.currentUserCmd.rightMove = 0;
if (frozenCommandState.oldUserCmd) {
    frozenCommandState.oldUserCmd->buttons = 0;
    frozenCommandState.oldUserCmd->forwardMove = 0;
    frozenCommandState.oldUserCmd->rightMove = 0;
}
```

**⇒ 八层**：

```text
1. **操作员的赛前规则是"环顾并切换你的职业，但不要移动或开火"**
2. ⇒ **所以【看向角度】原样存活**（它们不在这个结构里）
3. ⇒ **而【武器切换】命令存活**
4. ⇒ **因为 `PM_BeginWeaponChange` 由数字键/滚轮驱动**
5. ⇒ **而不是由一个 usercmd 按钮**
6. ⇒ **所以这里只清移动与开火按钮**
7. ⇒ **而 `oldUserCmd` 也清**
8. ⇒ **所以"两个命令"都中性化**
```

**✅ 一个**精确的用户体验规格**（从操作员的规则推导）。**

**⚠ 而"看向角度不在这个结构里"⇒ **所以它们自动保留**。**

**✅ 与 §368 的"`Look angles survive untouched`"配合。**

### 2.7 而**"玩家报告『狂按 ADS 而相机抖动』"**

**✅ 与 §355 的"玩家的判决"**第五次。**

**⇒ 三层**：

```text
1. 服务器持原点
2. ⇒ **而客户端仍预测移动**
3. ⇒ **所以每帧校正 ⇒ 抖动**
```

**✅ 与 §343 的"坐标要对着它被编码时用的基线测"**不同** —— 这是**预测与服务端不一致**。**

**⚠ 一个**常见的网络代码问题**。**

## 三、**复活冻结的两个条件**

```cpp
auto frozenCommandState = *client.commandState;
const bool travelHold = factoryTravelHeld(playerState.clientNum, playerState.spawnGeneration);
const bool reviveHold = (travelHold || zombieReviveHeld(playerState.clientNum)) &&
    (travelHold || (frozenCommandState.currentUserCmd.buttons & UserCmdButtonActivate) != 0);
```

### 3.1 四层

```text
1. **`travelHold`**（工厂旅行）
2. ⇒ **`reviveHold` = (travel 或 revive) 而（travel 或 有 Activate 按钮）**
3. ⇒ **所以旅行【不需要】按钮**
4. ⇒ **而复活【需要】Activate**
```

**✅ 一个**精确的双条件**。**

**⚠ 而 `travelHold` 短路 ⇒ **所以旅行时总冻结**。**

### 3.2 而**"复活时强制写当前武器"**

```cpp
if (reviveHold) {
    frozenCommandState.currentUserCmd.weapon = playerState.currentWeaponAssetIndex;
    if (frozenCommandState.oldUserCmd)
        frozenCommandState.oldUserCmd->weapon = playerState.currentWeaponAssetIndex;
}
```

**⇒ 三层**：

```text
1. **复活时把 cmd 的武器字段设为【服务端的当前武器】**
2. ⇒ **所以客户端不能通过 cmd 换枪**
3. ⇒ **而 `oldUserCmd` 也同步**
```

**✅ 与 §369 二.6 的"武器切换命令存活"**矛盾**？**

**⚠ 不矛盾**：那个是**赛前**（允许换职业），这个是**复活**（不允许换枪）。**

**✅ 两个不同场景。**

## 四、**`fullCommandState` 的两处清零**

### 4.1 未出生时的清零（29 项）

```cpp
playerState.pmType = 5;
playerState.eFlags |= 0x10u;
playerState.groundEntityNum = EntityNumNone;
playerState.viewmodelIndex = 0;
playerState.currentWeaponAssetIndex = 0;
playerState.weaponAnim = {};
playerState.weaponTime = {};
playerState.weaponDelay = {};
playerState.weaponState = {};
playerState.heldWeapons = {};
playerState.ammoClips = {};
playerState.ammoPools = {};
entity.networkState.eventSequence = 0;
// 而实体侧的 17 项
```

**⇒ 三层**：

```text
1. **`pmType = 5`**（等待职业）
2. ⇒ **`eFlags |= 0x10`**（隐藏位）
3. ⇒ **而"没有武器、没有弹药、没有动画"**
```

**✅ 与 §368 八的"`pmType = 4`（未出生）"**不同**。**

**⇒ **两个不同的 pmType：**

```text
4   刚连接，无任何状态
5   Factory 等待职业选择
0   正常（§364 的"pmType == 0 才能传送"）
```

**✅ 三个值。**

**⚠ 而 §368 用 `pmType = 4` 而这里用 `5`。**

**⇒ 所以**4 = "未请求"而 5 = "在等职业"**。**

**✅ 与注释的"original Factory 10950..19950 has pm_type 5 and eFlags 31"**配合。**

### 4.2 而 `eFlags |= 0x10` 的理由

```php
// CODDIFF(client_spawn): original Factory 10950..19950 has
// pm_type 5 and eFlags 31. Restore the waiting type and only the
// needed hide bit: out.exe 53C650 skips the zero-viewmodel path
// at 53C6AA..53C704 when ps+0xFC bit0x10 is set. This remains
// non-playing even after Escape; only a resolved class spawns.
```

**⇒ 七层**：

```text
1. **原始 Factory `10950..19950` 有 `pm_type 5` 与 `eFlags 31`**
2. ⇒ **恢复等待类型与【只】那个需要的隐藏位**
3. ⇒ **`out.exe 53C650` 在 `53C6AA..53C704` 跳过零视模型路径**
4. ⇒ **当 `ps+0xFC` 的 bit `0x10` 被设**
5. ⇒ **所以设 `0x10` 避免那个路径**
6. ⇒ **而在 Escape 之后这仍是"非游戏中"**
7. ⇒ **只有一个已解析的职业才生成**
```

**✅ 与 §368 的"`playerState.eFlags &= ~0x10u` 在生成前"**完全闭合 ✓**

**⇒ **一个 `0x10` 位的完整生命周期**（等职业时设，生成时清）。

## 五、**`beginFrame` 的回滚（八项）**

```php
if (nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) {
    const auto attemptedServerTime = snapshot_.serverTime;
    for (auto &[clientNum, previous] : previousClientStates) {
        if (previous) clientStates_.insert_or_assign(clientNum, std::move(*previous));
        else clientStates_.erase(clientNum);
    }
    factoryArrivalHolds_ = previousArrivalHolds;
    snapshot_ = std::move(previousSnapshot);
    snapshot_.serverTime = attemptedServerTime;
    frameEvents_ = std::move(previousFrameEvents);
    deferredEvents_ = std::move(previousDeferredEvents);
    eventSequence_ = previousEventSequence;
    lastEvent_ = previousLastEvent;
    rebuildCollisionView(SvNativeEntityMirrorPhase::Presentation);
    return false;
}
```

### 5.1 九层

```text
1. **记下 `attemptedServerTime`**（在回滚前）
2. ⇒ **恢复每个 `clientStates_` 条目**（有则赋值，无则删除）
3. ⇒ **恢复 `factoryArrivalHolds_`**
4. ⇒ **`snapshot_ = std::move(previousSnapshot)`**
5. ⇒ **但 `serverTime = attemptedServerTime`**（**保持单调**）
6. ⇒ **恢复 `frameEvents_` / `deferredEvents_`**
7. ⇒ **恢复 `eventSequence_` / `lastEvent_`**
8. ⇒ **重建碰撞视图**
9. ⇒ **返回 false**
```

### 5.2 ⭐ **"帧调度器已经消费了这一段墙钟时间 ⇒ 保持 `serverTime` 单调而撤回所有玩法与序列化载荷变异"**

```php
// The fixed-frame scheduler has consumed this wall-clock slice.
// Keep serverTime monotonic while withdrawing all gameplay and
// serialized payload mutations from the rejected frame.
snapshot_.serverTime = attemptedServerTime;
```

**⇒ 五层**：

```text
1. **固定的帧调度器已经消费了这一段墙钟时间**
2. ⇒ **所以 `serverTime` 必须【保持单调】**
3. ⇒ **而【撤回】所有玩法与序列化载荷的变异**
4. ⇒ **所以只有 `serverTime` 不回滚**
5. ⇒ **一个精确的"时间不可回滚而状态可回滚"**
```

**✅ 与 §368 的"一个被拒帧推进 `zmRoundTickMilliseconds_`"**同族（**第二次"时间单向"**）。

**⇒ **一个极重要的原理**：**

```text
时间      ⇒ **单调，不可回滚**
状态      ⇒ **可回滚**
```

**✅ 与 §349 的"进程生命期锁存"**不同**（那是**不重置**，这是**不回滚**）。

### 5.3 而**`previousClientStates` 的"有则赋值，无则删除"**

**⇒ 三层**：

```text
1. `previous` 有值 ⇒ **`insert_or_assign`**（恢复或新增）
2. ⇒ `previous` 为 `nullopt` ⇒ **`erase`**（这个客户端本帧【新增】）
3. ⇒ **所以两个方向都恢复**
```

**✅ 与 §364 的"`std::swap` 回滚"、§365 的"`= std::move` 回滚"**第三种回滚风格。**

**⇒ **三种回滚风格**（swap / move / 双向 insert-erase）。**

## 六、**`pendingActorPlayerDamage_` 的"在镜像之后"**

```php
// Actor melee is committed only after the ordinary begin-frame player
// image has passed its native mirror transaction. finishPlayerDamage may
// create a player corpse on a lethal hit, so doing this inside the actor
// entity iteration would invalidate that iteration.
for (const auto &damage : pendingActorPlayerDamage_) {
    const auto result = finishPlayerDamage(damage);
    OlMod::RuntimeLog::write(..., "ZMHIT ... result=" + std::to_string((int)result));
}
pendingActorPlayerDamage_.clear();
```

### 6.1 六层

```text
1. **actor 近战只在 begin-frame 的玩家镜像事务【通过之后】提交**
2. ⇒ **因为 `finishPlayerDamage` 在一次致命命中上【可能创建一具玩家尸体】**
3. ⇒ **所以在 actor 实体迭代【之内】做这个会让那个迭代失效**
4. ⇒ **所以排队**
5. ⇒ **而 `result` 是【整数值】而不是名字**（与 §368 的六种名字不同）
6. ⇒ **所以这是【一个退化】的日志**
```

**⚠ 而 §368 的摔落伤害有 `damageResultName` 而这里用 `std::to_string((int)result)`。**

**⇒ **一处不一致**（同一个枚举两种打印方式）。**

**✅ 与 §344 的"每次击杀六行"**同族（**日志质量不一致**）。

### 6.2 而**"会让那个迭代失效"**

**✅ 与 §355 的"尸体排队而不是在这里释放"**完全同族（**第二次"迭代失效"**）。

**⇒ 三层**：

```text
1. `finishPlayerDamage` 可能 `entities_.emplace`（新尸体）
2. ⇒ **而外层在迭代 `entities_`**
3. ⇒ **所以必须排队**
```

**✅ **第三次"收集后处理"。**

## 七、**`freeEntity` 的三个调用点（在镜像之后）**

```php
if (entityPool_) {
    const auto expired = entityPool_->expiredEventEntities(snapshot_.serverTime);
    for (const auto handle : expired) static_cast<void>(freeEntity(handle));
    // Actor corpses only; torn boards retain their brush entities.
    // Same rule, same place: after the mirror has accepted the
    // frame. The generation comes from the pool because a bare handle
    // carries 0 and freeEntity fails closed on it.
    for (const auto entityNum : pendingActorFrees_) {
        const auto *const lifetime = entityPool_->resolve(entityNum);
        if (lifetime && (!zmDeaths_.empty()
                ? retainZombieCorpse({entityNum, lifetime->generation})
                : freeEntity({entityNum, lifetime->generation})))
        {
            zmActorDeadAt_.erase(entityNum);
            entityDamageStates_.erase(entityNum);
            actorRoutes_.erase(entityNum);
        }
    }
    pendingActorFrees_.clear();
}
```

### 7.1 九层

```text
1. **事件实体过期**（`expiredEventEntities`）
2. ⇒ **actor 尸体（`pendingActorFrees_`）**
3. ⇒ **"同一条规则，同一个地方：在镜像接受这一帧【之后】"**
4. ⇒ **代际来自池**
5. ⇒ **因为一个裸句柄携带 0 而 `freeEntity` 在它上面【故障关闭】**
6. ⇒ **而若 `zmDeaths_` 非空 ⇒ `retainZombieCorpse`**（保留而不是释放）
7. ⇒ **否则 `freeEntity`**
8. ⇒ **而三者都成功 ⇒ 清三个表**（`zmActorDeadAt_` / `entityDamageStates_` / `actorRoutes_`）
```

**✅ 与 §355 的"尸体转账到有界池"**完全闭合 ✓

**⇒ **第二次确认 `retainZombieCorpse`。**

### 7.2 而**"一个裸句柄携带 0"**

**⇒ 三层**：

```text
1. `SvEntityHandle{e}` 若没有 generation ⇒ **generation = 0**
2. ⇒ **而 `freeEntity` 的 `resolve(handle)` 会失败**（代际不匹配）
3. ⇒ **所以必须从池里查**
```

**✅ 与 §363 的"代际拥有的 `G_FreeEntity`"**完全一致 ✓

**⇒ **第二次确认代际的必要性。**

## 八、**`zmRetainedCorpses_` 的 100 秒 / 32 上限**

```php
// Reconstructed bounded policy: 100 seconds from death, maximum 32.
// Retirement is outside the player-frame transaction, like actor frees.
for (auto it = zmRetainedCorpses_.begin(); it != zmRetainedCorpses_.end();) {
    const auto *slot = entityPool_ ? entityPool_->resolve(it->handle) : nullptr;
    if (!slot || (snapshot_.serverTime - it->diedAt >= 100000u && freeEntity(it->handle)))
        it = zmRetainedCorpses_.erase(it);
    else ++it;
}
```

### 8.1 五层

```text
1. **重建的有界策略：死后 100 秒，最多 32 个**
2. ⇒ **退役在玩家帧事务【之外】**（像 actor 释放）
3. ⇒ **两个释放条件**：槽失效 / **100 秒到且 `freeEntity` 成功**
4. ⇒ **注意 `freeEntity` 成功才 erase**（否则保留重试）
5. ⇒ **一个精确的"失败则重试"**
```

**✅ 与 §365 的"成功后【才】设 `started`"**同族（**第三次"成功后才改状态"**）。

## 九、关键结论

1. **⭐⭐ "一次冻结也必须让【手】停下来"`** —— 持原点而喂按钮让玩家**在抖动中狂按 ADS**（客户端对着每帧重写的原点做预测）。
2. **"命令被【中性化】而不是跳过 pmove"`** —— 因为 pmove 拥有武器计时器/动画/镜像，不跑它会把那些**冻在过渡中途**。
3. **⭐⭐ "设 `pmFlags |= 0x800` 让【客户端】停止推进它自己的命令时间 ⇒ 清掉后服务器拒绝所有命令 ⇒ 玩家不能走路"`** —— 第二次"一个字段的远端后果"。
4. **"28800 的赛前保持是它自己的分支而绝不能碰 `pmFlags`"`** —— 而**替代方案是已证明的**（零化 usercmd 字段）。
5. **"操作员的赛前规则是『环顾并切换你的职业，但不要移动或开火』"`** —— 所以**看向角度与武器切换存活**（后者由数字键/滚轮驱动，不是 usercmd 按钮）。
6. **`travelHold` 短路（不需要按钮）而 `reviveHold` 需要 `Activate`** —— 一个精确的双条件。
7. **复活时强制 `cmd.weapon` 为服务端当前武器**（与赛前允许换职业**不矛盾**，两个场景）。
8. **三个 `pmType`**：`4`（刚连接）/ `5`（Factory 等职业）/ `0`（正常）。
9. **`eFlags |= 0x10` 的完整生命周期**（等职业时设以避免 `out.exe 53C650` 的零视模型路径，生成时清）。
10. **⭐ `beginFrame` 的九项回滚**，而 **"`serverTime` 必须保持单调而所有玩法与序列化载荷变异被撤回"`** —— **一个"时间单向 / 状态可回滚"的原理**（第二次"时间单向"）。
11. **`previousClientStates` 的双向恢复**（有则赋值，无则删除）—— **第三种回滚风格**。
12. **`pendingActorPlayerDamage_` 在镜像之后** —— 因为 `finishPlayerDamage` **可能创建尸体而让 `entities_` 迭代失效**（第三次"收集后处理"）。
13. **⚠ `ZMHIT` 用整数值而摔落伤害用名字** —— 一处日志**退化**（同一枚举两种打印）。
14. **三个 `freeEntity` 调用点都在镜像之后**，而 **"一个裸句柄携带 0 而 `freeEntity` 在它上面故障关闭"`**（第二次确认代际必要性）。
15. **`zmRetainedCorpses_` 的 100 秒 / 32 上限**，而 **`freeEntity` 成功才 erase**（第三次"成功后才改状态"）。

## 十、未闭合点

- `SvPmFlagsMatchEndFrozen` 的位值（是否 0x800）。
- `zombieReviveHeld` / `factoryTravelHeld` 的判定。
- `retainZombieCorpse` 的 32 上限实现。
- `UserCmdButtonActivate` 的位。
- `playerState.otherFlags = 1u << 12` 的语义。
- `sv_snapshot_mp.cpp` 19600 行之后未读取（27,016 行，进度 73%）。
