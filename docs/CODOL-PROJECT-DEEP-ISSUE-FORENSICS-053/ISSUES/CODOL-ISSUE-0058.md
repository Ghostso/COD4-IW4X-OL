# CODOL-ISSUE-0058 — 小地图为空：northyaw 缺失、compass_map_* 需地图边界

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

configstring 里缺 northyaw；compass_map_* 需要地图边界。

## 2. 历史首次发现过程

- **首次发现**：2026-10-22（`HANDOFF_20261022_PAUSE.md §1.5`）
- **最近验证**：2026-10-22
- **所属系统**：`battle-snapshot`　**优先级**：P3　**登记状态**：`OPEN`　**严重度**：low
- **是否阻塞可玩战斗**：否

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-22 | HANDOFF 记录 |  |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0058-01 | source | `battle/battle_service.c` | 302-372 | 只改 header，不补 configstring | — |
| EV-0058-02 | location | `firingrange-gamestate.bin` | — | 模板 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 302-372 | 只改 header，不补 configstring |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `firingrange-gamestate.bin` | — | 模板 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0058，系统 `battle-snapshot`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

本 Issue 的协议字段与字节布局：见 §6 的 `firingrange-gamestate.bin`，以及 `05_PROTOCOL_GAPS.md` 中 battle-snapshot 对应小节。

## 9. 完整数据流

```
gamestate configstring → 小地图
```

## 10. 第一条未闭合调用边

**configstring 编号与格式。**

## 11. 已确认事实

- configstring 缺 northyaw（文档）

## 12. 尚未确认的假设

- 编号与格式

## 13. 已排除的假设

(本 Issue 尚无已排除假设)

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

未补。

## 16. 最小复现条件

—

## 17. 最小验证实验

**实验 B58**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 补 northyaw 后观察小地图 |
| 通过判据 | 小地图有内容 |
| 失败判据 | — |
| 成本 | 1 轮 |

## 18. 条件式修复方案

**方案A：从地图 zone 取边界与朝向补进 configstring。**

**方案B：—**

## 19. 修改影响分析

HUD 不完整，但不阻断可玩性验证。

## 20. 可测量的验收标准

1. 小地图有内容。

## 21. 回归测试方案

—

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B58：补 northyaw。
- **上游依赖**：`CODOL-ISSUE-0020`

---