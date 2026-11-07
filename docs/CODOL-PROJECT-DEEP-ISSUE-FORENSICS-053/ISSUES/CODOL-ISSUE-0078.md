# CODOL-ISSUE-0078 — 战斗握手只有模拟客户端 e2e_client.py 验证过

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

e2e_client.py 是独立实现，不是官方客户端。加密/NAT/DTLS 的端到端只对模拟客户端成立。

## 2. 历史首次发现过程

- **首次发现**：2026-10-22（`CODOL_SERVER_319_20261021/docs/STAGE1_CRYPTO_DONE.md §五`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P1　**登记状态**：`UNVERIFIED`　**严重度**：high
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-22 | STAGE1_CRYPTO_DONE 自述只对 e2e 验证 |  |
| 2026-10-26 | 8 轮官方客户端连上，战斗服日志完整（64 MB） | 但无 pcap |
| 2026-10-29 | E1 尝试抓包，pktmon 过滤 127.0.0.1:28960 → 0 包 | 抓包工具可用，只是没包 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0078-01 | source | `battle/battle.c` | — | NAT/DTLS/ECDH 实现 | — |
| EV-0078-02 | location | `run_codol_001/runs/ONCE_20261026_220815/kit/_battle_out.txt` | — | 8 轮之一的完整 RX | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle.c` | — | NAT/DTLS/ECDH 实现 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `run_codol_001/runs/ONCE_20261026_220815/kit/_battle_out.txt` | — | 8 轮之一的完整 RX |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0078，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `run_codol_001/runs/ONCE_20261026_220815/kit/_battle_out.txt`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
NAT → DTLS Init → ECDH → getchallenge → connect → stats
```

## 10. 第一条未闭合调用边

**官方客户端握手的字节级记录（可复现的 pcap）。**

## 11. 已确认事实

- 10-26 有 8 轮官方客户端全链路（日志）
- pktmon 在 10-29 能正常起停并产出 pcapng

## 12. 尚未确认的假设

- 8 轮成功的共同条件（见 ISSUE-0020）

## 13. 已排除的假设

- '握手没实现'——10-26 证明能通

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

battle.c 实现未变。

## 16. 最小复现条件

在能连上的配置下同时开 pktmon 抓 127.0.0.1:28960。

## 17. 最小验证实验

**实验 B78**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 复现一次成功连接（E1 型）<br>2. 同时 pktmon 抓包并 etl2pcap |
| 通过判据 | 得到非空 pcapng 且含握手序列 |
| 失败判据 | 0 包 ⇒ 未能连上 |
| 成本 | 1 轮 |

## 18. 条件式修复方案

**方案A：拿到 pcap 后逐字节对拍 battle.c。**

**方案B：维持现状（日志已足够指导实现）。**

## 19. 修改影响分析

决定传输层是否可声称'官方兼容'。

## 20. 可测量的验收标准

1. 官方客户端握手被完整抓包并逐字节复用。

## 21. 回归测试方案

每次成功 run 都保存 pcap。

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 CODOL-ISSUE-0020。
- **上游依赖**：`CODOL-ISSUE-0020`

---