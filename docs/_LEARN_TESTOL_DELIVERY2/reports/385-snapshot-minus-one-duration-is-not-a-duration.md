# 385 · **"而一个 `-1` 的时长【不是一个时长】"** —— `max(-1,1)` 塌缩成一毫秒、`msSinceDeath=50`、`G_SpawnPlayerClone` 的 `64/8` vs `19/18`

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 25600–26000 行。

## 二、**`deathAnimMs = -1` 的完整事故**（本组最重要的一段）

### 2.1 那段

```php
// AND A DURATION OF -1 IS NOT A DURATION. The native death event
// returns -1 on every death on this build -- `deathAnimMs=-1` in
// every one of the respawn diagnostics -- and std::max(-1, 1)
// collapses to a ONE MILLISECOND hold, so the timed respawn fires
// on the very next frame, 50 ms after death. Measured:
//     respawn client=1 via=timed msSinceDeath=50 deathAnimMs=-1
//
// That is what made death instant, and it silently OVERRODE the
// gametype. dm.lua asks for `method:respawn(player, 3000)` in the
// death callback, which runs a frame later -- by which time the
// player has already respawned and deathState is gone, so
// requestPlayerRespawn refuses it and the log has been saying so on
// every death since:
//     player respawn deferred  respawn requires a dead Playing player
//
// So arm the engine hold ONLY when the event returned a real
// duration. With no duration there is nothing to hold FOR, and the
// respawn belongs to the gametype, which is where CoD puts it and
// which is the only thing here that has ever named a number.
// Retail's own death-to-respawn gap in the dm demo is 1500..2200 ms
// across all 24 deaths; dm.lua asks 3000.
if (*animationDuration > 0 && !zombieRevivalActive_ && !roundBasedDeathHold_)
    mutation.client.respawnTime = snapshot_.serverTime + *animationDuration;
```

### 2.2 二十层

```text
1. **而一个 `-1` 的时长【不是一个时长】**
2. ⇒ **原生死亡事件在这个 build 上【每一次死亡】都返回 `-1`**
3. ⇒ **（每一次重生诊断里的 `deathAnimMs=-1`）**
4. ⇒ **而 `std::max(-1, 1)` 【塌缩成一个一毫秒的保持】**
5. ⇒ **所以那个计时重生【在紧接着的下一帧】触发**
6. ⇒ **死后 `50ms`**
7. ⇒ **实测：`respawn client=1 via=timed msSinceDeath=50 deathAnimMs=-1`**
8. ⇒ **那就是让死亡【瞬间】的东西**
9. ⇒ **而它【静默地覆盖】了 gametype**
10. ⇒ **`dm.lua` 在死亡回调里请求 `method:respawn(player, 3000)`**
11. ⇒ **而那个回调【晚一帧】运行**
12. ⇒ **到那时玩家【已经重生了】而 `deathState` 没了**
13. ⇒ **所以 `requestPlayerRespawn` 【拒绝】它**
14. ⇒ **而日志【从那时起】每一次死亡都在说**：
      · **`player respawn deferred  respawn requires a dead Playing player`**
15. ⇒ **所以【只在事件返回一个真时长时】武装引擎保持**
16. ⇒ **没有时长就没有东西可保持**
17. ⇒ **而重生属于【gametype】**
18. ⇒ **那是 CoD 把它放的地方**
19. ⇒ **而那也是这里【唯一命名过一个数字**】的东西**
20. ⇒ **零售自己在 dm demo 里的死到重生间隔是 `1500..2200ms`（跨全部 24 次死亡）**
21. ⇒ **而 `dm.lua` 请求 `3000`**
```

### 2.3 ⭐⭐ **"`max(-1, 1)` 塌缩成一毫秒"**

**✅ 这是本文件里**最纯粹的一个"哨兵被当成值"的实例**。**

**⇒ 三层**：

```text
`-1` 是"没有动画"的哨兵
⇒ **而 `max(-1, 1)` 把它变成一个【合法的 1 毫秒】**
⇒ **⇒ 于是"没有动画"变成"1 毫秒的动画"**
```

**✅ 与 §361 的"2047/2046/0xFFFFFF 是全一哨兵，用零代替不是更小的值"**完全同族（**第七次"哨兵"）。**

**⚠ 而"一个 `-1` 的时长不是一个时长"⇒ **一个极清晰的陈述**。**

**✅ 与 §370 的"一个有时存活的值是别的东西拥有的"**同族（**第六次"值语义"）。**

### 2.4 而**"静默地覆盖了 gametype"**

**✅ 与 §367 的"两条路径必须一致"**相反**（这里是**两条冲突**）。**

**⇒ 三层**：

```text
引擎路径：`respawnTime = now + (-1 → 1)` ⇒ **50ms 后重生**
脚本路径：`dm.lua` 请求 `3000ms` ⇒ **被拒（已重生）**
⇒ **引擎【赢了】而脚本【静默失败】**
```

**✅ 一个**极隐蔽的竞态**。**

**⚠ 而"日志从那时起每一次死亡都在说"⇒ **日志【一直在说】，而没人在读**。**

**✅ 与 §372 的"日志只在前 40 帧"**不同**（这里**一直在说**）。**

**⇒ 所以**一个持续的、正确的、被忽视的日志**。**

**✅ 与 §355 的"从这个日志引用的每一个位置都是加载之前的"**同族（**第七次"日志被忽视"）。**

### 2.5 而**"零售 `1500..2200ms`，`dm.lua` 请求 `3000`"**

**✅ 与 §384 的 `73/163`**第十四次大规模统计。

**⚠ 而"`3000` 与 `1500..2200` 不同"⇒ **所以脚本与零售不同**。**

**⚠ 而"零售跨全部 24 次死亡"⇒ **一个完整的样本**。**

**✅ 与 §362 的 `145`、§375 的 `294`**同族。

### 2.6 而**`roundBasedDeathHold_` 的第二理由**

```php
// OLMOD(sd-round-death-hold): the second reason to leave respawnTime
// unset. A round-based mode has nothing to hold FOR either -- one
// life per round means the round, not the animation, decides when
// this player comes back, and beginNextRound() already does it by
// bumping spawnSequence for every Active client. Say so once per
// death, otherwise "the hold was suppressed" and "the hold never
// armed" look identical in the log.
if (roundBasedDeathHold_ && *animationDuration > 0 && !zombieRevivalActive_) {
    OlMod::RuntimeLog::write(..., "SD death-hold client=... animMs=... -- no engine timed respawn armed; the round owns it");
}
```

**⇒ 八层**：

```text
1. **第二个不设 `respawnTime` 的理由**
2. ⇒ **一个回合制模式【也没有东西可保持】**
3. ⇒ **一回合一条命意味着【回合】而不是动画决定这个玩家何时回来**
4. ⇒ **而 `beginNextRound()` 已经通过给每一个 Active 客户端 bump `spawnSequence` 做到了**
5. ⇒ **每次死亡说一次**
6. ⇒ **否则"保持被压制"与"保持从未武装"在日志里【看起来一样】**
7. ⇒ **所以显式记一行**
```

**✅ 与 §346 的"一个标签不能把两个答案塌缩成一个词"**完全同族（**第三次）。**

**⇒ **一个精确的可观测性关切**。**

**✅ 与 §368 的"三层命名失败项"**同族（**第六次）。**

## 三、**`G_SpawnPlayerClone` 的完整位移常数记录**（本组第二重要）

### 3.1 那段

```php
// DISABLED - this crashed the client on the first kill, and the
// reason is that a corpse is NOT an ordinary pool entity.
//
// IW3's G_SpawnPlayerClone does not call G_Spawn at all:
//     e = &level.gentities[level.currentPlayerClone + 64];
//     level.currentPlayerClone = (level.currentPlayerClone + 1) % 8;
//     flags = e->s.lerp.eFlags & 2 ^ 2;
// Corpses live in a fixed, dedicated, contiguous, round-robin
// entity-number range, and eFlags bit 0x2 INVERTS every time a slot
// is reused. The OLfinal demo agrees independently: its corpses are
// entity numbers 19..36, contiguous, exactly 18 of them. Spawning
// one at 396 out of the dynamic FIFO puts it outside whatever
// fixed-size corpse array the client indexes by slot.
//
// Re-enable only once BOTH are read out of THIS build - the base
// and the count are per-build constants and neither IW3's 64/8 nor
// OLfinal's 19/18 may be ported.
```

### 3.2 十六层

```text
1. **【已禁用】—— 它在第一次击杀时【崩掉了客户端】**
2. ⇒ **理由是【一具尸体不是一个普通的池实体】**
3. ⇒ **IW3 的 `G_SpawnPlayerClone` 【根本不调 `G_Spawn`】**：
     · `e = &level.gentities[level.currentPlayerClone + 64]`
     · `level.currentPlayerClone = (level.currentPlayerClone + 1) % 8`
     · `flags = e->s.lerp.eFlags & 2 ^ 2`
4. ⇒ **尸体住在一个【固定、专用、连续、轮转】的实体号范围里**
5. ⇒ **而 `eFlags` 的 bit `0x2` 【在每次一个槽被复用时反转】**
6. ⇒ **OLfinal demo 【独立地】同意**：它的尸体是**实体号 `19..36`**
7. ⇒ **连续、恰好 18 个**
8. ⇒ **在动态 FIFO 里生成一个在 396 的**
9. ⇒ **把它放到客户端【按槽索引的固定大小尸体数组】之外**
10. ⇒ **重新启用条件**：**基址与计数都必须【从【这个】build 读出】**
11. ⇒ **而 IW3 的 `64/8` 与 OLfinal 的 `19/18` 【都不能移植】**
```

### 3.3 ⭐⭐ **"`64/8` vs `19/18` —— 都不能移植"**

**✅ 与 §360 的"索引→偏移相同而编解码器不同"**同族（**第六次"逐 build 常数"）。**

**⇒ 三层**：

```text
IW3      基址 64 / 计数 8
OLfinal  基址 19 / 计数 18
⇒ **两套常数完全不同**
⇒ **所以都不能移植**
```

**✅ 与 §380 的"`IW4 shuffleKillStreaksFILO` 与 `CODOL key4` 不同"**同族（**第三次"逐 build 差异"）。**

**⚠ 而"`19..36` 连续恰好 18 个"⇒ **一个完整的实测范围**。**

**✅ 与 §362 的"`eFlags` 位 0x2 的反转"**完全闭合 ✓

**⇒ **第三次确认 `0x2` 的反转。**

### 3.4 而**"基址与计数是逐 build 常数"**

**✅ 与 §369 的"`SvPmFlagsMatchEndFrozen` 是 `0x800`"**不同（那是**一个位**）。**

**⇒ 这里**两个常数**（基址 + 计数）。

**⚠ 而"`19..36`"⇒ **基址 19、计数 18**。**

**✅ 与 §363 的"`FirstPlayerCorpseEntityNum + PlayerCorpseRingSize`"**完全一致 ✓

**⇒ **第三次确认那个环。**

### 3.5 而**"DISABLED... Re-enabled"的两个注释块**

**⇒ 四层**：

```text
第一个注释块：DISABLED，理由 1（不是普通池实体）
第二个注释块：Re-enabled，理由 2（"不能渲染尸体"是【过度声称】）
```

**✅ 而第二个的完整论证：**

```php
// Re-enabled. The claim that this build cannot render a corpse was
// an OVERCLAIM: what was actually shown is that three encodings of a
// 952-byte memcpy are absent, not that no populator exists - an
// inlined SSE or rep-movsd copy would not have matched any of them.
// The dm demo shows retail leaving an animated body on a corpse
// entity while the player entity goes quiet, so the corpse IS the
// mechanism and this follows its measured shape.
```

**⇒ 十一层**：

```text
1. **重新启用**
2. ⇒ **"这个 build 不能渲染一具尸体"的声称是一个【过度声称】**
3. ⇒ **实际显示的是：`952` 字节 `memcpy` 的【三种编码】都缺席**
4. ⇒ **而不是【没有一个填充器】** ——
5. ⇒ **一个内联的 SSE 或 `rep movsd` 拷贝【不会匹配它们中的任何一个】**
6. ⇒ **dm demo 显示零售在一具尸体实体上留下一个动画的身体**
7. ⇒ **而玩家实体【变得安静】**
8. ⇒ **所以尸体【是】那个机制**
9. ⇒ **而这跟随它的【测量形状】**
```

**✅ ⭐⭐ **"一个内联的 SSE 或 `rep movsd` 拷贝不会匹配任何三种编码"** —— 一个**经典的定向负面的失败**。**

**⇒ 三层**：

```text
扫描"三种已知的 memcpy 编码" ⇒ 零命中
⇒ **而结论是"没有拷贝"**
⇒ **而实际上是一个内联的 SIMD 拷贝**
```

**✅ 与 §372 的"`[reg+12Ch]` 的扫描返回空但不是证据"**完全同族（**第二次"扫描方法错误导致假负面"）。**

**⇒ **第六次"定向负面的失败"。**

**⚠ 而"过度声称"⇒ **一个自我纠正**。**

**✅ 与 §370 的"从反编译读出的常数是一个假设"**同族（**第五次自我纠正）。**

## 四、**`finishPlayerDamageBatch` 的提交与回滚**（本组第三重要）

### 4.1 提交

```php
for (std::size_t index = 0; index < payloads.size(); ++index) {
    auto &mutation = pending[index];
    mutation.target->client = std::move(mutation.client);
    mutation.target->entity = std::move(mutation.entity);
}
rebuildCollisionView();
const auto committedDeath = std::ranges::any_of(pending,
    [](const PendingDamageMutation &m) { return m.lethal; });
```

### 4.2 回滚

```php
if (committedDeath && nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) {
    // OLMOD(player-die-native-transaction): a lethal transition
    // changes corpse bounds, contents and entityState together. Do not
    // publish source death or player_killed when the real CODOL
    // gentity/CM mirror rejected that candidate. Rebuild once more
    // after restoring source ownership so the synchronizer can recover
    // the prior live-player image.
    for (std::size_t index = 0; index < payloads.size(); ++index) {
        auto &mutation = pending[index];
        mutation.target->client = std::move(mutation.originalClient);
        mutation.target->entity = std::move(mutation.originalEntity);
    }
    rebuildCollisionView();
    return FinishPlayerDamageResult::NativeMirrorUnavailable;
}
```

### 4.3 九层

```text
1. **提交：【全部目标】一次 `move`**
2. ⇒ **然后 `rebuildCollisionView()`**
3. ⇒ **然后判断 `committedDeath`**
4. ⇒ **只在【有一次致命】且镜像未同步时回滚**
5. ⇒ **理由：一次致命转换【同时】改变尸体 bounds、contents 与 `entityState`**
6. ⇒ **不要在真实 CODOL gentity/CM 镜像【拒绝那个候选】时发布源死亡或 `player_killed`**
7. ⇒ **恢复源所有权后【再重建一次】**
8. ⇒ **所以同步器可以【恢复先前的活玩家图像】**
9. ⇒ **返回 `NativeMirrorUnavailable`**
```

**✅ 与 §376 的"七处 swap 的逆序回滚"**同族（**第九次事务性）。**

**⚠ 而"只在致命时回滚"⇒ **所以非致命伤害的镜像失败【不回滚】。**

**⇒ 三层**：

```text
非致命：镜像失败 ⇒ **不回滚**（因为 damage 已经在 playerState 里，而它不需要新尸体）
致命：  镜像失败 ⇒ **回滚**（因为需要新尸体而镜像拒绝了它）
```

**✅ 一个**精确的条件**。**

### 4.4 而**"一个失败的后续目标曾给一个更早的目标留下一个再生窗口"**

```php
// A failed later target used to leave a regen window and pain/death
// vocal behind for an earlier target, despite restoring its health.
// Keep these side owners behind the same successful publication gate.
```

**⇒ 五层**：

```text
1. **一个失败的【后续】目标**
2. ⇒ **曾给一个【更早】的目标留下一个再生窗口与疼痛/死亡呼叫**
3. ⇒ **尽管恢复了它的血量**
4. ⇒ **所以把这些【旁路所有者】保持在【同一个成功发布门】之后**
5. ⇒ **一个"部分成功"的经典 bug**
```

**✅ 与 §376 的"部分插入 ⇒ 全回滚"**同族（**第二次"部分成功"）。**

## 五、**六个侧效应的完整顺序**（本组第四重要）

```php
for (index) {
    // 1. 僵尸受伤记录（近战 + actor）
    if (mutation.damage && !lethal && zombieRevivalEnabled_ && melee && attacker) { ... }
    // 2. 倒地
    if (mutation.downed) { zombieDowned_[...] = ...; weaponGrants_ = {}; sendZombieDownedPresentation; healthRegen_.erase; noclipHoldUntil_.erase; }
    // 3. 取消作为复活血量的所有
    for (auto &[victim, down] : zombieDowned_) if (down.reviver == clientNum) down.cancel();
    // 4. 致命 ⇒ 清再生 + 清涂装
    if (mutation.lethal) { healthRegen_.erase; clearPlayerPaint; }
    // 5. 非致命 ⇒ 开再生窗口 + 可能涂装
    else if (!downed && damage) { healthRegen_[...] = {...}; if (paintsTarget) markPlayerPainted; }
    // 6. 呼叫
    stagePlayerVocal(clientNum, lethal ? DeathVoice : PainVoice, lethal);
}
```

### 5.1 六层的顺序

```text
1. **受伤记录**（只近战且 actor）
2. ⇒ **倒地**（含五个子动作）
3. ⇒ **取消作为复活者**
4. ⇒ **致命 ⇒ 清再生/涂装**
5. ⇒ **非致命 ⇒ 开再生窗口/涂装**
6. ⇒ **呼叫**（致命与疼痛）
```

**✅ 与 §349 的"`beginFrame` 的十二步"**同族（**第三次"精确的顺序"）。**

**⚠ 而 ④⑤ 是**互斥的**（`if (lethal) ... else if`）。**

**✅ 一个**正确的分支**。

### 5.2 而**"倒地的五个子动作"**

```text
zombieDowned_[clientNum] = {...}          记录
zombieDownedInventories_ = ...            背包
weaponGrants_[clientNum] = {}             清授予
sendZombieDownedPresentation(true, ...)   表现
healthRegen_.erase                       清再生
noclipHoldUntil_.erase                    清 noclip
```

**⇒ 六项（含 `zombieDowned_` 记录）。**

**✅ 与 §380 的"`noclipHoldUntil_.erase`"**配合。**

**⚠ 而"倒地时清 noclip"⇒ **一个精确的清理**。**

**✅ 与 §380 的"不是活着意味着保持结束"**完全一致 ✓

**⇒ **第三次确认那个规则。**

### 5.3 而**呼叫的六项**

```cpp
stagePlayerVocal(clientNum,
    mutation.lethal
        ? ((clientNum & 1u) ? PlayerVocalDeathVoice2 : PlayerVocalDeathVoice1)
        : ((clientNum & 1u) ? PlayerVocalPainVoice2 : PlayerVocalPainVoice1),
    mutation.lethal);
```

**⇒ 四层**：

```text
1. **两种声音**（死亡 / 疼痛）
2. ⇒ **各两个变体**（1 / 2）
3. ⇒ **按 `clientNum & 1` 选**
4. ⇒ **`force = lethal`**（死亡强制，疼痛受冷却）
```

**✅ 与 §349 的"`stagePlayerVocal` 的 500ms 冷却"**完全闭合 ✓

**⇒ **第二次确认那个设计**（`force` 绕过冷却）。

## 六、`weaponNameForDeath` 的三级回退

```cpp
const std::array owners{ payload.attackerEntityNum, payload.inflictorEntityNum, std::optional{ payload.targetClientNum } };
```

**⇒ 三层**：

```text
① 攻击者的装备
② inflictor 的装备
③ **目标自己的装备**
```

**✅ 与 §384 七的 `deathYaw` 的三级回退**完全同构**。**

**⚠ 而 ③ 用**目标自己**⇒ **自杀时用一个合法的名字**。**

**✅ 与 §368 的"`MOD_FALLING` 的自我归因"**完全一致 ✓

**⇒ **第二次确认那个"自我归因"**。

## 七、`setPlayerWeapons` 的**十项验证**

```cpp
if (!weaponDefinitionResolver_ || !primary || !secondary ||
    primary == secondary ||
    primary >= WeaponConfigStringCount || secondary >= WeaponConfigStringCount ||
    supplemental >= WeaponConfigStringCount ||
    (supplemental != 0 && (supplemental == primary || supplemental == secondary)) ||
    (selected != 0 && selected != primary && selected != secondary && selected != supplemental))
    return false;
```

**⇒ 十层**：

```text
① 解析器存在
② primary 非零
③ secondary 非零
④ **primary != secondary**
⑤ primary < 1700
⑥ secondary < 1700
⑦ supplemental < 1700
⑧ **若 supplemental 非零 ⇒ 不能等于 primary 或 secondary**
⑨ **若 selected 非零 ⇒ 必须是三个之一**
```

**✅ 与 §374 的"`primary != secondary` 是 `SV_IsResolvedLoadoutValid` 的结尾"**完全闭合 ✓

**⇒ **第三次确认那个不变式。**

**⚠ 而"四把武器的唯一性检查"⇒ **一个组合约束**。**

**✅ 与 §366 的"四种共享索引组合"**同族。

## 八、关键结论

1. **⭐⭐ "而一个 `-1` 的时长【不是一个时长】"`** —— 原生死亡事件在**每一次死亡**都返回 `-1`，而 **`std::max(-1, 1)` 塌缩成一个【一毫秒】的保持**。
2. **"所以那个计时重生在紧接着的下一帧触发，死后 `50ms`；实测 `respawn client=1 via=timed msSinceDeath=50 deathAnimMs=-1`"`**。
3. **"那就是让死亡瞬间的东西，而它【静默地覆盖】了 gametype"`** —— `dm.lua` 请求 `3000ms` 而**回调晚一帧 ⇒ 玩家已重生 ⇒ 被拒**。
4. **"日志从那时起每一次死亡都在说 `player respawn deferred  respawn requires a dead Playing player`"`** —— **一个持续的、正确的、被忽视的日志**（第七次"日志被忽视"）。
5. **"零售自己的死到重生间隔是 `1500..2200ms` 跨全部 `24` 次死亡，而 `dm.lua` 请求 `3000`"`** —— 第十四次大规模统计，而**脚本与零售不同**。
6. **⭐ "只在事件返回一个真时长时武装引擎保持 —— 没有时长就没有东西可保持，而重生属于 gametype"`**。
7. **`roundBasedDeathHold_` 的第二理由**（回合制模式**也没有东西可保持**）—— 而 **"否则『保持被压制』与『保持从未武装』在日志里看起来一样"`**（第三次"一个标签不能塌缩两个答案"）。
8. **⭐⭐ `G_SpawnPlayerClone` 的完整三行**（`&level.gentities[clone + 64]` / `% 8` / `eFlags & 2 ^ 2`）。
9. **⭐ "IW3 的 `64/8` 与 OLfinal 的 `19/18` 【都不能移植】"`** —— 第三次"逐 build 常数"。
10. **"OLfinal demo 独立地同意：它的尸体是实体号 `19..36`，连续，恰好 18 个"`** —— 第三次确认那个环。
11. **⭐⭐ "『这个 build 不能渲染一具尸体』是一个【过度声称】：实际显示的是 `952` 字节 `memcpy` 的三种编码都缺席，而【一个内联的 SSE 或 `rep movsd` 拷贝不会匹配它们中任何一个】"`** —— **第二次"扫描方法错误导致假负面"**（第六次"定向负面的失败"）。
12. **`finishPlayerDamageBatch` 的提交与回滚**，而**只在致命时回滚**（因为非致命的 damage 已在 playerState 里而它不需要新尸体）。
13. **"一个失败的【后续】目标曾给一个【更早】的目标留下一个再生窗口与呼叫"`** —— 第二次"部分成功"。
14. **六个侧效应的精确顺序**（受伤记录 → 倒地六动作 → 取消复活者 → 致命清 / 非致命开 → 呼叫）。
15. **"倒地时清 `noclipHoldUntil_`"`** —— 第三次确认"不是活着意味着保持结束"。
16. **呼叫的四种**（死亡/疼痛 × 变体 1/2，按 `clientNum & 1`）而 **`force = lethal`**（第二次确认 `stagePlayerVocal` 的设计）。
17. **`weaponNameForDeath` 的三级回退**（attacker → inflictor → **目标自己**）与 §384 的 `deathYaw` **同构** —— 第二次确认"自我归因"。
18. **`setPlayerWeapons` 的十项验证**含 **`primary != secondary`** —— 第三次确认那个不变式。

## 九、未闭合点

- 为什么原生死亡事件每次都返回 `-1`。
- `952` 字节的 `memcpy` 是哪三个编码。
- `DeadPlayerTraceBounds` / `DeadPlayerCollisionContents` 的值。
- `PlayerVocalDeathVoice1/2` / `PlayerVocalPainVoice1/2` 的值。
- `sendZombieDownedPresentation` 的实现。
- `sv_snapshot_mp.cpp` 26000 行之后未读取（27,016 行，进度 96%）。
