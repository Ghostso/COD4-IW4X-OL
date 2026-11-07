# 371 · **"空手是一个【保持状态】，不是一次【写】"** —— `dmz_empty_mp=1137` 的 `4,253` 次拒绝、武器 0 是引擎自己的名字、`ps+0x10` 被 pmove 覆写

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 20000–20400 行。

## 二、**`dmz_empty_mp = 1137` 的完整事故链**（本组最重要的一段）

### 2.1 那段（第一半：为什么必须持有）

```php
// EMPTY HANDS ARE A HELD STATE, NOT A WRITE -- the same shape as
// setPlayerNoclip, and for the same reason it gives: the world rebuilds each
// client's playerState from pmove, so a single write is gone on the very next
// frame.
//
// MEASURED: the spawn puts dmz_empty_mp in correctly and the native buffer
// takes it (`current3F8=1137`, `list2F4=1137,0,...`), and then the FIRST pmove
// returns `before=1137 after=0` and clears heldWeapons with it. The native
// PM_Weapon will not keep a weapon the player was never properly given, and
// this server has no give-weapon owner -- that is the same missing piece that
// blocks loot pickup.
//
// So it is re-asserted after every pmove instead. The client agrees already:
// it reports `cmdWeapon=1137` on its own once told, and kept asking for it for
// the whole match while the server answered 0. This makes the server's answer
// match the question.
//
// ONLY WHILE UNARMED. The moment a weapon grant exists this hold has to yield
// to it, or a looted gun would be overwritten by empty hands every frame.
//
// AND SAY IT TO THE NATIVE BUFFER TOO. Correcting only the source copy was
// measured to be not enough: the probe read `after=1137` on every frame while
// the snapshot still carried `weap=0`, because the think projects native ->
// source a SECOND time after the weapon-movement stage and the native buffer
// still held the pmove's zero.
```

### 2.2 二十层

```text
1. **空手是一个【保持状态】，不是一次【写】**
2. ⇒ **与 `setPlayerNoclip` 同一个形状，同一个理由**
3. ⇒ **世界从 pmove 重建每个客户端的 `playerState`**
4. ⇒ **所以一次单写【在下一帧就没了】**
5. ⇒ **实测：spawn 把 `dmz_empty_mp` 正确放进去而原生缓冲区接住它**
6. ⇒ **（`current3F8=1137`、`list2F4=1137,0,...`）**
7. ⇒ **然后【第一次】 pmove 返回 `before=1137 after=0` 并连带清 `heldWeapons`**
8. ⇒ **原生 `PM_Weapon` 不会保留一把玩家【从未被正确给予】的武器**
9. ⇒ **而这个服务器【没有 give-weapon 所有者】**
10. ⇒ **那正是阻塞战利品拾取的【同一个缺失件】**
11. ⇒ **所以在每一个 pmove 之后重新断言**
12. ⇒ **客户端已经同意了**：一旦被告知它自己就报 `cmdWeapon=1137`
13. ⇒ **而整场比赛都在要它而服务器答 0**
14. ⇒ **这让服务器的答案与问题匹配**
15. ⇒ **【只在无武装时】**（一把授予存在时这个保持必须让位）
16. ⇒ **否则一把捡来的枪会每帧被空手覆盖**
17. ⇒ **并且要【对原生缓冲区】也说**
18. ⇒ **只修正源副本被测量为【不够】**
19. ⇒ **因为探针每帧读到 `after=1137` 而快照仍携带 `weap=0`**
20. ⇒ **因为 think 在武器移动阶段【之后】把原生 → 源投影【第二次】**
21. ⇒ **而原生缓冲区仍持有 pmove 的零**
```

### 2.3 ⭐ **"空手是一个保持状态，不是一次写"**

**✅ 与 §352 的"每帧保持 vs 写一次"**第五次。**

**⇒ 三层**：

```text
写一次   ⇒ **下一帧被 pmove 重建覆盖**
每帧保持 ⇒ **正确**
```

**✅ 与 §369 的"命令被中性化而不是跳过 pmove"**同族（**第二次"必须喂一个安全状态而不是绕过"**）。

### 2.4 而**"two owners"（源与原生）**

**✅ 与 §355 的"`ps` 与 `ent` 两个位置"**同族（**第四次"两个副本"）。**

**⇒ 三层**：

```text
源副本（`playerState`）    ⇒ 快照从此构建
原生副本（`nativePlayerState`）⇒ pmove 读写
⇒ **两者都必须写**
```

**⚠ 而"只修正源副本被测量为不够"⇒ **一个真实的一次错误**。**

**✅ 与 §361 的"源与原生不一致会导致 `25 j_spine4`"**同族（**第三次"两个副本必须同步"）。

## 三、**`1137` 的 `4,253` 次拒绝**（本组第二重要）

### 3.1 那段

```php
// EMPTY HANDS ARE NOT ASSERTED HERE ANY MORE, and the reason is the
// whole bug. Writing dmz_empty_mp into the NATIVE buffer made the very
// next stage refuse the frame: NativeWeaponMovementBindings reads the
// current weapon out of that buffer and runs it through
// SV_FindResolvedWeapon, which knows only the class's primary and
// secondary. 1137 is neither, so it returned nullopt, which is
// WeaponMovementRejected, which discards the usercmd -- and a discarded
// usercmd is the player being pulled back to where the server last agreed
// they were. MEASURED: 4,253 rejections in one session, every one of them
// `weapon=1137`, and not a single one after a real gun was granted.
```

### 3.2 十四层

```text
1. **空手不再在这里断言，而理由是【整个 bug】**
2. ⇒ **把 `dmz_empty_mp` 写进【原生】缓冲区让【紧接着的下一阶段】拒绝这一帧**
3. ⇒ **`NativeWeaponMovementBindings` 从那个缓冲区读当前武器**
4. ⇒ **并把它跑过 `SV_FindResolvedWeapon`**
5. ⇒ **而它【只知道】职业的主武器与副武器**
6. ⇒ **`1137` 两个都不是**
7. ⇒ **所以它返回 `nullopt`**
8. ⇒ **那是 `WeaponMovementRejected`**
9. ⇒ **它【丢弃 usercmd】**
10. ⇒ **而一个被丢弃的 usercmd 是玩家被拉回服务器最后一次同意的位置**
11. ⇒ **实测：一个会话里 `4,253` 次拒绝**
12. ⇒ **每一次都是 `weapon=1137`**
13. ⇒ **而在授予一把真枪之后【一次都没有】**
```

### 3.3 ⭐ **"4,253 次拒绝，每一次都是 `weapon=1137`"**

**✅ 与 §355 的 `259,968`、§351 的 `237`**第七次大规模统计。

**⚠ 而"授予真枪后零次"⇒ **一个完美的阴性对照**。**

**✅ 与 §370 的"阳性对照"**互补（**这里是**阴性对照**）。**

**⇒ 一对完整的对照：**

```text
空手 ⇒ 4,253 次拒绝
真枪 ⇒ 0 次
⇒ **所以拒绝的原因是 `1137` 而不是别的**
```

**✅ **一个决定性的实验。**

### 3.4 而**"不能通过把 1137 放进装备来修"**

```php
// AND IT CANNOT BE FIXED BY PUTTING 1137 IN THE LOADOUT.
// SV_IsResolvedLoadoutValid demands a nonzero ammo index, clip index,
// clip size, max ammo and fire time from EVERY slot it validates; empty
// hands have none of those, so the slot would fail and take the whole
// loadout -- and the class's real weapons with it -- down with it.
```

**⇒ 七层**：

```text
1. **它【不能】通过把 `1137` 放进装备来修**
2. ⇒ **`SV_IsResolvedLoadoutValid` 从它验证的【每一个槽】要求**
     · 非零的 `ammoIndex`
     · 非零的 `clipIndex`
     · 非零的 `clipSize`
     · 非零的 `maxAmmo`
     · 非零的 `fire time`
3. ⇒ **空手一个都没有**
4. ⇒ **所以那个槽会失败**
5. ⇒ **并带走【整个装备】**
6. ⇒ **以及【职业的真实武器】**
```

**✅ 与 §366 的"`SV_IsResolvedLoadoutValid` 是原生火器契约"**完全一致 ✓

**⇒ **第二次确认那个契约。**

**⚠ 而"带走整个装备"⇒ **一个极端的后果**。**

**✅ 与 §346 的"缺一个 eType 拒整帧"**同族（**第七次"全有或全无"）。**

## 四、**"武器 0 是引擎自己的名字"**（本组第三重要）

### 4.1 那段

```php
// THE ENGINE ALREADY HAS A NAME FOR THIS STATE: weapon 0, the native null
// weapon, which the same binding accepts without consulting the loadout at
// all ("PM_Weapon deliberately selects CODOL's native null weapon"). Empty
// hands ARE that state as far as movement is concerned. 1137 exists only
// so the CLIENT has a viewmodel to draw, so it belongs on the wire and
// nowhere else -- asserted at the very end of the think, after the last
// native projection, where nothing native reads it again.
```

### 4.2 十层

```text
1. **引擎【已经】有这个状态的名字：武器 `0`**
2. ⇒ **原生空武器**
3. ⇒ **同一个绑定【接受它】而【完全不查装备】**
4. ⇒ **（"`PM_Weapon` 故意选择 CODOL 的原生空武器"）**
5. ⇒ **空手就【是】那个状态**（就移动而言）
6. ⇒ **`1137` 只存在是为了让【客户端】有一个视模型可画**
7. ⇒ **所以它属于【线上】而不属于任何别的地方**
8. ⇒ **在 think 的【最末尾】断言**
9. ⇒ **在【最后一次】原生投影之后**
10. ⇒ **在那里没有原生的东西再读它**
```

### 4.3 ⭐ **"`1137` 只存在是为了让客户端有一个视模型可画"**

**✅ 这是本文件里**最清晰的一条"两个 id 空间"的陈述**。**

**⇒ 三层**：

```text
武器 0    ⇒ **移动层的"空"**（引擎认识）
武器 1137 ⇒ **渲染层的"空手"**（客户端画视模型）
⇒ **两者不是同一个东西**
```

**✅ 与 §345 的"客户端的基线 xmodel 不是文件的 xmodel"**同族（**第五次"两个 id 空间"）。**

**⚠ 而"断言在最末尾，在最后一次原生投影之后"⇒ **一个精确的时序约束**。**

**✅ 与 §347 的"THE TIME FIRST"**同族（**第四次时序约束**）。

### 4.4 而**"授予一把真枪 ⇒ 无条件重新断言"**

```php
if (grant) {
    // A GRANTED WEAPON OUTRANKS EMPTY HANDS and is re-asserted
    // unconditionally, not just when the pmove has zeroed it -- the pmove
    // also erases the ammo, and a gun that reloads to nothing every frame
    // would be worse than no gun.
    playerState.currentWeaponAssetIndex = grant->weaponAssetIndex;
    playerState.heldWeapons[0].weaponAssetIndex = grant->weaponAssetIndex;
    playerState.heldWeapons[0].heldBefore = true;
    auto &clip = playerState.ammoClips[0];
    if (clip.clipIndex != grant->clipIndex) { clip.clipIndex = grant->clipIndex; clip.count[0] = grant->clipSize; }
    auto &pool = playerState.ammoPools[0];
    if (pool.ammoIndex != grant->ammoIndex) { pool.ammoIndex = grant->ammoIndex; pool.count = grant->maxAmmo; }
    SV_SetNativePlayerStateCurrentWeapon(client.nativePlayerState, grant->weaponAssetIndex);
    SV_SetNativePlayerStateWeaponAmmo(client.nativePlayerState, 0, clip.clipIndex, clip.count[0], pool.ammoIndex, pool.count);
}
```

**⇒ 九层**：

```text
1. **一把授予的武器【压过】空手**
2. ⇒ **而无条件重新断言，不只是当 pmove 清零它时**
3. ⇒ **因为 pmove 【也擦掉弹药】**
4. ⇒ **而一把每帧重装到空的枪会比没有枪更糟**
5. ⇒ **填 `heldWeapons[0]` / `ammoClips[0]` / `ammoPools[0]`**
6. ⇒ **只在索引【不匹配】时填**（即 pmove 擦过）
7. ⇒ **所以玩家已经花掉的子弹【保持花掉】**
8. ⇒ **而计数来自源副本，不是来自授予**
9. ⇒ **两个原生设置函数都调**
```

### 4.5 ⭐ **"只在索引不匹配时填 ⇒ 已花掉的子弹保持花掉"**

**✅ 一个**极精确的补弹语义**。**

**⇒ 三层**：

```text
若每帧都填 ⇒ **开火永远不消耗子弹**（射击后下一帧补满）
若只在索引不匹配时填 ⇒ **只补 pmove 擦掉的情况** ✓
```

**✅ 与 §366 的"这不是从储备到弹匣的转移"**不同**（那是**补给站**，这是**保持**）。**

**⚠ 而"开火永远不消耗子弹"⇒ **一个具体的 bug**。**

**✅ 与 §353 的"越修越坏"**同族。

### 4.6 而**"武器活下来因为写到两个，弹药没活因为只写到一个"**

```php
// AND THE AMMO INTO THE NATIVE BUFFER, for the reason the weapon is
// already written there: the think re-projects native -> source after
// the weapon-movement stage, and that projection reads the clips and
// pools back out of the native buffer. Correcting only the source copy
// was measured to produce a gun in hand reading "Out of ammo" -- the
// weapon survived because it was written to both, the ammo did not
// because it was written to one.
```

**⇒ 七层**：

```text
1. **弹药也写进原生缓冲区**
2. ⇒ **因为 think 在武器移动阶段之后把原生 → 源【再投影一次】**
3. ⇒ **而那个投影从原生缓冲区【读回】clips 与 pools**
4. ⇒ **只修正源副本被测量为产生"手里一把枪而读 'Out of ammo'"**
5. ⇒ **武器活下来因为写到了【两个】**
6. ⇒ **弹药没活因为只写到了【一个】**
7. ⇒ **所以两个都必须写**
```

**✅ 与 §371 二.4 的"两个所有者"**完全闭合 ✓

**⚠ 而"Out of ammo"⇒ **一个极具体的症状**（第六次具体视觉症状）。**

## 五、`spawn-animation` 的**"每次都说，带一个计数"**（本组第四重要）

### 5.1 那段

```php
if (spawnAnimationRunner_ && client.spawnAnimationGeneration != playerState.spawnGeneration) {
    // SAY IT EVERY TIME, WITH A COUNT. This is supposed to fire ONCE PER LIFE.
    // spawnGeneration is read back out of the native playerState every think
    // (`next.spawnGeneration = spawnCountStat`, ps+0x1B0), so if that offset is
    // not this build's spawn counter the gate opens on every frame and the
    // weapon-raise animation restarts forever -- which is exactly what a player
    // watching the client reported. A counter distinguishes "once per life"
    // from "once per frame" without any further reasoning.
    static std::uint32_t runs{};
    ++runs;
    OlMod::RuntimeLog::write(..., "spawn-animation re-run " + runs + " gen=" +
        client.spawnAnimationGeneration + "->" + playerState.spawnGeneration + " t=" + commandTime);
    client.spawnAnimationGeneration = playerState.spawnGeneration;
    const auto spawnAnimation = spawnAnimationRunner_(client.nativePlayerState, snapshot_.serverTime);
    OlMod::RuntimeLog::write(..., "spawn-animation result " +
        (spawnAnimation ? (*spawnAnimation < 0 ? "NO ANIM FOR THE EVENT (-1)"
            : "duration=" + *spawnAnimation) : "CALL REFUSED OR FAULTED"));
}
```

### 5.2 十三层

```text
1. **每次都说，带一个计数**
2. ⇒ **这【本应】一生只触发一次**
3. ⇒ **`spawnGeneration` 每个 think 从原生 `playerState` 读回**
4. ⇒ **（`next.spawnGeneration = spawnCountStat`，`ps+0x1B0`）**
5. ⇒ **所以若那个偏移不是这个 build 的出生计数器**
6. ⇒ **门控会【每帧打开】而举枪动画【永远重启】**
7. ⇒ **而那正是【一个看客户端的玩家】报告的**
8. ⇒ **一个计数器区分"一生一次"与"每帧一次"而无需进一步推理**
9. ⇒ **并且说它【返回】了什么**
10. ⇒ **结果过去被一个 `static_cast<void>` 丢掉**
11. ⇒ **所以 "spawn-animation re-run" 只证明服务器【决定】跑它**
12. ⇒ **而不是引擎解析出了一个动画**
13. ⇒ **三种不同的世界**（`-1` 无动画 / `duration` 有 / `nullopt` 拒绝或出错）从外面读起来相同**
```

### 5.3 ⭐ **"一个计数器区分『一生一次』与『每帧一次』而无需进一步推理"**

**✅ 与 §368 的"三层命名失败项"**同族（**第五次"命名而不是计数"…… 而这里**用计数来命名频率**）。**

**⇒ 三层**：

```text
若 `runs` 很小 ⇒ 正确
若 `runs` 每帧涨 ⇒ **门控坏了**
⇒ **一个数字就分开了**
```

**✅ 与 §355 的"每 5 帧而非前 40 帧"**同族（**第四次"频率是一个判据"**）。

### 5.4 而**"三种世界从外面读起来相同"**

**✅ 与 §368 的"一个裸的 `static_cast<void>` 只证明服务器决定伤害"**完全同族（**第三次）。**

**⇒ **本文件的一个核心纪律**：**

```text
调用成功 ≠ 引擎解析出东西
⇒ **必须打印返回值**
```

## 六、**`ps+0x10` 被 pmove 覆写**（本组第五重要）

### 6.1 那段

```php
// THE NATIVE PMOVE WRITES OVER ps+0x10, SO SAY IT AGAIN HERE.
// SV_OverlayPlayerStateToNative already put this server's otherFlags there at
// the top of the think, but ps+0x10 is the engine's PROTECTED storage on this
// build and the pmove writes its own encoded form into it. Measured: the value
// the converter then read as plaintext was 0x00001000 on some commands and
// 0x519FE7D0, 0x5BF15C99, 0x5685BA3B on others -- and that word is what gets
// protected and tested against 0x1800 for eType, so the player flickered between
// ET_PLAYER and ET_INVISIBLE according to noise. beginFrame owns otherFlags
// outright (`effectivePlaying ? 1u << 12 : 0`), so re-asserting it is not a
// policy change; it is making the write at the top of the think survive a native
// stage that was never going to leave a plain dword alone.
SV_SetNativePlayerStateOtherFlags(client.nativePlayerState, playerState.otherFlags);
```

### 6.2 十三层

```text
1. **原生 pmove 覆写 `ps+0x10`，所以在这里【再说一次】**
2. ⇒ **`SV_OverlayPlayerStateToNative` 已经在 think 的开头把这个服务器的 `otherFlags` 放进去**
3. ⇒ **但 `ps+0x10` 是这个 build 的引擎【受保护存储】**
4. ⇒ **而 pmove 把它自己的【编码形式】写进去**
5. ⇒ **实测：转换器随后读作明文的那个值**
     · **某些命令是 `0x00001000`**
     · **其它是 `0x519FE7D0`、`0x5BF15C99`、`0x5685BA3B`**
6. ⇒ **而那个字正是被保护并与 `0x1800` 比较来决定 eType 的**
7. ⇒ **所以玩家在 `ET_PLAYER` 与 `ET_INVISIBLE` 之间【按噪声闪烁】**
8. ⇒ **`beginFrame` 直接拥有 `otherFlags`**（`effectivePlaying ? 1u << 12 : 0`）
9. ⇒ **所以重新断言它不是一次策略变更**
10. ⇒ **它是让 think 开头的写【存活过】一个从来不打算让一个普通 dword 独处的原生阶段**
```

### 6.3 ⭐ **"按噪声在 `ET_PLAYER` 与 `ET_INVISIBLE` 之间闪烁"**

**✅ 与 §361 的"红色 FX 占位符"**同族（**第七次具体视觉症状）。**

**⇒ 三层**：

```text
1. `ps+0x10` 被覆写成随机般的数据
2. ⇒ **那个字被测试 `0x1800` 决定 eType**
3. ⇒ **所以 eType 按噪声在 0 与 1 之间变**
4. ⇒ **⇒ 玩家闪烁**
```

**✅ **一个极端的"下游后果"**。**

**⚠ 而三个具体的噪声值**（`0x519FE7D0` 等）⇒ **看起来像指针或加密块**。

**✅ 与 §360 的"编解码器不同 ⇒ 失步"**同族。

### 6.4 而**"受保护存储"**

**⇒ 三层**：

```text
1. `ps+0x10` 在这个 build 是【受保护的】
2. ⇒ **所以 pmove 按它自己的编码写**
3. ⇒ **所以明文读会得到垃圾**
```

**✅ 与 §368 的"`ps+0xFC` 的 bit `0x10`"**不同**（那是**另一个偏移的另一个位**）。**

**⚠ 所以**两个不同的 `0x10`**：**

```text
`ps + 0x10`    otherFlags 字段（受保护存储）
`ps+0xFC` bit 0x10  隐藏位
```

**✅ 一处**容易混淆的地方**。**

## 七、**`stg=%d,%d,%d,...` 的九段**

```php
idle.stageWmTime[0], ..., idle.stageWmTime[8]
```

**⇒ 三层**：

```text
1. **九个阶段的 `weaponIdleTime` 快照**
2. ⇒ **所以武器移动有【九个内部阶段】**
3. ⇒ **而每个阶段后都记下 `wmTime`**
```

**✅ 与 §349 的"四十个 client-think 阶段"**不同**（那是**失败阶段**，这是**内部阶段**）。**

**⚠ 而九段的用途**：**定位 `weaponIdleTime` 在哪一段被重置。**

**✅ 一个**极精细的插桩**。**

## 八、**狙击镜抖动的两个假设**（本组第六重要）

### 8.1 那段

```php
// Why this exists: "the sniper scope twitches, and holding Shift stops it"
// has exactly two surviving candidates and no existing log separates them --
// (A) the native idle phase restarts every frame because `weaponIdleTime` is
// never stored back (see SvWeaponMovementIdleDiagnostics), or (B) the frame's
// view offset itself is the twitch. dA=/srvView/cmdView already proved the
// VIEW ANGLE channel is clean, so the fault is in this stage or nowhere.
//
// BOUNDED, ONCE PER SECOND PER CLIENT, and it prints a CHANGE flag: an idle
// phase that restarts every frame shows up as `adv=` never advancing, which
// is a reading rather than an inference. Cost is one snprintf per second.
```

### 8.2 十二层

```text
1. **为什么这个存在："狙击镜抖动，而按住 Shift 就停"**
2. ⇒ **恰好【两个】存活的候选而没有现成的日志分开它们**
3. ⇒ **(A) 原生 idle 相位每帧重启，因为 `weaponIdleTime` 从不被存回**
4. ⇒ **(B) 那一帧的 view offset 本身是那个抖动**
5. ⇒ **`dA=/srvView/cmdView` 已经证明【视角通道是干净的】**
6. ⇒ **所以故障【在这个阶段或者哪里都没有】**
7. ⇒ **有界，每客户端每秒一次**
8. ⇒ **而它打印一个【变化】标志**
9. ⇒ **一个每帧重启的 idle 相位显示为 `adv=` 从不推进**
10. ⇒ **那是一个【读数】而不是一个推断**
11. ⇒ **成本是每秒一个 `snprintf`**
```

### 8.3 ⭐ **"恰好两个存活的候选"**

**✅ 与 §343 的"两个极端"、§362 的"两个方向"**同族（**第三次"候选空间被缩小到二"）。**

**⇒ 三层**：

```text
一个假设（视角通道）已被 dA= 日志排除
⇒ **剩两个**
⇒ **而这条日志能让一次运行（十秒不按 Shift、十秒按）做出决定**
```

**✅ 与 §355 的"两个极端都测"**同族（**第五次"通过实验缩小"）。**

### 8.4 而**"按住 Shift 是 CODOL 的闭气"**

```php
// THE BREATH CHANNEL, AND IT IS HERE BECAUSE THE OPERATOR'S OWN
// DISCRIMINATOR IS SHIFT.
//
// Measured on this client, not assumed: players\config_mp.cfg carries
//     bind SHIFT "+breath_sprint"
// so holding Shift while scoped is CODOL's hold-breath, and the
// operator reports the twitch STOPS while it is held. Hold-breath
// scales the sway (ps+0x298) -- it does not touch the view angles --
// so printing swayScale/timer in the SAME line as wmTime/idleFactor
// turns one run (ten seconds without Shift, ten with) into the
// decision between "the idle stage itself" and "the sway scale that
// merely masks it".
```

**⇒ 十一层**：

```text
1. **呼吸通道，而它在这里因为【操作员自己的判别器是 Shift】**
2. ⇒ **在这个客户端上测量，不是假设**
3. ⇒ **`players\config_mp.cfg` 携带 `bind SHIFT "+breath_sprint"`**
4. ⇒ **所以持着 Shift 而开镜是 CODOL 的闭气**
5. ⇒ **而操作员报告抖动在被持有时【停止】**
6. ⇒ **闭气缩放 sway（`ps+0x298`）**
7. ⇒ **它【不碰】视角角度**
8. ⇒ **所以把 `swayScale`/`timer` 打印在与 `wmTime`/`idleFactor` 同一行**
9. ⇒ **把一次运行（十秒不按 Shift、十秒按）变成**
10. ⇒ **在"idle 阶段本身"与"仅仅遮蔽它的 sway 缩放"之间的决定**
```

### 8.5 ⭐ **"操作员的判别器是 Shift"**

**✅ 与 §355 的"玩家的判决"**第六次。**

**⇒ 三层**：

```text
玩家观察到：按住 Shift 抖动停止
⇒ **而 Shift 是闭气**
⇒ **而闭气缩放 sway 而不碰视角**
⇒ **所以抖动在 sway 通道而不是视角通道**
```

**✅ **一个从玩家行为反推故障层的推理**。**

**⚠ 而"配置是明文的"⇒ 与 §370 的"`config_mp.cfg` 是加密的"**矛盾**！**

**⚠ 一处**真实的矛盾**。**

**⇒ 可能**两个不同的配置文件**（`players/config_mp.cfg` vs `players\\config_mp.cfg`）。**

**✅ 或者一个被解密了。**

## 九、关键结论

1. **⭐⭐ "空手是一个【保持状态】，不是一次【写】"`** —— 世界从 pmove 重建 `playerState`，所以单写在**下一帧就没了**。
2. **"第一次 pmove 返回 `before=1137 after=0` 并连带清 `heldWeapons`"`** —— 原生 `PM_Weapon` **不保留一把从未被正确给予的武器**。
3. **"这个服务器没有 give-weapon 所有者 —— 那正是阻塞战利品拾取的同一个缺失件"`** —— 一个**共同的架构缺口**。
4. **"客户端一旦被告知就自己报 `cmdWeapon=1137`，而整场都在要它而服务器答 0"`** —— 一个**极清晰的客户端/服务端对话**。
5. **⭐ "只修正源副本被测量为不够：think 在武器移动阶段之后把原生 → 源投影第二次"`** —— 第三次"两个副本必须同步"。
6. **⭐⭐ `1137` 的 `4,253` 次拒绝** —— 每次都 `weapon=1137`，而**授予真枪后零次**（**一个完美的阴性对照**）。
7. **"写进原生缓冲区让 `NativeWeaponMovementBindings` 返回 nullopt ⇒ `WeaponMovementRejected` ⇒ 丢弃 usercmd ⇒ 玩家被拉回"`** —— 一整个因果链。
8. **⭐ "不能通过把 `1137` 放进装备来修：`SV_IsResolvedLoadoutValid` 从每个槽要求五个非零值 ⇒ 那个槽失败 ⇒ 带走整个装备以及职业的真实武器"`** —— 第七次全有或全无。
9. **⭐⭐ "引擎已经有这个状态的名字：武器 `0`（原生空武器），同一个绑定接受它而不查装备"`**。
10. **"`1137` 只存在是为了让客户端有一个视模型可画 ⇒ 它属于线上而不属于任何别的地方 ⇒ 在 think 的最末尾断言，在最后一次原生投影之后"`** —— 第五次"两个 id 空间"。
11. **"授予的武器压过空手而无条件重新断言，因为 pmove 也擦掉弹药，而一把每帧重装到空的枪比没有枪更糟"`**。
12. **⭐ "只在索引不匹配时填 ⇒ 已花掉的子弹保持花掉"`** —— 否则**开火永远不消耗子弹**。
13. **⭐ "武器活下来因为写到了两个，弹药没活因为只写到了一个 ⇒ 手里一把枪读 'Out of ammo'"`**。
14. **`spawn-animation` 的"每次都说带一个计数"`** —— **"一个计数器区分『一生一次』与『每帧一次』而无需进一步推理"`**（第四次"频率是一个判据"）。
15. **`spawnGeneration` 从 `ps+0x1B0` 读回** ⇒ 若那个偏移不是出生计数器则**门控每帧打开**。
16. **"结果被一个 `static_cast<void>` 丢掉 ⇒ 只证明服务器决定跑它"`** —— 第三种世界（`-1` / `duration` / `nullopt`）从外面读起来相同（第三次）。
17. **⭐⭐ `ps+0x10` 被 pmove 覆写** —— 实测读到 `0x00001000` / `0x519FE7D0` / `0x5BF15C99` / `0x5685BA3B`。
18. **"那个字被保护并与 `0x1800` 比较来决定 eType ⇒ 玩家在 `ET_PLAYER` 与 `ET_INVISIBLE` 之间【按噪声闪烁】"`** —— 第七次具体视觉症状。
19. **"它让 think 开头的写存活过一个从来不打算让一个普通 dword 独处的原生阶段"`**。
20. **武器移动的九个内部阶段**（`stg=%d,%d,...` 九段）—— 一个极精细的插桩。
21. **⭐ 狙击镜抖动的两个存活候选**（idle 相位每帧重启 / view offset 本身），而 **`dA=/srvView/cmdView` 已排除视角通道**。
22. **⭐ "操作员的判别器是 Shift"`** —— 而 `bind SHIFT "+breath_sprint"` ⇒ **闭气缩放 sway 而不碰视角** ⇒ 从玩家行为反推故障层。
23. **⚠ `config_mp.cfg` 在 §370 是加密的而这里读出明文** —— 一处真实矛盾。

## 十、未闭合点

- `config_mp.cfg` 加密性的矛盾。
- `Ps+0x1B0` 是否真的是 `spawnCountStat`。
- `weaponIdleTime` 为什么从不被存回。
- `SV_ReadNativeHoldBreathState` 的实现。
- `ps+0x298` 的 swayScale。
- `sv_snapshot_mp.cpp` 20400 行之后未读取（27,016 行，进度 76%）。
