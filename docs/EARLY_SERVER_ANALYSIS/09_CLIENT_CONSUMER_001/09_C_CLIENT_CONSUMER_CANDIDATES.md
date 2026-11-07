# 09 — C：客户端消费路径静态调查（Client Consumer Candidates）

> 任务：`EARLY-SERVER-CLIENT-CONSUMER-001` 任务 C。**修订版 REV2**（见文末 C.R 修订记录）。
> 边界：**只做静态分析**。不启动客户端/服务端，不执行 `.cmd`/未知脚本，不修改原始样本与既有报告，不进行补丁/反调试/反作弊绕过，不输出秘密材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 客户端样本：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe`
> SHA-256 `904436480938632A856B39DEA73FB94C9682B5A0EBF7FA619ECD5DD5475ED3B6`；20,918,752 B；x86；ImageBase `0x400000`；**FileVersion 1.1.1.13**（本轮独立复算）。
> 前置证据：`08_OFFLINE_002\OFFLINE_002_E_SERIALIZER_CLIENT_MAP.md`（本文件在其基础上做**分级分类**与**纠错**，不重复全量反编译）。

---

## C.0 一句话结论

- 客户端**确实内置** gamestate/configstrings/snapshot 的解析器与错误串（**CONFIRMED 存在**），且样本被 **VMProtect 加壳**（代码段全部改名 `nsn`、附加 `.vmp0` 段、导入表仅 `Kernel33.dll`）。
- **重要更正（REV2）**：加壳**并未**把全部网络代码虚拟化。参考文档 `lobby\docs\ERRORS.md`、`protocol_map.md` 引用的 client VA（`0x0049C586`、`0x0049C5E0`、`0x0049D95F`、`0x00497360`、`0x005A0131`、`0x005D8241`、`0x005D82BB` 等）在本样本中**字节可读、反汇编语义自洽**，与文档描述**逐条吻合**。→ 客户端**解密/解码/分派入口已可定位到函数级**（CONFIRMED 存在 + STRONG_CANDIDATE 语义），**不再是笼统的 INSTRUMENTATION_BLOCKED**。
- **重要更正（REV2）**：`console_mp*.log`（20 个轮转 + 主文件）与 `captures\wiretap-*.jsonl`（4 个）**在本机确实存在**；REV1 的“未找到”结论**错误**。日志记录了客户端从 `CA_SENDINGSTATS` 一路走到 `CA_ACTIVE` 的**真实消费过程**（对参考 Python 服务端 `127.0.0.1:17733`）。
- **重要更正（REV2）**：REV1 的字符串 VA 表把**文件偏移**当成了 VA。正确 VA = 文件偏移 + `0x401000`（本样本第二 `nsn` 段：VA `0x742000` / raw `0x741000`）。修正后**交叉引用不再为空**（如 `ignoring illegible message` → 1 处 `push`；`non-SNAPFLAG_BASELINE` → 1 处 `push`）。
- **仍未闭合**：客户端 opcode **分派表项**（`CL_ParseSnapshot` 无 E8/E9 直接调用者，其地址作为 4 字节指针也未找到）→ 分派经**间接跳转/函数指针/运行时构造**，该点 **INSTRUMENTATION_BLOCKED**。
- **仍未证明**：本仓库 CODOL 服务端序列化器的产出被**本客户端逐字节接受** → **NOT_OBSERVED**（日志证明的是“客户端能消费**参考实现**的服务端流”，不是“消费本仓库流”）。

---

## C.1 客户端 PE 结构与加壳证据（CONFIRMED）

来源：`08_OFFLINE_002\_evidence\client_xrefs.json` + 本轮独立复算 `_tools\probe_client_refva.py` / `_vamap.py`（pefile + capstone，只读）。

| 项 | 值 | 含义 |
|---|---|---|
| SHA-256 | `904436480938632A…5ED3B6` | 与 `08_OFFLINE_002` 一致 |
| 大小 | 20,918,752 B | — |
| 架构 | x86 / ImageBase `0x400000` | 32 位 |
| FileVersion | **1.1.1.13** | 与 `protocol_map.md:3` 头部 “Build: CODOL 1.1.1.13” **同一构建线** |
| ProductVersion | 0.0.0.550136 | InternalName `CoDOnline` |
| 代码段名 | **全部为 `nsn`**（非 `.text`） | 段名被改写 |
| 段布局 | `nsn` VA `0x1000`/raw `0x400`；`nsn` VA `0x742000`/raw `0x741000`；… | 字符串落在第二段（偏移↔RVA 差 `0x1000`） |
| 附加段 | `.vmp0`（VA `0x9610000`，vsize `0xc668`，raw `0x13c6800`） | **VMProtect 虚拟化段** |
| 导入表 | 仅 `Kernel33.dll` | 真实导入被加壳器隐藏 |

**VA↔文件偏移换算（本样本，第二段）**：`VA = 文件偏移 + 0x401000`。
例：`netchan_t established` 文件偏移 `0x8479AC` → VA `0xC489AC`（REV1 误写为 `0x8489AC`，那其实是**文件偏移**）。

**裁决**：加壳事实 **CONFIRMED**；但“加壳 = 全部网络代码不可静态读” **REFUTED**（见 C.5）。

---

## C.2 字符串 VA 修正表 + 交叉引用（本轮独立复算）

来源：`_evidence\client_string_xrefs.json`（`_tools\probe_client_string_xrefs.py`，正确 VA 的 4 字节指针全文件扫描 + 引用点反汇编）。

| 语义串 | 正确 VA | 命中数 | 引用点（site VA） | 引用点上下文 |
|---|---|---|---|---|
| `netchan_t established, getting gamestate` | `0xC489AC` | 2 | `0x004944D9`、`0x0049978B` | `push 0xC489AC`；`mov eax,0xC489AC; ret`（字符串表桩） |
| `Received gamestate from server, %d bytes` | `0xC49238` | 0 | — | 仅字符串存在（引用被间接化） |
| `CL_ParseGamestate: begin parse of gamestate` | `0xC49358` | 0 | — | 仅字符串存在 |
| `CL_ParseGamestate: bad command byte %d` | `0xC4939B` | 0 | — | 仅字符串存在 |
| `configStrings: %d  (%d percent const).` | `0xC49210` | 0 | — | 仅字符串存在 |
| `ignoring illegible message` | `0xC481D8` | 1 | `0x00497565` | `push 0xC481D8`（`CL_PacketEvent` 溢出回滚分支） |
| `G_FindConfigstringIndex: overflow` | `0xC5D13C` | 15 | `0x00543EA6`…`0x00570976` 等 | 各 `push 0xC5D13C`（索引上限检查，多为 `0x100`/`0x40`/`0x140`） |
| `CL_GetSnapshot: truncated %i entities to %i` | `0xC46370` | 1 | `0x0048706D` | `push 0x400; push ecx; push 0xC46370`（实体上限 0x400） |
| `We got a non-SNAPFLAG_BASELINE snap… Discarding packet` | `0xC48F70` | 1 | `0x0049D99D` | `push 0xC48F70`（`CL_ParseSnapshot` 内） |
| `EXE_AWAITINGGAMESTATE` | `0xC6B724` | 1 | `0x005F424D` | `push 0xC6B724` |
| `EXE_CONFIGSTRINGMISMATCH` | `0xC4933C` | 0 | — | 仅字符串存在 |

> 说明：`CL_ParseSnapshot: begin parse` / `bad command byte` / `configStrings:` / `EXE_CONFIGSTRINGMISMATCH` 的静态指针引用仍为 0 —— 不是“不存在”，而是这些串在**运行时被间接取址**（VMProtect 常见手法）。**不得**因此把这些字符串的宿主函数判为不存在。

---

## C.3 候选位置分级（任务 C 要求：区分证据类型）

对每个候选，按**证据强度**分层标注（同一位置可跨层）：

| # | 语义候选 | 字符串 / VA | 引用点 | 证据层级 | 状态 |
|---|---|---|---|---|---|
| C1 | netchan 建立→取 gamestate | `netchan_t established` @ `0xC489AC` | `0x4944D9`、`0x49978B` | 有控制流证据（`push`/`mov`) | **CANDIDATE** |
| C2 | 收到 gamestate（日志打印） | `Received gamestate…%d bytes` @ `0xC49238` | — | 只有字符串引用 | **STRONG_CANDIDATE（存在）** |
| C3 | gamestate 解码入口 | `CL_ParseGamestate: begin parse` @ `0xC49358` | — | 只有字符串引用 | **STRONG_CANDIDATE（存在）** |
| C4 | gamestate 坏命令分支 | `bad command byte %d` @ `0xC4939B` | — | 只有字符串引用 | **STRONG_CANDIDATE（存在）** |
| C5 | configstrings 统计 | `configStrings: %d (%d percent const)` @ `0xC49210` | — | 只有字符串引用 | **CANDIDATE** |
| C6 | configstring 索引溢出 | `G_FindConfigstringIndex: overflow` @ `0xC5D13C` | 15 处 | 有控制流证据 | **STRONG_CANDIDATE（存在）** |
| C7 | configstring 不匹配 | `EXE_CONFIGSTRINGMISMATCH` @ `0xC4933C` | — | 只有字符串引用 | **CANDIDATE** |
| C8 | 快照实体截断 | `CL_GetSnapshot: truncated` @ `0xC46370` | `0x48706D` | 有控制流证据 | **STRONG_CANDIDATE（存在）** |
| C9 | 非基线快照丢弃 | `non-SNAPFLAG_BASELINE … Discarding packet` @ `0xC48F70` | `0x49D99D` | 有控制流+数据流证据 | **STRONG_CANDIDATE** |
| C10 | 等待 gamestate 状态 | `EXE_AWAITINGGAMESTATE` @ `0xC6B724` | `0x5F424D` | 有控制流证据 | **CANDIDATE** |
| C11 | 网络消息事件入口 | `CL_PacketEvent` @ `0x00497360` | 3 调用者 | 有控制流+数据流证据 | **STRONG_CANDIDATE** |
| C12 | 入站解密 | `CL_Netchan_Decode` @ `0x0049C5E0` | `0x49754A` | 有控制流+数据流证据 | **STRONG_CANDIDATE** |
| C13 | 出站加密 | `CL_Netchan_Encode` @ `0x0049C586` | 0 | 有数据流证据 | **STRONG_CANDIDATE** |
| C14 | **快照解码入口** | `CL_ParseSnapshot` @ `0x0049D95F`（函数起始 `0x0049D800`） | **无 E8/E9 直接调用者** | 有控制流+数据流证据 | **STRONG_CANDIDATE（存在+语义）/ INSTRUMENTATION_BLOCKED（分派表）** |
| C15 | 快照状态过渡 | `CG_TransitionSnapshot` @ `0x0045D180` | `0x46BC3E`、`0x46D270`、`0x46D365` | 有控制流+数据流证据 | **STRONG_CANDIDATE** |
| C16 | nextNoDeltaEntity 自增 | `0x0049CA69` | `0x49CCE5`、`0x49CD91` | 有数据流证据 | **STRONG_CANDIDATE** |
| C17 | 消息读溢出标志置位 | `MSG_Read` overflow @ `0x005A0131` | — | 有数据流证据 | **STRONG_CANDIDATE** |

---

## C.4 客户端真实消费证据（CONFIRMED，来自 `console_mp*.log`）

来源：`…\CODOL_Client\main\console_mp*.log`（20 个轮转 + 主文件，本轮独立复算）。客户端连接 `127.0.0.1:17733`（**参考 Python 服务端 / lobby kit**，非本仓库原生 CODOL 服务端）。

### C.4.1 状态机（`console_mp-000.log`，行号为本轮复算）

```
4990: CA_CONNECTING -> CA_CHALLENGING (sending challenge packets to the server)
4991: challenge = -1457697
4992: CA_CHALLENGING -> CA_SENDINGSTATS (sending stats to the server)
4997: CA_SENDINGSTATS -> CA_CONNECTED (netchan_t established, getting gamestate)
4999: Received gamestate from server, 6691 bytes
5001: map:           mp_killhouse_sh
5002: type:          mp
5003: servercmd:     0
5005: cs checksum:   -1390536941
5007: CL_ParseGamestate: begin parse of gamestate
5008: configStrings: 870  (68 percent const).
5009: CL_ParseGamestate: begin wait on fast files
5010: CL_ParseGamestate: end wait on fast files
5011: CL_ParseGamestate: begin parse of gamestate
5012: CL_ServerIdChanged: serverId: 124418
5013: CL_ParseGamestate: restarting file system due to checksumFeed
5014: CL_ParseGamestate: comparing files with server
5015: CL_ParseGamestate: calling CL_DownloadsComplete
5016: CA_CONNECTED -> CA_LOADING (only during cgame initialization, never during main loop)
5029: CA_LOADING -> CA_PRIMED (got gamestate, waiting for first frame)
5030: oldMessageNum is 86, newSnap.messageNum is 118 - not clearing it because they overlap
5031: CA_PRIMED -> CA_ACTIVE (game views should be displayed)
```

### C.4.2 跨日志统计（本轮复算）

| 文件 | `CA_PRIMED -> CA_ACTIVE` | `Received gamestate` | `bad command byte` | `CL_GetSnapshot: truncated` | `CONFIGSTRINGMISMATCH` |
|---|---|---|---|---|---|
| `console_mp-000.log` | 2 | 2 | 0 | 0 | 0 |
| `console_mp-005.log` | 1 | 1 | 0 | 0 | 0 |
| `console_mp-008…018.log`（11 个） | 各 1 | 各 1 | 0 | 0 | 0 |
| 其余（001–004/006/007/019/主文件） | 0 | 0 | 0 | 0 | 0 |
| **合计** | **17 次到 ACTIVE** | **17** | **0** | **0** | **0** |

**裁决**：
- 客户端**具备**完整的 gamestate 消费与 `CS_PRIMED` 前状态转换能力 → **CONFIRMED（行为级）**。
- 全部日志**无** `bad command byte` / `CL_GetSnapshot: truncated` / `CONFIGSTRINGMISMATCH` / `AWAITINGGAMESTATE` → 参考实现的 gamestate+snapshot 流**被客户端无错误接受** → 对**参考实现**的兼容 **CONFIRMED**。
- 但这**不是**本仓库 CODOL 序列化器被逐字节接受的证明 → 本仓库↔本客户端互通 **NOT_OBSERVED**。

---

## C.5 参考文档引用 VA 的反汇编复算（本轮独立复算）

来源：`_evidence\client_refva_probe.json`、`client_decoder_va_probe.json`（`_tools\probe_client_refva.py`、`probe_client_decoder_va.py`，capstone，只读）。

| VA | 反汇编（首若干条） | 与 `lobby\docs\ERRORS.md` 描述 | 裁决 |
|---|---|---|---|
| `0x0049C586` `CL_Netchan_Encode` | `mov al,[ecx+0x40148]; xor al,[ecx+0x138]; xor al,[0x6D0D12C]` | key = `serverMessageSequence ^ challenge ^ serverId`（ERRORS.md:424-427） | **逐条吻合** |
| `0x0049C5E0` `CL_Netchan_Decode` | `mov eax,[0x16F8068]; xor eax,0x26F950CC; mov ecx,[eax+0x144]; and ecx,0xff; shl ecx,0xa; lea edx,[ecx+eax+0x148]` | `clc=*(u32*)0x016F8068^0x26F950CC`；reliableCommands base `clc+0x148` stride `0x400`（ERRORS.md:439-446） | **逐条吻合** |
| `0x005A0131` `MSG_Read` overflow | `mov dword ptr [edx],1; or eax,-1; ret` | `overflowed=1` 置位（ERRORS.md:402） | **吻合** |
| `0x0049755B` `CL_PacketEvent` 回滚 | `cmp dword ptr [ebx],0; je …; push 0xC481D8` | overflowed 检查 + “ignoring illegible message”（ERRORS.md:405-408） | **吻合** |
| `0x005D8241` | `mov byte ptr [edx+eax],1` | `svc_serverCommand==1`（ERRORS.md:394） | **吻合** |
| `0x005D82BB` / `0x005D8354` | `mov byte ptr [eax+ecx],5` | `svc_EOF==5`（ERRORS.md:393） | **吻合** |
| `0x0049D95F` `CL_ParseSnapshot` | `mov [ebx+0x336C],eax; test al,8; …; cmp dword ptr [0x6D36AB8],0` | snapFlags@`+0x336C`、`nextNoDeltaEntity@0x06D36AB8`（ERRORS.md:547-548） | **吻合** |
| `0x0049CA69` nextNoDeltaEntity++ | `add dword ptr [0x6D36AB8],eax` | `nextNoDeltaEntity` 自增（ERRORS.md:562） | **吻合** |
| `0x0045D180` `CG_TransitionSnapshot` | `push ebp; …; mov eax,[0x16F8068]; xor eax,0x26F950CC; …` | 每快照 memcpy 整个 playerstate（ERRORS.md:4687-4695） | **吻合** |

**裁决**：参考文档引用的 client VA **在本样本中可读且语义自洽** → 这些**不是**“巧合可读”，而是**同一构建线（1.1.1.13）的可执行代码**。因此：
- “客户端解密/解码/分派入口**存在**” → **CONFIRMED**。
- “上述 VA 的**语义**与文档一致” → **STRONG_CANDIDATE**（语义由反汇编+文档双重支持；未运行验证）。
- REV1 的“VA 语义 INSTRUMENTATION_BLOCKED”对**这些网络函数** → **REFUTED**。

---

## C.6 调用图（本轮 E8/E9 + 4 字节指针扫描）

来源：`_evidence\client_callxrefs.json`、`client_func_start.json`、`client_parser_ptr_refs.json`。

| 函数 | 起始 VA | 直接调用者（E8/E9） | 4 字节指针引用 |
|---|---|---|---|
| `CL_Netchan_Decode` | `0x0049C5E0` | `0x0049754A`（在 `CL_PacketEvent` 体内） | 0 |
| `CL_PacketEvent` | `0x00497360` | `0x595D6D`、`0x595DE6`、`0x595F36` | 1（文件偏移 `0x13DA0E7`，落在 `.vmp0`/数据区，非映射代码） |
| `CL_ParseSnapshot` | `0x0049D800` | **0**（唯一命中 `call 0x8312A7E` 落在加壳/非代码区，疑误报） | **0** |
| `nextNoDelta_inc` | `0x0049CA00` | `0x49CCE5`、`0x49CD91` | 0 |
| `CL_Netchan_Encode` | `0x0049C586` | 0 | 0 |
| `CG_TransitionSnapshot` | `0x0045D180` | `0x46BC3E`、`0x46D270`、`0x46D365` | 0 |

**裁决**：
- `CL_Netchan_Decode ← CL_PacketEvent ← (3 调用者)` 的**入站链闭合到函数级** → **CONFIRMED**。
- `CL_ParseSnapshot` **既无直接调用者、也无 4 字节指针引用** → 它经**间接分派（跳转表 / 函数指针 / 运行时构造表）**调用，而该表项**未在文件静态数据中找到**（可能被 VMProtect 加密或运行时构造）→ **INSTRUMENTATION_BLOCKED**（分派表）。

---

## C.7 跨构建线索（ol-mod，3.19.26.13）——REFUTED 作为直接证据

`D:\BaiduNetdiskDownload\使命召唤OL\_e1_regression\ol-mod-olfinal\`：`config\codol-game-dir.txt` → `D:\codo_3.19.26.13_fresh\CoD Online`（构建 **3.19.26.13**），**非**本轮审计客户端（**1.1.1.13**）。其 `sv_gamestate_mp.hpp:30-32` 定义 `ServerCommandSnapshot=0`、`ServerCommandGameState=3`、`ServerCommandConfigString=4`——gamestate/configstring 与我们的服务端 `2/3` **不同**（不同血缘）。其注释引用的 client VA（`0x0046D170` 等）在本客户端**大多反汇编为垃圾**。

**裁决**：ol-mod **REFUTED** 作为本客户端语义的直接证据；仅可作**结构蓝图**（不得引用其 RVA）。

---

## C.8 状态转换 / `CS_PRIMED` 静态调用关系

| 项 | 证据 | 等级 |
|---|---|---|
| `CS_PRIMED` 客户端常量 | 无字符串、无符号 | **UNKNOWN** |
| `CA_LOADING -> CA_PRIMED -> CA_ACTIVE` | `console_mp*.log`（17 次） | **CONFIRMED（行为级）** |
| “等待 gamestate”状态存在 | `EXE_AWAITINGGAMESTATE`（`0xC6B724`，xref `0x5F424D`） | **CANDIDATE** |
| 非基线首帧丢弃分支 | `0xC48F70`（xref `0x49D99D`，`nextNoDeltaEntity==0` 时丢弃） | **STRONG_CANDIDATE** |
| `CS_PRIMED` 转换点的**函数级**地址 | 未定位（分派间接化） | **INSTRUMENTATION_BLOCKED** |

> 行为级状态机 **CONFIRMED**；但“哪个函数写 `client->state = CS_PRIMED`”未静态闭合 → 保留 **INSTRUMENTATION_BLOCKED**。

---

## C.9 与服务端编码路径的对应（分级）

| 服务端写出（`09_A`） | 客户端候选消费点 | 对应证据 | 等级 |
|---|---|---|---|
| gamestate `0x02` | `CL_ParseGamestate` 串 `0xC49358` + 日志 `Received gamestate…6691 bytes` | 参考实现产出被客户端**实际接受**（日志），但非本仓库流 | **STRONG_CANDIDATE** |
| configstring 子流 `0x03` | configstring 表 + `G_FindConfigstringIndex` `0xC5D13C` + 日志 `configStrings: 870` | 客户端统计到 870 个 CS；语义一致 | **STRONG_CANDIDATE** |
| snapshot `0x00`（服务端侧） | `CL_ParseSnapshot` `0x0049D95F` | 客户端**存在**快照解析器（读 snapFlags@+0x336C）；**期望 opcode 未知** | **STRONG_CANDIDATE（存在）/ UNKNOWN（opcode 值）** |
| serverCommand `0x01` | `0x005D8241`（server half 实测 =1） | 与客户端 server half 常量一致 | **STRONG_CANDIDATE** |
| EOF `0x05` | `0x005D82BB`/`0x005D8354`（server half 实测 =5） | 与客户端 server half 常量一致 | **STRONG_CANDIDATE** |
| baseline flag8 | `non-SNAPFLAG_BASELINE … Discarding packet` `0xC48F70` | 服务端置 flag8；客户端丢弃非基线首帧 → **语义对齐** | **STRONG_CANDIDATE** |

> **重要限制**：以上“对应”多数建立在**语义名一致 + 参考实现被接受**上；**没有**任何一条建立了**本仓库流 ↔ 客户端**的逐字节或数据流级对应 → **NOT_OBSERVED**。

---

## C.10 静态盲区（必须标记）

| 盲区 | 证据 | 影响 |
|---|---|---|
| opcode 分派表项 | `CL_ParseSnapshot` 无 E8/E9 调用者、无 4 字节指针引用 | 无法闭合“首字节 opcode → 处理函数”映射 |
| 字符串间接引用 | `Received gamestate`/`begin parse`/`bad command byte`/`configStrings:` xref 为空 | 无法从引用点直接回溯宿主函数 |
| 运行时生成/解密代码 | `.vmp0` 段 + 非映射区的间接跳转 | 分派目标可能运行时构造 |
| 本仓库流未被客户端消费 | 日志证明的是**参考实现**被消费；无本仓库流样本 | 本仓库↔客户端互通 **NOT_OBSERVED** |

---

## C.11 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 客户端存在 gamestate 解析器（含坏命令/坏 clientNum 报错） | **CONFIRMED（字符串存在）** | `0xC49358/0xC4939B/0xC493B0` |
| 客户端存在 configstrings 表与索引分配 | **CONFIRMED（字符串存在）** | `0xC49210/0xC5D13C/0xC4933C` |
| 客户端存在 snapshot 解码 + 基线/实体上限逻辑 | **CONFIRMED（字符串存在）** | `0xC46370/0xC48F70` |
| 客户端**实际消费** gamestate 并到 `CA_ACTIVE` | **CONFIRMED（行为级）** | `console_mp*.log` 17 次 |
| 客户端解密/解码/入站链函数级定位 | **CONFIRMED（存在）** | `0x0049C5E0/0x00497360/0x0049C586` |
| 上述函数**语义**与参考文档一致 | **STRONG_CANDIDATE** | 反汇编 + `ERRORS.md` 双重 |
| 客户端 opcode **分派表** | **INSTRUMENTATION_BLOCKED** | 间接分派，表项未找到 |
| 本客户端能解析**本仓库** CODOL 序列化器产出 | **NOT_OBSERVED** | 无本仓库下行样本 |
| ol-mod 可作本客户端直接证据 | **REFUTED** | 构建号/哈希/反汇编均不同 |
| “加壳 = 全部网络代码不可静态读” | **REFUTED** | C.5 反汇编可读 |

---

## C.12 复算命令（只读）

```powershell
$t='D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\09_CLIENT_CONSUMER_001\_tools'
python "$t\probe_client_refva.py"           # -> _evidence\client_refva_probe.json
python "$t\probe_client_string_xrefs.py"    # -> _evidence\client_string_xrefs.json
python "$t\probe_client_decoder_va.py"      # -> _evidence\client_decoder_va_probe.json
python "$t\probe_client_callxrefs.py"       # -> _evidence\client_callxrefs.json
python "$t\probe_client_func_start.py"      # -> _evidence\client_func_start.json
# 客户端实测日志
$c='D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\main'
Get-Content -LiteralPath "$c\console_mp-000.log" | Select-Object -Skip 4989 -First 46
```

---

## C.R 修订记录（REV2，2026-10-11）

相对 REV1 的更正：

1. **日志/抓包存在性**：REV1 称 `console_mp.log` 与 `captures\*.jsonl` “未找到” → **错误**。两者均存在（20 个日志轮转 + 4 个 wiretap JSONL）。已新增 C.4。
2. **字符串 VA**：REV1 使用**文件偏移**当 VA（`0x8489ac` 等）→ 更正为真实 VA（`0xC489AC` 等，`+0x401000`）。已重写 C.2。
3. **交叉引用**：REV1 称 xref 为空 → 更正：修正 VA 后多处命中（`0xC481D8`×1、`0xC5D13C`×15、`0xC46370`×1、`0xC48F70`×1、`0xC6B724`×1、`0xC489AC`×2）。
4. **加壳裁决**：REV1 笼统判“函数级语义 INSTRUMENTATION_BLOCKED” → 更正：网络/解密/快照函数**可读且语义自洽**（C.5），仅**分派表**仍 blocked。
5. **构建线**：新增 FileVersion `1.1.1.13` 与 `protocol_map.md:3` 同线证据。
6. **双端对应**：从 REV1 的“全 UNKNOWN/NOT_OBSERVED”提升为“客户端侧 **STRONG_CANDIDATE/CONFIRMED**，本仓库↔客户端仍 **NOT_OBSERVED**”。

> 完整双端对应矩阵见 `09_D`，抓包必要性判断见 `09_E`。