# 294 · **`bot-create` 的四段计时**、**`<map>_const.ff` 才是实体编号的真源**、`288/397` 的死假设

## 一、范围

本报告学习 `Appmain.cpp` 5220–5440 行。

## 二、`bot-create` 的**五个计时字段**

```php
const auto createStart = ...;
const auto afterResolve = ...;
const auto afterCreate = ...;
logGameServer(
    "BOTTRACE|bot-create index=" + index + " bots=" + BotsCreated +
    " elapsedUs=" + (now - createStart) +
    " resolveUs=" + (afterResolve - createStart) +
    " createUs="  + (afterCreate - afterResolve) +
    " restUs="    + (now - afterCreate) +
    " spacingMs=" + BotCreateIntervalMs);
lastBotCreateMs = steadyNowMs();
break;    // 【这个间隔的一个 bot；其余等着】
```

### 2.1 四段

```text
elapsedUs   总
resolveUs   职业解析（createStart → afterResolve）
createUs    createBotClient（afterResolve → afterCreate）
restUs      其余（afterCreate → now，含日志本身）
spacingMs   间隔
```

### 2.2 而**三个时间戳都在循环内**

**⇒ 所以每个 bot 的耗时是**独立**的。**

### 2.3 而"时间戳在**工作之后**"

```php
// The timestamp is taken AFTER the work: measured before it, a 900 ms
// creation would satisfy the interval on the very next call and the burst
// would come back.
```

### 2.4 三层

```text
1. 时间戳在工作**之后**取
2. 如果在**之前**取，一个 900 ms 的创建会**在下次调用就满足间隔**
3. ⇒ 而**爆发会回来**
```

**⇒ 一个非常细致的时序论证** —— 因为 `steadyNowMs()` 在**之后**取 ⇒ `lastBotCreateMs + 400` 从**完成时刻**起算。

**✓ 正确。**

### 2.5 而 `break` 保证**每间隔一个**

**⇒ 与 §292 的"按间隔一次一个"配合。**

### 2.6 而那个"判据"

```php
// ★ ③c 三段拆分（判据：resolveUs 大 ⇒ 缓存 9 套职业解析；restUs 大 ⇒ 成本在发布/同帧其它）
```

**⇒ 三层**：

```text
resolveUs 大  ⇒ 缓存 9 套职业解析
restUs 大     ⇒ 成本在发布/同帧其它
```

**✓ 一个清晰的判据。**

## 三、`takeTimeoutDrops` 的**十二个字段**

```php
logGameServer(cause + " client=" + N + " xuid=" + N + " state=" + N +
    " last_packet=" + N + " profile=" + N + "/" + N +
    " profile_complete=" + N + " gamestate_stage=" + N +
    " session_generation=" + N + " generation_active=" + N +
    " msg_ack=" + N + " reliable_ack=" + N);
```

### 3.1 十二个

```text
cause               Leave 或 Timeout
client / xuid / state
last_packet
profile             收到/必需的掩码
profile_complete
gamestate_stage
session_generation / generation_active
msg_ack / reliable_ack
```

### 3.2 而 `cause` 的两值

```php
drop.cause == TimeoutDrop::Cause::Leave ? "client leave" : "client timeout"
```

**⇒ "客户端主动离开" 与 "客户端超时" 分开。**

**✓ 与 §273 的"playerDamage vs entityDamage 分开"同族。**

### 3.3 而 `profile` 的**两个掩码对比**

```text
profileStatsReceivedMask / profileStatsRequiredMask
```

**⇒ 与 §255 的 `ProfileRequiredChunkMask` 的**相等**判据**不同** —— 这里可能是子集判据。**

**⚠ 两处对 profile 就绪用了不同的判据。**

## 四、`PendingWorldAsset` 的**1 秒节流**

```php
{
    const std::lock_guard lock(WorldAssetMutex);
    if (!PendingWorldAsset ||
        (PendingWorldAsset->attempted &&
         nowMilliseconds - PendingWorldAsset->lastAttemptMilliseconds < 1000))
        return;
    PendingWorldAsset->attempted = true;
    PendingWorldAsset->lastAttemptMilliseconds = nowMilliseconds;
    request = PendingWorldAsset;
}
```

**⇒ 与 §279 的 `ensureClientSessionBridge` 的 1 秒节流**同族**。**

**⇒ 三次了（§279 / §281 的 `ensureDedicatedControlServer` / §294）。**

## 五、**三个查找缓存**（本组第二重要）

```php
// OLMOD(world-preparation-lookups): cache only within this setup attempt.
// Colour variants share damage models/head bones and FX. Repeating the
// same native DB/CCS scans blocks the frame thread (and network service)
// during join. No cache survives a failed attempt or a zone generation.
std::map<std::pair<std::string,std::string>, optional<uint8>> boneResults;
std::map<std::array<std::string,3>, optional<uint8>> attachmentResults;
std::map<std::string, optional<uint16>> effectResults;
uint32 lookupRequests{}, lookupMisses{};
```

### 5.1 三层

```text
1. 【只在这一**次**设置尝试内】缓存
2. 颜色变体共享伤害模型/头骨与 FX ⇒ 重复的同一次原生 DB/CCS 扫描会**阻塞帧线程**（以及网络服务）
3. ⇒ **没有缓存能挺过一次失败尝试或一个 zone 代际**
```

### 5.2 而三个缓存的键

```text
boneResults         (model, bone) → optional<uint8>
attachmentResults   (body, head, bone) → optional<uint8>
effectResults       name → optional<uint16>
```

**⇒ 而**都缓存 `nullopt`**（因为 value 是 `optional`）。**

**✓ 所以"查不到"也被缓存** —— 与 §274 的 `resolveServerMeleeDamage`（不缓存失败）**相反**。

**⇒ 但这里注释说"只在这次尝试内" ⇒ 所以下次会重试。**

**✓ 合理的折中。**

### 5.3 而 `lookupRequests` / `lookupMisses`

```cpp
const auto boneIndex = [&](model, bone) {
    ++lookupRequests;
    if (found) return found->second;
    ++lookupMisses;
    const auto result = Bindings.modelBoneIndex(model, bone);
    boneResults.emplace(key, result);
    return result;
};
```

**⇒ `lookupRequests` 是**总请求**而 `lookupMisses` 是**缓存未命中**。**

**⚠ `lookupMisses` 这个名字**误导** —— 它统计的是"缓存未命中"而不是"查找失败"。**

**⇒ 应该叫 `cacheMisses`。**

### 5.4 而这三个 lambda 对应三个函数

```text
modelBoneIndex(model, bone)                   §261
attachmentBoneIndex(body, head, bone)         §261
resolveEffectEventParameter(name)             §261
```

**⇒ 三个都是 §261 学过的。**

### 5.5 而"颜色变体共享伤害模型/头骨与 FX"

**⇒ 所以一个地图上的多个角色变体会重复查同样的骨骼。**

**⇒ 缓存命中率高。**

## 六、`reportFailure` 的**四个参数**

```cpp
const auto reportFailure = [&request](std::string stage) {
    bool changed{};
    {
        const std::lock_guard lock(WorldAssetMutex);
        if (PendingWorldAsset && request &&
            PendingWorldAsset->mapName == request->mapName &&
            PendingWorldAsset->gameType == request->gameType &&
            PendingWorldAsset->lastFailureStage != stage)
        {
            PendingWorldAsset->lastFailureStage = stage;
            changed = true;
        }
    }
    if (changed)
        logGameServer("world spawn pending map=" + request->mapName + " stage=" + stage);
};
```

### 6.1 四个条件

```text
PendingWorldAsset 存在
request 存在
mapName 与 gameType 【仍匹配】
stage 【与上次不同】
```

**⇒ 四项 AND ⇒ 只在**同一个请求**且**阶段变化**时打印。**

**✓ 与 §244 的 `refuse` 边沿触发同族。**

### 6.2 而 `mapName`/`gameType` 匹配是**防止跨地图混淆**

**⇒ 所以一个旧请求的失败不会打到新请求上。**

## 七、**世界准备的六个阶段**（本组第三重要）

```php
// ① map_entity_asset
const auto entityText = request->mapEntities ? optional<string>{} : Bindings.readMapEntityString(request->mapName);
if (!request->mapEntities && !entityText) { reportFailure("map_entity_asset"); return; }

// ② glass_map_metadata
const auto glassMetadata = Bindings.resolveGlassMapMetadata(request->mapName);
if (!glassMetadata) { reportFailure("glass_map_metadata"); return; }

// ③ glass_damage_thresholds
const auto glassThresholds = glassDamageThresholds();
if (!glassThresholds) { reportFailure("glass_damage_thresholds"); return; }

// ④ glass_world_commit
if (!Server.configureGlassMap(*glassMetadata, *glassThresholds)) { reportFailure("glass_world_commit"); return; }

// ⑤ map_entity_parse
const auto entities = request->mapEntities ? request->mapEntities : SV_ParseMapEntities(*entityText);
if (!entities) { reportFailure("map_entity_parse"); return; }

// ⑥（后续）
```

### 7.1 六个阶段

```text
map_entity_asset
glass_map_metadata
glass_damage_thresholds
glass_world_commit
map_entity_parse
（后续）
```

### 7.2 而与 §289 的"`NO_SPAWN_POINT`"**对齐**

**§289**："configureWorldSpawn then failed on `initial_spawn_ground_trace`"

**⇒ 那是**更后面**的阶段（这里只到 `map_entity_parse`）。**

### 7.3 而 `map_entity_asset` 与 §257 的"两种命名"配套

**⇒ 所以 `readMapEntityString` 的失败会走到这里。**

## 八、**`<map>_const.ff` 才是实体编号的真源**（本组最重要的一段）

### 8.1 那段完整的假设推翻

```php
// OLMOD(const-baselines): THE ENTITY NUMBER IS THE IDENTITY, and it is not something
// this server derives -- it is shipped data.
//
// A census used to run here, printing every map entity in parse order, to test the
// hypothesis that retail numbers by position among ALL map entities. That hypothesis
// is dead: hill-climbing it plateaued at 288/397 with an incoherent skip-set, because
// the gaps encode which entities take a slot and the entity list does not say.
//
// The answer is `<map>_const.ff`, an asset every map ships:
// `mp/constbaselines/bl_pc_<map>_<gametype>.bin` IS retail's table, and the client
// loads it at map load and indexes cl.entityBaselines out of it by entity number.
// sv_const_baselines_mp.hpp carries the extracted numbers; re/demo-re/16-const-baselines.md
// has the derivation. This log says whether this map got them.
```

### 8.2 七层

```text
1. **实体编号是身份**，而且**不是**这个服务器推导的 —— 它是**随包数据**
2. 过去在这里跑一个普查，按解析顺序打印每一个地图实体，测试"零售按**所有**地图实体中的位置编号"
3. **那个假设死了**：爬山法在 **288/397** 平台期，且**跳跃集不连贯**
4. 因为**间隙编码了哪些实体占一个槽**而实体列表**不说明**
5. ⇒ 答案是 `<map>_const.ff`，每张地图都随包的资产
6. `mp/constbaselines/bl_pc_<map>_<gametype>.bin` **就是**零售的表
7. 客户端在地图加载时加载它并从 `cl.entityBaselines` 按实体号索引
```

### 8.3 **`288/397` 是一个死假设的量化结果**

**⇒ 与 §245 的"三次运行都说 stage=5"、§277 的"26 次命中只 1 次能定姿态"同族**（第五次量化失败）。

**⇒ 而 397 是**地图实体总数**而 288 是**匹配的**。**

**⇒ 所以 109 个不匹配（27%）⇒ 而"跳跃集不连贯"说明不是简单偏移。**

### 8.4 而记忆里"const baseline keyed on `(map, gametype)`"

**⇒ 与这里的 `bl_pc_<map>_<gametype>.bin` **完全一致** ✓**

**⇒ 而记忆里"snapshot flag **0x10**（`cl.entityBaselines`，`<map>_const.ff` 是那个编号）"**也完全一致** ✓

**✅ 这是第三次确认这组事实。**

### 8.5 而两段日志

```php
if (constBaselines) {
    logGameServer("const baselines map=" + map + " gametype=" + gameType +
        " entries=" + size + " brushModels=" + N +
        " -- static entities publish on retail's numbers and snapshot flag 0x10 is armed");
}
else {
    logGameServer("const baselines map=" + map +
        " NONE -- no extracted table for this map, static entities "
        "fall back to sequential numbering and snapshot flag 0x10 stays off");
}
```

### 8.6 两种

```text
有表 ⇒ "按零售的编号发布" 且 "flag 0x10 已武装"
无表 ⇒ "回退到顺序编号" 且 "flag 0x10 保持关闭"
```

**⇒ 一个**降级路径**，且**明确说明** flag 0x10 的状态。**

**✓ 与 §236/§244 的"降级但明说"同族。**

### 8.7 而 `brushModels` 的计数

```php
size_t brushModels = 0;
for (const auto &entry : constBaselines->entries)
    brushModels += entry.brushModelIndex ? 1 : 0;
```

**⇒ 所以 `brushModelIndex != 0` 的条目数。**

**⇒ 与 §294 后面的"brush `*N` 随槽序严格上升"相关。**

## 九、**"临时"的锚点假设**

```php
// TEMPORARY: the map's OWN order for the two classes that take a static
// entity slot. Retail's table is in allocation order -- brush `*N` rises
// strictly with slot order -- so brush models are exact ordered ANCHORS, and
// the script models between two consecutive anchors must be the table rows
// between those same two anchors, in order. Position within an anchored
// bracket is an identity in a way an origin is not.
//
// Logged raw so the hypothesis can be tested against the shipped table before
// any of it is believed.
```

### 9.1 五层

```text
1. 【临时】
2. 零售的表是**分配顺序** —— brush `*N` 随槽序**严格上升**
3. ⇒ brush models 是**有序锚点**
4. 而两个连续锚点之间的 script models **必须**是那两个锚点之间的表行，**按序**
5. ⇒ **锚定括号内的位置**是一种身份，而原点不是
6. ⇒ **原样记录**以便假设能对着随包表被测试，**在任何一项被相信之前**
```

### 9.2 而"在任何一项被相信之前"**

**⇒ 与 §288 的"留空是有意的"、§292 的"没什么被发明"同族**（第六次"不信未验证的"）。

## 十、关键结论

1. **`bot-create` 的四段计时**（elapsed/resolve/create/rest + spacing）。
2. **时间戳在**之后**取** —— 否则 900 ms 的创建会在下次调用就满足间隔。
3. **`resolveUs` 大 ⇒ 缓存职业解析；`restUs` 大 ⇒ 成本在发布/同帧其它** —— 一个清晰的判据。
4. **`takeTimeoutDrops` 分开 Leave 与 Timeout**。
5. **`profile` 的两个掩码对比与 §255 的"相等"判据不同** —— 两处不同判据。
6. **1 秒节流第三次出现**。
7. **三个查找缓存只活在一次设置尝试内**，且**缓存 `nullopt`**。
8. **`lookupMisses` 名字误导** —— 它统计缓存未命中而非查找失败。
9. **`reportFailure` 的四个条件**（含 mapName/gameType 匹配防止跨地图混淆）。
10. **世界准备的六个阶段**（`map_entity_asset` / `glass_map_metadata` / `glass_damage_thresholds` / `glass_world_commit` / `map_entity_parse` / …）。
11. **"实体编号是随包数据不是推导的"** —— 记忆里"`<map>_const.ff` 是那个编号"第三次确认。
12. **`288/397` 的死假设** —— 按位置编号在 27% 处平台期且跳跃集不连贯。
13. **`bl_pc_<map>_<gametype>.bin`** 与记忆里"(map, gametype)"键完全一致。
14. **有表 ⇒ flag 0x10 武装；无表 ⇒ 回退顺序编号且 flag 关闭** —— 明确的降级路径。
15. **"临时"的锚点假设**：brush `*N` 随槽序严格上升 ⇒ 有序锚点 ⇒ 括号内的 script model 位置是身份。
16. **"在任何一项被相信之前"先记录** —— 第六次"不信未验证的"。

## 十一、未闭合点

- `profile` 两处判据差异。
- `288/397` 的 109 个不匹配实体的具体性质。
- 世界准备的后续阶段（`initial_spawn_ground_trace` 等）。
- `Appmain.cpp` 5440 行之后未读取。
