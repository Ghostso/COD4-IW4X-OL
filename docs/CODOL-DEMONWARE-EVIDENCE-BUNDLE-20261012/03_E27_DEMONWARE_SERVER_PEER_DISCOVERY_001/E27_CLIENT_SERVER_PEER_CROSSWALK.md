# E27 客户端—服务端对端交叉表

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

## 7. KAT 向量的证据等级（重要限定）

`DemonwareTests.cpp:2466-2477` 与 `codol_crypto.py` 自测使用**同一组** KAT：

```text
sessionKey  = "Shippo fuute, mofu-mofu!" (24B)
transcript  = 0x00..0x3F (64B)
response_id = ea09fd53518d4361     (challenge[8:16])
request_hmac= 96548bb09f4bd93996465628b618c9d3ec09ddd5
response_hmac=4395bd6340aa21bc95d9b77db1c04afc67061382
decrypt     = 71120733ba54e6ff13ded72c69deca7f
encrypt     = b1adf0f2663cde670df4f20fbe37fc2e
```

**限定**：该 KAT 的两份实现（C++ 与 Python）**同源于 `ol-mod` 项目**，因此它证明的是**两套实现彼此一致 + 派生公式内部自洽**（`INFERRED（强）`），**不是**对原版 Demonware 服务端的独立测量。要提升为 `PROVEN`（客户端↔服务端独立交叉验证），需把该派生在 **2697 客户端**内定位并比特级比对（见 E27-NEXT-GATE 第 2 步）。
