# 372 · **"在两条线上测同一个问题"** —— 零售 `1909/1909` 相等而本服务器 `95/558` 不等、`4900ms` 的窗口、两个排除数组

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 20400–20800 行。

## 二、**两个游标必须相等**（本组最重要的一段）

### 2.1 那段

```php
// AND THE TWO CURSORS GO OUT EQUAL, BECAUSE THE EVENTS ARE ALREADY
// CONSUMED BY THE TIME THIS LINE RUNS. Netfield 2 is not "the cursor at
// the top of the think" -- it is the cursor of events that have been
// DISPATCHED, and clientEventsHandler_ above has just dispatched every
// one of them. Sending the pre-Pmove value leaves a window of
// `current - old` events standing open on the wire, which is a standing
// instruction to a client that replays it.
//
// MEASURED ON BOTH WIRES, SAME QUESTION (handoff section 172):
//
//   retail C-2021-7-25[1-19-26]dm.demo   6160 snapshots, 621 s
//       netfields 1 and 2 change 1909 times; EVERY ONE of the 1909
//       leaves them EQUAL, and neither ever moves without the other.
//       Total time the window stood open: 0 ms.
//   ours   C-2026-9-2[11-37-7]dm.demo    17798 snapshots, 890 s
//       558 change points, 95 of them leave the two UNEQUAL and 117
//       move one without the other. Total time open: 4900 ms.
//
// That is the only measured divergence from retail anywhere on the
// predictable-event path, and 4900 ms spread over 95 openings is a
// window standing open for one to two snapshots each -- which is the
// shape of "it plays the landing animation three or four times".
```

### 2.2 二十层

```text
1. **而两个游标【相等地】上线**
2. ⇒ **因为事件在这一行运行时【已经被消费】了**
3. ⇒ **netfield 2 不是"think 顶部的游标"**
4. ⇒ **它是【已经被派发】的事件的游标**
5. ⇒ **而上面的 `clientEventsHandler_` 刚刚派发了它们【每一个】**
6. ⇒ **发 pre-Pmove 的值会在线上留一个 `current - old` 个事件的窗口开着**
7. ⇒ **那是一个给【会重放它】的客户端的【常设指令】**
8. ⇒ **在【两条线上】测【同一个问题】**（handoff 第 172 节）：
9. ⇒ **零售 `C-2021-7-25[1-19-26]dm.demo`**：**6160 个快照、621 秒**
     · **netfield 1 与 2 变化 `1909` 次**
     · **那 1909 次里的【每一次】都让它们【相等】**
     · **而两者【从不】在另一个不动时移动**
     · **窗口开着的总时间：`0 ms`**
10. ⇒ **我们 `C-2026-9-2[11-37-7]dm.demo`**：**17798 个快照、890 秒**
     · **558 个变化点**
     · **其中 95 个让两者【不等】**
     · **117 个在另一个不动时移动了一个**
     · **开着的总时间：`4900 ms`**
11. ⇒ **那是可预测事件路径上【唯一】测到的与零售的分歧**
12. ⇒ **而 `4900ms` 分散在 95 次开口上 ⇒ 每次【一到两个快照】**
13. ⇒ **那正是"它把落地动画播三到四次"的形状**
```

### 2.3 ⭐⭐ **"在两条线上测同一个问题"**

**✅ 这是本文件里**最强的证据方法**。**

**⇒ 三层**：

```text
零售：1909 次变化，**1909 次相等，窗口 0ms**
我们：558 次变化，**95 次不等，窗口 4900ms**
⇒ **一个绝对干净 vs 一个明确的分歧**
```

**✅ 与 §355 的 `259,968` / §351 的 `237` / §362 的 `145`**第八次大规模统计。

**⚠ 而"1909/1909"⇒ ****一个绝对的全对**。**

**⇒ 与 §370 的"10/10"、§353 的"15/15"**同族（**第五次"全对"**）。

### 2.4 而**"落地动画播三到四次"**

**✅ 与 §342 的"一个真实事件 + 三个重复"**完全同族（**第四次"事件重复"**）。

**⇒ 三次重复的原因：**

```text
§342  uint8 截断 ⇒ 256 的倍数回跳
§372  游标窗口开着 ⇒ 一到两个快照的重放
```

**✅ **两个不同的根因、同样的"播三到四次"。**

### 2.5 而**"两种客户端解读下都安全"**

```php
// WHY THIS IS SAFE UNDER EITHER READING OF THE CLIENT. If out.exe fires
// the window `[old, current)`, retail's own wire would fire NOTHING, so
// that half is settled by retail's numbers alone; if out.exe instead
// dedups against the previous snapshot and ignores netfield 2, closing
// the window costs nothing. A scan of out.exe for `[reg+12Ch]` masked
// into a ring index came back empty, but that is NOT evidence the
// client ignores the field: the playerstate is reached through a
// containing struct, so the folded displacement is not 0x12C and the
// scan was looking at the wrong base.
```

### 2.6 十一层

```text
1. **为什么这在【任一】客户端解读下都安全**
2. ⇒ **若 `out.exe` 触发窗口 `[old, current)`**
3. ⇒ **零售自己的线会【什么都不触发】**
4. ⇒ **所以那一半【仅由零售的数字】就已定案**
5. ⇒ **若 `out.exe` 反而对前一个快照去重而忽略 netfield 2**
6. ⇒ **关闭窗口【零代价】**
7. ⇒ **一个对 `out.exe` 的 `[reg+12Ch]` 掩码成环索引的扫描【返回空】**
8. ⇒ **但那不是客户端忽略这个字段的证据**
9. ⇒ **因为 playerState 是【通过一个包含结构】到达的**
10. ⇒ **所以折叠位移【不是】`0x12C`**
11. ⇒ **而扫描在【错的基址】上找**
```

### 2.7 ⭐ **"一个返回空的扫描不是证据"**

**✅ 与 §340 的"定向的负面"**完全同族，而这是**一个反例（一个不是定向负面的负面）。**

**⇒ 三层**：

```text
定向的负面：按它【必须】出现的方式找而零命中 ⇒ 确定不存在
普通负面：  按【可能不对】的方式找而零命中 ⇒ **什么也不能说**
```

**✅ 与 §346 的"采样偏差"**同族（**第二次"一个负面因为方法而无效"）**。

**⚠ 而"折叠位移不是 `0x12C`"⇒ **一个精确的技术理由**。**

**✅ 与 §360 的"索引→偏移相同而编解码器不同"**同族（**第四次"偏移会骗人"）。

### 2.8 而**"给一个会重放它的客户端的常设指令"**

**✅ 三层**：

```text
1. 窗口开着 ⇒ `[old, current)` 里的事件【仍在待处理】
2. ⇒ **所以每一帧客户端都重放**
3. ⇒ **⇒ 三到四次**
```

**✅ 一个**精确的机制**。

## 三、**两个排除数组**（本组第二重要）

### 3.1 那段

```php
// AND IT LABELS THE PROJECTION'S OWN VERDICT. out.exe's copier
// BG_PlayerStateToEntityState_CopyEvents (0x00411280) copies every
// event into the entity ring EXCEPT the members of two zero-terminated
// exclusion arrays it walks -- the server-only ids at 0x00DADC0C and
// the non-networked ids at 0x00DADBB8. So an id marked `sv` or `local`
// here is one the engine will never network and which a producer must
// ADD (that is what section 191s did for the fire events); an unmarked
// id reaching the ring is networked automatically, and adding it again
// would send it TWICE. Printing the verdict beside the count is what
// stops that mistake being made from a count alone.
static constexpr std::array<std::int32_t, 10> serverOnlyIds{
    0x1E, 0x1D, 0x23, 0x17, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B};
static constexpr std::array<std::int32_t, 20> nonNetworkedIds{
    0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x4A, 0x15, 0x16, 0x18, 0x4D,
    0x90, 0x91, 0x92, 0x93, 0x94, 0x56, 0x57, 0x58, 0xA7, 0xA8};
```

### 3.2 十二层

```text
1. **并且它标注投影【自己的判决】**
2. ⇒ **`out.exe` 的复制器 `BG_PlayerStateToEntityState_CopyEvents`（`0x00411280`）**
3. ⇒ **把每一个事件拷进实体环【除了】它走的两个零终结排除数组的成员**
4. ⇒ **服务端专属 id 在 `0x00DADC0C`**
5. ⇒ **而非联网 id 在 `0x00DADBB8`**
6. ⇒ **所以一个在这里被标 `sv` 或 `local` 的 id**
7. ⇒ **是引擎【永不联网】的一个** ⇒ **而一个生产者【必须添加它】**
8. ⇒ **（那正是第 191s 节为开火事件所做的）**
9. ⇒ **一个【未标记】的 id 到达环是【自动联网】的**
10. ⇒ **而再添加它一次会把它发【两次】**
11. ⇒ **在计数【旁边】打印判决是阻止那个错误仅从计数作出的事情**
12. ⇒ **所以十个 `sv` 而二十个 `local`**
```

### 3.3 而**十个 `sv`**

```text
0x1E  0x1D  0x23  0x17  0x36  0x37  0x38  0x39  0x3A  0x3B
```

**⚠ 与 §342 的 `isOwnerPredictedEvent` 的二十八个 id**部分重合**。**

**⇒ 而 `0x17`（23）在两者里都有。**

**⇒ 所以**一个事件可以既是所有者预测又是服务端专属**。**

**✅ 与 §370 的"`n 89` 是命令不是按钮"**不同层次**。**

### 3.4 而**二十个 `local`**

```text
0x0C 0x0D 0x0E 0x0F 0x10 0x4A 0x15 0x16 0x18 0x4D
0x90 0x91 0x92 0x93 0x94 0x56 0x57 0x58 0xA7 0xA8
```

**⚠ 与 §342 的 `0x98..0x9F`（脚步）**不同**（`0x90..0x94` 是别的）。**

**✅ 而 `0x18..0x1F` 是换弹（§342）。**

**⇒ 所以 `0x15/0x16/0x18` 与换弹区**部分重合**。**

## 四、**落地的两个事件**（本组第三重要）

### 4.1 那段

```php
if (event.event == SvEventLandingHard) {
    // THE CONTROL, AND ONLY THE FIRST FEW. Landings are as
    // frequent as jumps, and RuntimeLog takes a global lock --
    // section 104 measured a chatty line as the two-player lag.
    // Five per client is enough to answer "does this arrive".
    static std::unordered_map<std::uint32_t, std::uint32_t> loggedHardLandings;
    auto &logged = loggedHardLandings[playerState.clientNum];
    if (logged < 5) { ++logged; write(...); }
    continue;
}
if (event.event != SvEventLandingPain) continue;
const auto packed = SV_LandingPainDamage(event.parameter);
const auto abilities = playerAbilities_.find(playerState.clientNum);
const auto fallScale = abilities == playerAbilities_.end() || abilities->second.spawnGeneration != playerState.spawnGeneration
    ? 1.0f : abilities->second.modifiers.fallDamageScale;
const auto damage = (uint32)(SV_FallDamageApplied(packed) * fallScale);
if (!damage) continue;
pendingFallDamage_[playerState.clientNum] += damage;
```

### 4.2 八层

```text
1. **`SvEventLandingHard` ⇒ 一个【对照】探针**
2. ⇒ **每客户端最多五行**
3. ⇒ **因为 `RuntimeLog` 取一个【全局锁】**
4. ⇒ **而第 104 节测到一个话多的行【就是双人延迟】**
5. ⇒ **所以五行足够回答"它到不到"**
6. ⇒ **`SvEventLandingPain` ⇒ 计算伤害**
7. ⇒ **乘以 `fallDamageScale`（若能力代际匹配）**
8. ⇒ **累加而不是赋值**（"一次 think 里两次落地是两次独立的摔落"）
```

**✅ 与 §349 的"`P5: 每帧零日志`"**完全一致 ✓**

**⇒ **第三次确认那条热路径规则**。**

**⚠ 而"第 104 节测到一个话多的行就是双人延迟"⇒ **一个真实的事故**。**

**✅ 与 §371 的"每帧 `findXAsset` 守卫把战斗服卡成 1.2 秒每帧"**同族（**第二次"日志/守卫导致性能崩溃"）。**

## 五、**`player-kinematics` 的爆发采样**（本组第四重要）

### 5.1 那段

```php
// EVERY COMMAND FOR THE FIRST FOUR SECONDS, THEN ONCE A SECOND.
// The player leaves the ground within about 30 ms of spawning, with zero
// velocity and an unchanged origin. A once-a-second sample cannot contain
// that frame, and every aggregate so far has averaged straight over it.
// PER CLIENT. This was one static for the whole server, so with two
// players client 0 would set it to second 204, client 1 would
// overwrite it with 207, and client 0's next command no longer
// matched -- the once-a-second throttle degenerated into once per
// usercmd, about 140 lines a second, each of them ~200 characters
// written under RuntimeLog's global lock.
```

### 5.2 十一层

```text
1. **前四秒每一条命令，然后每秒一次**
2. ⇒ **玩家在出生后约 `30ms` 内离开地面**
3. ⇒ **零速度而原点不变**
4. ⇒ **一个每秒采样【不能包含那一帧】**
5. ⇒ **而到目前为止每一个聚合都【直接平均过去了】**
6. ⇒ **按客户端**（这是一个服务端级的 `static`）
7. ⇒ **所以两个玩家时客户端 0 设它为 `204` 秒**
8. ⇒ **客户端 1 用 `207` 覆盖它**
9. ⇒ **而客户端 0 的下一条命令【不再匹配】**
10. ⇒ **那个每秒节流【退化成每条 usercmd 一次】**
11. ⇒ **约每秒 140 行，每行约 200 字符，写在 `RuntimeLog` 的【全局锁下】**
```

### 5.3 ⭐ **"一个服务端级的 `static` 在多客户端时退化成每条 usercmd"**

**✅ 与 §346 的 `psDomainBad` 的 `static reported`**完全同族（**第三次"static 跨客户端污染"）。**

**⇒ 三层**：

```text
单客户端：`static second` 正确节流
双客户端：**两个客户端交替覆盖 ⇒ 永不匹配 ⇒ 每条命令都写**
```

**✅ **一个极常见的 bug**，而这里**有精确的量化**（140 行/秒）。**

**⚠ 而"140 行/秒 × 200 字符 × 全局锁"⇒ **正是"双人延迟"的原因**（§104）。**

**✅ **第三次"日志导致性能崩溃"。**

### 5.4 而**ADS 的 20Hz 采样**

```php
// THE ADS SAMPLE IS 1 Hz, AND THE ADS FLIP IS 20 Hz. Measured
// 2026-10-09: `buttons & 0x800` and the view are the two candidates
// still standing for "the sniper scope twitches", and a once-a-second
// sample cannot see a bit that flips every frame. So the sampler
// escalates to per-frame for a BOUNDED window when the ADS bit
// changes, and drops straight back to 1 Hz.
//
// THE BOUND IS THE POINT. The previous per-frame logger in this file
// (the findXAsset guard) turned the game server into 1.2 s per frame
// and took matchmaking down with it.
constexpr int PlayerKinematicsBurstFrames = 60;   // ~3 s at 20 Hz
constexpr int PlayerKinematicsBurstsPerWindow = 3; // per 5 s, per client
```

**⇒ 十三层**：

```text
1. **ADS 采样是 1Hz 而 ADS 翻转是 20Hz**
2. ⇒ **2026-10-09 测量**：`buttons & 0x800` 与视角是两个仍站着的候选
3. ⇒ **而一个每秒采样【看不见一个每帧翻转的位】**
4. ⇒ **所以采样器在 ADS 位变化时【升级到每帧】一个【有界的】窗口**
5. ⇒ **然后直接落回 1Hz**
6. ⇒ **那个界是关键**
7. ⇒ **这个文件里之前的每帧日志（`findXAsset` 守卫）把游戏服务器变成每帧 1.2 秒**
8. ⇒ **并【带走了匹配】**
9. ⇒ **`PlayerKinematicsBurstFrames = 60`**（20Hz 下约 3 秒）
10. ⇒ **`PlayerKinematicsBurstsPerWindow = 3`**（每 5 秒、每客户端）
11. ⇒ **所以最多 `3 × 60 = 180` 行每 5 秒每客户端**
12. ⇒ **而停止时打印 `capped`**
13. ⇒ **"所以一个失控不能是静默的"**
```

**✅ 与 §349 的"`OLMOD_LOG_ENTITY_EVENTS` 的 200 次批量"**同族（**第二次"有界日志"）。

**⚠ 而"一个失控不能是静默的"⇒ **一个极重要的可观测性规则**：**

```text
日志有界 ⇒ **但截断时必须说"我截断了"**
⇒ 否则"零日志"与"日志被限"不可分
```

**✅ 与 §346 的"七十五项合取"**同族（**第五次"沉默的歧义"）。

### 5.5 而 `player-kinematics` 的**十六组字段**

```text
t / org / vel / grav / speed / ground / pmType / pmFlags / pmTime
vhCur / vhTgt / bob / wState / wTime / wDelay
vm / weap / wAnim / legs / torso / spawnGen
cmd{buttons / fwd / right / srvView / cmdView / dA}
pre{org.z / vel / ground}
```

**⇒ 三层**：

```text
1. **二十二组**
2. ⇒ **`cmd{}` 与 `pre{}` 是两个嵌套块**
3. ⇒ **而 `dA` 与 `srvView`/`cmdView` 是从 §371 的诊断继承的**
```

**✅ 与 §371 的"`dA=/srvView/cmdView` 已证明视角通道干净"**完全一致 ✓

**⚠ 而这里说"`yaw(srv-cmd)` 下面是【恒等】`dA[1]`"⇒ **一个自我验证的不变式**。**

**✅ 与 §351 的"`238` 个..."**不同**（那是**数据**，这是**等式**）。**

### 5.6 而**`cmdView` 用 `BG_ShortToAngle`**

```cpp
BG_ShortToAngle(commandState.currentUserCmd.angles[0]),
BG_ShortToAngle(commandState.currentUserCmd.angles[1]),
```

**⇒ 三层**：

```text
1. **usercmd 的角是 16 位短角**
2. ⇒ **必须 `BG_ShortToAngle` 转回度数**
3. ⇒ **才能与 `srvView` 比较**
```

**✅ 与 §364 的"`BG_ShortToAngle`"**第二次。**

## 六、**"他升起来约一个跳跃高度并卡住，在一个没人碰的无头客户端上"**

```php
// HE RISES ABOUT ONE JUMP HEIGHT AND WEDGES, ON A HEADLESS CLIENT
// THAT NOBODY IS TOUCHING. Button bits are a per-build layout in
// this project already -- crouch and prone TOGGLE, and bit 14 is not
// what 3.3.3.3 called it -- so a jump bit read at the wrong position
// would look exactly like this. Print what the command actually
// carries instead of reasoning about what it should.
```

### 6.1 八层

```text
1. **他升起来约一个跳跃高度并卡住**
2. ⇒ **在一个【没人碰的】无头客户端上**
3. ⇒ **按钮位在这个项目里【已经是】逐 build 的布局**
4. ⇒ **（蹲与趴是【切换】的，而 bit 14 不是 3.3.3.3 叫它那样）**
5. ⇒ **所以一个读在【错位置】的跳跃位会看起来【完全像这样】**
6. ⇒ **打印命令【实际携带】的东西，而不是推理它【应该】携带什么**
```

**✅ 与 §370 的"去问键盘不要问镜像"**完全同族（**第三次"打印实际值"）。**

**⇒ **一个贯穿全文件的核心纪律**：**

```text
推理"应该是什么" ⇒ **错**
打印"实际是什么" ⇒ 对
```

**✅ **第七次确认。**

### 6.2 而**"蹲与趴是切换的"**

**⇒ 三层**：

```text
1. 在这个 build 上蹲与趴是【切换】而不是【按住】
2. ⇒ **所以按钮位是【状态】而不是【动作】**
3. ⇒ **而 bit 14 不是 3.3.3.3 叫它那样**
```

**✅ 与 §342 的"`packEntityWeapon` 两个 16 位"**不同**。**

**⚠ 所以**按钮位布局必须逐 build 确认**。**

## 七、**`predictableEventStatus` 的"派发后游标"**

```php
if (predictableEvents->count) {
    client.predictableEventStatus = {
        .commandTime = playerState.commandTime,
        .oldSequence = oldEventSequence,
        .currentSequence = predictableEvents->currentSequence,
        .count = (uint32)predictableEvents->count,
        .events = predictableEvents->events,
    };
}
playerState.predictableEventSequence = (uint32)predictableEvents->currentSequence;
playerState.predictableOldEventSequence = playerState.predictableEventSequence;
```

**⇒ 四层**：

```text
1. **`predictableEventStatus` 保留 pre-Pmove 的游标**（供服务端派发诊断）
2. ⇒ **而线上两个游标都发【派发后】的值**
3. ⇒ **所以两者相等** ✓
4. ⇒ **而诊断仍有旧值**
```

**✅ 与 §372 二的"两个游标相等"**完全闭合 ✓

**⚠ 而"两者相等"⇒ **第二次确认。**

## 八、**"不要过滤 playerstate 环"**

```php
// DO NOT FILTER THE PLAYERSTATE RING. out.exe's "non-networked"
// list belongs to BG_PlayerStateToEntityState (0x411280), where it
// prevents owner-predicted events from being broadcast through an
// entityState. The owning client's playerState correction ring is a
// different stream.
```

### 8.1 六层

```text
1. **【不要】过滤 playerstate 环**
2. ⇒ **`out.exe` 的"非联网"列表属于 `BG_PlayerStateToEntityState`**
3. ⇒ **在那里它阻止所有者预测的事件通过一个 entityState 广播**
4. ⇒ **而拥有客户端的 playerState【修正环】是【一个不同的流】**
5. ⇒ **所以两个排除数组【不适用】于 playerState 环**
6. ⇒ **只适用于 entityState 环**
```

**✅ 与 §342 的"`filterOwnerPredictedEvents` 只作用于实体"**完全闭合 ✓

**⇒ **第三次确认那个两流分离。**

**⚠ 而 §372 三的两个数组**只用于**实体环。**

**✅ **一个精确的适用范围**。

## 九、关键结论

1. **⭐⭐ 两个游标必须相等** —— 因为**事件在这一行运行时已经被派发**，而 `clientEventsHandler_` 刚派发了它们每一个。
2. **"发 pre-Pmove 的值会在线上留一个 `current - old` 个事件的窗口开着 —— 那是一个给会重放它的客户端的【常设指令】"`**。
3. **⭐⭐ "在两条线上测同一个问题"`** —— 零售 **`1909/1909` 相等、窗口 `0ms`** vs 我们 **`95/558` 不等、窗口 `4900ms`**。
4. **"`4900ms` 分散在 95 次开口上 ⇒ 每次一到两个快照 ⇒ 那正是『它把落地动画播三到四次』的形状"`** —— 第四次"事件重复"。
5. **⭐ "在任一客户端解读下都安全"`** —— 若 `out.exe` 触发 `[old, current)` 则**零售自己什么都不触发** ⇒ 那一半**仅由零售的数字定案**。
6. **⭐ "一个对 `out.exe` 的 `[reg+12Ch]` 掩码扫描返回空，但那不是客户端忽略这个字段的证据 —— 因为 playerState 通过一个包含结构到达 ⇒ 折叠位移不是 `0x12C` ⇒ 扫描在错的基址上找"`** —— **一个不是"定向的负面"的负面**。
7. **⭐ 两个排除数组**：**十个 `sv`**（`0x00DADC0C`）与**二十个 `local`**（`0x00DADBB8`），而**在计数旁边打印判决**阻止"仅从计数作决定"。
8. **"一个 `sv` 或 `local` 的 id 引擎永不联网而生产者必须添加；一个未标记的到达环是自动联网的，而再添加会发两次"`**。
9. **落地的两个事件**：`SvEventLandingHard` 是**对照探针**（每客户端五行，因为 `RuntimeLog` 取全局锁而**第 104 节测到一个话多的行就是双人延迟**）。
10. **`pendingFallDamage_ += damage`（累加而非赋值）** —— "一次 think 里两次落地是两次独立的摔落"。
11. **⭐⭐ "一个服务端级的 `static` 在多客户端时退化成每条 usercmd"`** —— 客户端 0 设 `204`、客户端 1 覆盖成 `207` ⇒ **140 行/秒 × 200 字符 × 全局锁**（第三次 static 跨客户端污染）。
12. **⭐ `player-kinematics` 的爆发采样**：**ADS 翻转是 20Hz 而采样是 1Hz ⇒ 看不见一个每帧翻转的位** ⇒ **升级到每帧但有界**（`60` 帧 / `3` 次每 5 秒 / **每客户端**）。
13. **"之前的 `findXAsset` 守卫把游戏服务器变成每帧 1.2 秒并带走了匹配"`** —— 第三次"日志/守卫导致性能崩溃"。
14. **⭐⭐ "所以一个失控不能是静默的"`** —— **停止时打印 `capped`**，否则"零日志"与"日志被限"不可分。
15. **`player-kinematics` 的二十二组字段**，而 **`yaw(srv-cmd)` 恒等于 `dA[1]`** ⇒ **一个自我验证的不变式**。
16. **⭐ "他升起来约一个跳跃高度并卡住，在一个没人碰的无头客户端上"`** —— **按钮位逐 build 不同**（蹲与趴是**切换**，bit 14 不是 3.3.3.3 叫它那样）。
17. **"打印命令【实际携带】的东西而不是推理它【应该】携带什么"`** —— **第七次确认那条核心纪律**。
18. **`predictableEventStatus` 保留 pre-Pmove 游标供诊断**，而**线上两个都发派发后的值**。
19. **⭐ "不要过滤 playerstate 环 —— 两个排除数组属于 `BG_PlayerStateToEntityState`（实体环），而拥有客户端的 playerState 修正环是一个【不同的流】"`** —— 第三次确认两流分离。

## 十、未闭合点

- `SvEventLandingHard` / `SvEventLandingPain` 的 id。
- `PSvLandingPainDamageShift` 的值（13 位打包）。
- `fallDamageScale` 的能力来源。
- 十个 `sv` 与二十个 `local` 的完整事件名。
- `playerState` 的二十二组日志里各字段的完整语义。
- `sv_snapshot_mp.cpp` 20800 行之后未读取（27,016 行，进度 77%）。
