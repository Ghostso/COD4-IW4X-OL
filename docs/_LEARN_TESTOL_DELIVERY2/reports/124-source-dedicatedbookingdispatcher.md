# 学习报告 124（重开）— `DedicatedBookingDispatcher.cpp`（47,443 B / 953 行）

**学习范围**：`backend\DedicatedBookingDispatcher.cpp` 全文（**953 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录八个重大发现**：①**平台 id → DW 账号 id 映射的三次实测修正（d35/d36/d37）** ②**`match_rules_rejected` 的"载体专用度"取值规则** ③**`ffa` 的 30/10 与 configstring 467/468** ④**`fallbackMatchRules` 的三个模式标准值** ⑤**`member selection differs` 的 rotationIndex 不比较** ⑥**`submit` 的队列上限 8** ⑦**`updateLoadout` 的刷新** ⑧**五种诊断结果**

---

## 一、★★★★★ **平台 id → DW 账号 id 映射的三次实测修正**

### 1.1 ★★★★★ 完整注释（第 70–85 行，逐字）

```cpp
// ★★★ 2026-10-07 10:1x -- **平台 id → Demonware 账号 id 映射**（进图最后一跳的定因；单变量）。
//
// 客户端在两个命名空间里使用两个不同的 id：
//   * **LSG / 房间层**（auth、房间消息、记录 sender 字段）用 fake auth 给出的**平台 id**
//     `0x01100001DEADC0DE`（= **76561201696194782**）；
//   * **netchan / 战斗服层**（`getchallenge`/`connect` 的 xuid、市场库存 `Owner`、
//     遥测 `${CODOID(...)}`）用这台安装的 **Demonware 账号 id**
//     `0xE7C8A98A6B4C2D0E`（= **16701785630074219790**）。
//
// 老外的两个 id 恰好是同一个值（`Profiles2Service.cpp:170-181` 原文），所以他们从来
// 不需要这个映射；我们的 fake auth 给平台 id、安装本体报 Demonware 账号 id，
// **两条链在"房间成员 → 战斗服名册"这一跳首次相撞**。
// d35 判据日志（单变量证明）：
//     `connectionless rejected reason=getchallenge XUID is not in the session roster
//       (xuid=16701785630074219790 pending=gen1[0x01100001deadc0de,];active=none;)`
// ⇒ **名册必须换成 Demonware 账号 id**,客户端才会被 `sessionAllowsXuid` 放行。
```

### ★★★★★ 两个命名空间的完整对照

| 层 | id | 十进制 |
|---|---|---|
| **LSG / 房间层** | ★ **`0x01100001DEADC0DE`** | **76,561,201,696,194,782** |
| **netchan / 战斗服层** | ★★ **`0xE7C8A98A6B4C2D0E`** | **16,701,785,630,074,219,790** |

★★★ **⇒ 与报告 119 的**完全一致** ✓**
**⇒ 且明确了**哪一层用哪个**：**
```
LSG / 房间层 ⇒ **平台 id**（auth、房间消息、sender 字段）
netchan / 战斗服 ⇒ **DW 账号 id**（`getchallenge`/`connect` 的 xuid、库存 `Owner`、遥测 `${CODOID}`）
```

### ★★★★★ d35 的精确拒单日志（逐字）

```
connectionless rejected reason=getchallenge XUID is not in the session roster
  (xuid=16701785630074219790 pending=gen1[0x01100001deadc0de,];active=none;)
```

★★★ **⇒ 三个精确值：**
```
`xuid` = **16701785630074219790**（DW 账号 id,客户端报的）
`pending` = **`0x01100001deadc0de`**（平台 id,名册里的）
        ↓
★★★ ⇒ **不匹配** ⇒ `sessionAllowsXuid` 拒绝
```

### ★★★★★ 三次实测修正的完整表

| # | 日期 | 单变量 | 结果 |
|---|---|---|---|
| **d35** | 2026-10-07 10:1x | ★ **名册成员换成 DW 账号 id** | `getchallenge XUID is not in the session roster` |
| **d36** | 2026-10-07 10:2x | ★★ **`ownerUserId` 也一起映射** | 不映射 ⇒ **`non_owner_booking_ignored`** |
| **d37** | 2026-10-07 10:2x | ★★★ **`entitlementCheck` 仍要原始平台 id** | 映射后喂 ⇒ **`entitlement_rejected`** |

★★★ **⇒ 完整的因果：**
```
d35：名册要 DW 账号 id（否则 getchallenge 被拒）
        ↓
★★★ d36：`ownerUserId` 是**独立字段**,必须一起映射
   ⇒ 否则 **本机(已映射) ≠ 房主(未映射)** ⇒ `non_owner_booking_ignored`
   ⇒ booking 跳过 ⇒ 无 SessionStart ⇒ **`GAMESTATE_NOT_CONFIGURED` 卡"设置游戏"**
        ↓
★★★ d37：`entitlementCheck` **仍要原始平台 id**
   （市场/权益存储是**按平台 id 记账**的）
   ⇒ 映射后喂 ⇒ `entitlement_rejected`（**items 不变、仅 id 变即失败**）
        ↓
★★★★★ ⇒ 最终实现：**映射前按位留一份原始 id,供 entitlement 专用**
```

### ★★★ 实现（第 86–107 行 + 第 667–677 行）

```cpp
std::uint64_t demonwareAccountIdForPlatformId(const std::uint64_t platformId)
{
    constexpr std::uint64_t KnownPlatformId  = **0x01100001DEADC0DE**ull;
    constexpr std::uint64_t DefaultAccountId = **0xE7C8A98A6B4C2D0E**ull;
    auto accountId = DefaultAccountId;
    // OLMOD_DW_ACCOUNT_ID 覆盖
    return platformId == KnownPlatformId ? accountId : platformId;   // ★ 名单外原样透传
}
...
std::vector<std::uint64_t> platformMemberIds;                    // ★ 留原始 id
for (const auto &member : roster->members)
    platformMemberIds.push_back(member.userId);
for (auto &member : roster->members)
    member.userId = demonwareAccountIdForPlatformId(member.userId);   // ★ 映射
if (roster->ownerUserId)
    roster->ownerUserId = demonwareAccountIdForPlatformId(roster->ownerUserId);   // ★ d36
...
if (!state->entitlementCheck(**platformMemberIds[memberIndex]**, items))          // ★ d37
```

★★★ **⇒ 三个实现要点**完全对应**三次实测：**
```
① 映射 `member.userId`
② **映射 `ownerUserId`**（d36）
③ **entitlement 用 `platformMemberIds[i]`**（d37）
```

---

## 二、★★★★★ **`match_rules_rejected` 的"载体专用度"取值规则**

### 2.1 ★★★★★ 完整注释（第 463–478 行，逐字）

```cpp
// ★★★ 2026-10-11 22:5x -- **分歧不再一律致命：按"载体专用度"取值**。
//
// 实测（发行播单 `mp_playlists_shipRetail_release.info`）：**`mp_nuked,cha` 出现在 10 个播单里**,
// 其中 **5 个能通过 `valid(rules,"cha")`**,却**分两派** ——
//   **Skirmish/Onboarding 50/10**（行 **478**/**512**）与
//   **Ground War / "Map: Nuketown"(110) / Charge-9v9(160) 150/20**（行 **1693**/**615**/**2221**）。
// 老外 legacy 路径要求"唯一共识",于是 `mp_nuked+cha` 被 `match_rules_rejected` 拒绝、
// 整张票被跳过 ⇒ 战斗服收不到 booking ⇒ 无 SessionStart ⇒ **`GAMESTATE_NOT_CONFIGURED`**,
// 客户端卡"**设置游戏**"。
//
// 取值规则：在都能通过校验的候选里，**rotation 条目最少的那个播单**说的算。
// 依据：单条目 "Map: X" 列表（如 110 "Map: Nuketown"）就是玩家点那张图时实际
// 启用的列表，它对这张图的**专用度最高**；条目多的是顺带包含此图的大列表。
// **同专用度仍分歧 ⇒ 保持原判决拒绝**。
```

### ★★★★★ 完整的分歧数据

```
`mp_nuked,cha` 出现在 **10 个播单**里
        ↓
★★★ 其中 **5 个**能通过 `valid(rules,"cha")`
        ↓
★★★ 但**分两派**：
  ① **Skirmish / Onboarding ⇒ 50/10**（行 **478** / **512**）
  ② **Ground War / "Map: Nuketown"(110) / Charge-9v9(160) ⇒ 150/20**（行 **1693** / **615** / **2221**）
        ↓
★★★ 老外要求"唯一共识" ⇒ **`match_rules_rejected`**
   ⇒ 整张票被跳过 ⇒ 无 booking ⇒ 无 SessionStart
   ⇒ **`GAMESTATE_NOT_CONFIGURED`** ⇒ 客户端卡"**设置游戏**"
```

### ★★★★★ 取值规则

```
在都能通过校验的候选里，**`rotation` 条目最少的那个播单**说的算
        ↓
★★★ 依据：单条目 "Map: X" 列表（如 **110 "Map: Nuketown"**）就是
   **玩家点那张图时实际启用的列表**,它对这张图的**专用度最高**
        ↓
★★★ 条目多的是**顺带包含此图的大列表**
        ↓
★★★ **同专用度仍分歧 ⇒ 保持原判决拒绝**
```

### ★★★ 实现（第 478–514 行）

```cpp
std::optional<std::size_t> consensusRotationSize;
for (const auto &candidate : document->playlists)
{
    if (!containsSelection) continue;
    const auto rules = parseMatchRules(*document, candidate, selectionGameType);
    if (!rules) continue;
    const auto rotationSize = candidate.rotation.size();
    if (!consensus) { consensus = *rules; consensusRotationSize = rotationSize; continue; }
    if (*consensus == *rules)
    {
        consensusRotationSize = std::min(*consensusRotationSize, rotationSize);   // ★ 取更小
        continue;
    }
    if (rotationSize < *consensusRotationSize) { consensus = *rules; consensusRotationSize = rotationSize; }  // ★ 更专用者胜
    else if (rotationSize == *consensusRotationSize) return std::nullopt;          // ★ 同专用度 ⇒ 拒绝
}
return consensus ? consensus : fallbackMatchRules(...);
```

★★★ **⇒ 三个分支：**
```
① 规则相同 ⇒ 取**更小的 rotationSize**
② 规则不同且**新候选更专用**（rotationSize 更小）⇒ **换**
③ 规则不同且**同专用度** ⇒ **拒绝**（`nullopt`）
```

---

## 三、★★★★★ **`ffa` 的 30/10 与 configstring 467/468**

### 3.1 ★★★★★ 完整注释（第 236–263 行，逐字）

```cpp
else if (gameType == "ffa")
{
    // Unlike cha and sd there is nothing to read: neither shipped free-for-all playlist
    // - **23 ("Free For All")** or **154 ("Snipers Only")** - declares a single `scr_*` rule,
    // so the limits are the gametype's own defaults rather than playlist-driven.
    //
    // OLMOD: **30 and 10 are read from the retail demo `C-2021-7-25[1-19-26]dm.demo`,
    // configstrings 467 and 468**. Those two indices were identified with an **oracle**
    // rather than by eye - the shipped playlist pins `scr_cha_scorelimit 50` and
    // `scr_cha_timelimit 10`, and **467/468 are the only candidates that read exactly 50 and
    // 10 in both cha demos while still separating every other mode**
    // (**war 75/10, dom 200/0, chicken 300/15**).
    //
    // They cross a build boundary - that demo is **OLfinal** - so they are a **project choice**
    // here, not a constant recovered from 3.3.3.3.
    // A wrong limit is **visible and harmless**, unlike a wire constant.
    rules.scoreLimit = **ffaScoreLimit()**;
    rules.timeLimitMinutes = **60**;
}
```

### ★★★★★ 完整的"oracle"论证

```
两个 shipped FFA playlist（**23 "Free For All"** / **154 "Snipers Only"**）
   ⇒ **一条 `scr_*` 规则都不声明**
        ↓
★★★ 所以限额是 **gametype 自己的默认值**
        ↓
★★★ **30 与 10 从零售 demo `C-2021-7-25[1-19-26]dm.demo` 的
   configstring `467` 与 `468` 读出**
        ↓
★★★★★ **用"oracle"而非目视识别**：
   shipped playlist 钉住 `scr_cha_scorelimit 50` / `scr_cha_timelimit 10`
   ⇒ **467/468 是唯一在两个 cha demo 里都读到 50 和 10,
      且能区分其他所有模式的候选**
   ⇒ 其他模式：**war 75/10 / dom 200/0 / chicken 300/15**
```

★★★ **⇒ 这是一个**用已知常量反推未知索引**的精妙方法**（"oracle"）。**

### ★★★ 四个模式的限额对照

| 模式 | scorelimit | timelimit |
|---|---|---|
| **`cha`** | ★ **50** | ★ **10** |
| **`war`（tdm）** | **75** | **10** |
| **`dom`** | **200** | **0** |
| **`chicken`** | **300** | **15** |

★★ **⇒ 第 4 条（`chicken 300/15`）是**唯一能与 467/468 区分开的关键**（其余可能撞值）。**

### ★★★ 时间限制改成 60 的理由（第 254–261 行，逐字）

```cpp
// OLMOD(ffa-test-limits): the time limit is **raised to 60 for development**.
// `SV_BuildGameState` computes configstring 15 as
// **`matchStartServerTime + minutes * 60 * 1000` in uint64**,
// so 60 is **3,600,000 ms** and nowhere near an overflow; a zero here would mean NO limit
// and erase the clock entirely.
// TODO(CODOL): **restore 10 before this branch is offered upstream** - it is the retail
// value, read from the dm demo's configstring 468.
```

★★★ **⇒ 三个精确事实：**
```
① ★★ configstring 15 = **`matchStartServerTime + minutes * 60 * 1000`**（**uint64**）
② ★ 60 分钟 = **3,600,000 ms**,远未溢出
③ ★★★ **TODO：上游化前恢复 10**（零售值）
```

### ★★★ `ffaScoreLimit()` 的边界（第 39–63 行）

```cpp
static const std::uint32_t limit = [] {
    constexpr std::uint32_t fallback = **30**;
    ...
    if (error != std::errc{} || pointer != last || parsed < **1** || parsed > **1000**)
        return fallback;
    return parsed;
}();
```

★★★ **⇒ 上限 **1..1000**,理由（逐字）：**
```
"Bounded at 1..1000: **a zero would mean NO score limit and the match could never end
 by score**, which is the opposite of what a tester wants."
```

---

## 四、★★★★★ **`fallbackMatchRules` 的三个模式标准值**

### 4.1 ★★★★★ 完整实现（第 339–375 行）

```cpp
std::optional<MatchRules> fallbackMatchRules(playlistVersion, gameType)
{
    MatchRules rules{ .playlistVersion = playlistVersion };
    if (gameType == "**sd**")
    {
        rules.timeLimitMinutes = **2**;
        rules.roundSwitch = **8**;
        rules.roundLimit = **17**;
        rules.winLimit = **9**;
    }
    else if (gameType == "**cha**")
    {
        rules.scoreLimit = **50**;
        rules.timeLimitMinutes = **10**;
    }
    else if (gameType == "**tdm**")
    {
        rules.scoreLimit = **75**;
        rules.timeLimitMinutes = **10**;
    }
    else return std::nullopt;
    return valid(rules, gameType) ? std::optional{rules} : std::nullopt;
}
```

### ★★★★★ 三个模式的完整标准值

| 模式 | `scoreLimit` | `timeLimitMinutes` | `roundSwitch` | `roundLimit` | `winLimit` |
|---|---|---|---|---|---|
| **`sd`** | — | **2** | **8** | **17** | **9** |
| **`cha`** | **50** | **10** | — | — | — |
| **`tdm`** | **75** | **10** | — | — | — |

### ★★★★★ `sd` 的四个值从哪来（第 333–338 行，逐字）

```cpp
// 取值出处（**不拍脑袋**）：
//   * **sd**：这些列表自己的描述文案「**率先取胜9回合，8回合后双方换边**」⇒
//     **winLimit=9 / roundSwitch=8**；**roundLimit=17**（9-8 结束所需的**最大回合数**）；
//     **timeLimitMinutes=2** 与既有 sd 分支缺省一致
//   * **cha**：代码注释记载的发行方规则值「**scr_cha_scorelimit 50 / scr_cha_timelimit 10**」
```

★★★ **⇒ `sd` 的四个值有**精确出处**：**
```
**描述文案**：「率先取胜 **9** 回合,**8** 回合后双方换边」
        ↓
`winLimit = **9**` / `roundSwitch = **8**`
        ↓
★★★ `roundLimit = **17**` = **9-8 结束所需的最大回合数**
   ⇒ 推导：先赢 9 局需要最少 9 回合；若双方交替（8:8）则需 17 回合
        ↓
`timeLimitMinutes = **2**`（与既有 sd 分支缺省一致）
```

★ **⇒ 第 3 条的 `17 = 9 + 8` ⇒ **最大回合数**的精确推导。**

### ★★★ 触发场景（第 323–332 行，逐字）

```cpp
// 依据：`mp_playlists_shipRetail_release.info` 里的 **17 个 "Map: X" 排位列表**
// （playlist **110/111/125/190/223/224/226/238/239/240/241/242/247/248/250/252/253**）
// **全部不带任何 `scr_sd_*` / `scr_cha_*` 规则行**；
// 老外的 legacy 选择路径要求"候选里能解析出的规则必须唯一共识，全解析不出即拒绝"
// ⇒ **突尼斯（`mp_tunisia+sd`）被 `match_rules_rejected playlist=34 rotation=0
//    map=mp_tunisia gametype=sd` 拒绝**。
// 坠机之地此前能进纯属侥幸：唯一的规则携带者 = **playlist 133 "Express"**
// （`roundswitch 1 / roundlimit 7 / winlimit 4`）。
```

★★★ **⇒ 五个精确事实：**
```
① ★★ **17 个 "Map: X" 排位列表**全部无 `scr_*` 规则行
② 完整列表：**110/111/125/190/223/224/226/238/239/240/241/242/247/248/250/252/253**
③ ★★★ **突尼斯被拒**：`match_rules_rejected playlist=34 rotation=0 map=mp_tunisia gametype=sd`
④ ★★ **坠机之地此前能进是侥幸**：唯一规则携带者 = **playlist 133 "Express"**
   （`roundswitch 1 / roundlimit 7 / winlimit 4`）
```

---

## 五、★★★★★ **`applyPlaylistAuthorFields` 的 D1b 透传**

### 5.1 ★★★★★ 完整实现（第 385–410 行）

```cpp
void applyPlaylistAuthorFields(MatchRules &rules, const Playlist &playlist)
{
    if (findProperty(playlist, "**combattraining**").has_value())
        rules.combatTraining = **1**;
    if (const auto value = findProperty(playlist, "**difficulty**"); value && !value->empty())
        if (const auto parsed = parseRuleU32(*value)) rules.difficulty = *parsed;
    if (const auto value = findProperty(playlist, "**vsrule**"); value && !value->empty())
    {
        const auto digits = value->substr(0, value->find_first_not_of("0123456789"));
        if (const auto parsed = parseRuleU32(digits)) rules.teamSize = *parsed;   // ★ "6V6" ⇒ 6
    }
    if (const auto value = findProperty(playlist, "**maxhumanplayersperteam**"); value && !value->empty())
        if (const auto parsed = parseRuleU32(*value)) rules.maxHumanPlayersPerTeam = *parsed;
}
```

### ★★★★★ 四个作者字段

| 字段 | 处理 |
|---|---|
| **`combattraining`** | ★ **裸旗标** ⇒ `combatTraining = 1` |
| **`difficulty`** | 解析 u32 |
| **`vsrule`** | ★★ **取开头的十进制数字**（`"6V6"` ⇒ **6**、`"9V9"` ⇒ **9**） |
| **`maxhumanplayersperteam`** | 解析 u32 |

★★★ **⇒ 与报告 093/113 的 `properties` 容器**完全对应** ✓**

### ★★★★★ 为什么必须作用在**最终返回的 rules** 上（第 381–384 行，逐字）

```cpp
// **为什么单独成一个函数、并在 `resolveMatchRules` 的返回点调用**：
// 人机播单（**184/159/123**）**没有** `scr_sd_*` 规则行 ⇒ `parseMatchRules` 会返回
// `nullopt`，最后走 `fallbackMatchRules`。
// 若把搬运写在 `parseMatchRules` 里，这条（正是我们需要的）路径会把作者字段**丢掉**。
// ⇒ **搬运必须作用在最终返回的那个 rules 上**。
```

★★★ **⇒ 三个精确的播单号：**`184` / `159` / `123`（人机播单）。**

★ **⇒ 与报告 079 的 playlist **123**（`sd`×8，`combattraining`+`onboardbonus`）**完全对应** ✓**
**⇒ 且 `159`/`160` 是 StreakBreak 段（报告 079 已记录）。**

---

## 六、★★★★★ **`member selection differs` 的 rotationIndex 不比较**

### 6.1 ★★★★★ 完整注释（第 806–810 行，逐字）

```cpp
// **rotationIndex is deliberately not compared**: a live client reported **5 against a
// booking command of 8**, and **12 against 0**, while its **map matched the command every
// time**. Comparing a field **measured not to track anything** would report divergence on
// identical selections.
```

★★★★★ **⇒ 三个精确观测：**
```
客户端报 `rotationIndex = **5**`,而 booking command 是 **8**
客户端报 `rotationIndex = **12**`,而 booking command 是 **0**
        ↓
★★★ 但**地图每次都匹配**
        ↓
★★★ ⇒ 结论：**`rotationIndex` 不追踪任何东西**（不要比较它）
```

★★ **⇒ 这与报告 079 的"playlist N 是启用条目序号,不是发行版 id"**完全呼应** ✓**

### ★★★ 完整的比较字段（第 811–813 行）

```cpp
if (memberSelection.playlistId == selection->playlistId &&
    memberSelection.mapName == selection->mapName &&
    memberSelection.gameType == selection->gameType)
{
    continue;   // ★ 三个字段都匹配 ⇒ 不报警
}
```

★★ **⇒ 只比较 **3 个字段**：`playlistId` / `mapName` / `gameType`（**不含 `rotationIndex`**）。**

### ★★★★★ 为什么只信房主的选择（第 766–777 行，逐字）

```cpp
// The **ROSTER OWNER's selection is the match's selection**. Its booking command is already
// the only one honoured a few lines up (non_owner_booking_ignored), so requiring every member
// to have independently arrived at the same one was **a stricter rule than the booking itself
// follows**.
//
// It held only because **search and destroy books a slot whose rotation always rolls index 0**,
// so every client trivially agreed. **Free-for-all offers 14 maps under
// `playlistMapRotateSequentially 0`**, so **each client rolls its own** - observed as one
// client on rotation **7** and the other on **8** - and **no free-for-all session could ever
// be assembled**.
```

★★★★★ **⇒ 一个精确的"为什么 FFA 永远组不起来"：**
```
`sd` ⇒ **rotation 总是 index 0** ⇒ 所有客户端**天然一致**
        ↓
★★★ 而 `FFA` 有 **14 张地图** + **`playlistMapRotateSequentially 0`**
   ⇒ **每个客户端自己 roll**
   ⇒ 观测到一个在 rotation **7**、另一个在 **8**
        ↓
★★★★★ ⇒ **"no free-for-all session could ever be assembled"**
```

★ **⇒ `playlistMapRotateSequentially` = **0** ⇒ 与报告 079 的 `mp_playlists` 的
`set playlistMapRotateSequentially 0` **完全对应** ✓**

---

## 七、★★★★ **主循环的完整流程与五种诊断**

### 7.1 ★★★★★ 完整流程（第 611–922 行）

```
① `state->ready.wait(...)` ⇒ 等命令
        ↓
② 取 `command` + `requestId`
        ↓
③ **获取名册**（`rosterProvider` 或单成员兜底）
   ⇒ 重试 **150 次 × 100 ms**（= 15 秒）
        ↓
④ ★★★ **平台 id → DW 账号 id 映射**（d35/d36/d37）
        ↓
⑤ **校验名册**（`invalid_room_roster` 若：id/port/ready 无效、id 重复、**bridge 对重复**）
        ↓
⑥ ★★ **非房主 ⇒ `non_owner_booking_ignored`**（`localUserId != ownerUserId`）
        ↓
⑦ **逐个成员 `CaptureLoadout`**（重试 **3 次 × 200 ms**，超时 **2500 ms**）
        ↓
⑧ **解码 `ClientSessionCapture`** ⇒ `invalid_client_descriptor` 若失败
        ↓
⑨ **房主的选择 = 比赛的选择**；其他成员的选择只记日志
        ↓
⑩ ★★★ **`entitlementCheck(platformMemberIds[i], items)`** ⇒ `entitlement_rejected`
        ↓
⑪ **`matchRulesProvider(selection)`** ⇒ `match_rules_rejected`
        ↓
⑫ **`UpdateLoadout` 刷新每个成员**（超时 2500 ms）
        ↓
⑬ **`SessionStart` 提交到专服控制口**（超时 2500 ms）
        ↓
⑭ 诊断：**`accepted=true`** 或 **`dedicated_submit_failed`**
```

### ★★★★★ 八种诊断结果

| # | 诊断串 | 触发 |
|---|---|---|
| **1** | **`room_roster_failed`** | 名册取不到 / generation 不符 / 空 |
| **2** | **`invalid_room_roster`** | id/port/ready 无效 / 重复 id / **重复 bridge 对** |
| **3** | **`non_owner_booking_ignored`** | `localUserId != ownerUserId` |
| **4** | **`client_capture_failed`** | `CaptureLoadout` 三次都失败 |
| **5** | **`invalid_client_descriptor`** | `ClientSessionCapture` 解码失败 |
| **6** | **`entitlement_rejected`** | 缺权益（现在会**自动补种**） |
| **7** | **`match_rules_rejected playlist=N rotation=N map=X gametype=Y`** | 规则解析失败 |
| **8** | **`accepted=true`** / **`dedicated_submit_failed`** | 最终提交 |

★★★ **⇒ 第 7 条的诊断串**极其详细**（含四个字段）：**
```
`match_rules_rejected playlist=<N> rotation=<N> map=<X> gametype=<Y>`
        ↓
★★★ 理由（逐字）："A **bare verdict** here cost a whole test cycle:
   the rejection could be an absent playlist id, a map/mode pair in no rotation at all,
   or rules that failed to validate, and **the three need completely different fixes**."
```

### ★★★ `submit` 的队列上限（第 939–951 行）

```cpp
bool DedicatedBookingDispatcher::submit(std::string command)
{
    if (!state_ || command.empty()) return false;
    {
        const std::lock_guard lock(state_->mutex);
        if (state_->stopping || state_->commands.size() >= **8**)     // ★ 上限 8
            return false;
        state_->commands.push_back(std::move(command));
    }
    state_->ready.notify_one();
    return true;
}
```

★★ **⇒ 队列上限 **8**（超了直接拒）。**

### ★★★ 四个重试常量（第 65–68 行）

```cpp
constexpr std::size_t ClientCaptureAttempts = **3**;
constexpr auto ClientCaptureRetryDelay = std::chrono::milliseconds(**200**);
constexpr std::size_t RoomRosterAttempts = **150**;
constexpr auto RoomRosterRetryDelay = std::chrono::milliseconds(**100**);
```

★★★ **⇒ 两个重试窗口：**
```
`ClientCapture` ⇒ **3 次 × 200 ms** = 400 ms
`RoomRoster`    ⇒ **150 次 × 100 ms** = **15 秒**
```

### ★★★ `requestedItems` 的去重（第 109–134 行）

```cpp
if (request.characterItemIds.front())
    result.push_back(request.characterItemIds.front());      // ★ 只取第 0 个角色物品
for (classIndex...) {
    if (!(request.classMask & (1u << classIndex))) continue; // ★ 只处理启用的类
    for (weapon...) {
        result.push_back(weapon.itemId);                     // ★ 含 0（不检查）
        for (attachmentItemIds) if (itemId) result.push_back(itemId);  // ★ 跳过 0
    }
}
std::ranges::sort(result);
result.erase(std::unique(...), result.end());                // ★ 排序去重
```

★★★ **⇒ 一个**不一致**：`weapon.itemId` **不检查 0**,而 `attachmentItemIds` **检查 0**。**
**⇒ 记录为**待核对项**。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **两个命名空间** | LSG/房间层 = **`0x01100001DEADC0DE`**（76,561,201,696,194,782）；netchan/战斗服 = **`0xE7C8A98A6B4C2D0E`**（16,701,785,630,074,219,790） |
| 2 | ★★★★★ **d35 拒单日志** | `connectionless rejected reason=getchallenge XUID is not in the session roster (xuid=16701785630074219790 pending=gen1[0x01100001deadc0de,];active=none;)` |
| 3 | ★★★★★ **三次实测修正** | **d35** 映射名册 / **d36** 也映射 `ownerUserId` / **d37** entitlement 用**原始平台 id** |
| 4 | ★★ d36 的后果 | 不映射 ⇒ **`non_owner_booking_ignored`** ⇒ 无 SessionStart ⇒ **`GAMESTATE_NOT_CONFIGURED`** 卡"设置游戏" |
| 5 | ★★ d37 的后果 | 映射后喂 ⇒ **`entitlement_rejected`**（**items 不变、仅 id 变即失败**） |
| 6 | ★★★ 最终实现 | **映射前按位留一份原始 id**,供 entitlement 专用 |
| 7 | ★★★★★ **`mp_nuked,cha` 的分歧** | 出现在 **10 个播单**,**5 个**通过校验,**分两派**：**Skirmish/Onboarding 50/10**（行 478/512）vs **Ground War/Map: Nuketown(110)/Charge-9v9(160) 150/20**（行 1693/615/2221） |
| 8 | ★★★★★ **取值规则** | **`rotation` 条目最少的那个播单**说的算；**同专用度仍分歧 ⇒ 拒绝** |
| 9 | ★★ 依据 | 单条目 "Map: X" 列表是**玩家点那张图时实际启用的列表** ⇒ **专用度最高** |
| 10 | ★★★★★ **`ffa` 的 oracle 论证** | 两个 FFA playlist（**23 "Free For All"** / **154 "Snipers Only"**）**无 `scr_*` 规则** ⇒ 限额是 gametype 默认；**30/10 从 `C-2021-7-25[1-19-26]dm.demo` 的 cs 467/468 读出** |
| 11 | ★★★★ **oracle 的方法** | 467/468 是**唯一在两个 cha demo 里都读到 50 和 10,且能区分其他所有模式的候选** |
| 12 | ★★★ **四模式限额对照** | **cha 50/10** / **war 75/10** / **dom 200/0** / **chicken 300/15** |
| 13 | ★★★ configstring 15 公式 | **`matchStartServerTime + minutes * 60 * 1000`**（**uint64**）；60 分钟 = **3,600,000 ms** |
| 14 | ★★★ TODO | **上游化前恢复 10**（零售值） |
| 15 | ★★ `ffaScoreLimit` 边界 | **1..1000**（0 ⇒ 无分数上限 ⇒ 比赛永不结束） |
| 16 | ★★★★★ **`fallbackMatchRules` 三模式** | **`sd` ⇒ 2/8/17/9**（timeLimit/roundSwitch/roundLimit/winLimit）；**`cha` ⇒ 50/10**；**`tdm` ⇒ 75/10** |
| 17 | ★★★★★ **`sd` 四值的出处** | 描述文案「率先取胜 **9** 回合,**8** 回合后双方换边」⇒ `winLimit=9` / `roundSwitch=8`；**`roundLimit=17 = 9+8`**（最大回合数）；`timeLimit=2` |
| 18 | ★★★★ **17 个 "Map: X" 列表** | **110/111/125/190/223/224/226/238/239/240/241/242/247/248/250/252/253** ⇒ 全无 `scr_*` 规则 |
| 19 | ★★★ **突尼斯被拒** | `match_rules_rejected playlist=34 rotation=0 map=mp_tunisia gametype=sd` |
| 20 | ★★★ **坠机之地是侥幸** | 唯一规则携带者 = **playlist 133 "Express"**（`roundswitch 1 / roundlimit 7 / winlimit 4`） |
| 21 | ★★★★ **`applyPlaylistAuthorFields`** | `combattraining`(裸旗标⇒1) / `difficulty` / **`vsrule`（取开头数字：`6V6`⇒6）** / `maxhumanplayersperteam` |
| 22 | ★★★★ 为什么作用在**最终 rules** | 人机播单 **184/159/123** 无 `scr_sd_*` ⇒ 走 `fallbackMatchRules` ⇒ 写在 `parseMatchRules` 里会**丢掉作者字段** |
| 23 | ★★★★★ **`rotationIndex` 不比较** | 客户端报 **5 vs command 8**、**12 vs 0**,但**地图每次都匹配** ⇒ 该字段**不追踪任何东西** |
| 24 | ★★ 只比较 3 字段 | `playlistId` / `mapName` / `gameType` |
| 25 | ★★★★★ **为什么 FFA 组不起来** | `sd` 的 rotation **总是 index 0** ⇒ 天然一致；**FFA 有 14 张图 + `playlistMapRotateSequentially 0`** ⇒ **每个客户端自己 roll**（观测到 7 vs 8）⇒ **"no free-for-all session could ever be assembled"** |
| 26 | ★★★ **八种诊断** | `room_roster_failed` / `invalid_room_roster` / `non_owner_booking_ignored` / `client_capture_failed` / `invalid_client_descriptor` / `entitlement_rejected` / `match_rules_rejected playlist=N rotation=N map=X gametype=Y` / `accepted=true`\|`dedicated_submit_failed` |
| 27 | ★★ 详细诊断的理由 | "A **bare verdict** cost a whole test cycle... **the three need completely different fixes**" |
| 28 | ★★ `submit` 队列上限 | **8** |
| 29 | ★★★ 四个重试常量 | `ClientCapture` **3 × 200 ms** / `RoomRoster` **150 × 100 ms = 15 秒** |
| 30 | ★★★ `requestedItems` 的不一致 | `weapon.itemId` **不检查 0**,`attachmentItemIds` **检查 0** ⇒ 待核对 |

---

## 九、结论

### 1. ★★★★★ **平台 id → DW 账号 id 的映射经过**三次实测修正**（d35/d36/d37）

```
d35：名册要 DW 账号 id（否则 `getchallenge` 被拒）
d36：`ownerUserId` 是独立字段,必须一起映射（否则 `non_owner_booking_ignored`）
d37：`entitlementCheck` 仍要**原始平台 id**（市场按平台 id 记账）
        ↓
★★★★★ 最终：**映射前按位留一份原始 id,供 entitlement 专用**
```

### 2. ★★★★★ **`match_rules_rejected` 的"载体专用度"取值规则**

★ **⇒ 分歧时**取 `rotation` 条目最少的播单**,同专用度仍分歧才拒绝。**

### 3. ★★★★★ **`ffa` 的 30/10 是用"oracle"从 cs 467/468 反推出来的**

★ **⇒ 判据：唯一在两个 cha demo 里都读到 50/10 且能区分 `chicken 300/15` 的候选。**

### 4. ★★★★★ **`fallbackMatchRules` 的三个模式标准值都有精确出处**

★ **⇒ 尤其 `sd` 的 `roundLimit = 17 = 9 + 8`（最大回合数）。**

### 5. ★★★★★ **`rotationIndex` 不追踪任何东西**（观测到 5 vs 8、12 vs 0 但地图匹配）

### 6. ★★★★★ **FFA 永远组不起来的原因**（`playlistMapRotateSequentially 0` + 14 张图 ⇒ 各自 roll）

### 7. ★★★★ **八种诊断结果**,其中 `match_rules_rejected` 带四个字段

### 8. ★★★ **`requestedItems` 有一处 0 检查的不一致**

---

## 十、下一步

- `DedicatedBookingDispatcher.hpp`（62 行）
- `SharedRoomClient`（180 + 41）/ `SharedRoomControl`（426 + 76）/ `SharedRoomHost`（49）/ `SharedRoomSessionOwner`（163 + 66）
- `IServer.hpp`（2 行）
- 然后 `game_server` 根 32 文件
