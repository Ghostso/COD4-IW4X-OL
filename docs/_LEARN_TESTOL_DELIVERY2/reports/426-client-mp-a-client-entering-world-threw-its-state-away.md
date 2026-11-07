# 426 · **"一个进入世界的客户端刚刚把它的快照状态扔掉了"** —— `deltaMessage = -1` 为什么还不够、`391` 处的墓碑、以及"两个非 (B) 分支都能永久楔死一个客户端"

## 一、范围

本报告学习 `sv_client_mp.cpp` 420–760 行（菜单响应、构造器、OOB 分派、`ProfileStats`、`GameStateUpdate` 的 `stage 6`、`reliableKeyComplaints`）。

## 二、**"一个进入世界的客户端刚刚把它的快照状态扔掉了"**（本组最重要的一段）

### 2.1 那段

```php
// AND THE RESET THAT HAS TO COME WITH IT -- `client->deltaMessage = -1`.
// Section 167: this branch cited SV_ClientEnterWorld for the snapshot
// schedule and took only that line from it. A CLIENT ENTERING THE WORLD HAS
// JUST THROWN ITS SNAPSHOT STATE AWAY: it loaded the map, reinitialised
// cgame -- which is what re-deals every characterInfo name buffer out of a
// freshly memset pool (0x004555D0) -- and remembers nothing it acknowledged
// while it was loading. Every one of those acknowledgements was still being
// used here as a delta baseline.
//
// MEASURED, both ends of the same frame. ...
//     clientinfo WIRE observer=0 baseline=NONE  0:model6/item545(FULL)
//     clientinfo WIRE observer=1 baseline=NONE  0:model6/item545(FULL)
//     clientinfo WIRE observer=0 baseline=yes   0:model6/item545(skipped)
//     clientinfo WIRE observer=1 baseline=yes   0:model6/item545(skipped)
// while inside one of the two clients every entry sat at
//     req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY
// -- present, flagged for rebuild, and with no model index, which is
// CG_SetupClientCharacterInfo 0x00541800's one early return. So that client
// never wrote a model name again and nobody could see that player.
```

### 2.2 二十四层

```text
1. **而【必须随之而来的重置**】—— `client->deltaMessage = -1`**
2. ⇒ **第 `167` 节：这个分支【引用了 `SV_ClientEnterWorld` 为了快照调度**】**
3. ⇒ **而【只从它那里拿了那一行**】**
4. ⇒ **一个【进入世界的客户端【刚刚把它的快照状态扔掉了**】】**
5. ⇒ **它【加载了地图、重新初始化了 cgame**】**
6. ⇒ **（那正是【从一个刚 memset 的池里重新分发每一个 characterInfo 名字缓冲**】的东西，`0x004555D0`）**
7. ⇒ **⇒ 而它【不记得自己在加载时确认过的任何东西**】**
8. ⇒ **⇒ 那些确认【每一个都仍在这里被用作 delta 基准**】**
9. ⇒ **测量，同一帧的两端**：
      · **专用服说【写了一次然后永远跳过**】，正确地，因为它的基准说客户端已经知道
      · **`baseline=NONE` ⇒ `(FULL)`**
      · **`baseline=yes` ⇒ `(skipped)`**
10. ⇒ **而【在其中一个客户端内部，每一个条目都停在**】：
      · **`req{ALL-ZERO}`**
      · **`valid=1`**
      · **`rebuild=1`**
      · **`model=EMPTY`**
11. ⇒ **⇒ 【存在、被标记为重建、而没有模型索引**】**
12. ⇒ **那正是 `CG_SetupClientCharacterInfo` 的【唯一一个早期返回**】（`0x00541800`）**
13. ⇒ **⇒ 所以【那个客户端【再也没写过模型名**】】**
14. ⇒ **⇒ 而【没有人能看见那个玩家**】**
15. ⇒ **⇒ 而它咬哪个客户端【只取决于它是否在进入世界之前确认过一份快照**】**
16. ⇒ **⇒ 那就是为什么它【看起来随机**】并在不同运行间【在玩家之间移动**】**
```

### 2.3 ⭐⭐⭐ **"咬哪个客户端只取决于它是否在进入世界之前确认过一份快照"**

**✅ 这是本报告里**最重要的一个"竞态的正确解释**。**

**⇒ 三层**：
```text
机制：**进入世界前的确认 ⇒ 服务端的基准以为客户端知道** ⇒ **跳过发送**
后果：**客户端已清空 ⇒ 它什么也没有** ⇒ **永不可见**
⇒ **⇒ 而"进入世界之前确认过"是一个【时序竞态**】
```

**✅ 与 §413 的"`12.163` 追了一个 1.6s 的 think 尖峰"**不同（这是**一个时序竞态**）。

**⇒ 三层**：
```text
§406  "延迟是常数；选择是那个竞赛"
§426  **"咬哪个客户端取决于它是否在进入世界之前确认过"**
⇒ **⇒ 两次"一个选择其实是竞赛"**
```

**✅ ⭐⭐ **一个"竞赛伪装成随机"的两例**。

### 2.4 而**"四个东西必须一起清"**

```cpp
slot->deltaMessage = -1;
slot->snapshotHistory = {};
slot->baselineCacheAcknowledged = false;
slot->baselineCacheInitializationMessage.reset();
...
slot->newestFlaggedSnapshotMessage.reset();
slot->baselineFrame.reset();
```

**⇒ 十二层**：
```text
1. **`deltaMessage = -1`** ⇒ **标准**（`SV_ClientEnterWorld` 的那一行）
2. ⇒ **`snapshotHistory = {}`** ⇒ **历史帧全部作废**
3. ⇒ **`baselineCacheAcknowledged = false`** ⇒ **持久实体基准缓存也必须走**
4. ⇒ **理由**："留着 `baselineCacheAcknowledged` 会让【下一份快照拿到 `baselineFrame`**】而【完全撤销这件事**】"
5. ⇒ **因为【那条路径【根本不查 `deltaMessage`**】】**
6. ⇒ **⇒ 所以【客户端的缓存【随它的地图加载一起死了**】】**
7. ⇒ **`baselineCacheInitializationMessage.reset()`**
8. ⇒ **`newestFlaggedSnapshotMessage.reset()`** ⇒ **第 `170` 节**
9. ⇒ **`baselineFrame.reset()`**
10. ⇒ **理由**："它们描述【同一个代次**】"
11. ⇒ **⇒ 留着它会让【下一次选择**】命名【这个连接【前一个生命**】的一个被标记的帧**
12. ⇒ **⇒ 而那是【"多绕几步的同一个缺陷**】"
```

### 2.5 ⭐⭐⭐ **"那是『多绕几步的同一个缺陷』"**

**✅ 这是本报告里**最精准的一句"不完整的修复"**。**

**⇒ 三层**：
```text
只清 `deltaMessage` ⇒ **那个缺陷仍在**（通过 `baselineCacheAcknowledged` 复发）
全部清 ⇒ **缺陷消失**
⇒ **⇒ 所以【"清一半"是【换一个路径复发同样的 bug**】】
```

**✅ 与 §410 的"压制边沿是不够的，因为边沿是先到的"**同族（**第六次"修一半等于没修"）。

**⇒ 三层**：
```text
§404  压制边沿不够 ⇒ **触发也必须检查**
§426  清 `deltaMessage` 不够 ⇒ **五个兄弟状态也必须清**
⇒ **⇒ 两次"一个入口多个出口**】
```

**✅ ⭐⭐⭐ **一个"修一半"的两例**。

**⚠ 而"六个状态"⇒ **`deltaMessage` / `snapshotHistory` / `baselineCacheAcknowledged` / `baselineCacheInitializationMessage` / `newestFlaggedSnapshotMessage` / `baselineFrame`**。**

**⇒ 三层**：
```text
六个状态
而注释分别给出【第 `167` 节（前四个）与第 `170` 节（后两个）**】
⇒ **⇒ 所以【两个代次被两次发现**】
```

**✅ ⭐ **一个"两次独立发现同一类问题"的实例**。

### 2.6 而**"`req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY`"**

**⇒ 六层**：
```text
`req{ALL-ZERO}` ⇒ **请求记录全零**
`valid=1` ⇒ **但标记为有效**
`rebuild=1` ⇒ **且标记为需重建**
`model=EMPTY` ⇒ **而模型索引为空**
⇒ **⇒ 所以【一个"有效但空"的状态**】
```

**✅ 与 §418 的"`SvEntityState{}` 不是零"**不同（这是**一个"有效但空"的合法状态**）。

**⇒ 三层**：
```text
`valid=1` ⇒ **一个合法的记录**
`model=EMPTY` ⇒ **而它指向"没有模型"**
⇒ **⇒ 所以【`CG_SetupClientCharacterInfo` 的早期返回是正确的行为**】
```

**✅ ⭐⭐ **"一个正确的函数在一个错误的状态上返回"** —— 与 §413 的"GIGO"**同族（**第二次"输入错误而非实现错误"）。

## 三、**`reliableKeyComplaints` 的两个永远楔死分支**（本组第二重要）

### 3.1 那段

```php
// OLMOD(reliable-key-desync-witness): SAY WHICH BRANCH TOOK THE KEY AWAY.
//
// A REMOTE client wedged permanently mid-match 2026-08-25 (HANDOFF 150e): its ack
// counter froze at 1835/103 and never moved again while two local clients carried on,
// and it posted no ClientException because a netchan that no longer decodes cannot
// carry one. The freeze correlates exactly with the DEATH/RESPAWN reliable burst --
// eight commands in three seconds, SIX of them on one serverTime.
//
// Both non-(B) branches below can wedge a client for good, and neither says so:
//   nullopt      the packet is rejected. If the client keeps acking that same number,
//                every future packet is rejected too -- a permanent one-way freeze.
//   empty key    the XOR key diverges from the one the client used, so every later
//                packet decodes to garbage. Also permanent.
// A local client acks instantly and its gap never grows; a remote one, mid-burst, is
// exactly where a gap comes from -- which is why this has only ever bitten remotely.
//
// Silent while healthy, and it reports the VALUES rather than a verdict: whichever
// branch fires names itself, instead of a fourth guess being made about which did.
```

### 3.2 二十四层

```text
1. **说【哪一个分支**】把键拿走了**
2. ⇒ **一个远端客户端在 `2026-08-25` 【永久地楔死**】在比赛中途（`HANDOFF 150e`）**
3. ⇒ **它的 `ack` 计数器【冻在 `1835/103`**】**
4. ⇒ **而【再也不动**】而两个本地客户端照常**
5. ⇒ **而它【没有发 `ClientException`**】**
6. ⇒ **⇒ 因为【一个不再能解码的 netchan 【不能携带一个**】】**
7. ⇒ **⇒ 那个冻结【精确地与死亡/重生可靠突发相关**】**
8. ⇒ **（三秒内 `8` 条命令，其中 `6` 条在【同一个 `serverTime`**）**
9. ⇒ **⇒ 而下面两个非 (B) 分支【每一个**】都能永久楔死一个客户端**
10. ⇒ **而【两个都不说**】**
11. ⇒ **`nullopt`** ⇒ **包被拒绝**
12. ⇒ **⇒ 若客户端【继续 ack 同一个号**】⇒ **每一个未来的包也被拒绝**】
13. ⇒ **⇒ 【一个永久单向冻结**】**
14. ⇒ **空键** ⇒ **XOR 键【从客户端用的那个偏离**】**
15. ⇒ **⇒ 所以【每一个后来的包解码成垃圾**】⇒ **也是永久的**
16. ⇒ **一个本地客户端【瞬间 ack**】而它的间隙【从不增长**】**
17. ⇒ **一个远端的一个【在突发中途**】正是【间隙来的地方**】**
18. ⇒ **⇒ 那就是【为什么这【只**】咬过远端**】**
19. ⇒ **⇒ 健康时静默**
20. ⇒ **而它【报告值而不是一个判决**】**
21. ⇒ **⇒ 无论哪个分支触发【它自己命名自己**】**
22. ⇒ **而不是【对"哪个做了"作第四个猜测**】**
```

### 3.3 ⭐⭐⭐ **"报告值而不是一个判决；无论哪个分支触发它自己命名自己，而不是作第四个猜测"**

**✅ 这是本报告里**最重要的一条取证设计**。**

**⇒ 三层**：
```text
错误做法：**一个布尔"键坏了"** ⇒ **还要猜是哪个分支**
正确做法：**每个分支【自己打印】** ⇒ **日志直接命名**
⇒ **⇒ 所以【取证点必须【在分叉处**】而不是在汇合处**】
```

**✅ 与 §405 的"三个可能的所有者而一个也没留一行"**同族（**第五次"多因歧义"）。

**⇒ 三层**：
```text
§405  "『领先/失去是静默的』三个所有者一个没留一行" ⇒ **加一行**
§410  "『create vs send』两个不同的声明" ⇒ **端到端核对**
§426  **"两个非 (B) 分支都能楔死而两个都不说"** ⇒ **各自命名自己**
⇒ **⇒ 三次"歧义的消除**】
```

**✅ ⭐⭐ **一个"消除歧义"的三例表**。

### 3.4 而**"一个本地客户端瞬间 ack 而其间隙从不增长"**

**✅ 与 §405 的"两个客户端，一个本地一个远端"**不同（这是**延迟差**）。

**⇒ 三层**：
```text
本地 ⇒ **`RTT ≈ 0`** ⇒ **ack 立刻到** ⇒ **间隙不增长**
远端 ⇒ **`RTT > 0`** 而**在突发中** ⇒ **间隙出现**
⇒ **⇒ 所以【这个 bug 只在远端发作**】
```

**✅ ⭐⭐ **"一个只在远端发作的 bug 在本地测试里永不可见"** —— 与 §412 的"远端 bot"不同。

**⚠ 而"三秒内 `8` 条命令，其中 `6` 条在同一个 `serverTime`"⇒ **一个具体的突发**。**

**✅ 与 §404 的"`1500ms` 的竞赛"**配合（**那是重生突发**）。

**⇒ 三层**：
```text
§404  **死亡/重生簇**（`r 2`/`r 1`/`v 18`）
§426  **"死亡/重生可靠突发"** ⇒ **正是那个簇**
⇒ **⇒ 所以【同一个簇在两个层面有害**】
```

**✅ ⭐⭐ **一个"同一突发两个后果"的实例**。

## 四、**`SV_ProfileStats` 的"部分块 ⇒ 缩小必需掩码"**

### 4.1 那段

```cpp
const auto chunkIndex = packet[std::size(ProfileStatsPrefix)];
if (chunkIndex >= ProfileStatsChunkCount)
    return reject("EXE_BAD_STATS", "profile stats chunk index is out of range");

const auto slot = std::find_if(...);
if (slot == clients_.end())
    return reject("EXE_BAD_STATS", "profile stats arrived before direct connect");

const auto chunkBit = 1u << chunkIndex;
slot->profileStatsReceivedMask |= chunkBit;
const auto payloadSize = packet.size() - HeaderSize;
if (payloadSize < ProfileStatsChunkSize)
    slot->profileStatsRequiredMask = (chunkBit << 1) - 1;
const auto remainingMask =
    slot->profileStatsRequiredMask & ~slot->profileStatsReceivedMask;
slot->profileStatsComplete = remainingMask == 0;
```

### 4.2 十八层

```text
1. **`chunkIndex` 必须 `< 27`** ⇒ 否则拒绝
2. ⇒ **必须在一个【已连接的槽**】（`state != Free && peer == peer`）
3. ⇒ **⇒ 所以【`stats` 必须在 `connect` 之后**】
4. ⇒ **`receivedMask |= 1 << chunkIndex`**
5. ⇒ **若 `payloadSize < 1238`**（**一个短块 = 最后一块**）
6. ⇒ **⇒ `requiredMask = (chunkBit << 1) - 1`**
7. ⇒ **⇒ 那是【`chunkIndex + 1` 个低位全一**】**
8. ⇒ **⇒ 所以【只需要 `0..chunkIndex` 块**】**
9. ⇒ **`remaining = required & ~received`**
10. ⇒ **`complete = remaining == 0`**
11. ⇒ **回 `statResponse <remainingMask>`**
12. ⇒ **⇒ 所以【客户端知道还缺哪些块**】
```

### 4.3 ⭐⭐⭐ **"一个短块的索引决定了总共需要多少块"**

**✅ 这是本报告里**最精巧的一处协议设计**。**

**⇒ 三层**：
```text
假设：**总是 27 块**
实际：**第 N 块短 ⇒ 一共只要 N+1 块**
⇒ **⇒ 所以【块数是【自描述的**】**
```

**✅ 与 §425 的"27 个独立的 OOB 包没有序列号"**——**这里给出了缓解**。**

**⇒ 三层**：
```text
§425  我标注"没有序列号 ⇒ 顺序与完整性依赖客户端重试"
§426  **`receivedMask` 是一个【27 位集合**】⇒ **乱序无害**
⇒ **⇒ 所以【位掩码解决了乱序问题**】
```

**✅ ⭐⭐⭐ **一个跨报告的闭合**。

**⚠ 而"`(chunkBit << 1) - 1`"⇒ **让我验证**。**

**⇒ 计算**：
```text
chunkIndex = 0 ⇒ chunkBit = 1 ⇒ (1<<1)-1 = 1 = 0b1 ⇒ **需要块 0**
chunkIndex = 2 ⇒ chunkBit = 4 ⇒ (4<<1)-1 = 7 = 0b111 ⇒ **需要块 0/1/2**
chunkIndex = 26 ⇒ chunkBit = 1<<26 ⇒ (1<<27)-1 ⇒ **需要块 0..26** ✓
```

**✅ **精确吻合**。

**✅ ⭐⭐ **一个"位掩码算术"的验证**。

**⚠ 而"`1u << 26`"⇒ **`uint32` 够**（最大 `2^27 - 1`）✓

## 五、**`SV_GameStateUpdate` 的六个阶段**

```cpp
if (!stage || *stage < 1 || *stage > 6 || !trimLeft(arguments).empty())
    return {};
...
if (*stage < slot->gameStateUpdateStage ||
    *stage > slot->gameStateUpdateStage + 1)
{
    return {};
}
```

**⇒ 十二层**：
```text
1. **六个阶段（`1..6`）**
2. ⇒ **必须【单调递增**】或【同一个**】**
3. ⇒ **⇒ 所以【`stage` 只能【保持或 +1**】**
4. ⇒ **而多余 token ⇒ 拒绝**
5. ⇒ **`stage == 6` ⇒ 客户端变 `Active`**
6. ⇒ **并【六样东西一起重置**】（§二）
7. ⇒ **⇒ 所以【`stage 6` 是"进入世界**"**
```

### 5.1 ⭐⭐ **"只能保持或 `+1`"**

**✅ 一个"单调递增的握手"**。

**⇒ 三层**：
```text
若允许跳跃（`1 → 6`）⇒ **跳过中间状态**
若允许回退（`6 → 3`）⇒ **重复进入**
⇒ **⇒ 所以【保持或 `+1`**】是最严格的可接受集**
```

**✅ ⭐ **一个"状态机转移规则"的实例**。

**⚠ 而"重复同一个 stage ⇒ 接受但不递增"**（`if (*stage > slot->gameStateUpdateStage)` 才 `++gameStateUpdatesReceived_`）。

**⇒ 三层**：
```text
同一个 stage ⇒ **`lastPacketTime` 更新** ⇒ **但计数器不增**
⇒ **⇒ 所以【重传是幂等的**】
```

**✅ ⭐⭐ **一个"幂等的重传"**。

## 六、**`SV_DispatchMenuResponse` 的"重放不改阵营"**

### 6.1 那段

```php
// COD class menus can be replayed by the client after entering the
// game.  A replay selects a loadout, but does not renegotiate the
// authoritative team; accepting it here would silently move a player
// between SD sides and make the round state oscillate.
if (client.gameplayState == ClientGameplayState::Playing &&
    (client.team == SvTeam::Tf || client.team == SvTeam::Sc))
{
    client.pendingCharacterFaction = client.characterFaction;
    client.pendingTeam = client.team;
}
```

**⇒ 十四层**：
```text
1. **COD 的职业菜单【可以在进入游戏后**】被客户端重放**
2. ⇒ **一次重放【选择一个配装**】**
3. ⇒ **但【不重新协商**】那个权威的队伍**
4. ⇒ **⇒ 在这里接受它会让一个玩家【在 SD 两边之间【静默地移动**】】**
5. ⇒ **⇒ 而让回合状态【振荡**】**
6. ⇒ **⇒ 所以在 `Playing` 且队伍已定时【保留原队**
```

### 6.2 ⭐⭐⭐ **"接受它会让一个玩家在 SD 两边之间静默地移动，而让回合状态振荡"**

**✅ 这是本报告里**最重要的一次"重放防护**。**

**⇒ 三层**：
```text
风险：**重放菜单 ⇒ 换边**
后果：**回合状态振荡**（**因为回合数已计**）
⇒ **⇒ 所以【队伍在 `Playing` 后【不可变**】】
```

**✅ 与 §407 的"没有人在这之后重生"**同族（**第二次"一个状态在某个点之后不可变"）。

**⇒ 三层**：
```text
§407  `matchStatus_.completed` ⇒ **之后无人重生**
§426  `Playing` + team 已定 ⇒ **之后不可换边**
⇒ **⇒ 两个"锁定点**】
```

**✅ ⭐⭐ **一个"锁定点"的两例**。

**⚠ 而"`characterFaction` 保留原值"⇒ **所以模型也不变**。**

**✅ 与 §411 的"faction 只驱动敌我显示"**配合。

## 七、关键结论

1. **⭐⭐⭐ "一个进入世界的客户端刚刚把它的快照状态扔掉了"**：它**加载了地图、重新初始化了 cgame**（**从刚 memset 的池重新分发每一个 `characterInfo` 名字缓冲，`0x004555D0`**），**不记得自己确认过什么**——而**那些确认仍被用作 delta 基准**。
2. **⭐⭐⭐ 端到端测量**：**专用服写每个观察者一次然后永远跳过（正确）**，**而客户端内部每个条目停在 `req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY`** ⇒ **正是 `CG_SetupClientCharacterInfo` 的早期返回** ⇒ **那个客户端再也没写过模型名 ⇒ 没人能看见那个玩家**。
3. **⭐⭐⭐ "咬哪个客户端只取决于它是否在进入世界之前确认过一份快照 ⇒ 那就是为什么它看起来随机并在不同运行间在玩家之间移动"`** —— 一个**竞赛伪装成随机**的实例（与 §406 的"选择是那个竞赛"同族）。
4. **⭐⭐⭐ 六个状态必须一起清**（`deltaMessage` / `snapshotHistory` / `baselineCacheAcknowledged` / `baselineCacheInitializationMessage` / `newestFlaggedSnapshotMessage` / `baselineFrame`），而**只清 `deltaMessage` 是"多绕几步的同一个缺陷"**（因为 `baselineFrame` 那条路径**根本不查 `deltaMessage`**）。
5. **⭐⭐⭐ "那是『多绕几步的同一个缺陷』"`** —— 第二次"修一半等于没修"（与 §404 的"压制边沿不够"同族）。
6. **⭐⭐ "`req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY`"** —— 一个**"有效但空"的合法状态** ⇒ `CG_SetupClientCharacterInfo` 的早期返回是正确行为，**错的是输入**（第二次"输入错误而非实现错误"）。
7. **⭐⭐⭐ `HANDOFF 150e` 的完整病历**：**一个远端客户端的 `ack` 冻在 `1835/103` 永不移动**，**没有 `ClientException` 因为"一个不再能解码的 netchan 不能携带一个"**，**而冻结精确地与死亡/重生可靠突发相关（三秒 `8` 条命令，`6` 条在同一个 `serverTime`）**。
8. **⭐⭐⭐ "两个非 (B) 分支都能永久楔死一个客户端，而两个都不说"**：`nullopt`（**永久单向冻结**）/ 空键（**永久乱码**）。
9. **⭐⭐ "一个本地客户端瞬间 ack 而它的间隙从不增长；一个远端的一个在突发中途正是间隙来的地方 ⇒ 那就是为什么这只咬过远端"`** —— 一个**只在远端发作的 bug 在本地测试里永不可见**。
10. **⭐⭐⭐ "它报告值而不是一个判决：无论哪个分支触发它自己命名自己，而不是对『哪个做了』作第四个猜测"`** —— 第三次"消除歧义"（与 §405/§410 同族）。
11. **⭐⭐⭐ `ProfileStats` 的"一个短块的索引决定总共需要多少块"**：**`requiredMask = (chunkBit << 1) - 1`** ⇒ **`chunkIndex + 1` 个低位全一** ⇒ **块数是自描述的**；而我验证：`index 0` ⇒ `0b1`、`index 2` ⇒ `0b111`、`index 26` ⇒ `0b(1<<27)-1` ✓
12. **⭐⭐ 这解决了 §425 的"27 个 OOB 包没有序列号"的乱序问题**：**`receivedMask` 是一个 `27` 位集合 ⇒ 乱序无害**。
13. **⭐ `GameStateUpdate` 的六个阶段只能【保持或 `+1`】**（跳级与回退都被拒绝），而**重复同一个 stage 是幂等的**（`lastPacketTime` 更新而计数器不增）。
14. **⭐⭐ "COD 的职业菜单可以在进入游戏后被客户端重放；一次重放选择一个配装但不重新协商权威队伍；接受它会让一个玩家在 SD 两边之间静默地移动而让回合状态振荡"`** —— 第二个"锁定点"（与 §407 的"之后无人重生"同族）。

## 八、未闭合点

- `0x004555D0` 的 memset 池。
- `CG_SetupClientCharacterInfo` 的"唯一早期返回"条件。
- `(B)` 分支是什么（注释提到"两个非 (B) 分支"）。
- `ReliableKeyComplaintLimit` 的值。
- `1835/103` 的两个数各是什么。
- `sv_client_mp.cpp` 760 行之后未读取（**共 `4500` 行**）。
