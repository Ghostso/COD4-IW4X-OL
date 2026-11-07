# 15 — C：静态包结构审查（方案，本轮未执行）

> 任务：`EARLY-NATIVE-TAP-TOOLCHAIN-PREP-001`
> 边界：**本阶段本轮未执行**。本文件制定“不运行包内程序”的静态审查方案与判据；**未下载、未解压、未读取任何包内文件**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。
> 前置：阶段 A（来源）通过；阶段 B（暂存 + 完整性）在执行时通过。

## C.0 原则

1. **只读、不执行**：仅列目录、读文件头、读二进制字符串；**不运行** `gcc`/`make`/`nasm`/`windres` 或任何包内 `.exe`/`.bat`/`.cmd`/`.ps1`。
2. **不临时拼装**：若不满足目标规格，**停止**；**不**通过替换单个 DLL / 编译器 / 运行库来拼装工具链。
3. **不以路径名推断可信**：版本、线程模型、异常模型必须由**包内文件内容**（如 `gcc -v` 字符串、`libgcc` 名称、`*.spec`、`share\gcc-*` 目录）确认，而非仅凭目录名。
4. **留痕**：审查结论需可复核（记录文件路径、字节位置或清单快照）。

## C.1 预期目录结构（待核实，不得预先断言）

mingw-builds 8.1.0 归档的**预期**顶层为 `mingw32\`（解压后即 CI 里的 `C:\mingw32`），其中包含：

| 预期路径 | 预期内容 | 核验方式 |
|---|---|---|
| `mingw32\bin\i686-w64-mingw32-gcc.exe` | i686 C 编译器驱动 | 文件存在 + 读 `gcc -v` **字符串**（不执行） |
| `mingw32\bin\i686-w64-mingw32-g++.exe` | i686 C++ 编译器驱动 | 同上 |
| `mingw32\bin\mingw32-make.exe` | GNU Make | 文件存在 + 读版本字符串 |
| `mingw32\bin\windres.exe` | i686 资源编译器 | 文件存在 + 读字符串 |
| `mingw32\bin\i686-w64-mingw32-windres.exe`（或等价名） | 交叉前缀 windres | 文件存在 |
| `mingw32\bin\i686-w64-mingw32-ar.exe` 等 | binutils | 文件存在 |
| `mingw32\i686-w64-mingw32\lib\libgcc*` | libgcc（dwarf 展开） | 名称含 dwarf；无 `*sjlj*` |
| `mingw32\lib\gcc\i686-w64-mingw32\8.1.0\...` | GCC 8.1.0 运行时 | 路径内版本号 |
| `mingw32\i686-w64-mingw32\include\` | 目标头文件 | 目录存在 |
| `mingw32\share\...`、`mingw32\doc\...` | 文档/许可 | 存在性 |

**注意：** 上述为**预期**；实际结构、命名与是否含 `windres`、`mingw32-make` 必须由 C.5 的实测清单确认。若顶层目录名不是 `mingw32`，需相应调整（CI 依赖 `C:\mingw32\bin`，故顶层应可重命名或即为 `mingw32`）。

## C.2 必须核验的规格项

| # | 规格项 | 通过判据（静态） |
|---|---|---|
| S1 | **GCC 版本 = 8.1.0** | 包内 `lib\gcc\i686-w64-mingw32\8.1.0\` 存在；`gcc` 二进制内字符串含 `8.1.0`；**不以文件名断言** |
| S2 | **目标 = i686 / 32 位** | 存在 `i686-w64-mingw32-*` 工具；`lib\gcc\i686-w64-mingw32\8.1.0\` 而非 `x86_64-*` |
| S3 | **线程模型 = posix** | 存在 `libgcc_s_*.dll` / `libwinpthread*`；**无** `-win32` 线程变体特征；与目录 `threads-posix` 一致 |
| S4 | **异常展开 = dwarf** | `libgcc` 相关文件名/路径含 **dwarf**，**不含 sjlj/seh** |
| S5 | **CRT = msvcrt** | 头/库指向 msvcrt（该 8.1.0 personal build 系列默认 msvcrt）；**无** UCRT 相关库 |
| S6 | **windres 可用** | `bin\windres.exe` 或 `i686-w64-mingw32-windres.exe` 存在 |
| S7 | **GNU Make 可用** | `bin\mingw32-make.exe` 存在 |
| S8 | **POSIX 相关** | 包内是否含 `sh.exe`/coreutils——**预期不含**（由 MSYS2 提供）；若不含量化说明 |
| S9 | **无意外组件** | 目录清单中**无**不明可执行、无与目标不符的组件（如 x86_64 编译器等） |

## C.3 必须检出的“陷阱”清单

| 陷阱 | 检出方式 | 处置 |
|---|---|---|
| 版本被重命名伪装 | 读包内 `lib\gcc\<triplet>\<版本>\` 路径 + 二进制字符串 | 与 8.1.0 不符 → 停止 |
| 线程模型不符（win32/sjlj） | 检查 `libgcc`/`libwinpthread` 命名与目录 `threads-posix` | 不符 → 停止 |
| 异常模型不符（sjlj/seh） | 检查 dwarf/sjlj 标识 | 不符 → 停止 |
| 目标架构不符（x86_64） | 检查 `i686-*` 存在性 | 不符 → 停止 |
| 捆绑未知可执行/脚本 | 全量清单 + 扩展名统计 + 可疑 `.bat/.cmd/.ps1/.vbs` | 逐一说明；无法解释 → 停止 |
| 与文件名/目录名不符 | 内容级核验（C.2） | 不符 → 停止 |
| 需要临时拼装才满足规格 | 若缺少 windres/make 等必需件 | **停止，不拼装** |

## C.4 归档“不解压即审查”手段（可选前置）

在不释放到磁盘的前提下，可先做**只读清单**：

- 使用已有解压器（本机发现：`C:\Program Files\NVIDIA Corporation\NVIDIA App\7z.exe`、`C:\Program Files (x86)\VMware\VMware Workstation\7za.exe`、`D:\Program Files\Microvirt\MEmu\7za.exe`；`tar.exe` 为 bsdtar 3.5.2）以 **list 模式**（如 `7z l`）输出完整文件清单。
- **约束：此步骤在阶段 C 执行时也需授权；本轮未执行。** 且**仅列清单**，不得提取或运行。

## C.5 静态审查交付记录（执行时产出）

1. 归档顶层结构树（含文件数、总解压尺寸）。
2. 全量文件清单快照（可含 SHA-256 摘要，供复核）。
3. S1–S9 逐项判定表（每项附依据：路径/字符串/字节偏移）。
4. 可执行文件清单与用途说明（含对不明项的结论）。
5. 与“目标规格”的差异汇总与处置建议。
6. 阶段 C 裁决：`GO`（规格满足，可进入阶段 D 执行）/ `NO-GO`（存在不符或需拼装）。

## C.6 阶段 C 裁决（本轮）

- 阶段 C 方案：**CONFIRMED（已就绪）**。
- 阶段 C 执行：**NOT_EXECUTED（未下载、未解压、未审查）**。
- 任何“windres/make 随包提供”的说法在阶段 C 前均为 **CANDIDATE**，不得作为既成事实。
- 关键红线：**不满足规格时停止，不通过替换单个 DLL/编译器/运行库临时拼装工具链。**

> 本文件为**方案**，非执行记录；本轮未解压、未读取任何包内文件、未运行任何程序。