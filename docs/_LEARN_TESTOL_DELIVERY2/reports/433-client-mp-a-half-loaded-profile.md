# 433 · **"客户端每装载一条就重建一次，UI 在重建时读到半装载的 profile"** —— `0x3FC` 的 `1185 B` 分成两条、`J` 只在最后一条、以及"已连接但未收到 gamestate 的客户端才可以移动"

## 一、范围

本报告学习 `sv_client_mp.cpp` 2810–3150 行（`queueScoreboardResponse` 的 `1185 B` 问题、`reset`、`stageSessionRoster` 的座位重定位、`commitSessionRoster` 的开头）。

## 二、**"一次装载一次重建"**（本组最重要的一段）

### 2.1 那段

```php
// ★ 28100 刀H（三轮）：**把一次更新压进单条命令**。
//   12 行完整更新 = 1185 B > SvProfilePatchMaximumPayload(0x3FC) ⇒ 分两条。
//   票 22310 让每条命令都带 'J'（装载+重建）⇒ 客户端每装载一条就重建一次，
//   UI 在重建时读到半装载的 profile（客户端 `myTeam` 恒 0 ⇒ 敌我显示错乱，
//   甲方实测"无改善"）。老外的参考实现与我们的 hpp 契约都只在最后一条写 'J'。
//   这里在 roster / 比赛级字段**未变化时不重复发送身份段与 round/limit**
//   （12×13 B + 8 B = 164 B），使常规比分更新落进单条命令 ⇒ 一次装载一次重建。
```

### 2.2 二十四层

```text
1. **把一次更新压进【单条命令**】**
2. ⇒ **`12` 行完整更新 = `1185 B` > `SvProfilePatchMaximumPayload`（`0x3FC`）**
3. ⇒ **⇒ 所以【分两条**】**
4. ⇒ **而票 `22310` 让【每条命令都带 `'J'`**】（**装载 + 重建**）**
5. ⇒ **⇒ 客户端【每装载一条就重建一次**】**
6. ⇒ **⇒ **UI 在重建时读到【半装载的 profile**】**
7. ⇒ **⇒ 而客户端 `myTeam` 【恒 `0`**】**
8. ⇒ **⇒ 所以【敌我显示错乱**】**
9. ⇒ **⇒ 甲方实测"无改善"**】
10. ⇒ **老外的参考实现与我们的 `hpp` 契约【都只在最后一条写 `'J'`**】**
11. ⇒ **⇒ 所以【在 roster / 比赛级字段【未变化**】时不重复发送**
12. ⇒ **（身份段 `12 × 13 B` + `round`/`limit` `8 B` = `164 B`）**
13. ⇒ **⇒ 使常规比分更新落进【单条命令**】**
14. ⇒ **⇒ 所以【一次装载一次重建**】**
```

### 2.3 ⭐⭐⭐ **"客户端每装载一条就重建一次，UI 在重建时读到半装载的 profile"**

**✅ 这是本报告里**最重要的一条"多包的一致性"**。**

**⇒ 三层**：
```text
若 `J` 只在最后一条 ⇒ **中间条不重建** ⇒ **UI 看不到半装载**
若每条都带 `J` ⇒ **每装一条重建** ⇒ **读到半装载**
⇒ **⇒ 所以【`J` 的位置【决定一致性**】**
```

**✅ 与 §429 的"一个节内局部空基准"**同族（**第三次"部分 vs 整体**）。

**⇒ 三层**：
```text
§427  **一节用空基准而其余用真实基准** ⇒ 不可声明
§432  **四个 dvar 在过渡帧发出** ⇒ 失同步
§433  **每条都 `J`** ⇒ 半装载
⇒ **⇒ 三次"部分更新**】
```

**✅ ⭐⭐⭐ **一个"部分更新"的三例表**。

**⚠ 而"`myTeam` 恒 `0`"⇒ **一个具体的症状**。**

**⇒ 三层**：
```text
`myTeam` 从 record row `+0x10` 读（§433 的 `.team` 字段）
而【半装载 ⇒ 那个字段还是零】
⇒ **⇒ 所以 `myTeam = 0`** ⇒ **敌我显示错乱**
```

**✅ ⭐⭐ **"一个半装载的字段读作零 ⇒ 一个具体的显示错乱"** —— 一个完整的因果链。

### 2.4 而**"`12 × 13 B + 8 B = 164 B`"**

**⇒ 让我核对**：

```text
12 行 × 13 B = 156 B
round（4）+ limit（4）= 8 B
⇒ 156 + 8 = 164 B ✓
```

**✅ 算术闭合**。

**⚠ 而"为什么是 `13 B`/行"⇒ **identity run 的每条记录**（`userId` 变长？）。**

**⇒ 三层**：
```text
`12` 行（`SvScoreboardRowCount`）
`13 B`/行的【身份段**】
⇒ **⇒ 所以【身份段是一个固定 `13 B` 的记录**】
```

**✅ 而"`1185 - 164 = 1021 B`"⇒ **比分段 `1021 B` ≤ `1022`（`0x3FE`）** ✓

**⇒ 三层**：
```text
完整 `1185 B`
减身份段 `164 B` ⇒ **`1021 B`**
而 `0x3FE = 1022`
⇒ **⇒ 所以 `1021 <= 1022`** ✓ **落进单条**
```

**✅ ⭐⭐⭐ **一个"刚好落进"的算术**（`1021` vs `1022`，**只差 `1` 字节**）。

**⚠ 一个**极紧的边界**（**加一个字节就会再分成两条**）。

**✅ 与 §431 的"`0x3FC` vs `0x3FE` 的两字节差"**完全闭合 ✓

**⇒ 三层**：
```text
§431  **`0x3FC`（旧）→ `0x3FE`（真实界）**
§433  **`1021 B` 恰好落进 `1022`**
⇒ **⇒ 所以【§431 的那个修正是【这个优化成立的前提**】】**
```

**✅ ⭐⭐⭐ **一个"一个修正使另一个优化成为可能"的因果链**。

**⇒ 三层**：
```text
若界还是 `0x3FC = 1020` ⇒ **`1021 > 1020`** ⇒ **仍分两条**
若界是 `0x3FE = 1022` ⇒ **`1021 <= 1022`** ⇒ **单条** ✓
⇒ **⇒ 所以【§431 的两字节修正【正是**】§433 的优化得以成立的条件**】
```

**✅ ⭐⭐⭐ **"一个两字节的修正使一个优化成立"** —— 本报告最漂亮的发现。

### 2.5 而**两个指纹**

```cpp
std::uint64_t rosterFingerprint = 1469598103934665603ull;
for (const auto &entry : entries) {
    rosterFingerprint = fingerprintStep(rosterFingerprint, entry.userId);
    rosterFingerprint = fingerprintStep(rosterFingerprint, entry.clientNum << 56);
}
std::uint64_t matchFingerprint = 1469598103934665603ull;
matchFingerprint = fingerprintStep(matchFingerprint, match.roundNumber);
matchFingerprint = fingerprintStep(matchFingerprint, match.scoreLimit);
```

**⇒ 十二层**：
```text
1. **两个指纹**：`roster` 与 `match`**
2. ⇒ **初始值 `1469598103934665603` = FNV-1a 的 offset basis**
3. ⇒ **`fingerprintStep` = `(hash ^ value) * 1099511628211`** ⇒ **FNV-1a 的 prime**
4. ⇒ **`roster` 指纹 = `userId` + `clientNum << 56`**
5. ⇒ **`match` 指纹 = `roundNumber` + `scoreLimit`**
6. ⇒ **⇒ 所以【两个独立的指纹**分别跟踪"谁在"与"比赛级设置"
```

**✅ 与 §425 的 `mix32`（`lowbias32`）**不同（这是 **FNV-1a**）。

**⇒ 三层**：
```text
§425  `mix32` = **`lowbias32`**
§433  `fingerprintStep` = **FNV-1a**
⇒ **⇒ 两个不同的哈希算法，两个不同的用途**
```

**✅ ⭐ **一个"两个哈希"的对照**。

**⚠ 而"`clientNum << 56`"⇒ **把 `clientNum` 推到高字节**。**

**⇒ 三层**：
```text
`clientNum`（`0..17`）⇒ **低 5 位**
`<< 56` ⇒ **高 8 位**
⇒ **⇒ 所以【只动高字节，避免与 `userId` 混淆**】
```

**✅ ⭐⭐ **一个"位移隔离"的实例**。

### 2.6 而**"`pendingCount + commands.size() > capacity` ⇒ `skipped_capacity`"**

**⇒ 八层**：
```text
1. **先检查【四个 `commands` 是否都排得下**】**
2. ⇒ **任何一个排不下 ⇒ 【全部不排**】**
3. ⇒ **⇒ 所以【一个全或无**】**
4. ⇒ **`trace("skipped_capacity", ...)` ⇒ 一个有名字的结果**
```

**✅ 与 §430 的"`setPlayerNameString` 的全或无"**完全同族（**第六次"事务性**）。

**⇒ 三层**：
```text
§409  `advanceSdRound` 的四个 candidate
§422  `purchaseMapTargetGroup`
§430  `setPlayerNameString`
§433  **`queueScoreboardResponse` 的 `pendingCount + size > capacity`**
⇒ **⇒ 四次"全或无"**
```

**✅ ⭐⭐ **一个"全或无"的四例表**。

**⚠ 而"`trace` 的 `outcome`"⇒ **四个值**：`client_free` / `skipped_capacity` / `queued` / （`SV_ScoreboardTraceLine` 里可能还有）。

**⇒ 三层**：
```text
`client_free`
`skipped_capacity`
`queued`
⇒ **⇒ 三个明确的结局**
```

**✅ ⭐ **一个"三个结局"的枚举**。</br>

**✅ 与 §425 的"`trace-budget-exhausted`"**配合。

## 三、**`J` 是装载 + 重建**（本组第二重要）

### 3.1 那段（2891–2902）

```php
// OLMOD(scoreboard-response): CODOL's removed dedicated producer is
// unavailable. This source producer is constrained by the retained
// client chain CL_ParseServerMessage 0x0046E6A0 -> sub_46E470 ->
// sub_57E330 -> sub_57BF70 -> CG_InitScoreboardFromProfile 0x0057B760.
//
// CODDIFF(scoreboard-response): this used to send C/D/E, which set the
// two team scores and one row's score and nothing else - so kills,
// deaths and assists had no producer and their columns never moved. The
// reason no command produces them is that no command can: 0x0057B760
// rebuilds every row out of the mp/playerdata.def profile blob, and the
// blob is written by the 'J' patch stream. C/D/E are gone because the
// rebuild sets the team scores and the score column too.
```

### 3.2 二十层

```text
1. **客户端链**：`CL_ParseServerMessage`（`0x0046E6A0`）→ `sub_46E470`
   → `sub_57E330` → `sub_57BF70` → `CG_InitScoreboardFromProfile`（`0x0057B760`）
2. ⇒ **⚠ 这【曾经发 `C`/`D`/`E`**】**
3. ⇒ **它们设置了两个队伍分与一行的 score 而【别的什么也没有**】**
4. ⇒ **⇒ 所以【击杀、死亡与助攻【没有生产者**而它们的列【从不移动**】】**
5. ⇒ **⚠ 而"没有命令产生它们"的理由【是【没有命令能**】】**
6. ⇒ **`0x0057B760` 【从 `mp/playerdata.def` 的 profile blob【重建每一行**】】**
7. ⇒ **⇒ 而那个 blob 是【被 `'J'` patch 流【写的**】】**
8. ⇒ **⇒ 所以 `C`/`D`/`E`【走了**】**
9. ⇒ **因为【重建【也设置**】队伍分与 score 列**
```

### 3.3 ⭐⭐⭐ **"没有命令产生它们，因为【没有命令能】"**

**✅ 这是本报告里**最重要的一次"为什么一个命令必须被替换而不是补充"**。**

**⇒ 三层**：
```text
朴素方案：**加一条命令设置 kills**
真相：**客户端【每次重建都从 blob 重读全部**】 ⇒ **一条命令设置的会被下一次重建抹掉**
⇒ **⇒ 所以【唯一可行的路是【改 blob**】（`J` patch 流）**
```

**✅ 与 §408 的"`_tp` 只在 `DB_FindXAssetHeader` 成功时写"**不同（这是**一个"唯一可行路"的论证**）。

**⇒ 三层**：
```text
`C`/`D`/`E` ⇒ **设置【显示值**】 ⇒ 被重建覆盖
`J` patch  ⇒ **设置【数据源**】 ⇒ **持久**
⇒ **⇒ 所以【改数据源是唯一持久的方式**】
```

**✅ ⭐⭐⭐ **"改数据源而不是改显示"** —— 一个**极重要的架构判据**。

**⚠ 而"`mp/playerdata.def` 的 profile blob"⇒ **一个客户端侧的持久数据**。**

**✅ 与 §408 的"`_tp` 在【地图自己的 fastfile】"**同族（**第五次"数据的归属**）。

**⇒ 三层**：
```text
§399  **名字在 `cs 3624+n`（服务器写）**
§408  **`_tp` 在地图的 fastfile**
§433  **profile blob 在 `mp/playerdata.def`**（**客户端读**）
⇒ **⇒ 三次"一个数据在哪**】
```

**✅ ⭐ **一个"数据归属"的三例表**。

## 四、**`stageSessionRoster` 的"座位重定位"**（本组第三重要）

### 4.1 那段

```php
// A MEMBER THAT IS ALREADY CONNECTED MUST BE MOVED TO ITS ORDINAL, OR
// THE OWNER OF THE SEAT IT IS SITTING IN IS REFUSED AS SERVER-FULL --
// the 房间人数已满 box.
//
// The roster fixes each member's slot by its ordinal in the
// xuid-sorted member list, and the gamestate commits player names in
// that same order, so the ordinals cannot simply be reassigned around
// whoever happens to be seated. A client that connects BEFORE the
// session is staged has no roster to place it and takes the first
// free slot; when the roster then arrives, that slot is somebody
// else's ordinal. Measured on three consecutive cycles 2026-08-24:
//
//     17:13:11  SessionStart queued members=2
//     17:13:12  connectionless rejected reason=the session roster
//                 client slot is occupied
//     17:13:15  commitSessionRoster rosterMembers=[69420,69421]
//                 connectedClients=[69421@gen0]
//
// 69421 was already sitting in slot 0, which is 69420's ordinal, and
// 69420 got the box every time.
```

### 4.2 二十四层

```text
1. **一个已经连接**的成员【必须被移到它的序号**】**
2. ⇒ **⇒ 否则【坐在它那个座位上的所有者【被拒为"服务器已满**"】】
3. ⇒ **（那个"房间人数已满"框）**
4. ⇒ **名册【按 `xuid` 排序的成员列表里的序号**】固定每个成员的槽**
5. ⇒ **而 gamestate 【按同样的顺序**】提交玩家名**
6. ⇒ **⇒ 所以【序号【不能**】就着【谁碰巧坐着**】重新分配**】
7. ⇒ **一个【在会话被 stage 之前**】连接的客户端【没有名册**】**
8. ⇒ **⇒ 所以【它占【第一个空闲槽**】】**
9. ⇒ **而当名册然后到达时，那个槽【是别人的序号**】**
10. ⇒ **测量，三个连续的周期**（`2026-08-24`）：
      · **`17:13:11`** ⇒ **`SessionStart queued members=2`**
      · **`17:13:12`** ⇒ **`connectionless rejected reason=the session roster client slot is occupied`**
      · **`17:13:15`** ⇒ **`commitSessionRoster rosterMembers=[69420,69421] connectedClients=[69421@gen0]`**
11. ⇒ **`69421` 【已经在槽 `0`**】**而那是 `69420` 的序号**
12. ⇒ **⇒ 而【`69420` 【每一次**】都拿到那个框**】**
```

### 4.3 ⭐⭐⭐ **"`69421` 已经在槽 `0`，而那是 `69420` 的序号，而 `69420` 每次都拿到那个框"**

**✅ 这是本报告里**最完整的一个"序号与座位冲突"的病历**。**

**⇒ 三层**：
```text
名册：【`xuid` 排序**】 ⇒ `[69420, 69421]`
而【先连的那个是 `69421`**】 ⇒ **占了槽 `0`**
⇒ **⇒ 而槽 `0` 是 `69420` 的序号** ⇒ **`69420` 【被拒**】
```

**✅ 与 §426 的"咬哪个客户端只取决于它是否在进入世界之前确认过"**同族（**第四次"一个连接时序决定结果"）。

**⇒ 三层**：
```text
§426  **是否在进入世界前 ack 过**
§433  **谁先连**
⇒ **⇒ 两次"时序决定谁受害**】
```

**✅ ⭐⭐ **一个"时序决定受害"的两例**。

**⚠ 而"三个连续的周期，同一个现象"⇒ **一个可复现的 bug**。**

**✅ 与 §404 的"同一崩溃在一个完全没有 `a` 的 build 上也触发过"**不同（这是**一个稳定复现的 bug**）。

**⇒ 三层**：
```text
**稳定复现** ⇒ **可以定位**
**偶发** ⇒ **难定位**
⇒ **⇒ 所以【三个周期【是一个礼物**】】
```

**✅ ⭐⭐ **"一个稳定复现的 bug 是一个礼物"** —— 一个**取证的机会**。

### 4.4 而**"只有一个【还没被送过 gamestate**】的客户端可以移动"**

```php
// ONLY A CLIENT THAT HAS NOT BEEN SENT A GAMESTATE MAY MOVE. Its slot
// index is its clientNum and nothing has told it that number yet;
// past Connected it has, so it keeps its seat and the collision falls
// through to the reject, which is at least honest about itself.
if (seat.state != ClientState::Free && seat.state != ClientState::Connected)
{
    continue;
}
```

**⇒ 十六层**：
```text
1. **只有一个【还没被送过 gamestate**】的客户端【可以移动**】**
2. ⇒ **它的槽索引【就是它的 `clientNum`**】**
3. ⇒ **而【还没有东西告诉它那个号**】**
4. ⇒ **⇒ 所以【移动它【无害**】**
5. ⇒ **而【过了 `Connected`**】⇒ **它【已经被告诉**】**
6. ⇒ **⇒ 所以【它【保持它的座位**】】**
7. ⇒ **⇒ 而【那个冲突【落到拒绝**】】**
8. ⇒ **⇒ 而那是【至少对自己诚实**】**
```

### 4.5 ⭐⭐⭐ **"那个冲突落到拒绝，而那是至少对自己诚实"**

**✅ 这是本报告里**最重要的一条"宁可拒绝也不破坏"**。**

**⇒ 三层**：
```text
可移动 ⇒ **重定位**（**因为客户端还不知道自己的号**）
不可移动 ⇒ **拒绝**（**因为移动会破坏一个已知的号**）
⇒ **⇒ 所以【"诚实拒绝"优于"静默破坏**】**
```

**✅ 与 §422 的"扣住子实体直到这个名字出现，比把它挂到任意一根骨上更安全"**同族（**第九次"省略优于错误"）。

**⇒ 三层**：
```text
§407  **实体号拿不到 ⇒ 跳过**
§413  **`tag_weapon_right` 不可得 ⇒ 扣住子实体**
§433  **客户端已被告知号 ⇒ 拒绝而不是重定位**
⇒ **⇒ 三次"宁可拒绝**】
```

**✅ ⭐⭐⭐ **一个"宁可拒绝"的三例表**。

**⚠ 而"`Connected` 是那个边界"⇒ **一个精确的状态点**。**

**✅ 与 §426 的"`stage 6` 是进入世界"**配合。

**⇒ 三层**：
```text
`Free` ⇒ 无客户端
`Connected` ⇒ **已被挑战，还不知道号** ⇒ **可移动**
`ClientLoading` ⇒ **已被送 gamestate（含号）** ⇒ **不可移动**
`Active` ⇒ 同
⇒ **⇒ 所以【`Connected` 是【最后一个可安全移动**的状态**】
```

**✅ ⭐⭐ **一个"状态边界"的精确界定**。

## 五、**`stageSessionRoster` 的"stale pending roster 可以被替换"**

### 5.1 那段

```php
// ★★★ 2026-10-07 05:3x -- **允许替换「从未被连接」的旧 pending roster（单变量；d29 实测）**：
//   d29：request 1 全通（`SessionStart accepted`），但客户端在 cold map load 完成前超时
//   报 1102（17 s vs 客户端耐心）⇒ 从未有客户端连接 ⇒ `commitSessionRoster` 永不发生
//   ⇒ `pendingRoster_` 永久占位 ⇒ request 2 起每一次都被拒
//   （`session roster rejected request=N`）⇒ 每点一次必 1102，直到重启 dedicated。
//   判据：若旧 pending roster 的成员**一个都没有占座位**（没有任何非 Free 客户端属于它），
//   它是"空等"的世代，可安全换成新世代；有成员已连接时仍走原来的保守拒绝（不拆活连接）。
```

### 5.2 二十层

```text
1. **允许替换"从未被连接"的旧 `pending roster`**
2. ⇒ **`d29`：request 1 全通（`SessionStart accepted`）**
3. ⇒ **但客户端在【cold map load 完成前超时**】**
4. ⇒ **报 `1102`**（**`17` 秒 vs 客户端的耐心**）
5. ⇒ **⇒ 所以【从未有客户端连接**】**
6. ⇒ **⇒ 所以 `commitSessionRoster` 【永不发生**】**
7. ⇒ **⇒ `pendingRoster_` 【永久占位**】**
8. ⇒ **⇒ 所以【`request 2` 起每一次都被拒**】**
9. ⇒ **（`session roster rejected request=N`）**
10. ⇒ **⇒ 所以【每点一次必 `1102`，【直到重启 dedicated**】】**
11. ⇒ **判据**：**若旧 pending roster 的成员【一个都没有占座位**】**
12. ⇒ **⇒ 它是【"空等"的世代**】**
13. ⇒ **⇒ 所以【可以安全地换成新世代**】**
14. ⇒ **而【有成员已连接时【仍走原来的保守拒绝**】】**
15. ⇒ **⇒ 不拆活连接**
```

### 5.3 ⭐⭐⭐ **"每点一次必 1102，直到重启 dedicated"**

**✅ 这是本报告里**最重要的一个"自锁"**。**

**⇒ 三层**：
```text
`pendingRoster_` 永久占位 ⇒ **新请求全被拒** ⇒ **永远无法恢复**
⇒ **⇒ 所以【一个"等"的状态【变成了一个永久的锁**】】
```

**✅ 与 §407 的"不做清理就会变成永久 prematch"**完全同族（**第三次"忘记释放"）。

**⇒ 三层**：
```text
§402  **prematch 不做清理 ⇒ 永久 prematch**
§426  **`baselineCacheAcknowledged` 不清 ⇒ 永不重发**
§433  **`pendingRoster_` 不超时 ⇒ 永久拒绝**
⇒ **⇒ 三次"需要超时/清理**】
```

**✅ ⭐⭐⭐ **一个"需要清理"的三例表**。

**⚠ 而"判据是『一个都没有占座位』"⇒ **一个基于可观测状态的判据**。**

**✅ 与 §418 的"`baseline != nullptr` 是那个证明"**同族（**第三次"用可观测信号**）。

**⇒ 三层**：
```text
§418  `baseline != nullptr` ⇒ **已 ack**
§432  `reliableAcknowledge == reliableSequence` ⇒ **队列空**
§433  **"没有任何非 Free 客户端属于它"** ⇒ **空等**
⇒ **⇒ 三次"用性质**】
```

**✅ ⭐⭐ **一个"用性质"的三例**（与 §432 的重合）。

**⚠ 而"有成员已连接时仍走保守拒绝，不拆活连接"⇒ **一个精确的边界**。**

**⇒ 三层**：
```text
零成员连接 ⇒ **可替换**
一个成员连接 ⇒ **保守拒绝**（**不拆活连接**）
⇒ **⇒ 所以【"零"是那个安全的点**】
```

**✅ ⭐⭐ **"零是安全的"** —— 与 §416 的"`team = 0` 是崩溃"**相反（这里的零是安全的）。

**✅ 一个**极精细的对比**。

## 六、关键结论

1. **⭐⭐⭐ "票 `22310` 让每条命令都带 `J` ⇒ 客户端每装载一条就重建一次，UI 在重建时读到半装载的 profile ⇒ 客户端 `myTeam` 恒 `0` ⇒ 敌我显示错乱"`** —— 第三次"部分更新"（与 §427、§432 同族）。
2. **⭐⭐ "老外的参考实现与我们的 `hpp` 契约都只在最后一条写 `J`"`**。
3. **⭐⭐⭐ "在 roster / 比赛级字段未变化时不重复发送身份段（`12 × 13 B`）与 `round`/`limit`（`8 B`）= `164 B`，使常规比分更新落进单条命令"`**，而我复算：**`1185 - 164 = 1021 B` ≤ `0x3FE = 1022`** —— **只差 `1` 字节**。
4. **⭐⭐⭐ 一个"一个两字节的修正使一个优化成立"的因果链**：**§431 把 `0x3FC`（`1020`）修正为 `0x3FE`（`1022`）** ⇒ **`1021` 才能落进单条** ⇒ **若界还是 `1020` 则仍分两条** ⇒ **所以 §431 的两字节修正【正是】§433 的优化得以成立的前提**。
5. **⭐⭐ 两个 FNV-1a 指纹**（`1469598103934665603` 的 offset basis + `1099511628211` 的 prime）：`roster`（`userId` + `clientNum << 56`）与 `match`（`roundNumber` + `scoreLimit`）—— 与 §425 的 `lowbias32` 是两个不同的哈希。
6. **⭐ "`clientNum << 56` 只动高字节，避免与 `userId` 混淆"`** —— 一个位移隔离。
7. **⭐⭐ `queueScoreboardResponse` 的"全或无"**（`pendingCount + commands.size() > capacity` ⇒ 全部不排）—— 第四次"全或无"；而 `trace` 有三个明确的结局（`client_free` / `skipped_capacity` / `queued`）。
8. **⭐⭐⭐ "`C`/`D`/`E` 走了：没有命令产生 kills/deaths/assists 的理由是【没有命令能】—— `0x0057B760` 从 `mp/playerdata.def` 的 profile blob 重建每一行，而那个 blob 是被 `J` patch 流写的；`C`/`D`/`E` 走了因为重建也设置队伍分与 score 列"`** —— **"改数据源而不是改显示"** 是一个极重要的架构判据。
9. **⭐ 客户端链**：`CL_ParseServerMessage`（`0x0046E6A0`）→ `sub_46E470` → `sub_57E330` → `sub_57BF70` → `CG_InitScoreboardFromProfile`（`0x0057B760`）。
10. **⭐⭐⭐ `stageSessionRoster` 的座位冲突病历**：**名册按 `xuid` 排序固定序号**，而**先连的 `69421` 占了槽 `0`（`69420` 的序号）⇒ `69420` 每次都拿到"房间人数已满"框** —— 三个连续周期的稳定复现（`2026-08-24 17:13:11/12/15`）⇒ **第四次"时序决定谁受害"**；而**稳定复现是一个取证的机会**。
11. **⭐⭐⭐ "只有一个还没被送过 gamestate 的客户端可以移动：它的槽索引就是它的 `clientNum` 而还没有东西告诉它那个号；过了 `Connected` 它已经被告诉，所以它保持座位，而那个冲突落到拒绝 —— 至少对自己诚实"`** —— 第三次"宁可拒绝"（与 §407、§413 同族）。
12. **⭐ `Connected` 是最后一个可安全移动的状态**（`Free` 无客户端 / `Connected` 不知号 / `ClientLoading`+ 已知号）。
13. **⭐⭐⭐ "`pendingRoster_` 的永久占位 ⇒ 每点一次必 `1102`，直到重启 dedicated"`** —— 第三次"需要清理"（与 §402 的永久 prematch、§426 的 `baselineCacheAcknowledged` 同族）。
14. **⭐ "判据是『一个都没有占座位』"`** —— 第三次"用可观测信号"；而 **"零成员连接"是安全的那个点，有成员连接时走保守拒绝不拆活连接**。

## 七、未闭合点

- `SvProfilePatchMaximumPayload` 的确切值（我推断 `0x3FE`）。
- `SvScoreboardRowCount`（我推断 `12`）与 `13 B`/行的 identity 记录。
- `mp/playerdata.def` 的 blob 格式。
- `1102` 错误码的语义（客户端耐心 `17` 秒）。
- `SV_ScoreboardTraceLine` 的完整结局枚举。
- `sv_client_mp.cpp` 3150 行之后未读取（**共 `4500` 行**）。
