# 380 · **"不是活着意味着保持【结束】，不是挂起"** —— `LEFT ALT` 的 ALT-TAB 自杀链、两次 `0xC0000005`、spawn 帧重新武装

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 23600–24000 行。

## 二、**`applyNoclipHold` 的完整事故**（本组最重要的一段）

### 2.1 那段

```php
// ONLY 0 <-> 2, NEVER ANYTHING ELSE. Death writes 8, the match end
// writes 5, and a laststand or a linked player carries its own value;
// stepping on any of them here would either resurrect a corpse or
// strand a player in a state its own owner then clears. It also gives
// release-on-death for free: the value stops being 2 the moment
// somebody dies, and comes back only if the key is still held when
// they respawn at 0.
//
// EXCEPT THAT "COMES BACK WHEN THEY RESPAWN" IS A CRASH, MEASURED TWICE ON
// 2026-09-03 (handoff SS191h). Leaving pmType alone while somebody is dead
// SUSPENDS the hold; it does not end it. So the entry is still here on the
// frame the respawn writes pmType 0, this runs in the same frame, and noclip
// re-arms ON THE RESPAWN FRAME. The client died there both times:
//
//   14:12:14 fall death -> 14:12:17 respawn -> 0xC0000005 read [0x00000018]
//   14:32:05 fall death -> 14:32:08 respawn -> 0xC0000005 read [0x21CE9880]
//
// Two different faults, one trigger. And the deaths themselves come from the
// same key: the hotkey is LEFT ALT, so every ALT-TAB toggles noclip, drops the
// player through the floor (org.z=-64) and kills them with fall damage on the
// way out. Four fall deaths exist in the entire log; the two that happened
// while this could re-arm are the two that crashed.
//
// NOT ALIVE MEANS THE HOLD IS OVER, not suspended. The key repeats every
// 500 ms, so a player still holding it gets noclip back within half a second
// of being alive again -- from a fresh request, on an ordinary frame, instead
// of from a stale entry racing the respawn.
if (wanted && playerState.pmType != SvPmTypeNormal &&
    playerState.pmType != SvPmTypeNoclip)
{
    noclipHoldUntil_.erase(clientNum);
    wanted = false;
    OlMod::RuntimeLog::write(..., "noclip hold DROPPED client=" + ... + " pmType=" + ... +
        " (not alive; it must not re-arm on the respawn frame)");
}
```

### 2.2 二十二层

```text
1. **只 `0 <-> 2`，绝不动其它任何值**
2. ⇒ **死亡写 `8`，比赛结束写 `5`**
3. ⇒ **而 `laststand` 或一个被链接的玩家携带自己的值**
4. ⇒ **在这里踩它们中的任何一个会【复活一具尸体】或【把一个玩家困在一个它自己的所有者随后清除的状态里】**
5. ⇒ **它还免费给出"死亡时释放"**：
     · **有人死的那一刻值不再是 `2`**
     · **而只在重生到 `0` 时【如果键仍被按住】才回来**
6. ⇒ **除开"重生时回来"是一次【崩溃】，2026-09-03 测量了两次**（handoff SS191h）
7. ⇒ **在有人死时【不管 `pmType`】是【挂起】保持，它【不是结束】它**
8. ⇒ **所以那个条目在重生写 `pmType 0` 的那一帧【仍在】**
9. ⇒ **这个函数在同一帧跑**
10. ⇒ **而 noclip 【在重生帧重新武装】**
11. ⇒ **客户端两次都死在那里**：
     · `14:12:14` 摔落死 → `14:12:17` 重生 → **`0xC0000005 read [0x00000018]`**
     · `14:32:05` 摔落死 → `14:32:08` 重生 → **`0xC0000005 read [0x21CE9880]`**
12. ⇒ **两个不同的故障，一个触发器**
13. ⇒ **而那些死亡本身来自【同一个键】**
14. ⇒ **热键是 `LEFT ALT`**
15. ⇒ **所以每一次 `ALT-TAB` 都切换 noclip**
16. ⇒ **把玩家【扔穿地板】**（`org.z=-64`）
17. ⇒ **并在出去的路上用摔落伤害杀死他们**
18. ⇒ **整个日志里存在【四次】摔落死**
19. ⇒ **而那两个在"这能重新武装"的窗口里发生的就是那两个崩溃的**
20. ⇒ **"不是活着"意味着保持【结束】，不是挂起**
21. ⇒ **这个键每 `500ms` 重复**
22. ⇒ **所以一个仍按着它的玩家在重新活着后【半秒内】就拿回 noclip —— 来自一个【新鲜的请求】，在一个普通的帧上，而不是来自一个与重生赛跑的陈旧条目**
```

### 2.3 ⭐⭐ **"两个不同的故障，一个触发器"**

**✅ 与 §378 的"一个原因两个症状"**同族（**第四次"一个触发器多个故障"）。**

**⇒ 三层**：

```text
触发器：**重生帧重新武装 noclip**
故障 A：`read [0x00000018]`（近空指针）
故障 B：`read [0x21CE9880]`（一个垃圾地址）
⇒ **两个不同的崩溃地址、同一时刻**
```

**✅ **一个极精确的 ASLR/状态相关的证据**。**

**⚠ 而"每次 ALT-TAB 都切换 noclip"⇒ **一个灾难性的键选择**。**

**✅ 与 §368 的"玩家的判决"**同族（**第九次）。**

### 2.4 而**"四次摔落死，两个崩溃"**

**✅ 与 §371 的 `4,253`、§375 的 `294`**第十一次大规模统计。

**⚠ 而"四次里两次"⇒ **一个 50% 的相关性**。**

**✅ 与 §355 的"四个 actor 里两个"**同数值**。**

**⇒ **可能同一批测量。**

### 2.5 而**"挂起 vs 结束"的精确区分**

**✅ 这是本文件里**最精确的一个语义区分**。**

**⇒ 三层**：

```text
挂起：条目仍在 ⇒ 重生帧重新武装 ⇒ **崩溃**
结束：条目被删 ⇒ 重生帧无事 ⇒ **安全**
```

**✅ 与 §365 的"释放 vs 保持"**同族（**第二次"挂起/结束/释放"的三分）。**

**⚠ 而"500ms 重复"⇒ **所以**释放是安全的**（玩家半秒内拿回）。**

**✅ 一个**精确的补偿设计**。

### 2.6 而**"那个条目的不在就是你怎么知道这个守卫【什么都没做】"**

```php
// The edge only. This fires once per death, because the entry is gone
// afterwards -- and its absence is how you tell this guard did nothing.
```

**⇒ 四层**：

```text
1. **只触发边沿**
2. ⇒ **每次死亡一次**
3. ⇒ **因为条目之后【没了】**
4. ⇒ **而【它的不在】就是你怎么知道这个守卫【什么都没做】**
```

**✅ **一个极精妙的"负面也是信息"**。**

**⇒ 与 §346 的"七十五项合取"**相反**（那是**沉默**，这是**缺失即证据**）。**

**✅ 与 §340 的"定向的负面"**第六次。

## 三、**`setPlayerPodiumView` 与 `setPlayerKillCam` 的截断拒绝**（本组第二重要）

### 3.1 那段

```php
// 11 bits and 6 bits on the wire. A value that does not fit would be
// truncated into a DIFFERENT entity number rather than refused, which
// is the failure mode that looks like "the camera went somewhere else".
if (entityNum > 2047 || tag > 63) return false;
...
// 11, 11, 8 and 32 bits. A value that does not fit would be TRUNCATED
// into a different entity or client rather than refused, which is the
// failure mode that looks like "the killcam showed the wrong player".
if (lookAtEntityNum > 2047 || killerClientNum > 255) return false;
```

### 3.2 六层

```text
1. **`11` 位与 `6` 位**（`2047` / `63`）
2. ⇒ **一个不合适的值会被【截断】成一个不同的实体号**
3. ⇒ **而不是被拒**
4. ⇒ **那是看起来像"相机去了别处"的失败模式**
5. ⇒ **`11`/`11`/`8`/`32`**（`2047`/`2047`/`255`/`uint32`）
6. ⇒ **"killcam 显示了错的玩家"**
```

**✅ 与 §346 的"界必须是线宽"**完全同族（**第五次"界=线宽"）。**

**⚠ 而**两处都明说"截断成不同的号"**。**

**⇒ 与 §346 的"写 3 而客户端读 11"**不同** —— 那是**多读**，这是**截断**。**

**✅ **两种界错误**。**

### 3.3 而**`killCamEntityNum = 2047` 的"每一次"**

```php
// 2047 EVERY TIME, on all eight of the demo's killcams. This is the
// only value retail ever writes here, and it is the same all-ones
// "none" an 11-bit entity field uses everywhere else -- so the camera
// is not attached to an entity, it is placed from the other three.
playerState.killCamEntityNum = SvKillCamEntityNone;
```

**⇒ 七层**：

```text
1. **`2047` 每一次**（demo 的全部八次 killcam）
2. ⇒ **这是零售在这里写过的唯一值**
3. ⇒ **它是 11 位实体字段到处用的同一个"全一 = 无"**
4. ⇒ **所以相机【不】附着到一个实体**
5. ⇒ **它被从【其它三个】放置**
```

**✅ 与 §345 的"`EntityNumWorld = 2046`、`EntityNumNone = 2047`"**第四次确认。

**⚠ 而"八次 killcam 全是 2047"⇒ **一个 8/8 的全对**。**

**✅ 与 §370 的"10/10"、§353 的"15/15"**第六次"全对"。

### 3.4 而**"四个一起归零"**

```php
// ALL FOUR GO BACK TO ZERO TOGETHER, which is what the demo shows: the
// four are asserted on one frame and cleared on one frame, never
// partially. killCamEntity returns to 0 rather than staying at 2047.
playerState.killCamEntityNum = 0;
playerState.killCamLookAtEntityNum = 0;
playerState.killCamClientNum = 0;
playerState.killCamDeltaTime = 0;
```

**⇒ 五层**：

```text
1. **四个一起归零**
2. ⇒ **因为 demo 显示它们在一帧上断言、在一帧上清除，【从不部分】**
3. ⇒ **而 `killCamEntity` 回到 `0` 而不是停在 `2047`**
4. ⇒ **所以"设置"与"清除"是【不对称的】**（2047 vs 0）
```

**✅ 与 §372 的"两个游标必须相等"**同族（**第二次"多个字段同步"）。**

**⚠ 而"设置 2047 清除 0"⇒ **一个真实的非对称**。**

**✅ 与 §344 的"`EntityNumWorld` 与零是两个语义"**配合。

## 四、**`setMatchCompleted` 的"指南针随比赛走"**

```php
// THE COMPASS GOES OUT WITH THE MATCH. The demo clears playerState 86 at
// 648700, the same instant the outro opens, and it never comes back --
// so this follows the match rather than the player, and a re-arm on a
// new match is the caller's own reset.
for (auto &entry : clientStates_) {
    entry.second.client.playerState.compassRadarEnabled = completed ? 0u : 1u;
}
```

### 4.1 五层

```text
1. **指南针随比赛走**
2. ⇒ **demo 在 `648700` 清除 `playerState 86`**
3. ⇒ **正好是 outro 打开的那一刻**
4. ⇒ **而它【再也不回来】**
5. ⇒ **所以这跟随【比赛】而不是【玩家】**
6. ⇒ **而一次新比赛上的重新武装是【调用方自己的重置】**
```

**✅ 与 §346 的"`radarFlags` 的 6 位"**配合（`compassRadarEnabled` 可能不同）。

**⚠ 而"`playerState 86`"⇒ **一个具体的索引**。**

**✅ 与 §334 的"字段 86 在第二 pass 停止解码"**同族（**第二次提到索引 86**）。

**⚠ 所以**86 是 `compassRadarEnabled`**？**

**⇒ 与 §334 的"`compassRadar` 在第二 pass 停止解码（86 是 type 0，不在 `PlayerStateSecondPassFields`）"**完全闭合 ✓

**⇒ **一个具体的字段身份确定。**

## 五、**`setPlayerIntermission` 的"相机是一个【地方】"**（本组第三重要）

### 5.1 那段

```php
// AND THE CAMERA IS A PLACE (section 121). Writing pm_type without the
// move is what this server did for three sessions: the screen changed
// and the view did not, because the view IS the position.
//
// The demo's move frame asserts 81 fields where the one before it
// asserts 15, so the state below is the measured set rather than "the
// origin plus whatever seems related". Re-applied every frame by
// holdMatchCompletionState, because pmove rebuilds playerState and a
// single write is gone by the next frame.
playerState.origin = camera->origin;
playerState.velocity = {};
playerState.viewAngles = camera->angles;
// delta_angles is what actually turns the client's head: the client
// adds it to its own command angles, so without it the player keeps
// looking wherever the mouse last pointed and only the body turns.
if (commandState) {
    for (index) {
        playerState.deltaAngles[index] = camera->angles[index] - BG_ShortToAngle(commandState->currentUserCmd.angles[index]);
    }
}
// THE VIEW HEIGHT IS PART OF THE MEASURED SET, and leaving it out is
// what put the camera on the floor: the demo's intermission frame
// asserts viewHeightCurrent 40.00 and viewHeightTarget 0 together with
// everything else here.
playerState.viewHeightCurrent = 40.0f;
playerState.viewHeightTarget = 0;
playerState.speed = 0; playerState.bobCycle = 0; playerState.movementDir = 0;
playerState.legsAnim = 0; playerState.legsTimer = 0;
playerState.torsoAnim = 0; playerState.torsoTimer = 0;
playerState.weaponAnim = {}; playerState.weaponTime = {}; playerState.weaponDelay = {};
```

### 5.2 十四层

```text
1. **而相机是【一个地方】**（第 121 节）
2. ⇒ **只写 `pm_type` 而不移动是**这个服务器做了三个会话的事**；
3. ⇒ **屏幕变了而视角没变**
4. ⇒ **因为视角【就是】位置**
5. ⇒ **demo 的移动帧断言 81 个字段而那之前那一帧断言 15 个**
6. ⇒ **所以下面的状态是【测量出来的集合】而不是"原点加任何看起来相关的东西"**
7. ⇒ **由 `holdMatchCompletionState` 每帧重新施加**
8. ⇒ **因为 pmove 重建 `playerState` 而单写在下一帧就没了**
9. ⇒ **`deltaAngles` 是**真正转动客户端头**的东西**：客户端把它加到自己的命令角上
10. ⇒ **没有它玩家继续看鼠标最后指的地方而【只有身体转】**
11. ⇒ **视角高度是测量集合的一部分**
12. ⇒ **而漏掉它就是**把相机放在地板上**的那个**
13. ⇒ **demo 的中场帧断言 `viewHeightCurrent 40.00` 与 `viewHeightTarget 0` 与这里其它一切一起**
14. ⇒ **然后 12 个清零字段**
```

### 5.3 ⭐ **"81 个字段 vs 15 个"**

**✅ 与 §351 的 `237`、§371 的 `4,253`**第十二次大规模统计。

**⚠ 而"81 vs 15"⇒ **一个 5.4 倍的跳变**。**

**⇒ 所以**一个状态转换会断言大量字段**。**

**✅ 与 §344 的"布告无条件断言三字段"**同族（**第五次"一个转换写很多字段"）。**

### 5.4 而**"`deltaAngles` 是真正转动头的东西"**

**✅ 与 §372 的"`dA` 与 `yaw(srv-cmd)` 恒等"**完全闭合 ✓

**⇒ **第二次确认那个身份。**

**⚠ 而"没有它只有身体转"⇒ **第十一次具体视觉症状**。**

### 5.5 而**"三个会话"**

**✅ 与 §370 的"sect.190 花了两个会话"**同族（**第二次"以会话计的代价"）。**

**⚠ 而"三个会话"⇒ **一个昂贵的教训**。**

## 六、`equipPlayerEquipment` 的**"同一职业重新发布时不补弹"**

```php
if (const auto *current = playerEquipment(clientNum, generation)) {
    // SAME CLASS RE-PUBLISHED: never refill a spent grenade.
    if (*current == equipment) return true;
    // A DIFFERENT CLASS IN THE SAME LIFE IS A BACKPACK SWAP. Retail
    // lets the player change class without dying, and the new class's
    // lethal/tactical -- with their own counts -- must replace the old
    // pair. Refusing this is exactly why a mid-life backpack switch left
    // the old, spent grenades on the client.
}
auto candidate = owner.playerState;
if (const auto *const previous = playerEquipment(clientNum, generation))
    SV_ClearOffhandLoadout(candidate, *previous);
if (!SV_EquipOffhandLoadout(candidate, equipment)) return false;
```

### 6.1 七层

```text
1. **同一职业重新发布 ⇒ 【绝不补给一个用掉的投掷物】**
2. ⇒ **（`*current == equipment` ⇒ 直接 return true）**
3. ⇒ **同一世里的不同职业是【背包交换】**
4. ⇒ **零售允许玩家不死就换职业**
5. ⇒ **而新职业的致命/战术装备（带自己的计数）必须替换旧的那对**
6. ⇒ **拒绝这个正是为什么一次**中途背包交换**把旧用掉的投掷物留在客户端**
7. ⇒ **所以先 `SV_ClearOffhandLoadout` 再 `SV_EquipOffhandLoadout`**
```

**✅ 与 §366 的"退役旧存储后才装新的"**不同**（那是**先装后清**，这是**先清后装**）。

**⚠ 而两个**相反的顺序**：**

```text
§366  武器交换  ⇒ **先装后清**（因为共享索引）
§380  背包交换  ⇒ **先清后装**（因为新职业有自己的计数）
```

**✅ 一个**精确的差异**（共享 vs 独立）。**

### 6.2 而**"`SV_EquipOffhandLoadout` 只加"**

```php
// The swap branch above means `previous` is a DIFFERENT class. Release
// its grenades first: SV_EquipOffhandLoadout only adds, so without this
// the old lethal/tactical would survive the backpack swap.
```

**⇒ 四层**：

```text
1. **`SV_EquipOffhandLoadout` 【只加】**
2. ⇒ **所以不清会让旧的存活**
3. ⇒ **⇒ 所以必须显式清**
4. ⇒ **一个"只有加没有减"的 API 陷阱**
```

**✅ 一个**真实的 API 不对称**。

### 6.3 而 **`registerMultiplayerOffhandWeapons(equipment)`**

```php
// OLMOD(multiplayer_offhand_projectile): 本次 grant 进来的投掷物登记进 MP 表，
// 否则 endFrame 只认 Factory 池，MP 的投掷物不会被步进/引爆。
registerMultiplayerOffhandWeapons(equipment);
```

**⇒ 四层**：

```text
1. **本次 grant 进来的投掷物登记进 MP 表**
2. ⇒ **否则 `endFrame` 只认 Factory 池**
3. ⇒ **MP 的投掷物【不会被步进/引爆】**
4. ⇒ **一个完整的因果**
```

**✅ 与 §376 的"非副手导弹以前没有 runner"**同族（**第七次"一个缺失的注册"）。**

## 七、`consumePlayerUavAction` 的**六项**

```cpp
if (client == end || matchCompleted_ || !weaponAssetIndex ||
    client->second.client.gameplayState != Playing) return false;
auto &ps = owner.playerState;
if (ps.pmType == SvPmTypeDead || ps.currentWeaponAssetIndex != weaponAssetIndex ||
    ps.rewardActionType != 1 || ps.rewardActionWeapon != weaponAssetIndex ||
    std::ranges::none_of(ps.heldWeapons, [&](const auto &held) {
        return held.weaponAssetIndex == weaponAssetIndex;
    })) return false;
```

**⇒ 四项 + 六项 = 十项。**

**✅ 与 §366 的"十四项具名拒绝"**不同（这是**裸 false**）。**

**⚠ 而两处 `weaponAssetIndex != weaponAssetIndex`（当前 vs rewardAction）⇒ **三重一致性**。**

**✅ 与 §376 的"三重身份检查"**同族（**第四次）。**

### 7.1 而**"不清除当前选中的物品"**

```php
// IW4 _killstreaks.gsc shuffleKillStreaksFILO clears the action after
// successful use. It does not take the currently selected item away.
// CODDIFF: CODOL key4 is runtime action1 (checkpoint77), not IW4 slot4.
ps.rewardActionType = 0;
ps.rewardActionWeapon = 0;
```

**⇒ 五层**：

```text
1. **IW4 的 `shuffleKillStreaksFILO` 在成功使用后清除那个动作**
2. ⇒ **它【不】拿走当前选中的物品**
3. ⇒ **而 CODOL 的 `key4` 是 runtime `action1`（checkpoint77）**
4. ⇒ **不是 IW4 的 `slot4`**
5. ⇒ **所以只清 `rewardActionType` 与 `rewardActionWeapon`**
```

**✅ 与 §369 的"两个错位的位"**同族（**第二次"逐 build 的差异"）。**

## 八、关键结论

1. **⭐⭐ "只 `0 <-> 2`，绝不动其它任何值"`** —— 死亡写 `8`、比赛结束写 `5`、`laststand` 有自己的值，**踩它们会复活一具尸体或困住玩家**。
2. **⭐⭐ "『重生时回来』是一次【崩溃】，测量了两次"`** —— **离开 `pmType` 而有人死时是【挂起】，不是【结束】**。
3. **两次精确的崩溃**：`14:12:14` 摔死 → `14:12:17` 重生 → **`0xC0000005 read [0x00000018]`**；`14:32:05` → `14:32:08` → **`read [0x21CE9880]`**。
4. **⭐ "两个不同的故障，一个触发器"`** —— 第四次"一个触发器多个故障"。
5. **⭐ "热键是 `LEFT ALT` ⇒ 每一次 `ALT-TAB` 都切换 noclip ⇒ 把玩家扔穿地板（`org.z=-64`）⇒ 用摔落伤害杀死他们"`** —— 一个灾难性的键选择。
6. **"整个日志里存在四次摔落死，而那两个在这个窗口里的就是那两个崩溃的"`** —— 第十一次大规模统计（50% 相关）。
7. **⭐⭐ "『不是活着』意味着保持【结束】，不是挂起"`** —— 而 **500ms 的重复让释放安全**（玩家半秒内拿回）。
8. **⭐ "那个条目的【不在】就是你怎么知道这个守卫什么都没做"`** —— 第六次"定向的负面"。
9. **`setPlayerPodiumView` / `setPlayerKillCam` 的截断拒绝** —— 第五次"界=线宽"，而**两处都明说"截断成不同的号"**。
10. **`killCamEntityNum = 2047` 每一次**（demo 的全部八次）⇒ **相机不附着到一个实体，它被从其它三个放置** —— 第四次确认 `2047`。
11. **"四个一起归零，从不部分"`** —— 而 **`killCamEntity` 回到 `0` 而不是停在 `2047`** ∈ 一个**真实的非对称**。
12. **⭐ `compassRadarEnabled` = `playerState 86`**（demo 在 `648700` 清除）—— 与 §334 的"字段 86"**完全闭合**。
13. **⭐⭐ "相机是一个【地方】：只写 `pm_type` 而不移动 ⇒ 屏幕变了而视角没变，因为视角【就是】位置"`** —— **三个会话的代价**。
14. **"demo 的移动帧断言 81 个字段而那之前断言 15 个 ⇒ 下面的状态是【测量的集合】"`** —— 第十二次大规模统计。
15. **"`deltaAngles` 是真正转动客户端头的东西：没有它玩家继续看鼠标最后指的地方而【只有身体转】"`** —— 第二次确认那个身份。
16. **"漏掉视角高度就是【把相机放在地板上】的那个"`**（`viewHeightCurrent 40.00` / `viewHeightTarget 0`）。
17. **`equipPlayerEquipment` 的"同一职业重新发布 ⇒ 绝不补给一个用掉的投掷物"`**，而**同一世的不同职业是背包交换**。
18. **⭐ `SV_EquipOffhandLoadout` **只加不减** ⇒ 必须先 `SV_ClearOffhandLoadout`** —— 与 §366 的"先装后清"**相反的顺序**（共享 vs 独立）。
19. **"不登记进 MP 表 ⇒ `endFrame` 只认 Factory 池 ⇒ MP 投掷物不会被步进/引爆"`** —— 第七次"一个缺失的注册"。
20. **`consumePlayerUavAction` 的十项检查**含**三重 `weaponAssetIndex` 一致性**。
21. **"IW4 的 `shuffleKillStreaksFILO` 不清除当前选中物品；而 CODOL 的 `key4` 是 runtime `action1`，不是 IW4 的 `slot4`"`** —— 第二次"逐 build 差异"。

## 九、未闭合点

- `SvPmTypeNoclip` / `SvPmTypeIntermission` 的值（2 / 5）。
- `SvNoclipDefaultHoldMilliseconds` / `SvNoclipMaximumHoldMilliseconds` 的值。
- `holdMatchCompletionState` 的实现。
- `playerState 86` 与 `compassRadarEnabled` 的确认。
- `shuffleKillStreaksFILO` 的完整逻辑。
- `sv_snapshot_mp.cpp` 24000 行之后未读取（27,016 行，进度 89%）。
