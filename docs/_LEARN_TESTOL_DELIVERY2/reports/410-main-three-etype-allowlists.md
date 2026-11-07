# 410 · **"三条独立的 eType 白名单"** —— 第三个白名单的一条缺失会【拒收整帧】、`OLMOD_KILL_FEED` 从关到开的完整病历、连杀表的 15 行而核弹只剩注释

## 一、范围

本报告学习 `sv_main_mp.cpp` 9264–9768 行（`projectClientHudElems` 的伤害/击杀反馈段与 HUD 合成段）。

## 二、**三条 eType 白名单与"拒收整帧"**（本组最重要的一段）

### 2.1 那段

```php
// AND THE BLOCKER WAS FOUND ON 2026-09-04, WHICH CHANGES THE ODDS.
// There are THREE independent eType allow-lists and the third one's
// own comment says "adding an eType means touching all three";
// section 191q touched two. The one it missed is the frame-wide
// list, and an eType missing THERE does not drop the entity -- it
// rejects the WHOLE FRAME, every field for every client, on every
// snapshot carrying a kill.
//
// That explains BOTH halves of the player's report at once: no feed
// (the obituary never reached anyone) AND a hitch between the white
// hitmarker and the red kill marker (a dropped snapshot at exactly
// the instant of a kill). The diagnosis I could not reproduce from
// the server side was real, and it was not the obituary -- it was
// the missing gate. Fixed in the same commit that added the flesh
// hit.
//
// AND IT WORKS. Player-confirmed 2026-09-04 on the very next bench
// run after the gate fix: *"kill feed works"*. So the default
// follows the demonstration, as promised, and OLMOD_KILL_FEED=0
// turns it off again.
```

### 2.2 二十四层

```text
1. **有三条独立的 eType 白名单**
2. ⇒ **而第三条自己的注释写着"加一个 eType 意味着【要动全部三条**】"**
3. ⇒ **第 191q 节【动了两条**】**
4. ⇒ **它漏掉的正是【帧级的那一击**】**
5. ⇒ **而一个在那里缺失的 eType 【不会丢掉那个实体**】**
6. ⇒ **它【拒收整帧**】**：
      · **每一个客户端的每一个字段**
      · **在每一份携带一次击杀的快照上**
7. ⇒ **⇒ 那【同时解释了玩家报告的两半**】：
      · **没有 feed**（**obituary 从未到达任何人**）
      · **白 hitmarker 与红击杀标记之间的一个卡顿**（**在击杀那一刻的一份被丢弃的快照**）
8. ⇒ **我从服务器侧无法复现的那个诊断【是真的**】**
9. ⇒ **而它【不是 obituary**】**
10. ⇒ **它【是那个缺失的门**】**
11. ⇒ **在加 flesh hit 的同一个提交里修好了**
12. ⇒ **而它【管用**】**
13. ⇒ **玩家在门修好后的【下一次 bench 运行】确认**：*"kill feed works"*
14. ⇒ **所以默认【跟随着那个演示**】**
15. ⇒ **而 `OLMOD_KILL_FEED=0` 再把它关掉**
16. ⇒ **那个机制【从来没有错**】**
17. ⇒ **它无法看见的是【第三个白名单**】**
18. ⇒ **而那里一个缺失的 eType 【足以删掉 obituary 搭乘的每一帧**】**
```

### 2.3 ⭐⭐⭐ **"一个在那里缺失的 eType 不会丢掉那个实体，它拒收整帧"**

**✅ 这是本报告里**最重要的一条协议脆弱性**。**

**⇒ 三层**：
```text
白名单 1/2（per-entity）⇒ **缺 eType ⇒ 【丢掉那一个实体**】
白名单 3（帧级）        ⇒ **缺 eType ⇒ 【拒收整帧**】
⇒ **⇒ 同一个"名单"概念，**错误的量级完全不同****
```

**✅ 与 §406 的"一个错误毁掉整段"**（`sv_snapshot_mp.cpp` 的见证概念）完全同族（**第二次"错误的量级"**）。

**⚠ 而"同时解释了两半"⇒ **一个诊断的判决性价值**。**

**✅ 与 §397 的"一个结果在两种假设下都成立 ⇒ 零信息"**相反**（这是**一个解释同时覆盖两个独立症状 ⇒ 强信息**）。

**⇒ 三层**：
```text
弱解释：只能解释"没有 feed"
强解释：**同时解释"没有 feed" + "击杀时刻的卡顿"**
⇒ **⇒ 而第二个症状【原本被认为是另一个东西**】
```

**✅ ⭐ **一个"解释力"的判据**（**能解释多少独立观察**）。

### 2.4 而**"玩家的拒绝是对的"**

```php
// OFF BY DEFAULT, AND THE PLAYER DECIDED THAT (2026-09-04).
// ...
// The answer was: *"im not even gonna test this. I guarantee you the
// lag was caused by your stupid obituary thing that didn't even give
// me a killfeed."*
//
// That is the right call whether or not the diagnosis is: a feature
// that delivers nothing has no claim on a live match. It stays in
// the tree because the mechanism is decoded and the remaining
// question is client-side (section 191q), and it turns on with
// OLMOD_KILL_FEED=1 for a bench run.
```

**⇒ 十层**：
```text
1. **玩家**："我根本不去测这个。我保证那个卡顿是由你那个蠢 obituary 引起的，它甚至没给我一个 killfeed。"
2. ⇒ **"无论那个诊断对不对，那是【正确的决定**】"**
3. ⇒ **一个【交付不了任何东西的特性】对一场活的比赛【没有主张**】**
4. ⇒ **它留在树里因为【机制已解码**】**
5. ⇒ **而剩下的问题【是客户端侧的**】**
6. ⇒ **它用 `OLMOD_KILL_FEED=1` 在一场 bench 运行里打开**
7. ⇒ **而门修好之后改了默认（§2.1）**
```

**✅ ⭐⭐ **"一个交付不了任何东西的特性对一场活的比赛没有主张"** —— 本报告里最重要的产品判据。**

**✅ 与 §409 的"名字不是数字"**不同（这是**一个范围判据而不是格式判据**）。

**⚠ 而"玩家的诊断【和实际根因不同】而决定仍然正确"⇒ **一个极精确的区分**。**

**⇒ 三层**：
```text
玩家的诊断：obituary 引起卡顿 ⇒ **错**（是缺门）
玩家的决定：关掉它 ⇒ **对**（因为交付不了东西）
⇒ **⇒ 所以【决定与诊断可以分离**】
```

**✅ ⭐ **一个"行为正确而理由错误"的诚实处理**。

### 2.5 而**"存活时静默"**

```php
if (!world_.spawnObituaryEvent(...))
{
    // SILENT WHEN HEALTHY. The only way this fails is a spent
    // entity pool or a state the writer would refuse, and both
    // are worth a line because the feed then just stops.
    OlMod::RuntimeLog::write(... "obituary REFUSED ...");
}
```

**⇒ 五层**：
```text
1. **存活时静默**（**只在失败时记一行**）
2. ⇒ **唯一会失败的方式**：**实体池耗尽** 或 **写者会拒绝的状态**
3. ⇒ **两者都值得一行**
4. ⇒ **因为【feed 然后就直接停了**】**
```

**✅ 与 §409 的"`obituary REFUSED`"**同族（**第二次"只在异常时记日志"）**。**

**⇒ 三层**：
```text
正常 ⇒ **零日志**（不污染）
异常 ⇒ **一行**（有证人）
⇒ **⇒ 一个"低噪声取证"的纪律**
```

**✅ 与 §402 的"`PREMATCH|` 从 `INF` 提到 `Warn`"**不同**（那是**日志级别导致不可见**）。

**⇒ 三层**：
```text
§402  太少（级别太高⇒被丢弃）⇒ **提级**
§409  太多（每 tick 一行）⇒ **降频**
§410  正常零行 ⇒ **只在异常记**
```
**✅ ⭐ **一个完整的"日志量"三维纪律**。

## 三、**`OLMOD_KILL_FEED` 的默认值写法**

```cpp
static const bool killFeedEnabled = [] {
    const char *const value = std::getenv("OLMOD_KILL_FEED");
    return !(value && value[0] == '0' && !value[1]);
}();
```

**⇒ 六层**：
```text
1. **`static const bool`** ⇒ **只求值一次**（不是每帧 `getenv`）
2. ⇒ **`lambda` 立即调用**（`[] { ... }()`）
3. ⇒ **`!(value && value[0]=='0' && !value[1])`**
4. ⇒ **未设 ⇒ `value == nullptr` ⇒ `!(false)` ⇒ 【`true`**】**
5. ⇒ **设为 `"0"` ⇒ `value[0]=='0' && !value[1]` ⇒ `!(true)` ⇒ 【`false`**】**
6. ⇒ **设为 `"00"` / `"0x"` ⇒ `!value[1]` 为假 ⇒ 【`true`**】**
```

**✅ ⭐ **一个精确的"只认恰好 `"0"`"的写法**。**

**⚠ 而"`static` 在函数内"⇒ **一个进程级的缓存**（环境变量在运行中改变**不再生效**）。

**✅ 与 §409 的"`static` 局部 ⇒ 全局"**同族（**第三次）。**

**⇒ 三层**：
```text
§407  `animatedThisLife`：**按 clientNum**（正确）
§409  `lastBlockedBits`：**全局**（因为门控是全局的 ⇒ 正确）
§410  `killFeedEnabled`：**全局且只求值一次**（因为环境变量不该中途变 ⇒ 正确）
```

**✅ ⭐ **一个"作用域必须匹配语义"的三例表**。

## 四、**击杀的六个独立副作用**（本组第二重要）

### 4.1 那段

```text
① addClientDeaths(victim, 1)         ← 在任何 attacker 测试之前
② 一个 EV_OBITUARY 每次死亡         ← 也在任何 attacker 测试之前
③ killCamSubjects_[victim] = {attacker, serverTime}
   lastMatchKill_ = SvMatchEndKill{...}
④ addClientStreak(attacker, 1)
⑤ firstBlood / headshot / revenge / firstPlaceKill 四个 medal（入队）
⑥ lastKilledBy_[victim] = attacker
⑦ killFeedbackSound_（`p 15` mp_hit_kill）
⑧ 连杀 splash（15 行表）
```

**⇒ 五层排序理由**：

```text
1. **死亡计数【最先**】（在 attacker 测试之前）
2. ⇒ **因为自杀、坠落、队友击杀【仍然要让受害者付一次死亡**】**
3. ⇒ **obituary 也【在 attacker 测试之前**】**
4. ⇒ **因为零售为 dm demo 的全部 `145` 次死亡各发一条**
5. ⇒ **而它的 `ET_PLAYER` lives 数也【恰好是 `145`**】**
```

**✅ ⭐⭐ **"`145` 对 `145`"** —— 一个**双向计数的闭合**。

**✅ 与 §407 的"`24` 个 `N` 对 `24` 个 `r 2`"**同族（**第三次"配对计数排除假设"）。**

**⇒ 三层**：
```text
观察：`145` 条 obituary、`145` 次 `ET_PLAYER` lives
⇒ **⇒ 所以 obituary【每死一条**，不是每合法击杀一条】
```

**✅ 而"自杀/坠落/队友击杀各得一行"⇒ **一个精确的边界**。**

### 4.2 而**"爆头提升是【这个服务器的】，不是 payload 的"**

```php
// The head-shot promotion is this server's, not the payload's: the
// bullet path files MOD_PISTOL_BULLET/MOD_RIFLE_BULLET and never
// MOD_HEAD_SHOT, so the obituary would show a rifle where retail
// shows a skull. The test is the SAME hit-location pair the headshot
// medal below already fires on, so the icon and the medal cannot
// disagree.
```

**⇒ 七层**：
```text
1. **爆头提升是【这个服务器的**】，不是 payload 的**
2. ⇒ **子弹路径只填 `MOD_PISTOL_BULLET`/`MOD_RIFLE_BULLET`**
3. ⇒ **而【从不】填 `MOD_HEAD_SHOT**】**
4. ⇒ **所以 obituary 会显示【一把步枪】而零售显示【一个骷髅**】**
5. ⇒ **所以服务端把 `methodOfDeath` 提升为 `SvMethodOfDeathHeadShot`**
6. ⇒ **而用的【正是下面爆头奖章已经在用的同一对 hit-location**】**
7. ⇒ **⇒ 所以【图标与奖章不可能不一致**】**
```

**✅ ⭐ **"图标与奖章不可能不一致"** —— 一个**用共享判据消除不一致**的设计**。**

**✅ 与 §409 的"`scoreBefore`/`scoreAfter` 两两互校"**同族（**第二次"共享单一真相源"）。**

**⚠ 而"这是这个服务器的不是 payload 的"⇒ **第五次"明确标注非原版"**。**

**⇒ 三层**：
```text
§403  按 demo 形态驱动的显示值 ⇒ 标注
§409  偏好顺序是回退梯子 ⇒ 标注
§410  爆头提升是服务端的 ⇒ 标注
```

### 4.3 而**"死亡数据源在会话层不存在"的填补**

**⇒ 而 `killCamSubjects_[victim] = {attacker, serverTime}` 的理由**：

```php
// THE KILLCAM'S SUBJECT, RECORDED HERE BECAUSE THIS IS THE ONLY
// PLACE THAT KNOWS IT. driveClientUiScreens sees a player go from
// alive to dead and nothing else; who did it and when lives on this
// event, one frame earlier, and was thrown away by everything that
// consumed it. The victim's OWN entity number is what retail points
// the camera at -- killCamLookAtEntity is 6 on all seven of the
// recording client's deaths, and 6 is its clientNum -- so only the
// killer and the time need carrying.
```

**⇒ 九层**：
```text
1. **摄像机的目标【记录在这里，因为这是【唯一知道它】的地方**】**
2. ⇒ **`driveClientUiScreens` 只看见一个玩家从活到死，别的什么也没有**
3. ⇒ **谁干的、什么时候【活在这个事件上，早一帧**】**
4. ⇒ **而它被【每一个消费它的东西丢掉了**】**
5. ⇒ **受害者的【自己的实体号】是零售指向相机的那个东西**
6. ⇒ **`killCamLookAtEntity` 在记录客户端全部七次死亡上【都是 `6`**】**
7. ⇒ **而 `6` 就是它的 `clientNum`**
8. ⇒ **⇒ 所以只有【凶手与时间】需要携带**
```

**✅ ⭐⭐ **"`killCamLookAtEntity` 是 `6` 而 `6` 就是 `clientNum`"** —— 第二次"两个数同值 ⇒ 同物"（§408 `+1799`、§407 `L n 7`）。

**⚠ 而"唯一知道它的地方"⇒ **一个"信息在传递中丢失"的经典**。**

**✅ 与 §409 的"`use` 键的黑洞"**同族（**第二次"关键信息在某处被丢弃"）。**

## 五、**五个奖章的两个时机**（本组第三重要）

### 5.1 那段

```php
// OLMOD(splash-queue): a medal is ENQUEUED, not sent. The client
// holds one splash per display slot, so two on the same frame means
// the second overwrites the first before it draws - which is what
// "it will not give me both revenge and headshot" looks like from
// the screen. releasePendingSplashes drains one every
// SvSplashReleaseIntervalMilliseconds, which is the interval the
// retail demo spaces its own multi-medal kills by.
//
// The sound moves with the banner rather than firing per kill, so
// each medal keeps its own sting and they cannot drift apart. That
// also matches the demo: 18 splash sounds against 20 slot-0
// splashes, not one per kill.
```

### 5.2 十八层

```text
1. **一个奖章是【入队的】，不是发出的**
2. ⇒ **客户端【每个展示槽只持有一个 splash**】**
3. ⇒ **所以同一帧两个【意味着第二个在第一个绘制之前覆盖它**】**
4. ⇒ **那正是从屏幕上看到的"它不会同时给我复仇和爆头"的样子**
5. ⇒ **`releasePendingSplashes` 每 `SvSplashReleaseIntervalMilliseconds` 排空一个**
6. ⇒ **那是【零售 demo 为它自己的多奖章击杀所间隔的**】那个间隔
7. ⇒ **声音【随横幅一起移动】而不是每个击杀各发**
8. ⇒ **所以每个奖章【保持自己的刺音**】而它们【不能彼此漂移**】**
9. ⇒ **那也与 demo 一致**：**`18` 个 splash 声音对 `20` 个槽 `0` splash**
10. ⇒ **不是每个击杀一个**
```

### 5.3 ⭐⭐ **"一个槽只持有一个 splash"**

**✅ 与 §407 的"槽复用要清状态"**、§409 的"槽位是位置性的"**同族（**第五次"槽"**）。

**⇒ 三层**：
```text
槽 = 一个展示位置
⇒ **同一帧写两个 ⇒ 第二个覆盖第一个**
⇒ **⇒ 所以必须【排队 + 间隔释放**】
```

**✅ ⭐ **一个"资源容量导致必须排序"的实例**。

**⚠ 而"`18` 对 `20`"⇒ **不是 1:1**。**

**✅ 与 §409 的"不是每 tick 一次"**不同（这不是**频率**而是**数量的非一一对应**）。

**⇒ 三层**：
```text
`20` 个槽-0 splash
`18` 个 splash 声音
⇒ **⇒ 所以【两个奖章共享一个声音**】或【有一个奖章没声音】
```

**⚠ 一个**未闭合点**。

### 5.4 而**"入队上限"**

```cpp
if (queue.size() >= SvSplashQueueLimit)
{
    OlMod::RuntimeLog::write(..., "splash queue full client=" +
        std::to_string(attacker) + " dropped row=" + std::to_string(row));
    return;
}
```

**⇒ 四层**：
```text
1. **队满 ⇒ 【丢弃并记一行**】**
2. ⇒ **而不是【无限增长**】**
3. ⇒ **而丢弃是【可见的**】（`dropped row=`）
4. ⇒ **⇒ 一个"有界 + 可观测的丢弃"**
```

**✅ 与 §407 的"`uint8` 截断"**相反**（那是**静默截断**）。

**⇒ 三层**：
```text
静默截断 ⇒ **数据错而无证人**
有界丢弃 + 日志 ⇒ **数据丢而有证人**
⇒ **⇒ 后者可接受**
```

**✅ ⭐ **一个精确的"可接受的失败"判据**。

### 5.5 而**"第一名的击杀奖章"的一帧偏斜**

```php
// ORDERING: dm.lua credits the attacker's kill during the world
// frame, so an attacker who takes the lead with this very kill is
// already ahead of the victim by the time this runs and the medal
// is missed. That is one frame of skew, not a wrong trigger, and
// fixing it would mean keeping a shadow copy of the scoreboard.
```

**⇒ 八层**：
```text
1. **`dm.lua` 在【世界帧】里给攻击者记击杀**
2. ⇒ **所以一个【用这一杀】夺得领先的攻击者**
3. ⇒ **在这个跑的时候【已经在受害者前面**】**
4. ⇒ **⇒ 所以那个奖章【被漏掉**】**
5. ⇒ **那是【一帧的偏斜**】，不是一个错的触发**
6. ⇒ **而修它会意味着【保存一份计分板的影子副本**】**
7. ⇒ **⇒ 所以【不修**】**
```

**✅ ⭐⭐ **"一帧的偏斜，不是一个错的触发"** —— 一个**极精确的问题定性**。**

**✅ 与 §404 的"窄回退不是诊断"**同族（**第二次"明确的定性而不含混"）。**

**⚠ 而"修它要保存影子副本"⇒ **第十三次"改动的代价评估"**。**

## 六、**连杀表的 15 行**（本组第四重要）

### 6.1 而**"核弹只留下注释"**

```cpp
// ★★★ 28100 刀CQ（链A 连杀 · 核弹可视化）——
//   依据 `_nuke.gsc` 原文：
//     nukeVision() { visionSetNaked( "mpnuke", 3 ); visionSetNaked( "mpnuke_aftermath", 5 ); }
//   与零售 cha demo 实测 `d 2557 "mpnuke" 3000` / `d 2557 "aftermath" 5000` 一致
//   （第三参数是毫秒时长）。
//   本刀只做视觉：25 杀（killstreakTable 的 nuke 需求）时发 mpnuke 3 秒；
//   不结束对局、不做慢动作/地震（那些要改比赛状态，另行单刀）。
                            }
```

**⚠ 注意 `9600` 行的 `}`**：这一段是**纯注释**，**没有对应的代码**。

**⇒ 六层**：
```text
1. **`_nuke.gsc` 的 `nukeVision()`**：`visionSetNaked("mpnuke", 3)` + `visionSetNaked("mpnuke_aftermath", 5)`
2. ⇒ **而零售 cha demo 实测**：`d 2557 "mpnuke" 3000` / `d 2557 "aftermath" 5000`
3. ⇒ **（第三参数是【毫秒时长**】）**
4. ⇒ **本刀只做视觉：25 杀时发 `mpnuke` 3 秒**
5. ⇒ **不结束对局、不做慢动作/地震**
6. ⇒ **⚠ 而【代码块里只有 `}`】，没有实际发送**
```

**✅ ⭐ **一个"注释写了而代码没有"的空块** —— **第七次"记录下来了但没接线"**。

**⚠ 而与 §403 的"`mpnuke` 是核弹滤镜不是开场黑白"**完全一致 ✓

**⇒ 三层**：
```text
§403  撤掉了把 `mpnuke` 当开场滤镜
§410  `mpnuke` 的正确用途（25 杀的核弹）**写进了注释**
⇒ **⇒ 而【代码仍然没有**】
```

**⚠ 而"`aftermath`"⇒ §407 的 `mpnuke_aftermath` 在这里写作 `aftermath`** —— **一个名字差异**。

**⇒ 三层**：
```text
`_nuke.gsc`：`mpnuke_aftermath`
零售 demo：`"aftermath"`（**没有 `mpnuke_` 前缀**）
⇒ **⇒ 两个不同的名字**
```

**⚠ 一个**需要标注的差异**（可能是 GSC 的 `visionSetNaked` 会加前缀，或 demo 里确实是裸名）。

### 6.2 而**15 行的连杀表**

```cpp
static constexpr std::array<std::pair<std::uint32_t, std::uint16_t>, 15>
    KillstreakSplashRows{{
        {3, 18}, {4, 34}, {4, 38}, {5, 26}, {5, 35},
        {6, 30}, {7, 20}, {7, 32}, {8, 44}, {9, 24},
        {9, 31}, {11, 25}, {11, 21}, {15, 40}, {25, 27},
    }};
for (const auto &[needKills, splashRow] : KillstreakSplashRows)
    if (killerKills != needKills) continue;
```

**⇒ 七层**：
```text
1. **`{击杀数, splash 行号}` 的十五对**
2. ⇒ **`3` ⇒ `18`（uav）**
3. ⇒ **`4` ⇒ `34`（counter_uav）/ `38`（airdrop）**
4. ⇒ **`5` ⇒ `26`（predator）/ `35`（sentry）**
5. ⇒ **`6` ⇒ `30`（precision_airstrike）**
6. ⇒ **`7` ⇒ `20`（helicopter）/ `32`（harrier）**
7. ⇒ **`8` ⇒ `44`（airdrop_mega）**
8. ⇒ **`9` ⇒ `24`（helicopter_flares）/ `31`（stealth_airstrike）**
9. ⇒ **`11` ⇒ `25`（ac130）/ `21`（helicopter_minigun）**
10. ⇒ **`15` ⇒ `40`（emp）**
11. ⇒ **`25` ⇒ `27`（nuke）**
```

**⚠ 而"`killerKills != needKills ⇒ continue`"⇒ **精确相等**，不是"≥"。**

**⇒ 五层**：
```text
用 `!=` ⇒ **每一次击杀【恰好触发一次**】**
若用 `>=` ⇒ **3 杀之后每次击杀都重播 UAV**
⇒ **⇒ 所以 `!=` 是正确的**
```

**✅ ⭐ **一个"精确相等而不是阈值"的正确选择**。

**✅ 与 §409 的"`roundSwitch` 是模数"**不同（这是**一次性的**）。

**⚠ 而两个奖励同一击杀数（`4` 有两个）⇒ **两个都会发**。**

**⇒ 三层**：
```text
`4` ⇒ **counter_uav(34) + airdrop(38)**
`5` ⇒ **predator(26) + sentry(35)**
...
⇒ **⇒ 所以同一击杀数可以【多个奖章**】
```

**✅ 而"字幕格式 `w <slot> <row> <dur>`，slot=0、dur=0"⇒ **与 §407 的 `w 2 4 0`**不同（那是**slot 2**）。

**⇒ 三层**：
```text
§407  `w 2 4 0` ⇒ **slot 2**（横幅/语音手势）
§410  `w 0 <row> 0` ⇒ **slot 0**（奖章）
```
**✅ 而 §410 五.2 说"`20` 个槽 `0` splash"⇒ **确认 slot 0 是奖章槽**。

## 七、**`p 15` = `mp_hit_kill`**

```php
// MEASURED: the retail dm server plays `p 15` -- alias
// `mp_hit_kill` -- 28 times against 84 `mp_hit_alert`, which is the
// ratio of kills to hits and is what the alias name says anyway.
// It goes to the ATTACKER, beside the kill marker and the score
// popup, which are the two things it is the audio for.
```

**⇒ 七层**：
```text
1. **零售 dm 发 `p 15` = 别名 `mp_hit_kill`**
2. ⇒ **`28` 次，对 `84` 次 `mp_hit_alert`**
3. ⇒ **`28:84 = 1:3`** ⇒ **正是击杀对命中的比例**
4. ⇒ **而那是【别名名字自己说的**】**
5. ⇒ **它到【攻击者**】**
6. ⇒ **在旁边是击杀标记与分数弹出**
7. ⇒ **⇒ 那两个正是【它是其音频**】的东西
```

**✅ ⭐ **"正是击杀与命中的比例，而那是别名名字自己说的"** —— **一个交叉验证（数量比 ↔ 名字语义）**。

**✅ 与 §407 的"`28` 条 `L <victim> 7`"**同族（**又一个 `28`**）—— 但**这是不同的 `28`**。

**⇒ 三层**：
```text
§407  `28` 条 `L x 7`（每死一条）
§410  `28` 次 `p 15`（每杀一次）
⇒ **⇒ 同一局的两个 `28`** ⇒ **而它们是【同一次死亡的两种表现**】
```

**✅ ⭐ **一个极漂亮的交叉闭合**（**`28` 次死亡 ⇒ `28` 条 `L` + `28` 次 `p 15`**）。

**⚠ 一个**需要标注的巧合可能性**。

## 八、**HUD 元素的"位置性"**

```php
// Hold the marker for as long as the popup lives even though its
// own fade finishes sooner. These elems are POSITIONAL - the
// client keys them by slot - so retiring the marker first would
// slide the popup from slot 1 down to slot 0 and restart its
// animation mid-flight. Retail never moves an elem either; it
// leaves the faded one in place. By then the marker has reached
// alpha 0, so holding it costs nothing on screen.
```

**⇒ 十层**：
```text
1. **把标记持有到与弹出【一样长**】**
2. ⇒ **即使它自己的淡出【更早结束**】**
3. ⇒ **这些元件是【位置性的**】——**客户端按槽索引它们**】
4. ⇒ **所以【先退役标记】会让弹出【从槽 1 滑到槽 0**】**
5. ⇒ **并【在飞行中途重启它的动画**】**
6. ⇒ **零售【也从不移动一个元件**】**
7. ⇒ **它【把淡出的那个留在原地**】**
8. ⇒ **到那时标记已达到 `alpha 0`**
9. ⇒ **⇒ 所以【持有它在屏幕上零代价**】**
```

**✅ ⭐⭐ **"先退役标记会让弹出从槽 1 滑到槽 0 并在飞行中途重启它的动画"** —— 一个**极精确的 UI 机制推理**。

**✅ 与 §409 的"一个错的人偶仍然胜过一个没有人偶"**同族（**第四次"位置语义"）。**

## 九、关键结论

1. **⭐⭐⭐ 三条独立的 eType 白名单，而第三条（帧级）的一条缺失【拒收整帧】**（每一个客户端的每一个字段，在每一份携带击杀的快照上）—— 与 per-entity 白名单"丢掉那一个实体"是**完全不同的量级**。
2. **⭐⭐⭐ 那个缺失的门【同时解释了两半报告】**：没有 feed（obituary 从未到达）+ 击杀瞬间的卡顿（一份被丢弃的快照）—— **一个解释力的判据**（能解释多少独立观察）。
3. **⭐⭐ "我从服务器侧无法复现的那个诊断是真的，而它不是 obituary —— 它是那个缺失的门"`** —— 而**玩家在门修好的下一次 bench 运行就确认了："kill feed works"**。
4. **⭐⭐⭐ "一个交付不了任何东西的特性对一场活的比赛【没有主张】"`** —— 而 **"无论那个诊断对不对，那是正确的决定"** ⇒ **行为正确而理由错误是可以接受的**。
5. **"存活时静默：唯一会失败的方式是实体池耗尽或写者会拒绝的状态，两者都值得一行"`** —— 与 §402 的"太少"、§409 的"太多"构成**日志量的三维纪律**（太少/太多/正常零行）。
6. **`OLMOD_KILL_FEED` 的写法**：`static const bool` + lambda + `!(value && value[0]=='0' && !value[1])` ⇒ **只认恰好 `"0"`**。
7. **⭐⭐ "`145` 条 obituary 对 `145` 次 `ET_PLAYER` lives"** ⇒ obituary **每死一条**（不是每合法击杀），自杀/坠落/队友击杀各得一行 —— **第三次"配对计数排除假设"**。
8. **⭐⭐ "爆头提升是【这个服务器的】不是 payload 的：子弹路径只填 `MOD_*_BULLET` 而从不填 `MOD_HEAD_SHOT`，所以 obituary 会显示步枪而零售显示骷髅；用的正是爆头奖章同一对 hit-location，所以【图标与奖章不可能不一致】"`** —— 第五次"明确标注非原版"，第二次"共享单一真相源"。
9. **⭐⭐ "`killCamLookAtEntity` 在全部七次死亡上都是 `6`，而 `6` 就是记录客户端的 `clientNum`"** ⇒ **只有凶手与时间需要携带** —— 第二次"两个数同值 ⇒ 同物"，第二次"关键信息在某处被丢弃"。
10. **⭐⭐ "一个奖章是【入队的】：客户端每个槽只持有一个 splash，同一帧两个⇒第二个覆盖第一个 —— 那正是『它不会同时给我复仇和爆头』的样子"`** —— 而 **`18` 个 splash 声音对 `20` 个槽-0 splash**（**不是 1:1**）。
11. **"队满 ⇒ 丢弃并记一行 `dropped row=`"`** —— **有界 + 可观测的丢弃**，与静默截断相反。
12. **⭐⭐ `firstPlaceKill` 的"一帧偏斜而不是错的触发"**：**"`dm.lua` 在世界帧给攻击者记击杀 ⇒ 用这一杀夺得领先的攻击者已经在前，奖章被漏掉；那是一帧的偏斜，不是错的触发，而修它要保存一份计分板的影子副本"`** —— 第二次"明确的定性"，第十三次"改动的代价评估"。
13. **⭐⭐⭐ 核弹的注释是【空块】**：`_nuke.gsc` 的 `nukeVision()`（`mpnuke` 3 + `mpnuke_aftermath` 5）与零售 `d 2557 "mpnuke" 3000` 对齐**只写在注释里，9600 行只有一个 `}`** —— 第七次"记录下来了但没接线"。
14. **⚠ 一处名字差异**：`_nuke.gsc` 写作 `mpnuke_aftermath`，零售 demo 写作 `aftermath`（无前缀）。
15. **15 行连杀表**（`3`→18 uav / `4`→34 counter_uav + 38 airdrop / `5`→26 predator + 35 sentry / `6`→30 precision_airstrike / `7`→20 helicopter + 32 harrier / `8`→44 airdrop_mega / `9`→24 flares + 31 stealth / `11`→25 ac130 + 21 minigun / `15`→40 emp / `25`→27 nuke），而 **`!=` 精确相等**（`>=` 会重播）。
16. **⭐ `p 15` = `mp_hit_kill` 的 `28` 次对 `84` 次 `mp_hit_alert`**（`1:3`，正是击杀对命中），而**与 §407 的 `28` 条 `L x 7` 是同一批死亡**。
17. **⭐⭐ "这些元件是位置性的：先退役标记会让弹出从槽 1 滑到槽 0 并在飞行中途重启它的动画；零售也从不移动一个元件，它把淡出的那个留在原地"`** —— 第四次"位置语义"。

## 十、未闭合点

- `20` 个槽-0 splash 对 `18` 个声音的差（哪一个没声音）。
- `SvSplashQueueLimit` / `SvSplashReleaseIntervalMilliseconds` 的值。
- `SvSplashFirstBlood*` / `*Headshot*` / `*Revenge*` / `*FirstPlaceKill*` 的四个 row 与 points。
- `aftermath` 与 `mpnuke_aftermath` 的名字差异。
- `SvDamageFeedbackDurationMilliseconds` / `SvScoreFeedbackDurationMilliseconds` 的值。
- `sv_main_mp.cpp` 9768 行之后未读取（**文件实际 `11,940` 行**）。
