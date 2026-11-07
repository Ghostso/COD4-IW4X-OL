# 387 · **"一个尸体只是表现"** —— 两套 `lerpData0058` 编码、`ActorCorpseRingSize` 的"最旧优先"、六个事件载体的统一五步

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 26500–27000 行。

## 二、**两套 `lerpData0058` 编码**（本组最重要的一段）

### 2.1 `retainZombieCorpse`

```cpp
n.eType = EntityTypeActorCorpse;
n.lerpData0058 = (static_cast<std::uint32_t>(n.actorModelIndex) << 16) | 0x300u | corpseSlot;
n.scriptMoverBrushModelIndex = n.actorModelIndex;
```

### 2.2 `convertActorToCorpse`

```cpp
network.eType = EntityTypeActorCorpse;
network.lerpData0058 = ActorCorpseLerpPrefix | corpseSlot;
```

### 2.3 两套编码的对比

```text
retainZombieCorpse   [modelIndex:16][0x03:8][slot:8]    ⇒ 0xFF-style？
convertActorToCorpse [ActorCorpseLerpPrefix:~低5][slot:低5]
```

**⚠ 而 §344 的 `validActorCorpseEntity` 有**两套**：**

```cpp
cyborgActorsEnabled:
    (lerpData0058 & 0xFF) < ActorCorpseRingSize &&
    ((lerpData0058 >> 8) & 0xFF) == 3 &&
    (lerpData0058 >> 16) == scriptMoverBrushModelIndex

else:
    (lerpData0058 & ~0x1F) == ActorCorpseLerpPrefix &&
    (lerpData0058 & 0x1F) < ActorCorpseRingSize
```

**⇒ 五层**：

```text
1. **`retainZombieCorpse` 用【赛博格编码】**：
     · 低 8 位 = 槽
     · 次 8 位 = `3`
     · 高 16 位 = `modelIndex`
2. ⇒ **而 `scriptMoverBrushModelIndex = modelIndex`** ⇒ **与高 16 位一致** ✓
3. ⇒ **`convertActorToCorpse` 用【普通编码】**：
     · `ActorCorpseLerpPrefix | 槽`
4. ⇒ **所以两个函数用两套**
5. ⇒ **而 §344 的验证器分别接受**
```

**✅ ⭐ **完全闭合：§344 的两套验证器对应这两个函数。**

**⇒ 三层**：

```text
§344 的验证器有两支
§387 的生成器有两个
⇒ **一对一**
```

**✅ 一个**极清晰的对应**。**

**⚠ 而 `retainZombieCorpse` 的编码**把 `modelIndex` 放高 16 位**。**

**⇒ 所以**一个 16 位的模型索引**。**

**✅ 与 §342 的"字段 20 是 16 位角色物品 id"**同族（**第二次"16 位 id"）。**

### 2.4 而 `convertActorToCorpse` 的 `startRagdoll`

```php
// CODREF(demo 362950..366350): all nine cargo-blast ragdolls clear
// entityState modelindex while their actor-corpse ring slot retains
// the client DObj. Ordinary weapon corpses keep model 259.
network.scriptMoverBrushModelIndex = startRagdoll ? 0 : (uint16)agent->fields[ModelField];
...
network.positionTrajectoryType = startRagdoll ? SvCorpseRagdollTrajectoryType : 0;
network.angleTrajectoryType = startRagdoll ? SvCorpseRagdollAngleTrajectoryType : 1;
```

### 2.5 九层

```text
1. **全部九个货舱爆炸布娃娃【清 `entityState` 的 modelindex】**
2. ⇒ **而它们的 actor-corpse 环槽【保留客户端的 DObj】**
3. ⇒ **普通的武器尸体保留模型 `259`**
4. ⇒ **所以 `startRagdoll` 决定模型索引**
5. ⇒ **而两个轨迹类型也一起变**
6. ⇒ **`positionTrajectoryType`：ragdoll ⇒ 某个常量 / 否则 `0`**
7. ⇒ **`angleTrajectoryType`：ragdoll ⇒ 某个常量 / 否则 `1`**
8. ⇒ **所以四处分叉**
```

**✅ 与 §363 的"`SvCorpseRagdollTrajectoryType`"**同族（**第二次确认那两个常量）。**

**⚠ 而"普通的武器尸体保留 259"⇒ **一个具体的模型号**。**

**✅ 与 §386 的"actor 的 modelIndex 来自 `agent.fields[ModelField]`"**配合。

## 三、**`ActorCorpseRingSize` 的"最旧优先"**（本组第二重要）

### 3.1 那段

```php
// Separate native32-slot corpse presentation ownership (530AF0).
// FIFO/100s are reconstructed policy, not recovered server predicates.
std::erase_if(zmRetainedCorpses_, [&](const auto &c) { return !entityPool_->resolve(c.handle); });
std::array<bool, ActorCorpseRingSize> occupied{};
for (const auto &c : zmRetainedCorpses_) occupied[c.slot] = true;
auto victim = zmRetainedCorpses_.end();
std::uint8_t corpseSlot{};
if (zmRetainedCorpses_.size() == ActorCorpseRingSize) {
    victim = std::max_element(zmRetainedCorpses_.begin(), zmRetainedCorpses_.end(),
        [&](const auto &a, const auto &b) {
            return snapshot_.serverTime - a.diedAt < snapshot_.serverTime - b.diedAt;
        });
    corpseSlot = victim->slot;
}
else while (occupied[corpseSlot]) ++corpseSlot;
```

### 3.2 十一层

```text
1. **分开的 `native32` 槽尸体表现所有权（`530AF0`）**
2. ⇒ **FIFO/100 秒是【重建的策略】，不是恢复的服务端谓词**
3. ⇒ **先清掉失效句柄**
4. ⇒ **然后标出已占的槽**
5. ⇒ **若【满】⇒ 用 `max_element` 找"最旧"**
6. ⇒ **而比较式是 `(now - a.diedAt) < (now - b.diedAt)`** ⇒ **即 `a.diedAt > b.diedAt`**
7. ⇒ **所以 `max_element` 找的是【最小的 `diedAt`】= 最旧**
8. ⇒ **取它的槽**
9. ⇒ **否则从槽 0 找第一个空的**
10. ⇒ **所以满了就【替换最旧】（FIFO）**
```

### 3.3 ⭐ **`max_element` + "找一个最小值"**

**✅ 一个**双重否定的精妙手法**。**

**⇒ 三层**：

```text
要"最旧的" ⇒ 要"最小的 diedAt"
⇒ `max_element` 配一个反转比较
⇒ **所以是 max_element 但语义是 min**
```

**⚠ 一处**容易读错的地方**。**

**✅ 与 §353 的"`zmDamageRoll` 的拒绝采样"**同族（**第二次"反向思维"）。**

### 3.4 而**"FIFO/100 秒是重建的策略"**

**✅ 与 §362 的"100 秒 / 32 上限"**完全一致 ✓

**⇒ **第二次确认。而这里说"32"是 `native32`。**

**⇒ 三层**：

```text
`ActorCorpseRingSize` = **32**
⇒ 与 §349 的 `zmRetainedCorpses_` 的"最多 32"**一致** ✓
```

**⚠ 而"`native32`-slot"⇒ **所以 32 是客户端侧的槽数**。**

**✅ 与 §344 的"`ActorCorpseRingSize`"**配合。**

### 3.5 而**两个函数的"环槽"不同**

```text
retainZombieCorpse   ⇒ 用 `zmRetainedCorpses_` 的槽（32 个）
convertActorToCorpse ⇒ 用 `nextActorCorpseSlot_ % ActorCorpseRingSize`（轮转）
```

**⇒ 三层**：

```text
retain    ⇒ **查表 + 最旧替换**
convert   ⇒ **简单轮转**
⇒ **两种分配**
```

**⚠ 所以**两个不同的分配策略**。**

**✅ 而两个都用同一个 `ActorCorpseRingSize`。**

## 四、**"一个尸体只是表现"**（本组第三重要）

### 4.1 那段

```php
std::erase_if(campaignAgents_, [&](const SvAgentState &candidate) {
    return candidate.agentNum == agent->agentNum;
});
// A corpse is presentation-only. Leaving the live actor's damage row
// behind lets a later blast select the corpse and can dispatch a
// second entity_killed callback against an already released agent.
entityDamageStates_.erase(actor.entityNum);
entityDamageHandlers_.erase(actor.entityNum);
```

### 4.2 七层

```text
1. **从 `campaignAgents_` 删**
2. ⇒ **"一个尸体只是表现"**
3. ⇒ **留下活 actor 的伤害行让一次后续爆炸【选中尸体】**
4. ⇒ **并能对一个【已释放的 actor】派发【第二次 `entity_killed` 回调】**
5. ⇒ **所以 `entityDamageStates_` 与 `entityDamageHandlers_` 都清**
```

**✅ 与 §355 的"`entityDamageStates_` 保留一个终态条目"**不同**（那里**保留**，这里**删**）。**

**⇒ 三层**：

```text
§355  `reset()` 里的 `entityDamageStates_.clear()` ⇒ **保留终态**
§387  `convertActorToCorpse` ⇒ **删除**
```

**⚠ 所以**两种策略**。**

**⇒ 而 §387 的理由"防第二次 `entity_killed`"⇒ **一个具体的双重派发**。**

**✅ 与 §354 的"`killed` 事件排队到下一帧"**配合。

## 五、**六个事件载体的统一五步**（本组第四重要）

### 5.1 六个载体

```text
spawnSoundAliasEvent      ⇒ `EntityTypeSoundAlias` / `SoundAliasAsMaster`
spawnFireMagicEvent       ⇒ `EntityTypeFireMagic`
spawnExploderEvent        ⇒ `EntityTypeExploder`
spawnWorldFxEvent         ⇒ `EntityTypePlayFx`
spawnWorldFxOnTagEvent    ⇒ `EntityTypePlayFxOnTag`
```

**⇒ 五个函数（`SoundAlias` 一个处理两种）。**

### 5.2 统一的五步

```cpp
// ① 前置验证
if (!entityPool_ || !eventParameter || eventParameter >= LIMIT || !finite(origin)) return false;
// ② 分配
const auto handle = spawnEntity(); if (!handle) return false;
// ③ 找槽
const auto slot = entities_.find(handle->entityNum); if (slot == end) { freeEntity(*handle); return false; }
// ④ 填字段
entity.networkState.eType = ...; origin; eventParm; clientNum = EntityNumNone; currentOrigin; gameplayActive = true; collisionLinked = false;
// ⑤ 验证 + 标记 + 失败回滚
if (!validSimpleEventEntity(...) || !entityPool_->markFreeAfterEvent(*handle, serverTime, EntityNumWorld)) {
    static_cast<void>(freeEntity(*handle));
    return false;
}
```

**⇒ 五步在五个函数里【完全同构】。**

**✅ 与 §337 的"两个几乎相同的函数"**第六次。**

**⚠ 而差异只在：**

```text
① 位置：
     · SoundAlias  ⇒ `eventParameter < SoundAliasEventParameterLimit`
     · WorldFx     ⇒ `eventParameter < EffectConfigStringCount`
     · FireMagic   ⇒ 只 `!eventParameter`
     · Exploder    ⇒ 只 `!eventParameter`
② 字段：
     · PlayFx      ⇒ 还有 `angles`
     · PlayFxOnTag ⇒ `eventParm = effect | (tag << 9)` 且 `otherEntityNum = target`
     · FireMagic   ⇒ `otherEntityNum = EntityNumNone`
③ `markFreeAfterEvent` 的 `sourceEntityNum`：
     · **全部 `EntityNumWorld`**
```

**✅ 与 §347 的"`effect | (bone << 9)`"**第二次确认。

**⚠ 而 `PlayFxOnTag` 的 `tagIndex == 0xFF` 拒绝** ⇒ **与 §353 的 `bone == 255` 一致**。

**✅ **第三次确认"255 = 无骨骼"。**

## 六、**`queueScriptModelSoundEvent` / `FxEvent` 的 `& 3`**

```cpp
state.events[state.eventSequence & 3u] = { EventSoundAlias, alias };
state.eventSequence = (uint8)(state.eventSequence + 1u);
...
state.events[state.eventSequence & 3u] = { EventPlayFxOnTag,
    (int32)(effect | ((uint32)bone << 9u)) };
state.eventSequence = (uint8)(state.eventSequence + 1u);
```

**⇒ 三层**：

```text
1. **四槽环（`& 3`）**
2. ⇒ **写当前 sequence 命名的槽，然后推进**
3. ⇒ **`uint8` 回绕**
```

**✅ 与 §349 的"四槽环"**第六次确认。**

**⇒ **第五次确认"写当前 sequence 命名的槽然后推进"（§349 的规则）。**

### 6.1 而 `queueScriptModelFxEvent` 的额外检查

```cpp
if (it == entities_.end() || it->second.networkState.eType != EntityTypeScriptMover ||
    !it->second.networkState.modelIndex || !it->second.gameplayActive) return false;
```

**⇒ `!modelIndex` 是额外的**（因为 `FxOnTag` 需要一个模型）。**

**✅ 一个**正确的额外前置**。

### 6.2 而 `queueActorPresentationEvent` 的**两支**

```php
if (entity->second.mapClassName == "zombie_actor") {
    // CODREF(actor_head_attachment): Factory's writeChangedActor emits
    // +0xB4 from actorField00B4, unlike the campaign DTO. Advance exactly
    // the counter consumed by CG_CheckEvents; retain it for corpse transfer.
    network.events[network.actorField00B4 & 3u] = event;
    network.actorField00B4 = (uint8)(network.actorField00B4 + 1u);
    network.eventSequence = network.actorField00B4;
    return true;
}
```

**⇒ 五层**：

```text
1. **僵尸 ⇒ 用 `actorField00B4`（`+0xB4`）作游标**
2. ⇒ **而不是 `eventSequence`**
3. ⇒ **"正好推进 `CG_CheckEvents` 消费的那个计数器"**
4. ⇒ **"为尸体转移保留它"**
5. ⇒ **而两支都写到四槽环**
```

**✅ 与 §336 的"`+0xB4`"**配合。**

**⚠ 而"两支"⇒ **所以 campaign actor 与 zombie actor 有不同的游标字段**。**

**✅ 与 §344 的"`actorField00B4` 是事件计数器"**完全一致 ✓

**⇒ **第二次确认。**

### 6.3 而 **`event.event == 41`（`EV_FIRE_WEAPON`）的躯干**

```php
// CODREF(Wetwork demo ET_ACTOR + agentState): EV_FIRE_WEAPON is
// paired with a stable torso pose selected by the actor's carried
// weapon model. The exact observed pairs are 463->1192 (RPG),
// 466->1195 (UMP), and 479..482->1208..1211 (AK variants).
// Retail leaves this pose asserted between shots; it returns to
// zero when the actor state is released.
if (const auto agent = actorAgentState(actor))
    network.torsoAnim = actorTorsoAnimation(*agent);
```

**⇒ 七层**：

```text
1. **`EV_FIRE_WEAPON`（41）与一个稳定的躯干姿态配对**
2. ⇒ **由 actor 携带的武器模型选**
3. ⇒ **精确的观测对**：
     · `463 → 1192`（RPG）
     · `466 → 1195`（UMP）
     · `479..482 → 1208..1211`（AK 变体）
4. ⇒ **零售在射击之间【保持断言这个姿态】**
5. ⇒ **它在 actor 状态被释放时回到零**
6. ⇒ **所以只在这个事件上重算 `torsoAnim`**
```

**✅ 与 §370 的"十次按键十条命令"**同族（**第五次"精确的观测对"）。**

**⚠ 而"三个武器族、三组映射"⇒ **一个具体的表**。**

**✅ 与 §386 的 `actorTorsoAnimation(agent)`**配合。**

## 七、`spawnWorldFxOnTagEvent` 的 `eventParm` 编码

```cpp
eventEntity.networkState.eventParm =
    effectIndex | (static_cast<std::uint32_t>(tagIndex) << 9u);
eventEntity.networkState.otherEntityNum = (std::uint16_t)target.entityNum;
```

**⇒ 三层**：

```text
1. **`effectIndex | (tagIndex << 9)`**
2. ⇒ **`effectIndex` 占低 9 位**
3. ⇒ **`tagIndex` 占高位**
```

**✅ 与 §353 的"`effect | (bone << 9)`"**第三次确认。**

**⇒ 而注释说"`CG_PlayFxOnTag` 解码 `effect | (bone << 9)`；不像 `EV_PLAY_FX` 它不消费事件角度"。**

**✅ 一个**精确的行为差异**。

## 八、关键结论

1. **⭐⭐ 两套 `lerpData0058` 编码与 §344 的两套验证器【一对一】`** —— `retainZombieCorpse` 用赛博格编码（`[model:16][3:8][slot:8]`）而 `convertActorToCorpse` 用普通编码（`ActorCorpseLerpPrefix | slot`）。
2. **"`scriptMoverBrushModelIndex = modelIndex` 与高 16 位一致"`** —— 一个自洽的不变式。
3. **⭐ `startRagdoll` 的四处同时分叉**（模型索引 / `positionTrajectoryType` / `angleTrajectoryType`），而 **"全部九个货舱爆炸布娃娃清 `entitystate modelindex` 而它们的环槽保留客户端 DObj；普通武器尸体保留模型 259"`**。
4. **⭐⭐ `ActorCorpseRingSize` 的"最旧优先"用 `max_element` 配一个反转比较** —— 一个双重否定的精妙手法。
5. **"FIFO/100 秒是【重建的策略】，不是恢复的服务端谓词"`** —— 而 **`ActorCorpseRingSize = 32` 与 `native32`-slot 的尸体表现所有权一致**。
6. **两个函数的两个不同分配策略**：`retainZombieCorpse` 查表 + 最旧替换 / `convertActorToCorpse` 简单轮转。
7. **⭐⭐ "一个尸体只是表现：留下活 actor 的伤害行让一次后续爆炸【选中尸体】并能对一个【已释放的 actor】派发【第二次 `entity_killed` 回调】"`** —— 与 §355 的"保留终态"**相反的策略**。
8. **⭐ 六个事件载体的统一五步**（验证 / 分配 / 找槽 / 填字段 / 验证+标记+回滚）—— 第六次"几乎相同的函数"。
9. **三个位置上限**（`SoundAliasEventParameterLimit` / `EffectConfigStringCount` / 只 `!eventParameter`）。
10. **`PlayFxOnTag` 的 `tagIndex == 0xFF` 拒绝** ⇒ **第三次确认"255 = 无骨骼"**。
11. **`markFreeAfterEvent` 的 `sourceEntityNum` 全部 `EntityNumWorld`**。
12. **⭐ 四槽环（`& 3`）第六次确认**，而 **"写当前 sequence 命名的槽然后推进"第五次确认**。
13. **`queueScriptModelFxEvent` 的额外 `!modelIndex` 前置**（`FxOnTag` 需要模型）。
14. **⭐⭐ `queueActorPresentationEvent` 的两支**：**僵尸用 `actorField00B4`（`+0xB4`）作游标而 campaign actor 用 `eventSequence`** —— 而 **"正好推进 `CG_CheckEvents` 消费的那个计数器；为尸体转移保留它"`**（第二次确认）。
15. **⭐ `EV_FIRE_WEAPON`（41）的三组精确观测对**（`463→1192` RPG / `466→1195` UMP / `479..482→1208..1211` AK）—— 而 **"零售在射击之间保持断言这个姿态，在 actor 状态被释放时回到零"`**。
16. **`eventParm = effectIndex | (tagIndex << 9)` 第三次确认**，而 **"`CG_PlayFxOnTag` 不像 `EV_PLAY_FX` 它不消费事件角度"`**。

## 九、未闭合点

- `ActorCorpseLerpPrefix` 与 `ActorCorpseRingSize` 的确切值。
- `SvCorpseRagdollTrajectoryType` / `SvCorpseRagdollAngleTrajectoryType` 的值。
- `actorTorsoAnimation` 的完整映射表。
- `EventSoundAlias` / `EventPlayFxOnTag` 的事件 id。
- `FireMagic` / `Exploder` 的 eType 数值。
- `sv_snapshot_mp.cpp` 27000 行之后未读取（27,016 行，进度 99.9%）。
