# 09 — 移动与战斗系统缺口

---

## 1. 移动

### 1.1 当前实现路径

```
usercmd → codol_battle_service_apply_usercmd()
        → if (world) codol_movement_process_usercmd_dt(world, 0, cmd, dt)
              → 构造局部 codol_player_t（on_ground=true 恒真）
              → codol_player_move_in_world(player, cmd, dt, world, ent_num)
              → 回填 ps->origin/velocity
        → else codol_player_move_in_world(&svc->player, ...)
```

### 1.2 已知缺陷

| # | 缺陷 | 证据 | Issue |
|---|---|---|---|
| 1 | 跳跃在 usercmd 路径上不可达 | `codol_pmove_single()` 从不被调用；`walking` 从不被设置 | ISSUE-0028 |
| 2 | `on_ground` 恒 true | `movement.c:125` 硬编码 | ISSUE-0028 |
| 3 | 地面是 `z = -116` 无限平面 | `collision.c:11` | ISSUE-0029 |
| 4 | 重力只在 `!walking` 时施加，而 walking 恒 false（局部对象 memset） ⇒ 实际上恒定施加 | `movement.c:85` | 同上 |
| 5 | dt 已修（曾写死 1/128 导致位移偏小上千倍） | `movement.c:96-101` 注释 | 已修 |
| 6 | 每 tick 与每输入的区别：`codol_world_step` 以 `NULL,0` 调用，世界不自走 | `main.c:164` | ISSUE-0032 |
| 7 | 服务器 tick 20 Hz vs 快照 128 Hz 不一致 | `main.c:154` vs `battle_service.c:412` | 新增（见下） |

### 1.3 ★ 新发现：tick 与快照频率不一致

```
main.c:154      tick_interval_us = 1e6 / tick_rate_hz     (默认 20 Hz = 50 ms)
battle_service.c:412  CODOL_SNAP_DT_MS 7                  (约 143 Hz)
world.c:106     codol_mode_tick(world_mode(world), 16)     (写死 16 ms)
```

三个时间步长互不相干。后果：
- 128 Hz 的快照里，大部分帧的 `svc->player` 完全没变
- 模式状态机按 16 ms 推进，但实际被调用的频率是 20 Hz（每 50 ms）⇒ 时间慢了 3.125 倍
- 服务端时间基准与客户端预期的 128 Hz 世界时间不同源

**这是一条此前没有任何报告记录过的缺陷**，会影响"对局时间/回合推进"的全部表现。

### 1.4 移动的真实状态（区分输入源）

| 输入 | 服务端能看到？ | 服务端能影响客户端？ |
|---|---|---|
| 前后左右（fwd/right） | ✅ 518/832 条非零 | ❌（位置推不动） |
| 视角（yaw/pitch） | ✅ 20 个不同取值 | ❌ |
| 跳跃 | ⚠️ 按钮位定义冲突；且服务端分支不可达 | ❌ |
| 蹲伏 | ❓ 未见记录 | ❌ |
| 开火 | ❌ bit0 从未出现 | — |

**结论**：服务端能"看到"水平移动与视角，但**不能影响**客户端的位置。
也就是说当前是"客户端权威 + 服务端旁观"。

---

## 2. 射击与命中

### 2.1 当前实现

```c
/* battle_service.c:76-102 */
distance = |target.origin - player.origin|;
codol_damage_apply(world, target_num, weapon, distance, CODOL_HITLOC_TORSO_UPPER, ...);
```

- 武器写死 `"m4a1tech_mp"`
- 命中部位写死 `TORSO_UPPER`
- 目标写死为 `ensure_damage_target()` 在 `(0,0,-116)` 生成的 `owner=1001` actor
- **没有射线、没有遮挡、没有 miss**

### 2.2 后果

| 事实 | 含义 |
|---|---|
| `codol_damage_apply` 本身正确（33 伤害、100→67） | 数值层可用 |
| 但调用它的方式不是射击 | 不能声称"命中系统已实现" |
| `codol_movement_trace()` 存在且有测试 | 能力有，但没接进伤害路径 |
| 目标血量不重置 | 长跑后所有命中打在 0 血实体（ISSUE-0031） |

### 2.3 缺失项

| 项 | 状态 |
|---|---|
| 子弹方向（从视角取 forward） | ❌ |
| 射线 trace（player→infinity） | ❌（函数有，未接） |
| 命中盒几何（20 个 hitloc 槽只有名字） | ❌ |
| 距离衰减（六段伤害表已有） | ✅ 数据有，公式已用 |
| 护甲 / 盾 | 只有通用 policy（`armor_scale` / `shield_scale`） |
| FMJ 材质穿透 | ❌ |
| 后坐力 / 视野抖动 | ❌ |
| ADS 精度修正 | ❌ |
| 投射物 / 爆炸 | 代码有，**无调用者** |

---

## 3. 生命值 / 死亡 / 复活 / 计分

| 环节 | 实现 | 接线 |
|---|---|---|
| 生命值扣减 | ✅ `codol_damage_apply` | ✅（但只服务合成靶） |
| 死亡判定 | ✅ `result.killed` | ⚠️ 只打日志，不触发任何后续 |
| 死亡处理（掉枪/尸体/通知） | ❌ | — |
| 复活 | ✅ `codol_mode_respawn_due()` | ❌ **无调用者** |
| 击杀计分 | ✅ `codol_mode_player_killed()` | ❌ **无调用者** |
| 回合/胜负 | ✅ `codol_mode_end_match()` | 只由 `player_killed` 内部调用，而它没被调用 |
| 对局结束 | ✅ `codol_mode_is_match_over()` | ❌ 无调用者 |
| 结果回传大厅 | ❌ | — |

**即：整条"击杀→计分→复活→结束"链在代码里都在，但没有一个入口把它启动起来。**

---

## 4. 武器数据

| 项 | 状态 | 证据 |
|---|---|---|
| 18 把 firingrange 武器的六段伤害 | ✅ 从 3.19 zone 闭合（`0xD10` 6 个 int） | `INMATCH_COMPLETENESS_GAP_MATRIX` 第二轮 |
| 六段距离 | ✅（`0xD28` 6 个 float） | 同上 |
| 20 项位置倍率 | ✅（`0xD4C`） | 同上 |
| `hitloc_mapping` 0..19 部位名 | ✅ | 同上 |
| 运行时 `WeaponDef` 布局 | ❌ **未验证**；旧候选 +0xBB4/+0xBCC/+0xBF0 已被否定 | ISSUE-0066 |
| 配件（4912 条记录 / 44 附件的标量） | ✅ 部分 | ISSUE-0066 |
| 配件字符串/资源（545 条） | ❌ | ISSUE-0066 |
| 后坐力 / 扩散 / ADS 公式 | ❌ | ISSUE-0067 |
| 动态武器索引 | ❌ 无静态全表，每图起点不同 | ISSUE-0057 |

---

## 5. 与"可玩战斗"的距离

按 `INMATCH_COMPLETENESS_GAP_MATRIX` 的六条硬门槛逐条核对（截至 2026-10-29）：

| # | 门槛 | 状态 |
|---|---|---|
| 1 | 客户端稳定进入 ACTIVE 战斗状态 | ❌ 客户端甚至不连战斗服（ISSUE-0020） |
| 2 | 移动/跳跃/蹲/ADS/开火/换弹/切枪由 usercmd 驱动并在快照收敛 | ⚠️ 移动与视角可观测；跳跃不可达；开火位缺失；位置不收敛 |
| 3 | 至少一把枪完成真实命中（trace/距离/部位/护甲/穿透/事件/死亡） | ❌ 无 trace、无穿透、死亡不触发 |
| 4 | 至少一种非枪械武器完成生命周期闭环 | ❌ 投射物无调用者 |
| 5 | 至少一个模式完成 spawn/得分/回合/结束/清理 | ❌ 模式状态机未接线 |
| 6 | 全部证据在独立 run 目录，含前后受保护哈希 | ⚠️ 机制有；`marketplace_store.py` 不符（ISSUE-0001） |

**0/6 完全满足；2 项部分满足。**

---

## 6. "Rubber-banding / 预测与权威同步"

当前根本不存在这个问题，因为：

- 服务端位置推不动客户端（ISSUE-0025）⇒ 没有权威
- 客户端自己的预测就是最终结果 ⇒ 没有校正

换句话说，**"预测 vs 权威"这条线还没有开始**。
任何关于 rubber-banding 的讨论现在都是超前的。
