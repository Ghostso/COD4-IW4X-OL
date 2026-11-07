# 360 · **"19，而 21 被试过并被回退" —— 它【杀死了客户端】** —— 同一索引→偏移映射下**不同位宽**、`demoq` 是对的而崩溃是证据、`ack` 冻在 11

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 15600–16000 行。

## 二、**`spawnZombieActor` 的"拒绝一个图走不到的目标"**（本组第四重要）

```cpp
// REFUSE A GOAL THE GRAPH CANNOT WALK, BEFORE TAKING AN ENTITY NUMBER.
//
// 12.80: two of four actors spawned onto isolated nodes and stood on their
// spawners for the whole match. Spawning one is strictly worse than not:
// it holds an entity number, it is published, it is drawn, and it can never
// do anything. The caller already handles a refusal by trying the next
// spawn point, so this turns a dead zombie into a live one somewhere else.
if constexpr (SvActorRefuseUnroutableSpawn)
{
    if (place.hasGoalOrigin && !zmGoalRoutable(place.goalOrigin))
        return std::nullopt;
}
```

### 2.1 七层

```text
1. **在占用一个实体号【之前】拒绝一个图走不到的目标**
2. ⇒ **12.80：四个 actor 里两个生成到孤立节点上，整场比赛站在它们的生成器上**
3. ⇒ **生成一个严格【更糟】于不生成**：
     · 它占一个实体号
     · 它被发布
     · 它被画
     · **而它永远不能做任何事**
4. ⇒ **调用方已经处理拒绝（试下一个生成点）**
5. ⇒ **所以这把一个死僵尸变成别处的活僵尸**
```

**✅ 与 §352 的"一个被拒的生成绝不能花掉一个实体"**完全同族（**第二次"验证在副作用之前"**）。**

**⚠ 而"四个里两个"⇒ **50% 的失败率**。**

**✅ 与 §356 的"四个 actor 里两个走了 151 单位"**同数值**。**

**⇒ **可能同一批测量。**

### 2.2 而 **"它永远不能做任何事"**

**✅ 与 §350 的"接收了、存储了、而从未被画"**不同** —— 这里**被画但不动**。**

**⇒ 三层**：

```text
1. 实体存在、被发布、被画
2. ⇒ **但站在生成器上不动**
3. ⇒ **所以玩家看到一个不动的僵尸**
```

**✅ **一个更糟的失败**（"死"的但不消失）。**

## 三、**`eType = 19` vs `21` 的完整事故**（本组最重要的一段）

### 3.1 完整的那段

```php
// 21, NOT 19. Retail publishes every zombie as 21 (12.30: zero eType-19
// entities alive at any sampled time in the whole capture), and the client
// treats them differently: sub_540860 calls sub_530E70 for 21 and never for
// 19, which is the record initialiser that fills from the entity state.
// Publishing 19 opted out of that path. See EntityTypeActorCorpse.
// 19, AND 21 WAS TRIED AND REVERTED. Retail does publish 21 (12.30) and the
// client gives 21 a record initialiser 19 never gets (sub_530E70 via
// sub_540860), so the change looked right -- and it KILLED THE CLIENT:
// acks froze at 11, snapshots kept climbing server-side, client timeout,
// game closed. 12.38.
//
// WHY: the per-eType netfield tables do NOT share codecs. The index -> OFFSET
// map is identical for 19 and 21, which is what was checked, but demoq's
// census reports different BITS for the same offset (+0x018 is -83 COORD on
// 19 and -79 ANGLE on 21). That difference was dismissed as a demoq bug on
// the strength of the 0xDA6808 table being per-index; the crash says demoq
// was right. Writing 19's codecs under a 21 header desynchronises the
// reader exactly like a missing bump() does.
//
// Switching eType therefore means re-deriving the WHOLE field table for 21,
// codec by codec, not changing a constant.
entity.networkState.eType = EntityTypeActor;
```

### 3.2 二十层

```text
1. **21，不是 19**
2. ⇒ **零售把每一个僵尸发布为 21**
3. ⇒ **（12.30：在整个捕获的【任何采样时刻】eType-19 实体数都是【零】）**
4. ⇒ **而客户端区别对待它们**：
     · **`sub_540860` 为 21 调用 `sub_530E70`**
     · **而从不为 19**
5. ⇒ **`sub_530E70` 是那个从实体状态填充的【记录初始化器】**
6. ⇒ **发布 19 等于【退出】那条路径**
7. ⇒ **而 21 被试过并被【回退】**
8. ⇒ **零售确实发布 21 而客户端给 21 一个 19 从来得不到的记录初始化器**
9. ⇒ **所以那个改动看起来是对的**
10. ⇒ **而它【杀死了客户端】**：
     · **`ack` 冻在 11**
     · **服务器侧快照数继续攀升**
     · **客户端超时**
     · **游戏关闭**
11. ⇒ **12.38**
12. ⇒ **为什么：逐 eType 的 netfield 表【不共享编解码器】**
13. ⇒ **索引 → 偏移映射对 19 与 21 是【相同】的**
14. ⇒ **而那正是被检查过的东西**
15. ⇒ **但 `demoq` 的普查报告【同一个偏移】不同的【位】**
16. ⇒ **（`+0x018` 在 19 上是 `-83` COORD 而在 21 上是 `-79` ANGLE）**
17. ⇒ **那个差别被当作一个 `demoq` 的 bug 而【驳回】**
18. ⇒ **理由是 `0xDA6808` 表是【按索引】的**
19. ⇒ **而崩溃说 `demoq` 是【对的】**
20. ⇒ **把 19 的编解码器写在 21 的头下失步读者，【正像一个缺失的 `bump()`】**
21. ⇒ **所以切换 eType 意味着逐编解码器地【重新推导 21 的整张字段表】，不是改一个常数**
```

### 3.3 ⭐⭐ **"检查了索引→偏移映射而它是相同的"**

**✅ 这是本文件里**最重要的一条教训**。**

**⇒ 三层**：

```text
1. 索引 → 偏移映射：**19 与 21 相同**
2. ⇒ **所以"看起来安全"**
3. ⇒ **而编解码器（位宽/类型）不同**
4. ⇒ **所以映射相同 ≠ 表相同**
```

**✅ 与 §340 的"按偏移比较在重排表上和按索引一样错"**同族但**更深一层**：**

```text
§340  按偏移比较错（因为字段移了位置）
§360  按【索引→偏移】比较也不够（因为编解码器不同）
```

**⇒ **三层比较都不够**：偏移、索引、索引→偏移映射。**

**⇒ 唯一可靠的是**逐字段的编解码器 + 位宽**。**

**✅ **第六次"表比较的三层陷阱"。**

### 3.4 而**`+0x018` 的两个不同含义**

```text
19   +0x018 = -83  COORD（坐标）
21   +0x018 = -79  ANGLE（角度）
```

**⇒ 三层**：

```text
1. **同一个偏移**
2. ⇒ **不同的编解码器（-83 vs -79）**
3. ⇒ **所以不同的解释（坐标 vs 角度）**
```

**✅ 与 §342 的"`-83..-78` 是坐标编解码器"**配合。**

**⇒ 而 `-79` 也是**其中之一**。**

**⇒ 但 `-79` 是**编码为角度的**（`writeEntityAngle`）。**

**✅ 所以**同一族但语义不同**。**

### 3.5 而**"崩溃说 `demoq` 是对的"**

**✅ 与 §340 的"`82e` 的诊断错而建议对"**相反**。**

**⇒ 三层**：

```text
§340  诊断错而建议对（无害）
§360  诊断对而【被驳回】⇒ 崩溃（致命）
```

**✅ **一对精确的对照。**

**⇒ 而理由是一个**错误的先验**：**

```text
"`0xDA6808` 表是按索引的" ⇒ 所以"同一索引应给同一编解码器"
```

**⚠ 而"按索引"与"逐 eType 不同"**不矛盾**。**

**⇒ 所以那个先验**本身是错的**。**

**✅ **第五次"先验错误"。**

### 3.6 而**"`ack` 冻在 11"**

**✅ 与 §347 的"`cacheAcked=0` 永远"、§356 的"永远停在开口里"**同族（**第三次"ack 冻结"**）。**

**⚠ 而"11"是一个**具体数字**（可能 11 是**某个上限**）。**

**⇒ 与 §349 的"六个计数器"、§347 的"`cacheAcked`"配合。**

**✅ 而"服务器侧快照数继续攀升"⇒ **服务端健康而客户端死**（**第五次"服务端看不见客户端的死"**）。

### 3.7 而**"把 19 的编解码器写在 21 的头下失步读者【正像一个缺失的 `bump()`】"**

**✅ 与 §343 的"缺失的 `bump()` 关闭客户端"**完全同族（**第二次）。**

**⇒ 三层**：

```text
1. 头说 21（客户端用 21 的表）
2. ⇒ **而载荷是 19 的编解码器**
3. ⇒ **所以读者失步**
4. ⇒ **与 `bump()` 缺失完全一样**
```

**✅ **一个统一的心智模型**：任何"头/载荷不一致"都导致同一结果。**

## 四、**"pitch 与 roll 被强制为零，不是从生成点复制"**（本组第三重要）

```php
// PITCH AND ROLL FORCED TO ZERO, not copied from the spawn point. The map's
// spawn structs carry a yaw and this server must not put a leaning zombie on
// the wire: every retail actor's pitch and roll is zero, always.
entity.networkState.angles = { 0.0f, place.angles[1], 0.0f };
```

### 4.1 五层

```text
1. **pitch 与 roll 强制为零，不是从生成点复制**
2. ⇒ **地图的生成结构携带一个 yaw**
3. ⇒ **而这个服务器绝不能把一个【倾斜的僵尸】放到线上**
4. ⇒ **每一个零售 actor 的 pitch 与 roll 都是零，永远**
5. ⇒ `angles = { 0.0f, place.angles[1], 0.0f }`
```

**✅ 与 §344 的"`apos.trBase[0]` 与 `[2]` 断言六次且都是零"**完全一致 ✓**

**⇒ **第二次确认"僵尸不俯仰不翻滚"。**

**⚠ 而**只取 `place.angles[1]`**（yaw）。**

**✅ 一个**精确的三分量处理**。**

## 五、**"解析出的模型索引去字段 29，不是 `modelIndex`"**（本组第二重要）

### 5.1 那段

```php
// THE RESOLVED MODEL INDEX GOES TO FIELD 29, NOT TO modelIndex.
//
// `modelIndex` is written at field 19 / +0x05C, which is ET_SCRIPTMOVER's
// xmodel slot. On eType 19 that same offset is a 32-bit field pinned to
// 0x00FFFFFF -- so a model index parked there selected nothing at all,
// which is why an actor validated, kept frames healthy, and did not draw.
//
// Field 29 / +0x09C is the 10-bit index this eType actually carries: one
// write on the spawn frame, constant for the life.
```

### 5.2 十二层

```text
1. **解析出的模型索引去【字段 29】，不是 `modelIndex`**
2. ⇒ **`modelIndex` 被写在字段 19 / `+0x05C`**
3. ⇒ **那是 `ET_SCRIPTMOVER` 的 xmodel 槽**
4. ⇒ **在 eType 19 上同一个偏移是一个【钉到 `0x00FFFFFF` 的 32 位字段】**
5. ⇒ **所以一个停在里面的模型索引【什么也没选中】**
6. ⇒ **那就是为什么一个 actor 验证通过、帧保持健康、【而不画】**
7. ⇒ **字段 29 / `+0x09C` 是这个 eType 实际携带的【10 位索引】**
8. ⇒ **生成帧写一次，一生不变**
```

### 5.3 ⭐ **"钉到 `0x00FFFFFF` 的 32 位字段"**

**✅ 与 §350 的"`solid == 0xFFFFFF` 走画笔分支"**同一个数**。**

**⚠ 但这里是 **`modelIndex` 的偏移在 eType 19 上**。**

**⇒ 所以**同一个偏移在不同 eType 上是不同的东西**（第三次确认）。**

**✅ **第七次"一个偏移多个语义"。**

### 5.4 而 **"生成帧写一次，一生不变"**

**⚠ 而 §357 说动画需要**每 1.6-3.3 秒重断言**。**

**⇒ 所以**模型一次、动画反复**。**

**✅ 一个**精确的区分**（模型是常量、动画是状态）。

## 六、**`agentSlot` 的两个模式**（本组第五重要）

```php
std::uint8_t agentSlot = 4;
if constexpr (SvSendActorAgentElements) {
    bool haveSlot = false;
    // Retail zm allocates from slot zero because players live in CLIENTS,
    // not ACTORS. Preserve the legacy floor outside that explicit mode.
    const auto firstSlot = zmActorNamespaceEnabled_
        ? std::size_t{}
        : static_cast<std::size_t>(MaximumGameClients);
    for (auto candidate = firstSlot; candidate < SvAgentSlotCount; ++candidate) {
        if (agentSlotsInUse_[candidate]) continue;
        agentSlotsInUse_[candidate] = true;
        agentSlot = (uint8)candidate;
        haveSlot = true;
        break;
    }
    if (!haveSlot) return std::nullopt;
}
entity.networkState.actorAgentSlot = agentSlot;
```

### 6.1 七层

```text
1. **默认 `agentSlot = 4`**（关闭时的旧值）
2. ⇒ **开启时**：
     · **`zmActorNamespaceEnabled_` ⇒ 从槽 0 开始**
     · **否则 ⇒ 从 `MaximumGameClients`（18？）开始**
3. ⇒ **找一个未用的槽并置为占用**
4. ⇒ **没有空槽 ⇒ 拒绝生成**（`return nullopt`）
5. ⇒ **所以槽是【有界且唯一的】**
```

**✅ 与 §349 的"`agentSlotsInUse_.fill(false)`"**配合。**

**⚠ 而"零售 zm 从槽零分配，因为玩家住在【CLIENTS】不在【ACTORS】"。**

**⇒ 三层**：

```text
1. **零售 zm：玩家在 CLIENTS，所以 actor 槽从 0 开始**
2. ⇒ **旧模式：玩家与 actor 共享 ACTORS 命名空间**
3. ⇒ **所以 actor 从 `MaximumGameClients` 开始**
```

**✅ 与 §345 的"`emitPlayersInActorsSection`"**完全一致 ✓**

**⇒ **第三次确认那个双命名空间。**

## 七、**"模型去 AGENT 元素，不在这个实体上"**

```php
// THE MODEL GOES TO THE AGENT ELEMENT, NOT ONTO THIS ENTITY. eType 19 has
// no model field; sub_52FBE0 builds one from the 684-byte record that
// sub_530C90 fills out of agentState.
const auto outfit = SV_ZmChooseOutfit(zmOutfits_, zmOutfitSequence_,
    zmPresentationRound_, SvZmOutfit{appearanceIndex, headIndex});
entity.networkState.actorModelIndex = outfit.body;
entity.networkState.actorAttachModelIndex0 = outfit.head;
```

### 7.1 六层

```text
1. **模型去【AGENT 元素】，不在这个实体上**
2. ⇒ **eType 19 没有模型字段**
3. ⇒ **`sub_52FBE0` 从 `sub_530C90` 从 `agentState` 填出的【684 字节记录】构建一个**
4. ⇒ `actorModelIndex` = body
5. ⇒ `actorAttachModelIndex0` = head
6. ⇒ **所以模型与附件都在 agent 元素里**
```

**✅ 与 §338 的"agentState 的十个字段（8 modelIndex / 13 attach0 / 14 attach1）"**完全一致 ✓**

**⚠ 而 **684 字节**是 agent 记录的尺寸。**

**⇒ 与 §341 的 `352`（clientInfo）、§345 的 `280`（entityState）、§350 的 `60`（bmodel）**第四个尺寸。**

### 7.2 而 **`zmPresentationRound_` 的参与**

**✅ 与 §349 的"`zmPresentationRound_ = 1`"**配合。**

**⇒ 所以装扮选择**按轮次过滤**。**

**✅ 与注释的"`OLMOD(zm-round-colors)`：按轮次过滤的匹配身体/头对"**一致 ✓**

## 八、**"动画时钟现在开始"**

```php
// THE ANIM CLOCK STARTS NOW. sub_5242D0 discards the anim index unless
// this is non-zero, so the pair has to be asserted together or neither
// does anything.
```

### 8.1 四层

```text
1. **动画时钟现在开始**
2. ⇒ **`sub_5242D0` 丢弃动画索引【除非这个是零】**
3. ⇒ **所以这一对必须【一起】断言**
4. ⇒ **否则两者都不做任何事**
```

**✅ 与 §347 的"THE TIME FIRST，而它不是可选的"**完全同族（**第二次"时间必须先"**）。

**⚠ 而"除非这个是零"⇒ **所以零 = 丢弃**。**

**⇒ 与 §347 的"时间字段读 -99999 而地板是 0"配合。**

**✅ **第三次确认那个时间陷阱。**

## 九、**`expiredActors` 的"排队而不是在这里释放"**

```php
// THE CORPSES ARE QUEUED, NOT FREED HERE. Two reasons, and the second one
// is the one that mattered: freeEntity mutates `entities_`, which the loop
// above iterates -- and it is a generation-owned G_FreeEntity operation that
// cannot run inside the frame transaction at all. Draining the queue after
// the player-frame mirror commits is the only legal point.
for (const auto entityNum : expiredActors)
    pendingActorFrees_.push_back(entityNum);
```

### 9.1 八层

```text
1. **尸体是【排队】的，不在这里释放**
2. ⇒ **两个理由**
3. ⇒ **第一个：`freeEntity` 会修改 `entities_`，而上面的循环正在迭代它**
4. ⇒ **第二个（而它是重要的那个）**：
     · **它是一个【代际拥有的 `G_FreeEntity` 操作】**
     · **它在帧事务里【根本不能运行】**
5. ⇒ **在玩家帧镜像提交【之后】排空队列是【唯一的合法点】**
```

**✅ 与 §349 的"事务性"**第五次。**

**⇒ **本文件的核心：所有副作用必须在事务边界之外。**

### 9.2 而**"代际拥有"**

**⇒ 三层**：

```text
1. 实体有**代际**（`generation`）
2. ⇒ **释放必须指名代际**
3. ⇒ **所以一个已被复用槽的旧释放会失败**（而不是释放新实体）
```

**✅ 与 §353 的"`handle.generation`"**完全一致。

## 十、**"两个玩家原点，因为路由器读一个而碰撞视图读另一个"**

```php
// BOTH PLAYER ORIGINS, because the router reads one of them and the
// collision view reads the other, and every actor is routing to node
// 0 -- the node nearest the world origin -- rather than to a player.
// Guessing which field is stale has been wrong twice tonight.
```

### 10.1 六层

```text
1. **两个玩家原点，因为路由器读【一个】而碰撞视图读【另一个】**
2. ⇒ **而每一个 actor 都在路由到【节点 0】**
3. ⇒ **（最靠近世界原点的那个节点）**
4. ⇒ **而不是到一个玩家**
5. ⇒ **猜测哪个字段陈旧【今晚已经错过两次】**
```

### 10.2 ⭐ **"每一个 actor 都在路由到节点 0"**

**✅ 一个**极严重的症状**。**

**⇒ 三层**：

```text
1. 节点 0 是最靠近世界原点的节点
2. ⇒ **所以若玩家位置读到零 ⇒ 所有 actor 都去那里**
3. ⇒ **它们全都会走向地图中心**
```

**✅ 与 §355 的"`ps` 与 `ent` 两个位置"**完全闭合 ✓**

**⇒ **那个两个位置的打印就是为了诊断这个。**

### 10.3 而**"今晚已经错过两次"**

**✅ 与 §355 的"前 40 帧的日志结论都作废"**同族（**第五次自我推翻**）。

**⚠ 而"今晚"⇒ **一个会话内的时间标记**。**

**✅ 与 §342 的"2026-10-08"、§343 的"2026-08-24"**同族。

## 十一、**"面向它【实际走过的路】"**

```php
// FACE THE WAY IT ACTUALLY WALKED.  Collision steering can turn the
// traced displacement away from the blocked node; facing the old desired
// vector while moving along a wall is visible as sideways foot skating.
const auto actualDx = entity.currentOrigin[0] - previousOrigin[0];
const auto actualDy = entity.currentOrigin[1] - previousOrigin[1];
const auto yaw = actualDistanceSquared > 0.0001f
    ? SV_ZmTurnBody(entity.currentAngles[1], atan2(actualDy, actualDx)*180/PI, frameMilliseconds)
    : entity.currentAngles[1];
```

### 11.1 六层

```text
1. **面向它【实际走过的路】**
2. ⇒ **碰撞转向可以把 traced 位移【转离】被阻塞的节点**
3. ⇒ **而面向旧的期望向量当沿墙移动时可见为【侧向脚打滑】**
4. ⇒ **所以用【实际位移】**（`currentOrigin - previousOrigin`）
5. ⇒ **而 `SV_ZmTurnBody` 平滑旋转**（不是瞬移）
6. ⇒ **零位移 ⇒ 保持当前 yaw**
```

**✅ 与 §355 的"脚会打滑"**同族（**第四次的"打滑"**）。

**⇒ 而这里是**打滑的一个独立原因**（面向错方向）。****

**✅ **四种打滑原因**：**

```text
§355  速度 0.385 而非 0.079（太快）
§357  动画只播一次（冻结）
§359  侧向人群车道（游荡）
§360  面向期望向量而非实际位移（侧滑）
```

**✅ **四个不同的根因、一个可见症状。**

## 十二、**`block`/`slide`/`ground`/`steer` 四种报告**

```text
block<n>:node/to/frac/ss/as/hit/contents/normal          ← 移动被阻
slide<n>:side/frac                                      ← 沿墙滑动
ground<n>:proposed/up/down/mid/half/frac/ss/as/hit      ← 地面探测
groundStep<n>:z                                         ← 支撑步进重试
steer<n>:mode/target/wall/probeAge                      ← 最终转向
```

**⇒ 五种。**

**✅ 与 §355 的"命名是哪一个"**第五次。

## 十三、关键结论

1. **"在占用一个实体号【之前】拒绝一个图走不到的目标"`** —— **生成一个严格更糟于不生成**（占号/被发布/被画/永不行动）。
2. **⭐⭐ "19，而 21 被试过并被【回退】—— 它【杀死了客户端】"`** —— `ack` 冻在 11、快照继续攀升、客户端超时。
3. **零售把每一个僵尸发布为 21**（12.30：任何采样时刻 eType-19 实体数都是**零**）。
4. **`sub_540860` 为 21 调用 `sub_530E70`（记录初始化器）而从不为 19`**。
5. **⭐⭐ "索引 → 偏移映射对 19 与 21 是相同的，而那正是被检查过的东西"`** —— **而编解码器不同**。
6. **`+0x018` 在 19 上是 `-83` COORD 而在 21 上是 `-79` ANGLE`**。
7. **"那个差别被当作 `demoq` 的 bug 而驳回，理由是 `0xDA6808` 表是按索引的 —— 而崩溃说 `demoq` 是对的"`**。
8. **⭐ "把 19 的编解码器写在 21 的头下失步读者，正像一个缺失的 `bump()`"`** —— **一个统一的心智模型**。
9. **"切换 eType 意味着【逐编解码器重新推导】整张字段表，不是改一个常数"`**。
10. **pitch 与 roll 强制为零** —— **"绝不能把一个倾斜的僵尸放到线上；每一个零售 actor 的 pitch 与 roll 都是零，永远"`**（第二次确认）。
11. **⭐ "解析出的模型索引去【字段 29】，不是 `modelIndex`"`** —— `modelIndex` 在 `+0x05C` 而 eType 19 上那个偏移是**钉到 `0x00FFFFFF` 的 32 位字段**。
12. **"那就是为什么一个 actor 验证通过、帧保持健康、而不画"`** —— 第三次同一个诊断链。
13. **字段 29 / `+0x09C` 是 10 位索引，生成帧写一次一生不变`** —— 与动画的**反复重断言**形成精确区分。
14. **`agentSlot` 的两个模式**：零售 zm 从**槽 0**（玩家在 CLIENTS）vs 旧模式从 `MaximumGameClients`。
15. **"没有空槽 ⇒ 拒绝生成"`** —— 槽是有界且唯一的。
16. **"模型去 AGENT 元素，不在这个实体上"`** —— `sub_52FBE0` 从 **684 字节记录**（`sub_530C90` 从 agentState 填）构建模型。
17. **四个结构尺寸**（`684` agent / `352` clientInfo / `280` entityState / `60` bmodel）。
18. **"动画时钟现在开始 —— `sub_5242D0` 丢弃动画索引除非这个非零，所以这一对必须【一起】断言"`** —— 第三次确认时间陷阱。
19. **⭐ "尸体是【排队】的，不在这里释放"`** —— 因为 `freeEntity` 修改正在迭代的容器且**代际拥有的 `G_FreeEntity` 在帧事务里根本不能运行**。
20. **"在玩家帧镜像提交【之后】排空队列是唯一的合法点"`** —— 第五次事务性。
21. **⭐⭐ "每一个 actor 都在路由到【节点 0】（最靠近世界原点的节点）而不是到一个玩家"`** —— 极度严重的症状，而 **"猜测哪个字段陈旧今晚已经错过两次"`**。
22. **⭐ "面向它实际走过的路"`** —— `atan2(actualDy, actualDx)` 而非期望向量。
23. **四种打滑原因**（速度太快 / 动画冻结 / 侧向车道 / 面向错方向）—— **四个根因一个症状**。
24. **五种报告**（`block` / `slide` / `ground` / `groundStep` / `steer`）。

## 十四、未闭合点

- `SvAgentSlotCount` 的值。
- 为什么 `agentSlot` 关闭时默认是 4。
- `GlobalactorEntityFloor_` 的具体值。
- `ack` 冻在 11 的"11"是什么上限。
- 节点 0 的坐标（"最靠近世界原点"）。
- `sv_snapshot_mp.cpp` 16000 行之后未读取（27,016 行，进度 59%）。
