# 11 — A：真实执行路径与源码/二进制对应关系

> 任务：`EARLY-NATIVE-TAP-DESIGN-001`。
> 本文件只读核查，不运行、不注入、不编译、不应用补丁。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## A.0 结论先行

| 问题 | 结论 | 状态 |
|---|---|---|
| 启动脚本实际运行哪个可执行文件？ | `dedicated\bin\codol_dedrun_next.exe` | **CONFIRMED** |
| `codol_dedrun_next.exe` 与 `codol_dedrun.exe` 是否字节相同？ | 是，长度和 SHA-256 均相同 | **CONFIRMED** |
| `next` 是否由 `codol_dedrun.exe` 人工 promote？ | 构建脚本和启动脚本均明确描述该流程；但未找到该次 copy 的独立操作日志 | **STRONG_CANDIDATE** |
| 当前源码/对象文件/二进制是否来自同一构建？ | `.d` 依赖、对象时间链、`CODOL_SERVER` 构建宏和二进制内嵌源码独有字符串均支持；缺少精确 commit/构建日志/PDB | **STRONG_CANDIDATE** |
| `SV_WriteGameState` / `SV_WriteSnapshotToClient` 的 CODOL 分支是否在当前执行路径？ | 源码调用链闭合到启动后正常客户端状态机；对应对象文件在链接输入集合中 | **CONFIRMED（源码/构建级可达）** |
| 是否已证明当前客户端能消费该二进制？ | 未观察；历史 `console_mp` 日志只证明参考实现可被消费 | **NOT_OBSERVED** |

**不能把 `STRONG_CANDIDATE` 写成“精确源码 commit 与二进制已确认同一”。** 本轮没有 Git 元数据、PDB/MAP、构建日志或可重放链接记录来证明这一点。

## A.1 目标二进制与启动入口

服务器根：

`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server`

| 文件 | 大小（B） | LastWriteTimeUtc | SHA-256 |
|---|---:|---|---|
| `dedicated\bin\codol_dedrun_next.exe` | 8,469,493 | 2026-10-04T09:49:36Z | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `dedicated\bin\codol_dedrun.exe` | 8,469,493 | 2026-10-04T09:03:01Z | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `dedicated\bin\START-CODOL-SERVER.cmd` | 12,116 | 2026-10-04T17:30:07Z | `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` |

启动脚本证据：

- `START-CODOL-SERVER.cmd:4-6`：注释明确“Runs the native server ... in place of the Python `game-server.py`”。
- `:71-74`：要求 `codol_dedrun_next.exe` 存在；提示从仓库根构建 `bin\codol_dedrun.exe`，再 promote 到 `bin\codol_dedrun_next.exe`。
- `:183`：`cd /d "%~dp0"`。
- `:189`：实际启动 `"%~dp0codol_dedrun_next.exe"`。
- `:190-216`：参数包含 `dedicated 2`、`fs_basepath`、`fs_homepath`、`net_port %CODOL_MM_HOST_PORT%`、`rcon_password`、`logfile 2`、`logrcon 1`、`developer`、`sv_fps 60`、脚本路径、`codol_securityKeyPath`、`codol_admissionPath`、`codol_profilePath`、`codol_zoneType`、`codol_sessionMap`、`g_gametype`、bots、`map`。

**结论：实际执行文件为 `codol_dedrun_next.exe`，等级 CONFIRMED。**
该脚本同时把 `net_port`、安全密钥路径、准入文件、profile 路径和地图/模式参数传入目标进程；本设计只引用路径和参数名，不读取、复制、哈希或导出密钥内容。

## A.2 源码、构建脚本、对象文件与二进制

### A.2.1 构建脚本

实际脚本路径：

`...\CODOL_Server\dedicated\tools\BUILD-CODOL.ps1`

SHA-256：

`6EAB7B2759A9A2A276AF708F28715753EB503ED2DA4C997CB5B90E5E7FC79BB4`

关键证据：

- `BUILD-CODOL.ps1:20-25`：默认目标是 `bin\codol_dedrun.exe`；**不会触碰** `bin\codol_dedrun_next.exe`；要求人工执行 `copy /y bin\codol_dedrun.exe bin\codol_dedrun_next.exe`。
- `:27`：建议在 promote 前保留 `bin\rollback\` 回滚副本。
- `:39`：`$repo = Split-Path -Parent $PSScriptRoot`，即 `CODOL_Server\dedicated`。
- `:57`：默认目标文本为 `default (links bin\codol_dedrun.exe)`。
- `:63-70`：`-ObjectsOnly` 调 `make ... objects`；默认调 `make ...`。
- `:75-81`：链接成功后打印 `bin\codol_dedrun.exe`，并提示尚未 promote。

### A.2.2 Makefile 与编译宏

Makefile：

`...\CODOL_Server\dedicated\makefile`

SHA-256：

`FEFF456D713ED926A48B4DACE6B0DD8B81F30B757F2B263975E314369A9C8703`

关键证据：

- `:16-23`：`GAME ?= codol`；`TARGETNAME=codol_dedrun`。
- `:51-57`：`CC=gcc`；通用编译参数含 `-m32`、`-msse2`、`-Wall`、`-MMD -MP`。
- `:59-63`：非 DEBUG 默认 `-fno-pie -O1 -DNDEBUG`。
- `:65`：Windows 链接参数包含 `-m32 -g`、`--nxcompat`、`--large-address-aware`、`-mwindows`、静态库链接。
- `:71-73`：`GAME=codol` 时追加 `CODOL_SERVER` 宏。
- `:77-94`：`SRC_DIR=src`、`BIN_DIR=bin`、`OBJ_DIR=obj/$(GAME)`；CODOL 区域为 `net snapshot player weapon vehicle script assets collision stats`。
- `:161-178`：C 源集合包含 `src/*.c` 以及所有 `src/codol/<area>/*.c`。
- `:255-262`：链接目标为 `$(BIN_DIR)/$(TARGETNAME)`，即 `bin/codol_dedrun.exe`。
- `:293-315`：通用 C 和 CODOL area 编译规则。

### A.2.3 对象文件与 `.d` 依赖

对象目录：

`...\dedicated\obj\codol`

| 对象/依赖 | 大小（B） | LastWriteTimeUtc | 对应源码证据 |
|---|---:|---|---|
| `codol_sv_state.o` | 5,569 | 2026-10-04T09:00:46Z | `codol_sv_state.d` 指向 `src/codol/snapshot/codol_sv_state.c` |
| `codol_configstrings.o` | 34,153 | 2026-10-04T09:00:46Z | `.d` 指向 `src/codol/snapshot/codol_configstrings.c` |
| `codol_snapshot.o` | 4,043 | 2026-10-04T09:00:47Z | `.d` 指向 `src/codol/snapshot/codol_snapshot.c` |
| `sv_main.o` | 110,782 | 2026-10-04T09:00:31Z | `.d` 指向 `src/sv_main.c` |
| `sv_snapshot.o` | 38,630 | 2026-10-04T09:00:33Z | `.d` 指向 `src/sv_snapshot.c` |
| `sv_net_chan.o` | 1,820 | 2026-10-04T09:00:41Z | `.d` 指向 `src/sv_net_chan.c` |
| `common.o` | — | 2026-10-04T09:00:38Z | `.d` 指向 `src/common.c` |
| `version.o` | — | 2026-10-04T09:03:00Z | 由 makefile `:271-273` 强制重建 |

时间链：

- 大多数对象集中在 `2026-10-04T09:00:31Z` 至 `09:00:47Z`。
- `version.o` 在 `09:03:00Z` 重建。
- `codol_dedrun.exe` 时间为 `09:03:01Z`，与链接阶段吻合。
- `codol_dedrun_next.exe` 时间为 `09:49:36Z`，晚于 `codol_dedrun.exe`，且两者 SHA-256 完全相同。

### A.2.4 二进制内嵌源码独有字符串

对 `codol_dedrun_next.exe` 做只读字节扫描（ASCII，非 UTF-16LE）命中：

| 字符串 | 文件偏移 |
|---|---:|
| `CoDOL snapshot clock:` | `0x3BF8EC` |
| `pending snapshot sequence/preparation mismatch at end` | `0x3BFAC0` |
| `no native frame for sequence` | `0x3BF7F0` |
| `CODOL_WriteServerGamestate` | `0x6B1482` |
| `CODOL_WriteGamestate` | `0x6B09DA` |
| `codol_debugTrace` | `0x3CB0AA` |
| `CoDOL gamestate rejected (metadata or message capacity)` | `0x3D9B74` |

这些字符串分别出现在本轮复核的 `sv_snapshot.c:249/275/845`、`sv_main.c:2306`、`common.c:574` 以及 CODOL 函数名所在路径中。它们证明二进制包含与当前源码高度一致的 CODOL 专用文本，但**字符串命中本身不能证明逐字节的精确构建同一性**。

### A.2.5 对应关系裁决

支持同一构建的快照证据：

1. 构建脚本默认只产出 `bin\codol_dedrun.exe`，并要求人工 promote 到 `next`。
2. 两个 exe 长度和 SHA-256 完全相同，`next` 时间晚于 `codol_dedrun.exe`。
3. `CODOL_SERVER` 宏、CODOL 源集合和链接输入在 makefile 中闭合。
4. `.d` 依赖指向当前 `src` 路径；对象时间链紧邻 exe 时间。
5. exe 内嵌多条当前 CODOL 源码独有字符串和错误文本。

仍缺失的精确证明：

- 没有 `.git` 目录，无法把二进制锁定到某个 commit。
- PE VersionInfo 为空，无法用版本资源证明构建输入。
- 未找到 PDB/MAP/ILK 或 native server 构建日志。
- 未找到人工执行 `copy /y` promote 的独立日志。
- 字符串命中和时间链不能排除“源码在构建后被相同内容再次写入”或“未记录的重链接”等边界情形。

**最终等级：源码快照、对象文件和 `codol_dedrun.exe` 属于同一构建线为 `STRONG_CANDIDATE`；`next` 是 promoted copy 为 `STRONG_CANDIDATE`。**
**不能写 CONFIRMED 的“精确 commit ↔ 当前 exe”。**

## A.3 目标序列化函数是否位于当前执行路径

### A.3.1 gamestate 调用链

证据：

- `sv_client.c:2160`：`SV_SendClientGameState`。
- `:2273`：`client->state = CS_PRIMED`。
- `:2281-2287`：初始化消息并写 `lastClientCommand`。
- `:2293`：`SV_UpdateServerCommandsToClient(client, &msg)`。
- `:2298`：`SV_WriteGameState(&msg, client)`。
- `:2312`：`SV_SendMessageToClient(&msg, client)`。

`sv_main.c:3939-3949`：

- `SV_WriteGameState` 在 `#ifdef CODOL_SERVER` 下调用 `CODOL_WriteServerGamestate(...)`，随后 `return`。
- 传统 `svc_ops_e` 分支位于 `#endif` 之后，CODOL 编译时不可达。

`codol_sv_state.c:119-151`：

- `:141` `CODOL_MsgWriteInit` 指向 `msg->data + msg->cursize`。
- `:142-143` 调 `CODOL_WriteGamestate`。
- `:144` `msg->cursize += wire.size`。
- `:145-146` 注释明确 gamestate 以字节字段结束，`msg->bit = msg->cursize * 8`。

`codol_configstrings.c:269-308`：

- `:275-284` configstring 子流：byte `3`、u16 count、13 位索引/字符串项、byte `5`。
- `:298-306` gamestate：byte `2`、u32 sequence、cstring map、cstring zone_type、u32 const_crc、configstrings 子流、u32 client_number、u32 checksum_feed、byte `5`。

**结论：gamestate 编码入口在当前 CODOL 编译分支和正常连接状态机中可达，等级 CONFIRMED（源码/构建级可达）；实际线上运行尚未观察。**

### A.3.2 snapshot 调用链

证据：

- `sv_snapshot.c:759`：`SV_SendClientSnapshot`。
- `:765`：`SV_BeginClientSnapshot`。
- `:767`：`SV_WriteSnapshotToClient`。
- `:769`：`SV_EndClientSnapshot`。

`sv_snapshot.c:224-263`：

- `:228`：`CS_ZOMBIE` 直接返回。
- `:230-231`：取 `outgoingSequence` 与 native frame。
- `:238`：取 `client->frames[...]`。
- `:247-252`：无 native frame 时设置失败原因和 `overflowed`。
- `:254-259`：命令、ACK、origin velocity flag。
- `:260-263`：`CODOL_PrepareClientSnapshot(...)`。

`codol_sv_snapshot.c:85-130`：

- `:102`：分配序列化副本。
- `:104-106`：调 `CODOL_PrepareServerSnapshot`。
- `:124-127`：记录 `message/data/size/sequence`，保存 prepared 副本。

`codol_snapshot.c:8-46`：

- `:22-23`：`m->bit = 0`，`CODOL_WriteByte(m, 0)`。
- `:24-27`：serverTime、delta、flags、base bit。
- `:28-40`：player state、anim commands、actors、entities、clients、glass 六个 section。
- `:41`：写 byte `5`。

`sv_snapshot.c:642-696`：

- `:642`：`SV_SendMessageToClient`。
- `:648`：`overflowed` 直接拒绝。
- `:679`：记录 `msg->cursize`。
- `:688`：`SV_Netchan_Transmit(client, msg->data, msg->cursize)`。
- `:690-695`：发送失败时回滚 frame 记录。

`sv_net_chan.c:135-149`：

- `:140`：参数与长度检查。
- `:141-143`：`malloc` 后 `memcpy` 调用者明文。
- `:144`：`SV_Netchan_Encode`。
- `:145`：`CODOL_NetchanSubmit(&client->netchan, cursize, encoded)`。
- `:146-148`：提交后释放临时编码缓冲；调用者明文保持原样。

**结论：snapshot 编码和发送路径在当前 CODOL 编译分支中可达，等级 CONFIRMED（源码/构建级可达）；实际线上运行和客户端接受尚未观察。**

## A.4 启动脚本中的秘密材料边界

启动脚本参数包含：

- `codol_securityKeyPath`（`:203`）。
- `codol_admissionPath`（`:204`）。
- `rcon_password`（`:195`）。
- `codol_profilePath`（`:206`）。

本设计只记录这些参数的存在和用途，不读取其目标文件内容、不计算密钥哈希、不把任何凭据写入交付物。后续运行实验必须使用隔离环境自己的受控配置，并在捕获/归档前过滤秘密材料。

## A.5 仍未证明的事项

| 事项 | 状态 |
|---|---|
| 当前 exe 精确对应某个 Git commit | **UNKNOWN** |
| 当前 exe 由当前对象文件逐字节重链接得到 | **STRONG_CANDIDATE** |
| `next` 由某次具体人工 copy 操作产生 | **STRONG_CANDIDATE** |
| 启动脚本实际运行时会成功进入 `CS_PRIMED` / `CS_ACTIVE` | **NOT_OBSERVED** |
| 当前客户端能接收并解析该 exe 的 gamestate/snapshot | **NOT_OBSERVED** |
| 客户端 opcode 分派表 | **INSTRUMENTATION_BLOCKED**（见 09_C） |

## A.6 复算命令（只读）

```powershell
Get-FileHash -LiteralPath '...\dedicated\bin\codol_dedrun_next.exe' -Algorithm SHA256
Get-FileHash -LiteralPath '...\dedicated\bin\codol_dedrun.exe' -Algorithm SHA256
Get-FileHash -LiteralPath '...\dedicated\bin\START-CODOL-SERVER.cmd' -Algorithm SHA256
Get-Content -LiteralPath '...\dedicated\tools\BUILD-CODOL.ps1' | Select-Object -Index (19..86)
Get-Content -LiteralPath '...\dedicated\makefile' | Select-Object -Index (48..94)
Get-ChildItem -LiteralPath '...\dedicated\obj\codol' -Filter '*.o' | Select-Object Name,Length,LastWriteTimeUtc
Get-ChildItem -LiteralPath '...\dedicated\obj\codol' -Filter '*.d' | Select-String -Pattern 'src[\\/]'
```

二进制字符串复算只做只读 `ReadAllBytes` + ASCII 搜索，不执行 exe。