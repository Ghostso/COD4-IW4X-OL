# E26 消息码方向矩阵

## 1. 客户端侧（E-21..E-25 已证）

客户端会话分派器 `0x6AC0C0` 以 `[esi+0x5CC]`（阶段）与 `[ebp-0xE]`（报文码）二级分派：

| 阶段 `[+0x5CC]` | 报文码 | 处理函数 | 方向证据 |
|---|---|---|---|
| 1 | `0x81` | `0x6AB310`（应答组装 + 入队 + 置阶段 2） | 无直接收发 API 边；`CLIENTCHAL` 字符串线索 |
| 1 | `0x04` | `0x6AAA770`（置 `[+0xC8]=4` 失败） | — |
| 2 | `0x83` | `0x6AB260`（置阶段 3、写 `[+0x5D0]=3`） | 接收计数器被写 |
| 2 | `0x84` | `0x6A9690` | 返回后无条件 `0x6AAA770` |
| 3 | `0x85` | `0x6AAE70`（HMAC + 接收计数器校验） | `Bad recv counter`/`HMAC mismatch` → 偏入站 |
| 3 | `0x84` | `0x6A9690` | 同上 |

E-25 追加：阶段 1 应答经 `0x6AB310 → 0xDAB40 序列化器 → 0x6AA230 入队 → 0x6AA7B0 泵 → 0x783B50 → 0x784E40 → ws2_32!send`（**出站**，PROVEN 五层）。

## 2. 服务端侧（本轮新证）

服务端**客户端→服务端**消息用 **3 位 opcode（0..4）**（`_SV_ExecuteClientMessage` `0x472E77..0x472EB0`）：

| opcode | 处理 | 方向 |
|---|---|---|
| 0 | `_SV_UserMove(...,1)`（`0x473104`） | 入站（客户端移动包） |
| 1 | `_SV_UserMove(...,0)`（`0x47311B`） | 入站 |
| 2 | `_SV_ClientCommand`（`0x473132`） | 入站（客户端命令/字符串） |
| 3 | 无操作返回（`0x47319A`） | — |
| 4 | 拒绝/重读（`0x472E6F`） | — |

服务端**服务端→客户端** servercommand 用：

| 值 | 编码 | 说明 |
|---|---|---|
| `0x01` | `long + string` | legacy serverCommand |
| `0x02` | `long + short(len) + data[len]` | 2697 reliable |
| `0x03` | 2697 gamestate | 2697 通道 |
| `0x04` | 2697 configstring | 2697 通道 |
| `0x05` | legacy EOF | legacy 通道 |
| `0x06` | 2697 EOF/终止 | 2697 通道 |

（来源：本目录 04_PROTOCOL_PATHS / E3 报告；`_SV_WriteReliableCommand` RVA `0x8612E`、`_CODOL2697_WriteGamestate` RVA `0xA21B8`、`_CODOL2697_WriteConfigstrings` RVA `0xA0468`、`_SV_EndClientSnapshot` RVA `0x86F7D`。）

## 3. 两侧对照（判定）

| 维度 | 客户端 | 服务端 | 判定 |
|---|---|---|---|
| 客户端消息 opcode 宽度 | 8 位值（`cmp al,0x81/0x83/0x84/0x85`） | **3 位（0..4）** | **明确冲突** |
| 客户端消息 opcode 取值 | `0x81/0x04/0x83/0x84/0x85` | `0..4` | **明确冲突** |
| 阶段字段 | `[+0x5CC]` = 0/1/2/3 | `_CODOL_HandshakeInit`/`_HandshakeCookie` 用 `[obj+0x238/0x23C/0x50/0x54/0x78]` | **无同构字段** |
| 出站 servercommand | Demonware 对象 slot+3（`0xA87D50`） | `0x01/0x02/0x03/0x04/0x05/0x06` | **无同构** |
| 握手标签 | `CLIENTCHAL`、`BDDATA` | `challengeResponse %d` | **不同族** |
| 共享签名 | `7F 00 00 01`（客户端 2 处） | `7F 00 00 01`（服务端 6 处） | **共享（PROVEN）** |
| 共享标签 | `challengeResponse` | `challengeResponse %d` | **共享（PROVEN）** |

## 4. 方向判定汇总

| 消息 | 方向 | 依据 | 等级 |
|---|---|---|---|
| 客户端 `0x81` 应答 | 出站（客户端→服务端） | E-25 五层链至 `ws2_32!send` | PROVEN |
| 客户端 `0x85` | 入站（服务端→客户端） | `[+0x5D0]` 接收计数器递增 + `Bad recv counter` | INFERRED（强） |
| 服务端 opcode 0/1 | 入站（客户端→服务端） | `_SV_UserMove` 语义 + 3 位读 | PROVEN |
| 服务端 opcode 2 | 入站 | `_SV_ClientCommand` | PROVEN |
| 服务端 `0x02/0x03/0x04` | 出站 | `_SV_WriteReliableCommand`/`_WriteGamestate` | PROVEN |
| 服务端 `challengeResponse` | 出站（服务端响应） | `_CODOL_WriteChallengeResponse` → `0x6DD83` 发送 | PROVEN |

## 5. 禁止的等同

- **`0x81..0x85` ≠ 服务端 `0x01..0x06` servercommand**：前者是客户端 Demonware 对象消息码（8 位），后者是服务端 iD-Tech servercommand（不同方向、不同编码）。
- **`0x81..0x85` ≠ configstring `0x04`/snapshot `0x05/0x06`/demo 子帧**：无论方向还是编码粒度均不同（服务端 `0x04` 是 configstring，客户端 `0x04` 是阶段 1 的失败码）。
- **`0x84` 两侧数值巧合**：客户端 `0x84`（阶段 2/3 处理）与服务端 `0x84` 无语义关联，且服务端 `0x84` 只作为 `cmp eax,0x84` 出现在**非网络**路径（`0xAA5D8` 属浮点/参数解析，`0x165E38`/`0x3416FF` 为日志选择），与协议无关。
