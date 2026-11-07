# CODOL-ISSUE-0022 — 战斗服 --map 参数不改变碰撞数据（仍加载 coop_train clipmap）

> 深度取证档案 · 2026-10-29 · `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053`

---

## 1. 问题精确定义

E1 运行日志打印 `world "mp_firingrange" assets loaded (29 clip volumes)`，而 codol_clipmap_coop_train.inc 只有 29 行，内容全是 mp_firingrange 的道具（tire_wall 等）。world.c:66-67 把 clipmap 与 map_ents 都指向同一个编译期数组，--map 只存字符串。

## 2. 历史首次发现过程

- **首次发现**：2026-10-29（`本次审计：源码 + 10-29 run 日志`）
- **最近验证**：2026-10-29
- **所属系统**：`battle-world`　**优先级**：P1　**登记状态**：`OPEN`　**严重度**：high
- **是否阻塞可玩战斗**：是

## 3. 全部相关历史实验

| 日期 | 实验/事件 | 结果 |
|---|---|---|
| 2026-10-25 | Phase 7 把 clipmap 接进世界 | 固定为 coop_train |
| 2026-10-27 | 文档指出'换图不改变客户端是否连 28960' | 但未指出服务端也不换碰撞 |
| 2026-10-29 | E1 日志实锤：--map mp_firingrange 仍加载 29 volumes | 确认 |

## 4. 原始证据及 SHA-256

| Evidence ID | 类型 | 路径 | 定位 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0022-01 | source | `world_assets/world.c` | 55-96 | codol_world_init / codol_world_load_assets | — |
| EV-0022-02 | location | `world_assets/world.c` | 66-67 | world->clipmap = codol_static_boxes; world->map_ents = 同 | — |
| EV-0022-03 | location | `world/collision.c` | 25-29 | codol_static_boxes[] 来自 codol_clipmap_coop_train.inc | — |
| EV-0022-04 | location | `main.c` | 64 | 默认 map_name="mp_firingrange"（--map 可覆盖，但无效果） | — |

> 完整哈希与存在性见 `EVIDENCE_INDEX.json`；本表只列与该 Issue 直接相关的条目。

## 5. 当前源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `world_assets/world.c` | 55-96 | codol_world_init / codol_world_load_assets |

## 6. 关键函数及调用关系

| 文件/地址 | 行/位置 | 作用 |
|---|---|---|
| `world_assets/world.c` | 66-67 | world->clipmap = codol_static_boxes; world->map_ents = 同 |
| `world/collision.c` | 25-29 | codol_static_boxes[] 来自 codol_clipmap_coop_train.inc |
| `main.c` | 64 | 默认 map_name="mp_firingrange"（--map 可覆盖，但无效果） |

## 7. 客户端逆向证据

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0022，系统 `battle-world`）不涉及客户端逆向。

## 8. 网络协议字段及字节布局

`NOT_APPLICABLE` — 该问题（CODOL-ISSUE-0022，系统 `battle-world`）不涉及线上协议字段与字节布局。

## 9. 完整数据流

```
main.c --map → config → codol_world_init(map_name) → 只存字符串 → load_assets 用常量数组
```

## 10. 第一条未闭合调用边

**没有任何'按地图名选 clipmap'的代码路径。**

## 11. 已确认事实

- E1 日志：Map: mp_raid 时仍打印 29 clip volumes（10-28 run 同样）
- clipmap 数据源是编译期 .inc

## 12. 尚未确认的假设

- mp_raid 的 clipmap 是否可从 zone 提取（未做）

## 13. 已排除的假设

- '--map 没传进去'——config.battle_port 等参数正常生效，说明参数解析没问题

## 14. 历史修复尝试

(无历史修复尝试)

## 15. 当前代码状态

无按图选择的实现；--map 实际只影响日志与 world->map_name。

## 16. 最小复现条件

codol_battle_server.exe --map <任意> → 日志始终 '29 clip volumes'。

## 17. 最小验证实验

**实验 B22**

| 项 | 内容 |
|---|---|
| 步骤 | 1. 在 world.c 加断言：map_name 与 clipmap 来源不一致时 WARN<br>2. 对比 --map coop_train vs --map mp_raid 的 trace 结果 |
| 通过判据 | 两种 map 产生不同 trace |
| 失败判据 | 相同 ⇒ 确认无效 |
| 成本 | 离线 20 分钟 |

## 18. 条件式修复方案

**方案A（条件式）：先提取 mp_raid zone 的 clipmap，再按 map_name 查表选择。**

**方案B：短期只支持 coop_train，并在 --map 非法时报错退出，避免静默错误。**

## 19. 修改影响分析

决定服务端碰撞是否与客户端地图一致；影响移动/命中/出生。

## 20. 可测量的验收标准

1. 加载 mp_raid 时使用 mp_raid 的碰撞数据（trace 结果可区分）。

## 21. 回归测试方案

probe_world_damage 增加'换图后起点下方有地板'的用例。

## 22. 修复准备度

**BLOCKED_BY_DEPENDENCY**

- **下一步**：依赖 CODOL-ISSUE-0087（layer-2 资产导出）。
- **上游依赖**：`CODOL-ISSUE-0029`, `CODOL-ISSUE-0087`

---