# CODOL-ISSUE-0028 — 跳跃在 usercmd 网络路径上不可能触发（walking 从不被刷新）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

codol_pmove_single() 里 jump 分支要求 pm->walking 为真（movement.c:79-84），但 codol_movement_process_usercmd_dt() 每次构造全新局部 codol_player_t、设 on_ground=true，从不设置 walking，也从不调用 codol_pmove_single()（movement.c:116-129）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：src/movement/movement.c`）
- **最近验证**：2026-10-29
- **所属系统**：`movement`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 本审计全 src 调用点 grep + 取地址检查 | 确认 pmove_single 零调用者 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0028-01 | source | `movement/movement.c` | 71-87 | codol_pmove_single（含 jump） | — |
| EV-0028-02 | source | `movement/movement.c` | 102-141 | codol_movement_process_usercmd_dt（不调 pmove_single） | — |
| EV-0028-03 | location | `battle/battle_service.c` | 126-143 | apply_usercmd → process_usercmd_dt | — |
| EV-0028-04 | location | `world/player.c` | — | codol_player_move_in_world 实际移动实现 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `movement/movement.c` | 71-87 | codol_pmove_single（含 jump） |
| `movement/movement.c` | 102-141 | codol_movement_process_usercmd_dt（不调 pmove_single） |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 126-143 | apply_usercmd → process_usercmd_dt |
| `world/player.c` | — | codol_player_move_in_world 实际移动实现 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0028，系统 `movement`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0028，系统 `movement`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
usercmd → apply_usercmd → process_usercmd_dt → move_in_world（无 jump 分支）
```

## 10. 第一条未闭合调用边

**move_in_world 里是否有等价 jump 逻辑（需读 world/player.c）——即便有，walking 也不会被维护。**

## 11. 已确认事实

- codol_pmove_single 在 src/ 内零调用者、零取地址
- process_usercmd_dt 里 on_ground 恒 true

## 12. 尚未确认的假设

- 客户端跳跃时服务端的实际表现（无实机）

## 13. 已排除的假设

- '跳跃位定义错导致不起跳'——那是 ISSUE-0060，与此处是两个独立缺陷

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

jump 逻辑存在于死函数 pmove_single 中。

## 16. 最小复现条件

单测：构造 buttons=0x01 的 usercmd，断言 vz>0。当前必然失败。

## 17. 最小验证实验

**实验 B28**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 写一个单测直接调 process_usercmd_dt，buttons=0x01<br>2. 断言 ps->velocity[2] > 0 |
| 通过判据 | vz 变正 |
| 失败判据 | vz 不变 ⇒ 确认死路径 |
| 成本 | 离线 20 分钟 |

## 18. 条件式修复方案

**方案A：把 jump 分支并入 process_usercmd_dt / move_in_world，并正确维护 walking。**

**方案B：改用 trace 结果决定 on_ground，再据 on_ground 允许跳跃。**

## 19. 修改影响分析

垂直移动目前完全依赖客户端预测；服务端永远认为玩家在地面。

## 20. 可测量的验收标准

1. 带跳跃键的 usercmd 使 vz>0 且随后被重力拉回。

## 21. 回归测试方案

test_player 增加跳跃用例。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 codol_movement_process_usercmd_dt 里按 cmd->buttons 的跳位设置 vz，并用 trace 维护 on_ground。
- **上游依赖**：无

---