# 14 — B：项目构建需求（编译器 / 目标架构 / 运行库 / 依赖 / ABI）

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-001`（为 `EARLY-NATIVE-TAP-BUILD-001` 准备可复现构建环境）
> 边界：**只读**。本文件仅从项目内文件与既有二进制/目标文件中提取“项目声明了什么、既有产物由什么构建”，**不编译、不链接、不应用补丁、不运行任何脚本或游戏**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。
> 依据文件以只读的 `13_NATIVE_TAP_BUILD_001\experiment_copy`（与原始树 3726 文件逐一致）为准，并在需要时对照原始树 `.github\workflows\build.yml`。

## B.0 结论先行

| 需求维度 | 项目要求 | 依据 | 状态 |
|---|---|---|---|
| 构建系统 | GNU Make（`makefile`，非 CMake/非 xmake） | `makefile:1-10` | **CONFIRMED** |
| 编译器 | GCC 驱动：`CC=gcc`、`CPP=g++`（MinGW-w64） | `makefile:51-52`；`README.md` | **CONFIRMED** |
| 目标架构 | **32 位（i686 / PE32）强制**，全路径 `-m32` | `makefile:55,65` | **CONFIRMED** |
| C/C++ 标准 | `gnu11` / `gnu++11`（依赖 GCC 扩展） | `makefile:56-57` | **CONFIRMED** |
| 汇编器 | **NASM**，`-f win -dWin32 --prefix _`（win32 COFF） | `makefile:111,119` | **CONFIRMED** |
| 资源编译器 | **Windres**（`-O coff` 生成 `.res`） | `makefile:131,265-266` | **CONFIRMED** |
| 运行库 / CRT | **静态链接** `-static -static-libgcc`，依赖 mingw-w64 msvcrt | `makefile:65` | **CONFIRMED** |
| 异常 / 线程模型 | **posix 线程 + dwarf 展开**（`i686-posix-dwarf-rev0`） | 既有二进制/`.o` 指纹 | **CONFIRMED（指纹）** |
| 编译器版本 | 既有产物与 CI 均锁定 **GCC 8.1.0** | 二进制内嵌路径 + `.github\workflows\build.yml` | **CONFIRMED** |
| 第三方依赖 | mbedTLS 2.16.6、vendored tomcrypt、vendored zlib；`lib\*.a` 为 i386 COFF | `src\mbedtls\version.h`；`src\tomcrypt\makefile`；`lib\` | **CONFIRMED** |
| POSIX 外壳依赖 | makefile 需要 POSIX shell + coreutils（`realpath`/`command -v`/`grep`/`cut`/`timeout`）+ `python3` | `makefile:107,131,371,625,630,633` | **CONFIRMED** |
| 本机是否满足以上需求 | **否**，缺少 i686 MinGW-w64 工具链 | 见 `14_A` | **INSTRUMENTATION_BLOCKED** |

**一句话：** 本项目需要的是 **一整套 `i686-w64-mingw32` + posix 线程 + dwarf 展开 + msvcrt + NASM(win32) + Windres + GNU Make(POSIX shell)** 环境，且既有产物与 CI 把版本锁在 **GCC 8.1.0**；不是“任意能编 C 的编译器”即可满足。

## B.1 构建系统与入口

| 项 | 值 | 依据 |
|---|---|---|
| 构建系统 | GNU Make（`makefile`，50,570 字节） | `makefile` 全文；`14_A A.4` |
| 默认目标名 | `bin/codol_dedrun.exe`（`TARGETNAME=codol_dedrun`） | `makefile:16-23` |
| 安全仅编译目标 | `objects`（编译全部对象、**不链接**） | `makefile:202-204` |
| Windows 驱动脚本 | `tools\BUILD-CODOL.ps1`（硬编码 `C:\msys64\usr\bin\make.exe`） | `tools\BUILD-CODOL.ps1` |
| CI（原始树） | `.github\workflows\build.yml`（Linux + Windows 两个作业） | 原始树 `.github\workflows\build.yml` |
| 版本号 | `SYS_COMMONVERSION 21.2` | `src\version\version.c` |

**CI Windows 作业的关键固定（原始树 `.github\workflows\build.yml`）：**

- 下载并解压 `https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` 到 `C:\mingw32`。
- 使用 `ilammy/setup-nasm@v1` 安装 NASM。
- 构建前 `$env:Path = "C:\mingw32\bin;" + $path`，随后执行 `mingw32-make`。
- 发布产物名 `bin/cod4x18_dedrun.exe`（上游名；本项目 `TARGETNAME` 为 `codol_dedrun`）。

**CI Linux 作业：** `g++-multilib gcc-multilib` + `nasm:i386`，执行 `make`。此路径与本机无关（本机无 WSL 发行版，见 `14_A`）。

## B.2 编译器、目标架构与语言标准

| 需求 | 值 | 依据 |
|---|---|---|
| C 编译器变量 | `CC=gcc` | `makefile:51` |
| C++ 编译器变量 | `CPP=g++` | `makefile:52` |
| 公共编译标志 | `-m32 -msse2 -mfpmath=sse -Wall -fno-omit-frame-pointer -fmax-errors=15 -MMD -MP` | `makefile:55` |
| C 标准 | `-std=gnu11` | `makefile:56` |
| C++ 标准 | `-std=gnu++11` | `makefile:57` |
| 优化/调试 | 非 DEBUG：`-fno-pie -O1 -DNDEBUG` | `makefile:62` |
| Windows 目标宏 | `WINVER=0x501`（Windows XP / Server 2003 目标） | `makefile:53` |
| 应用宏 | `IW4OL_UPDATE`、`BUILD_NUMBER/BRANCH/REVISION`、`CODOL_SERVER` | `makefile:70-73` |

**32 位强制性证据（不止 `-m32`）：**

- 链接标志同样带 `-m32`（`makefile:65`）。
- `src\q_platform.h` 以 `_M_IX86 || __i386__` 决定 `id386`（即 32 位 x86 专用路径）。
- 资源脚本 `src\win32\win_cod4.rc` 与 NASM `-f win` 均面向 win32。
- 既有 `bin\codol_dedrun.exe`：`Machine=0x014C (i386)`、`OptMagic=0x010B (PE32)`、`Subsystem=2 (GUI)`。

**GCC 扩展依赖（非严格 ISO C）：** 源码扫描命中约 133 处 `__attribute__((...))`、`__asm__`、`__builtin_*`、`typeof` 等 GCC 扩展。这排除了“用 MSVC 直接替换”的可能，并提高了对具体 GCC 版本的敏感度。

## B.3 汇编器与资源编译器

| 工具 | 要求 | 依据 |
|---|---|---|
| NASM | `NASM=nasm`，`NASMFLAGS=-f win -dWin32 --prefix _`（win32 COFF，符号下划线前缀） | `makefile:111,119,320-322` |
| 汇编源规模 | `src` 下 **118** 个 `.asm`（含 `%include` 本地 `.inc`） | `src\asmsource\*.asm` |
| Windres | `WINDRES?` 优先 `i686-w64-mingw32-windres`，否则回退 `windres` | `makefile:131` |
| 资源规则 | `$(WINDRES) -I src/win32 -i win_cod4.rc -O coff -o $(RESOURCE_FILE)` | `makefile:265-266` |
| 插件接口（可选） | `dlltool` + `pexports`（`.def` 为空时跳过，不影响主可执行文件） | `makefile:350-372` |

**关键约束：** makefile 明确注释——`i686-w64-mingw32-windres` 在纯 msys2 mingw32 安装中可能不存在，此时回退到 `windres`；因此**必须把 `mingw32\bin` 放在 `usr\bin` 之前**，否则 `windres` 会解析到 `usr\bin` 下面向 x86_64 的那一个，导致 `.res` 目标架构错误。

## B.4 C/C++ 运行库、ABI 与异常/线程模型

| 维度 | 要求 | 依据 | 风险 |
|---|---|---|---|
| 链接方式 | `-static -static-libgcc`（不依赖 mingw 运行 DLL） | `makefile:65` | 中：静态 CRT 必须与编译器版本配套 |
| CRT | mingw-w64 **msvcrt**（非 UCRT） | 二进制含 `mingw_helpers.c`、`mingw_getsp.S`、`___mingw_*` 等 mingw-w64 CRT 符号 | 中：UCRT/msvcrt 混用会引入不兼容 |
| 异常展开模型 | **dwarf**（`i686-posix-dwarf-rev0`） | 二进制与 597 个 `.o` 的 GCC 注释 | 高：sjlj/seh 变体将改变 libgcc/异常 ABI |
| 线程模型 | **posix**（同上 GCC 标识） | 同上 | 高：win32 线程模型变体会改变运行库行为 |
| 入口/子系统 | `-mwindows`（GUI 子系统，无控制台窗口） | `makefile:65` | 低 |
| 安全/地址属性 | `--nxcompat --large-address-aware --stack,0x800000` | `makefile:65` | 低 |
| C++ 运行库 | 链接 `stdc++`（静态） | `makefile:66` | 中：C++ ABI 与 libstdc++ 版本绑定 |

**结论：** 本项目对 **i686 + posix + dwarf + msvcrt** 这一组合有**强约束**。任何“线程/异常模型不同”或“CRT 不同”的 i686 工具链都不能默认视为兼容；它们会改变 libgcc 展开、异常传播与运行库符号，属于**未验证的 ABI 风险**。

## B.5 第三方依赖与锁定清单

| 依赖 | 版本/形态 | 依据 |
|---|---|---|
| mbedTLS | **2.16.6**（vendored 源码 + 预置静态库） | `src\mbedtls\version.h`（`MBEDTLS_VERSION_STRING "2.16.6"`） |
| tomcrypt | vendored 源码，`CFLAGS=-m32 -Wall -Os -s -I. -DLTC_NO_ROLC -DLTC_SOURCE` | `src\tomcrypt\makefile` |
| zlib | vendored 源码（`src\zlib`） | `makefile` 规则 |
| 预置静态库 | `lib\libmbedcrypto.a`、`lib\libmbedtls.a`、`lib\libmbedx509.a`、`lib\libtomcrypt.a`（**i386 COFF**） | `lib\libs.txt`；`lib\` |
| 运行库链接清单 | `tomcrypt mbedtls mbedcrypto mbedx509 ws2_32 wsock32 iphlpapi gdi32 winmm crypt32 stdc++` | `makefile:66` |
| 工具链锁定清单 | CI 固定 `i686-8.1.0-release-posix-dwarf-rt_v6-rev0` + NASM | `.github\workflows\build.yml` |

**切换工具链的陷阱（项目已明确记录）：** `docs\CODOL_PORT.md` 指出第三方 makefile 把对象/归档放在共享位置，**在 Linux 与 Windows 工具链之间切换时必须用 `-B` 强制重建**，因为引擎对象目录并不能隔离第三方库的格式（i386 COFF vs ELF）。

## B.6 既有二进制/目标文件反推的实际工具链身份

| 证据 | 值 |
|---|---|
| GCC 注释（`bin\codol_dedrun.exe` 与 597 个 `obj\codol\*.o`） | `GCC: (i686-posix-dwarf-rev0, Built by MinGW-W64 project) 8.1.0` |
| 二进制内嵌原始构建路径 | `C:\mingw810\i686-810-posix-dwarf-rt_v6-rev0\...`、`C:/mingw810/src/gcc-8.1.0/...` |
| PE 特征 | `Machine=0x014C (i386)`、`OptMagic=0x010B (PE32)`、`Subsystem=2 (GUI)`、8,469,493 字节 |
| 中间产物 | `obj\codol`：597 `.o`、484 `.d`、1 `win_codol.res`，时间戳 2026-10-04 17:00–17:03 |
| 实验副本第三方对象 | `src\mbedtls\*.o`、`src\tomcrypt\**\*.o` 为 i386 COFF（文件头 `4c 01`） |

这些证据**只能证明既有构建线与工具链身份**，不构成本轮的可构建环境，也不代表可复现构建已获得（`obj` 被排除在实验副本之外，原始树 Git 无 commit）。

## B.7 POSIX 外壳与辅助工具依赖

makefile 在 Windows 目标下仍依赖 POSIX 语义（`ifeq ($(OS),Windows_NT)` 分支）：

| 依赖 | 用途 | 依据 |
|---|---|---|
| POSIX shell（`sh`） | makefile 的 `$(shell ...)`、`if [ -s ... ]; then ... fi` 等 | `makefile:355-359,371-372` |
| `realpath` | `TEST_LIB_TARGET_REL=$(shell realpath -m --relative-to=...)` | `makefile:107` |
| `command -v` | 探测 `i686-w64-mingw32-windres` / `pexports` | `makefile:131,371` |
| `grep` / `cut` | 版本号提取 | `makefile:33`（Linux 分支）、CI |
| `timeout` | `timeout 15s ./$(OBJ_DIR)/test_...` | `makefile:625` |
| `python3` | 若干测试目标 | `makefile:630,633` |

**含义：** Windows 原生构建需要 MSYS2 的 `usr\bin`（提供 `make`、`sh`、coreutils）**以及** `mingw32\bin`（提供 i686 工具链），且两者顺序有讲究（见 B.3）。纯 PowerShell 或纯 Git Bash 环境不足以覆盖全部依赖。

## B.8 构建产物与实验约束（与本阶段无关但影响验证计划）

| 项 | 值 | 依据 |
|---|---|---|
| 默认产物 | `bin\codol_dedrun.exe` | `makefile:259-262` |
| 运行目标名 | `bin\codol_dedrun_next.exe`（由 `START-CODOL-SERVER.cmd` 启动） | `13_A A.1` |
| 链接失败风险 | `ld` 在链接失败时会删除输出；`BUILD-CODOL.ps1` 默认目标可能破坏 `bin\codol_dedrun.exe` | `tools\BUILD-CODOL.ps1` |
| 安全仅编译 | `make objects` / `BUILD-CODOL.ps1 -ObjectsOnly`（不链接、不触碰部署二进制） | `makefile:202-204`；脚本 |

## B.9 阶段 B 裁决

- 项目构建需求：**CONFIRMED（静态）**。
- 32 位 ABI / posix+dwarf+msvcrt 约束：**CONFIRMED**。
- 目标工具链身份：**CONFIRMED（MinGW-w64 GCC 8.1.0 i686-posix-dwarf，rt_v6）**。
- 本机对以上需求的满足程度：**INSTRUMENTATION_BLOCKED**（详见 `14_C`、`14_E`）。

> 本文件为**需求提取**，非编译验证结果；未编译、未链接、未应用补丁、未运行任何程序。