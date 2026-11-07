# 489 · **"那个 demo 给对了**形状**而给错了**数字**"** —— `sv_entity_mp.hpp` 的 `19..36` 十八条尸体环、`trType 13` 的 `Com_Error`、以及"把 `0x200000` 读成尸体位是一次误归属"

## 一、范围

本报告学习 `sv_entity_mp.hpp`（**`297` 行**）全文件：`EntityNumWorld/None` 两个哨兵、`FirstDynamicServerEntityNum = 37`、`SvCorpseReinitialiseFlag = 0x80000`、`SvDeadPlayerHiddenFlag = 0x20000`、`SvCorpseSettleRespawnSeparationMs` 与它的 `static_assert`、`PlayerCorpseRingSize = 18` 与它的 `static_assert`、以及 `SvEntityPool` 的 `reserve`/`spawnAt`/`rollbackFree`。

## 二、**"那个 demo 给对了形状而给错了数字"**（本组最重要的一段）

### 2.1 那段

```cpp
// A corpse spawns with trType 1 and holds it while the body settles, then is
// handed to the ragdoll on BOTH trajectories - the shape is measured off the
// dm demo (slot 20 spawns at t=216700 and ragdolls at t=217700).
//
// The demo's ragdoll VALUE is 13 and that value DOES NOT EXIST IN THIS
// BUILD. CODREF(bg_evaluate_trajectory) sub_AB29C0 switches on trType and
// handles only 0..12; everything else falls to
//     Com_Error(2, "90 %i", trType)
// which is the error dialog a live client raised on the first kill after
// 13 was sent. Sending a demo constant straight across builds is exactly
// the trap this project keeps hitting: the demo gave the SHAPE correctly
// and the NUMBER wrongly.
```

### 2.2 二十四层

```text
1. **形状【是从 dm demo **测量的**】（**slot `20` 在 `t=216700` 生成，`t=217700` 变 ragdoll**）**
2. ⇒ **⇒ 而那个 demo 的 ragdoll **值**是 `13`**】
3. ⇒ **⇒ ⚠ 而那个值【在这个 build 上【**不存在**】
4. ⇒ **⇒ 因为 `sub_AB29C0` 【只处理 `0..12`**】
5. ⇒ **⇒ 而【其余一切【落到 `Com_Error(2, "90 %i", trType)`**】
6. ⇒ **⇒ 而那【正是【那个**错误对话框**】（**一个活的客户端【在【`13` 被发出后的【第一次击杀【上【弹出**）**
7. ⇒ **⇒ 所以【把一个 demo 常量【直接**跨 build** 搬运【正是【这个项目【反复**踩到**的陷阱**】
8. ⇒ **⇒ ⇒ 那个 demo 【给对了【那个**形状**】而【给错了【那个**数字**
```

### 2.3 ⭐⭐⭐ **"那个 demo 给对了形状而给错了数字"**

**✅ 这是本报告里**最重要的一条"**一个**测量的参照【的【两个成分【可靠性不同**"**。**

**✅ 与 §487 的"骨骼名字是槽位"**、§476 的"§51i 的 FOREIGN 被推翻"**——**同族** ✓

**⇒ 三层**：
```text
形状 ⇒ **"先 trType 1 保持，然后变 ragdoll"** ⇒ **⇒ 一个**结构的**事实**（**跨 build 稳定**）
数字 ⇒ **`13`** ⇒ **⇒ 一个**枚举的**成员**（**每个 build 不同**）
⇒ **⇒ 所以【同一个 demo 【的两个结论【可靠性【不同**】
```

**✅ ⭐⭐⭐ **"同一个 demo 的两个结论可靠性不同"** —— 一个**极精确的分层**。

**✅ 与 §479 的"`29,013` / `48,522` 是无向对"**——**同族**（**第二次"一个**测量的**语义【需要**解释**"**）。

**⚠ 而 `9` 是**这个 build 的** ragdoll**】**。**

**⇒ 十六层**：
```text
`sub_AB29C0` 的 `switch` 【把 `case 9` 【与 `0`/`1`/`12` 分组**】⇒ **⇒ "保持那个位置**"**
⇒ **⇒ 而那【正是【一个**客户端模拟的** ragdoll 【需要的】
⇒ **⇒ 而 IW3 【把 `9` 命名【为 `TR_RAGDOLL` / `TR_FIRST_RAGDOLL`**】
⇒ **⇒ 而 `10` 【是 `TR_RAGDOLL_GRAVITY`**】⇒ **⇒ 那个 demo 与它配对的那个 `apos` 值**】
⇒ **⇒ 而这个 build 的 `switch` **确实接受它** ⇒ **⇒ 所以 `aprType 10` 【从来【没报错**】
```

**✅ ⭐⭐⭐ **"`aprType 10` 从来没报错"** —— 一个**反向的验证**（**那个 `10` 一直在工作**）。

**✅ 与 §471 的"打不死人 + 穿透仍无效是同一刀的两个症状"**——**同族**（**第三次"一个**部分的成功【掩盖【一个**整体的错**"**）。

## 三、**`0x80000` vs `0x200000` 的误归属**（本组第二重要）

### 3.1 那段

```cpp
// TWO earlier conclusions were wrong and are corrected here.
//
// The gate is 0x80000, NOT 0x200000. There is no two-bit shift for this
// flag. The 0x200000 test at ida 0x00BB86BD is an unrelated flag inside
// sub_BB8050, and reading it as the corpse bit was a misattribution - which
// also means the dm demo's 0xA0206 was right all along and "correcting" it
// to 0x280000 broke a working value.
```

### 3.2 二十四层

```text
1. **两个**早期的结论【是错的**】
2. ⇒ **⇒ 那个门【是 `0x80000`，**不是 `0x200000`**】
3. ⇒ **⇒ 而【那个标志【没有【一个**两位的**移位**】
4. ⇒ **⇒ 而 `0x00BB86BD` 的 `0x200000` 测试【是【`sub_BB8050` 里的【一个**无关的**标志**】
5. ⇒ **⇒ 而【把它【读成【那个尸体位【是【一次**误归属**】
6. ⇒ **⇒ ⇒ 而那【也【意味着【那个 dm demo 的 `0xA0206` 【一直【是对的**】
7. ⇒ **⇒ 而【"更正"它到 `0x280000` 【破坏了【一个**能工作的**值**】
```

### 3.3 ⭐⭐⭐ **"把它读成那个尸体位是一次误归属"**

**✅ 与 §476 的"§51i 把它们记成 FOREIGN"**、§482 的"§49 的那个推断是错的"**——**完全同族** ✓

**⇒ 三层**：
```text
§471  **§79g 数错了对象**
§476  **§51i 的 FOREIGN 被镜像推翻**
§482  **§49 的"因此一个不同的行布局"**
§489  **`0x200000` 的误归属**
⇒ **⇒ **四次**"一个**早期的结论【被【一个更精确的**读法推翻**"**
```

**✅ ⭐⭐⭐ **"一个早期的结论被一个更精确的读法推翻"四例表**。

**⚠ 而"那个 `0x280000` 的『更正』破坏了一个能工作的值"**⇒ **一个**最严重的**后果**。**

**⇒ 十层**：
```text
`0xA0206` ⇒ **那个 demo 的值**（**一直【是对的**）
"更正" ⇒ **`0x280000`**（**而【那是 `0x200000 | 0x80000`**）
⇒ **⇒ 所以【那个"更正"【把【两个位**组合**【起来**】⇒ **⇒ 而【它【破坏了【一个**能工作的**值**】
```

**✅ ⭐⭐⭐ **"那个『更正』把两个位组合起来，而它破坏了一个能工作的值"** —— 一个**极精确的因果**。

**✅ 与 §483 的"`0x2800 = 0x2000 | 0x800`"**——**同族**（**第二次"一个**两个位的**组合**"**）。

**⚠ 而"`SvCorpseSpawnFlags = 0xA0000`"**⇒ **`0xA0000 = 0x80000 | 0x20000`**。】

**⇒ 独立验证**：
```text
`0xA0000` = `0x80000 | 0x20000` ✓
⇒ **⇒ 所以【那个生成的标志【是【两个**位的组合**】（**重初始化 + 死亡隐藏**）
```

**✅ ⭐⭐⭐ **"那个生成的标志是两个位的组合（重初始化 + 死亡隐藏）"**。

## 四、**`PlayerCorpseRingSize = 18` 的四条独立推导**（本组第三重要）

### 4.1 那四条（对 3.3.3.3）

```text
① 客户端 corpseinfo 边界：`sub_BBAD90` case 2 与 `sub_BBB3F0`（`imul ecx, 3B8h`）
   都是 `cgs + 1455144 + 952 * es.number`；号 19..26 的记录跨 `cgs+0x167AD0..0x169890`，
   而 `cgs+0x169890` 是那个镜像里下一个被引用的全局（15 个 xref）⇒ 那个数组恰好持 8 个
② 嵌入服务器的尸体池：`G_RunCorpseAnimate 0x004E8460` 线性搜索，基 `0xBC22708`，
   步长 1016，边界 `0xBC246C8`；`0x1FC0 / 1016 == 8`
③ 客户端字面量：`sub_BA6A80` 分支在 `es.number < 19`
④ 零售流量：dm demo 的尸体是 19..24（死亡顺序）
⇒ 而 `19 + 8 == 27` 闭合那个算术
```

### 4.2 而**本 build 的 18 来自零售流量的离线解码**

```cpp
// MEASURED on this build's own retail traffic, offline, 6160/6160
// snapshots decoded with no desync (CODOL-main Tools/demo-re):
//
//     ET_PLAYER          1..8      the eight players in that match
//     ET_PLAYER_CORPSE   19..36    CONTIGUOUS, 18 distinct numbers
//     everything else    37..750   and the LOWEST of them is exactly 37
```

**⇒ 二十四层**：
```text
1. **`6160` 个里的 `6160` 个快照【解码【零失步**】
2. ⇒ **⇒ `ET_PLAYER` ⇒ `1..8`**（**那场比赛的**八个玩家**）
3. ⇒ **⇒ `ET_PLAYER_CORPSE` ⇒ `19..36`（**连续，`18` 个不同的号**）**
4. ⇒ **⇒ 其余 ⇒ `37..750`**】⇒ **⇒ 而【它们里【最低**的【恰好是 `37`**】
5. ⇒ **⇒ 所以【`19 + 18 == 37` 【恰好**闭合**那个到动态区的**间隙**】
```

### 4.3 ⭐⭐⭐ **"6160 个里的 6160 个快照解码零失步"**

**✅ 与 §468 的"`81,128/81,128` 零失配"**、§482 的"`consumed 22940 of 22940 bytes EXACT`"**——**完全同族** ✓

**⇒ 三层**：
```text
§468  **`81,128/81,128`**（**哈希**）
§482  **`22940/22940`**（**一个 zone 流**）
§489  **`6160/6160` 快照【零失步**】
⇒ **⇒ **三次**"一个**完全**的计数【是【一个**可判定的正确性**"**
```

**✅ ⭐⭐⭐ **"一个完全的计数是唯一的可判定的正确性"三例**。

**⚠ 而"那个 `18` 也【正是【这个 build 的客户端槽数**"**】**。**

**⇒ 十层**：
```text
`PlayerCorpseRingSize = 18`
`EngineBindings.hpp` 的 `ServerCharacterInfoSlotCount` ⇒ **`18`**
`0xAF350 + 18 * 0x450` ⇒ **`18`**
那个大厅报告的房间容量 ⇒ **`18`**
⇒ **⇒ 所以【四个**独立**的地方【都是 `18`**】
```

**✅ ⭐⭐⭐ **"四个独立的地方都是 18"** —— 与 §469/§472/§477 的 `MaximumGameClients = 18` **完全闭合** ✓

**✅ 而"那个 `37` 是 `19 + 18`"**⇒ **一个**算术**的闭合**。**

**⚠ 而**那四条 3.3.3.3 的推导【在本 build 上【没有被重跑**】**。**

**⇒ 十二层**：
```cpp
// The four derivations above it are 3.3.3.3's and were never re-run here:
// out.exe's 0x004E8460 is a dvar registration, not G_RunCorpseAnimate, so
// the corpseinfo bound, the pool stride and the `es.number < 19` literal
// are all unchecked on this build. The demo needs none of them.
```
```text
1. **那四条【是 3.3.3.3 的**】而【从未【在这里【被【重跑**】
2. ⇒ **⇒ 因为 `out.exe` 的 `0x004E8460` 【是一个 dvar 注册**】⇒ **⇒ 不是** `G_RunCorpseAnimate`
3. ⇒ **⇒ 所以【那个 corpseinfo 边界 / 池步长 / `es.number < 19` 字面量【全部【**未检查**】
4. ⇒ **⇒ 而那个 demo 【不需要**它们里的任何一个**
```

**✅ ⭐⭐⭐ **"那个 demo 不需要它们里的任何一个"** —— 一个**极诚实的标注**。

**✅ 与 §473 的"注释本身说是候选"**——**同族**（**第三次"一个**显式的**未验证**声明**"**）。

### 4.4 而**"带着那个 8 的代价"**

```cpp
// What the carried 8 cost: this server would hand a DYNAMIC entity number
// 27..36, which the client stores as a CORPSE -- sub_BB9EE0 indexes
// corpseinfo by the entity number with no subtraction and no bounds check
// -- and it would recycle corpse slots after eight bodies where retail
// uses eighteen.
```

**⇒ 十六层**：
```text
1. **带着那个 `8` 的代价**【是【那个服务器【会【把一个**动态**实体号【发【成 `27..36`**】
2. ⇒ **⇒ 而【客户端【把它【存成【一个**尸体**】
3. ⇒ **⇒ 因为 `sub_BB9EE0` 【按实体号索引** corpseinfo**】⇒ **⇒ 而【**没有任何减法**】
4. ⇒ **⇒ 而【**没有任何边界检查**】
5. ⇒ **⇒ ⇒ 所以【一个动态实体【会【写进【那个尸体数组**】（**⇒ 越界**）
```

**✅ ⭐⭐⭐ **"一个动态实体会写进那个尸体数组，没有任何边界检查"** —— 一个**具体的**越界**。

**✅ 与 §480 的"`entityNum` 的 `824..1776`"**——**不同**（那是一个**间隔**，这是一个**语义重叠**）但**同族**（**第四次"一个**值域【的**语义**"**）。

**⚠ 而"`sub_BB9EE0` 用 `globals + 952 * entityState->number + 639904`"**⇒ **一个**无减法的**索引**。】

**⇒ 十层**：
```text
`952 * number + 639904` ⇒ **⇒ 对【号 `19` ⇒ `19 × 952 = 18088`**】
⇒ **⇒ 所以【那个数组【从【号 `19` 【开始**】⇒ **⇒ 而【号 `27..36` 【会【落在【那个数组的【第 `8..17` 项**】
⇒ **⇒ 而那【是【一个**合法的写入**】（**但【语义上【错**）
```

**✅ ⭐⭐⭐ **"那是一个合法的写入，但语义上错"** —— 一个**最隐蔽的**类型**。**

**✅ 与 §481 的"那个武器索引走进了一个事件字段"**——**完全同族** ✓

**⇒ 三层**：
```text
§481  **一个武器索引【走进【一个事件字段**】⇒ **⇒ 每帧发事件**
§489  **一个动态实体号【走进【一个尸体槽**】⇒ **⇒ 一个**合法的**越界写**
⇒ **⇒ 两次"一个**错的值【在【一个错的**语义【上【但【仍然**合法**"**
```

**✅ ⭐⭐⭐ **"一个错的值在一个错的语义上但仍然合法"两例**。

## 五、**那个 `SvCorpseSettleRespawnSeparationMs` 的五步链**（本组第四重要）

### 5.1 那五步

```text
1. respawnTime     = serverTime + max(deathAnimMs, 1)
   clearReinitTime = serverTime + max(deathAnimMs, 50)
   ⇒ 两个表达式【几乎**相同**】⇒ **⇒ 所以【两者【在【同一个服务器帧**上触发**
2. 那一帧【客户端【更新【那个重生的玩家的 clientInfo】
   CG_UpdateCharacterModelsFromClientInfo 0x0051BC80 【在 modelIndex 为零时【**清掉全部十个**模型槽**
3. 那个尸体的 eFlags 【在同一帧【变化**】⇒ **⇒ 重新触发 `CG_ResetEntity` 的 case 2**
   ⇒ **⇒ 它调用 `CG_CopyCorpseInfo`（`sub_BB9F70`）**
   ⇒ **⇒ 而【把【那个**刚被清空**的 clientinfo 【复制进** corpseinfo
4. `BG_UpdatePlayerDObj 0x0040B700` 【开头【是**】
       `if (!valid || !model[0]) ...`
   ⇒ **⇒ 而【在那个分支上【**释放**那个 DObj**
5. 之后【没有东西【再复制** corpseinfo**】（**那个数组【在整个镜像里【只有三个代码引用，全是读/复制路径**）
   ⇒ **⇒ 所以【那个身体【再也【回不来**】
```

### 5.2 二十四层

```text
1. **两个时间【几乎相同**】⇒ **⇒ 同一帧**
2. ⇒ **⇒ 而【那个 clientinfo 被清**】⇒ **⇒ 而【尸体【复制【那个**空的**】**
3. ⇒ **⇒ 而【DObj 【在 `!model[0]` 上【被**释放**】
4. ⇒ **⇒ 而【没有东西【再【复制**】
5. ⇒ **⇒ 所以【那个身体【**永远**【消失**】
```

### 5.3 ⭐⭐⭐ **"零售从不撞上这个"**

**✅ 与 §463 的"一个 bug 只在另一个被修好之后才暴露"**——**不同**（那是一个**时序**的**暴露**，这是一个**时序**的**碰撞**）但**同族**（**第五次"一个**两件事【在【同一帧**"**）。

**⇒ 三层**：
```text
零售 ⇒ **settle 在尸体生成后 `1.4..2.9` 秒**】⇒ **⇒ 而【重生【是【一个**独立的** gametype 计时器**】
⇒ **⇒ 所以【两者【从不【在同一帧**】
⇒ **⇒ 而【这里【两者【用【几乎**相同的**表达式**】
```

**✅ ⭐⭐⭐ **"两者用几乎相同的表达式"** —— 一个**极精确的诊断**。

**⚠ 而"那个 `250ms` 的分离"**⇒ **一个**最小的**偏置**。**

**⇒ 十层**：
```text
`deathAnimMs 1616..1818` ⇒ **加上那个 `250` ⇒ `1.87..2.07` 秒**】
⇒ **⇒ 而【那【保持**在【那个零售的窗口**里】（`1.4..2.9`**）
⇒ **⇒ 而【保证【那个尸体【从不在【一个重生帧【上【被重置**】
```

**✅ ⭐⭐⭐ **"那个偏置保持在零售的窗口里，而保证那个尸体从不在一个重生帧上被重置"** —— 一个**双重满足**。

**✅ 与 §489 四 的"一个恰好用尽"**——**不同**，但与 §475 的"那个 `1.0` 防止一个免费的穿透"**同族**（**第六次"一个**小的数值【满足【两个**约束**"**）。

**⚠ 而那个 `static_assert` 的**理由**】**。**

```cpp
// No server-side test can catch a regression here: the damage is done in the
// CLIENT, which frees the corpse DObj after copying a cleared clientinfo, and
// the server's own snapshot still contains a perfectly valid corpse. So the
// invariant is enforced at compile time instead - zeroing this separation
// silently restores "the body vanishes the moment it settles".
static_assert(SvCorpseSettleRespawnSeparationMs > 0, "...");
```

**⇒ 十六层**：
```text
1. **没有一个服务器侧的测试【能【抓住【这里的【一个回归**】
2. ⇒ **⇒ 因为【那个伤害【是【在**客户端**里【做的**
3. ⇒ **⇒ 而【服务器自己的快照【仍然【含有一个【**完全合法**的**尸体**
4. ⇒ **⇒ 所以【那个不变式【被【在【**编译期**强制**
5. ⇒ **⇒ 而【把它**归零**会【静默地【恢复【"那个身体【在【它沉降的【那一刻【就消失**"**
```

**✅ ⭐⭐⭐ **"服务器自己的快照仍然含有一个完全合法的尸体"** —— 一个**极精确的**不可测**论证**。

**✅ 与 §483 的"那个测试阻止那个修复，而不是验证它"**——**同族**（**第四次"一个**测试【的**边界**"**）。

**✅ 而"`static_assert` 是那个唯一的手段"**⇒ **与 §468 的"`static_assert(sizeof(void*) == 4)`"同族**（**第四次"一个 `static_assert` 是一个行为"**）。

## 六、**`SvEntityPool` 的 `reserve` 与"一个动态实体被交给 42 会继承那个槽的原点、模型与 solid"**（本组第五重要）

### 6.1 那段

```cpp
// TAKE A NUMBER OUT OF SEQUENTIAL ALLOCATION'S REACH.
//
// Retail's static map entities do not occupy a contiguous run: factory's
// are 37, 42..46, 48, 53, 55, 56, 59.. -- and the client resolves
// cl.entityBaselines BY NUMBER (snapshot flag 0x10). A dynamic entity
// handed 42 would inherit that slot's origin, model and solid, so every
// number the map's const-baseline table names has to be withheld from
// spawn() whether or not a static entity is published on it.
//
// Reserved slots stay reachable through spawnAt and never enter the free
// list. Call before the first spawn; reset() clears every reservation.
```

### 6.2 二十四层

```text
1. **零售的静态地图实体【不占【一个**连续**的区间**】
2. ⇒ **⇒ （Factory 的是 `37`, `42..46`, `48`, `53`, `55`, `56`, `59..`**）**
3. ⇒ **⇒ 而【客户端【按**号**【解析** `cl.entityBaselines`】（**快照标志 `0x10`**）**
4. ⇒ **⇒ 所以【一个被交给 `42` 的动态实体【会**继承**【那个槽的原点、模型与 solid**】
5. ⇒ **⇒ 所以【每一个【那个地图的 const 基线表【命名的**号**【都必须【从 `spawn()` 【**扣留**】
6. ⇒ **⇒ 无论【是否【有一个静态实体【被【发布**在它上面**
```

### 6.3 ⭐⭐⭐ **"一个被交给 42 的动态实体会继承那个槽的原点、模型与 solid"**

**✅ 与 §414 的"`SnapshotUseEntityBaselinesFlag = 0x10`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§414  **`0x10` ⇒ 每个字段【等于基线就**不发**】
§489  **而【那个基线【是【按**号**索引的**】⇒ **⇒ 所以【一个**冲突的号**【会【继承**】
⇒ **⇒ 所以【那个 `reserve` 【是【一个**必须的**前置**
```

**✅ ⭐⭐⭐ **"那个 reserve 是一个必须的前置"** —— 一个**极重要的机制**。

**⚠ 而"`spawnAt` 只接受**一个被保留、未使用**的槽"**⇒ **一个**双向**的约束**。**

**⇒ 十层**：
```text
`reserve(n)` ⇒ **⇒ 从 `spawn()` 的序列里【扣留**】⇒ **⇒ 但仍然【可【通过 `spawnAt`** 拿到**
`spawnAt(n)` ⇒ **⇒ 只接受【一个**被保留、未使用**的槽**
⇒ **⇒ 所以【两个函数【是【一对**互补的**】
```

**✅ ⭐⭐⭐ **"两个函数是一对互补的"**。

**✅ 而"取一个任意号【会【让【一个静态实体【落在一个【那个序列分配【已经【许诺给别人的**槽上"**】**。**

**⇒ 三层**：
```text
`spawn()` ⇒ **顺序分配**（**`37`, `38`, ...**）
`spawnAt(n)` ⇒ **一个具体的号**
⇒ **⇒ 而【若 `spawnAt` 接受【一个【未被保留**的号 ⇒ **⇒ 它【会【撞上** `spawn()` 的下一个**
```

**✅ ⭐⭐⭐ **"它会撞上 spawn() 的下一个"**。

### 6.4 而**`rollbackFree` 的"一个前一个生命期"**

**⇒ 十层**：
```cpp
[[nodiscard]] bool rollbackFree(SvEntityHandle handle, const SvEntityLifetime &previousLifetime);
```
```text
1. **那个参数【是 `previousLifetime`**】⇒ **⇒ 所以【它【恢复【一个**之前**的生命期**
2. ⇒ **⇒ 而那【正是【§424 的 `entity free rollback lost FIFO ownership`**】
3. ⇒ **⇒ 所以【`rollbackFree` 【是【那个错误的**一个正确的**替代**
```

**✅ ⭐⭐⭐ **"rollbackFree 是那个错误的一个正确的替代"** —— 一个**跨报告的闭合**。

**✅ 与 §422 的"`0x3FC → 0x3FE`"**——**不同**，但与 §426 的"进入世界的客户端刚刚把它的快照状态扔掉了"**同族**。

**⚠ 而"`expiredEventEntities(serverTime)` 与 `EntityEventLifetimeMilliseconds = 300`"**⇒ **一个**有界的事件**。**

**⇒ 三层**：
```text
`EntityEventLifetimeMilliseconds = 300`
⇒ **⇒ 而 `markFreeAfterEvent(handle, eventTime, otherEntityNum)` ⇒ **⇒ 一个**带超时**的释放**
⇒ **⇒ 而 `expiredEventEntities` 【收集**它们**
```

**✅ ⭐⭐⭐ **"300ms 的事件生命周期"** —— 与 §475 的 `1400ms` 静止展示**同族**（**第七次"一个**超时的**数**"**）。

**✅ 而 `EntityReuseDelayMilliseconds = 500`**⇒ **另一个**时间**。**

**⇒ 十层**：
```text
`EntityReuseDelayMilliseconds = 500` ⇒ **一个槽【在【释放后【`500ms` 内【不可【被【重用**】
`EntityEventLifetimeMilliseconds = 300` ⇒ **一个事件实体【活 `300ms`**
⇒ **⇒ 所以【两个**不同的**时间【各自【一个语义**】
```

**✅ ⭐⭐⭐ **"两个不同的时间各自一个语义"**。

## 七、**`SvDeadPlayerHiddenFlag = 0x20000` 与"那个敌人【就【消失**"** 的**症状**】**

### 7.1 那段

```cpp
// MEASURED on the wire: a live player's entity carries eFlags 2 or 0, a
// dead one carries 0x20002, constant for the full three seconds it stays
// archived. In the client, sub_BB89E0 skips the ENTIRE per-client
// animation-state initialisation - the XAnim setup, the lerp reset and both
// 0x40 memsets - when this bit is set:
//
//     v5 = 952 * centity[99] + base + 1433256;   // per-client anim state
//     if ( (centity[62] & 0x20000) == 0 )        // centity+0xF8 = es.eFlags
//     { ...initialise... }
//
// That is IW's EF_DEAD behaviour: the client stops presenting the player
// entity because the CORPSE is meant to take over, so leaving this bit set
// on the player entity means the player entity itself stops being drawn -
// which is the "enemy just disappears" symptom if no corpse takes over.
```

### 7.2 二十四层

```text
1. **在线上测量**：一个活玩家的实体【携带 `eFlags 2` 或 `0`**】
2. ⇒ **⇒ 而【一个死的【携带 `0x20002`**】⇒ **⇒ 在【它【被归档的**整整三秒**里【恒定**】
3. ⇒ **⇒ 而在客户端【`sub_BB89E0` 【跳过【整个**每客户端的动画状态初始化**】
4. ⇒ **⇒ （`XAnim` 的建立 / `lerp` 的重置 / 两个 `0x40` 的 `memset`**）**
5. ⇒ **⇒ 当【那个位【被设**时】
6. ⇒ **⇒ 那【是 IW 的 `EF_DEAD` 行为**：客户端【停止【呈现【那个玩家实体**】
7. ⇒ **⇒ 因为【那个**尸体**【本应【接管**】
8. ⇒ **⇒ 所以【把【这个位【留在【那个玩家实体上【意味着【那个玩家实体【自己【停止**被画**】
9. ⇒ **⇒ 而那【就是【"**那个敌人【就【消失**"**】的症状**】⇒ **⇒ 若【没有尸体【接管**】
```

### 7.3 ⭐⭐⭐ **"那个敌人就消失"**

**✅ 与 §467 的"没有武器也没有手"**、§477 的"炸了但不伤人"**——**完全同族** ✓

**⇒ 三层**：
```text
§467  **`NO_SPAWN_POINT` ⇒ 加载了的地图 + 没有武器 + 没有手**
§477  **`eType-98` 发出了而没有伤害 ⇒ 一个不伤人的爆炸**
§489  **`0x20000` 留着而没有尸体接管 ⇒ 那个敌人就消失**
⇒ **⇒ **四次**"一个**表现层【的症状【指向【一个**逻辑层【的缺失**"**
```

**✅ ⭐⭐⭐ **"一个表现层的症状指向一个逻辑层的缺失"四例表**。

**⚠ 而"那个位【留在【`playerState`**里，`pmove` 需要它"**】**。**

**⇒ 十层**：
```cpp
// The bit stays in the playerState, where pmove needs it. It is masked only
// out of the entityState that goes on the wire, and only while the death
// animation is being held.
```
```text
`playerState` ⇒ **保留那个位**（**因为 `pmove` 需要它**）
`entityState` ⇒ **屏蔽**它（**只在【那个死亡动画【被持有的期间**）
⇒ **⇒ 所以【同一个位【在两个**表示【上【不同**
```

**✅ ⭐⭐⭐ **"同一个位在两个表示上不同"** —— 而**那【正是【`PlayerState` 与 `entityState` **的分工**。**

**✅ 与 §481 的"`unarmed` 的双副本分歧"**——**同族**（**第三次"两个**副本【被允许**分歧**"**）。

## 八、**`FirstDynamicServerEntityNum = 37` 与"3.3.3.3 的 `27`"** 的一个笔误核对

### 8.1 两处

```text
① "CODREF(g_spawn): CODOL reserves 2046/2047 as world/none and returns only
    slots 27..2045 to G_FreeEntity's dynamic FIFO."
② "CODDIFF(1649370): THIRTY-SEVEN, not 27."
③ "CODOL G_FreeEntity 0x004E8E70 returning only slots 27+ to the dynamic
    FIFO closes the arithmetic: 19 + 8 == 27"
④ "19 + 18 == 37，... The arithmetic in the comment there is 3.3.3.3's own
    and it still holds: 19 + 18 == 37"
```

**⇒ 二十四层**：
```text
1. **① 与 ③ 说【3.3.3.3 是 `27`**】（**`19 + 8`**）
2. ⇒ **⇒ ② 说【本 build 是 `37`**】（**`19 + 18`**）
3. ⇒ **⇒ ④ 说【`19 + 18 == 37`**】
4. ⇒ **⇒ 所以【三处【一致**：3.3.3.3 = `27`、本 build = `37`、而【两者【都是 `19 + ring`**】
```

**✅ ⭐⭐⭐ **"两者都是 19 + ring"** —— 一个**极清晰的对照**。

**⚠ 而 ④ 里那句"`19 + 18 == 37`"**⇒ **一个**正确的算术**；但 ② 里的"THIRTY-SEVEN, not 27"**⇒ **一个正确的对照**。**

**⇒ 独立验证**：
```text
`19 + 8  = 27` ✓（3.3.3.3）
`19 + 18 = 37` ✓（本 build）
⇒ **⇒ 两个**都对**
```

**✅ ⭐⭐ **"两个都对"**。

**⚠ 而"`EntityNumWorld = 2046` 作那个 `entities_` 数组的大小"**⇒ **`0..2045` 共 `2046` 项** ✓（**`std::array<SvEntityLifetime, EntityNumWorld>`**）**。**

**⇒ 三层**：
```text
`EntityNumWorld = 2046` ⇒ **⇒ 而【那个数组【是 `std::array<..., 2046>`**】
⇒ **⇒ 所以【合法索引【`0..2045`**】⇒ **⇒ 而 `2046`/`2047` 【不【在数组里**】
```

**✅ ⭐⭐⭐ **"2046/2047 不在数组里"** —— 与 §476 的 `MaximumServerCollisionEntityNum = 2045`**完全闭合** ✓

**✅ 一个跨报告的算术闭合**（**§476 的 `2045` = 这里 `2046` 项的最大索引**）**。**

## 九、关键结论

1. **⭐⭐⭐ "那个 demo 给对了形状而给错了数字"**：形状（先 `trType 1` 保持再变 ragdoll）是**一个结构的事实**（跨 build 稳定），而那个 **值 `13` 在本 build 上不存在**（`sub_AB29C0` 只处理 `0..12`，其余落到 `Com_Error(2, "90 %i", trType)` ⇒ **一个活的客户端在 `13` 被发出后第一次击杀时弹了错误对话框**）⇒ **"同一个 demo 的两个结论可靠性不同"**；而 **`9` 是本 build 的 ragdoll**（`switch` 把 `case 9` 与 `0`/`1`/`12` 分组为"保持那个位置"，而 IW3 命名 `9` 为 `TR_RAGDOLL`）；**`10` 是 `TR_RAGDOLL_GRAVITY` 而本 build 确实接受它 ⇒ "所以 aprType 10 从来没报错"**（一个反向验证）。
2. **⭐⭐⭐ `0x80000` vs `0x200000` 的误归属**：**"那个门是 `0x80000`，不是 `0x200000`；那个标志没有两位的移位；`0x00BB86BD` 的 `0x200000` 测试是 `sub_BB8050` 里一个无关的标志，把它读成那个尸体位是一次误归属 —— 而那也意味着那个 dm demo 的 `0xA0206` 一直是对的，而『更正』它到 `0x280000` 破坏了一个能工作的值"`** ⇒ **"那个『更正』把两个位组合起来，而它破坏了一个能工作的值"** —— 第四次"一个早期的结论被一个更精确的读法推翻"（与 §471/§476/§482 同族）；而 **`SvCorpseSpawnFlags = 0xA0000 = 0x80000 | 0x20000`**（**独立验证：那个生成的标志是两个位的组合**）。
3. **⭐⭐⭐ `PlayerCorpseRingSize = 18`（不是 8）**，而那**四条 3.3.3.3 的推导从未在这个 build 上重跑**：**"`out.exe` 的 `0x004E8460` 是一个 dvar 注册，不是 `G_RunCorpseAnimate`，所以那个 corpseinfo 边界、池步长和 `es.number < 19` 字面量在这个 build 上全部未检查。那个 demo 不需要它们里的任何一个"`** ⇒ **"那个 demo 不需要它们里的任何一个"**（一个极诚实的标注）。
4. **⭐⭐⭐ 那个 `18` 的测量是 `6160/6160` 个快照解码零失步**（`ET_PLAYER 1..8` / `ET_PLAYER_CORPSE 19..36` 连续 / 其余 `37..750` 而最低恰是 `37`）⇒ **"一个完全的计数是唯一的可判定的正确性"**（第三次，与 §468/§482 同族）；而 **`18` 在四个独立的地方都是 `18`**（`ServerCharacterInfoSlotCount` / `0xAF350 + 18 * 0x450` / 那个大厅容量 / 这里）—— 与 §469/§472/§477 的 `MaximumGameClients = 18` **完整闭合**。
5. **⭐⭐⭐ "带着那个 8 的代价：这个服务器会把一个动态实体号发成 `27..36`，而客户端把它存成一个尸体 —— `sub_BB9EE0` 按实体号索引 corpseinfo 而没有任何减法、没有任何边界检查"`** ⇒ **"那是一个合法的写入，但语义上错"** —— 与 §481 的"那个武器索引走进了一个事件字段"**同族**。
6. **⭐⭐⭐ 那个 `SvCorpseSettleRespawnSeparationMs` 的五步链**：**两个时间表达式（`max(deathAnimMs, 1)` 与 `max(deathAnimMs, 50)`）几乎相同 ⇒ 同一帧 ⇒ `CG_UpdateCharacterModelsFromClientInfo 0x0051BC80` 在 `modelIndex` 为零时清掉全部十个模型槽 ⇒ 尸体的 eFlags 变化重新触发 `CG_ResetEntity` case 2 ⇒ 它把那个刚被清空的 clientinfo 复制进 corpseinfo ⇒ `BG_UpdatePlayerDObj 0x0040B700` 在 `!model[0]` 上释放 DObj ⇒ 而那个数组在整个镜像里只有三个代码引用且全是读/复制路径 ⇒ 那个身体永远消失**；**零售从不撞上这个**（`settle` 在尸体生成后 `1.4..2.9` 秒，而重生是一个独立的 gametype 计时器 ⇒ **"两者用几乎相同的表达式"** 而零售用两个独立的计时器）。
7. **⭐⭐⭐ "没有一个服务器侧的测试能抓住这里的回归：那个伤害是在客户端里做的，而服务器自己的快照仍然含有一个完全合法的尸体"** ⇒ **"服务器自己的快照仍然含有一个完全合法的尸体"** ⇒ 所以那个不变式**在编译期强制**（`static_assert(SvCorpseSettleRespawnSeparationMs > 0, ...)`）⇒ **"一个 `static_assert` 是一个行为"**（第四次，与 §468 同族）。
8. **⭐⭐⭐ `SvEntityPool::reserve` 的完整理由**：**"零售的静态地图实体不占一个连续的区间（Factory 的是 `37`, `42..46`, `48`, `53`, `55`, `56`, `59..`），而客户端按号解析 `cl.entityBaselines`（快照标志 `0x10`）⇒ **一个被交给 `42` 的动态实体会继承那个槽的原点、模型与 solid** ⇒ 所以每个那个 const 基线表命名的号都必须从 `spawn()` 扣留"** ⇒ **"那个 reserve 是一个必须的前置"**（与 §414 的 `0x10` **完整闭合**）；而 **`spawnAt` 只接受一个被保留、未使用的槽** ⇒ **"两个函数是一对互补的"**。
9. **⭐⭐ `rollbackFree` 的 `previousLifetime` 参数** = §424 的 `entity free rollback lost FIFO ownership` **一个正确的替代**；而 `EntityReuseDelayMilliseconds = 500` 与 `EntityEventLifetimeMilliseconds = 300` 是**两个不同的时间各自一个语义**。
10. **⭐⭐⭐ `SvDeadPlayerHiddenFlag = 0x20000` 的完整症状链**：**线上测量：活玩家 `eFlags 2` 或 `0`，死的 `0x20002`，在归档的整整三秒里恒定**；而 **`sub_BB89E0` 跳过整个每客户端动画状态初始化**（XAnim 建立 / lerp 重置 / 两个 `0x40` 的 `memset`）⇒ **"那正是 IW 的 `EF_DEAD` 行为：客户端停止呈现那个玩家实体因为那个尸体本应接管 ⇒ 所以把这个位留在玩家实体上意味着那个玩家实体自己停止被画 —— 那就是『那个敌人就消失』的症状，若没有尸体接管"** ⇒ **"一个表现层的症状指向一个逻辑层的缺失"**（第四次，与 §467/§477/§489 二 同族）；而 **"这个位留在 playerState 里，`pmove` 需要它；它只从那个上线的 entityState 里被屏蔽，且只在死亡动画被持有的期间"** ⇒ **"同一个位在两个表示上不同"**（与 §481/§483 同族）。
11. **⭐⭐ 那个 `37` 的三处一致**：3.3.3.3 = `27`（`19 + 8`）、本 build = `37`（`19 + 18`）⇒ **"两者都是 `19 + ring`"**（独立验证两个都精确）；而 **`std::array<SvEntityLifetime, 2046>` ⇒ 合法索引 `0..2045` ⇒ `2046`/`2047` 不在数组里** —— 与 §476 的 `MaximumServerCollisionEntityNum = 2045` **完整闭合**。

## 十、`sv_entity_mp.hpp` 全文件总览

**`297` 行。**

**`16` 个常量**：
```text
EntityNumWorld                        2046
EntityNumNone                         2047
EntityReuseDelayMilliseconds           500
EntityEventLifetimeMilliseconds        300
FirstDynamicServerEntityNum             37
SvCorpseReinitialiseFlag           0x80000
SvCorpseSpawnFlags                 0xA0000   (= 0x80000 | 0x20000)
SvDeadPlayerHiddenFlag             0x20000
SvCorpseSpawnTrajectoryType              1
SvCorpseRagdollTrajectoryType            9   (demo 的 13 在本 build 不存在)
SvCorpseRagdollAngleTrajectoryType      10
SvCorpseRagdollDelayMilliseconds      1000
SvCorpseSettleRespawnSeparationMs      250
FirstPlayerCorpseEntityNum              19
PlayerCorpseRingSize                    18
```

**`2` 个 `static_assert`**：`SvCorpseSettleRespawnSeparationMs > 0` 与 `FirstPlayerCorpseEntityNum + PlayerCorpseRingSize == FirstDynamicServerEntityNum`。

**`3` 个结构/类**：`SvEntityHandle` / `SvEntityLifetime` / `SvEntityPool`（13 个方法）。

**`18` 个反汇编锚点**：`sub_BB9EE0` / `sub_BBAD90` / `sub_BBB3F0`（`imul ecx, 3B8h`）/ `0x004E8460`（**本 build 是 dvar 注册**）/ `sub_BA6A80` / `sub_BB9F70` / `0x0051BC80` / `0x0040B700` / `sub_BB89E0` / `sub_AB29C0` / `0x00BB86BD` / `sub_BB8050` / `0x004E8E70` / `0x004E8460` / `0x00693840`（BO1）/ `0x140168DC0`（Ghosts）/ `0x00BB588` / `0xAF350 + 18 * 0x450`。

**`5` 个测量锚点**：`6160/6160` 快照零失步；`952 × number + 639904` / `+ 1455144` 两个基；`0x1FC0 / 1016 == 8`；slot 20 `t=216700` → `t=217700`；`deathAnimMs 1616..1818`；零售 settle `1.4..2.9` 秒。

## 十一、未闭合点

- `sub_BB9F70` 那个 populator 是否在运行时被到达（注释说"still open and tracked by TODO(CODOL)"）。
- `0x004E8460` 在本 build 上是 dvar 注册 ⇒ 那条推导（②）不可用 ⇒ `PlayerCorpseRingSize = 18` 只有 demo 一条证据。
- `SvEntityPool` 的实现在 `sv_entity_mp.cpp`（`10,107` 字节）。
- 下一个文件：`sv_entity_mp.cpp`（`10,107` 字节）或按大小继续 `sv_alpha_weapon_port_mp.cpp`（`14,940` 字节）。
