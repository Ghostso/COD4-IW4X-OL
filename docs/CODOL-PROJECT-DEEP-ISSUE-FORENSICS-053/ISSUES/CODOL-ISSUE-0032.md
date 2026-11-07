# CODOL-ISSUE-0032 — 投射物/爆炸、模式击杀、复活、复制层全部定义但从未被调用

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

codol_projectile_spawn/step/trigger 无调用者；codol_mode_player_killed、codol_mode_respawn_due 无调用者；codol_replication_build/_ack 无调用者；codol_world_step 的 commands 参数在 main.c:164 传 NULL,0。对上述函数取地址的代码 0 处（已排除函数指针路径）。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：全 src 调用点 grep + 取地址检查`）
- **最近验证**：2026-10-29
- **所属系统**：`combat`　**优先级**：P1　**登记状态**：`NOT_IMPLEMENTED`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-23 | INMATCH_COMPLETENESS_GAP_MATRIX 标为 PARTIAL（'静态闭环'） | 那是指测试能过 |
| 2026-10-29 | 本审计按 7 步法（定义/调用者/取地址/回调槽/构建/主循环/网络输出/测试）复核 | 确认全部未接线 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0032-01 | source | `main.c` | 157-175 | 主循环 | — |
| EV-0032-02 | source | `world/gamemode.c` | 60-92 | player_killed/respawn_due/end_match | — |
| EV-0032-03 | source | `world/projectile.c` | 22-165 | projectile_* | — |
| EV-0032-04 | source | `replication/replication.c` | 11-78 | replication_build/ack | — |
| EV-0032-05 | location | `world/combat.c` | 61 | result->killed = ... 之后没有任何 mode 调用（断层） | — |
| EV-0032-06 | location | `world_assets/world.c` | 106 | codol_mode_tick(mode,16) 是唯一被调的模式函数 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `main.c` | 157-175 | 主循环 |
| `world/gamemode.c` | 60-92 | player_killed/respawn_due/end_match |
| `world/projectile.c` | 22-165 | projectile_* |
| `replication/replication.c` | 11-78 | replication_build/ack |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `world/combat.c` | 61 | result->killed = ... 之后没有任何 mode 调用（断层） |
| `world_assets/world.c` | 106 | codol_mode_tick(mode,16) 是唯一被调的模式函数 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0032，系统 `combat`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0032，系统 `combat`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
见 UNWIRED_MODULES_FORENSICS.md §3 的实测调用图
```

## 10. 第一条未闭合调用边

**伤害 → 死亡事件 之间没有连线（world/combat.c:61 之后直接 return）。**

## 11. 已确认事实

- 9 个函数全部零调用者、零取地址（已排除间接调用）
- codol_pmove_single 独占跳跃逻辑因而导致 ISSUE-0028

## 12. 尚未确认的假设

- 接线时应遵循的事件顺序

## 13. 已排除的假设

- '通过函数指针表注册'——全树无取地址

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

全部定义存在、编进主目标、但不在主循环调用图上。

## 16. 最小复现条件

在 main.c 里把 world_step 的 commands 接上，跑一次，看 mode 状态是否推进。

## 17. 最小验证实验

**实验 B32**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在 codol_damage_apply 返回 killed 后调用 codol_mode_player_killed<br>2. 在 tick 里轮询 codol_mode_respawn_due |
| 通过判据 | 一次对局内出现 spawn→kill→score 日志链 |
| 失败判据 | 无变化 ⇒ 接线位置不对 |
| 成本 | 离线 2 小时 |

## 18. 条件式修复方案

**方案A：按 INMATCH 门槛 5 逐项接线（按依赖顺序：伤害→击杀→计分→复活→结束）。**

**方案B：先接最小闭环（kill→score），再逐步加。**

## 19. 修改影响分析

对局无法结束/计分/复活/投掷物。

## 20. 可测量的验收标准

1. 一次对局内出现 spawn→kill→score→respawn→end 的可复核日志链。

## 21. 回归测试方案

test_static_closure 改为走主循环路径。

## 22. 修复准备度

**FIX_READY**

- **下一步**：先在 combat.c 的 killed 处接 mode_player_killed，再跑一次确认日志链。
- **上游依赖**：`CODOL-ISSUE-0030`

---