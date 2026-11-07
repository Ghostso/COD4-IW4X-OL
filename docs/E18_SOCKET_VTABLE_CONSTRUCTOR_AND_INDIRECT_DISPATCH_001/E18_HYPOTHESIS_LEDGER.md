# E18 — 假设台账 / HYPOTHESIS LEDGER

---

### H-E18-01：0x898588/0x898590 是 libcurl 传输对象的 vtable 槽位
- 支持：表 0x898568..0x898634（52 槽）；表后紧跟 i386-pc-win32 / 7.38.0 / smtps / OCSP_* / BIO_ZLIB_*（EV-18-01/02/03）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E18-02：0x775A50 / 0x775AB0 是 socket 对象的接口方法
- 支持：thiscall，读 this[0x14]=sock；直接 call recv/recvfrom；不解析载荷（EV-18-08/09）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E18-03：虚表构造者已定位
- 支持：0x776139/0x776188 写 vptr=0xC98568；分配器 0x776170（EV-18-04/05/06）
- 反证：0x776170 无直接调用者（注册路径未定）
- 状态：CONFIRMED_BY_EVIDENCE（构造）/ BLOCKED（注册）

### H-E18-04：两候选属游戏会话路径
- 支持：（无）
- 反证：libcurl 4 根 6 层闭包不含任何游戏解析候选（EV-18-11）
- 状态：REFUTED（限定范围）

### H-E18-05：0xA84CE0 是 Demonware 消息交付点
- 支持：（E-17 表述）
- 反证：实为定长 0x84 字节 rep movsd 结构体赋值 + 写 word 字段（EV-18-10/12）
- 状态：REFUTED

### H-E18-06：Demonware 栈承载游戏会话
- 支持：Demonware 是 COD 官方后端网络库
- 反证：7 层闭包不含游戏解析器（E-17 EV-17-08）
- 状态：BLOCKED（未证，未否证）

### H-E18-07：游戏协议入口仍在 socket 调用点内
- 支持：（E-12..E-17 曾假设）
- 反证：全部 9 个 recv/recvfrom 调用点已归属（E-17 + E-18）
- 状态：REFUTED（限定范围）

## 保留（未被本轮推翻）

| 假设 | 状态 |
|---|---|
| E-15 TLS 栈属 HTTP 更新 | 保留 |
| E-16 0x1B0430 属 ICMP ping | 保留 |
| E-16 0x78772D 是时间戳工具 | 保留 |
| E-17 0x6B4DE0/0x784F60 是 recv 封装 | 保留 |
| E-13 0x3524F0 是环形缓冲写侧 | 保留（发送暂存） |
