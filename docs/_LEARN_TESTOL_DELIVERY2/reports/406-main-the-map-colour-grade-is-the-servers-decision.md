# 406 · **"地图的调色是【服务器的决定】"** —— vision 家族的六个命令各自一个类型索引、`'default'` 的平光、`bestClientKills` 在 0-0 时返回最低占用槽

## 一、范围

本报告学习 `sv_main_mp.cpp` 5550–5900 行。

## 二、**vision 家族的完整逆向**（本组最重要的一段）

### 2.1 那段

```php
// MEASURED (out.exe): the map's colour grade is the SERVER'S decision on
// this engine, and it reaches the client as one reliable command.
//
// CODREF: the client's server-command dispatcher is 0x00613A40 and it
// switches on the verb CHARACTER. Six cases are the vision family, each
// the same five instructions -- copy argv(1) into a 0x40-byte name
// buffer, atoi argv(2) as a blend time in milliseconds, call the applier
// at 0x0046CEF0 with a vision TYPE index:
//
//     'N' 78 -> type 0   name buffer +0x192578      <- the map grade
//     'O' 79 -> type 1   +0x1925B8
//     'P' 80 -> type 2   +0x1925F8
//     'Q' 81 -> type 3   +0x192638
//     'R' 82 -> type 4   +0x192678
//     '3' 51 -> type 5   +0x1926B8
//
// 0x0046CEF0 blends when the time is positive and hands a zero straight
// to the instant setter at 0x0046CE80; both load "vision/%s.vision"
// (0x00DB44BC) through DB_FindXAssetHeader asset type 0x24 via
// 0x0046BFD0. A client nobody tells keeps the engine's fallback name
// 'default' (0x00DADE10) -- a neutral grade with none of the map's sun
// colour, contrast or filmtweaks, which is the flat look every map has
// had in this project (HANDOFF section 98).
```

### 2.2 二十二层

```text
1. **地图的调色是【服务器的决定】在这个引擎上**
2. ⇒ **而它作为【一条可靠命令】到达客户端**
3. ⇒ **客户端的 server-command 派发器是 `0x00613A40`**
4. ⇒ **而它在【动词的字符】上 switch**
5. ⇒ **六个 case 是 vision 家族，每一个都是【同样的五条指令**】：
      · **把 `argv(1)` 拷进一个 `0x40` 字节的名字缓冲区**
      · **`atoi(argv(2))` 作为一个毫秒的混合时间**
      · **用一个 vision【类型索引】调 `0x0046CEF0` 的应用器**
6. ⇒ **六个命令**：
      · **`'N'` 78 ⇒ 类型 `0`，名字缓冲 `+0x192578`** ← **地图调色**
      · **`'O'` 79 ⇒ 类型 `1`，`+0x1925B8`**
      · **`'P'` 80 ⇒ 类型 `2`，`+0x1925F8`**
      · **`'Q'` 81 ⇒ 类型 `3`，`+0x192638`**
      · **`'R'` 82 ⇒ 类型 `4`，`+0x192678`**
      · **`'3'` 51 ⇒ 类型 `5`，`+0x1926B8`**
7. ⇒ **`0x0046CEF0` 在时间【正】时混合**
8. ⇒ **而把【零】直接交给 `0x0046CE80` 的【即时设置器**】**
9. ⇒ **两者都通过 `0x0046BFD0` 的 `DB_FindXAssetHeader` 资产类型 `0x24` 加载 `"vision/%s.vision"`（`0x00DB44BC`）**
10. ⇒ **一个没人告诉的客户端保持引擎的【回退名 `'default'`（`0x00DADE10`）**】**
11. ⇒ **一个中性的调色，没有任何地图的阳光颜色、对比度或 filmtweak**
12. ⇒ **那就是这个项目里【每一张地图】都有过的【平光外观**】**（`HANDOFF` 第 98 节）
```

### 2.3 ⭐⭐⭐ **"六个命令、六个类型索引、六个名字缓冲"**

**✅ 这是本文件里**最完整的命令派发逆向**。**

**⇒ 三层**：

```text
派发器：`0x00613A40`，按【动词字符】switch
六个 case：`'N'` `'O'` `'P'` `'Q'` `'R'` `'3'`
⇒ **每个一个类型索引 `0..5` 与一个名字缓冲偏移**
```

**⚠ 而 `'3'`（51）**打破了字母顺序**。**

**⇒ 三层**：

```text
`N O P Q R` ⇒ **连续的五个字母**
`3`         ⇒ **一个数字**
⇒ **⇒ 所以类型 5 是一个【不同来源的命令**】
```

**✅ ⭐ **一个"字母族 + 一个数字例外"的清单**。**

**⚠ 而"`0x192578` 到 `0x1926B8`"⇒ **步长 `0x40`**。**

**⇒ 三层**：

```text
0x1925B8 - 0x192578 = 0x40
0x1925F8 - 0x1925B8 = 0x40
...
0x1926B8 - 0x192678 = 0x40
⇒ **六个 `0x40` 字节的名字缓冲，连续**
```

**✅ ⭐ **"`0x40` 字节的名字缓冲区"与"步长 `0x40`"完整闭合** ✓

**⇒ 所以**六个缓冲紧邻**。**

### 2.4 而**"`'default'` 的平光"**

**✅ 与 §405 的"`splash` 第 4 行在每一列都是空白"**同族（**第二次"一个静默的回退产生一个可见的缺陷**）。**

**⇒ 三层**：

```text
没人告诉 ⇒ 引擎回退到 `'default'`
⇒ **一个中性调色（没有阳光颜色/对比度/filmtweak）**
⇒ **⇒ 项目里每一张地图都是平的**
```

**✅ ⭐ **"这个项目里每一张地图都有过的平光外观"** —— 一个**全局的、一直存在**的视觉缺陷。**

**⚠ 而"`HANDOFF` 第 98 节"⇒ **一个已记录的条目**。**

**✅ 与 §398 的"`sub_466450` 不只是显示它 —— 它除以它"**同族（**第三次"一个缺失的数据产生一个可见的缺陷**）。**

### 2.5 而**"正时间混合、零即时"**

**✅ 与 §369 的"`0` 是有意义的"**同族（**第五次"零有语义"）。**

**⇒ 三层**：

```text
time > 0  ⇒ **混合（一个渐变）**
time == 0 ⇒ **即时设置**
⇒ **⇒ 所以零是一个【合法的操作模式**】而不是"无操作"**
```

**✅ 一个**精确的语义**。

## 三、**`bestClientKills` 在 0-0 时的行为**（本组第二重要）

### 3.1 那段

```php
// NOT `bestClientKills()` ALONE. At 0-0 it returns the lowest occupied
// slot, so an unguarded watch announces a lead change on the first
// frame of every match and again every time that slot changes hands
// while nobody has scored. A lead exists once somebody is ahead of
// nothing.
if (!best || best->second <= 0)
    return;
```

### 3.2 九层

```text
1. **不是只用 `bestClientKills()`**
2. ⇒ **在 `0-0` 时它返回【最低的占用槽**】**
3. ⇒ **所以一个无守卫的监视会在一场比赛的【第一帧**】宣告一次领先变化**
4. ⇒ **并在【那个槽易手】时再来一次**
5. ⇒ **而那时【还没有人得分**】**
6. ⇒ **一个领先【存在】一旦有人领先于【无**】**
7. ⇒ **所以 `!best || best->second <= 0 ⇒ return`**
```

### 3.3 ⭐⭐ **"一个领先存在一旦有人领先于无"**

**✅ 这是本文件里**对"退化输入"最清晰地陈述**。**

**⇒ 三层**：

```text
`bestClientKills()` 在 0-0 时返回 **最低占用槽**（一个确定的答案）
⇒ **而那个答案是【无意义的**】
⇒ **⇒ 所以必须显式加 `<= 0`**
```

**✅ 与 §405 的"`resource deadlock would occur`"**不同（这是**一个退化输出**）。**

**⚠ 而"第一帧宣告一次"⇒ **一个具体的症状**。**

**✅ 与 §391 的"`remaining == 30000` 永不触发"**同族（**第二次"一个边界条件产生错误行为"）。**

### 3.4 而**"FLOOR：冷却吞掉宣告时仍记领先者"**

```php
// THE FLOOR. The leader is still recorded when the cooldown swallows the
// announcement - otherwise the NEXT flip back would look like a fresh
// change and announce immediately, which is the spam this prevents
// arriving one flip later.
const auto now = world_.snapshot().serverTime;
const auto previous = announcer_.leader;
announcer_.leader = leaderKey;
if (announcer_.lastLeadChangeServerTime && now >= *announcer_.lastLeadChangeServerTime &&
    now - *announcer_.lastLeadChangeServerTime < SvAnnouncerLeadChangeCooldownMs)
{
    return;
}
```

**⇒ 八层**：

```text
1. **记 `previous`，然后【立刻】更新 `announcer_.leader = leaderKey`**
2. ⇒ **【然后】检查冷却**
3. ⇒ **冷却内 ⇒ `return`（不发）**
4. ⇒ **所以领先者【已被记录**】**
5. ⇒ **理由**：**否则【下一次翻回来**】会看起来像一次【新的变化**】**
6. ⇒ **并【立即宣告**】**
7. ⇒ **⇒ 那正是这个冷却防止的【刷屏】，只是【晚一个翻转**】到达**
```

**✅ ⭐ **"否则下一次翻回来会看起来像一次新的变化并立即宣告 —— 那正是这个冷却防止的刷屏，只是晚一个翻转到"** —— 一个**极精确的机制论证**。**

**✅ 与 §369 的"一个有时存活的值是别的东西拥有的"**同族（**第三次"顺序决定语义"）。**

## 四、**团队模式 vs 个人模式的三处分叉**（本组第三重要）

### 4.1 那段

```php
const auto teamMode = matchGameType_ == "cha" || matchGameType_ == "sd";
std::optional<std::uint32_t> leaderKey;
std::uint32_t leaderScore{};
const std::int32_t tf = clients_.teamScore(SvTeam::Tf).value_or(0);
const std::int32_t sc = clients_.teamScore(SvTeam::Sc).value_or(0);
if (teamMode) {
    if (tf == 0 && sc == 0) return;
    if (tf == sc) return;   // 平局不算领先
    leaderKey = tf > sc ? 1000u : 1001u;
    leaderScore = tf > sc ? tf : sc;
} else {
    const auto best = clients_.bestClientKills();
    if (!best || best->second <= 0) return;
    leaderKey = best->first;
    leaderScore = best->second;
}
```

### 4.2 十层

```text
1. **`teamMode = cha || sd`**
2. ⇒ **一个统一的"当前领先者"编码**：
      · **dm ⇒ `clientNum`**
      · **团队 ⇒ `1000 + 队伍序号`**（`1000` = Tf / `1001` = Sc）
3. ⇒ **团队模式的三个守卫**：
      · **`tf == 0 && sc == 0 ⇒ return`**
      · **`tf == sc ⇒ return`**（**平局不算领先**）
      · 否则 `leaderKey = tf > sc ? 1000 : 1001`
4. ⇒ **dm 的两个守卫**（`!best || best->second <= 0`）
```

**✅ ⭐ **"`1000 + 队伍序号`"** —— 一个**用一个域编码两个种类的**手法。**

**⇒ 三层**：

```text
`0..17`      ⇒ **客户端号（dm）**
`1000`/`1001` ⇒ **队伍（团队模式）**
⇒ **⇒ 所以一个 `uint32` 可以装两种**
```

**✅ 与 §402 的"复合缓存键"**同族（**第二次"多域编码）。**

**⚠ 而"平局不算领先"⇒ **一个精确的规则**。**

**✅ 与 §391 的"攻方全灭而已下包 ⇒ 没有结果"**同族（**第二次"不满足时返回 nullopt"）。**

### 4.3 而**"播报对象也改对了"**

```php
const auto leadingTeam = *leaderKey == 1000u ? SvTeam::Tf : SvTeam::Sc;
for (clientNum) {
    const bool onLeadingTeam = teamMode
        ? slots[clientNum].team == leadingTeam
        : (uint32)clientNum == (*leaderKey - (teamMode ? 1000u : 0u));
    const bool wasLeadingTeam = teamMode
        ? previous && *previous == (leadingTeam == SvTeam::Tf ? 1001u : 1000u)
        : previous && *previous == clientNum;
    ...
}
```

**⇒ 七层**：

```text
1. **`onLeadingTeam`**：
      · **团队 ⇒ 那个客户端在领先队里**
      · **dm ⇒ 那个客户端【就是**】领先者
2. ⇒ **`wasLeadingTeam`**：
      · **团队 ⇒ `previous` 是【【对方**】的 key**】
      · **dm ⇒ `previous` 就是那个客户端
3. ⇒ **所以团队模式的两个判断【互相取反**】**
```

**⚠ 而"`previous && *previous == (leadingTeam == Tf ? 1001u : 1000u)`"⇒ **所以它查的是【对方的 key**】。**

**⇒ 三层**：

```text
若当前领先是 Tf（1000）
⇒ `wasLeadingTeam` 查 `previous == 1001`（**即之前是 Sc 领先**）
⇒ **⇒ 一个【翻转**】的判据**
```

**✅ 一个**精确的"是否发生了翻转"的检查**。**

### 4.4 而**"比分差 >= 20 时播『要赢』那句"**

```php
constexpr std::int32_t SvLeadBlowoutMargin = 20;
const auto margin = tf >= sc ? tf - sc : sc - tf;
const bool blowout = margin >= SvLeadBlowoutMargin;
if (onLeadingTeam) {
    if (blowout) queueAnnouncerLine(clientNum, winningFightSound_, true);
    else queueAnnouncerLine(clientNum, leadTakenSound_, true);
    queueLocalSound(clientNum, SvAnnouncerWinningMusic);
} else {
    queueAnnouncerLine(clientNum, leadLostSound_, true);
    queueLocalSound(clientNum, SvAnnouncerLosingMusic);
}
```

**⇒ 八层**：

```text
1. **`SvLeadBlowoutMargin = 20`**（**甲方给的"我方 60 敌方 40"**）
2. ⇒ **`margin = |tf - sc|`**
3. ⇒ **`blowout = margin >= 20`**
4. ⇒ **领先队**：**blowout ⇒ `winningFightSound_`（"我们要赢得这场战斗啦"）**，否则 `leadTakenSound_`（"夺得领先"）
5. ⇒ **并播 `SvAnnouncerWinningMusic`**
6. ⇒ **落后队**：**`leadLostSound_`（"失去领先"）**
7. ⇒ **并播 `SvAnnouncerLosingMusic`**
8. ⇒ **⇒ 所以三个 announcer id + 两个音乐 id**
```

**✅ ⭐ **"甲方给的『我方 60 敌方 40』"** —— 一个**从用户口述推导的常数**。**

**⚠ 而"三个 id + 两个音乐"⇒**五个 announcer 常量**。**

**✅ 与 §403 的"`SvAnnouncerSpawnMusic = 2130`"**配合。

### 4.5 而**"三个 id 打进日志便于替换"**

```php
OlMod::RuntimeLog::write(..., "announcer lead change: " + ... +
    " ids=" + std::to_string(leadTakenSound_) + "/" +
    std::to_string(leadLostSound_) + "/" +
    std::to_string(winningFightSound_));
```

**⇒ 三层**：

```text
1. **三个 id 都打进日志**
2. ⇒ **所以替换它们【不需要重编**】**
3. ⇒ **⇒ 因为它们在 `leadTakenSound_` / `leadLostSound_` / `winningFightSound_` 三个成员里**
```

**✅ 与 §378 的"`OLMOD_OUTFIT_TAG` 的旋钮"**同族（**第十一次"可替换的推断值"）。**

## 五、**`SV_BuildFactoryEntryHud` 的四个偏移**（本组第四重要）

### 5.1 那段

```php
// CODREF(g_run_frame): out.exe 0x538B70 type1 and 0x538250 resolve
// text+952; 0x514880 resolves the map's native constant-string table.
// Original solo Factory demo: four current HUD rows 516..519, fade
// births20500/21500/21750/23000 after first spawn20250; all fade out
// at40300 for500ms. This is a recorded presentation, not recovered GSC.
std::array<SvHudElem, 4> result{};
if (serverTime < birth || serverTime - birth >= 20550) return result;
constexpr std::array<std::uint32_t, 4> offsets{250,1250,1500,2750};
```

### 5.2 十二层

```text
1. **`0x538B70`（type 1）与 `0x538250` 解析 `text + 952`**
2. ⇒ **`0x514880` 解析地图的原生常量串表**
3. ⇒ **原始单人 Factory demo**：
      · **四个当前 HUD 行 `516..519`**
      · **fade birth `20500`/`21500`/`21750`/`23000`**
      · **在 `first spawn 20250` 之后**
      · **全部在 `40300` fade out `500ms`**
4. ⇒ **"这是一个【录制的表现】，不是恢复的 GSC"**
5. ⇒ **总窗口 `20550ms`**
6. ⇒ **四个相对偏移 `250`/`1250`/`1500`/`2750`**
```

**✅ ⭐ **"`text + 952`"** 与 §390 的"`label + 952` 然后一个 1 基的本地化查找"**完全闭合 ✓

**⇒ **第二次确认那 `952`。**

**⚠ 而"`40300 - 20250 = 20050`"⇒ 与"`elapsed >= 20050` 开始 fade"**完全一致 ✓

**✅ **一个精确的算术闭合。**

**⚠ 而"四个 birth `20500/21500/21750/23000` 减 `20250`"⇒ `250/1250/1500/2750`** ✓**

**✅ **第二次闭合。**

### 5.3 而**"保留一个连续的 HUD 前缀"**

```php
for (std::size_t i{}; i < result.size(); ++i) {
    if (elapsed < offsets[i]) break; // Keep a contiguous HUD prefix.
    ...
}
```

**⇒ 三层**：

```text
1. **`break` 而不是 `continue`**
2. ⇒ **所以一个还没到点的元素会【终止整个循环**】**
3. ⇒ **⇒ 保留一个【连续的 HUD 前缀**】**
```

**✅ ⭐ **一个"前缀而不是子集"的选择**。**

**⚠ 而"`break`"⇒ **一个精确的语义**（不是"跳过这个"）。**

**✅ 与 §346 的"`foundFree` 之后一切必须零"**同族（**第二次"前缀语义"）。**

## 六、**battleChatter 的听众判定**（本组第五重要）

### 6.1 而**"说话者占着话轮即使没人听"**

```php
// THE SPEAKER HOLDS THE FLOOR EVEN WHEN NOBODY IS LISTENING. IW4's
// doSound adds the speaker before playSoundToTeam and removes it after
// the hold, with no reference to who received anything - so a line with
// an empty audience still costs the speaker their two seconds. Making
// the hold conditional on receivers would let a player alone in a
// corner bank up chatter and fire it the moment someone walks in.
battleChatterSpeakers_.push_back({ speakerClientNum, speakerOrigin, now + SvBattleChatterSpeakerHoldMs });
```

**⇒ 九层**：

```text
1. **说话者占着话轮【即使没人听**】**
2. ⇒ **IW4 的 `doSound` 在 `playSoundToTeam`【之前】**加说话者，在持有之后移除
3. ⇒ **而【不参考谁收到了任何东西**】**
4. ⇒ **所以一条【空听众**】的行仍然花掉说话者【那两秒**】**
5. ⇒ **把持有条件化在收件人上会让一个【独自在角落**】的玩家【攒起**】chatter**
6. ⇒ **并在【有人走进来的那一刻**】一次发出**
7. ⇒ **所以无条件 `push_back`**
```

**✅ ⭐ **"让一个独自在角落的玩家攒起 chatter 并在有人走进来的那一刻一次发出"** —— 一个**极具体的滥用场景**。**

**✅ 与 §400 的"缓存键必须含那个状态"**不同（这是**一个资源占用**）。**

**⚠ 而"两秒"⇒ 与 `SvBattleChatterSpeakerHoldMs`**配合。**

## 七、**`driveBattleChatter` 的"`RELOAD_START` 不是 `RELOAD`"**

```php
// CODREF: iw4 _battlechatter_mp.gsc reloadTracking --
// `self waittill ( "reload_start" )`. EV_RELOAD_START is 27 in
// re/olfinal-events.tsv, and this build's own event ring
// carries it, so the trigger needs no new plumbing at all.
//
// RELOAD_START, not RELOAD: the ring also carries EV_RELOAD
// (25), EV_RELOAD_FROM_EMPTY (26) and EV_RELOAD_END (28), and
// a player who empties a magazine produces more than one of
// them for a single reload.
if (status->events[index].event != SvEventReloadStartNotify) continue;
```

### 7.1 八层

```text
1. **IW4 `_battlechatter_mp.gsc` 的 `reloadTracking`**：`self waittill("reload_start")`
2. ⇒ **`EV_RELOAD_START` 是 `27`**（`re/olfinal-events.tsv`）
3. ⇒ **而这个 build 自己的事件环【携带它**】**
4. ⇒ **所以那个触发器【不需要任何新管道**】**
5. ⇒ **`RELOAD_START` 不是 `RELOAD`**：
      · 环还携带 `EV_RELOAD (25)`
      · `EV_RELOAD_FROM_EMPTY (26)`
      · `EV_RELOAD_END (28)`
6. ⇒ **而一个打空弹匣的玩家为一次换弹产生【不止一个**】它们**
```

**✅ ⭐ **"一次换弹产生不止一个事件"** —— 一个**精确的去重理由**。**

**✅ 与 §342 的"`0x19..0x1E` 六个换弹事件"**完全闭合 ✓

**⇒ **第二次确认那个区间**（`25/26/27/28` 对应 `0x19/0x1A/0x1B/0x1C`）。**

**⚠ 而"只取 `27`"⇒ **一个精确的选择**。**

**✅ 与 §402 的"按次数统计"**不同（这是**按事件 id 精确选**）。

### 7.2 而**听众的三档**

```php
// Team is the faithful one and wins when asked for. Otherwise the
// speaker hears their own callouts, which is this project's own
// choice and not IW4's -- see the enum. EXCLUDE_SELF restores
// retail's behaviour without going all the way to team-only.
if (flag("OLMOD_BATTLECHATTER_TEAM")) return SvBattleChatterAudience::Team;
if (flag("OLMOD_BATTLECHATTER_EXCLUDE_SELF")) return SvBattleChatterAudience::Everyone;
return SvBattleChatterAudience::EveryoneIncludingSpeaker;
```

**⇒ 五层**：

```text
1. **`Team` 是【忠实的那个**】而它被要求时【优先**】**
2. ⇒ **否则说话者【听到自己的呼叫**】**
3. ⇒ **那是【这个项目自己的选择**】，不是 IW4 的**
4. ⇒ **`EXCLUDE_SELF` 恢复零售的行为【而不一路到 team-only**】**
5. ⇒ **默认 `EveryoneIncludingSpeaker`**
```

**✅ ⭐ **"那是这个项目自己的选择，不是 IW4 的"** —— 又一个**明确的诚实标注**。**

**✅ 与 §403 的"按 demo 形态驱动的显示值"**同族（**第三次"明确标注非原版"）。**

## 八、关键结论

1. **⭐⭐⭐ vision 家族的完整逆向**：**`0x00613A40` 按【动词字符】switch，六个 case 是 `'N'`(78)/`'O'`(79)/`'P'`(80)/`'Q'`(81)/`'R'`(82)/**`'3'`(51)**，各自一个类型索引 `0..5` 与一个名字缓冲（`0x192578` 起，**步长 `0x40`**）。
2. **"每个 `0x40` 字节的名字缓冲"与"步长 `0x40`"完整闭合** —— 六个缓冲紧邻。
3. **⭐ `'3'`（51）打破了字母顺序** —— **一个"字母族 + 一个数字例外"的清单**。
4. **`0x0046CEF0` 在时间正时混合、把零直接交给 `0x0046CE80` 的即时设置器**；两者都通过 `0x0046BFD0` 的 `DB_FindXAssetHeader`（资产类型 `0x24`）加载 `"vision/%s.vision"`。
5. **⭐⭐ "一个没人告诉的客户端保持引擎的回退名 `'default'` —— 一个中性的调色，没有任何地图的阳光颜色、对比度或 filmtweak ⇒ 那就是这个项目里每一张地图都有过的平光外观"`** —— 一个**全局的、一直存在**的视觉缺陷。
6. **⭐⭐ "不是只用 `bestClientKills()`：在 `0-0` 时它返回【最低的占用槽】⇒ 一个无守卫的监视会在一场比赛的第一帧宣告一次领先变化"`** —— 第二次"一个边界条件产生错误行为"，而 **"一个领先存在一旦有人领先于无"`**。
7. **⭐ "THE FLOOR：冷却吞掉宣告时仍记领先者 —— 否则下一次翻回来会看起来像一次新的变化并立即宣告，那正是这个冷却防止的刷屏，只是晚一个翻转到"`** —— 第三次"顺序决定语义"。
8. **"`1000 + 队伍序号`"的多域编码**（`0..17` 客户端号 / `1000`/`1001` 队伍）—— 第二次"多域编码"。
9. **"平局不算领先"** 与 **"`tf == 0 && sc == 0 ⇒ return`**" —— 第二次"不满足时返回"。
10. **`wasLeadingTeam` 查的是【对方的 key**】** ⇒ 一个精确的"是否发生了翻转"的检查。
11. **⭐ `SvLeadBlowoutMargin = 20`**（**甲方给的"我方 60 敌方 40"**）⇒ **`margin >= 20` 时播 `winningFightSound_`，否则 `leadTakenSound_`** —— 一个从用户口述推导的常数。
12. **三个 announcer id + 两个音乐 id 都打进日志** ⇒ 替换**不需要重编** —— 第十一次"可替换的推断值"。
13. **⭐ `SV_BuildFactoryEntryHud` 的完整算术闭合**：`40300 - 20250 = 20050`（fade 起点）、四个 birth 减 20250 = `250/1250/1500/2750`；而 **`text + 952` 第二次确认 §390 的 `label + 952`**。
14. **"这是一个【录制的表现】，不是恢复的 GSC"`** —— 第四次"明确标注非原版"。
15. **`break` 而不是 `continue` ⇒ 保留一个连续的 HUD 前缀** —— 第二次"前缀语义"。
16. **⭐ "说话者占着话轮即使没人听：IW4 的 `doSound` 在 `playSoundToTeam` 之前加说话者而不参考谁收到了任何东西 ⇒ 一条空听众的行仍然花掉说话者那两秒；把持有条件化在收件人上会让一个【独自在角落的玩家攒起 chatter 并在有人走进来的那一刻一次发出】"`**。
17. **⭐ "`RELOAD_START` 不是 `RELOAD`：环还携带 `EV_RELOAD (25)` / `EV_RELOAD_FROM_EMPTY (26)` / `EV_RELOAD_END (28)`，而一个打空弹匣的玩家为一次换弹产生不止一个它们"`** —— 第二次确认 `0x19..0x1C` 那个区间。
18. **⭐ "`Team` 是忠实的那个；默认说话者听到自己的呼叫，那是【这个项目自己的选择，不是 IW4 的】"`** —— 第三次"明确标注非原版"。

## 九、未闭合点

- vision 的六个名字（`vision/%s.vision`）在零售 demo 里的实际值。
- `SvAnnouncerWinningMusic` / `SvAnnouncerLosingMusic` 的值。
- `SvBattleChatterSpeakerHoldMs` 的值。
- `SvBattleChatterAudience` 的完整枚举。
- `SV_BattleChatterAudience` 的过滤逻辑（按队伍/距离）。
- `sv_main_mp.cpp` 5900 行之后未读取。
