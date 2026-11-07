# 03 二进制差分 / BINARY DIFF

对象：NEW（2697）vs OLD（28366ae9）vs 1113（a96c5dfb）。**纯静态**，未运行、未修改样本。
派生数据：`_data\pe_meta.json`、`_data\strings_*.txt`、`_data\strings_diff.txt`、`_data\syms_*.json`、`_data\disasm_key2697.txt`。

> 证据等级：**VERIFIED** / **STATIC-INFERENCE** / **NOT-OBSERVED** / **BLOCKED**。

---

## 1. PE 头与节区（VERIFIED）

| 维度 | NEW | OLD | 1113 |
|---|---|---|---|
| Machine | I386 (0x14c) | I386 | I386 |
| Subsystem | WINDOWS_GUI (2) | WINDOWS_GUI (2) | WINDOWS_GUI (2) |
| ImageBase | 0x400000 | 0x400000 | 0x400000 |
| EntryPoint | 0x14e0 | 0x1480 | 0x14e0 |
| SizeOfImage | 0x15cf0000 | 0x13f6d000 | 0x13f6c000 |
| Characteristics | 0x326 | 0x126 | 0x326 |
| DllCharacteristics | 0x140（NX_COMPAT + DYNAMIC_BASE） | 0x100（仅 NX_COMPAT） | 0x140 |
| Linker | 2.47 | 2.30 | 2.47 |
| 节区数 | 11 | 20 | 11 |
| Imphash | `5298c76ec6910429495ead35879da26c` | `506faee6444b112462fb1301d26bca17` | `d5a1b1cde88e92542961a54faaf79f5d` |

**STATIC-INFERENCE：** NEW 与 1113 的 `Characteristics`/`DllCharacteristics`/EntryPoint/节区数完全一致（0x326 / 0x140 / 0x14e0 / 11 节），说明二者出自 **同一代工具链与构建配置**；OLD 明显属于上一代构建（0x126 / 0x100 / 20 节 / ld 2.30 / 未开 DYNAMIC_BASE）。

节区明细（VERIFIED）：

| NEW 节区 | VA | VSize | OLD 对应 | 1113 对应 |
|---|---|---|---|---|
| `.text` | 0x1000 | 0x382878 | 0x3a7a68 | 0x3d4ee8 |
| `.rodata` | 0x384000 | 0x1bc | 0x1bc | 0x1bc |
| `.data` | 0x385000 | 0xe340 | 0xfb34 | 0xfe3c |
| `.rdata` | 0x394000 | 0xcac38 | 0xc4360 | 0xc782c |
| `.eh_fram` | 0x45f000 | 0x6a040 | （无，被编号节替代） | 0x8b0c4 |
| `.bss` | 0x4ca000 | **0x157f26c8** | **0x139f9600** | 0x139f98fc |
| `.edata` | — | 0x1800 | 0x1800 | 0x1800 |
| `.idata` | — | 0x1f4c | 0x1fec | 0x2098 |
| `.tls` | — | 0x10 | 0x8 | 0x10 |
| `.rsrc` | — | 0x8bf0 | 0x88d0 | 0x8bf0 |
| `.reloc` | — | 0x24194 | 0x26ff8 | 0x27db4 |

- OLD 独有：`.CRT` 节与 9 个编号节 `/4 /14 /29 /41 /55 /67 /80 /91 /102`（旧 GNU ld 的节放置方式）。
- **VERIFIED：** NEW 的 `.bss` 虚拟大小（0x157f26c8 ≈ 344 MiB）显著大于 OLD/1113（≈313 MiB），与 2697 层新增的静态/全局缓冲一致（数量级推断，非逐符号核对）。

---

## 2. 导入表差分（VERIFIED）

导入 DLL（9 个，三者一致）：`ADVAPI32.dll, CRYPT32.dll, GDI32.dll, KERNEL32.dll, SHELL32.dll, USER32.dll, WINMM.DLL, WS2_32.dll, msvcrt.dll`。

每 DLL 导入函数数：

| DLL | NEW | OLD | 1113 |
|---|---|---|---|
| ADVAPI32 | 4 | 4 | 4 |
| CRYPT32 | 4 | 4 | 4 |
| GDI32 | 5 | 5 | 5 |
| KERNEL32 | 88 | 87 | 89 |
| SHELL32 | 1 | 1 | 1 |
| USER32 | 28 | 28 | 28 |
| WINMM | 1 | 1 | 1 |
| WS2_32 | **28** | 25 | 25 |
| msvcrt | **132** | 142 | 148 |
| **合计** | **291** | **297** | **305** |

### 2.1 NEW 相对 OLD 新增导入（37 项，VERIFIED）

- **kernel32**：`CreateEventW, GetCPInfo, GetFileInformationByHandle, GetFileType, IsDBCSLeadByte, IsProcessorFeaturePresent, LoadLibraryW, LocalFree, OpenProcess`
- **msvcrt**：`_XcptFilter, __fpecode, __lc_codepage, __p___initenv, __p___mb_cur_max, __p__commode, __p__iob, __pxcptinfoptrs, _assert, _close, _fstati64, _get_osfhandle, _isctype, _lock, _open_osfhandle, _stati64, _unlock, atexit, fgetc, isdigit, isxdigit, ldexp, log, strcspn`
- **ws2_32**：`WSASetLastError, getpeername, htonl, inet_pton`

### 2.2 OLD 相对 NEW 独有导入（41 项，VERIFIED，节选）

- kernel32：`AddVectoredExceptionHandler, CreateProcessA, GetHandleInformation, GetModuleHandleW, IsDebuggerPresent, RemoveVectoredExceptionHandler, UnhandledExceptionFilter`
- msvcrt：`printf, setlocale, wcs*, isprint, _onexit, fgetpos/fsetpos …`
- ws2_32：`WSAStringToAddressA`

**STATIC-INFERENCE：**
- NEW 新增的 `GetFileType/GetFileInformationByHandle/_open_osfhandle/_get_osfhandle/_stati64/_fstati64` 指向 **新增的文件/句柄探测逻辑**，与 2697 的 archive probe / registration 读取路径相符（见 04）。
- NEW 新增 `inet_pton/getpeername/htonl/WSASetLastError` 指向 **新增的地址解析与 TCP/UDP 端点处理**（与 `codol_loopback_win32.c` 的 `_guard_*` 逻辑一致）。
- 换成较新 MSYS2 工具链后 CRT 层导入集合整体变化（`printf/setlocale/wcs*` 换成 `_lock/_unlock/isdigit/isxdigit/fgetc`），**不能**用导入差异单独判定功能变化。

### 2.3 NEW 相对 1113 独有导入（仅 9 项，VERIFIED）

`_lock, _unlock, fgetc, isxdigit, strcspn`（msvcrt）+ `WSASetLastError, getpeername, htonl, inet_pton`（ws2_32）。

**STATIC-INFERENCE：** NEW 与 1113 导入集几乎一致（仅 9 项差异），说明 **2697 的"新增"主要不是靠新的 OS API**，而是一个 **独立的 `.text` 内部协议/适配实现层**（如下 2697 符号）。

---

## 3. 导出表（VERIFIED）

| | NEW | OLD | 1113 |
|---|---|---|---|
| `Plugin_*` 导出 | 185 | 185 | 185 |
| 集合是否完全相同 | — | NEW==OLD: **True** | NEW==1113: **True** |

**VERIFIED：** 三样本导出表 **完全相同**（185 个 `Plugin_*`，集合逐项相等）。即 2697 层的功能 **不是通过新增导出暴露**，而是内部实现 + 已有导出内部行为改变（或由新的内部流程驱动）。

---

## 4. 资源与调试目录（VERIFIED）

| 项 | NEW | OLD | 1113 |
|---|---|---|---|
| VERSIONINFO（FileVersion/ProductVersion/OriginalFilename） | 无 | 无 | 无 |
| CodeView / PDB 调试目录 | 无（`debug=[]`） | 无 | 无 |
| `.rsrc` 体积 | 0x8bf0 | 0x88d0 | 0x8bf0 |

**STATIC-INFERENCE：** 三样本均 **无版本资源、无 PDB**，因此**无法**从版本资源判定版本号，也无法直接恢复源码级符号（→ 2697 层符号仅靠 COFF 次要符号表，见第 6 节）。

---

## 5. 字符串差分（VERIFIED）

字符串提取统计：

| | NEW | OLD | 1113 |
|---|---|---|---|
| 字符串条数 | 62,147 | 72,859 | 71,857 |

差分（`_data\strings_diff.txt`）：

| 比较 | NEW-only | OLD-only |
|---|---|---|
| NEW vs OLD | 9,564 | 20,276 |
| NEW vs 1113 | 8,511 | — |

（NEW-only 数量大，其中相当比例来自工具链/CRT 字符串差异；真正有价值的增量见第 6、7 节的 `2697` 命名簇。）

### 5.1 NEW 中源码文件名串（VERIFIED，`strings_NEW_80816711.txt`）

以下**源码文件名**以字符串形式存在于 NEW，且 **在 OLD / 1113 中均不存在**：

```
codol_2697_snapshot.c        codol_2697_gamestate.c
codol_2697_configstrings.c   codol_2697_registration.c
codol_2697_entities.c        codol_2697_clients.c
codol_2697_delta.c           codol_2697_fields.c
codol_2697_actors.c          codol_2697_anim.c
codol_2697_arrays.c          codol_2697_publication.c
codol_2697_profile.c         codol_2697_resources.c
codol_2697_history.c         codol_2697_adapter.c
codol_weapon_2697_core.c     codol_weapon_2697_keys.c
codol_weapon_2697_loader.c   codol_weapon_2697_registry.c
codol_weapon_2697_runtime.c  codol_weapon_2697.c
codol_loopback_win32.c       codol_netconst_index.c
codol_archive_probe.c
```

**VERIFIED：** 这些文件名证实 NEW 中新增了一整套 `codol_2697_*` / `codol_weapon_2697_*` / loopback / netconst / archive-probe 编译单元（**26 个不同源文件名**）。作为对照，这些源文件名 **未** 出现在 COFF 符号表中（源码文件符号数 = 0），因此它们来自 **字符串常量/`__FILE__` 类引用**，仍属直接证据。

### 5.2 mbedTLS 并非新增（VERIFIED，重要排除项）

| | NEW | OLD | 1113 |
|---|---|---|---|
| `mbedtls` 相关字符串数 | 922 | 934 | 934 |

**VERIFIED：** 三样本都内含 mbedTLS，**mbedTLS 不是 2697 的新增特征**，不应用作"更新"的判据。

---

## 6. 符号差分（COFF 次要符号表，VERIFIED）

| | NEW | OLD | 1113 |
|---|---|---|---|
| 原始符号条目 | 45,792 | 55,074 | 56,052 |
| 去重函数/符号名 | 36,980 | 46,160 | 46,707 |

> 注：这些是链接期保留的次要符号（非 PDB 全符号）。数量少于 OLD 与"NEW 体积更小"一致，但 **不能**据此认为功能更少——NEW 去重后仍新增了 99 个 `2697` 符号。

### 6.1 `2697` 命名符号簇（VERIFIED，关键发现）

- NEW 中匹配 `2697` 的符号：**99 个**。
- 这 99 个 **在 OLD 与 1113 中全部不存在**（absent from both = 99）。
- 换言之：**2697 符号是 NEW 独有的、完整的实现层**，不是命名替换。

关键 RVA（VA = RVA + 0x400000）：

| 符号 | RVA | 说明（STATIC-INFERENCE） |
|---|---|---|
| `_CODOL2697_WriteGamestate` | 0xa21b8 | 2697 gamestate 序列化 |
| `_CODOL2697_WriteSnapshot` | 0xa4fa0 | 2697 snapshot 序列化（薄封装） |
| `_CODOL2697_WriteSnapshotReached` | 0xa4860 | 2697 snapshot 实际写实体 |
| `_CODOL2697_WriteConfigstrings` | 0xa0468 | 2697 configstring 写 |
| `_CODOL2697_WriteDeltaValue` | 0xa0a9c | 2697 delta 值写 |
| `_CODOL2697_WriteNativeGamestate` | 0xa3dab | 原生 gamestate 出口（含注册门，见首条下节） |
| `_CODOL2697_ReadRegistration` | 0xa3ea0 | 读取客户端注册导出文件 |
| `_CODOL2697_PublicationAudit_f` | 0xa3996 | 发布审计 |
| `_CODOL2697_PrepareHistory` / `_FinishHistory` | 0xa249d / 0xa27c7 | 历史/回放准备与收尾 |
| `_CODOL2697_TranslateCommand` / `_LinkTagCommand` | 0xa35b0 / 0xa3821 | 命令转换 / tag 关联 |
| `_SV_BuildClientSnapshot` | 0x89081 | 构建客户端 snapshot（NEW-only） |
| `_SV_WriteReliableCommand` | 0x8612e | 写可靠命令（NEW-only） |
| `_SV_ProfileCommand2697` | 0x860de | 命令画像（NEW-only） |
| `_CODOL2697_ProfileCommandBytes` | 0x85d32 | 命令字节画像 |
| `_CODOL_BuildWeapon2697Core` | 0xf38d7 | 2697 武器核心构建 |
| `_CODOL_BuildWeapon2697Registry` | 0xf48eb | 2697 武器注册表 |
| `_CODOL2697_ParseWeaponRecipe` | 0xf4e6f | 2697 武器配方解析 |
| `_CODOL_LoadEngineWeapon2697` | 0x164307 | 引擎武器加载 2697 |
| `_CODOL_SendScoreboard2697` | 0x17c77b | 计分板发送 2697 |
| `_CODOL_AcceptClientStats2697` | 0x17e200 | 客户端统计接收 2697 |

（其余 2697 符号含 `_CODOL2697_Adapt*/_Reach*/_WriteActors/_WriteAnimations/_WriteClients/_WriteEntities/_WriteEntityPayload/_WritePlayerArrays/_WritePlayerFields/_WriteClientPayload/_CODOL2697_*Resources` 及 weapon 全套，完整清单见 `_data\syms_NEW.json`。）

### 6.2 旧版同名封装函数三样本均存在（VERIFIED，RVA 不同）

| 符号 | NEW | OLD | 1113 |
|---|---|---|---|
| `_CODOL_WriteSnapshot` | 0xbee15 | 0xb271c | 0xb21e4 |
| `_CODOL_WriteGamestate` | 0xa865a | 0xa8de5 | 0x9cb65 |
| `_CODOL_WriteConfigstrings` | 0xa857f | 0xa8d1f | 0x9ca9f |
| `_CODOL_WriteSnapshotDeltaNumber` | 0xbe946 | 0xb2322 | 0xb1dea |
| `_CODOL_HandshakeInit` | 0x982a3 | 0x97230 | 0x96034 |
| `_CODOL_HandshakeCookie` | 0x9857b | 0x97597 | 0x9639b |
| `_CODOL_HandshakeClear` | 0x9828d | 0x97217 | 0x9601b |
| `_SV_DirectConnect` | 0x6f2c0 | 0x834d6 | 0x6ed8a |
| `_SV_ConnectionlessPacket` | 0x8487f | 0x15cd3 | 0x83ceb |
| `_SV_SendMessageToClient` | 0x86b06 | 0x1a8c0 | 0x858c0 |
| `_CODOL_Client2697History` | 0xc1abc | — | — |

**VERIFIED：** 旧协议封装（`_CODOL_WriteGamestate` 等）在三样本中都存在；NEW 在其中 **另起** 一套 `_CODOL2697_*` 通道（见 04 的调用链）。

### 6.3 loopback 守卫（NEW-only，VERIFIED）

NEW 独有（OLD/1113 无）一整套 `_guard_*` 包装，用于拦截/审计网络调用，来源文件 `codol_loopback_win32.c`（见 5.1）。

下表同时给出两个不同的地址（**务必区分**）：
- **符号 RVA**：COFF 次要符号表中 `_guard_*` 的函数起始 RVA；
- **调用点 VA**：启动器审计 `evidence\loopback-executable-audit.json` 中记录的、被该守卫接管的导入调用点（位于对应守卫函数体内）。

| 守卫符号 | 符号 RVA | 符号 VA | 审计记录的导入调用点 VA |
|---|---|---|---|
| `_guard_socket@12` | 0x98920 | 0x498920 | 0x498968 |
| `_guard_bind@12` | 0x98e4f | 0x498e4f | 0x498ed1 |
| `_guard_connect@12` | 0x98f03 | 0x498f03 | 0x498f2c |
| `_guard_send@16` | 0x98dfe | 0x498dfe | 0x498e2b |
| `_guard_sendto@24` | 0x98d8a | 0x498d8a | 0x498df1 |
| `_guard_recv@16` | 0x98d39 | 0x498d39 | 0x498d66 |
| `_guard_recvfrom@24` | 0x98c4e | 0x498c4e | 0x498cae |
| `_guard_accept@12` | 0x98b93 | 0x498b93 | 0x498bd8 |
| `_guard_getaddrinfo@16` | 0x98a73 | 0x498a73 | 0x498b5f |
| `_guard_getnameinfo@28` | 0x989cd | 0x4989cd | 0x498a1f |
| `_guard_setsockopt@20` | 0x98f50 | 0x498f50 | 0x498fa3 |

**VERIFIED：** 以 `_guard_socket@12` 为例，符号起始 RVA 0x98920（VA 0x498920）处为 `push ebp` 函数序言；审计记录的 0x498968 处为函数体内的 `call dword ptr [...]` 导入跳转，二者均落在同一 `.text` 函数内，自洽。

**STATIC-INFERENCE：** 该层用于把网络收束到 loopback（127.0.0.1）并做调用审计，对应审计工件 `unguarded_import_thunk_calls: 0`、`unexpected_network_imports: 0`（该审计为历史产物，**不是本阶段的运行结果**）。

## 7. 代码/工具链差分结论

| 结论 | 等级 |
|---|---|
| NEW 是独立构建，非 OLD 重打包（大小/节区/导入/符号/字符串全不同） | VERIFIED |
| NEW 与 1113 共享 GCC 16.2.0 / ld 2.47 / 11 节区构建配置 | VERIFIED |
| NEW 含 99 个 `2697` 独有符号（OLD/1113 均无） | VERIFIED |
| NEW 含 26 个 `codol_2697_*`/`codol_weapon_2697_*`/loopback/netconst/archive-probe 源文件名串 | VERIFIED |
| mbedTLS 三样本均有，非 2697 新增 | VERIFIED |
| 185 个 `Plugin_*` 导出三样本完全相同，2697 未新增导出 | VERIFIED |
| 2697 层源码本地不可得，只能反汇编 | BLOCKED |
| 2697 层是否被客户端实际使用 | NOT-OBSERVED |

未决问题：
- 99 个 2697 符号在 `.text` 中的实际调用频度/覆盖范围（本阶段只对关键函数做了调用链，未做全量反向可达性分析）。
- `_SV_BuildClientSnapshot`（0x89081）与旧 snapshot 写路径的关系（是否并存/替代）→ 需进一步反汇编（见 06）。
