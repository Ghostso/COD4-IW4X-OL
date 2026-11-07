# CODOL-ISSUE-0039 — 世界配置写死 dm 模式、30 分、10 分钟、3 秒复活

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

mode_config.gametype 恒 "dm"；score_limit=30、time_limit_ms=600000、respawn_delay_ms=3000。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：world.c:70-79`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-world`　**优先级**：P2　**登记状态**：`NOT_IMPLEMENTED`　**严重度**：medium
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-29 | 源码复核 world.c:70-79 | 确认写死 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0039-01 | source | `world_assets/world.c` | 70-79 | mode_config 写死 | — |
| EV-0039-02 | location | `battle/battle_service.c` | 302-372 | _gs_adapt_dynamic 只改 gamestate 字符串，不改世界 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `world_assets/world.c` | 70-79 | mode_config 写死 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/battle_service.c` | 302-372 | _gs_adapt_dynamic 只改 gamestate 字符串，不改世界 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0039，系统 `battle-world`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0039，系统 `battle-world`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
lobby → active_room.json → 只影响 gamestate 文本；世界仍 dm/30/600000
```

## 10. 第一条未闭合调用边

**mmstart/gamestate 里的模式信息没有传到 world。**

## 11. 已确认事实

- 三处写死在源码里
- --map 之外无模式参数

## 12. 尚未确认的假设

- 官方 gametype 参数表

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

写死。

## 16. 最小复现条件

--map 与 gametype 无论如何变化，world 日志仍是 dm。

## 17. 最小验证实验

**实验 B39**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 把 gametype/score_limit 从 active_room.json 传入<br>2. 打印生效值 |
| 通过判据 | 日志显示 coop 而非 dm |
| 失败判据 | — |
| 成本 | 离线 1 小时 |

## 18. 条件式修复方案

**方案A：把模式配置从 mmstart/gamestate 传入。**

**方案B：加 --gametype/--score-limit 命令行参数。**

## 19. 修改影响分析

模式语义错误；胜负判定无意义。

## 20. 可测量的验收标准

1. 服务端 gametype 与 mmstart 一致。

## 21. 回归测试方案

test_static_closure 断言 gametype。

## 22. 修复准备度

**FIX_READY**

- **下一步**：在 world_init 前读 active_room.json 的 game_type。
- **上游依赖**：无

---