# 347 · **"位 0x02 是客户端离开 `CA_PRIMED` 的门票而这服务器从未设过它"** —— `cls.state 9` 与 `XBOXLIVE_CANTJOINSESSION 46s`、两个极端的实测、样本普查

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 9998–10798 行。

## 二、`writeExplicitAnimationCommand` 的**三段拼接**（本组第四重要）

### 2.1 完整

```cpp
message.MSG_WriteBits(0, 1);            // explicit record, not baseline reuse
writeAnimationCommandSelector(message, 3);   // → 1; BITS(2)=2 → type 3
message.MSG_WriteBits(command.entityNum, 11);        // sticky target entity
writeAnimationCommandSelector(message, 4);   // → 0 1; BITS(2)=3 → type 4（共享时间码）
if (serverTime >= command.time && serverTime - command.time <= 0xFF) {
    message.MSG_WriteBits(0, 1);
    message.MSG_WriteBits(serverTime - command.time, 8);
} else {
    message.MSG_WriteBits(1, 1);
    message.MSG_WriteLong(command.time);
}
if (command.type == ClearTree) {
    writeAnimationCommandSelector(message, 9);    // → 0 0 1; BITS(2)=0
    message.MSG_WriteBits(0, 1);                 // 6714D0: blend .2
    return !message.overflowed();
}
writeAnimationCommandSelector(message, 1);        // → 1; BITS(2)=0 → type 1
message.MSG_WriteBits(command.flags, 2);
if (aliasBits) message.MSG_WriteBits(aliasIndex, aliasBits);
message.MSG_WriteBits(0, 1);
message.MSG_WriteBits(command.weight == 1.0f ? 1 : 0, 1);
message.MSG_WriteBits(0, 1);     // 6714D0: blend .2
message.MSG_WriteBits(0, 1);     // 671550: rate 1
```

### 2.2 五层

```text
1. **每个记录以一个 0 位开头**（"显式记录，不是基线复用"）
2. ⇒ **selector 3 = 实体号**（11 位 sticky）
3. ⇒ **selector 4 = 时间**（9 或 33 位）
4. ⇒ **`ClearTree` ⇒ selector 9 然后一个 0 位就结束**
5. ⇒ **`SetGoalWeight` ⇒ selector 1 + flags(2) + [alias] + 三个 0 位**
```

### 2.3 而**三个 0 位是"最便宜的合法编码"**

```text
0        权重（不是"从 0 到 1"?）
weight   权重值（1.0 或 0.0）
0        blend 0.2s（`6714D0` 的位 0 = 0.2）
0        rate 1.0（`671550` 的一位支直接返回 1.0）
```

**✅ 与 §346 的"`0x6714D0`/`0x671550`"**完全一致 ✓**

### 2.4 而 `SV_WriteAnimationCommands` 的**对齐表**

```cpp
message.MSG_WriteBits(1, 1);                        // section present
message.MSG_WriteBits(aliases.empty() ? 0 : 1, 1);  // alias table follows
if (!aliases.empty()) {
    message.MSG_WriteByte((uint8)aliases.size());
    for (alias : aliases) message.MSG_WriteBits(alias, 12);
}
const auto aliasBits = aliases.size() <= 1 ? 0u
    : std::bit_width((uint32)(aliases.size() - 1));
const auto baselineBits = baseline && !baseline->empty()
    ? (baselineWidth ? baselineWidth : 1u) : 0u;
```

### 2.5 四层

```text
① 段存在位 + 表跟随位
② **字节计数** + 每个 12 位别名
③ **`aliasBits = bit_width(size - 1)`**（`size <= 1` ⇒ 0）
④ **基线宽度同样推导**（而空基线 ⇒ 0；有一个 ⇒ **最小 1 位**）
```

**✅ 与 §345 的"`aliasBits` 由 count 推导"**同族。**

**⚠ 而 `baselineBits` 的**最小 1 位**与 `aliasBits` 的**0** 不同：**

```text
aliasBits      size <= 1 ⇒ 0
baselineBits   size == 1 ⇒ bit_width(0) = 0 ⇒ 但强制为 1
```

**⚠ 所以**两个推导对 size==1 的处理不同**。**

**⇒ 可能因为 `baselineBits == 0` 会让"基线复用"标记无法携带索引。**

**✅ 一个**必要的例外**。**

### 2.6 而**终止序列**

```cpp
message.MSG_WriteBits(0, 1);                   // not a baseline reuse
writeAnimationCommandSelector(message, 5);     // end of list → 0 1; BITS(2)=0
```

**⇒ 三层**：

```text
1. 一个 0 位（不是复用）
2. ⇒ **selector 5（第二臂，`0 1` + 2 位 0）**
3. ⇒ **解码成 5 = 结束**
```

**✅ 与 §346 的"列表以 selector 5 结束"**完全一致 ✓**

### 2.7 而**512 的上限**

```cpp
if (commands.size() > 512 || ... ) return false;
```

**✅ 与 §346 的"`cl_parse_packet_anims` 的 512 记录环"**完全一致 ✓**

**⇒ **第二次确认 512。**

## 三、`SV_RecordPredictedFieldsMode` 的**每客户端计数**（本组第五重要）

### 3.1 那段

```php
// THE PREDICTED-FIELDS MODE, COUNTED PER CLIENT, BECAUSE THE WHOLE
// POINT OF MAKING IT A DECISION IS A NUMBER.
//
// Retail's dm demo sets this bit on 781 of 6160 snapshots -- 12.7%.
// This server set it on 4239 of 4239. This reports the CONDITION and
// not just the outcome, because the ways it can go wrong are
// different faults: command times that never match mean the client's
// reported prediction is not the clock we think it is, while command
// times that match with a large worst-case distance means our pmove
// and the client's have genuinely diverged.
```

### 3.2 十层

```text
1. **预测字段模式，按客户端计数，因为把它做成一个决定的整个意义是一个数字**
2. ⇒ **零售 dm demo 在 6160 个快照里的 781 个上设这个位 —— 12.7%**
3. ⇒ **这个服务器在 4239 / 4239 上设它 —— 100%**
4. ⇒ **这报告【条件】而不只是结果**
5. ⇒ **因为出错的方式是不同的故障**
6. ⇒ **命令时间从不匹配 ⇒ 客户端报告的预测不是我们以为的那个时钟**
7. ⇒ **命令时间匹配而最坏距离很大 ⇒ 我们的 pmove 与客户端的真的分叉了**
```

### 3.3 **`781/6160 = 12.7%` vs `4239/4239 = 100%`**

**✅ 一个**极端的对照**。**

**⚠ 所以本服务器**总是**用预测字段而零售只用 12.7%。**

**⇒ **8 倍过量**。**

**来源？**

**✅ 与 §331 的"`OLMOD_SWAY_PHASE` 是狙击镜抖动的真修复"可能相关（预测字段包含 sway phase）。**

### 3.4 而**六个计数器**

```text
frames                    总帧数
modeZero                  未发预测字段的帧
commandTimeMatches        命令时间匹配的帧
noPrediction              预测不可用的帧
weaponPositionForced      被武器位置强制的帧
worstMatchedDistanceSquared  匹配时最坏距离平方
```

**✅ 六个，而 `worstMatchedDistanceSquared` 是**取最大值**。**

### 3.5 而 `PredictedModeReportInterval = 600`

**⇒ 三层**：

```text
1. 每 600 帧报一次
2. ⇒ 50ms/帧 ⇒ **600 帧 = 30 秒**
3. ⇒ **而报告后重置**
```

**✅ 一个**30 秒的窗口**。**

### 3.6 而**格式**

```text
"predicted-mode client=%u frames=%u mode0=%u (%.1f%%) ctMatch=%u worstDist=%.4f noPred=%u weaponForced=%u"
```

**✅ 七项。**

## 四、**`SV_PresentableTeam` 的"只有 1 和 2 解析"**（本组第六重要）

```cpp
SvTeam SV_PresentableTeam(SvTeam team, const std::optional<SvCharacterCustomization> &customization)
{
    // Only 1 and 2 resolve on the client. Everything else -- None from
    // free-for-all, Spectator -- has to be presented as one of them.
    if (team == SvTeam::Tf || team == SvTeam::Sc) return team;
    return customization && customization->faction == SvCharacterFaction::Sc
        ? SvTeam::Sc : SvTeam::Tf;
}
```

### 4.1 五层

```text
1. **只有 1 与 2 在客户端解析**
2. ⇒ **其它一切 —— 自由混战的 `None`、`Spectator` —— 必须被呈现为其中之一**
3. ⇒ `Tf`（1）与 `Sc`（2）原样
4. ⇒ **否则看 `customization->faction` 决定**
5. ⇒ **无 customization ⇒ `Tf`**
```

**✅ 与 §337 的"`team` 从 3 位变 11 位"**配合 —— 11 位能装很多值但**只有 2 个有效**。**

**⚠ 而 §337 说"`CL_ParsePacketClients` 从一个 `0x58` 字节行初始化而它的 `team` 是 `Sc`（2）"。**

**⇒ 所以默认是 **2**，而这里无 customization 时选 **1**。**

**⚠ 一处**不一致**。**

**⇒ 可能因为 §337 是**新行初始化**而这里是**呈现**。**

**✅ 两个不同的语境。**

## 五、**`SNAPSHOT BASELINE MISMATCH` 的线半**（本组第三重要）

### 5.1 那段

```php
// THE ONE INVARIANT THIS WIRE HAS, AND IT IS WORTH AN INSTRUMENT (section 169).
// out.exe resolves ONE baseline for every section of a snapshot, from two wire
// facts only -- the distance byte and SnapshotBaselineFlag (CL_ParseSnapshot
// 0x0047222E..0x00472268). It uses an EMPTY baseline if and only if the distance
// is zero AND the flag is set. If this server ever encodes a section against an
// empty baseline without setting that flag, the client XORs our absolute values
// against the values it already holds and lands on ZERO -- modelIndex 0,
// CG_SetupClientCharacterInfo's early return at 0x00541814, no model name written,
// and BG_UpdatePlayerDObj refuses the living player at 0x0040ABD2.
```

### 5.2 十一层

```text
1. **这条线只有的【一个】不变量，而它值得一个仪器（第 169 节）**
2. ⇒ **`out.exe` 为一个快照的【每一个段】解析【一个】基线**
3. ⇒ **只从两个线事实：距离字节与 `SnapshotBaselineFlag`**
4. ⇒ **（`CL_ParseSnapshot` `0x0047222E..0x00472268`）**
5. ⇒ **它用【空】基线【当且仅当】距离为零【且】标志置位**
6. ⇒ **如果这个服务器对着一个空基线编码一个段【而不设那个标志】**
7. ⇒ **客户端把我们的绝对值对它所持有的值 XOR 而落在【零】上**
8. ⇒ **`modelIndex` 0**
9. ⇒ **`CG_SetupClientCharacterInfo` 在 `0x00541814` 的早退**
10. ⇒ **不写模型名**
11. ⇒ **而 `BG_UpdatePlayerDObj` 在 `0x0040ABD2` 拒绝活着的玩家**
```

### 5.3 **"一个快照的每一个段解析一个基线"**

**✅ 与 §347 的"`clientInfos` 段没有逐条'全量编码'位"**完全一致 ✓**

**⇒ 三层**：

```text
1. 基线是【消息级】的
2. ⇒ **段级无法覆盖**
3. ⇒ **所以任何段级"强制全量"都是错的（§347 七）**
```

**✅ **一个极清晰的不变量。**

### 5.4 而**三个可分辨的失败**

```cpp
const bool emptyBaselineOnWire = baseline == nullptr;
const bool flagDisagrees = emptyBaselineOnWire != initializeBaselineCache;
const bool distanceDisagrees = emptyBaselineOnWire && deltaMessageDistance != 0;
if (flagDisagrees || distanceDisagrees) { /* log */ }
```

**⇒ 三层**：

```text
① 空基线而标志未设 ⇒ 不一致
② 非空基线而标志设了 ⇒ 不一致
③ 空基线而距离非零 ⇒ 不一致
```

**✅ "每个析取项可以分别从打印的字段识别" ✓**

### 5.5 而**"这是线半，而它对另一半是盲的"**

```php
// THIS IS THE WIRE HALF ONLY, AND IT IS BLIND TO THE OTHER ONE (section 170). It
// can see that the distance byte and SnapshotBaselineFlag agree with `baseline`.
// It cannot see whether a flagged baseline is the newest flagged frame that
// client holds, because SV_WriteSnapshot is given one frame pointer and no
// history -- and a stale flagged baseline is perfectly well-formed here while
// decoding every entity row out of the wrong generation of the client's flat
// array (sub_470E90 0x00470e97, cursor reset 0x00472223). That half is asserted
// in SvClientSystem's snapshot assembly under kind=entity-generation; grep
// "SNAPSHOT BASELINE MISMATCH" to get both.
```

### 5.6 九层

```text
1. **这只是线半，而它对另一半是【盲】的**
2. ⇒ **它能看见距离字节与 `SnapshotBaselineFlag` 与 `baseline` 一致**
3. ⇒ **它【不能】看见一个被置标志的基线是不是那个客户端持有的最新的被置标志的帧**
4. ⇒ **因为 `SV_WriteSnapshot` 拿到的是一个帧指针而没有历史**
5. ⇒ **而一个【陈旧】的被置标志的基线在这里是【完全良构】的**
6. ⇒ **而在从客户端平坦数组的【错误代际】解码每一个实体行**
7. ⇒ **（`sub_470E90` `0x00470e97`，游标重置 `0x00472223`）**
8. ⇒ **那一半在 `SvClientSystem` 的快照装配里以 `kind=entity-generation` 断言**
9. ⇒ **`grep "SNAPSHOT BASELINE MISMATCH"` 得到两者**
```

**✅ 一个**"我知道我的仪器看不见什么"**的极成熟陈述。**

**⇒ 与 §340 的"定向的负面"**同族但更强**（**主动说出仪器的盲区**）。**

### 5.7 而**去重手法**

```cpp
static std::array<std::size_t, MaximumGameClients> reportedMismatch{};
const auto digest = std::hash<std::string>{}(line);
if (clientNum < reportedMismatch.size() && reportedMismatch[clientNum] != digest) {
    reportedMismatch[clientNum] = digest;
    OlMod::RuntimeLog::write(..., line);
}
```

**⇒ 四层**：

```text
① 每客户端一个摘要
② ⇒ **`std::hash<string>`**
③ ⇒ **只在摘要变化时写**
④ ⇒ **所以每个客户端每种不同的错只报一次**
```

**✅ 与 §346 的 `psDomainBad`（全局 `static string`）与 `entity_domain`（全局 `set`）**第三个去重实现**。**

**⚠ 但这一个**按客户端索引**（最好）。**

**⇒ 三种去重、三种粒度。**

## 六、**位 `0x02` 是客户端的 `CA_PRIMED` 出口**（本组最重要的一段）

### 6.1 那段

```php
// BIT 0x02 IS THE CLIENT'S TICKET OUT OF CA_PRIMED, AND THIS SERVER HAS NEVER
// SET IT.
//
// re/OLFINAL-INGAME-BRINGUP.md section 2: `sub_515C90` is CL_FirstSnapshot, it
// sets cls.state to 10 at 0x515DAE, and it is "gated ONLY on `snap.snapFlags & 2`".
// `snapshot_.flags` is assigned 0 and never touched again, so the only bits this
// server puts on the wire are 0x08 (baseline) and 0x10 (entity baselines). A
// client that never receives 0x02 stays at cls.state 9 forever -- which is
// section 3a's description exactly: "no netchan packets at all, only a 2-byte
// keepalive at 1 Hz, because a CA_PRIMED client is waiting for its first
// snapshot".
//
// MEASURED on mp_battlecity 2026-09-04: the dedicated logs the 2-byte keepalive
// as `netchan packet too short: 2 bytes, minimum 5`, the client sends ~65 packets
// and then stops, produces no `pmove-slice`, never acks (`cacheAcked=0` forever,
// so every frame stays `source=none(FULL)`), and times out on
// XBOXLIVE_CANTJOINSESSION after 46 s. All of that is one client stuck at 9.
//
// ON THE FIRST FRAME ONLY, which is what CL_FirstSnapshot is. It rides
// `initializeBaselineCache` -- the no-baseline frame -- because that is the frame
// the client has nothing prior for. Costs nothing on the render side: cgame
// already discards frames whose flags meet SnapshotSceneBlockFlags (0x0A) and
// this frame carries 0x08 regardless.
//
// WHY mp_nuked WORKS WITHOUT IT IS NOT ESTABLISHED -- it may reach cls.state 10
// by another route, which is why this has a kill switch rather than a rewrite:
// OLDMOD_SNAPSHOT_ENTRY_FLAG=0 restores the old byte exactly.
```

### 6.2 十八层

```text
1. **位 `0x02` 是客户端离开 `CA_PRIMED` 的门票，而这个服务器【从未】设过它**
2. ⇒ `re/OLFINAL-INGAME-BRINGUP.md` 第 2 节：**`sub_515C90` 是 `CL_FirstSnapshot`**
3. ⇒ **它在 `0x515DAE` 把 `cls.state` 设为 10**
4. ⇒ **而它"只被 `snap.snapFlags & 2` 门控"**
5. ⇒ **`snapshot_.flags` 被赋 0 而之后从未再被碰过**
6. ⇒ **所以这个服务器放到线上的唯一位是 `0x08`（基线）与 `0x10`（实体基线）**
7. ⇒ **一个从未收到 `0x02` 的客户端永远停在 `cls.state 9`**
8. ⇒ **而那正是第 3a 节的描述："完全没有 netchan 包，只有一个 1 Hz 的 2 字节心跳，因为一个 `CA_PRIMED` 客户端在等它的第一个快照"**
9. ⇒ **在 `mp_battlecity` 上 2026-09-04 实测**：
     · **专用服务器把那个 2 字节心跳记成 `netchan packet too short: 2 bytes, minimum 5`**
     · **客户端发约 65 个包然后停**
     · **不产生 `pmove-slice`**
     · **从不应答（`cacheAcked=0` 永远，所以每一帧停在 `source=none(FULL)`）**
     · **46 秒后在 `XBOXLIVE_CANTJOINSESSION` 上超时**
10. ⇒ **所有这些都是【一个客户端卡在 9】**
11. ⇒ **只在第一帧，而那正是 `CL_FirstSnapshot`**
12. ⇒ **它搭乘 `initializeBaselineCache` —— 那个无基线的帧**
13. ⇒ **因为那是客户端没有前驱的帧**
14. ⇒ **渲染侧零代价**：cgame 已经丢弃 flags 命中 `SnapshotSceneBlockFlags`（`0x0A`）的帧，而这帧反正携带 `0x08`
15. ⇒ **为什么 `mp_nuked` 不需要它【没有确立】**
16. ⇒ **它可能通过另一条路到达 `cls.state 10`**
17. ⇒ **那就是为什么这有一个死亡开关而不是一次重写：`OLMOD_SNAPSHOT_ENTRY_FLAG=0` 精确恢复旧字节**
```

### 6.3 **"五个实测症状，一个根因"**

```text
① netchan packet too short: 2 bytes, minimum 5
② 客户端发约 65 个包然后停
③ 不产生 pmove-slice
④ cacheAcked=0 永远 ⇒ source=none(FULL)
⑤ 46 秒后 XBOXLIVE_CANTJOINSESSION 超时
```

**✅ 与记忆里的"战斗服 world 从未绑定"**不同**（那是服务端的空指针）。**

**⚠ 而"46 秒"是一个**极具体的数字**。**

**✅ 与记忆的"本体 6 秒必崩 = enable_iips=0"**不同**（那是客户端崩溃，这是客户端卡住）。**

**⇒ **两个不同的失败模式**。**

### 6.4 而 **`SnapshotSceneBlockFlags = 0x0A`**

**⇒ 三层**：

```text
1. `0x0A = 0x08 | 0x02`
2. ⇒ **cgame 丢弃携带 0x08 或 0x02 的帧**
3. ⇒ **所以入场帧被丢弃（不渲染）**
```

**✅ 一个**优雅的"入场帧不渲染"机制**。**

**⚠ 而 `0x0A` 来自 `0x08 | 0x02`。**

**⇒ 与 §346 的 `if (frame.flags & SnapshotSceneBlockFlags) return reject(SceneFlags)` **配合。**

**⚠ 所以 `SV_ValidateSnapshotFrame` **拒绝**携带 `SceneFlags` 的帧。**

**⇒ 但这里说**cgame** 丢弃渲染。**

**⇒ 两个不同的"丢弃"（服务端准入 vs 客户端渲染）。**

**⚠ 一处需要区分。**

**⇒ 可能 `SnapshotSceneBlockFlags` 在服务端也有**另一个含义**（`frame.flags` 由生产者设置，而服务端拒绝它）。**

### 6.5 而**"两个极端都是错的"**（本组最重要的第二段）

```php
// REPEAT UNTIL IT TAKES, THEN STOP. Both extremes were measured on mp_battlecity
// and both are wrong:
//
//   every FULL frame   the client ACKED for the first time ever (cacheAcked 0->1)
//                      but then oscillated rearm/FULL with deltaMessage frozen --
//                      each repeat restarts CL_FirstSnapshot instead of finishing
//   exactly once       the client never acked at all (cacheAcked=0), because the
//                      one announcement lands while it is still loading the map
//                      and there is no second chance
//
// So the flag has to persist until the client demonstrably enters, and then stop.
// `baseline != nullptr` IS that demonstration: a baseline only exists once the
// client has acknowledged a frame
```

### 6.6 十层

```text
1. **重复直到它生效，然后停止**
2. ⇒ **两个极端都在 `mp_battlecity` 上被测量，而两个都是错的**：
3. ⇒ **每一帧 FULL**：**客户端第一次应了（`cacheAcked 0→1`）但然后 `rearm`/`FULL` 振荡而 `deltaMessage` 冻结**
4. ⇒ **每一次重复都重起 `CL_FirstSnapshot` 而不是完成它**
5. ⇒ **恰好一次**：**客户端从不应答（`cacheAcked=0`）**
6. ⇒ **因为那一次公告落在它还在加载地图的时候而【没有第二次机会】**
7. ⇒ **所以标志必须持续直到客户端【证明】进入，然后停止**
8. ⇒ **`baseline != nullptr` 【就是】那个证明**
9. ⇒ **因为一个基线只在客户端已经确认了一帧之后才存在**
10. ⇒ **（日志为 `rearm(flagged-baseline)` 与 `acked` 都打印 `cacheAcked=1`，只为 `source=none(FULL)` 打印 `cacheAcked=0`）**
```

### 6.7 **"两个极端都错"是本文件最珍贵的形态**

**✅ 与 §343 的"`bump` 从约定变结构"、§346 的"两条 3.3.3.3 规则"**同族。**

**⇒ 而这里是**两个方向都试过并都测了**。**

**✅ **一个完整的实验记录。**

**⚠ 而"`baseline != nullptr` 是那个证明"是一个**极优雅的状态推导**。**

**⇒ 与 §345 的"`baseline ? 0 : 1` 恰好意味着新实体"**同族。**

**⇒ **第二次"用已有状态推导语义"。**

### 6.8 而**两个 `static` 数组 + 门**

```cpp
static std::array<bool, MaximumGameClients> clientEntered{};
constexpr uint8 SnapshotFirstSnapshotFlag = 0x02;
if (baseline && clientNum < clientEntered.size() && !clientEntered[clientNum]) {
    clientEntered[clientNum] = true;
    OlMod::RuntimeLog::write(..., "snapshot ENTRY FLAG 0x02 withdrawn for client ...");
}
const auto sendEntryFlag = initializeBaselineCache && !entryFlagDisabled &&
    clientNum < clientEntered.size() && !clientEntered[clientNum];
{
    static std::array<bool, MaximumGameClients> announced{};
    if (sendEntryFlag && clientNum < announced.size() && !announced[clientNum]) {
        announced[clientNum] = true;
        OlMod::RuntimeLog::write(..., "snapshot ENTRY FLAG 0x02 arming for client ...");
    }
}
```

**⇒ 五层**：

```text
① `clientEntered` ⇒ 一旦有基线就永久置位
② ⇒ **并记一行 "withdrawn"**
③ ⇒ **`sendEntryFlag` = 无基线 && 未禁止 && 未进入**
④ ⇒ `announced` ⇒ **只记一次 "arming"**
⑤ ⇒ **两个数组都是进程生命期**
```

**✅ 与注释的"进程生命期的锁存足够"一致。**

**⚠ 而注释**两次**重复"进程生命期的锁存足够"（一次在 10474 一次在 10495）。**

**⇒ 一处**重复的注释**（可能是两次编辑的遗留）。**

**✅ 与 §338 的"三条遗留注释"同族（**第二次**）。**

### 6.9 而**"如果一次专用服务器服务两场比赛而不重启"**

```php
// A PROCESS-LIFETIME LATCH IS ENOUGH HERE. The dedicated is a fresh process on
// every cycle, so there is nothing to reset between connections in practice. If
// that ever stops being true -- a dedicated serving two matches without a restart
// -- this needs clearing when a slot is reused, and the symptom would be a second
// client that never leaves CA_PRIMED.
```

**⇒ 四层**：

```text
1. **进程生命期的锁存在这里足够**
2. ⇒ **专用服务器每个周期是一个新进程**
3. ⇒ **如果那不再是真 —— 一个服务两场比赛而不重启**
4. ⇒ **这需要在槽被复用时清理，而症状会是【第二个永不离开 `CA_PRIMED` 的客户端】**
```

**✅ 一个**明确的"何时会坏"**陈述。**

**⚠ 而 `frame.flags` 的头部组装：**

```cpp
message.MSG_WriteByte(frame.flags
    | (initializeBaselineCache ? SnapshotBaselineFlag : 0)
    | (sendEntryFlag ? SnapshotFirstSnapshotFlag : 0)
    | (useEntityBaselines ? SnapshotUseEntityBaselinesFlag : 0));
```

**⇒ 四个位或：**

```text
frame.flags                      （生产者设置）
SnapshotBaselineFlag = 0x08
SnapshotFirstSnapshotFlag = 0x02   ← 新加
SnapshotUseEntityBaselinesFlag = 0x10
```

**✅ 与注释的"只有 0x08 与 0x10"**对照** —— 现在有 `0x02`。**

**⇒ 所以 §347 的修改是**新增**。**

## 七、**`clientInfos` 段绝不能对着段级空基线写**（本组第二重要）

### 7.1 那段

```php
// EVERY SECTION USES THE MESSAGE'S OWN BASELINE (section 169). The clientInfos
// wire has no per-entry "encoded in full" bit -- writeClientInfos emits a client
// number and one removed bit and nothing else -- so unlike the playerstate (its
// own selector bit, written a few lines above) and entities (the per-entity new
// flag), this section CANNOT tell the client it was written against an empty
// baseline. It must therefore never be written against one unless the whole
// message was, which is what SnapshotBaselineFlag announces.
//
// This used to be `baseline && !forceFullClientInfos`, and that second term was a
// section-local empty baseline with nothing on the wire to declare it.
// CLIENTINFO IS NEVER WRITTEN AGAINST A SECTION-LOCAL EMPTY BASELINE. TRIED,
// AND IT IS THE DEFECT THIS FILE ALREADY DOCUMENTS.
//
// The theory was sound: the client applies clientinfo only while every frame is
// FULL (CA_PRIMED, discarding), then enters, a baseline appears, the entries
// compare equal and are OMITTED forever -- leaving it at model 0, which is
// exactly `req{ALL-ZERO (the modelIndex gate fired)}`. So a short window of
// forced-full clientinfo after entry looked like the fix.
//
// It is not, because this section has no per-entry "encoded in full" bit. The
// ONLY thing that tells the client the section was written full is
// SnapshotBaselineFlag on the WHOLE message. Withholding the baseline from just
// this section says "full" on our side and "delta" on the client's. The
// instrument next door named it on the first run --
// `clientinfo WIRE baseline=empty(UNFLAGGED)` -- which is the case its own
// comment calls the defect, and the reason the old `!forceFullClientInfos` term
// was removed. Measured 2026-09-04; do not add it back.
//
// If clientinfo really must be refreshed after entry, the message has to go out
// FULL as a whole (SnapshotBaselineFlag set), not this section alone.
```

### 7.2 十七层

```text
1. **每一个段使用【消息自己的】基线（第 169 节）**
2. ⇒ **`clientInfos` 线没有逐条的"全量编码"位**
3. ⇒ **（`writeClientInfos` 只发一个客户端号与一个 removed 位，仅此而已）**
4. ⇒ **所以不像 playerstate（它有自己的选择位，写在上几行）与 entities（逐实体新标志）**
5. ⇒ **这个段【不能】告诉客户端它是对着一个空基线写的**
6. ⇒ **所以它绝不能对着一个空基线写，除非【整个消息】是** —— 那是 `SnapshotBaselineFlag` 公告的
7. ⇒ **这过去是 `baseline && !forceFullClientInfos`**
8. ⇒ **而那个第二项是一个【段级】的空基线而没有线上任何东西来声明它**
9. ⇒ **`CLIENTINFO` 从不被对着一个段级空基线写。试过，而它正是本文件已经记录的那个缺陷**
10. ⇒ **理论是成立的**：客户端只在每一帧都 FULL 时应用 clientinfo（`CA_PRIMED`，正在丢弃）
11. ⇒ **然后进入，一个基线出现，那些条目比较相等而【永远被省略】** —— 让它停在 model 0
12. ⇒ **而那正是 `req{ALL-ZERO (the modelIndex gate fired)}`**
13. ⇒ **所以进入后一小段"强制全量 clientinfo"看起来是那个修复**
14. ⇒ **它不是**，因为这个段没有逐条"全量编码"位
15. ⇒ **唯一告诉客户端这个段是以全量写的，是整个消息上的 `SnapshotBaselineFlag`**
16. ⇒ **只从这个段扣留基线，在我们这边说"全量"而在客户端那边说"delta"**
17. ⇒ **隔壁的仪器在第一次运行就命名了它 —— `clientinfo WIRE baseline=empty(UNFLAGGED)` —— 那正是它自己注释称为缺陷的情况，而那是旧 `!forceFullClientInfos` 项被移除的原因。2026-09-04 实测；【不要】加回来**
```

### 7.3 **"理论成立而实现不可能"**

**✅ 与 §340 的"§82e 的诊断错而建议对"**相反**（那里是**诊断错建议对**，这里是**理论对实现不可能**）。**

**⇒ 两个**互补的"部分正确"**。**

### 7.4 而 **`clientinfo WIRE baseline=empty(UNFLAGGED)`**

**✅ 一个**具体的仪器输出**命名了缺陷。**

**⇒ 与 §344 的"`obituary WIRE`"、§345 的"`entity_domain reject`"**第四次"仪器命名缺陷"**。**

**⇒ 四种仪器：**

```text
§344  obituary WIRE num=...            到达写入器
§345  entity_domain reject num=700 ... 在验证处被拒
§346  SNAPSHOT BASELINE MISMATCH       线/状态不一致
§347  clientinfo WIRE baseline=empty   段级基线错误
```

**✅ **四个层次，四条日志。**

### 7.5 而**"不要加回来"**

**✅ 与 §347 六.9 的"进程生命期"**同族。**

**⇒ **明确的负面指令**（一个**未来维护者陷阱**）。**

**⚠ 本文件里"不要加回来"至少两处（这里是其一）。**

## 八、`ActorCommandDeliveryState` 的**每观察者投递状态**（本组第七重要）

```cpp
struct ActorCommandDeliveryState {
    bool initialized{};
    bool initializingBaseline{};
    uint32 lastServerTime{};
    std::array<uint64, EntityNumNone + 1u> delivered{};
};
static std::array<ActorCommandDeliveryState, MaximumGameClients> actorCommandDelivery{};
...
const auto newDeliveryGeneration = !commandDelivery->initialized ||
    frame.serverTime < commandDelivery->lastServerTime ||
    (initializeBaselineCache && !commandDelivery->initializingBaseline);
if (newDeliveryGeneration) commandDelivery->delivered.fill(0u);
```

### 8.1 五层

```text
1. **每个客户端一个投递状态**
2. ⇒ **`delivered[entityNum]` 是 64 位签名**
3. ⇒ **新代际的三个条件**：
     · 未初始化
     · **`serverTime` 倒退**（新地图/新局）
     · **`initializeBaselineCache` 而之前不是**
4. ⇒ **新代际 ⇒ 清空**
5. ⇒ **签名 = `(animIndex << 32) | animStartTime`**
```

**✅ 一个**精确的代际检测**。**

### 8.2 而**为什么"每观察者"**

```php
// Keep delivery ownership per observer: a command sent to one client says
// nothing about another client's animation tree.
```

**⇒ 三层**：

```text
1. **投递所有权按观察者**
2. ⇒ **发给一个客户端的命令对另一个客户端的动画树什么也不说**
3. ⇒ **所以状态必须每客户端**
```

**✅ 与 §345 的"实体基线是每客户端的"**同族。**

### 8.3 而**维护节奏的两个分支**

```cpp
if (deliveredCommands.empty() && !commandActors.empty()) {
    const auto tick = frame.serverTime / 50u;
    const auto slot = commandActors.size() <= 20u ? tick % 20u : tick % commandActors.size();
    if (slot < commandActors.size()) {
        const auto *actor = commandActors[slot];
        if (animFor(*actor) && animFor(*actor) < 4096u)
            deliveredCommands.emplace_back(actor, signatureFor(*actor));
    }
}
```

**⇒ 四层**：

```text
① 无变化而有 actor ⇒ 走维护
② ⇒ `serverTime / 50` = **帧号**
③ ⇒ **`size <= 20` ⇒ `% 20`，否则 `% size`**
④ ⇒ **每帧一个 actor**
```

**✅ 而 `50ms` 的除数是**快照间隔**（与 §347 的"快照 50ms 间隔"一致）。**

**⚠ 而"`size <= 20` ⇒ `% 20`" ⇒ 所以**最多 20 帧一轮**（= 1 秒）。**

**⇒ 与注释的"每秒一个 actor"配合。**

**✅ 与 §347 八.4 的"大约每 actor 每秒一对"**完全一致 ✓**

### 8.4 而**那个 55,591 的实测**

```php
// ROUGHLY ONE PAIR PER ACTOR PER SECOND, NOT ONE PER SNAPSHOT.
//
// MEASURED off C-2021-7-31[15-32-16]zm: 55,591 commands across 120 target
// entities in a ~20 minute match, i.e. about ONE PER ACTOR PER SECOND.
// The first cut of this section sent a pair every snapshot -- twenty a
// second, twenty-four times retail's rate -- and 12.77 saw an animation
// start and then appear frozen. Re-applying a command re-enters
// sub_789D00 every 50 ms, which is the shape of an animation that never
// gets to advance.
```

**⇒ 九层**：

```text
1. **大约每 actor 每秒一对，不是每快照一对**
2. ⇒ **在 `C-2021-7-31[15-32-16]zm` 上测量：55,591 个命令跨 120 个目标实体在一场约 20 分钟的比赛里**
3. ⇒ **即大约每 actor 每秒一个**
4. ⇒ **这个段的第一版每快照发一对**
5. ⇒ **每秒二十个，零售速率的二十四倍**
6. ⇒ **而 12.77 看到一个动画开始然后【看起来冻结】**
7. ⇒ **重新施加一个命令每 50ms 重入 `sub_789D00`**
8. ⇒ **那是"一个永远不会前进的动画"的形状**
```

**✅ 与 §331 的"把常数喂进动态逻辑出来还是常数"**同族（**第二次"频率错了看起来像冻结"**）。**

### 8.5 而**快照 50ms 的实测**

```text
consecutive command times 19300, 19350
```

**✅ 一个**精确的间隔**。**

**⇒ 20 Hz。**

## 九、**actor 动画树的完整链（12.122 → 12.158）**（本组第八重要）

### 9.1 **"这个段给一个 actor 它的动画树"**

```php
// THIS SECTION IS WHAT GIVES AN ACTOR ITS ANIMTREE. See SvActorSeedAnimTree
// and re/demo-re/20-zm-actor-lifecycle.md 12.75: applying any command to a
// DObj runs sub_7886D0, which creates the tree's ROOT NODE and writes its
// index to cell+4 -- the one field 12.74 measured as still zero on this
// server while every other link in the chain was already working.
```

**⇒ 五层**：

```text
1. **这个段是给一个 actor 它的 animtree 的东西**
2. ⇒ 见 `SvActorSeedAnimTree` 与 `re/demo-re/20-zm-actor-lifecycle.md` 12.75
3. ⇒ **对 DObj 施加任何命令会跑 `sub_7886D0`**
4. ⇒ **它创建树的【根节点】并把它的索引写到 `cell+4`**
5. ⇒ **那个 12.74 测到在本服务器上仍为零的字段，而链上其它每一环都已经在工作**
```

**✅ 与记忆里的"battle server world 从未绑定 ⇒ 实体层整条是死的"**不同**（那是服务端，这是**客户端动画树**）。**

### 9.2 而**一个空别名表代价什么（12.153）**

```php
// 12.153 found what a one-entry null table costs. `record+20` is never
// on the wire: `sub_540040` resolves it CLIENT-SIDE, mapping
//     entity -> word_7855720[entity] -> unk_77E9720 + 216*idx (the tree)
//     -> sub_785870(tree, record+24) -> the animation KEY
// and it bails at `cmp [esi+18h],0 / cmp [esi+1Ch],0` when both alias
// fields are zero. A null alias therefore resolves to nothing, and the
// actor keeps the 0 or 2 the reader set -- one node, played once,
// frozen at playback 1.0 (12.122).
```

**⇒ 八层**：

```text
1. **12.153 发现一个只有一项的空别名表代价什么**
2. ⇒ **`record+20` 从不在线上**
3. ⇒ **`sub_540040` 在【客户端】解析它**，映射：
     · `entity -> word_7855720[entity] -> unk_77E9720 + 216*idx`（树）
     · `-> sub_785870(tree, record+24)` ⇒ **动画 KEY**
4. ⇒ **而它在 `cmp [esi+18h],0 / cmp [esi+1Ch],0` 处退出当两个别名字段都是零**
5. ⇒ **所以一个空别名解析成什么也没有**
6. ⇒ **而 actor 保留读者设的 0 或 2 —— 一个节点、播一次、冻结在 playback 1.0（12.122）**
```

**✅ 与 §340 的"`table+0x10` 零次引用 ⇒ 遍历器不存在"**同族（**第四次"定向的负面"**）。**

### 9.3 而 **"12.154 让别名解析而树从 2 个节点长到 8 个"**

```php
// 12.154 got the alias resolving and the tree grew from 2 nodes to
// 8: root -> 5 -> 152 -> 389 -> 409 -> 411 -> 495, with the walk
// asset on the leaf. The actors stayed in the bind pose, and the
// reason is that every node BETWEEN the root and the leaf carries
// zero weight and zero rate.
```

**⇒ 六层**：

```text
1. **12.154 让别名解析而树从 2 个节点长到 8 个**
2. ⇒ **`root -> 5 -> 152 -> 389 -> 409 -> 411 -> 495`**
3. ⇒ **而 walk 资产在叶子上**
4. ⇒ **actor 仍留在绑定姿势**
5. ⇒ **而原因是根与叶之间的每一个节点【携带零权重与零速率】**
```

**✅ 一个**具体的节点链**（七个节点名）。**

### 9.4 而 `sub_7886D0` 的**两个分支**

```php
// `sub_7886D0` creates them that way ON PURPOSE. Its root branch
// writes +40=1.0 +44=1.0 +48=1.0 +36=0.0; its LABEL_7 branch, the
// one that creates every intermediate container, writes +36..+52 as
// eight zero dwords. Nothing else in the module ever raises a
// container's goal weight -- `sub_7888B0` only lowers it to 0, and
// `sub_789570` is the only writer of a non-zero +40.
```

**⇒ 七层**：

```text
1. **`sub_7886D0` 故意那样创建它们**
2. ⇒ **它的根分支写 `+40=1.0 +44=1.0 +48=1.0 +36=0.0`**
3. ⇒ **它的 `LABEL_7` 分支（创建每一个中间容器的那个）把 `+36..+52` 写成八个零 dword**
4. ⇒ **模块里没有别的东西曾提高一个容器的目标权重**
5. ⇒ **`sub_7888B0` 只把它降到 0**
6. ⇒ **而 `sub_789570` 是非零 `+40` 的【唯一】写者**
```

**✅ 一个**穷尽性的"谁写这个"普查**。**

**⇒ 与 §340 的"定向的负面"、§347 五.7 的"我们看不见的另一半"**同族。**

### 9.5 而**三个消费者都在第一个零处停**

```php
// Both consumers then stop dead at the first zero:
//   sub_787490 (the ramp)   node+44 = node+40, so 0 stays 0
//   sub_787100 (the clock)  `if (0.0 == node+44) return`, and for a
//                           container `rate * dt == 0` returns too
//   sub_78B570 (the pose)   descends only into nodes with +44 != 0
// which is exactly what was measured: leaf time frozen at 0.0000.
```

**⇒ 六层**：

```text
1. **两个消费者然后在第一个零处戛然而止**（实际列了三个）
2. ⇒ **`sub_787490`（斜坡）`node+44 = node+40`，所以 0 保持 0**
3. ⇒ **`sub_787100`（时钟）`if (0.0 == node+44) return`，而对一个容器 `rate * dt == 0` 也返回**
4. ⇒ **`sub_78B570`（姿势）只下降到 `+44 != 0` 的节点**
5. ⇒ **那正是所测量的：叶子时间冻结在 `0.0000`**
```

**⚠ 注释说"两个消费者"而列了三个。**

**⇒ 一处**小的计数错误**（或"both"指前两个）。**

### 9.6 而 **`sub_7891D0`（type-8 处理器）是修复它的函数**

```php
// `sub_7891D0`, the type-8 handler, is the function that fixes it.
// After playing the animation itself through `sub_7893F0` it walks
// node+14 (parent) upward and, for every ancestor until the key
// equals record+32, calls
//     sub_788AF0(node, 1.0, blend)          fade this level's siblings
//     sub_789570(tree, node, 1.0, blend, 1.0)   weight 1.0, rate 1.0
// (disassembled at 0x789235..0x7892AF: `fld1` twice, `push edi`).
```

**⇒ 七层**：

```text
1. **`sub_7891D0`，type-8 处理器，是修复它的函数**
2. ⇒ **在通过 `sub_7893F0` 播放动画本身之后**
3. ⇒ **它走 `node+14`（父）向上**
4. ⇒ **而对每一个祖先直到 key 等于 `record+32`**
5. ⇒ **调用 `sub_788AF0(node, 1.0, blend)`** —— 淡出这一级的兄弟
6. ⇒ **调用 `sub_789570(tree, node, 1.0, blend, 1.0)`** —— 权重 1.0、速率 1.0
7. ⇒ **（在 `0x789235..0x7892AF` 反汇编：两次 `fld1`、`push edi`）**
```

**✅ 一个**指令级的证据**（`fld1` 两次 = 1.0）。**

### 9.7 而 **"type 8 携带两个别名索引"**

```php
// Type 8 carries TWO alias indices. `sub_540040` resolves both --
// `record+20 = sub_785870(record+24)` always, and `record+32 =
// sub_785870(record+28)` only when `record+4 == 8`. `sub_785870`
// returns 0 for alias 0, and the root's key is 0, so a NULL second
// alias means "walk all the way to the root", which is what we want.
```

**⇒ 六层**：

```text
1. **type 8 携带【两个】别名索引**
2. ⇒ **`sub_540040` 两个都解析**
3. ⇒ **`record+20 = sub_785870(record+24)` 总是**
4. ⇒ **`record+32 = sub_785870(record+28)` 只在 `record+4 == 8`**
5. ⇒ **`sub_785870` 对别名 0 返回 0，而根的 key 是 0**
6. ⇒ **所以一个【空】的第二别名意味着"一直走到根"，那正是我们要的**
```

**✅ 一个**极优雅的"用零做终止"**。**

**⇒ **第三次"零即终止"**（§342 的 `EntityNumWorld`、§345 的 `isAgent`、这里）。**

### 9.8 而 **`record+48 = 0` 两位的精确语义**

```php
// RECORD+48 = 0, BOTH BITS CLEAR.
//
// bit 0 picks sub_7892D0 over sub_7891D0, and sub_7891D0 is the whole
// point of this record, so it must stay clear.
//
// bit 1 becomes sub_7893F0's last argument, which only decides whether
// an ALREADY EXISTING node is cloned through sub_789B60 before being
// re-weighted. The type-1 record needed it set, because there the
// existing-node branch does nothing else at all; sub_7893F0 falls
// through to sub_788AF0 + sub_789570 either way, so a repeat command
// re-asserts the weight on the same node instead of churning a new
// one every second.
```

**⇒ 八层**：

```text
1. **`record+48 = 0`，两位都清零**
2. ⇒ **bit 0 在 `sub_7892D0` 与 `sub_7891D0` 之间选**
3. ⇒ **而 `sub_7891D0` 是这条记录的全部意义 ⇒ 所以它必须保持清零**
4. ⇒ **bit 1 变成 `sub_7893F0` 的最后一个参数**
5. ⇒ **它只决定一个【已存在】的节点是否通过 `sub_789B60` 被克隆然后再重新加权**
6. ⇒ **type-1 记录需要它置位**，因为在那里"已存在节点"分支什么也不做别的
7. ⇒ **`sub_7893F0` 无论哪种方式都落到 `sub_788AF0` + `sub_789570`**
8. ⇒ **所以一条重复命令在【同一个】节点上重新断言权重，而不是每秒搅一个新节点**
```

**✅ 一个**极精细的权衡**（克隆 vs 复用）。**

### 9.9 而**权重的两位码**

```php
// WEIGHT 1.0 (sub_6715D0's two-bit arm).
message.MSG_WriteBits(0, 1);
message.MSG_WriteBits(1, 1);
```

**⇒ 三层**：

```text
1. 一个 0 位
2. ⇒ 一个 1 位
3. ⇒ **`sub_6715D0` 的两位支 ⇒ 1.0**
```

**✅ 而 §346 的 `writeExplicitAnimationCommand` 里权重是 `command.weight == 1.0f ? 1 : 0`。**

**⇒ **两个不同的权重编码**（type-1 vs type-8）。**

**⚠ 一处需注意的差异。**

### 9.10 而**混合帧的 `writeClients`**

```cpp
std::size_t emittedModelFields = 0;
writeClients(message, frame.clients, baseline ? &baseline->clients : nullptr,
    frame.agents, baseline ? &baseline->agents : nullptr,
    frame.emitPlayersInActorsSection,
    baseline ? baseline->emitPlayersInActorsSection : frame.emitPlayersInActorsSection,
    frame.serverTime, &emittedModelFields);
```

**⇒ 三层**：

```text
1. **`emittedModelFields` 是一个输出参数**
2. ⇒ **统计真正写出的 modelIndex 字段数**
3. ⇒ **供 `AGENTWIRE` 日志使用**
```

**✅ 与 §347 五.7 的"仪器"同族（**第五次**）。**

### 9.11 而 `AGENTWIRE` 日志的**八个字段**

```text
serverTime / client / clients / agents / withModel / emittedModelFields / baseline
+ 每个 agent：slot / model / attach0 / attach1 / tag0 / anim / animStart / tag1
```

**⇒ 七个全局 + 每个 agent 八个。**

**✅ 而注释解释为什么 `attach0` 重要：**

```php
// THE ATTACHMENTS TOO, not just the body. 12.47 resolved
// c_zom_ger_head to model index 330 off the CLIENT'S OWN
// NCS union, and the resolver is union-correct (a map prop
// logged ourIndex=388, which is union 387 + 1 exactly). So
// the head SHOULD already be on the wire as 330 and the open
// question is no longer the number -- it is whether the
// client keeps it. Printing attach0 makes that a one-cycle
// answer instead of an inference.
```

**⇒ 七层**：

```text
1. **附件也要，不只是身体**
2. ⇒ **12.47 从【客户端自己的】NCS union 解析 `c_zom_ger_head` 到模型索引 330**
3. ⇒ **而那个解析器是 union 正确的**
4. ⇒ **（一个地图道具记录到 `ourIndex=388`，那是 union 387 + 1 恰好）**
5. ⇒ **所以头【应该】已经以 330 在线上**
6. ⇒ **而开放的问题不再是那个数字 —— 而是【客户端是否保留它】**
7. ⇒ **打印 `attach0` 让那变成一个一周期就能回答的问题而不是一个推断**
```

**✅ 与 §345 的"客户端基线 xmodel 不是文件的 xmodel（+3）"**完全同族 ✓**

**⇒ 而这里说 +1（387 → 388）。**

**⚠ 所以**两个不同的偏移**：**

```text
§345  模型索引 +3（390/387、410/407、388/385）
§347  union 索引 +1（ourIndex 388 = union 387 + 1）
```

**⇒ **两套编号系统，两个偏移**。**

**✅ 与 §345 的"客户端重新解析进自己的 configstring 带"配合。**

**⇒ 而 union 是一个**独立编号空间**。**

## 十、关键结论

1. **`writeExplicitAnimationCommand` 的三段拼接**（显式位 → selector 3 实体 → selector 4 时间 → selector 1 或 9）。
2. **三个 0 位是"最便宜的合法编码"**（权重起手 / blend 0.2 / rate 1.0）。
3. **`aliasBits` 与 `baselineBits` 对 `size == 1` 处理不同**（0 vs 强制 1）。
4. **512 的段上限第二次确认**。
5. **⭐ 预测字段模式：零售 `781/6160`（12.7%）而本服务器 `4239/4239`（100%）** —— **8 倍过量**。
6. **六个计数器与 600 帧（30 秒）的报告窗口**。
7. **`SV_PresentableTeam`："只有 1 与 2 在客户端解析"** ⇒ `None`/`Spectator` 必须映射到其中之一。
8. **⭐ "这条线只有一个不变量"** —— 客户端从**距离字节 + `SnapshotBaselineFlag`** 解析**一个消息级基线**。
9. **违反它的后果链**：`modelIndex 0` → `CG_SetupClientCharacterInfo` 早退 → 无模型名 → `BG_UpdatePlayerDObj` 拒绝。
10. **三个可分辨的失败**（空基线未标 / 非空基线已标 / 空基线非零距离）。
11. **⭐ "这只是线半，而它对另一半是盲的"** —— `SV_WriteSnapshot` 没有历史 ⇒ 看不见**陈旧的**被置标志基线。
12. **第三种去重（每客户端 `std::hash` 摘要）** —— 三种去重三种粒度。
13. **⭐⭐ "位 `0x02` 是客户端离开 `CA_PRIMED` 的门票而这服务器从未设过它"** —— `sub_515C90` 在 `0x515DAE` 设 `cls.state = 10`。
14. **五个实测症状一个根因**（2 字节心跳 / 65 包 / 无 pmove-slice / `cacheAcked=0` / 46 秒 `XBOXLIVE_CANTJOINSESSION`）。
15. **`SnapshotSceneBlockFlags = 0x0A = 0x08 | 0x02`** ⇒ cgame 丢弃入场帧。
16. **⭐ "两个极端都是错的"** —— 每帧 FULL ⇒ `rearm`/`FULL` 振荡；恰好一次 ⇒ 落在加载中而永不应答。
17. **"`baseline != nullptr` 就是那个证明"** —— 用已有状态推导语义（第二次）。
18. **进程生命期锁存 + 明确的"何时会坏"**（服务两场比赛不重启 ⇒ 第二个客户端卡在 `CA_PRIMED`）。
19. **⭐ "`clientInfos` 绝不能对着段级空基线写"** —— 它没有逐条"全量编码"位。
20. **"理论是成立的而实现不可能"** —— 与 §340 的"诊断错建议对"互补。
21. **`clientinfo WIRE baseline=empty(UNFLAGGED)`** —— 第四个仪器命名缺陷。
22. **"不要加回来"** —— 明确的维护者陷阱。
23. **`ActorCommandDeliveryState` 的三代际条件**（未初始化 / `serverTime` 倒退 / `initializeBaselineCache` 转换）。
24. **"投递所有权按观察者"** —— 每客户端状态。
25. **`55,591` 命令 / 120 实体 / 20 分钟 ⇒ 每 actor 每秒一个** —— 而"第一版每秒二十个"使动画**看起来冻结**。
26. **快照 50ms（20 Hz）实测**（19300, 19350）。
27. **⭐ actor 动画树的完整 12.x 链**：`SvActorSeedAnimTree` → `sub_7886D0` 建根 → 空别名表 ⇒ 一个节点 → （12.154）别名解析而树长到 8 节点 → 中间节点零权重 ⇒ 绑定姿势 → （12.155）type 8 加权祖先。
28. **七个节点名**：`root -> 5 -> 152 -> 389 -> 409 -> 411 -> 495`。
29. **`sub_7886D0` 的两个分支**（根写 `1.0/1.0/1.0/0.0`；`LABEL_7` 写八个零 dword）+ **穷尽性的"谁写这个"**（`sub_7888B0` 只降、`sub_789570` 是唯一非零写者）。
30. **三个消费者都在第一个零处停**（`sub_787490` / `sub_787100` / `sub_78B570`）⇒ **叶子时间冻结在 0.0000**。
31. **`sub_7891D0` 的祖先走 + `sub_788AF0` + `sub_789570(..., 1.0, blend, 1.0)`**，`0x789235..0x7892AF` 的两次 `fld1`。
32. **"type 8 携带两个别名而空的第二别名 = 走到根"** —— 第三次"零即终止"。
33. **`record+48` 两位的精确权衡**（bit 0 必须清零 / bit 1 决定克隆 vs 复用）。
34. **权重两个编码**（type-1 的 `weight == 1.0f ? 1 : 0` vs type-8 的 `0 1` = 1.0）。
35. **`AGENTWIRE` 的十五个字段**（七全局 + 八每 agent）。
36. **"头应该已经是 330 而开放的问题不再是数字而是客户端是否保留它"** —— 与 §345 的 +3 同族；**union 是 +1**（两套编号两个偏移）。

## 十一、未闭合点

- `SnapshotSceneBlockFlags = 0x0A` 在服务端拒绝与客户端丢弃之间的区分。
- `gZmActorWalkAnim` 的来源与值。
- 模型索引 `+3` 与 union 索引 `+1` 两套编号的关系。
- `sub_7892D0` 与 `sub_7891D0` 的分工（bit 0）。
- 为什么 `mp_nuked` 不需要 `0x02`。
- `sv_snapshot_mp.cpp` 10798 行之后未读取（27,016 行，进度 40%）。
