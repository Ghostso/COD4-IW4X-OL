# LOBBY_PROTOCOL_TRACE — A 层：大厅服务器协议

**目标版本：** CODOL 3.19.26.22 / Build 1649370
**分析对象：** `COD OL\codoMP_client_shipRetail.exe`（`36997674…`）+ `codoMP_client_shipRetailBase.dll`（`ef75220d…`）
**性质：** 只读静态追踪。证据等级 `CONFIRMED` / `INFERRED` / `REFERENCE` / `UNKNOWN`。
**边界纪律：** 本节只写大厅；战斗网络见 `BATTLE_PROTOCOL_TRACE.md`；两者之间的交接见 `LOBBY_BATTLE_BRIDGE.md`。

---

## 1. 大厅链总览

```
[TCLS 登录器] --凭据--> [客户端] --Demonware 加密流--> [大厅服务器]
                                     |
                       LobbyProtocol (phase 状态机)
                                     |
                          ServiceRegistry 服务/任务分派
                                     |
                     service 0x06 / task 14  =  Messaging::sendGlobalInstantMessage
                                     |
                              "mmbook ..." 预约请求 / "mmbook accepted" 应答
```

**关键判定：** 大厅协议**不是**直接的 UDP 游戏协议。它是 Demonware 控制面上的**加密流**（消息类型 `0x86`），与战斗 UDP/netchan 是**两套不同的传输与分派**。

---

## 2. 传输与会话初始化

| 项 | 值 | 等级 | 证据 |
|---|---|---|---|
| 大厅/认证端点 | `formal-zone-lsg.codol.qq.com:3074`、`formal-zone-auth.codol.qq.com:3074` | CONFIRMED | `COD OL\dwauth.ini`（明文配置，目标目录） |
| Ticket 字段 | `0x03EA` | CONFIRMED | `COD OL\dwauth.ini` 第 3 行 |
| STUN 端点 | `stun1/2/3-tub.codol.qq.com` | CONFIRMED | `COD OL\stun.ini` |
| 本地启动门禁 | 命名内核对象 `TCLS_SHAREDMEMEMORY` / `TCLS_TASMEMORY_` / `TP3GameGuardShareMapping` | CONFIRMED | `docs/protocol.md` §4（目标 DLL 内硬编码） |
| 启动器链 | `TCLS/Client.exe` → `WeGameLauncher/launcher.exe` → 客户端 EXE | CONFIRMED | `docs/protocol.md` §4；`COD OL\ICH042_stdout.txt` |

**说明：** 客户端 EXE 由 TenProtect 加壳（`.tp3`×5 + `.tvm0`），启动前必须通过本地 TCLS 共享内存检查。**该门禁在客户端本地，不在服务端协议层。**

---

## 3. 大厅消息分派（Demonware 层）

| 项 | 值 | 等级 | 证据 |
|---|---|---|---|
| 阶段状态机 | `clientHeader → clientAuth → established` | REFERENCE→CONFIRMED（结构） | `ol-mod\src\backend\Demonware\LobbyProtocol.hpp`（`enum class LobbyPhase`） |
| 加密大厅消息类型 | `0x86`（默认 `encodeEncryptedLobbyMessage(..., messageType=0x86)`） | REFERENCE | 同上（`LobbyProtocol.hpp`） |
| 帧结构 | AES 加密载荷 + HMAC + `u32 sequence` + `u8 messageType` | REFERENCE | 同上（`DecodedLobbyMessage{sequence,messageType,payload}`） |
| 接收入口 | `LobbyProtocol::receive()` → `processFrame` → `processClientHeader/processClientAuth/processServiceMessage` | REFERENCE | 同上 |
| 会话密钥 | `sessionKey`（24B，来自认证） | REFERENCE | `AuthSession.hpp`（`AuthIdentity.sessionKey` 24B） |
| 身份 | `titleId = 1004`、`userId` | REFERENCE | `AuthSession.hpp`（`AuthIdentity`） |

**升级条件（已满足部分）：** title `1004` 与 CodolJoinTrace 的「3.19.26.22」标注一致；端点来自**目标目录自身**明文配置，属 CONFIRMED。**Demonware 帧内部结构仍是 REFERENCE**，因为尚未在目标 EXE 中逐字段命中。

---

## 4. 服务 / 任务注册表与业务消息

| 服务.任务 | 名称 | 载荷形状 | 等级 |
|---|---|---|---|
| `0x06.5` | `Messaging::readQueuedMessages` | — | REFERENCE |
| **`0x06.14`** | **`Messaging::sendGlobalInstantMessage`** | `readU64(recipient); readBlob(message); trailing 必须为空或单个 0x00` | REFERENCE + CONFIRMED（目标侧 payload 形状吻合） |
| `0x06.18` | `Messaging::sendInstantMessage` | — | REFERENCE |

**目标侧实证：** 抓包/运行记录中的 `6/14` payload 形状为
```
0a <u64 SessionId> 13 08 <len 0x1d> <u32 25> "mmbook 796 ..." 00
```
与 ol-mod `InstantMessageService.cpp:56-76` 的解析一致 ⇒ `service 0x06 / task 14` 承载预约消息 = **CONFIRMED（形状）**。

### 4.1 `mmbook` 预约请求（大厅发出）

| 项 | 值 | 等级 | 证据 |
|---|---|---|---|
| `mmbook` 字符串 | VA `0xDC6724`，引用点 `0x0062F7E1`（构造）/ `0x007F1540`、`0x7F1400`（`strncmp`） | CONFIRMED | `DEV-BOOKING\OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030.md` §3 |
| 请求构造器 | `0x0062F7E0` | CONFIRMED | `BOOKING_PROTOCOL_SPEC-002.md` §9 |
| A/B 读取（写入请求） | `0x0062F7F9` / `0x0062F809` | CONFIRMED | 同上 |
| A/B 真实写入 | `0x0062F6F0`（`A=[edi+0x168] → [esi+0x3A048]`，`B=[edi+0x16C] → [esi+0x3A04C]`） | CONFIRMED | 同上 §2.3 |
| 预约数组 | base `this+0x75D8`，stride `0x238`，元素数 `0x6EF0` | CONFIRMED | 同上 §2.2/§2.4 |
| 数组填充器 | `0x0062F840`（vtable `+0x40`），索引写入 `[this+0xE360]`（`0x0062F902`） | CONFIRMED | 同上 §2.2 |
| 预约状态位 | `[this+0x278]` = BOOKING_PENDING/ACTIVE（1 字节，`0x62CCCD`/`0x62FBBB` 置 1） | STRONG_CANDIDATE | 同上 §1 |

### 4.2 `accepted` 预约应答（大厅返回）

| 项 | 值 | 等级 | 证据 |
|---|---|---|---|
| 应答字节（ol-mod 存档） | `13 08 | 13 00 00 00 | 0f 00 00 00 | "mmbook accepted"` | CONFIRMED（ol-mod 单测逐字节断言） | `DemonwareTests.cpp:1602-1606` |
| 保存形态 | 外层 `u32(15)` 前缀 + 15B 文本（**无 NUL**） | 见 `LOBBY_BATTLE_BRIDGE.md` §3（与 023 冲突） | 同上 |
| 解析器 | `0x00632680`（`ret 0x14`，5 参数） | CONFIRMED | `BOOKING_PROTOCOL_SPEC-002.md` §6 |
| 入口守卫 | `0x0063268D cmp byte [esi+0x278],0` / `je 0x006328EB` | CONFIRMED | 同上 §1 |
| 成功副作用 | `0x00632745` 写 `[esp+0x28] = 1` | CONFIRMED | 同上 §9 |
| A/B 回显要求 | `[ebp+8]==[this+0x3A048]`、`[ebp+0xC]==[this+0x3A04C]` | CONFIRMED | 同上 §6 |
| 超时处理 | vtable `+0x13C` = `0x00632A00`；`"mmbook timedout"` @ `0xDC69D4`，引用 `0x00632FB2` | CONFIRMED | `BRIDGE-030` §3 |

---

## 5. 大厅状态机

```
[] --认证--> phase.clientHeader --客户端头--> phase.clientAuth
                                                     |
                                        sessionKey 建立
                                                     v
                                            phase.established
                                                     |
                                      匹配对象 matching 创建
                                                     |
                                  [this+0x278] BOOKING_PENDING
                                                     |
                                      预约数组填充 (0x62F840)
                                                     |
                                        mmbook 请求外发
                                                     |
                          +--------------------------+--------------------------+
                          |                          |                          |
                    accepted 应答             timeout 应答                 拒绝路径
                    (0x632680)               (0x632A00)                (清零 0x6328F7)
                          |                          |
                 [esp+0x28]=1                        v
                          |                   回退/重试
                 [matching+0x288] 闩锁
                          |
                 consumer 0x634402  ->  mmstart 构造器 0x632070
```

| 状态 | 前置 | 触发 | 证据 |
|---|---|---|---|
| BOOKING_PENDING | 匹配对象就绪 | `[this+0x278] = 1` | `0x62CCCD` / `0x62FBBB`（CONFIRMED） |
| BOOKING_ACCEPTED | BOOKING_PENDING | `accepted` 解析成功 | `0x632745`（CONFIRMED） |
| MMSTART_READY | BOOKING_ACCEPTED | `[matching+0x288] = 1`，consumer `0x634402` | STRONG_CANDIDATE |
| MMSTART_SENT | MMSTART_READY | `mmstart` 构造器 `0x632070` | CONFIRMED（构造器存在）/ 未观测（发送） |

---

## 6. mmstart 构造器（当前客户端 CONFIRMED）

| 项 | 值 | 等级 |
|---|---|---|
| 构造器函数 | `0x00632070` | CONFIRMED |
| 格式串 | `"mmstart sv_resetServer; 2486 %d; …"` @ VA `0xDC6800`，引用 `0x00632462` | CONFIRMED |
| 变体 | `"2634 1; start_map_rotate"` @ `0xDC6914`（引用 `0x0063259F`）、`"start_map_rotate_once"` @ `0xDC6930`（引用 `0x006325A6`） | CONFIRMED |
| 内部字段 | `[edi+0x105F8]` / `[edi+0x105FC]` / `[edi+0x105FE]` / `[edi+0x10604]` / `[edi+0x105D8]` | CONFIRMED |
| 字符串格式化 | `call 0x00774980`（sprintf 型） | CONFIRMED |

**注意：** `mmstart` 命令的具体数字 cvar 索引含义（`901/2486/2490/3265/2489/2574/2500`）仍为 `UNKNOWN`。

---

## 7. A 层结论

- **大厅分派边界**：Demonware 加密帧（`0x86`）→ 服务/任务注册表 → `service 0x06 / task 14` → `mmbook`。
- **已确认**：端点、启动门禁、`mmbook` 请求构造与 A/B 配对号、预约数组、`accepted` 解析器与字节、`mmstart` 构造器。
- **未确认**：`accepted` 的传输通道与调用者；Demonware 帧内部字段级结构；`mmstart` 数字 cvar 语义；`[matching+0x288]` 未置 1 的根因。
- **不得声称**：大厅登录成功 = 战斗连接成功；`accepted` 收到 = 已进入战斗。
