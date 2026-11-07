# 422 · **"命名它是什么而不是命名它写的那两个字段"** —— `setPlayerMatchEndFreeze` 的命名纪律、`pmove` 会把人走出位置、以及 `390` 个公开方法的世界层

## 一、范围

本报告学习 `sv_snapshot_mp.hpp` 3620–3950 行（`SvServerWorld` 的实体/事件/Factory/脚本玩家接口）。

## 二、**`setPlayerMatchEndFreeze` 的命名纪律**（本组最重要的一段）

### 2.1 那段

```php
// Puts one client into the end-of-match state. Named after what it is
// rather than after the two fields it writes, because a caller has no
// business knowing that intermission IS pm_type 5 plus eFlags 16.
// The camera is optional so a map without the entity still gets the
// pm_type/eFlags half rather than nothing.
// Hold a player where they stand for the end-of-match wait. Captures
// the position on the first call and re-applies it every frame after,
// because pmove rebuilds playerState and would walk them off it.
[[nodiscard]] bool setPlayerMatchEndFreeze(std::uint32_t clientNum);
```

### 2.2 十六层

```text
1. **把一个客户端放进【比赛末状态**】**
2. ⇒ **按【它是什么**】命名，而不是按【它写的那两个字段**】**
3. ⇒ **因为【一个调用方【没有义务**】知道"中场休息**就是 `pm_type 5` 加 `eFlags 16`**】
4. ⇒ **相机是【可选的**】**
5. ⇒ **⇒ 所以【一张没有那个实体的地图仍然得到 `pm_type`/`eFlags` 那一半**】而不是什么都没有**
6. ⇒ **把一个玩家【保持在他站着的地方**】度过比赛末等待**
7. ⇒ **⇒ 在【第一次调用时捕获位置**】**
8. ⇒ **并【在之后的每一帧重新应用它**】**
9. ⇒ **因为 `pmove` **重建 `playerState` 并会【把他们走出那个位置**】**
```

### 2.3 ⭐⭐⭐ **"调用方没有义务知道中场休息就是 pm_type 5 加 eFlags 16"**

**✅ 这是本报告里**最重要的一条命名判据**。**

**⇒ 三层**：
```text
按字段命名：`setPlayerPmType5AndEFlags16()` ⇒ **泄露实现**
按意图命名：`setPlayerMatchEndFreeze()` ⇒ **只表达意图**
⇒ **⇒ 所以【名字应该描述【结果**】不是【机制**】】
```

**✅ 与 §412 的"`SvPmFlagsMatchEndFrozen` 的名字与真实用途不符"**不同（**那是名字误导，这是名字正确抽象**）。

**⇒ 三层**：
```text
§412  `SvPmFlagsMatchEndFrozen` ⇒ **名字说是"匹配结束冻结"而 2697 说也用于 `spawn protection`** ⇒ **名字太窄**
§422  `setPlayerMatchEndFreeze` ⇒ **名字说是"比赛末冻结"而这个函数确实只做那件事** ⇒ **名字精确**
⇒ **⇒ 所以【名字的抽象层级要匹配函数的范围**】
```

**✅ ⭐⭐ **一个"名字抽象层级"的对照**。

**⚠ 而"`pm_type 5` 加 `eFlags 16`"⇒ **与 §416 的 `SvPmTypeIntermission = 5`、`SvEFlagsIntermission = 0x10 = 16`**完全闭合 ✓

**⇒ 三层**：
```text
§416  `SvPmTypeIntermission = 5`、`SvEFlagsIntermission = SvEFlagsNoDraw = 0x10`
§422  **"intermission IS `pm_type 5` plus `eFlags 16`"**
⇒ **⇒ 完全一致**
```

**✅ ⭐ **一个跨报告的常量闭合**。

### 2.4 而**"pmove 重建 playerState 并会把他们走出那个位置"**

**✅ 与 §421 的"世界从 pmove 重建每个客户端的 playerState"**完全同源 ✓

**⇒ 三层**：
```text
§421  一次单写会在下一帧被覆写
§422  **不重新应用位置 ⇒ pmove 【会把人走出去**】
⇒ **⇒ 同一个架构事实的两次应用**
```

**✅ ⭐⭐ **一个"必须每帧重新应用"的三例**（`noclip` / 武器授予 / 冻结）。

**⇒ 三层**：
```text
`noclip`      ⇒ 记录 + 每帧应用（`SvNoclipDefaultHoldMilliseconds = 1500`）
武器授予      ⇒ 记录 + 每次 pmove 后断言
`matchEndFreeze` ⇒ **捕获位置 + 每帧应用**
⇒ **⇒ 三个"捕获 + 重放"的模式**
```

**✅ ⭐ **一个"捕获+重放"的三例表**。

## 三、**工厂的无盈利与原子性**（本组第二重要）

### 3.1 那段

```php
// Atomically spends Factory battery and removes every brush/script model
// named by a door/debris trigger's target key. A failed native publication
// rolls the whole group back and spends nothing.
[[nodiscard]] bool purchaseMapTargetGroup(
    std::uint32_t clientNum, std::uint32_t cost, std::string_view targetName);

// Opens an authored door/debris target group without charging a player.
// Factory's two electric doors take this path together on the power-switch
// frame; the retail demo proves they are not separate 10000 purchases.
[[nodiscard]] bool openMapTargetGroup(std::string_view targetName);
```

### 3.2 十四层

```text
1. **原子地花工厂电池并移除【一个门/碎片触发器的目标键命名的每一个 brush/script model**】**
2. ⇒ **一次失败的【原生发布】把【整个组回滚**】而【一分钱不花**】**
3. ⇒ **⇒ 所以 `purchaseMapTargetGroup` 是一个【全有或全无**】的事务**
4. ⇒ **而 `openMapTargetGroup` 【打开一个作者编写的组而不向玩家收费**】**
5. ⇒ **Factory 的两扇电动门【在电源开关那一帧【一起】走这条路径**】**
6. ⇒ **⇒ 而【零售 demo 证明它们不是【两个 `10000` 的购买**】】**
```

### 3.3 ⭐⭐⭐ **"零售 demo 证明它们不是两个 10000 的购买"**

**✅ 这是本报告里**最重要的一条"用 demo 否证一个模型"**。**

**⇒ 三层**：
```text
假设：**两扇门各是一次 `10000` 购买**
demo：**它们在【同一帧】一起开** ⇒ **不是两次购买**
⇒ **⇒ 所以【`openMapTargetGroup` 是【免费**的】**
```

**✅ 与 §412 的"`24` 个 `r 2` 簇的第一个前面没有 `N`"**同族（**第五次"用 demo 排除假设"）。

**⚠ 而"`10000`"⇒ **一个具体的价格**。**

**⇒ 三层**：
```text
`10000` 电池 ⇒ **`10000 * 6/5 = 12000` 原始电池**（§409 的 `6/5`）
⇒ **⇒ 两扇门 = `24000` 原始电池** ⇒ **一个玩家负担不起**
```

**✅ 与 §409 的"`BatteryMultiplier 6/5`"**完全闭合 ✓

### 3.4 而**"`changeFactoryBattery` 拒绝溢出/封顶裁剪"**

```php
// Applies one exact Factory battery debit/refund only for the current
// life. It refuses overflow/cap clipping so a failed refund is visible
// to the caller instead of silently losing currency.
[[nodiscard]] bool changeFactoryBattery(std::uint32_t clientNum,
    std::int64_t deltaRaw, std::uint8_t expectedLifeGeneration);
```

**⇒ 八层**：
```text
1. **为一个精确的工厂电池扣款/退款，【只对当前这条命**】**
2. ⇒ **它【拒绝溢出/封顶裁剪**】**
3. ⇒ **⇒ 所以【一次失败的退款【对调用方可见**】**
4. ⇒ **而不是【静默地丢失货币**】**
5. ⇒ **`expectedLifeGeneration`** ⇒ **一个代次守卫**
6. ⇒ **⇒ 所以【跨命退款被拒绝**】**
```

### 3.5 ⭐⭐⭐ **"拒绝溢出/封顶裁剪，所以一次失败的退款对调用方可见"**

**✅ 这是本报告里**最重要的一条"不静默截断"**。**

**✅ 与 §410 的"队满 ⇒ 丢弃并记一行"**、§413 的"`initialized` 三态"**同族（**第五次"静默 vs 可见"）。

**⇒ 三层**：
```text
静默裁剪：`min(battery + refund, MAX)` ⇒ **退款部分丢失而无证人**
拒绝：**返回 `false`** ⇒ **调用方必须处理**
⇒ **⇒ 所以【后者可诊断**】
```

**✅ ⭐⭐ **一个"精确算术"的实例**。

**⚠ 而"`std::int64_t deltaRaw`"⇒ **一个 64 位增量**。**

**⇒ 三层**：
```text
`deltaRaw` 是 `int64` ⇒ **可以表示一个巨大的退款**
⇒ **而【封顶检查在函数内部**】
⇒ **⇒ 所以【溢出在【这里**】被捕获而不是在调用方**
```

**✅ ⭐ **一个"在边界处检查"的实例**。

## 四、**`setPlayerScriptedPosition` 的"在 Pmove 之后重新应用"**

```php
// Drives a player along a mission-owned path while retained Pmove still
// consumes the real usercmd. The hold is re-applied after Pmove so a
// single script write cannot be erased before the snapshot is built.
[[nodiscard]] bool setPlayerScriptedPosition(
    std::uint32_t clientNum,
    const std::array<float, 3> &origin,
    std::uint8_t pmType,
    std::uint32_t pmFlags);
```

**⇒ 八层**：
```text
1. **沿一条【任务拥有的路径】驱动一个玩家**
2. ⇒ **而【保留的 Pmove 【仍然】消费真正的 usercmd**】**
3. ⇒ **⇒ 那个保持在【Pmove 之后重新应用**】**
4. ⇒ **⇒ 所以【一次脚本写【不能**】在快照被构建之前被擦除**】**
```

**✅ ⭐⭐ **"在 Pmove 之后重新应用"** —— 与 §422 二 的"每帧重新应用"**同族（**第四次）。

**⇒ 三层**：
```text
`noclip`          ⇒ 每帧（在 pmove 之前）
武器授予          ⇒ 每次 pmove 之后
`matchEndFreeze`  ⇒ 每帧（捕获 + 重放）
`scriptedPosition`⇒ **在 pmove 之后**
⇒ **⇒ 四个"重新应用"，两种时机**
```

**✅ ⭐⭐ **"在 pmove 之前 vs 之后"的区分**。

**⇒ 三层**：
```text
**之前**：`noclip`（**要让 pmove 看见它**）
**之后**：武器/位置（**要覆盖 pmove 的输出**）
⇒ **⇒ 所以【时机由"是输入还是输出"决定**】
```

**✅ ⭐⭐⭐ **一个"pmove 前后"的精确判据**。

## 五、**`setPlayerCanTakeDamage` 的"代次作用域"**

```php
// Scripted sequences such as Wetwork's helicopter flight temporarily
// protect a player without changing health or the native playerState
// image. The owner is generation-scoped side storage; a new life is
// damageable even if the previous script never reached its cleanup.
[[nodiscard]] bool setPlayerCanTakeDamage(std::uint32_t clientNum, bool enabled);
```

**⇒ 十层**：
```text
1. **脚本序列（如 Wetwork 的直升机飞行）临时保护一个玩家**
2. ⇒ **而不改变生命值或原生 `playerState` 镜像**
3. ⇒ **所有者是【代次作用域的侧存储**】**
4. ⇒ **⇒ 所以【一条新的命【是可伤害的**】**
5. ⇒ **【即使前一个脚本从未到达它的清理**】**
```

### 5.1 ⭐⭐⭐ **"即使前一个脚本从未到达它的清理"**

**✅ 这是本报告里**最重要的一条"防止脚本泄漏状态"**。**

**⇒ 三层**：
```text
风险：**脚本设置 `canTakeDamage = false` 而【脚本崩溃/中断**】⇒ **永不清理**
防护：**代次作用域 ⇒ 新命自动清零**
⇒ **⇒ 所以【一个泄漏被【死亡**】修复**】
```

**✅ 与 §412 的"死亡/重生两个边沿清空 AI 状态"**同族（**第七次"死亡是一个自然的重置点"）。

**⇒ 三层**：
```text
§412  bot 的 `lifeState` 变化 ⇒ **`walk = SvBotWalkState{}`**
§422  `setPlayerCanTakeDamage` ⇒ **代次变化 ⇒ 自动清零**
⇒ **⇒ 同一设计两处**
```

**✅ ⭐⭐ **一个"死亡即重置"的两例**。

**⚠ 而"Wetwork 的直升机飞行"⇒ **一个具体的用例**。**

**✅ 与 §408 的"Wetwork 不进竞争性 32.7 秒 outro"**配合。

## 六、**击杀回放的三个接口**

```text
setPlayerDeathView(clientNum, until)        ← 死亡视角（1.5 秒）
clearPlayerDeathView(clientNum)
setPlayerKillcamReplay(clientNum, until, deltaTime)  ← 回放窗口
clearPlayerKillcamReplay(clientNum)
playerKillcamReplay(clientNum, serverTime) const
setPlayerPrematchHold(clientNum, untilServerTime)    ← 开场保持
clearPlayerPrematchHold(clientNum)
playerPrematchHeld(clientNum) const
```

**⇒ 六层**：
```text
1. **三对（set/clear）+ 两个查询**
2. ⇒ **`deathView`**：**死亡相机窗口**
3. ⇒ **`killcamReplay`**：**回放窗口**（`deltaTime` 是 `playerState +0x0C48` 的倒带量）
4. ⇒ **`prematchHold`**：**开场保持**（"move/fire only; command time untouched"）
5. ⇒ **⇒ 三个"有期限的状态**】
```

**✅ 与 §404 的"`deathViewUntil = now + SvDeathViewMilliseconds`"**完全闭合 ✓

**⇒ 三层**：
```text
§404  `1500ms` 身体相机 ⇒ `2500ms` 回放 ⇒ `2000ms` 后延迟
§422  **三个独立的世界状态**（`deathView` / `killcamReplay` / `prematchHold`）
⇒ **⇒ 而 `prematchHold` 是【一个独立的机制**】
```

### 6.1 而**"`prematchHold` 只冻结移动与开火，不动命令时间"**

```php
// 28800: prematch control hold (move/fire only; command time untouched).
void setPlayerPrematchHold(std::uint32_t clientNum, std::uint32_t untilServerTime);
```

**⇒ 四层**：
```text
`move/fire only` ⇒ **只冻结这两个**
`command time untouched` ⇒ **【不动**命令时间**
⇒ **⇒ 所以【客户端的命令流【继续**】而【移动/开火被忽略**】**
```

**✅ ⭐⭐ **"只冻结两个而不动时间"** —— 一个**最小侵入**。

**⚠ 与 §402 的"`pmFlags |= 0x800` 让客户端停止推进命令时间"**相反**（那里**停了时间**）。

**⇒ 三层**：
```text
§402  `pmFlags 0x800` ⇒ **客户端停止推进命令时间**
§422  `prematchHold` ⇒ **命令时间不动（继续）而移动/开火被忽略**
⇒ **⇒ 两个不同的冻结机制**
```

**✅ ⭐ **一个"两种冻结"的区分**。

## 七、**`spawnObituaryEvent` 的"没有原点"**

```php
// THE KILL FEED IS AN ENTITY EVENT (section 191q). One temp entity per
// death, eType 166, carrying victim / attacker / weapon-or-means and
// nothing else -- no origin, which is why it needs no PVS and reaches
// every client. `attackerClientNum` may be EntityNumWorld for a death
// nobody owns, and may equal the victim for a suicide; CG_Obituary
// handles both and prints no line for either.
```

**⇒ 十二层**：
```text
1. **击杀提示是一个【实体事件**】**
2. ⇒ **每次死亡一个临时实体，`eType 166`**
3. ⇒ **携带【受害者 / 攻击者 / 武器或方式**】而【别的什么也没有**】**
4. ⇒ **⇒ 【没有原点，那就是为什么它不需要 PVS 并到达每一个客户端**】**
5. ⇒ **`attackerClientNum` 可以是 `EntityNumWorld`**
6. ⇒ **⇒ 对一次【没有人拥有的死亡**】**
7. ⇒ **而可以【等于受害者**】对一次自杀**
8. ⇒ **⇒ `CG_Obituary` 处理两者【并且对两者都不打印一行**】**
```

### 7.1 ⭐⭐⭐ **"没有原点，所以它不需要 PVS 并到达每一个客户端"**

**✅ 这是本报告里**最重要的一条"PVS 规避"**。**

**⇒ 三层**：
```text
有原点 ⇒ **需要 PVS 剔除** ⇒ **只有附近的客户端收到**
无原点 ⇒ **无 PVS** ⇒ **每个客户端收到**
⇒ **⇒ 所以【"没有原点"是一个【功能**】不是一个遗漏**】
```

**✅ 与 §410 的"`145` 条 obituary 对 `145` 次 `ET_PLAYER` lives"**完全闭合 ✓

**⇒ 三层**：
```text
§410  **`145` 对 `145`** ⇒ 每死一条
§422  **没有原点 ⇒ 每客户端收到** ⇒ 所以 `145` 条能被每个客户端看到
⇒ **⇒ 而 §410 的"没有 feed"是【第三个白名单**】的问题，不是 PVS
```

**✅ ⭐⭐ **一个"两个机制叠加"的完整图景**。**

### 7.2 而**"自杀与无人拥有的死亡都不打印一行"**

**⇒ 四层**：
```text
自杀（`attacker == victim`）⇒ **`CG_Obituary` 【不打印**】
无人拥有（`attacker == EntityNumWorld`）⇒ **也不打印**
⇒ **⇒ 所以【两者都是【静默的**】**
```

**✅ 与 §410 的"自杀、坠落与队友击杀各得一行"**——**矛盾？**

**⇒ 三层**：
```text
§410  **服务端【发**每死一条**（包括自杀）**
§422  **客户端【对自杀不打印**】
⇒ **⇒ 不矛盾：【服务端发，客户端选择不画**】
```

**✅ ⭐⭐ **"服务端发而客户端不画"** —— 与 §410 的"只有客户端决定是否为它画文本"**完全一致** ✓

**⇒ 三层**：
```text
§410  "A suicide, a fall and a team kill each get a line; **only the client decides whether to draw text for it**"
§422  "**`CG_Obituary` 处理两者并且对两者都不打印一行**"
⇒ **⇒ 完全一致**
```

**✅ ⭐ **一个"分层职责"的确认**。

## 八、`spawnPlayerCorpse` 的"18 个尸体号"**

```php
// OLMOD(player-corpse-pool): a corpse is a SEPARATE entity from the
// player who died, because the respawn resets the player's own entity
// and the death animation has to keep playing after it. The dm demo
// shows 18 distinct corpse entity numbers across a whole match - more
// deaths than that by far - so the policy is a fixed pool the size of
// MaximumGameClients with the oldest recycled, not a timeout nobody
// measured.
```

**⇒ 十四层**：
```text
1. **一个尸体是【与死去的玩家分离**】的实体**
2. ⇒ **因为【重生重置玩家自己的实体**】**
3. ⇒ **而【死亡动画必须在它之后继续播放**】**
4. ⇒ **dm demo 显示【一场比赛里 `18` 个不同的尸体实体号**】**
5. ⇒ **⇒ 而【死亡远多于那个**】**
6. ⇒ **⇒ 所以策略是【一个 `MaximumGameClients` 大小的固定池**】，**最旧的被回收**
7. ⇒ **而【不是一个没人测量过的超时**】**
```

### 8.1 ⭐⭐⭐ **"一个固定池而不是一个没人测量过的超时"**

**✅ 这是本报告里**最重要的一条"从数据反推机制"**。**

**⇒ 三层**：
```text
观察：**一场比赛恰好 `18` 个尸体的号**
若策略是"超时" ⇒ **号的数量取决于死亡频率** ⇒ **每场不同**
若是"固定池" ⇒ **恰好等于池大小**
⇒ **⇒ 所以【`18` 是一个池大小**】
```

**✅ ⭐⭐⭐ **"一个恰好等于某个常数的观察是一个池大小的证据"** —— 一个**极精巧的推理**。

**✅ 与 §419 的"`2→1` 而玩家在 `71`"**同族（**第六次"一个数值定案一个机制"）。

**⚠ 而"`MaximumGameClients`"⇒ **`18`**（**确认 §417 的推断**）。

**⇒ 三层**：
```text
§417  我推断 `MaximumGameClients = 18`（从 `CG_Obituary` 的夹到 `18`）
§422  **"一个 `MaximumGameClients` 大小的固定池"而 demo 显示 `18` 个尸体号**
⇒ **⇒ 所以【`18` 被两处独立确认**】
```

**✅ ⭐⭐ **一个"跨报告独立确认"**。

### 8.2 而**"重生重置玩家自己的实体"**

**✅ 与 §409 的"槽复用要清状态"**同族（**第九次"号复用"）。

**⇒ 三层**：
```text
玩家实体 ⇒ **重生时【被重置**】
尸体实体 ⇒ **一个【独立的号**】
⇒ **⇒ 所以【死亡动画不被重生打断**】
```

**✅ ⭐ **一个"分离实体"的实例**。

## 九、**`spawnScriptedMissile` 的"在 `missiles_` 之外"**

```php
// Campaign recordings contain scripted rockets whose trajectories are
// presentation, not player-owned grenade simulation. They use the
// recovered ET_MISSILE state and ordinary entity lifetime while staying
// outside missiles_, so the gameplay runner cannot collide or detonate
// them a second time.
```

**⇒ 八层**：
```text
1. **战役录像包含脚本火箭，它们的轨迹是【表现**】**
2. ⇒ **不是【玩家拥有的榴弹模拟**】**
3. ⇒ **它们用【解出的 `ET_MISSILE` 状态与普通实体生命周期**】**
4. ⇒ **⇒ 而【留在 `missiles_` 之外**】**
5. ⇒ **⇒ 所以【玩法 runner 【不能**】碰撞或引爆它们第二次**】**
```

**✅ ⭐⭐ **"留在 `missiles_` 之外，所以不能第二次引爆"** —— 一个**用数据结构隔离来防重**。

**✅ 与 §409 的"两个入口一个出口"**不同（这是**两个池**）。

**⇒ 三层**：
```text
`missiles_` ⇒ **玩法导弹**（会碰撞/引爆）
`scriptedMissiles` ⇒ **表现导弹**（不碰撞）
⇒ **⇒ 所以【同一个 eType 在两个池里有不同行为**】
```

**✅ ⭐⭐ **一个"同一个 eType 分池"的实例**。

## 十、关键结论

1. **⭐⭐⭐ "按它是什么命名，而不是按它写的那两个字段：一个调用方没有义务知道『中场休息就是 `pm_type 5` 加 `eFlags 16`』"`** —— 一个名字的抽象层级判据；与 §412 的 `SvPmFlagsMatchEndFrozen`（名字太窄）形成对照。
2. **⭐ "`pm_type 5` + `eFlags 16`"与 §416 的 `SvPmTypeIntermission = 5` / `SvEFlagsIntermission = 0x10` 完全闭合**。
3. **⭐⭐ "`pmove` 重建 `playerState` 并会把他们走出那个位置 ⇒ 在第一次调用时捕获位置并每帧重新应用"`** —— 第四个"捕获+重放"，与 §421 同源。
4. **⭐⭐⭐ 一个"pmove 之前 vs 之后"的精确判据**：**`noclip` 在 pmove **之前**（要让 pmove 看见它）；武器授予与 `scriptedPosition` 在 pmove **之后**（要覆盖 pmove 的输出）** —— **时机由"是输入还是输出"决定**。
5. **⭐⭐ `purchaseMapTargetGroup` 的全有或全无**：**"一次失败的原生发布把整个组回滚而一分钱不花"`**。
6. **⭐⭐⭐ "`openMapTargetGroup` 不收费，因为【零售 demo 证明两扇电动门不是两个 `10000` 的购买（它们在同一帧一起开）】"`** —— 第五次"用 demo 排除假设"；而 `10000 × 6/5 = 12000` 原始电池，**两扇门 `24000` 一个玩家负担不起**（与 §409 的 `6/5` 闭合）。
7. **⭐⭐ "`changeFactoryBattery` 拒绝溢出/封顶裁剪，所以一次失败的退款对调用方可见，而不是静默地丢失货币"`** —— 第五次"静默 vs 可见"。
8. **⭐⭐ "`setPlayerCanTakeDamage` 的所有者是【代次作用域的侧存储】，所以一条新的命是可伤害的【即使前一个脚本从未到达它的清理】"`** —— 第七次"死亡是一个自然的重置点"，与 §412 的 bot 状态重置同族。
9. **⭐ 击杀回放的三个独立世界状态**（`deathView` / `killcamReplay` / `prematchHold`），而 **`prematchHold` 只冻结移动与开火、【不动命令时间】**（与 §402 的 `pmFlags 0x800` 停止推进命令时间相反）。
10. **⭐⭐⭐ "击杀提示是实体事件 `eType 166`，携带受害者/攻击者/武器，【没有原点，那就是为什么它不需要 PVS 并到达每一个客户端】"`** —— **"没有原点"是一个功能不是一个遗漏**；而 §410 的"没有 feed"是第三个白名单的问题。
11. **⭐⭐ "`CG_Obituary` 处理自杀与无人拥有的死亡【并且对两者都不打印一行】"`** —— 与 §410 的"服务端发，只有客户端决定是否为它画文本"完全一致（分层职责）。
12. **⭐⭐⭐ "dm demo 显示一场比赛 `18` 个不同的尸体实体号 —— 而死死亡远多于那个 ⇒ 所以策略是一个 `MaximumGameClients` 大小的固定池，不是一个没人测量过的超时"`** —— 第六次"一个数值定案一个机制"；而 **`18` 与 §417 的 `CG_Obituary` 夹到 `18` 独立确认 `MaximumGameClients = 18`**。
13. **⭐ "一个尸体是与死去的玩家分离的实体，因为重生重置玩家自己的实体而死亡动画必须在它之后继续播放"`**。
14. **⭐⭐ "`scriptedMissiles` 留在 `missiles_` 之外，所以玩法 runner 不能碰撞或引爆它们第二次"`** —— 用数据结构隔离防重（同一个 `ET_MISSILE` 在两个池里有不同行为）。

## 十一、未闭合点

- `purchaseMapTargetGroup` 的 `10000` 价格来源。
- `clearPlayerWeaponGrant` 与 `setUnarmedSpawns` 的交互。
- 尸体池的 `MaximumGameClients = 18` 是否最终确认。
- `setPlayerScriptedPosition` 的 `pmType` 参数取值。
- `suppressPlayerCorpse` 的"28600 kill FX family"（金币/鱼/像素块/碎裂）。
- `sv_snapshot_mp.hpp` 3950 行之后未读取（**共 `4703` 行**）。
