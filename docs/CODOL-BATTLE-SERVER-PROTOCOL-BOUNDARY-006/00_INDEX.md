# CODOL-BATTLE-SERVER-PROTOCOL-BOUNDARY-006

**任务性质：** 3.9.9.7 客户端初始化与 snapshot 的只读证据闭合。  
**日期：** 2026-10-13（Asia/Shanghai）  
**正式工程：** `D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1`  
**源码基线：** FREEZE-005，25 个 C# 文件，指纹 `5655b7b97350ae613c9508336983b4e318b49a435064436b12f05d38e0a9fddf`。  
**代码修改：** 无。

## 1. 首要结论

1. FREEZE-005 与当前正式源码完全一致；PROTOCOL-002 的源码哈希已包含，GAMEPLAY-003 的精确哈希未原样保留，但 captured 运动学、`vertical_sim` 和第 12 节测试语义仍存在。
2. **没有找到可归属于 CODOL 3.9.9.7 的客户端样本、抓包、运行时 dump 或函数级分析结果。** 本机登记客户端只有 1.1.1.13、3.3.3.3 和 2.6.9.7。
3. 3.3.3.3 有真实大厅/战斗抓包和参考握手链，但只能作为版本隔离的辅助证据。
4. 2.6.9.7 / C-2697-Rec 有较深的静态 Demonware 会话链；S-2697 服务端是 iD-Tech 对局面，二者没有闭合。
5. snapshot 客户端消费链未建立。S-2697 的服务端 writer 链可证，但客户端 delta decoder、帧边界、baseline、实体计数和增删规则均 BLOCKED。
6. 当前**不具备**实施 3.9.9.7 最小协议修改的证据条件。

## 2. 交付文件

| 文件 | 内容 |
|---|---|
| `CLIENT_INIT_EVIDENCE.md` | 客户端发现、连接、握手、gamestate/configstring 消费与玩家激活证据 |
| `SNAPSHOT_EVIDENCE.md` | snapshot 服务端写入链、客户端候选、字段和 delta 边界 |
| `EVIDENCE_MATRIX.tsv` | 44 条证据记录；含版本、定位、等级、影响和下步证据 |
| `BLOCKERS.md` | 10 条阻塞、解除顺序与最小证据 |
| `VERSION_ISOLATION.md` | 3.9.9.7 / 3.3.3.3 / 2.6.9.7 的版本隔离规则 |
| `FREEZE005_BASELINE_AUDIT.md` | 002、003 与 FREEZE-005 的实际合并审计 |

## 3. 六项完成标准回答

### Q1. 3.9.9.7 初始化链中，最后一个已证实阶段是什么？

**没有已证实阶段。**  
当前没有 3.9.9.7 客户端身份、入口、抓包或运行时数据，不能把其他版本阶段填补成目标版本事实。

### Q2. 下一个未闭合阶段具体缺少什么证据？

首先缺 **3.9.9.7 样本身份**：SHA-256、版本资源/manifest、映像入口和模块信息。  
其次缺 **目标版本一条真实连接样本**：pcap/UDP 字节/socket trace，能够覆盖首个有效包、服务端响应和客户端下一包。

### Q3. snapshot 服务端构造和客户端消费能否建立对应关系？

- 3.9.9.7：不能，无目标样本。
- 3.3.3.3：只有 29 个索引顺序的交叉印证，原始 motion trace JSON 缺失，帧边界和 delta 未证。
- S-2697 ↔ C-2697-Rec：服务端 writer 链已定位，客户端候选 `0x6E060/0x6D340` 未连接，是 BLOCKED。

### Q4. 哪些字段已经证实，哪些仍未知？

已证实的只是版本特定的局部事实：

- C-2697-Rec 的 4B 长度前缀帧读取器 `0x6ABBC0`、状态机 `0x6ABE80`、类型码读取器 `0x6A9920`。
- C-2697-Rec Demonware 分派器 `0x6AC0C0`、阶段字段 `[+0x5CC]`、0x81/0x83/0x84/0x85 控制流和 0x85 HMAC/counter 分支。
- S-2697 `_CODOL2697_WriteSnapshot 0xA4FA0 → 0xA4860`、内部 `0x06` 和区域复制常量。
- C-3333 的真实 NAT/INIT/COOKIE/ECDH、challenge/connect/stats/heartbeat 抓包。
- 当前服务器的 legacy/2697 实现路径和源码行号。

未知项：

- 3.9.9.7 的所有线上字段宽度、位偏移、入口和状态转换。
- real-time gamestate `0x03` 消费者、configstring 外层 `0x04` 的显式分派、`0x06` 客户端终止。
- snapshot 帧边界、entity count、entity ID、状态编码、base snapshot、delta、add/remove、拒绝条件和首帧语义。
- 本地玩家创建/激活和大厅→战斗切换条件。

### Q5. 当前是否已具备安全实施最小协议修改的证据条件？

**不具备。**  
可以形成下一步调查方案，但不能修改正式 3.9.9.7 协议字段或 snapshot 边界。

### Q6. 下一项最小、可验证的技术工作是什么？

**第一优先级：确认 3.9.9.7 客户端身份并取得一条目标版本连接样本。**  
在该条件满足前，任何针对 2697/3.3.3.3 的进一步工作都只能标记为辅助研究，不能直接转化为目标实现。

## 4. 交付判定

本轮以“未修改代码的静态分析报告”完成，不宣称客户端互通，不宣称 snapshot 已闭合，也不宣称 3.9.9.7 已完成。