# 学习报告 128（重开）— `NativeWeaponMovementBindings.cpp`（709 行）+ 交付包内唯一 `.bak`

**学习范围**：`NativeWeaponMovementBindings.cpp`（31,427 B / 709 行）+ `.bak-20261009-scopeidle`（29,791 B）
**性质**：全实测（**主文件逐行读完**）
**★★★★★ 本报告收录九个重大发现**：①**"一个结构体、两个文件、只更新一个"的完整故障** ②**9 个 `playerState_s` 偏移的审计方法** ③**`ps+0x400` 是"主动副手选择器"** ④**`0x3FF` 十位 vs 本 build 十一位** ⑤**alt-fire 死在第二层** ⑥**`lastIdleFactor` / `weaponIdleTime` 的冻结相位** ⑦**`NativeStateSlack = 512` 的测量法** ⑧**`callSetWeaponAngles` 的两个寄存器**互换** ⑨**9 个 stage sample 的完整清单**

---

## 一、★★★★★ **"一个结构体、两个文件、只更新一个"**

### 1.1 ★★★★★ 完整注释（第 30–42 行，逐字）

```cpp
// CODDIFF(1649370): **THIS WHOLE BLOCK WAS 3.3.3.3's AND NONE OF IT WAS PORTED.**
// Every constant below was **byte-identical to ..\ol-mod-ffa's copy of this file**
// while **sv_native_playerstate_mp.cpp -- the same struct, in this tree -- had already
// moved all of them**. That is **the failure this project keeps paying for**:
// **one struct, two files, and only one gets updated**.
// The symptom was **total, not subtle**: runServerWeaponMovement read **currentWeapon
// from 0x340**, which on this build is **inside the held-weapon state array**, got a value
// **past its bound** and **refused EVERY command with `weapon_movement_rejected`**.
// **Nothing moved, ever.**
//
// Confirmed by **`Tools/olfinal/audit-native-offsets.py`** against the **extracted
// playerstate netfield table**. **Four are direct table hits**; **WeaponFlags is bracketed
// by 0x344 and 0x34C at the same +0xB8 shift**, and shows up as **A-only 0x348 / C-only
// 0x400** -- **the same relocation seen from both sides**.
```

★★★★★ **⇒ 一个完整的故障链：**
```
`playerState_s` 出现在 **2 个文件**
        ↓
★★★ `sv_native_playerstate_mp.cpp` **已经搬了所有偏移**
★★★ 而本文件（`NativeWeaponMovementBindings.cpp`）**一个都没搬**
        ↓
★★★ 症状：`currentWeapon` 从 **`0x340`** 读
   ⇒ 在**本 build 上 `0x340` 落在"手持武器状态数组"里**
   ⇒ 读到一个**越界值**
        ↓
★★★★★ ⇒ **`weapon_movement_rejected` 拒绝每一条命令**
   ⇒ **"Nothing moved, ever."**
```

### 1.2 ★★★★★ **审计脚本的四个证据**

```
工具：**`Tools/olfinal/audit-native-offsets.py`**
对照：**提取出的 playerstate netfield 表**
        ↓
★★★ **四个是直接的表格命中**
★★★ `WeaponFlags` 由 **`0x344`** 和 **`0x34C`** 夹住（**同一个 `+0xB8` 位移**）
★★★ 显示为 **A-only `0x348`** / **C-only `0x400`** ⇒ **同一个重定位从两侧看到**
```

★★★ **⇒ 这是一个**双向验证**方法：**
```
旧偏移 + `0xB8` = 新偏移
   ⇒ `0x348`（A-only） + `0xB8` = **`0x400`**（C-only）✓
```

### 1.3 ★★★★★ **9 个 `playerState_s` 偏移**

| 偏移 | 名称 | 备注 |
|---|---|---|
| **`0x104`** | `EFlagsOffset` | 与报告 126/127 **一致** ✓ |
| **`0x160`** | `ViewAnglesOffset` | 3 个 float |
| **`0x248`** | `LinkEntityOffset` | `int32`，未链接 = **2047** |
| **`0x2F4`** | （内联）**手持武器数组** | **`std::array<uint32_t, 15>`** |
| **`0x3E4`** | `SelectedOffhandOffset` | ★ **选中的手雷** |
| **`0x3F8`** | `CurrentWeaponOffset` | ★ **仍在手里的枪** |
| **`0x400`** | `WeaponFlagsOffset` | ★ **`uint8`**,bit 2 = 副手激活 |
| **`0x404`** | `WeaponPositionFractionOffset` | `float`,0..1 |
| **`0x340`** | ★ **旧（3.3.3.3）的 `currentWeapon`** | **已作废** |

★★★ **⇒ 与报告 127 的 `NativeWeaponBindings.cpp` 对照：**
```
`NativeWeaponBindings.cpp`（**未移植**）：
  `EFlagsOffset 0x104` / `ViewAnglesOffset 0x160` / `LinkEntityOffset 0x248` /
  `CurrentWeaponOffset 0x3F8` / `WeaponPositionFractionOffset 0x404`
        ↓
★★★ 这 **5 个恰好是移植后正确的值** ⇒ 但该文件**声称"未移植"**
★★★ 而它**缺少** `0x3E4`（offhand）/ `0x400`（WeaponFlags）/ `0x2F4`（held array）
        ↓
★★★ ⇒ **记录为**待核对**：`NativeWeaponBindings.cpp` 的 5 个偏移看起来是**对的**,
   但它自己标注 "THE SAME UNPORTED BLOCK" ⇒ **可能注释是旧的,或者只部分移植**
```

### 1.4 ★★★ 两个常量

```cpp
constexpr std::uint8_t OffhandWeaponFlag = **0x02**;              // ★ bit 1（不是 bit 2）
constexpr std::size_t WeaponMovementDefinitionBytes = **3152**;   // ★ 最高直读 +3148
constexpr std::size_t NativeStateSlack = **512**;                 // ★ 测量用零尾
constexpr std::int32_t UnlinkedEntityNum = **2047**;
constexpr std::uint32_t TurretViewFlags = **0x0C00**;
```

★★★ **⇒ `OffhandWeaponFlag = 0x02`（bit 1）但注释说 "sets ps+0x400 **bit 2**"**
**⇒ 记录为**一处措辞不一致**（"bit 2" 可能是 1-based 数法）。**

---

## 二、★★★★★ **`ps+0x400` 是"主动副手选择器"**

### 2.1 ★★★★★ 完整注释（第 490–501 行，逐字）

```
// CODREF(1649370): **this is the active-offhand selector, not an unsupported
// alternate-overlay state**. **PM_OffHandPrepare 0x429640 enters weapon state 17 and
// sets ps+0x400 bit 2 at 0x429663.** Every retained view/weapon movement stage below
// tests the same bit and then **reads the selected offhand from ps+0x3E4 instead of the
// current gun at ps+0x3F8** (for example **0x4353F2..0x435405**).
//
// **Rejecting the bit discarded every command from a natural grenade preparation onward.**
// A **high-latency client visibly replayed a shot** as snapshots kept rolling it back to
// the last accepted command. **Pmove has already checked the selection against the
// held-weapon array**; keep the native definition boundary fail-closed before invoking
// consumers.
```

★★★★★ **⇒ 六个精确值：**
```
`PM_OffHandPrepare` = **`0x429640`**
进入 **weapon state 17**
在 **`0x429663`** 设置 **`ps+0x400` bit 2**
        ↓
★★★ 每个 view/weapon movement 阶段**测同一位**,然后
   **从 `ps+0x3E4` 读选中的副手**（而不是 `ps+0x3F8` 的当前枪）
★★★ 例：**`0x4353F2..0x435405`**
        ↓
★★★★★ ⇒ **拒绝该位 ⇒ 从"自然的扔雷准备"起丢弃每一条命令**
   ⇒ **高延迟客户端"看得见地重放了射击"**（快照不断回滚到最后一个被接受的命令）
```

### ★★★ 新的边界（第 502–519 行）

```cpp
if ((weaponFlags & OffhandWeaponFlag) != 0)
{
    const auto selectedOffhand = readNativeValue<std::uint32_t>(*input.playerState, SelectedOffhandOffset);
    if (!selectedOffhand || selectedOffhand > MaximumWeaponAssetIndex)
        return std::nullopt;                                     // ★ 上界校验
    const auto *const definitionSlot = module_ + WeaponDefinitionsRva + selectedOffhand * sizeof(void*);
    if (!readableNativeSpan(definitionSlot, sizeof(void*))) return std::nullopt;   // ★ 槽可读
    const auto *const definition = *(const std::uint8_t *const *)definitionSlot;
    if (!readableNativeSpan(definition, WeaponMovementDefinitionBytes)) return std::nullopt;  // ★ 定义体 3152 字节可读
}
```

★★★ **⇒ 三层 fail-closed：**
```
① `selectedOffhand` 非 0 且 ≤ 上界
② **定义槽**（8 字节指针）可读
③ **定义体 3152 字节**可读
```

---

## 三、★★★★★ **`0x3FF` 十位 vs 本 build 十一位**

### 3.1 ★★★★★ 完整注释（第 523–526 行，逐字）

```
// CODDIFF(1649370): **0x3FF is 3.3.3.3's TEN-BIT weapon index; this build writes
// eleven and its registry holds 1700**. The live gamestate reports
// **firstDynamicWeapon=1224**, so a **modular weapon -- the only kind a real class
// produces -- is ALWAYS above 1023** and this **rejected all of them**.
```

★★★★★ **⇒ 五个精确值：**
```
`0x3FF` = **1023** = **3.3.3.3 的十位武器索引**
本 build：**十一位**（`0x7FF` = 2047）
本 build 注册表：**1700** 项
        ↓
★★★ live gamestate 报 **`firstDynamicWeapon = 1224`**
★★★ ⇒ **模块化武器（真实 class 唯一产生的种类）恒 > 1023**
        ↓
★★★★★ ⇒ **旧的 `> 1023` 检查拒绝了所有模块化武器**
```

★★ **⇒ 与报告 098 的 `UserCmdWeaponIndexBits = 11`**完全一致** ✓**

### ★★★ 新检查（第 527–528 行）

```cpp
if (currentWeapon > EngineBindings::MaximumWeaponAssetIndex) return std::nullopt;
```
★★★ **⇒ 用 `MaximumWeaponAssetIndex`（应 ≥ 1700）而非硬编码 1023。**

---

## 四、★★★★★ **alt-fire 死在第二层**

### 4.1 ★★★★★ 完整注释（第 538–556 行，逐字）

```
// **AND THIS IS WHERE ALT-FIRE DIED, ONE LAYER PAST WHERE IT WAS FIXED.**
// **sect.190 gave the FIRE path SV_SetAltWeaponLookup** so a shot with an alt selected
// would not return Invalid and reject the whole command. **Weapon movement resolves the
// weapon too, out of the same frozen loadout, and nobody taught it.**
//
// Measured **2026-09-04** with the real button (**0x08000000**): **the switch fired
// sixteen times, 1224->1225 and 1235->1236**, and **`check-alt-fire.py` reported
// `switches happened and clientThink was rejected afterwards, stages: weapon_movement_rejected`**.
// **From the player's chair that is "the UI changed and the gun did not"** --
// **netfield 39 goes out, and every command after it is thrown away**.
//
// The alt **STILL must not be added to SvResolvedLoadout**: that struct sits **inside the
// client state the address-keyed native buffer is sized against**, and **growing a struct
// in that position is what broke the death animation twice (sect.184h)**.
// **A lookup costs nothing and moves nothing.**
```

★★★★★ **⇒ 七个精确值：**
```
① **sect.190** 修好了 **FIRE 路径**（`SV_SetAltWeaponLookup`）
② 但 **weapon movement 也解析武器**（从同一份冻结 loadout）⇒ **没人教它**
        ↓
★★★ 实测（**2026-09-04**,真按键 **`0x08000000`**）：
   切换**触发 16 次**：**`1224→1225`** 和 **`1235→1236`**
   `check-alt-fire.py` 报：**`stages: weapon_movement_rejected`**
        ↓
★★★ 玩家视角：**"the UI changed and the gun did not"**
★★★ **netfield 39 发出去了,而它之后的每条命令都被丢弃**
        ↓
★★★ **alt 仍不能加进 `SvResolvedLoadout`**：
   那个结构体在**按地址加密的原生缓冲**里,**在这里增长结构体曾两次弄坏死亡动画**（**sect.184h**）
```

### ★★★★★ UAV 的特殊分支（第 557–575 行）

```cpp
if (!SV_LookupAltWeapon(currentWeapon, altWeapon))
{
    // CODREF(OLfinal live): key 4 selects the granted UAV via retained PM_Weapon.
    // It is held inventory, not a class gun or an alt.
    const auto uav = resolveUavWeapon();
    const auto held = readNativeValue<std::array<std::uint32_t, 15>>(*input.playerState, **0x2F4**);
    if (!uav || uav->weaponAssetIndex != currentWeapon ||
        std::ranges::find(held, currentWeapon) == held.end())
        return std::nullopt;
    altWeapon.weaponAssetIndex = uav->weaponAssetIndex;
    ...
}
```

★★★★★ **⇒ 三个精确事实：**
```
**key 4** 通过保留的 `PM_Weapon` 选择**已授予的 UAV**
UAV 是**手持库存**,不是 class 枪或 alt
手持武器数组在 **`ps+0x2F4`**（**15 个 `uint32`** = 60 字节）
        ↓
★★★ ⇒ 三重校验：`uav` 存在 + `uav->index == currentWeapon` + **`currentWeapon` 在 held 数组里**
```

### ★★★ 主手/副手的分流（第 529–577 行）

```
`currentWeapon == 0`          ⇒ 不解析（引擎的 null 武器）
`currentWeapon != 0`：
   `SV_FindResolvedWeapon` 命中 ⇒ 用它
   未命中 ⇒ ① `SV_LookupAltWeapon` 命中 ⇒ 用 alt
           ② 否则 ⇒ UAV 三重校验 ⇒ 用 UAV
```

---

## 五、★★★★★ **`lastIdleFactor` / `weaponIdleTime` 的冻结相位**

### 5.1 ★★★★★ 完整注释（第 676–698 行，逐字）

```
// OLMOD(**scope-idle-quantifier 2026-10-09**): publish the idle-stage inputs
// and outputs for one diagnostic line. **DIAGNOSTIC ONLY** -- read here, consumed only
// by a log; **the transaction verdict above is untouched**.
//
// The question this answers: **the native idle stage (sub_4355D0) reads AND writes
// `lastIdleFactor` and dereferences `weaponIdleTime` as a pointer**.
// **SV_SaveWeaponMovementState (sv_weapon_movement_mp.cpp:151-159) stores
// lastIdleFactor back but NEVER stores weaponIdleTime**, so **if the native stage also
// ADVANCES it, the phase would restart from a frozen counter on every frame**.
// **A per-frame reset reads as a constant-amplitude twitch that never grows** -- which is
// **what the user reports**.
```

★★★★★ **⇒ 一个完整的症状链：**
```
原生 idle 阶段 **`sub_4355D0`**：
  **读并写 `lastIdleFactor`**
  **把 `weaponIdleTime` 当指针解引用**
        ↓
★★★ `SV_SaveWeaponMovementState`（**`sv_weapon_movement_mp.cpp:151-159`**）
   **存回 `lastIdleFactor`,但从**不**存 `weaponIdleTime`**
        ↓
★★★ ⇒ 若原生阶段也**推进** `weaponIdleTime`
   ⇒ **相位每帧从冻结的计数器重启**
        ↓
★★★★★ ⇒ **"每帧重置读起来就是一个永不增长、恒定振幅的抖动"**
   ⇒ **"which is what the user reports"**
```

### ★★★★★ **谁在推进它**（第 692–698 行，逐字）

```
// OLMOD(scope-idle-quantifier): **WHO ADVANCES IT**. `sub_4355D0` **only READS
// *weaponIdleTime (0x4356F8 `fild dword ptr [edx]`, no store anywhere in the function)**,
// yet **the counter advances 1.45-6.9x real time** and **the phase constant is exactly
// 0.001** -- so **the sway really does run that much fast**.
// **One of the other eight bound stages must be the writer.** Sampling it after each
// stage **names that stage in a single run** instead of guessing from overlapping
// disassembly windows.
```

★★★★★ **⇒ 五个精确值：**
```
`sub_4355D0` **只读** `*weaponIdleTime`（**`0x4356F8`** 的 `fild dword ptr [edx]`,**函数内无任何 store**）
        ↓
★★★ 但计数器**以 1.45–6.9 倍实时速度推进**
★★★ 相位常数恰好是 **`0.001`**
        ↓
★★★ ⇒ **其他 8 个绑定阶段之一必是写入者**
★★★ ⇒ 在每个阶段之后**采样**,一次运行就能**点名那个阶段**
```

### ★★★★★ **9 个 stage sample 的完整清单**

| slot | 阶段 | 函数 |
|---|---|---|
| **0** | `view_damage_kick` | `0x004318B0` |
| **1** | `view_idle_angles` | （`__cdecl` 直接调用） |
| **2** | `view_bob_angles` | `0x00431C40` |
| **3** | `view_ads_bob` | `0x00431DE0` |
| **4** | `weapon_base` | （`__cdecl(int32, state)`） |
| **5** | `weapon_sway` | （`__cdecl(state)`） |
| **6** | `weapon_recoil` | `0x004310F0` |
| **7** | `weapon_bob` | `0x004312F0` |
| **8** | `weapon_set_angles` | `0x00434F90` |

★★★ **⇒ 9 个 slot 与注释"the other **eight** bound stages"**一致**（slot 0 是 view 的第一个）。**

### ★★★ `SV_SetCurrentNativeStage` 的四个阶段名

```cpp
"view_movement" / "weapon_movement" / "ads_composition" / "none"
```

---

## 六、★★★★★ **`NativeStateSlack = 512` 的测量法**

### 6.1 ★★★★★ 完整注释（第 283–299 行，逐字）

```
// **MEASURE WHAT THE ENGINE ACTUALLY WRITES, RATHER THAN TRUST A CARRIED SIZE.**
//
// `sv_weapon_movement_mp.hpp` is **byte-identical to ..\ol-mod-ffa's copy**, so **both
// structs handed to these native stages are 3.3.3.3's layout** and **NOTHING has
// established their footprint on 1649370**. This project has **already been bitten twice
// by exactly that** -- **playerState_s 0x3564 -> 0x3BBC** and **characterInfo 0x3B8 -> 0x450**,
// both cases of **handing the engine a buffer shorter than it believes it owns** -- and
// **the first cycle that actually reached these calls killed the dedicated with a wild
// write (0xC0000005 op=1 target=0x001B0000)**.
//
// **A guessed size would be a fourth guess.** Instead give the native stage a buffer with
// a **large zero tail**, snapshot it, and **report the highest byte that changed**.
// **The tail is ZERO rather than a fill pattern on purpose**: a native read past the
// struct then sees a **null pointer or a 0.0f, not 0xCDCDCDCD**.
// The slack also means **an overrun lands in slack instead of on a return address**, so
// **the measurement can be taken at all**.
```

★★★★★ **⇒ 六个精确值：**
```
`sv_weapon_movement_mp.hpp` **与 `..\ol-mod-ffa` 的副本逐字节相同**
⇒ **两个结构体都是 3.3.3.3 的布局**,**本 build 上从未确定过尺寸**
        ↓
★★★ 已两次被同样问题咬：
   **`playerState_s` `0x3564` → `0x3BBC`**
   **`characterInfo` `0x3B8` → `0x450`**
★★★ 首次到达这些调用的循环**用野写杀死了专服**（**`0xC0000005 op=1 target=0x001B0000`**）
        ↓
★★★ 解法：**大零尾 + 快照 + 报告最高变化字节**
★★★ **零尾而非填充图案**：越界读看到 **null 或 `0.0f`**,不是 **`0xCDCDCDCD`**
★★★ **slack 也意味着越界落在 slack 里而不是返回地址上** ⇒ **测量才可能进行**
```

★★★ **⇒ 与报告 126 的 `playerState_s 0x3BBC`**完全一致** ✓**
**⇒ 新增 `characterInfo 0x3B8 → 0x450`。**

### ★★★★★ **"HIGH-WATER OF ZERO IS STILL A HIGH-WATER"**（第 321–325 行，逐字）

```
// **A HIGH-WATER OF ZERO IS STILL A HIGH-WATER.** `!seen` made a stage that **writes
// nothing** -- **view_movement, which really does write through 0** -- **report on EVERY
// frame: 6452 lines in a 110-second run**, one of **the three things that pushed tick
// time to 8ms**. Remember **that the stage has been reported at all**, not just how far
// it wrote.
```

★★★★★ **⇒ 四个精确值：**
```
`view_movement` **真的写到 0 字节**
        ↓
★★★ 用 `!seen` 判断 ⇒ **每帧都报**
★★★ **110 秒运行 6452 行**
★★★ 这是**把 tick time 推到 8ms 的三件事之一**
        ↓
★★★ 修复：**记住"是否已报过"（`optional<size_t>`）,而不只是"写了多远"**
```

### ★★★ 报告格式（第 332–337 行）

```
"native state write <stage> declared=<N> wroteThrough=<M>[ *** PAST THE DECLARED END ***][ (stage faulted)]"
```

---

## 七、★★★★★ **`callSetWeaponAngles` 的两个寄存器**互换

### 7.1 ★★★★★ 完整注释（第 193–205 行，逐字）

```
// CODREF(g_build_weapon_state): **3.3.3.3's 0x00431460 receives the output angles in
// EAX and weaponState_t in ECX**.
//
// CODDIFF(1649370): **both moved, and they SWAPPED sides**. out.exe's **sub_434F90** opens
//     **434f99  mov ebx, [ebp+arg_0]**   <- output angles, off the **STACK**
//     **434f9c  fst dword ptr [ebx]**    <- writes angles[0..2]
//     **434fa6  mov edi, eax**           <- weaponState_t, in **EAX**
// so **the angles are a stack argument and the state is the register one**.
// **Passing them the 3.3.3.3 way put the state in EAX where the callee expects nothing,
// left ECX unread, and pushed no stack argument at all** - so the callee **wrote three
// floats through whatever happened to sit at [ebp+arg_0]**.
```

★★★★★ **⇒ 六个精确值：**
```
3.3.3.3：`0x00431460` ⇒ **EAX = 输出角度**、**ECX = weaponState_t**
        ↓
★★★ 1649370：`sub_434F90`
   `434f99  mov ebx, [ebp+arg_0]`  ← 角度在**栈**
   `434f9c  fst dword ptr [ebx]`   ← 写 angles[0..2]
   `434fa6  mov edi, eax`          ← weaponState 在 **EAX**
        ↓
★★★ ⇒ **两个都移动了,而且互换了位置**
        ↓
★★★★★ ⇒ 用旧方式：state 进 EAX（callee 不期待）、ECX 未读、**栈上没参数**
   ⇒ callee **通过 `[ebp+arg_0]` 恰好在那里的东西写三个 float**（**野写**）
```

### ★★★ 正确的调用（第 206–212 行）

```cpp
__asm
{
    push angles          // ★ 栈参数
    mov eax, state       // ★ EAX = state
    call function
    add esp, 4
}
```

---

## 八、★★★★ **另外 6 个原生调用的 ABI**

| 函数 | RVA | ABI |
|---|---|---|
| `callViewDamageKick` | **`0x004318B0`** | ★ **ESI = viewState**、**EDI = angles** |
| `callViewBobAngles` | **`0x00431C40`** | ★ **ECX = viewState**、**栈 = angles** |
| `callViewAdsBob` | **`0x00431DE0`** | ★ **EDI = angles**、**栈 = viewState** |
| `callWeaponRecoil` | **`0x004310F0`** | ★ **EDX = weaponState** |
| `callWeaponBob` | **`0x004312F0`** | ★ **EDI = weaponState** |
| `callAngleVectors` | **`sub_767890`** | ★ **4 个栈参数**、`__cdecl`、3 个独立目标 |
| `callMatrixMultiply` | **`0x00629730`** | ★ **栈 = weaponAxis**、**EAX = viewAxis**、**EDX = output** |
| `callAxisToAngles` | **`0x0062AE50`** | ★ **EAX = angles**、**ECX = axis** |

★★★ **⇒ 8 个调用,每个的寄存器约定都**不同**：**
```
ESI+EDI / ECX+栈 / EDI+栈 / EDX / EDI / 4栈 / 栈+EAX+EDX / EAX+ECX
        ↓
★★★ ⇒ **没有一个统一的约定** ⇒ 每个都必须单独核对
```

### ★★★ 两个链的完整顺序

```
**View movement**（`CG_OffsetFirstPersonView 0x0051D3B0`）：
  damage_kick → idle → bob → ads_bob
        ↓
**Weapon movement**（`CG_AddViewWeapon 0x0055C8A0`）：
  Base → Sway → Recoil → Bob → SetAngles
  （**SetOrigin 是渲染输出阶段,不需要**）
        ↓
**ADS composition**（客户端生产者 `0x00559D10`）：
  AngleVectors(weapon) → AngleVectors(view) → MatrixMultiply → AxisToAngles
```

### ★★★ `runServerWeaponMovement` 的六个前置拒绝（第 468–475 行）

```cpp
if (!valid() || !input.playerState || !resolvedLoadout ||
    input.frameTime <= 0.0f ||
    input.shellShockStart != 0 || input.shellShockDuration != 0 ||
    input.shellShockFadeTime != 3000 ||           // ★ 精确值 3000
    gameThreadId_ != GetCurrentThreadId())
    return std::nullopt;
```

★★★ **⇒ `shellShockFadeTime` 必须是 **`3000`**（3 秒）,其余两个必须 **0**。**

### ★★★ ADS 的四个条件（第 661–662 行）

```cpp
if (weapon && weapon->aimDownSight && !weapon->hasOverlayReticle &&
    weaponPositionFraction != 0.0f && !invokeAdsComposition(...))
    return std::nullopt;
```
★★★ **⇒ 四个条件：`aimDownSight` + **无** overlay reticle + `weaponPositionFraction != 0`。**

---

## 九、★★★★ **`.bak-20261009-scopeidle`（29,791 B）**

### 9.1 与主文件的差异

```powershell
主文件      : 31,427 B / 709 行
.bak 文件   : 29,791 B
差异        : **-1,636 B**
```

★★★ **⇒ `.bak` 是**加诊断之前**的版本：**
```
主文件新增（约 40 行）：
  第 676–701 行  OLMOD(scope-idle-quantifier 2026-10-09) 诊断块
  `output.idleDiagnostics.*` 的 6 个字段
  `stageSamples` 的采样逻辑
```

★★★ **⇒ 结论：`.bak` 是**同一次提交的前一版**（`scopeidle` = 作用域闲置量化器）。**
**⇒ 与用户此前删除的**包根 6 个 `.bak`** 不同：这一个是**交付包内 `source\` 下的历史备份**，
属于 MANIFEST 记录范围。⇒ **记录为"交付包内唯一 `.bak`,内容 = 主文件减去诊断块"。**

---

## 十、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **"一个结构体两个文件"** | `playerState_s` 在 **2 个文件**；`sv_native_playerstate_mp.cpp` 已搬,本文件**一个都没搬** |
| 2 | ★★★★★ **旧偏移的后果** | `currentWeapon` 从 **`0x340`** 读（本 build 上落在**手持武器数组**里）⇒ 越界 ⇒ **`weapon_movement_rejected` 拒绝每条命令** |
| 3 | ★★★★★ 症状 | **"Nothing moved, ever."** |
| 4 | ★★★ 审计工具 | **`Tools/olfinal/audit-native-offsets.py`** 对 **提取的 playerstate netfield 表** |
| 5 | ★★★★ 双向验证 | `0x348`（A-only）**+ `0xB8`** = **`0x400`**（C-only）；`WeaponFlags` 由 **`0x344`/`0x34C`** 夹住 |
| 6 | ★★★★★ **9 个偏移** | `0x104` eFlags / `0x160` viewAngles / `0x248` linkEntity / **`0x2F4` held[15]** / **`0x3E4` offhand** / **`0x3F8` currentWeapon** / **`0x400` weaponFlags** / `0x404` posFraction / **`0x340` 旧值（作废）** |
| 7 | ★★ 常量 | `OffhandWeaponFlag = **0x02**` / `WeaponMovementDefinitionBytes = **3152**`（最高直读 **+3148**）/ `NativeStateSlack = **512**` / `UnlinkedEntityNum = **2047**` / `TurretViewFlags = **0x0C00**` |
| 8 | ★★ 一处措辞不一致 | 注释说 "bit 2" 而常量是 **`0x02`**（bit 1）⇒ 可能是 1-based 数法 |
| 9 | ★★★★★ **`ps+0x400` 语义** | **主动副手选择器**；`PM_OffHandPrepare **0x429640**` 进入 **weapon state 17**,在 **`0x429663`** 设该位 |
| 10 | ★★★ 副手分支 | 测同一位 ⇒ 从 **`ps+0x3E4`** 读副手（而非 `0x3F8`）；例 **`0x4353F2..0x435405`** |
| 11 | ★★★★★ 旧行为的后果 | 拒绝该位 ⇒ **从"自然扔雷准备"起丢弃每条命令** ⇒ 高延迟客户端**可见地重放射击** |
| 12 | ★★★ 三层 fail-closed | `selectedOffhand` 上界 / **定义槽 8 字节可读** / **定义体 3152 字节可读** |
| 13 | ★★★★★ **`0x3FF` 十位 vs 十一位** | 3.3.3.3 **10 位**（`0x3FF`=1023）；本 build **11 位**,注册表 **1700**；live `firstDynamicWeapon = **1224**` |
| 14 | ★★★★★ 后果 | 模块化武器**恒 > 1023** ⇒ 旧的 `> 1023` 检查**拒绝所有模块化武器** |
| 15 | ★★★★★ **alt-fire 死在第二层** | **sect.190** 修了 FIRE 路径（`SV_SetAltWeaponLookup`）,**weapon movement 没人教** |
| 16 | ★★★★ 实测 | **2026-09-04**,按键 **`0x08000000`**，切换 **16 次**：**`1224→1225`** / **`1235→1236`**；`check-alt-fire.py` 报 **`stages: weapon_movement_rejected`** |
| 17 | ★★★ 玩家视角 | **"the UI changed and the gun did not"**；**netfield 39 发出去了,之后每条命令都被丢弃** |
| 18 | ★★★ 为什么不能加进 loadout | `SvResolvedLoadout` 在**按地址加密的原生缓冲**里；**在这里增长结构体曾两次弄坏死亡动画（sect.184h）** |
| 19 | ★★★★★ **UAV 分支** | **key 4**；UAV 是**手持库存**；held 数组在 **`ps+0x2F4`**（**15 个 u32**）；三重校验 |
| 20 | ★★★★★ **idle 相位冻结** | 原生 **`sub_4355D0`** 读并写 `lastIdleFactor`；`SV_SaveWeaponMovementState`（**`sv_weapon_movement_mp.cpp:151-159`**）**存回 lastIdleFactor 但从不存 weaponIdleTime** |
| 21 | ★★★★★ 症状 | 相位**每帧从冻结计数器重启** ⇒ **"永不增长、恒定振幅的抖动"** = **用户报告的现象** |
| 22 | ★★★★★ **谁在推进** | `sub_4355D0` **只读**（**`0x4356F8`** `fild dword ptr [edx]`,**无 store**）但计数器**以 1.45–6.9 倍实时推进**；相位常数 **`0.001`** |
| 23 | ★★★ 结论 | **其他 8 个绑定阶段之一是写入者** ⇒ 逐阶段采样**一次运行点名** |
| 24 | ★★★★★ **9 个 stage sample** | 0 damage_kick / 1 idle / 2 bob_angles / 3 ads_bob / 4 base / 5 sway / 6 recoil / 7 bob / 8 set_angles |
| 25 | ★★★ 四个阶段名 | `view_movement` / `weapon_movement` / `ads_composition` / `none` |
| 26 | ★★★★★ **`NativeStateSlack = 512`** | 零尾 + 快照 + 最高变化字节；**零尾使越界读看到 null/`0.0f` 而非 `0xCDCDCDCD`**；**slack 让越界落在 slack 而非返回地址** |
| 27 | ★★★★★ 两次尺寸错误 | **`playerState_s` `0x3564` → `0x3BBC`**；**`characterInfo` `0x3B8` → `0x450`** |
| 28 | ★★★★★ 首次到达的后果 | **野写杀死专服**：**`0xC0000005 op=1 target=0x001B0000`** |
| 29 | ★★★★★ **HIGH-WATER OF ZERO** | `view_movement` **真的写到 0**；用 `!seen` ⇒ **每帧都报** ⇒ **110 秒 6452 行** ⇒ **tick time 推到 8ms 的三件事之一** |
| 30 | ★★★ 报告格式 | `native state write <stage> declared=<N> wroteThrough=<M>[ *** PAST THE DECLARED END ***][ (stage faulted)]` |
| 31 | ★★★★★ **`callSetWeaponAngles` 互换** | 3.3.3.3：**EAX = 角度 / ECX = state**；1649370 `sub_434F90`：**栈 = 角度 / EAX = state** |
| 32 | ★★★★★ 旧方式的后果 | state 进 EAX（不期待）、ECX 未读、**栈无参数** ⇒ callee **通过 `[ebp+arg_0]` 恰好在那里的东西写三个 float** |
| 33 | ★★★★★ 8 个 ABI 各不相同 | `0x4318B0` **ESI+EDI** / `0x431C40` **ECX+栈** / `0x431DE0` **EDI+栈** / `0x4310F0` **EDX** / `0x4312F0` **EDI** / `sub_767890` **4栈** / `0x629730` **栈+EAX+EDX** / `0x62AE50` **EAX+ECX** |
| 34 | ★★★ 三条链 | View：**damage_kick → idle → bob → ads_bob**（`CG_OffsetFirstPersonView 0x51D3B0`）；Weapon：**Base → Sway → Recoil → Bob → SetAngles**（`CG_AddViewWeapon 0x55C8A0`）；ADS：**AngleVectors×2 → MatrixMultiply → AxisToAngles** |
| 35 | ★★★ 六个前置拒绝 | `!valid` / `!playerState` / `!resolvedLoadout` / `frameTime <= 0` / **`shellShockStart/Duration == 0` 且 `FadeTime == 3000`** / 非游戏线程 |
| 36 | ★★★ ADS 四条件 | `aimDownSight` + **无** overlay reticle + `weaponPositionFraction != 0` |
| 37 | ★★★ `.bak` 差异 | 主文件 **31,427 B** vs `.bak` **29,791 B**（**-1,636 B**）= **诊断块之前**的版本 |

---

## 十一、结论

### 1. ★★★★★ **"一个结构体、两个文件、只更新一个"是本项目反复付代价的失败模式**

★ **⇒ 症状是**总体的**：`currentWeapon` 从作废的 `0x340` 读 ⇒ **每条命令被拒** ⇒ **"Nothing moved, ever."**

### 2. ★★★★ **`audit-native-offsets.py` 用 `+0xB8` 双向验证了重定位**（`0x348` → `0x400`）

### 3. ★★★★★ **`ps+0x400` bit 是"主动副手选择器"**,不是"不支持的 overlay 状态"

★ **⇒ 拒绝它 ⇒ 从**自然的扔雷准备**起丢弃每条命令。**

### 4. ★★★★★ **`0x3FF`（十位）在本 build 上是**十一位**,注册表 1700**

★ **⇒ 模块化武器恒 > 1023 ⇒ 旧检查拒绝所有模块化武器。**

### 5. ★★★★★ **alt-fire 死在"第二层"**（FIRE 路径修好了,weapon movement 没修）

★ **⇒ 且 alt **不能**加进 `SvResolvedLoadout`（在那里增长结构体曾两次弄坏死亡动画）。**

### 6. ★★★★★ **`weaponIdleTime` 从未被存回 ⇒ 相位每帧冻结重启**（= 用户报告的抖动）

★ **⇒ `sub_4355D0` 只读不写,但计数器以 1.45–6.9 倍推进 ⇒ 其他 8 个阶段之一是写入者。**

### 7. ★★★★★ **`NativeStateSlack = 512` 的零尾测量法是正确做法**

★ **⇒ 且 `HIGH-WATER OF ZERO` 的教训（110 秒 6452 行、tick 8ms）值得记住。**

### 8. ★★★★★ **8 个原生调用的 ABI **没有一个相同**（ESI+EDI / ECX+栈 / EDI+栈 / EDX / EDI / 4栈 / 栈+EAX+EDX / EAX+ECX）

### 9. ★★ **`NativeWeaponBindings.cpp` 的 5 个偏移看起来正确,但自己标注"未移植"** ⇒ 待核对

---

## 十二、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）—— 最大两块
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000）
4. `ClientProcessPatches.cpp`（82,545）
5. `DedicatedProcessPatches.cpp`（39,058）
6. `ClientRenderFrameHook.cpp`（32,154）
7. `ClientCommandTrace.cpp`（27,720）
8. 然后 `server_mp` 154 文件（12,604,630 B）
