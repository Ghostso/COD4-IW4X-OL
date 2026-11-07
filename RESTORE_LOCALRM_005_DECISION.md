# RESTORE-LOCALRM-005 — PE32 Loader Compatibility

## 判定

```text
RESTORE_LOCALRM_005_STATUS = COMPLETE

ORIGINAL_IIPS_INTEGRITY  = BYTE_IDENTICAL
                           SHA256 E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
                           347704 bytes, mtime unchanged (2026-09-21 20:52:32)
PE32                     = CONFIRMED
SECTION_LAYOUT           = CONFIRMED
IMPORT_DIRECTORY         = CONFIRMED (12 DLLs / 287 imports, original bytes reused)
EXPORT_DIRECTORY         = CONFIRMED (2 named exports, rebuilt minimal)
ENTRYPOINT               = CONFIRMED (DllMain / stdcall-compatible)
RELOCATION               = CONFIRMED (original .reloc preserved)
TLS                      = NOT_PRESENT (original had none either)

LOADLIBRARY              = PASS
GETPROCADDRESS           = PASS (2/2)

LOCALRM_LOADABILITY      = CONFIRMED
LOCALRM_EXPORT_RUNTIME   = CONFIRMED
LOCALRM_ABI              = UNKNOWN   (ResourceManager ABI still not established)
LOCALRM_STANDALONE_LIFECYCLE = PARTIAL_CONFIRMED

SHA256(LocalRM_v2.dll)   = 88a613961203d13657f4d28ee6e68df2c04a816ae86e16a11cf01611949590bf

NEXT_TARGET              = RESTORE-ENGINE-BRIDGE-003 (gate satisfied)
```

本轮唯一目标 `LoadLibrary = PASS` 已达成。产物为 **`LocalRM_v2.dll`**。

---

## 0. 方法学纠正：上一轮的 193 是仪器假象（伪阴性）

上一轮报告 `LoadLibrary = FAIL / ERROR_BAD_EXE_FORMAT (193)`，但当时的宿主是
**64 位 PowerShell + .NET**。把真正的 32 位 DLL 交给 64 位宿主，`LoadLibraryW`
永远返回 193 —— 这是仪器错误，不是工件缺陷。

本轮先建立**真正的 32 位宿主**（`restore005/probe32/Probe32.exe`，
`PlatformTarget=x86` + `RuntimeIdentifier=win-x86` + self-contained），
然后做对照实验：

```text
原始 iips.dll  在 32 位宿主下 → LOADLIBRARY = PASS
                在 64 位宿主下 → LOADLIBRARY = FAIL 193
```

**结论：RESTORE-004 的 `LoadLibrary = FAIL` 不可作为证据。**
所有历史 "LOAD_FAIL err=193"（含 `_ebo1_dllprobe`、`_ebo1_loadprobe32.ps1`）
都必须按伪阴性重新解释。

---

## 1. Agent 01 / 02 — PE 结构 Diff

原始与生成物的差异集中在 OptionalHeader 与 Section Table：

| 字段 | original | 生成物 (LocalRM.dll) |
|---|---|---|
| AddressOfEntryPoint | 0x2C288 | 0x1000 |
| SizeOfCode | 0x32000 | **0x6** |
| SizeOfInitializedData | 0x20000 | **0x47C** |
| SizeOfImage | 0x55000 | **0x481** |
| SizeOfHeaders | 0x1000 | **0xFFF** |
| BaseOfData | 0x33000 | **0x106F** |
| .text VirtualSize | 0x31C3B | **0x6** |
| .rdata VirtualAddress | 0x33000 | **0x1006** |
| .data VirtualAddress | 0x42000 | **0x106F** |
| EXPORT dir RVA | 0x41BD0 | 0x3302E |

`.rsrc` / `.reloc` 完全未变；IMPORT / BASERELOC / LOAD_CONFIG / IAT / SECURITY
的**目录表项**未变（指向原始 RVA），且这些区域的**原始字节在生成物中仍然是
byte-identical**（见 Agent 03/04 的 byte-identity check）。

### 根因（三个独立致命缺陷，已用 A/B 实验逐个复现）

```text
BAD_ALIGNMENT   .rdata VirtualAddress = 0x1006, .data = 0x106F
                不是 SectionAlignment(0x1000) 对齐

BAD_ALIGNMENT   OptionalHeader 之后又重复写出 16 个 Data Directory，
                使 Section Table 整体后移 0x80 字节 → 节表指向垃圾

BAD_IMAGE_SIZE  SizeOfImage = 0x481，而 SECURITY(certificate) 结束于 0x54E38。
                loader 把文件按 ROM image 映射，判定镜像被截断
```

`SizeOfHeaders = 0xFFF`（未按 FileAlignment 对齐）**本身不致命** ——
单独复现时仍然 PASS，故不列为根因。

---

## 2. Agent 03 — Import Directory Recovery

原始 imports **一个都没删**，全部按原 RVA 保留：

```text
KERNEL32.dll   72      USER32.dll  14     ADVAPI32.dll  3
SHELL32.dll     2      ole32.dll    4     OLEAUT32.dll  3
MSVCP80.dll    80      SHLWAPI.dll  2     VERSION.dll   3
WS2_32.dll     15      MSVCR80.dll 87     WSOCK32.dll   2
                      --------------------------------
                      总计 287 个 IAT 槽位 (1148 bytes)
```

IMPORT 描述符 / OFT / 名称串 / IAT 在 `LocalRM_v2.dll` 中与原始 **逐字节相同**。

重要（不要 "修" 的地方）：

```text
IMPORT dir  [0x3EE3C, 0x3EF40)
IAT         [0x33000, 0x334AC)
```

两者在**原始 iips.dll 中就是重叠的**（IAT 前 0x40 字节同时被当作第 13 个
IMPORT_DESCRIPTOR 读取，其所有权重字段为 0 → 合法终止符）。原始 DLL 可正常
加载，因此这不是缺陷，**不得改动**。

---

## 3. Agent 04 — Export Directory Reconstruction

原始 iips.dll 的导出（供参考）：

```text
iips.dll  Base=1  NumberOfFunctions=4  NumberOfNames=4
  GetResourceManager           RVA 0x1BC0
  GetResourceManagerII         RVA 0x1C80
  ReleaseResourceManager       RVA 0x1C60
  ReleaseResourceManagerII     RVA 0x1C60
```

把新的 EXPORT 目录**覆盖写在原始 .rdata 上**正是 004 出错的方式之一。
本轮改为放进全新的 `.localrm` 节：

```text
EXPORT dir RVA 0x55028  (40 bytes, 合法 IMAGE_EXPORT_DIRECTORY)
  Base                 = 1
  NumberOfFunctions    = 2
  NumberOfNames        = 2
  AddressOfFunctions   = 0x55094
  AddressOfNames       = 0x5509C
  AddressOfNameOrdinals= 0x550A4
  Name                 = 0x5505C ("LocalRM_v2.dll")

  GetResourceManagerII      ord 0  funcRVA 0x55010  bytes b8 00 54 05 00 c3
  ReleaseResourceManagerII  ord 1  funcRVA 0x55020  bytes b8 00 00 00 00 c3
```

两个函数 RVA 都落在**可执行节** `.localrm`（Characteristics 0x60000060）内。

---

## 4. Agent 05 — EntryPoint / DllMain

上一轮把 EntryPoint 指向自己的 stub（RVA 0x1000），但那个 stub 是

```asm
mov eax, 0x12345678
ret                ; <- 普通 ret，没有清理 stdcall 的 3 个参数
```

`DllMain` 是 `BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID)`，x86 下由
**callee** 清栈。用 `ret` 会在加载时破坏栈。

本轮 EntryPoint RVA 0x55000，内容为：

```asm
B8 01 00 00 00    mov eax, 1     ; TRUE
C2 0C 00          ret 0x0C       ; 弹出 3 个 stdcall 参数
```

```text
ENTRYPOINT_ABI = DllMain / stdcall-compatible
```

**这不是 ResourceManager export 的 ABI。** 两者必须分开理解。

---

## 5. Agent 06 — Loader-only Repair

采用 **"全新自洽 PE32 scaffold + 原样搬运 loader-critical 目录"** 策略，
而不是 "改原始节的内容"：

### 保留（逐字节搬运）

```text
原始 .text / .rdata / .data / .rsrc / .reloc 全部原样 (VA / RawPtr / RawSz 不变)
IMPORT directory, thunks, 名称串
IAT
BASERELOC (.reloc)
SECURITY (签名证书区)
LOAD_CONFIG
RESOURCE (.rsrc)
DEBUG
```

### 替换（只有这三样）

```text
EntryPoint                  -> .localrm 内的 DllMain stub
Export Directory            -> .localrm 内的新目录
两个 export stub            -> .localrm 内的两个函数
```

### 新增

```text
.localrm  VA 0x55000  RawPtr 0x55000  VS/RS 0x1000  Ch 0x60000060
```

之所以 RawPtr == VA，是因为原始 template 满足
`FileAlignment == SectionAlignment == 0x1000`（ROM-image 布局），
新节必须遵守同一约定。

---

## 6. Agent 07 — Windows Loadability Test

真实 32 位宿主（`HOST_BITS = 32`），调用真实 `LoadLibraryW` / `GetProcAddress`：

```text
--- LocalRM.dll (RESTORE-004 产物, 对照组) ---
LOADLIBRARY   = FAIL
GETLASTERROR  = 193
ERROR_MESSAGE = %1 不是有效的 Win32 应用程序。

--- LocalRM_v2.dll (本轮产物) ---
LOADLIBRARY   = PASS
MODULE_HANDLE = 0x10000000
GETLASTERROR  = 0
GETPROCADDRESS[GetResourceManagerII]      = PASS addr=0x10055010 (base+RVA 0x55010)
GETPROCADDRESS[ReleaseResourceManagerII]  = PASS addr=0x10055020 (base+RVA 0x55020)
GETPROCADDRESS = PASS (2/2)
```

### Level 4 附加（export 可安全执行）

```text
CALL[GetResourceManagerII]        = OK ret=0x55400
CALL[ReleaseResourceManagerII]    = OK ret=0x0
REPEAT_CALL[GetResourceManagerII]      = STABLE (0x55400 vs 0x55400)
REPEAT_CALL[ReleaseResourceManagerII]  = STABLE (0x0 vs 0x0)
RELOAD = PASS base=0x10000000
```

`CALL` 成功本身还额外证明了 EntryPoint 的 stdcall 清栈是正确的 ——
若 `DllMain` 用普通 `ret`，加载阶段栈就已失衡，不可能走到这一步。

---

## 7. Agent 08 — Independent PE Validation

```text
checks passed: 38/38
```

覆盖：MZ / PE / Machine=0x014C / Magic=0x10B / IMAGE_FILE_DLL /
SizeOfImage >= 所有节末端 / SizeOfHeaders 对齐 /
每节 VA 与 RawPtr 对齐且落在文件内 /
EntryPoint 落在可执行节 /
所有 Data Directory RVA < SizeOfImage /
SECURITY 证书落在 SizeOfImage 内 / file size <= SizeOfImage。

证据文件：

```text
restore005/evidence/a08_pe_validation.json
restore005/evidence/a08_pe_validation.txt
```

---

## 8. 失败分类（本轮结论）

上一轮若出现 193，正确分类不是 `UNKNOWN`，而是：

```text
BAD_ALIGNMENT    (主要)
BAD_IMAGE_SIZE   (主要)
```

`BAD_IMPORT` `BAD_EXPORT` `BAD_ENTRYPOINT` `BAD_RELOCATION` `BAD_TLS`
`BAD_LOAD_CONFIG` **均排除** —— 这些区域全部沿用原始字节，且已验证可加载。

---

## 9. 对原始模板的完整性

```text
original iips.dll 只被以 "rb" 打开读取，程序上从未打开写入。
SHA256 全程不变: E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
```

`_ebo1_mkproxy.py` 的产物位于 `工具/EB1_SANDBOX/IIPS/iips.dll`，未参与本轮工程。

---

## 10. 复现命令

```powershell
# 1) 结构 diff
python restore005/a01_pe_dump.py

# 2) imports / exports / 原始字节同一性
python restore005/a03_import_export_probe.py

# 3) 构建 LocalRM_v2.dll
python restore005/build_localrm_v2.py

# 4) 静态校验
python restore005/pe_validate.py .\LocalRM_v2.dll

# 5) 真实 32 位加载测试（Level 2/3/4）
.\restore005\probe32\out\Probe32.exe .\LocalRM_v2.dll GetResourceManagerII ReleaseResourceManagerII

# 6) 根因 A/B 因果证明
python restore005/run_proof.py

# 7) Agent 07+08 证据汇总
python restore005/run_a07_a08.py
```

---

## 11. 本轮未做的事（遵守边界）

未注入 CODOL、未修改原始 iips.dll、未修改 EXE / Base.dll / BugTrace.dll、
未运行或调试 CODOL、未触碰反调试、未研究 Engine / Game Init / FF / Zone /
Asset / localization / PRCL / `.tvm0`。

**未实现完整 ResourceManager ABI** —— 本轮 export 只是返回哨兵值的 stub。
`LOCALRM_ABI` 仍为 `UNKNOWN`。

---

## 12. 下一轮 Gate

```text
PE32                     = CONFIRMED   OK
LOADLIBRARY              = PASS        OK
GETPROCADDRESS           = PASS        OK
LOCALRM_LOADABILITY      = CONFIRMED   OK

-> 允许进入 RESTORE-ENGINE-BRIDGE-003
```
