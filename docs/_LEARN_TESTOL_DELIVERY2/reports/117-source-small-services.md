# 学习报告 117（重开）— `StatsService.hpp` + 三个小服务全文

**学习范围**：`StatsService.hpp`（116 行）+ `ContentUnlock2Service`（22 + 79）+ `TencentService`（19 + 94）+ `TitleUtilitiesService`（16 + 56）
**性质**：全实测（**7 文件逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**`LeaderBoardRow<10>` 的 6 段字段表** ②**`4/4` 与 `4/13` 的请求格式** ③**`ContentUnlock2` 的 `max(count, 32)`** ④**`Tencent` 的 7 个任务与 AAS 记录** ⑤**`TitleUtilities2` 的 base64 用户名**

---

## 一、★★★★★ **`LeaderBoardRow<10>` 的 6 段字段表**

### 1.1 ★★★★★ 完整注释（`StatsService.hpp`，逐字）

```cpp
// Demonware service **4 (STATS)** -- the ranked leaderboard.
//
// MEASURED on this client (2026-10-06/07 backend logs): every login sends
//   **4/4  readStatsByRank  [u32 leaderboardId][u64 startRank][u32 numRows]**  e.g. (**932,1,101**)
// and the lobby screens probe
//   **4/13 <self stats>     [u32 leaderboardId][u32 1][u64 CODOID][u32 0]**
// (both were answered with the unhandled empty ack until now).
//
// The reply record is Demonware's **`LeaderBoardRow<10>`**, re-measured
// field-by-field from the sibling build in the Antia tree
// (`dw_types.md` 6, `career/stats_service.py`, **vftable 0xC81F0C**):
//   **tag 10 u64 entityId** | **tag 9 i64 score** | **tag 10 u64 rank** | **tag 16 string name** |
//   **tag 8 u32 numColumns=10** | **10 x tag 7 i32 columns**
```

### ★★★★★ 完整的 6 段字段

| # | tag | 类型 | 字段 |
|---|---|---|---|
| **1** | **`10`** | **u64** | ★ **`entityId`** |
| **2** | **`9`** | **i64** | ★ **`score`** |
| **3** | **`10`** | **u64** | ★ **`rank`** |
| **4** | **`16`** | **string** | ★ **`name`** |
| **5** | **`8`** | **u32** | ★★ **`numColumns = 10`** |
| **6** | **`7`** | **i32 × 10** | ★★ **10 个列** |

★★★ **⇒ 6 段,最后一段是 10 个 i32。**
**⇒ 与报告 105 的类型码表**完全一致**（`7=I32` / `8=U32` / `9=I64` / `10=U64` / `16=String`）✓**

### ★★★★★ 两个请求的精确格式

| 请求 | 格式 | 实例 |
|---|---|---|
| **`4/4` `readStatsByRank`** | ★ `[u32 leaderboardId][u64 startRank][u32 numRows]` | **`(932, 1, 101)`** |
| **`4/13` `<self stats>`** | ★ `[u32 leaderboardId][u32 1][u64 CODOID][u32 0]` | — |

★★★ **⇒ 两个请求的字段数不同（3 vs 4）,且 `4/13` 多一个 `u64 CODOID`。**

★ **⇒ `4/4` 的实例 **`(932, 1, 101)`**：**
```
`leaderboardId = **932**` ⇒ ★ 与报告 078 的 `[tournament12]` 的 `leaderboard_id = **932**` 一致?
`startRank = **1**`
`numRows = **101**`
```

★★ **⇒ 若 `932` 确为 `[tournament12]` 的 id,则说明**排位赛第 12 季的榜单**在跑。**
**⇒ 但报告 078 的 `tournament12` 的 `leaderboard_id` 是 **932** ⇒ **吻合** ✓（记录为**强线索**,未完全确证）**

### ★★★ 出处（逐字）

```
(`dw_types.md` 6, `career/stats_service.py`, **vftable 0xC81F0C**)
```

★★ **⇒ 三个出处 + 一个 vftable 地址。**

### ★★★★★ 名册的数据源（逐字）

```cpp
// Ledger rows are authored as per-player saves: **one directory per fake player**
// under `<assetRoot>/<titleId>/<UID-HEX>/` carrying **`ranked.json`**
// (`{"name": ..., "xp": ...}`); this service scans them and **ranks by XP**.
```

★★★ **⇒ 数据源：**
```
`<assetRoot>/<titleId>/<UID-HEX>/`**`ranked.json`**
   ⇒ `{"name": ..., "xp": ...}`
        ↓
★★★ ⇒ 服务扫描所有目录并按 **XP 排序**
```

★ **⇒ 与报告 106/115 的 `Identity.json` / `Inventory.json` **同目录结构** ✓**

### ★★★ `RankedPlayer` 的 5 个字段（逐字）

```cpp
struct RankedPlayer
{
    std::uint64_t userId{};
    std::string name;
    std::int64_t xp{};
    std::string clan;   // ranked.json 的原生 clan（top100 原本战队）
    std::uint32_t clanId{};   // ★ 第八轮：clans.json 里该战队的 id（lb1000 要发）
};
```

★★★ **⇒ 5 个字段,含 **`clan`**（原生战队名）与 **`clanId`**（来自 `clans.json`）。**
**⇒ 注释提到 **"lb1000 要发"** ⇒ 说明有个 `leaderboardId = 1000` 的榜单需要 clanId。**

### ★★★★★ `buildBoard` 的合并榜（逐字）

```cpp
// ★ 2026-10-20：4/4（全区）与 4/13（本人/好友）用**同一张合并榜**：
//   名册（剔除 uid == 我）+ 我（selfXp）⇒ 按分数降序。
//   名次 = 在合并榜里的位置（不再硬编码"我第 1、名册从第 2 起"）。
[[nodiscard]] std::vector<RankedPlayer> buildBoard() const;
```

★★★ **⇒ 合并榜 = **名册（剔除自己）+ 自己**,按分数降序,名次 = 实际位置。**

★ **⇒ 且明确"**不再硬编码'我第 1、名册从第 2 起'**" ⇒ 修正了旧的硬编码。**

### ★★★ `buildRow` 的签名（逐字）

```cpp
[[nodiscard]] std::vector<std::uint8_t> buildRow(
    std::uint64_t entityId, std::uint64_t rank, const std::string &name,
    std::int64_t xp, std::uint32_t leaderboardId,
    const std::array<std::int32_t, 10> *columnsOverride = nullptr,
    const std::string &clanName = std::string(),
    std::uint32_t clanId = 0) const;
```

★★★ **⇒ 8 个参数,含 **`columnsOverride`**（10 个 i32 的覆盖）与 **`clanName` / `clanId`**。**

---

## 二、★★★★★ **`ContentUnlock2Service`（服务 `0x1C`）**

### 2.1 ★★★ 4 个任务（第 10–27 行）

```cpp
registry.registerTask(**0x1C**, 1, "ContentUnlock2::task1");
registry.registerTask(**0x1C**, 2, "ContentUnlock2::task2");
registry.registerTask(**0x1C**, 3, "ContentUnlock2::task3");
registry.registerTask(**0x1C**, 4, "ContentUnlock2::task4");
```

### ★★★★★ 4 个任务的请求/响应

| task | 请求 | 响应 |
|---|---|---|
| **1** | ★ `readU32Array(contentIds)` | 空 |
| **2** | ★★ `u64 userId` + `readU32Array(contentIds)` | 空 |
| **3** | `u64 userId` | 空 |
| **4** | ★ `readU32Array(contentIds)` | ★★★ **每个 contentId 一个对象** |

★★★ **⇒ task 1/2 是**上报解锁**,task 4 是**查询计数**。**

### ★★★★★ `task4` 的 `max(count, 32)`（第 65–75 行）

```cpp
for (const auto contentId : contentIds)
{
    const auto entry = unlockCounts_.find(contentId);
    const auto count = entry == unlockCounts_.end() ? 0 : entry->second;
    ByteBuffer object;
    object.writeU32(contentId);
    object.writeU32((**std::max**)(count, std::uint32_t{ **32** }));   // ★★★ 至少 32
    response.objects.push_back(object.data());
}
```

★★★★★ **⇒ 一个精确的"地板值"：**
```
`count = max(实际解锁次数, **32**)`
        ↓
★★★ ⇒ 即：**每个内容 ID 至少报 32 次解锁**
   ⇒ 可能为了让客户端认为"已充分解锁"
```

★★ **⇒ 且 `unlockCounts_` 是 **`unordered_map<uint32, uint32>`** ⇒ 内存态（不持久化）。**

### ★★★ `incrementUnlockCounts`（第 77–83 行）

```cpp
std::scoped_lock lock(mutex_);
for (const auto contentId : contentIds)
    ++unlockCounts_[contentId];
```

★★ **⇒ 每次上报 ⇒ 计数 +1。**

★ **⇒ 所以 `max(count, 32)` 意味着：**前 31 次上报都不改变返回值（恒 32）**。**

### ★★★ 使用 `readU32Array` 的对比

★★ **⇒ 这里用了 **`readU32Array`**（tag `0x6C` 的 bd array）。**
**⇒ 而报告 115 的 `getSkusPaginated` 明确说**不能用 `readU32Array`**（客户端写裸 count）。**
**⇒ 即：**两个服务的数组编码方式不同** ⇒ `ContentUnlock2` 用真 bd array,`Marketplace` 用裸 count。**

---

## 三、★★★★★ **`TencentService`（服务 `0x47`）**

### 3.1 ★★★ 7 个任务（第 12–38 行）

```cpp
registry.registerTask(**0x47**, **1**,  "Tencent::verifyString");
registry.registerTask(**0x47**, **2**,  "Tencent::task2");
for (task : { **3**, **7**, **8** }) registry.registerTask(0x47, task, "Tencent::acceptTelemetry");
registry.registerTask(**0x47**, **5**,  "Tencent::getAASRecord");
registry.registerTask(**0x47**, **9**,  "Tencent::task9");            // ★ 匿名 lambda
registry.registerTask(**0x47**, **11**, "Tencent::claimClientDecidedRewards");
```

### ★★★★★ 7 个任务的完整表

| task | 名称 | 行为 |
|---|---|---|
| **1** | `verifyString` | ★ 读 string ⇒ 回 **`u32 0`** |
| **2** | `task2` | ★ 读 string ⇒ 回 **`bool false` + 同一 string** |
| **3/7/8** | `acceptTelemetry` | 读 string ⇒ **空** |
| **5** | `getAASRecord` | ★★ 回 **5 个字段**（见下） |
| **9** | `task9` | ★★★ **直接空**（无 lambda 捕获） |
| **11** | `claimClientDecidedRewards` | 读 `u32 count` + N 个 string ⇒ **空** |

### ★★★★★ `getAASRecord` 的 5 个字段（第 66–75 行）

```cpp
ByteBuffer object;
object.writeU8(**1**);
object.writeU64(session_.snapshot().userId);
object.writeU8(**0x58**);
object.writeU32(**60**);
object.writeU32(**30**);
```

| # | 类型 | 值 |
|---|---|---|
| **1** | **u8** | ★ **`1`** |
| **2** | **u64** | `userId` |
| **3** | **u8** | ★★ **`0x58`** |
| **4** | **u32** | ★ **`60`** |
| **5** | **u32** | ★ **`30`** |

★★★ **⇒ `0x58 = 88`；`60` 与 `30` 可能是**时间限制**（60 秒 / 30 秒）。**
**⇒ "AAS" = **Anti-Addiction System**（腾讯防沉迷）⇒ `60`/`30` 可能是**游戏时长配额**。**

★ **⇒ 这与报告 077 的 `[server_cmd] aas_challenge_fullreward=1` **同一体系** ✓**

### ★★★ `verifyString` 的回 `u32 0`（第 47–53 行）

```cpp
ByteBuffer object;
object.writeU32(**0**);
return ServiceResponse{ .task = request.task, .objects = { object.data() } };
```

★★ **⇒ 恒返回 **0**（可能是"验证失败"或"无需验证"）。**

### ★★★ `task2` 的回显（第 57–64 行）

```cpp
ByteBuffer object;
object.writeBool(**false**);
object.writeString(username);
```

★★ **⇒ `bool false` + **原样回显用户名**。**

### ★★★ task 9 的匿名 lambda（第 30–33 行）

```cpp
registry.registerTask(0x47, 9, "Tencent::task9", [](const auto &request)
{
    return ServiceResponse{ .task = request.task };
});
```

★ **⇒ **不捕获 `this`**（`[]` 而非 `[this]`）⇒ 因为不需要成员。**

---

## 四、★★★★★ **`TitleUtilitiesService`（服务 `0x0C`）**

### 4.1 ★★★ 2 个任务（第 30–38 行）

```cpp
registry.registerTask(**0x0C**, **6**, "TitleUtilities2::getServerTime");
registry.registerTask(**0x0C**, **9**, "TitleUtilities2::task9");
```

### ★★★ `getServerTime`（第 40–44 行）

```cpp
ByteBuffer object;
object.writeU32(static_cast<std::uint32_t>(std::time(nullptr)));
return ServiceResponse{ .task = request.task, .objects = { object.data() } };
```

★★ **⇒ 回**当前 Unix 时间戳**（`u32`）。**

### ★★★★★ `task9` 的 base64 用户名（第 46–56 行）

```cpp
ByteBuffer input(request.payload);
std::uint64_t userId{};
if (!input.readU64(userId) || !input.valid())
    return ServiceResponse{ .error = 1000, .task = request.task };

ByteBuffer object;
object.writeU64(userId);
object.writeString(**base64**(session_.snapshot().username));   // ★★★ base64
return ServiceResponse{ .task = request.task, .objects = { object.data() } };
```

★★★★★ **⇒ `task9` 返回 `u64 userId` + **base64(用户名)**。**
**⇒ 而 `base64` 用 `EVP_EncodeBlock`（第 14–26 行）。**

★★ **⇒ 与报告 103 的 `Auth3Protocol` 的 `extra_data.username` 是 **base64(明文用户名)** **完全一致** ✓**
**⇒ 即：**用户名在两处都以 base64 形式传递**。**

★ **⇒ 但注释说"名字全链路已切 UTF-8"（报告 112/113）⇒ **base64 只是传输编码,不是字符集**。**

---

## 五、★★★★★ **四个服务的注册表总览**

### 5.1 ★★★★★ 完整的服务 ID 对照

| 服务 | ID | 文件 | 任务数 |
|---|---|---|---|
| **Stats** | **`0x04`** | `StatsService` | 2（`4/4` / `4/13`） |
| **TitleUtilities2** | **`0x0C`** | `TitleUtilitiesService` | **2**（`6` / `9`） |
| **ContentUnlock2** | **`0x1C`** | `ContentUnlock2Service` | **4**（`1`–`4`） |
| **Tencent** | **`0x47`** | `TencentService` | **7**（`1`/`2`/`3`/`5`/`7`/`8`/`9`/`11`） |

★★★ **⇒ 与报告 109 的 `RecoveredCatalog` **完全吻合** ✓：**
```
`0x0C`(lobby) = **TitleUtilities2** ✓
`0x1C`(lobby) = **ContentUnlock2** ✓
`0x47` = **Tencent** ✓
`0x04` = **Stats**（报告 109 的 27 个里**没有列出 `0x04`**）
```

★★ **⇒ 报告 109 的目录**缺 `0x04`（Stats）** ⇒ 因为它不在那 27 个 xref 里。**
**⇒ 但 `StatsService.hpp` 明确说 "Demonware service **4 (STATS)**" ⇒ **服务 ID 确认是 4**。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **服务 4 = STATS** | "Demonware service **4 (STATS)** -- the ranked leaderboard" |
| 2 | ★★★★ **`4/4` 请求** | `[u32 leaderboardId][u64 startRank][u32 numRows]`,实例 **`(932, 1, 101)`** |
| 3 | ★★★ **`4/13` 请求** | `[u32 leaderboardId][u32 1][u64 CODOID][u32 0]` |
| 4 | ★★★★★ **`LeaderBoardRow<10>` 六段** | **`tag 10 u64 entityId`** / **`tag 9 i64 score`** / **`tag 10 u64 rank`** / **`tag 16 string name`** / **`tag 8 u32 numColumns=10`** / **`10 × tag 7 i32 columns`** |
| 5 | ★★ 出处 | `dw_types.md` 6 / `career/stats_service.py` / **vftable `0xC81F0C`** |
| 6 | ★★★ `932` 的线索 | 与报告 078 的 `[tournament12] leaderboard_id = **932**` **吻合**（未完全确证） |
| 7 | ★★★★ **名册数据源** | `<assetRoot>/<titleId>/<UID-HEX>/**ranked.json**` ⇒ `{"name":..., "xp":...}` ⇒ **按 XP 排序** |
| 8 | ★★★ `RankedPlayer` 5 字段 | `userId` / `name` / `xp` / **`clan`** / **`clanId`**（来自 `clans.json`，**"lb1000 要发"**） |
| 9 | ★★★★ **`buildBoard` 合并榜** | **名册（剔除自己）+ 自己**,按分数降序 ⇒ **"不再硬编码'我第 1、名册从第 2 起'"** |
| 10 | ★★ `buildRow` 8 参数 | 含 **`columnsOverride`**（10 × i32）/ `clanName` / `clanId` |
| 11 | ★★★ **`ContentUnlock2` = 服务 `0x1C`** | 4 任务：1/2 上报、3 只读 uid、**4 查询** |
| 12 | ★★★★★ **`max(count, 32)`** | `task4` 每个 contentId 至少报 **32** 次解锁 ⇒ 前 31 次上报不改变返回值 |
| 13 | ★★★ **用真 `readU32Array`** | 与报告 115 的 `getSkusPaginated`（**不能用**）**相反** ⇒ 两服务数组编码不同 |
| 14 | ★★★★★ **`Tencent` = 服务 `0x47`** | **7 个任务**：`1`(verifyString) / `2`(回显) / **`3`/`7`/`8`**(telemetry) / **`5`**(AAS) / **`9`**(空) / **`11`**(claim) |
| 15 | ★★★★★ **`getAASRecord` 5 字段** | `u8 1` / `u64 userId` / **`u8 0x58`** / **`u32 60`** / **`u32 30`** ⇒ **AAS = 防沉迷**（与 `[server_cmd] aas_challenge_fullreward` 同体系） |
| 16 | ★★ `verifyString` | 恒回 **`u32 0`** |
| 17 | ★★ `task2` | 回 **`bool false` + 原样回显用户名** |
| 18 | ★★ task 9 | **不捕获 `this`**（`[]` lambda） |
| 19 | ★★★ **`TitleUtilities2` = 服务 `0x0C`** | **2 个任务**：`6`(serverTime) / `9`(userId + **base64(用户名)**) |
| 20 | ★★★★★ **base64 用户名** | `task9` 回 `u64 userId` + **`base64(username)`** ⇒ ✓ 与报告 103 的 `extra_data.username` **一致** |
| 21 | ★★★ 服务 ID 对照 | `0x04`=Stats / `0x0C`=TitleUtilities2 / `0x1C`=ContentUnlock2 / `0x47`=Tencent ⇒ **与报告 109 的目录吻合**（除 `0x04` 未列） |

---

## 七、结论

### 1. ★★★★★ **`LeaderBoardRow<10>` 的 6 段字段被完整还原**

```
**`tag 10 u64 entityId`** → **`tag 9 i64 score`** → **`tag 10 u64 rank`** →
**`tag 16 string name`** → **`tag 8 u32 numColumns=10`** → **10 × tag 7 i32**
```

### 2. ★★★★★ **两个请求的格式不同**（`4/4` 3 字段 / `4/13` 4 字段）

### 3. ★★★★★ **`ContentUnlock2` 的 `max(count, 32)`** 是一个精确的地板值

### 4. ★★★★★ **`Tencent` 的 `getAASRecord` 揭示防沉迷机制**（`0x58` / `60` / `30`）

### 5. ★★★★★ **`TitleUtilities2` 的 base64 用户名与报告 103 一致**

### 6. ★★★★ **两个服务的数组编码方式相反**（`ContentUnlock2` 用真 bd array,`Marketplace` 用裸 count）

### 7. ★★★ **服务 ID 与报告 109 的目录吻合**（`0x04` 是新增确认）

---

## 八、下一步

- `StatsService.cpp`（875 行）
- `Profiles2Service`（630 行）/ `ClanService`（623 行）
- `Storage2Service`（450 行）/ `Friends2Service`（325 行）
- `SharedRoom*`（4 文件）/ `Servers.cpp`（624 行）
