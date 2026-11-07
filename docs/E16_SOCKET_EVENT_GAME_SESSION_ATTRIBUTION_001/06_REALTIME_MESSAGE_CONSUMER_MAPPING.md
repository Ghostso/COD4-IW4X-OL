# 06 — 实时消息消费者映射 / REALTIME MESSAGE CONSUMER MAPPING

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED
> 前置：仅在本轮已证入站数据流之后才能映射。本轮已证入站数据为 ICMP 回复（非游戏数据），故本节为归属复核。

---

## 1. 本轮入站数据流的终点（PROVEN）

    0x1B0430 (ICMP ping)
      recvfrom 0x1B0BA1 -> [esp+0x50]
        IcmpParseReplies 0xBAE094
          RTT -> [obj+ebx+0x934]
            [end - 无应用层调用]

终点是 RTT 数值，不是消息缓冲。无下游消息消费者。

## 2. 与既有解析候选的关系

| 候选 | 是否在本轮入站链内 | 裁定 |
|---|---|---|
| MSG_ReadBits 0x1AC670 | 否 | 无关 |
| MSG_ReadData 0x1AC1D0 | 否 | 无关 |
| 0xA2660 | 否 | 实时归属 BLOCKED（未变） |
| 0x350170 | 否 | demo（REFUTED 实时） |
| 0x3547D0 | 否 | demo（REFUTED 实时） |
| 0x354100 | 否 | demo（REFUTED 实时） |
| 0x34FD80 | 否 | demo（REFUTED 实时） |

## 3. 层级独立登记（禁止混淆）

| 层 | 定位 | 裁定 |
|---|---|---|
| socket API | 全 IAT 锚点 | PROVEN |
| ICMP ping 栈 | 0x1B0430 | PROVEN（非游戏） |
| HTTP 栈 | 0x605220 链 | PROVEN（非游戏） |
| 游戏消息外层分帧 | 未定位 | BLOCKED |
| Gamestate 0x03 消费者 | 未定位 | BLOCKED |
| Configstring 子帧 | 0x354100 case 6（demo） | REFUTED（实时） |
| Configstring body | 0xA2660（字段级 PROVEN） | 实时归属 BLOCKED |

## 4. 是否可建立实时网络到消息分派器的调用链

否（BLOCKED）。现有三条已归属路径（ICMP、HTTP、错误日志）分别通向：延迟数值、更新文件、日志——均非游戏消息分派器。

## 5. 是否找到实时 Gamestate 0x03 消费者

否（BLOCKED）。维持 E-12..E-15 结论。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 本轮入站数据终点 | PROVEN（RTT 数值） |
| 是否有下游消息消费者 | REFUTED（无） |
| 实时消息分派器 | BLOCKED |
| 实时 Gamestate 0x03 | BLOCKED |
| 0xA2660 实时归属 | BLOCKED（未变） |
