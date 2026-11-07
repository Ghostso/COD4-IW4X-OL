# C 服务器进展（第一阶段：密码学地基）

日期：2026-10-21
位置：`CODOL_SERVER_319_20261021`

## 定位

本工程是**重写**的 CODOL 3.19 战斗服，不是对 `battle_server.py` 的移植。
`battle_server.py` 只作为**线格式参照**（它自己承认的问题：玩家状态不正确、
移动方向不正确、小地图空白）。凡参照与客户端行为冲突处，以客户端为准。

## 已完成并验证：密码学层

| 模块 | 文件 | 验证 |
|---|---|---|
| SHA-1 | `src/crypto/sha1.c` | 3 组标准向量 |
| HMAC-SHA1 | 同上 | RFC 向量 |
| AES-128 | `src/crypto/aes128.c` | FIPS-197 向量 |
| 密钥流 | 同上 | 与参考实现逐字节一致 |
| P-224 ECDH | `src/crypto/p224.c` | 生成元、2G/3G/4G、公钥导入导出往返、**ECDH 共享密钥与参考一致** |
| 传输密钥派生 | 同上 | SHA1(shared_x ‖ securityKey) 前 20B + 4×0 |

测试：`tests/test_crypto.c`、`tests/test_p224.c`、`tests/test_fe.c`
状态：`ctest -C Debug` **6/6 通过**

### 调试中确认的三个坑（已修，留档）

1. **SHA-1 填充缓冲未清零** —— 除 0x80 外全是栈垃圾。
2. **模数 P 多写了一个 limb** —— p = 2²²⁴−2⁹⁶+1 是 224 位 = 7 个 32 位字，
   写成 8 个字后最高字非 0，导致 225 位的和判定"小于 P"而不归约。
3. **e = p−2 未传播借位** —— `e[0] -= 2` 在 p 的最低字为 1 时会跨字借位。

## 已有骨架（第一阶段之前）

platform（时钟/日志/配置）、transport（UDP 收发）、session（连接状态机）、
wire_codec（位流读写）、world_assets、entity、movement、replication、
diagnostics/evidence_gate（证据门控，release 构建拒绝非 3.19 证据的 handler）

## 待实现：战斗服协议

线格式已从参照实现与客户端交互中确认，逐项待写：

| 环节 | 报文形态 |
|---|---|
| NAT 遍历应答 | 29B，`pkt[0]` 13→12 |
| DTLS init → cookie | 收 16B（`01 02 00 00 | tag | 1`）→ 回 38B |
| 密钥交换 | 收 219B（cookie + 100B 公钥）→ 回 114B ack |
| 数据帧 | `06 02 <tag:2> <seq:2> <hmac:8> <len:2> <cipher>`；HMAC-SHA1 前 8B；AES 流 seed=`seq,0,0,tag` |
| OOB 命令 | `getchallenge` / `connect` / `stats` / `heartbeat` |
| game state | `firingrange-gamestate.bin`(259B)，`[8:]` 按 `seq^1` 掩码 |
| 运动快照 | 123/124B（**不是** 141B —— 141B 那版客户端不 ACK） |

## 客户端侧的判据（决定"通了没有"）

- `RX_CLIENT_GAME_HEADER messageAck` **非 0** = 客户端开始消费我方帧
- 快照长度 **123/124B**
- 客户端从"设置游戏"进入靶场场景

## 关键前置（大厅侧，已解决）

1. `firingrange-session.enabled` 存在 → 21/5 必须回 **靶场 session**
   （GameType 0x1000007 / MaxPlayers=1），不能被 playlist 分支覆盖
2. session 的 map 必须与 mmstart 里客户端要加载的 map 一致
3. 出站帧 seq 必须**严格 +1**，应答与推送共用同一计数器
   （否则客户端同秒 ConnectionReset；详见 HANDOFF §13.8）

---

# 第二阶段：msg 位流层（已完成）

| 模块 | 文件 | 验证 |
|---|---|---|
| 位流缓冲 | `src/msg/msg.c` / `include/codol_msg.h` | 位流编码与 Python 参考逐字节一致（`ad4662d9abedbbb7b00438`）；往返读取全字段一致 |

API：`codol_msg_init / begin_reading / write_bits / read_bits / write_byte|short|long / write_data / write_string`，含 `overflowed` 与 `readcount`。

位序：**MSB-first**，与 CoD/Quake 家族一致（结构照 CoD4x `msg_t`）。

# 第三阶段蓝图：netchan（来自 CoD4x，同源直系）

CoD4x `src/netchan.c` 是本工程**内层**（netchan/快照）的结构依据 —— 它是 CoD4 系引擎的直系实现，
比 Python 参照可靠得多（Python 那版在玩家状态/方向/快照上自认有问题）。

线格式（CoD 家族）：

```
uint32 sequence           bit31 = FRAGMENT_BIT
[uint16 qport]            服务端读、发送时不带
if fragmented:
    uint32 fragmentStart
    uint16 fragmentLength
payload
```

行为要点（逐条照 CoD4x）：

- `Netchan_Transmit`：写 `outgoingSequence++`；长度 ≥ `FRAGMENT_SIZE`(1300) 时改走分片路径，每次只发一片
- `Netchan_Process`：读 sequence → 去 FRAGMENT_BIT → 弹掉 qport → 读分片信息 →
  **`sequence <= incomingSequence` 直接丢弃**（乱序/重包）
- 分片缓冲：收 `fragmentSequence` / `fragmentLength` 组装；发侧用 `unsentFragments` + `unsentFragmentStart` 摊开

# 分层归属（重要）

```
┌─ CODOL 私有外层 ────────────────────────────────┐
│ DTLS-like 握手(NAT/init/cookie/密钥交换)          │
│ 数据帧 06 02 tag seq hmac len cipher            │  ← 客户端已验证
│   AES 流(seed=seq,0,0,tag) + HMAC-SHA1 前 8B     │
└──────────────────┬──────────────────────────────┘
                   │ 解出的明文
┌──────────────────▼──────────────────────────────┐
│ CoD 直系内层 (借 CoD4x 结构)                     │
│ netchan: sequence / qport / 分片 / 可靠命令        │
│ msg: 位流 + (待) huffman 压缩                     │
│ snapshot: 实体 delta / baseline                  │
└─────────────────────────────────────────────────┘
```

外层决定"客户端认不认"，内层决定"语义对不对"（玩家状态、移动、小地图）。
参照实现在内层是坏掉的，所以内层必须走 CoD4x 这条路，不能抄 Python。

---

# 第三阶段：netchan（已完成）

| 模块 | 文件 | 验证 |
|---|---|---|
| netchan | `src/netchan/netchan.c` / `include/codol_netchan.h` | 线头布局(seq[+qport]/分片头)、往返、乱序丢弃、分片(3000B→3片) |

## 结构依据：IW4X（IW4 世代，比 CoD4x 更近）

`IW4X/iw4x-client/src/Game/Structs.hpp:7119` 给出 IW4 的 `netchan_t`：

```c
struct netchan_t {
    int outgoingSequence;
    netsrc_t sock;
    int dropped;
    int incomingSequence;
    netadr_t remoteAddress;
    int qport;                 // ★ IW4: 单个 int
    int fragmentSequence;
    int fragmentLength;
    char* fragmentBuffer;
    int fragmentBufferSize;
    int unsentFragments;
    int unsentFragmentStart;
    int unsentLength;
    char* unsentBuffer;
    int unsentBufferSize;
    netProfileInfo_t prof;
};
static_assert(sizeof(netchan_t) == 0x62C);
```

与 CoD4x(IW3) 的差别：**CoD4x 用 `unsigned short qport` + 自加的 `upperqport`；IW4 用单个 `int qport`。**
CODOL 更接近 IW4，因此本工程按 IW4 布局实现。

行为照 CoD4x `src/netchan.c`：发送 `outgoingSequence++`；接收 `sequence <= incomingSequence` 丢弃；
长度 ≥1300 转分片，每次只发一片。

## 本轮抓到的两个真 bug（都是"自己验自己"验不出来的）

1. **msg 位序写反**：字节内写成 LSB-first（`1 << bit`），Quake/CoD 的真实语义是 **MSB-first**（`1 << (7 - bit)`）。
   `0xDE` 会被写成 `0x7B`（位反转）。
   ⚠️ 我最初的"Python 参考向量"是**我自己按同一套错误语义重写的**，所以两边"对上了" —— 验证无效。
   对照 CoD4x 的真实实现才暴露。教训：**参考向量必须来自独立来源**。
2. **`init_readonly` 未设 `cursize`**：只读模式下 cursize=0，一读即判溢出。
   Quake 的 `MSG_InitReadOnly` 会设 `cursize = length`。

## 当前测试

`ctest -C Debug` 共 8 项：evidence_gate / crypto / p224 / fe / msg / netchan / session / wire_codec

---

# 第四阶段：CODOL 战斗服外层（已完成）

| 环节 | 报文 | 测试结果 |
|---|---|---|
| NAT 遍历 | 收 29B(`[0]=13`) → 回 29B(`[0]=12`) | ✅ |
| DTLS init | 收 16B → 回 **38B cookie** | ✅ 布局核对 |
| 密钥交换 | 收 219B → 回 **114B**(含 100B 公钥) | ✅ |
| **传输密钥** | `ECDH P-224` → `SHA1(shared_x‖securityKey)` | ✅ **双方派生一致** |
| 数据帧 | `06 02 tag seq hmac len cipher` | ✅ HMAC+密钥流双向一致 |
| 篡改拒绝 | MAC 校验 | ✅ |

关键实现点（逐条对齐客户端实测）：

- cookie 38B 布局：`02 02 | client_tag:2 | 0:2 | ms:4 | 0:4 | server_tag:2 | server_tag:2 | client_tag:2 | 0:2 | 0:2 | ip:4 | port:2 | 1:8`
- 密钥交换**不对称**用 tag：请求用 server_tag(@2)，响应用 client_tag(@2)，数据帧用 server_tag(@2)
- 密钥交换请求校验：`u16@2==server_tag`、`pkt[6:44]==cookie`、`u64@111==1`、`pkt[119:219]` = 100B 公钥
- 传输密钥 = `SHA1(shared_x_28BE ‖ securityKey16)` 前 20B + `00 00 00 00` = 24B
- securityKey = **16 个 0x01**（build 1649370 对 ID 1 的 live 默认值，不是全 0）
- 数据帧：`auth = pkt[0:6] ‖ pkt[14:]`，HMAC-SHA1(key24, auth) 前 8B；密钥流 seed = `seq_lo,seq_hi,0,0,tag_lo,tag_hi`

# 当前测试总览（9 项，全绿）

evidence_gate · crypto(SHA1/HMAC/AES/keystream) · p224 · fe · msg · netchan · **battle** · session · wire_codec

---

# 第五阶段：接线 + 真实 UDP 端到端（已完成）

## 接线

- `src/battle/battle_service.c`：UDP 包 → NAT / DTLS init / 密钥交换 / 数据帧 → OOB 分发 → 回包
- `codol_transport_set_packet_sink()`：transport 增加"包接收回调"，由 battle 服务接管
- `main.c`：初始化 battle 服务并挂上 sink

## 端到端验证（真实 UDP，独立客户端实现）

`tests/e2e_client.py` 扮演客户端（独立实现，非复用服务端代码），与 C 服务器走完整链路：

```
ok   NAT 回包 type=12
ok   DTLS init 38B cookie, server_tag=0xDD6B
ok   密钥交换 114B, 传输密钥=34d4de66...
ok   OOB getchallenge -> 'challengeResponse 1'
ok   OOB connect -> 'connectResponse'
ok   OOB heartbeat -> 'heartbeatresponse'
ALL PASSED
```

**关键意义**：客户端侧独立算出传输密钥并与服务端一致 → ECDH + 派生 + 帧封装整条链正确，
不是"自己验自己"。

## OOB 应答（参照实现实测格式）

| 命令 | 应答 | 位置 |
|---|---|---|
| `getchallenge <n> "<..>"` | `challengeResponse 1` | 加密数据帧内(`FF FF FF FF` + text + NUL) |
| `connect <..>` | `connectResponse` | 同上 |
| `heartbeat` | `heartbeatresponse` | 同上 |
| `stats` | `statResponse <missing 掩码>` | 同上 |
| `gamestateupdate <stage>` | 无应答(仅记录进度) | — |
| `cancelConnect` | 无应答 | — |

客户端 netchan 帧(≥14B，非 OOB)按 `messageAck=(plain[5:9] & 0x1FFFFFFF)` 记录。

## 当前状态

- 测试：`ctest` 9 项全绿 + 1 项真实 UDP 端到端
- 下一步：**拿真实 3.19 客户端验**（进靶场时会先发 16B DTLS init；日志出现 `TX_DTLS_INIT_ACK` 即第一个活性证据），
  然后补 gamestate(259B) 与运动快照(123/124B)，并接 CoD4x/IW4X 的内层语义修正玩家状态/方向/小地图
