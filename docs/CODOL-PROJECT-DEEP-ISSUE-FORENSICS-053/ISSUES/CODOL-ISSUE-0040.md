# CODOL-ISSUE-0040 — 多客户端/重连：per-connection 重置只在 key-exchange 分支发生

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

gamestate_sent/snapshot_sent/snapshot_epoch/processed_input_time/FAT 只在此重置；会话超时后重建但未重新 key exchange 的情况未覆盖。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：battle_service.c:1100-1127`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-network`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-24 | 曾修过一次'第二轮再进卡等待玩家数据' | 只补了快照相关字段 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0040-01 | source | `battle/battle_service.c` | 1105-1127 | 重置块 | — |
| EV-0040-02 | location | `battle/battle_service.c` | 1090-1095 | KEY_EXCHANGE_OK 分支 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 1105-1127 | 重置块 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 1090-1095 | KEY_EXCHANGE_OK 分支 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0040，系统 `battle-network`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-network 对应小节。

## 9. 完整数据流

```
key-exchange → 重置 → 会话继续
```

## 10. 第一条未闭合调用边

**非 key-exchange 的重连路径是否存在。**

## 11. 已确认事实

- 重置块只在 key-ex 分支

## 12. 尚未确认的假设

- 是否有其它建会话路径

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-24 | 补 snapshot_* 重置 | 部分 |

## 15. 当前代码状态

重置散落在 key-ex 分支内。

## 16. 最小复现条件

模拟会话超时后同地址重连，检查各字段。

## 17. 最小验证实验

**实验 B40**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把重置抽成 reset_session_state()<br>2. 在所有新建会话处调用 |
| 通过判据 | 任意新会话开始时字段为初值 |
| 失败判据 | — |
| 成本 | 离线 30 分钟 |

## 18. 条件式修复方案

**方案A：抽函数并在所有新建会话处调用。**

**方案B：保持现状并文档化。**

## 19. 修改影响分析

可能出现'第二轮再进卡住'。

## 20. 可测量的验收标准

1. 任意新会话开始时全部相关字段为初值。

## 21. 回归测试方案

test_session 增加重连用例。

## 22. 修复准备度

**FIX_READY**

- **下一步**：抽出 reset_session_state() 并从 assoc 新建处统一调用。
- **上游依赖**：`CODOL-ISSUE-0034`

---