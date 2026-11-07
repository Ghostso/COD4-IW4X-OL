# 379 · **"这不是一个队伍"** —— agent 字段 21 恒为 1、`12.36` 说发零而那是【错的】、`node_type` 的 extract/insert 回滚、`27` 次 `12.x` 引用

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 23200–23600 行。

## 二、**agent 元素的六个字段实测**（本组最重要的一段）

### 2.1 那段

```php
for (const auto &entity : candidateSnapshot.entities) {
    if constexpr (!SvSendActorAgentElements) break;
    if (entity.eType != EntityTypeActor || !entity.actorModelIndex) continue;
    candidateSnapshot.agents.push_back({
        .clientNum = entity.actorAgentSlot,
        // NOT A TEAM. On an agent this is field 21, +0x008, eleven bits, and
        // the netfield table has no name for it. MEASURED on three retail
        // zombie spawn frames -- slot 4 @288250, slot 6 @1230050, slot 3
        // @1074950 -- it reads 1 every time, while this server was sending
        // 0. `SvTeam::Tf` is simply the enumerator whose value is 1; the
        // member is reused because this list's element struct is shared with
        // the player entries, not because a zombie has a team.
        .team = SvTeam::Tf,
        .modelIndex = entity.actorModelIndex,
        // THE ACTOR'S OWN ENTITY NUMBER, field 20, +0x004. sub_530C90 copies
        // it to record+0x0C; retail's records read 723..741 there, matching
        // the actors they describe, while ours read 345 -- the untouched
        // default row -- because this was never sent. 12.26/12.27.
        .entityNumber = entity.number,
        .attachModelIndex0 = entity.actorAttachModelIndex0,
        .attachModelIndex1 = 0,
        .attachTagIndex0 = entity.actorAttachModelIndex0 ? SvActorHeadTagIndex : std::uint16_t{},
        .attachTagIndex1 = 0,
        .animIndex = SvActorSendAnimIndex ? (entity.actorAnimIndex ? entity.actorAnimIndex : SvActorAnimIndex) : std::uint16_t{},
        .animStartTime = SvActorSendAnimIndex ? entity.actorAnimStartTime : std::uint32_t{},
    });
    ...
}
```

### 2.2 十四层

```text
1. **不是一个队伍**
2. ⇒ **在一个 agent 上这是字段 21、`+0x008`、十一位**
3. ⇒ **而 netfield 表【没有名字】给它**
4. ⇒ **在三个零售僵尸生成帧上测量**：
     · **槽 4 @288250**
     · **槽 6 @1230050**
     · **槽 3 @1074950**
5. ⇒ **它每次都读 `1`**
6. ⇒ **而这个服务器在发 `0`**
7. ⇒ **`SvTeam::Tf` 只是那个值为 `1` 的枚举子**
8. ⇒ **这个成员被复用因为【这个列表的元素结构是与玩家条目共享的】**
9. ⇒ **不是因为一个僵尸有一个队伍**
```

### 2.3 ⭐⭐ **"这不是一个有队伍的僵尸 —— 是元素结构被复用"**

**✅ 与 §344 的"`groundEntityNum` 在布告上是字段 13"**同族（**第九次"一成员多语义"。**

**⇒ 三层**：

```text
同一个 `SvClientState` 结构
⇒ 玩家的 `.team` 是队伍
⇒ **而 agent 的 `.team` 是 field 21 的一个无名字**
⇒ **只是值恰好 1**
```

**✅ 与 §379 的"注释明说不是队伍"**完全一致。

**⚠ 而"表没有名字给它"⇒ **所以它确实是未知的。**

**✅ 与 §360 的"字段 29 不是外观 ⇒ 什么都不发"**不同** —— 这里**发 1 因为实测**。**

**⇒ 三次"实测胜过命名"。**

### 2.4 而**`entityNumber` 的"`723..741` vs `345`"**

```text
retail 记录读 `723..741` ⇒ **匹配它们描述的那些 actor**
而我们的读 `345` ⇒ **未触碰的默认行**
⇒ **因为这个从未被发送**
```

**✅ 与 §338 的"`unk_DA9920` 的四个非零默认（含 `entityNumber = 345`）"**完全闭合 ✓

**⇒ **第二次确认 `345` 是那个默认。**

**⚠ 而"`723..741`"⇒ **19 个不同的值**（对应不同的 actor）。**

**✅ 与 §352 的"1100 个节点"**不同（这是**19 个实体号**）。

### 2.5 而 **`12.36` 说发零而那是【错的】**

```php
// 12.36 SAID SEND ZERO HERE AND THAT WAS WRONG -- it sampled the
// gaps BETWEEN animations, where retail does read 0, and
// generalised. Retail asserts idx9 constantly (12.50), 476 among
// them, and 476 is a valid key in the zombie anim BST read live
// out of playback (12.52). A zero index means sub_524A10 never
// allocates an animation block at all, which is the T-pose.
// PER ACTOR NOW, not one constant for all of them: the stepper
// overrides it for the length of a barrier vault. Zero still means
// the default, so an actor that never vaults is byte-identical to
// what this server sent before.
```

**⇒ 十二层**：

```text
1. **`12.36` 说在这里发零而那是【错的】**
2. ⇒ **它采样了动画【之间】的空隙**
3. ⇒ **在那里零售确实读 `0`**
4. ⇒ **而【一般化】了**
5. ⇒ **零售【持续地】断言 idx9（`12.50`）**
6. ⇒ **`476` 在其中**
7. ⇒ **而 `476` 是僵尸动画 BST 里的一个【有效键】**（`12.52`，从播放活读出）
8. ⇒ **一个零索引意味着 `sub_524A10` 【根本】不分配动画块**
9. ⇒ **那就是【T 姿势】**
10. ⇒ **现在是【按 actor】而不是一个常数**
11. ⇒ **步进器为一次屏障翻越的时长覆盖它**
12. ⇒ **零仍意味着默认，所以一个从不翻越的 actor 与这个服务器之前发的【逐字节相同】**
```

### 2.6 ⭐⭐ **"采样了动画之间的空隙而一般化了"**

**✅ 与 §355 的"从几个样本读了 38-39"**同族（**第四次采样偏差**）。**

**⇒ 三层**：

```text
样本：动画之间的空隙 ⇒ 读到 0
⇒ **而一般化成"总是 0"**
⇒ **而实际上动画在播时是 476 等**
```

**✅ 与 §372 的"前 40 帧的日志结论都作废"**同族（**第五次"样本不代表"）。**

**⚠ 而"T 姿势"⇒ **一个极具体的症状**（第十次具体视觉症状）。**

**✅ 与 §371 的"手里一把枪读 Out of ammo"**同族。

## 三、**`node_type` 的 extract/insert 回滚**（本组第二重要）

### 3.1 那段

```php
// A full pool may reuse a missile's newly retired number for a living
// child in this same candidate. Extract the old node before inserting
// that child; rollback already removes children before restoring missiles.
for (auto &staged : stagedMissiles) {
    if (staged.retire) staged.retiredNode = entities_.extract(staged.handle.entityNum);
    else std::swap(entities_.at(staged.handle.entityNum), staged.entity);
}
std::vector<std::unordered_map<std::uint32_t, SvGameEntity>::node_type> retiredLivingWeaponNodes;
for (auto &staged : stagedLivingWeaponChildren) {
    if (staged.retire) retiredLivingWeaponNodes.push_back(entities_.extract(staged.handle.entityNum));
    else if (staged.inserted) entities_.emplace(staged.handle.entityNum, std::move(staged.entity));
    else std::swap(entities_.at(staged.handle.entityNum), staged.entity);
}
```

### 3.2 十一层

```text
1. **一个满的池可能在这个【同一个候选】里复用一个导弹【刚退役的号】给一个活子实体**
2. ⇒ **在插入那个子实体【之前】抽取旧节点**
3. ⇒ **而回滚已经在恢复导弹【之前】移除子实体**
4. ⇒ **所以顺序是【关键的】**
5. ⇒ `entities_.extract(num)` ⇒ **返回一个 `node_type`**（不销毁、不拷贝）
6. ⇒ **所以退役的实体可以在回滚时【原样插回】**
7. ⇒ **三种操作**：
     · `retire` ⇒ **extract**（暂存节点）
     · `inserted` ⇒ **emplace**（新增）
     · 否则 ⇒ **swap**（更新）
```

**✅ ⭐ **`node_type` 是 C++17 的"节点句柄"—— 零拷贝的 extract/insert**。**

**⇒ 三层**：

```text
`extract` ⇒ **移除节点而【不销毁】**
`insert(node)` ⇒ **原样放回**
⇒ **所以回滚 = 零拷贝 + 保留哈希**
```

**✅ 与 §364 的"`std::swap` 作为零成本的保存"**同族（**第四次"零成本回滚手法"）。**

**⚠ 而"一个满的池可能复用同一个号"⇒ **一个极精确的冲突场景**。**

**✅ 与 §376 的"只暂存导弹"**配合。

### 3.3 而**"回滚已经移除子实体【之前】恢复导弹"**

**⇒ 三层**：

```text
提交顺序：  抽导弹 → 插子实体
回滚顺序：  **删子实体 → 插回导弹**
⇒ **所以子实体先走，导弹后回来** ✓
```

**✅ 一个**正确的逆序**（与 §376 同族）。**

### 3.4 而回滚的完整对称

```php
for (auto it = stagedLivingWeaponChildren.rbegin(); it != rent(); ++it) {
    if (it->retire) {
        auto node = std::move(retiredLivingWeaponNodes.back());
        retiredLivingWeaponNodes.pop_back();
        entities_.insert(std::move(node));
    } else if (it->inserted) entities_.erase(it->handle.entityNum);
    else std::swap(entities_.at(it->handle.entityNum), it->entity);
}
for (const auto &[handle, effect] : stagedMissileEffects) entities_.erase(handle.entityNum);
for (auto &staged : stagedMissiles) {
    if (staged.retire) entities_.insert(std::move(staged.retiredNode));
    else std::swap(entities_.at(staged.handle.entityNum), staged.entity);
}
```

**⇒ 四层**：

```text
1. **子实体按【逆序】回滚**（`rbegin`）
2. ⇒ **而 `retiredLivingWeaponNodes` 是【后进先出】**（`back` + `pop_back`）
3. ⇒ **所以两个逆序【嵌套】而不冲突**
4. ⇒ **然后导弹效果 `erase`**
5. ⇒ **然后导弹本身（`insert` 或 `swap`）**
```

**✅ 一个**精确的多层逆序**。**

**⚠ 而"两个逆序嵌套"⇒ **一个极易出错的模式**。**

**✅ 而这里**正确**。

## 四、**`agents` 的"追加之后排序"**（本组第三重要）

```php
// ONE AGENT ELEMENT PER LIVE ACTOR -- the ACTORS section, which is where an
// ET_ACTOR's model lives and the only thing that fills the client's 684-byte
// render record. Without it sub_52FBE0 returns at `record[0] == 0` and the
// zombie is invisible while every other measure of health stays green.
// re/demo-re/20-zm-actor-lifecycle.md 12.7 and 12.8.
//
// Appended AFTER the per-client elements and sorted, because the section is
// written as an ascending walk: writeClientNumber emits `++index` or an
// explicit five-bit slot, and a slot out of order would renumber the rest of
// the list. Actor slots start above MaximumGameClients so they never collide
// with a player's.
std::ranges::sort(candidateSnapshot.agents, {}, &SvClientState::clientNum);
```

### 4.1 十二层

```text
1. **每个活 actor 一个 agent 元素** —— ACTORS 段
2. ⇒ **那是 `ET_ACTOR` 的模型【住的地方】**
3. ⇒ **而唯一填写客户端 **684 字节渲染记录** 的东西**
4. ⇒ **没有它 `sub_52FBE0` 在 `record[0] == 0` 处返回**
5. ⇒ **而僵尸【不可见】**
6. ⇒ **而其它每一个健康度量保持绿色**
7. ⇒ **（`12.7` 与 `12.8`）**
8. ⇒ **在按客户端元素【之后】追加并排序**
9. ⇒ **因为那个段是以【升序走】写的**
10. ⇒ **`writeClientNumber` 发 `++index` 或一个显式的五位槽**（§337）
11. ⇒ **而一个乱序的槽会【重新编号】列表的其余部分**
12. ⇒ **actor 槽从 `MaximumGameClients` 之上开始，所以永不与玩家的冲突**
```

**✅ ⭐ **"而其它每一个健康度量保持绿色"** —— 第十次"沉默读起来像健康"。**

**⇒ 三次确认 `684` 字节记录。**

**✅ 与 §361 的"`sub_52FBE0` 从 `sub_530C90` 从 `agentState` 填出的 684 字节记录"**完全一致 ✓

**⚠ 而"`record[0] == 0`"⇒ **记录的**第一个字段**是空 ⇒ 返回。**

**✅ 与 §379 二.2 的"字段 21 是 `+0x008`"**不同**（`record[0]` 是**头**）。

**⚠ 所以**记录的第一个字节是"有效性"**。**

**✅ 一个**需要确认的细节**。

### 4.2 而**排序的必要性**

**✅ 与 §337 的"`writeClientNumber` 的连续/跳跃两分支"**完全闭合 ✓

**⇒ 第三次确认那个编码。**

## 五、**`pendingAnimationCommands_` 的 `framesRemaining`**

```php
for (const auto &pending : pendingAnimationCommands_)
    if (pending.framesRemaining) candidateSnapshot.animationCommands.push_back(pending.command);
...
for (auto &pending : pendingAnimationCommands_)
    if (pending.framesRemaining) --pending.framesRemaining;
std::erase_if(pendingAnimationCommands_, [](const PendingAnimationCommand &p) { return !p.framesRemaining; });
```

### 5.1 五层

```text
1. **有 `framesRemaining` ⇒ 进快照**
2. ⇒ **（提交成功后）递减**
3. ⇒ **归零 ⇒ 擦除**
4. ⇒ **所以一个命令存活【四帧】**（§361 的 `framesRemaining = 4`）
5. ⇒ **而失败则【不递减】**（所以重试）
```

**✅ 与 §349 的"投递状态在整快照成功后提交"**同族（**第四次"成功后提交"）。**

**⚠ 而"递减在提交【之后】**⇒ **所以一个失败的帧不消耗 `framesRemaining`。**

**✅ 一个**正确的重试语义**。

## 六、**`WeaponChanged` 的四级回退命名**

```php
if (!weapon) name = "none";
else if (const auto *resolved = SV_FindResolvedWeaponOrAlt(client.resolvedLoadout, weapon, alt))
    name = resolved->weaponName;
else if (client.playerState.rewardActionType == 1 && client.playerState.rewardActionWeapon == weapon)
    name = "killstreak_uav_mp";
else if (const auto *equipment = playerEquipment(clientNum, client.playerState.spawnGeneration))
    if (const auto *offhand = SV_FindOffhandWeapon(*equipment, weapon))
        name = offhand->weaponName;
if (name.empty()) continue; // Retry when the definition is available.
```

### 6.1 六层

```text
1. **`weapon == 0` ⇒ `"none"`**
2. ⇒ **否则查装备（主/副/alt）**
3. ⇒ **否则若 `rewardActionType == 1` 且匹配 ⇒ `"killstreak_uav_mp"`**
4. ⇒ **否则查副手装备**
5. ⇒ **名字仍空 ⇒ `continue`（重试）**
6. ⇒ **所以**四级回退** + 一个"还没准备好"**
```

**✅ 与 §366 的"三个武器出现机制"**配合。**

**⚠ 而"`continue` 重试"⇒ **所以 `observed.weapon` 不被设置 ⇒ 下一帧重试。**

**✅ 一个**正确的"等待依赖"**。**

## 七、`antiLagHistory_` 的**五条件**

```cpp
for (const auto &[clientNum, state] : clientStates_) {
    if (state.client.gameplayState != ClientGameplayState::Playing ||
        state.client.playerState.health == 0 ||
        !state.entity.collisionLinked ||
        state.entity.clientNum != clientNum)
        continue;
    antiLagPlayers.push_back({ .clientNum = clientNum, .spawnGeneration = ..., .origin = state.entity.currentOrigin });
}
antiLagHistory_.record(snapshot_.serverTime, antiLagPlayers);
```

**⇒ 四项**

**✅ 与 §373 的"400ms 回溯"**配合。**

**⚠ 而 `!collisionLinked` 的也排除 ⇒ **所以只有**在碰撞世界里的**玩家有历史。****

**✅ 一个**精确的范围**。**

## 八、关键结论

1. **⭐⭐ "这不是一个队伍"`** —— agent 的 `.team` 是**字段 21 / `+0x008` / 11 位**的**无名字**，而**成员被复用因为元素结构与玩家共享**。
2. **三个零售生成帧的实测**（槽 4 @288250 / 槽 6 @1230050 / 槽 3 @1074950）**都读 `1`** 而**这个服务器在发 `0`**。
3. **`entityNumber` 的 `723..741` vs 我们的 `345`** —— **第二次确认 `345` 是 `unk_DA9920` 的默认。**
4. **⭐⭐ "`12.36` 说在这里发零而那是【错的】——它采样了动画【之间】的空隙，在那里零售确实读 0，而【一般化】了"`** —— 第四次采样偏差。
5. **"零售持续断言 idx9，`476` 是僵尸动画 BST 的一个有效键"`** —— 而**零索引意味着 `sub_524A10` 根本不分配动画块 ⇒ T 姿势**（第十次具体视觉症状）。
6. **"现在是按 actor 而不是一个常数：步进器为一次屏障翻越的时长覆盖它，而零仍意味着默认"`** —— 一个**向后兼容的扩展**。
7. **⭐ `entities_.extract` / `insert(node_type)` 的零拷贝回滚** —— 第四次"零成本回滚手法"（保留哈希、不销毁）。
8. **"一个满的池可能在这个同一个候选里复用一个导弹刚退役的号给一个活子实体 ⇒ 在插入那个子实体【之前】抽取旧节点"`** —— 一个极精确的冲突场景。
9. **两个逆序嵌套**（子实体 `rbegin` + `retiredLivingWeaponNodes` 的 LIFO）—— 一个极易出错而这里正确的模式。
10. **⭐ "每个活 actor 一个 agent 元素 —— 那是 `ET_ACTOR` 模型住的地方，而唯一填写客户端 684 字节渲染记录的东西"`** —— 第三次确认 `684`。
11. **"没有它 `sub_52FBE0` 在 `record[0] == 0` 处返回而僵尸不可见，而【其它每一个健康度量保持绿色】"`** —— 第十次"沉默读起来像健康"。
12. **agents 的排序必要性**（升序走 + `writeClientNumber` 的 `++index` / 五位槽）—— 第三次确认那个编码。
13. **`pendingAnimationCommands_` 的 `framesRemaining`**：**递减在提交【之后】** ⇒ **失败的帧不消耗**（第四次"成功后提交"）。
14. **`WeaponChanged` 的四级回退命名**（`none` / 装备 / `killstreak_uav_mp` / 副手）+ **"名字仍空则重试"**。
15. **`antiLagHistory_` 的四项范围**（含 `collisionLinked`）。

## 九、未闭合点

- `record[0]` 的"有效性"字节语义。
- `SvActorHeadTagIndex` / `SvActorAnimIndex` / `SvActorHeadTagIndex` 的值。
- `sub_524A10` 的动画块分配。
- 僵尸动画 BST 的完整键集。
- `SvActorSendActorAgentElements` / `SvActorSendAnimIndex` 的开关。
- `sv_snapshot_mp.cpp` 23600 行之后未读取（27,016 行，进度 87%）。
