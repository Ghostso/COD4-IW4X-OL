# 421 · **"一个授予被记录为服务器拥有的状态，并在每次 pmove 之后重新断言"** —— 原生 pmove 会删掉没被正确给予的武器、`a <weapon>` 是唯一告知通道、以及 `ActorRoute` 的四十个字段

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 3290–3620 行。

## 二、**"原生 pmove 会删掉一个玩家没被正确给予的武器"**（本组最重要的一段）

### 2.1 那段

```php
// GIVE A PLAYER A WEAPON -- the owner this server has never had, and the
// reason both loot pickup and the fists spawn were stuck.
//
// The native pmove DELETES a weapon the player was not properly given: the
// measurement was `weapon ACROSS PMOVE before=1137 after=0` on the very first
// frame, heldWeapons wiped with it. Nothing here can perform the native give,
// so a grant is recorded as SERVER-OWNED STATE and re-asserted after every
// pmove, the same way setPlayerNoclip holds noclip. Empty hands are simply the
// grant a player starts with.
//
// The resolver turns a weapon asset index into a full definition (ammo index,
// clip index, clip size, max ammo). Without it a grant cannot fill ammo and
// the weapon would be unfireable, so a grant is refused when it is unset.
```

### 2.2 二十层

```text
1. **给一个玩家一把武器 —— 这个服务器【从未拥有过的所有者**】**
2. ⇒ **⇒ 而那是【拾取与拳头出生两者都卡住**】的原因**
3. ⇒ ⇒ **原生 pmove【删掉一个玩家【没有被正确给予**】的武器**】**
4. ⇒ **测量：`weapon ACROSS PMOVE before=1137 after=0` 在【第一帧**】上**
5. ⇒ **`heldWeapons` 【随之被清空**】**
6. ⇒ **这里【没有任何东西能做原生给予**】**
7. ⇒ **⇒ 所以一个授予被记录为【服务器拥有的状态**】**
8. ⇒ **并在【每一次 pmove 之后重新断言**】**
9. ⇒ **与 `setPlayerNoclip` 持有的方式【一样**】**
10. ⇒ **空手【就是"一个玩家开始时的那个授予**】】**
11. ⇒ **resolver 把一个武器资产索引变成一个完整定义**
12. ⇒ **（弹药索引、弹匣索引、弹匣大小、最大弹药）**
13. ⇒ **没有它一个授予【填不了弹药**】**
14. ⇒ **而武器会【无法开火**】**
15. ⇒ **⇒ 所以【resolver 未设时【一个授予被拒绝**】】**
```

### 2.3 ⭐⭐⭐ **"原生 pmove 删掉一个没被正确给予的武器"**

**✅ 这是本报告里**最重要的一个"引擎是权威"**。**

**⇒ 三层**：
```text
假设：**服务端把 `heldWeapons` 填上就能给武器**
真相：**下一次 pmove 会删掉它**（`before=1137 after=0` 在**第一帧**）
⇒ **⇒ 所以【只有引擎自己的 give 才算数**】
```

**✅ 与 §413 的"零 viewmodel ⇒ AV"**同族（**第四次"引擎不检查地覆写"）。

**⇒ 三层**：
```text
§413  `sub_59CC70` **不检查地写穿一个 null**
§416  `sub_53F5F0` **返回 `0`** ⇒ `sub_59CC70` 写穿
§421  **pmove 删掉未正确授予的武器**
⇒ **⇒ 三次"引擎的权威不可绕过**】
```

**✅ ⭐⭐⭐ **一个"引擎权威"的三例表**。

**⚠ 而"`before=1137 after=0`"⇒ **`1137` 与 §388 的 `1147..1154` 不同**。**

**⇒ 三层**：
```text
`1137` ⇒ **一个具体的武器号**
`1147` ⇒ **`firstDynamicWeapon`**（§388）
⇒ **⇒ 所以 `1137 < 1147`** ⇒ **一个地图自带的武器**
```

**✅ ⭐ **一个"静态 vs 动态武器号"的区分**。

### 2.4 而**"与 `setPlayerNoclip` 同样的方式"**

```php
// NOCLIP IS A HELD STATE, NOT A WRITE. holdMatchCompletionState says
// why: "the world rebuilds each client's playerState from pmove, so a
// single write is overwritten on the very next frame". This records the
// request and clientThink re-applies it ahead of every pmove until it
// expires. holdMilliseconds 0 takes SvNoclipDefaultHoldMilliseconds.
```

**⇒ 十层**：
```text
1. **`noclip` 是一个【持续的状态，不是一次写**】**
2. ⇒ **`holdMatchCompletionState` 说为什么："世界从 `pmove` 重建每个客户端的 `playerState`，所以【一次单写会在【下一帧】被覆写**】"**
3. ⇒ **⇒ 这里【记录请求**】**
4. ⇒ **而 `clientThink` 【在每一次 pmove 之前重新应用它**】**
5. ⇒ **直到它过期**
6. ⇒ **`holdMilliseconds == 0` ⇒ 取 `SvNoclipDefaultHoldMilliseconds`（`1500`）**
```

### 2.5 ⭐⭐⭐ **"世界从 pmove 重建每个客户端的 playerState"**

**✅ 这是本报告里**最重要的一条架构事实**。**

**⇒ 三层**：
```text
架构：**`playerState` 是 pmove 的【输出**，不是输入**
⇒ **⇒ 所以【任何直接写入都会被下一帧覆写**】
⇒ **⇒ 所以【"持续状态"必须每帧重新应用**】
```

**✅ 与 §413 的"`thinkBudget` 的基准必须随它前进"**不同（这是**一个被覆写的输出**）。

**⇒ 三层**：
```text
§409  `holdMatchCompletionState` **每帧重建**
§421  **所有"持续状态"都必须在 pmove 之前重新应用**
⇒ **⇒ 同一个架构事实的两次应用**
```

**✅ ⭐⭐ **一个"输出而非输入"的架构判断**。

**⚠ 而"三个这样的状态"：`noclip`、武器授予、`matchEndFreeze`**（§412）。

**⇒ 三层**：
```text
`setPlayerNoclip` ⇒ **持续到过期**（`1500`/`10000`）
`givePlayerWeapon` ⇒ **持续到 `clearPlayerWeaponGrant`**
`setPlayerMatchEndFreeze` ⇒ **持续到比赛结束**
⇒ **⇒ 三个"重新断言"的状态**
```

**✅ ⭐ **一个"重新断言"的三例表**。

### 2.6 而**"空手就是玩家开始时的那个授予"**

**✅ 与 §413 的"空手出生不可用（`viewmodelIndex = 0` ⇒ AV）"**——**但这里说"空手是一个授予"**。**

**⇒ 三层**：
```text
§413  **"空手出生"不可用**（`viewmodelIndex = 0` ⇒ `sub_53F5F0` 返回 null ⇒ AV）
§421  **"空手是一个玩家开始时的那个授予"**
⇒ **⇒ 矛盾？**
```

**⚠ 可能**：§413 说的是**BR 的"空手出生"**（`no loadout`），而 §421 说的是**"一个 `unarmed` 授予"**（有武器号但为空手的武器）。

**⇒ 三层**：
```text
`SvClientSpawnConfig::unarmed` ⇒ **一个"拳头"武器**（有 `weaponAssetIndex`）
vs **`no loadout`** ⇒ **`viewmodelIndex = 0`** ⇒ **AV**
⇒ **⇒ 所以【"空手"有两种，一种有武器号一种没有**】
```

**✅ ⭐⭐ **一个"空手"的歧义澄清**。</br>

**✅ 而 §421 的 `setUnarmedSpawnWeapon(uint16_t)` 要**一个武器号** ⇒ **所以"空手"= 拳头武器的索引**。

## 三、**`a <weapon>` 是唯一告知通道**（本组第二重要）

### 3.1 那段

```php
// HOW THE CLIENT IS TOLD. The current weapon is not a playerstate netfield on
// this build, so it never rides the snapshot -- the server has to SAY it, with
// the reliable command `a <weaponAssetIndex>`.
//
// MEASURED in C-2021-7-25[22-23-22]dmz: `a` fires at spawn and again inside
// every cursorHint window where the player takes something, and three of its
// six values (1184, 1193, 1186) are entries of that match's OWN loot band
// (cs 12506..12692, 1148..1211). The other three sit just above the band, which
// is what a freshly registered modular variant of a looted gun would look like.
// Its values are always >= firstDynamicWeapon; the `w` command's are always
// small and static, so `w` is something else.
```

### 3.2 二十层

```text
1. **客户端【如何被告知**】**
2. ⇒ **当前武器在这个 build 上【不是一个 playerstate netfield**】**
3. ⇒ **⇒ 所以【它永不骑在快照上**】**
4. ⇒ **⇒ 服务器必须【说**】它，用可靠命令 `a <weaponAssetIndex>`**
5. ⇒ **在 `C-2021-7-25[22-23-22]dmz` 上测量**：
6. ⇒ **`a` 【在出生时触发**】**
7. ⇒ **并在【每一个玩家拿走东西的 `cursorHint` 窗口里】再次触发**
8. ⇒ **而它的六个值里的三个（`1184`、`1193`、`1186`）是【那场比赛自己的 loot 带的条目**】**
9. ⇒ **（`cs 12506..12692`，`1148..1211`）**
10. ⇒ **另外三个【坐在带的正上方**】**
11. ⇒ **⇒ 那正是【一把刚被注册的、掉落枪械的模块化变体**】会看起来的样子**
12. ⇒ **它的值【总是 `>= firstDynamicWeapon`**】**
13. ⇒ **而 `w` 命令的值【总是小且静态**】**
14. ⇒ **⇒ 所以【`w` 是别的什么**】**
```

### 3.3 ⭐⭐⭐ **"三个在带内、三个在带正上方"**

**✅ 这是本报告里**最重要的一条"值域分布推理"**。**

**⇒ 三层**：
```text
loot 带：`1148..1211`（`cs 12506..12692`）
三个值：`1184`/`1193`/`1186` ⇒ **在带内** ⇒ **一个现有条目**
另外三个 ⇒ **在带正上方** ⇒ **一个新注册的变体**
⇒ **⇒ 所以【`a` 的值域 = "loot 带 + 它的扩展**】**
```

**✅ 与 §420 的"`n 89` 的 `10:10` 计数"**同族（**第三次"值域/计数决定语义"）。

**⇒ 三层**：
```text
§420  **计数 `10:10`** ⇒ `n 89` 是事件
§421  **值域在 `1148..1211` 及其上方** ⇒ `a` 是一个 loot 武器号
⇒ **⇒ 两次"分布定语义**】
```

**✅ ⭐⭐ **一个"分布定语义"的两例**。

**⚠ 而"`a` 与 `w` 的区别"⇒ **`a` 的值 `>= firstDynamicWeapon`，`w` 的值小且静态**。**

**⇒ 三层**：
```text
`a <n>` ⇒ **`n >= 1147`**（动态武器）
`w <slot> <row> <dur>` ⇒ **`slot` 小、`row` 静态**（**§410 的 `w 0 <row> 0` 与 §407 的 `w 2 4 0`**）
⇒ **⇒ 两个完全不同的参数空间**
```

**✅ ⭐⭐ **"`w` 是别的什么"** —— 与 §410 的"`w 0 <row> 0` 是奖章"和 §407 的"`w 2 4 0` 是横幅/语音手势"**完全闭合** ✓

## 四、**`ActorRoute` 的四十个字段**（本组第三重要）

### 4.1 分类

```text
路由核心：nodes / cursor / plannedAtMilliseconds / destination / planned
捷径（shortcut）：shortcutChecks / shortcutAccepted / lastShortcutAt
直追（directPursuit）：target / player / checkedAt / clear / checks / accepted
前瞻（lookahead）：target / area / direction / lastNode / checkedAt / cursor / clear
屏障（barrier）：spawnBarrier / spawnBarrierResolved / spawnBarrierPassed
窗口穿越（windowTraverse）：active / landing / negotiationActive / negotiationCompleted
                        / negotiationStartedAt / negotiationOffset / startedAt
                        / start / end / endNode / anim / variant / yaw
碰撞：fullNavigationBounds / wallFollowWaypoint / wallFollowSign / previousNode
封边：blockedEdges / blockedCandidate / blockedCandidateSince
     / blockedCandidateDistance
```

**⇒ 约 `40` 个字段，分成九组。**

### 4.2 ⭐⭐ **"碰撞体从紧凑探针提升为与玩家同尺寸的胶囊，且【永不降级】"**

```php
// Spawn closets and the authored receiver-window mantle need the
// compact route probe: their static collision intentionally overlaps
// the actor while it is outside the playable space. Once the actor
// has reached ordinary map space, promote it exactly once to the same
// player-sized horizontal capsule used by its linked collision body.
// Never demote it again after promotion; doing so would let an actor
// that entered a wall resume moving through it.
bool fullNavigationBounds{};
```

**⇒ 十二层**：
```text
1. **出生壁橱与作者编写的接收窗攀爬需要【紧凑的路由探针**】**
2. ⇒ **因为**它们的静态碰撞【故意重叠**】actor，当它在可玩空间之外时**
3. ⇒ **一旦 actor 到达【普通地图空间**】**
4. ⇒ **把它【恰好一次**】提升为【与其链接碰撞体相同的、玩家尺寸的水平胶囊**】**
5. ⇒ **⇒ 【在提升之后【永不**】再降级**】**
6. ⇒ **否则会让一个【已经进入墙里的**】actor【恢复穿墙移动**】**
```

### 4.3 ⭐⭐⭐ **"永不降级，否则一个已经进入墙里的 actor 会恢复穿墙"**

**✅ 这是本报告里**最重要的一条单向状态机**。**

**⇒ 三层**：
```text
升：紧凑探针（出生壁橱）→ 玩家胶囊（地图空间）⇒ **一次**
降：**永不** ⇒ **因为降级会让一个已经在墙里的 actor 合法地穿出去**
⇒ **⇒ 所以【这是一个【单向**】状态】
```

**✅ 与 §418 的"`initialized = (tag != 0) || !emptyTag` 的三态"**不同（那是**一个终态**，这是**一个单向迁移**）。

**⇒ 三层**：
```text
§416  `perkHudVisible` **恒真**（玩家接受）
§418  `livingWeaponRightTagInitialized_` **三态**
§421  `fullNavigationBounds` **单向提升**
⇒ **⇒ 三次"不可逆状态**】
```

**✅ ⭐⭐ **一个"不可逆"的三例表**。

### 4.4 而**"走廊绕过一个世界刷子时，把选边【保留】给这个路点"**

```php
// A sparse graph edge can describe a corridor that bends around a
// world brush.  Once collision chooses a side of that brush, retain
// the choice for this waypoint. Recomputing it from the shrinking
// node vector every frame flips the tangent at the node's Y value and
// leaves the actor oscillating at the wall instead of rounding it.
std::optional<std::uint16_t> wallFollowWaypoint;
std::int8_t wallFollowSign{};
```

**⇒ 十二层**：
```text
1. **一个稀疏图边可以描述一条【绕过一个世界刷子弯曲**】的走廊**
2. ⇒ **一旦碰撞【选了那个刷子的一边**】**
3. ⇒ **把那个选择【保留给这个路点**】**
4. ⇒ **在每帧从一个收缩的节点向量里重算它【会在节点的 Y 值处翻转切线**】**
5. ⇒ **⇒ 而【让 actor 在墙边振荡而不是绕过它**】**
```

### 4.5 ⭐⭐⭐ **"每帧重算会在 Y 值处翻转切线"**

**✅ 这是本报告里**最重要的一条"振荡的机制解释**。**

**⇒ 三层**：
```text
原因：**`wallFollowSign` 每帧从收缩的节点向量重算**
后果：**在某个临界点符号翻转** ⇒ **切线反转** ⇒ **振荡**
⇒ **⇒ 所以【一个"瞬时决策"必须被【锁定**】】
```

**✅ 与 §421 四.3 的"单向提升"**同族（**第二次"锁定一个决策"）。

**⇒ 三层**：
```text
§421 四.3  `fullNavigationBounds` ⇒ **永不降级**
§421 四.4  `wallFollowWaypoint`/`wallFollowSign` ⇒ **保留给这个路点**
§421 四.6  `blockedCandidateDistance` ⇒ **不能只靠横向移动清计时**
⇒ **⇒ 三次"锁定一个瞬时决策**】
```

**✅ ⭐⭐ **一个"锁定瞬时决策"的三例**。

### 4.6 而**"`blockedCandidate` 的"横向移动不能清计时"**

```php
// A partial trace is only proof of a bad inferred edge when the
// actor is no longer getting closer to its waypoint.  Lateral wall
// motion alone must not clear the timer: that was the endless
// wall-hugging failure this state is meant to detect.
float blockedCandidateDistance{};
```

**⇒ 八层**：
```text
1. **一个部分 trace 只有在【actor 不再靠近它的路点**】时**
2. ⇒ **才是【一条坏的推断边**】的证据**
3. ⇒ **【只有横向的贴墙运动】不能清掉计时器**】
4. ⇒ **⇒ 那正是【这个状态要检测的【无休止贴墙**】故障】
```

**✅ ⭐⭐ **"横向运动不代表进展"** —— 一个**极精确的判据**。

**✅ 与 §419 的"`2→1` 而玩家在 `71`"**不同（这是**一个"什么算进展"的定义**）。

## 五、**`RealiableCommandSender` 与"世界只知道事实"**

```php
using ReliableCommandSender =
    std::function<bool(std::uint32_t, const std::string &)>;
void setReliableCommandSender(ReliableCommandSender sender);
```

**⇒ 四层**：
```text
1. **世界层【不知道命令文本**】**
2. ⇒ **它只调用一个注入的 sender**
3. ⇒ **⇒ 所以【命令格式的知识在【调用方**】**
4. ⇒ **⇒ 一个"关注点分离"的实例**
```

**✅ 与 §413 的"`a` 的发送路径有 5 个发射点"**——**所以命令构造在 `ServerCore`，而世界只发。**

**⇒ 三层**：
```text
`SvServerWorld` ⇒ **状态和事实**（`givePlayerWeapon`）
`ServerCore` ⇒ **命令文本**（`a <n>`）
⇒ **⇒ 所以【"给武器"与"告知客户端"是两件事**】
```

**✅ ⭐⭐ **一个"事实与呈现分离"的实例**。

**⚠ 而"`a` 的命令在 `sv_main_mp.cpp` 的 `A_RESEND|` 里"**（§413）⇒ **与这里的世界层 `givePlayerWeapon` 是两条路径**。

**⇒ 三层**：
```text
路径 A：**`ServerCore` 的 `loadoutSequence` 变 ⇒ 发 `a`**（§413 的 `A_RESEND|`）
路径 B：**`givePlayerWeapon` 通过 `ReliableCommandSender` 发 `a`**
⇒ **⇒ 所以【两条 `a` 的发送路径**】
```

**✅ 一个**需要注意的重复**（§413 的"5 个发射点"）。

## 六、**`spawnScriptModel` 的"一个 mutator 不是一个构造函数"**

```php
// CREATE A SCRIPT MODEL THAT THE MAP DOES NOT CONTAIN. The loot primitive.
//
// setScriptModelPresentation is a MUTATOR, not a constructor: it requires
// eType == EntityTypeScriptMover and a non-zero modelIndex before it will
// touch an entity, which is exactly right for moving one of the map's own
// script models and useless for making a new one. spawnEntity() hands back a
// blank slot -- eType 0, no model, gameplayActive false -- so the two do not
// compose, and every loot spawn failed on that gap.
//
// Modelled on spawnPodiumFigure, which is the only other place this server
// creates a script mover from nothing, and which documents the trap: an entity
// is filtered out of the snapshot before publication unless gameplayActive is
// set, and the staging pass that sets it for MAP script models runs on mode
// changes, so an entity created mid-match is never staged and never drawn.
//
// SCENERY, NOT AN OBSTACLE. Collision is deliberately left unlinked with the
// default capsule, so loot cannot become an invisible wall. Pickup will need a
// linked volume; that belongs with the touch wiring, not here.
```

### 6.1 二十层

```text
1. **创建一个地图【不包含**】的 script model —— 拾取原语**
2. ⇒ **`setScriptModelPresentation` 是一个【mutator 不是一个 constructor**】**
3. ⇒ **它要求 `eType == EntityTypeScriptMover` 与一个【非零 `modelIndex`**】**
4. ⇒ **⇒ 那对【移动地图自己的一个 script model】【恰好正确**】**
5. ⇒ **⇒ 而对【制造一个新的**】【无用**】**
6. ⇒ **`spawnEntity()` 交回一个【空白槽**】**
7. ⇒ **（`eType 0`、无模型、`gameplayActive = false`）**
8. ⇒ **⇒ 所以【两者【不能合成**】】**
9. ⇒ **而【每一次 loot 生成都在那个缺口上失败**】**
10. ⇒ **仿照 `spawnPodiumFigure`**
11. ⇒ **它是这个服务器【从无到有**】创建 script mover 的【唯一另一个地方**】**
12. ⇒ **而它记录那个陷阱**：
      · **一个实体【被过滤出快照**】除非 `gameplayActive` 被设**
      · **而为地图 script model 设置它的 staging pass【在模式变化时跑**】**
      · **⇒ 所以一个【在比赛中途创建**】的实体【永远不会被 staging**】** ⇒ **永远不画**
13. ⇒ **⚠ 场景，不是一个障碍** ⇒ **碰撞【故意不链接**】**
14. ⇒ **⇒ 所以【loot 不能变成一堵看不见的墙**】**
15. ⇒ **拾取【将需要一个链接的体积**】⇒ **那属于触控接线，不属于这里**
```

### 6.2 ⭐⭐⭐ **"两者不能合成，而每一次 loot 生成都在那个缺口上失败"**

**✅ 这是本报告里**最重要的一条"两个正确的东西不能组合"**。**

**⇒ 三层**：
```text
`setScriptModelPresentation` ⇒ **只对已存在的 scriptmover 有效** ⇒ 正确
`spawnEntity()` ⇒ **交回一个空白槽** ⇒ 正确
组合 ⇒ **失败**（**空白槽不满足 mutator 的前置条件**）
⇒ **⇒ 所以【需要一个【constructor**】】
```

**✅ 与 §409 的"一个 HUD 需要身体，不是什么先解出就用什么"**同族（**第六次"两个正确的东西不匹配"）。

**⇒ 三层**：
```text
§409  `hea_` 是一个正确的模型【但不是身体】
§421  `spawnEntity` + `setPresentation` 各自正确【但不能组合】
⇒ **⇒ 两次"组成部分正确而组合错误**】
```

**✅ ⭐⭐ **一个"组合失败"的两例**。

**⚠ 而"`gameplayActive` 的 staging 在模式变化时跑"⇒ **一个"中途创建永远不会被 stage"的陷阱**。**

**⇒ 三层**：
```text
地图加载时 ⇒ **staging pass 跑 ⇒ `gameplayActive` 被设**
比赛中途 ⇒ **staging pass 【不跑**】 ⇒ **永远不画**
⇒ **⇒ 所以【一个中途创建的实体必须自己设 `gameplayActive`**】
```

**✅ ⭐⭐ **一个"时序依赖"的陷阱**。

## 七、`spawnPodiumCamera` 与"零售的相机是一个地图 scriptmover"

```php
// The outro CAMERA as an ENTITY (HANDOFF 129). Retail's is a map
// scriptmover that has existed since map load and simply starts moving
// at match-end +16950; this server has no such entity, so it spawns one
// on the map's own `top_players_camera` and hands every player's view
// to it. The hidden tag carrier supplies the DObj the client requires
// to resolve the playerState camera tag.
```

**⇒ 十层**：
```text
1. **outro 相机【作为一个实体**】**
2. ⇒ **零售的【是一个地图 scriptmover**】**
3. ⇒ **它【从地图加载起就存在**】**
4. ⇒ **而【只是在 `match-end +16950` 开始移动**】**
5. ⇒ **而这个服务器【没有这样一个实体**】**
6. ⇒ **⇒ 所以它【在比赛末生成一个**】**
7. ⇒ **在【地图自己的 `top_players_camera` 上**】**
8. ⇒ **并把【每一个玩家的视图】交给它**
9. ⇒ **而那个隐藏的 tag 载体【提供客户端解析 `playerState` 相机 tag 所需的 DObj**】**
10. ⇒ **⇒ 所以【三件事：实体 + 位置 + tag 载体**】
```

**✅ ⭐⭐ **"零售的不需要生成，因为它从地图加载起就存在"** —— 一个**架构差异**。

**⇒ 三层**：
```text
零售：**地图自带 ⇒ 直接移动**
我们：**地图没有 ⇒ 生成一个替身**
⇒ **⇒ 所以【同一行为两条实现**】
```

**✅ 与 §408 的"`_tp` 调色在地图自己的 fastfile"**同族（**第三次"地图自带 vs 我们补**）。

## 八、关键结论

1. **⭐⭐⭐ "原生 pmove 删掉一个玩家没被正确给予的武器：`weapon ACROSS PMOVE before=1137 after=0` 在第一帧上，`heldWeapons` 随之被清空"** ⇒ **所以一个授予被记录为【服务器拥有的状态】并在每次 pmove 之后重新断言** —— 第四次"引擎的权威不可绕过"。
2. **⭐⭐ "这里没有任何东西能做原生给予"`** —— 一个诚实的边界。
3. **⭐⭐⭐ "世界从 pmove 重建每个客户端的 `playerState`，所以一次单写会在下一帧被覆写"`** ⇒ **所有"持续状态"（`noclip`、武器授予、`matchEndFreeze`）必须在 pmove 之前每帧重新应用** —— 一个**架构事实的两次应用**。
4. **⭐ "空手就是玩家开始时的那个授予"`** —— 与 §413 的"空手出生 ⇒ `viewmodelIndex = 0` ⇒ AV"**不矛盾**：**"空手"有两种，一种有武器号（拳头）一种没有（`no loadout`）**。
5. **⭐⭐⭐ "当前武器在这个 build 上不是一个 playerstate netfield，所以它永不骑在快照上 —— 服务器必须【说】它，用可靠命令 `a <weaponAssetIndex>`"`**。
6. **⭐⭐⭐ `a` 的值域分布**：**六个值里三个（`1184`/`1193`/`1186`）在 `loot 带（`1148..1211`，`cs 12506..12692`）内，另外三个在带的正上方（"一把刚被注册的掉落枪械模块化变体"）** ⇒ **`a` 的值总是 `>= firstDynamicWeapon`，而 `w` 总是小且静态** —— 第三次"分布定语义"，与 §410 的 `w 0 <row> 0` 和 §407 的 `w 2 4 0` 闭合。
7. **⭐⭐⭐ `ActorRoute` 约 `40` 个字段分九组**（路由核心 / 捷径 / 直追 / 前瞻 / 屏障 / 窗口穿越 / 碰撞 / 封边）。
8. **⭐⭐⭐ "紧凑探针 → 玩家胶囊【恰好一次提升】，之后【永不降级】，否则会让一个已经进入墙里的 actor 恢复穿墙"`** —— 第三次"不可逆状态"。
9. **⭐⭐⭐ "每帧从一个收缩的节点向量里重算 `wallFollowSign` 会在节点的 Y 值处翻转切线，让 actor 在墙边振荡而不是绕过它"`** ⇒ **一个瞬时决策必须被锁定到这个路点** —— 第三次"锁定瞬时决策"。
10. **⭐⭐ "一个部分 trace 只有在 actor 不再靠近它的路点时才是坏边的证据；只有横向的贴墙运动不能清计时器，那正是这个状态要检测的无休止贴墙故障"`** —— 一个"什么算进展"的精确判据。
11. **⭐ `ReliableCommandSender` 的注入 ⇒ 世界层不知道命令文本** ⇒ **"给武器"与"告知客户端"是两件事**；而 **`a` 有两条发送路径**（`ServerCore` 的 `A_RESEND|` 与世界的 `givePlayerWeapon`）。
12. **⭐⭐⭐ `spawnScriptModel` 的"两个正确的东西不能组合"**：`setScriptModelPresentation` 是 **mutator**（要求 `eType == 6` 与非零 `modelIndex`），`spawnEntity()` 交回**空白槽**（`eType 0`）⇒ **每次 loot 生成都在那个缺口上失败**。
13. **⭐⭐ `gameplayActive` 的 staging pass 只在【模式变化】时跑 ⇒ 一个中途创建的实体永不被 stage ⇒ 永远不画** —— 一个时序陷阱。
14. **⭐ "SCENERY, NOT AN OBSTACLE：碰撞故意不链接，所以 loot 不能变成一堵看不见的墙"`**。
15. **⭐⭐ `spawnPodiumCamera` 的"零售的从地图加载起就存在，而我们必须生成一个替身"`** —— 第三次"地图自带 vs 我们补"。

## 九、未闭合点

- `1137` 与 `1147`（`firstDynamicWeapon`）的关系。
- `SvClientSpawnConfig::unarmed` 与 `unarmedWeaponAssetIndex` 的具体值。
- `a` 的两条发送路径是否有冲突。
- `ActorRoute` 的 `SvZmAreaLookahead` 结构。
- `spawnGroundTiltController` 的 `playerState` 字段 `231`。
- `sv_snapshot_mp.hpp` 3620 行之后未读取（**共 `4703` 行**）。
