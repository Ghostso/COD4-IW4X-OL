# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001"
F={}
F["06_REALTIME_MESSAGE_CONSUMER_MAPPING.md"]="""# 06 — 实时消息消费者映射 / REALTIME MESSAGE CONSUMER MAPPING

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
"""

F["07_BLOCKER_REGISTER.md"]="""# 07 — 阻断登记 / BLOCKER REGISTER

---

## BLK-16-1：游戏会话入站路径

| 项 | 内容 |
|---|---|
| 缺口 | 未定位游戏协议入站数据路径 |
| 本轮排除 | 0x1B0430（ICMP ping）、0x605220 链（HTTP 更新）、0x6029A0（错误日志） |
| 替代解释 | 1) 走明文 UDP 虚表族但未找到消息特征；2) 位于 .tvm0；3) 由未解析间接分派 |
| 最小下一步 | 审计剩余 recv/recvfrom 调用点：0x6B4DE0、0x784F60、0x6D340 区段 |
| 范围 | E-13 的 9 收包函数中尚未归属者 |

## BLK-16-2：0x775A50 / 0x775AB0 虚表实例化

| 项 | 内容 |
|---|---|
| 缺口 | 虚表 .rdata 0x898588/0x898590 的构造者未定位 |
| 已排除 | 无直接 call；仅数据指针 |
| 替代解释 | socket 对象构造时填表 |
| 最小下一步 | 定位写入 0x898588 的构造函数 |
| 范围 | .rdata 0x898588 引用点 |

## BLK-16-3：0x6B4DE0 / 0x784F60 的归属

| 项 | 内容 |
|---|---|
| 缺口 | 这两个 recv/recvfrom 函数（E-13 清单）尚未做本轮级归属审计 |
| 已排除 | 本轮范围限定于 0x1B0430 与 0x78772D |
| 替代解释 | 可能是游戏协议栈 |
| 最小下一步 | 按 E-16 同法审计其 IAT 使用与原语 |
| 范围 | 0x6B4DE0 与 0x784F60 |

## BLK-16-4：实时消息分派器

| 项 | 内容 |
|---|---|
| 缺口 | 未定位应用层游戏消息分派器 |
| 已排除 | ICMP/HTTP/日志三条路径 |
| 替代解释 | 位于 .tvm0 或未解析间接分派 |
| 最小下一步 | 见 BLK-16-3 |
| 范围 | 剩余未归属收包函数 |

## 负搜索的限定表述

- 在 0x1B0430..0x1B0F30 内，未发现游戏协议的分帧、队列或应用层分派。
- 在 0x78772D 与 0x1B0430 之间，未发现调用边或数据流边。
- 不表述为"客户端不存在游戏协议分派"。
"""

F["08_E16_VERDICT.md"]="""# 08 — E-16 总裁定 / VERDICT

> 只读静态分析。冻结基线哈希本轮开工与收工各复核一次，均一致；原始样本未修改。

---

## 1. 八个最终问题

Q1. 四个事件分支分别承担什么职责？

| 分支 | 职责 | 裁定 |
|---|---|---|
| 0x1B086D | 计时基准（GetTickCount） | PROVEN |
| 0x1B0991 | 构造并发 ICMP echo（htons + IcmpSendEcho2） | PROVEN |
| 0x1B0A25 | ping 阶段判定 | PROVEN |
| 0x1B0ADF | select + recvfrom + IcmpParseReplies | PROVEN |

四者不是并列 socket 事件类型，而是同一 ICMP ping 流程的四个顺序阶段。

Q2. 是否找到真实游戏会话的入站数据路径？

否（REFUTED，限定范围）。0x1B0430 的入站数据是 ICMP echo 回复；本函数不含游戏消息特征。

Q3. 入站数据的第一个可证实应用层消费者是什么？

无（REFUTED）。数据交 IcmpParseReplies 后转为 RTT 数值写入 [obj+ebx+0x934]，无应用层消费者。

Q4. 0x78772D 是否属于该路径？

否（REFUTED）。0x78772D 是时间戳换算函数（GetSystemTimeAsFileTime），与 0x1B0430 无调用边或数据流边。

Q5. 是否能建立实时网络数据到消息分派器的调用链？

否（BLOCKED）。三条已归属路径（ICMP/HTTP/日志）均不通向游戏消息分派器。

Q6. 是否找到实时 Gamestate 0x03 消费者？

否（BLOCKED）。维持 E-12..E-15。

Q7. 若仍未闭合，最小阻塞点是什么？

游戏协议入站路径的归属。本轮已排除 0x1B0430（ICMP）与 0x78772D（时间戳）。剩余未归属的 recv/recvfrom 调用点为 0x6B4DE0、0x784F60 等。

Q8. 风险加权解决率是否变化？

是。Q-15（网络虚表构造者）维持 BLOCKED；新增证据不改变 Q-01..Q-08 的 BLOCKED 状态。但本轮**新增两项否定性结论**，使 E-13 遗留候选从 2 条降为 0 条已证实的游戏候选：

| 问题 ID | 权重 | 旧解决度 | 新解决度 | 说明 |
|---|---|---|---|---|
| Q-01（游戏协议传输栈） | 8 | 0.0 | 0.0 | 仍 BLOCKED，但候选集合已排除 2 条 |
| Q-15（虚表构造者） | 3 | 0.0 | 0.0 | 未变 |
| Q-16（0x67F5F0 边界） | 1 | 0.0 | 0.0 | 未变 |

加权得分仍为 32 / 91 = 35.2%（无 PROVEN 项新增）。

## 2. 对 E-13/E-14/E-15 的修订

| 旧结论 | 本轮修订 | 依据 |
|---|---|---|
| E-13：0x1B0430 是通用 socket 事件管理 | ICMP ping / 服务器延迟测量 | IAT 全量统计（Icmp* 四件套） |
| E-13：0x78772D 含 .tvm0 调用 | 时间戳换算；.tvm0 定性 REFUTED（实为 .data/BSS 与 .rimp 伪影） | 段表比对 + 调用形态 |
| E-13：四个事件分支 | 更正为 ICMP 四阶段 | 逐分支反汇编 |
| E-14/E-15：TLS 属更新模块 | 维持 | 与本轮无冲突 |

## 3. 完成标准逐条

| # | 标准 | 裁定 |
|---|---|---|
| 1 | 四分支职责 | PROVEN |
| 2 | 是否找到游戏入站路径 | REFUTED（限定范围） |
| 3 | 第一应用层消费者 | REFUTED（无） |
| 4 | 0x78772D 归属 | PROVEN（时间戳工具） |
| 5 | 到消息分派器的链 | BLOCKED |
| 6 | 实时 0x03 消费者 | BLOCKED |

## 4. 交付物清单

| 文件 | 状态 |
|---|---|
| 01_SOCKET_EVENT_DISPATCH.md | 完成 |
| 02_FOUR_EVENT_BRANCH_AUDIT.md | 完成 |
| 03_INBOUND_SOCKET_DATAFLOW.md | 完成 |
| 04_78772D_FUNCTION_ATTRIBUTION.md | 完成 |
| 05_TRANSPORT_STACK_ATTRIBUTION.md | 完成 |
| 06_REALTIME_MESSAGE_CONSUMER_MAPPING.md | 完成 |
| 07_BLOCKER_REGISTER.md | 完成 |
| 08_E16_VERDICT.md | 完成 |
| SHA256SUMS.txt | 完成 |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
