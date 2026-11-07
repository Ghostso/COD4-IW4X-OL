# 07 — 战斗服实现缺口

> 本文件区分三种"没有"：
> **(a) 根本没写** · **(b) 写了但没接线** · **(c) 接线了但有缺陷**。
> 历史报告最常犯的错是把 (b) 当成"已实现"。

---

## 1. 模块级状态总表

| 模块 | 文件 | 写了？ | 接线？ | 缺陷？ | 证据等级 |
|---|---|---|---|---|---|
| 平台/时钟 | `platform/platform.c` | ✅ | ✅ | 双时钟（ISSUE-0039） | impl |
| UDP 传输 | `transport/transport.c` | ✅ | ✅ | — | impl + 10-26 官方 |
| 会话表 | `session/session.c` | ✅ | ✅ | 超时用另一时钟 | impl |
| 线协议 | `wire_codec/wire_codec.c` | ✅ | 部分 | 需人工登记证据 ID | impl |
| 战斗传输（NAT/DTLS/ECDH/帧） | `battle/battle.c` | ✅ | ✅ | 只在 10-26 对官方客户端成立 | sim + 官方(8轮) |
| 战斗服务编排 | `battle/battle_service.c` | ✅ | ✅ | 见 §3 | impl |
| 快照编码 | `battle/snapshot.c` | ✅ | ✅ | 见 ISSUE-0023/0027/0063 | impl + C-ack |
| 武器定义 | `battle/weapondefs.c` | ✅（部分） | ✅ | 运行时布局未验证（ISSUE-0066） | impl |
| 配件 | `battle/weaponattach.c` | ✅（部分） | ✅ | 545 条字符串记录未解 | impl |
| 装备/背包 | `battle/equipment.c` | ✅ | ✅ | — | impl + 实机日志 |
| 实体池 | `entity/entity.c` | ✅ | ✅ | model_index 恒 0 | impl |
| 移动 | `movement/movement.c` | ✅ | ✅ | **jump 不可达**（ISSUE-0028） | impl |
| 玩家 | `world/player.c` | ✅ | ✅ | — | impl |
| 碰撞 | `world/collision.c` | ✅ | ✅ | 写死地面（ISSUE-0029） | impl |
| 战斗/伤害 | `world/combat.c` | ✅ | 仅测试靶 | 距离公式非 trace（ISSUE-0030） | impl |
| 投射物 | `world/projectile.c` | ✅ | ❌ **无调用者** | — | impl（死代码） |
| 模式状态机 | `world/gamemode.c` | ✅ | 部分 | kill/respawn 无调用者（ISSUE-0032） | impl |
| 复制层 | `replication/replication.c` | ✅ | 部分 | build/ack 无调用者 | impl |
| 世界资产 | `world_assets/world.c` | ✅ | ✅ | 换图无效（ISSUE-0022） | impl |
| 证据门 | `diagnostics/evidence_gate.c` | ✅ | ✅ | — | impl |
| 加密 | `crypto/{aes128,sha1,p224}.c` | ✅ | ✅ | `p224.c:330` 有一处"占位"注释 | impl |
| **消息层（svc_/clc_ 全表）** | — | ❌ | — | 只有 gamestate/snapshot/EOF 三件 | — |
| **Configstring 生成** | — | ❌（只有 `_gs_adapt_dynamic` 改首部） | — | — | — |
| **敌方玩家快照** | — | ❌ | — | 单客户端设计（ISSUE-0033） | — |
| **下行分片** | — | ❌ | — | — | — |
| **对局结算/回传大厅** | — | ❌ | — | — | — |
| **地图资源选择** | — | ❌ | — | `--map` 只存字符串 | — |

---

## 2. 明确的死代码 / 未接线清单（本次审计 grep 结果）

| 函数 | 定义位置 | 调用者 |
|---|---|---|
| `codol_projectile_spawn` | `world/projectile.c:22` | **无** |
| `codol_projectile_step` | `:82` | 仅测试 |
| `codol_projectile_trigger` | `:156` | **无** |
| `codol_mode_player_killed` | `world/gamemode.c:60` | **无** |
| `codol_mode_respawn_due` | `:73` | **无** |
| `codol_replication_build` | `replication/replication.c:11` | **无** |
| `codol_replication_ack` | `:40` | **无** |
| `codol_world_step(..., commands, count)` | `world_assets/world.c:97` | 被 `main.c:164` 以 `NULL, 0` 调用 ⇒ commands 分支是死的 |
| `codol_pmove_single` | `movement/movement.c:71` | **无**（网络路径走 `codol_player_move_in_world`） |
| `_cs_replace_kv` | `battle/battle_service.c:274` | 仅 `(void)` 引用来抑制警告 |

---

## 3. `battle_service.c` 的具体缺陷清单

| # | 位置 | 缺陷 | Issue |
|---|---|---|---|
| 1 | `:541` | 基线在 `send_frame` 之前前移 | ISSUE-0035 |
| 2 | `:610` | gamestate 最多 5 次 | ISSUE-0036 |
| 3 | `:680-703` | stats 状态全局非 per-peer | ISSUE-0034 |
| 4 | `:1100-1127` | 重置只在 key-exchange 分支 | ISSUE-0040 |
| 5 | `:708-839` vs `:923-1053` | 两个重复的 usercmd 分支且已分歧 | ISSUE-0037 |
| 6 | `:425` | 512 B TX 缓冲 | ISSUE-0023 |
| 7 | `:486` | `omit = snapshot_sent`（首帧后不发位置） | ISSUE-0025 |
| 8 | `:524-532` | idx61 恒 false | ISSUE-0027 的历史 |
| 9 | `:53-102` | 合成靶 + 距离公式 | ISSUE-0030/0031 |
| 10 | `:175,178,391,805` | 全部依赖 CWD 相对路径 | ISSUE-0038 |
| 11 | `:643-652` | `send_oob_text` 无长度检查（当前调用安全） | 潜在 |
| 12 | `:302-372` | `_gs_adapt_dynamic` 对 map 串做 `strlen` 无界 | 潜在 |
| 13 | `:805` | keymap CSV 以 `"w"` 打开、从不 fclose | 诊断性 |
| 14 | `:800-820` vs `:994-1024` | keymap 表头一处 `\\n` 一处 `\n` | 诊断性 |
| 15 | `:436` | server_time 基数 1000 无出处 | 待定 |

---

## 4. `main.c` 的具体缺陷

| # | 位置 | 缺陷 | Issue |
|---|---|---|---|
| 1 | `:64` | `map_name = "mp_firingrange"` 硬编码默认 | ISSUE-0022 |
| 2 | `:164` | `codol_world_step(..., NULL, 0, ...)` | ISSUE-0032 |
| 3 | `:165` | session 用 `codol_platform_time_us`，battle 用 `mono_ms` | ISSUE-0039 |
| 4 | `:20-30` | `battle_sink` 丢弃 `ctx` | — |
| 5 | 全局 | 一个 `g_battle`、一个 `server->world`、一个 client 0 | ISSUE-0033 |

---

## 5. 与大厅的接口缺口

| 大厅产出 | 战斗服是否消费 |
|---|---|
| `active_room.json`（map / game_type） | ✅ 仅用来改 gamestate 首部字符串；**不改变世界/map/碰撞** |
| `mmstart` 的 map / gametype | ❌ 完全未传 |
| playlist 编号 | ❌ |
| 67 B 地址块 | 由大厅构造，战斗服不感知 |
| 模式配置（分数上限/时限） | ❌ 写死 dm/30/600000 |

**这是"三个地图真相源"（大厅选图 / 战斗服 `--map` / 编译期 clipmap）不相干的直接后果。**

---

## 6. 构建/可复现性

- CMakeLists 注册 22 个 ctest；有 3 个探针与 1 个 e2e 未注册（ISSUE-0005）。
- `build/Debug` 混有 10-21..10-26 多个状态的产物；`test_session.exe` 与 `codol_battle_server.exe` 同尺寸（ISSUE-0004）。
- 无 git（ISSUE-0003）。
- `p224.c:330` 有 `/* 占位, 下面重算 */` 注释——需确认该行不是漏实现。

---

## 7. 优先级建议

1. 接线 `codol_world_step` 的 commands（一行），让模式状态机真正跑起来。
2. 把 `codol_mode_player_killed` / `respawn_due` / `projectile_*` 接进 `apply_usercmd` / tick。
3. 用 `codol_movement_trace()` 替换 `apply_test_hit` 的距离公式。
4. 把 `--map` 接到真实 clipmap 选择（依赖地图提取）。
5. 扩 TX 缓冲 + 下行分片。
6. 把 per-client 状态移进 assoc（多客户端）。

> 注意：1–3 都是**服务端内部**改动，不会改变客户端是否连接（ISSUE-0020），
> 因此可以与连接问题并行推进，但**不能作为"能进对局"的证据**。
