# 398 · **"`sub_466450` 不只是显示它 —— 它【除以】它"** —— `0xC0000094` 除零、`cs 189 → cs 509 = 189 + 320` 的名字/值分带、`ui_hud_round_goal` 是 8 不是 16

## 一、范围

本报告学习 `sv_main_mp.cpp` 2760–3120 行。

## 二、**`battery_multiplier` 的完整崩溃与分带**（本组最重要的一段）

### 2.1 那段（第一半：崩溃）

```php
// `battery_multiplier` matters because the client does not merely display it --
// sub_466450 DIVIDES by it. Dvar_FindVar missing it yields 0.0, `fldz` at
// 0x4665AF, and the `idiv` at 0x4665EC faults the client with 0xC0000094 on any
// zm map. That is the crash `out.exe`'s byte patch at VA 0x46659C papers over by
// jumping the whole lookup; supplying the dvar makes the real path work.
```

### 2.2 十二层

```text
1. **`battery_multiplier` 重要因为客户端不只是【显示】它**
2. ⇒ **`sub_466450` 【除以】它**
3. ⇒ **`Dvar_FindVar` 找不到它 ⇒ 得到 `0.0`**
4. ⇒ **`0x4665AF` 的 `fldz`**（加载零）
5. ⇒ **而 `0x4665EC` 的 `idiv` 让客户端以 `0xC0000094` 崩溃**
6. ⇒ **在任何 zm 地图上**
7. ⇒ **而那正是 `out.exe` 在 VA `0x46659C` 的【字节补丁】所掩盖的崩溃**
8. ⇒ **通过【跳过整个查找】**
9. ⇒ **而提供一个 dvar 让【真正的路径】工作**
```

### 2.3 ⭐⭐ **"不只是显示它 —— 它除以它"**

**✅ 与 §390 的"`int()` 截断而不是四舍五入"**同族（**第八次"一个值的第二个用途"）。**

**⇒ 三层**：

```text
假设：一个 "multiplier" 只用于显示
实际：**`sub_466450` 除以它**
⇒ **⇒ 缺它就是除零**
```

**✅ ⭐ **`0xC0000094` = `EXCEPTION_INT_DIVIDE_BY_ZERO`**。**

**⚠ 而"`0x46659C` 的字节补丁【跳过整个查找】"⇒ **一个绕过**。**

**⇒ 三层**：

```text
原版：`Dvar_FindVar` ⇒ 0.0 ⇒ `idiv` ⇒ 崩溃
字节补丁：**跳过查找与除法** ⇒ 不崩但也不缩放
提供 dvar：**真正的路径工作**
```

**✅ ⭐ **"补丁掩盖 vs 提供数据"** —— 一个**根本性的区别**。**

**✅ 与 §360 的"崩溃说 `demoq` 是对的"**同族（**第八次"崩溃是一个证据"）。**

### 2.4 那段（第二半：分带）

```php
// THE VALUE IS 1.2, AND IT IS IN THE DEMOS AFTER ALL. This comment used to say
// "no demo carries it" and sent 1. Both were wrong: the zm captures pair a NAME
// band with a VALUE band at a FIXED +320 OFFSET, so the dvar is present but not
// greppable by name. Verified on C-2021-7-31[15-32-16]zm:
//
//     cs 189 battery_multiplier   ->  cs 509 = 1.2      (189 + 320)
//     cs 190 scr_spy_round_state  ->  cs 510 = end
//     cs 195 ui_cpoffsety         ->  cs 515 = 0
//     cs 206 ui_zhunt_zombie_hp   ->  cs 526 = (empty)
//
// Eighteen zm names at 189..206, alphabetically sorted. THE INDICES ARE
// PER-GAMETYPE and do not transfer -- dm publishes twelve at 189..200, where
// 189 is ui_bossBodyDestroyedInfo and ui_cpoffsety is 190 rather than 195. So
// never hardcode 189; it is battery_multiplier only because it sorts first in
// zm's list.
//
// Sending 1 did not crash -- the divisor was 1000 instead of retail's 1200 --
// so the battery economy ran ~20% off retail with nothing to show for it.
```

### 2.5 二十层

```text
1. **值【是】1.2，而它【在】demo 里**
2. ⇒ **这段注释过去说"没有 demo 携带它"而发 `1`**
3. ⇒ **两个都错了**
4. ⇒ **因为 zm 捕获把一个【名字带】与一个【值带】配对在一个【固定的 +320 偏移】上**
5. ⇒ **所以那个 dvar 【存在】但【不能按名字 grep】**
6. ⇒ **在 `C-2021-7-31[15-32-16]zm` 上验证**：
      · `cs 189 battery_multiplier` → `cs 509 = 1.2`（`189 + 320`）
      · `cs 190 scr_spy_round_state` → `cs 510 = end`
      · `cs 195 ui_cpoffsety` → `cs 515 = 0`
      · `cs 206 ui_zhunt_zombie_hp` → `cs 526 = (空)`
7. ⇒ **十八个 zm 名字在 `189..206`，【按字母排序】**
8. ⇒ **而那个索引是【逐 gametype】的而【不能转移】**
9. ⇒ **dm 发布十二个在 `189..200`**
10. ⇒ **而那里 `189` 是 `ui_bossBodyDestroyedInfo`**
11. ⇒ **而 `ui_cpoffsety` 是 `190` 而不是 `195`**
12. ⇒ **所以【绝不硬编码 189】**
13. ⇒ **它只是 `battery_multiplier` 因为它在 zm 的列表里【排第一】**
14. ⇒ **发 `1` 没有崩溃**（除数是 `1000` 而不是零售的 `1200`）
15. ⇒ **所以电池经济跑了约 20% 偏差而【什么也没显示**】
```

### 2.6 ⭐⭐⭐ **"名字带与值带在固定的 +320 偏移"**

**✅ 这是本文件里**最重要的一个协议发现**。**

**⇒ 三层**：

```text
假设：dvar 的值在名字【同一个 configstring】
实际：**名字在 `cs 189..206` 而值在 `cs 509..526`**（+320）
⇒ **⇒ 按名字 grep 会漏掉它们**
```

**✅ 与 §340 的"定向的负面"**同族（**第七次"一个搜索方式决定了结论"）。**

**⚠ 而"不能按名字 grep"⇒ **一个具体的工具盲区**。**

**✅ **第八次"工具/搜索盲区"。**

**⇒ 一个**可复用的教训**：**

```text
grep 名字找不到 ⇒ **先检查名字与值是否【分带】**
```

**✅ ⭐ **一个极有价值的方法论**。**

### 2.7 而**"索引是逐 gametype 的而不能转移"**

**✅ 与 §394 的"`gameState.scriptMenus` 的三槽表是不同的"**同族（**第四次"逐 gametype 差异"）。**

**⇒ 三层**：

```text
zm：18 个在 189..206（**字母序**）
dm：12 个在 189..200，而 189 是 `ui_bossBodyDestroyedInfo`
⇒ **⇒ 同一个索引不同含义**
```

**✅ ⭐ **"绝不硬编码 189"** —— 一个明确的禁令。**

**⚠ 而"按字母排序"⇒ **所以顺序由名字决定**。**

**✅ 一个**可推导的规则**。

### 2.8 而**"发 1 没有崩溃 —— 除数是 1000 而不是零售的 1200"**

**✅ 与 §389 的"`battery_multiplier = 1.2` 而客户端除以 1200"**完全闭合 ✓

**⇒ **第三次确认那个转换。**

**⚠ 而"20% 偏差"⇒ **`1200 / 1000 = 1.2`** ✓**

**✅ **一个精确的算术**。

## 三、**`ui_hud_round_goal` 是 8 不是 16**（本组第二重要）

### 3.1 那段

```php
// ZOMBIES' OWN CONNECT BLOCK, MEASURED. All five zm demos send exactly these,
// once, as plain `s` setDvars (re/demo-re/15-zm-inventory.md sec.2). The 3.3.3.3
// project recorded that zm "has no such dvars at all"; on this build it is four
// commands, and `ui_hud_round_goal` is 8 rather than the 16 that was guessed.
```

### 3.2 七层

```text
1. **僵尸自己的连接块，测量出来的**
2. ⇒ **全部五个 zm demo 恰好发这些，一次，作为普通 `s` setDvar**
3. ⇒ **（`re/demo-re/15-zm-inventory.md` 第 2 节）**
4. ⇒ **3.3.3.3 项目记录 zm "根本没有这样的 dvar"**
5. ⇒ **而在这个 build 上是【四条命令】**
6. ⇒ **而 `ui_hud_round_goal` 是 `8` 而不是猜的 `16`**
```

**✅ ⭐ **"3.3.3.3 项目记录 zm 根本没有这样的 dvar"** —— 又一次**逐 build 差异**（第五次）。**

**⚠ 而"四条命令"⇒ **一个具体的数量**。**

**✅ 与 §391 的"零售 `zm_factory_sh` 发 34 个模型带条目"**同族。

## 四、**`evaluateMatchLimits` 的三条路径**（本组第三重要）

### 4.1 那段

```php
if (!matchStatus_.configured || matchStatus_.completed) return;
// Zombies has no score limit either -- see SV_UpdateMatchTimeLimit for
// the clock. The booking hands zm scoreLimit 30, which is a couple of
// kills' worth of points, and the ONLY reason it has never ended a zm
// match is that nothing awards zm team score yet. Gate it before
// something does.
if (matchGameType_ == "zm") return;
if (matchGameType_ == "dm") {
    const auto best = clients_.bestClientKills();
    if (matchStatus_.rules.scoreLimit && best &&
        best->second >= (int32)matchStatus_.rules.scoreLimit) {
        matchStatus_.completed = true;
        matchStatus_.endReason = ScoreLimit;
        matchStatus_.winner = SvTeam::None;
        matchStatus_.winnerClientNum = best->first;
        write("match complete gametype=dm reason=scoreLimit winner=client...");
    }
    return;
}
const auto tfScore = clients_.teamScore(SvTeam::Tf).value_or(0);
const auto scScore = clients_.teamScore(SvTeam::Sc).value_or(0);
if (matchStatus_.rules.scoreLimit && (tfScore >= limit || scScore >= limit)) { ... }
```

### 4.2 十四层

```text
1. **三条路径**：`zm`（直接返回）/ `dm`（per-client）/ 其它（per-team）
2. ⇒ **`zm` 【没有分数上限】**
3. ⇒ **而预约给 zm `scoreLimit 30`，那是几个击杀的点数**
4. ⇒ **而它从未结束一场 zm 比赛的【唯一】理由**
5. ⇒ **是【还没有东西给 zm 队伍分】**
6. ⇒ **"在有什么东西之前门控它"**
7. ⇒ **`dm`：`bestClientKills()` ≥ limit ⇒ 完成**
8. ⇒ **`winner = SvTeam::None` 而 `winnerClientNum = best->first`**
9. ⇒ **其它：`tfScore` 或 `scScore` ≥ limit ⇒ 完成**
10. ⇒ **而赢家是 `tfScore == scScore ? None : 大的那个`**
11. ⇒ **两个分支都有日志**
12. ⇒ **而 `dm` 的日志是 `winner=clientN` 而队伍的是 `tf=/sc=/winner=Tf/Sc/None`**
13. ⇒ **所以两种格式**
```

**✅ 与 §391 的"ZM 没有比赛时钟"**完全闭合 ✓

**⇒ 而这里是"ZM 也没有分数上限" ⇒ **第二次确认。**

**⚠ 而"预约给 zm scoreLimit 30"⇒ **所以预约层的限制对 zm 无意义**。**

**✅ 与 §391 的"`DedicatedSession::valid` 拒绝没有限制的规则"**完全一致 ✓

### 4.3 而**`matchStatus_.startServerTime` 的"懒设置"**

```cpp
if (!matchStatus_.startServerTime)
    matchStatus_.startServerTime = world_.snapshot().serverTime;
evaluateMatchLimits();
```

**⇒ 三层**：

```text
1. **在第一次计分时【才设 `startServerTime`】**
2. ⇒ **而不是在配置时**
3. ⇒ **⇒ 所以"比赛时钟从第一次计分开始"**
```

**⚠ 而 §393 的 `configureGameState` 是 `matchStartServerTime = 0`。**

**⇒ 三层**：

```text
`gameState.matchStartServerTime = 0`  ⇒ **HUD 时钟的基**
`matchStatus_.startServerTime`        ⇒ **第一次计分时设**
⇒ **两个不同的时间基**
```

**✅ 与 §393 的"`matchStatus_.startServerTime` 在这里【什么都没有】"**完全一致 ✓

**⇒ **第二次确认那个区分。**

**⚠ 而"`!startServerTime`"⇒ **零是一个哨兵**。**

**✅ 与 §381 的"零速度是合法的"**同族（**第四次"零有语义"）。**

### 4.4 而 **`addClientScore` 与 `addKillForClient` 的分工**

```cpp
bool addClientScore(clientNum, delta) {
    // Display score only. It is 100 per kill and the limit is 30, so this must
    // NOT drive the limit - see addKillForClient, which is what does.
    return !matchStatus_.completed && clients_.addClientScore(clientNum, delta);
}
bool addKillForClient(clientNum, delta) {
    if (matchStatus_.completed || !clients_.addClientKills(clientNum, delta)) return false;
    if (delta > 0) sayBattleChatter(clientNum, KillfirmInfantry);
    if (!matchStatus_.startServerTime) matchStatus_.startServerTime = world_.snapshot().serverTime;
    evaluateMatchLimits();
    return true;
}
```

**⇒ 八层**：

```text
1. **`addClientScore` 只驱动【显示分】**（`100` 每击杀、`limit` 是 `30`）
2. ⇒ **所以它【绝不能】驱动上限**
3. ⇒ **`addKillForClient` 才是那个驱动上限的**
4. ⇒ **而它只在 `delta > 0` 时说战地闲聊**
5. ⇒ **因为一次自杀是减分，而确认一次你没做的击杀比沉默更糟**
6. ⇒ **而它设 `startServerTime` 并调 `evaluateMatchLimits`**
```

**✅ 与 §391 的"`124 SessionStart` vs `47 spawn-applied`"**不同（这是**两个计数器**）。**

**⚠ 而"`100` 每击杀而 `limit` 是 `30`"⇒ **所以 `limit` 是**击杀数**不是分数**。**

**✅ 一个**关键的区分**（`addKillForClient` 与 `addClientScore` 的计数器不同）。**

### 4.5 而**"确认一次你没做的击杀比沉默更糟"**

**✅ 与 §353 的"缺选的变体不被静默转成内脏"**同族（**第二十一次"不要伪造"）。**

**⇒ 三层**：

```text
自杀 ⇒ `delta < 0` ⇒ **不说话**
⇒ **因为"确认一次击杀"的语音在自杀时是【错的】**
⇒ **⇒ 而错的声音比没有声音更糟**
```

**✅ 一个**精确的产品判断**。

## 五、`sdRuntimeStatus` 与 `gameplayPresentationStatus` 的**两份队伍计数**

### 5.1 两份几乎相同的代码

```cpp
// sdRuntimeStatus
auto *const total = client.team == SvTeam::Tf ? &teams.attackers : client.team == SvTeam::Sc ? &teams.defenders : nullptr;
auto *const alive = client.team == SvTeam::Tf ? &teams.attackersAlive : client.team == SvTeam::Sc ? &teams.defendersAlive : nullptr;
if (!total || !alive) continue;
++*total;
if (playerState->health > 0) ++*alive;

// gameplayPresentationStatus（同样五句，且在 if (playerState->spawnGeneration) 内）
```

**⇒ 三层**：

```text
1. **两份【完全同构】的队伍计数**
2. ⇒ **而第二份多一个 `spawnGeneration` 检查**
3. ⇒ **⇒ 一处复制**
```

**✅ 与 §337 的"两个几乎相同的函数"**第八次。

**⚠ 而"第二份多一个 `spawnGeneration`"⇒ **所以两份**不完全等价**。**

**✅ 一个**细微的差异**。

### 5.2 而 `gameplayPresentationStatus` 的**九个 `lastXxxUserCmdTime`**

```text
pendingUserCmdCount / oldestPendingUserCmdTime / newestPendingUserCmdTime
lastReceivedUserCmdTime / lastDispatchedUserCmdTime / lastExecutedUserCmdTime
lastDiscardedUserCmdTime / discardedUnsupportedUserCmds
```

**⇒ 八个。**

**✅ 与 §392 的"`cmdAge`"、§383 的"`commitExecutedUserCmd`"**完全闭合 ✓

**⇒ **第三次确认那个命令流水线**：**

```text
received → dispatched → executed
         ↘ discarded
```

**✅ ⭐ **一个四阶段的命令追踪**。**

**⚠ 而"`discardedUnsupportedUserCmds`"⇒ **一个累计计数**。**

**✅ 与 §389 的"`SV_ShouldDiscardRejectedUserCmd`"**完全闭合 ✓

### 5.3 而**两个位掩码**

```cpp
if (entity.eType == EntityTypePlayer && entity.number < 32)
    snapshotPlayerEntityMask |= 1u << entity.number;
if (clientInfo.clientNum < 32)
    snapshotClientInfoMask |= 1u << clientInfo.clientNum;
```

**⇒ 三层**：

```text
1. **两个 32 位掩码**
2. ⇒ **一个给实体、一个给 clientInfo**
3. ⇒ **所以一次能看"这一帧发布了哪些玩家的哪一半"**
```

**✅ ⭐ **一个"按客户端位的存在图"**。**

**⚠ 而 `< 32`⇒ **一个 32 位的上限**（而 `MaximumGameClients` 是 18）。**

**✅ 一个**充裕的位宽**。

## 六、`playSoundForClient` 的"只对已注册的别名槽生效"

```php
// ★★ 28100 刀BP：Lua 侧 `method:playsound <aliasIndex>` 的落点。
//   只对**已注册的别名槽**生效（刀BQ 注册了槽 62 = wpn_kill_tank_special）。
//   走 `queueLocalSound`，与既有 `killFeedbackSound_`（通用击杀音）同一条通道，
//   差别只是"由脚本按武器系列决定播哪个槽"。
if (aliasIndex < 0 || aliasIndex > 255) return false;
return clients_.queueLocalSound(clientNum, (uint16)aliasIndex);
```

**⇒ 六层**：

```text
1. **Lua 侧 `method:playsound <aliasIndex>` 的落点**
2. ⇒ **只对【已注册的别名槽】生效**（`刀BQ` 注册了槽 `62` = `wpn_kill_tank_special`）
3. ⇒ **走 `queueLocalSound`，与既有的 `killFeedbackSound_` 【同一条通道】**
4. ⇒ **差别只是"由脚本按武器系列决定播哪个槽"**
5. ⇒ **而范围 `[0, 255]`**
```

**✅ 与 §391 的"`LocalSoundEventParameterMaximum`"**配合。**

**⚠ 而"槽 62 = `wpn_kill_tank_special`"⇒ **一个具体的注册**。**

**✅ 与 §352 的"`OLMOD_DMZ_PICKUP_EVENT` 是一个旋钮"**不同（这是**一个槽号**）。

## 七、关键结论

1. **⭐⭐ "`battery_multiplier` 重要因为客户端不只是显示它 —— `sub_466450` 【除以】它"`** —— **缺它就是 `0xC0000094` 除零崩溃**（`fldz` 在 `0x4665AF`、`idiv` 在 `0x4665EC`）。
2. **⭐ "`out.exe` 在 VA `0x46659C` 的字节补丁通过跳过整个查找来掩盖那个崩溃；而提供一个 dvar 让真正的路径工作"`** —— **"补丁掩盖 vs 提供数据"**。
3. **⭐⭐ "zm 捕获把一个【名字带】与一个【值带】配对在一个固定的 `+320` 偏移上 ⇒ 那个 dvar 存在但不能按名字 grep"`** —— `cs 189` → `cs 509 = 1.2`，`cs 190` → `cs 510 = end`，`cs 195` → `cs 515 = 0`，`cs 206` → `cs 526 = 空`。
4. **"十八个 zm 名字在 `189..206`，按字母排序"** 而 **"那个索引是逐 gametype 的而不能转移：dm 发布十二个在 `189..200` 而 `189` 是 `ui_bossBodyDestroyedInfo`，`ui_cpoffsety` 是 `190` 而不是 `195` ⇒ 绝不硬编码 189"`**。
5. **"发 `1` 没有崩溃 —— 除数是 `1000` 而不是零售的 `1200` ⇒ 电池经济跑了约 20% 偏差"`** —— 第三次确认那个转换。
6. **"3.3.3.3 项目记录 zm 根本没有这样的 dvar，而在这个 build 上是四条命令，`ui_hud_round_goal` 是 `8` 而不是猜的 `16`"`** —— 第五次"逐 build 差异"。
7. **⭐ `evaluateMatchLimits` 的三条路径**：**`zm` 直接返回**（"没有分数上限，而预约给的 `30` 从未结束一场 zm 比赛的唯一理由是还没有东西给 zm 队伍分"）/ **`dm` 用 `bestClientKills`** / **其它用 `teamScore`**。
8. **"两个分支都有日志"**，而 **`dm` 的格式是 `winner=clientN`** 而**队伍的是 `tf=/sc=/winner=Tf/Sc/None`** —— 两种格式。
9. **⭐ `matchStatus_.startServerTime` 的"懒设置"**（第一次计分时设）与 **§393 的 `gameState.matchStartServerTime = 0`** 是**两个不同的时间基**。
10. **"`addClientScore` 只驱动显示分（`100` 每击杀、`limit` 是 `30`）⇒ 绝不能驱动上限；`addKillForClient` 才是那个"`** —— 两个计数器。
11. **⭐ "只有 `delta > 0` 才说战地闲聊：一次自杀是减分，而确认一次你没做的击杀比沉默更糟"`** —— 第二十一次"不要伪造"。
12. **⚠ `sdRuntimeStatus` 与 `gameplayPresentationStatus` 的两份队伍计数完全同构**，而第二份多一个 `spawnGeneration` 检查 —— 第八次"复制代码"。
13. **`gameplayPresentationStatus` 的八个命令时间字段** —— 第三次确认那个四阶段流水线（`received → dispatched → executed` / `discarded`）。
14. **⭐ 两个 32 位位掩码**（`snapshotPlayerEntityMask` / `snapshotClientInfoMask`）—— 一个**"按客户端位的存在图"**。
15. **`playSoundForClient` 只对已注册的别名槽生效**，而 **`killFeedbackSound_` 与它走同一条 `queueLocalSound` 通道**。

## 八、未闭合点

- `sub_466450` 的完整实现（除法的另一端）。
- `0x46659C` 字节补丁的原始字节。
- zm 的十八个 dvar 名字全表。
- `bestClientKills` 的实现。
- `SvBattleChatterLine` 的完整枚举。
- `sv_main_mp.cpp` 3120 行之后未读取。
