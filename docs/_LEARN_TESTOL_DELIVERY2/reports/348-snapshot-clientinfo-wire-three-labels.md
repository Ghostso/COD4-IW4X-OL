# 348 · **"一个标签不能把两个答案塌缩成一个词"** —— `clientinfo WIRE` 的三种基线标签、十五种写失败名、段的固定顺序与 EOF、`reset()` 的镜像阶段

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 10974–11197 行（`SV_WriteSnapshot` 尾 + `SvServerWorld::reset` 起），
并补上 10139–10168 的 `SV_SnapshotWriteFailure` 名字表。

## 二、`SV_SnapshotWriteFailure` 的**十五种**（补 10139–10168）

```cpp
None / InvalidFrame / MissingPlayerState / InvalidBaselineFrame /
MissingBaselinePlayerState / MapCenterMismatch / DeltaWithoutBaseline /
BaselineInitializationWithBaseline / PlayerState / AnimationCommands /
Clients / PacketEntities / ClientInfos / Glass / Overflow
```

### 2.1 三层分类

```text
① 前置条件（7 种）
   InvalidFrame / MissingPlayerState / InvalidBaselineFrame /
   MissingBaselinePlayerState / MapCenterMismatch /
   DeltaWithoutBaseline / BaselineInitializationWithBaseline
② 段内写失败（6 种）
   PlayerState / AnimationCommands / Clients / PacketEntities /
   ClientInfos / Glass
③ 全局（2 种）
   Overflow / None
```

### 2.2 而**七个前置条件是一对互斥的**

```cpp
if (!baseline && deltaMessageDistance) return reject(DeltaWithoutBaseline);
if (baseline && initializeBaselineCache) return reject(BaselineInitializationWithBaseline);
```

**⇒ 三层**：

```text
1. **无基线而有 delta 距离 ⇒ 拒绝**
2. ⇒ **有基线而要求初始化缓存 ⇒ 拒绝**
3. ⇒ **两个是同一对角的两端**（一致性）
```

**✅ 与 §347 五 的"`emptyBaselineOnWire` / `initializeBaselineCache` / `deltaMessageDistance`"**完全一致 ✓**

**⇒ 三条线事实的两两组合。**

### 2.3 而**六种段名与段的顺序一一对应**

```text
PlayerState  →  AnimationCommands  →  Clients  →  PacketEntities
             →  ClientInfos        →  Glass
```

**✅ 与 §347 八 的"playerstate, 动画命令, clients, entities, client infos 和 glass 恰好这个顺序"**完全一致 ✓**

**⇒ **一个名字表就是一份段清单。**

**✅ 与 §346 的十九种 `SvSnapshotFrameValidationFailure` **同族（**第二个枚举 + 名字函数**）。

## 三、**`clientinfo WIRE` 的三标签**（本组最重要的一段）

### 3.1 那段

```php
// WHAT THIS OBSERVER WAS ACTUALLY TOLD. Section 167: with the validation
// failure fixed, one client resolves both players and the other resolves
// neither, from the same server on the same frame -- so the difference is
// PER OBSERVER, which is the one thing no shared-frame reasoning can explain
// and no client-side probe can see. Every entry is either written in full
// (the observer had no baseline for it), written as a delta, or SKIPPED as
// unchanged -- and "skipped as unchanged" against a client that never got the
// original is exactly a player with modelIndex zero, which is a player with no
// model name, which is a player nobody can see. Deduped on the whole line, so
// it is silent while the answer is not changing.
```

### 3.2 十一层

```text
1. **这个观察者实际被告知了什么**
2. ⇒ 第 167 节：在验证失败被修好之后，【一个客户端解析出两个玩家而另一个一个也解析不出】
3. ⇒ **从同一个服务器、同一帧**
4. ⇒ **所以差别是【每观察者】的**
5. ⇒ **那是任何共享帧推理都无法解释、而任何客户端侧探针都看不见的一件事**
6. ⇒ **每一条目要么以全量写出**（观察者对那条目没有基线）
7. ⇒ **要么以一个 delta 写出**
8. ⇒ **要么作为【未变】被跳过**
9. ⇒ **而"作为未变被跳过"对一个从未收到原件客户端而言**
10. ⇒ **恰好就是一个 `modelIndex` 为零的玩家，也就是一个没有模型名的玩家，也就是一个没人能看见的玩家**
11. ⇒ **整行去重，所以在答案不变时它是静默的**
```

### 3.3 **"唯一一个共享帧推理解释不了而客户端探针看不见的东西"**

**✅ 这是本文件里**最精确的"为什么需要这个仪器"**。**

**⇒ 三层**：

```text
服务端共享帧推理   ⇒ 同一帧对所有客户端相同 ⇒ 解释不了差异
客户端侧探针       ⇒ 只看自己收到的东西 ⇒ 看不见自己【没】收到的东西
⇒ 所以必须【在服务端、按观察者】打印
```

**✅ 与 §347 五.7 的"这是线半而对另一半盲"**同族（**第三次"说出仪器的边界"**）。**

### 3.4 而**三个标签**

```cpp
(clientInfoBaseline ? " baseline=frame"
    : (initializeBaselineCache ? " baseline=empty(flagged)"
                               : " baseline=empty(UNFLAGGED)"))
```

**⇒ 三层**：

```text
frame             有基线（正常）
empty(flagged)    **空基线【而】快照头写了 SnapshotBaselineFlag**（良性 —— 客户端同意）
empty(UNFLAGGED)  **空基线而头没写那个标志**（【缺陷】）
```

### 3.5 而**为什么必须三个（本组核心）**

```php
// AND THE LABEL MUST NOT COLLAPSE TWO ANSWERS ONTO ONE WORD. This
// printed "baseline=NONE" for both the SIGNALLED empty baseline (benign,
// SnapshotBaselineFlag is on the wire and the client agrees) and the
// UNFLAGGED one (the defect). That single word is why the fault sat in
// recorded runs without being seen.
```

**⇒ 六层**：

```text
1. **而那个标签绝不能把两个答案塌缩成一个词**
2. ⇒ **这过去为【被信号化的】空基线（良性）与【未标志的】（缺陷）都打印 "baseline=NONE"**
3. ⇒ **而那个单一的词就是那个故障在已记录的运行里坐着而不被看见的原因**
4. ⇒ 所以现在三分
```

**✅ **这是本文件里最珍贵的一条工程教训：一个过粗的标签把一个缺陷藏了整整一批录制的 run。** **

**⇒ 与 §346 的"沉默的合取成了头号 frameReject"**同族。**

**⇒ **第二次"可观测性本身是缺陷源"。**

### 3.6 而**三种条目标签**

```cpp
wire += ... + (!previous ? "(FULL)" : (unchanged ? "(omitted)" : "(delta)"));
```

**⇒ 三层**：

```text
(FULL)     无基线 ⇒ 全量写
(omitted)  有基线且三个字段相同 ⇒ 跳过
(delta)    有基线而不同 ⇒ delta
```

**✅ 而 `unchanged` 只比较**三个字段**：**

```cpp
previous->customization.modelIndex == entry.customization.modelIndex &&
previous->customization.characterItemId == entry.customization.characterItemId &&
previous->customization.bodyModelConfigStringIndex ==
    entry.customization.bodyModelConfigStringIndex
```

**⚠ 而 §341 的 `writeClientInfoDelta` 比较**整条记录**（`*entryBaseline == clientInfos[currentIndex]`）。**

**⇒ 两处**不同的比较范围**。**

**⚠ 所以日志的 `(omitted)` 可能与实际行为**不一致**（日志说 omitted 而实际发了）。**

**⇒ 一处**仪器与实现不同步**。**

**⚠ 但方向是**保守**的（日志可能少报 omitted）。**

### 3.7 而**五个字段的打印**

```text
model<modelIndex> / item<characterItemId> / body<bodyModelConfigStringIndex> / f<faction>
```

**⇒ 四个（不是五个）。**

### 3.8 而**为什么加 faction 而不加 team**

```php
// OLMOD(clientinfo-faction-witness, 20261016-0450): the faction selector and
// the team, ON THE LINE THAT ALREADY EXISTS AND IS ALREADY DEDUPED. A new line
// per frame would violate this project's own hot-path rule (P5: zero logs per
// frame); this one only prints when the digest changes, so it costs nothing
// until the answer moves. Purpose: settle whether the 1-bit faction ever
// reaches the wire -- "server sent it and client read 0" and "server never sent
// it" are the two possibilities left, and this line separates them.
// AND THE TEAM IS NOT ADDED HERE: SvClientInfoState has no team member at all
// (clientState +0x404 is the CLIENT's own and is already correct on the wire
// side), so only the faction selector this wire actually carries is reported.
```

### 3.9 十层

```text
1. **派系选择子与队伍，在【已经存在且已经去重】的那一行上**
2. ⇒ **每帧一行新的会违反本项目自己的热路径规则（P5：每帧零日志）**
3. ⇒ **这一行只在摘要变化时打印，所以直到答案移动前它零成本**
4. ⇒ **目的：settle 那个 1 位派系是否曾经到达线上**
5. ⇒ **"服务器发了而客户端读成 0"与"服务器从未发它"是剩下的两个可能性**
6. ⇒ **而这一行把它们分开**
7. ⇒ **而队伍【不加】在这里：`SvClientInfoState` 根本没有 team 成员**
8. ⇒ **（`clientState +0x404` 是【客户端自己的】而在线侧已经正确）**
9. ⇒ **所以只报告这条线真正携带的派系选择子**
```

**✅ 与 §341 的"字段 18 `faction` 1 位"**完全一致 ✓**

**⇒ 而 `clientState + 0x404` 是**客户端的 team**（与 §337 的 `clientState +0x08` 的 team 不同）。**

**⚠ 所以**两个 team**：**

```text
clientState +0x08   实体/客户端状态里的 team（§337）
clientState +0x404  客户端自己的 team（这里）
```

**⚠ 一处**需要核对的偏移**。**

### 3.10 而 **`digest` 与 `reportedWire`**

```cpp
static std::array<std::size_t, MaximumGameClients> reportedWire{};
const auto digest = std::hash<std::string>{}(wire);
if (clientNum < reportedWire.size() && reportedWire[clientNum] != digest) {
    reportedWire[clientNum] = digest;
    OlMod::RuntimeLog::write(..., wire);
}
```

**✅ 与 §347 五.7 的 `SNAPSHOT BASELINE MISMATCH` **完全同一个实现**。**
**⇒ 所以**两处复制**。**

**⚠ 一处**可以抽出的重复**。**

### 3.11 而 **`entries NONE`**

```cpp
if (frame.clientInfos.empty()) wire += " NONE";
```

**✅ 与 §341 的"`clientInfos` 段在 66% dm / 46% war / 85% clash 快照上完全为空"配合。**

**⇒ 而 `NONE` 让"空"变成一个**被记录的事实**而不是一个缺失。**

**✅ 与 §340 的"缺席是证据"同族。**

## 四、**`SV_WriteGlassChanges` 是最后一个由 `CL_ParseSnapshot` 拥有的段**（本组第二重要）

```php
if (!SV_WriteGlassChanges(message, frame.glassPieces,
        baseline ? &baseline->glassPieces : nullptr))
{
    return reject(SvSnapshotWriteFailure::Glass);
}
// CODREF(sv_write_snapshot_to_client): glass is the final
// CL_ParseSnapshot-owned section. Once its mixed cursor advances past
// the last glass byte, EOF belongs to the outer command loop.
message.MSG_WriteByte(ServerCommandEof);
```

### 4.1 五层

```text
1. **glass 是最后一个 `CL_ParseSnapshot` 拥有的段**
2. ⇒ **一旦它的混合游标越过最后一个 glass 字节**
3. ⇒ **EOF 属于【外层命令循环】**
4. ⇒ 所以写一个 `ServerCommandEof` 字节
5. ⇒ **这是整个快照的终点**
```

**✅ 与 §346 的"`CL_ParseSnapshot` 0x0046D170"配合。**

### 4.2 而**"mixed cursor"**

**⇒ 三层**：

```text
1. `CL_ParseSnapshot` 用一个【混合】游标
2. ⇒ **bit 游标 + byte 游标**
3. ⇒ **越过最后一个 glass 字节** = byte 游标跨过边界
```

**✅ 与 §258 的"`msg_t` 两个游标独立前进"**完全一致 ✓**

**⇒ **第二次确认那个双游标模型。**

### 4.3 而**`ServerCommandEof` 的语义**

**⇒ 三层**：

```text
1. 快照段在此结束
2. ⇒ **后面的字节属于外层命令循环**（可能还有别的 ServerCommand）
3. ⇒ **所以 EOF 不是包尾**
```

**✅ 一个**段尾 vs 包尾**的区分。**

## 五、**`commandDelivery` 的提交在最后**（本组第三重要）

```php
if (commandDelivery) {
    for (const auto &[actor, signature] : deliveredCommands)
        if (actor->number < commandDelivery->delivered.size())
            commandDelivery->delivered[actor->number] = signature;
}
return true;
```

### 5.1 四层

```text
1. **投递状态在【整个快照成功之后】才提交**
2. ⇒ **所以一个溢出会重试整批**
3. ⇒ **一个失败的快照不消耗投递配额**
4. ⇒ **最后才 `return true`**
```

**✅ 与 §347 八 的注释"只在完整快照成功之后提交投递，所以一个溢出会重试整批"**完全一致 ✓**

**⇒ 一个**事务性的投递**。**

**⚠ 而 §347 八.3 的 `newDeliveryGeneration` 会在**读时**清空 —— 所以顺序是**先清除（若新代际）→ 读 → 最后提交**。**

**✅ 一个**三阶段的正确顺序**。**

## 六、`SvServerWorld::reset()` 的**镜像阶段**（本组第四重要）

```cpp
void SvServerWorld::reset()
{
    if (nativeEntityMirrorSynchronizer_) {
        static_cast<void>(nativeEntityMirrorSynchronizer_(
            SvNativeEntityMirrorPhase::Collision, {}, {},
            snapshot_.serverTime));
    }
    nativeEntityMirrorSynchronized_ = false;
    snapshot_ = {};
    zombieDamageNumbers_.clear();
    zombieInjuries_.clear();
    zombieScoreFeedback_.clear();
```

### 6.1 四层

```text
1. **若有原生实体镜像同步器 ⇒ 用一个 【Collision】 阶段的空调用**
2. ⇒ **（空的两个参数 ⇒ 清空）**
3. ⇒ **然后用旧的 `snapshot_.serverTime`**
4. ⇒ **再清 `snapshot_` 与三个容器**
```

**⚠ 而 `nativeEntityMirrorSynchronizer_` 与记忆里的"战斗服 `world` 从未绑定"**相关**。**

**⇒ 但这里是**客户端侧**的实体镜像（原生 = 客户端那套）。**

**✅ 与 §345 的"`SV_WritePacketEntities` 的准入"**不同阶段**。**

### 6.2 而**"用旧的 `serverTime` 清空"**

**⇒ 三层**：

```text
1. 清空发生在 `snapshot_ = {}` 之【前】
2. ⇒ **所以 `serverTime` 还是旧值**
3. ⇒ **而阶段是 `Collision`**
```

**✅ 一个**顺序敏感的清理**。**

**⚠ 为什么用旧时间？可能因为要**撤销**在旧时刻施加的镜像。**

**✅ 合理。**

## 七、关键结论

1. **`SV_SnapshotWriteFailure` 的十五种**，而**七种前置 / 六种段 / 二种全局**。
2. **七种前置里有两个是同一对角的两端**（`DeltaWithoutBaseline` / `BaselineInitializationWithBaseline`）。
3. **六种段名与段的顺序一一对应** —— 一个枚举就是一份段清单。
4. **⭐ "一个标签不能把两个答案塌缩成一个词"** —— `baseline=NONE` 曾同时表示良性的被信号化空基线与缺陷的未标志空基线，**而那个单一的词就是故障在已记录 run 里坐着而不被看见的原因**。
5. **`clientinfo WIRE` 的三个基线标签**（`frame` / `empty(flagged)` / `empty(UNFLAGGED)`）。
6. **三个条目标签**（`(FULL)` / `(omitted)` / `(delta)`），而 `unchanged` 只比**三个字段**而 `writeClientInfoDelta` 比**整条记录** —— **一处仪器与实现不同步**（方向保守）。
7. **"每观察者"是唯一共享帧推理解释不了、客户端探针看不见的维度**。
8. **"作为未变被跳过"对一个从未收到原件的客户端 = `modelIndex` 零 = 没人能看见的玩家**。
9. **为什么加 faction 不加 team**：`SvClientInfoState` 没有 team 成员；`clientState +0x404` 是客户端自己的 team。
10. **`P5: 每帧零日志`** —— 一个明确的热路径规则，所以仪器必须搭乘已去重的那一行。
11. **`entries NONE`** 让"空"成为一个被记录的事实。
12. **glass 是最后一个 `CL_ParseSnapshot` 拥有的段**，之后是 `ServerCommandEof`（**段尾不是包尾**）。
13. **"mixed cursor"第二次确认双游标模型**（bit + byte）。
14. **`commandDelivery` 在整快照成功后提交** —— 事务性投递，溢出会重试整批。
15. **`reset()` 先以 `Collision` 阶段的空调用撤销镜像（用旧 `serverTime`），再清状态**。

## 八、未闭合点

- `clientState +0x404` 与 `clientState +0x08` 两个 team 的关系。
- `clientinfo WIRE` 的 `unchanged` 三字段与 `writeClientInfoDelta` 整条记录的比较差异是否会误导。
- `ServerCommandEof` 之后外层命令循环还有什么。
- `nativeEntityMirrorSynchronizer_` 的阶段枚举全表。
- `sv_snapshot_mp.cpp` 11197 行之后未读取（27,016 行，进度 41%）。
