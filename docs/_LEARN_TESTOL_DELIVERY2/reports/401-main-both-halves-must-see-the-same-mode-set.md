# 401 · **"要么两半都看到同一个模式集，要么两个都不工作"** —— 三次重复的"grant 无门控而 consume 有门控"、`u 11` 的首生/重生不对称

## 一、范围

本报告学习 `sv_main_mp.cpp` 3800–4150 行。

## 二、**"grant 无门控而 consume 有门控"的三次重复**（本组最重要的一段）

### 2.1 那段

```php
// OLMOD(killstreak-announcer, 20261014-1620): sd joined dm. The old
// dm-only gate produced the live defect the 14:54 sd session captured:
// grant runs UNGATED (the weapon flashes into the hand for a single
// snapshot), while consume sits behind this flag and never ran once,
// so owned rose, the UAV never opened a radar, and the earn/use
// announcer stayed silent behind the same flag. Both halves must see
// the same mode set or neither works; zm is excluded because its
// reward state is deliberately cleared every frame (see below).
// OLMOD(killstreak-announcer, 20261015-22230): cha joined dm+sd.
// The 20261014-1620 comment above records the exact defect this gate
// produced once already for sd, and a live cha session on 2026-10-15
// reproduced it a third time: "grant runs UNGATED ... while consume
// sits behind this flag and never ran once, so owned rose, the UAV
// never opened a radar". The operator's report is "无人机失效".
const bool uavRadarEnabled = uavRadarDuration_ &&
    (matchGameType_ == "dm" || matchGameType_ == "sd" ||
        matchGameType_ == "cha" || uavRadarTestOverride_);
```

### 2.2 十八层

```text
1. **sd 加入了 dm**（`20261014-1620`）
2. ⇒ **旧的 dm-only 门控产生了 `14:54` sd 会话捕获的那个活缺陷**：
3. ⇒ **`grant` 运行【无门控】**（武器在手里闪一个快照）
4. ⇒ **而 `consume` 坐在这个标志后面【一次也没跑过】**
5. ⇒ **所以 `owned` 上升、UAV 从未打开一个雷达、而 earn/use 宣告者【在同一个标志后面静默】**
6. ⇒ **两半必须看到【同一个模式集**】否则两个都不工作**
7. ⇒ **zm 被排除因为它的 reward 状态【故意每帧清空】**
8. ⇒ **cha 加入了 dm+sd**（`20261015-22230`）
9. ⇒ **上面那段注释记录了这个门控【已经为 sd 产生过一次】的同一个缺陷**
10. ⇒ **而 2026-10-15 的一次活 cha 会话【第三次】复现它**：
11. ⇒ **"`grant` 运行无门控……而 `consume` 坐在这个标志后面一次也没跑过，所以 `owned` 上升，UAV 从未打开一个雷达"**
12. ⇒ **操作员的报告是"无人机失效"**
13. ⇒ **`configureGameState` 【已经】把 sd、cha 与 dm 当作同一个计分家族**（`:1656`）
14. ⇒ **所以这个门控现在【匹配它】**
15. ⇒ **zm 保持排除**（理由见下面的注释）
```

### 2.3 ⭐⭐⭐ **"同一个缺陷第三次"**

**✅ 这是本文件里**最重要的一个"同一 bug 反复出现"的记录**。**

**⇒ 三层**：

```text
20261014  sd   ⇒ 第一次
20261015  cha  ⇒ **第三次**（注释说"已经为 sd 产生过一次"而这次又一次）
⇒ **⇒ 而两次的原因【完全相同**】
```

**✅ 与 §384 的"是 `-75` 自己的注释记录的【同一类错误】"**同族（**第三次"同一 bug 重复"）。**

**⚠ 而"grant 无门控而 consume 有门控"⇒ **一个不对称的模式集**。**

**⇒ 三层**：

```text
`grant`（发武器）⇒ **无门控 ⇒ 每个模式都跑**
`consume`（用 UAV）⇒ **有门控 ⇒ 只在 dm**
⇒ **⇒ 武器发了而永远用不掉**
```

**✅ ⭐ **"要么两半都看到同一个模式集，要么两个都不工作"** —— 一个**极清晰的对称性判据**。**

**✅ 与 §391 的"两个生成路径都必须门控"**同族（**第四次"对称性"）。**

### 2.4 而**"武器在手里闪一个快照"**

**✅ 与 §344 的"一个活玩家的 `modelIndex` 被断言一次然后静默"**同族（**第十次"单次闪现"）。**

**⇒ 三层**：

```text
`grant` 发武器 ⇒ **武器进入玩家手里**
⇒ **而 `consume` 不跑 ⇒ 它【永远不被使用】**
⇒ **而下一个 `grant` 覆盖它 ⇒ 闪一下就没了**
```

**✅ ⭐ **一个"半功能"的具体表现**。**

### 2.5 而**"zm 的 reward 状态故意每帧清空"**

**✅ 与 §401 五的"zm 的 `clearPlayerRewardState` 每帧"**完全闭合 ✓

**⇒ 三层**：

```text
zm ⇒ `clearPlayerRewardState` 【每帧】
⇒ **所以 zm 的任何 reward 都不可能存活**
⇒ **⇒ 所以支持它没有意义**
```

**✅ 一个**正确的排除理由**。

## 三、**UAV 的完整状态机**（本组第二重要）

### 3.1 六个字段

```cpp
struct UavOwner {
    uint64 xuid;
    SvUavEarningState state;     // owned / grantedLife
    optional<uint16> weapon;
    vector<uint32> radarExpiries;
    uint16 lastGun;              // 上一次持有的枪
    optional<uint8> committedLife;
    uint16 committedWeapon;
    bool returning, returnQueued;
    bool radarManaged;
    bool testRewardGranted;
};
```

**⇒ 十一个字段。**

### 3.2 而**`observeUavWeaponChanges` 的四层**

```php
auto &owner = uavOwners_[event.clientNum];
const auto xuid = clients_.clients()[event.clientNum].xuid;
if (owner.xuid != xuid) owner = {xuid, {}};
if (owner.committedLife != event.spawnGeneration) {
    owner.lastGun = 0;
    owner.returning = owner.returnQueued = false;
}
owner.committedLife = event.spawnGeneration;
owner.committedWeapon = event.weaponAssetIndex;
if (event.weaponAssetIndex && event.weaponName != "killstreak_uav_mp") {
    owner.lastGun = event.weaponAssetIndex;
    owner.returning = owner.returnQueued = false;
}
```

**⇒ 七层**：

```text
1. **`xuid` 变 ⇒ 整个重置**
2. ⇒ **`spawnGeneration` 变 ⇒ 清 `lastGun` 与返回标志**
3. ⇒ **记 `committedLife` 与 `committedWeapon`**
4. ⇒ **而若新武器不是 UAV ⇒ 记 `lastGun` 并清返回标志**
5. ⇒ **所以 `lastGun` 是"上一把真枪"**
6. ⇒ **⇒ 用于 UAV 用完后把枪还给玩家**
```

**✅ ⭐ **一个"用完还枪"的设计**（`a <lastGun>`）。**

**⚠ 而"`event.weaponName != "killstreak_uav_mp"`"⇒ **一个按名字的排除**。**

**✅ 与 §391 的"`killstreak_uav_mp`"**完全闭合 ✓

**⇒ **第二次确认那个名字。**

### 3.3 而**雷达强度的三值**

```php
// INFERRED test values: native bit0 enables radar and mask0C
// selects normal/fast sweep (checkpoint74). IW4 FFA counts UAVs
// per GUID and preserves active aircraft across the owner's death.
const auto radar = owner.radarExpiries.empty() ? 0 :
    owner.radarExpiries.size() == 1 ? 5 : 9;
```

**⇒ 六层**：

```text
1. **`bit0` 启用雷达而 `mask0C` 选择正常/快速扫描**（`checkpoint74`）
2. ⇒ **IW4 FFA 【按 GUID】计 UAV**
3. ⇒ **并在所有者的死亡【之后】保留活动的飞机**
4. ⇒ **所以三值**：`0`（无）/ `5`（一个）/ `9`（两个或更多）
5. ⇒ **而 `5` = `0b0101` / `9` = `0b1001`** ⇒ **`bit0` 都置位，而 `bit2`（`0x4`）区分**
```

**✅ ⭐ **一个从位掩码反推的语义**（`mask0C` 是 `0b1100`，而 `5` 与 `9` 差 `0x4`）。**

**⚠ 而"`5 = 0b101` 与 `9 = 0b1001`"⇒ **

**⇒ 让我核算：`5 = 0b0101`（bit0 + bit2），`9 = 0b1001`（bit0 + bit3）。**

**⇒ 所以 `mask0C = 0b1100` 而 `5` 置了 bit2、`9` 置了 bit3。**

**✅ **两个位**（`0x4` 与 `0x8`）而 `5` 与 `9` 分别是"置 `0x4`"与"置 `0x8`"。**

**⚠ 而"`mask0C` 选择正常/快速"⇒ **`0x4` 是"一个"而 `0x8` 是"两个或更多"**。**

**✅ 一个**精确的位语义**。

## 四、**`consume` 的八项前置**（本组第三重要）

### 4.1 那段

```php
if (uavRadarEnabled && !owner.returning && owner.weapon && heldGun &&
    owner.state.owned && owner.state.grantedLife == ps->spawnGeneration &&
    owner.committedLife == ps->spawnGeneration &&
    owner.committedWeapon == owner.weapon->weaponAssetIndex &&
    ps->currentWeaponAssetIndex == owner.committedWeapon)
{
    // A committed end-frame notification is required, not a
    // requested usercmd or WeaponSwitchStarted. The next fixed
    // frame supplies the IW4 waittillframeend use boundary.
    ...
    if (world_.consumePlayerUavAction(client.clientNum, owner.weapon->weaponAssetIndex))
    {
        owner.radarExpiries.push_back(now + uavRadarDuration_);
        --owner.state.owned;
        owner.state.grantedLife.reset();
        owner.returning = true;
        ...
    }
}
```

### 4.2 十二层

```text
1. **八项前置**：
      · 雷达启用 / 不在返回中 / 有武器 / **持有那把枪**
      · `owned` 非零 / `grantedLife` 匹配
      · `committedLife` 匹配 / `committedWeapon` 匹配
      · **`currentWeaponAssetIndex` == `committedWeapon`**（**第三重武器检查**）
2. ⇒ **"一个已提交的 end-frame 通知是必需的，不是一个请求的 usercmd 或 `WeaponSwitchStarted`"**
3. ⇒ **"下一个固定帧提供 IW4 的 `waittillframeend` 使用边界"**
4. ⇒ **所以 consume 在【下一个帧】而不是当前**
5. ⇒ **成功后三件事**：加到期 / 减 `owned` / 清 `grantedLife`
6. ⇒ **并设 `returning = true`**（进入还枪路径）
7. ⇒ **并立刻设雷达位**
8. ⇒ **并播使用音**
```

**✅ ⭐ **"`waittillframeend` 使用边界"** —— 一个**一帧延迟的语义**。**

**⚠ 而"第三重武器检查"⇒ **三重一致性**（`committedWeapon` / `weapon->weaponAssetIndex` / `currentWeaponAssetIndex`）。**

**✅ 与 §376 的"三重身份检查"**同族（**第五次）。**

### 4.3 而**"不要在一个排队的充能上重新授予而仍持有 UAV"**

```php
if (owner.returning)
{
    // Do not re-grant a queued charge while still holding UAV:
    // re-enabling it can otherwise auto-consume the next reward.
    // Reliable queue failure retries without spending again.
    if (!owner.returnQueued && heldGun)
        owner.returnQueued = clients_.queueReliableCommand(client.clientNum,
            "a " + std::to_string(owner.lastGun));
    continue;
}
```

**⇒ 六层**：

```text
1. **不要在一个排队的充能上重新授予而仍持有 UAV**
2. ⇒ **重新启用它否则能【自动消费下一个 reward】**
3. ⇒ **可靠队列失败【不重复花费】地重试**
4. ⇒ **所以 `returnQueued` 是一个"已排队"标志**
5. ⇒ **而 `continue` 跳过授予**
```

**✅ ⭐ **"可靠队列失败不重复花费地重试"** —— 一个**精确的成本保证**。**

**✅ 与 §392 的"一次没到达任何人的写绝不能锁存"**同族（**第二次"失败可重试"）。**

## 五、**`driveClientPerks` 的 zm 五层排除**（本组第四重要）

### 5.1 那段

```php
// Zombie Siege has no multiplayer reward loadout. Clear all five
// runtime slots, not only the three profile-owned slots: slots 0/4
// can retain state from the front-end/player profile and make the
// client draw the vertical MP scorestreak stack in a zm match.
// Repeat before every fixed-frame projection because native Pmove
// imports the client's predicted playerState between snapshots.
if (matchGameType_ == "zm")
    (void)world_.clearPlayerRewardState(client.clientNum);
```

### 5.2 九层

```text
1. **僵尸围城【没有】多人 reward 装备**
2. ⇒ **清全部【五个】运行时槽，不只是三个 profile 拥有的**
3. ⇒ **因为槽 `0/4` 能从前端/玩家 profile 保留状态**
4. ⇒ **并让客户端在 zm 比赛里画【垂直的 MP 连杀栈】**
5. ⇒ **在每个固定帧投影【之前】重复**
6. ⇒ **因为原生 `Pmove` 在快照之间【导入客户端的预测 playerState】**
7. ⇒ **所以必须每帧清**
```

**✅ ⭐ **"槽 `0/4` 能从前端/玩家 profile 保留状态"** —— 与 §390 的"槽 `0` 与 `4` 有独立所有者"**完全闭合 ✓

**⇒ **第二次确认那五个槽。**

**⚠ 而"原生 `Pmove` 在快照之间导入客户端的预测 `playerState`"⇒ **所以每帧清是必需的**。**

**✅ 与 §371 的"世界从 pmove 重建 `playerState`"**完全一致 ✓

**⇒ **第五次确认那个机制。**

### 5.3 而**zm 的第二个 `continue`**

```php
if (matchGameType_ == "zm")
{
    // Zombie perks are bought from map machines and persist only
    // for this life. Applying the selected multiplayer class here
    // overwrote those purchases a moment later and also exposed MP
    // perk presentation in Zombie Siege. Spawn/death already clears
    // ps.perks; leave the live machine-owned mask alone.
    perkLives_.erase(client.clientNum);
    (void)world_.setPlayerAbilities(client.clientNum, {});
    (void)world_.setPlayerEquippedRewards(client.clientNum, {}, {});
    continue;
}
```

**⇒ 七层**：

```text
1. **僵尸技能从地图机柜购买并【只在这一世】持续**
2. ⇒ **在这里应用选中的多人职业【片刻之后覆盖那些购买】**
3. ⇒ **并【在僵尸围城里暴露 MP 技能表现】**
4. ⇒ **spawn/death 已经清 `ps.perks`**
5. ⇒ **所以【让活动的机柜拥有的掩码独处】**
6. ⇒ **而 `setPlayerAbilities({})` 与 `setPlayerEquippedRewards({}, {})` 仍调**
7. ⇒ **⇒ 清 MP 侧但不清机柜侧**
```

**✅ ⭐ **"让活动的机柜拥有的掩码独处"** —— 一个**精确的职责边界**。**

**⚠ 而"spawn/death 已经清 `ps.perks`"⇒ **与 §384 的"`perks = {}` 在死亡时"**完全闭合 ✓

**⇒ **第二次确认。**

### 5.4 而 `driveClientPerks` 的**四个条件重解析**

```cpp
if (life == perkLives_.end() || life->second.xuid != slot.xuid ||
    life->second.spawnGeneration != playerState->spawnGeneration ||
    life->second.selectedLoadout != slot.selectedLoadout)
```

**⇒ 与 §400 的"`driveClientEquipment` 的四个条件"**完全同构 ✓

**⇒ **第三次确认那个四元组**（无记录 / `xuid` / `spawnGeneration` / `selectedLoadout`）。**

### 5.5 而**"`assertAt = serverTime + SvPerkAssertDelayMilliseconds`"**

```cpp
life = perkLives_.insert_or_assign(client.clientNum, PerkLife{
    .xuid = slot.xuid,
    .spawnGeneration = playerState->spawnGeneration,
    .selectedLoadout = slot.selectedLoadout,
    .assertAt = serverTime + SvPerkAssertDelayMilliseconds,
    .perks = *perks,
    .persistentRewards = rewards && rewards->persistentCosts,
}).first;
...
if (state.asserted || serverTime < state.assertAt) continue;
if (world_.setPlayerPerks(client.clientNum, state.perks.bits)) {
    state.asserted = true;
    write("perks asserted client=... bits=...");
}
```

**⇒ 七层**：

```text
1. **能力【立即设】**（`setPlayerAbilities`）
2. ⇒ **而 `perks.bits` 【延迟】`SvPerkAssertDelayMilliseconds` 后设**
3. ⇒ **所以是"能力先、位后"**
4. ⇒ **而 `asserted` 保证只设一次**
5. ⇒ **⇒ 一个"两阶段断言"**
```

**✅ ⭐ **一个"延迟断言"的精确设计**（可能为了等 pmove 稳定）。**

**⚠ 而"`persistentRewards = rewards && rewards->persistentCosts`"⇒ **一个 bool**。**

**✅ 与 §401 三的"`eligible` 用 `!persistentRewards`"**完全闭合 ✓

## 六、**UI 屏幕序列的逐字复制**（本组第五重要）

### 6.1 那段（第一半）

```php
// THE SEQUENCE BELOW IS COPIED FROM THE DEMO, NOT COMPOSED. See
// re/demo-re/12-dm-timeline.txt: the first spawn puts u 11 FIRST and
// sends no u 9, and every one of the 24 respawns puts it LAST and does.
// That asymmetry is measured, so it is reproduced rather than tidied
// away. What each index MEANS is section 109d's co-occurrence reading
// and is INFERRED - which is why this sends the retail sequence exactly
// instead of picking indices that seem right.
//
// MEASURED (12-dm-timeline.txt seq 15/16/17, serverTime 43100): the
// connect trio rides in the SAME message as the gamestate, before any
// spawn. Verified in out.exe rather than assumed: `9` is a sub-verb
// dispatcher (sub_60D210) over six tokens -- ready, cinematic_wait,
// purchase, consume, refresh_loadouts, and a numeric default -- and
// `ready` is the cheapest of them: it sets ONE byte, HIBYTE of
// word_34F41A8, which sub_5C98C0 hands to the UI as a variant. So
// `9 ready 0` tells the client's menus the server is ready and does
// nothing else. Its `0` argument is read by the OTHER branches only.
//
// CORRECTS SECTION 109c on one point: it is `9 cinematic_wait`, not
// `9 ready`, that builds "cmd mr %i %i cinematic_done" -- so the
// connect trio does NOT close the request/response loop. Nothing here
// depends on a reply; SV_ParseMenuResponse still has no asker.
static constexpr std::array ConnectScreens{
    "9 ready 0", "q 3", "u 18" };
static constexpr std::array FirstSpawnScreens{
    "u 11", "r 2", "r 3", "r 1", "v 18" };
```

### 6.2 十八层

```text
1. **下面的序列【从 demo 复制】，不是【组合】的**
2. ⇒ **（`re/demo-re/12-dm-timeline.txt`）**
3. ⇒ **第一次出生把 `u 11` 放【第一个】而【不发 `u 9`】**
4. ⇒ **而 24 次重生里的【每一次】把它放【最后】而【发它】**
5. ⇒ **那个不对称是【测量的**】**
6. ⇒ **所以它被【复现】而不是被"整理掉"**
7. ⇒ **每个索引【意味着】什么是第 109d 节的共现读法而它是【推断的】**
8. ⇒ **所以这发送零售序列【精确地】而不是挑看起来对的索引**
9. ⇒ **`12-dm-timeline.txt` 的 seq `15/16/17`（`serverTime 43100`）**
10. ⇒ **连接三件套【与 gamestate 同一条消息】，在任何出生之前**
11. ⇒ **在 `out.exe` 里【验证】而不是假设**：
       · **`9` 是一个子动词派发器（`sub_60D210`）跨六个 token**
       · **`ready` / `cinematic_wait` / `purchase` / `consume` / `refresh_loadouts` / 一个数字默认**
12. ⇒ **而 `ready` 是最便宜的那个**：
       · **它设【一个字节】**（`word_34F41A8` 的 **`HIBYTE`**）
       · **而 `sub_5C98C0` 把它作为【一个变体】交给 UI**
13. ⇒ **所以 `9 ready 0` 告诉客户端菜单"服务器就绪"而【什么也不做别的】**
14. ⇒ **它的 `0` 参数【只】被其它分支读**
15. ⇒ **更正第 109c 节的一点**：**是 `9 cinematic_wait` 而不是 `9 ready` 构造 `cmd mr %i %i cinematic_done`**
16. ⇒ **所以连接三件套【不】关闭那个请求/响应回路**
17. ⇒ **什么都【不】依赖一个回复**
18. ⇒ **`SV_ParseMenuResponse` 【仍】没有询问者**
```

### 6.3 ⭐⭐ **"那个不对称是测量的，所以它被复现而不是被整理掉"**

**✅ 这是本文件里**最重要的一个"不要整理"的陈述**。**

**⇒ 三层**：

```text
首生：`u 11` 第一，无 `u 9`
重生：`u 11` 最后，有 `u 9`
⇒ **一个不对称**
⇒ **而它被【复现】而不是被"整理成一致"**
```

**✅ 与 §350 的"不要一般化这个例外"**同族（**第四次"不要整理"）。**

**⚠ 而"每个索引意味着什么是【推断的】"⇒ **所以只复现序列不发明语义**。**

**✅ 与 §370 的"去问键盘不要问镜像"**同族（**第八次"只复现不发明"）。**

### 6.4 而 **`9` 的六个子动词**

```text
ready                ⇒ 设 HIBYTE of word_34F41A8（一个字节）
cinematic_wait       ⇒ **构造 `cmd mr %i %i cinematic_done`**
purchase
consume
refresh_loadouts
数字默认
```

**⇒ 三层**：

```text
1. **`ready` 最便宜**（一个字节）
2. ⇒ **`cinematic_wait` 才构造那个响应**
3. ⇒ **所以"连接三件套不关闭回路"**
```

**✅ ⭐ **一个"最便宜的子动词"** —— 一个**精确的成本选择**。**

**⚠ 而"更正第 109c 节"⇒ **一个自我更正**。**

**✅ 与 §384 的"一个编解码器不是一个类型"**同族（**第六次自我更正）。**

### 6.5 而**四套 gametype 序列**

```text
dm  ：`9 ready 0` / `q 3` / `u 18`（连接）+ `u 11`/`r 2`/`r 3`/`r 1`/`v 18`（首生）
dmz ：`9 ready 0` / `L 13 6`（连接）+ `r 2`/`r 3`/`r 1`/`v 18`/`u 11`/`I 0 0 0`
cha ：`9 ready 0` / `q 3` / `u 18`（**`q` 取值是 3**）
```

### 6.6 而**"dmz 的三个差异，全都是我们该修的"**

```php
// Three differences, all of them ours to fix: retail's dmz join sends `L 13 6`
// and `I 0 0 0`, sends NEITHER `q 2` NOR `u 18`, and orders `u 11` AFTER the
// r/v cluster rather than before it. We sent the dm sequence on every map.
//
// WHY IT MATTERS: on mp_battlecity the client took the gamestate and then never
// sent a usercmd (no `pmove-slice`) and never acked a baseline (no
// `snapshot baseline source=acked`), so no playerstate was ever built for it --
// `snapshot build rejected failure=missing_playerstate init=1` -- and it ended on
// 无法加入游戏会话, "Unable to join game session". mp_nuked on the same stack minutes
// later produced all of those lines. A client waiting on a handshake it never
// receives is exactly that shape.
```

**⇒ 十六层**：

```text
1. **三个差异，全都是【我们该修的】**
2. ⇒ **零售的 dmz 加入发 `L 13 6` 与 `I 0 0 0`**
3. ⇒ **【既不】发 `q 2`【也不】发 `u 18`**
4. ⇒ **而把 `u 11` 排在 r/v 簇【之后】而不是之前**
5. ⇒ **我们把 dm 序列发在【每一张地图】上**
6. ⇒ **为什么重要**：**在 `mp_battlecity` 上客户端拿了 gamestate 然后【从不】**发 usercmd**（无 `pmove-slice`）**
7. ⇒ **而【从不】ack 一个基线**（无 `snapshot baseline source=acked`）
8. ⇒ **所以【从未为它构建任何 `playerstate`】**
9. ⇒ **（`snapshot build rejected failure=missing_playerstate init=1`）**
10. ⇒ **而它结束在 `无法加入游戏会话` / "Unable to join game session"**
11. ⇒ **`mp_nuked` 在同一栈上几分钟后【产生了所有那些行】**
12. ⇒ **一个等待它永远收不到的握手的客户端【正是那个形状**】
```

**✅ 与 §377 的"`NO WORLD STATE` 的六级死锁链"**完全同族（**第六次"握手死锁"）。**

**⇒ 三层**：

```text
§377  缺世界状态 ⇒ 快照拒 ⇒ 无 ack ⇒ 永远 FULL
§401  **缺 UI 握手** ⇒ 无 usercmd ⇒ 无 ack ⇒ `missing_playerstate` ⇒ **无法加入**
⇒ **两个不同的缺失、同一条死锁链**
```

**✅ ⭐ **"一个等待它永远收不到的握手的客户端正是那个形状"** —— 一个**极精确的诊断**。**

## 七、关键结论

1. **⭐⭐⭐ "同一个缺陷第三次"`** —— **`grant` 无门控而 `consume` 有门控**，为 **sd（20261014）** 产生过一次，而 **cha（20261015）** 又复现一次。
2. **⭐⭐ "要么两半都看到同一个模式集，要么两个都不工作"`** —— 一个**对称性判据**，而**操作员的报告是"无人机失效"**。
3. **"武器在手里闪一个快照"** —— 一个"半功能"的具体表现。
4. **"zm 的 reward 状态故意每帧清空"** ⇒ **所以支持它没有意义**。
5. **⭐ UAV 的十一个状态字段**，而 `observeUavWeaponChanges` 的"`xuid` 变 ⇒ 整个重置 / `spawnGeneration` 变 ⇒ 清 `lastGun`" 与 **"新武器不是 UAV ⇒ 记 `lastGun`"** ⇒ **一个"用完还枪"的设计**（`a <lastGun>`）。
6. **⭐ 雷达强度的三值**（`0` / `5` / `9`）从位掩码反推：**`bit0` 启用雷达而 `mask0C`（`0x4` 一个 / `0x8` 两个或更多）**。
7. **"IW4 FFA 按 GUID 计 UAV 并在所有者的死亡之后保留活动的飞机"`**。
8. **⭐ `consume` 的八项前置**含**第三重武器检查**（`committedWeapon` / `weapon->weaponAssetIndex` / `currentWeaponAssetIndex`）—— 第五次"三重一致性"。
9. **⭐ "一个已提交的 end-frame 通知是必需的，不是一个请求的 usercmd 或 `WeaponSwitchStarted`；下一个固定帧提供 IW4 的 `waittillframeend` 使用边界"`** —— 一个**一帧延迟的语义**。
10. **"不要在一个排队的充能上重新授予而仍持有 UAV：重新启用它能自动消费下一个 reward；可靠队列失败不重复花费地重试"`** —— 第二次"失败可重试"。
11. **⭐⭐ `driveClientPerks` 的 zm 五层排除**：**"清全部五个运行时槽，不只是三个 profile 拥有的，因为槽 `0/4` 能从前端/玩家 profile 保留状态并让客户端在 zm 里画垂直的 MP 连杀栈"`** —— 第二次确认那五个槽。
12. **"在每个固定帧投影之前重复，因为原生 `Pmove` 在快照之间导入客户端的预测 `playerState`"`** —— 第五次确认那个机制。
13. **⭐ "让活动的机柜拥有的掩码独处"`** —— 一个精确的职责边界（清 MP 侧但不清机柜侧）。
14. **第三个"四元组重解析"**（`driveClientEquipment` / `driveClientPerks` / 无记录 / `xuid` / `spawnGeneration` / `selectedLoadout`）。
15. **⭐ "能力立即设而 `perks.bits` 延迟 `SvPerkAssertDelayMilliseconds` 后设"`** —— 一个"两阶段断言"。
16. **⭐⭐ "那个不对称是测量的，所以它被【复现】而不是被【整理掉】"`** —— `u 11` 首生第一无 `u 9`、重生最后有 `u 9`（**24 次重生全部一致**）。
17. **"每个索引意味着什么是推断的 ⇒ 所以这发送零售序列【精确地】而不是挑看起来对的索引"`** —— 第八次"只复现不发明"。
18. **⭐ `9` 的六个子动词**（`ready` / `cinematic_wait` / `purchase` / `consume` / `refresh_loadouts` / 数字默认），而 **`ready` 是最便宜的**（**只设 `word_34F41A8` 的 `HIBYTE` 一个字节**）。
19. **⭐ "更正第 109c 节的一点：是 `9 cinematic_wait` 而不是 `9 ready` 构造 `cmd mr %i %i cinematic_done` ⇒ 连接三件套不关闭那个请求/响应回路"`** —— 第六次自我更正。
20. **⭐⭐ "dmz 的三个差异全都是我们该修的"`**，而 **"在 `mp_battlecity` 上客户端拿了 gamestate 然后从不发 usercmd、从不 ack 一个基线 ⇒ 从未构建任何 `playerstate` ⇒ `无法加入游戏会话`；而 `mp_nuked` 在同一栈上产生了所有那些行"`** —— **第六次"握手死锁"**，而 **"一个等待它永远收不到的握手的客户端正是那个形状"`**。

## 八、未闭合点

- `SvUavEarningState::observe` 的完整逻辑。
- `UINT32_MAX` 在 `owner.state.owned` 上的哨兵语义。
- `SvPerkAssertDelayMilliseconds` 的值。
- `L 13 6` 与 `I 0 0 0` 的语义（未解码）。
- `cha` 的完整序列（`q 3` 之后）。
- `sv_main_mp.cpp` 4150 行之后未读取。
