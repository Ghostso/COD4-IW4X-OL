# ICH-002-A — IW4X CRT / Entry / Memory Runtime 差分

ICH002_A_STATUS = COMPLETE

CRT_DEPENDENCY = YES — IW4X 直接依赖原始 IW4 CRT。Main::EntryPoint 在自身初始化后显式调用 Game::__tmainCRTStartup()。

CRT_REPLACEMENT = NO — IW4X 不替换 CRT。原始 CRT startup (0x06BAA2F) 被完整调用。

CRT_PATCHING = NO — IW4X 不 patch CRT 本身。它 patch 的是 host binary 中 0x6BAC0F 处的一条指令，将控制流重定向到 Main::EntryPoint，然后 IW4X 初始化完成后调用原始 CRT startup。

MEMORY_RUNTIME = IW4X 使用标准 CRT heap (std::calloc / std::free / _aligned_malloc)，不提供自己的全局 allocator 替换原始 IW4 引擎。Game::Z_VirtualAlloc/Z_Malloc/Z_Free 均为原始引擎函数指针绑定，不是 IW4X 自建内存系统。Utils::Memory 是 IW4X 自身功能的通用 allocator，不影响原始运行时启动。

MEMORY_PATCHING = YES — Utils::Hook 机制通过 VirtualProtect + memcpy + FlushInstructionCache 在启动阶段修改原始 IW4 二进制中的代码和数据。patch 时机为 DllMain 安装入口 hook + Components::Loader::Initialize() 中各 Component 构造函数批量安装。

ENVIRONMENT_SETUP =
IW4X_STARTUP_ENVIRONMENT_REQUIRED = YES
IW4X 在进入原始 CRT 前执行以下操作：
1. SetProcessDEPPolicy(PROCESS_DEP_ENABLE)
2. 设置工作目录（IW4x_INSTALL 环境变量或 exe 所在目录）
3. 设置 DLL 搜索路径（SetDllDirectoryA）
4. Steam::Proxy::RunMod()（平台桥接）
5. 原地修改命令行缓冲区（去除所有引号字符）— lazy 由 Component 触发

COMMAND_LINE_SETUP =
YES — Flags::ParseFlags() 原地修改 GetCommandLineA/W() 返回的缓冲区，去除所有双引号字符。此操作在 Components::Loader::Initialize() 期间由多个 Component 构造函数触发 Flags::HasFlag() 时首次执行。修改后的命令行缓冲区会影响原始 CRT 后续的 argv 解析。

WORKING_DIRECTORY_SETUP =
YES — Utils::SetEnvironment() 在 Main::Initialize() 中调用：
如果环境变量 IW4x_INSTALL 存在，则 SetCurrentDirectoryA() + SetDllDirectoryA()。
否则 SetLegacyEnvironment() 使用 exe 路径 SetCurrentDirectoryW()。

STARTUP_RUNTIME_REQUIREMENTS =
IW4X 必须在原始 CRT startup 运行前完成以下准备工作：
1. 初始化 host binary 的 __security_init_cookie (0x06CA062) — 否则 IW4X 自身使用 /GS 保护的代码在异常处理时可能崩溃
2. 设置工作目录和 DLL 搜索路径
3. 安装所有 Component patch（CEG 禁用、Auth 绕过、QuickPatch 等）
4. 修改命令行缓冲区（引号剥离）
没有这些步骤，IW4X 自身功能无法运行，但原始 CRT 本身仍可启动。

RESTORE_ORIGINAL =
无独立 RESTORE_ORIGINAL 机制。IW4X 不恢复被损坏的原始运行时；它通过 patch 扩展原始二进制。

EXTEND_IW4 =
YES — 主要分类。
- src/DllMain.cpp:18 调用 __security_init_cookie 确保 /GS 安全
- src/DllMain.cpp:25 调用原始 CRT startup
- src/Components/Modules/QuickPatch.cpp:448-840 大量 gameplay/UI/兼容性 patch
- src/Components/Modules/Exception.cpp:358-362 异常处理改进

REPLACE_PLATFORM =
YES — 以下代码替换/绕过原始平台依赖：
- src/Components/Modules/Ceg.cpp:5-63 禁用 CEG (DRM) 检查
- src/Components/Modules/Auth.cpp:612-627 绕过原始认证
- src/DllMain.cpp:8 → Steam::Proxy::RunMod() Steam 平台桥接

IW4X_ONLY =
YES — 以下为 IW4X 自身功能，不影响原始运行时的可启动性：
- src/Utils/Memory.cpp 通用 allocator（calloc/free）
- src/Utils/Hooking.cpp hook 基础设施
- src/Components/Modules/Flags.cpp:22-103 命令行引号剥离
- src/Utils/Utils.cpp:151-180 工作目录/DLL 路径设置
- src/Components/Loader.cpp:90-197 Component 注册

UNKNOWN =
- 0x6BAC0F 处被 patch 前的原始指令内容（host binary 不在本仓库）
- 0x06BAA2F 的二进制级身份验证（仅源码符号绑定）
- Steam::Proxy::RunMod() 内部是否设置环境变量的完整影响

CORE_FINDING =
IW4X 不替换也不 patch CRT。它通过 DLL 注入到原始 IW4 进程，
在 DllMain 中 patch 0x6BAC0F 处的指令以劫持控制流到 Main::EntryPoint。
Main::EntryPoint 完成以下操作后调用原始 CRT startup (0x06BAA2F)：
(1) 初始化安全 cookie，(2) 设置环境，(3) 安装所有 patch。
抽象模型成立：
Original IW4 binary + IW4X bootstrap layer → original CRT → runtime。
该机制位于 src/DllMain.cpp 整个文件。

CODOL_RELEVANCE =
此差分确认 IW4X 的 bootstrap 模式是"DLL 注入 + entry hook + patch + delegate to original CRT"。
如果 CODOL 需要类似机制，可以复用此模式，但地址和符号需要针对 CODOL 二进制重新映射。
IW4X 不需要自建 CRT 或 allocator；它依赖原始 CRT。

NEXT_STEP =
ICH-002-B 应分析 IW4X 引擎层（renderer / filesystem / network）与原始 IW4 的接口，
特别是 Component 构造函数中安装的 hook 如何在原始 CRT startup 后生效。
---

## 机制溯源表

### 1. 入口劫持

```
source file:        src/DllMain.cpp
symbol/function:    DllMain
line number:        51
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Utils::Hook(0x6BAC0F, Main::EntryPoint, HOOK_JUMP).install()->quick();
                    将 host binary 中 0x6BAC0F 处的 5 字节替换为 E9 jmp 到 Main::EntryPoint。
```

### 2. Security cookie 初始化

```
source file:        src/DllMain.cpp
symbol/function:    Main::EntryPoint
line number:        18
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Game::__security_init_cookie();
                    绑定地址 src/Game/Functions.cpp:6 = 0x06CA062。
                    确保 host binary 的 /GS cookie 在 IW4X 使用异常处理前初始化。
                    历史证据: git commit 64cbcef6 将其从 DllMain 移入 EntryPoint，
                    注释明确说明 "/GS security cookie must be initialized before any
                    exception-handling constructs are registered in the current module."
```

### 3. CRT startup 调用

```
source file:        src/DllMain.cpp
symbol/function:    Main::EntryPoint
line number:        25
classification:     RESTORE_ORIGINAL
confidence:         HIGH
mechanism:          return Game::__tmainCRTStartup();
                    绑定地址 src/Game/Functions.cpp:7 = 0x06BAA2F。
                    直接调用原始 CRT startup，不修改其行为。
                    历史证据: 旧代码 (pre-64cbcef6) 使用 asm push 6BAA2Fh; push 6CA062h; retn。
```

### 4. 工作目录 / DLL 搜索路径

```
source file:        src/Utils/Utils.cpp
symbol/function:    Utils::SetEnvironment
line number:        166-180
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          _dupenv_s("IW4x_INSTALL") → SetCurrentDirectoryA + SetDllDirectoryA
                    fallback: SetLegacyEnvironment (line 151-160) → SetCurrentDirectoryW(exe_dir)
                    被 Main::Initialize (src/DllMain.cpp:7) 在原始 CRT 前调用。
```

### 5. DEP 策略

```
source file:        src/DllMain.cpp
symbol/function:    DllMain
line number:        34
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          SetProcessDEPPolicy(PROCESS_DEP_ENABLE);
                    进程级设置，在 DllMain 的 DLL_PROCESS_ATTACH 时执行。
```

### 6. 命令行引号剥离

```
source file:        src/Components/Modules/Flags.cpp
symbol/function:    Flags::ParseFlags
line number:        22-103
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          GetCommandLineA/W() 返回的缓冲区原地去除所有 '"' 字符。
                    触发时机: Flags::HasFlag() 首次被 Component 构造函数调用时 lazy init。
                    Loader::Initialize() 期间多个组件触发。
                    修改后的缓冲区影响原始 CRT 的 argv 解析。
```

### 7. Hook patch 基础设施

```
source file:        src/Utils/Hooking.cpp
symbol/function:    Hook::install / Hook::Nop / Hook::SetString
line number:        142-167 / 204-213 / 220-243
classification:     IW4X_ONLY (infrastructure) / EXTEND_IW4 (usage)
confidence:         HIGH
mechanism:          VirtualProtect → memcpy(save original) → write E9/nop/data →
                    VirtualProtect(restore) → FlushInstructionCache
```

### 8. CEG 保护禁用

```
source file:        src/Components/Modules/Ceg.cpp
symbol/function:    Ceg::Ceg (constructor)
line number:        5-63
classification:     REPLACE_PLATFORM
confidence:         HIGH
mechanism:          签名扫描 + 固定地址 patch，将 CEG 检查函数替换为 retn(1) / nop。
                    在 Components::Loader::Initialize() → Register(new Ceg()) 时构造。
```

### 9. Auth 认证绕过

```
source file:        src/Components/Modules/Auth.cpp
symbol/function:    Auth::Auth (constructor)
line number:        612-627
classification:     REPLACE_PLATFORM
confidence:         HIGH
mechanism:          多个 hook 绕过原始连接认证流程。
```

### 10. QuickPatch gameplay/UI patch 批量安装

```
source file:        src/Components/Modules/QuickPatch.cpp
symbol/function:    QuickPatch::QuickPatch (constructor)
line number:        448-840
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          50+ 处 Hook/Set/Nop，修改 dvar、字符串、渲染、gameplay 逻辑。
                    在 Components::Loader::Initialize() → Register(new QuickPatch()) 时构造。
```

### 11. Component 批量注册

```
source file:        src/Components/Loader.cpp
symbol/function:    Loader::Initialize
line number:        90-197
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          Register(new ...) 逐个构造 Component。
                    每个 Component 构造函数在其自身范围内安装 patch。
                    被 Main::Initialize (src/DllMain.cpp:10) 在原始 CRT 前调用。
```

### 12. Steam 平台桥接

```
source file:        src/DllMain.cpp
symbol/function:    Main::Initialize
line number:        8
classification:     REPLACE_PLATFORM
confidence:         MEDIUM
mechanism:          Steam::Proxy::RunMod();
                    具体行为未完全展开（不在本次分析范围）。
```

### 13. 原始引擎 allocator 函数指针绑定（非替换）

```
source file:        src/Game/Zone.cpp
symbol/function:    Game::Z_VirtualAlloc / Game::Z_Malloc / Game::Z_Free
line number:        5-7
classification:     EXTEND_IW4
confidence:         HIGH
mechanism:          Z_VirtualAlloc_t(0x4CFBA0) / Z_Malloc_t(0x4F3680) / Z_Free_t(0x4291A0)
                    这些是原始引擎函数的指针绑定，供 IW4X 调用原始引擎的内存管理。
                    不替换、不包装、不 hook。
```

### 14. IW4X 自建虚拟内存 wrapper（非启动级）

```
source file:        src/Game/Zone.cpp
symbol/function:    Z_VirtualReserve / Z_VirtualCommit / Z_VirtualDecommit / Z_VirtualFree
line number:        14-73
classification:     IW4X_ONLY
confidence:         HIGH
mechanism:          Win32 VirtualAlloc/VirtualFree 封装。
                    消费者: src/Game/Engine/Hunk.cpp:7-41 (Hunk user),
                           src/Components/Modules/GSC/ScriptError.cpp:551-585 (script parser),
                           src/Components/Modules/RawFiles.cpp:43,60 (menu buffer)。
                    均为 IW4X 功能级使用，不是启动必需机制。
```

---

## 控制流

```
IW4X
  ↓
DllMain (DLL_PROCESS_ATTACH)
  → SetProcessDEPPolicy(PROCESS_DEP_ENABLE)          [src/DllMain.cpp:34]
  → binary identity check (0x6F9358)                  [src/DllMain.cpp:37-49]
  → Hook(0x6BAC0F → Main::EntryPoint) install        [src/DllMain.cpp:51]
  ↓
Main::EntryPoint
  → Game::__security_init_cookie()                   [src/DllMain.cpp:18]
      binding: 0x06CA062                              [src/Game/Functions.cpp:6]
  → Main::Initialize()
      → std::srand(...)                               [src/DllMain.cpp:5]
      → Utils::SetEnvironment()                       [src/DllMain.cpp:7]
          → IW4x_INSTALL or exe dir                   [src/Utils/Utils.cpp:166-180]
          → SetCurrentDirectory + SetDllDirectory
      → Steam::Proxy::RunMod()                        [src/DllMain.cpp:8]
      → Utils::Cryptography::Initialize()             [src/DllMain.cpp:9]
      → Components::Loader::Initialize()              [src/DllMain.cpp:10]
          → Register(new Ceg())                       [src/Components/Loader.cpp:121]
              → CEG patches                           [src/Components/Modules/Ceg.cpp:5-63]
          → Register(new Auth())                      [src/Components/Loader.cpp:102]
              → Auth patches                          [src/Components/Modules/Auth.cpp:612-627]
          → Register(new QuickPatch())                [src/Components/Loader.cpp:160]
              → QuickPatch patches                    [src/Components/Modules/QuickPatch.cpp:448-840]
          → Register(60+ other Components)            [src/Components/Loader.cpp:90-197]
              → 各自构造函数安装 patch
          → Flags::ParseFlags() lazy triggered        [src/Components/Modules/Flags.cpp:22-103]
              → GetCommandLineA/W 缓冲区原地去引号
  → return Game::__tmainCRTStartup()                  [src/DllMain.cpp:25]
      binding: 0x06BAA2F                              [src/Game/Functions.cpp:7]
  ↓
Original IW4 Runtime
  → CRT init (argv from modified command line buffer)
  → main() → engine init → IW4X patches already installed and active
```

---

## 分析范围声明

- 本次分析仅针对 IW4X Client commit `0699a7e5716ded53bcfa6748bcb89a535f8f39f0` 的源码。
- Host IW4 binary 不在本仓库中，0x6BAC0F 处被 patch 前的原始指令无法确认。
- 0x06BAA2F 的二进制级身份（是否确实为 `__tmainCRTStartup`）仅依赖源码中的符号命名和历史提交注释。
- Steam::Proxy::RunMod() 内部逻辑未完全展开，因其属于平台层，超出本 ICH 的 CRT/Entry/Memory 范围。
- 未运行任何程序、未动态调试、未编译、未修改任何源码文件。
