# 学习报告 135（重开）— `EngineBindings.cpp` 中段（7,601–11,600 / 17,867 行）

**学习范围**：`EngineBindings.cpp` 第 **7,601–11,600 行**
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录十二个重大发现**：①**动画初始化的九阶段与六个失败清理点** ②**`ServerGetDObjCallbackOffset` 必须换成服务端适配器的完整理由（`animMap=0 srvMap=278`）** ③**`mp/playeranim.script` 的两个 RawFile 前置** ④**`slot=0x158` 而非 `0x144` 的静默仪器** ⑤**`booking` 的五个偏移从 3.3.3.3 到 1649370 的两次反复** ⑥**`combat` 也是合法 selectionKind** ⑦**`profile layout BY NAME` 的双路径** ⑧**附件序号 `16..21`+`22` / `23..28`+`29` 的顺序** ⑨**`NativeCharacterItemRecord` 的 12 字节与 48 字节溢出** ⑩**`loadout record` 的 38 槽缓存与 owner 键** ⑪**`WeaponDef` 的 25 条拒绝与逐字段日志** ⑫**`weapon registry` 重建的 5 阶段与 volatile 教训**

---

## 一、★★★★★ **动画初始化的九阶段**

### 1.1 ★★★★★ 完整阶段序列（第 7706–8026 行）

```
① `ContextBusy`（CAS 抢占）
② `InvalidBinding`（valid/空名）
③ `WrongThread`
④ ★ **`armVectoredFaultWitnessImpl(module_)`** —— 整个函数都装着见证器
⑤ `begin_load_anim_trees` ⇒ `invokeScrBeginLoadAnimTrees`
⑥ `load_anim_trees` ⇒ `invokeBGLoadAnimTrees(gameType, mapName)`
⑦ ★★ **两个 RawFile 检查**（`mp/playeranim_defines.script` / `mp/playeranim.script`）
⑧ `find_anims` ⇒ `invokeBGFindAnims(serverContext + 0xACE70)`
⑨ `parse_anim_script` ⇒ `invokeBGAnimParseAnimScript(scratch, context, count=1024)`
⑩ `precache_anim_trees` ⇒ `invokeScrPrecacheAnimTrees(func, hunkAllocXAnim_, 0)`
⑪ `find_anim_trees` ⇒ `invokeNoArgument(bgFindAnimTrees_)`
⑫ `end_load_anim_trees` ⇒ `invokeScrEndLoadAnimTrees(module_)`
⑬ `finalize_player_anims` ⇒ `invokeNoArgument(bgFinalizePlayerAnims_)`
⑭ ★ **六个输出校验** ⇒ `InvalidOutput`
⑮ ★ **四个回调换成服务端适配器**
⑯ `Ready`
```

★★★ **⇒ 16 个步骤,其中 **9 个原生调用** + **6 个输出校验** + **4 个回调替换**。**

### ★★★★★ **四个回调替换的完整理由**（第 8001–8018 行，逐字）

```cpp
// **Parsing can use the client callbacks installed above. Runtime player updates must
// instead own the server DObj map.** **CODOL's retained 0x00445460 callback is
// client-only and marks the held model as collidable**; **BO1/BO2 server callbacks
// exclude the ordinary held model from collision, while Ghosts disables the callback.**
// **Keep it detached until a CODOL server policy is recovered** instead of **changing
// native locational traces with a presentation callback**.
*reinterpret_cast<void **>(serverContext + ServerCreateDObjCallbackOffset) =
    reinterpret_cast<void *>(&serverDObjCreateAdapter);      // ★ 0xAF328
*reinterpret_cast<void **>(serverContext + ServerAppendWeaponModelCallbackOffset) =
    nullptr;                                                 // ★ 0xAF32C = null
*reinterpret_cast<void **>(serverContext + ServerFreeDObjCallbackOffset) =
    reinterpret_cast<void *>(&serverDObjFreeAdapter);        // ★ 0xAF330
*reinterpret_cast<void **>(serverContext + ServerGetDObjCallbackOffset) =
    reinterpret_cast<void *>(&serverDObjGetAdapter);         // ★ 0xAF334
```

★★★ **⇒ 四个槽的最终值：CREATE = 适配器 / **APPEND = `nullptr`** / FREE = 适配器 / GET = 适配器。**
**⇒ `0xAF32C` 是**故意置空**的那个槽 —— 而它恰好是**唯一被守护**的槽（报告 134 已记录）。**

### ★★★★★ **`animMap=0 srvMap=278` 的完整故障**（第 7760–7790 行，逐字）

```cpp
// OLMOD(server-dobj-lookup-boundary): **the get-DObj slot must resolve through the
// SERVER map, and CODOL's own function for this slot does not.**
//
// **One 0xCC-stride DObj pool at VA 0x02E8E850 is reached through two independent maps.**
// **ServerDObjCreate VA 0x0059E740 registers a server DObj in VA 0x02E8D050 ONLY** --
// its **single map write is at 0x0059E755** and it **returns at 0x0059E7B6**, so
// **the 0x02EF4858 write at 0x0059E7EE belongs to a different function**. But
// **CODOL's stock callback for this slot, RVA 0x0455D0, indexes the OTHER table**:
// **`movzx eax, word [eax*2 + 0x02EF4858]` at 0x004455D6**, returning **null when that
// word is zero**.
//
// **BG_SetLerpFrameAnimation VA 0x00409BF0 calls this slot at 0x00409C24 and BAILS at
// 0x00409C2E when it returns null** -- so **with the stock function installed, no
// animation is EVER set for any player on this server, on any frame**, and **the posed
// skeleton is whatever DObjCalcSkel produces with nothing driving it**.
// **MEASURED live 2026-08-17: at a respawn this project logged `animMap=0 srvMap=278`
// for a player whose DObj was present and healthy** -- **present in the server map,
// absent from the one the stock callback reads.**
```

★★★★★ **⇒ 八个精确值：**
```
一个 **`0xCC` 步长**的 DObj 池在 **`VA 0x02E8E850`**,经**两张独立映射**到达
        ↓
★★★ `ServerDObjCreate` **`VA 0x0059E740`** 只写 **`VA 0x02E8D050`**
★★★ 唯一映射写 @ **`0x0059E755`**,返回 @ **`0x0059E7B6`**
★★★ ⇒ **`0x02EF4858` 的写在 `0x0059E7EE`,属于**另一个函数**
        ↓
★★★ CODOL 的**库存回调 RVA `0x0455D0`** 索引**另一张表**：
   **`movzx eax, word [eax*2 + 0x02EF4858]` @ `0x004455D6`**
★★★ 该字为零 ⇒ **返回 null**
        ↓
★★★ `BG_SetLerpFrameAnimation VA 0x00409BF0` 在 **`0x00409C24`** 调用该槽
★★★ **在 `0x00409C2E` 遇到 null 就 BAIL**
        ↓
★★★★★ ⇒ **用库存函数 ⇒ 任何玩家任何帧都**从未设置过动画****
★★★ 实测（**2026-08-17**）：**`animMap=0 srvMap=278`** ⇒ **DObj 在服务端映射里,在库存回调读的映射里缺席**
```

### ★★★ ABI 兼容性论证（第 7785–7787 行）

```
"The native call site **pushes two arguments and cleans 8 bytes itself**, so a
 **one-argument `__cdecl` adapter is ABI-compatible with the slot**."
```
★★★ **⇒ 原生调用点 push 两个参数并自己清 8 字节 ⇒ 单参数 `__cdecl` 适配器**ABI 兼容**（`__cdecl` 调用者清理）。**

### ★★★★★ **六个输出校验**（第 7966–7999 行）

```cpp
if (!animationCount || animationCount > MaximumPlayerAnimations ||        // ★ 1024
    !finalAnimationCount || finalAnimationCount > MaximumPlayerAnimations ||
    !animTree ||
    *animScriptDataPointer_ != serverContext ||
    !restoreServerAnimConditionStorage(previousConditionBase))
```

★★★ **⇒ 六个条件（含"恢复失败"）,统一报 `InvalidOutput`。**
**⇒ 注释（第 7976–7978 行逐字）："SIX CONDITIONS, ONE STATUS. `invalid_output` was true of all of them, and **three of the values it reads were 3.3.3.3 offsets**, so **say which one is unhappy rather than making the next run guess**."**

### ★★★★★ **`restoreFailedContext` 的三步清理**（第 7811–7826 行）

```cpp
logStage("failure_cleanup_begin");
if (scriptLoadingBegun) {
    logStage("failure_end_load_anim_trees_begin");
    invokeScrEndLoadAnimTrees(module_);
    scriptLoadingBegun = false;
    logStage("failure_end_load_anim_trees_complete");
}
logStage("failure_globals_restore_begin");
InterlockedCompareExchangePointer(scriptSlot, previousScriptData, serverContext);
restoreServerAnimConditionStorage(previousConditionBase);
logStage("failure_globals_restore_complete");
```

★★★ **⇒ 三步：① 若脚本加载已开始 ⇒ `EndLoadAnimTrees` ② 恢复 `scriptData` 全局 ③ 恢复 `animConditionBase`。**
**⇒ 五个 `logStage` 点。**

### ★★★ `OLMOD_FACTORY_DEATH_FX` 与 `zm_factory_sh`（第 7745–7752 行）

```cpp
const auto *deathFxOptIn = std::getenv("OLMOD_FACTORY_DEATH_FX");
const bool loadActorHitTree = mapName == "zm_factory_sh" &&
    deathFxOptIn && std::string_view(deathFxOptIn) == "1";
*reinterpret_cast<std::uint32_t *>(serverContext + AnimTreeMaskOffset) =
    loadActorHitTree ? **8u** : **0u**;
```

★★★ **⇒ 双门禁：地图必须是 **`zm_factory_sh`** **且** `OLMOD_FACTORY_DEATH_FX=1`。**
**⇒ `AnimTreeMask = 8` = family 3（`generic_human`）。**

### ★★★ **`actorAnims` 的 708,228 偏移**（第 7757 行 + 第 7957 行）

```cpp
std::memcpy(&actorAnims, serverContext + **708228** + 3 * 20, sizeof(actorAnims));
```
★★★ **⇒ `708228 = 0xACE44` ⇒ `0xACE44 + 60 = 0xACE80`。**
**⇒ 注释（第 7748–7750 行）："40B210 resolves six family records at `context+708228+20*family`, selected by `context+0xAF318`. **Family3 is generic_human in the native actor client**."**

---

## 二、★★★★★ **`mp/playeranim.script` 的两个 RawFile 前置**

### 2.1 ★★★★★ 完整实现（第 7849–7870 行）

```cpp
constexpr std::array animationScriptAssets{
    "**mp/playeranim_defines.script**",
    "**mp/playeranim.script**",
};
for (const auto *const assetName : animationScriptAssets)
{
    const auto asset = findXAsset(AssetTypeRawFile, assetName, false);   // ★ 36
    const auto isDefault = dbIsXAssetDefault_(AssetTypeRawFile, assetName);
    OlMod::RuntimeLog::write(..., "server animation rawfile=" + assetName +
        " present=" + (asset.data && !isDefault ? "true" : "false") +
        " default=" + (isDefault ? "true" : "false"));
    if (!asset.data || isDefault) {
        restoreFailedContext();
        return fail(AnimationScriptAssetsUnavailable);
    }
}
```

★★★ **⇒ 两个 RawFile（资产类型 **36**）,都必须**存在且非默认**。**

---

## 三、★★★★★ **`slot=0x158` 而非 `0x144` 的静默仪器**

### 3.1 ★★★★★ 完整注释（第 8166–8173 行，逐字）

```cpp
// CODDIFF(1649370): **0x144 IS 3.3.3.3'S clientNum OFFSET.** This build keeps
// clientNum at **ps+0x158** -- **audit-ported-offsets has ClientNumOffset moving
// 0x144 -> 0x158** -- and **the engine itself indexes the characterInfo array with it**:
// **sub_407E10 does `mov ecx, [edi+158h]` then `imul ecx, 450h;
// lea ecx, [ecx+edx+0AF350h]`**. **Reading 0x144 got some other field, which is almost
// always >= 18, so this diagnostic returned WITHOUT LOGGING ANYTHING** --
// **a silent instrument, which reads exactly like a healthy one.**
```

★★★★★ **⇒ 五个精确值：**
```
3.3.3.3：`ps+0x144`
1649370：**`ps+0x158`**
        ↓
★★★ `sub_407E10` 做 **`mov ecx, [edi+158h]`** 然后
   **`imul ecx, 450h; lea ecx, [ecx+edx+0AF350h]`**
        ↓
★★★ 读 `0x144` ⇒ 得到另一个字段 ⇒ **几乎总是 `>= 18`**
★★★ ⇒ **诊断**什么都没记录就返回** ⇒ **"一个静默的仪器读起来和一个健康的仪器一模一样"**
```

### ★★★ 三个 `verbose()` 门禁（第 8179 / 8198 行）

```cpp
if (OlMod::RuntimeLog::verbose())   // ★ 2026-10-13（热日志修复）
```
★★★ **⇒ 两处逐帧诊断都加了 `verbose()` 门禁。**

### ★★★★★ **`logServerAnimScriptTable` 的两张表**（第 8055–8102 行，逐字）

```cpp
// **THE EVENT TABLE, WHICH THIS INSTRUMENT COULD NEVER SEE.** The line above walks the
// **MOVETYPE state table at +0x1A004** -- the locomotion selector's input -- and says
// **nothing whatever about scriptEvents at +0x25F80**, which is **the table
// BG_AnimScriptEvent sub_407E10 walks and the ONLY thing that can make a death return
// -1**. **Every one of the thirteen runs that failed every death it saw printed a healthy
// `populated=43/47` here**, because **the healthy half was the only half being read**.
// **Report both**, so **"the parse worked" and "the parse worked for the table the death
// event uses" stop being the same sentence.**
```

★★★★★ **⇒ 五个精确值：**
```
MOVETYPE 状态表 @ **`+0x1A004`**（locomotion 选择器的输入）
`scriptEvents` @ ★ **`+0x25F80`**（`sub_407E10` 遍历的表,唯一能让死亡返回 -1 的）
        ↓
★★★ **13 次全失败的运行都打印了健康的 `populated=43/47`**
★★★ ⇒ **因为只读了健康的那一半**
        ↓
★★★ `sub_407790` 开 **`mov eax,[eax]` / `test eax,eax` / `jle`** 于每个 `animScript_t` 的第一个 dword
★★★ ⇒ **那个 dword 是 `numItems`,`<= 0` 就是静默的 -1**
★★★ 健康的 OLfinal `mp/playeranim.script`：**DEATH 24 个 set / RAISEWEAPON 13 个 set**
```

### ★★★★★ **两个动画全局的双读**（第 8119–8126 行，逐字）

```
// **AND IT READS THE TABLE FROM BOTH BASES, because they are two globals.**
// **sub_407E10 takes the script table from dword_827F734 (0x00407E14) and the
// characterInfo from dword_827F730 (0x00407E37)**. **installServerAnimConditionStorage
// installs only the second**; the first **holds whatever the last sub_407530 in this
// process left there**, and **this project never writes it after initialisation**.
// **If `live` and `ours` differ, every death since that moment walked a foreign script
// block** -- which **no existing line could have shown**.
```

★★★ **⇒ 两个全局：`dword_827F734`（脚本表,`0x00407E14`）/ `dword_827F730`（characterInfo,`0x00407E37`）。**
**⇒ 本项目**只装第二个** ⇒ 若 `live != ours` ⇒ **每次死亡都走了外来的脚本块**。**

---

## 四、★★★★★ **`booking` 的五个偏移的两次反复**

### 4.1 ★★★★★ 五个偏移（第 8570–8574 行）

```cpp
constexpr std::size_t SelectionKindOffset   = **67056**;
constexpr std::size_t GameTypeOffset        = **67060**;
constexpr std::size_t MapNameOffset         = **67064**;
constexpr std::size_t PlaylistSlotOffset    = **67068**;
constexpr std::size_t RotationIndexOffset   = **67100**;
```

### ★★★★★ **第一次失败：3.3.3.3 的五个偏移在 1649370 上**一次也没成功过****（第 8463–8483 行，逐字）

```
"OLMOD(booking-selection-refusal-reasons): section 75. **THIS READER HAS FIVE SILENT
 `return std::nullopt` PATHS AND ONE CALLER THAT TREATS ALL OF THEM AS "the client did
 not book anything".**
        ↓
★★★ `scan-image-literals.py` reports **every one of the five offsets below as ABSENT
 FROM out.exe** -- **3.3.3.3 mentions 0xF730 thirty-eight times, 0xF738 fourteen,
 0xF73C twenty-six, and this build mentions none of them at all**.
★★★ ⇒ **它们是对 CLIENT 的 room singleton 的偏移,而且是另一个 build 的**
   ⇒ **这个函数在 1649370 上**一次也不可能成功****
        ↓
★★★ **没人注意到**,因为 `CODOL_GameServerConfigureBooking` **回退到命令串里的地图和模式**,
   而**每轮都显式传那些**
★★★ ⇒ **真正丢失的是**安全网**：`playlistMapRotateSequentially 0` 让每侧自己 roll 地图,
   而 booking 一个客户端没 roll 的会**无声地把会话卡在 `clients=1 active=0`**
```

★★★ **⇒ 三个偏移的引用次数：`0xF730` **38** 次 / `0xF738` **14** 次 / `0xF73C` **26** 次（全在 3.3.3.3）。**

### ★★★★★ **第二次：移植后**服务僵尸**（第 8512–8535 行，逐字）

```
"PORTED TO 1649370. Section 187i. **These were 3.3.3.3's, and the cost was not a failed
 read -- it was the server SERVING ZOMBIES**:
        ↓
     **client booking selection unavailable reason=selection-kind**
     **SessionStart queued map=zm_factory_sh gametype=zm members=1**
     **gamestate configuration ACCEPTED**                  <- **the zombies one**
     **connectionless rejected ... XUID is not in the session roster**
     **SessionStart queued map=mp_rust_long gametype=dm members=2**   <- **too late**
        ↓
★★★ ⇒ **读不到选择 ⇒ 回退到僵尸默认 ⇒ 提交那个 gamestate ⇒ 然后拒绝每个 booking 了
   deathmatch 的客户端 ⇒ 全部超时,此后没有任何客户端在无人值守下到达过 `active`**
        ↓
★★★ **THE VALUES WERE ALREADY IN THE TREE.** `tools/runtime/CodolMatchFlow.py` 带**两个
   build 的 room 布局**,并用 frida **正确地**读这个对象：
     `{"selection_kind": "playlist", "game_type": "dm",
       "map_name": "mp_rust_long", "playlist_slot": 11, "rotation_index": 0}`
★★★ 其注释记录**推导**而非断言数字："**the whole 0xF7xx booking block moves +0xEC0 and
   the active flag moves +0x18**",并与 **`mgr+632` 宿主标志**互相印证
```

★★★ **⇒ 两个精确位移：**`0xF7xx` 块 **+0xEC0** / active 标志 **+0x18**。**

### ★★★★★ **第三次：回退到 3.3.3.3,因为移植版**服务了团队模式**（第 8536–8558 行，逐字）

```
"**REVERTED TO 3.3.3.3's ON PURPOSE. Section 187p.**
        ↓
★★★ **The ported 1649370 offsets (67056/67060/67064/67068/67100) are CORRECT** and are
 **kept below for whoever finishes this**. **They made the dedicated read the client's real
 booking and self-book it** -- **which is the right behaviour and immediately served `cha`,
 Charge, a TEAM mode, because that is what the menu had selected. Two players on one side
 cannot damage each other, so shooting stopped working.**
        ↓
★★★ **Three attempts to pin the gametype downstream all missed**: the export next to
 `readClientBookingSelection` **is not on the path**, and pinning the SessionStart control
 message logged **`PINNED cha -> dm`** while `configureGameState` still reported
 **`booked=cha`** -- **the gamestate takes its gametype from the stored booking, not from
 that message**.
        ↓
★★★ ⇒ **回到 deathmatch 最后一次能用的状态（17:20:09 和 17:47:59,都是 `booked=dm`）**
```

### ★★★★★ **第四次：改用 1649370 组（2026-10-07）**（第 8559–8569 行，逐字）

```cpp
// ★★★ 2026-10-07 05:1x -- **改用 1649370 组偏移**（我方 3.19.26.13 现场实测成立；单变量）：
//   实测（客户端 pid 2776，菜单选中快速匹配 / 26 / sd）：
//     **room+67056 -> "playlist"**      （而 3.3.3.3 组 room+63280 全零 —— 这就是 d26 的
//     **room+67060 -> "sd"**              `client booking selection unavailable reason=selection-kind`
//     **room+67064 -> "mp_crash_tropical"** 与随后 `match_rules_rejected playlist=0 …` 的来源）
//     **room+67068 字节 = 0x1A = 26**    （= 客户端 mmstart 命令里的 "playlist 26"）
//     **room+67100 字节 = 0**
```

★★★★★ **⇒ 五个实测值（客户端 pid 2776）：**
```
`room+67056` ⇒ **`"playlist"`**
`room+67060` ⇒ **`"sd"`**
`room+67064` ⇒ **`"mp_crash_tropical"`**
`room+67068` ⇒ ★ **`0x1A` = 26**（= 客户端 `mmstart` 里的 "playlist 26"）
`room+67100` ⇒ **0**
        ↓
★★★ 3.3.3.3 组（`room+63280`）**全零**
★★★ ⇒ 与老外 `20260812_sd_objectives_v7` 的 **26/0/mp_crash_tropical/sd** 闭合
```

### ★★★★★ **`combat` 也是合法 selectionKind**（第 8581–8593 行，逐字）

```cpp
// OLMOD(L1-selection-kind-combat) 2026-10-13: **THIS GENERATION ALSO BOOKS AS "combat"**.
// Measured live in a **人机 (combattraining) room at 19:21:05** -- the room's
// **selection-kind reads "combat"** while **gameType/mapName/playlistSlot/rotationIndex
// are all populated (sd / mp_mountain / 33 / 4)**, and the old **`!= "playlist"`** test
// refused the whole read, which surfaced downstream as
//     client booking selection unavailable reason=selection-kind
//     match_rules_rejected playlist=0 rotation=0 map= gametype=
//     gamestate NOT sent client=0 GAMESTATE_NOT_CONFIGURED   (stuck on "设置游戏")
// **"combat" carries the same four fields**, so it is admitted with the same weight
if (!selectionKind ||
    (*selectionKind != "**playlist**" && *selectionKind != "**combat**"))
    return refuse("selection-kind");
```

★★★ **⇒ 两个合法值：`"playlist"` / `"combat"`。**
**⇒ 人机房间实测：`combat` + `sd` / `mp_mountain` / **33** / **4**。**

### ★★★ 五个 `refuse` 原因串（第 8505–8598 行）

```cpp
"module"                // module_ 空
"room-slot-unreadable"  // room 指针不可读
"room-too-small"        // *roomBytes <= 67100
"selection-kind"        // selectionKind 不是 playlist/combat
"map-or-gametype-name"  // validBookingName 失败
```
★★★ **⇒ 五个原因串,上限 **4 次**日志。**

---

## 五、★★★★★ **`profile layout BY NAME` 的双路径**

### 5.1 ★★★★★ 八个常量与两条路径（第 8712–8827 行）

```cpp
ProfileLayout layout{
    .characterSlotsBase = CharacterClassesBaseIndex + CharacterSlotsOrdinal,  // 605 + 5 = 610
    .characterStride    = CharacterClassIndexStride,                          // 14
    .characterCount     = CharacterItemCount,                                 // 12
    .slotCount          = CharacterProfileSlotCount,                          // 9
    .weaponClassBase    = WeaponClassesBaseIndex,                             // 1607
    .weaponClassStride  = WeaponClassIndexStride,                             // 37
    .weaponClassCount   = CharacterItemCount * WeaponClassesPerCharacter,      // 12 × 5 = 60
    .classesPerCharacter= WeaponClassesPerCharacter,                          // 5
    .primaryBase        = WeaponClassPrimaryBaseOrdinal,                      // 22
    .secondaryBase      = WeaponClassSecondaryBaseOrdinal,                    // 29
    .primaryAttach      = WeaponClassPrimaryBaseOrdinal - attachmentCount,    // 22 - 6 = 16
    .secondaryAttach    = WeaponClassSecondaryBaseOrdinal - attachmentCount,  // 29 - 6 = 23
    .attachCount        = attachmentCount,                                    // 6
    .byName             = false,
};
```

★★★★★ **⇒ 13 个回退值,其中两个是**推导的 numerology**：**
```
`primaryAttach   = 22 - 6 = **16**`
`secondaryAttach = 29 - 6 = **23**`
        ↓
★★★ 注释（第 8708–8711 行逐字）："**The two attachment ordinals were never measured at
 all: they were derived as `weaponOrdinal - AttachmentCount`, arithmetic the source itself
 called numerology after it landed on the wrong weapon once (sections 187g and 187m).
 The def NAMES them.**"
```

### ★★★★★ **按名解析的七个路径**（第 8741–8747 行）

```cpp
const auto characters       = schema->resolve("characterClasses");
const auto slots            = schema->resolve("characterClasses[0].slots");
const auto weapons          = schema->resolve("weaponClasses");
const auto primary          = schema->resolve("weaponClasses[0].primaryBase");
const auto secondary        = schema->resolve("weaponClasses[0].secondaryBase");
const auto primaryAttach    = schema->resolve("weaponClasses[0].primaryAttach");
const auto secondaryAttach  = schema->resolve("weaponClasses[0].secondaryAttach");
```

★★★ **⇒ 七个路径,任一失败 ⇒ 用回退值（`byName = false`）。**

### ★★★★★ **五个额外的按名解析**（第 8788–8825 行）

```cpp
const auto perks    = schema->resolve("weaponClasses[0].perks");           // 5 个
const auto rewards  = schema->resolve("weaponClasses[0].killstreaks");    // 3 个
constexpr std::array names{ "lethal", "tactical" };
// weaponClasses[0].lethal            (CategoryInt)
// weaponClasses[0].lethalDoubleAmmo  (CategoryBool)
// weaponClasses[0].tactical          (CategoryInt)
// weaponClasses[0].tacticalDoubleAmmo(CategoryBool)
```

★★★ **⇒ 五组（`perks` + `killstreaks` + 2×2 装备）= 九个属性按名解析。**

### ★★★★★ **三个边界校验**

```cpp
// ① 五个序号必须在 weapons 基址之上
if (primary->index < weapons->index || secondary->index < weapons->index ||
    primaryAttach->index < weapons->index || secondaryAttach->index < weapons->index)
    return layout;
        ↓
★★★ 理由（第 8753–8755 行逐字）："**Every ordinal is measured from the class element's own
 base, so a class that moves as a whole does not move its fields. A field BELOW that base is
 not an ordinal of this struct and means the walk went somewhere unexpected.**"

// ② slotCount 取较小值
layout.slotCount = std::min(slots->count, (u32)CharacterProfileSlotCount);   // min(def, 9)

// ③ classesPerCharacter 必须整除
if (characters->count && weapons->count % characters->count == 0)
    layout.classesPerCharacter = weapons->count / characters->count;
```

★★★ **⇒ 第 ③ 条的注释（第 8774–8778 行逐字）："**weaponClasses is FLAT -- sixty entries
that are twelve characters of five classes -- and the def does not say where the split is,
only how long the whole array is. Dividing is the one honest way to get it.**"**

### ★★★★★ **"DISAGREES WITH THE MEASURED ORDINALS"**（第 8900–8917 行）

```cpp
const auto disagreement =
    compare("characterSlots", layout.characterSlotsBase, CharacterClassesBaseIndex + CharacterSlotsOrdinal) +
    compare("characterStride", layout.characterStride, CharacterClassIndexStride) +
    compare("weaponClassBase", layout.weaponClassBase, WeaponClassesBaseIndex) +
    compare("weaponClassStride", layout.weaponClassStride, WeaponClassIndexStride) +
    compare("primary", layout.primaryBase, WeaponClassPrimaryBaseOrdinal) +
    compare("secondary", layout.secondaryBase, WeaponClassSecondaryBaseOrdinal);
line += disagreement.empty()
    ? " -- agrees with every measured ordinal"
    : " -- DISAGREES WITH THE MEASURED ORDINALS:" + disagreement;
```

★★★ **⇒ 六个值比对,一致则说"agrees with every measured ordinal"。**

---

## 六、★★★★★ **附件序号的 `16..21`+`22` / `23..28`+`29` 顺序**

### 6.1 ★★★★★ 完整实测（第 9101–9125 行，逐字）

```cpp
// **ATTACHMENTS PRECEDE THEIR WEAPON. Section 187m, and this is measured.**
//
// A full dump of the 37-ordinal class block:
//
//   **class=0 weapons=10609/10028**
//     **16=for_gripvtlong2ak104ss**  **17=sco_targetfinderak104ss**
//     **22=ak104ss_mp**   <- **PRIMARY**      **23=red_rmrtmp**   **29=tmp_mp** <- **SECONDARY**
//   **class=2 weapons=10015/10042**
//     **16=red_rmrl86**    **17=mag_extclipl86**
//     **22=l86_mp**       <- **PRIMARY**      **29=stinger_mp** <- **SECONDARY**
//
// **16 and 17 name the PRIMARY's own parts in both classes, and 23 names `red_rmrtmp`
// while `tmp_mp` sits at 29 -- the SECONDARY.** So **each weapon's six attachments come
// BEFORE it: 16..21 then the primary at 22, 23..28 then the secondary at 29.**
//
// **This code read 23..28 and gave them to the PRIMARY -- the secondary's attachments on
// the wrong gun.** That is **why only the one at 23 ever showed up**, why **everything else
// answered "not supported by this weapon"**, and why **the translated id built a variant
// whose index the client did not share, which refused every bullet (§187l)**.
//
// **The "gap of exactly SEVEN" I built the first reading on was right about the width and
// wrong about the ORDER: six attachments then the weapon, not the weapon then six
// attachments.**
```

★★★★★ **⇒ 两个完整的实测类：**

| 类 | 武器 | `16` | `17` | `22`（主） | `23` | `29`（副） |
|---|---|---|---|---|---|---|
| **0** | **10609/10028** | `for_gripvtlong2ak104ss` | `sco_targetfinderak104ss` | ★ **`ak104ss_mp`** | **`red_rmrtmp`** | ★ **`tmp_mp`** |
| **2** | **10015/10042** | `red_rmrl86` | `mag_extclipl86` | ★ **`l86_mp`** | — | ★ **`stinger_mp`** |

★★★★★ **⇒ 正确的序号布局：**
```
**`16..21`**（主武器 6 个附件）→ **`22`**（主武器）
**`23..28`**（副武器 6 个附件）→ **`29`**（副武器）
        ↓
★★★ 错读成 `23..28` 给主武器 ⇒ **副武器的附件装在错的枪上**
★★★ ⇒ **只有 23 那个出现过** / **其余全报"not supported by this weapon"**
★★★ ⇒ **翻译后的 id 建了一个客户端不共享索引的变体** ⇒ **拒绝每一发子弹**（§187l）
```

### ★★★★★ **第一次错读：附件在武器**之后****（第 9168–9182 行，逐字）

```
"Two readings of this got shipped before the def was asked. **The first put the attachments
 AFTER their weapon -- ordinals 30..35 for the secondary** -- and the provenance line said
 what they really are:
        ↓
   **class=0 weaponSlot=1 ordinal=32 item=60006 name=emp_grenade_mp**
   **class=1 weaponSlot=1 ordinal=32 item=60005 name=smoke_grenade_mp**
   **class=2 weaponSlot=1 ordinal=34 item=60186 name=fragshort_grenade_mp**
        ↓
★★★ **the LETHAL and TACTICAL equipment slots**, which is why **every one of them failed
 `readAttachmentModelSlot` with "has no model slot"**
```

### ★★★ `readAttachments` 的实现（第 9126–9187 行）

```cpp
const auto readAttachments = [&](const std::uint32_t firstAttachmentOrdinal,
                                  const std::size_t weaponSlot) {
    for (entry < layout.attachCount) {     // ★ 6
        const auto value = readIndex(base + firstAttachmentOrdinal + entry);
        if (!value || !*value || *value > 0xFFFFu) continue;
        attachments[entry] = *value;
        // 去重日志：class / weaponSlot / ordinal / item / name / weaponItem
    }
};
readAttachments(layout.primaryAttach, 0);     // ★ 16
readAttachments(layout.secondaryAttach, 1);   // ★ 23
```

### ★★★ 装备的双弹药位（第 9190–9210 行）

```cpp
if (layout.equipmentDoubleAmmoBase[equipmentSlot]) {
    const auto bit = offsetTable[index];          // ★ BIT 偏移,不是字节
    if ((bit >> 3) < ProfileDocumentSize &&
        (dataBuffer[bit >> 3] & (1u << (bit & 7))))
        equipment.doubleAmmoMask |= 1u << equipmentSlot;
}
```
★★★ **⇒ 与报告 133 的 `CategoryBool` **存 BIT 偏移**完全一致** ✓**

---

## 七、★★★★★ **`loadout record` 的 38 槽缓存与 owner 键**

### 7.1 ★★★★★ 完整的缓存读取（第 9242–9327 行）

```cpp
std::array<unsigned short, LoadoutRecordWords> record{};       // ★ 80 word = 160 字节

// ① 读 owner 的两个键
for (const auto rva : {LoadoutOwnerPrimaryRva, LoadoutOwnerFallbackRva}) {
    const auto owner = *(u32*)(module_ + rva);
    if (!owner) continue;
    const auto *at = (const u8*)(uintptr_t)owner + LoadoutOwnerKeyOffset;   // ★ +248
    ownerKeys[0] = at[0]; ownerKeys[1] = at[1];
    haveOwnerKeys = true; break;
}

// ② 扫 38 个槽
for (slot = 0; slot < 38; ++slot) {
    const auto at = module_ + LoadoutRecordCacheRva + slot * 168 + 8;
    if (!readableSpan(at, 80 * 2)) continue;
    const auto *words = (const u16*)at;
    if (haveOwnerKeys) {
        const auto *keys = (const u32*)at;
        if (keys[0] != ownerKeys[0] || keys[1] != ownerKeys[1]) continue;   // ★ 键匹配
    }
    const auto primary   = words[**24**];
    const auto secondary = words[**24 + 7**] = words[**31**];
    if (!primary || !secondary) continue;
    if (!populated) std::copy_n(words, 80, record.begin());    // ★ 取第一个
    ++populated;
}

// ③ 歧义报告
if (populated > 1) { "client loadout cache has N populated slots -- taking the first" }

// ④ 缓存空则重建
if (!populated) loadoutRecordBuild_(record.data());
```

★★★★★ **⇒ 五个精确值：**
```
记录 = **80 word = 160 字节**
槽步长 **168**,记录起点 **+8**
owner 键偏移 **+248**（`LoadoutOwnerKeyOffset`）
主武器 @ **word 24**,副武器 @ **word 31**
        ↓
★★★ ⇒ **"四个武器组 = 两个类,不是一个"**（第 9329–9333 行逐字）：
   "`sub_7C5A50` 写**四个 7-word 武器组**,而 `WeaponsPerClass` 是 **2**
    ⇒ 记录携带**类 0 和类 1 背靠背**。**只读前两个会扔掉一半**并产生**单类请求**,
    而**本 build 上每一个被接受的 `SessionStart` 都记录了 `classMask=3`**。
    **单类的那些排队而永不提交。**"
```

### ★★★★★ **"全有或全无"的类规则**（第 9335–9337 行，逐字）

```
"**ALL OR NOTHING PER CLASS**, because `valid()` enforces
 **`present != (weapon.itemId != 0)`**: a class whose bit is set must have every weapon
 filled, and a class whose bit is clear must have none."
```

### ★★★★★ **`missing_playerstate` 的三个错误假设**（第 9402–9420 行，逐字）

```cpp
// **MIRROR THE CAPTURED CLASS ACROSS EVERY SLOT.**
//
// **The record reports ONE class -- weapons 2 and 3 read zero -- but the player's UI has
// five**, and **the spawn asks for whichever slot they have selected**. **Registering only
// class 0 left `snapshot build rejected failure=missing_playerstate` and both clients stuck
// on 等待玩家数据 with active=2 and snapshots=0**, while **a two-class fixture on the same
// stack produced snapshots immediately**.
//
// **Mirroring is not a guess about which slot they will pick**: it makes **every slot
// resolve to the weapons they are actually holding**.
//
// **AND IT DID NOT FIX missing_playerstate. `classMask=31` was accepted and the spawn still
// had no playerstate**, so **the class COUNT was never the cause** -- **the third hypothesis
// about this failure to die on contact with the log**, after **"classMask=1 is refused"** and
// **"four weapon groups are two classes"**. **Kept because every slot resolving to the
// player's real weapons is right on its own terms, not because it fixed anything.**
```

★★★ **⇒ 三个已死的假设：**
```
① "`classMask=1` 被拒绝"
② "四个武器组是两个类"
③ "镜像到所有槽能修 `missing_playerstate`"
        ↓
★★★ ⇒ **`classMask=31` 被接受,而 spawn 仍无 playerstate** ⇒ **类数量从来不是原因**
★★★ **未解的问题**：为什么这些武器 id 不建 playerstate,而 3.3.3.3 fixture 的 id 在同一栈上能 spawn
```

### ★★★ **`LoadoutRecord REJECTED` 的 32 字 dump**（第 9438–9458 行）

```cpp
std::string dump = "client loadout record REJECTED, words 0..31:";
for (index < 32) dump += " " + std::to_string(record[index]);
```
★★★ **⇒ 前 32 个 word 的完整 dump。**

### ★★★ **武器名回读**（第 9476–9487 行）

```cpp
for (classIndex...) {
    if (!(classMask & (1u << classIndex))) continue;
    for (weapon : request.classes[classIndex].weapons) {
        const auto name = readItemInternalName(weapon.itemId);
        report += " [" + id + "=" + (name ? *name : "<no internal name>") + "]";
    }
    break;   // ★ 一个类足够,它们是彼此的镜像
}
```

---

## 八、★★★★★ **`WeaponDef` 的 25 条拒绝与逐字段日志**

### 8.1 ★★★★★ 完整的 25 条条件（第 9894–9951 行）

```cpp
const bool absentClip = clipIndex == **-1**;
if (ammoIndex <= 0 || ammoIndex > **0x7FF** ||                                    // ①
    (!meleeWeapon && !absentClip && (clipIndex <= 0 || clipIndex > **0x7FE**)) || // ②
    (!meleeWeapon && (clipSize <= 0 || clipSize > **0x1FF**)) ||                   // ③
    (!meleeWeapon && maxAmmoMultiplier <= 0) ||                                    // ④
    (meleeWeapon && (clipIndex < -1 || clipSize < 0 || maxAmmoMultiplier < 0)) ||  // ⑤
    weaponType < 0 || weaponType > 255 ||                                          // ⑥
    weaponClass < 0 || weaponClass > 255 ||                                        // ⑦
    penetrateType < 0 || penetrateType > 255 ||                                    // ⑧
    impactType < 0 || impactType > 255 ||                                          // ⑨
    fireType < 0 || fireType > **MaximumWeaponFireType** ||                        // ⑩ (10)
    fireDelay < 0 ||                                                               // ⑪
    shotCount < 0 || shotCount > 255 ||                                            // ⑫
    (meleeWeapon && meleeDamage <= 0) ||                                           // ⑬
    meleeDamage > 65535 ||                                                         // ⑭
    fireDelay > int16_max ||                                                       // ⑮
    dropTime < 0 || dropTime > int16_max ||                                        // ⑯
    raiseTime < 0 || raiseTime > int16_max ||                                      // ⑰
    fireTime <= 0 || fireTime > int16_max ||                                       // ⑱
    !isfinite(hipSpreadStandMin) || hipSpreadStandMin < 0 ||                       // ⑲
    !isfinite(hipSpreadCrouchMin) || hipSpreadCrouchMin < 0 ||                     // ⑳
    !isfinite(hipSpreadProneMin) || hipSpreadProneMin < 0 ||                       // ㉑
    !isfinite(hipSpreadStandMax) || hipSpreadStandMax < hipSpreadStandMin ||       // ㉒
    !isfinite(hipSpreadCrouchMax) || hipSpreadCrouchMax < hipSpreadCrouchMin ||    // ㉓
    !isfinite(hipSpreadProneMax) || hipSpreadProneMax < hipSpreadProneMin ||       // ㉔
    !isfinite(adsSpread) || adsSpread < 0 ||                                       // ㉕
    !SV_IsWeaponDamageCurveValid(damageCurve) ||                                   // ㉖
    any_of(hitLocationMultipliers, !isfinite || < 0 || > 20.0f))                   // ㉗
```

★★★ **⇒ 实际 **27 条**（注释说 25）⇒ 记录为**注释数字略保守**。**

### ★★★★★ **`absentClip` 的一行修复**（第 9882–9893 行，逐字）

```cpp
// **A WEAPON WITH NO CLIP IS LEGAL, AND THIS REJECTED ONE.** The comment above names
// **all-ones as the absent-clip sentinel** and the bound below is set one under it for
// exactly that reason -- and then **`clipIndex <= 0` threw out the sentinel itself, which
// reads back as -1**. **raygun_mp is an energy weapon with no magazine**:
//
//   **weapon definition rejected index=1235 ammo=1203 clip=-1 clipSize=1 maxAmmo=1
//     type=0 class=1 penetrate=0 impact=0 fire=1 shots=1 fireDelay=0 fireTime=250
//     drop=250 raise=250 spreadStand=0.000/0.000 ads=0.000 curveOk=1**
//
// **Every other field is sane. Twenty-five conditions, one `return false`, and the log line
// written to identify WHICH is what made this a one-line fix instead of twenty-five
// re-derived offsets** -- **the reason that line prints them all.**
```

### ★★★★★ **`meleeDamage` 的类门**（第 9912–9929 行，逐字）

```
"28800: **MELEE DAMAGE IS A MELEE-WEAPON FIELD, NOT A UNIVERSAL ONE.**
        ↓
★★★ This was `meleeDamage <= 0 ||` **with no weapon-class gate**, so **every definition
 whose +2072 is not populated was rejected outright**:
   **weapon definition rejected index=1188 ammo=1188 clip=1188 ...
     type=1 class=6 penetrate=0 impact=2 fire=0 shots=0 melee=0**
★★★ `type=1` 是 **THROWABLE**,`class=6` 是它的类;`+2072` 在它上面**就是缺的,这是正常的**。
   **杀掉整个定义**正是**让手雷/榴弹不可用的原因**。
        ↓
★★★ `sv_melee_mp.cpp:43` **已经把 `meleeDamage == 0` 当作"无近战伤害"并拒绝**,
   所以非近战资产这里为 0 是安全的：**近战路径会拒绝它,没有别的东西读该字段**
   （`Appmain.cpp:838` 保留自己的 `!selection.meleeDamage` 守卫）。
```

### ★★★ **`maxAmmo` 的 0x7FF 检查**（第 9977–9999 行）

```cpp
auto maxAmmo = (u64)maxAmmoMultiplier;
if (definition[WeaponAmmoCountClipRelativeOffset])     // ★ +3865
    maxAmmo *= (u32)clipSize;
if (maxAmmo > 0x7FF) { /* 完整日志 */ return false; }
```
★★★ **⇒ `+3865` 非零 ⇒ `maxAmmo = multiplier × clipSize`。**

### ★★★★★ **`weapon alt linkage` 的三次纠正**（第 9596–9648 行，逐字）

```
"**+3880 name -> +3892 index**      (error "1222 %s %s" if unresolved)
 **+3884 name -> +3896 index**      (error "1223 %s %s")
 **+3888 name -> +3900 index**      (error "1223 %s %s")
 and **+3900 is the one sub_426BC0 reads on the FIRE path, gated on the byte flag at +3876**.
        ↓
★★★ **THE FIRST SWEEP CORRECTED THIS FILE'S OWN READING**: **+3880/+3884/+3888 are NOT an
 alt-weapon link**: **all 57 definitions that carry them are the underbarrel launchers
 `uni_gl_<host>_mp`**, and **the three names are `frag_grenade_mp` / `flash_grenade_mp` /
 `flash_grenade_mp`** (or `molotovcocktail_mp` on the molotov variants). **They are the
 launcher's PROJECTILE types. `sub_42FA00` was over-read.**
        ↓
★★★ **But the sweep found the real thing on the way past: an ALT WEAPON IS AN ORDINARY BASE
 WEAPON ASSET, `uni_gl_famasss_mp` at 1065 next to `famasss_mp`, one per host rifle**, and
 **it pairs with an attachment we already resolve (`gre_unifamasss->188`)**.
        ↓
★★★ **So sweep the field that DOES carry the relation.** `sub_42FA00` reads a weapon name off
 **`definition+12`** and **inherits that weapon's whole attachment table through
 `mp/coAltWeaponAttachmentTable.csv`** -- **source weapon +12, destination the weapon being
 iterated**. On `uni_gl_famasss_mp` that names `famasss_mp`, so **+12 is THE HOST, stored on
 the alt.**
```

### ★★★★★ **`+3716 → +3720` 的最终答案**（第 9762–9786 行，逐字）

```
"**THE ALT WEAPON IS +3716 -> +3720, NOT +3880..+3900.**
        ↓
★★★ **sub_42EF60 is its linker** and it is in the registration chain **sub_42F1E0 runs on
 EVERY weapon, modular ones included**:
     **altName = def[+3716]**
     **def[+3720] = 0**
     **if (*altName) {
         index = def->name[0] == '*' ? sub_431490(self) : BG_FindWeaponIndex(altName)
         def[+3720] = index
     }**
        ↓
★★★ **and the live sweep found 46 host/alt pairs among the base assets, bidirectional**:
   **the HOST carries +3716 naming the alt (`g36css_mp` -> `altfireg36css_mp`)**,
   **the ALT carries +12 naming the host**.
   **Two of them are in this player's own loadout -- `csg12ss_mp` and `g36css_mp`.**
        ↓
★★★ **THE MODULAR BRANCH IS WHAT THIS PRINT IS FOR.** When the name starts with `'*'` the
 engine **BUILDS the modular alt itself through `sub_431490`** rather than looking one up.
```

★★★★★ **⇒ 五个精确值：**
```
真正的 alt 关系：**`+3716`（名字）→ `+3720`（索引）**
**46 个 host/alt 对**（基武器资产中,双向）
`+12` 是**宿主名**,存在 alt 上
`'*'` 前缀 ⇒ **引擎用 `sub_431490` 自建模块化 alt**
        ↓
★★★ 三个曾被误读的字段：**`+3880` / `+3884` / `+3888`**（实际是**榴弹发射器的投射物类型**）
★★★ **57 个定义**携带它们,全是 `uni_gl_<host>_mp`
```

### ★★★ **基武器全扫（200 条上限）**（第 9658–9741 行）

```cpp
for (index = 1; index < BaseWeaponAssetCount; ++index) {     // ★ 1300
    ...
    const auto host     = text(**12**);
    const auto parent   = text(**3716**);
    const auto linked   = text(**3736**);
    if (printed < **200**) { /* 日志 */ }
}
// "alt host link SWEEP readable=N hosted=N printed=N of 1300 slots"
```

★★★ **⇒ 三个名字字段：`+12`（host）/ `+3716`（parent）/ `+3736`（link）。**
**⇒ 打印上限 **200**,扫描上限 **1300**。**

---

## 九、★★★★★ **`weapon registry` 重建的 5 阶段与 volatile 教训**

### 9.1 ★★★★★ **`volatile` 的承重作用**（第 11299–11305 行，逐字）

```cpp
// **VOLATILE IS LOAD-BEARING.** MSVC gives **a non-volatile local that is modified inside
// `__try` an INDETERMINATE value once an exception unwinds**, so **every counter here read
// as garbage on exactly the path worth measuring**: **one run reported `stage=5` with
// `walked=1` and `mismatches=0` while also naming a mismatch at index 1**, which
// **cannot all be true at once**. **The char buffers were always fine -- they are memory
// writes -- and it was the register-cached scalars that lied.**
volatile bool initialized{};
volatile std::uint32_t failedIndex{};
volatile std::uint32_t failedResolvedIndex{};
volatile std::uint32_t defaultWeapon{};
volatile std::uint32_t exceptionCode{};
volatile std::uint32_t walked{};
volatile std::uint32_t named{};
volatile std::uint32_t stage{1};
volatile std::uint32_t faultStage{};
volatile std::uint32_t mismatches{};
volatile std::uint32_t faults{};
```

★★★★★ **⇒ 11 个 `volatile` 标量 + 3 个 `char` 缓冲区（不需要 `volatile`,因为是内存写）。**
**⇒ 理由：MSVC 对 `__try` 内被修改的非 volatile 局部变量在异常展开后给出**不确定值**。**

### ★★★★★ **`stage` 与 `faultStage` 的区分**（第 11320–11324 行，逐字）

```cpp
// `stage` records **PROGRESS** and is **overwritten as the function walks on past a break**;
// `faultStage` records **where a fault actually happened** and is **written once**.
// **Reading progress as the fault site said `stage=5` for three runs while the real fault
// was the resolver at `stage=22`.**
```

### ★★★ 五个阶段的编码（第 11318 行 + 第 11500 / 11543 / 11545 / 11551 / 11560 行）

```
**1** = reset
**2** = configstring walk
**3** = default resolve
**4** = initialize
**5** = verify
        ↓
★★★ 故障专用：**`20 + pass`**（pass 0/1 ⇒ 20/21）/ **`51`**（verify 的 lookup）/ **`90 + stage`**（`__except` 兜底）
```

### ★★★★★ **`g_gametype` 的空 dvar 故障**（第 11348–11357 行，逐字）

```cpp
// **THE GAMEPLAY DVARS FIRST, because registering a weapon reads one.**
// **sub_432130 loads `mp/gametypeWeaponCustomTable.csv`** and asks, per weapon, **whether
// the current gametype is in that row's `'|'`-separated list** -- and **sub_432000 does it
// with `mov ecx, [edx+0Ch]` on the `g_gametype` dvar, unguarded**. **In a dedicated process
// that dvar has never been registered**, because **the only thing that registers it is
// CG_Init**, so **edx was 0 and the read of `0xC` was the whole fault.**
//
// **Nothing here is a workaround**: it **calls the game's own registration blocks**, and it
// does so **ONCE, gated on the dvar the fault named**.
```

★★★ **⇒ 五个精确值：**
```
`sub_432130` 加载 **`mp/gametypeWeaponCustomTable.csv`**
`sub_432000` 用 **`mov ecx, [edx+0Ch]`** 读 `g_gametype` dvar,**无守护**
        ↓
★★★ 专服里该 dvar **从未注册**（只有 `CG_Init` 注册）
★★★ ⇒ **`edx = 0` ⇒ 读 `0xC` 就是整个故障**
```

### ★★★★★ **与游戏自己重建的 1:1 对照**（第 11389–11412 行，逐字）

```
"**1:1 WITH THE GAME'S OWN REBUILD.** CL_ParseGamestate does this at
 **sub_453760+0x12D0**, and the lazy Com_Frame rebuild **sub_4FE120** agrees on every step
 the two share:
        ↓
     **if (weaponCount == 0) { registryMode = 2; reset(); }**
     **for (i = 1; i < 0x6A4; ++i) walk(i, 1);   // skip '*' names**
     **defaultWeapon = resolve("defaultweapon_mp", nullptr);**
     **[knife block, guarded off - see below]**
     **initialize(1);**
     **loadKnifeStatsTable();**
     **for (i = 1; i < 0x6A4; ++i) walk(i, 0);   // now the '*' ones**
        ↓
★★★ **Three things this used to get wrong, all of them measurable**:
   **the reset was UNCONDITIONAL**, **the mode word was never set**,
   and **initialize() was called with no argument at all**.
```

★★★ **⇒ 三处旧错误：① reset 无条件 ② mode word 从未设置 ③ `initialize()` 无参数调用。**

### ★★★ **`0x1588634` 的第三个数**（第 11346 行）

```cpp
registryWord(**0x1588634u**)
```
★★★ **⇒ 一个此前未记录的 RVA,在 `PerWeaponAttachmentCountsRva = 0x1588638` **之前 4 字节**。**

### ★★★★★ **`sub_59B560` 的完整前缀**（第 11437–11450 行，逐字）

```cpp
// **THE WALK IS sub_59B560, ONE INDEX AT A TIME.** Its whole prefix is **reproduced here
// rather than called**, because **on a mismatch it ends in `Com_Error("181 %s %d %d")` and
// Com_Error LONGJMPS** -- **through this `__try`, and through a `jmp_buf` this thread may
// never have set**. The decision tree is the game's:
//
//     **lea esi, [edi+1748h]**      ; base 5960 + index
//     **call CL_GetConfigString**   ; index in ESI
//     **test al, al / jz**          ; empty -> skip
//     **cmp [ebp+arg_0], 0 / jz**   ; pass 0 does NOT skip modular
//     **cmp al, '*'    / jz**       ; pass 1 skips modular names
//     **push 0 / push esi / call WeaponResolver**
//     **cmp eax, edi**              ; resolved index must BE the index
```

★★★★★ **⇒ 六条指令与 `Com_Error("181 %s %d %d")` 的 LONGJMP 风险。**
**⇒ 两个 `static_assert`（第 11455–11460 行）：**
```cpp
WeaponConfigStringBase == WeaponWalkConfigStringBase      // 0x1748
WeaponConfigStringCount == WeaponWalkEntryCount           // 0x6A4
```

### ★★★ **两遍的顺序与 `skipModular`**（第 11462–11479 行）

```cpp
for (pass = 0; pass < 2; ++pass) {
    const bool skipModular = pass == 0;      // ★ pass 0 跳过 '*' 名
    ...
    if (skipModular ? *name == '*' : *name != '*') continue;
}
```
★★★ **⇒ pass 0 = 普通武器（跳过 `'*'`）；pass 1 = 模块化武器（只要 `'*'`）。**
**⇒ 注释（第 11464–11465 行）："Pass 1 first, exactly as CL_ParseGamestate orders them: the plain weapons register before anything modular refers to one."**

### ★★★ **刀块被跳过**（第 11536–11543 行，逐字）

```cpp
// The knife block at **0x454A98** is **skipped** -- it is **guarded on an obfuscated mode
// word (`[eax+0x180C1C] == 2` read through `dword_1C1D188 ^ 0xFBB2C97A`)** and it
// **only populates a deferred-reload list**.
```
★★★ **⇒ `0x454A98` / `[eax+0x180C1C] == 2` / `dword_1C1D188 ^ 0xFBB2C97A`。**

### ★★★ **`initialize(1)` 的参数**（第 11546–11548 行）

```cpp
// `push 1; call sub_42FE80` at **0x454B41** and **0x4FE1AC**. The parameter is **not
// optional** and **was never being passed**.
static_cast<void>(weaponRegistryInitialize_(**1**));
```

### ★★★ **六个名字的样本**（第 11486–11492 行）

```cpp
if (named < 6) snprintf(firstNames[named], 96, "%u:%s", index, name);
++named;
```
★★★ **⇒ 前 6 个名字,格式 `index:name`。**
**⇒ 前 6 个不匹配,格式 `index->resolved:name`。**

---

## 十、★★★★ **其余关键细节**

### 10.1 ★★★ `readStringTable` 的四个边界（第 3578–3590 行）

```cpp
if (!readableSpan(table, sizeof(*table)) ||
    table->columnCount < minimumColumns || table->columnCount > **256** ||
    table->rowCount <= 0 || table->rowCount > **4096** || !table->values)
    return nullptr;
...
if (!tableName || !asciiCaseInsensitiveEqual(*tableName, name))
    return nullptr;
```
★★★ **⇒ 五个校验：可读 / `columnCount` 在 `[min, 256]` / `rowCount` 在 `(0, 4096]` / `values` 非空 / **名字大小写不敏感匹配**。**

### ★★★ `readItemDefinition` 的两级索引（第 10038–10085 行）

```cpp
const auto bucket = itemId / **1000**;
const auto lookupIndex = itemId % **1000** + bucketOffsets[bucket];
const auto definitionIndex = lookup[lookupIndex];
const auto *definition = definitions + definitionIndex * **ItemDefinitionSize**(40);
```
★★★ **⇒ 桶化索引：`itemId / 1000` + `itemId % 1000`。**
**⇒ `ItemDefinitionSize = **40**`（与 `CharacterItemDefinitionSize = 52` **不同**）。**

### ★★★★★ **`characterOptionSelectionMask` 的 384 位**（第 10087–10215 行）

```cpp
constexpr std::uint32_t MaskBitCount = **384**;
const auto addressable = std::min(optionCount, MaskBitCount);
...
mask[index / 32] |= 1u << (index % 32);
...
// witness: "character option mask character=N options=N selected=N bits=<...> NOT AN OPTION FOR THIS CHARACTER=<...>"
// 若一个都没匹配：追加 " -- THE LIST STARTS" + 前 16 个 option
```

★★★★★ **⇒ 三个精确值：**
```
`charDef+36` = **optionCount**
`charDef+40` = **optionList**（`u16*`）
`MaskBitCount = **384**`（12 dword）
        ↓
★★★ 不在列表的 id ⇒ **不置位**（否则会选到该索引上的任意选项）
★★★ ⇒ 这正是 **section 182** 测到的：**原始 item id 当掩码发出去 ⇒ 客户端画出与 loadout 无关的部件**
        ↓
★★★ **`sub_80E600` 按解析出的模型**名字**把每个选中项归入 12 个槽之一,并**覆盖**（升序,后写者胜）**
★★★ ⇒ **两个名字归类相同的部件会静默冲突,高索引的胜出** ⇒ **数字看不出来,名字能**
```

### ★★★★★ **`characterCatalog` 的双源交集**（第 10396–10461 行）

```cpp
// ① 读 mp/coCharItemStatsTable.csv 的 column 0 集合
// ② 扫 itemId 100..60348,名字在集合里的进 catalog
// ③ 写 character-catalog.csv
```
★★★ **⇒ 范围 **100..60348**（60,249 个 id）。**
**⇒ 注释（第 10351 行）："The range is the catalogue's own: **ids 100..60348** per `re/demo-re/marketplace/items.csv`."**

### ★★★★★ **`auditItemNames` 的 60,249 次扫描**（第 10354–10394 行）

```cpp
for (std::uint32_t itemId = **100**; itemId <= **60348**; ++itemId) { ... }
// "item name sweep: N of **60249** ids resolve to a name -> path (the extracted marketplace tables name only **905**)"
```
★★★ **⇒ 三个精确值：范围 **100..60348**（60,249）/ 提取的 marketplace 表只命名 **905**。**
**⇒ 且在 **Dedicated** 进程里**跳过**（第 10358–10365 行）："the item tables it needs belong to the client"。**

### ★★★★★ **`probeOwnership` 的七个探针**（第 10515–10528 行）

| # | itemId | 名字 | 理由 |
|---|---|---|---|
| **1** | ★ **686** | `cha_COWprestigeA` | ★ **当前穿的角色** —— 无论如何都拥有,**NO 说明探针本身错了** |
| **2** | **14368** | `melhammer_mp` | 授权位置 **10630**,远超线材的 **8460** |
| **3** | **14386** | `molotovcocktail_mp` | 授权位置 **10666** |
| **4** | **24308** | `muz_slnc45smgveprlaborday` | 授权位置 **10479** |
| **5** | **11281** | `scope_med` | ★ **从未出售** |
| **6** | **17097** | `shotgun_fn2000` | ★ **从未出售** |
| **7** | **10435** | `cam_kawaiirsrt3` | ★ **从未出售** |

★★★ **⇒ 三个授权位置：**10630 / 10666 / 10479**（线材上限 **8460**）。**
**⇒ **1,675 个**目录项从未出售（共 **21,740**）。**

### ★★★★★ **`probeOwnership` 的进程门禁教训**（第 10485–10502 行，逐字）

```cpp
// **THE PATCH IS IN THE CLIENT; THIS MUST NOT RUN IN THE DEDICATED.**
//
// **The first run of this probe reported all four items NOT owned -- including item 686,
// the character the player was wearing at that moment.** **The control caught it**: the
// patch logs under **[client/game-server]** and the probe logged under
// **[dedicated/game-server]**. **Two processes, both out.exe.** **The dedicated has no
// logged-in player and no inventory, so "not owned" is the CORRECT answer there and says
// nothing whatever about the client.**
//
// **Without the 686 control that would have read as "the patch does not work", and the next
// hours would have gone into a patch that was fine.**
```

### ★★★ `reportUnlockAllCoverage` 的 4096 上界（第 10608 行）

```cpp
if (excluded > **4096**) { "not a plausible blocklist -- treat the RVA as wrong" }
```
★★★ **⇒ 上界 **4096**；`0` 时**调用 `probeOwnership()` 而不是下结论**（第 10592–10603 行）。**

### ★★★ `resolveSessionRewards` 的三列（第 10824 行）

```cpp
if (!read(0, result.runtimeId) || !read(4, result.normalCost) || !read(40, result.persistentCost))
```
★★★ **⇒ 三列：**0 = runtimeId / 4 = normalCost / 40 = persistentCost**（`coKillstreakStatsTable.csv` 至少 41 列）。**

### ★★★ `auditWeaponItemsTable` 的三条跳过规则（第 10936–10941 行）

```cpp
if (slotName->empty() && defaultName->empty() && enabled->empty()) continue;   // 全空
if (!slotName->empty() && defaultName->empty() && enabled->empty()) continue;  // 只有槽名
if (*enabled == "n" || *enabled == "y") continue;                              // 明确 y/n
```

### ★★★★★ **`readDefaultWeaponAttachments` 的 19 个受影响武器**（第 11078–11093 行，逐字）

```
"**A BLANK `enabled` BESIDE A REAL DEFAULT IS NOT ENABLED.** This **dropped the whole class
 for 19 of the table's 838 weapons** -- **every type95 variant INCLUDING the base `type95_mp`,
 plus `ak47ornate`, `akbpcoral`, `famasnya` and `famasnyb`** -- and **a dropped class is a
 player who edits his loadout, spawns, and finds the gun he picked is simply not there.**
 **Measured by auditWeaponItemsTable; all nineteen are the same shape, `iro`/`iro_default`
 with an empty third cell (`cam` on three of them).**
        ↓
★★★ **WHICH WAY TO READ A BLANK IS A JUDGEMENT**, so it is made **in the direction that
 cannot build a wrong gun**. **Reading it as ENABLED would add a default attachment nobody
 asked for, and a wrong attachment id names a tag the model does not have and faults the
 client at spawn (section 187)**. **Reading it as NOT enabled can at worst omit one built-in
 component.**
```

### ★★★★★ **`readAttachmentModelSlot` 的四个字符**（第 11163–11197 行）

```cpp
outcome += '-';   // 表缺失
outcome += '?';   // 行读取失败
outcome += '.';   // 行缺席
outcome += 'y';   // 匹配
...
if (!result || ambiguous || outcome.find_first_of("-?") != npos) { /* 日志 */ }
```
★★★ **⇒ 四个字符：`-` 表缺失 / `?` 行读失败 / `.` 行缺席 / `y` 匹配。**
**⇒ 日志：`"attachment slot unresolved name=X tables=<15 字符> slot=N|none [AMBIGUOUS]"`。**

---

## 十一、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **动画初始化 16 步** | 9 原生调用 + 6 输出校验 + 4 回调替换 + 见证器装载 |
| 2 | ★★★★★ **四个回调最终值** | CREATE **适配器** / **APPEND `nullptr`** / FREE **适配器** / GET **适配器** |
| 3 | ★★★★★ **`animMap=0 srvMap=278`** | 两张独立映射：`VA 0x02E8D050`（服务端）/ `VA 0x02EF4858`（库存回调读） |
| 4 | ★★★ 五个精确地址 | `ServerDObjCreate VA 0x0059E740` / 映射写 `0x0059E755` / 返回 `0x0059E7B6` / 另一写 `0x0059E7EE` / 回调 `0x0455D0` 的读 `0x004455D6` |
| 5 | ★★★★★ **bail 点** | `BG_SetLerpFrameAnimation VA 0x00409BF0` 在 **`0x00409C24`** 调用、**`0x00409C2E`** 遇 null 就 BAIL |
| 6 | ★★★ ABI 兼容 | 原生调用点 **push 两参数并自清 8 字节** ⇒ 单参数 `__cdecl` 兼容 |
| 7 | ★★★★★ **六个输出校验** | `animationCount` / `finalAnimationCount` / `animTree` / `*animScriptDataPointer_` / `restore` |
| 8 | ★★★ 六个的注释 | "**SIX CONDITIONS, ONE STATUS**… **three of the values it reads were 3.3.3.3 offsets**" |
| 9 | ★★★ `restoreFailedContext` 三步 | `EndLoadAnimTrees` / 恢复 `scriptData` / 恢复 `animConditionBase`；五个 `logStage` |
| 10 | ★★★ 双门禁 | 地图 `zm_factory_sh` **且** `OLMOD_FACTORY_DEATH_FX=1`；`AnimTreeMask = 8`（family 3 = `generic_human`） |
| 11 | ★★★ `actorAnims` 偏移 | `context + **708228** + 3*20` = `0xACE44 + 60` |
| 12 | ★★★★★ **两个 RawFile** | `mp/playeranim_defines.script` / `mp/playeranim.script`；资产类型 **36**；必须**存在且非默认** |
| 13 | ★★★★★ **`0x144 → 0x158`** | `sub_407E10` 的 `mov ecx,[edi+158h]` + `imul ecx,450h` + `lea [ecx+edx+0AF350h]` |
| 14 | ★★★★★ 静默仪器的教训 | **"a silent instrument, which reads exactly like a healthy one"** |
| 15 | ★★★★★ **MOVETYPE `+0x1A004` vs scriptEvents `+0x25F80`** | 13 次全失败都打印健康的 `populated=43/47` |
| 16 | ★★★ 健康值 | **DEATH 24 个 set / RAISEWEAPON 13 个 set** |
| 17 | ★★★★★ **两个动画全局** | `dword_827F734`（脚本表 `0x00407E14`）/ `dword_827F730`（characterInfo `0x00407E37`）；**只装第二个** |
| 18 | ★★★★★ **booking 五偏移** | **67056 / 67060 / 67064 / 67068 / 67100** |
| 19 | ★★★ 3.3.3.3 的引用次数 | `0xF730` **38** / `0xF738` **14** / `0xF73C` **26**；**本 build 零** |
| 20 | ★★★★★ **服务僵尸的日志** | `selection-kind` / `SessionStart queued map=zm_factory_sh gametype=zm` / `ACCEPTED` / `XUID is not in the session roster` / `mp_rust_long dm members=2`（too late） |
| 21 | ★★★ 两个位移 | `0xF7xx` 块 **+0xEC0** / active 标志 **+0x18** |
| 22 | ★★★★★ **实测五值（pid 2776）** | `playlist` / `sd` / `mp_crash_tropical` / **`0x1A`=26** / `0` |
| 23 | ★★★ 老外对照 | `20260812_sd_objectives_v7` 的 **26/0/mp_crash_tropical/sd** |
| 24 | ★★★★★ **`combat` 合法** | 人机房间 **19:21:05**：`combat` + `sd` / `mp_mountain` / **33** / **4** |
| 25 | ★★★ 五个 `refuse` 串 | `module` / `room-slot-unreadable` / `room-too-small` / `selection-kind` / `map-or-gametype-name`（上限 **4**） |
| 26 | ★★★★★ **13 个回退布局值** | `610`/`14`/`12`/`9`/`1607`/`37`/`60`/`5`/`22`/`29`/**`16`**/**`23`**/`6` |
| 27 | ★★★★★ **两个 numerology 值** | `primaryAttach = 22-6 = **16**` / `secondaryAttach = 29-6 = **23**` |
| 28 | ★★★ 七个按名路径 | `characterClasses` / `.slots` / `weaponClasses` / `.primaryBase` / `.secondaryBase` / `.primaryAttach` / `.secondaryAttach` |
| 29 | ★★★ 五个额外属性 | `perks` / `killstreaks` / `lethal` / `lethalDoubleAmmo` / `tactical` / `tacticalDoubleAmmo` |
| 30 | ★★★ 三个边界校验 | 序号 ≥ `weapons->index` / `slotCount = min(def, 9)` / `classesPerCharacter` 整除 |
| 31 | ★★★ `weaponClasses` 是**扁平 60 项** | 12 角色 × 5 类；def 不说分界 ⇒ **整除是唯一诚实办法** |
| 32 | ★★★★★ **附件序号顺序** | **`16..21` + `22`（主）/ `23..28` + `29`（副）** |
| 33 | ★★★★★ **实测两类** | 类 0：`10609/10028`,`16=for_gripvtlong2ak104ss`,`22=ak104ss_mp`,`23=red_rmrtmp`,`29=tmp_mp`；类 2：`10015/10042`,`16=red_rmrl86`,`22=l86_mp`,`29=stinger_mp` |
| 34 | ★★★★★ 错读的后果 | 只有 23 出现 / 其余"not supported" / **翻译 id 建的变体客户端不共享 ⇒ 拒绝每一发子弹** |
| 35 | ★★★★★ **第一次错读** | 附件在武器**之后**（`30..35`）⇒ 实际是 **`emp_grenade_mp` / `smoke_grenade_mp` / `fragshort_grenade_mp`**（**装备槽**） |
| 36 | ★★★ 双弹药位 | **BIT 偏移**（`bit >> 3` 字节,`1u << (bit & 7)`） |
| 37 | ★★★★★ **loadout 记录 160 字节** | **80 word**；槽步长 **168**,记录 `+8`；owner 键 `+248`；主 `word 24` / 副 `word 31` |
| 38 | ★★★★★ **四个武器组 = 两个类** | `sub_7C5A50` 写 4 × 7 word；`WeaponsPerClass = 2`；**每个被接受的 SessionStart 都记录 `classMask=3`** |
| 39 | ★★★★★ **全有或全无** | `valid()` 强制 `present != (weapon.itemId != 0)` |
| 40 | ★★★★★ **三个已死假设** | "`classMask=1` 被拒绝" / "四组 = 两类" / "镜像到所有槽修 `missing_playerstate`"；**`classMask=31` 被接受而 spawn 仍无 playerstate** |
| 41 | ★★★ REJECTED dump | 前 **32** 个 word |
| 42 | ★★★★★ **25（实为 27）条拒绝** | `0x7FF` / `0x7FE` / `0x1FF` / `MaximumWeaponFireType=10` / `int16_max` / `20.0f` |
| 43 | ★★★★★ **`absentClip = clipIndex == -1`** | `raygun_mp`：`index=1235 ammo=1203 clip=-1 clipSize=1 maxAmmo=1 type=0 class=1` |
| 44 | ★★★★★ **`meleeDamage` 的类门** | `index=1188 ammo=1188 clip=1188 type=1 class=6 melee=0`（**THROWABLE**） |
| 45 | ★★★ `maxAmmo` 公式 | `+3865` 非零 ⇒ `multiplier × clipSize`；上界 **`0x7FF`** |
| 46 | ★★★★★ **alt 的三个误读字段** | `+3880`/`+3884`/`+3888` 实为**榴弹发射器的投射物类型**；**57 个定义**全是 `uni_gl_<host>_mp` |
| 47 | ★★★★★ **真正的 alt** | **`+3716`（名）→ `+3720`（索引）**；**46 个 host/alt 对**；`+12` 是宿主名（存在 alt 上） |
| 48 | ★★★ 模块化分支 | `'*'` 前缀 ⇒ **`sub_431490` 自建模块化 alt** |
| 49 | ★★★ 三个名字字段 | `+12`（host）/ `+3716`（parent）/ `+3736`（link）；打印上限 **200** |
| 50 | ★★★★★ **`volatile` 承重** | MSVC 对 `__try` 内修改的非 volatile 局部在展开后给**不确定值**；**11 个 volatile 标量** |
| 51 | ★★★★★ **`stage` vs `faultStage`** | 前者**进度**（会被覆盖）/ 后者**故障点**（写一次）；"`stage=5` 三次而真故障在 `stage=22`" |
| 52 | ★★★ 五个阶段编码 | **1** reset / **2** walk / **3** default / **4** initialize / **5** verify；故障 **`20+pass`** / **`51`** / **`90+stage`** |
| 53 | ★★★★★ **`g_gametype` 空 dvar** | `sub_432130` 加载 `mp/gametypeWeaponCustomTable.csv`；`sub_432000` 用 `mov ecx,[edx+0Ch]` **无守护** ⇒ **`edx=0` ⇒ 读 `0xC` 就是故障** |
| 54 | ★★★★★ **1:1 重建七步** | `count==0 ⇒ mode=2 + reset` / `walk(i,1)` / `resolve("defaultweapon_mp")` / `[knife 跳过]` / `initialize(1)` / `loadKnifeStatsTable` / `walk(i,0)` |
| 55 | ★★★ 三处旧错误 | reset **无条件** / mode word **从未设置** / `initialize()` **无参数** |
| 56 | ★★★ 新 RVA | **`0x1588634`**（在 `PerWeaponAttachmentCountsRva = 0x1588638` 之前 4 字节） |
| 57 | ★★★★★ **`sub_59B560` 六指令** | `lea esi,[edi+1748h]` / `call CL_GetConfigString` / `test al,al; jz` / `cmp [ebp+arg_0],0; jz` / `cmp al,'*'; jz` / `cmp eax,edi` |
| 58 | ★★★ LONGJMP 风险 | 不匹配 ⇒ `Com_Error("181 %s %d %d")` ⇒ **穿过 `__try` 和可能从未设过的 `jmp_buf`** |
| 59 | ★★★ 两个 `static_assert` | `0x1748` / `0x6A4` |
| 60 | ★★★ 两遍顺序 | **pass 0 = 普通（跳过 `'*'`）/ pass 1 = 模块化（只要 `'*'`）** |
| 61 | ★★★ 刀块 | **`0x454A98`**,门 `[eax+0x180C1C] == 2`（`dword_1C1D188 ^ 0xFBB2C97A`）⇒ **只填延迟重载列表** |
| 62 | ★★★ `initialize(1)` | `push 1; call sub_42FE80` @ **`0x454B41`** / **`0x4FE1AC`** |
| 63 | ★★★ 六个名字样本 | `index:name`（前 6）/ `index->resolved:name`（前 6 个不匹配） |
| 64 | ★★★ `readStringTable` 五校验 | 可读 / `columnCount ∈ [min,256]` / `rowCount ∈ (0,4096]` / `values` 非空 / **大小写不敏感名字匹配** |
| 65 | ★★★ `readItemDefinition` 桶化 | `itemId/1000` + `itemId%1000`；`ItemDefinitionSize = **40**` |
| 66 | ★★★★★ **`MaskBitCount = 384`** | `charDef+36` count / `charDef+40` list；不在列表 ⇒ **不置位** |
| 67 | ★★★★ `sub_80E600` 的归类 | 按**模型名**归入 12 槽,**覆盖**（升序,后写者胜）⇒ **数字看不出冲突,名字能** |
| 68 | ★★★ `characterCatalog` 范围 | **100..60348**（60,249） |
| 69 | ★★★ `auditItemNames` | 60,249 次扫描；提取表只命名 **905**；**Dedicated 跳过** |
| 70 | ★★★★★ **七个探针** | 686（**当前角色,控制组**）/ 14368 / 14386 / 24308（授权位置 **10630/10666/10479**）/ 11281 / 17097 / 10435（**从未出售**） |
| 71 | ★★★ 三个数 | 线材上限 **8460** / 从未出售 **1,675** / 目录 **21,740** |
| 72 | ★★★★★ **进程门禁教训** | 首轮四件全 NOT owned（含 686）；`[client/...]` vs `[dedicated/...]`；**没有 686 控制组会误判"补丁不工作"** |
| 73 | ★★★ `reportUnlockAllCoverage` | `excluded > **4096**` ⇒ RVA 错；`0` ⇒ **调 `probeOwnership()` 而非下结论** |
| 74 | ★★★ `resolveSessionRewards` 三列 | **0** runtimeId / **4** normalCost / **40** persistentCost |
| 75 | ★★★ 三条跳过规则 | 全空 / 只有槽名 / `enabled` 是 `y` 或 `n` |
| 76 | ★★★★★ **19 个受影响武器** | 全部 type95 变体（含 `type95_mp`）+ `ak47ornate` / `akbpcoral` / `famasnya` / `famasnyb`；形状 `iro`/`iro_default` 空第三格（`cam` 三个） |
| 77 | ★★★★★ 空格的判断方向 | **"读成 ENABLED 会加一个没人要的附件,而错的附件 id 会在 spawn 时让客户端崩"** |
| 78 | ★★★★★ **四个字符** | `-` 表缺失 / `?` 行读失败 / `.` 行缺席 / `y` 匹配 |

---

## 十二、结论

### 1. ★★★★★ **动画初始化是 16 步,其中 9 个原生调用 + 6 个输出校验 + 4 个回调替换**

### 2. ★★★★★ **`ServerGetDObjCallbackOffset` 必须换成服务端适配器**（`animMap=0 srvMap=278`）

★ **⇒ 库存回调读的是**另一张映射**,而本项目只在服务端映射里注册。**

### 3. ★★★★★ **`0x144 → 0x158` 的静默仪器**是"仪器看起来健康"的教科书案例

### 4. ★★★★★ **MOVETYPE 表与 `scriptEvents` 表是两张表**,只读一张会让 13 次全失败的运行看起来健康

### 5. ★★★★★ **booking 的五个偏移经历了**四次反复**（3.3.3.3 → 移植 → 回退 → 再移植）

★ **⇒ 每次反复都有精确日志与实测值。**

### 6. ★★★★★ **`combat` 也是合法 selectionKind**（人机房间）

### 7. ★★★★★ **附件序号是 `16..21`+`22` / `23..28`+`29`**（两次错读,第一次读到了装备槽）

### 8. ★★★★★ **`loadout record` 的四个武器组是两个类**,而 `missing_playerstate` 的三个假设全死

### 9. ★★★★★ **`WeaponDef` 的 27 条拒绝 + 逐字段日志**使 `raygun_mp` 成为一行修复

### 10. ★★★★★ **`meleeDamage` 的类门缺失曾让手雷/榴弹不可用**

### 11. ★★★★★ **alt 武器是 `+3716 → +3720`**,而 `+3880..+3900` 是**榴弹发射器的投射物类型**

### 12. ★★★★★ **`volatile` 是 `__try` 内的承重语法**,而 `stage` 与 `faultStage` 必须分开

### 13. ★★★★★ **`g_gametype` 的空 dvar 是专服武器注册的根因**（`mov ecx,[edx+0Ch]` 无守护）

### 14. ★★★★★ **`probeOwnership` 的 686 控制组**避免了一次"补丁不工作"的误判

---

## 十三、下一步

`EngineBindings.cpp` 剩余 **11,601–17,867 行**（约 **6,300 行**）：
- `ensureWeaponRegistryInitialized` 的后半
- 角色呈现解析（`resolveClientCharacterPresentation` / `resolveSessionCharacterPresentation`）
- Alpha Barrett 移植与三个审计
- 武器解析（`resolveWeaponItem` / 附件翻译）
- 声音别名注册表
- 痕迹/碰撞的完整实现
- 约 50 个访问器

然后 `Appmain.cpp`（10,564 行）与 `server_mp` 154 文件。
