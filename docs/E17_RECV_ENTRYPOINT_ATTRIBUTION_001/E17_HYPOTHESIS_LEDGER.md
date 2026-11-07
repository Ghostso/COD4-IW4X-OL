# E17 — 假设台账 / HYPOTHESIS LEDGER

> 格式：陈述 / 支持 / 反证 / 状态 / 下一步

---

### H-E17-01：0x6B4DE0 是 recvfrom 薄封装
- 支持：入口标准 prologue；调用 recvfrom@0x6B4E3C；参数 (sock,buf,len,flags,from,fromlen) 直接转（EV-17-01）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E17-02：0x784F60 是 recv 薄封装
- 支持：入口标准 prologue；调用 recv@0x784F7D（EV-17-02）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

### H-E17-03：两候选属 Demonware 传输/会话栈
- 支持：调用者簇与 demonware.net / DW-Client-Ticket / bdSessionParams@@ / DW-RSAENC 同镜像（EV-17-06/07）
- 反证：无源码或公开符号直接对应
- 状态：**STRONG_INFERENCE**
- 下一步：若有公开 Demonware 文档/符号，交叉验证

### H-E17-04：两候选是游戏会话入站路径
- 支持：（无）
- 反证：7 层闭包不含任何游戏解析候选（EV-17-08）；数据交 Demonware 对象（EV-17-05）
- 状态：**REFUTED（限定范围）**
- 下一步：无

### H-E17-05：两候选写入环形缓冲或消息队列
- 支持：（无）
- 反证：仅写 socket 统计/状态全局（EV-17-03/04）；无 0x3524F0/0x352570 引用
- 状态：**REFUTED**
- 下一步：无

### H-E17-06：0xD47370/0xD47374 是消息状态
- 支持：（曾疑为消息状态）
- 反证：消费者 0x6B4920 是错误/状态查询函数；写入的是 WSA 错误码与状态码 2（EV-17-04）
- 状态：**REFUTED**
- 下一步：无

### H-E17-07：游戏协议入站路径仍存在（未定位）
- 支持：E-12..E-16 已排除多条非游戏路径
- 反证：本轮又排除 2 个候选
- 状态：**BLOCKED**
- 下一步：审计 0x775A50/0x775AB0 虚表实例化路径

## 保留（未被本轮推翻）

| 假设 | 状态 |
|---|---|
| E-15：TLS 栈属 HTTP 更新模块 | 保留（CONFIRMED） |
| E-16：0x1B0430 属 ICMP ping | 保留（CONFIRMED） |
| E-16：0x78772D 是时间戳工具 | 保留（CONFIRMED） |
| E-13：0x3524F0 是环形缓冲写侧 | 保留（但属发送暂存） |
