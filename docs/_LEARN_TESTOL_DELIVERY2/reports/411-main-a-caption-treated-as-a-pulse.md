# 411 · **"一个 HUD 文段被当成脉冲字幕而标签被清零"** —— `fadeTime == 0` 五个条件的或、bot 的 team 与 faction 血缘、以及 `-2700` 与 `codol_bot.c` 的血统标注

## 一、范围

本报告学习 `sv_main_mp.cpp` 9768–10426 行（HUD 合成收尾、`nonBotTeamCounts`、`createBotClient`、`driveBotClients` 的常量与状态表）。

## 二、**`writeHudElems` 的"脉冲字幕"判定**（本组最重要的一段）

### 2.1 那段

```php
// 28800: THIS PAIR MUST LOOK LIKE THE OUTCOME BOARD, NOT
// LIKE A PULSE. writeHudElems treats a Text elem with
// fadeTime == 0 AND any of (fadeStartTime, materialIndex,
// width, scaleStartTime, scaleTime) as a PULSED caption and
// zeroes its label -- which is why the caption never drew.
// The outcome board sets alignScreen 0x98 and a glowColor and
// nothing else, so this does the same.
```

### 2.2 十六层

```text
1. **这一对必须【看起来像结果板】，不是像一个脉冲**
2. ⇒ **`writeHudElems` 把一个 `Text` 元件当作【脉冲字幕**】当且仅当**：
      · **`fadeTime == 0`  【且】**
      · **下列五个【任一】**：
          · `fadeStartTime`
          · `materialIndex`
          · `width`
          · `scaleStartTime`
          · `scaleTime`
3. ⇒ **而它【把那个元件的标签清零**】**
4. ⇒ **⇒ 那就是【那个字幕从未被绘制**】的原因**
5. ⇒ **结果板设置 `alignScreen 0x98` 与一个 `glowColor`，【别的什么也不设**】**
6. ⇒ **所以这里做同样的事**
```

### 2.3 ⭐⭐⭐ **"一个五条件的或 ⇒ 标签被清零"**

**✅ 这是本报告里**最重要的一个陷阱**。**

**⇒ 三层**：
```text
意图：**画一段文字**（"等待更多玩家"）
触发：`fadeTime == 0` 且 **五个可选字段任一非零**
结果：**`label` 被清零** ⇒ **文本消失**（但元件仍在 ⇒ 不报错）
```

**✅ 与 §406 的"`'default'` 平光"**同族（**第七次"静默的失败产生可见的缺陷"）。**

**⇒ 三层**：
```text
§406  没发 `N` ⇒ 引擎回退到中性调色 ⇒ **地图是平的**
§411  多设一个字段 ⇒ 引擎把 `label` 清零 ⇒ **字幕不画**
⇒ **⇒ 两条都是【配置正确但结果全无**】
```

**✅ ⭐ **一个"默认/陷阱"的双例**。

**⚠ 而"结果板设置了 `alignScreen 0x98` 与一个 `glowColor`，别的什么也不设"⇒ **一个"最小合法配置"的模板**。**

**✅ 与 §409 的"`sdOriginText` 是模板"**不同（这是**值的最小集**）。

**⇒ 三层**：
```text
`alignScreen = 0x98`（屏幕中心，两轴）
`glowColor = 0xFF000000`
⇒ **⇒ 别的不设 ⇒ 不被当成脉冲**
```

**✅ ⭐ **一个"什么【不】设"决定语义的实例**。

### 2.4 而**数值行的 `0.9375` 与 `(0.16, 0.65, 1)`**

```php
// The number matches 2697's hudsmall at 0.9375 and its
// (0.16,0.65,1) colour. Value, not Text: no label involved.
*dst = {
    .type = SvHudElemType::Value,
    .color = 0xFF29A6FFu,
    .fontScale = 0.9375f,
    ...
};
```

**⇒ 六层**：
```text
1. **`0.9375`** ⇒ **2697 的 `hudsmall`**（`0.9375 = 15/16`）
2. ⇒ **`(0.16, 0.65, 1)`** ⇒ **`0xFF29A6FF`**：
      · `0x29 = 41` ⇒ `41/255 = 0.1608`
      · `0xA6 = 166` ⇒ `166/255 = 0.651`
      · `0xFF = 255` ⇒ `1.0`
3. ⇒ **`Value` 而不是 `Text`** ⇒ **不涉及 `label`** ⇒ **不会命中脉冲陷阱**
```

**✅ ⭐⭐ **一个"用 `Value` 而不是 `Text` 来绕开 `label` 陷阱"的选择**。**

**✅ 与 §411 二.3 的"`label` 被清零"**完全闭合 ✓

**⚠ 而 `0.16 × 255 = 40.8` ⇒ **`41` 是四舍五入**。**

**⇒ 三层**：
```text
精确：`0.16 * 255 = 40.8`
取整：`41`（`0x29`）
或 `40`（`0x28`）
⇒ **⇒ 选了 `41`（四舍五入）**
```

**✅ 一个**需要标注的取整选择**。

## 三、**`archivalHud` 与 `currentHud` 的两层**（本组第二重要）

### 3.1 那段

```php
// The objectives this frame already committed to the world are the
// waypoint source; rebuilding from them keeps one HUD owner without
// making the archival array depend on the SD projector running.
auto archivalHud = SV_BuildObjectiveHudElems(playerState->objectives);
if(matchGameType_=="zm" && archivalHud.back().type==SvHudElemType::Free)
{
    // Reserve one stable prefix slot, preserving every objective.
    // If all 31 slots are occupied, omit optional score feedback.
    std::move_backward(archivalHud.begin(),archivalHud.end()-1,archivalHud.end());
    archivalHud[0]=SV_BuildZmScoreHudElem(...);
}
```

### 3.2 十二层

```text
1. **两层**：
      · `currentHud`  ⇒ **瞬时反馈**（伤害标记/分数弹出/入场 HUD）
      · `archivalHud` ⇒ **目标/持续状态**（waypoint/僵尸计分/复活标记/时钟/结果板）
2. ⇒ **`archivalHud` 从 `playerState->objectives` 【重建**】**
3. ⇒ **⇒ 所以【HUD 只有一个主人】，而不让归档数组依赖 SD 投影器是否运行**
4. ⇒ **`zm` 且最后一个槽是 `Free` ⇒ 【保留一个稳定的前缀槽**】**
5. ⇒ **`std::move_backward(begin, end-1, end)`** ⇒ **整体后移一位**（**保留全部目标**）
6. ⇒ **`archivalHud[0] = 僵尸分数**】**
7. ⇒ **若 31 槽全占 ⇒ `back().type != Free` ⇒ 【不发分数反馈**】**
```

### 3.3 ⭐⭐ **"保留一个稳定的前缀槽"**

**✅ 与 §409 的"元件是位置性的"**同族（**第五次"位置语义"）。**

**⇒ 三层**：
```text
槽 0 ⇒ **僵尸分数**（固定位置）
槽 1..30 ⇒ **目标**
⇒ **⇒ 所以分数【永远在同一个位置**】而目标【整体后移**】
```

**✅ ⭐ **一个"稳定前缀 + 可变后缀"的布局**。

**⚠ 而"31 槽全占 ⇒ 省略可选分数反馈"⇒ **一个明确的优先级**。**

**✅ 与 §410 的"队满 ⇒ 丢弃并记一行"**同族（**第二次"有界 + 明确优先级"）。**

**⇒ 三层**：
```text
§410  splash 队满 ⇒ **丢弃并记一行**（有证人）
§411  HUD 满 ⇒ **静默省略可选反馈**（因为它本身是可选的）
⇒ **⇒ 两个都对，但【第二个不需要证人**（不是数据丢失，是特性降级）
```

**✅ 一个**精确的区分**。

### 3.4 而**"僵尸团灭时清空两层"**

```cpp
if (world_.zombieTeamWiped())
{
    currentHud={}; archivalHud={};
    archivalHud[0]=SV_BuildZombieGameOverHud();
}
```

**⇒ 四层**：
```text
1. **两层【都清空**】**
2. ⇒ **然后只在槽 0 放"游戏结束"**
3. ⇒ **⇒ 所以一个团灭的屏幕上【只有一行**】**
```

**✅ ⭐ **一个"清零一切只留一个"的设计**。

**✅ 与 §407 的"`zm` 团灭路径没有胜利音乐、没有奖励授予、没有 FFA podium"**完全同族（**第二次"zm 团灭是最小路径"）。**

## 四、**`createBotClient` 的 team/faction 三次修正**（本组第三重要）

### 4.1 第 1 次：opposite faction（J4）

```php
// J4: A REAL TEAM THAT IS NOT THE HOST'S. Measured 2026-10-10 37:0x:
// giving the bot a real team made it visible (spawn points filter by
// team, sv_snapshot_mp.cpp:18610-18627) but it inherited the HOST's
// team, so onSameTeam(0, 1) stayed true and finishPlayerDamageBatch
// dropped every hit at :24887 -- visible, shootable, unkillable.
// Spawning needs a real team; mutual damage needs a different one, so
// the bot takes the side OPPOSITE the faction it inherited.
```

**⇒ 十层**：
```text
1. **给 bot 一个真实 team ⇒ 它【可见**】（出生点按 team 过滤）
2. ⇒ **但它继承了【主机的 team**】**
3. ⇒ **所以 `onSameTeam(0, 1)` 【仍然为真**】**
4. ⇒ **而 `finishPlayerDamageBatch` 在 `:24887` 【丢弃每一次命中**】**
5. ⇒ **⇒ 可见、可射、【不可杀**】**
6. ⇒ **出生需要【一个真实 team**】**
7. ⇒ **互相伤害需要【一个不同的 team**】**
8. ⇒ **所以 bot 取【它继承的那个 faction 的对面**】】
```

**✅ ⭐⭐ **"可见、可射、不可杀"** —— 一个极清晰的症状三元组**。**

**✅ 与 §410 的"没有 feed + 击杀时刻的卡顿"**同族（**第二次"两个症状一个根"）。**

### 4.2 第 2 次：`None` 回退

```php
// A BOT NEVER CONFIRMS A CLASS, SO THE MENU THAT ASSIGNS A REAL TEAM
// NEVER RUNS FOR IT. Measured 2026-10-10 33:0x, mp_crash_tropical/sd:
// the bot was created at 23:08:41, three seconds BEFORE the host's
// `first spawn` (23:08:44), so it inherited the host's still-None team;
// ... while the bot stayed None and kept failing `spawn refused client=1
// ... NO_SPAWN_POINT` -- selectSpawnPoint filters by team and a map has
// no None-typed spawn point.
```

**⇒ 十层**：
```text
1. **一个 bot 【从不确认职业**】**
2. ⇒ **所以【分配真实 team**】的那个菜单【从不为它运行**】**
3. ⇒ **测量 `mp_crash_tropical/sd`**：bot 在 `23:08:41` 创建
4. ⇒ **比主机的 `first spawn`（`23:08:44`）【早三秒**】**
5. ⇒ **所以它【继承了主机仍然是 `None` 的 team**】**
6. ⇒ **主机然后从它的职业确认得到真实 team 并出生**
7. ⇒ **而 bot 【停在 `None`**】**
8. ⇒ **并持续 `spawn refused ... NO_SPAWN_POINT`**
9. ⇒ **因为 `selectSpawnPoint` 按 team 过滤而地图【没有 `None` 类型的出生点**】**
10. ⇒ **没有应用的出生 ⇒ `effectivePlaying` 为假 ⇒ 【bot 存在但从不被渲染**】**
```

**✅ ⭐⭐ **"bot 存在但从不被渲染"** —— 第三个"静默的实体"实例**。**

**⇒ 三层**：
```text
§410  obituary 从未到达任何人
§411  没有 apply 的出生 ⇒ bot 存在但不渲染
§402  dmz 客户端等 46 秒
⇒ **⇒ 三条"存在但不可见"**
```

**✅ ⭐ **一个"存在但无效"的三例表**。

### 4.3 第 3 次：faction 跟随 team（推翻 J4 的推理）

```php
// OLMOD(bot-faction-align, 20261015-22270): faction MATCHES team.
//
// This used to be the OPPOSITE side, added with J4. J4's own reason was
// "a bot and the host must be able to damage each other", but that is
// decided by TEAM, not faction: SvServerWorld::onSameTeam
// (sv_snapshot_mp.cpp:24553-24560) reads playerTeam() (:24544-24551),
// which returns client.team and never touches characterFaction. ...
//
// Operator, 2026-10-15 in a cha match: "小地图里不显示我的队友，并且
// 瞄准队友显示是红色名字" -- the client draws the name colour and the
// minimap marker from this faction, so a bot on your own team carried
// the enemy's faction and rendered as an enemy.
```

**⇒ 十四层**：
```text
1. **`faction` 现在【匹配 `team`**】**
2. ⇒ **它过去是【对面**】，随 J4 一起加的**
3. ⇒ **而 J4 自己的理由是"bot 与主机必须能互相伤害"**
4. ⇒ **但那是由【TEAM】决定的，不是 faction**：
      · **`SvServerWorld::onSameTeam`（`sv_snapshot_mp.cpp:24553-24560`）读 `playerTeam()`（`:24544-24551`）**
      · **它【返回 `client.team`**】**
      · **而【从不触及 `characterFaction`**】**
5. ⇒ **在 `:8942-8943` 的【对面 TEAM**】才是修好伤害的那个**
6. ⇒ **而这里的【对面 FACTION】只是【让记录自相矛盾**】**
7. ⇒ **甲方 2026-10-15 在一场 cha**：「小地图里不显示我的队友，并且瞄准队友显示是红色名字」
8. ⇒ **⇒ 客户端【从 faction 画名字颜色与小地图标记**】**
9. ⇒ **所以一个【在你队里的 bot 携带了敌人的 faction**】并【渲染成敌人**】**
10. ⇒ **人类路径【已经保持两者同步**】：
      · `sv_client_mp.cpp:2274-2276`（`team==Tf ⇒ faction Tf`）
      · `:452-464`（菜单 ⇒ 匹配的 team）
11. ⇒ **这里让 bot 路径与它们一致**
```

### 4.4 ⭐⭐⭐ **"由 TEAM 决定，不是 faction"**

**✅ 这是本报告里**最重要的一次因果纠正**。**

**⇒ 三层**：
```text
J4 的观察：对面 faction ⇒ 能互相伤害
J4 的推理：**faction 决定伤害** ⇒ **错**
真因：**上一行已经设了对面 TEAM** ⇒ team 决定伤害
⇒ **⇒ 所以对面 faction 是【一个巧合造成的错误结论**】
```

**✅ 与 §397 的"`isAllowed("")` 在两种读法下都返回 `true` ⇒ 那个返回值零信息"**同族（**第四次"一个观察在两种假设下都成立"）。**

**⇒ 三层**：
```text
J4 改了两件事：① 对面 TEAM ② 对面 FACTION
⇒ **伤害修好了**
⇒ **⇒ 但它归因到了【②】，而真因是【①**】
```

**✅ ⭐⭐ **"一次改两个变量 ⇒ 无法归因"** —— 一个**经典的方法论错误实例**。

**⚠ 而 §403 的"单变量映射实验"**正是**同一教训的正面版**。

**⇒ 三层**：
```text
§403  正面：**单变量映射实验 + 日志 + 判据**
§411  反面：**一次改两个变量 ⇒ 归因错误，隐藏了四个月**
```

**✅ ⭐ **一个完整的正反对照**。

**⚠ 而"客户端从 faction 画名字颜色与小地图标记"⇒ **一个新的语义**。**

**⇒ 三层**：
```text
faction ⇒ **视觉（名字颜色 + 小地图标记）**
team    ⇒ **逻辑（伤害/出生点）**
⇒ **⇒ 两个不同的域，必须同步**
```

**✅ 与 §409 的"`L` 的槽位号"**不同（这是**两个字段的职责划分**）。

## 五、**`BotLoadoutSequence = 1` 的"第一个提交不是背包切换"**

```php
// A FIXED, NON-ZERO CLASS GENERATION FOR EVERY BOT. This is the whole of
// G3: it is what makes the resolvedLoadouts_ lookup a HIT on the very
// first frame the slot is Active. weaponSelectSequences_ keys on the
// same value and starts at 0, so the first commit is not mistaken for a
// backpack swap and no `a <weapon>` is queued.
constexpr std::uint32_t BotLoadoutSequence = 1;
```

**⇒ 八层**：
```text
1. **一个固定的、非零的职业代次【给每个 bot**】**
2. ⇒ **它是 G3 的全部**：**它让 `resolvedLoadouts_` 在槽变 `Active` 的第一帧就【命中**】**
3. ⇒ **`weaponSelectSequences_` 用【同一个值】而【从 `0` 开始**】**
4. ⇒ **所以第一次提交【不被误认为一次背包切换**】**
5. ⇒ **而【不排队一条 `a <weapon>`**】**
6. ⇒ **⇒ 所以 `1` 而不是 `0` 是【有功能的**】**
```

**✅ ⭐⭐ **"用一个非零初值区分『第一次』与『变化』"** —— 一个**极简洁的边沿编码**。

**✅ 与 §404 的"撤掉 `a <weapon>`"**完全闭合 ✓

**⇒ 三层**：
```text
§404  `a <weapon>` 从重生簇里撤掉（因为它在模型重建时解析手部 tag ⇒ 崩）
§411  `BotLoadoutSequence = 1` 保证 bot 【从不排 `a <weapon>`**】
⇒ **⇒ 所以 bot 路径【避免**了那个崩溃**
```

**✅ ⭐ **一个"缺陷在另一条路径上被一个巧合避开"的实例**。

**⚠ 而"`resolvedLoadouts_[*clientNum]` 在 `activateBotSlot` 【之前】填"⇒ **顺序**。**

**✅ 与 §409 的"候选-提交模式"**同族（**第三次"顺序决定正确性"）。**

**⇒ 三层**：
```text
填 `resolvedLoadouts_` ⇒ **然后** `activateBotSlot`
⇒ **若 act 失败 ⇒ `resolvedLoadouts_.erase(*clientNum)`**
⇒ **⇒ 所以失败时【不留残迹**】
```

**✅ ⭐ **一个"回滚"的实例**（与 §409 的事务式提交同族）。

## 六、**`BOTTRACE` 的十行一次性日志**

```text
BOTTRACE|slot-create
BOTTRACE|team-set
BOTTRACE|loadout-fill
BOTTRACE|spawn-request
BOTTRACE|timeout-exempt
BOTTRACE|create-stages
BOTTRACE|spawn-applied     ← 在 driveBotClients 里，一次
BOTTRACE|pose              ← 一次
BOTTRACE|create-refused    ← 只在失败
BOTTRACE|spawn-applied
```

**⇒ 七层**：
```text
1. **每个 bot 只打【1 行】（`11` 行/局）** ⇒ 这里实际是**六行/ bot**
2. ⇒ **`[INF]` 级别**
3. ⇒ **零行为改动**
4. ⇒ **（本函数每次入场只调用一次，不进每帧热路径）**
5. ⇒ **分段计时**：`slotUs` / `activateUs` / `otherUs` / `totalUs`
6. ⇒ **为回答"那次入场 `0.35–0.87 s` 花在哪一步"**
```

**⚠ 而注释说"每个 bot 只打 1 行（11 行/局）"，实际是六行** ⇒ **一处注释与实际不符**。

**✅ 与 §408 的"`STILL NOT SENT` 列表部分过期"**同族（**第三次"注释与代码不同步"）。**

**⇒ 三层**：
```text
注释：**1 行/bot**
代码：`slot-create` + `team-set` + `loadout-fill` + `spawn-request` + `timeout-exempt` + `create-stages` = **6 行/bot**
⇒ **⇒ 所以【注释说的是"分段计时"那一行**，前面的五行是**独立的记录**
```

**⚠ 更可能：注释指的是**"计时相关的 1 行"**，而另外五行是**内容记录**。→ 一个**可接受的读法**。

**✅ 与 §409 的"一次性的边界触发"**同族（**第四次"低频取证"）。**

**⇒ 三层**：
```text
§402  `PMFLAGS|`：**值变化时**
§409  `advance-blocked`：**位掩码变化时**
§410  `killFeedEnabled`：**进程级一次**
§411  `BOTTRACE`：**每 bot 一次（入场）**
```

**✅ ⭐ **一个四个粒度的表**。

## 七、**`driveBotClients` 的"武器字段不是可选的"**

```php
// THE WEAPON FIELD IS NOT OPTIONAL. A usercmd with cmd.weapon == 0
// reaches the weapon code as "none", and the measured result is a player
// who runs with empty hands. The value is the bot's own resolved primary,
// so the command agrees with the class the slot was admitted with.
```

**⇒ 六层**：
```text
1. **武器字段【不是可选的**】**
2. ⇒ **一个 `cmd.weapon == 0` 的 usercmd 【以"无"到达武器代码**】**
3. ⇒ **而测量结果是【一个空手跑动的玩家**】**
4. ⇒ **这个值是【bot 自己解析后的主武器**】**
5. ⇒ **⇒ 所以那个命令【与槽被接纳时的职业一致**】**
6. ⇒ **其他一切保持零**：**无按钮、`forwardMove`/`rightMove` 为 `0`、无视角变化**
```

**✅ 与 §370 的"空手是一个持有的状态"（`sv_snapshot_mp.cpp` §371）**完全闭合 ✓

**⇒ 三层**：
```text
§371  空手是【一个持有的状态**】不是"没有状态"
§411  `cmd.weapon == 0` ⇒ **武器代码读作"无"** ⇒ **空手**
⇒ **⇒ 所以"零"是一个【有效的武器号**】
```

**✅ ⭐ **第二次确认"零是一个有效的值"**。

**⚠ 而"其他一切保持零"⇒ **本刀 bot 是静止的**（后续 P4m 加转向）。**

**✅ 与 §409 的"一个走完 32.7 秒日程的结束"**不同（这是**一个"什么都不做"的基线**）。

## 八、**`SvBotWalkState` 的字段演化**（本组第四重要）

```text
v1 基础：destination / chosenAt / planTime / plan / hasPlan / hasYaw / yaw / reportedAt
         lastOrigin / graphRouted / hasMode
+ generation                      ← S3 v1，代次绑定
+ lifeState                       ← 刀AD2，0=alive 1=dead 2=frozen
+ siteIndex / reportedSiteIndex / goalLabel   ← S3 v2 队伍目标
+ aimTarget / fireCycle           ← S3 v2 combat
+ travelWindow / travelLast / travelHas      ← 刀F 位移硬读数
+ combatYaw/Pitch / combatHasAim / aimReadyAt ← 刀K 平滑朝向
+ combatYawVel / combatPitchVel   ← 刀M 二阶弹簧
+ meleeReadyAt                     ← 刀O 近战冷却
+ deltaYawDeg / deltaPitchDeg      ← 刀M `delta_angles` 减法
+ stuckLevel / stuckCheckAt / stuckRefOrigin / stuckHasRef
  / nudgeUntil / nudgeRight       ← 刀P 卡死三级升级
+ sprintReported                   ← 刀R 去抖
+ blockedEdges[16] / blockedCursor / blockedCount ← 刀S 封边黑名单
```

**⇒ 十九个字段组。**

**⚠ 而"`std::array<std::pair<uint16,uint16>, 16> blockedEdges`"⇒ **与 2697 的 `blocked[16]` 同尺寸**。**

**⇒ 三层**：
```text
2697 `codol_bot.c`：每 bot 一个 `blocked[16]` + `blockedCursor`
§411：`blockedEdges[BotBlockedEdgeCapacity=16]` + `blockedCursor` + `blockedCount`
⇒ **⇒ 同结构 + 加一个 `count`**（因为**环形需要知道满没满**）
```

**✅ ⭐ **一个"照抄结构但补一个必要字段"的实例**。

**⚠ 而"定义必须在 `SvBotWalkState` 之前（结构体用它定 `std::array` 的尺寸）"⇒ **一个 C++ 语序约束**。

**✅ 与 §409 的"模板 on purpose"**同族（**第二次"语序/类型约束**）。

## 九、**卡死判据的三次调参：1500 → 800 → 300**

```php
// ★★ 28100 刀Y-1（甲方：卡住判定调到 300，重启对性能无影响就 300）：
//   **800 → 300**（上一刀 X-2 是 1500 → 800）。
//   **性能判断（为什么 300 安全）**：
//     · 这个常量只决定**"多久比一次位移"**；
//       判定体是 `if(serverTime >= stuckCheckAt)` + 三个 float 的距离平方比较，
//       单次开销是常数级、无分配、无 trace；
//     · **真正的动作有独立节流**：`nudgeUntil = now + BotStuckNudgeMilliseconds(700)`
//       （照老外 `codol_bot.c:447` 的 `b->nudgeUntil=now+700`），
//       且 `walk.nudgeUntil` 在前时不会再次升级 ⇒ **不会因为 300 而频繁触发寻路**；
//     · 老外平地窗口是 1500（`codol_bot.c:571`），攀爬 4000；300 只是更早进入同一套升级。
//   ⇒ 结论：**300 对每帧成本无影响**（由 `check_perframe_cost.py` 复核）。
static constexpr std::uint32_t BotStuckCheckMilliseconds = 300;
static constexpr float BotStuckDistanceUnits = 12.0f;
static constexpr std::uint32_t BotStuckNudgeMilliseconds = 700;
```

**⇒ 十六层**：
```text
1. **`800 → 300`**（上一刀是 `1500 → 800`）
2. ⇒ **甲方的条件**："重启对性能无影响就 300"
3. ⇒ **三条性能论证**：
      · **这个常量【只决定多久比一次位移**】**
      · **判定体是 `if` + 三个 `float` 的距离平方比较** ⇒ **常数级、无分配、无 trace**
      · **真正的动作有【独立节流**】（`nudgeUntil = now + 700`）
      · **而 `nudgeUntil` 在前时【不会再次升级**】⇒ **不会因为 300 而频繁触发寻路**
4. ⇒ **老外平地窗口是 `1500`**（`codol_bot.c:571`），**攀爬 `4000`**
5. ⇒ **`300` 只是【更早进入同一套升级**】**
6. ⇒ **结论：`300` 对每帧成本无影响**
7. ⇒ **（由 `check_perframe_cost.py` 复核）**
8. ⇒ **位移判据保持 `12` 单位**（**= 老外 `12*12` 的平方形式**）
9. ⇒ **不做改动（单变量）**
```

### 9.1 ⭐⭐⭐ **"这个常量只决定多久比一次位移，而真正的动作有独立节流"**

**✅ 这是本报告里**最重要的一个性能论证法**。**

**⇒ 三层**：
```text
担忧：300ms 会不会太频繁？
分析：**检查频率** 与 **动作频率** 是【两个独立的量】
⇒ **⇒ 检查便宜（三个 float 比较）而动作有 700ms 节流**
```

**✅ 与 §402 的"`INF` 在 `OLMOD_LOG_LEVEL=warn` 下不可见"**不同（这是**一个性能分析而不是取证）**。**

**⚠ 而"`check_perframe_cost.py` 复核"⇒ **一个自动化的成本检查器**。**

**✅ ⭐ **"由脚本复核"** —— 一个**可复现的性能主张**。

**✅ 与 §409 的"测出来的，不是推理的"（`demoq phases`）**同族（**第三次"用工具而不是推理"）。

**⇒ 三层**：
```text
`demoq phases` ⇒ **测时序**
`check_perframe_cost.py` ⇒ **测成本**
`175` 份 demo 统计 ⇒ **测频次**
```

**✅ ⭐ **三个工具，三种测量**。

**⚠ 而"位移判据保持 `12` 单位（单变量）"⇒ **第八次"单变量"**。**

**⇒ 三层**：
```text
§402  四条**不同**命令 ⇒ **一次一条是无望的**
§403  一条命令的**三个值** ⇒ **逐一试可接受**
§411  一个常量（`800→300`）而**另一个（`12`）不动** ⇒ **单变量**
```

**✅ ⭐ **一个"什么时候该单变量"的判据**：**一个可独立调的量**。

## 十、**按键位表的血统**

```php
// ★★ 28100 刀R（甲方："人机不会跑步"）—— 按 2697 `codol_bot.c` 的**同一张按键位表**：
//   `:35 #define SPRINT 2u`（同表 `MELEE 4u`(:43) / `PRONE 256u` / `CROUCH 512u` /
//   `JUMP 1024u` / `ADS 2048u` / `ADS_TRIGGER 0x100000u`）。
static constexpr std::uint32_t BotUserCmdButtonSprint = 0x00000002;
static constexpr std::uint32_t BotUserCmdButtonMelee = 0x00000004;
static constexpr std::uint32_t BotCombatUserCmdButtonFire = 0x00000001;
// UserCmdButtonActivate = 0x8（sv_use_object_mp.hpp:13）
// NativePmoveBindings.cpp:515 的实测位一致（该常量在匿名命名空间里，这里本地重声明，值即 0x1，CODREF 1649370 section-75）
```

**⇒ 九层按键表**：
```text
FIRE          = 0x1        ← **本 build 实测**（`NativePmoveBindings.cpp:515`）
SPRINT        = 0x2        ← 2697 `codol_bot.c:35`
MELEE         = 0x4        ← 2697 `codol_bot.c:43`
ACTIVATE      = 0x8        ← 本工程 `sv_use_object_mp.hpp:13`
PRONE         = 0x100      ← 2697
CROUCH        = 0x200      ← 2697
JUMP          = 0x400      ← 2697
ADS           = 0x800      ← 2697
ADS_TRIGGER   = 0x100000   ← 2697
```

### 10.1 ⭐⭐ **"`FIRE = 0x1` 是本 build 实测，其余来自 2697"**

**✅ 与 §402 的"`UserCmdButtonActivate` 是 `0x8` 而【本 build 无人独立确认过】"**完全闭合 ✓

**⇒ 三层**：
```text
`FIRE`        ⇒ **本 build 实测**（`NativePmoveBindings.cpp:515`）
`ACTIVATE`    ⇒ **只有 SD 路径用过，无独立确认**（§402）
`SPRINT`/`MELEE`/... ⇒ **2697（一个外部参照）**
⇒ **⇒ 所以【血统不齐**】
```

**⚠ 而 §410 的 `loot BUTTONS` 日志正是**为确认 `ACTIVATE` 而加**。**

**✅ 与 §410 的"如果 use 是另一个位，这一行在一次按键里就命名它，而不是花掉又一次构建"**完全闭合 ✓

**⇒ 三层**：
```text
问题：`ACTIVATE = 0x8` **未在本 build 确认**
工具：`loot BUTTONS client=... buttons=0x%08X activate=N`
⇒ **⇒ 所以一次按键就解决**
```

**✅ ⭐ **一个"为未确认常量专设的判据"**。

### 10.2 而**"只清 FIRE、置 MELEE，不清未知位"**

```php
// ⚠ `ADS/ADS_TRIGGER` 的位值我方未取证 ⇒ **只清 FIRE、置 MELEE**，不清未知位。
```

**⇒ 五层**：
```text
1. **`ADS`/`ADS_TRIGGER` 的位值【未取证**】**
2. ⇒ **所以【只清 `FIRE`、置 `MELEE`**】**
3. ⇒ **【不清未知位**】**
4. ⇒ **⇒ 一个"最小必要改动"的纪律**
5. ⇒ **（2697 写的是 `(cmd.buttons & ~(FIRE|ADS|ADS_TRIGGER)) | MELEE`）**
```

**✅ ⭐ **"只动已知的位"** —— 一个**极精确的保守策略**。

**✅ 与 §407 的"不猜数"**同族（**第二十五次"不要发明"）。**

**⇒ 三层**：
```text
§407  实体号拿不到 ⇒ **跳过**
§411  按钮位未取证 ⇒ **不清**（而不是猜一个掩码）
⇒ **⇒ 同一纪律在【位掩码】上**
```

**✅ ⭐ **一个"未取证 ⇒ 不动"的通则**。

### 10.3 而**"`SvNativeUserCmd` 没有 `meleeChargeDist`"**

```php
// ⚠ 老外还写 `cmd.meleeChargeDist/meleeChargeYaw`（`lunge = clamp(flat-24,0,255)`）；
//   我方 usercmd（`SvNativeUserCmd`，0x2C）**没有同名字段**，未取证的
//   `conditionalByte/conditionalElevenBits` **不猜绑定** ⇒ 本轮**只发按钮位**
//   （刀仍会触发，lunge 距离为 0），charge 镜像列为下一刀。
```

**⇒ 九层**：
```text
1. **老外写 `cmd.meleeChargeDist`/`meleeChargeYaw`**
2. ⇒ **（`lunge = clamp(flat - 24, 0, 255)`）**
3. ⇒ **我方 `SvNativeUserCmd`（`0x2C` 字节）【没有同名字段**】**
4. ⇒ **而 `conditionalByte`/`conditionalElevenBits` 【未取证**】**
5. ⇒ **所以【不猜绑定**】**
6. ⇒ **本轮【只发按钮位**】**
7. ⇒ **（刀仍会触发，但 `lunge` 距离为 `0`）**
8. ⇒ **`charge` 镜像列为【下一刀**】**
```

**✅ ⭐⭐ **"刀仍会触发，但 lunge 距离为 0"** —— 一个**精确的降级后果说明**。**

**✅ 与 §409 的"一个错的人偶仍然胜过一个没有人偶"**同族（**第五次"部分功能优于无功能"）。**

**⇒ 三层**：
```text
§409  错的人偶 ⇒ **形状/服装错但仍可见**
§411  `lunge = 0` ⇒ **刀触发但不前冲**
⇒ **⇒ 两者都是【部分可用**
```

**✅ ⭐ **一个"部分可用"的判据：核心语义保留**。

**⚠ 而"`0x2C`"⇒ **`SvNativeUserCmd` 是 44 字节**。**

**✅ 与 §388 的"`0x58`/`0x118`/`0x160`"**同族（**第二个结构尺寸表**）。

## 十一、**`0.35–0.87 s` 的入场耗时**

```cpp
// ★★★ 2026-10-14（V1.203 ③b）—— **一次性分段计时**，只为回答"那次入场 0.35–0.87 s 花在哪一步"。
//   纪律：每个 bot 只打 **1 行**（11 行/局）、`[INF]`、零行为改动
```

**⇒ 五层**：
```text
1. **入场耗时 `0.35–0.87 s`**（一个**已测量的区间**）
2. ⇒ **分段计时只为回答【花在哪一步**】**
3. ⇒ **三段**：`freeClientSlot` / `activateBotSlot` / 其余
4. ⇒ **纪律：`[INF]`、零行为改动**
5. ⇒ **⇒ 一个"先测量再优化"的实例**
```

**✅ 与 §404 的"排除最新嫌疑（值得一个周期）"**同族（**第四次"测量优先"）。**

**⚠ 而"`[INF]`"⇒ **与 §402 的"`INF` 在 `warn` 下不可见"冲突**。**

**⇒ 三层**：
```text
§402  `INF` 被丢弃 ⇒ **窗口没有证人** ⇒ 提到 `Warn`
§411  新增的 `BOTTRACE` **用 `[INF]`** ⇒ **在 `warn` 级别下同样不可见**
⇒ **⇒ 一个【重复的坑**】
```

**⚠ 一个**必须标注的问题**（`BOTTRACE` 在 `OLMOD_LOG_LEVEL=warn` 下不可见）。

## 十二、关键结论

1. **⭐⭐⭐ `writeHudElems` 把 `Text` 元件当作"脉冲字幕"当且仅当 `fadeTime == 0` 且（`fadeStartTime` / `materialIndex` / `width` / `scaleStartTime` / `scaleTime`）任一非零，而它【把 `label` 清零**】 —— **这就是那个字幕从未被绘制的原因**，而结果板只设 `alignScreen 0x98` 与 `glowColor` 别的不设。
2. **⭐ "用 `Value` 而不是 `Text` 来绕开 `label` 陷阱"** —— 数值行可以避开这个语义。
3. **`0.9375 = 15/16`（2697 的 `hudsmall`）与 `(0.16, 0.65, 1) = 0xFF29A6FF`**（`0x29 = 41`，而 `0.16 × 255 = 40.8` 是四舍五入）。
4. **两层 HUD**（`currentHud` 瞬时反馈 / `archivalHud` 目标与持续状态），而 **`archivalHud` 从 `playerState->objectives` 重建 ⇒ "HUD 只有一个主人"，且不依赖 SD 投影器是否运行**。
5. **`zm` 的"保留一个稳定的前缀槽"**：`std::move_backward` 整体后移一位、槽 0 放僵尸分数；**31 槽全占 ⇒ 静默省略可选的分数反馈**（不是数据丢失、是特性降级 ⇒ 不需要证人）。
6. **僵尸团灭 ⇒ 两层都清空，只在槽 0 放"游戏结束"**。
7. **⭐⭐⭐ J4 的"对面 faction"是一次【一次改两个变量】的归因错误**：**对面 TEAM 修好了伤害（`onSameTeam` 只读 `client.team`，`sv_snapshot_mp.cpp:24553-24560`）**，而对面 FACTION **只是让记录自相矛盾**，并让**队友 bot 渲染成敌人**（甲方原话「小地图里不显示我的队友，并且瞄准队友显示是红色名字」）。
8. **⭐ faction 与 team 是两个域**：**faction ⇒ 视觉（名字颜色 + 小地图标记）；team ⇒ 逻辑（伤害/出生点）**，必须同步（人类路径 `sv_client_mp.cpp:2274-2276`/`:452-464` 已经同步）。
9. **⭐⭐ "可见、可射、不可杀"**：bot 继承主机 team ⇒ `onSameTeam` 为真 ⇒ `finishPlayerDamageBatch` 丢弃每一次命中。
10. **⭐⭐ "bot 从不确认职业 ⇒ 分配真实 team 的菜单从不为它运行"** ⇒ 继承了主机仍为 `None` 的 team ⇒ `spawn refused ... NO_SPAWN_POINT`（地图没有 `None` 类型的出生点）⇒ **bot 存在但从不被渲染**。
11. **⭐⭐ `BotLoadoutSequence = 1`（非零）**：**`weaponSelectSequences_` 从 `0` 开始 ⇒ 第一次提交不被误认为背包切换 ⇒ 不排队 `a <weapon>`** —— 一个"用非零初值区分『第一次』与『变化』"的边沿编码，也**巧合地避开了 §404 的崩溃**。
12. **`resolvedLoadouts_` 在 `activateBotSlot` 之前填，失败则 `erase`** —— 一个回滚。
13. **⭐⭐⭐ "这个常量只决定多久比一次位移，而真正的动作有独立节流（`nudgeUntil = now + 700`）"** —— 一个"检查频率与动作频率是两个独立量"的性能论证，并由 **`check_perframe_cost.py` 复核**。
14. **卡死判据三次调参 `1500 → 800 → 300`**，而**位移判据 `12` 单位不动（单变量）**。
15. **九层按键位表**：`FIRE 0x1`（**本 build 实测**）/ `SPRINT 0x2` / `MELEE 0x4` / `ACTIVATE 0x8`（**未独立确认，§410 的 `loot BUTTONS` 就是为它专设的判据**）/ `PRONE 0x100` / `CROUCH 0x200` / `JUMP 0x400` / `ADS 0x800` / `ADS_TRIGGER 0x100000`（后七项来自 2697）。
16. **⭐⭐ "只清 `FIRE`、置 `MELEE`，【不清未知位】"**（`ADS`/`ADS_TRIGGER` 未取证）—— 第二十五次"不要发明"。
17. **⭐ "我方的 usercmd（`SvNativeUserCmd`，`0x2C`）没有 `meleeChargeDist` ⇒ 不猜绑定 ⇒ 只发按钮位，刀仍会触发但 `lunge` 距离为 `0`"** —— 第五次"部分功能优于无功能"，判据是**核心语义保留**。
18. **⚠ `BOTTRACE` 用 `[INF]`，而在 `OLMOD_LOG_LEVEL=warn` 下同样不可见** —— 与 §402 的重复坑。

## 十三、未闭合点

- `0x98` 的 `alignScreen` 位语义。
- `glowColor` 的四个字节各是什么。
- `SvHudElemType` 的完整枚举。
- `archivalHud` 的 31 槽来源。
- `BotWalkProbeIntervalMs = 1000` 探什么。
- `SvBotNavSteerPlan` 的字段。
- `codol_bot.c` 的 `stuck_escalate()` 三级实现细节。
- `sv_main_mp.cpp` 10426 行之后未读取（**文件实际 `11,940` 行**）。
