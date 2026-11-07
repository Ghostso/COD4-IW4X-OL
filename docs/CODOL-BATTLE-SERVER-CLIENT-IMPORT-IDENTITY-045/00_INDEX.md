# CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045

**任务:** 最小导入证据核验(A) + 六方交叉验证矩阵启动(B)。
**前序:** 040 / 041 / 042 / 043 / 044。
**日期:** 2026-10-13 (Asia/Shanghai)。
**性质:** 只读静态分析。未启动游戏/服务器;无动态调试/注入/hook/内存转储;
未修改任何原始客户端、040–044 历史交付物、冻结基线或正式服务器源码。
新产物全部位于本目录。

---

## 一句话结论

**工作流 A 取得决定性突破:** 040–044 长期记为 BLOCKED 的读 API 身份问题,其根因是**地址约定错误**,
而非证据缺失。`0x0CA84E8` 是**绝对 VA**;正确换算 `file_off = VA - ImageBase = 0x8A84E8`,
**完全落在 `image_best.bin` 文件内**(文件长 `0xA65000`)。043/044 把它当作 RVA 去比对文件长度,
因而错误地得出"超出 EOF / 镜像未覆盖"。解析后:

- `[0x0CA84E8]` = **`select`**(ws2_32 序号 18)
- `[0x0CA84E4]` = **`recv`**  (ws2_32 序号 16)
- `[0x0CA853C]` = **`WSAGetLastError`**(序号 111)

因此 **H1 成立、H2 证否**:`0x87BE00` 是 **socket 接收原语(`select` 超时门控 + `recv`)**,
不是 `ReadFile`/重叠文件读。044 提出的"更像文件读"假设被**推翻**(其两条支持证据均被重新解释:
那个 `mov ecx,0x10624DD3; imul; sar 6` 魔数是 **`tv_sec = ms/1000`**(select 超时结构),
`0x2714`/`0x2733` 是 **WSA** 错误域 `WSAEINTR`/`WSAEWOULDBLOCK`,不是 Win32 等待错误)。

**工作流 B:** 六方矩阵已启动,仅使用**实际存在且身份明确**的证据;关系类型严格限于任务书限定集合;
相似函数名/消息编号/结构**一律不据此认定协议相同**。

## 判定口径

`CONFIRMED`(机器码/原始数据直接) · `CROSS_VALIDATED`(>=2 独立证据源一致) · `INFERRED`(有据推断) ·
`UNKNOWN`(证据不足) · `BLOCKED`(保护区/覆盖缺口) · `REJECTED`(有反证被推翻)。

## 交付物

| 文件 | 内容 |
|---|---|
| `01_SAMPLE_IDENTITY_AND_ADDRESS_MAPPING.md` | 三份样本身份、完整 SHA-256、PE 结构、地址约定与 VA/RVA 换算勘误 |
| `02_IMPORT_IDENTITY_HYPOTHESES.md` | `0x87BE00` H1–H4 逐项裁定 + 导入身份决定性证据 |
| `03_IO_PATH_EVIDENCE.tsv` | I/O 路径逐条证据(地址、字节、API、数据流、判定) |
| `04_SIX_WAY_ARCHITECTURE_MATRIX.tsv` | 六方架构对比矩阵(关系类型限定集) |
| `05_PROTOCOL_EVIDENCE_MATRIX.tsv` | 协议维度证据矩阵(11 维度 × 六方) |
| `06_CAUSAL_DIFFERENCE_ANALYSIS.md` | 因果差异分析:版本演化 vs 竞争性解释 |
| `07_SERVER_READINESS_ISSUE_LEDGER.tsv` | 服务器开工问题账本 + 每个 A 类阻断的关闭条件 |
| `08_NEXT_ACTION_DECISION.md` | 下一步决策(已择一) |
| `TEST_AND_VALIDATION_RESULTS.md` | 独立校验结果 |
| `SHA256SUMS.txt` / `FILE_HASH_MANIFEST.tsv` | 完整性校验(含输入样本 + 输出) |
| `evidence/` / `scripts/` | 原始证据转储与只读脚本 |

## 对历史交付物的处理

- 040–044 文件**一字未改**。
- 043 的 `10_CORRECTION_LOG.md` 与 044 的 `09_CORRECTION_LOG.md` **保留**;
  本任务新增 `08_NEXT_ACTION_DECISION.md` 中"勘误编号 045-C*"续记(不覆盖历史)。
- 044 的 BE-01 行"image not covering / beyond EOF"判定**被 045 推翻**,原因见 `01` §4。
