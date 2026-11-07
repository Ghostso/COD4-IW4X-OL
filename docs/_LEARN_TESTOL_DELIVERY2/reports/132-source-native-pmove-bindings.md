# 学习报告 132（重开）— `NativePmoveBindings.cpp`（2,152 行）：服务端 pmove 的完整适配层

**学习范围**：`NativePmoveBindings.cpp`（113,000 B / **2,152 行**）——全文逐行读完
**性质**：全实测
**★★★★★ 本报告收录十四个重大发现**：①**`trace_t` 的 `0x28` 布局与 6 个 `static_assert`** ②**handler 槽的 CAS 交换** ③**`ps+0x10` 是三 dword 加密对象（含两个 cookie）** ④**访问器对**镜像**（get 键 `+0x20` 存 `+0x24`）** ⑤**`StableAccessorSelector = 0` 取代 `QPC % 33`** ⑥**`sub_403C70` 的 34 路变体 switch** ⑦**PM_Weapon 的四个门（T/F/E/P）** ⑧**`PMF_RESPAWNED` 只在**不按开火键**的帧清除** ⑨**`pmove+8` = `cmd.buttons`** ⑩**`0x014 → 0x028` 的 20 字节插入** ⑪**动画事件表的**追加而非插入** ⑫**条件偏移 `characterInfo+0x2EC+8*idx`** ⑬**`0x1800` 决定 `eType`** ⑭**`PmoveSliceTraceLimit = 64` 的 94,148 行事故**

---

## 一、★★★★★ **`trace_t` 的 `0x28` 布局**

### 1.1 ★★★★★ 六个 `static_assert`（第 24–46 行）

```cpp
struct NativeTraceResult
{
    float fraction;                  // +0x00
    std::array<float, 3> normal;     // +0x04
    std::uint32_t surfaceFlags;      // +0x10
    std::uint32_t contents;          // +0x14
    std::uint32_t hitType;           // +0x18  ★
    std::uint16_t hitId;             // +0x1C
    std::uint16_t modelIndex;        // +0x1E  ★
    std::uint16_t partName;          // +0x20  ★
    std::uint16_t partGroup;         // +0x22  ★
    std::uint8_t allSolid;           // +0x24  ★
    std::uint8_t startSolid;         // +0x25
    std::uint8_t walkable;           // +0x26
    std::uint8_t unknownEnd;         // +0x27
};

static_assert(sizeof(NativeTraceResult) == **0x28**);
static_assert(offsetof(NativeTraceResult, hitType) == **0x18**);
static_assert(offsetof(NativeTraceResult, modelIndex) == **0x1E**);
static_assert(offsetof(NativeTraceResult, partName) == **0x20**);
static_assert(offsetof(NativeTraceResult, partGroup) == **0x22**);
static_assert(offsetof(NativeTraceResult, allSolid) == **0x24**);
```

★★★★★ **⇒ 完整的 40 字节布局：**

| 偏移 | 类型 | 字段 |
|---|---|---|
| **`+0x00`** | `float` | `fraction` |
| **`+0x04`** | `float[3]` | `normal` |
| **`+0x10`** | `u32` | `surfaceFlags` |
| **`+0x14`** | `u32` | `contents` |
| **`+0x18`** | `u32` | `hitType` |
| **`+0x1C`** | `u16` | `hitId` |
| **`+0x1E`** | `u16` | `modelIndex` |
| **`+0x20`** | `u16` | `partName` |
| **`+0x22`** | `u16` | `partGroup` |
| **`+0x24`** | `u8` | `allSolid` |
| **`+0x25`** | `u8` | `startSolid` |
| **`+0x26`** | `u8` | `walkable` |
| **`+0x27`** | `u8` | `unknownEnd` |

★★★ **⇒ 六个 `static_assert` 把 `hitType` / `modelIndex` / `partName` / `partGroup` / `allSolid` 全部钉死。**

### ★★★ 无命中时的填充（第 236–244 行）

```cpp
void writeNoHitTrace(void *const result)
{
    NativeTraceResult native{};
    native.fraction = **1.0f**;      // ★ 无命中 ⇒ fraction = 1
    native.hitId = **2047**;         // ★ ENTITYNUM_NONE
    std::memcpy(result, &native, sizeof(native));
}
```

★★★ **⇒ 两个哨兵：`fraction = 1.0f`（无命中）+ `hitId = 2047`（`ENTITYNUM_NONE`）。**

---

## 二、★★★★★ **handler 槽的 CAS 交换**

### 2.1 ★★★★★ 完整注释（第 48–68 行，逐字）

```cpp
// CODREF(pmove): CODOL PM_playerTrace dispatches the **0x28-byte trace_t**
// through **`pmoveHandlers[pm->handler].trace`**. **The client image retains only
// handler 0**, so the embedded server **temporarily replaces that trace callback
// while keeping the native PmoveSingle implementation**.
...
// OLMOD(pmove-handler-swap-owner): the handler slot is **process-global**,
// while the authoritative trace inputs are **game-thread local**. Serialize
// the short swap and **route incidental foreign-thread calls back to the
// original client trace**.
```

★★★★★ **⇒ 三个精确事实：**
```
`PM_playerTrace` 通过 **`pmoveHandlers[pm->handler].trace`** 派发 **`0x28` 字节的 `trace_t`**
        ↓
★★★ **客户端镜像只保留 handler 0**
★★★ ⇒ 服务端**临时替换**那个 trace 回调,**保留原生 `PmoveSingle`**
        ↓
★★★ 槽是**进程全局**,而权威 trace 输入是**游戏线程本地**
★★★ ⇒ 必须**串行化短暂交换**,并把**外来线程调用路由回原客户端 trace**
```

### ★★★★★ **CAS 交换（第 751–760 行）**

```cpp
const auto expectedBits = (LONG)(uintptr_t)expectedTrace;      // 客户端原 trace
const auto callbackBits = (LONG)(uintptr_t)&SV_ServerPmoveTrace;
auto *const slot = (volatile LONG*)handlerSlot;
if (InterlockedCompareExchange(slot, callbackBits, expectedBits) != expectedBits)
    return SvNativePmoveFailure::**HandlerSlotBusy**;
```

★★★ **⇒ 交换是**比较并交换**：只有当前值**等于客户端原 trace** 才换成我们的。**

### ★★★★★ **恢复在 `__finally` 里**（第 868–873 行）

```cpp
__finally
{
    MemoryBarrier();
    traceRestored = InterlockedCompareExchange(slot, **expectedBits**, **callbackBits**) == callbackBits;
}
```

★★★ **⇒ 两条关键：**
```
① **`MemoryBarrier()`** 在恢复之前
② **`__finally`** ⇒ **即使 `__leave` 或异常也会恢复**
③ 恢复失败 ⇒ **`HandlerRestoreFailed`**（第 889–890 行）
```

### ★★★ 外来线程的兜底（第 399–408 行）

```cpp
auto *const context = activeServerPmoveTrace;      // ★ thread_local
if (!context)
{
    const auto fallback = clientPmoveTraceFallback.load(std::memory_order_acquire);
    if (fallback) fallback(result, start, end, bounds, passEntityNum, contentMask);
    else writeNoHitTrace(result);
    return;
}
```

★★★ **⇒ 三层兜底：`thread_local` context → `clientPmoveTraceFallback` → `writeNoHitTrace`。**

---

## 三、★★★★★ **`ps+0x10` 是三 dword 加密对象**

### 3.1 ★★★★★ 完整注释（第 1085–1120 行，逐字）

```cpp
// **playerState +0x10 IS NOT A PLAIN DWORD ON THIS BUILD.**
//
// ol-mod stores **otherFlags** there as a plaintext uint32, and **nothing in this tree
// maps 0x14, 0x18, 0x1C, 0x20 or 0x24 at all**. That gap is the shape of the answer:
// **ps+0x10 is a THREE-DWORD PROTECTED VALUE whose accessor pair lives at ps+0x20/+0x24**,
// and **the engine only ever reads it through the getter**.
//
// **BG_PlayerStateToEntityState, sub_411360 at 0x0041143E**:
//     **lea  eax, [esi+10h]**        ; the protected object
//     **lea  ecx, [eax+10h]**        ; ps+0x20, the paired ADDRESS
//     **xor  ecx, [eax+14h]**        ; ^ the stored dword at ps+0x24
//     **xor  ecx, ds:0x00E60B78**    ; ^ the get key
//     **push edx / push eax / call ecx**
//     **mov  eax, [ebp-0Ch]**        ; the SECOND dword of the plaintext
//     **test eax, 1800h**            ; bits 11 and 12
//     **sete al / lea eax, [eax*4+1]**
//     **mov  [edi+4], eax**          ; **eType = 1 (ET_PLAYER) or 5 (ET_INVISIBLE)**
//
// So a server that writes the flags plaintext gets them decoded into noise, the
// **0x1800 test fails**, and **every player is published as ET_INVISIBLE**. That is
// exactly what the live log said: **`converted state mismatch eType converted=5
// playerState=1`**, and **5 is ET_INVISIBLE in this build's own etype dispatch table**.
```

★★★★★ **⇒ 六个精确值：**
```
`ps+0x10` = **三 dword 的加密对象**
访问器对在 **`ps+0x20`（存地址）/ `ps+0x24`（存 dword）**
        ↓
★★★ `sub_411360 @ 0x0041143E` 的完整序列：
   `lea eax, [esi+10h]`      ⇒ 对象
   `lea ecx, [eax+10h]`      ⇒ **`ps+0x20`**
   `xor ecx, [eax+14h]`      ⇒ **^ `ps+0x24`**
   `xor ecx, ds:0x00E60B78`  ⇒ **^ get 键**
   `call ecx`
   `mov eax, [ebp-0Ch]`      ⇒ **明文第 2 个 dword**
   `test eax, 1800h`         ⇒ **bit 11 和 12**
   `sete al / lea eax,[eax*4+1]`
   `mov [edi+4], eax`        ⇒ **`eType = 1`(ET_PLAYER) 或 `5`(ET_INVISIBLE)**
        ↓
★★★ ⇒ 明文写入 ⇒ 解码成噪声 ⇒ `0x1800` 测试失败 ⇒ **所有玩家发布为 ET_INVISIBLE**
★★★ 实测日志：**`converted state mismatch eType converted=5 playerState=1`**
```

### ★★★★★ **setter 侧是镜像的**（第 1108–1116 行，逐字）

```cpp
// The set side is read from the engine's own playerState initializer **sub_5BEB50**,
// which loops at the **0x3BBC** playerState stride, at **0x005BEEC3**:
//     **lea  eax, [eax+ebx+10h]**    ; the same object
//     **lea  edi, [eax+14h]**        ; ps+0x24, the paired ADDRESS
//     **xor  edi, [eax+10h]**        ; ^ the stored dword at ps+0x20
//     **xor  edi, ds:0x00E60B74**    ; ^ the SET key -- the other cookie
//     **push ecx / push edx / call edi / add esp, 8**   ; set(value, object), cdecl
// **Note the two sides are MIRRORED: the getter is keyed on ps+0x20 and stores at
// ps+0x24, the setter is keyed on ps+0x24 and stores at ps+0x20.**
```

★★★★★ **⇒ 完整的镜像表：**

| 侧 | 键位置 | 存位置 | cookie |
|---|---|---|---|
| **getter** | ★ **`ps+0x20`** | ★ **`ps+0x24`** | ★ **`ds:0x00E60B78`** |
| **setter** | ★ **`ps+0x24`** | ★ **`ps+0x20`** | ★ **`ds:0x00E60B74`** |

★★★ **⇒ 两个 cookie 相差 **4 字节**（`B78` vs `B74`）。**
**⇒ 且 `sub_5BEB50` 的循环步长 = **`0x3BBC`**（playerState 大小，与报告 126 **一致** ✓）。**

### ★★★★★ **getter 与 setter 的参数顺序相反**（第 1176–1182 行，逐字）

```cpp
// **THE GETTER, WHICH SECTION 44d DELIBERATELY LEFT UNMODELLED.** Its ABI is read
// straight off **PmoveSingle at 0x0041CBCE**, where the engine does exactly this:
//     **v4 = dword_E60B78 ^ (unsigned)(ps + 0x20) ^ *(ps + 0x24);**
//     **v4(ps + 0x10, out);**        // **__cdecl(object, outBuffer), caller cleans 8**
// **Note the get and set sides take their arguments in OPPOSITE orders -- get is
// (object, out) and set is (value, object)** -- which is of a piece with the pair
// itself being mirrored (section 43j).
```

★★★ **⇒ 两个 ABI：**
```
get：**`__cdecl(object, out)`**
set：**`__cdecl(value, object)`**
        ↓
★★★ ⇒ **参数顺序相反**
```

### ★★★★★ **`writeNativeProtectedPlayerStateFlags` 的实现**（第 1121–1170 行）

```cpp
auto *const object = bytes + **0x010**;
std::uint32_t storedSet{};
std::memcpy(&storedSet, object + **0x10**, sizeof(storedSet));           // ★ ps+0x20
const auto pairedAddress = (uint32_t)(uintptr_t)(object + **0x14**);     // ★ ps+0x24 的地址
auto *const setFunction = (void*)(storedSet ^ pairedAddress ^ *nativePlayerStateAccessorSetKey_);
std::uint32_t flags{};
std::memcpy(&flags, object, sizeof(flags));                              // ★ ps+0x10
plaintextFlags = flags;                                                  // ★ 保存明文
std::array<std::uint32_t, 3> value{ **0**, **flags**, **0** };            // ★ 只有第 2 个 dword
...
__asm
{
    mov eax, object        // ★ 参数 2 = object
    push eax
    mov ecx, valueBytes    // ★ 参数 1 = value
    push ecx
    mov edx, setFunction
    call edx
    add esp, 8
}
```

★★★★★ **⇒ 六个精确细节：**
```
① 解出 setter：**`storedSet ^ (object+0x14 的地址) ^ setKey`**
② 明文是 **`object[0]`**（= `ps+0x10`）
③ 传给 setter 的 value = **`{0, flags, 0}`**（**只有第 2 个 dword 非零**）
④ 参数顺序：**`push value` 然后 `push object`** ⇒ 栈上是 `(value, object)` ✓
⑤ `add esp, 8`（2 个参数）
⑥ **`plaintextFlags = flags`** 供调用者在调用后恢复
```

### ★★★★★ **`readNativeProtectedPlayerStateFlags`**（第 1183–1217 行）

```cpp
std::uint32_t storedGet{};
std::memcpy(&storedGet, object + **0x14**, sizeof(storedGet));           // ★ ps+0x24
const auto pairedAddress = (uint32_t)(uintptr_t)(object + **0x10**);     // ★ ps+0x20 的地址
auto *const getFunction = (void*)(storedGet ^ pairedAddress ^ *nativePlayerStateAccessorGetKey_);
...
__asm
{
    mov ecx, valueBytes
    push ecx               // ★ 参数 2 = out
    mov eax, object
    push eax               // ★ 参数 1 = object
    mov edx, getFunction
    call edx
    add esp, 8
}
if (completed) **flags = value[1]**;      // ★ 第 2 个 dword
```

★★★ **⇒ 与 setter **完全镜像**：读 `+0x14`,用 `+0x10` 的地址,`(object, out)` 顺序,取 `value[1]`。**

---

## 四、★★★★★ **`StableAccessorSelector = 0` 取代 `QPC % 33`**

### 4.1 ★★★★★ 完整注释（第 1256–1307 行，逐字）

```cpp
// **AN ADDRESS-KEYED POINTER DOES NOT SURVIVE BEING COPIED.**
//
// CODOL stores a function pointer as **key ^ function ^ THE PAIRED SLOT'S OWN ADDRESS**,
// so **the encoding is only valid at the address it was written at**. Every
// `auto candidate = state;` in this project **relocates the playerState into a new buffer**,
// and **the pair inside it silently stops decoding to a function**.
//
// That is measured, not argued. ... with a relocated pair the dedicated **jumped somewhere
// different on every single command -- 0x00198A90 (its own stack), 0x00DAF2AC (a data table),
// 0x0041144C (its own code)** -- with **0xC0000096 privileged-instruction faults** from
// executing whatever it landed on. **A MOVING FAULT ADDRESS IS THE SIGNATURE OF A ZEROED
// OBFUSCATED SLOT**; this project had that written down. **What it did not have was the rule
// that COPYING THE BUFFER causes the same thing.**
```

★★★★★ **⇒ 与报告 126 的三个野地址**完全一致** ✓**
**⇒ 且新增：`0xC0000096` = **特权指令故障**（执行了非代码）。**

### ★★★★★ **`sub_403C70` 的 34 路变体**（第 1282–1306 行，逐字）

```cpp
// **THE SELECTOR PICKS AN ACCESSOR VARIANT, AND A VALUE ENCODED WITH ONE VARIANT CAN ONLY
// BE DECODED WITH THAT VARIANT.** It must not be random.
//
// **sub_403C70 is a 34-way switch -- cases 0..32 plus a default** -- and each case installs
// a DIFFERENT getter/setter pair:
//     **case 0:  *set = key ^ sub_401720 ^ addr;   *get = key ^ sub_4017C0 ^ addr;**
//     **case 1:  *set = key ^ sub_401840 ^ addr;   *get = key ^ sub_4018D0 ^ addr;**
//     ...
// The pairs are **the same SHAPE** -- **read three dwords, xor with the object's own
// address bytes and a key triple, write three dwords** -- but **not the same FUNCTION**.
// **sub_4017C0 uses keys 0x00E60224/0x00E609A0/0x00E609A4** and one permutation of the
// address bytes; **sub_4018D0 uses 0x00E609A8/0x00E609AC/0x00E609B0** and a different
// permutation. **Ciphertext written by one is noise to the other.**
//
// This used to be **`(QueryPerformanceCounter ^ buffer address) % 33`**, a fresh random
// variant on **EVERY call** -- and this is called **once per pmove slice, again in the
// converter, and again in runServerAnimationEvent**. So whatever the engine stored through
// one variant was **read back through another**, and the result **differed run to run and
// frame to frame**. That is the shape of **the viewmodel being wrong on some cycles and
// right on others with no code change between them**, and of **groundEntityNum answering
// two ways at one origin**.
//
// **A fixed variant is self-consistent: the choice is stored IN the slot**, so whatever is
// installed is what the engine uses to decode.
constexpr std::uint32_t StableAccessorSelector = **0**;
```

★★★★★ **⇒ 七个精确值：**
```
`sub_403C70` = **34 路 switch**（`case 0..32` + default）
        ↓
★★★ **case 0**：`*set = key ^ sub_401720 ^ addr` / `*get = key ^ sub_4017C0 ^ addr`
★★★ **case 1**：`*set = key ^ sub_401840 ^ addr` / `*get = key ^ sub_4018D0 ^ addr`
        ↓
★★★ 所有对**形状相同**（读 3 dword、xor 地址字节 + 键三元组、写 3 dword）但**函数不同**
★★★ `sub_4017C0` 用键 **`0x00E60224` / `0x00E609A0` / `0x00E609A4`**
★★★ `sub_4018D0` 用键 **`0x00E609A8` / `0x00E609AC` / `0x00E609B0`**
        ↓
★★★★★ ⇒ **一个变体写的密文对另一个是噪声**
        ↓
★★★ 旧实现：**`(QueryPerformanceCounter ^ buffer address) % 33`** ⇒ **每次调用都是新变体**
★★★ 而它**每 pmove 切片调用一次 + 转换器一次 + `runServerAnimationEvent` 一次**
        ↓
★★★ ⇒ 结果**逐次运行、逐帧不同**
★★★ ⇒ **视图模型某些周期错、某些周期对,而代码没变**
★★★ ⇒ **`groundEntityNum` 在同一原点给出两种答案**
        ↓
★★★ 修复：**`StableAccessorSelector = 0`**（固定变体,选择**存在槽里**）
```

### ★★★ `invokeNativePlayerStateAccessorInitialize` 的 ABI（第 919–940 行）

```cpp
auto *const encodedSet = playerState + **0x020**;
auto *const encodedGet = playerState + **0x024**;
__asm
{
    push edi
    push setKey
    push encodedSet
    push encodedGet
    push selector
    mov eax, encodedSet      // ★ SET 槽
    mov edx, getKey          // ★ get 键
    mov edi, encodedGet      // ★ GET 槽
    mov ecx, function
    call ecx
    add esp, 16              // ★ 4 个参数
    pop edi
}
```

★★★ **⇒ 五个精确事实：**
```
① **4 个栈参数**：`selector` / `encodedGet` / `encodedSet` / `setKey`（从右到左）
② **`eax` = SET 槽**（`ps+0x20`）
③ **`edi` = GET 槽**（`ps+0x24`）
④ **`edx` = get 键**
⑤ 第一个 push 是 **setKey**（第 3 个参数）
```

★★★ **⇒ 注释（第 896–901 行，逐字）：**
```
"This is the same encoder and the same register/stack convention as the **characterInfo
 lerp frames** -- **eax and the third push are the SET slot, edi and the second push are the
 GET slot, edx is the get key and the first push is the set key** -- but the slots live in the
 playerState and are keyed on **two different cookies**."
```

---

## 五、★★★★★ **PM_Weapon 的四个门（T/F/E/P）**

### 5.1 ★★★★★ `sub_42AED0` 的完整反汇编（第 548–560 行，逐字）

```
// **PmoveSingle calls PM_Weapon = sub_42B4E0 unconditionally at 0x0041D263.**
// **PM_Weapon's FIRST act is `sub_42AED0(ps)`**; **a non-zero return takes the long
// weapon-think branch at 0x0042B597** and **a zero return takes a short one that cannot
// fire**. sub_42AED0 is small enough to read whole:
//
//   **cmp dword [ps+04h], 8**       ; **pm_type >= 8 -> also zeroes ps+3F8h and returns 0**
//   **jl  ...**
//   **test dword [ps+0Ch], 400h**   ; **pm_flags  -> returns 0**
//   **test dword [ps+104h], 0C00h** ; **eFlags    -> returns 0**
//   **<obfuscated read of the PROTECTED value at ps+10h>**
//   **shr eax, 1Eh / and al, 1**    ; **BIT 30 of the second dword**
//   **test dl, dl / sete al**       ; **return !bit30**
```

★★★★★ **⇒ 四个门的完整表：**

| # | 门 | 条件 | 后果 |
|---|---|---|---|
| **T** | `pm_type` | ★ **`>= 8`** | **返回 0**（并清零 `ps+0x3F8`） |
| **F** | `pm_flags` | ★ **`& 0x400`** | **返回 0** |
| **E** | `eFlags` | ★ **`& 0xC00`** | **返回 0** |
| **P** | protected | ★ **bit 30 置位** | **返回 0** |

★★★ **⇒ 四个**全部为假**时武器才会思考（`return !bit30`）。**

### ★★★★★ **探针的四字母输出**（第 1784–1792 行）

```cpp
const char gate[5] = {
    probePmType  >= **8**   ? '**T**' : '-',
    (probePmFlags & **0x400**) ? '**F**' : '-',
    (probeEFlags  & **0xC00**) ? '**E**' : '-',
    ((probeProtected >> **30**) & 1u) ? '**P**' : '-',
    '\0',
};
```

★★★ **⇒ 输出形如 `gate=TFE-` 或 `gate=----`。**
**⇒ `gate=----` 表示**四个门都通过** ⇒ 引擎被允许思考但什么也没做 ⇒ **这是一个真实发现**。**

### ★★★★★ **`PMF_RESPAWNED` 只在**不按开火键**的帧清除**（第 568–586 行，逐字）

```cpp
// OLMOD(section-86): **AND THE PROBE MUST RELEASE THE TRIGGER BEFORE IT PULLS IT.** The
// gate that actually refused was **`pm_flags & 0x400`**, on every frame of every window,
// and **PmoveSingle clears that bit in exactly ONE place** -- **0x0041CEA6 on out.exe,
// 0x0041DDBB on 3.3.3.3**, identical logic:
//
//     **cmp dword [ps+04h], 8**            pm_type < 8
//     **jge  skip**
//     **test dword [pmove+8], 101h**       **cmd.buttons & 0x101**
//     **jne  skip**
//     **and dword [ps+0Ch], 0FFFFFBFFh**   **clear PMF_RESPAWNED**
//
// **`pmove+8` is cmd.buttons.** So **the respawn latch clears only on a frame where NEITHER
// bit 0 (fire) NOR bit 8 is held** -- and **this probe held bit 0 from its very first frame,
// so the latch never cleared and PM_Weapon refused for the whole window**. **A person
// releases the trigger between magazines without thinking about it**, which is why **their
// fire worked and 120 injected frames did not**.
```

★★★★★ **⇒ 六个精确值：**
```
清除点：**`0x0041CEA6`（out.exe）/ `0x0041DDBB`（3.3.3.3）**
        ↓
★★★ 条件：`pm_type < 8` **且** **`!(cmd.buttons & 0x101)`**
★★★ 动作：`and [ps+0x0C], 0xFFFFFBFF` ⇒ **清 `PMF_RESPAWNED`（bit 10 = 0x400）**
        ↓
★★★ **`pmove+8` = `cmd.buttons`**（`pmove.cmd` 在 `pmove+4`,`buttons` 在 `cmd+4`）
        ↓
★★★★★ ⇒ **闩锁只在既不按 bit 0（开火）也不按 bit 8 的帧清除**
★★★ ⇒ **探针从第 1 帧就按住 bit 0 ⇒ 闩锁永不清除 ⇒ `PM_Weapon` 整个窗口拒绝**
★★★ ⇒ **真人换弹匣时会自然松扳机** ⇒ **人的开火有效,120 帧注入无效**
```

### ★★★ **`BulletFireProbeReleaseFrames = 12`**（第 586 行）

```cpp
inline constexpr std::uint32_t BulletFireProbeReleaseFrames = **12**;
inline constexpr std::uint32_t BulletFireProbeFrames = **120**;
```

### ★★★★★ **`pmove+8` = `cmd.buttons` 的 layout 论证**（第 521–530 行，逐字）

```cpp
// OLMOD(section-85): **AND `cmdOut` IS NOT A DIFFERENT COPY.** It is
// **`pmove.cmd.buttons` read AFTER invokeNativeServerPmove returns**, and the
// **adapter's own two gates mutate that field in place** -- so **cmdOut=1 means the bit
// survived both of them and was live in the pmove_t at the moment PmoveSingle was called**.
// Section 80a's conclusion that this writes "a copy PM_Weapon does not read" **does not
// survive the layout**: **pmove.cmd is at pmove+4 and buttons at +4 of that**,
// **static_asserted in sv_native_pmove_mp.hpp**, which is **exactly where the engine looks**.
// **What was missing was never the write; it was any way to see WHICH gate refused**, and
// **the probe prints all four of them now**.
```

★★★ **⇒ 精确布局：`pmove.cmd` @ **`pmove+4`**；`cmd.buttons` @ **`pmove+8`**。**

---

## 六、★★★★★ **`0x014 → 0x028` 的 20 字节插入**

### 6.1 ★★★★★ 完整注释（第 733–740 行，逐字）

```cpp
// CODDIFF(1649370): **0x014 -> 0x028. OLfinal inserts 20 bytes into playerState
// between +0x10 and this field**: the netfield tables pair them on
// **(3 bits, same codec)** at **A 0x014 / C 0x028**, and **both neighbours corroborate it
// independently** -- **the field above is otherFlags, which changed codec in place at
// +0x10**, and **the field below is bobCycle, which section 34 had already moved
// 0x018 -> 0x02C from the other direction**.
constexpr std::size_t PmoveControlFlagsOffset = **0x028**;
```

★★★★★ **⇒ 四个精确值：**
```
`PmoveControlFlags`：3.3.3.3 **`0x014`** → 1649370 **`0x028`**
        ↓
★★★ 理由：**OLfinal 在 `+0x10` 和该字段之间插入了 20 字节**
★★★ 证据：netfield 表把它们配成 **（3 位,同一编解码器）** 在 **A `0x014` / C `0x028`**
        ↓
★★★ **两个邻居独立佐证**：
   上方 = **`otherFlags`**,在 **`+0x10`** 处**原地换了编解码器**
   下方 = **`bobCycle`**,section 34 已从另一方向确认 **`0x018` → `0x02C`**
```

★★★ **⇒ 三个偏移的完整对照：**

| 字段 | 3.3.3.3 | 1649370 |
|---|---|---|
| **`otherFlags`** | `0x010` | ★ **`0x010`**（原地换 codec） |
| **`PmoveControlFlags`** | **`0x014`** | ★ **`0x028`** |
| **`bobCycle`** | **`0x018`** | ★ **`0x02C`** |

### ★★★ 六个常量（第 730–743 行）

```cpp
constexpr std::size_t CommandTimeOffset = **0x000**;
constexpr std::size_t PmTypeOffset      = **0x004**;
constexpr std::size_t PmFlagsOffset     = **0x00C**;
constexpr std::size_t PmoveControlFlagsOffset = **0x028**;
constexpr std::int32_t MaximumBacklog = **1000**;
constexpr std::int32_t MaximumSlice   = **66**;
constexpr std::uint32_t MaximumSlices = **16**;
```

★★★ **⇒ 三个时间常量：**
```
`MaximumBacklog = **1000**`（ms）
`MaximumSlice = **66**`（ms）
`MaximumSlices = **16**`（= ceil(1000/66)）
        ↓
★★★ 注释（第 821–824 行）："after the native **1000 ms clamp**, **ceil(1000 / 66) is 16**.
 The explicit guard only fails a corrupted/non-advancing reconstruction; **it does not reduce
 the CODOL driver's valid domain**."
```

### ★★★ 两个命令门（第 780–795 行）

```cpp
const auto pmFlags = readNativeInt(pmove->playerState, PmFlagsOffset);
if ((pmFlags & **0x80000**) != 0 || (pmove->cmd.buttons & **0x200000**) != 0)
{
    pmove->cmd.buttons &= **0x80300**;      // ★ 只保留 bit 8,9,19
    pmove->cmd.forwardMove = 0;
    pmove->cmd.rightMove = 0;
}
if ((readNativeInt(pmove->playerState, PmoveControlFlagsOffset) & **4**) != 0)
{
    pmove->cmd.buttons &= **0xFFFFFBF9**;   // ★ 清 bit 1,2,10
    pmove->cmd.forwardMove = 0;
    pmove->cmd.rightMove = 0;
}
```

★★★ **⇒ 两个门与两个掩码：**
```
门 1：`pm_flags & **0x80000**` 或 `cmd.buttons & **0x200000**`
      ⇒ `buttons &= **0x80300**`（保留 **bit 8, 9, 19**）
        ↓
门 2：`PmoveControlFlags & **4**`
      ⇒ `buttons &= **0xFFFFFBF9**`（清 **bit 1, 2, 10**）
```

---

## 七、★★★★★ **动画事件表的**追加而非插入**

### 7.1 ★★★★★ 完整注释（第 1378–1401 行，逐字）

```cpp
// OLMOD(section-84): **THE ID IS NOW READ OFF 1649370**. This comment used
// to say "event 7 in THIS BUILD'S OWN event table at **VA 0x00CE4A20**" and
// **0x00CE4A20 IS 3.3.3.3's TABLE** -- out.exe's own **0x00CE4A20 is .rdata
// holding IME strings ("RemoveList", "RepositionCandWindow")**. That is
// **section 81a's rebase hazard in its other form**: an address that is real
// on ONE image, described as the host's.
//
// **out.exe's table is at VA 0x00E60410**. Same 8-byte entry
// `{const char *name, 0xFFFFFFFF}`, same order, and **ENTRIES 0..32 ARE
// NAME-FOR-NAME IDENTICAL to 3.3.3.3's 0x00CE4A20**:
//
//   0 **PAIN**   1 **DEATH**   2 **FIREWEAPON**   3 **JUMP**   4 **JUMPBK**   5 **LAND**
//   6 **DROPWEAPON**   7 **RAISEWEAPON**   8 **CLIMBMOUNT** ... 32 **SPAWN**
//
// **1649370 APPENDS seven and inserts none** -- **33 HOLDFIRE, 34 HOLDFIRELOOP,
// 35 HOLDFIRECANCEL, 36 SIDEROLLING_LEFT, 37 SIDEROLLING_RIGHT,
// 38 ADSTURRET_DEPLOY, 39 ADSTURRET_UNDEPLOY** -- so **7 is correct and is
// now a MEASUREMENT rather than an inheritance**.
//
// **AND THAT IS THE OPPOSITE OUTCOME TO SECTION 80 ON THE SAME BUILD.** The
// predictable-event enum **INSERTED entries and shifted eight ids**; this
// one **appended**. **"1649370 shifted the enums" is not a build-wide rule --
// it is PER TABLE, so every enum has to be read, and an identical answer
// is worth as much as a different one.**
```

★★★★★ **⇒ 八个精确值：**
```
错误地址：**`0x00CE4A20`** 是 **3.3.3.3 的表**
        ↓
★★★ out.exe 的 `0x00CE4A20` 是 **.rdata 里的 IME 字符串**（"RemoveList" / "RepositionCandWindow"）
        ↓
★★★ 正确地址：**`VA 0x00E60410`**
★★★ 条目 = **8 字节** `{const char *name, 0xFFFFFFFF}`
★★★ **条目 0..32 与 3.3.3.3 的 0x00CE4A20 逐名相同**
        ↓
★★★ 0 PAIN / 1 DEATH / 2 FIREWEAPON / 3 JUMP / 4 JUMPBK / 5 LAND /
   6 DROPWEAPON / **7 RAISEWEAPON** / 8 CLIMBMOUNT / ... / **32 SPAWN**
        ↓
★★★ **1649370 追加了 7 个,没有插入**：
   **33 HOLDFIRE / 34 HOLDFIRELOOP / 35 HOLDFIRECANCEL /
    36 SIDEROLLING_LEFT / 37 SIDEROLLING_RIGHT /
    38 ADSTURRET_DEPLOY / 39 ADSTURRET_UNDEPLOY**
```

### ★★★★★ **"不是 build 级规则,是**每表**规则"**

```
section 80：**可预测事件枚举** ⇒ **插入条目,8 个 id 移位**
section 84：**动画事件表** ⇒ **追加,0 移位**
        ↓
★★★★★ ⇒ **"`1649370 shifted the enums` 不是 build 级规则 —— 它是**每表**的"**
★★★ ⇒ **每个枚举都必须读,而"答案相同"和"答案不同"同样有价值**
```

### ★★★ 两个事件 id（第 1351 / 1402 行）

```cpp
constexpr std::int32_t AnimEventDeath = **1**;
constexpr std::int32_t AnimEventRaiseWeapon = **7**;
```

### ★★★★★ **`-1` 的两个原因**（第 1518–1525 行，逐字）

```cpp
// **-1 IS THE ENGINE SAYING "NO ANIMATION MATCHED", AND IT HAS EXACTLY TWO CAUSES.**
// **sub_407790 walks the sets in scriptEvents[event]** and **returns without writing its
// out-parameter** either when **the event has no sets at all**, or when **every set's
// conditions fail against this client's characterInfo**. **A zeroed characterInfo fails
// EVERY condition of either type**, so **"the conditions were never computed" and "this build
// has no animation for this event" are indistinguishable from the return value.**
```

★★★ **⇒ 两个原因：`numItems <= 0`（`0x004077B0`）/ 所有 set 的条件都失败。**

### ★★★★★ **`sub_407980` 拒绝事件的判据**（第 1472–1483 行，逐字）

```cpp
// **BG_AnimScriptEvent's tail (out.exe sub_407980) decodes that word and refuses the whole
// event when bit 0x20000000 comes back set**, clearing the animation index on its way out:
//
//     **if (legs & 0x3FF) legs = ((((legs>>10)&3)+1)%4) << 10;**
//     **return -1;**
//
// which is **BOTH halves of the signature at once** -- **durationMs=-1 AND
// ps legs=2048/3072/1024/0**, band kept and index gone. Measured on a real death with
// **`Tools/olfinal/anim-event-flag-probe.py`**: **the word decoded to 0xe4001126, which is
// our 0x1000 read as ciphertext**. Not a flag -- **noise**, and **about half of all noise
// has bit 29 set**.
```

★★★★★ **⇒ 四个精确值：**
```
拒绝条件：**bit `0x20000000`（bit 29）置位**
        ↓
★★★ 清索引公式：**`legs = ((((legs>>10)&3)+1)%4) << 10`**
★★★ 返回 **`-1`**
        ↓
★★★ 实测：明文 **`0x1000`** 被当密文读 ⇒ 解码成 **`0xe4001126`**
★★★ ⇒ **`0xe4001126 >> 29` = 7 ⇒ bit 29 置位** ✓
★★★ ⇒ **"约一半的噪声有 bit 29 置位"** ⇒ **每次死亡是抛硬币**
```

### ★★★★★ **"为什么这个 bug 从八月活到现在"**（第 1485–1492 行，逐字）

```cpp
// **WHICH IS WHY THIS SURVIVED SINCE AUGUST.** sect.171f measured **failures
// interleaving with successes minutes apart on both sides of every commit**; sect.171i
// recorded **"works 6/6 and no fix explains it"**. **A coin flip per death is what a
// garbage decode looks like**, and **any edit that moves a buffer re-rolls it** -- so
// **every recurrence read as a fresh regression from whatever changed last, mine included**.
// **The condition hunt could not converge either: DEATH set 23 carries zero conditions and
// matches unconditionally, so the walk was never the failure.**
```

★★★★★ **⇒ 四个精确事实：**
```
sect.171f：**失败与成功相隔几分钟交错**,在**每次提交的两侧**
sect.171i：**"works 6/6 and no fix explains it"**
        ↓
★★★ ⇒ **每次死亡抛硬币 = 垃圾解码的样子**
★★★ ⇒ **任何移动缓冲区的编辑都会重掷硬币** ⇒ **每次复发都被读成"上次改动引入的新回归"**
        ↓
★★★ ⇒ **条件追查也无法收敛：DEATH set 23 零条件,无条件匹配** ⇒ **遍历从来不是失败点**
```

### ★★★ 条件偏移的完整校准（第 1341–1350 行，逐字）

```cpp
// **THE OFFSETS ARE CALIBRATED, NOT ASSUMED.** Conditions live at
// **characterInfo + 0x2EC + 8*index**. This tree's own
// **CharacterInfoMoveTypeConditionOffset is 0x304**, which is **0x18 past the base --
// exactly three entries** -- and **MOVETYPE is entry 3 of out.exe's condition name table at
// 0x00E60828**. Its **parallel type table at 0x00E608C8** then agrees name-for-values on
// every populated entry: **1 WEAPONCLASS -> RIFLE/SNIPER/MG**, **7 WEAPON_POSITION ->
// HIP/ADS**, **11 HITLOCATION -> HIT_TORSO/HEAD/NECK/LEGS**. So **10/11/12 are
// DAMAGETYPE / HITLOCATION / HITDIRECTION** and their **condType is 1, ANIM_CONDTYPE_VALUE**
// -- **plain integers, not the bitflags MOVETYPE uses**.
```

★★★★★ **⇒ 七个精确值：**
```
条件基址 = **`characterInfo + 0x2EC`**,步长 **8**
        ↓
★★★ 校准：本树 `CharacterInfoMoveTypeConditionOffset = **0x304**`
★★★ `0x304 - 0x2EC = **0x18**` ⇒ **正好 3 个条目**
★★★ 而 **MOVETYPE 是 `0x00E60828` 条件名表的条目 3** ✓
        ↓
★★★ 并行类型表 **`0x00E608C8`** 逐值一致：
   **1 WEAPONCLASS → RIFLE/SNIPER/MG**
   **7 WEAPON_POSITION → HIP/ADS**
   **11 HITLOCATION → HIT_TORSO/HEAD/NECK/LEGS**
        ↓
★★★ ⇒ **`10` = DAMAGETYPE / `11` = HITLOCATION / `12` = HITDIRECTION**
★★★ 且它们的 **`condType = 1`（`ANIM_CONDTYPE_VALUE`）** ⇒ **纯整数,不是 MOVETYPE 用的位标志**
```

### ★★★ 三个条件的写入（第 1407–1437 行）

```cpp
constexpr std::size_t CharacterInfoSlotOffset = **0x158**;   // ★ clientNum
constexpr std::size_t ConditionBaseOffset = **0x2EC**;
constexpr std::size_t ConditionStride = **8**;
constexpr std::size_t DamageTypeCondition = **10**;
constexpr std::size_t HitLocationCondition = **11**;
constexpr std::size_t HitDirectionCondition = **12**;
...
const std::uint64_t widened = value;      // ★ 写 8 字节
std::memcpy(characterInfo.data() + 0x2EC + condition * 8, &widened, 8);
```

★★★ **⇒ 每个条件占 **8 字节**（`uint64`）,只写低 4 字节的有效值。**

---

## 八、★★★★★ **`invokeNativeAnimScriptEvent` 的 EDI 错误**

### 8.1 ★★★★★ 完整注释（第 976–992 行，逐字）

```cpp
// **THE PLAYERSTATE IS IN EDI ON THIS BUILD, NOT EAX.** sub_407E10's very
// first use of a register it never wrote is **`mov ecx, [edi+158h]`** --
// **ps+0x158 is ClientNumOffset here** -- and it turns that into
// **`dword_827F730 + 0x450*clientNum + 0xAF350`**, the characterInfo entry,
// which it hands to **sub_407790** to resolve the anim. **EAX is dead on
// entry: 0x407E26 `lea eax, [ebp+var_4]` overwrites it before any read.**
//
// So the **3.3.3.3 convention this was carried from (EAX = playerState, 0x004096D0)**
// left **EDI holding whatever the compiler last put there**. The read does not fault
// reliably -- **it lands wherever EDI points, and __except swallows it when it does** --
// so the symptom is **a spawn animation that silently does not happen, or happens off the
// WRONG client's characterInfo, differently on every run**.
//
// **ESI is a real input too and was already correct**: **0x407E1C `imul ecx, 204h`** scales
// it by **AnimScriptItemsStride** to index the script-event array at
// **animScriptData + 0x25F80**.
```

★★★★★ **⇒ 七个精确值：**
```
`sub_407E10` 第一条用到未写寄存器的指令 = **`mov ecx, [edi+158h]`**
        ↓
★★★ `ps+0x158` = **ClientNum**
★★★ 变换成 **`dword_827F730 + 0x450*clientNum + 0xAF350`** ⇒ **characterInfo 条目**
★★★ 交给 **`sub_407790`** 解析动画
        ↓
★★★ **EAX 在入口已死**：`0x407E26 lea eax, [ebp+var_4]` **在任何读之前覆盖它**
        ↓
★★★ 3.3.3.3 约定（`0x004096D0`：EAX = playerState）⇒ **EDI 留着编译器上次放的东西**
★★★ 读不一定会崩（**落在 EDI 指向的任何地方,`__except` 吞掉**）
★★★ ⇒ 症状：**出生动画静默不发生,或发生在**别的客户端**的 characterInfo 上,每次运行不同**
        ↓
★★★ **ESI 是真输入且本来是对的**：`0x407E1C imul ecx, 204h` ⇒ **`AnimScriptItemsStride = 0x204`**
★★★ 索引 `animScriptData + 0x25F80` 的脚本事件数组
```

### ★★★ 正确的调用（第 993–1004 行）

```cpp
__asm
{
    push seed         // ★ 参数 3（randomSeed*）
    push force        // ★ 参数 2
    push isContinue   // ★ 参数 1
    mov esi, event    // ★ ESI = 事件号
    mov edi, nativeState   // ★ EDI = playerState
    mov edx, function
    call edx
    add esp, 0Ch      // ★ 3 个栈参数
    mov result, eax
}
```

★★★ **⇒ 三个栈参数 + 两个寄存器（`ESI` = event,`EDI` = playerState）。**

---

## 九、★★★★★ **`callPMSetPitchValues` 的 ECX 错误**

### 9.1 ★★★★★ 完整注释（第 693–704 行，逐字）

```cpp
// CODDIFF(1649370): **THE PLAYERSTATE ARRIVES IN ECX ON THIS BUILD, NOT EAX.**
// out.exe's **PM_SetPitchValues (sub_41DB40, RVA 0x01DB40)** is **__usercall** and IDA
// types it **`__cdecl sub_41DB40(int a1)` with a ecx variable that is never
// assigned** -- **the giveaway for an incoming register argument**. The body uses it
// as the playerState and nothing else:
//     **((void (__cdecl *)(_DWORD *, _BYTE *))(
//         dword_E60B78 ^ v1[9] ^ (unsigned int)(v1 + 8)))(v1 + 4, v22);**
// i.e. **the accessor pair at +0x24/+0x20 decoded against base +0x10** -- the same
// pair PmoveSingle uses. **The stack argument is the pmove**, used for +288/+292.
//
// **Passing it in eax left ecx holding whatever the caller had**, which the log
// caught as **`ecx=0x00000010`** and **a read fault at 0x34** -- exactly **[ecx+0x10+0x14]**.
```

★★★★★ **⇒ 五个精确值：**
```
`PM_SetPitchValues` = **`sub_41DB40`**（RVA **`0x01DB40`**）
IDA 类型：**`__cdecl sub_41DB40(int a1)` 带一个从未赋值的 `ecx`** ⇒ **传入寄存器参数的迹象**
        ↓
★★★ 内部解码：**`dword_E60B78 ^ v1[9] ^ (v1 + 8)`** ⇒ 访问器对在 **`+0x24`/`+0x20`**
★★★ 栈参数 = **pmove**,用于 **`+288`/`+292`**
        ↓
★★★ 用 EAX 传 ⇒ **ECX 留着调用者的值** ⇒ 实测 **`ecx=0x00000010`**
★★★ 读故障在 **`0x34`** ⇒ 正是 **`[ecx+0x10+0x14]`** = `0x10 + 0x24`
```

### ★★★ 正确的调用（第 705–711 行）

```cpp
__asm
{
    push pmove        // ★ 栈参数
    mov ecx, playerState   // ★ ECX = playerState
    call function
    add esp, 4
}
```

---

## 十、★★★★★ **`PmoveSliceTraceLimit = 64` 的 94,148 行事故**

### 10.1 ★★★★★ 完整注释（第 2043–2053 行，逐字）

```cpp
// OLMOD(pmove-slice-cap): **`unexplained` is true on EVERY slice of an idle client** --
// an idle usercmd lets **gravity take velocity[2] from zero to -80 inside the same slice**,
// which is exactly the shape this test looks for -- and **the injected bot commands are idle
// by construction**. Unbounded, that printed **one line per slice per bot:
// 94,148 lines in one 25-minute session** (**12 bots at 20 Hz = 240 lines/s of synchronous
// file writes, 198 MB of log**) and **the frame never finished its snapshot step**, so
// **the client sat on "setting up game" while the snapshot counter stood still**.
// Keep the opening slices and the first anomalies: **64 full pmove dumps is more than this
// diagnosis needs**, and **the anomaly stays visible in the log**.
constexpr std::uint32_t PmoveSliceTraceLimit = **64**;
```

★★★★★ **⇒ 六个精确值：**
```
`unexplained` 在**空闲客户端的每一片**都为真（重力在同一片里把 `vel[2]` 从 0 拉到 **-80**）
★★★ 注入的 bot 命令**天生就是空闲的**
        ↓
★★★ 无上限 ⇒ **每 bot 每片一行**：**94,148 行 / 25 分钟**
★★★ = **12 bot × 20 Hz = 240 行/秒的同步文件写,198 MB 日志**
        ↓
★★★ ⇒ **帧从未完成快照步骤** ⇒ **客户端停在"setting up game",快照计数器不动**
        ↓
★★★ 修复：**`PmoveSliceTraceLimit = 64`**
```

### ★★★ `stance` 诊断的默认关闭（第 1933–1936 行，逐字）

```cpp
// ★★★ 2026-10-13（甲方令「新构建先把热日志修复掉」）—— 逐帧 stance 诊断**默认关**（`OLMOD_VERBOSE_LOG`）。
//   它按帧/按人放大：1 真人 1×、12 人 12×；实测 `runtime-frame beginUs≈0.55–0.71 s`、`FRAMESTALL wall≈CPU`。
//   复现本次问题只需把 `OLMOD_VERBOSE_LOG=1` 设回去（`RuntimeLog::verbose()` 是既有开关,未新增机制）。
if (OlMod::RuntimeLog::**verbose**() && stanceFollow && stanceLines < **400**)
```

★★★ **⇒ 两个精确值：**
```
`runtime-frame beginUs ≈ **0.55–0.71 s**`
`FRAMESTALL wall ≈ CPU`
```

### ★★★★★ **`stance` 行的两个关键位（第 1989–1998 行，逐字）

```cpp
// **AND THE TWO BITS THE STANCE HANDLER ACTUALLY GATES ON.**
// Section 76a: **out.exe's sub_417D10 makes TWO reads of the protected value at ps+0x10
// through the obfuscated accessor pair -- 0x00417E55 and 0x00417FCE -- takes bit 22 and
// bit 24 of the SECOND dword, and `jne`s past the stance transition when either is set.**
// **3.3.3.3's 0x00419270 makes NO such read**, which is why nothing in dest1yo's tree has
// an opinion about these bits. The second dword is **the one ol-mod fills with otherFlags**,
// and it is **the same dword BG_PlayerStateToEntityState tests 0x1800 in at 0x00411454**.
// So **this server owns the two bits that decide whether a crouch is allowed to happen,
// and has never once printed them.**
```

★★★★★ **⇒ 六个精确值：**
```
`sub_417D10` 读 protected 值**两次**：**`0x00417E55`** 和 **`0x00417FCE`**
        ↓
★★★ 取 **第二个 dword 的 bit 22 和 bit 24**
★★★ **任一置位 ⇒ `jne` 跳过姿态转换**
        ↓
★★★ **3.3.3.3 的 `0x00419270` 没有这个读** ⇒ dest1yo 的树对此无意见
★★★ 第二个 dword 就是 **ol-mod 填 `otherFlags` 的那个**
★★★ 也是 **`BG_PlayerStateToEntityState` 在 `0x00411454` 测 `0x1800` 的那个**
        ↓
★★★★★ ⇒ **服务端拥有决定"下蹲能否发生"的两个位,却从未打印过它们**
```

### ★★★★★ **`vhCur` 的收敛目标是错的**（第 1952–1958 行，逐字）

```cpp
// **THE LERP ITSELF, WHICH THIS LINE HAS NEVER PRINTED.** Section 177a concluded
// **"vhCur never converges on vhTgt"** from **0x16C and 0x170** alone -- but **0x170 does
// not move toward 0x16C**. It moves toward the **LERP TARGET at 0x178**, starting from the
// **LERP TIME at 0x174**. **If those two disagree with 0x16C then vhCur is converging
// correctly on the wrong number**, which is **a different defect with a different fix**,
// and **no measurement so far could tell the two apart**.
```

★★★★★ **⇒ 四个精确偏移：**
```
`ps+0x16C` = **viewHeightTarget**（`int32`）
`ps+0x170` = **viewHeightCurrent**（`float`）
`ps+0x174` = **viewHeightLerpTime**（`int32`）
`ps+0x178` = **viewHeightLerpTarget**（`int32`）
`ps+0x17C` = **viewHeightLerpDown**（`int32`）
        ↓
★★★ ⇒ **`0x170` 朝 `0x178` 收敛,不是朝 `0x16C`**
★★★ ⇒ 若 `0x178` 与 `0x16C` 不一致 ⇒ **`vhCur` 正确地收敛到**错的数**
```

### ★★★★★ **两个玩家的帧交错**（第 2001–2009 行，逐字）

```cpp
// **CLIENT NUMBER FIRST, AND IT IS NOT COSMETIC.** This line has never carried one, and
// **TWO PLAYERS' frames interleave in it.** Section 177a read **"vhCur wanders between 40.0
// and 47.4 and never converges"** off exactly such a trace -- and **one player prone near 40
// beside one crouched near 47, sampled alternately, IS that range.** Measured 2026-09-02:
// **with a client number available, a single crouch and a single prone each showed a clean
// monotone descent to their target.** Same trap as
// **[[an-instrument-that-maps-two-answers-onto-one-word]]**.
```

★★★★★ **⇒ 一个精确的仪器陷阱：**
```
无 clientNum ⇒ **两个玩家的帧交错**
        ↓
★★★ section 177a 读到 "**vhCur 在 40.0 和 47.4 之间游走,永不收敛**"
★★★ 而**一个俯卧在 40 附近、一个下蹲在 47 附近,交替采样** ⇒ **正好是这个范围**
        ↓
★★★ 实测（**2026-09-02**）：**有 clientNum 后,单次下蹲和单次俯卧各自单调下降到目标**
```

---

## 十一、★★★★ **其余的关键细节**

### 11.1 ★★★★★ **`serverAnimationTimeMilliseconds_ = command.commandTime`**（第 1684–1691 行，逐字）

```cpp
// CODREF(pmove): **"now" INSIDE pmove is this command's time, not the frame's.**
// PmoveSingle compares **playerState +0x33C** against **the shared animation clock at
// animBase +0x96DD8** with **jge/jle at VA 0x00419FD8 and 0x00419FF8**, and **a backlog
// replays several commands within one server frame** -- so **stamping the frame time here
// would run every command of that backlog against the same "now" and expire nothing in
// order**. **commandTime is the value the comparison is written against.**
```

★★★ **⇒ 三个精确值：**
```
比较：**`ps+0x33C`** vs **`animBase + 0x96DD8`**
指令：**`0x00419FD8`（`jge`）/ `0x00419FF8`（`jle`）**
        ↓
★★★ ⇒ 若用**帧时间** ⇒ 一个 backlog 的所有命令用**同一个 "now"** ⇒ **顺序全乱**
```

### ★★★ `static_assert` 的动画存储上界（第 214–216 行）

```cpp
static_assert(
    **0x96E20 + 64 * 0x3B8 + 0x320** <= EngineBindings::ServerAnimConditionStorageSize);
```
★★★ **⇒ 三个精确值：`0x96E20`（基址）+ `64 × 0x3B8`（64 个 characterInfo）+ `0x320`（余量）。**
**⇒ `64 × 0x3B8 = 60,928` ⇒ 总需 **`0x96E20 + 0xEE00 + 0x320`** = **`0xA5F40`** ≈ **679 KB**。**

### ★★★ `validNativeCommand` 的四个上界（第 950–958 行）

```cpp
return std::isfinite(command.conditionalAngle) &&
    command.weapon <= MaximumWeaponAssetIndex &&
    command.offHandIndex <= MaximumWeaponAssetIndex &&
    command.lastWeaponAltModeSwitch <= MaximumWeaponAssetIndex &&
    command.conditionalElevenBits <= **0x7FF**;      // ★ 11 位
```
★★★ **⇒ `conditionalElevenBits <= 0x7FF` ⇒ **11 位**,与报告 098 的 `UserCmdWeaponIndexBits = 11`**一致** ✓**

### ★★★★★ **`ps` 的完整偏移表（跨全部三个文件汇总）**

| 偏移 | 字段 | 出处 |
|---|---|---|
| **`0x000`** | `commandTime` | 本文件 |
| **`0x004`** | `pm_type` | 本文件 |
| **`0x00C`** | `pm_flags` | 本文件 |
| **`0x010`** | **protected 对象（3 dword）** | 本文件 |
| **`0x020`** | **setter 槽 / getter 键** | 本文件 |
| **`0x024`** | **getter 槽 / setter 键** | 本文件 |
| **`0x028`** | `PmoveControlFlags` | 本文件 |
| **`0x02C`** | `bobCycle` | 本文件 |
| **`0x030`** | `origin`（3 float） | 本文件 |
| **`0x03C`** | `velocity`（3 float） | 本文件 |
| **`0x0C0`** | `groundEntityNum` | 本文件 |
| **`0x0C8`** | `legsAnim` | 本文件 |
| **`0x0D0`** | `torsoAnim` / `jumpTime` | 本文件 |
| **`0x0D4`** | `jumpOriginZ` | 本文件 |
| **`0x104`** | `eFlags` | 报告 126/128 |
| **`0x158`** | `clientNum` | 报告 126/本文件 |
| **`0x160`** | `viewAngles` | 报告 128 |
| **`0x16C`** | `viewHeightTarget` | 本文件 |
| **`0x170`** | `viewHeightCurrent` | 本文件 |
| **`0x174`** | `viewHeightLerpTime` | 本文件 |
| **`0x178`** | `viewHeightLerpTarget` | 本文件 |
| **`0x17C`** | `viewHeightLerpDown` | 本文件 |
| **`0x1A4`** | `health`（stats[0]） | 报告 127 |
| **`0x20C`** | 服务端 Pmove 影子 / health | 报告 127/本文件 |
| **`0x248`** | `linkEntity` | 报告 128 |
| **`0x2C0`** | `weaponTime` | 本文件 |
| **`0x2C4`** | `weaponDelay` | 本文件 |
| **`0x2CC`** | `weaponState` | 本文件 |
| **`0x2F4`** | `heldWeapons[15]` | 报告 128 |
| **`0x33C`** | 动画时钟比较字段 | 本文件 |
| **`0x3B8`** | `characterInfo` 步长 | 本文件 |
| **`0x3E4`** | `selectedOffhand` | 报告 128 |
| **`0x3F8`** | `currentWeapon` | 报告 128 |
| **`0x400`** | `weaponFlags` | 报告 128 |
| **`0x404`** | `weaponPositionFraction` | 报告 128 |
| **`0x3BBC`** | **`sizeof(playerState_s)`** | 报告 126/128/本文件 |

★★★ **⇒ 共 **36 个精确偏移**,跨 4 份报告。**

### ★★★ `characterInfo` 的三个偏移

```cpp
characterInfo + **0x2EC** + 8*index     // 条件数组
characterInfo + **0x450**                // 大小（报告 128/130）
cg + **0x180C50** + 0x450*clientNum      // 定位公式（报告 130）
```

### ★★★ 三个环境变量

```cpp
**OLMOD_MSGWIN_PROBE**       // 消息窗口探针（最多 2 次）
**OLMOD_WSWITCH_PROBE**      // 武器切换时间线（只读）
**OLMOD_BULLET_FIRE_PROBE**  // 注入开火位（**必须恰好 "1"**）
```

★★★ **⇒ 三者的门禁不同：**
```
MSGWIN / WSWITCH：`size > 0 && value[0] != '0'`
BULLET_FIRE：**`size == 1 && value[0] == '1'`**（更严）
```

### ★★★ `sub_529440` 消息窗口打印（第 599–621 行）

```cpp
inline constexpr std::size_t MessageWindowPrintRva = **0x129440**;
using PrintFn = char(__cdecl *)(const char *, int, int, int, int);
fn(text, **0, 0, 2000, 0**);
```

★★★ **⇒ 五个参数：`text` / `0` / `0` / **`2000`** / `0`。**
**⇒ 注释（第 599–603 行）："This client has **NO developer console**（`toggleconsole` /
`Con_*Console` / `con_inputBoxColor` are absent from every readable generation: **2014 alpha,
3.3.3.3, 3.19**）."**

---

## 十二、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`trace_t` = `0x28`** | 六个 `static_assert`：`hitType@0x18` / `modelIndex@0x1E` / `partName@0x20` / `partGroup@0x22` / `allSolid@0x24` |
| 2 | ★★★ 无命中哨兵 | **`fraction = 1.0f`** / **`hitId = 2047`** |
| 3 | ★★★★★ **handler 槽** | **`pmoveHandlers[pm->handler].trace`**；**客户端只保留 handler 0** |
| 4 | ★★★★★ **CAS 交换** | `InterlockedCompareExchange(slot, callbackBits, expectedBits)`；失败 ⇒ **`HandlerSlotBusy`** |
| 5 | ★★★ 恢复在 `__finally` | **`MemoryBarrier()`** + CAS 换回；失败 ⇒ **`HandlerRestoreFailed`** |
| 6 | ★★★ 三层兜底 | `thread_local` context → **`clientPmoveTraceFallback`** → **`writeNoHitTrace`** |
| 7 | ★★★★★ **`ps+0x10` 三 dword** | 访问器对在 **`ps+0x20`/`ps+0x24`**；`sub_411360 @ 0x0041143E` |
| 8 | ★★★★★ **`eType` 的判定** | `test eax, **0x1800**` / `sete al` / `lea eax,[eax*4+1]` ⇒ **`eType = 1`(ET_PLAYER) 或 `5`(ET_INVISIBLE)** |
| 9 | ★★★★★ 实测日志 | **`converted state mismatch eType converted=5 playerState=1`** |
| 10 | ★★★★★ **镜像的访问器对** | **getter**：键 `ps+0x20`、存 `ps+0x24`、cookie **`ds:0x00E60B78`**；**setter**：键 `ps+0x24`、存 `ps+0x20`、cookie **`ds:0x00E60B74`** |
| 11 | ★★★ 两个 cookie 差 4 字节 | **`0x00E60B78`** vs **`0x00E60B74`** |
| 12 | ★★★★★ **参数顺序相反** | **get = `(object, out)`** / **set = `(value, object)`** |
| 13 | ★★★ setter 的 value | **`{0, flags, 0}`** ⇒ **只有第 2 个 dword 非零** |
| 14 | ★★★ `sub_5BEB50` 步长 | **`0x3BBC`**，设置点在 **`0x005BEEC3`** |
| 15 | ★★★★★ **`sub_403C70` 34 路** | `case 0..32` + default；**case 0** = `sub_401720`/`sub_4017C0`；**case 1** = `sub_401840`/`sub_4018D0` |
| 16 | ★★★★ 两组键 | `sub_4017C0`：**`0x00E60224`/`0x00E609A0`/`0x00E609A4`**；`sub_4018D0`：**`0x00E609A8`/`0x00E609AC`/`0x00E609B0`** |
| 17 | ★★★★★ **旧实现 `QPC % 33`** | 每次调用新变体 ⇒ **一写一读用不同变体** ⇒ **逐帧不同** |
| 18 | ★★★★★ **`StableAccessorSelector = 0`** | 固定变体,**选择存在槽里** |
| 19 | ★★★ 初始化 ABI | **4 个栈参数**（`selector`/`encodedGet`/`encodedSet`/`setKey`）；**`eax` = SET 槽**、**`edi` = GET 槽**、**`edx` = get 键** |
| 20 | ★★★★★ **PM_Weapon 四门** | **T** `pm_type >= 8` / **F** `pm_flags & 0x400` / **E** `eFlags & 0xC00` / **P** protected bit 30 |
| 21 | ★★★ `sub_42AED0` 位置 | **PM_Weapon = `sub_42B4E0`**；调用点 **`0x0041D263`**；长分支 **`0x0042B597`** |
| 22 | ★★★★★ **`PMF_RESPAWNED` 的清除** | **`0x0041CEA6`**(out.exe) / **`0x0041DDBB`**(3.3.3.3)；条件 `pm_type<8` **且** **`!(cmd.buttons & 0x101)`**；`and [ps+0x0C], 0xFFFFFBFF` |
| 23 | ★★★★★ **`pmove+8` = `cmd.buttons`** | `pmove.cmd` @ **`pmove+4`**；`buttons` @ **`cmd+4`** ⇒ **`pmove+8`** |
| 24 | ★★★ 探针帧数 | **`BulletFireProbeReleaseFrames = 12`** / **`BulletFireProbeFrames = 120`** |
| 25 | ★★★★★ **`0x014 → 0x028`** | OLfinal **在 `+0x10` 与该字段之间插入 20 字节**；netfield 表配对 **A `0x014` / C `0x028`** |
| 26 | ★★★ 两个邻居佐证 | 上方 `otherFlags` **原地换 codec @ `0x010`**；下方 `bobCycle` **`0x018` → `0x02C`** |
| 27 | ★★★ 三个时间常量 | **`MaximumBacklog = 1000`** / **`MaximumSlice = 66`** / **`MaximumSlices = 16`**（= ceil(1000/66)） |
| 28 | ★★★ 两个命令门 | `pm_flags & **0x80000**` 或 `buttons & **0x200000**` ⇒ `buttons &= **0x80300**`；`PmoveControlFlags & **4**` ⇒ `buttons &= **0xFFFFFBF9**` |
| 29 | ★★★★★ **事件表地址** | **`VA 0x00E60410`**（out.exe）；**`0x00CE4A20`** 是 3.3.3.3 的表,out.exe 该处是 **.rdata IME 字符串** |
| 30 | ★★★ 条目格式 | **8 字节** `{const char *name, 0xFFFFFFFF}` |
| 31 | ★★★★★ **0..32 逐名相同** | 0 PAIN / 1 DEATH / 2 FIREWEAPON / 3 JUMP / 4 JUMPBK / 5 LAND / 6 DROPWEAPON / **7 RAISEWEAPON** / 8 CLIMBMOUNT / ... / 32 SPAWN |
| 32 | ★★★★★ **追加 7 个** | **33 HOLDFIRE / 34 HOLDFIRELOOP / 35 HOLDFIRECANCEL / 36 SIDEROLLING_LEFT / 37 SIDEROLLING_RIGHT / 38 ADSTURRET_DEPLOY / 39 ADSTURRET_UNDEPLOY** |
| 33 | ★★★★★ **"每表规则"** | 可预测事件枚举**插入**（8 移位）；动画事件表**追加**（0 移位）⇒ **不是 build 级规则** |
| 34 | ★★★★★ **`sub_407980` 的拒绝** | **bit `0x20000000`** 置位 ⇒ `legs = ((((legs>>10)&3)+1)%4) << 10` + **`return -1`** |
| 35 | ★★★★★ 实测 | 明文 **`0x1000`** 当密文读 ⇒ 解码成 **`0xe4001126`** ⇒ **bit 29 置位** |
| 36 | ★★★★★ **"约一半噪声有 bit 29"** | ⇒ **每次死亡是抛硬币** ⇒ **任何移动缓冲区的编辑都重掷** |
| 37 | ★★★ 条件追查为何失败 | **DEATH set 23 零条件,无条件匹配** ⇒ 遍历从来不是失败点 |
| 38 | ★★★★★ **条件偏移** | **`characterInfo + 0x2EC + 8*index`**；校准：`CharacterInfoMoveTypeConditionOffset = **0x304**` = `0x2EC + 0x18`（**3 条目**） |
| 39 | ★★★ MOVETYPE 是条目 3 | 条件名表 **`0x00E60828`**；并行类型表 **`0x00E608C8`** |
| 40 | ★★★ 三个条件的编号 | **`10` = DAMAGETYPE / `11` = HITLOCATION / `12` = HITDIRECTION**；`condType = 1`（**纯整数**） |
| 41 | ★★★★★ **`sub_407E10` 的 EDI** | 第一条 `mov ecx, [edi+158h]`；**EAX 在 `0x407E26` 被覆盖** ⇒ **EAX 已死** |
| 42 | ★★★ characterInfo 定位 | **`dword_827F730 + 0x450*clientNum + 0xAF350`** |
| 43 | ★★★ `AnimScriptItemsStride` | **`0x204`**（`0x407E1C imul ecx, 204h`）；数组在 **`animScriptData + 0x25F80`** |
| 44 | ★★★★★ **`PM_SetPitchValues`** | **`sub_41DB40`**（RVA **`0x01DB40`**）；**`ECX` = playerState**；栈 = pmove（用于 `+288`/`+292`） |
| 45 | ★★★ 用 EAX 的后果 | **`ecx=0x00000010`** ⇒ 读故障 **`0x34`** = `[ecx+0x10+0x14]` |
| 46 | ★★★★★ **动画"now"** | `ps+**0x33C**` vs **`animBase + 0x96DD8`**；`jge` **`0x00419FD8`** / `jle` **`0x00419FF8`** |
| 47 | ★★★ 动画存储上界 | **`0x96E20 + 64 × 0x3B8 + 0x320`** ≤ `ServerAnimConditionStorageSize` |
| 48 | ★★★ `conditionalElevenBits` | **`<= 0x7FF`**（11 位） |
| 49 | ★★★★★ **`PmoveSliceTraceLimit = 64`** | 无上限 ⇒ **94,148 行 / 25 分钟 / 198 MB**（**12 bot × 20 Hz = 240 行/秒**）⇒ **帧卡在快照步骤** |
| 50 | ★★★ `runtime-frame beginUs` | **0.55–0.71 s** |
| 51 | ★★★ stance 行上限 | **400** 行（`OLMOD_VERBOSE_LOG` 门禁） |
| 52 | ★★★★★ **姿态的两个门位** | `sub_417D10` 读 **`0x00417E55`** 和 **`0x00417FCE`** ⇒ **第二 dword 的 bit 22 / bit 24**；任一置位 ⇒ **跳过姿态转换** |
| 53 | ★★★ 3.3.3.3 无此读 | **`0x00419270`** ⇒ dest1yo 的树对此无意见 |
| 54 | ★★★★★ **`vhCur` 收敛目标** | `0x170` 朝 **`0x178`（lerp target）** 收敛,不是朝 **`0x16C`**；从 **`0x174`（lerp time）** 起 |
| 55 | ★★★★★ **两玩家帧交错** | "vhCur 在 **40.0–47.4** 游走" = **一个俯卧 40 + 一个下蹲 47 交替采样** |
| 56 | ★★★ 实测（2026-09-02） | 有 clientNum 后,单次下蹲/俯卧各**单调下降**到目标 |
| 57 | ★★★ 三个环境变量 | **`OLMOD_MSGWIN_PROBE`** / **`OLMOD_WSWITCH_PROBE`** / **`OLMOD_BULLET_FIRE_PROBE`**（**必须恰好 "1"**） |
| 58 | ★★★ 消息窗口 | **`sub_529440`**（RVA **`0x129440`**）；`fn(text, 0, 0, **2000**, 0)` |
| 59 | ★★★ 无开发者控制台 | `toggleconsole` / `Con_*Console` / `con_inputBoxColor` 在 **2014 alpha / 3.3.3.3 / 3.19** 全部缺席 |
| 60 | ★★★ `ps` 偏移总数 | **36 个**,跨 4 份报告（126/128/130/132） |

---

## 十三、结论

### 1. ★★★★★ **`ps+0x10` 是三 dword 加密对象,不是普通 `otherFlags`**

★ **⇒ getter/setter **镜像**（键与存位置互换,cookie 差 4 字节）,参数顺序也相反。**
**⇒ 明文写入 ⇒ 解码成噪声 ⇒ `0x1800` 测试失败 ⇒ **所有玩家发布为 ET_INVISIBLE**。**

### 2. ★★★★★ **`QPC % 33` 的随机变体是**逐帧不一致**的根因**

★ **⇒ `sub_403C70` 有 **34 路变体**,**一个变体写的密文对另一个是噪声**。**
**⇒ 修复 = **`StableAccessorSelector = 0`**（固定,且**存在槽里**）。**

### 3. ★★★★★ **PM_Weapon 有四个门（T/F/E/P）**,探针必须**先松扳机再拉**

★ **⇒ `PMF_RESPAWNED` 只在 **`!(buttons & 0x101)`** 的帧清除 ⇒ **从第 1 帧按住开火 ⇒ 闩锁永不清除**。**

### 4. ★★★★★ **`0x014 → 0x028` 的 20 字节插入有**三方佐证**（netfield 表 + 上下邻居）**

### 5. ★★★★★ **"1649370 shifted the enums" 不是 build 级规则,是**每表**规则**

★ **⇒ 可预测事件枚举**插入**（8 移位）,动画事件表**追加**（7 个新条目,0 移位）。**

### 6. ★★★★★ **`sub_407980` 的 bit 29 是 T-pose 的直接判据**

★ **⇒ 明文 `0x1000` 被当密文读 ⇒ `0xe4001126` ⇒ bit 29 置位 ⇒ `return -1`。**
**⇒ **"约一半噪声有 bit 29"** ⇒ **每次死亡抛硬币** ⇒ **从八月活到现在。**

### 7. ★★★★★ **`sub_407E10` 与 `sub_41DB40` 都在**非 EAX**的寄存器里收 playerState**

★ **⇒ 前者 `EDI`,后者 `ECX`；两者用 EAX 都留下垃圾。**

### 8. ★★★★★ **两个性能事故都有精确数字**

★ **⇒ `PmoveSliceTraceLimit = 64` 之前：**94,148 行 / 25 分钟 / 198 MB**（240 行/秒）⇒ **帧卡在快照步骤**。**
**⇒ `stance` 诊断：`runtime-frame beginUs ≈ 0.55–0.71 s`。**

### 9. ★★★★★ **`vhCur` 的收敛目标是 `0x178` 而非 `0x16C`**（一个此前未测的区分）

### 10. ★★★★★ **两个玩家的帧交错能伪造出"永不收敛"**（40.0–47.4 的假范围）

### 11. ★★★ **`ps` 的 36 个偏移已跨 4 份报告完整汇总**

---

## 十四、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. 然后 `server_mp` 154 文件（12,604,630 B）
