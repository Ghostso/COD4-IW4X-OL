# 10 — C：隔离、副本、哈希核验与回滚（Isolation & Rollback）

> 任务：`EARLY-SERVER-TAP-PREFLIGHT-001`，只读审查与实验设计。
> 本轮不创建实验副本，不修改任何原始样本或可运行基线。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。

---

## C.0 一句话结论

后续若获另行授权进行运行实验，必须在**独立实验副本**中进行；原始 `CODOL-AlphaBuild By Antia` 树保持只读。原始样本、既有报告和当前可进入大厅的基线均不得覆盖。实验前后必须对允许纳入清单的可执行文件、源码和关键脚本做 SHA-256 核验；密钥文件和凭据文件不复制、不哈希、不落盘。

---

## C.1 目录规划

### C.1.1 原始样本（只读）

原始基线根：

`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia`

其中关键路径：

| 用途 | 原始路径 | 实验期间处理 |
|---|---|---|
| 原生服务端 | `...\CODOL_Server\dedicated\bin\codol_dedrun_next.exe` | 只读，不替换 |
| 服务端启动脚本 | `...\CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd` | 只读，不编辑 |
| 服务端源码 | `...\CODOL_Server\dedicated\src` | 只读，不编辑 |
| 客户端 | `...\CODOL_Client\codoMP_client_shipRetail.exe` | 只读，不替换 |
| 既有报告 | `D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001` | 只读，不覆盖 |
| 既有 tap 模块 | `...\CODOL_Server\lobby\demonware\wire_tap.py` | 只读；实验副本可复制 |
| 既有捕获 | `...\CODOL_Server\lobby\captures\wiretap-*.jsonl` | 只读，不覆盖 |

### C.1.2 实验副本（后续授权后创建）

建议独立根：

`D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\10_TAP_PREFLIGHT_001\_runtime_copy\`

建议结构：

```text
_runtime_copy\
  server\                # 服务端可执行文件、配置、脚本的副本
  client\                # 仅复制运行所需客户端文件；不复制用户秘密
  source_patch\          # 只在副本中保存候选源码补丁，禁止写入原始树
  captures\              # 仅本会话、限时保留的脱敏游戏层证据
  logs\                  # 服务端/客户端日志归档
  hashes_before.txt      # 实验前允许清单的 SHA-256
  hashes_after.txt       # 实验后允许清单的 SHA-256
  README.md              # 实验目的、授权范围、停止条件、清理步骤
```

命名建议使用时间戳和实验编号，例如 `run-YYYYMMDD-HHMMSS-TAP-PREFLIGHT-001`。不要在原始树内创建副本。

### C.1.3 不进入副本的内容

- `securitykey.bin` 原始内容；
- `c1_keys.bin` 原始内容；
- 私钥、证书私钥、长期会话密钥；
- 认证令牌、MAC、完整会话凭据；
- 含账号/XUID/真实 IP/完整 userinfo 的日志或配置，除非先做不可逆或本地化脱敏。

如实验需要密钥文件存在，应通过实验环境自身的受控配置提供，且不在报告中输出其内容或哈希。

---

## C.2 原始样本只读核验

### C.2.1 文件属性核验

实验前，对原始文件执行只读核验：

```powershell
$orig='D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia'
Get-Item -LiteralPath "$orig\CODOL_Server\dedicated\bin\codol_dedrun_next.exe",
  "$orig\CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd",
  "$orig\CODOL_Client\codoMP_client_shipRetail.exe" |
  Select-Object FullName,Length,Attributes,LastWriteTime
```

要求：

- `Attributes` 显示只读或由实验流程明确以只读方式挂载；
- 记录 `Length` 与 `LastWriteTime`；
- 实验前后 `Length` 和 `LastWriteTime` 不变，除非有明确、经授权的实验记录解释；
- 不通过“打开写入再关闭”来测试只读属性。

### C.2.2 哈希核验

以下哈希为本轮只读复核得到，作为实验前基线参考：

| 文件 | 大小（B） | SHA-256 |
|---|---:|---|
| `CODOL_Server\dedicated\bin\codol_dedrun_next.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `CODOL_Server\dedicated\bin\codol_dedrun.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| `CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd` | 12,116 | `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` |
| `CODOL_Server\lobby\demonware\wire_tap.py` | 12,408 | `5004CF5EB473F0B4C5D0D1256E06C465690983965882A6EDB885F83BF07FBF59` |
| `CODOL_Server\lobby\dw-capture.py` | 100,516 | `2D4EE954915C66DA874B1D400327775E8E60627D5C2D414FA742A74DB262D01E` |
| `CODOL_Server\lobby\docs\wire_interception.md` | 13,470 | `BB1F82F118DA9694ECE8ECF679495256A41423ECE50A6DD0BAA11AF279C61375` |
| `CODOL_Client\codoMP_client_shipRetail.exe` | 20,918,752 | `904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6` |

额外源码基线（仅用于实验前后核验）：

| 文件 | SHA-256 |
|---|---|
| `dedicated\src\sv_main.c` | `4E9AC58B85FF52325AB5039050969D155DD9BC48F2218145DF8C9B9D0F4A1E7C` |
| `dedicated\src\sv_snapshot.c` | `D6C182B177D2A07FA7A74C5E97E0013F1F147EF4F8812E8A24C2983793597172` |
| `dedicated\src\sv_net_chan.c` | `A11DD2FF663C64D53165488F7323E003D6B4DB2CD851A7F07A9DB8C7CA2258EA` |
| `dedicated\src\common.c` | `E53DAB6428C2E196E873FE9C9662B44E970731CF3958BC251F60612ECCE0BD0F` |
| `dedicated\src\qcommon.h` | `755DCD36E112800195CA779BD6938830A14F33212DE2EEEA25D69065EA5FF10E` |
| `dedicated\src\codol\snapshot\codol_sv_state.c` | `D5C3B427240B3AC6F179BC08C1BDAA915FD223D7C09B930C060FA9432840ABB0` |
| `dedicated\src\codol\snapshot\codol_configstrings.c` | `9D10C372792A05147EFBE8F1FAE819F9C34595DB32F3B0638781DF2AEEA7E3A9` |
| `dedicated\src\codol\snapshot\codol_snapshot.c` | `E8E1677F0250CCB294A4A9DA9F36D34874BF671C2BA05CBA04A4AA181E589577` |

复核命令（只读）：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath <文件路径>
```

### C.2.3 禁止哈希/复制的秘密文件

- `securitykey.bin`
- `c1_keys.bin`
- 任何私钥、证书私钥、长期会话密钥、认证令牌、MAC、完整凭据文件

原因：即使只记录哈希，也可能形成可关联的密钥指纹或促进秘密材料处理。实验如需验证“密钥是否变化”，只能使用运行日志中既有的不可逆 `key_fp()` 形式，且该日志本身不得包含原始密钥。

---

## C.3 实验前后哈希清单

### C.3.1 允许清单

实验副本创建后，`hashes_before.txt` 至少包含：

- 副本中的服务端可执行文件；
- 副本中的启动脚本；
- 副本中被修改或可能被构建影响的源码文件；
- 副本中的客户端可执行文件；
- 副本中的实验插桩脚本；
- 实验分析工具（只读工具也记录，便于复现）。

### C.3.2 实验后

`hashes_after.txt` 使用相同路径和算法生成。比较规则：

- 原始树文件：必须与 C.2.2 基线一致，除非实验前有明确授权记录。
- 实验副本中允许变化的文件：只允许出现在 `source_patch/`、构建产物和本实验明确列出的目标文件；变化必须逐项记录。
- 捕获/日志：单独计算哈希，但不与源码/可执行文件混在同一张“可执行基线”表中。

### C.3.3 核验命令模板

```powershell
$list = Get-Content -LiteralPath .\hashes_before.txt
# 逐行解析后对相同路径重新计算 SHA-256；只读比较，不自动覆盖。
```

不要使用“自动恢复”或“自动回滚”脚本；回滚必须人工审查目标路径。

---

## C.4 日志归档规则

- 服务端日志、客户端日志、捕获文件分别放在 `logs\server`、`logs\client`、`captures`。
- 每份日志记录生成时间、来源进程、SHA-256、保留期限。
- 日志中如出现账号、XUID、真实 IP、聊天文本、完整 userinfo 或秘密材料，先脱敏再归档。
- 客户端日志保留状态转换行和错误行；不必保留完整无关 UI 日志。
- 服务端日志保留与本次会话时间窗口相关的行；如日志含 rcon 密码或认证材料，必须过滤或截断。
- 不覆盖既有 `lobby\captures\wiretap-*.jsonl`；实验捕获使用新的会话文件和目录。

---

## C.5 回滚步骤

1. 停止实验副本中的客户端和服务端进程；若无法确认已停止，先停止实验，不继续下一步。
2. 对实验副本中的服务端、客户端、脚本和源码执行 `hashes_after.txt` 核验。
3. 将实验副本的源码补丁、构建产物、捕获和日志移入只读归档或按保留规则删除；不得写回原始树。
4. 对原始树执行 C.2.2 哈希核验，确认原始可执行文件、启动脚本、源码和客户端未变化。
5. 删除实验副本中的临时状态、缓存、运行目录和未脱敏日志；如实验需要保留，保留在实验目录并记录保留期限。
6. 记录回滚结果：时间、执行人、原始树哈希核验结果、实验副本清理结果、异常和未决项。
7. 如原始树任何哈希不匹配，立即停止实验、隔离实验副本、保留证据并报告；不得自动覆盖原始文件。

---

## C.6 停止条件（隔离/回滚相关）

出现以下任一情况即停止，不自动重试：

- 原始样本或可运行基线出现非预期文件改写、长度变化或哈希漂移。
- 无法唯一确认实验副本与原始树的边界。
- 插桩可能改变原始网络行为且无法隔离其影响。
- 捕获需要导出认证秘密或无法可靠过滤秘密材料。
- 服务端或客户端出现非预期崩溃、文件改写或基线漂移。
- 实际输出与静态协议账本不一致，且无法解释差异。

---

## C.7 本轮未做事项

- 未创建 `_runtime_copy` 或任何实验副本。
- 未启动客户端、服务端或 launcher。
- 未执行任何 `.cmd`、脚本或二进制。
- 未修改原始样本、既有报告或可运行基线。