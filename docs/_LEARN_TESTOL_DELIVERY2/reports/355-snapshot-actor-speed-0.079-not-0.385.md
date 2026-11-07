# 355 · **"0.079，不是 0.385 —— 12.33 的速度错了 4.8 倍"** —— `1,063` 条零售轨、`259,968` 个 100ms 断言、中位数 7.9 单位、"每 5 帧而非前 40 帧"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 13600–14000 行。

## 二、**`0.079` 的完整测量**（本组最重要的一段）

### 2.1 那段

```php
// 0.079, NOT 0.385 -- 12.33's speed was WRONG BY 4.8x. See 12.62.
//
// It read "38-39 units per 100 ms snapshot" off a handful of samples. Measured
// across all 1063 reconstructed retail tracks (12.58), on the 259,968 asserts
// whose interval really is 100 ms, with teleports and standing still excluded:
//
//     displacement per 100 ms assert   median 7.9 u   p25 7.0   p75 8.2
//     in 36..41 u, i.e. 12.33's band    0.7% of moving asserts
//     in 6..10 u                       46.8%
//
// and it is FLAT: 78-80 u/s in every quarter of all three captures, so there is
// no round scaling to model here either. A retail zombie walks at ~79 u/s, which
// is well under a player's run -- they are slow and they are relentless. At 385
// this server was moving them nearly five times too fast, which is also why no
// walk animation could ever have matched: the feet would skate.
constexpr float ActorUnitsPerMillisecond = 0.079f;
```

### 2.2 十四层

```text
1. **`0.079`，不是 `0.385` —— 12.33 的速度错了 4.8 倍**（见 12.62）
2. ⇒ **它从【几个样本】上读"每 100ms 快照 38-39 单位"**
3. ⇒ **在全部 1063 条重建的零售轨上测量（12.58）**
4. ⇒ **在 259,968 个【间隔真的 100ms】的断言上**
5. ⇒ **排除传送与站着不动**
6. ⇒ **每 100ms 断言的位移：中位数 7.9 单位、p25 7.0、p75 8.2**
7. ⇒ **在 36..41 单位里（即 12.33 的带）⇒ 只有【移动断言的 0.7%】**
8. ⇒ **在 6..10 单位里 ⇒ 46.8%**
9. ⇒ **而它是【平的】：三个捕获的【每一个四分之一】都是 78-80 单位/秒**
10. ⇒ **所以这里也没有回合缩放在建模**
11. ⇒ **一个零售僵尸以约 79 单位/秒行走，远低于玩家的跑速**
12. ⇒ **它们是慢的而且不屈不挠**
13. ⇒ **在 385 这个服务器把它们移动得【近五倍过快】**
14. ⇒ **那也正是一旦没有行走动画能匹配的原因：脚会【打滑】**
```

### 2.3 **"0.7% vs 46.8%"是决定性证据**

**✅ 三层**：

```text
12.33 的带（36..41 单位）  覆盖 0.7% 的移动断言
真实的中位带（6..10 单位）  覆盖 46.8%
⇒ 所以 12.33 从一个【离群】的样本带读了速度
```

**✅ 与 §345 的"从一个不可能包含一个的样本得出结论"**同族（**第二次采样偏差**）。**

**⚠ 而这里更微妙：12.33 的样本**确实**是移动断言 —— 只是它们**不在中位数上**。**

**⇒ 所以这是**"小样本 + 分布偏移"**而不是**"样本不含目标"**。】

**✅ **两个不同的采样罪**（§345 与这里）。**

### 2.4 而 **`1063` / `259968` / `7.9` / `78-80`**

```text
1,063    重建的零售轨数
259,968  间隔真的是 100ms 的断言数
7.9      每 100ms 位移中位数（单位）
7.0 / 8.2  p25 / p75
78-80    每四分之一都在这个区间（单位/秒）
79       约等于零售僵尸速度
```

**⚠ 而 `7.9 × 10 = 79` ⇒ **与 78-80 一致 ✓**

**✅ **两个推导互相印证。**

### 2.5 而 **"也没有回合缩放在建模"**

**⇒ 三层**：

```text
1. 若零售在多轮次里有速度缩放
2. ⇒ **那么四分之一分组会显示差值**
3. ⇒ **而它是平的（78-80 全部）**
4. ⇒ **所以没有缩放**
```

**✅ 一个**主动排除混淆变量**的论证。**

**⇒ 与 §349 的"那个速率是真的而它是错误的模型"**同族。**

### 2.6 而 **"脚会打滑"**

**✅ 一个**具体的、可见的**症状（**第三次"打滑/冻结"族**）。**

**⇒ 与 §347 的"重新施加命令让动画看起来冻结"、§353 的"到一半停止挥击"**同族。**

**⇒ 三次，都是**"动画与位移不同步"**。**

### 2.7 而 **`.079 × frameMilliseconds`**

```cpp
const auto step = ActorUnitsPerMillisecond * static_cast<float>(frameMilliseconds);
```

**⇒ 三层**：

```text
1. **每毫秒的单位数**
2. ⇒ **乘以帧的毫秒数**
3. ⇒ **所以是【时间补偿】的**（不依赖帧率）
```

**✅ 与 §349 的 `PredictedModeReportInterval`、§353 的 `dotAt = now + 1000`**同族。**

## 三、**"死者在任何东西移动它之前先处理"**（本组第二重要）

### 3.1 那段

```php
// DEAD FIRST, BEFORE ANYTHING ELSE MOVES IT (12.161).
//
// A zombie is dead when the damage pass has taken its health to zero.
// `entityDamageStates_` keeps a terminal entry rather than erasing it --
// `SV_IsEntityDamageStateValid` refuses to REGISTER non-positive health
// but the pass leaves the record -- so this reads the same map the
// damageable view is built from.
//
// Stop routing/collision while the death clip runs. The opt-in
// presentation then transfers ownership to a bounded corpse pool;
// the legacy path frees the entity at the end of its death clip.
if (zmDeathFx_.bo1Derived) stepZmDeathFx(entity, now);
stepZmFaceGlow(entity, now);
const auto damageState = entityDamageStates_.find(entityNum);
const auto dead = damageState != entityDamageStates_.end() && damageState->second.health <= 0;
if (dead) { ... continue; }
```

### 3.2 十层

```text
1. **死者先处理，在任何别的东西移动它之前（12.161）**
2. ⇒ **一个僵尸在伤害 pass 把它的血量降到零时是死的**
3. ⇒ **`entityDamageStates_` 保留一个终态条目而不是擦掉它**
4. ⇒ **`SV_IsEntityDamageStateValid` 拒绝【注册】非正血量**
5. ⇒ **但 pass 留下记录**
6. ⇒ **所以这里读的是【可伤害视图】所建自的同一张表**
7. ⇒ **在死亡片段运行时停止路由/碰撞**
8. ⇒ **opt-in 的表现层然后把所有权转移到一个【有界的尸体池】**
9. ⇒ **legacy 路径在死亡片段结束时释放实体**
10. ⇒ **所以 `dead` 分支必须 `continue`**（不进入移动逻辑）
```

### 3.3 而**"`SV_IsEntityDamageStateValid` 拒绝注册非正血量但 pass 留下记录"**

**✅ 与 §345 的"一个从观测范围取的界"**不同**。**

**⇒ 三层**：

```text
1. **注册**要求 health > 0
2. ⇒ **而伤害 pass 可以通过扣血把它降到 0**
3. ⇒ **所以有一个"有效状态里含非正血量"的窗口**
```

**✅ 一个**聪明的两阶段设计**（注册严、运行宽）。**

**⚠ 而 `entityDamageStates_` 因此有**两种含义**（注册状态 / 当前状态）。**

**⚠ 一处**需要小心的语义**。**

### 3.4 而**死亡分支的十一项初始化（`first` 时）**

```cpp
entity.networkState.actorVelocity = {};
entity.collisionLinked = false;
entity.collisionContents = 0;
entity.networkState.solid = 0;
entity.networkState.actorField00AC = 0;
const auto fxState = zmDeathFxStates_.find(entityNum);
const bool electrical = zmDeathFx_.bo1Derived && fxState != end && fxState->second.electrical;
const bool headless = fxState != end && fxState->second.headless;
const auto death = SV_ZmChooseDeath(zmDeaths_, zmDeathSequence_++,
    { zmActorDeathAnim_, SvActorCorpseMilliseconds, 1 },
    electrical ? std::optional<bool>{true} : std::nullopt,
    zmDeathFx_.refined && !electrical && !headless);
if (death.animation) {
    entity.networkState.actorAnimIndex = death.animation;
    entity.networkState.actorAnimStartTime = now;
}
```

**⇒ 八层**：

```text
1. **速度清零**
2. ⇒ **`collisionLinked = false`**
3. ⇒ **`collisionContents = 0`**
4. ⇒ **`solid = 0`**
5. ⇒ **`actorField00AC = 0`**
6. ⇒ **取 electrical 与 headless 标志**
7. ⇒ **`SV_ZmChooseDeath` 五个参数**：deaths / sequence / 三件套 / electrical 提示 / refined 提示
8. ⇒ **有动画 ⇒ 设 animIndex 与 startTime = now**
```

### 3.5 而**五个清零的含义**

```text
actorVelocity      不再移动
collisionLinked    从碰撞视图移除
collisionContents  0 ⇒ 不挡任何东西
solid              0 ⇒ 【不是画笔模型】（§350 说 0xFFFFFF 才是）
actorField00AC     未知字段
```

**✅ 与 §350 的"`solid == 0xFFFFFF` ⇒ 走画笔分支"配合。**

**⇒ 所以死后 `solid = 0` ⇒ **正确处理（不是画笔）。**

### 3.6 而**"一个有界的尸体池"**

**✅ 与 §344 的"`ET_ACTOR_CORPSE` 的 32 个字段"**配合。**

**⇒ 三层**：

```text
1. 死亡 ⇒ 转成 `ET_ACTOR_CORPSE`
2. ⇒ **进一个有界的池**
3. ⇒ **超出的被回收**（`zmRetainedCorpses_`）
```

**✅ 与 §349 的 `reset()` 里 `zmRetainedCorpses_.clear()`**配合。**

## 四、**电击序列的四段**（本组第三重要）

```php
if (zmDeathFx_.refined && electrical && death.electrical && SV_ZmHasDeathSequence(death))
    if (auto fx = zmDeathFxStates_.find(entityNum); fx != end) {
        auto &state = fx->second;
        state.downAnimation = death.downAnimation;
        state.downAt = now + death.loopMilliseconds;
        state.downMilliseconds = death.downMilliseconds;
        state.retireAt = state.downAt + death.downMilliseconds;
        entity.networkState.actorAnimIndex = death.loopAnimation;
        if (zmDeathFx_.shock && state.outfit.shockBone < 255)
            state.emissions[2] = { zmDeathFx_.shock, state.outfit.shockBone, now + 50 };
        OlMod::RuntimeLog::write(..., "ZMFX loop entity=... animation=... down=... holdMs=...");
    }
```

### 4.1 七层

```text
1. **五个前置**：refined / electrical / `death.electrical` / `SV_ZmHasDeathSequence` / state 存在
2. ⇒ **`downAt = now + loopMilliseconds`** ⇒ 循环片段播完后才倒下
3. ⇒ **`retireAt = downAt + downMilliseconds`**
4. ⇒ **当前动画换成 `loopAnimation`**
5. ⇒ **`emissions[2]` = shock 效果**
6. ⇒ **日志 `ZMFX loop`**
```

### 4.2 而**时间链**

```text
now
  ↓ loopMilliseconds
downAt        开始播 downAnimation
  ↓ downMilliseconds
retireAt      释放（转尸体）
```

**✅ 一个**三段的时间线**（循环 → 倒下 → 释放）。

### 4.3 而**"`retireAt` 在延迟帧时仍给倒下片段完整时长"**

```php
if (!state.downStarted && now >= state.downAt) {
    state.downStarted = true;
    entity.networkState.actorAnimIndex = state.downAnimation;
    entity.networkState.actorAnimStartTime = now;
    // A delayed server frame still gives the down clip its
    // full duration before native corpse ownership transfer.
    state.retireAt = now + state.downMilliseconds;
    ...
}
```

**⇒ 五层**：

```text
1. **一个延迟的服务器帧仍给倒下片段它的【完整时长】**
2. ⇒ 所以 `retireAt = now + downMilliseconds`（**不是** `downAt + downMilliseconds`）
3. ⇒ **在原生尸体所有权转移之前**
4. ⇒ 所以即使 `now` 已经超过 `downAt` 很多，倒下的片段**仍播完整**
```

**✅ 一个**"延迟不吞时长"**的修正。**

**⚠ 而 §354 的 `position.duration` 也是这样处理（用 `started` 而不是 `now`）。**

**⇒ 两处**不同的选择**：**

```text
死亡倒下片段  用 `now`（延迟则顺延）
屏障修复动画  用 `started`（延迟则快进）
```

**⚠ 一处**不一致**。**

**⇒ 可能因为动画**必须完整**而**几何可以快进**。**

**✅ 一个**合理的区分**。**

## 五、**"每隔 5 帧而不是前 40 帧"**（本组第四重要）

### 5.1 那段

```php
// A BOUNDED BURST, exactly like AGENTWIRE above it, and for the same reason:
// "the zombies did not move" has half a dozen causes -- no graph, no goal
// node, no player node, an empty route, a frozen cursor -- and they are
// indistinguishable from the outside. One line per frame names which.
std::string routeReport;
static std::atomic<int> routeReports{ 0 };
// EVERY 5th FRAME WHILE EXPLICITLY ENABLED, FOREVER -- not the first 40.
//
// This used to stop after 40 reports, which at a 20 Hz frame is the first TWO
// SECONDS of a match. Every actor position quoted from this log has therefore
// been from before the player finished loading, including the ones used to
// argue that actors spawn far away. Steady-state behaviour was never visible.
const auto reportRoutes = zombieRouteDiagnosticsEnabled() &&
    (routeReports.fetch_add(1, std::memory_order_relaxed) % 5u) == 0u;
```

### 5.2 十二层

```text
1. **一个有界的爆发，与上面的 AGENTWIRE 完全一样，理由也一样**
2. ⇒ **"僵尸没有移动"有【半打】原因**：
     · 没有图
     · 没有目标节点
     · 没有玩家节点
     · 空路由
     · 冻结的游标
3. ⇒ **它们从外面【无法区分】**
4. ⇒ **每帧一行命名是哪一个**
5. ⇒ **每隔 5 帧而【只要显式启用】就永远 —— 不是前 40 帧**
6. ⇒ **这过去在 40 份报告后停止**
7. ⇒ **而在 20Hz 帧下那是比赛的【头两秒】**
8. ⇒ **所以从这个日志引用的每一个 actor 位置都是玩家完成加载【之前】的**
9. ⇒ **包括那些被用来说"actor 生成在很远的地方"的**
10. ⇒ **稳态行为从未可见**
```

### 5.3 ⭐ **"从这个日志引用的每一个位置都是加载之前的"**

**✅ 这是本文件里**最尖锐的自我推翻**。**

**⇒ 三层**：

```text
1. 日志只在前 2 秒
2. ⇒ **所以所有从这个日志得出的结论都是关于加载期的**
3. ⇒ **包括"actor 生成在很远的地方"这个结论**
```

**✅ 与 §349 的"那个速率是真的而它是错误的模型"**同族（**第三次"自己的数据骗了自己"**）。**

**⇒ 而这里是**更彻底**的：**整批结论作废**。**

**⚠ 与 §340 的"§82e 的诊断错而建议对"、§345 的"`demoq` 的表示差"**四次自我推翻**。**

### 5.4 而**"半打原因"**

**⇒ 五个列出（图/目标节点/玩家节点/空路由/冻结游标）。**

**⚠ "半打"是六而列了五个。**

**⇒ 一处**小的计数不符**（第二次，见 §347 的"两个消费者"列了三个）。**

### 5.5 而**"每帧一行命名是哪一个"**

**⇒ 三层**：

```text
1. 五个症状外部不可分
2. ⇒ **所以日志必须命名**
3. ⇒ **而不是只报告"没动"**
```

**✅ 与 §351 的"命名而不是计数"**同族（**第三次**）。**

**⇒ **"命名而不是计数/命名是哪一个"是本文件的核心仪器纪律。**

## 六、`playerOriginReport` 的**两个候选字段**（本组第五重要）

```php
if (reportRoutes) {
    const auto whole = [](const float value) { return std::to_string(static_cast<int>(std::lround(value))); };
    for (const auto &[clientNum, state] : clientStates_) {
        playerOriginReport += " p" + std::to_string(clientNum) +
            ":state=" + std::to_string(static_cast<int>(state.client.gameplayState)) +
            ":ps=" + whole(state.client.playerState.origin[0]) + "," + whole(...[1]) + "," + whole(...[2]) +
            ":ent=" + whole(state.entity.currentOrigin[0]) + "," + whole(...[1]) + "," + whole(...[2]);
    }
}
```

### 6.1 五层

```text
1. **每个玩家两个位置**：
     · `ps` = `playerState.origin`
     · `ent` = `entity.currentOrigin`
2. ⇒ **加 `gameplayState`**
3. ⇒ **目的：路由看到的是哪一个？**
4. ⇒ **`lround` 取整**（不要小数）
5. ⇒ **每 5 帧**
```

### 6.2 而**为什么两个**

**✅ 与 §347 的"两个时间源"**同族。**

**⇒ 三层**：

```text
1. `playerState.origin` 是**发给客户端的**
2. ⇒ `entity.currentOrigin` 是**服务端实体的**
3. ⇒ **而路由器可能用其中之一**
4. ⇒ **所以打印两个以确定"路由看到的是哪个"**
```

**✅ 与 §354 的"`nearestPlayerPosition` 用 `playerState.origin`"**配合。**

**⇒ 所以路由用 `playerState.origin`。**

**⚠ 而 `entity.currentOrigin` 才是**物理位置**。**

**⇒ 所以**两个可能分叉**（一个有积分一个有原始）。**

**✅ 与 §312 的"实体位置 vs playerState 位置"**同族。

## 七、**"在同一个稳定顺序里处理 actor"**（本组第六重要）

### 7.1 那段

```php
// PROCESS ACTORS IN THE SAME STABLE ORDER THE WINDOW QUEUE USES.
//
// entities_ is unordered.  The queue rule below lets a higher-numbered
// follower move only after every lower-numbered actor on the same authored
// goal has moved.  Iterating the hash table allowed the follower to move
// first and then the leader to move into it, producing byte-identical piles
// even though the spacing test itself was enabled.  Sorting the tiny actor
// set makes the existing one-way queue invariant true.
for (const auto entityNum : actorNumbers) { ... }
```

### 7.2 九层

```text
1. **在窗口队列用的【同一个稳定顺序】里处理 actor**
2. ⇒ **`entities_` 是【无序的】**（`unordered_map`）
3. ⇒ **下面的队列规则让一个【更高编号的跟随者】只在同一个作者化目标上的【每一个更低编号的 actor 都已移动】之后才移动**
4. ⇒ **迭代哈希表让跟随者先移动而然后领导者移进它**
5. ⇒ **产生【逐字节相同的堆】即使间距测试本身是启用的**
6. ⇒ **排序这个小小的 actor 集合让既有的【单向队列不变式】成真**
```

**✅ 与 §337 的"`writeClients` 的两个几乎相同的函数"、§354 的"七个 nearestPlayer"**不同** —— 这是**顺序依赖**。**

**⇒ **第六次"确定性要求"**（§337 的 `clientNum` 排序、§339 的 `currentEntries` 排序、§344 的 `SV_PresentableTeam`、§349 的 `actorNumbers`）。**

**⚠ 而"逐字节相同的堆"是一个**极具体的失败**。**

**⇒ 所以**间距测试通过但实际重叠**。**

### 7.3 而**"单向队列不变式"**

**⇒ 三层**：

```text
1. 低编号先走
2. ⇒ 高编号只能在低编号都走过之后走
3. ⇒ **所以高编号永远追不上低编号**
```

**✅ 一个**极简的防重叠**（不需要真正的空间分区）。**

**⚠ 而它依赖**每帧的重排序**（因为排序是每帧做的）。**

**✅ 与 §347 的"每个 actor 每秒一对"配合。**

## 八、`actorRoutes_` 的**每帧清理**

```cpp
// Entity numbers are reused, so a route left behind by a dead actor would be
// inherited by the next one to take its slot. Cheap at 32 actors.
std::erase_if(actorRoutes_, [this](const auto &entry) {
    const auto existing = entities_.find(entry.first);
    return existing == entities_.end() || !isActorEType(existing->second.networkState.eType);
});
```

### 8.1 四层

```text
1. **实体号被复用**
2. ⇒ **所以一个死 actor 留下的路由会被下一个占它槽的继承**
3. ⇒ **清理条件**：实体不存在 或 不是 actor 类型
4. ⇒ **32 个 actor ⇒ 便宜**
```

**✅ 与 §345 的"实体号被复用 ⇒ 继承前一个占用者的 `+0xA0`"**完全同族（**第四次"号复用"**）。**

**⇒ **"号复用"是本文件反复的 bug 源**。**

**⚠ 而这里用 `isActorEType` 而不是 `== EntityTypeActor` ⇒ **所以 `ActorCorpse` 也算 actor**。**

**✅ 与 §344 的 `isActorEType` 配合。**

### 8.2 而**"廉价在 32 个 actor"**

**✅ 与 §349 的 `PredictedModeReportInterval`、§353 的"32 个整数"同族。**

**⇒ **一个明确的成本论证**（不是"应该够快"）。**

## 九、**`actorHasGoal` 的"没有目标就站着不动"**

```cpp
// NO GOAL MEANS STAND STILL. 8 of factory's 69 spawners name no
// target, and walking those somewhere invented is precisely the
// through-walls behaviour this replaces.
if (!entity.networkState.actorHasGoal) continue;
```

### 9.1 五层

```text
1. **没有目标意味着站着不动**
2. ⇒ **factory 的 69 个生成器里有 8 个不命名目标**
3. ⇒ **而把那些走到某个【臆造】的地方**
4. ⇒ **正是这个（代码）所替代的【穿墙行为】**
5. ⇒ 所以 `continue`
```

**✅ 与 §350 的"better than to be wrong"**同族（**第十四次"不要猜"**）。**

**⚠ 而 `8/69 = 11.6%`。**

**⇒ 所以**一个显著的少数**。**

### 9.2 而**"穿墙行为"**

**✅ 一个**具体的失败模式**（走到臆造处 ⇒ 穿墙）。**

**⇒ 与 §347 的"`through-walls behaviour`"**第一次出现在这里。**

**⚠ 与 §353 的"到一半停止挥击"、§355 二.6 的"脚会打滑"**同族（**第四次具体视觉症状**）。**

## 十、`negotiationActive` 的**"测量的协商拥有位移【与】动画"**

### 10.1 那段

```php
// A measured negotiation owns displacement AND animation. Replanning,
// ground snapping and ordinary 18-unit stepping must not interrupt it.
if (route.negotiationActive) {
    const auto motion = zmNavGraph_.negotiationMotion.find(*route.negotiationActive);
    if (motion == end) { route.negotiationActive.reset(); entity.networkState.actorVelocity = {}; continue; }
    const auto elapsed = now - route.negotiationStartedAt;
    const auto previous = entity.currentOrigin;
    auto position = motion->second.position(elapsed);
    for (axis = 0; axis < 3; ++axis) position[axis] += route.negotiationOffset[axis];
    entity.currentOrigin = position; entity.networkState.origin = position;
    // Map-authored facing, not velocity yaw: small sideways root offsets
    // during the climb must not spin it.
    entity.currentAngles[1] = motion->second.facingYaw;
    entity.networkState.angles = {0.0f, motion->second.facingYaw, 0.0f};
    for (axis) entity.networkState.actorVelocity[axis] = (position[axis]-previous[axis])*1000.0f/frameMilliseconds;
    const auto walkingExit = elapsed >= motion->second.walkingHandoff;
    entity.networkState.actorAnimIndex = walkingExit ? zmActorWalkAnim_ : motion->second.animation;
    entity.networkState.actorAnimStartTime = route.negotiationStartedAt + (walkingExit ? motion->second.walkingHandoff : 0u);
    ...
}
```

### 10.2 十一层

```text
1. **一次测量的协商拥有位移【与】动画**
2. ⇒ **重规划、地面对齐与普通的 18 单位步进绝不能打断它**
3. ⇒ **位置来自 `motion->second.position(elapsed)`**（参数化曲线）
4. ⇒ **加 `negotiationOffset`**（实体自己的偏移）
5. ⇒ **朝向用【地图作者化的】 `facingYaw`，不是速度 yaw**
6. ⇒ **"爬升中小的侧向根偏移绝不能让它旋转"**
7. ⇒ **速度 = 实际位移 / 帧时长**（不是曲线导数）
8. ⇒ **动画在 `walkingHandoff` 处从"协商动画"切到"行走动画"**
9. ⇒ **而 `animStartTime` 也相应偏移**（保持相位连续）
10. ⇒ **走完后重新推导朝向（`atan2`）**
```

### 10.3 而 **"朝向用地图作者化的 facingYaw 而不是速度 yaw"**

**✅ 一个**极精细的区别**。**

**⇒ 三层**：

```text
1. 爬窗/翻越时根有小的侧向偏移
2. ⇒ **若用速度 yaw ⇒ 会旋转**
3. ⇒ **所以用地图作者的 facingYaw**
```

**✅ 与 §354 的"`nearestPlayerDistance` 不数 Z"**同族（**第三次"故意忽略一个信号"**）。**

### 10.4 而**"速度 = 实际位移/帧时长"而不是曲线导数**

**⇒ 三层**：

```text
1. `position(elapsed)` 是一条曲线
2. ⇒ **理论上速度是它的导数**
3. ⇒ **而这里用【相邻帧的差】**
4. ⇒ **所以是有限差分**（与客户端看到的一致）
```

**✅ 一个**"报告看到的东西而不是理论"**的选择。**

**⚠ 而若帧时长变化，差分速度会抖动。**

**✅ 与 §355 二.7 的"时间补偿"配合（`* 1000/frameMilliseconds`）。**

### 10.5 而**"18 单位步进"**

**⇒ 三层**：

```text
1. 普通步进每步 18 单位
2. ⇒ **而 §355 二 说行走速度 79 单位/秒**
3. ⇒ **79/秒 ÷ 20Hz = 3.95 单位/帧**
```

**⚠ 所以"18 单位"是**另一条路径**（可能是航点到达半径）。**

**⇒ 与 §354 的 `SvActorNodeSearchRadius`**可能相关。**

### 10.6 而**协商结束后的完整重置（九项）**

```php
route.negotiationCompleted = route.negotiationActive;
route.previousNode = route.negotiationActive->second;
route.negotiationActive.reset();
route.nodes.clear();
route.cursor = 0;
route.planned = false;
route.wallFollowWaypoint.reset();
route.wallFollowSign = 0;
route.blockedCandidate.reset();
route.directPursuitClear = false;
entity.networkState.actorVelocity = {};
entity.networkState.actorAnimIndex = zmActorWalkAnim_;
entity.networkState.actorAnimStartTime = now;
```

**⇒ 十二项重置。**

**✅ 而注释解释理由：**

```php
// Retail negotiation cleanup does not continue the route which
// led INTO the traverse. OpenBLOPS Actor_Negotiation_Think sets
// pNearestNode to the negotiation end, zeros wish/velocity,
// calls Actor_RecalcPath, pops the state and repeats think. Keep
// that ownership boundary here: previousNode is the exact end
// node and an unplanned route makes the next fixed step rebuild
// from it toward the player's current node.
```

**⇒ 九层**：

```text
1. **零售的协商清理【不继续】通往翻越的那条路由**
2. ⇒ **`OpenBLOPS Actor_Negotiation_Think` 把 `pNearestNode` 设为协商结束**
3. ⇒ **清零 wish/velocity**
4. ⇒ **调 `Actor_RecalcPath`**
5. ⇒ **弹出状态并重复 think**
6. ⇒ **这里保持那个所有权边界**
7. ⇒ **`previousNode` 是精确的结束节点**
8. ⇒ **而一个【未规划的】路由让下一个固定步从它重建**
9. ⇒ **朝向玩家的当前节点**
```

**✅ 与 §343 的"`sub_7891D0` 的祖先走"**同族（**引用外部实现作为权威**）。**

**⚠ 而 `OpenBLOPS` 是**BO1 的开源实现**。**

**⇒ 与本项目的 `IW4X`/`CoD4X` 层级**不同**（这是**BO 系**）。**

**✅ 而注释说"保留那个所有权边界" ⇒ **有意的对齐**。**

## 十一、关键结论

1. **⭐⭐ "0.079 而不是 0.385 —— 12.33 的速度错了 4.8 倍"`**。
2. **`1,063` 条零售轨、`259,968` 个真的 100ms 断言、中位数 `7.9` 单位、p25 `7.0`、p75 `8.2`**。
3. **12.33 的带（36..41 单位）只覆盖移动断言的 `0.7%`，而真实的带（6..10）覆盖 `46.8%`** —— **小样本 + 分布偏移**（第二次采样罪）。
4. **"它是平的：三个捕获的每个四分之一都是 78-80 单位/秒 ⇒ 没有回合缩放"`** —— 主动排除混淆变量。
5. **"在 385 时脚会打滑"`** —— 第三次"动画与位移不同步"。
6. **`0.079 × frameMilliseconds` 是时间补偿的**（不依赖帧率）。
7. **⭐ "死者先处理，在任何别的东西移动它之前"（12.161）`**。
8. **`SV_IsEntityDamageStateValid` 拒绝注册非正血量但伤害 pass 留下记录** —— 一个**注册严、运行宽**的两阶段设计。
9. **死亡分支的十一项初始化**（速度/碰撞/`solid`/`actorField00AC` 清零 + 取 electrical/headless + 选死亡）。
10. **"opt-in 表现层把所有权转移到一个【有界的尸体池】"`**。
11. **电击序列的三段时间线**（循环 → 倒下 → 释放）。
12. **"一个延迟的服务器帧仍给倒下片段完整时长"（`retireAt = now + downMilliseconds`）** —— 与 §354 的修复动画用 `started`（可快进）**不同的选择**。
13. **⭐⭐ "每隔 5 帧而不是前 40 帧"** —— 前 40 帧在 20Hz 下只是头两秒。
14. **"从这个日志引用的每一个 actor 位置都是玩家完成加载之前的，包括那些被用来说『actor 生成在很远的地方』的"`** —— **最尖锐的自我推翻**（第四次）。
15. **"『僵尸没有移动』有半打原因而它们从外面无法区分 ⇒ 每帧一行命名是哪一个"`** —— 第三次"命名而不是计数"。
16. **`playerOriginReport` 打印两个位置**（`ps` = `playerState.origin` / `ent` = `entity.currentOrigin`）以确定**路由器用的是哪一个**。
17. **⭐ "在同一个稳定顺序里处理 actor"** —— `entities_` 是无序的，迭代哈希表让**跟随者先动而领导者移进它** ⇒ **逐字节相同的堆**。
18. **"排序这个小 actor 集合让既有的单向队列不变式成真"`** —— 一个**极简的防重叠**（低编号先走）。
19. **`actorRoutes_` 每帧清理**（号复用 ⇒ 死 actor 的路由被下一个继承）—— **第四次"号复用"**。
20. **"没有目标就站着不动"：factory 的 `69` 个生成器里有 `8` 个不命名目标，而走到臆造处正是【穿墙行为】"`** —— 第十四次"不要猜"。
21. **"一次测量的协商拥有位移【与】动画"** —— 重规划/地面对齐/18 单位步进都不得打断。
22. **"朝向用地图作者化的 `facingYaw` 而不是速度 yaw，因为爬升中小的侧向偏移绝不能让它旋转"`** —— 第三次"故意忽略一个信号"。
23. **速度用【相邻帧差分】而不是曲线导数**（与客户端看到的一致）。
24. **协商结束时十二项重置**，理由引用 **`OpenBLOPS Actor_Negotiation_Think`**（BO1 开源实现，与本项目的 IW4X/CoD4X 层级不同）。

## 十二、未闭合点

- `SvActorCorpseMilliseconds` 的值。
- `SV_ZmChooseDeath` 的五个参数语义。
- "18 单位步进"与 79 单位/秒的关系。
- `negotiationMotion` 曲线的构造来源。
- `OpenBLOPS` 与本项目参照体系的层级关系。
- `sv_snapshot_mp.cpp` 14000 行之后未读取（27,016 行，进度 52%）。
