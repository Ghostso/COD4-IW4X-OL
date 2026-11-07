# OFFLINE_002 — D：战斗序列化器（服务端）定向地图

> 任务：`EARLY-SERVER-OFFLINE-VALIDATION-002` §5（最高优先级，服务端侧）。
> 输入：只读。派生脚本/证据仅写 `08_OFFLINE_002\`；不启动服务端/客户端，不执行 `.cmd`，不修改样本/既有报告。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 服务端源码根：`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src`。
> 说明：本报告**只登记真实文件位置与调用关系**；函数名不确定处一律以"文件:行 + 语义"描述，不凭空命名。

---

## D.0 一句话结论

- 服务端战斗序列化器**存在且路径完整**：gamestate / configstrings / snapshot 三段均有 `codol\` 下的**专用 CoDOL 实现**（非 IW3 复用），并在 `#ifdef CODOL_SERVER` 下切换。**CONFIRMED（源码级）**。
- 该实现写入的**线值**与 `net_game_conf.h` 的 `svc_ops_e` 枚举**不一致**（gamestate 写 `2`、snapshot 写 `0`、终止写 `5`；枚举为 gamestate=1/configstring=2/snapshot=6/EOF=7）→ **登记为待解冲突**（D.6）。
- **本机未见任何真实下行 gamestate/snapshot 抓包**与之逐字节比对 → 服务端序列化器的**客户端可解析性 NOT_OBSERVED**。

---

## D.1 编码入口总览（调用链）

```
SV_SendClientGameState            sv_client.c:2160
  ├─ client->state = CS_PRIMED     sv_client.c:2273
  ├─ MSG_WriteLong(lastClientCmd)  sv_client.c:2287
  ├─ SV_UpdateServerCommandsToClient sv_client.c:2293
  ├─ SV_WriteGameState(&msg,cl)    sv_client.c:2298
  │    └─(CODOL) CODOL_WriteServerGamestate  sv_main.c:3946 -> codol_sv_state.c:119
  │          ├─ CODOL_SetServerInfo          codol_sv_state.c:132 / :104-117
  │          ├─ CODOL_SetConfigstring(cs,2,"cod") codol_sv_state.c:133
  │          ├─ CODOL_MsgWriteInit           codol_sv_state.c:141
  │          └─ CODOL_WriteGamestate         codol_sv_state.c:142 -> codol_configstrings.c:288
  │                └─ CODOL_WriteConfigstrings codol_configstrings.c:303 -> :269
  └─ SV_SendMessageToClient        sv_client.c:2312 -> sv_snapshot.c:642 -> :688 SV_Netchan_Transmit

SV_SendClientSnapshot             sv_snapshot.c:759
  ├─ SV_BeginClientSnapshot        sv_snapshot.c:765 -> :774
  │    ├─ CODOL_BuildGameplayFrame sv_snapshot.c:791
  │    └─ MSG_WriteLong / SV_UpdateServerCommandsToClient / SV_UpdateConfigData  sv_snapshot.c:814/818/822
  ├─ SV_WriteSnapshotToClient      sv_snapshot.c:767 -> :224
  │    └─ CODOL_PrepareClientSnapshot sv_snapshot.c:260 -> codol_sv_snapshot.c:85
  │          └─ CODOL_PrepareServerSnapshot codol_sv_snapshot.c:105 -> :241
  │                └─ write_server_snapshot_delta codol_sv_snapshot.c:284 -> :205
  │                      └─ CODOL_WriteSnapshotDeltaNumber codol_snapshot.c:230 -> :8
  └─ SV_EndClientSnapshot          sv_snapshot.c:769 -> :827 (写 SV_WIRE_EOF=5  @ :849)
```

**结论：服务端编码入口 = `SV_WriteGameState`（gamestate）与 `SV_WriteSnapshotToClient`（snapshot）；两者最终经 `SV_SendMessageToClient`→`SV_Netchan_Transmit` 出网。CONFIRMED（源码级调用链闭合）。**

---

## D.2 gamestate 构造（精确行号）

### D.2.1 `SV_SendClientGameState`（`sv_client.c:2160`）
| 行 | 语义 | 证据 |
|---|---|---|
| `:2273` | `client->state = CS_PRIMED`（**发送前**置位） | 源码 |
| `:2287` | `MSG_WriteLong(&msg, client->lastClientCommand)`（首个 4B 明文 ACK） | 源码 |
| `:2293` | `SV_UpdateServerCommandsToClient`（写未确认 serverCommand） | 源码 |
| `:2298` | `SV_WriteGameState(&msg, client)`（CODOL 分支） | 源码 |
| `:2299-2308` | 溢出回滚（恢复 state/gamestateSent/messageNum/reliableSent） | 源码 |
| `:2310-2311` | 从 `msg.data[0:4]` 取 wire ACK 用于 trace | 源码 |
| `:2312` | `SV_SendMessageToClient(&msg, client)` | 源码 |

### D.2.2 `SV_WriteGameState`（`sv_main.c:3939`）
- `:3940-3949` **CODOL 分支**：先做 6 项刷新（`CODOL_SetServerId` / `RefreshServerAssetNames` / `RefreshServerMapConfigstrings` / `RefreshServerPlayerNames` / `RefreshServerWeaponRegistry` / `RefreshServerWeaponMappings`），失败即 `msg->overflowed=qtrue`；成功则调用 `CODOL_WriteServerGamestate(msg, sv_mapname, codol_zoneType, sv_g_gametype, sv_maxclients, cl->reliableSequence, cl-svs.clients, sv.checksumFeed, sv_hostname)`。
- `:3951+` 的 `MSG_WriteByte(msg, svc_gamestate)`… 分支在 `CODOL_SERVER` 下**不可达**（死代码）。

### D.2.3 `CODOL_WriteServerGamestate`（`codol\snapshot\codol_sv_state.c:119-151`）
| 行 | 语义 |
|---|---|
| `:125-129` | 参数/容量校验；`CODOL_ConstConfigChecksum(zone_type,&crc)` |
| `:132` | `CODOL_SetServerInfo(map,gametype,max_clients,hostname)` |
| `:133` | `CODOL_SetConfigstring(&configstrings, 2, "cod")` |
| `:138-139` | `CODOL_ServerMapIdentityMatches` + `CODOL_ConfigstringPoolSize`（128 KiB 串池校验） |
| `:141` | `CODOL_MsgWriteInit(&wire, msg->data+msg->cursize, msg->maxsize-msg->cursize)` |
| `:142` | `CODOL_WriteGamestate(&wire, &configstrings, map, zone_type, crc, sequence, client_number, checksum_feed)` |
| `:144` | `msg->cursize += wire.size` |
| `:146` | `msg->bit = msg->cursize * 8`（gamestate 结束后**位池复位到字节边界**） |

### D.2.4 `CODOL_SetServerInfo`（`codol_sv_state.c:104-117`）
- `:115` 组串：`\g_gametype\<gt>\mapname\<map>\2485\<maxclients>\2492\<hostname>\2482\<animlist_flags>`。
- `:111-114` 注释记录客户端读取点：`CG_ParseServerinfo 0x465f57`（"2485"@0xc44704 = maxclients）、`0x465bc1`（数字键 2492 → hostname[256]）、`0x465c27`（键 2482 → CG_Init animlist）。**这些客户端 VA 本轮已在 `_evidence\client_cited_rva_disasm.json` 反汇编确认存在（见 E 报告）。**

### D.2.5 `CODOL_WriteGamestate`（`codol\snapshot\codol_configstrings.c:288-308`）逐字节布局
| 行 | 写操作 | 线值 |
|---|---|---|
| `:298` | `CODOL_WriteByte(msg, 2)` | `0x02`（gamestate 起始字节） |
| `:299` | `CODOL_WriteLong(msg, command_sequence)` | u32 LE |
| `:300` | `CODOL_WriteString(msg, map)` | NUL 结尾 |
| `:301` | `CODOL_WriteString(msg, zone_type)` | NUL 结尾（`mp`/`coop`/`zm`） |
| `:302` | `CODOL_WriteLong(msg, const_crc)` | u32 LE |
| `:303` | `CODOL_WriteConfigstrings(msg, state)` | 见 D.3 |
| `:304` | `CODOL_WriteLong(msg, client_number)` | u32 LE |
| `:305` | `CODOL_WriteLong(msg, checksum_feed)` | u32 LE |
| `:306` | `CODOL_WriteByte(msg, 5)` | `0x05`（终止） |

### D.2.6 常量 CRC（`codol_configstrings.c:9-20`）
`mp=0xad1e1713`、`coop=0xe8139f9b`、`zm=0x801cef02`（按 zone_type 选择）。

---

## D.3 configstrings 写入/更新路径

### D.3.1 API（`codol_configstrings.c`）
| 函数 | 行 | 语义 |
|---|---|---|
| `CODOL_SetConfigstring` | `:30` | 写入/覆盖某索引 |
| `CODOL_GetConfigstring` | `:49` | 读原始值 |
| `CODOL_GetEffectiveConfigstring` | `:54` | 读"继承表 + 覆盖"后的有效值 |
| `CODOL_ConfigstringPoolSize` | `:61` | 串池字节数（用于 128 KiB 校验） |

### D.3.2 `CODOL_WriteConfigstrings`（`codol_configstrings.c:269-286`）
| 行 | 写操作 | 说明 |
|---|---|---|
| `:275` | `msg->bit = 0` | **重置位池**（新子流，独立于前序位） |
| `:276` | `CODOL_WriteByte(msg, 3)` | 子流起始字节 `0x03` |
| `:277` | `CODOL_WriteShort(msg, state->count)` | u16 LE 计数 |
| `:280` | `CODOL_WriteBits(msg, 0, 1)` | **1 bit** "绝对索引"标志 |
| `:281` | `CODOL_WriteBits(msg, i, 13)` | **13 bit** 索引 |
| `:282` | `CODOL_WriteString(msg, state->values[i])` | NUL 结尾串 |
| `:284` | `CODOL_WriteByte(msg, 5)` | 终止 `0x05` |

- **关键位布局**：每个存在的 configstring = `1 bit(0) + 13 bit(index) + cstring`；`0x03`/`count`/`0x05` 为整字节字段，**不重置位池**（`codol_msg.c:82-86`：`WriteBits` 在字节游标处预留 1 字节再按位填充）。
- **复用判断**：该编码器是**纯 C、无引擎结构体依赖**（`codol_msg_t` 仅 `{data,size,capacity,cursor,bit,failed}`，`codol_msg.h:9-13`）→ **可移植性高（CANDIDATE：需客户端确认）**。

---

## D.4 snapshot 生成 / 差分 / 压缩路径

### D.4.1 入口（`sv_snapshot.c`）
| 函数 | 行 | 语义 |
|---|---|---|
| `SV_SendClientSnapshot` | `:759` | 三步：Begin → Write → End |
| `SV_BeginClientSnapshot` | `:774` | `MSG_Init` + `CODOL_DiscardClientSnapshot` + `CODOL_BuildGameplayFrame`（`:791`）+ 写 4B ACK（`:814`）+ serverCommands（`:818`）+ `SV_UpdateConfigData`（`:822`） |
| `SV_WriteSnapshotToClient` | `:224`（CODOL `:225-283`） | 取 `CODOL_ClientNativeFrame(slot,seq)`（`:231`）、`CODOL_ReadOriginVelocityFlag`（`:257`）、`CODOL_PrepareClientSnapshot`（`:260`） |
| `SV_EndClientSnapshot` | `:827` | 若快照未准备则 `MSG_WriteByte(msg, SV_WIRE_EOF)`（`:849`，值 `5`）；溢出则 `CODOL_DiscardClientSnapshot`（`:854`） |

### D.4.2 快照准备（`codol\snapshot\codol_sv_snapshot.c`）
| 函数 | 行 | 语义 |
|---|---|---|
| `CODOL_PrepareClientSnapshot` | `:85-130` | 校验 → `CODOL_ApplyServerPositionBase` → malloc 序列化副本 → `CODOL_PrepareServerSnapshot`（`:105`）→ 可选 matchdata 段（`:111-123`）→ `client_pending[n]` 记录（`:124-127`） |
| `CODOL_PrepareServerSnapshot` | `:241-290` | `ack_base`（`:251`）、`baseline`（`:252`）、`baseline_frame`（`:253-254`）、flag-8 强制基线（`:260-261`，注释引用 C1 `0x49dd7e`）、delta_number（`:264`）、pinned 无 delta 基线（`:266-269`，注释引用 C1 `0x49d9ce`）、`CODOL_Prepare(Baseline)History`（`:271-273`）、`write_server_snapshot_delta`（`:284`） |
| `write_server_snapshot_delta` | `:205-239` | 玻璃世界捕获（`:218-224`）→ `CODOL_MsgWriteInit`（`:229`）→ `CODOL_WriteSnapshotDeltaNumber`（`:230`）→ `msg->cursize += wire.size; msg->bit = msg->cursize*8`（`:234`） |

### D.4.3 快照逐字节布局（`codol\snapshot\codol_snapshot.c:8-46`）
| 行 | 写操作 | 线值/说明 |
|---|---|---|
| `:22` | `m->bit = 0` | 新位池 |
| `:23` | `CODOL_WriteByte(m, 0)` | `0x00`（snapshot 起始字节） |
| `:24` | `CODOL_WriteLong(m, ctx->server_time)` | u32 LE |
| `:25` | `CODOL_WriteByte(m, delta)` | delta 编号（≤31，`:19` 校验） |
| `:26` | `CODOL_WriteByte(m, flags)` | 标志字节（flag8=基线，flag1=rateDelayed，flag2=非 active） |
| `:27` | `CODOL_WriteBits(m, base!=NULL, 1)` | 1 bit "有基线" |
| `:28` | SECTION "player state" → `CODOL_WritePlayerState` | |
| `:30` | SECTION "anim commands" → `CODOL_WriteAnimCommands` | |
| `:31` | SECTION "actors" → `CODOL_WriteActors` | |
| `:33` | SECTION "entities" → `CODOL_WriteEntities` | |
| `:35` | SECTION "clients" → `CODOL_WriteClients` | |
| `:40` | SECTION "glass" → `CODOL_WriteGlass` | |
| `:41` | `CODOL_WriteByte(m, 5)` | 终止 `0x05` |

### D.4.4 差分编解码（`codol\snapshot\codol_delta.c`，文件头 `:1` 注明 "C1.exe sub_5A0510 codecs"）
| 函数 | 行 | 语义 |
|---|---|---|
| `compressed` | `:9-14` | `n&7` 位 + 逐字节 |
| `CODOL_SetDeltaPositionBase` | `:20-30` | 位置基（round-even） |
| `angle` | `:31-36` | `round_even(value*182.04444885253906)` → u16（**16-bit 角度**） |
| `integer` | `:37-50` | 可选 presence bit + XOR 压缩 |
| `trimmed` | `:51-61` | 1 bit "trunc 可表示" + 压缩 / 否则原 4B XOR |
| `CODOL_ReachDeltaValue` | `:63+` | 到达值重算（用于"序列化到达态"） |

### D.4.5 压缩 / 位流（`codol\net\codol_msg.c` + `sv_snapshot.c:651-657`）
- **位流模型**：`codol_msg.c:1-3` 头注释——"位池字节在字节游标处预留，随后填充/读取；整字节字段**永不**对齐或重置该池"。`WriteBits`（`:77-92`）、`ReadBits`（`:41-57`）、`write_integer`（`:67-75`，**LE**）。
- **整包 Huffman**：`SV_SEND_HUFFMAN` 宏在 CODOL 分支**未定义**（`sv_snapshot.c:63-67` 的 `#else` 才定义）→ CODOL 路径 `SV_SendMessageToClient` 走 `:688 SV_Netchan_Transmit(client, msg->data, msg->cursize)`（**无 Huffman**）。**注意**：这是**外层 netchan 包**级；CoDOL 自定义位流在 `codol_msg_t` 内独立。
- **帧构造器**：`codol_frame_builder.c:33 CODOL_ClientNativeFrame`、`:39 CODOL_BuildClientNativeFrame`；帧结构 `:12-22`（state/player/updates/hud/entities[ENTITYNUM_WORLD]/clients[32]/actors[32]/commands）。

---

## D.5 出网调用链（网络发送）

| 步骤 | 位置 | 语义 |
|---|---|---|
| 1 | `sv_snapshot.c:642 SV_SendMessageToClient` | 入口（gameState + snapshot 共用） |
| 2 | `sv_snapshot.c:677-682` | 记录 `frames[seq&PACKET_MASK]` 的 messageSize/Sent/Acked |
| 3 | `sv_snapshot.c:688` | `SV_Netchan_Transmit(client, msg->data, msg->cursize)` |
| 4 | `codol\net\codol_wire.c:22-95` | `CODOL_WritePacket`/`CODOL_ReadFragment`/`CODOL_Xor`（netchan 头 + 分片 + XOR） |

---

## D.6 待解冲突：线值 vs `svc_ops_e` 枚举

- `net_game_conf.h:64-78 svc_ops_e`：`svc_nop=0, svc_gamestate=1, svc_configstring=2, svc_baseline=3, svc_serverCommand=4, svc_download=5, svc_snapshot=6, svc_EOF=7`。
- 但 CODOL 线值（D.2.5/D.3.2/D.4.3）：
  - gamestate 起始 = `0x02`（枚举里是 `svc_configstring`）
  - configstring 子流起始 = `0x03`（枚举里是 `svc_baseline`）
  - snapshot 起始 = `0x00`（枚举里是 `svc_nop`）
  - 终止 = `0x05`（枚举里是 `svc_download`）
  - serverCommand = `0x01`（`sv_snapshot.c:61 SV_WIRE_SERVERCOMMAND 1`，枚举里是 `svc_gamestate`）
- **判定**：CODOL 线值是**自定义 opcode 空间**，与引擎 `svc_ops_e` 枚举**不是同一编号系**（`sv_snapshot.c:61-62` 用 `#define` 而非枚举值即为例证）。**不强行统一**；登记为 **CONFIRMED（两套编号系并存）**，但"客户端按哪一套解析"= **UNKNOWN**（缺客户端下行解析证据，见 E 报告）。

---

## D.7 证据等级汇总

| 断言 | 等级 | 依据 |
|---|---|---|
| 服务端 gamestate 编码入口 = `SV_WriteGameState`（CODOL 分支） | **CONFIRMED** | `sv_main.c:3939-3949`；`sv_client.c:2298` |
| gamestate 逐字节布局（0x02/seq/map/zone/crc/configstrings/clientNum/checksumFeed/0x05） | **CONFIRMED** | `codol_configstrings.c:288-307` |
| configstrings 位布局（1+13 bit + cstring，0x03…0x05） | **CONFIRMED** | `codol_configstrings.c:269-286` + `codol_msg.c:77-92` |
| snapshot 编码入口 = `SV_WriteSnapshotToClient`（CODOL 分支） | **CONFIRMED** | `sv_snapshot.c:224-283` |
| snapshot 逐字节布局（0x00/time/delta/flags/1bit + 6 sections + 0x05） | **CONFIRMED** | `codol_snapshot.c:8-46` |
| 差分 codec = C1 `sub_5A0510` 族 | **STRONG_CANDIDATE** | `codol_delta.c:1` 自述 + 客户端 VA 存在（E 报告） |
| 出网链 = `SV_SendMessageToClient`→`SV_Netchan_Transmit` | **CONFIRMED** | `sv_snapshot.c:642/688` |
| CODOL 路径不走整包 Huffman | **CONFIRMED** | `sv_snapshot.c:63-67`（宏未定义） |
| 线值与 `svc_ops_e` 为两套编号系 | **CONFIRMED** | `net_game_conf.h:64-78` vs 各写点 |
| 服务端序列化器产出可被真实客户端解析 | **NOT_OBSERVED** | 无下行抓包逐字节比对 |

---

## D.8 复算/核对命令（只读）

```
# 逐行核对（PowerShell，-LiteralPath 处理空格/括号）
$root='D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src'
Get-Content -LiteralPath "$root\codol\snapshot\codol_configstrings.c" | Select-Object -Skip 265 -First 45
Get-Content -LiteralPath "$root\codol\snapshot\codol_snapshot.c"       | Select-Object -First 46
Get-Content -LiteralPath "$root\codol\net\codol_msg.c"                | Select-Object -First 100
```
