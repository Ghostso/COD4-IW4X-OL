# 462 · **"四十个项共用一个 `return false`，而给那一项命名把『玩家永不出生』变成【一个要检查的偏移】**" —— 反向准入、`y 906` 的回归、以及"填它们服务端侧不能【单独】工作"

## 一、范围

本报告学习 `sv_native_playerstate_mp.cpp` 820–1160 行（`SV_OverlayPlayerStateToNative` 的收尾、`altWeaponSlots` 的完整病历、`SV_OverlayNativePlayerStateToPlayerState` 的开头与三十个 `refuse`）。

## 二、**"四十个项共用一个 `return false`"**（本组最重要的一段）

### 2.1 那段

```php
// ONE `return false` FOR FORTY TERMS. This is the reverse admission for the
// native playerState, and it runs inside a ROUND TRIP: SV_ClientSpawn writes
// this buffer from a struct it just built, reads it straight back, and refuses
// the spawn if anything here trips. So a term failing does not mean the value
// is bad -- it means the writer and the reader disagree about WHERE that field
// lives, and on a per-build layout that is the likeliest thing in the file.
// Naming the term turns "the player never spawns" into one offset to check.
const auto refuse = [failureReason](const char *const reason) {
    if (failureReason)
        *failureReason = reason;
    return false;
};
```

### 2.2 二十四层

```text
1. **四十个项【共用一个 `return false`**】**
2. ⇒ **这是【原生 `playerState` 的反向准入**】**
3. ⇒ **而它【跑在【一个往返里**】】**
4. ⇒ **`SV_ClientSpawn` 【从它刚构建的一个结构【写这个缓冲**】】**
5. ⇒ **⇒ 【直接读回来**】**
6. ⇒ **⇒ 而【如果这里的任何东西触发，就拒绝那个出生**】**
7. ⇒ **⇒ 所以【一个项失败【不意味着那个值是坏的**】】**
8. ⇒ **⇒ 它意味着【写者与读者【对那个字段【住在哪里【不一致**】】**
9. ⇒ **⇒ 而【在一个逐 build 的布局上，那是【这个文件里最可能的东西**】】**
10. ⇒ **⇒ 给那一项【命名**把"玩家永不出生"变成【一个要检查的偏移**】】
```

### 2.3 ⭐⭐⭐ **"一个项失败不意味着那个值是坏的 —— 它意味着写者与读者对那个字段住在哪里不一致"**

**✅ 这是本报告里**最重要的一条"一个反向准入的真正含义**。**

**✅ 与 §437 的"五个（实为八）拒绝都返回同一个 `false`"**——**完全同族** ✓

**⇒ 三层**：
```text
值错 ⇒ **数据的问题**
偏移错 ⇒ **写者与读者的分歧**（**一个逐 build 的布局问题**）
⇒ **⇒ 所以【在那个往返里，后者【最可能**】
```

**✅ ⭐⭐⭐ **"在那个往返里后者最可能"** —— 一个**极精确的概率判断**。

**⚠ 而"`SV_ClientSpawn` 从它刚构建的结构写这个缓冲，直接读回来"⇒ **一个自往返**。**

**⇒ 三层**：
```text
写：**我们的结构 ⇒ 原生字节**
读：**原生字节 ⇒ 我们的结构**
⇒ **⇒ 所以【任何失败【都是【我们自己**的不一致**】
```

**✅ ⭐⭐⭐ **"任何失败都是我们自己的不一致"** —— 一个**极重要的判断**。</br>

**✅ 与 §460 的"`SwaySpeed` 明确不搬对方数字"**同族（**一个一致性纪律**）。

### 2.4 而**三十个 `refuse` 的清单**

```text
pmType / bobCycle / movementDir / clientNum
groundEntity / viewEntity / linkEntity / movingPlatform
remoteEyes / remoteControl / remoteTurret
viewmodelIndex / rightWeaponAnim / leftWeaponAnim
rightWeaponState / leftWeaponState
currentWeapon / offhandWeapon / rewardActionType / rewardActionWeapon
offhandWeaponSlots
weaponPositionFraction / aimSpreadScale / spreadOverride / spreadOverrideState
viewHeightLerpDown / legsTimer / torsoTimer / torsoAnim / legsAnim
weaponRestrictKickTime / weaponHandFlags / weaponShotCount（+ 后续）
```

**⇒ 三十三个以上。**

### 2.5 ⭐⭐⭐ **`viewmodelIndex > MaximumViewmodelIndex` ⇒ `refuse("viewmodelIndex")`**

**✅ 与 §460 的"`MaximumViewmodelIndex = 0x3FF`"**完全闭合 ✓

**⇒ 三层**：
```text
§460  **"用 `0x7FF` 验证 viewmodel ⇒ 允许 snapshot 写者然后拒绝的值，【它把失败报告在整整一个阶段之外的地方**】"**
§462  **`refuse("viewmodelIndex")`** ⇒ **那个名字**
⇒ **⇒ 所以【§460 的修法【就是【加上这个名字**】
```

**✅ ⭐⭐⭐ **"§460 的修法就是加上这个名字"** —— 一个**跨报告的完整闭环**。

## 三、**`y 906` 的回归与"填它们服务端侧不能单独工作"**（本组第二重要）

### 3.1 那段

```php
// OFF BY DEFAULT, AND THE REASON IS THE RESULT. Measured 2026-09-02:
// the write is CORRECT -- `weapon slots a3E8=1224 b3EC=0 c3F0=1225
// current3F8=1224` against `1224 ** 306 (csg12ss) -> alt 1225
// (** 139 0 0 4422 10545 9321)`, host and alt both right, and the same
// for the AK -- and the player reported the server DESYNCING HEAVILY
// with the switch still not happening.
//
// That is the finding, not a defect in the write. These four fields are
// NOT in this build's playerState netfield table, so the client keeps
// predicting against zeros while the server predicts against real
// weapons, and the two diverge every frame. Filling them server-side
// cannot work ALONE.
//
// Which puts retail's `y 906` back in frame: section 140j lists it as
// one of THREE verbs in the dm demo this server has never sent, and it
// lands in the playerState weapon block on exactly the frames it is
// sent. Whatever fills these slots is something BOTH sides run.
```

### 3.2 二十层

```text
1. **默认关，而【理由是那个结果**】**
2. ⇒ **测量 `2026-09-02`：【那个写是对的**】**
3. ⇒ **`weapon slots a3E8=1224 b3EC=0 c3F0=1225 current3F8=1224`**
4. ⇒ **对 `1224 ** 306 (csg12ss) -> alt 1225 (** 139 0 0 4422 10545 9321)`**
5. ⇒ **⇒ 【主机与 alt 都对**】**
6. ⇒ **⇒ 而【对 AK 也一样**】**
7. ⇒ **⇒ 而【那个玩家报告【服务器【严重失同步**】】**
8. ⇒ **⇒ 【而那个切换【仍然没发生**】】**
9. ⇒ **⚠ 【那是一个发现，不是那个写的一个缺陷**】**
10. ⇒ **⇒ 因为这四个字段【不在这 build 的 `playerState` 网络字段表里**】**
11. ⇒ **⇒ 所以【客户端【继续对零**预测**】**
12. ⇒ **而【服务器【对真实武器**】预测**
13. ⇒ **⇒ 而【两者【每一帧【分歧**】】
14. ⇒ **⇒ 【填它们服务端侧【不能单独工作**】】**
15. ⇒ **⇒ 而那【把零售的 `y 906` 【放回框架里**】**
16. ⇒ **⇒ 第 `140j` 节把它列为 【dm demo 里这个服务器【从未发过**的三个动词之一】
17. ⇒ **⇒ 而它【在【被发的那些帧上】【落进**那个 `playerState` 武器块**
18. ⇒ **⇒ 【不管什么填这些槽，它是【两边都跑**的东西**】**
```

### 3.3 ⭐⭐⭐ **"那是一个发现，不是那个写的一个缺陷"**

**✅ 这是本报告里**最重要的一条"一个正确的写产生一个坏的结果**。**

**✅ 与 §452 的"一个测出的表【不是零售的 `aipaths`**】"**、§461 的"一个合法的弹药索引失败了出生"**同族**。

**⇒ 三层**：
```text
写：**正确**（**测量确认 `a3E8=1224`/`c3F0=1225` 与预期一致**）
结果：**严重失同步**
⇒ **⇒ 所以【不是那个写的缺陷，是一个【架构**的缺口**】
```

**✅ ⭐⭐⭐ **"不是那个写的缺陷，是一个架构的缺口"** —— 一个**极精确的归因**。

**⚠ 而"这四个字段不在这 build 的 `playerState` 网络字段表里"**⇒ **一个结构性的缺失**。**

**⇒ 三层**：
```text
我们的结构 ⇒ **有这四个字段**（`SvPlayerState` 的 `offhandWeaponSlotA/B/C`）
而【网络字段表【没有**】⇒ **客户端【不预测它们**】
⇒ **⇒ 所以【客户端对零而我们对真值**】
```

**✅ ⭐⭐⭐ **"客户端对零而我们对真值"** —— 一个**极清晰的失同步机制**。

**✅ 与 §429 的"`baseSent != baseHeld` ⇒ 永久偏移"**同族（**第六次"两端不一致**）。

**⇒ 三层**：
```text
§426  **`baselineCacheAcknowledged` 与 `deltaMessage` 必须一起清**
§429  **`baseSent ^ baseHeld` 一个永久的偏移**
§462  **客户端零而服务器真值 ⇒ 每帧分歧**
⇒ **⇒ 三次"两端不一致**】
```

**✅ ⭐⭐ **"两端不一致"三例表**。

### 3.4 而**`y 906` 的"不管什么填这些槽，它是两边都跑的东西"**

**⇒ 十层**：
```text
1. **`y 906` 是一个【从未发过**的动词**
2. ⇒ **⇒ 而它【在被发的那些帧上【落进**那个武器块**】
3. ⇒ **⇒ 所以【它【就是**一个"两边都跑"的候选**
4. ⇒ **⇒ 而【`140j` 说它是【三个**从未发过的动词之一**】
```

**✅ 与 §415 的"`v 18`"**——**一个同族的字母动词**。

**⇒ 三层**：
```text
`v 18` ⇒ **一个字母动词**（§404）
`y 906` ⇒ **一个字母动词**（§462）
⇒ **⇒ 而【`140j` 说有三个**
```

**⚠ 一个**可推导的第三例**。</br>

**✅ 与 §404 的"`w 2 4 0` 两次"**配合。

## 四、`altForceTest` 的"标记为仅用于可复现性"

```php
// The old opt-in OLMOD_ALT_FORCE_TEST experiment below is retained
// for reproducibility only; it seeds the throwback path with a gun's
// alternate asset. Do not enable it for normal equipment gameplay.
static const auto altForceTestEnabled = [] { ... };
```

**⇒ 八层**：
```text
1. **旧的可选实验【只为了可复现性**保留**】**
2. ⇒ **它【用一个武器的 alt 资产【给那个 throwback 路径【播种**】】**
3. ⇒ **⇒ 而【不要在【正常的装备玩法上**启用它**】
4. ⇒ **⇒ 所以【一个"保留但不要用**"的开关**
```

**✅ 与 §435 的"这缩短窗口，它不关闭它"**同族（**第四次"一个保留但不推荐的路径**）。

**⇒ 三层**：
```text
§404  **"窄回退不是诊断"**
§435  **"缩短窗口不关闭"**
§462  **"保留但不要用"**
⇒ **⇒ 三次"保留但**】
```

**✅ ⭐⭐ **"保留但"三例表**。

**⚠ 而"`sub_429DA0` 是 grenade THROWBACK，不是普通枪的 alt-mode"**⇒ **一个明确的否定**。**

**⇒ 三层**：
```text
`sub_429DA0` ⇒ **grenade THROWBACK**（**`ps+0x50` 是引信，`+0x54` 是手雷武器，`+0x254` 是提示实体**）
⇒ **⇒ 所以【它不是【普通枪的 alt-mode**的证据**】
```

**✅ ⭐⭐⭐ **"`sub_429DA0` 不是普通枪 alt-mode 的证据"** —— 与 §462 三 的"那是一个发现，不是一个缺陷"**互补**。</br>

**✅ 而"`sub_429640/429450/429AE0` 是 offhand 的 prepare/init/use 路径【尽管它们的旧 IDB 名字】"**⇒ **一个名字与实际功能的差异**。

**⇒ 三层**：
```text
旧 IDB 名字 ⇒ **暗示 alt-mode**
实际 ⇒ **offhand 的 prepare/init/use**
⇒ **⇒ 所以【一个"名字不承载意义"的实例**
```

**✅ 与 §417 的"`clientNum` 是一个错的 MW3 名字"**同族（**第三次"名字不承载意义**）。

**⇒ 三层**：
```text
§415  **`demoq` 把 `21` 标为 `ET_ACTOR_CORPSE` 而它们不是尸体**
§417  **`+0x09C` 的 `clientNum` 是一个错的 MW3 名字**
§462  **`sub_429640/429450/429AE0` 的旧 IDB 名字暗示 alt-mode 而实际是 offhand**
⇒ **⇒ 三次"名字不可信**】
```

**✅ ⭐⭐ **"名字不可信"三例表**。

## 五、`DualWieldActive` 的"从 `heldWeapons` 的 `unknownState[0]`"

```cpp
const auto currentHeld = std::ranges::find_if(
    source.heldWeapons,
    [&source](const SvHeldWeaponState &weapon) {
        return weapon.weaponAssetIndex == source.currentWeaponAssetIndex;
    });
const auto dualWieldActive =
    currentHeld != source.heldWeapons.end() && currentHeld->unknownState[0];
writeValue(destination, DualWieldActiveOffset, static_cast<std::int32_t>(dualWieldActive));
```

**⇒ 十层**：
```text
1. **找到【当前武器**那一项**
2. ⇒ **若找到且 `unknownState[0]`** ⇒ **`dualWieldActive = true`**
3. ⇒ **⇒ 所以【一个"未知状态"的第 `0` 位【被解释为**双持**】
4. ⇒ **⇒ 而这与 §416 的 `unknownState` 的四位**配合**
```

**✅ 与 §416 的"四个 `bool` 的 `unknownState`"**——**一个语义的赋予**。

**⇒ 三层**：
```text
§416  **`std::array<bool, 4> unknownState{}`**（**四个"未知"的位**）
§462  **`unknownState[0]` ⇒ `dualWieldActive`**
⇒ **⇒ 所以【一个"未知"的位【被赋予了**一个名字**】
```

**✅ ⭐⭐⭐ **"一个未知的位被赋予了一个名字"** —— 与 §462 四 的"名字不可信"**互补**（**那里**拒绝一个名字**，这里**赋予一个名字**）。

**⇒ 三层**：
```text
否定：**旧 IDB 名字暗示 alt-mode ⇒ 实际不是**
赋予：**`unknownState[0]` ⇒ `dualWieldActive`**
⇒ **⇒ 两个方向**
```

**✅ ⭐⭐ **"两个方向"**。

## 六、关键结论

1. **⭐⭐⭐ "四十个项共用一个 `return false`；这跑在一个往返里 —— `SV_ClientSpawn` 从它刚构建的结构写这个缓冲、直接读回来，而如果任何东西触发就拒绝那个出生 ⇒ 一个项失败【不意味着那个值是坏的】，它意味着【写者与读者对那个字段住在哪里不一致】，而在一个逐 build 的布局上那是【这个文件里最可能的东西】"`** ⇒ **"给那一项命名把『玩家永不出生』变成【一个要检查的偏移】**"`。
2. **⭐⭐⭐ "在那个往返里，偏移错比值错更可能"** ⇒ **"任何失败都是我们自己的不一致"`**（因为**一个自往返**）。
3. **⭐⭐ `refuse("viewmodelIndex")` 与 §460 的 `MaximumViewmodelIndex = 0x3FF` 的修正完全闭合** —— **"§460 的修法就是加上这个名字"**（一个跨报告的完整闭环）。
4. **⭐⭐⭐ `altWeaponSlots` 的完整病历**：**"测量 `2026-09-02`：那个写【是对的**】（`a3E8=1224 b3EC=0 c3F0=1225 current3F8=1224` 对 `1224 ** 306 (csg12ss) -> alt 1225`，主机与 alt 都对，AK 也一样），**而那个玩家报告服务器【严重失同步】而那个切换【仍然没发生**】"` ⇒ **"那是一个发现，不是那个写的一个缺陷"`**。
5. **⭐⭐⭐ "这四个字段【不在这 build 的 `playerState` 网络字段表里】，所以【客户端继续对零预测】而【服务器对真实武器预测】⇒ 两者每一帧分歧 ⇒ 【填它们服务端侧不能单独工作】**"` ⇒ **"客户端对零而我们对真值"** —— 第六次"两端不一致"（与 §426/§429 同族）。
6. **⭐⭐⭐ "那把零售的 `y 906` 放回框架里：`140j` 把它列为 dm demo 里这个服务器从未发过的【三个动词之一】，而它在被发的那些帧上落进那个 `playerState` 武器块 ⇒ 不管什么填这些槽，它是【两边都跑】的东西"`**。
7. **⭐⭐ "`altForceTest` 的『保留但不要用』"**（"只为了可复现性"，"不要在正常的装备玩法上启用它"）—— 第三次"保留但"（与 §404/§435 同族）。
8. **⭐⭐⭐ "`sub_429DA0` 是 grenade THROWBACK（`ps+0x50` 是引信、`+0x54` 是手雷武器、`+0x254` 是提示实体），它不是普通枪 alt-mode 的证据"`** —— 而 **"`sub_429640/429450/429AE0` 是 offhand 的 prepare/init/use 路径【尽管它们的旧 IDB 名字】"`** ⇒ **"名字不可信"**（第三次，与 §415/§417 同族）。
9. **⭐⭐ `DualWieldActive` 从 `heldWeapons` 的 `unknownState[0]` 派生** ⇒ **"一个『未知』的位被赋予了一个名字"** —— 与上面"名字不可信"**互补**（**那里拒绝一个名字，这里赋予一个名字**）。

## 七、未闭合点

- 四十个项的确切数量与我数到的三十三个的差。
- `y 906` 的完整语义。
- `140j` 的三个从未发过的动词的完整清单。
- `unknownState[1..3]` 的语义。
- `sv_native_playerstate_mp.cpp` 1160 行之后未读取（**共 `1687` 行**）。
