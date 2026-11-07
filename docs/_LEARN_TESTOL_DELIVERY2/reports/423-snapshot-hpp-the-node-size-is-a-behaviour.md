# 423 · **"这个节点的大小是一个行为，不是一个细节"** —— `25184` 字节、`48` 字节代价（`5.3%` 帧与 `222/4153`）、事件环不能加偏移

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 3950–4290 行（`SvServerWorld` 的私有区，**结构性最强的一段**）。

## 二、**`static_assert(sizeof(WorldClientState) == 25184)`**（本组最重要的一段）

### 2.1 那段

```php
// THE SIZE OF THIS NODE IS A BEHAVIOUR, NOT A DETAIL. Section 184h.
//
// WorldClientState is the mapped type of a std::unordered_map, and it holds
// SvGameClient -- whose member 0 is the native playerState the engine keys to
// its own address. Section 141 pinned that member at OFFSET 0 and the assert
// below it still holds; what section 184h found is that the offset was never
// what moved. Forty-eight bytes added to SvCharacterCustomization, which this
// struct holds BY VALUE, changed only the NODE SIZE -- and living players lost
// their leg animation on 5.3% of sampled frames (222 of 4153, against 0 of
// 5830 before), every death returned durationMs=-1, and every corpse T-posed.
// A/B/A: reverting gave 1816/2883, moving the field off the customization gave
// 2883/2883 with the identical mask still on the wire.
//
// WHERE is proved; WHY node size matters to an address-keyed slot is not, and
// this comment does not pretend otherwise.
//
// SO IF YOU ARE HERE BECAUSE THIS FAILED: do not just update the number. The
// number is cheap to change and the animation is not covered by any test. Add
// the field, run a live cycle, kill a player, and read `durationMs` out of
// CodolGameServer.log -- positive means it still selects, -1 means you have
// just done what section 184h did. THEN update the number.
static_assert(sizeof(WorldClientState) == 25184);
```

### 2.2 二十四层

```text
1. **这个节点的大小是【一个行为，不是一个细节**】**
2. ⇒ **`WorldClientState` 是 `std::unordered_map` 的【映射类型**】**
3. ⇒ **它持有 `SvGameClient`**
4. ⇒ **而后者的【成员 `0` 是原生 `playerState`，引擎把它键控到自己的地址**】**
5. ⇒ **第 `141` 节把那个成员钉在【偏移 `0`**】**
6. ⇒ **⇒ 而它下面的断言【仍然成立**】**
7. ⇒ **⇒ 而 `184h` 发现的是：【偏移从来不是移动的东西**】**
8. ⇒ **`48` 字节加到 `SvCharacterCustomization`**（**而这个结构【按值持有它**】）
9. ⇒ **⇒ 【只改变了节点大小**】**
10. ⇒ **⇒ 而【活着的玩家在 `5.3%` 的采样帧上丢掉了它们的腿部动画**】**
11. ⇒ **（`222/4153`，对【之前的 `0/5830`**】）**
12. ⇒ **而【每一次死亡返回 `durationMs = -1`**】**
13. ⇒ **而【每一具尸体 T-pose**】**
14. ⇒ **A/B/A**：
      · **回退 ⇒ `1816/2883`**
      · **把字段移出 customization ⇒ `2883/2883`**（**而那个掩码仍然在线上**）
15. ⇒ **⇒ `WHERE` 是被证明的**
16. ⇒ **而【为什么节点大小对一个地址键控的槽重要【未被证明**】】**
17. ⇒ **⇒ 而【这个注释【不假装不是**】】**
18. ⇒ **⇒ 所以【如果你在这里是因为它失败了：不要就改数字**】**
19. ⇒ **（数字便宜而动画【不被任何测试覆盖**】）**
20. ⇒ **加那个字段，跑一次实机循环，杀一个玩家**
21. ⇒ **并从 `CodolGameServer.log` 里读 `durationMs`**
22. ⇒ **（正数 ⇒ 它仍然会选；`-1` ⇒ 你刚做了 `184h` 做过的事）**
23. ⇒ **然后才改那个数字**
```

### 2.3 ⭐⭐⭐ **"`WHERE` 是被证明的；`WHY` 未被证明，而【这个注释不假装不是】"**

**✅ 这是本报告里**最重要的一条科学诚实**。**

**⇒ 三层**：
```text
已知：**`48` 字节 ⇒ 动画坏**（`A/B/A` 三次测量）
未知：**为什么节点大小会影响一个地址键控的槽**
⇒ **⇒ 而注释【明说未知**】
```

**✅ 与 §419 的"`2→1` 是承重样本"**同族（**第三次"知道到什么程度就说到什么程度"）。

**⇒ 三层**：
```text
§408  "这是测出来的，不是推理的"
§419  "一个略低于 1 的乘数也拟合，所以写成更简单的规则"
§423  "`WHERE` 被证明；`WHY` 未被证明，而注释不假装"
⇒ **⇒ 三次"证据边界的声明**】
```

**✅ ⭐⭐ **一个"证据边界"的三例表**。

### 2.4 而**`A/B/A` 的三个数字**

```text
回退            ⇒ `1816 / 2883`
移出字段        ⇒ `2883 / 2883`
失败            ⇒ `222 / 4153`（`5.3%`）
之前基线        ⇒ `0 / 5830`
```

**⇒ 六层**：
```text
1. **`A/B/A`** ⇒ **回退（`A`）→ 改动（`B`）→ 回退（`A`）**
2. ⇒ **回退到 `1816/2883`** ⇒ **不是 `2883/2883`** ⇒ **部分恢复**
3. ⇒ **把字段移出 ⇒ `2883/2883`** ⇒ **完全恢复**
4. ⇒ **⇒ 所以【"移出"比"回退"更彻底**】
5. ⇒ **而"那个掩码仍然在线上"⇒ 所以【功能没丢，只是位置变了**】
```

**✅ ⭐⭐⭐ **"移出比回退更彻底，而功能仍然在线上"** —— 一个**极精确的 A/B/A 结果解读**。

**⚠ 而"`1816/2883` 是什么"⇒ **两个数字是什么比例**？**

**⇒ 三层**：
```text
`2883` ⇒ **可能是一个实验的总样本**
`1816` ⇒ **其中正常的部分**
⇒ **⇒ 所以【回退只有 `63%` 正常**】
```

**⚠ 一个**需要标注的读数不确定性**（`1816/2883` 的语义未被注释说明）。

### 2.5 而**"数字便宜而动画不被任何测试覆盖"**

**⇒ 五层**：
```text
1. **改数字【便宜**】**
2. ⇒ **而【动画不被任何测试覆盖**】**
3. ⇒ **⇒ 所以【"把断言更新到新值"= 把一个可检出的错误变成一个静默的错误**】
4. ⇒ **⇒ 而【流程必须是：加字段 → 实机 → 读 `durationMs` → 才改数字**】
5. ⇒ **⇒ 一个"测试无法覆盖时的替代流程"**
```

**✅ 与 §411 的"`check_perframe_cost.py` 复核"**不同（**那是自动化的**，这是**一个必须人工执行的替代流程**）。

**⇒ 三层**：
```text
自动化测试：`audit-wire-zero-baseline.py`（§418）
成本检查：`check_perframe_cost.py`（§411）
**不可自动化的**：**动画选择** ⇒ **实机 + 读日志 + 人工判据**
⇒ **⇒ 三类验证的边界**
```

**✅ ⭐⭐ **一个"可自动化 vs 不可自动化"的三层**。

**⚠ 而"`durationMs` 正数 ⇒ 仍会选；`-1` ⇒ 坏了"**⇒ **一个精确的判据。**

**✅ 与 §419 的"`durationMs` 从 `2250` 到 `-1`"**完全闭合 ✓

**⇒ 三层**：
```text
§419  `-1` ⇒ **"没有动画匹配"** ⇒ **T-pose**
§423  **`durationMs` 是那个判据**
⇒ **⇒ 两处同一个信号**
```

**✅ ⭐ **一个"同一个判据"的确认**。

## 三、**四个 `offsetof` 断言**（本组第二重要）

```cpp
static_assert(offsetof(SvPlayerState, offhandWeaponAssetIndex) == 10);
static_assert(offsetof(SvPlayerState, pmTime) == 12);
static_assert(offsetof(SvPlayerState, offhandWeaponSlotA) + 2 ==
    offsetof(SvPlayerState, gravity));
static_assert(offsetof(SvPlayerState, offhandWeaponSlotB) + 2 ==
    offsetof(SvPlayerState, lastSprintStart));
static_assert(offsetof(SvPlayerState, offhandWeaponSlotC) + 2 ==
    offsetof(SvPlayerState, legsTimer));
static_assert(sizeof(SvCharacterCustomization) == 64);
```

**⇒ 五层**：
```text
1. **`offhandWeaponAssetIndex` 在偏移 `10`** ⇒ `uint8 clientNum(0)` + `uint32 commandTime(4)` + `uint8 pmType(8)` + `uint8 killstreak(9)` ⇒ **`10`** ✓
2. ⇒ **`pmTime` 在 `12`** ⇒ **`offhandWeaponAssetIndex` 是 `uint16`（`10..11`）** ⇒ **`12`** ✓
3. ⇒ **三个 `offhandWeaponSlot` 都插在【两个字段之间**】**
4. ⇒ **`sizeof(SvCharacterCustomization) == 64`** ⇒ **而那个失败的版本是 `64 + 48 = 112`**
5. ⇒ **⇒ 所以【单独钉住它，因为它是"看起来无害的那个"】**
```

### 3.1 ⭐⭐⭐ **"单独钉住它，因为它是最诱人的那个：它看起来像一个普通值类型而它被嵌在上面"**

```php
// And the struct that actually got grown, pinned separately because it is the
// tempting one: it looks like a plain value type and it is embedded above.
static_assert(sizeof(SvCharacterCustomization) == 64);
```

**⇒ 三层**：
```text
`SvCharacterCustomization` ⇒ **看起来像一个普通值类型**（`std::array<uint16,12>` + 几个标量）
而它 ⇒ **被按值嵌在 `WorldClientState` 里**
⇒ **⇒ 所以【改它会改节点大小**】
```

**✅ ⭐⭐ **"看起来无害的那个"** —— 与 §413 的"`sub_53F5F0` 返回 null 而 `sub_59CC70` 不检查"**同族（**第六次"看起来对的最危险"）。

**⇒ 三层**：
```text
§416  **一个地址在目标 build 里存在但做别的事**
§421  **两个正确的东西不能组合**
§423  **一个看起来无害的值类型按值嵌入**
⇒ **⇒ 三次"表面无害**】
```

**✅ ⭐⭐ **一个"表面无害"的三例表**。

**⚠ 而"`offhandWeaponAssetIndex == 10`"⇒ **一个具体的偏移钉。**

**⇒ 三层**：
```text
`clientNum`      `uint32` ⇒ `0..3`
`commandTime`    `uint32` ⇒ `4..7`
`pmType`         `uint8`  ⇒ `8`
`killstreak`     `uint8`  ⇒ `9`
`offhandWeaponAssetIndex` `uint16` ⇒ **`10..11`**
`pmTime`         `uint32` ⇒ **`12..15`**
⇒ **⇒ 完全吻合**
```

**✅ ⭐⭐ **一个"偏移布局"的算术验证**。

**✅ 而注释说"Use the existing alignment gap before `pmTime`"**（§416 的 1265 行）⇒ **所以那个 `uint16` 用了一个本来就有的空洞。**

**⇒ 三层**：
```text
`uint8` × 2 ⇒ **`8..9`**
若无那个 `uint16` ⇒ **`pmTime` 会在 `10`** ⇒ **不对齐**（`uint32` 需 `4` 对齐）
⇒ **⇒ 所以【`pmTime` 本应在 `12`**，而 `10..11` 是空洞】
```

**✅ ⭐⭐⭐ **"用既有的对齐空洞"** —— 一个**零成本的字段插入**。

**⇒ 三层**：
```text
策略：**在既有的对齐空洞里插字段** ⇒ **节点大小不变**
vs：**加字段到末尾** ⇒ **节点变大** ⇒ **`184h` 的故障**
⇒ **⇒ 所以【前者的成本是零**
```

**✅ ⭐ **一个"零成本扩展"的手法**（`SvPlayerState` 里的 `offhandWeaponSlotA/B/C` 三处都是）。

## 四、**`SvPlayerEventRing` 的完整历史**（本组第三重要）

### 4.1 那段

```php
// THE SERVER OWNS A PLAYER'S ENTITY EVENT RING, and it has to, because
// it adds events the native projection knows nothing about.
//
// The first attempt emitted `native sequence + this frame's additions`.
// That drops shots: fire on two consecutive frames with no native event
// (a footstep, a jump) in between and both frames emit the SAME
// sequence, so the client sees no change and skips the second. The
// player's words were "it seems to be working, but not for every single
// shot", which is exactly that.
//
// Nor can the offset simply be added to the native sequence: the client
// reads slot = sequence & 3, so shifting our sequence past the native
// one would make it read NATIVE events out of the wrong slots.
//
// So the ring is rebuilt: new native events are copied in at OUR
// sequence, then our own are appended, and the whole thing is stored
// back after the event handler runs.
```

### 4.2 二十四层

```text
1. **服务器【拥有**】一个玩家的实体事件环**
2. ⇒ **⇒ 而它【必须**】，因为它加了【原生投影一无所知**】的事件
3. ⇒ **第一次尝试发出【`native sequence + 这一帧的新增**】**
4. ⇒ **⇒ 那【丢掉射击**】**
5. ⇒ **在两帧上开火而中间【没有原生事件**】（一个脚步、一个跳跃）**
6. ⇒ **⇒ 而两帧发出【同一个序列**】**
7. ⇒ **⇒ 所以客户端【看不见变化**】而【跳过第二个**】**
8. ⇒ **玩家的原话**："它似乎在工作，但不是为每一发都工作"
9. ⇒ **⇒ 而那【正是那个**】**
10. ⇒ **也【不能就地把偏移加到原生序列上**】**
11. ⇒ **因为客户端读 `slot = sequence & 3`**
12. ⇒ **⇒ 所以【把我们的序列移到原生序列之外会让它从【错误的槽**】读原生事件**】**
13. ⇒ **所以那个环被【重建**】**
14. ⇒ **新的原生事件【用【我们的**】序列拷进来**】
15. ⇒ **然后【我们自己的被追加**】**
16. ⇒ **而【整件事在事件处理器跑完之后【被存回去**】**
```

### 4.3 ⭐⭐⭐ **"玩家的原话：它似乎在工作，但不是为每一发都工作"**

**✅ 这是本报告里**最重要的一次"玩家描述 ⇔ 机制"的对齐**。**

**⇒ 三层**：
```text
机制：**两帧同一个序列 ⇒ 客户端跳过第二个**
症状：**"不是为每一发都工作"**（**隔一发丢一发**）
⇒ **⇒ 所以【玩家的模糊描述精确对应一个具体的序列 bug**】
```

**✅ 与 §410 的"我保证那个卡顿是由你那个蠢 obituary 引起的"**不同（**那里玩家诊断错**；这里**玩家描述精确**）。

**⇒ 三层**：
```text
§410  **玩家的诊断错而决定对**
§423  **玩家的描述精确对应机制**
⇒ **⇒ 两种"玩家输入"的价值**
```

**✅ ⭐⭐ **一个"玩家输入"的两例**。

**⚠ 而"`sequence & 3`"⇒ **`4` 个槽 ⇒ `2` 位**。**

**✅ 与 §416 的"`predictableEvents` 的 `4` 个环槽"**完全闭合 ✓

**⇒ 三层**：
```text
`SvPlayerEventRing::ring` ⇒ **`std::array<SvEntityEvent, 4>`**
`SvPlayerState::predictableEvents` ⇒ **`std::array<SvEntityEvent, 4>`**
⇒ **⇒ 两个 4 槽环**
```

**⚠ 一处**需要区分的两个环**：`playerEventRings_`（服务器拥有，可加事件）vs `predictableEvents`（原生 pmove 的输出）。**

**⇒ 三层**：
```text
`SvPlayerState::predictableEvents` ⇒ **原生 pmove 产生**（§416："被读了、被服务端用了、并在线上之前被丢掉"）
`SvPlayerEventRing` ⇒ **服务器拥有**，可加自己的事件
⇒ **⇒ 所以【两个环，前者是数据源，后者是发布通道**】
```

**✅ ⭐⭐ **一个"数据源 vs 发布通道"的区分**。

### 4.4 而**"不能就地把偏移加到原生序列上"**

**⇒ 六层**：
```text
朴素方案：`ourSequence = nativeSequence + N` ⇒ **只要推到原生之外**
问题：**客户端读 `slot = sequence & 3`** ⇒ **`N` 不是 `4` 的倍数 ⇒ 槽错位**
⇒ 若 `N = 4` ⇒ **槽对齐但序列与原生相同**
⇒ **⇒ 所以【加法方案【根本不可行**】】
```

**✅ ⭐⭐ **"一个看起来显然的方案被一个细节否证"**。

**✅ 与 §419 的"一个略低于 1 的乘数也拟合"**不同（这是**一个方案被完全排除**）。

### 4.5 而**"`mutable` 因为 `clientThinkReal` 是 `const`"**

```cpp
mutable std::unordered_map<std::uint32_t, SvPlayerEventRing>
    playerEventRings_;
```

**⇒ 四层**：
```text
1. **`mutable`**
2. ⇒ **因为 `clientThinkReal` 是 `const`**
3. ⇒ **⇒ 所以【一个 `const` 成员函数需要写这个 map**】
4. ⇒ **⇒ 而【`mutable` 是唯一的方法**】
```

**✅ 而"`mutable std::array<bool, MaximumGameClients> pendingAltToggle_`"也是同理**：

```php
// One pending alt-fire toggle per client. A plain array so nothing is
// added to a struct the address-keyed native buffer contains.
// mutable for the same reason playerEventRings_ is: the think that
// consumes it is const.
```

**⇒ 五层**：
```text
1. **每个客户端一个待处理的 alt-fire 切换**
2. ⇒ **一个【普通数组**】**
3. ⇒ **⇒ 所以【没有东西被加到【那个地址键控的原生缓冲所包含的结构**】上**
4. ⇒ **`mutable` 同理由**
5. ⇒ **⇒ 所以【"避免加到那个结构"是一个【反复出现的约束**】**
```

**✅ 与 §422 的"搬出去"**完全同族（**第三次"搬到兄弟结构"）。

**⇒ 三层**：
```text
`playerEventRings_` ⇒ **`WorldClientState` 之外**
`pendingAltToggle_` ⇒ **`MaximumGameClients` 的普通数组**
`zombieDowned_`（§420）⇒ **`unordered_map`**
`zombieBattery_`（§423）⇒ **`MaximumGameClients` 的数组**
⇒ **⇒ 四种"搬出去"的形态**
```

**✅ ⭐⭐ **一个"搬到外面"的四例表**。

### 4.6 而**"一个明确的 CAVEAT"**

```php
// CAVEAT, stated rather than hidden: a REJECTED command candidate does
// not roll this back, so a rejected frame can leave the sequence one
// ahead. Rejections are rare (frameReject=none across the logs) and the
// cost is one missed dispatch, not a desync -- the client resyncs its
// cursor whenever the sequence moves the other way.
```

**⇒ 十层**：
```text
1. **一个 CAVEAT，"
陈述出来而不是藏起来**"**
2. ⇒ **一个【被拒绝的命令候选【不会回滚**】这个**
3. ⇒ **⇒ 所以【一个被拒绝的帧可以让序列【超前一个**】】**
4. ⇒ **而【拒绝是罕见的**】（`frameReject=none` 跨日志）
5. ⇒ **而【代价是【一次错过的派发**，不是一次失同步**】**
6. ⇒ **⇒ 因为【客户端在序列【向另一边移动**】时，"
重同步它的游标**"**
```

**✅ ⭐⭐⭐ **"陈述出来而不是藏起来"** —— 一个**已知缺陷的诚实记录**。

**✅ 与 §419 的"`WHERE` 被证明，`WHY` 未被证明，而注释不假装"**同族（**第四次"明确的边界**）。

**⇒ 三层**：
```text
§408  "`STILL NOT SENT` 每个都有一个理由"
§419  "`WHERE` 证明 / `WHY` 未证明"
§423  "`CAVEAT`，陈述出来而不是藏起来"
⇒ **⇒ 三次"把不确定性写进代码**】
```

**✅ ⭐⭐ **一个"把不确定性写进代码"的三例表**。

**⚠ 而"客户端在序列向另一边移动时重同步游标"⇒ **一个从机制推导的缓解**。**

## 五、**`pendingAnimationCommands_` 的"四个连续帧"**

```php
// Retail carries each new packet-animation operation through four
// consecutive snapshot frames. The writer may then reuse an equal
// record from the selected delta baseline. This survives beginFrame's
// snapshot reset and is decremented only after endFrame commits.
std::vector<PendingAnimationCommand> pendingAnimationCommands_;
```

**⇒ 八层**：
```text
1. **零售把每一个新的 packet-animation 操作【通过四个连续的快照帧**】携带**
2. ⇒ **⇒ 然后写者【可以从选中的 delta 基准里【复用一个相等的记录**】】**
3. ⇒ **⇒ 所以【那个 delta 基准【必须持有它**】】**
4. ⇒ **这【在 `beginFrame` 的快照重置中【存活**】】**
5. ⇒ **而【只在 `endFrame` 提交之后【递减**】】**
```

### 5.1 ⭐⭐⭐ **"四个连续帧，然后可以从 delta 基准复用"**

**✅ 这是本报告里**最重要的一条"冗余与 delta 的配合**。**

**⇒ 三层**：
```text
要求：**客户端必须【最终收到**那个操作**
但：**快照可能丢失** ⇒ **一个帧不够**
⇒ **⇒ 所以【重复 `4` 帧**】**
而：**重复会让 delta 变大**
⇒ **缓解：`4` 帧后 delta 基准已有它 ⇒ 复用它 ⇒ 大小回到 `0`**
```

**✅ ⭐⭐ **"重复 4 帧后 delta 基准接管"** —— 一个**冗余与压缩的精确配合**。

**✅ 与 §413 的"`SnapshotHistoryCapacity = 32` / `SnapshotDeltaWindow = 29`"**配合。

**⇒ 三层**：
```text
历史容量 `32`
delta 窗口 `29`
重复 `4` 帧 ⇒ **总在窗口内** ✓
⇒ **⇒ 所以【`4 << 29`**】
```

**✅ ⭐ **一个"参数协同"的验证**。

**⚠ 而"一个相等的记录"⇒ **`SvAnimationCommand` 有 `operator==`**（§417 的 `bool operator==(const SvAnimationCommand &) const = default;`）✓

**✅ ⭐ **一个"比较运算符的用途"**。</br>

**✅ 与 §414 的"一个实体与其基准相同时有自己的编码"**同族（**第二次"相等即省略"）。

## 六、**`rebuildCollisionView` 的两个阶段**

```cpp
void rebuildCollisionView(
    SvNativeEntityMirrorPhase phase = SvNativeEntityMirrorPhase::Collision);
```

**⇒ 五层**：
```text
1. **`SvNativeEntityMirrorPhase` 是一个枚举**
2. ⇒ **默认 `Collision`**
3. ⇒ **⇒ 所以【至少两个阶段**】（另一个可能是 `Native`）
4. ⇒ **而 `SV_ValidateSnapshotFrame` 与 `endFrame` 都提到"native entity mirror 未同步"**
5. ⇒ **⇒ 所以【这是一个两步同步**】
```

**✅ 与 §413 的"`endFrame` 在原生实体镜像未同步时拒绝"**完全闭合 ✓

**⇒ 三层**：
```text
`rebuildCollisionView(Collision)` ⇒ **第一步**
`rebuildCollisionView(Native)` ⇒ **第二步**
⇒ **⇒ 而 `endFrame` 检查【两者都已同步**】
```

**✅ ⭐ **一个"两阶段同步"的实例**。

## 七、**`markPlayerPainted` 与 "PAINT"**

```cpp
void markPlayerPainted(std::uint32_t clientNum);
void clearPlayerPaint(std::uint32_t clientNum);
void expirePaintedPlayers();
```

**⇒ 四层**：
```text
1. **"标记、清除、过期"三个操作**
2. ⇒ **⇒ 所以【"painted" 是一个有期限的状态**】**
3. ⇒ **而"expire" 是一个【批量定期**】操作**
4. ⇒ **⇒ 与 `deathView`/`prematchHold` 同形**
```

**⚠ 而"painted" 的具体语义**⇒ **未在此段说明**（可能是"这个玩家已被画过"用于某些优化或去重）。

**✅ 一个**未闭合点**。

## 八、关键结论

1. **⭐⭐⭐ "这个节点的大小是一个行为，不是一个细节：`48` 字节加到 `SvCharacterCustomization`（按值持有）只改变了节点大小，而活着的玩家在 `5.3%` 的采样帧上丢掉了腿部动画（`222/4153`，对 `0/5830`），每一次死亡返回 `durationMs = -1`，每一具尸体 T-pose"`**。
2. **⭐⭐⭐ `A/B/A` 的完整结果**：**回退 ⇒ `1816/2883`；把字段移出 customization ⇒ `2883/2883`（而那个掩码仍然在线上）** ⇒ **"移出比回退更彻底，而功能没丢，只是位置变了"**。
3. **⭐⭐⭐ "`WHERE` 是被证明的；`WHY` 节点大小对一个地址键控的槽重要【未被证明】，而这个注释【不假装不是】"`** —— 第三次"证据边界的声明"。
4. **⭐⭐⭐ "如果你在这里是因为它失败了：不要就改数字 —— 数字便宜而动画【不被任何测试覆盖**】；加字段、跑一次实机循环、杀一个玩家、从 `CodolGameServer.log` 读 `durationMs`（正数 ⇒ 仍会选；`-1` ⇒ 你刚做了 `184h` 做过的事），**然后才改数字**"`** —— 一个"测试无法覆盖时的替代流程"，也是**三类验证的边界**（自动化 Python / 成本脚本 / **必须人工的实机判据**）。
5. **⭐ 四个 `offsetof` 断言全部可算术验证**：`offhandWeaponAssetIndex == 10`（`uint32 + uint32 + uint8 + uint8`）、`pmTime == 12`、三个 `offhandWeaponSlot` 都**插在既有的对齐空洞里**。
6. **⭐⭐⭐ "在既有的对齐空洞里插字段 ⇒ 节点大小不变"** —— 一个**零成本扩展**的手法（`SvPlayerState` 里三处 `offhandWeaponSlot` 都是）。
7. **⭐⭐⭐ `SvCharacterCustomization` 被单独钉住，"因为它是最诱人的那个：它看起来像一个普通值类型而它被嵌在上面"`** —— 第六次"表面无害的最危险"。
8. **⭐⭐⭐ `SvPlayerEventRing` 的完整历史**：**第一次尝试 "`native sequence + 这一帧的新增`" ⇒ 丢射击（两帧同一个序列 ⇒ 客户端看不见变化 ⇒ 跳过第二个）**，而 **玩家的原话"它似乎在工作，但不是为每一发都工作"精确对应那个机制**。
9. **⭐⭐ "也不能就地把偏移加到原生序列上，因为客户端读 `slot = sequence & 3` ⇒ 把我们的序列移到原生之外会让它从错误的槽读原生事件"`** —— 一个"看起来显然的方案被一个细节否证"。
10. **⭐ 修法是重建环**：**新的原生事件用【我们的】序列拷进来，然后追加我们自己的，整件事在事件处理器之后存回去**。
11. **⭐⭐ 两个环的区分**：`SvPlayerState::predictableEvents`（**原生 pmove 产生**，§416 说"读了、用了、在线上之前丢掉"）vs `SvPlayerEventRing`（**服务器拥有**，可加自己的事件）⇒ **数据源 vs 发布通道**。
12. **⭐⭐⭐ "一个明确陈述出来而不是藏起来的 CAVEAT：一个被拒绝的命令候选不会回滚这个，所以一个被拒绝的帧可以让序列超前一个；拒绝是罕见的（`frameReject=none` 跨日志）而代价是【一次错过的派发，不是一次失同步**】，因为客户端在序列向另一边移动时重同步它的游标"`** —— 第四次"把不确定性写进代码"。
13. **⭐⭐⭐ `pendingAnimationCommands_` 的"四个连续帧"**：**零售把每个新操作通过四个连续快照帧携带 ⇒ 然后写者可以从选中的 delta 基准复用一条相等的记录 ⇒ 而它只在 `endFrame` 提交之后递减** ⇒ **冗余与压缩的精确配合**（`4 << SnapshotDeltaWindow = 29`）。
14. **⭐ `mutable` 的三处用途**（`playerEventRings_` / `pendingAltToggle_` / `lastPlayerVocalTime_`？）**因为 `clientThinkReal` 是 `const`**；而 **`pendingAltToggle_` 用"一个普通数组"的理由是"没有东西被加到那个地址键控的原生缓冲所包含的结构上"** —— 第三次"搬到外面"。
15. **⭐ `rebuildCollisionView` 有两个阶段**（`SvNativeEntityMirrorPhase`），与 `endFrame` 的"原生实体镜像未同步"检查闭合。

## 九、未闭合点

- `1816/2883` 与 `2883/2883` 的确切含义（分子分母各是什么）。
- `markPlayerPainted` 的"painted" 语义。
- `SvNativeEntityMirrorPhase` 的完整枚举。
- `lastPlayerVocalTime_` 是否也是 `mutable`（未见）。
- `staticBaselineEntities_` 的"add-on campaign map的 base-map rows"。
- `sv_snapshot_mp.hpp` 4290 行之后未读取（**共 `4703` 行**）。
