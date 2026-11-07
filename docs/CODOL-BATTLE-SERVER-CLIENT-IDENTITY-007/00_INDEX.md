# CODOL-BATTLE-SERVER-CLIENT-IDENTITY-007

**任务性质：** 目标客户端资产定位与身份验证（只读）。为后续 3.9.9.7 协议研究提供样本身份与证据归属。
**日期：** 2026-10-13（Asia/Shanghai）
**工作区根：** `D:\BaiduNetdiskDownload\使命召唤OL`
**正式工程：** `CODOL-Combat-Server-v0.1`（**本轮未修改**）
**冻结基线：** `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`，源码指纹 `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`（**本轮未修改**）
**代码修改：** 无。原始游戏文件、FREEZE-005、既有逆向证据均未改动。新产物仅写入本目录。

---

## 1. 首要结论（必须先读）

1. **本地不存在可确认属于 CODOL 3.9.9.7 的客户端映像。** 全工作区、`D:\BaiduNetdiskDownload` 全部客户端目录以及 `E:\CODOL_SANDBOX` 内，未发现任何 3.9.9.7 客户端。
2. 工作区实际存在的客户端二进制只有 **3 个版本族**：
   - **2.6.9.7**（`CODOL.NET\Game\CODOL_2.6.9.7`）：`CONFIRMED`，学习样本。
   - **3.3.3.3 族 / FileVersion 1649370**（`COD OL` 零售目录，7,841,344 B + 60,327,992 B 主 DLL）：`PROBABLE`，学习样本。
   - **1.1.1.13**（`CODOL.NET\Game\CODOL_1.1.1.13`）：`CONFIRMED`，学习样本。
3. **字符串 `3.9.9.7` 在整个工作区的文本资料中仅出现在既有任务报告的“目标版本”行**（10 个文件），从未出现在任何客户端二进制内（ASCII/UTF-16 命中数均为 0）。
4. **`3.3.3.3` 这一版本号也不是二进制自证**：`codoMP_client_shipRetail.exe` 与 `codoMP_client_shipRetailBase.dll` 内均无 `3.3.3.3` 字符串；其版本归属来自外部 ol-mod 仓库的运行目标与 FileVersion `1649370`，因此只能判为 `PROBABLE`。
5. 目标版本 **3.9.9.7 的 dump、抓包、函数级分析均不存在**。现有 dump / 抓包 / 反汇编全部归属于 1.1.1.13、3.3.3.3 族或 2.6.9.7。
6. 本轮**不修改**任何源码，不宣称客户端互通，不启动下一轮协议编码。

---

## 2. 执行过程

1. **强制目录检查**：枚举 `CODOL-Combat-Server-v0.1`、`CODOL-BATTLE-SERVER-PROTOCOL-BOUNDARY-006`、`CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`，读取既有 `00_INDEX.md`、`VERSION_ISOLATION.md`、`EVIDENCE_MATRIX.tsv`、`EVIDENCE_FILE_HASHES.tsv`、`BLOCKERS.md`、`14_SERVER_KNOWLEDGE_ATLAS_001\00_SAMPLE_MATRIX.md`。
2. **全工作区客户端检索**：按文件名 `codoMP_client*` 与 `out.exe` 递归检索，得到 13 个不同 SHA-256 组（含日志/注解等非 PE 文件）。
3. **库外候选检索**：在 `D:\BaiduNetdiskDownload\CODOL.NET`、`CODOL_2697_Launcher`、`CODOL-AlphaBuild_By_Antia(20261006)`、`CODOL-201506-2.6.9.7` 以及 `E:\CODOL_SANDBOX`（深度 ≤5）检索。
4. **逐文件身份核验**：对每个候选计算 SHA-256、读取 PE 头（Machine/Subsystem/ImageBase/EntryPoint/SizeOfImage/Linker/TimeDateStamp/节区/Characteristics）与 PE 版本资源。
5. **二进制内版本串核验**：对候选二进制直接做 ASCII 与 UTF-16 子串扫描（`3.9.9.7`、`3.3.3.3`、`2.6.9.7`、`1.1.1.13`、`1649370`）。
6. **证据关联检索**：检索 dump、`pktmon.pcapng`、反汇编注解、`vsd_callsite` 运行时镜像、ol-mod 审计与 `artifact_provenance.json`，逐一判定其归属版本。

---

## 3. 交付物清单

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文件：范围、过程、结论、交付物、未解决事项 |
| `CLIENT_CANDIDATES.tsv` | 9 条实际发现的候选记录（path/size/sha256/PE/版本资源/version_status/证据/备注） |
| `TARGET_IDENTITY_REPORT.md` | 是否存在 3.9.9.7 客户端及判定依据 |
| `EVIDENCE_ASSOCIATION.md` | 样本 ↔ 静态分析 / dump / 抓包 / 函数定位的已建立与未建立关联 |
| `BLOCKERS.md` | 缺失文件、证据类型及对后续协议研究的影响 |
| `SHA256SUMS.txt` | 本轮生成交付文件的哈希 |

---

## 4. 六项完成标准回答

1. **本地是否存在能确认属于 CODOL 3.9.9.7 的客户端映像？**
   **否。** 没有任何样本达到 `CONFIRMED`，连 `PROBABLE` 都不存在；所有实际样本均明确属于其他版本。

2. **如果存在，路径与 SHA-256？**
   不适用。**不存在** 3.9.9.7 候选，因此没有可报告的路径与哈希。

3. **版本归属由哪些直接证据支持？**
   对**其他版本**存在直接证据：2.6.9.7 由 PE FileVersion 资源 + 二进制内 `2.6.9.7` 串 + `manifest.json` 的 `version`/`original_exe_sha256` 三重支持；1.1.1.13 由 PE FileVersion 资源 + 二进制内 `1.1.1.13` 串支持。
   对 **3.9.9.7 没有任何直接证据**：无版本资源、无二进制串、无清单、无官方来源声明。

4. **是否存在与该映像可靠关联的 dump、抓包或函数级分析？**
   不存在“与该映像”的关联，因为没有该映像。
   现有 dump / 抓包 / 函数分析可分别关联到 **3.3.3.3 族**（`codoMP_client_shipRetailBase.image.bin`、ol-mod 反汇编、`pktmon.pcapng`）与 **2.6.9.7**（Demonware 静态分析、S-2697 服务端）；这些关联**不能**转写为 3.9.9.7 证据。

5. **如果不存在，缺少的决定性证据是什么？**
   缺少 3.9.9.7 客户端映像本体，以及由其派生的版本资源/清单、SHA-256 登记、与之一致的 dump、真实网络抓包与函数级锚点。详见 `BLOCKERS.md`。

6. **下一项最小工作是什么，为什么？**
   取得并核验**一个**可归属于 CODOL 3.9.9.7 的客户端映像（或具有明确来源说明 + 完整 SHA-256 的等价制品），随后在其上完成版本资源、入口与模块信息登记。
   原因：在没有目标样本之前，任何针对 2697 / 3.3.3.3 的字段、偏移、包长都只能标记为辅助学习证据，不能安全转化为目标版本实现，因此“补足目标样本身份”是唯一能解锁后续协议研究的最小前置工作。

---

## 5. 未解决事项

- 3.9.9.7 客户端样本缺失（BLK-007-01）。
- 3.9.9.7 版本清单 / 哈希登记缺失（BLK-007-02）。
- 3.9.9.7 真实连接抓包缺失（BLK-007-03）。
- 3.9.9.7 函数级定位缺失（BLK-007-04）。
- 3.3.3.3 的版本归属仍为 `PROBABLE`（缺少二进制自证或官方来源声明）。
- 2.6.9.7 恢复镜像与运行时映射等价性未验证（既有 BLOCKED，本轮不解除）。

---

## 6. 交付判定

本轮以“未修改代码的只读身份调查报告”完成。
明确结论：**本地没有可确认属于 CODOL 3.9.9.7 的客户端映像**，本轮不降低版本确认标准，也不以其他版本替代目标版本。完成后停止，不自行启动下一轮开发。
