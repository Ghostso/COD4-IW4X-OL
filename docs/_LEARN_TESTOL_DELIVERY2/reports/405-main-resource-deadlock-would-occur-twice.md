# 405 · **"连续两次同一把 mutex 被一个已持有它的调用方命中"** —— `resource deadlock would occur` 杀了服务器帧、`f1` 是女声 1 不是前缀

## 一、范围

本报告学习 `sv_main_mp.cpp` 5200–5550 行。

## 二、**非递归 mutex 的第二次死锁**（本组最重要的一段）

### 2.1 那段

```php
// NO LOCK. This is called from the character customization provider,
// which the frame loop invokes while already holding mutex_ -- taking
// it again is "resource deadlock would occur" on a non-recursive
// std::mutex, and it KILLED THE SERVER FRAME: `server frame terminated
// by C++ exception`, two clients stuck on the loading screen at
// active=0. That is the second time this feature has hit the same
// mutex from a caller that already owned it.
//
// The rule for this file, learned twice: a public ServerCore method
// takes mutex_ because the control thread may call it; anything the
// FRAME reaches must not. This one is frame-only.
void ServerCore::setBattleChatterVoiceFemale(const std::uint32_t clientNum, const bool female)
{
    battleChatterVoiceFemale_[clientNum] = female;   // ← 无锁
}
```

### 2.2 十六层

```text
1. **无锁**
2. ⇒ **它从【角色自定义 provider】调用**
3. ⇒ **而帧循环在【已持有 `mutex_`】时调用它**
4. ⇒ **再次取它是【`resource deadlock would occur`**】**
5. ⇒ **在一个【非递归 `std::mutex`】上**
6. ⇒ **而它【杀死了服务器帧**】**：
      · **`server frame terminated by C++ exception`**
      · **两个客户端卡在加载屏，`active=0`**
7. ⇒ **那是这个特性【第二次**】从【一个已持有它的调用方】命中同一把 mutex**
8. ⇒ **这个文件的规则（学了两次）**：
      · **一个【公开的 `ServerCore` 方法】取 `mutex_`**（因为控制线程可能调它）
      · **而任何【帧】触及的东西【绝不能取**】**
9. ⇒ **这个是【仅帧**】的**
```

### 2.3 ⭐⭐⭐ **"这个文件的规则，学了两次"**

**✅ 这是本文件里**最重要的一条并发规则**。**

**⇒ 三层**：

```text
公开方法（控制线程）⇒ **取 `mutex_`**
帧内路径          ⇒ **绝不取**
⇒ **⇒ 所以"谁调用"决定"取不取锁"**
```

**✅ 与 §394 的"两把锁（`mutex_` 与 `zmZonesMutex_`）"**完全同源 ✓

**⇒ 三层**：

```text
`mutex_`          ⇒ 控制线程 + 帧（**帧进入后不再取**）
`zmZonesMutex_`   ⇒ **因为 `loadGameplayScript` 持 `mutex_` 时脚本要读区域**
```

**✅ **一个"单一主锁 + 少量例外"的设计**。**

**⚠ 而"杀了服务器帧"⇒ **一个具体的后果**。**

**✅ 与 §392 的"`server frame terminated by C++ exception`"**完全一致 ✓

**⇒ **第二次确认那条错误消息。**

### 2.4 而**`sayBattleChatter` 的同一个坑第三次**

```php
// world_ DIRECTLY, NOT worldPlayerSample. Both callers already hold
// mutex_ - the frame loop for the reload trigger, the script builtin
// for the kill one - and the public accessor takes it again, which on
// a non-recursive std::mutex is "resource deadlock would occur". The
// test suite caught it on the first run; a live match would have taken
// the server down on the first kill. driveMatchAnnouncer reads
// world_.snapshot() the same way for the same reason.
const auto speakerState = world_.playerState(speakerClientNum);
```

**⇒ 十层**：

```text
1. **直接 `world_` 而不是 `worldPlayerSample`**
2. ⇒ **两个调用方【都已持有 `mutex_`】**：
      · **帧循环的换弹触发**
      · **脚本 builtin 的击杀触发**
3. ⇒ **而【公开的访问器】再取它**
4. ⇒ **在非递归 `std::mutex` 上那是 `resource deadlock would occur`**
5. ⇒ **测试套件【第一次运行】就抓到了它**
6. ⇒ **而一场实机比赛本会在【第一次击杀】时把服务器拿下去**
7. ⇒ **`driveMatchAnnouncer` 也读 `world_.snapshot()`**（**同样的方式、同样的理由**）
```

**✅ ⭐ **"测试套件第一次运行就抓到了它；而一场实机比赛本会在第一次击杀时把服务器拿下去"** —— 一个**极强的测试价值论证**。**

**⚠ 而"同一坑第三次"⇒ **一个反复的教训**。**

**✅ 与 §384 的"同一 bug 第三次"**同族（**第二次"同一 bug 重复"）。**

**⇒ 三层**：

```text
第一次：`setBattleChatterVoiceFemale`（杀帧）
第二次：（注释说"第二次"）
第三次：`sayBattleChatter` 的 `worldPlayerSample`
```

**⚠ 而"学了两次"⇒ **所以实际上至少三次**。**

**✅ 一个**诚实的计数**。

## 三、**`perkSlot` 的去重**（本组第二重要）

### 3.1 那段

```php
// ★ 2026-10-18（会话 28330 / 第 2 项）：**perkSlot 去重**。
//   实测：零售 cha demo `s perkSlot_*` = 0 条；我方 19:22 那局 210 条（6 槽 × 35 命）。
//   本函数在每次重生都会被 `PerkLife` 重建触发 ⇒ 每死都重发 6 条同样的值。
//   这里与「上一命真正发出去的 6 元组」比对，**完全相同就一条都不发**（只写日志）。
//   客户端 exe 里 `perkSlot_%d`（0x6ca3d8）确实存在 ⇒ 通道保留，只在值变化时用。
std::array<std::uint32_t, 6> slotValues{};
for (slot) slotValues[slot] = slot < life.perks.itemIds.size() ? std::max(1u, life.perks.itemIds[slot]) : 1u;
auto &sent = perkSlotsSent_[clientNum];
const bool slotsChanged = sent != slotValues;
if (slotsChanged) { 发六条; sent = slotValues; }
else { perkTrace = " unchanged"; queued = true; }
```

### 3.2 十三层

```text
1. **实测：零售 cha demo `s perkSlot_*` = `0` 条**
2. ⇒ **我方 `19:22` 那局 `210` 条**（**6 槽 × 35 命**）
3. ⇒ **本函数在每次重生都被 `PerkLife` 重建触发**
4. ⇒ **⇒ 每死都重发 6 条同样的值**
5. ⇒ **所以与"上一命真正发出去的 6 元组"比对**
6. ⇒ **完全相同 ⇒ 【一条都不发**】**（只写日志）
7. ⇒ **客户端 exe 里 `perkSlot_%d`（`0x6ca3d8`）确实存在**
8. ⇒ **⇒ 所以通道保留，只在值变化时用**
9. ⇒ **而 `std::max(1u, ...)` ⇒ 空槽写成 `1`**
10. ⇒ **（这是 CODOL 的空槽约定）**
```

### 3.3 ⭐⭐ **"零售零条而我方 210 条"**

**✅ 与 §341 的"`clientInfo` 零售零次而我们 11,048 次"**完全同族（**第二次"零售零而我们过量"）。**

**⇒ 三层**：

```text
零售：`s perkSlot_*` = **0 条**
我们：**210 条**（6 × 35）
⇒ **⇒ 一个纯过量的通道**
```

**✅ ⭐ **"完全相同就一条都不发"** —— 与 §341 的"一个未变的客户端完全不提"**同一条原则**。**

**⇒ **第三次确认那条原则。**

**⚠ 而"`0x6ca3d8`"⇒ **一个具体的地址**（`perkSlot_%d` 的格式串）。**

**✅ 一个**可验证的存在性**。

### 3.4 而**"空槽会写成 1，这是 CODOL 的空槽约定"**

**✅ 与 §381 的"`clipIndex == 0` 是空槽"**不同**。**

**⇒ 三层**：

```text
`clipIndex`     ⇒ **`0` 是空槽**
`perkSlot`      ⇒ **`1` 是空槽**
⇒ **⇒ 两个不同的哨兵**
```

**✅ 一个**精确的区分**（**第四次确认"零/一因空间而异"**）。

### 3.5 而**"客户端有 93 个 `specialty_*` 资产 ⇒ 技能效果极可能由客户端按 perk ID 自己实现"**

```php
// 取证结论（`步进-A3人物技能入口perkSlot-20261017-28100.md`）：
// 我方**已经有** `s perkSlot_0..5` 通道且真在发（demo 实测 `60050`/`60215`），
// 客户端有 93 个 `specialty_*` 资产 ⇒ **技能效果极可能由客户端按 perk ID 自己实现**。
// ⇒ 所以第一步不是"实现 6% 回弹 / 击杀爆尸"，而是**核对 perk ID 有没有传对**。
```

**⇒ 九层**：

```text
1. **我方已经有 `s perkSlot_0..5` 通道且【真在发**】**（demo 实测 `60050`/`60215`）
2. ⇒ **客户端有 `93` 个 `specialty_*` 资产**
3. ⇒ **⇒ 技能效果【极可能由客户端按 perk ID 自己实现**】**
4. ⇒ **所以第一步【不是】"实现 6% 回弹 / 击杀爆尸"**
5. ⇒ **而是【核对 perk ID 有没有传对**】**
6. ⇒ **所以本刀只加日志（**零玩法风险**）**：
      · **该角色/武器带的 perk 有没有进到槽里**
      · **每个槽的 ID 是多少（空槽会写成 1）**
```

**✅ ⭐⭐ **"第一步不是实现效果，而是核对 ID 有没有传对"** —— 一个**极重要的排查顺序**。**

**✅ 与 §370 的"去问键盘不要问镜像"**同族（**第九次"先确认输入再实现"）。**

**⚠ 而"`93` 个 `specialty_*` 资产"⇒ **一个具体的资产数**。**

**✅ 与 §350 的"373 个 `ET_SCRIPTMOVER`"**同族（**第二次"资产计数"）。**

## 四、**announcer 的队列合并**（本组第三重要）

### 4.1 那段

```php
// GROUP COALESCING (_globallogic_audio.gsc leaderDialogOnPlayer):
// a pending line of the same group is REPLACED, not followed. Two
// lead changes inside one 3 s window must not become "you're
// winning" then "you're losing" three seconds later, describing a
// board that has already moved on.
if (statusGroup && dialog.statusSlot && *dialog.statusSlot < dialog.queue.size()) {
    dialog.queue[*dialog.statusSlot] = announcerParameter;
    return;
}
if (statusGroup) dialog.statusSlot = dialog.queue.size();
dialog.queue.push_back(announcerParameter);
```

### 4.2 十层

```text
1. **组内合并**（`_globallogic_audio.gsc` 的 `leaderDialogOnPlayer`）
2. ⇒ **一个【同一组】的待播行被【替换**】，不是被跟随**
3. ⇒ **一个 `3` 秒窗口里的【两次领先变化】不能变成**
      · **"你在赢"**
      · **然后三秒后"你在输"**
4. ⇒ **描述一个【已经移动过的】计分板**
5. ⇒ **所以 `statusSlot` 记录那个槽的位置**
6. ⇒ **有槽 ⇒ 覆盖它**
7. ⇒ **无槽 ⇒ 记 `statusSlot = queue.size()` 然后 `push_back`**
```

**✅ ⭐ **"描述一个已经移动过的计分板"** —— 一个**极清晰的 UI 陈旧论证**。**

**✅ 与 §400 的"缓存键必须含那个状态"**同族（**第二次"陈旧的状态"）。**

**⚠ 而"`3` 秒窗口"⇒ 与 §402 的"`SvAnnouncerDialogSpacingMs`"**配合。**

**✅ 一个**精确的时间窗**。

### 4.3 而**`pumpAnnouncerDialog` 的"离开了的客户端什么都不保留"**

```php
if (clientNum >= slots.size() || slots[clientNum].state != ClientState::Active) {
    // A CLIENT THAT LEFT KEEPS NOTHING. Draining into a free slot
    // would send into another player's ring when the slot is reused.
    dialog.queue.clear();
    dialog.statusSlot.reset();
    continue;
}
```

**⇒ 五层**：

```text
1. **一个离开了的客户端【什么都不保留**】**
2. ⇒ **排空进一个空闲槽会在【那个槽被复用时**】**
3. ⇒ **发进【另一个玩家的环**】**
4. ⇒ **所以清 `queue` 与 `statusSlot`**
```

**✅ 与 §404 的"一个释放的槽绝不能带它的旧生命状态进下一个占用者"**完全同族（**第二次"槽复用"。**

**⇒ 三层**：

```text
§404  `uiClientLife_` 的槽复用 ⇒ **清 life 状态**
§405  `announcerDialog_` 的槽复用 ⇒ **清队列**
⇒ **⇒ 同一个原则两处**
```

**✅ **第六次确认"号复用"。**

### 4.4 而**"横幅与语音是【一个手势】"**

```php
// THE BANNER AND THE VOICE ARE ONE GESTURE. All fourteen `w 2 4 0`
// in the dm demo carry a high-band `p` on the same frame; splash
// row 4 is blank in every column, so the banner alone draws nothing.
```

**⇒ 五层**：

```text
1. **横幅与语音是【一个手势**】**
2. ⇒ **dm demo 里全部十四个 `w 2 4 0` 都在【同一帧】携带一个高带 `p`**
3. ⇒ **而 `splash` 的第 `4` 行在【每一列都是空白**】**
4. ⇒ **所以横幅【单独】什么也不画**
```

**✅ ⭐ **"splash 第 4 行在每一列都是空白"** —— 一个**具体的资产证据**。**

**⚠ 而"十四个 `w 2 4 0`"⇒ 与 §404 的"`i 0 0.000000 0 1` 的八帧"**不同**（不同的命令）。

**✅ 一个**精确的计数**。

### 4.5 而**"说它播了"**

```php
// 28400: SAY THAT IT PLAYED. "lead/lost is silent" had three possible
// owners -- the alias never registered, the queue never drained, or the
// client ignored `p <n>` -- and none of them left a line. This one
// separates them: it fires only when the queue actually emits, and it
// carries the id, so `p 106`/`p 107` in the log means the sound was
// handed to that client on that frame.
```

**⇒ 七层**：

```text
1. **说它播了**
2. ⇒ **"领先/失去是静默的"有三个可能的**所有者**：
      · **别名从未注册**
      · **队列从未排空**
      · **客户端忽略了 `p <n>`**
3. ⇒ **而它们【一个也没留一行**】**
4. ⇒ **这一行【分开它们**】**
5. ⇒ **它只在队列【真的发出时】触发**
6. ⇒ **而它携带那个 id**
7. ⇒ **所以日志里的 `p 106`/`p 107` 意味着那个声音【在那帧被交给了那个客户端**】
```

**✅ ⭐ **"三个可能的所有者，一个也没留一行"** —— 一个**典型的多因歧义**。**

**✅ 与 §399 的"`grep -c ... is 0`"**同族（**第六次"沉默的歧义"。**

## 五、**`sendRawCommand` 的"首字节通道"**（本组第四重要）

### 5.1 那段

```php
// THE CALLER STATES THE CHANNEL. It used to be inferred from the first
// byte -- printable ASCII means text -- and that was WRONG for the one
// command this tool exists to replay: `@` is 0x40, printable, and the
// demo records it as BINARY. The first live test sent it down the text
// path, hit CL_ServerCommand_Dispatch's default case, did nothing, and
// looked exactly like a negative result.
//
// A heuristic that is wrong for the subject of the experiment is worse
// than no tool, so payload[0] is now an explicit channel byte:
// 0 = text, 1 = binary. The bytes to send follow it.
const auto binary = payload[0] != 0;
const auto command = payload.subspan(1);
```

### 5.2 十二层

```text
1. **调用方【陈述】那个通道**
2. ⇒ **它过去是【从首字节推断**】的（可打印 ASCII ⇒ 文本）
3. ⇒ **而对这个工具存在的【那一条命令】那是错的**：
      · **`@` 是 `0x40`，可打印**
      · **而 demo 把它记录为【二进制**】**
4. ⇒ **第一次实机测试把它送下【文本路径**】**
5. ⇒ **命中 `CL_ServerCommand_Dispatch` 的 `default` 分支**
6. ⇒ **什么也没做**
7. ⇒ **而看起来【完全像一个负面结果**】**
8. ⇒ **一个对【实验主体】是错的启发式【比没有工具更糟**】**
9. ⇒ **所以 `payload[0]` 现在是一个【显式的通道字节**】
10. ⇒ **`0` = 文本，`1` = 二进制**
11. ⇒ **要发送的字节跟在它后面**
```

### 5.3 ⭐⭐⭐ **"一个对实验主体是错的启发式比没有工具更糟"**

**✅ 这是本文件里**最重要的一个工具设计教训**。**

**⇒ 三层**：

```text
启发式：可打印 ASCII ⇒ 文本
⇒ **而对 `@`（0x40）它错了**
⇒ **⇒ 而 `@` 正是【这个工具存在的理由**】
```

**✅ 与 §370 的"去问键盘不要问镜像"**同族（**第十次"启发式不可靠"）。**

**⚠ 而"看起来完全像一个负面结果"⇒ **最危险的失败模式**。**

**✅ 与 §397 的"一个结果在两种假设下都成立 ⇒ 零信息"**同族（**第三次"无效实验"。**

## 六、**`playAnnouncerLine` 与 `sendRawCommand` 的锁注释**

```php
std::uint32_t ServerCore::sendRawCommand(...) {
    // Locks, like playAnnouncerLine and for the same reason: the CONTROL
    // thread's drain calls this, and that drain does not hold mutex_.
    const std::lock_guard lock(mutex_);
}

std::uint32_t ServerCore::playAnnouncerLine(...) {
    const std::lock_guard lock(mutex_);
    // The VOICE only. No `w 2 4 0` banner: an audition is asking what a
    // clip says, and a banner on screen is one more thing to mistake for
    // the answer.
}
```

**⇒ 三层**：

```text
`sendRawCommand`      ⇒ **取锁**（因为**控制线程的 drain 调用它**而那个 drain 不持锁）
`playAnnouncerLine`   ⇒ **取锁**（同理由）
`sayBattleChatter`    ⇒ **不取锁**（因为**帧与 builtin 都持锁**）
```

**✅ ⭐ **一个清晰的三分**：**

```text
控制线程调用 ⇒ **取锁**
帧/builtin 调用 ⇒ **不取锁**
```

**✅ 与 §405 二.3 的"规则"**完全一致 ✓

**⇒ **第二次确认那条规则。**

**⚠ 而"试听只播声音不要横幅"⇒ **一个精确的实验设计**。**

**✅ 与 §370 的"阳性对照"**同族（**第五次"只测一个变量"）。**

## 七、`driveMatchAnnouncer` 的"两条都不调度"

```php
// BOTH LINES ARE QUEUED HERE AND NEITHER IS SCHEDULED. `on_your_own`
// is free-for-all's OBJECTIVE line - the mode with no objective
// still gets one - so it follows the gametype line through the same
// queue rather than after a delay this project invented. The demo's
// 3.0 s gap is the queue; demo 2's 12.5 s is a later prematch.
//
// The music is not dialogue and does not go through the queue: IW4
// plays it with a bare playLocalSound on the spawn frame. MEASURED
// in dm demo 2 at serverTime 19700, `p 2130` beside `p 1414`.
```

### 7.1 九层

```text
1. **两条都在这里排队而那一条也不【被调度**】**
2. ⇒ **`on_your_own` 是自由混战的【目标行**】**
3. ⇒ **（**没有目标的模式仍然得到一条**）**
4. ⇒ **所以它【通过同一个队列】跟随 gametype 行**
5. ⇒ **而不是在【这个项目发明的**】一个延迟之后**
6. ⇒ **demo 的 `3.0` 秒间隔【是那个队列**】**
7. ⇒ **demo 2 的 `12.5` 秒是【一个更晚的 prematch**】**
8. ⇒ **音乐不是对话而【不过那个队列**】**
9. ⇒ **IW4 用一个裸的 `playLocalSound` 在【出生帧**】播它**
10. ⇒ **（dm demo 2 在 `serverTime 19700`：`p 2130` 与 `p 1414` 并列**）**
```

**✅ ⭐ **"demo 的 3.0 秒间隔是那个队列；demo 2 的 12.5 秒是一个更晚的 prematch"** —— 一个**极精确的"不要发明延迟"论证**。**

**✅ 与 §404 三 的"延迟是常数；选择是那个竞赛"**同族（**第二次"延迟来自机制而不是调度"）。**

**⚠ 而"`p 2130` 与 `p 1414`"⇒ **两个 announcer id**。**

**✅ 与 §403 的"`p 2130` = SpawnMusic"**完全闭合 ✓

**⇒ **第二次确认 `2130`。**

## 八、关键结论

1. **⭐⭐⭐ "这个文件的规则，学了两次：一个公开的 `ServerCore` 方法取 `mutex_` 因为控制线程可能调它；任何【帧】触及的东西绝不能取"`** —— 而**违反它就是 `resource deadlock would occur`，杀死了服务器帧**（两个客户端卡在加载屏 `active=0`）。
2. **⭐ "那是这个特性【第二次】从【一个已持有它的调用方】命中同一把 mutex"`** —— 而 `sayBattleChatter` 又是**第三次**。
3. **⭐⭐ "两个调用方都已持有 `mutex_`（帧循环的换弹触发、脚本 builtin 的击杀触发）而公开的访问器再取它 ⇒ 测试套件【第一次运行】就抓到了它；而一场实机比赛本会在【第一次击杀】时把服务器拿下去"`** —— 一个极强的测试价值论证。
4. **⭐⭐ `perkSlot` 的去重**：**零售 cha demo `s perkSlot_*` = `0` 条而我们的 `210` 条（6 槽 × 35 命）** ⇒ **"完全相同就一条都不发"**（第三次确认 §341 的原则）。
5. **"客户端 exe 里 `perkSlot_%d`（`0x6ca3d8`）确实存在 ⇒ 通道保留，只在值变化时用"`** —— 一个可验证的存在性。
6. **`perkSlot` 的空槽是 `1`** 而 **`clipIndex` 的空槽是 `0`** —— 两个不同的哨兵（第四次确认"因空间而异"）。
7. **⭐⭐ "客户端有 `93` 个 `specialty_*` 资产 ⇒ 技能效果极可能由客户端按 perk ID 自己实现 ⇒ 所以第一步不是『实现 6% 回弹/击杀爆尸』而是【核对 perk ID 有没有传对】"`** —— 第九次"先确认输入再实现"。
8. **⭐ announcer 的组内合并**：**"两次领先变化不能变成『你在赢』然后三秒后『你在输』，描述一个已经移动过的计分板"`** —— 第二次"陈旧的状态"。
9. **"一个离开了的客户端什么都不保留：排空进一个空闲槽会在那个槽被复用时发进另一个玩家的环"`** —— 第六次确认"号复用"。
10. **"横幅与语音是一个手势：全部十四个 `w 2 4 0` 都在同一帧携带一个高带 `p`，而 `splash` 的第 4 行在每一列都是空白 ⇒ 横幅单独什么也不画"`**。
11. **⭐ "『领先/失去是静默的』有三个可能的所有者——别名从未注册、队列从未排空、客户端忽略了 `p <n>`——而它们一个也没留一行"`** —— 第六次"沉默的歧义"。
12. **⭐⭐⭐ `sendRawCommand` 的"首字节通道"**：**"可打印 ASCII ⇒ 文本"的启发式对 `@`（`0x40`）错了，而 `@` 正是【这个工具存在的理由】⇒ 它走了文本路径、命中 `default` 分支、什么也不做、而【看起来完全像一个负面结果】"`** —— 第三次"无效实验"，而 **"一个对实验主体是错的启发式比没有工具更糟"`**。
13. **清晰的三分锁规则**：**控制线程调用 ⇒ 取锁（`sendRawCommand` / `playAnnouncerLine`）/ 帧或 builtin 调用 ⇒ 不取锁（`sayBattleChatter`）**。
14. **"试听只播声音不要 `w 2 4 0` 横幅：一次试听是问一个片段说什么，而屏幕上的横幅是多一个会被误认为答案的东西"`** —— 第五次"只测一个变量"。
15. **⭐ "两条都在这里排队而那一条也不被调度：`on_your_own` 通过同一个队列跟随 gametype 行，而不是在一个【这个项目发明的】延迟之后；demo 的 3.0 秒间隔【是那个队列】；demo 2 的 12.5 秒是一个更晚的 prematch"`** —— 第二次"延迟来自机制而不是调度"。

## 九、未闭合点

- `SvAnnouncerDialogSpacingMs` 的值。
- `perks.itemIds` 的六个来源。
- `SV_BuildSplashCommand` 的四个参数。
- `sayBattleChatter` 的完整听众广播逻辑。
- `93` 个 `specialty_*` 资产的完整清单。
- `sv_main_mp.cpp` 5550 行之后未读取。
