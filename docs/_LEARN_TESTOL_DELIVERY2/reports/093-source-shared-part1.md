# 学习报告 093（重开）— `source\src\shared\`（10 文件 / 112,091 B）

**学习范围**：`shared\CodolPlaylist.cpp`（7,963 B / 197 行）+ `.hpp`（3,841 B / 90 行）+ `DedicatedSession.hpp`（5,772 B / 146 行）+ `.cpp`（22,221 B / 582 行）
**性质**：全实测（**4 个文件逐行读完**）
**★★★★★ 本报告收录四个重大发现**：①**token 表只有 3 项,有 CODREF 三重证据** ②**playlist 解析器的完整契约（含 D1a 作者字段）** ③**`DedicatedSession` 的完整线上格式（`OLDS` magic / v5–v8）** ④**`MatchRules` 的逐 gametype 校验规则**

---

## 一、★★★★★ **`CodolPlaylist.cpp` 的 token 表（3 项,CODREF 三重证据）**

### 1.1 ★★★★★ 完整的映射表（第 73–78 行，逐字）

```cpp
using BookingTokenGameType = std::pair<std::string_view, std::string_view>;
constexpr std::array<BookingTokenGameType, 3> BookingTokenGameTypes{ {
    { "ffa", "dm" },
    { "tdm", "war" },
    { "kc",  "conf" },
} };
```

★★★ **⇒ **只有 3 项**（不是 4、5 或更多）。**

### 1.2 ★★★★★ **CODREF 的三重独立证据**（第 69–87 行，逐字）

```cpp
// A rotation entry names what the client BOOKS. For three modes the engine
// gametype is a different string, and it is the engine name that every
// derived name is built from - g_gametype, mp_<x>_spawn, scr_<x>_* and the
// shipped per-gametype assets.
//
// CODREF, three independent sources in the shipped 3.3.3.3 install:
//  - 262 mp_constbaselines_bl_pc_<map>_<gametype>.bin rawfiles across the
//    fastfiles name dm (25 maps), war (23) and conf (24). None is named ffa,
//    tdm or kc.
//  - every playlist whose rotation says tdm declares scr_war_scorelimit and
//    scr_war_timelimit (e.g. playlist 30, "Ground War").
//  - the retail demo C-2021-7-25[1-19-26]dm.demo carries serverinfo
//    \g_gametype\dm on mp_cross_fire, which is entry [3] of playlist 23's ffa
//    rotation.
//
// These are the stock IW names - dm.gsc is free-for-all and war.gsc is team
// deathmatch in CoD4/MW2/MW3 - kept underneath CODOL's booking vocabulary.
// Anything unlisted is returned unchanged, and both directions are total, so
// callers can normalise without knowing which vocabulary they were handed.
```

### ★★★★★ 三重证据的完整拆解

| # | 证据 | 精确数据 |
|---|---|---|
| **1** | ★★★ **262 个 `mp_constbaselines_bl_pc_<map>_<gametype>.bin`** rawfile | **`dm` 25 张地图 / `war` 23 / `conf` 24**；★★★ **没有任何一个叫 `ffa`/`tdm`/`kc`** |
| **2** | ★★ **凡 rotation 写 `tdm` 的 playlist 都声明 `scr_war_scorelimit` + `scr_war_timelimit`** | 例：**playlist 30 "Ground War"** |
| **3** | ★★★ **零售录像 `C-2021-7-25[1-19-26]dm.demo`** | serverinfo 带 **`\g_gametype\dm`** on `mp_cross_fire`,即 **playlist 23 的 `ffa` rotation 的 entry [3]** |

★★★ **⇒ 证据 1 的算术自洽：**25 + 23 + 24 = **72**（而总数是 262 ⇒ 每张图有多个变体）。**

★★ **⇒ 证据 2 与我在报告 079 的观察**完全吻合**：**
```
报告 079：`mp_playlists` 的 playlist 30（cat=3, `tdm`×13）…
          而 playlist 4 声明 `rule scr_cha_*`
        ↓
本报告：★ "every playlist whose rotation says `tdm` declares
        **`scr_war_scorelimit` and `scr_war_timelimit`**"
        ↓
★★★ ⇒ **代码级证实**：rotation 写 `tdm` ⇒ 规则前缀是 `scr_war_`（不是 `scr_tdm_`）
```

★★★ **⇒ 证据 3 与报告 074 的 `dm.lua` 注释**完全吻合**：**
```
`dm.lua`：`C-2021-7-25[1-19-26]dm.demo` / `mp_cross_fire` / 8 clients
        ↓
本报告：同一份录像,★ 且它**是 playlist 23 的 ffa rotation 的 entry [3]**
        ↓
★★★ ⇒ 报告 079 记录的 playlist 23 = `ffa`（cat=10）**得到代码级证实** ✓
```

### ★★★ "stock IW names" 的血统声明（逐字）

```
"These are the **stock IW names** - **dm.gsc is free-for-all** and
 **war.gsc is team deathmatch** in **CoD4/MW2/MW3** -
 kept underneath CODOL's **booking vocabulary**."
        ↓
★★★ ⇒ 三层命名：
  **CODOL booking token**（`ffa` / `tdm` / `kc`）
  **引擎 gametype**（`dm` / `war` / `conf`）
  **IW 原版脚本名**（`dm.gsc` / `war.gsc`）
        ↓
★★★ 且 `conf` 对应的是 IW 的 Kill Confirmed（MW3 引入）
```

### ★★★ 双向归一化（第 163–175 行）

```cpp
std::string_view engineGameType(const std::string_view bookingToken)
{
    const auto found = std::ranges::find(
        BookingTokenGameTypes, bookingToken, &BookingTokenGameType::first);
    return found == BookingTokenGameTypes.end() ? bookingToken : found->second;
}

std::string_view bookingToken(const std::string_view gameType)
{
    const auto found = std::ranges::find(
        BookingTokenGameTypes, gameType, &BookingTokenGameType::second);
    return found == BookingTokenGameTypes.end() ? gameType : found->first;
}
```

★★★ **⇒ **未列出的原样返回**,两个方向都是**全函数**（total）⇒ 调用方无需知道自己拿到的是哪套词汇。**

★★ **⇒ 这与报告 090 的"两插件命名空间不相交"是**同一种设计哲学**（宽容归一化）。**

---

## 二、★★★★★ **`CodolPlaylist` 解析器的完整契约**

### 2.1 ★★★ 支持的关键字（只有 5 种）

| 关键字 | 处理 |
|---|---|
| **`version <N>`** | ★ 解析为 `Document::version` |
| **`playlist <id>`** | ★ 开新 playlist；**重复 ID ⇒ 整体失败**（`return std::nullopt`） |
| **`rule <name> <value>`** | 进 `Playlist::rules` |
| **`<map>,<gametype>,<weight>`** | ★ 进 `Playlist::rotation`（**必须恰好 2 个逗号**） |
| ★★ **其他 `keyword [value]`** | ★★★ 进 `Playlist::properties`（**D1a 新增**） |

### 2.2 ★★★ `parseRotationEntry` 的严格校验（第 48–70 行）

```cpp
const auto firstComma = line.find(',');
if (firstComma == std::string_view::npos) return std::nullopt;
const auto secondComma = line.find(',', firstComma + 1);
if (secondComma == std::string_view::npos ||
    line.find(',', secondComma + 1) != std::string_view::npos)   // ★ 第三个逗号 ⇒ 拒
    return std::nullopt;

const auto mapName  = trim(line.substr(0, firstComma));
const auto gameType = trim(line.substr(firstComma + 1, secondComma - firstComma - 1));
const auto weight   = parseU32(trim(line.substr(secondComma + 1)));
if (!validName(mapName) || !validName(gameType) || !weight || !*weight)
    return std::nullopt;
```

★★★ **⇒ 四条精确校验：**
```
① **恰好 2 个逗号**（第 3 个 ⇒ 拒）
② `validName(mapName)` ⇒ 只允许 `[A-Za-z0-9_]`
③ `validName(gameType)` ⇒ 同上
④ ★★ **`weight` 必须存在且非零**（`!*weight` ⇒ 拒）
        ↓
★★★ ⇒ **`weight = 0` 的 rotation 行会被丢弃**！
```

★★ **⇒ 这解释了报告 079 的 `mp_playlists` 里**为什么没有 weight=0 的行** —— 解析器会拒。**
**⇒ 而 `[map_loads_ratio]` 里的 `0,` 是**另一个文件、另一套解析器**（不是这里）。**

### 2.3 ★★★★★ **D1a：作者字段的完整背景（第 34–47 行 + 149–156 行，逐字）**

```cpp
// ★★★ 2026-10-13（D1a，会话 2130）-- 官方播单里**不带 `rule` 前缀**的作者字段。
//
// 为什么需要：发布播单 `mp_playlists_shipRetail_release.info` 的"人机混战"语义是这么写的：
//     combattraining            ← **裸旗标**（整行没有值）
//     difficulty 1
//     vsrule "6V6"
//     maxhumanplayersperteam 3
// 而本解析器原先**只收 `rule <name> <value>`**（`.cpp:130-135`）⇒ 上面四行被**静默丢弃**
// ⇒ 后端读不到"这是官方人机混战、难度 1、6V6、每队最多 3 真人"（依据
// `推进-地图内官方bot-…-1900.md` §2①「全树 grep combattraining/maxhumanplayersperteam = 0 命中」）。
//
// 纪律（`rope` §2.3 单变量）：本容器**只收录**，**不参与任何既有判定**；模式规则（`scr_*`）仍走 `rules`，
// 两套不混。值去外层双引号；裸旗标的 value 为空串（`findProperty` 返回**有值**的空串）。
```

★★★★★ **⇒ 这是我在报告 079 观察到的 `combattraining` / `difficulty` / `vsrule` / `maxhumanplayersperteam` 的**代码级归属**：**
```
报告 079：`mp_playlists` 的 playlist 里有 `combattraining`（裸旗标）/
          `difficulty 0` / `vsrule "6V6"` / `maxhumanplayersperteam 3`
        ↓
本报告：★★★ **原先解析器把这些行静默丢弃**
   ⇒ 修复（2026-10-13 D1a）把她们收进 `properties`
   ⇒ ★★★ 且**纪律明确**："只收录,不参与任何既有判定"
```

★★ **⇒ 关键背景（逐字）：**
```
"依据 `推进-地图内官方bot-…-1900.md` §2①
 「全树 grep **combattraining** / **maxhumanplayersperteam** = **0 命中**」"
        ↓
★★★ ⇒ 即：这两个关键字在**整棵树里原本 0 命中** ⇒ 是**新发现的官方字段**
```

### 2.4 ★★★ `unquote`（第 31–37 行）

```cpp
// ★ D1a：作者字段的值可能带外层双引号（`vsrule "6V6"` / `name english "Skirmish"`）⇒ 去掉一层。
std::string_view unquote(const std::string_view value)
{
    if (value.size() >= 2 && value.front() == '"' && value.back() == '"')
        return value.substr(1, value.size() - 2);
    return value;
}
```

★★ **⇒ 与报告 079 的 `name english "Skirmish"` 完全对应。**

### 2.5 ★★★ 解析失败的两个条件（第 158–160 行）

```cpp
if (!result.version || result.playlists.empty())
    return std::nullopt;
```

★★ **⇒ 必须有 `version` 行且至少 1 个 playlist。**

★★ **⇒ 与报告 079 的 `mp_playlists` 第 1 行 `version 796` 对应 ✓**

### 2.6 ★★★ 注释行与空行

```cpp
if (line.empty() || line.starts_with("//"))
    continue;
```

★ **⇒ 只认 `//` 前缀（报告 079 的 `mp_playlists` 确实全用 `//`）。**
**⇒ `[leaderboard]` 那种 `#` 注释在这个解析器里**不被识别**（但那是另一个文件）。**

---

## 三、★★★★★ **`DedicatedSession` 的完整线上格式**

### 3.1 ★★★★★ 三个 magic 与三种 payload（第 11–14 行）

```cpp
constexpr std::uint32_t PayloadMagic = 0x53444C4F; // **OLDS**
constexpr std::uint16_t LoadoutPayloadKind              = 1;
constexpr std::uint16_t SessionStartPayloadKind         = 2;
constexpr std::uint16_t ClientSessionCapturePayloadKind = 3;
```

★★★ **⇒ `0x53444C4F` 小端 = `4F 4C 44 53` = **`OLDS`** = **O**l-mod **L**oadout/**D**edicated **S**ession。**

| kind | 名称 | 用途 |
|---|---|---|
| **1** | **`LoadoutPayloadKind`** | 单独传配装 |
| **2** | **`SessionStartPayloadKind`** | ★★ **会话开始（含全部成员）** |
| **3** | **`ClientSessionCapturePayloadKind`** | ★★ **客户端会话捕获** |

### 3.2 ★★★★★ 通用头（第 198–203 行）

```cpp
void writeHeader(Writer &writer, const std::uint16_t kind)
{
    writer.u32(PayloadMagic);                                  // 4 字节
    writer.u16(OlMod::DedicatedSession::SchemaVersion);         // 2 字节
    writer.u16(kind);                                          // 2 字节
}
```

★★★ **⇒ 头是 **8 字节**：`magic(4) + version(2) + kind(2)`,**全部小端**。**

### 3.3 ★★★★★ 版本接受范围（第 205–214 行）

```cpp
return reader.u32(magic) && reader.u16(version) && reader.u16(kind) &&
    magic == PayloadMagic &&
    (version >= 5 && version <= OlMod::DedicatedSession::SchemaVersion) &&
    kind == expectedKind;
```

★★★ **⇒ 接受 **v5 – v8**（当前是 v8）。**

★★ **⇒ 头文件注释（逐字）：**
```
"Kept in lockstep with `configure-session.py` and `ClientSessionCapture`.
 **Version 8 adds the current perk/equipment/reward loadout fields**;
 accepting only version 5 **rejects every live booking before world initialization**."
        ↓
★★★ ⇒ 版本演进：
  **v5** ⇒ 基础
  **v6** ⇒ 加 `perkItemIds`（`if (version >= 6)`）
  **v7** ⇒ 加 `equipment`（`if (version >= 7)`）
  **v8** ⇒ 加 `rewardItemIds`（`if (version >= 8)`）
```

### 3.4 ★★★★★ `SessionStart` 的完整字段布局（第 480–500 行）

```cpp
Writer writer;
writeHeader(writer, SessionStartPayloadKind);
writer.u16(members.size());
writer.u16(bookingCommand.size());
writeBookingBody(writer, request.booking);
writeMatchRulesBody(writer, request.matchRules);
writer.text(request.bookingCommand);
for (const auto &member : request.members)
{
    writer.u64(member.userId);
    writer.u16(member.username.size());
    writer.u16(0);                                  // ★ 保留
    writeLoadoutBody(writer, member.loadout);
    writer.text(member.username);
}
```

### ★★★★★ 完整的 `SessionStart` 线格式

```
偏移  类型    字段
 0    u32     magic = 'OLDS' (0x53444C4F)
 4    u16     schemaVersion (5..8)
 6    u16     kind = 2
 8    u16     memberCount
10    u16     bookingCommandSize
12    u32     playlistId
16    u32     rotationIndex
20    u16     mapNameSize
22    u16     gameTypeSize
24    ...     mapName bytes
      ...     gameType bytes
      u32×6   playlistVersion, scoreLimit, timeLimitMinutes,
              roundSwitch, roundLimit, winLimit
      u32×4   combatTraining, difficulty, teamSize, maxHumanPlayersPerTeam   ★ D1b
      ...     bookingCommand bytes
      ┌─ 每个 member ─────────────────────────┐
      │ u64   userId                          │
      │ u16   usernameSize                    │
      │ u16   reserved (必须 0)                │
      │ ...   loadoutBody                     │
      │ ...   username bytes                  │
      └───────────────────────────────────────┘
```

★★ **⇒ 注意**顺序**：`bookingCommand` 在 `matchRules` **之后**,而 member 的 `username` 在 `loadout` **之后**。**

### 3.5 ★★★★★ `LoadoutRequest` 的完整布局（第 216–244 行）

```cpp
writer.u32(request.characterIndex);
writer.u8(request.classMask);
writer.u8(0);      // 保留
writer.u16(0);     // 保留
for (const auto itemId : request.characterItemIds)   // × 12
    writer.u32(itemId);
for (const auto &loadoutClass : request.classes)     // × 5
{
    for (const auto &weapon : loadoutClass.weapons)  // × 2
    {
        writer.u32(weapon.itemId);
        for (const auto attachmentItemId : weapon.attachmentItemIds)  // × 6
            writer.u32(attachmentItemId);
    }
    for (const auto perkItemId : loadoutClass.perkItemIds)   // × 6
        writer.u32(perkItemId);
    for (const auto itemId : loadoutClass.equipment.itemIds) // × 2
        writer.u32(itemId);
    writer.u8(loadoutClass.equipment.doubleAmmoMask);
    writer.u8(0);
    writer.u16(0);
}
for (const auto itemId : request.rewardItemIds)      // × 3
    writer.u32(itemId);
```

### ★★★★★ 完整的 `LoadoutRequest` 字节数（v8）

```
u32 characterIndex                  =  4
u8  classMask                       =  1
u8  reserved                        =  1
u16 reserved                        =  2
12 × u32 characterItemIds           = 48
5 × ( 2 × (4 + 6×4)                 = 5 × 2 × 28 = 280
    + 6 × 4                         = 24
    + 2 × 4                         =  8
    + 1 + 1 + 2                     =  4 )  = 5 × 316 = **1,580**
3 × u32 rewardItemIds               = 12
        ↓
★★★ **v8 总计 = 4+1+1+2+48+1580+12 = 1,648 字节**
```

★★ **⇒ 这是一个**可以手算验证的精确布局**（与报告 080 的 `22×2×1024 ≈ 45,000` 同一性质）。**

### 3.6 ★★★★★ 八个结构常量（`DedicatedSession.hpp:15-26`）

| 常量 | 值 | 含义 |
|---|---|---|
| **`SchemaVersion`** | ★ **8** | 当前协议版本 |
| **`RewardSlotCount`** | **3** | 奖励槽数 |
| **`CharacterItemCount`** | **12** | 角色物品数 |
| **`LoadoutClassCount`** | **5** | 配装类数 |
| **`WeaponsPerClass`** | **2** | 每类武器数（主/副） |
| **`AttachmentCount`** | **6** | 每武器配件数 |
| **`PerkSlotCount`** | **6** | 特长槽数 |
| **`MaximumUsernameSize`** | **16** | ★★ 用户名上限（**字节**） |
| **`MaximumBookingCommandSize`** | **1,024** | booking 命令上限 |
| **`MaximumMapNameSize`** | **64** | 地图名上限 |
| **`MaximumGameTypeSize`** | **32** | gametype 上限 |
| **`MaximumSessionMembers`** | ★★ **18** | ★★★ 会话成员上限（**= `MaximumGameClients`**） |

★★★★★ **⇒ `MaximumSessionMembers = 18` 与报告 071 的**
**"`MaximumGameClients (18) .. SvAgentSlotCount (32)`"** **完全吻合** ✓**
**⇒ 这是**第三次**跨文件交叉验证（前两次见报告 083 的清单与报告 077 的 zone/title）。**

---

## 四、★★★★★ **`MatchRules` 的逐 gametype 校验（本报告最重要的逻辑）**

### 4.1 ★★★ 四个上限（第 394–404 行）

```cpp
constexpr std::uint32_t MaximumScoreLimit = 1'000'000;
constexpr std::uint32_t MaximumTimeLimitMinutes = 24 * 60;   // = 1,440
constexpr std::uint32_t MaximumRoundLimit = 1'000;
```

### 4.2 ★★★★★ 四个分支的完整规则（第 405–440 行）

| gametype（**归一化后**） | 要求 | 禁止 |
|---|---|---|
| **`cha`** | `playlistVersion` **且** `scoreLimit` **且** `timeLimitMinutes` | ★★ **`roundSwitch` / `roundLimit` / `winLimit` 全必须为 0** |
| **`sd`** | `playlistVersion` **且** `roundSwitch` **且** `roundLimit` **且** `winLimit`,且 **`roundSwitch <= roundLimit`**、**`winLimit <= roundLimit`** | ★★ **`scoreLimit` 必须为 0** |
| **`ffa`** | 同 `cha` | 同 `cha` |
| **`tdm`** | 同 `cha` | 同 `cha` |
| **其他** | ★★★ **`return true`（接受一切）** | — |

### ★★★★★ 三个精确的设计要点

```
① ★★★ **`cha` / `ffa` / `tdm` 三者规则完全相同** ⇒ 都是"有分数上限 + 有计时,无回合"
        ↓
② ★★★ **`sd` 完全相反** ⇒ "有回合 + 有胜场,无分数上限"
        ↓
③ ★★★★★ **其他 gametype 走"accept-anything tail"** ⇒ 不做任何校验
```

### 4.3 ★★★★★ 三条**注释里的实测故事**（逐字,极有价值）

#### 故事 1：`ffa` 的零分数陷阱（第 419–422 行）

```cpp
// Free-for-all books as ffa and runs as the gametype dm. It is scored and
// timed like cha but has no rounds; without this it would fall through to
// the accept-anything tail below and a zero score limit - a match that can
// never end - would look valid.
```

★★★ **⇒ 若不特判 `ffa` ⇒ 落到 accept-anything ⇒ **零分数上限**的比赛会被判"合法"**
**⇒ 而零分数上限 = **比赛永远无法结束**。**

#### 故事 2：`tdm` 的静默降级（第 429–433 行）

```cpp
// Team deathmatch books as tdm and runs as the gametype war, and it is
// scored and timed like cha. It used to fall through to the
// accept-anything tail below, so a booking whose playlist declared no
// scr_war_* rule resolved with both limits zero - silently a match with
// no clock and no score limit rather than a visible refusal.
```

★★★ **⇒ 历史缺陷：`tdm` 曾落到 accept-anything**
**⇒ 若 playlist 没声明 `scr_war_*` ⇒ 两个上限都是 **0** ⇒ **既无时钟也无分数上限**,且**静默**（不是显式拒绝）。**

#### 故事 3：归一化的必要性（第 389–392 行）

```cpp
// Callers on the backend side hold the token the client booked; callers on
// the game-server side hold the engine gametype. Normalise rather than
// pick one, because the failure of getting it wrong is silent - an
// unrecognised name falls through to the accept-anything tail below.
```

★★★ **⇒ 两侧持不同词汇：**
```
后端（backend）      ⇒ 持有客户端 booked 的 **token**（`ffa`/`tdm`/`kc`）
对局服（game-server）⇒ 持有 **engine gametype**（`dm`/`war`/`conf`）
        ↓
★★★ ⇒ 所以先 `bookingToken(rawGameType)` **归一化**
   ⇒ 否则"认不出的名字"会落到 accept-anything ⇒ **静默失败**
```

★★ **⇒ 这解释了为什么 `valid()` 里第一行就是 `const auto gameType = OlMod::CodolPlaylist::bookingToken(rawGameType);`**

---

## 五、★★★★★ **用户名编码（GBK,不是 ASCII）**

### 5.1 ★★★★★ `validUsername` 的完整逻辑（第 115–125 行，逐字）

```cpp
bool validUsername(const std::string &username)
{
    return !username.empty() &&
        username.size() <= OlMod::DedicatedSession::MaximumUsernameSize &&
        // ★ 2026-10-07 15:0x -- 放宽到「无控制符」：名字线编码 = GBK 字节
        //   （`Lifetime丷` = `... 81 52`），与 `IdentityConfig::validateDisplayName`
        //   同一口径（≤16 字节 / ≥0x20 / ≠0x7F）。原先的 0x7E 上限会把 GBK 名字拒掉。
        std::ranges::all_of(username, [](const unsigned char value) {
            return value >= 0x20 && value != 0x7F;
        });
}
```

★★★★★ **⇒ 三条精确规则：**
```
① **≤ 16 字节**（不是 16 字符）
② **每个字节 ≥ 0x20**
③ **每个字节 ≠ 0x7F**
        ↓
★★★ ⇒ 上限从 **0x7E** 放宽到 **"无控制符"**
   ⇒ 原因：**GBK 名字的第二字节可以 ≥ 0x7F**
   ⇒ 例：**`Lifetime丷`** 的 `丷` = **`... 81 52`**
        ↓
★★★★★ ⇒ **这解决了报告 050 / 081 的悬案！**
```

### 5.2 ★★★★★ 与 `force_display_name.py` 的对照

```
报告 050：`force_display_name.py` 尝试 5 条通道改显示名,全失败；
          且记录"ASCII-only（1–16 可打印）vs 中文名支持"的不一致
报告 081：`Identity.json` = `{"username": "Alwaysoffline"}`,字段名是 `username`
        ↓
★★★★★ 本报告（代码级权威）：
   **名字线编码 = GBK 字节**，**≤16 字节**，**≥0x20 且 ≠0x7F**
   ⇒ ★★★ **支持中文（GBK）**,但**字节数上限 16**
   ⇒ 即：**UTF-8 中文会被当成多字节,GBK 才是正确编码**
   ⇒ ★ 例：`Lifetime丷` 是 **GBK 字节**,`丷` 的 GBK 是 `81 52`
        ↓
★★★ ⇒ **"ASCII-only" 的推测被否定**：代码明确支持 GBK 中文
```

★★ **⇒ 且明确"与 `IdentityConfig::validateDisplayName` **同一口径**" ⇒ 两处规则一致。**

### 5.3 ★★★ `validItemId`（第 110–113 行）

```cpp
bool validItemId(const std::uint32_t itemId)
{
    return itemId <= (std::numeric_limits<std::uint16_t>::max)();
}
```

★★ **⇒ itemId **≤ 65535**（`u16` 上限）⇒ 尽管线格式里用 `u32` 存。**

★★ **⇒ 与报告 089 的 `MarketplaceSkus.json` 对照：**
```
`MarketplaceSkus` 的 itemId 范围：**100 … 60076**（从 grant 样例看）
        ↓
★ 而这里是 **≤ 65535**
        ↓
★★★ ⇒ **两者相容**（60076 > 65535？—— 需核对：`kis` 的 `uav` = **60076**）
        ↓
★★★ **⇒ 冲突！`60076 > 65535`**
```

★★ **⇒ 这是一个**待核对的矛盾**（记录,不擅自判定）：**
```
`validItemId` 要求 ≤ **65535**
但 `MarketplaceSkus` 里有 itemId = **60076**（`kis/uav`）等
        ↓
★ 可能解释：① `60076` 是 `items` 表的**行号**而非 `itemId`
              ② 或 `validItemId` 只用于**配装**（不含连杀奖励）
              ③ 或 `items` 表与配装用的是**两套编号**
        ↓
★★★ ⇒ **未实测,记录为待核对项**
```

### 5.4 ★★★★★ `EquipmentRequest` 的"catalog ID + 1"编码（第 36–45 行）

```cpp
// Source-owned transport of the named lethal/tactical profile fields.
// Raw item integers use **catalog ID + 1**, with **0/1 empty**.
// Double-ammo flags are booleans from the profile, not a guessed native ammo count.
struct EquipmentRequest
{
    std::array<std::uint32_t, 2> itemIds{}; // lethal, tactical
    std::uint8_t doubleAmmoMask{};          // bit 0 lethal, bit 1 tactical
};
```

★★★★★ **⇒ 一个精确的编码规则：**
```
配装里的 item 整数 = **catalog ID + 1**
**0 与 1 都表示"空"**
        ↓
★ 且 `doubleAmmoMask` 是**布尔位**（bit 0 lethal / bit 1 tactical）
   —— "**not a guessed native ammo count**"
```

★ **⇒ 这与报告 089 的 `MarketplaceSkus` 的 itemId 是**不同的编号空间**（配装用 `catalog ID + 1`）。**

### 5.5 ★★★ `valid(LoadoutRequest)` 的三条硬约束（第 306–354 行）

```cpp
if (request.characterIndex >= CharacterItemCount ||        // < 12
    request.classMask & ~((1u << LoadoutClassCount) - 1u) ||  // 只允许低 5 位
    !request.characterItemIds.front())                    // ★ 第 0 项必须非零
{
    return false;
}
...
return request.classMask != 0;   // ★ 至少一个 class
```

★★★ **⇒ 三条精确约束：**
```
① `characterIndex` **< 12**
② `classMask` **只有低 5 位可用**（`~((1<<5)-1)` = 高 27 位必须为 0）
③ ★★ `characterItemIds[0]` **必须非零**（不能全空）
④ ★ `classMask != 0`（至少启用一个配装类）
```

### 5.6 ★★★★★ `valid(ClientSessionCapture)` 的一个**实测教训**（第 365–385 行，逐字）

```cpp
// A CAPTURE WITH NO BOOKING IS STILL A CAPTURE, and the two halves are
// gathered from completely different places. The loadout comes out of the
// stored profile and is there whenever the client is logged in; the booking
// selection only exists while the client is HOLDING a lobby booking, which
// it is not at the menu and may drop again once a match starts.
//
// Requiring both meant a client sitting in the menu with five perfectly
// readable classes reported nothing at all -- measured as
//     client capture empty: NO_BOOKING_SELECTION characterIndex=4 classMask=31
// where classMask 31 is all five classes read successfully.
```

★★★★★ **⇒ 一条带**实测日志原文**的教训：**
```
问题：原实现要求 booking 与 loadout **都有效**
        ↓
★★★ 但二者来源完全不同：
  `loadout`  ⇒ 来自**存储的 profile**,**登录即有**
  `booking`  ⇒ 只在**持有大厅预订**时存在（菜单里没有,开赛后可能丢）
        ↓
★★★ 后果（逐字）："a client sitting in the menu with **five perfectly readable
   classes** reported **nothing at all**"
        ↓
★★★ 实测日志：`client capture empty: NO_BOOKING_SELECTION
              characterIndex=4 classMask=31`
   ⇒ ★ **`classMask=31` = 五个配装类全部成功读取**
        ↓
★★★★★ 修复：**完全空的 booking 表示"这个客户端没持有预订"**,不视为错误
```

★★ **⇒ 这与报告 073 的 `dmz.lua` "nil 三值约定"、报告 069 的 `zm.lua` fail-closed**同一类工程判断。**

---

## 六、★★★★ 其余 6 个 `shared\` 文件（未在本报告展开）

| 文件 | 字节 | 行 |
|---|---|---|
| `DedicatedControl.cpp` | **36,106** | **844** |
| `DedicatedControl.hpp` | 13,274 | 297 |
| `RuntimeLog.cpp` | 18,359 | 398 |
| `RuntimeLog.hpp` | 2,018 | 43 |
| `LocalnetServer.hpp` | 1,359 | 42 |
| `ProcessRole.hpp` | 1,178 | 45 |

★ **⇒ 下一份报告（094）覆盖 `DedicatedControl` + `RuntimeLog` + 两个小 `.hpp`。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **token 表只有 3 项** | **`ffa→dm`** / **`tdm→war`** / **`kc→conf`** |
| 2 | ★★★★★ **CODREF 三重证据** | ① **262 个 `mp_constbaselines_bl_pc_<map>_<gametype>.bin`**（`dm` 25 / `war` 23 / `conf` 24，**无 ffa/tdm/kc**）② **rotation 写 `tdm` 的 playlist 声明 `scr_war_*`**（例 playlist 30）③ **`C-2021-7-25[1-19-26]dm.demo` 的 `\g_gametype\dm`** = **playlist 23 的 ffa rotation entry [3]** |
| 3 | ★★★ 血统 | **stock IW names**（`dm.gsc`=FFA / `war.gsc`=TDM，CoD4/MW2/MW3） |
| 4 | ★★ 双向归一化 | `engineGameType` / `bookingToken`，**未列出者原样返回**,两个方向都是 total |
| 5 | ★★★ 解析器 5 关键字 | `version` / `playlist` / `rule` / `<map>,<gt>,<w>` / ★★ **其他 ⇒ `properties`** |
| 6 | ★★★★ **rotation 四条校验** | **恰好 2 个逗号** / `validName(map)` / `validName(gt)` / ★★ **`weight` 非零** |
| 7 | ★★★ 后果 | **`weight = 0` 的 rotation 行会被丢弃** |
| 8 | ★★★★★ **D1a 作者字段** | `combattraining`（裸旗标）/ `difficulty N` / `vsrule "6V6"` / `maxhumanplayersperteam N` **原被静默丢弃** |
| 9 | ★★★ 依据 | `推进-地图内官方bot-…-1900.md` §2①「全树 grep `combattraining`/`maxhumanplayersperteam` = **0 命中**」 |
| 10 | ★★ D1a 纪律 | **只收录,不参与任何既有判定**（`properties` 与 `rules` 两套不混） |
| 11 | ★★ `unquote` | 去掉一层双引号（`vsrule "6V6"`） |
| 12 | ★★★ 解析失败条件 | 无 `version` **或** playlist 为空 |
| 13 | ★★★★★ **`PayloadMagic`** | **`0x53444C4F` = `OLDS`**（小端 `4F 4C 44 53`） |
| 14 | ★★★ 三种 payload | kind **1=Loadout** / **2=SessionStart** / **3=ClientSessionCapture** |
| 15 | ★★ 通用头 8 字节 | `magic(4) + version(2) + kind(2)`,**全小端** |
| 16 | ★★★★★ **版本 v5–v8** | **v6 加 perks / v7 加 equipment / v8 加 rewards**；只收 v5 会"**rejects every live booking before world initialization**" |
| 17 | ★★★★★ **`SessionStart` 布局** | 头 + memberCount + bookingCommandSize + **bookingBody** + **matchRulesBody(10 个 u32)** + bookingCommand + **每个 member**(u64 userId + u16 nameSize + u16 reserved + loadoutBody + name) |
| 18 | ★★★★★ **`LoadoutRequest` v8 = 1,648 字节** | 4+1+1+2+**48**(12×u32)+**1,580**(5×316)+**12**(3×u32) |
| 19 | ★★★★ **12 个结构常量** | `SchemaVersion 8` / `RewardSlotCount 3` / `CharacterItemCount 12` / `LoadoutClassCount 5` / `WeaponsPerClass 2` / `AttachmentCount 6` / `PerkSlotCount 6` / `MaximumUsernameSize 16` / `MaximumBookingCommandSize 1024` / `MaximumMapNameSize 64` / `MaximumGameTypeSize 32` / ★★★ **`MaximumSessionMembers 18`** |
| 20 | ★★★★★ **`MaximumSessionMembers = 18`** | ✓ 与报告 071 的 **`MaximumGameClients (18)`** 吻合（**第三次跨文件交叉验证**） |
| 21 | ★★★★ **`MatchRules` 四上限** | `MaximumScoreLimit` **1,000,000** / `MaximumTimeLimitMinutes` **1,440**（24h）/ `MaximumRoundLimit` **1,000** |
| 22 | ★★★★★ **逐 gametype 校验** | **`cha`/`ffa`/`tdm`** ⇒ 有分数+计时,**无回合**；**`sd`** ⇒ 有回合+胜场,**无分数**,且 `roundSwitch<=roundLimit`、`winLimit<=roundLimit`；**其他 ⇒ `return true`** |
| 23 | ★★★★★ **三条实测故事** | ① `ffa` 若不特判 ⇒ **零分数上限被当合法 ⇒ 比赛永不结束** ② `tdm` 曾静默降级为"无时钟无分数" ③ 两侧词汇不同 ⇒ 不归一化就**静默失败** |
| 24 | ★★★★★ **用户名 = GBK 字节** | **≤16 字节** / **≥0x20** / **≠0x7F**；上限从 **0x7E** 放宽；例 **`Lifetime丷`** 的 `丷` = `... 81 52` |
| 25 | ★★★★★ **否定"ASCII-only"** | 代码明确支持 **GBK 中文**；与 `IdentityConfig::validateDisplayName` **同一口径** |
| 26 | ★★★ `validItemId` | **≤ 65,535**（`u16` 上限，尽管线上用 `u32`） |
| 27 | ★★★★ **待核对的矛盾** | `validItemId` 限 **65,535**,而 `MarketplaceSkus` 有 itemId **60,076**（`kis/uav`）⇒ 三种可能解释,**未实测** |
| 28 | ★★★ `EquipmentRequest` 编码 | **`catalog ID + 1`**,**0/1 都是空**；`doubleAmmoMask` 是**布尔位**（"not a guessed native ammo count"） |
| 29 | ★★★ `valid(LoadoutRequest)` | `characterIndex < 12` / `classMask` 只用低 5 位 / `characterItemIds[0]` 非零 / `classMask != 0` |
| 30 | ★★★★★ **`ClientSessionCapture` 的实测教训** | 原要求 booking+loadout 都有效 ⇒ 菜单里的客户端"**five perfectly readable classes** reported **nothing at all**"；日志 **`NO_BOOKING_SELECTION characterIndex=4 classMask=31`**（31 = 五类全读到） |

---

## 八、结论

### 1. ★★★★★ **`CodolPlaylist` 的 token 表被代码级确认为**只有 3 项**,且有**三重独立证据**

```
**`ffa→dm`** / **`tdm→war`** / **`kc→conf`**
        ↓
★★★ 证据 1：**262 个 constbaselines bin**（dm 25 / war 23 / conf 24,无 ffa/tdm/kc）
★★★ 证据 2：**rotation 写 `tdm` ⇒ 声明 `scr_war_*`**
★★★ 证据 3：**`C-2021-7-25[1-19-26]dm.demo` 的 `\g_gametype\dm`** = playlist 23 的 ffa rotation entry [3]
        ↓
★★★★★ ⇒ **报告 079 从 playlist 侧推断的三条映射,现在有了代码级权威** ✓
```

### 2. ★★★★★ **`DedicatedSession` 的线上格式被完整还原**（`OLDS` magic / 3 kind / v5–v8 / 1,648 字节配装）

### 3. ★★★★★ **`MatchRules` 的逐 gametype 校验揭示三条实测故事**

★ **⇒ 最有价值的是 `ffa` 那条：**不特判就会让**零分数上限**的比赛被判合法 ⇒ **永远无法结束**。**

### 4. ★★★★★ **用户名是 GBK 字节（≤16 字节），不是 ASCII** —— 解决了"ASCII-only vs 中文名"的悬案

### 5. ★★★★ **`MaximumSessionMembers = 18` 与 `MaximumGameClients (18)` 吻合**（第三次跨文件验证）

### 6. ★★★ **`weight = 0` 的 rotation 行会被解析器丢弃**（解释了报告 079 的观察）

### 7. ★★★ **一处待核对的矛盾**（`validItemId ≤ 65535` vs `MarketplaceSkus` 的 60076）

---

## 九、下一步

- `shared\` 剩余 6 文件（`DedicatedControl.cpp` 844 行 / `RuntimeLog.cpp` 398 行 / 两个小 `.hpp`）
- 然后 `game_server\qcommon\`（8 文件 / 103 KB）—— `net_chan_mp` / `net_dtls_cod`
