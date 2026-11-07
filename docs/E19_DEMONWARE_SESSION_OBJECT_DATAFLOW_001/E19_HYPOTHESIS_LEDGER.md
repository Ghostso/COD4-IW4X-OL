# E19 — 假设台账 / HYPOTHESIS LEDGER

---

### H-E19-01：0x6ABBC0 是 4 字节长度前缀帧读取器
- 支持：累计 [esi+0xA4]；满 4 后 0x6878A0 解析；长度写 [esi+0xAC]（EV-19-01/02）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E19-02：0x6ABE80 是 4 状态接收状态机
- 支持：jmp [ebx*4+0xAAC090]；状态字段 [esi+0x9C]（EV-19-03/04）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E19-03：0x6A9920 读 1 字节类型码并二值分派
- 支持：mov al,[edi]；cmp al,1 / cmp al,2；size 1/9（EV-19-05）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E19-04：该状态机承载 CODOL 游戏消息
- 支持：（无直接证据）
- 反证：类型码域为 {1,2} 二值，与游戏顶层 opcode 1..4 + 子帧 0..8 不同；4 层闭包不含任何游戏解析候选（EV-19-11）
- 状态：BLOCKED（未证，未完全否证）
- 下一步：解出类型码 1/2 的语义；展开 [esi+0xB0]/[esi+0xB4] 对象类型

### H-E19-05：0x6ABBC0 对象是 Demonware 会话对象
- 支持：与 DW-Client-Ticket / bdSessionParams 同簇（E-17）；调用 0xB83B70（Demonware recv 封装）
- 反证：无类型名到函数的直接绑定
- 状态：STRONG_INFERENCE

### H-E19-06：0x788133 与 0x6ABBC0 同路径
- 支持：（无）
- 反证：无调用边/数据流；共享下游仅通用工具（EV-19-12）
- 状态：REFUTED（限定范围）

### H-E19-07：0x788133 属 0x78772D（E-16 标注）
- 支持：（prologue 启发式）
- 反证：真实 prologue 在 0x787B2F 附近（EV-19-10）
- 状态：REFUTED

### H-E19-08：该会话对象与游戏解析候选连接
- 支持：（无）
- 反证：4 层闭包不含任何已知候选（EV-19-11）
- 状态：REFUTED（限定范围）

## 保留（未被本轮推翻）

| 假设 | 状态 |
|---|---|
| E-18 libcurl vtable 不承载游戏协议 | 保留 |
| E-16 0x1B0430 属 ICMP ping | 保留 |
| E-15 TLS 栈属 HTTP 更新 | 保留 |
| E-13 0x3524F0 是发送暂存 | 保留 |
