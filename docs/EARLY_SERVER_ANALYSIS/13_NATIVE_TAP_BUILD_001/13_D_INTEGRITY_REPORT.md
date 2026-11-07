# 13 — D：完整性与隔离报告

> 任务：`EARLY-NATIVE-TAP-BUILD-001`
> 边界：只读核验、隔离副本清单、候选审查；**未应用补丁到实验副本、未编译、未运行、未注入、未导出秘密材料**。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## D.0 结论

| 验收问题 | 结论 | 状态 |
|---|---|---|
| 实验副本是否与原始源码清单一致，除明确记录的改动外？ | 3726/3726 纳入文件 SHA-256 匹配，0 差异 | **CONFIRMED** |
| 原始源码、原始二进制、既有报告、大厅基线是否被修改？ | 本轮未修改 | **CONFIRMED（本轮边界内）** |
| 候选补丁是否已应用到副本？ | 未应用；`experiment_copy/src/n3_observer.*` 不存在 | **CONFIRMED** |
| 是否启动过客户端/服务端/launcher？ | 未启动 | **CONFIRMED（本轮操作记录）** |
| 是否执行过构建？ | 未执行 | **NOT_OBSERVED** |
| 是否产生候选二进制？ | 无 | **NOT_OBSERVED** |
| 候选 diff 能否干净应用（一次性临时副本）？ | `git apply --check` 通过，5 个文件 | **CONFIRMED（apply-check）** |
| 候选代码是否编译过？ | 未编译（工具链缺失） | **INSTRUMENTATION_BLOCKED** |
| 是否导出认证秘密？ | 未读取、未导出 | **CONFIRMED（本轮边界内）** |

## D.1 隔离副本基线

实验副本：

`D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\experiment_copy`

清单：

`D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\logs\experiment_copy_manifest.csv`

| 项 | 值 |
|---|---:|
| 纳入文件数 | 3726 |
| 纳入总字节数 | 174,976,245 |
| 原始/副本逐文件 SHA-256 匹配 | 3726/3726 |
| 不匹配 | 0 |
| 副本缺失 | 0 |
| 清单 SHA-256 | `C8745A2651A66C0D2C7F2AB012F205914F34E7B14641E76E399272484DC4D607` |

排除项：

- `.git`
- `bin\home`
- `obj`
- `dis`
- `pbsv_exec`
- `scriptdocumentation`
- `wiki`
- `.github`

排除理由见 `13_A_SOURCE_AND_BASELINE.md:75-80`。`bin\home` 被排除以避免复制可能包含会话材料或运行时状态的目录。

## D.2 原始树关键文件复核

本节只计算 SHA-256；未读取或输出秘密材料。

| 文件 | 字节数 | SHA-256 | 副本匹配 |
|---|---:|---|---|
| `makefile` | 50,570 | `FEFF456D713ED926A48B4DACE6B0DD8B81F30B757F2B263975E314369A9C8703` | **是** |
| `tools\BUILD-CODOL.ps1` | 3,625 | `6EAB7B2759A9A2A276AF708F28715753EB503ED2DA4C997CB5B90E5E7FC79BB4` | **是** |
| `src\sv_main.c` | 219,831 | `4E9AC58B85FF52325AB5039050969D155DD9BC48F2218145DF8C9B9D0F4A1E7C` | **是** |
| `src\sv_client.c` | 119,801 | `C793898743682709A1BFEF82A297EE6895C87A6E76F83B1222A5FBDD250202B4` | **是** |
| `src\sv_snapshot.c` | 102,448 | `D6C182B177D2A07FA7A74C5E97E0013F1F147EF4F8812E8A24C2983793597172` | **是** |
| `src\sv_net_chan.c` | 5,664 | `A11DD2FF663C64D53165488F7323E003D6B4DB2CD851A7F07A9DB8C7CA2258EA` | **是** |
| `src\common.c` | 37,462 | `E53DAB6428C2E196E873FE9C9662B44E970731CF3958BC251F60612ECCE0BD0F` | **是** |
| `src\msg.h` | 未另行复算 | `1712307615C4510547412348314A6021C4656C05C7DF8728A624EC11CDB8FA9F` | **是** |
| `src\server.h` | 未另行复算 | `5B93068C0C08108BFBE051CE2D9B4890CE20CDE7A026488AFD14237A284A6C4A` | **是** |
| `src\codol\snapshot\codol_sv_state.c` | 7,243 | `D5C3B427240B3AC6F179BC08C1BDAA915FD223D7C09B930C060FA9432840ABB0` | **是** |
| `src\codol\snapshot\codol_snapshot.c` | 3,396 | `E8E1677F0250CCB294A4A9DA9F36D34874BF671C2BA05CBA04A4AA181E589577` | **是** |
| `bin\codol_dedrun.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` | **是** |
| `bin\codol_dedrun_next.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` | **是** |
| `bin\START-CODOL-SERVER.cmd` | 12,116 | `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` | **是** |

`codol_dedrun.exe` 与 `codol_dedrun_next.exe` 字节相同；这只证明两者一致，不证明它们与当前源码精确同一 commit。源码与二进制的精确对应关系仍为 **STRONG_CANDIDATE / UNKNOWN（精确 commit 层）**。

## D.3 候选文件状态

候选文件位于：

`D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\13_NATIVE_TAP_BUILD_001\patch_candidates`

| 文件 | 字节数 | SHA-256 | 状态 |
|---|---:|---|---|
| `n3_observer.c` | 见 `13_CHECKSUMS.txt` | `E4E126A40CEF648377A248CC544E5095EF79169D341EDABD62149ABD8DDEE338` | 审查草案（`#ifdef CODOL_SERVER` 包裹；`wire_byte0`/`segment_opcode=unknown`） |
| `n3_observer.h` | 见 `13_CHECKSUMS.txt` | `2680625D723E56504B1C9DFAB470F3771A7F0ED7C6AD5C6B8A5D2B023E44786D` | 审查草案（直接 `#include "msg.h"`，无重复 typedef） |
| `n3_hooks.diff` | 见 `13_CHECKSUMS.txt` | `D564A17ECDC35D032187904FBA93E913B29EBBCBC97CFE023E92DC4AD565B788` | 审查草案（单文件 unified diff，5 文件，apply-check 通过） |
| `n3_sv_snapshot_hook.diff` | 58 | `C1D9FEA6AE59F82197775B3CD7F705835739188536449312645309BA5D632299` | **SUPERSEDED** |

核验：

- `experiment_copy/src/n3_observer.c`：不存在；
- `experiment_copy/src/n3_observer.h`：不存在；
- 因此候选代码未进入实验副本源码树；
- 没有应用补丁到 `experiment_copy`；
- 没有编译；
- 没有生成 `obj/codol/n3_observer.o`；
- 没有生成新的 `bin/codol_dedrun.exe`。

> 注：为验证 diff 可应用性，本轮在 `%TEMP%` 下创建了**一次性临时副本**，仅复制 `common.c`、`sv_client.c`、`sv_snapshot.c` 三个待改文件并执行 `git apply --check`。该临时目录不属于实验副本，不参与构建，不改变任何原始文件或 `experiment_copy`。

## D.4 未执行操作清单

本轮未执行：

- 启动 `codol_dedrun_next.exe`；
- 启动任何客户端或 launcher；
- 注入进程、附加调试器；
- 运行 `.cmd`、`.ps1` 或未知脚本；
- 应用补丁到 `experiment_copy`；
- 编译；
- 修改原始样本；
- 覆盖既有报告；
- 修改可进入大厅的基线；
- 导出认证密钥、私钥、token 或完整会话凭据；
- 读取或哈希 `securitykey.bin`、私钥、认证 token 等禁止材料。

## D.5 进程检查

只读进程名检查未发现 CODOL 客户端、服务端或 launcher 相关进程处于运行状态。未启动任何进程。

## D.6 完整性裁决

**原始树、既有报告与可进入大厅基线在本轮边界内保持未修改；隔离副本与纳入清单一致；候选补丁未应用到实验副本。**

已满足：

- 候选 diff 已在一次性临时副本上通过 `git apply --check`（5 文件）；
- 候选头文件类型自洽性经静态审查修正。

仍未满足：

- 候选代码未编译（工具链缺失，见 `13_C`）；
- 未构建候选二进制；
- 运行时无扰动为 **NOT_OBSERVED**；
- 内部 gamestate/snapshot opcode 边界仍不能仅靠 N-3 整包观测确定。