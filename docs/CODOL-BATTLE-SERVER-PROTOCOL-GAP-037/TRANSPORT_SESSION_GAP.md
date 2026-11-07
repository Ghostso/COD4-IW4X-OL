# TRANSPORT_SESSION_GAP — 传输层与会话缺口

**目标：** CODOL 3.19.26.22 / Build 1649370  
**纪律：** 区分客户端真实实现、服务器现有实现和推断。

---

## 1. UDP 数据报与消息类型区分

服务器实现：

- `UdpTransport.TryReceive` 单次最多 4096B：`src/Net/UdpTransport.cs:49-77`。
- `ClientLogic.HandlePacket` 先按会话和 transport 解密；再尝试 NAT、DTLS init、key exchange：`ClientLogic.cs:87-204`。
- `CodolProtocol.IsOob` 以四字节 `FF FF FF FF` 识别 OOB：`CodolProtocol.cs:247-250`。
- 连接内消息走 legacy 或 2697 netchan：`ClientLogic.cs:303-306`。

目标证据：

- OOB 命令字面量与发送器/接收器已定位（034）。
- 目标版本是否存在与服务器相同的 NAT/cookie/key exchange/data frame 封装，**未定位**。
- OOB 是否还有额外封装、分片、可靠传输或握手机制，**UNKNOWN**。

**判定：** `FF FF FF FF` OOB 前缀是服务器实现；目标客户端 OOB 响应字面量存在，但完整入站信封/长度规则仍 `UNKNOWN`。

---

## 2. 服务器现有传输握手

| 阶段 | 实现 | 目标证据 |
|---|---|---|
| NAT 29B 探针 | `CodolProtocol.TryBuildNatReply` | 无目标直接证据 |
| DTLS init → 38B cookie | `TryBuildInitAck` | 无目标直接证据 |
| key exchange → 114B ack | `TryHandleKeyExchange` / `BuildKeyAck` | 无目标直接证据 |
| 16B data header + HMAC + AES | `TryReadData` / `BuildData` | 无目标直接证据 |
| 24B transport key | `P224.DeriveTransportKey` | 无目标直接证据 |
| securityKey | 默认 16×`0x01` | 来自实机核实，但 034 未定位目标消费点 |

**结论：** 这套握手是服务器按旧抓包/参考实现移植的，必须保留 `SERVER_IMPLEMENTED` 与 `TEST_VERIFIED` 标识，**不能**升级为 `CLIENT_CONFIRMED`。

---

## 3. 会话绑定

服务器实现：

- 会话键：`ip:port`（`ClientLogic.cs:77-81`）。
- 槽位由权威实体表分配：`ClientLogic.cs:160-179`。
- 同一 peer 重发 DTLS init：已建立 transport 时拒绝重建 cookie；未完成时原地刷新：`ClientLogic.cs:133-159`。
- 重复 connect：不重复计数、不重复恢复：`ClientLogic.cs:267-276`。
- 超时：握手 5000ms / 已连接 15000ms：`ServerConfig.cs`、`ClientLogic.cs:563-575`。
- cancelConnect：直接释放本会话：`ClientLogic.cs:290-294`。

目标证据：

- `cancelConnect` 字面量与 handler `0x1BF1C0` 存在；具体副作用 `UNKNOWN`。
- 目标地址/会话绑定方式未在 034 直接确认。
- 目标重复请求、超时、断开行为未直接确认。

---

## 4. 2697 netchan 与目标版本的关系

服务器 2697 实现：

- 服务端 4B 头 / 客户端 6B 头。
- 29-bit sequence mask。
- 1162×128 分片。
- ACK 位与重放窗口。
- XOR body（challenge ^ outgoingSequence）。

证据来源：本地 2697 服务端证据。

目标 034 证据：

- 镜像中出现 `0x1FFFFFFF` 46 次、`1154` 4 处候选。
- 这些候选**均未绑定**战斗接收链。
- `netchanProcess` 真实入口 `UNKNOWN`。

**判定：** 不能因常量相似就把 2697 netchan 当作目标 3.19.26.22 格式。

---

## 5. 会话清理与错误路径

服务器实现已有：

- 握手失败/超时释放。
- 数据帧 HMAC/长度/tag 拒绝日志：`ClientLogic.cs:107-111`。
- key exchange 的 cookie/serverTag 校验失败日志：`ClientLogic.cs:206-220`。
- 2697 解码失败、stale serverId 日志：`ClientLogic.cs:341-373`。
- shutdown 清空 session/entity/reconnect：`ClientLogic.cs:578-590`。

测试：

- FREEZE-005 记录 `sessions=0 entities=0` 停机清理 PASS。
- 251/251 自测包含会话/实体生命周期测试。

目标证据：

- 目标错误码 `EXE_HOSTUNREACH`、`EXE_CLIENTFAILEDTOCHALLENGE`、`EXE_MATCHENDED`、`EXE_DISCONNECTED` 存在。
- 目标针对各错误的具体状态迁移未闭合。

---

## 6. 传输层关键 UNKNOWN

| 项 | 状态 | 最小验证方法 |
|---|---|---|
| 目标 NAT/cookie/key exchange 入口 | `UNKNOWN` | 从目标网络初始化与 datagram 回调静态向上定位 |
| 目标数据帧头/加密 | `UNKNOWN` | 定位 0x06/0x02 等候选，但不以相似常量下结论 |
| OOB 入站信封与长度 | `UNKNOWN` | 追 `0x1C13A0` 入参、比较分支、长度检查 |
| 目标 netchan 分片/可靠传输 | `UNKNOWN` | 从重建缓冲定位 netchanProcess |
| 目标会话绑定键 | `UNKNOWN` | 定位会话表键来源 |
| 目标超时/断开副作用 | `UNKNOWN` | 追 `0x1BF1C0` 与定时器 |
| 是否存在额外封装/加密 | `UNKNOWN` | 静态 + 只读观测需授权 |

---

## 7. 结论

传输与会话层目前是“服务器实现完整、目标证据稀薄”。现有 FREEZE-005 的 UDP 绑定和自测只证明服务端自身，不证明客户端会按这套封装发起通信。下一任务不得把 legacy/2697 封装外推为目标版本行为。
