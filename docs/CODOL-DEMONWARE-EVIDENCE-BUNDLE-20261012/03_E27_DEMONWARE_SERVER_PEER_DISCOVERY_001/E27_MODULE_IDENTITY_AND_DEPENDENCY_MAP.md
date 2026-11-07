# E27 模块身份与依赖图

## 1. 冻结样本复核

| 角色 | 路径 | SHA-256 | 结果 |
|---|---|---|---|
| 客户端（打包） | `CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | MATCH |
| 客户端（恢复镜像） | `CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | MATCH |
| 服务端 | `...\server2697\native\bin2697\codol_dedrun.exe` | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | MATCH |

## 2. 2697 服务端生态内的 4 个 PE 模块

| 模块 | SHA-256 | 架构 | ImageBase | SizeOfImage | 导入 | 导出 | 角色 |
|---|---|---|---|---|---|---|---|
| `codol_dedrun.exe` | `80816711…0ea1` | i386 (014C) | `0x400000` | `0x15CF0000` | ADVAPI32, CRYPT32, GDI32, KERNEL32, SHELL32, USER32, WINMM, **WS2_32**, msvcrt | **185**（`Plugin_*` = CoD4x/iw4x 插件 API） | iD-Tech 对局服务端（E-26 已析） |
| `client_room2697.dll` | `120c4cfd…c3a7` | i386 | `0x10000000` | `0x39000` | KERNEL32, **WS2_32** | **1**：`LocalRoomPump` | 本地房间泵（loopback） |
| `client_native_loopback.dll` | `53c6fbe2…4829` | i386 | `0x10000000` | `0x24000` | KERNEL32, **WS2_32** | **1**：`LocalMatchBegin` | 本地对局启动（loopback） |
| `client_loopback_guard.exe` | `2d9f99da…505c` | **x64 (8664)** | `0x140000000` | `0x41000` | KERNEL32, RPCRT4, fwpuclnt | 无 | 本地回环守卫（WFP/RPC，无 socket 导入） |

### 2.1 关键网络导入（逐模块）

| 模块 | WS2_32 网络 API |
|---|---|
| `codol_dedrun.exe` | WSAStartup, socket, bind, listen, accept, connect, recv, recvfrom, send, sendto, closesocket, ioctlsocket |
| `client_room2697.dll` | WSAStartup, socket, bind, connect, recv, send, closesocket, ioctlsocket |
| `client_native_loopback.dll` | WSAStartup, socket, bind, connect, recv, send, closesocket, ioctlsocket |
| `client_loopback_guard.exe` | 无（仅 fwpuclnt/RPCRT4） |

## 3. Demonware 标记在 4 个模块中的命中（精确字节扫描）

| 标记 | codol_dedrun | client_room2697 | client_native_loopback | client_loopback_guard |
|---|---|---|---|---|
| `CLIENTCHAL` | 0 | 0 | 0 | 0 |
| `BDDATA` | 0 | 0 | 0 | 0 |
| `bdLobby` | 0 | 0 | 0 | 0 |
| `dwRoom` / `dwLobby` | 0 | 0 | 0 | 0 |
| `HMAC mismatch` / `Bad recv counter` | 0 | 0 | 0 | 0 |
| `0xDEADBEEF`（LE 字节） | 1 | 0 | 0 | 0 |
| `0xAB85` 帧标记 | 0（独立） | 0 | 0 | 0 |

> `codol_dedrun.exe` 的 `EF BE AD DE` 命中属其 iD-Tech/CoD4x 代码，**无** Demonware 帧头 `0xAB85` 结构佐证；不作为 Demonware 证据。

## 4. 与 `codol_dedrun.exe` 的静态依赖/配置关联

- **loopback 三件套**（`client_room2697.dll`、`client_native_loopback.dll`、`client_loopback_guard.exe`）由上层 Python（`run_native_connection.py`、`room_host2697.py`、`batch_guard_client2697.py`）加载，用于**本地对局回环**，与线上 Demonware 控制面无关。
- `codol_dedrun.exe` 与三者**无导入级依赖**（后三者不导入前者；前者不导入它们）。
- 无启动清单、插件注册表或配置文件声明 Demonware 端点/组件。

## 5. 生态外的 Demonware 对端（PROVEN，非 2697 包）

| 实现 | 路径 | 语言 | 握手/派生 |
|---|---|---|---|
| `ol-mod-olfinal` | `使命召唤OL\_e1_regression\ol-mod-olfinal\src\backend\Demonware\Crypto.cpp` | C++ | `deriveSessionKeys`：`hmacSha1(sessionKey, transcriptHash)` → `expandKey(secret,"CLIENTCHAL",16)` / `expandKey(secret,"BDDATA",72)` |
| `ol-mod-olfinal` | 同目录 `LobbyProtocol.cpp`、`Auth3Protocol.cpp`、`ServiceRegistry.cpp`、`InstantMessageService.cpp`、`MatchmakingService.cpp`、`MarketplaceService.cpp`、`Storage2Service.cpp`、`TencentService.cpp` | C++ | 大厅服务分发 |
| `REF_LOBBY_KIT` | `使命召唤OL\REF_LOBBY_KIT\codol_crypto.py`（961 行） | Python | `derive_session_keys`、`expand_key`、`build_handshake_reply`、`build_stage2`、`decrypt_task_frame`、`ticket_from_client_auth`、`session_key_from_ticket` |
| `REF_LOBBY_KIT` | `nt10.py`（169 KB）、`lobby_server.py` | Python | 大厅服务端 |
| Demonware lobby（1.1.1.13） | `CODOL-AlphaBuild_By_Antia(20261006)\...\CODOL_Server\lobby\demonware\`（`dw_wire.py`、`dw_auth.py`、`dw_session.py`、`dw_admission.py`、`tiger_sboxes.py`、`a22_tiger.py`） | Python | 3DES-CBC 帧（`0xDEADBEEF` magic），**无 HMAC**；面向 `C1.exe` 1.1.1.13 |
| `DemonwareTests.cpp` | `ol-mod-olfinal\tests\backend\DemonwareTests.cpp`（150 KB） | C++ | `deriveSessionKeys` KAT 向量 |

## 6. 依赖/归属结论

```text
2697 服务端包 (server2697/)
  ├─ codol_dedrun.exe ............... iD-Tech 对局服务（UDP 17733）      [PROVEN]
  ├─ client_room2697.dll ............ 本地房间泵 LocalRoomPump          [PROVEN]
  ├─ client_native_loopback.dll ..... 本地对局 LocalMatchBegin          [PROVEN]
  ├─ client_loopback_guard.exe ...... 本地回环守卫 (x64, WFP)           [PROVEN]
  └─ *.py / *.gsc / runtime-assets .. 启动器/脚本/资源                  [PROVEN]
  ✗ Demonware 控制面模块（大厅/认证） ................ 不存在 [范围内 PROVEN]

生态外（同工作区，面向其它构建）
  ol-mod-olfinal (C++) / REF_LOBBY_KIT (Python) ... Demonware 对端 [存在]
  CODOL_Server\lobby\demonware (Python) .......... 1.1.1.13 DW lobby [存在]
```

**裁定**：2697 服务端包**不含** Demonware 组件；Demonware 对端在生态外存在，但面向不同客户端构建。
