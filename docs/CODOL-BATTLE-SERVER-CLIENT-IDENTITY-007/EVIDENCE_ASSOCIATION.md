# EVIDENCE_ASSOCIATION — 客户端样本与既有证据的关联

**任务：** CODOL-BATTLE-SERVER-CLIENT-IDENTITY-007
**日期：** 2026-10-13（Asia/Shanghai）
**性质：** 只读关联判定。未修改任何源码或原始证据。

---

## 0. 判定原则

- 关联必须建立在**同一文件 SHA-256**、**明确的模块名+基址+尺寸**、或**明确的版本资源**之上。
- 只有“目录相邻”“文件名相同”“时间接近”不构成可靠关联。
- 服务端能写 ≠ 客户端能读；其他版本的函数/抓包不得转写为目标版本证据。
- 无法建立可靠关联时，必须标记为 `UNASSOCIATED`，不得拼接成虚假完整链。

---

## 1. 关联总表

| 客户端样本 | SHA-256 | 静态分析 | 运行时 dump | 抓包 | 函数级定位 | 目标 3.9.9.7？ |
|---|---|---|---|---|---|---|
| C-3333 EXE (`codoMP_client_shipRetail.exe`) | `36997674…b537` | **已建立**（ol-mod 反汇编注解、`codol_server_function_matrix.json`） | 无（EXE 本体无 dump） | **已建立**（`pktmon.pcapng` 系列） | **已建立**（ol-mod RVA/函数矩阵，3.3.3.3 族） | 否 |
| C-3333 主 DLL (`codoMP_client_shipRetailBase.dll`) | `ef75220d…6a20` | **已建立**（`CLIENT-DEMONWARE-CODEC-KEYFLOW-001`、`CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001` 对其分析） | **已建立**（`codoMP_client_shipRetailBase.image.bin`，基址 0x55B70000） | 同上（间接，通过同族 EXE） | **已建立**（Demonware codec / 分派器函数） | 否 |
| C-2697 EXE (`CODOL_2.6.9.7\codoMP_client_shipRetail.exe`) | `35375404…4d6e1` | **部分建立**（服务端 2697 静态分析对应 C-2697 生态） | 无（无运行时解包镜像） | 无 2697 真实抓包 | **部分**（C-2697-Rec 上的 Demonware 链） | 否 |
| C-2697-Rec (`codol2697-static-candidate.bin`) | `24b4ef25…b97e4` | **已建立**（E06/E08/E09/E11/E12/E15/E20… 系列） | 非运行时（静态恢复镜像） | 无 | **已建立**（Demonware 分派器 0x6AC0C0、帧读取器 0x6ABBC0 等） | 否 |
| C-1113 EXE (`CODOL_1.1.1.13\...`) | `90443648…5ed3b6` | **已建立**（`EARLY_SERVER_ANALYSIS` 系列） | 无 | 无（早期样本） | **已建立**（早期 CoD4x 对照） | 否 |
| **3.9.9.7 目标** | **（无）** | **无** | **无** | **无** | **无** | — |

---

## 2. 已建立的关联（逐条）

### A-01 3.3.3.3 族 EXE ↔ 静态分析（ol-mod）

- 样本：`36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`（7,841,344 B）
- 关联依据：ol-mod 仓库（`_e1_regression\ol-mod-olfinal`）的 `tools/reverse/annotations/codoMP_client_shipRetail.exe.json`、`tools/reverse/catalogs/codol_server_function_matrix.json` 记录该构建为运行目标。
- 结论：**已建立**，但归属 3.3.3.3 族，非目标。
- 强度：中（依赖外部仓库声明；二进制内无 `3.3.3.3` 串，且被加壳）。

### A-02 3.3.3.3 族主 DLL ↔ 运行时镜像 dump

- 样本：`ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`（60,327,992 B）
- dump：`run_codol_001\runs\vsd_callsite_20260929\codoMP_client_shipRetailBase.image.bin`（60,362,752 B，`7505132f…`），`vsd_callsite.json` 记录模块名 `codoMP_client_shipRetailBase.dll`、基址 `0x55B70000`、尺寸 `60362752`。
- 关联依据：模块名 + 尺寸 + 相同 `TimeDateStamp 2020-02-25T12:29:09Z`。
- 结论：**已建立**（同族运行时镜像），非目标。
- 缺口：dump 为 rebase 后镜像（+8,192 B），二者 SHA-256 不同，属“同源运行时/磁盘”关系而非同哈希。

### A-03 3.3.3.3 族 ↔ 真实网络抓包

- 抓包：`run_codol_001\runs\*\pktmon.pcapng`（`TCLS_DIR_20260924_220810`、`ENTRY_CAPTURE_ELEVATED_20260924_160326`、`ENTRY_CAPTURE_ELEVATED_20260925_013045`、`LOBBY_DEEP_20260924_181441`）。
- 关联依据：`CODOLServer/_subagents/pcap_report.md` 记录了这些会话，属于大厅/入口链路，来自 3.3.3.3 族客户端环境。
- 结论：**已建立**（3.3.3.3 族），非目标。

### A-04 3.3.3.3 族主 DLL ↔ 函数级定位（Demonware）

- 样本：`ef75220d…6a20`
- 分析：`CLIENT-DEMONWARE-CODEC-KEYFLOW-001`、`CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001`、`CLIENT-DEMONWARE-BUNDLE-001`、E17–E27 系列。
- 结论：**已建立**（3.3.3.3 族），非目标。

### A-05 2.6.9.7 ↔ 静态恢复镜像与 Demonware 分析

- 样本：`35375404…4d6e1`（EXE，加壳）与 `24b4ef25…b97e4`（aplib 静态恢复镜像）。
- 关联依据：`manifest.json` `version=2.6.9.7` 与 EXE SHA 一致；恢复镜像 `TimeDateStamp 2015-05-05T10:18:04Z` 与 EXE 相同；E06/E08/E09/E11/E12/E15/E20 系列在其上定位。
- 结论：**已建立**（2.6.9.7），非目标。
- 缺口：恢复镜像**不是运行时 dump**，运行时映射等价性未证。

### A-06 1.1.1.13 ↔ 早期分析

- 样本：`90443648…5ed3b6`
- 分析：`EARLY_SERVER_ANALYSIS` 系列（含 `09_CLIENT_CONSUMER_001`）。
- 结论：**已建立**（1.1.1.13），非目标。

---

## 3. 未建立的关联（必须显式记录）

| 编号 | 未建立项 | 现状 |
|---|---|---|
| U-01 | 3.9.9.7 样本 ↔ 任何静态分析 | `UNASSOCIATED`（无目标样本） |
| U-02 | 3.9.9.7 样本 ↔ 任何运行时 dump | `UNASSOCIATED`（无目标样本） |
| U-03 | 3.9.9.7 样本 ↔ 任何真实抓包 | `UNASSOCIATED`（无目标样本） |
| U-04 | 3.9.9.7 样本 ↔ 初始化 / gamestate / configstring / snapshot 函数定位 | `UNASSOCIATED`（无目标样本） |
| U-05 | S-2697 服务端 snapshot writer ↔ C-2697 客户端 delta decoder | `BLOCKED`（既有结论：`0x6E060/0x6D340` 未连接） |
| U-06 | C-2697-Rec 静态恢复镜像 ↔ 运行时等价镜像 | `BLOCKED`（无运行时 dump） |
| U-07 | 3.3.3.3 族抓包 ↔ 3.3.3.3 客户端函数的逐帧对应 | `PARTIAL`（有抓包与反汇编，但无逐帧函数级绑定） |

---

## 4. 关键反例（防止虚假拼接）

1. **不能把 3.3.3.3 抓包当作 3.9.9.7 行为**：抓包来自 3.3.3.3 族环境，与目标版本无身份映射。
2. **不能把 C-2697-Rec 的 Demonware 链当作 3.9.9.7**：它是 2.6.9.7 的静态恢复镜像。
3. **不能把 ol-mod 的 RVA/函数矩阵当作 3.9.9.7 地址**：其构建为 FileVersion 1649370（3.3.3.3 族），且记录目标为 `out.exe`（本机不存在）。
4. **不能把服务端 writer 当作客户端 reader 证据**：S-2697 的 `_CODOL2697_WriteSnapshot` 链仅证明服务端写入，客户端消费未闭合。
5. **目录名 / 时间戳不构成关联**：`CODOL_2.6.9.7` 目录名只反映配置意图；本机存在大量同尺寸副本，必须按 SHA-256 区分。

---

## 5. 结论

- 现有全部静态分析、dump、抓包、函数定位均可归属到 **1.1.1.13 / 3.3.3.3 族 / 2.6.9.7**。
- **没有任何证据与 CODOL 3.9.9.7 建立关联**，因为目标样本本身不存在。
- 因此目标版本的“客户端消费链”仍完全空缺，后续协议研究不得引用其他版本结论作为目标事实。
