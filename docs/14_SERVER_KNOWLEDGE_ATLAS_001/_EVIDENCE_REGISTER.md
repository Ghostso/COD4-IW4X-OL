# 证据登记册 / EVIDENCE REGISTER（全档案共享 ID 表）

> 本文件是全档案的统一证据编号表。所有交付文档（`12`–`21`）引用证据时必须使用本表 ID，不得自造编号。
> 每个 ID 只算 **一个原始证据来源**。同一底层证据被多篇报告重复引用，不构成多个独立验证。

## A. 样本身份证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-S-Old | OLD 服务端 `codol_dedrun.exe` SHA-256 `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a`，8,469,493 B，ld 2.30，20 节区 | VERIFIED |
| EV-S-1113 | 1113 服务端 SHA-256 `a96c5dfb5386f166a0e1d4262b8fdecf9835b856cf1a863f891ead4eda5cb6e9`，8,622,389 B，ld 2.47，11 节区 | VERIFIED |
| EV-S-2697 | 2697 服务端 SHA-256 `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`，7,295,919 B，ImageBase 0x400000，无 PDB/版本资源 | VERIFIED |
| EV-S-2697-Mirror | 2697 服务端镜像副本字节一致 | VERIFIED |
| EV-C-1113 | 1.1.1.13 客户端 SHA-256 `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6`，20,918,752 B | VERIFIED |
| EV-C-3333 | 3.3.3.3 客户端 SHA-256 `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`，7,841,344 B，FileVersion 1649370 | VERIFIED |
| EV-C-2697 | 2.6.9.7 客户端 SHA-256 `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`，9,964,656 B，TenProtect 包装，仅导入 Base.dll ordinal #1 | VERIFIED |
| EV-C-2697-Rec | 恢复镜像 SHA-256 `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`，12,571,648 B，EntryPoint RVA 0x74FF4F | VERIFIED(文件) / BLOCKED(运行时等价) |
| EV-C-2697-Manifest | `manifest.json` SHA-256 `34017bf787800678a66d277520869873c3352c713da883e9dce2d348f669da00`，version 2.6.9.7，original_exe_sha256 与 EV-C-2697 一致 | VERIFIED |
| EV-Comp-DLLs | `client_room2697.dll` `120c4cfd…`；`client_native_loopback.dll` `53c6fbe2…`；两者 ImageBase 0x10000000，均导入 WS2_32 | VERIFIED |
| EV-Registration | `evidence\client-registration2697.txt` 2,976 B SHA-256 `4F1B4A38…`，首行 `codol2697-registration 2 6b6fb5d0 180 139 f78302fe` | VERIFIED |

## B. 仓库 / 源码血统证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-R-OldSrc | OLD 附带完整 C 源码 1,770 文件 / 25,603,769 B；CoD4x fork（Id/Ninja/TheKelm 版权）；`grep 2697` = 0 命中 | VERIFIED |
| EV-R-OldSrc-1113 | OLD src 与 1113 src 除 `g_sv_main.c`（移除 `player_sprintTime` 的 CVAR_CHEAT）外完全相同 | VERIFIED |
| EV-R-OlMod | ol-mod-olfinal，分支 `OLfinal-live`，HEAD `2a75bdd8872bb9f54006382a924c3006ec9affc2`，origin `CODOL-EMU/ol-mod-olfinal` | VERIFIED |
| EV-R-OlMod-NoIW4x | ol-mod 是 CODOL 专有链路源码重建（Project Nova / Ayria），**不基于 IW4x**；IW4/BO1/BO2 仅作 CODREF/CODDIFF 反编译参照 | VERIFIED（AUDIT.md） |
| EV-R-OlMod-NoEvidence | `.runtime/natural-match/<ts>/` 在 C:/D:/E:/F:/G: 全盘不存在；仓库内无 Golden Copy；记录中的“已验证客户端 EXE 哈希”与本机任何 EXE 不匹配 | VERIFIED（缺口） |
| EV-R-OlMod-Substitute | ol-mod 有 3 处非 CODOL 资产/数据替代，其中 2 处默认开启（与“禁止 MW2/IW4X 资产替代”冲突） | VERIFIED（AUDIT.md） |
| EV-R-Cod4x | CoD4x_Server `master` HEAD `ddd65fce1a1093017bad2dbb6840d75d11c0d56f`（2026-09-18），origin `callofduty4x/CoD4x_Server` | VERIFIED |
| EV-R-IW4x-A | iw4x-client 克隆 A HEAD `d1b175da1a25d31043246de103a702b206269e5a`（2026-09-20），511 文件 / 109,496 LOC | VERIFIED |
| EV-R-IW4x-B | iw4x-client 克隆 B HEAD `0699a7e5716ded53bcfa6748bcb89a535f8f39f0`（2026-09-17） | VERIFIED |
| EV-R-IW4x-NoServer | IW4x **没有专用服务器源码**（只产出 DLL）；`iw4x-rawfiles` 本地空克隆 0 文件 | VERIFIED（缺口） |

## C. 2697 服务端协议证据（指令级）

| ID | 证据 | 等级 |
|---|---|---|
| EV-2697-Gate | `_CODOL2697_WriteNativeGamestate` RVA 0xA3DAB 双门控：资源对象 `+0x78F4 != 0` 且 注册结构 `+0x6408 != 0`；任一为 0 则 Com_Printf "withheld" 并 `return 0`（不编码/不排队/不重试） | VERIFIED |
| EV-2697-RegRead | `_CODOL2697_ReadRegistration` RVA 0xA3EA0：fopen/sscanf/CRC32；栈 blob `[ebp-0xC820]` 在 `+0x6408`（= `[ebp-0x6418]`）置 1；`memcpy 0xC814` → `0x14973B00` | VERIFIED |
| EV-2697-ResStruct | 注册结构 base `0x14973B00`，`memset 0xC814`（大小 0xC814）；默认不读取，仅 `codol_target2697Registration` CVar 非空时读取 | VERIFIED |
| EV-2697-GS-Body | `_CODOL2697_WriteGamestate` RVA 0xA21B8 → `_CODOL2697_WriteConfigstrings` RVA 0xA0468（调用点 0xA22C1） | VERIFIED |
| EV-2697-GS-Format | gamestate 编码顺序 `03 <long> <map\0> "mp"\0 <long> <configstrings:04…> <long> <long> 06`（RVA 0xA224C..0xA22F8） | VERIFIED（字段顺序）/ BLOCKED（state 字段语义） |
| EV-2697-CS-Format | configstring：RVA 0xA07F8 写 opcode `0x04`，RVA 0xA0807 写 short count（上限 0x1DD7），编码串/bit 字段，RVA 0xA0997 写终止 `0x06` | VERIFIED（头尾）/ PARTIAL（body bit 编码） |
| EV-2697-RC-Format | `_SV_WriteReliableCommand` RVA 0x8612E：`<0` → Com_Error；`==0` → `01 | long | string`；`>0` → `02 | long | short(length) | data[length]`。写入点 0x8616B/0x8617D/0x86189/0x8619F（0x02）、0x861D0/0x861E2/0x861EE（0x01） | VERIFIED |
| EV-2697-RC-Gate | `_SV_ProfileCommand2697` RVA 0x860DE：archives 未激活或 `CODOL2697_PROFILE_WIRE=text` → 返回 0（回退 0x01）；否则调 `_CODOL2697_ProfileCommandBytes` RVA 0x85D32 | VERIFIED |
| EV-2697-RC-Limits | 边界常量 `0xCCC`、`0x7FFB`、`0xFF`、`0x3FB`、`0x3FC`；长度 1 拒绝；`O → 0x01`、`Z → 0x00`、大写两位 hex 合成字节（小写不接受） | VERIFIED |
| EV-2697-RC-Callers | 上游调用点 0x710B7、0x86DE0（常规更新）、0x873E4（recover）；发送链 `_SV_SendMessageToClient 0x86B06` → `_SV_Netchan_Transmit 0x856B6` | VERIFIED |
| EV-2697-Snap-Wrap | `_CODOL2697_WriteSnapshot` RVA 0xA4FA0 在 0xA4FF7 包装调用 `_CODOL2697_WriteSnapshotReached` RVA 0xA4860；0xA4860 另有调用点 0xA26EB（`_CODOL2697_PrepareHistory` RVA 0xA249D） | VERIFIED |
| EV-2697-Snap-Seq | 已观察序列：player fields/arrays → animations → actors/entities → clients → glass → 内部 `0x06`（RVA 0xA4CAF）→ HUD → 第二遍 actors/entities；随后复制 `0x728`/`0x2C38`/`count*0x1F8`/`count*0x13C`/`count*0x5C` 区域 | VERIFIED |
| EV-2697-Snap-Outer | `_SV_EndClientSnapshot` RVA 0x86F7D 的 0x87104：`_CODOL_Target2697ArchivesActive` false → 写 `0x05`；true → 写 `0x06` | VERIFIED |
| EV-2697-Snap-Op | 初始写 `0x00`（RVA 0xA495D，STATIC-INFERENCE：不证明是网络 opcode）；序列 long（RVA 0xA496E） | PARTIAL |
| EV-2697-Archive-Active | `_CODOL_Target2697ArchivesActive` RVA 0x140133：判 `[edx+0x34] == 0x16D`；`_CODOL_MountTarget2697Archives` RVA 0x1400C3 | VERIFIED（指令）/ STATIC-INFERENCE（`0x16D` 语义） |
| EV-2697-MsgTypes | 旧通道（三样本一致）：gamestate `0x02`、configstring `0x03`、snapshot `0x00`、serverCommand `0x01`、EOF `0x05`。2697 通道：gamestate 起 `0x03` 终 `0x06`、configstring 内部 `0x04` 终 `0x06`、reliable `0x02`、EOF `0x06` | VERIFIED（字节）/ STATIC-INFERENCE（语义） |
| EV-2697-Diag | NEW-only 诊断串：`CoDOL 2697 publication dry encode=%d bytes=%u actual_client_crc=%d`（VA 0x7c419c）、`CoDOL 2697 netconst checksum=%08x seed=%08x`（VA 0x7c416c）、`Read-only verified client registration export for target gamestate publication`（VA 0x7edee0） | VERIFIED |
| EV-2697-Modules | 2697 模块源文件串：snapshot/gamestate/configstrings/registration/publication/history/adapter/fields/actors/anim/arrays/clients/delta/entities/resources/profile + weapon 系列 + `codol_loopback_win32.c` + `codol_netconst_index.c` + `codol_archive_probe.c` | VERIFIED |
| EV-2697-Guards | 11 个 loopback 守卫 `_guard_socket/bind/connect/send/sendto/recv/recvfrom/accept/getaddrinfo/getnameinfo/setsockopt`，RVA 0x98920..0x98f50 | VERIFIED |
| EV-2697-Symbols | NEW 符号（去重）36,980；GCC 16.2.0 符号保留（旧包源码无 2697） | VERIFIED |
| EV-2697-NoSrc | 旧包源码树 `grep 2697` = 0 命中 → 本地无 2697 源码 | VERIFIED（缺口） |

## D. 2697 客户端 / 最终版逆向证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-C-2697-Packed | 直接完整反汇编不可行（TenProtect 包装） | VERIFIED |
| EV-C-2697-Rec-Limits | 恢复镜像缺原始最后 `.tp3`（VA 0xDC11000 起）；`.rimp` RVA 0xDC11000 修复 1536 B `.rdata` 指针表；`.tvm0` RVA 0xD958000 | VERIFIED |
| EV-C-2697-MsgCore | Msg 字节读取核心 RVA 0x1AC1D0（VA 0x5AC1D0）分段/环形缓冲区复制逻辑；名称“Msg_ReadData”为 STATIC-INFERENCE | VERIFIED（指令）/ STATIC-INFERENCE（名称） |
| EV-C-2697-A2E50 | RVA 0xA2E50 读取 `long(4) + short(2) + payload` 并更新槽（0x3FC 上限）；错误串 0xCB83E0/0xCB83E8 仅自引用 | VERIFIED（字段形状） |
| EV-C-2697-Dispatch-Blocked | opcode `0x02` → 分派 → 0xA2E50 未找到：全映像 E8/E9 0 命中；绝对 VA 0x4A2E50 指针 0 命中；裸 RVA 指针 0 命中；已解析跳转表 0 命中；libcurl/SOCKS/QoS 路径未形成控制流 | BLOCKED |
| EV-C-2697-A2D90 | RVA 0xA2D90 有 4 字节读取+游标推进+全局槽更新；不能确认是 reliable command 读取器 | VERIFIED（指令）/ BLOCKED（语义） |
| EV-C-2697-GSStr | 字符串 `gamestateupdate %d` 位于 RVA 0x8B8378，代码引用 RVA 0x56893、0xA2994；0xA2660 是状态/表更新候选 | VERIFIED（引用）/ STATIC-INFERENCE（语义） |
| EV-C-2697-NetCalls | 真实网络调用点：0x602441/0x6029BE/0x6052AD/0x784F7F/0x788135 call [recv]；0x76D65E jmp [recv]；0x775A6E call [recv]；0x775AA2 call [sendto]；0x775ADE call [recvfrom]；0x77592C call [send]；IAT recv 0xBAE490、recvfrom 0xBAE50C | VERIFIED |
| EV-C-2697-NoEof | 客户端 `0x06` 读取/终止判断/长度检查未找到；`UNEXPECTED_EOF` 无直接代码引用；`EXE_CONFIGSTRINGMISMATCH` 无 reader | NOT-OBSERVED / BLOCKED |
| EV-C-2697-Mapping | 校验映射：0x1AC1D0 → VA 0x5AC1D0 → file off 0x1AB5D0；0xA2E50 → VA 0x4A2E50 → file off 0xA2250 | VERIFIED |
| EV-C-2697-NoRuntime | 无运行时解包 dump / 无断点 / 无抓包；静态镜像与运行时映射等价性未证明 | BLOCKED |

## E. OLD / 1113 服务端架构证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-Old-Init | `WinMain`(sys_win32.c:868) → `Sys_Main`(sys_main.c:506) → `Com_Init`(common.c:599) → `NET_Init`(common.c:642→sys_net.c:3694) / `Netchan_Init` / `Huffman_InitMain` / `PHandler_Init` → `SV_Init`(common.c:711→sv_main.c:3717) | VERIFIED |
| EV-Old-Frame | `while(1) Com_Frame()`(sys_main.c:548) → `SV_Frame`(sv_main.c:4951) → `SV_PreFrame` → `G_RunFrame` 循环(4994) → `SV_RunSApiFrame`(5004) → `SV_RunFrameXAC`(5005) → [CODOL] `CODOL_Publish*`(5017-5025) → `SV_SendClientMessages`(5039) → `SV_CalcPings`(5044) | VERIFIED |
| EV-Old-Recv | `NET_UDPPacketEvent`(net_game.c:37) → [loopback OOB rcon 直通] → `CODOL_NetworkReceive`(net_game.c:54→codol_network.c:304) → `SV_PacketEvent`(sv_main.c:2423) → seq==-1 `SV_ConnectionlessPacket`(2328) / else netchan | VERIFIED |
| EV-Old-Connect | `SV_DirectConnect` → client_t CS_FREE→CS_CONNECTED(sv_client.c:750) → `SV_SendClientGameState`(2160) → CS_PRIMED(2272) → 首个 usercmd → `SV_ClientEnterWorld`(1597) → CS_ACTIVE(1631) → `SV_SendClientSnapshot`(sv_snapshot.c:759) | VERIFIED |
| EV-Old-Plugins | 主程序导出 185 `Plugin_*`；8 个插件 DLL 导入 `codol_dedrun.exe`（进程内插件） | VERIFIED / STRONG_CANDIDATE（加载点） |
| EV-Old-Incomplete | `dedicated\README.md`："This is an incomplete port, not a playable CoDOL server."；`CODOL_PORT.md:3537` 列 6 项未完成（native bdDTLS association、CoDOL 连接语法、usercmd 扩展、gamestate/configstrings/snapshot、runtime asset/script、gameplay parity） | VERIFIED（自述） |
| EV-Old-Run | 运行日志 `running=1 bots=12 humans=0` | VERIFIED |

## F. 传输层（bdDTLS）证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-DTLS-Client | C-1113 `.rdata` 存在逐字对应的 Demonware 类名：`bdDTLSAssociation::sendInit/handleInitAck/handleInit/sendCookieEcho/handleCookieAck/sendData/handleData`、`bdDTLSCookieEcho`、`bdDTLSData::serialize/deserialize`、`bdNATTravClient::receiveFrom/sendStage1/sendStage2/connect`、`bdQoSProbe::sendRequest/handleReply`、`bdQoSReplyPacket::deserialize` | VERIFIED |
| EV-DTLS-Wire | NAT 0x0D→0x0C（29 B）；INIT 16 B `01 02`；INIT_ACK 38 B；COOKIE_ECHO 189 B；COOKIE_ACK 114 B `[0]=4,[1]=2`；公钥 100 B；曲线 P-224；DATA 16 B 头 `06 02 tag(2) seq(2) mac8(8) len(2)` | VERIFIED（合成对等体/源码 + C1 字符串）/ UNKNOWN（真实 C1 互操作） |
| EV-DTLS-Conflict | COOKIE_ECHO 长度冲突：189 B（`codol_handshake.c:47`）vs 219 B（C# `CodolProtocol`；DEV-BOOKING-021 §8 记 “cookie+pubkey 219B（/ack 114B）”）。**双方均保留** | SOURCE-CONFLICT |
| EV-DTLS-OpenSSL | 客户端里的 DTLS/ECDH/secp224 字符串来自**静态链接的 OpenSSL 自带表**（OpenSSL x45、DTLS1_ x27、X509 x119、ASN1 x138、OCSP x47、EVP_ x38）——字符串不能作为“CODOL 使用标准 DTLS”的证据 | VERIFIED |
| EV-DTLS-Nat | C# `CodolProtocol.cs:109-117` INIT 16 B `01 02`；`CookieLength=38`；`PublicKeyLength=100`；P224.cs | VERIFIED |
| EV-Netchan-Old | OLD `codol_netchan.c`：头 `{u32 sequence|flags, [u16 qport 仅 server]}`，flags FRAGMENT_BIT 0x80000000 / FORCE_ACK 0x40000000 / ACK 0x20000000 / MASK 0x1fffffff；分片 6 B `{index,last,stride=1162,chunk}`；body 经 `CODOL_Xor`；最多 128 片（1162*128） | VERIFIED（源码） |
| EV-Netchan-CoD4x | CoD4x `netchan.c`：`PACKET_HEADER 10`（4 seq + [2 qport] + 4 fragment start）；`MAX_MSGLEN 0x20000`；`FRAGMENT_BIT (1<<31)`；seq==-1 → OOB | VERIFIED（源码） |
| EV-Netchan-IW4x | IW4x 与 CoD4x 的 `netchan_t` 布局 1:1 相同（共同 Quake3 血统）；CODOL **未发现**该结构 | VERIFIED（DEV-BOOKING-021 §9） |

## G. clc / svc 与服务端命令证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-clc | `sv_client.c:2505` `MSG_ReadBits(&decompressMsg,3)` → 3 位 clc opcode；`net_game_conf.h:85-99` `clc_ops_e`：clc_move=0、clc_moveNoDelta=1、clc_clientCommand=2、clc_EOF=3、clc_nop=4、clc_download=5、clc_sApiData=5 | VERIFIED（服务端分发器） |
| EV-clc-Nohuff | CODOL 分支不做 Huffman 解压（`sv_client.c:2422-2427`） | VERIFIED |
| EV-svc | `sv_snapshot.c:61-62` `SV_WIRE_SERVERCOMMAND=1`、`SV_WIRE_EOF=5`；`net_game_conf.h:64-78` `svc_ops_e`；serverCommand `{0x01, u32 cmdSeq, cstring} xN`；终止 0x05 | VERIFIED（serverCommand）/ STRONG_CANDIDATE（svc_EOF=5） |
| EV-Protocol-Conflict | 内部 codec 187（`codol_wire.h:8` `CODOL_PROTOCOL 187`）vs 出站 connectResponse `protocol\1\shortversion\1.1.1.13`；`codol_connect.c:89-91` 注释记 2026-09-02 实机二分：187 卡住客户端，1 能连 | SOURCE-CONFLICT（内部选择 vs 出站值） |
| EV-RCON | 环回 RCON 控制面：`4x0xff + "rcon <password> <cmd>"`（net_game.c:43-53、sv_main.c:2375）；仅 loopback | VERIFIED |
| EV-sh1x | `codol_match_status.c:38-61`：`sh1x_status map=<m> session_map=<sm> gametype=<gt> type=<t> running=<0|1> humans=<n> bots=<n> maxclients=<n> uids=<csv>` | VERIFIED |
| EV-Old-Legacy | `CODOL_WriteGamestate` RVA 0xA865A（opcode 0x02，终止 0x05）；`CODOL_WriteConfigstrings` RVA 0xA857F（opcode 0x03，终止 0x05）；`SV_WriteSnapshotToClient`（sv_snapshot.c:224）仍用 IW3 序列化器 | VERIFIED |
| EV-Cfg-6519 | 旧实现 configstring 6519 条，武器从 5362 起 | VERIFIED（旧文档/源码） |

## H. 战斗通道 / 平台（DEV-BOOKING-021）证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-Battle-Endpoint | 战斗端点由 21/5 findSessions 会话记录 ① Hostaddress 下发（`build_session_record(host_ipv4, host_port)`）；本工作区实测 127.0.0.1；端口 28960 是下发值，**不是客户端常量** | VERIFIED |
| EV-Battle-Transport | UDP（SOCK_DGRAM/IPPROTO_UDP）；**无证据**是标准 DTLS | VERIFIED（socket 枚举）/ 无证据（DTLS 断言） |
| EV-Battle-RX0 | 017/019 已监听 28960，客户端 `BATTLE_RX=0`（一个包都没发）→ “缺 Battle Server”作为“不进入”的因果解释被 REFUTED | VERIFIED |
| EV-Battle-Sockets | 9 处 socket() 创建点：IPX/NSPROTO_IPX；通用包装；AF_INET+SOCK_DGRAM+IPPROTO_UDP 等 | VERIFIED |
| EV-Battle-EndpointParser | 端点解析器 RVA 0x621E50 写 `{+0x00=4, +0x04=ip(u32), +0x08=port(u16), +0x14=值}`；要求传输对象 `[obj+0x1F0]` state==1；调用者游戏层 0x4F8F25/0x4F9075 | VERIFIED |
| EV-Battle-Cmp | IW4X 相似度 LOW–MEDIUM（无 DTLS/ECDH，无服务器源码）；CoD4X 相似度 MEDIUM（骨架可学，游戏通道无加密，仅 XOR 混淆） | VERIFIED |
| EV-Battle-Distinct | `CODOL_BATTLE_ARCHITECTURE = DISTINCT`（cookie+ECDH+HMAC/AES 战斗通道）+ HYBRID（骨架借 CoD4X、OOB/发现借 IW4x） | VERIFIED |

## I. 大厅 / 复现基线证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-Lobby-Anchor | 2026-10-05 16:36 首次进入正式 Online Lobby（`HANDOFF_20261005_LOBBY_REACHED.md`）；anchor 之后自研 `CODOLServer\lobby_server\` **未再修改一字节** | VERIFIED |
| EV-Lobby-Third | 进大厅用的是第三方 `REF_LOBBY_KIT\lobby_server.py`，不是自研 `CODOLServer\lobby_server\lobby_plain_probe.py`（两个不同服务端） | VERIFIED |
| EV-Lobby-Golden | `GOLDEN-LOBBY-001` STATUS=FROZEN（2026-10-07），`_golden_hashes.json` 为机器可读哈希基线；**只冻结大厅** | VERIFIED |
| EV-Lobby-NoFullPVE | `FULL_PVE = NOT_REPRODUCED`（复现基线只到大堂，未复现完整 PvE） | VERIFIED |

## J. C# / Codec MVP 证据

| ID | 证据 | 等级 |
|---|---|---|
| EV-CS-Selftest | `CODOLCombatServer.exe --selftest`：通过 111 项，失败 3 项（均为 `%TEMP%\codol_*` UnauthorizedAccessException，属测试环境临时目录权限） | VERIFIED |
| EV-CS-Codec | 工作副本新增 `src\Codol\Codec2697.cs`、`Codec2697SelfTest.cs`；`Program.cs` 增加 `--codec-selftest`，不改原 `--selftest` | VERIFIED |
| EV-CS-Build | 原工程 22 源文件 fingerprint `61982c96…`；工作副本 24 源文件 `af48d95a…`；工作副本构建产物 SHA-256 `66B9AE0164F1CFBF2B79149CEBC27D565DB88EF099700E9E96AE483FB6B7E677` | VERIFIED |
| EV-CS-Vectors | 黄金向量（结构向量，非原版抓包）：RC-BIN-001 `02 44 33 22 11 03 00 10 20 30`；RC-TEXT-001 `01 04 03 02 01 61 62 63 00`；GS-001 见 `12_CODEC_MVP_001\03_GOLDEN_VECTOR_CATALOG.md` | VERIFIED（由已确认字段规则构造）/ CONSTRUCTED |

## K. 历史结论 / 冲突登记

| ID | 内容 | 处置 |
|---|---|---|
| EV-Hist-Cookie | COOKIE_ECHO 189 B vs 219 B | SOURCE-CONFLICT，双留 |
| EV-Hist-Protocol | codec 187 vs connectResponse protocol 1 | SOURCE-CONFLICT，双留 |
| EV-Hist-DTLS | “CODOL 使用 DTLS”曾是长期判断；“OpenSSL 静态表”证据将其降级 | 保留旧结论 + 修订记录（见 `16` §7） |
| EV-Hist-IW4x | 任务早期把 IW4x 当作可复用服务器血缘 | 被 EV-R-IW4x-NoServer / EV-R-OlMod-NoIW4x 推翻，保留修订 |
| EV-Hist-ClientMix | 3.3.3.3 与 2.6.9.7 客户端样本混淆风险 | 已在 `00` §2.2 显式隔离 |
---

# === 追加：证据编号补充（UPDATE-2, 2026-10-12） ===

## L'. 第二轮执行的常量级 / 结构级证据

| ID | 证据 | 底层来源 | 等级 |
|---|---|---|---|
| EV-2697-NetchanConst | 2697 二进制常量：`0x489`(1161)、`0x24500`(148736=1162×128)、`0x1fffffff`、`0x70cc729`(=ceil(2³⁷/1162))，读取点 `_CODOL_NetchanTransmit` RVA 0x999B6 / `_CODOL_NetchanTransmitNextFragment` RVA 0x998D8 | S-2697 | VERIFIED |
| EV-2697-SymbolSets | `.text` 函数符号数：2697=9,827 / 1113=12,718 / OLD=12,477；Jaccard：2697↔1113 73.2%、2697↔OLD 70.5%、1113↔OLD 93.1%；同名同 RVA 仅 0.15% | S-2697/S-1113/S-Old | VERIFIED |
| EV-2697-SnapshotOrder | `_CODOL2697_WriteSnapshotReached`：RVA 0xA4CAF 写 `6` 后仍 `call 0x49f2e5`(ReachHud)、`call 0x4a1a65`(WriteEntities)、`call 0x4a1a65` 等 | S-2697 | VERIFIED |
| EV-2697-RCSelect | `_SV_WriteReliableCommand` RVA 0x8612E 指令级：`test eax,eax; js→Com_Error`；`je→0x01`；否则 `MSG_WriteByte(2)`@0x8616B + `WriteLong`@0x8617D + `WriteShort`@0x86189 + `WriteData`@0x8619F | S-2697 | VERIFIED |
| EV-2697-RCGate2 | `_SV_ProfileCommand2697` RVA 0x860DE：先 `call 0x540133`（archives active），再读 CVar `@0x7B98E0`(`CODOL2697_PROFILE_WIRE`) 与 `@0x7B98F7`(`"text"`) 比较；否则 `ecx=0x3fc` → `_CODOL2697_ProfileCommandBytes` RVA 0x85D32 | S-2697 | VERIFIED |
| EV-2697-RegFmt3 | 注册格式串三变体 @VA 0x7C42A0 / 0x7C42C0 / 0x7C42E4；`withheld` @0x7C4261；`_CODOL2697_ReadRegistration` 0xA3EA0：栈帧 0xC8D8、blob `[ebp-0xC820]` 大小 0xC814、`sscanf` 返回须为 3、`kind∈{1,2}`、CRC 通过后写 `[ebp-0x6418]`(=base+0x6408)、`memcpy(0x14973B00, blob, 0xC814)` | S-2697 | VERIFIED |
| EV-C2697-DataGap | C-2697-Rec `.data`：VA 0x8F1000、VSize **0x0D05C420 (218,120,224 B)**、RawSize **0x00049600 (300,544 B)** → **仅 0.138% 在文件内** | C-2697-Rec | VERIFIED |
| EV-C2697-DataPtrs | 上述 `.data` 原始区中已初始化指针：→`.rdata` 18,156、→`.data` 9,084、→`.text` 2,375、→`.tvm0` 56（**部分 vtable 存在**） | C-2697-Rec | VERIFIED |
| EV-C2697-RdataPtrs | `.rdata`（0x142A00 B）含 30,895 个对齐 VA→`.text` 指针、613 个 ≥4 连续指针表；前 0x400 B 有 243/256 u32 →`.rimp`；全域 386 个 →`.rimp`；**→RVA 0xA2E50 的指针 = 0** | C-2697-Rec | VERIFIED |
| EV-C2697-Tvm0Noise | `.tvm0` 内 E8 字节 29,474 个，目标在映像内 23,184 个，落在函数入口（前字节 `0xCC`/`0xC3`）= **0（0.0%）**；同法 `.text` = 130,362/137,010 = **95.1%** | C-2697-Rec | VERIFIED |
| EV-C2697-ParserLive | RVA 0xA0000–0xAFFFF 收到 **1,458** 次 E8 调用、252 个不同目标（最多 0xAFAB0=132 次）→ 该簇**非死代码** | C-2697-Rec | VERIFIED |
| EV-C2697-PackedSecs | C-2697（打包）7 个区段全部名为 `.tp3`（最后一节 VA 0xDC11000 VSize 0x03214000 RawSize 0x00336800） | C-2697 | VERIFIED |
| EV-Scripts-NoProto | 2697 `scripts` 1,341 文件（`.gsc` 1,198）；含 `2697|gamestate|netconst|registration` 者仅 15 个且为游戏逻辑脚本 | 2697 发行包 | VERIFIED |
| EV-IW4x-DualDiff | IW4x 克隆 A（`d1b175da…`）独有 3 文件：`.git-blame-ignore-revs`、`src\Components\Modules\ServerDemo.cpp`、`ServerDemo.hpp`；A=568 / B=565 文件 | 两份克隆 | VERIFIED |

## 独立来源计数（更新）

| 底层原始来源 | 复制次数 | 独立计数 |
|---|---|---|
| S-2697 二进制 | 多篇报告 + 本轮 | **1** |
| C-2697 / C-2697-Rec | 多篇报告 + 本轮 | **1**（同一 SHA 谱系的两种形态） |
| OLD / 1113 源码树 | 多篇报告 + 本轮 | **1** |
| CoD4x_Server | 12/13/20 + 本轮 | **1** |
| IW4x 克隆 A | — | **1** |
| IW4x 克隆 B | — | **1** |
| 2697 发行包 scripts/runtime-assets | 本轮 | **1** |

**纪律重申：** 本轮新增的全部证据均**派生自既有原始样本**，因此**不增加独立来源数量**——它们提高的是**同一来源内部的置信度**，而不是独立验证次数。这一点在评估“多份报告都说 X”时必须坚持。

---

# === 追加：E-08 Configstring Body 逆向结果（UPDATE-3, 2026-10-12） ===

> 任务：`E-08 2697 Configstring Body 静态逆向与客户端协议交叉验证`
> 完整报告与原始输出：`D:\BaiduNetdiskDownload\使命召唤OL\E08_CONFIGSTRING_BODY_001\`
> 纪律：只读静态；未启动样本；本段为**追加**，不覆盖既有条目。

## EV-08-01 — 服务端 configstring body 位编码（**已闭合**）

`_CODOL2697_WriteConfigstrings` RVA **0xA0468**（入口）.. **0xA04E2**（`leave; ret`）；栈帧 `0x1E28`。

写入顺序（DIRECT，逐指令）：

```
0x04                          WriteByte(4)   @ RVA 0xA07F8
count1                        WriteShort     @ RVA 0xA0807   ← 2 字节（mov ecx,2）
A1  字符串表                  每项: 索引增量 + (strlen+1) 字节（含 NUL）@ RVA 0x99651
A2  索引+值                   10-bit count; 每项: 索引增量 + 10-bit 值
A3  定长记录（步长 0x4C）      10-bit count; 每项: 索引增量 + 10-bit + 7-bit + 4-bit n + n×12-bit
0x06                          WriteByte(6)   @ RVA 0xA0997
```

**索引增量（RVA 0xA0400，DIRECT）：** `newIdx == lastIdx+1` → 写 1 bit `1`；否则写 1 bit `0` + 13 bit 绝对值。初始 `lastIdx = -1`（故首个索引 0 仅 1 bit）。

**上限/校验（DIRECT）：** 索引 ≤ `0x1DD6` 且去重且落在 0..0x13（跳过 0x12）区间表内；A1 字符串长 ≤ `0x1FFF` 且不含 `0x25`/`0x92`；`count2 ≤ 0x7FF`；A3 字段 ≤ `0x3FF`/`0x7F`/`0xF`/`0xFFF`；总位长 ≤ `0x20000`。任一失败 → `msg+0x14 = 1` 且 `return 0`。

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-01 | 上述 body 结构（索引增量 / A1 / A2 / A3 / 上限 / 失败语义） | VERIFIED（指令级） |

## EV-08-02 — 服务端写入原语族（DIRECT）

| 原语 | RVA | 行为 |
|---|---|---|
| `WriteByte/Short/Long` | 0x99551 / 0x99566 / 0x9957B | `ecx=1/2/4` → 核心位移写入（LE） |
| 核心 | 0x994FC | 逐字节 `(value >> 8k) & 0xFF` → `WriteData` |
| `WriteBits(msg,val,bits)` | 0x99590 | **LSB-first**；`bits > 0x20` → 置错返回 |
| `WriteData` | 0x9949B | 容量检查后 `memcpy`；`used += len` |
| 索引增量写入器 | 0xA0400 | 见 EV-08-01 |
| `strlen` 包装 | 0x365740 | IAT thunk → `msvcrt!strlen`（已解析导入） |

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-02 | 原语族定位与语义 | VERIFIED（指令级 + 导入解析） |

## EV-08-03 — 客户端位读取原语（**两侧位序同构**）

客户端**存在**同构的 LSB-first 位读取原语（54 处）：

```asm
and  ecx, 7      ; bitpos & 7
mov  edx, 1
shl  edx, cl     ; mask = 1 << (bitpos & 7)
shr  eax, 3      ; byte index
mov  al, [buf+eax]
test al, dl
setne al
```

自足函数：**入口 RVA 0x1A07B0，出口 0x1A0807**（`and r,7 / shl / shr r,3 / test / setne / leave / ret`）。
**该 1 位读取函数被 115 个调用点共用。**

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-03 | 客户端 LSB-first 位读取原语（含 0x1A07B0 自足函数、115 个调用者） | VERIFIED（指令级） |

## EV-08-04 — 更正：RVA 0xA0807 / 0xA0997 属**服务端**函数体

| 侧 | RVA 0xA0807 | RVA 0xA0997 |
|---|---|---|
| 服务端 `S-2697` | `_CODOL2697_WriteConfigstrings` 函数体内（`call 0x499566`） | 函数体内（`call 0x499551`，写 `0x06`） |
| 客户端 `C-2697-Rec` | 函数尾 `mov esp,ebp / pop ebp / ret / int3` | `int3` 填充之后（无意义字节） |

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-04 | 0xA0807/0xA0997 的归属更正（服务端 ≠ 客户端） | VERIFIED |

## EV-08-05 — 客户端 `0x1AC1D0` 是**字节**读取，非位读取

既有 E4/E5 称 `0x1AC1D0` 为"Msg 字节复制核心"。本轮确认其为**按字节环形缓冲复制**（`movzx byte [ecx+eax]`），**不含位域逻辑**。位读取在别处（EV-08-03）。

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-05 | 0x1AC1D0 性质澄清 | VERIFIED |

## EV-08-06 — 冲突：`count1` 宽度（8 vs 16 位）

| 侧 | 主张 | 依据 |
|---|---|---|
| 指令级 | **16 位（2 字节）** | 0xA0807 `call 0x499566`；0x99566 `mov ecx,2` |
| 内联注释串 | 暗示 **8 位** | VA 0x7C0A00 `"* %u"`、0x7C0A05 `"** %u %u"` |

**状态：SOURCE-CONFLICT（双留）。** 本轮以指令级 16 位为准，但记录两者可能各自属于函数内**不同**计数字段。

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-06 | count1 宽度冲突 | SOURCE-CONFLICT |

## EV-08-07 — 方法学：VA/RVA 混淆在本项目第三次复发

E-08 期间再现同类错误（把 Capstone 输出的 **VA** 当 **RVA** 查区段表，落入 `.eh_fram` 得到误导反汇编）。已建立强制自检与统一 helper（`E08_CONFIGSTRING_BODY_001\_tools\pe_helper.py`）。

| ID | 证据 | 等级 |
|---|---|---|
| EV-08-07 | 地址基准自检（第三次复发记录） | VERIFIED（方法学） |

## 独立来源计数（更新）

| 底层原始来源 | 独立计数 |
|---|---|
| S-2697 服务端二进制 | 1 |
| C-2697 / C-2697-Rec | 1 |
| OLD/1113 源码树 | 1 |
| CoD4x_Server | 1 |
| IW4x 克隆 A / B | 2 |
| 2697 发行包 scripts/runtime-assets | 1 |

**E-08 新增的全部证据均派生自 S-2697 与 C-2697-Rec**，**不增加**独立来源数量。

---

# === 追加：E-09 Configstring 三大阻断项定向取证（UPDATE-4, 2026-10-12） ===

> 任务：`E-09 Configstring 三大阻断项定向取证与服务器开工准入复核`
> 完整报告与原始输出：`D:\BaiduNetdiskDownload\使命召唤OL\E09_CONFIGSTRING_BLOCKERS_001\`
> 纪律：只读静态；未启动样本；本段为**追加**，不覆盖既有条目。

## EV-09-01 — 客户端 Msg 位读取原语的真实位置（**修正 E-08**）

| 项 | 值 |
|---|---|
| 客户端 `MSG_ReadBits` | **RVA 0x1AC670**（126 个调用点） |
| 客户端 `MSG_ReadData` | RVA 0x1AC1D0（25 个调用点，纯字节复制） |
| 客户端 `MSG_WriteBits` | RVA 0x1AC2B0（141 个调用点） |
| 客户端 `MSG_InitReadOnly` | RVA 0x1AC190 |
| **E-08 曾记为"共享单比特读取器"的 0x1A07B0** | **实为 `.def` 脚本字段读取器**（引用 `mp/playerdata.def` / `mp/playersecuredata.def`，经 `0x1A0660` 取字段定义，再按类型 `cmp eax,9` + 10 项跳转表分派 bit/word/… 读取） |

| ID | 证据 | 等级 |
|---|---|---|
| EV-09-01 | 四个 Msg 原语的 RVA 与语义；0x1A07B0 的性质更正 | VERIFIED（指令级） |

## EV-09-02 — 客户端 Configstring body 消费路径（**PROVEN**）

**入口 `0xA2660`（`0xA2975` 返回）**，读取顺序：

```
count1                     MSG_ReadData(es, &t, 2)   @ 0xA26B2   → 2 字节
A1 循环（count1 次）:
    索引增量判定            call 0x44C8C0             @ 0xA26E2
    13-bit 索引             MSG_ReadBits(es, 0xD)     @ 0xA26F4
    索引上界                cmp edi, 0x1DD7           @ 0xA2702
    索引合法区间            mov cl,[edi+0x2BD0A40]; cmp cl,0x14; cmp cl,0x12  @ 0xA2728..0xA2736
    条目（字符串）          call 0xA25F0              @ 0xA2751
A2: 11-bit 计数 @0xA276C ; 每项 13-bit 索引 @0xA27A8 + 10-bit 值 @0xA27D7
A3: 10-bit 计数 @0xA2879 ; 每项 13-bit 索引 @0xA28A9 + 记录 0xA2480 @0xA28E0
```

**A3 子过程 `0xA2480`：** `10-bit`@0xA2490 + `7-bit`@0xA249B + `4-bit n`@0xA24A7 + `n×12-bit` 内联。

**字符串旁证：** `"** %i %i"`(0xCB8334)、`"* %i"`(0xCB8344)、`EXE_CONFIGSTRINGMISMATCH`(0xCB835C)、`gamestateupdate %d`(0xCB8378)。

| ID | 证据 | 等级 |
|---|---|---|
| EV-09-02 | 客户端 configstring body 读取器与服务端写入**逐字段**对应 | VERIFIED（两侧指令级） |

## EV-09-03 — `count1` = 2 字节（16 位）**裁定**

| 侧 | 证据 |
|---|---|
| 服务端 | `0x99566` 包装 `ecx=2` → 核心 `0x994FC` 中 `ecx` 同时用作拆字节循环次数、`MSG_WriteData` 的 `len`、`value >> 8k` 步长 → **字节数** |
| 客户端 | `0xA26AF push 2` → `MSG_ReadData`；`0xA26B7 movsx eax, word ptr [...]` → **16 位有符号** |
| 8 位假设来源 | `"* %u"`（VA 0x7C0A00）经复核为 `snprintf` **文本**用途，非线格式位宽 |

**裁定：16 位 PROVEN；8 位 REFUTED。**（E-08 的 SOURCE-CONFLICT 状态关闭。）

| ID | 证据 | 等级 |
|---|---|---|
| EV-09-03 | count1 宽度裁定 | VERIFIED |

## EV-09-04 — 服务端位游标的字节边界重同步机制

`MSG_WriteBits`（RVA 0x99590）增长块 **0x9960A–0x99635** 原始字节：

```
f6 47 10 07 75 cc | 8b 47 04 3b 47 08 73 b5 | 3d ff ff ff 1f 77 ae
8d 14 c5 00 00 00 00 | 89 57 10  ← bitpos = used*8
8b 17 8d 48 01 89 4f 04 c6 04 02 00
```

即：当 `bitpos % 8 == 0` 时，**强制 `bitpos = used*8`**（丢弃落后偏移），然后 `used++` 并追加 0 字节。

**A1 字符串不占位：** `WriteLenStr`（0x99651）**全函数**无 `[msg+0x10]` 访问（脚本核对 `out_c09.txt`: `result: False`）→ 字符串按裸字节写入，后续位字段在边界处**跳过**它们。

| ID | 证据 | 等级 |
|---|---|---|
| EV-09-04 | 位游标重同步 + A1 字符串不占位 | VERIFIED（指令 + 原始字节） |

## EV-09-05 — `0x06` 位边界（服务端已闭合 / 客户端未定位）

| 项 | 裁定 |
|---|---|
| 服务端写入点 | `WriteByte(6)` @ **0xA0997**（DIRECT） |
| `0x06` 起始 bitpos | 依输入而变（模型：44 / 53 / 61 / **72** / 129）；**不总字节对齐** |
| 客户端 `0x06` 读取 | **未定位**（`0xA2660` 循环结束即 `ret` @0xA2975） |
| 端到端终止语义 | **BLOCKED**（缺读取侧） |

| ID | 证据 | 等级 |
|---|---|---|
| EV-09-05 | configstring 终止符位边界（服务端写入侧闭合） | VERIFIED（服务端）/ BLOCKED（客户端） |

## EV-09-06 — 新识别阻断项（BLK-7 / BLK-8）

| ID | 内容 |
|---|---|
| BLK-7 | **外层消息分派器未定位**（读取 `0x04` / `0x06` 的 switch）；`0xA2660` 无此逻辑 |
| BLK-8 | `0x06` 究竟为"位流内 8 位常量"还是"需字节对齐的外部标记" |

## 独立来源计数（更新）

E-09 的全部证据派生自 **S-2697** 与 **C-2697-Rec** 两个既有原始来源，**独立来源数量不变**（仍为 6 个底层来源）。
