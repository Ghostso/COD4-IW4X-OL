# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001")
files={}

files["E27_MODULE_IDENTITY_AND_DEPENDENCY_MAP.md"]=r'''# E27 模块身份与依赖图

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
'''

files["E27_PROTOCOL_SIGNATURE_SEARCH.md"]=r'''# E27 协议标记定向搜索

## 1. 搜索方法（可回溯）

| 项 | 值 |
|---|---|
| 范围 A | `runtime\game\server2697\` 全部 **12,511** 文件（含 `.ff`/`.iwi`/`.mp3` 二进制） |
| 范围 B | 工作区全量文本类文件 **113,920** 个（`.py/.md/.txt/.json/.js/.c/.cpp/.h/.pyc/.lua/.gsc/.cfg/.ini/.log/.csv`） |
| 编码 | ASCII **与** UTF-16LE 双向变体 |
| 标记集 | `bdCore`、`bds`、`demonware`、`CLIENTCHAL`、`BDDATA`、`HMAC mismatch`、`Bad recv counter`、`Bad frame/payload size` |
| 输出 | `_data\sigsearch_all.txt`、`_data\bdtags_ws.txt`（含文件路径 + SHA-256 前 16 位） |
| 目录清单 | `_data\inventory.txt`、`_data\file_list.txt`、`_data\module_hashes.txt` |

## 2. 范围 A：2697 服务端生态结果

| 标记 | 命中文件数 | 说明 |
|---|---:|---|
| `CLIENTCHAL` | **0** | — |
| `BDDATA` | **0** | — |
| `HMAC mismatch` | **0** | — |
| `Bad recv counter` | **0** | — |
| `Bad frame/payload size` | **0** | — |
| `bdCore` | 0 | — |
| `demonware` / `Demonware` / `DEMONWARE` | **2** | `scripts\maps\_credits.gsc`（制作人员表）、`scripts\maps\mp\gametypes\_codol_chat.gsc`（注释） |
| `bds` / `BDS` | 57 | **全部为二进制资源中的字节巧合**（见 §2.1） |

### 2.1 `bds` 命中的性质（重要）

57 个 `bds`/`BDS` 命中里：
- 2 个在 `evidence\attachment-registry2697.json/.txt`（文本，属其它词的子串）；
- 其余 55 个分布在 `.ff`/`.iwi`/`.mp3`/模型二进制中，**ASCII 三字节巧合**（例如浮点/纹理数据中 `62 64 73`）。**不构成协议证据**。

### 2.2 `demonware` 命中的性质（重要）

| 文件 | 行 | 内容 | 性质 |
|---|---|---|---|
| `scripts\maps\_credits.gsc` | 1764/1917/1955/1957/1958 | `initATVICredits_demonware()`、`// Managing Director, Demonware`、`addCenterHeading(&"CREDIT_DEMONWARE")` | **制作人员表**，非协议 |
| `scripts\maps\mp\gametypes\_codol_chat.gsc` | 11 | `// ... on this build that is the Demonware service-102 channel (room.say / room.say2team / party.say, docs/service102_chat.md), because C1.exe has NO 'say' reliable client command` | **注释**：说明"某一构建"的聊天走 Demonware service-102；**不是** 2697 服务端的实现 |

**裁定**：范围 A 内**没有**任何 Demonware 协议实现；`demonware` 仅出现在致谢表与一条注释中。**PROVEN（范围内）。**

## 3. 范围 B：工作区全量文本结果（Demonware 对端存在）

`CLIENTCHAL`/`BDDATA` 在 **108** 处命中（成对出现），分布于 5 类：

| 类 | 代表路径 | 性质 |
|---|---|---|
| **1. C++ 对端实现** | `_e1_regression\ol-mod-olfinal\src\backend\Demonware\Crypto.cpp` | `expandKey(secret,"CLIENTCHAL",16)` / `expandKey(secret,"BDDATA",72)`（L206-207） |
| **2. Python 对端实现** | `REF_LOBBY_KIT\codol_crypto.py`、`GOLDEN-LOBBY-001\REF_LOBBY_KIT\*`、`REF_LOBBY_KIT_CAP009\*` | `derive_session_keys`、`expand_key`、帧编解码 |
| **3. 历史逆向手册** | `CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md`、`KEY_CONTEXT_20260925.txt`、`_mainline\_kdf13d0.py` | `0xD5A4E0 "BDDATA"`、`0xD5A4E8 "CLIENTCHAL"`（**打包客户端** VA） |
| **4. 本项目 E21-E27 交付物** | `E21..E27\*` | 我们自己的报告/脚本 |
| **5. 其它研究** | `run_codol_001\strings_found.txt`、`_e1_regression\ol-mod-olfinal\.agents\research\dw3_feasibility.md` | 研究产物 |

## 4. 关键对比：打包客户端字符串位置

| 客户端 | `BDDATA` VA | `CLIENTCHAL` VA |
|---|---|---|
| **打包** `codoMP_client_shipRetail.exe`（2.6.9.7） | `0xD5A4E0` | `0xD5A4E8` |
| **恢复镜像** `codol2697-static-candidate.bin` | `0xC5B13C` | `0xC5B144` |

（两镜像 VA 不同是 aplib 重排所致；**字符串内容与相邻次序一致**，因此是同一客户端。）

## 5. `0xAB85` 帧标记搜索

| 对象 | `0x00 0xAB` 命中 | `0xAB 0x85` 命中 | 说明 |
|---|---:|---:|---|
| 2697 打包客户端 | 18 | 由恢复镜像验证 | Demonware 帧类型字节 |
| 恢复镜像 | — | **0（对齐）** | 帧类型属**运行时**写入，非静态表 |
| `codol_dedrun.exe` | 0 表项 | 0 | 无 Demonware 帧结构 |

**裁定**：Demonware `0xAB85` 帧标记**不在** 2697 服务端任何模块中；只在客户端与生态外的对端实现中。**PROVEN。**

## 6. 搜索的边界声明

- 范围 A 为 **100% 字节覆盖**（12511/12511）。
- 范围 B 限于**文本类扩展名**；未对工作区全部二进制（数万 `.ff`/`.dll` 等）做全量扫描，故范围 B 的"未命中"**不等于**全局不存在。
- 字符串命中仅证明"文件包含该内容"；用途判定均另附**引用位置/上下文**（见上表"性质"列）。
'''

files["E27_CLIENT_SERVER_PEER_CROSSWALK.md"]=r'''# E27 客户端—服务端对端交叉表

## 1. 客户端侧已知事实（E-21..E-25，不新增假设）

```text
0x6AB310 (阶段1应答状态机; 唯一调用者 0x6AC192 = 分派器 [esi+0x5CC]==1 && msgcode==0x81)
  → 0xDAB40 序列化器 (vtable 0xCBBD24; 缓冲 [ebx+0xC], 写游标 [ebx+0x10])
  → 0x6AA230 (克隆 0x1C 节点 + 头插 [edi+0xB8])
  → 0x6AA7B0 (会话泵)
  → 0x783B50 → 0x784E40 → ws2_32!send
```
会话/认证线索：`CLIENTCHAL`(VA 0xC5B144)、`BDDATA`(0xC5B13C)、`HMAC mismatch`(0xC5B0EC)、`Bad recv counter`(0xC5B110)；阶段字段 `[+0x5CC]`=0/1/2/3；消息码 `0x81/0x83/0x84/0x85`。

## 2. Demonware 对端（生态外，PROVEN）

### 2.1 密钥派生（两侧一致）

**C++**（`ol-mod-olfinal\src\backend\Demonware\Crypto.cpp`）：

```cpp
const auto transcriptHash = sha1(transcript);
const auto secret         = hmacSha1(sessionKey, transcriptHash);   // L205
const auto challenge      = expandKey(secret, "CLIENTCHAL", 16);    // L206
const auto data           = expandKey(secret, "BDDATA", 72);        // L207
//  requestHmac = data[0..20) ; responseHmac = data[20..40)
//  decrypt     = data[40..56) ; encrypt      = data[56..72)
```

**Python**（`REF_LOBBY_KIT\codol_crypto.py`）：

```python
transcript_hash = sha1(transcript)
secret = hmac_sha1(transcript_hash, session_key)
challenge     = expand_key(secret, b"CLIENTCHAL", 16)
data          = expand_key(secret, b"BDDATA", 72)
# response_id = challenge[8:16]  (0x83 的 8 字节)
# request_hmac = data[0:20] / response_hmac = data[20:40]
# decrypt = data[40:56] / encrypt = data[56:72]
```

### 2.2 帧结构（Python `codol_crypto.py` 文档头，逐字段）

```text
u32 total_len( = 整帧长度 - 4 )
u8  0xAB
u8  0x85
u32 seq
u8  iv[16]
u8  cipher[n]      (n 为 16 的倍数; AES-128-CBC)
u8  hmac8[8]       ( = HMAC-SHA1(key, frame[:-8])[:8] )

明文 = u32 payload_len | u8 marker(0x01=任务应答, 0x02=服务端推送) | payload[payload_len]
```

### 2.3 握手函数（Python）

`ticket_from_client_auth` → `session_key_from_ticket` → `build_transcript(hello28, server_ack26, client_auth_frame)` → `derive_session_keys` → `build_handshake_reply` / `build_stage2`。

## 3. 逐项对应（任务书 §C 五问）

| # | 问题 | 结论 | 等级 |
|---|---|---|---|
| 1 | 接收对应数据 | 对端实现**有** `decrypt_task_frame`（`0xAB85` 帧解析）；但**不属 2697 服务端包** | PROVEN（实现存在） |
| 2 | 识别消息边界/标签 | 对端用 `u32 total_len` + `0xAB/0x85`；客户端解码链在 2697 镜像中**未定位到对应函数** | 部分匹配 |
| 3 | 解析应答字段 | 对端 `build_task_reply_objects` 的 TLV = `tag10+u64 replyId`、`tag8+u32 status`、`tag3+u8 task`、`tag8+u32 count` | PROVEN（对端） |
| 4 | 更新会话/握手状态 | 对端 `deriveSessionKeys` 产出 4 个方向密钥，`0x83` 用 `challenge[8:16]` | PROVEN（对端） |
| 5 | 生成客户端可消费的后续消息 | 对端有 `build_push`/`instant_push_body`/`channel_push_body`；有 KAT（`DemonwareTests.cpp`） | PROVEN（对端） |

## 4. 客户端构建适配度（本轮核心冲突）

| 检查 | 结果 |
|---|---|
| 对端实现引用的客户端地址 `0x9CE310`（`bdLobbyConnection::getMessageToDispatch`）在 **2697 恢复镜像** | **不匹配**：RVA `0x5CE310` 处为数据（`3B 11 12 13…`），非该函数 |
| `dw_wire.py` 依据的 `C1.exe.i64` | 面向 **1.1.1.13 / 3.3.3.3**，非 2.6.9.7 |
| 2697 客户端是否 Demonware 客户端 | **是**：`bdLobby`(2)、`dwLobby`(1)、`dwRoom`(38)、`CLIENTCHAL`(1)、`BDDATA`(1) |
| 2697 客户端是否 IW4 谱系 | **是**：`iw4\code_source`(3)、`com_memory.cpp`(1)、`codoMP_client_shipRetail.pdb`(1)、`IWffs100`(1) |
| 2697 客户端 `0xDEADBEEF` | 存在，但为 **写入**（`0x686210 mov [ecx],0xDEADBEEF`），非 `getMessageToDispatch` 的读取比较 |

## 5. 分层架构结论（本轮最重要产出）

```text
CODOL 客户端（2.6.9.7 与 1.1.1.13 均适用）
  ├── Demonware 控制面（大厅/认证）: TCP, 0xAB85 帧, AES-128-CBC + HMAC-SHA1,
  │     CLIENTCHAL / BDDATA 密钥派生        ← 对端在生态外（ol-mod / REF_LOBBY_KIT）
  └── iD-Tech 对局面: UDP 17733, 3 位 clc opcode,
        challengeResponse / 7F000001         ← 对端在 codol_dedrun.exe（E-26 已析）
```

**两侧是不同协议层，不是替代关系。** E-26 的"服务端无 Demonware"应精确表述为"**`codol_dedrun.exe`（对局面）内无 Demonware**"；Demonware 对端**有其独立实现**，只是不在 2697 服务端包内。

## 6. 明确的对应/冲突/未决

| 类别 | 条目 |
|---|---|
| **完全匹配** | 密钥派生算法与标签（`CLIENTCHAL`→16B、`BDDATA`→72B 切分 20/20/16/16）；帧头 `0xAB/0x85`；`0x83` 用 `challenge[8:16]` |
| **部分匹配** | 客户端 `0x81..0x85` 与对端 `0xAB85` 帧的关系：客户端有全部字符串，但对端的"服务/任务"语义未在 2697 镜像中定位 |
| **明确冲突** | 对端引用的客户端 VA（`0x9CE310` 等）在 2697 恢复镜像**不成立** → 对端为**另一构建**的测量 |
| **证据不足** | 2697 服务端是否有**任何**模块承担 Demonware 大厅（本轮 100% 扫描：无） |
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
