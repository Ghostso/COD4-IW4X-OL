# 427 · **"一个捕获的样本是唯一存在的独立判据"** —— `usercmd` 的 `11` 位 vs `10` 位、`OLMOD(section-86)` 的"改变不是非零"、以及"首次目击每比特"

## 一、范围

本报告学习 `sv_client_mp.cpp` 760–1100 行（`reliableCommandResolver` 的两分支、usercmd 样本捕获、`baselineFrame` 的记录、按钮位首见）。

## 二、**"一个捕获的样本是这条方向上唯一存在的独立判据"**（本组最重要的一段）

### 2.1 那段

```php
// OLMOD(section-85): CAPTURE ONE REAL USERCMD SAMPLE, BECAUSE THE GOLDEN
// NEEDS A CAPTURED ONE AND HAS NEVER HAD IT.
//
// The two red goldens (section 58f) are red because their wire sample is
// HAND-BUILT and encodes the three weapon-index deltas at TEN bits where
// this build reads ELEVEN. Section 58f rejected both cheap repairs for
// stated reasons: an offline Python mirror disagreed with the reader at
// the first keyed bit, and building the writer inside the test is the
// symmetric round trip section 51j proved passes even when both sides are
// wrong.
//
// A CAPTURED sample is neither. The bytes come from a real CODOL client,
// so the test would compare this reader against the shipped WRITER --
// which is the only independent oracle that exists for this direction of
// the wire, because a demo records what a server SENDS and contains no
// usercmds at all.
```

### 2.2 二十四层

```text
1. **捕获一个真实的 usercmd 样本**，因为【那个金样本需要一个捕获的而【从来没有过**】】**
2. ⇒ **两个红色的金样本（第 `58f` 节）是红的**
3. ⇒ **因为【它们的线缆样本是【手工构建**】的**】
4. ⇒ **⇒ 而【它在【十个位**】上编码三个武器索引 delta**】**
5. ⇒ **而这个 build 【读【十一个位**】】** ⇒ **`10 ≠ 11`**
6. ⇒ **第 `58f` 节【拒绝了两个便宜的修法，附理由**】**
7. ⇒ **① 一个离线的 Python 镜像【在第一个被键控的位上【与读者不一致**】】**
8. ⇒ **② 在测试【内部构建写者**】是【对称往返**】**
9. ⇒ **⇒ 而第 `51j` 节【证明了它【即使两边都错也会通过**】】**
10. ⇒ **⇒ 一个【捕获的**】样本【两者都不是**】**
11. ⇒ **字节来自【一个真实的 CODOL 客户端**】**
12. ⇒ **⇒ 所以测试会【把这个读者与【随货的写者**】比较**】**
13. ⇒ **⇒ 那是【这条方向上唯一存在的独立判据**】**
14. ⇒ **⇒ 因为【一个 demo 记录一个服务器【发**】什么而【完全不含 usercmd**】】**
```

### 2.3 ⭐⭐⭐ **"一个 demo 记录一个服务器发什么而完全不含 usercmd"**

**✅ 这是本报告里**最重要的一条"取证源的不对称"**。**

**⇒ 三层**：
```text
demo（录制）⇒ **只有服务器 → 客户端**（**一个方向**）
usercmd ⇒ **客户端 → 服务器**（**另一个方向**）
⇒ **⇒ 所以【demo 对 usercmd 方向【零信息**】】
```

**✅ 与 §402 的"`s 0201` 在 dm 与 dmz 各测到一次"**不同（那是**同一个方向**）。

**⇒ 三层**：
```text
服务器→客户端 ⇒ **有 demo**
客户端→服务器 ⇒ **只有一个真实的客户端能提供**
⇒ **⇒ 所以【"一个捕获的样本"是【唯一的**】独立判据**】
```

**✅ ⭐⭐⭐ **一个"方向决定可用取证源"的实例**。

**⚠ 而"两个红色的金样本"⇒ **两个测试【已知失败**】。**

**⇒ 三层**：
```text
金样本 1 ⇒ **`10` 位编码**
金样本 2 ⇒ **另一个**
⇒ **⇒ 两个都是【手工构建 ⇒ 10 位 ⇒ 与 `11` 位读者不匹配**】
```

**✅ ⭐ **一个"测试失败的原因被明确记录"的实例**。</br>

**✅ 与 §419 的"`2→1` 是承重样本"**不同（那是一个好样本；这里是一个**坏样本**）。

### 2.4 而**"对称往返即使两边都错也会通过"**

**✅ 这是本报告里**最重要的一条"测试有效性**。**

**⇒ 三层**：
```text
若测试 = **我们的写者 + 我们的读者** ⇒ **一个自洽的错误【通过**】
正确测试 = **他们的写者 + 我们的读者**（或反之）
⇒ **⇒ 所以【测试的两端必须来自【不同来源**】】
```

**✅ 与 §397 的"一个结果在两种假设下都成立 ⇒ 零信息"**同族（**第九次"无效实验**）。

**⇒ 三层**：
```text
§397  **两种假设下都 `true`** ⇒ 零信息
§423  **测试测的是我们的写者** ⇒ 零信息
§427  **对称往返** ⇒ 零信息
⇒ **⇒ 三次"零信息的实验**】
```

**✅ ⭐⭐⭐ **一个"零信息实验"的三例表**。

### 2.5 而**"`OLMOD(section-86)` 的改变不是非零"**

```php
// OLMOD(section-86): AND "EXERCISES" MEANS CHANGED, NOT NON-ZERO. The
// first gate here was `weapon != 0`, and the three samples it caught all
// carried weapon=1224 against a baseline of weapon=1224 -- unchanged, so
// the eleven-bit path was not walked and the sample could not have shown
// the defect the goldens are red for. Compare against the BASELINE, which
// is the thing the delta is relative to. A weapon switch produces one.
```

**⇒ 十六层**：
```text
1. **"exercises" 意味着【改变**】，不是【非零**】**
2. ⇒ **第一个门是 `weapon != 0`**
3. ⇒ **而【它抓到的三个样本【全部携带 `weapon = 1224`**】】**
4. ⇒ **对【一个基准 `weapon = 1224`**】**
5. ⇒ **⇒ 所以【未改变**】**
6. ⇒ **⇒ 所以【`11` 位那条路径【没有被走过**】】**
7. ⇒ **⇒ 而那个样本【不可能显示出【那些金样本为它而红的那个缺陷**】】**
8. ⇒ **⇒ 与【基准**】比较**
9. ⇒ **那正是【那个 delta 【相对于**】的东西】
10. ⇒ **一次武器切换【产生一个**】**
```

### 2.6 ⭐⭐⭐ **"三个样本全部携带 `weapon = 1224` 而基准也是 `1224`"**

**✅ 这是本报告里**最重要的一次"门写错**。**

**⇒ 三层**：
```text
意图：**捕获走 `11` 位路径的样本**
错误实现：`weapon != 0` ⇒ **抓到 `1224`（非零但未变）**
正确实现：`weapon != baseline.weapon` ⇒ **抓到一次切换**
⇒ **⇒ 所以【"非零"与"改变"是【两个不同的条件**】】
```

**✅ 与 §419 的"`2→1` 而玩家在 `71`"**不同（这是**一个条件的定义错误**）。

**⇒ 三层**：
```text
`!= 0` ⇒ **"有值"**
`!= baseline` ⇒ **"走过 delta 路径"**
⇒ **⇒ 所以【后者才是那个测试要的**】
```

**✅ ⭐⭐⭐ **"门槛必须对准它要测的那个机制"** —— 与 §411 的"卡死判据的等价速度被改了"**同族（**第二次"参数与派生量"）。

**⚠ 而"三个样本"⇒ **所以捕获有上限（`3`）**。**

**✅ 与 §425 的"`200` 行预算"**同族（**第三次"有界"）。

## 三、**`reliableCommandResolver` 的两个分支**（本组第二重要）

### 3.1 三段代码

```cpp
if (reliableAcknowledge > slot->reliableSequence) { ... "reliable key REJECTED" ... return std::nullopt; }
if (reliableAcknowledge && reliableAcknowledge <= slot->reliableSequence &&
    slot->reliableSequence - reliableAcknowledge < ServerReliableCommandCapacity)
{
    return std::string(slot->reliableCommands[
        reliableAcknowledge & (ServerReliableCommandCapacity - 1)].xorKey());
}
// ack==0 is the ordinary pre-first-command case and is CORRECT here. A non-zero
// ack reaching this line is a stale-gap desync and is not.
if (reliableAcknowledge && slot->reliableKeyComplaints < ReliableKeyComplaintLimit) { ... "reliable key EMPTY" ... }
return std::string{};
```

**⇒ 二十层**：
```text
1. **分支 1：`ack > serverSequence`** ⇒ **`REJECTED`** ⇒ `nullopt`
      · **⇒ 一个【未来的 ack**】 ⇒ **客户端确认了它不该有的东西**
2. ⇒ **分支 2：`ack <= serverSequence 且 gap < capacity`** ⇒ **返回那个槽的 `xorKey()`**
      · **⇒ 【正常路径**】
3. ⇒ **分支 3：其余** ⇒ **`EMPTY`**（**返回空串**）
      · **⇒ 包括 `ack == 0`（正常）与 `ack != 0 而 gap >= capacity`（坏）**
4. ⇒ **而分支 3 的日志【只在 `ack != 0` 时打印**】**
5. ⇒ **⇒ 所以【`ack == 0` 是静默的正常路径**】
```

### 3.2 ⭐⭐⭐ **"`ack == 0` 是普通的『第一条命令之前』的情况，而在这里是正确的；一个非零的 ack 到达这一行是一个陈旧的间隙失同步，而不是"**

**✅ 这是本报告里**最重要的一条"分支边界"**。**

**⇒ 三层**：
```text
`ack == 0` ⇒ **正常**（还没有命令）
`ack != 0 且 gap >= capacity` ⇒ **失同步**（**客户端确认的号已经滚出环形缓冲**）
⇒ **⇒ 同一个分支，两种语义** ⇒ **而日志只对后者**
```

**✅ 与 §426 的"两个非 (B) 分支都能楔死而两个都不说"**——**现在它们都说了** ✓

**⇒ 三层**：
```text
§426  **"都没说"** ⇒ 加日志
§427  **两处都打印 `REJECTED` / `EMPTY` 并带 `ack`/`serverSequence`/`gap`/`capacity`**
⇒ **⇒ 所以【那条注释的意图【已被实现**】】
```

**✅ ⭐⭐ **一个跨报告的闭合**。

**⚠ 而"`gap`"⇒ **`serverSequence - reliableAcknowledge`**。**

**⇒ 三层**：
```text
`gap == 0` ⇒ ack 等于 serverSequence ⇒ **客户端确认了最新的**
`gap >= capacity` ⇒ **确认的号已滚出环形缓冲** ⇒ **它的 XOR 键【不可得**】
⇒ **⇒ 所以【`capacity` 是那个"多久以前的 ack 仍可解**】的界限**】
```

**✅ ⭐⭐ **"环形缓冲的容量 = 可寻址的历史深度"** —— 与 §425 的"`27` 块"**不同（这是**一个环形**）。

**⇒ 三层**：
```text
`ServerReliableCommandCapacity` ⇒ **环形大小**
`reliableAcknowledge & (capacity - 1)` ⇒ **槽索引** ⇒ **所以是 2 的幂**
⇒ **⇒ 一个"位与取模"的优化**
```

**✅ ⭐ **一个"2 的幂环形"的实例**。

## 四、**`baselineFrame` 的"记录客户端缓存了什么，但绝不作为 delta 源"**（本组第三重要）

### 4.1 那段

```php
// WHICH FRAME THE CLIENT'S PERSISTENT CACHE HOLDS, KEYED ON THE ACKNOWLEDGED
// FRAME'S OWN FLAG (section 169). This used to demand that the acknowledgement
// match the ONE initializer thought to be in flight, because SnapshotBaselineFlag
// was being used as a cache-generation handshake. It is not a handshake: it is
// the wire's statement that a message was written against no baseline, so it now
// rides every such frame and any one of them the client acknowledges is a frame
// the client provably stored (CL_ParseSnapshot copies it at 0x00472745). Asking
// the acknowledged snapshot whether it carried the flag is therefore both simpler
// and generation-agnostic, and it cannot lose an acknowledgement to a fresher
// initializer having been armed in the meantime.
//
// Note this records WHAT THE CLIENT CACHED. It is deliberately never used as a
// delta source -- see the invariant at the snapshot assembly.
```

### 4.2 二十四层

```text
1. **客户端的持久缓存持有哪一帧，按【被确认的那一帧【自己的旗标**】键控**
2. ⇒ **这【过去要求**】那个确认【匹配【那个据信在飞的【唯一初始化器**】】】
3. ⇒ **因为 `SnapshotBaselineFlag` 【被用作一个缓存代次握手**】**
4. ⇒ **⚠ 它【不是一个握手**】**
5. ⇒ **⇒ 它是【线缆的声明：一条消息是【对无基准**】写的**
6. ⇒ **⇒ 所以【它现在【骑在每一个这样的帧上**】】**
7. ⇒ **⇒ 而【客户端确认的【任何一个**】就是一个【客户端可证明地存储了**】的帧**
8. ⇒ **（`CL_ParseSnapshot` 在 `0x00472745` 拷贝它）**
9. ⇒ **⇒ 所以【问那个被确认的快照它是否携带那个旗标**】既【更简单**】又【与代次无关**】
10. ⇒ **⇒ 而它【不能把一个确认【丢给一个更晚被武装的初始化器**】】**
11. ⇒ **⚠ 注意【这记录【客户端缓存了什么**】】**
12. ⇒ **它【刻意地【从不**】被用作一个 delta 源**】
13. ⇒ **⇒ 见快照装配处的那个不变式**
```

### 4.3 ⭐⭐⭐ **"它现在骑在每一个这样的帧上，而任何被确认的一个都是客户端可证明地存储了的帧"**

**✅ 这是本报告里**最重要的一次"从握手到属性"的语义化简**。**

**⇒ 三层**：
```text
旧模型：**`SnapshotBaselineFlag` 是一个【请求/应答握手**】⇒ 要求匹配"那个"初始化器
新模型：**它是一个【属性**】（"这一帧对无基准写的"）⇒ **每个这样的帧都带**
⇒ **⇒ 所以【任何被确认的一个都比"那一个"更好**】
```

**✅ 与 §404 的"压制边沿不够"**不同（这是**一个从"状态机"到"属性"的重构**）。

**⇒ 三层**：
```text
状态机 ⇒ **需要记住"哪个在飞"** ⇒ **会丢**
属性   ⇒ **无状态** ⇒ **不会丢**
⇒ **⇒ 所以【无状态优于状态机**】
```

**✅ ⭐⭐⭐ **一个"把握手化简成一个属性"的实例**。</br>

**✅ 而与 §426 的"客户端进入世界时清六样东西"**配合（**那也是一个"代次"问题**）。

### 4.4 而**"它刻意地从不被用作一个 delta 源"**

**✅ 这是本报告里**最重要的一条不变式**。**

**⇒ 三层**：
```text
`baselineFrame` ⇒ **记录客户端缓存了什么**
delta 源 ⇒ **必须来自 `snapshotHistory`**（一个双方同意的代次）
⇒ **⇒ 所以【两者不能混用**】
```

**✅ 与 §418 的"`constBaselines` 与 `useEntityBaselines` 是一个决定"**同族（**第五次"两条路径不能混用"）。

**⇒ 三层**：
```text
§418  `useEntityBaselines` 与 `constBaselines` **必须同步**
§426  `baselineCacheAcknowledged` 与 `deltaMessage` **必须一起清**
§427  `baselineFrame` 与 delta 源 **必须分开**
⇒ **⇒ 三次"两条路径的耦合约束**】
```

**✅ ⭐⭐ **一个"耦合约束"的三例表**。

## 五、**"一个重新断言被删除了，而它的工作由进入世界的重置完成"**

### 5.1 那段

```php
// THE RE-ASSERTION IS GONE, AND ITS JOB IS DONE BY THE ENTER-WORLD RESET
// (section 169). It re-sent the clientInfos section alone against a null
// baseline while the rest of the message still deltaed against a real one -- a
// section-local empty baseline with nothing on the wire to declare it, which is
// exactly the defect it was built to work around. What actually recovers a client
// whose cgame threw its characterInfo away on a map load is the reset above:
// deltaMessage = -1 clears the history and the cache state, the next snapshot has
// no baseline, SnapshotBaselineFlag goes out with it, and the client rebuilds
// every clientInfo from a section it is TOLD is absolute. That is also what retail
// does, and it is why retail needs no re-assertion of its own.
```

### 5.2 二十层

```text
1. **那个重新断言【走了**】，而【它的工作由进入世界的重置完成**】**
2. ⇒ **它【单独重发 `clientInfos` 那一节【对一个空基准**】】**
3. ⇒ **⇒ 而消息的其余部分【仍然对【一个真实基准**】做增量**】**
4. ⇒ **⇒ 【一个节内局部空基准**】而【线上【没有任何东西声明它**】】**
5. ⇒ **⇒ 那正是【它被造出来【绕开**】的那个缺陷**
6. ⇒ **⇒ 真正恢复一个【cgame 在地图加载时扔掉了它的 characterInfo**】的客户端的东西**
7. ⇒ **是【上面那个重置**】**
8. ⇒ **`deltaMessage = -1` ⇒ 清历史与缓存状态**
9. ⇒ **⇒ 下一份快照【没有基准**】**
10. ⇒ **`SnapshotBaselineFlag` 【随它出去**】**
11. ⇒ **⇒ 而客户端【从一个【被告知是绝对的**】的节里【重建每一个 `clientInfo`**】】**
12. ⇒ **⇒ 那也正是【零售做的**】**
13. ⇒ **⇒ 而那就是【为什么零售【不需要它自己的重新断言**】】**
```

### 5.3 ⭐⭐⭐ **"一个节内局部空基准而线上没有任何东西声明它"**

**✅ 这是本报告里**最精妙的一处"局部 vs 全局基准"**。**

**⇒ 三层**：
```text
正确：**整条消息一个基准** ⇒ **`SnapshotBaselineFlag` 声明"无基准"**
错误：**`clientInfos` 一节用空基准而其余用真实基准**
⇒ **⇒ 所以【客户端无法知道那一节是绝对的**】
```

**✅ 与 §418 的"`useEntityBaselines` 与 `constBaselines` 是一个决定"**——**完全同族**（**第三次"基准必须声明**）。

**⇒ 三层**：
```text
§414  **`0x10` 是每快照的**（**不能对 237 个对而对 1 个无害**）
§418  **旗标与 delta 基准是一个决定**
§427  **一个节内局部空基准是【不可声明的**】
⇒ **⇒ 三次"基准的全局性**】
```

**✅ ⭐⭐⭐ **一个"基准的全局性"的三例表**。

**⚠ 而"那也正是零售做的，而那就是为什么零售不需要它自己的重新断言"**⇒ **一个用零售行为验证的论证**。**

**✅ 与 §408 的"`_tp` 只在 `DB_FindXAssetHeader` 成功时写"**同族（**第三次"用零售行为定设计**）。

## 六、**按钮位的"首次目击每比特"**

### 6.1 那段

```php
// FIRST SIGHTING PER BIT, never per press. One OR and one compare
// per accepted move packet, and it goes quiet the moment the
// vocabulary is known -- which is the only shape an always-on
// instrument may have (section 188d).
{
    static std::uint32_t seenButtonBits{};
    static std::uint32_t buttonReports{};
    const auto fresh = latest.buttons & ~seenButtonBits;
    if (fresh && buttonReports < 32) { ... "button bits FIRST SIGHTING" ... }
    else if (fresh) { seenButtonBits |= latest.buttons; }
}
```

**⇒ 十二层**：
```text
1. **每比特首次目击，从不每次按下**
2. ⇒ **每个被接受的 move 包【一次 OR 与一次比较**】**
3. ⇒ **⇒ 而它【在词汇已知的那一刻【安静下来**】】**
4. ⇒ **⇒ 那是【一个常开仪器【唯一可以有的形状**】】（第 `188d` 节）**
5. ⇒ **`fresh = buttons & ~seenButtonBits`** ⇒ **新位**
6. ⇒ **`buttonReports < 32`** ⇒ **上限 `32` 行**
7. ⇒ **⇒ 而【超过上限后【仍然更新 `seenButtonBits`**】**
8. ⇒ **⇒ 所以【`fresh` 会一直计算但不再打印**】
```

### 6.2 ⭐⭐⭐ **"一个常开仪器唯一可以有的形状"**

**✅ 这是本报告里**最重要的一条"常开仪器的纪律**。**

**⇒ 三层**：
```text
若"每次按下" ⇒ **日志爆炸** ⇒ **必须关**
若"首次目击每比特" ⇒ **最多 `32` 行** ⇒ **可以常开**
⇒ **⇒ 所以【"首次"是一个【自然的界**】】
```

**✅ 与 §425 的"`200` 行预算"**同族（**第四次"有界"）。

**⇒ 三层**：
```text
§409  **按秒去重**（`advance-wait`）
§411  **值变化时**（`PMFLAGS|`）
§425  **`200` 行预算**（`ScoreboardTrace`）
§427  **每比特首次**（`button bits`）
⇒ **⇒ 四种"有界"的手法**
```

**✅ ⭐⭐ **一个"有界"的四例表**。

**⚠ 而"超过上限后仍然更新 `seenButtonBits`"⇒ **一个刻意的选择**。**

**⇒ 三层**：
```text
若【不更新】⇒ **`fresh` 永远非零** ⇒ **但不再打印** ⇒ **无害**
若【更新】⇒ **`fresh` 归零** ⇒ **无害**
⇒ **⇒ 两者等价**（**因为不打印**）
```

**⚠ 一个**无害的冗余**。

### 6.3 而**"一个阳性对照，因为第一次实机运行产生了【零个边**】"**

```php
// AND A POSITIVE CONTROL, because the first live run produced NO
// edge at all and a silent instrument is indistinguishable from an
// instrument that never ran. This says the field is being read and
// what it holds; if the edge below never fires AND this says 0,
// the client is genuinely not sending one.
```

**⇒ 十层**：
```text
1. **而一个阳性对照**
2. ⇒ **因为【第一次实机运行产生了【零个边**】】**
3. ⇒ **⇒ 而【一个沉默的仪器【与一个从未运行过的仪器【不可区分**】】**
4. ⇒ **⇒ 这一行说【那个字段被读了**】以及【它持有什么**】**
5. ⇒ **⇒ 若【下面那个边【永不触发**】而【这个说 `0`**】**
6. ⇒ **⇒ 那么【客户端【真的没有发**】】**
```

**✅ ⭐⭐⭐ **"一个沉默的仪器与一个从未运行过的仪器不可区分"** —— 本报告里最重要的取证原则。

**✅ 与 §405 的"『领先/失去是静默的』三个所有者而一个没留一行"**同族（**第六次"沉默的诊断"）。

**⇒ 三层**：
```text
§370  **"阳性对照"**
§405  **"三个所有者一个没留一行"**
§427  **"沉默的仪器与从未运行的仪器不可区分"**
⇒ **⇒ 三次"必须有阳性对照**】
```

**✅ ⭐⭐⭐ **一个"阳性对照"的三例表**。

## 七、关键结论

1. **⭐⭐⭐ "一个 demo 记录一个服务器发什么而完全不含 usercmd"** ⇒ **一个捕获的真实 usercmd 样本是这条方向上【唯一存在的独立判据】**。
2. **⭐⭐⭐ "对称往返即使两边都错也会通过"（第 `51j` 节）** ⇒ **测试的两端必须来自不同来源** —— 第三次"零信息的实验"（与 §397、§423 同族）。
3. **⭐⭐ "两个红色的金样本是手工构建的，在【十个位】上编码三个武器索引 delta，而【这个 build 读十一个位】"`**。
4. **⭐⭐⭐ `OLMOD(section-86)` 的"改变不是非零"**：**第一个门是 `weapon != 0`，抓到的三个样本全部携带 `weapon = 1224` 而基准也是 `1224` ⇒ 未改变 ⇒ `11` 位路径没有被走过 ⇒ 那个样本不可能显示缺陷** ⇒ **改为与【基准】比较**。
5. **⭐⭐ "门槛必须对准它要测的那个机制"`** —— 与 §411 的"卡死判据的等价速度被改了"同族。
6. **⭐⭐⭐ `reliableCommandResolver` 的三分支**：**`ack > serverSequence` ⇒ `REJECTED`**；**`ack <= serverSequence 且 gap < capacity` ⇒ 返回 `xorKey()`**（正常）；**其余 ⇒ `EMPTY`**（含 `ack == 0` 的正常路径）—— **而日志只对 `ack != 0` 打印**。
7. **⭐ "`ServerReliableCommandCapacity` 是 2 的幂（`ack & (capacity - 1)`）"** ⇒ 环形缓冲的容量 = **可寻址的历史深度**。
8. **⭐⭐⭐ `SnapshotBaselineFlag` 的角色重构**：**从"缓存代次握手"（要求匹配那一个在飞的初始化器）改为"一个属性"（"这一帧对无基准写的"）⇒ 骑在每一个这样的帧上 ⇒ 任何被确认的一个都是客户端可证明地存储了的帧** ⇒ **更简单、与代次无关、且【不会把确认丢给一个更晚被武装的初始化器】** —— 一个"把握手化简成属性"的实例。
9. **⭐⭐⭐ "它刻意地从不被用作一个 delta 源"`** —— `baselineFrame` 记录什么是被分开的。
10. **⭐⭐⭐ "一个重新断言被删除了：它单独重发 `clientInfos` 那一节【对一个空基准】而消息的其余部分仍对【一个真实基准】做增量 —— 一个节内局部空基准而线上【没有任何东西声明它】"`** ⇒ **那正是它被造出来绕开的那个缺陷**；**真正的修复是 `deltaMessage = -1` 的清 + `SnapshotBaselineFlag` 的声明** —— **"那也正是零售做的，而那就是为什么零售不需要它自己的重新断言"**。</br>
11. **⭐⭐⭐ 按钮位的"每比特首次目击，从不每次按下"** —— **"那是【一个常开仪器唯一可以有的形状】（第 `188d` 节）"**；**四种"有界"的手法**（按秒去重 / 值变化 / `200` 行预算 / 每比特首次）。
12. **⭐⭐⭐ "一个沉默的仪器与一个从未运行过的仪器不可区分"** ⇒ **必须有一个阳性对照**：**"若下面那个边永不触发而这个说 `0`，那么客户端真的没有发"`** —— 第三次"阳性对照"（与 §370、§405 同族）。

## 八、未闭合点

- `ServerReliableCommandCapacity` 的具体值。
- `ReliableKeyComplaintLimit` 的值。
- `processed.terminalCommand == ClientCommandKind::MoveDelta` 与 `MoveNoDelta` 的区别。
- `Message Acknowledge` 在 `MoveNoDelta` 时 `deltaMessage = -1` 的理由。
- `sub_429E10` 的 `oldcmd.buttons` 位 `0x4000`/`0x8000`/`0x10000`。
- `sv_client_mp.cpp` 1100 行之后未读取（**共 `4500` 行**）。
