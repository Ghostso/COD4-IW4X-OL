# 学习报告 110（重开）— `MatchmakingService.cpp`（58,994 B / 1,174 行）

**学习范围**：`backend\Demonware\MatchmakingService.cpp` 全文（**1,174 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录七个重大发现**：①**`bdCommonAddr` 37B→67B 的三条独立证据** ②**会话记录尾部的 20 个字段（含 `version 796`）** ③**kind 1 vs kind 3 的硬性设计区分** ④**`Session.SecurityKey` 全零的实测** ⑤**一次 `resource deadlock` 的死锁修复** ⑥**`OLMOD_GAME_ENDPOINT` / `OLMOD_GAME_SECURITY_ID` / `OLMOD_GAME_SECURITY_KEY`** ⑦**RoomHostUid 的正确值**

---

## 一、★★★★★ **`bdCommonAddr` 37B → 67B（三条独立证据）**

### 1.1 ★★★★★ 完整注释（第 543–559 行，逐字）

```cpp
// ★★★ 2026-10-07 10:0x -- **6 槽 → 11 槽（37B → 67B）**（1102 2 37 的定因修复；单变量）。
//
// 定因（本轮，三条独立证据交叉确认）：
//   ① 客户端门常数：`sub_B95C50` 要求 `[MatchMakingInfo+0x118] == 0x43`（IDB 实测
//      `83 BB 18 01 00 00 43` @0xB95C8C；老外 2016 构建同位置是 `... 25` @0xA5561C = 37）。
//      该字段 = **bdCommonAddr 地址块的字节数**（`625CE0` 把"第一个字段的声明长度"抄进
//      `room+0x7350`），错误弹窗第二参直接把它打出来。
//   ② 两个客户端自己的 `21/1` 记录：老外 `1308 25`（37B，6 槽），我们 2021 客户端 `1308 43`
//      （67B）—— 我们客户端自己生成的就是 67。
//   ③ Antia 团队参考实现（`CODOL-AlphaBuild By Antia\CODOL_Server\lobby\dw-capture.py`
//      `_common_addr` 原文注释）："This build's blob is 37 bytes = 6 slots + natType,
//      against the **FINAL build's 11 slots**" —— FINAL build（= 本客户端代次）= 11 槽
//      = 11×6+1 = 67B。
//   ⇒ 服务端一直照老外形态发 4 个空槽（37B）⇒ 2021 客户端读到 37 ≠ 67 ⇒ 1102 2 37
//      ⇒ `21/3` 删会话 + `11/2` 退房、永不拨 28960。
```

### ★★★★★ 三条证据的完整拆解

| # | 证据 | 精确数据 |
|---|---|---|
| **1** | ★★★ **客户端门常数** | `sub_B95C50` 要求 **`[MatchMakingInfo+0x118] == 0x43`**；IDB 实测 **`83 BB 18 01 00 00 43`** @ **`0xB95C8C`**；老外 2016 构建同位置是 **`... 25`** @ **`0xA5561C`**（= **37**） |
| **2** | ★★ **两个客户端自己的 `21/1` 记录** | 老外 **`1308 25`**（37B,6 槽）；我们 2021 客户端 **`1308 43`**（**67B**） |
| **3** | ★★★ **Antia 团队参考实现** | `dw-capture.py` 的 `_common_addr` 注释："This build's blob is **37 bytes = 6 slots + natType**, against the **FINAL build's 11 slots**" ⇒ **11 × 6 + 1 = 67B** |

★★★ **⇒ 完整的因果：**
```
服务端一直照老外形态发 **37B**（6 槽）
        ↓
★★★ 2021 客户端读到 **37 ≠ 67** ⇒ 错误 **`1102 2 37`**
        ↓
★★★ ⇒ **`21/3` 删会话 + `11/2` 退房、永不拨 28960**
```

★★ **⇒ `0x43 = 67` / `0x25 = 37` ⇒ 两个十六进制值精确对应两个字节数。**

### ★★★★★ `commonAddress` 的精确构造（第 560–571 行）

```cpp
std::vector<std::uint8_t> output;
output.reserve(**67**);
appendEndpoint(output, endpoint.ipv4, endpoint.port);       // slot 0 = 本端地址（6 字节）
constexpr std::array<std::uint8_t, 6> EmptyEndpoint{
    0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,                      // ★ 空槽哨兵
};
for (int index = 0; index < **9**; ++index)
    output.insert(output.end(), EmptyEndpoint.begin(), EmptyEndpoint.end());   // 9 个空槽
appendEndpoint(output, endpoint.ipv4, endpoint.port);       // slot 10 = 发布地址
output.push_back(**1**);                                     // ★ natType = 1（open）
return output;
```

### ★★★★★ 完整的 67 字节布局

| 偏移 | 大小 | 内容 |
|---|---|---|
| **0–5** | **6** | ★ **slot 0 = 本端地址**（IPv4 4 + port 2） |
| **6–59** | **54** | ★★★ **9 个空槽**,每个 `00 FF 00 FF 00 00` |
| **60–65** | **6** | ★ **slot 10 = 发布地址**（与 slot 0 相同） |
| **66** | **1** | ★★ **`natType = 1`（open）** |

★★★ **⇒ 6 + 54 + 6 + 1 = **67** ✓**
**⇒ 且 `11 × 6 + 1 = 67` ⇒ **11 个槽 + 1 个 natType** ✓ 与证据 ③ **完全吻合**。**

### ★★★★★ 空槽哨兵 `00 FF 00 FF 00 00` 的解读

```
`00 FF 00 FF` ⇒ 可能是 `0.0.255.0` 或"无效地址"标记
`00 00`       ⇒ 端口 0
        ↓
★★★ 注释明确："**0.0.0.0 型哨兵，非 0**"（不是全零）
```

★ **⇒ 这与报告 104 的"`00FF00FF0000` 哨兵串"**完全一致** ✓**
**⇒ 即：当 `bdCommonAddr` 长度错误时,`securityId` 会从这个哨兵里取出来（报告 100 已记录）。**

---

## 二、★★★★★ **会话记录尾部的 20 个字段**

### 2.1 ★★★★★ `writeSessionRecordTail` 全文（第 818–868 行）

```cpp
void MatchmakingService::writeSessionRecordTail(
    ByteBuffer &object, const LanDiscovery::RemoteSession &session) const
{
    const auto roomId = static_cast<std::uint64_t>(session.id & 0x7FFFFFFFULL) | 1ULL;
    object.writeString(std::to_string(roomId));              // ① room id（十进制字符串）
    object.writeU64(localUserId_);                            // ② 主 ID
    const auto mapName = jsonString(session.properties, "Session.Map");
    object.writeString(mapName.empty() ? "mp_crash_tropical" : mapName);   // ③ 地图
    object.writeI32(**-695030357**);                          // ④ query criterion（0xD692ADAB）
    for (int index = 0; index != 6; ++index)
        object.writeI32(0);                                   // ⑤ 6 个 0
    const auto securityKey = jsonBytes(session.properties, "Session.SecurityKey");
    std::array<std::uint8_t, 16> key{};
    std::copy_n(securityKey.begin(), min(securityKey.size(), 16), key.begin());
    object.writeBlob(key);                                    // ⑥ 16 字节密钥
    object.writeI32(**19**);                                  // ⑦ query criterion
    object.writeI32(0);
    object.writeI32(0);
    object.writeI32(**8**);                                   // ⑧ query criterion
    object.writeI32(**-1**);
    object.writeI32(**796**);                                 // ⑨ ★★★ playlist 版本
    object.writeI32(**30**);                                  // ⑩ query criterion
    object.writeI32(0);
    object.writeI32(**7**);
    object.writeI32(0);
    object.writeI32(**0x0C0DE001**);                          // ⑪ room id（非零）
    object.writeU64(**RoomHostUid**);                         // ⑫ demonwareID / room id
    object.writeI32(0);
    object.writeI32(0);
    object.writeI32(0);
    object.writeI32(**1**);
    object.writeI32(0);
}
```

### ★★★★★ 完整的字段表

| # | 类型 | 值 | 说明 |
|---|---|---|---|
| **①** | **String** | `to_string(session.id & 0x7FFFFFFF \| 1)` | ★★ **十进制字符串**（见下） |
| **②** | **U64** | `localUserId_` | ★★★ **自己的 userId**（不是 `1000001`） |
| **③** | **String** | `"mp_crash_tropical"`（默认） | 地图名 |
| **④** | **I32** | ★ **`-695030357`** | query criterion（= `0xD692ADAB`） |
| **⑤** | I32×6 | **0** | 6 个零 |
| **⑥** | **Blob** | **16 字节** `Session.SecurityKey` | ★★ 密钥 |
| **⑦** | **I32** | ★ **`19`** | query criterion |
| **⑧** | I32 | **0** / **0** | |
| **⑨** | **I32** | ★ **`8`** | query criterion |
| **⑩** | I32 | ★ **`-1`** | |
| **⑪** | **I32** | ★★★ **`796`** | ★★★ **`mp_playlists_shipRetail_release.info` 的版本号** |
| **⑫** | **I32** | ★ **`30`** | query criterion |
| **⑬** | I32 | **0** / **7** / **0** | |
| **⑭** | **I32** | ★ **`0x0C0DE001`** | ★★ **room id（非零）** |
| **⑮** | **U64** | **`RoomHostUid`** | ★★★ demonwareID / room id |
| **⑯** | I32×5 | **0 / 0 / 0 / 1 / 0** | |

### ★★★★★ **`796` 与报告 079 的精确吻合**

```
报告 079（`mp_playlists_shipRetail_release.info`）：
  第 1 行 = **`version 796`**
        ↓
★★★★★ 本报告：会话记录的字段 ⑪ = **`796`**
   ⇒ 注释逐字："**`mp_playlists_shipRetail_release.info` version 796**"
        ↓
★★★ ⇒ **会话记录携带 playlist 版本号** ⇒ 客户端据此判断 playlist 是否匹配
```

### ★★★★★ 两个"必须"（逐字）

```
"room id   **MUST be a NON-ZERO DECIMAL STRING**. `MatchController.as` rejects a join when
           `_strtoui64(room.id)` equals the `last_kick_room_id` dvar, which is unset and
           so parses to 0; a non-numeric id also parses to 0, and **0 == 0 reported every
           join as a kick**.
 host uid  **MUST NOT be the player's own CODOID**, or the client addresses the room join
           to itself and discards its own reply."
```

★★★★★ **⇒ 两条精确的"必须"：**
```
① ★★★ **room id 必须是非零十进制字符串**
   ⇒ 因为 `_strtoui64(room.id)` 与 `last_kick_room_id` 比较
   ⇒ 后者**未设置 ⇒ 解析为 0**
   ⇒ **非数字的 id 也解析为 0** ⇒ **`0 == 0` ⇒ 每次加入都报"被踢"**
        ↓
② ★★★ **host uid 不能是玩家自己的 CODOID**
   ⇒ 否则客户端**把加入消息发给自己并丢弃回复**
```

★★ **⇒ 第 ② 条与报告 109 的 `RoomHostUid` 注释**完全一致** ✓**

### ★★★★★ 主 ID 的**黄金对齐**（第 826–832 行，逐字）

```cpp
// ★★★ 2026-10-07 05:0x -- **主 ID 改回"自己"（黄金对齐，单变量）**：
// 这个字段 = 客户端记录 `+0x168`，客户端拿它 (a) 当 `mmbook` 请求的收件人、
// (b) 存进 `room+0x3A048/+0x3A04C` 供 `HandleMMBookReply` 比对。
// 黄金抓包（`成果-抓包定因…-1645.md` §9.1）：跑通轮客户端发的 `6/14 mmbook` 收件人
// = `0x01100001DEADC0DE`（= account userId），不是合成 `1000001`。
// 我们发 1000001 ⇒ 收件人 ≠ localUserId ⇒ 服务端走"转发"分支、且回执推送 sender 也对不上。
object.writeU64(**localUserId_**);
```

★★★★★ **⇒ 一个精确的"黄金对齐"：**
```
黄金抓包：跑通轮客户端发的 `6/14 mmbook` **收件人 = `0x01100001DEADC0DE`**
        ↓
★★★ 而 `0x01100001DEADC0DE` = **account userId**（与报告 105 的 `0x0110000100000000` 前缀一致）
        ↓
★★★ 旧实现发 **`1000001`**（合成值）⇒ **收件人 ≠ localUserId**
   ⇒ 服务端走"**转发**"分支、且**回执推送 sender 也对不上**
        ↓
★★★★★ ⇒ 改为 **`localUserId_`** ✓
```

★★ **⇒ 这解决了报告 109 里 `RoomHostUid = 1000001` 的困惑：**
```
报告 109：`RoomHostUid = 1000001`（来自 C# 参考）
        ↓
★★★ 本报告：**主 ID（字段②）用 `localUserId_`,不是 `RoomHostUid`**
   ⇒ 而 `RoomHostUid` 用在**字段⑮**（`demonwareID / room id`）
        ↓
★★★ ⇒ **两个不同的 ID 用在两个不同的字段**
```

---

## 三、★★★★★ **kind 1 vs kind 3 的硬性设计区分**

### 3.1 ★★★★★ 完整注释（第 875–906 行，逐字）

```cpp
// LOCAL OVERRIDE (DSH, 2026-10-05 19:0x) -- KIND 3 ALSO GETS THE SERVER CANDIDATE.
//
// ★★ 2026-10-05 19:5x —— **我 19:0x 的改动已回退，下面是为什么。**
//
// 我当时的推理：`21/5` 的 75 B 请求头是 `08 03 00 00 00`（kind 3），
// 而代码专门把 server 会话从 kind 3 结果里删掉 ⇒ 客户端永远拿不到候选 ⇒ 匹配无效。
// 于是我把 kind 3 也改成插 server 候选。
//
// **那是错的。** 老外原文（`research\source_reconstruction_progress.md:172-190`）逐字：
//
//   The historical PVP run advanced to `mmstart` because task `0x15/5` returned the
//   client-created player lobby for a query whose leading typed `uint32` was `1`
//   (`MatchMaking_FIND_SERVERS_Query`). ... The handler now distinguishes
//   kind `1` from kind `3` (`MatchMaking_FIND_LOBBIES_BY_PLAYLIST_Query`) and **excludes
//   the local lobby from server searches.** The first story mission's empty server result
//   and **busy-server UI are now the expected behavior until an explicit external server
//   candidate is registered.**
//
//   An explicit-candidate probe now exists ... **The backend accepts only remote discovery
//   sessions labelled `Session.Role=server` for `FIND_SERVERS` and excludes those sessions
//   from playlist-lobby queries.**
//
// ⇒ 两条硬结论：
//   1. **kind 3 排除 server 会话是故意设计**（kind 3 = 找 lobby，不是找 server）。
//   2. **「服务器繁忙」是"还没有外部 server 候选注册"时的预期 UI**，不是某个 bug 的症状。
```

### ★★★★★ 两个 kind 的完整语义

| kind | 常量 | 含义 | server 会话 |
|---|---|---|---|
| **`1`** | **`FindServersQuery`** | ★ **FIND_SERVERS**（找服务器） | ★★★ **只保留 `Session.Role=server`** |
| **`3`** | **`FindPlaylistLobbiesQuery`** | ★ **FIND_LOBBIES_BY_PLAYLIST**（按 playlist 找大厅） | ★★★ **排除 `Session.Role=server`** |

★★★ **⇒ 两条完全相反的处理：**
```
kind 1 ⇒ `std::erase_if(sessions, [](s){ return **!isServerSession**(s.properties); });`
          ⇒ **只留 server 会话**
        ↓
kind 3 ⇒ `std::erase_if(sessions, [](s){ return **isServerSession**(s.properties); });`
          ⇒ **删掉 server 会话**
```

### ★★★★★ "服务器繁忙"是**预期行为**（不是 bug）

```
"the **busy-server UI are now the expected behavior** until an explicit external
 server candidate is registered."
        ↓
★★★★★ ⇒ **在还没有外部 server 候选时,"服务器繁忙"是正确的 UI**
```

★★ **⇒ 这是一个**重要的判据**：不要为了消除"服务器繁忙"而放宽 kind 3。**

### ★★★★★ 一次**回退**的完整记录（第 877–898 行）

★★ **⇒ 作者在 19:0x 改了 kind 3,19:5x 就回退了,并写下了完整的理由。**
**⇒ 这是**"先改后撤 + 记录原因"的诚实做法**（与报告 109 的自我更正同类）。**

---

## 四、★★★★★ **`Session.SecurityKey` 全零的实测**

### 4.1 ★★★★★ 完整注释（第 350–368 行，逐字）

```cpp
// ★ 2026-10-05 21:5x -- LOCAL OVERRIDE (DSH): the 16-byte DTLS security key carried by
// the session descriptor, for `Session.SecurityKey`.
//
// WHY THIS IS MISSING TODAY.  `writeSessionRecordTail` (upstream `MatchmakingService.cpp:531-537`,
// ours is the same code) fills the record's 16-byte key from
//     jsonBytes(session.properties, "Session.SecurityKey")
// but **NEITHER upstream's `findSessions` candidate (upstream `:585-592`) NOR ours ever puts
// that property in**.  MEASURED 2026-10-05 21:24:53, decoding the object we actually put on the
// wire (`decode_candidate_object.py`):
//     130810000000 00000000000000000000000000000000
//     ^ marker      ^ **16 bytes of ZERO**  <- Session.SecurityKey
// Every other field of that record matched upstream's field list exactly (roomId decimal string
// "2118550191", hostUid 1000001, map "mp_crash_tropical", criterion -695030357, 0x0C0DE001, ...).
```

### ★★★★★ 实测的字节

```
`130810000000`  ⇒ ★ marker（`Blob` 0x13 + 长度 `08 10 00 00 00`? = 16 字节）
`00000000000000000000000000000000` ⇒ ★★★ **16 字节全零**
        ↓
★★★ ⇒ 即：**`Session.SecurityKey` 从未被填过** ⇒ 记录里是 16 个零
```

★★ **⇒ 且注释列出**其他字段全部正确**：**
```
roomId = **"2118550191"**（十进制字符串）
hostUid = **1000001**
map = **"mp_crash_tropical"**
criterion = **-695030357**
room id = **0x0C0DE001**
        ↓
★★★ ⇒ 与 `writeSessionRecordTail` 的字段值**逐一吻合** ✓
```

### ★★★★★ `securityKeyFromDescriptor` 的 marker 解析（第 369–413 行）

```cpp
constexpr std::array<std::uint8_t, 6> marker{ **0x13, 0x08, 0x10, 0x00, 0x00, 0x00** };
const auto found = std::search(descriptor.begin(), descriptor.end(),
    marker.begin(), marker.end());
if (found == descriptor.end() ||
    static_cast<std::size_t>(descriptor.end() - found) < marker.size() + **16**)
{
    return {};
}
return std::vector<std::uint8_t>(found + marker.size(), found + marker.size() + **16**);
```

★★★★★ **⇒ 精确的 marker：`13 08 10 00 00 00`**
```
`0x13` ⇒ **Blob 类型码**（报告 105 已确认）
`0x08` ⇒ ★ 可能是嵌套的 `U32` 类型码
`0x10 00 00 00` ⇒ ★★ **16（小端 u32）** ⇒ 长度
        ↓
★★★ ⇒ 即：**一个 16 字节的 Blob,前面还有一层 `0x08`**
   ⇒ 与实测的 `130810000000` **完全吻合** ✓
```

★★ **⇒ 且注释指出出处：**`CodolGameplayProbe.py:87-92 extract_descriptor_security_key`**（上游的同一个访问器）。**

### ★★★ 三个外部战斗服环境变量（第 372–402 行）

```cpp
// ★ 2026-10-20 本地整合·阶段1（单变量）：外部战斗服的 16 字节会话密钥。
// OLMOD_GAME_SECURITY_KEY=<32 hex> ⇒ 直接返回这 16 字节（= 他们 DS 的
// run/ds/home/securitykey.bin 内容）；不设则走原 marker 解析。
```

★★★ **⇒ `OLMOD_GAME_SECURITY_KEY`（32 个十六进制字符 = 16 字节）**
**⇒ 且注明来源：**他们 DS 的 `run/ds/home/securitykey.bin`**。**

---

## 五、★★★★★ **一次 `resource deadlock` 的死锁修复**

### 5.1 ★★★★★ 完整注释（第 1022–1033 行，逐字）

```cpp
// ★★★ 2026-10-07 03:0x -- **死锁修复**（A 补丁自己的 bug，实测 `fail`）。
//
// 这里原本又套了一层 `std::scoped_lock candidateLock(localMutex_);`，而上面 `:775`
// 的 `std::scoped_lock lock(localMutex_)` 在**同一个 else 块内仍然持有它**；
// `localMutex_` 是**非递归** `std::mutex`（`MatchmakingService.hpp:72`）⇒ 同线程二次
// 加锁抛 `std::system_error("resource deadlock would occur")` ⇒ 整个 LSG 帧被丢弃：
//     [02:45:48] LSG_REQUEST sequence=55 service=21 task=5 payload=0803000000…
//     [02:45:48] Rejected LSG frame: resource deadlock would occur
//     [02:47:17] LSG_REQUEST sequence=74 service=21 task=5 payload=0803000000…
//     [02:47:17] Rejected LSG frame: resource deadlock would occur
// ⇒ **kind 3 一条应答都发不出去**，客户端点匹配后只停在「正在快速加入」（甲方截图 4）。
```

### ★★★★★ 完整的死锁链

```
① 外层 `std::scoped_lock lock(localMutex_)` 在 else 块里持有锁
        ↓
② 内层又 `std::scoped_lock candidateLock(localMutex_)`
        ↓
★★★ ③ `localMutex_` 是**非递归** `std::mutex`（`MatchmakingService.hpp:72`）
        ↓
★★★ ④ 同线程二次加锁 ⇒ 抛 **`std::system_error("resource deadlock would occur")`**
        ↓
★★★ ⑤ ⇒ **整个 LSG 帧被丢弃**
        ↓
★★★★★ ⑥ ⇒ **kind 3 一条应答都发不出去** ⇒ 客户端停在「**正在快速加入**」
```

★★ **⇒ 实测日志（两条）都显示 `Rejected LSG frame: resource deadlock would occur`。**

★ **⇒ 修复：**去掉内层锁**（"外层锁已覆盖,这里直接用,不再加锁"）。**

### ★★★ 两处 `armForcedAllocationPatch()` 的调用点

```cpp
// kind 1 分支（第 972 行）
armForcedAllocationPatch();

// kind 3 分支（第 1058 行）
armForcedAllocationPatch();
```

★★★ **⇒ 两个分支都调用 ⇒ 与报告 107 的"冷启动武装补漏"呼应。**

### ★★★★★ 冷启动武装补漏的完整理由（第 956–971 行，逐字）

```
"实测缺口（`AlwaysofflineRe.Localnet32.log` 原文）：
   **20:37:51** 客户端**重启后第一次进房** → `21/5` 的第一问是 **kind 3**，
            应答 `…0305 0800000000` = **0 个对象**（此刻后端还没有任何 descriptor：
            `localProperties_` 与 `rememberedServerDescriptor()` 都是空，
            客户端的 `21/1` 在它**之后**才来）⇒ kind-3 分支的
            `armForcedAllocationPatch()` **根本没被调用** ⇒ 分配门不强制
            ⇒ 连 43 B `11/4` 分配请求都发不出去 ⇒ 「服务器繁忙」/加载流程到不了。
   **20:39:29** 60 s 后那条 **kind 1** 应答**确实带了完整 server 候选**
            （`1308430000 7F000001 2071 …` = 127.0.0.1:28960 + `Session.Demonware`），
            而**这条分支从来不武装** ⇒ 候选白给。
   ⇒ 在 kind-1 插完候选的**同一处**补上武装，与 kind-3 同权。"
        ↓
★★★ ⇒ **两条时间线 + 一条字节证据：**
   `1308430000 7F000001 2071 …` ⇒ ★ **`1308 43` = Blob 长度 67** + `7F000001` = **127.0.0.1** + `2071` = **28960**（小端 `0x7120`）
```

★★ **⇒ `0x7120` = 28,960 ✓ 与"永不拨 28960"里的端口**完全吻合**。**

---

## 六、★★★★★ **`OLMOD_GAME_ENDPOINT` 与三个环境变量**

### 6.1 ★★★★★ 完整解析（第 251–288 行）

```cpp
// ★ 2026-10-20 本地整合·阶段1（单变量）：外部战斗服端点。
// OLMOD_GAME_ENDPOINT="127.0.0.2:28960" ⇒ FIND_SERVERS 直接下发它，
// 与本进程是否加载 CodolGameServer.Localnet32 无关（= 他们的原生 DS）。
// 不设该变量 ⇒ 原分支不变。
char endpointText[64]{};
const auto endpointSize = GetEnvironmentVariableA(
    "OLMOD_GAME_ENDPOINT", endpointText, sizeof(endpointText));
...
if (std::sscanf(host.c_str(), "%u.%u.%u.%u%n",
        &octets[0], &octets[1], &octets[2], &octets[3], &consumed) == 4 &&
    consumed == static_cast<int>(host.size()) &&
    octets[0] < 256 && octets[1] < 256 && octets[2] < 256 && octets[3] < 256)
{
    const auto port = std::strtoul(text.c_str() + colon + 1, nullptr, 10);
    if (port > 0 && port <= 0xFFFF)
    {
        const auto ipv4 = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3];
        ...
        return GameServerEndpoint{ .ipv4 = ipv4, .port = port };
    }
}
```

### ★★★★★ 三个外部战斗服环境变量

| 变量 | 格式 | 用途 |
|---|---|---|
| **`OLMOD_GAME_ENDPOINT`** | ★ **`"127.0.0.2:28960"`** | ★★★ **外部战斗服端点** ⇒ `FIND_SERVERS` 直接下发 |
| **`OLMOD_GAME_SECURITY_KEY`** | ★ **32 个十六进制字符** | 16 字节会话密钥（来自他们的 `securitykey.bin`） |
| **`OLMOD_GAME_SECURITY_ID`** | ★ **16 个十六进制字符** | ★★ **`bdSecurityID`**（见下） |

★★★ **⇒ 这是**"本地整合"的三个开关** ⇒ 用于对接**外部的原生 DS**。**
**⇒ 与报告 106 的 `OLMOD_PLATFORM_USER_ID` 一起 ⇒ `OLMOD_*` 累计 **18 个**。**

### ★★★★★ `OLMOD_GAME_SECURITY_ID` 的**逆变换**（第 33–88 行，逐字）

```cpp
// ★ 2026-10-20 第三十轮：`OLMOD_GAME_SECURITY_ID=<16 hex>` = **希望 DS 看到的那个值**。
//   实测变换（甲方两次报错回代）：打印值 = reverse( reverse(M字节) XOR 我方id的LE字节 )，
//   M = **0x53525652564F4443**（本文件 886/988 行的 `processSessionNumericId() ^ M`）。
//   ⇒ 这里直接做**逆变换**，调用方只填想要的值，不再需要自己算逆象。
//   依据 `codol-revival-main/logs/goal2_recon.md:122`：会话 blob 的 sessionId(8) 就是 bdSecurityID。
```

### ★★★★★ 完整的变换与逆变换

```
**变换（发送时）**：`sessionId = processSessionNumericId() ^ M`
  `M = **0x53525652564F4443**`
        ↓
★★★ 解码 `0x53525652564F4443`（小端）
  `43 44 4F 56 52 56 53 53` ⇒ **`CDOVRVSS`**?
        ↓
★★★ 更可能按大端：`53 52 56 52 56 4F 44 43` ⇒ **`SRVRVODC`**?
        ↓
★★★ 实际注释说"`M = 0x53525652564F4443`"，未解码
        ↓
**逆变换（本函数）**：
  `preimage[i] = desired[7-i] ^ reversedMagic[i]`
  其中 `reversedMagic[i] = M >> ((7-i)*8)`（**字节反转**）
        ↓
★★★★★ ⇒ 即：`preimage = reverse(reverse(M字节) XOR desired的LE字节)`
   ⇒ 这样 `processSessionNumericId() ^ M` 就**正好等于 desired**
```

★ **⇒ 这是一个**精确的代数逆变换**（作者自己推导的）。**

### ★★★ 默认的 sessionId 生成（第 89–114 行）

```cpp
QueryPerformanceFrequency(&frequency);
QueryPerformanceCounter(&counter);
const auto nanoseconds = 1e9 * (ticks / ticksPerSecond) + 1e9 * (ticks % ticksPerSecond) / ticksPerSecond;
std::array<std::uint8_t, 8> id{};
std::memcpy(id.data(), &nanoseconds, sizeof(nanoseconds));    // ★ 纳秒时间戳
const auto seed = static_cast<unsigned int>(std::time(nullptr)) & **0xFEFEFEFE**;
std::srand(seed);
auto index = std::size_t{ 1 };
do
{
    id[index] ^= id[index - 1];                              // ★ 链式异或
    index = static_cast<std::size_t>(std::rand() % 8 + 1);
}
while (index < 7);
```

★★★ **⇒ 默认生成是**"纳秒时间戳 + 随机链式异或"**：**
```
① 取**纳秒级时间戳**（8 字节）
② 用 `time(nullptr) & 0xFEFEFEFE` 播种 `srand`
③ **链式异或**：`id[index] ^= id[index-1]`,index 随机跳跃
        ↓
★★★ ⇒ 一个**廉价的伪随机扰动**（不是密码学安全的）
```

---

## 七、★★★★★ **服务注册与 8 个任务**

### 7.1 ★★★★★ `registerTasks`（第 620–660 行）

```cpp
registry.registerTask(service, **1**,  prefix + "::createSession");
registry.registerTask(service, **2**,  prefix + "::updateSession");
registry.registerTask(service, **3**,  prefix + "::deleteSession");
registry.registerTask(service, **5**,  prefix + "::findSessions");
registry.registerTask(service, **9**,  prefix + "::submitPerformance");
registry.registerTask(service, **10**, prefix + "::getPerformanceValues");
registry.registerTask(service, **12**, prefix + "::updatePlayers");
registry.registerTask(service, **16**, prefix + "::findSessions");    // ★ 与 5 同一函数
...
registerService(**0x15**, "Matchmaking");
registerService(**0x8A**, "Matchmaking2");
```

### ★★★★★ 完整的 8 个任务 × 2 个服务

| task | 名称 | 说明 |
|---|---|---|
| **1** | `createSession` | 建会话 |
| **2** | `updateSession` | 更新会话 |
| **3** | `deleteSession` | 删会话 |
| **5** | `findSessions` | ★ 查找 |
| **9** | `submitPerformance` | 提交性能 |
| **10** | `getPerformanceValues` | 取性能 |
| **12** | `updatePlayers` | 更新玩家数 |
| **16** | ★★ **`findSessions`** | ★ **与 task 5 同一个函数** |

★★★ **⇒ task **16** 与 task **5** 用**同一个 `findSessions`** ⇒ 但 kind 从 payload 读 ⇒ 行为不同。**

★★ **⇒ 两个服务 **`0x15`（Matchmaking）** 与 **`0x8A`（Matchmaking2）** ⇒ **同一套 8 个任务注册两遍**。**

### ★★★ `createSession` 的响应（第 739–741 行）

```cpp
ByteBuffer object;
object.writeBlob(**processSessionId()**);          // ★ 8 字节 sessionId
return ServiceResponse{ .task = request.task, .objects = { object.data() } };
```

★★ **⇒ 建会话的响应就是**一个 8 字节 Blob**（sessionId）。**

### ★★★ 四个错误码

```cpp
return ServiceResponse{ .error = **1000**, .task = request.task };    // ★ 参数解析失败
```

★★ **⇒ 统一用 **`error = 1000`**（5 处）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`bdCommonAddr` 37B→67B** | 三条证据：①`sub_B95C50` 要求 **`[+0x118] == 0x43`**（IDB `83 BB 18 01 00 00 43` @`0xB95C8C`；老外是 `...25` @`0xA5561C`=37）②老外 `1308 25`(37B) vs 我们 `1308 43`(**67B**) ③Antia `dw-capture.py`："37 bytes = 6 slots + natType, against the **FINAL build's 11 slots**" |
| 2 | ★★★ 后果 | 服务端发 37 ⇒ 2021 客户端读 37 ≠ 67 ⇒ **`1102 2 37`** ⇒ `21/3` 删会话 + `11/2` 退房、**永不拨 28960** |
| 3 | ★★★★★ **67 字节布局** | `slot0(6) + 9×空槽(54) + slot10(6) + natType(1)` = **67** ✓；`11×6+1=67` ✓ |
| 4 | ★★★ 空槽哨兵 | **`00 FF 00 FF 00 00`**（"0.0.0.0 型哨兵,非 0"）⇒ 与报告 104 的 `00FF00FF0000` **一致** |
| 5 | ★★ natType | **`1`**（open） |
| 6 | ★★★★★ **会话记录 20 字段** | 含 ★ **`-695030357`**（`0xD692ADAB`）/ **`19`** / **`8`** / **`-1`** / ★★★ **`796`** / **`30`** / **`0x0C0DE001`** / **`RoomHostUid`** |
| 7 | ★★★★★ **`796` 的印证** | = `mp_playlists_shipRetail_release.info` 的 `version 796` ✓ 与报告 079 **完全吻合** |
| 8 | ★★★★★ **两个"必须"** | ①room id **必须非零十进制字符串**（否则 `0 == 0` ⇒ **每次加入都报"被踢"**）②host uid **不能是玩家自己的 CODOID** |
| 9 | ★★★★★ **主 ID 的黄金对齐** | 黄金抓包 `6/14 mmbook` 收件人 = **`0x01100001DEADC0DE`**（account userId）；旧值 `1000001` ⇒ 收件人 ≠ localUserId ⇒ **走"转发"分支** ⇒ 改为 **`localUserId_`** |
| 10 | ★★★ 两个 ID 的分工 | 字段② = **`localUserId_`**；字段⑮ = **`RoomHostUid`**（`1000001`） |
| 11 | ★★★★★ **kind 1 vs kind 3** | **kind 1 = FIND_SERVERS** ⇒ **只留 `Session.Role=server`**；**kind 3 = FIND_LOBBIES_BY_PLAYLIST** ⇒ **删掉 server 会话** |
| 12 | ★★★★★ **"服务器繁忙"是预期行为** | "the **busy-server UI are now the expected behavior** until an explicit external server candidate is registered" |
| 13 | ★★★ 一次回退 | 19:0x 改了 kind 3,19:5x 回退并记录理由（"**那是错的**"） |
| 14 | ★★★★★ **`Session.SecurityKey` 全零** | 实测 `130810000000` + **16 字节全零**（`decode_candidate_object.py`,21:24:53）；其他字段全对（roomId `"2118550191"` / hostUid `1000001` / map `"mp_crash_tropical"` / criterion `-695030357` / `0x0C0DE001`） |
| 15 | ★★★★ **marker** | **`13 08 10 00 00 00`**（`0x13` Blob + `0x08` + **`0x10`=16**）⇒ 后跟 16 字节密钥 |
| 16 | ★★★ marker 出处 | `CodolGameplayProbe.py:87-92 extract_descriptor_security_key` |
| 17 | ★★★★★ **一次死锁** | 内层又锁非递归 `localMutex_` ⇒ **`std::system_error("resource deadlock would occur")`** ⇒ **整个 LSG 帧被丢弃** ⇒ **kind 3 一条应答都发不出去** ⇒ 客户端停在「**正在快速加入**」 |
| 18 | ★★★★ **冷启动武装补漏** | **20:37:51** 首次进房先问 kind 3 ⇒ 0 对象 ⇒ `armForcedAllocationPatch()` 未调用；**20:39:29** 60 s 后 kind 1 带完整候选（**`1308430000 7F000001 2071`** = Blob 67 + **127.0.0.1** + **28960**）但**从不武装** ⇒ 补上 |
| 19 | ★★★ 端口印证 | `0x7120` = **28,960** ✓ 与"永不拨 28960"吻合 |
| 20 | ★★★★★ **三个外部战斗服变量** | **`OLMOD_GAME_ENDPOINT`**（`"127.0.0.2:28960"`）/ **`OLMOD_GAME_SECURITY_KEY`**（32 hex）/ **`OLMOD_GAME_SECURITY_ID`**（16 hex） |
| 21 | ★★★★ **`OLMOD_GAME_SECURITY_ID` 的逆变换** | 变换 `sessionId = processSessionNumericId() ^ M`,`M = **0x53525652564F4443**`；逆变换 `preimage[i] = desired[7-i] ^ reversedMagic[i]` |
| 22 | ★★ 默认 sessionId | **纳秒时间戳** + `srand(time & 0xFEFEFEFE)` + **链式异或**（`id[i] ^= id[i-1]`,索引随机跳跃） |
| 23 | ★★★ **8 个任务 × 2 个服务** | task **1/2/3/5/9/10/12/16**（★ **16 与 5 同一函数**）；服务 **`0x15`** 与 **`0x8A`** |
| 24 | ★★ `createSession` 响应 | **一个 8 字节 Blob**（`processSessionId()`） |
| 25 | ★ 错误码 | 统一 **`1000`**（5 处） |
| 26 | ★★ `OLMOD_*` 累计 | **18 个** |

---

## 九、结论

### 1. ★★★★★ **`bdCommonAddr` 从 37B 改到 67B,有三条独立证据**

```
① 客户端门常数 `0x43`（67）vs 老外 `0x25`（37）
② 两个客户端自己的记录：老外 `1308 25` vs 我们 `1308 43`
③ Antia 的 dw-capture.py："FINAL build's 11 slots" ⇒ 11×6+1 = 67
        ↓
★★★ 发 37 ⇒ `1102 2 37` ⇒ 删会话 + 退房 + **永不拨 28960**
```

### 2. ★★★★★ **会话记录携带 `796`**（= `mp_playlists` 的 `version`）

★ **⇒ 与报告 079 精确吻合,这是 playlist 版本协商的载体。**

### 3. ★★★★★ **kind 1 与 kind 3 是刻意的相反设计,"服务器繁忙"是预期行为**

### 4. ★★★★★ **`Session.SecurityKey` 曾全零**（实测 `130810000000` + 16 个零）

### 5. ★★★★★ **一次 `resource deadlock` 让 kind 3 完全无法应答**

★ **⇒ 非递归 `std::mutex` 同线程二次加锁。**

### 6. ★★★★★ **三个外部战斗服环境变量 + 一个精确的代数逆变换**

### 7. ★★★★ **主 ID 的黄金对齐**（`localUserId_` 而不是 `1000001`）

---

## 十、下一步

- `MatchmakingService.hpp`（116 行）
- `MarketplaceService`（1,099 行）/ `StatsService`（875 行）/ `LobbyProtocol`（807 行）
- 其余 Service 与 `LanDiscovery` / `SharedRoom*`
