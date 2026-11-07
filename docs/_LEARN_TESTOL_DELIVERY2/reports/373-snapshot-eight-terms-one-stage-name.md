# 373 · **"八个项，一个阶段名"** —— `converted_state_mismatch` 的八项具名分歧、事件环合并的"只取原生的增量"、`antiLagHistory_` 的 400ms 回溯

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 20800–21200 行。

## 二、**八项 `converted_state_mismatch`**（本组第二重要）

### 2.1 那段

```php
// EIGHT TERMS, ONE STAGE NAME. converted_state_mismatch says the native
// conversion disagreed with the playerState it was built from, which is exactly
// the finding -- but not WHICH field, and the eight are not equally likely. Say
// it once per distinct disagreement, with both sides.
```

### 2.2 五层

```text
1. **八个项，一个阶段名**
2. ⇒ **`converted_state_mismatch` 说原生转换与它建自的 `playerState` 不一致**
3. ⇒ **那正是那个发现**
4. ⇒ **但【不是哪一个字段】，而那八个【不是同等可能】**
5. ⇒ **每个不同的分歧说一次，带【两边】的值**
```

### 2.3 而八项的完整清单

```text
① commandTime          vs currentUserCmd.commandTime
② entity.clientNum     vs playerState.clientNum
③ convertedEntityState.number       vs playerState.clientNum
④ convertedEntityState.clientNum    vs playerState.clientNum
⑤ convertedEntityState.eType        vs EntityTypePlayer（+ otherFlags + pmType）
⑥ convertedEntityState.weaponAssetIndex vs currentWeaponAssetIndex
⑦ convertedEntityState.origin       vs playerState.origin
⑧ convertedEntityState.groundEntityNum vs playerState.groundEntityNum
```

**✅ 八项。**

**⚠ 而 ②③④ 三项都是 `clientNum` 类的。**

**⇒ 所以实际是**六个语义**：**

```text
时间 / clientNum（三个形式）/ eType / 武器 / 原点 / 地面
```

**✅ 与 §346 的"七十五项合取"**不同**（这是**八项且具名**）。**

**⇒ **第四次"具名而不是笼统"**。

### 2.4 而 ⑤ 的**"`ET_INVISIBLE` 是一个正确答案"**

```php
// eType comes out of a single `test eax, 1800h` on the second dword of
// the protected value at ps+0x10, so print what this server believes
// those flags and its own liveness are. ET_INVISIBLE is a CORRECT answer
// for a player who is not playing; it is only a mismatch if otherFlags
// says otherwise.
```

**⇒ 七层**：

```text
1. **`eType` 从 `ps+0x10` 的那个受保护值的【第二个 dword】上一条 `test eax, 1800h` 得出**
2. ⇒ **所以打印这个服务器相信那些标志与它自己的存活状态是什么**
3. ⇒ **`ET_INVISIBLE` 对一个不在玩的玩家是一个【正确答案】**
4. ⇒ **只有当 `otherFlags` 说别的时候它才是一个不一致**
5. ⇒ **所以日志带 `otherFlags=` 与 `pmType=`**
```

**✅ 与 §371 的"`ps+0x10` 被 pmove 覆写 ⇒ `0x1800` 决定 eType"**完全闭合 ✓

**⇒ **第二次确认 `0x1800` 与 `ps+0x10`。**

**⚠ 而"第二个 dword"⇒ 所以 `ps+0x14`。**

**✅ 一个**精确的偏移**。

## 三、**`disagree` 的去重**

```cpp
const auto disagree = [](const char *const term, const std::string &produced, const std::string &expected) {
    static std::string reported;
    auto details = std::string(term) + " converted=" + produced + " playerState=" + expected;
    if (details != reported) { reported = details; write(...); }
    return true;
};
```

**⇒ 四层**：

```text
1. **一个 `static std::string reported`**（全局）
2. ⇒ **所以只在【变化】时写**
3. ⇒ **而返回 `true`**（让 `||` 链继续）
4. ⇒ **所以第一次不匹配就短路**
```

**⚠ 而 `static` 是**全局的**（跨客户端）。**

**⇒ 与 §372 的"`static` 跨客户端污染"**同族（**第四次）。**

**⚠ 而这里的目的**可能是有意的**（只关心第一个）。**

**但**多个客户端的不同分歧会互相覆盖。**

**✅ 与 §346 的 `psDomainBad`**完全同构。

## 四、**事件环的合并**（本组最重要的一段）

### 4.1 那段

```php
// MERGE THE NATIVE RING INTO THE SERVER-OWNED ONE. See SvPlayerEventRing.
//
// The projection never carries a fire event -- BG_PlayerStateToEntityState
// does not copy server-only ids into es.events, correctly -- so the fire
// event is ADDED where the shot is accepted, and this ring is what makes
// those additions survive alongside the native footsteps and jumps.
{
    auto &eventRing = playerEventRings_[entity.networkState.clientNum];
    const auto publishedSequenceBefore = eventRing.sequence;
    const auto nativeSequence = convertedEntityState.eventSequence;
    if (!eventRing.seeded) {
        eventRing.seeded = true;
        eventRing.sequence = nativeSequence;
        eventRing.ring = convertedEntityState.events;
    } else {
        // Only the events the native ring GAINED since last frame, and
        // never more than the four it can hold.
        auto gained = (uint8)(nativeSequence - eventRing.lastNativeSequence);
        if (gained > eventRing.ring.size()) gained = (uint8)eventRing.ring.size();
        for (uint8 back = gained; back >= 1; --back) {
            const auto nativeSlot = (size_t)((uint8)(nativeSequence - back)) & 3u;
            eventRing.ring[eventRing.sequence & 3u] = convertedEntityState.events[nativeSlot];
            eventRing.sequence = (uint8)(eventRing.sequence + 1);
        }
    }
    eventRing.lastNativeSequence = nativeSequence;
    entity.networkState.events = eventRing.ring;
    entity.networkState.eventSequence = eventRing.sequence;
}
```

### 4.2 十四层

```text
1. **把原生环合并进服务器拥有的那个**
2. ⇒ **投影【从不】携带一个开火事件**
3. ⇒ **`BG_PlayerStateToEntityState` 【不】把服务端专属 id 拷进 `es.events`，正确地**
4. ⇒ **所以开火事件在【射击被接受的地方】被 ADDED**
5. ⇒ **而这个环是让那些添加【与原生脚步/跳跃一起存活】的东西**
6. ⇒ **未 seeded ⇒ 直接取原生环**
7. ⇒ **否则只取原生环【自上一帧起获得】的事件**
8. ⇒ **而【从不超过它能持有的四个】**
9. ⇒ **`gained = nativeSequence - lastNativeSequence`（uint8 模算术）**
10. ⇒ **`if (gained > 4) gained = 4`**
11. ⇒ **从 `back = gained` 递减到 1**
12. ⇒ **`nativeSlot = (nativeSequence - back) & 3`**
13. ⇒ **`eventRing.ring[eventRing.sequence & 3] = ...`**
14. ⇒ **而 sequence 递增**
```

### 4.3 ⭐ **"投影从不携带一个开火事件，正确地"**

**✅ 与 §372 的"不要过滤 playerstate 环"**完全闭合 ✓

**⇒ 三层**：

```text
1. `BG_PlayerStateToEntityState` 【正确地】**不**拷服务端专属 id
2. ⇒ **所以开火事件在实体环里【缺】**
3. ⇒ **所以服务器必须【ADD】它**
```

**✅ **第三次确认那个两流分离。**

### 4.4 而**`gained` 的 uint8 模算术**

**⇒ 三层**：

```text
1. `nativeSequence` 与 `lastNativeSequence` 都是 `uint8`
2. ⇒ **所以差是模 256**
3. ⇒ **若原生环回绕 ⇒ 差仍然正确**
```

**✅ 与 §342 的"`writeEntityEventSequence` 的模算术"**同族（**第二次）。**

**⚠ 而注释说"从不携带一个开火事件"⇒ **所以火事件由服务器加**。**

**⚠ 而 §342 的 `isOwnerPredictedEvent` 压制 28 个 ⇒ **压制与添加是两件事**。**

**✅ 一个**精细的分工**。

### 4.5 而 **`ring-advance` 的"DELTAS 7/9/10/13"**

```php
// WHAT IS FILLING THE RING. sect.191w measured eventSequence
// DELTAS of 7, 9, 10 and 13 on the wire where a healthy entity
// moves 1-2, and the ring holds four slots -- so the client replays
// nine events out of four and everything queued at that instant is
// undispatchable. This prints the advance and the ids that caused
// it, because the wire can only show the four that survived.
```

### 4.6 九层

```text
1. **什么在填这个环**
2. ⇒ **sect.191w 在线上测到 `eventSequence` 的 DELTA 是 `7`、`9`、`10`、`13`**
3. ⇒ **而一个健康的实体走 `1-2`**
4. ⇒ **而环持有【四个槽】**
5. ⇒ **所以客户端【从四个里重放九个事件】**
6. ⇒ **而那个瞬间排队的一切都是【不可派发的】**
7. ⇒ **这打印 advance 与造成它的 id**
8. ⇒ **因为【线上只能显示存活下来的那四个】**
```

**✅ 与 §372 的"三到四次重复"**完全同族（**第五次"事件重复"**）。

**⇒ 三次不同原因：**

```text
§342  uint8 截断 ⇒ 256 的倍数回跳
§372  游标窗口开着 ⇒ 一到两个快照
§373  **advance 7-13 而环只有四槽** ⇒ 九个事件从四个里重放
```

**✅ **三个根因一个症状。**

**⚠ 而"不可派发的"⇒ **所以事件丢失。****

## 五、**`player-entity` 的"第三方读实体不读 playerState"**（本组第三重要）

### 5.1 那段

```php
// WHAT THE OTHER PLAYER'S ENTITY ACTUALLY CARRIES, once a second.
//
// A player reports weapon world models not showing on OTHER players.
// The weapon index itself is not in doubt -- retail's ET_PLAYER field 18
// is `weapon | (weapon << 16)` (measured: 1270 and 1284 in the spec dm
// demo, via Tools/demo-re/mine-entities.py) and packEntityWeapon writes
// exactly that shape -- so what has to be seen is every OTHER entity
// field the client could hang a model off, per client, at the same
// instant. Third person reads the ENTITY, not the playerState, and this
// server has never printed the entity side of a player at all.
```

### 5.2 十二层

```text
1. **另一个玩家的【实体】实际携带什么，每秒一次**
2. ⇒ **一个玩家报告武器世界模型【不在其他玩家身上显示】**
3. ⇒ **武器索引本身不是疑问**
4. ⇒ **零售的 `ET_PLAYER` 字段 18 是 `weapon | (weapon << 16)`**
5. ⇒ **（测得：spec dm demo 里的 `1270` 与 `1284`，经 `Tools/demo-re/mine-entities.py`）**
6. ⇒ **而 `packEntityWeapon` 写出【恰好那个形状】**
7. ⇒ **所以必须被看见的是客户端能挂一个模型的【每一个其他实体字段】**
8. ⇒ **按客户端，在同一瞬间**
9. ⇒ **第三人称读【实体】不是 `playerState`**
10. ⇒ **而这个服务器【从未】打印过一个玩家的实体侧**
```

### 5.3 ⭐ **"第三方读实体不读 playerState"**

**✅ 与 §345 的"`sub_53DF40` 从 `entityState+0xA0` 挑 clientInfo"**同族（**第三次"分层的读取源"）。**

**⇒ 三层**：

```text
第一人称  ⇒ 读 `playerState`（自己的武器/视角）
第三人称  ⇒ 读 `entityState`（别人的模型）
```

**✅ **一个精确的架构分层**。**

**⚠ 而"从未打印过实体侧"⇒ **一个可观测性缺口**。**

**✅ 与 §355 的"从这个日志引用的每一个位置都是加载之前的"**同族（**第五次"日志覆盖不全"）。**

### 5.4 而 `weapon | (weapon << 16)`

**✅ 与 §342 的 `packEntityWeapon` **完全一致 ✓**

**⇒ **第二次确认那个打包**。

**⚠ 而"测得 `1270` 与 `1284`"⇒ **两个具体的武器号**。**

**✅ 而 `1270 | (1270 << 16) = 0x04F604F6`。**

**✅ **一个可验证的等式。**

## 六、**`antiLagHistory_` 的 400ms 回溯**（本组第四重要）

### 6.1 那段

```php
// CODREF(g_antilag): CoD4 rewinds other live players to the firing
// command's server time for bullet and melee traces, then restores the
// current world immediately. Its history window is 400 ms and it does
// not rewind a command newer than one server frame.
//
// Keep this transaction on local collision/native-mirror copies. The
// authoritative source entities stay current, and spawnGeneration
// prevents a late packet from reaching through a death into an older
// life.
const auto rewindAttack = std::ranges::any_of(eventView, SV_IsRewindableAttackEvent);
```

### 6.2 九层

```text
1. **`CoD4` 把其他活玩家回溯到【开火命令的服务器时间】**
2. ⇒ **用于子弹与近战 trace，然后【立刻】恢复当前世界**
3. ⇒ **它的历史窗口是 `400ms`**
4. ⇒ **而它【不】回溯一条比一个服务器帧更新的命令**
5. ⇒ **把这个事务保持在【本地碰撞/原生镜像副本】上**
6. ⇒ **权威源实体【保持当前】**
7. ⇒ **而 `spawnGeneration` 防止一个迟到包穿过一次死亡到达一个更早的生命**
8. ⇒ **只在有一个可回溯攻击事件时**
9. ⇒ **而 `SV_IsRewindableAttackEvent` 判定**
```

**✅ 与 §355 的"`spawnGeneration` 防跨死亡"**第三次确认。**

**⚠ 而"保持在本地副本上"⇒ **所以权威源不被修改。****

**✅ 与 §364 的"staged-then-commit"**同族（**第八次事务性）。

### 6.3 而**"不回溯比一个服务器帧更新的命令"**

**⇒ 三层**：

```text
1. 一个命令若比一个服务器帧更新 ⇒ **不回溯**
2. ⇒ **因为那样的回溯没有意义**（延迟太小）
3. ⇒ **而副作用会大于收益**
```

**✅ 一个**明确的边界**。**

### 6.4 而**"然后立刻恢复当前世界"**

**⇒ 三层**：

```text
1. 回溯 ⇒ 做 trace ⇒ **恢复**
2. ⇒ **所以回溯是【一个短暂的窗口】**
3. ⇒ **不是持续状态**
```

**✅ 与 §369 的"命令被中性化而不是跳过 pmove"**不同**（那是**保持**，这是**短暂**）。**

## 七、**`damageablePlayers` 的四项条件**

```cpp
if (damageClient->gameplayState == ClientGameplayState::Playing &&
    damageClient->playerState.health > 0 &&
    damageEntity->networkState.number == clientNum &&
    damageEntity->clientNum == clientNum)
{
    damageablePlayers.push_back({ .entityNum = damageEntity->networkState.number, .clientNum = clientNum });
}
```

**⇒ 四层**：

```text
① **Playing**
② **活着**
③ **`entityState.number == clientNum`**
④ **`entity.clientNum == clientNum`**
```

**✅ 与 §345 的"`clientNum` 必须无条件断言"**配合。**

**⇒ **第三次确认那个连接。**

**⚠ 而 ③④ 是两个不同的字段但都要求等于 `clientNum`。**

**⇒ 所以**一个"身份一致"的双重检查**。**

**✅ 与 §368 的"三层命名失败项"**不同**（这是**静默过滤**）。**

**⚠ 一处**可以加日志的地方**。**

## 八、`damageableEntities` 的五项

```cpp
if (damageEntity != entities_.end() && lifetime &&
    damageState.canTakeDamage && damageState.health > 0)
{
    damageableEntities.push_back({
        .entityNum = entityNum,
        .generation = lifetime->generation,
        .kind = damageState.kind,
        .usesWeaponHitLocationMultipliers = zmActorNamespaceEnabled_ &&
            damageEntity->second.mapClassName == "zombie_actor",
    });
}
```

**⇒ 四层前置 + 四个字段。**

**✅ 而 `usesWeaponHitLocationMultipliers` 只在 `zmActorNamespaceEnabled_` 且 `mapClassName == "zombie_actor"`。**

**⇒ 三层**：

```text
1. **只有僵尸用武器命中位置倍率**
2. ⇒ **而 `mapClassName` 是字符串检查**（§353 第二次）
3. ⇒ **所以"僵尸"是【一个类名】而不是一个 eType**
```

**✅ 与 §353 的"`mapClassName == "zombie_actor"`"**第二次。**

## 九、关键结论

1. **八项 `converted_state_mismatch`**，而**每一项带两边的值**（第四次"具名而不是笼统"）。
2. **八项实际是六个语义**（`clientNum` 有三个形式）。
3. **⭐ "`eType` 从 `ps+0x10` 的受保护值的第二个 dword 上一条 `test eax, 1800h` 得出"`** —— 第二次确认 `0x1800` 与 `ps+0x10`。
4. **"`ET_INVISIBLE` 对一个不在玩的玩家是一个【正确答案】；只有当 `otherFlags` 说别的时候它才是一个不一致"`**。
5. **`disagree` 的 `static std::string` 是全局的** —— 第四次 `static` 跨客户端污染（与 §346 的 `psDomainBad` 同构）。
6. **⭐ 事件环合并的"只取原生环自上一帧起的增量，且从不超过四个"`**。
7. **"投影【从不】携带一个开火事件 —— `BG_PlayerStateToEntityState` 正确地不拷服务端专属 id ⇒ 所以开火事件必须在射击被接受的地方 ADDED"`** —— 第三次确认两流分离。
8. **`gained` 的 `uint8` 模算术**（第二次）。
9. **⭐ 三个事件重复的根因**：`uint8` 截断（§342）/ 游标窗口（§372）/ **advance `7-13` 而环只有四槽（§373）**。
10. **"客户端从四个里重放九个事件 ⇒ 那个瞬间排队的一切都不可派发 ⇒ 而线上只能显示存活下来的那四个"`**。
11. **⭐ "第三方读【实体】不读 `playerState`"`** —— 第三次"分层的读取源"；而**"这个服务器从未打印过一个玩家的实体侧"**（第五次日志覆盖不全）。
12. **"零售的 `ET_PLAYER` 字段 18 是 `weapon | (weapon << 16)`（测得 1270 与 1284）而 `packEntityWeapon` 写出恰好那个形状"`** —— 第二次确认。
13. **⭐ `antiLagHistory_` 的 400ms 回溯** —— CoD4 的 `g_antilag`，**不回溯比一个服务器帧更新的命令**，**然后立刻恢复**。
14. **"保持在本地碰撞/原生镜像副本上 ⇒ 权威源实体保持当前"`** —— 第八次事务性。
15. **"`spawnGeneration` 防止一个迟到包穿过一次死亡到达一个更早的生命"`** —— 第三次确认。
16. **`damageablePlayers` 的四项条件**含**两个 `== clientNum` 的双重身份检查**。
17. **`damageableEntities` 的 `usesWeaponHitLocationMultipliers` 只在 `zombie_actor` 类名上为真** —— 第二次确认"僵尸是类名不是 eType"。

## 十、未闭合点

- `SV_IsRewindableAttackEvent` 的事件 id 集。
- `antiLagHistory_.originAt` 的插值方式。
- `PS+0x10` 的"受保护值"与 `0x1800` 的完整判定。
- `playerEventRings_` 与 `convertedEntityState.events` 的双环关系。
- `SvCollisionBodyRole` 的完整枚举。
- `sv_snapshot_mp.cpp` 21200 行之后未读取（27,016 行，进度 78%）。
