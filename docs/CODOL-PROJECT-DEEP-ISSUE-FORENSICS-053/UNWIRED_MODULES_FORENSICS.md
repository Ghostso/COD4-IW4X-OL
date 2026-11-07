# 未接线模块取证报告

> 上一轮审计用 `grep` 得出结论"这些函数没有调用者"。本文件按任务要求，
> **不只用文本搜索**，而是逐一核对：定义 → 调用者 → 函数指针/回调 → 注册表 → 构建路径 → 主循环 → 网络输出 → 回归测试。

---

## 0. 方法

对每个函数执行 7 步检查：

1. `grep -n "<symbol>"` 全 `src/` + `include/` + `tests/`
2. 检查是否有**取地址** `&symbol`（函数指针）
3. 检查是否有**同名结构体字段**（回调槽）
4. 检查 `CMakeLists.txt` 是否把它所在 `.c` 编进主目标
5. 检查主循环 `main.c` 的调用图
6. 检查是否影响 `send_frame` / `send_snapshot` 的输出
7. 检查 `tests/` 是否覆盖

---

## 1. 结果总表

| 函数 | 定义 | 直接调用者 | 取地址 | 结构体回调槽 | 编进主目标 | 进入主循环 | 影响网络输出 | 有测试 |
|---|---|---|---|---|---|---|---|---|
| `codol_projectile_spawn` | `world/projectile.c:22` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ✅ `test_static_closure.c` |
| `codol_projectile_step` | `world/projectile.c:82` | 仅测试 | 无 | 无 | ✅ | ❌ | ❌ | ✅ |
| `codol_projectile_trigger` | `world/projectile.c:156` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ✅ |
| `codol_mode_player_killed` | `world/gamemode.c:60` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ✅ |
| `codol_mode_respawn_due` | `world/gamemode.c:73` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ✅ |
| `codol_replication_build` | `replication/replication.c:11` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ❌ |
| `codol_replication_ack` | `replication/replication.c:40` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ❌ |
| `codol_pmove_single` | `movement/movement.c:71` | **无** | 无 | 无 | ✅ | ❌ | ❌ | ❌ |
| `_cs_replace_kv` | `battle/battle_service.c:274` | 仅 `(void)` 抑制警告 | 无 | 无 | ✅ | ❌ | ❌ | ❌ |

**结论**：全部 9 项确认**没有任何间接调用路径**。
不存在"通过函数指针表注册"的隐藏调用——本工程里没有任何一处对它们取地址。

---

## 2. 逐项详查

### 2.1 `codol_projectile_spawn` / `_step` / `_trigger`

**定义**：`src/world/projectile.c`

```c
void codol_projectile_default(codol_projectile_t *p);            /* :7  */
codol_result_t codol_projectile_spawn(codol_world_t *, codol_projectile_t *,
                                      ...);                       /* :22 */
codol_result_t codol_projectile_step(codol_world_t *, codol_projectile_t *,
                                     float dt_ms, ...);            /* :82 */
codol_result_t codol_projectile_trigger(codol_world_t *, codol_projectile_t *,
                                        ...);                      /* :156*/
```

| 检查 | 结果 |
|---|---|
| 取地址 | 全树 `&codol_projectile` **0 处** |
| 回调槽 | `codol_world_t` / `codol_battle_service_t` 里**没有**投射物函数指针 |
| 主循环 | `main.c` 的 while 循环只调 `codol_world_step` / `codol_session_check_timeouts` / `codol_battle_service_tick` |
| usercmd 路径 | `apply_usercmd` 只调 `codol_equipment_step` + `apply_test_hit`，**不产生投射物** |
| 网络输出 | 投射物从不进入 `send_snapshot` |
| 测试 | `tests/test_static_closure.c` 直接调用 → 测试能过，但那是**自测** |

**判定**：`NOT_IMPLEMENTED`（在真实路径上）。

**影响**：手雷/火箭/爆炸完全不存在。这不是"效果不对"，是"没有"。

---

### 2.2 `codol_mode_player_killed` / `codol_mode_respawn_due`

**定义**：`src/world/gamemode.c:60` / `:73`

| 检查 | 结果 |
|---|---|
| 取地址 | **0 处** |
| 回调槽 | `codol_mode_t` 结构体**无**函数指针 |
| 谁会调它 | 应当由"伤害结算 → 死亡事件"触发；`codol_damage_apply` 只设 `result.killed`，**不通知模式** |
| 主循环 | `codol_world_step` 只调 `codol_mode_tick(mode, 16)` |
| 网络输出 | 无 |

**判定**：`NOT_IMPLEMENTED`（在真实路径上）。

**关键断层（代码级）**：

```c
/* world/combat.c:61 */
result->killed = target->health == 0;
/* ← 到此为止。没有 codol_mode_player_killed(...) */
```

⇒ **伤害与模式之间没有连线**。即使真人被打死，计分/复活/结束都不会发生。

---

### 2.3 `codol_replication_build` / `codol_replication_ack`

**定义**：`src/replication/replication.c:11` / `:40`

| 检查 | 结果 |
|---|---|
| 取地址 | **0 处** |
| 主循环 | 只调 `codol_replication_init`（world.c:65）与 `codol_replication_commit_frame`（world.c:109） |
| 谁产快照 | **`battle_service.c:send_snapshot` 直接调 `codol_snapshot_build`**，绕过 replication 层 |
| 测试 | 无 |

**判定**：`DEAD_LAYER`。

**含义**：`replication` 这一层是**第二套快照机制**，与实际发包路径并行且未使用。
它是架构上的重复，不是缺陷——但意味着"replication ACK 历史"在真实路径上不存在。

---

### 2.4 `codol_pmove_single`

**定义**：`src/movement/movement.c:71`

| 检查 | 结果 |
|---|---|
| 取地址 | 0 |
| 谁在跑移动 | `codol_battle_service_apply_usercmd` → `codol_movement_process_usercmd_dt` → `codol_player_move_in_world` |
| `codol_pmove_single` 内含 | 跳跃分支（`pm->walking`）+ 重力 |

**判定**：`DEAD`，且**它的死亡直接导致 ISSUE-0028（跳跃不可达）**。

这是本次"不只用 grep"的收获：`codol_pmove_single` 不只是没人调，
它**独占**了跳跃逻辑，所以跳跃在网络路径上根本不存在。

---

### 2.5 `_cs_replace_kv`

`battle_service.c:274` 定义，`:370` 只有 `(void)_cs_replace_kv;` 抑制警告。
⇒ 死代码，且从未被调用过。

---

## 3. 与主循环的真实调用图（实测）

```
main()
 └ while(g_running)
     ├ codol_transport_poll()            → codol_battle_service_on_packet()
     │                                     └ handle_plain()
     │                                        └ apply_usercmd()
     │                                           ├ codol_equipment_step()   ← 开火计数
     │                                           └ apply_test_hit()         ← 合成靶
     │                                              └ codol_damage_apply()  ← 到此为止
     ├ codol_world_step(NULL, 0, &frame)  ← commands 参数恒为 NULL
     │   └ codol_mode_tick(mode, 16)
     ├ codol_session_check_timeouts()
     └ codol_battle_service_tick()
         ├ send_snapshot()                → codol_snapshot_build()  ← 直接调，不走 replication
         └ send_gamestate()
```

**不在这张图上的**：projectile 全部、mode_player_killed、mode_respawn_due、
replication_build/ack、pmove_single、cs_replace_kv。

---

## 4. 结论与优先级

| 模块 | 是否应接线 | 前置条件 | 建议 |
|---|---|---|---|
| `codol_pmove_single` 的跳跃逻辑 | **是** | 无（纯服务端） | 把跳跃分支并入 `process_usercmd_dt`，成本 S |
| `mode_player_killed` | **是** | 需要真实的死亡判定（ISSUE-0030） | 在 `codol_damage_apply` 后接线 |
| `mode_respawn_due` | 是 | 同上 | 在 tick 里轮询 |
| `projectile_*` | 是 | 需要武器投掷触发点 | 在 equipment_step 产生投射物后接线 |
| `replication_build/ack` | **否** | — | 建议**删除**（重复层），或在快照重构时统一 |

**注意**：接线这些**不会**让客户端连上战斗服（ISSUE-0020 是另一条链）。
它们只影响"连上之后能不能打着"。
