# 学习报告 126（重开）— `game_server` 根：钩子层与小文件（15 文件）

**学习范围**：`FrameHook.hpp/.cpp`（12/74）+ `DisconnectWitness.hpp`（18）+ `ClientBatteryLookup.hpp`（21）+ `ClientNoclipHotkey.hpp/.cpp`（17/262）+ `GameStateConfiguration.hpp`（151）+ `DedicatedSessionConsumption.hpp`（109）+ `SessionAssetRegistry.hpp`（168）+ `codol_bot_classes.hpp`（112）+ `NativeEntityStateBindings.cpp`（198）+ `DedicatedProcessPatches.hpp`（64）+ `ClientAnimtreeHook.hpp/.cpp`（48/907）+ `PlayerDataDef.hpp/.cpp`（195/333）+ `ClientCommandTrace.hpp`（80）
**性质**：全实测（**15 文件逐行读完**）
**★★★★★ 本报告收录八个重大发现**：①**`StructuredDataDef` 的完整记录布局（14 个头部字段 + 3 种记录）** ②**`playerdata.def` 按名解析替代 8 个手测序号** ③**`playerState` 从 ECX 移到栈（CODDIFF 1649370）** ④**`.tp3` 未解包时 6 个 RVA 的实测密文/明文对照** ⑤**animtree 519 vs 123 条目的三层钩子** ⑥**`com_maxfps` 上限 200 与 `Sleep(1)` 过冲** ⑦**`DedicatedProcessPatches` 的 12 种结果** ⑧**`botclasstable.csv` 的 9 类 + 10 个外观部件**

---

## 一、★★★★★ **`PlayerDataDef` —— `StructuredDataDef` 的完整记录布局**

### 1.1 ★★★★★ 头部 14 个字段（`Layout`，逐字）

```cpp
static constexpr std::size_t HeaderBytes = **0x3C**;   // 60 字节

Version             = 0x00;   FormatChecksum    = 0x04;
EnumCount           = 0x08;   Enums             = 0x0C;
StructCount         = 0x10;   Structs           = 0x14;
IndexedArrayCount   = 0x18;   IndexedArrays     = 0x1C;
EnumedArrayCount    = 0x20;   EnumedArrays      = 0x24;
RootCategory        = 0x28;   RootType          = 0x2C;
DocumentSize        = 0x30;   OffsetTableCount  = 0x34;
OffsetTable         = 0x38;
```

★★★ **⇒ 14 个字段,每 4 字节一对（count + pointer），最后 3 个是单值。**
**⇒ `HeaderBytes = 0x3C` 恰好覆盖到 `0x38 + 4`。**

### 1.2 ★★★★★ **三种记录的精确布局**

| 记录 | 字节 | 字段 |
|---|---|---|
| **StructRecord** | ★ **20** | `{propertyCount@0, properties*@4, sizeBytes@8, bitOffset@12, indexCount@16}` |
| **PropertyRecord** | ★ **24** | `{name*@0, category@4, typeIndex@8, offsetIndex@12, 0@16, 0@20}` |
| **IndexedArrayRecord** | ★ **16** | `{arraySize@0, elementCategory@4, elementTypeIndex@8, elementSizeBytes@12}` |
| **EnumedArrayRecord** | ★ **16** | （未使用） |
| **EnumRecord** | ★ **12** | （未使用） |

★★★ **⇒ 与报告 093 的 `StructuredDataDef` 记录**完全对应** ✓**

### 1.3 ★★★★★ **6 个 Category 值（逐字）**

```cpp
CategoryInt          = **0**,
CategoryByte         = **1**,
CategoryBool         = **2**,   // ★ stores a **BIT offset**, not a byte one
CategoryString       = **3**,   // ★ typeIndex is the **maximum length**
CategoryStruct       = **5**,
CategoryIndexedArray = **6**,
```

★★★★★ **⇒ 六个值,注意 **缺 4**（`CategoryFloat` 未声明？）以及两个**特殊语义**：**
```
`CategoryBool = 2`   ⇒ **存的是 BIT 偏移**,不是字节偏移
`CategoryString = 3` ⇒ **`typeIndex` 是最大长度**
```

★ **⇒ 第 4 号（`4`）在本代码里**未命名** ⇒ 记录为**待核对项**（可能是 `CategoryFloat`）。**

### 1.4 ★★★★★ **`sub_50F410` 的最后一跳（逐字）**

```cpp
byteOffset = *(_DWORD *)(*(_DWORD *)(def + **0x38**) + 4 * index)
```

★★★ **⇒ `def + 0x38` = `OffsetTable` 指针 ⇒ `+ 4*index` ⇒ 字节偏移。**

### 1.5 ★★★★★ **为什么按名解析（逐字，最重要）**

```
EngineBindings 原先携带 **8 个手测序号**：
  characterClasses @ **605**, stride **14**
  weaponClasses    @ **1607**, stride **37**
  slots            @ child ordinal **5**
  primaryBase      @ **22**
  secondaryBase    @ **29**
        ↓
★★★ "every one of them is a **PER-BUILD constant**。
   **Six of the eight differ on 3.3.3.3**（**576/10/1** 和 **1154/36**）
   ⇒ 同样的代码读同样的名字,在 3.3.3.3 上会读到**垃圾**。"
        ↓
★★★★★ 附件的序号更糟：**不是测出来的,是推导出来的**
   `weaponOrdinal - AttachmentCount`
   ⇒ 源码注释自己称之为 "**numerology**"
   ⇒ **已经错过一次**（section **187g/187m**）
        ↓
★★★ def **自己命名了**它们：`primaryAttach @ 16`、`secondaryAttach @ 23`（**六宽**）
   ⇒ "asking it is **both shorter and correct by construction**"
```

### ★★★★★ 8 个手测序号 vs 3.3.3.3 的完整对照

| 项 | 本 build | **3.3.3.3** |
|---|---|---|
| `characterClasses` | **605** / stride **14** | ★ **576** / stride **10** |
| `weaponClasses` | **1607** / stride **37** | ★ **1154** / stride **36** |
| `slots` | child ordinal **5** | ★ **1** |
| `primaryBase` | **22** | — |
| `secondaryBase` | **29** | — |
| `primaryAttach` | **16**（六宽） | — |
| `secondaryAttach` | **23**（六宽） | — |

★★★ **⇒ 四个精确数字：`605/14` → `576/10`；`1607/37` → `1154/36`；`slots` `5` → `1`。**

### 1.6 ★★★★★ **内存形态 = 磁盘形态 + 指针修正（逐字）**

```
"A zone loads as **one contiguous image** and the loader replaces each
 **0xFFFFFFFF** 'the data follows here' placeholder with **the address of that inline data**."
        ↓
★★★ 实测：def 的头部 `+0x38` 在**提取文件里是 `0xFFFFFFFF`**,
   在**运行时是偏移表指针**
        ↓
★★★ ⇒ "It is also what lets the tests below walk an **extracted def**:
   link the placeholders and the production code runs unchanged over
   the real schema of **two different builds**."
```

★★ **⇒ `pointerAt` 拒绝 `0` 和 `0xFFFFFFFF`（第 90 行）。**

### 1.7 ★★★ 七个防御性常量

| 常量 | 值 | 理由 |
|---|---|---|
| **`MaxTypeDepth`** | ★ **8** | 类型图有环 ⇒ 否则无限递归 |
| **`MaxNameLength`** | ★ **128** | 更长的不是名字,是野指针 |
| `static_assert(sizeof(void*) == sizeof(uint32_t))` | — | ★ **32 位镜像**,64 位会截断 |

### 1.8 ★★★★★ `resolve()` 的路径语法（第 216–325 行）

```
"characterClasses"                     ⇒ 数组元素 0 + 报告 count/stride
"characterClasses[3].slots"            ⇒ 逐层下钻
"weaponClasses[7].primaryBase"         ⇒ 逐层下钻
```

★★★ **⇒ 三层校验：**
```
① `property->offsetIndex >= offsetTableCount_ || index > offsetTableCount_ - offsetIndex` ⇒ 拒
② `subscript >= array->size` ⇒ 拒
③ `moved > offsetTableCount_ || index > offsetTableCount_ - moved` ⇒ 拒
```

★★★ **⇒ 都是**减法形式**（`index > N - delta`）⇒ **防无符号溢出**。**

### ★★★ `nameEquals` 的 NUL 校验（第 97–110 行，逐字）

```cpp
// The NUL is part of the comparison: without it "primaryBase" would match
// "primaryBaseSomething", and this def **does carry names that share a prefix**
// (**primaryAttach / primaryBase**, **lethal / lethalDoubleAmmo**).
return std::memcmp(name, want.data(), want.size()) == 0 &&
    name[want.size()] == '\0';
```

★★ **⇒ 两组真实的前缀冲突：`primaryAttach`/`primaryBase`、`lethal`/`lethalDoubleAmmo`。**

### ★★★ `elementSpan` 的乘积上界（第 196–200 行）

```cpp
const auto total = static_cast<std::uint64_t>(array->size) * *inner;
if (total > offsetTableCount_) return std::nullopt;   // ★ 不能超过偏移表
```

---

## 二、★★★★★ **`NativeEntityStateBindings.cpp` —— `playerState` 从 ECX 移到栈**

### 2.1 ★★★★★ CODDIFF 原文（第 19–33 行，逐字）

```cpp
// CODREF(client_think_real): **3.3.3.3**'s BG_PlayerStateToEntityState
// **0x00413AB0** receives playerState_s in **ECX** and entityState_s in **EAX**.
//
// CODDIFF(1649370): **the playerState moved OFF the registers**. out.exe's
// sub_4116F0 opens
//     4116f4  mov ebx, [ebp+arg_0]    <- playerState_s, off the **STACK**
//     4116f9  mov edi, eax            <- entityState_s, still in **EAX**
//     411703  mov eax, [ebx+104h]     <- reads through ebx, the input
//     41170c  mov [edi+8], eax        <- writes through edi, the output
// and its frame declares **exactly one argument slot**. EAX was right; the
// playerState was going into ECX, **which nothing reads**, while the stack
// slot the callee **does** read got **whatever was already there**.
```

★★★★★ **⇒ 五个精确事实：**
```
3.3.3.3：`playerState` 在 **ECX**、`entityState` 在 **EAX**
1649370：`playerState` 在 **[ebp+arg_0]**（**栈**）、`entityState` 仍在 **EAX**
        ↓
★★★ 四条指令：
   `4116f4  mov ebx, [ebp+arg_0]`    ← playerState（栈）
   `4116f9  mov edi, eax`            ← entityState（EAX）
   `411703  mov eax, [ebx+104h]`     ← 经 ebx 读
   `41170c  mov [edi+8], eax`        ← 经 edi 写
        ↓
★★★★★ ⇒ 老实现把 playerState 放进 **ECX**（**没人读**）,
   而 callee **真正读的栈槽**得到的是 **"whatever was already there"**
```

### ★★★ 正确的调用序列（第 42–49 行）

```cpp
__asm
{
    mov eax, entityStateBytes     // ★ EAX = entityState
    push playerStateBytes         // ★ 栈 = playerState
    mov edx, function
    call edx
    add esp, 4                    // ★ cdecl,1 个参数
}
```

### ★★★★★ 事务化语义（第 65–71 行，逐字）

```cpp
// OLMOD(playerstate-entitystate-transaction): **the native function can
// mutate both inputs**, so source publication waits until conversion,
// animation-context restoration and typed projection **all succeed**.
```

★★★ **⇒ 三步必须全成功才提交：转换 / 动画上下文恢复 / 类型化投影。**

### ★★★★★ **"RE-KEY THE COPY" —— 函数指针按地址加密**（第 127–137 行，逐字）

```cpp
// RE-KEY THE COPY BEFORE THE ENGINE DECODES A POINTER OUT OF IT.
// `auto playerCandidate = playerState;` above **relocated the buffer**, and CODOL's
// **function pointers are keyed on the slot's own ADDRESS** -- so without this the
// converter's `xor ecx, ds:0x00E60B78 / call ecx` at **0x0041144C** jumps to a
// **different wild address on every command**.
// Measured: **0x00198A90, 0x00DAF2AC, 0x0041144C**, plus privileged-instruction
// faults from executing what it hit.
```

★★★★★ **⇒ 五个精确值：**
```
★★★ 加密指令：`xor ecx, ds:0x00E60B78` / `call ecx` @ **0x0041144C**
★★★ 密钥位置：**`ds:0x00E60B78`**
★★★ 实测跳到的三个野地址：**`0x00198A90`** / **`0x00DAF2AC`** / **`0x0041144C`**
        ↓
★★★ 原因：`auto playerCandidate = playerState;` **搬迁了缓冲区**
   ⇒ 函数指针**按槽自身地址加密** ⇒ 解密出别的值
```

### ★★★ "size hypothesis is RETIRED"（第 134–137 行，逐字）

```cpp
// The size hypothesis this replaced is **RETIRED, not forgotten**: with **a kilobyte of
// slack on each buffer** the engine wrote through **ps+72 of 15292** and **es+226 of 280**.
// **Neither struct is too small**, so entityState_s **0x118** and playerState_s **0x3BBC**
// both stand.
```

★★★ **⇒ 四个精确尺寸：**
```
`playerState_s` = **0x3BBC**（**15,292** 字节）⇒ 写穿到 **+72**（在范围内）
`entityState_s` = **0x118**（**280** 字节）⇒ 写穿到 **+226**（在范围内）
        ↓
★★★ ⇒ **两个结构体都不太小** ⇒ "size 假设" 作废
```

### ★★★★★ **保护标志的读写顺序**（第 140–161 行，逐字）

```cpp
// The pair is valid again, so the **protected value** behind it can be written.
// **Order matters**: the setter is **decoded THROUGH the pair**, so it has to be
// **re-keyed first**.
if (!writeNativeProtectedPlayerStateFlags(playerCandidate, plaintextProtectedFlags))
    return false;
...调用原生函数...
// The engine's **SET accessor replaced ps+0x10 with its encoded form**, and that is
// the dword ol-mod reads **otherFlags** from. Leaving it there made the server's own
// otherFlags **a different random number every frame** -- which the snapshot frame
// validator then refused (`playerstate domain refused otherFlags=...`),
// so **no snapshot ever reached the client**.
captureNativeProtectedPlayerStateFlags(playerCandidate, plaintextProtectedFlags);
```

★★★★★ **⇒ 一个完整的故障链：**
```
引擎的 **SET 访问器把 `ps+0x10` 换成编码形式**
        ↓
★★★ 而 ol-mod 正是从那个 dword 读 **`otherFlags`**
        ↓
★★★ ⇒ 服务端自己的 `otherFlags` **每帧都是不同的随机数**
        ↓
★★★ ⇒ 快照帧校验器拒绝：**`playerstate domain refused otherFlags=...`**
        ↓
★★★★★ ⇒ **"no snapshot ever reached the client"**
```

★ **⇒ 精确偏移：**`ps+0x10` = `otherFlags`。**

### ★★★ 三个 origin key（第 166–171 行）

```cpp
SvEntityOriginKeys originKeys;
for (index...) originKeys.values[index] = *(u32*)(module_ + EntityOriginKeyRvas[index]);
```

★★★ **⇒ `entityState` 的 origin 字是**用字段地址加密的**（第 191–193 行逐字）：**
```
"CODDIFF(client_think_real): entityState **origin words are encrypted
 with their field addresses**. SvNativeEntityState assignment **relocates**
 them from the temporary native-call buffer to this persistent owner."
```

### ★★★ 诊断行的 64 次上限（第 94–96 行，逐字）

```cpp
constexpr std::uint32_t ReportsPerEntityState = **64**;
```
```
理由："the steady state was **~140 lines a second** under RuntimeLog's global lock"
```

### ★★★ 诊断行格式（第 110–117 行）

```
"playerstate->entitystate inputs es=0x%08X esSize=%u eFlags@104=0x%08X seq@108=%u
 parms@12C=%u events@10C=%u,%u,%u,%u,%u,%u,%u,%u"
```

★★★ **⇒ 五个 `playerState` 偏移：`0x104`（eFlags）/ `0x108`（seq）/ `0x12C`（parms）/ `0x10C..0x128`（events 8 个 u32）。**

### ★★★★★ **原生函数内部的实际调用**（第 79–85 行，逐字）

```
"The converter reaches **sub_411280** as
 **sub_411280(ps+0x10C, ps+0x108, ps+0x12C)** -- the **predictable-event copier** --
 ending in `mov [edi+eax*8+0xB8], esi`: edi is the **entityState** this server puts
 in EAX, **0xB8** is its **event array** (which makes **0xD0** index **3**, the event
 slot this build is already known to use), and eax is an index computed from those
 three playerState words."
```

★★★★★ **⇒ 四个精确值：**
```
`sub_411280(ps+0x10C, ps+0x108, ps+0x12C)` ⇒ **可预测事件复制器**
写入：`mov [edi+eax*8+0xB8], esi`
        ↓
★★★ `0xB8` = entityState 的 **event 数组**
★★★ `0xD0` = `0xB8 + 3*8` ⇒ **index 3**（本 build 已知使用的 event 槽）
```

---

## 三、★★★★★ **`DedicatedProcessPatches.hpp` —— `.tp3` 未解包时的密文对照**

### 3.1 ★★★★★ 完整注释（第 48–62 行，逐字）

```cpp
// LOCAL OVERRIDE (olmod-local, **2026-10-03**) -- **.tp3 UNPACK ORDER**.
//
// Every install* function above reads **THIS process's own in-memory image**.
// On the distributed client that image is **still packed** when the plugin's
// entry callbacks run, so the reads see **ciphertext** and every guard reports
// a mismatch. Measured on **codoMP_client_shipRetail.exe**
// SHA256 **36997674B18F2896DE5E9D755686F6922AF10708F355175714058D0A0172B537**:
// at **t=567/1055/2068 ms** RVA **0x0034EF10** reads **EC 36 00 01 8D 39 B0 0F** and
// RVA **0x0037EE5A** reads **02 2E 08 00 AF 04 02 70**;
// at **t=4065 ms** the same two RVAs read
// **55 8B EC 83 E4 F8 83 EC 3C 53 56 8B F0 8B CE 81** and
// **81 3D C0 80 1F 0E B7 ... 75 2D**.
// Upstream's out.exe is an **already-unpacked** image, which is why this never mattered there.
```

★★★★★ **⇒ 六个精确值：**

| 时刻 | RVA | 字节 |
|---|---|---|
| ★ **t=567/1055/2068 ms** | **`0x0034EF10`** | ★ **`EC 36 00 01 8D 39 B0 0F`**（密文） |
| 同上 | **`0x0037EE5A`** | ★ **`02 2E 08 00 AF 04 02 70`**（密文） |
| ★ **t=4065 ms** | **`0x0034EF10`** | ★ **`55 8B EC 83 E4 F8 83 EC 3C 53 56 8B F0 8B CE 81`**（明文） |
| 同上 | **`0x0037EE5A`** | ★ **`81 3D C0 80 1F 0E B7 ... 75 2D`**（明文） |

★★★ **⇒ 关键判据：**
```
**t ≤ 2068 ms** ⇒ 密文（**`EC 36 00 01 ...`**）
**t = 4065 ms** ⇒ 明文（**`55 8B EC 83 E4 F8 ...`** = `push ebp; mov ebp,esp; and esp,-8; ...`）
        ↓
★★★ 明文开头 **`55 8B EC`** = **标准 x86 函数序言**
★★★ 第二个 **`81 3D C0 80 1F 0E B7 ... 75 2D`** = `cmp dword ptr ds:[0x0E1F80C0], imm32; jne +0x2D`
```

★ **⇒ 与报告 107 的 `.tp3` 解包 **~3400 ms** **完全一致** ✓**（4065 ms 已在明文）

### ★★★ `startupImageUnpacked()` 的语义（第 61–63 行，逐字）

```
"This predicate is **read-only and side-effect free**; it is the **readiness
 signal** used to **defer startup until the unpack has happened**."
```

### ★★★★★ **12 种 `DedicatedProcessPatchResult`**

```cpp
Patched / AlreadyPatched / UnsupportedHost / UnexpectedBytes /
UnexpectedSingleInstanceBytes / UnexpectedClientFrameBytes /
UnexpectedFrontendStartupBytes / UnexpectedFocusStartupBytes /
UnexpectedAccessibilityStartupBytes / UnexpectedCursorVisibilityBytes /
UnexpectedInputFrameStartupBytes / UnexpectedAudioStartupBytes /
ProtectionFailed
```

★★★ **⇒ 实际 **13 个**值（`UnexpectedBytes` 是通用,后 8 个是每补丁专用）。**

### ★★★ 八个专用补丁函数

```cpp
patchDedicatedClientFrameBuffer          // 客户端帧
patchDedicatedFrontendStartupBuffer      // 前端启动
patchDedicatedFocusStartupBuffer         // 焦点启动
patchDedicatedAccessibilityStartupBuffer // 无障碍启动
patchDedicatedCursorVisibilityBuffer     // 光标可见性
patchDedicatedInputFrameStartupBuffer    // 输入帧启动
patchDedicatedAudioStartupBuffer         // 音频启动
patchDedicatedSingleInstanceBuffer       // 单实例
```

★★ **⇒ 八个补丁,各带**专用**的错误码（除 `UnexpectedBytes` 外）。**

---

## 四、★★★★★ **`ClientAnimtreeHook` —— 519 vs 123 条目的三层钩子**

### 4.1 ★★★★★ 核心问题（第 12–17 行，逐字）

```
"**Our column 3 resolves to a 519-entry descriptor where retail's resolves to a
 123-entry one (12.124)**, and that single difference accounts for the
 **T-pose**, the **frozen animation** and the **apparent bad spawns** (12.122, 12.133)."
```

★★★★★ **⇒ 三个症状同源：**
```
**519 条目**（我们）vs **123 条目**（零售）
        ↓
★★★ ⇒ **T-pose** / **动画冻结** / **看似错误的出生点**
```

### 4.2 ★★★★★ **五个钩子站点**

| # | 站点 | RVA | 原始字节 | 目的 |
|---|---|---|---|---|
| **1** | **`sub_40B210 + 0x7B`**（resolve） | ★ **`0xB28B`** | ★ **`E8 60 FA 33 00`** | 记录**选中的**资产 |
| **2** | **`sub_74AAF0 + 0x12B`**（build） | ★ **`0x34AC1B`** | ★ **`E8 00 B0 03 00`** | 记录**构建的**树 |
| **3** | **`sub_74AAF0 + 0xCA`**（populate） | ★ **`0x34ABBA`** | ★ **`E8 41 FE FF FF`** | 记录**输入**（`.atr` 大小） |
| **4** | **`sub_788540`**（node alloc，**5 个调用点**） | ★ **`0x388540`** | — | 记录 **EAX 里的 key** |
| **5** | **`sub_527B40`**（record consumer） | ★ **`0x127B40`** | — | 记录**被应用**的记录 |

### ★★★★★ 站点 1 的反汇编（逐字）

```
0040B288  8B 11           mov  edx, [ecx]       ; the name pointer
0040B28A  52              push edx
0040B28B  E8 60 FA 33 00  call sub_74ACF0       ; <- the five bytes replaced
0040B290  83 C4 04        add  esp, 4           ; ★ CALLER cleanup, **cdecl**
0040B293  89 06           mov  [esi], eax       ; stored into the six-entry table
```

★★★ **⇒ 关键：`add esp, 4` 在**调用方** ⇒ **cdecl**（不是 stdcall）。**

### ★★★★★ 站点 2 的反汇编（逐字）

```
0074AC1A  51              push ecx                ; the NAME
0074AC1B  E8 00 B0 03 00  call sub_785C20         ; <- replaced
0074AC20  83 C4 0C        add  esp, 0Ch           ; ★ cdecl, **3 args**
0074AC2C  8B D8           mov  ebx, eax           ; the built tree
```

### ★★★★★ 站点 3 的反汇编（逐字）

```
0074ABB9  51              push ecx                 ; the NAME
0074ABBA  E8 41 FE FF FF  call sub_74AA00          ; <- replaced
0074ABBF  83 C4 0C        add  esp, 0Ch            ; ★ cdecl, **3 args**
```

### ★★★★★ **五个 node allocator 调用点**

| RVA | 函数 | 类型 |
|---|---|---|
| ★ **`0x38731C`** | `sub_7872D0` | **clone** |
| ★ **`0x3886F8`** | `sub_7886D0` | **root** |
| ★ **`0x38878C`** | `sub_7886D0` | **ancestor** |
| ★ **`0x38888F`** | `sub_7887E0` | **asset-bearing leaf** |
| ★ **`0x38A097`** | `sub_78A050` | **clone** |

★★★ **⇒ 五个站点,其中 `sub_7886D0` **两个**（root + ancestor）。**

### ★★★★★ **字符串表 / 桶 / 注册表的完整布局**（第 34–45 行，逐字）

```
string table   *(void **)dword_789C524, **20-byte stride**,
               **+0..+1 refcount**, **+3 length**, **+4.. name inline**
buckets        **0x7A5F100**, **u16** each,
               index **((kind*101) + sid*2) & 0xFFFF**
registry       **0x7A7F100**, **16-byte entries**, **4096 per bank**,
               **+0 value**, **+4 u16 next**, **+6 type**, **+8 key=(kind<<16)|(sid>>8)**
```

★★★★★ **⇒ 三个结构的精确偏移与公式：**
```
★ 字符串表：stride **20**、refcount@**0..1**、length@**3**、name@**4**
★ 桶：**`0x7A5F100`**,u16,index = **`((kind*101) + sid*2) & 0xFFFF`**
★ 注册表：**`0x7A7F100`**,**16 字节/条**,**4096/ bank**,bank = **`kind & 1`**
   ⇒ `+0` value / `+4` u16 next / `+6` type / `+8` key = **`(kind<<16)|(sid>>8)`**
```

★★★ **⇒ 第 269–270 行实现：**
```cpp
const auto bucketIndex = ((kind * 101u) + sid * 2u) & 0xFFFFu;
const auto key = ((kind << 16) | (sid >> 8)) & 0xFFFFFFFFu;
```
**⇒ 第 278–280 行：**
```cpp
const auto *entry = module + RegistryRva + ((kind & 1u) * 4096u + slot) * 16u;
```

### ★★★ `sub_74C610` 的**访问顺序依赖**（第 38–40 行，逐字）

```
"`sub_74C610` **MOVES a matched node to the front of its chain**, so **which of
 two same-key entries wins is access-order dependent** -- which is what this
 walk is here to expose."
```

★★★ **⇒ 同名条目的胜者**取决于访问顺序** ⇒ 这是**本次钩子要暴露的东西**。**

### ★★★ Zone 表的布局（第 24–29 行）

```cpp
ZoneCountRva   = **0x1A2ACF4**;   // 0x01E2ACF4
ZoneTableRva   = **0x25C9DE8**;   // 0x029C9DE8
ZoneStride     = **164**;
ZoneNameOffset = **8**;
```

★★ **⇒ 164 字节步长,名字在 +8。**

### ★★★★★ **12.153 的硬件写断点**（第 112–121 行，逐字）

```cpp
// THE WRITE WATCH (12.153). **Static search for the producer is hopeless** --
// **212 candidates for +0x14 alone** (12.150) and the base is a pointer, so an
// offset names nothing. Instead: learn a live record's address from the
// consumer, then put a **HARDWARE write breakpoint** on its `record+20` and let
// the writer identify itself.
//
// **DR0** is armed on **every thread** (the writer need not be ours), a **vectored
// handler** logs the **faulting EIP**, and it **disarms after the first hit** so this
// cannot storm the game. Separate opt-in from the hooks: **CODOL_ANIMTREE_WRITE_WATCH=1**.
```

★★★ **⇒ 五个要点：**
```
★ 静态搜索无望：**`+0x14` 单独就有 212 个候选**
★ 方法：从 consumer 学到活记录的地址 ⇒ 在 **`record+20`** 上下**硬件写断点**
★ **DR0** 在每个线程上（写入者不一定是我们的线程）
★ **VEH** 记录**出错 EIP**,**首次命中后解除**（防风暴）
★ 独立开关：**`CODOL_ANIMTREE_WRITE_WATCH=1`**
```

### ★★★★★ DR7 的精确编码（第 480–482 行）

```cpp
// len=4 (0b11), rw=write (0b01), L0 enable
ctx.Dr7 = (ctx.Dr7 & ~0xFul) | 1ul | (0x1ul << 16) | (0x3ul << 18);
```

★★★ **⇒ 三个位域：**
```
`bit0` = **L0**（本地启用）
`bit16-17` = **rw = 01**（写）
`bit18-19` = **len = 11**（4 字节）
```

### ★★★★★ **"NEVER THE CALLING THREAD"**（第 461–466 行，逐字）

```cpp
// **NEVER THE CALLING THREAD**. The first cut **suspended every thread including
// this one and the process deadlocked instantly** -- the client **froze mid-demo** (12.153).
// Our own debug registers are set **without suspending**, since a thread can safely
// set its own context.
```

★★★ **⇒ 精确故障：挂起**包括自己** ⇒ **立即死锁** ⇒ **客户端在 demo 中途冻结**。**
**⇒ 修复：自己那条线程**不挂起**,直接 `SetThreadContext`。**

### ★★★ `scanChunk` 的分块理由（第 221–226 行，逐字）

```cpp
// ONE CHUNK OF THE STRING-TABLE SCAN, guarded on its own. The first cut
// scanned **65536 entries inside a single __try**; in-process that runs off the
// end of the allocation and **the fault killed the whole walk**, which is why
// the first run logged `chain=unreadable`. An **external ReadProcessMemory probe
// survived the same bug** because its reads fail **per-call** instead of faulting.
// **Chunking means a fault ends the SCAN, not the function.**
```

★★★ **⇒ 两个不同语义：**
```
**`__try` 内的越界** ⇒ **整个函数死**
**`ReadProcessMemory` 的越界** ⇒ **单次调用失败**
        ↓
★★★ ⇒ 分块（**256 条**）⇒ 故障只结束**扫描**
```

### ★★★ 三个开关变量

| 变量 | 默认 | 作用 |
|---|---|---|
| ★ **`CODOL_ANIMTREE_RESOLVE_HOOK`** | **关** | 总开关（默认关） |
| ★ **`CODOL_ANIMTREE_TRACE`** | **关** | 启用 allocator + record consumer（旧 RE 仪器） |
| ★ **`CODOL_ANIMTREE_WRITE_WATCH`** | **关** | 硬件写断点 |

★★★ **⇒ 为什么默认关（第 689–691 行逐字）：**
```
"DEFAULT OFF. **Two changes broke the client earlier in this session** (12.127, 12.131);
 a patch that **rewrites the client's own load path** opts in explicitly rather than
 shipping enabled."
```

★★★ **⇒ 为什么 trace 默认关（第 701–705 行逐字）：**
```
"The resolver/build/populate hooks below are **the production fix**. The allocator and
 record-consumer hooks are **old RE instruments**: each adds a thunk, atomic and
 formatted file write to **animation hot paths**, producing **thousands of events
 exactly when a zombie wave appears**."
```

### ★★★ 三个日志格式

```
**ANIMTREERESOLVE** n= name= -> 0x entries= zones= [zones] sid= bucket= key= chain:[...]
**ANIMTREEBUILD**    n= name= a2= a3= -> 0x entries=
**ANIMTREEASSET**    n= name= assetSize= a3= ok=
**ANIMTREENODE**     key= asset= parent= from=<site> ret=0x
**ANIMTREEAPPLY**    type= ent= key= flags= rec=0x
**ANIMTREEWRITER**   eip=0x
**ANIMTREEWATCH**    armed at 0x on N threads
```

★★★ **⇒ 七个日志前缀。**

### ★★★ 各日志的上限

| 日志 | 上限 |
|---|---|
| `ANIMTREENODE` | ★ **4000** |
| `ANIMTREEAPPLY` | ★ **3000** |
| `ANIMTREEWRITER` | ★ **12** |

### ★★★ `logNodeKey` 跳过 key < 3（第 391 行）

```cpp
if (key < 3) return;   // ★ key 0 和 2 跳过
```
★ **理由（第 93–95 行逐字）："the wire can only ever carry **key 0 or 2** (12.105, 12.110.1),
yet the demo's actors carry **key 112 with ancestors 20/100/101/102** (12.113)."**

### ★★★ `readRecord` 的五个偏移（第 525 行）

```cpp
*type = r[1];   // +4
*ent  = r[4];   // +16
*key  = r[5];   // +20
*flags= r[12];  // +48
```
★★ **⇒ 四个字段：`+4` type / `+16` entity / `+20` key / `+48` flags。**

### ★★★ `readAssetSize` 的 size 公式（第 77–78 行）

```
"`v4 = *(DWORD *)(asset + 8) + 1`"   ⇒ asset **+8** 是 size（+1）
```

### ★★★ 六个 animtree 名字（第 149–151 行）

```
"**Six run per map load**, one per column of `sub_40B210`'s hard-coded name list,
 plus one for **"multiplayer"** from the separate call site this hook does NOT touch."
```

---

## 五、★★★★ **`ClientCommandTrace.hpp` —— 三个测量工具**

### 5.1 ★★★★★ **三个 dispatch 站点**（第 16–19 行，逐字）

```
"the vocabulary has **THREE dispatch sites** --
 **sub_613A40**'s switch,
 **sub_614AC0** for **'!' sub-frames**, and
 **sub_614C00** itself for the **disconnect paths**.
 **sub_614C00 is the only one that sees all of them, before the split.**"
```

★★★★★ **⇒ 三个站点,RVA = `0x213A40` / `0x214AC0` / `0x214C00`：**
```
`sub_613A40` ⇒ 126-case switch
`sub_614AC0` ⇒ `'!'` 子帧
`sub_614C00` ⇒ 断线路径
        ↓
★★★ ⇒ **`sub_614C00`（RVA `0x214C00`）是唯一看到全部且**在分裂之前**的**
```

### ★★★★★ **速率论证（第 21–24 行，逐字）**

```
"**RATE IS THE SAFETY ARGUMENT**, and it is measured rather than assumed.
 The retail dm demo carries **1478 reliable commands across 621 s** -- about **2.4/s**.
 A **Frida hook on the PER-FRAME sub_54FDA0 crashed all three running clients at once
 on 2026-08-24 at 100-180 fps**; the two probes that were fine the same day fired
 only on **rare paths**. This is the rare kind."
```

★★★★★ **⇒ 四个精确值：**
```
零售 dm demo：**1478 条**可靠命令 / **621 秒** ⇒ **约 2.4/s**
        ↓
★★★ 反例：**Frida hook 在每帧的 `sub_54FDA0`** 上
   ⇒ **2026-08-24 一次性崩掉三个客户端**（**100-180 fps**）
```

### ★★★★★ **`com_maxfps` 的完整分析**（第 59–70 行，逐字）

```cpp
// The dvar is registered at **0x004FC400** with default **200**, min **0**, MAX **200**,
// so nothing in the graphics menu can ask for more. **Com_Frame's limiter
// (0x004FE220**, whose own profiler scope is literally "**max fps spin**") then does
//
//     if (maxfps > 0) minMsec = **1000 / maxfps**;        // INTEGER division: 200 -> 5 ms
//     while (timeGetTime() - last < minMsec) **Sleep(1)**;
//
// and **Sleep(1) plus a millisecond-granular clock overshoot 5 ms to about 5.3**,
// which is the **~186-190 a player sees**. **Zero SKIPS the limiter entirely** --
// minMsec stays **1** -- and zero **is inside the dvar's own range**, so it is
// the only route past that ceiling.
```

★★★★★ **⇒ 五个精确值：**
```
dvar 注册 @ **0x004FC400**：default **200** / min **0** / max **200**
限速器 @ **0x004FE220**：profiler scope = **"max fps spin"**
        ↓
★★★ `minMsec = 1000 / maxfps`（**整数除法**）⇒ 200 ⇒ **5 ms**
★★★ `while (timeGetTime() - last < minMsec) Sleep(1)`
★★★ `Sleep(1)` + 毫秒粒度时钟 ⇒ **5 ms 过冲到约 5.3** ⇒ **~186-190 fps**
        ↓
★★★ **零跳过限速器**（minMsec 保持 **1**）且 **0 在 dvar 范围内** ⇒ **唯一突破天花板的路**
```

### ★★★ **246 个 netfield 的对照**（第 45–49 行，逐字）

```
"**WHY IT IS WORTH 246 FIELDS.** `playerstate-0x00DA8540.tsv` carries **246 netfields
 across 15,220 bytes** and has **never been checked against anything but itself**.
 Theatre playback decodes a **RETAIL demo** into that struct with the **retail client's
 own code**, and we decode the same bytes offline -- so **every field where the two
 disagree is either our codec being wrong or a field we have mis-named**, and every
 field where they agree is verified."
```

★★★ **⇒ 三个精确值：**
```
**246 个 netfield** / **15,220 字节** / 表 `playerstate-0x00DA8540.tsv`
```

### ★★★ 输出路径的教训（第 27–29 行，逐字）

```
"Writes `Ayria\Logs\client-commands.csv` **beside the EXECUTABLE**. **Not a relative path**:
 `weapon-slots.csv` was opened relatively once, which **works from the client and silently
 does nothing from the dedicated**, and **the audit reported its counts either way**."
```

★★★ **⇒ 一次真实的静默失败：相对路径在客户端可用、在专服静默无操作,而审计仍报数。**

### ★★★ 三个函数

```cpp
installClientCommandTrace(bindings)        // ⇒ Ayria\Logs\client-commands.csv
installPlayerStateTrace(bindings, intervalMs)  // ⇒ Ayria\Logs\client-ps.csv（**无钩子,detached 线程**）
startFpsProbe(bindings, set, value, sampleMs)
```

★ **⇒ 第 2 条的理由（第 40–43 行逐字）："**NO HOOK**. We are already inside the process,
 so this is a **detached thread reading memory on a timer** -- it **cannot perturb the
 code it observes**, which a trampoline always can. **Hooks are for EVENTS; state only
 ever needed a reader**."**

---

## 六、★★★★ **`ClientNoclipHotkey` —— 飞行热键与调试电池**

### 6.1 ★★★★★ 五个常量（第 27–39 行，逐字）

```cpp
constexpr int DefaultKey = **VK_LMENU**;                          // ★ 左 Alt（不是 VK_MENU）
constexpr auto PollInterval = std::chrono::milliseconds(**33**);   // ★ 30 Hz
constexpr auto RepeatInterval = std::chrono::milliseconds(**500**); // ★ 2 Hz
constexpr std::uint32_t HoldMilliseconds = **1500**;
constexpr std::uint32_t SubmitTimeoutMilliseconds = **150**;
```

### ★★★★★ 为什么是 `VK_LMENU` 而不是 `VK_MENU`（逐字）

```
"**VK_LMENU is LEFT ALT specifically** -- **VK_MENU would also fire on right alt**,
 and **AltGr on a non-US layout sends right alt together with control**, which is
 a keystroke nobody meant as 'fly'."
```

### ★★★★★ 为什么 33 ms（逐字）

```
"**30 Hz**. A human keypress is **hundreds of milliseconds**; this resolves the edge
 to **~33 ms**, which is **under one server frame at 50 ms**."
```

### ★★★★★ **边沿 + 保活,绝不是电平**（第 157–163 行，逐字）

```cpp
// **EDGE PLUS KEEP-ALIVE, NEVER LEVEL**: nothing is sent while the key is up,
// and **twice a second while it is down**.
if (held && now >= nextRepeat) { nextRepeat = now + RepeatInterval; send(userId, true); }
```

★★★ **⇒ 三条：**
```
键抬起 ⇒ **不发**
键按下 ⇒ **每 500 ms 发一次**
        ↓
★★★ 理由（第 31–33 行）："The dedicated **expires a hold it has not heard about**,
 so this is what makes a **LOST key-up recover on its own** instead of
 **stranding somebody in the air**."
```

### ★★★★★ **前台窗口检查**（第 91–104 行，逐字）

```cpp
// **ONLY WHEN THIS PROCESS OWNS THE FOREGROUND WINDOW**. GetAsyncKeyState is
// **global**, so without this an alt-tabbed client would **fly whenever the
// player pressed alt in another window** -- and **ALT IS THE ALT-TAB KEY**, so
// that is **not a corner case, it is the common one**. Losing focus also releases.
```

★★★★★ **⇒ 一个精确的必然后果：**
```
`GetAsyncKeyState` 是**全局**的
        ↓
★★★ 不检查前台 ⇒ **alt-tab 出去后按 Alt 就会飞**
★★★ 而 **Alt 正是 alt-tab 键** ⇒ **不是边角情况,是常见情况**
```

### ★★★★★ **`ResolveBySenderAddress = 0` 的理由**（第 245–252 行，逐字）

```cpp
// **ZERO, DELIBERATELY**: "**resolve me by the address I am sending from**".
// A client **CANNOT name itself** here. It knows **OLMOD_PLATFORM_USER_ID
// (0x01100001DEADC0DE)** and the server knows **the xuid out.exe put in its connect
// string, which is the C# AuthServer's sequentially issued account** --
// **a live match ran with 69420 and 69422 against platform ids ...C0DE and ...C0DF**.
// Sending the platform id would **name no slot at all**. Only the **tool path** sends
// a real xuid.
```

★★★★★ **⇒ 四个精确值：**
```
客户端知道：**`OLMOD_PLATFORM_USER_ID = 0x01100001DEADC0DE`**
服务端知道：**out.exe 在 connect 串里的 xuid** = **C# AuthServer 顺序发放的账号**
        ↓
★★★ 实测一局：**`69420`** 和 **`69422`** ↔ 平台 id **`...C0DE`** 和 **`...C0DF`**
        ↓
★★★★★ ⇒ **发平台 id 会"name no slot at all"**
```

★ **⇒ 与报告 124/125 的**第三个命名空间**（平台 id / DW 账号 id / **C# AuthServer 顺序号**）**
**⇒ 记录为**重要补正**。**

### ★★★★★ **调试电池的两个开关**（第 185–186 行）

```cpp
if (environmentValue("OLMOD_ZM_DEBUG_BATTERY") != "1" ||
    OlMod::DedicatedControl::configuredHostAddress() != "127.0.0.1") return;
```

★★★ **⇒ **双重门禁**：`OLMOD_ZM_DEBUG_BATTERY=1` **且** host 必须是 **`127.0.0.1`**。**
**⇒ 记录为**安全设计**（远端不可用）。**

### ★★★ 三个别名键（第 197 行）

```cpp
(GetAsyncKeyState(key) | GetAsyncKeyState(VK_ADD) | GetAsyncKeyState(VK_OEM_7))
```
★★ **⇒ 主键（默认 **F6**）+ **Numpad+** + **撇号**。**

### ★★★ 500 ms 节流（第 209 行）

```cpp
next = now + std::chrono::milliseconds(500);
```

### ★★★ 物理抬键追踪（第 206–208 行，逐字）

```
"Track **physical key-up even while unfocused**. Returning to the game with the
 key already held **cannot synthesize another grant**."
```

---

## 七、★★★★ **`ClientBatteryLookup.hpp` —— `cg` 是 `table[selector] XOR FBB2C97A`**

### 7.1 ★★★★★ 完整逻辑（逐字）

```cpp
// CODREF(out.exe613A40): **cg is table[selector] XOR FBB2C97A, NOT
// table[localClientNum]**. Live clients use selectors **5** and **3**.
// The **64-entry bound** is a **conservative read guard**, not a recovered
// native array declaration.
```

★★★★★ **⇒ 四个精确值：**
```
`cg = table[selector] ^ **0xFBB2C97A**`（**不是** `table[localClientNum]`）
实测 selector：**5** 和 **3**
表边界：**64**（保守读守卫,**不是**恢复的数组声明）
```

### ★★★★★ 四个读地址与校验

| # | 地址 | 校验 |
|---|---|---|
| **1** | **`base + 0x7EC3B58`** | `selector < 64` |
| **2** | **`base + 0x181D188 + selector*4`** | `encoded != 0` |
| **3** | `cg + 0` | `commandTime != 0` |
| **4** | `cg + 4` | ★ **`pmType == 0`** |
| **5** | **`cg + 0x1A4`** | `health != 0` |
| **6** | **`cg + 0x158`** | ★ **`client < 18`** |

★★★ **⇒ 六个偏移,其中两个与报告 126 §1 呼应：**
```
`cg + 0x1A4` = **复制的 health stats[0]**（**420**）
`cg + 0x20C` = **服务端 Pmove 影子,两个活客户端都保持零**
`cg + 0x158` = **clientNum**（与报告 126 §2 的 `ps+0x158` 同名不同物）
```

### ★★★ 两个 CODREF 出处

```
**CODREF(out.exe613A40)** ⇒ cg 解析
**CODREF(out.exe411360)** ⇒ "replicated health stats[0] is **+1A4 (420)**.
   **+20C is a server Pmove shadow and remains zero in both live clients**."
```

### ★★★ `client >= 18` 的上界

```cpp
client >= **18**  ⇒ 拒绝
```
★★ **⇒ 与 `MaximumSessionMembers = 18` / `capacity = 18`**第三次一致** ✓**

---

## 八、★★★★ **`GameStateConfiguration` 与 `DedicatedSessionConsumption` 的状态机**

### 8.1 ★★★★★ **`GameStateConfigurationStage` 的 18 个值**

| # | 值 | 名 |
|---|---|---|
| 0 | `None` | `none` |
| 1 | `Processing` | `processing` |
| 2 | `InvalidChecksum` | `invalid_checksum` |
| 3 | `MapCenterUnavailable` | `map_center_unavailable` |
| 4 | `CharacterUnavailable` | `character_unavailable` |
| 5 | `PreparedLoadoutMismatch` | `prepared_loadout_mismatch` |
| 6 | `DynamicWeaponRangeUnavailable` | `dynamic_weapon_range_unavailable` |
| 7 | `PrimaryDependencyRegistrationFailed` | `primary_dependency_registration_failed` |
| 8 | `PrimaryWeaponRegistrationFailed` | `primary_weapon_registration_failed` |
| 9 | `SecondaryDependencyRegistrationFailed` | `secondary_dependency_registration_failed` |
| 10 | `SecondaryWeaponRegistrationFailed` | `secondary_weapon_registration_failed` |
| 11 | `CharacterChanged` | `character_changed` |
| 12 | `ServerCommitFailed` | `server_commit_failed` |
| 13 | `Accepted` | `accepted` |
| 14 | `DynamicWeaponRegistryUnavailable` | `dynamic_weapon_registry_unavailable` |
| 15 | `DynamicWeaponRegistryRegistrationFailed` | `dynamic_weapon_registry_registration_failed` |
| 16 | `MiniMapUnavailable` | `minimap_unavailable` |
| 17 | `ObjectiveMaterialUnavailable` | `objective_material_unavailable` |

★★★ **⇒ **18 个阶段,17 种失败 + `Accepted`。**

### ★★★★★ 为什么要有这个枚举（第 44–48 行，逐字）

```
"**Every stage below is a distinct way the gamestate can fail to configure**, and
 **NONE of them was reported anywhere: not in the log, not over the dedicated control
 port**. That was survivable while the **loadout resolver refused earlier** and this
 code was **unreachable**. It **stopped being survivable the moment the booking started
 succeeding**, because **the frame thread then stops somewhere in here** and the last
 line printed is the only thing that says where."
```

★★★★★ **⇒ 一条完整的因果：**
```
**booking 开始成功** ⇒ 代码路径**首次可达**
        ↓
★★★ **帧线程停在这里某处** ⇒ **最后打印的那行是唯一线索**
        ↓
★★★ 之前**没有一行日志** ⇒ 无法定位
```

### ★★★ `GameStateConfigurationStatus` 的 5 个字段

```cpp
std::uint32_t attemptCount{};
GameStateConfigurationStage stage{};
std::int32_t  failedClassIndex{**-1**};
std::uint32_t registeredClassMask{};
std::uint32_t firstDynamicWeaponAssetIndex{};
```

### ★★★★★ **`DedicatedSessionConsumeStage` 的 17 个值**

```
None / Queued / Processing / MapAssetLoadFailed / WaitingForMapAssets /
ConfigStringGenerationResetFailed / WaitingForClientReadiness /
WaitingForConfigStringGeneration / ConstantConfigStringsInitializationFailed /
WeaponRegistryUnavailable / WeaponRegistryInitializationFailed /
CharacterPresentationFailed / WeaponLoadoutFailed / ConfigureBookingFailed /
Accepted / WorldInitializationFailed / SessionRosterRejected
```

★★★ **⇒ **17 个值,4 个是"等待"**（`WaitingForMapAssets` / `WaitingForClientReadiness` /
`WaitingForConfigStringGeneration`）⇒ **3 个等待,12 个失败,1 个 `Accepted`,1 个 `None`。**
**⇒ 与报告 094 的**17 种 `DedicatedControl` 消息类型**数字巧合 ⇒ 记录为**巧合**（不是同一组）。**

### ★★★ `DedicatedSessionConsumptionStatus` 的 8 个字段

```cpp
std::uint64_t queuedRequestId{};
std::uint64_t processedRequestId{};
DedicatedSessionConsumeStage stage{};
std::int32_t  failedClassIndex{**-1**};
std::uint32_t requestedClassMask{};
std::uint32_t resolvedClassMask{};
std::uint32_t characterFailure{};
std::uint32_t characterRecordIndex{**0xFFFFFFFFu**};   // ★ 哨兵
std::uint32_t characterItemId{};
```

★★★ **⇒ 两个哨兵：`failedClassIndex = -1` / `characterRecordIndex = 0xFFFFFFFF`。**

### ★★★ `DedicatedSessionConsumptionTracker` **没有 mutex**

```cpp
private:
    DedicatedSessionConsumptionStatus status_;   // ★ 无 mutex
```
★★★ **⇒ 对比 `GameStateConfigurationTracker` **有** `mutable std::mutex mutex_;`**
**⇒ 记录为**不一致**（前者假定单线程）。**

---

## 九、★★★★ **`SessionAssetRegistry` —— 名册资产与三个原地更新**

### 9.1 ★★★★★ 六个映射

```cpp
ClientCharacterPresentation characterPresentation;                       // ★ 单值
std::map<std::string, SvResolvedLoadout>   loadouts;                     // 按 loadout 名
std::map<std::string, SvResolvedPerks>     perks;
std::map<std::string, OlMod::DedicatedSession::EquipmentRequest> equipment;
std::map<std::string, SvResolvedEquipment> offhands;
std::optional<SvResolvedRewards>           rewards;                      // ★ 共享 class-0
```

★★★ **⇒ `rewards` 的注释（第 23–25 行，逐字）：**
```
"**Shared class-0 selection**; **nullopt means resolution failed**, while an
 **engaged empty selection means the player equipped no rewards**."
```
**⇒ 三态语义：`nullopt` = 失败 / 空值 = 未装备 / 有值 = 已装备。**

### ★★★ `replace()` 的三重校验（第 36–47 行）

```cpp
if (members.empty() || members.contains(0) && members.size() != 1) return false;  // ★
for (auto &[xuid, assets] : members)
    if (assets.loadouts.empty()) return false;                                    // ★
```

★★★ **⇒ 第 1 条**精确**：`members.contains(0) && members.size() != 1`
```
有 **xuid 0** ⇒ **必须只有 1 个成员**（单人/测试路径）
```

### ★★★★★ **`updateMember` 与 `updateCharacter` 的分工**（第 52–87 行，逐字）

```
`updateMember`（§157c）：
  "it replaces one player's **classes/character** without the full `replace()`
   that a SessionStart does, so **the other members and the running match are untouched**.
   **The next spawn resolves the new loadout.**"
        ↓
`updateCharacter`：
  "**CHANGE ONE MEMBER'S CHARACTER IN PLACE** -- **live, mid-match, without touching
   their classes or the running world**."
   ⇒ "The **per-frame clientInfo provider re-reads characterPresentation every frame**
      and **sv_main_mp section 166 remembers the last good answer**, so **a NEW answer
      always wins**: the new body, hands and outfit land **on the next frame the client
      is drawn**. Nothing else about the member moves, which is exactly why this is
      **not** `updateMember()`."
```

★★★ **⇒ 两个方法的语义差别：**
```
`updateMember`    ⇒ 换 **classes + character** ⇒ **下次出生**生效
`updateCharacter` ⇒ 只换 **character**       ⇒ **下一帧**生效（逐帧重读）
```

### ★★★ **`findMember` 的 xuid-0 回退**（第 154–164 行）

```cpp
if (member == members_.end() && members_.size() == 1 && members_.begin()->first == 0)
    member = members_.begin();     // ★ 单个 xuid-0 成员 ⇒ 任何查询都命中它
```

---

## 十、★★★★ **`codol_bot_classes.hpp` —— 9 类 + 10 个外观部件**

### 10.1 ★★★★★ 数据来源（逐字）

```
Source: `dedicated\bin\home\main\mp\botclasstable.csv`（**5838 B**,
        sha256 **DE062FAEB2BF5577**）
        ↓
★★★ "The file holds **nine classes over 53 rows**; the three rows reproduced here are
   **loadoutName / loadoutPrimary / loadoutSecondary**."
        ↓
★★★ 未消费的："**attachments, camo, perks, killstreaks, lethal/tactical and the
   TF and SC appearance sets** are NOT consumed by this header -- they need
   **server-side plumbing that does not exist yet**, and are **left named rather than
   approximated**."
```

### ★★★★★ 9 个官方 bot 类

| # | name | primary | secondary |
|---|---|---|---|
| 1 | `CLASS_CLASS1` | `scarsapr` | `m9` |
| 2 | `CLASS_CLASS2` | `m14ebr` | `deserteagle` |
| 3 | `CLASS_CLASS3` | `m1014` | `pp2000` |
| 4 | `CLASS_CLASS4` | `aa12` | `tmp` |
| 5 | `CLASS_CLASS5` | `m240` | `coltanaconda` |
| 6 | `CLASS_CLASS6` | `vector` | `deserteagle` |
| 7 | `CLASS_CLASS7` | `aa12` | `m9` |
| 8 | `CLASS_CLASS8` | `miniuzi` | `m93` |
| 9 | `CLASS_CLASS9` | `mp5k` | `m9` |

★★ **⇒ 注意 **`coltanaconda`**（不是 `anaconda`）⇒ CSV 原文如此。**

### ★★★★★ 10 个外观部件（逐字）

```cpp
"charGender", "charBOO", "charFJA", "charFPA", "charHAN",
"charHEA",    "charVES", "charHEG", "charELP", "charKNP",
```

★★★ **⇒ 10 个部件,每个有 **TF 侧 9 个 + SC 侧 9 个**（按类）。**

### ★★★★★ 外观表的来源与生成器（第 41–48 行，逐字）

```
"**THE OFFICIAL APPEARANCE SETS, TRANSCRIBED VERBATIM FROM THE SHIPPED TABLE.**
 Source rows **31-40** (TF side) and **43-51** (SC side) of
 dedicated\bin\home\main\mp\botclasstable.csv
 Generated by
 `01-docs\40-evidence\人机AI移植-20261011-30000\P4k-官方外观表-20261012-15000\
  gen_bot_appearance_table.py`,
 which **parses its own output back and compares it cell by cell with the CSV** --
 **the strings below are not hand-typed**."
```

★★★★★ **⇒ 精确出处：TF = 行 **31-40**、SC = 行 **43-51**；生成器**自校验**。**

### ★★★★★ 为什么需要外观表（第 50–54 行，逐字）

```
"**WHY THIS EXISTS.** The loadout half of this file **replaced the host-clone bot**
 with the nine shipped classes; **the appearance half did not exist**, so **every bot's
 CHARACTER still came from the cloned host member** and **the fill looked like a pile
 of the player**."
```

★★★ **⇒ 一个精确的症状：**"**the fill looked like a pile of the player**"（填充物像一堆玩家自己）。**

### ★★★ 三个**全空**的行

```
charELP 的 SC 侧 ⇒ **全部 9 个空串**
charKNP 的 SC 侧 ⇒ **全部 9 个空串**
```
★★★ **⇒ 注释（第 54 行）："An **empty string is the table's own empty cell** --
 it stays empty here too."**

### ★★★ `charGender` 全 `"m"`（18 个）

### ★★★ 两个 `static_assert`

```cpp
static_assert(OfficialBotAppearancePartCount == **10**,
              "the shipped table carries this many character rows");
```

---

## 十一、★★★★ **`FrameHook` 与 `DisconnectWitness`**

### 11.1 ★★★★★ `FrameHook.cpp` 的完整实现（74 行）

```cpp
constexpr std::size_t HookSize = **5**;     // ★ 5 字节 E9 跳转

__declspec(naked) void comFrameHook()
{
    __asm
    {
        call dword ptr [OriginalComFrame]   // ★ 先调原函数
        pushfd                              // ★ 保存标志
        pushad                              // ★ 保存全部通用寄存器
        call runServerFrame                 // ★ 我们的回调
        popad
        popfd
        ret
    }
}
```

★★★ **⇒ 顺序**关键**：**
```
① 先 `call [OriginalComFrame]`（**原函数**）
② 再 `pushfd` + `pushad`
③ 再 `call runServerFrame`
④ 再 `popad` + `popfd`
⑤ `ret`
```

★★★ **⇒ 理由：原函数会**破坏标志和寄存器** ⇒ 必须在它**之后**才保存。**

### ★★★ 蹦床的构造（第 45–56 行）

```cpp
auto *trampoline = VirtualAlloc(nullptr, HookSize + 5, MEM_COMMIT|MEM_RESERVE, PAGE_EXECUTE_READWRITE);
std::copy_n(target, HookSize, trampoline);          // ★ 复制 5 字节
trampoline[HookSize] = 0xE9;                        // ★ jmp
*(int32_t*)(trampoline + HookSize + 1) = (target + HookSize) - (trampoline + HookSize + 5);
```

★★★ **⇒ 蹦床 = **原 5 字节 + `E9` 跳回 `target+5`**。**

### ★★★ 三个失败路径

```cpp
if (!bindings.valid() || !callback || OriginalComFrame) return false;   // ★ 已装过
if (!trampoline) return false;                                          // ★ 分配失败
if (!VirtualProtect(...)) { VirtualFree(trampoline, 0, MEM_RELEASE); return false; }  // ★ 清理
```

### ★★★★★ `DisconnectWitness` 的五个结果

```cpp
NotRequested / Installed / AlreadyInstalled / UnexpectedBytes / UnsupportedHost
```

★★★ **⇒ 五个值（比 `AnimtreeHookResult` 少 `Disabled` 和 `ProtectionFailed`）。**

### ★★★ 开关（第 6 行，逐字）

```
"**Off unless `OLMOD_DISCONNECT_WITNESS=1`**."
```

★ **⇒ 与 `CODOL_ANIMTREE_*` 的**不同前缀**（`OLMOD_` vs `CODOL_`）⇒ 记录为**命名不一致**。**

---

## 十二、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`StructuredDataDef` 头部** | **`0x3C`** 字节 / 14 字段（`Version@0` … `OffsetTable@0x38`） |
| 2 | ★★★★★ **StructRecord 20B** | `{propertyCount@0, properties*@4, sizeBytes@8, bitOffset@12, indexCount@16}` |
| 3 | ★★★★★ **PropertyRecord 24B** | `{name*@0, category@4, typeIndex@8, offsetIndex@12}` |
| 4 | ★★★ **IndexedArrayRecord 16B** | `{arraySize@0, elementCategory@4, elementTypeIndex@8, elementSizeBytes@12}` |
| 5 | ★★★★★ **6 个 Category** | **Int=0 / Byte=1 / Bool=2（**BIT 偏移**）/ String=3（**maxlen**）/ Struct=5 / IndexedArray=6** |
| 6 | ★★ **Category 4 未命名** | 待核对（可能是 Float） |
| 7 | ★★★★ **`sub_50F410` 公式** | `byteOffset = *(u32*)(*(u32*)(def+0x38) + 4*index)` |
| 8 | ★★★★★ **8 个手测序号 vs 3.3.3.3** | `characterClasses` **605/14** → **576/10**；`weaponClasses` **1607/37** → **1154/36**；`slots` **5** → **1**；`primaryBase` 22 / `secondaryBase` 29 |
| 9 | ★★★★★ **附件序号是 numerology** | `weaponOrdinal - AttachmentCount` ⇒ 已错过一次（**187g/187m**）；def 自己命名：`primaryAttach@16`、`secondaryAttach@23`（**六宽**） |
| 10 | ★★★ **内存形态 = 磁盘 + 指针修正** | 磁盘 `+0x38` = **`0xFFFFFFFF`**,运行时 = **偏移表指针** |
| 11 | ★★ 三个防御常量 | `MaxTypeDepth=8` / `MaxNameLength=128` / `sizeof(void*)==4` |
| 12 | ★★★ 前缀冲突 | **`primaryAttach`/`primaryBase`**、**`lethal`/`lethalDoubleAmmo`** ⇒ 比较含 NUL |
| 13 | ★★★★★ **`playerState` 从 ECX 到栈** | 3.3.3.3：`ps`@**ECX**；1649370：`ps`@**[ebp+arg_0]**、`es`@**EAX** |
| 14 | ★★★★★ **四条指令** | `4116f4 mov ebx,[ebp+arg_0]` / `4116f9 mov edi,eax` / `411703 mov eax,[ebx+104h]` / `41170c mov [edi+8],eax` |
| 15 | ★★★★★ **函数指针按地址加密** | `xor ecx, ds:**0x00E60B78**` / `call ecx` @ **0x0041144C**；实测野地址 **0x00198A90 / 0x00DAF2AC / 0x0041144C** |
| 16 | ★★★★ **两个结构体尺寸** | `playerState_s` = **0x3BBC**（15,292）；`entityState_s` = **0x118**（280） |
| 17 | ★★★ 写穿位置 | `ps+72` / `es+226` ⇒ **都在范围内** ⇒ size 假设作废 |
| 18 | ★★★★★ **`otherFlags` 故障链** | 引擎 SET 访问器把 **`ps+0x10`** 换成编码形式 ⇒ 每帧随机 ⇒ **`playerstate domain refused otherFlags=...`** ⇒ **无快照** |
| 19 | ★★★★ **`sub_411280(ps+0x10C, ps+0x108, ps+0x12C)`** | 可预测事件复制器；写 `mov [edi+eax*8+0xB8], esi` ⇒ **`0xD0` = index 3** |
| 20 | ★★ `playerState` 五个偏移 | `0x104` eFlags / `0x108` seq / `0x12C` parms / `0x10C..0x128` events(8) |
| 21 | ★★ 诊断上限 | **64** 次/entityState（稳态 **~140 行/秒**） |
| 22 | ★★★★★ **`.tp3` 密文/明文** | **t≤2068ms**：`0x0034EF10`=`EC 36 00 01 8D 39 B0 0F`、`0x0037EE5A`=`02 2E 08 00 AF 04 02 70`；**t=4065ms**：`55 8B EC 83 E4 F8 83 EC 3C 53 56 8B F0 8B CE 81` / `81 3D C0 80 1F 0E B7 ... 75 2D` |
| 23 | ★★★ **13 种 `DedicatedProcessPatchResult`** | 5 通用 + **8 专用 `Unexpected*Bytes`** + `ProtectionFailed` |
| 24 | ★★★ 八个专用补丁 | ClientFrame / FrontendStartup / FocusStartup / AccessibilityStartup / CursorVisibility / InputFrameStartup / AudioStartup / SingleInstance |
| 25 | ★★★★★ **animtree 519 vs 123** | 我们 **519**、零售 **123** ⇒ **T-pose + 动画冻结 + 错误出生点** |
| 26 | ★★★★★ **五个钩子站点** | resolve `0xB28B`（`E8 60 FA 33 00`）/ build `0x34AC1B`（`E8 00 B0 03 00`）/ populate `0x34ABBA`（`E8 41 FE FF FF`）/ alloc `0x388540`（5 个调用点）/ apply `0x127B40` |
| 27 | ★★★ 五个 alloc 调用点 | `0x38731C`(clone7872D0) / `0x3886F8`(root7886D0) / `0x38878C`(anc7886D0) / `0x38888F`(leaf7887E0) / `0x38A097`(clone78A050) |
| 28 | ★★★★★ **字符串表布局** | stride **20** / refcount@**0..1** / length@**3** / name@**4** |
| 29 | ★★★★★ **桶公式** | **`0x7A5F100`**,u16,`((kind*101) + sid*2) & 0xFFFF` |
| 30 | ★★★★★ **注册表布局** | **`0x7A7F100`**,**16B/条**,**4096/bank**,bank=**`kind&1`**；`+0`value / `+4`next / `+6`type / `+8`key=**`(kind<<16)\|(sid>>8)`** |
| 31 | ★★★ `sub_74C610` 移到链头 | ⇒ 同名条目胜者**取决于访问顺序** |
| 32 | ★★★ Zone 表 | count@**`0x1A2ACF4`** / table@**`0x25C9DE8`** / stride **164** / name@**+8** |
| 33 | ★★★★★ **硬件写断点** | `+0x14` 有 **212 个候选** ⇒ 在 **`record+20`** 上设 **DR0** |
| 34 | ★★★★★ **DR7 编码** | `bit0`=L0 / `bit16-17`=**01 写** / `bit18-19`=**11 4字节** |
| 35 | ★★★★★ **"NEVER THE CALLING THREAD"** | 首次实现挂起**包括自己** ⇒ **立即死锁** ⇒ 客户端**在 demo 中途冻结** |
| 36 | ★★★ `scanChunk` 分块 | **256 条**；`__try` 越界杀整个函数,`ReadProcessMemory` 只失败单次 |
| 37 | ★★★ 三个开关 | `CODOL_ANIMTREE_RESOLVE_HOOK` / `CODOL_ANIMTREE_TRACE` / `CODOL_ANIMTREE_WRITE_WATCH`（**全默认关**） |
| 38 | ★★★ 默认关的理由 | "**Two changes broke the client earlier in this session**（12.127, 12.131）" |
| 39 | ★★★ trace 默认关的理由 | "allocator/record-consumer 是**旧 RE 仪器** ⇒ 在**动画热路径**上产生**数千事件**,恰好在僵尸潮出现时" |
| 40 | ★★★ 三个日志上限 | `ANIMTREENODE` **4000** / `ANIMTREEAPPLY` **3000** / `ANIMTREEWRITER` **12** |
| 41 | ★★★ `readRecord` 四个偏移 | `+4` type / `+16` entity / `+20` key / `+48` flags |
| 42 | ★★★ `readAssetSize` | `*(u32*)(asset + 8) + 1` |
| 43 | ★★★★★ **三个 dispatch 站点** | `sub_613A40`(switch) / `sub_614AC0`(`'!'`) / **`sub_614C00`(RVA 0x214C00,唯一看全部)** |
| 44 | ★★★★★ **速率论证** | 零售 dm demo **1478 条 / 621 秒 = 2.4/s**；反例：**Frida 在 `sub_54FDA0`（每帧）上 2026-08-24 崩掉三个客户端**（100-180 fps） |
| 45 | ★★★★★ **`com_maxfps`** | dvar @**`0x004FC400`** default **200** / min **0** / max **200**；限速器 @**`0x004FE220`** scope=**"max fps spin"** |
| 46 | ★★★★★ **`Sleep(1)` 过冲** | `minMsec = 1000/200 = 5 ms` ⇒ 实际 **~5.3** ⇒ **~186-190 fps**；**零跳过限速器**（minMsec 保持 1） |
| 47 | ★★★ **246 netfields** | `playerstate-0x00DA8540.tsv` / **15,220 字节** |
| 48 | ★★★ 相对路径教训 | `weapon-slots.csv` 在客户端可用、在专服**静默无操作**,**审计仍报数** |
| 49 | ★★★★★ **noclip 五个常量** | `VK_LMENU` / **33 ms** / **500 ms** / **1500 ms** / **150 ms** |
| 50 | ★★★ `VK_LMENU` 的理由 | `VK_MENU` 也会响应右 Alt；**AltGr = 右Alt+Ctrl** |
| 51 | ★★★★★ **前台检查** | `GetAsyncKeyState` 是**全局**的；**Alt 正是 alt-tab 键** ⇒ 不检查就是**常见情况** |
| 52 | ★★★★★ **`ResolveBySenderAddress = 0`** | 客户端知道 `OLMOD_PLATFORM_USER_ID`=`0x01100001DEADC0DE`；服务端知道 **C# AuthServer 顺序号**；实测 **69420 / 69422** ↔ **...C0DE / ...C0DF** |
| 53 | ★★★ 调试电池双门禁 | `OLMOD_ZM_DEBUG_BATTERY=1` **且** host = **`127.0.0.1`** |
| 54 | ★★★★★ **`cg = table[selector] ^ 0xFBB2C97A`** | **不是** `table[localClientNum]`；实测 selector **5** / **3**；边界 **64** 是守卫非声明 |
| 55 | ★★★★★ **battery 六个偏移** | `base+0x7EC3B58` selector / `base+0x181D188+sel*4` encoded / `cg+0` commandTime / `cg+4` pmType(**==0**) / `cg+0x1A4` health(**420**) / `cg+0x158` client(**<18**) |
| 56 | ★★ `cg+0x20C` | 服务端 **Pmove 影子**,两个活客户端**都保持零** |
| 57 | ★★★★★ **`GameStateConfigurationStage` 18 个值** | 17 失败 + `Accepted` |
| 58 | ★★★★★ 为什么需要 | booking 成功 ⇒ 路径首次可达 ⇒ **帧线程停在这里** ⇒ 之前**无任何日志** |
| 59 | ★★★★★ **`DedicatedSessionConsumeStage` 17 个值** | 3 等待 + 12 失败 + `None` + `Accepted` |
| 60 | ★★★ 两个哨兵 | `failedClassIndex = **-1**` / `characterRecordIndex = **0xFFFFFFFF**` |
| 61 | ★★★ 两个 Tracker 的不一致 | `GameStateConfigurationTracker` **有** mutex；`DedicatedSessionConsumptionTracker` **无** |
| 62 | ★★★ `rewards` 三态 | `nullopt` = 失败 / **空值** = 未装备 / 有值 = 已装备 |
| 63 | ★★★ `replace()` 的 xuid-0 规则 | `members.contains(0) && members.size() != 1` ⇒ 拒 |
| 64 | ★★★★★ **`updateMember` vs `updateCharacter`** | 前者换 **classes+character**（**下次出生**生效）；后者只换 character（**下一帧**生效） |
| 65 | ★★★★★ **botclasstable.csv** | **5838 B** / sha256 **DE062FAEB2BF5577** / **9 类 / 53 行** |
| 66 | ★★★ 9 个类 | `scarsapr`+`m9` … `mp5k`+`m9`；注意 **`coltanaconda`** |
| 67 | ★★★★★ **10 个外观部件** | `charGender/BOO/FJA/FPA/HAN/HEA/VES/HEG/ELP/KNP` |
| 68 | ★★★ 外观表出处 | TF = 行 **31-40**、SC = 行 **43-51**；生成器**自校验** |
| 69 | ★★★ 全空的 SC 侧 | `charELP` 和 `charKNP` 的 SC 侧 **9 个全空** |
| 70 | ★★★★★ **"a pile of the player"** | 外观表缺失时**每个 bot 的 CHARACTER 都来自克隆的房主** |
| 71 | ★★★ `FrameHook` 顺序 | 先 `call [OriginalComFrame]` **再** `pushfd`+`pushad` ⇒ 原函数会破坏标志 |
| 72 | ★★★ 蹦床构造 | 原 5 字节 + **`E9`** 跳回 `target+5` |
| 73 | ★★★ `DisconnectWitness` 五个结果 | `NotRequested`/`Installed`/`AlreadyInstalled`/`UnexpectedBytes`/`UnsupportedHost` |
| 74 | ★★ 命名不一致 | `OLMOD_DISCONNECT_WITNESS` vs `CODOL_ANIMTREE_*` |

---

## 十三、结论

### 1. ★★★★★ **`PlayerDataDef` 用按名解析取代了 8 个手测序号**

★ **⇒ 其中 6 个在 3.3.3.3 上不同（`605/14`→`576/10`、`1607/37`→`1154/36`、`slots` `5`→`1`）。**
**⇒ 附件序号原本是 `weaponOrdinal - AttachmentCount` 的"numerology",已经错过一次。**

### 2. ★★★★★ **`playerState` 在 1649370 里从 ECX 移到了栈**

★ **⇒ 老实现把 ps 放进 ECX（没人读）,而 callee 真正读的栈槽得到的是**垃圾**。**

### 3. ★★★★★ **函数指针按槽地址加密**（`ds:0x00E60B78`）

★ **⇒ 复制缓冲区后必须 **re-key**,否则 `call ecx` 跳到随机野地址。**

### 4. ★★★★★ **`otherFlags` 的故障链解释了"无快照"**

★ **⇒ 引擎 SET 访问器把 `ps+0x10` 换成编码形式 ⇒ 每帧随机 ⇒ 快照校验器拒绝。**

### 5. ★★★★★ **`.tp3` 在 2068ms 还是密文、4065ms 已是明文**（六个精确字节串）

### 6. ★★★★★ **animtree 的 519 vs 123 用三层钩子 + 硬件写断点追查**

★ **⇒ 五个钩子站点 + 五个 alloc 调用点 + DR0 写断点（`record+20`）。**

### 7. ★★★★★ **`com_maxfps` 的 186-190 天花板有完整推导**（整数除法 + `Sleep(1)` 过冲）

### 8. ★★★★★ **noclip 的 `ResolveBySenderAddress = 0` 揭示了第三个 id 命名空间**

★ **⇒ C# AuthServer 顺序号（实测 **69420 / 69422**）≠ 平台 id ≠ DW 账号 id。**

### 9. ★★★★★ **`cg = table[selector] ^ 0xFBB2C97A`**（不是 `table[localClientNum]`）

### 10. ★★★ **三处 `18` 的上界一致**（`capacity` / `MaximumSessionMembers` / `client >= 18`）

### 11. ★★ **两个 Tracker 的 mutex 不一致**（一个有一个没有）⇒ 待核对

---

## 十四、下一步

`game_server` 根剩余大文件：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000）+ `NativeWeaponMovementBindings.cpp`（31,427）+ `.bak-20261009-scopeidle`（29,791）
4. `ClientProcessPatches.cpp`（82,545）+ `.hpp`（13,278）
5. `DedicatedProcessPatches.cpp`（39,058）
6. `ClientRenderFrameHook.cpp`（32,154）+ `.hpp`（9,126）
7. `ClientCommandTrace.cpp`（27,720）
8. `DisconnectWitness.cpp`（25,594）
9. `NativeWeaponBindings.cpp`（17,835）
10. `codol_bot_names.hpp`（16,545）
