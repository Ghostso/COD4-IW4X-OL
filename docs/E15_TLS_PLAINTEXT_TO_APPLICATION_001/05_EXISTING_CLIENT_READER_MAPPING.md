# 05 — 与既有客户端解析证据对照 / READER MAPPING

> 严格按任务要求：仅在明文进入应用层后才对照。本轮前提已 REFUTED，因此本节为归属复核而非链路映射。
> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 候选函数实时路径归属复核

| 函数 | E-10..E-14 归属 | E-15 复核 | 裁定 |
|---|---|---|---|
| MSG_ReadBits 0x1AC670 | 通用位读取原语 | 维持（不属任何特定路径） | PROVEN（原语） |
| MSG_ReadData 0x1AC1D0 | 通用字节读取原语 | 维持 | PROVEN（原语） |
| 0xA2660 | Configstring body reader；实时归属 BLOCKED | 在 0x605220 闭包内不出现 | 实时归属 BLOCKED（不变） |
| 0x354100 | 子帧分派器（demo 链） | 维持 demo 归属 | REFUTED（实时） |
| 0x3547D0 | 子帧循环（demo 链） | 维持 demo 归属 | REFUTED（实时） |
| 0x350170 | demo 顶层分派器 | 维持 | REFUTED（实时） |
| 0x34FD80 | 长度前缀消费者（demo 链） | 维持 | REFUTED（实时） |
| 0xA2E50 | reliable payload 候选 | 调用者 0、数据指针 0 | BLOCKED |

## 2. 与 TLS 链的关系（关键）

| 检查 | 结果 |
|---|---|
| 0xA2660 是否在 0x605220 六层闭包内 | 否 |
| 0x3547D0 是否在闭包内 | 否 |
| 0x350170 是否在闭包内 | 否 |
| 0x34FD80 是否在闭包内 | 否 |
| 0xA2E50 是否在闭包内 | 否 |

裁定（PROVEN 负）：TLS/libcurl 链与所有已知游戏解析器不相交。

## 3. 各层级的独立登记（禁止混淆）

| 层 | 本轮定位 | 裁定 |
|---|---|---|
| 网络外层分帧 | HTTP/1.x（libcurl） | PROVEN（属更新模块） |
| 游戏消息外层分帧 | 未定位 | BLOCKED |
| Gamestate 0x03 | 未定位（demo 消费者字段不匹配） | BLOCKED |
| Configstring 子帧 | 0x354100 case 6（demo 链） | REFUTED（实时） |
| Configstring body | 0xA2660（字段级 PROVEN） | 实时归属 BLOCKED |

## 4. 共享工具函数纪律

按任务要求：0xA2660 与 TLS 链即使共享 MSG_ReadBits / MSG_ReadData，也不构成同一调用链。

本轮实测：二者连共享工具函数都不成立——0x605220 闭包内无 0xA2660，亦无 MSG_ReadBits / MSG_ReadData 的直接调用。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| TLS 链到 0xA2660 | REFUTED |
| TLS 链到 demo 分派器 | REFUTED |
| 0xA2660 实时归属 | BLOCKED（未变） |
| 既有候选中可保留的实时候选 | 0x1B0430、0x78772D（BLOCKED） |