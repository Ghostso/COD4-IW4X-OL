# CODOL-ISSUE-0065 — FAT 分片实机从未触发；RELIABLE 分片 ack 无实机证据

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

FAT 重组离线 7 项全绿，但修好索引编码后客户端消息稳定在 174~371 字节，永远达不到 1154 阈值。RELIABLE 片段 ack(0xA0000000) 只有文档。

## 2. 历史首次发现过程

- **首次发现**：2026-10-24（`HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P2　**登记状态**：`UNVERIFIED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-24 | FAT_REASSEMBLY_PLAN 离线 7 项 |  |
| 2026-10-25 | §8.2 记录阻断点自行消失 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0065-01 | source | `netchan/netchan.c` | 94-186 | codol_fat_reset / codol_fat_receive | — |
| EV-0065-02 | location | `battle/battle_service.c` | 895-920 | FAT 分支 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `netchan/netchan.c` | 94-186 | codol_fat_reset / codol_fat_receive |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 895-920 | FAT 分支 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0065，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
长消息 > 1154 → 分片 → 重组 → handle_netchan_frame
```

## 10. 第一条未闭合调用边

**能让消息超长的场景。**

## 11. 已确认事实

- 离线 7 项通过
- 实机零触发

## 12. 尚未确认的假设

- RELIABLE 片段 ack

## 13. 已排除的假设

- 'FAT 是进图阻断点'——已消失

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

分片代码保留、未触发。

## 16. 最小复现条件

构造一条超长可靠命令（如大配装串）触发分片。

## 17. 最小验证实验

**实验 B65**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在客户端上执行长命令（大配装/长文本）<br>2. 观察 RX_FAT_FRAGMENT |
| 通过判据 | 出现分片日志 |
| 失败判据 | 仍无 ⇒ 消息不够长 |
| 成本 | 1 轮 |

## 18. 条件式修复方案

**方案A：保留代码，不投入直到有触发场景。**

**方案B：用服务端主动构造长可靠命令。**

## 19. 修改影响分析

分片是'离线已验证、实机未验'。

## 20. 可测量的验收标准

1. 实机日志出现 RX_FAT_REASSEMBLED 且后续 usercmd 正常。

## 21. 回归测试方案

—

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B65：触发长消息。
- **上游依赖**：`CODOL-ISSUE-0020`

---