# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001"
F={}
F["09_EVIDENCE_REGISTER_ADDENDUM.md"]="""# 09 — 证据登记（E-16 追加）

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/_EVIDENCE_REGISTER.md 及 E-10..E-15 的同名追加。

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-16-01 | IAT | 0x1B0430..0x1B0F30 | 核心网络原语为 ICMP 四件套：IcmpCreateFile(0xBAE098)、IcmpSendEcho2(0xBAE09C)、IcmpParseReplies(0xBAE094)、IcmpCloseHandle(0xBAE090) | out_t02_iat | PROVEN |
| EV-16-02 | SEMANTICS | 0x1B0430 | 服务器延迟测量（ping）：getaddrinfo 解析 0x2CCA3C8 服务器表 -> socket -> IcmpSendEcho2 -> recvfrom/IcmpParseReplies -> RTT | out_1b0430_full.txt | PROVEN |
| EV-16-03 | BRANCH | 0x1B086D/0x1B0991/0x1B0A25/0x1B0ADF | 四者非并列事件类型，而是 ICMP ping 的四个顺序阶段 | out_t08_branches | PROVEN |
| EV-16-04 | INBOUND | 0x1B0BA1 | 唯一入站点：recvfrom，缓冲 [esp+0x50]（栈上） | out_1b0430_full.txt | PROVEN |
| EV-16-05 | RESULT | 0x1B097A | RTT 写入 [obj+ebx+0x934]；无应用层消费者 | out_1b0430_full.txt | PROVEN |
| EV-16-06 | REFUTE | 0x1B0430 | 无分帧/队列/应用层分派（限定范围） | 03 第4节 | REFUTED |
| EV-16-07 | SEMANTICS | 0x78772D | 64 位时间戳换算（GetSystemTimeAsFileTime 0xBAE1C0 + 除法 0xB50980） | out_78772d.txt | PROVEN |
| EV-16-08 | REFUTE | 0x78772D | 无调用者、无数据指针引用、无 .tvm0 调用；与 0x1B0430 无调用/数据流边 | out_t06_verify | REFUTED |
| EV-16-09 | SECTION | 0xDBEF28A | 属 .data(BSS) 段（0x8F1000..0xD945420），非 .tvm0（0xD958000..）；E-13 的 tvm0 定性为 .rimp 修复伪影 | 04 第5节 | REFUTED（tvm0） |
| EV-16-10 | HASH | 三样本 | 冻结基线开工/收工各复核一次，均一致 | Get-FileHash | PROVEN |
"""
F["10_HYPOTHESIS_LEDGER_ADDENDUM.md"]="""# 10 — 假设台账（E-16 追加）

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
"""
F["11_CLAIM_EVIDENCE_DEPENDENCY_GRAPH_ADDENDUM.md"]="""# 11 — 结论—证据依赖图（E-16 追加）

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/21_CLAIM_EVIDENCE_GRAPH.md 及 E-10..E-15 的同名追加。

    C-16-01  0x1B0430 是 ICMP ping / 服务器延迟测量
       满足 EV-16-01（Icmp* 四件套）
       满足 EV-16-02（getaddrinfo + socket + SendEcho2 + recvfrom 闭环）
       满足 EV-16-05（RTT 写 [obj+ebx+0x934]）

    C-16-02  四分支是 ICMP 四阶段（非并列事件）
       满足 EV-16-03

    C-16-03  0x1B0430 无游戏消息分帧/队列/分派
       满足 EV-16-04（唯一入站点 + 栈缓冲）
       满足 EV-16-06（无长度/类型/队列）

    C-16-04  0x78772D 是时间戳换算函数
       满足 EV-16-07（GetSystemTimeAsFileTime + 除法）

    C-16-05  0x78772D 与 0x1B0430 无关系
       满足 EV-16-08（无调用边/数据流边）

    C-16-06  E-13 的 .tvm0 定性为误判
       满足 EV-16-09（段表比对）

    C-16-07  实时消息分派器
       未满足（缺口）BLK-16-1/3/4
       裁定：BLOCKED

## 依赖缺口汇总

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| C-16-07 | 剩余收包函数归属（BLK-16-3） | 实时消息分派器 BLOCKED |
| C-16-04 | 无（0x78772D 已闭合） | — |
"""
F["12_START_GATING_AND_QUESTION_REGISTER_ADDENDUM.md"]="""# 12 — 开工准入与统一问题库增补（E-16 追加）

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/22_SERVER_START_GATING_AUDIT.md 及 E-09..E-15 的对应审计与 E-15 的 12_UNIFIED_QUESTION_REGISTER。

## 1. 开工准入判据变化（相对 E-15）

| # | 判据 | E-15 | E-16 | 依据 |
|---|---|---|---|---|
| G-30 | TLS 链归属 | 通过 | 通过 | 维持 |
| G-31 | TLS 明文流存在性 | 通过（否定） | 通过（否定） | 维持 |
| G-32 | 实时 0x03 消费者 | 未通过 | 未通过 | 仍未定位 |
| G-33（新） | 0x1B0430 归属 | — | 通过 | ICMP ping（EV-16-01/02） |
| G-34（新） | 0x78772D 归属 | — | 通过 | 时间戳工具（EV-16-07） |
| G-35（新） | E-13 的 .tvm0 定性 | — | 通过（更正） | .data/BSS（EV-16-09） |

E-15：通过 23 / 部分 4 / 未通过 3 -> E-16：通过 26 / 部分 4 / 未通过 3。

## 2. 统一问题库增补（Q-17..Q-19）

依 E-15 的权重标度（I4=8 / I3=5 / I2=3 / I1=1；PROVEN=1.0，BLOCKED=0.0）：

| Q ID | 协议层 | 问题 | 影响 | 权重 | 当前等级 | 解决度 | 成本 | 阻塞开工 |
|---|---|---|---|---|---|---|---|---|
| Q-17 | 传输 | 0x1B0430 归属（ICMP ping） | I2 | 3 | PROVEN | 1.0 | C1 | 否 |
| Q-18 | 工程 | 0x78772D 归属（时间戳工具） | I1 | 1 | PROVEN | 1.0 | C1 | 否 |
| Q-19 | 消息 | 剩余 recv/recvfrom 调用点归属（0x6B4DE0、0x784F60 等） | I4 | 8 | BLOCKED | 0.0 | C2 | 是 |

## 3. 风险加权解决率重算

- 旧总权重 = 91（E-15）
- 新增权重 = 3 + 1 + 8 = 12
- 新总权重 = 103
- 新增加权得分 = 3x1.0 + 1x1.0 + 8x0.0 = 4
- 新加权得分 = 32 + 4 = 36
- 风险加权解决率 = 36 / 103 = 34.95%（约 34.9%）

## 4. 解读

| 观察 | 说明 |
|---|---|
| 解决率从 35.2% 微降至 34.9% | 因新增 1 项高权重 BLOCKED（Q-19，权重 8） |
| 净效果 | 两项候选被彻底排除（0x1B0430、0x78772D），但游戏入站路径仍未定位 |
| I4 层 | 新增 Q-19（权重 8）后，I4 层解决度进一步下降 |

注意（纪律）：不得只报 34.9% 而省略分母 103 与口径说明。

## 5. 与 E-13/E-14/E-15 结论的关系

| 来源 | 关系 |
|---|---|
| E-13 | 本轮 REFUTED 其 2 条剩余候选（0x1B0430、0x78772D）及其 .tvm0 定性 |
| E-14 | 无冲突（TLS 归属维持） |
| E-15 | 无冲突；本轮为 E-15 VERDICT Q8 指出的下一轮任务的执行结果 |

## 6. 准入裁定

维持 CONDITIONAL GO（放宽不变）。服务器编码器可实现服务端自洽版本；客户端实时消费链仍 BLOCKED。下一步最小范围：Q-19（剩余 recv/recvfrom 调用点归属）。
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
