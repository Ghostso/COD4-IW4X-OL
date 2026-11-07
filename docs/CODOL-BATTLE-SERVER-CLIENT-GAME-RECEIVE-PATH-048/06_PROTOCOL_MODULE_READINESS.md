# 06 — 八类协议模块实现准备度

对每个模块给出:最小必需协议事实 / 已有直接证据 / 可复用的 047 代码 / 尚缺事实 /
能否先实现内部模块 / **能否开始最终 CODOL 兼容实现** / 验收测试与通过标准。

---

## 1. 总览

| # | 模块 | 已有证据级别 | 准备度判定 | 现在能做 |
|---|---|---|---|---|
| 1 | 握手与连接状态 | `DIRECT_STATIC`(OOB token + 方向) | **ReadyForFinalImplementation** | **是(明文连接无关层)** |
| 2 | opcode 分派 | `UNKNOWN` | BlockedOnReceivePathLink | 仅显式拒绝骨架 |
| 3 | reliable commands 与 ACK | `UNKNOWN`(仅错误串) | Blocked | 仅内部模型 |
| 4 | gamestate | `UNKNOWN`(仅诊断串) | BlockedOnReceivePathLink | 仅内部模型 |
| 5 | configstrings | `UNKNOWN`(仅错误串) | BlockedOnReceivePathLink | 仅内部模型 |
| 6 | snapshot 分帧 | `UNKNOWN`(仅日志串) | BlockedOnReceivePathLink | 仅内部模型 |
| 7 | snapshot netfield/delta | `UNKNOWN` | Blocked | 否 |
| 8 | usercmd 与移动同步 | `DIRECT_ARTIFACT`(项目侧,已否证为官方线格式) | InternalModelOnly | 仅内部模型 |

---

## 2. 模块 1:握手与连接状态 —— **唯一可开始最终实现**

**最小必需协议事实(已具备):**
1. 客户端识别的服务端→客户端连接无关命令名集合:
   `challengeResponse / connectReject / connectResponse / heartbeatresponse /
   statResponse / disconnect_ack / echo / keyAuthorize / loadingnewmap / fastrestart`
   (RVA 0x9BFEE8..0x9BFF90;比较点 0x1C1685..0x1C1DF0)。
2. 客户端自身发出的连接无关请求格式:
   `getchallenge 0 "%s"`(0x9BFD04)、`connect %s "%s"`(0x9BFE28)、
   `heartbeat`(0x9BFE40)、`stats`(0x9BFE38)。
3. 客户端把 `connectResponse` 的响应交给会话层:
   `0x1C17B5`(分派)→ `0x1C15AB`(处理)→ 唯一调用者 `0x1F1860`(会话时间/地址写入)。

**已有直接证据:** `03` §2.5、`04` §4;`evidence/048_analysis.json` 的 anchors。

**可复用的 047 代码:** `Sessions\ClientSession`(生命周期/超时)、
`Transport\UdpDatagramTransport`、`Diagnostics\*`。

**尚缺事实(不阻塞握手层的“接收+识别”):**
- 连接无关之上的**密文/压缩**层(若存在)——本轮未证。
- `keyAuthorize` 的载荷格式。

**能否先实现内部模块:** 是。**能否开始最终 CODOL 兼容实现:** 是(**仅限连接无关明文层**)。

**047 本轮实现:** `Protocol\ConnectionlessCommands`(词表)+
`Protocol\ConnectionlessTextDecoder`(最小文法)。
**验收:** 见 `08`;`protocol/connectionless-*` 三项测试。

---

## 3. 模块 2:opcode 分派

- 最小事实:**in-match opcode 表** + 其接收缓冲来源。
- 已有证据:**无**。`0x1C13A0` 是连接无关层,不是 in-match。
- 047 可复用:`Protocol\FinalCodolOpcodeDispatcher`(本轮新增,表为空 + 显式拒绝)。
- 尚缺:**任何**一个经验证的 opcode 数值或「读 opcode → 分支」指令点。
- 内部模块可先做:是(空表 + 拒绝)。
- **最终兼容实现:否。**
- 验收:未知 opcode → `UnknownMessage`;无证据注册被拒;与 2697 不混用。

---

## 4. 模块 3:reliable commands 与 ACK

- 已有证据:仅 `EXE_LOSTRELIABLECOMMANDS` 错误串(错误上报)。
- 尚缺:reliable 命令序号、ACK 位图、重传/超时线上格式。
- 047 可复用:`Reliable\ReliableCommandChannel`(内部窗口/重传/重放拒绝)。
- 内部模型可先做:是。**最终实现:否**(猜 ACK 规则被明令禁止)。
- 验收:内部窗口测试(已有 4 项);线格式一旦出现需与错误上报点区分。

## 5. 模块 4:gamestate

- 已有证据:`CA_GAMESTATE`(0x9C0974)、`EXE_AWAITINGGAMESTATE`(0x9C5F1C)、
  `gamestateupdate %d`(0x9B4700)。**全部为诊断/日志,不是消费者。**
- 尚缺:从收包缓冲到 gamestate 状态转换的直接数据流。
- 047 可复用:`GameState\GameStateModel`、`ConfigStringTable`。
- 内部模型可先做:是。**最终实现:否。**

## 6. 模块 5:configstrings

- 已有证据:`EXE_CONFIGSTRINGMISMATCH`(0x9B46E4)、
  `ExpectedNetConfigStringMismatch`(0x9B4D98)。**均为错误处理。**
- 尚缺:configstring 索引→字符串存储的指令级读/写点(且来源为网络)。
- 047 可复用:`ConfigStringTable`(带边界检查)。
- 内部模型可先做:是。**最终实现:否。**

## 7. 模块 6:snapshot 分帧

- 已有证据:`process snapshots`(0x9BEBD0,xref 0x14B5F8)为**日志**。
- 尚缺:snapshot 的帧边界/分片/结束标记与网络来源。
- 内部模型可先做:是(帧容器抽象)。**最终实现:否。**

## 8. 模块 7:snapshot netfield/delta

- 已有证据:**无**。046 已把 TQOS/TDR 解包器从本模块排除。
- 尚缺:netfield 表、delta 基线与 EOF。
- 内部模型可先做:**否**。**最终实现:否。**

## 9. 模块 8:usercmd 与移动同步

- 已有证据:项目侧 usercmd 宽度表 / MotionSnapshot 写侧(`DIRECT_ARTIFACT`),
  且 046 判定其**不能**反推官方线格式(`CONTRADICTED` / `N-3`)。
- 047 可复用:`Movement\MovementModel`、`Protocol\MixedBitReader`(仅内部)。
- 内部模型可先做:是。**最终实现:否。**

---

## 10. 结论

**只有模块 1(握手与连接状态)达到“可以开始最终 CODOL 兼容实现”的条件**,
且范围限定为**连接无关明文命令层**;其上的密文/压缩与其下的 in-match 层均未证。
其余七个模块一律保持 BLOCKED / 内部模型态。此判定由 047 的
`Analysis\ProtocolModuleReadiness` 在代码层固化,并有测试断言
「恰好一个模块 Ready」。
