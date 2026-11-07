# 10 — 假设台账（E-16 追加）

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/17_HYPOTHESIS_LEDGER.md 及 E-10..E-15 的同名追加。

### H-E16-01：0x1B0430 是通用 socket 事件管理（E-13 假设）
- 类别：传输层（被否定）
- 支持：（E-13 曾据 30+ socket API 调用推断）
- 反证：全部网络原语为 ICMP 四件套 + getaddrinfo（EV-16-01/02）
- 状态：REFUTED
- 可证伪：找到该函数内的游戏消息特征
- 下一步：无

### H-E16-02：0x1B0430 是服务器延迟测量（ping）
- 类别：传输层
- 支持：IcmpCreateFile/SendEcho2/ParseReplies 闭环 + RTT 写 [obj+ebx+0x934]（EV-16-01/02/05）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE
- 下一步：无

### H-E16-03：四个"事件分支"是并列的 socket 事件类型
- 类别：结构（被否定）
- 支持：（E-13 用词）
- 反证：四者是 ICMP ping 的四个顺序阶段（EV-16-03）
- 状态：REFUTED
- 下一步：无

### H-E16-04：0x1B0430 内存在游戏消息分帧/队列/应用层分派
- 类别：应用层（被否定）
- 支持：（无）
- 反证：无长度字段、无队列、无类型分派；数据交 IcmpParseReplies 后转 RTT（EV-16-04/05/06）
- 状态：REFUTED
- 下一步：无

### H-E16-05：0x78772D 是游戏协议相关函数
- 类别：职责（被否定）
- 支持：（E-13 列为候选）
- 反证：GetSystemTimeAsFileTime + 除法，纯时间戳换算（EV-16-07）；无调用者（EV-16-08）
- 状态：REFUTED
- 下一步：无

### H-E16-06：0x78772D 调用 .tvm0
- 类别：混淆边界（被否定）
- 支持：（E-13 记录 0x787982 call 0xDBEF28A 落入 .tvm0）
- 反证：0xDBEF28A 属 .data(BSS)，非 .tvm0；形态为 memchr 类查找（EV-16-09）
- 状态：REFUTED
- 下一步：无

### H-E16-07：E-13 的实时候选路径仍然存在
- 类别：实时链（收窄）
- 支持：（E-13 保留 2 条：0x1B0430、0x78772D）
- 反证：本轮两条均被 REFUTED（ICMP / 时间戳）
- 状态：2 条候选全部移除；剩余未归属 recv/recvfrom 调用点见 BLK-16-3
- 下一步：审计 0x6B4DE0、0x784F60
