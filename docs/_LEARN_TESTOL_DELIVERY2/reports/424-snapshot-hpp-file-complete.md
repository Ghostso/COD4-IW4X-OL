# 424 · **`sv_snapshot_mp.hpp` 全文件收尾** —— "偏移 `0` 是承重的"成了二十三处注释、`0x2B` 个"搬出去"、以及一次"免费的失败"暴露出的真实缺陷

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 4290–4703 行（`SvServerWorld` 的全部私有状态），并收尾整个文件（**共 `4703` 行**）。

## 二、**"一次免费失败"暴露了真实缺陷**（本组最重要的一段）

### 2.1 那段

```php
// ENTITIES THE ACTOR STEPPER WANTS GONE, freed after the frame commits.
//
// `freeEntity` is a generation-owned G_FreeEntity operation and it cannot run
// inside the frame transaction: doing it from stepActorEntities threw
// "entity free rollback lost FIFO ownership" and killed the dedicated. The
// barrier tear had always called it from there and got away with it only
// because a bare `SvEntityHandle{ num }` carries generation 0 and the free
// silently failed -- fixing that generation is what exposed this.
std::vector<std::uint32_t> pendingActorFrees_;
```

### 2.2 二十层

```text
1. **实体 stepper 想要消失的实体，在帧提交之后才释放**
2. ⇒ **`freeEntity` 是一个【代次拥有的 `G_FreeEntity` 操作**】**
3. ⇒ **而它【不能在帧事务【内部**】跑**】**
4. ⇒ **从 `stepActorEntities` 里做它【抛了**】**
5. ⇒ **"`entity free rollback lost FIFO ownership`"**
6. ⇒ **⇒ 并【杀死了专用服**】**
7. ⇒ **而屏障撕裂【一直**】从那里调用它**
8. ⇒ **而【它侥幸**】只因为一件事**
9. ⇒ **一个裸的 `SvEntityHandle{ num }` 携带【代次 `0`**】**
10. ⇒ **⇒ 而【那个 free 【静默地失败了**】】**
11. ⇒ **⇒ 而【修好那个代次**】正是【暴露这件事**】的东西
```

### 2.3 ⭐⭐⭐ **"一个静默的失败掩盖了一个真实的缺陷"**

**✅ 这是本报告里**最重要的一条"静默失败的代价**。**

**⇒ 三层**：
```text
真实缺陷：**在帧事务内调用 `freeEntity`** ⇒ **会杀专用服**
掩盖：**`SvEntityHandle{ num }` 的代次是 `0`** ⇒ **free 静默失败**
⇒ **⇒ 所以【那个缺陷【从未发作**】因为操作【从未成功**】
```

**✅ 与 §418 的"两个哨兵互相抵消了自己"**同族（**第二次"两个错误互相抵消"）。

**⇒ 三层**：
```text
§418  **默认值是哨兵 ⇒ 等于基准 ⇒ 永不发送**（意图落空）
§424  **免费失败 ⇒ 缺陷不发作**（缺陷被掩盖）
⇒ **⇒ 两次"两个错误抵消**】
```

**✅ ⭐⭐⭐ **"修好一个东西会暴露另一个"** —— 一个**极常见的重构风险**。

**⚠ 而"`entity free rollback lost FIFO ownership`"⇒ **一个非常具体的错误消息**。**

**✅ 与 §405 的"`resource deadlock would occur`"**同族（**第二次"精确错误消息"）。

**⇒ 三层**：
```text
§405  `resource deadlock would occur`（**非递归 mutex**）
§424  `entity free rollback lost FIFO ownership`（**帧事务外的 free**）
⇒ **⇒ 两次"错误消息直接命名根因**】
```

**✅ ⭐⭐ **一个"错误消息命名根因"的两例**。

**⚠ 而"代次 `0` 是一个有效的第一命"⇒ 见下：**

```cpp
struct LivingWeaponChild
{
    // Generation zero is a valid first life. Use an invalid entity
    // number for absence, not the generation counter.
    SvEntityHandle handle{EntityNumNone, 0};
    ...
};
```

**⇒ 六层**：
```text
1. **代次 `0` 是一个【有效的第一命**】**
2. ⇒ **⇒ 所以【不能用代次来判断"没有"**】**
3. ⇒ **用【一个无效的实体号**】`EntityNumNone`
4. ⇒ **⇒ 而这是【那个 `free` 静默失败的原因**】**
5. ⇒ **⇒ 因为【`SvEntityHandle{ num }` 意味着代次 `0`**】**
6. ⇒ **⇒ 而【一个代次 `0` 的 handle 对代次 `1` 的实体是无效的**】
```

**✅ ⭐⭐ **一个"代次 0 的双重含义"的陷阱**。

**⇒ 三层**：
```text
含义 A：**"第一命的代次"**（合法）
含义 B：**"未指定代次"**（`SvEntityHandle{ num }` 的默认）
⇒ **⇒ 所以【一个裸构造会静默地"不匹配"**】
```

**✅ ⭐⭐⭐ **一个"默认构造值有语义"的陷阱**。</br>

**✅ 与 §411 的"`BotLoadoutSequence = 1` 用非零区分首次"**同族（**第三次"零的语义**）。

## 三、**"搬出去"的完整清单**（本组第二重要）

### 3.1 二十三处显式标注

| 状态 | 位置 | 理由 |
|---|---|---|
| `zombieDowned_` | `unordered_map` | **"Side owner: never grow the address-sensitive `SvGameClient`/`WorldClientState`"** |
| `playerEventRings_` | `unordered_map` | **`184h`** |
| `pendingAltToggle_` | 数组 | **"一个普通数组，所以没有东西被加到那个地址键控的原生缓冲所包含的结构上"** |
| `zombieBattery_` | `MaximumGameClients` 数组 | **"Per player."** |
| `livingWeaponChildren_` | 数组 | **"Outside `WorldClientState` because its native mirror has a fixed size."** |
| `scriptedPlayerPositions_` | `unordered_map` | **"保留地址键控的原生玩家镜像的【受保护的分配大小】"** |
| `playerDamageProtectionGeneration_` | `unordered_map` | **"改变那个节点的大小以前已经破坏过原生动画选择"** |
| `playerAbilities_` | `unordered_map` | **"Side storage keeps `WorldClientState` and its native pmove image stable."** |
| `paintedPlayers_` | `unordered_map` | 同上 |
| `playerEquipment_` | `unordered_map` | 同上 |
| `noclipHoldUntil_` | `unordered_map` | **"那个结构每次 think 被整个拷贝，而它的偏移 `0` 是承重的"** |
| `healthRegen_` | `unordered_map` | 同 §419 |
| `pendingFallDamage_` | `mutable unordered_map` | 同上 |
| `matchEndFreezeOrigins_` | `unordered_map` | 同上 |
| `prematchHolds_` | `map` | 同上 |
| `deathViewWindows_` | `map` | **"owned by the world so the snapshot builder can see it"** |
| `killcamReplayWindows_` | `map` | 同上 |
| `factoryDoorMotions_` | `unordered_map` | **"keep metadata outside address-sensitive `WorldClientState`/`SvGameEntity`"** |
| `logicalMapEntities_` | `unordered_map` | **"`SvGameEntity` 有一个【受保护的字节大小】"** |
| `factoryViewFxRecipients_` | `map` | **"Source-owned only; the guarded `WorldClientState` layout is unchanged."** |
| `playerTouchHandlers_` / `entityTouchHandlers_` | `unordered_map` | 同模式 |
| `zmDeathFxStates_` / `zmFaceGlowStates_` | `map` | **"kept outside `SvEntityState`/native mirrored layouts"** |
| `SvHoldBreathState`（§418）/`SvKillcamReplayPose`（§417） | 兄弟结构 | 同模式 |

**⇒ 超过 `20` 处。**

### 3.2 ⭐⭐⭐ **"偏移 `0` 是承重的"成了本文件最反复出现的一条注释**

**✅ 这是本报告里**最重要的一个"单一约束的影子长度**。**

**⇒ 三层**：
```text
约束：`SvGameClient::nativePlayerState` **在偏移 `0`**（一个 `static_assert`）
后果：**任何新状态都必须【搬到外面**】
⇒ **⇒ 所以【一个断言塑造了整个类的结构**】
```

**✅ 与 §419 的"`offsetof == 0` 是一条规则而不是声明顺序的意外"**完全同源 ✓

**⇒ 三层**：
```text
§419  **`static_assert` 让规则不可违反**
§424  **而它导致 `20+` 处"搬出去"**
⇒ **⇒ 一个断言，二十个副作用**
```

**✅ ⭐⭐⭐ **一个"单一约束的结构性影响"**。</br>

**⚠ 而这本身是一个**设计张力**：**布局稳定性 vs 内聚性**。**

**⇒ 三层**：
```text
内聚：状态应该住在它所属的对象里
布局：**不能动那个对象的地址**
⇒ **⇒ 所以【选择了布局优先**】
```

**✅ 而理由充分**（`184h` 的实测代价：**`5.3%` 帧丢动画**）。

## 四、**`prematchHold` 的"28500 的失败"**（本组第三重要）

### 4.1 那段

```php
// 28800: THE PREMATCH HOLD -- command-level, never pmFlags.
//
// 2697 freezes controls for the whole "waiting + match starting" window
// and releases with freezeControlsWrapper(false) + enableWeapons().
// The 28500 attempt set pmFlags 0x800 and the CLIENT stopped advancing
// its own command time, so after the flag cleared every command was
// rejected with `non_increasing_command_time` and the player could not
// walk. Nothing here writes pmFlags; clientThinkReal zeroes the command
// instead, exactly as it already does for match end and revive.
// Keyed by (clientNum, spawnGeneration) so a respawn drops it.
```

### 4.2 二十四层

```text
1. **prematch hold —— 命令级，【绝不是 `pmFlags`**】**
2. ⇒ **2697 在【整个"等待 + 比赛开始"窗口**】冻结控制**
3. ⇒ **并用 `freezeControlsWrapper(false)` + `enableWeapons()` 释放**
4. ⇒ **⚠ 而 `28500` 的尝试【设了 `pmFlags 0x800`**】**
5. ⇒ **⇒ 而【客户端停止推进它自己的命令时间**】**
6. ⇒ **⇒ 所以【在旗标清除之后，每一条命令都被 `non_increasing_command_time` 拒绝**】**
7. ⇒ **⇒ 而【玩家不能走**】**
8. ⇒ **⇒ 这里【什么都不写 `pmFlags`**】**
9. ⇒ **`clientThinkReal` 【改为把命令清零**】**
10. ⇒ **与它【已经**】为比赛末与复活所做的一样**
11. ⇒ **按 `(clientNum, spawnGeneration)` 键控 ⇒ 所以一次重生把它丢掉**
```

### 4.3 ⭐⭐⭐ **"设了 `pmFlags 0x800` ⇒ 客户端停止推进自己的命令时间 ⇒ 清旗之后每一条命令都被拒绝"**

**✅ 这是本报告里**最重要的一条"不可逆的副作用**。**

**⇒ 三层**：
```text
意图：**冻结控制**（一个临时的、可逆的操作）
实现：**`pmFlags |= 0x800`**
后果：**客户端停止推进命令时间** ⇒ **清旗之后时间【落后**】 ⇒ **所有命令 `non_increasing`**
⇒ **⇒ 所以【一个"可逆"的设置【产生了不可逆的后果**】
```

**✅ 与 §412 的"`pmFlags 0x800` 让客户端停止推进命令时间"**——**完全闭合，而这里给出了那个后果的具体机制** ✓

**⇒ 三层**：
```text
§402  `SvPmFlagsMatchEndFrozen(0x800)` 全树无置位处
§412  `holdMatchCompletionState` 里 `setPlayerMatchEndFreeze` **确实置位**
§424  **`28500` 曾在 `prematch` 上用它 ⇒ 玩家不能走**
⇒ **⇒ 三次确认那个位的行为**
```

**✅ ⭐⭐⭐ **一个跨越三个报告的完整因果链**。

**⚠ 而"`clientThinkReal` 把命令清零"⇒ **一个替代实现**。**

**⇒ 三层**：
```text
错误：**设 `pmFlags`** ⇒ **副作用不可逆**
正确：**在 `clientThinkReal` 里【丢弃命令**】 ⇒ **副作用限定在一帧**
⇒ **⇒ 所以【"在消费端丢弃"优于"在上游关闸"**】
```

**✅ ⭐⭐ **"在消费端丢弃"** —— 与 §410 的"压制边沿不够，触发也必须检查"**同族（**第五次"修出口而非入口"）。

**⇒ 三层**：
```text
§404  "压制边沿是不够的，因为边沿是先到的"
§424  "不在上游关闸，在消费端丢弃"
⇒ **⇒ 同一原则两次**
```

## 五、**`actorEntityFloor_` 的"保真而不是正确性要求"**

### 5.1 那段

```php
// THE FLOOR RUNTIME ACTORS ALLOCATE ABOVE. One past the highest number
// the map's const-baseline table names, or FirstDynamicServerEntityNum
// when the map has no table.
//
// MEASURED, and NOT a correctness requirement: the pool already reserves
// every const-baseline number, so an actor in the gaps resolves a zeroed
// client baseline and this server deltas against zero -- the two agree
// and nothing is inherited. This is fidelity. Retail numbers its actors
// 488..815 on factory, above the map's last static entity (625), and
// sixteen of the seventeen measured lives sit above it -- one did not,
// so it is retail's convention rather than an invariant.
```

### 5.2 二十层

```text
1. **运行时 actor 分配在【那个地板之上**】**
2. ⇒ **地图 const-baseline 表命名的【最高号加一**】**
3. ⇒ **或 `FirstDynamicServerEntityNum`**（**当地图没有表时**）**
4. ⇒ **⚠ 测量出来的，而【不是一个正确性要求**】**
5. ⇒ **因为【池已经保留了每一个 const-baseline 号**】**
6. ⇒ **⇒ 所以【一个在空隙里的 actor 解析一个零化的客户端基准**】**
7. ⇒ **而【这个服务器对零做增量**】**
8. ⇒ **⇒ 两者【一致**】而【什么也不被继承**】**
9. ⇒ **⇒ 这【是保真**】**
10. ⇒ **零售在 factory 上把它的 actor 编号在 `488..815`**
11. ⇒ **在【地图最后一个静态实体（`625`）之上**】**
12. ⇒ **⇒ 而【十七个被测量的生命里的十六个坐在它之上**】**
13. ⇒ **⇒ 一个【不**】**
14. ⇒ **⇒ 所以【它是零售的【约定**】而不是一个【不变式**】】
```

### 5.3 ⭐⭐⭐ **"十六个坐在它之上，一个不 ⇒ 所以它是约定而不是不变式"**

**✅ 这是本报告里**最精确的一个"约定 vs 不变式"判据**。**

**✅ 与 §414 的"`238/238` brush 模型按构造一致"**相反**（那里**是 `100%`** ⇒ 可以叫不变式）。

**⇒ 三层**：
```text
`16/17` ⇒ **一个例外** ⇒ **约定**
`238/238` ⇒ **零例外** ⇒ **不变式**（但仍被"每次加载核对"保护）
⇒ **⇒ 判据是【有没有例外**】
```

**✅ ⭐⭐⭐ **"一个例外区分约定与不变式"** —— 一个**极简洁的判据**。

**✅ 与 §419 的"`2→1` 而玩家在 `71`"**同族（**第七次"一个例外定案"）。

**⚠ 而"`488..815`"与"`625`"⇒ **两个具体的数**。**

**⇒ 三层**：
```text
最后静态实体：**`625`**
actor 范围：**`488..815`**
⇒ **⇒ 所以 `488 < 625 < 815`** ⇒ **`actor 跨越**了那条线**
```

**⚠ 一个**需要标注的观察**（`actor` 的范围与静态实体的范围**重叠**）。

**⇒ 三层**：
```text
若 actor **必须**在静态之上 ⇒ **`488` 违规**
⇒ **⇒ 所以【"之上"是一个统计倾向而不是规则**】
```

**✅ ⭐⭐ **"`16/17`"与"`488 < 625`"两处都指向【约定而非规则**】**。

## 六、**`SvPlayerCorpseStages` 的三阶段**

### 6.1 那段

```php
// A corpse is a THREE-STAGE entity on the wire, measured off the dm demo
// (Tools/ffa/corpse-lifetime.py following one slot end to end):
//   1. spawn   - re-initialise bit set, trType 1, anims written ONCE
//   2. settle  - the re-initialise bit clears once the death animation
//                has had time to run
//   3. ragdoll - trType 13 + aprType 10, about a second after the spawn
// Deadline of 0 means the stage is already done for that slot.
```

**⇒ 十二层**：
```text
1. **一具尸体在线上是一个【三阶段的实体**】**
2. ⇒ **从一个 dm demo 测出（跟一个槽从头到尾）**：
      · **① spawn**：**重初始化位置位、`trType 1`、动画【写一次**】**
      · **② settle**：**重初始化位【清除**，一旦死亡动画有时间跑完**
      · **③ ragdoll**：**`trType 13` + `aprType 10`**，**出生后约一秒**
3. ⇒ **`0` 的截止时间 ⇒ 那个阶段【对该槽已经完成**】**
```

**✅ 与 §377 的"`0x20000` 跳过动画状态初始化但不停止绘制"**完全闭合 ✓

**⇒ 三层**：
```text
§377  `0x20000` **跳过动画状态初始化**
§424  **三阶段的"重初始化位"**
⇒ **⇒ 同一个位在两个场景**
```

**✅ ⭐ **一个"位的用途"的确认**。

**⚠ 而"`trType 1 → 13`"与 §406 的"`trType` 必须从 `1` 移到 `13` 而 `aprType` 到 `10`，约一秒后"**完全一致** ✓

## 七、**六条"每帧拷贝"的约束汇总**

**⇒ 本文件里所有"搬到外面"的注释，理由归结为两类**：

```text
① 地址敏感（偏移 0 承重，指针混淆）
② 每 think 整个拷贝（6.4KB / 25184 字节）
```

**⇒ 五层**：
```text
1. **`SvGameClient` 的【偏移 `0`**】是地址键控的**
2. ⇒ **而【`WorldClientState`（`25184` 字节）【每次 think 被整个拷贝**】**
3. ⇒ **⇒ 所以【两者都禁止增长**】**
4. ⇒ **⇒ 而【这是【20+ 处"搬出去"**】的全部理由**
5. ⇒ **⇒ 一次 `184h` 的故障塑造了整个类的组织方式**
```

**✅ ⭐⭐⭐ **"一次故障塑造了整个类的组织方式"** —— 本报告的核心结论。

## 八、关键结论

1. **⭐⭐⭐ "一个静默的失败掩盖了一个真实的缺陷"**：**`freeEntity` 在帧事务内调用会杀专用服**（`entity free rollback lost FIFO ownership`），而**屏障撕裂一直那么做却侥幸**，**只因为 `SvEntityHandle{ num }` 携带代次 `0` 而那个 free 静默失败了** ⇒ **修好代次才暴露了它**。
2. **⭐⭐ "修好一个东西会暴露另一个"`** —— 与 §418 的"两个哨兵互相抵消"同族（**两个错误互相抵消**）。
3. **⭐⭐⭐ 代次 `0` 的双重含义陷阱**：**"第一命的代次"（合法）vs "未指定代次"（`SvEntityHandle{ num }` 的默认）** ⇒ **一个裸构造会静默地"不匹配"** ⇒ 所以 `LivingWeaponChild` 用 **`EntityNumNone` 而不是代次来表达"没有"**。
4. **⭐⭐⭐ 超过 `20` 处"搬出去"的显式标注**，全部理由归结为两类：**偏移 `0` 地址键控** 与 **`WorldClientState`（`25184` 字节）每 think 整个拷贝**。
5. **⭐⭐⭐ "一次 `184h` 的故障塑造了整个类的组织方式"`** —— 一个 `static_assert` 的二十个结构性副作用。
6. **⭐⭐⭐ `prematchHold` 的 `28500` 完整病历**：**设 `pmFlags 0x800` ⇒ 客户端停止推进它自己的命令时间 ⇒ 清旗之后每一条命令被 `non_increasing_command_time` 拒绝 ⇒ 玩家不能走** ⇒ **所以现在"什么都不写 `pmFlags`，`clientThinkReal` 改为把命令清零"** —— 一个"可逆的设置产生了不可逆的后果"。
7. **⭐⭐ "在消费端丢弃优于在上游关闸"`** —— 第五次"修出口而非入口"（与 §404 的"压制边沿不够，触发也必须检查"同族）。
8. **⭐ `prematchHold` 按 `(clientNum, spawnGeneration)` 键控 ⇒ 一次重生自动丢掉它**。
9. **⭐⭐⭐ `actorEntityFloor_` 的"`16/17` 坐在静态实体 `625` 之上，一个不 ⇒ 所以它是【约定】而不是【不变式】"`** —— 一个"一个例外区分约定与不变式"的判据（与 §414 的 `238/238` 零例外对照）。
10. **⚠ "`actor` 范围 `488..815` 而最后的静态实体是 `625`" ⇒ `488 < 625 < 815`** ⇒ **"之上"是一个统计倾向**。
11. **⭐⭐ `actorEntityFloor_` 也"不是正确性要求"**：**池已保留每一个 const-baseline 号 ⇒ 空隙里的 actor 解析零化基准而与我们的零增量【一致】⇒ 这是保真不是正确性**。
12. **⭐⭐ 尸体的三阶段（`spawn` / `settle` / `ragdoll`）由 `Tools/ffa/corpse-lifetime.py` 跟一个槽从头到尾测出**，与 §377/§406 的 `0x20000`/`trType 1→13`/`aprType 10` 完全闭合。
13. **⭐ `spawnRefusalReasons_` 的"每客户端一个而不是一个共用的"**：**"一个共用的字符串意味着两个客户端通过它交替 `client=0` 和 `client=1`，而比较永不匹配，于是一个本该在【变化】时触发的诊断会【每帧】触发"`** ⇒ 与 §405 的"一个共用的边沿触发锁存会让其余致盲"同源。
14. **⭐ `agentSlotsInUse_` 的"一个槽在 actor 的 `entityState +0x058` 出生时被烘焙进去而必须【在其生命的整个期间**】不移动**"。
15. **⭐ `pendingFallDamage_` 的 `mutable` 理由**：**"观察落地事件的 think 是一个 `const` 方法 —— 它读客户端的状态而绝不能改变它；记录一次坠落发生是【为后来一帧的记账】，不是对被思考的状态的变异"`**。

## 九、`sv_snapshot_mp.hpp` 全文件总览

**行数：`4703`**。**`SvServerWorld` 约 `390` 个公开方法**（`70` 个在 2960–3290 段，其余在 3290–4106 段）。

**十二个结构族**：

| 族 | 结构 |
|---|---|
| 实体状态 | `SvEntityState`（含 `ET_PLAYER`/`ET_SCRIPTMOVER`/`ET_ACTOR` 三个语义组）、`SvGameEntity`、`SvConstBaselineEntry` |
| 玩家状态 | `SvPlayerState`（~`6.4KB`）、`SvGameClient`（`nativePlayerState` 在偏移 `0`）、`WorldClientState`（`25184` 字节） |
| 客户端信息 | `SvClientInfoState`、`SvCharacterCustomization`（**`64` 字节，受 `static_assert` 保护**） |
| 快照框架 | `SvSnapshotFrame`、`SvAgentState`（`24` 字段）、`SvClientState`、`SvAnimationCommand` |
| 世界事件 | `SvWorldEvent`（`20` 个类型）、`SvSdEventPayload` |
| 失败诊断 | `SvClientThinkFailureStage`（`37` 值）、`SvSnapshotFrameValidationFailure`（`20` 值）、`SvSnapshotWriteFailure`（`15` 值） |
| 路由 | `ActorRoute`（`~40` 字段）、`BarrierState`（`6` 板）、`SvZmNavGraph` |
| 工厂 | `FactoryDoorMotionState`、`FactoryPurchasedPerkLife`、`FactorySpecialStatus`、`FactoryTrapPresentation` |
| 尸体 | `SvPlayerCorpseStages`（三阶段）、`ZmRetainedCorpse` |
| ZM 死亡表现 | `ZmDeathFxState`（含 `4` 个 `Emission`）、`ZmFaceGlowState` |
| 回放 | `SvKillcamReplayPose`、`SvKillcamReplayWindow`、`SvDeathViewWindow` |
| 拾取 | `SvLootItem`、`SvWeaponGrant`、`SvScavengerBag` |

**七个编译期断言**：
```cpp
static_assert(offsetof(SvGameClient, nativePlayerState) == 0);
static_assert(sizeof(WorldClientState) == 25184);
static_assert(sizeof(SvCharacterCustomization) == 64);
static_assert(offsetof(SvPlayerState, offhandWeaponAssetIndex) == 10);
static_assert(offsetof(SvPlayerState, pmTime) == 12);
static_assert(offsetof(SvPlayerState, offhandWeaponSlotA) + 2 == offsetof(SvPlayerState, gravity));
static_assert(offsetof(SvPlayerState, offhandWeaponSlotB) + 2 == offsetof(SvPlayerState, lastSprintStart));
static_assert(offsetof(SvPlayerState, offhandWeaponSlotC) + 2 == offsetof(SvPlayerState, legsTimer));
```

**二十四个线上常量**：
```text
0x04 服务器计数 / 0x08 baseline / 0x0A 场景阻断 / 0x10 实体 baseline / 0x02 入口
eType: 0 general / 1 player / 2 corpse / 3 item / 6 scriptmover / 19 actor / 21 actorentitycorpse / 23 events base
事件 id: 0x03/0x04/0x2C/0x4B/0x53/0x56/0x6F/0x71/0x82/0x83/0x86/0x88/0x8F
哨兵: 2046 EntityNumWorld / 2047 EntityNumNone / 0xFFFFFF brush solid / 0xFFFFFFFF agent 附件
```

## 十、未闭合点

- `spawnRefusalReasons_` 的"一个共用的边沿触发锁存会让其余致盲"（§118）的完整记录。
- `wetworkRecordedOpeningUntil_` 的"880 行 admission scene"。
- `zmRoundTickMilliseconds_` 的"零售早期回合节奏是 `300ms` 所以导演心跳是 `100ms`"。
- `SvZmBoardFlightProfile` 的字段。
- `PlayerCorpseRingSize` 与 §422 的 `18` 尸体号的关系。
- **下一步**：`sv_client_mp.cpp`（`214,126` 字节）。
