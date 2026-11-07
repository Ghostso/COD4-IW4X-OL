# 485 · **"一个被持有的复活暂停流血；它**不能**被持有【在没有【新鲜的已提交命令、距离与一个存活的索取者**的情况下**"** —— `sv_zm_revive_mp.cpp` 的 `i 1000 2.000000 0 1`、`90` 发备弹、以及"一个快照**是**一个摄像机，不是一个生命"

## 一、范围

本报告学习 `sv_zm_revive_mp.cpp`（**`357` 行**）全文件：倒地清单的保存/恢复、`sendZombieDownedPresentation` 的四条命令、`SV_PlayerSnapshotView` 的三层重写（跟随/回放/双冻结）、复活索取的四道门、以及 `stepZombieRevives` 的五个状态。

## 二、**"一个被持有的复活暂停流血；它不能被持有没有新鲜的已提交命令、距离与一个存活的索取者"**（本组最重要的一段）

### 2.1 那段

```cpp
// A held revive pauses bleedout. It cannot be held without fresh
// committed commands, range and a surviving claimant.
if (down.reviver) continue;
if (now - down.downedAt < SvZombieBleedoutMilliseconds) continue;
```

### 2.2 二十四层

```text
1. **一个被持有的复活【暂停【流血**】
2. ⇒ **⇒ 而它【不能【被持有【没有【三个条件**】
3. ⇒ **① 新鲜的已提交命令**
4. ⇒ **② 距离**
5. ⇒ **③ 一个存活的索取者**
6. ⇒ **⇒ 所以【那个"暂停"【不是【一个**免费的**状态**】
```

### 2.3 ⭐⭐⭐ **"一个被持有的复活暂停流血，而它不能被持有没有那三个条件"**

**✅ 这是本报告里**最重要的一条"**一个**暂停【必须【被【三个**独立条件**维持**"**。**

**✅ 与 §483 的"那些权限三道在扣钱之前"**、§475 的"关闭是幂等性的唯一保证"**——**同族** ✓

**⇒ 三层**：
```text
若【只有 `down.reviver` 一个字段**】⇒ **⇒ 一个**断线的**帮手【能【永久**暂停流血**
三个条件 ⇒ **⇒ 无**漏洞**
⇒ **⇒ 所以【那个"暂停"【是一个**受约束的**状态**
```

**✅ ⭐⭐⭐ **"那个暂停是一个受约束的状态"**。

**⚠ 而那三个条件的**实现**】**。**

**⇒ 十六层**：
```text
① 新鲜 ⇒ **`now - down.lastSeen > 500` ⇒ `down.cancel()`**】（**`stepZombieRevives`**）
② 距离 ⇒ **`zombieReviveTarget(*down.reviver) != clientNum` ⇒ `down.cancel()`**】
③ 存活 ⇒ **`zombieReviveTarget` 【检查【那个帮手【活着**】（`!health` ⇒ `nullopt`**）**
⇒ **⇒ 所以【三个条件【全部【在【那个每帧循环里【被【检查**】
```

**✅ ⭐⭐⭐ **"三个条件全部在那个每帧循环里被检查"**。

**✅ 而"`500` 毫秒"**⇒ **一个**极短的**窗口**。**

**⇒ 十层**：
```text
`500ms` ⇒ **@ 30Hz ⇒ `15` 帧**
⇒ **⇒ 所以【一个帮手【必须【每 `15` 帧【至少【提交一次**】
⇒ **⇒ 而【一个**已提交**的命令【意味着【那个 usercmd 【被【执行**了**
```

**✅ ⭐⭐⭐ **"一个帮手必须每 15 帧至少提交一次"** —— 与 §483 的"`4,253` 次 usercmd 丢弃"**同族**（**第五次"一个**已提交命令**"**）。

**✅ 而与 §472 的"`PendingUserCmdCapacity = 32`"**——**配合**（**`500ms` 内【最多 `15` 个命令**）**。**

## 三、**`i 1000 2.000000 0 1` 与 `3 "grayscale" 1000`**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(613A40): 'i' ->611920 parses duration,blur,flags,priority;
// '3' ->46CEF0 type5. Exact original Factory down/revive command pair.
reliableCommandSender_(client, downed ? "i 1000 2.000000 0 1" : "i 100 0.000000 0 1");
if (downed) reliableCommandSender_(client, "3 \"grayscale\" 1000");
else reliableCommandSender_(client, "3 \"zm_factory_sh\" 0");
if (weapon) reliableCommandSender_(client, "a " + std::to_string(weapon));
if (const auto owner = clientStates_.find(client); owner != clientStates_.end())
    reliableCommandSender_(client, "y " + std::to_string(owner->second.client.playerState.offhandWeaponAssetIndex));
```

### 3.2 二十四层

```text
1. **`'i'` ⇒ 一个【四字段**的解析**（`duration` / `blur` / `flags` / `priority`**）**
2. ⇒ **⇒ 倒地 ⇒ `1000` / `2.000000` / `0` / `1`**（**1 秒 / 模糊 2.0**）**
3. ⇒ **⇒ 复活 ⇒ `100` / `0.000000` / `0` / `1`**（**0.1 秒 / 无模糊**）**
4. ⇒ **⇒ 而 `'3'` ⇒ 一个**类型 5** 的视觉改变**】
5. ⇒ **⇒ 倒地 ⇒ `"grayscale"` `1000`**】
6. ⇒ **⇒ 复活 ⇒ `"zm_factory_sh"` `0`**】（**⇒ 恢复【那个地图自己的**色调**）**
```

### 3.3 ⭐⭐⭐ **"复活时把视觉改回 `"zm_factory_sh"`"**

**✅ 与 §470 的"六条 vision 的 `"<mapname>" 0`"**——**完全闭合** ✓

**⇒ 三层**：
```text
§470  **`VisionNakedConfigStringIndex` ⇒ `"<mapname>" 0`**（**六条**）
§485  **`'3' "zm_factory_sh" 0`**（**复活时**）
⇒ **⇒ 所以【那条复活命令【恢复【那个**地图的色调**】
```

**✅ ⭐⭐⭐ **"那条复活命令恢复那个地图的色调"** —— 一个**跨报告的闭合**。

**⚠ 而"`'i'` 的 `priority = 1` 两次都一样"**⇒ **一个**恒定的**优先级**。**

**⇒ 十层**：
```text
倒地 ⇒ **`priority 1`**
复活 ⇒ **`priority 1`**
⇒ **⇒ 所以【那个优先级【不是【一个**区分**的因素**
```

**✅ ⭐⭐ **"那个优先级不是一个区分的因素"**。

**⚠ 而那个 `'a'` 与 `'y'` 的两条**】**。**

**⇒ 三层**：
```text
`'a' <weapon>` ⇒ **那个当前武器**】
`'y' <offhand>` ⇒ **那个副武器槽**】
⇒ **⇒ 所以【两条【更新【那两个**展示字段**】
```

**✅ ⭐⭐⭐ **"两条更新那两个展示字段"** —— 而**§474 的 `'a'`** **同族**（**第二次"一个**单字母命令**"**）。

**✅ 而与 §462 的 `y 906`**⇒ **一个**对照**（**那里【从未发过**，这里【每**次复活【发**）**。**

**⇒ 三层**：
```text
§462  **`y 906` 【从未【被【这个服务器【发过**】（**三个未发动词之一**）
§485  **`y <offhand>` 【每次【复活**都发**
⇒ **⇒ 所以【`y` 【是【一个**活的**命令**】⇒ **⇒ 而【`906` 【是【一个**特定参数**】
```

**✅ ⭐⭐⭐ **"`y` 是一个活的命令，而 `906` 是一个特定参数"** —— **一个跨报告的精化**。

## 四、**`90` 发备弹与"独立的全手枪弹匣"**（本组第三重要）

### 4.1 那段

```cpp
// CODREF(original Factory60150/514050): hide ordinary weapons, independent
// full pistol clip and90 reserve; restore pre-down ammo at72750/521150.
// Pistol preference beyond the two observed loadouts remains reconstruction.
...
ps.heldWeapons = {}; ps.ammoClips = {}; ps.ammoPools = {};
ps.heldWeapons[0].weaponAssetIndex = pistol->weaponAssetIndex;
ps.heldWeapons[0].heldBefore = true;
ps.ammoClips[0].clipIndex = pistol->clipIndex;
ps.ammoClips[0].count[0] = pistol->clipSize;
ps.ammoPools[0].ammoIndex = pistol->ammoIndex; ps.ammoPools[0].count = 90;
```

### 4.2 二十四层

```text
1. **隐藏【普通武器**】
2. ⇒ **⇒ 一个【独立的【满手枪弹匣**】
3. ⇒ **⇒ 而【`90` 发备弹**】
4. ⇒ **⇒ 而【在复活时【恢复【倒地前的**弹药**
5. ⇒ **⇒ 所以【那个 `90` 【是【一个**测量的**数**】（不是【`maxAmmo`**）**
```

### 4.3 ⭐⭐⭐ **"90 发备弹是一个测量的数，不是 maxAmmo"**

**✅ 与 §483 的"那个结构体默认值 `250/100/0` 是源自己的"**——**同族**（**第六次"一个**测量的**常量**"**）。

**⇒ 三层**：
```text
若【用 `pistol->maxAmmo`**】⇒ **⇒ 一个【随武器变**的数**
而【`90` 是【一个**固定**的数 ⇒ **⇒ 所以【那是【一个**测量的**倒地状态**】
```

**✅ ⭐⭐⭐ **"那是零售的倒地状态的一个测量"**。

**⚠ 而"那个手枪的**选取**"**】**。**

**⇒ 十六层**：
```text
① 遍历 `{secondary, primary}` ⇒ **优先副武器**
② 条件：`weaponClass == 5`（**手枪**）且 `clipSize` 且 `ammoIndex`**
③ 若【找不到**】⇒ **⇒ `zombieFallbackPistol_`**（**一个配置的**备用手枪**）
④ **⇒ 而【若【那个 fallback 【也【不合格**】⇒ **⇒ 返回 `false`**
```

**✅ ⭐⭐⭐ **"若那个 fallback 也不合格就返回 false —— 不发明一个武器身份"** —— 而**注释明说**："`// Asset failure: do not invent a weapon identity.`"**。**

**⇒ 三层**：
```text
`return false` ⇒ **⇒ 一个**明确的**失败**
而【发明一个 `weaponClass 5` 的假武器**】⇒ **⇒ 一个**看似合理的**错误**
⇒ **⇒ 所以【后者【更坏**】
```

**✅ ⭐⭐⭐ **"发明一个假武器比失败更坏"** —— 第五次"一个看似合理的错误"（与 §467/§468/§471/§484 同族）。

## 五、**`SV_PlayerSnapshotView` 的三层重写**（本组第四重要）

### 5.1 三层

```text
① 跟随：`zombieSpectatorTargets`（zm 观战）或 `deathViewTargets`（MP 死亡视角）
   ⇒ subject 换成被看的人；`view.otherFlags = (view.otherFlags & ~0x1000u) | 0x2800u`
② 回放：`killcamReplayPoses` ⇒ 覆盖 origin/viewAngles，并 `view.velocity = {}`
③ 双冻结：`zombieReviverGenerations` / `factoryTravelerGenerations`
   ⇒ `pmFlags |= SvPmFlagsMatchEndFrozen`，后者还 `eFlags |= SvEFlagsNoDraw`
```

### 5.2 二十四层

```text
1. **三层，而【每一层【只【改【一个**副本**】（`auto view = *state`**）**
2. ⇒ **⇒ 所以【那个活的** `playerStates` 【不被**触碰**】
3. ⇒ **⇒ 而【那是一句**注释**说的**："**这里发布它【保持【那个活的 `playerStates` **不被触碰**"**
```

### 5.3 ⭐⭐⭐ **"这里发布它保持那个活的 playerStates 不被触碰"**

**✅ 与 §469 的"只读是安全的取证方式"**、§477 的"玩家半程是它自己的有界的一趟"**——**同族** ✓

**⇒ 三层**：
```text
只读 ⇒ **`auto view = *state`**（**一个副本**）
改写 ⇒ **只在【那个副本**上**
⇒ **⇒ 所以【三个**投影【全部【无副作用**】
```

**✅ ⭐⭐⭐ **"三个投影全部无副作用"** —— 而**那【正是【"按接收者投影"**的**正确写法**。

**⚠ 而"`29200: THE KILLCAM REPLAY`"**⇒ **一个**极重要的机制**。】

**⇒ 二十层**：
```text
1. **2697 【从不【要求【客户端【回放【它自己的**快照历史**】
2. ⇒ **⇒ 服务器【保留【那些归档的帧**】
3. ⇒ **⇒ 而【交给【接收者【一个【在 `now - deltaTime` 上**求值的**状态**
4. ⇒ **⇒ （`sv_snapshot.c:1432-1436` 取 `archiveTime` 从 `sess.archiveTime`**）**
5. ⇒ **⇒ （`2926-3052` 回卷那个缓存的** `playerState`**）**
6. ⇒ **⇒ （`codol_engine_state.c:388-397` 说【客户端【在 `deltaTime`（`+0xa50`）非零**的那一刻【进入它的 killcam**）**
7. ⇒ **⇒ 而【这个项目的环【就是【那个**归档**】
8. ⇒ **⇒ 所以【在这里发布它【保持【那个活的 `playerStates` 【不被触碰**】
```

**✅ ⭐⭐⭐ **"这个项目的环就是那个归档"** —— 与 §422 的"`snapshotHistory` 的 32 个条目"**完全闭合** ✓

**⇒ 三层**：
```text
§422  **`SnapshotHistoryCapacity = 32`**
§485  **"这个项目的环就是那个归档"**
⇒ **⇒ 所以【那 32 个条目【是【killcam 回放的**来源**
```

**✅ ⭐⭐⭐ **"那 32 个条目是 killcam 回放的来源"**。

**⚠ 而"`view.velocity = {}` 在回放里"**⇒ **一句**极精确的**注释**。**

**⇒ 三层**：
```text
`// A replay is a camera, not a life: no prediction from a past pose.`
⇒ **⇒ 所以【清速度【防止【客户端【从【一个**过去的姿态**【预测**】
```

**✅ ⭐⭐⭐ **"一个回放是一个摄像机，不是一个生命：不从过去的姿态预测"** —— 一个**极重要的区分**。

### 5.4 而**`otherFlags` 的 `~0x1000 | 0x2800`**

**⇒ 十层**：
```text
`view.otherFlags = (view.otherFlags & ~0x1000u) | 0x2800u`
⇒ **⇒ 清 `0x1000`**】⇒ **⇒ 而【设 `0x2800` = `0x2000 | 0x800`**】
⇒ **⇒ 所以【那个 `0x1000` 位【被【替换【成【两个**位**
```

**✅ ⭐⭐⭐ **"那个 0x1000 位被替换成两个位"**。

**✅ 与 §463 的"`ps+0x10` 的三个 dword 受保护值"**——**完全闭合** ✓

**⇒ 三层**：
```text
§463  **`ps+0x10`（`otherFlags`）【是一个**三 dword 的受保护值**】
§485  **`otherFlags = (x & ~0x1000) | 0x2800`**（**一个读改写**）
⇒ **⇒ 所以【那个读改写【在【一个**受保护的**字段**上
```

**⚠ 而"`0x2800` 与 `0x1000`"**⇒ **而 §462 的 `PlayerOtherFlagsServerOwnedMask = 0x1800`**】**。**

**⇒ 三层**：
```text
`0x1800` ⇒ **`0x1000 | 0x800`**（**那个服务器拥有的掩码**）
`0x2800` ⇒ **`0x2000 | 0x800`**
⇒ **⇒ 所以【`0x800` 【是【共享**的】而 `0x1000` vs `0x2000` 【不同**
```

**✅ ⭐⭐⭐ **"0x800 是共享的，而 0x1000 vs 0x2000 不同"** —— 一个**极精确的位分析**。

**⚠ 标注**：那个 `~0x1000` 清【可能【违反【§462 的"服务器拥有的掩码"**约束**（**因为 `0x1000` 在【那个掩码**里**）⇒ **一个可质疑的候选**。

## 六、**复活索取的四道门**（本组第五重要）

### 6.1 四道

```text
① `if (down.reviver && now - down.lastSeen > 500) down.cancel();`  ← 陈旧索取者
② `if (down.reviver && down.reviver != reviver) return false;`      ← 别人在救
③ `if (!down.reviver || down.reviverGeneration != helper.spawnGeneration)` ← 新的索取
        ⇒ cancel + 记录 reviver/generation/startedAt + 算 duration
④ `down.lastSeen = now;` 然后 `if (now - down.startedAt < down.duration) return false;`  ← 还没到时间
```

### 6.2 二十四层

```text
1. **四道，而【第 ③ 道【是【唯一的【一个"开始**"的**】
2. ⇒ **⇒ 而那三道【其余【都是"继续**"或"拒绝**"**
3. ⇒ **⇒ 所以【那个 `down.reviver` 字段【同时【承担【"有人在救**"与"是**谁**"**
```

### 6.3 ⭐⭐⭐ **"一个断线/陈旧的持有者不能预定一个受害者"**

**✅ 与 §483 的"一个无效的输入不能部分地重置一个玩家"**——**同族**（**第五次"一个**过期状态【必须【被【显式**取消**"**）。

**⇒ 三层**：
```text
若【不检查 `lastSeen`**】⇒ **⇒ 一个**断线的**帮手【永久**持有一个受害者**
检查 ⇒ **⇒ `500ms` 后【自动**取消**】
⇒ **⇒ 所以【那个检查【是【必须的**】
```

**✅ ⭐⭐⭐ **"那个检查是必须的"**。

**⚠ 而那个 `duration` 的**算法**】**。**

**⇒ 十层**：
```cpp
const auto abilities = effectivePlayerAbilities(reviver, down.reviverGeneration);
const auto rate = abilities ? SV_AbilityValue(*abilities, SvAbilityReviveRate, 1.0f) : 1.0f;
down.duration = static_cast<std::uint32_t>(SvZombieReviveMilliseconds /
    (std::isfinite(rate) ? std::clamp(rate, 1.0f, 3.0f) : 1.0f));
```
```text
1. **`rate` 默认 `1.0`**】
2. ⇒ **⇒ 而【它【被 【`clamp(rate, 1.0, 3.0)`**】
3. ⇒ **⇒ 所以【一个 `rate > 3` ⇒ `3`**】⇒ **⇒ 而【`duration = ms / 3`**】（**最快**）
4. ⇒ **⇒ 而【`rate < 1` ⇒ `1`**】⇒ **⇒ 而【`duration = ms`**】（**最慢**）
⇒ **⇒ 所以【那个 `rate` 【只能【加速**】（**不能【减速**）
```

**✅ ⭐⭐⭐ **"那个 rate 只能加速，不能减速"** —— 一个**有意的**单侧**设计**。

**✅ 而"`!std::isfinite(rate)` ⇒ `1.0`"**⇒ **一个**NaN 的**守卫**（**与 §467/§476 同族**）**。**

## 七、`stepZombieRevives` 的五个状态

```text
① 清理：`zombieDowned_` 与 `zombieDownedInventories_` 里代次过期的条目
② 计数：`participants`（Playing + 已应用生成序列）与 `standing`（活着且未倒地）
③ 武装：`!zombieRevivalActive_ && participants >= 2` ⇒ 启用
④ 团灭：`participants && !standing && !zombieDowned_.empty()` ⇒ `zombieTeamWiped_` + `setMatchCompleted(true)`
⑤ 每受害者：已流血完 ⇒ 按 round 递增给 respawnTime；否则检查 reviver 有效性、500ms 超时、或流血计时
```

### 7.1 二十四层

```text
1. **五个状态，而【第 ③（武装）与 ④（团灭）【是【两个**阈值**
2. ⇒ **⇒ 而【第 ⑤【是【那个**每受害者**的循环**
3. ⇒ **⇒ 所以【那个函数【是【一个**三层的**状态机**】
```

### 7.2 ⭐⭐⭐ **"`participants >= 2` 才武装 —— 一个单人不启用合作复活"**

**✅ 与 §469 的"`14` 种姿态里三个是战术标记"**——**不同**（那是一个**分类**，这是一个**阈值**）但**同族**（**第六次"一个**阈值【是【一个**行为**"**）。

**⇒ 三层**：
```text
`participants >= 2` ⇒ **合作复活【有意义**】
`participants == 1` ⇒ **一个单人【倒地【无法【被救**】⇒ **⇒ 所以【不启用以【避免【一个**必然的**团灭**
⇒ **⇒ 所以【那个阈值【是【一个**正确性**的要求**
```

**✅ ⭐⭐⭐ **"那个阈值是一个正确性的要求"**。

**⚠ 而"`setMatchCompleted(true)` 在团灭时"**⇒ **一个**终局**的**触发**。**

**⇒ 十层**：
```text
团灭 ⇒ **`zombieTeamWiped_ = true` + `setMatchCompleted(true)`**
⇒ **⇒ 而【`for (auto &[clientNum, down] : zombieDowned_) down.cancel();`**】
⇒ **⇒ 所以【那个团灭【取消**所有**正在进行的复活**】
```

**✅ ⭐⭐⭐ **"那个团灭取消所有正在进行的复活"**。

## 八、关键结论

1. **⭐⭐⭐ "一个被持有的复活暂停流血；它不能被持有没有**新鲜的已提交命令、距离与一个存活的索取者**"`** ⇒ 那三个条件在**每帧循环**里被检查（`500ms` 超时 + `zombieReviveTarget` 的活着/距离/视线）⇒ **"那个暂停是一个受约束的状态"**；而 **`500ms` @ 30Hz = `15` 帧 ⇒ "一个帮手必须每 15 帧至少提交一次"**。
2. **⭐⭐⭐ `i 1000 2.000000 0 1` / `i 100 0.000000 0 1`**：`'i'` 的四个字段是 **duration / blur / flags / priority**（`613A40` → `611920`），倒地时 1 秒模糊 2.0、复活时 0.1 秒无模糊；而 **`'3' "grayscale" 1000`（倒地）/ `'3' "zm_factory_sh" 0`（复活）** ⇒ **"那条复活命令恢复那个地图的色调"`** —— 与 §470 的六条 vision 的 `"<mapname>" 0` **完整闭合**。
3. **⭐⭐⭐ `'a' <weapon>` 与 `'y' <offhand>`** ⇒ **"两条更新那两个展示字段"`**；而 **§462 的 `y 906` 是"从未发过的三个动词之一"，而这里 `y <offhand>` 每次复活都发** ⇒ **"`y` 是一个活的命令，而 `906` 是一个特定参数"`** —— 一个跨报告的精化。
4. **⭐⭐⭐ 倒地手枪的选取**：**遍历 `{secondary, primary}` 找 `weaponClass == 5`（手枪）且 `clipSize` 且 `ammoIndex`** ⇒ 找不到时用 `zombieFallbackPistol_` ⇒ **再不合格就 `return false`**（**"Asset failure: do not invent a weapon identity"**）⇒ **"发明一个假武器比失败更坏"** —— 第五次"一个看似合理的错误"（与 §467/§468/§471/§484 同族）。
5. **⭐⭐⭐ `90` 发备弹是一个测量的数**（不是 `pistol->maxAmmo`）—— 与 §483 的"结构体默认值 `250/100/0` 是源自己的"同族。
6. **⭐⭐⭐ `SV_PlayerSnapshotView` 的三层重写全部在 `auto view = *state` 的副本上** ⇒ **"这里发布它保持那个活的 `playerStates` 不被触碰"`** —— 与 §469/§477 同族（**"三个投影全部无副作用"**）。
7. **⭐⭐⭐ `29200: THE KILLCAM REPLAY` 的完整机制**：**"2697 从不要求客户端回放它自己的快照历史：服务器保留那些归档的帧，并交给接收者一个在 `now − deltaTime` 上求值过的状态（`sv_snapshot.c:1432-1436` 从 `sess.archiveTime` 取 `archiveTime`；`2926-3052` 回卷那个缓存的 `playerState`；`codol_engine_state.c:388-397` 说客户端在 `deltaTime`（`+0xa50`）非零的那一刻进入它的 killcam）⇒ 这个项目的环就是那个归档"`** ⇒ 与 §422 的 `SnapshotHistoryCapacity = 32` **完全闭合**（**"那 32 个条目是 killcam 回放的来源"**）。
8. **⭐⭐⭐ "一个回放是一个摄像机，不是一个生命：不从过去的姿态预测"`**（`view.velocity = {}`）—— 一个极重要的区分。
9. **⭐⭐⭐ `otherFlags` 的 `(view.otherFlags & ~0x1000u) | 0x2800u`** ⇒ **独立分析：`0x2800 = 0x2000 | 0x800`，而 §462 的 `PlayerOtherFlagsServerOwnedMask = 0x1800 = 0x1000 | 0x800`** ⇒ **`0x800` 是共享的，而 `0x1000` vs `0x2000` 不同**。**⚠ 那个 `~0x1000` 清可能违反 §462 的"服务器拥有的掩码"约束（因为 `0x1000` 在那个掩码里）—— 标注为一个可质疑的候选。**
10. **⭐⭐⭐ 复活索取的四道门**（陈旧索取者 `500ms` / 别人在救 ⇒ `false` / 新索取 ⇒ 记录 + 算 `duration` / 还没到时间）⇒ **"一个断线/陈旧的持有者不能预定一个受害者"**（与 §483 同族）；而 **`duration = ms / clamp(rate, 1.0, 3.0)`** ⇒ **"那个 rate 只能加速，不能减速"**（一个**有意的单侧设计**），且 `!isfinite(rate) ⇒ 1.0` 是**一个 NaN 守卫**。
11. **⭐⭐⭐ `stepZombieRevives` 的五个状态**，其中 **`participants >= 2` 才武装** ⇒ **"一个单人不启用合作复活"**（"那个阈值是一个正确性的要求"）；而**团灭时 `setMatchCompleted(true)` + 取消所有正在进行的复活**。

## 九、`sv_zm_revive_mp.cpp` 全文件总览

**`357` 行。**

**`9` 个 `SvServerWorld` 方法**：`prepareZombieDownedInventory` / `restoreZombieDownedInventory` / `sendZombieDownedPresentation` / `consumeZombieDown` / `zombieDowned` / `zombieDownedState` / `zombieReviveTarget` / `zombieReviveHeld` / `processZombieReviveUse` / `stepZombieRevives`；以及自由函数 `SV_PlayerSnapshotView`。

**`4` 条可靠命令**：`i <dur> <blur> <flags> <prio>` / `3 "<vision>" <ms>` / `a <weapon>` / `y <offhand>`。

**`12` 个测量锚点**：
```text
Factory 60150/514050（倒地：藏武器 + 满手枪弹匣 + 90 备弹）
Factory 72750/521150（复活：恢复倒地前弹药）
613A40 → 611920（'i' 的解析）/ 46CEF0（'3' 的 type 5）
cg+0x10 bit 800（CGAME_FOLLOWING）/ field54 0x2800
zm20-21-43 / 20-34-14 / 21-43-53（三份 demo 的 field54 = 0x2800）
sv_snapshot.c:1432-1436 / 2926-3052 / codol_engine_state.c:388-397
deltaTime 在 +0xa50
500 ms 的索取者新鲜度窗口
weaponClass 5 = 手枪
SvZombieReviveRadius / SvZombieReviveMilliseconds
SvAbilityReviveRate（clamp 1..3）
```

## 十、未闭合点

- `otherFlags` 的 `~0x1000` 是否违反 §462 的 `PlayerOtherFlagsServerOwnedMask = 0x1800`。
- `0x2800` 的两个位（`0x2000` / `0x800`）的语义。
- `SvZombieReviveRadius` / `SvZombieReviveMilliseconds` / `SvZombieBleedoutMilliseconds` 的值。
- `zombieFallbackPistol_` 指向哪把枪。
- 下一个文件：`sv_zm_teleporters_mp.cpp`（`16,747` 字节）。
