# 15 — D：可复现构建环境搭建与后续验证方案（本任务不执行）

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-PREP-001`
> 边界：**本文件只制定方案**。本任务**未执行**下列任何获取/安装/编译步骤；也未执行第 1–7 步验证。所有执行动作须**单独授权**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## D.0 目标环境规格（来自 `14_B` / `15_A`）

| 组件 | 目标 | 来源 |
|---|---|---|
| MinGW-w64 GCC | `i686-8.1.0-release-posix-dwarf-rt_v6-rev0` | SourceForge（CI 同一 URL） |
| 目标架构 | i686 / PE32 | `makefile:55,65` |
| POSIX threads | **是** | 二进制指纹 `i686-posix-dwarf-rev0` |
| DWARF 异常展开 | **是** | 同上 |
| CRT | msvcrt（`-static -static-libgcc`） | `makefile:65` |
| GNU Make | `mingw32-make` | 随包 |
| NASM | 支持 `-f win --prefix _` | `makefile:111,119` |
| Windres | i686 版，须先于 `usr\bin` | `makefile:125-131` |
| POSIX shell/coreutils/Python 3 | MSYS2 `usr\bin` 或等价 | `makefile:107,131,625-633` |
| 项目依赖 | mbedTLS 2.16.6、vendored tomcrypt/zlib、`lib\*.a`、pexports | 项目内锁定 |

## D.1 可复现来源固定（Reproducibility Pins）

| 物料 | 固定值 |
|---|---|
| MinGW 规范 URL | `https://downloads.sourceforge.net/project/mingw-w64/Toolchains%20targetting%20Win32/Personal%20Builds/mingw-builds/8.1.0/threads-posix/dwarf/i686-8.1.0-release-posix-dwarf-rt_v6-rev0.7z` |
| MinGW 大小 | `45050859` |
| MinGW SHA-256 | `adb84b70094c0225dd30187ff995e311d19424b1eb8f60934c60e4903297f946` |
| MinGW MD5 | `07583a272282f71e6e8701b2bf64fafe` |
| NASM（CI 默认） | `2.16.01` — `https://www.nasm.us/pub/nasm/releasebuilds/2.16.01/win64/nasm-2.16.01-win64.zip`（506,056 字节；官方无 sidecar 校验） |
| NASM（备选，可核） | `3.01` — SHA-512 `771c238ddb17c98d5736ccaba4ade1d1601d896f09e588489cb43a4f6381bc0ae14d1869f5316fe94f847f54867e65cf12665529b1e7ad88e5e7d3e162719a4f` |
| MSYS2 | `https://www.msys2.org/`（官方入口；用于 `usr\bin` 的 make/sh/coreutils/python3） |
| 项目内依赖 | mbedTLS 2.16.6 / tomcrypt / zlib / `lib\*.a` / `pexports-0.47`（**不另行下载**） |

**NASM 版本决策（须显式记录）：** CI 默认 2.16.01；本机缓存为 3.01。两者都支持 `-f win --prefix _`，但**不是同一版本**。方案要求：**优先与 CI 一致（2.16.01）**；若采用 3.01，须在构建记录中显式说明偏离，并作为**未验证差异**标注。

## D.2 搭建步骤（执行时，需授权）

| 步 | 动作 | 写位置 | 约束 |
|---|---|---|---|
| 1 | 下载/复制 MinGW 7z 到 `_staging\packages\` | 仅输出目录 | 保留原始包 |
| 2 | 校验 SHA-256/MD5/大小（`15_B B.3`） | `_staging\integrity\` | 不匹配即停止 |
| 3 | 用已有解压器解压到 `_staging\extract\` | 仅输出目录 | **不解压到系统目录** |
| 4 | 静态包结构审查（`15_C`） | 记录 | 只读、不运行 |
| 5 | 获取 NASM（按 D.1 决策）到 `_staging\` | 仅输出目录 | 记录版本与哈希 |
| 6 | 准备 POSIX 环境（MSYS2 或既有），**不改系统 PATH** | 会话级临时 PATH | 通过构建脚本/会话变量注入 |
| 7 | 组装**会话级**环境（`PATH` 指向 `_staging\extract\...\bin` 与 MSYS2 `usr\bin`） | 仅当前会话 | 不写注册表、不改全局 |
| 8 | 落盘环境清单（版本/路径/哈希） | `_staging\` | 供复核 |

**顺序要点：** `mingw32\bin` 必须**先于** `usr\bin`，否则 `windres` 会解析到 `usr\bin` 的 x86_64 版本（`makefile:125-131`）。
**TMP/TEMP：** `BUILD-CODOL.ps1` 记录 gcc 默认临时目录 `C:\WINDOWS` 不可写；执行时须将会话级 `TMP/TEMP` 指向可写目录（例如 `obj\_tmp`）。

## D.3 后续验证顺序（七步，独立授权；本任务均不执行）

| 步 | 验证内容 | 动作 | 通过判据 |
|---|---|---|---|
| **1** | 工具链身份及版本 | 只读执行 `gcc -v`、`g++ -v`、`nasm -v`、`windres --version`、`make --version`、`gcc -dumpmachine` | 三元组 `i686-w64-mingw32`；标识含 `posix-dwarf`；版本 8.1.0 |
| **2** | i686/PE32 目标能力 | 独立临时目录编译最小探针 `-m32`，检查产物 `Machine=0x014C` | 产出 PE32 i386；无缺库错误 |
| **3** | POSIX/DWARF 运行库与 msvcrt 链接配置 | 只读检查 `libgcc`/`libwinpthread` 命名、`-static` 链接、`-static-libgcc`；确认无 sjlj/seh/UCRT | 与 `i686-posix-dwarf` + msvcrt 一致 |
| **4** | Make/NASM/Windres/Python/POSIX shell 可用性 | 只读版本查询 + 存在性核验 | 全部可用；`windres` 解析为 i686 版 |
| **5** | 项目依赖与构建配置 | 独立副本中检查 `-I` 路径、`lib\*.a`(i386)、`src\{mbedtls,tomcrypt,zlib}`、`realpath`/`command -v`/`timeout`/`python3` | 全部满足 |
| **6** | 候选补丁应用检查 | 一次性临时副本 `git apply --check patch_candidates\n3_hooks.diff`（仅检查） | 退出码 0；触及 5 文件 |
| **7** | 对象编译/构建验证 | 独立副本先 `make objects`（**不链接**）；通过后再单独授权链接到独立输出 | 退出码 0；对象 i386 COFF；不覆盖 `bin\codol_dedrun*.exe` |

**放行规则：** 逐级放行；任一步失败即停止。**第 7 步必须单独授权**，且优先 `make objects` 而非默认链接目标（`ld` 链接失败会删除输出，见 `tools\BUILD-CODOL.ps1`）。

## D.4 与既有交付物的衔接

| 关系 | 说明 |
|---|---|
| 上游依据 | `14_A`（环境盘点）、`14_B`（项目需求）、`14_C`（兼容性矩阵）、`14_D`（六步验证）、`14_E`（裁决） |
| 本任务补充 | `15_A/B/C` 提供**来源固定 + 完整性方案 + 静态审查方案**，把 `14` 的“目标工具链”落到“可复现的获取与核验” |
| 验证顺序变化 | 本任务把 `14_D` 的六步扩展为**七步**：新增“POSIX/DWARF 运行库与 msvcrt 链接配置核验”为独立第 3 步 |
| 未闭合项 | 源可访问但**未下载**；哈希**已记录但未实测比对**；包结构**未审查**；工具链**未运行** |

## D.5 明确不做（本任务）

- 不下载、不复制、不解压、不安装、不升级任何工具链。
- 不修改 PATH/注册表/全局或用户构建设置。
- 不运行包内或工具链中的任何程序。
- 不编译、不链接、不应用候选补丁。
- 不修改原始源码、既有实验副本、候选补丁或大厅基线。
- 不开始任何客户端/服务端运行实验。

## D.6 阶段 D 裁决

- 方案：**CONFIRMED（可复现来源已固定，步骤与放行规则已定义）**。
- 执行：**NOT_EXECUTED（需单独授权）**。
- 硬性红线：**不满足规格即停止；不得通过替换单个 DLL/编译器/运行库临时拼装工具链。**

> 本文件为**方案**，非执行记录；本轮未获取、未安装、未解压、未编译、未运行任何程序。