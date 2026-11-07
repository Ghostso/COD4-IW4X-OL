# 483 · **"你**能**换到**一把**枪而你**不能**开火，那**不是**一个可用的**alt-fire**"** —— `sv_client_spawn_mp.cpp` 的 `SV_LookupAltWeapon` vs `…ForHost`、`4253` 次快照回弹、以及"零不是一个权威的值，是一个未设的值"

## 一、范围

本报告学习 `sv_client_spawn_mp.cpp`（**`427` 行**）全文件：`equipResolvedLoadout` 的 alt 武器循环、`SV_ClientSpawn` 的十道准入、`perks` 的三位字、`playerSizeScale` 的零陷阱、`unarmed` 的双副本分歧、以及 `SV_SetNativeHoldBreathState`。

## 二、**"你能换到一把枪而你不能开火，那不是可用的**alt-fire**"**（本组最重要的一段）

### 2.1 那段

```cpp
// SECTION 190: AND EACH WEAPON'S ALT, BECAUSE A GUN YOU CAN SWITCH
// TO AND CANNOT FIRE IS NOT A WORKING ALT-FIRE.
...
for (const auto &base : { loadout.primary, loadout.secondary })
{
    // SECTION 191z: ...FOR_HOST. `SV_LookupAltWeapon` takes an
    // ALT and resolves it -- "returns false when the index is
    // not an alt of anything", its own header says -- and this
    // handed it the HOST. It returned false every time, for
    // every weapon in every class, and the loop below never ran
    // once since section 190 shipped it.
    //
    // Measured, not inferred: the always-on `weapon slots` line
    // prints the held array and it read
    // `list2F4=1224,1226,0,0,0,0` on every sample -- primary,
    // secondary, and nothing. out.exe refuses a cmd.weapon that
    // is not in that array and stores a ZERO instead
    // (finish-weapon-change, 0x00424470), which is exactly
    // what the alt-weapon trace caught:
    // `03-post-pmove ps=1225 native=0`.
    SvResolvedWeapon alt{};
    if (!SV_LookupAltWeaponForHost(base.weaponAssetIndex, alt))
        continue;
```

### 2.2 二十四层

```text
1. **每一把武器的 alt 【也要【放【进【`heldWeapons`**】
2. ⇒ **⇒ 因为【一把【你能**换到**而【你不能**开火**的枪【不是【一个可用的 alt-fire**】
3. ⇒ **⚠ 而【那个函数【是 `SV_LookupAltWeapon`，它【取【一个 **ALT** 并解析它**】
4. ⇒ **（**它自己的头文件说**："**当一个索引【不是任何东西的 alt 时【返回 `false`**"）**
5. ⇒ **⇒ 而【这里【递给它【那个 **HOST**】
6. ⇒ **⇒ 所以【它【每一次【都【返回 `false`**】⇒ 对【每一个武器/每一个类**】
7. ⇒ **⇒ 所以【下面那个循环【自 §190 发布以来【一次【也没跑过**】
8. ⇒ **⚠ 【测量，不是推断**】：
9. ⇒ **⇒ 那个【常开的** `weapon slots` 行【打印那个**持有数组**】
10. ⇒ **⇒ 而它【在【每一个样本上【读 `list2F4=1224,1226,0,0,0,0`**】
11. ⇒ **⇒ 主武器、副武器、【然后【什么都没有**】
12. ⇒ **⇒ 而 `out.exe` 【拒绝一个【不在那个数组里的** `cmd.weapon`|
13. ⇒ **⇒ 而【改为【存一个**零**】（**finish-weapon-change，`0x00424470`**）**
14. ⇒ **⇒ 而那【正是【那个 alt 武器追踪【抓到的**】：`03-post-pmove ps=1225 native=0`**】
```

### 2.3 ⭐⭐⭐ **"它每一次都返回 false，对每一个武器、每一个类，而那个循环自 §190 发布以来一次也没跑过"**

**✅ 这是本报告里**最重要的一条"**一个 API 的**参数语义【反了，而那个错误【完全**静默**"**。**

**✅ 与 §474 的"`sv_bullet_mp` 从未运行"**、§479 的"每枚投掷物在第一帧被静默退役"**——**完全同族** ✓

**⇒ 三层**：
```text
§474  **四个 fire id 错 ⇒ 整条子弹链【从不运行**】
§479  **前置缺失 ⇒ 每个投掷物【静默退役**】
§483  **参数语义反 ⇒ 那个循环【一次也没跑**】
⇒ **⇒ 三次"一个**整链【静默地**死**"**
```

**✅ ⭐⭐⭐ **"一个整链静默地死"三例表**。

**⚠ 而"递给它 HOST 而它要 ALT"**⇒ **一个**极隐蔽的**参数错误**。**

**⇒ 十层**：
```text
`SV_LookupAltWeapon(altIndex, out)` ⇒ **要【一个 ALT**】
`SV_LookupAltWeaponForHost(hostIndex, out)` ⇒ **要【一个 HOST**】
⇒ **⇒ 所以【两个函数【名字【几乎一样**】而【语义【相反**】
```

**✅ ⭐⭐⭐ **"两个函数名字几乎一样而语义相反"** —— 一个**API 设计**的缺陷**。

**✅ 与 §477 的"`findWeapon` 的 loadout 优先，然后 alt"**——**同族**（**第二次"一个**回退【链【掩盖【一个**参数错**"**）。

**⚠ 而那个**测量链**】**。**

**⇒ 十六层**：
```text
① `weapon slots` 行【打印 `list2F4`**】
② 读到 `1224,1226,0,0,0,0`** ⇒ **⇒ 只有两个**（**primary + secondary**）
③ `out.exe` 【拒绝【不在那个数组里的 `cmd.weapon`**】（`0x00424470`**）**
④ ⇒ **⇒ 而【存一个**零**】
⑤ ⇒ **⇒ 而【那个追踪【看到 `ps=1225 native=0`**】（**`ps` 有值而 `native` 是零**）
```

**✅ ⭐⭐⭐ **"`ps=1225 native=0` — 一个 ps 有值而 native 是零"** —— 一个**极精确的症状**。

**✅ 与 §481 的"那个武器索引走进了一个事件字段"**——**同族**（**第三次"一个**错的值【在【一个错的层**上"**）。

## 三、**`perks` 的三位字与"它不是三个 perk，而是两个面向玩家的 perk 加一个内部的护甲专长"**（本组第二重要）

### 3.1 那段

```cpp
// SvRetailLivePerks is a retail OLfinal player's own word triple,
// and the perks it names ARE established now - mp/coPerkStatsTable
// .csv, 77 rows, out of code_post_gfx_mp.ff, decoded by
// Tools/olfinal/perk-bits.py:
//
//   word 0 bit 2  -> row 2   PERKS_LIGHTWEIGHT   modMoveSpeedScale
//   word 0 bit 7  -> row 7   PERKS_EXTREMECOND   modSprintTime -7
//   word 1 bit 24 -> row 56  specialty_destroyer_armor
//
// So it is TWO player-facing perks and one internal armor
// specialty, NOT the "three perks, so three icons" the old comment
// here claimed. Bit n of word w is row w*32+n, and the encoder
// turns 2,7,56 straight back into {132, 16777216, 0}.
```

### 3.2 二十四层

```text
1. **那个字三元组【是一个零售 OLfinal 玩家自己的**】
2. ⇒ **⇒ 而【它命名的 perks 【现在【已确立**】
3. ⇒ **⇒ （`mp/coPerkStatsTable.csv`，`77` 行，来自 `code_post_gfx_mp.ff`**）**
4. ⇒ **⇒ 由 `Tools/olfinal/perk-bits.py` 解码**】
5. ⇒ **`word 0` bit `2` ⇒ 行 `2`**】⇒ **`PERKS_LIGHTWEIGHT`（`modMoveSpeedScale`**）**
6. ⇒ **`word 0` bit `7` ⇒ 行 `7`**】⇒ **`PERKS_EXTREMECOND`（`modSprintTime -7`**）**
7. ⇒ **`word 1` bit `24` ⇒ 行 `56`**】⇒ **`specialty_destroyer_armor`**
8. ⇒ **⇒ 所以【那是【两个**面向玩家的 perk**】与【一个**内部的护甲专长**】
9. ⇒ **⇒ ⚠ 而【不是【那个旧注释【主张的【"三个 perk，所以三个图标**"】
10. ⇒ **⇒ 而【`word w` 的 bit `n` 【是行 `w*32 + n`**】
11. ⇒ **⇒ 而【那个编码器【把 `2` / `7` / `56` 【直接**变回 `{132, 16777216, 0}`**】
```

### 3.3 ⭐⭐⭐ **"两个面向玩家的 perk 与一个内部的护甲专长"**

**✅ 与 §482 的"那个 def 在每一个被测量过的地方确实不同，而那个 aarScoreboard 的行仍然逐字节相同"**——**同族**（**第四次"一个**事实【推翻【一个**旧主张**"**）。

**⚠ 而那几个**算术**】**。**

**⇒ 独立验证**：
```text
`word 0` bit `2` ⇒ **`1 << 2 = 4`** ⇒ **⇒ 而注释说 `{132, ...}`**】⇒ **`132 = 0b10000100 = 128 + 4`**】
⇒ **⇒ 所以【`word 0` 【有【两个位**：bit `2`（`4`）与 bit `7`（`128`）**
⇒ **⇒ `4 + 128 = 132`** ✓
`word 1` bit `24` ⇒ **`1 << 24 = 16777216`** ✓
⇒ **⇒ 所以【`{132, 16777216, 0}` 【正是【那三个位**】
```

**✅ ⭐⭐⭐ **"`132 = 4 + 128`、`16777216 = 1 << 24`、`0` —— 三个位全部精确"** —— 一个**完整的算术闭合**。

**⚠ 而"行 `w*32 + n`"**⇒ **一个**位到行的**映射**。**

**⇒ 十层**：
```text
`word 0` bit `2` ⇒ **行 `0*32 + 2 = 2`** ✓
`word 0` bit `7` ⇒ **行 `7`** ✓
`word 1` bit `24` ⇒ **行 `32 + 24 = 56`** ✓
⇒ **⇒ 所以【那个映射【正确**】
```

**✅ ⭐⭐⭐ **"那个映射正确"**。

**⚠ 而"`77` 行"**⇒ **`3` 个字 × `32` 位 = `96` 个可能的位，而只有 `77` 行**。**

**⇒ 三层**：
```text
`77` 行 ⇒ **而【三个字【共 `96` 个位**】
⇒ **⇒ 所以【还有 `19` 个位【没有**行**】（**或【那第 `4` 个字【不存在**）
```

**✅ ⭐⭐⭐ **"还有 19 个位没有行"** —— 一个**可推导的余量**。

### 3.4 而**"在 spawn 上归零，是有意的"**

```cpp
// ZERO ON SPAWN, on purpose. The client's perk HUD adds a perk
// only on the frame its bit goes clear-in-cache to set-in-ps
// (sub_52B8E0), so writing the final value here would spend the
// only edge there is before the HUD is necessarily alive.
// ServerCore re-asserts the real value a moment later, which is
// what retail's own traffic does on every life.
```

**⇒ 二十层**：
```text
1. **客户的 perk HUD 【只在【它的位【从【缓存的零【变成【ps 里的一**的那一帧【添加**一个 perk**】（`sub_52B8E0`**）**
2. ⇒ **⇒ 所以【在这里【写【最终值【会【烧掉【那个**唯一的边沿**】
3. ⇒ **⇒ 而在【那个 HUD 【必然**还活着之前**】
4. ⇒ **⇒ 所以【ServerCore 【稍后【重新断言【真正的值**】
5. ⇒ **⇒ 而那【正是【零售自己的流量【在【每一次生命【上**做的**
```

### 3.5 ⭐⭐⭐ **"写最终值会烧掉那个唯一的边沿"**

**✅ 与 §470 的"`requiredMapAspectRatio = 0` ⇒ 不扩张"**——**不同**（那是一个**禁用**，这是一个**时序**）但**同族**（**第六次"一个**边沿【必须【被【保留**"**）。

**⇒ 三层**：
```text
若【写最终值**】⇒ **⇒ 那个位【从【零【直接【到**最终**】⇒ **⇒ 一个**边沿**】
而【HUD 【可能【还没【活着**】⇒ **⇒ 那个边沿【被【浪费**】
⇒ **⇒ 所以【归零 + 稍后断言【是【唯一**的正确做法**】
```

**✅ ⭐⭐⭐ **"归零 + 稍后断言是唯一的正确做法"** —— 一个**极精确的时序**。

**✅ 与 §475 的"`BoxOfferMs = 10000` 的下降"**——**同族**（**第二次"一个**两阶段【的时序**"**）。

## 四、**"零不是一个权威的值，它是一个未设的值"**（本组第三重要）

### 4.1 那段

```cpp
// Preserve the authoritative pre-spawn value established by the
// player initializer instead of silently re-hardcoding normal
// scale on every respawn.
//
// BUT ZERO IS NOT AN AUTHORITATIVE VALUE, IT IS AN UNSET ONE. The field
// is `float playerSizeScale{}` and nothing in this tree ever assigns it,
// so a first spawn preserved 0.0 and published it. EngineBindings records
// the meaning: PM_GetStandHeight = round(playerSizeScale * 60), and this
// same struct hardcodes viewHeightCurrent to 60.0f -- which IS scale 1.0.
// A player was therefore published at zero size while standing 60 units
// tall, and the client drew a viewmodel that filled the entire screen.
// Preserve any positive value, which keeps the respawn intent intact, and
// treat non-positive as unset.
.playerSizeScale = playerState.playerSizeScale > 0.0f
    ? playerState.playerSizeScale
    : 1.0f,
```

### 4.2 二十四层

```text
1. **保留那个【前置条件【建立的权威之前-生成值**】而不是【在每次重生时【静默地【重新硬编码**正常尺度**】
2. ⇒ **⚠ 而【零【不是**一个权威的值**】⇒ **⇒ 【它是一个**未设的值**】
3. ⇒ **⇒ 而那个字段【是 `float playerSizeScale{}`**】⇒ **⇒ 而【这棵树里【没有东西【赋过它**】
4. ⇒ **⇒ 所以【一个第一次生成【保留了 `0.0` 并【发布了它**】
5. ⇒ **⇒ 而 `EngineBindings` 【记录**那个语义**】：`PM_GetStandHeight = round(playerSizeScale * 60)`**
6. ⇒ **⇒ 而【同一个结构【硬编码 `viewHeightCurrent = 60.0f`**】⇒ **⇒ 而那【正是**尺度 `1.0`**】
7. ⇒ **⇒ 所以【一个玩家【在【被【发布【为零尺寸**时【站着 `60` 单位高**】
8. ⇒ **⇒ 而【客户端【画了一个【填满【整个屏幕**的 viewmodel**】
9. ⇒ **⇒ 所以【保留任何正值，那【保持【重生**的意图完整**】
10. ⇒ **⇒ 而【把非正**当成【未设**】
```

### 4.3 ⭐⭐⭐ **"一个玩家在零尺寸上被发布，而站着 60 单位高，于是客户端画了一个填满整个屏幕的 viewmodel"**

**✅ 这是本报告里**最具体的一条"**一个未设的零【产生【一个**可见的崩坏**"**。**

**✅ 与 §477 的"一个多人手雷炸了但不伤人"**——**同族**（**第三次"一个**逻辑缺【产生【一个**可见的症状**"**）。

**⇒ 三层**：
```text
`playerSizeScale = 0` ⇒ **`PM_GetStandHeight = round(0 × 60) = 0`**
而 `viewHeightCurrent = 60` ⇒ **⇒ 【矛盾**】
⇒ **⇒ 所以【客户端【一个【零尺寸**的玩家【在【一个 `60` 单位高处**】
```

**✅ ⭐⭐⭐ **"一个零尺寸的玩家在一个 60 单位高处"** —— 一个**极精确的矛盾**。

**✅ 与 §481 的"`es+96 <- ps` 与 `es+100 <- ps`"**——**同族**（**第四次"一个**两处【数据【必须【一致**"**）。

**⚠ 而那个**判据**】**。**

**⇒ 十层**：
```text
正值 ⇒ **保留**（**重生【保持【那个**意图**）
非正 ⇒ **`1.0`**（**一个**未设**的值【被【替换【成【正常尺度**）
⇒ **⇒ 所以【那个三元【是【一个**正确的**判据**】
```

**✅ ⭐⭐⭐ **"那个三元是一个正确的判据"**。

**✅ 与 §475 的"零=禁用"**——**相反**（那里**零【是【一个**有意的**禁用**】；这里**零【是【一个**未设**的意外**）**。**

**⇒ 三层**：
```text
§444/§465/§467  **`0` ⇒ 禁用**（**一个**有意的**哨兵**）
§483  **`0` ⇒ 未设**（**一个**意外的**默认**）
⇒ **⇒ 所以【同一个值【两种**语义【由【那个字段的**历史**决定**】
```

**✅ ⭐⭐⭐ **"同一个值两种语义，由那个字段的历史决定"** —— **本报告最精确的判据**。

## 五、**`unarmed` 的"两个副本被允许分歧"**（本组第四重要）

### 5.1 那段

```cpp
// AN UNARMED SPAWN HANDS THE ENGINE NO WEAPON AT ALL.
//
// The source copy keeps dmz_empty_mp, because that is what the CLIENT needs to
// draw a pair of hands. The native buffer must not: the weapon-movement stage
// reads the current weapon out of it and refuses any nonzero value that is not
// in the frozen loadout, and empty hands can never be in a loadout -- the
// validator demands a clip, an ammo pool and a fire time, and fists have none.
// A refused stage discards the usercmd, and a discarded usercmd is the player
// snapping back to spawn. MEASURED: 4,253 of them in one session, all
// `weapon=1137`.
//
// AFTER THE ROUND TRIP, DELIBERATELY. The gate above compares the whole
// projected struct back against the source and refuses the spawn on any
// difference, so zeroing this before it would refuse every unarmed spawn.
// This is the one field the two copies are allowed to disagree about, and the
// think re-establishes the source side at the end of every frame.
```

### 5.2 二十四层

```text
1. **一个【空手**的生成【交给【引擎【完全没有**武器**】
2. ⇒ **⇒ 而那个**源**副本【保留 `dmz_empty_mp`**】（**⇒ 因为【那【是【客户端【需要的**，为了【画一双手**）**
3. ⇒ **⇒ 而那个**原生**缓冲【必须**不**保留它**】
4. ⇒ **⇒ 因为【武器移动阶段【从它那里【读【那个当前武器**】
5. ⇒ **⇒ 而【拒绝【任何【不在【那个冻结装备里的**非零值**】
6. ⇒ **⇒ 而【空手【永远不能在一个装备里**】⇒ **⇒ 因为【校验器要求【一个弹匣、一个弹药池、一个开火时间**】
7. ⇒ **⇒ 而【拳头【一个都没有**】
8. ⇒ **⇒ 而【一个被拒绝的阶段【丢弃那个 usercmd**】
9. ⇒ **⇒ 而【一个被丢弃的 usercmd 【就是【那个玩家【弹回**到生成点**】
10. ⇒ **⚠ 【测量：一个会期里 `4,253` 次，全部 `weapon=1137`**】
11. ⇒ **⚠ 而【在那个往返**之后，故意的**
12. ⇒ **⇒ 因为【上面那个门【比较【整个投影的结构【回【对那个源**】
13. ⇒ **⇒ 而【在它之前【归零【会【拒绝【每一个**空手生成**】
14. ⇒ **⇒ 而【这是那两个副本【被允许【分歧**的唯一字段】
15. ⇒ **⇒ 而【那个 think 【在【每一帧末尾【重新建立**那个源侧**】
```

### 5.3 ⭐⭐⭐ **"一个被拒绝的阶段丢弃那个 usercmd，而一个被丢弃的 usercmd 就是那个玩家弹回生成点"**

**✅ 这是本报告里**最精确的一条"**一个校验【产生【一个**玩家可见的**行为**"**。**

**✅ 与 §474 的"一个被拒绝的事件拒绝整个 usercmd"**——**完全同族** ✓

**⇒ 三层**：
```text
§474  **`Invalid` ⇒ 拒绝整个 usercmd（**伤害 + 移动**）**
§483  **一个被拒绝的阶段 ⇒ 丢弃 usercmd ⇒ 弹回生成点**
⇒ **⇒ 两次"一个**拒绝【的【爆炸半径【是【整个** usercmd**"**
```

**✅ ⭐⭐⭐ **"一个拒绝的爆炸半径是整个 usercmd"两例**。

**⚠ 而"`4,253` 次，全部 `weapon=1137`"**⇒ **一个**极具体的**测量**。**

**⇒ 独立核算**：
```text
若【一个会期【有 `N` 帧**】⇒ **⇒ 而 `4,253` 次**】
⇒ **⇒ 所以【每一帧【至少一次**】（**若那个会期【约 `4253` 帧 ⇒ `142` 秒 @ 30Hz**）
```

**✅ ⭐⭐⭐ **"约 4253 帧 ⇒ 142 秒 @ 30Hz"** —— 一个**可推导的时长**。

**⚠ 而"`weapon=1137`"**⇒ **一个**具体的**资产号**。**

**⇒ 三层**：
```text
`1137` ⇒ **那是 `dmz_empty_mp` 的资产索引**】
⇒ **⇒ 所以【那个日志【恰好【点名【那个**空手武器**】
```

**✅ ⭐⭐ **"那个日志恰好点名那个空手武器"**。

### 5.4 而**"这是那两个副本被允许分歧的唯一字段"**

**✅ 与 §462 的"自往返的错误"**、§481 的"`roundTrip != next` ⇒ 拒绝"**——**一个精确的例外** ✓

**⇒ 三层**：
```text
一般规则 ⇒ **`roundTrip == next`**（**§481/§462**）
例外 ⇒ **`unarmed` 的 `currentWeaponAssetIndex`**（**源 `1137` / 原生 `0`**）
⇒ **⇒ 所以【那个例外【被【显式**命名【并【放在【那个门【之后**】
```

**✅ ⭐⭐⭐ **"那个例外被显式命名并放在那个门之后"**。

**✅ 而"那个 think 在每一帧末尾重新建立那个源侧"**⇒ **"一个**持续的**修正**"**。**

**⇒ 十层**：
```text
若【不重新建立**】⇒ **⇒ 那个源侧【会在【下一帧【被【原生【覆写**】
若【每帧重建**】⇒ **⇒ 那个不一致【被【限制在【一帧**】
⇒ **⇒ 所以【那是一个**有界的**分歧**
```

**✅ ⭐⭐⭐ **"那是一个有界的分歧"**。

## 六、**`playerSizeScale` 的 `+0x98 → +0xAC`**（本组第五重要）

### 6.1 那段

```cpp
// OLMOD(section-84): +0x98 is 3.3.3.3's. On out.exe the field is at
// +0xAC -- read off its own height family, seven functions at
// 0x004104B0..0x004105D0 that all do `fld [eax+0ACh]` and multiply
// by 15/70/50/30/60/40/11, the same seven constants in the same
// order as 3.3.3.3's 0x00412410..0x00412530. So the 60 below is
// this build's number too, not an inherited one.
```

### 6.2 二十四层

```text
1. **`+0x98` 【是 3.3.3.3 的**】
2. ⇒ **⇒ 而在 `out.exe` 上【那个字段【在 `+0xAC`**】
3. ⇒ **⇒ 从【它自己的高度族**读出来**】
4. ⇒ **⇒ （`0x004104B0..0x004105D0` 的**七个函数**，全部做 `fld [eax+0ACh]`**）**
5. ⇒ **⇒ 而【乘**以 `15/70/50/30/60/40/11`**】
6. ⇒ **⇒ 而【那七个常量【同样的顺序【与 3.3.3.3 的 `0x00412410..0x00412530`**】
7. ⇒ **⇒ 所以【下面那个 `60` 【也是【这个 build 的数**，不是【一个继承的**】
```

### 6.3 ⭐⭐⭐ **"同样七个常量，同样的顺序"**

**✅ 与 §481 的"两张 `ET_PLAYER` 网络字段表按 `(bits, codec)` 对齐"**——**同族**（**第五次"一个**跨 build 的**对齐**"**）。

**⇒ 三层**：
```text
§468  **`81,128/81,128` 零失配**（**哈希**）
§481  **`(bits, codec)` 对齐**（**网络字段表**）
§483  **七个常量同样的顺序**（**高度族**）
⇒ **⇒ 三次"一个**跨 build 的一致性**"**
```

**✅ ⭐⭐⭐ **"一个跨 build 的一致性"三例**。

**⚠ 而"那个 `60` 与 `viewHeightCurrent = 60.0f`**"**⇒ **一个**双重出现**。**

**⇒ 十层**：
```text
`playerSizeScale` 的默认 ⇒ **`1.0`**（**scale**）
`viewHeightCurrent` ⇒ **`60.0f`**（**单位**）
⇒ **⇒ 而 `PM_GetStandHeight = round(1.0 × 60) = 60`** ✓
⇒ **⇒ 所以【两者【一致**】
```

**✅ ⭐⭐⭐ **"两者一致（1.0 × 60 = 60）"** —— 与 §483 四 的矛盾**对照**。

## 七、`SV_ClientSpawn` 的**十道准入**

### 7.1 十道

```text
① config.clientNum > MaxClientNum (63)          ⇒ admission/clientNum
② !finiteVector(config.origin)                  ⇒ admission/origin_not_finite
③ !finiteVector(config.angles)                  ⇒ admission/angles_not_finite
④ config.groundEntityNum > MaxEntityNum (2047)  ⇒ admission/groundEntityNum
⑤ !config.gravity                               ⇒ admission/gravity_zero
⑥ !config.speed                                 ⇒ admission/speed_zero
⑦ moveSpeedScaleMultiplier ≤ 0                  ⇒ admission/moveSpeedScaleMultiplier
⑧ config.viewmodelIndex > 0x3FF                 ⇒ admission/viewmodelIndex
⑨ !maxHealth || maxHealth > 0xFF                ⇒ admission/maxHealth
⑩ !SV_IsResolvedLoadoutValid(loadout)           ⇒ admission/resolved_loadout_invalid
```

### 7.2 二十四层

```text
1. **十道，而【每一道【命名**】
2. ⇒ **⇒ 而【那个理由【是【一个 `const char *`**】（**不是【一个枚举**）**
3. ⇒ **⇒ 而【注释说**："**在【构造任何一个所有者之前**拒绝**】
4. ⇒ **⇒ 所以【一个无效的 profile/运行时输入【不能【部分地【重置一个玩家**】
```

### 7.3 ⭐⭐⭐ **"在构造任何一个所有者之前拒绝，所以一个无效的输入不能部分地重置一个玩家"**

**✅ 与 §471 的 `GlassCommandRollback`**、§477 的 `replaceFactoryEquipment`**——**同族**（**第七次"一个**两阶段提交**"**）。

**⇒ 三层**：
```text
全部十道【在一个候选构造**之前**】⇒ **⇒ 无部分状态** ✓
而【那个候选【是【一个**局部的** `SvPlayerState next`**】⇒ **⇒ 只在【最后【`playerState = std::move(next)`**】
⇒ **⇒ 所以【三层原子性**：准入 / 候选 / 提交**
```

**✅ ⭐⭐⭐ **"三层原子性：准入 / 候选 / 提交"**。

**⚠ 而"`MaxClientNum = 63`"**⇒ **`0..63`**，而 **`MaximumGameClients = 18`**（§469/§472/§477）**。**

**⇒ 十层**：
```text
`MaxClientNum = 63` ⇒ **一个**协议**的上界**（`6` 位**）
而 `MaximumGameClients = 18` ⇒ **一个**游戏**的上界**】
⇒ **⇒ 所以【两个**不同的界**】（**协议 vs 玩法**）
```

**✅ ⭐⭐⭐ **"两个不同的界：协议 vs 玩法"** —— 而**`63` 恰好【是 `6` 位**的顶**】**。

**✅ 与 §481 的"`clientNum > 0x3F` ⇒ 拒绝"**——**完全一致** ✓

## 八、关键结论

1. **⭐⭐⭐ "每一把武器的 alt 也要放进 `heldWeapons`，因为**一把你能换到而不能开火的枪不是一个可用的 alt-fire**"`** ⇒ 而那个 bug 是 **"`SV_LookupAltWeapon` 取一个 **ALT** 并解析它（它自己的头文件说『当一个索引不是任何东西的 alt 时返回 false』），而这里递给它那个 **HOST** ⇒ 它每一次都返回 `false`，对每一个武器、每一个类，而那个循环自 §190 发布以来**一次也没跑过**"`** ⇒ **第三次"一个整链静默地死"**（与 §474/§479 同族）。
2. **⭐⭐⭐ 那个测量链**：**`weapon slots` 行读 `list2F4=1224,1226,0,0,0,0`**（**只有 primary + secondary**）⇒ **`out.exe` 拒绝一个不在那个数组里的 `cmd.weapon` 并改存一个**零**（`0x00424470`）** ⇒ **追踪看到 `03-post-pmove ps=1225 native=0`**（**一个 ps 有值而 native 是零**）。
3. **⭐⭐⭐ `perks` 的三位字**：**`mp/coPerkStatsTable.csv`，`77` 行，来自 `code_post_gfx_mp.ff`，由 `perk-bits.py` 解码** ⇒ **word 0 bit 2 → 行 2 (`PERKS_LIGHTWEIGHT`) / word 0 bit 7 → 行 7 (`PERKS_EXTREMECOND`) / word 1 bit 24 → 行 56 (`specialty_destroyer_armor`)** ⇒ **"两个面向玩家的 perk 与一个内部的护甲专长，不是『三个 perk 所以三个图标』"`**；**独立验证：`1<<2 = 4`、`1<<7 = 128` ⇒ `4 + 128 = 132` ✓、`1<<24 = 16777216` ✓ ⇒ `{132, 16777216, 0}` 正是那三个位**；而 **`行 = w*32 + n`** 也独立验证（`0*32+2=2`、`1*32+24=56`）。
4. **⭐⭐⭐ "在 spawn 上归零，是有意的：客户的 perk HUD 只在它的位从『缓存的零』变成『ps 里的一』的那一帧添加一个 perk（`sub_52B8E0`），所以在这里写最终值会**烧掉那个唯一的边沿**，而在那个 HUD 必然还活着之前"`** ⇒ **"归零 + 稍后断言是唯一的正确做法"`**。
5. **⭐⭐⭐ `playerSizeScale` 的零陷阱**：**"零不是一个权威的值，是一个未设的值 —— 那个字段是 `float playerSizeScale{}` 而这棵树里没有东西赋过它，所以一个第一次生成保留了 `0.0` 并发布了它；`PM_GetStandHeight = round(playerSizeScale * 60)` 而同一个结构硬编码 `viewHeightCurrent = 60.0f`（那正是尺度 `1.0`）⇒ **一个玩家在零尺寸上被发布而站着 60 单位高，于是客户端画了一个填满整个屏幕的 viewmodel**"`** ⇒ 修法是 **`> 0.0f ? 保留 : 1.0f`** ⇒ **"同一个值（`0`）两种语义，由那个字段的历史决定"`**（与 §444/§465/§467 的"零=禁用"**相反**）。
6. **⭐⭐⭐ `unarmed` 的双副本分歧**：**"一个空手的生成交给引擎**完全没有武器**：源副本保留 `dmz_empty_mp`（那是客户端画一双手需要的），而原生缓冲必须不保留 —— 武器移动阶段从它读当前武器并拒绝任何不在冻结装备里的非零值，而空手永远不能在装备里（校验器要求弹匣/弹药池/开火时间，拳头一个都没有）⇒ 一个被拒绝的阶段丢弃那个 usercmd，而**一个被丢弃的 usercmd 就是那个玩家弹回生成点**。测量：一个会期里 `4,253` 次，全部 `weapon=1137`"`** ⇒ 而修法**必须在那个往返门之后**（否则会拒绝每一个空手生成）⇒ **"这是那两个副本被允许分歧的唯一字段，而那个 think 在每一帧末尾重新建立那个源侧"`** ⇒ **"那是一个有界的分歧"`** —— 与 §474 的"一个拒绝的爆炸半径是整个 usercmd"同族；**独立推得 `4253` 帧 ≈ `142` 秒 @ 30Hz**。
7. **⭐⭐⭐ `playerSizeScale` 的 `+0x98 → +0xAC`**：**"从它自己的高度族读出：`0x004104B0..0x004105D0` 的七个函数全部做 `fld [eax+0ACh]` 并乘以 `15/70/50/30/60/40/11`，同样七个常量、同样的顺序，与 3.3.3.3 的 `0x00412410..0x00412530` 一致"`** ⇒ **"下面那个 `60` 也是这个 build 的数，不是一个继承的"`** —— 第三次"一个跨 build 的一致性"（与 §468/§481 同族）。
8. **⭐⭐⭐ `SV_ClientSpawn` 的十道准入全部具名**（`admission/clientNum` / `origin_not_finite` / `angles_not_finite` / `groundEntityNum` / `gravity_zero` / `speed_zero` / `moveSpeedScaleMultiplier` / `viewmodelIndex` / `maxHealth` / `resolved_loadout_invalid`）⇒ **"在构造任何一个所有者之前拒绝，所以一个无效的输入不能部分地重置一个玩家"`** ⇒ **"三层原子性：准入 / 候选 / 提交"`**。
9. **⭐⭐ `MaxClientNum = 63` 与 `MaximumGameClients = 18` 是两个不同的界**（协议 `6` 位 vs 玩法），而 `63` 恰好是 `6` 位的顶 —— 与 §481 的"`clientNum > 0x3F` ⇒ 拒绝"**完全一致**。
10. **⭐⭐ `equipResolvedLoadout` 的弹药压实**：`clipSize` 用 `std::max` 累加、`maxAmmo` 用 `min(0x7FF, count + maxAmmo)` 求和（**一个 `TODO(CODOL)` 明确标注"这不是原生 ClientSpawn 行为"**）。

## 九、`sv_client_spawn_mp.cpp` 全文件总览

**`427` 行。**

**`6` 个常量**：`MaxClientNum = 63` / `MaxEntityNum = 2047` / `EFlagTeleportBit = 1<<1` / `PmFlagRespawned = 1<<10` / `SpawnClearedButtonMask = 0x300` / `WeaponAnimationToggleBit = 0x400`。

**`4` 个函数**：`finiteVector` / `equipResolvedLoadout` / `SV_ClientSpawn` / `SV_EquipResolvedLoadout`。

**`10` 条准入理由 + `2` 条构造期理由**（`equip_resolved_loadout` / `native_round_trip_mismatch`）。

**`13` 个测量锚点**：
```text
list2F4=1224,1226,0,0,0,0（weapon slots 常开行）
0x00424470（finish-weapon-change 存零）
03-post-pmove ps=1225 native=0（alt 武器追踪）
mp/coPerkStatsTable.csv 77 行 / code_post_gfx_mp.ff
{132, 16777216, 0} = {1<<7|1<<2, 1<<24, 0}
sub_52B8E0（perk HUD 的边沿消费者）
PM_GetStandHeight = round(playerSizeScale * 60)
0x004104B0..0x004105D0 七个高度函数 / 15,70,50,30,60,40,11
0x00412410..0x00412530（3.3.3.3 的同族）
4,253 次 usercmd 丢弃，全部 weapon=1137
dmz_empty_mp = 资产 1137
0x3FF（viewmodel 界） / 0xFF（maxHealth 界）
```

## 十、未闭合点

- **⚠ 一个编号歧义（`EFlagTeleportBit`）**：`.cpp:22` 是 `constexpr std::uint32_t EFlagTeleportBit = 1u << 1;` ⇒ **`0x02`**，而 `.cpp:220` 的注释写 **"toggle eFlags bit 2"**。
  ```text
  若"bit 2"是【0 基】（1 << 2）⇒ **`0x04`** ⇒ **而代码【是 `0x02`** ⇒ 差一位**
  若"bit 2"是【1 基】（第 2 个位 = 1 << 1）⇒ **`0x02`** ⇒ **与代码一致** ✓
  ⇒ **⇒ 两种读法【都自洽**，而【注释【没有【指明**是哪一种**
  ```
  **旁证**：同一段注释把 `pm_flags` 写成 **`0x400`**（一个十六进制字面量，无歧义），而 `PmFlagRespawned = 1u << 10 = 0x400` **精确一致** ⇒ 那段注释在 `pm_flags` 上用的是**数值**，在 `eFlags` 上用的是**位号** ⇒ **口径不统一**。
  **⚠ 标注为一个需要现场验证的候选差异**（按 `AGENTS.md` 的层级，需先查本 build 的 `BG_*` 里那个 toggle 的真实掩码，而不是照搬 IW4X 的 `EF_TELEPORT_BIT`）。
- `PmFlagRespawned = 1<<10 = 0x400` 与注释"set pm_flags 0x400"一致 ✓。
- 那 `19` 个没有行的 perk 位。
- `dmz_empty_mp = 1137` 的独立确认。
- 下一个文件：`sv_forge_image_mp.cpp`（`21,038` 字节）。
