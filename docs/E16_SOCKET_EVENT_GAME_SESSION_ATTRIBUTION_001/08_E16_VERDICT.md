# 08 — E-16 总裁定 / VERDICT

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
