# 417 · **"一个非零默认值落进 `wireZeroBaseline()` 也相等，于是永不发送"** —— `SvEntityState` 的三字段哨兵、`+0x5C` 一偏移四义、以及"命名要靠偏移而不是发明"

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 1650–1990 行（`SvAgentState` 的 `24` 字段、`SvClientInfoState`、`SvEntityState` 的四族成员）。

## 二、**"非零默认值会落进 `wireZeroBaseline()` 而相等"**（本组最重要的一段）

### 2.1 那段

```cpp
// NONE OF THESE CARRIES A NON-ZERO DEFAULT, deliberately. A non-zero
// default lands in wireZeroBaseline() too, compares equal, and is then
// never sent -- the exact bug that cost the scriptmover sentinels their
// first frame. spawnZombieActor sets them explicitly instead.
```

### 2.2 十六层

```text
1. **这些里【没有一个】携带一个非零默认值**，故意的**
2. ⇒ **一个非零默认值【也落进 `wireZeroBaseline()`**】**
3. ⇒ ⇒ **它比较相等**】
4. ⇒ **⇒ 于是【永不发送**】**
5. ⇒ **那正是【让 scriptmover 的哨兵丢掉它们第一帧**】的那个 bug**
6. ⇒ **`spawnZombieActor` 【显式地】设置它们**
```

### 2.3 ⭐⭐⭐ **"一个非零默认值落进零基准 ⇒ 比较相等 ⇒ 永不发送"**

**✅ 这是本报告里**最重要的一条默认值陷阱**。**

**⇒ 三层**：
```text
机制：`wireZeroBaseline()` **把成员的值填进基准**
⇒ 若一个成员的默认值【就是它该发的值】 ⇒ **两者相等 ⇒ 不发**
⇒ **⇒ 所以【一个"正确的默认"等于"永远不发送"**】
```

**✅ 与 §416 的"用 `0` 而不是 `-1` 来少发"**相反**（那里**故意让它相等**，这里**相等是 bug**）。

**⇒ 三层**：
```text
§416  `cursorHintString = 0` ⇒ **相等是有意的节省**
§417  `lerpData0058{2047}` ⇒ **相等是无意的遗漏**
⇒ **⇒ 同一个机制，相反的意图**
```

**✅ ⭐⭐⭐ **"同一个机制可以是优化也可以是缺陷，取决于意图"** —— 一个**极精细的区分**。

**⚠ 而"`lerpData0058{2047}` 与 `scriptMoverField00E4{255}` 是**有默认值的**"：**

```cpp
std::uint32_t lerpData0058{ 2047 };
std::uint32_t scriptMoverField00E4{ 255 };
```

**⇒ 三层的矛盾**：
```text
注释（1930 行）："NONE OF THESE CARRIES A NON-ZERO DEFAULT"
实际（1806/1807 行）：**`lerpData0058{2047}` 与 `scriptMoverField00E4{255}` 是非零默认**
```

**⚠ 但 1930 行的注释说的是 **ET_ACTOR 那一族**（1918 行是 `---- ET_ACTOR ----` 分节），而 `lerpData0058` 属于 **scriptmover 那一族**。

**⇒ 三层**：
```text
`lerpData0058{2047}` ⇒ **在 ET_SCRIPTMOVER 节**（1795–1833）
`actorField0054{}`  ⇒ **在 ET_ACTOR 节**（1935 起）
⇒ **⇒ 所以【两条规则适用于两个族**】
```

**✅ ⭐ **一个"注释的作用域"必须读清的例子**。

**⇒ 而注释说"那正是让 scriptmover 的哨兵丢掉它们第一帧的那个 bug"** ⇒ **所以 scriptmover 的哨兵曾经因为"相等"而丢帧，现在的 `{2047}`/`{255}` 是【修复后的写法**】。**

**⇒ 五层**：
```text
过去：`lerpData0058` 默认 `0` ⇒ 而 `wireZeroBaseline` 里也是 `0` ⇒ **相等** ⇒ **那一位值为 `0`** ⇒ **不是 `2047` 的哨兵**
现在：`lerpData0058{2047}` ⇒ **`wireZeroBaseline()` 里也 `2047`** ⇒ **相等** ⇒ **仍是"不发"**……
```

**⚠ 等等，那现在的写法**仍然**会导致"不发"**。除非 `wireZeroBaseline()` **把数值字段清零**而**这些成员是例外**。

**⇒ 三层**：
```text
`wireZeroBaseline()` **可能不是 `SvEntityState{}` 而是【一个不同的零化函数**】
⇒ 而它【可能把 `lerpData0058` 设成 `2047`**】
⇒ **⇒ 所以"落进 `wireZeroBaseline()`"指的是【那个函数读成员的当前值**】
```

**⚠ 一个**必须查证的点**（`wireZeroBaseline()` 的实现）。

**✅ 这是我第一次遇到"默认值 == 发送值"这个机制，需要标注为**需要核对 `wireZeroBaseline()` 的实现**。**

### 2.4 而**"三个零售每个 scriptmover 都携带而服务器发零的字段"**

```cpp
// THREE FIELDS EVERY RETAIL ET_SCRIPTMOVER CARRIES AND THIS SERVER SENT
// ZERO FOR. Measured across the dm demo: field 25 (+0xE4, 8 bits) reads
// 255 on 2377 of 2390 assertions and field 27 (+0x58, 11 bits) reads
// 2047 on all 2377 -- 0xFF and 0x7FF, both all-ones, which is what a
// "none" sentinel looks like. A zero in their place is not a smaller
// value, it is index 0 of whatever they select.
```

**⇒ 十二层**：
```text
1. **零售每一个 `ET_SCRIPTMOVER` 都携带的三个字段，而这个服务器【发零**】**
2. ⇒ **字段 `25`（`+0xE4`，`8` 位）在 `2390` 次断言里的 `2377` 次读 `255`**
3. ⇒ **字段 `27`（`+0x58`，`11` 位）在全部 `2377` 次读 `2047`**
4. ⇒ **`0xFF` 与 `0x7FF`，【都是全一**】**
5. ⇒ **⇒ 那正是一个"没有"哨兵的样子**
6. ⇒ **⇒ 而【一个零在它们的位置上不是一个更小的值**】**
7. ⇒ **它是【它们所选择的那个东西的索引 `0`**】**
```

### 2.5 ⭐⭐⭐ **"一个零不是一个更小的值，它是索引 0"**

**✅ 这是本报告里**最重要的一条语义论证**。**

**⇒ 三层**：
```text
误解：`0` 是"最小"⇒ **发 `0` 无害**
真相：`0` 是【一个合法的索引**】⇒ **选中了第一个东西**
⇒ **⇒ 所以【"没有"必须用一个【不可能**的索引**来表达】
```

**✅ 与 §416 的"`SvTeam::None = 0` ⇒ 客户端 `v1[62]` 读 `0` ⇒ 空指针"**完全同族（**第三次"零是一个有效的索引"）。

**⇒ 三层**：
```text
§413  `viewmodelIndex = 0` ⇒ **索引 0 = 空指针**
§416  `team = 0`          ⇒ **索引 0 = 空指针**
§417  `field00E4 = 0`     ⇒ **索引 0 = 第一个东西**
⇒ **⇒ 三次"零不是中性值"**
```

**✅ ⭐⭐⭐ **一个"零不是中性值"的三例表**。

**⚠ 而"`8` 位的满值是 `255`，`11` 位是 `2047`"⇒ **与 §414 的 `field00E4 = 255`、`field0058 = 2047`**完全一致 ✓

**⇒ 三层**：
```text
§414  `<map>_const.ff` 里的 `field00E4 = 255`、`field0058 = 2047`
§417  线上零售也发 `255`/`2047`
⇒ **⇒ 所以【文件与线上一致**】
```

**✅ ⭐⭐ **一个"离线文件与线上字节一致"的确认**。

## 三、**`+0x5C` 一个偏移四种含义**（本组第二重要）

### 3.1 那段

```cpp
// CODOL entityState_s +0x5C is an eType-owned union: ET_PLAYER uses
// movementDir while ET_SCRIPTMOVER uses the model configstring index.
std::int32_t movementDir{};
...
// Field 26, +0x09C, 10 bits -- a DIFFERENT field from `modelIndex`, which this eType writes
// at field 19 / +0x05C as the XModel configstring index.
std::uint16_t scriptMoverBrushModelIndex{};
...
// Field 12, +0x05C, 32 bits. ONE distinct value in the whole census --
// 0x00FFFFFF on all 51 asserts, and 0x00FFFFFF live.
// NOT the xmodel slot. That is +0x05C 10-bit on ET_SCRIPTMOVER; on this
// eType the same offset is 32 bits and pinned.
std::uint32_t actorField005C{};
```

### 3.2 十八层

```text
1. **`entityState_s` 是【一个**结构体，而【每个 eType 的表从同一批字节里读出它自己的含义**】**
2. ⇒ **`+0x5C`**：
      · **`ET_PLAYER`** ⇒ **`movementDir`**（`int32`）
      · **`ET_SCRIPTMOVER`** ⇒ **`modelIndex`**（`10` 位 XModel 索引）
      · **`ET_ACTOR (19)`** ⇒ **`actorField005C`**（`32` 位，恒 `0x00FFFFFF`）
      · **`ET_MISSILE`** ⇒ **`+0x58` 是发射时间**（另一种用法）
3. ⇒ **⇒ 所以【同一个偏移四种宽度与语义**】
4. ⇒ **而 `+0x8C`**：
      · **`ET_SCRIPTMOVER`** ⇒ **`groundEntityNum`**（`11` 位）
      · **`ET_ACTOR`** ⇒ **`actorLoopSound`**（codec `-96`）
5. ⇒ **而 `+0x54`**：
      · **`ET_PLAYER`** ⇒ **`playerSizeScale`**（float）
      · **`ET_ACTOR`** ⇒ **`actorField0054`**（float，恒 `1.0`）
      · **`ET_SCRIPTMOVER`** ⇒ **`modelScale`**（float）
```

### 3.3 ⭐⭐⭐ **"entityState_s 是一个结构体，而每个 eType 的表从同一批字节里读出它自己的含义"**

**✅ 这是本报告里**最重要的一条内存复用**。**

**⇒ 三层**：
```text
误解：`+0x5C` 有一个含义
真相：**`(eType, +0x5C)` 才有含义**
⇒ **⇒ 所以【成员必须按 eType 分开，不能复用**】
```

**✅ 与 §415 的"`19` 与 `21` 的索引→偏移映射相同"**——**但那里是【两个 eType 共用一个表**】。**

**⇒ 三层**：
```text
§415  `19` 与 `21` ⇒ **索引→偏移【相同**】⇒ **共用表**
§417  `player`/`scriptmover`/`actor` ⇒ **同一偏移【不同宽度与语义**】⇒ **必须分开**
⇒ **⇒ 所以【"是否可共用"由表决定，不由偏移决定**】
```

**✅ ⭐⭐⭐ **一个"偏移相同不等于语义相同"的精确判据**。

**⚠ 而"`0x00FFFFFF` 在全部 `51` 次断言上"⇒ **与 §414 的 `solid = 0xFFFFFF`**完全一致 ✓

**⇒ 三层**：
```text
§414  `<map>_const.ff` 的 `solid = 0xFFFFFF`（`238` 个 brush）
§417  `ET_ACTOR` 的 `+0x05C` = `0x00FFFFFF`（`51` 次）
⇒ **⇒ 同一个值在两个 eType 上的不同含义**
```

**✅ ⭐ **一个"同一个 `0xFFFFFF` 在 `scriptmover` 是 `solid` 而在 `actor` 是 `+0x5C`"** 的精确区分。

### 3.4 而**"`groundEntityNum` 与 `bullet impact` 共用一个成员"**

```cpp
// ONE MEMBER, TWO ET_EVENTS FIELDS, CHOSEN BY eType.
//
//   obituary      -> field 13, entityState_s +0x88, 11 bits.  This is
//                    the offset the netfield table itself calls
//                    `groundEntityNum`, and CG_Obituary (out.exe
//                    0x00531080) reads the KILLER out of it:
//                    `*(es + 136)`, clamped to 18, 2046 for nobody.
//   bullet impact -> field 23, entityState_s +0x8C, codec -96, the HIT
//                    entity. Historic use, and the misnomer.
//
// IT DOES NOT GET ITS OWN MEMBER, and that is not a style choice:
// SvEntityState is embedded in the address-keyed WorldClientState, whose
// size is pinned by a static_assert further down because growing it once
// broke the death animation (section 184h). Adding a field here fails
// that assert, and the assert is right.
std::uint32_t groundEntityNum{};
```

**⇒ 十八层**：
```text
1. **一个成员，两个 `ET_EVENTS` 字段，由 `eType` 选择**
2. ⇒ **obituary ⇒ 字段 `13`，`+0x88`，`11` 位**
3. ⇒ **那是【netfield 表自己叫做 `groundEntityNum` 的偏移**】**
4. ⇒ **而 `CG_Obituary`（`0x00531080`）从它读【凶手**】**
5. ⇒ **（`*(es + 136)`，夹到 `18`，`2046` 表示没有人）**
6. ⇒ **bullet impact ⇒ 字段 `23`，`+0x8C`，codec `-96`，【命中实体**】**
7. ⇒ **（历史用法，以及那个误名）**
8. ⇒ **⚠ 它【不拿到自己的成员，而那不是风格选择**】**
9. ⇒ **`SvEntityState` 被嵌在【地址键控的 `WorldClientState`**】里**
10. ⇒ **它的大小【被一个 `static_assert` 钉住**】**
11. ⇒ **因为【增长它一次就毁了死亡动画**】（第 184h 节）
12. ⇒ **在这里加一个字段【让那个断言失败**】**
13. ⇒ **而那个断言【是对的**】**
```

### 3.5 ⭐⭐⭐ **"因为增长它一次就毁了死亡动画，而那个断言是对的"**

**✅ 这是本报告里**最重要的一条结构约束**。**

**⇒ 三层**：
```text
`SvEntityState` 嵌在 `WorldClientState` 里
而 `WorldClientState` 是【地址键控**】的（**`static_assert` 钉大小**）
⇒ **⇒ 所以【加一个字段会破坏一个外部的内存契约**】
```

**✅ 与 §409 的"`SvNativeUserCmd` 是 `0x2C`"**同族（**第三次"结构大小是一个外部契约"）。

**⇒ 三层**：
```text
§413  `SvNativeUserCmd` `0x2C` ⇒ **没有 `meleeChargeDist` 字段** ⇒ **不猜绑定**
§416  `SvPlayerState` 的注释反复说"preserve the address-sensitive allocation size"
§417  `SvEntityState` **被 `static_assert` 钉大小** ⇒ **加字段会失败**
⇒ **⇒ 三次"大小是一个不能违反的契约**】
```

**✅ ⭐⭐ **一个"内存布局是外部契约"的三例表**。

**⚠ 而"那个断言是对的"⇒ **一个"承认约束合理"的表述**。**

**✅ ⭐ **一个"不是绕过约束而是接受它"的纪律**。

### 3.6 而**"`CG_Obituary` 从 `+0x88` 读杀手，`*(es + 136)`"**

**⇒ 五层**：
```text
`es + 136 = es + 0x88` ✓
夹到 `18` ⇒ **`MaximumGameClients = 18`？**
`2046` 表示"没有人" ⇒ **`EntityNumWorld`**
```
**✅ 与 §388 的"`EntityNumWorld = 2046`"**完全闭合 ✓

**⇒ 三层**：
```text
`2046` ⇒ `EntityNumWorld`
`2047` ⇒ `EntityNumNone`
⇒ **⇒ 两个哨兵：`2046` = "世界"，`2047` = "没有"**
```

**✅ ⭐ **一个"两个哨兵语义"的精确区分**。

**⚠ 而"`18`"⇒ 与 `MaximumGameClients`（§416 的 `SvAgentSlotCount = 32`）**不同**。**

**⇒ 三层**：
```text
`MaximumGameClients` ⇒ **`18`**（推断）
`SvAgentSlotCount`   ⇒ **`32`**
⇒ **⇒ 玩家槽与服务槽【不同数**】
```

**✅ 一个**需要核对的常量**。

## 四、**"命名要靠偏移而不是发明"**（本组第三重要）

### 4.1 那段

```cpp
// Named by OFFSET because nothing has established what they mean, and
// section 120 is the record of what inventing a name for a field costs.
// ET_MISSILE uses the same +58 union word as its launch time. The
// generic name allows both owners without growing this pinned record.
std::uint32_t lerpData0058{ 2047 };
std::uint32_t scriptMoverField00E4{ 255 };
```

**⇒ 而 `scriptMoverField0070`：**

```cpp
// Field 21 (+0x70, codec -7). Retail's podium figures carry 1 and this
// demo shows no other value anywhere. Named by OFFSET: the netfield
// table has no name for it either, and 120 is the record of what
// inventing one costs.
std::int32_t scriptMoverField0070{};
```

### 4.2 十六层

```text
1. **按偏移命名，因为【没有东西确立它们的意思**】**
2. ⇒ **而第 `120` 节是【这个项目为"发明一个字段名"付出代价的记录**】**
3. ⇒ **而 `ET_MISSILE` 把【同一个 `+0x58` 联合字**】用作它的发射时间**
4. ⇒ **⇒ 所以【那个通用名字允许两种所有者】** **而不增长这个被钉住的记录**
5. ⇒ **而 `+0x70`（codec `-7`）：零售的 podium 人偶携带 `1`**
6. ⇒ **而这个 demo 【在任何地方都不显示别的值**】**
7. ⇒ **按偏移命名**：**netfield 表【也没有给它一个名字**】**
8. ⇒ **而 `120` 是【发明一个名字的代价的记录**】**
```

### 4.3 ⭐⭐⭐ **"第 120 节是发明一个字段名的代价的记录"**

**✅ 这是本报告里**最重要的一条命名纪律**。**

**⇒ 三层**：
```text
做法：**按偏移命名**（`scriptMoverField00E4`）
理由：**没有确立含义** ⇒ **一个"看起来对的名字"会误导后续的推理**
代价：**第 120 节的记录**
⇒ **⇒ 所以【一个错的名字比没有名字更贵**】
```

**✅ 与 §416 的"`0x00BD81C3` 在 `out.exe` 里存在但做别的事"**同族（**第五次"看起来对的错误最贵**）。

**⇒ 三层**：
```text
§397  **零信息**
§416  **存在但错位**
§417  **一个错的名字**
⇒ **⇒ 三次"看起来对"的危险**
```

**✅ ⭐⭐ **一个"三种看起来对"的表**。

**⚠ 而"`ET_MISSILE` 把同一个 `+0x58` 用作发射时间"⇒ **所以一个名字（`lerpData0058`）能服务两个所有者**。**

**✅ 与 §417 三 的"`+0x5C` 四义"**同族（**第二次"一个偏移多义"**。**

**⇒ 三层**：
```text
`+0x5C` ⇒ **三个不同的成员**（`movementDir`/`modelIndex`/`actorField005C`）
`+0x58` ⇒ **一个成员服务两个所有者**（`lerpData0058` = scriptmover lerp / missile launch time）
⇒ **⇒ 两个相反的处置**
```

**⚠ 一个**不一致的处置**（为什么 `+0x5C` 分三而 `+0x58` 合一？）。

**⇒ 三层**：
```text
`+0x5C` ⇒ **宽度不同**（`10` 位 vs `32` 位）⇒ **不能共用一个成员**
`+0x58` ⇒ **宽度相同**（`32` 位 vs `32` 位）⇒ **可以共用一个成员**
⇒ **⇒ 所以【处置由宽度决定**】
```

**✅ ⭐⭐ **一个"成员复用判据：宽度相同才能复用"** 的精确规则。

### 4.4 而**"`actorField009C` 的 `clientNum` 是错的 MW3 名字"**

```cpp
// THE APPEARANCE INDEX. Field 29, +0x09C, 10 bits, and the netfield
// table's name for it -- `clientNum` -- is an unmeasured MW3 transfer
// that is wrong here, exactly as it was wrong for the `*N` brush model
// index at this same offset on ET_SCRIPTMOVER
//
// MEASURED: written ONCE on the spawn frame and never again across 367 asserting frames;
// 13 distinct values 1..409 over the capture. Write-once, per-life
// constant, 10 bits against a 1024-entry model band. 409 is not a client
// number -- no zm match has 410 players.
```

**⇒ 十八层**：
```text
1. **`+0x09C` 是【外观索引**】**
2. ⇒ **而 netfield 表叫它 `clientNum`**
3. ⇒ **那是一个【未测量的 MW3 名字转移，在这里是错的**】**
4. ⇒ **正像它在 `ET_SCRIPTMOVER` 的同一个偏移上是错的**（那里是 `*N` brush 索引）
5. ⇒ **测量**：**在出生帧写【一次**】，`367` 个断言帧里【再也没写过**】
6. ⇒ **捕获里 `13` 个不同的值，`1..409`**
7. ⇒ **写一次、每命恒定、`10` 位对 `1024` 项的模型带**
8. ⇒ **⇒ `409` 【不是一个客户端号**】——**没有一场 zm 有 `410` 个玩家**
```

### 4.5 ⭐⭐⭐ **"`409` 不是一个客户端号 —— 没有一场 zm 有 `410` 个玩家"**

**✅ 这是本报告里**最漂亮的一个用"不可能值"否证假设**。**

**✅ 与 §413 的"`+0x090` 读出 `[?,0,1,…,10]` ⇒ 不是 faction"**完全同族（**第二次"用值的范围否证语义"）。

**⇒ 三层**：
```text
假设：`+0x09C` = `clientNum`
实测范围：`1..409`
而 zm 最多 `18` 人（或 `32` 槽）
⇒ **⇒ 所以【`409` 不可能是一个客户端号**】
```

**✅ ⭐⭐ **一个"用上界排除假设"的实例**。

**⚠ 而"`10` 位对 `1024` 项的模型带"⇒ **`409 < 1024`** ⇒ **合理**。**

**✅ ⭐ **一个"范围匹配"的正向证据**。

**⇒ 三层**：
```text
`1..409` ⊆ `0..1023` ⇒ **匹配模型带**
`1..409` ⊄ `0..17`   ⇒ **不匹配客户端号**
⇒ **⇒ 所以【两个方向都指向模型**】
```

**✅ ⭐⭐⭐ **一个"双向范围匹配"的完美论证**。

**⚠ 而"`409` 是 13 个值里的最大"⇒ **`13` 个值覆盖 `1..409`** ⇒ **稀疏**。**

**✅ 与 §414 的"`<map>_const.ff` 的号是稀疏的"**同族（**第二次"稀疏性携带信息**）。

### 4.6 而**"从不发送 demo 的字面 `287`"**

```cpp
// THIS IS THIS SERVER'S BAND INDEX, resolved from a model NAME by
// zmspawnactor's ModelResolver. Never the demo's literal 287: the client
// rebuilds its own configstring band at map load, and sending a capture's
// index is the bug that cost this project three sessions on the doors.
```

**⇒ 七层**：
```text
1. **这是【这个服务器的带索引】，从一个模型【名字】解析**
2. ⇒ **从不 demo 的字面 `287`**
3. ⇒ **因为客户端【在地图加载时重建它自己的 configstring 带**】**
4. ⇒ **⇒ 而【发送一个捕获的索引**】正是【让这个项目在门上花了三次会话**】的那个 bug
```

**✅ 与 §414 的"xmodel 的 `+3` 偏移"**完全闭合 ✓

**⇒ 三层**：
```text
§414  客户端重解析 ⇒ **`base != file`** ⇒ **发 `ours ^ file` ⇒ 客户端得 `file`（错 3 格）**
§417  **发捕获的 `287`** ⇒ **同一类错误**
⇒ **⇒ 所以【索引必须从名字解析，不能从捕获抄**】
```

**✅ ⭐⭐⭐ **"三次会话"的代价** —— 第十次"同一 bug 重复"。

## 五、**`SvAgentState` 的 `24` 个字段与三个常量**

### 5.1 结构

```cpp
struct SvAgentState
{
    static constexpr std::size_t FieldCount = 24;
    static constexpr std::size_t ModelField = 8;
    static constexpr std::size_t AnimationField = 9;
    static constexpr std::size_t AnimationStartTimeField = 10;
    static constexpr std::size_t AttachmentField = 13;
    static constexpr std::size_t EntityNumField = 20;
    static constexpr std::size_t TeamField = 21;

    std::uint32_t agentNum{};
    std::array<std::uint32_t, FieldCount> fields{
        0, 0, 0, 0, 0, 0, 0, 0,
        1266, 0, 0, 1, 3, 1267, 1317, 3,
        0, 0, 0, 0, 345, 2, 0xFFFFFFFFu, 0,
    };
};
```

**⇒ 十层**：
```text
1. **`24` 个字段**，六个命名索引：`8`（模型）、`9`（动画）、`10`（动画起点）、`13`（附件）、`20`（实体号）、`21`（队伍）
2. ⇒ **默认值**：
      · **idx8  = 1266** ⇒ 模型
      · **idx11 = 1**
      · **idx12 = 3**
      · **idx13 = 1267** ⇒ 附件模型 0
      · **idx14 = 1317** ⇒ 附件模型 1
      · **idx15 = 3** ⇒ 附件 tag 1
      · **idx20 = 345** ⇒ 实体号
      · **idx21 = 2** ⇒ 队伍
      · **idx22 = 0xFFFFFFFF**
3. ⇒ **⇒ 与 §415 的 `unk_DA9920` 九个值**完全吻合 ✓
```

**✅ ⭐⭐ **一个"`24` 位数组与九个命名值"的精确对照**。

**⇒ 而 §415 的九个值与这里的索引映射**：

| `unk_DA9920` 偏移 | 值 | `SvAgentState` 索引 | §415 的说法 |
|---|---|---|---|
| `+0x004` | `345` | **20** | 实体号 |
| `+0x008` | `2` | **21** | 队伍 |
| `+0x00C` | `1266` | **8** | 模型 |
| `+0x010` | `0xFFFFFFFF` | **22** | — |
| `+0x014` | `1267` | **13** | 附件模型 0 |
| `+0x018` | `1317` | **14** | 附件模型 1 |
| `+0x024` | `0` | **23** | 附件 tag 0 |
| `+0x028` | `3` | **15** | 附件 tag 1 |
| `+0x034` | `3` | **12**（？） | — |
| `+0x040` | `1` | **11**（？） | — |

**⚠ 而 `+0x034 = 3` 对应哪个索引？`SvAgentState` 的 idx12 = 3。**

**⇒ 所以 `+0x034`（原生偏移）⇒ **索引 `12`**。**

**⇒ 而 `+0x040 = 1` ⇒ **索引 `11`**。**

**✅ ⭐ **一个"原生偏移与 netfield 索引的完整映射表**（从两个来源拼出）。

### 5.2 而**"重述：`fields` 的默认值就是那九个"**

```cpp
// Values are indexed by the shipping descriptor table at out.exe
// 0x00DA63E8. These defaults are the exact 88-byte native template at
// 0x00DA9920, projected through that table. In particular, entity 345,
// team 2, model 1266 and the all-ones attachment sentinel are real
// baseline values; replacing them with zero changes the wire delta.
```

**⇒ 七层**：
```text
1. **值按 `0x00DA63E8` 的描述符表索引**
2. ⇒ **这些默认值是【`0x00DA9920` 的 `88` 字节原生模板**】**
3. ⇒ **通过那张表投影**
4. ⇒ **特别是**：**实体 `345`、队伍 `2`、模型 `1266` 与那个全一的附件哨兵是【真实的基准值**】**
5. ⇒ **【把它们替换成零会改变线缆增量**】**
```

### 5.3 ⭐⭐⭐ **"替换成零会改变线缆增量"**

**✅ 这是本报告里**最直接的"默认值必须对"的论证**。**

**⇒ 三层**：
```text
`wireUnsignedDelta(value) = value ^ (base & mask)`
⇒ **`base` 是【客户端的默认行**】，不是零**
⇒ **⇒ 所以【我们发 `value` 而客户端算 `value ^ base`**】
```

**✅ 与 §415 的"`310 ^ 242 = 452`"**完全同一条链 ✓

**⇒ 三层**：
```text
§415  我们发 `310`（值），客户端算 `310 ^ (1266 & 0x3FF)` = `452`
§417  **所以 `SvAgentState::fields` 的默认值【就是那个 `base`**】
⇒ **⇒ 而若我们把默认值改成零 ⇒ 我们的 `base` 与客户端的不同 ⇒ 全错**
```

**✅ ⭐⭐⭐ **一个"服务器侧也必须持有客户端的 base"的完整图景**。**

**⇒ 三层**：
```text
正确：`fields[8] = 1266`（与客户端同）
⇒ `writeUnsignedDelta(ours) = ours ^ (1266 & 0x3FF)`
⇒ 客户端：`(ours ^ 242) ^ 242 = ours` ✓
错误：`fields[8] = 0`
⇒ `writeUnsignedDelta(ours) = ours ^ 0 = ours`
⇒ 客户端：`ours ^ 242` ✗
```

**✅ ⭐⭐ **一个"对称性"的完整代数证明**。

**✅ 这是本报告的核心技术结论**。

## 六、**`attachmentIgnoreCollision{3}`**

```cpp
// CODREF(actor_head_attachment): native agent field12 (+0x34,32bits)
// -> record+564 -> DObjModel+6 at 0x53004B. This is an attachment
// collision mask, not a count. Preserve native template3 by default.
std::uint32_t attachmentIgnoreCollision{3};
```

**⇒ 五层**：
```text
1. **原生 agent 字段 `12`（`+0x34`，`32` 位）**
2. ⇒ **→ `record+564` → `DObjModel+6` 在 `0x53004B`**
3. ⇒ **这是【一个附件碰撞掩码，不是一个计数**】**
4. ⇒ **默认保留原生模板的 `3`**
5. ⇒ **⇒ 而 `+0x34 = 3` 正对应 §415 第九个值 ✓**
```

**✅ ⭐ **一个"`0x034 = 3` 的语义"** —— **碰撞掩码**。

**⚠ 而 §417 五.1 的映射表里 `+0x034` 对应索引 `12`** ⇒ **而 `attachmentIgnoreCollision` 就是这个字段。**

**✅ ⭐ **一个"从两个来源拼出完整语义"的确认。**

## 七、`SvClientInfoState` 的四个新字段

```cpp
std::array<ExplicitAttachment, 4> explicitAttachments{};
std::array<std::uint32_t, SvCharacterRecordEntryCount> characterOptionMask{};
std::uint32_t zombieBattery{};
std::uint32_t zombieScoreboardTeam{};
```

**⇒ 而注释**：

```cpp
// Legacy local bookkeeping only. Correction (2026-09-06): native
// clientInfo+0xA4 is not network clientState+0xA4. Wire field 5 is
// ability mask word 3, copied into ps+0x59C at 0x54C25A.
std::uint32_t zombieBattery{};
```

**⇒ 八层**：
```text
1. **仅遗留本地记账**
2. ⇒ **更正（2026-09-06）：原生 `clientInfo+0xA4` 【不是】网络 `clientState+0xA4`**
3. ⇒ **线缆字段 `5` 是【能力掩码的第三个字**】**
4. ⇒ **在 `0x54C25A` 被拷进 `ps+0x59C`**
5. ⇒ **⇒ 所以【两个同名偏移在两个不同的结构上**】**
```

### 7.1 ⭐⭐ **"原生 clientInfo+0xA4 不是网络 clientState+0xA4"**

**✅ 与 §413 的"`number` 是网络实体号而 `\ent\<n>` 是实体索引"**同族（**第四次"同名不同物"）。

**⇒ 三层**：
```text
`clientInfo + 0xA4` ⇒ **原生结构的内存偏移**
`clientState + 0xA4` ⇒ **网络结构的内存偏移**
⇒ **⇒ 两个完全不同的东西，名字里有同一个"client"**】
```

**✅ ⭐⭐ **"同一个偏移在两个结构上"** —— 一个**极易混淆的陷阱**。

### 7.2 而**"`zombieScoreboardTeam` 只有 ZM 供给"**

```cpp
// CODREF(g_update_client_info): out.exe descriptor36 at0xDA8228 is
// clientState+4,11bits;54BC8E copies it to characterInfo+7C. Only ZM
// supplies this newly recovered field; zero preserves legacy MP wire.
std::uint32_t zombieScoreboardTeam{};
```

**⇒ 六层**：
```text
1. **`descriptor 36` 在 `0xDA8228`** ⇒ **`clientState+4`，`11` 位**
2. ⇒ **`0x54BC8E` 把它拷进 `characterInfo+0x7C`**
3. ⇒ **只有 ZM 供给这个新解出的字段**
4. ⇒ **零【保留遗留 MP 的线缆**】**
5. ⇒ **⇒ 所以【一个字段只在一种模式下被填充**】
```

**✅ 与 §411 的"`OLMOD_*` 的开关"**不同（这是**按模式的门**）。

**⇒ 三层**：
```text
按模式：**`zombieScoreboardTeam` 只 ZM 填**
按版本：**`SvAgentState` 的默认值**
按旗标：**`SvActorSendAnimAlias`**
⇒ **⇒ 三种"部分启用"的机制**
```

**✅ ⭐ **一个"部分启用"的三层**。

## 八、`SvKillcamReplayPose`

```cpp
// 29200: the pose the server publishes to a client whose killcam replay is
// running. Filled from the project pose ring at (now - deltaTime), which is
// the value 2697s cachedSnapshot rewind would have evaluated
// (sv_snapshot.c:1843-1870). Recipient-only: live playerStates are untouched.
struct SvKillcamReplayPose
{
    std::uint32_t clientNum{};
    std::uint32_t timestamp{};
    std::array<float, 3> origin{};
    std::array<float, 2> view{};
};
```

**⇒ 七层**：
```text
1. **`29200`：服务器发布给【一个回放正在跑**】的客户端的位姿
2. ⇒ **从项目的位姿环在 `(now - deltaTime)` 处填**
3. ⇒ **那是 `2697` 的 `cachedSnapshot` 倒带本会求出的值**（`sv_snapshot.c:1843-1870`）
4. ⇒ **【只对接收者**】**：**活的 `playerState` 【不被触碰**】**
5. ⇒ **四个字段**：`clientNum` / `timestamp` / `origin[3]` / `view[2]`
```

**✅ ⭐⭐ **"只对接收者"** —— 与 §413 的"`SvKillcamReplayPose` 的位姿"**—**其实是同一个特性。**

**⚠ 注意："`2697` 的 `cachedSnapshot`"⇒ **`2697` 是一个外部参照**（`sv_snapshot.c`）。**

**⇒ 三层**：
```text
`2697` ⇒ **另一个实现**（**CoD4x/IW4 系**）
本 build ⇒ **用项目自己的位姿环**
⇒ **⇒ 所以【行为对齐而实现不同**】
```

**✅ 与 §413 的"`SvKillcamArchiveRecord`（24 人 × 160 帧 × 32 B）"**完全闭合 ✓

**⇒ 三层**：
```text
§413  **档案（录制）**：`SV_KillcamArchiveRecord`
§417  **回放（读取）**：`SvKillcamReplayPose` 从位姿环 `(now - deltaTime)`
⇒ **⇒ 一写一读**
```

**✅ ⭐⭐ **一个"录制与回放"的两端**。

## 九、关键结论

1. **⭐⭐⭐ "一个非零默认值落进 `wireZeroBaseline()`，比较相等，于是永不发送"** —— 而**"把 `0` 用作默认"与"把正确的值用作默认"在同一个机制上是相反的效果**（§416 是刻意的节省，§417 是无意的遗漏）。
2. **⭐ 一处需要核对的措辞**：`lerpData0058{2047}`/`scriptMoverField00E4{255}` 在 ET_SCRIPTMOVER 节，而"NONE OF THESE CARRIES A NON-ZERO DEFAULT"在 ET_ACTOR 节 ⇒ **两条规则适用于两个族**；但 `wireZeroBaseline()` 的实现需要核对（若它读成员的当前值，则 `{2047}` 仍会相等）。
3. **⭐⭐⭐ "三个字段零售每个 scriptmover 都携带而服务器发零：`+0xE4`（`8` 位，`2377/2390` 次读 `255`）与 `+0x58`（`11` 位，`2377/2377` 次读 `2047`）；`0xFF` 与 `0x7FF` 都是全一 ⇒ 一个零在它们的位置上不是一个更小的值，而是它选择的东西的【索引 0】"`** —— 第三次"零不是中性值"。
4. **⭐⭐ `+0x5C` 一个偏移四种含义**：`ET_PLAYER` = `movementDir`（`int32`）、`ET_SCRIPTMOVER` = `modelIndex`（`10` 位）、`ET_ACTOR` = `actorField005C`（`32` 位恒 `0x00FFFFFF`）、`ET_MISSILE` 的 `+0x58` 是发射时间。
5. **⭐⭐⭐ "entityState_s 是一个结构体，而每个 eType 的表从同一批字节里读出它自己的含义"** ⇒ **成员必须按 eType 分开**；而**§415 的 `19`/`21` 共用表**则是"索引→偏移相同 ⇒ 可共用" ⇒ **"是否可共用"由表决定，不由偏移决定**。
6. **⭐⭐ 成员复用判据**：`+0x5C` 分三个（**宽度不同**），`+0x58` 合一（**宽度相同**）⇒ **"宽度相同才能复用"**。
7. **⭐⭐⭐ `groundEntityNum` 一成员两义**：obituary 用字段 `13`/`+0x88`/`11` 位（`CG_Obituary` 从 `*(es+136)` 读**杀手**，夹到 `18`，`2046` 表示没有人）；bullet impact 用字段 `23`/`+0x8C`/codec `-96`（**命中实体**）。
8. **⭐⭐⭐ "它不拿到自己的成员，而那不是风格选择：`SvEntityState` 嵌在地址键控的 `WorldClientState` 里，大小被 `static_assert` 钉住，因为增长它一次就毁了死亡动画（第 184h 节）；加一个字段会让那个断言失败，而那个断言是对的"`** —— 第三次"结构大小是外部契约"。
9. **⭐ `2046` = `EntityNumWorld`（"世界"）与 `2047` = `EntityNumNone`（"没有"）是两个不同的哨兵**。
10. **⭐⭐⭐ "按偏移命名，因为第 120 节是发明一个字段名的代价的记录"`** —— 第五次"看起来对的错误最贵"；而 `ET_MISSILE` 把同一个 `+0x58` 用作发射时间 ⇒ **一个通用名字服务两个所有者**。
11. **⭐⭐⭐ `+0x09C` 的 `clientNum` 是错的 MW3 名字**：**"在出生帧写一次，`367` 个断言帧里再也没写过；`13` 个不同的值 `1..409`；`10` 位对 `1024` 项的模型带；`409` 不是一个客户端号 —— 没有一场 zm 有 `410` 个玩家"`** ⇒ **双向范围匹配**（`1..409 ⊆ 0..1023` 而 `⊄ 0..17`）。
12. **⭐⭐⭐ "从不 demo 的字面 `287`：客户端在地图加载时重建它自己的 configstring 带，而发送一个捕获的索引正是让这个项目在门上花了三次会话的那个 bug"`** —— 第十次"同一 bug 重复"。
13. **⭐⭐⭐ `SvAgentState` 的 `24` 字段与九个默认值**（`idx8=1266`、`idx11=1`、`idx12=3`、`idx13=1267`、`idx14=1317`、`idx15=3`、`idx20=345`、`idx21=2`、`idx22=0xFFFFFFFF`）**与 §415 的 `unk_DA9920` 九个值完全吻合** ⇒ **一个"原生偏移 ↔ netfield 索引"的完整映射表**（`+0x004`→20、`+0x008`→21、`+0x00C`→8、`+0x010`→22、`+0x014`→13、`+0x018`→14、`+0x024`→23、`+0x028`→15、`+0x034`→12、`+0x040`→11）。
14. **⭐⭐⭐ "把它们替换成零会改变线缆增量"** ⇒ **代数证明**：正确时 `writeUnsignedDelta(ours) = ours ^ (1266 & 0x3FF)` 而客户端 `(ours ^ 242) ^ 242 = ours`；错误时 `ours ^ 0 = ours` 而客户端 `ours ^ 242` ✗ —— **服务器侧也必须持有客户端的 base**。
15. **⭐ `attachmentIgnoreCollision{3}` = 原生 agent 字段 `12`（`+0x34`）⇒ `record+564` → `DObjModel+6`，是【附件碰撞掩码】不是计数** —— 与 §415 的 `+0x034 = 3` 及 §417 的 idx12 三方闭合。
16. **⭐⭐ "原生 `clientInfo+0xA4` 不是网络 `clientState+0xA4`；线缆字段 `5` 是能力掩码第三个字，在 `0x54C25A` 被拷进 `ps+0x59C`"`** —— 第四次"同名不同物"。
17. **`zombieScoreboardTeam` 只由 ZM 供给**（`descriptor 36` at `0xDA8228` = `clientState+4` 的 `11` 位 ⇒ `characterInfo+0x7C`），**零保留遗留 MP 线缆**。
18. **`SvKillcamReplayPose`（四个字段）与 §413 的 `SV_KillcamArchiveRecord` 是一写一读**：写入 `24×160×32` 的档案，回放时从位姿环 `(now - deltaTime)` 取值，**只对接收者**。

## 十、未闭合点

- `wireZeroBaseline()` 的实现（它读成员的当前值还是硬编码零？）。
- `MaximumGameClients` 是否为 `18`。
- `+0x034`（idx12）与 `+0x040`（idx11）的语义（一个是碰撞掩码，另一个未名）。
- `unmeasured` 的 `actorField0058`（`0xFF0003xx` 的打包动画状态字）。
- `SvActorSendUnmeasuredSpawnWords` 的实现。
- `sv_snapshot_mp.hpp` 1990 行之后未读取（**共 `4703` 行**）。
