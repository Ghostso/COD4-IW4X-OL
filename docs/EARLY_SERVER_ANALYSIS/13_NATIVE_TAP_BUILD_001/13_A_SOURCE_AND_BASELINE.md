# 13 — A：源码、构建系统与隔离基线

> 任务：`EARLY-NATIVE-TAP-BUILD-001`
> 状态：只读核查与隔离副本复核；未启动任何游戏进程、未编译、未应用补丁。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## A.0 结论先行

| 问题 | 结论 | 状态 |
|---|---|---|
| 实际源码根目录 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated` | **CONFIRMED** |
| 构建系统 | GNU Make + 32 位 MinGW/MSYS2 工具链；目标 `bin/codol_dedrun.exe` | **CONFIRMED（静态）** |
| 启动脚本实际目标 | `dedicated\bin\codol_dedrun_next.exe` | **CONFIRMED**（继承 `11_A`） |
| 源码与当前二进制精确同一构建 | 缺少 commit/PDB/MAP/构建日志；只能建立同一构建线 | **STRONG_CANDIDATE** |
| 隔离实验副本是否与原始构建输入一致 | 3726 个纳入清单文件逐文件 SHA-256 匹配，0 差异 | **CONFIRMED** |
| 原始样本/大厅基线是否被修改 | 本轮只读；未修改 | **CONFIRMED（本轮边界内）** |
| 候选补丁是否已应用/编译 | 未应用、未编译 | **NOT_OBSERVED** |

## A.1 源码根、启动脚本与目标二进制

源码根：

`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated`

实际启动脚本：

`...\CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd`

关键哈希（本轮独立复算）：

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `makefile` | 50,570 | `FEFF456D713ED926A48B4DACE6B0DD8B81F30B757F2B263975E314369A9C8703` |
| `tools\BUILD-CODOL.ps1` | 3,625 | `6EAB7B2759A9A2A276AF708F28715753EB503ED2DA4C997CB5B90E5E7FC79BB4` |
| `src\sv_main.c` | 219,831 | `4E9AC58B85FF52325AB5039050969D155DD9BC48F2218145DF8C9B9D0F4A1E7C` |
| `src\sv_client.c` | 119,801 | `C793898743682709A1BFEF82A297EE6895C87A6E76F83B1222A5FBDD250202B4` |
| `src\sv_snapshot.c` | 102,448 | `D6C182B177D2A07FA7A74C5E97E0013F1F147EF4F8812E8A24C2983793597172` |
| `src\sv_net_chan.c` | 5,664 | `A11DD2FF663C64D53165488F7323E003D6B4DB2CD851A7F07A9DB8C7CA2258EA` |
| `src\common.c` | 37,462 | `E53DAB6428C2E196E873FE9C9662B44E970731CF3958BC251F60612ECCE0BD0F` |
| `src\codol\snapshot\codol_sv_state.c` | 7,243 | `D5C3B427240B3AC6F179BC08C1BDAA915FD223D7C09B930C060FA9432840ABB0` |
| `src\codol\snapshot\codol_snapshot.c` | 3,396 | `E8E1677F0250CCB294A4A9DA9F36D34874BF671C2BA05CBA04A4AA181E589577` |
| `bin\codol_dedrun.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `bin\codol_dedrun_next.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `bin\START-CODOL-SERVER.cmd` | 12,116 | `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` |

`codol_dedrun.exe` 与 `codol_dedrun_next.exe` 长度和 SHA-256 完全相同，是字节相同的副本。该事实只证明两者一致，不证明它们与当前源码精确同一 commit。

## A.2 构建系统

`makefile` 关键行：

- `:16-23`：`GAME ?= codol`；`TARGETNAME=codol_dedrun`。
- `:51-57`：`CC=gcc`；含 `-m32`、`-msse2`、`-Wall`、`-MMD -MP`。
- `:59-63`：非 DEBUG 使用 `-fno-pie -O1 -DNDEBUG`。
- `:65`：Windows 链接参数含 `-m32 -g`、`--nxcompat`、`--large-address-aware`、`-mwindows`。
- `:71-73`：`GAME=codol` 时追加 `CODOL_SERVER` 宏。
- `:77-94`：源码目录 `src`、对象目录 `obj/codol`、二进制目录 `bin`；CODOL 区域包含 `snapshot`。
- `:161-178`：C 源集合为 `src/*.c` 加 `src/codol/<area>/*.c`。
- `:255-262`：链接目标 `bin/codol_dedrun.exe`。
- `:293-315`：通用 C / CODOL area 编译规则。

`tools\BUILD-CODOL.ps1` 关键行：

- 默认构建产物为 `bin\codol_dedrun.exe`，不触碰 `bin\codol_dedrun_next.exe`。
- 默认调用 `make`，需要 `make` 与 `gcc` 在 PATH 中；脚本本身未被本轮执行。

**构建约束结论：** 本项目不是独立于 MinGW/MSYS2 的自包含构建；在缺少 `make`、`gcc` 和 32 位运行库时，不能产生可信候选二进制。

## A.3 隔离实验副本

实验副本：

`D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy`

副本纳入清单：

- 3726 个文件
- 174,976,245 字节
- 排除：`.git`、`bin\home`、`obj`、`dis`、`pbsv_exec`、`scriptdocumentation`、`wiki`、`.github`
- 排除理由：运行状态、会话材料、既有反汇编/中间产物及与构建无关内容；排除项不作为本轮候选构建输入。

副本清单：

`...\13_NATIVE_TAP_BUILD_001\logs\experiment_copy_manifest.csv`

- 3726 行
- SHA-256：`C8745A2651A66C0D2C7F2AB012F205914F34E7B14641E76E399272484DC4D607`

逐文件核验结果：

- 原始纳入文件与副本文件对比：3726
- 不匹配：0
- 副本缺失：0
- 结论：**CONFIRMED**

`dedicated\.git` 存在但无任何 commit：

- `git status` 不能给出可用于构建溯源的正确 commit。
- 因此不能把 Git 元数据作为源码/二进制同一性证据。

## A.4 原始树只读性

本轮未执行：

- 未启动客户端、服务端、launcher；
- 未编译、未应用补丁、未运行 `.cmd`/未知脚本；
- 未注入进程；
- 未导出或读取认证秘密；
- 未修改原始源码、原始二进制、既有报告或可进入大厅基线。

`bin\home` 被排除在实验副本之外，避免复制可能包含会话材料或运行时状态的目录。

## A.5 当前阻塞

工具链核查结果（仅查询命令是否存在）：

| 工具 | 状态 |
|---|---|
| `make` | 未找到 |
| `mingw32-make` | 未找到 |
| `gcc` | 未找到 |
| `clang` | 未找到 |
| `i686-w64-mingw32-gcc` | 未找到 |
| `x86_64-w64-mingw32-gcc` | 未找到 |
| `windres` | 未找到 |
| `nasm` | 未找到 |
| `cl` | 未找到 |

常见安装目录均不存在：

- `C:\msys64`
- `C:\MinGW`
- `D:\msys64`
- `D:\MinGW`
- Visual Studio 2022 常见目录

因此阶段 C 的构建状态为：

**BUILD_NOT_EXECUTED / INSTRUMENTATION_BLOCKED（工具链缺失）**

该阻塞不否定阶段 A/B 的静态审查价值，但否定“已获得可运行候选产物”的结论。
