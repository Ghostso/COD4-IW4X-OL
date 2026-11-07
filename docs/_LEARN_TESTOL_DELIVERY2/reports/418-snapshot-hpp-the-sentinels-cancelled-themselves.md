# 418 · **`wireZeroBaseline()` 的完整解答** —— "两个哨兵互相抵消了自己"、`0x0AC` 在 `scriptmover` 是 `solid`、以及 `flags` 与 `delta base` 是**一个决定**

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 1990–2330 行，重点是 **2058 行的 `wireZeroBaseline()`**（报告 417 遗留的未闭合点在这里被解出）。

## 二、**"默认值互相抵消了自己"**（本组最重要的一段）

### 2.1 那段

```cpp
// THE CLIENT'S BASELINE FOR AN ENTITY IT HAS NEVER SEEN IS A ZEROED STRUCT,
// SO THE ONE A WRITER COMPARES AGAINST HAS TO BE ZERO TOO.
//
// `SvEntityState{}` is NOT zero. Two members carry a non-zero default member
// initialiser -- lerpData0058 = 2047 and scriptMoverField00E4 = 255,
// the two all-ones "none" sentinels every retail ET_SCRIPTMOVER asserts --
// and every writer opens with `const SvEntityState zeroBaseline{}`. A field
// is written only when it DIFFERS from that baseline, so those two compared
// equal, were skipped, and the client decoded 0 for both: entity 0 and
// index 0 of whatever they select, not "none".
//
// The defaults were added so that every scriptmover would carry the
// sentinels, and they cancelled themselves out. Measured after the fact in
// this server's own recorded demo (HANDOFF 140): retail's podium figures
// carry `clientLinkInfo 255` and `entToTakeMarksFrom 2047` on their first
// frame and ours carried neither, three sections after the change that was
// supposed to send them.
//
// Anything with a non-zero default belongs in this function, and the audit
// that keeps it honest is Tools/olfinal/audit-wire-zero-baseline.py.
[[nodiscard]] inline SvEntityState wireZeroBaseline() noexcept
{
    SvEntityState baseline{};
    baseline.lerpData0058 = 0;
    baseline.scriptMoverField00E4 = 0;
    return baseline;
}
```

### 2.2 二十四层

```text
1. **客户端对一个它【从未见过**】的实体的基准是一个【零化结构体**】**
2. ⇒ **⇒ 所以写者【比对的那个**】也必须【是零**】**
3. ⇒ **而 `SvEntityState{}` **不是零**】
4. ⇒ **两个成员携带一个非零的默认成员初始化器**：
      · **`lerpData0058 = 2047`**
      · **`scriptMoverField00E4 = 255`**
5. ⇒ **而它们是【每一个零售 `ET_SCRIPTMOVER` 都断言的**】那两个全一"没有"哨兵
6. ⇒ **而【每一个写者都以 `const SvEntityState zeroBaseline{}` 开头**】**
7. ⇒ **一个字段【只有当它与那个基准【不同】时**】才被写**
8. ⇒ **⇒ 所以那两个【比较相等 ⇒ 被跳过**】**
9. ⇒ **⇒ 而客户端【对它们解码出 `0`**】**
10. ⇒ **⇒ 实体 `0` 与【它们所选择的那个东西的索引 `0`**】，不是"没有"**
11. ⇒ **那些默认值【是为了让每一个 scriptmover 携带哨兵**】而加的**
12. ⇒ **⇒ 而它们【互相抵消了自己**】**
13. ⇒ **事后在这个服务器【自己的录制 demo**】里测量（`HANDOFF 140`）**：
      · **零售的 podium 人偶在它们的【第一帧**】携带 `clientLinkInfo 255` 与 `entToTakeMarksFrom 2047`
      · **而我们的【两个都没携带**】**
14. ⇒ **在【那个本该发送它们的改动之后【三个小节**】】**
15. ⇒ **⇒ 所以【任何带非零默认值的东西必须进这个函数**】**
16. ⇒ **而保持它诚实的审计是 `Tools/olfinal/audit-wire-zero-baseline.py`**
```

### 2.3 ⭐⭐⭐ **"那些默认值是为了让它携带哨兵而加的，而它们互相抵消了自己"**

**✅ 这是本报告里**最重要的一条反直觉失败**。**

**⇒ 三层**：
```text
意图：**让每个 scriptmover 携带哨兵** `2047`/`255`
实现：**把默认值设成哨兵**
机制：**写者只在"与基准不同"时写**
⇒ **⇒ 所以【默认值 = 期望值 ⇒ 永不写 ⇒ 客户端读 `0`**】
```

**✅ 与 §417 的"一个非零默认值落进 `wireZeroBaseline()` ⇒ 相等 ⇒ 永不发送"**完全同源 ✓

**⇒ 而 §417 我标注的未闭合点（`wireZeroBaseline()` 是否读成员当前值）在这里**解出**：**

**⇒ 三层**：
```text
`SvEntityState baseline{}` ⇒ **值初始化 ⇒ 用默认成员初始化器 ⇒ `lerpData0058 = 2047`**
⇒ **然后再显式清零** `baseline.lerpData0058 = 0`
⇒ **⇒ 所以【这个函数就是那个修正**】
```

**✅ ⭐⭐⭐ **一个完整的因果闭合**。

**⇒ 三层**：
```text
失败：`zeroBaseline{}` **不是零**（两个成员 `2047`/`255`）
修正：`wireZeroBaseline()` **先 `SvEntityState{}` 再把两个改成 `0`**
⇒ **⇒ 所以【`SvEntityState{}` 与 `wireZeroBaseline()` 是两个不同的基准**】
```

**✅ 这就是关键**：**写者应该用 `wireZeroBaseline()` 而不是 `SvEntityState{}`**。

**⚠ 而 `SvEntityState` 的成员【保留】`2047`/`255` 默认值** ⇒ **所以"投影时有值"而"比对时为零"**。

**⇒ 三层**：
```text
成员默认：`lerpData0058 = 2047` ⇒ **一个新建的实体天然携带哨兵**
写基准：`wireZeroBaseline()` ⇒ **`0`** ⇒ **所以 `2047 != 0` ⇒ 会写**
⇒ **⇒ **两者兼顾** ✓
```

**✅ ⭐⭐⭐ **"默认值保留、基准清零"是一个精妙的双赢** —— **既让新建实体有哨兵，又让写者会发它**。

### 2.4 而**"两个哨兵的真实名字"**

```php
// retail's podium figures carry `clientLinkInfo 255` and `entToTakeMarksFrom 2047`
```

**⇒ 四层**：
```text
`scriptMoverField00E4 = 255` ⇒ **零售名字 `clientLinkInfo`**
`lerpData0058 = 2047`        ⇒ **零售名字 `entToTakeMarksFrom`**
⇒ **⇒ 所以两个"按偏移命名"的字段【有零售名字了**】
```

**⚠ 但 §417 的注释说"Named by OFFSET because nothing has established what they mean"** —— **而现在有了名字**。

**⇒ 三层**：
```text
§417  "按偏移命名，因为第 120 节是发明字段名的代价"
§418  **`HANDOFF 140` 给出了零售名字 `clientLinkInfo` / `entToTakeMarksFrom`**
⇒ **⇒ 所以【两个来源给了两个名字，而代码选择保留偏移名**】
```

**✅ ⭐⭐ **"一个有了名字但仍用偏移名"的保守选择**。**

**⇒ 三层**：
```text
理由 1：**`+0x58` 被 `ET_MISSILE` 用作发射时间** ⇒ **一个成员两个所有者** ⇒ **名字会误导**
理由 2：**第 120 节的代价**
⇒ **⇒ 所以【名字是注释而不是标识符**】
```

**✅ ⭐ **一个"名字放在注释里"的纪律**。

### 2.5 而**"审计脚本"**

```php
// Anything with a non-zero default belongs in this function, and the audit
// that keeps it honest is Tools/olfinal/audit-wire-zero-baseline.py.
```

**⇒ 四层**：
```text
规则：**任何带非零默认值的东西【必须】进这个函数**
工具：**`Tools/olfinal/audit-wire-zero-baseline.py`**
⇒ **⇒ 所以【这条规则是可执行的，不是记忆的**】
```

**✅ ⭐⭐ **"一条规则配一个审计脚本"** —— 与 §411 的"`check_perframe_cost.py` 复核"**同族（**第二次"规则的可执行化"）。

**⇒ 三层**：
```text
§411  **性能主张** ⇒ `check_perframe_cost.py`
§414  **列数/范围主张** ⇒ 我的复算（`373`/`238`/`475..480`）
§418  **默认值主张** ⇒ `audit-wire-zero-baseline.py`
```
**✅ ⭐ **一个"主张必须可执行验证"的三例**。

## 三、**`0x0AC` 在 `scriptmover` 上是 `solid`**（本组第二重要）

### 3.1 那段

```cpp
// Field 28, +0x0AC, 24 bits. Nine distinct values, none of them a
// sentinel. The table names it `eventSequence` at `exact` confidence,
// but the SAME offset is `solid` on a scriptmover and the const
// baselines settled that one the other way -- so it is carried by offset
// and left out of the existing uint8 eventSequence member, which is far
// too narrow to hold 6816015 anyway. Unmeasured.
std::uint32_t actorField00AC{};
```

### 3.2 十四层

```text
1. **字段 `28`，`+0x0AC`，`24` 位**
2. ⇒ **`9` 个不同的值，【没有一个是哨兵**】**
3. ⇒ **netfield 表把它叫 `eventSequence`，'exact' 置信度**
4. ⇒ **而【同一个偏移在 scriptmover 上是 `solid`**】**
5. ⇒ **而【常量基准表把那个方向定死了**】**
6. ⇒ **⇒ 所以它【按偏移携带**】**
7. ⇒ **并被【排除在已有的 `uint8 eventSequence` 成员之外**】**
8. ⇒ **那个成员【远太窄而装不下 `6816015`**】**
9. ⇒ **⇒ 未测量**
```

### 3.3 ⭐⭐⭐ **"`exact` 置信度的名字，被【另一个 eType**】推翻"**

**✅ 这是本报告里**最重要的一次"名字置信度不等于正确性"**。**

**⇒ 三层**：
```text
netfield 表说：`eventSequence`，**`exact` 置信度**
而：**同一个偏移在 scriptmover 上是 `solid`**
⇒ **⇒ 所以【一个 `exact` 的名字只对【某个 eType**】成立**】
```

**⚠ ⚠ 但这仍然可疑**：`solid` 在 §414 是**条目字段**（`SvConstBaselineEntry::solid`，不是 `+0x0AC`）。

**⇒ 三层**：
```text
§414  `solid` 是 `SvConstBaselineEntry` 的一个【独立字段**】
§418  注释说 "`+0x0AC` is `solid` on a scriptmover"
⇒ **⇒ 所以【`solid` 的偏移是 `+0x0AC`**】
```

**✅ ⭐ **一个"`solid` 的偏移"的澄清**（**`+0x0AC`**）。

**⇒ 而 §414 说 brush 的 `solid = 0x00FFFFFF`** ⇒ **而 `+0x0AC` 是 `24` 位 ⇒ `0xFFFFFF` 是满值** ✓

**⇒ 三层**：
```text
`+0x0AC` `24` 位 ⇒ **满值 `0xFFFFFF`**
§414 brush 的 `solid = 0xFFFFFF` ⇒ **满值**
⇒ **⇒ 完全吻合** ✓
```

**✅ ⭐⭐ **一个"`0x00FFFFFF` 的 `24` 位来源"的闭合**。

**⚠ 而"`6816015`"⇒ **`6816015 = 0x68018F`** ⇒ **需要 `23` 位** ⇒ **`uint8` 装不下** ✓

**✅ ⭐ **一个"为什么不能用 `uint8`"的算术验证**。

**⚠ 而"`9` 个不同的值，没有一个是哨兵"⇒ **所以 `0` 可能是其中之一**。**

**⇒ 三层**：
```text
若 `0` 是九个值之一 ⇒ **它不是"没有"**
⇒ **⇒ 所以【`+0x0AC` 在 actor 上不是一个哨兵语义**】
```

**✅ ⭐ **一个"值的分布否证哨兵假设"的实例**。

## 四、**`actorField0058` 的"打包动画状态字"**

### 4.1 那段

```cpp
// Field 11, +0x058, 32 bits. A PACKED ANIMATION-STATE WORD, and the
// model-selector hypothesis was tested and REFUTED (section 12.2): at
// spawn always 0xFF0003xx/0xFF0004xx with a low byte 0..25, later
// 0x000N0000 with bits 16..23 running 1..13. The layout changes over the
// life. Unmeasured -- see SvActorSendUnmeasuredSpawnWords.
```

**⇒ 十四层**：
```text
1. **字段 `11`，`+0x058`，`32` 位**
2. ⇒ **一个【打包的动画状态字**】**
3. ⇒ **而"模型选择器"假设【被测过并【被驳倒**】】（第 12.2 节）**
4. ⇒ **在出生时【总是 `0xFF0003xx`/`0xFF0004xx`】**（**低字节 `0..25`**）
5. ⇒ **后来 `0x000N0000`**（**位 `16..23` 跑 `1..13`**）
6. ⇒ **⇒ 所以【布局在一条命里会改变**】**
7. ⇒ **未测量** ⇒ **见 `SvActorSendUnmeasuredSpawnWords`**
```

### 4.2 ⭐⭐ **"布局在一条命里会改变"**

**✅ 与 §415 的"`_const.ff` 是静态的"**相反（这是**一个随时间变形的字段**）。

**⇒ 三层**：
```text
`ET_SCRIPTMOVER` 的 `+0x58` ⇒ **`2047` 恒定**（§417）
`ET_ACTOR` 的 `+0x58` ⇒ **两个不同的布局**（出生 `0xFF0003xx`，后来 `0x000N0000`）
⇒ **⇒ 所以【同一个偏移在两个 eType 上一个静态一个变形**】
```

**✅ ⭐ **一个"静态 vs 变形"的对照**。

**⚠ 而"`0xFF0003xx` 的 `0xFF` 高字节"⇒ **一个"哨兵 + 数据"的混合**。**

**⇒ 三层**：
```text
`0xFF0003xx`：
  `0xFF` 高字节 ⇒ **可能是一个哨兵/类型**
  `0x0003` ⇒ **`3`**
  `xx` 低字节 ⇒ **`0..25`**
⇒ **⇒ 所以【三个子字段打包在一个 32 位里**】
```

**✅ ⭐ **一个"打包字"的字段分解**。

**⚠ 而"后来 `0x000N0000` 的位 `16..23` 跑 `1..13`"⇒ **`N` 就是那个字节**。**

**⇒ 三层**：
```text
出生：`0xFF 00 03 xx` ⇒ **高字节有值**
后来：`0x00 0N 00 00` ⇒ **高位清零，第二个字节有值**
⇒ **⇒ 所以【同一条命里，高字节先有后无**】
```

**✅ 一个**可验证的观察**。

### 4.3 而**`actorField005C` 与 `actorAttackerEntityNum`**

```cpp
// Field 12, +0x05C, 32 bits. ONE distinct value in the whole census --
// 0x00FFFFFF on all 51 asserts, and 0x00FFFFFF live. An all-ones
// sentinel, and a zero here is index 0 of whatever it selects.
std::uint32_t actorField005C{};
// Field 39, +0x084, 11 bits. 2047 on all 51 asserts -- all-ones "none".
std::uint32_t actorAttackerEntityNum{};
// Field 10, +0x08C, codec -96. 2046 or 2047; 2046 is codec -96's own
// one-bit sentinel, which is what writeEntityGround emits for
// EntityNumWorld.
std::uint32_t actorLoopSound{};
```

**⇒ 十层**：
```text
1. **`+0x05C`（字段 `12`，`32` 位）** ⇒ **全部 `51` 次断言都是 `0x00FFFFFF`**
2. ⇒ **⇒ 一个全一哨兵** ⇒ **零这里是"索引 `0`"**
3. ⇒ **`+0x084`（字段 `39`，`11` 位）** ⇒ **全部 `51` 次 `2047`**
4. ⇒ **⇒ 全一"没有"** ⇒ **`actorAttackerEntityNum`**
5. ⇒ **`+0x08C`（字段 `10`，codec `-96`）** ⇒ **`2046` 或 `2047`**
6. ⇒ **`2046` 是【codec `-96` 自己的【一位哨兵**】**
7. ⇒ **那是 `writeEntityGround` 为 `EntityNumWorld` 发出的**
8. ⇒ **⇒ 所以【同一个 codec、同一个形状、不同的字段**】
```

**✅ ⭐⭐ **"codec `-96` 的一位哨兵是 `2046`"** —— 与 §388 的 `EntityNumWorld = 2046` 闭合 ✓

**⇒ 三层**：
```text
`2046` ⇒ **`EntityNumWorld`**（"世界"，一个合法目标）
`2047` ⇒ **`EntityNumNone`**（"没有"）
而 **codec `-96` 用【一位**】表达"世界"**
⇒ **⇒ 所以【codec 本身编码了"世界 vs 一个号"**】
```

**✅ ⭐⭐⭐ **一个"codec 编码了语义而不只是宽度"的实例**。

## 五、**"flags 与 delta base 是【一个决定】"**（本组第三重要）

### 5.1 那段

```cpp
// The table the client loaded at map load, so the entity writers delta against the
// SAME records the client resolves against. Non-null exactly when
// useEntityBaselines is set: the flag and the delta base are ONE decision, and
// setting the flag without moving the base is what made 237 correctly-numbered
// doors XOR themselves to zero.
const SvConstBaselineTable *constBaselines{};
```

### 5.2 十六层

```text
1. **客户端在地图加载时加载的那张表**
2. ⇒ **⇒ 所以实体写者【对【同一批记录**】做增量**】**
3. ⇒ **⇒ 客户端对同一批记录解析**
4. ⇒ **【非空恰好当 `useEntityBaselines` 被设**】**
5. ⇒ **⇒ 【那个旗标与那个 delta 基准是【一个决定**】】**
6. ⇒ **⇒ 而【设了旗标而不移动基准**】正是**
7. ⇒ **【让 `237` 扇正确编号的门把自己 XOR 成零**】的原因**
```

### 5.3 ⭐⭐⭐ **"设了旗标而不移动基准 ⇒ 237 扇正确编号的门 XOR 成零"**

**✅ 与 §414 的"`base = file` vs `base = ours`"**完全同族（**第三次"基准必须与旗标一致"）。

**⇒ 三层**：
```text
正确：`useEntityBaselines = true` **且** `constBaselines = 表`
错误：`useEntityBaselines = true` **且** `constBaselines = nullptr`
⇒ **⇒ 所以【写者用零基准 ⇒ 发 `value ^ 0 = value`**】
而客户端用【表的记录**】⇒ **`value ^ base`** ⇒ **`value ^ value ^ base`？**
```

**⚠ 让我推**：

**⇒ 三层**：
```text
写者用零基准：`wire = ours ^ 0 = ours`
客户端用表：`decoded = wire ^ base = ours ^ base`
⇒ **⇒ 所以【若 base != 0 ⇒ decoded != ours**】
```

**⚠ 但注释说"XOR 成零"。**

**⇒ 另一种读法**：
```text
写者用【表的记录**】做基准：`wire = ours ^ base`
客户端用【表的记录**】：`decoded = (ours ^ base) ^ base = ours` ✓
⇒ **⇒ 所以正确**
```

**⇒ 而"XOR 成零"可能指的是**：
```text
`wire = ours ^ base` 而【客户端用【零基准**】】⇒ `decoded = ours ^ base`
若 `ours == base` ⇒ `decoded = 0` **且 wire 也是 0** ⇒ **字段不发送**
⇒ **⇒ 所以【客户端保持它的零基准 `0`**】
```

**⚠ 一个**需要标注的推演**（"XOR 成零"的确切含义）。

**✅ 但核心结论清楚**：**旗标与基准必须同步**。

**⇒ 三层**：
```text
§414  `constBaselineStorage.modelIndex = entities[currentIndex].modelIndex` ⇒ **一个字段的基准对齐**
§418  **整个 `constBaselines` 指针与 `useEntityBaselines` 同步**
⇒ **⇒ 同一原则的两个粒度**
```

**✅ ⭐⭐ **"旗标与它的数据必须是一个原子决定"** —— 与 §410 的"帧级白名单不可分割"**同族（**第四次"全局开关的不可分割性"）。

## 六、**`clients` 与 `agents` 的分离**（本组第四重要）

### 6.1 那段

```cpp
// THE ACTORS SECTION'S NON-PLAYER ELEMENTS, kept OUT of `clients`.
//
// `clients` is the server's per-player bookkeeping AND the wire list for the
// ACTORS section, and it cannot be both once agents exist: five consumers
// assume one entry per player -- the sorted-unique bound, the
// playerStates.size() == clients.size() check, the clientInfo lookup, the
// index walk, and the ET_PLAYER entity-to-client resolve. Putting agents in
// there rejected EVERY frame (`frameReject=player_client_count`, snapshots=0,
// client stuck on the map-load screen).
```

### 6.2 十八层

```text
1. **`clients` 是【服务器的每玩家记账**】**
2. ⇒ **而【也是 ACTORS 那一节的线缆列表**】**
3. ⇒ **⇒ 而一旦 agent 存在它【不能两者都是**】**
4. ⇒ **五个消费者【假设每玩家一个条目**】：
      · **排序去重边界**
      · **`playerStates.size() == clients.size()` 检查**
      · **`clientInfo` 查找**
      · **索引遍历**
      · **`ET_PLAYER` 的实体到客户端解析**
5. ⇒ **把 agent 放进去【拒收了【每一帧**】】**
6. ⇒ **（`frameReject=player_client_count`，`snapshots=0`，客户端卡在地图加载屏）**
```

### 6.3 ⭐⭐⭐ **"五个消费者假设每玩家一个条目"**

**✅ 这是本报告里**最重要的一条"隐式不变式"清单**。**

**⇒ 三层**：
```text
显式契约：`clients` 是"线缆列表"
隐式契约：**五个消费者假设 `size() == 玩家数`**
⇒ **⇒ 所以【加一个元素破坏的是【五个地方**】**
```

**✅ 与 §410 的"三条独立的 eType 白名单"**同族（**第三次"同一条数据有多个消费者各自假设"）。

**⇒ 三层**：
```text
§410  **三条白名单**（各自需要维护）
§411  **`weaponSelectSequences_` 与 `resolvedLoadouts_` 的序列号**（各自记账）
§418  **五个消费者**（各自假设）
⇒ **⇒ 三次"多点维护**】
```

**✅ ⭐⭐ **一个"隐式不变式的代价"的三例表**。

**⚠ 而"`frameReject=player_client_count`"⇒ **一个具名的拒绝原因**。**

**✅ ⭐ **一个"拒绝必须有名字"的实例**（否则"帧被拒"不可诊断）。

### 6.4 而**"agent 在写时才合并进那一节，在玩家之后、在更高的槽"**

```cpp
// So agents live here and are merged into the section at write time, after the
// players and at higher slots, which keeps the list ascending as the framing
// requires.
std::vector<SvClientState> agents;
```

**⇒ 六层**：
```text
1. **agent 住在这里**
2. ⇒ **在【写时才合并**】进那一节**
3. ⇒ **在【玩家之后**】**
4. ⇒ **在【更高的槽**】**
5. ⇒ **⇒ 那保持列表【升序**】**
6. ⇒ **而那是【框架所要求的**】**
```

**✅ 而"玩家在前、agent 在后、槽更高"⇒ **一个"槽位分配"的精确规则**。**

**✅ 与 §415 的"`SvAgentSlotCount = 32`"及"`SvEmitPlayersInActorsSection`"**配合。

**⇒ 三层**：
```text
`SvEmitPlayersInActorsSection = true` ⇒ **玩家占用低槽（`slot = clientNum`）**
agent ⇒ **占用高槽**
⇒ **⇒ 所以【`32` 槽里玩家与 agent 共享**】
```

**⚠ 而"玩家 `18` 个 + agent `14` 个 = `32`"⇒ **一个可能的容量冲突**。**

**✅ 一个**需要标注的容量问题**。

## 七、**`SvClientPrediction` 的"解析并丢掉"**

### 7.1 那段

```cpp
// THE CLIENT'S OWN PREDICTED RESULT, WHICH IT SENDS BACK IN EVERY MOVE
// PACKET AND WHICH THIS SERVER PARSED AND THREW AWAY UNTIL NOW.
//
// The five longs that follow the usercmds in a clc move packet are these
// four values plus one that has only ever been observed as zero. They were
// read into ClientPredictedState, stored on the slot, printed to a
// three-shot sample log and never used. The sample log is what identified
// them: `predicted=1140621312,1095761920,3277423512,1354,0` decodes to the
// floats 505.0, 13.0, -217.5 and the integer 1354, and this server's own
// capsule log for the same client reads
// `eType=1 origin=505.0,13.0,-217.5`. Three floats and a command time.
```

### 7.2 二十层

```text
1. **客户端自己的预测结果，它在【每一个移动包里**】发回来**
2. ⇒ **而这个服务器【解析了并丢掉了，直到现在**】**
3. ⇒ **`clc move packet` 里跟随 usercmd 的【五个 `long`**】是这四个值 + 一个只被观察为零的**
4. ⇒ **它们被读进 `ClientPredictedState`，存在槽上，打印到一个【三次采样日志**】**
5. ⇒ **而【从未被使用**】**
6. ⇒ **那个采样日志就是【识别它们的东西**】**
7. ⇒ **`predicted=1140621312,1095761920,3277423512,1354,0`**
8. ⇒ **解码成浮点 `505.0`、`13.0`、`-217.5` 与整数 `1354`**
9. ⇒ **而这个服务器自己为同一个客户端的胶囊日志读**
10. ⇒ **`eType=1 origin=505.0,13.0,-217.5`**
11. ⇒ **⇒ 三个浮点与一个命令时间**
12. ⇒ **`out.exe` 的写者 `sub_678740` 【正好读这些**】**
13. ⇒ **（`ctx->[16] + 1760/1764/1768` 对它即将发出的 `playerState` origin，`+1772` 对它的 `commandTime`）**
```

### 7.3 ⭐⭐⭐ **"那个采样日志就是识别它们的东西"**

**✅ 这是本报告里**最重要的一次"诊断日志的实际价值**。**

**⇒ 三层**：
```text
日志：`predicted=1140621312,1095761920,3277423512,1354,0`（**三次采样**）
解码：`505.0, 13.0, -217.5, 1354`
而服务器的胶囊日志：`origin=505.0,13.0,-217.5`
⇒ **⇒ 所以【两个日志一对，语义就出来了**】
```

**✅ ⭐⭐⭐ **"两个日志交叉解码"** —— 与 §413 的"`+1799` 逐字节是奖励数"**同族（**第二次"两个数字一对就出语义"）。

**⇒ 三层**：
```text
日志 A：`predicted=1140621312` ⇒ **一个裸 hex/十进制**
日志 B：`origin=505.0`        ⇒ **一个可读的浮点**
⇒ **⇒ 所以【A 是 B 的位模式**】
```

**✅ 而我验证**：`1140621312 = 0x43FC8000` ⇒ **`float = 505.0`** ✓

**⇒ 计算**：
```text
0x43FC8000: 符号 0，指数 0x87 = 135 ⇒ 2^8 = 256
尾数 0x7C8000 ⇒ 1 + 0x7C8000/0x800000 = 1 + 0.97265625 = 1.97265625
⇒ 256 × 1.97265625 = 505.0 ✓
```

**✅ **精确吻合**。

**✅ ⭐⭐ **一个"位模式到浮点"的算术验证**。

**⚠ 而"`1095761920 = 0x41500000 = 13.0`"⇒ **也是整数** ✓

**⚠ 而"`3277423512`"⇒ **`> 2^31`** ⇒ **有符号下是负的**。**

**⇒ 计算**：
```text
3277423512 = 0xC3540000
符号 1（负），指数 0x86 = 134 ⇒ 2^7 = 128
尾数 0x540000 ⇒ 1 + 0.65625 = 1.65625
⇒ -128 × 1.65625 = -212.0
```

**⚠ 而注释说 `-217.5`，我算出 `-212.0`。**

**⇒ 让我重算**：
```text
0xC3540000
bits: 1 10000110 10101000000000000000000
指数 = 10000110 = 134 ⇒ 134 - 127 = 7 ⇒ 2^7 = 128
尾数 = 1.10101 (二进制) = 1 + 1/2 + 1/8 + 1/32 = 1 + 0.5 + 0.125 + 0.03125 = 1.65625
⇒ 128 × 1.65625 = 212.0 ⇒ -212.0
```

**⚠ 所以注释的 `-217.5` 与我的 `-212.0` 不一致。**

**⇒ 三层**：
```text
注释：`3277423512` ⇒ `-217.5`
我校验：`0xC3540000` ⇒ **`-212.0`**
⇒ **⇒ 一处【需要标注的差异**】
```

**⚠ 可能是**：
- 我读错了 hex（`3277423512` = `0xC3530000`？）
- 或注释里的另一个数

**⇒ 让我精确计算 `3277423512` 的 hex**：
```text
3277423512 / 16 = 204838969 余 8
204838969 / 16 = 12802435 余 9
12802435 / 16 = 800152 余 3
800152 / 16 = 50009 余 8
50009 / 16 = 3125 余 9
3125 / 16 = 195 余 5
195 / 16 = 12 余 3
12 / 16 = 0 余 12 (C)
⇒ 0xC359838? 不对，让我重算
```

**⇒ 用另一种方法**：
```text
0xC3500000 = 3272605696
3277423512 - 3272605696 = 4817816
4817816 / 65536 = 73.5...  ⇒ 73 × 65536 = 4784128
4817816 - 4784128 = 33688
⇒ 0xC3500000 + 0x49_8398?
```

**⚠ 我算不准 —— 停止猜测，标注为"需要独立核对"。**

**✅ 但结论是**：**`3277423512` 按 IEEE754 解码应当接近 `-217.5`，我的粗略计算给出 `-212` 左右，两者接近但不精确 —— 以注释为准，标注我未能精确复算。**

**⇒ 三层**：
```text
`1140621312` ⇒ **`505.0`** ✓（我精确验证）
`1095761920` ⇒ **`13.0`** ✓（`0x41500000`）
`3277423512` ⇒ **`-217.5`**（**我未能精确复算**）
`1354` ⇒ **commandTime**（整数，非浮点）
`0` ⇒ **一个只被观察为零的值**
```

**✅ ⭐ **一个"三个浮点一个整数"的结构**。

### 7.4 而**`SvPredictedOriginToleranceSquared = 0.01f`**

```cpp
// THE TOLERANCE RETAIL USES TO DECIDE THE CLIENT'S PREDICTION IS RIGHT.
// out.exe's own writer compares the SQUARED distance against 0.0099999998,
// i.e. a tenth of a unit.
constexpr float SvPredictedOriginToleranceSquared = 0.01f;
```

**⇒ 五层**：
```text
1. **零售用来判定"客户端预测是对的"的容差**
2. ⇒ **`out.exe` 自己的写者把【平方距离**】与 `0.0099999998` 比**
3. ⇒ **⇒ 即【十分之一单位**】**
4. ⇒ **⇒ 所以 `sqrt(0.01) = 0.1`** ✓
5. ⇒ **⇒ 一个"平方比较避免开方"的实例**
```

**✅ ⭐ **一个"平方距离"的实例**（与 §412 的 `nearestDistSq` 同族）。

**⇒ 三层**：
```text
§412  `nearestDistSq >= BotEngageMinDistUnits * BotEngageMinDistUnits`
§418  `SvPredictedOriginToleranceSquared = 0.01f` ⇒ **`0.1` 单位**
⇒ **⇒ 两次"存平方避免 sqrt**】
```

**✅ ⭐ **一个性能技巧的两例**。

## 八、`SvHoldBreathState` 与"地址敏感契约"

```cpp
// Native PM_UpdateHoldBreath owns these at playerState +0x298/+0x29C.
// Keep them beside SvPlayerState because WorldClientState's size is an
// address-sensitive engine contract.
struct SvHoldBreathState
{
    std::uint32_t clientNum{};
    float swayScale{ 1.0f };
    std::uint32_t timer{};
};
```

**⇒ 六层**：
```text
1. **原生 `PM_UpdateHoldBreath` 在 `playerState +0x298`/`+0x29C` 拥有它们**
2. ⇒ **把它们【放在 `SvPlayerState` 旁边**】**
3. ⇒ **因为 `WorldClientState` 的大小是一个【地址敏感的引擎契约**】**
4. ⇒ **⇒ 所以【不能加进 `SvPlayerState`，只能做一个兄弟结构**】
```

**✅ 与 §417 的"`SvEntityState` 被 `static_assert` 钉大小"**同族（**第四次"地址敏感"）。

**⇒ 三层**：
```text
策略 1：**加进 `SvPlayerState`** ⇒ **增长 `WorldClientState`** ⇒ **失败**
策略 2：**一个兄弟结构** ⇒ **不动 `WorldClientState`** ⇒ **成功**
⇒ **⇒ 所以【"搬出去"是一个通用的解法**】
```

**✅ ⭐⭐ **"搬出去而不是塞进去"** —— 一个**反复使用的模式**。

**⇒ 而 §417 的 `SvKillcamReplayPose`、`SvSnapshotFrame` 的 `PlayerViewLinkState` 都是同一个模式。**

## 九、关键结论

1. **⭐⭐⭐ `wireZeroBaseline()` 的完整解答**：`SvEntityState{}` **不是零**（`lerpData0058 = 2047`、`scriptMoverField00E4 = 255`），而**每个写者以 `zeroBaseline{}` 开头 ⇒ 那两个比较相等 ⇒ 被跳过 ⇒ 客户端解码出 `0`（实体 `0` 与索引 `0`）**。
2. **⭐⭐⭐ "那些默认值是为了让每个 scriptmover 携带哨兵而加的，而它们互相抵消了自己"** —— 一个**反直觉的自我取消**。
3. **⭐⭐⭐ 修法**：`wireZeroBaseline()` **先 `SvEntityState{}` 再显式把两个改成 `0`** ⇒ **成员默认值保留（新建实体天然带哨兵）而写基准是零（所以 `2047 != 0` ⇒ 会写）** ⇒ **一个精妙的双赢**。
4. **⭐ 事后测量（`HANDOFF 140`）**：**零售 podium 人偶第一帧携带 `clientLinkInfo 255` 与 `entToTakeMarksFrom 2047`，而我们两个都没携带，在那个本该发送它们的改动之后三个小节**。
5. **⭐⭐ 两个"按偏移命名"的字段有了零售名字**：`scriptMoverField00E4` = `clientLinkInfo`、`lerpData0058` = `entToTakeMarksFrom` —— 而**代码【保留偏移名**】（因为 `+0x58` 被 `ET_MISSILE` 用作发射时间，一个成员两个所有者）。
6. **⭐⭐ "任何带非零默认值的东西必须进这个函数，而保持它诚实的审计是 `Tools/olfinal/audit-wire-zero-baseline.py`"`** —— 第二次"规则的可执行化"。
7. **⭐⭐⭐ `+0x0AC`（字段 `28`，`24` 位）**：netfield 表说 `eventSequence`（**`exact` 置信度**），**而同一个偏移在 scriptmover 上是 `solid`，常量基准表把那个方向定死了** ⇒ **一个 `exact` 的名字只对某个 eType 成立**。
8. **⭐ `+0x0AC` 的 `24` 位满值 `0xFFFFFF`** 与 §414 的 brush `solid = 0x00FFFFFF` 闭合；而 `6816015` 需要 `23` 位 ⇒ **`uint8 eventSequence` 装不下**。
9. **⭐ `+0x0AC` 在 actor 上"九个不同的值，没有一个是哨兵"** ⇒ **值的分布否证了哨兵语义**。
10. **⭐⭐ `+0x058` 在 `ET_ACTOR` 上是一个【变形的打包动画状态字】**：出生 `0xFF0003xx`/`0xFF0004xx`（低字节 `0..25`），后来 `0x000N0000`（位 `16..23` 跑 `1..13`）—— **与 `ET_SCRIPTMOVER` 的恒定 `2047` 形成对照**。
11. **⭐⭐ codec `-96` 的"一位哨兵是 `2046`"**：`writeEntityGround` 为 `EntityNumWorld` 发出 `2046` ⇒ **codec 本身编码了"世界 vs 一个号"**，与 §388 的 `EntityNumWorld = 2046` / `EntityNumNone = 2047` 闭合。
12. **⭐⭐⭐ "那个旗标与那个 delta 基准是【一个决定】；设了旗标而不移动基准，正是让 `237` 扇正确编号的门把自己 XOR 成零的原因"`** —— 第四次"全局开关的不可分割性"。
13. **⭐⭐⭐ `clients` 的五个隐式消费者**（排序去重边界、`playerStates.size() == clients.size()`、`clientInfo` 查找、索引遍历、`ET_PLAYER` 实体到客户端解析）⇒ **加一个元素破坏五个地方**；而**把 agent 放进去"拒收了每一帧"**（`frameReject=player_client_count`，`snapshots=0`，卡在地图加载屏）。
14. **⭐ "agent 在写时才合并进那一节，在玩家之后、在更高的槽，那保持列表升序，而那是框架所要求的"`** —— 一个**槽位分配规则**；但**玩家 `18` + agent `14` = `32` 可能冲突**（需标注）。
15. **⭐⭐⭐ `SvClientPrediction` 的"解析并丢掉"**：`clc move packet` 里跟随 usercmd 的五个 `long` 被读进 `ClientPredictedState`、存槽、打印到**三次采样日志**、**从未使用** —— **而那个采样日志就是识别它们的东西**：`predicted=1140621312,...` 与服务器的胶囊日志 `origin=505.0,13.0,-217.5` 一对 ⇒ **三个浮点与一个命令时间**。
16. **⭐ 我精确验证了 `1140621312 = 0x43FC8000 = 505.0` 与 `1095761920 = 0x41500000 = 13.0`**；**第三个 `3277423512` 我未能精确复算到 `-217.5`**（标注）。
17. **⭐ `SvPredictedOriginToleranceSquared = 0.01f`** ⇒ **`0.1` 单位** ⇒ 第二次"存平方避免 `sqrt`"。
18. **⭐⭐ `SvHoldBreathState` 是"搬出去而不是塞进去"**：`PM_UpdateHoldBreath` 拥有 `playerState +0x298`/`+0x29C`，而 **`WorldClientState` 的大小是地址敏感的引擎契约** ⇒ **不能加进 `SvPlayerState`，只能做兄弟结构**。

## 十、未闭合点

- `3277423512` 的 IEEE754 精确值（我算得约 `-212`，注释说 `-217.5`）。
- `SvActorSendUnmeasuredSpawnWords` 的实现。
- `+0x040`（idx11 = `1`）的语义。
- 玩家 `18` 个 + agent `14` 个是否超出 `32` 槽。
- `wireZeroBaseline()` 在 `sv_snapshot_mp.cpp` 里的实际调用点（是否所有写者都用它）。
- `sv_snapshot_mp.hpp` 2330 行之后未读取（**共 `4703` 行**）。
