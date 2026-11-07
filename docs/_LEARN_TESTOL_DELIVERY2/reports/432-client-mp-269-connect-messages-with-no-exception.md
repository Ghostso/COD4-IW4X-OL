# 432 · **"实测 269 条 `MP_CONNECTED` 无一例外：`15 FE <base64>`"** —— 一个漏掉的字节让屏上显示 `MP_CONNECT?`、以及"门是一个性质而不是一个计时器"

## 一、范围

本报告学习 `sv_client_mp.cpp` 2480–2810 行（`addClientXp`、`announceConnectionChanges` 的 `f`/`e` 命令、`publishZmRoundHud` 的 `200` 帧门、`bestClientKills` 的平局判据）。

## 二、**`0x15` 那个漏掉的字节**（本组最重要的一段）

### 2.1 那段

```php
// ★★ 28100 刀AG（甲方 2026-10-17：「右上角 MP_CONNECT 那个 base64 本轮研究一下」）——
//   **实测：零售的这条消息在名字前还有一个 `0x15`**，我方一直只发 `0xFE`。
//   证据（本轮逐份拆 17 份 spy demo，共 **269** 条 `MP_CONNECTED`，**无一例外**）：
//     紧跟 "MP_CONNECTED" 的 3 字节全部是 `15 FE <base64首字符>`：
//       [15 FE 35]×162  [15 FE 36]×32  [15 FE 62]×10  [15 FE 4D]×9  [15 FE 63]×7  [15 FE 56]×6 …
//   实样本（`0C-2020-11-19[17-10-13]spy.demo` @759722 一带）：
//     f "MP_CONNECTED \x15 \xFE 5bCP6JmO5LuW54i5OTk4 \xFE ^7"
//     base64 解出 **小虎他爹998**（15 B）；另一条解出 **你好我是空白**（18 B）
//     ⇒ `0x15`(=21) **不是长度**（15/18 都不等于 21）⇒ 按零售**照抄恒定 tag**，不猜语义。
//   ⚠ 这条与"那一份 demo 里 0x15"是同一件事：此前 `-1340` 记的"逐要素一致"漏了这 1 字节，
//     而客户端把它当参数解析的一部分 ⇒ 屏上就显示成 `MP_CONNECT?` + 名字。
```

### 2.2 二十四层

```text
1. **实测：零售的这条消息【在名字前还有一个 `0x15`**】**
2. ⇒ **而我方【一直只发 `0xFE`**】**
3. ⇒ **证据：逐份拆 `17` 份 spy demo，共 `269` 条 `MP_CONNECTED`，【无一例外**】**
4. ⇒ **紧跟 `"MP_CONNECTED"` 的 `3` 字节全是 `15 FE <base64首字符>`**
5. ⇒ **分布**：
      · **`[15 FE 35]` × `162`**
      · **`[15 FE 36]` × `32`**
      · **`[15 FE 62]` × `10`**
      · **`[15 FE 4D]` × `9`**
      · **`[15 FE 63]` × `7`**
      · **`[15 FE 56]` × `6`**
6. ⇒ **实样本**：`f "MP_CONNECTED \x15 \xFE 5bCP6JmO5LuW54i5OTk4 \xFE ^7"`
7. ⇒ **base64 解出【小虎他爹998**】（`15` 字节）
8. ⇒ **另一条解出【你好我是空白**】（`18` 字节）
9. ⇒ **⇒ `0x15`（`21`）【不是长度**】（`15`/`18` 都不等于 `21`）**
10. ⇒ **⇒ 所以【按零售【照抄恒定 tag**】，不猜语义**】
11. ⇒ **⚠ 此前 `-1340` 记的"逐要素一致"【漏了这 1 字节**】**
12. ⇒ **而客户端【把它当参数解析的一部分**】**
13. ⇒ **⇒ 屏上就显示成【`MP_CONNECT?` + 名字**】**
```

### 2.3 ⭐⭐⭐ **"`0x15` 不是长度（`15`/`18` 都不等于 `21`）⇒ 照抄恒定 tag，不猜语义"**

**✅ 这是本报告里**最重要的一条"排除长度假设**。**

**⇒ 三层**：
```text
假设：`0x15 = 21` 是【名字的字节长度**】
实测：两条名字是 `15` 与 `18` 字节 ⇒ **都不等于 `21`**
⇒ **⇒ 所以【它不是长度**】
```

**✅ 与 §413 的"`+0x090` 读出 `[?,0,1,…,10]` ⇒ 不是 faction"**完全同族（**第三次"用值的范围否证假设"）。

**⇒ 三层**：
```text
§413  `+0x090` 的 `0..10` ⇒ 不是 faction
§417  `+0x09C` 的 `1..409` ⇒ 不是 clientNum
§432  `0x15` 与 `15`/`18` 不符 ⇒ 不是长度
⇒ **⇒ 三次"范围否证**】
```

**✅ ⭐⭐⭐ **一个"范围否证"的三例表**。

**⚠ 而"照抄恒定 tag，不猜语义"⇒ **一个明确的保守选择**。**

**✅ 与 §425 的"`SMALL` 每发 `LARGE` 不发，因为不发明一个没有可观察差异的规则"**同族（**第七次"不要发明"）。

**⇒ 三层**：
```text
`0x15` 的语义 ⇒ **未知**
而【它的位置与值【恒定**】 ⇒ **照抄即可**
⇒ **⇒ 所以【不需要知道语义**】
```

**✅ ⭐⭐ **"一个恒定的值不需要语义**。

### 2.4 而**"此前记的『逐要素一致』漏了这 1 字节"**

**✅ 这是本报告里**最重要的一条"验证方法的漏洞**。**

**⇒ 三层**：
```text
旧验证：**逐要素一致**
漏掉：**一个【夹在 `"MP_CONNECTED"` 与 `0xFE` 之间的 `0x15`**】
⇒ **⇒ 所以【"逐要素"的定义【漏了一个位置**】】
```

**✅ 与 §411 的"一个合并的计时窗口制造了一个错误的嫌疑"**同族（**第七次"一个测量的定义决定了它的盲区"）。

**⇒ 三层**：
```text
§411  **合并的计时窗口** ⇒ 分不清 think 与脚本
§432  **"逐要素"** ⇒ 漏掉一个【不显眼**的位置
⇒ **⇒ 两次"方法的定义决定盲区**】
```

**✅ ⭐⭐⭐ **一个"盲区"的两例表**。

**⚠ 而"客户端把它当参数解析的一部分 ⇒ 屏上显示成 `MP_CONNECT?` + 名字"⇒ **一个可见的症状**。**

**✅ 与 §407 的"`d 792` 的 `mat`/`offmat` 换位"**同族（**第二次"一个字节的差异产生可见的错"）。

**⇒ 三层**：
```text
§407  **两个 `d` 记录的键顺序**
§432  **一个 `0x15` 字节**
⇒ **⇒ 两次"一个字节/顺序的可见后果**】
```

**✅ ⭐ **一个"字节级可见性"的两例**。

### 2.5 而**"17 份 demo、269 条、无一例外"**

**✅ 这是本报告里**最重要的一条统计强度**。**

**⇒ 三层**：
```text
样本：**`17` 份 demo**
事件：**`269` 条**
例外：**`0`**
⇒ **⇒ 所以【这是一个【强结论**】】
```

**✅ 与 §414 的"`238/238` 零例外"**同族（**第二次"零例外 ⇒ 强结论"）。

**⇒ 三层**：
```text
§414  `238/238` brush ⇒ **不变式**
§424  `16/17` ⇒ **约定**
§432  **`269/269` ⇒ 强结论**
⇒ **⇒ 三次"例外计数**】
```

**✅ ⭐⭐ **一个"例外计数"的三例表**。

**⚠ 而"`[15 FE 35]` × `162`"⇒ **`162/269 = 60%`**。**

**⇒ 三层**：
```text
`35` = `'5'` ⇒ **base64 首字符 `'5'`** ⇒ **一个以 `5` 开头的 base64**
⇒ **⇒ 所以【`162` 条名字【都以 `5` 开头**】**
```

**✅ 而 base64 的 `'5'`（`0x35`）⇒ **前 6 位是 `110101` = `53`** ⇒ **原文首字节高 6 位 `110101`** ⇒ **原文首字节 `0xD?`** ⇒ **UTF-8 中文（`0xE4..0xE9`）？**

**⚠ 等等**：`0x35` 是 ASCII `'5'`，base64 索引 `57`。而 `57 << 2 = 228 = 0xE4` ⇒ **正是 UTF-8 中文的首字节高 4 位** ✓

**✅ ⭐⭐⭐ **"`'5'` 解码出首字节 `0xE4` ⇒ 一个中文名"** —— 一个**可验证的推论**。

**⇒ 三层**：
```text
base64 `'5'` ⇒ 索引 `57`
`57 << 2 = 228 = 0xE4`
⇒ **⇒ 而 `0xE4` 是 UTF-8 三字节中文的首字节** ✓
```

**✅ 与 §432 二 的"小虎他爹998"（中文名）**完全吻合 ✓

**✅ ⭐⭐ **一个"base64 首字符 ⇒ 原文首字节"的推论**。

## 三、**`f` 与 `e` 是一条特性的两半**（本组第二重要）

### 3.1 那段

```php
// MEASURED (retail 2021 corpus, verb 'e', 9 distinct / 35 total):
//   e "<FE>base64<FE>^7 EXE_LEFTGAME"
// The same 0xFE-wrapped base64 name as 'f', with the reason INSIDE the
// quotes after `^7 ` and no MP_ prefix. CG_ServerCommand case 101 ('e')
// and case 102 ('f') reach the same sink 0x0044D170, so the pair is one
// feature and this tree was sending half of it.
```

### 3.2 十四层

```text
1. **`e "<FE>base64<FE>^7 EXE_LEFTGAME"`**
2. ⇒ **与 `f` 【同一个 `0xFE` 包裹的 base64 名字**】**
3. ⇒ **而【理由在引号内 `^7 ` 之后**】**
4. ⇒ **而【没有 `MP_` 前缀**】**
5. ⇒ **`CG_ServerCommand` 的 case `101`（`'e'`）与 case `102`（`'f'`）【到达同一个 sink `0x0044D170`**】**
6. ⇒ **⇒ 所以【那一对【是一条特性**】】**
7. ⇒ **⇒ 而【这棵树一直只发了一半**】**
```

### 3.3 ⭐⭐⭐ **"那一对是一条特性，而这棵树一直只发了一半"**

**✅ 与 §407 的"`RELOAD_START` 不是 `RELOAD`，因为一次换弹产生不止一个事件"**——**互补**。

**⇒ 三层**：
```text
§407  **两个命令的区分**（选对的那个）
§432  **两个命令是同一条特性的两半**（两个都要）
⇒ **⇒ 相反的判断，同一个方法【看它们到哪个 sink**】
```

**✅ ⭐⭐⭐ **"看它们到哪个 sink"** —— 一个**判决性判据**。

**⇒ 三层**：
```text
`sink` 相同 ⇒ **同一条特性**（两个都要）
`sink` 不同 ⇒ **不同的特性**（选合适的那个）
⇒ **⇒ 所以【`sink` 是那条分界线**】
```

**✅ ⭐⭐ **一个"sink 决定关系"的判据**。

**⚠ 而"`e` 的出现是 `9` 个不同/`35` 次，而 `f` 呢？"⇒ **未给出**。**

**⚠ 而"`EXE_TIMEDOUT` / `EXE_PLAYERKICKED_BOT_BALANCE` 未实现"⇒ **一个诚实的 CODDIFF**。

**⇒ 六层**：
```text
零售也用 `EXE_TIMEDOUT` 与 `EXE_PLAYERKICKED_BOT_BALANCE`
⇒ **而【这里只看到"槽变 Free**】**
⇒ **⇒ 所以【每一次离开都被宣告为 `EXE_LEFTGAME`**】**
⇒ **⇒ 而【区分超时需要【把 cause 带出 `takeTimeoutDrops`**】】**
⇒ **⇒ 那是一个【分开的改动**】】
```

**✅ 与 §426 的"`TimeoutDrop::Cause` 枚举"**完全闭合 ✓

**⇒ 三层**：
```text
§426  `dropClientSlot(clientNum, TimeoutDrop::Cause::...)`
§432  **`takeTimeoutDrops` 已经返回 `TimeoutDrop` 带 `cause`**
⇒ **⇒ 所以【数据【已经有了**，只是【`announceConnectionChanges` 没读它**】】
```

**⚠ 一个**比注释说的更近的改动**（`cause` **已经在 `TimeoutDrop` 里**，只是公告没用它）。

**✅ ⭐⭐ **一个"数据已有而没被消费"的实例** —— 与 §416 的"`predictableEvents` 读了、用了、在线上之前丢掉"**同族（**第三次）。

**⇒ 三层**：
```text
§413  **常量定义了而写通道不存在**
§416  **`predictableEvents` 有数据而没发**
§432  **`TimeoutDrop.cause` 有数据而公告没读**
⇒ **⇒ 三次"最后一公里"**
```

**✅ ⭐⭐ **一个"最后一公里"的三例表**。

### 3.4 而**"一个名字不能编码的槽必须不被每帧重试"**

```php
// Claimed BEFORE the roster lookup, exactly as this did when it was a
// set: a slot whose name cannot be encoded must not be retried every
// frame. The name is filled in below once there is one, and a slot
// still holding the empty string is simply not announced as leaving.
connectionAnnounced_.insert_or_assign(clientNum, std::string{});
...
if (it->second.empty())
{
    it = connectionAnnounced_.erase(it);
    continue;
}
```

**⇒ 十六层**：
```text
1. **在名册查找【之前**】占位**
2. ⇒ **⇒ 所以【一个名字不能编码的槽【不会被每帧重试**】】**
3. ⇒ **名字【下面填**】
4. ⇒ **而【一个仍然持空串的槽【不会被宣告为离开**】】**
5. ⇒ **⇒ 所以【空串是【一个"已占位但未成功"的标记**】】**
6. ⇒ **⇒ 而【它在离开**】时被【erase 而【不宣告**】】**
```

**✅ ⭐⭐⭐ **"空串是一个已占位但未成功的标记"** —— 一个**三态的字符串用法**。

**✅ 与 §418 的"`initialized = (tag != 0) || !emptyTag`"**同族（**第三次"三态"）。

**⇒ 三层**：
```text
§413  `livingWeaponRightTagInitialized_` **三态**
§418  **`initialized` 的两种失败**
§432  **空串 = 已占位未成功**
⇒ **⇒ 三次"三态标记**】
```

**✅ ⭐⭐ **一个"三态"的三例表**。

**⚠ 而"`insert_or_assign` 的"⇒ **一个 `unordered_map` 而不是 `set`**。**

**⇒ 三层**：
```text
旧：**一个 `set`**（**只有"已宣告"**）
新：**`unordered_map<clientNum, string>`**（**加一个"名字**）
⇒ **⇒ 所以【现在还知道【那个名字**】以便发 `e` 命令**】
```

**✅ ⭐⭐ **"从 set 到 map 的理由"** —— 因为 `e` 需要名字。

**✅ 与 §409 的"候选-提交模式"**不同（这是**一个数据结构的升级**）。

## 四、**`publishZmRoundHud` 的"门是一个性质而不是一个计时器"**（本组第三重要）

### 4.1 那段

```php
// THE ZM ROUND HUD, ON A LATER TICK (12.132).
//
// 12.131 sent these four dvars inside the `gameStateUpdateStage == 6` branch
// -- the frame the client turns Active -- and the client stalled at
// "waiting for connection". `queueReliableCommand` refuses once
// `reliableSequence - reliableAcknowledge >= ServerReliableCommandCapacity`,
// and at enter-world the client has acknowledged NOTHING, so four commands
// pushed into that window is exactly where the reliable stream desyncs.
//
// Retail's own timing said so and 12.131 did not read it: the gamestate goes
// out at 10950 and `s ui_hud_round "1"` at 20250 -- NINE SECONDS LATER, not
// at enter-world.
//
// So the gate here is the property that actually matters, not a timer:
// the client must have acknowledged EVERYTHING already queued
// (`reliableAcknowledge == reliableSequence`), which means the queue is empty
// and the client is settled. A frame delay is layered on top so this cannot
// fire in the transition frame even if the counters momentarily agree.
```

### 4.2 二十四层

```text
1. **zm 回合 HUD，在【一个更晚的 tick 上**】（`12.132`）**
2. ⇒ **`12.131` 把这四个 dvar 放进【`gameStateUpdateStage == 6` 的分支**】**
3. ⇒ **（那个客户端变 `Active` 的帧）**
4. ⇒ **⇒ 而客户端【卡在"等待连接"**】**
5. ⇒ **`queueReliableCommand` 【在 `pending >= capacity` 时拒绝**】**
6. ⇒ **⇒ 而在进入世界时客户端【什么都没确认**】**
7. ⇒ **⇒ 所以【四条命令【推进那个窗口**】正是【可靠流【失同步**】的地方**】
8. ⇒ **❗ 零售自己的时序【早就说了**】而 `12.131` 【没有读它**】**
9. ⇒ **gamestate 在 `10950` 发出**
10. ⇒ **而 `s ui_hud_round "1"` 在 `20250`** ⇒ **【九秒之后**】**
11. ⇒ **⇒ 【不是进入世界时**】**
12. ⇒ **⇒ 所以这里的门【是那个真正重要的**性质**，不是一个计时器**】**
13. ⇒ **客户端【必须已经确认了每一个已排队的**】（`reliableAcknowledge == reliableSequence`）**
14. ⇒ **⇒ 那意味着【队列空**且客户端【已稳定**】**
15. ⇒ **⇒ 而【一个帧延迟【叠在上面**】**
16. ⇒ **⇒ 所以【这【不能在过渡帧**】触发，即使计数器【 momentarily 一致**】**
```

### 4.3 ⭐⭐⭐ **"门是一个性质而不是一个计时器"**

**✅ 与 §418 的"重复到 `baseline != nullptr` 这个协议内的信号出现，然后停"**、§429 的"活跃性规则不需要一个计时器"**完全同族（**第三次"用性质而不是计时器"）。

**⇒ 三层**：
```text
§418  **`0x02` 重复到有 baseline**
§429  **`selectBaseline` 失败驱动活跃性**
§432  **`reliableAcknowledge == reliableSequence`**
⇒ **⇒ 三次"用性质**】
```

**✅ ⭐⭐⭐ **一个"用性质"的三例表**。

**⚠ 而"零售自己的时序早就说了而 `12.131` 没有读它"⇒ **一个明确的"没读证据"的自我批评**。**

**✅ 与 §404 的"我上一刀把 dm 的 `16/14` 用到 cha，方向错了"**同族（**第八次"自我更正"）。

**⇒ 三层**：
```text
`10950` ⇒ **gamestate**
`20250` ⇒ **`s ui_hud_round "1"`**
⇒ **⇒ 差 `9300ms` = `9.3` 秒**（而注释说"九秒**"）✓
```

**✅ ⭐ **一个时间差的算术验证**。</br>

**✅ 而"`200` 帧 @ `20Hz` = `10` 秒"⇒ **`200 / 20 = 10**` ✓

**⇒ 三层**：
```text
`settleFrames = 200`
`20 Hz` 快照率 ⇒ **`200 / 20 = 10` 秒**
⇒ **⇒ 而零售的间隔是 `9.3` 秒** ⇒ **所以 `10` 秒是【一个地板，不是一个日程**】
```

**✅ ⭐⭐ **"一个地板不是一个日程"** —— 与 §419 的"`N-1` vs 乘数"**同族（**第二次"一个下界而不是一个常量"）。

## 五、**`bestClientKills` 的平局判据**（本组第四重要）

### 5.1 那段

```cpp
std::optional<std::pair<std::uint32_t, std::int32_t>> best;
std::int32_t bestDeaths{};
for (...) {
    if (clients_[index].state == ClientState::Free) continue;
    const auto score = clientScores_[index].kills;
    const auto deaths = clientScores_[index].deaths;
    if (!best || score > best->second || (score == best->second && deaths < bestDeaths))
    {
        best = { index, score };
        bestDeaths = deaths;
    }
}
```

**⇒ 十层**：
```text
1. **按【击杀数降序**】**
2. ⇒ **平局 ⇒ 【死亡数升序**】**
3. ⇒ **⇒ 所以【一个杀得多而死得少的赢**】**
4. ⇒ **而 `bestDeaths` 【只在替换时更新**】**
5. ⇒ **⇒ 所以【它是【当前最佳的那个的死亡数**】】**
```

### 5.2 ⭐⭐⭐ **"`bestDeaths` 只在替换时更新"**

**✅ 与 §409 的"`announcer_.leader = leaderKey` 在冷却检查**之前**"**不同（这是**一个滚动的最佳**）。

**⇒ 三层**：
```text
`best` 与 `bestDeaths` **必须同步更新**
⇒ **⇒ 所以【两者在同一个 `if` 体内**】**
```

**✅ ⭐ **一个"状态配对"的实例**。

**⚠ 而"`SvClientSystem::topClientsByKills` 用 `stable_sort` 保留下标"⇒ **同 §432 五 的排序一致性**。**

**⇒ 三层**：
```text
`bestClientKills` ⇒ **手工遍历，`score > best` 或 `(== && deaths <)`**
`topClientsByKills` ⇒ **`stable_sort`，`score >` 或 `deaths <`**
⇒ **⇒ 两个【同一个判据**】
```

**✅ ⭐⭐ **"两个函数同一个判据"** —— 与 §409 的"`scoreBefore`/`scoreAfter` 两两互校"**同族（**第五次"单一真相源"）。

**⚠ 而"`stable_sort` 保留较低的下标"⇒ **一个明确的平局规则**。**

**⇒ 三层**：
```text
`stable_sort` ⇒ **相等元素【保持原序**】
原序 ⇒ **index 升序** ⇒ **较低下标在前**
⇒ **⇒ 所以【一个稳定的平局判据**】
```

**✅ ⭐ **一个"稳定排序作为平局规则"的实例**。

**✅ 与 §406 的"`bestClientKills` 在 0-0 时返回最低占用槽"**完全闭合 ✓

**⇒ 三层**：
```text
§406  **0-0 时返回最低占用槽** ⇒ 所以需要 `<= 0` 守卫
§432  **`stable_sort` 保留下标** ⇒ 所以 0-0 时【也是最低的**
⇒ **⇒ 两处同一个行为**
```

**✅ ⭐⭐⭐ **一个跨报告的行为闭合**。

## 六、`addClientXp` 的上界不同

```cpp
clientScores_[clientNum].xp = static_cast<std::int32_t>(
    std::clamp<std::int64_t>(xp, 0, std::numeric_limits<std::int32_t>::max()));
```

**⇒ 四层**：
```text
九个计分字段 ⇒ **`clamp(0, 1'000'000)`**
`xp` ⇒ **`clamp(0, INT32_MAX)`**
⇒ **⇒ 所以【`xp` 的上界【不同**】**
```

**✅ 与 §430 的"`awardedXp` 的 `min(bonus, INT32_MAX)`"**配合。

**⇒ 三层**：
```text
§413  `awardedXp = min(bonus, INT32_MAX)`
§432  `xp` 的 `clamp(0, INT32_MAX)`
⇒ **⇒ 所以【`xp` 允许到 `21` 亿**】
```

**✅ ⭐ **一个"上界的差异"**。</br>

**⚠ 而"为什么 `xp` 不同"⇒ **可能因为它是一个累积的长期值**。**

**✅ 一个**可推导的理由**（标注）。

## 七、关键结论

1. **⭐⭐⭐ "实测 `269` 条 `MP_CONNECTED` 无一例外：紧跟名字的是 `15 FE <base64首字符>`"**，而 **`0x15`（`21`）不是长度（两条名字是 `15` 与 `18` 字节）** ⇒ **"按零售照抄恒定 tag，不猜语义"`** —— 第三次"范围否证假设"（与 §413/§417 同族），第七次"不要发明"。
2. **⭐⭐⭐ "此前记的『逐要素一致』漏了这 1 字节，而客户端把它当参数解析的一部分 ⇒ 屏上显示成 `MP_CONNECT?` + 名字"`** —— 第七次"一个测量的定义决定了它的盲区"（与 §411 的"合并的计时窗口"同族）。
3. **⭐⭐ "`17` 份 demo、`269` 条、零例外"** ⇒ 一个强结论 —— 第三次"例外计数"（与 §414 的 `238/238`、§424 的 `16/17` 同族）。
4. **⭐ 我复算了 `[15 FE 35]` × `162`**：base64 的 `'5'`（索引 `57`）⇒ **`57 << 2 = 228 = 0xE4`** ⇒ **正是 UTF-8 三字节中文的首字节** ⇒ 与"小虎他爹998"这个中文名吻合。
5. **⭐⭐⭐ `e` 与 `f` 到达【同一个 sink `0x0044D170`】⇒ 它们是【一条特性的两半】，而这棵树一直只发了一半** —— 与 §407 的"`RELOAD_START` 不是 `RELOAD`"形成对照：**`sink` 相同 ⇒ 两个都要；`sink` 不同 ⇒ 选合适的那个**。
6. **⭐ "`TimeoutDrop::Cause` 数据【已经有了】（§426 的 `dropClientSlot` 传它），只是 `announceConnectionChanges` 没读它"** ⇒ 第三次"最后一公里"（与 §413、§416 同族）。
7. **⭐⭐⭐ "在名册查找之前占位 ⇒ 一个名字不能编码的槽不会被每帧重试，而一个仍然持空串的槽不会被宣告为离开"`** ⇒ **空串是一个"已占位但未成功"的标记** —— 第三次"三态"（与 §413/§418 同族）。
8. **⭐ 从 `set` 到 `unordered_map<clientNum, string>` 的升级，因为 `e` 命令需要那个名字**。
9. **⭐⭐⭐ "这里的门是那个真正重要的【性质】而不是一个计时器：客户端必须已经确认了每一个已排队的（`reliableAcknowledge == reliableSequence`）⇒ 队列空且客户端已稳定"`** —— 第三次"用性质而不是计时器"（与 §418、§429 同族）。
10. **⭐⭐ "零售自己的时序早就说了而 `12.131` 没有读它：gamestate 在 `10950` 发出而 `s ui_hud_round "1"` 在 `20250` —— 九秒之后"`** —— `9300ms` 的算术验证；第八次"自我更正"。
11. **⭐ `settleFrames = 200` @ `20Hz` = `10` 秒** ⇒ **"一个地板，不是一个日程"**（零售的本机是 `9.3` 秒）—— 第二次"一个下界而不是一个常量"（与 §419 同族）。
12. **⭐⭐ `bestClientKills` 与 `topClientsByKills` 用【同一个判据】**（击杀降序、死亡升序），而 **`stable_sort` 保留较低的下标 ⇒ 0-0 时返回最低占用槽** ⇒ **与 §406 的"需要 `<= 0` 守卫"完全闭合**。
13. **⭐ `addClientXp` 的上界是 `INT32_MAX` 而其余九个是 `1'000'000`**（`xp` 是一个累积的长期值）。

## 八、未闭合点

- `0x15` 的真实语义（它是恒定的，但未知）。
- `e` 命令在 `17` 份 demo 里的出现频次。
- `EXE_TIMEDOUT` / `EXE_PLAYERKICKED_BOT_BALANCE` 的确切使用场景。
- `0x0044D170` 这个 sink 的能力（它同时处理 `e` 与 `f`）。
- `settleFrames = 200` 与零售 `9.3` 秒的关系。
- `sv_client_mp.cpp` 2810 行之后未读取（**共 `4500` 行**）。
