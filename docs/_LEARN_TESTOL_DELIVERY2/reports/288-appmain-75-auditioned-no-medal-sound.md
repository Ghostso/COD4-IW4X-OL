# 288 · **75 个别名全试过、没有一个是奖章音**、`p 11 x84 mp_hit_alert` 的实测计数、高低两带的回退

## 一、范围

本报告学习 `Appmain.cpp` 3896–4120 行。

## 二、Factory 时钟的三段

```php
if (complete) {
    const auto indices = SV_RegisterDynamicServerMaterials(gameState, *first, names, occupied);
    if (indices) gameState.factoryClockMaterials = { (*indices)[1], (*indices)[2] };
}
logGameServer("Factory clock registration boundary=" + *first +
    " face=" + gameState.factoryClockMaterials[0] +
    " glass=" + gameState.factoryClockMaterials[1]);
```

### 2.1 三个材质名

```text
zombie_stopwatchneedle   （[0] 指针 —— 【未使用】）
zombie_stopwatch          （[1] 表盘）
zombie_stopwatch_glass    （[2] 玻璃）
```

**⇒ `factoryClockMaterials` 只存 `[1]` 与 `[2]`** —— 所以 `[0]`（指针）被**丢弃**。

**⚠ 三个材质注册但只用两个。**

### 2.2 而 `SV_RegisterDynamicServerMaterials` 返回**三个索引**

**⇒ 按 `names` 的顺序。**

### 2.3 而失败时的日志

```php
if (!gameState.factoryClockMaterials[0])
    logGameServer("Factory clock unavailable: missing artwork, dynamic boundary or namespace");
```

**⇒ **三个可能的原因**在一行里。**

**✓ 与 §244 的 `refuse` 同族（一个日志覆盖多种原因，但列出它们）。**

## 三、`kill_feedback` 与 `scavenger_bag_mp`

```php
gameState.killFeedbackMaterial = Bindings.resolveServerMaterialConfigStringIndex("kill_feedback");
gameState.scavengerBagWeaponAssetIndex = Bindings.resolveBaseWeaponAssetIndex("scavenger_bag_mp");
```

**⇒ 两个不同来源**：

```text
kill_feedback       材质配置串
scavenger_bag_mp    基础武器索引
```

**⇒ 与 §287 的 `damage_feedback`（材质）一致。**

## 四、**`p 11 x84 mp_hit_alert`** 的实测计数（本组最重要的一段）

### 4.1 那段实测

```php
// THE KILL SOUND. `mp_hit_alert` above was already the right guess
// and the demo now CONFIRMS it: naming every `p <n>` a retail dm
// server sent, through configstring 3624+n, gives
//
//     p 11  x84  mp_hit_alert     the hit marker's sound
//     p 15  x28  mp_hit_kill      the kill's
//     p 29  x4   mp_headshot
//
// Resolved by NAME for the same reason the hit alias is: the alias
// INDEX is handed out per match as sounds are first needed, so 15
// is only `mp_hit_kill` in the match that assigned it that way.
// The name is the portable half, and this is what
// resolveSoundAliasEventParameters takes.
```

### 4.2 三个 `p <n>` 与计数

```text
p 11   × 84   mp_hit_alert    命中标记的声音
p 15   × 28   mp_hit_kill     击杀的
p 29   × 4    mp_headshot
```

**⇒ 三个参数与三个计数。**

### 4.3 而"**索引是每局分配的**"

**"the alias INDEX is handed out per match as sounds are first needed, so 15 is only `mp_hit_kill` in the match that assigned it that way."**

**⇒ 所以**数字不可移植而名字可移植**。**

**⇒ 与 §243 的"index 1188 是加载顺序证据不是 ABI"同一原则** ✓

**⇒ 第三次出现。**

### 4.4 而 `configstring 3624 + n`

**⇒ 与 §261 的"`announceSoundAliases` 写 `name -> cs 3624+idx`"**完全一致** ✓**

**⇒ 记忆里"`3624` sound aliases"。**

**⇒ 所以 `p 11` 对应 cs 3635。**

### 4.5 而这段"demo 现在确认了"

**⇒ 所以 `mp_hit_alert` 原来是**猜测**而现在**被证实**。**

**⇒ 与 §277 的"我瞄的正是那堵墙"**相反** —— 那是错的猜，这是对的猜。**

## 五、**75 个别名全试过、没有一个是奖章音**（本组第二重要）

### 5.1 那段完整的实测记录

```php
// These are read off THIS build, live: the CCS constant-string
// table was dumped from a running client (type 5 = the sound alias
// pool, 1507 entries) and only 68 of them are not announcer
// voice-over - the rest carry ab_/uk_/za_/rb_ language prefixes.
// mp_challenge_complete and mp_level_up are NOT among them; the
// splash table references them but this map does not load them,
// which is the same reason mp_hit_alert never resolved either.
// mp_bonus_start, mp_ingame_summary and mp_capture_flag ARE loaded
// and are the closest thing this build has to a reward stinger -
// retail's own splash table uses mp_bonus_start on row 79.
// RESULT, 2026-08-17: all 75 were auditioned live, one per hit, and NONE of
// them is a medal sound. That is the honest answer rather than a
// near-miss: this build's networked constant-string table simply has
// no reward cue in it. The real ones exist as ASSETS in
// common_mp.ff - mp_challenge_complete, mp_level_up, and the
// ui_reward_bronze/silver/gold/rare family whose audio is
// main\sound\mp\ui_medal_reward_get.mp3 - but none of them is in
// the networked table, so no server can reference one. Retail is
// silent here for the same reason (2d-quindecies: every medal row's
// column 9 is a backreference).
//
// Left empty deliberately. Shipping a wrong sound is worse than
// none; the resolution path below still works, so a single name
// here is all it takes if a suitable alias is ever found or added.
```

### 5.2 五层

```text
1. CCS 类型 5 有 1507 项，只有 **68** 个不是播音员语音 —— 其余带 ab_/uk_/za_/rb_ 语言前缀
2. `mp_challenge_complete` 与 `mp_level_up` 【不在其中】；splash 表引用它们但这张地图不加载
3. `mp_bonus_start`/`mp_ingame_summary`/`mp_capture_flag` 【在】且是最接近的 —— 零售 splash 表在第 79 行用 `mp_bonus_start`
4. **RESULT 2026-08-17：全部 75 个都现场试听过，一次一个命中，没有一个是奖章音**
5. ⇒ 这个 build 的网络化常量串表里【根本没有奖励音】
```

### 5.3 而"真实的那些作为**资产**存在于 `common_mp.ff`"

```text
mp_challenge_complete
mp_level_up
ui_reward_bronze / silver / gold / rare 家族
  其音频是 main\sound\mp\ui_medal_reward_get.mp3
```

**⇒ 6 个资产**（三个名字 + 四个 ui_reward_*）。

**⇒ 但没有一个在网络化表里 ⇒ 没有服务器能引用。**

### 5.4 而"零售在这里也是静默的，同样的原因"

```text
// Retail is silent here for the same reason (2d-quindecies: every medal
// row's column 9 is a backreference).
```

**⇒ 所以**零售自己也没有奖章音** —— 因为 splash 表的第 9 列是**回引**（backreference）而不是字面量。**

**⇒ 与 §144 里"`sub_C1C860` plays column 9 of `mp/splashTable.csv`, skipping an empty cell or the literal `"null"`"一致。**

### 5.5 而三个数字的对照

```text
1507    CCS 类型 5 总项
68      非播音员语音
75      现场试听的数量
```

**⚠ `75 > 68`。**

**⇒ 所以试听的是 `collectServerSoundAliasAuditions` 的**75 项**（§261 说 1432/1507 带语言前缀 ⇒ 1507-1432 = 75）。**

**✓ 1507 - 1432 = 75。**

**⇒ 而"68 个不是播音员"是另一次统计。**

**⚠ 68 与 75 不一致 —— 两次统计的口径不同。**

**⇒ 但都指向"极少数非语音别名"。**

### 5.6 **"留空是有意的"**

```text
// Left empty deliberately. Shipping a wrong sound is worse than
// none; the resolution path below still works, so a single name
// here is all it takes if a suitable alias is ever found or added.
```

**⇒ 三层**：

```text
1. 发一个错误的声音比没有更糟
2. 而解析路径仍然工作
3. ⇒ 只要发现或添加一个合适的别名，这里加一个名字就够了
```

**⇒ 与 §244 的"读作 ENABLED 会加一个没人要的附件"同族**（代价不对称）。

**⇒ 第四次"宁可缺失也不要错误"。**

### 5.7 而 `splashAliases{}` 是**空数组**

```php
const std::vector<std::string> splashAliases{};
const auto splashParameters = Bindings.resolveSoundAliasEventParameters(splashAliases);
for (...) { ... }        // ← 永远不会进
if (!gameState.splashSound) {
    logGameServer("splash sound unresolved; medals stay silent");
    Bindings.logServerSoundAliasTables(40);
}
```

**⇒ 空数组 ⇒ 循环不进 ⇒ 总是打 "unresolved" 并转储表。**

**✓ 所以 `logServerSoundAliasTables(40)` 每次配置 gamestate 都会跑。**

**⚠ 而 §262 说那个函数枚举 16 个 CCS 类型 × 16384 项 —— **每次 gamestate 都跑会很贵**。**

**⇒ 这是一处**潜在的性能问题**（虽然 gamestate 配置不频繁）。**

## 六、**高低两带的回退**（本组第三重要）

```php
// OLMOD(killstreak-announcer): the UAV earn/use pair. Try the
// LOW-BAND alias name first (same resolver as every sound above;
// a miss returns nothing), then fall back to the MEASURED
// high-band announcer constants: p 1277 uk_1mc_achieve_uav lands
// exactly 3.0 s before the grant frame and p 1605
// uk_1mc_use_uav 3.0 s after the use frame (dm demo 2, twice
// each). The high band is client-owned CCS type 5 and needs no
// registration, which is why the fallback is safe on any map.
constexpr uint16 SvAnnouncerAchieveUav = 1277;
constexpr uint16 SvAnnouncerUseUav = 1605;
const auto uavAliases{ "mp_killstreak_uav" };
const auto uavParameters = resolveSoundAliasEventParameters(uavAliases);
const auto uavLowBand = ... ? uavParameters.front() : optional<uint16>{};
gameState.uavEarnSound = uavLowBand ? uavLowBand : optional<uint16>{SvAnnouncerAchieveUav};
gameState.uavUseSound  = uavLowBand ? uavLowBand : optional<uint16>{SvAnnouncerUseUav};
```

### 6.1 五个数

```text
1277    p 1277 uk_1mc_achieve_uav
3.0 s   在授予帧【之前】
1605    p 1605 uk_1mc_use_uav
3.0 s   在使用帧【之后】
2       dm demo 2，各两次
```

### 6.2 三层

```text
1. 先试【低带】别名名（同一解析器，未命中返回空）
2. 回退到【测量过的】高带播音员常量
3. 高带是【客户端拥有的 CCS 类型 5】且【不需要注册】⇒ 所以回退在任何地图上都安全
```

### 6.3 ⚠ **而 `uavEarnSound` 与 `uavUseSound` 用同一个 `uavLowBand`**

```php
gameState.uavEarnSound = uavLowBand ? uavLowBand : {1277};
gameState.uavUseSound  = uavLowBand ? uavLowBand : {1605};
```

**⇒ 如果低带解析成功，**两个字段都是同一个值**。**

**⚠ 这看起来不对** —— earn 与 use 应该是**两个不同的声音**。

**⇒ 而 §261 的 `resolveSoundAliasEventParameters` 对一个名字返回一个参数 ⇒ 所以低带只能给一个值。**

**⇒ 所以"低带成功 ⇒ 两个都用它"是一个**有意的降级**（至少有一个声音）。**

**⚠ 但玩家会听到"获得"的声音两次（一次在获得，一次在使用）。**

## 七、**lead/lost/winning 三条与覆盖**

```php
struct VoiceRequest { const char *name; std::optional<uint16> *slot; uint16 fallback; };
const std::array requests{
    VoiceRequest{"ab_1mc_lead_taken_01", &gameState.leadTakenSound, SvAnnouncerLeadTakenHigh},
    VoiceRequest{"uk_1mc_lead_lost_01",  &gameState.leadLostSound,  SvAnnouncerLeadLostHigh},
    VoiceRequest{"uk_1mc_winning_fight_01", &gameState.winningFightSound, SvAnnouncerWinningHigh},
};
for (const auto &request : requests)
{
    const std::vector<std::string> names{ request.name };
    const auto resolved = resolveSoundAliasEventParameters(names);
    const auto value = !resolved.empty() && resolved.front() ? resolved.front() : optional<uint16>{};
    // An override wins over both the CCS answer and the constant, so a
    // wrong guess costs one restart instead of one build.
    const char *overrideName = nullptr;
    if (request.name == "ab_1mc_lead_taken_01") overrideName = "OLMOD_LEAD_TAKEN";
    else if (request.name == "uk_1mc_lead_lost_01") overrideName = "OLMOD_LEAD_LOST";
    ...
}
```

### 7.1 三层

```text
① CCS 解析
② 常量回退
③ 【环境变量覆盖】—— 优先于两者
```

### 7.2 而"一个错误的猜测只花一次重启而不是一次构建"

**⇒ 与 §279 的 `fps-set-<n>` 同一原则** ✓

**⇒ 第五次"参数化 > 枚举"。**

### 7.3 而三个名字的**语言前缀**

```text
ab_1mc_lead_taken_01      ab_ = §155 的 sc↔ab_
uk_1mc_lead_lost_01       uk_ = §155 的 tf↔uk_
uk_1mc_winning_fight_01
```

**⇒ 两个不同语言前缀混用。**

**⇒ 因为 `ab_` 与 `uk_` 是**不同语言**的同一个语音。**

**⚠ 所以 `lead_taken` 是 ab_ 而 `lead_lost` 是 uk_ —— **不一致**。**

**⇒ 可能是一个**疏漏**（应该都是同一个语言）。**

### 7.4 而 §288 开头说"28800: the fallback is now the HIGH band, not 106/107/1620"

```php
// 28800: the fallback is now the HIGH band, not 106/107/1620.
// Those low-band slots never resolved on this client (see the
// header note); a high-band index plays without any registration.
```

**⇒ 三个旧的低带槽**（106/107/1620）**从未解析过**。**

**⇒ 与 §288 开头"52 个 `announcer play p 106` 行和静默"一致。**

## 八、`OLMOD_LEAD_TAKEN` 等的**三个覆盖变量**

```text
OLMOD_LEAD_TAKEN
OLMOD_LEAD_LOST
（第三个待读）
```

## 九、关键结论

1. **Factory 时钟注册三个材质但只用两个**（`[0]` 指针被丢弃）。
2. **`p 11 × 84 mp_hit_alert` / `p 15 × 28 mp_hit_kill` / `p 29 × 4 mp_headshot`** —— demo 实测的计数。
3. **"索引每局分配而名字可移植"** —— 与 §243 同一原则，第三次。
4. **`configstring 3624 + n`** 与 §261 完全一致。
5. **`mp_hit_alert` 从"对的猜"变成"被证实"**。
6. **CCS 类型 5 有 1507 项，只有 68（或 75）非播音员语音**。
7. **`mp_challenge_complete`/`mp_level_up` 不在网络化表里 ⇒ 没有服务器能引用**。
8. **真实的奖章音作为资产存在于 `common_mp.ff`**（含 `ui_medal_reward_get.mp3`）。
9. **零售自己在这里也静默**（splash 表第 9 列是回引）。
10. **"全部 75 个都现场试听过，没有一个是奖章音"** —— 一个完整的负结果。
11. **"留空是有意的：发一个错误的声音比没有更糟"** —— 第四次"宁可缺失"。
12. **`splashAliases{}` 空数组 ⇒ 每次 gamestate 都跑 `logServerSoundAliasTables(40)`** —— 潜在性能问题。
13. **UAV 的高低两带**：1277（前 3.0 s）/ 1605（后 3.0 s）。
14. **⚠ earn 与 use 在低带成功时用同一个值** —— 玩家会听到两次一样的。
15. **三条语音的 `ab_`/`uk_` 前缀不一致** —— 可能疏漏。
16. **106/107/1620 三个低带槽从未解析过**（52 行静默）。

## 十、未闭合点

- 68 与 75 两个统计口径的差异。
- `uavEarnSound`/`uavUseSound` 低带同值的后果。
- `ab_`/`uk_` 前缀不一致是否有意。
- `Appmain.cpp` 4120 行之后未读取。
