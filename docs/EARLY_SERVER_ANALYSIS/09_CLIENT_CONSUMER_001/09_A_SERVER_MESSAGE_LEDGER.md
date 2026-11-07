# 09 — A：服务端消息编码账本（Server Message Ledger）

> 任务：`EARLY-SERVER-CLIENT-CONSUMER-001` 任务 A。
> 边界：**只做静态分析**。不启动客户端/服务端，不执行 `.cmd`/未知脚本，不修改原始样本与既有报告，不实施补丁，不输出秘密材料。
> 服务端源码根：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src`
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## A.0 一句话结论

- 从 `SV_WriteGameState` 与 `SV_WriteSnapshotToClient` 出发的**服务端编码调用链已闭合到出网函数**（`SV_SendMessageToClient` → `SV_Netchan_Transmit`），等级 **CONFIRMED（源码级）**。
- CODOL 分支实际写出的**消息首字节**：serverCommand=`0x01`、gamestate=`0x02`、configstring 子流=`0x03`、snapshot=`0x00`、EOF=`0x05`。**CONFIRMED（源码级）**。
- 这些线值与 `net_game_conf.h:64-78` 的 `svc_ops_e` 枚举**不一致**；枚举常量在 CODOL 可达路径中**未被使用**（仅出现在 `#else` 死分支）→ **两套编号体系并存，CONFIRMED**。
- **snapshot 的服务端首字节 = `0x00` 已确认（源码级）**；但"客户端期望的 snapshot opcode 是否也是 `0x00`"**无法由服务端源码确定** → **UNKNOWN**（详见 `09_E`）。

---

## A.1 调用链总览（CONFIRMED，源码级）

```
SV_SendClientGameState                     sv_client.c:2160
  ├─ client->state = CS_PRIMED             sv_client.c:2273
  ├─ MSG_WriteLong(lastClientCommand)      sv_client.c:2287   (4B 明文 ACK)
  ├─ SV_UpdateServerCommandsToClient       sv_client.c:2293   (serverCommand 0x01)
  ├─ SV_WriteGameState(&msg, client)       sv_client.c:2298
  │    └─(CODOL) CODOL_WriteServerGamestate      sv_main.c:3946  → codol_sv_state.c:119
  │          ├─ CODOL_SetServerInfo              codol_sv_state.c:132 → :104-117
  │          ├─ CODOL_SetConfigstring(cs,2,"cod") codol_sv_state.c:133
  │          ├─ CODOL_MsgWriteInit               codol_sv_state.c:141
  │          └─ CODOL_WriteGamestate             codol_sv_state.c:142 → codol_configstrings.c:288
  │                └─ CODOL_WriteConfigstrings   codol_configstrings.c:303 → :269
  └─ SV_SendMessageToClient                sv_client.c:2312 → sv_snapshot.c:642 → :688 SV_Netchan_Transmit

SV_SendClientSnapshot                      sv_snapshot.c:759
  ├─ SV_BeginClientSnapshot                sv_snapshot.c:765 → :774
  │    ├─ CODOL_BuildGameplayFrame         sv_snapshot.c:791
  │    └─ MSG_WriteLong / SV_UpdateServerCommandsToClient / SV_UpdateConfigData  sv_snapshot.c:814/818/822
  ├─ SV_WriteSnapshotToClient              sv_snapshot.c:767 → :224
  │    └─ CODOL_PrepareClientSnapshot      sv_snapshot.c:260 → codol_sv_snapshot.c:85
  │          └─ CODOL_PrepareServerSnapshot codol_sv_snapshot.c:105 → :241
  │                └─ write_server_snapshot_delta  codol_sv_snapshot.c:284 → :205
  │                      └─ CODOL_WriteSnapshotDeltaNumber  codol_snapshot.c:230 → :8
  └─ SV_EndClientSnapshot                  sv_snapshot.c:769 → :827 (写 SV_WIRE_EOF=5 @ :849)
```

**出网**：`SV_SendMessageToClient`（`sv_snapshot.c:642`）在 CODOL 分支**不启用整包 Huffman**（`SV_SEND_HUFFMAN` 仅在 `#else` 定义，`:63-67`），直接 `SV_Netchan_Transmit(client, msg->data, msg->cursize)`（`:688`）。**CONFIRMED**。

---

## A.2 gamestate 编码账本

### A.2.1 `SV_SendClientGameState`（`sv_client.c:2160`）

| 行 | 写入内容 | 证据 |
|---|---|---|
| `:2273` | `client->state = CS_PRIMED`（发送前置位） | 源码 |
| `:2287` | `MSG_WriteLong(&msg, client->lastClientCommand)` | 源码 |
| `:2293` | `SV_UpdateServerCommandsToClient(client,&msg)` | 源码 |
| `:2298` | `SV_WriteGameState(&msg, client)` | 源码 |
| `:2312` | `SV_SendMessageToClient(&msg, client)` | 源码 |

### A.2.2 `SV_WriteGameState`（`sv_main.c:3939`）

- `:3940-3949` **CODOL 分支**：6 项刷新（`CODOL_SetServerId` / `RefreshServerAssetNames` / `RefreshServerMapConfigstrings` / `RefreshServerPlayerNames` / `RefreshServerWeaponRegistry` / `RefreshServerWeaponMappings`）任一失败 → `msg->overflowed=qtrue; return`；成功则调用 `CODOL_WriteServerGamestate(...)`（`:3946-3947`）后 `return`（`:3948`）。
- `:3951+` 的 `MSG_WriteByte(msg, svc_gamestate)`（`:3956`）… `MSG_WriteByte(msg, svc_configstring)`（`:3958`）… `MSG_WriteByte(msg, svc_EOF)`（`:4011`）分支在 `CODOL_SERVER` 下**不可达（死代码）**。**REFUTED（可达性）**。

### A.2.3 `CODOL_WriteServerGamestate`（`codol\snapshot\codol_sv_state.c:119-151`）

| 行 | 语义 |
|---|---|
| `:125-129` | 参数/容量校验；`CODOL_ConstConfigChecksum(zone_type,&crc)` |
| `:132` | `CODOL_SetServerInfo(map,gametype,max_clients,hostname)` |
| `:133` | `CODOL_SetConfigstring(&configstrings, 2, "cod")` |
| `:138-140` | `CODOL_ServerMapIdentityMatches` + `CODOL_ConfigstringPoolSize` |
| `:141` | `CODOL_MsgWriteInit(&wire, msg->data + msg->cursize, msg->maxsize - msg->cursize)` |
| `:142` | `CODOL_WriteGamestate(&wire, &configstrings, map, zone_type, crc, sequence, client_number, checksum_feed)` |
| `:144` | `msg->cursize += wire.size` |
| `:146` | `msg->bit = msg->cursize * 8`（gamestate 以整字节字段结尾，不共享位池） |

`CODOL_SetServerInfo`（`:104-117`）：`:115` 写入 configstring[0] = `\g_gametype\<gt>\mapname\<map>\2485\<maxclients>\2492\<hostname>\2482\<animlist_flags>`；`:111-113` 注释引用客户端 `CG_ParseServerinfo` VA `0x465f57` / `0x465bc1` / `0x465c27`。

### A.2.4 `CODOL_WriteGamestate`（`codol\snapshot\codol_configstrings.c:288-308`）

| 行 | 写入 | 线上字节 |
|---|---|---|
| `:298` | `CODOL_WriteByte(msg, 2)` | **opcode = `0x02`** |
| `:299` | `CODOL_WriteLong(msg, command_sequence)` | u32 LE |
| `:300` | `CODOL_WriteString(msg, map)` | cstring（含 NUL） |
| `:301` | `CODOL_WriteString(msg, zone_type)` | cstring |
| `:302` | `CODOL_WriteLong(msg, const_crc)` | u32 LE |
| `:303` | `CODOL_WriteConfigstrings(msg, state)` | 子流（见 A.2.5） |
| `:304` | `CODOL_WriteLong(msg, client_number)` | u32 LE |
| `:305` | `CODOL_WriteLong(msg, checksum_feed)` | u32 LE |
| `:306` | `CODOL_WriteByte(msg, 5)` | **EOF = `0x05`** |

### A.2.5 `CODOL_WriteConfigstrings`（`codol_configstrings.c:269-286`）

| 行 | 写入 |
|---|---|
| `:275` | `msg->bit = 0`（独立子流，不继承前一消息的位池） |
| `:276` | `CODOL_WriteByte(msg, 3)` → **configstring 子流 opcode = `0x03`** |
| `:277` | `CODOL_WriteShort(msg, state->count)` → u16 LE 计数 |
| `:278-283` | 对每个非空项：`WriteBits(0,1)`（绝对索引）+ `WriteBits(i,13)`（13-bit 索引）+ `WriteString(value)` |
| `:284` | `CODOL_WriteByte(msg, 5)` → **子流终止 = `0x05`** |

位流语义（`codol\net\codol_msg.c:1-3, 41-57, 77-92`）：**整字节字段永不重新对齐/重置位池**；`WriteBits` 在字节游标处预留位池字节；整数 LE（`write_integer` `:67-75`）。**CONFIRMED**。

---

## A.3 snapshot 编码账本

### A.3.1 `SV_SendClientSnapshot` → `SV_WriteSnapshotToClient`

| 步骤 | 位置 | 语义 |
|---|---|---|
| 1 | `sv_snapshot.c:759 SV_SendClientSnapshot` | 入口 |
| 2 | `sv_snapshot.c:765 SV_BeginClientSnapshot` | 写 ACK/命令/（CODOL 无 configdata） |
| 3 | `sv_snapshot.c:767 SV_WriteSnapshotToClient` | CODOL 分支 `:225-283` |
| 4 | `sv_snapshot.c:769 SV_EndClientSnapshot` | 补 EOF / 收尾 |

### A.3.2 `SV_BeginClientSnapshot`（`sv_snapshot.c:774`）

| 行 | 语义 |
|---|---|
| `:779` | `MSG_Init(msg, tempSnapshotMsgBuf, sizeof)` |
| `:781` | `CODOL_DiscardClientSnapshot(slot)` |
| `:782-783` | 刷新资产/玩家名/武器映射，失败置 overflow |
| `:787-809` | 若已就绪且序列匹配，`CODOL_BuildGameplayFrame`（`:791`） |
| `:812` | `MSG_ClearLastReferencedEntity(msg)` |
| `:814` | `MSG_WriteLong(msg, client->lastClientCommand)` |
| `:818` | `SV_UpdateServerCommandsToClient(client, msg)`（写 `0x01` 命令） |
| `:822` | `SV_UpdateConfigData(client, msg)` → CODOL 为 **no-op**（`:529-535`） |

### A.3.3 `SV_UpdateServerCommandsToClient`（`sv_snapshot.c:97`）

| 行 | 语义 |
|---|---|
| `:102` | 遍历 `client->reliableAcknowledge+1 .. reliableSequence` |
| `:103` | `MSG_WriteByte(msg, SV_WIRE_SERVERCOMMAND)` → CODOL 下 `#define SV_WIRE_SERVERCOMMAND 1`（`:61`） |
| `:104` | `MSG_WriteLong(msg, i)`（命令序号） |
| `:106` | `MSG_WriteString(msg, client->reliableCommands[...].command)` |

### A.3.4 `SV_WriteSnapshotToClient`（`sv_snapshot.c:224`，CODOL 分支 `:225-283`）

| 行 | 语义 |
|---|---|
| `:228` | `client->state==CS_ZOMBIE` 直接返回（无游戏帧） |
| `:229-231` | slot / `outgoingSequence` / `CODOL_ClientNativeFrame` |
| `:234` | `flags = svsHeader.snapFlagServerBit` |
| `:243-246` | `rateDelayed` → flags|=1；非 active → flags|=2 |
| `:247-252` | 无 native frame → `msg->overflowed=qtrue; return`（**该帧不发送**） |
| `:255-256` | `acknowledged = (state==CS_ACTIVE && deltaMessage>0) ? deltaMessage : 0` |
| `:257-258` | `rov = CODOL_ReadOriginVelocityFlag(...)` |
| `:260-263` | `CODOL_PrepareClientSnapshot(slot,msg,state,acknowledged,updates,commands,count,flags,rov,&context)` |

### A.3.5 `CODOL_PrepareClientSnapshot`（`codol\snapshot\codol_sv_snapshot.c:85-130`）

| 行 | 语义 |
|---|---|
| `:97-100` | 客户端/待发/消息状态与容量校验 |
| `:105` | `CODOL_PrepareServerSnapshot(msg,history,state,acknowledged,updates,commands,count,flags,rov,&next)` |
| `:111-123` | 若到 match data 到期：在**预留 EOF 字节**的位流中追加 match 段，再补 `0x05` |
| `:124-127` | 记录 pending 副本（serialized copy） |

### A.3.6 `CODOL_PrepareServerSnapshot`（`codol_sv_snapshot.c:241-290`）

| 行 | 语义 |
|---|---|
| `:251` | `ack_base = flags&8 ? NULL : CODOL_FindHistoryBase(...)` |
| `:252-254` | `baseline = CODOL_HistoryBaseline`；`baseline_frame` 判定 |
| `:260-261` | 基线帧：`base=NULL; flags|=8u; rov=1`（**flag8 = baseline**） |
| `:262-264` | 有 ack base：`delta_number = state->sequence - ack_base->sequence` |
| `:266-269` | 无 ack base：使用 pinned baseline，**线上 deltaNum 保持 0** |
| `:271-273` | `CODOL_PrepareBaselineHistory` / `CODOL_PrepareHistory` |
| `:283` | 序列化"到达态"（已量化状态）而非原始态 |
| `:284` | `write_server_snapshot_delta(...)` |

### A.3.7 `write_server_snapshot_delta`（`codol_sv_snapshot.c:205-239`）

| 行 | 语义 |
|---|---|
| `:229` | `CODOL_MsgWriteInit(&wire, msg->data+msg->cursize, msg->maxsize-msg->cursize)`（**追加**在已有命令之后） |
| `:230` | `CODOL_WriteSnapshotDeltaNumber(&wire, state, base, delta_number, updates, commands, count, flags, rov, &next)` |
| `:234` | `msg->cursize += wire.size; msg->bit = msg->cursize*8` |

### A.3.8 `CODOL_WriteSnapshotDeltaNumber`（`codol\snapshot\codol_snapshot.c:8-46`）

| 行 | 写入 | 线上字节 |
|---|---|---|
| `:22` | `m->bit = 0`（新位池） | — |
| `:23` | `CODOL_WriteByte(m, 0)` | **snapshot 首字节 = `0x00`** |
| `:24` | `CODOL_WriteLong(m, ctx->server_time)` | u32 LE |
| `:25` | `CODOL_WriteByte(m, delta)` | u8 |
| `:26` | `CODOL_WriteByte(m, flags)` | u8（bit3=baseline，bit0=rateDelayed，bit1=non-active） |
| `:27` | `CODOL_WriteBits(m, base != NULL, 1)` | 1 bit |
| `:28-29` | `CODOL_WritePlayerState(...)` | 段 |
| `:30` | `CODOL_WriteAnimCommands(...)` | 段 |
| `:31-32` | `CODOL_WriteActors(...)` | 段 |
| `:33-34` | `CODOL_WriteEntities(...)` | 段 |
| `:35-36` | `CODOL_WriteClients(...)` | 段 |
| `:40` | `CODOL_WriteGlass(...)` | 段 |
| `:41` | `CODOL_WriteByte(m, 5)` | **EOF = `0x05`** |

### A.3.9 `SV_EndClientSnapshot`（`sv_snapshot.c:827-850`）

| 行 | 语义 |
|---|---|
| `:835-836` | `client->state != CS_ZOMBIE` 时 `SV_WriteDownloadToClient` |
| `:842-847` | pending 序列/prepared 校验；不一致 → overflow |
| `:847-849` | **未 prepared** 时才 `MSG_WriteByte(msg, SV_WIRE_EOF)`（CODOL `#define SV_WIRE_EOF 5`，`:62`） |

### A.3.10 `SV_SendMessageToClient`（`sv_snapshot.c:642`）

| 行 | 语义 |
|---|---|
| `:648` | `msg->overflowed` → 返回 qfalse |
| `:651-658` | `#ifdef SV_SEND_HUFFMAN`：CODOL 分支**未定义该宏** → 不走压缩 |
| `:679-682` | 记录 `frames[...].messageSize/messageSent/messageAcked` |
| `:688` | `SV_Netchan_Transmit(client, msg->data, msg->cursize)` |

---

## A.4 每条消息的账本汇总

| 消息 | 发送函数 / 调用链 | opcode 值 | 编号体系 | 编码字段 | 可达性 | 等级 |
|---|---|---|---|---|---|---|
| reliable ACK | `sv_client.c:2287` / `sv_snapshot.c:814` | 无 opcode（裸 u32） | netchan 内 | `u32 lastClientCommand` | 是 | **CONFIRMED** |
| serverCommand | `sv_snapshot.c:97-107`（经 `sv_client.c:2293`、`sv_snapshot.c:818`） | `0x01` | CODOL 自定义 | `{u8=1, u32 cmdSeq, cstring}` ×N | 是 | **CONFIRMED** |
| gamestate | `sv_client.c:2298` → `sv_main.c:3939` → `codol_sv_state.c:119` → `codol_configstrings.c:288` | `0x02` | CODOL 自定义 | `u32 seq, cstr map, cstr zone, u32 crc, <configstrings 子流>, u32 clientNum, u32 checksumFeed, u8=5` | 是 | **CONFIRMED** |
| configstring 子流 | `codol_configstrings.c:269-286` | `0x03`（终止 `0x05`） | CODOL 自定义 | `u16 count, {1b=0, 13b idx, cstring}*` | 是（gamestate 内） | **CONFIRMED** |
| snapshot | `sv_snapshot.c:759` → `:224` → `codol_sv_snapshot.c:241` → `codol_snapshot.c:8` | `0x00` | CODOL 自定义 | `u32 serverTime, u8 delta, u8 flags, 1b base, 6 段, u8=5` | 是 | **CONFIRMED（服务端侧）** |
| EOF（外层补写） | `sv_snapshot.c:849` | `0x05` | CODOL 自定义 | `u8=5` | 条件（仅未 prepared） | **CONFIRMED** |
| svc_ops_e gamestate/configstring/snapshot/EOF | `sv_main.c:3956/3958/4011`、`sv_client.c:2328/2333`、`sv_snapshot.c:356` | 1/2/6/7 | `svc_ops_e` 枚举 | — | **否（`#else` 死分支）** | **REFUTED（CODOL 可达性）** |

---

## A.5 复算步骤（只读）

```powershell
$root='D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src'
Get-Content -LiteralPath "$root\sv_client.c"                  | Select-Object -Skip 2159 -First 175
Get-Content -LiteralPath "$root\sv_main.c"                   | Select-Object -Skip 3938 -First 80
Get-Content -LiteralPath "$root\codol\snapshot\codol_sv_state.c"       | Select-Object -Skip 103 -First 50
Get-Content -LiteralPath "$root\codol\snapshot\codol_configstrings.c"  | Select-Object -Skip 268 -First 45
Get-Content -LiteralPath "$root\codol\snapshot\codol_sv_snapshot.c"    | Select-Object -Skip 84  -First 210
Get-Content -LiteralPath "$root\codol\snapshot\codol_snapshot.c"       | Select-Object -First 46
Get-Content -LiteralPath "$root\codol\net\codol_msg.c"                 | Select-Object -First 100
Get-Content -LiteralPath "$root\sv_snapshot.c"               | Select-Object -Skip 59 -First 10
Get-Content -LiteralPath "$root\sv_snapshot.c"               | Select-Object -Skip 641 -First 60
```

> 备注：本账本只登记**服务端写出**的字节；客户端是否接受这些字节属于 `09_C` / `09_E`，不在本文件断言。
