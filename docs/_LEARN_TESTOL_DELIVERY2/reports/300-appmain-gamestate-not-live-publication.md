# 300 · **"body418 送到两个观察者而一个客户端仍写了空模型名"**、两次失败的 actor 模型发布、`han_` 的缺失

## 一、范围

本报告学习 `Appmain.cpp` 6540–6760 行。

## 二、`scriptModels` 的**十二个字段**

```cpp
scriptModels.push_back({
    .mapOrdinal, .walkEntityNum, .origin, .angles,
    .modelIndex, .modelName, .scale,
    .scriptGameObjectName, .targetName, .destructibleType,
    .mapModeEligible, .gameplayActive, .noteworthy,
});
```

**⇒ 十三个（含 `noteworthy`）。**

### 2.1 而 `scale` 在 script model 有而 brush model 没有

**⇒ 因为 brush model 是固定的几何。**

## 三、**可破坏物的三个资源**

```cpp
const auto *const destructible = gameplayActive
    ? SV_FindIw4DestructibleDefinition(scriptModelSpawn.destructibleType)
    : nullptr;
if (destructible)
{
    auto presentation = SV_ResolveDestructiblePresentation(*destructible,
        [](modelName) { return Bindings.resolveModelConfigStringIndex(modelName); });
    const auto initialState = SV_InitializeDestructibleDamageState(*destructible);
    if (!initialState || !presentation)
    { reportFailure("destructible_owner_" + destructible->type); return; }
    scriptModelDamageOwners.push_back({
        .scriptModelIndex = scriptModels.size() - 1,     // ← 【刚 push 的那个】
        .state = *initialState,
        .handler = [destructible, presentation = move(*presentation)](payload, state, modelIndex) {
            return SV_ApplyDestructibleEntityDamage(*destructible, presentation, payload, state, modelIndex);
        },
    });
}
```

### 3.1 三项

```text
定义        SV_FindIw4DestructibleDefinition(destructibleType)
表现        SV_ResolveDestructiblePresentation（注入模型解析器）
初始状态    SV_InitializeDestructibleDamageState
```

### 3.2 而 `scriptModelIndex = scriptModels.size() - 1`

**⇒ 因为刚 push 过 ⇒ 所以索引是最后一个。**

**⚠ 一个**脆弱**的依赖 —— 如果中间插入了 push 就会错。**

**⇒ 但从代码看 push 与这里是连续的。**

### 3.3 而 `handler` 是**一个捕获所有依赖的 lambda**

**⇒ `destructible`（指针）+ `presentation`（move 进来的值）。**

**⇒ 所以"损坏处理器"完全自包含。**

**✓ 一个干净的回调设计。**

### 3.4 而 `presentation` 被 **move 捕获**

```cpp
presentation = std::move(*presentation)
```

**⇒ 因为 lambda 必须拥有它（`optional` 的值被移入）。**

**⚠ 而 `presentation` 是 `optional<...>` 而 move 的是 `*presentation`（即值本身）。** ✓

### 3.5 而"只有 `gameplayActive` 时才查定义"

**⇒ 所以一个非游戏激活的 script model 不注册损坏处理。**

**✓ 与 `gameplayActive` 的语义一致。**

## 四、**`top_players_camera` 的"缺席不是错误"**（本组第二重要）

```php
// THE END-OF-MATCH CAMERA IS A MAP ENTITY (section 121). Absent is not
// an error -- a map with no `top_players_camera` keeps the pm_type-only
// intermission it had before -- so this logs which it was and moves on.
auto topPlayersCamera = SV_SelectTopPlayersCamera(*entities);
if (topPlayersCamera)
{
    Server.setTopPlayersCamera(SvWorldSpawnPoint{ .origin, .angles });
    logGameServer("top_players_camera " + mapName + " origin x,y,z angles p,y,r");
}
else
{
    Server.setTopPlayersCamera(std::nullopt);
    logGameServer("no top_players_camera in " + mapName + " -- the end-of-match view will not move");
}
```

### 4.1 三层

```text
1. 比赛结束摄像机是一个**地图实体**
2. **缺席不是错误** —— 没有它的地图保持之前的**仅 pm_type 的中场**
3. ⇒ 所以记录哪一种并继续
```

### 4.2 而两句日志都**明说后果**

```text
有  ⇒ "origin ... angles ..."
无  ⇒ "the end-of-match view will not move"
```

**✓ 与 §236/§244 的"降级但明说"同族。**

### 4.3 而 `SV_SelectTopPlayersPlaces` 的**领奖台位置**

```cpp
auto places = SV_SelectTopPlayersPlaces(*entities);
std::vector<SvWorldSpawnPoint> podiumPlaces;
for (const auto &place : places)
    podiumPlaces.push_back({ .origin = place.origin, .angles = place.angles });
logGameServer("top_players_loc " + mapName + " places=" + podiumPlaces.size());
Server.setTopPlayersPlaces(std::move(podiumPlaces));
```

**⇒ 无 `if` —— 空 vector 也设置。**

**⇒ 因为"0 个位置"是合法答案。**

**✓ 与 §292 的"空图也发布"同族。**

## 五、**8 个角色前缀**（本组第三重要）

```php
// The character families, by the slot prefixes section 67 named:
// cha fpa boo fja han hea ves heg.
const auto isCharacter =
    name.rfind("fpa_", 0) == 0 || name.rfind("cha_", 0) == 0 ||
    name.rfind("boo_", 0) == 0 || name.rfind("fja_", 0) == 0 ||
    name.rfind("han_", 0) == 0 || name.rfind("hea_", 0) == 0 ||
    name.rfind("ves_", 0) == 0 || name.rfind("heg_", 0) == 0;
```

### 5.1 八个前缀

```text
fpa_    身体（female player actor?）
cha_    角色
boo_    ？
fja_    ？
han_    viewhands
hea_    头？
ves_    ？
heg_    ？
```

**⇒ 而 §299 说"角色发布器每人拿两个槽 —— `fpa_` 身体与 `han_` viewhands"，与这里一致** ✓

### 5.2 而 `sample` 的 **1200 字符上限**

```cpp
if (sample.size() < 1200)
    sample += " " + std::to_string(index) + ":" + name;
```

**⇒ 与 §299 的"分块不截断"**矛盾**！**

**⚠ 这里用**1200 字符上限**而 §299 刚刚批评了截断。**

**⇒ 但这里是**采样**（"sample"）而 §299 是**完整列表**。**

**✓ 命名 `sample` 承认了这一点。**

## 六、`podiumFallbackModel` 的**取第一个 `fpa_`**

```php
// THE GENERIC BODY. mp_rust_long publishes exactly one model per
// character slot at indices 2..6 -- boo/fja/fpa/han/hea -- which is
// the map's own default character. The `fpa_` one is the body, and
// it is what a podium figure falls back to when the band does not
// publish that player's own (section 125).
for (const auto &[index, name] : band)
{
    if (name.rfind("fpa_", 0) != 0) continue;
    Server.setPodiumFallbackModel(index, name);
    logGameServer("podium fallback body " + index + ":" + name);
    break;
}
```

### 6.1 四层

```text
1. `mp_rust_long` 在索引 2..6 **每个角色槽恰好发布一个模型** —— boo/fja/fpa/han/hea
2. ⇒ 那是地图**自己的默认角色**
3. `fpa_` 那个是**身体**
4. ⇒ 而它是领奖台人物在带里没有发布该玩家自己的时的**回退**
```

### 6.2 而"索引 2..6"与 §299 的"从 1 开始找空槽"

**⚠ 索引 1 不用 ⇒ 与 §259/§260 的"`index = 1` 开始"**不同**。**

**⇒ §299 是"从 1 开始找**空**槽"而这里是"索引 2..6 是**已占用**的"。**

**✓ 不矛盾。**

## 七、**"发布到 gamestate 而不是 live"**（本组最重要的一段）

### 7.1 那段完整论证

```php
// AND PUBLISH EVERY ROSTERED CHARACTER'S BODY MODEL RIGHT HERE, INTO THE
// GAMESTATE. Section 168.
//
// The body model at clientState +0x14 is only useful if the client can
// RESOLVE that index, and it resolves it through configstring
// 2568 + index. Registering it from the customization provider publishes it
// LIVE, after every client already holds its gamestate -- so a client only
// learns it from a reliable command arriving while it is loading a map, and
// one measurably does not end up with it: the wire carried body418 in every
// write to both observers, `cs 2986 fpa_goose_ss_m_15` is in one client's
// demo, and the other still wrote an EMPTY model name.
//
// This runs during world configuration, BEFORE gameStateConfigured_ lets any
// gamestate go out, so the band entry is part of the gamestate every client
// receives and there is no live delivery to miss.
```

### 7.2 七层

```text
1. `clientState +0x14` 的 body model **只有在客户端能解析那个索引时才有用**
2. 而它通过**配置串 `2568 + index`** 解析
3. 从定制 provider 注册它 ⇒ **LIVE 发布**，在每个客户端**已持有其 gamestate 之后**
4. ⇒ 一个客户端只从**在地图加载时到达的可靠命令**学到它
5. 而**一个实测地没有拿到它**：
     · 线上对**两个**观察者的每次写都携带 `body418`
     · `cs 2986 fpa_goose_ss_m_15` 在**一个**客户端的 demo 里
     • 而**另一个仍写了空模型名**
6. ⇒ 这在世界配置期间跑，**在 `gameStateConfigured_` 让任何 gamestate 出去之前**
7. ⇒ 所以带条目是**每个客户端收到的 gamestate 的一部分**，没有 live 投递可错过
```

### 7.3 **"线上对两个观察者的每次写都携带 `body418` 而一个客户端仍写了空模型名"**

**⇒ 这是整个文件里**最精确的一次不一致观测**。**

**⇒ 同一个 `body418` 送到**两个**客户端，**一个**解析出 `cs 2986 fpa_goose_ss_m_15` 而**另一个**空。**

**⇒ 所以**不是"没送到"而是"送到了但一个没解析"。**

**⚠ 一个**客户端特定的**差异。**

**⇒ 可能与 §255 的 `NULL`/`EMPTY`/`UNREADABLE` 三态**相关**。**

### 7.4 而 `cs 2568 + index` 与 §256 的 `ModelConfigStringBase`

**⇒ 记忆里"`2568` models"。**

**⇒ 所以 `ModelConfigStringBase = 2568`。**

**⚠ 而 §299 的 `ModelConfigStringCount` 与 §259 的"up to 1024"⇒ 2568 + 1..1023。**

**⇒ 与 §296 的"`316 nodes`"无关。**

### 7.5 那句"隔壁的 outfit 注释已经说了真答案是**一次 GAMESTATE 变更，不是每 spawn 一次**"

**⇒ 所以这个设计是**早先论证的落地**。**

### 7.6 而实现

```cpp
{
    const std::lock_guard lock(LoadoutMutex);
    std::set<std::string> published;
    for (const auto &[memberXuid, member] : RegisteredSessionAssets.members())
    {
        const auto &presentation = member.characterPresentation;
        if (presentation.characterItemId == 0) continue;                    // ①
        SvCharacterCustomization probe{};
        probe.characterItemId = presentation.characterItemId;
        probe.recordItemIds = presentation.recordItemIds;
        probe.recordItemIds[0] = probe.characterItemId;                     // ②
        for (const auto &name : Bindings.characterResolvedModelNames(probe))
        {
            const auto isBody  = name.rfind("fpa_", 0) == 0;
            const auto isHands = name.rfind("han_", 0) == 0;
            if (!isBody && !isHands) continue;                               // ③
            if (published.contains(name)) continue;                           // ④
            published.insert(name);
            if (Bindings.resolveModelConfigStringIndex(name)) continue;       // ⑤ 已在带里
            const auto index = Server.registerOutfitModelConfigString(name);
            logGameServer((isBody ? "character body" : "character hands") +
                " published INTO THE GAMESTATE name=" + name +
                (index ? " index=" + *index : " -- NO BAND SLOT") +
                " xuid=" + memberXuid);
        }
    }
}
```

### 7.7 五项

```text
① 跳过无角色物品的成员
② 【强制 recordItemIds[0] = characterItemId】
③ 只要 body 或 hands
④ 按名字去重（跨成员）
⑤ 已在带里 ⇒ 跳过
```

### 7.8 而 ② 的**强制覆盖**

```cpp
probe.recordItemIds[0] = probe.characterItemId;
```

**⇒ 因为"entry 0 携带角色"（§283）⇒ 所以即使 `recordItemIds[0]` 是 0 也补上。**

**✓ 与 §283 的 `recordItemIds[0] = characterItemId` 一致。**

### 7.9 而 `" -- NO BAND SLOT"` 是 §299 里的那条日志

**⇒ 所以 §299 引用的两条日志**就在这里产生**。**

**✅ 闭环。**

## 八、**`han_` 在 `mp_nuked` 不发布**

```php
// THE BODY AND THE HANDS. `han_` is the character's own viewhands
// and mp_nuked does not publish it -- `viewhands: character hands
// NOT IN BAND name=han_infbasea_tf_m_00` -- which is the only
// reason a player still wears tf141's. Same band, same gamestate,
// same two-step; nothing about it is body-specific.
```

### 8.1 四层

```text
1. `han_` 是角色**自己的 viewhands**
2. 而 `mp_nuked` **不发布**它
3. ⇒ `viewhands: character hands NOT IN BAND name=han_infbasea_tf_m_00`
4. ⇒ 而这**就是一个玩家仍穿着 tf141 的手的唯一原因**
```

### 8.2 而"tf141"与 §256 的 `GenericCharacterViewhands`

**§256**："按固定 tf141 名解析一个 CCS 索引"

**⇒ 所以 `GenericCharacterViewhands` = 一个 **tf141** 的 viewhands。**

**⇒ 而如果 `han_` 不在带里 ⇒ 用 tf141 的 ⇒ **玩家看到 tf141 的手**。**

**✅ 两处完全对上。**

### 8.3 而 `viewhands: character hands NOT IN BAND` 这条日志

**⇒ 在别处产生**（不在这一行）。**

**⇒ 所以这是**第三处**记录同一现象。**

## 九、**两次失败的 actor 模型发布**（本组第四重要）

```php
// NO ACTOR-MODEL PUBLISH HERE. Two attempts, both of which broke the
// session -- see re/demo-re/20-zm-actor-lifecycle.md 12.21/12.22.
//
// 1. Publishing at first-zombie-spawn: a LIVE configstring change after
//    clients hold their gamestate. Client could not enter at all
//    (无法加入游戏会话), reproduced twice.
// 2. Publishing here at world configuration, driven off the map's own
//    actor_* entities: the client TIMED OUT a few seconds in
//    (`client timeout ... last_packet=`, snapshots stopped at 141).
//    AND IT PUBLISHED THE WRONG MODELS. The map's actor entities name
//    c_zom_juggernaut_body_RED, c_zom_ger_body_YEL and zombie_wolf --
//    only zombie_wolf is even in the dedicated band (index 409) -- while
//    zm.lua spawns c_zom_ger_body1 (index 308), which is NOT named by any
//    actor_* entity. So the map entities are the wrong source for this.
```

### 9.1 两次与四个后果

```text
① 在首只僵尸 spawn 时发布 ⇒ LIVE 配置串变更 ⇒ **客户端完全进不去**（无法加入游戏会话），复现两次
② 在世界配置这里发布（用地图的 actor_* 实体）⇒
     · 客户端**几秒后超时**（`client timeout ... last_packet=`）
     • **快照停在 141**
     · **而且发布了错误的模型**
```

### 9.2 而"错误的模型"的三个对比

```text
地图 actor_* 实体命名    c_zom_juggernaut_body_RED
                        c_zom_ger_body_YEL
                        zombie_wolf            ← 【只有它在专用服带里，索引 409】
zm.lua 实际 spawn        c_zom_ger_body1        ← 【索引 308，不被任何 actor_* 命名】
```

**⇒ 所以"地图实体是这件事的错误来源"。**

### 9.3 而**"快照停在 141"**

**⇒ 与 §244/§258 的"141 字节"**是否同一个 141？**

**⚠ 记忆里"141 字节 = 真 Python 参照的首帧 = 让客户端卡住的那一份"。**

**⇒ 而这里是"快照停在 **141**" —— 可能是**快照序号**而不是字节数。**

**⚠ 两个不同的 141。**

### 9.4 而"复现两次"与"几秒后超时"

**⇒ 两次实验的**不同失败模式**：**

```text
① 完全进不去
② 进去后几秒超时
```

**⇒ 所以是**不同的**破坏方式。**

**✓ 而这个注释把两者都记录了。**

## 十、关键结论

1. **`scriptModels` 十三个字段**（比 brush model 多 `scale` 与 `noteworthy`）。
2. **可破坏物的三项资源**，而 `handler` 是自包含的 lambda。
3. **`scriptModelIndex = size() - 1`** 是脆弱但连续的依赖。
4. **"`top_players_camera` 缺席不是错误"**，且**两句日志都明说后果**。
5. **领奖台位置"0 个"是合法答案**（空 vector 也设置）。
6. **8 个角色前缀**（`fpa_`/`cha_`/`boo_`/`fja_`/`han_`/`hea_`/`ves_`/`heg_`）。
7. **`sample` 的 1200 字符上限**与 §299 的"分块不截断"**潜在矛盾**，但名字 `sample` 承认了。
8. **`mp_rust_long` 在索引 2..6 发布 boo/fja/fpa/han/hea 五个**。
9. **"发布到 gamestate 而不是 live"** —— 因为 live 投递会错过。
10. **"线上对两个观察者的每次写都携带 `body418` 而一个客户端仍写了空模型名"** —— 最精确的不一致观测。
11. **`cs 2568 + index` 是模型配置串的解引用路径** ⇒ `ModelConfigStringBase = 2568`。
12. **`recordItemIds[0] = characterItemId` 的强制覆盖**。
13. **`" -- NO BAND SLOT"` 就是 §299 引用的那条日志** —— 闭环。
14. **`han_` 在 `mp_nuked` 不发布 ⇒ 玩家穿着 tf141 的手**。
15. **`GenericCharacterViewhands` = tf141 的 viewhands** —— 与 §256 对上。
16. **两次失败的 actor 模型发布**：
    - live 变更 ⇒ **完全进不去**（复现两次）
    - 世界配置用 actor_* 实体 ⇒ **几秒超时** + **发布错误模型**
17. **"地图实体是这件事的错误来源"** —— 因为 `zm.lua` spawn 的 `c_zom_ger_body1` 不被任何 `actor_*` 命名。
18. **"快照停在 141"** 可能与记忆里的"141 字节"是**两个不同的 141**。

## 十一、未闭合点

- "快照停在 141"是序号还是字节。
- `ves_`/`heg_`/`hea_`/`boo_`/`fja_` 各自的语义。
- `ModelConfigStringBase = 2568` 的确认。
- `Appmain.cpp` 6760 行之后未读取。
