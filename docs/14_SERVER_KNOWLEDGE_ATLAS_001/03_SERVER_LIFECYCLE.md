# 03 — 服务端生命周期 / SERVER LIFECYCLE

> 源码级证据来自 OLD/1113（VERIFIED）。2697 为同族 STATIC-INFERENCE（无源码）。

## 1. 进程启动与引擎初始化（S-Old / S-1113，VERIFIED）

```
[PE] codol_dedrun.exe  EP RVA 0x1480 (OLD) / 0x14e0 (1113), ImageBase 0x400000
  └─ WinMain                      win32\sys_win32.c:868
       └─ Sys_Main(sys_cmdline)    sys_main.c:926
            ├─ Sys_SetDefaultInstallPath(DEFAULT_BASEDIR)              sys_main.c:527
            ├─ Sys_TimerInit / Sys_PlatformInit
            │  Sys_InitializeCriticalSections / Sys_InitMainThread     :529-535
            ├─ Com_InitSmallZoneMemory / CON_Init / extractor_init     :538-541
            ├─ Com_Init(commandLine)  common.c:599                    :544
            │    ├─ Cbuf_Init → Cmd_Init → CODOL_InitAssetCommands
            │    ├─ Com_InitEventQueue → Com_ParseCommandLine → Com_InitCvars
            │    ├─ Cvar_Init → Sec_Init → Com_InitZoneMemory
            │    ├─ FS_InitCvars → Sys_Init
            │    ├─ NET_Init()        common.c:642 → sys_net.c:3694 → NET_Config(qtrue)
            │    ├─ Sec_Update → FS_InitFilesystem → Win_InitLocalization → PMem_Init
            │    ├─ Netchan_Init(qport) → Huffman_InitMain → PHandler_Init
            │    └─ SV_Init()         common.c:711 → sv_main.c:3717
            │         └─ SV_AddOperatorCommands → SV_InitCvarsOnce → SVC_RateLimitInit
            │            → SV_InitBanlist → Init_CallVote → SV_InitServerId
            │            → SV_MasterHeartbeatInit → SV_InitSApi → SV_TryLoadXAC
            └─ while (1) Com_Frame()   sys_main.c:548-550
```

**特殊分支：** `--codol-info` 只打印 protocol/port 并 `return 0`，**不开 socket**（`sys_main.c:509-517`）。

## 2. 帧循环（S-Old / S-1113，VERIFIED）

```
Com_Frame (common.c)
  └─ SV_Frame(usec)                             sv_main.c:4951
       ├─ SV_PreFrame()                          :4991
       ├─ while (sv.timeResidual >= frameUsec)
       │     G_RunFrame()                        :4994   ← game VM
       ├─ SV_RunSApiFrame()                      :5004
       ├─ SV_RunFrameXAC()                       :5005
       ├─ #ifdef CODOL_SERVER (state == SS_GAME)
       │     CODOL_PublishTeamScores()           :5017
       │     CODOL_PublishPlayerScores()         :5021
       │     CODOL_RefreshWeaponHud()            :5022
       │     CODOL_PushSecureProfiles()          :5025
       ├─ SV_SendClientMessages()                :5039
       └─ SV_CalcPings()                         :5044
```

**业务含义：** `CODOL_Publish*` 系列 **在消息发出前**写入 configstring/快照银行，是 CODOL 记分板/武器 HUD/安全档案的**下行注入点**。

## 3. 网络接收链（S-Old / S-1113，VERIFIED）

```
UDP socket
  └─ NET_UDPPacketEvent(from, data, len, buflen)      net_game.c:37
       ├─ [loopback OOB rcon] → SV_PacketEvent（直通）  net_game.c:43-53
       ├─ CODOL_NetworkReceive(from, data, len)         net_game.c:54 → codol_network.c:304
       │     ├─ NAT 0x0D  → 回显 0x0C                   codol_network.c:366
       │     ├─ INIT 0x01 → CODOL_HandshakeInit         codol_network.c:380
       │     ├─ COOKIE 0x03 → CODOL_HandshakeCookie     codol_network.c:411
       │     └─ DATA 0x06 → CODOL_AssociationOpenDetailed
       │                     → MSG_InitReadOnly
       │                     → SV_PacketEvent(from,&msg) codol_network.c:431
       ├─ PHandler_Event(PLUGINS_ONUDPNETEVENT, ...)
       └─ SV_PacketEvent(from, msg)                     sv_main.c:2423
            ├─ seq == -1 → SV_ConnectionlessPacket      sv_main.c:2328
            │     ├─ "connect"      → SV_DirectConnect  :2351
            │     ├─ "getchallenge" → SV_GetChallenge   :2379
            │     └─ getstatus / getinfo / rcon / stats / SE-Query
            └─ else → netchan 消息处理
```

## 4. 客户端入世链（S-Old / S-1113，VERIFIED）

```
SV_DirectConnect
  ├─ 分配 client_t：      CS_FREE → CS_CONNECTED     sv_client.c:750
  ├─ SV_SendClientGameState                          sv_client.c:2160
  │     └─ CS_CONNECTED → CS_PRIMED                  sv_client.c:2272-2273
  ├─ (收到首个 usercmd)
  └─ SV_ClientEnterWorld                             sv_client.c:1597
        └─ CS_PRIMED → CS_ACTIVE                     sv_client.c:1631-1632
             └─ SV_SendClientSnapshot                sv_snapshot.c:759
```

## 5. 地图切换与服务器关闭

```
SV_SpawnServer(mapname)                              sv_main.c:5723
  ├─ SV_InitGameProgs(savedPersist)                  sv_main.c:6099
  └─ G_RunFrame (VM)（每帧）
```

- 地图加载看门狗线程：`sys_loadWatchThread`（`sys_main.c:630-639`）。
- 关停看门狗线程：`Sys_ShutdownWatchdogThread`（`sys_main.c:581`）。
- 插件加载：`Com_Init → PHandler_Init`；`SV_Init → SV_InitSApi`（STRONG_CANDIDATE）。

## 6. 2697 生命周期差异（STATIC-INFERENCE）

2697 沿用同族启动/主循环，但**在 gamestate 发布前插入门控**：

```
SV_SendClientGameState
  └─ SV_WriteGameState
       └─ _CODOL_WriteServerGamestate
            └─ _CODOL2697_WriteNativeGamestate  RVA 0xA3DAB
                 ├─ 资源对象 [0x78AEC8]→[+0x78F4] != 0   ？否则 return 0（扣留）
                 ├─ 注册结构 [0x14973B00+0x6408] != 0     ？否则 return 0（扣留）
                 └─ _CODOL2697_WriteGamestate  RVA 0xA21B8
                      └─ _CODOL2697_WriteConfigstrings  RVA 0xA0468
```

**关键：** 门控失败时 `Com_Printf("CoDOL 2697 gamestate withheld: ...")` 然后 **直接 `return 0`**——不延迟、不切旧通道、不排队、不重试。这是 2697 相对旧通道**新增的前置条件**。

---

## 7. 生命周期对照结论（回答问题 3.1）

| 问题 | 结论 | 等级 |
|---|---|---|
| 这些项目主循环结构是否相同？ | OLD/1113/2697 同族（`common → SV_Frame → G_RunFrame`）；ol-mod 有独立 `Appmain`/`FrameHook` | STATIC-INFERENCE（2697）/ VERIFIED（OLD） |
| 相同函数是否在相同调用位置？ | OLD/1113 完全一致；2697 在 `SV_Frame → SV_SendClientMessages` 链上多一层 gamestate 门控 | VERIFIED / STATIC-INFERENCE |
| 初始化顺序是否相同？ | OLD/1113 逐行一致；2697 增加文件/句柄探测导入（`_open_osfhandle` 等） | VERIFIED（导入差分）/ STATIC-INFERENCE（顺序） |
| 相同生命周期来自公共引擎还是独立实现？ | 来自 **公共 Quake3/CoD 引擎骨架**（Id 版权链），CODOL 在其上叠加专用层 | VERIFIED（源码版权 + 同名链） |
| OL-mod 是重用引擎服务端还是插件重实现？ | **混合**：重用原生引擎（注入 + 原生函数绑定）**并**重实现控制面（backend/localnetworking/platformwrapper 插件） | VERIFIED（AUDIT.md + 源码） |
| 2697 大厅/连接生命周期能否映射？ | 连接/入世骨架可映射；**gamestate 门控后的客户端消费不可映射**（BLOCKED） | STATIC-INFERENCE / BLOCKED |
| 哪些映射有调用链证据，哪些只是概念对应？ | 有调用链：OLD/1113 全链、2697 服务端写入链。仅概念：2697→客户端消费链 | 见 `14`/`15` |