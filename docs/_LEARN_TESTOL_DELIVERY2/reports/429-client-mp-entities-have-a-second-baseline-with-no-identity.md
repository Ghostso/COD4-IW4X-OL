# 429 · **"实体有一个第二基准，而它没有身份"** —— `dword_C89E050` 的 `70 × listPosition` 平铺数组、`deltaMessageDistance > 0 ⇔ baseline != nullptr ⇔ flag CLEAR` 的三重不变式

## 一、范围

本报告学习 `sv_client_mp.cpp` 1440–1790 行（`SV_SendClientMessages` 的软预算轮转、`dropClientSlot`、`buildSnapshotMessage` 的基准选择 —— **本文件里最密集的一段逆向**）。

## 二、**"实体有一个第二基准，而它没有身份"**（本组最重要的一段）

### 2.1 那段

```php
// ENTITIES HAVE A SECOND BASELINE, AND IT HAS NO IDENTITY (section 170). The
// frame ring is not the only place out.exe keeps entity rows. sub_470E90
// 0x00470e97 tests the BASELINE frame's snapFlags, and when bit 8 is set it reads
//     &dword_C89E050[70 * listPosition]
// -- a FLAT array indexed by list position alone, with no frame number and no
// generation. CL_ParseSnapshot resets its cursor at 0x00472223
//     mov dword ptr [0xc89e04c], 0
// inside the flag-8 block, so the array is refilled from position zero by EVERY
// flagged frame and holds exactly ONE generation: the newest flagged frame the
// client has parsed.
```

### 2.2 二十四层

```text
1. **实体有一个【第二基准】，而它【没有身份**】**
2. ⇒ **帧环【不是】`out.exe` 保存实体行的唯一地方**
3. ⇒ **`sub_470E90` 在 `0x00470e97` 测【那个基准帧的 `snapFlags`**】**
4. ⇒ **当位 `8` 被设时它读**：
5. ⇒ **`&dword_C89E050[70 * listPosition]`**
6. ⇒ **⇒ 一个【平铺数组，只按列表位置索引**】**
7. ⇒ **⇒ 而【没有帧号，没有代次**】**
8. ⇒ **`CL_ParseSnapshot` 在 `0x00472223` 重置它的游标**：
      · **`mov dword ptr [0xc89e04c], 0`**
9. ⇒ **在一个【位 `8`**】的块里**
10. ⇒ **⇒ 所以【那个数组【被每一个被标记的帧从位置零重新填充**】】**
11. ⇒ **⇒ 而【恰好持有一个代次：客户端已解析的【最新的那个被标记的帧**】】**
```

### 2.3 ⭐⭐⭐ **"一个平铺数组，只按列表位置索引 —— 没有帧号，没有代次"**

**✅ 这是本报告里**最重要的一条"一个无身份的缓存"**。**

**⇒ 三层**：
```text
帧环 ⇒ **每个条目有 `messageNum`** ⇒ **可寻址**
平铺数组 ⇒ **只有位置** ⇒ **只有一个代次**
⇒ **⇒ 所以【命名一个"旧的"被标记帧会让它的行对客户端的最新的行解码**】
```

**✅ 与 §427 的"`baselineFrame` 刻意地从不被用作 delta 源"**完全同族（**第二次"一个无身份的基准**）。

**⇒ 三层**：
```text
§426  **`clientInfo` 的名字缓冲在地图加载时被 memset**
§427  **`baselineFrame` 记录但不用作 delta 源**
§429  **`dword_C89E050` 只有位置没有帧号**
⇒ **⇒ 三次"无身份/已失效的基准**】
```

**✅ ⭐⭐⭐ **一个"无身份基准"的三例表**。

**⚠ 而"`70 * listPosition`"⇒ **`70` 字节/条**。**

**⇒ 三层**：
```text
`entityState_t` = `280` 字节（§414/§415）
而 `70 * listPosition` ⇒ **`70`？**
⇒ **⇒ 所以【这不是 `entityState_t` 数组**】
```

**⚠ 一个**需要核对的尺寸**（`70` vs `280`）—— **可能 `70` 是 `uint16` 的下标而元素是 `140` 或 `280` 字节**。

**⇒ 三层**：
```text
若 `dword_C89E050` 是 `uint32*` 而元素 `280` 字节 ⇒ **`280 / 4 = 70**`** ✓
⇒ **⇒ 所以【`70 * listPosition` 是【`uint32` 索引 ⇒ `280` 字节元素**】】
```

**✅ ⭐⭐ **一个"指针算术单位"的验证**（`70 × 4 = 280`）。

**✅ 与 §414 的"`280` 字节记录"**完全闭合 ✓

**⚠ 而"游标在四个地址"⇒ **`0x470edf` 读、`0x470f3b` 增、`0x472223` 重置、`0x5bec9c` `CL_ClearState`**。**

**✅ 与 §426 的"`CL_ClearState` 零化 `dword_C89E050` 与它的游标在 `0x005becb0`/`0x005bec9c`"**完全吻合 ✓

**⇒ 三层**：
```text
§426  `0x005becb0` 零化 + `0x005bec9c` 游标
§429  **§429 的四个地址里的 `0x5bec9c`**
⇒ **⇒ 同一对地址**
```

**✅ ⭐ **一个跨报告的地址闭合**。

### 2.4 而**"命名一个被标记帧作为 delta 基准只在它是我们发过的【最新**】被标记帧时才是正确的"**

**⇒ 而两个失败模式：**

```text
① 一个【在我们的基准里有而客户端的数组里没有**】的实体
   ⇒ **对 `0x0047114A` 的 memset-零行解码**（`modelIndex 0`, `origin 0`）
② 而【每一个 XOR 字段**】落在 `value ^ (baseSent ^ baseHeld)` **永久地**
   ⇒ **因为从那时起【我们相信客户端持有我们发的东西**】
```

**⇒ 十层**：
```text
1. **`value ^ (baseSent ^ baseHeld)`** ⇒ **一个永久的偏移**
2. ⇒ **因为【我们相信客户端持有我们发的**】**
3. ⇒ **⇒ 所以【那个错误【永不自我修正**】】**
4. ⇒ **而"`memset` 零行"** ⇒ **`modelIndex 0`, `origin 0`** ⇒ **一个不可见的实体**
5. ⇒ **⇒ 两个失败模式【对玩家【不可区分**】】**
```

### 2.5 ⭐⭐⭐ **"`value ^ (baseSent ^ baseHeld)` 永久地，因为从那时起我们相信客户端持有我们发的东西"**

**✅ 这是本报告里**最精确的一条"沉默的永久错误"**。**

**⇒ 三层**：
```text
若 `baseSent != baseHeld` ⇒ **每次解码差 `baseSent ^ baseHeld`**
而发送侧【以为客户端有 `baseSent`**】 ⇒ **差值不变**
⇒ **⇒ 所以【那个偏移【永不消失**】】
```

**✅ 与 §426 的"`CG_SetupClientCharacterInfo` 的早期返回 ⇒ 那个客户端再也没写过模型名"**同族（**第四次"一个沉默的状态永久不变**）。

**⇒ 三层**：
```text
§426  **`model=EMPTY`** ⇒ **永不写模型名**
§429  **`baseSent ^ baseHeld`** ⇒ **永不修正**
⇒ **⇒ 两次"永久**】
```

**✅ ⭐⭐ **一个"永久错误"的两例**。

### 2.6 而**"测量：零售在 `84` 份 demo 的 `0` 份里命名一个陈旧的被标记基准；把这修的旗标放置重放到我们自己的 `50` 份录制上，在 `8` 份里命名一个，`23` 帧，漂移 `1` 与 `2`"**

**⇒ 十层**：
```text
1. **零售：`0/84`**
2. ⇒ **我们的 50 份录制（重放这修的旗标放置）：`8/50`，`23` 帧**
3. ⇒ **漂移 `1` 与 `2`**
4. ⇒ **⇒ 所以【零售从不发送这种形状（`0/422478` delta 帧）**】**
5. ⇒ **而【零售也从不【在比赛中途**】进入被标记状态（`0/83` demo）**】**
6. ⇒ **⇒ 而【它的运行坐在【出生前**】而世界是静态的**
7. ⇒ **⇒ 所以【它未验证的缓存路径【在零售创建它的唯一地方是无害的**】】**
8. ⇒ **⇒ 而【我们的是比赛中途**】**
```

### 2.7 ⭐⭐⭐ **"零售在 `0/84` 里，我们在 `8/50` 里"**

**✅ 这是本报告里**最重要的一次"我们与零售的差异**。**

**⇒ 三层**：
```text
零售：**`0/84`** ⇒ **从不**
我们：**`8/50`（`16%`）** ⇒ **会**
⇒ **⇒ 所以【这个修复是【为我们自己的偏离**】而做的**
```

**✅ 与 §426 的"咬哪个客户端取决于它是否在进入世界之前确认过"**同族（**第三次"我们的状况与零售不同**）。

**⇒ 三层**：
```text
§408  **零售的 `32.7` 秒日程**
§426  **我们的客户端在地图加载时清空而零售不需要重新断言**
§429  **零售 `0/84` 而我们 `8/50`**
⇒ **⇒ 三次"我们偏离零售**】
```

**✅ ⭐⭐ **一个"偏离零售"的三例表**。

**⚠ 而"零售的运行坐【出生前**】"⇒ **所以它的旗标总在同一个静态世界**。**

**✅ 与 §413 的"`412` 的"⇒ 无关。

## 三、**"为何 `delta > 0` 而不是零售的 `delta == 0` 桥"**（本组第二重要）

### 3.1 那段

```php
// WHY DELTA > 0 AND NOT RETAIL'S DELTA == 0 BRIDGE. Retail exits a flagged run
// through delta==0 frames with the flag CLEAR, which the client decodes against
// its persistent cache &unk_C89A490 (0x00472246 -> 0x00472268). That path is
// checked by ONE BIT -- dword_C89E010 & 8, which is nothing but the cached frame's
// own snapFlags word (0xC89A490 + 0x3B80 = 0xC89E010). It carries no frame number,
// so a cache generation the client does not hold is a SILENT misdecode, which is
// the failure class we are removing.
```

### 3.2 二十层

```text
1. **零售【通过 `delta == 0` 帧（旗标【清**）】退出一段被标记的运行**
2. ⇒ **客户端【对它的持久缓存 `&unk_C89A490` 解码**】**
3. ⇒ **（`0x00472246` → `0x00472268`）**
4. ⇒ **⚠ 那条路径【被【一个位**】检查**
5. ⇒ **`dword_C89E010 & 8`**
6. ⇒ **⇒ 那【正是缓存帧自己的 `snapFlags` 字**】**
7. ⇒ **（`0xC89A490 + 0x3B80 = 0xC89E010`）**
8. ⇒ **⚠ 它【不携带帧号**】**
9. ⇒ **⇒ 所以【一个客户端【不持有**】的缓存代次【是一个【静默的错误解码**】】**
10. ⇒ **⇒ 那正是【我们正在消除的那个失败类**】**
```

### 3.3 ⭐⭐⭐ **"那条路径被一个位检查，它不携带帧号，所以一个客户端不持有的缓存代次是一个静默的错误解码"**

**✅ 这是本报告里**最重要的一条"为什么不用零售的桥**。**

**⇒ 三条路径对比**：

```text
路径 A：**`delta == 0` + flag CLEAR**（零售的桥）
  ⇒ **一个位检查**（`& 8`）
  ⇒ **无帧号** ⇒ **静默错**
路径 B：**`delta > 0`**（本修复的选择）
  ⇒ **`0x004722c0` 有效位 + `0x004722e8` `messageNum == deltaNum` + 四个环新鲜边界**
  ⇒ **每次失败都是 `*msg = 1`** ⇒ **一个被丢弃的快照**
  ⇒ **⇒ 所以【`delta > 0` 是被【自身身份检查**】约束的**
```

**✅ ⭐⭐⭐ **"零售的桥无检查而我们选的路径有检查"** —— 一个**用更严格的路径替换一个更宽松的**。

**✅ 与 §418 的"≥ 90% 才接受偏移"**同族（**第三次"用更严格的条件**）。

**⚠ 而"四个环新鲜边界"⇒ **`entities`（25600 条）、`clientInfos`、`clients`、`glass`**。**

**⇒ 三层**：
```text
`0x004722f0` ⇒ **entities（`25600` 条环）**
`0x0047230c` ⇒ **`clientInfos`**
`0x0047234f` ⇒ **`clients`**
`0x00472368` ⇒ **`glass`**
⇒ **⇒ 四个环各有自己的上界**】
```

**✅ ⭐⭐ **一个"四个环"的清单**。

**⚠ 而"`25600` 条 entities"⇒ **与 §413 的 `SnapshotHistoryCapacity = 32`**不同（那**是消息环**）。

**⇒ 三层**：
```text
`SnapshotHistoryCapacity = 32` ⇒ **消息环**
`25600` ⇒ **实体环**（**在客户端侧**）
⇒ **⇒ 两个不同的环，两个不同的大小**
```

**✅ ⭐ **一个"两个环"的区分**。

### 3.4 而**"收敛，那个被拒绝的『拒绝 ack』守卫没有的"**

```php
// Convergence, which the rejected "refuse the ack" guard did not have: while the
// acknowledgement still names a flagged frame we emit a DELTA, not another full,
// so newestFlaggedSnapshotMessage is FROZEN and the acknowledgement walks onto an
// unflagged frame within one round trip at any acknowledgement lag. The rejected
// guard emitted another flagged frame every tick, advancing the target in lockstep
// with the ack -- a permanent full-snapshot stream.
```

**⇒ 十四层**：
```text
1. **收敛性**
2. ⇒ **当 ack 仍然命名一个被标记帧时，我们发一个 **DELTA**
3. ⇒ **⇒ 而不是另一个 FULL**
4. ⇒ **⇒ 所以 `newestFlaggedSnapshotMessage` 【被冻结**】**
5. ⇒ **⇒ 而 ack 【在一个往返内走到一个未标记帧上**】**
6. ⇒ **⇒ 在任何 ack 滞后下**
7. ⇒ **⚠ 被拒绝的守卫【每一 tick 发另一个被标记帧**】**
8. ⇒ **⇒ 把目标【与 ack 同步推进**】**
9. ⇒ **⇒ 【一个永久的 full-snapshot 流**】**
```

### 3.5 ⭐⭐⭐ **"那个被拒绝的守卫每一 tick 发另一个被标记帧，把目标与 ack 同步推进 —— 一个永久的 full-snapshot 流"**

**✅ 这是本报告里**最重要的一条"反馈回路设计**。**

**⇒ 三层**：
```text
错误设计：**每 tick 发一个被标记帧** ⇒ **目标随 ack 前进** ⇒ **永不收敛**（**同步推进**）
正确设计：**发 DELTA** ⇒ **目标冻结** ⇒ **ack 走到未标记帧上** ⇒ **收敛**
⇒ **⇒ 所以【"冻结那个目标"是收敛的条件**】
```

**✅ 与 §413 的"`thinkBudget` 会复合"**同族（**第三次"一个反馈回路**）。

**⇒ 三层**：
```text
§413  **落后 ⇒ delta 大 ⇒ 一次花光预算 ⇒ 更落后**（**正反馈**）
§429  **错误设计：目标与 ack 同步推进 ⇒ 永不收敛**（**无反馈**）
§429  **正确设计：目标冻结 ⇒ 一个往返收敛**（**负反馈**）
⇒ **⇒ 三次"反馈的方向**】
```

**✅ ⭐⭐⭐ **一个"反馈方向"的三例表**。

**⚠ 而"我们的 lag 是 `1-2` 帧的 `97%`"⇒ **所以这个状态持续一或两帧**。**

**✅ 与 §425 的"`200` 行预算"**不同（这是**一个实测的收敛速度**）。

### 3.6 而**"活跃性规则，而它不需要一个计时器"**

```php
// And if the newest flagged frame has aged out of SnapshotDeltaWindow or its
// history entry is gone, selectBaseline fails, `baseline` stays null, and the next
// line makes this a fresh FULL frame -- which re-arms
// newestFlaggedSnapshotMessage. That is the liveness rule, and it needs no timer.
```

**⇒ 十层**：
```text
1. **若最新的被标记帧【老化出**】`SnapshotDeltaWindow`**
2. ⇒ **或【它的历史条目没了**】**
3. ⇒ **`selectBaseline` 失败**
4. ⇒ **`baseline` 保持 `null`**
5. ⇒ **⇒ 而下一行让它成为一个【新的 FULL 帧**】**
6. ⇒ **⇒ 那【重新武装**】`newestFlaggedSnapshotMessage`
7. ⇒ **⇒ 那就是【活跃性规则**】**
8. ⇒ **而它【不需要一个计时器**】**
```

**✅ ⭐⭐⭐ **"活跃性规则不需要一个计时器"** —— 与 §418 的"重复到 `baseline != nullptr` 这个协议内本来就有的信号出现"**完全同族**（**第二次"用机制而不是发明超时"）。

**⇒ 三层**：
```text
§418  `0x02` 重复到 `baseline != nullptr` ⇒ **不需要超时**
§429  活跃性由 `selectBaseline` 的失败驱动 ⇒ **不需要计时器**
⇒ **⇒ 两次"用已有的失败作信号**】
```

**✅ ⭐⭐⭐ **一个"无计时器的活跃性"的两例**。

## 四、**三重不变式**（本组第三重要）

### 4.1 那段

```php
// THE INVARIANT FROM HERE DOWN, and SV_WriteSnapshot asserts it:
//     deltaMessageDistance > 0  <=>  baseline != nullptr  <=>  flag CLEAR.
// `baseline` is now assigned in exactly one place, paired with its distance.
```

### 4.2 二十层

```text
1. **`deltaMessageDistance > 0`** ⇔ **`baseline != nullptr`** ⇔ **`flag CLEAR`**
2. ⇒ **三个量【必须同时成立或同时不成立**】**
3. ⇒ **而 `baseline` 【现在恰好在一个地方被赋值，与它的距离配对**】**
4. ⇒ **⇒ 所以【不可能出现"有基准而距离为零"**】**
5. ⇒ **⇒ **而距离为零正是客户端读作"非 delta"**（`0x004721AC`/`0x004721AE`）
```

### 4.3 ⭐⭐⭐ **"距离为零正是客户端读作『非 delta』"**

**✅ 这是本报告里**最重要的一条"一个零的语义**。**

**⇒ 三层**：
```text
`distance > 0` ⇒ **delta 到 `now - distance`**
`distance == 0` ⇒ **非 delta** ⇒ **客户端用【持久缓存**】
⇒ **⇒ 所以【`0` 是一个【分支开关**】不是"最近的那个帧**】**
```

**✅ 与 §416 的"`0` 是索引 0"**、§417 的"`2047` 是满值哨兵"**同族（**第四次"零/满值的语义**）。

**⇒ 三层**：
```text
§416  `team = 0` ⇒ **空指针**
§417  `field00E4 = 0` ⇒ **索引 0**
§429  `distance = 0` ⇒ **非 delta 分支**
⇒ **⇒ 三次"零是一个有效选择**】
```

**✅ ⭐⭐ **一个"零的语义"的三例表**。

### 4.4 而**"旧代码恢复 `baseline = client.baselineFrame.get()` 而让 `deltaMessageDistance` 为零"**

```php
// AND IT IS NOT A BASELINE WE CAN NAME ON THIS WIRE AT ALL (section 169). This
// used to restore `baseline = client.baselineFrame.get()` when the acknowledgement
// fell outside the history window -- while leaving deltaMessageDistance at ZERO,
// and distance zero is precisely what the client reads as "non-delta"
```

**⇒ 十层**：
```text
1. **旧代码：ack 落在历史窗口外 ⇒ `baseline = client.baselineFrame.get()`**
2. ⇒ **而【让 `deltaMessageDistance` 保持【零**】】**
3. ⇒ **⇒ 所以【客户端读作"非 delta"**】**
4. ⇒ **⇒ 而【我们发的是【delta**】】**
5. ⇒ **⇒ 【一个致命的不一致**】
6. ⇒ **而更糟：客户端保留的【不是它的内容**
7. ⇒ **`sub_472830` 只拷【头部字 `0x3B7C..0x3BB8`**】**
8. ⇒ **（`firstClientInfo` 在 `+0x3BAC`，`numClients` 在 `+0x3B9C`）**
9. ⇒ **⇒ 那些是【`608` 条环里的【裸索引**】】**
10. ⇒ **⇒ 而在两个玩家下【约十五秒就回收**】**
```

### 4.5 ⭐⭐⭐ **"服务器保留条目；客户端保留一个会移动的窗口"**

**✅ 这是本报告里**最重要的一条"两端存储的不对称**。**

**⇒ 三层**：
```text
服务器：**保留 `snapshotHistory` 里的帧指针**（`32` 条）
客户端：**只保留 `firstClientInfo`/`numClients` 两个索引**（进 `608` 条环）
⇒ **⇒ 所以【不能用"客户端缓存了那一帧"来推断"客户端持有那一帧的内容**】**
```

**✅ 与 §426 的"客户端进入世界时扔掉了它的快照状态"**同族（**第五次"客户端的持有是不可推断的**）。

**⇒ 三层**：
```text
§426  **客户端清空了六个状态**
§427  **`baselineFrame` 刻意不用于 delta**
§429  **客户端只保留两个索引而环 `15` 秒回收**
⇒ **⇒ 三次"不要假设客户端持有**】
```

**✅ ⭐⭐ **一个"不要假设客户端持有"的三例表**。

## 五、**`SnapshotBaselineFlag` 的真实语义**（本组第四重要）

### 5.1 那段

```php
// AND SnapshotBaselineFlag IS NOT "THIS MESSAGE INITIALIZES THE CACHE" (section
// 169). It is the ONLY thing on this wire that tells out.exe which baseline to
// decode against, and the client reads it as "every section of this message is
// encoded against an EMPTY baseline". CL_ParseSnapshot 0x0047222E clears its
// baseline pointer, KEEPS the null if the flag is set (0x0047223D), and otherwise
// deltas against its PERSISTENT cached snapshot (0x00472246 -> 0x00472268) whose
// valid bit dword_C89E010 is that snapshot's own snapFlags word, written by the
// struct copy at 0x00472849. Any extra condition here writes ABSOLUTE values into
// a message the client decodes as a DELTA -- and the codec is a symmetric XOR
// (writeUnsignedDelta's `value ^ (baseline & mask)` against the client's
// `readBits ^ (mask & baseline)` at 0x0066FE68), so a field whose held value
// already equals the transmitted one decodes to V ^ V = ZERO.
```

### 5.2 二十四层

```text
1. **`SnapshotBaselineFlag` **不是**"这条消息初始化缓存"**
2. ⇒ **它是【这条线缆上【唯一**】告诉 `out.exe` 对哪个基准解码的东西】
3. ⇒ **而客户端把它读作【"这条消息的【每一节**】都对一个【空基准**】编码"】
4. ⇒ **`CL_ParseSnapshot` 在 `0x0047222E` 清空它的基准指针**
5. ⇒ **【保留那个 null**】如果旗标被设（`0x0047223D`）**
6. ⇒ **否则**对它的【持久缓存快照**】做增量**（`0x00472246` → `0x00472268`）**
7. ⇒ **而它的有效位 `dword_C89E010` 是【那个快照自己的 `snapFlags` 字**】**
8. ⇒ **由 `0x00472849` 的结构拷贝写入**
9. ⇒ **⇒ 这里任何额外的条件【把【绝对值**】写进一条客户端【读作 delta**】的消息**】
10. ⇒ **⇒ 而那个编解码器【是一个对称 XOR**】**
11. ⇒ **（`writeUnsignedDelta` 的 `value ^ (baseline & mask)` 对客户端的 `readBits ^ (mask & baseline)`）**
12. ⇒ **⇒ 所以【一个【已持有值等于传输值**】的字段【解码成 `V ^ V = ZERO`**】**
```

### 5.3 ⭐⭐⭐ **"一个已持有的值等于传输的值解码成 `V ^ V = ZERO`"**

**✅ 这是本报告里**最重要的一条"XOR 的双重语义**。**

**⇒ 三层**：
```text
正确：**`wire = new ^ base`** ⇒ **客户端 `new ^ base ^ base = new`** ✓
错误：**`wire = new`（绝对值）** ⇒ **客户端 `new ^ base`**
⇒ **⇒ 而若 `new == base`** ⇒ **`new ^ new = 0`**
```

**✅ 与 §417 的"`310 ^ (1266 & 0x3FF) = 452`"**完全同族（**第二次"XOR 的对称性**）。

**⇒ 三层**：
```text
§415  **`writeUnsignedDelta` = `value ^ (baseline & mask)`**
§417  **客户端存 `ours ^ base`**
§429  **`V ^ V = ZERO`**
⇒ **⇒ 三次"XOR 对称性的后果**】
```

**✅ ⭐ **一个"XOR 语义"的三例表**。

**⚠ 而"额外条件"⇒ **"旧的 condition 还要求 `!baselineCacheAcknowledged` 与没有在飞的初始化器"**。**

**⇒ 十层**：
```text
旧：`initializeBaselineCache = !baseline && !baselineCacheAcknowledged && no initializer`
⇒ **⇒ 所以【在 `baseline` 仍为 null 时它为 FALSE**】**
⇒ **⇒ 而【一个往返，每一次运行，都是【未标记的空基准帧**】】**
新：`initializeBaselineCache = !baseline`
⇒ **⇒ 所以【旗标恰好是"没有基准"，没有别的**】**
```

**✅ ⭐⭐⭐ **"旗标恰好是『没有基准』，没有别的"** —— 与 §427 的"从握手化简成属性"**完全同族**（**第三次"一个旗标的语义化简**）。

**⇒ 三层**：
```text
§418  **`useEntityBaselines` 与 `constBaselines` 一个决定**
§427  **`SnapshotBaselineFlag` 是一个属性不是握手**
§429  **`initializeBaselineCache = !baseline`**（**最简形式**）
⇒ **⇒ 三次"旗标本义**】
```

**✅ ⭐⭐⭐ **一个"旗标本义"的三例表**。

### 5.4 而**"一个要求非 delta 快照的客户端必须得到一个"**

```php
// A CLIENT THAT ASKS FOR A NON-DELTA SNAPSHOT MUST GET ONE. Section 167:
// deltaMessage == -1 is the client saying, through clc_moveNoDelta, that it has
// NO usable snapshot state -- which is exactly what it says after a map load,
// because loading reinitialises cgame and that re-deals every characterInfo name
// buffer out of a freshly memset pool (0x004555D0). Substituting the persistent
// baseline frame there answers "I have nothing" with a delta against a frame the
// client no longer holds, and every field equal to that frame is then NEVER SENT
// AGAIN. For clientInfos that is permanent: modelIndex stays zero,
// CG_SetupClientCharacterInfo 0x00541800 takes its early return, no model name is
// ever written, and nobody can see that player for the rest of the match.
```

**⇒ 十六层**：
```text
1. **一个要求非 delta 快照的客户端【必须得到一个**】**
2. ⇒ **`deltaMessage == -1` 是客户端通过 `clc_moveNoDelta` 说【它没有可用的快照状态**】**
3. ⇒ **⇒ 那正是它在【一次地图加载之后**】说的**
4. ⇒ **因为加载【重新初始化 cgame**】**
5. ⇒ **⇒ 而那【从一个刚 memset 的池里重新分发每一个 `characterInfo` 名字缓冲**】**
6. ⇒ **⚠ 在那里【替换成持久基准帧**】**
7. ⇒ **⇒ 是【用【对一个客户端不再持有的帧的 delta**】回答"我什么都没有"**】**
8. ⇒ **⇒ 而【每一个等于那个帧的字段【从此【永不再发送**】】**
9. ⇒ **对 `clientInfos` 那是【永久的**】**
10. ⇒ **`modelIndex` 停在零**
11. ⇒ **`CG_SetupClientCharacterInfo` 取它的早期返回**
12. ⇒ **⇒ 而【没有人能看见那个玩家【整场比赛剩下的时间**】】**
```

**✅ 与 §426 的"咬哪个客户端只取决于它是否在进入世界之前确认过一份快照"**完全同源 ✓

**⇒ 三层**：
```text
§426  **四个状态在 `stage 6` 时清空**
§429  **`deltaMessage = -1` 必须换来一个 FULL**
⇒ **⇒ 而【§426 的清空【必须配合**】§429 的尊重**
```

**✅ ⭐⭐⭐ **一个"两端必须一致"的完整图景**。

**⚠ 而"持久缓存是 Ghosts 的 `hasAckedBaselineData`"⇒ **一个跨实现的概念对位**。**

**⇒ 三层**：
```text
`baselineCacheAcknowledged`（CODOL） ⇔ `hasAckedBaselineData`（Ghosts）
⇒ **⇒ 所以【同一个概念的两次命名**】
```

**✅ ⭐ **一个"概念对位"的实例**。

**⚠ 而"它【从来不是**】一个【对一个刚告诉我们它什么都没有的客户端扣留一个完整快照的许可**】"**

**✅ 这是本报告里**最有力的一句结论**。**

## 六、关键结论

1. **⭐⭐⭐ "实体有一个第二基准，而它没有身份"**：`sub_470E90` 在 `0x00470e97` 测基准帧的 `snapFlags`，位 `8` 被设时读 `&dword_C89E050[70 * listPosition]` —— **一个平铺数组，只按列表位置索引，没有帧号，没有代次**；`CL_ParseSnapshot` 在 `0x00472223` 重置游标（`mov dword [0xc89e04c], 0`）⇒ **只持有一个代次：客户端已解析的最新的那个被标记帧**。
2. **⭐ `70 × 4 = 280`** ⇒ `dword_C89E050` 是 `uint32*` 而元素是 `280` 字节 ⇒ 与 §414 的"`280` 字节记录"闭合。
3. **⭐ 游标的四个地址**（`0x470edf` 读 / `0x470f3b` 增 / `0x472223` 重置 / `0x5bec9c` `CL_ClearState`）—— 而 §426 已记录 `0x005becb0`/`0x005bec9c`，**同一对**。
4. **⭐⭐⭐ "命名一个被标记帧作为 delta 基准只在它是【我们发过的最新】被标记帧时才是正确的"**，否则两个失败模式：**一个在我们基准里而客户端数组里没有的实体解码成 memset 零行**（`modelIndex 0`, `origin 0`），**而每一个 XOR 字段落在 `value ^ (baseSent ^ baseHeld)` 永久地**。
5. **⭐⭐⭐ "永久地，因为从那时起我们相信客户端持有我们发的东西"`** —— 第二次"一个沉默的状态永久不变"（与 §426 同族）。
6. **⭐⭐⭐ "零售在 `0/84` 份 demo 里命名一个陈旧的被标记基准；我们（重放这个修复的旗标放置）在 `8/50` 里，`23` 帧，漂移 `1` 与 `2`"`** —— 第三次"我们偏离零售"；而**零售也从不【在比赛中途】进入被标记状态（`0/83`）**，**它的运行坐在出生前而世界是静态的** ⇒ **它未验证的缓存路径在它创建它的唯一地方是无害的**。
7. **⭐⭐⭐ "为何 `delta > 0` 而不是零售的 `delta == 0` 桥"**：**零售的桥被【一个位】检查（`dword_C89E010 & 8`，那只是缓存帧自己的 `snapFlags`），不携带帧号 ⇒ 一个客户端不持有的缓存代次是【静默的错误解码】**；而 **`delta > 0` 路径被 `0x004722c0` 的有效位、`0x004722e8` 的 `messageNum == deltaNum`、以及四个环新鲜边界（`entities` `25600` 条 / `clientInfos` / `clients` / `glass`）policed，每次失败都是 `*msg = 1` ⇒ 一个被丢弃的快照**。
8. **⭐⭐⭐ "收敛，那个被拒绝的『拒绝 ack』守卫没有的"**：**我们发 DELTA ⇒ `newestFlaggedSnapshotMessage` 冻结 ⇒ ack 在一个往返内走到未标记帧上**；**而那个守卫每一 tick 发另一个被标记帧、把目标与 ack 同步推进 ⇒ 一个永久的 full-snapshot 流** —— **第三次"反馈方向"（与 §413 的正反馈对照）**。
9. **⭐⭐⭐ "活跃性规则不需要一个计时器"**：**若最新的被标记帧老化出 `SnapshotDeltaWindow` 或历史条目没了 ⇒ `selectBaseline` 失败 ⇒ `baseline` 为 null ⇒ 下一行是 FULL ⇒ 重新武装** —— 第二次"用机制而不是发明超时"（与 §418 的 `0x02` 同族）。
10. **⭐⭐⭐ 三重不变式**：**`deltaMessageDistance > 0` ⇔ `baseline != nullptr` ⇔ flag CLEAR**，而 **`baseline` 恰好在一个地方被赋值，与它的距离配对** ⇒ **"不可能出现有基准而距离为零"**。
11. **⭐⭐⭐ "距离为零正是客户端读作『非 delta』"`** —— 第四次"零是一个有效选择"（与 §416、§417 同族）。
12. **⭐⭐ 旧代码的致命不一致**：**ack 落在历史窗口外 ⇒ 恢复 `baseline = client.baselineFrame.get()` 而让 `deltaMessageDistance` 为零 ⇒ 客户端读作非 delta 而我们发的是 delta**；而 **`sub_472830` 只拷头部字 `0x3B7C..0x3BB8`（`firstClientInfo +0x3BAC`、`numClients +0x3B9C`）—— 裸索引进一个 `608` 条环，两个玩家下约十五秒回收**。
13. **⭐⭐⭐ "服务器保留条目；客户端保留一个会移动的窗口"`** —— 第五次"不要假设客户端持有"。
14. **⭐⭐⭐ `SnapshotBaselineFlag` 的**真实**语义**：**它不是"这条消息初始化缓存"，它是【这条线缆上唯一告诉 `out.exe` 对哪个基准解码的东西】，而客户端读作"这条消息的【每一节】都对一个【空基准】编码"**；`CL_ParseSnapshot` 在 `0x0047222E` 清指针、`0x0047223D` 保留 null、否则 `0x00472246`→`0x00472268` 对持久缓存做增量。
15. **⭐⭐⭐ "一个已持有的值等于传输的值解码成 `V ^ V = ZERO`"`** —— 第二次"XOR 对称性"（与 §417 的 `310 ^ 242 = 452` 同族）。
16. **⭐⭐⭐ 旧 condition 的三个额外条件（`!baselineCacheAcknowledged` 与没有在飞的初始化器）在 `baseline` 仍为 null 时让旗标为 FALSE** ⇒ **"一个往返，每一次运行，都是未标记的空基准帧"** ⇒ **新 condition 是 `initializeBaselineCache = !baseline`，即"旗标恰好是『没有基准』，没有别的"`** —— 第三次"旗标本义的化简"。
17. **⭐⭐⭐ "一个要求非 delta 快照的客户端必须得到一个"**：**`deltaMessage == -1` 是客户端通过 `clc_moveNoDelta` 说"我没有可用的快照状态"**（**那正是地图加载之后**）⇒ **在那里替换成持久基准帧是用"对一个客户端不再持有的帧的 delta"回答"我什么都没有" ⇒ 【每一个等于那个帧的字段从此永不再发送】⇒ 对 `clientInfos` 那是**永久的**：`modelIndex` 停在零、`CG_SetupClientCharacterInfo` 取早期返回、**没有人能看见那个玩家整场比赛剩下的时间**。
18. **⭐⭐ "持久缓存是 Ghosts 的 `hasAckedBaselineData`，它【从来不是】一个【对一个刚告诉我们它什么都没有的客户端扣留一个完整快照的许可】"`** —— 一句最有力的结论。

## 七、未闭合点

- `dword_C89E050` 的元素是 `280` 字节还是别的（`70 × 4 = 280` 是我的推断）。
- `25600` 条 `entities` 环的条目大小。
- `0x004722c0` / `0x004722e8` / `0x004722f0` / `0x0047230c` / `0x0047234f` / `0x00472368` 六个检查的完整语义。
- `608` 条 `clientInfo` 环的容量来源。
- `SnapshotDeltaWindow = 29`（§416）与 `SnapshotHistoryCapacity = 32`。
- `sv_client_mp.cpp` 1790 行之后未读取（**共 `4500` 行**）。
