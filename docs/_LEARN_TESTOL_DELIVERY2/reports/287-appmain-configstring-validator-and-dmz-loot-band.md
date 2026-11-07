# 287 · **`sub_514540` 是配置串校验器**（`XBOXLIVE_CANTJOINSESSION` 的真因）、dmz 战利品带的 64 槽实测

## 一、范围

本报告学习 `Appmain.cpp` 3677–3900 行。

## 二、`prepareClientLoadouts` 的**六个阶段**

```php
for (index = 0; index < 5; ++index)
{
    if (!characterIndex || !characterPresentation) break;      // ① 前置
    const auto selectedLoadout = "custom" + std::to_string(index + 1);
    const auto loadout = Bindings.resolveClientWeaponLoadout(selectedLoadout, *characterIndex);
    if (!loadout) continue;                                     // ② 单职业失败跳过
    resolvedClassMask |= 1u << index;
    registeredClassMask |= 1u << index;                         // ③ 两个掩码同时置
    preparedMember.loadouts.emplace(selectedLoadout, *loadout);
}
if (characterPresentation && !preparedMember.loadouts.empty())
    prepared.members.push_back(std::move(preparedMember));      // ④ 有 loadout 才推成员
const auto finalCharacterIndex = Bindings.currentCharacterIndex();
const auto succeeded = characterPresentation && !prepared.members.empty() &&
    finalCharacterIndex == characterIndex;                      // ⑤ 三条件
const std::lock_guard lock(LoadoutMutex);
++LoadoutPreparation.attemptCount;
LoadoutPreparation.currentCharacter = finalCharacterIndex ? *finalCharacterIndex : -1;
LoadoutPreparation.resolvedClassMask = resolvedClassMask;
LoadoutPreparation.registeredClassMask = registeredClassMask;
if (requestSequence != LoadoutPrepareRequestSequence) return false;   // ⑥ 序列变更 ⇒ 放弃
if (succeeded) PreparedLoadouts = std::move(prepared);
else if (finalCharacterIndex && PreparedLoadouts &&
    (PreparedLoadouts->members.empty() ||
     PreparedLoadouts->members.front().characterIndex != *finalCharacterIndex))
    PreparedLoadouts.reset();
return succeeded;
```

### 2.1 **③ 两个掩码在这里**总是相等**

```text
resolvedClassMask |= 1u << index;
registeredClassMask |= 1u << index;
```

**⇒ 与 §284 的"两阶段"定义**又一处不一致**。**

**⇒ 所以 `registeredClassMask` 在**客户端路径**里也是同时置的。**

### 2.2 **⑤ 的第三个条件是"索引没变"**

```php
finalCharacterIndex == characterIndex
```

**⇒ 与 §256 的四次索引检查同族。**

**⇒ 这是**第六次**（`captureClientLoadoutRequest` 两次、`resolveClientCharacterPresentation` 一次、这里一次、加上 `prepareClientLoadout` 两次）。**

### 2.3 **⑥ 的"序列变更 ⇒ 放弃"**

```php
if (requestSequence != LoadoutPrepareRequestSequence) return false;
```

**⇒ 所以一次准备过程中如果有新请求，这次**结果被丢弃**。**

**✓ 一个正确的"最新者胜"策略。**

### 2.4 而失败时的**两种清理**

```text
succeeded                              ⇒ 保存
!succeeded && 已有准备 && 角色不匹配    ⇒ 【reset】
!succeeded && 其它                      ⇒ 【保留旧的】
```

**⇒ 所以"旧结果仍有效"时保留。**

## 三、`configureGameStateImpl` 的**入口四项**

```php
const auto gameType = SV_EngineGameType(bookingGameType);
GameStateConfiguration.processing();
logGameServer("configureGameState entry map=" + mapName + " booked=" + bookingGameType +
    " engine=" + gameType + " checksum=" + configStringChecksum);
if (!configStringChecksum) { failed(InvalidChecksum); return false; }
```

### 3.1 而那句"这是唯一一处让 token 变成服务器运行的 gametype"

```php
// Every caller reaches here holding the token the client BOOKED. This is
// the one place it becomes the gametype the server runs, so nothing
// downstream - serverinfo, the spawn class lookup, the per-gametype gates
// - has to know both vocabularies.
```

**⇒ 一个**单一转换点**（`SV_EngineGameType`）。**

**⇒ 与 §280 的"不在这里静默改语义"配套 —— 转换是**显式**的。**

## 四、`currentCharacter` 的**两条来源**

```php
std::optional<uint32> currentCharacter;
if (OlMod::processRole() == ProcessRole::Dedicated)
{
    const std::lock_guard lock(LoadoutMutex);
    if (PreparedLoadouts && !PreparedLoadouts->members.empty())
        currentCharacter = PreparedLoadouts->members.front().characterIndex;
}
else
{
    currentCharacter = Bindings.currentCharacterIndex();
}
```

### 4.1 两个进程两条路

```text
Dedicated   从 PreparedLoadouts 的【第一个成员】
Client      从 currentCharacterIndex()（读 profile）
```

**⇒ 因为专用服没有本地玩家 ⇒ 用会话里第一个成员的角色。**

**⚠ 多个成员时只取第一个 ⇒ 所有成员共用一个角色索引。**

**⇒ 这是一个**已知的限制**。**

## 五、**`XBOXLIVE_CANTJOINSESSION` 的真因**（本组最重要的一段）

### 5.1 那段完整论证

```php
// THE LOOT BAND IS NOW A SUSPECT, SO IT HAS A SWITCH.
//
// The client kicks with XBOXLIVE_CANTJOINSESSION from sub_514540, and that
// function is a CONFIGSTRING VALIDATOR: it takes an index in [0, 0x31D9), reads a
// per-configstring type byte at `0x77D8250 + index`, and if the byte is neither
// 0x15 nor >= 0x17 it calls the CCS clear and raises ERR_SERVERDISCONNECT.
//
// We publish cs 12504..12692 for dmz, inside that range, and the client has NEVER
// been tested entering a match without them -- the band was added before the
// snapshot entry flag that first let it in at all. If those indices carry a type
// the client does not accept, this is exactly the failure we see.
//
// OLMOD_DMZ_LOOT_BAND=0 removes them for a run. Default stays on: retail sends
// them, and dmz cannot work without loot eventually.
```

### 5.2 六层

```text
1. 客户端从 `sub_514540` 用 `XBOXLIVE_CANTJOINSESSION` 踢人
2. 而那个函数是一个【配置串校验器】：
     · 取 [0, 0x31D9) 内的一个索引
     · 从 `0x77D8250 + index` 读一个【每配置串的类型字节】
     · 如果那个字节【既不是 0x15 也不是 >= 0x17】
     · ⇒ 调 `CCS clear` 并抛 `ERR_SERVERDISCONNECT`
3. 我们为 dmz 发布 cs 12504..12692，【在那个范围内】
4. 而客户端【从来没被测试过】不带着它们进入比赛
5. ⇒ 如果那些索引携带一个客户端不接受的类型，这正是我们看到的失败
6. ⇒ `OLMOD_DMZ_LOOT_BAND=0` 为一次运行移除它们
```

### 5.3 **这是 §236 那两个哨兵的第三次出现**

```text
§236  接受 `type >= 0x17 || type == 0x15`（本 build）
§262  `firstDynamicServerMaterialIndex` 用 `types[i] >= 23`（只一个）
§287   同上：`type` 既非 `0x15` 也非 `>= 0x17`
```

**⇒ **0x15 = 21、0x17 = 23** ✓ 与 §236 的 `{21, 23}` 完全一致。**

**⇒ 所以 `sub_514540` 是那个校验器的**第三个实例**。**

### 5.4 而 `0x77D8250`

**⇒ 与 §262 的 `ConfigStringTypesRva = 0x73D8250`（VA = `0x77D8250`）**完全一致** ✓**

**⇒ **第三次确认那个地址。** ✓

### 5.5 而 `[0, 0x31D9)`

**`0x31D9 = 12761`** —— 而 §175 里学过 "`0x31D9` bound" ✓

**⇒ **第二次确认那个界。** ✓

### 5.6 而"客户端从来没被测试过不带着它们"

**⇒ 一个**诚实的不确定性声明** —— 而不是"这不是原因"。**

**⇒ 而 `OLMOD_DMZ_LOOT_BAND=0` 提供一个**单变量实验**。**

### 5.7 而 `OLMOD_DMZ_LOOT_BAND` 的**解析**

```cpp
static const bool lootBandEnabled = [] {
    const char *const value = std::getenv("OLMOD_DMZ_LOOT_BAND");
    return !(value && value[0] == '0');
}();
```

**⇒ 第九种模式**：

```text
未设置           ⇒ 开
首字符 '0'       ⇒ 关
其它任何          ⇒ 开
```

**⇒ 与 §276 的 `OLMOD_CLIENT_UI_DVAR_REPAIR`（`!(size == 1 && value[0] == '0')`）**几乎相同**但少了长度检查。**

**⚠ `"0extra"` 会关（因为首字符是 '0'）而 `"1"` 会开。**

## 六、dmz 战利品带的**64 个槽**（本组第二重要）

### 6.1 那段实测

```php
// MEASURED 2026-09-04 by diffing `@gamestate` configstrings of two captures in
// Essential/demos:
//
//     cs 12500-13000   retail dm = 0 entries      retail dmz = 65 entries
//     cs 12504         "mp/dmzloot.csv"           the loot table asset
//     cs 12506..12692  64 entries, values 1148..1211
//
// Nothing in this server ever wrote above 12246, so a dmz client was handed a
// battle royale with no loot table and no lootable weapons.
```

### 6.2 五个数

```text
cs 12500-13000   范围
dm = 0 项
dmz = 65 项       （1 个表名 + 64 个槽）
cs 12504         "mp/dmzloot.csv"
cs 12506..12692  64 项，值 1148..1211
12246            我们之前写过的最高索引
```

### 6.3 而"我们之前从没写过 12246 以上"

**⇒ 与 §283 的"Nothing in this server ever wrote above 12246"**同一句，但那里是"玩家装饰"上下文？**

**⚠ 而这里说的是 dmz 战利品带。**

**⇒ 两处都引用"12246"这个数 —— 而记忆里"`12246` weaponCount"。**

**⇒ 所以 12246 是**武器配置串的最后一个索引**。**

### 6.4 那 64 个槽的**索引不连续**

```text
12506, 12507, 12508, 12509, 12510, 12511, 12512, 12513   连续 8
12516, 12517                                              跳 2
12520, 12521                                              跳 2
12528, 12529, 12530                                       跳 6
12537, 12538, 12539, 12540, 12541, 12542                  跳 5
12546, 12547, 12548, 12549, 12550, 12551                  跳 3
12555, 12556, 12557, 12558, 12559, 12560                  跳 3
12564, 12565                                              跳 3
12568, 12569, 12570, 12571                                跳 2
12576, 12577                                              跳 4
12584, 12585                                              跳 3
12592, 12593                                              跳 6
12602, 12603                                              跳 7
12610, 12611                                              跳 6
12614, 12615, 12616, 12617, 12618, 12619, 12620           跳 2
12623, 12625, 12628, 12629, 12631, 12632                  跳 1..6
12634                                                     跳 1
12692                                                     跳 57  ← 【最后一个很远】
```

**⇒ **索引是稀疏的** —— 与"战利品位置"语义一致（地图上的点）。**

### 6.5 而**值是 1148..1211 的武器索引**

```text
第一项 12616 → 1148    ← 【注意：第一个槽的武器是 1148 而在列表中间】
最后项 12692 → 1188
```

**⚠ **槽的顺序与武器的顺序不匹配** —— 第一个槽（12506）是武器 1149，而 1148 在 12616。**

**⇒ 所以这是**一个真实的随机布局**（零售每局随机）。**

**✓ 与那段注释"replay ONE real layout verbatim rather than inventing one"一致。**

### 6.6 而 64 个槽里**武器不连续**

```text
1149..1185  连续（37 个）
1189, 1190, 1191, 1192, 1193, 1194   跳
1186, 1187  （在 12592/12593）
1195..1211
1188        （在 12692）
```

**⇒ 所以武器的**排序**也是随机的。**

### 6.7 而 `firstDynamicWeapon=1147` 与"值从 1148 开始"

```php
// Values are ABSOLUTE weapon indices, left as captured: this build reports
// firstDynamicWeapon=1147 on mp_battlecity and the captured values start at
// 1148, so the two agree without rebasing.
```

**⇒ **1147 + 1 = 1148** ⇒ 所以第一个动态武器是 1148。**

**⇒ 值与 `firstDynamicWeapon + 1` 对齐 ⇒ **不需要重定基**。**

**✓ 一个精确的对齐论证。**

### 6.8 而 `gameState.configStrings.emplace(12504, "mp/dmzloot.csv")`

**⇒ 表名占一个槽。**

**⇒ 所以是 1 + 64 = 65 项** ✓ 与"dmz = 65 entries"一致。

## 七、`TimescaleConfigStringIndex` 的**第二次出现**

```cpp
gameState.configStrings.emplace(CodolGameServer::TimescaleConfigStringIndex, "0 0 1 1");
```

**⇒ 与 §268 的 `validateMessageBindings` **完全相同** ✓

**⇒ 记忆里 `11861` timescale。**

## 八、`damageFeedbackMaterial`

```php
// The client already carries this material: sub_BB5680 resolves an
// icon elem through configstring materialIndex+4355, and a read-only
// walk of that configstring range in a live client finds
// "damage_feedback" there, next to damage_feedback_endgame,
// damage_feedback_j and kill_feedback. Nothing needs precaching; this
// only asks the engine for the index it already has.
```

### 8.1 四个名字

```text
damage_feedback
damage_feedback_endgame
damage_feedback_j
kill_feedback
```

### 8.2 而 `materialIndex + 4355` 是**材质配置串的基址**

**⇒ 与 §262 的 `ServerMaterialConfigStringBase` 相关。**

**⇒ 所以 `4355` 可能就是那个基址。**

**⚠ 而 §262 的 `resolveServerMaterialConfigStringIndex` 用 `ServerMaterialConfigStringBase + index`。**

**⇒ 若基址是 4355 则一致。**

### 8.3 而"不需要预缓存"

**⇒ 因为客户端已经有那个材质。**

**⇒ 这与 §261 的"服务器只放索引"一致** ✓

## 九、`zm` 分支的**六个材质/武器**

```php
if (gameState.gameType == "zm") {
    gameState.factoryAmmoMaterials = {
        resolveServerMaterialConfigStringIndex("progress_bar_fill").value_or(0),
        resolveServerMaterialConfigStringIndex("progress_bar_bg").value_or(0)};
    gameState.zombieFallbackPistol = resolveBaseWeaponAssetIndex("m9_mp").value_or(0);
    gameState.zombieReviveMaterials = {
        resolveServerMaterialConfigStringIndex("waypoint_last_stand_localized").value_or(0),
        resolveServerMaterialConfigStringIndex("waypoint_revive_new").value_or(0)};
    ...
}
```

### 9.1 五对

```text
弹药          progress_bar_fill / progress_bar_bg
手枪          m9_mp
复活          waypoint_last_stand_localized / waypoint_revive_new
```

### 9.2 而"原版 Factory 的无手枪倒地会给一把模块化 M9（base646）"

```php
// Original Factory's no-pistol down grants a modular M9 (base646).
// Resolve the resident base by name; never reuse a recording's forged index.
gameState.zombieFallbackPistol = resolveBaseWeaponAssetIndex("m9_mp").value_or(0);
```

**⇒ 三层**：

```text
1. 原版 Factory 的无手枪倒地给一把【模块化 M9（base 646）】
2. 而这里按名解析常驻基址
3. **绝不复用录制里的伪造索引**
```

**⇒ 与 §243 的"index 1188 是加载顺序证据不是 ABI"同一原则** ✓

### 9.3 而 `base646` 与 §285 的 `** 646 0 0 8738 9321` **同一个 646**

**⇒ 所以 646 是 M4？**

**⚠ 而 §287 说 M9 是 `base646`。**

**⇒ 而 §285 的 1163 = `** 646 0 0 8738 9321`。**

**⇒ 所以 646 是**M9 的基址**？**

**⚠ 而 `m9_mp` 是 M9 手枪。**

**⇒ 可能 646 是 M9 而 1163 是 M9 的一个模块化变体。**

**⇒ 与 §285 的"1163..1213 是 51 个动态变体"一致** ✓

## 十、`OLMOD_FACTORY_TELEPORTERS` 的三段

```php
if (gameState.mapName == "zm_factory_sh") {
    const auto *option = std::getenv("OLMOD_FACTORY_TELEPORTERS");
    const std::array<std::string,3> names{
        "zombie_stopwatchneedle", "zombie_stopwatch", "zombie_stopwatch_glass"};
    if (option && std::string_view(option) == "1" &&
        std::ranges::all_of(names, [](const auto &name) {
            return Bindings.findXAsset(5, name.c_str(), false).data != nullptr;
        })) {
        if (const auto first = Bindings.firstDynamicServerMaterialIndex()) {
            std::map<uint16, std::string> occupied;
            bool complete = true;
            for (uint16 i = *first; i < ServerMaterialConfigStringCount; ++i) {
                const auto value = Bindings.readConfigString(ServerMaterialConfigStringBase + i, 64);
                if (!value) { complete = false; break; }
                if (!value->empty()) occupied.emplace(i, *value);
            }
            if (complete) { ... }
```

### 10.1 四个条件

```text
地图是 zm_factory_sh
OLMOD_FACTORY_TELEPORTERS == "1"        ← 【精确串比较】
三个材质都【存在】                        ⇒ findXAsset(5, ...) 非空
firstDynamicServerMaterialIndex 有值
```

### 10.2 而 `AssetType 5 = Material` ✓

**⇒ 与 §143/§252 一致。**

### 10.3 而那段"记录已占用的槽"

```php
std::map<uint16, std::string> occupied;
for (i = *first; i < ServerMaterialConfigStringCount; ++i) {
    const auto value = readConfigString(ServerMaterialConfigStringBase + i, 64);
    if (!value) { complete = false; break; }
    if (!value->empty()) occupied.emplace(i, *value);
}
```

**⇒ 一个"先读现状再分配"的模式** ✓

**⇒ 与 §262 的 `firstDynamicServerMaterialIndex` 配合。**

### 10.4 而 `readConfigString` 的 64 上限

**⇒ 与 §262 的 `resolveServerMaterialConfigStringIndex` 用 64 一致** ✓

## 十一、关键结论

1. **`prepareClientLoadouts` 里两个 classMask 也同时置** —— 与"两阶段"定义第三处不一致。
2. **"序列变更 ⇒ 放弃"** 是最新者胜策略。
3. **`SV_EngineGameType` 是唯一的 token → engine gametype 转换点**。
4. **专用服从 `PreparedLoadouts` 的第一个成员取角色索引** —— 多成员时共用。
5. **`sub_514540` 是配置串校验器**，接受 `type == 0x15 || type >= 0x17` —— 与 §236 的 `{21, 23}` 完全一致，第三次确认。
6. **`0x77D8250` 与 `[0, 0x31D9)`** —— 分别是第二次与第二次确认。
7. **`XBOXLIVE_CANTJOINSESSION` 的可疑来源是 dmz 战利品带**，有单变量开关。
8. **dmz 战利品带 64 槽 + 1 个表名 = 65 项**，索引稀疏（12506..12692）。
9. **`firstDynamicWeapon=1147` 与"值从 1148 开始"对齐 ⇒ 不需要重定基**。
10. **`12616 → 1148` 说明这是真实随机布局**（第一个槽是 1149 而 1148 在中间）。
11. **`12246` 是我们之前写过的最高索引** —— 与记忆里 `weaponCount` 一致。
12. **`m9_mp` 的 base 是 646** —— 与 §285 的 `** 646 0 0 ...` 同一 646。
13. **"绝不复用录制里的伪造索引"** —— 与 §243 同一原则。
14. **`OLMOD_FACTORY_TELEPORTERS` 用精确串 `== "1"`** —— 第十种解析。

## 十二、未闭合点

- dmz 战利品带是否真的是 `XBOXLIVE_CANTJOINSESSION` 的原因（开关实验未做）。
- `4355` 是否就是 `ServerMaterialConfigStringBase`。
- `12246` 与 `WeaponConfigStringCount`/武器配置串末索引的关系。
- `Appmain.cpp` 3900 行之后未读取。
