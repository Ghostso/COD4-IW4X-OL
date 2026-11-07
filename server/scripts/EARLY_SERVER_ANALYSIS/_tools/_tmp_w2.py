# -*- coding: utf-8 -*-
import io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\02_ARCHITECTURE"

entrypoints = """artifact,type,relative_path,anchor_kind,anchor_value,role,confidence
codol_dedrun.exe,PE,d edicated/bin/codol_dedrun.exe,ImageBase,0x400000,game server main image,CONFIRMED
codol_dedrun.exe,PE,dedicated/bin/codol_dedrun.exe,EntryPointRVA,0x1480,CRT/entry stub -> WinMain,CONFIRMED
codol_dedrun.exe,PE,dedicated/bin/codol_dedrun.exe,ExportCount,185,all exports are Plugin_* (plugin host ABI),CONFIRMED
WinMain,function,dedicated/src/win32/sys_win32.c:868,int WINAPI WinMain(HINSTANCE,HINSTANCE,LPSTR,int),calls Sys_Main(Sys_GetCommandline()),CONFIRMED
Sys_Main,function,dedicated/src/sys_main.c:506,int Sys_Main(char* commandLine),top-level init then infinite Com_Frame loop,CONFIRMED
Sys_Main --codol-info,function-branch,dedicated/src/sys_main.c:509,--codol-info,prints protocol/port and returns 0 without opening sockets,CONFIRMED
Sys_Init,function,dedicated/src/sys_main.c:367,void Sys_Init(),registers arch/username cvars,CONFIRMED
Com_Init,function,dedicated/src/common.c:599,void Com_Init(char* commandLine),subsystem init orchestration,CONFIRMED
Com_Frame,function,dedicated/src/common.c,-,per-frame pump,CONFIRMED
NET_Init,function,dedicated/src/sys_net.c:3694,void NET_Init(void),network subsystem init,CONFIRMED
SV_Init,function,dedicated/src/sv_main.c:3717,void SV_Init(),server subsystem init,CONFIRMED
SV_Frame,function,dedicated/src/sv_main.c:4951,qboolean SV_Frame(unsigned int usec),per-frame server tick + CODOL publish hooks,CONFIRMED
SV_SpawnServer,function,dedicated/src/sv_main.c:5723,void SV_SpawnServer(const char *mapname),map load,CONFIRMED
SV_InitGameProgs,function,dedicated/src/sv_main.c:6099,SV_InitGameProgs(savedPersist),game VM init,CONFIRMED
""".strip().replace("d edicated","dedicated")

state_machines = r"""# EARLY_SERVER_02 - 状态机与协议状态转移

> 阶段 2 交付物（第 4 件）。全部状态名与转移均来自 `dedicated\src\` 源码，行号为当前样本。
> 结论标签：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

---

## 1. 客户端连接状态机（`client_t.state`）— CONFIRMED

枚举定义：`dedicated\src\server.h:61-66`

| 值 | 名称 | 注释（原文） |
|---|---|---|
| 0 | `CS_FREE` | can be reused for a new connection |
| 1 | `CS_ZOMBIE` | client has been disconnected, but don't reuse |
| 2 | `CS_CONNECTED` | has been assigned to a client_t, but no gamestate yet |
| 3 | `CS_PRIMED` | gamestate has been sent, but client hasn't sent a usercmd |
| 4 | `CS_ACTIVE` | client is fully in game |

转移证据（行号 CONFIRMED）：

```
CS_FREE --[SV_DirectConnect 分配 client_t]--> CS_CONNECTED      src\sv_client.c:750
CS_CONNECTED --[SV_SendClientGameState 发送 gamestate]--> CS_PRIMED   src\sv_client.c:2272-2273
CS_PRIMED --[收到首个 usercmd -> SV_ClientEnterWorld]--> CS_ACTIVE    src\sv_client.c:1631-1632
任意态 --[SV_DropClient]--> CS_ZOMBIE                            src\sv_client.c (drop 路径)
```

关键函数：
- `SV_SendClientGameState` — `dedicated\src\sv_client.c:2160`（前置守卫 `if(client->state < CS_PRIMED)` @ 2259）
- `SV_ClientEnterWorld` — `dedicated\src\sv_client.c:1597`
- 快照发送 `SV_SendClientSnapshot` — `dedicated\src\sv_snapshot.c:759`

**尚未观察到**（NOT_OBSERVED）：CS_ZOMBIE 的精确赋值行；`SV_DropClient` 中把 state 置为 CS_ZOMBIE 的语句本轮未逐行定位（函数存在，语义与 IW4 一致）。

---

## 2. bdDTLS 握手状态机 — CONFIRMED（合成对等体）/ UNKNOWN（真实 C1）

实现：`dedicated\src\codol\net\codol_network.c:304` `CODOL_NetworkReceive`（单入口分发）。

| 入站 | 条件 | 出站 | 证据 |
|---|---|---|---|
| `0x28` bdQoSProbe (18B) | 明文，无需 association | `0x29` bdQoSReply (27B) | codol_network.c:326-349 |
| NAT INTRO REQ (type 13, ver 02 00, 29B) | 明文 | type 12 原样回显 | codol_network.c:366-371 |
| INIT (type 1/2, 16B) | 匹配 security ID + 有 session key | INIT_ACK (38B) | codol_network.c:380-410；`CODOL_HandshakeInit` codol_handshake.c:12 |
| COOKIE_ECHO (type 3/2, 189B) | 已有 pending INIT + key | COOKIE_ACK (114B) → association established | codol_network.c:411-418；`CODOL_HandshakeCookie` codol_handshake.c:40 |
| DATA (type 6/2) | `p->used && p->handshake.established` | 解密后 `SV_PacketEvent` | codol_network.c:419-431 |

状态推进：
```
(空) --INIT--> pending --COOKIE_ECHO--> established --> DATA 记录解封 --> SV_PacketEvent
```
- 关联建立：`CODOL_AssociationStart` — `dedicated\src\codol\net\codol_association.c:15`（P-224 共享 X + 16B security → 24B DATA key）
- 记录封包/解封：`CODOL_AssociationSeal` @ :32 / `CODOL_AssociationOpenDetailed` @ :45（record[0]==6,record[1]==2；[2:4]=local_tag；[4:6]=seq lo；[14:16]=len；32 位重放窗口）
- 关联槽：PEERS 64（codol_network.c），每槽 1 地址；INIT 可替换旧地址（`replacing`）。

**未验证**（UNKNOWN）：上述握手只在 `docs\CODOL_ASSOCIATION.md` 记录的**合成加密对等体**上完成；**真实 C1（1.1.1.13 客户端）握手从未在隔离环境跑通**（无运行验证）。

---

## 3. 应用层连接状态机（connect/challenge）— CONFIRMED（代码）/ NOT_OBSERVED（真实客户端回环）

入口：`SV_ConnectionlessPacket`（`dedicated\src\sv_main.c:2328`）分派：

```
"getstatus"/"getinfo"   -> 直接回包
"rcon"                  -> 远程控制
"connect"               -> SV_DirectConnect(from)          sv_main.c:2351
"getchallenge"          -> SV_GetChallenge(from)           sv_main.c:2379
"stats"                 -> SV_ReceiveStats
"HostMigrationPacket"   -> SV_HostMigrationReadPacket
"v"                     -> SV_VoicePacket
Source Engine Query     -> SVC_SourceEngineQuery_Info
```

CoDOL 专用响应生成（`dedicated\src\codol\net\codol_connect.c`）：
- `CODOL_WriteConnectResponse` @ :84 → `connectResponse \mapname\..\gametype\..\sv_maxclients\..\protocol\1\shortversion\1.1.1.13`（4 个 0xff 前缀 + 尾 NUL）。
  - **冲突证据（保留）**：内部 codec 常量 `CODOL_PROTOCOL 187`（`codol_wire.h:8`），但 connect-response 里 `protocol` 字段写死为 `1`；源码注释含 2026-09-02 bisect 记录。**两者不可互相替换。**
- `CODOL_WriteChallengeResponse` @ :95 → `challengeResponse %d`
- `CODOL_ReadConnectUserinfo` @ :35 → 取 userinfo 参数 2（含 xuid/challenge/qport/dvar 2490=-1157214325）

**NOT_OBSERVED**：真实 C1 对本服务的 connect/getchallenge 往返未在隔离环境验证。

---

## 4. 运行态观察到的状态（`bin\home`）— CONFIRMED

- `dedicated\bin\home\main\qconsole.log` 尾部：`map=mp_killhouse_sh gametype=combat running=1 humans=0 bots=12 maxclients=16`
  - 说明服务端**能自主运行并跑 bots**（SV_SpawnServer → SV_InitGameProgs → G_RunFrame 全链跑通）。
  - `humans=0`：**从未有真实客户端成功进入世界**（与 C# 现有战斗服"收包=0"呼应）。
- `dedicated\bin\codol_crash.txt`：两次 "unexpected exit()"，帧 `codol_dedrun_next.exe+0x38c7`（2026-10-04）。
- `dedicated\bin\sys_error.txt`：`Sys_Error: script compile error bad syntax bar.x = -barWidth / 2;`（GSC 脚本编译错误，非网络问题）。
"""

with io.open(os.path.join(OUT,"EARLY_SERVER_02_ENTRYPOINTS.csv"),"w",encoding="utf-8",newline="") as f:
    f.write(entrypoints + "\n")

with io.open(os.path.join(OUT,"EARLY_SERVER_02_STATE_MACHINES.md"),"w",encoding="utf-8",newline="") as f:
    f.write(state_machines)

print("wrote ENTRYPOINTS.csv and STATE_MACHINES.md")
print(os.listdir(OUT))
