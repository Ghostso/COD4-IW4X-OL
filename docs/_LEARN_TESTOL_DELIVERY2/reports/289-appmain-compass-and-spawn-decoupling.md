# 289 · **"指南针与出生列表无关"**、244 个 fastfile 里没有基础 MP 实体串、sd 的八个路点

## 一、范围

本报告学习 `Appmain.cpp` 4115–4340 行。

## 二、三个语音覆盖的**五层**

```php
std::optional<uint16> chosen = value;
if (overrideName)
{
    char *raw{}; size_t rawSize{};
    if (_dupenv_s(&raw, &rawSize, overrideName) == 0 && raw)
    {
        const auto parsed = std::atoi(raw);
        std::free(raw);
        if (parsed > 0 && parsed < 0x4000)
            chosen = (uint16)parsed;
    }
}
if (!chosen) chosen = request.fallback;
*request.slot = chosen;
```

### 2.1 五层

```text
① CCS 解析（`value`）
② 环境变量覆盖（`chosen = parsed`）
③ `parsed > 0 && parsed < 0x4000` 的界
④ 常量回退（`request.fallback`）
⑤ 写入 slot
```

### 2.2 **`atoi` 是第 N 种宽松解析**

```text
"1277abc"  ⇒ 1277    ← 【接受】
"abc"      ⇒ 0       ⇒ 被 `parsed > 0` 拒绝
"-5"       ⇒ -5      ⇒ 被拒绝
```

**⚠ 而 `0x4000 = 16384`** —— 与 §261 的 `16384` 上界一致。

### 2.3 而三层优先级的**顺序**

```text
环境变量 > CCS 解析 > 常量回退
```

**⇒ 与 §288 的注释"override wins over both the CCS answer and the constant"一致** ✓

### 2.4 而日志的**两种形态**

```php
"announcer voice " + name + " eventParameter=" +
(value ? std::to_string(*value)
       : "UNRESOLVED (fallback " + std::to_string(request.fallback) + ")")
```

**⚠ 日志打印的是 `value`（CCS 结果）而**不是 `chosen`（实际用的值）**。**

**⇒ 所以如果环境变量覆盖了，日志**不会显示覆盖值**。**

**⚠ 一处诊断缺陷** —— "用了什么"没有记录。

## 三、`damage feedback` 的三项日志

```php
"damage feedback material=" + (damageFeedbackMaterial ? N : "unavailable") +
" killMaterial=" + (... ? N : "unavailable") +
" sound=" + (... ? N : "unavailable")
```

**⇒ 三项，各自可用或 unavailable。**

**⇒ 与 §261 的"`material=125 killMaterial=144`"**同一个日志** ✓

**⇒ 所以那次实测的三个值在这里产生。**

## 四、sd 的**八个路点材质**（本组第二重要）

```php
if (gameType == "sd")
{
    const auto targetA = resolveServerMaterialConfigStringIndex("waypoint_target_a");
    const auto targetB = resolveServerMaterialConfigStringIndex("waypoint_target_b");
    const auto defendA = resolveServerMaterialConfigStringIndex("waypoint_defend_a");
    const auto defendB = resolveServerMaterialConfigStringIndex("waypoint_defend_b");
    const auto defuseA = resolveServerMaterialConfigStringIndex("waypoint_defuse_a");
    const auto defuseB = resolveServerMaterialConfigStringIndex("waypoint_defuse_b");
    const auto bomb    = resolveServerMaterialConfigStringIndex("waypoint_bomb");
    const auto escort  = resolveServerMaterialConfigStringIndex("waypoint_escort");
    if (!targetA || !targetB || !defendA || !defendB || !defuseA || !defuseB || !bomb || !escort)
    {
        GameStateConfiguration.failed(ObjectiveMaterialUnavailable);
        return false;
    }
    ...
}
```

### 4.1 八个

```text
target_a / target_b     目标点
defend_a / defend_b     防守点
defuse_a / defuse_b     拆弹点
bomb                    炸弹
escort                  护送
```

### 4.2 而**八个全部必需**（`||` 链）

**⇒ 任一缺失 ⇒ 整个 gamestate 失败。**

**⚠ 相对 §284 的"一个坏职业跳过"这是**严格相反**的处理。**

**⇒ 但这是 gamestate 配置（不是玩家 loadout），所以严格是对的。**

## 五、**"指南针与出生列表无关"**（本组最重要的一段）

### 5.1 那段完整论证

```php
// MAP ENTITIES ARE READ FOR EVERY MAP THAT HAS A SCRIPT, not only those that
// carry a minimap. Spawn points come from this entity string and from nothing
// else, so gating it on miniMapMaterial silently made "this map has no compass"
// mean "this map has no spawns": configureWorldSpawn then failed on
// `initial_spawn_ground_trace`, and a client that got that far sat forever at
// NO_SPAWN_POINT with the map loaded around it.
//
// A compass and a spawn list are unrelated, and the coupling was an MP-only
// assumption. Zombies has no compass to name: none of the three retail
// zm_factory_sh demos emits a compass configstring while the retail dm gamestate
// does, and out.exe's only compass_map_* string is compass_map_awareness_radar
// @ 0xDB1D0C -- the per-map materials live in fastfiles and no zombies one
// exists. Those maps still need their spawns.
//
// MP maps are unaffected: mp_nuked and mp_crash_tropical both set
// miniMapMaterial, so both blocks below run for them exactly as before.
```

### 5.2 七层

```text
1. 有脚本的【每一张】地图都读 map entities，不只是有 minimap 的
2. 出生点【只】从这个实体串来
3. ⇒ 用 `miniMapMaterial` 门控它 ⇒ 静默地让"这张地图没有指南针"意味着"没有出生点"
4. ⇒ `configureWorldSpawn` 在 `initial_spawn_ground_trace` 失败
5. ⇒ 一个走到那一步的客户端**永远停在 `NO_SPAWN_POINT`**，而地图已经加载
6. ⇒ 指南针与出生列表【无关】，那个耦合是**仅 MP 的假设**
7. ⇒ 僵尸没有指南针可命名（三个零售 zm_factory_sh demo 都不发 compass 而 dm 发）
```

### 5.3 两个实测证据

```text
三个零售 zm_factory_sh demo   都不发 compass configstring
零售 dm gamestate             发
out.exe 唯一 compass_map_* 串  compass_map_awareness_radar @ 0xDB1D0C
```

**⇒ 而"每张地图的材质住在 fastfile 里而没有僵尸的"。**

### 5.4 而"MP 地图不受影响"

```text
mp_nuked            设 miniMapMaterial
mp_crash_tropical   设 miniMapMaterial
⇒ 两块都照旧跑
```

**⇒ 所以修法是**解耦**而不是"取消门控"。**

**✓ 一个精确的最小改动。**

### 5.5 而"`NO_SPAWN_POINT` 而地图已加载"

**⇒ 与 §257 的"一个渲染完整但玩家站不进去的地图"**几乎相同的症状**。**

**⇒ 两次都是"地图加载了但没有出生点"。**

## 六、**244 个 fastfile 里没有基础 MP 实体串**（本组第三重要）

```php
// Which spawn classes a CODOL map actually carries cannot be read
// offline - the base MP entity strings are in none of the 244
// shipped fastfiles, only coop/asym addons are - so report it
// from the live load rather than leaving the names assumed.
std::string census;
for (const auto &[className, count] : SV_SpawnClassNameCensus(*mapEntities))
    census += className + " x" + std::to_string(count);
logGameServer("map spawn classes " + mapName + " " + gameType + ": " + census);
```

### 6.1 三层

```text
1. 一张 CODOL 地图实际携带哪些出生类【无法离线读】
2. 因为基础 MP 实体串在【244 个随包 fastfile 里一个都没有】，只有 coop/asym 附加的
3. ⇒ 从【活加载】报告它而不是让名字被假定
```

### 6.2 而"244 个 fastfile"

**⇒ 与记忆里"974 个 .ifs 就是全部游戏内容"不同的数字**（244 vs 974）。

**⇒ 但 244 是**fastfile**（`.ff`）而 974 是 `.ifs` 容器。**

**✓ 两个不同的计数。**

### 6.3 而"只有 coop/asym 附加的"

**⇒ 所以基础 MP 的实体串**在哪里**？**

**⇒ 可能在 `.d3dbsp` 里（不是 `MapEnts` 资产）** ⇒ 而 §257 的 `readMapEntityString` 查 `maps/mp/<map>.d3dbsp`。

**⇒ 所以"基础 MP 实体串不在 fastfile 里"与"`AssetTypeMapEnts` 用 `.d3dbsp` 名"一致** ✓

## 七、minimap 的四项

```php
if (mapMetadata && mapMetadata->miniMapMaterial)
{
    const auto nativeNorthYaw = Bindings.readConfigString(NorthYawConfigStringIndex, 64);
    const auto northYaw = nativeNorthYaw
        ? (nativeNorthYaw->empty() ? std::optional{0.0f} : parseFiniteFloat(*nativeNorthYaw))
        : std::nullopt;
    const auto corners = mapEntities && northYaw
        ? SV_SelectMiniMapCorners(*mapEntities, *northYaw) : std::nullopt;
    if (!corners || !SV_SetMiniMapConfigStrings(gameState, *northYaw, {...}))
    {
        GameStateConfiguration.failed(MiniMapUnavailable);
        return false;
    }
}
```

### 7.1 四项

```text
① 读 native northYaw 配置串
② 【空串 ⇒ 0.0f】而不可读 ⇒ nullopt
③ SV_SelectMiniMapCorners(mapEntities, northYaw)
④ SV_SetMiniMapConfigStrings
```

### 7.2 **"空串 ⇒ 0.0f" 与 "不可读 ⇒ nullopt" 的区分**

**⇒ 与 §235 的 `readConfigString` 的"空串即合法"**完全一致** ✓

**⇒ 第四处"空串 vs 读不出"的区分。**

### 7.3 而 `parseFiniteFloat` 在这里第一次被用

**⇒ §277 学过 `parseFiniteFloat` 只去空格。**

**⇒ 所以配置串的值必须只是数字加空格。**

## 八、`PreparedLoadouts` 的**四项校验**

```php
{
    const std::lock_guard lock(LoadoutMutex);
    if (!PreparedLoadouts ||
        PreparedLoadouts->requestSequence != LoadoutPrepareRequestSequence ||
        PreparedLoadouts->members.empty() ||
        PreparedLoadouts->members.front().characterIndex != *currentCharacter)
    {
        GameStateConfiguration.failed(PreparedLoadoutMismatch);
        return false;
    }
    prepared = *PreparedLoadouts;
}
```

### 8.1 四项

```text
PreparedLoadouts 存在
requestSequence 【等于当前】      ← 【代际检查】
members 非空
第一个成员的 characterIndex 等于 currentCharacter
```

### 8.2 而"序列相等"是**防陈旧**

**⇒ 与 §282 的 `sameMapGeneration`、§265 的 `gEntities_` 指针同族**（第四次代际检查）。

## 九、`playerNames` 的**排序**

```php
std::vector<std::pair<uint64, std::string>> identities;
transform(prepared.members, back_inserter(identities),
    [](const auto &member) { return std::pair{member.xuid, member.username}; });
sort(identities, {}, [](const auto &identity) { return identity.first; });
gameState.playerNames.reserve(identities.size());
transform(identities, back_inserter(gameState.playerNames),
    [](const auto &identity) { return identity.second; });
SV_PopulateRequiredConfigStrings(gameState);
```

### 9.1 三层

```text
① 转成 (xuid, username) 对
② 【按 xuid 排序】
③ 只取 username
```

### 9.2 **按 xuid 排序而不是按加入顺序**

**⇒ 所以 playerNames 的顺序是**确定的**（不依赖到达顺序）。**

**✓ 一个重要的确定性要求** —— 因为服务端与客户端必须生成同样的 configstring。

**⇒ 与 §270 的"校验和错配"同族（任何不确定都会导致错配）。**

### 9.3 而 `SV_PopulateRequiredConfigStrings` **第二次调用**

**⇒ §287 里在 `configureGameStateImpl` 开头已调过一次。**

**⇒ 所以这里是在**填写了 playerNames 之后重新填充**。**

**⚠ 两次调用 —— 第二次应该包含第一次的内容。**

**⇒ 所以第一次的调用可能是**冗余**的。**

**⇒ 但也可能是"必须至少调一次，然后有玩家名再调一次"。**

## 十、`firstDynamicWeaponAssetIndex` 的**失败**

```php
const auto firstDynamicWeaponAssetIndex = Bindings.firstDynamicWeaponAssetIndex();
if (!firstDynamicWeaponAssetIndex)
{
    GameStateConfiguration.failed(DynamicWeaponRangeUnavailable);
    return false;
}
GameStateConfiguration.dynamicWeaponRange(*firstDynamicWeaponAssetIndex);
```

**⇒ 与 §236 的 "`first > count` 时返回空表"**不同**。**

**⇒ 这里 `nullopt` ⇒ **整个 gamestate 失败**。**

**⇒ 而 §236 的修法是"返回空表（合法）"。**

**⚠ 两层不一致** —— 里面返回空表而外面把 nullopt 当失败。

**⇒ 但从 §236 的代码看，`firstDynamicWeaponAssetIndex` 的内部已经改成"夹紧后返回空表"，所以这里的 `nullopt` 只在"真的错"时出现** ✓

## 十一、`coop_training_mp_cargoship` 的**湿活武器带**

```php
if (mapName == "coop_training_mp_cargoship" && gameType == "coop")
{
    std::string mapping;
    for (const auto &weapon : RecordedWetworkWeapons)
    {
        const auto registered = Bindings.registerModularWeaponConfigString(...);
```

**⇒ 所以 §285 的 51 条武器带**只**在 `coop_training_mp_cargoship` + `coop` 时注册。**

**⇒ 与那段注释"Wetwork's complete dynamic weapon band"一致** ✓

**⇒ 而"训练地图借用湿活的武器带"。**

## 十二、关键结论

1. **三个语音覆盖的五层**（环境变量 > CCS > 常量）。
2. **`atoi` 是又一宽松解析**，而 `0x4000` 与 §261 的 `16384` 一致。
3. **日志打印 `value` 而不是 `chosen`** ⇒ 覆盖值不显示 —— 一处诊断缺陷。
4. **`damage feedback material= killMaterial= sound=`** 三项 —— 与 §261 的实测同源。
5. **sd 的八个路点材质全部必需**（`||` 链 ⇒ 失败即整个 gamestate 失败）。
6. **"指南针与出生列表无关"** —— 耦合成"没有 minimap 就没出生点"⇒ `NO_SPAWN_POINT` 而地图已加载。
7. **三个零售 `zm_factory_sh` demo 都不发 compass 而 dm 发** —— 实测证据。
8. **修法是解耦而不是取消门控**（MP 地图照旧）。
9. **244 个 fastfile 里没有基础 MP 实体串**，只有 coop/asym 附加的。
10. **"空串 ⇒ 0.0f" vs "不可读 ⇒ nullopt"** —— 第四处该区分。
11. **`PreparedLoadouts` 的四项校验含代际检查**（第四次）。
12. **`playerNames` 按 xuid 排序** —— 确定性要求（否则客户端与服务端校验和错配）。
13. **`SV_PopulateRequiredConfigStrings` 被调用两次** —— 第一次可能冗余。
14. **`firstDynamicWeaponAssetIndex` 的 `nullopt` ⇒ 整体失败**，而内部已改成"返回空表"。

## 十三、未闭合点

- 日志不打 `chosen` 是否已知。
- `SV_PopulateRequiredConfigStrings` 两次调用的必要性。
- 基础 MP 实体串的确切来源（`.d3dbsp`？）。
- `Appmain.cpp` 4340 行之后未读取。
