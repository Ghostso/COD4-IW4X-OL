# ICH-003 — IW4 / IW4X / CODOL Runtime 交叉差分

## 基线引用

IW4X 侧结论直接引用 ICH-002-A 和 ICH-002-B（已 CLOSED，不重新验证）：
- Original IW4 CRT = YES
- Original IW4 filesystem = YES
- Original IW4 IWD = YES
- Original IW4 Zone loader = YES
- Original IW4 Asset DB = YES
- Startup environment = MODIFIED
- Bootstrap = ADDED
- Memory = 原始 runtime + startup patches
- Runtime model = Original IW4 + compatibility/extensions

CODOL 侧结论引用已有静态证据报告。

---

## 一、六层比较

### Layer 1 — Entry / Bootstrap

| IW4 baseline | IW4X modification | CODOL modification |
|---|---|---|
| PE entry → CRT __tmainCRTStartup → engine main | DllMain hook 0x6BAC0F → Main::EntryPoint → security_cookie + init → call Game::__tmainCRTStartup(0x06BAA2F) | EXE Entry 0xE5DC690 → call [IAT 0x0E9DC665] → Base.dll ordinal 1 → VM .tvm0 boundary (ordinal1 has no ret, never returns to EXE) |

Relation: SAME_LAYER_DIFFERENT_IMPLEMENTATION
Evidence:
- IW4X: src/DllMain.cpp:51 (hook install), :25 (CRT call); Functions.cpp:7 (0x06BAA2F)
- CODOL: CODOL_ORDINAL1_LIFECYCLE_FINAL.md (ordinal-1 = VM stub, no ret, jmp to .tvm0); EX-011 (entry executed, no alternative entry)
Confidence: HIGH

分析:
两者都在"引擎代码执行前"有一个 bootstrap 层。
IW4X 通过 DLL 注入 + hook 原始 entry 实现，然后 delegate 回原始 CRT。
CODOL 通过 EXE → Base.dll ordinal 1 → VM 实现但永不返回。
结构层相同（Entry/Bootstrap），但实现模型不同（hook-and-return vs VM-never-return）。

---

### Layer 2 — CRT / Startup Environment

| IW4 baseline | IW4X modification | CODOL modification |
|---|---|---|
| 标准 CRT init（locale, heap, security cookie） | __security_init_cookie(0x06CA062) + SetProcessDEPPolicy(PROCESS_DEP_ENABLE) + SetEnvironment(CWD + DLL search path) + srand，全部在原始 CRT 之前 | Base DLL 内部 CRT/locale init（Base+0x288A05 setlocale 解析器, Base+0x292800 config string 解析器）；当前在 Base+0x306A 因 this=3 崩溃 |

Relation: SAME_LAYER_DIFFERENT_IMPLEMENTATION
Evidence:
- IW4X: src/DllMain.cpp:5-10 (srand, SetEnvironment, Steam, Crypto, Loader), :18 (security cookie), :34 (DEP); src/Utils/Utils.cpp:166-180
- CODOL: CODOL_BOOTSTRAP_REPORT (Base CRT/locale init confirmed; crash at Base+0x306A); EX-051 (IIPS environment contract)
Confidence: HIGH

分析:
两者都有"CRT/环境初始化"层。
IW4X 添加了进程级环境修改（DEP, CWD, DLL path），作为兼容层。
CODOL 的 CRT init 是 Base.dll 内置的，不需要外部注入，但当前因 locale 对象指针损坏而崩溃。
解决的问题域相同（启动前环境准备），实现不同（进程级 hook vs DLL 内部初始化）。

---

### Layer 3 — Filesystem / Search Path

| IW4 baseline | IW4X modification | CODOL modification |
|---|---|---|
| 标准 IW4 FS searchpath | RegisterFolder("userraw"), Sys_DefaultInstallPath→CWD, fs_homepath→BASE_INSTALL, basePath check removed, file count expanded, FS sync wrappers | UNKNOWN — EX-015 确认在 Base+0x306A 崩溃前无任何游戏文件访问；main\%s 字符串引用存在但无 clean function |

Relation: UNKNOWN
Evidence:
- IW4X: src/Components/Modules/FileSystem.cpp:247-266, 337-341, 354-374, 493-517
- CODOL: CODOL_EX015_FS_RESULT.md (no game file API before crash); EX-020 (main\%s ref at 0x239B7D, no clean function)
Confidence: HIGH (for UNKNOWN determination)

分析:
CODOL 的 filesystem 层在当前 bootstrap 崩溃点之前未到达，无法建立有效比较。

---

### Layer 4 — IWD / Zone / Asset DB

| IW4 baseline | IW4X modification | CODOL modification |
|---|---|---|
| 原始 IW4 Zone loader + Asset DB | IW4x zone header ('IW4x'), CODO version compat (316-360/423-461), custom XOR/rotate decrypt, RSA+AES-CTR, DB_FindXAssetHeader hook, asset pool expansion, ZoneConvert x64→x86 | UNKNOWN — asset layout (.ff/.iwd/settings_*.iw4) 已确认存在但无代码入口到达 |

Relation: UNKNOWN
Evidence:
- IW4X: src/Components/Modules/FastFiles.cpp:329-369, 468-484; AssetHandler.cpp:160-223, 503-548
- CODOL: EX-014 (asset layout confirmed, code entry UNKNOWN); EX-015 (no game file access before crash)
Confidence: HIGH (for UNKNOWN determination)

分析:
CODOL 的 asset 层在当前 bootstrap 崩溃点之前未到达，无法建立有效比较。

---

### Layer 5 — Dvar / Command

| IW4 baseline | IW4X modification | CODOL modification |
|---|---|---|
| 原始 IW4 command line parsing, dvar system | Flags::ParseFlags() 原地去除 GetCommandLineA/W 缓冲区中所有引号; Flags::HasFlag() lazy init 由 Component 构造触发; QuickPatch dvar 注册 | argv provider 0xCA827C → UTF-16 command line → argv builder → argv array (0x0196928C count / 0x01969290 ptr) → gate predicate 0x37F580 检查 -q/-qa → 0x0849413B gate byte |

Relation: SAME_LAYER_DIFFERENT_IMPLEMENTATION
Evidence:
- IW4X: src/Components/Modules/Flags.cpp:22-103 (quote stripping + parse + lazy init)
- CODOL: EX-032 (argv provider partial, command line source confirmed); EX-034 (argv shape confirmed, gate predicate confirmed); STANDALONE-CORE-007 (0x0849413B write confirmed)
Confidence: HIGH

分析:
两者都在启动阶段解析 command line。
IW4X 修改原始缓冲区以修复引号解析问题（兼容性扩展）。
CODOL 使用 argv 结果做 launcher context gate（平台门控）。
层级相同（command line parsing），问题不同（兼容修复 vs 平台检查）。

---

### Layer 6 — Game Initialization

| IW4 baseline | IW4X modification | CODOL modification |
|---|---|---|
| 原始 Com_Init → FS_Init → DB_Init → CL_Init | Components::Loader::Initialize() → Register 60+ Components → 每个 Component 构造函数安装 patch; 全部在原始 CRT 之前 | 0x77F580→0x4FD9B0→0x4FCEE0→0x808650→0x7E98F0→0x6212C0 链 (STRONG for network/STUN); Game Init / FS / Renderer / Main Loop NOT REACHED |

Relation: UNKNOWN
Evidence:
- IW4X: src/Components/Loader.cpp:90-197; src/DllMain.cpp:10
- CODOL: CODOL_STANDALONE_CORE_001 (bootstrap/network chain STRONG; Game Init NOT REACHED); EX-020 (no clean Engine entry)
Confidence: HIGH (for UNKNOWN determination)

分析:
CODOL 的 Game Init 层在当前 bootstrap 崩溃点之前未到达。
0x77F580 链是 bootstrap dispatcher 候选，但不能证明完整 Game Init 到 Main Loop。

---

## 二、交集汇总

INTERSECTION_COUNT = 3

---

INTERSECTION_01 = Entry / Bootstrap 层结构交集

IW4X_SIDE =
  DllMain (DLL_PROCESS_ATTACH)
  → Utils::Hook(0x6BAC0F, Main::EntryPoint, HOOK_JUMP)
  → Main::EntryPoint
  → __security_init_cookie + SetEnvironment + Components::Loader
  → return Game::__tmainCRTStartup(0x06BAA2F)

CODOL_SIDE =
  EXE Entry 0xE5DC690
  → call dword ptr [0x0E9DC665]
  → Base.dll ordinal 1 (Base+0x1D6582C)
  → push 0x592A35B8; push ecx/edx/ebx/eax
  → jmp Base+0x1F27FDC (.tvm0 VM boundary)
  → never returns to EXE (no ret in stub)

COMMON_LAYER = Entry / Bootstrap
RELATION = SAME_LAYER_DIFFERENT_IMPLEMENTATION
EVIDENCE =
  IW4X: src/DllMain.cpp:51 (hook), :25 (CRT call); Functions.cpp:7 (0x06BAA2F)
  CODOL: CODOL_ORDINAL1_LIFECYCLE_FINAL.md (ordinal1 stub = VM entry, no ret); EX-011 (executed entry, no alternative)
CONFIDENCE = HIGH

---

INTERSECTION_02 = CRT / Startup Environment 层结构交集

IW4X_SIDE =
  Game::__security_init_cookie() [src/DllMain.cpp:18, Functions.cpp:6=0x06CA062]
  Utils::SetEnvironment() → IW4x_INSTALL or exe_dir → SetCurrentDirectory + SetDllDirectory [src/Utils/Utils.cpp:166-180]
  SetProcessDEPPolicy(PROCESS_DEP_ENABLE) [src/DllMain.cpp:34]
  std::srand(...) [src/DllMain.cpp:5]

CODOL_SIDE =
  Base DLL CRT/locale init:
  Base+0x292800 (config string parser)
  Base+0x288A05 (CRT setlocale category parser)
  Base+0x2F0D (small-string/locale object init)
  Base+0x306A (locale object access — current crash point, this=3)

COMMON_LAYER = CRT / Startup Environment
RELATION = SAME_LAYER_DIFFERENT_IMPLEMENTATION
EVIDENCE =
  IW4X: src/DllMain.cpp:5-18,34; src/Utils/Utils.cpp:166-180
  CODOL: CODOL_BOOTSTRAP_REPORT (Base CRT/locale init confirmed; crash at Base+0x306A with this=3); EX-051 (environment contract)
CONFIDENCE = HIGH

---

INTERSECTION_03 = Command Line Parsing 层结构交集

IW4X_SIDE =
  Flags::ParseFlags() [src/Components/Modules/Flags.cpp:22-103]
  → GetCommandLineA() 返回 char* → in-place strip all '"'
  → GetCommandLineW() 返回 wchar_t* → in-place strip all L'"'
  → CommandLineToArgvW(GetCommandLineW()) → parse '-' prefixed flags
  → lazy init triggered by Flags::HasFlag() during Component construction

CODOL_SIDE =
  argv provider slot 0xCA827C (packed/decoded provider, exact API unproven)
  → UTF-16 command line string
  → argv builder (runtime decoded, writes [0x0196928C]=count, [0x01969290]=argv_ptr)
  → gate predicate EXE+0x37F580
  → scans argv for "-q" / "-qa"
  → if absent: WIN_NO_TCLS error
  → if present: writes byte 1 to 0x0849413B (gate flag)

COMMON_LAYER = Dvar / Command (startup command parsing)
RELATION = SAME_LAYER_DIFFERENT_IMPLEMENTATION
EVIDENCE =
  IW4X: src/Components/Modules/Flags.cpp:22-103
  CODOL: EX-032 (argv provider partial, source confirmed); EX-034 (argv shape confirmed); STANDALONE-CORE-007 (0x0849413B write confirmed)
CONFIDENCE = HIGH

---

## 三、Runtime Bridge 候选

BRIDGE_ID = BRIDGE_01
LAYER = Entry / Bootstrap
IW4X_MECHANISM =
  DLL injection → DllMain hook (0x6BAC0F) → Main::EntryPoint
  → initialize (security cookie + environment + components)
  → delegate to original CRT startup (0x06BAA2F)
CODOL_REQUIREMENT =
  Need to establish control after Base ordinal 1 / .tvm0 VM boundary.
  Current state: ordinal 1 never returns to EXE (no ret in stub).
  Need to understand what the VM does and identify a post-VM continuation point.
RELATION = SAME_LAYER_DIFFERENT_IMPLEMENTATION
REUSE_POSSIBILITY = POSSIBLE
  IW4X pattern is "hook entry → initialize → delegate to original CRT".
  The structural pattern (inject → hook → init → delegate) is reusable,
  but CODOL's delegate target cannot be the original CRT because
  ordinal 1 enters a VM that never returns.
  A different delegation strategy is required.
CONFIDENCE = HIGH

---

BRIDGE_ID = BRIDGE_02
LAYER = CRT / Startup Environment
IW4X_MECHANISM =
  __security_init_cookie + SetProcessDEPPolicy + SetCurrentDirectory + SetDllDirectory
  executed before original CRT startup in Main::EntryPoint
CODOL_REQUIREMENT =
  Base.dll CRT/locale init currently crashes at Base+0x306A (this=3).
  Need valid locale/heap state inside Base.dll before ordinal 1 can proceed.
RELATION = SAME_LAYER_DIFFERENT_IMPLEMENTATION
REUSE_POSSIBILITY = LOW
  IW4X modifies the host process's environment from outside (DLL injection).
  CODOL's crash is internal to Base.dll's own CRT init and may require
  Base.dll-internal state preparation rather than process-level
  environment changes. The IW4X pattern addresses a different failure mode.
CONFIDENCE = HIGH

---

BRIDGE_ID = BRIDGE_03
LAYER = Dvar / Command (command line parsing)
IW4X_MECHANISM =
  Flags::ParseFlags() modifies GetCommandLineA/W buffer in-place before
  CRT startup; Flags::HasFlag() provides lazy feature gating for Components.
CODOL_REQUIREMENT =
  argv array (0x0196928C/0x01969290) must be populated before gate
  predicate 0x37F580 runs; -q/-qa tokens needed to bypass WIN_NO_TCLS.
RELATION = SAME_LAYER_DIFFERENT_IMPLEMENTATION
REUSE_POSSIBILITY = POSSIBLE
  Both consume process command line at startup.
  IW4X's approach of modifying the buffer before CRT could be applied
  to ensure CODOL's argv array is correctly populated with -q tokens
  before the gate predicate runs.
CONFIDENCE = MEDIUM

---

## 四、最终结论

Q1 = IW4X 与 CODOL 是否在 Bootstrap/Runtime 层存在结构交集？

```text
CONFIRMED
```

三个层（Entry/Bootstrap, CRT/Startup Environment, Command Line Parsing）
均已确认存在结构交集，关系为 SAME_LAYER_DIFFERENT_IMPLEMENTATION。
两者都在"引擎代码执行前"有 bootstrap 层，都在启动阶段准备环境，
都解析 command line。但实现方式明显不同。

---

Q2 = 最有价值的交集在哪一层？

```text
Layer 1 — Entry / Bootstrap (INTERSECTION_01)
```

这是唯一的层，两者都拥有一个"引擎执行前的接管点"。
IW4X 的接管点是 hook 0x6BAC0F，然后 delegate 回原始 CRT。
CODOL 的接管点是 Base ordinal 1 → VM boundary，但永不返回。

事实：这是两者结构最相似的位置，也是差异最大的位置。
IW4X 的 hook-and-delegate 模式可被参考，但 CODOL 需要
不同的 delegate 目标（因为 VM 不返回）。

---

Q3 = 是否已经存在足够证据设计 CODOL Runtime Bridge？

```text
PARTIAL
```

已有证据：
- CODOL Entry → Base ordinal 1 → VM boundary 完整确认
- 0x77F580→0x6212C0 bootstrap/network dispatcher 链 STRONG
- argv gate 0x37F580 语义确认
- CRT/locale 崩溃点 Base+0x306A 确认

缺失证据：
- CODOL FS/Search Path 层未到达（UNKNOWN）
- CODOL Zone/Asset DB 层未到达（UNKNOWN）
- CODOL Game Init 完整链未确认
- .tvm0 VM boundary 之后的执行流未恢复
- Base ordinal 1 的输入/输出合约未完全确认（CORE-008: input contract UNKNOWN）
- 8189FEC / IIPS 错误的精确来源未确认

因此 Q3 = PARTIAL，不能 READY。
缺少的关键证据是：VM boundary 之后的执行流和
CODOL FS/Asset 层的行为。
