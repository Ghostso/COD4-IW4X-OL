# 02 — 四分支逐项审计 / FOUR EVENT BRANCH AUDIT

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 分支 B1：0x1B086D（计时基准）

| 项 | 内容 |
|---|---|
| 触发条件 | [obj+0xB83C] != 0（主机解析已完成） |
| 比较值 | test dl,dl；je 0x5B0550 |
| 对象字段 | [0x7474EAC]+0xB83C |
| socket API | 无（GetTickCount 于 0x1B0881/0x1B0890） |
| 缓冲区 | 无 |
| 职责 | 周期性计时基准（ping 超时判定） |
| 方向 | 纯状态管理 |
| 裁定 | PROVEN（非数据路径） |

## 分支 B2：0x1B0991（构造 ICMP echo 请求）

| 项 | 内容 |
|---|---|
| 触发条件 | [obj+edi+0x655D] == 0（DNS 尚未成功） |
| 对象字段 | [obj+0xB838]（ICMP 句柄）、[obj+ebx+8]（端口）、[obj+ebx+0x10]（地址） |
| socket API | htons（0xBAE500）、IcmpSendEcho2（0xBAE09C @0x1B0957） |
| 传入缓冲 | [obj+ebx+0x410]，长度 0x51C（1308） |
| 超时 | 0x2328（9000 ms） |
| 返回值 | 若 != 0 且 != 0x3E5 → GetLastError；否则记录 GetTickCount() |
| 状态更新 | [obj+ebx+0x930] = 1（已发出） |
| 方向 | 出站（ICMP echo 请求） |
| 裁定 | PROVEN（出站 ping） |

## 分支 B3：0x1B0A25（检查 ping 阶段）

| 项 | 内容 |
|---|---|
| 触发条件 | [obj+ebx+0x930] != 0 且 [obj+ebx+0x931] == 0 |
| 对象字段 | [obj+ebx+0x930] / [+0x931] |
| socket API | 无 |
| 职责 | 已在 B2 发出、等待回复期间的轮询判定 |
| 方向 | 纯状态管理 |
| 裁定 | PROVEN（非数据路径） |

## 分支 B4：0x1B0ADF / 0x1B0B44（select + recvfrom 收 ICMP）

| 项 | 内容 |
|---|---|
| 触发条件 | [obj+edi+0x655C] != 0 且 [obj+edi+0x655D] == 0 |
| socket API | select（0xBAE4D8 @0x1B0B44）、__WSAFDIsSet（0xBAE4E0 @0x1B0B66） |
| 收包 | recvfrom（0xBAE50C @0x1B0BA1） |
| 收包缓冲 | [esp+0x50]（栈上临时缓冲） |
| 收到后 | IcmpParseReplies（0xBAE094 @0x1B0A72 附近） |
| 方向 | 入站，但属 ICMP echo 回复（非游戏数据） |
| 裁定 | PROVEN（ICMP 回复解析） |

## 汇总：四分支职责

| 分支 | 职责 | 方向 | 是否消费入站数据 |
|---|---|---|---|
| B1 0x1B086D | 计时基准 | 状态 | 否 |
| B2 0x1B0991 | 构造并发 ICMP echo | 出站 | 否 |
| B3 0x1B0A25 | ping 阶段判定 | 状态 | 否 |
| B4 0x1B0ADF | select + recvfrom + IcmpParseReplies | 入站（ICMP） | 是，但为 ICMP 回复 |

## 裁定

| 项 | 裁定 |
|---|---|
| 是否存在接收行为 | PROVEN（B4） |
| 接收内容性质 | PROVEN（ICMP echo 回复，非游戏消息） |
| 接收缓冲位置 | PROVEN（栈上 [esp+0x50]） |
| 是否有分帧/队列/应用层分派 | REFUTED（无：直接交 IcmpParseReplies） |
| 是否游戏会话入站 | REFUTED |