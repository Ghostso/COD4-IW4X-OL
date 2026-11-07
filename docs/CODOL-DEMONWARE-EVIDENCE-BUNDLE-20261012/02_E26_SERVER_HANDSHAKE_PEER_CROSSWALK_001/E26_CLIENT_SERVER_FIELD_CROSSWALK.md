# E26 客户端—服务端字段交叉表

## 1. 参考路径（E-25 实际交付，不新增假设）

```text
0x6AB310 (阶段1应答状态机)
  → 0xDAB40 (序列化器，vtable 0xCBBD24；缓冲 [ebx+0xC]、写游标 [ebx+0x10])
  → 0x6AA230 (克隆 0x1C 节点 + 头插 [edi+0xB8])
  → 0x6AA7B0 (会话泵)
  → 0x783B50 (send 包装: send(fd,buf,len))
  → 0x784E40
  → ws2_32!send
```

## 2. 逐项比较（任务书 §C 六问）

| # | 问题 | 服务端证据 | 判定 |
|---|---|---|---|
| C1 | 服务端是否有证据接收此类客户端数据？ | 有接收入口（`recvfrom`→`_SV_ReadPackets`→`_SV_PacketEvent`），但**无** `CLIENTCHAL`/`BDDATA` 标签、**无** Demonware 模块、**无** 8 位 `0x81..0x85` 分支 | **证据不足/不同族** |
| C2 | 服务端从何层级读消息边界与码？ | 帧：`_SV_Netchan_Decode`（`0x855C0`，XOR + `CODOL2697_PROFILE_WIRE`）；消息码：`_MSG_ReadBits(msg,3)`（`0x472E7D`） | **完全不同的分层** |
| C3 | 服务端如何处理字段长度/字符串/二进制？ | `_MSG_ReadByte/Short/Long/Data/String`（`0x2BC61..0x2BEAA`）；`_CODOL_ReadByte/Short/Long`（`0x99394/0x993A6/0x993B8`） | 机制存在，但与 Demonware 序列化器无对应 |
| C4 | 状态条件能否解释客户端阶段转换？ | 服务端状态是 `[obj+0x25C]`/`[+0x64]`/`[+0x68]`/`[+0x10..13]==7F000001`；**无 `[+0x5CC]` 同构** | **无对应** |
| C5 | 服务端响应能否对应客户端 `0x83/0x84/0x85` 分派？ | 服务端下行 `0x01..0x06`；与客户端 `0x83/0x84/0x85` 不同方向、不同编码 | **无对应** |
| C6 | 是否存在字段序/长度/编码/状态冲突？ | 见 E26 冲突报告：首个冲突 = 客户端消息 opcode 位数（8 vs 3） | **明确冲突** |

## 3. 共享点（唯一可交叉验证）

| 项 | 客户端 | 服务端 | 判定 |
|---|---|---|---|
| `challengeResponse` 字符串 | VA `0xCB7AE4`（ref `0x9BFB9`）、`0xCC5EF0`（ref `0x1EC4FE`） | VA `0x7BCCCA`（ref `0x975A4`） | **PROVEN 共享** |
| `7F 00 00 01` 签名 | 2 处 | 6 处（含 `_CODOL_NetworkSessionReady` `0x9A454..0x9A46A`） | **PROVEN 存在**；语义对应 INFERRED（强） |
| 长度常量 `0xBD`（189） | 未找到 | `_CODOL_HandshakeCookie` `0x98611` | 服务端特有 |
| 16 字节 `[1,2,0,0,0,0,≠0,cookie8]` | 未找到 | `_CODOL_HandshakeInit` `0x9830D..0x98377` | 服务端特有 |
| `CLIENTCHAL`/`BDDATA` | 各 1 处 | **0 处** | **客户端特有** |
| HMAC/recv counter | `HMAC mismatch`/`Bad recv counter` | **0 处**（HMAC 仅 mbedTLS 库） | **客户端特有** |

## 4. 结论

- **完全匹配**：`challengeResponse` 字符串、`7F 00 00 01` 签名（iD-Tech 握手族）。
- **部分匹配**：两侧都有可靠命令/快照/配置字符串通道，但编码与 opcode 空间不同（本目录 04/E3 已记录）。
- **明确冲突**：客户端 Demonware 会话握手（`CLIENTCHAL`/`BDDATA`/HMAC/recv counter/`[+0x5CC]` 阶段）在服务端**不存在对应实现**。
- **证据不足**：客户端 `0x81..0x85` 与E-25 那条发送链的服务端消费方，未在本样本中找到（**不等于全局不存在**）。

## 5. 替代解释（必须保留）

1. 客户端 Demonware 会话握手的对端是**独立的 Demonware 大厅/会话服务**（非 `codol_dedrun.exe`），而 2697 专用服务端只承担 iD-Tech 对局流量。
2. 也可能经 `client_room2697.dll`/`client_native_loopback.dll` 桥接后再转发——但这两个 DLL 亦无该族标签（已扫描）。
3. 本轮**不能**断言"协议不兼容"；只能断言"2697 专用服务端样本中未找到该握手族的消费路径"。
