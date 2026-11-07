# ICH-001-02 — IW4X Client 原始 IW4 接管链闭合

ICH001_02_STATUS = PARTIAL

DLLMAIN_ENTRY =
  CONFIRMED：src/DllMain.cpp:29 `BOOL APIENTRY DllMain(...)` 是 IW4X DLL 的
  DllMain 入口；第 31 行只在 `fdwReason == DLL_PROCESS_ATTACH` 时继续执行。
  - 当前 commit：iw4x-client @ 0699a7e5（origin/main）。

HOST_VALIDATION =
  CONFIRMED-CODE / EXECUTION-CONDITIONAL：
  - src/DllMain.cpp:34 设置 `SetProcessDEPPolicy(PROCESS_DEP_ENABLE)`。
  - src/DllMain.cpp:36-49 为默认启用的 host validation：
    第 37 行将 0x6F9358 解释为 host 内字符串；第 38 行与
    src/STDInclude.hpp:160 的 `BASEGAME_NAME = "iw4mp_ceg.exe"`（14 字节）比较；
    不匹配时第 40-46 行弹错误框，第 47 行返回 FALSE 阻止加载。
  - src/premake5.lua:59-61、234-237 显示该检查可通过
    `--disable-binary-check` 定义 `DISABLE_BINARY_CHECK` 关闭。
  - 因此默认构建会验证；该条件在“运行时验证了哪个进程”的层面未动态确认。

MAIN_ENTRYPOINT =
  CONFIRMED：`Main::EntryPoint`
  - 定义：src/DllMain.cpp:13-26。
  - 签名：`int EntryPoint()`（无参，返回 `int`）。
  - calling convention：源码未显式标注；项目为 Win32 x86
    （premake5.lua:183 `architecture "x86"`，premake5.lua:217-218 `SharedLib`）。
    MSVC 默认为 `__cdecl`，但这一点属于工具链默认推定。
  - 参数：无。
  - 返回值：`Game::__tmainCRTStartup()` 的返回值（DllMain.cpp:25）。
  - 执行次数：源码没有计数/一次性保护；但源码控制流只把
    0x6BAC0F 跳向它，接管 CRT 启动入口后控制流不回到 0x6BAC0F，
    因此按启动链语义预期只执行一次。没有显式“once”机制。
  - 不负责安装 Hook：Hook 安装在 DllMain.cpp:51。
  - 不负责保存原始函数地址：原始相对目标在 Hook 初始化时保存。
  - 负责初始化 IW4X，并把执行流转给原始 CRT/IW4 入口。

MAIN_ENTRYPOINT_CALLER =
  CONFIRMED-CODE：唯一调用方是 0x6BAC0F 处的原 host 指令被替换后的
  间接控制流，不是显式源码调用。
  - 安装点：src/DllMain.cpp:51
    `Utils::Hook (0x6BAC0F, Main::EntryPoint, HOOK_JUMP).install ()->quick ();`
  - 未发现 `Main::EntryPoint()` 的直接 C++ 调用点。

MAIN_ENTRYPOINT_ROLE =
  IW4X pre-CRT initialization + transfer to original CRT/IW4 startup：
  - src/DllMain.cpp:18 `Game::__security_init_cookie();`
  - src/DllMain.cpp:23 `Initialize();`
  - src/DllMain.cpp:25 `return Game::__tmainCRTStartup();`

HOOK_TARGET =
  0x6BAC0F

HOOK_TARGET_STATUS =
  PRESENT_IN_CURRENT_COMMIT：
  - 当前 commit 的 src/DllMain.cpp:51 仍然写入 `0x6BAC0F`。
  - 不是 HISTORICAL / NOT_PRESENT。
  - 该地址位于 IW4 host 模块而非 iw4x.dll；host 二进制不在本仓库，
    故“该地址当前 host 指令是什么”不能由 iw4x-client 源码直接证明。

HOOK_INSTALLER =
  CONFIRMED：`Utils::Hook(...).install()->quick()`
  - 使用处：src/DllMain.cpp:51。
  - 实现：src/Utils/Hooking.hpp:50-63 初始化 Hook 对象；
    src/Utils/Hooking.cpp:129-140 保存 `place/stub/original`；
    src/Utils/Hooking.cpp:143-168 改写目标处 5 字节；
    src/Utils/Hooking.cpp:170-176 `quick()` 将 installed 标志清 false，
    使析构时不会自动卸载。

HOOK_REPLACEMENT =
  CONFIRMED：`Main::EntryPoint`
  - 使用处：src/DllMain.cpp:51。
  - 定义：src/DllMain.cpp:13-26。

HOOK_MECHANISM =
  CONFIRMED（源码机制）/ NO-TRAMPOLINE-FOR-ENTRY：
  - `HOOK_JUMP` 定义为 true：src/Utils/Hooking.hpp:3。
  - install() 备份 5 字节（Hooking.cpp:154-155），写入 `0xE9` JMP
    及相对偏移（Hooking.cpp:159-161），随后
    `FlushInstructionCache`（Hooking.cpp:165）。
  - 这是一个 5-byte inline jump/detour。
  - `original` 在 Hooking.cpp:138 计算为：
    `place + 5 + *(DWORD*)(place + 1)`，
    即“按目标处原有 E9/JMP 相对地址解释出的目标”。它只保存地址；
    源码未生成 trampoline，也没有复制重定位原指令。
  - 本接管 Hook 的替换函数不通过 `this->original` 调回；它直接进入
    src/DllMain.cpp:25 调用 `Game::__tmainCRTStartup()`。

ORIGINAL_FUNCTION_STORAGE =
  CONFIRMED-ADDRESS-COMPUTATION / ROLE-CONFIRMED：
  - 字段：src/Utils/Hooking.hpp:177 `void* original;`
  - 计算：src/Utils/Hooking.cpp:138。
  - 对 0x6BAC0F 的具体解释结果是 host 二进制中的相对跳转目标，
    不能仅凭 iw4x-client 源码解析；属于 host 侧事实。
  - 已确认该字段不被此 Hook 的 replacement 回调，原始 CRT 入口由
    `Game::__tmainCRTStartup` 符号另行显式调用。

ORIGINAL_IW4_ENTRY =
  CONFIRMED-BINDING / CALL-INTENT：
  `Game::__tmainCRTStartup = __tmainCRTStartup_t(0x06BAA2F)`
  - 符号绑定：src/Game/Functions.cpp:7。
  - 类型：src/Game/Functions.hpp:9 `typedef int(* __tmainCRTStartup_t)(void);`
    第 10 行声明同名函数指针。
  - 调用：src/DllMain.cpp:25。
  - 源码层面可确认：IW4X 初始化完成后实际调用这个绑定的原始入口。

ORIGINAL_IW4_ENTRY_CONFIDENCE =
  SYMBOL_BINDING_HIGH / BINARY_IDENTITY_NOT_PROVEN
  - “实际调用点会执行 0x06BAA2F 绑定的函数指针”在源码级成立。
  - “0x06BAA2F 在 host 二进制中就是原始 IW4 CRT startup”依赖
    逆向/符号命名，不能只凭本仓库源码闭环证明。

ORIGINAL_IW4_ENTRY_CALL_SITE =
  CONFIRMED：src/DllMain.cpp:25
  `return Game::__tmainCRTStartup();`

INITIALIZATION_ORDER =
  ACTUAL_SOURCE_ORDER：
  1. `Main::EntryPoint()` 进入后先执行
     `Game::__security_init_cookie()`（src/DllMain.cpp:18；
     函数指针绑定 src/Game/Functions.cpp:6 = 0x06CA062）。
  2. `Main::Initialize()`（src/DllMain.cpp:3-11）。
     第一层顺序：
     - src/DllMain.cpp:5 设置随机种子；
     - src/DllMain.cpp:7 `Utils::SetEnvironment()`；
     - src/DllMain.cpp:8 `Steam::Proxy::RunMod()`；
     - src/DllMain.cpp:9 `Utils::Cryptography::Initialize()`；
     - src/DllMain.cpp:10 `Components::Loader::Initialize()`。
  3. 返回并执行 `Game::__tmainCRTStartup()`（src/DllMain.cpp:25）。

  第一层目标实现：
  - SetEnvironment：src/Utils/Utils.cpp:166-181。
    `IW4x_INSTALL` 存在时设置 CWD 和 DLL directory；
    否则 src/Utils/Utils.cpp:152-161 以宿主 EXE 目录作为 legacy CWD。
  - Steam::Proxy::RunMod：src/Steam/Proxy.cpp:203-226。
    仅当命令行包含 `-proc ` 时等待父 PID 后终止；常规启动立即返回。
  - Cryptography::Initialize：src/Utils/Cryptography.cpp:9-13，
    调 `Rand::Initialize()`。
  - Components::Loader::Initialize：src/Components/Loader.cpp:90-198。
    先清 allocator（Loader.cpp:93-94），第一个注册 ZoneConvert
    （Loader.cpp:98），然后继续注册其他组件；不展开。

RETURN_TO_IW4_RUNTIME =
  CONFIRMED
  - 源码控制流：Main::EntryPoint 的第 25 行显式
    `return Game::__tmainCRTStartup();`。
  - 该指针绑定 0x06BAA2F（Functions.cpp:7）。
  - 返回值也原样作为 Main::EntryPoint 的返回值。
  - “0x06BAA2F = 原始 IW4 runtime 起点”的最终二进制身份是
    SYMBOL_BINDING_HIGH / BINARY_IDENTITY_NOT_PROVEN。

MINIMAL_CONFIRMED_CHAIN =

```text
iw4x.dll
  ↓
DllMain
  ↓
Main::EntryPoint
  ↓
Hook
  ↓
IW4X initialization
  ↓
Original IW4 Entry
  ↓
IW4 Runtime
```

### Edge evidence

```text
iw4x.dll → DllMain
  src/DllMain.cpp
  symbol: APIENTRY DllMain(HINSTANCE, DWORD, LPVOID)
  line: 29；DLL_PROCESS_ATTACH 分支 line: 31

DllMain → Main::EntryPoint
  src/DllMain.cpp
  symbol: Utils::Hook::Hook(DWORD place, void* stub, bool useJump)
          + Hook::install() + Hook::quick()
  line: 51 安装 `0x6BAC0F -> Main::EntryPoint` 的 HOOK_JUMP
  src/Utils/Hooking.cpp
  Hook::initialize line: 129-140
  Hook::install line: 143-168（0xE9 inline jump，line 159-161）
  Hook::quick line: 170-176

Hook → IW4X initialization
  src/DllMain.cpp
  symbol: Main::EntryPoint / Main::Initialize
  line: 13 定义；line: 18 __security_init_cookie；
  line: 23 调用 Initialize；line: 3-11 初始化顺序

IW4X initialization → Original IW4 Entry
  src/DllMain.cpp
  symbol: Main::EntryPoint return Game::__tmainCRTStartup()
  line: 25
  src/Game/Functions.cpp
  symbol: Game::__tmainCRTStartup = 0x06BAA2F
  line: 7
  src/Game/Functions.hpp
  symbol: __tmainCRTStartup_t / extern __tmainCRTStartup
  line: 9-10

Original IW4 Entry → IW4 Runtime
  src/Game/Functions.cpp
  symbol: __tmainCRTStartup_t(0x06BAA2F)
  line: 7（执行流转入该函数指针指向的 host 入口）
  status: SYMBOL_BINDING_HIGH / BINARY_IDENTITY_NOT_PROVEN
```

## Unknown / boundary

```text
HOOK_MECHANISM_TRAMPOLINE = NO（源码未生成；original 只是地址保存）
HOST_BINARY_INSTRUCTION_AT_0x6BAC0F = UNKNOWN（host 不在本仓库）
0x06BAA2F_BINARY_IDENTITY = NOT_PROVEN（只有源码符号绑定）
MAIN_ENTRYPOINT_CDECL = CANDIDATE（MSVC x86 默认，非显式源码标注）
```
