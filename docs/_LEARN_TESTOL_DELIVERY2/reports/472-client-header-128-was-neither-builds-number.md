# 472 · **"128 既不是任何一个 build 的数"** —— `sv_client_mp.hpp` 的 `512/256` 环形缓冲、`8 → 32` 的 usercmd 上限、以及"一个字段与一个序列化器而没有任何东西写它"

## 一、范围

本报告学习 `sv_client_mp.hpp`（**`883` 行**）全文件：`ServerReliableCommandCapacity = 512` 的 XOR 键、`PendingUserCmdCapacity = 32` 的实测、`ClientSlot` 的四个 pending/committed 对、`newestFlaggedSnapshotMessage` 与 `baselineCacheInitializationMessage` 的分工、`teamPolicy()` 的单点派生、`SvClientTimeouts` 的 `80/240 → 45/15`、以及 `ServerCore` 级的记分板指纹。

## 二、**"128 既不是任何一个 build 的数"**（本组最重要的一段）

### 2.1 那段

```cpp
constexpr std::size_t ClientCommandPrefixCapacity = 64;
// OLMOD(section-82): THIS ONE IS NOT OURS TO CHOOSE. The comment above says these
// are source-side capacities, and for ClientCommandPrefixCapacity that is true --
// but `reliableCommandResolver` in sv_client_mp.cpp reproduces the CLIENT'S OWN
// indexing, because the client XORs its packet with
// `serverCommands[reliableAcknowledge & mask]`. Pick a different mask and the two
// sides derive the key from different slots the moment a sequence exceeds it.
//
// out.exe's CL_ParseCommandString is sub_4737E0 and says the mask outright:
//
//   3.3.3.3  sub_46E3B0    and ebx, 0FFh    shl ebx,0Ah   lea esi,[ebx+ecx+40154h]
//   out.exe  sub_4737E0    and ebx, 1FFh    shl ebx,0Ah   lea esi,[ebx+ecx+80154h]
//
// Same 1024-byte slots, same `push 3FFh` strncpy, same `xor ecx, 0D362501Fh`
// pointer cookie -- and 512 entries where 3.3.3.3 has 256. The sequence field and
// the ring base both move by 0x40000, which is exactly the extra 256 slots.
//
// **128 WAS NEITHER BUILD'S NUMBER.** It also made the staleness guard in
// reliableCommandResolver return an empty key for any gap of 128..511, which is a
// second way to desync the same XOR.
constexpr std::size_t ServerReliableCommandCapacity = 512;
static_assert(std::has_single_bit(ServerReliableCommandCapacity));
```

### 2.2 二十四层

```text
1. **`ClientCommandPrefixCapacity = 64` 【是【我们**的**】
2. ⇒ **⚠ 而【`ServerReliableCommandCapacity` 【不是【我们【可以选**的**】
3. ⇒ **⇒ 因为【`reliableCommandResolver` 【复现【客户端【自己的索引**】
4. ⇒ **⇒ 而【客户端【用一个 `serverCommands[reliableAcknowledge & mask]` **XOR** 它的包**】
5. ⇒ **⇒ 所以【选一个不同的掩码 ⇒ 【两边【从【不同的槽**推导【那个键**】
6. ⇒ **⇒ 而【那【只在【一个序列【超过【那个掩码**时【发生**】
7. ⇒ **两个 build 的掩码**：3.3.3.3 `0FFh` ⇒ `256` / out.exe `1FFh` ⇒ `512`**
8. ⇒ **⇒ 而【同样的 `1024` 字节槽、同样的 `push 3FFh` 的 `strncpy`、同样的 `xor ecx, 0D362501Fh` 指针 cookie**】
9. ⇒ **⇒ 而【`512` 个【对 `256` 个**】
10. ⇒ **⇒ 而【那个序列字段与那个环基【都移动 `0x40000`**】
11. ⇒ **⇒ 而【`0x40000` 【恰好是【多出来的那 `256` 个槽**】（`256 × 1024 = 262144 = 0x40000`）**
12. ⇒ **⚠ 【`128` 既不是任何一个 build 的数**】**
13. ⇒ **⇒ 而它【还【让【那个陈旧性守卫【对【任何 `128..511` 的间隙【返回【一个空键**】
14. ⇒ **⇒ 而【那【是【同一个 XOR 的【第二条失同步**路径**】
```

### 2.3 ⭐⭐⭐ **"128 既不是任何一个 build 的数"**

**✅ 这是本报告里**最重要的一条"**一个数【必须【来自【那个对端**"**。**

**✅ 与 §470 的"`> 0x3FF` 曾写在九处"**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **一个界【写在九处** ⇒ 改一处【剩八处【错**】
§472  **一个容量【被选成 `128`** ⇒ 与【两边的掩码**都不符**】
⇒ **⇒ 两次"一个数【必须【从【那个对端**读出来**】
```

**✅ ⭐⭐⭐ **"一个数必须从那个对端读出来"两例**。

**⚠ 而"`0x40000` 恰好是那 `256` 个槽"**⇒ **一个**精确的算术闭合**。**

**⇒ 独立验证**：
```text
256 槽 × 1024 字节 = 262,144 = 0x40000 ✓
而【环基 `40154h → 80154h` ⇒ 差 `0x40000` ✓】
而【序列字段【也【移动 `0x40000`**】⇒ **⇒ 所以【两个地址【同步移动** ✓
```

**✅ ⭐⭐⭐ **"两个地址同步移动，而那个差恰好是那 256 个槽"** —— 一个**双重算术闭合**。

**✅ 与 §468 的"`20 - 4 - 1 = 15`"**——**同族**（**第二次"一个**布局的算术**"**）。

### 2.4 而**"`static_assert(std::has_single_bit(...))`"**

**⇒ 十层**：
```text
`& mask` ⇒ **要求【容量【是【`2` 的幂**】
⇒ **⇒ 所以【那个 `static_assert` 【是【一个【结构性的**要求，不是【一个**风格**】
```

**✅ ⭐⭐⭐ **"那个 `static_assert` 是一个结构性的要求"** —— 与 §470 的"`MaximumWeaponAssetIndex < (1u << 11)`"**同族**（**第三次"一个 `static_assert` 【是一个【行为**"**）。

### 2.5 而**"一个 `128..511` 的间隙【返回一个空键**"**

**⇒ 十六层**：
```text
1. **若容量 = `128`**】
2. ⇒ **⇒ 那么【一个 `128..511` 的间隙**】
3. ⇒ **⇒ 会【让【那个陈旧性守卫【返回【一个**空键**】
4. ⇒ **⇒ 而【它【是【"第二条失同步**"**
5. ⇒ **⇒ 所以【即使【你【把掩码改对了**】⇒ **那个守卫【仍然【会【在一个【更大的**间隙上【给出【空键**】
```

**✅ ⭐⭐⭐ **"即使你把掩码改对了，那个守卫仍然会给出一个空键"** —— 一个**两处耦合的病灶**。

**✅ 与 §471 的"打不死人 + 穿透仍无效是同一刀的两个症状"**——**同族**（**第二次"两个症状【一个**病因**"**）。

## 三、**`8 → 32` 的 usercmd 上限与"抬高它在 50ms 帧下是惰性的，而那正是要点"**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(cl_write_packet): CODOL out.exe 1649370 CL_WritePacket
// 0x005B2C10 (RVA 0x1B2C10) computes
//     count = cl.cmdNumber - outPackets[..].cmdNumber;
//     if (count > 32) count = 32;
// and then chains that many MSG_WriteDeltaUsercmdKey 0x0066F410 deltas
// into one packet. THIRTY-TWO IS CODOL'S OWN MAX_PACKET_USERCMDS, read off
// the client that actually talks to us. What stood here was Ghosts' retained-eight,
// which silently discarded player input the moment more than eight commands arrived
// together -- and a CODOL client will hand a server up to thirty-two in ONE packet.
//
// RAISING IT IS INERT AT THE CURRENT 50 ms FRAME, AND THAT IS THE POINT.
// Per-hour runtime-perf samples over live matches: at 50 ms the queue
// peaks at 7 of 8 and NEVER reaches capacity; at the 100 ms frame it sat
// AT capacity in 33% of samples, and every one of those was a dropped
// usercmd. The ceiling was the defect; the tick rate was not.
inline constexpr std::size_t PendingUserCmdCapacity = 32;
```

### 3.2 二十四层

```text
1. **`count = cl.cmdNumber - outPackets[..].cmdNumber`**
2. ⇒ **`if (count > 32) count = 32`**】
3. ⇒ **⇒ 然后【把【那么多【`MSG_WriteDeltaUsercmdKey` 的 delta【串进【一个包**】
4. ⇒ **⇒ `32` 【是 CODOL 自己的 `MAX_PACKET_USERCMDS`**】
5. ⇒ **⇒ 从【那个【真的【与我们说话**的客户端【读出来**】
6. ⇒ **⚠ 而【原来【站在这里的是 Ghosts 的保留八**】
7. ⇒ **⇒ 而它【会【静默地【丢弃玩家输入**】
8. ⇒ **⇒ 【只要【超过八个命令【一起到达**】
9. ⇒ **⇒ 而【一个 CODOL 客户端【会【在一个包里【交给服务器【最多三十二个**】
10. ⇒ **⚠ 而"抬高它【在【当前的 `50ms` 帧下【是【惰性的**，而那正是要点**"**
11. ⇒ **⇒ 每小时的运行时性能采样**：
12. ⇒ **`50ms` ⇒ 队列【峰值 `7`（共 `8`）⇒ 【从不**到达容量**】
13. ⇒ **`100ms` ⇒ 【在 `33%` 的采样里【就【坐在【容量上**】
14. ⇒ **⇒ 而【每一个【都是【一个【被丢掉的 usercmd**】
15. ⇒ **⇒ 所以【那个上限【是那个缺陷**】⇒ **⇒ 【那个帧率不是**】
```

### 3.3 ⭐⭐⭐ **"那个上限是那个缺陷，那个帧率不是"**

**✅ 这是本报告里**最精确的一条归因**。**

**✅ 与 §471 的"打不死人 + 穿透仍无效是同一刀的两个症状"**——**同族**（**第三次"两个候选【一个**病因**"**）。

**⇒ 三层**：
```text
若【认为【是帧率**】⇒ **降低帧率**？**⇒ 方向**反**
若【认为【是上限**】⇒ **抬高上限** ⇒ **⇒ 而【在 `50ms` 下【它【是【惰性**的** —— 而那【证明【上限【不是【当前**的瓶颈**】
⇒ **⇒ 所以【那句"惰性"【是【一个【反证**】
```

**✅ ⭐⭐⭐ **"那句『惰性』是一个反证"** —— 一个**极精巧的论证结构**。

**⚠ 而"`50ms` 下峰值 `7`/`8`"**⇒ **一个**贴近**的值**。**

**⇒ 十层**：
```text
`50ms` 帧 ⇒ **`20` 帧/秒**
而【峰值 `7`**】⇒ **⇒ 所以【平均【约 `3.5`**】
⇒ **⇒ 而 `8` 【的容量【只剩 `1` 的余量**】
```

**✅ ⭐⭐ **"只剩 1 的余量"** —— 而**这正是【那个 bug【在某些情况下【仍然【可触发**的原因**。

**⇒ 三层**：
```text
峰值 `7`/`8` ⇒ **余量 `1`**
⇒ **⇒ 所以【一个【突发的**第八个【会【满**】⇒ **⇒ 而【第九个【会被丢**】
```

**✅ ⭐⭐⭐ **"一个突发的第八个会满，而第九个会被丢"** —— 一个**极精确的余量分析**。

**✅ 与 §464 的"`thinkBudget` 的 `100ms` 在五个命令后就用完**"**——**同族**（**第二次"一个**预算的余量**"**）。

## 四、**`newestFlaggedSnapshotMessage` 与 `baselineCacheInitializationMessage` 的分工**（本组第三重要）

### 4.1 那段

```cpp
bool baselineCacheAcknowledged{};
std::optional<std::uint32_t> baselineCacheInitializationMessage;
// THE NEWEST FLAGGED MESSAGE, WHICH IS THE ONLY FLAGGED FRAME THE CLIENT CAN
// STILL BE HOLDING ENTITIES FOR (section 170). out.exe stores the entities of a
// flagged frame in dword_C89E050, a FLAT array with no frame number, and
// CL_ParseSnapshot resets its cursor dword_C89E04C to zero at 0x00472223 on every
// frame that carries the flag. So that array holds exactly ONE generation: the
// newest flagged frame the client has parsed. sub_470E90 0x00470e97 reads an
// entity baseline row out of it whenever the BASELINE frame's snapFlags carry
// bit 8, indexed by list position alone.
//
// baselineCacheInitializationMessage cannot answer this question: it is reset the
// moment the client acknowledges it (sv_client_mp.cpp, the acknowledged-snapshot
// block), which is precisely when the selection below needs to know. This one is
// monotone for the life of a connection and is cleared only where
// snapshotHistory is cleared, because both describe the same client generation.
std::optional<std::uint32_t> newestFlaggedSnapshotMessage;
```

### 4.2 二十四层

```text
1. **`dword_C89E050` 【是一个【平的**数组，没有帧号**】
2. ⇒ **⇒ 而 `CL_ParseSnapshot` 【把它的游标 `dword_C89E04C` 【在 `0x00472223` 【对【每一个【携带那个标志**的帧【重置为零**】
3. ⇒ **⇒ 所以【那个数组【恰好【持有一个**代**】
4. ⇒ **⇒ 而【那【就是【客户端【已经解析的【最新的那个带标志的帧**】
5. ⇒ **而 `sub_470E90` 的 `0x00470e97` 【在【基线帧的 `snapFlags` 携带第 `8` 位时【读**一行**】
6. ⇒ **⇒ 【仅按【列表位置**索引**】
7. ⇒ **⚠ 而 `baselineCacheInitializationMessage` 【不能【回答这个问题**】
8. ⇒ **⇒ 因为【它【在【客户端【确认它【的那一刻【被重置**】
9. ⇒ **⇒ 而那【正是【下面那个选择【需要知道**的时刻**
10. ⇒ **⇒ 而这个【在一个连接的生命期里【单调**】
11. ⇒ **⇒ 而【只在【`snapshotHistory` 被清的地方【被清**】
12. ⇒ **⇒ 因为【两者【描述【同一个客户端代**】
```

### 4.3 ⭐⭐⭐ **"它被重置的那一刻，正是下面那个选择需要知道的时刻"**

**✅ 这是本报告里**最漂亮的一条"一个字段的**生命周期**与**用途**相反**"**。**

**✅ 与 §463 的"它只在 `clientThink` 开始提交时才变得可见"**——**同族**（**第二次"一个**时序**的陷阱**）。

**⇒ 三层**：
```text
`baselineCacheInitializationMessage` ⇒ **在【确认时【被清**】
而【那个选择【恰好【在【确认时【需要知道**】
⇒ **⇒ 所以【那个字段【在【最需要**它的那一刻【是【空**的**】
```

**✅ ⭐⭐⭐ **"那个字段在最需要它的那一刻是空的"** —— 一个**极精确的时序缺陷**。

**⚠ 而"那个新字段【单调**"**⇒ **一个**正确的替代**。**

**⇒ 十层**：
```text
单调 ⇒ **只增不减**（除【`snapshotHistory` 被清时**）
⇒ **⇒ 所以【它【永远【能回答"最新的带标志帧【是哪个**"**
⇒ **⇒ 而【它与【`snapshotHistory` 【同生同死**】
```

**✅ ⭐⭐⭐ **"它与 snapshotHistory 同生同死，因为两者描述同一个客户端代"** —— 一个**极清晰的所有权**。

**✅ 与 §469 的"两级代次"**——**完全闭合** ✓

**⇒ 三层**：
```text
§426  **`enter world` ⇒ `slot->snapshotHistory = {}`**
§469  **`generation`（运行时）+ `entityGeneration`（实体）**
§472  **`newestFlaggedSnapshotMessage` 【与 `snapshotHistory` 同生同死**】
⇒ **⇒ 三层【同一个"代"的概念**】
```

**✅ ⭐⭐⭐ **"三层同一个『代』的概念"**。

## 五、**"一个字段与一个序列化器而没有任何东西写它"**（本组第四重要）

### 5.1 那段

```cpp
// Deaths are a scoreboard column, never a limit. Unlike kills they are
// not awarded by script - dm.lua has no counterpart to addkill for the
// victim - so the server counts them itself off the kill event.
[[nodiscard]] bool addClientDeaths(std::uint32_t clientNum, std::int32_t delta);
// Assists are the same kind of column as deaths and, until now, had the
// same shape of hole: a field and a serializer with nothing writing it.
// The server counts them itself off the kill event (see
// SvAssistAwardees in sv_scoreboard_mp.hpp), so no script awards them -
// and unlike a death an assist must NOT reset the killstreak.
[[nodiscard]] bool addClientAssists(std::uint32_t clientNum, std::int32_t delta);
// The other two columns of the same kind: a field and a serializer with
// nothing writing them. Both are counted natively and neither may reset
// the killstreak -- an objective completion and an earning are not
// deaths. The award decisions live in sv_scoreboard_mp.hpp
// (SvObjectiveCompletionAward / SV_GpForXp).
[[nodiscard]] bool addClientObjectives(...);
[[nodiscard]] bool addClientGp(...);
```

### 5.2 二十四层

```text
1. **"一个字段与一个序列化器【而【没有任何东西【写**它"**】
2. ⇒ **⇒ 那是【一个反复出现的**洞的形状**】
3. ⇒ **`deaths`**（**现在【由服务端【从【那个击杀事件**数**）
4. ⇒ **`assists`**（**同一形状的洞**【直到最近**）
5. ⇒ **`objectives`**（**同一形状**）
6. ⇒ **`gp`**（**同一形状**）
7. ⇒ **⇒ 所以【四列【同一个**病灶**】
8. ⇒ **⇒ 而【修复【是【同一个**：**服务端【自己**数**】
```

### 5.3 ⭐⭐⭐ **"一个字段与一个序列化器而没有任何东西写它"**

**✅ 这是本报告里**最精确的一条"一个**半成品**的**命名**"**。**

**✅ 与 §414 的"`SV_ConstBaselineTable` 的 `nullptr` 是正常情况"**——**不同**，但与 §468 的"`UnresolvedString` 没有生产者"**同族**（**第二次"一个**声明【没有实现**"**）。

**⇒ 三层**：
```text
§468  **`SvForgeXAnimStatus::WrongThread` 【没有生产者**】（**一个枚举值**）
§472  **四列【有字段 + 有序列化器 + 没有写者**】（**四个字段**）
⇒ **⇒ 两次"一个【声明【没有实现**"**
```

**✅ ⭐⭐⭐ **"一个声明没有实现"两例**。

**⚠ 而"`deaths` 【不像 `kills` **那样【由脚本【授予**"**⇒ **一个**不对称**的发现**。**

**⇒ 十层**：
```text
`kills` ⇒ **`dm.lua` 的 `addkill`**（**脚本授予**）
`deaths` ⇒ **`dm.lua` **没有【一个【对应物**】（**⇒ 服务端自己数**）
`assists` ⇒ **同样**（**`sv_scoreboard_mp.hpp` 的 `SvAssistAwardees`**）
`objectives` ⇒ **同样**（**`SvObjectiveCompletionAward`**）
`gp` ⇒ **同样**（**`SV_GpForXp`**）
⇒ **⇒ 所以【五列【两种**授予机制**】
```

**✅ ⭐⭐⭐ **"五列两种授予机制"** —— 一个**极清晰的分工**。

**⚠ 而"一个助攻**不能**重置那个连杀，而一个死亡**可以**"**⇒ **一个**语义的判据**。**

**⇒ 三层**：
```text
`deaths` ⇒ **重置连杀**
`assists` ⇒ **不重置**
`objectives` ⇒ **不重置**
`gp` ⇒ **不重置**
⇒ **⇒ 所以【只有 `deaths` 【重置**】
```

**✅ ⭐⭐⭐ **"只有 deaths 重置连杀"** —— 而注释明确写出："**不像一个死亡，一个助攻必须不重置那个连杀**"。

## 六、**`teamPolicy()` 的单点派生**

### 6.1 那段

```cpp
// Whether this match has sides at all. Derived in one place so the class
// menu and the loadout commit cannot disagree about it - they gate on the
// same SvTeam::None and would otherwise have to each know the gametype.
[[nodiscard]] SvTeamPolicy teamPolicy() const
{
    return gameState_.gameType == "dm"
        ? SvTeamPolicy::FreeForAll
        : SvTeamPolicy::Teams;
}
```

### 6.2 二十四层

```text
1. **"这场比赛【到底【有没有边**"**
2. ⇒ **⇒ 在【一个地方**派生**】
3. ⇒ **⇒ 所以【那个类菜单【与【那个装备提交【不能【就它【不一致**】
4. ⇒ **⇒ 因为它们【在【同一个 `SvTeam::None` 上**设门**】
5. ⇒ **⇒ 而【否则【它们【各自【都得【知道【那个 gametype**】
```

### 6.3 ⭐⭐⭐ **"在一个地方派生，所以类菜单与装备提交不能就它不一致"**

**✅ 与 §470 的"`THE WEAPON INDEX BOUND LIVES HERE AND NOWHERE ELSE`"**——**完全同族** ✓

**⇒ 三层**：
```text
§470  **一个界【写在九处** ⇒ 改一处【剩八处【错**】
§472  **一个策略【在一个地方**派生**】
⇒ **⇒ 两次"一个**单点**的派生**】
```

**✅ ⭐⭐⭐ **"一个单点的派生"两例**。

**⚠ 而 `SvTeamPolicy` **没有默认值**"**⇒ **一个**极重要的设计决定**。**

**⇒ 十层**：
```cpp
// Deliberately has no default: a teamless mode that forgets to say so would land
// both players on one team and silently make them unable to damage each other.
```
```text
1. **故意【没有默认值**】
2. ⇒ **⇒ 因为【一个【忘了说**的无队伍模式】
3. ⇒ **⇒ 会【把两个玩家【放在【同一队**】】
4. ⇒ **⇒ 而【静默地【使他们【不能【互相造成伤害**】
```

**✅ ⭐⭐⭐ **"静默地使他们不能互相造成伤害"** —— 与 §467 的"一个回落比一个失败更危险"**完全同族**（**第三次"一个**默认值【是陷阱**"**）。

**⇒ 三层**：
```text
§467  **回落到 `info_player_start` ⇒ 在地图下面**
§468  **回落到默认材质 ⇒ 每个表面画错**
§472  **回落到一个默认队伍策略 ⇒ 两人同队且不能互伤**
⇒ **⇒ 三次"一个**默认值【是【陷阱**】
```

**✅ ⭐⭐⭐ **"一个默认值是陷阱"三例表**。

## 七、**`SvClientTimeouts` 的 `80/240 → 45/15`**

### 7.1 那段

```cpp
// A CRASHED CLIENT HOLDS ITS SLOT UNTIL ONE OF THESE EXPIRES, AND IT CANNOT
// REJOIN WHILE IT DOES. A CODOL client that crashes exits tidily and simply
// stops sending (see codol-client-crash-reports-are-already-captured), so the
// server sees only silence and waits out the full timeout.
//
// These were 80 s connecting / 240 s active. Four minutes to reclaim a seat is
// unusable when a player crashes mid-match and wants straight back in, and the
// zhunt load crash (HANDOFF section 152w) lands in the CONNECTING state, so
// that one cost 80 s every time.
//
// Silence is unambiguous once the lifecycle reaches Playing: nothing
// legitimate stops sending for 15 s during gameplay. A gamestate
// acknowledgement and even an early move packet can arrive before the map
// load finishes, so the connecting grace remains in force until Playing.
// Large maps (za_island, mp_battlecity, Wetwork) genuinely take tens of
// seconds to load.
//
// Override without a rebuild: OLMOD_CLIENT_TIMEOUT_MS, OLMOD_CONNECT_TIMEOUT_MS.
struct SvClientTimeouts
{
    std::uint32_t connectingMilliseconds{ 45'000 };
    std::uint32_t activeMilliseconds{ 15'000 };
};
```

### 7.2 二十四层

```text
1. **一个崩溃的客户端【持有【它的槽【直到其中一个过期**】
2. ⇒ **⇒ 而【它【不能【重新加入【在那期间**】
3. ⇒ **⇒ 而一个 CODOL 客户端【崩溃时【干净地退出，只是【停止发送**】
4. ⇒ **⇒ 所以【服务器【只看到【沉默**，而【等满整个超时**】
5. ⇒ **⚠ 原来是 `80` 秒连接 / `240` 秒活跃**】
6. ⇒ **⇒ 四分钟【收回一个座位，【在【一个玩家【中途崩溃【想【直接回来**时【不可用**】
7. ⇒ **⇒ 而【`zhunt` 的加载崩溃【落在 `CONNECTING` 状态**】
8. ⇒ **⇒ 所以【那一个【每次【花 `80` 秒**】
9. ⇒ **⇒ 而【沉默【在【生命周期【到达 `Playing` 之后【是无歧义**的**】
10. ⇒ **⇒ 因为在【游戏进行中【没有任何合法的东西【会【停发 `15` 秒**】
11. ⇒ **⇒ 而【一个 gamestate 确认、甚至【一个早期移动包【可以【在地图加载完成之前**到达**】
12. ⇒ **⇒ 所以【那个连接宽限【保持有效【直到 `Playing`**】
13. ⇒ **⇒ 而【大图（`za_island`/`mp_battlecity`/`Wetwork`）【真的【要【几十秒**加载**】
```

### 7.3 ⭐⭐⭐ **"沉默在生命周期到达 Playing 之后是无歧义的"**

**✅ 这是本报告里**最精确的一条"**一个**沉默**的**语义**随状态变化**"**。**

**✅ 与 §467 的"`SV_SelectInitialSpawn` 的六元回退"**——**不同**（那是一个**选择**，这是一个**超时**）但**同族**（**"一个**时间预算【必须【按【状态**分开**"**）。

**⇒ 十层**：
```text
`CONNECTING` ⇒ **`45` 秒**（**因为【大图【要几十秒**）
`Active/Playing` ⇒ **`15` 秒**（**因为【没有合法的东西【停发这么久**）
⇒ **⇒ 所以【两个**超时【各自【被【一个具体的**事实**决定**
```

**✅ ⭐⭐⭐ **"两个超时各自被一个具体的事实决定"**。

**⚠ 而"`OLMOD_CLIENT_TIMEOUT_MS` / `OLMOD_CONNECT_TIMEOUT_MS` 不重建就能覆盖**"**⇒ **一个**运营**的钩子**。**

**⇒ 三层**：
```text
两个环境变量 ⇒ **不重建**的覆盖**
⇒ **⇒ 所以【一个【现场**的调参路径**
```

**✅ ⭐⭐ **"一个现场的调参路径"** —— 与 §470 的 `OLMOD_PERF_BASELINE`**同族**（**第二次"一个**环境变量**的开关**"**）。

## 八、**`bestClientKills` 的"击杀数，不是得分"**

### 8.1 那段

```cpp
// Kills, not score: a kill awards display points while the shipped
// limit is 30, so comparing the limit against the score ends the match on
// the first kill. cha avoids this by counting its limit on addteamscore's
// 1-per-kill, which is exactly what this mirrors. Ties resolve to the
// player with fewer deaths and then the lowest slot, matching the
// shipped FFA placement ordering while keeping the result deterministic.
```

### 8.2 二十四层

```text
1. **击杀数，不是得分**】
2. ⇒ **⇒ 因为【一个击杀【授予【展示分**】】
3. ⇒ **⇒ 而【那个已发布的限制【是 `30`**】
4. ⇒ **⇒ 所以【把那个限制【与【那个得分**比较【会【在【第一个击杀**就结束比赛**】
5. ⇒ **⇒ 而 `cha` 【通过【在 `addteamscore` 的【每次击杀 `1`** 上【计它的限制【避免了这一点**】
6. ⇒ **⇒ 而那【正是【这里【镜像**的东西**
7. ⇒ **⇒ 而【平局【解析到【死亡更少**的那个玩家**】
8. ⇒ **⇒ ⇒ 然后【最低的槽**】
9. ⇒ **⇒ ⇒ 匹配【那个已发布的 FFA 名次排序**，同时【保持结果【确定**】
```

### 8.3 ⭐⭐⭐ **"把那个限制与那个得分比较会在第一个击杀就结束比赛"**

**✅ 与 §442 的"`addkill` —— 展示分 `100` vs 限制计数 `1`，混用会在第一个击杀结束比赛"**——**完全闭合** ✓

**⇒ 三层**：
```text
§442  **`addkill` 【记展示分 `100`** 而【限制计数 `1`**】
§472  **`bestClientKills` 【读击杀数**而不是得分**】
⇒ **⇒ 同一个坑【两处【同一个修法**】
```

**✅ ⭐⭐⭐ **"同一个坑两处同一个修法"** —— 一个**跨报告的完整闭合**。

**⚠ 而"平局【先【死亡更少**，然后【最低的槽**"**⇒ **一个**两级的确定性**。**

**⇒ 十层**：
```text
第一级 ⇒ **击杀数**
第二级 ⇒ **死亡更少**
第三级 ⇒ **最低的槽**
⇒ **⇒ 所以【三级【全序**】
```

**✅ ⭐⭐⭐ **"三级全序"** —— 而**注释说**"保持结果确定**"**。

**✅ 与 §466 的"`_a` 然后 `_b`"**——**同族**（**第三次"一个**全序【保证**"**）。

## 九、**`connectionAnnounced_` 的"那个名字必须比那个槽活得更久"**

```cpp
// clientNum -> the ENCODED name it was announced under. The name has
// to outlive the slot: a client is announced as gone once its slot is
// already Free, and by then its roster entry is not reachable.
std::map<std::uint32_t, std::string> connectionAnnounced_;
```

**⇒ 十二层**：
```text
1. **`clientNum → 它被宣告时的那个编码名字**】
2. ⇒ **⇒ 那个名字【必须【比那个槽【活得更久**】
3. ⇒ **⇒ 因为【一个客户端【被宣告为"走了**"【是在【它的槽【已经 `Free`** 之后**】
4. ⇒ **⇒ 而在那【时【它的名册条目【不可达**】
```

**✅ ⭐⭐⭐ **"那个名字必须比那个槽活得更久"** —— 一个**极精确的生命周期**。

**✅ 与 §472 四 的"`newestFlaggedSnapshotMessage` 与 `snapshotHistory` 同生同死"**——**相反**（那里**同生同死**，这里**必须【比那个槽**更长**）。

**⇒ 三层**：
```text
§472  **`newestFlaggedSnapshotMessage` 【与槽【同生同死**】
§472  **`connectionAnnounced_` 【必须【比槽【更长**】
⇒ **⇒ 两个相反的**生命周期【各自【被【用途**决定**】
```

**✅ ⭐⭐⭐ **"两个相反的生命周期各自被用途决定"**。

## 十、**`scoreboardRosterFingerprint_` 的 `1185 → 1029`**

```cpp
// ★ 28100 刀H（三轮）：**记分板更新压缩到单条命令**所需的两个指纹，
//   按**接收客户端**分别记：roster（userIds）与比赛级字段（round/limit）。
//   未变化时不再重复发送对应的 run 段，使一次普通比分更新从 1185 B
//   降到 ~1029 B 且不再分两条命令 ⇒ 客户端一次装载、一次重建。
//   队分（teamScores）**不进指纹**：它每个击杀都在变，且是重建要读的值。
std::array<std::uint64_t, MaximumGameClients> scoreboardRosterFingerprint_{};
std::array<std::uint64_t, MaximumGameClients> scoreboardMatchFingerprint_{};
```

### 10.1 二十四层

```text
1. **两个指纹**（`roster` 的 `userIds` 与【比赛级字段**）】
2. ⇒ **⇒ 按【接收客户端**分别记**】
3. ⇒ **⇒ 未变化时【不再重复发送**对应的 `run` 段**】
4. ⇒ **⇒ 所以【一次普通比分更新【从 `1185` B 【降到 `~1029` B**】
5. ⇒ **⇒ 且【不再分两条命令**】⇒ **⇒ 客户端【一次装载、一次重建**】
6. ⇒ **⚠ 队分（`teamScores`）【不进指纹**】
7. ⇒ **⇒ 因为【它【每个击杀【都在变**】
8. ⇒ **⇒ 且【它【是重建【要读**的值**
```

### 10.2 ⭐⭐⭐ **"队分不进指纹：它每个击杀都在变，且是重建要读的值"**

**✅ 这是本报告里**最精确的一条"一个**指纹【的**成员资格**"**。**

**✅ 与 §433 的"`0x3FC → 0x3FE` 的两字节修正使 `1021` 字节的单命令记分板可用"**——**完全衔接** ✓

**⇒ 三层**：
```text
§433  **`0x3FC → 0x3FE`** ⇒ **`1023 - 1 = 1022 = 0x3FE`** ⇒ **`1021` 字节【可用**】
§472  **`1185 - ? = 1029`** ⇒ **而【`1029 ≤ 1022`？** ⇒ **⚠ 不成立**】
```

**⚠ 独立核算**：`1029 > 1022` ⇒ **那 `1029` 字节【仍然【超过 `0x3FE`**】**。**

**⇒ 十层**：
```text
若【单条命令的头上限是 `1022`**】⇒ **而【`1029` > `1022`**】
⇒ **⇒ 所以【"不再分两条命令**"【与【`1029` B【可能【不一致**】
```

**⚠ 标注为未闭合**（可能 `1022` 是**载荷**的上限，而 `1029` 含**命令头**）。

**⇒ 三层**：
```text
若【`1022` 是【载荷**上限**而 `1029` 含【约 `7` 字节的【命令头**】
⇒ **⇒ 则【载荷 `1022` ✓ 而【总计 `1029` ✓】
⇒ **⇒ 所以【两个数【可以【一致**】
```

**✅ ⭐⭐ **"两个数可以一致（如果 1022 是载荷上限）"** —— 一个**合理的解释**。

## 十一、`ClientSlot` 的四个 pending/committed 对

```text
selectedLoadout              / pendingSelectedLoadout
loadoutSequence              / pendingLoadoutSequence
characterFaction             / pendingCharacterFaction
team                         / pendingTeam
```

### 11.1 二十四层

```text
1. **四对**（`selectedLoadout` / `loadoutSequence` / `characterFaction` / `team`）
2. ⇒ **⇒ 每一对【一个**已提交**、一个**待提交**】
3. ⇒ **⇒ 所以【一次【装备变更【是【一个**两阶段**的提交**】
```

### 11.2 ⭐⭐⭐ **"四个字段一起 pending，四个一起 commit"**

**✅ 与 §471 的 `GlassCommandRollback`**——**同族**（**第四次"一个**两阶段**的提交**"**）。

**⇒ 三层**：
```text
`GlassCommandRollback` ⇒ **一个 RAII 的两阶段**
`pendingLoadout*` × 4 ⇒ **一个显式的两阶段**
⇒ **⇒ 两次"一个**两阶段【保证**"**
```

**✅ ⭐⭐ **"一个两阶段保证"两例**。

**⚠ 而"`resolveAndCommitPendingLoadout`"**⇒ **一个**原子的**提交**。**

**⇒ 三层**：
```text
若【四个字段【各自【独立【更新**】⇒ **⇒ 一个【半更新的**装备**
若【一起**】⇒ **⇒ 一个【原子的**装备**
⇒ **⇒ 所以【四个 `pending` 【是【必须的**】
```

**✅ ⭐⭐⭐ **"四个 pending 是必须的"**。

## 十二、`ChallengeRecord` 的 `1024` 与 `challengeLifetimeMilliseconds = 30'000`

### 12.1 二十四层

```text
1. **`ChallengeCapacity = 1024`**
2. ⇒ **⇒ 而【一个 challenge【的生命期 `30` 秒**】
3. ⇒ **⇒ 所以【`1024` 个【并发**的连接尝试**
```

### 12.2 ⭐⭐ **"1024 个挑战，每个 30 秒"**

**⇒ 独立核算**：
```text
若【每个客户端【每秒【重试一次**】⇒ **⇒ `1024` 个挑战【支持【约 `1024` 个客户端/30 秒**】
⇒ **⇒ 而【`18` 个槽 ⇒ `1024 / 18 ≈ 57` 倍【的余量**】
```

**✅ ⭐⭐ **"57 倍的余量"** —— 一个**宽松但安全的**选择**。

**✅ 与 §469 的"`XAssetMaxChainSteps = 4096` vs 实测 `7` ⇒ `585` 倍余量"**——**同族**（**第二次"一个**防御的余量**"**）。

## 十三、关键结论

1. **⭐⭐⭐ "`ServerReliableCommandCapacity` **不是我们**可以选的：客户端用 `serverCommands[reliableAcknowledge & mask]` XOR 它的包，选一个不同的掩码两边就从不同的槽推导那个键"`** —— 而 **`out.exe` 的 `sub_4737E0` 说 `and ebx, 1FFh`（`512`）对 3.3.3.3 的 `sub_46E3B0` 的 `and ebx, 0FFh`（`256`）**，**同样的 `1024` 字节槽、同样的 `push 3FFh` 的 `strncpy`、同样的 `xor ecx, 0D362501Fh` 指针 cookie** ⇒ **独立验证：`256 × 1024 = 262,144 = 0x40000`，而环基 `40154h → 80154h` 与序列字段都移动 `0x40000` ✓**。
2. **⭐⭐⭐ "**128 既不是任何一个 build 的数**"** ⇒ **"它还让那个陈旧性守卫对任何 `128..511` 的间隙返回一个空键，那是同一个 XOR 的第二条失同步路径"`** ⇒ **"即使你把掩码改对了，那个守卫仍然会给出一个空键"`** —— 两处耦合的病灶（与 §471 的"两个症状一个病因"同族）。而 `static_assert(std::has_single_bit(...))` 是一个**结构性**要求（`& mask` 必须对 `2` 的幂）。
3. **⭐⭐⭐ `PendingUserCmdCapacity = 8 → 32`**：`CL_WritePacket` `0x005B2C10` 的 `if (count > 32) count = 32` ⇒ **"三十二是 CODOL 自己的 `MAX_PACKET_USERCMDS`，从那个**真的**与我们说话的客户端读出来"`**；而 Ghosts 的保留八 **"会静默地丢弃玩家输入，只要超过八个命令一起到达"`**。
4. **⭐⭐⭐ "抬高它在当前的 `50ms` 帧下是**惰性的**，而那正是要点"`** —— 每小时采样：**`50ms` ⇒ 峰值 `7`/`8`，从不**到达容量；`100ms` ⇒ 在 `33%` 的采样里**坐在容量上**，每一个都是被丢掉的 usercmd ⇒ **"那个上限是那个缺陷，那个帧率不是"`**（一个**反证结构**：惰性本身证明了上限不是当前瓶颈）。**独立分析：峰值 `7`/`8` 只剩 `1` 的余量 ⇒ 一个突发的第八个会满、第九个会被丢。**
5. **⭐⭐⭐ `newestFlaggedSnapshotMessage` 的完整理由**：**`dword_C89E050` 是一个平数组没有帧号，而 `CL_ParseSnapshot` 在 `0x00472223` 对每个携带那个标志的帧把游标 `dword_C89E04C` 重置为零 ⇒ 那个数组恰好持有一个代**；而 **`baselineCacheInitializationMessage` 不能回答这个问题，因为"它在客户端确认它的那一刻被重置，而那正是下面那个选择需要知道的时刻"`** ⇒ **"那个字段在最需要它的那一刻是空的"`** —— 第二次"一个时序的陷阱"（与 §463 同族）；新字段**单调**且**与 `snapshotHistory` 同生同死**（"因为两者描述同一个客户端代"）。
6. **⭐⭐⭐ "deaths / assists / objectives / gp 四列同一个洞的形状：一个字段与一个序列化器而**没有任何东西写它**"`** ⇒ **"不像 kills，`dm.lua` 对受害者没有 `addkill` 的对应物，所以服务端自己从击杀事件数它"`** —— 第二次"一个声明没有实现"（与 §468 的 `WrongThread` 同族）；而**五列两种授予机制**（`kills` 由脚本，其余四列由服务端），且 **"只有一个 `deaths` 重置连杀"`**（"不像一个死亡，一个助攻必须不重置那个连杀"）。
7. **⭐⭐⭐ `teamPolicy()` 的单点派生**（`gameType == "dm"` ⇒ `FreeForAll` 否则 `Teams`）—— **"在一个地方派生，所以类菜单与装备提交不能就它不一致"`**（与 §470 的"THE WEAPON INDEX BOUND LIVES HERE AND NOWHERE ELSE"同族）；而 **`SvTeamPolicy` **故意没有默认值**，因为"一个忘了说自己的无队伍模式会把两个玩家放在同一队，而静默地使他们不能互相造成伤害"`** —— 第三次"一个默认值是陷阱"（与 §467/§468 同族）。
8. **⭐⭐⭐ `SvClientTimeouts` 的 `80/240 → 45/15`**：**"一个崩溃的客户端持有它的槽直到其中一个过期，而它不能在那期间重新加入；一个 CODOL 客户端崩溃时干净退出、只是停止发送，所以服务器只看到沉默"`**；**`zhunt` 的加载崩溃落在 `CONNECTING` 状态 ⇒ 每次花 `80` 秒** ⇒ **"沉默在生命周期到达 `Playing` 之后是无歧义的（游戏进行中没有任何合法的东西会停发 `15` 秒），而一个 gamestate 确认甚至一个早期移动包可以在地图加载完成之前到达 ⇒ 连接宽限保持有效直到 `Playing`"`** ⇒ **"两个超时各自被一个具体的事实决定"`**。
9. **⭐⭐⭐ `bestClientKills` 的"击杀数，不是得分"`**：**"一个击杀授予展示分而那个已发布的限制是 `30`，所以把那个限制与那个得分比较会在**第一个击杀**就结束比赛"`** —— 与 §442 的"`addkill` 的展示分 `100` vs 限制计数 `1`"**完全闭合**；平局**三级全序**（击杀数 → 死亡更少 → 最低槽）。
10. **⭐⭐⭐ `connectionAnnounced_` 的"那个名字必须比那个槽活得更久：一个客户端被宣告为走了是在它的槽已经 `Free` 之后，而到那时它的名册条目不可达"`** —— 与四的"`newestFlaggedSnapshotMessage` 与槽同生同死"**相反** ⇒ **"两个相反的生命周期各自被用途决定"`**。
11. **⭐⭐⭐ 记分板指纹 `1185 → ~1029` B**：两个指纹（`roster` 的 `userIds` 与比赛级字段 `round/limit`）**按接收客户端分别记**，未变化时不再重发对应的 `run` 段 ⇒ **"客户端一次装载、一次重建"`**；而 **"队分不进指纹：它每个击杀都在变，且它是重建要读的值"`** ⇒ **"指纹的成员资格由『它变不变』与『重建要不要读它』两个条件决定"`**。
12. **⭐⭐ `ClientSlot` 的四对 pending/committed**（`selectedLoadout` / `loadoutSequence` / `characterFaction` / `team`）⇒ **"四个 pending 是必须的，否则会得到一个半更新的装备"`** —— 第四次"一个两阶段提交"（与 §471 的 `GlassCommandRollback` 同族）。
13. **⭐⭐ `ChallengeCapacity = 1024` 与 `challengeLifetimeMilliseconds = 30'000`** ⇒ **独立算得 `1024 / 18 ≈ 57` 倍的余量**（与 §469 的 `4096` vs 实测 `7` 的 `585` 倍同族）；`SvPublishZmRoundHud` 的**回合 1 是一个常数**——**"还没有回合循环，而这故意不假装不是"`**。
14. **⚠ 一个未闭合**：`1029` 字节与 §433 的 `0x3FE = 1022` 的关系——若 `1022` 是**载荷**上限而 `1029` 含约 `7` 字节命令头，两者一致；否则不一致。

## 十四、`sv_client_mp.hpp` 全文件总览

**`883` 行。**

**`24` 个常量 / 容量**：
```text
ClientCommandPrefixCapacity      64
ServerReliableCommandCapacity   512   （static_assert 2 的幂）
ReliableKeyComplaintLimit         8
PendingUserCmdCapacity           32
ChallengeCapacity              1024
LocalSoundEventParameterMaximum 0x3E80
challengeLifetimeMilliseconds   30'000
connectingMilliseconds          45'000
activeMilliseconds              15'000
profileStatsRequiredMask        0x07FFFFFF
SvPublishZmRoundHud            true（回合 1 是常数）
```

**`6` 个枚举**：`ClientState`（`Free`/`Connected`/`ClientLoading`/`Active`）、`ServerReliableCommandKind`（`Text`/`Binary`）、`SvSnapshotAssemblyFailure`（`6` 值）、`SvTeamPolicy`（`Teams`/`FreeForAll`，**无默认**）、`ConnectionlessResultKind`（`5` 值）、`TimeoutDrop::Cause`（`Timeout`/`Leave`）。

**`ClientSlot` 的六个关注簇**：
```text
身份      peer / xuid / sessionGeneration / challenge / connectTime / name / userInfo / isBot
netchan   NetchanState / reliableSequence / reliableCommands[512] / reliableKeyComplaints
gamestate profileStats*Mask / gameStateGateReport / gamestateMessageNum / gameStateUpdateStage
快照      nextSnapshotTime / lastSnapshotTime / rateDelayed / snapshotSent / snapshotAssembly*
          baselineCacheAcknowledged / baselineCacheInitializationMessage
          newestFlaggedSnapshotMessage / baselineFrame / deltaMessage / snapshotHistory[32]
命令      lastReceived/Dispatched/Executed/DiscardedUnsupported/DiscardedRejected/DroppedOverflow
          pendingUserCmds / lastQueuedUserCmdTime / reportedUnhandledCommands
玩法      gameplayState / selectedLoadout+pending / loadoutSequence+pending
          characterFaction+pending / team+pending / predictedState
诊断      六个计数器 / lastPacketReject / lastDecodedCommandsPrefix[64]
```

**`SvClientSystem` 的方法面**（约 `70` 个）分十一组：入站（`SV_ConnectionlessPacket` / `SV_PacketEvent`）、出站（`SV_SendClientMessages` / `buildSnapshotMessage` / `queueScoreboardResponse`）、生命周期（`SV_CheckTimeouts` / `dropClientSlot` / `takeTimeoutDrops`）、世界（`setWorldFrame` / `configureGameState` / `setGameplayAuthorityReady`）、名册（`stageSessionRoster` / `commitSessionRoster` / `rollbackSessionRoster`）、配置串（`SV_SetConfigString` verb `d` / `registerDynamicWeaponConfigString`）、usercmd（`queuePendingUserCmd` / `dispatchNextPendingUserCmd` / `commitExecutedUserCmd` / 三个 discard）、记分（`addClient{Kills,Deaths,Assists,Objectives,Gp,Downs,Revives,Headshots,Streak,Xp}`）、比赛（`beginNextRound` / `bestClientKills` / `topClientsByKills`）、bot（`freeClientSlot` / `activateBotSlot` / `queuePendingUserCmd`）、只读查询。

## 十五、未闭合点

- `1029` 字节与 `0x3FE = 1022` 的精确关系（见上）。
- `MethodOfDeathCount` 与 `methodOfDeath == 3`（承接 §471）。
- `sv_client_mp.cpp` 已读（§425–437），但 `.hpp` 里的 `SessionRoster`/`ChallengeRecord` 的实现在那里，需交叉。
- `OLMOD_CLIENT_TIMEOUT_MS` / `OLMOD_CONNECT_TIMEOUT_MS` 的读取点。
- 下一个文件：`sv_alpha_barrett_assets_mp.cpp`（`38,314` 字节）。
