# 402 · **"一次一个缺失命令花了四个周期与四个负面"** —— `24` 条 vs 我们 `10` 条、`s 0201 "1"` 是零售【每个模式都发而我们一个都不发】的那条、`d 12246` 的越界崩溃

## 一、范围

本报告学习 `sv_main_mp.cpp` 4150–4500 行。

## 二、**`s 0201 "1"` 的完整实验史**（本组最重要的一段）

### 2.1 那段

```php
// `s 0201 "1"` IS THE ONE COMMAND RETAIL SENDS ON EVERY MODE AND WE SEND ON NONE.
//
// MEASURED in both captures -- dm at serverTime 43100 (seq 35) and dmz at 23000
// (seq 51), once each, a few seconds after the join burst. A grep of the whole
// ol-mod tree for "0201" returns nothing, so this server has never sent it.
//
// This project already named it: the C# GameServer's status-command work called
// it the thing that "lets the client into the match", and its own fix was gated
// behind server-commands.txt (default 0), so it has stayed inert there too.
//
// WHY IT IS TRIED HERE AND NOT EVERYWHERE. mp_nuked reaches a live match without
// it, so it is demonstrably not required on cha -- our client gets in by some
// other route. dmz has no such route: the client takes the gamestate, sends 68
// packets, then waits 46 SECONDS and tears the session down (MatchMaking 21/3),
// which is a client waiting for a signal that never comes, not one refusing
// anything. This is the most conspicuous signal we never send. Scoped to dmz so
// a mode that currently works cannot regress on it.
//
// TIMING IS APPROXIMATED. Retail sends it seconds AFTER the join burst, not
// inside it; this rides the first-spawn cluster, which is the closest existing
// hook. If it changes the failure but does not fix it, the delay is the next
// variable to move, not the command.
```

### 2.2 二十层

```text
1. **`s 0201 "1"` 是零售【在每一个模式都发】而我们【一个都不发】的那条命令**
2. ⇒ **在【两个】捕获里测量**：
      · **dm 在 `serverTime 43100`（seq 35）**
      · **dmz 在 `23000`（seq 51）**
      · **各一次，在加入突发【几秒之后】**
3. ⇒ **对整个 ol-mod 树 grep `"0201"` 【返回空】**
4. ⇒ **所以这个服务器【从未】发过它**
5. ⇒ **这个项目【已经命名过】它**：**C# GameServer 的 status-command 工作叫它"让客户端进入比赛"的那个东西**
6. ⇒ **而它自己的修复坐在 `server-commands.txt`（默认 0）后面 ⇒ 所以它在那里也【保持惰性】**
7. ⇒ **为什么在这里尝试而【不是到处】**
8. ⇒ **`mp_nuked` 【不需要它】就到达一场活的比赛**
9. ⇒ **所以它在 cha 上【可证明不是必需的】**（我们的客户端通过别的路径进入）
10. ⇒ **而 dmz 【没有这样的路径】**：
      · **客户端拿 gamestate**
      · **发 `68` 个包**
      · **然后等 `46` 秒并【拆掉会话】**（MatchMaking 21/3）
11. ⇒ **那是一个等待一个永不到来的信号的客户端**，不是一个拒绝任何东西的客户端
12. ⇒ **这是我们从未发过的信号里【最显眼的**】
13. ⇒ **限定到 dmz 所以一个当前工作的模式不能在它上面回归**
14. ⇒ **时机是【近似的**】
15. ⇒ **零售在加入突发【几秒之后】发它，不在突发之内**
16. ⇒ **这个搭乘 first-spawn 簇，那是最接近的既有钩子**
17. ⇒ **若它改变了失败但没有修好它，延迟是下一个要移动的变量，不是那条命令**
```

### 2.3 ⭐⭐⭐ **"一个等待一个永不到来的信号的客户端，不是一个拒绝任何东西的客户端"**

**✅ 这是本文件里**最重要的一个诊断区分**。**

**⇒ 三层**：

```text
"拒绝" ⇒ 客户端发了一个负面的响应 ⇒ **可以在日志里看到它拒绝了什么**
"等待" ⇒ **客户端沉默** ⇒ **而沉默没有内容**
```

**✅ 与 §377 的"`NO WORLD STATE`"、§401 的"`missing_playerstate` 死锁"**同族（**第七次"沉默的诊断"）。**

**⚠ 而"`68` 个包然后等 `46` 秒"⇒ **一个精确的时间线**。**

**✅ 与 §368 的"`46` 秒后 `XBOXLIVE_CANTJOINSESSION`"**完全一致 ✓

**⇒ **第二次确认那个 `46` 秒。**

### 2.4 而**"对整个 ol-mod 树 grep `0201` 返回空"**

**✅ 与 §340 的"定向的负面"**第九次。**

**⚠ 而"C# GameServer 的修复坐在 `server-commands.txt`（默认 0）后面"⇒ **所以它是【一个已知的可能修复**】**

**✅ 一个**极有价值的交叉线索**（另一个实现也认为这是关键）。

**⇒ 三层**：

```text
两个独立实现（C# GameServer 与本项目）
⇒ **都指向 `s 0201`**
⇒ **而两个的实现都【默认关闭**】
```

**✅ ⭐ **一个"两个独立实现都怀疑同一点"的证据**。**

**✅ 与 §397 的"一个结果在两种假设下都成立 ⇒ 零信息"**相反**（这是**两个独立来源一致 ⇒ 强信息**）。

### 2.5 而**"限定到 dmz 所以一个工作的模式不能回归"**

**✅ 与 §350 的"不要一般化这个例外"**同族（**第五次"限定范围"）。**

## 三、**"一次一个缺失命令花了四个周期与四个负面"**（本组第二重要）

### 3.1 那段

```php
// THE WHOLE RETAIL dmz JOIN BURST, REPLAYED IN ORDER. DELIBERATELY A SHOTGUN.
//
// Sending one missing command per build-and-run cost four cycles and four
// negatives (the ui-screen order, the loot band, `I 0 0 0`, `s 0201`). Counting
// what retail actually sends in the window ending at its `s 0201` shows why that
// was hopeless: 24 commands against our 10.
//
// MEASURED, C-2021-7-25[22-0-7]dmz, serverTime 18500..23000, in this order --
// `demoq.py cmds`. `f "MP_CONNECTED..."` and `s ui_DMKillScore` are omitted
// because this server already sends both by other paths.
//
// NOTHING HERE IS DECODED, and that is on purpose. `r`, `H`, `i`, `w`, `o` and
// the numeric `s` dvars are reproduced byte for byte from the capture rather
// than reasoned about -- the same rule the dm sequence was written under. The
// point is to learn whether the burst as a whole is what the client waits on;
// if it is, BISECT THIS LIST, do not keep it as-is.
//
// `a 1213` is retail's own weapon grant for that match and is the one value here
// that may not port -- `a <n>` is the spawning player's weapon, and this build
// reports firstDynamicWeapon=1147 on mp_battlecity. Suspect it first if the
// client's weapon comes out wrong rather than the join failing.
```

### 3.2 二十层

```text
1. **整个零售 dmz 加入突发的【按序重放】**
2. ⇒ **【故意是一个霰弹枪】**
3. ⇒ **每次构建-运行发【一条】缺失命令【花了四个周期与四个负面**】：
      · **ui-screen 顺序**
      · **loot 带**
      · **`I 0 0 0`**
      · **`s 0201`**
4. ⇒ **数零售在那个窗口里【实际发】什么显示为什么那是【无望的**】：
5. ⇒ **`24` 条命令对**我们的 `10` 条**
6. ⇒ **测量 `C-2021-7-25[22-0-7]dmz`，`serverTime 18500..23000`，按这个顺序**
7. ⇒ **（`demoq.py cmds`）**
8. ⇒ **`f "MP_CONNECTED..."` 与 `s ui_DMKillScore` 被省略**
9. ⇒ **因为这个服务器【已经通过别的路径】发了两者**
10. ⇒ **这里【什么也没有解码】，而那是【故意的**】
11. ⇒ **`r` / `H` / `i` / `w` / `o` 与那些数字 `s` dvar 【逐字节复现**】而不是推理
12. ⇒ **同一个规则 dm 序列是在它下面写的**
13. ⇒ **要点是【学会那个突发【作为一个整体**】是否是客户端等待的东西**
14. ⇒ **若是 ⇒ 【二分这个列表**】，不要保持原样】
15. ⇒ **`a 1213` 是零售自己那场比赛的武器授予**
16. ⇒ **而它是这里【唯一可能不能移植**】的值
17. ⇒ **`a <n>` 是【生成中玩家的武器**】
18. ⇒ **而这个 build 在 `mp_battlecity` 上报 `firstDynamicWeapon=1147`**
19. ⇒ **若客户端的武器出来是错的而不是加入失败 ⇒ 【先怀疑它**】
```

### 3.3 ⭐⭐ **"四个周期与四个负面"**

**✅ 这是本文件里**最重要的一个实验方法论批评**。**

**⇒ 三层**：

```text
方法 A：一次一条命令 ⇒ **每次一个构建+运行** ⇒ 4 条命令 = 4 个周期
方法 B：**全量重放** ⇒ 一个周期学到"整体是不是"
⇒ **⇒ 而若整体是 ⇒ 再【二分**】
```

**✅ ⭐ **"霰弹枪"然后二分** —— 一个**经典的调试策略**（先确认整体再定位）。**

**⚠ 而"`24` 条对我们的 `10` 条"⇒ **所以逐一排查是**2.4 倍**的工作量**。**

**✅ 与 §392 的"`124 SessionStart` vs `47 spawn-applied`"**同族（**第五次"数量差距"）。**

### 3.4 而**"这里什么也没有解码，而那是故意的"**

**✅ 与 §399 的"跳过而不是搬移"**同族（**第二十三次"不要发明"）。**

**⇒ 三层**：

```text
`r` / `H` / `i` / `w` / `o` / 数字 `s` dvar
⇒ **逐字节复现** ⇒ 而不是"推理它们该是什么"
⇒ **⇒ 所以不引入错误**
```

**✅ **第七次确认"只复现不发明"。**

### 3.5 而**"若客户端的武器出来是错的而不是加入失败 ⇒ 先怀疑它"**

**✅ 与 §352 的"`OLMOD_DMZ_PICKUP_EVENT` 是一个旋钮"**同族（**第九次"假设一个值不可移植"）。**

**⚠ 而"`firstDynamicWeapon=1147`"⇒ 与 §388 的"`1147..1154`"**完全闭合 ✓

**⇒ **第三次确认。**

## 四、**`d 12246` 的越界崩溃**（本组第三重要）

### 4.1 那段

```php
// Retail also sends `d 12246 1201`, but 12246 is the exclusive upper
// bound of the client's weapon-definition registry. out.exe
// sub_590A60 immediately initializes every newly exposed index through
// sub_58F370. Our current session registers through 1168, so replaying
// retail's bound made sub_58F370 dereference the first absent entry,
// index 1169, at 0x58F3C0. Keep the bound produced by this gamestate
// until the captured campaign weapon tail is registered as real assets.
```

### 4.2 十二层

```text
1. **零售也发 `d 12246 1201`**
2. ⇒ **但 `12246` 是客户端武器定义注册表的【排他上界**】
3. ⇒ **`out.exe sub_590A60` 立刻通过 `sub_58F370` 初始化【每一个新暴露的索引**】
4. ⇒ **我们当前的会话【只注册到 `1168`**】
5. ⇒ **所以重放零售的上界让 `sub_58F370` 解引用【第一个缺失的条目**】**
6. ⇒ **索引 `1169`，在 `0x58F3C0`**
7. ⇒ **⇒ 一个越界读**
8. ⇒ **保持这个 gamestate 产生的上界**
9. ⇒ **直到那个捕获的战役武器尾部【被注册为真实的资产**】
```

### 4.3 ⭐⭐ **"`12246` 是排他上界而它触发初始化"**

**✅ 与 §399 的"`cs 1413` 的 `typeByte` 来自客户端资产集"**同族（**第九次"一个数字的含义取决于已加载的资产"）。**

**⇒ 三层**：

```text
`d 12246 1201` ⇒ **12246 是一个【上界**】
⇒ **而写它触发【立刻初始化 0..12245**】
⇒ **⇒ 而 1169..12245 在本 build 【不存在**】
```

**✅ ⭐ **一个"边界值本身有副作用"的实例**。**

**⚠ 而"`1168` 是我们注册到的"⇒ **一个具体的数字**。**

**✅ 与 §388 的 `1147..1154`**不同**（那是 **8 个模块化武器**）。**

**⇒ 三层**：

```text
`firstDynamicWeapon = 1147`
而注册到 **1168**
⇒ **所以 1147..1168 = 22 个索引**
```

**⚠ 与 §388 的"注册了八把（1147..1154）"**矛盾**。**

**⇒ 一个**需要标注的差异**（可能是后续注册更多）。**

## 五、**五套 gametype 的完整序列**（本组第四重要）

### 5.1 五套

```text
dm       ConnectScreens            = { "9 ready 0", "q 3", "u 18" }
         FirstSpawnScreens          = { "u 11", "r 2", "r 3", "r 1", "v 18" }
dmz      DmzConnectScreens          = { "9 ready 0", "L 13 6" }
         DmzFirstSpawnScreens       = { "r 2","r 3","r 1","v 18","u 11","I 0 0 0","s 0201 \"1\"" }
cha      ChaConnectScreens          = { "S 1214", "9 ready 0", "q 3", "u 18" }
coop     WetworkConnectScreens      = 11 条
         WetworkFirstSpawnScreens   = 11 条
         WetworkActivationAfterSpawnTime = 7 条
spy      （在 prematch 结束后发 pickup_weapon 五条）
```

**⇒ 五套。**

### 5.2 而**`WetworkConnectScreens` 的十一条**

```text
"9 ready 0"
"s ui_hide_pausemenu_class \"1\""
"s 2831 \"1\""
"d 2555 \"compass_map_cargoship\" 4264.000000 4033.000244 -3968.000000 -4199.000000"
"s 0189 \"mp/coFieldOrderMapCargoship.csv\""
"9 cinematic_wait 0"
"s 0201 \"1\""
"d 394 3"
"d 403 0.45"
"d 404 0.5"
"d 427 1"
```

**⇒ 三个 `9`/`s` 与**八个 `d`/`s`**。**

**✅ ⭐ 而 `d 2555 "compass_map_cargoship"` 的**四个浮点参数**。**

**⇒ 三层**：

```text
`d <cs> "<name>" <f1> <f2> <f3> <f4>`
⇒ **所以 `d` 命令可以带【最多四个浮点**】
⇒ **而 §399 的 `d 2557 "mpIntro" 0` 只有【一个**】
```

**✅ **第二次确认 `d` 的额外参数**（且这里是**四个**而不是一个）。

**⚠ 而"`4264.000000 4033.000244 -3968.000000 -4199.000000`"⇒ **一个地图片段的边界**。**

**✅ 一个**具体的地图数据**。

### 5.3 而**`WetworkActivationAfterSpawnTime` 的七条含 `d 5924 tag_stowed_back`**

```text
"s pve_set_activated_info \"\""
"d 5924 tag_stowed_back"          ← ★ 与 §378 的 cs 5924 完全一致
"d 12249 tag_stow_back_mid_attach"
"s 0193 \"0\""
"d 2552 n\\storm_cargoship_intro\\t\\12000"
"s 0195 \"UK_M2_\""
"d 12250 tag_weapon_right"
```

**✅ ⭐⭐ **`d 5924 tag_stowed_back`** 与 §378 的"`5896 + 28 = cs 5924 = tag_stowed_back`"**完全闭合 ✓

**⇒ **第三次确认那个 tag 的 configstring**。**

**⚠ 而"`d 12250 tag_weapon_right`"⇒ 与 §361 的"`scriptMoverTagIndex` 连接到 `tag_weapon_right`"**配合。**

**✅ 一个**极有价值的交叉验证**。**

## 六、**`PMFLAGS|` 的只读观测**（本组第五重要）

### 6.1 那段

```php
// ★★ 28100 刀AK（goal 第③步「出生无敌取证」）—— **纯只读观测，不改任何状态**。
//   甲方要的是"复活 5 秒无敌 / 开局 20 多秒无敌"，但这两个数字背后的机制
//   （pm_flags 的哪个位、什么时候置、什么时候清）**我方一帧都没观测过**：
//     · 2697 `codol_bot.c:618-619` 只说 `PMF_FROZEN(0x800)` 在零售里
//       用于 "game end, streak use, spawn protection"；
//     · 我方 `SvPmFlagsMatchEndFrozen(0x800)` **只有定义、从未置位**（全树无置位处）；
//     · 命令流里 `invuln/godmode/protect/frozen/pm_flags` 全部 0 命中
//       ⇒ 它**不是一条下发命令，是玩家状态位**，只能从快照读。
//   ⇒ 这里在 pmFlags **变化时**打一行，把"开局/复活后到底变成什么值"钉在日志里。
```

### 6.2 十六层

```text
1. **纯只读观测，不改任何状态**
2. ⇒ **甲方要的是"复活 5 秒无敌 / 开局 20 多秒无敌"**
3. ⇒ **但这两个数字背后的机制（`pm_flags` 的哪个位、什么时候置、什么时候清）**【我方一帧都没观测过**】
4. ⇒ **2697 `codol_bot.c:618-619` 只说 `PMF_FROZEN(0x800)` 在零售里用于**
      · `game end`
      · `streak use`
      · **`spawn protection`**
5. ⇒ **我方 `SvPmFlagsMatchEndFrozen(0x800)` 【只有定义、从未置位**】（**全树无置位处**）
6. ⇒ **命令流里 `invuln/godmode/protect/frozen/pm_flags` 【全部 0 命中**】
7. ⇒ **它【不是一条下发命令，是玩家状态位**】
8. ⇒ **只能从快照读**
9. ⇒ **所以在 `pmFlags` 【变化时**】打一行**
10. ⇒ **把"开局/复活后到底变成什么值"【钉在日志里**】
11. ⇒ **判据（你打一局即可）**：
      · **进图与每次复活后各出现一行 `PMFLAGS|…`**
      · **观察 `flags=` 在出生窗口内是否带 `0x800`（`frozen800=1`）**
```

### 6.3 ⭐⭐⭐ **"只有定义、从未置位（全树无置位处）"**

**✅ 这是本文件里**最重要的一条"死代码"识别**。**

**⇒ 三层**：

```text
`SvPmFlagsMatchEndFrozen(0x800)` 有一个常量定义
⇒ **而【全树没有置位处**】
⇒ **⇒ 所以它是一个【永不生效**】的位**
```

**✅ 与 §368 的"`SvActorSendUnmeasuredSpawnWords` 默认关闭"**不同**（那是**开关**，这是**死常量**）。**

**⚠ 而"2697 说它用于 `spawn protection`"⇒ **所以那个位应该是无敌**。**

**⇒ 三层**：

```text
定义：`SvPmFlagsMatchEndFrozen` ⇒ **"匹配结束冻结"**
2697：**用于 `spawn protection`** ⇒ **"出生保护"**
⇒ **⇒ 同一个 `0x800` 两个语义**
```

**✅ ⭐ **一个"名字与真实用途不符"的实例**（第十六次"一成员多语义"）。

**✅ 与 §369 的"`pmFlags |= 0x800` 让客户端停止推进命令时间"**完全闭合 ✓

**⇒ **第四次确认那条链。**

**⚠ 而"`0x800` 在零售里用于【三个】**（`game end` / `streak use` / **`spawn protection`**）。**

**⇒ 所以**它不是一个"匹配结束"专用的位**。**

**✅ 一个**极重要的语义纠正**。

### 6.4 而 **`PMFLAGS|` 的八个字段**

```text
client / flags / frozen800 / pmType / alive / gametype / t
```

**⇒ 七项。**

**✅ 与 §368 的"三层命名失败项"**同族（**第八次）。**

**⚠ 而"`frozen800=` 单独一项"⇒ **所以那一位被显式抽出**。**

**✅ 与 §393 的"`cs` 的指纹"**同族。

## 七、**prematch 的两阶段完整实现**（本组第六重要）

### 7.1 而**"这一块就是『把瞬间结束变成 10 秒倒计时』的执行体"**

```php
// ★★ 刀AL：维持 prematch 窗口 —— 每秒重发状态词 + 滴一声，直到窗口结束。
//   这一块就是"把瞬间结束变成 10 秒倒计时"的执行体：只有 cha 走，
//   到期主动 reset（不做清理就会变成永久 prematch，和永久冻结同类的坑）。
if (life.prematchUntil)
{
    if (serverTime < *life.prematchUntil)
    {
        const auto secondsLeft = (*life.prematchUntil - serverTime + 999u) / 1000u;
        // 阶段二
        if (life.prematchStageTwoAt && serverTime >= *life.prematchStageTwoAt && life.prematchStage != 2) {
            life.prematchStage = 2;
            ask(..., "d 2557 \"" + matchMapName_ + "\" 3000", "prematch vision -> map");
            write(Warn, "PREMATCH|client=... phase=match_starting_in left=...s t=...");
        }
        if (life.prematchTickSecond != secondsLeft) {
            life.prematchTickSecond = secondsLeft;
            ask(..., "d 510 prematch", "cha prematch hold");
            // ⚠ 28100 已撤（甲方实测 + 零售录像）：「战斗即将开始并不会滴滴」
            //   ⇒ prematch 窗口内**只重发状态词，不再发 `p 52`**。
            write(Warn, "PREMATCH|client=... phase=waiting_for_more_players left=...s t=...");
        }
    }
    else { /* 关闭 */ }
}
```

### 7.2 十二层

```text
1. **"这一块就是『把瞬间结束变成 10 秒倒计时』的执行体"**
2. ⇒ **只有 cha 走**
3. ⇒ **到期【主动 reset**】
4. ⇒ **（不做清理就会变成永久 prematch，和永久冻结同类的坑）**
5. ⇒ **`secondsLeft = (until - now + 999) / 1000`** ⇒ **向上取整**
6. ⇒ **阶段二在【时间边界】上触发**
7. ⇒ **并 `ask("d 2557 \"<map>\" 3000", "prematch vision -> map")`**
8. ⇒ **每秒 `ask("d 510 prematch", "cha prematch hold")`**
9. ⇒ **而 `⚠ 28100 已撤`：「战斗即将开始并不会滴滴」⇒ 不再发 `p 52`**
10. ⇒ **（`ui_mp_timer_countdown` 不是开场倒计时音，是我早先的错误推断）**
11. ⇒ **`28500`：`INF` 在 `OLMOD_LOG_LEVEL=warn` 下不可见 ⇒ 窗口完全没有证人**
12. ⇒ **所以 `PREMATCH|` 提升到 `Warn`**
```

### 7.3 ⭐⭐ **"战斗即将开始并不会滴滴"**

**✅ 与 §355 的"玩家的判决"**第十二次。**

**⇒ 三层**：

```text
推断：`ui_mp_timer_countdown` 是开场倒计时音
⇒ **而甲方实测 + 零售录像：【不会滴滴**】
⇒ **⇒ 所以撤掉 `p 52`**
```

**✅ ⭐ **"是我早先的错误推断"** —— 一个诚实的自我更正**。**

**✅ 与 §384 的"一个编解码器不是一个类型"**同族（**第七次自我更正）。**

**⚠ 而"不做清理就会变成永久 prematch，和永久冻结同类的坑"⇒ **一个已知的错误模式**。**

**✅ 与 §380 的"不是活着意味着保持结束"**同族（**第二次"忘记释放"）。**

### 7.4 而**"窗口完全没有证人"**

**✅ 与 §372 的"失控不能是静默的"**完全同族（**第三次）。**

**⇒ 三层**：

```text
日志级别 `INF`
⇒ **而启动器跑在 `OLMOD_LOG_LEVEL=warn`**
⇒ **⇒ 所以每一行 `INF` 都被丢弃**
```

**✅ 与 §399 的"`INF` 被丢弃而 alias 带自 10-17 21:23 以来不可见"**完全一致 ✓

**⇒ **第二次确认那个日志级别问题。**

## 八、关键结论

1. **⭐⭐ `s 0201 "1"` 是零售【在每一个模式都发】而我们【一个都不发】的那条** —— 在 dm（`43100`）与 dmz（`23000`）各测到一次，而**对整个 ol-mod 树 grep `"0201"` 返回空**。
2. **⭐ "C# GameServer 的 status-command 工作叫它『让客户端进入比赛』，而它自己的修复坐在 `server-commands.txt`（默认 0）后面 ⇒ 所以它在那里也保持惰性"`** —— **两个独立实现都指向同一点**。
3. **⭐⭐ "dmz 没有那样的路径：客户端拿 gamestate、发 `68` 个包、然后等 `46` 秒并拆掉会话 ⇒ 那是一个【等待一个永不到来的信号】的客户端，不是一个拒绝任何东西的客户端"`** —— 第二次确认 `46` 秒。
4. **⭐ "若它改变了失败但没有修好它，延迟是下一个要移动的变量，不是那条命令"`**。
5. **⭐⭐ "一次一个缺失命令花了四个周期与四个负面（ui-screen 顺序、loot 带、`I 0 0 0`、`s 0201`）；而零售在我们那个窗口里发 `24` 条对 `10` 条 ⇒ 那是无望的"`** —— 一个经典的实验方法论批评，而**策略是"霰弹枪然后二分"**。
6. **"这里什么也没有解码，而那是故意的：`r`/`H`/`i`/`w`/`o` 与数字 `s` dvar 逐字节复现"`** —— 第七次"只复现不发明"。
7. **"`a 1213` 是唯一可能不能移植的值：`a <n>` 是生成中玩家的武器，而这个 build 报 `firstDynamicWeapon=1147` ⇒ 若客户端武器出来是错的而不是加入失败就先怀疑它"`** —— 第三次确认 `1147`。
8. **⭐⭐ `d 12246 1201` 的越界崩溃**：**`12246` 是【排他上界】而写它触发 `sub_590A60` 立刻通过 `sub_58F370` 初始化每一个新暴露的索引 ⇒ 而我们只注册到 `1168` ⇒ 索引 `1169` 在 `0x58F3C0` 被解引用**。
9. **⚠ `12246` vs 我们注册到 `1168` vs §388 的"注册了八把（`1147..1154`）"** —— 一处需要标注的差异（可能是后续注册更多）。
10. **⭐⭐ 五套 gametype 序列**（dm 3+5 / dmz 2+7 / cha 4+5 / coop 11+11+7 / spy 五条）。
11. **⭐ `d 2555 "compass_map_cargoship"` 带【四个浮点参数】** —— 第二次确认 `d` 的额外参数（且这里是四个）。
12. **⭐⭐ `d 5924 tag_stowed_back` 与 §378 的"`5896 + 28 = cs 5924 = tag_stowed_back`"完全闭合** —— 第三次确认那个 tag。
13. **`d 12250 tag_weapon_right`** 与 §361 的"`scriptMoverTagIndex` 连接到 `tag_weapon_right`"配合。
14. **⭐⭐⭐ `SvPmFlagsMatchEndFrozen(0x800)`【只有定义、从未置位】（全树无置位处）"`** —— 一个死常量，而 **2697 说 `PMF_FROZEN(0x800)` 在零售里用于 `game end` / `streak use` / **`spawn protection`**。
15. **"它不是一个下发命令，是玩家状态位，只能从快照读"`** —— 因为**命令流里 `invuln`/`godmode`/`protect`/`frozen`/`pm_flags` 全部 0 命中**。
16. **`PMFLAGS|` 的七个字段**（含单独的 `frozen800=`）—— 第八次"命名失败项"。
17. **⭐⭐ "这一块就是『把瞬间结束变成 10 秒倒计时』的执行体；到期主动 reset（不做清理就会变成永久 prematch，和永久冻结同类的坑）"`** —— 第二次"忘记释放"。
18. **⭐ "`⚠ 28100 已撤`：『战斗即将开始并不会滴滴』⇒ prematch 窗口内只重发状态词，不再发 `p 52`（`ui_mp_timer_countdown` 不是开场倒计时音，是我早先的错误推断）"`** —— 第七次自我更正。
19. **⭐ "`28500`：`INF` 在 `OLMOD_LOG_LEVEL=warn` 下不可见 ⇒ 窗口完全没有证人 ⇒ 所以 `PREMATCH|` 提升到 `Warn`"`** —— 第二次确认那个日志级别问题。

## 九、未闭合点

- `s 0201 "1"` 的语义（未解码）。
- `12246` 与我们注册到的 `1168` vs `1147..1154` 的差异。
- `L 13 6` 的语义。
- `SvAnnouncerTeamBanner` 的值（108？）。
- `spy` 的完整五阶段流程。
- `sv_main_mp.cpp` 4500 行之后未读取。
