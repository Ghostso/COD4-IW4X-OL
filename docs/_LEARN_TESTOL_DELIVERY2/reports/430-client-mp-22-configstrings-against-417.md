# 430 · **"我们自己的录制带 `22` 个 configstring 而零售是 `417`，且一条 `d` 命令都没有"** —— `SV_SetConfigString` 的六个带、`a <index>` 的空指针崩溃、以及 `drift` 的符号选择

## 一、范围

本报告学习 `sv_client_mp.cpp` 1790–2130 行（`SNAPSHOT BASELINE MISMATCH` 的两类、`clientPrediction`、`snapshotHistory` 的发布、`queueReliableCommand` 的 `a` 检查、`SV_SetConfigString` 的完整理由）。

## 二、**"我们的 `22` 对零售的 `417`"**（本组最重要的一段）

### 2.1 那段

```php
// MEASURED (C-2021-7-25[1-19-26]dm.demo, re/demo-re/12-dm-timeline.txt):
// a real free-for-all sends 123 distinct `d` records, 326 sends, from
// serverTime 0 to the last second of the match. They are NOT mostly
// player names. They are how a match acquires content it did not have
// when the gamestate was built:
//
//   3636..3678  sound aliases, pushed as each killstreak/weapon is
//               first used - `d 3648 mp_killstreak_carepackage` at 1:33
//   12254..12278 model bone/tag names, pushed as each vehicle or model
//               is first damaged - `d 12267 right_wheel_02_jnt` at 6:15
//   864..871    localized pickup strings
//   792..794    an attach record, `\ent\381\offs\0 0 0\mat\154\flags\0`
//   15, 464     the match clock and ui_timelimit, CLEARED at 9:48.7
//   11861       the end-of-match timescale ramp
//   2557        the vision set switched to `mp_cross_fire_tp` at 10:05.7
//
// Without this the gamestate is the only configstring this server can
// ever produce, which is why our own recordings carry 22 configstrings
// against retail's 417 and not one `d` command.
```

### 2.2 二十四层

```text
1. **一个真实的自由混战发【`123` 个不同的 `d` 记录，`326` 次发送**】**
2. ⇒ **从 `serverTime 0` 到比赛的【最后一秒**】**
3. ⇒ **⇒ 它们【不是大多数玩家名**】**
4. ⇒ **⇒ 它们是【一场比赛如何获得它在 gamestate 构建时【没有的内容**】】**
5. ⇒ **六个带**：
      · **`3636..3678`** ⇒ **音效别名**（**每个连杀/武器【首次使用时**】推送；`d 3648 mp_killstreak_carepackage` 在 `1:33`）
      · **`12254..12278`** ⇒ **模型骨/tag 名**（**每个载具/模型【首次受损时**】；`d 12267 right_wheel_02_jnt` 在 `6:15`）
      · **`864..871`** ⇒ **本地化拾取串**
      · **`792..794`** ⇒ **一个 attach 记录**（`\ent\381\offs\0 0 0\mat\154\flags\0`）
      · **`15`, `464`** ⇒ **比赛时钟与 `ui_timelimit`**，在 `9:48.7` 被【清空**】
      · **`11861`** ⇒ **比赛末的时间缩放斜坡**
      · **`2557`** ⇒ **调色在 `10:05.7` 切到 `mp_cross_fire_tp`**
6. ⇒ **⇒ 没有这个，gamestate 【是这个服务器【能产生的唯一 configstring**】】**
7. ⇒ **⇒ 那就是为什么【我们自己的录制带 `22` 个 configstring 而零售是 `417`，且【一条 `d` 命令都没有**】】**
```

### 2.3 ⭐⭐⭐ **"`22` 对 `417`，且一条 `d` 命令都没有"**

**✅ 这是本报告里**最重要的一条"量的差距**。**

**⇒ 三层**：
```text
我们：**`22` 个 configstring，零条 `d`**
零售：**`417` 个 configstring，`326` 条 `d`**
⇒ **⇒ 所以【`d` 通道【完全未使用**】】
```

**✅ 与 §402 的"`s 0201` 是零售每个模式都发而我们一个都不发"**同族（**第二次"一条命令的完全缺失"）。

**⇒ 三层**：
```text
§402  `s 0201` ⇒ **`0` 条**
§430  **`d` ⇒ `0` 条**
⇒ **⇒ 两次"一个通道完全未用**】
```

**✅ ⭐⭐⭐ **一个"通道未用"的两例**。

**⚠ 而"`417 - 22 = 395`"⇒ **`395` 个 configstring 的差**。**

**⇒ 三层**：
```text
若 gamestate 提供 `22`
而零售有 `417` ⇒ **`395` 个是【比赛期间加的**】
⇒ **⇒ 所以【`d` 通道占 `95%`**】
```

**✅ ⭐⭐ **"`95%` 的 configstring 是运行时加的"** —— 一个**极重要的比例**。

### 2.4 而**六个带的"何时"**

**⇒ 三层**：
```text
`3636..3678`（音效别名）⇒ **每个连杀/武器【首次使用时**】**
`12254..12278`（骨/tag 名）⇒ **每个载具/模型【首次受损时**】**
`864..871`（拾取串）⇒ **拾取时**
`792..794`（attach）⇒ **死亡时**（§407 的"每死一条 `d 792`"）
`15`/`464`（时钟）⇒ **开场 + 比赛末清空**
`11861`（时间缩放）⇒ **比赛末**
`2557`（调色）⇒ **开场 + 比赛末**
⇒ **⇒ 所以【六个带各有自己的【触发点**】】
```

**✅ ⭐⭐ **一个"带与触发点的映射**。

**✅ 与 §407 的"`d 792` 每死写两次"**完全闭合 ✓

**⇒ 三层**：
```text
§407  `\ent\<n>\offs\0 0 0\mat\-1\offmat\-1\flags\0` 与 `...\offmat\-1\mat\154\flags\0`
§430  **`\ent\381\offs\0 0 0\mat\154\flags\0`**
⇒ **⇒ 而 §430 的只有【一个 `mat 154`**】而 §407 的【两个**
```

**⚠ 一处**形态差异**（§407 的两次 vs §430 的一次）。

**⇒ 三层**：
```text
§407  **两次（`mat -1`/`offmat -1` 然后换位 `mat 154`）**
§430  **一次（`mat 154`，无 `offmat`）**
⇒ **⇒ 所以【§430 是【第二次**的那个形态】
```

**✅ ⭐ **一个"同一记录的两个形态"的澄清**。

### 2.5 而**`SV_SetConfigString` 的完整守卫链**

```cpp
if (!gameStateConfigured_) return 0;
if (index 在 PlayerName 带) { 必须与格式化后的玩家名一致，否则 return 0; }
const auto existing = gameState_.configStrings.find(index);
if (existing != end && existing->second == value) return 0;   // 未变 ⇒ 不发
const auto command = "d " + index + " " + value;
if (command.size() >= 1024) return 0;
gameState_.configStrings.insert_or_assign(index, value);
for (每个客户端) {
    if (Free || !gamestateMessageNum) continue;   // 还没收到 gamestate ⇒ 不发
    if (queueReliableCommand(clientNum, command)) ++queued;
}
```

**⇒ 十四层**：
```text
1. **没有 gamestate ⇒ 返回 `0`**
2. ⇒ **玩家名带 ⇒ 必须与【格式化后的**】一致** ⇒ 否则拒绝
3. ⇒ **⇒ 所以【玩家名不能通过 `SV_SetConfigString` 任意设置**】
4. ⇒ **值未变 ⇒ 返回 `0`**（**不发**）
5. ⇒ **过长 ⇒ 拒绝**
6. ⇒ **⇒ 先【更新 `gameState_.configStrings`**】**
7. ⇒ **然后【对每个已收到 gamestate 的客户端排队**】**
8. ⇒ **`!gamestateMessageNum` ⇒ 跳过**
9. ⇒ **⇒ 理由：`d` 会描述一个【客户端还没有表**】的 configstring**
10. ⇒ **⇒ 而那个值【已经在它即将收到的 gamestate 里**】】
```

### 2.6 ⭐⭐⭐ **"`d` 会描述一个客户端还没有表的 configstring，而那个值已经在它即将收到的 gamestate 里"**

**✅ 这是本报告里**最重要的一条"两个通道的冗余**。**

**⇒ 三层**：
```text
gamestate ⇒ **全量**
`d`      ⇒ **增量**
⇒ **⇒ 所以在 gamestate 之前发 `d` 是【纯浪费 + 可能有害**】
```

**✅ 与 §408 的"`d 2557` 而不是 `N`，所以中场休息期间加入的人也读到"**同族（**第二次"`d` 是全局状态**）。

**⇒ 三层**：
```text
§408  **`d 2557` 是全局** ⇒ 晚加入者自然读到
§430  **`d` 必须在 gamestate 之后** ⇒ 因为 gamestate 已经含它
⇒ **⇒ 两个约束，一个机制**
```

**✅ ⭐⭐ **一个"gamestate 与 `d` 的关系"的精确界定**。

**⚠ 而"`insert_or_assign` 在排队**之前**"⇒ **一个顺序**。**

**⇒ 三层**：
```text
先更新 `gameState_.configStrings`
⇒ **然后排队**
⇒ **⇒ 所以【即使排队失败，状态也已更新**】
```

**⚠ 一个**需要标注的行为**（**排队失败 ⇒ 客户端永远不知道**）。

**⇒ 三层**：
```text
若客户端在 gamestate 后【队列满**】⇒ `queueReliableCommand` 返回 `false`
⇒ **⇒ 而 `gameState_.configStrings` 已更新** ⇒ **下一次同值 ⇒ 返回 `0`** ⇒ **永不重试**】
```

**⚠ 一个**可能的静默丢失**（**标注**）。

## 三、**`a <index>` 的空指针崩溃**（本组第二重要）

### 3.1 那段

```php
// `a <index>` enters out.exe's CG_SelectWeapon path immediately.  A
// dynamic index that is not present in this gamestate's weapon block
// resolves to a null definition and crashes at out.exe+0x19B79B before
// the client can report a useful error.  Wetwork exposed this with the
// retail demo's `a 1198`: this live gamestate started its dynamic block
// at 1163 and registered only 1163..1168.
```

### 3.2 十八层

```text
1. **`a <index>` 【立即进入 `out.exe` 的 `CG_SelectWeapon` 路径**】**
2. ⇒ **一个【不在这个 gamestate 的武器块里**】的动态索引**
3. ⇒ **解析成【一个 null 定义**】**
4. ⇒ **⇒ 而在 `out.exe+0x19B79B` 崩溃**
5. ⇒ **⇒ 在客户端【能报告一个有用的错误之前**】**
6. ⇒ **Wetwork 用零售 demo 的 `a 1198` 暴露了它**
7. ⇒ **⇒ 因为【这个实机的 gamestate 把它的动态块【从 `1163` 开始**】】**
8. ⇒ **⇒ 而【只注册了 `1163..1168`**】**
```

### 3.3 ⭐⭐⭐ **"一个不在 gamestate 武器块里的动态索引解析成 null 定义，并在客户端能报告一个有用的错误之前崩溃"**

**✅ 这是本报告里**最重要的一条"`a` 的前提条件**。**

**✅ 与 §403 的"`a` 要求 cgame 画一把它必须已经拥有的武器"**完全同源 ✓

**⇒ 三层**：
```text
§403  **`a` 要求【在权威 playerState 里已拥有**】
§413  **`a` 的前提（`ownsActivationWeapon` 检查）**
§430  **`a` 还要求【那个索引在 gamestate 的武器块里**】
⇒ **⇒ 三个层次的前提**
```

**✅ ⭐⭐⭐ **一个"`a` 的三重前提"**。

**⚠ 而"`1163` vs `1147`/`1148`"⇒ **三处不同的数字**。**

**⇒ 三层**：
```text
§388  `firstDynamicWeapon = 1147`（`mp_battlecity`）
§413  `1148` 是 "FIRST LOOT-BAND INDEX"
§430  **这个 gamestate 从 `1163` 开始，注册 `1163..1168`**（`Wetwork`）
⇒ **⇒ 三处【不同的地图/模式**有不同的动态起点**】
```

**✅ ⭐⭐ **"动态起点是逐 gamestate 的"** —— 与 §398 的"索引逐 gametype"**同族（**第八次）。

**⇒ 三层**：
```text
`firstDynamic` ⇒ **从 `gameState_.modularWeaponConfigStrings.begin()->first - WeaponConfigStringBase` 算**
⇒ **⇒ 所以【它是【运行时算的**】不是常量**
```

**✅ ⭐⭐ **一个"运行时计算的边界"的实例**。

### 3.4 而**"检查的两个分支"**

```cpp
if (error == std::errc{} && end == token.data() + token.size() &&
    requested >= firstDynamic &&
    (requested >= WeaponConfigStringCount ||
        !gameState_.modularWeaponConfigStrings.contains(
            static_cast<std::uint16_t>(WeaponConfigStringBase + requested))))
```

**⇒ 十层**：
```text
1. **解析成功**
2. ⇒ **消耗了全部 token**
3. ⇒ **`requested >= firstDynamic`**（**在动态区**）
4. ⇒ **而【`requested >= WeaponConfigStringCount`】（**超出整个武器带**）**
5. ⇒ **或【那个 configstring 不在 `modularWeaponConfigStrings` 里**】**
6. ⇒ **⇒ 则【拒绝**】**
7. ⇒ **⇒ 所以【静态区（`< firstDynamic`）不受检查**】
```

### 3.5 ⭐⭐⭐ **"静态区不受检查"**

**✅ 这是本报告里**最重要的一条"检查的适用范围**。**

**⇒ 三层**：
```text
静态武器 ⇒ **引擎自带** ⇒ **任何索引都有效**（**在带内**）
动态武器 ⇒ **必须在 gamestate 里注册过**
⇒ **⇒ 所以【只有动态区需要检查**】
```

**✅ 与 §422 的"`spawnScriptModel` 的 `gameplayActive` staging 只在模式变化时跑"**不同（这是**一个"静态 vs 动态"的区分**）。

**⇒ 三层**：
```text
静态 ⇒ **地图/引擎提供**
动态 ⇒ **运行时注册**
⇒ **⇒ 同一个"检查"只对后者**
```

**✅ ⭐⭐ **一个"静态 vs 动态"的精确界限**。

**⚠ 而"`a 1198` 对 `firstDynamic = 1163`"⇒ **`1198 > 1163`** ⇒ **检查会触发**。**

**⇒ 三层**：
```text
`1198 >= 1163` ⇒ **在动态区**
而 `1198` 不在 `1163..1168` ⇒ **不在 `modularWeaponConfigStrings`**
⇒ **⇒ 而 `1198 < WeaponConfigStringCount`？** ⇒ **若是 ⇒ 拒绝**
```

**✅ 所以那个检查**正确地拒绝了**零售的 `a 1198`。**

**✅ ⭐ **一个"保护性拒绝"的实例**。</br>

**✅ 与 §413 的"`A_RESEND|` 只在主武器索引真的变了才补发"**不同（那是**去重**，这是**可行性**）。

## 四、**`drift` 的有符号理由**（本组第三重要）

### 4.1 那段

```php
// Signed on purpose. An unsigned difference would print a
// ten-digit number instead of the truth if a future change ever
// named a flagged frame NEWER than the recorded one, and an
// instrument that misreports the failure it exists to catch is
// worse than none.
" drift=" + std::to_string(
    static_cast<std::int64_t>(*client.newestFlaggedSnapshotMessage) -
    static_cast<std::int64_t>(*baselineMessage))
```

### 4.2 十四层

```text
1. **有符号，故意的**
2. ⇒ **一个无符号的差【会打印一个十位数字**】而不是真相**】
3. ⇒ **如果【一个未来的改动**】命名了一个【比记录的那个【更新**】的被标记帧**
4. ⇒ **⇒ 那么【`newestFlagged - baseline` 为负**】**
5. ⇒ **⇒ 而无符号 ⇒ 一个【巨大的正数**】】
6. ⇒ **⇒ 而【一个【误报它存在的那个失败的仪器**】比没有更糟**】
```

### 4.3 ⭐⭐⭐ **"一个误报它存在的那个失败的仪器比没有更糟"**

**✅ 这是本报告里**最重要的一条"仪器的可靠性"**。**

**✅ 与 §405 的"一个对实验主体是错的启发式比没有工具更糟"**——**几乎逐字相同** ✓

**⇒ 三层**：
```text
§405  "一个对【实验主体】是错的启发式【比没有工具更糟**】**
§430  "一个【误报它存在的那个失败的仪器**】比没有更糟**"
⇒ **⇒ 同一原则的两次**
```

**✅ ⭐⭐⭐ **一个"工具质量"的两例**。

**⚠ 而"十位数字"⇒ **`uint32` 的负值 ≈ `4.29e9`** ⇒ **恰好十位**。**

**✅ ⭐ **一个精确的量级。

### 4.4 而**"两个失败打印不同的字段而不是共用一个词"**

```php
// The two failures print different fields rather
// than sharing one word: a stale generation names both message numbers and the
// drift between them, a missing generation names neither.
```

**⇒ 六层**：
```text
1. **两个失败打印【不同的字段**】**
2. ⇒ **`staleFlaggedGeneration`** ⇒ **两个消息号 + drift**
3. ⇒ **`unrecordedFlaggedGeneration`** ⇒ **都没有**
4. ⇒ **⇒ 所以【`kind=` 有两个不同的值**】
5. ⇒ **（`entity-generation` 与 `entity-generation-unrecorded`）**
```

**✅ 与 §426 的"它报告值而不是一个判决"**完全同族（**第四次"每个分支命名自己"）。

**⇒ 三层**：
```text
§405  **三个所有者一个没留一行** ⇒ 加行
§426  **两个非 (B) 分支** ⇒ 各自命名
§430  **两个失败** ⇒ 不同的 `kind=` 与不同的字段
⇒ **⇒ 三次"分支各自命名**】
```

**✅ ⭐⭐ **一个"分支命名"的三例表**。

## 五、**`newestFlaggedSnapshotMessage` 的"与旗标上线同一瞬间记录"**

### 5.1 那段

```php
if (initializeBaselineCache)
{
    client.baselineCacheInitializationMessage = messageNum;
    // THE ONLY GENERATION THE CLIENT'S FLAT ENTITY ARRAY CAN HOLD (section 170).
    // Every flagged frame refills dword_C89E050 from position zero -- the cursor
    // reset at 0x00472223 -- so the newest one we have EMITTED is the newest one
    // the client can possibly be holding entities for. Recorded here, at the same
    // instant the flag actually goes on the wire, so it can never describe a
    // message we decided not to send. Unlike
    // baselineCacheInitializationMessage this is NOT cleared on acknowledgement:
    // the acknowledgement is precisely when the selection above needs it.
    client.newestFlaggedSnapshotMessage = messageNum;
}
```

### 5.2 十六层

```text
1. **客户端平铺实体数组【唯一能持有的代次**】**
2. ⇒ **每一个被标记帧【从位置零重新填充 `dword_C89E050`**】**
3. ⇒ **⇒ 所以【我们【发过的**】最新的一个【是客户端可能持有的最新**】】**
4. ⇒ **⇒ 记录在这里，【与旗标真正上线【同一瞬间**】】**
5. ⇒ **⇒ 所以【它【永不**】能描述一条【我们决定不发**】的消息**】
6. ⇒ **⚠ 与 `baselineCacheInitializationMessage` 不同**
7. ⇒ **这个【不在确认时被清空**】**
8. ⇒ **⇒ 因为【确认【正是**】上面那个选择需要它的时刻**】**
```

### 5.3 ⭐⭐⭐ **"记录在旗标真正上线的同一瞬间，所以它永远不能描述一条我们决定不发的消息"**

**✅ 这是本报告里**最重要的一条"记录点的选择**。**

**⇒ 三层**：
```text
错误：**在决定发送时记录** ⇒ **若 `Netchan_Transmit` 失败 ⇒ 【记录了一个没发的**】
正确：**在**成功后**记录**（`plaintext` 非空之后）
⇒ **⇒ 所以【记录必须在【副作用发生之后**】】
```

**⚠ 但代码是**在 `Netchan_Transmit` 之后**（`plaintext.empty()` 已检查）⇒ **所以是记录在成功后** ✓

**✅ ⭐⭐⭐ **"记录在成功之后"** —— 与 §409 的"候选-提交模式"**同族（**第四次"提交后记录**）。

**⇒ 三层**：
```text
§409  `candidate` → 转移 → 检查 → **全部成功才 `move`**
§426  **`stage 6` 时清六样**
§430  **`Netchan_Transmit` 成功后才记 `newestFlaggedSnapshotMessage`**
⇒ **⇒ 三次"成功后再提交状态**】
```

**✅ ⭐⭐ **一个"提交顺序"的三例表**。

**⚠ 而"不在确认时清空，因为确认正是需要它的时刻"⇒ **一个反直觉但正确的生命周期**。**

**⇒ 三层**：
```text
`baselineCacheInitializationMessage` ⇒ **在确认时清空**（**它已完成使命**）
`newestFlaggedSnapshotMessage` ⇒ **永不自动清空**（**因为确认时【需要它**】）
⇒ **⇒ 两个相似的名字，相反的处置**
```

**✅ ⭐⭐⭐ **"两个相似的名字，相反的处置"** —— 一个**极精细的区分**。

**✅ 与 §417 的"`checkDeathAnimationRisk` 的 `static` map"**不同（这是**两个字段的不同生命周期**）。

## 六、**`clientPrediction` 的 `memcpy` 与 `static_assert`**

```cpp
SvClientPrediction clientPrediction{};
if (client.lastReceivedUserCmd)
{
    static_assert(
        sizeof(clientPrediction.origin) ==
        sizeof(std::uint32_t) * 3);
    std::memcpy(
        clientPrediction.origin.data(),
        client.predictedState.values.data(),
        sizeof(clientPrediction.origin));
    clientPrediction.commandTime = client.predictedState.values[3];
    clientPrediction.valid = true;
}
```

**⇒ 八层**：
```text
1. **`static_assert` 保证【`3` 个 `uint32` 与 `3` 个 `float` 同大小**】**
2. ⇒ **⇒ 所以 `memcpy` 是【安全的位重解释**】**
3. ⇒ **`values[0..2]` ⇒ `origin`（三个 `float`）**
4. ⇒ **`values[3]` ⇒ `commandTime`（一个整数）**
5. ⇒ **`values[4]` ⇒ 【未用**】（**"只被观察为零"**）
6. ⇒ **⇒ 所以【五个 `long` 里用了四个**】**
```

**✅ 与 §418 的"`predicted=1140621312,...` 是三个浮点与一个整数"**完全闭合 ✓

**⇒ 三层**：
```text
§417  `SvClientPrediction` 的四个字段
§418  **五个 `long` 的实测解码**
§430  **`memcpy` + `static_assert` 的实现**
⇒ **⇒ 三次确认同一个结构**
```

**✅ ⭐ **一个跨三报告的闭合**。

## 七、`setPlayerNameString` 的"全或无"

```cpp
for (std::uint32_t recipient{}; recipient < clients_.size(); ++recipient)
{
    if (clients_[recipient].state != ClientState::Free &&
        clients_[recipient].gamestateMessageNum &&
        !canQueueReliableCommands(recipient))
    {
        return false;
    }
}
```

**⇒ 八层**：
```text
1. **先检查【每一个收件人能排队**】**
2. ⇒ **任何一个不能 ⇒ 【返回 `false`，什么都不做**】**
3. ⇒ **⇒ 所以【名字更新是【全或无**】】**
4. ⇒ **理由：一个玩家名若只发给一部分客户端 ⇒ 【不一致**】**
```

**✅ 与 §422 的"`purchaseMapTargetGroup` 的全有或全无"**完全同族（**第五次"事务性**）。

**⇒ 三层**：
```text
§409  `advanceSdRound` 的四个 candidate
§422  `purchaseMapTargetGroup` 的全有或全无
§430  `setPlayerNameString` 的全或无
⇒ **⇒ 三次"事务**】
```

**✅ ⭐⭐ **一个"事务性"的三例表**。

**⚠ 而"`canQueueReliableCommands(recipient)` 默认 `count = 1`"⇒ **`pending <= capacity - 1`**。**

**⇒ 三层**：
```text
`canQueueReliableCommands` 的 `count = 1`
⇒ **`pending <= capacity - 1`**
⇒ **⇒ 所以【恰好 `capacity` 个待发 ⇒ 满**】
```

**✅ 与 §426 的"`reliableSequence - reliableAcknowledge >= capacity` ⇒ 拒绝"**一致 ✓

**⇒ 三层**：
```text
§426  `queueReliableCommand`：`pending >= capacity` ⇒ 拒绝
§430  `canQueueReliableCommands`：`pending <= capacity - count` ⇒ 可
⇒ **⇒ 两个条件【等价**】
```

**✅ ⭐ **一个"两个 API 的一致性"**。

## 八、关键结论

1. **⭐⭐⭐ "我们自己的录制带 `22` 个 configstring 而零售是 `417`，且【一条 `d` 命令都没有】"** —— 第二次"一个通道完全未用"（与 §402 的 `s 0201` 同族）；而 **`395 / 417 = 95%` 的 configstring 是比赛期间加的**。
2. **⭐⭐ 六个 `d` 带各有自己的触发点**：`3636..3678`（音效别名，**每个连杀/武器首次使用时**）、`12254..12278`（骨/tag 名，**每个载具/模型首次受损时**）、`864..871`（拾取串）、`792..794`（attach 记录）、`15`/`464`（时钟，`9:48.7` 清空）、`11861`（时间缩放）、`2557`（调色）。
3. **⭐ `792` 的两形态澄清**：§407 的两次（`mat -1`/`offmat -1` 然后换位 `mat 154`）vs §430 的一次（`\ent\381\offs\0 0 0\mat\154\flags\0`）⇒ **§430 是第二次的那个形态**。
4. **⭐⭐ `SV_SetConfigString` 的五道守卫**：没有 gamestate / 玩家名带必须与格式化值一致 / **值未变返回 `0`** / 过长 / **只发给已收到 gamestate 的客户端**。
5. **⭐⭐⭐ "`d` 会描述一个客户端还没有表的 configstring，而那个值已经在它即将收到的 gamestate 里"`** ⇒ **`d` 必须在 gamestate 之后** —— 与 §408 的"`d 2557` 是全局状态"共同构成"gamestate 与 `d` 的关系"。
6. **⚠ 一个可能的静默丢失**：`insert_or_assign` **在排队之前**，所以**若排队失败（队列满），`gameState_` 已更新而客户端永远不知道，且下一次同值返回 `0` 永不重试**。
7. **⭐⭐⭐ `a <index>` 的三重前提**：① **在权威 `playerState` 里已拥有**（§403）；② **那个索引在 gamestate 的武器块里**（§430）；③ **`ownsActivationWeapon` 检查**（§413）—— 而**一个不在块里的动态索引解析成 null 定义并在 `out.exe+0x19B79B` 崩溃，"在客户端能报告一个有用的错误之前"**。
8. **⭐⭐ "动态起点是逐 gamestate 的"**：`mp_battlecity` 的 `1147`、`Wetwork` 的 `1163`（注册 `1163..1168`）、loot 带的 `1148` —— **而代码从 `modularWeaponConfigStrings.begin()->first - WeaponConfigStringBase` 运行时计算**。
9. **⭐⭐ "静态区不受检查"**：只有 `requested >= firstDynamic` **且**（超出整个带 **或** 不在 `modularWeaponConfigStrings`）才拒绝 ⇒ **一个"静态 vs 动态"的精确界限**。
10. **⭐⭐⭐ "一个有符号的差是故意的：无符号会打印一个十位数字而不是真相，如果将来命名了一个比记录更新的被标记帧；而【一个误报它存在的那个失败的仪器比没有更糟】"`** —— 与 §405 的"一个对实验主体是错的启发式比没有工具更糟"**几乎逐字相同**。
11. **⭐⭐ "两个失败打印不同的字段而不是共用一个词：`stale` 命名两个消息号与 drift，`unrecorded` 都不命名"`** —— 第三次"每个分支命名自己"。
12. **⭐⭐⭐ `newestFlaggedSnapshotMessage` 记录在 `Netchan_Transmit` 成功之后**（`plaintext` 已检查非空）⇒ **"它永远不能描述一条我们决定不发的消息"`** —— 第三次"成功后再提交状态"。
13. **⭐⭐⭐ 两个相似的名字，相反的处置**：`baselineCacheInitializationMessage` **在确认时清空**（使命完成）而 `newestFlaggedSnapshotMessage` **永不自动清空**（**因为确认时正是上面那个选择需要它的时刻**）。
14. **⭐ `clientPrediction` 的 `memcpy` + `static_assert(sizeof(origin) == sizeof(uint32)*3)`** ⇒ **五个 `long` 里用四个**（`values[4]` 只被观察为零）—— 跨 §417/§418/§430 三报告闭合。
15. **⭐⭐ `setPlayerNameString` 的"全或无"**：**先检查每一个收件人能排队，任何一个不能就返回 `false` 什么都不做** —— 第三次"事务性"；而 `canQueueReliableCommands` 与 `queueReliableCommand` 的两个条件**等价**。

## 九、未闭合点

- `WeaponConfigStringCount` 的值。
- `PlayerNameConfigStringBase` / `PlayerNameConfigStringCount`。
- `SV_FormatPlayerNameConfigString` 的格式。
- `SV_SetConfigString` 排队失败时的重试路径（我推断为"永不重试"）。
- `values[4]` 的语义。
- `sv_client_mp.cpp` 2130 行之后未读取（**共 `4500` 行**）。
