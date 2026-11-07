# 学习报告 134（重开）— `EngineBindings.cpp` 上半（1–7,600 / 17,867 行）

**学习范围**：`EngineBindings.cpp` 第 **1–7,600 行**（共 17,867 行）
**性质**：全实测（**逐行读完前半**）
**★★★★★ 本报告收录十二个重大发现**：①**故障见证器（VEH）的完整实现与栈扫描** ②**`ServerDObjGetRva` 是**谓词**不是 getter** ③**`DObj` 步长 `0xD8` 而非 `0xCC`** ④**`AnimTreeContextOffset = 0xACE70` 与 `Handle = 0xACE64`** ⑤**十个动画回调的 `+0x18530` 重定位** ⑥**`CharacterInfoDObjDirtyOffset 560→660`** ⑦**`ItemDefinitionSize 40→52`** ⑧**`WeaponDef` 七个不同位移** ⑨**`CharacterItemDefinitionSize = 0x34` 的四点独立证据** ⑩**`invokeSVTrace` 四个参数错误的后果** ⑪**`FxGlass` 的三条精确关系** ⑫**`bind()` 的 60+ 前缀守卫**

---

## 一、★★★★★ **故障见证器（VEH）的完整实现**

### 1.1 ★★★★★ 完整理由（第 131–140 行，逐字）

```cpp
// OLMOD(silent-death-witness): **__try is not enough**. The dedicated
// process **died inside BG_AnimParseAnimScript with NOTHING in the log** -
// **no exception code, no stage** - which a __try **cannot produce and so
// cannot explain**. A **vectored handler runs BEFORE any SEH frame** and
// **before anything can unwind or exit**, so it **gets to write the line even
// when the process is about to disappear**.
//
// It **only WITNESSES**: it returns **EXCEPTION_CONTINUE_SEARCH** so normal
// handling is unchanged, and **it filters to the codes worth a line** so
// that ordinary handled exceptions do not fill the log.
```

★★★★★ **⇒ 三个精确事实：**
```
进程**死在 `BG_AnimParseAnimScript` 内,日志里什么也没有**
（无异常码、无 stage）
        ↓
★★★ `__try` **无法产生也无法解释**这个
★★★ **VEH 在任何 SEH 帧之前运行**,在**任何栈展开或退出之前**
★★★ ⇒ **即使进程即将消失也能写那一行**
        ↓
★★★ 它**只见证**：返回 `EXCEPTION_CONTINUE_SEARCH` ⇒ 正常处理不变
★★★ **按值得记录的码过滤** ⇒ 普通已处理异常不填满日志
```

### ★★★ 六个"值得记录"的码（第 200–206 行）

```cpp
code == EXCEPTION_ACCESS_VIOLATION ||
code == EXCEPTION_STACK_OVERFLOW ||
code == EXCEPTION_ILLEGAL_INSTRUCTION ||
code == EXCEPTION_PRIV_INSTRUCTION ||
code == EXCEPTION_IN_PAGE_ERROR ||
code == EXCEPTION_INT_DIVIDE_BY_ZERO
```

★★★ **⇒ 六个码,上限 **10 次**（第 209 行）。**

### ★★★ 日志格式（第 218–219 行）

```
"native fault witness code=0x%08lX rva=0x%07X op=%u target=0x%08X thread=%lu stage=%s"
```

★★★ **⇒ 五个字段：码 / RVA / 操作类型 / 目标地址 / 线程 / **stage**。**
**⇒ `stage` 来自 `SV_CurrentNativeStage()`（一个 `atomic<const char*>`）。**

### ★★★★★ **为什么需要 stage**（第 230–233 行，逐字）

```
"**WHICH NATIVE STAGE.** An RVA says **where** the engine died; it **does not say
 which of ol-mod's calls put it there**, and **every stage in clientThink reaches
 the same shared BG code**. The breadcrumb costs **one atomic store per native call**
 and turns **"0xC0000005 at 0x411310" into a named suspect**."
```

### ★★★★★ **寄存器行与记录读取**（第 238–289 行，逐字）

```cpp
// **THE RVA SAYS WHERE; THE REGISTERS SAY WHY.** The **zhunt load crash**
// (HANDOFF section 152w) dies at **sub_59CC70+0x1A5 writing [edi+3ECh]**,
// where **edi is sub_53F5F0's return -- 0 when the record's type tag at +0xF8
// is neither 1 nor 2**. Without edi and ebx in hand that is a **hypothesis**;
// with them it is a **reading**.
//
// **Hooking sub_53F5F0 or sub_59CC70 would answer the same question and is NOT
// an option: both are per-frame, and a per-frame client hook crashed three
// clients at once.** A vectored handler **costs nothing until the fault actually
// happens**.
```

★★★★★ **⇒ 六个精确值：**
```
故障点：**`sub_59CC70+0x1A5`** 写 **`[edi+3ECh]`**
`edi` = **`sub_53F5F0` 的返回值** ⇒ **当记录的 `+0xF8` 类型标签既不是 1 也不是 2 时为 0**
        ↓
★★★ 记录的两个字段：**`record+0x194`** = 实体索引 / **`record+0x1CC`** = 武器索引
        ↓
★★★ 不用钩子的理由：**两者都是每帧的,而每帧客户端钩子曾一次崩掉三个客户端**
```

### ★★★★★ **栈扫描：为什么不用 EBP 链**（第 290–306 行，逐字）

```cpp
// **THE FAULTING INSTRUCTION IS NOT THE QUESTION - HOW WE GOT THERE IS.**
// **0x4888CC said the DB's load pump faulted; it did not say which call reached it.**
//
// **AN EBP CHAIN IS THE WRONG INSTRUMENT HERE and was tried first**: the pump is
// **FPO** - `sub_4888B0` opens `push ecx; push esi` with **no `mov ebp, esp` at
// all** - so **EBP at the fault belongs to whatever frame-pointer function ran
// last**, and walking it produced **three plausible-looking addresses that were
// not on the path**.
//
// So **scan the raw stack instead**. Every dword in **the next kilobyte** that
// **points into .text AND is preceded by a `call`** is a return address or a
// very good imitation of one; **the E8/FF15/FF five- and six-byte forms cover
// almost every call MSVC emits**. **This over-reports** - stale slots survive
// below ESP - so **it is labelled a SCAN, not a stack**, and **the order is
// address order, not call order**.
```

★★★★★ **⇒ 七个精确值：**
```
泵函数 **`sub_4888B0`** 是 **FPO**：`push ecx; push esi`,**无 `mov ebp, esp`**
        ↓
★★★ ⇒ **故障时的 EBP 属于最后运行的帧指针函数**
★★★ ⇒ 走 EBP 链给出**三个看起来合理但不在路径上的地址**
        ↓
★★★ 改：**扫描原始栈**（**下一个千字节**）
★★★ 判据：dword **指向 .text** **且** **前面是 `call`**
★★★ 三种 call 形式：**`E8`**（rel32）/ **`FF15`**（间接）/ **`FF`**（reg）
★★★ **会过度报告**（ESP 以下的陈旧槽仍在）⇒ **标为 SCAN 而非 stack**
★★★ **顺序是地址序,不是调用序**
★★★ 上限 **14 个**（第 314 行）
```

### ★★★ `witnessCanRead` 的五种可读保护（第 155–157 行）

```cpp
constexpr DWORD Readable = PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
    PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY;
```
★★★ **⇒ 六种（注释说五种但列了六种）⇒ 记录为**注释笔误**。**

### ★★★ 两个装载点（第 169–173 行，逐字）

```
"**ARMED FROM TWO PLACES NOW.** The dedicated arms it around **native animation
 init**; the **CLIENT arms it at startup**, because **the crash worth catching
 (HANDOFF section 152w) happens in the client** and **a CODOL client that crashes
 exits tidily with no dump** -- **the handler is the only thing that runs before
 its own TopLevelExceptionFilter swallows the context**."
```

---

## 二、★★★★★ **`ServerDObjGetRva` 是**谓词**不是 getter**

### 2.1 ★★★★★ 完整注释（第 662–686 行，逐字）

```cpp
// **THE FUNCTION THIS USED TO CALL IS A PREDICATE ON THIS BUILD, NOT A GETTER.**
// **ServerDObjGetRva 0x34E160 is sub_74E160 in out.exe**, and it decompiles to
//     **v1 = word_77E7F20[(a1 - &unk_31437A0) / 712];**
//     **return v1 && (&unk_77E9720 + 216 * v1) != 0;**
// -- **a BOOL**. **It returned literally 1, which is non-null, so every caller
// sailed past its null check and then failed on the first read through the
// "pointer".** **The live log caught it as `dobj=1`.**
//
// **out.exe has no standalone getter to re-point at: every call site inlines the
// same two lines** (sub_4EC9E0 among them), which is **very likely why a signature
// port picked the predicate -- it is the only function shaped like one**. So
// **inline it here too, from the map and pool this project already binds**, and
// **drop the RVA dependency for this operation entirely**. ServerDObjGetTarget
// **stays bound because other checks look for it; nothing reads it any more.**
```

★★★★★ **⇒ 六个精确值：**
```
`sub_74E160` = **`word_77E7F20[(a1 - &unk_31437A0) / 712]`** ⇒ **bool**
        ↓
★★★ **`712`** = **`0x2C8`** = `NativeServerEntitySize` ✓
★★★ **`216`** = **`0xD8`** = `NativeServerDObjSize` ✓
        ↓
★★★ ⇒ **返回字面 `1`** ⇒ **所有调用者都过了 null 检查**
★★★ ⇒ **在第一次通过"指针"读取时失败**
★★★ 实测日志：**`dobj=1`**
        ↓
★★★ out.exe **没有独立 getter**：每个调用点**内联同样两行**
★★★ ⇒ **签名移植选了这个谓词,因为它是唯一形状像 getter 的函数**
```

### ★★★ 内联实现（第 676–686 行）

```cpp
auto *const map = ServerDObjMap.load();
auto *const pool = ServerDObjPool.load();
if (!map || !pool) return nullptr;
const auto dobjIndex = map[entityNum];
if (!dobjIndex || dobjIndex >= NativeServerDObjCapacity) return nullptr;
return pool + (size_t)dobjIndex * NativeServerDObjSize;
```

★★★ **⇒ `NativeServerDObjCapacity = 2048`（第 76 行）。**

---

## 三、★★★★★ **`DObj` 步长 `0xD8` 而非 `0xCC`**

### 3.1 ★★★★★ 完整注释（第 82–87 行，逐字）

```cpp
// CODDIFF(1649370): **THE DObj POOL STRIDE IS 0xD8, NOT 3.3.3.3's 0xCC.** Every
// **inlined lookup in out.exe multiplies the map entry by 216**: the allocator
// **sub_66BEE0** (`&unk_77E9720 + 216 * v5`), the predicate **sub_74E160**, and
// both bulk walkers **sub_66BFF0/sub_66C050**. **At 0xCC every DObj after index 0
// was the wrong object by 12*index bytes.**
```

★★★★★ **⇒ 四个精确值：**
```
步长 **`0xD8`** = **216**（本 build）/ **`0xCC`** = **204**（3.3.3.3）
        ↓
★★★ 四个独立佐证：`sub_66BEE0`（分配器）/ `sub_74E160`（谓词）/ `sub_66BFF0` / `sub_66C050`（批量遍历）
        ↓
★★★ ⇒ 用 `0xCC` ⇒ **索引 0 之后的每个 DObj 都错 `12 × index` 字节**
```

### ★★★★★ **`DObjScaleOffset = 200` 的三分量证据**（第 1138–1154 行，逐字）

```cpp
// **CONFIRMED AGAINST out.exe, AND IT IS A VECTOR.** The DObj constructor
// **sub_781960** writes **THREE floats** here and nothing else touches them:
//     ***(float *)(dobj + 200) = 1.0;**
//     ***(float *)(dobj + 204) = 1.0;**
//     ***(float *)(dobj + 208) = 1.0;**
//     ***(_DWORD *)(dobj + 212) = -1;**
// so **200 is the X component of a per-axis model scale, not a scalar**, and
// **the object reaches 216 -- which independently confirms the 0xD8 stride,
// because 0xCC would have cut off both 208 and 212**. **Writing only X while
// Y and Z keep whatever they hold is a non-uniform scale**: harmless while
// every modelScale is 1.0, and **a stretched model the moment one is not**.
//
// The same function confirms two more of this block **by construction**:
// **memset(dobj + 20, 0, 0x88)** is exactly **DObjSkelStateOffset 20** and
// **DObjSkelStateSize 136**, and it zeroes **160..188** across **DObjBoneHideBitsOffset**.
```

★★★★★ **⇒ 七个精确值：**
```
`dobj+200` / `dobj+204` / `dobj+208` = **三个 1.0f**
`dobj+212` = **-1**
        ↓
★★★ ⇒ **200 是每轴模型缩放的 X 分量,不是标量**
★★★ ⇒ **对象达到 216** ⇒ **独立确认 `0xD8` 步长**
★★★ ⇒ **`0xCC` 会切掉 208 和 212**
        ↓
★★★ **只写 X 而 Y/Z 保持原值 = 非均匀缩放** ⇒ **modelScale 不是 1.0 时模型被拉伸**
        ↓
★★★ `memset(dobj+20, 0, 0x88)` ⇒ 确认 **`DObjSkelStateOffset = 20`** / **`DObjSkelStateSize = 136`**
★★★ 并清零 **160..188** ⇒ 覆盖 **`DObjBoneHideBitsOffset = 160`**
```

### ★★★ DObj 的九个偏移（第 1128–1137 行）

```cpp
DObjModelCountOffset      = 9;
DObjBoneCountOffset       = 10;
DObjModelHideMaskOffset   = 12;
DObjSkelStateOffset       = 20;
DObjSkelStateSize         = 136;
DObjSkelPartBitsOffset    = 116;
DObjSkelEpochOffset       = 148;
DObjPoseMatricesOffset    = 152;
DObjBoneHideBitsOffset    = 160;
DObjModelPointersOffset   = 192;
```

★★★ **⇒ 十个偏移,`DObjScaleOffset = 200`,`DObjModelScaleOffset = 0xC8`（200）⇒ **同一偏移两个名字**。**

### ★★★ `NativeDObjModel` 的 44 字节（第 1155–1163 行）

```cpp
struct NativeDObjModel
{
    void *model{};                              // +0
    std::uint16_t boneName{};                   // +4
    std::uint8_t ignoreCollision{};             // +6
    std::uint8_t pad{};                         // +7
    std::array<std::byte, 36> reserved{};       // +8..43
};
static_assert(sizeof(NativeDObjModel) == 44);
```

### ★★★ `XModel` 的五个偏移（第 1164–1169 行）

```cpp
XModelBoneCountOffset          = 4;
XModelNameOffset               = 0;
XModelBoneClassificationOffset = 60;
XModelGeometryOffset           = 312;
XModelGeometryEntrySize        = 28;
XModelGeometryPointerOffset    = 24;
```

---

## 四、★★★★★ **`AnimTreeContextOffset = 0xACE70` 与 `Handle = 0xACE64`**

### 4.1 ★★★★★ 完整注释（第 1077–1091 行，逐字）

```cpp
// CODDIFF(1649370): **0x94D40 was 3.3.3.3's.** CL_ParseGamestate hands
// BG_FindAnims its context directly and says what the offset is:
//     **454c63  mov eax, dword_827F730**
//     **454c68  add eax, 0ACE70h**
//     **454c77  call sub_404D80**
// and **sub_404D80 fills a1+4, a1+8, a1+12, a1+16 from there**.
constexpr std::size_t AnimTreeContextOffset = **0xACE70**;
// **The HANDLE is twelve bytes below the context, and it is a different thing**:
// BG_FinalizePlayerAnims reads a pointer there and dereferences it for the
// animation count.
//     **v1 = *((_DWORD *)dword_827F734 + 177049);   // +0xACE64**
//     ***((_DWORD *)dword_827F734 + 26624) = *v1;   // +0x1A000**
// **Checking the context slot for "is the anim tree there" was checking a word
// nothing writes.**
```

★★★★★ **⇒ 六个精确值：**
```
3.3.3.3 的 `0x94D40` → 本 build 的 **`0xACE70`**
        ↓
★★★ 三条指令：`0x454C63 mov eax, dword_827F730` / `0x454C68 add eax, 0ACE70h` / `0x454C77 call sub_404D80`
★★★ `sub_404D80` 从那里填 **`a1+4` / `a1+8` / `a1+12` / `a1+16`**
        ↓
★★★ **HANDLE 在 context 下方 12 字节** = **`0xACE64`**
★★★ `BG_FinalizePlayerAnims` 在那里读一个指针并解引用得到动画数
   `v1 = *(u32*)(dword_827F734 + 177049)` ⇒ **`177049 × 4 = 708,196 = 0xACE64`** ✓
   `*(u32*)(dword_827F734 + 26624) = *v1` ⇒ **`26624 × 4 = 106,496 = 0x1A000`** ✓
        ↓
★★★ ⇒ **"用 context 槽检查'动画树在不在'是在检查一个没人写的字"**
```

### ★★★ 两个 `static_assert`（第 1099–1103 行）

```cpp
static_assert(
    AnimTreeContextOffset + 4 * sizeof(std::uint32_t) <= ServerCharacterInfoBaseOffset,
    "the anim tree handle and context must not run into the derived "
    "characterInfo array inside the shared anim-condition storage");
```
★★★ **⇒ `0xACE70 + 16 = 0xACE80` ≤ **`0xAF350`** ✓（差 **`0x24D0`** = 9,424 字节）。**

---

## 五、★★★★★ **十个动画回调的 `+0x18530` 重定位**

### 5.1 ★★★★★ 完整注释（第 1206–1262 行，逐字）

```cpp
// CODDIFF(1649370): **THIS WHOLE BLOCK IS RELOCATED BY +0x18530 AND WAS NOT PORTED.**
// The shared anim-condition storage moved its derived characterInfo array from
// 3.3.3.3's **0x96E20** to this build's **0xAF350** -- **a delta of 0x18530**,
// already carried by ServerCharacterInfoBaseOffset. **Everything that lives just
// BEFORE that array moved with it, and these nine did not.**
//
// **Four of them are confirmed directly against out.exe**, not inferred from the delta.
// **BG_UpdatePlayerDObj (sub_40AB30)** reaches the callbacks through the storage base:
//     **(*((void (__cdecl **)(...))dword_827F730 + 179402))(...)   7 args -> CREATE**
//     **(*((... **)dword_827F730 + 179403))(&v53, v39, a5, a2)     4 args -> APPEND**
//     **(*((... **)dword_827F730 + 179404))(*(_DWORD *)a4, a2)     2 args -> FREE**
// which are **byte offsets 717608, 717612 and 717616** -- exactly
// **0x96DF8, 0x96DFC and 0x96E00 plus 0x18530**. **The argument counts match
// this project's own adapter signatures.** And **both that function and
// sub_407EA0** test
//     ***((_BYTE *)dword_827F730 + 717596)**
// which is **0x96DEC + 0x18530**, the asymmetric anim-script flag.
//
// **The old values were wrong twice over.** **0x96DD8..0x96E04 all sit BELOW
// AnimTreeContextOffset 0xACE70**, and **BG_FindAnimTrees memsets 0xACE70 bytes
// from the base** -- so **the callbacks this project installed were not merely in
// the wrong place, they were inside the region the engine zeroes on every
// anim-tree load**. **The corrected offsets sit above it, between the anim array
// and the characterInfo array**, which is where **a clock and a callback table
// belong**.
```

★★★★★ **⇒ 八个精确值：**
```
delta = **`+0x18530`**（`0xAF350 - 0x96E20` = **`0x18530`** ✓）
        ↓
★★★ **四个直接确认**：`dword_827F730 + 179402/179403/179404`
★★★ = 字节偏移 **717608 / 717612 / 717616**
★★★ = **`0x96DF8` / `0x96DFC` / `0x96E00` + `0x18530`**
★★★ 三个参数数：**7（CREATE）/ 4（APPEND）/ 2（FREE）**
★★★ 第四：`dword_827F730 + 717596` = **`0x96DEC + 0x18530`**（asymmetric anim-script flag）
        ↓
★★★★★ ⇒ **旧值错两次：**
   ① **`0x96DD8..0x96E04` 全部**低于** `AnimTreeContextOffset = 0xACE70`**
   ② **`BG_FindAnimTrees` 从基址 memset `0xACE70` 字节**
   ⇒ **装的回调不仅在错的位置,而且在引擎每次动画树加载都会清零的区域内**
        ↓
★★★ 修正后位于**动画数组与 characterInfo 数组之间**
```

### ★★★★★ **十个回调的完整表**（第 1273–1285 行）

| # | 偏移 | RVA | 用途 |
|---|---|---|---|
| 0 | **`0xAF320`** | **`0x053430`** | — |
| 1 | **`0xAF324`** | ★ **`0x053420`** | ★ **被 `0x0040AD1F` 无空检查调用** |
| 2 | **`0xAF328`** | **`0x0535B0`** | ★ **CREATE DObj** |
| 3 | **`0xAF32C`** | **`0x0534A0`** | ★ **APPEND weapon model** |
| 4 | **`0xAF330`** | **`0x26BF60`** | ★ **FREE DObj** |
| 5 | **`0xAF334`** | **`0x053600`** | ★ **GET DObj** |
| 6 | **`0xAF338`** | ★ **`0x368220`** | ★ **`HunkAllocXAnim`** |
| 7 | **`0xAF33C`** | ★ **`0x368220`** | ★ **`HunkAllocXAnim`**（同一个） |
| 8 | **`0xAF348`** | **`0x049030`** | — |
| 9 | **`0xAF34C`** | **`0x048FF0`** | — |

### ★★★★★ **`BG_UpdatePlayerDObj` 的 `op=8` 故障**（第 1243–1249 行，逐字）

```cpp
// **THAT IS THE `BG_UpdatePlayerDObj` FAULT, AND IT WAS NEVER AN ABI MISMATCH.**
// **sub_40AB30 reaches its callbacks as `mov edx, [ecx + 0xAF324]; push eax;
// call edx` at 0x0040AD1F, with no null check** -- so **a zero slot is CALLED**,
// and **the witness reports `code=0xC0000005 op=8 target=0x00000000`**.
// **op 8 is a DEP violation: the CPU tried to EXECUTE address zero.**
// **Only 0xAF32C is guarded** (`test eax, eax; je` at 0x0040AE28), which is why
// **the one slot this project deliberately nulls was never the one that crashed**.
```

★★★★★ **⇒ 五个精确值：**
```
`sub_40AB30` 在 **`0x0040AD1F`** 做 **`mov edx, [ecx + 0xAF324]; push eax; call edx`**
        ↓
★★★ **无空检查** ⇒ **零槽被 CALL**
★★★ 见证器报 **`code=0xC0000005 op=8 target=0x00000000`**
★★★ **`op 8` = DEP 违规** ⇒ **CPU 试图执行地址 0**
        ↓
★★★ **只有 `0xAF32C` 被守护**（`0x0040AE28` 的 `test eax, eax; je`）
★★★ ⇒ **本项目故意置空的槽从来不是崩溃的那个**
```

### ★★★★★ **三条独立确认**（第 1264–1272 行，逐字）

```
// **THREE MORE CONFIRMATIONS, none of which shares a step with that arithmetic:**
//   * **entries 6 and 7 come out at RVA 0x368220, which is HunkAllocXAnimRva** --
//     already bound and prefix-guarded here from a **different derivation**.
//   * the **get-DObj entry comes out at 0x053600**, and its body is
//     **`movzx eax, word [eax*2 + 0x7855720]`** against 3.3.3.3's
//     **`[eax*2 + 0x2EF4858]`** -- the same client DObj map **sub_53DF40 indexes
//     at 0x0053DFC9** to find the DObj it hands BG_UpdatePlayerDObj.
//   * the **CONSUMER COUNT per slot matches across builds**: **2/1/1/2/3/1/1/1**
//     for **0x96DF4..0x96E1C** against **0xAF324..0xAF34C**.
```

★★★★★ **⇒ 三个独立确认：**
```
① 条目 **6 和 7** 落在 **`0x368220`** = **`HunkAllocXAnimRva`** ⇒ 从**另一条推导**已绑定并前缀守护
② get-DObj 条目在 **`0x053600`**,体是 **`movzx eax, word [eax*2 + 0x7855720]`**
   （3.3.3.3 是 `[eax*2 + 0x2EF4858]`）⇒ 同一个客户端 DObj 映射
③ **每个槽的消费者计数跨 build 匹配**：**2/1/1/2/3/1/1/1**
```

### ★★★ 四个具名回调偏移（第 1286–1289 行）

```cpp
ServerCreateDObjCallbackOffset        = **0xAF328**;
ServerAppendWeaponModelCallbackOffset = **0xAF32C**;
ServerFreeDObjCallbackOffset          = **0xAF330**;
ServerGetDObjCallbackOffset           = **0xAF334**;
```

### ★★★★★ **两个 `static_assert` 把表与具名常量绑死**（第 1294–1306 行）

```cpp
static_assert(
    ServerCreateDObjCallbackOffset == ServerAnimationCallbackRvas[2].first &&
    ServerAppendWeaponModelCallbackOffset == ServerAnimationCallbackRvas[3].first &&
    ServerFreeDObjCallbackOffset == ServerAnimationCallbackRvas[4].first &&
    ServerGetDObjCallbackOffset == ServerAnimationCallbackRvas[5].first,
    "the stock callback table and the four adapter slots must name the same "
    "four offsets -- **they were 0x96DF8..0x96E04 and 0xAF328..0xAF334 at once**");
static_assert(
    ServerAnimationCallbackRvas[6].second == HunkAllocXAnimRva &&
    ServerAnimationCallbackRvas[7].second == HunkAllocXAnimRva,
    "out.exe's installer writes HunkAllocXAnim into both of these slots, and "
    "that binding is derived independently and prefix-guarded");
```

★★★ **⇒ 第一个 `static_assert` 是 **`==`** 而不是 `<=`（注释第 1603–1604 行逐字）：**
```
"**== and not <=.** The three carried numbers section 59 and section 60 found
 **all survived a bound, because every value smaller than the answer satisfies one.**"
```

### ★★★ 五个时钟与标志偏移（第 1229–1233 行）

```cpp
AnimFrameTimeOffset              = **0xAF308**;
AnimSnapshotTimeOffset           = **0xAF30C**;
AnimUserOffset                   = **0xAF314**;
AnimTreeMaskOffset               = **0xAF318**;
AsymmetricAnimScriptFlagOffset   = **0xAF31C**;
```

---

## 六、★★★★★ **`CharacterInfoDObjDirtyOffset 560 → 660`**

### 6.1 ★★★★★ 完整注释（第 1107–1125 行，逐字）

```cpp
// CODDIFF(1649370): **BOTH OF THESE WERE 3.3.3.3's AND BOTH ARE +100 HERE**, which is
// the same **+0x64** shift sv_native_characterinfo_mp.cpp already derived for
// **0x1F4..0x208 -> 0x258..0x26C**. **These two sat in the same struct and were missed.**
//
// Read straight off **BG_UpdatePlayerDObj (sub_40AB30, RVA 0x00AB30)**, where a5 is the
// characterInfo:
//   ***(_DWORD *)(a5 + 660)  is the REBUILD flag** -- the early-out is
//       **`if (*(a5 + 924) == v12 && !*(a5 + 660)) return 0;`**
//       and the function **clears it on the way out with `v18[165] = 0`** (165*4 = 660).
//   ***(_DWORD *)(a5 + 900)  is the ANIM TREE** -- it is loaded into v46 and passed as
//       **the third argument of the DObj create**, which is `tree` in this project's own
//       serverDObjCreateAdapter signature.
// **Neither 560 nor 800 appears anywhere in that function.**
//
// **The consequence of the first one is not cosmetic**: **writing the dirty flag to 560
// left the engine's flag at 660 clear, so BG_UpdatePlayerDObj took its early-out and
// never rebuilt the player DObj at all.**
constexpr std::size_t CharacterInfoDObjDirtyOffset = **660**;
constexpr std::size_t CharacterInfoAnimTreeOffset  = **900**;
```

★★★★★ **⇒ 七个精确值：**
```
两个偏移：**560 → 660**（dirty flag）/ **800 → 900**（anim tree）
位移 = **+100** = **`0x64`**
        ↓
★★★ 早退条件：**`if (*(a5 + 924) == v12 && !*(a5 + 660)) return 0;`**
★★★ 清除：**`v18[165] = 0`** ⇒ **`165 × 4 = 660`** ✓
★★★ anim tree 在 **`a5 + 900`**,作为 **DObj create 的第三个参数**
        ↓
★★★ **`560` 和 `800` 在那个函数里**一次都没出现**
        ↓
★★★★★ ⇒ **写 `560` ⇒ 引擎的 `660` 保持清零 ⇒ `BG_UpdatePlayerDObj` 走早退 ⇒ **从不重建玩家 DObj**
```

### ★★★★★ **同族的 `+100` 位移**（第 1352–1364 行，逐字）

```cpp
// CODDIFF(1649370): **0x288 AND 0x2A0 WERE 3.3.3.3'S.** sub_407790 -- the
// condition walker BG_AnimScriptEvent calls to pick an animation -- reads
// **`*(DWORD *)(characterInfo + 8 * conditionIndex + 748)`** and its partner at
// **+752**, so **the array base on this build is 748 = 0x2EC with an 8-byte stride**.
// **That is +100 from 3.3.3.3**, and it is **the SAME +100 already measured for two
// of its neighbours**: **CharacterInfoDObjDirtyOffset 560 -> 660** and
// **CharacterInfoAnimTreeOffset 800 -> 900**. **Three fields in one region agreeing
// on the shift is what makes this a relocation rather than a coincidence.**
//
// The movetype slot is carried by INDEX, not re-derived: **0x2A0 - 0x288 = 24
// is condition slot 3**, so it is **748 + 24 = 772** here.
```

★★★★★ **⇒ 五个精确值：**
```
`sub_407790` 读 **`characterInfo + 8*conditionIndex + 748`** 和 **`+752`**
        ↓
★★★ ⇒ 数组基址 **`748 = 0x2EC`**,步长 **8**
★★★ ⇒ **`0x288 + 100 = 748`** ✓
★★★ **三个字段在同一区域都同意 `+100`** ⇒ **是重定位而非巧合**
        ↓
★★★ movetype 槽按**索引**携带：**`0x2A0 - 0x288 = 24`** ⇒ **条件槽 3**
★★★ ⇒ **`748 + 24 = 772`** = **`0x304`** = `CharacterInfoMoveTypeConditionOffset`
```

### ★★★★★ **条件数 38 → 19**（第 1367–1375 行，逐字）

```cpp
// CODDIFF(1649370): **THIS WAS 38 AND out.exe SAYS 19.** The condition NAME
// table at **VA 0x00E60828** terminates with **{0, 0xFFFFFFFF} at index 19**
// (**VA 0x00E608C0**), and the parallel condition-TYPE table **sub_407790**
// indexes as **dword_E608C8[2 * conditionIndex]** begins one entry later at
// **VA 0x00E608C8** with **nineteen entries of its own**. **Counting 38 made
// `nonzero=N/38` below read nineteen real condition slots plus nineteen
// slots of unrelated characterInfo at 0x384..0x41C**, so **the number it
// printed was the measurement plus its neighbours.**
```

★★★★★ **⇒ 五个精确值：**
```
条件名表 **`VA 0x00E60828`**,在**索引 19** 处以 **`{0, 0xFFFFFFFF}`** 终止（**`VA 0x00E608C0`**）
        ↓
★★★ 并行类型表 **`dword_E608C8[2 * conditionIndex]`**,从 **`0x00E608C8`** 开始,**19 个条目**
        ↓
★★★ ⇒ 数 38 ⇒ `nonzero=N/38` **读了 19 个真条件槽 + 19 个 `0x384..0x41C` 的无关 characterInfo**
★★★ ⇒ **"它打印的数字是测量值加上它的邻居"**
```

### ★★★ `ScrAnimTree` 的六个偏移（第 1404–1409 行）

```cpp
ScrAnimTreeObjectRva              = **0x749C528**;
ScrAnimLoadingOffset              = **0x118**;
ScrAnimTreeCountOffset            = **0x10C**;
ScrAnimTreeParsingOffset          = **0x00C**;
ScrSecondaryAnimTreeObjectOffset  = **0x004**;
ScrAnimTreeScratchOffset          = **0x158**;
```

★★★★★ **⇒ 完整注释（第 1382–1403 行，逐字）：**
```
"CODDIFF(1649370): **ALL SIX OF THESE WERE 3.3.3.3'S, BYTE FOR BYTE.**
 **0x2B371B8 has ZERO cross-references in out.exe** -- the engine **neither reads nor
 writes it** -- so **Scr_BeginLoadAnimTrees' reproduction was setting the anim-tree
 loading state in a place nothing looks at**, and **the script parse's asset lookups
 took the LOAD path instead of the register-for-precache one**. **That is what reached
 the asset database's inline load pump and killed the process.**
        ↓
★★★ 真块是 `CL_ParseGamestate` 在 **`0x454C1A`** 写的那个：
   **`0x454C21 mov byte_789C640, 1`** ⇒ loading **`+0x118`**
   **`0x454C28 mov dword_789C634, edi`** ⇒ count **`+0x10C`**
   **`0x454C2E mov dword_789C534, edi`** ⇒ parsing **`+0x00C`**
   **`0x454C34 call sub_74CED0`** ⇒ `Scr_CreateObject`
   **`0x454C4D mov dword_789C528, eax`** ⇒ the object **`+0x000`**
   **`0x454C52 mov dword_789C52C, edi`** ⇒ secondary **`+0x004`**
   **`0x454C58 mov dword_789C680, edi`** ⇒ scratch **`+0x158`**
        ↓
★★★ **"六个偏移里有两个碰巧没变；结构体的头是稳定的,尾巴移动了。
   这正是为什么'因为看起来还对'就移植偏移不奏效。"**
```

---

## 七、★★★★★ **`ItemDefinitionSize 40 → 52`**

### 7.1 ★★★★★ 完整注释（第 1527–1554 行，逐字）

```cpp
// CODDIFF(1649370): **40 IS 3.3.3.3's AND IT WAS WRONG BY TWELVE BYTES PER RECORD**,
// and **this file already said so eight hundred lines away**: "indexes
// CharacterItemDefinitionTable at **stride 52** by the u16 at +2". **The constant that
// actually places the record was never moved to match** -- **section 51k's rule, and
// the third time it has cost this port.**
//
// **out.exe writes the same three-instruction sequence at FOUR independent sites and
// every one of them uses 0x34.** The first is the exact counterpart of the code
// below, `baseItemDefinition + 2` and all:
//     **0044E1F0  movzx eax, word ptr [eax + 2]     <- the record index**
//     **0044E1F4  cmp   eax, [0x7798900]            <- the count**
//     **0044E1FC  imul  eax, eax, 0x34              <- THE STRIDE**
//     **0044E1FF  add   eax, [0x77988FC]            <- the table**
// and **0x0061B859, 0x00619C1D and 0x00660A94 agree**. `tools/runtime/
// CodolCharacterCategoryDump.py` has read the same table with the same **0x34** on a
// live client since section 67, **across 54 records and twelve characters**.
//
// **WHAT IT COST, and it is not cosmetic: the two bytes read out of this record are
// the FEMALE flag and the COLOUR selector.** At **record index 0 the two strides agree**
// and **every measurement this project has taken was on character 0**; at **index 1 they
// are already twelve bytes apart**, so **any player on a character other than the first
// would have been given another character's sex and colour -- silently, with no error**,
// which is **section 48d's failure mode exactly**.
constexpr std::size_t CharacterItemDefinitionSize = **52**;
static_assert(
    CharacterItemDefinitionSize == **0x34**,
    "out.exe indexes CharacterItemDefinitionTable with imul reg, reg, 0x34 at "
    "0x0044E1FC, 0x0061B859, 0x00619C1D and 0x00660A94");
```

★★★★★ **⇒ 八个精确值：**
```
`40`（3.3.3.3）→ **`52` = `0x34`**（本 build）⇒ **每条记录错 12 字节**
        ↓
★★★ 四个独立站点：**`0x0044E1FC`** / **`0x0061B859`** / **`0x00619C1D`** / **`0x00660A94`**
★★★ 四条指令：`movzx eax, word[eax+2]` / `cmp eax,[0x7798900]` / **`imul eax,eax,0x34`** / `add eax,[0x77988FC]`
        ↓
★★★ `CodolCharacterCategoryDump.py` 用同样 `0x34` 读**54 条记录 × 12 个角色**
        ↓
★★★★★ ⇒ **代价不是装饰：记录里读出的两个字节是**女性标志**和**颜色选择器****
★★★ **索引 0 时两个步长一致** ⇒ **本项目所有测量都在角色 0 上**
★★★ **索引 1 时已差 12 字节** ⇒ **任何非第一个角色的玩家会被赋予**另一个角色的性别和颜色**
   ⇒ **静默、无错误** = **section 48d 的失败模式**
```

### ★★★ `ItemDefinition` 的三个偏移（第 1410–1444 行）

```cpp
ItemDefinitionSize              = **40**;      // ★ 通用物品定义（不是角色定义）
ItemDefinitionNameOffset        = **8**;       // ★ 武器资产名
ItemDefinitionFlagsOffset       = **4**;       // ★ category 在 flags >> 8
ItemDefinitionRecordEntryOffset = **6**;       // ★ 记录条目
ItemCategoryCharacter           = **2**;
ItemCategoryCharacterPiece      = **3**;
```

★★★★★ **⇒ 完整注释（第 1411–1421 行，逐字）：**
```
"CODDIFF(1649370): **12 is 3.3.3.3's, and on this build it is the DISPLAY KEY,
 not the internal name.** **The definition gained a field ahead of it.** Dumped live
 from item 10001:
     **+8  = m4_mp**                  <- the weapon asset name
     **+12 = sf_weapon_m4_mp_name**   <- localisation key
     **+16 = sf_weapon_m4_mp_desc**   **+20 = wea_m4_item_icon**
        ↓
★★★ **Reading +12 handed the weapon resolver "sf_weapon_m4_mp_name", which is not
 a weapon**, so **it returned 0 and every class in every loadout was skipped with
 base_weapon_resolver**. **The two strings differ by a suffix**, which is why this
 read as **"the item is missing on this build"** for as long as only the id was logged."
```

### ★★★★★ **`+4` / `+6` 的语义**（第 1423–1444 行，逐字）

```cpp
// **THE ITEM RECORD'S OWN CATEGORY AND SLOT, at +4 and +6.** A definition is
// **{u16 id, u16 slot, u16 flags, u16 recordEntry, char *name, ...}** -- the same
// four leading shorts Tools/olfinal/marketplace-decode.py reads out of the
// zone, and the engine's own use of them pins both:
//
//   **sub_61B7D0 tests `*(BYTE *)(definition + 5) == 2`** before it will treat an
//   item as a character -- that is **the HIGH BYTE of the u16 at +4**, so the
//   **category lives in flags >> 8**: **2 is a character, 3 is a character piece.**
//
//   **+6 is which RECORD ENTRY the piece occupies**, and the engine published the
//   proof itself. **Character 569 resolved live to
//       record=569,555,525,552,1139,561,-,564**
//   and the zone gives those pieces recordEntry 1,2,3,4,5 and 7** -- exactly the
//   entries sub_619AD0 put them in. **A character's own entry is 0.**
```

★★★★★ **⇒ 五个精确值：**
```
定义前四个 short：**`{u16 id, u16 slot, u16 flags, u16 recordEntry, char *name, ...}`**
        ↓
★★★ **`sub_61B7D0` 测 `*(BYTE*)(definition + 5) == 2`** ⇒ **`+4` 的**高字节** ⇒ category = `flags >> 8`**
★★★ **2 = 角色**,**3 = 角色部件**
        ↓
★★★ **`+6` = 记录条目**
★★★ 实测：角色 **569** 解析为 **`record=569,555,525,552,1139,561,-,564`**
★★★ 该区的 `recordEntry` 是 **1,2,3,4,5,7** ⇒ 与 `sub_619AD0` 放的完全一致
★★★ **角色自己的条目是 0**
```

### ★★★★★ **`AttachmentSlotTables` 的 15 个条目**（第 1463–1480 行）

| # | 表名 | slot |
|---|---|---|
| 1 | `mp/coweapitems**bas**.csv` | **3** |
| 2 | `mp/coweapitems**cqc**.csv` | **13** |
| 3 | `mp/coweapitems**hbs**.csv` | **4** |
| 4 | `mp/coweapitems**iro**.csv` | **10** |
| 5 | `mp/coweapitems**muz**.csv` | **2** |
| 6 | `mp/coweapitems**rai**.csv` | **6** |
| 7 | `mp/coweapitems**ret**.csv` | **15** |
| 8 | `mp/coweapitems**sco**.csv` | **1** |
| 9 | `mp/coweapitems**sto**.csv` | **5** |
| 10 | `mp/coweapitems**gri**.csv` | **7** |
| 11 | `mp/coweapitems**bip**.csv` | **8** |
| 12 | `mp/coweapitems**sra**.csv` | **9** |
| 13 | `mp/coweapitems**mag**.csv` | **11** |
| 14 | `mp/coweapitems**cam**.csv` | **12** |
| 15 | `mp/coweapitems**dec**.csv` | **16** |

### ★★★★★ **为什么是 `mp/coweapitemsXXX.csv` 而非 `mp/coweapitems/`**（第 1449–1462 行，逐字）

```
"CODDIFF(1649370): **the last five were `mp/coweapitems/gri.csv`** -- a **SUBDIRECTORY
 form that does not exist in this build's zone**. Decrypted
 **`common_marketplace_lite.ff`** (`ff_init_common_marketplace_V95.ifs`) and listed its
 StringTable assets: **sixteen tables, every one of them flat `mp/coweapitemsXXX.csv`**,
 and **the string `coweapitems/` appears NOWHERE in the zone**. **The lookup returned no
 table for the tenth entry and the old loop treated that as fatal**, so **EVERY equipped
 attachment failed as `equipped_attachment_slot`** no matter which slot it was in.
        ↓
★★★ **The same zone settles the two tables not listed here.** Its WEA table's slot-name
 column uses exactly these fourteen -- **iro mag rai sco hbs muz cam sto gri bas bip sra
 cqc ret** -- so **`mp/coweapitemsdec.csv` is not a loadout slot**, and **`rof` (slot 14 in
 SlotNames) has no table on this build** because nothing equips it."
```

### ★★★ 16 个 `SlotNames`（第 3536–3553 行）

```cpp
"wea", "sco", "muz", "bas", "hbs", "sto", "rai", "gri",
"bip", "sra", "iro", "mag", "cam", "cqc", "rof", "ret",
"dec",   // ★ 第 17 个（索引 16）
```

★★★ **⇒ 索引：`wea`=0 / `sco`=1 / `muz`=2 / `bas`=3 / `hbs`=4 / `sto`=5 / `rai`=6 / `gri`=7 /
`bip`=8 / `sra`=9 / `iro`=10 / `mag`=11 / `cam`=12 / `cqc`=13 / `rof`=14 / `ret`=15 / **`dec`=16**。**
**⇒ 与上表的 slot 值**完全一致** ✓（`dec` 是 16,`rof` 无表）。**

### ★★★★★ **`dec` 的实测日志**（第 3544–3552 行，逐字）

```
// DECORATION (`dec_*`). These items arrive from the client profile like any
// other attachment, but **with no name here every one of them leaves
// readAttachmentModelSlot as `slot=none` and is dropped before the weapon string
// is built** -- the live log says
//   **attachment slot unresolved name=dec_littlesis**
//   **tables=.............. slot=none**
//   **attachment skipped item=16807 weapon=msrmodern_mp has no model slot**
// **The table is mp/coweapitemsdec.csv and the naming rule is the same one that
// produced cam/iro/mag/sto, so the spelling is read off the asset rather than guessed.**
```

---

## 八、★★★★★ **`WeaponDef` 的七个不同位移**

### 8.1 ★★★★★ 完整注释（第 1481–1489 行，逐字）

```cpp
// CODDIFF(1649370): **THE WHOLE WeaponDef MOVED. Every offset below was
// 3.3.3.3's, and the struct grew in SEVEN separate places between the builds,
// so NO SINGLE DELTA FIXES IT** -- **the shift is +268 at the head, +308 across
// the ammo block, +312, +320, +344, +348 and +352 by the tail**.
// `Tools/olfinal/struct-offset-uses.py` lists every instruction that touches an
// offset in either image; **each value here is named by out.exe's OWN code, with
// the deriving function in the comment**. **The three that carry no function
// reference are bracketed on both sides by confirmed neighbours at fixed stride,
// which pins them exactly.**
```

★★★★★ **⇒ 七个位移：`+268` / `+308` / `+312` / `+320` / `+344` / `+348` / `+352`。**
**⇒ 工具：`Tools/olfinal/struct-offset-uses.py`。**

### ★★★★★ **`WeaponDef` 的 32 个偏移**

| 偏移 | 字段 | 出处 |
|---|---|---|
| **1416** | `WeaponType` | ★ `sub_42BF80 == 3` |
| **1420** | `WeaponClass` | ★ `sub_421DE0 == 11` |
| **1424** | `WeaponPenetrateType` | 在 1420/1428 之间 |
| **1428** | `WeaponImpactType` | ★ `sub_421DE0 == 2` |
| **1432** | `WeaponFireType` | ★ `sub_426320` |
| **2028** | `WeaponAmmoIndex` | `sub_42EC80` 写 |
| **2036** | `WeaponClipIndex` | `sub_42EE90` 写 |
| **2040** | `WeaponMaxAmmo` | `sub_42BF80` |
| **2044** | `WeaponShotCount` | 在 2040/2048 之间 |
| **2072** | `WeaponMeleeDamage` | `sub_4BC1D0` |
| **2088** | `WeaponFireDelay` | `sub_426320` |
| **2188** | `WeaponDropTime` | `sub_423CF0` putaway |
| **2192** | `WeaponRaiseTime` | `sub_424470` raise |
| **2348** | `WeaponOverlayReticle` | `sub_421DE0 != 3` |
| **2384** | `WeaponHipSpreadStandMin` | ★ `sub_423060` 的十一次读 |
| **2388** | `WeaponHipSpreadCrouchMin` | 同上 |
| **2392** | `WeaponHipSpreadProneMin` | 同上 |
| **2396** | `WeaponHipSpreadStandMax` | 同上 |
| **2400** | `WeaponHipSpreadCrouchMax` | ★ 与 `sub_422AA0` **完全相同** |
| **2404** | `WeaponHipSpreadProneMax` | 同上 |
| **3096** | `WeaponAdsSpread` | `sub_56C510` |
| **3344** | `WeaponDamage` | `sub_591790` |
| **3368** | `WeaponDamageRange` | `sub_432510` 索引 |
| **3404** | `WeaponHitLocationMultipliers` | — |
| **3688** | `WeaponClipSize` | `sub_432E90` |
| **3696** | `WeaponFireTime` | `sub_433360` |
| **3802** | `WeaponRifleBullet` | `sub_5923C0` |
| **3806** | `WeaponAimDownSight` | `sub_433910` / `sub_434680` |
| **3810** | `WeaponBulletExplosiveDamage` | — |
| **3865** | `WeaponAmmoCountClipRelative` | `sub_42BF80` |
| ★ **`0xEEC`** = **3820** | `WeaponDualWieldCapable` | ★ `BG_DualWieldActive 0x433030` |
| ★ **3704**（报告 127） | 穿透系数 | 本报告未列 |
| ★ **3708**（报告 127） | 厚度损失 | 本报告未列 |

★★★ **⇒ 与报告 127 的 `WeaponDef + 3704`（`0xE78`）和 `+3708`（`0xE7C`）**互补** ✓**

### ★★★★★ **`MaximumWeaponFireType = 10`**（第 1523–1526 行，逐字）

```cpp
// CODDIFF(1649370): **6 was 3.3.3.3's highest fire type.** out.exe compares
// this field against **7, 8, 9 and 10** as well (**sub_426320 tests == 10**), so
// **the old bound rejected four fire types that exist on this build.**
constexpr std::int32_t MaximumWeaponFireType = **10**;
```

### ★★★★★ **`NativeCharacterItemRecord` 的 12 字节**（第 1568–1606 行，逐字）

```cpp
// CODDIFF(character_item_record): **TWELVE bytes on OLfinal, not eight**, and the
// difference is **not padding** -- there is **a whole dword this build's decode needs
// and 3.3.3.3's shape does not have**.
//
// Read off **sub_619E90**, which is the function this file binds as
// **CharacterCurrentItemsCopyRva**, so **this is its own call site and not a nearby one**:
//
//     **619ed0  lea ebx, [ecx+4]        ; ecx = the destination, entry 0 presence**
//     **619ee6  lea esi, [ebx-4]        ; the entry BASE is destination + 12k**
//     **619ef3  mov dword ptr [ebx+4], 0    ; the high dword, at +8**
//     **619efa  mov byte ptr [ebx], 0       ; the presence byte, at +4**
//     **619f00  add ebx, 0Ch            ; TWELVE, twelve times**
//     **619f08  cmp byte ptr [ecx+4], 0 ; entry 0's presence, again at +4**
//
// and its only caller **memsets the destination to 0x90 = 144 = 12 x 12** before
// every call (**0x618bad**). **At eight bytes an array of twelve is 96, so the engine
// wrote FORTY-EIGHT BYTES PAST IT** -- and **it does that on BOTH arms**, because the
// **sub_6206B0-said-no path at 0x619eb0 still walks all twelve entries at stride
// twelve**. **A stack overrun in the frame thread, latent only because
// captureClientLoadoutRequest cannot currently reach the call.**
```

★★★★★ **⇒ 七个精确值：**
```
六条指令：`0x619ED0` / `0x619EE6` / `0x619EF3` / `0x619EFA` / **`0x619F00 add ebx, 0Ch`** / `0x619F08`
        ↓
★★★ 调用者 **`0x618BAD`** memset **`0x90` = 144 = 12 × 12**
★★★ ⇒ **8 字节 × 12 = 96** ⇒ **引擎写超 48 字节**
★★★ **两条路径都这样**（`0x619EB0` 的"`sub_6206B0` 说不"路径仍走 12 项 × 12 步长）
★★★ ⇒ **帧线程上的栈溢出,只因 `captureClientLoadoutRequest` 当前到不了该调用而潜伏**
```

### ★★★ 结构体与两个 `static_assert`（第 1595–1606 行）

```cpp
struct NativeCharacterItemRecord
{
    std::uint32_t encodedLow{};          // +0
    std::uint8_t present{};              // +4
    std::array<std::uint8_t, 3> padding{}; // +5..7
    std::uint32_t encodedHigh{};         // +8
};
static_assert(sizeof(NativeCharacterItemRecord) == 12);
static_assert(sizeof(NativeCharacterItemRecord) * 12 == 0x90);
```

### ★★★★★ **`decodeCharacterItemId` 与 `encodeCharacterItemId`**（第 1613–1638 行）

```cpp
[[nodiscard]] constexpr std::uint32_t decodeCharacterItemId(
    const NativeCharacterItemRecord &record, const std::uint32_t decodeKey) noexcept
{
    return std::rotl(decodeKey ^ record.encodedLow ^ record.encodedHigh, 8);
}

[[nodiscard]] constexpr NativeCharacterItemRecord encodeCharacterItemId(
    const std::uint32_t itemId, const std::uint32_t decodeKey) noexcept
{
    NativeCharacterItemRecord record{};
    record.present = 1;
    record.encodedLow = 0;
    record.encodedHigh = std::rotr(itemId, 8) ^ decodeKey;
    return record;
}
```

★★★★★ **⇒ 完整的编解码：**
```
decode：**`ROL32(key ^ low ^ high, 8)`**
encode：**`low = 0`** / **`present = 1`** / **`high = ROR32(id, 8) ^ key`**
        ↓
★★★ ⇒ 验证：`ROL32(key ^ 0 ^ (ROR32(id,8) ^ key), 8) = ROL32(ROR32(id,8), 8) = id` ✓
```

### ★★★★★ **四个 `static_assert` 锚定到**引擎写的字节****（第 1652–1663 行）

```cpp
// **AND IT IS PINNED TO A DWORD THAT WAS MEASURED, NOT TO ITSELF.** Section 51j's rule
// is that **a symmetric round trip passes even when both sides are wrong**, so
// **asserting encode-then-decode would prove nothing about either**.
//
// **0x5FCE6C73 is the literal dword sitting at manager+0xFB2 in
// C:\Games\OLfinal\codol_1649370_full.bin** -- **a recording of a real client** -- and
// **0x7ECE6C71 is that same profile's obfuscation key from manager+0x11138**.
// **The client wrote those bytes; nothing in this tree did.** If this encoder ever
// stops producing them **it stops agreeing with the engine**, and **the build fails
// here rather than a player rendering as the wrong character with no error at all**.
// **Tools/olfinal/decode-profile-blob.py --path "characterClasses[0].slots[0]"
// reads 545 back out of them.**
static_assert(encodeCharacterItemId(**545**u, **0x7ECE6C71**u).encodedHigh == **0x5FCE6C73**u);
static_assert(encodeCharacterItemId(**686**u, 0x7ECE6C71u).encodedHigh == **0xD0CE6C73**u);
static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).encodedLow == 0u);
static_assert(encodeCharacterItemId(545u, 0x7ECE6C71u).present == 1u);
```

★★★★★ **⇒ 六个精确值：**
```
`encodeCharacterItemId(545, 0x7ECE6C71).encodedHigh == **0x5FCE6C73**`
`encodeCharacterItemId(686, 0x7ECE6C71).encodedHigh == **0xD0CE6C73**`
        ↓
★★★ 锚点来源：`C:\Games\OLfinal\codol_1649370_full.bin` 的 **`manager+0xFB2`**
★★★ 密钥：`manager+0x11138` = **`0x7ECE6C71`**
★★★ ⇒ **"客户端写了那些字节;这棵树里没有任何东西写过它们"**
        ↓
★★★ 验证器：**`Tools/olfinal/decode-profile-blob.py --path "characterClasses[0].slots[0]"`** 读回 **545**
        ↓
★★★ 第 51j 的规则：**"对称往返即使两侧都错也会通过"** ⇒ 所以不 assert encode-decode
```

---

## 九、★★★★★ **`invokeSVTrace` 四个参数错误的后果**

### 9.1 ★★★★★ 完整注释（第 3162–3193 行，逐字）

```cpp
// **THIS MARSHALLING WAS 3.3.3.3's AND FOUR OF EIGHT ARGUMENTS WERE WRONG.**
//
// The whole function was **byte-identical to ..\ol-mod-ffa**. On 1649370 the target
// is
//     **void __usercall sub_46E780(
//         float *end@<ecx>, Bounds *bounds@<edx>,
//         trace_t *results, float *start, int passEntityNum, int contentMask,
//         unsigned __int8, char)**          // **SIX stack args, CALLER cleans 0x18**
//
// read out of the decompilation: **`*a3` is compared against 0.0 so a3 is the trace_t
// whose first float is the fraction**; **`a2[3] + a2[4] + a2[5] == 0.0` selects the
// point-trace branch, so a2 is a six-float Bounds** -- exactly this project's
// **TraceBounds{midpoint[3], halfSize[3]}**; and **a4 and a1 are the two endpoints**,
// each offset by the bounds midpoint, with **a4's components landing in the LOWER slots
// of the pair, which makes a4 the start and a1 the end**.
//
// **The image proves the mapping without any of that reasoning.** **sub_46EA60 is a
// pure passthrough**:
//     **sub_46EA60(a, b, c, d, e, f)
//         -> ecx = c, edx = d, push a, b, e, f, 0, 0; add esp, 18h**
// which is **plain SV_Trace(results, start, end, bounds, passEntityNum, contentMask) in
// the natural CoD order**. **sub_46E9C0 and sub_46EA10 are its point-trace siblings and
// both pass a fixed zero-Bounds global in edx.**
//
// **What the carried version did: ecx got a POINTER TO AN IGNORE STRUCT where the
// engine wanted the end position, edx got the END where it wanted the bounds, a5 got
// the bounds POINTER where it wanted an int entity number, and a7/a8 were never pushed
// at all**, so **the engine read two arguments out of this frame's stack**.
// **Measured consequence, over 1349 hits in one run: ZERO upward normals, every hit at
// fraction 0.0000 with the same hitId 2046, walkable never set** -- so **groundEntityNum
// was ENTITYNUM_NONE on every frame and the player rose about one unit per pmove call,
// forever.**
```

★★★★★ **⇒ 八个精确值：**
```
`sub_46E780` = **`void __usercall(float *end@<ecx>, Bounds *bounds@<edx>, trace_t*, float*, int, int, u8, char)`**
⇒ **六个栈参数,调用者清 `0x18`**
        ↓
★★★ `sub_46EA60` 是**纯透传**：`ecx = c` / `edx = d` / `push a,b,e,f,0,0` / `add esp,18h`
★★★ ⇒ 就是 **`SV_Trace(results, start, end, bounds, passEntityNum, contentMask)`**
        ↓
★★★★★ **旧实现的四个错误：**
   ① `ecx` 得到**忽略结构指针**（引擎要 end 位置）
   ② `edx` 得到 **end**（引擎要 bounds）
   ③ `a5` 得到 **bounds 指针**（引擎要 int 实体号）
   ④ **`a7`/`a8` 从未 push** ⇒ 引擎从**本帧栈上读两个参数**
        ↓
★★★ 实测后果（**1349 次命中**）：**零个向上法线** / **每次命中 fraction 0.0000 且 hitId 恒 2046** / **walkable 从不置位**
★★★ ⇒ **`groundEntityNum` 每帧都是 `ENTITYNUM_NONE`** ⇒ **玩家每次 pmove 上升约一单位,永远**
```

### ★★★ 正确的调用（第 3265–3281 行）

```cpp
alignas(16) std::array<std::byte, sizeof(NativeTraceResult) + 512> padded{};
__asm
{
    mov ecx, endPointer
    mov edx, boundsPointer
    push flagA8          // 0
    push flagA7          // 0
    push mask
    push passEntity
    push startPointer
    push resultPointer
    call function
    add esp, 18h
}
```

★★★ **⇒ 六个栈参数（`0x18` = 24 = 6 × 4）+ 两个寄存器。**

### ★★★★★ **为什么用 512 字节零尾**（第 3250–3261 行，逐字）

```
// **IS trace_t BIGGER THAN 0x28 ON THIS BUILD?** NativeTraceResult is
// **byte-identical to the 3.3.3.3 tree**, on a build where **entityState grew
// 0x110 -> 0x118 and playerState 0x3564 -> 0x3BBC**. **If it grew, the engine writes
// past what we model and reads back fields we never initialise** -- which is what a
// **groundEntityNum flipping 2046/2047 on consecutive slices at an unchanged origin**
// looks like, because **a deterministic trace cannot otherwise give two answers**.
```

★★★ **⇒ 两个已知增长：`entityState 0x110 → 0x118`**（+8）/ **`playerState 0x3564 → 0x3BBC`**（+1,624）。**
**⇒ 与报告 128/132 的 `0x3BBC`**一致** ✓**

---

## 十、★★★★★ **`FxGlass` 的三条精确关系**

### 10.1 ★★★★★ 完整注释（第 1045–1073 行，逐字）

```cpp
// CODREF(fxglass): **SETTLED (section 93) against every map the game ships, offline.**
// Section 71c could not settle either of these because **the only map this project runs
// has no glass at all** -- `fxglass header map=mp_rust_long definitions=0 pieceLimit=0`.
// **It never needed a glass map to be RUN**: the **FxWorld is asset type 20** in the
// map's own fastfile and **all 975 fastfiles are on disk**.
// **CODOL-main Tools/olfinal/fxglass-map-survey.py reads 37 of them and finds THREE
// exact relations, each holding on every map with glass (27 of the 37; the other ten
// are all zero, mp_rust_long among them):**
//
//     **pieceWordCount == ceil(pieceLimit / 32)**         **37/37**   the availability bitset
//     **pieceLimit     == initialPieceCount + 1024**      **27/27**   <- the one that matters
//     **geometryLimit  == 8 * pieceLimit**                **37/37**
//
// **The second one means MaximumFxGlassPieceLimit IS NOT A FREE CONSTANT**, the same
// way **section 59b's lastChanged width was not**: the map compiler sizes the piece
// array as **the initial pieces plus a FIXED 1024 of headroom for the fragments
// breaking glass creates**, and **1024 is SvGlassPieceCount** -- the same number
// **out.exe's own sparse-list reader hardcodes as its terminator** (sub_447500 @
// 0x447527: `i = BITS(11); 1024 ends it`).
// **So given the initialPieceCount check below, `pieceLimit <= 2048` FOLLOWS.** It is
// **not a plausibility guess; it is exactly the largest value the other check permits**,
// which is why **the static_assert ties them together rather than leaving two numbers
// to drift.**
//
// **The observed maxima, for whoever has to judge a future map:**
//     **definitionCount   41   mp_terminal_cls**      **pieceLimit   1903   mp_conflict**
//     **initialPieceCount 879  mp_conflict**          **cellCount    203    mp_battlecity**
// **1903 is 93% of this bound and 879 is 86% of SvGlassPieceCount**, so neither has much
// slack left -- **if a map is ever refused here, these are the numbers to print first**.
```

★★★★★ **⇒ 三条精确关系 + 四个观测最大值：**

| 关系 | 比例 |
|---|---|
| ★ **`pieceWordCount == ceil(pieceLimit / 32)`** | **37/37** |
| ★★ **`pieceLimit == initialPieceCount + 1024`** | **27/27** |
| ★ **`geometryLimit == 8 * pieceLimit`** | **37/37** |

```
四个观测最大值：
**`definitionCount = 41`**（`mp_terminal_cls`）
**`pieceLimit = 1903`**（`mp_conflict`）⇒ **93% 于 2048 上界**
**`initialPieceCount = 879`**（`mp_conflict`）⇒ **86% 于 `SvGlassPieceCount = 1024`**
**`cellCount = 203`**（`mp_battlecity`）
        ↓
★★★ `1024` 就是 **`SvGlassPieceCount`**,也是 **`sub_447500 @ 0x447527` 的 `i = BITS(11)` 终止符**
★★★ ⇒ **`pieceLimit <= 2048`** 是**推导**而非猜测
★★★ `static_assert(MaximumFxGlassPieceLimit == 2 * SvGlassPieceCount)`
```

### ★★★ 四个 `FxGlass` 结构体（第 2792–2840 行）

```cpp
struct NativeFxGlassInitPieceState   // sizeof == 52
{
    std::array<float, 4> quaternion;              // +0
    std::array<float, 3> origin;                  // +16
    float radius;                                 // +28
    std::array<float, 2> textureCoordinateOrigin; // +32
    std::uint32_t supportMask;                    // +40
    float doubledArea;                            // +44
    std::uint8_t definitionIndex;                 // +48
    std::uint8_t vertexCount;                     // +49
    std::uint8_t fanDataCount;                    // +50
    std::uint8_t padding;                         // +51
};

struct NativeFxGlassSystem   // sizeof == 112
{
    std::int32_t time;                    // +0
    std::int32_t previousTime;            // +4
    std::uint32_t definitionCount;        // +8
    std::uint32_t pieceLimit;             // +12
    std::uint32_t pieceWordCount;         // +16
    std::uint32_t initialPieceCount;      // +20
    std::uint32_t cellCount;              // +24
    std::uint32_t activePieceCount;       // +28
    std::uint32_t firstFreePiece;         // +32
    std::uint32_t geometryLimit;          // +36
    std::uint32_t geometryCount;          // +40
    std::uint32_t initialGeometryCount;   // +44
    std::array<const void *, 11> runtimePointers;  // +48..91
    const NativeFxGlassInitPieceState *initialPieceStates;  // +92 ★
    const void *initialGeometry;          // +96
    std::uint8_t needsCompaction;         // +100
    std::uint8_t initialCount;            // +101
    std::uint16_t padding;                // +102
    float effectChanceAccumulator;        // +104
    std::int32_t lastPieceDeletionTime;   // +108
};

struct NativeFxWorld  // sizeof == 116
{
    const char *name;                     // +0
    NativeFxGlassSystem glassSystem;      // +4
};
```

★★★ **⇒ 四个 `static_assert`：`52` / `92`（`initialPieceStates`）/ `112` / `4`（`glassSystem`）/ `116`。**

---

## 十一、★★★★★ **`bind()` 的 60+ 前缀守卫**

### 11.1 ★★★ `bind()` 的七个阶段（第 3662–4231 行）

```
① `bindingCommitted_ = false`（★ **失败的重绑必须撤销已提交的发布**）
② PE 身份校验（`TimeDateStamp` + `SizeOfImage`）
③ **原生实体三前缀**（`SV_LinkEntity` / `SV_UnlinkEntity` / `SV_Trace`）
④ **玩家 DObj 六前缀**（`NativeLerpFrameAccessorInitialize` / `BG_PlayerAnimation` /
   `BG_UpdatePlayerDObj` / **`DObjFree`** / `ServerDObjCreate` / **`ServerDObjGet` 的后缀**）
⑤ **约 60 个统一前缀校验**（一个巨大的 `||` 链）
⑥ 指针赋值（约 70 个）
⑦ **运行时槽校验**（`pmoveTraceHandlerSlot_` / `animConditionBasePointer_` /
   `animScriptDataPointer_` / `mantleAnims_`）
⑧ **`validateMessageBindings()`**
⑨ **`installBrushTraceGlassBridge(module_)`**
⑩ `bindingCommitted_ = true`
```

### ★★★★★ **`ServerDObjGetSuffix` 的特殊性**（第 964–966 行 + 第 3744–3748 行）

```cpp
constexpr std::array<std::uint8_t, 3> ServerDObjGetSuffix{ 0x8B, 0xC8, 0xB8 };
...
!std::equal(ServerDObjGetSuffix.begin(), ServerDObjGetSuffix.end(),
            module_ + ServerDObjGetRva + **5**)
```
★★★ **⇒ 唯一一个用**后缀**（`+5` 偏移）的守卫 ⇒ 因为函数开头是可重定位操作数。**

### ★★★ **`CurrentCharacterGetPrefix` 的 10 字节含重定位操作数**（第 988–999 行，逐字）

```cpp
// CODDIFF(1649370): was 3.3.3.3's `55 8B EC 83 E4 F8` -- **a stack-aligning prologue
// this build's function does not have**. **sub_6B87C0 opens by reading its cache
// directly**: `mov eax, ds:0E567C0h / cmp eax, -1 / jnz short`.
//
// **Bytes 1..4 are a RELOCATED absolute operand.** That would **disqualify them from
// a cross-build signature** (the byte-signature relocation trap), and **it does not
// disqualify them here**: **this guard's whole job is to ask whether the image is
// still the one the RVA was derived against, so pinning the operand makes it stricter,
// not wronger.**
constexpr std::array<std::uint8_t, 10> CurrentCharacterGetPrefix{
    0xA1, 0xC0, 0x67, 0xE5, 0x00, 0x83, 0xF8, 0xFF, 0x75, 0x1F,
};
```

★★★★★ **⇒ 五个精确值：**
```
`sub_6B87C0` 开：**`mov eax, ds:0E567C0h` / `cmp eax, -1` / `jnz short`**
        ↓
★★★ 字节：**`A1 C0 67 E5 00 83 F8 FF 75 1F`**
★★★ `A1` = `mov eax, ds:[imm32]`,`C0 67 E5 00` = **`0x00E567C0`**
★★★ `83 F8 FF` = `cmp eax, -1`,`75 1F` = `jnz +0x1F`
        ↓
★★★★★ ⇒ **字节 1..4 是可重定位绝对操作数** ⇒ **本该取消跨 build 签名资格**
★★★ **但它在这里不取消**：**"这个守卫的全部工作就是问镜像是否还是 RVA 推导时的那个,
   所以钉住操作数让它更严格,而不是更错"**
```

### ★★★ **`CharacterRecordToSelectionNamesPrefix` 的自守卫**（第 1014–1021 行，逐字）

```cpp
// sub_61B6C0, and **this one guards itself**: the **`6A 2C` at bytes 12..13** is the
// **`push 0x2C` of its own opening memset**, which is **the ELEVEN-POINTER output size
// this port depends on**. **A build whose selection-name array stopped being eleven
// dwords would fail this guard on exactly the byte that says so.**
constexpr std::array<std::uint8_t, 16> CharacterRecordToSelectionNamesPrefix{
    0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08, 0x8B, 0x45,
    0x08, 0x53, 0x56, 0x57, **0x6A, 0x2C**, 0x6A, 0x00,
};
```
★★★ **⇒ `6A 2C` = `push 0x2C` = **11 个指针 × 4 字节 = 44 = `0x2C`** ✓**

### ★★★★★ **`valid()` 故意排除四个指针**（第 4277–4289 行，逐字）

```cpp
// CODDIFF(character_customization, client_loadout_capture): **four pointers that
// 3.3.3.3 requires here are deliberately NOT part of validity on OLfinal** --
// **worldCharacterModelResolve_ and characterSelectionResolve_** because **§16a
// establishes the subsystem is absent from the build**, **weaponSlotReadStaged_ and
// currentCharacterGet_** because **no 1649370 address is established for either**.
//
// **Keeping them in this conjunction is what made the first version of this change
// fail silently**: every target still built and **all six test suites still passed**,
// while **valid() would have returned false on the first frame and taken the entire
// engine binding with it**. **Nothing in the SERVER frame calls any of the four**;
// see clientLoadoutBindingsAvailable() for the one path that does.
```

★★★★★ **⇒ 四个被排除的指针：`worldCharacterModelResolve_` / `characterSelectionResolve_` /
`weaponSlotReadStaged_` / `currentCharacterGet_`。**
**⇒ 且 `currentCharacterGet_` **实际已绑定**（第 4192–4193 行）⇒ 注释里的"未建立地址"是**过时的**（第 4189–4191 行已纠正）。**

---

## 十二、★★★★ **其余关键细节**

### 12.1 ★★★ `NativeServerEntitySize = 0x2C8` / 容量 2046 / DObj 容量 2048

```cpp
constexpr std::size_t NativeServerEntitySize = **0x2C8**;
constexpr std::uint32_t NativeServerEntityCapacity = **2046**;
constexpr std::uint32_t NativeServerDObjCapacity = **2048**;
```
★★★ **⇒ 三个精确值；`2046` 与 `hitId > 2047` 的校验**一致**（`2047` = `ENTITYNUM_NONE`）。**

### 12.2 ★★★ 五个 `Trace` 前缀的长度分布

```cpp
ComFramePrefix                    5 字节  { 0x55, 0x8B, 0xEC, 0x56, 0x57 }
DBFindXAssetHeaderPrefix          6      { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 }
DBLinkXAssetEntryPrefix          10      { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x24, 0x8B, 0x45, 0x0C, 0x8B }
MsgInitPrefix                     6
MsgWriteBitsPrefix                9
MsgWriteStringPrefix              9
LevelZoneLoadPrefix               9      { 0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x28, 0x0E, 0x00, 0x00 }
SVLinkEntityPrefix               16      { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x83, 0xEC, 0x3C, 0x53, 0x56, 0x8B, 0xF0, 0x8B, 0xCE, 0x81 }
SVTracePrefix                    10
ByteDirectionsPrefix             12      { 0x4F, 0x96, 0x06, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x44, 0xC4, 0x59, 0x3F }
ScrPrecacheAnimTreesPrefix       13
CharacterRecordFillDefaultsPrefix 16
CharacterRecordToSelectionNamesPrefix 16
```

★★★ **⇒ 最长 **16 字节**（四个），最短 **3 字节**（`ServerDObjGetSuffix`）。**
**⇒ `ByteDirectionsPrefix` 是**数据**（`0x3F59C444` = 0.85000002f）而不是代码。**

### ★★★★★ **`DObjTracelinePrefix` 的 9 字节与 `0x364` 帧**（第 820–828 行，逐字）

```cpp
// `push ebp; mov ebp,esp; and esp,-8; sub esp,364h`. **Byte-identical to 3.3.3.3's
// DObjTraceline at 0x00645DD0 for the whole prologue.**
// OLMOD(section-84): and **READ BACK off out.exe at VA 0x007825F0**
// (DObjTracelineRva 0x3825F0) -- **same nine bytes, same 0x364 frame**.
// **The guard is what enforces it; this line records that it was looked at on the
// host and not only inherited.**
constexpr std::array<std::uint8_t, 9> DObjTracelinePrefix{
    0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8, 0x81, 0xEC, 0x64,
};
```
★★★ **⇒ 9 字节：`push ebp` / `mov ebp,esp` / `and esp,-8` / `sub esp,0x364`（`81 EC 64 03 00 00` 的前两字节）。**

### ★★★ **`NativeTraceResult` 的三个副本**

★★★ **⇒ 同一个 40 字节结构在**三处**定义：**
```
`NativePmoveBindings.cpp`（报告 132）
`EngineBindings.cpp` 第 2859 行
`EngineBindings.cpp` 第 3115 行的 `encodeTraceResult`
        ↓
★★★ ⇒ 与报告 128 的 "一个结构体、两个文件" **同一模式**,这里是**三处**。
```

### ★★★ `TraceBounds` 的 `0x18`

```cpp
static_assert(sizeof(TraceBounds) == **0x18**);
```
★★★ **⇒ `midpoint[3]` + `halfSize[3]` = 24 字节 ✓**

### ★★★ `NativeDObjTraceResult` 的 `0x1C`（第 2293–2309 行）

```cpp
struct NativeDObjTraceResult
{
    float fraction;                  // +0x00  ★ SEEDED BY THE CALLER
    std::uint32_t surfaceFlags;      // +0x04
    std::array<float, 3> normal;     // +0x08  ★ MODEL SPACE
    std::uint16_t modelIndex;        // +0x14
    std::uint16_t partName;          // +0x16
    std::uint16_t partGroup;         // +0x18
    std::uint16_t pad001A;           // +0x1A
};
static_assert(sizeof(NativeDObjTraceResult) == 0x1C);
```

★★★★★ **⇒ 完整注释（第 2280–2292 行，逐字）：**
```
"Read off the **ONE caller 1649370 still has (0x0046E280)** plus the function's own
 prologue, which zeroes +4, +8..+0x10 and the three words at +0x14:
     **+0x00  fraction   SEEDED BY THE CALLER with the running best** -
                 **0x0046E1FC loads it from the trace_t before the call, so this is a
                 max, not an out-only field**
     **+0x04  surfaceFlags        -> trace_t +0x10**
     **+0x08  normal[3]  MODEL SPACE -> rotated back at 3.3.3.3's 0x005FB7DC before it
                 reaches trace_t +4**
     **+0x14  modelIndex          -> trace_t +0x1E**
     **+0x16  partName            -> trace_t +0x20**
     **+0x18  partGroup           -> trace_t +0x22**"
```

### ★★★ **`ByteDirections` 的 12 字节**

```cpp
constexpr std::array<std::uint8_t, 12> ByteDirectionsPrefix{
    0x4F, 0x96, 0x06, 0xBF, 0x00, 0x00, 0x00, 0x00, 0x44, 0xC4, 0x59, 0x3F,
};
```
★★★ **⇒ 后 4 字节 `44 C4 59 3F` = **`0x3F59C444`** = **0.85000002f**。**

### ★★★ **玻璃桥的两个站点与位移**（第 2964–2974 行）

```cpp
CallbackInstruction{ **0x268302**, **0xB4** },   // -0x4C
CallbackInstruction{ **0x2684CB**, **0xB8** },   // -0x48
constexpr std::size_t CallbackOperandOffset = **3**;
constexpr std::size_t OriginalGlassCallbackRva = **0x450A40**;
```

★★★★★ **⇒ 完整注释（第 2952–2963 行，逐字）：**
```
"both sites store the engine's own glass callback into a stack local --
 `mov [ebp-disp], offset callback` -- and the mod redirects them at SV_Glass_IsPieceSolid.
 Identified on 1649370 by the **callback ADDRESS rather than by position**: each build
 contains **exactly TWO such stores**, the owning functions correspond (the second is
 TransformedBrushModelTrace, which this file already binds), and the **callback body is
 byte-identical in both -- `32 C0 C3`, xor al,al / ret.**
        ↓
★★★ **THE DISPLACEMENT IS PER SITE ON THIS BUILD** and that is why the guard had to
 change shape. **3.3.3.3 uses -0x4C at both sites**, so one shared 3-byte prefix covered
 them. **out.exe uses -0x4C at 0x268302 and -0x48 at 0x2684CB**, because the two
 functions' stack frames **drifted independently**. **A single prefix silently fails the
 second site**, which is exactly how this presented: **bind() reaching stage=glass_bridge
 and refusing.**"
```

★★★ **⇒ 三个精确值：`0x268302`（`-0x4C` = `0xB4`）/ `0x2684CB`（`-0x48` = `0xB8`）/ 原回调 `0x450A40`。**
**⇒ 回调体 **`32 C0 C3`** = `xor al,al; ret`。**

---

## 十三、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **VEH 的理由** | 进程死在 `BG_AnimParseAnimScript` 内**无任何日志**；`__try` 无法产生也无法解释；**VEH 在任何 SEH 帧之前** |
| 2 | ★★★ 六个值得记录的码 | `ACCESS_VIOLATION` / `STACK_OVERFLOW` / `ILLEGAL_INSTRUCTION` / `PRIV_INSTRUCTION` / `IN_PAGE_ERROR` / `INT_DIVIDE_BY_ZERO` |
| 3 | ★★★ 上限 | **10 次** |
| 4 | ★★★★ 日志六字段 | `code` / `rva` / `op` / `target` / `thread` / **`stage`** |
| 5 | ★★★ `stage` 的作用 | **一个 RVA 说在哪死,不说哪个调用把它送到那里** |
| 6 | ★★★★★ **zhunt 崩溃** | **`sub_59CC70+0x1A5` 写 `[edi+3ECh]`**；`edi` = **`sub_53F5F0` 返回**（记录 `+0xF8` 类型标签不是 1/2 时为 0） |
| 7 | ★★★ 记录两字段 | **`+0x194`** 实体索引 / **`+0x1CC`** 武器索引 |
| 8 | ★★★★★ **EBP 链为何失败** | 泵 **`sub_4888B0`** 是 **FPO**（`push ecx; push esi`,无 `mov ebp,esp`）⇒ 给出**三个合理但不在路径上的地址** |
| 9 | ★★★★★ **栈扫描三判据** | 指向 `.text` + 前面是 `call` + 三种形式 **`E8`/`FF15`/`FF`**；上限 **14**；**标为 SCAN 而非 stack** |
| 10 | ★★★ 两个装载点 | dedicated（动画初始化前后）/ **client（启动时,因为崩溃在客户端）** |
| 11 | ★★★★★ **`ServerDObjGetRva` 是谓词** | `sub_74E160` = `word_77E7F20[(a1-&unk_31437A0)/712]` ⇒ **bool**；返回字面 **1** ⇒ 日志 `dobj=1` |
| 12 | ★★★ 两个除数 | **`712 = 0x2C8`**（实体）/ **`216 = 0xD8`**（DObj） |
| 13 | ★★★★★ **DObj 步长 `0xD8`** | 四个佐证：`sub_66BEE0` / `sub_74E160` / `sub_66BFF0` / `sub_66C050`；用 `0xCC` 每个 DObj 错 **`12 × index`** |
| 14 | ★★★★★ **`DObjScaleOffset = 200` 三分量** | `sub_781960` 写 **200/204/208 = 1.0f** 和 **212 = -1** ⇒ **对象达到 216** ⇒ 独立确认 `0xD8` |
| 15 | ★★★ 两个 `memset` 确认 | **`memset(dobj+20, 0, 0x88)`** ⇒ `SkelStateOffset = 20` / `SkelStateSize = 136`；清零 **160..188** |
| 16 | ★★★ DObj 十偏移 | `9`/`10`/`12`/`20`/`136`/`116`/`148`/`152`/`160`/`192` |
| 17 | ★★★ `NativeDObjModel` | **44 字节**：`model@0` / `boneName@4` / `ignoreCollision@6` / `reserved[36]@8` |
| 18 | ★★★ XModel 六偏移 | `0`/`4`/`60`/`312`/`28`/`24` |
| 19 | ★★★★★ **`AnimTreeContextOffset = 0xACE70`** | `0x454C63/0x454C68/0x454C77`；`sub_404D80` 填 `a1+4/8/12/16` |
| 20 | ★★★★★ **`AnimTreeHandleOffset = 0xACE64`** | `v1 = *(u32*)(dword_827F734 + 177049)` ⇒ **`177049 × 4 = 708,196 = 0xACE64`** |
| 21 | ★★★★★ 为何分开 | **"用 context 槽检查'动画树在不在'是在检查一个没人写的字"** |
| 22 | ★★★★★ **十个回调的 `+0x18530`** | `0xAF350 - 0x96E20 = 0x18530` |
| 23 | ★★★ 四个直接确认 | `dword_827F730 + 179402/179403/179404` = 字节 **717608/717612/717616** = `0x96DF8/0x96DFC/0x96E00 + 0x18530` |
| 24 | ★★★ 三个参数数 | **7（CREATE）/ 4（APPEND）/ 2（FREE）** |
| 25 | ★★★ 第四确认 | `dword_827F730 + 717596` = **`0x96DEC + 0x18530`**（asymmetric flag） |
| 26 | ★★★★★ **旧值错两次** | ① `0x96DD8..0x96E04` **低于** `0xACE70` ② `BG_FindAnimTrees` **memset `0xACE70` 字节** ⇒ **回调在引擎每次清零的区域内** |
| 27 | ★★★★★ **十个回调表** | `0xAF320`→`0x053430` / **`0xAF324`→`0x053420`** / `0xAF328`→`0x0535B0` / `0xAF32C`→`0x0534A0` / `0xAF330`→`0x26BF60` / `0xAF334`→`0x053600` / **`0xAF338`→`0x368220`** / **`0xAF33C`→`0x368220`** / `0xAF348`→`0x049030` / `0xAF34C`→`0x048FF0` |
| 28 | ★★★★★ **`op=8` 的故障** | `0x0040AD1F` 的 `mov edx,[ecx+0xAF324]; call edx` **无空检查** ⇒ **`op=8 target=0`**（DEP,执行地址 0） |
| 29 | ★★★ 唯一被守护的槽 | **`0xAF32C`**（`0x0040AE28` 的 `test eax,eax; je`） |
| 30 | ★★★★★ **三个独立确认** | ① 条目 6/7 = **`HunkAllocXAnimRva`** ② get-DObj 体 **`movzx eax, word[eax*2+0x7855720]`** ③ 消费者计数 **2/1/1/2/3/1/1/1** |
| 31 | ★★★ `static_assert` 用 `==` | **"`==` 而非 `<=`：比答案小的值都满足上界"** |
| 32 | ★★★ 五个时钟/标志 | `0xAF308` / `0xAF30C` / `0xAF314` / `0xAF318` / `0xAF31C` |
| 33 | ★★★★★ **`DObjDirtyOffset 560 → 660`** | 早退 `if (*(a5+924) == v12 && !*(a5+660)) return 0;`；清 `v18[165]=0`（`165×4=660`） |
| 34 | ★★★★★ **`AnimTreeOffset 800 → 900`** | 作为 DObj create 的**第三个参数** |
| 35 | ★★★ 后果 | **写 560 ⇒ 引擎的 660 保持清零 ⇒ 走早退 ⇒ 从不重建玩家 DObj** |
| 36 | ★★★★★ **三个字段同意 `+100`** | `560→660` / `800→900` / `0x288→748`（`0x2EC`） |
| 37 | ★★★ movetype 槽 | **`0x2A0 - 0x288 = 24`** ⇒ 槽 3 ⇒ **`748 + 24 = 772 = 0x304`** |
| 38 | ★★★★★ **条件数 38 → 19** | 名表 `VA 0x00E60828` 在**索引 19** 终止（`0x00E608C0`）；类型表 `dword_E608C8[2*i]` 从 `0x00E608C8` 开始 |
| 39 | ★★★ 数 38 的后果 | `nonzero=N/38` 读 **19 真槽 + 19 个 `0x384..0x41C` 的无关数据** |
| 40 | ★★★★★ **`ScrAnimTree` 六偏移** | `0x118` loading / `0x10C` count / `0x00C` parsing / `0x000` object / `0x004` secondary / `0x158` scratch |
| 41 | ★★★★★ **`0x2B371B8` 零交叉引用** | ⇒ **在没人看的地方设动画树加载状态** ⇒ **走到资产数据库的内联加载泵 ⇒ 杀死进程** |
| 42 | ★★★ 七条真指令 | `0x454C21` / `0x454C28` / `0x454C2E` / `0x454C34` / `0x454C4D` / `0x454C52` / `0x454C58` |
| 43 | ★★★★★ **`ItemDefinitionSize 40 → 52`** | **`0x34`**；四个站点 `0x0044E1FC` / `0x0061B859` / `0x00619C1D` / `0x00660A94` |
| 44 | ★★★★★ **代价** | 记录里两个字节是**女性标志**和**颜色选择器**；索引 0 时步长一致 ⇒ **所有测量都在角色 0**；索引 1 已差 12 字节 |
| 45 | ★★★★★ **`ItemDefinitionNameOffset 12 → 8`** | 实测 item **10001**：`+8 = m4_mp` / `+12 = sf_weapon_m4_mp_name` / `+16 = ...desc` / `+20 = wea_m4_item_icon` |
| 46 | ★★★ 读 `+12` 的后果 | 给武器解析器 **"sf_weapon_m4_mp_name"** ⇒ 返回 0 ⇒ **每个 loadout 的每个 class 都以 `base_weapon_resolver` 跳过** |
| 47 | ★★★★★ **`+4` 高字节 = category** | `sub_61B7D0` 测 `*(BYTE*)(def+5) == 2`；**2 = 角色,3 = 角色部件** |
| 48 | ★★★★★ **`+6` = 记录条目** | 角色 **569** 实测 `record=569,555,525,552,1139,561,-,564`；zone 的 recordEntry **1,2,3,4,5,7** |
| 49 | ★★★ 角色自己的条目 | **0** |
| 50 | ★★★★★ **15 个附件槽表** | `bas`=3 / `cqc`=13 / `hbs`=4 / `iro`=10 / `muz`=2 / `rai`=6 / `ret`=15 / `sco`=1 / `sto`=5 / `gri`=7 / `bip`=8 / `sra`=9 / `mag`=11 / `cam`=12 / `dec`=16 |
| 51 | ★★★★★ **`coweapitems/` 不存在** | 解密 `common_marketplace_lite.ff`（`ff_init_common_marketplace_V95.ifs`）：**16 张表全是扁平的 `mp/coweapitemsXXX.csv`** |
| 52 | ★★★ 后果 | 第 10 个条目找不到表 ⇒ 旧循环视为致命 ⇒ **每个已装备附件都以 `equipped_attachment_slot` 失败** |
| 53 | ★★★ 14 个 slot 名 | **`iro mag rai sco hbs muz cam sto gri bas bip sra cqc ret`**；**`dec` 不是 loadout 槽**；**`rof`（槽 14）在本 build 没有表** |
| 54 | ★★★ `dec` 的实测日志 | `attachment slot unresolved name=dec_littlesis` / `slot=none` / `attachment skipped item=16807 weapon=msrmodern_mp` |
| 55 | ★★★★★ **`WeaponDef` 七个位移** | **`+268`（头）/ `+308`（弹药块）/ `+312` / `+320` / `+344` / `+348` / `+352`（尾）** |
| 56 | ★★★ 工具 | **`Tools/olfinal/struct-offset-uses.py`** |
| 57 | ★★★ 32 个 `WeaponDef` 偏移 | `1416`/`1420`/`1424`/`1428`/`1432`/`2028`/`2036`/`2040`/`2044`/`2072`/`2088`/`2188`/`2192`/`2348`/`2384`/`2388`/`2392`/`2396`/`2400`/`2404`/`3096`/`3344`/`3368`/`3404`/`3688`/`3696`/`3802`/`3806`/`3810`/`3865`/`0xEEC`(3820) |
| 58 | ★★★★★ **`MaximumWeaponFireType 6 → 10`** | `sub_426320` 测 `== 10` ⇒ 旧上界**拒绝了本 build 上存在的四种开火类型** |
| 59 | ★★★★★ **`NativeCharacterItemRecord` 12 字节** | `encodedLow@0` / `present@4` / `padding[3]@5` / `encodedHigh@8` |
| 60 | ★★★★★ **六条指令** | `0x619ED0` / `0x619EE6` / `0x619EF3` / `0x619EFA` / **`0x619F00 add ebx,0Ch`** / `0x619F08` |
| 61 | ★★★★★ **8 字节的 48 字节溢出** | 调用者 `0x618BAD` memset **`0x90` = 12 × 12**；8 字节 × 12 = 96 ⇒ **写超 48**；**两条路径都这样** |
| 62 | ★★★★★ **编解码** | decode = **`ROL32(key ^ low ^ high, 8)`**；encode = **`low=0` / `present=1` / `high=ROR32(id,8) ^ key`** |
| 63 | ★★★★★ **四个 `static_assert` 锚到引擎字节** | `encode(545, 0x7ECE6C71).high == **0x5FCE6C73**` / `encode(686, ...).high == **0xD0CE6C73**` |
| 64 | ★★★ 锚点来源 | `C:\Games\OLfinal\codol_1649370_full.bin` 的 **`manager+0xFB2`**；密钥 `manager+0x11138` = **`0x7ECE6C71`** |
| 65 | ★★★★★ **section 51j 的规则** | **"对称往返即使两侧都错也会通过"** ⇒ 所以不 assert encode-decode |
| 66 | ★★★★★ **`invokeSVTrace` 四错** | ① `ecx` 得忽略结构指针 ② `edx` 得 end ③ `a5` 得 bounds 指针 ④ **`a7`/`a8` 未 push** |
| 67 | ★★★★★ 实测后果 | **1349 次命中：零向上法线 / 全 fraction 0.0000 / hitId 恒 2046 / walkable 从不置位** |
| 68 | ★★★★★ 结论 | **`groundEntityNum` 每帧 `ENTITYNUM_NONE` ⇒ 玩家每次 pmove 上升一单位,永远** |
| 69 | ★★★ 正解 | `sub_46EA60` 是纯透传：`ecx=c` / `edx=d` / `push a,b,e,f,0,0` / `add esp,18h` |
| 70 | ★★★ 两个已知增长 | **`entityState 0x110 → 0x118`** / **`playerState 0x3564 → 0x3BBC`** |
| 71 | ★★★★★ **`FxGlass` 三条关系** | `pieceWordCount == ceil(pieceLimit/32)` **37/37** / **`pieceLimit == initialPieceCount + 1024` 27/27** / `geometryLimit == 8*pieceLimit` **37/37** |
| 72 | ★★★ 四个观测最大值 | `definitionCount 41` / `pieceLimit 1903`（**93%**）/ `initialPieceCount 879`（**86%**）/ `cellCount 203` |
| 73 | ★★★ `1024` 的双重身份 | = **`SvGlassPieceCount`** = **`sub_447500 @ 0x447527` 的 `BITS(11)` 终止符** |
| 74 | ★★★ 五个 `FxGlass` 尺寸 | `NativeFxGlassInitPieceState` **52** / `initialPieceStates@92` / `NativeFxGlassSystem` **112** / `glassSystem@4` / `NativeFxWorld` **116** |
| 75 | ★★★ `bind()` 十阶段 | 身份 → 3 前缀 → 6 前缀 → ~60 前缀 → 70 赋值 → 4 运行时槽 → 消息 → 玻璃桥 → 提交 |
| 76 | ★★★ `ServerDObjGetSuffix` 特殊 | 唯一用**后缀**（`+5`）的守卫：`8B C8 B8` |
| 77 | ★★★★★ **`CurrentCharacterGetPrefix` 含重定位操作数** | `A1 C0 67 E5 00 83 F8 FF 75 1F`；**"钉住操作数让它更严格,而不是更错"** |
| 78 | ★★★★★ **`CharacterRecordToSelectionNamesPrefix` 自守卫** | `6A 2C` = `push 0x2C` = **11 指针 × 4** |
| 79 | ★★★★★ **`valid()` 排除四指针** | `worldCharacterModelResolve_` / `characterSelectionResolve_` / `weaponSlotReadStaged_` / `currentCharacterGet_` |
| 80 | ★★★★★ 排除的理由 | **"保留它们会让 valid() 在第一帧返回 false,把整个引擎绑定一起带走"** |
| 81 | ★★★ 三个容量 | `NativeServerEntitySize = 0x2C8` / `Capacity = 2046` / `DObjCapacity = 2048` |
| 82 | ★★★ 最长/最短前缀 | **16 字节**（四个）/ **3 字节**（`ServerDObjGetSuffix`） |
| 83 | ★★★ `ByteDirections` 是数据 | 后 4 字节 `44 C4 59 3F` = **0.85000002f** |
| 84 | ★★★ `DObjTracelinePrefix` | **`push ebp; mov ebp,esp; and esp,-8; sub esp,364h`** ⇒ 9 字节,与 3.3.3.3 **逐字节相同** |
| 85 | ★★★★★ **玻璃桥的两个位移** | **`0x268302` 的 `-0x4C`（`0xB4`）** / **`0x2684CB` 的 `-0x48`（`0xB8`）**；原回调 **`0x450A40`** |
| 86 | ★★★ 回调体 | **`32 C0 C3`** = `xor al,al; ret` |
| 87 | ★★★★★ 单前缀失败的后果 | **`bind()` 到 `stage=glass_bridge` 就拒绝** |
| 88 | ★★★ `NativeTraceResult` 三副本 | `NativePmoveBindings.cpp` / `EngineBindings.cpp:2859` / `EngineBindings.cpp:3115` |
| 89 | ★★★ `TraceBounds = 0x18` | `midpoint[3]` + `halfSize[3]` |
| 90 | ★★★★★ **`NativeDObjTraceResult = 0x1C`** | `fraction@0`（**调用者播种**）/ `surfaceFlags@4` / `normal[3]@8`（**模型空间**）/ `modelIndex@0x14` / `partName@0x16` / `partGroup@0x18` |

---

## 十四、结论

### 1. ★★★★★ **故障见证器是"进程即将消失时唯一能写一行"的仪器**

★ **⇒ 六个码、上限 10、含 `stage` 面包屑、寄存器行、栈扫描（三判据、14 个、地址序）。**

### 2. ★★★★★ **`ServerDObjGetRva` 是**谓词**——一个真实的"签名移植选错函数"**

★ **⇒ 返回字面 `1`,所有调用者过了 null 检查,在第一次读"指针"时失败。**

### 3. ★★★★★ **`DObj` 步长 `0xD8`,四个独立佐证,且 `DObjScaleOffset = 200` 是**三分量向量****

### 4. ★★★★★ **十个动画回调的 `+0x18530` 重定位：旧值错两次**

★ **⇒ 不仅位置错,而且在**引擎每次动画树加载都清零的区域内**。**

### 5. ★★★★★ **`op=8 target=0` 是 DEP 违规**（执行地址 0）,来自 `0xAF324` 槽无空检查被调用

### 6. ★★★★★ **`DObjDirtyOffset 560 → 660` 的后果是"从不重建玩家 DObj"**

★ **⇒ 三个字段同意 `+100` 使它是重定位而非巧合。**

### 7. ★★★★★ **`ItemDefinitionSize 40 → 52`：所有测量都在角色 0 上,所以看不出来**

★ **⇒ 代价是**另一个角色的性别和颜色**,静默无错。**

### 8. ★★★★★ **`invokeSVTrace` 四个参数错误的后果是"玩家永远每次 pmove 上升一单位"**

★ **⇒ 1349 次命中：零向上法线、全 fraction 0.0000、hitId 恒 2046。**

### 9. ★★★★★ **`FxGlass` 的 `pieceLimit == initialPieceCount + 1024` 使上界成为**推导**而非猜测**

### 10. ★★★★★ **`CharacterItemRecord` 的 8→12 字节曾是**48 字节栈溢出**,只因路径不可达而潜伏**

### 11. ★★★★★ **四个 `static_assert` 锚到**引擎写的字节**（`0x5FCE6C73` / `0xD0CE6C73`）而非自证**

### 12. ★★★★★ **`valid()` 排除四个指针的理由是"保留它们会让整个引擎绑定在首帧失效"**

---

## 十五、下一步

`EngineBindings.cpp` 剩余 **7,601–17,867 行**（约 **10,300 行**）：
- 实体镜像事务（`synchronizeNativeServerEntities` 的剩余部分）
- 武器/附件解析（`resolveWeaponItem` / `readWeaponDefinition`）
- 角色呈现解析
- 声音别名注册表
- 十四个 `audit*` 诊断
- 约 100 个访问器实现

然后 `Appmain.cpp`（10,564 行）与 `server_mp` 154 文件。
