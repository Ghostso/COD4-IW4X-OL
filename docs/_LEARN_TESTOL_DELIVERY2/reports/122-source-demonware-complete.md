# 学习报告 122（重开）— `Demonware` 收官：三个头文件 + 模块总账

**学习范围**：`ClanService.hpp`（72 行）+ `MarketplaceService.hpp`（87 行）+ `Profiles2Service.hpp`（39 行）
**性质**：全实测（**三文件逐行读完**）
**★★★★★ 本报告收录 `backend\Demonware` **52 文件全部完成**的总账，以及两个新发现**

---

## 一、★★★★★ **`ClanService.hpp` 的规格来源（首次完整列出）**

### 1.1 ★★★★★ 完整注释（第 15–22 行，逐字）

```cpp
// Clan service (DemonWare svc **0x03**) -- 本地整合 v1。
//
// 规格来源（**全部实测，不是猜**）：
//   **他方 `logs/clan_protocol.md` §3**（对象线格式）/ **§4**（task 表）
//   **他方 `tools/server/clans.py`**（行为）
//   **他方 `logs/soc_protocol.md` §4**（typed 标签：**0x01 bool / 0x03 u8 / 0x06 u16 /
//                                0x07 i32 / 0x08 u32 / 0x09 i64 / 0x0a u64 /
//                                0x10 string(NUL) / 0x13 blob(u32 len+bytes)**）
```

### ★★★★★ 四个精确出处

| # | 出处 | 内容 |
|---|---|---|
| **1** | ★ **`logs/clan_protocol.md` §3** | **对象线格式** |
| **2** | ★ **`logs/clan_protocol.md` §4** | **task 表** |
| **3** | ★ **`tools/server/clans.py`** | **行为** |
| **4** | ★★ **`logs/soc_protocol.md` §4** | **typed 标签表（9 个）** |

★★★ **⇒ 第 4 条给出了完整的 9 个 typed 标签（与报告 105/120 一致 ✓）：**
```
**`0x01` bool / `0x03` u8 / `0x06` u16 / `0x07` i32 / `0x08` u32 /
`0x09` i64 / `0x0a` u64 / `0x10` string(NUL) / `0x13` blob(u32 len+bytes)**
```

★ **⇒ 且明确"**全部实测，不是猜**"。**

### ★★★ v1 的范围声明（第 21–22 行，逐字）

```cpp
// v1 只做"**能建队、能看到自己的队、能看成员、能搜索、能退队**"这条闭环；
// 其余 task（升降职/邀请/申请/聊天）先回空 ack，避免客户端 pending op 卡死。
```

★★ **⇒ 五个闭环 + 四类未实现（升降职 / 邀请 / 申请 / 聊天）。**

### ★★★★★ `Clan` 的 15 个字段（逐字）

```cpp
struct Clan
{
    std::uint64_t teamId{};
    std::string name;
    std::string description;
    std::string announcement;
    std::uint64_t ownerId{};
    std::uint32_t profileVersion{ **1** };
    std::uint32_t autoJoinLevel{ **1** };
    std::int32_t  recruitState{ **0** };
    std::uint32_t createTimestamp{};
    std::uint32_t activeTimestamp{};
    std::uint32_t ctp{};
    std::uint32_t ctpEarnedToday{};
    std::uint32_t level{ **1** };
    std::uint32_t teamTags{};
    std::vector<Member> members;
};
```

★★★ **⇒ 15 个字段,与报告 120 的 `teamInfos` 12 字段**完全对应**（12 个 + `members` + `ownerId` + `name`）。**

### ★★★ `Member` 的 4 个字段（逐字）

```cpp
struct Member
{
    std::uint64_t userId{};
    std::uint8_t role{ **2** };   // **2 = owner, 1 = officer, 0 = member**
    bool online{ **true** };
    std::string name;         // 来自 `Ayria\Assets\Alwaysoffline\<标题>\<uid>\ranked.json`
};
```

★★★ **⇒ 三个 role 值：**2 = owner / 1 = officer / 0 = member**。**

★ **⇒ 且 `name` 的**出处明确**：`ranked.json`（报告 120 已记录构造函数读它但 `members()` 不用）。**

### ★★★ 两个默认值

```cpp
std::uint64_t nextTeamId_{ **1** };       // ★ teamId 从 1 开始
std::map<std::uint64_t, Clan> clans_;     // teamId -> clan
```

---

## 二、★★★★★ **`MarketplaceService.hpp` 的 `SecondaryCurrencyId = 2`**

### 2.1 ★★★★★ 完整注释（逐字）

```cpp
/// The currency id the client's **second wallet getter (`sub_6AF970`)** hunts for. It
/// returns **0** for every id it does not find, so **this constant is what decides whether
/// the second balance readout has a number in it at all**.
static constexpr std::uint8_t **SecondaryCurrencyId = 2**;
```

★★★★★ **⇒ 与报告 114 的完整吻合：**
```
报告 114（`MarketplaceService.cpp`）：
  `v2 = &byte_BA0B2C8; while (*v2 != **2**) { ... }`
  ⇒ "answering this with the id-1 record leaves the **id-2 readout at zero**"
        ↓
★★★ 本报告：`SecondaryCurrencyId = **2**` ✓
   ⇒ **就是那个被 `sub_6AF970` 搜索的 id**
```

### ★★★★★ `InventoryItem` 的**默认值就是"永久"**（逐字）

```cpp
struct InventoryItem
{
    std::uint32_t id{};
    std::uint32_t quantity{ **1** };
    std::uint32_t expireDateTime{ **(std::numeric_limits<std::uint32_t>::max)()** };
    std::int64_t  expiryDuration{ **(std::numeric_limits<std::int64_t>::max)()** };
    std::uint32_t modifiedTime{ **(std::numeric_limits<std::uint32_t>::max)()** };
    std::uint8_t  customSourceType{};
};
```

★★★★★ **⇒ 三个字段的默认值就是"永久"：**
```
`expireDateTime` = **`UINT32_MAX`**
`expiryDuration` = **`INT64_MAX`**
`modifiedTime`   = **`UINT32_MAX`**
        ↓
★★★ ⇒ 与报告 115 的 `PermanentExpiration` / `PermanentDuration` **完全一致** ✓
```

★ **⇒ 且**结构体默认值直接写成永久** ⇒ 新物品默认永久（更简洁）。**

### ★★★ 四个内部结构（逐字）

```cpp
struct Wallet       { std::uint8_t type{}; std::uint32_t amount{}; };
struct ItemGrant    { InventoryItem item; std::uint32_t durationSeconds{}; };
struct SkuGrant     { std::uint32_t sku{}; std::vector<ItemGrant> items; };
```

★★ **⇒ 三层嵌套：`SkuGrant` → `ItemGrant` → `InventoryItem`。**

### ★★★ 三个缓存字段（逐字）

```cpp
mutable std::filesystem::path skuGrantsCachePath_;
mutable std::filesystem::file_time_type skuGrantsCacheWriteTime_{};
mutable std::uintmax_t skuGrantsCacheSize_{};
mutable std::shared_ptr<const std::vector<SkuGrant>> skuGrantsCache_;
```

★★★ **⇒ 与报告 115 的"三重缓存键"**完全对应** ✓**
**⇒ 且用 `shared_ptr<const vector>` ⇒ **不可变共享**（线程安全）。**

### ★★★ 两个 mutex

```cpp
mutable std::mutex inventoryMutex_;
mutable std::mutex skuGrantsMutex_;
```

★ **⇒ 两个独立锁（库存与 SKU 缓存分开）。**

---

## 三、★★★★ **`Profiles2Service.hpp` 的 8 个任务声明**

### 3.1 ★★★ 完整清单（逐字）

```cpp
getPublicInfos / getPrivateInfo / getPrivateInfoByUserId
setPublicInfo / setPublicInfoByUserId
setPrivateInfo / setPrivateInfoByUserId
deleteProfile
```

★★ **⇒ 与报告 119 的 8 个任务**完全一致** ✓**

### ★★★ 三个文件操作辅助

```cpp
profilePath(userId, filename)          // 路径
loadProfile(userId, filename)          // 读
saveProfile(userId, filename, profile) // 写（原子）
stripOptionalUserId(payload)           // ★ static：剥掉可选的 userId 前导
```

★ **⇒ `stripOptionalUserId` 是 **`static`**（不依赖实例）。**

---

## 四、★★★★★ **`backend\Demonware` 52 文件全部完成 —— 收官账**

### 4.1 ★★★ 完整的 52 文件清单（按行数排序）

| # | 文件 | 字节 | 行 | 报告 |
|---|---|---|---|---|
| **1** | `MatchmakingService.cpp` | 58,994 | **1,101** | **110** |
| **2** | `MarketplaceService.cpp` | 55,404 | **1,099** | **114–115** |
| **3** | `StatsService.cpp` | 44,421 | **875** | **118** |
| **4** | `CodolClientPatches.cpp` | 43,329 | **882** | **107** |
| **5** | `LobbyProtocol.cpp` | 41,030 | **807** | **116** |
| **6** | `Unknown0BService.cpp` | 39,926 | **669** | **113** |
| **7** | `Profiles2Service.cpp` | 32,616 | **630** | **119** |
| **8** | `ClanService.cpp` | 24,704 | **623** | **120** |
| **9** | `Storage2Service.cpp` | 19,411 | **450** | **121** |
| **10** | `Friends2Service.cpp` | 17,532 | **325** | **121** |
| **11** | `Auth3Protocol.cpp` | 12,998 | **303** | **103** |
| **12** | `Auth3TlsTransport.cpp` | 12,771 | **311** | **108** |
| **13** | `InstantMessageService.cpp` | 12,905 | **242** | **112** |
| **14** | `LanDiscovery.cpp` | 11,351 | **295** | **111** |
| **15** | `Auth3ClientPatches.cpp` | 10,785 | **241** | **104** |
| **16** | `IdentityConfig.hpp` | 8,954 | **108** | **106** |
| **17** | `ByteBuffer.cpp` | 8,755 | **258** | **105** |
| **18** | `Crypto.cpp` | 8,736 | **225** | **105** |
| **19** | `Unknown0BService.hpp` | 8,655 | **132** | **112** |
| **20** | `MatchmakingService.hpp` | 7,779 | **116** | **111** |
| **21** | `IdentityConfig.cpp` | 6,983 | **165** | **106** |
| **22** | `MarketplaceService.hpp` | 3,915 | **87** | ★ **122** |
| **23** | `TencentService.cpp` | 3,773 | **94** | **117** |
| **24** | `InstantMessageService.hpp` | 3,465 | **66** | **112** |
| **25** | `ServiceRegistry.hpp` | 3,252 | **69** | **109** |
| **26** | `ContentUnlock2Service.cpp` | 3,251 | **79** | **117** |
| **27** | `ClanService.hpp` | 3,180 | **72** | ★ **122** |
| **28** | `LobbyProtocol.hpp` | 2,967 | **74** | **116** |
| **29** | `StatsService.hpp` | 2,891 | **60** | **117** |
| **30** | `RecoveredCatalog.cpp` | 2,984 | **54** | **109** |
| **31** | `ServiceRegistry.cpp` | 2,686 | **74** | **109** |
| **32** | `AckOnlyServices.cpp` | 2,645 | **57** | **109** |
| **33** | `AckOnlyServices.hpp` | 2,549 | **41** | **109** |
| **34** | `CodolStartupTasks.cpp` | 2,307 | **50** | **109** |
| **35** | `CodolClientPatches.hpp` | 2,094 | **41** | **108** |
| **36** | `TitleUtilitiesService.cpp` | 2,003 | **56** | **117** |
| **37** | `ByteBuffer.hpp` | 2,199 | **50** | **105** |
| **38** | `LanDiscovery.hpp` | 1,896 | **52** | **111** |
| **39** | `Profiles2Service.hpp` | 1,884 | **39** | ★ **122** |
| **40** | `Storage2Service.hpp` | 1,791 | **45** | **121** |
| **41** | `Friends2Service.hpp` | 1,627 | **38** | **121** |
| **42** | `AuthSession.cpp` | 1,474 | **50** | **105** |
| **43** | `Crypto.hpp` | 1,328 | **33** | **105** |
| **44** | `Auth3TlsTransport.hpp` | 939 | **31** | **108** |
| **45** | `ContentUnlock2Service.hpp` | 826 | **22** | **117** |
| **46** | `Auth3Protocol.hpp` | 791 | **29** | **105** |
| **47** | `TencentService.hpp` | 781 | **19** | **117** |
| **48** | `AuthSession.hpp` | 638 | **26** | **105** |
| **49** | `RecoveredCatalog.hpp` | 550 | **14** | **109** |
| **50** | `TitleUtilitiesService.hpp` | 513 | **16** | **117** |
| **51** | `Auth3ClientPatches.hpp` | 349 | **10** | **104** |
| **52** | `CodolStartupTasks.hpp` | 146 | **6** | **109** |
| **合计** | — | **549,733** | **11,000+** | **14 份报告（103–122）** |

### ★★★★★ 核对

```
文件数：**52** ✓（与 MANIFEST 一致）
总字节：**549,733** ✓（与报告 092 的目录统计一致）
```

---

## 五、★★★★★ **`Demonware` 模块的完整服务目录（跨报告汇总）**

### 5.1 ★★★★★ 服务 ID 与实现

| ID | 服务名 | 实现文件 | 任务数 | 报告 |
|---|---|---|---|---|
| **`0x03`** | **Teams/Clan** | `ClanService` | **24**（6 实装 + 18 ack） | 120 |
| **`0x04`** | **Stats** | `StatsService` | **3**（4/4 / 4/13 / 4/3） | 118 |
| **`0x06`** | **Messaging** | `InstantMessageService` | **3**（5 / 14 / 18） | 112 |
| **`0x08`** | **Profiles2** | `Profiles2Service` | **8** | 119 |
| **`0x09`** | **Friends2** | `Friends2Service` | **1**（0x1A） | 121 |
| **`0x0A`** | **Storage2** | `Storage2Service` | **4**（10 / 12 / 20 / 21） | 121 |
| **`0x0B`** | **Unknown0B（ROOM）** | `Unknown0BService` | **6**（+ 3 consumeUserPair） | 112–113 |
| **`0x0C`** | **TitleUtilities2** | `TitleUtilitiesService` | **2**（6 / 9） | 117 |
| **`0x15`** | **Matchmaking** | `MatchmakingService` | **8** | 110 |
| **`0x1C`** | **ContentUnlock2** | `ContentUnlock2Service` | **4** | 117 |
| **`0x44`** | **RichPresence** | `Friends2Service` | **1**（4） | 121 |
| **`0x47`** | **Tencent** | `TencentService` | **7** | 117 |
| **`0x50`** | **Marketplace** | `MarketplaceService` | **7**（32/130/70/154/107/174/203/230） | 114–115 |
| **`0x5D`** | **Unknown93** | `MarketplaceService` | **3**（4/131/1） | 114 |
| **`0x8A`** | **Matchmaking2** | `MatchmakingService` | **8**（与 0x15 同） | 110 |

★★★ **⇒ **15 个服务**有完整实现,合计 **约 90 个任务**。**

★★ **⇒ 与报告 109 的 `RecoveredCatalog` 的 27 个目录对照：**
```
**有实现（15）**：`0x03` `0x04` `0x06` `0x08` `0x09` `0x0A` `0x0B` `0x0C`
              `0x15` `0x1C` `0x44` `0x47` `0x50` `0x5D` `0x8A`
**仅有空 ack（由 AckOnlyServices 覆盖）**：`0x03/53` `0x03/46` `0x03/48` 等
**目录里有但未实现**：`0x21` `0x32` `0x43` `0x12` `0x1B` `0x26` `0x17` `0x0F` 等
```

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★ **`ClanService.hpp` 四个出处** | `logs/clan_protocol.md` **§3**（对象线格式）/**§4**（task 表）/ `tools/server/clans.py`（行为）/ **`logs/soc_protocol.md` §4**（typed 标签） |
| 2 | ★★★★★ **9 个 typed 标签（完整）** | **`0x01` bool / `0x03` u8 / `0x06` u16 / `0x07` i32 / `0x08` u32 / `0x09` i64 / `0x0a` u64 / `0x10` string(NUL) / `0x13` blob(u32 len+bytes)** |
| 3 | ★★★ v1 范围 | 五个闭环（建队/看自己的队/看成员/搜索/退队）+ 四类未实现（升降职/邀请/申请/聊天） |
| 4 | ★★★ **`Clan` 15 字段** | 与报告 120 的 `teamInfos` 12 字段对应 + `members` + `ownerId` + `name` |
| 5 | ★★★ **三个 role 值** | **`2` = owner / `1` = officer / `0` = member** |
| 6 | ★★ `nextTeamId_` | 从 **1** 开始 |
| 7 | ★★★★★ **`SecondaryCurrencyId = 2`** | = 客户端 `sub_6AF970` 搜索的 id ⇒ ✓ 与报告 114 的 `while (*v2 != 2)` **完全吻合** |
| 8 | ★★★★★ **`InventoryItem` 默认值即永久** | `expireDateTime` = **`UINT32_MAX`** / `expiryDuration` = **`INT64_MAX`** / `modifiedTime` = **`UINT32_MAX`** ⇒ ✓ 与报告 115 **一致** |
| 9 | ★★ 三层嵌套 | `SkuGrant` → `ItemGrant` → `InventoryItem` |
| 10 | ★★★ **三重缓存字段** | `skuGrantsCachePath_` / `skuGrantsCacheWriteTime_` / `skuGrantsCacheSize_` + `shared_ptr<const vector>` |
| 11 | ★★ 两个 mutex | `inventoryMutex_` / `skuGrantsMutex_`（独立） |
| 12 | ★★ `Profiles2Service` 8 任务 | 与报告 119 **一致** |
| 13 | ★★ `stripOptionalUserId` 是 static | 不依赖实例 |
| 14 | ★★★★★ **`Demonware` 52 文件全部完成** | **549,733 字节 / 11,000+ 行 / 14 份报告（103–122）** ✓ |
| 15 | ★★★★★ **15 个服务有完整实现** | 合计约 **90 个任务** |
| 16 | ★★ 与报告 109 的对照 | 有实现 15 个；目录里未实现的：`0x21` `0x32` `0x43` `0x12` `0x1B` `0x26` `0x17` `0x0F` |

---

## 七、结论

### 1. ★★★★★ **`backend\Demonware` 52 个文件全部读完**（549,733 字节 / 11,000+ 行 / 14 份报告）

### 2. ★★★★★ **15 个服务有完整实现，合计约 90 个任务**

### 3. ★★★★★ **`ClanService.hpp` 首次完整列出四个规格出处**

★ **⇒ 且给出完整的 9 个 typed 标签（与报告 105/120 一致）。**

### 4. ★★★★★ **`SecondaryCurrencyId = 2` 与报告 114 的 `while (*v2 != 2)` 完全吻合**

### 5. ★★★★ **`InventoryItem` 的结构体默认值就是"永久"**（三个 `MAX` 哨兵）

---

## 八、下一步

`backend\Demonware` 已完成。按报告 092 的目录顺序，接下来：

1. ★★★ **`backend`（根，13 文件 / 127,397 B）** —— `Servers.cpp`（624 行）/ `DedicatedBookingDispatcher`（926 行）/ `SharedRoom*`（4 文件）
2. **`game_server`（根，32 文件 / 2,175,797 B）** —— `Appmain.cpp`（10,564 行）/ `EngineBindings.cpp`（17,867 行）/ `*Patches`
3. **`server_mp`（154 文件 / 12,604,630 B）** —— 最大块
4. `localnetworking` / `platformwrapper` / `client_bridge` / `win32`
5. `source\` 非 `src` 部分（`docs` / `tools` / `assets` / `tests` / `distribution` / `.agents` / `references`）
