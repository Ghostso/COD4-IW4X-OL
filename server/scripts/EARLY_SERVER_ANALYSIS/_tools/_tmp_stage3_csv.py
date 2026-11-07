# -*- coding: utf-8 -*-
import csv, io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\03_PROTOCOL"
os.makedirs(OUT, exist_ok=True)

HEAD = ["消息标识","客户端证据","服务端证据","数据布局","状态条件","响应关系","证据等级","复用判断"]

rows = [
# 1 NAT
["bdNATTrav INTRO 请求/应答 (type 0x0D -> 0x0C)",
 "codoMP_client_shipRetail.exe 字符串表 .rdata: bdNATTravClient::receiveFrom @0x8271132, sendStage1 @0x8271248, sendStage2 @0x8270524, connect @0x8271688; 现有项目 C# CODOL-Combat-Server-v0.1/src/Codol/CodolProtocol.cs:22-25,73-90 (实机抓包常量)",
 "dedicated/src/codol/net/codol_network.c:366-372 CODOL_NetworkReceive 明文分支",
 "29B: [0]=0x0D, [1]=0x02, [2]=0x00, u32 id, 10B MAC, 两个 6B 地址; 应答=请求原样回显仅 [0]->0x0C",
 "明文, 无需 association (pre-DTLS); C1 在 bdDTLS INIT 前等待 type 12 否则 EXE_HOSTUNREACH",
 "INTRO 0x0D -> 应答 0x0C",
 "CONFIRMED",
 "可直接复用"],
# 2 QoS
["bdQoSProbe 探针/应答 (type 0x28 -> 0x29)",
 "codoMP_client_shipRetail.exe 字符串表: bdQoSProbe::sendRequest @0x8261480, handleReply @0x8262552, bdQoSReplyPacket::deserialize @0x8270076, pump @0x8262488; 现有 C# 未实现 (对照缺口)",
 "dedicated/src/codol/net/codol_network.c:326-350 CODOL_NetworkReceive QoS 分支",
 "请求 18B: [0]=0x28, u64 clienttime@1, u32 probeid@9, 4B secId@13, u8 retryflag@17; 应答 27B: [0]=0x29, u32 id@1, u64 time@5, u8 enabled@13, u32 dataSize, u32 0, f32 proctime, u8 hasData",
 "明文, 无 association; 限流 500ms/地址, 50/s 全局",
 "0x28 -> 0x29 (无 association, 不影响游戏)",
 "CONFIRMED",
 "可直接复用"],
# 3 getchallenge
["getchallenge (Path A 明文 OOB)",
 "codoMP_client_shipRetail.exe 字符串表: \"getchallenge 0 \\\"%s\\\"\" @8678472, \"challengeResponse %i\" @8801752, \"challengeResponse\" @8679184",
 "dedicated/src/sv_client.c:271-277 SV_GetChallenge -> codol_connect.c:95-99 CODOL_WriteChallengeResponse; 分派 sv_main.c:2378 SV_ConnectionlessPacket",
 "明文: 4x0xff 前缀 + cstring; 应答 finish()=4x0xff + text + NUL (codol_connect.c:77-83)",
 "pre-connect OOB; challenge = NET_CookieHash(from) (sv_client.c:271)",
 "getchallenge -> challengeResponse <单个整数>",
 "CONFIRMED",
 "可直接复用"],
# 4 connect
["connect -> connectResponse (Path A 明文 OOB)",
 "codoMP_client_shipRetail.exe 字符串表: \"connectResponse\" @8679288, \"connectResponse packet while not connecting.  Ignored.\" @8679340, \"connectResponse from a different address.  Ignored.\" @8679396",
 "dedicated/src/sv_client.c:295 SV_DirectConnect; codol_connect.c:84-93 CODOL_WriteConnectResponse",
 "应答: 4x0xff + \"connectResponse \\mapname\\<map>\\gametype\\<gt>\\sv_maxclients\\<n>\\protocol\\1\\shortversion\\1.1.1.13\" + NUL",
 "challenge 必须匹配 (sv_client.c:375-379); admission 校验 (sv_client.c:336-368)",
 "connect -> connectResponse; challenge 不符 -> error\\nNo or bad challenge",
 "CONFIRMED",
 "可适配 (protocol=1 值需实机复验)"],
# 5 DTLS INIT
["bdDTLS INIT/INIT_ACK (type 0x01/0x02 -> 0x02/0x02)",
 "codoMP_client_shipRetail.exe 字符串表: bdDTLSAssociation::sendInit @0x8273624, handleInitAck @0x8274400, handleInit @0x8274620; 现有 C# CodolProtocol.cs:109-131 TryBuildInitAck",
 "dedicated/src/codol/net/codol_handshake.c:12-39 CODOL_HandshakeInit; codol_network.c:380-410",
 "INIT 16B: [0]=1,[1]=2,[2:4]=0,[4:6]=0,[6:8]=tag!=0,[8:16]=security id; INIT_ACK 38B: [0]=2,[1]=2,[2:4]=clientTag,[14:16]&[16:18]=tag,[18:20]=clientTag,[24:28]=IP,[28:30]=port LE,[30:38]=id",
 "association pending; 校验 security id 与 session key 可用 (codol_network.c:383-392)",
 "INIT -> INIT_ACK; 相同 INIT 重传返回 2 (复用 cookie, 不重建状态)",
 "CONFIRMED (合成加密对等体); 真实 C1 互操作 UNKNOWN",
 "可直接复用"],
# 6 COOKIE
["bdDTLS COOKIE_ECHO/COOKIE_ACK (type 0x03/0x02 -> 0x04/0x02)",
 "codoMP_client_shipRetail.exe 字符串表: bdDTLSCookieEcho::bdDTLSCookieEcho @0x8272396, sendCookieEcho @0x8273784, handleCookieAck @0x8273420; docs/CODOL_ASSOCIATION.md 静态证据: C1 serializer 0xa62220/header 0xa6223a/内嵌 INIT_ACK serializer 0xa62255, 构造器 0xa62539 vtable 0xbe49ac; 现有 C# CodolProtocol.cs:175-185 BuildKeyAck",
 "dedicated/src/codol/net/codol_handshake.c:40-66 CODOL_HandshakeCookie; codol_network.c:411-418",
 "COOKIE_ECHO 189B: [0]=3,[1]=2,[2:4]=init_ack[16:18],[4:6]=0,[6:44]=init_ack(38B),[81:89]=init[8:16],[89:189]=100B 客户端公钥; COOKIE_ACK 114B: [0]=4,[1]=2,[2:4]=init[6:8] peerTag,[6:106]=服务端公钥100B,[106:114]=id",
 "pending -> established; 重复 echo 必须复用缓存应答 (codol_handshake.c:48-51)",
 "COOKIE_ECHO -> COOKIE_ACK (建立 association)",
 "CONFIRMED (合成加密对等体); 真实 C1 互操作 UNKNOWN",
 "可直接复用"],
# 7 DATA
["bdDTLS DATA 记录 (type 0x06/0x02)",
 "codoMP_client_shipRetail.exe 字符串表: bdDTLSData::serialize @0x8275952, deserialize @0x8276028; 现有 C# CodolProtocol.cs:192-244 TryReadData/BuildData",
 "dedicated/src/codol/net/codol_crypto.c:80-120 CODOL_EncryptRecord/CODOL_DecryptRecord; codol_association.c:45-98 CODOL_AssociationOpenDetailed",
 "16B 头: [0]=6,[1]=2,[2:4]=tag LE,[4:6]=counter16 LE,[6:14]=MAC 截断8B,[14:16]=len LE,[16:]=cipher; MAC 输入=record[0:6]+cipher",
 "association established 后; 32 位重放窗口; 失败可用候选 key 轮换 (codol_association.c:45-98)",
 "成功 -> MSG_InitReadOnly + SV_PacketEvent (codol_network.c:431)",
 "CONFIRMED (记录格式); 密码学原语冲突待验证",
 "可适配 (须先解决原语冲突)"],
# 8 netchan
["netchan 头 + 分片 (server 6B / client 4B)",
 "无客户端符号证据; lobby/docs/protocol_map.md B.2 实测 netchan body 头 15B",
 "dedicated/src/codol/net/codol_netchan.c:8-49 CODOL_NetchanProcess; codol_wire.c:22-95 CODOL_WritePacket/CODOL_ReadFragment/CODOL_Xor",
 "头 {u32 sequence|flags, [u16 qport 仅 server]}; flags: FRAGMENT_BIT 0x80000000, FORCE_ACK 0x40000000, ACK 0x20000000, MASK 0x1fffffff; 分片 6B {index,last,stride=1162,chunk}; body 经 CODOL_Xor (对称 XOR)",
 "association 之后; 分片 1162B, 最多 128 片 (CODOL_MAX_MESSAGE=1162*128)",
 "单包 或 分片重组; ACK_BIT 包被丢弃",
 "STRONG_CANDIDATE",
 "可适配"],
# 9 clc
["客户端命令 clc_* (3 位 opcode)",
 "生产端未观测 (仅服务端分发器为证据); lobby/docs/protocol_map.md B.2 body[0] 低 nibble = reliable 命令数, pmove.py:337 clc_move=0x06 仅被识别",
 "dedicated/src/sv_client.c:2505 MSG_ReadBits(&decompressMsg,3); :2515 clc_strings[256]; net_game_conf.h:85-99 clc_ops_e",
 "3 位 opcode: clc_move=0, clc_moveNoDelta=1, clc_clientCommand=2, clc_EOF=3, clc_nop=4, clc_download=5, clc_sApiData=5(表内) ...",
 "CS_ACTIVE; CODOL 分支不做 Huffman 解压 (sv_client.c:2422-2427)",
 "clc_move/clc_moveNoDelta -> SV_UserMove; clc_clientCommand -> SV_ClientCommand; clc_EOF -> 返回",
 "CONFIRMED (服务端分发器)",
 "可适配"],
# 10 svc
["服务端命令 svc_* (CODOL wire 值)",
 "无直接客户端符号; lobby/docs/protocol_map.md B.3 svc_EOF=5 实测 (0x005D82BB/0x005D8354), svc_serverCommand=1, configstring block=3, svc_gamestate=2(live)",
 "dedicated/src/sv_snapshot.c:61-62 SV_WIRE_SERVERCOMMAND=1/SV_WIRE_EOF=5; :97-111 SV_UpdateServerCommandsToClient; net_game_conf.h:64-78 svc_ops_e",
 "serverCommand: {0x01, u32 cmdSeq, cstring} xN (在 snapshot 头之前); 终止 0x05",
 "connected/active",
 "单向 (服务端 -> 客户端)",
 "CONFIRMED (serverCommand); svc_EOF=5 STRONG_CANDIDATE",
 "可适配"],
# 11 protocol conflict
["内部 codec 187 vs connectResponse protocol 1 (冲突)",
 "客户端不暴露该字段 (opaque, 实测 userinfo 仅含数值 key 2490, 无文本 protocol)",
 "codol_wire.h:8 CODOL_PROTOCOL 187; codol_connect.c:89-91 注释; sv_client.c:381-388 version=CODOL_PROTOCOL",
 "N/A (内部选择 vs 出站线值)",
 "N/A",
 "N/A",
 "冲突保留 (不强行统一)",
 "仅供参考"],
# 12 match status
["sh1x_status (lobby 轮询契约)",
 "N/A (lobby 每实例轮询)",
 "dedicated/src/codol/net/codol_match_status.c:38-61 CODOL_MatchStatus_f",
 "文本: \"sh1x_status map=<m> session_map=<sm> gametype=<gt> type=<t> running=<0|1> humans=<n> bots=<n> maxclients=<n> uids=<csv>\"",
 "任意状态; 未加载地图 -> map=none running=0",
 "lobby 查询 -> 状态行",
 "CONFIRMED",
 "可直接复用"],
# 13 RCON loopback
["loopback RCON 控制面 (4x0xff 明文 OOB)",
 "N/A (lobby/运维使用)",
 "dedicated/src/net_game.c:43-53 NET_UDPPacketEvent 环回直通; sv_main.c:2375 rcon",
 "4x0xff + \"rcon <password> <cmd>\"",
 "仅环回 (NA_LOOPBACK 或 127.x); C1 游戏流量不经此路径",
 "rcon -> 命令执行",
 "CONFIRMED",
 "可直接复用"],
# 14 gamestate/snapshot
["服务端 -> 客户端 gamestate/snapshot",
 "无客户端确认证据; lobby/docs/protocol_map.md B.3 svc_snapshot 仍未知 (CODOL_SNAP_OP)",
 "dedicated/src/sv_snapshot.c:224 SV_WriteSnapshotToClient; :759 SV_SendClientSnapshot; sv_client.c:2160 SV_SendClientGameState; docs/CODOL_PORT.md 第 3537 行 \"Required before a client can play\" 第 4 项未完成",
 "作者自述 SV_WriteSnapshotToClient 仍用 IW3 序列化器; configstring 6519 条, 武器从 5362 起",
 "CS_PRIMED / CS_ACTIVE",
 "N/A (下行)",
 "CANDIDATE (未完成)",
 "移植 (尚未完成, 不可直接用)"],
]

csvp = os.path.join(OUT, "EARLY_SERVER_03_PROTOCOL_MATRIX.csv")
with io.open(csvp, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    for r in rows:
        w.writerow(r)
print("wrote", csvp, "rows", len(rows))
