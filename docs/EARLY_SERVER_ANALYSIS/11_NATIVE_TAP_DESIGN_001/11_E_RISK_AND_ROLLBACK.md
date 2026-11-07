# 11 — E：风险、隔离与回滚

> 任务：`EARLY-NATIVE-TAP-DESIGN-001`，只读设计。
> 本文件不创建实验副本、不修改原始样本、不应用补丁、不运行任何程序。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

## E.0 结论先行

后续运行实验必须在**独立实验副本**中进行。原始 `CODOL-AlphaBuild By Antia` 树、`09_CLIENT_CONSUMER_001`、`10_TAP_PREFLIGHT_001` 和当前可进入大厅的基线均保持只读。任何观测代码都只能作为实验副本中的候选补丁，在单独审查、构建和授权后运行。

本阶段不生成可执行补丁，不创建副本，不修改原始文件。

## E.1 原始样本只读边界

| 对象 | 路径 | 实验期间要求 |
|---|---|---|
| 原生服务端 | `...\CODOL_Server\dedicated\bin\codol_dedrun_next.exe` | 只读，不替换、不 patch、不重命名 |
| 原生服务端副本 | `...\CODOL_Server\dedicated\bin\codol_dedrun.exe` | 只读，不覆盖 |
| 启动脚本 | `...\CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd` | 只读，不编辑 |
| 服务端源码 | `...\CODOL_Server\dedicated\src` | 只读，不在原树写补丁 |
| 构建脚本 | `...\CODOL_Server\dedicated\tools\BUILD-CODOL.ps1` | 只读 |
| Makefile | `...\CODOL_Server\dedicated\makefile` | 只读 |
| 客户端 | `...\CODOL_Client\codoMP_client_shipRetail.exe` | 只读，不替换、不 patch |
| 既有报告 | `...\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001` | 只读，不覆盖 |
| 既有报告 | `...\EARLY_SERVER_ANALYSIS\10_TAP_PREFLIGHT_001` | 只读，不覆盖 |
| 既有 tap 模块 | `...\CODOL_Server\lobby\demonware\wire_tap.py` | 只读；实验副本可复制 |
| 既有捕获 | `...\CODOL_Server\lobby\captures\wiretap-*.jsonl` | 只读，不覆盖 |

不得在原始树内创建 `_runtime_copy`、构建产物、日志、捕获或临时状态。

## E.2 实验副本目录规划

后续若获授权，建议在原始树之外创建：

```text
<isolated-root>\run-YYYYMMDD-HHMMSS-NATIVE-TAP-001\
  README.md                 # 目的、授权范围、停止条件、清理步骤
  source_copy\              # 只读源码副本
  server_copy\              # 服务端可执行文件、配置、脚本副本
  client_copy\              # 仅在确有需要时复制；不得改原始客户端
  patch_candidates\         # 候选补丁，仅保存在副本内
  build\                    # 副本内构建产物
  logs\
    server\
    client\
  captures\
    raw_temp\               # 临时内存/短期文件，优先不落盘
    redacted\               # 经脱敏后允许保留的证据
  hashes_before.txt
  hashes_after.txt
  cleanup_record.md
```

命名建议包含时间戳和实验编号，例如 `run-20261011-XXXXXX-NATIVE-TAP-001`。实验副本的根路径必须在实验前人工确认，不能是原始树或其子目录。

## E.3 实验前哈希核验

### E.3.1 允许清单

`hashes_before.txt` 至少包含：

- 副本中的服务端可执行文件；
- 副本中的启动脚本；
- 副本中可能被修改或受构建影响的源码文件；
- 副本中的客户端可执行文件（若使用客户端副本）；
- 副本中的观测代码或脚本；
- 实验配置中不含秘密的清单文件。

### E.3.2 当前只读基线哈希

以下为本轮复核值，用于实验前确认原始对象未漂移：

| 文件 | 大小（B） | SHA-256 |
|---|---:|---|
| `dedicated\bin\codol_dedrun_next.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `dedicated\bin\codol_dedrun.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `dedicated\bin\START-CODOL-SERVER.cmd` | 12,116 | `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` |
| `dedicated\tools\BUILD-CODOL.ps1` | 3,625 | `6EAB7B2759A9A2A276AF708F28715753EB503ED2DA4C997CB5B90E5E7FC79BB4` |
| `dedicated\makefile` | 50,570 | `FEFF456D713ED926A48B4DACE6B0DD8B81F30B757F2B263975E314369A9C8703` |
| `dedicated\src\sv_main.c` | 219,831 | `4E9AC58B85FF52325AB5039050969D155DD9BC48F2218145DF8C9B9D0F4A1E7C` |
| `dedicated\src\sv_snapshot.c` | 102,448 | `D6C182B177D2A07FA7A74C5E97E0013F1F147EF4F8812E8A24C2983793597172` |
| `dedicated\src\sv_net_chan.c` | 5,664 | `A11DD2FF663C64D53165488F7323E003D6B4DB2CD851A7F07A9DB8C7CA2258EA` |
| `dedicated\src\common.c` | 37,462 | `E53DAB6428C2E196E873FE9C9662B44E970731CF3958BC251F60612ECCE0BD0F` |
| `dedicated\src\qcommon.h` | 5,846 | `755DCD36E112800195CA779BD6938830A14F33212DE2EEEA25D69065EA5FF10E` |
| `dedicated\src\codol\snapshot\codol_sv_state.c` | 7,243 | `D5C3B427240B3AC6F179BC08C1BDAA915FD223D7C09B930C060FA9432840ABB0` |
| `dedicated\src\codol\snapshot\codol_configstrings.c` | 13,373 | `9D10C372792A05147EFBE8F1FAE819F9C34595DB32F3B0638781DF2AEEA7E3A9` |
| `dedicated\src\codol\snapshot\codol_snapshot.c` | 3,396 | `E8E1677F0250CCB294A4A9DA9F36D34874BF671C2BA05CBA04A4AA181E589577` |
| `...\CODOL_Client\codoMP_client_shipRetail.exe` | 20,918,752 | `904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6` |

### E.3.3 禁止哈希/复制的秘密文件

- `securitykey.bin` 或任何密钥文件；
- 私钥、证书私钥、认证令牌；
- `game_admissions.txt` 中可能含凭据的部分；
- profile、账号、XUID、真实 IP、完整 userinfo；
- rcon 密码或含密码的配置；
- 任何与目标会话无关的用户数据。

原因：即使只记录哈希，也可能形成可关联指纹或促进秘密材料处理。如实验需要确认密钥未变化，只能使用运行日志中既有的不可逆 `key_fp()` 形式；不得输出原始密钥或自建可关联指纹。

## E.4 实验后哈希与归档

- `hashes_after.txt` 对相同允许清单重新计算；
- 允许变化的文件只限实验副本中的补丁、构建产物和明确列出的目标文件；
- 原始树在实验后必须重新核验 E.3.2 的哈希；
- 捕获/日志单独计算 SHA-256，不与可执行基线混在一起；
- 若原始树任何哈希不匹配，立即停止、隔离实验副本、保留证据并报告；不得自动覆盖原始文件。

日志归档规则：

- 服务端日志、客户端日志、捕获文件分目录存放；
- 每份日志记录生成时间、来源进程、SHA-256、保留期限；
- 含账号、XUID、真实 IP、聊天文本、完整 userinfo 或秘密材料的行必须先脱敏；
- 客户端日志只保留状态转换和错误行；
- 服务端日志只保留目标会话时间窗口；rcon 输出必须过滤或截断。

## E.5 回滚步骤

1. 停止实验副本中的客户端和服务端进程；若无法确认已停止，先停止实验，不继续下一步。
2. 对实验副本中的服务端、客户端、脚本和源码执行 `hashes_after.txt` 核验。
3. 将实验副本的候选补丁、构建产物、捕获和日志移入只读归档，或按保留规则删除；不得写回原始树。
4. 对原始树执行 E.3.2 哈希核验，确认可执行文件、启动脚本、源码和客户端未变化。
5. 删除实验副本中的临时状态、缓存、运行目录和未脱敏日志；需要保留的必须记录保留期限。
6. 记录回滚结果：时间、执行人、原始树哈希核验结果、实验副本清理结果、异常和未决项。
7. 若原始树任何哈希不匹配，立即停止实验、隔离实验副本、保留证据并报告；不得自动覆盖原始文件。

不要使用“自动恢复”或“自动回滚”脚本；回滚必须人工审查目标路径。

## E.6 停止条件

出现以下任一情况即停止，不自动重试：

- 目标进程或插桩目标无法唯一确认；
- 插桩可能改变原始网络行为且无法隔离其影响；
- 捕获需要导出认证秘密或无法可靠过滤秘密材料；
- 服务端或客户端出现非预期崩溃、文件改写或基线漂移；
- 实际输出与静态协议账本不一致，无法解释差异；
- 捕获内容无法与会话、方向、序号或客户端状态建立可靠关联；
- 观测代码可能改变缓冲区、消息长度、发送顺序、返回值或错误处理；
- 实验副本与原始树边界无法唯一确认；
- 原始树任何哈希不匹配。

## E.7 最小风险控制

- 先元数据、后完整载荷；先 N-3 整包、后 N-1/N-2 段级交叉核对；不要先做 N-4。
- 短会话、单客户端、低风险地图；避免长时间高频 trace。
- 观测代码只读复制，不写回 `msg->data`、`msg->cursize`、`msg->bit`、`msg->overflowed`。
- 完整载荷优先临时内存处理；必须落盘时先过滤秘密材料并设置保留期限。
- 所有构建和运行都在实验副本中进行；原始树只读核验。
- 客户端侧不做补丁、不绕过保护、不注入、不反调试。

## E.8 本轮未做事项

- 未创建实验副本；
- 未生成、应用或编译任何补丁；
- 未启动客户端、服务端、launcher 或未知程序；
- 未注入进程或附加调试器；
- 未捕获、导出或保存任何秘密材料；
- 未修改原始样本、既有报告或可运行大厅基线。