# E21 证据登记

| 证据 ID | 类型 | 地址/RVA | 内容 | 等级 |
|---|---|---|---|---|
| EV-E21-01 | 构造器 | RVA 0x6A84E0 | 对象构造，写 vtable VA 0xC5B0A4，初始化 +0x04..+0x28 | PROVEN |
| EV-E21-02 | vtable | RVA 0x85B0A4 | 槽位 0xAA8570/0xAA85A0/0xAA83C0/0xAA82E0/0xAA88C0/0xAA8720 | PROVEN |
| EV-E21-03 | 字符串引用 | RVA 0x6AAE70 | 直接引用 HMAC calculation、HMAC mismatch、Bad recv counter、Bad frame/payload size | PROVEN |
| EV-E21-04 | 连接状态 | RVA 0x6AC0C0 | 读 [esi+0xC8]、[esi+0xAC]、[esi+0xB0]、[esi+0x5CC] | PROVEN |
| EV-E21-05 | 生产者 | RVA 0x6A84E0 34 个调用点 | 广泛复用的载荷对象构造器 | PROVEN |
| EV-E21-06 | 间接边界 | RVA 0x6AAC80、0xAAB1C0 | .tvm0/VM 混淆区域，线性反汇编不可靠 | BLOCKED |
| EV-E21-07 | 游戏候选 | 5 层闭包 | 未发现 0xA2660/0xA2E50/0x350170/0x3547D0/0x354100/0x3524F0/0x352570 | 限定 REFUTED |
| EV-E21-08 | 基线哈希 | 三样本 | 与冻结值一致 | PROVEN |
