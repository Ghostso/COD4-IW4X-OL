# TEST_AND_VALIDATION_RESULTS

**镜像:** S-IMG `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`
**日期:** 2026-10-13 (Asia/Shanghai)

## 1. 独立校验项

| # | 校验 | 结果 | 证据 |
|---|---|---|---|
| 1 | input S-IMG sha256 | **PASS** | `D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` |
| 2 | input S-DLL sha256 | **PASS** | `D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll` |
| 3 | input S-EXE sha256 | **PASS** | `D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe` |
| 4 | deliverable present: 00_INDEX.md | **PASS** | `` |
| 5 | deliverable present: 01_SAMPLE_SCOPE_AND_HASHES.md | **PASS** | `` |
| 6 | deliverable present: 02_DECODER_TYPE_DOMAIN.tsv | **PASS** | `` |
| 7 | deliverable present: 03_DECODER_CONTROL_FLOW.md | **PASS** | `` |
| 8 | deliverable present: 04_INDIRECT_CALL_SCAN.tsv | **PASS** | `` |
| 9 | deliverable present: 05_FUNCTION_POINTER_CANDIDATES.tsv | **PASS** | `` |
| 10 | deliverable present: 06_BLOCKER_REASSESSMENT.tsv | **PASS** | `` |
| 11 | deliverable present: 07_RUNTIME_EVIDENCE_NECESSITY.md | **PASS** | `` |
| 12 | deliverable present: 08_NEXT_ACTION_DECISION.md | **PASS** | `` |
| 13 | deliverable present: 09_CORRECTION_LOG.md | **PASS** | `` |
| 14 | deliverable present: TEST_AND_VALIDATION_RESULTS.md | **PASS** | `` |
| 15 | deliverable present: SHA256SUMS.txt | **PASS** | `` |
| 16 | deliverable present: FILE_HASH_MANIFEST.tsv | **PASS** | `` |
| 17 | TSV header+rectangular: 02_DECODER_TYPE_DOMAIN.tsv | **PASS** | `15 cols / 40 rows` |
| 18 | TSV header+rectangular: 04_INDIRECT_CALL_SCAN.tsv | **PASS** | `9 cols / 41922 rows` |
| 19 | TSV header+rectangular: 05_FUNCTION_POINTER_CANDIDATES.tsv | **PASS** | `13 cols / 61 rows` |
| 20 | TSV header+rectangular: 06_BLOCKER_REASSESSMENT.tsv | **PASS** | `9 cols / 7 rows` |
| 21 | 06 covers BE-01..BE-07 | **PASS** | `['BE-01', 'BE-02', 'BE-03', 'BE-04', 'BE-05', 'BE-06', 'BE-07']` |
| 22 | 08 states a single decision | **PASS** | `` |
| 23 | E8 callers 0x87C110 == [0x85D49D] | **PASS** | `['85d49d']` |
| 24 | E8 callers 0x87D5A0 == 4 sites | **PASS** | `['85d3db', '85d418', '85d9b5', '85d9f7']` |
| 25 | E8 callers 0x87EDB0 == [0x87C9B7] | **PASS** | `['87c9b7']` |
| 26 | 043 deliverables unmodified (re-hash 043 manifest) | **PASS** | `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-EVIDENCE-AUDIT-043\SHA256SUMS.txt` |

## 2. 覆盖范围与算法(可复现)

- Phase A: `scripts/a01_identity.py`(哈希 / 节区表 / 约定探测 / E8 目标扫描 / 12 份镜像盘点)。
- Phase B: `scripts/_cfg.py` + `b01_cfg.py`(递归下降 CFG)+ `b02_types.py`(字段/比较/间接提取)。
- Phase C: `scripts/c01_indirect.py`(PASS-A 线性扫描 + PASS-B 覆盖缺口扫描;union)+ `c02_focus.py`(跳表/近邻寄存器间接)。
- Phase E: `scripts/e01_alt_images.py` / `e02_raw_copies.py`(跨镜像 IAT 可达性)。
- Phase D/交付: `scripts/d01_tables.py` / `g_docs.py` / `_mk_index.py` / `_mk_corr.py`。

## 3. 局限(明示,不掩盖)

1. 间接调用扫描只覆盖**已映射且存在于文件内**的节区 #0;缺失节区内的跳表**无法排除**。
2. `0x87xxxx` 区扫描到 12 处 `[reg*4+disp]` 候选表基址,**全部证伪**为乘 4 索引位移(见 `05`);
   这是**排除**性结论,不表示「不存在其它跳表」。
3. 「无引用」一律记作**未发现**,**不**等价于「无调用者」。
4. 类型域 `{0,1,21,22}` 只是**该字段在本函数内被显式比较**的值,不是协议完整类型枚举。
