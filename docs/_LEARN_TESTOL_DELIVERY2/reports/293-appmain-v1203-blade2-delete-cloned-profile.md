# 293 · **V1.203 第 2 刀"删除整份克隆真人档案"**、`890 ms` 的单帧 stall、`39,324` 行的 item-names.csv

## 一、范围

本报告学习 `Appmain.cpp` 5000–5220 行。

## 二、`BotSeedSource` 的**四层挑选**

```php
if (!BotSeedSource && !BotSeedRefused)
{
    const std::lock_guard lock(LoadoutMutex);
    for (const auto &[xuid, member] : RegisteredSessionAssets.members())
    {
        if (member.characterPresentation.characterItemId == 0) continue;
        for (const auto &[name, candidate] : member.loadouts)
        {
            if (!SV_IsResolvedLoadoutValid(candidate)) continue;
            BotSeedSource = BotSeed{ .sourceXuid = xuid, .name = name, .loadout = candidate };
            break;
        }
        if (BotSeedSource) break;
    }
    if (!BotSeedSource)
    {
        BotSeedRefused = true;
        logGameServer("BOTTRACE|create-refused reason=no_published_class_or_character");
        return;
    }
    logGameServer("BOTTRACE|source class=" + name + " xuid=" + xuid + " primary=" + N);
}
```

### 2.1 四层

```text
① 成员必须有 characterItemId
② loadout 必须通过 SV_IsResolvedLoadoutValid
③ 取【第一个】满足的
④ 一旦找不到 ⇒ BotSeedRefused（【永久】）
```

### 2.2 ⚠ **`BotSeedSource` 现在只是"是否有可用成员"的标志**

**⇒ 因为第 2 刀删除了"克隆真人档案"的行为（见下）。**

**⇒ 但代码仍然**要求**存在一个种子 ⇒ 所以"没有真人就没有 bot"。**

**⚠ 这可能是一个遗留约束** —— 因为 bot 现在用自己的角色与官方职业。

**⇒ 待读 `BotSeedSource` 的后续使用。**

## 三、**`890 ms` 的单帧 stall**（本组第二重要）

### 3.1 那段实测

```php
// ── P4n.3: THE FILL IS SPREAD, NOT BURSTED ───────────────────────────
// Measured 2026-10-12 12:19:35 on the live log: ONE frame that admits a new
// bot client and publishes its first FULL baseline costs ~890 ms of CPU
// (`clientinfo WIRE observer=11 baseline=empty(flagged)` -> `snapshot ENTRY
// FLAG 0x02 arming for client 11` -> FRAMESTALL wallUs=977641
// threadCpuUs=890625), and this loop used to run every remaining slot inside
// a single call -- eleven of those back to back. That is exactly the report
// "after entering the map the game is very laggy for a while, normal once
// the bots are in". Every bot is still created; they are created one per
// interval so the client keeps a usable frame between them.
constexpr uint64 BotCreateIntervalMs = 400;
static uint64 lastBotCreateMs{};
...
if (lastBotCreateMs != 0 && steadyNowMs() < lastBotCreateMs + BotCreateIntervalMs) return;
```

### 3.2 七个数字

```text
~890 ms CPU     一个帧引入新 bot 客户端并发布其第一个【完整】基线
977641 wallUs   墙钟（977.6 ms）
890625 threadCpuUs 线程 CPU（890.6 ms）
11              剩余槽数
400 ms          BotCreateIntervalMs
12:19:35        实测时间
```

### 3.3 完整因果链

```text
1. 一帧引入新 bot 客户端并发布第一个完整基线 ⇒ 花费 ~890 ms CPU
2. 日志链：`clientinfo WIRE observer=11 baseline=empty(flagged)`
        → `snapshot ENTRY FLAG 0x02 arming for client 11`
        → `FRAMESTALL wallUs=977641 threadCpuUs=890625`
3. 而这个循环过去在【单次调用内】跑完所有剩余槽 —— **十一个背靠背**
4. ⇒ 正是那个报告："**进图之后很卡一会儿，人机进去之后就正常了**"
5. ⇒ 每个 bot 仍然创建；**按间隔一次一个**，让客户端之间有一个可用的帧
```

### 3.4 **"进图之后很卡一会儿，人机进去之后就正常了"**

**⇒ 一个**玩家原话**的症状，而现在有了精确的解释。**

**⇒ 与 §259 的"170-320 ms"、§260 的"165-300 ms"同族**（第四次性能症状）。

### 3.5 而 `FRAMESTALL` 是**一个新的日志标签**

**⇒ 与本文件的 `BOTTRACE|`、`SLOW TRACE`、`TRACE CENSUS`、`SNAPHEX` 同族。**

### 3.6 而 `977641 wallUs` vs `890625 threadCpuUs`

**⇒ 墙钟 977 ms 而 CPU 890 ms ⇒ **87 ms 的等待**（`Sleep` 或被抢占）。**

**✓ 与 §292 的 `Sleep(1)` 轮询一致。**

### 3.7 而 `BotCreateIntervalMs = 400`

**⇒ 11 个 bot × 400 ms = 4.4 秒** ⇒ 所以填充需要 4.4 秒。

**⇒ 与"进图之后很卡一会儿"**4.4 秒**吻合。**

### 3.8 而"这个函数在后续帧再次运行"（§292）

**⇒ 所以 `lastBotCreateMs` 的节流让每个会话帧只创建**一个**。**

## 四、**V1.203 第 2 刀"删除整份克隆真人档案"**（本组最重要的一段）

### 4.1 那段完整的中文注释

```php
// ★★★ 2026-10-14（V1.203 第 2 刀「人机专属档案」）—— **已删除整份克隆真人档案**。
//   旧行为：`RegisteredSessionAssets.updateMember(botXuid, source->second)` 把**第一个真实成员**的
//   `characterPresentation` + `loadouts` + `perks` + `equipment` + `offhands` + `rewards` **整份**写进
//   bot 的 xuid ⇒ 人机长得像那个真人（症状：人机复制我、我的装饰掉、人物不是我当前那套）。
//   新行为：不再在这里写档案；改为**职业解析之后**给每个 bot 写**它自己**的一份（见下方
//   `BOTTRACE|bot-profile`）：官方角色 item + 官方 9 套里它那一个 class 的 loadout。
//   必须保留的语义：**仍要给 bot 注册一份 presentation**，否则 `validCharacterCustomization` 为假、
//   spawn 会以 `CUSTOMIZATION_ABSENT` 被拒（见本文件 4743-4749 的既有注释）。
```

### 4.2 五层

```text
1. 旧行为：`updateMember(botXuid, source->second)` 把**第一个真实成员**的
   六项（presentation + loadouts + perks + equipment + offhands + rewards）**整份**写进 bot 的 xuid
2. ⇒ 人机长得像那个真人
3. ⇒ **三个症状**：人机复制我、我的装饰掉、人物不是我当前那套
4. 新行为：职业解析之后给每个 bot 写**它自己**的一份
5. 必须保留：**仍要给 bot 注册一份 presentation**，否则 `CUSTOMIZATION_ABSENT`
```

### 4.3 **"人机复制我"是操作者的原话（§283 的"谁让你复制我的了"）**

**⇒ 所以这一刀直接回应了那条禁令。**

**⇒ 而"我的装饰掉"是 §283 的 `>=` bug —— 两个 bug 叠加！**

```text
§283  `>=` 把真人判成人机 ⇒ 11 个装饰被抹掉
§293  克隆真人档案 ⇒ 人机长得像真人
```

**⇒ 两个独立的 bug 都产生"装饰"相关的症状。**

**⇒ 而 §283 的注释说"撤掉那份拷贝后依然没有"** ⇒ 所以先修了 §293 而 §283 仍存在。**

**✓ 两个 bug 的时间顺序：§293 先修，§283 后修。**

### 4.4 而"没有克隆回退"

```php
// THE SLOT GETS ONE OF THE NINE SHIPPED CLASSES, ALWAYS. There is no
// clone fallback: a slot whose class cannot be resolved is NOT created,
// because a filled match is filled with the official bots -- a copy of
// the host's class is exactly the old-method bot this work replaces.
// Every class is tried (the assigned one first, then the rest of the
// table), so one unresolvable entry costs an attempt, not the fill.
// Nothing else about the slot changes -- xuid, team and the asset clone
// are untouched; only the loadout resolvedLoadouts_ holds is replaced.
```

### 4.5 四层

```text
1. 槽**总是**拿到九套出货职业之一
2. **没有克隆回退**：解析不出职业的槽**不被创建**
3. 因为"一个填充的比赛是用官方 bot 填充的 —— 宿主职业的拷贝正是这项工作要替换的旧方法"
4. ⇒ **每个职业都试**（先分配的，然后表的其余）⇒ 一个不可解析项**花一次尝试而不是整个填充**
```

### 4.6 而"表的其余"的**循环**

```cpp
for (uint32 attempt = 0; attempt < OfficialBotClassCount && !official; ++attempt)
{
    const auto candidate = (index + attempt) % OfficialBotClassCount;
    classTrace.clear();
    official = resolveOfficialBotClass(candidate, classTrace);
    if (official && attempt != 0)
        logGameServer("BOTTRACE|bot-class-shifted index=" + index +
            " class=" + candidate + " attempts=" + (attempt + 1));
}
```

**⇒ 从 `index` 开始试 **9 个**（`OfficialBotClassCount`）。**

**⇒ 而"偏移"会被记录 ⇒ 所以"哪个 class 换了"可见。**

### 4.7 ⚠ **9 个职业 × 0.68-1.42 s = 最长 12.8 s**

**⇒ 如果**所有**职业都解析失败，每次尝试要花 0.68-1.42 s。**

**⇒ 9 × 1.42 = **12.8 秒** 的单帧停顿！**

**⚠ 而 §260 的 `resolveWeaponConfigStringIndex` 优化（O(1) 名表）应该让这个降到微秒级。**

**⇒ 所以这个循环在 §260 之后应该很快。**

**⇒ 只是 §291 的中文注释"0.68–1.42 s/次"是**优化前**的观测。**

### 4.8 而 `bot-class-unavailable` 的**每索引一次**

```cpp
static std::uint32_t lastUnavailableLogged = ~0u;
if (lastUnavailableLogged != index)
{
    lastUnavailableLogged = index;
    logGameServer("BOTTRACE|bot-class-unavailable index=" + index +
        " tried=" + OfficialBotClassCount + " reason=no_official_class_resolved");
}
return;
```

**⇒ `return`（不是 `continue`）⇒ **整个填充停止**。**

**⇒ 因为"一个填充的比赛是用官方 bot 填充的" ⇒ 不能用错误的替代。**

## 五、**每个 bot 自己的档案**

```cpp
{
    const std::lock_guard lock(LoadoutMutex);
    CodolGameServer::RegisteredSessionAssets botAssets{};
    botAssets.characterPresentation = ClientCharacterPresentation{
        .viewmodelIndex = 1,
        .selectionIds = { 1 },
        .characterItemId = botCharacterItem,
    };
    botAssets.loadouts.emplace(botClass, botLoadout);
    if (!RegisteredSessionAssets.updateMember(botXuid, std::move(botAssets))) { ... break; }
    logGameServer("BOTTRACE|bot-profile index=" + index + " xuid=" + botXuid +
        " character=" + botCharacterItem + " class=" + botClass);
}
```

### 5.1 **只写两项**

```text
characterPresentation    （viewmodelIndex 1 / selectionIds {1} / characterItemId）
loadouts                 （一个 class）
```

**⇒ 而 `perks`/`equipment`/`offhands` 空、`rewards` 为 nullopt。**

**⇒ 那段注释解释：**

```php
// 留空是**故意的**：`perks`/`equipment`/`offhands` 空、`rewards` 为 nullopt —— 取用点
// （`RegisteredSessionAssets.perks/equipment/resolvedEquipment/rewards`）对 nullopt 都有分支。
// `recordItemIds` 全 0 = 引擎按该角色的每槽默认补齐（`EngineBindings.hpp:286-290` 原文）。
```

### 5.2 三层

```text
1. 留空是**故意的**
2. 取用点对 nullopt 都有分支
3. `recordItemIds` 全 0 ⇒ 引擎按该角色的**每槽默认**补齐
```

**⇒ 与 §283 的"客户端从 entry 0 单独推导角色的每槽默认值"**完全一致** ✓

### 5.3 而 `viewmodelIndex = 1` 与 `selectionIds = {1}`

**⇒ 与 §283 的占位符完全相同** ✓

## 六、**12 个官方 `cha_*` 角色 id**（本组第三重要）

```cpp
constexpr uint16_t VerifiedDefaults[] = {
    545,     // cha_infbasea
    569,     // cha_snibasea
    570,     // cha_sniveterana
    592,     // cha_acubasea
    612,     // cha_grebasea
    635,     // cha_speveterana
    649,     // cha_sheprestigea
    671,     // cha_copveterana
    789,     // cha_infbaseb
    792,     // cha_infbasee
    2056,    // cha_cowgirl
    2105,    // cha_infiltrator
};
```

### 6.1 十二个 id 与名字

```text
545     cha_infbasea
569     cha_snibasea
570     cha_sniveterana
592     cha_acubasea
612     cha_grebasea
635     cha_speveterana
649     cha_sheprestigea
671     cha_copveterana
789     cha_infbaseb
792     cha_infbasee
2056    cha_cowgirl
2105    cha_infiltrator
```

### 6.2 而**踢掉了 `10362 cha_zombiehunter`**

```php
// ★ 2026-10-14 修正：**踢掉 `10362 cha_zombiehunter`**。
//   实机（`BOTTRACE|bot-profile` 11 行）显示轮换生效，但 index 0 与 8 拿到 10362，
//   而 10362 正是**默认/玩家同款**的身体 ⇒ 甲方看到的"只有个别人机还是复制我"就是这两个。
//   下面 12 个 id 全部是官方 `cha_*` 族、且**逐条可查** `Ayria\Logs\item-names.csv`。
```

### 6.3 四层

```text
1. 实机 11 行 `BOTTRACE|bot-profile` 显示轮换生效
2. 但 index 0 与 8 拿到 10362
3. 而 10362 正是**默认/玩家同款**的身体
4. ⇒ 甲方看到的"**只有个别人机还是复制我**"就是这两个
```

**⇒ 一个**极精确**的观测** —— 12 个里 2 个是 10362 而 12 % 11 = ？**

**⚠ 如果 `botCharacters.size() == 13`（含 10362）而 11 个 bot ⇒ `index % 13` 得 0..10 ⇒ 拿到前 11 个。**

**⇒ 所以 index 0 与 8 拿到 10362 意味着 10362 在前 11 个里的位置 0 与 8。**

**⇒ 而"12 个默认"里若要复现需要 13 个元素。**

**⇒ 总之：从列表里删掉 10362 是**正确的修复**。**

### 6.4 而"`Ayyria\Logs\item-names.csv` 39,324 行"

```php
// ★ V1.203 第 2 刀·续：**逐 bot 不同角色**。角色 item 取自官方 `cha_*` 族，
//   id 来源 = 本机 sweep 产物 `Ayria\Logs\item-names.csv`（39,324 行，`itemId,name`）——
//   不是手编：`10362 = cha_zombiehunter` 与既有注释一致，其余为该表里逐条可查的官方角色。
```

### 6.5 三层

```text
1. 角色 item 取自官方 `cha_*` 族
2. id 来源 = 本机 sweep 产物 `Ayria\Logs\item-names.csv`（**39,324 行**）
3. ⇒ **不是手编** —— `10362 = cha_zombiehunter` 与既有注释一致，其余逐条可查
```

### 6.6 而 `39,324` 与 §243 的 `60,249`

**⚠ 两个不同的数：**

```text
§243  "X of 60249 ids resolve to a name"     ← 候选数
§293  "39,324 行"                             ← 【实际解析出的】
```

**⇒ 39,324 / 60,249 = 65%** ⇒ **所以 60,249 个 id 里 39,324 有名字。**

**✓ 补齐了 §243 的空白。**

### 6.7 而 `OLMOD_BOT_CHARACTER` 与 `OLMOD_BOT_CHARACTERS`

```php
if (const auto *const single = std::getenv("OLMOD_BOT_CHARACTER"); single && single[0])
    pushList(single);           // 向后兼容：单一角色，全 bot 同一个
else if (const auto *const many = std::getenv("OLMOD_BOT_CHARACTERS"); many && many[0])
    pushList(many);
if (list.empty())
    list.assign(begin(VerifiedDefaults), end(VerifiedDefaults));
```

### 6.8 三层

```text
`OLMOD_BOT_CHARACTER`（单数）优先 ⇒ 【向后兼容】
否则 `OLMOD_BOT_CHARACTERS`（复数）
否则 `VerifiedDefaults`
```

**⇒ `else if` ⇒ 单数**覆盖**复数。**

**✓ 向后兼容的正确做法。**

### 6.9 而 `pushList` 的**逗号分割**

```cpp
const auto pushList = [&list](const char *const value) {
    std::string_view text{ value };
    while (!text.empty())
    {
        const auto comma = text.find(',');
        const auto token = text.substr(0, comma);
        const auto parsed = std::strtoul(std::string(token).c_str(), nullptr, 10);
        if (parsed > 0 && parsed <= 0xFFFFu) list.push_back((uint16)parsed);
        if (comma == npos) break;
        text.remove_prefix(comma + 1);
    }
};
```

**⇒ 与 §291 的手写 CSV 解析**不同**（用 `find(',')` + `substr` 而不是逐字符）。**

**⚠ 两处不同的 CSV 解析。**

**⇒ 而这里**不去空格**（`"545, 569"` 的第二个会 `strtoul(" 569")` 得 569 因为 `strtoul` 跳过前导空白）。** ✓

## 七、`createBotClient` 的**五个参数**

```php
const auto created = Server.createBotClient(
    botXuid, botDisplayName(index), botClass, botLoadout, side);
```

```text
botXuid          BotXuidBase + index
botDisplayName   从池循环
botClass         职业名（classTrace）
botLoadout       解析出的 loadout
side             从 fill plan
```

### 7.1 而 `side` 的**回退**

```cpp
const auto side = index < plan.size() ? plan[index] : CodolGameServer::SvTeam::None;
```

**⇒ 手动门请求而没有 plan ⇒ `None`（历史继承）。**

**✓ 与那段注释"a manual door request with no plan falls back to the historical inherit"一致。**

## 八、关键结论

1. **`BotSeedSource` 现在只是"是否有可用成员"的标志** —— 遗留约束。
2. **一个引入 bot 客户端的帧花 ~890 ms CPU**（`FRAMESTALL wallUs=977641 threadCpuUs=890625`）。
3. **"进图之后很卡一会儿，人机进去之后就正常了"** —— 玩家原话的精确解释。
4. **`BotCreateIntervalMs = 400` ⇒ 11 个 bot 需 4.4 秒。**
5. **V1.203 第 2 刀删除了"整份克隆真人档案"** —— 三个症状（人机复制我、我的装饰掉、人物不是我当前那套）。
6. **§293 与 §283 是两个独立 bug 都产生装饰症状**，而 §293 先修。
7. **"没有克隆回退"** —— 解析不出职业的槽**不被创建**，而**每个职业都试**。
8. **9 个职业 × 0.68-1.42 s = 最长 12.8 s**（在 §260 优化之前）。
9. **每个 bot 只写两项**（presentation + 一个 loadout），其余留空是**故意的**。
10. **`recordItemIds` 全 0 ⇒ 引擎按角色的每槽默认补齐** —— 与 §283 完全一致。
11. **12 个官方 `cha_*` 角色 id**，而**踢掉了 `10362 cha_zombiehunter`**（默认/玩家同款）。
12. **"index 0 与 8 拿到 10362"** —— 一个极精确的观测。
13. **`item-names.csv` 有 39,324 行** ⇒ 60,249 个 id 里 65% 有名字（补齐 §243 的空白）。
14. **`OLMOD_BOT_CHARACTER`（单数）优先于 `OLMOD_BOT_CHARACTERS`（复数）** —— 向后兼容。
15. **`pushList` 用 `find(',')` 而 §291 用逐字符** —— 两处不同的 CSV 解析。

## 九、未闭合点

- `BotSeedSource` 的遗留约束（为何仍需真人）。
- 9 个职业全失败时的 12.8 s 停顿（§260 后应已解决）。
- `39,324` 与 `60,249` 的精确关系。
- `Appmain.cpp` 5220 行之后未读取。
