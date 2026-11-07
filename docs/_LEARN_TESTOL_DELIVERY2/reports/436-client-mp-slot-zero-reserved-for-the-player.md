# 436 · **"从 `1` 开始扫描，让槽 `0` 每次都留给那个玩家"** —— `EXE_SERVERISFULL` 的"房间已满"、`connectTime` 的保留、以及 `'K'` 与 `'J'` 的诊断区分

## 一、范围

本报告学习 `sv_client_mp.cpp` 3820–4160 行（`SV_DirectConnect` 的收尾、多个状态查询、`freeClientSlot` 的槽 `0` 保留、`activateBotSlot` 的开头）。

## 二、**"从 `1` 开始扫描，让槽 `0` 每次都留给那个玩家"**（本组最重要的一段）

### 2.1 那段

```php
// B3 (V1.7): SLOT 0 IS RESERVED FOR A REAL PLAYER. Only bot allocation
// calls this, so the reservation lives here. Measured 2026-10-11
// 00:02:31: BOTTRACE|slot-create client=0..3 -- the bots took the
// host's own slot before he had rejoined, and he was then refused with
// "connectionless rejected ... reason=the session roster client slot
// is occupied" (what the player sees as "the room is full"). Starting
// the scan at 1 leaves slot 0 free for that player every time.
const auto first = clients_.size() > 1 ? clients_.begin() + 1 : clients_.begin();
const auto slot = std::ranges::find(first, clients_.end(), ClientState::Free, &ClientSlot::state);
```

### 2.2 二十四层

```text
1. **槽 `0` 是【留给一个真实玩家**】的**
2. ⇒ **只有 bot 分配调用这个** ⇒ **所以保留【在【这里**】**
3. ⇒ **测量 `2026-10-11 00:02:31`**：**`BOTTRACE|slot-create client=0..3`**
4. ⇒ **⇒ bot 【拿走了主机自己的槽**】在他重新加入之前**
5. ⇒ **⇒ 而他然后被拒为【"`connectionless rejected ... reason=the session roster client slot is occupied`"**】**
6. ⇒ **⇒ 那就是【玩家看成"房间已满**"的东西**】
7. ⇒ **⇒ 从 `1` 开始扫描【让槽 `0` 【每一次**】都留给那个玩家**
```

### 2.3 ⭐⭐⭐ **"bot 拿走了主机自己的槽，而他然后被拒为『房间已满』"**

**✅ 这是本报告里**最重要的一条"一个修复在错误的地方制造了问题"**。**

**✅ 与 §433 的"`69420` 每次都拿到那个框"**——**同一症状，不同的原因** ✓

**⇒ 三层**：
```text
§433  **先连的占错槽 ⇒ 后连的被拒**
§436  **bot 先占了槽 `0` ⇒ 主机被拒**
⇒ **⇒ 同一个"房间已满"的两个来源**
```

**✅ ⭐⭐⭐ **"同一个症状的两个来源"** —— 与 §428 的"四个项能把它关着"**同族（**第八次"多因歧义"）。

**⇒ 三层**：
```text
§405  **三个所有者一个没留一行**
§428  **四个闸门一个都没命名**
§433+§436  **同一个"房间已满"有两个原因**
⇒ **⇒ 三次"同一症状多因**】
```

**✅ ⭐⭐ **一个"同一症状多因"的三例表**。

**⚠ 而"`client=0..3`"⇒ **四个 bot 全部从 `0` 开始**。**

**⇒ 三层**：
```text
`client=0..3` ⇒ **bot 1 拿 `0`，bot 2 拿 `1`，...**
⇒ **⇒ 所以【槽 `0` 被第一个 bot 占了**】
```

**✅ ⭐ **一个"顺序分配"的实例**。

### 2.4 而**"保留在【这里】**"**

**⇒ 五层**：
```text
1. **"只有 bot 分配调用这个"** ⇒ **所以保留在 `freeClientSlot`**
2. ⇒ **而【不是**】在 `SV_DirectConnect`
3. ⇒ **⇒ 所以【一个真实玩家的连接【不受**】这个保留影响**
4. ⇒ **⇒ 而【一个真实玩家【能拿槽 `0`**】**
5. ⇒ **⇒ 所以【这个保留是【单向**的】
```

**✅ ⭐⭐ **"一个单向的保留"** —— 与 §433 的"只有 `Connected` 的客户端可以移动"**同族（**第四次"单向**）。

**⇒ 三层**：
```text
§421  `fullNavigationBounds` **单向提升**
§431  `spawnSequence` **防溢出**
§433  **只有 `Connected` 可以移动**
§436  **槽 `0` 保留只对 bot**
⇒ **⇒ 四个单向规则**
```

**✅ ⭐ **一个"单向规则"的四例表**。

## 三、**`connectTime` 的保留**（本组第二重要）

### 3.1 那段

```cpp
*slot = {
    .state = ClientState::Connected,
    ...
    .connectTime = existing == clients_.end() ? nowMilliseconds : existing->connectTime,
    .lastPacketTime = nowMilliseconds,
    .nextSnapshotTime = nowMilliseconds,
    ...
};
```

**⇒ 十层**：
```text
1. **`existing` 找到了** ⇒ **重连** ⇒ **保留 `existing->connectTime`**
2. ⇒ **`existing` 没找到** ⇒ **新连** ⇒ **`nowMilliseconds`**
3. ⇒ **⇒ 所以【`connectTime` 是【第一次连接的**时间**】
4. ⇒ **而【`lastPacketTime` 与 `nextSnapshotTime` 【每次都重置**】**
5. ⇒ **⇒ 所以【一个是累积的，两个是瞬时的**】
```

### 3.2 ⭐⭐⭐ **"`connectTime` 保留而 `lastPacketTime` 重置"**

**✅ 与 §434 的"`stage 6` 时重置六个而 `spawnSequence` 保留"**不同（这是**一个重连场景**）。

**⇒ 三层**：
```text
`connectTime` ⇒ **第一次连接** ⇒ **保留** ⇒ **因为【`autoSelectMissingLoadouts` 的宽限【从一个【固定的**起点算**】
`lastPacketTime` ⇒ **超时判据** ⇒ **重置** ⇒ **因为【它是"最近活动**"
⇒ **⇒ 所以【两个字段的语义不同**】
```

**✅ ⭐⭐⭐ **"`connectTime` 是宽限的起点，`lastPacketTime` 是超时的判据"** —— 一个**语义分工的精确定位**。

**✅ 与 §435 的"`500ms` 宽限"**完全闭合 ✓

**⇒ 三层**：
```text
§435  **`nowMilliseconds - client.connectTime < GraceMilliseconds`**
§436  **`connectTime` 【在重连时保留**】
⇒ **⇒ 所以【一个重连的客户端【不重置宽限**】
```

**✅ ⭐⭐ **"重连不重置宽限"** —— 一个**行为的具体后果**。

**⚠ 而"这可能是【有意**的（**重连不应重得宽限**）或**一个疏漏**。"

**⚠ 一个**需标注的点**。

### 3.3 而**`nextSnapshotTime` 的注释**

```php
// CODREF(sv_direct_connect): BO1/Kisak SV_DirectConnect and Ghosts
// 0x1401F25B0 initialize nextSnapshotTime from svs.time
// after accepting the client. This is scheduling state, not a
// sentinel where zero means immediately due.
.nextSnapshotTime = nowMilliseconds,
```

**⇒ 八层**：
```text
1. **`BO1`/`Kisak` 的 `SV_DirectConnect` 与 `Ghosts` `0x1401F25B0`**
2. ⇒ **在接一个客户端之后【从 `svs.time` 初始化 `nextSnapshotTime`**】**
3. ⇒ **⇒ 而【这是【调度状态**，不是一个"零意味着立刻到期**"的哨兵**】
4. ⇒ **⇒ 所以【必须显式设 `nowMilliseconds`**】
```

**✅ 与 §413 的"`stage 6` 时 `nextSnapshotTime = nowMilliseconds`，重用零初始化的字段在 `INT32_MAX` 毫秒之后会破坏环绕安全的比较"**——**完全同源** ✓

**⇒ 三层**：
```text
§413  **`nextSnapshotTime = nowMilliseconds`（因为零初始化在 `INT32_MAX` 之后坏）**
§436  **"这是调度状态，不是一个哨兵"**
⇒ **⇒ 两次同一理由**
```

**✅ ⭐⭐ **一个"零不是哨兵"的第三次确认**。</br>

**✅ 与 §416 的"`team = 0` 是崩溃"**、§417 的"`field00E4 = 0` 是索引 0"**同族（**第五次"零不是中性值"）。

**⇒ 三层**：
```text
§413  **`nextSnapshotTime = 0` 在 `INT32_MAX` 后坏**
§416  **`team = 0` ⇒ AV**
§417  **`field00E4 = 0` ⇒ 索引 0**
§429  **`distance = 0` ⇒ 非 delta 分支**
§435  **`viewmodelIndex = 0` ⇒ AV**
§436  **`nextSnapshotTime = 0` ⇒ 立刻到期**
⇒ **⇒ 六次"零不是中性值**】
```

**✅ ⭐⭐⭐ **一个"零不是中性值"的六例表** —— 本报告最完整的归纳。

## 四、**"`EXE_SERVERISFULL` = 房间已满"的三条路径**（本组第三重要）

### 4.1 三条

```text
① `rosterMember` 存在但【那个序号槽被占**】 ⇒ `EXE_SERVERISFULL` + "the session roster client slot is occupied"
② `rosterMember` 不存在而【没有空闲槽**】 ⇒ `EXE_SERVERISFULL` + "all CODOL client slots are occupied"
③ （隐含）`duplicateIdentity` ⇒ 不同错误（`EXE_BAD_CHALLENGE`）
```

**⇒ 十二层**：
```text
1. **① 名册序号槽被占** ⇒ **一个【逻辑上的**冲突**
2. ⇒ **② 全部槽被占** ⇒ **一个【物理上的**耗尽**
3. ⇒ **⇒ 两条不同的消息**（`"the session roster client slot is occupied"` vs `"all CODOL client slots are occupied"`）
4. ⇒ **⇒ 而【玩家看到的都是"房间已满**"】**
5. ⇒ **⇒ 加上 §433 的"先连的占错槽"** ⇒ **三条路径通向同一个框**
```

**✅ 与 §430 的"两个失败打印不同的字段而不是共用一个词"**同族（**第五次"分支各自命名"）。

**⇒ 三层**：
```text
§426  **`REJECTED` / `EMPTY`**
§430  **`entity-generation` / `entity-generation-unrecorded`**
§436  **两条不同的 `EXE_SERVERISFULL` 消息**
⇒ **⇒ 三次"分支命名"**
```

**✅ ⭐⭐ **一个"分支命名"的三例表**。

**⚠ 而"`duplicateIdentity` 的 `client.peer != peer`"⇒ **一个"同一 XUID 来自不同 peer"的检查**。**

**⇒ 六层**：
```text
`client.xuid == outerXuid && client.sessionGeneration == challengeRecord->sessionGeneration && client.peer != peer`
⇒ **⇒ 一个【同一身份来自不同地址**】⇒ 拒绝**
⇒ **⇒ 理由：一个会话里的一个玩家【只能有一个连接**】
```

**✅ ⭐⭐ **一个"身份唯一性"的实例**。

### 4.2 而**"`existing` 的匹配用 `peer == peer`"**

```cpp
auto existing = std::find_if(clients_.begin(), clients_.end(), [&](const ClientSlot &client) {
    return client.state != ClientState::Free && client.peer == peer &&
        client.xuid == *outerXuid &&
        client.sessionGeneration == challengeRecord->sessionGeneration;
});
```

**⇒ 八层**：
```text
1. **三重匹配**：`peer` + `xuid` + `sessionGeneration`**
2. ⇒ **⇒ 所以【一个重连的客户端【必须三者都相同**】】
3. ⇒ **而【端口可能变**】（§435 的 `findChallenge` 只比 IP）
4. ⇒ **⇒ 所以【`peer` 的比较【是比较端口吗**】】**
```

**⚠ 一个**需要核对的问题**（`peer == peer` **是否包含端口**）。

**⇒ 三层**：
```text
若 `PeerAddress` 的 `==` **含端口** ⇒ **端口变 ⇒ 找不到 `existing`** ⇒ **新建一个槽**
若**只含 IP** ⇒ **端口变 ⇒ 找到 `existing`** ⇒ **重连**
⇒ **⇒ 而 §435 说 `findChallenge` "只比 IP"** ⇒ **所以 `==` 可能含端口**
```

**⚠ 一个**潜在的不一致**（`findChallenge` 只比 IP 而 `existing` 用 `==`）。

**✅ 一个**需标注的点**。

## 五、**`serverReliableCommandStatus` 的 `'K'` 与 `'J'`**（本组第四重要）

### 5.1 那段

```cpp
// A profile patch is opaque bytes, so the diagnostic shows
// its verb and size - which is the part worth reading, since
// 'K' loading without a rebuild is exactly what a split
// update looks like on the wire.
if (!command.payload.empty() &&
    (command.payload[0] == SvProfilePatchLoadAndRebuild ||
        command.payload[0] == SvProfilePatchLoadOnly))
{
    return std::string{ "!" } + static_cast<char>(command.payload[0]) + " " +
        std::to_string(command.payload.size());
}
```

### 5.2 十四层

```text
1. **一个 profile patch 是【不透明字节**】**
2. ⇒ **⇒ 所以诊断【显示它的【动词与大小**】】**
3. ⇒ **而那是【值得读的部分**】**
4. ⇒ **因为【`'K'` 装载而不重建**】**
5. ⇒ **⇒ 正是【一个分裂的更新**在线上看起来的样子**】**
6. ⇒ **`SvProfilePatchLoadAndRebuild`**（= `'J'`）
7. ⇒ **`SvProfilePatchLoadOnly`**（= `'K'`）
8. ⇒ **⇒ 所以【`'J'` 与 `'K'` 是两个动词**】
```

### 5.3 ⭐⭐⭐ **"`'K'` 装载而不重建，那正是一个分裂的更新在线上看起来的样子"**

**✅ 这与 §433 的"只在最后一条写 `J`"**——**完全闭合** ✓

**⇒ 三层**：
```text
正确：**第一条 `'K'`（装载，不重建）+ 最后一条 `'J'`（装载 + 重建）**
错误：**每条都 `'J'`** ⇒ **每条都重建** ⇒ **半装载**
⇒ **⇒ 所以【`'K'` 的存在【正是为了**避免每条都重建**】
```

**✅ ⭐⭐⭐ **一个"两个动词"的完整功能解释**。

**⇒ 三层**：
```text
`SvProfilePatchLoadOnly`（`'K'`）⇒ **装载**
`SvProfilePatchLoadAndRebuild`（`'J'`）⇒ **装载 + 重建**
⇒ **⇒ 所以【一条分片更新 = `K`...`K` `J`**】
```

**✅ ⭐⭐ **"`K`...`K` `J`"** —— 一个**分片协议的完整形态**。

**⚠ 而"诊断显示 `!J 1234`"⇒ **一个可读的日志格式**。**

**✅ 与 §425 的 `trace-budget-exhausted`**不同（这是**一个内容格式**）。

## 六、**`activateBotSlot` 的"两个保持客户端活着的不变式"**

### 6.1 那段（开头）

```cpp
// OLMOD(bot-client-p2a): build 1 of the bot surface -- a stationary
// second player, no AI. This function only builds the SLOT; the world
// spawns it, exactly as it spawns a player, off the fields set below.
if (clientNum >= clients_.size()) return false;
auto &client = clients_[clientNum];
if (client.state != ClientState::Free) return false;
// THE TWO INVARIANTS THAT KEEP THE CLIENT ALIVE, both read off the frame
```

**⇒ 六层**：
```text
1. **bot 表面的 build 1 —— 一个静止的第二玩家，无 AI**
2. ⇒ **这个函数【只构建那个槽**】**
3. ⇒ **世界【出生它**】，**就像它出生一个玩家**】
4. ⇒ **⇒ 从【下面设的字段**】**
5. ⇒ **而【两个保持不变式【保持客户端活着**】**（**都从那个帧读出**）
```

**✅ 而"只构建槽"⇒ **一个清晰的职责分离**。**

**✅ 与 §421 的"`ReliableCommandSender` 的注入 ⇒ 世界层不知道命令文本"**同族（**第五次"职责分离"）。

**⇒ 三层**：
```text
§421  **世界层只发,不构造**
§433  **`queueScoreboardResponse` 只构建命令**
§436  **`activateBotSlot` 只构建槽**
⇒ **⇒ 三次"只做一件事**】
```

**✅ ⭐ **一个"单一职责"的三例表**。

**⚠ 而"两个不变式"⇒ **在下一段（未读）。**

## 七、**`clientIngressStatus` 的四十个字段**

**⇒ 五层**：
```text
1. **一个 `ClientIngressStatus` 有【约四十个字段**】**
2. ⇒ **覆盖**：`peer`/`xuid`/`name`/`state`/`profileStats`/`gameStateUpdateStage`/`sessionGeneration`/`lastPacketTime`
3. ⇒ **加**：`incomingSequence`/`outgoingSequence`/`messageAcknowledge`/`reliableAcknowledge`/`deltaMessage`
4. ⇒ **加**：`snapshotAssemblyFailure`/`Attempts`/`Failures`
5. ⇒ **加**：`lastReceived`/`Dispatched`/`Executed`/`Discarded*`/`Dropped*` **五个 userCmd 状态**
6. ⇒ **加**：`gameplayState`/`selectedLoadout`/`loadoutSequence`/`spawnSequence`/`characterFaction`/`team`/`pending*`
7. ⇒ **加**：`acceptedPackets`/`duplicatePackets`/`rejectedPackets`/`lastPacketReject`/`decodedCommandsSize`/`Prefix`
```

### 7.1 ⭐⭐ **"五个 `userCmd` 状态"**

```text
lastReceivedUserCmd
lastDispatchedUserCmd
lastExecutedUserCmd
lastDiscardedUnsupportedUserCmd + 计数
lastDiscardedRejectedUserCmd   + 计数
lastDroppedOverflowUserCmd     + 计数
```

**⇒ 六层**：
```text
1. **`Received`** ⇒ **到达**
2. ⇒ **`Dispatched`** ⇒ **出队**
3. ⇒ **`Executed`** ⇒ **执行成功**
4. ⇒ **`DiscardedUnsupported`** ⇒ **因不支持的客户端事件丢弃**
5. ⇒ **`DiscardedRejected`** ⇒ **因 think 拒绝丢弃**
6. ⇒ **`DroppedOverflow`** ⇒ **因队列满丢弃**
⇒ **⇒ 所以【一条命令有【六个可能的状态**】】
```

**✅ 与 §404 的"`SV_ShouldDiscardRejectedUserCmd` 六种"**完全闭合 ✓

**⇒ 三层**：
```text
§404  六种**失败阶段**是"可丢弃"的
§436  **六个**命令生命周期状态**
⇒ **⇒ 两个"六"是不同的东西**
```

**✅ ⭐ **一个"两个六"的澄清**。

## 八、关键结论

1. **⭐⭐⭐ "从 `1` 开始扫描，让槽 `0` 每次都留给那个玩家"`**：**测量 `2026-10-11 00:02:31` 的 `BOTTRACE|slot-create client=0..3` —— bot 拿走了主机自己的槽，而他然后被拒为 `the session roster client slot is occupied`（玩家看成"房间已满"）** —— **与 §433 是同一个症状的【两个不同来源**】（第八次"多因歧义"）。
2. **⭐⭐ "槽 `0` 的保留只在 `freeClientSlot` 里，因为只有 bot 分配调用它 ⇒ 一个真实玩家的连接不受影响 ⇒ 一个单向的保留"`** —— 第四个"单向规则"。
3. **⭐⭐⭐ `connectTime` 在重连时【保留】而 `lastPacketTime`/`nextSnapshotTime` 【重置】**：**`connectTime` 是 §435 的 `500ms` 宽限的起点，`lastPacketTime` 是超时的判据，`nextSnapshotTime` 是调度状态** ⇒ **一个语义分工的精确定位**；而**一个重连的客户端不重置宽限**（可能有意，也可能是疏漏）。
4. **⭐⭐ "`nextSnapshotTime` 是从 `svs.time` 初始化的【调度状态】，不是一个『零意味着立刻到期』的哨兵"`** —— 与 §413 的同一理由（**零初始化在 `INT32_MAX` 之后破坏环绕安全的比较**）。
5. **⭐⭐⭐ "零不是中性值"的第六例** —— 本报告最完整的归纳：`nextSnapshotTime = 0`（立刻到期）/ `team = 0`（AV）/ `field00E4 = 0`（索引 `0`）/ `distance = 0`（非 delta 分支）/ `viewmodelIndex = 0`（AV）。
6. **⭐⭐ `EXE_SERVERISFULL` 的两条不同消息**（`"the session roster client slot is occupied"` 与 `"all CODOL client slots are occupied"`）⇒ **加上 §433 的"先连的占错槽"** ⇒ **三条路径通向同一个"房间已满"框** —— 第五次"分支各自命名"。
7. **⭐ `duplicateIdentity` 的"同一 XUID 来自不同 peer"⇒ `EXE_BAD_CHALLENGE`**（不是 `EXE_SERVERISFULL`）⇒ **一个身份唯一性的检查**。
8. **⚠ 一个可能的不一致**：§435 的 `findChallenge` **只比 IP 不比端口**，而 `existing` 用 `client.peer == peer`（**可能含端口**）⇒ **端口变化时两者行为不同**（需核对 `PeerAddress::operator==`）。
9. **⭐⭐⭐ `'K'`（`SvProfilePatchLoadOnly`）与 `'J'`（`SvProfilePatchLoadAndRebuild`）是两个动词**，而 **"`'K'` 装载而不重建，【那正是一个分裂的更新在线上看起来的样子】"`** —— 与 §433 的"只在最后一条写 `J`"完全闭合：**一条分片更新 = `K`...`K` `J`**。
10. **⭐ 诊断显示 `!J 1234` 这样的"动词 + 大小"格式**（因为 payload 是不透明字节）。
11. **⭐ `activateBotSlot` 的"只构建槽；世界出生它，就像它出生一个玩家"`** —— 第三次"单一职责"。
12. **⭐ `ClientIngressStatus` 的约四十个字段，其中【六个 `userCmd` 生命周期状态**】（`Received` / `Dispatched` / `Executed` / `DiscardedUnsupported` / `DiscardedRejected` / `DroppedOverflow`）。

## 九、未闭合点

- `PeerAddress::operator==` 是否含端口。
- `activateBotSlot` 的"两个不变式"（下一段）。
- `SvProfilePatchLoadOnly` / `SvProfilePatchLoadAndRebuild` 的字节值。
- `connectTime` 在重连时保留是否有意。
- `sv_client_mp.cpp` 4160 行之后未读取（**共 `4500` 行**）。
