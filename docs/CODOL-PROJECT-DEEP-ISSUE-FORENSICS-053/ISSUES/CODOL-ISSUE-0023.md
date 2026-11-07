# CODOL-ISSUE-0023 — TX 快照缓冲仅 512 B，零售快照 7000–15000 B，且无下行分片

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

battle_service.c:425 `uint8_t snap[512], payload[520];`；零售首帧实测 14962 B（2020 语料）。实体段上限 8 条（约 10 个实体）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-25（`HANDOFF_20261025_BINARY_BISECT.md §16.4`）
- **最近验证**：2026-10-29 (source re-read)
- **所属系统**：`battle-network`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-25 | §16.4 记录 512 B 与零售 7000-15000 B 的差距 | 未处理 |
| 2026-10-29 | 源码复核：snap[512] / payload[520] 仍在 | 未变 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0023-01 | source | `battle/battle_service.c` | 421-591 | send_snapshot，含 snap[512] | — |
| EV-0023-02 | location | `battle/battle_service.c` | 425 | uint8_t snap[512], payload[520]; | — |
| EV-0023-03 | location | `include/codol_types.h` | — | CODOL_MAX_PACKET_SIZE 1400（帧上限） | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 421-591 | send_snapshot，含 snap[512] |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 425 | uint8_t snap[512], payload[520]; |
| `include/codol_types.h` | — | CODOL_MAX_PACKET_SIZE 1400（帧上限） |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0023，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
world entities → ents[8] → codol_snapshot_build(snap,512) → payload[520] → send_frame(frame[2048])
```

## 10. 第一条未闭合调用边

**没有下行分片协议；零售 14962 B 首帧如何分片未知。**

## 11. 已确认事实

- snap 512 B / payload 520 B / frame 2048 B 三个上限都在源码里
- 实体段显式限制 ent_count<8

## 12. 尚未确认的假设

- 客户端是否接受多帧拼装的快照；分片序号如何编号

## 13. 已排除的假设

- '扩大缓冲就能发全部 334 实体'——还要解决帧 2048 B 与 UDP MTU

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

硬编码 512/520/2048 三处上限，未改动。

## 16. 最小复现条件

打开 snapshot_entities.on，看 ents 是否恒 ≤8、bytes 是否逼近 512。

## 17. 最小验证实验

**实验 B23**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把 snap 扩到 16 KB、payload 到 16 KB，只发一帧极大快照<br>2. 观察客户端 messageAck 是否仍递增、是否断连 |
| 通过判据 | 单帧 4 KB 能被 ack |
| 失败判据 | 超过 MTU 需要分片 |
| 成本 | 1 轮实机 |

## 18. 条件式修复方案

**方案A（条件式）：若 B23 证明单帧可到 4 KB → 先扩缓冲到 4 KB，实体上限提到 ~60。**

**方案B：实现服务端→客户端分片（需要先解出客户端的重组规则）。**

## 19. 修改影响分析

决定实体规模上限；影响多人同步与地图实体下发。

## 20. 可测量的验收标准

1. 可下发 >4 KB 的快照且客户端 ack 不断。

## 21. 回归测试方案

test_snapshot_delta 增加大缓冲用例。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B23：扩缓冲单变量实验。
- **上游依赖**：无

---