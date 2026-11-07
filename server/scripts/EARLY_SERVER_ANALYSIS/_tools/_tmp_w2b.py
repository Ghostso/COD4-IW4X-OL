# -*- coding: utf-8 -*-
import io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\02_ARCHITECTURE"

arch = r"""# EARLY_SERVER_02 — 服务端架构分析

> 阶段 2 交付物。全部结论基于 `dedicated\src\` 源码与 `bin\` 产物静态证据；**未启动任何样本程序**。
> 标签：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。

## 0. 一句话结论

样本服务端是一个 **CoD4x fork 的原生 CoDOL 移植**（C/C++，Win32 单进程多线程，UDP 单端口多路复用），
**架构骨架完整、可自主运行（跑 bots）**，但按作者自述与源码证据，**是一个"不完整移植、非可玩 CoDOL 服务端"**（`dedicated\README.md` 原文："This is an incomplete port, not a playable CoDOL server."）。

---

## 1. 进程与线程模型（CONFIRMED）

- **单进程**：`codol_dedrun.exe`（x86，ImageBase 0x400000，EP RVA 0x1480），无独立网络/游戏子进程。
- **插件模型**：主程序导出 **185 个 `Plugin_*` 符号**；8 个 DLL 插件（`dedicated\plugins\*`）导入表均引用 `codol_dedrun.exe`，即以**进程内插件**形式被主程序加载（`SV_InitSApi` / `PHandler_Init` 相关）。
- **线程**：
  - 主线程：`WinMain` → `Sys_Main` → `while(1) Com_Frame()`（`sys_main.c:548-550`）。
  - 辅助线程（源码证据）：`Sys_CreateNewThread`（关停看门狗 `Sys_ShutdownWatchdogThread` sys_main.c:581；地图加载看门狗 `sys_loadWatchThread` sys_main.c:630-639）。
- **模块初始化顺序**由 `Com_Init` 统一编排（见 §2）。

---

## 2. 初始化调用链（CONFIRMED）

入口：`dedicated\src\win32\sys_win32.c:868`
```c
int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int)  // :868
  -> return Sys_Main(sys_cmdline);                    // :926
```

顶层：`dedicated\src\sys_main.c:506`
```c
int Sys_Main(char* commandLine)                       // :506
  [--codol-info 分支: 打印 protocol/port, return 0, 不开 socket]   // :509-517
  Sys_SetDefaultInstallPath(DEFAULT_BASEDIR)          // :527
  Sys_TimerInit(); Sys_PlatformInit(); Sys_InitializeCriticalSections(); Sys_InitMainThread();  // :529-535
  Com_InitSmallZoneMemory(); CON_Init(); extractor_init();     // :538-541
  Com_Init(commandLine);                              // :544
  while (1) Com_Frame();                              // :548-550
```

子系统编排：`dedicated\src\common.c:599` `void Com_Init(char* commandLine)`
```
Cbuf_Init -> Cmd_Init -> CODOL_InitAssetCommands -> Com_InitEventQueue
-> Com_ParseCommandLine -> Com_InitCvars -> Cvar_Init -> Sec_Init
-> Com_InitZoneMemory -> FS_InitCvars -> Sys_Init (:367)
-> NET_Init()      [common.c:642]   -> sys_net.c:3694 NET_Init -> NET_Config(qtrue) [sys_net.c:2770]
-> Sec_Update -> FS_InitFilesystem -> Win_InitLocalization -> PMem_Init
-> Netchan_Init(qport) -> Huffman_InitMain -> PHandler_Init
-> SV_Init()       [common.c:711]
```

服务端子系统：`dedicated\src\sv_main.c:3717` `void SV_Init()`
```
SV_AddOperatorCommands -> SV_InitCvarsOnce -> SVC_RateLimitInit -> SV_InitBanlist
-> Init_CallVote -> SV_InitServerId -> SV_MasterHeartbeatInit -> SV_InitSApi -> SV_TryLoadXAC
```

---

## 3. 每帧主循环（CONFIRMED）

`dedicated\src\sv_main.c:4951` `qboolean SV_Frame(unsigned int usec)`
```
SV_PreFrame()                                   // :4991
while (sv.timeResidual >= frameUsec) G_RunFrame();  // :4994  (game VM)
SV_RunSApiFrame();                              // :5004
SV_RunFrameXAC();                               // :5005
#ifdef CODOL_SERVER  (sv.state == SS_GAME)      // :5007-5016
    CODOL_PublishTeamScores();                  // :5017
    CODOL_PublishPlayerScores();                // :5021
    CODOL_RefreshWeaponHud();                   // :5022
    CODOL_PushSecureProfiles();                 // :5025
#endif
SV_SendClientMessages();                        // :5039
SV_CalcPings();                                 // :5044
```

`CODOL_Publish*` 系列**在消息发出前**写入 configstring/快照银行（源码注释明确），是 CoDOL 记分板/武器 HUD/安全档案的下行注入点。

---

## 4. 网络接收链（CONFIRMED）

UDP 收包 → `NET_UDPPacketEvent`（`dedicated\src\net_game.c:37`）
```
NET_UDPPacketEvent(from, data, len, buflen)                     // net_game.c:37
  if loopback OOB RCON -> SV_PacketEvent                        // 直通
  if (CODOL_NetworkReceive(from, data, len)) return;            // net_game.c:54  (CoDOL 加密通道优先)
  PHandler_Event(PLUGINS_ONUDPNETEVENT, ...)                    // 插件钩子
  SV_PacketEvent(from, msg)                                     // 普通 Quake 通道
```

`SV_PacketEvent`（`sv_main.c:2423`）：
```
if (msg seq == -1) SV_ConnectionlessPacket(from, msg);          // sv_main.c:2328
else -> 常规 netchan 消息处理
```

`SV_ConnectionlessPacket`（`sv_main.c:2328`）分派（§见 STATE_MACHINES.md §3）：
`connect`→`SV_DirectConnect`（:2351）、`getchallenge`→`SV_GetChallenge`（:2379）、`getstatus`/`getinfo`/`rcon`/`stats`/`HostMigrationPacket`/`v`/Source-Engine-Query。

CoDOL 加密层入口：`dedicated\src\codol\net\codol_network.c:304` `CODOL_NetworkReceive`
（bdQoSProbe / NAT INTRO / bdDTLS INIT-COOKIE-DATA，详见 `EARLY_SERVER_02_STATE_MACHINES.md`）。

---

## 5. 游戏逻辑模块（`dedicated\src\codol\`，591 文件 / ≈96,686 行）

`makefile` 的 `CODOL_AREAS=net snapshot player weapon vehicle script assets collision stats` 划定 9 区域：

| 区域 | 文件数 | 职责 | 代表文件 |
|---|---:|---|---|
| `net\` | 28 | bdDTLS/握手/关联/连接/准入/消息编解码 | `codol_network.c`, `codol_handshake.c`, `codol_association.c`, `codol_connect.c`, `codol_admission.c`, `codol_wire.h` |
| `snapshot\` | 76 | 快照/configstrings/实体/delta/事件 | `codol_engine_state.c`(140KB), `codol_playerstate_ext.c`(64KB), `codol_configstrings.c`, `codol_frame_builder.c`, `codol_history.c`, `codol_sv_snapshot.c`, `codol_sv_gameframe.c`, `codol_snapshot_pacing.c`, `codol_delta.c`, `codol_entities.c`, `codol_events.c` |
| `player\` | 87 | 玩家状态/移动/动画 | — |
| `weapon\` | 64 | 武器/弹道/装备 | — |
| `vehicle\` | 48 | 载具 | — |
| `script\` | 150 | GSC/内置函数桥 | — |
| `assets\` | 66 | 资产加载/映射 | — |
| `collision\` | 33 | 碰撞 | — |
| `stats\` | 39 | 统计上传/回传 | — |

**非 CoDOL 部分**：`dedicated\src\` 其余 ~1,179 文件是 **CoD4x/IW3 引擎底座**（`sv_main.c`、`sv_client.c`、`sv_snapshot.c`、`net_chan.c`、`common.c`、`sys_*` 等）。CoDOL 逻辑以 `#ifdef CODOL_SERVER` 与 `codol\*` 模块叠加在底座上。

---

## 6. 与作者自述的未完成项（`dedicated\docs\CODOL_PORT.md`，3577 行）

文档第 **3537 行** "Required before a client can play" 列 6 项未完成：
1. native bdDTLS association + lobby handoff
2. CoDOL connection/message grammar
3. usercmd gameplay extensions（引擎 128 槽 vs CoDOL wire ID 1024）
4. gamestate/configstrings/snapshots（6519 configstrings，武器从 5362 起；`SV_WriteSnapshotToClient` 仍用 IW3 序列化器）
5. runtime asset/script compatibility
6. gameplay parity & live acceptance
另：分片 ACK/重传调度待完成。

> 这 6 项与源码证据一致：骨架在，**面向真实 C1 客户端的协议与序列化仍未收敛**。

---

## 7. 结论与置信度

| 命题 | 标签 | 依据 |
|---|---|---|
| 存在真实原生游戏服务端主程序 | CONFIRMED | `codol_dedrun.exe`（185 Plugin_* 导出、EP 0x1480） |
| 服务端能自主启动并跑 game VM | CONFIRMED | `qconsole.log` running=1 bots=12 |
| 有完整初始化/帧循环/网络接收链 | CONFIRMED | sys_main/common/sv_main/net_game 行号证据 |
| 有 CoDOL 专用加密通道实现 | CONFIRMED | `codol\net\*` 源码 |
| 面向真实 C1 客户端可玩 | REFUTED（作者自述）| README + CODOL_PORT.md 6 项未完成 |
| 真实 C1 曾成功进入世界 | NOT_OBSERVED | 运行日志 humans=0 |
"""

callchains = r"""# EARLY_SERVER_02 — 关键调用链

> 阶段 2 交付物（第 3 件）。行号为当前样本实测。标签见各条目。

## 1. 启动链（CONFIRMED）

```
[PE] codol_dedrun.exe  EP RVA 0x1480  IB 0x400000
  -> WinMain                       dedicated\src\win32\sys_win32.c:868
     -> Sys_Main(sys_cmdline)      dedicated\src\sys_main.c:926
        -> Sys_Main                dedicated\src\sys_main.c:506
           -> Sys_TimerInit/PlatformInit/InitializeCriticalSections/InitMainThread   :529-535
           -> Com_InitSmallZoneMemory/CON_Init/extractor_init                         :538-541
           -> Com_Init(commandLine)  dedicated\src\common.c:544 -> :599
              -> NET_Init()          common.c:642 -> sys_net.c:3694 -> NET_Config(qtrue) sys_net.c:2770
              -> SV_Init()           common.c:711 -> sv_main.c:3717
           -> while(1) Com_Frame()   sys_main.c:548-550
```

## 2. 帧循环链（CONFIRMED）

```
Com_Frame (common.c)
  -> SV_Frame                       sv_main.c:4951
     -> SV_PreFrame                 sv_main.c:4991
     -> while(residual) G_RunFrame   sv_main.c:4994   (game VM / bots)
     -> SV_RunSApiFrame             sv_main.c:5004
     -> SV_RunFrameXAC              sv_main.c:5005
     -> [CODOL_SERVER] CODOL_PublishTeamScores/PublishPlayerScores/RefreshWeaponHud/PushSecureProfiles  :5017-5025
     -> SV_SendClientMessages       sv_main.c:5039
     -> SV_CalcPings                sv_main.c:5044
```

## 3. 收包链（CONFIRMED）

```
UDP socket
  -> NET_UDPPacketEvent             net_game.c:37
     -> [loopback OOB rcon] SV_PacketEvent (直通)
     -> CODOL_NetworkReceive        net_game.c:54 -> codol\net\codol_network.c:304
        -> (INIT/COOKIE/DATA) -> SV_PacketEvent(from,&msg)   codol_network.c:431
     -> PHandler_Event(PLUGINS_ONUDPNETEVENT,...)
     -> SV_PacketEvent               sv_main.c:2423
        -> seq==-1 : SV_ConnectionlessPacket   sv_main.c:2328
           -> "connect"      -> SV_DirectConnect(from)        sv_main.c:2351
           -> "getchallenge" -> SV_GetChallenge(from)         sv_main.c:2379
           -> "getstatus"/"getinfo"/"rcon"/"stats"/"v"/SE-Query
        -> else : netchan 消息处理
```

## 4. 客户端入世链（CONFIRMED）

```
SV_DirectConnect
  -> 分配 client_t, CS_FREE -> CS_CONNECTED       sv_client.c:750
  -> SV_SendClientGameState                        sv_client.c:2160
     -> CS_CONNECTED -> CS_PRIMED                  sv_client.c:2272-2273
  -> (收到首个 usercmd)
  -> SV_ClientEnterWorld                           sv_client.c:1597
     -> CS_PRIMED -> CS_ACTIVE                     sv_client.c:1631-1632
  -> SV_SendClientSnapshot                         sv_snapshot.c:759
```

## 5. 地图加载链（CONFIRMED）

```
SV_SpawnServer(mapname)                            sv_main.c:5723
  -> SV_InitGameProgs(savedPersist)                sv_main.c:6099
  -> G_RunFrame (VM)                               (每帧)
```

## 6. 插件加载链（STRONG_CANDIDATE）

```
Com_Init -> PHandler_Init                          common.c (PHandler_Init)
SV_Init  -> SV_InitSApi                             sv_main.c:3717 区域
主程序导出 185x Plugin_*                            codol_dedrun.exe 导出表
8x 插件 DLL 导入 codol_dedrun.exe                    dedicated\plugins\*
```
> STRONG_CANDIDATE：`PHandler_Init`/`SV_InitSApi` 与 185 导出 + 8 插件导入表的对应关系由 PE 证据强支持；未逐行核对每个插件的加载调用点。
"""

with io.open(os.path.join(OUT,"EARLY_SERVER_02_ARCHITECTURE.md"),"w",encoding="utf-8",newline="") as f:
    f.write(arch)
with io.open(os.path.join(OUT,"EARLY_SERVER_02_CALLCHAINS.md"),"w",encoding="utf-8",newline="") as f:
    f.write(callchains)
print("wrote ARCHITECTURE.md and CALLCHAINS.md")
print(sorted(os.listdir(OUT)))
