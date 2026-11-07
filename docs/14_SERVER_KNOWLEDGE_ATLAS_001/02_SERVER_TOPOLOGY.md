# 02 — 服务端拓扑 / SERVER TOPOLOGY

> 证据 ID 见 `_EVIDENCE_REGISTER.md`。等级：VERIFIED / STATIC-INFERENCE / NOT-OBSERVED / BLOCKED。

## 1. 三服务端总体形态

| 维度 | S-Old (OLD) | S-1113 | S-2697 |
|---|---|---|---|
| 目标客户端 | 1.1.1.13 (C-1113) | 1.1.1.13 (C-1113) | 2.6.9.7 (C-2697) |
| 源码 | 有（CoD4x fork，24.4 MB） | 有（与 OLD 同源，1 文件差异） | **无** |
| 进程数 | 1 | 1 | 1（原生层）+ Python 启动器 |
| 插件模型 | 185 `Plugin_*` 导出 + 8 DLL | 185 `Plugin_*` 导出 | 185 `Plugin_*` 导出 + 11 loopback 守卫 |
| 线程 | 主线程 `while(1) Com_Frame()` + 看门狗 + 地图加载线程 | 同 OLD | 同族（含新增文件/句柄探测） |
| 网络端口 | UDP 单端口复用 | 同 | UDP 单端口 + 2697 archive 门控 |
| 2697 层 | 无 | 无 | **有** |
| 构建工具链 | ld 2.30，20 节区，无 DYNAMIC_BASE | ld 2.47，11 节区，DYNAMIC_BASE | ld 2.47，11 节区，DYNAMIC_BASE，GCC 16.2.0 |
| 证据 | EV-S-Old, EV-R-OldSrc | EV-S-1113, EV-R-OldSrc-1113 | EV-S-2697, EV-2697-* |

**核心：** 三者是**独立构建**。S-Old 与 S-1113 共享同一份 CODOL 移植源码（仅 1 处玩法改动），因此二者“几乎同源”；S-2697 **无源码**，只能反汇编。

---

## 2. S-Old / S-1113 模块拓扑（源码级 VERIFIED）

```
codol_dedrun.exe (x86, ImageBase 0x400000)
├── 平台层
│   ├── win32\sys_win32.c        WinMain
│   ├── sys_main.c               Sys_Main / 主循环 / 看门狗
│   └── win_net.c / sys_net.c    socket / UDP 事件
├── 引擎公共层
│   ├── common.c                 Com_Init / Com_Frame
│   ├── cvar.c / cmd.c / filesystem.c / common_io.c
│   ├── msg.c                    MSG_* 序列化
│   ├── netchan.c                QUAKE 通道
│   ├── huffman.c                Huffman 压缩
│   └── zone memory / PMem
├── 服务端层
│   ├── sv_main.c                SV_Init / SV_Frame / SV_SpawnServer
│   ├── sv_client.c              SV_DirectConnect / SV_ClientEnterWorld
│   ├── sv_snapshot.c            SV_WriteSnapshotToClient (IW3 serializer)
│   ├── sv_game.c / sv_world.cpp / sv_bot* 
│   └── g_*                      game VM 侧
├── CoDOL 专用层（#ifdef CODOL_SERVER）
│   ├── codol\net\codol_network.c      CODOL_NetworkReceive
│   ├── codol\net\codol_handshake.c    INIT/COOKIE 握手
│   ├── codol\net\codol_crypto.c       EncryptRecord/DecryptRecord
│   ├── codol\net\codol_ecdh.c         P-224
│   ├── codol\net\codol_netchan.c      分片/XOR
│   ├── codol\snapshot\*               76 文件（configstring/entity/delta/frame）
│   └── codol\weapon\* / codol\char\* / codol\script\*
└── 插件层
    └── 8 DLL（导入 codol_dedrun.exe 的 Plugin_* 导出）
```

证据：EV-Old-Init, EV-Old-Frame, EV-Old-Recv, EV-Old-Plugins, EV-Old-Legacy。

---

## 3. S-2697 模块拓扑（反汇编级 VERIFIED）

S-2697 在 S-Old/S-1113 的骨架上**叠加**一个 2697 专属层（源码文件名以字符串形式保留）：

```
codol_dedrun.exe (x86, ImageBase 0x400000, 7,295,919 B)
├── 沿用：win32 / sys_main / common / cvar / netchan / huffman / sv_main / sv_client / sv_snapshot
├── 2697 专属层（NEW-only 源文件串）
│   ├── codol_2697_snapshot.c        _CODOL2697_WriteSnapshot / _WriteSnapshotReached
│   ├── codol_2697_gamestate.c       _CODOL2697_WriteGamestate / _WriteNativeGamestate
│   ├── codol_2697_configstrings.c   _CODOL2697_WriteConfigstrings
│   ├── codol_2697_registration.c    _CODOL2697_ReadRegistration   ← 门控
│   ├── codol_2697_publication.c     _CODOL2697_PublicationAudit_f
│   ├── codol_2697_history.c         _PrepareHistory / _FinishHistory
│   ├── codol_2697_adapter.c         _CODOL2697_Adapt*
│   ├── codol_2697_fields.c          _CODOL2697_*Field
│   ├── codol_2697_actors.c          _CODOL2697_WriteActors
│   ├── codol_2697_anim.c            _CODOL2697_WriteAnimations
│   ├── codol_2697_arrays.c          _CODOL2697_WritePlayerArrays
│   ├── codol_2697_clients.c         _CODOL2697_WriteClients
│   ├── codol_2697_delta.c           _WriteDeltaValue / _ReachDeltaValue
│   ├── codol_2697_entities.c        _WriteEntities / _WriteEntityPayload
│   ├── codol_2697_resources.c       _CODOL2697_*Resources
│   ├── codol_2697_profile.c         _CODOL2697_ProfileCommandBytes
│   ├── codol_weapon_2697.c (+core/keys/loader/registry/runtime)
│   ├── codol_loopback_win32.c       11 个 _guard_*
│   ├── codol_netconst_index.c       netconst 索引/校验
│   └── codol_archive_probe.c        归档探测
├── 2697 CVar / 特性串
│   ├── CODOL2697_PROFILE_WIRE
│   ├── CODOL_INVENTORY2697
│   ├── CODOL_RUNTIME_WEAPONS2697
│   └── WireFixture2697
└── 门控全局对象
    ├── 资源对象指针    0x78AEC8  (+0x78F4 标志)
    └── 注册结构        0x14973B00 (大小 0xC814, +0x6408 标志)
```

证据：EV-2697-Modules, EV-2697-Gate, EV-2697-RegRead, EV-2697-ResStruct, EV-2697-Guards, EV-2697-Diag。

### 3.1 2697 的“封装形态”

2697 是 **launcher + 原生 EXE + 脚本/资源** 的三段式封装：

| 层 | 内容 | 体量 |
|---|---|---|
| Python 启动器 | `launch_backend.py`、`lobby_runtime2697.py`、`room_host2697.py`、`run_native_connection.py` 等 | — |
| 原生服务端 | `native\bin2697\codol_dedrun.exe` | 7,295,919 B（1 文件） |
| 资源/脚本 | `runtime-assets\` + `scripts\` + `script-overlay2697\` | 1,797,434,023 B + 19,154,634 B |
| 客户端侧组件 | `client_room2697.dll`、`client_native_loopback.dll`、`client_loopback_guard.exe` | 184,832 / 125,440 / 242,176 B |
| 证据工件 | `evidence\client-registration2697.txt` 等 | — |

证据：EV-2697-Symbols, EV-2697-Modules, EV-Comp-DLLs, EV-Registration。

---

## 4. 与外部参考的拓扑对照

| 维度 | OLD/1113/2697 | CoD4x | IW4x | ol-mod |
|---|---|---|---|---|
| 形态 | 原生 EXE + 插件 | 原生 `cod4x18_dedrun` + 插件 | **DLL-only**（无服务器） | 多 DLL + 注入器 |
| 游戏通道加密 | cookie + ECDH P-224 + HMAC/AES | 仅 XOR 混淆 | 无加密 | CODOL 自身握手 |
| netchan_t 布局 | **未发现**该结构 | Quake3 netchan（PACKET_HEADER 10） | 与 CoD4x 1:1 相同 | 自有 `net_chan_mp.cpp` |
| 目标 | CODOL 1.1.1.13 / 2.6.9.7 | CoD4（IW3） | MW2（IW4） | CODOL 3.3.3.3 |
| 源码 | 部分（2697 无） | 有 | 有（客户端） | 有 |

证据：EV-Netchan-Old, EV-Netchan-CoD4x, EV-Netchan-IW4x, EV-R-IW4x-NoServer, EV-R-OlMod-NoIW4x, EV-Battle-Distinct。

---

## 5. 拓扑结论

1. **三服务端共享 Quake3/CoD 引擎骨架**：`sys_main → common → sv_main` 的初始化/主循环/收包链是同一套命名与控制流（OLD/1113 VERIFIED 源码；2697 STATIC-INFERENCE 同族）。
2. **2697 是“骨架 + 2697 层”**：新增约 20 个 `codol_2697_*` 模块 + 武器/守卫/归档，体量集中在脚本与资源，而非原生逻辑。
3. **2697 层有独立门控**：资源对象 `+0x78F4` 与注册结构 `+0x6408` 双条件，缺一即扣留 gamestate。
4. **CoD4x 可作服务端骨架模板**（事件循环/状态机/槽位/快照复制分离），**但不能作战斗协议模板**（无加密）。
5. **IW4x 无服务器源码**，只能作 OOB/发现/认证信封参考。
6. **ol-mod 独立于 IW4x**，是 CODOL 专有链路重建，目标 3.3.3.3。