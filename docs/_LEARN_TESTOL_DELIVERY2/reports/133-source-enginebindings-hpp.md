# 学习报告 133（重开）— `EngineBindings.hpp`（2,205 行）：整个适配层的常量总账

**学习范围**：`EngineBindings.hpp`（133,088 B / **2,205 行**）——全文逐行读完
**性质**：全实测
**★★★★★ 本报告收录十二个重大发现**：①**`ExpectedTimestamp` / `ExpectedImageSize` 的双重身份校验** ②**动画存储的四个 `static_assert` 与 `0x100000` 的推导** ③**`ServerCharacterInfoBaseOffset = 0xAF350`（不是 `0x96E20`）的完整论证** ④**`0x12000` = 1024 × 72** ⑤**`EntityOriginKeyRvas` 三个不连续地址** ⑥**`CharacterItemDecodeKeyRva` 的纠正** ⑦**`LoadoutRecordCache` 的 38 × 168 布局** ⑧**`CharacterProfileSlotCount = 9`（不是 12）** ⑨**`BaseWeaponAssetCount = 0x514` 的 `static_assert`** ⑩**`DB_FindXAssetHeader` 的三参数形式** ⑪**`CharacterOptionSelectionMask` 的 384 位** ⑫**约 200 个 RVA 的完整清单**

---

## 一、★★★★★ **两个身份常量**

### 1.1 ★★★★★ 完整注释（第 461–473 行，逐字）

```cpp
// OLMOD(engine-binding-catalog): fixed identity and DB/qcommon/CCS
// entry points for the **0x57611E31, 0x0C72A000 CODOL executable only**.
// **Prefix guards in bind() reject another build but do not by themselves
// prove complete ABI or pointed-to global layout semantics.**
static constexpr std::uint32_t ExpectedTimestamp = **0x6096930A**;
// LOCAL OVERRIDE (olmod-local, **2026-10-03**): the distributed client here is
// **codoMP_client_shipRetail.exe SHA256
// 36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537**,
// whose PE header reports **SizeOfImage 0x0E659000 instead of 0x0E5D6000**.
// Every ExpectedRVA below was re-read from that image's **RUNTIME memory** and
// every sampled prefix matched **byte-for-byte** (SV_LinkEntity/SV_UnlinkEntity/
// SV_Trace/BG_GetPlayerEyePosition, **2026-10-03**), so **the only mismatch is this
// header field**. Revert to **0x0E5D6000** for the upstream out.exe build.
static constexpr std::size_t ExpectedImageSize = **0x0E659000**;
```

★★★★★ **⇒ 六个精确值：**
```
`ExpectedTimestamp = **0x6096930A**`（时间戳）
`ExpectedImageSize = **0x0E659000**`（分发版）/ **`0x0E5D6000`**（上游 out.exe）
        ↓
★★★ SHA256 = **`36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`**
★★★ **两个值 `0x57611E31` / `0x0C72A000`**（未在注释里说明含义 ⇒ 可能是 `TimeDateStamp` 与 `SizeOfImage` 的旧值）
        ↓
★★★ 四个 RVA 的**运行时内存**已逐字节验证：
   **`SV_LinkEntity` / `SV_UnlinkEntity` / `SV_Trace` / `BG_GetPlayerEyePosition`**
```

### ★★★★★ **"只差这一个头部字段"**

```
分发版 vs 上游：**只有 `SizeOfImage` 不同**（`0x0E659000` vs `0x0E5D6000`）
        ↓
★★★ 差值 = **`0x83000`** = **536,576 字节**（约 **524 KB**）
★★★ ⇒ 分发版**多出 524 KB**（可能是加壳/水印）
        ↓
★★★ ⇒ **所有 RVA 已从分发版重新读取并逐字节验证**
```

---

## 二、★★★★★ **动画存储的四个 `static_assert`**

### 2.1 ★★★★★ 完整注释（第 663–684 行，逐字）

```cpp
// CODDIFF(1649370): **THIS BUFFER WAS SMALLER THAN WHAT THE GAME WRITES INTO IT.**
// It was **0xA6000**, and BG_FindAnimTrees opens with
//     **40b21e  push 0ACE70h; Size**
//     **40b225  push eax**          ; eax = dword_827F730, i.e. this array
//     **40b226  call _memset**
// which is **0xACE70 = 708,208 bytes** -- **28,272 past the end**. The live log
// shows **serverLoadAnimStorage_ starting at exactly base + 0xA6000**, so
// **the overrun lands in the next member rather than in unmapped memory**,
// which is why **it corrupted rather than crashed**.
//
// The reads go further still, and all of them are off this same base:
//     **+0xAF31C**  sub_407530's script-mode byte
//     **+0xAF314**  sub_74AF50's anim user     **+0xAF338** its allocator
//     **+0xAF350**  sub_407E10's per-entry array, **stride 0x450**
//     **+0xAF318**  CL_ParseGamestate writes here at **0x454CD4**
// **0xAF350 + 18 * 0x450 = 0xB4200** for this project's client count, and
// the game's own block is **`ebx + 0xD1900`** inside a larger allocation
// whose extent is **not visible**. So this is **rounded UP well past every
// measured offset** rather than fitted to them: **over-allocating costs
// address space, under-allocating hands the engine someone else's memory
// and the failure looks like anything at all.**
static constexpr std::size_t ServerAnimConditionStorageSize = **0x100000**;
static_assert(ServerAnimConditionStorageSize >= **0xACE70**,
    "BG_FindAnimTrees memsets 0xACE70 bytes at this base");
static_assert(ServerAnimConditionStorageSize >= **0xAF350 + 18 * 0x450**,
    "sub_407E10 indexes +0xAF350 with a 0x450 stride, per client");
```

★★★★★ **⇒ 八个精确值：**
```
旧大小：**`0xA6000`**（= 679,936）
`BG_FindAnimTrees` 的 `memset`：**`0xACE70`**（= **708,208**）
        ↓
★★★ 差 = **`0xACE70 - 0xA6000` = `0x2E70` = **11,888 字节**
★★★ 注释说 **28,272 字节** ⇒ **按十六进制重算：`0xACE70 - 0xA6000 = 0x2E70` = 11,888**
★★★ ⇒ **注释里的 28,272 与 11,888 不符** ⇒ **记录为待核对项**
        ↓
★★★ `serverLoadAnimStorage_` 恰在 **`base + 0xA6000`** ⇒ **越界落在下一个成员上** ⇒ **损坏而非崩溃**
```

### ★★★★★ **五个读偏移**

| 偏移 | 用途 | 出处 |
|---|---|---|
| **`+0xAF31C`** | **`sub_407530` 的 script-mode 字节** | — |
| **`+0xAF314`** | **`sub_74AF50` 的 anim user** | — |
| **`+0xAF338`** | **其 allocator** | — |
| **`+0xAF350`** | ★ **`sub_407E10` 的 per-entry 数组,stride `0x450`** | — |
| **`+0xAF318`** | **`CL_ParseGamestate` 在 `0x454CD4` 写** | — |

★★★ **⇒ 最大的读 = `0xAF350 + 18 × 0x450` = **`0xB4200`**（737,792）。**
**⇒ 游戏自己的块 = `ebx + 0xD1900`（858,368）,在**更大的分配里**,范围**不可见**。**

### ★★★★★ **"向上取整远超所有测到的偏移"**

```
`ServerAnimConditionStorageSize = **0x100000**` = **1,048,576**（1 MB）
        ↓
★★★ 最大测到偏移 **`0xB4200`** = 737,792 ⇒ **留 **310,784 字节**余量
        ↓
★★★★★ ⇒ **理由（逐字）："over-allocating costs address space,
   under-allocating hands the engine someone else's memory
   and the failure looks like anything at all."**
```

### ★★★★★ **三个事件表位置的 `static_assert`**（第 691–714 行）

```cpp
// **WHERE scriptEvents SITS RELATIVE TO THE TWO REGIONS ABOVE**, because
// that is what makes the init order legal. **BG_AnimParseAnimScript
// sub_407530 clears the movetype table at +0x1A004 and one scrap script
// at +0x25D7C and DOES NOT clear scriptEvents**, so **parses accumulate
// into it**; the only thing that ever zeroes it is **BG_FindAnimTrees
// sub_40B210's `memset(dword_827F730, 0, 0xACE70)` at 0x0040B226**.
// **initializeServerAnimation runs parse -> BG_FindAnimTrees ->
// BG_FinalizePlayerAnims, which is CL_ParseGamestate's own order
// (0x00454CDF, 0x00454D38, 0x00454D42)** and **leaves finalize's re-parse
// as the one that populates the event table**.
static_assert(
    SvNativeAnimScriptEventTableOffset + SvNativeAnimScriptEventCount * SvNativeAnimScriptStride <= **0xACE70**,
    "BG_FindAnimTrees' 0xACE70 memset must cover the whole event table, "
    "or finalize's re-parse would append to a stale one");
static_assert(
    ... <= **0xAF350**,
    "the event table must not overlap the per-client characterInfo array "
    "sub_407E10 derives at +0xAF350");
```

★★★★★ **⇒ 五个精确值：**
```
`sub_407530` 清 **`+0x1A004`**（movetype 表）和 **`+0x25D7C`**（一个废弃脚本）
**不清 `scriptEvents`** ⇒ **解析会累积**
        ↓
★★★ 唯一清零者 = **`sub_40B210` 的 `memset(0x827F730, 0, 0xACE70)` @ `0x0040B226`**
        ↓
★★★ 初始化顺序 = **parse → BG_FindAnimTrees → BG_FinalizePlayerAnims**
★★★ = **`CL_ParseGamestate` 自己的顺序**：**`0x00454CDF` / `0x00454D38` / `0x00454D42`**
★★★ ⇒ **finalize 的重解析才是填充事件表的那个**
        ↓
★★★ 两个 `static_assert` 保证：
   ① 事件表**完全在 `0xACE70` 的 memset 之内**（否则 finalize 会追加到**陈旧的表**）
   ② 事件表**不与 `+0xAF350` 的 characterInfo 数组重叠**
```

---

## 三、★★★★★ **`ServerCharacterInfoBaseOffset = 0xAF350` 的完整论证**

### 3.1 ★★★★★ 完整注释（第 715–753 行，逐字）

```cpp
// CODREF(bg_update_player_dobj): the locomotion anim-script state setter
// indexes the per-client characterInfo_t array from the anim-condition
// base at this fixed byte offset, with a **sizeof(characterInfo) stride**.
//
// **CODDIFF(1649370): 618016 (0x96E20) is 3.3.3.3's; this build derives
// the array at 717648 (0xAF350).** Both builds state it in the same
// instruction pair -- 3.3.3.3 at **0x004094C0**
//     **mov ecx,[eax+0x144] ; imul ecx,ecx,0x3B8 ; lea edi,[ecx+edx+0x96E20]**
// and this build with **clientNum at ps+0x158** and a **0x450 stride**.
// **Scanning every such site: 0x96E20 in 12 of 14 on 3.3.3.3, 0xAF350 in
// 11 of 16 here**, the outliers in both being **field reads INSIDE the struct
// (base + 0x2D0 / 0x308 there, base + 0x334 / 0x37C here)**. It also
// agrees with **the animation projection at 0x53DE1F**, which reaches the
// same array as **`lea edi, [ecx + eax + 0xAF350]`**.
//
// The measurement was already in this file -- **the storage comment above
// lists "+0xAF350 sub_407E10's per-entry array, stride 0x450"** and the
// static_assert below it is written against those exact numbers. **The
// constant the code actually places the array with was simply never moved
// to match**, so **the storage was sized for the right region and the array
// was put somewhere else inside it**.
```

★★★★★ **⇒ 八个精确值：**
```
3.3.3.3：`0x004094C0` 的 `mov ecx,[eax+0x144] / imul ecx,ecx,**0x3B8** / lea edi,[ecx+edx+**0x96E20**]`
1649370：`clientNum` 在 **`ps+0x158`**,stride **`0x450`**,基址 **`0xAF350`**
        ↓
★★★ 扫描统计：
   **`0x96E20` 在 3.3.3.3 的 14 个中占 12 个**
   **`0xAF350` 在本 build 的 16 个中占 11 个**
★★★ 两者的离群值都是**结构体内部的字段读**：
   3.3.3.3 = **`base + 0x2D0` / `base + 0x308`**
   1649370 = **`base + 0x334` / `base + 0x37C`**
        ↓
★★★ 独立佐证：**动画投影 `0x53DE1F`** 用 **`lea edi, [ecx + eax + 0xAF350]`** 到达同一数组
        ↓
★★★★★ ⇒ **"存储是按正确区域定尺寸的,而数组被放在了它里面的**别处**"**
```

### ★★★ 三个常量（第 753–761 行）

```cpp
static constexpr std::size_t ServerCharacterInfoBaseOffset = **0xAF350**;
static constexpr std::size_t ServerCharacterInfoSlotCount = **18**;
static_assert(
    ServerCharacterInfoBaseOffset + ServerCharacterInfoSlotCount * SvNativeCharacterInfoSize
        <= ServerAnimConditionStorageSize,
    "the derived characterInfo array must fit inside the installed "
    "anim-condition storage: sub_AA94C0 reads it there whether or not "
    "this project put anything at that offset");
```

★★★ **⇒ `0xAF350 + 18 × 0x450 = **`0xB4200`** ≤ **`0x100000`** ✓**
**⇒ 且注释（第 1672–1680 行）："`sub_AA94C0`（VA **`0x004094C0`**）… derives one as
**`dword_7EB7B80 + 618016 + 952 * playerState[+0x144]`**"**
**⇒ `952 = 0x3B8`,`618016 = 0x96E20` ⇒ **这是 3.3.3.3 的公式**（本 build 用 `0xAF350` + `0x450`）。**

### ★★★★★ **`0x12000` = 1024 × 72**（第 762–779 行，逐字）

```cpp
// **CONFIRMED against out.exe, and it is 1024 x 72 exactly.**
//
// This buffer is the **`loadAnims` array BG_AnimParseAnimScript takes in ECX**,
// and CL_ParseGamestate's own call states **both of its dimensions**:
//     **454c6d  mov [ebp+var_100], 400h**     ; the animation **CAPACITY**
//     **454cca  mov esi, dword_827F730**      ; the anim-condition base
//     **454cd6  push 0**
//     **454cd8  push ecx**                    ; &var_100
//     **454cd9  mov ecx, [ebp+var_10C]**      ; the loadAnims array
//     **454cdf  call sub_407530**
// sub_407530 stores that array in **dword_1971E04** and saves the capacity
// in **dword_196DB0C** before zeroing the caller's count, and **sub_404FE0
// walks the array with `v5 += 72`**. So **0x400 slots of 72 bytes is
// 0x12000**, and **MaximumPlayerAnimations is the same 1024 the engine passes**.
// **This value is IDENTICAL to 3.3.3.3's and is nonetheless right** -- which
// is the whole reason **a match is a suspicion and only a check is a result**.
static constexpr std::size_t ServerLoadAnimStorageSize = **0x12000**;
```

★★★★★ **⇒ 七个精确值：**
```
`0x400` = **1024** 个槽
`sub_404FE0` 用 **`v5 += 72`** 遍历
        ↓
★★★ **1024 × 72 = 73,728 = `0x12000`** ✓
        ↓
★★★ 六个精确地址：
   `0x454C6D`（`mov [ebp+var_100], 400h`）
   `0x454CCA`（`mov esi, dword_827F730`）
   `0x454CD6`（`push 0`）
   `0x454CD8`（`push ecx`）
   `0x454CD9`（`mov ecx, [ebp+var_10C]`）
   `0x454CDF`（`call sub_407530`）
        ↓
★★★ `sub_407530` 把数组存在 **`dword_1971E04`**,容量存 **`dword_196DB0C`**
        ↓
★★★★★ ⇒ **"这个值与 3.3.3.3 的**完全相同**,却**仍然是正确的** ——
   这正是为什么**"匹配只是怀疑,只有检查才是结论"**"**
```

---

## 四、★★★★★ **`EntityOriginKeyRvas` 三个不连续地址**

### 4.1 ★★★★★ 完整注释（第 1138–1153 行，逐字）

```cpp
// **CODDIFF(1649370): THESE WERE 3.3.3.3's, AND THEY ARE NOT EVEN CONSECUTIVE HERE.**
// Read straight out of this build's **BG_PlayerToEntity_SetTrajectory at 0x0041167A**:
//     **mov ecx, ds:0x00E51A84 / not ecx / xor ecx, [ebp-10h]**   ; origin[0]
//     **lea eax, [esi+18h]     / xor ecx, eax / mov [eax], ecx**  ; ^ **ITS OWN ADDRESS**
//     **mov edx, ds:0x00E51B1C / not edx / xor edx, [ebp-0Ch]**   ; origin[1]
//     **mov ecx, ds:0x00E51B20 / not ecx / xor ecx, [ebp-08h]**   ; origin[2]
// which also confirms **OriginOffsets {0x18,0x1C,0x20}** and the decode this
// project already uses, **`encoded ^ fieldAddress ^ ~key`**. **Only the key
// ADDRESSES were wrong.**
//
// **The first key sits 0x98 bytes away from the other two**, so **the old triple
// being three consecutive dwords was never a layout this build has**. **Any port
// that assumed "three in a row" -- including reading one and adding 4 -- lands on
// the wrong global twice out of three times.**
static constexpr std::array<std::size_t, 3> EntityOriginKeyRvas{
    **0xA51A84**, **0xA51B1C**, **0xA51B20**,
};
```

★★★★★ **⇒ 六个精确值：**
```
三个键：**`0xA51A84`** / **`0xA51B1C`** / **`0xA51B20`**
        ↓
★★★ `0xA51B1C - 0xA51A84` = **`0x98`**（152 字节）
★★★ `0xA51B20 - 0xA51B1C` = **`0x04`**
        ↓
★★★ ⇒ **第一个键离另两个 0x98 字节** ⇒ **"三个连续 dword"从来不是本 build 的布局**
★★★ ⇒ **任何"读一个再加 4"的移植 ⇒ 三次中有两次落到错的全局**
        ↓
★★★ 解码公式：**`encoded ^ fieldAddress ^ ~key`**（注意 **`~key`**）
★★★ `OriginOffsets = **{0x18, 0x1C, 0x20}**`
★★★ 三个值的来源：`[ebp-10h]` / `[ebp-0Ch]` / `[ebp-08h]`
```

---

## 五、★★★★★ **`CharacterItemDecodeKeyRva` 的纠正**

### 5.1 ★★★★★ 完整注释（第 1156–1170 行，逐字）

```cpp
// CODDIFF(character_item_decode_key): **was 0xA57A70**, which is **a real runtime key
// on this build but NOT the one that decodes a character item record**. It was
// **the only address in this block with no derivation beside it** -- section 51k,
// in its mildest form: **an undocumented constant sitting between two documented ones**.
//
// The record's own copier settles it. **sub_619E90 finishes at 0x619f20 with
//     ROL32(dword_E4DD90 ^ *(dword *)entry ^ *(dword *)(entry + 8), 8)**
// and its **only caller repeats the same three-way XOR against dword_E4DD90 at
// four further sites (0x618c8e, 0x618cb2, 0x618e5a, 0x619161)**.
// **dword_E4DD90 is VA 0xE4DD90, so RVA 0xA4DD90.**
//
// **NEITHER ADDRESS CAN BE TOLD FROM THE OTHER BY ITS IMAGE VALUE**: both read
// **0xFFFFFFFF**, because both are **runtime-initialised**. **Only the call site
// discriminates**, which is why **the rule is to confirm against one**.
static constexpr std::size_t CharacterItemDecodeKeyRva = **0xA4DD90**;
```

★★★★★ **⇒ 七个精确值：**
```
错误：**`0xA57A70`**（真实存在的运行时键,但**不是**解码角色物品记录的那个）
正确：**`0xA4DD90`**（`dword_E4DD90`,VA **`0xE4DD90`**）
        ↓
★★★ 解码公式：**`ROL32(dword_E4DD90 ^ *(dword*)entry ^ *(dword*)(entry+8), 8)`**
★★★ 五个调用点：**`0x619F20`**（`sub_619E90` 尾部）+ **`0x618C8E`** / **`0x618CB2`** / **`0x618E5A`** / **`0x619161`**
        ↓
★★★★★ ⇒ **"两个地址无法从镜像值上分辨：两者都读 `0xFFFFFFFF`,因为都是运行时初始化"**
★★★ ⇒ **"只有调用点能判别,所以规则是：对着一个调用点确认"**
```

---

## 六、★★★★★ **`LoadoutRecordCache` 的 38 × 168 布局**

### 6.1 ★★★★★ 完整注释（第 973–1001 行，逐字）

```cpp
// **THE BUILT RECORD IS CACHED, AND READING IT BEATS REBUILDING IT.**
//
// **sub_7C5500 is a 38-slot cache keyed by two dwords**; **sub_7C6480 fetches a slot,
// memcpy's 160 bytes out of `slot + 8`, and only then calls sub_7C5BA0 to rebuild
// into that same place**. So **`slot + 8` holds the last record the CLIENT built for
// itself, and it persists**.
//
//     **slot stride  42 dwords = 168 bytes**
//     **slot + 4     flag byte**        **slot + 8/+12  the two keys**
//     **slot + 8     the 160-byte record starts here** (its first two dwords ARE the
//                  keys -- sub_7C6480 writes them through the same pointer it
//                  hands to sub_7C5BA0, which is why the character items land at
//                  word 12 and the weapons at word 24)
//
// **Reading it is a bounded memory read. REBUILDING it is a native call on the
// bridge thread**, which is the exact hazard that made `profileSlotProbeEnabled()`
// default to off. **Prefer the read; keep the call only as a fallback.**
// **WHICH SLOT IS THE PLAYER'S, without calling anything.** sub_7C6480 picks the
// cache keys by a plain pointer chase, and **the record's first two dwords ARE
// those keys**, so **the owner's slot is identifiable from memory alone**:
//
//     **mov ecx, dword_84ABB08**      ; else **dword_84ABB14** when that is null
//     **call sub_B9A0F0**             ; returns **ecx + 216**
//     **mov esi, [eax+20h]**          ; key 1  -> **owner + 248**
//     **mov edi, [eax+24h]**          ; key 2  -> **owner + 252**
```

★★★★★ **⇒ 八个精确值：**
```
缓存：**`sub_7C5500`**,**38 个槽**,按**两个 dword** 键
        ↓
★★★ 槽步长 = **42 dword = 168 字节**
★★★ `slot + 4` = **标志字节**
★★★ `slot + 8/+12` = **两个键**
★★★ `slot + 8` = **160 字节记录起点**（**前两个 dword 就是键**）
        ↓
★★★ 记录内布局：**角色物品 @ word 12**,**武器 @ word 24**
        ↓
★★★ 定位玩家的槽（**纯内存读**）：
   `mov ecx, dword_84ABB08`（**`0x40ABB08`**）
   ⇒ 若为 null 用 **`dword_84ABB14`**（**`0x40ABB14`**）
   `call sub_B9A0F0` ⇒ 返回 **`ecx + 216`**
   `mov esi, [eax+20h]` ⇒ key 1 ⇒ **`owner + 248`**
   `mov edi, [eax+24h]` ⇒ key 2 ⇒ **`owner + 252`**
```

### ★★★★★ **"没有这个,读到的就是硬币"**

```
不定位 owner ⇒ **读第一个已填充的槽**
        ↓
★★★ 在大厅里还有其他成员时 ⇒ **在他们和玩家的 class 之间抛硬币**
★★★ ⇒ **"一个错但合理的 class 是最难注意到的错误"**
```

### ★★★ 五个缓存常量（第 1005–1014 行）

```cpp
static constexpr std::size_t LoadoutRecordCacheRva = **0xDF72D60**;
static constexpr std::size_t LoadoutRecordCacheSlots = **38**;
static constexpr std::size_t LoadoutRecordCacheStride = **168**;
static constexpr std::size_t LoadoutRecordCacheOffset = **8**;
static constexpr std::size_t LoadoutRecordCharacterWord = **12**;
static constexpr std::size_t LoadoutRecordWeaponWord = **24**;
static constexpr std::size_t LoadoutRecordWeaponStride = **7**;
static constexpr std::size_t LoadoutRecordClasses = **2**;
static constexpr std::size_t LoadoutRecordWords = **80**;
```

★★★ **⇒ 完整的记录布局（160 字节 = 80 word）：**
```
word **0..1**   = 两个键（`slot + 8`/`slot + 12`）
word **12..23** = **12 个角色物品 id**
word **24..30** = **武器 0**：itemId + 6 个附件 id（**7 word = 14 字节**）
word **31..37** = 武器 1
word **38..44** = 武器 2
word **45..51** = 武器 3
        ↓
★★★ **`LoadoutRecordClasses = 2`** ⇒ **4 个武器组 / 每类 2 个武器 = 2 个类**
```

### ★★★★★ **`sub_7C5BA0` 的完整记录格式**（第 956–970 行，逐字）

```
// sub_7C5BA0 is the entry point: **sub_7C6480 calls it to fill the 160-byte
// record it then qmemcpy's**. It writes, as **u16**:
//
//     **word 12..23**   twelve character item ids
//     **word 24..30**   weapon 0: itemId then SIX attachment ids
//     **word 31..37**   weapon 1        (stride 7 words = 14 bytes)
//     **word 38..44**   weapon 2
//     **word 45..51**   weapon 3
//
// **Seven words per weapon is WeaponRequest field for field**, which is why this
// maps across with **no reinterpretation**. **The offsets are read off the WRITES
// in sub_7C5A50** (v14 = a3+48 advancing 7 words; v8 = a3+52 writing v8-1..v8[3]
// then v8-3 after the advance), **not inferred from the shape of the struct**.
```

---

## 七、★★★★★ **`CharacterProfileSlotCount = 9`（不是 12）**

### 7.1 ★★★★★ 完整注释（第 1015–1025 行，逐字）

```cpp
// **AND THE ARRAY IS NINE WIDE, NOT TWELVE.** Measured through **CodolMatchFlow.py**,
// which **reads the same function on the same build and catches the fault in JS
// instead of dying of it**:
//
//     **character_slots: [545, 0, 0, 0, 0, 0, 0, 0, 0, null, null, null]**
//
// **Slots 0..8 return; slots 9, 10 and 11 THROW.** So **characterClasses[N].slots is
// nine entries**, and **CharacterItemCount's twelve is a DIFFERENT array's size** --
// the item record sub_619E90 fills. **Looping a 12-wide index over a 9-wide array
// is a read past the end, and __try cannot save you from it here.**
static constexpr std::size_t CharacterProfileSlotCount = **9**;
```

★★★★★ **⇒ 五个精确值：**
```
实测输出：**`[545, 0, 0, 0, 0, 0, 0, 0, 0, null, null, null]`**
        ↓
★★★ **槽 0..8 返回；槽 9/10/11 抛异常**
★★★ ⇒ **`characterClasses[N].slots` 是 9 个条目**
★★★ ⇒ **`CharacterItemCount` 的 12 是**另一个数组**的大小**（`sub_619E90` 填的物品记录）
        ↓
★★★★★ ⇒ **"12 宽的索引循环 9 宽的数组 = 读越界,而 `__try` 在这里救不了你"**
```

### ★★★★★ **五个类名与九槽的对应**（第 1083–1099 行，逐字）

```cpp
// CODDIFF(section-67): **OLfinal's model resolution, and the reason the port is small.**
// **sub_619AD0 makes TWO passes over the twelve-entry item record**, and **the second
// one fills every EMPTY entry from a per-slot default table the CHARACTER itself
// carries** -- **twelve uint16 at +0xC of a 0x34-byte character record**, reached
// through the same bucket scheme with **def[+5] == 2** as the type check. So **the
// server writes ONE value, entry 0, and the engine derives the other eleven**.
//
// That is also why **every character on this account reads slots = [545,0,...]**:
// **the zeros are not a bare profile, they are the NORMAL case and they mean
// "use the character's defaults here"** (section 66a).
//
// The slots are named, and the names are a **GOLDEN for this port** because they came
// out of the client's own tables and **share no code with it**:
//     **0 cha   1 fpa   2 boo   3 fja   4 han   5 hea   6 ves   7 heg**
//     **545 cha_infbasea -> fpa_infbasea, boo_infbasea, fja_infbasea,
//                         han_infbasea00, hea_socomb**
```

★★★★★ **⇒ 六个精确值：**
```
`sub_619AD0` 对 12 条目记录做**两遍**
第二遍用**角色自带的每槽默认表**填每个空条目
        ↓
★★★ 该表在 **`character record + 0xC`**,**12 个 `uint16`**,记录大小 **`0x34`**
★★★ 类型检查用 **`def[+5] == 2`**
        ↓
★★★ ⇒ **服务端只写**一个值**（条目 0）,引擎派生其余 11 个**
★★★ ⇒ **零不是"空档案",而是**正常情况**,意思是"这里用角色的默认值"**
        ↓
★★★ **八个槽名**：`0 cha / 1 fpa / 2 boo / 3 fja / 4 han / 5 hea / 6 ves / 7 heg`
   （**第 8 个未列** ⇒ 记录为待核对）
★★★ **`545` = `cha_infbasea`** ⇒ 派生出 `fpa_infbasea` / `boo_infbasea` /
   `fja_infbasea` / `han_infbasea00` / `hea_socomb`
```

### ★★★ `characterVariantSelector` 的归属（第 1102–1114 行，逐字）

```cpp
// sub_61B6C0's **FOURTH argument**. It reaches **sub_80DEF0** and contributes one bit
// to a variant bitmask; **out.exe's own frontend caller keeps the value only when it
// is 1 or 2 and OTHERWISE SUBSTITUTES 2 (0x61D81B, `lea eax, [ecx+2]` with ecx zero)**.
//
// **SECTION 166 NAMED THE SEMANTICS AND MOVED THE OWNER.** The IN-MATCH caller is
// **CG_SetupClientCharacterInfo 0x00541800**, and it passes
// **`*(int *)(clientState + 0x154) + 1`** -- **THE FACTION FIELD THIS SERVER SENDS,
// PLUS ONE**. So **the selector is not a constant this side may choose: it is a
// function of the wire**, and **characterVariantSelector(faction) in the .cpp is the
// one place that computes it**. **This constant is deliberately GONE rather than
// left as a default nobody reads** -- **a stale default is exactly how the dedicated
// came to resolve variant 2 while the client resolved variant 1 for a whole session**.
```

★★★★★ **⇒ 五个精确值：**
```
`sub_61B6C0` 的**第四个参数** ⇒ 给 `sub_80DEF0` 贡献**变体位掩码的一位**
        ↓
★★★ 前端调用者：**只保留值 1 或 2**,否则**替换成 2**（**`0x61D81B`** 的 `lea eax,[ecx+2]`）
★★★ 比赛内调用者 = **`CG_SetupClientCharacterInfo 0x00541800`**
   ⇒ 传 **`*(int*)(clientState + 0x154) + 1`** ⇒ **服务端发的阵营字段 + 1**
        ↓
★★★★★ ⇒ **"选择器不是这一侧可以选的常量：它是**线材的函数**"**
★★★ ⇒ **常量被**故意删除**而不是留作没人读的默认值**
★★★ 原因：**"一个陈旧的默认值,正是专服解析变体 2 而客户端解析变体 1 整整一局的经过"**
```

---

## 八、★★★★★ **`DB_FindXAssetHeader` 的三参数形式**

### 8.1 ★★★★★ 完整注释（第 360–378 行，逐字）

```cpp
// **DB_FindXAssetHeader KEEPS its third parameter on 1649370.** out.exe has
// **BOTH forms** and DBFindXAssetHeaderRva names **the three-argument one**:
//     **sub_49CF30(type, name, allowDefault)**   <- **0x09CF30**, bound here
//     **sub_49D3B0(type, name)**                 <- **0x09D3B0**, a wrapper
//                                               that **hardcodes 1**
// **The weapon resolver happens to call the wrapper**, and **reading only
// that call site is how this was briefly declared with two parameters**.
// **Under __cdecl the caller cleans up, so dropping the argument does not
// crash either**: the callee reads `allowDefault` out of **whatever the
// caller's stack happened to hold**, and `if (a3)` then decides **at random
// whether a MISSING asset comes back as nullptr or as a freshly created
// default placeholder with null strings in it**.
//
// **audit-binding-abi.py --reference reads +0x8, +0xC and +0x10 on BOTH
// builds.** It could not see that until it **stopped ending its scan at the
// first call**: **sub_49CF30 reads a3 at 0x49D335, a dozen calls in**.
// **findXAsset() still asks DB_IsXAssetDefault separately**, because
// **allowDefault=false suppresses the default only on the miss path** --
// **an asset present but not yet loaded still comes back as the default**.
```

★★★★★ **⇒ 八个精确值：**
```
三参数：**`sub_49CF30(type, name, allowDefault)`** @ **`0x09CF30`** ← **绑定的这个**
两参数：**`sub_49D3B0(type, name)`** @ **`0x09D3B0`** ← **硬编码 1 的包装**
        ↓
★★★ 武器解析器恰好调用**包装** ⇒ **只看那个调用点就误判成两参数**
        ↓
★★★★★ ⇒ **`__cdecl` 下调用者清理,所以丢掉参数**不会崩**
★★★ 但 callee 从**调用者栈上恰好有的东西**读 `allowDefault`
★★★ ⇒ `if (a3)` **随机决定**缺失资产返回 `nullptr` 还是**新建的默认占位符（字符串为 null）**
        ↓
★★★ 工具：**`audit-binding-abi.py --reference`** 读 **`+0x8` / `+0xC` / `+0x10`** 在**两个 build 上**
★★★ 之前看不到,因为**扫描在第一个调用处就结束了**
★★★ ⇒ **`sub_49CF30` 在 `0x49D335` 才读 a3,是十几个调用之后**
        ↓
★★★ `findXAsset()` 仍**单独**问 `DB_IsXAssetDefault`,因为
   **`allowDefault=false` 只在**未命中路径**抑制默认值**
★★★ ⇒ **存在但未加载的资产仍返回默认值**
```

### ★★★ 六个 `using` 的类型契约（第 379–459 行）

```cpp
using DBFindXAssetHeader  = XAssetHeader(__cdecl *)(u32 type, const char *name, bool allowDefault);
using DBIsXAssetDefault   = bool(__cdecl *)(u32 type, const char *name);
using DBLinkXAssetEntry   = void *(__cdecl *)(u32 type, void **header);
using CCSInitialize       = int(__cdecl *)();
using CurrentCharacterGet = int(__cdecl *)();
using CharacterSlotGet    = int(__cdecl *)(int characterIndex, int slot);
using LoadoutRecordBuild  = unsigned short(__cdecl *)(unsigned short *record);
using WeaponLookup        = u32(__cdecl *)(const char *name);
using WeaponResolver      = u32(__cdecl *)(const char *name, void (__cdecl *registerCallback)(int));
using AttachmentLookup    = u32(__cdecl *)(const char *name);
using WeaponRegistryReset = void(__cdecl *)();
using WeaponRegistryInitialize = int32(__cdecl *)(int32 completeRegistration);
using WeaponKnifeStatsLoad     = int32(__cdecl *)();
using ZoneLoaded               = bool(__cdecl *)(const char *name);
using BGGetPlayerEyePosition   = void(__cdecl *)(int32 linkedEntityContext, const void *playerState, float *origin, int32 time);
using Trace                    = void(__cdecl *)(void *result, const float *start, const float *end,
                                                  const TraceBounds *bounds, int32 passEntityNum, u32 contentMask);
```

### ★★★★★ **三个"没有 `using`"的 ABI**（第 403–429 行，逐字）

```cpp
// CODDIFF(1649370): **sub_619E90 takes TWO arguments, not one, and the first is in
// EAX -- so it has no C calling convention and is stored as a raw pointer**, the same
// way ConfigStringGet already is. The game's own call site says so outright:
//
//     **618bbe  push ecx**        ; the 144-byte destination record
//     **618bbf  mov eax, edi**    ; <- the index, in EAX
//     **618bc1  call sub_619E90**
//     **618bc6  add esp, 4**      ; **ONE stack argument, caller cleans**
//
// and **edi there is a loop counter running 0 .. dword_82E13A4 - 1**, so **the index
// is a SESSION MEMBER index and not a character index**. sub_619E90 **scales it by
// 160** (`lea edi,[edi+edi*4]` then `shl edi,5`) into the member array at
// **unk_C911424**, and **sub_620B90 clears that array with the bound `v0 <= 0x11` --
// eighteen entries, which is MaximumSessionMembers, not the twelve of CharacterItemCount.**
//
// **Declared as void(__cdecl *)(void *) it ran with EAX holding whatever the last
// expression left there**, i.e. **it indexed the member array at an arbitrary offset**.
// **There is deliberately no `using` for it: a type that cannot express the ABI is
// exactly what let the wrong one compile.**
```

★★★★★ **⇒ 七个精确值：**
```
`sub_619E90` 取**两个参数**,**第一个在 EAX**
        ↓
★★★ 调用点：`0x618BBE push ecx` / `0x618BBF mov eax, edi` / `0x618BC1 call` / `0x618BC6 add esp,4`
★★★ ⇒ **一个栈参数,调用者清理**
        ↓
★★★ `edi` = 循环计数 `0 .. dword_82E13A4 - 1` ⇒ **是**会话成员索引**,不是角色索引**
★★★ 缩放 **160**：`lea edi,[edi+edi*4]` 然后 `shl edi,5` ⇒ `edi*5*32 = edi*160`
★★★ 数组在 **`unk_C911424`**
★★★ **`sub_620B90` 用 `v0 <= 0x11` 清除** ⇒ **18 个条目** = `MaximumSessionMembers`
        ↓
★★★★★ ⇒ **"故意没有 `using`：一个无法表达该 ABI 的类型,正是让错误类型编译通过的原因"**
```

### ★★★★★ **`CL_GetConfigString` 的 ESI**（第 422–429 行，逐字）

```cpp
// CODDIFF(1649370): **CL_GetConfigString takes its index in ESI on this build, not
// ECX**, so it has **NO C calling convention** and is stored as a raw pointer and
// reached through `nativeConfigString()`. **3.3.3.3's sub_4F9850 opens
// `cmp ecx, 0x1B92`; out.exe's sub_514880 opens `cmp esi, 0x31D9` and indexes the
// class table as `[esi + 0x77D8250]`.** Declared `__fastcall` the index went to ECX
// and **the callee read whatever the caller had left in ESI, so EVERY index returned
// the same unrelated string**.
```

★★★★★ **⇒ 五个精确值：**
```
3.3.3.3：`sub_4F9850` 开 `cmp ecx, **0x1B92**`（索引在 **ECX**）
1649370：`sub_514880` 开 `cmp esi, **0x31D9**`（索引在 **ESI**）,表基址 **`0x77D8250`**
        ↓
★★★ ⇒ **`0x31D9` 与报告 127 的 configstring 校验器上界**完全一致** ✓
★★★ ⇒ **`0x77D8250` 与报告 127 的 CCS 类型字节表**完全一致** ✓
        ↓
★★★★★ ⇒ 声明成 `__fastcall` ⇒ **每个索引都返回同一个无关字符串**
```

---

## 九、★★★★★ **`CharacterOptionSelectionMask` 的 384 位**

### 9.1 ★★★★★ 完整注释（第 1615–1638 行，逐字）

```cpp
// **THE TWELVE WORDS AT clientState +0x4C ARE A 384-BIT SELECTION MASK**, and this
// is the only thing that can build it. Read straight off **sub_80E600**, which is what
// **CG_SetupClientCharacterInfo 0x541800** hands those twelve dwords to:
//
//     **80e729  cmp   [eax+24h], edi**              ; **charDef+36 = option COUNT**
//     **80e732  mov   ecx, edi / and ecx, 1Fh**
//     **80e737  mov   edx, 1  / shl edx, cl**       ; **1 << (i & 31)**
//     **80e743  test  [ebx+ecx*4+10h], edx**        ; **request+0x10 == the twelve**
//     **80e74d  mov   edx, [eax+28h]**              ; **charDef+40 = option LIST**
//     **80e750  movzx eax, word ptr [edx+edi*2]**   ; **optionList[i], an ITEM ID**
//
// So **bit `i` of dword `i/32` selects `optionList[i]`**, and the character
// definition -- **reached from characterItemId, which is already on the wire as
// field 20** -- supplies the list. **THAT is why the block needs no decode key:
// both sides index the same per-character table.** Handoff section **184**.
//
// **An equipped id absent from the option list leaves its bit CLEAR**, which is
// **the character's own default piece, never a wrong one**.
```

★★★★★ **⇒ 八个精确值：**
```
`clientState + **0x4C**` = **12 个 dword = 384 位掩码**
        ↓
★★★ 六条指令：
   `0x80E729 cmp [eax+0x24], edi` ⇒ **`charDef+36` = 选项数**
   `0x80E732 mov ecx,edi / and ecx,1Fh`
   `0x80E737 mov edx,1 / shl edx,cl` ⇒ **`1 << (i & 31)`**
   `0x80E743 test [ebx+ecx*4+0x10], edx` ⇒ **`request+0x10` = 那 12 个 dword**
   `0x80E74D mov edx,[eax+0x28]` ⇒ **`charDef+40` = 选项列表**
   `0x80E750 movzx eax, word ptr [edx+edi*2]` ⇒ **`optionList[i]` = 一个物品 id**
        ↓
★★★ ⇒ **dword `i/32` 的 bit `i` 选择 `optionList[i]`**
★★★ 角色定义从 **`characterItemId`**（**线材字段 20**）到达
        ↓
★★★★★ ⇒ **"这就是为什么这块**不需要解码键**：两侧索引同一张每角色表"**
★★★ 不在选项列表里的已装备 id ⇒ **位保持清零** ⇒ **角色自己的默认件,绝不是错的**
```

---

## 十、★★★★★ **约 200 个 RVA 的完整分类**

### 10.1 ★★★★★ **身份与 DB/qcommon（6 个）**

| 常量 | 值 |
|---|---|
| `ExpectedTimestamp` | **`0x6096930A`** |
| `ExpectedImageSize` | **`0x0E659000`** |
| `ComFrameRva` | **`0x0FEA20`** |
| `DBFindXAssetHeaderRva` | **`0x09CF30`** |
| `DBIsXAssetDefaultRva` | **`0x09D3D0`** |
| `DBLinkXAssetEntryRva` | **`0x09DA10`** |

### ★★★ **消息与 CCS（8 个）**

| 常量 | 值 |
|---|---|
| `MsgInitRva` | **`0x26E720`** |
| `MsgWriteBitsRva` | **`0x26E840`** |
| `MsgWriteStringRva` | **`0x26EA90`** |
| `LevelZoneLoadRva` | **`0x09E600`** |
| `CCSClearRva` | **`0x261610`** |
| `CCSInitializeRva` | **`0x261A30`** |
| `CCSGetConstantStringRva` | **`0x261C50`** |
| `ZoneLoadedRva` / `IsZoneLoadedRva` | **`0x09F180`**（同一地址） |

### ★★★ **客户端 UI dvar 缓存（5 个，仅客户端）**

| 常量 | 值 |
|---|---|
| `RegisterGameplayDvarsRva` | **`0x0E8990`** |
| `GametypeDvarCacheRva` | **`0x2EAA908`** |
| `IsZoneLoadedRva` | **`0x09F180`** |
| `UiZoneNameRva` | **`0x9B5F58`** |
| `UiZoneStateFlagsRva` | **`0x18DAF1C`** |

★★★ **⇒ 注释（第 486–494 行，逐字）：**
```
"`sub_4E8990` is the **only writer** of every slot in that table, it has **exactly
 one caller**, and the chain above it -- **sub_616F60 <- sub_6172E0 <- sub_617700 <-
 sub_4757D0** -- is gated on **`DB_IsZoneLoaded("ui_mp")`**. A client driven into a
 match **without the legacy UI zone ever loading** therefore reaches
 `CL_ParseGamestate` **with the cache still NULL**, and **the level load faults at
 `0x0043204F` reading `[cache + 0x0C]`**."
```

### ★★★ **碰撞与 trace（18 个）**

| 常量 | 值 |
|---|---|
| `TraceRva` | **`0x06EA60`** |
| `WorldTraceRva` | **`0x268220`** |
| `TransformedBrushModelTraceRva` | **`0x268470`** |
| `TransformedCapsuleTraceRva` | **`0x268560`** |
| `CalcTraceExtentsRva` | **`0x269460`** |
| `PointTraceToEntitiesRva` | **`0x06E6D0`** |
| `DObjGeomTracelinePartBitsRva` | **`0x3831C0`** |
| `DObjContentsTracelinePartBitsRva` | **`0x383360`** |
| `DObjTracelineRva` | **`0x3825F0`** |
| `DObjContentsTracelineRva` | **`0x383290`** |
| `PointTraceStaticModelsRva` | **`0x26A3D0`** |
| `DObjCalcSkelRva` | **`0x3847A0`** |
| `GEntitiesRva` | **`0x2D437A0`** |
| `ServerGameEntitiesPointerRva` | **`0x76BAC74`** |
| `ServerGameEntityCountRva` | **`0x76BAC78`** |
| `SVLinkEntityRva` | **`0x34EF10`** |
| `SVUnlinkEntityRva` | **`0x34ECE0`** |
| `SVTraceRva` | **`0x06E780`** |
| `CollisionMapRva` | **`0x73E1C00`** |

### ★★★★★ **武器与开火（17 个）**

| 常量 | 值 |
|---|---|
| `BGGetPlayerEyePositionRva` | **`0x0123B0`** |
| `BulletEndposRva` | **`0x192230`** |
| `ViewMovementDamageKickRva` | **`0x0353E0`** |
| `ViewMovementIdleAnglesRva` | ★ **`0x0355D0`**（= `sub_4355D0`,报告 128 的 idle 阶段） |
| `ViewMovementBobAnglesRva` | **`0x035770`** |
| `ViewMovementAdsBobRva` | **`0x035910`** |
| `WeaponMovementBaseRva` | **`0x034520`** |
| `WeaponMovementSwayRva` | **`0x034680`** |
| `WeaponMovementRecoilRva` | ★ **`0x034C20`**（= `sub_434C20`） |
| `WeaponMovementBobRva` | **`0x034E20`** |
| `SetWeaponMovementAnglesRva` | ★ **`0x034F90`**（= `sub_434F90`） |
| `AnglesToQuaternionRva` | ★ **`0x3853E0`**（**不是** `AnglesToAxis`） |
| `AngleVectorsRva` | ★ **`0x367890`**（= `sub_767890`） |
| `MatrixMultiplyRva` | **`0x3653E0`** |
| `AxisToAnglesRva` | **`0x3667B0`** |
| `PmoveSingleRva` | **`0x01CB40`** |
| `PMSetPitchValuesRva` | ★ **`0x01DB40`** |
| `PlayerStateToEntityStateRva` | **`0x0116F0`** |

★★★ **⇒ 与报告 128 的对照**完全吻合** ✓**
```
报告 128 说 `0x004310F0`（recoil）/ `0x004312F0`（bob）/ `0x00434F90`（setAngles）
        ↓
★★★ 本文件：`WeaponMovementRecoilRva = **0x034C20**`（= 0x00434C20）
★★★ 报告 128 的 `0x004310F0` 与 `0x00434C20` **不同** ⇒ 记录为**待核对**
   （报告 128 的 `callWeaponRecoil` 用的是 `0x004310F0`,本文件是 `0x034C20`）
```

### ★★★ **动画与 DObj（24 个）**

| 常量 | 值 |
|---|---|
| `BGAnimScriptEventRva` | ★ **`0x007E10`**（= `sub_407E10`） |
| `BGFindAnimsRva` | **`0x004D80`** |
| `BGAnimParseAnimScriptRva` | **`0x007530`** |
| `BGLoadAnimTreesRva` | **`0x00B130`** |
| `ScrCreateObjectRva` | **`0x34CED0`** |
| `ScrPrecacheAnimTreesRva` | ★ **`0x34AF50`**（= `sub_74AF50`,**不是** `0x34AAF0`） |
| `BGFindAnimTreesRva` | ★ **`0x00B210`**（= `sub_40B210`） |
| `BGFinalizePlayerAnimsRva` | **`0x004FE0`** |
| `NativeLerpFrameAccessorInitializeRva` | ★ **`0x003C70`**（= `sub_403C70`） |
| `BGPlayerAnimationRva` | **`0x00A960`** |
| `BGUpdatePlayerDObjRva` | **`0x00AB30`** |
| `MantleCreateAnimsRva` | **`0x00CCA0`** |
| `MantleAnimsRva` | **`0x1574568`** |
| `HunkAllocXAnimRva` | **`0x368220`** |
| `XAnimFreeInfoRva` | ★ **`0x386340`**（= VA `0x006497C0`） |
| `DObjFreeRva` | **`0x381A80`** |
| `ServerDObjGetRva` | **`0x34E160`** |
| `ServerDObjCreateRva` | **`0x26BEE0`** |
| `ServerDObjMapRva` | **`0x73E7F20`** |
| `ServerDObjInUseRva` | **`0x73E8F20`** |
| `ServerDObjPoolRva` | **`0x73E9720`** |
| `ServerDObjFreeCountRva` | **`0x73E7F1C`** |
| `ServerAnimDObjMapRva` | **`0x7455720`** |
| `NativeLerpFrameZeroVectorRva` | **`0x9A2B2C`** |

### ★★★★★ **访问器键（5 个）**

| 常量 | 值 |
|---|---|
| `NativeLerpFrameSetKeyRva` | **`0xA60B3C`** |
| `NativeLerpFrameGetKeyRva` | **`0xA60B40`** |
| `NativePlayerStateAccessorSetKeyRva` | ★ **`0xA60B74`** |
| `NativePlayerStateAccessorGetKeyRva` | ★ **`0xA60B78`** |
| `PmoveHandlersRva` | ★ **`0xA5FCD0`** |

★★★ **⇒ 与报告 132 的 `ds:0x00E60B74` / `ds:0x00E60B78`**完全一致** ✓**
**⇒ 且 `NativeLerpFrameSetKey`/`GetKey` 是 **`0xA60B3C`/`0xA60B40`**（**相差 4**）⇒ 另一对。**

### ★★★ **动画基址（2 个）**

| 常量 | 值 |
|---|---|
| `AnimConditionBasePointerRva` | ★ **`0x7E7F730`**（= `dword_827F730`） |
| `AnimScriptDataPointerRva` | ★ **`0x7E7F734`**（= `dword_827F734`） |

### ★★★★★ **武器注册表（14 个）**

| 常量 | 值 |
|---|---|
| `WeaponLookupRva` | ★ **`0x02F2F0`**（= `sub_42F2F0`） |
| `WeaponResolverRva` | **`0x02F3E0`** |
| `AttachmentLookupRva` | **`0x02F650`** |
| `WeaponRegistryResetRva` | **`0x02F160`** |
| `WeaponRegistryInitializeRva` | ★ **`0x02FE80`**（= `sub_42FE80`） |
| `CollisionMapLoadRva` | **`0x262D90`** |
| `CollisionWorldLinkRva` | **`0x269A40`** |
| `WeaponDefinitionsRva` | ★ **`0x1588B50`**（= `0x01988B50`） |
| `WeaponRegistryCountRva` | **`0x7E7F738`** |
| `WeaponRegistryLookupCacheRva` | **`0x7E7F73C`** |
| `WeaponRegistryModeRva` | **`0x7ECA52C`** |
| `WeaponKnifeStatsLoadRva` | **`0x030670`** |
| `PerWeaponAttachmentCountsRva` | **`0x1588638`** |
| `AttachmentModelDefinitionsRva` | **`0x158B8A0`** |
| `AttachmentMappingsRva` | **`0x158C0A0`** |
| `InternedStringTableRva` | **`0x1578640`** |
| `NoneAttachmentModelIndexRva` | **`0x15DDECC`** |
| `AttachmentModelCountRva` | **`0x1588B4C`** |

### ★★★★★ **`BaseWeaponAssetCount = 0x514` 的 `static_assert`**（第 847–878 行，逐字）

```cpp
// CODDIFF(1649370): **the per-weapon attachment count array is 1300 entries here and
// 500 on 3.3.3.3**, and **it is bounded by the two RVAs either side of it** -- so the
// static_assert below **is the measurement, not a comment about one**. It lives here
// because **it was written out twice and only ONE copy got updated**, which quietly
// **rejected every base weapon from 500 up as out of range**.
static constexpr std::uint32_t BaseWeaponAssetCount = **0x514**;
...
static_assert(
    AttachmentModelCountRva - PerWeaponAttachmentCountsRva == BaseWeaponAssetCount,
    "the per-weapon attachment counts are **one byte each** and fill the gap "
    "between these two globals: change a base weapon count without the RVAs "
    "and this is what says so");
```

★★★★★ **⇒ 四个精确值：**
```
`BaseWeaponAssetCount = **0x514**` = **1300**
3.3.3.3 = **500**
        ↓
★★★ `AttachmentModelCountRva - PerWeaponAttachmentCountsRva`
   = **`0x1588B4C - 0x1588638`** = **`0x514`** ✓
★★★ ⇒ **每个武器的附件计数是**1 字节**,填满这两个全局之间的空隙**
        ↓
★★★ 历史故障：**同一个值写了两处,只更新了一处** ⇒ **500 以上的所有基础武器被判越界**
```

### ★★★★★ **`MaximumWeaponAssetIndex` 的别名**（第 854–864 行，逐字）

```cpp
// CODDIFF(1649370): **every weapon-index sanity check in this project was `> 0x3FF`,
// which is 3.3.3.3's**. That number is **a WIRE WIDTH, not a table size**: the weapon
// index is **ten bits there and ELEVEN here** (**sv_gamestate_mp.cpp's WeaponIndexBits,
// section 26**), and **the registry table went 900 -> 1700 entries with it**. A modular
// weapon is registered dynamically and **lands near the END of that table**, so
// **rejecting anything above 1023 rejected exactly the weapons a real loadout produces**.
// **Defined in sv_gamestate_mp.hpp; ALIASED here, never re-derived.**
static constexpr std::uint32_t MaximumWeaponAssetIndex = ::CodolGameServer::MaximumWeaponAssetIndex;
```

★★★★★ **⇒ 五个精确值：**
```
`0x3FF` = **1023** ⇒ **3.3.3.3 的**线宽**,不是表大小**
        ↓
★★★ 3.3.3.3：**10 位**,注册表 **900** 条
★★★ 1649370：**11 位**,注册表 **1700** 条
        ↓
★★★ ⇒ **模块化武器注册在表**末端** ⇒ 拒绝 > 1023 恰好拒绝**真实 loadout 产生的那些**
        ↓
★★★ **"在 `sv_gamestate_mp.hpp` 里定义;这里只**别名**,永不重推"**
```

### ★★★ **七个 dvar 注册块**（第 805–830 行）

```cpp
static constexpr std::size_t GameplayDvarsRegisterRva = **0x00E8990**;
static constexpr std::size_t GameLogDvarsRegisterRva   = **0x00EA390**;
static constexpr std::size_t VehicleDvarsRegisterRva   = **0x03BC5C0**;
static constexpr std::size_t PlayerDvarsRegisterRva    = **0x00EAF30**;
static constexpr std::size_t ActorDvarsRegisterRva     = **0x000FAF0**;
static constexpr std::size_t MiscDvarsRegisterRva      = **0x03C2240**;
static constexpr std::size_t ScoreDvarsRegisterRva     = **0x00E83F0**;
static constexpr std::size_t GametypeDvarRva           = **0x2EAA908**;
```

★★★★★ **⇒ 完整注释（第 805–822 行，逐字）：**
```
"**THE GAMEPLAY DVARS ARE REGISTERED BY CG_Init, AND CG_Init NEVER RUNS IN A DEDICATED
 PROCESS.** **sub_616F60 calls eight registration blocks back to back at
 0x61701D..0x617040**, and in a driven server **NONE of them have run** -- so every
 dvar pointer they cache is **still null**, and the native code that reads one does it
 the way **sub_432000** does: **`mov ecx, [edx+0Ch]`, no null check.**
        ↓
★★★ **That is what faulted.** The weapon registry's per-weapon gametype filter reads
 **`*(char **)(g_gametype + 0xC)`** to test the weapon's `|`-separated gametype list,
 and read **address 0xC**.
        ↓
★★★ **SEVEN of the eight are called here, in CG_Init's order.** Each was
 **disassembled first** and each is nothing but **`push "name"; call Dvar_Register*;
 mov dword_..., eax`** -- no device state, no allocation, and **idempotent**, because
 **Dvar_Register hands back an existing dvar**.
 **THE EIGHTH IS NOT ONE OF THEM**: **sub_4EAC90** opens with
 **memset(unk_31437A0, 0, 0x164000)** and is a **state initializer** that happens to
 sit in the same run of calls. **It is left out on purpose.**"
```

★★★ **⇒ 五个精确值：**
```
`sub_616F60` 在 **`0x61701D..0x617040`** 连续调 **8 个注册块**
        ↓
★★★ **专服里一个都没跑** ⇒ dvar 指针全 null
★★★ 原生代码读法：**`mov ecx, [edx+0Ch]`,无空检查**
★★★ ⇒ **故障点：`*(char**)(g_gametype + 0xC)`,读**地址 `0xC`**
        ↓
★★★ **八个中调了 7 个**（按 `CG_Init` 顺序）
★★★ 每个都只是 `push "name"; call Dvar_Register*; mov dword_..., eax`
   ⇒ **无设备状态、无分配、幂等**
★★★ **第 8 个不是注册块**：`sub_4EAC90` 开 `memset(unk_31437A0, 0, **0x164000**)`
   ⇒ **状态初始化器**,只是碰巧在同一串调用里 ⇒ **故意排除**
```

### ★★★ **`WeaponWalkConfigStringBase` 与 `WeaponWalkEntryCount`**（第 831–838 行，逐字）

```cpp
// The walk's own base and count, **read off the game's loop rather than derived**:
// **sub_59B560 opens `lea esi, [edi+1748h]`** before calling CL_GetConfigString, and
// **CL_ParseGamestate bounds the loop with `cmp edi, 6A4h`**.
// **0x1748 = 5960 and 0x6A4 = 1700**, which is **exactly what sv_gamestate_mp.hpp
// derived a different way in §26**.
static constexpr std::size_t WeaponConfigStringWalkRva = **0x019B560**;
static constexpr std::uint32_t WeaponWalkConfigStringBase = **0x1748**;
static constexpr std::uint32_t WeaponWalkEntryCount = **0x6A4**;
```

★★★★★ **⇒ 三个精确值：**
```
`sub_59B560` 开 **`lea esi, [edi+0x1748]`** ⇒ 基址 **`0x1748`** = **5960**
`CL_ParseGamestate` 用 **`cmp edi, 0x6A4`** 限界 ⇒ **`0x6A4`** = **1700**
        ↓
★★★ ⇒ **与 `sv_gamestate_mp.hpp` §26 用**另一条路**推出的完全一致** ✓
```

### ★★★ **`Com_Error` 的三个状态**（第 839–845 行）

```cpp
static constexpr std::size_t ComErrorTextRva  = **0x2FE7958**;
static constexpr std::size_t ComErrorLevelRva = **0x2FE7904**;
static constexpr std::size_t ComErrorDepthRva = **0x31053DC**;
```

★★★★★ **⇒ 完整注释（逐字）：**
```
"**Com_Error's own state. sub_4F82E0 formats into the text buffer, keeps the level,
 bumps the depth, and then LONGJMPS** -- so after a native fault **a non-zero depth
 says the engine raised an error rather than dereferencing something, and the text
 says which one.**"
```

### ★★★★★ **角色与物品表（18 个）**

| 常量 | 值 |
|---|---|
| `CharacterCurrentItemsCopyRva` | ★ **`0x219E90`**（= `sub_619E90`） |
| `CurrentCharacterGetRva` | ★ **`0x2B87C0`**（= `sub_6B87C0`） |
| `CharacterSlotGetRva` | ★ **`0x10FF30`**（= `sub_50FF30`） |
| `WeaponClassFieldGetRva` | ★ **`0x10FC20`**（= `sub_50FC20`） |
| `LoadoutRecordBuildRva` | ★ **`0x3C5BA0`**（= `sub_7C5BA0`） |
| `CharacterRecordFillDefaultsRva` | ★ **`0x219AD0`**（= `sub_619AD0`） |
| `CharacterRecordToSelectionNamesRva` | ★ **`0x21B6C0`**（= `sub_61B6C0`） |
| `CharacterItemDefinitionTableRva` | **`0x73988FC`** |
| `CharacterItemDefinitionCountRva` | **`0x7398900`** |
| `CharacterItemDecodeKeyRva` | ★ **`0xA4DD90`** |
| `ItemDefinitionsRva` | **`0x739583C`** |
| `ItemDefinitionCountRva` | **`0x7395840`** |
| `ItemLookupRva` | **`0x7395844`** |
| `ItemLookupCountRva` | **`0x7395848`** |
| `ItemBucketOffsetsRva` | **`0x739584C`** |
| `ConstantConfigStringChecksumRva` | **`0x73D8240`** |
| `ConfigStringTypesRva` | ★ **`0x73D8250`**（= `0x77D8250`） |
| `ConstantConfigStringsInitializedRva` | **`0x73DB42C`** |

### ★★★★★ **Profile 的七个偏移**（第 1026–1053 行）

```cpp
static constexpr std::size_t ProfileDataBufferOffset   = **0xA0**;
static constexpr std::size_t ProfileDecodeKeyOffset    = **0x11138**;
static constexpr std::size_t ProfileObfuscatedFlagOffset = **0x1113C**;
static constexpr std::size_t ProfileDocumentSize       = **0x8000**;
static constexpr std::uint32_t AssetTypeStructuredDataDef = **39**;
static constexpr std::size_t PlayerDataDefBufferPointerOffset = **8**;
static constexpr std::size_t PlayerDataDefOffsetTablePtrOffset = **0x38**;
static constexpr std::size_t ProfileManagerRva = **0xE14BC48**;
static constexpr std::size_t PublicProfileOffset = **16**;
static constexpr std::size_t ProfileChunkMaskOffset = **0x1008C**;
static constexpr std::size_t ProfileOperationOffset = **116**;
static constexpr std::size_t ProfileParsedOffset = **0x1112C**;
static constexpr std::uint32_t ProfileRequiredChunkMask = **0x07FFFFFF**;
```

★★★★★ **⇒ 七个精确值：**
```
`ProfileDataBufferOffset = **0xA0**`（文档）
`ProfileDecodeKeyOffset = **0x11138**`（混淆键）
`ProfileObfuscatedFlagOffset = **0x1113C**`（标志）
`ProfileDocumentSize = **0x8000**`（32 KB）
        ↓
★★★ 解码：**`ROL32(raw ^ key, 8)`**
★★★ def 资产类型 = **39**（`AssetTypeStructuredDataDef`）
★★★ `def = *(DB_FindXAssetHeader(39, "mp/playerdata.def") + **8**)`
★★★ 偏移表 = **`*(*(def + **0x38**) + 4 * index)`**
        ↓
★★★ `ProfileManagerRva = **0xE14BC48**`（= `sub_7F9090` 返回 `&dword_E54BC48`）
★★★ `PublicProfileOffset = **16**`
★★★ `ProfileChunkMaskOffset = **0x1008C**`
★★★ `ProfileOperationOffset = **116**`
★★★ `ProfileParsedOffset = **0x1112C**`
★★★ `ProfileRequiredChunkMask = **0x07FFFFFF**`
```

### ★★★★★ **`sub_50FF30` 的空档案陷阱**（第 1119–1129 行，逐字）

```cpp
// **AND THE GUARD THAT HAS TO COME WITH IT.** sub_50FF30 opens with
//     **v2 = sub_7F9090() + 160; if (!v2) return 0;**
// which **does NOT catch a null profile** -- **a null manager makes v2 = 160, the
// check passes, and 160 is then dereferenced**. **Calling it without a parsed public
// profile is an access violation, and __try does not save you: CODOL's own crash
// reporter takes the fault first and writes a ClientException.**
//
// **CodolMatchFlow.py never calls either accessor without checking the profile
// (readCurrentCharacter returns null unless publicProfile.ready), and that guard is
// load-bearing -- porting the call without it killed the client.**
```

★★★★★ **⇒ 四个精确值：**
```
`v2 = sub_7F9090() + **160**; if (!v2) return 0;`
        ↓
★★★ **null manager ⇒ `v2 = 160` ⇒ 检查通过 ⇒ `160` 被解引用**
★★★ ⇒ **`__try` 救不了：CODOL 自己的崩溃报告器先拿到故障并写 `ClientException`**
        ↓
★★★ **`CodolMatchFlow.py` 从不在没检查 profile 时调用**（`readCurrentCharacter`
   在 `publicProfile.ready` 为假时返回 null）
★★★ ⇒ **"那个守卫是承重的 —— 不带它移植调用**杀死了客户端**"**
```

### ★★★ **会话成员（4 个）**

```cpp
static constexpr std::size_t RoomSingletonRva = **0x7EE13FC**;
static constexpr std::size_t SessionMemberCountRva = **0x7EE13A4**;
static constexpr std::size_t SessionMemberItemHandlesRva = **0xC511424**;
static constexpr std::size_t SessionMemberStride = **160**;
static constexpr std::size_t SessionMemberCapacity = **18**;
static constexpr std::size_t SessionMemberItemHandleCount = **12**;
```

★★★ **⇒ `0x82E13FC - 0x82E13A4` = **`0x58`**（88 字节）⇒ 注释（第 1183 行）已确认。**
**⇒ `sub_620B90` 用 `v0 <= **0x11**` 清除 ⇒ **18 个** ✓**

### ★★★ **`sub_619E90` 的两个步长**（第 1187–1196 行，逐字）

```cpp
// **sub_619E90 walks the SOURCE at stride 4 and the destination at stride 12**
// (`add edi,4` / `add ebx,0Ch` at **0x619efd**), so **the source is twelve PLAIN
// dwords** -- **item handles, 48 bytes of the 160-byte member record**. **It is the
// 12-byte destination record that carries the obfuscation**, and **the engine applies
// it itself in sub_810B20**.
```

★★★ **⇒ 两个步长：源 **4**,目标 **12**。**
**⇒ 源 = **12 个纯 dword**（48 字节）⇒ 是 **160 字节成员记录**的一部分。**
**⇒ 混淆在 **12 字节的目标记录**上,引擎在 **`sub_810B20`** 自己施加。**

### ★★★★★ **`ExcludedItems` 与 `OwnershipResolver`**（第 1889–1897 行）

```cpp
// **sub_5DE440 parses a comma-separated string of item ids into these**: the array,
// its length, and its capacity. **VA 0xC9113CC / 0xC9113D4 at image base 0x400000.**
static constexpr std::size_t ExcludedItemsArrayRva = **0x8D113CC**;
static constexpr std::size_t ExcludedItemsCountRva = **0x8D113D4**;

// **sub_5E3760, the ownership resolver behind 94 call sites.**
// **int __usercall(int itemId@<eax>, void *outRecord@<edi>) -> eax**; the record's
// **+4 is a u16 set to 1 when the item is owned**.
static constexpr std::size_t OwnershipResolverRva = **0x1E3760**;
```

★★★★★ **⇒ 五个精确值：**
```
`sub_5DE440` 解析逗号分隔的物品 id 串 ⇒ 三个全局：
   **`0x8D113CC`**（数组）/ **`0x8D113D4`**（计数）
        ↓
★★★ `sub_5E3760` = 所有权解析器（**94 个调用点**）
★★★ ABI：**`int __usercall(int itemId@<eax>, void *outRecord@<edi>) -> eax`**
★★★ 记录 **`+4` 是 `u16`,物品被拥有时置 1**
        ↓
★★★ ⇒ 与报告 127 的 `sub_5E3760`（94 个调用点）**完全一致** ✓
```

### ★★★★★ **`CharacterItemCount` 的 12 与 `CharacterSelectionNameCount = 11`**（第 1115–1118 行）

```cpp
// **Twelve entries of twelve bytes.** The size is **CharacterItemCount's**, and the
// entry layout is **NativeCharacterItemRecord's** -- see the CODDIFF on that struct,
// which is **where the eight-versus-twelve stack overrun was found**.
static constexpr std::size_t CharacterSelectionNameCount = **11**;
```

★★★ **⇒ `12 条目 × 12 字节 = 144 字节`。**
**⇒ `CharacterSelectionNameCount = 11`** ⇒ **11 个名字**（不是 12）⇒ **与 `ClientCharacterPresentation::selectionIds` 的 `std::array<u16, 11>` 一致 ✓**

---

## 十一、★★★★★ **五个 `enum` 的完整值**

### 11.1 ★★★ `ClientLoadoutResolveFailure`（16 个）

```cpp
None / StagedSlot / NativeResolverUnavailable / ItemName / BaseWeaponLookup /
BaseWeaponResolver / DefaultAttachments / EquippedAttachmentName /
EquippedAttachmentSlot / AttachmentMerge / AttachmentLookup / AttachmentCapacity /
ModularWeaponResolver / WeaponDefinition / ModularWeaponDependency /
AttachmentModelResolution
```

### 11.2 ★★★ `WeaponRegistryInitializationStatus`（3 个）

```cpp
Ready / CommonAssetsUnavailable / InitializationFailed
```

### 11.3 ★★★ `AlphaWeaponPortStatus`（9 个）

```cpp
Disabled / WaitingForCommonAssets / WaitingForWeaponRegistry / WrongThread /
SourceAssetMissing / InvalidDefinition / LinkFailed / RegistrationFailed / Ready
```

### 11.4 ★★★★★ `ServerAnimationInitializationStatus`（15 个）

```cpp
NotInitialized / Ready / InvalidBinding / WrongThread / ContextBusy /
BeginLoadAnimTreesFailed / LoadAnimTreesFailed / AnimationScriptAssetsUnavailable /
FindAnimsFailed / ParseAnimScriptFailed / PrecacheAnimTreesFailed /
FindAnimTreesFailed / EndLoadAnimTreesFailed / FinalizePlayerAnimsFailed / InvalidOutput
```

★★★ **⇒ 15 个值 ⇒ **13 种失败**,顺序即**初始化管线顺序**：**
```
BeginLoadAnimTrees → LoadAnimTrees → (assets) → FindAnims → ParseAnimScript →
PrecacheAnimTrees → FindAnimTrees → EndLoadAnimTrees → FinalizePlayerAnims
        ↓
★★★ **9 个管线阶段** + `NotInitialized` / `Ready` / `InvalidBinding` / `WrongThread` /
   `ContextBusy` / `InvalidOutput` / `AnimationScriptAssetsUnavailable`
```

### 11.5 ★★★ `ClientCharacterPresentationResolveFailure`（9 个）

```cpp
None / InvalidRequest / ItemName / Selection / BaseItemDefinition /
CharacterDefinitionTable / CharacterDefinition / ViewmodelConfigString / ConstantConfigStrings
```

---

## 十二、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **两个身份常量** | `ExpectedTimestamp = **0x6096930A**` / `ExpectedImageSize = **0x0E659000**`（分发）/ **`0x0E5D6000`**（上游） |
| 2 | ★★★ SHA256 | **`36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537`** |
| 3 | ★★★ 两个未说明值 | **`0x57611E31`** / **`0x0C72A000`** |
| 4 | ★★★ 两个 ImageSize 的差 | **`0x83000`** = **536,576**（约 524 KB） |
| 5 | ★★★ 已逐字节验证的四个 RVA | **`SV_LinkEntity` / `SV_UnlinkEntity` / `SV_Trace` / `BG_GetPlayerEyePosition`** |
| 6 | ★★★★★ **旧缓冲区 `0xA6000`** | `BG_FindAnimTrees` 的 `memset(**0xACE70**)` @ **`0x0040B226`** |
| 7 | ★★★ **两数不符** | `0xACE70 - 0xA6000` = **11,888**；注释说 **28,272** ⇒ **待核对** |
| 8 | ★★★★ 五个读偏移 | `+0xAF31C` / `+0xAF314` / `+0xAF338` / **`+0xAF350`**（stride `0x450`）/ `+0xAF318` |
| 9 | ★★★ 游戏自己的块 | **`ebx + 0xD1900`**（858,368）,范围不可见 |
| 10 | ★★★★★ **`ServerAnimConditionStorageSize = 0x100000`** | 最大测到 `0xB4200` ⇒ 留 **310,784 字节**余量 |
| 11 | ★★★★★ 理由 | "**over-allocating costs address space, under-allocating hands the engine someone else's memory and the failure looks like anything at all**" |
| 12 | ★★★★★ **`sub_407530` 的清与不清** | 清 **`+0x1A004`**（movetype）/ **`+0x25D7C`**（一个废弃脚本）；**不清 `scriptEvents`** |
| 13 | ★★★ 唯一清零者 | **`sub_40B210` 的 `memset(0x827F730, 0, 0xACE70)` @ `0x0040B226`** |
| 14 | ★★★★★ **初始化顺序** | parse → BG_FindAnimTrees → BG_FinalizePlayerAnims = **`0x00454CDF` / `0x00454D38` / `0x00454D42`** |
| 15 | ★★★★★ **`ServerCharacterInfoBaseOffset = 0xAF350`** | 3.3.3.3 是 **`0x96E20`**；扫描 **12/14** vs **11/16** |
| 16 | ★★★ 两者的离群值 | 3.3.3.3 = `base+0x2D0` / `base+0x308`；1649370 = `base+0x334` / `base+0x37C` |
| 17 | ★★★ 独立佐证 | 动画投影 **`0x53DE1F`** 的 `lea edi,[ecx+eax+0xAF350]` |
| 18 | ★★★★★ 3.3.3.3 的公式 | **`dword_7EB7B80 + 618016 + 952 * ps[+0x144]`**（`sub_AA94C0` @ `0x004094C0`） |
| 19 | ★★★★★ **`ServerLoadAnimStorageSize = 0x12000`** | **1024 × 72**；`sub_404FE0` 用 `v5 += 72` |
| 20 | ★★★ 六个精确地址 | `0x454C6D` / `0x454CCA` / `0x454CD6` / `0x454CD8` / `0x454CD9` / `0x454CDF` |
| 21 | ★★★ 两个全局 | `dword_1971E04`（数组）/ `dword_196DB0C`（容量） |
| 22 | ★★★★★ 格言 | "**a match is a suspicion and only a check is a result**" |
| 23 | ★★★★★ **`EntityOriginKeyRvas`** | **`0xA51A84`** / **`0xA51B1C`** / **`0xA51B20`**；第一个离另两个 **`0x98`** |
| 24 | ★★★ 解码公式 | **`encoded ^ fieldAddress ^ ~key`**（**`~key`**） |
| 25 | ★★★ `OriginOffsets` | **`{0x18, 0x1C, 0x20}`** |
| 26 | ★★★★★ **`CharacterItemDecodeKeyRva = 0xA4DD90`** | 旧的 **`0xA57A70`** 是**真实但错的**键 |
| 27 | ★★★ 解码 | **`ROL32(dword_E4DD90 ^ *(dword*)entry ^ *(dword*)(entry+8), 8)`** |
| 28 | ★★★ 五个调用点 | `0x619F20` / `0x618C8E` / `0x618CB2` / `0x618E5A` / `0x619161` |
| 29 | ★★★★★ 判据规则 | 两个地址都读 **`0xFFFFFFFF`** ⇒ **只有调用点能判别** |
| 30 | ★★★★★ **`LoadoutRecordCache`** | **38 槽 × 168 字节**；`slot+4` 标志 / `slot+8/+12` 两键 / `slot+8` 记录起点 |
| 31 | ★★★ 记录布局 | word **12..23** 角色物品 / word **24..30** 武器 0 / **31..37** / **38..44** / **45..51** |
| 32 | ★★★ `LoadoutRecordClasses = 2` | **4 个武器组 / 2 = 2 个类** |
| 33 | ★★★★★ 定位 owner | **`0x40ABB08`**（否则 **`0x40ABB14`**）⇒ `sub_B9A0F0` ⇒ `ecx+216` ⇒ key @ **`+0x20`/`+0x24`** ⇒ owner **`+248`/`+252`** |
| 34 | ★★★★★ 不定位的后果 | **在大厅里抛硬币** ⇒ **"一个错但合理的 class 是最难注意到的错误"** |
| 35 | ★★★★★ **`CharacterProfileSlotCount = 9`** | 实测 `[545,0,0,0,0,0,0,0,0,null,null,null]`；**槽 9/10/11 抛** |
| 36 | ★★★★★ 关键区分 | **`CharacterItemCount` 的 12 是**另一数组**（`sub_619E90` 填的物品记录） |
| 37 | ★★★★ 12 循环 9 的后果 | **读越界,`__try` 救不了** |
| 38 | ★★★★★ **两遍填充** | `sub_619AD0` 第二遍用**角色自带的每槽默认表**填空条目 |
| 39 | ★★★ 该表位置 | **`character record + 0xC`**,**12 个 `u16`**,记录 **`0x34`**,类型检查 **`def[+5] == 2`** |
| 40 | ★★★★★ 零的含义 | **"零不是空档案,而是正常情况,意思是'这里用角色的默认值'"** |
| 41 | ★★★ 八个槽名 | `0 cha / 1 fpa / 2 boo / 3 fja / 4 han / 5 hea / 6 ves / 7 heg`（**第 8 未列**） |
| 42 | ★★★ 545 的派生 | `cha_infbasea` → `fpa_infbasea` / `boo_infbasea` / `fja_infbasea` / `han_infbasea00` / `hea_socomb` |
| 43 | ★★★★★ **变体选择器是线的函数** | `CG_SetupClientCharacterInfo **0x00541800**` 传 **`*(int*)(clientState+0x154) + 1`** |
| 44 | ★★★ 前端调用者 | 只保留 **1 或 2**,否则**替换成 2**（**`0x61D81B`**） |
| 45 | ★★★★★ 删常量的理由 | **"一个陈旧的默认值,正是专服解析变体 2 而客户端解析变体 1 整整一局的经过"** |
| 46 | ★★★★★ **`DB_FindXAssetHeader` 三参数** | **`sub_49CF30(type,name,allowDefault)`** @ **`0x09CF30`**；包装 **`sub_49D3B0`** @ **`0x09D3B0`** 硬编码 1 |
| 47 | ★★★★★ 丢参数的后果 | `__cdecl` 不崩,但 **`if (a3)` 随机决定**返回 null 还是**新建默认占位符（字符串为 null）** |
| 48 | ★★★ 工具教训 | `audit-binding-abi.py` 之前**在第一个调用处就结束扫描**；`sub_49CF30` 在 **`0x49D335`** 才读 a3 |
| 49 | ★★★ `allowDefault=false` 的边界 | **只在**未命中路径**抑制默认值** ⇒ **存在但未加载仍返回默认值** |
| 50 | ★★★★★ **`sub_619E90` 的 EAX** | **第一个参数在 EAX**；调用点 `0x618BBE..0x618BC6`（**1 个栈参数**） |
| 51 | ★★★ 索引语义 | `edi` 是**会话成员索引**（`0 .. dword_82E13A4 - 1`）,**不是**角色索引 |
| 52 | ★★★ 缩放 160 | `lea edi,[edi+edi*4]` + `shl edi,5` ⇒ **`edi*160`**；数组 **`unk_C911424`** |
| 53 | ★★★★★ **故意没有 `using`** | **"一个无法表达该 ABI 的类型,正是让错误类型编译通过的原因"** |
| 54 | ★★★★★ **`CL_GetConfigString` 的 ESI** | 3.3.3.3 `sub_4F9850` `cmp ecx, **0x1B92**`；1649370 `sub_514880` `cmp esi, **0x31D9**`,表 **`0x77D8250`** |
| 55 | ★★★★★ `__fastcall` 的后果 | **每个索引都返回同一个无关字符串** |
| 56 | ★★★★★ **`CharacterOptionSelectionMask`** | `clientState + **0x4C**` = **12 dword = 384 位** |
| 57 | ★★★ 六条指令 | `0x80E729` / `0x80E732` / `0x80E737` / `0x80E743` / `0x80E74D` / `0x80E750` |
| 58 | ★★★ charDef 的两个偏移 | **`+0x24`**（选项数）/ **`+0x28`**（选项列表） |
| 59 | ★★★★★ 无需解码键 | **"两侧索引同一张每角色表"** |
| 60 | ★★★ 位清零的含义 | 不在列表的已装备 id ⇒ **角色自己的默认件,绝不是错的** |
| 61 | ★★★★★ **七个 dvar 注册块** | `0x00E8990` / `0x00EA390` / `0x03BC5C0` / `0x00EAF30` / `0x000FAF0` / `0x03C2240` / `0x00E83F0` |
| 62 | ★★★★★ 专服故障 | `sub_616F60` 在 **`0x61701D..0x617040`** 调 8 块,**专服一个都没跑** ⇒ **`mov ecx,[edx+0Ch]` 读地址 `0xC`** |
| 63 | ★★★ 第 8 个被排除 | **`sub_4EAC90`** 开 **`memset(unk_31437A0, 0, 0x164000)`** ⇒ **状态初始化器** |
| 64 | ★★★★★ **武器走查基址/计数** | `sub_59B560` `lea esi,[edi+**0x1748**]`；`CL_ParseGamestate` `cmp edi, **0x6A4**` |
| 65 | ★★★ 两数与 §26 一致 | **`0x1748` = 5960** / **`0x6A4` = 1700** ✓ |
| 66 | ★★★ **`Com_Error` 三状态** | 文本 **`0x2FE7958`** / 层级 **`0x2FE7904`** / 深度 **`0x31053DC`** |
| 67 | ★★★ 深度语义 | 非零深度 ⇒ **引擎 raise 了错误,而不是解引用了什么** |
| 68 | ★★★★★ **`BaseWeaponAssetCount = 0x514`** | `0x1588B4C - 0x1588638` = **`0x514`** = **1300**（3.3.3.3 = **500**） |
| 69 | ★★★ 单位 | 每武器附件计数是 **1 字节** |
| 70 | ★★★ 历史故障 | **同一个值写了两处,只更新一处** ⇒ **500 以上全判越界** |
| 71 | ★★★★★ **`MaximumWeaponAssetIndex` 别名** | `0x3FF` 是**线宽不是表大小**；**10 位/900 条 → 11 位/1700 条** |
| 72 | ★★★ 定义位置 | **`sv_gamestate_mp.hpp`**；**这里只别名,永不重推** |
| 73 | ★★★★★ **Profile 七个偏移** | 文档 **`0xA0`** / 键 **`0x11138`** / 标志 **`0x1113C`** / 大小 **`0x8000`** / 类型 **39** / def 指针 **`+8`** / 偏移表 **`0x38`** |
| 74 | ★★★ 解码 | **`ROL32(raw ^ key, 8)`** |
| 75 | ★★★ ProfileManager | **`0xE14BC48`**（`sub_7F9090` 返回 `&dword_E54BC48`） |
| 76 | ★★★ 另外四个 | `PublicProfileOffset = 16` / `ChunkMaskOffset = 0x1008C` / `OperationOffset = 116` / `ParsedOffset = 0x1112C` / `RequiredChunkMask = 0x07FFFFFF` |
| 77 | ★★★★★ **`sub_50FF30` 的空档案陷阱** | `v2 = sub_7F9090() + **160**; if (!v2) return 0;` ⇒ **null manager ⇒ `v2 = 160` ⇒ 检查通过 ⇒ 解引用 160** |
| 78 | ★★★★★ `__try` 救不了 | **CODOL 自己的崩溃报告器先拿到故障并写 `ClientException`** |
| 79 | ★★★ 承重守卫 | `CodolMatchFlow.py` 的 `publicProfile.ready` 检查 ⇒ **不带它移植调用**杀死了客户端** |
| 80 | ★★★ 会话成员 | `RoomSingleton` **`0x7EE13FC`** / `Count` **`0x7EE13A4`**（差 **`0x58`**）/ `ItemHandles` **`0xC511424`** / stride **160** / 容量 **18** / 句柄数 **12** |
| 81 | ★★★★★ `sub_619E90` 两步长 | **源 4 / 目标 12**（`0x619EFD`）；源 = **12 个纯 dword**；混淆在 **12 字节目标记录**上,由 **`sub_810B20`** 施加 |
| 82 | ★★★★★ **`ExcludedItems`** | `sub_5DE440` 解析逗号串 ⇒ 数组 **`0x8D113CC`** / 计数 **`0x8D113D4`** |
| 83 | ★★★★★ **`OwnershipResolverRva = 0x1E3760`** | **`int __usercall(int itemId@<eax>, void *outRecord@<edi>) -> eax`**；记录 **`+4` 的 `u16` = 1 表示拥有 |
| 84 | ★★★ `CharacterSelectionNameCount = 11` | **12 条目 × 12 字节** = 144；名字是 **11 个** |
| 85 | ★★★★★ **五个 enum 的值数** | `ClientLoadoutResolveFailure` **16** / `WeaponRegistryInitializationStatus` **3** / `AlphaWeaponPortStatus` **9** / `ServerAnimationInitializationStatus` **15** / `ClientCharacterPresentationResolveFailure` **9** |
| 86 | ★★★ 动画初始化管线 | **9 个阶段**：BeginLoadAnimTrees → LoadAnimTrees → (assets) → FindAnims → ParseAnimScript → PrecacheAnimTrees → FindAnimTrees → EndLoadAnimTrees → FinalizePlayerAnims |
| 87 | ★★★ `actorHitPoseOwners_` | **`std::array<ActorHitPoseOwner, 2048>`**（**2048** 个实体上限） |
| 88 | ★★★ `NativeServerDObjSkelArenaSize` | **`18 × 256 × 32`** = **147,456** 字节 |
| 89 | ★★★ `nativeServerDObjSkeletonHeight_` | **`std::array<int32, 64>`**（**64** 个实体） |
| 90 | ★★★ `playerDObjReportedState_` | **`std::array<PlayerDObjState, 64>`** |

---

## 十三、结论

### 1. ★★★★★ **`ExpectedTimestamp` + `ExpectedImageSize` 是双重身份校验**

★ **⇒ 分发版与上游**只差 `SizeOfImage`**（`0x0E659000` vs `0x0E5D6000`,差 **524 KB**）,且四个关键 RVA 已逐字节验证。**

### 2. ★★★★★ **`ServerAnimConditionStorageSize = 0x100000` 是"向上取整远超测到的偏移"**

★ **⇒ 旧值 `0xA6000` 小于 `BG_FindAnimTrees` 的 `0xACE70` memset ⇒ **落在下一个成员上 ⇒ 损坏而非崩溃**。**

### 3. ★★★★★ **`ServerCharacterInfoBaseOffset = 0xAF350` 有**扫描统计**支撑**（12/14 vs 11/16）

★ **⇒ 且存储是按正确区域定尺寸的,而数组被放在了**它里面的别处**。**

### 4. ★★★★★ **`0x12000` = 1024 × 72 与 3.3.3.3 **完全相同**却**仍然正确****

★ **⇒ "a match is a suspicion and only a check is a result"。**

### 5. ★★★★★ **三个 `EntityOriginKey` 不连续**（第一个离另两个 `0x98`）

★ **⇒ "三个连续 dword"从来不是本 build 的布局 ⇒ 任何"读一个再加 4"三次有两次错。**

### 6. ★★★★★ **`CharacterItemDecodeKeyRva` 的纠正靠**调用点**而非镜像值**

★ **⇒ 两个地址都读 `0xFFFFFFFF`（运行时初始化）。**

### 7. ★★★★★ **`LoadoutRecordCache` 的 38 × 168 布局与 owner 定位是纯内存读**

★ **⇒ 不定位 owner ⇒ **在大厅里抛硬币** ⇒ **错但合理的 class 是最难注意的错误**。**

### 8. ★★★★★ **`CharacterProfileSlotCount = 9` 而 `CharacterItemCount` 的 12 是**另一数组****

★ **⇒ 12 循环 9 = 读越界,`__try` 救不了。**

### 9. ★★★★★ **`BaseWeaponAssetCount = 0x514` 的 `static_assert` 是**测量本身****

★ **⇒ "同一个值写了两处只更新一处"曾让 500 以上全部判越界。**

### 10. ★★★★★ **`DB_FindXAssetHeader` 的三参数形式：丢参数的后果是**随机****

★ **⇒ `__cdecl` 不崩,但 `if (a3)` 随机决定返回 null 还是**新建的默认占位符**。**

### 11. ★★★★★ **`CharacterOptionSelectionMask` 的 384 位**不需要解码键****

★ **⇒ "两侧索引同一张每角色表"。**

### 12. ★★★★★ **约 200 个 RVA 已完整分类记录**（身份 6 / 消息 8 / dvar 5 / 碰撞 18 / 武器 18 / 动画 24 / 访问器 5 / 注册表 18 / 角色 18 / 会话 6）

---

## 十四、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B / **17,867 行**）** —— 最大单文件
2. ★ **`Appmain.cpp`（565,999 B / **10,564 行**）**
3. 然后 `server_mp` 154 文件（12,604,630 B）
