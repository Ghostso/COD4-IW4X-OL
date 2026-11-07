# CODOL-ISSUE-0035 — 快照基线在发送成功前就前移，发送失败会导致基线错位

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

svc->snap_from = svc->snap_cur 在 send_frame 之前执行；send_frame 失败时客户端没收到这一帧，但服务端已把它当基线。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：battle_service.c:541`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-snapshot`　**优先级**：P2　**登记状态**：`OPEN`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码复核 :541 位置 | 确认在 send_frame(:569) 之前 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0035-01 | source | `battle/battle_service.c` | 541 | snap_from = snap_cur | — |
| EV-0035-02 | source | `battle/battle_service.c` | 618-640 | send_frame | — |
| EV-0035-03 | location | `battle/battle_service.c` | 569 | if (send_frame(...) < 0) return -1; | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 541 | snap_from = snap_cur |
| `battle/battle_service.c` | 618-640 | send_frame |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 569 | if (send_frame(...) < 0) return -1; |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0035，系统 `battle-snapshot`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `battle/battle_service.c`，以及 `05_PROTOCOL_GAPS.md` 中 battle-snapshot 对应小节。

## 9. 完整数据流

```
build → snap_from 前移 → send_frame（可能失败）
```

## 10. 第一条未闭合调用边

**无失败分支的回滚。**

## 11. 已确认事实

- 前移在 send 之前（源码顺序）

## 12. 尚未确认的假设

- 实机是否真的出现过发送失败

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

顺序未改。

## 16. 最小复现条件

注入 send 失败（如 buffer 满），检查基线。

## 17. 最小验证实验

**实验 B35**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 单测：mock send 返回 -1<br>2. 断言 snap_from 未改变 |
| 通过判据 | 基线不变 |
| 失败判据 | 基线仍前移 ⇒ 确认缺陷 |
| 成本 | 离线 30 分钟 |

## 18. 条件式修复方案

**方案A：把基线前移放到 send_frame 成功之后。**

**方案B：按 ack 前移（更严格，但需要更多改造）。**

## 19. 修改影响分析

后续帧全部按错误基线做增量。

## 20. 可测量的验收标准

1. 发送失败的帧不改变基线。

## 21. 回归测试方案

test_snapshot_delta 增加发送失败用例。

## 22. 修复准备度

**FIX_READY**

- **下一步**：把 :541 的赋值移到 send_frame 成功分支内。
- **上游依赖**：无

---