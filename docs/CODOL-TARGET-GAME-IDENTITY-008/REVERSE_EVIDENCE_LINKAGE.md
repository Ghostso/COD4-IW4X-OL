# REVERSE_EVIDENCE_LINKAGE — 目标客户端与逆向证据的关联

**任务：** CODOL-TARGET-GAME-IDENTITY-008
**日期：** 2026-10-13（Asia/Shanghai）
**目标客户端：** `COD OL\codoMP_client_shipRetail.exe`（`36997674…`）+ `codoMP_client_shipRetailBase.dll`（`ef75220d…`）

---

## 0. 判定原则

- 关联必须基于**同一 SHA-256**、**模块名 + 基址 + 尺寸**、或**明确版本资源**。
- “同目录 / 同名 / 时间接近”不构成可靠关联。
- 服务端能写 ≠ 客户端能读；其他版本结论不得转写为目标版本事实。
- 无法关联时必须标记 `UNASSOCIATED`，不得拼接虚假完整链。

---

## 1. 关联总表

| 证据类别 | 关联对象 | 关联状态 | 依据 |
|---|---|---|---|
| 静态分析（PE 结构 / 网络承载者） | 目标主 DLL `ef75220d…` | **已建立** | `COD OL\docs\protocol.md`、`docs\game-net-hunt-report.md`、`docs\net-familyAB-report.md` 明确分析 `codoMP_client_shipRetailBase.dll`（60MB）的节表/导入/网络面 |
| 静态分析（脚本与数据流） | 目标主 DLL | **已建立** | `COD OL\scripts\*`（`entry_sentinel_family.py`、`tvm0*`、`ca8000_*`、`netcallers.py` 等）与输出（`ca8000_full_dump.txt`、`high_reuse_slot_disasm.txt` 等） |
| 运行时 dump | 目标主 DLL | **部分建立** | `run_codol_001\runs\vsd_callsite_20260929\codoMP_client_shipRetailBase.image.bin`（`7505132f…`，60,362,752 B）按模块名+尺寸+时间戳关联到 `ef75220d`；**非同哈希**（运行时版重定位） |
| 真实网络抓包 | 目标客户端族 | **已建立（族级）** | `run_codol_001\runs\*\pktmon.pcapng`（4 份）与 `CODOLServer\_subagents\pcap_report.md`；抓包来自该客户端族的大厅/入口环境 |
| 启动 / 加载链路 | 目标 EXE + DLL | **已建立** | `COD OL\ICH042_stdout.txt`（WinDbg）记录 `ModLoad` 目标 EXE 与 `...COD OL\codoMP_client_shipRetailBase.dll` |
| 初始化函数级定位 | 目标客户端 | **UNASSOCIATED** | 目标目录内无针对该实例的“连接→初始化”函数级闭合证据 |
| gamestate/configstring 消费入口 | 目标客户端 | **UNASSOCIATED** | `docs/protocol.md` 仅做 PE/网络承载者分析，未闭合 gamestate 消费 |
| snapshot 读取 / entity / delta 解码 | 目标客户端 | **UNASSOCIATED** | 目标目录内无 snapshot 消费链定位；`vsd_callsite` 探针仅验证 VSD 三方 DLL 字符串（`count=0`），不涉及 snapshot |

---

## 2. 已建立的关联（逐条展开）

### L-01 目标主 DLL ↔ `COD OL\docs\protocol.md`

- 关联对象：`ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20`（60,327,992 B）
- 证据：该文档标题即“分析对象：`codoMP_client_shipRetailBase.dll`（60 MB）”，并给出精确节表：
  `.text/.rdata/.data/.idata2/.rsrc2/.tls/.tvm0/.reloc`，`ImageBase 0x10000000`，`EntryRVA 0x0000149c`，`SizeOfImage 0x03991000`。
- 与本轮实测 PE 头**逐项一致** ⇒ **关联已建立**。
- 内容性质：PE 结构 + 网络承载者（libcurl / WS2_32 / Demonware 线索），**不含** gamestate/snapshot 消费链。

### L-02 目标主 DLL ↔ `COD OL\scripts\*`（该实例的自建逆向工程）

- 关联对象：同 L-01
- 证据：`scripts\` 内含 `entry_sentinel_family.py`、`tvm0iat.py`、`tvm0vm.py`、`ca8000_*`、`netcallers.py`、`rt_sockets.py` 等，以及对应的 `*.txt/*.csv/*.json` 输出（如 `ca8000_full_dump.txt`、`slot_ca812c_audit.txt`、`sockcensus.txt`）。
- 说明：这些是**针对本目标目录 DLL** 的静态/动态分析工程（目录内自建），是当前最贴近目标客户端的逆向资料。
- ⇒ **关联已建立**。

### L-03 目标主 DLL ↔ 运行时镜像 dump

- dump：`run_codol_001\runs\vsd_callsite_20260929\codoMP_client_shipRetailBase.image.bin`（`7505132f…`，60,362,752 B）
- 关联依据：同目录 `vsd_callsite.json` 记录 `module.name = codoMP_client_shipRetailBase.dll`、`module.size = 60362752`、`module.base = 0x55B70000`；`TimeDateStamp 2020-02-25` 与文件版 DLL 相同。
- 限制：dump 为运行时重定位镜像（比磁盘文件大 8,192 B），**SHA-256 不同**，属“同源”而非“同哈希”。
- ⇒ **关联已建立（同源运行时镜像）**，但**不是**目标版本的新鲜运行时 dump 用于 snapshot 分析。

### L-04 目标客户端族 ↔ 真实网络抓包

- 抓包：`run_codol_001\runs\{TCLS_DIR_20260924_220810, ENTRY_CAPTURE_ELEVATED_20260924_160326, ENTRY_CAPTURE_ELEVATED_20260925_013045, LOBBY_DEEP_20260924_181441}\pktmon.pcapng`
- 关联依据：`CODOLServer\_subagents\pcap_report.md` 记录这些为 CODOL 客户端大厅/入口会话。
- 限制：抓包是**族级**（该目标目录客户端的运行沙箱），未逐帧绑定到目标函数。
- ⇒ **关联已建立（族级）**。

### L-05 目标 EXE + DLL ↔ 启动/模块加载证据

- 证据：`COD OL\ICH042_stdout.txt`（WinDbg 10.0.29617.1000 x86）记录：
  - `ModLoad: 00400000 0ea59000   codoMP_client_shipRetail.exe`
  - `ModLoad: 58e70000 5c801000   ...\COD OL\codoMP_client_shipRetailBase.dll`
- 说明：证明目标 EXE 在运行期确实加载目标目录内的主 DLL。
- ⇒ **关联已建立**。

---

## 3. 未建立的关联（必须显式记录）

| 编号 | 未建立项 | 状态 | 缺口 |
|---|---|---|---|
| U-01 | 目标客户端 ↔ 初始化阶段函数级定位 | `UNASSOCIATED` | 无“连接建立→初始化状态机”的闭合反汇编 |
| U-02 | 目标客户端 ↔ gamestate 消费入口 | `UNASSOCIATED` | 无 `0x03/0x04` 消费函数定位 |
| U-03 | 目标客户端 ↔ configstring 消费 | `UNASSOCIATED` | 无 configstring body reader 定位 |
| U-04 | 目标客户端 ↔ snapshot 读取 / entity / delta | `UNASSOCIATED` | 目标目录无 snapshot 消费链定位 |
| U-05 | 目标客户端 ↔ 服务端写入链 | `UNASSOCIATED` | 服务端（S-2697 / FREEZE-005）证据属其他版本，不能跨用 |
| U-06 | 目标客户端 ↔ 逐帧抓包绑定 | `PARTIAL` | 有族级抓包，无“帧 → 客户端函数”绑定 |
| U-07 | 目标客户端 ↔ 完整初始化/进图闭环 | `NOT_RUN` | 本轮未运行客户端 |

> `vsd_callsite.json` 探针结果为 `count=0`（VSD DLL 字符串未命中），**不构成**任何 snapshot/初始化关联。

---

## 4. 关键反例（防止虚假拼接）

1. **不得**把 2.6.9.7 / C-2697-Rec 的 Demonware 链当作目标客户端证据——那是另一个版本族。
2. **不得**把 3.3.3.3 QA 构建（`0x57611E31`/`0x0C72A000`）的 RVA 套到目标实例（`0x6096930A`/`0x0E659000`）。
3. **不得**把 ol-mod 的 `out.exe`（1649370 去壳）RVA 当作目标**加壳**镜像的文件级字节证据——加壳镜像的静态字节不代表运行时映射。
4. **不得**把 FREEZE-005 服务端实现（来自 C-3333 参考链）称为目标客户端兼容实现。
5. **不得**把族级抓包的结果当作目标函数的逐帧证明。

---

## 5. 结论

- 目标客户端（`36997674…` EXE + `ef75220d…` DLL）与以下证据**可靠关联**：目标目录自建 PE/网络分析（`COD OL\docs`、`COD OL\scripts`）、运行时镜像 dump（同源）、族级真实抓包、模块加载日志。
- 目标客户端与 **初始化 / gamestate / configstring / snapshot** 的函数级消费链**尚未建立关联**。
- 因此当前**尚未具备**把这些网络证据转成目标协议字段的完整条件；但已具备继续追踪的**身份、模块与网络输入前提**。
