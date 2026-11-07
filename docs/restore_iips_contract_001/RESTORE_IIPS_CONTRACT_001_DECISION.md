# RESTORE-IIPS-CONTRACT-001 — IIPS provider initialization contract

## 判定

```text
RESTORE_IIPS_CONTRACT_001_STATUS = COMPLETE

GETRM_STATIC_CALLER            = NONE_IN_IMAGE
                                 (GetResourceManagerII has exactly one in-image
                                  reference: its own export-directory entry)
GETRM_STATIC_CHAIN             = STATIC_CHAIN_BLOCKED_AT_EXTERNAL_BOUNDARY
                                 (callers are external and reached by name via
                                  GetProcAddress; no chain exists to follow)
GETRM_RUNTIME_OBSERVED         = NO
                                 (not observed in 9 EB-003 runs / 2 A-B runs,
                                  2 providers, 60–90 s windows)
GETRM_PREREQUISITE             = ResourceManagerII::Initialize() must complete,
                                 which requires LoadLibrary("IFS.dll") ->
                                 IIPSWndMsgProcessor -> LaunchIIPSHostApp ->
                                 pipe connect -> InitializeWorkAfterClientConnected
                                 -> readiness PostMessage(0x506D)

IIPSINIT_MEANING               = MSVC DECORATED SYMBOL NAME ("?iipsinit"),
                                 NOT a window class or title literal,
                                 NOT an initialization function name
8189FEC_PRODUCER               = runtime formatter (no byte literal in any
                                 shipped binary)
8189FEC_SEMANTICS              = UNKNOWN
                                 (DISPLAYED_VALUE confirmed; CONTROL_FLOW_VALUE
                                  unknown)
FFFFFFFF_SOURCE                = UNKNOWN
                                 (found in all images 17221/43239/9080 times;
                                  mere presence is not attribution)

PROVIDER_A_FIRST_DIVERGENCE    = window text: "Environment List Box" present;
                                 #32770 致命错误 dialog present
PROVIDER_B_FIRST_DIVERGENCE    = same window class with EMPTY text;
                                 no #32770 dialog; self-exit 0xFFFFFFFF
LAST_COMMON_OBSERVABLE_STATE   = iips.dll loaded AND the "iipsinit"-classed
                                 window created, in BOTH conditions

CALLBACK_CONTRACT              = PostMessageA(hWnd, 0x506D, wParam=1, lParam=0)
                                 at iips.dll RVA 0x17E90
SYNC_CONTRACT                  = CreateEventA/W, SetEvent, WaitForSingleObject,
                                 WaitForMultipleObjects, CreateMutexA,
                                 CreateFileMappingA, OpenFileMappingA,
                                 MapViewOfFile, CreateThread
FILE_CONTRACT                  = LoadLibrary("IFS.dll")  -> FAILS (err=126)
                                 IIPSHostApp.exe via ShellExecute
                                 NECESSARY BUT NOT SUFFICIENT: exposing IFS.dll in
                                 a sandbox makes it loadable, yet the contract
                                 still does not advance (see §8b)
REGISTRY_CONTRACT              = NOT_OBSERVED
NAMED_OBJECT_CONTRACT          = Global\SharedSpaceName_,
                                 Global\FDTFileMutxtName_,
                                 Global\ReadBitMapInfos_,
                                 Global\IIPSShareState_MMF_,
                                 Global\IIPSShareState_Mutex_,
                                 Global\DownloadingFileInfos_,
                                 \\.\Pipe\

ROOT_BLOCKING_CONDITION        = The declared contract does not advance past its
                                 FIRST step. Step 1 (the provider's window being
                                 created) is observed in 3/3 comparable runs;
                                 step 2 (IFS.dll loaded as a result of the
                                 provider's own initialisation) and step 3
                                 (IIPSHostApp.exe launched) are observed in 0/3.
                                 The blocker therefore lies UPSTREAM of
                                 LoadLibrary("IFS.dll"), not at it: satisfying the
                                 IFS dependency in a sandbox does not advance the
                                 sequence.
CONFIDENCE                     = CONFIRMED for the contract shape, for the
                                 IFS dependency being unresolvable, and for the
                                 contract not advancing past step 1.
                                 UNKNOWN for: the numeric semantics of 8189fec and
                                 0xFFFFFFFF, and the precise upstream precondition
                                 that is unmet.
NEXT_TARGET                    = Identify the precondition between "window created"
                                 and "LoadLibrary IFS.dll" (see §9)
```

---

## 0. 边界与完整性

```text
原始 iips.dll      byte-identical   E2367C48...F97770   347704 bytes
原始 EXE           byte-identical   36997674...72B537   7841344 bytes
原始 Base.dll      byte-identical   EF75220D...BC6A20   60327992 bytes
LocalRM_v3.dll     byte-identical   032FAC66...A3EF26   352256 bytes
```

本轮**未**修改任何原始文件；A/B 通过 EB-003 已建立的隔离沙箱实现。
全程**未**使用 debugger / CDB / WinDbg / hardware breakpoint / anti-debug bypass /
TenProtect / ACE bypass / PRCL 静态扫描 / `.tvm0` ISA 恢复。
观测手段仅限 `CreateProcess`、`Toolhelp32`、`ReadProcessMemory`、
`EnumWindows`、`SendMessageTimeout`（读窗口文本）、NT 对象目录枚举。

`RESTORE-ENGINE-BRIDGE-002` 依前轮结论视为 INVALIDATED，本轮**未**引用其任何数据。

---

## 1. Task 02 — `iipsinit` 到底是什么（**不是**初始化函数）

本轮被明确要求"不能仅凭字符串名判断"。静态结果：

```text
EXE 中 "iipsinit" 出现次数 = 1
  文件偏移 0x75B90C，所在段 .tp3
  实际字节上下文：  ... 3F 69 69 70 73 69 6E 69 74 00 00 00 00 [ptr] ...
                       ?  i  i  p  s  i  n  i  t  NUL NUL NUL NUL
  即符号为 "?iipsinit"，NUL 补齐到 4 字节边界后紧跟一个指针

邻居（同一张表）：
  0x75B8B4  '.?AVdwRoom@@'
  0x75B8CC  '.?AVdwRoomImp@@'
  0x75B90B  '?iipsinit'              <- 就是它
  0x75B920  '.?AVCallsign_UnequipAdvancedConsumable@@'
  0x75B954  '.?AVCallsign_UnequipItem@@'
  ...
  EXE 中 '.?AV' 类型描述符总数 = 1251

iips.dll 中 "iipsinit" 出现次数 = 0
LocalRM_v3.dll 中 "iipsinit" 出现次数 = 0
```

```text
IIPSINIT_IS = RTTI_SYMBOL_NAME
IIPSINIT_IS_NOT = window class literal / window title / initialization function
```

唯一引用该符号地址的代码位于 EXE RVA `0x18F45A`（`mov [esp+0x58], 0x00E6F90C`），
其 ±0x400 范围内**没有**任何 `RegisterClassEx*` / `CreateWindowEx*` 等 API 名字符串，
所以该点本身不是窗口类注册点。

> 运行时 EB-003 观察到一个**类名回读为 `iipsinit`** 的窗口。
> 由于两张 provider 镜像都不含该字面量，该窗口类名由**代码构造**，而不是从
> provider 的 `.rdata` 读出的。窗口类名的确切来源记为 `CANDIDATE`，本轮不宣称已知。

---

## 2. Task 01 — `GetResourceManagerII` 反向分析

```text
GetResourceManagerII (RVA 0x1C80) 的镜像内引用数 = 1
   0x41C00  .rdata  imm32   → 就是导出目录的 AddressOfFunctions 条目
   => 镜像内没有任何调用者
```

```asm
GetResourceManagerII @0x1C80  （原始 iips.dll）
  6A FF                  push -1
  68 A9 25 03 10         push 0x100325A9           ; SEH scope table
  64 A1 00 00 00 00      mov  eax,fs:[0]
  50                     push eax
  51                     push ecx
  A1 20 20 04 10         mov  eax,[0x10042020]     ; /GS cookie
  33 C4                  xor  eax,esp
  50                     push eax
  8D 44 24 08            lea  eax,[esp+8]
  ...
  F6 05 6C EB 04 10 01   test byte [0x1004EB6C],1   ; <-- singleton GUARD
  75 5B                  jne  0x1D05
  83 0D 6C EB 04 10 01   or   dword [0x1004EB6C],1
  68 10 04 00 00         push 0x410                ; object size
  ...
  E8 71 A1 02 00         call 0x2BE34              ; operator new
```

构造函数的调用点（RVA `0x11F20`）恰好两个：

```asm
0x1CD4  （在 GetResourceManagerII 内部，lazy singleton 路径）
        push eax ; call 0x11F20 ; mov [0x1004EB68],eax   <- 写入 singleton slot

0x1024D （独立函数）
        call 0x2AC0 ; push eax ; call 0x11F20
        push 0x10035684      ; "[ResourceManager::ResourceManager()][OK]"
        call 0x4280
        ; 不写 singleton slot，不碰 guard
```

```text
GETRM_DIRECT_CALLER   = NONE_IN_IMAGE
GETRM_CALLER_CHAIN    = STATIC_CHAIN_BLOCKED_AT_EXTERNAL_BOUNDARY
GETRM_PREREQUISITES   = singleton guard 0x1004EB6C == 0 时方可构造；
                        构造结果写入 slot 0x1004EB68
GETRM_BLOCKING_CONDITIONS = guard 已置位（则直接返回缓存对象）；
                        更上游：ResourceManagerII::Initialize() 必须先成功
```

**未伪造 caller。** 静态链在外部边界处截断，因为调用方在镜像之外、按名字解析。

> 附带确认一个技术细节：`0x1004EB6C` / `0x1004EB68` 在重定位表中**不存在**，
> 但代码确实编码了 `test byte [0x1004EB6C],1`（字节 `F6 05 6C EB 04 10 01`）。
> 即这些是**未重定位的绝对地址**，模块假定自己落在 `0x10000000`。

---

## 3. Task 06 — provider 初始化契约（来自 provider 自己的日志表）

`iips.dll` 自带 327 条形如 `[Class::Method()][LastError:...]` 的日志消息。
这是本轮最有价值的证据：**provider 用自己的话记录了它的初始化契约**。
`ResourceManagerII::Initialize()` 的顺序（每条都对应一个真实代码位点）：

```text
 1. ResourceManagerII::ResourceManagerII()            -> OK       (0x35E88)
 2. ResourceManagerII::Initialize()                   -> begin    (0x127B7)
 3. SetPrivilege / SE_CREATE_GLOBAL_NAME                          (0x36038)
 4. IIPSWndMsgProcessor::Initialize  创建窗口                      (0x360F8)
 5. LoadLibrary IFS.dll                                           (0x12CC8)
    └─ 失败则 LastError:IIPSERR_IFS_LOAD_DLL_ERROR [NifsInitError]
 6. LaunchIIPSHostApp  (IIPSHostApp.exe, "/mode iipslaunch")       (0x13294)
    └─ 失败则 IIPSERR_IIPSHOST_INIT
 7. m_iipsClient connect   (命名管道)                              (0x13363)
    └─ 失败则 IIPSERR_PIPE_INIT
 8. InitializeWorkAfterClientConnected():
       m_iipsShareState.Open()                                   (0x17987)
       LoadFileList                                              (0x17A82)
       m_resUseRec.Load()
       check m_sharedSpaces
       "ResourceManagerII::Initialize() succeed"                 (0x17E52)
 9. PostMessageA(hWnd, 0x506D, 1, 0)   <-- READINESS HANDSOFF     (0x17E90)
```

### 回调/就绪握手（Task 07）

```asm
0x17E86  6A 00                 push 0              ; lParam
0x17E88  6A 01                 push 1              ; wParam
0x17E8A  68 6D 50 00 00        push 0x506D         ; Msg
0x17E8F  52                    push edx            ; hWnd (callback member)
0x17E90  FF 15 28 34 03 10     call dword [0x10033428]
```

IAT 槽 `0x10033428` 解析为 **`USER32!PostMessageA`**。

> 注意：日志字符串写的是 `[SendMessage]`，但**导入表才是权威**。
> 这是一个"日志文本不等于 API"的实例，本轮按导入表纠正。

`0x506D` 作为立即数在 `iips.dll` 中出现 5 次：`0x15671, 0x179E1, 0x17BC7, 0x17C4E, 0x17E8B`。

---

## 4. Task 03 — `8189fec` 的产生路径

```text
DISPLAYED_VALUE   = CONFIRMED
    条件 A 对话框文本："初始化IIPS错误：8189fec。"
PRODUCED_VALUE    = NOT_OBSERVED
    "8189fec" / "8189FEC" 的字节字面量在四个镜像中全部为 0 次：
       EXE=0  Base.dll=0  iips.dll=0  LocalRM_v3.dll=0
    => 该值在运行时被格式化产生，小写十六进制、无 0x 前缀
       （EXE 中 '%x' 33 次、'0x%x' 仅 3 次）
CONTROL_FLOW_VALUE = UNKNOWN
    无法在 protected boundary 之前证明它参与控制流
```

**数值事实**（不作为语义）：token `8189fec` 为 **7** 位十六进制；
按 32 位读作 `0x08189FEC`，**bit31 为 0**，所以**不是**负的 HRESULT 形态。

```text
ERROR_VALUE_SEMANTICS = UNKNOWN
```

### 与 `8189FFCE` 的关系（Task 10）

```text
8189fec   7 hex digits  -> 0x08189FEC
8189FFCE  8 hex digits  -> 0x8189FFCE
high 16 : 0x0818 vs 0x8189   DIFFERENT
low  16 : 0x9FEC vs 0xFFCE   DIFFERENT
两者都不是任何 shipped binary 里的字节字面量
```

```text
RELATION_8189FEC_8189FFCE = NOT_EQUATED   (REFUTED as unsupported)
```

> 按要求，本轮**未**把两者自动等同。它们在数字形状上就不同（7 位 vs 8 位），
> 低位与高 16 位均不同。

---

## 5. Task 04 — `0xFFFFFFFF` 终止路径

```text
条件 B 在 5 次运行中有 4 次（B2/B3/B4/B5）以 exit code 0xFFFFFFFF 自行退出，
时间约 30.5 s；B1 早于退出码观测的加装，故未携带该信号。

字面量 0xFFFFFFFF 出现次数（因此"存在"本身不构成归因）：
    EXE            17221
    Base.dll       43239
    iips.dll        9080
    LocalRM_v3.dll  9080
```

```text
FFFFFFFF_SOURCE = UNKNOWN
    return value / ExitProcess argument / exception-derived / HRESULT-like /
    engine status / thread exit code / wrapper status —— 均未确证
```

**不根据数值外形猜语义。**

---

## 6. Task 05/07/08 — A/B 运行时差分（**第一处分叉**）

两次运行使用相同启动条件（`codoMP_client_shipRetail.exe -q`，60 s，同一观测器）。

```text
                     A (原始 iips.dll)        B (LocalRM_v3)
modules              151                      136
threads               71                       63
windows                7                        2
gate                 通过                     通过
iips.dll 加载        YES                      YES
```

窗口时间线：

```text
A:
   9.636  #32770         '致命错误'                 <- 错误对话框
   9.646  iipsinit       'Environment List Box'      <- 有文本
   9.647  IME            'Default IME'
   9.671  MSCTFIME UI    'MSCTFIME UI'
   9.671  SoPY_Hint      'HintWnd'
   9.671  SoPY_UI        ''
   9.672  Sogou_TSF_UI   'Sogou_TSF_UI'

B:
   7.966  iipsinit       ''                          <- 同 class，文本为空
   8.170  IME            ''
```

```text
两者共有窗口类 = {iipsinit, IME}
仅 A 有的类     = {#32770, MSCTFIME UI, SoPY_Hint, SoPY_UI, Sogou_TSF_UI}
                 （IME / 搜狗 / Windows 子系统，非 provider 产物）
仅 B 有的类     = {}

LAST_COMMON_OBSERVABLE_STATE = iips.dll 已加载
                               AND 类名为 iipsinit 的窗口已被创建
                               —— 这两件事在 A 与 B **都**发生
FIRST_DIVERGENCE             = 该窗口的 TEXT
                               A: "Environment List Box"
                               B: （空）
                               以及 #32770 致命错误对话框仅在 A 出现
```

> 重要修正：`iipsinit` 窗口**在两种条件下都出现**。
> 因此"窗口存在与否"**不是** A/B 的分叉点；分叉点是**窗口内容**与**错误 UI**。

### provider 依赖模块在两种条件下都**没有**出现

```text
IFS.dll         A=False  B=False
IIPSHostApp     A=False  B=False
IIPSCheck       A=False  B=False
IIPSVFS         A=False  B=False
p2papp          A=False  B=False
Download.dll    A=False  B=False
```

即：静态契约要求的依赖链（IFS → HostApp → pipe）在**两种条件下都没有推进**。

---

## 7. Task 11/12 — 同步 / 命名对象契约

```text
SYNC_CONTRACT（iips.dll 实际导入）
    CreateEventA / CreateEventW        各 1
    SetEvent                           1
    WaitForSingleObject                1
    WaitForMultipleObjects             2
    CreateMutexA                       1
    CreateFileMappingA                 1
    OpenFileMappingA                   1
    MapViewOfFile                      2
    CreateThread                       1
    PostMessageA                       1
    CreateWindowExA                    1
    CreateFileA / CreateFileW          各 1
    ReadFile                          16
    WriteFile                          2

    CreateNamedPipe* / ConnectNamedPipe / WaitNamedPipe*  = 未导入
    => "pipe connect" 是用 CreateFile 打开管道，而不是服务端建管道
```

```text
NAMED_OBJECT_CONTRACT（iips.dll .rdata 中的确切名字）
    Global\SharedSpaceName_         共享内存  (OpenFileMappingA + MapViewOfFile)
    Global\FDTFileMutxtName_        文件传输 mutex
    Global\ReadBitMapInfos_         读位图
    Global\IIPSShareState_MMF_      share-state 内存映射
    Global\IIPSShareState_Mutex_    share-state mutex
    Global\DownloadingFileInfos_    下载信息
    \\.\Pipe\                       管道前缀

    IIPSHostApp.exe                 宿主进程（"/mode iipslaunch"）
    IFS.dll                         IFS 库
```

基线快照（运行前）显示上述全部命名对象**均不存在**。

---

## 8. Task 13/14 — 根因阻塞条件（**IFS.dll 依赖不可满足**）

契约第 5 步是 `LoadLibrary("IFS.dll")`。实测（真实 32-bit host，
以 `IIPS\` 作为 CWD 与 DLL 目录）：

```text
LoadLibraryA("IFS.dll")  = FAIL  err=126  (ERROR_MOD_NOT_FOUND)
LoadLibraryA("ifs.dll")  = FAIL  err=126
LoadLibraryA("IFS2.dll") = PASS  base=0x10000000
      GetProcAddress(CreateIFSLibDll)           = 0x100166D0
      GetProcAddress(DestoryIFSLibDll)          = 0x10016740
      GetProcAddress(IFSDllVerifyApiCompatable) = 0x10016760
```

```text
工作区内名为 IFS.dll 的文件          = 0 个（全盘搜索）
实际存在的 IFS 家族文件              = IFS2.dll（13 处副本）
IFS2.dll 的导出                      = CreateIFSLibDll (ord 1)
                                       DestoryIFSLibDll (ord 2)
                                       IFSDllVerifyApiCompatable (ord 3)
iips.dll 中 "IFS2" 出现次数          = 0
iips.dll 查找的入口名                = CreateIFSLibDll (2 次)
                                       DestoryIFSLibDll (2 次，原文即为此拼写)
```

**结论**：provider 是按 `IFS.dll` 构建的，而安装里只有 `IFS2.dll`，
且 `IFS2.dll` 恰好导出 provider 要找的那三个入口。
`LoadLibrary("IFS.dll")` 在正常搜索顺序下无法解析，于是契约在 IFS 这一步失败 ——

> 该步位于 **pipe connect 之前**、**InitializeWorkAfterClientConnected 之前**、
> 因而也在**就绪 PostMessage(0x506D) 之前**，即在任何可能返回
> ResourceManager 的路径之前。

```text
ROOT_BLOCKING_CONDITION = LoadLibrary("IFS.dll") 不可解析
CONFIDENCE              = CONFIRMED（依赖不可满足）
```

**必须并列记录的限制**：这个依赖缺失对 **A 与 B 同样成立**（A 也没有 IFS.dll，
A 的依赖模块同样未出现）。所以它解释的是"**为什么两者都走不到 GetRM**"，
而**不是**"为什么 A 与 B 不同"。A/B 的差异（窗口文本、错误对话框）
发生在更下游，其成因本轮未确证。

---

## 8b. 单因子实验：IFS 依赖是**必要**但**不充分**的

为检验"IFS 就是直接阻塞点"这一假设，做了一个单因子实验：
**只在沙箱里**把 `IFS2.dll` 以 `IFS.dll` 的名字暴露给 provider
（原始安装目录全程只读，结束时重新校验 SHA256 未变）。

```text
沙箱内名字解析（真实 32-bit host，IIPS\ 作为 CWD 与 DLL 目录）：
  LoadLibraryA("IFS.dll")  = PASS  base=0x10000000      <- 之前是 FAIL err=126
        GetProcAddress(CreateIFSLibDll)           = 0x100166D0
        GetProcAddress(DestoryIFSLibDll)          = 0x10016740
        GetProcAddress(IFSDllVerifyApiCompatable) = 0x10016760
```

然后以与条件 B 完全相同的方式运行观测器：

```text
RUN_START   ... sandbox_ifs
8.072  WINDOW_NEW  class=iipsinit  text=        <- 文本仍为空
8.278  WINDOW_NEW  class=IME       text=
60.029 PROCESS_END exited=False exitcode=terminated

IFS*.dll 已加载        : True     （因为文件被放进搜索路径）
IIPSHostApp 已启动      : False
命名对象出现            : 无
窗口数                  : 2

原始 iips.dll 未变      : True
```

```text
IFS_DEPENDENCY = NECESSARY_BUT_NOT_SUFFICIENT  (CONFIRMED)
```

**满足 IFS 依赖并没有让契约前进一步。** 这说明阻塞点在 IFS 步骤的**上游**。

---

## 8c. 契约究竟推进到哪一步

用 provider 自己声明的副作用顺序做判据，只用**同一台仪器**（AboProbe）跑的运行：

```text
步骤                                                          3 次可比运行中的观察数
1. IIPSWndMsgProcessor 创建窗口                                      3 / 3
2. IFS.dll 被 provider 自己加载                                      0 / 3
3. IIPSHostApp.exe 被启动                                            0 / 3
4. 管道连接                                                          0 / 3
5. ShareState 命名对象出现                                           0 / 3
```

> 唯一让 `IFS*.dll` 载入的那次运行是沙箱实验，而那次是**文件被放进搜索路径**
> 才载入的，不是 provider 走到那一步才载入的 —— 因此**不计**为步骤 2 的达成。

```text
CONTRACT_ADVANCES_PAST_STEP_1 = NO            (CONFIRMED)
ROOT_BLOCKING_CONDITION       = 步骤 1 与步骤 2 之间未被满足的前置条件
```

**这是一个负结论，但它把搜索空间缩小到了明确的一段**：阻塞点位于
"窗口已创建" 与 "`LoadLibrary("IFS.dll")`" 之间，而不是 IFS 依赖本身。

---

## 8d. 该区间内一个具体的候选前置条件（`CANDIDATE`，非 `CONFIRMED`）

契约在步骤 1→2 之间包含 `SetPrivilege` / `IIPSERR_PRIVILEGE_SE_CREATE_GLOBAL_NAME`，
而后续步骤（`m_iipsShareState.Open()` 等）操作的正是 `Global\...` 命名对象。
纯令牌查询（不修改任何东西）结果：

```text
令牌中的权限总数        = 5
SeCreateGlobalPrivilege = ABSENT
SeChangeNotifyPrivilege = PRESENT, enabled=True
SeShutdownPrivilege     = PRESENT, enabled=False
SeDebugPrivilege        = ABSENT
进程已提权 (IsUserAnAdmin) = False
```

```text
UNMET_PRECONDITION_CANDIDATE = SetPrivilege / SeCreateGlobalPrivilege 不可得
LEVEL                        = CANDIDATE
```

**为什么只到 `CANDIDATE`**：这是**观测进程自身令牌**的属性，
既不能证明目标进程的 `SetPrivilege` 步骤确实失败，
也不能证明 provider 就停在这一步。它**缩窄了区间，但没有关闭它**。

---

## 9. 证据分级汇总

```text
CONFIRMED
  "iipsinit" 是 MSVC 装饰符号名，不是窗口类/标题字面量（两个 provider 均为 0 次）
  GetResourceManagerII 镜像内无调用者，唯一引用是其导出目录条目
  ResourceManager 构造函数恰有两个调用点：0x1CD4（singleton 路径）与 0x1024D
  provider 初始化契约的完整顺序（来自其自身 327 条日志表）
  就绪握手 = PostMessageA(hWnd, 0x506D, 1, 0) @ RVA 0x17E90
  LoadLibrary("IFS.dll") 在真实 32-bit host 中失败，err=126
  全工作区不存在 IFS.dll；存在 IFS2.dll，且导出所需三入口
  iips.dll 从不提及 IFS2
  A 与 B 都加载 iips.dll，都创建 iipsinit 类窗口
  第一处分叉 = 窗口文本 + #32770 错误对话框
  命名对象契约的全部确切名字
  LocalRM_v3 携带原始代码字节但该路径不可达

STRONG_CANDIDATE
  (none promoted) — the IFS dependency is necessary but provably not sufficient

CANDIDATE
  0xFFFFFFFF 是条件 B 自行退出的退出码（4/5 次观测），语义未知
  iipsinit 窗口类的创建者（代码构造，来源未定）
  未被满足的前置条件 = SetPrivilege / SeCreateGlobalPrivilege 不可得
      （观测器令牌中该权限 ABSENT，进程未提权；契约后续步骤需要 Global\ 命名对象）

UNKNOWN
  8189FEC 的语义（DISPLAYED 已确认，CONTROL_FLOW 未知）
  0xFFFFFFFF 的语义
  A/B 分叉（窗口文本差异）的成因
  步骤 1 与步骤 2 之间那个未被满足的前置条件
  RM slot 语义

REFUTED
  "8189FEC 与 8189FFCE 是同一个值"（位数与高低位均不同）
  "iipsinit 是初始化函数名"
  "provider 的 §5 步 IFS 失败只发生在条件 B"
  "IFS 依赖缺失就是直接阻塞点"（沙箱实验已否证：满足它后契约仍不推进）

NOT_OBSERVED
  GetResourceManagerII 运行时调用（9+2 次运行、两种 provider）
  RM 对象被消费 / RM vtable 被访问 / RM vtable 调用
  ReleaseResourceManagerII 调用
  registry 访问
  IFS.dll 加载成功 / IIPSHostApp.exe 启动 / 命名对象出现

INSTRUMENTATION_BLOCKED
  Base.dll ~32.7 MB .tvm0 内的保护侧决策点
  LoadLibraryA/GetProcAddress IAT hook 未捕获相关调用
  （因此**不得**声称它们就是 provider 初始化入口）
```

关于 `GetRM not observed` 的**正确表述**（本轮严格遵守）：

> 在当前 9 次 EB-003 运行 + 2 次 A/B 运行、两种 provider、
> 以及当前非 debugger 观测窗口内，**未观察到** `GetResourceManagerII` 调用。

**不写**"Engine 从不调用 GetResourceManagerII"。

---

## 10. 复现

```powershell
# 静态
python restore_iips_contract_001/t01_iipsinit_identity.py       # iipsinit 是符号名
python restore_iips_contract_001/t02_window_class_owner.py      # 无该字面量
python restore_iips_contract_001/t03_getrm_backward.py          # 反向引用
python restore_iips_contract_001/t04_disasm_key_sites.py        # 关键位点反汇编
python restore_iips_contract_001/t05_second_site.py             # 第二个构造点
python restore_iips_contract_001/t06_log_string_table.py        # provider 日志表
python restore_iips_contract_001/t07_iipsinit_origin.py         # 符号来源
python restore_iips_contract_001/t08_iipsinit_use_site.py       # 唯一使用点
python restore_iips_contract_001/t09_init_contract_sites.py     # 契约位点
python restore_iips_contract_001/t10_callback_handoff.py        # 就绪握手
python restore_iips_contract_001/t11_sendmessage_import.py      # PostMessageA
python restore_iips_contract_001/t13_class_owner_and_8189fec.py # 8189fec 分类
python restore_iips_contract_001/t14_8189_relations.py          # 不等同
python restore_iips_contract_001/t15_ffffffff_and_sync.py       # 0xFFFFFFFF + 同步
python restore_iips_contract_001/t16_pipe_and_sharename.py      # 命名对象确切名
python restore_iips_contract_001/t17_named_object_runtime.py    # 基线快照
python restore_iips_contract_001/t18_ifs_dll_missing.py         # IFS.dll 缺失

# 实测 IFS 名字解析
.\restore_iips_contract_001\observer2\out\AboProbe.exe --nameprobe `
    ".\COD OL\IIPS"

# A/B 运行时
.\restore_iips_contract_001\observer2\out\AboProbe.exe --mode A --tag A1 --duration 60
.\restore_iips_contract_001\observer2\out\AboProbe.exe --mode B --tag B1 --duration 60 `
    --sandbox ".\restore003\sandbox_B"

# 汇总
python restore_iips_contract_001/t12_ab_differential.py
python restore_iips_contract_001/t19_aggregate.py
```

---

## 11. 下一步（单一目标）

```text
NEXT_TARGET = 定位 "步骤 1（窗口已创建）" 与 "步骤 2（LoadLibrary IFS.dll）"
              之间那个未被满足的前置条件。
```

最小实验（不做额外扩张）：

1. 该区间在契约里只有两步之差，因此应做**定向**分析而不是扩大扫描：
   - 在 `ResourceManagerII::Initialize()` 的 begin（RVA 0x127B7 引用的
     `0x35F14` 串）与 `LoadLibrary IFS.dll`（RVA 0x12CC8 引用的 `0x36318` 串）
     之间的代码区间内，逐条列出所有 `call` / 条件分支 / `LastError:` 日志引用，
     找出这段代码里**先于 IFS 加载**的每一个检查点。
   - 已知该区间应包含：`SetPrivilege` / `SE_CREATE_GLOBAL_NAME`、
     `IIPSWndMsgProcessor::Initialize`、`getkey`、
     `IIPSERR_GETMODULEPATH` / `IIPSERR_GETMAINMODULEPATH`。
2. `SetPrivilege` 是本轮最可疑的候选：它需要进程具备
   `SeCreateGlobalPrivilege` 才能创建 `Global\` 命名对象，而契约后面正要用
   `Global\SharedSpaceName_` / `Global\IIPSShareState_*`。
   非管理员/受限令牌下该权限可能不可用。
   先在**不修改任何文件**的前提下，用同样非侵入的方式确认当前进程令牌是否持有
   `SeCreateGlobalPrivilege`，以及该结果与 A/B 两种条件是否相关。
3. 判据：找到步骤 1→2 之间第一个"能证明未被满足"的前置条件，或
   严格证明该区间在当前观测手段下不可继续。
4. 若仍不推进，按同一标准记录新的负证据，**不要**修改结论去迎合旧模型。

**若观测手段在 protected boundary（`.tvm0`）前无法继续：立即 STOP，不猜其内部逻辑。**

---

## 12. 本轮未做的事（边界）

未修改原始 EXE / `iips.dll` / Base.dll / BugTrace.dll / TenProxy.dll；
未使用 debugger / CDB / WinDbg / hardware breakpoint；
未绕过反调试 / TenProtect / ACE；未做 PRCL 静态扫描；
未恢复 `.tvm0` ISA；未猜 ResourceManager slot 语义；
未访问在线服务；未构造假的 FF / Zone / Asset；
未恢复 WeGame / TCLS / IIPS QoS；
**未**把 `8189FEC` 与 `8189FFCE` 等同；
**未**把 `iipsinit` 当作初始化函数；
**未**把 LocalRM 缺少某个行为直接认定为 root cause。

`LoadLibraryA`/`GetProcAddress` 的 IAT hook 未捕获相关调用，
因此本轮**没有**声称它们是 provider 初始化入口。
