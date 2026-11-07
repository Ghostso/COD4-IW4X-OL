# 299 · **`36 = 2 × 18` 的模型槽**、**"分块不截断"**（427 而 96 截断丢掉了 walk/attack/death）、`sd` 的炸弹触发器

## 一、范围

本报告学习 `Appmain.cpp` 6320–6540 行。

## 二、**"分块不截断"**（本组最重要的一段）

### 2.1 那段自我更正

```php
// CHUNKED, NOT TRUNCATED. The first cut capped at 96 and the band
// holds 427, so the names that matter -- walk, attack, death, taunt --
// fell off the end and cost a cycle. 64 per line keeps each record
// readable without losing any of it.
for (std::size_t first = 0; first < zmAnimNames.size(); first += 64u)
{
    std::string chunk;
    for (std::size_t at = first; at < zmAnimNames.size() && at < first + 64u; ++at)
        chunk += " " + zmAnimNames[at];
    logGameServer("zm animband part=" + (first / 64u) + chunk);
}
```

### 2.2 四层

```text
1. **第一版上限 96 而带里有 427**
2. ⇒ 重要的名字（walk、attack、death、taunt）**从末尾掉了出去**
3. ⇒ **花掉了一个周期**
4. ⇒ **64 每行**保持每条记录可读而**什么都不丢**
```

### 2.3 **这是一个"截断丢掉了最重要的部分"的实例**

**⇒ 因为重要的名字在**后面**（字母序或索引序）。**

**⚠ 而 §295 的 `verboseStatics` 与 §298 的 `dumped++ >= 400u` 也是截断。**

**⇒ 所以本文件里有**三种**上限：96（已修）/ 400（FXBAND）/ 18（ZMNOTIFY）。**

**⇒ 而 `400` 对一个"带里有几百个"的情况**可能也截断**。**

**⚠ 与这里的教训**矛盾**。**

### 2.4 而 `zm animband` 的**四个量**

```php
"zm animband map=" + mapName + " total=" + animBand.size() +
" zombie=" + zmAnimNames.size() +
" tearAnim=" + (zmTearAnim ? *zmTearAnim : "UNRESOLVED")
```

**⇒ 三个 + 一个可能 UNRESOLVED。**

### 2.5 而 "UNRESOLVED, keeping 476"

```php
" walkAnim=" + (zmWalkAnim ? std::to_string(*zmWalkAnim)
                           : std::string("UNRESOLVED, keeping 476"))
```

**⇒ 三层**：

```text
1. 解析失败 ⇒ 保留 **476**
2. 而 476 是 `ai_zombie_boardtear_l_1`（§296）
3. ⇒ 所以"僵尸永远在撕板子"是**失败的回退**
```

**✓ 明说"keeping 476"** —— 所以读者立刻知道是回退。

### 2.6 而**决定性的一行**

```php
// The one line that matters when zombies do not move: a table that
// exists but a graph that does not means the loaded map's nodes did
// not match it, and every actor will park.
(zmNavTable && zmNavNodes == 0
     ? " REJECTED (map nodes do not match the table)"
     : "")
```

**⇒ 三层**：

```text
1. **当僵尸不动时唯一重要的一行**
2. 表存在而图不存在 ⇒ 加载地图的节点与它不匹配
3. ⇒ **每个 actor 都会停住**
```

**✓ 一个精确的诊断信号。**

## 三、`zm navgraph` 的**九个量**

```php
"zm navgraph map=" + mapName + " table=" + (zmNavTable ? "yes" : "none") +
" nodes=" + zmNavNodes + " edges=" + zmNavEdges +
" source=" + (navSource == Bo1Hybrid ? "bo1_hybrid" : "codol_recovered") +
" referenceNodes=" + zmNavGraph.referenceNodes +
" referenceEdges=" + zmNavGraph.referenceEdgesAccepted + "/" + zmNavGraph.referenceEdgesConsidered +
" vaults=" + zmNavVaults +
" walkAnim=" + ...
```

### 3.1 九个

```text
table                    yes / none
nodes / edges
source                   bo1_hybrid / codol_recovered
referenceNodes
referenceEdgesAccepted / referenceEdgesConsidered
vaults
walkAnim
```

### 3.2 而"期望 Factory 上全部 53 个"

```php
// How many negotiation edges got a playable animation. Expect all 53
// on Factory: the demo identifies `zombie_mantle_over_40` as the
// slow `ai_zombie_traverse_v6` sequence.
```

**⇒ 三个**：

```text
53 条协商边
`zombie_mantle_over_40`
`ai_zombie_traverse_v6`（慢序列）
```

### 3.3 而**`referenceEdgesAccepted / referenceEdgesConsidered`**

**⇒ 所以"参考边"有一个接受/考虑比。**

**⇒ 与 §258 的玻璃、§295 的 zone volume 同族**（"接受数/总数"）。

## 四、**`36 = 2 × 18` 的模型槽**（本组第二重要）

### 4.1 那段完整论证

```php
// An add-on campaign map owns its map entities in a separate fastfile.
// Those entities can name XModels which are resident in the add-on but
// absent from the base multiplayer model configstring band. The client
// still needs a band index for every script_model we publish. Reserve
// empty slots before resolving the entity list so the existing live model
// publisher can assign and precache those campaign models. Wetwork has
// eight unique script-model names.
//
// SIZED FOR THE WHOLE ROSTER, NOT FOR EIGHT PLAYERS. The character publisher
// takes TWO slots per player -- the `fpa_` body AND the `han_` viewhands --
// and the roster is MaximumGameClients wide, so the roster alone needs
// 2 * 18 = 36. The previous cap of sixteen therefore ran out after eight
// players: player nine resolved a body model name correctly and then had
// nowhere to publish it, which the log states twice over --
//     body model COULD NOT BE PUBLISHED name=fpa_copveterana_tf_m_00
//     character body published INTO THE GAMESTATE name=... -- NO BAND SLOT
// and the observer then received `body0` for that slot, which is an EMPTY
// model name, which is a player nobody can see. Sixteen more keep the map's
// own script models covered exactly as before, so this is never worse for
// the script-model path that fails the whole spawn when it runs out.
```

### 4.2 八层

```text
1. **一个附加战役地图在单独的 fastfile 里拥有它的地图实体**
2. 那些实体可以命名**在附加里常驻而在基础 MP 模型带里缺席**的 XModel
3. ⇒ 客户端仍需要**每一个我们发布的 script_model** 的带索引
4. ⇒ 在解析实体列表**之前**预留空槽
5. **按整个名册定尺寸，不是按八个玩家**
6. 角色发布器每人拿**两个槽** —— **`fpa_` 身体** 与 **`han_` viewhands**
7. 名册是 `MaximumGameClients` 宽 ⇒ **2 × 18 = 36**
8. ⇒ **旧的 16 上限在八个玩家后耗尽**：第九个玩家正确解析了身体模型名而**没有地方发布它**
```

### 4.3 而**两条日志证词**

```text
body model COULD NOT BE PUBLISHED name=fpa_copveterana_tf_m_00
character body published INTO THE GAMESTATE name=... -- NO BAND SLOT
```

**⇒ 两条日志说明同一件事（**双层记录**）。**

### 4.4 而**后果链**

```text
1. 发布失败 ⇒ observer 收到 `body0`
2. `body0` 是一个**空模型名**
3. ⇒ **一个没人能看到的玩家**
```

**⇒ 与 §255 的 `NULL`/`EMPTY`/`UNREADABLE` 同族**（`body0` 是"空"的那一态）。

### 4.5 而"十六个更多保持地图自己的 script model 覆盖"

```text
36 = 2 × 18          角色
16                   script model 的预留
⇒ 52                 总预留
```

**⇒ 而"对这个耗尽时会失败整个 spawn 的 script-model 路径**永远不会更差**"。**

**✓ 一个正确的最小增量。**

### 4.6 而实现

```cpp
constexpr size_t CharacterModelSlotsPerPlayer = 2;
constexpr size_t ScriptModelSlotReserve = 16;
constexpr size_t ModelSlotReserve = 2 * MaximumGameClients + 16;    // = 52

const auto band = Bindings.modelConfigStringBand();
std::set<uint16> used;
for (const auto &[index, name] : band) used.insert(index);
std::vector<uint16> free;
for (uint16 index = 1; index < ModelConfigStringCount && free.size() < ModelSlotReserve; ++index)
    if (!used.contains(index)) free.push_back(index);
Server.setOutfitModelSlots(std::move(free));
```

### 4.7 四项

```text
① 收集已用索引（从 band）
② 从 1 开始找空槽
③ 直到 52 个
④ `setOutfitModelSlots`
```

**⇒ 与 §287 的"记录已占用的槽"同族。**

### 4.8 而"Wetwork 有八个唯一的 script-model 名字"**

**⇒ 8 < 16 ⇒ 所以 16 的预留对 Wetwork 够。**

**⇒ 而 8 是**实测**。**

## 五、`sd` 炸弹的三个触发器（本组第三重要）

### 5.1 五个阶段

```php
if (request->gameType == "sd")
{
    const auto bombSites = SV_SelectSdBombSites(*entities);
    const auto bombPickup = SV_SelectSdBombPickup(*entities);
    if (!bombSites || !bombPickup) { reportFailure("sd_bomb_object_select"); return; }

    sdBombPickup = *bombPickup;
    const auto pickupCollision = Bindings.resolveBrushModelCollision(bombPickup->triggerModel);
    if (!pickupCollision) { reportFailure("sd_bomb_pickup_resolve"); return; }

    const SvTriggerVolume pickupTrigger{ .objectId, .origin, .collision };

    std::vector<SvSdBombSiteRuntime> siteRuntime;
    for (const auto &site : *bombSites)
    {
        const auto plantCollision  = resolveBrushModelCollision(site.triggerModel);
        const auto defuseCollision = resolveBrushModelCollision(site.defuseTriggerModel);
        if (!plantCollision || !defuseCollision) { reportFailure("sd_bomb_trigger_resolve_" + site.label); return; }
        siteRuntime.push_back({ .label, .plantTrigger, .defuseTrigger });
    }
    if (!Server.configureSdBombRuntime(*bombSites, pickupTrigger, siteRuntime))
    { reportFailure("sd_bomb_runtime_commit"); return; }
}
```

### 5.2 四种触发器

```text
pickup          炸弹拾取
plant           安放（每个 site）
defuse          拆解（每个 site）
```

**### 5.3 而阶段名的四种**

```text
sd_bomb_object_select
sd_bomb_pickup_resolve
sd_bomb_trigger_resolve_<label>
sd_bomb_runtime_commit
```

**⇒ 四种，且第三个**带 site label**。**

**✓ 与 §284 的 `failedClassIndex` 同族（定位到具体实例）。**

### 5.4 而 `resolveBrushModelCollision` 是 §262 的函数

**⇒ 用 `clipHandle` 索引 `collisionMap` 的 `models`。**

**⚠ 而 §295 说"`?N` 索引 `MapEnts.trigger` 而 `cmodel` 索引 clipmap"** ⇒ 两套索引。**

**⇒ 所以这里用 `triggerModel` 索引 `resolveBrushModelCollision` —— **是不是同一个错**？**

**⚠ 而 §262 的 `resolveBrushModelCollision(clipHandle)` 明确叫 `clipHandle`。**

**⇒ 而这里传 `bombPickup->triggerModel`。**

**⇒ 如果 `triggerModel` 是 `?N` 空间则**错误**；如果是 `clipHandle` 空间则正确。**

**⇒ 命名 `triggerModel` 暗示 `?N` 空间。**

**⚠ 这是**第三处**需要核对的索引空间问题。**

## 六、`brushModels` 的**十个字段**

```cpp
brushModels.push_back({
    .mapOrdinal, .walkEntityNum, .origin, .angles, .collision,
    .scriptGameObjectName, .targetName, .destructibleType,
    .mapModeEligible, .gameplayActive,
});
```

### 6.1 十个

```text
mapOrdinal              地图序号
walkEntityNum           遍历实体号
origin / angles
collision
scriptGameObjectName
targetName
destructibleType
mapModeEligible
gameplayActive
```

### 6.2 而 `gameplayActive` 的**三个条件**

```cpp
const auto gameplayActive = brushSpawn.regularMultiplayerEligible &&
    brushSpawn.scriptGameObjectName.empty();
```

**⇒ 两个条件**：

```text
regularMultiplayerEligible   在普通 MP 里合格
scriptGameObjectName 为空      没有脚本对象名
```

### 6.3 而那段

```php
// OLMOD(entity-publication-bootstrap): this combines current map
// eligibility with recovered serializer coverage. It is not the
// missing CODOL gentity in-use/SVF_NOCLIENT producer.
```

**⇒ 三层**：

```text
1. 这**组合**了当前地图资格与恢复的序列化覆盖
2. 它**不是**那个缺失的 CODOL `gentity` in-use / `SVF_NOCLIENT` **生产者**
3. ⇒ 所以这是一个**近似**而不是原版逻辑
```

**✓ 与 §295 的"临时"标注同族**（第七次"标注近似"）。

### 6.4 而 `destructibleType` 与 §148 的"destructible (IW4 subset only)"

**⇒ 相关但待读。**

## 七、`scriptModels` 的**两路模型索引**

```php
auto modelIndex = Bindings.resolveModelConfigStringIndex(scriptModelSpawn.modelName);
if (!modelIndex)
    modelIndex = Server.registerOutfitModelConfigString(scriptModelSpawn.modelName);
if (!modelIndex) { reportFailure("script_model_index_" + modelName); return; }
```

### 7.1 三层

```text
① 先在已有带里查
② 查不到 ⇒ 从【预留的空槽】分配
③ 仍失败 ⇒ 整个世界失败
```

**⇒ 所以 ② 正是 §4 里那 52 个预留槽的**用途**。**

**✓ 两段完全配套。**

### 7.2 而 ③ 是**致命的**

**⇒ 与 §299 开头的"script-model 路径耗尽时会失败整个 spawn"**完全一致** ✓

### 7.3 而 `gameplayActive` 在 script model 里**同样两个条件**

```cpp
const auto gameplayActive = scriptModelSpawn.regularMultiplayerEligible &&
    scriptModelSpawn.scriptGameObjectName.empty();
```

**⇒ 与 brush model 的定义**完全相同**。**

**✓ 一致性。**

## 八、关键结论

1. **"分块不截断"** —— 96 的上限丢掉了 walk/attack/death/taunt 而**花掉一个周期**。
2. **而本文件里仍有 400（FXBAND）与 18（ZMNOTIFY）的截断** —— 与这个教训**潜在矛盾**。
3. **"UNRESOLVED, keeping 476"** —— 明确标注回退。
4. **"表存在而图不存在 ⇒ 每个 actor 都会停住"** —— 唯一重要的一行。
5. **53 条协商边**、`zombie_mantle_over_40` 与 `ai_zombie_traverse_v6`。
6. **`referenceEdgesAccepted / Considered`** 的接受比。
7. **`36 = 2 × 18`**（每人 2 槽：`fpa_` 身体 + `han_` viewhands）× 名册宽。
8. **旧的 16 上限在八个玩家后耗尽** ⇒ 第九个玩家的身体发布失败。
9. **`body0` 是空模型名 ⇒ 一个没人能看到的玩家**。
10. **16 的 script model 预留 ⇒ 总 52**，且"永远不会更差"。
11. **Wetwork 有 8 个唯一 script-model 名字**（实测）。
12. **`sd` 的四种触发器**（pickup / plant / defuse / runtime commit）与四个阶段名。
13. **`sd_bomb_trigger_resolve_<label>`** 带 site label。
14. **⚠ `resolveBrushModelCollision(triggerModel)` 可能又是一处索引空间混淆**（第三处）。
15. **`gameplayActive` 用两个条件**（`regularMultiplayerEligible` + `scriptGameObjectName` 为空）。
16. **"不是那个缺失的 CODOL `gentity` in-use/`SVF_NOCLIENT` 生产者"** —— 明确标注近似。
17. **`scriptModels` 的两路索引**（已有带 → 预留槽 → 失败），与 §4 的 52 槽**完全配套**。

## 九、未闭合点

- FXBAND 的 400 与 ZMNOTIFY 的 18 是否会丢掉重要项。
- `resolveBrushModelCollision(triggerModel)` 的索引空间。
- `destructibleType` 的语义。
- `Appmain.cpp` 6540 行之后未读取。
