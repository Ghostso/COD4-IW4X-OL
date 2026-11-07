# 377 · **"`0x20000` 只让 `sub_BB89E0` 跳过动画状态初始化 —— 它不阻止实体被画"** —— 死者的 `ET_PLAYER` 必须停止归档、尸体的八个环槽永不释放、按"这一世结束"而不是按"存在一具带此 `clientNum` 的尸体"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 22400–22800 行。

## 二、**`0x20000` 的两个含义的澄清**（本组最重要的一段）

### 2.1 那段

```php
// CODREF(player_die): once a client's corpse exists, retail STOPS
// archiving that client's player entity and lets the corpse be the
// body. Measured across 8 corpse spawns in the dm demo: the owner's
// ET_PLAYER assertions collapse from ~20 per 2 s to 0..6 the moment
// the corpse appears (clientNum 1: 16 -> 0, 5: 20 -> 1, 3: 20 -> 2,
// 2: 20 -> 4).
//
// This is not cosmetic. The client's draw path has NO eFlags 0x20000
// gate: sub_BA7500 sends eType 1 and eType 2 alike into sub_BB88E0,
// which draws whenever centity+0x204 bit 0 is set and picks
// clientinfo for eType 1 / corpseinfo for eType 2. 0x20000 only makes
// sub_BB89E0 skip animation-state INITIALISATION - it does not stop
// the entity being drawn. So a dead player's entity keeps rendering
// with its death animation and then TELEPORTS to the spawn point on
// respawn, which is a body that disappears no matter what the corpse
// does. Retail does not have that entity to teleport.
```

### 2.2 十六层

```text
1. **一旦一个客户端的尸体存在，零售【停止】归档那个客户端的玩家实体**
2. ⇒ **而让尸体成为那个身体**
3. ⇒ **跨 dm demo 的 `8` 次尸体生成测量**
4. ⇒ **所有者的 `ET_PLAYER` 断言从每 2 秒约 `20` 次【塌缩到】`0..6`**
5. ⇒ **在尸体出现的那一刻**
6. ⇒ **（`clientNum 1: 16→0`、`5: 20→1`、`3: 20→2`、`2: 20→4`）**
7. ⇒ **这不是装饰性的**
8. ⇒ **客户端的绘制路径【没有】 `eFlags 0x20000` 门**
9. ⇒ **`sub_BA7500` 把 `eType 1` 与 `eType 2` 一样送进 `sub_BB88E0`**
10. ⇒ **它在 `centity+0x204` 的 bit 0 被设时【画】**
11. ⇒ **并为 `eType 1` 挑 `clientinfo`、为 `eType 2` 挑 `corpseinfo`**
12. ⇒ **`0x20000` 只让 `sub_BB89E0` 跳过【动画状态的初始化】**
13. ⇒ **它【不】阻止实体被画**
14. ⇒ **所以一个死玩家的实体【继续渲染】它的死亡动画**
15. ⇒ **然后在重生时【传送到】出生点**
16. ⇒ **那是一个【无论尸体做什么都会消失】的身体**
17. ⇒ **而零售没有那个可被传送的实体**
```

### 2.3 ⭐⭐ **"`0x20000` 只跳过初始化而【不】阻止绘制"**

**✅ 这是本文件里**最重要的一个语义澄清**。**

**⇒ 三层**：

```text
§363  `0x20000` 让 `sub_BB89E0` 跳过动画状态初始化
§377  **同一个位【不】阻止 `sub_BB88E0` 绘制**
⇒ **所以两个不同的函数、同一个位**
```

**⚠ 所以**"清 `0x20000` 能让身体不消失"（§363）与"`0x20000` 不阻止绘制"（§377）**不矛盾**。**

**⇒ 三层**：

```text
§363  清 `0x20000` ⇒ **动画初始化跑** ⇒ 尸体**能动**
§377  `0x20000` 不阻止**玩家实体**被画 ⇒ **所以必须停止归档**
```

**✅ **两个不同的实体类型**（尸体 vs 玩家）、**同一个位**。**

### 2.4 而**"实体传送到出生点"**

**✅ 与 §372 的"`srvView` 站着不动而 `cmdView` 在动"**不同**。**

**⇒ 三层**：

```text
1. 死玩家的实体【仍被归档】
2. ⇒ **所以客户端一直画它**
3. ⇒ **而重生时它的 origin 变成出生点**
4. ⇒ **⇒ 身体"传送"走**
```

**✅ **一个极具体的机制**。**

**⚠ 而"无论尸体做什么都会消失"⇒ **所以修正必须在这里**（停止归档）。**

**✅ 与 §347 的"在哪里消失"**同族（**第六次"分层的可观测性"）。

### 2.5 而**四个具体的数字**

```text
clientNum 1:  16 → 0
clientNum 5:  20 → 1
clientNum 3:  20 → 2
clientNum 2:  20 → 4
```

**⇒ 三层**：

```text
1. **每 2 秒约 20 次断言 ⇒ 即 10Hz**
2. ⇒ **塌缩到 0..6**
3. ⇒ **一个剧烈的、明确的落差**
```

**✅ 与 §362 的 `145`、§375 的 `294`**第十次大规模统计。

**⚠ 而"每 2 秒 20 次"⇒ **10Hz**（而不是 20Hz）。**

**⇒ 可能因为**每 2 帧一次**。**

## 三、**八个环槽永不释放的完整事故**（本组第二重要）

### 3.1 那段

```php
// The condition is THIS LIFE being over, not "a corpse carrying this
// clientNum exists somewhere". Those read the same only until the
// client respawns. The corpse ring is eight slots that are never
// freed - retail reuses a slot after eight more deaths, and this
// server matches that - so a corpse stamped with a clientNum
// outlives that client's death by however long it takes eight more
// people to die. Keying the gate on the corpse made every player
// who had died even once permanently invisible, both to themselves
// and to everyone else, which is exactly what a live two-client
// match showed: corpses #19{client=0} #20,#21,#22{client=1} present
// simultaneously with both clients alive and neither model drawn.
```

### 3.2 十四层

```text
1. **条件是【这一世结束了】**
2. ⇒ **不是"某个携带此 `clientNum` 的尸体存在于某处"**
3. ⇒ **两者只在客户端重生之前读起来相同**
4. ⇒ **尸体环是【八个槽】而【永不释放】**
5. ⇒ **零售在【再有八个人死亡之后】复用一个槽**
6. ⇒ **而这个服务器匹配那个**
7. ⇒ **所以一个打了 `clientNum` 印记的尸体**
8. ⇒ **活得比那个客户端的死亡【久】—— 久到再有八个人死**
9. ⇒ **以尸体为门控让每一个【曾经死过一次】的玩家永久不可见**
10. ⇒ **无论对自己还是对所有人**
11. ⇒ **而那正是一场活动的双客户端比赛所显示的**：
     · **尸体 `#19{client=0}`、`#20,#21,#22{client=1}`**
     · **同时存在而两个客户端都活着**
     · **而两个模型都不被画**
```

### 3.3 ⭐⭐ **"以尸体为门控让每一个曾经死过一次的玩家永久不可见"**

**✅ 与 §360 的"实体号被复用 ⇒ 继承前一个占用者的 `+0xA0`"**同族（**第六次"号复用"）。**

**⇒ 三层**：

```text
1. 门控问"存在一具带 clientNum 的尸体吗？"
2. ⇒ **尸体环八个槽、永不释放**
3. ⇒ **所以一个旧尸体永远回答"是"**
4. ⇒ **⇒ 那个玩家永久不被归档 ⇒ 永久不可见**
```

**✅ **一个极隐蔽的、永久性的失败**。**

**⚠ 而"六次，`#19`/`#20`/`#21`/`#22`"⇒ **一个具体的比赛记录**。**

**✅ 与 §355 的"玩家的判决"**第七次。

### 3.4 而**"两者只在客户端重生之前读起来相同"**

**✅ 与 §369 的"一个有时存活的值是别的东西拥有的"**同族（**第二次"两个判据在一个窗口内等价"）。**

**⇒ 三层**：

```text
重生前：这一世结束 == 存在带此 clientNum 的尸体 ✓
重生后：**这一世没结束 而 尸体仍在** ⇒ **两者分叉**
```

**✅ **一个精确的分叉点**。**

**⚠ 而"重生"⇒ **一个具体的事件**。**

**✅ 与 §362 的"`ownerClearTime = +900ms`"**不同**（那是**拾取**）。**

## 四、**`ENDFRAME COPY` 的四段计时与 `3000ms` 的嫌疑**（本组第三重要）

### 4.1 那段

```php
// OLMOD(endframe-copy-cost): section 103. The stall watchdog resolved EIP to
// the unordered_map copy constructor reached from here, so these three lines
// are the suspect -- but WHICH of the three, and how many entries each holds,
// is not known, and a 2276-byte node times a handful of clients does not add
// up to a 3000 ms frame on its own. Measure before shrinking anything.
const auto copyBegan = std::chrono::steady_clock::now();
auto candidateClientStates = clientStates_;
auto candidateLivingWeaponChildren = livingWeaponChildren_;
...
const auto afterClientStates = std::chrono::steady_clock::now();
auto candidatePlayerTouchHandlers = playerTouchHandlers_;
const auto afterTouchHandlers = std::chrono::steady_clock::now();
auto candidateSnapshot = snapshot_;
```

### 4.2 十一层

```text
1. **停摆看门狗把 EIP 解析到【从这里的 `unordered_map` 拷贝构造函数】**
2. ⇒ **所以这三行是嫌疑**
3. ⇒ **但【哪三行里的哪一行】，以及每一个持有多少条目，【未知】**
4. ⇒ **而"一个 2276 字节的节点 × 少数几个客户端"**
5. ⇒ **【自己加不出】一个 `3000ms` 的帧**
6. ⇒ **所以在缩小任何东西之前【测量】**
7. ⇒ **三段计时**：
     · `clientStates_`
     · `playerTouchHandlers_`
     · `snapshot_`
8. ⇒ **总 >= `20ms` 且报告数 < 12 ⇒ 打一行**
9. ⇒ **格式：`ENDFRAME COPY <total> us total: clientStates <us> n=<size> | touchHandlers <us> n=<size> | snapshot <us> entities=<size>`**
```

### 4.3 ⭐ **"在缩小任何东西之前【测量】"**

**✅ 与 §355 的"不猜"**同族（**第十八次）。**

**⚠ 而"一个 2276 字节的节点 × 少数几个客户端加不出 3000ms"⇒ **一个数量级论证**。**

**⇒ 三层**：

```text
2276B × ~10 clients = ~23KB
⇒ **一个 memcpy 不可能花 3000ms**
⇒ **所以看门狗的 EIP 可能【不是】根因**
```

**✅ 一个**极有价值的自我怀疑**。**

**⚠ 而"看门狗把 EIP 解析到..."⇒ **可能是一个不精确的采样**。**

**✅ 与 §363 的"探针测到恰好一次重置"**对比** —— 那是**精确**的，这是**粗糙**的。**

### 4.4 而**"报告数 < 12"的上限**

**⇒ 三层**：

```text
1. **只报 12 次**
2. ⇒ **所以一个长期慢的情况会在 12 次后静默**
3. ⇒ **而"静默"⇒ **§372 的"失控不能是静默的"**警告的正是这个**
```

**⚠ 一处**潜在的不一致**（12 次上限**没有**"capped"提示）。**

**✅ 与 §372 的"`player-kinematics` 打印 `capped`"**对比。**

## 五、**`NO WORLD STATE` 的"静默跳过变成 `missing_playerstate`"**（本组第四重要）

### 5.1 那段

```php
if (worldClient == candidateClientStates.end()) {
    // THE SILENT SKIP THAT BECOMES `missing_playerstate`, NAMED.
    //
    // An ACTIVE client with no WORLD state gets no playerState pushed, so
    // SV_WriteSnapshot's findPlayerState returns null and the whole snapshot
    // is rejected as `missing_playerstate` -- two layers away, naming nothing.
    // That reading cost a long session on mp_battlecity: the first snapshot
    // is rejected, so the client never receives a frame to ack, so every
    // later frame is FULL (`source=none(FULL)`), so cgame discards them all
    // (section 3b's snapFlags & 0x0A), so no usercmds, so no ack -- the
    // documented FULL-forever deadlock, entered from here.
    //
    // Edge-triggered per client: the loop runs per frame and a stuck client
    // would print at 20 Hz otherwise.
    static std::array<bool, MaximumGameClients> reported{};
    if (clientNum < reported.size() && !reported[clientNum]) {
        reported[clientNum] = true;
        write(..., "NO WORLD STATE for active client ... -- gameplayState=" ... " team=" ...
            " loadoutSeq=" ... " resolvedLoadout=" ... " worldStates=" ...
            "; its snapshot will be rejected as missing_playerstate");
    }
    continue;
}
```

### 5.2 十六层

```text
1. **那个变成 `missing_playerstate` 的静默跳过，被【命名】了**
2. ⇒ **一个【活动的】客户端没有世界状态 ⇒ 不给它推 `playerState`**
3. ⇒ **所以 `SV_WriteSnapshot` 的 `findPlayerState` 返回 null**
4. ⇒ **而【整个快照】被拒为 `missing_playerstate`**
5. ⇒ **两层之外，【什么也没命名】**
6. ⇒ **那个读法在 `mp_battlecity` 上花了【一个长会话】**
7. ⇒ **【第一个】快照被拒**
8. ⇒ **所以客户端【从不】收到一个可 ack 的帧**
9. ⇒ **所以【之后每一帧都是 FULL】**（`source=none(FULL)`）
10. ⇒ **所以 cgame 【全部丢弃】**（`snapFlags & 0x0A`）
11. ⇒ **所以没有 usercmd**
12. ⇒ **所以没有 ack**
13. ⇒ **⇒ 那个【文档化的"永远 FULL"死锁】，从这里进入**
14. ⇒ **按客户端边沿触发**（否则一个卡住的客户端会以 20Hz 打印）
```

### 5.3 ⭐⭐ **一个完整的六级死锁链**

**✅ 与 §347 的"位 `0x02` 是客户端的 `CA_PRIMED` 出口"**完全闭合 ✓

**⇒ **一个完整的因果链**：

```text
无世界状态
⇒ 快照拒（missing_playerstate）
⇒ 客户端无从 ack
⇒ 每帧 FULL
⇒ cgame 丢弃
⇒ 无 usercmd
⇒ 无 ack
⇒ **永远 FULL**
```

**✅ 与 §368 的"`ack` 冻在 11"**同族（**第四次"ack 链断裂"）。**

**⚠ 而"第一个快照被拒"⇒ **所以是**单点失败**致整个会话。**

**✅ 与 §346 的"全有或全无"**第十次。

### 5.4 而**七个诊断字段**

```text
clientNum / gameplayState / team / loadoutSeq / resolvedLoadout / worldStates
```

**⇒ 六项（含客户端的号）。**

**✅ 与 §368 的"三层命名失败项"**完全同族（**第五次）。**

**⇒ 而这里**明说**"its snapshot will be rejected as missing_playerstate"。

**✅ **一个前瞻性的诊断**（说未来的后果）。**

## 六、**`dead-body` 的十二个字段**

```php
"dead-body client=" + ... + " archived=" + (effectivePlaying ? "1" : "0") +
    " eType=" ... " num=" ... " eFlags=" ... " legs=" ... " torso=" ...
    " weapon=" ... " pres=" ... " solid=" ... " ground=" ... " origin=" ...
    " msDead=" ...
```

### 6.1 五层

```text
1. **十二个字段**（含 `archived` 与 `msDead`）
2. ⇒ **每一【死亡帧】都打**
3. ⇒ **所以一个 3 秒的死亡 = 60 行**
4. ⇒ **而注释说"每帧它死亡时"⇒ **所以是有意的**
5. ⇒ **"所以下一个问题用值而不是对代码的推理来回答"**
```

**⚠ 而"每死亡帧一行"⇒ **与 §372 的"日志有界"原则**冲突**。**

**⇒ 三层**：

```text
一个 3 秒死亡 = 60 行 × 2 玩家 = 120 行/死亡
⇒ **而 §372 说 140 行/秒就是"双人延迟"的原因**
```

**⚠ 一处**潜在的性能风险**。**

**✅ 而注释说"所以下一个问题用值回答"⇒ **一个有意的取舍**。**

## 七、**`SV_PresentableTeam` 的"绝不直接用 `client.team`"**

```php
candidateSnapshot.clients.push_back({
    .clientNum = clientNum,
    // NEVER client.team DIRECTLY. Free-for-all's teamless value is
    // 0 and the client's presentation lookup returns null for it,
    // which its caller then writes through. See SV_PresentableTeam.
    .team = SV_PresentableTeam(client.team, state.characterCustomization),
});
```

**⇒ 五层**：

```text
1. **绝不直接用 `client.team`**
2. ⇒ **自由混战的无队值是 `0`**
3. ⇒ **而客户端的呈现查找为它返回 null**
4. ⇒ **而其调用方【然后写穿它】**（空指针崩溃）
5. ⇒ **所以必须 `SV_PresentableTeam`**（§347）
```

**✅ 与 §347 的"`SV_PresentableTeam` 把 `None` 映射到 1 或 2"**第二次确认。**

**⚠ 而"写穿它"⇒ **所以是一个**空指针解引用**（不是静默）。****

**✅ 与 §360 的"杀死客户端"**同族（**第三次"客户端崩溃"）。**

## 八、关键结论

1. **⭐⭐ "`0x20000` 只让 `sub_BB89E0` 跳过动画状态初始化 —— 它【不】阻止实体被画"`** —— `sub_BA7500` 把 `eType 1` 与 `eType 2` 一样送进 `sub_BB88E0`，而它**在 `centity+0x204` bit 0 被设时画**。
2. **"所以一个死玩家的实体继续渲染它的死亡动画，然后在重生时【传送到】出生点"`** —— **一个无论尸体做什么都会消失的身体**。
3. **⭐ 零售测量**：8 次尸体生成，所有者的 `ET_PLAYER` 断言从 **每 2 秒约 20 次（10Hz）塌缩到 `0..6`**（`16→0`、`20→1`、`20→2`、`20→4`）。
4. **⭐⭐ "条件是【这一世结束了】，不是『某个携带此 `clientNum` 的尸体存在于某处』"`** —— **两者只在客户端重生之前读起来相同**。
5. **"尸体环是八个槽而永不释放 ⇒ 一个打了 `clientNum` 印记的尸体活得比那个客户端的死亡久"`** —— 第六次确认"号复用"。
6. **"以尸体为门控让每一个曾经死过一次的玩家【永久不可见】，无论对自己还是对所有人"`** —— 而**四个具体的尸体号**（`#19`/`#20`/`#21`/`#22`）配两个活客户端。
7. **⭐ `ENDFRAME COPY` 的三段计时**（`clientStates` / `touchHandlers` / `snapshot`），只在 **>= 20ms** 时打。
8. **⭐ "一个 2276 字节的节点 × 少数几个客户端【自己加不出】一个 3000ms 的帧 ⇒ 在缩小任何东西之前【测量】"`** —— 一个数量级论证与自我怀疑。
9. **⚠ `reportLimit = 12` 而没有"capped"提示** —— 与 §372 的"失控不能是静默的"**不一致**。
10. **⭐⭐ `NO WORLD STATE` 的六级死锁链**：无世界状态 ⇒ 快照拒 ⇒ 无从 ack ⇒ 每帧 FULL ⇒ cgame 丢弃 ⇒ 无 usercmd ⇒ 无 ack ⇒ **永远 FULL**。
11. **"那个读法在 `mp_battlecity` 上花了【一个长会话】"`** —— 第四次"ack 链断裂"。
12. **"its snapshot will be rejected as missing_playerstate"`** —— 一个**前瞻性的诊断**（说未来的后果）。
13. **`dead-body` 的十二个字段每一死亡帧都打** —— 一个**有意的**性能取舍（与 §372 的有界原则**冲突**）。
14. **⭐ "绝不直接用 `client.team` —— 自由混战的无队值是 0 而客户端的呈现查找为它返回 null ⇒ 其调用方【然后写穿它】"`** —— 第二次确认 `SV_PresentableTeam`，而这里**明确了空指针后果**。

## 九、未闭合点

- `sub_BB88E0` 与 `sub_BB89E0` 的分工。
- `centity+0x204` bit 0 的语义。
- 停摆看门狗的 EIP 采样的精确性。
- `livingWeaponChildren_` 的用途与 `livingWeaponRightTag_`。
- `SvPresentableTeam` 的 `customization->faction` 来源。
- `sv_snapshot_mp.cpp` 22800 行之后未读取（27,016 行，进度 84%）。
