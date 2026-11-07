# E18 — 游戏会话归属 / GAME SESSION ATTRIBUTION

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 阶段 E 的四个命题（分别给出证据与等级）

| # | 命题 | 证据 | 等级 |
|---|---|---|---|
| 1 | 函数属 libcurl 相关模块 | vtable 后紧跟 i386-pc-win32 / 7.38.0 / smtps / OCSP_* / BIO_ZLIB_* | PROVEN |
| 2 | 函数参与 libcurl 传输 | 0x775A50/0x775AB0 直接 recv/recvfrom；this+0x14=sock、this+0x04=addr | PROVEN（职责） |
| 3 | 函数承载游戏会话消息 | 未见游戏 opcode/长度/序列号解析 | REFUTED（限定范围） |
| 4 | 函数处理游戏应用层协议 | 6 层闭包不含任何游戏解析候选 | REFUTED（限定范围） |

纪律：命题 1 与 2 成立，不推出 3 或 4。本轮 3、4 取否定值是基于限定范围内未发现。

## 2. libcurl 簇闭包审计（PROVEN 负）

| 根 | 闭包(6) 大小 | 含游戏解析候选 |
|---|---|---|
| 0x775A50 | 0 | 否 |
| 0x775AB0 | 0 | 否 |
| 0x776130 | 1 | 否 |
| 0x776170 | 0 | 否 |

（候选集合：0xA2660、0x3547D0、0x354100、0x350170、0x34FD80、0xA2E50）

## 3. Demonware 侧（E-17 结论，维持）

| 命题 | 等级 |
|---|---|
| 属 Demonware 相关模块 | STRONG_INFERENCE（E-17） |
| 参与 Demonware 后端通信 | INFERRED |
| 承载游戏会话消息 | BLOCKED |
| 处理游戏应用层协议 | BLOCKED |

## 4. 0xA84CE0 的归属

裁定（PROVEN）：定长 0x84 字节结构体赋值函数（rep movsd + 写 word 字段）。属通用内存操作，不是消息消费者。

## 5. 是否找到第一个游戏应用层消费者

否（BLOCKED）。三阶段严格区分：

| 阶段 | 状态 |
|---|---|
| 找到网络对象 | 是（libcurl 传输对象族，5 个 vtable） |
| 找到数据交接 | 是（0x783F00 复制 0x84 字节，到 0xA84CE0） |
| 找到游戏协议消费者 | 否（BLOCKED） |

## 6. 与 7 个已知候选的连接

| 候选 | libcurl 簇 | Demonware 簇 | 裁定 |
|---|---|---|---|
| 0xA2660 | 否 | 否 | 未连接 |
| 0xA2E50 | 否 | 否 | 未连接 |
| 0x350170 | 否 | 否 | 未连接 |
| 0x3547D0 | 否 | 否 | 未连接 |
| 0x354100 | 否 | 否 | 未连接 |
| 0x3524F0 | 否 | 否 | 未连接 |
| 0x352570 | 否 | 否 | 未连接 |

## 7. 裁定

| 项 | 裁定 |
|---|---|
| 两槽位属 libcurl | PROVEN |
| 是游戏消息消费者 | REFUTED（限定范围） |
| Demonware 承载游戏会话 | BLOCKED |
| 首个游戏应用层消费者 | BLOCKED |
| 与已有候选连接 | REFUTED（限定范围） |
