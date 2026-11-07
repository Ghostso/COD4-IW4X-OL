# EARLY_SERVER_02 — 关键调用链

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
