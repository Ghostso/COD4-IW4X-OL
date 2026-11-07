# 14 — A：只读环境盘点

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-001`（为 `EARLY-NATIVE-TAP-BUILD-001` 准备可复现构建环境）
> 边界：**只读**。本轮未安装/升级任何工具链，未修改 PATH/注册表/全局设置，未修改源码、实验副本、候选补丁或大厅基线，未编译、未应用补丁、未运行游戏/服务端/launcher，未执行任何 `.cmd`/`.bat`/构建脚本。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## A.0 结论先行

| 问题 | 结论 | 状态 |
|---|---|---|
| 主机操作系统 | Windows 10 专业版，10.0.19045（22H2），**x64** 体系结构 | **CONFIRMED** |
| PATH 中可见的编译器/汇编器/资源编译器/构建工具 | `make`/`gcc`/`g++`/`clang`/`cl`/`windres`/`nasm`/`yasm`/`ar`/`ld`/`cmake`/`ninja` **均未找到** | **CONFIRMED（环境检查）** |
| 常见 MSYS2/MinGW-w64 安装位置 | 全部**不存在**（含 `C:\msys64`、`C:\MinGW`、`C:\Program Files\mingw-w64`、`C:\Program Files\LLVM` 等） | **CONFIRMED（环境检查）** |
| Visual Studio Build Tools | **存在**：VS Build Tools 2022 17.14.37710.0，位于 `E:\BuildTools`，含 MSVC 14.44.35207（x86/x64）与 Windows Kits 10 | **CONFIRMED** |
| WSL | `wsl.exe` 存在，但**未安装任何发行版**（`Lxss` 注册表项为空） | **CONFIRMED（环境检查）** |
| 项目声明的编译器/目标架构 | GNU Make + `gcc`/`g++` + **`-m32`** + NASM + Windres；目标 `bin/codol_dedrun.exe`（PE32 i386） | **CONFIRMED（静态）** |
| 已交付二进制的实际构建工具链 | MinGW-w64 **GCC 8.1.0（i686-posix-dwarf-rev0, rt_v6）** | **CONFIRMED（二进制/目标文件指纹）** |
| 该精确工具链当前是否在本机 | **否**，原始 `C:\mingw810` 与 CI 用的 `C:\mingw32` 均不存在 | **CONFIRMED（环境检查）** |
| 是否存在来源明确、可复现的锁定工具链依据 | **是**：CI 工作流固定 `i686-8.1.0-release-posix-dwarf-rt_v6-rev0` | **CONFIRMED** |
| 是否已获得可构建环境 | **否** | **INSTRUMENTATION_BLOCKED** |

## A.1 Windows 版本与体系结构

| 项 | 值 |
|---|---|
| Caption | Microsoft Windows 10 专业版 |
| Version | 10.0.19045 |
| BuildNumber | 19045 |
| OSArchitecture | 64 位 |
| SystemType | x64-based PC |
| `PROCESSOR_ARCHITECTURE` | AMD64 |
| `PROCESSOR_ARCHITEW6432` | （未设置） |
| Is64BitOperatingSystem / Is64BitProcess | True / True |
| PowerShell | 7.6.5 |

说明：主机是 64 位 Windows，**默认不提供任何 32 位交叉编译能力**；`-m32` 目标必须有 32 位工具链与 32 位运行库显式提供。

## A.2 PATH 中可见的编译器 / 汇编器 / 资源编译器 / 构建工具

查询方式：`Get-Command <name>`（只读；未执行任何编译器）。

| 工具 | 结果 |
|---|---|
| `make` | NOT_FOUND |
| `mingw32-make` | NOT_FOUND |
| `gmake` | NOT_FOUND |
| `gcc` | NOT_FOUND |
| `g++` | NOT_FOUND |
| `cc` | 解析到 `C:\Users\Z7-CT5N1\.claude-profiles\cc.bat` —— 这是 Claude Code 配置档切换脚本，**不是 C 编译器**，不计入工具链 |
| `clang` / `clang++` | NOT_FOUND |
| `cl`（MSVC） | NOT_FOUND（未进入 PATH；`E:\BuildTools` 下存在，见 A.3） |
| `windres` | NOT_FOUND |
| `nasm` / `yasm` | NOT_FOUND |
| `ar` / `ld` | NOT_FOUND |
| `cmake` / `ninja` / `pkg-config` | NOT_FOUND |
| `rustc` / `tcc` | NOT_FOUND |
| `git` | `C:\Program Files\Git\cmd\git.exe`（2.55.0.windows.4）——非编译器 |
| `python` | `…\Python311\python.exe`（3.11.9）——仅用于测试脚本，非 C 工具链 |
| `xmake` | `D:\Program Files\xmake\xmake\xmake.exe`（v3.1.1）——通用构建工具，**不是 GNU Make**，且本机无可用 i686 工具链 |

PATH 中共 37 个条目（总长 2167 字符），无任何 MinGW/MSYS2/GCC/LLVM 目录。结论：**当前 PATH 不具备构建本项目所需的任何 32 位 C/C++ 工具链组件。**

## A.3 常见 MSYS2 / MinGW-w64 / Visual Studio Build Tools 安装位置

| 路径 | 是否存在 |
|---|---|
| `C:\msys64` | 否 |
| `C:\msys32` | 否 |
| `C:\MinGW` | 否 |
| `C:\mingw32` / `C:\mingw64` | 否 |
| `D:\msys64` / `D:\msys32` | 否 |
| `D:\MinGW` / `D:\mingw32` / `D:\mingw64` | 否 |
| `C:\Program Files\mingw-w64` | 否 |
| `C:\Program Files (x86)\mingw-w64` | 否 |
| `C:\Program Files\LLVM` | 否 |
| `C:\mingw810`（二进制中嵌入的原始路径） | 否 |
| `C:\Program Files (x86)\Microsoft Visual Studio` | 是（仅安装器） |
| `C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe` | 是 |
| `E:\BuildTools`（VS Build Tools 2022） | **是** |
| `C:\Program Files (x86)\Windows Kits\10` | 是 |

Visual Studio Build Tools 详情（`vswhere` 只读查询）：

- 产品：Visual Studio 生成工具 2022，`installationVersion` 17.14.37710.0，`installationPath = E:\BuildTools`，`isComplete = true`。
- MSVC 工具集：`E:\BuildTools\VC\Tools\MSVC\14.44.35207`，含 `bin\Hostx64\x64`、`bin\Hostx64\x86`、`bin\Hostx86\x64`、`bin\Hostx86\x86` 下的 `cl.exe`（**有 32 位目标能力**，但属 MSVC ABI，见 14_C）。
- 另有 `E:\BuildTools\VC\vcpkg`、`E:\BuildTools\VC\Tools\Llvm`（LLVM 组件目录，**未发现可用 i686 MinGW 工具链**）。
- **未发现** NASM、`windres` 或任何 MinGW `gcc`。

全盘（C/D/E/F/G）深度 2–3 扫描 `gcc.exe`/`make.exe`/`mingw32-make.exe`/`nasm.exe`/`windres.exe`/`i686-w64-mingw32-gcc.exe`：**零命中**（仅命中的是 VS Build Tools 目录本身，其内无这些可执行文件）。注册表卸载项中亦无 MinGW/MSYS2/Cygwin/NASM/TDM/winlibs/w64devkit 记录。

WSL：`C:\Windows\system32\wsl.exe` 存在，但 `wsl --list --quiet` 返回用法/错误信息，`HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss` 为空 —— **未安装任何 WSL 发行版**，因此 `docs/CODOL_PORT.md` 所述的 WSL/Linux 交叉构建路径当前也不可用。

工作区自带 LLVM（`D:\BaiduNetdiskDownload\使命召唤OL\toolchain\`）：

- `llvm18\clang+llvm-18.1.8-x86_64-pc-windows-msvc\bin` 是**不完整解压**：仅 47 个文件、4 个可执行（`amdgpu-arch.exe`、`bugpoint.exe`、`c-index-test.exe`、`clang++.exe`）。**缺少** `clang.exe` 驱动、`lld`、`llvm-ar`、`llvm-rc`、`llvm-dlltool` 等；无 libclang 头文件目录。
- 目标三元组是 `x86_64-pc-windows-msvc`，**不是 i686-w64-mingw32**，且不带 MinGW sysroot。
- 结论：**NOT_OBSERVED（不可用）**，不能作为本项目工具链。

## A.4 项目 README / Makefile / 构建脚本 / CI 声明的编译器、目标架构、运行库与依赖

依据文件（均在只读的 `13_NATIVE_TAP_BUILD_001\experiment_copy`，与原始树 3726 文件逐一致）：

| 文件 | SHA-256 |
|---|---|
| `makefile` | `FEFF456D713ED926A48B4DACE6B0DD8B81F30B757F2B263975E314369A9C8703` |
| `README.md` | `7873FBA3A5B6733FD213BB3AB41D896FA5A61BCE0BDE5B04D5D3DA92F7D3EC63` |
| `docs\CODOL_PORT.md` | `26F083C3F5C150FA0BF2513E81AFD5ABA5AEF724BDE3050A96D7F62E066846FF` |
| `tools\BUILD-CODOL.ps1` | `6EAB7B2759A9A2A276AF708F28715753EB503ED2DA4C997CB5B90E5E7FC79BB4` |
| `src\win32\win_cod4.rc` | `A4C70D39B3D653092D325F680AF8AEC39CD7675708F5429824755A306E6C86F8` |
| `.github\workflows\build.yml`（原始树，见 A.6） | （本轮只读；内容见 A.6） |

**README.md 声明：**

- `make` 构建 `bin/codol_dedrun`（Windows 上为 `.exe`）。
- Linux 前置：NASM、gcc、make（**32 位工具链**）。
- Windows 前置：msys2（**mingw32 工具链、NASM、make**），运行 `tools/BUILD-CODOL.ps1`。

**makefile 声明（行号为该文件内行号）：**

| 行 | 事实 |
|---|---|
| `:16-23` | `GAME ?= codol`；`TARGETNAME=codol_dedrun`（`iw4ol` 时为 `iw4ol_dedrun`） |
| `:51-52` | `CC=gcc`；`CPP=g++` |
| `:53` | `WIN_DEFINES=WINVER=0x501`（**Windows XP 目标**） |
| `:55` | `COMMON_FLAGS=-m32 -msse2 -mfpmath=sse -Wall -fno-omit-frame-pointer -fmax-errors=15 -MMD -MP`（**32 位目标**） |
| `:56-57` | `-std=gnu11` / `-std=gnu++11` |
| `:62` | 非 DEBUG：`-fno-pie -O1 -DNDEBUG` |
| `:65` | 链接：`-m32 -g -Wl,--nxcompat,--large-address-aware,--stack,0x800000 -mwindows -static-libgcc -static -lm` |
| `:66` | 运行库：`tomcrypt mbedtls mbedcrypto mbedx509 ws2_32 wsock32 iphlpapi gdi32 winmm crypt32 stdc++` |
| `:71-73` | `GAME=codol` 追加 `-DCODOL_SERVER` |
| `:111` | `NASM=nasm` |
| `:119` | `NASMFLAGS=-f win -dWin32 --prefix _`（**win32 COFF 语法、C 符号下划线前缀**） |
| `:131` | `WINDRES?=` 优先 `i686-w64-mingw32-windres`，否则回退 `windres` |
| `:203` | `objects` 目标（仅编译不链接，安全） |
| `:259-266` | 链接目标 `$(BIN_DIR)/$(TARGETNAME).exe`；`.res` 由 `$(WINDRES) -I src/win32 -i win_cod4.rc -O coff -o $@` 生成 |
| `:350-370` | 插件接口用 `dlltool`/`pexports`（可选，不影响主可执行文件） |
| `:212-214` | `GAME=codol` 时 `release` 目标被禁用（`$(error ...)`） |

**tools\BUILD-CODOL.ps1 声明：**

- 硬编码 `$make = 'C:\msys64\usr\bin\make.exe'`；不存在则 `Write-Error` 退出。
- `$env:PATH = 'C:\msys64\mingw32\bin;C:\msys64\usr\bin;' + $env:PATH`（**mingw32/bin 必须在 usr/bin 之前**，因为两者都提供 `windres`，只有 mingw32 那个面向 i686）。
- 默认链接 `bin\codol_dedrun.exe`；`-ObjectsOnly` 走 `make objects`（不链接）。
- 脚本记录了两个环境陷阱：gcc 默认临时目录 `C:\WINDOWS` 不可写；msys2 必须在 PATH 中否则 `make` 报 `echo: No such file or directory`。

**docs\CODOL_PORT.md 声明（“Build and verify”一节）：**

- 服务器是 CoD4x 分支（基线 commit `def475a7c3681171698a6bf365bc2a3ae9747fe7`）。
- Linux/WSL 前置：`nasm`、`make`、`gcc-multilib`、`g++-multilib`。
- Windows 可执行文件“**was cross-compiled with MinGW-w64**”，命令：
  `make -B -j6 OS=Windows_NT CC=i686-w64-mingw32-gcc CPP=i686-w64-mingw32-g++ AR=i686-w64-mingw32-ar OBJ_DIR=obj/codol-win32 bin/codol_dedrun.exe`
- 原生 Windows：“use the upstream 32-bit MinGW/NASM prerequisites and `mingw32-make bin/codol_dedrun.exe`; **this native tool invocation has not been tested here**”。
- 切换 Linux/Windows 工具链时必须 `-B`，因为第三方库的 `.o`/`.a` 放在共享位置。
- 已产出：`bin/codol_dedrun`（**32 位 Linux ELF**）与 `bin/codol_dedrun.exe`（**32 位 Windows PE，MinGW-w64**）。

**CI（原始树 `.github\workflows\build.yml`，本轮只读）：**

- `windows` 作业在 `windows-latest` 上：下载并解压 `https://downloads.sourceforge.net/mingw-w64/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` 到 `C:\mingw32`；`ilammy/setup-nasm@v1` 获取 NASM；`$env:Path = "C:\mingw32\bin;" + $path`；执行 `mingw32-make`。
- `linux` 作业在 `ubuntu-22.04` 上：`g++-multilib gcc-multilib` + `nasm:i386`，执行 `make`。

**第三方依赖（项目内声明）：**

| 依赖 | 版本/来源 | 构建方式 |
|---|---|---|
| mbedTLS | **2.16.6**（`src\mbedtls\version.h`） | `src\mbedtls\makefile`：`CC=gcc`，`CFLAGS ?= -O2 -m32` |
| libtomcrypt | 项目内 vendored（`src\tomcrypt`） | `src\tomcrypt\makefile`：`CFLAGS=-m32 … -DLTC_NO_ROLC -DLTC_SOURCE`，`AR` 归档到 `../../lib` |
| zlib | 项目内 vendored（`src\zlib`） | 主 makefile 规则 `-m32` |
| 预置静态库 | `lib\libmbedcrypto.a`、`lib\libmbedtls.a`、`lib\libmbedx509.a`、`lib\libtomcrypt.a`（i386 COFF） | `lib\libs.txt` 说明 |

## A.5 项目是否需要特定 32 位 ABI / 预处理宏 / 汇编语法 / 旧版本编译器

| 维度 | 结论 | 依据 |
|---|---|---|
| **32 位 ABI** | **必需**。全部编译/链接路径均为 `-m32`；`q_platform.h` 以 `_M_IX86 \|\| __i386__` 决定 `id386`；`win_cod4.rc`、NASM `-f win` 均为 win32 | `makefile:55,65`；`src\q_platform.h` |
| **运行库/CRT** | **静态链接**（`-static -static-libgcc`），不依赖 mingw 运行 DLL；构建产物含 `mingw_helpers.c`、`mingw_getsp.S`、`___mingw_*` 等 mingw-w64 CRT 符号 → **依赖 mingw-w64 的 msvcrt + dwarf 异常模型** | `makefile:65`；二进制字符串 |
| **异常/线程模型** | 二进制 GCC 注释为 `i686-posix-dwarf-rev0` → **posix 线程 + dwarf-2 展开**（非 sjlj、非 seh）。若改用 sjlj/seh 变体，libgcc/异常/线程 ABI 会不一致 | 二进制与 `.o` 的 GCC 注释 |
| **汇编语法** | **NASM**，`-f win`（win32 COFF），`-dWin32`，`--prefix _`（下划线符号前缀）；113 个 `.asm` 文件，含 `%include` 本地 `.inc` | `makefile:119,320-322`；`src\asmsource\*.asm` |
| **预处理宏** | `WINVER=0x501`、`CODOL_SERVER`、`NDEBUG`、`BUILD_NUMBER/BRANCH/REVISION`、`IW4OL_UPDATE` | `makefile:53,62,70-73` |
| **资源编译** | 需要 `windres`（`-O coff`）生成 `obj\codol\win_codol.res` | `makefile:265-266` |
| **旧版本编译器** | **有强约束**：随附二进制与 597 个 `.o` 均由 **GCC 8.1.0** 构建，CI 亦固定 8.1.0；二进制内嵌原始构建路径 `C:\mingw810\i686-810-posix-dwarf-rt_v6-rev0\...` 与 `C:/mingw810/src/gcc-8.1.0/...` | 二进制/`.o` 字符串；CI |
| **源码级 GCC 依赖** | 存在 `__attribute__((...))`、`__asm__`、`__builtin_*`、`typeof` 等 GCC 扩展（约 133 处命中），非严格 ISO C | `src` 扫描 |
| **Shell 依赖** | makefile 用 `$(shell realpath …)`、`command -v`、`grep`/`cut`、`timeout 15s`、`python3` → **需要 POSIX shell + coreutils**（MSYS2 的 `usr\bin` 或 Git Bash 环境） | `makefile:107,131,282,625,630,633` |

**关键含义：** 本项目不是“任意能编 C 的编译器”即可；它需要 **i686-w64-mingw32 + posix 线程 + dwarf 展开 + msvcrt + NASM win32 + windres** 这一整套，且既有产物与 CI 都把版本锁在 **GCC 8.1.0**。

## A.6 是否存在可复用、来源明确的项目构建环境或锁定依赖清单

**存在“锁定的工具链规格”，但本机没有“已安装的构建环境”。**

| 项 | 结论 | 状态 |
|---|---|---|
| 来源明确的工具链锁定清单 | **有**：`.github\workflows\build.yml` 固定 `i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z`（SourceForge mingw-w64）+ NASM；Linux 作业固定 `gcc-multilib/nasm:i386` | **CONFIRMED** |
| 已提交的既有构建产物可反推工具链身份 | **有**：`bin\codol_dedrun.exe` 与 597 个 `obj\codol\*.o` 的 GCC 注释均为 `GCC: (i686-posix-dwarf-rev0, Built by MinGW-W64 project) 8.1.0` | **CONFIRMED** |
| 依赖版本清单 | **有**：mbedTLS 2.16.6、vendored tomcrypt/zlib；`lib\libs.txt`；`lib\*.a` | **CONFIRMED** |
| 本机已安装该工具链 | **无** | **CONFIRMED（环境检查）** |
| 本机缓存了该工具链安装包 | **无**（`Downloads`、各盘根目录均无 `mingw*.7z`/`i686-8.1.0*`） | **CONFIRMED（环境检查）** |
| 实验副本是否可作为构建输入 | **是**：3726 文件逐一致（继承 `13_A`） | **CONFIRMED** |

补充事实（只读）：原始树的 `obj\codol` 保留了上一轮原生构建的中间产物（597 个 `.o`、484 个 `.d`、1 个 `win_codol.res`），时间戳为 **2026-10-04 17:00–17:03**，PE 特征：`Machine=0x014C (i386)`、`OptMagic=0x010B (PE32)`、`Subsystem=2 (GUI)`。实验副本的 `src\mbedtls\*.o`、`src\tomcrypt\**\*.o` 也是 i386 COFF（`4c 01`）。这些都**只能证明既有构建线与工具链身份**，不构成本轮的可构建环境。

## A.7 本轮明确未做的事（边界声明）

- 未安装、下载或升级任何工具链；未解压任何安装包。
- 未修改 PATH、注册表、`TMP/TEMP` 或任何全局/用户构建设置。
- 未修改原始源码、原始二进制、实验副本、候选补丁或大厅基线。
- 未编译、未链接、未应用补丁、未执行 `make`/`gcc`/`nasm`/`windres`/`cl`。
- 未运行游戏、客户端、服务端、launcher 或任何 `.cmd`/`.bat`/未知脚本。
- 未生成或应用任何可执行补丁。
- 本文件所有工具链结论均为**环境盘点/二进制指纹**，**不是编译验证结果**。

## A.8 阶段 A 裁决

- 环境盘点：**CONFIRMED**。
- 可构建环境：**INSTRUMENTATION_BLOCKED（32 位 MinGW-w64/NASM 工具链缺失）**。
- 目标工具链身份：**CONFIRMED（MinGW-w64 GCC 8.1.0 i686-posix-dwarf，rt_v6）**。
