> 任务编号：`EARLY-NATIVE-TAP-RUN-001`
> 裁决：**NO-GO**
> 执行状态：**NOT_EXECUTED**
> 本文件不包含运行证据、捕获载荷、客户端状态或互通结论。
> 状态词仅使用：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / NOT_OBSERVED / INSTRUMENTATION_BLOCKED / REFUTED。
# 12 — A：运行清单与实验前冻结

任务编号：`EARLY-NATIVE-TAP-RUN-001`

## A.0 裁决

**NO-GO / NOT_EXECUTED。** 未创建实验副本，未启动程序，未编译或应用补丁。

## A.1 已核验基线

以下为 2026-10-11 本轮只读复核值：

| 对象 | 完整路径 | 大小（B） | SHA-256 |
|---|---|---:|---|
| 原生服务端 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\bin\codol_dedrun_next.exe` | 8,469,493 | `28366AE992310BFE41D3C8975EC8DBC36E4DE202CE438C1266E1A09E335DD98A` |
| 启动脚本 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\bin\START-CODOL-SERVER.cmd` | 12,116 | `388C7F6F5BC91BD71D5EB039860B8297B826773C3D20D9CF3CBC902E43ECDE96` |
| 客户端 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe` | 20,918,752 | `904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6` |
| 11_F 设计裁决 | `D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\11_NATIVE_TAP_DESIGN_001\11_F_GO_NO_GO.md` | 8,972 | `7DF71518E7913C91DFCBC9A9D818B6B4FAC57A8A81D02AEEFF049B0A7F3AA338` |
| 11_E 隔离/回滚设计 | `D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\11_NATIVE_TAP_DESIGN_001\11_E_RISK_AND_ROLLBACK.md` | 9,171 | `762A9D02DDB1DE9C367F9B4BAE73550A47E8D811FD37DEE4E64C329EA519222B` |

服务端与客户端路径、版本和哈希已记录；实验未执行，因此没有实验副本哈希、构建标识、启动参数或运行日志。

## A.2 前置条件矩阵

| 条件 | 状态 | 证据 |
|---|---|---|
| 本轮运行授权 | **CONFIRMED**：任务文本已明确授权本轮运行验证 | 本任务文本；`11_F:115` 的“尚未授权”仅反映设计阶段状态 |
| `11_F` 条件满足 | **未满足** | `11_F:113-117` |
| 路径、版本、SHA-256 已记录 | **CONFIRMED（只读）** | 本文件 A.1 |
| 原始样本/既有报告保持只读 | **CONFIRMED（本轮未修改）** | 仅执行读取、清单和哈希计算 |
| 独立实验副本 | **NOT_CREATED** | `11_E:3-11` 明确本阶段不创建副本 |
| 插桩实现已单独审查 | **NOT_OBSERVED / INSTRUMENTATION_BLOCKED** | `11_F:113-114`；11 目录未发现已审查 native tap 实现 |
| 捕获不会导出秘密 | 设计已定义，运行验证未发生 | `11_C` 与 `11_E` 的设计；本轮未捕获 |

## A.3 执行边界

本轮未执行阶段 B（单次会话观测），未进入阶段 C（客户端接受核验），未产生阶段 D 的运行后冻结证据。

未修改：

- `codol_dedrun_next.exe`；
- `START-CODOL-SERVER.cmd`；
- `codoMP_client_shipRetail.exe`；
- `09_CLIENT_CONSUMER_001`、`10_TAP_PREFLIGHT_001`、`11_NATIVE_TAP_DESIGN_001` 中的既有交付物；
- 当前可进入大厅的基线。

