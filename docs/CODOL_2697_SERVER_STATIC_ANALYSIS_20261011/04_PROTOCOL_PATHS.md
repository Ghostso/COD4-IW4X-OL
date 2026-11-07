# 04 协议路径 / PROTOCOL PATHS

对象：NEW（2697）关键通信代码路径。方法：COFF 次要符号名 + Capstone 反汇编调用链（`_data\disasm_key2697.txt`、`_data\syms_NEW.json`）。
**纯静态**，未运行任何进程。VA = RVA + 0x400000（ImageBase）。

> 证据等级：**VERIFIED** / **STATIC-INFERENCE** / **NOT-OBSERVED** / **BLOCKED**。
> 重要提醒：本报告描述的是 **服务端发送/序列化逻辑**。**不得**据此推断客户端已能接收或互通（互通 = NOT-OBSERVED，见 05）。

---

## 0. 旧版 wire 常量（ground truth，来自旧包随附源码，VERIFIED）

文件：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_wire.h`

```
#define CODOL_PROTOCOL      187
#define CODOL_PORT          17733
#define CODOL_FRAGMENT_SIZE 1162u
#define CODOL_MAX_FRAGMENTS 128u
#define CODOL_MAX_MESSAGE   (CODOL_FRAGMENT_SIZE * CODOL_MAX_FRAGMENTS)
#define CODOL_SEQUENCE_MASK UINT32_C(0x1fffffff)
#define CODOL_FRAGMENT_BIT  UINT32_C(0x80000000)
#define CODOL_FORCE_ACK_BIT UINT32_C(0x40000000)
#define CODOL_ACK_BIT       UINT32_C(0x20000000)
```

文件：`...\dedicated\src\sv_snapshot.c`

```c
#ifdef CODOL_SERVER
  #define SV_WIRE_SERVERCOMMAND 1
  #define SV_WIRE_EOF 5
#else
  #define SV_WIRE_SERVERCOMMAND svc_serverCommand
  #define SV_WIRE_EOF svc_EOF
#endif
```

**VERIFIED：** 旧版 CODOL_SERVER wire 中 serverCommand = `0x01`、EOF = `0x05`。这是任务书"旧版消息类型"的源码级依据。

> 注意：`net_game_conf.h` 的 `svc_*` 枚举顺序（nop=0, gamestate=1, configstring=2, baseline=3, serverCommand=4, download=5, snapshot=6, EOF=7）**与 wire 实际字节不同**，不能混用；对 wire 应以 `codol_wire.h` / `SV_WIRE_*` 为准。

---

## 1. 旧协议写路径（三样本共有，VERIFIED）

以下旧封装在三样本都存在，且 **写字节常量一致**：

| 函数 | 写入字节 | 证据 |
|---|---|---|
| `_CODOL_WriteGamestate` | `2`（gamestate）、`5`（EOF） | VERIFIED（NEW rva 0xa86ec/0xa8769；OLD 0xa8e7c/0xa8ef9；1113 0x9cbfc/0x9cc79） |
| `_CODOL_WriteConfigstrings` | `3`、`5`、`2`、`5` | VERIFIED（NEW 0xa85b7/0xa8639；OLD 0xa8d50/0xa8dc7；1113 0x9cad0/0x9cb47） |
| `_CODOL_WriteSnapshotDeltaNumber` | `0`（snapshot）、`5`（EOF） | VERIFIED（NEW 0xbea0b/0xbeccd；OLD 0xb23cf/0xb25c7；1113 0xb1e97/0xb208f） |

**VERIFIED：** 旧版的 snapshot=0x00 / gamestate=0x02 / configstring=0x03 / EOF=0x05 在新样本的**旧通道**里保持不变。

---

## 2. 新增 2697 写通道（NEW-only，VERIFIED）

### 2.1 `_CODOL2697_WriteGamestate`（RVA 0xa21b8）

调用链（反汇编确认）：

```
_SV_SendMessageToClient   (函数 rva 0x86b06)
   <- _SV_SendClientGameState (函数 rva 0x70e47, 调用点 0x7110c)
   <- _SV_EndClientSnapshot   (函数 rva 0x86f7d, 调用点 0x87073)
_SV_SendClientMessages  (函数 rva 0x8a9f1)
   <- _SV_Frame (函数 rva 0x8404c, 调用点 0x84158)

_CODOL_WriteGamestate (0xa865a)  <- _CODOL_WriteServerGamestate (0xc3c22)
_CODOL_WriteServerGamestate      <- _SV_WriteGameState (0x82396)
_CODOL2697_WriteNativeGamestate (0xa3dab) <- _CODOL_WriteServerGamestate (0xc3a81)
_CODOL2697_WriteGamestate       <- _CODOL2697_PublicationAudit_f (0xa3b0b)
                                <- _CODOL2697_WriteNativeGamestate (0xa3e83)
_CODOL2697_WriteConfigstrings   <- _CODOL2697_WriteGamestate (0xa22c1)
```

写字节常量（VERIFIED，Capstone）：

- `_CODOL2697_WriteGamestate`：先 `_CODOL_WriteByte 3`（rva 0xa224c），再 `_CODOL_WriteByte 6`（rva 0xa22f8）。
- `_CODOL2697_WriteSnapshotReached`（0xa4860）：写 `0`（多处）与 `_CODOL_WriteByte 6`（rva 0xa4caf）。

**关键差异（VERIFIED）：** 2697 通道用 **`0x06`** 处 **旧通道用 `0x05`** 的位置（EOF 所在）。任务书中旧版记录 EOF=`0x05`，在 2697 通道 **复现为 `0x06`**。

**STATIC-INFERENCE：** 2697 wire 的 EOF/终止字节很可能为 **`0x06`**，而非旧版 `0x05`。这是一个 **直接可见的协议差异**，但"客户端是否接受 0x06"仍是 **NOT-OBSERVED**。

### 2.2 `_CODOL2697_WriteSnapshot`（RVA 0xa4fa0）

- 该函数是 **薄封装**：设置参数后 tail-jump 到 `_CODOL2697_WriteSnapshotReached`（0xa4ff7 处 call，目标 0xa4860）。
- `_CODOL2697_WriteSnapshotReached` 会依次调用 `_CODOL2697_WriteEntities`（0xa1a65）、`_CODOL2697_WriteClients`（0xa01ec）、`_CODOL_WriteGlass`（0x4b6010）、`_CODOL2697_ReachHud`（0x49f2e5），最后写 `0x06`。
- 上述 2697 写实体函数（`_WriteDeltaValue` 被 `_WriteActors/_hud_array/_WritePlayerArrays/_WriteClientPayload/_ReachDeltaValue/_WriteEntityPayload/_WritePlayerFields/_prepare_target` 调用）。

**STATIC-INFERENCE：** 2697 snapshot 是一个**分段式**写入器（entities → clients → glass → hud → 终止字节 6），与旧 `_CODOL_WriteSnapshot` 的 delta-number 路径并行存在。

---

## 3. 可靠命令通道 `_SV_WriteReliableCommand`（NEW-only，RVA 0x8612e）

反汇编要点（VERIFIED）：

```
00486150  call _SV_ProfileCommand2697      ; 先尝试 2697 画像
00486155  test eax,eax ; js 0x4861af
  ... 命中（eax>=0）:
00486160  mov [esp+4], 2 ; call _MSG_WriteByte      ; <-- 写 0x02
0048617d  call _MSG_WriteLong
00486189  call _MSG_WriteShort
0048619f  call _MSG_WriteData
  ... 未命中 / 回退:
004861c5  mov [esp+4], 1 ; call _MSG_WriteByte      ; <-- 写 0x01（旧 serverCommand）
004861d0  ...
004861e2  call _MSG_WriteLong
004861ee  call _MSG_WriteString
```

调用方（VERIFIED）：

```
_SV_UpdateServerCommandsToClient       (call sites 0x486217, 0x48622b)
_SV_UpdateServerCommandsToClientRecover(call site 0x4862ac)
```

**VERIFIED：** 新可靠命令信封在 2697 分支写 `0x02`（并在其后附 long/short/data 的画像结构），回退分支写 `0x01`（旧 `SV_WIRE_SERVERCOMMAND`）。`_SV_ProfileCommand2697`（0x860de）对命令做画像并决定走哪条分支。

**STATIC-INFERENCE：** `0x01` 仍是旧 serverCommand 信封；`0x02` 是 2697 新的可靠命令封装（含结构化 payload）。此处的 `0x02` 与旧 gamestate 的 `0x02` **在不同上下文**（可靠命令流 vs gamestate 流），不应混淆。

> 诊断串（NEW-only，VERIFIED）：`"CoDOL 2697 reliable audit mapped=%u immutable_omitted=%u failures=%u"`、`"CoDOL 2697 reliable command conversion failed (letter %c): %.1024s"`。

---

## 4. 注册门控：gamestate 被扣留的条件（NEW-only，VERIFIED）

`_CODOL2697_WriteNativeGamestate`（RVA 0xa3dab）逻辑：

```
调用 _CODOL_Server2697ResourceSource，读 [eax+0x78f4]
  若为 0 -> 调用 _CODOL_Server2697Registration，读 [eax+0x6408]
  若任一为 0 -> Com_Printf(gate_str); 返回 0   （gamestate 被扣留，不发送）
  否则 -> _collect(...) 临时缓冲 -> 调用 _CODOL2697_WriteGamestate (0xa3e83)
```

- 门控字符串（VERIFIED）：VA `0x7c424c`（.rdata，fileoff 0x3c164c）=
  `"CoDOL 2697 gamestate withheld: verified client registration export is required\n"`
- `_CODOL2697_ReadRegistration`（RVA 0xa3ea0）：
  - `memset` 0xc814 字节；
  - `fopen(path,"rb")`（格式串 VA 0x7c429c）；
  - 解析三字段 `"codol2697-registration %u %x %u"`（VA 0x7c42a0）或五字段 `"codol2697-registration %u %x %u %u %x %c"`（VA 0x7c42e4）；
  - 校验 kind ∈ [1,2]、index ∈ [1,0xc7]（1..199）。
- 调用方（VERIFIED）：`_CODOL_SetTarget2697ServerResources`（0xc332f）调用 `_CODOL2697_ReadRegistration`。
- 磁盘上的实际注册文件（VERIFIED）：
  `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\evidence\client-registration2697.txt`
  首行：`codol2697-registration 2 6b6fb5d0 180 139 f78302fe`

**STATIC-INFERENCE：** 2697 在发送 gamestate 前 **要求存在一个"已验证客户端注册导出"**，否则整段 gamestate 被扣留。这是 2697 通道相对旧通道新增的 **门控/前置条件**，直接关系到能否进入大厅。

相关 NEW-only 诊断串（VERIFIED）：
- `"Read-only verified client registration export for target gamestate publication"`（VA 0x7edee0，被 `_CODOL_LoadStartupArchives` 0x13c730 引用）
- `"CoDOL 2697 publication dry encode=%d bytes=%u actual_client_crc=%d"`（VA 0x7c419c，被 `_CODOL2697_PublicationAudit_f` 0xa3b2c 引用）
- `"CoDOL 2697 netconst checksum=%08x seed=%08x"`（VA 0x7c416c，被 `_CODOL2697_PublicationAudit_f` 0xa3a2f 引用）

---

## 5. 连接/握手路径（三样本共有，RVA 不同，VERIFIED）

| 函数 | NEW | OLD | 1113 |
|---|---|---|---|
| `_SV_DirectConnect` | 0x6f2c0 | 0x834d6 | 0x6ed8a |
| `_SV_ConnectionlessPacket` | 0x8487f | 0x15cd3 | 0x83ceb |
| `_SV_SendMessageToClient` | 0x86b06 | 0x1a8c0 | 0x858c0 |
| `_CODOL_HandshakeInit` | 0x982a3 | 0x97230 | 0x96034 |
| `_CODOL_HandshakeCookie` | 0x9857b | 0x97597 | 0x9639b |
| `_CODOL_HandshakeClear` | 0x9828d | 0x97217 | 0x9601b |

**VERIFIED：** `_SV_SendMessageToClient` 被 `_SV_SendClientGameState`（函数 rva 0x70e47，调用点 0x7110c）与 `_SV_EndClientSnapshot`（函数 rva 0x86f7d，调用点 0x87073）调用；`_SV_SendClientMessages`（函数 rva 0x8a9f1）被 `_SV_Frame`（函数 rva 0x8404c，调用点 0x84158）调用。

---

## 6. 新增 2697 模块清单（与源文件名对应，VERIFIED）

源文件串（`strings_NEW_80816711.txt`，OLD/1113 均无）：

| 源文件名 | 对应关键符号（示例） |
|---|---|
| `codol_2697_snapshot.c` | `_CODOL2697_WriteSnapshot`, `_WriteSnapshotReached` |
| `codol_2697_gamestate.c` | `_CODOL2697_WriteGamestate`, `_WriteNativeGamestate` |
| `codol_2697_configstrings.c` | `_CODOL2697_WriteConfigstrings` |
| `codol_2697_registration.c` | `_CODOL2697_ReadRegistration` |
| `codol_2697_publication.c` | `_CODOL2697_PublicationAudit_f` |
| `codol_2697_history.c` | `_PrepareHistory`, `_FinishHistory` |
| `codol_2697_adapter.c` | `_CODOL2697_Adapt*` |
| `codol_2697_fields.c` | `_CODOL2697_*Field` |
| `codol_2697_actors.c` | `_CODOL2697_WriteActors` |
| `codol_2697_anim.c` | `_CODOL2697_WriteAnimations` |
| `codol_2697_arrays.c` | `_CODOL2697_WritePlayerArrays` |
| `codol_2697_clients.c` | `_CODOL2697_WriteClients` |
| `codol_2697_delta.c` | `_CODOL2697_WriteDeltaValue`, `_ReachDeltaValue` |
| `codol_2697_entities.c` | `_CODOL2697_WriteEntities`, `_WriteEntityPayload` |
| `codol_2697_resources.c` | `_CODOL2697_*Resources` |
| `codol_2697_profile.c` | `_CODOL2697_ProfileCommandBytes` |
| `codol_weapon_2697.c` / `_core/_keys/_loader/_registry/_runtime.c` | `_CODOL_BuildWeapon2697*`, `_LoadEngineWeapon2697` |
| `codol_loopback_win32.c` | `_guard_*`（11 个网络守卫） |
| `codol_netconst_index.c` | netconst 索引/校验 |
| `codol_archive_probe.c` | 归档探测 |

相关 CVar/特性串（NEW-only，VERIFIED）：`CODOL2697_PROFILE_WIRE`, `CODOL_INVENTORY2697`, `CODOL_RUNTIME_WEAPONS2697`, `WireFixture2697`。

---

## 7. 消息类型重新核验（VERIFIED）

| 流 | 旧通道（三样本一致） | 2697 通道（NEW-only） |
|---|---|---|
| gamestate | `0x02` | 起始 `0x03`（`_CODOL_WriteByte 3`），结束 `0x06` |
| configstring | `0x03` | 由 `_CODOL2697_WriteConfigstrings` 内部写出（与 gamestate 组合） |
| snapshot | `0x00` | `0x00`（多处）+ 终止 `0x06` |
| serverCommand（可靠命令） | `0x01` | `0x02`（结构化 payload）；回退仍为 `0x01` |
| EOF | `0x05` | `0x06`（2697 通道） |

**注意：** 2697 gamestate 起始字节为 `0x03`（与旧 configstring 同值），这是 **另一套 2697 上下文**，**不可**与 05 中"旧 configstring=0x03"直接等同解释。

---

## 8. 结论

| 结论 | 等级 |
|---|---|
| 旧通道消息常量（0/1/2/3/5）在新样本旧通道中保持不变 | VERIFIED |
| NEW 新增独立 2697 写通道（`_CODOL2697_Write*`），OLD/1113 无 | VERIFIED |
| 2697 通道在 EOF 位置写 `0x06`（旧为 `0x05`） | VERIFIED（字节事实） / STATIC-INFERENCE（"2697 EOF=0x06"语义） |
| 可靠命令 2697 分支写 `0x02`，回退写 `0x01` | VERIFIED |
| gamestate 发送前有"注册导出"门控，缺失则扣留 | VERIFIED |
| `_CODOL2697_WriteSnapshot` 是 `_WriteSnapshotReached` 的薄封装 | VERIFIED |
| 客户端是否接受 0x06 / 新可靠命令封装 | NOT-OBSERVED |
| 2697 层是否已在运行期被激活（有无 CVar 开关） | BLOCKED（需运行或更深的初始化路径追踪） |

未决问题：
- 2697 通道的启用开关（`CODOL2697_PROFILE_WIRE` 等 CVar 的实际读取点）→ 需追踪初始化。
- `_SV_BuildClientSnapshot`（0x89081，调用方 0x8a582/0x8aabc）与旧 snapshot 的关系 → 需进一步反汇编（见 06）。
