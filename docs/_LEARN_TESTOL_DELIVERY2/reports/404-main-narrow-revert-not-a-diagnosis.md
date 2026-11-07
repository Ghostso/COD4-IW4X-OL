# 404 · **"这是【一个窄回退】，不是一个诊断"** —— 撤掉 `a <weapon>`、`1500ms` 的竞赛、cha 的 `p 12`+`p 21` 是按次数统计定的

## 一、范围

本报告学习 `sv_main_mp.cpp` 4850–5200 行。

## 二、**撤掉 `a <weapon>` 的窄回退**（本组最重要的一段）

### 2.1 那段

```php
// `a <weapon>` USED TO GO HERE AND IS WITHDRAWN. It was added in
// 140j from the demo -- retail sends `a 1297` on the first spawn
// and all 24 respawns -- and what `a` DOES was inferred from the
// value, never measured.
//
// A player: "killing the guy still crashed his client". The client's
// own crash report puts the access violation on the respawn frame,
// microseconds after this cluster, in a TAG-MATRIX lookup against a
// DObj that is not there (141d/141e). `a` is the one command in the
// cluster this session added, it is the least established thing in
// it, and a weapon command resolving a hand tag on a player whose
// model is still being rebuilt is exactly that fault's shape.
//
// THIS IS A NARROW REVERT, NOT A DIAGNOSIS. The same crash fired
// once on a build with no `a` at all, so removing it may change
// nothing -- in which case it has still eliminated the newest
// suspect, which is worth one cycle. Nothing a player can see is
// lost: the weapon already reaches the client as playerState field
// 39 and on the entity.
```

### 2.2 十八层

```text
1. **`a <weapon>` 曾经在这里而【被撤回**】**
2. ⇒ **它是在 `140j` 从 demo 加的**：**零售在首生与全部 24 次重生都发 `a 1297`**
3. ⇒ **而 `a` 【做什么】是从【值】推断的，从未测量**（推测）
4. ⇒ **一个玩家：「杀了他仍然崩了他的客户端」**
5. ⇒ **客户端自己的崩溃报告把访问违例放在【重生帧**】**
6. ⇒ **在那个簇之后【几微秒**】**
7. ⇒ **在一个对一个【不存在的 DObj】的 `TAG-MATRIX` 查找里**（`141d`/`141e`）
8. ⇒ **`a` 是这个簇里【本次会话加的唯一一条命令**】**
9. ⇒ **它是里面【最没有确立**】的东西**
10. ⇒ **而一条武器命令在一个【模型还在重建**】的玩家身上解析一个【手部 tag**】**
11. ⇒ **正是那个故障的【形状**】**
12. ⇒ **这是一个【窄回退**】，不是一个【诊断**】**
13. ⇒ **同一个崩溃在一个【完全没有 `a`】的 build 上也曾触发过一次**
14. ⇒ **所以移除它【可能什么也不改变**】**
15. ⇒ **而在那种情况下它仍然【排除掉了最新的嫌疑**】**（值得一个周期）
16. ⇒ **玩家能看见的东西【什么也没丢失**】**
17. ⇒ **武器已经作为 `playerState` 字段 39 与实体到达客户端**
```

### 2.3 ⭐⭐⭐ **"这是一个窄回退，不是一个诊断"**

**✅ 这是本文件里**最重要的一个工程诚实**。**

**⇒ 三层**：

```text
回退：移除最新嫌疑 ⇒ **可能无效**
诊断：【已知根因**】⇒ 移除即修复
⇒ **⇒ 而这里明确说"不是诊断"**
```

**✅ 与 §390 的"那是一个合理的猜测而不是这个服务器所发的"**同族（**第二次"明确区分猜测与知识"）**。**

**⚠ 而"同一崩溃在一个【完全没有 `a`】的 build 上也触发过"⇒ **一个决定性的反面证据**。**

**✅ ⭐ **"所以移除它可能什么也不改变"** —— **一个诚实的预测**。**

### 2.4 而**"排除掉最新的嫌疑（值得一个周期）"**

**✅ 与 §402 的"一次一个缺失命令花了四个周期"**同族（**第二次"每个实验的代价"。**

**⇒ 三层**：

```text
一个周期 = 一次构建 + 一次运行
⇒ **而"排除嫌疑"是【一个合法的产出**】
⇒ **⇒ 即使不修好任何东西**
```

**✅ ⭐ **"值得一个周期"** —— 一个**精确的价值判断**。**

### 2.5 而**"玩家能看见的东西什么也没丢失：武器已经作为 `playerState` 字段 39 与实体到达客户端"**

**✅ 与 §352 的"三个武器出现机制"**完全闭合 ✓

**⇒ 三层**：

```text
`a <n>`           ⇒ **cgame 画一把它必须已拥有的武器**
`playerState` 39  ⇒ **权威的当前武器**
实体              ⇒ **投影**
⇒ **⇒ 所以撤 `a` 只是【不主动画】，而武器仍在**
```

**✅ ⭐ **一个"能安全撤掉"的证明**。**

**⚠ 而"字段 39"⇒ 与 §370 的"`currentWeaponAssetIndex` 是 netfield 39"**完全一致 ✓

**⇒ **第三次确认 `39`。**

## 三、**`1500ms` 的竞赛**（本组第二重要）

### 3.1 那段

```php
// THE KILLCAM FIRES 1500 ms AFTER THE DEATH SCREEN, IF STILL DEAD.
// Armed on the death edge below and fired here so that a respawn
// arriving first simply disarms it -- which is exactly what retail
// does: seven of its twenty-four deaths get a killcam and the other
// seventeen are the ones whose respawn cluster went out at the same
// 1500 ms mark. The delay is constant; the selection is the race.
```

### 3.2 十三层

```text
1. **击杀回放在死亡屏之后 `1500ms` 触发，如果【仍然死亡**】**
2. ⇒ **在下面的死亡边沿武装而在这里触发**
3. ⇒ **所以一个【先到达的重生】简单地解除它**
4. ⇒ **而那正是零售所做的**：
      · **它的 24 次死亡里的【七次】得到一个 killcam**
      · **而另外十七次是那些重生簇在同一个 `1500ms` 标记上发出的**
5. ⇒ **延迟是常数**
6. ⇒ **而选择是那个【竞赛**】**
```

### 3.3 ⭐⭐ **"延迟是常数；选择是那个竞赛"**

**✅ 这是本文件里**最精巧的一个机制解释**。**

**⇒ 三层**：

```text
观察：24 次死亡只有 7 次有 killcam
朴素推断：**某种选择逻辑**（按击杀类型？按距离？）
真相：**延迟固定 1500ms 而重生也大约在那时 ⇒ 一个竞赛**
```

**✅ ⭐ **"选择是那个竞赛"** —— 一个**极简洁的、反直觉的解释**。**

**⚠ 而"7/24"⇒ **`29%`**。**

**✅ 与 §384 的 `73/163`、§375 的 `294`**第十六次大规模统计。

### 3.4 而**"最终击杀得不到私有回放"**

```php
// THE FINAL KILL GETS NO PRIVATE KILLCAM. Its victim's death edge
// lands one frame BEFORE the match is announced complete, so the
// arm happens and then the outro starts -- and 1500 ms later a
// death killcam fired for one player while everybody else was
// already in the end-of-match hold. Measured: armed at serverTime
// 15000, `match complete` at 15050, fired at 16500.
//
// Suppressing the EDGE is not enough, because the edge is what got
// in first. The FIRE has to check too, and the match-end killcam at
// +11100 is the one everybody sees.
if (life.killCamAt && matchStatus_.completed) { disarm + log }
```

**⇒ 十一层**：

```text
1. **最终击杀得不到【私有的**】回放**
2. ⇒ **它的受害者的死亡边沿落在比赛被宣告完成【一帧之前**】**
3. ⇒ **所以武装发生了然后 outro 开始**
4. ⇒ **而 `1500ms` 后一个死亡回放为【一个玩家】触发而其他人【已经在结束保持里**】**
5. ⇒ **测量：`1500` 武装、`15050` 比赛完成、`16500` 触发**
6. ⇒ **【压制那个边沿是不够**】的**
7. ⇒ **因为【边沿是先到的**】**
8. ⇒ **【触发也必须检查**】**
9. ⇒ **而 `+11100` 的比赛末回放是【所有人看到的那个**】**
```

**✅ ⭐ **"压制边沿是不够的，因为边沿是先到的"** —— 一个**精确的时序论证**。**

**⚠ 而"`15000` → `15050` → `16500`"⇒ **三个精确的时间戳**。**

**✅ 与 §391 的"`10:51`"**同族（**第四次"精确时间戳"）。**

## 四、**cha 的 `p 12` + `p 21` 按次数统计定**（本组第三重要）

### 4.1 那段

```php
// ★★ 28100 刀BD（第 2/3 项：击杀/死亡音）—— **按次数统计**定的，不是按位置猜：
//   零售 cha `0C-2020-4-11[11-11-11]cha.demo`（662 条、19 次死亡）里，
//   「每次 `u 10` 之后 30 条内出现的 `p`」计数：
//     p 12  ×23（全片 32 次 ⇒ 72% 集中在死亡后）
//     p 21  ×23（全片 36 次 ⇒ 64%）
//     p 1586 ×4 （全片 4 次 ⇒ 我方上一版当成死亡播报是**错的**，已撤）
//   ⇒ cha 的死亡/击杀音就是 **`p 12` + `p 21`**。
// ★★★ 刀BM（修正刀BK）：**cha 的击杀音索引是 `p 21` + `p 12`，不是 dm 的 16/14**。
//   交叉核对（同为 mp_nuked，按"死亡后 30 条内 `p` 频次"统计）：
//     零售 **dm**  → `p 16` ×21/40、`p 14` ×17/39
//     零售 **cha** → `p 21` ×23、`p 12` ×23
//   ⇒ **同一张图、不同 gametype，索引不同**（正合我方注释
//     "THE INDICES ARE PER-GAMETYPE and do not transfer"）。
//   我上一刀（刀BK）把 dm 的 16/14 用到 cha，方向错了。
//   ⚠ 重要：刀BD 最早给 cha 的就是 12/21，但**甲方那次测试跑的是旧二进制**
//     （15:36 那局 vs 15:37 才部署刀BD）⇒ **12/21 从未被真正测过**。
```

### 4.2 二十层

```text
1. **按【次数统计】定的，不是按【位置】猜**
2. ⇒ **零售 cha `0C-2020-4-11[11-11-11]cha.demo`（`662` 条、`19` 次死亡）**
3. ⇒ **「每次 `u 10` 之后 `30` 条内出现的 `p`」计数**：
      · **`p 12` ×23**（全片 `32` 次 ⇒ **`72%` 集中在死亡后**）
      · **`p 21` ×23**（全片 `36` 次 ⇒ **`64%`**）
      · **`p 1586` ×4**（全片 `4` 次 ⇒ **我方上一版当成死亡播报是错的，已撤**）
4. ⇒ **所以 cha 的死亡/击杀音就是 `p 12` + `p 21`**
5. ⇒ **修正刀BK：cha 的击杀音是 `p 21` + `p 12`，不是 dm 的 `16/14`**
6. ⇒ **交叉核对（同为 `mp_nuked`，按"死亡后 `30` 条内 `p` 频次"统计）**：
      · 零售 **dm** → **`p 16` ×21/40、`p 14` ×17/39**
      · 零售 **cha** → **`p 21` ×23、`p 12` ×23**
7. ⇒ **同一张图、不同 gametype，索引不同**
8. ⇒ **正合我方注释 "THE INDICES ARE PER-GAMETYPE and do not transfer"**
9. ⇒ **我上一刀（刀BK）把 dm 的 `16/14` 用到 cha，【方向错了**】**
10. ⇒ **⚠ 重要：刀BD 最早给 cha 的就是 `12/21`**
11. ⇒ **但【甲方那次测试跑的是旧二进制**】（`15:36` 那局 vs `15:37` 才部署刀BD）
12. ⇒ **⇒ `12/21` 【从未被真正测过**】**
```

### 4.3 ⭐⭐⭐ **"按次数统计定的，不是按位置猜"**

**✅ 与 §403 的"错位取证：它在 demo 里出现的位置未必是开局"**完全闭合 ✓

**⇒ 三层**：

```text
§403  错位取证 ⇒ **"位置"不可靠**
§404  正确方法 ⇒ **"每次 `u 10` 之后 30 条内的频次"**
⇒ **⇒ 一个【条件频次**】统计**
```

**✅ ⭐ **"条件频次"** —— 一个**极精确的统计方法**（不是简单计数）。

**⚠ 而"`72%` / `64%` 集中在死亡后"⇒ **一个可判定的阈值**。**

**✅ 与 §403 的"`175` 份 demo 统计"**同族（**第三次"条件统计"）。**

### 4.4 而**"同一张图、不同 gametype、索引不同"**

**✅ 与 §398 的"`cs 189` 在 zm 是 `battery_multiplier` 而在 dm 是 `ui_bossBodyDestroyedInfo`"**完全闭合 ✓

**⇒ **第六次确认"索引逐 gametype"。**

**⚠ 而"我上一刀把 dm 的 `16/14` 用到 cha，方向错了"⇒ **一个明确的错误记录**。**

**✅ 与 §403 的"`mpnuke` 的错位取证"**同族（**第二次自我更正）。**

### 4.5 而**"甲方那次测试跑的是旧二进制"**

**✅ 与 §355 的"玩家的判决"**第十三次。**

**⇒ 三层**：

```text
部署：`15:37` 才部署刀BD
测试：**`15:36` 那局**
⇒ **⇒ 所以那次测试【测的是旧二进制**】**
```

**✅ ⭐ **一个极重要的"测试有效性"检查**。**

**⚠ 而"`12/21` 从未被真正测过"⇒ **所以它仍是【一个假设**】。**

**✅ 与 §397 的"一个结果在两种假设下都成立 ⇒ 零信息"**同族（**第二次"实验无效"。**

## 五、**`w 2 4 0` 的"死后收枪"**（本组第四重要）

### 5.1 那段

```php
// ★★ 28100 刀BG（第 6 项「死后摄像机挂枪」）——
//   零售死亡段（`0C-2020-4-11[12-19-23]dm.demo`）逐条：
//     u 10 → p 1586 → **w 2 4 0** → **w 2 4 0** → r 2/r 3/r 1/v 18 → u 11 → a 1221
//   ⇒ **死亡瞬间零售会连发两次 `w 2 4 0`（切武器/视角槽）把枪收起来**，
//     武器 `a` 只在**重生之后**才发。
//   我方原来死亡时一条 `w` 都没有 ⇒ 死亡镜头里还挂着枪。
//   本刀只补这两条（与零售同形），**不动 `a` 的发送路径**（那条路有 5 个发射点，盲改风险大）。
ask(client.clientNum, "w 2 4 0", "death stow 1");
ask(client.clientNum, "w 2 4 0", "death stow 2");
```

### 5.2 十一层

```text
1. **零售死亡段逐条**：
      · `u 10`
      · **`p 1586`**
      · **`w 2 4 0`**
      · **`w 2 4 0`**
      · `r 2`/`r 3`/`r 1`/`v 18`
      · `u 11`
      · **`a 1221`**
2. ⇒ **死亡瞬间零售会【连发两次】 `w 2 4 0`（切武器/视角槽）把枪收起来**
3. ⇒ **武器 `a` 只在【重生之后**】才发**
4. ⇒ **我方原来死亡时【一条 `w` 都没有**】**
5. ⇒ **⇒ 死亡镜头里【还挂着枪**】**
6. ⇒ **所以只补这两条（与零售同形）**
7. ⇒ **不动 `a` 的发送路径**（**那条路有 5 个发射点，盲改风险大**）
```

### 5.3 ⭐ **"那条路有 5 个发射点，盲改风险大"**

**✅ 与 §402 的"四个周期与四个负面"**同族（**第三次"改动的风险评估"。**

**⇒ 三层**：

```text
`a` 的发送路径：**5 个发射点**
⇒ **所以盲改会影响 5 处**
⇒ **⇒ 权衡后不动**
```

**✅ 一个**明确的风险-收益判断**。**

**⚠ 而"`P 1586`"⇒ 与 §403 的"`p 1586` ← 死后播报（下一刀的死亡簇也要用）"**完全闭合 ✓

**⇒ 而 §404 二.5 说 `p 1586` **是军犬音不是死亡播报**。**

**⇒ 三层**：

```text
§403  说"`p 1586` ← 死后播报"
§404  说"`p 1586` 是军犬连杀的音，不是死亡播报 ⇒ 已撤"
⇒ **⇒ 一个自我更正**
```

**✅ 第五次确认那个撤回。**

## 六、**`i 0 0.000000 0 1` 的"恰好八帧"**

### 6.1 那段

```php
// ONE RELIABLE COMMAND, ON THE SAME FRAME AS THE FOUR
// FIELDS. In the demo `i 0 0.000000 0 1` appears on
// exactly the eight frames the killcam fields are
// asserted on and on no other frame in ten minutes.
ask(client.clientNum, "i 0 0.000000 0 1", "killcam");
```

### 6.2 六层

```text
1. **一条可靠命令，与那四个字段【同一帧**】**
2. ⇒ **在 demo 里 `i 0 0.000000 0 1` 恰好出现在那八个击杀回放字段被断言的帧上**
3. ⇒ **而在十分钟里【没有别的帧**】**
4. ⇒ **⇒ 所以是一个 8/8 的精确配对**
```

**✅ 与 §370 的"十次按键十条命令"**同族（**第六次"精确配对"）。**

**⚠ 而"八帧"⇒ 与 §380 的"demo 的全部八次 killcam"**完全一致 ✓

**⇒ **第二次确认那个 8。**

**✅ 与 §404 三.3 的"24 次死亡里的七次"**不同**（**8 个 killcam 帧 vs 7 次死亡**）。

**⚠ 一处**需要核对的差异**（可能是 8 个字段断言帧对应 7 次死亡 + 1 次比赛末）。**

**✅ 而 §404 二.4 说"+11100 的比赛末回放是所有人看到的那个"⇒ **所以第 8 次是比赛末的**。**

**✅ **完整闭合**（7 次私有 + 1 次比赛末 = 8）。

## 七、**`SvDeathViewMilliseconds` 与四个字段的关系**

```php
// 28800/29200: phase one. 2697 keeps `sessionstate = "dead"` with
// the view on the body for 1.5 s (`_damage.gsc:857-884`) and only
// then hands it to the replay. During this window the four
// killcam fields stay ZERO so the client draws its own
// third-person body camera instead of a spectator target.
life.deathViewUntil = serverTime + SvDeathViewMilliseconds;
world_.setPlayerDeathView(client.clientNum, serverTime + SvDeathViewMilliseconds);
static_cast<void>(world_.clearPlayerKillCam(client.clientNum));
static_cast<void>(world_.clearPlayerKillcamReplay(client.clientNum));
```

### 7.1 九层

```text
1. **阶段一**：**2697 保持 `sessionstate = "dead"` 而视角在身体上 `1.5` 秒**（`_damage.gsc:857-884`）
2. ⇒ **然后才交给回放**
3. ⇒ **在这个窗口里那四个击杀回放字段【保持零**】**
4. ⇒ **所以客户端画【它自己的第三人称身体相机**】而不是一个旁观目标**
5. ⇒ **所以 `deathViewUntil = now + SvDeathViewMilliseconds`**
6. ⇒ **并 `clearPlayerKillCam` 与 `clearPlayerKillcamReplay`**
7. ⇒ **⇒ 一个"两阶段"的死亡相机**
```

**✅ 与 §380 的"`setPlayerIntermission` 的相机是一个地方"**同族（**第二次"相机状态机"。**

**⚠ 而"`1.5` 秒"⇒ 与 §404 三 的"`1500ms` 的延迟"**同值。**

**⇒ 三层**：

```text
阶段一：`1500ms` 的身体相机
阶段二：**`1500ms` 之后的回放**（若仍死亡）
⇒ **⇒ 两个 `1500ms`**
```

**✅ ⭐ **一个"串联的两个 1500ms"** 的设计。**

**⚠ 所以死亡后总时长 = `1500 + 2500 + 2000 = 6000ms`。**

**✅ 与 §404 三.4 的"`SvKillcamReplayLengthMs = 2500` / `SvKillcamPostDelayMs = 2000`"**完全闭合 ✓

## 八、关键结论

1. **⭐⭐⭐ "这是一个【窄回退】，不是一个【诊断】"`** —— 撤掉 `a <weapon>`，而 **"同一崩溃在一个【完全没有 `a`】的 build 上也触发过一次 ⇒ 所以移除它可能什么也不改变"`**。
2. **⭐ "而在那种情况下它仍然【排除掉了最新的嫌疑（值得一个周期）】"`** —— 第二次"每个实验的代价"。
3. **"玩家能看见的东西什么也没丢失：武器已经作为 `playerState` 字段 39 与实体到达客户端"`** —— 第三次确认 `39`，而这是一个**"能安全撤掉"的证明**。
4. **"`a` 做什么是从【值】推断的，从未测量"`** —— 第二次"明确区分猜测与知识"。
5. **⭐⭐ "击杀回放在 `1500ms` 后触发如果仍死亡；所以先到的重生简单地解除它 —— 而那正是零售所做的：24 次死亡里的七次，另外十七次是重生簇在同一标记上发出 ⇒ 延迟是常数，而【选择是那个竞赛】"`** —— 一个极精巧、反直觉的解释。
6. **⭐ "最终击杀得不到私有回放：边沿落在比赛完成一帧前 ⇒ 武装发生而 outro 开始 ⇒ `1500ms` 后一个死亡回放为一个人触发而其他人已在结束保持里（`1500`/`15050`/`16500`）"`**，而 **"压制边沿是不够的，因为边沿是先到的 ⇒ 触发也必须检查"`**。
7. **⭐⭐⭐ "按【次数统计】定的，不是按【位置】猜"`** —— **"每次 `u 10` 之后 `30` 条内出现的 `p`"** 的条件频次统计：`p 12` ×23（72%）、`p 21` ×23（64%）、`p 1586` ×4（**已撤**）。
8. **⭐ "同一张图、不同 gametype、索引不同"**（dm 的 `16/14` vs cha 的 `21/12`）—— 第六次确认"索引逐 gametype"，而**"我上一刀把 dm 的 `16/14` 用到 cha，方向错了"`**。
9. **⭐⭐ "甲方那次测试跑的是旧二进制（`15:36` 那局 vs `15:37` 才部署）⇒ `12/21` 从未被真正测过"`** —— 第二次"实验无效"，一个**极重要的测试有效性检查**。
10. **⭐ `w 2 4 0` 的死后收枪**：**死亡瞬间零售连发两次 `w 2 4 0` 把枪收起来，而 `a` 只在重生之后发**；我方原来一条 `w` 都没有 ⇒ **死亡镜头里还挂着枪**。
11. **"不动 `a` 的发送路径（那条路有 5 个发射点，盲改风险大）"`** —— 第三次"改动的风险评估"。
12. **⭐ "`i 0 0.000000 0 1` 恰好出现在那八个击杀回放字段被断言的帧上而在十分钟里没有别的帧"`** —— 第二次确认那个 **8**（而**7 次私有 + 1 次比赛末 = 8**）。
13. **⭐ "阶段一：`sessionstate = "dead"` 而视角在身体上 `1.5` 秒，然后才交给回放；在这个窗口里那四个字段保持零 ⇒ 所以客户端画它自己的第三人称身体相机"`** —— 第二次"相机状态机"。
14. **两个串联的 `1500ms`**（身体相机 + 回放延迟），而总时长 = **`1500 + 2500 + 2000 = 6000ms`**。

## 九、未闭合点

- `i 0 0.000000 0 1` 的语义。
- `w 2 4 0` 的三个参数语义。
- `SvDeathViewMilliseconds` / `SvKillCamDelayMilliseconds` / `SvKillCamPreKillMilliseconds` 的值。
- `a` 的五个发射点清单。
- `SV_KillcamArchiveCount` 的实现。
- `sv_main_mp.cpp` 5200 行之后未读取。
