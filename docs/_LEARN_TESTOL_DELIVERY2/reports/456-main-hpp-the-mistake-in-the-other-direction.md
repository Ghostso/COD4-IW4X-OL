# 456 · **"`524` 是 3.3.3.3 的索引用在 OLfinal 客户端上 —— 那个注释想避免的错误，在另一个方向上犯了"** —— 播报队列、`397` 的三面验证、以及两个比例窗的不相接

## 一、范围

本报告学习 `sv_main_mp.hpp` 420–760 行。

## 二、**"那个注释想避免的错误，在另一个方向上犯了"**（本组最重要的一段）

### 2.1 那段

```cpp
// The "+" in "+50". IW4's _rank.gsc labels its score popup with &"MP_PLUS".
//
// THIS WAS 524 AND THE REASONING FOR IT WAS EXACTLY BACKWARDS. The old
// comment read: "it is a per-build index - the retail demo's own label 397
// belongs to OLfinal's table and would print whatever happens to sit at 397
// here, so it was NOT copied", and took 524 from a live 3.3.3.3 client's
// localized configstrings instead.
//
// Both halves of that are right except for which build "here" is. Section
// 109 establishes that the demo IS this build: four configstring indices
// match out.exe's own (2557..2562, 2452+clientNum, 15, 464), all sixteen of
// its precache names are present verbatim in this install's zones, and its
// SVC_EOF is 5 rather than 3.3.3.3's 6. So 397 is OLfinal's index used on
// an OLfinal client, and 524 was 3.3.3.3's index used on an OLfinal client
// - the very mistake the comment set out to avoid, committed in the other
// direction.
//
// MEASURED: label=397 on the score popup, six times, in the same element
// that carries value=50 and y=-50.
constexpr std::uint16_t SvScoreFeedbackLabel = 397;
```

### 2.2 二十四层

```text
1. **`+50` 里的那个 `+`；IW4 的 `_rank.gsc` 用它标分数弹出**
2. ⇒ **⚠ 而【这个值曾是 `524`**】**
3. ⇒ **⇒ 而【那个推理【恰好是反的**】**
4. ⇒ **旧注释**："它是**一个逐 build 的索引** —— **零售 demo 自己的 `label 397` 属于 OLfinal 的表**而会打印在这里 `397` 位置上**碰巧**是任何东西，**所以它【没有被拷贝**】"**
5. ⇒ **而【从【一个活的 3.3.3.3 客户端的本地化 configstring**】取了 `524`**
6. ⇒ **⚠ 【两半都是对的，除了"这里"是哪个 build**】】
7. ⇒ **第 `109` 节确立：【那个 demo 就是**这个 build**
8. ⇒ **四个 configstring 索引与 `out.exe` 自己的匹配**（`2557..2562`、`2452+clientNum`、`15`、`464`）
9. ⇒ **全部十六个 precache 名字【逐字**出现在这个安装的 zone 里**
10. ⇒ **而它的 `SVC_EOF` 是 `5`**而不是 3.3.3.3 的 `6`
11. ⇒ **⇒ 所以【`397` 是【OLfinal 的索引**用在【一个 OLfinal 客户端**上**
12. ⇒ **而 `524` 是【3.3.3.3 的索引**用在【一个 OLfinal 客户端**上**
13. ⇒ **⇒ 【那个注释想避免的错误，在另一个方向上犯了**】】
14. ⇒ **⇒ 【测量：`label=397` 在分数弹出上，六次，在与 `value=50` 和 `y=-50` 同一个元件里**】**
```

### 2.3 ⭐⭐⭐ **"两半都是对的，除了『这里』是哪个 build"**

**✅ 这是本报告里**最重要的一条"一个正确的推理的错前提**。**

**✅ 与 `AGENTS.md` 的"ol-mod 服务的是 3.3.3.3、把我们的目标当另一个 build"**——**完全同族** ✓

**⇒ 三层**：
```text
旧推理：**"397 属于 OLfinal 的表，会打印在这里碰巧的 397"**
⇒ **`397` 是【OLfinal 的索引**（**对**）
⇒ **而"这里"是【3.3.3.3**（**错**）
⇒ **⇒ 所以【结论反了**】
```

**✅ ⭐⭐⭐ **"结论反了"** —— 一个**极精确的自我诊断**。

**⚠ 而"那个注释想避免的错误，在另一个方向上犯了"**⇒ **一个罕见的"双重否定**。**

**⇒ 三层**：
```text
想避免：**用 3.3.3.3 的索引在一个 OLfinal 客户端**
而实际：**用了 3.3.3.3 的 `524`，而**丢弃了 OLfinal 的 `397`**
⇒ **⇒ 所以【恰好做了想避免的那件事**】
```

**✅ 与 §413 的"方向错了"**同族（**第八次"方向反了**）。

**⇒ 三次闭合**：
```text
§404  **"我上一刀把 dm 的 `16/14` 用到 cha，方向错了"**
§413  **"我早先的错误推断"**
§456  **"那个注释想避免的错误，在另一个方向上犯了"**
⇒ **⇒ 三次"方向反了**】
```

**✅ ⭐⭐ **一个"方向反了"的三例表**。

### 2.4 而**"四面体证的 build 身份"**

**⇒ 十层**：
```text
1. **四个 configstring 索引**（`2557..2562` / `2452+clientNum` / `15` / `464`）**与 `out.exe` 匹配**
2. ⇒ **全部十六个 precache 名字【逐字**在 zone 里**
3. ⇒ **`SVC_EOF` 是 `5`**（**而 3.3.3.3 是 `6`**）
4. ⇒ **⇒ 三条独立证据**
5. ⇒ **⇒ 所以【那个 demo **就是这个 build**】
```

**✅ ⭐⭐⭐ **"三条独立证据确立那个 demo 就是这个 build"** —— 与 §414 的"两条独立路径"**同族（**第四次"多源验证"）。

**⇒ 三层**：
```text
§408  **`d 15 0`/`d 464 0` 从 `out.exe` 与线上两条独立路径**
§414  **`238/238` brush 与表**
§456  **三条证据（configstring / precache / `SVC_EOF`）**
⇒ **⇒ 三次"多源验证**】
```

**✅ ⭐⭐ **一个"多源验证"的三例表**。

**⚠ 而"`SVC_EOF` 是 `5` 而 3.3.3.3 是 `6`"**⇒ **与 `AGENTS.md` 的"ol-mod 自己写 3.3.3.3 用 6 收尾、OLfinal 用 5"**——**完全一致** ✓

**⇒ 三层**：
```text
`AGENTS.md`：**"3.3.3.3 ends a server message with 6; OLfinal ends it with 5"**（**`net_chan_mp.hpp` 的原文**）
§456：**"`SVC_EOF` 是 `5` 而不是 3.3.3.3 的 `6`"**
⇒ **⇒ 所以【同一个判据两处**】
```

**✅ ⭐⭐⭐ **"同一个判据两处"** —— 而 **这条判据【是本项目权威层级的基石**。

## 三、**"一个日程是一个错误的模型，而它产生了一个没有意义的常量"**（本组第二重要）

### 3.1 那段

```cpp
// THE ANNOUNCER IS A QUEUE, NOT A SCHEDULE, AND BLACK OPS' OWN SOURCE SAYS SO.
//
// CODREF: Black Ops mod tools, raw/maps/mp/gametypes/_globallogic_audio.gsc
// `playLeaderDialogOnPlayer` -- play the sound, then `wait ( 3.0 )` before
// the next line for that player, with `leaderDialogQueue` holding the rest.
// So NO announcer line ever lands within 3 s of another on one client, and
// a second line does not overwrite the first, it follows it.
//
// THIS DISSOLVES A CONSTANT THAT WAS WRITTEN DOWN AS UNEXPLAINED. The demo's
// `on_your_own` follows the match-start line by 3.0 s in demo 1 and 12.5 s
// in demo 2, which was recorded here as "not a fixed offset, whatever
// selects it is something else". It is not a delay at all: both are queued
// at spawn and the queue drains at 3 s. Demo 2's gap is a longer queue.
// A SCHEDULE WAS THE WRONG MODEL and it produced a constant with no meaning.
```

### 3.2 二十四层

```text
1. **播报器是一个【队列**，不是一个【日程**】**
2. ⇒ **而 Black Ops 自己的源码【这么说**】**
3. ⇒ **`playLeaderDialogOnPlayer` ⇒ 播那个声音，然后 `wait(3.0)` **才到下一行**
4. ⇒ **而 `leaderDialogQueue` 持有其余**
5. ⇒ **⇒ 所以【没有一个播报行【会在 3 秒内**落到同一客户端的上一行旁边**】
6. ⇒ **而【第二行【不覆盖**第一行**】**
7. ⇒ **⇒ 它【跟随**它**
8. ⇒ **⚠ 而这【溶解了一个曾被记为【未解释**】的常量**】
9. ⇒ **demo 的 `on_your_own` 在 demo 1 里【跟随 match-start 行 `3.0` 秒**】**
10. ⇒ **而在 demo 2 里【`12.5` 秒**】**
11. ⇒ **⇒ 而那【曾被记为"不是一个固定偏移，选它的东西是别的**】】**
12. ⇒ **⇒ 它【根本不是一个延迟**：两者都在 spawn 时入队，而【队列以 3 秒排空**】**
13. ⇒ **⇒ demo 2 的间隙【是一个更长的队列**】**
14. ⇒ **⇒ 【一个日程是一个错误的模型**，而它【产生了一个【没有意义**的常量**】】
```

### 3.3 ⭐⭐⭐ **"一个日程是一个错误的模型，而它产生了一个没有意义的常量"**

**✅ 这是本报告里**最重要的一条"错误的模型产生错误的常量**。**

**✅ 与 §404 的"demo 的 3.0 秒间隔是那个队列，不是我发明的延迟"**——**完全同源** ✓

**⇒ 三层**：
```text
§404  **"demo 的 `3.0` 秒间隔是那个队列；demo 2 的 `12.5` 秒是一个更晚的 prematch"**
§409  **"两条都在这里排队而那一条也不被调度"**
§456  **"一个日程是一个错误的模型"**
⇒ **⇒ 三次"队列不是日程**】
```

**✅ ⭐⭐⭐ **一个"队列不是日程"的三例表**。

**⚠ 而"`3.0` vs `12.5`"⇒ **同一个命令的两个间隔**。**

**⇒ 三层**：
```text
demo 1 的间隙 ⇒ `3.0`
demo 2 的间隙 ⇒ `12.5`
⇒ **⇒ 而【同一个队列 ⇒ 所以【demo 2 有【更长的队列**】
```

**✅ ⭐⭐⭐ **"demo 2 有一个更长的队列"** —— 本报告最漂亮的推理。</br>

**✅ 而"`wait(3.0)`"⇒ **一个源码级的证据**。**

**⇒ 三层**：
```text
源码 ⇒ `wait(3.0)`
而【一个"日程"的模型【会说"偏移是 `3.0` 或 `12.5`"**
⇒ **⇒ 所以【源码【否证**了日程模型】
```

**✅ ⭐⭐ **"源码否证了日程模型"**。

### 3.4 而**"`timesUp` 是精确的：`30.0` 秒剩余，到帧"**

```cpp
// `timesUp` is exact: 30.0 s remaining, to the frame (dm demo 1).
constexpr std::uint32_t SvAnnouncerTimesUpRemainingMs = 30'000;
```

**⇒ 六层**：
```text
1. **`timesUp` 是【精确的**：`30.0` 秒剩余**
2. ⇒ **到帧**】
3. ⇒ **⇒ 所以【一个【阈值**触发】
```

**✅ 与 §455 的"`100ms` 在 `97.4%`"**不同（那是**一个模态值**，这是**一个精确的阈值**）。

**⇒ 三层**：
```text
`timesUp` ⇒ **`30'000ms` 剩余，到帧**（**精确**）
帧间隔 ⇒ **`100ms`**（§455）
⇒ **⇒ 所以【`30'000` 是 `300` 帧的整数倍**】**
```

**✅ ⭐ **一个"阈值的整齐性"**。

## 四、**"`5000` 是同一个引擎家族的数字，而不是这个项目的一个猜测"**（本组第三重要）

### 4.1 那段

```cpp
// CODREF: _globallogic_score.gsc `onTeamScore` --
//     `getTime() - level.lastStatusTime > 5000`
// one shared floor across the match, exactly this shape, and SIX TIMES
// SHORTER than the 30 s invented here before the source was read.
//
// WHAT IT IS NOT EVIDENCE FOR: that block is the TEAM path, and lead_taken /
// lead_lost appear nowhere else in Black Ops - it has no free-for-all lead
// callout at all. CODOL added one (both dm demos carry it), so CODOL's own
// floor is unmeasured. 5000 is the same engine family's number rather than
// this project's guess, which is the whole improvement.
constexpr std::uint32_t SvAnnouncerLeadChangeCooldownMs = 5'000;
```

### 4.2 二十层

```text
1. **`_globallogic_score.gsc` 的 `onTeamScore`**：`getTime() - level.lastStatusTime > 5000`
2. ⇒ **一个在整个比赛里共享的地板**，**恰好这个形状**
3. ⇒ **⇒ 而【比这里在没有读源码之前【发明的 `30` 秒【短六倍**】】**
4. ⇒ **⚠ 而它【不是什么**的证据**：
      · **那个块是【TEAM 路径**】
      · **而 `lead_taken`/`lead_lost` **在 Black Ops 里【别处都不出现**】**
      · **⇒ 它【完全没有一个自由混战的领先呼叫**】**
5. ⇒ **CODOL 【加了一个**（两个 dm demo 都携带它）**
6. ⇒ **⇒ 所以 CODOL 自己的地板【是未测量的**】
7. ⇒ **⇒ `5000` 是【同一个引擎家族的数字**而不是【这个项目的一个猜测**】**
8. ⇒ **⇒ 而那【是【全部的改进**】】
```

### 4.3 ⭐⭐⭐ **"`5000` 是同一个引擎家族的数字而不是这个项目的一个猜测，而那是全部的改进"**

**✅ 这是本报告里**最重要的一条"改进的定义**。**

**⇒ 三层**：
```text
之前：**`30'000`（一个发明）**
现在：**`5000`（同一个引擎家族的数字）**
⇒ **⇒ 而【CODOL 自己的地板【仍未测量**】】
⇒ **⇒ 所以【这【不是**一个正确的值，只是一个【更可信**的值】
```

**✅ ⭐⭐⭐ **"这不是一个正确的值，只是一个更可信的值"** —— 一个**极精确的定性**。

**✅ 与 §408 的"两个数从不同路径读出"**不同（那是**验证**，这是**一个更可信的猜测**）。

**⇒ 三层**：
```text
§414  **"BO1 是一个供体参照，不是恢复的 `aipaths`"**
§455  **"3.3.3.3 猜了 `16` 而测量是 `8`"**
§456  **"`5000` 是同一个引擎家族的数字而不是这个项目的一个猜测"**
⇒ **⇒ 三次"外部 vs 本地**】
```

**✅ ⭐⭐ **一个"外部 vs 本地"的三例表**。

**⚠ 而"`lead_taken`/`lead_lost` 在 Black Ops 里别处都不出现"**⇒ **一个精确的负面**。**

**⇒ 三层**：
```text
Black Ops ⇒ **没有自由混战的领先呼叫**
CODOL ⇒ **加了一个**
⇒ **⇒ 所以【一个 OLfinal 独有的特性**】
```

**✅ 与 §407 的"vision 家族是 OLfinal 的唯一增量"**同族（**第二次"OLfinal 独有**）。

**⇒ 三层**：
```text
§407  **vision 的 `N` 是"这个路径上唯一的 OLfinal 独有增量"**
§456  **领先呼叫是 Black Ops **没有**而 CODOL 有**
⇒ **⇒ 两次"OLfinal 独有**】
```

**✅ ⭐⭐ **一个"OLfinal 独有"的两例表**。

## 五、**两个比例窗的"不相接"**（本组第四重要）

### 5.1 那段

```cpp
// The popup scales, and both durations below are retail's, read off one
// elem followed through its whole life:
//
//   t+0     fontScale 3.0, fromFontScale 0.9, scaleTime 100   grow
//   t+100   fromFontScale 3.0                 scaleTime 200   flat at 3.0
//   t+300   fontScale 0.9, fromFontScale 3.0, scaleTime 172   settle
//   t+1000  colour alpha 27 -> 0              fadeTime  750   fade
//
// The two scale windows there do NOT meet. The third update reuses the
// second window's start time, so by the time it is sent its window has
// already elapsed - the number holds flat at 3.0 and then jumps. Copying
// that literally is what made this look choppy.
//
// So the flat middle is dropped and the shrink window is started exactly
// where the grow window ends. Both durations stay retail's; the change is
// only that the windows now ABUT.
```

### 5.2 二十层

```text
1. **弹出会缩放，而两个时长【都是零售的**（**从一个元件【跟完它整个生命**读出**）
2. ⇒ **`t+0` ⇒ `fontScale 3.0`、`fromFontScale 0.9`、`scaleTime 100`** ⇒ **生长**】
3. ⇒ **`t+100` ⇒ `fromFontScale 3.0`、`scaleTime 200`** ⇒ **平在 `3.0`**】
4. ⇒ **`t+300` ⇒ `fontScale 0.9`、`fromFontScale 3.0`、`scaleTime 172`** ⇒ **沉降**】
5. ⇒ **`t+1000` ⇒ 颜色 `alpha 27 → 0`、`fadeTime 750`** ⇒ **淡出**】
6. ⇒ **⚠ 而那两个缩放窗【不相接**】**
7. ⇒ **第三次更新【复用**第二个窗的起点**】
8. ⇒ **⇒ 所以【到它被发出的时候，它的窗【已经过去了**】**
9. ⇒ **⇒ 而那个数字【平在 `3.0` 然后【跳**】**
10. ⇒ **⇒ 【照字面拷贝它【正是让这个看起来【卡顿**】的东西**】
11. ⇒ **⚠ 所以【中间的平台被丢弃**，而【收缩窗【恰好从生长窗结束的地方开始**】**
12. ⇒ **⇒ 两个时长【仍然是零售的**】**
13. ⇒ **⇒ 唯一的改变是【这两个窗现在【相接**】】
```

### 5.3 ⭐⭐⭐ **"第三次更新复用第二个窗的起点，所以到它被发出的时候它的窗已经过去了"**

**✅ 这是本报告里**最重要的一条"一个时间戳的重用**。**

**⇒ 三层**：
```text
第二次：`fromFontScale 3.0, scaleTime 200`（**从 `t+100` 起 `200ms` ⇒ 到 `t+300`**）
第三次：**`scaleTime 172` 但【起点【仍是 `t+100`**】**
⇒ **⇒ 所以【到它被发出（`t+300`）时，`t+100+172 = t+272`【已经过去**】】
⇒ **⇒ 而那个值【瞬跳到 0.9**】**
```

**✅ ⭐⭐⭐ **"到它被发出时 `t+272` 已经过去 ⇒ 那个值瞬跳到 0.9"** —— 本报告最精确的机制分解。</br>

**✅ 与 §419 的"`+14000`/`+15500` 的时间缩放"**不同（那是**一个斜坡**，这是**一个瞬跳**）。

**⇒ 三层**：
```text
`d 11861` 的时间缩放 ⇒ **一个斜坡**（`1000ms` 从 `1` 到 `0.25`）
而【这个弹出 ⇒ 【一个瞬跳**】（**因为窗已经过去**）
⇒ **⇒ 所以【同一个"时间窗"机制，两个后果**】
```

**✅ ⭐⭐ **"同一个时间窗两个后果"**。

**⚠ 而"照字面拷贝它正是让这个看起来卡顿的东西"**⇒ **一个"忠于零售反而更糟"的实例**。**

**⇒ 三层**：
```text
零售 ⇒ **一个卡顿的动画**（**因为它的第三次更新的窗已经过去了**）
我们照抄 ⇒ **同样的卡顿**
而修法 ⇒ **让两个窗相接**（**一个【改进**）**
⇒ **⇒ 所以【一个"忠于零售"的规则【在这里被【有理由地**违反**】
```

**✅ ⭐⭐⭐ **"一个忠于零售的规则在这里被有理由地违反"** —— 与 §407 的"vision 的 `N` 是 OLfinal 独有"**不同（那是**加**，这是**改**）。

**⇒ 三层**：
```text
§407  **`N` 是【OLfinal 独有**的增量
§456  **两个窗相接【是一个【项目自己的**改进**
⇒ **⇒ 所以【两种"偏离"**
```

**✅ ⭐⭐ **"两种偏离"**。

### 5.4 而**"`50ms` 的服务器帧与 `100ms` 的生长 ⇒ 边界落在一帧上，而不可能跳跃"**

```cpp
// The server frame is 50ms and the grow is 100ms,
// so the boundary lands on a frame exactly and no jump is possible.
```

**⇒ 六层**：
```text
1. **服务器帧 `50ms`**
2. ⇒ **而【生长 `100ms`**】**
3. ⇒ **⇒ 所以【边界【恰好落在一帧上**】】**
4. ⇒ **⇒ 而【不可能跳跃**】**
```

**⚠ 而 §455 说"`100ms` 才是零售的节奏，`50ms` 在 `30Hz` 主机上【不整除**"**。**

**⇒ 三层**：
```text
§455  **"`50` 不整除这个主机 ⇒ `100ms` 才是对的**"
§456  **"服务器帧是 `50ms`**"（**一个假设**）
⇒ **⇒ 所以【这个"边界落在帧上"的论证【建立在一个【可能不对**的 `50ms` 上**】
```

**⚠ 一个**可推导的矛盾**（**若帧是 `100ms` 而生长是 `100ms`，那也恰好落在一帧上**）。

**⇒ 三层**：
```text
`100ms` 帧 + `100ms` 生长 ⇒ **也恰好一帧**
`50ms` 帧 + `100ms` 生长 ⇒ **也恰好两帧**
⇒ **⇒ 所以【两个都成立**】
```

**✅ ⭐⭐⭐ **"两个都成立"** —— **所以那个论证【不受**帧率影响**。

## 六、`SvAnnouncerState` 的"`leader` 空直到有人真的得分"

```cpp
struct SvAnnouncerState
{
    bool matchStartSent{};
    bool timesUpSent{};
    // The slot that is currently top of the board. Empty until somebody has
    // actually scored - at 0-0 every player is "leading" and announcing it
    // would fire on the first frame of every match.
    std::optional<std::uint32_t> leader;
    std::optional<std::uint32_t> lastLeadChangeServerTime;
};
```

**⇒ 八层**：
```text
1. **`leader` 空【直到有人真的得分**】**
2. ⇒ **⇒ 因为【在 `0-0` 每一个玩家都是"领先**"**
3. ⇒ **而【宣告它【会在【每一场比赛的第一帧**】触发**
4. ⇒ **⇒ 与 §406 的"`bestClientKills` 在 `0-0` 返回最低占用槽 ⇒ 需要 `<= 0` 守卫**"**完全闭合** ✓
```

**✅ ⭐⭐⭐ **"与 §406 完全闭合"** —— 而 **这里的修法是"`leader` 为 `std::optional` 且空直到真的得分"**。

**⇒ 三层**：
```text
§406  **`if (!best || best->second <= 0) return;`**（**一个值守卫**）
§456  **`std::optional<std::uint32_t> leader`**（**一个类型守卫**）
⇒ **⇒ 所以【同一个问题的两个修法**】
```

**✅ ⭐⭐⭐ **"同一个问题的两个修法"** —— 一个**极精确的对照**。

## 七、关键结论

1. **⭐⭐⭐ `SvScoreFeedbackLabel` 的那个 `524` 的病历**：**"旧注释说『397 属于 OLfinal 的表，会打印在这里碰巧的 397，所以它没有被拷贝』，而从一个活的 3.3.3.3 客户端取了 `524`"`** —— **"两半都是对的，除了『这里』是哪个 build"** ⇒ **"那个注释想避免的错误，在另一个方向上犯了"**。
2. **⭐⭐⭐ 三条独立的 build 身份证据**：**四个 configstring 索引与 `out.exe` 匹配（`2557..2562` / `2452+clientNum` / `15` / `464`）/ 全部十六个 precache 名字逐字在 zone 里 / `SVC_EOF` 是 `5` 而不是 3.3.3.3 的 `6`** ⇒ **"那个 demo 就是这个 build"** —— 第四次"多源验证"。
3. **⭐⭐⭐ `SVC_EOF = 5` 与 `AGENTS.md` 的"3.3.3.3 用 `6` 收尾、OLfinal 用 `5`"完全一致** —— **同一个判据两处**，而它是**本项目权威层级的基石**。
4. **⭐ "MEASURED: `label=397` 在分数弹出上，六次，在与 `value=50` 和 `y=-50` 同一个元件里"`**。
5. **⭐⭐⭐ "播报器是一个队列，不是一个日程"**：**`playLeaderDialogOnPlayer` 播那个声音然后 `wait(3.0)` 才到下一行，而 `leaderDialogQueue` 持有其余** ⇒ **"没有一行会在 3 秒内落到同一客户端的上一行旁边，而第二行不覆盖第一行，它跟随它"`**。
6. **⭐⭐⭐ "这溶解了一个曾被记为『未解释』的常量：demo 1 的 `3.0` 秒与 demo 2 的 `12.5` 秒【都是队列】** ⇒ **"一个日程是一个错误的模型，而它产生了一个没有意义的常量"`** —— 第三次"队列不是日程"（与 §404/§409 同族），而 **"demo 2 有一个更长的队列"** 是本报告最漂亮的推理。
7. **⭐ "`timesUp` 是精确的：`30.0` 秒剩余，到帧"`** —— 而 `30'000 / 100 = 300` 帧（**一个阈值的整齐性**）。
8. **⭐⭐⭐ `SvAnnouncerLeadChangeCooldownMs` 从 `30'000`（一个发明）改到 `5000`**（**`_globallogic_score.gsc` 的 `getTime() - level.lastStatusTime > 5000`**，**同一个引擎家族的数字**）—— 而 **"`lead_taken`/`lead_lost` 在 Black Ops 里【别处都不出现】，它完全没有一个自由混战的领先呼叫，CODOL 加了一个"** ⇒ **"CODOL 自己的地板仍未测量；`5000` 是同一个引擎家族的数字而不是这个项目的一个猜测，而那是【全部的改进**】"**。
9. **⭐⭐ "这不是一个正确的值，只是一个更可信的值"`** —— 一个极精确的定性；而它是**第二次"OLfinal 独有"**（与 §407 的 vision `N` 同族）。
10. **⭐⭐⭐ 两个比例窗的"不相接"**：**零售的第二次更新 `fromFontScale 3.0, scaleTime 200`（从 `t+100` 起）而第三次 `scaleTime 172` 但【起点仍是 `t+100`】** ⇒ **"到它被发出（`t+300`）时 `t+100+172 = t+272` 已经过去 ⇒ 那个值瞬跳到 `0.9`"`** —— 本报告最精确的机制分解。
11. **⭐⭐⭐ "照字面拷贝它正是让这个看起来卡顿的东西，所以中间的平台被丢弃而收缩窗恰好从生长窗结束的地方开始（两个窗现在【相接】）"`** ⇒ **"一个忠于零售的规则在这里被有理由地违反"`** —— 而**"两个时长仍然是零售的"`**。
12. **⭐ "服务器帧是 `50ms` 而生长是 `100ms`，所以边界恰好落在一帧上而不可能跳跃"`** —— 而**那个论证【不受**帧率影响**（**`100ms` 帧也恰好一帧**）。
13. **⭐⭐⭐ `SvAnnouncerState::leader` 是 `std::optional` 且【空直到有人真的得分**】⇒ **"与 §406 的 `if (!best || best->second <= 0) return;` 是同一个问题的两个修法"`**（**一个值守卫 vs 一个类型守卫**）。

## 八、未闭合点

- `SvAnnouncerLeadTakenHigh = 1681` / `LeadLostHigh = 1683` / `WinningHigh = 1058` 的校准。
- `SvPrematchWaitingText = 396` 与 `SvPrematchStartingText = 396` **同值**（一个可疑点）。
- `SvScoreFeedbackFromColor = 0xD8FFA629` vs `FadeToColor = 0x00FFA629` 的 alpha 差（`0xD8 = 216`）。
- `SvFeedbackFadeToColor = 0x00FFFFFF`（**白色**）vs `SvScoreFeedbackGlowColor = 0x00FFA629`。
- `sv_main_mp.hpp` 760 行之后未读取（**共 `1793` 行**）。
