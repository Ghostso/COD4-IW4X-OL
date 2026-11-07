# 431 · **"一个裸字面量是三条已记录的隐藏方式之一"** —— `0x3FC` 与 `0x404`/`0x3FF` 的两字节差、`181` 是槽不对齐而不是广播有害、以及九个计分字段的统一 `1000000` 上界

## 一、范围

本报告学习 `sv_client_mp.cpp` 2130–2480 行（`queueReliableBinaryCommand` 的边界、`registerDynamicWeaponConfigString` 的广播、`beginNextRound` 的换边、九个计分累加器）。

## 二、**"一个裸字面量，另一种拼写"**（本组最重要的一段）

### 2.1 那段

```php
// THE SAME BOUND AS SvProfilePatchMaximumPayload, and it used to be a second copy
// spelled 0x3FC right here. A bare literal in a comparison is one of the three
// documented ways a carried constant hides from every auditor in this tree: it is
// not a constexpr, so audit-carried-constants cannot see it, and
// audit-duplicate-constants is blind to a name with only one declaration site.
//
// OLMOD(section-85): CONFIRMED SAFE ON out.exe, and it is not the engine's
// number at all -- it is a cap two bytes under the engine's real ceiling. The
// client's store reads at most `push 400h` into a 0x404 frame and keeps at most
// `push 3FFh` characters, identically on both builds (sub_46E3B0 / sub_4737E0),
// so `verb + payload` may be 1023 and the payload 0x3FE.
```

### 2.2 二十四层

```text
1. **与 `SvProfilePatchMaximumPayload` 同一个界**
2. ⇒ **而它【过去是这里一个拼作 `0x3FC` 的第二份拷贝**】**
3. ⇒ **⇒ 一个在比较里的裸字面量【是【三条已记录的方式**】之一**
4. ⇒ **⇒ 一个被携带的常数【从这棵树里的每一个审计器那里【藏起来**】】**
5. ⇒ **① 它【不是一个 `constexpr`**】**
6. ⇒ **⇒ 所以 `audit-carried-constants` 【看不见它**】**
7. ⇒ **② 而 `audit-duplicate-constants` 【对一个只有一个声明点的名字【是盲的**】】**
8. ⇒ **⇒ 所以【两条审计都漏**】】
9. ⇒ **⚠ 而它在 `out.exe` 上【确认安全**】**
10. ⇒ **⇒ 而它【根本不是引擎的数字**】**
11. ⇒ **⇒ 它是【引擎真实上限【之下的两个字节**】的一个帽子**
12. ⇒ **客户端的 store 【最多读 `push 400h`**】进一个 `0x404` 帧**】
13. ⇒ **⇒ 而【最多保留 `push 3FFh` 个字符**】**
14. ⇒ **⇒ 在两个 build 上【完全相同**】（`sub_46E3B0` / `sub_4737E0`）**
15. ⇒ **⇒ 所以 `verb + payload` 【可以是 `1023`**】**
16. ⇒ **⇒ 而【payload 是 `0x3FE`**】**
```

### 2.3 ⭐⭐⭐ **"三条已记录的方式让一个被携带的常数藏起来"**

**✅ 这是本报告里**最重要的一条"常数审计的盲区"**。**

**⇒ 三层**：
```text
方式 ①：**裸字面量**（不是 `constexpr`）⇒ `audit-carried-constants` 看不见
方式 ②：**只有一个声明点的名字** ⇒ `audit-duplicate-constants` 是盲的
方式 ③：**（未在本段列出）**
⇒ **⇒ 所以【两条审计各自有一个盲区，而一个常数可以同时落入两个**】
```

**✅ 与 §418 的"`audit-wire-zero-baseline.py`"**、§411 的"`check_perframe_cost.py`"**同族（**第四次"规则的可执行化"，但这里**是审计的盲区**）。

**⇒ 三层**：
```text
§418  **一个规则配一个审计脚本**
§430  **而审计脚本有盲区**
⇒ **⇒ 所以【规则可执行化，但执行器本身有限**】
```

**✅ ⭐⭐⭐ **一个"审计的边界"的实例**。

**⚠ 而"三条"里的第三条**⇒ **未在本段给出**（可能是"拼写不同但语义相同"）。

**✅ 一个**未闭合点**。

### 2.4 而**"`0x3FC` → `0x3FE` 的两字节差"**

**⇒ 让我核对**：

```text
`push 400h` ⇒ **`1024`**（帧大小）
`push 3FFh` ⇒ **`1023`**（字符数）
⇒ `verb + payload <= 1023`
⇒ 若 `verb` 是 1 个字符（如 `%`）⇒ **payload <= 1022 = 0x3FE** ✓
```

**✅ ⭐⭐ **一个"两字节"的完整推导**（`1023 - 1 = 1022 = 0x3FE`）。

**⚠ 而 `0x3FC = 1020`** ⇒ **差 `2`** —— 所以注释说"两个字节**" ✓

**⇒ 三层**：
```text
`0x3FC` = `1020`（**旧的裸字面量**）
`0x3FE` = `1022`（**真实的界**）
⇒ **⇒ 差 `2`** ⇒ **而注释说"under the engine's real ceiling" 是 `2`** ✓
```

**✅ ⭐ **一个数字闭合。

**⚠ 而"`0x404` 帧"⇒ **`1028`** ≠ `1024`。**

**⇒ 三层**：
```text
`push 400h` ⇒ **`1024`**（读的上限）
`0x404` ⇒ **`1028`**（帧大小）
⇒ **⇒ 差 `4`** ⇒ **可能是【一个头**】
```

**✅ 一个**可推导的结构**。

## 三、**`181` 是槽不对齐而不是广播有害**（本组第二重要）

### 3.1 那段

```php
// APPEND into the gamestate's dynamic block, then BROADCAST the new
// weapon to every connected client -- the retail behaviour, seamless.
// The '%' write only trips out.exe's 181 index-vs-slot check
// ([[codol-181-is-weapon-index-vs-slot]]) when the weapon's slot does
// NOT equal the client's monotonic registration counter. That is a
// GAMESTATE-ALIGNMENT problem, not a reason to avoid broadcasting: the
// strip in refreshMemberLoadout (§161a) used to desync the count by one,
// so the broadcast landed on the wrong slot. With the strip gone the
// appended block is byte-identical to what SessionStart builds, so the
// slot equals every client's next-free counter and the broadcast lands
// clean -- and each client HAS the weapon before it renders another
// player holding it, so no render crash either. NEW ONLY BROADCASTS:
// SV_RegisterModularWeaponConfigString returns the existing index for a
// duplicate without growing the table, so a weapon everyone already has
// is not re-pushed.
```

### 3.2 二十四层

```text
1. **追加**进 gamestate 的动态块，**然后【广播**】那把新武器给每一个已连接客户端**
2. ⇒ **⇒ 零售行为，无缝**
3. ⇒ **那个 `%` 写【只在**】武器的槽【不等于**】客户端的【单调注册计数器**】时触发 `out.exe` 的 `181` 索引-vs-槽检查**】
4. ⇒ **⇒ 那是一个【GAMESTATE 对齐**】问题**
5. ⇒ **⇒ 而不是【一个避免广播的理由**】**
6. ⇒ **⚠ `refreshMemberLoadout`（`§161a`）里的 strip 过去【让计数【差一**】】**
7. ⇒ **⇒ 所以广播【落在错误的槽上**】**
8. ⇒ **⇒ 而【strip 去掉之后**，追加的块【与 `SessionStart` 构建的【逐字节相同**】】**
9. ⇒ **⇒ 所以【槽等于每一个客户端的下一个空闲计数器**】**
10. ⇒ **⇒ 而【广播落在干净的地方**】**
11. ⇒ **⇒ 而【每个客户端在它【渲染另一个玩家持有它之前**】就【有了那把武器**】】**
12. ⇒ **⇒ 所以【也没有渲染崩溃**】**
13. ⇒ **⚠ 只有新的才广播**：**`SV_RegisterModularWeaponConfigString` 对一个重复【返回已存在的索引**】而【不增长表**】**
14. ⇒ **⇒ 所以【一个所有人都有的武器【不会被重推**】】**
```

### 3.3 ⭐⭐⭐ **"那是一个 GAMESTATE 对齐问题，而不是一个避免广播的理由"**

**✅ 这是本报告里**最重要的一次"症状的根因定位**。**

**⇒ 三层**：
```text
症状：**`181` 错误**
错误归因：**广播有害** ⇒ **因此不广播**
真因：**槽不对齐**（因为 strip 让计数差一）
⇒ **⇒ 所以【正确做法是【修 strip**】而不是【停止广播**】】
```

**✅ 与 §413 的"`missing_playerstate` 命名了错误的嫌疑"**完全同族（**第六次"症状的位置与根因的位置无关"）。

**⇒ 三层**：
```text
§413  `missing_playerstate`（**下游两层**）⇒ 真因是 `BG_UpdatePlayerDObj` 的 AV
§431  `181` ⇒ 真因是 **strip 让计数差一**
⇒ **⇒ 两次"症状命名了错误的嫌疑**】
```

**✅ ⭐⭐⭐ **一个"错误归因"的两例**。

**⚠ 而"`[[codol-181-is-weapon-index-vs-slot]]`"⇒ **一个 wiki 链接**（**项目内部的笔记引用**）。

**✅ ⭐ **一个"知识库引用"的实例**。

**⚠ 而"`byte-identical` 到 `SessionStart`"⇒ **一个可验证的等价**。**

**⇒ 三层**：
```text
`SessionStart` 构建的块 ⇒ **权威**
`registerDynamicWeaponConfigString` 追加的 ⇒ **必须【逐字节相同**】
⇒ **⇒ 所以【两条路径产生同一形状 ⇒ 客户端无法区分**】
```

**✅ ⭐⭐ **"两条路径同一形状"** —— 与 §414 的"两条独立路径一致"**同族（**第四次）。

**⚠ 而"每个客户端在它渲染另一个玩家持有它之前就有了那把武器"⇒ **一个顺序保证**。**

**✅ 与 §422 的"授予先于拾取"**同族（**第六次"顺序保证**）。

**⇒ 三层**：
```text
§422  "**授予先走，箱子只在它成功后才死**"
§431  **武器注册先于渲染**
⇒ **⇒ 两次"先给予再展示**】
```

**✅ ⭐ **一个"顺序保证"的两例**。

## 四、**`beginNextRound` 的换边与三个同步**（本组第三重要）

### 4.1 那段

```php
if (switchTeams)
{
    client.team = client.team == SvTeam::Tf ? SvTeam::Sc : SvTeam::Tf;
    client.characterFaction = client.team == SvTeam::Tf
        ? SvCharacterFaction::Tf : SvCharacterFaction::Sc;
    // A class response may already be pending when SD swaps sides.
    // Keep that pending transaction aligned with the authoritative
    // committed team; otherwise the next commit re-applies the old
    // side and clientInfo/scoreboard diverge from damage ownership.
    client.pendingTeam = client.team;
    client.pendingCharacterFaction = client.characterFaction;
}
++client.spawnSequence;
if (!client.spawnSequence) ++client.spawnSequence;
```

### 4.2 二十层

```text
1. **`team` 翻转**
2. ⇒ **`characterFaction` 【跟随** `team`】（**§411 的"faction 匹配 team"**）
3. ⇒ **⚠ 而一个职业响应【可能已经挂起**】**
4. ⇒ **⇒ 所以【那个挂起的事务【必须与权威的已提交队伍【对齐**】】**
5. ⇒ **⇒ 否则【下一次提交【重新应用旧的一边**】】**
6. ⇒ **⇒ 而 `clientInfo` / 计分板【从伤害归属【分歧**】】**
7. ⇒ **`pendingTeam = team`**
8. ⇒ **`pendingCharacterFaction = characterFaction`**
9. ⇒ **`++spawnSequence`**
10. ⇒ **`if (!spawnSequence) ++spawnSequence`** ⇒ **跳过 `0`**
```

### 4.3 ⭐⭐⭐ **"那个挂起的事务必须与权威的已提交队伍对齐，否则下一次提交重新应用旧的一边"**

**✅ 这是本报告里**最重要的一条"挂起事务的对齐**。**

**✅ 与 §426 的"重放不改阵营"**——**互补** ✓

**⇒ 三层**：
```text
§426  **一个重放的菜单【不改阵营**】（**因为它是重放**）
§431  **而一个换边【必须改挂起的 `pendingTeam`**】（**因为它是权威变更**）
⇒ **⇒ 两个相反的处置，同一个字段**
```

**✅ ⭐⭐⭐ **一个"同一个字段的两个处置"**。

**⚠ 而"跳过 `0`"⇒ **`spawnSequence` 从 `0` 开始 ⇒ `++` 到 `1`**。**

**⇒ 三层**：
```text
`spawnSequence` 初始 `0`
`++` ⇒ `1`
⇒ **而 `if (!spawnSequence)` 【永远不触发**】（因为 `0 + 1 = 1`）
```

**⚠ 一个**死代码**（`if (!spawnSequence)` 在 `++spawnSequence` 之后**永不成立**，除非溢出）。

**⇒ 三层**：
```text
若 `spawnSequence == UINT32_MAX` ⇒ `++` 溢出到 `0` ⇒ **`if` 触发 ⇒ `++` 到 `1`**
⇒ **⇒ 所以【它是【防溢出的**】】
```

**✅ ⭐⭐ **一个"防溢出"的实例**（`uint32` 的 `4.29e9` 次重生）。

**✅ 与 §417 的"代次 `0` 是一个有效的第一命"**不同（这是**一个溢出保护**）。

### 4.4 而**"一个 `169` 的重置被删除了"**

```php
// (Section 169: the per-spawn clientInfo re-assertion that used to sit here
// is deleted. `req{ALL-ZERO} valid=1 rebuild=1` was never a LOST clientInfo,
// so re-sending could not have cured it -- the observer received the bytes
// and decoded them against a baseline the message was not written with, and
// a re-assertion against a section-local empty baseline is another instance
// of that same defect rather than a retry for it.)
```

**⇒ 十六层**：
```text
1. **每个出生的 `clientInfo` 重新断言【被删除**】**
2. ⇒ **`req{ALL-ZERO} valid=1 rebuild=1` 【从来不是一个【丢失的**】 `clientInfo`**
3. ⇒ **⇒ 所以【重发【不可能**】治好它**】
4. ⇒ **观察者【收到了那些字节**】**
5. ⇒ **而【对一个【消息【不是**】用它写的基准**】解码它们**】
6. ⇒ **⇒ 而【一个对【节内局部空基准**】的重新断言【是【同一个缺陷的另一个实例**】】**
7. ⇒ **而不是【为它的一次重试**】**
```

### 4.5 ⭐⭐⭐ **"一个重新断言是同一个缺陷的另一个实例，而不是为它的一次重试"**

**✅ 这是本报告里**最重要的一条"治愈 vs 重演**。**

**✅ 与 §427 的"那个重新断言被删除了，而它的工作由进入世界的重置完成"**——**完全同源** ✓

**⇒ 三层**：
```text
§427  **重新断言【单独重发一节对空基准**】= 那个缺陷本身**
§431  **"同一个缺陷的另一个实例而不是为它的一次重试"**
⇒ **⇒ 两次同一个结论**
```

**✅ ⭐⭐⭐ **一个跨报告的同一结论**。

**⇒ 而"`req{ALL-ZERO} valid=1 rebuild=1`"是 §426 的那个观察** ✓

**⇒ 三次闭合**：
```text
§426  **观察：`req{ALL-ZERO} valid=1 rebuild=1 model=EMPTY`**
§427  **修法：`deltaMessage = -1` 的清 + `SnapshotBaselineFlag`**
§431  **并删除"重新断言"因为它是同一个缺陷的另一个实例**
⇒ **⇒ 三处完整**
```

**✅ ⭐⭐⭐ **一个三报告闭合的完整因果链**。

## 五、**九个计分累加器的统一模式**（本组第四重要）

### 5.1 九个

```text
addClientScore       score
addClientKills       kills
addClientDeaths      deaths       ← 唯一会重置 killstreak 的
addClientAssists     assists      ← 明确"不重置 killstreak"
addClientObjectives  objectives   ← 明确"不重置 killstreak"
addClientGp          gp           ← 明确"不重置且不影响 xp"
addClientStreak      killstreak
addClientDowns       downs
addClientRevives     revives
addClientHeadshots   headshots
```

**⇒ 十个。**

### 5.2 统一的四步

```cpp
① if (clientNum >= clients_.size() || clients_[clientNum].state == ClientState::Free) return false;
② const auto v = static_cast<std::int64_t>(clientScores_[clientNum].X) + delta;
③ clientScores_[clientNum].X = static_cast<std::int32_t>(std::clamp<std::int64_t>(v, 0, 1'000'000));
④ scoreboardDirty_ = true;
```

**⇒ 六层**：
```text
① **越界 + Free 检查**
② **`int64` 中间量**（**防溢出**）
③ **夹到 `0..1'000'000`**
④ **置 `scoreboardDirty_`**
⇒ **⇒ 四步，十个函数完全相同**
```

### 5.3 ⭐⭐ **"`int64` 中间量 + 夹到 `0..1000000`"**

**✅ 与 §409 的"`int64` 中间量 + 显式溢出检查"**同族（**第三次"整数宽度的防护**）。

**⇒ 三层**：
```text
§409  `rawCost64` 的 `int64` + `> UINT32_MAX ⇒ return`
§419  `healthAtDamage` 的 `uint32` 匹配
§431  **`int64` + `clamp(0, 1000000)`**
⇒ **⇒ 三次"整数宽度的防护**】
```

**✅ ⭐ **一个"整数防护"的三例表**。

**⚠ 而"`1'000'000`"⇒ **一个统一的业务上界**。**

**⇒ 三层**：
```text
若没有上界 ⇒ **一个 `int32` 溢出** ⇒ **负值**
⇒ **而 clamp 到 `0`** ⇒ **一个"归零"的显示**
⇒ **⇒ 所以【上界防止【溢出**】】
```

**✅ ⭐⭐ **一个"统一上界"的实例**。

### 5.4 而**"只有 `addClientDeaths` 重置 `killstreak`"**

```php
if (delta > 0)
    clientScores_[clientNum].killstreak = 0;
```

**⇒ 六层**：
```text
只有【死亡】**重置 `killstreak`**
⇒ **而【助攻/目标/GP 都明确说"不重置"**】**
⇒ **⇒ 理由分别在注释里**：
      · **助攻**："一个助攻【不是一次死亡**，而收件人可能是【还活着**的那个"
      · **目标**："完成一个目标【不是死亡**"
      · **GP**："两列收入是【独立的计数器**恰好一起被授予"
```

### 5.5 ⭐⭐⭐ **"`delta > 0` 才重置"**

**⇒ 三层**：
```text
若 `delta < 0`（**一个减法**）⇒ **不重置**
⇒ **⇒ 所以【一个"复活"或"撤销死亡"不会清连杀**】
```

**✅ 与 §409 的"`deltaRaw` 可以是负的（退款）"**配合。

**✅ ⭐⭐ **一个"增量符号决定副作用"的实例**。

**⚠ 而"九个函数各自有一份相同代码"⇒ **重复**。**

**⇒ 三层**：
```text
十个函数，四步相同
⇒ **⇒ 可以【抽成一个模板**】
⇒ **而【没抽**】 ⇒ **一个"三行重复优于一个过早抽象"的例子**
```

**✅ 与项目指令的"三个相似的行比一个过早的抽象好"**完全一致 ✓

## 六、`registerDynamicWeaponConfigString` 的"只有新的才广播"

```cpp
const auto before = gameState_.modularWeaponConfigStrings.size();
const auto assetIndex = SV_RegisterModularWeaponConfigString(gameState_, firstDynamicWeaponAssetIndex, std::move(configString));
if (!assetIndex) return std::nullopt;
if (buildCommand && gameState_.modularWeaponConfigStrings.size() != before)
{
    ... 广播 ...
}
```

**⇒ 八层**：
```text
1. **记 `before` 的大小**
2. ⇒ **注册**（**可能返回已存在的索引**）
3. ⇒ **只有【大小变了**】才广播**
4. ⇒ **⇒ 所以【`SV_RegisterModularWeaponConfigString` 对一个重复【返回已存在的**】而不增长**
5. ⇒ **⇒ 所以 `size() != before` 是【"这是一个新的"判据**】**
6. ⇒ **⇒ 而 `buildCommand` 可选**（**没有它就不广播**）
```

**✅ ⭐⭐ **"大小变化 = 新增判断**"** —— 一个**极简洁的幂等实现**。

**✅ 与 §418 的"`initialized` 三态"**同族（**第六次"幂等"）。

## 七、关键结论

1. **⭐⭐⭐ "一个在比较里的裸字面量【是三条已记录的方式】之一，让一个被携带的常数【从这棵树里的每一个审计器那里藏起来】"**：**① 它不是 `constexpr` ⇒ `audit-carried-constants` 看不见；② `audit-duplicate-constants` 对一个只有一个声明点的名字是盲的** ⇒ **两条审计都漏**。
2. **⭐⭐ "`0x3FC`（`1020`）→ `0x3FE`（`1022`）的 `2` 字节差"** 完整推导：**`push 400h`（`1024`）是读的上限、`push 3FFh`（`1023`）是字符数上限 ⇒ `verb（1）+ payload（1022）<= 1023`**；而 **`0x404`（`1028`）是帧大小，差 `4`（可能一个头）**。
3. **⭐⭐⭐ "那个 `%` 写只在武器的槽不等于客户端的单调注册计数器时才触发 `181` —— 那是一个 GAMESTATE 对齐问题，而不是一个避免广播的理由"`** —— 第六次"症状的位置与根因的位置无关"（与 §413 的 `missing_playerstate` 同族）。
4. **⭐ 知识库引用 `[[codol-181-is-weapon-index-vs-slot]]`**（一个项目内部的 wiki 链接）。
5. **⭐⭐ "`refreshMemberLoadout` 里的 strip 过去让计数差一 ⇒ 广播落在错误的槽上；strip 去掉之后追加的块与 `SessionStart` 构建的【逐字节相同】⇒ 槽等于每一个客户端的下一个空闲计数器 ⇒ 广播落在干净的地方"`** —— 一个可验证的等价（两条路径同一形状）。
6. **⭐⭐ "每个客户端在它渲染另一个玩家持有它之前就【有了那把武器】，所以也没有渲染崩溃"`** —— 第二次"先给予再展示"（与 §422 同族）。
7. **⭐ "只有新的才广播：`SV_RegisterModularWeaponConfigString` 对一个重复返回已存在的索引而不增长表"`** ⇒ **`size() != before` 是一个幂等判据** —— 第六次"幂等"。
8. **⭐⭐⭐ "一个职业响应可能在 SD 换边时已经挂起；那个挂起的事务必须与权威的已提交队伍对齐，否则下一次提交重新应用旧的一边，而 `clientInfo`/计分板从伤害归属分歧"`** —— 与 §426 的"重放不改阵营"**是同一字段的两个相反处置**。
9. **⭐ `if (!spawnSequence) ++spawnSequence` 是一个防溢出**（`uint32` 的 `4.29e9` 次重生后 `++` 到 `0` ⇒ 再 `++` 到 `1`）。
10. **⭐⭐⭐ "`req{ALL-ZERO} valid=1 rebuild=1` 从来不是一个【丢失的】 `clientInfo`，所以重发不可能治好它 —— 观察者收到了那些字节而对一个【消息不是用它写的】基准解码它们，而一个对【节内局部空基准】的重新断言是【同一个缺陷的另一个实例】，而不是为它的一次重试"`** —— 与 §427 完全同源；而 `req{ALL-ZERO}` 是 §426 的观察 ⇒ **三报告完整闭合**。
11. **⭐⭐ 九个计分累加器的统一四步**（越界+`Free` 检查 / `int64` 中间量 / 夹到 `0..1'000'000` / `scoreboardDirty_`）—— 第三次"整数宽度防护"。
12. **⭐⭐ "只有 `addClientDeaths` 重置 `killstreak`，而助攻/目标/GP 都明确说『不重置』，理由分别在注释里"`**，且 **`if (delta > 0)`** ⇒ **一个减法不重置连杀**。
13. **⭐ 十个几乎相同的函数没有抽成模板** —— 与项目指令的"三个相似的行比一个过早的抽象好"一致。

## 八、未闭合点

- "三条已记录的方式"里的第三条。
- `SvProfilePatchMaximumPayload` 的确切值（我推断 `0x3FE`）。
- `0x404` 帧的 `4` 字节头。
- `codol-181-is-weapon-index-vs-slot` 的完整记录。
- `refreshMemberLoadout` 的 strip（`§161a`）。
- `sv_client_mp.cpp` 2480 行之后未读取（**共 `4500` 行**）。
