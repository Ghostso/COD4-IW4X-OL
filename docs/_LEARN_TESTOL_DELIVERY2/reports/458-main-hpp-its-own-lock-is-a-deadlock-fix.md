# 458 · **"它自己的锁，而这不是一个优化 —— 它是为一个死锁的修复"** —— `zmZonesMutex_` 的完整病历、`driveCursorHints` 的"54 个里只有 1 个"、以及"一个没有名字就亮的提示比没有更糟"

## 一、范围

本报告学习 `sv_main_mp.hpp` 1100–1440 行。

## 二、**`zmZonesMutex_` 的完整死锁病历**（本组最重要的一段）

### 2.1 那段

```cpp
// ITS OWN LOCK, AND THIS IS NOT AN OPTIMISATION -- IT IS THE FIX FOR A
// DEADLOCK. ServerCore::loadGameplayScript holds mutex_ while it executes the
// gametype script, and that script calls the zm zone builtins, which read this
// model. Reading it under mutex_ therefore re-locks a NON-RECURSIVE mutex on
// the same thread and hangs the world spawn with no error logged -- observed
// 2026-09-01, the log stopping dead between "map triggers" and
// "gameplay script loaded".
//
// Safe because the order is one-way: a zone read never takes mutex_, so no
// cycle exists. Do not merge this back into mutex_.
mutable std::mutex zmZonesMutex_;
std::vector<SvZmZone> zmZones_;
```

### 2.2 二十四层

```text
1. **它自己的锁，而【这不是一个优化**】**
2. ⇒ **⇒ 它是【为一个死锁的修复**】**
3. ⇒ **`loadGameplayScript` **持 `mutex_`** 时【执行 gametype 脚本**】**
4. ⇒ **而【那个脚本【调用 zm 区域的内建**】**
5. ⇒ **⇒ 而那些内建【读这个模型**（`zmZones_`）**】**
6. ⇒ **⇒ 所以在 `mutex_` 下读它【在同一个线程上【重锁一个【非递归**的 mutex**】】**
7. ⇒ **⇒ 而【挂起世界出生**而【没有错误被记录**】】**
8. ⇒ **⇒ 观测 `2026-09-01`**：**日志【在 "map triggers" 与 "gameplay script loaded" 之间【完全停住**】】
9. ⇒ **⚠ 而【安全**因为【顺序是【单向的**】】**
10. ⇒ **⇒ 一个区域读【从不取 `mutex_`**】`
11. ⇒ **⇒ 所以【没有环存在**】**
12. ⇒ **⇒ 【不要把这个合并回 `mutex_`**】**
```

### 2.3 ⭐⭐⭐ **"日志在 map triggers 与 gameplay script loaded 之间完全停住"**

**✅ 这是本报告里**最重要的一条"一个死锁的可观测签名**。**

**✅ 与 §405 的"`resource deadlock would occur` 杀死了服务器帧"**——**互补** ✓

**⇒ 三层**：
```text
§405  **`resource deadlock would occur`**（**一个【抛异常**的死锁**）
§458  **一个【静默**的死锁（**日志停住而【没有错误**）**
⇒ **⇒ 所以【两种死锁，两个签名**】
```

**✅ ⭐⭐⭐ **"两种死锁两个签名"** —— 一个**极重要的区分**。

**⚠ 而"一个显式的锁（`std::lock_guard`）会抛 `resource deadlock would occur`"**⇒ **而这里【没有**。】

**⇒ 三层**：
```text
若【用 `lock_guard`**】⇒ **`resource deadlock would occur`**
若【用手动 `lock()/unlock()` 或 `try_lock`**】⇒ **静默**
⇒ **⇒ 所以【两种实现两个签名**】
```

**✅ ⭐⭐ **"两种实现两个签名"**。</br>

**⚠ 而注释说"re-locks a NON-RECURSIVE mutex on the same thread"**⇒ **一个 `lock_guard` 会抛**。

**⇒ 三层**：
```text
若【`lock_guard`**】⇒ **`std::system_error`**
而【日志停住** ⇒ **所以【不是 `lock_guard`**？**
⇒ **⇒ 或者【那个异常【在另一个线程**被吞了**】
```

**⚠ 一个**需要标注的疑点**（**两种可能的机制**）。

### 2.4 而**"顺序是单向的，所以没有环"**

**⇒ 十层**：
```text
1. **一个区域读【从不取 `mutex_`**】
2. ⇒ **⇒ 所以【`zmZonesMutex_` → `mutex_` 的顺序【永不发生**】**
3. ⇒ **而 `mutex_` → `zmZonesMutex_` 【会发生**】
4. ⇒ **⇒ 所以【单向 ⇒ 无环 ⇒ 无死锁**】
```

### 2.5 ⭐⭐⭐ **"一个单向的锁顺序"**

**✅ 与 §405 的"两把锁（`mutex_` 与 `zmZonesMutex_`）"**完全闭合 ✓

**⇒ 三层**：
```text
§405  **"两把锁：`mutex_`（控制线程 + 帧）与 `zmZonesMutex_`（zones，因为 `loadGameplayScript` 持 `mutex_` 时脚本要读区域）"**
§458  **那个设计的完整理由 + 一个死锁的观测**
⇒ **⇒ 同一个设计，两处**
```

**✅ ⭐⭐⭐ **"同一个设计两处"**。

**⚠ 而"不要把这个合并回 `mutex_`"**⇒ **一个【明确的将来指令**。】

**✅ 与 §437 的"若重提交被看到，扩展 `beginSessionRoster()`"**同族（**第五次"可执行的前进路径**）。

## 三、**`driveCursorHints` 的"54 个里只有 1 个"**（本组第二重要）

### 3.1 那段

```cpp
// THE USABLE PROMPT. Each frame, for each living client, decides whether they
// are standing in a usable trigger and publishes the hint that names it.
//
// ONLY `zombie_door` FOR NOW, on purpose. The shipped table carries all 54 of
// zm_factory_sh's trigger_use -- perk machines, the mystery box, the ammo boxes,
// the teleporter -- and every one of them is a piece of gameplay that does not
// exist yet. A prompt offering to open something this server cannot open is
// worse than no prompt, so the rest stay dark until the thing behind them works.
void driveCursorHints(std::span<const SvWorldClientInput> activeClients);
```

### 3.2 二十层

```text
1. **每帧，对流每个活着的客户端，决定他们是否站在一个可用触发器里**
2. ⇒ **并发布【命名它的那个提示**】**
3. ⇒ **⚠ 【现在只有 `zombie_door`，故意的**】**
4. ⇒ **发运的表携带【`zm_factory_sh` 的【全部 `54` 个 `trigger_use`**】】
5. ⇒ **（**perk 机器、神秘箱、弹药箱、传送器**）**
6. ⇒ **⇒ 而【每一个都是【一个还不存在的玩法**】】
7. ⇒ **⇒ 所以【一个【提供打开这个服务器打不开的东西**】的提示【比没有提示更糟**】】
8. ⇒ **⇒ 所以【其余的【保持暗**】直到【它们后面的东西【工作**】】
```

### 3.3 ⭐⭐⭐ **"一个提供打开这个服务器打不开的东西的提示比没有提示更糟"**

**✅ 这是本报告里**最重要的一条"一个诚实的空**。**

**✅ 与 §410 的"一个交付不了任何东西的特性对一场活的比赛没有主张"**——**完全同族** ✓

**⇒ 三层**：
```text
§410  **"一个交付不了任何东西的特性【没有主张**】"
§458  **"一个提供打开打不开的东西的提示【比没有更糟**】"
⇒ **⇒ 同一个原则，两个表现**（一个**关掉特性**，一个**不给提示**）
```

**✅ ⭐⭐⭐ **"同一个原则两个表现"**。

**⚠ 而"`54` 个 `trigger_use`"⇒ **一个具体的数**。**

**✅ 与 §440 的"`zm_sumpf_sh` 的 `74` 个 spawn 点里 `32` 个有 goal"**同族（**第三次"一个具体的计数**）。

**⇒ 三层**：
```text
§420  **factory 的 `69` 个 spawner**
§440  **`zm_sumpf_sh` 的 `74` 个 spawn 点**
§458  **`zm_factory_sh` 的 `54` 个 `trigger_use`**
⇒ **⇒ 三次"一个地图的实体计数**】
```

**✅ ⭐ **一个"地图实体计数"的三例表**。</br>

**⚠ 而"`54` 里的 `1` 个（`zombie_door`）是工作的**"⇒ **`1.85%`**。

**⇒ 三层**：
```text
`54` 个触发器
`1` 个有提示
⇒ **⇒ 所以【`98.15%` 【保持暗**】
```

**✅ ⭐⭐ **"`98.15%` 保持暗"**。

## 四、**`registerHintString` 的"96 宽的带"**（本组第三重要）

### 4.1 那段

```cpp
// THE HINT STRING TABLE. Hands back the RELATIVE index into configstring
// band 856 -- which is what playerState.cursorHintString carries -- for
// a piece of hint text, registering it on first use.
//
// Deliberately the same shape as the client's own allocator
// (sub_4EC5D0): scan from the low end, return the slot that already
// holds this text, otherwise take the first free one. Returns nullopt
// when the band is full, because the band is 96 wide and a 97th hint is
// a caller bug rather than something to wrap around on.
//
// The text may be a localization key (`ZOMBIE_BUTTON_REWARD_BARRIER`)
// or literal text -- the retail zm captures carry both, and a key the
// client cannot resolve is drawn as-is.
[[nodiscard]] std::optional<std::uint16_t> registerHintString(std::string_view text);
```

### 4.2 二十层

```text
1. **提示串表 ⇒ 返回 `configstring` 带 `856` 的【相对索引**】**
2. ⇒ **⇒ 而那正是 `playerState.cursorHintString` 携带的东西**
3. ⇒ **在【首次使用时注册**】**
4. ⇒ **⚠ 【刻意与客户端自己的分配器（`sub_4EC5D0`）同一个形状**】**
5. ⇒ **（从低端扫、返回已经持有这个文本的槽、否则取第一个空闲**）**
6. ⇒ **⇒ 当带满时返回 `nullopt`**】
7. ⇒ **因为【带是 `96` 宽**】**
8. ⇒ **⇒ 而【第 `97` 个提示【是一个调用方 bug**】而不是【要环绕处理的东西**】**
9. ⇒ **⚠ 文本可以是【一个本地化键**（`ZOMBIE_BUTTON_REWARD_BARRIER`）**或【字面文本**】】
10. ⇒ **⇒ 零售 zm 捕获【两种都有**】**
11. ⇒ **⇒ 而【一个客户端解不出的键【被原样画出**】】
```

### 4.3 ⭐⭐⭐ **"刻意与客户端自己的分配器同一个形状"**

**✅ 这是本报告里**最重要的一条"与客户端算法对齐**。**

**✅ 与 §439 的"对齐真实弹道（`.mode = BulletLocational` + `.allowChildren`）"**——**完全同族** ✓

**⇒ 三层**：
```text
§412  **bot 的遮挡门【对齐真实弹道**】
§447  **`actorfire` 的 trace【对齐同样的参数**】
§458  **提示串分配器【对齐客户端的 `sub_4EC5D0`**】
⇒ **⇒ 三次"对齐既有实现**】
```

**✅ ⭐⭐⭐ **一个"对齐既有实现"的三例表**。

**⚠ 而"带是 `96` 宽"⇒ **一个具体的容量**。**

**⇒ 三层**：
```text
`96` ⇒ **`HintStringConfigStringCount`**（§412/§416 的 `HintStringConfigStringBase`）
⇒ **⇒ 而【第 `97` 个【是一个 bug**】
```

**✅ 与 §416 的"`cursorHintString` 是 configstring 带 `856` 的相对索引"**完全闭合 ✓

**⚠ 而"第97个是一个调用方 bug 而不是要环绕处理的东西"**⇒ **一个明确的选择**。**

**✅ 与 §422 的"扣住子实体直到这个名字出现"**同族（**第十一次"省略优于错误**）。

**⇒ 三层**：
```text
可选 A：**环绕（复用最旧的）** ⇒ **一个提示【指向错误的名字**】
可选 B：**返回 `nullopt`** ⇒ **调用者【知道失败**】
⇒ **⇒ 所以【后者正确**】
```

**✅ ⭐⭐ **"环绕会让一个提示指向错误的名字"**。

**⚠ 而"一个客户端解不出的键被原样画出"**⇒ **与 §440 的"`""` 是一个真实的答案"**同族（**第四次"一个宽容的处置**）。

## 五、`matchCompletionAnnounced_` 与"四个地方设 `completed`"

```cpp
bool matchCompletionAnnounced_{};
// The serverTime the match was DECIDED. Retail's end-of-match sequence
// is a schedule hung off that instant, not a single frame's worth of
// commands - see driveMatchEndSequence.
std::uint32_t matchCompletionServerTime_{};
```

**⇒ 六层**：
```text
1. **`matchCompletionAnnounced_`** ⇒ **一个一次性标记**
2. ⇒ **`matchCompletionServerTime_`** ⇒ **那个决定时刻**
3. ⇒ **⇒ 而【§407 说"四条不同路径设 `completed` ⇒ 所以在一处处观察这个转移**】**
4. ⇒ **⇒ 所以【一个标记 + 一个时间戳**】
```

**✅ 与 §407 的"四条路径一个出口"**完全闭合 ✓

**⇒ 三层**：
```text
§407  **"四条不同路径都设 `matchStatus_.completed`，所以在这个转移上观察，而不是在四条各自宣告"**
§458  **`matchCompletionAnnounced_` + `matchCompletionServerTime_`**
⇒ **⇒ 一个"边沿捕获"的完整实现**】
```

**✅ ⭐ **一个"边沿捕获"的实例**。

## 六、**`lastCharacterCustomizations_` 的"键在 XUID 上"**

```cpp
// THE LAST CUSTOMIZATION THAT RESOLVED, PER PLAYER. Section 166: the
// provider runs EVERY FRAME and its answer is not retained anywhere, so a
// single frame on which it cannot answer drops that client out of the
// snapshot's clientInfos -- and writeClientInfos then tells every observer
// to REMOVE a clientInfo it already has. A removed clientInfo is a player
// with modelIndex zero, which is a player with no model name, which is a
// player nobody can see. Keyed on XUID so a reused client slot cannot
// inherit the previous occupant's character.
struct ClientCustomizationMemory
{
    std::uint64_t xuid{};
    SvCharacterCustomization customization{};
};
std::unordered_map<std::uint32_t, ClientCustomizationMemory> lastCharacterCustomizations_;
```

**⇒ 十层**：
```text
1. **那个 provider【每帧**跑而【它的答案【不在任何地方**被保留**】**
2. ⇒ **⇒ 所以【有一帧它答不出**】⇒ **那个客户端【掉出**快照的 `clientInfos`**】**
3. ⇒ **而 `writeClientInfos` 然后【告诉每一个观察者【移除**】一个它已经有的 `clientInfo`**】
4. ⇒ **⇒ 一个被移除的 `clientInfo` ⇒ `modelIndex` 零**】
5. ⇒ **⇒ ⇒ 一个没有模型名的玩家**】
6. ⇒ **⇒ ⇒ 【一个没人能看见**的玩家**】**
7. ⇒ **⇒ 【键在 XUID 上**，所以【一个被复用的客户端槽【不能**继承前一个占用者的角色**】】
```

### 6.1 ⭐⭐⭐ **"一个被移除的 clientInfo 是一个 modelIndex 零的玩家，一个没有模型名的玩家，一个没人能看见的玩家"**

**✅ 这是本报告里**最重要的一条"一个四段链**。**

**✅ 与 §426 的"`req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY ⇒ 那个客户端再也没写过模型名 ⇒ 没人能看见那个玩家"**——**完全同源** ✓

**⇒ 三层**：
```text
§426  **`model=EMPTY` ⇒ 再也没写过模型名 ⇒ 没人能看见**
§458  **`modelIndex` 零 ⇒ 没有模型名 ⇒ 没人能看见**
⇒ **⇒ 同一个链，两处**
```

**✅ ⭐⭐⭐ **"同一个链两处"**。

**⚠ 而"键在 XUID 上"⇒ **与 §413 的 `lastCharacterCustomizations_` 的 `xuid` 匹配**完全闭合 ✓

**⇒ 三层**：
```text
§413  **"`memory.xuid = clientSlots[index].xuid;` 与 `else if (memory.xuid && memory.xuid == clientSlots[index].xuid)`"**
§458  **"键在 XUID 上，所以一个被复用的客户端槽不能继承前一个占用者的角色"**
⇒ **⇒ 一个"缓存必须绑定身份"的完整理由**
```

**✅ ⭐⭐ **"缓存必须绑定身份"**。</br>

**✅ 与 §400 的"缓存键必须含那个状态"**同族（**第九次"缓存键"）。

## 七、`MatchParticipation` 的"累积 + 一个活跃起点"

```cpp
struct MatchParticipation
{
    std::uint64_t xuid{};
    std::uint32_t accumulatedMilliseconds{};
    std::optional<std::uint32_t> activeSince;
};
```

**⇒ 八层**：
```text
1. **`accumulatedMilliseconds` ⇒ 一个【累积量**】
2. ⇒ **`activeSince` ⇒ 一个【可选的起点**】**
3. ⇒ **⇒ 所以【`nullopt` ⇒ 不活跃**
4. ⇒ **而【有值 ⇒ 从那一刻起【在累积**】】
5. ⇒ **⇒ 与 §413 的 `matchParticipationMilliseconds` 的 `total += end - *activeSince`** 完全闭合 ✓
```

**✅ ⭐⭐ **一个"累积 + 起点"的实例**。</br>

**✅ 与 §413 的"`participation < 1'000 ⇒ continue`"**配合。

## 八、关键结论

1. **⭐⭐⭐ `zmZonesMutex_` 的完整死锁病历**：**"`loadGameplayScript` 持 `mutex_` 时执行 gametype 脚本，而那脚本调用 zm 区域的内建，它们读这个模型 ⇒ 在 `mutex_` 下读它在同一个线程上重锁一个非递归 mutex ⇒ 挂起世界出生而【没有错误被记录】—— 观测 `2026-09-01`，日志在 `"map triggers"` 与 `"gameplay script loaded"` 之间【完全停住】**）"**。
2. **⭐⭐⭐ "两种死锁两个签名"**：**§405 的 `resource deadlock would occur`（一个抛异常的）vs §458 的一个静默的（日志停住而没有错误）** —— 一个极重要的区分；而**这里的机制可能不是 `lock_guard`（否则会抛）**，需标注。
3. **⭐⭐⭐ "顺序是单向的：一个区域读从不取 `mutex_`，所以没有环 ⇒ 不要把这个合并回 `mutex_`"`** —— 与 §405 的"两把锁"完全闭合，也是**第五次"可执行的前进路径"**。
4. **⭐⭐⭐ `driveCursorHints` 的"54 个里只有 1 个"**：**"发运的表携带 `zm_factory_sh` 的【全部 `54` 个 `trigger_use`**】（perk 机器、神秘箱、弹药箱、传送器），而【每一个都是一个还不存在的玩法】⇒ **"一个提供打开这个服务器打不开的东西的提示【比没有提示更糟】"`** ⇒ **`98.15%` 保持暗** —— 与 §410 的"一个交付不了任何东西的特性没有主张"**完全同族**。
5. **⭐ 第三次"一个地图的实体计数"**：factory 的 `69` 个 spawner（§420）/ `zm_sumpf_sh` 的 `74` 个 spawn 点（§440）/ `zm_factory_sh` 的 `54` 个 `trigger_use`（§458）。
6. **⭐⭐⭐ `registerHintString` 的"刻意与客户端自己的分配器（`sub_4EC5D0`）同一个形状：从低端扫、返回已经持有这个文本的槽、否则取第一个空闲"`** —— 第三次"对齐既有实现"（与 §412/§447 同族）。
7. **⭐⭐ "带是 `96` 宽而第 `97` 个提示是一个调用方 bug 而不是要环绕处理的东西"`** ⇒ **"环绕会让一个提示指向错误的名字"** —— 第十一次"省略优于错误"（与 §422 同族）。
8. **⭐ "文本可以是一个本地化键或字面文本，而【一个客户端解不出的键被原样画出】"`** —— 一个宽容的处置（**第四次**）。
9. **⭐⭐ `matchCompletionAnnounced_` + `matchCompletionServerTime_` 是 §407 的"四条路径一个出口"的完整实现**（**一个边沿捕获**）。
10. **⭐⭐⭐ `lastCharacterCustomizations_` 的四段链**：**"那个 provider 每帧跑而它的答案不在任何地方被保留 ⇒ 有一帧它答不出 ⇒ 那个客户端掉出快照的 `clientInfos` ⇒ `writeClientInfos` 告诉每一个观察者【移除】一个它已经有的 `clientInfo` ⇒ 一个被移除的 `clientInfo` 是 `modelIndex` 零 ⇒ 没有模型名 ⇒ 【一个没人能看见的玩家】**）"**，而**"键在 XUID 上，所以一个被复用的客户端槽不能继承前一个占用者的角色"`** —— 与 §426 的"同一个链"完全闭合，第九次"缓存键"。
11. **⭐ `MatchParticipation` 的"累积量 + 一个可选的起点"**（`nullopt` ⇒ 不活跃）与 §413 的 `matchParticipationMilliseconds` 完全闭合。

## 九、未闭合点

- `zmZonesMutex_` 的死锁为何是静默的而不是抛 `resource deadlock would occur`。
- `sub_4EC5D0` 的客户端分配器实现。
- `54` 个 `trigger_use` 里 `zombie_door` 是哪个。
- `HintStringConfigStringCount = 96` 的确认。
- `sv_main_mp.hpp` 1440 行之后未读取（**共 `1793` 行**）。
