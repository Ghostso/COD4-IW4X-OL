# CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043

**任务:** 对 040/041/042 静态证据开展只读、可复现的独立审计,并建立六方交叉验证矩阵与服务器开工问题账本。
**日期:** 2026-10-13 (Asia/Shanghai)
**性质:** 只读静态分析。未启动游戏/服务器;无动态调试/注入/hook/运行期内存转储;
未修改原始 EXE/DLL/恢复镜像/FREEZE-005/正式服务器源码;**未改写 040/041/042 既有交付物**。

---

## 一句话结论

042 的三处解码器结论(`0x87A890`/`0x87C110`/`0x87D5A0`)**经独立反汇编复核基本成立**,
但存在**必须记录的勘误**(见 `10_CORRECTION_LOG.md`);`0x85E6F0` 的 TQOS 归因**需重新收紧**
(证据不足以排除业务层,见 03)。**接收点(recv/socket)在现有材料下无法闭合 → BLOCKED**。
六方矩阵仅达到**原语级**可比;**服务器尚不满足开工准入**,A 类阻断项见 `07`。

## 判定口径

`CONFIRMED`(机器码/数据直接) · `CROSS_VALIDATED`(≥2 独立证据源一致) · `INFERRED`(有据推断) ·
`UNKNOWN`(证据不足) · `BLOCKED`(保护区/覆盖缺口)。

## 交付物

| 文件 | 内容 |
|---|---|
| `01_SAMPLE_IDENTITY_AUDIT.md` | 样本身份、地址约定、镜像对应与覆盖、历史矛盾 |
| `02_DECODER_INSTRUCTION_AUDIT.md` | `0x87A890/0x87C110/0x87D5A0` 指令级审计 |
| `03_CALLER_AND_DATAFLOW_AUDIT.md` | 调用链/数据流审计 + TQOS 复核 |
| `04_IMAGE_COVERAGE_AND_BLOCKERS.md` | 镜像覆盖缺口与阻断边清单 |
| `05_SIX_WAY_CROSS_VALIDATION_MATRIX.tsv` | 六方对比矩阵(六对象) |
| `06_PROTOCOL_EVIDENCE_MATRIX.tsv` | 协议维度证据矩阵 |
| `07_SERVER_READINESS_ISSUE_LEDGER.tsv` | 服务器开工问题账本(A/B/C 类) |
| `08_HYPOTHESIS_AND_CONTRADICTION_LEDGER.md` | 竞争假设与矛盾账本 |
| `09_NEXT_ACTION_DECISION.md` | 下一步决策 |
| `10_CORRECTION_LOG.md` | 勘误记录 |
| `TEST_AND_VALIDATION_RESULTS.md` | 自校验结果 |
| `SHA256SUMS.txt` / `FILE_HASH_MANIFEST.tsv` | 完整性校验 |
| `evidence/` / `scripts/` | 证据与只读脚本 |
