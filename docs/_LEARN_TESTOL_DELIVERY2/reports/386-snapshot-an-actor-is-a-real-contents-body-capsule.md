# 386 · **"一个 actor 是一个真正的 `CONTENTS_BODY` 胶囊"** —— 只发 `ET_ACTOR` + `agentState` 造一个"令人信服的人形"而子弹永不能选中它、`ground_tilt_controller` 的字段 231

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 26000–26500 行。

## 二、**"一个令人信服的人形"但子弹永不能选中它**（本组最重要的一段）

### 2.1 那段

```php
// CODREF(G_SpawnActor / Agent_Spawn): an actor is a real CONTENTS_BODY
// capsule.  Publishing only ET_ACTOR + agentState makes a convincing
// figure, but the retained bullet trace can never select it and no
// entity-damage payload can be produced.  Use the same standing body
// dimensions and encoded solid as the player path until the actor
// stance fields recover a smaller native bound.
const auto solid = SV_EncodePlayerSolid(StandingPlayerTraceBounds, PlayerCollisionContents);
if (!solid) return std::nullopt;
...
const auto collision = SV_LinkActorCollisionEntity(
    handle->entityNum, std::nullopt, origin, angles,
    StandingPlayerTraceBounds, PlayerCollisionContents);
if (!collision) { freeEntity(*handle); return std::nullopt; }
```

### 2.2 十二层

```text
1. **一个 actor 是一个真正的 `CONTENTS_BODY` 胶囊**
2. ⇒ **只发布 `ET_ACTOR` + `agentState` 造一个【令人信服的人形】**
3. ⇒ **但保留的子弹 trace 【永远不能】选中它**
4. ⇒ **而没有实体伤害载荷能被产生**
5. ⇒ **用与玩家路径【相同的站立身体尺寸与编码 solid】**
6. ⇒ **直到 actor 的站姿字段恢复一个【更小的原生 bounds】**
7. ⇒ **所以 `SV_EncodePlayerSolid(StandingPlayerTraceBounds, PlayerCollisionContents)`**
8. ⇒ **而 `SV_LinkActorCollisionEntity(..., StandingPlayerTraceBounds, PlayerCollisionContents)`**
9. ⇒ **两者都必须成功，否则拒绝**
```

### 2.3 ⭐⭐ **"一个令人信服的人形"**

**✅ 与 §350 的"接收了、存储了、而从未被画"**相反**（这里**被画了**但**不能被击中**）。**

**⇒ 三层**：

```text
发布 `ET_ACTOR` + `agentState` ⇒ **客户端画一个完整的人形**
⇒ **而服务端的碰撞世界【没有它】**
⇒ **⇒ 子弹穿过它**
```

**✅ 与 §361 的"连上并且可被射击（12.161）"**完全同族（**第二次"画了但不可击中"）。**

**⇒ 而 §361 是**玩家**，这里**actor**。**

**⚠ 所以**同一个教训两次**：**

```text
§361  玩家实体  ⇒ `collisionLinked = false` ⇒ **子弹永不能到达**
§386  actor     ⇒ 只发状态不连碰撞 ⇒ **子弹永不能选中**
```

**✅ 与 §350 的"ET_GENERAL 的处理器没有画笔分支"**同族（**第三次"画与碰撞的分离"）。**

### 2.4 而**"直到 actor 的站姿字段恢复一个更小的原生 bounds"**

**⇒ 三层**：

```text
1. **临时用玩家尺寸**
2. ⇒ **因为 actor 的站姿 bounds 未恢复**
3. ⇒ **所以一个蹲着的 actor 会有玩家的全高碰撞体**
```

**✅ 一个**诚实的临时方案**。**

**⚠ 而"更小的原生 bounds"⇒ **所以 actor 的实际尺寸更小**。**

**✅ 与 §344 的"`validActorEntity` 拒绝俯仰/翻滚"**配合。**

## 三、**actor 的六个原生 union 字**（本组第二重要）

### 3.1 那段

```php
// Exact first-frame Wetwork actor image. These are native union words,
// not cosmetic defaults: partBits[0] builds the DObj, and both 2047
// values are "none" sentinels. Sending zero selects real entity zero.
network.eventParm = EntityNumWorld; // +0x8C loopSound = 2046
network.movementDir = 0x00FFFFFF; // +0x5C actor-owned word
network.groundEntityNum = EntityNumNone;
network.otherEntityNum = EntityNumNone; // +0x84 attackerEntityNum
network.torsoAnim = actorTorsoAnimation(agent);
network.scriptMoverAnimationIndex = 1; // +0xE8 partBits[0]
network.scriptMoverField00E4 = 0;
network.scriptMoverBrushModelIndex = (uint16)agent.fields[SvAgentState::ModelField];
network.lerpData0058 = 0xFF000000u | agent.agentNum;
```

### 3.2 十四层

```text
1. **精确的第一帧 Wetwork actor 图像**
2. ⇒ **这些是【原生 union 字】，不是装饰性默认**
3. ⇒ **`partBits[0]` 建 DObj**
4. ⇒ **而两个 `2047` 值是"无"哨兵**
5. ⇒ **发零选【真正的实体零】**
6. ⇒ **`eventParm = EntityNumWorld`（`+0x8C` 的 loopSound = `2046`）**
7. ⇒ **`movementDir = 0x00FFFFFF`（`+0x5C` 的 actor 拥有字）**
8. ⇒ **`groundEntityNum = EntityNumNone`（`2047`）**
9. ⇒ **`otherEntityNum = EntityNumNone`（`+0x84` 的 attackerEntityNum）**
10. ⇒ **`torsoAnim = actorTorsoAnimation(agent)`**
11. ⇒ **`scriptMoverAnimationIndex = 1`（`+0xE8` 的 partBits[0]）**
12. ⇒ **`scriptMoverBrushModelIndex = agent.fields[ModelField]`**
13. ⇒ **`lerpData0058 = 0xFF000000 | agentNum`**
14. ⇒ **"低字是稳定的 join key；高字是 actor 拥有的状态"**
```

### 3.3 ⭐ **一层成员的九个不同语义**

**⇒ 三层**：

```text
`eventParm`            ⇒ **loopSound**（`+0x8C`，2046）
`movementDir`          ⇒ **actor 拥有的 0xFFFFFF 字**（`+0x5C`）
`groundEntityNum`      ⇒ 真正的 ground（2047）
`otherEntityNum`       ⇒ **attackerEntityNum**（`+0x84`）
`torsoAnim`            ⇒ torso 动画
`scriptMoverAnimationIndex` ⇒ **partBits[0]**（`+0xE8`）
`scriptMoverField00E4` ⇒ 零
`scriptMoverBrushModelIndex` ⇒ **模型索引**
`lerpData0058`         ⇒ **`0xFF000000 | agentNum`**（join key）
```

**✅ 与 §344 的"`groundEntityNum` 在布告上是字段 13"**同族（**第十次"一成员多语义"）。**

**⚠ 而"`movementDir = 0x00FFFFFF`"⇒ 与 §350 的"`solid == 0xFFFFFF`"**同值不同义**。**

**⇒ 三层**：

```text
§350  `solid == 0xFFFFFF` ⇒ **走画笔分支**
§386  `movementDir = 0xFFFFFF` ⇒ **actor 拥有的一个字**
```

**✅ **一个极容易混淆的地方**。**

**⚠ 而"两个 `2047` 哨兵"⇒ **`groundEntityNum` 与 `otherEntityNum`**。**

**✅ 与 §345 的"`EntityNumNone = 2047`"**第五次确认。

### 3.4 而 **`lerpData0058 = 0xFF000000 | agentNum`**

**✅ 与 §361 的"`actorField0058 = 0xFF000300 | agentSlot`"**完全同族（**第二次"`0xFF` 前缀 + 一个字节域"）。**

**⇒ 三层**：

```text
§361  `0xFF0003NN` ⇒ **记录槽 + 指针索引**
§386  `0xFF0000NN` ⇒ **agent 号**
```

**⚠ 而 §361 说 `0xFF0000NN` 是【错的】（因为字节 1 是零）。**

**⇒ 所以 §386 这里**仍是旧的 `0xFF000000` 形式**。**

**⚠ 一处**潜在的同一错误**。**

**✅ 而注释说"低字是稳定的 join key"⇒ 所以它**只用于 join**。**

**⚠ 所以**可能无害**（因为它不参与渲染）。**

**✅ 与 §361 的"`+0x59` 指针索引"**配合。

### 3.5 而 **`scriptMoverAnimationIndex = 1` 是 `partBits[0]`**

**✅ 与 §345 的"`ActorPartBits0Field` 是 32 位"**不同**。**

**⚠ 所以**`scriptMoverAnimationIndex` 在 actor 上是 `partBits[0]`**。**

**⇒ **第四次"一成员多语义"（本段内）。**

## 四、**`ground_tilt_controller` 的字段 231**（本组第三重要）

### 4.1 那段

```php
// CODREF(Wetwork demo 368600..440250): playerState field 231 selects
// entity 100, a model-less ET_SCRIPTMOVER whose apos trajectory carries
// the freighter's roll.  COD4 names the script boundary
// playersetgroundreferenceent and copies the selected entity's angles
// into the player's ground tilt; BO2 and Ghosts retain the same method.
// CODOL's wire contract is the direct entity reference measured above,
// so keep the carrier model-less rather than inventing scenery for it.
```

### 4.2 十二层

```text
1. **Wetwork demo `368600..440250`：`playerState` 字段 231 选中实体 100**
2. ⇒ **一个【无模型的 `ET_SCRIPTMOVER`】** ⇒ **它的 `apos` 轨迹携带货轮的滚转**
3. ⇒ **COD4 把那个脚本边界命名为 `playersetgroundreferenceent`**
4. ⇒ **并把选中实体的角度【复制进玩家的地面倾角】**
5. ⇒ **BO2 与 Ghosts 保留同样的方法**
6. ⇒ **CODOL 的线契约是【上面测到的直接实体引用】**
7. ⇒ **所以让那个载体【无模型】而不是为它发明布景**
8. ⇒ **而 `linkEntityNum` 是它在这次移植里的转移名**
9. ⇒ **但它的观测到的 Wetwork 职责 + COD4/BO2/Ghosts 的同一脚本方法**
10. ⇒ **把这个用途识别为玩家的【地面参考】**
11. ⇒ **保留字段名直到原生偏移 `0x248` 的其它消费者都被恢复**
12. ⇒ **所以先叫 `linkEntityNum`**
```

### 4.3 ⭐ **"保留字段名直到其它消费者被恢复"**

**✅ 与 §360 的"字段 29 什么都不发因为未知"**不同**（这里**用一个语义明确的名字但保留原名**）。**

**⇒ 三层**：

```text
观测：字段 231 在 368600 从 2047 → 100
⇒ **而 COD4/BO2/Ghosts 都叫它 `playersetgroundreferenceent`**
⇒ **所以语义明确**
⇒ **但原生偏移 `0x248` 可能有别的消费者**
⇒ **所以名字保守**
```

**✅ 一个**精确的命名纪律**。**

**⚠ 而"字段 231"⇒ **`playerState` 有至少 231 个字段**。**

**✅ 与 §370 的"`playerState` netfield 表 0..245"**完全一致 ✓

**⇒ **第二次确认 246 项。**

## 五、**`spawnActor` 的完整事务**（本组第四重要）

### 5.1 三阶段的回滚

```php
// 阶段 1：验证
if (!validAgentState(agent) || !finite(origin) || !finite(angles) ||
    (existing != end && existing->agentNum == agent.agentNum)) return nullopt;

// 阶段 2：分配 + 链接
const auto handle = spawnEntity();
const auto collision = SV_LinkActorCollisionEntity(...);
if (!collision) { freeEntity(*handle); return nullopt; }

// 阶段 3：填字段 + 加入 campaignAgents_
campaignAgents_.insert(existing, joinedAgent);
rebuildCollisionView();
if (synchronizer && !synchronized) {
    std::erase_if(campaignAgents_, [&](auto &c) { return c.agentNum == joinedAgent.agentNum; });
    entities_.erase(handle->entityNum);
    entityPool_->free(*handle, snapshot_.serverTime);
    rebuildCollisionView();
    return nullopt;
}
```

**⇒ 七层**：

```text
1. **验证在分配之前**
2. ⇒ **链接失败 ⇒ `freeEntity`**
3. ⇒ **然后填入 + 插入表**
4. ⇒ **然后 `rebuildCollisionView`**
5. ⇒ **镜像失败 ⇒ 三重回滚**：
     · **从 `campaignAgents_` 删**
     · **从 `entities_` 删**
     · **`entityPool_->free`**
6. ⇒ **再 `rebuildCollisionView`**
7. ⇒ **所以是【三阶段 + 三重回滚】**
```

**✅ 与 §376 的"七处 swap"**同族（**第十次事务性）。**

**⚠ 而"三重回滚"⇒ **一个精确的逆序**。**

**✅ 与 §352 的"事务性"**完全一致 ✓

### 5.2 而**"void `freeEntity` 也可能失败"**

**⇒ 三层**：

```text
1. `freeEntity` 返回 bool
2. ⇒ **而这里 `static_cast<void>` 忽略它**
3. ⇒ **所以一个 free 失败会留下一个泄漏的实体**
```

**⚠ 一处**潜在的泄漏**。**

**✅ 与 §363 的"`rollbackFree` 失败则抛异常"**对比（那里**处理了**）。**

**⚠ **两种风格**。**

## 六、`setActorAgentState` 的四项验证

```cpp
if (entity == end ||
    entity->second.networkState.eType != EntityTypeActor ||
    (entity->second.networkState.lerpData0058 & 0xFFFFu) != agent.agentNum ||
    agent.fields[SvAgentState::EntityNumField] != actor.entityNum)
{
    return false;
}
```

**⇒ 五层**：

```text
① 实体存在
② eType 是 actor
③ **`lerpData0058` 的低 16 位 == `agent.agentNum`**
④ **`agent.fields[EntityNumField] == actor.entityNum`**
⑤ **而 `campaignAgents_` 里有它**
```

**✅ 与 §386 三.4 的"低字是稳定的 join key"**完全闭合 ✓

**⇒ **第二次确认那个 join key。**

**⚠ 而"四项 + 表检查"⇒ **一个五重身份验证**。**

**✅ 与 §376 的"三重身份检查"**同族。

## 七、`setActorTransforms` 的"24 上限"

```cpp
if (!entityPool_ || transforms.empty() || transforms.size() > 24) return false;
std::set<std::uint32_t> entityNums;
std::vector<std::pair<std::uint32_t, SvGameEntity>> previous;
```

**⇒ 三层**：

```text
1. **`> 24` ⇒ 拒绝**
2. ⇒ **而用 `std::set` 查重**
3. ⇒ **所以是一个有界的批处理**
```

**⚠ 而 `24` 与 §337 的"24 项描述符"**同值**。**

**⇒ 可能**同一个常量**。**

**✅ 与 §351 的"`svActorRouteReplanMilliseconds`"**不同。

## 八、`setPlayerGroundReference` 的六项

```cpp
if (client == end || !entityPool_ || !entityPool_->resolve(controller) ||
    entity == entities_.end() ||
    entity->second.mapClassName != "ground_tilt_controller" ||
    entity->second.networkState.eType != EntityTypeScriptMover ||
    !entity->second.gameplayActive ||
    controller.entityNum >= EntityNumWorld)
{
    return false;
}
```

**⇒ 七层，含**`mapClassName` 的字符串检查**与**`eType` 检查**。**

**✅ 与 §353 的"`mapClassName == "zombie_actor"`"**第三次。**

## 九、`setPlayerWeapons` 的补充武器（六项）

```cpp
// 找空 heldWeapons 槽
const auto held = find_if(heldWeapons, [](auto &c) { return c.weaponAssetIndex == 0; });
// 找 clip：先按 clipIndex 匹配，再回退到 clipIndex == 0
// 找 pool：先按 ammoIndex 匹配，再回退到 ammoIndex == 0
if (held == end || clip == end || pool == end) return false;
*held = { .weaponAssetIndex = supplementalWeaponAssetIndex };
clip->clipIndex = supplementalWeapon.clipIndex;
clip->count[0] = supplementalWeapon.clipSize;
pool->ammoIndex = supplementalWeapon.ammoIndex;
pool->count = min<uint16>(0xFFF, supplementalWeapon.maxAmmo);
```

### 9.1 五层

```text
1. **`weaponAssetIndex == 0` 是【空槽】**（§366 的第二次）
2. ⇒ **`clipIndex == 0` 是【空 clip 槽】**
3. ⇒ **`ammoIndex == 0` 是【空池槽】**
4. ⇒ **三个"零是空"的哨兵**
5. ⇒ **而 `pool->count` 上限 `0xFFF`**
```

**✅ 与 §366 的"`clipIndex == 0` 空槽"**完全一致 ✓

**⇒ **第三次确认那三个"零=空"。**

**⚠ 而"`0xFFF`"与 §366 的"`clipMaximum` 的 `0x1FF`"**不同**（池 vs 弹匣）。**

**✅ **第四次确认那两个界。**

## 十、关键结论

1. **⭐⭐ "一个 actor 是一个真正的 `CONTENTS_BODY` 胶囊"`** —— **只发布 `ET_ACTOR` + `agentState` 造一个【令人信服的人形】，但子弹 trace 永远不能选中它**。
2. **"用与玩家路径【相同的站立身体尺寸与编码 solid】，直到 actor 的站姿字段恢复一个【更小的原生 bounds】"`**。
3. **与 §361 的"连上并且可被射击"完全同族**（第二次"画了但不可击中"，而这次是 actor）。
4. **⭐ actor 的九个原生 union 字**，而 **`eventParm` 是 loopSound（`+0x8C`）、`otherEntityNum` 是 attackerEntityNum（`+0x84`）、`scriptMoverAnimationIndex` 是 `partBits[0]`（`+0xE8`）** —— 第十次"一成员多语义"。
5. **"这些是【原生 union 字】，不是装饰性默认：`partBits[0]` 建 DObj"`**。
6. **⚠ `movementDir = 0x00FFFFFF` 与 §350 的 `solid == 0xFFFFFF` 【同值不同义】** —— 一个极容易混淆的地方。
7. **⭐ "`lerpData0058 = 0xFF000000 | agentNum`，低字是稳定的 join key、高字是 actor 拥有的状态"`** —— 而 §361 说 `0xFF0000NN` 的**字节 1 = 0 是错的**（那里需要 `0xFF0003NN`）。
8. **⚠ 所以 §386 这里仍是旧的 `0xFF000000` 形式** —— 一处潜在的同一错误（但因为它只用于 join 可能无害）。
9. **⭐ `ground_tilt_controller` 的字段 231** —— 在 `368600..440250` 从 `2047 → 100`，而 **COD4 叫它 `playersetgroundreferenceent`**，**BO2/Ghosts 保留同一方法**。
10. **"保留字段名（`linkEntityNum`）直到原生偏移 `0x248` 的其它消费者都被恢复"`** —— 一个精确的命名纪律。
11. **"字段 231"确认 `playerState` 有至少 231 个字段** —— 第二次确认 §370 的"0..245"。
12. **`spawnActor` 的三阶段 + 三重回滚**（删 `campaignAgents_` / 删 `entities_` / `pool.free`）—— 第十次事务性。
13. **⚠ `static_cast<void>(freeEntity(*handle))` 忽略返回值** —— 一处潜在的泄漏（与 §363 的"失败则抛异常"**两种风格**）。
14. **`setActorAgentState` 的五重身份验证**含 **`lerpData0058` 的低 16 位** —— 第二次确认那个 join key。
15. **`setActorTransforms` 的 `24` 上限**（与 §337 的"24 项描述符"**同值**，可能同一常量）。
16. **三个"零=空"哨兵**（`weaponAssetIndex` / `clipIndex` / `ammoIndex`）—— 第三次确认。
17. **`pool->count` 的上限 `0xFFF` 与 `clipMaximum` 的 `0x1FF`** —— 第四次确认那两个界（池 12 位 / 弹匣 9 位）。

## 十一、未闭合点

- `SvAgentState::ModelField` / `EntityNumField` 的索引与完整字段表。
- `actorTorsoAnimation(agent)` 的实现。
- `validAgentState` 的完整验证。
- 原生偏移 `0x248` 的其它消费者。
- `24` 是否与 §337 的 24 项描述符同源。
- `sv_snapshot_mp.cpp` 26500 行之后未读取（27,016 行，进度 98%）。
