# CODOL-ISSUE-0024 — 实体段客户端收得下但看不到（model_index 恒 0、实体号冲突）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

开 snapshot_entities.on 后 ack 速率 83.02→83.05/s（比值 1.00），快照 103→176 B ents=8；撤掉即回 103。但游戏内看不到任何实体：只发 eType+origin，model_index 由 memset 恒 0，实体号 0..7 与客户端自己的玩家/装饰槽冲突。

## 2. 历史首次发现过程

- **首次发现**：2026-10-24（`HANDOFF_20261025_BINARY_BISECT.md §17`）
- **最近验证**：2026-10-24
- **所属系统**：`battle-entity`　**优先级**：P1　**登记状态**：`PARTIALLY_RESOLVED`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-24 13:20 | ENTITY_SECTION_20261024_1320 同客户端 ON/OFF 对照 | ack 不变 |
| 2026-10-25 | §17.5 提出'畸形实体段对照' | 至今未做 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0024-01 | source | `battle/battle_service.c` | 497-510 | 实体段填充（只取 number/type/x/y/z） | — |
| EV-0024-02 | source | `entity/entity.c` | 18-33 | codol_entity_alloc，memset 使 model_index=0 | — |
| EV-0024-03 | location | `battle/snapshot.c` | 497-499 | bw_write_entities 插入在 0x05 之前 | — |
| EV-0024-04 | location | `battle/snapshot.c` | 247-300 | bw_write_entities 实现 | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 497-510 | 实体段填充（只取 number/type/x/y/z） |
| `entity/entity.c` | 18-33 | codol_entity_alloc，memset 使 model_index=0 |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `battle/snapshot.c` | 497-499 | bw_write_entities 插入在 0x05 之前 |
| `battle/snapshot.c` | 247-300 | bw_write_entities 实现 |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0024，系统 `battle-entity`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0024，系统 `battle-entity`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
world->entities[] → ents[8] → bw_write_entities → 位于消息终止符 0x05 之前
```

## 10. 第一条未闭合调用边

**'客户端是否解析实体段'——从未做畸形对照。**

## 11. 已确认事实

- ack 速率在开/关之间几乎不变（比值 1.00）
- 快照 103→176 B, ents=8
- 撤掉开关当帧回到 103 B

## 12. 尚未确认的假设

- 客户端是否读了这段位；畸形态是否会被判废

## 13. 已排除的假设

- '实体段格式错导致整包判废'（§16.5 的风险已被 §17.2 排除）

## 14. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-24 | 发送 8 条实体 | 不可见 |

## 15. 当前代码状态

实体段代码保留，默认关闭（文件开关 snapshot_entities.on）。

## 16. 最小复现条件

runs/<RUN>/kit 放一个空文件 snapshot_entities.on，观察 bytes/ents 与游戏内可见性。

## 17. 最小验证实验

**实验 B24**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 基线：不推实体段<br>2. 正常：推当前格式<br>3. 畸形：推一条字段截断的实体段 |
| 通过判据 | 畸形 ≠ 基线 ⇒ 客户端确实在读 |
| 失败判据 | 畸形 == 基线 ⇒ 整段被忽略 |
| 成本 | 3 轮 |

## 18. 条件式修复方案

**方案A（条件式）：若 B24 证明被解析 → 补 model_index（需 configstring 绑定）与正确实体号空间。**

**方案B：若被忽略 → 先查实体段的插入位置与终止符。**

## 19. 修改影响分析

决定多人/实体同步是否可能。

## 20. 可测量的验收标准

1. 客户端世界里出现一个我们发送的、可见的、原本不存在的实体。

## 21. 回归测试方案

ack 速率比值保持在 1.00±0.05。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：B24：畸形实体段对照。
- **上游依赖**：`CODOL-ISSUE-0023`

---