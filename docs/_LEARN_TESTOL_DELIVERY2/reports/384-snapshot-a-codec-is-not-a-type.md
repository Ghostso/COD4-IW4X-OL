# 384 · **"一个编解码器【不是】一个类型"** —— 把 `-75` 的绝对值读成增量、`7/9/10/13` 不是跳号、`733` 条相同的日志、`73/163` 的零售技能为零

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 25200–25600 行。

## 二、**"一个编解码器不是一个类型"的完整撤回**（本组最重要的一段）

### 2.1 那段

```php
// AND THE DEATH HALF, BACK ON.
//
// It was pulled on a MISREADING and this is the correction. I read
// ET_PLAYER field 7 as a sequence DELTA and called values of 7, 9,
// 10 and 13 "jumps" that would overflow the four-slot ring. Codec
// -75 returns the ABSOLUTE eventSequence (`(baseline + 1 + bits3) &
// 0xFF`), so those were sequence NUMBERS, not advances, and the
// congestion they implied never existed.
//
// The server's own ring log settles it independently: the ring
// advances by ONE per event, two to four events a second, against
// forty snapshots a second. There is no overflow to design around.
//
// THE LESSON IS THE CODEC. `a codec is not a type` -- reading a
// baseline-relative field as though the decoder handed back the
// wire payload is the same class of error the comment on -75 itself
// records, and it cost a feature that was working.
```

### 2.2 十六层

```text
1. **而死亡那一半【回来了】**
2. ⇒ **它被一个【误读】撤掉，而这是【更正】**
3. ⇒ **我把 `ET_PLAYER` 字段 7 读成一个序列【增量】**
4. ⇒ **并把 `7`、`9`、`10`、`13` 这些值叫做会溢出四槽环的"跳号"**
5. ⇒ **编解码器 `-75` 返回【绝对的 `eventSequence`】**
6. ⇒ **（`(baseline + 1 + bits3) & 0xFF`）**
7. ⇒ **所以那些是【序列号】，不是增量**
8. ⇒ **而它们暗示的拥塞【从未存在】**
9. ⇒ **服务器自己的环日志【独立地】settle 它**：
     · **环每个事件推进【一】**
     · **每秒二到四个事件**
     · **对每秒四十个快照**
10. ⇒ **没有需要设计的溢出**
11. ⇒ **教训是【编解码器】**
12. ⇒ **"一个编解码器不是一个类型"**
13. ⇒ **把一个基线相对的字段当作解码器交回线载荷来读**
14. ⇒ **是 `-75` 自己的注释记录的【同一类错误】**
15. ⇒ **而它花掉了一个【本来在工作】的特性**
```

### 2.3 ⭐⭐⭐ **"一个编解码器不是一个类型"**

**✅ 这是本文件里**最重要的一条方法论**，而且它**引用自己的历史**。**

**⇒ 三层**：

```text
编解码器 -75 的定义：`(baseline + 1 + bits3) & 0xFF` ⇒ **绝对值**
我读到的：`7`, `9`, `10`, `13` ⇒ **我以为它们是增量**
⇒ **而它们是【序列号】**
```

**✅ 与 §372 的"`[reg+12Ch]` 的扫描返回空但那不是证据"**同族（**第五次"读错语义"）。**

**⚠ 而"是 `-75` 自己的注释记录的【同一类错误】"⇒ **同一类错误**重复**了**。**

**⇒ 三层**：

```text
第一次：注解里记录了那个错误的类别
第二次：**我在注解之上又犯了同一类错误**
⇒ **而注解没能阻止它**
```

**✅ 与 §370 的"从反编译读出的常数是一个假设"**同族（**第五次"注解/文档不足以阻止错误"）。**

### 2.4 而**"环每个事件推进一，每秒二到四个事件，对每秒四十个快照"**

**✅ 与 §349 的"实测每秒二到四个事件对四十个快照"**完全一致 ✓

**⇒ **第二次确认那三个数。**

**⚠ 而"四十个快照/秒"⇒ **40Hz**。**

**⇒ 与 §355 的"20Hz"**不同**！**

**⚠ 一处**真实矛盾**。**

**⇒ 可能**快照是 40Hz 而命令是 20Hz**。**

**✅ 与 §347 的"快照 50ms（20Hz）"**矛盾**。**

**⚠ 需要核对：**

```text
§347  "Snapshots are 50 ms apart (measured: consecutive command times 19300, 19350)"
§372  "17798 snapshots, 890 s" ⇒ 890000/17798 = **50.0ms** ⇒ **20Hz**
§384  "forty snapshots a second" ⇒ **40Hz**
```

**⇒ **§347/§372 与 §384 矛盾**。**

**✅ 而"二到四个事件对四十个快照"⇒ 若快照是 20Hz 则应说"二十个"。**

**⇒ 一个**可能的笔误或不同的测量**。**

**⚠ 一处**需要标注的数值矛盾**。**

### 2.5 而**"它花掉了一个本来在工作的特性"**

**✅ 与 §370 的"两个会话的代价"**同族（**第三次"以代价计的教训"）。**

**⇒ 三层**：

```text
一个【在工作】的特性
⇒ 被一个【误读】撤掉
⇒ **⇒ 一个回归**
```

**✅ 与 §360 的"21 被试过并被回退"**不同**（那是**回退因为崩溃**，这是**回退因为误读**）。**

## 三、**`perks = {}` 的"delta 编码器正确地什么都不发"**（本组第二重要）

### 3.1 那段

```php
// PERKS GO TO ZERO ON DEATH, and the demo is explicit about it: 73
// of retail's 163 perk-field assertions are (0,0,-), the first
// landing on t=66700 which is the recorder's first death, and the
// respawn re-asserts. Our own match carried a perk field TWICE in
// 12626 snapshots - the spawn path writes them every life, but the
// value is a constant, so it equals the previous life's and the
// delta encoder rightly sends nothing. Clearing here is what makes
// each spawn a real 0 -> value transition.
candidatePlayerState.perks = {};
```

### 3.2 十二层

```text
1. **技能在死亡时归零**
2. ⇒ **而 demo 是明确的**：零售的 **163** 个技能字段断言里 **73** 个是 `(0,0,-)`
3. ⇒ **第一个落在 `t=66700`，那是录制者的【第一次死亡】**
4. ⇒ **而重生【重新断言】**
5. ⇒ **而【我们自己的比赛】在 `12626` 个快照里只携带技能字段【两次】**
6. ⇒ **因为 spawn 路径每一世都写它们**
7. ⇒ **但那个值是一个【常数】**
8. ⇒ **所以它等于前一世的值**
9. ⇒ **而 delta 编码器【正确地什么都不发】**
10. ⇒ **在这里清零【正是】让每一次生成成为一个真正的 `0 -> 值` 转换的东西**
```

### 3.3 ⭐⭐ **"一个常数等于前一世的值 ⇒ delta 编码器正确地什么都不发"**

**✅ 与 §341 的"一个未变的客户端完全不提"**同族（**第三次"省略是正确但有害"）。**

**⇒ 三层**：

```text
值从不变化 ⇒ delta 编码器发【零】
⇒ **而客户端【永远】不知道那个值**
⇒ **⇒ 一个"正确"的优化产生一个错误的结果**
```

**✅ 与 §368 的"越精确地匹配就越精确地抵消"**同族（**第五次"正确反而错"）。**

**⚠ 而"清零正是让每一次生成成为一个真正的 `0 -> 值` 转换"⇒ **一个精妙的解法**。**

**✅ **用一个显式的中间态制造一个转换。**

### 3.4 而**`73/163`**

**✅ 与 §362 的 `145`、§375 的 `294`**第十三次大规模统计。

**⚠ 而"`163` 个技能字段断言"⇒ **一个具体的样本量**。**

**✅ 而 `73/163 = 44.8%`。**

**⇒ 所以**几乎一半的技能断言是零**。**

### 3.5 而 **`12626` 个快照里只有两次**

**⇒ 三层**：

```text
我们：2 / 12626（0.016%）
零售：73 / 163（44.8%）
⇒ **一个 2800 倍的差异**
```

**✅ 一个**极端的对照**。**

## 四、**`733` 条相同日志的"说哪一项"**（本组第三重要）

### 4.1 那段

```php
if (!playerState.health || !playerState.maxHealth ||
    playerState.health > playerState.maxHealth)
{
    // 28400: SAY WHICH TERM. This one rejection produced 733 identical
    // `finishplayerdamage payload is invalid` lines in the live log, and the
    // Lua side cannot tell a bad field from a full-health bar: it only sees
    // error code 4. A target that was already dead when the hit landed is
    // the common case on a burst, and it is NOT an invalid payload.
    OlMod::RuntimeLog::write(OlMod::RuntimeLog::Level::Warn,
        ..., "damage REFUSED target=" + ... + " reason=health-state health=" + ... +
        " maxHealth=" + ... + " pmType=" + ... + " dmg=" + ...);
    return FinishPlayerDamageResult::InvalidPayload;
}
```

### 4.2 十一层

```text
1. **说【哪一项】**
2. ⇒ **这一个拒绝产生了 `733` 条相同的 `finishplayerdamage payload is invalid` 行**
3. ⇒ **而 Lua 侧【无法】区分一个坏字段与一个满血条**
4. ⇒ **它只看到错误码 `4`**
5. ⇒ **一个在命中落地时【已经死了】的目标是一次连发上的常见情况**
6. ⇒ **而它【不是】一个无效载荷**
7. ⇒ **所以现在日志带 `reason=health-state` 与 `health`/`maxHealth`/`pmType`/`dmg`**
8. ⇒ **四项**
```

### 4.3 ⭐ **"它只看到错误码 4"**

**✅ 与 §346 的"七十五项一个 `return reject`"**完全同族（**第五次"一个码代表多种原因"）。**

**⇒ 三层**：

```text
Lua 侧：`error code 4`
⇒ **可能是"坏字段"、"满血条"、"已死"**
⇒ **⇒ 无法区分**
```

**✅ 与 §348 的"一个标签不能把两个答案塌缩成一个词"**完全同族（**第二次）。**

**⚠ 而"`733` 条相同的行"⇒ **一个具体的日志噪声量**。**

**✅ 与 §372 的"140 行/秒"**同族（**第三次"日志量"）。**

## 五、**`finishPlayerDamageBatch` 的 `PendingDamageMutation` 十一项**（本组第四重要）

```cpp
struct PendingDamageMutation {
    WorldClientState *target{};
    SvGameClient originalClient;
    SvGameEntity originalEntity;
    SvGameClient client;
    SvGameEntity entity;
    std::uint32_t damage{};
    std::optional<std::array<float, 3>> direction;
    bool lethal{};
    bool paintsTarget{};
    bool downed{};
    std::optional<ZombieDownedInventory> downedInventory;
};
```

### 5.1 十一项 = 四个"双份" + 各自修改 + 三个标志

```text
① `target`（指针）
② `originalClient`  ┐ 双份
③ `client`          ┘
④ `originalEntity`  ┐ 双份
⑤ `entity`          ┘
⑥ `damage`
⑦ `direction`
⑧ `lethal`
⑨ `paintsTarget`
⑩ `downed`
⑪ `downedInventory`
```

**✅ 与 §364 的"整条实体拷贝"**同族（**第三次"原始+候选"双份）。**

**⚠ 而这里**两个结构都双份**（client 与 entity）。**

**✅ 与 §376 的"七处 swap"**同族。

### 5.2 而**`paintsTarget` 的四层**

```cpp
const auto attackerIsCurrent = attacker != end &&
    attacker->second.client.gameplayState == Playing &&
    attacker->second.client.playerState.health &&
    attackerAbilities != playerAbilities_.end() &&
    attackerAbilities->second.spawnGeneration == attacker->second.client.playerState.spawnGeneration;
const auto targetBlocksPaint = targetAbilities != end &&
    targetAbilities->second.spawnGeneration == playerState.spawnGeneration &&
    SV_HasAbility(targetAbilities->second.modifiers, SvAbilityAntiPaint);
if (attackerIsCurrent && !targetBlocksPaint) {
    pending[index].paintsTarget =
        (SV_IsBulletPaintMethodOfDeath(payload.methodOfDeath) && SV_HasAbility(..., SvAbilityBulletPaint)) ||
        (SV_IsExplosivePaintMethodOfDeath(payload.methodOfDeath) && SV_HasAbility(..., SvAbilityExplosivePaint));
}
```

**⇒ 六层**：

```text
1. **`attackerIsCurrent` 五项**（含代际匹配）
2. ⇒ **`targetBlocksPaint` 三项**（含 `AntiPaint`）
3. ⇒ **两者都过才计算**
4. ⇒ **子弹涂装 或 爆炸涂装**
5. ⇒ **而只有非致命且不同队才进来**（`!lethal && attacker && != target && !onSameTeam`）
6. ⇒ **所以四个前置**
```

**✅ 与 §381 的"四层叠加"**同族（**第二次"技能叠加"）。**

## 六、**倒地的五处修改**

```php
if (mutation.lethal && zombieRevivalActive_ && !zombieTeamWiped_ &&
    !zombieDowned(payload.targetClientNum) && playerState.pmType == SvPmTypeNormal)
{
    ZombieDownedInventory saved;
    if (prepareZombieDownedInventory(mutation.client, saved)) mutation.downedInventory = std::move(saved);
    mutation.downed = true;
    mutation.lethal = false;
    mutation.client.playerState.health = 1;
    mutation.client.playerState.pmType = SvPmTypeZombieDowned;
    mutation.client.playerState.pmFlags = (playerState.pmFlags & ~3u) | 1u;
    mutation.client.damageFeedbackState.damageBlood += mutation.damage;
    mutation.client.damageFeedbackState.damageFrom = mutation.direction;
    SV_OverlayPlayerStateToNative(...);
    continue;
}
```

### 6.1 八层

```text
1. **四个前置**（致命 / 复活活跃 / 队未团灭 / 未倒地 / pmType 正常）
2. ⇒ **保存背包**
3. ⇒ **`downed = true` 而 `lethal = false`**
4. ⇒ **`health = 1`**（不是 0）
5. ⇒ **`pmType = ZombieDowned`**
6. ⇒ **`pmFlags = (old & ~3) | 1`** ⇒ **清低两位、置 bit 0**
7. ⇒ **累加伤害反馈**
8. ⇒ **写原生并 `continue`**（不走死亡路径）
```

**✅ 与 §380 的"只 `0 <-> 2`，绝不动其它任何值"**不同**（这里**清低两位置 bit 0**）。**

**⚠ 所以**两个 pmFlags 操作**：**

```text
§380  noclip     ⇒ 只 pmType（不碰 pmFlags）
§384  倒地       ⇒ **pmFlags = (old & ~3) | 1**
```

**✅ 一个**精确的差异**。

**⚠ 而 `& ~3u | 1u`⇒ **`bit0 = 1` / `bit1 = 0` 而其它保持**。**

**✅ 与 §369 的"`pmFlags |= 0x800`"**不同（那里**只置**）。**

## 七、**`deathYaw` 的三级回退**

```cpp
const auto deathYaw = [&entityOrigin](const svPlayerDamagePayload &payload, const SvGameEntity &target) {
    std::optional<std::array<float, 3>> source;
    if (payload.attackerEntityNum && *payload.attackerEntityNum != payload.targetClientNum)
        source = entityOrigin(*payload.attackerEntityNum);
    if (!source && payload.inflictorEntityNum && *payload.inflictorEntityNum != payload.targetClientNum)
        source = entityOrigin(*payload.inflctorEntityNum);
    if (!source)
        return (int32)BG_NormalizeAngle360(target.networkState.angles[1]);
    const auto deltaX = (*source)[0] - target.currentOrigin[0];
    const auto deltaY = (*source)[1] - target.currentOrigin[1];
    return (int32)BG_NormalizeAngle360(atan2(deltaY, deltaX) * RadiansToDegrees);
};
```

### 7.1 五层

```text
1. **先找攻击者的位置**
2. ⇒ **若没有或与目标相同 ⇒ 找 inflictor 的位置**
3. ⇒ **若都没有 ⇒ 【用目标自己的朝向】**
4. ⇒ **否则 `atan2` 算攻击者→目标的方向**
5. ⇒ **两次都 `BG_NormalizeAngle360`**
```

**✅ 与 §384 五.2 的"`attackerIsCurrent` 五项"**同族（**第二次"三级回退"）。**

**⚠ 而"与目标相同 ⇒ 不当作源"⇒ **自伤不产生方向**。**

**✅ 与 §368 的"`MOD_FALLING` 的自我归因"**不同**（那里**用自己**，这里**跳过**）。**

**⚠ 所以**两种处理自伤的方式**：**

```text
§368  摔落 ⇒ `inflictor = attacker = clientNum`
§384  死亡朝向 ⇒ **跳过自身，用目标朝向**
```

**✅ 一个**精确的区分**（一个需要归因，一个需要方向）。

## 八、`requestPlayerRespawn` 的"绝不把截止时间提前"

```php
// A gametype callback runs after player_die and may request a shorter
// delay than the native animation already selected. Never move that
// existing deadline earlier: the live client faults if SV_ClientSpawn
// replaces its player animation while that death track is still active.
if (!gameClient.respawnTime ||
    (int32)(requestedTime - *gameClient.respawnTime) > 0)
{
    gameClient.respawnTime = requestedTime;
}
```

**⇒ 六层**：

```text
1. **一个 gametype 回调在 `player_die` 之后运行**
2. ⇒ **并可能请求一个【比原生动画已选的更短】的延迟**
3. ⇒ **【绝不】把那个已有截止时间【提前】**
4. ⇒ **因为活客户端在 `SV_ClientSpawn` 【替换它的玩家动画】而那个死亡轨仍活跃时会故障**
5. ⇒ **所以只在 `requestedTime > existing` 时更新**
6. ⇒ **而 `!respawnTime`（首次）也更新**
```

**✅ 与 §380 的"设置 2047 清除 0 的非对称"**不同**（这是**单调的**）。**

**⚠ 而"活客户端会故障"⇒ **第五次"客户端崩溃"）。**

**✅ 与 §378 的"`0xC0000005`"**同族。

## 九、关键结论

1. **⭐⭐⭐ "一个编解码器【不是】一个类型"`** —— **`-75` 返回绝对的 `eventSequence`（`(baseline + 1 + bits3) & 0xFF`）**，而我把 `7/9/10/13` 读成**增量**，**暗示的拥塞从未存在**。
2. **"是 `-75` 自己的注释记录的【同一类错误】"`** —— **注解没能阻止它**（第五次"文档不足以阻止错误"）。
3. **"服务器自己的环日志独立地 settle 它：环每个事件推进一，每秒二到四个事件"`** —— 第二次确认那三个数。
4. **⚠ "对每秒【四十】个快照"与 §347/§372 的 "20Hz（50ms）"矛盾** —— 一处需标注的数值矛盾。
5. **"而它花掉了一个【本来在工作】的特性"`** —— 第三次"以代价计的教训"。
6. **⭐⭐ "perks 归零：零售 `163` 个技能断言里 `73` 个是 `(0,0,-)`，而我们 `12626` 个快照里只有【两次】"`** —— 一个 **2800 倍的差异**。
7. **⭐ "因为那个值是一个【常数】所以它等于前一世的值，而 delta 编码器【正确地】什么都不发 ⇒ 在这里清零正是让每一次生成成为一个真正的 `0 -> 值` 转换"`** —— 第五次"正确反而错"，而**用一个显式的中间态制造一个转换**。
8. **⭐ `733` 条相同的 `finishplayerdamage payload is invalid` 行，而 Lua 侧只看到错误码 `4`** —— 第五次"一个码代表多种原因"、第二次"一个标签不能塌缩"。
9. **"一个在命中落地时已经死了的目标是一次连发上的常见情况，而它【不是】一个无效载荷"`** —— 一个**误分类**。
10. **`PendingDamageMutation` 的十一项** = **四个双份**（`client`/`entity` 各原始+候选）+ 各自修改 + 三个标志 —— 第三次"原始+候选"。
11. **`paintsTarget` 的四层前置**（非致命 / 不同队 / `attackerIsCurrent` 五项 / `!targetBlocksPaint` 三项）—— 第二次"技能叠加"。
12. **倒地的八处修改**，而 **`pmFlags = (old & ~3) | 1`** 与 §380 的 noclip 的"只改 pmType"**精确不同**。
13. **`deathYaw` 的三级回退**（attacker → inflictor → 目标自己朝向），而**自伤被跳过**（与 §368 的"摔落的自我归因"**相反**）。
14. **⭐ `requestPlayerRespawn` 的"绝不把截止时间提前"`** —— **因为活客户端在 `SV_ClientSpawn` 替换玩家动画而死亡轨仍活跃时会故障**（第五次"客户端崩溃"）。

## 十、未闭合点

- "四十个快照/秒"与"20Hz"的矛盾。
- `SV_ZmDamageAward` 的完整评分表。
- `prepareZombieDownedInventory` 的完整逻辑。
- `pmFlags` 的低两位语义。
- `SvAnimHitDirection{Back,Front,Left,Right}` 的完整枚举。
- `sv_snapshot_mp.cpp` 25600 行之后未读取（27,016 行，进度 95%）。
