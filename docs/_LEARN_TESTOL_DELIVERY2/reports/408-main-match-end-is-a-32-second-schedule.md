# 408 · **"一个走完 32.7 秒【日程】的结束"** —— `d 15 0` + `d 464 0` 从盘上而非线上读出的独立确认、`pm_type 5` 早发的四个症状、`_tp` 调色在【地图自己的 fastfile】

## 一、范围

本报告学习 `sv_main_mp.cpp` 6278–7250 行（`announceMatchCompletion` 余下 + 整个 `driveMatchEndSequence`）。

## 二、**`d 15 0` / `d 464 0` 的"从盘上读出的独立确认"**（本组最重要的一段）

### 2.1 那段

```php
//     d 15 0        the HUD countdown's absolute end time
//     d 464 0       ui_timelimit
//
// Both indices are this project's own MatchEndTimeConfigStringIndex and
// UiTimeLimitConfigStringIndex, which is an independent confirmation of
// two numbers that were read off out.exe rather than off the wire.
// Until SV_SetConfigString existed there was no way to send either, so
// the countdown carried on ticking through a decided match.
```

### 2.2 十四层

```text
1. **`d 15 0`** ⇒ **HUD 倒计时的【绝对结束时间**】
2. ⇒ **`d 464 0`** ⇒ **`ui_timelimit`**
3. ⇒ **两个索引都是本项目自己的 `MatchEndTimeConfigStringIndex` 与 `UiTimeLimitConfigStringIndex`**
4. ⇒ **⇒ 那是【两个从 `out.exe` 读出、而不是从线上读出】的数字的【独立确认**】**
5. ⇒ **直到 `SV_SetConfigString` 存在之前，两个都【没有发送的办法**】
6. ⇒ **所以倒计时【在一场已决出的比赛中继续走**】
```

### 2.3 ⭐⭐⭐ **"从 `out.exe` 读出而不是从线上读出"**

**✅ 这是本报告里**最重要的一条证据独立性问题**。**

**⇒ 三层**：
```text
路 A：从线上（demo）读出 `d 15 0`
路 B：从 `out.exe` 的常量表读出 `15` / `464`
⇒ **⇒ 两条【独立路径】给出同一个数** ⇒ **强证据**
```

**✅ 与 §402 的"两个独立实现都指向 `s 0201`"**同族（**第二次"两条独立路径一致 ⇒ 强信息"）。**

**⚠ 而"倒计时在一场已决出的比赛中继续走"⇒ **一个可见的症状**。**

**✅ 与 §406 的"平光外观"**同族（**第六次"静默的失败产生可见的缺陷"）。**

**⚠ 而"直到 `SV_SetConfigString` 存在之前"⇒ **第十二次"定义了但没接线"**。**

**⇒ 三层**：
```text
常量：`MatchEndTimeConfigStringIndex = 15` 早就在
写通道：`SV_SetConfigString` **后来才有**
⇒ **⇒ 所以中间那段时间【常量在而无法使用**】
```

**✅ 与 §403 的"`SvAnnouncerSpawnMusic = 2130` 早就在，只是从来没发过"**完全同族（**第四次）。**

## 三、**结算屏没被打开的完整病历**（本组第二重要）

### 3.1 那段

```php
// ★★ 28100 刀BB（甲方第 14 项「结算没有」；数据侧已由日志证明正确）——
//   `match complete gametype=cha reason=scoreLimit tf=150 sc=31 winner=Tf` 说明**判定全对**，
//   缺的只是**结算屏没被打开**。
//   零售 cha 的结算段（`0C-2020-4-11[11-11-11]cha.demo`，第 647/648/654 条）：
//     s ui_match_complete "1"     ← ★ 打开结算屏
//     s 2972 "1"
//     … top3_*_current_weapon …
//     q 19
//   我方原来只在**campaign** 分支发过 `ui_match_complete`，多人模式从来没发 ⇒ 所以你看不到结算。
```

### 3.2 十六层

```text
1. **甲方「结算没有」**
2. ⇒ **而数据侧已由日志证明正确**：`match complete gametype=cha reason=scoreLimit tf=150 sc=31 winner=Tf`
3. ⇒ **所以【判定全对**】**
4. ⇒ **缺的只是【结算屏没被打开**】**
5. ⇒ **零售 cha 的结算段**：
      · **`s ui_match_complete "1"`** ← **打开结算屏**
      · **`s 2972 "1"`**
      · **… `top3_*_current_weapon` …**
      · **`q 19`**
6. ⇒ **我方原来【只在 `campaign` 分支】发过 `ui_match_complete`**
7. ⇒ **多人模式【从来没发**】**
8. ⇒ **⇒ 所以你看不到结算**
9. ⇒ **所以这里对【非战役模式】按零售补这四条**（逐 client 发）
```

### 3.3 ⭐⭐⭐ **"判定全对而只缺一个屏幕"**

**✅ 这是本报告里**最重要的一次"故障分层"**。**

**⇒ 三层**：
```text
层 1：判定（比分/胜负）⇒ **日志证明对**
层 2：状态写（`completed` 等）⇒ **对**
层 3：**屏幕（`ui_match_complete`）** ⇒ **从未发**
⇒ **⇒ 所以一个【逻辑全对】的比赛在玩家眼里是"没有结算"**
```

**✅ 与 §402 的"一个等待一个永不到来的信号的客户端"**同族（**第八次"沉默的诊断"）。**

**⚠ 而"只在 `campaign` 分支发过"⇒ **一个分支覆盖的漏洞**。**

**✅ 与 §407 的"`zm` 团灭路径"**同族（**第二次"分模式的路径覆盖"）。**

**⇒ 三层**：
```text
coop   ⇒ **发了** `ui_match_complete`
zm     ⇒ **发了**（`+1500ms`）
dmz/cha/sd/dm ⇒ **从来没发**
```

**✅ 一个**精确的分支覆盖表**。

**⚠ 而 `s 2972 "1"` 与 `q 19`⇒ **与 §407 的"`> 161` / `s 2972 "1"` 骑同一帧"**完全闭合 ✓

**⇒ 三层**：
```text
§407 说 +17000 的 `s 2972 "1"`/`> 161` 是 **podium** 帧
§408 说结算段（第 647/648/654 条）也有 `s 2972 "1"`
⇒ **⇒ 所以 `2972` 出现【两次**】
```

**⚠ 而 §407 也说 `s ui_match_complete "1"` **移到 `driveMatchEndSequence` 的 +17000**。**

**⇒ 一处**需要在 §408 标注的时序差异**：**这里（`announceMatchCompletion`）与 +17000（`driveMatchEndSequence`）都发 `ui_match_complete`。**

**✅ 而这正是下面 §四 的注释所解释的"从 +0 移到 +17000"。**

**⇒ 所以这两处【必须区分模式**】—— 而注释说 `if (matchGameType_ != "coop")` 覆盖了 dm/cha/sd/dmz/zm。

**⚠ 一个**真正的开放点**（会不会重复发）。

## 四、**`+1799` 的逐字节闭合**（本组第三重要）

### 4.1 那段

```php
// MEASURED (retail dm, serverTime 631700/631800): immediately before
// outcomeNotify is born, the recorder's aarScoreboard row changes from
// xp 5997 to 7796. The +1799 is byte-for-byte the match-bonus number
// shown by the HudElem at +1100. Freeze and award it on this one-shot
// transition, before the match-end scoreboard push below. Recomputing
// at +1100 used to leave the AAR at zero and could also disagree if a
// slot or rank changed during the delay.
```

### 4.2 十三层

```text
1. **在 `outcomeNotify` 出生之前，记录器的 `aarScoreboard` 行从 `xp 5997` 变成 `7796`**
2. ⇒ **`7796 - 5997 = 1799`**
3. ⇒ **那个 `+1799` 逐字节是 `+1100` 处 HudElem 显示的【比赛奖励数**】**
4. ⇒ **所以在这【一次性的转移】上冻结并授予它**
5. ⇒ **在下面的比赛末计分板推送【之前**】**
6. ⇒ **在 `+1100` 处【重算】过去会让 AAR 停在零**
7. ⇒ **也可能在那个延迟期间【一个槽或段位变化**】而导致不一致
8. ⇒ **参与时长 `< 1'000ms` ⇒ 跳过**（**不给没参与的人发奖**）
9. ⇒ **`placedTopThree = topThree 里有它**"
10. ⇒ **`bonus = SV_CalculateDmMatchBonus(rank, participation, placedTopThree)`**
11. ⇒ **`dmMatchBonuses_.insert_or_assign(clientNum, bonus)`** ⇒ **冻结**
12. ⇒ **`addClientXp(awardedXp)`**
13. ⇒ **`addClientGp(SV_GpForXp(awardedXp))`**
```

### 4.3 ⭐⭐ **"逐字节是同一个数"**

**✅ 与 §407 的"`L` 的第二个参数就是那个槽位号"**同族（**第二次"两个数同值 ⇒ 同物"）。**

**⇒ 三层**：
```text
demo 侧：`7796 - 5997 = 1799`
HudElem 侧：显示的奖励 = 1799
⇒ **⇒ 所以【同一个值在两条路径上出现**】⇒ **可判定的确认**
```

**⚠ 而"在 `+1100` 处重算过去会让 AAR 停在零"⇒ **一个具体的历史 bug**。**

**✅ 与 §400 的"缓存键必须含那个状态"**同族（**第三次"陈旧的计算"）。**

**⇒ 三层**：
```text
正确：**在转移那一刻【冻结**】
错误：**在延迟之后【重算**】
⇒ **⇒ 而重算【两次都错**】（AAR 零 / 段位已变）
```

**✅ ⭐ **一个"冻结 vs 重算"的完整论证**。

### 4.4 而**"故意的无闸写入器"**

```php
// The AAR's second earnings column, on the same row and at the same
// moment the MEASURED note above records the xp row changing.
// Deliberately the ungated writer beside the xp call:
// this block runs after the match is decided, so the ServerCore
// wrappers (which stop at matchStatus_.completed) would drop it.
static_cast<void>(clients_.addClientGp(clientNum, SV_GpForXp(awardedXp)));
```

**⇒ 六层**：
```text
1. **故意的【无闸写入器**】
2. ⇒ **因为这段跑在比赛【已决出之后**】**
3. ⇒ **而 `ServerCore` 的包装器【在 `matchStatus_.completed` 处停**】**
4. ⇒ **⇒ 所以带闸的版本会【丢掉它**】
5. ⇒ **所以用【不带闸的那个 `addClientGp`**】
```

**✅ ⭐ **一个"闸门与用途冲突"的精确处置**。**

**✅ 与 §405 的"三分锁规则（谁调用决定取不取锁）"**同族（**第二次"按调用点选择 API 变体"）。**

## 五、**`pm_type 5` 早发的四个症状**（本组第四重要）

### 5.1 那段

```php
// INTERMISSION STARTS AT +17000, NOT AT +0, AND A PLAYER CAUGHT THIS
// AFTER IT HAD BEEN WRONG FOR DAYS: "when the game is technically over
// it removes the players instead of keeping your viewhands and guns on
// the screen while it waits for the podium scene, it drops your head
// down to the floor and removes everything, you can still move but it's
// janky and you're invisible."
//
// This function used to apply pm_type 5 and eFlags 16 the instant
// matchStatus_.completed went true and hold them for the whole
// 32.7-second schedule. The demo puts the player into intermission on
// ONE frame -- serverTime 648700, the `s ui_match_complete "1"` frame,
// +17000 -- and leaves them entirely alone before it. The outro at
// +11100 is meant to play over a NORMAL player, which is the whole
// reason `u 10` shows your own body in third person.
//
// Everything the player described follows from the early flag: pm_type
// 5 stops the viewmodel being drawn, an intermission with no view
// height puts the eye at the feet, and the SERVER's own pmove keeps
// simulating the player as pmType 0 while the snapshot claims 5, so the
// client predicts a frozen player against a moving one.
```

### 5.2 二十层

```text
1. **中场休息从 `+17000` 开始，不是 `+0`**
2. ⇒ **一个玩家在它【错了好几天**】之后抓到了它
3. ⇒ **原话**：「当比赛技术上结束时，它【把玩家移走**】而不是在被等待 podium 场景时**把你的 viewhands 和枪留在屏幕上**，它**把你的头掉到地板上并移走一切**，你**还能动但很别扭而且你是不可见的**」
4. ⇒ **这个函数过去在 `matchStatus_.completed` 变真的【那一刻】就施加 `pm_type 5` 与 `eFlags 16`**
5. ⇒ **并【保持整整个 `32.7` 秒日程**】**
6. ⇒ **而 demo 在【一帧】上把玩家放进中场休息**（`serverTime 648700`，那个 `s ui_match_complete "1"` 帧，`+17000`）
7. ⇒ **在那之前【完全不动他们**】**
8. ⇒ **`+11100` 的 outro 意在【一个正常的玩家】之上播放**
9. ⇒ **那正是 `u 10` 显示你自己的身体的【全部理由**】
10. ⇒ **玩家描述的一切【都从那早期旗标流出**】：
      · **`pm_type 5` 停止绘制 viewmodel**
      · **一个没有视角高度的中场休息【把眼睛放到脚上**】
      · **服务器自己的 pmove 【继续把玩家当 `pmType 0` 模拟**】**
      · **而快照声称 `5`**
11. ⇒ **⇒ 所以客户端预测一个【冻结的玩家】去对抗一个【移动的】**
```

### 5.3 ⭐⭐⭐ **"四个症状从一个早期旗标流出"**

**✅ 这是本报告里**最完整的因果分解**。**

**⇒ 四层**：
```text
症状 1：**移走玩家/viewhands 消失** ⇒ `pm_type 5` 停止绘制 viewmodel
症状 2：**头掉到地板** ⇒ 没有视角高度的中场休息把眼睛放到脚上
症状 3：**还能动但别扭** ⇒ 服务器 pmove 继续动而快照说冻结
症状 4：**不可见** ⇒ `eFlags 16`
⇒ **⇒ 而四个【全部来自同一行早发的旗标**】
```

**✅ 与 §407 的"最后一杀的重生/回放是同根的两次发作"**同族（**第三次"一个根多个症状"）。**

**⚠ 而"错了好几天"⇒ **一个时间跨度**。**

**✅ 与 §355 的"玩家的判决"**第十四次。**

### 5.4 而**"`u 10` 的全部理由是让 outro 在一个正常玩家上播放"**

**✅ 与 §404 的"`u 10` 在死亡时画死亡相机（已由玩家确认）"**完全闭合 ✓

**⇒ 三层**：
```text
`u 10` 在死亡时 ⇒ **死亡相机**（§404，玩家确认）
`u 10` 在比赛末 ⇒ **画你自己的身体的第三人称**
⇒ **⇒ 同一命令两个场合，而第二个【只有在玩家正常时才有意义**】
```

**✅ ⭐ **一个"命令的语义依赖于玩家状态"**。

### 5.5 而**`+16600` 的 podium 人偶比 `+17000` 早 400ms**

```php
// THE FIGURES GO UP 400 MS BEFORE THE PLAYERS COME DOWN, AND THAT GAP IS
// THE POINT. Retail's three podium figures begin at match-end + 16600 and
// its intermission lands at +17000 -- section 120 wrote down "the figures
// spawn 400 ms BEFORE the players are removed" and nothing ever acted on
// it. This server spawned them on the SAME frame as the intermission.
//
// A retail figure carries `tag_origin` as its base model (140b): it has no
// mesh of its own and the client builds the character from field 49 and
// that client's live presentation. Doing that on the frame the players are
// torn down leaves nothing to build from, which is exactly what a player
// reports -- "they are not present at all in the podium camera".
//
// MEASURED, not reasoned: `demoq phases` reads outro-figures at +16600 on
// retail's demo and +17000 on ours, against the same match-end anchor.
```

**⇒ 十二层**：
```text
1. **人偶比玩家被移除【早 400ms 升起】**
2. ⇒ **而那个间隙【就是重点**】**
3. ⇒ **零售三个人偶从 `+16600` 开始，而中场休息落在 `+17000`**
4. ⇒ **第 120 节写下了"人偶在玩家被移除前 400ms 生出"而【从来没有东西按它行动**】**
5. ⇒ **这个服务器在【与中场休息同一帧】生出它们**
6. ⇒ **一个零售人偶携带 `tag_origin` 作为它的基础模型**（第 140b 节）
7. ⇒ **⇒ 它【没有自己的网格**】**
8. ⇒ **而客户端【从字段 49 与那个客户端的【实时表现】构建角色**】**
9. ⇒ **在玩家被拆掉的那一帧做那件事【没有东西可构建**】**
10. ⇒ **而那正是玩家报告的："他们在 podium 相机里【根本不存在**】"**
11. ⇒ **这是【测出来的，不是推理的**】**：`demoq phases` 在零售 demo 上读 `+16600`、在我们上读 `+17000`
```

**✅ ⭐⭐⭐ **"一个测出来的时序差，而它有一个机制解释"** —— 本报告里最完整的一处。**

**⇒ 三层**：
```text
观察：零售 `+16600` / 我们 `+17000`
机制：人偶要从【活玩家的表现】构建 ⇒ 玩家拆掉后【无源】
⇒ **⇒ 所以 400ms 是【功能性的**】不是随意的**
```

**✅ 与 §404 的"延迟是常数；选择是那个竞赛"**相反**（这里**延迟是有功能的**）。

**⚠ 而"第 120 节写下了而从来没有东西按它行动"⇒ **第六次"记录下来了但没接线"**。**

## 六、**`_tp` 调色在【地图自己的 fastfile】里**（本组第五重要）

### 6.1 那段

```php
// AND `d 2557 "<map>_tp"` IS SENT, because the asset question got an
// answer. MEASURED offline from the shipped fastfiles, no launch:
//
//     common_mp.ff        193 vision assets, none ending in _tp
//     mp_rust_long.ff     vision/mp_rust_long.vision
//                         vision/mp_rust_long_tp.vision      <-- exists
//     mp_cross_fire.ff    vision/mp_cross_fire_tp.vision     <-- the
//                         exact name the retail dm demo sends at +17000
//
// A map's `_tp` grade ships in the MAP's own fastfile, not in common,
// which is why the earlier search of common_mp found nothing. A map that
// does not ship one is safe: 0x0046CEF0 and 0x0046CE80 write their state
// record ONLY if DB_FindXAssetHeader succeeded (§99), so a missing asset
// leaves the previous grade in place instead of falling back to
// 'default'.
```

### 6.2 二十层

```text
1. **`d 2557 "<map>_tp"` 被发出去，因为【资产问题得到了一个答案**】**
2. ⇒ **离线测量，从随货的 fastfile，【不启动**】**
3. ⇒ **`common_mp.ff`：【193 个 vision 资产，没有一个以 `_tp` 结尾**】**
4. ⇒ **`mp_rust_long.ff`：**
      · **`vision/mp_rust_long.vision`**
      · **`vision/mp_rust_long_tp.vision`** ← **存在**
5. ⇒ **`mp_cross_fire.ff`：`vision/mp_cross_fire_tp.vision`** ← **零售 dm demo 在 `+17000` 发的那个确切的的名字**
6. ⇒ **一张地图的 `_tp` 调色【在【地图自己的 fastfile】里发运，不在 common 里**】**
7. ⇒ **⇒ 那就是为什么【早先在 `common_mp` 里搜什么也没找到**】**
8. ⇒ **一张不发运它的地图是【安全的**】**
9. ⇒ **`0x0046CEF0` 与 `0x0046CE80` **只在 `DB_FindXAssetHeader` 成功时**写它们的状态记录**（第 99 节）
10. ⇒ **⇒ 所以一个【缺失的资产】把上一个调色【留在原地】**，而不是回退到 `'default'`
11. ⇒ **作为 `d` 发在 configstring `2557` 上，正如零售所做的**
12. ⇒ **而不是作为 `N` 命令**
13. ⇒ **⇒ 所以它同时也是【一个在中场休息期间连接进来的客户端会读到的**】
```

### 6.3 ⭐⭐⭐ **"一个 `common_mp` 搜不到的东西在【地图自己的 fastfile】里"**

**✅ 与 §399 的"`cs 1413` 的 `typeByte` 来自客户端资产集"**同族（**第十次"一个数字的含义取决于已加载的资产"）。**

**⇒ 三层**：
```text
搜索范围：`common_mp.ff` ⇒ **0 个 `_tp`**
而资产确实存在 ⇒ **在【每张地图自己的 fastfile**】
⇒ **⇒ 所以"搜不到"≠"不存在"，而是【搜错了地方**】
```

**✅ ⭐ **一个精确的"负面结论的边界"**。**

**⚠ 而"`0x0046CEF0`/`0x0046CE80` 只在 `DB_FindXAssetHeader` 成功时写状态记录"⇒ **一个极重要的安全性质**。**

**⇒ 三层**：
```text
成功 ⇒ **写状态记录，调色改变**
失败 ⇒ **【不写**，保持上一个
⇒ **⇒ 所以"发一个不存在的 vision 名"是【无害**】的**
```

**✅ 与 §403 的"写 configstring 本身无副作用，不认也无害"**同族（**第二次"无害的失败**）。**

**⇒ 而这条与 §406 的"`'default'` 平光"**对照**（**那是【从未告诉】的回退，不是【告诉了一个不存在的名字**】）。**

**✅ ⭐ **一个精确的区分**：**
```text
从未发 `N` ⇒ **回退到 `'default'`（平光）**
发了不存在的名字 ⇒ **保持上一个**（因为 DB 失败）
```

**✅ **这是本报告里最实用的一条**（它说"多试几个名字"是安全的）。

### 6.4 而**"作为 `d` 而不是 `N`"**

**⇒ 四层**：
```text
`N "<name>" <blend>`  ⇒ **一条可靠命令** ⇒ **只对当前的接收者**
`d 2557 "<name>" <blend>` ⇒ **一个 configstring** ⇒ **任何【连接进来的人】都读它**
⇒ **⇒ 所以中场休息期间加入的人【也被正确调色**】
```

**✅ 与 §407 的"`visionAnnounced_` 保证晚加入的也被调色"**同族（**第二次"晚加入者**）。**

**⇒ 三层**：
```text
`N`：按客户端，记 `visionAnnounced_`
`d 2557`：**全局状态**，晚加入者自然读到
⇒ **⇒ 两条通道两种晚加入覆盖**
```

## 七、**32.7 秒日程的完整表**

```text
+0 ms       d 15 0; d 464 0; H; r; L 6 1, L 3 2, L 1 3 (top three);
            sixteen `|` precaches; d 479 1; p 2131
+11100 ms   r; H; N "mp_cross_fire" 0; i; u 10; L 2 7
+13950 ms   d 11861 645750 1000 1 0.25      timescale 1 -> 0.25
+15450 ms   d 11861 647250 1000 0.25 1      and back
+17000 ms   s ui_match_complete "1"; > 161; s 2972 "1";
            d 2557 "mp_cross_fire_tp" 0; d 13 <fog>; d 792
+17400 ms   r; H; I; i; the four top3_*_current_weapon dvars; q 19
+32700 ms   t "EXE_MATCHENDED"
```

**⇒ 七层时间戳 + 七组命令。**

**⚠ 而"`+13950` / `+15450`"与代码里的 `OutroSlowMotionStartMilliseconds = 14'000` / `OutroSlowMotionEndMilliseconds = 15'500`**差 `50ms`**。**

**⇒ 那是**刻意的后拨**（`OutroTimescaleBackdateMilliseconds = 50`）。

**✅ 与"零售的斜坡开始时间比携带它的帧【早 50ms】**"完全闭合 ✓

**⇒ 三层**：
```text
demo：`d 11861 645750 ...` 在 `645800` 发出
⇒ **起点 `645750` = 帧时间 `-50`**
代码：`start = now - 50`
⇒ **⇒ 所以"当客户端读到它时斜坡已经在跑"**
```

**✅ ⭐ **一个"一个服务器帧的提前量"的精确复现**。

## 八、**"不出门就不发"的四个明确理由**

```php
// STILL NOT SENT, each for a stated reason rather than for lack of a value:
// the sixteen `|` precaches and the four top3_* dvars name the podium
// players' character-model and weapon assets, and per-client character
// customization is the one blocked subsystem (section 82e); the timescale
// ramp at +13950/+15450 slows time for a camera move whose framing we have
// not measured; `>`, `s 2972`, `d 479` and `d 13` are that match's values
// on handlers that are still unnamed.
```

**⇒ 三层**：
```text
不发的东西【每一个都有一个陈述的理由，而不是因为缺值**】：
  · `|` 预缓存 + 四个 `top3_*` ⇒ **它们命名 podium 玩家的角色/武器资产，而【逐客户端角色自定义是唯一被阻塞的子系统**】
  · `+13950`/`+15450` 时间缩放 ⇒ **为一个**我们尚未测量其取景**的相机移动**放慢时间**
  · `> 161` / `s 2972` / `d 479` / `d 13` ⇒ **那是那场比赛的**值**，落在**仍未命名**的处理器上**
```

**✅ ⭐ **"每一个都有一个陈述的理由，而不是因为缺值"** —— 一个**极高的工程标准**。**

**⚠ 而其中两条【后来被推翻了**】：
```text
`|` 预缓存 ⇒ **§408 下文说"不需要新子系统"**（已经发）
`s 2972` / `> 161` ⇒ **§407 说加了**
```
⇒ **一个【注释与代码不同步】的实例**。

**✅ 与 §407 的"`elapsed >= 0` 读起来像一个阈值"**同族（**第二次"注释落后于代码"）。**

**⇒ 三层**：
```text
注释：`STILL NOT SENT` 列表
代码：`podiumRosterAsked_` 已发 `|` + `L`，`outroPodiumStateAsked_` 已发 `> 161` `s 2972`
⇒ **⇒ 所以这份列表【部分过期**】
```

**✅ ⭐ **一个诚实的阅读结论：注释是一份更早的状态**。

## 九、关键结论

1. **⭐⭐⭐ `d 15 0` / `d 464 0` 是"两个从 `out.exe` 读出【而不是从线上读出】"的数字的独立确认** —— 第二条独立路径给出同一个数。
2. **"直到 `SV_SetConfigString` 存在之前没有发送的办法 ⇒ 倒计时在一场已决出的比赛中继续走"`** —— 第十二次"定义了但没接线"。
3. **⭐⭐⭐ 结算屏的病历**：**"日志证明判定全对（`reason=scoreLimit tf=150 sc=31 winner=Tf`），缺的只是结算屏没被打开；我方原来只在 campaign 分支发过 `ui_match_complete`，多人模式从来没发"`** —— 第八次"沉默的诊断"，第二次"分模式的路径覆盖"。
4. **⭐ `+1799` 逐字节闭合**：**`xp 5997 → 7796` 的差正好是 `+1100` 处 HudElem 显示的奖励数** —— 第二次"两个数同值 ⇒ 同物"。
5. **⭐⭐ "在 `+1100` 处重算过去会让 AAR 停在零，也可能在那个延迟期间一个槽或段位变化而导致不一致 ⇒ 所以【在转移那一刻冻结】"`** —— 第三次"陈旧的计算"。
6. **⭐ "故意的无闸写入器：这段跑在比赛已决出之后，而 `ServerCore` 的包装器在 `matchStatus_.completed` 处停，所以带闸的版本会丢掉它"`** —— 第二次"按调用点选择 API 变体"。
7. **⭐⭐⭐ `pm_type 5` 早发的四个症状从一个旗标流出**：**"它把玩家移走（`pm_type 5` 停止绘制 viewmodel）、把你的头掉到地板上（没有视角高度的中场休息把眼睛放到脚上）、你还能动但别扭（服务器 pmove 继续当 `pmType 0` 模拟而快照声称 `5`）、而且你是不可见的（`eFlags 16`）"`** —— 第三次"一个根多个症状"。
8. **"中场休息从 `+17000` 开始而不是 `+0`；`+11100` 的 outro 意在【一个正常的玩家】之上播放，那正是 `u 10` 显示你自己身体的全部理由"`** —— 一个"命令语义依赖玩家状态"的实例。
9. **⭐⭐⭐ podium 人偶比玩家被移除早 `400ms`，而【那个间隙就是重点】**：**"人偶携带 `tag_origin` 作基础模型（没有自己的网格），客户端从字段 49 与该客户端的【实时表现】构建角色；在玩家被拆掉的那一帧做那件事没有东西可构建 —— 正是玩家报告的『他们在 podium 相机里根本不存在』"`**。**测出来的**（`demoq phases`：零售 `+16600` / 我们 `+17000`）。
10. **"第 120 节写下了『人偶在玩家被移除前 400ms 生出』而从来没有东西按它行动"`** —— 第六次"记录下来了但没接线"。
11. **⭐⭐⭐ `_tp` 调色在【地图自己的 fastfile】**：**`common_mp.ff` 193 个 vision 资产、没有一个 `_tp`；而 `mp_rust_long.ff` 与 `mp_cross_fire.ff` 各自带 `_tp`** —— 第十次"一个数字的含义取决于已加载的资产"，也是**一个精确的"负面结论的边界"**。
12. **⭐⭐ "`0x0046CEF0`/`0x0046CE80` 只在 `DB_FindXAssetHeader` 成功时写状态记录 ⇒ 缺失的资产把上一个调色留在原地，而不是回退到 `'default'`"`** ⇒ **"发一个不存在的 vision 名是无害的"** —— 与 §406 的"从未发 ⇒ 回退到平光"是一个精确的对照。
13. **"作为 `d 2557` 发而不是 `N`，所以它也是一个在中场休息期间连接进来的客户端会读到的"`** —— 第二次"晚加入者覆盖"（`N` 用 `visionAnnounced_` 按客户端，`d` 用全局状态）。
14. **32.7 秒完整日程**：`+0` / `+11100` / `+13950` / `+15450` / `+17000` / `+17400` / `+32700`，而 **`d 11861` 的起点是【帧时间减 50ms】**（一个服务器帧的提前量）。
15. **⭐ "不发的东西每一个都有一个陈述的理由，而不是因为缺值"`** —— 但**这份列表【部分过期】**（`|` 预缓存、`> 161`、`s 2972` 后来都加了）。第二次"注释落后于代码"。

## 十、未闭合点

- `s 2972` 是否在两处（`announceMatchCompletion` 与 `+17000`）重复发。
- `> 161` 的两个门控旗标。
- `I 17433 0 0` 的语义（`109b` 列了它的 callee）。
- `d 13` 的十一个 fog token 的语义。
- `i 0 0.000000 0 1` 的语义。
- `SvKillCamPreKillMilliseconds` 的值（`16450 = 11100 + 5350`）。
- `sv_main_mp.cpp` 7250 行之后未读取。
