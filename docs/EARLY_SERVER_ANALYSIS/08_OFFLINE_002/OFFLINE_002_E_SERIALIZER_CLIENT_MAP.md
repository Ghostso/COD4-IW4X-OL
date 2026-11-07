# OFFLINE_002 — E：战斗序列化器（客户端）定向地图

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §5（最高优先级，客户端侧）。
> 输入：只读。派生脚本/证据仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 客户端样本：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe`
> SHA-256：`904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6`；20,918,752B；x86；ImageBase `0x400000`。

---

## E.0 一句话结论

- 客户端**字符串证据充分**：gamestate 接收/解析、configstrings、snapshot 截断、baseline 等关键串**全部在样本中定位到**（CONFIRMED 存在）。
- 但样本为 **VMProtect 加壳**（`.vmp0` 段 + 全部代码段改名 `nsn`，导入表仅 `Kernel33.dll`）→ **运行时语义解码 INSTRUMENTATION_BLOCKED**；本轮只能做到"字符串存在 + 引用点 RVA 存在 + 引用点反汇编可读"。
- **`CS_PRIMED` 状态转换未直接定位**（客户端状态枚举常量无字符串）→ **UNKNOWN**。
- 服务端注释引用的 4 个客户端 VA（`0x49dd7e` / `0x49d9ce` / `0x5a0510` / `0x465f57` 等）**在样本中确实存在**且反汇编可读（CONFIRMED 存在；语义解读 INSTRUMENTATION_BLOCKED）。

---

## E.1 客户端网络接收与解密/校验边界（对照现有 C# 参考）

> 注意：下列 C# 是**从零重写的参考实现**（`CODOL-Combat-Server-v0.1`），**不是**早期原生服务端，也**未经**证明与真实客户端逐字节互通。它只提供"边界位置"的命名参考。

| 边界 | 参考实现位置 | 语义 |
|---|---|---|
| 报文接收入口 | `Engine\ClientLogic.cs:70 HandlePacket` | 先尝试 `CodolProtocol.TryReadData`（`:82`），失败再走 NAT/INIT/KeyExchange |
| 解密+MAC 校验 | `Codol\CodolProtocol.cs:192-244 TryReadData` | 头 `[0:2]type/ver [2:4]tag [4:6]seq [6:14]mac8 [14:16]len [16:]cipher` |
| 明文处理 | `Engine\ClientLogic.cs:193 HandlePlain` | OOB / stats / `gamestateupdate` 分支 |
| gamestate 推送 | `Engine\ClientLogic.cs:408 PumpGameState` | 4B seq + state（16..1100B），`i>=8` 逐字节 XOR mask `(seq^1)&0xFF` |
| snapshot 推送 | `Engine\ClientLogic.cs:432 PumpSnapshot` | `MotionSnapshot.Build`（`:458`）→ 4B seq + state + XOR mask |

- **证据等级**：这些是**参考实现的边界**，**非**客户端 EXE 的证据 → 对客户端只作 **CANDIDATE**（结构性参照），**不得**据此断言客户端真实路径。

---

## E.2 客户端字符串证据（CONFIRMED 存在）

来源：`_evidence\client_xrefs.json`（由 `_tools\probe_client_xrefs.py` 生成，只读扫描）。

| 语义 | 字符串 | VA | 存在 |
|---|---|---|---|
| netchan 建立→取 gamestate | `netchan_t established, getting gamestate` | `0x8489ac` | ✅ |
| 收到 gamestate | `Received gamestate from server, %d bytes` | `0x849238` | ✅ |
| gamestate 解析开始 | `CL_ParseGamestate: begin parse of gamestate` | `0x849358` | ✅ |
| gamestate 坏命令字节 | `CL_ParseGamestate: bad command byte %d` | `0x849388` | ✅ |
| gamestate 坏 clientNum | `CL_ParseGamestate: bad clientNum %i` | `0x8493b0` | ✅ |
| configstrings 统计 | `configStrings: %d  (%d percent const).` | `0x849210` | ✅ |
| 非基线快照丢弃 | `We got a non-SNAPFLAG_BASELINE snap when nextNoDeltaEntity is still 0.  Discarding packet` | `0x848f70` | ✅ |
| 快照实体截断 | `CL_GetSnapshot: truncated %i entities to %i` | `0x846370` | ✅ |
| configstring 溢出 | `G_FindConfigstringIndex: overflow...` | `0x85d13c` | ✅ |
| configstring 不匹配 | `EXE_CONFIGSTRINGMISMATCH` | `0x84933c` | ✅ |
| 等待 gamestate | `EXE_AWAITINGGAMESTATE` | `0x86b724` | ✅ |
| baseline | `baseline` | `0x74e784` | ✅ |

### E.2.1 引用点（xref）RVA
| 字符串 | 引用点 RVA | 说明 |
|---|---|---|
| `netchan_t established…` | `0x944d9`, `0x9978b` | 2 处引用 |
| `non-SNAPFLAG_BASELINE…` | `0x9d99e` | 与 `0x49d9ce` 同函数区（snapshot 决策） |
| `CL_GetSnapshot: truncated…` | `0x8706d` | 快照实体上限处理 |
| `EXE_AWAITINGGAMESTATE` | `0x1f424d` | 状态等待 |
| `baseline` | `0x3bd07a` | baseline 相关 |
| `G_FindConfigstringIndex: overflow…` | 15 处（`0x143ea6`…`0x273e4e`） | configstring 索引溢出检查点 |

- **`Received gamestate` / `CL_ParseGamestate: begin parse` / `bad command byte` / `configStrings: %d` / `EXE_CONFIGSTRINGMISMATCH` 的引用点为空**：这些串在**运行时/加壳后被间接引用**（VMProtect 常把字符串引用改写为解密后跳转），静态 xref 扫描不到 → **INSTRUMENTATION_BLOCKED**（不是"不存在"）。

---

## E.3 服务端注释引用的客户端 VA（CONFIRMED 存在）

来源：`_evidence\client_cited_rva_disasm.json`（由 `_tools\probe_client_cited.py` 生成）。

| 客户端 VA | RVA | 段 | 服务端引用它的位置 | 反汇编要点（存在性证据） |
|---|---|---|---|---|
| `0x49dd7e` | `0x9dd7e` | nsn | `codol_sv_snapshot.c:257`（flag-8 刷新基线） | `test byte ptr [ebx+0x336c], 8`（**仅 flag8 才刷新**） |
| `0x49d9ce` | `0x9d9ce` | nsn | `codol_sv_snapshot.c:266`（noDeltaSnapshot） | `mov dword ptr [ebp-4], 0x6d33710`（选持久 noDeltaSnapshot） |
| `0x5a0510` | `0x1a0510` | nsn | `codol_delta.c:1`（"C1.exe sub_5A0510 codecs"） | 函数入口存在（浮点/位运算体） |
| `0x465f57` | `0x65f57` | nsn | `codol_sv_state.c:111`（"2485"=maxclients） | `CG_ParseServerinfo` 区 |
| `0x465bc1` | `0x65bc1` | nsn | `codol_sv_state.c:112`（键 2492→hostname） | `call 0x8346291` 等 |
| `0x465c27` | `0x65c27` | nsn | `codol_sv_state.c:113`（键 2482→CG_Init animlist） | `mov [ebx+0x164], eax` |

- **证据等级**：VA 存在 + 反汇编字节可读 = **CONFIRMED**；"该 VA 确实实现服务端注释所述语义" = **INSTRUMENTATION_BLOCKED**（VMProtect 包裹，无法静态确证语义）。

---

## E.4 gamestate / configstrings / snapshot 解码路径（客户端）

| 环节 | 客户端证据 | 等级 |
|---|---|---|
| 网络消息接收入口 | 无直接符号；`netchan_t established, getting gamestate`（`0x8489ac`，xref `0x944d9`/`0x9978b`） | **CANDIDATE**（字符串存在，入口未闭合） |
| 解密与校验边界 | 无客户端符号证据；仅参考实现 `CodolProtocol.cs:192-244` | **UNKNOWN**（客户端侧） |
| gamestate 解码入口 | `CL_ParseGamestate: begin parse of gamestate`（`0x849358`）；`bad command byte %d`（`0x849388`）；`bad clientNum %i`（`0x8493b0`） | **STRONG_CANDIDATE**（解析器存在且会因坏命令/坏 clientNum 报错） |
| configstrings 写入路径 | `configStrings: %d (%d percent const).`（`0x849210`）；`G_FindConfigstringIndex: overflow`（`0x85d13c`，15 xref）；`EXE_CONFIGSTRINGMISMATCH`（`0x84933c`） | **STRONG_CANDIDATE**（configstring 表 + 索引分配 + 校验点存在） |
| snapshot 解码入口 | `CL_GetSnapshot: truncated %i entities to %i`（`0x846370`）；`non-SNAPFLAG_BASELINE … Discarding packet`（`0x848f70`）；`baseline`（`0x74e784`） | **STRONG_CANDIDATE**（快照解码 + 基线/实体上限逻辑存在） |
| 进入 `CS_PRIMED` 前后状态转换 | **无直接证据**（状态枚举常量无字符串） | **UNKNOWN** |
| 解码失败及后续处理 | `bad command byte %d` / `bad clientNum %i` / `Discarding packet` / `EXE_AWAITINGGAMESTATE` 表明存在失败分支 | **CANDIDATE**（失败分支存在，具体后续处理未闭合） |

### E.4.1 快照基线语义（与 D 报告呼应）
- 客户端串 `non-SNAPFLAG_BASELINE … Discarding packet`（`0x848f70`，xref `0x9d99e`）证明客户端**要求**首个快照为 `SNAPFLAG_BASELINE`，否则丢弃。
- 服务端 `codol_sv_snapshot.c:253-261` 在 `baseline_frame` 时 `flags |= 8u`（flag8=baseline）。→ 二者**语义上对齐**（服务端在需基线时置 flag8，客户端在非基线首帧时丢弃）。**等级：STRONG_CANDIDATE**（两串语义对应，但未逐字节联调）。

---

## E.5 静态分析盲区（必须标记）

| 盲区 | 证据 | 影响 |
|---|---|---|
| VMProtect 加壳 | 段表：`.vmp0`（`rawptr 0x13c6800`, vsize 0xc668）+ 所有代码段改名 `nsn`；导入表仅 `Kernel33.dll` | 无法静态确证函数语义 |
| 字符串间接引用 | `Received gamestate` / `begin parse` / `bad command byte` 等 xref 为空 | 无法从引用点回溯解码函数 |
| 运行时生成代码 | 服务端注释引用的 VA 均在 `nsn`（未加壳原代码区），但**调用它的解密后桩代码**不可静态读 | 无法闭合调用链 |
| 无客户端侧下行抓包 | 本机 `captures/*.jsonl` 0 载荷字节（见 A/B 报告） | 无法用真实数据校验解码 |

- **结论**：客户端序列化器/解码器的**存在性 CONFIRMED（字符串 + VA）**，但**逐字节格式与状态机 INSTRUMENTATION_BLOCKED**。若需闭合，最小任务是**带完整载荷的客户端抓包**或**动态调试**（均超出本轮只读范围）。

---

## E.6 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 客户端存在 gamestate 解析器（含坏命令/坏 clientNum 报错） | **CONFIRMED**（字符串存在） | `0x849358/0x849388/0x8493b0` |
| 客户端存在 configstrings 表与索引分配 | **CONFIRMED**（字符串存在） | `0x849210/0x85d13c/0x84933c` |
| 客户端存在 snapshot 解码 + 基线/实体上限逻辑 | **CONFIRMED**（字符串存在） | `0x846370/0x848f70/0x74e784` |
| 服务端注释引用的 4 个客户端 VA 存在 | **CONFIRMED** | `client_cited_rva_disasm.json` |
| 上述 VA 的语义（如 flag8 刷新基线） | **INSTRUMENTATION_BLOCKED** | VMProtect 包裹 |
| 客户端解密/MAC 校验边界 | **UNKNOWN** | 无符号证据 |
| `CS_PRIMED` 状态转换点 | **UNKNOWN** | 状态枚举无字符串 |
| 客户端能解析服务端 CoDOL 序列化器产出 | **NOT_OBSERVED** | 无下行抓包 |

---

## E.7 复算命令（只读）

```
python _tools\probe_client_xrefs.py     # 生成 client_xrefs.json（字符串 + xref）
python _tools\probe_client_cited.py     # 生成 client_cited_rva_disasm.json（VA 反汇编）
python _tools\probe_client_pe.py        # PE 头/段表（VMProtect 证据）
```
