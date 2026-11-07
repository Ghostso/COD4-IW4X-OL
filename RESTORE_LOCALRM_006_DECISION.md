# RESTORE-LOCALRM-006 — Minimal ResourceManager Provider

## 判定

```text
RESTORE_LOCALRM_006_STATUS = COMPLETE

ORIGINAL_IIPS_INTEGRITY = BYTE_IDENTICAL
                          SHA256 E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
                          347704 bytes, mtime unchanged (2026-09-21 20:52:32)

ARTIFACT                = LocalRM_v3.dll
SHA256(LocalRM_v3.dll)  = 032FAC66A3F78027AA93A7EDB6B1506693C15EE9AAD1896F7BE9AE3D21A3EF26

LOADLIBRARY             = PASS
GETPROCADDRESS          = PASS (2/2)
OBJECT_CONSTRUCTION     = PASS (0x410 heap object, 4 vptrs, 48-slot vtable)
OBJECT_LIFECYCLE        = PASS (singleton identity, non-freeing dtor, release,
                                unload/reload)
RM_PROBE                = ALL_PASS

RM_OBJECT_SIZE          = CONFIRMED (0x410)
RM_VTABLE_COUNT         = CONFIRMED (48)
CALLING_CONVENTION      = CONFIRMED (__cdecl for both exports)
VTABLE_0                = CONFIRMED (deleting destructor)

LOCALRM_LOADABILITY     = CONFIRMED
LOCALRM_EXPORT_RUNTIME  = CONFIRMED
LOCALRM_ABI             = PARTIAL (mechanically CONFIRMED, semantically UNKNOWN)
LOCALRM_STANDALONE_LIFECYCLE = CONFIRMED (mechanical lifecycle only)

NEXT_TARGET             = RESTORE-ENGINE-BRIDGE-003 (gate satisfied)
```

`LocalRM_v3.dll` 现在是一个**真实的 ResourceManager provider**，
不再是返回常量的 stub：它会真的 new 一个 0x410 对象、装 4 个 vptr、
提供 48 槽 vtable，并且 `ReleaseResourceManagerII` 会真的走
`vtable[0](this, 1)` 的 deleting-destructor 路径。

---

## 0. 最重要的发现：现有 "ResourceManager ABI" 大部分是虚构的

本轮第一件事是把项目里流传的 ABI 断言逐条拿去和机器码对质。

**它们全部来自 `RESTORE_LOCALRM_001/LocalRM.cpp`** —— 一个**手写的 C++ 草稿**，
它自己写的 `RESTORE_LOCALRM_001_ABI.json` 对每个字段标的是 `CANDIDATE`，
而那一轮**从未编译过、从未运行过**（`RESTORE_LOCALRM_002` 记录：无编译器）。

所以之前流传的 `0x410 / 48 vtable / __stdcall / 嵌套对象在 +0x70 /
+0x3BC / vtable[2]=CheckState` 中，**只有一部分经得起检验**：

```text
被证伪 (REFUTED)
  __stdcall            → 机器码是朴素 ret (C3) → 实为 __cdecl
  单 vptr 对象          → 构造函数写 4 个 vptr (+0x00/+0x04/+0x20/+0x44)
被降级 (DEMOTED_TO_UNKNOWN)
  嵌套对象在 +0x70      → 构造函数根本没有 +0x70 的 vptr 写入
  +0x3BC process flag   → 全函数没有任何 +0x3BC 访问
  nested vtable1/2 计数 → 二进制里无对应证据
被确认 (CONFIRMED)
  对象大小 0x410         → `push 0x410`，直接可见
  vtable 48 槽           → 0x1003929C 起 48 个指向 .text 的非空指针
  vtable[0] = 析构       → `test byte [esp+4],1 ; ... ; ret 4`，标量删除析构惯用法
  GetRM 单例             → 守卫字节 0x1004EB6C + 实例槽 0x1004EB68
  Release NULL-safe      → `test ecx,ecx ; je`
```

**这就是为什么本轮禁止 Agent 自己"重新发明 ABI"** —— 草稿很容易变成"事实"。

---

## 1. Agent 01 / 02 — 两个 export 的真实 ABI

### GetResourceManagerII (RVA 0x1C80)

```asm
push -1 ; push 0x100325A9            ; SEH
mov  eax, fs:[0] ; push eax ; push ecx
mov  eax, [0x10042020] ; xor eax, esp ; push eax     ; /GS cookie
lea  eax, [esp+8] ; mov fs:[0], eax
test byte [0x1004EB6C], 1            ; guard
jne  already
or   dword [0x1004EB6C], 1
push 0x410                           ; <-- object size
call 0x2BE34                         ; operator new(0x410)
add  esp, 4
test eax, eax ; je epilogue
push eax ; call 0x11F20              ; ctor(this)
mov  [0x1004EB68], eax               ; singleton slot
epilogue: ... ; ret                  ; <-- plain ret => __cdecl
```

### ReleaseResourceManagerII (RVA 0x1C60)

```asm
mov  ecx, [esp+4]     ; arg1 = this   (cdecl)
test ecx, ecx
je   ret
mov  eax, [ecx]       ; vtable
mov  edx, [eax]       ; vtable[0]
push 1                ; scalar-delete flag
call edx              ; vtable[0](this, 1)
ret                   ; plain ret => __cdecl
```

```text
GET_RM_II_CALLING_CONVENTION     = __cdecl (CONFIRMED)
RELEASE_RM_II_CALLING_CONVENTION = __cdecl (CONFIRMED)
```

依赖库（全部原样保留，未删）：

```text
KERNEL32 72  USER32 14  ADVAPI32 3  SHELL32 2  ole32 4  OLEAUT32 3
MSVCP80 80   SHLWAPI 2  VERSION 3   WS2_32 15  MSVCR80 87  WSOCK32 2
                                          总计 287 imports
```

---

## 2. Agent 03 / 04 / 05 — 对象与 vtable 真相

构造函数 RVA 0x11F20 写入的对象字段（`this` 在 ebp）：

```text
[this+0x00] = 0x1003929C   vptr A
[this+0x04] = 0x1003926C   vptr B
[this+0x20] = 0x100344E4   vptr C
[this+0x44] = 0x10039290   vptr D
[this+0x40] = 0
[this+0x4C] = &[this+0x24]
[this+0x50] = 0
... 之后是大量 zero-init 字段，直到 ++ [this+0x3BC] 附近的区域
```

```text
OBJECT_HAS_MULTIPLE_VPTRS = CONFIRMED
RM_VTABLE_SIZE            = 0x410 (CONFIRMED)
```

**注意：释放路径用的是 `[this+0x00]` 那个 vtable**，它的 slot[0] 是析构。
把 004 的做法（一个 vptr、48 个槽）当成唯一真相是错的。

`vtable[0]` 指向 RVA 0x118E0：

```asm
test byte [esp+4], 1      ; scalar-delete flag
push esi
mov  esi, ecx             ; this
mov  [esi], 0x1003929C    ; re-set vtable
je   join
push esi
call 0x2BE28              ; operator delete(void*)
add  esp, 4
join:
mov  eax, esi
pop  esi
ret  4                    ; thiscall + stack arg
```

---

## 3. Agent 16 — 无编译器下的实现路线

环境复查（与 `RESTORE_LOCALRM_002` 一致，**没有改善**）：

```text
cl.exe clang.exe clang-cl.exe gcc.exe g++ link.exe lld-link.exe
ml.exe llvm-mc.exe zig.exe tcc.exe nasm.exe yasm.exe   = 全部 absent
Visual Studio / Windows Kits                            = 不存在
toolchain/llvm/*.tar.xz                                 = 已截断，无法解压
dotnet 8.0.420 SDK                                      = 有，但不是原生代码生成器
NativeAOT pack (ILCompiler)                             = ABSENT
```

```text
NATIVE_C_COMPILER_AVAILABLE = NO
```

因此 Agent 16 的路线是 **直接发射机器码**（`restore006/x86asm.py`），
而不是"无编译器 C"或任何变通。这对一个**完全确定**的对象是合理的：
字段布局已知、vtable 槽数已知、析构 ABI 已知。

我**没有**发明 ResourceManager 的内部行为。

---

## 4. Agent 17 / 18 — 构造真实对象

`LocalRM_v3.dll` 的 `.localrm`（VA 0x55000，RWX）：

```text
+0x000  GetResourceManagerII      __cdecl, 31 bytes
+0x040  ReleaseResourceManagerII  __cdecl, 20 bytes
+0x080  rm_deleting_destructor    thiscall+flag, 30 bytes
+0x0C0  shared vtable stub        mov eax,1 ; ret
+0x0E0  lazy_init                 guarded operator new(0x410) + 4 vptr stores
+0x180  DllMain                   mov eax,1 ; ret 0x0C
+0x200  guard dword   (starts 0)
+0x204  instance dword(starts 0)
+0x210  vtable, 48 slots, all non-NULL absolute VAs
+0x300  export name strings
+0x340  EAT / name table / ordinal table
+0x360  IMAGE_EXPORT_DIRECTORY
```

对象是真的：`operator new` 来自 MSVCR80 的 IAT（`0x1003328C`），
析构走同一张 IAT 的 `operator delete`（`0x10033284`）。

---

## 5. Agent 19 / 20 / 21 — 32 位宿主集成测试

真实 32 位宿主（`HOST_BITS = 32`）：

```text
LOADLIBRARY = PASS base=0x10000000

GetProcAddress(GetResourceManagerII)      PASS 0x10055000
GetProcAddress(ReleaseResourceManagerII)  PASS 0x10055040

GetResourceManagerII() != NULL            PASS 0x92A79D8   (real heap object)
object[+0x00] vptr installed              PASS 0x10055210
object[+0x04] vptr installed              PASS 0x10055214
object[+0x20] vptr installed              PASS 0x10055230
object[+0x44] vptr installed              PASS 0x10055254

48/48 vtable slots non-NULL               PASS
vtable[0] != vtable[1]                    PASS
Two successive Get -> SAME pointer        PASS  (singleton)
vtable[0](this,0) returns this, no free   PASS
singleton still valid after that          PASS
ReleaseResourceManagerII(this) completed  PASS
Reload after FreeLibrary                   PASS base=0x10000000

RM_PROBE = ALL_PASS
```

`PE validation`（复用 005 的校验器）：`VALID (0 hard failures, 1 warning)`
（warning 是原始 `.data` 本来就有的 bss 尾巴）。

---

## 6. 一个必须记录的语义发现：release 后单例悬空

原始 `ReleaseResourceManagerII` **不清除** 单例槽，也不复位 guard。
所以：

```text
Release(obj) 之后再调用 GetResourceManagerII() 会返回悬空指针
```

这在**原始 iips.dll 中就是这样**（RVA 0x1C60 全部指令已列出，没有清零）。

我**没有**"顺手修好"它 —— 那会引入与原版不同的生命周期语义。
测试也因此**只在 release 前**做重复 `Get`。

```text
DESTRUCTOR_OWNERSHIP = UNKNOWN
```

如果 Engine 真的走 `Release → 再 Get`，那是 003 必须观察的**第一个**行为点。

---

## 7. Agent 22 — 分级证据总表

```text
CONFIRMED (11)
  RM_OBJECT_SIZE=0x410, GET_RM_II=__cdecl, RELEASE_RM_II=__cdecl,
  GET_RM_II_SINGLETON, RM_VTABLE_COUNT=48, RM_VTABLE_0=deleting dtor,
  RELEASE_CALLS_VTABLE_0, OBJECT_HAS_MULTIPLE_VPTRS,
  VTABLE_SLOTS_NOT_NULL, RELEASE_IS_NULL_SAFE, OBJECT_HEAP_ALLOCATED

DEMOTED_TO_UNKNOWN (4)
  NESTED_OBJECT_INPLACE_AT_0x70, RM_OFFSET_3BC,
  NESTED_VTABLE1_COUNT, NESTED_VTABLE2_COUNT

UNKNOWN (6)
  VTABLE_1_IS_INITIALIZE, VTABLE_2_IS_CHECKSTATE, VTABLE_3_IS_PROCESS,
  DESTRUCTOR_OWNERSHIP, RESOURCE_MANAGER_SEMANTICS, THREAD_SAFETY

REFUTED (3)
  GET_RM_II_STDCALL, RELEASE_RM_II_STDCALL, SINGLE_VPTR_OBJECT
```

完整机器可读版本：`restore006/evidence/a22_abi_ledger.json`

**`__stdcall` 现在是 REFUTED，不是 CANDIDATE。** 之前是 CANDIDATE 只是因为
没人去读 `ret` 那个字节。

---

## 8. 证据修正（按你的要求并入总表）

```ini
HISTORICAL_LOAD_FAIL_193 = INVALID_INSTRUMENTATION
32BIT_HOST_LOAD          = CONFIRMED
64BIT_HOST_LOAD          = EXPECTED_FAIL_193
ORIGINAL_IIPS_DLL        = LOADABLE
LocalRM_v2.dll           = LOADABLE
LocalRM_v3.dll           = LOADABLE
```

---

## 9. 本轮我在自己的代码里犯的错（全部被测试抓到）

诚实记录，因为这些正是 003 会踩的坑：

```text
1. vtable / EAT 里写了 RVA 而应为绝对 VA      → Agent 15 + pefile 抓到
2. 过度修正：export 结构里把 RVA 写成了 VA     → pefile 拒绝解析，抓到
3. `pop ecx` 覆盖了 operator new 的返回值      → Agent 21 崩溃抓到
4. `call rel32` 位移基数算错 5 字节             → 静态反汇编抓到
5. guard 落在 0xCC 填充区，读成"已初始化"      → ProbeStep2 读到 0xCCCCCCCC 抓到
6. 析构里 `mov eax,esi` 放进了分支而非汇合点   → RmProbe 抓到
7. 多处 `mov eax, imm32` 用了 RVA 而非 VA      → ProbeVeh 报 EIP=0x10055005 抓到
```

每一次都是**运行时证据**纠正了静态自信。这也是为什么本轮的验收标准
是 `RM_PROBE = ALL_PASS` 而不是"看起来对"。

---

## 10. 边界遵守

未注入 CODOL、未修改原始 iips.dll（全程 `rb` 只读，哈希不变）、
未修改 EXE / Base.dll / BugTrace.dll、未运行或调试 CODOL、未触碰反调试、
未研究 Engine / Game Init / FF / Zone / Asset / localization / PRCL / `.tvm0`。

---

## 11. 复现

```powershell
python restore006/a01_disasm_exports.py        # Agent 01/02 真实 ABI
python restore006/a03_object_layout.py         # Agent 03/04/06 对象与 vtable
python restore006/a16_toolchain_recheck.py     # Agent 16 环境
python restore006/build_localrm_v3.py          # Agent 16/17 构建
python restore006/a15_verify_code.py           # Agent 15 机器码校验
python restore006/a22_abi_audit.py             # Agent 22 反驳式审计
python restore006/a22_abi_ledger.py            # Agent 22 分级证据表
python restore005/pe_validate.py .\LocalRM_v3.dll
.\restore006\probe32\out\RmProbe.exe .\LocalRM_v3.dll    # Agent 19/20/21
```

---

## 12. 进入 RESTORE-ENGINE-BRIDGE-003 的资格

```text
PE32                    = CONFIRMED   OK
LOADLIBRARY             = PASS        OK
GETPROCADDRESS          = PASS        OK
LOCALRM_LOADABILITY     = CONFIRMED   OK
RM_OBJECT_CONSTRUCTION  = CONFIRMED   OK
RM_MECHANICAL_ABI       = CONFIRMED   OK

-> 允许进入 RESTORE-ENGINE-BRIDGE-003
```

**但 003 的目标必须收窄。** 现在能安全说的是：

> LocalRM_v3.dll 提供一个**机械上合法**的 ResourceManager：
> 真实 0x410 堆对象、4 个 vptr、48 槽非空 vtable、
> 正确的 `__cdecl` 导出、正确的 deleting-destructor ABI。

**不能**说的是：

> 这个对象语义上满足 Engine 的 ResourceManager 契约。

`RESOURCE_MANAGER_SEMANTICS` 仍是 `UNKNOWN`。003 的第一步不是继续造，
而是**观察**：Engine 拿到这个对象后是否访问 vtable、访问哪些槽、
是否调用 release、以及 gate 之后卡在哪。

如果 Engine 访问了 vtable 的某个槽而我们填的是共享 stub，那个槽的编号
就是 003 的第一个硬事实 —— 它会把 `VTABLE_n_IS_*` 从 UNKNOWN 变成有证据的结论。
```
