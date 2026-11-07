# 对局内完整度缺口矩阵（2026-10-23）

> 目标不是“能进图”，而是单客户端在同一 PID 生命周期内完成：进图、移动、开火、命中、受伤、死亡、复活、计分、结束。
> 状态：`DONE` 有可复核 3.19 证据和运行产物；`PARTIAL` 已有数据结构或局部实现；`TODO` 尚无足够证据。

## 总览

| 域 | 状态 | 当前已有 | 仍缺的关键信息 | 下一步证据入口 |
|---|---|---|---|---|
| 启动链与认证 | DONE | IIPS、Auth、Lobby 隔离链、受保护哈希基线 | 无（但不得改动 frozen kit） | `run_codol_001/run_frozen_chain_once.py` |
| 战斗传输握手 | DONE | NAT、DTLS-like、P2P 密钥交换、AES/HMAC 帧 | 长时间丢包/重放边界仍需实机 | `src/battle/battle.c` |
| 消息外层/opcode | PARTIAL | 已知 gamestate/configstring/snapshot/EOF 候选链 | 完整 `svc_*`/`clc_*` 分发和错误边界未全部逐项绑定 | `0x473A50`、`0x5C2260` |
| Gamestate/configstring | DONE | decoder/encoder、765 槽样本对拍 | 更多地图和动态 configstring 模板 | `tools/codol_gamestate_codec.py` |
| Snapshot codec | PARTIAL | 141B 历史黄金向量一致；`bw_run` 已改为按表宽编码并加位级回归 | 124B 可读向量的写侧冲突、真实客户端 ack、更多实体字段组合 | `src/battle/snapshot.c`、`tests/test_snapshot_run.c` |
| netField 语义 | PARTIAL | playerState 51/87、entityState 17/24 已命名 | 剩余字段、baseline 默认值、实体数组变体语义 | `0xDA8078`、`0xDA63E8`、`docs/PHASE4_*` |
| Usercmd/可靠命令 | DONE | 600+15 向量、背包命令闭环 | 真实按键到所有武器动作的端到端覆盖 | `src/world/usercmd.c` |
| 事件/计分 | PARTIAL | 46 个事件命令、关键 handler xref | kill/death/score/round/objective 的实际消息参数与状态转换 | `0x4F2350`、`0x5BF940`、`0x5C0FD0` |
| 基础武器参数 | PARTIAL | 18 把 firingrange 的 3.19 zone 六段伤害 `0xD10`、六段距离 `0xD28`、20 项位置倍率 `0xD4C`；hitloc_mapping 0..19 已恢复（20 槽） | 最终运行时 WeaponDef、recoil/view kick、ADS/移动/姿态修正公式 | `tools/export_weapondefs.py`、`src/battle/weapondefs.c` |
| 配件合成 | PARTIAL | type-43 header + 4912 records；44 个附件 94 条安全 scalar 进入运行表 | 545 条 string/resource class 的全局解析、168 个无本地尾表资产的共享槽位 | `0x49D760`、`0x49DA10`、`0x49DBC1` |
| 命中盒/护甲/穿透 | PARTIAL | 20 槽 hitloc、六段伤害、通用 armor/shield 策略、动态实体 AABB trace | 原生骨骼/命中盒几何、原生护甲表、FMJ 材质穿透、完整 G_Damage 分支 | bullet trace 与 G_Damage 链 |
| 爆炸/投掷物 | PARTIAL | 通用 THROWN/FLYING/STUCK/ARMED/EXPLODED/DUD 状态机、clipmap sweep、bounce/sticky/impact、内外半径伤害 | 3.19 原生 fuse/radius/伤害字段命名、状态效果、真实投掷物与客户端同步 | WeaponDef projectile block + actor/entity |
| actor/vehicle/turret/loot | PARTIAL | 实体表及 5 类通用 spawn/free 生命周期；动态 AABB 参与移动/射弹 trace | 3.19 原生实体布局、AI/载具/炮塔行为、掉落与世界交互 | `docs/INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md` |
| 模式状态机 | PARTIAL | WARMUP/ACTIVE/INTERMISSION/GAME_OVER、join/kill/score/respawn/time-limit 通用状态机，world 已接线 | 3.19 原生 gametype/round/objective/spawn 参数与事件消费者 | 模式表 + event consumer |
| 完整实机验证 | TODO | 首个实机链路与部分输入证据 | 同一 PID 的移动/射击/命中/受伤/死亡/复活/计分/结束证据 | `run_codol_001/runs/<RUN_ID>/` |

## 对“完整对局”的硬门槛

1. 客户端能稳定进入 `ACTIVE` 战斗状态，且 gamestate/configstring 无模板依赖。
2. 移动、跳跃、下蹲、ADS、开火、换弹、切枪均由 usercmd 驱动并在快照中收敛。
3. 至少一把枪完成真实命中：子弹 trace、距离伤害、命中部位倍率、护甲/穿透、伤害事件和死亡状态可复核。
4. 至少一种非枪械武器完成生命周期闭环：手雷/火箭/投掷物之一。
5. 至少一个模式完成 spawn、得分、回合/目标、结束、踢出/断线清理。
6. 所有证据位于独立 `run_codol_001/runs/<RUN_ID>/`，包含前后受保护哈希。

## 当前最关键的三条阻塞

1. **WeaponDef 字段族仍未完全映射**：六段伤害、命中倍率和基础 spread 布局已有 3.19 本地证据；recoil/view kick、ADS 精度、移动/姿态修正公式仍缺。
2. **WeaponAttach 共享字符串槽未闭合**：标量可用，但 545 条 string/resource 记录和 168 个无本地尾表资产不能安全消费。
3. **命中盒与 G_Damage 世界分支未闭合**：当前项目有伤害数值 API，但没有完整角色命中几何、护甲/穿透和爆炸/车辆分支。

## 不在本轮伪称完成的内容

- 没有把 IW4X/OLmod 的地址或数值直接当 3.19 证据。
- 没有把 `0x31xxxxxx` token 猜成固定文件指针。
- 没有把“能进图”或“首帧 snapshot 对上”写成“完整对局可用”。




## 2026-10-23 本轮结论

- 对局主表 6 张、数组类型 24 个、去重布局 18 种均已导出。
- `bw_run` 已按表宽实现，C/Python 各有位级回归；141B 历史 KAT 通过。
- 但 Phase 3 仍为 `PARTIAL`：历史 124B 可读向量的写侧冲突未解，且 141B 载荷没有真实客户端 ack 证据。
- WeaponDef 最终布局旧候选 `+0xBB4/+0xBCC/+0xBF0` 已被 3.19 zone 对拍否定；OLFinal 的 `0x13F5A40/0x7417B88` 在 3.19 中也读为零。运行时布局保持未验证。
- 完整对局需要的命中盒/护甲/穿透、投掷物/爆炸、actor/vehicle/objective、模式状态机与 Phase 8 同 PID 实机证据仍未完成。


## 2026-10-23 第二轮证据增量

- 六段伤害与距离已从 3.19 zone 闭合：`0xD10` 的 6 个 int、`0xD28` 的 6 个 float；18/18 firingrange 一致。
- 20 项命中倍率仍位于 `0xD4C`；独立 `hitloc_mapping` 字符串表给出 0..19 的部位名。
- `0xD10..0xD1C` 的附件 override 是浮点倍率，已限制为对应伤害档缩放。
- 投掷物/爆炸专用字段仍未命名；RPG 与手雷槽位差异不足以安全判定 fuse/radius。
- 本轮静态基线先通过 21/21；后续静态闭合轮提升为 22/22，且没有启动任何新客户端。


## 2026-10-23 静态闭合轮（Round 1）

- `world.gamemode` 生命周期已闭合：init 分配、spawn join、step tick、shutdown 释放。
- 玩家移动、通用实体和投掷物共用静态 ClipMap + 动态 AABB trace；trace 会返回命中的 `entity_num`。
- 通用伤害、投掷物/爆炸、actor/vehicle/turret/loot/objective、模式状态机均有 C 测试覆盖。
- `battle_service` 已通过 `bind_world/apply_usercmd` 把真实输入推进 `world.players/entities`，并同步快照缓存；不再是独立 player 与 world 两套状态。
- 验证结果：Debug 全量构建成功，`ctest` **22/22 passed**；静态清单 **42 文件 / bad=0**。
- 明确边界：这些是通用静态运行时闭环，不等于 CODOL 原生骨骼/命中盒、原生爆炸字段、原生 gametype 全部已证明；真实客户端同 PID 动态证据仍待下一轮。

## 动态轮执行门槛（Round 2）

- 新 run 目录：`run_codol_001/runs/<NEW_RUN_ID>/`，不得复用静态目录。
- 启动前：受保护哈希校验、无残留 client PID、3074 无监听、提权代理 PID/端口可用。
- 启动器：`run_frozen_chain_once.py`，单次调用最多一个客户端，不自动重启。
- 必收证据：IIPS/Auth/Lobby/Battle 时间戳、同一 client PID、进入 ACTIVE 世界、snapshot ack。
- 战斗链：移动、射击、命中、受伤、死亡、复活、计分、结束各至少一条可复核事件。
- 结束：前后受保护哈希一致，证据全部留在该 run 目录。
- 当前代理：`CODOLServer/logs/elevated_agent.json` 已更新为运行中的新代理；UAC 已由用户允许。



## 2026-10-23 动态首试（Round 2）

- run：`run_codol_001/runs/DYNAMIC_CLOSURE_20261023_2255`。
- 单客户端 PID 17204；10 秒退出 rc=`0xFFFFFFFF`，未加载 `iips.dll/ifs2.dll`。
- 未进入 Auth / Battle，未产生 usercmd/snapshot；C 战斗服 PID 16936 已起但未收到客户端握手。
- 关键配置差异：本次使用了 `sandbox_datafix_20260929`；已验证可长活的上一轮使用 `sandbox_ifs1_20260923`。
- 结果：动态轮 **未闭合**；下一轮必须使用 `sandbox_ifs1_20260923`，且保持新 run、单客户端、无自动重试。
- 受保护六个启动核心文件前后哈希一致；残留 C 战斗服与 3074 服务已停止。
