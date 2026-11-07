# ICH-004 — CODOL Entry / Bootstrap Bridge 可行性验证

## 0. 范围与冻结输入

本任务不修复 CODOL、不修改 EXE/DLL、不动态调试、不分析 `.tvm0` 内部、
不重新证明 Plan A。只评估：EXE Entry 与 Base.dll ordinal-1 之间是否存在
可承载 IW4X 式 Runtime Bridge 的 Bootstrap Boundary。

冻结证据源：

```text
Plan A                     CODOL_ORDINAL1_LIFECYCLE_FINAL.md  (CLOSED)
CORE-011                   CODOL_STANDALONE_CORE_011_POST_BOUNDARY_EXECUTION.md
CORE-012                   CODOL_STANDALONE_CORE_012_BOOTSTRAP_DESIGN.md
CORE-013R                  CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION.md
ICH-001                    ICH001_02_RESULT.md
ICH-002-A                  ICH002_A_RESULT.md
ICH-002-B                  ICH002_B_RESULT.md
ICH-003                    ICH003_RUNTIME_CROSS_DIFF.md
静态证据                   exe_tls.csv / exe_imports.csv / exe_runtime_boundaries.csv
                           exe_core008_entry_call_contract.csv
                           exe_core010_boot_state_machine.csv
                           exe_core012_entry_candidates.csv
```

固定边界：

```text
CODOL EXE Entry (0x0E5DC690)
  ↓  call dword ptr [0x0E9DC665]
Base.dll ordinal 1 (0x1D6582C, .tvm0 VM entry stub)
  ↓  push/jmp → .tvm0 VM dispatch
(never returns to EXE)
```

---

## 1. PRE-ORDINAL1 窗口分析

### 1.1 EXE Entry 本体

```text
0x0E5DC690  FF 15 65 C6 9D 0E    call dword ptr [0x0E9DC665]
0x0E5DC696  00 × 2410            zero padding; no fall-through
```

Entry 是单条 6 字节指令。Entry 前无显式 push、无寄存器初始化、无栈准备
（CORE-008 静态确认）。Entry 后无原生继续点（CORE-005/012 确认 2410 字节
零填充）。

### 1.2 Entry 前的进程级可执行结构

PE TLS 目录存在：

```text
TLS RVA          = 0x0E5C8000
Callbacks ptr    = 0x00CADA3C  (RVA 0x8ADA3C)
Callback[0]      = 0x00C585F6  (RVA 0x8585F6)
Callback[1]      = 0x00C5C721  (RVA 0x85C721)
TLS Index RVA    = 0x0196930C
```

两个回调目标均位于 `.tp3` 段的 **virtual-only** 区域（超出 raw data 边界），
与 CORE-013R 归因矩阵中的 `NOT_FILE_BACKED_OR_VIRTUAL_ONLY` 分类一致。
CORE-013R 明确未将其纳入可验证目标集。

```text
TLS_CALLBACK_PRESENCE  = CONFIRMED (PE directory)
TLS_CALLBACK_TARGETS   = NOT_FILE_BACKED / VIRTUAL_ONLY
TLS_EXECUTION_BEFORE_ENTRY = UNKNOWN (requires dynamic; prohibited)
```

### 1.3 各初始化职责在 PRE-ORDINAL1 的存在性

| 职责 | PRE-ORDINAL1 窗口内 | 证据 |
|------|---------------------|------|
| CRT 初始化 | **无** | Entry 无 CRT 序言；Base 内部 CRT 在 ordinal-1 后 |
| 环境准备 | **无** | EXE 侧无 SetEnvironment/SetCurrentDirectory 证据 |
| 参数准备 | **无** | argv 全局 0x0196928C/0x01969290 在边界入口均为 0 (12/12) |
| DLL 加载 | **仅 OS Loader 标准** | EXE 只导入 Base.dll ordinal-1；无延迟导入 |
| filesystem 初始化 | **无** | EX-015：Base+0x306A 崩溃前无任何游戏文件访问 |
| command-line 解析 | **无** | provider slot 0x00CA827C 在边界入口时未绑定执行 |
| 可替换函数指针 | **1 个** | IAT slot 0x0E5DC665 本身 |
| 可插入调用点 | **1 个** | EXE Entry 本体 |

### 1.4 PRE_ORDINAL1_WINDOW 结论

```text
PRE_ORDINAL1_WINDOW = EMPTY (EXE image side)
```

EXE 镜像中，从进程启动到 ordinal-1 调用之间不存在任何
IW4X 式初始化窗口。Entry 就是 ordinal-1 调用本身。
唯一的 PE 级 pre-entry 结构（TLS 回调）目标不可验证。

---

## 2. Bootstrap Responsibility Mapping

### 2.1 HOST_VALIDATION

```text
IW4X:
  DllMain: SetProcessDEPPolicy(PROCESS_DEP_ENABLE) + binary identity check
           (0x6F9358 vs BASEGAME_NAME "iw4mp_ceg.exe")
  source:  ICH001_02_RESULT.md src/DllMain.cpp:34-49

CODOL:
  PRE-ORDINAL1: 无 host 验证逻辑
  ORDINAL1:     Base.dll .tvm0 VM 内部语义不可分析
  POST-ORDINAL1: 无 EXE 代码执行证据

CODOL STRUCTURAL EQUIVALENT = MISSING
STATUS = MISSING
```

### 2.2 ENVIRONMENT_SETUP

```text
IW4X:
  Main::Initialize: Utils::SetEnvironment() → IW4x_INSTALL 或 exe 目录
  → SetCurrentDirectoryA/W + SetDllDirectoryA
  source:  ICH002_A_RESULT.md src/Utils/Utils.cpp:151-180

CODOL:
  PRE-ORDINAL1: 无环境准备代码
  Base.dll 内部 CRT/locale init 在 ordinal-1 后
  当前 Base+0x306A 因 this=3 崩溃 (ICH-003)

CODOL STRUCTURAL EQUIVALENT = MISSING (pre-boundary)
STATUS = MISSING
```

### 2.3 COMMAND_LINE_SETUP

```text
IW4X:
  Flags::ParseFlags() 原地去除 GetCommandLineA/W 缓冲区引号
  在 Components::Loader::Initialize() 期间 lazy 触发
  source:  ICH002_A_RESULT.md src/Components/Modules/Flags.cpp:22-103

CODOL:
  EXE 侧确认结构:
    argv count    0x0196928C  (write site 0x00561119)
    argv array    0x01969290  (write site 0x0056111E)
    provider slot 0x00CA827C  (call site 0x00561133)
    gate predicate 0x37F580   (scan -q/-qa → 0x0849413B=1)
    -src=tgp gate 0x0849B501
  但:
    边界入口时 argv globals 全部 = 0 (CORE-009 12/12)
    provider 在 ordinal-1 之后才可能运行
    0x0849B500 writer = NOT_FOUND (static)
    0x0849B501 writer = NOT_FOUND (static)

CODOL STRUCTURAL EQUIVALENT = PARTIAL (post-boundary only)
STATUS = PARTIAL
```

### 2.4 EARLY_ENTRY_TAKEOVER

```text
IW4X:
  DllMain → Utils::Hook(0x6BAC0F, Main::EntryPoint, HOOK_JUMP).install()
  5-byte inline jump redirect before CRT startup
  source:  ICH001_02_RESULT.md src/DllMain.cpp:51

CODOL:
  EXE Entry 0x0E5DC690 是唯一可替换的执行流控制点
  可替换方式:
    (a) 修改 PE AddressOfEntryPoint → 指向外部 bootstrap
    (b) 修改 IAT slot 0x0E5DC665 → 指向 bootstrap DLL
    (c) TLS callback 注入 (targets virtual-only, 不可验证)
  但:
    (a)(b) 均为修改 EXE 磁盘文件或进程内存 = 本任务禁止范围
    (c) 目标不可验证
  即使替换 Entry，仍无可 delegate 的原始 runtime 目标

CODOL STRUCTURAL EQUIVALENT = EXE_ENTRY (only structural candidate)
STATUS = PARTIAL (structural point exists; implementation prohibited/unverified)
```

### 2.5 COMPATIBILITY_INITIALIZATION

```text
IW4X:
  Components::Loader::Initialize() → 60+ Component 构造函数
  Ceg / Auth / QuickPatch / FileSystem / FastFiles 等
  source:  ICH002_A_RESULT.md src/Components/Loader.cpp:90-197

CODOL:
  PRE-ORDINAL1: 无兼容层初始化窗口
  POST-ORDINAL1: 历史链 0x77F580→0x6212C0 NOT_OBSERVED (CORE-011 0/28)
  IIPS/IFS2/CNIFS boundary 在 post-gate; 成功路径无证据

CODOL STRUCTURAL EQUIVALENT = MISSING
STATUS = MISSING
```

### 2.6 ORIGINAL_RUNTIME_HANDOFF

```text
IW4X:
  Main::EntryPoint 最后 return Game::__tmainCRTStartup() (0x06BAA2F)
  直接调用原始 CRT startup → 原始 IW4 Runtime
  source:  ICH001_02_RESULT.md src/DllMain.cpp:25

CODOL:
  ordinal-1 = push 0x592A35B8 + push ecx/edx/ebx/eax + jmp Base+0x1F27FDC
  无 ret 指令 (Plan A CONFIRMED)
  EXE return site 0x0E5DC696 命中 0/3 (Plan A dynamic)
  返回点为零填充，无消耗指令
  => 结构上不可返回

CODOL STRUCTURAL EQUIVALENT = BLOCKED (non-returning VM call)
STATUS = MISSING
```

---

## 3. Bridge Boundary 评估

### 3.1 候选评估表

| 候选 | 控制执行流 | 在原始 Runtime 之前 | 需修改 Base VM | 能建环境 | 能保存原始行为 | 稳定调用边界 | 结论 |
|------|-----------|---------------------|---------------|----------|---------------|-------------|------|
| EXE_ENTRY | YES (可替换) | YES | NO | NO (无窗口) | NO (无 handoff 目标) | YES (PE 结构) | **唯一结构候选** |
| PRE_ORDINAL1 | NO (窗口为空) | YES | NO | NO | NO | NO (不存在) | 不可行 |
| ORDINAL1 | YES (VM 内) | YES | YES (必须) | UNKNOWN | NO (永不返回) | NO (VM stub) | 不可行 |
| POST_ORDINAL1 | UNKNOWN | NO | NO | UNKNOWN | UNKNOWN | NOT_OBSERVED | 不可行 |
| UNKNOWN | — | — | — | — | — | — | 不适用 |

### 3.2 结论

```text
BRIDGE_BOUNDARY = EXE_ENTRY (CANDIDATE only)
```

EXE Entry 是唯一满足"控制执行流 + 在原始 Runtime 之前 + 不需修改 Base VM"
的位置。但它不满足"能建环境"和"能保存原始行为"两个条件。

### 3.3 为什么不是其他候选

```text
PRE_ORDINAL1:  窗口为空（Entry 即 ordinal-1 调用），无可插入点
ORDINAL1:      Plan A 确认 non-returning VM stub；作为 boundary 需
               理解/修改 .tvm0 内部 = 明确禁止
POST_ORDINAL1: CORE-011 0/28 historical candidates NOT_OBSERVED;
               无已确认的 EXE 侧接管点
```

---

## 4. 最小 Bridge 模型

基于证据的最小抽象模型（不写实现代码，不修改任何二进制）：

```text
CODOL EXE
   ↓
Bootstrap Layer (hypothetical)
   ├─ Environment           ← MISSING (no pre-entry window in CODOL EXE)
   ├─ Command line          ← PARTIAL (structures exist post-boundary only)
   ├─ Compatibility         ← MISSING (no initialization window)
   └─ Required runtime setup ← MISSING (no FS/CRT pre-entry evidence)
   ↓
Original CODOL Runtime
   ← BLOCKED: ordinal-1 is non-returning VM stub
   ← No post-ordinal1 EXE continuation confirmed
```

该模型与 IW4X 模型的核心差异：

```text
IW4X:
  EXE Entry → CRT hook → IW4X init → delegate to original CRT → IW4 Runtime
  (hook-and-return; original runtime is directly callable)

CODOL (hypothetical):
  EXE Entry → [Bootstrap init] → ??? → CODOL Runtime
  (??? = no delegate target; ordinal-1 never returns;
   no post-ordinal1 EXE code confirmed)
```

IW4X 模式的三个必要前提在 CODOL 中：

```text
1. 可 hook 的 pre-runtime 位置        → EXE Entry = YES (structural)
2. 初始化窗口（环境/命令行/兼容层）    → NO (Entry 是单条指令)
3. 可 delegate 的原始 runtime 入口    → NO (ordinal-1 non-returning)
```

前提 2 和 3 均不满足。

---

## 5. 最终评估

```text
ICH004_STATUS = PARTIAL

PRE_ORDINAL1_WINDOW =
  EMPTY (EXE image side)
  - Entry = single 6-byte FF15 call to Base.dll ordinal 1
  - No CRT init / environment prep / command-line parsing / FS init
    between process start and ordinal-1 call
  - TLS callbacks exist but targets are NOT_FILE_BACKED (UNKNOWN execution)

IW4X_BOOTSTRAP_ALIGNMENT =
  LAYER_LEVEL: PARTIAL (Entry/Bootstrap structural intersection confirmed ICH-003)
  PATTERN_LEVEL: NOT_ALIGNED
    IW4X = hook → initialize → delegate-to-original-CRT
    CODOL = call non-returning VM stub; no delegate target
  COMMAND_LINE: PARTIAL (same layer, but CODOL provider is post-boundary)
  ENVIRONMENT:   NOT_ALIGNED (no pre-boundary setup window in CODOL)

BRIDGE_BOUNDARY = EXE_ENTRY (CANDIDATE only)
  - Only structural point satisfying "controls flow + before runtime + no VM mod"
  - Does NOT satisfy "can establish environment" or "can preserve original behavior"

ENVIRONMENT_SETUP = MISSING
COMMAND_LINE_SETUP = PARTIAL
EARLY_ENTRY_TAKEOVER = PARTIAL
COMPATIBILITY_LAYER = MISSING
ORIGINAL_RUNTIME_HANDOFF = MISSING

RUNTIME_BRIDGE_FEASIBILITY = LOW
```

`PROMISING` 不适用于当前证据状态。IW4X 的核心模式
（inject → init → delegate）在 CODOL 中缺失两个必要前提：
初始化窗口和 delegate 目标。`EXE_ENTRY` 作为唯一候选 boundary，
即使可以注入，也无法返回原始 runtime。

---

## 6. 阻断点

```text
BLOCKER_01 = ORDINAL1_INPUT_CONTRACT
  EAX/EDX/ESI/EDI/EFLAGS register semantic roles UNKNOWN
  No EXE-provided stack arguments; no caller-side convention evidence
  Source: CORE-008/009/010

BLOCKER_02 = ORDINAL1_NON_RETURNING_BEHAVIOR
  ordinal-1 stub has no ret instruction (Plan A static CONFIRMED)
  EXE return site hit 0/3 dynamic (Plan A)
  Return site is zero padding with no consumer
  => Cannot hand control back to EXE after bootstrap initialization

BLOCKER_03 = VM_EXECUTION_BOUNDARY
  ordinal-1 jumps to .tvm0 VM dispatch (Base+0x1F27FDC → Base+0x1F9DFFD)
  VM internal semantics excluded from scope (Plan A, ICH-004 constraint)
  Cannot determine if VM ever returns to EXE-image code

BLOCKER_04 = RUNTIME_HANDOFF
  CORE-011: 7 historical EXE bootstrap chain RVAs 0/28 hits post-ordinal1
  No EXE image code execution confirmed after ordinal-1 boundary
  No delegate target for bootstrap layer to transfer into

BLOCKER_05 = FILESYSTEM_INITIALIZATION
  EX-015: no game file API call observed before Base+0x306A crash
  main\%s string ref exists but no clean function reached
  Bootstrap layer cannot establish FS paths if it cannot reach FS init

BLOCKER_06 = GAME_INITIALIZATION
  Game Init / Renderer / Main Loop all UNKNOWN (CORE-010 layer D)
  No clean executable engine entry found (EX-020)
  No confirmed post-bootstrap continuation into game runtime
```

所有 6 个阻断点均阻塞 Bridge 形成。本任务不解决它们，仅记录存在性。

---

## 7. 产物清单

```text
ICH004_BOOTSTRAP_BRIDGE.md     (this file)
ICH004_BRIDGE_MATRIX.csv       (6 responsibility rows)
```

## 8. 合规检查

| 约束 | 状态 |
|------|------|
| 不修改 EXE/DLL | PASS |
| 不注入 | PASS |
| 不动态调试 | PASS |
| 不启动 CODOL | PASS |
| 不启动 IW4X | PASS |
| 不分析 .tvm0 内部 | PASS |
| 不重新分析 ordinal-1 | PASS (引用 Plan A CLOSED 结论) |
| 不重新分析历史 TCLS/WeGame | PASS |
| 不扩大到历史 bootstrap RVAs | PASS (仅引用 CORE-011/012 冻结结论) |
| 不自动进入 ICH-005 | PASS |
| 只生成 2 个产物 | PASS |

---

*ICH-004 完成。不进入 ICH-005。*
