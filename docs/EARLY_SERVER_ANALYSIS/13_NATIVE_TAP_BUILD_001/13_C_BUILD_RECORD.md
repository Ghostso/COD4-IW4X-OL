# 13 — C：独立构建记录

> 任务：`EARLY-NATIVE-TAP-BUILD-001`
> 结论：**未执行构建**。
> 状态：**NOT_OBSERVED / INSTRUMENTATION_BLOCKED（工具链缺失）**。
> 本文件不包含候选二进制、构建成功声明或运行验证结论。

## C.0 裁决

| 项目 | 结果 | 状态 |
|---|---|---|
| 是否应用候选补丁 | 否 | **NOT_OBSERVED** |
| 是否执行构建 | 否 | **NOT_OBSERVED** |
| 是否产生候选二进制 | 否 | **NOT_OBSERVED** |
| 是否可复核构建产物 SHA-256 | 不适用 | **NOT_OBSERVED** |
| 构建工具链是否可用 | `make`/`gcc` 等均未找到 | **CONFIRMED（环境检查）** |
| 当前构建裁决 | 无候选产物 | **INSTRUMENTATION_BLOCKED** |

## C.1 构建系统静态事实

源码根：

`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated`

关键构建文件：

| 文件 | 事实 | 证据 |
|---|---|---|
| `makefile` | `GAME ?= codol`；`TARGETNAME=codol_dedrun` | `makefile:16-23` |
| `makefile` | `CC=gcc`；`CPP=g++`；含 `-m32 -msse2` | `makefile:51-57` |
| `makefile` | 非 DEBUG：`-fno-pie -O1 -DNDEBUG` | `makefile:59-63` |
| `makefile` | Windows 链接含 `-m32`、`-static-libgcc`、`-mwindows` | `makefile:65` |
| `makefile` | `CODOL_SERVER` 宏由 `GAME=codol` 追加 | `makefile:71-73` |
| `makefile` | 对象目录 `obj/codol`，目标 `bin/codol_dedrun.exe` | `makefile:77-94`、`:165`、`:255-262` |
| `makefile` | C 源集合为 `src/*.c` 与 `src/codol/<area>/*.c` | `makefile:161-178` |
| `makefile` | 通用 C 编译规则 | `makefile:293-295` |
| `makefile` | CODOL area C 编译规则 | `makefile:305-315` |
| `tools\BUILD-CODOL.ps1` | 硬编码 `C:\msys64\usr\bin\make.exe` | `tools\BUILD-CODOL.ps1:40` |
| `tools\BUILD-CODOL.ps1` | 该文件不存在时 `Write-Error` 并退出 | `tools\BUILD-CODOL.ps1:42-44` |
| `tools\BUILD-CODOL.ps1` | 默认链接 `bin\codol_dedrun.exe`，不自动覆盖 `codol_dedrun_next.exe` | `tools\BUILD-CODOL.ps1:20-23`、`:70-81` |

候选观察器源码若被纳入构建，按 `makefile:161-178` 的源集合规则，`src/n3_observer.c` 会自动进入 `C_SOURCES`。但本轮没有把候选文件复制到 `experiment_copy/src`，也没有编译。

## C.2 工具链核查

仅执行命令存在性查询；未运行任何编译器或构建脚本。

| 工具 | 查询结果 |
|---|---|
| `make` | NOT_FOUND |
| `mingw32-make` | NOT_FOUND |
| `gcc` | NOT_FOUND |
| `clang` | NOT_FOUND |
| `i686-w64-mingw32-gcc` | NOT_FOUND |
| `x86_64-w64-mingw32-gcc` | NOT_FOUND |
| `windres` | NOT_FOUND |
| `nasm` | NOT_FOUND |
| `cl` | NOT_FOUND |

目录存在性：

| 路径 | 结果 |
|---|---|
| `C:\msys64` | 不存在 |
| `C:\MinGW` | 不存在 |
| `D:\msys64` | 不存在 |
| `D:\MinGW` | 不存在 |
| `C:\Program Files (x86)\Microsoft Visual Studio` | 存在，但未发现可用 `cl` |

## C.3 未执行的构建命令

以下命令**仅作为记录**，本轮没有执行：

```powershell
# 原始构建脚本路径；本轮未运行
powershell -ExecutionPolicy Bypass -File tools\BUILD-CODOL.ps1 -ObjectsOnly
```

未执行原因：

- `tools\BUILD-CODOL.ps1:40` 要求 `C:\msys64\usr\bin\make.exe`；
- 该路径不存在；
- `gcc`、`g++`、`windres`、`nasm` 也不在 PATH；
- 本轮禁止执行未知脚本或构建。

## C.4 构建日志与产物

- 构建日志：无，因为未构建。
- 候选二进制：无。
- 候选二进制 SHA-256：不适用。
- 编译警告：无，因为未编译。
- 编译错误：无，因为未编译。
- 源码与构建产物对应关系：**UNKNOWN**，因为不存在本轮构建产物。

## C.5 构建能否证明什么

即使未来构建成功，也只能证明：

- 源码在指定工具链下可编译；
- 生成了某个候选二进制；
- 该二进制的 SHA-256 可复核。

不能证明：

- 候选二进制运行时无扰动；
- 观察器不改变发送时序；
- 服务端与客户端实际互通；
- 客户端成功解析 gamestate/snapshot；
- 客户端进入 `CA_ACTIVE` 或后续可玩状态。

## C.6 结论

本轮构建阶段未通过：

**BUILD_NOT_EXECUTED / INSTRUMENTATION_BLOCKED。**

当前没有可进入运行实验的候选产物。
