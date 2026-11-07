# -*- coding: utf-8 -*-
from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md')
s='''# 对局内完整度缺口矩阵（2026-10-23）

> 目标不是“能进图”，而是单客户端在同一 PID 生命周期内完成：进图、移动、开火、命中、受伤、死亡、复活、计分、结束。
> 状态：`DONE` 有可复核 3.19 证据和运行产物；`PARTIAL` 已有数据结构或局部实现；`TODO` 尚无足够证据。

## 总览

| 域 | 状态 | 当前已有 | 仍缺的关键信息 | 下一步证据入口 |
|---|---|---|---|---|
| 启动链与认证 | DONE | IIPS、Auth、Lobby 隔离链、受保护哈希基线 | 无（但不得改动 frozen kit） | `run_codol_001/run_frozen_chain_once.py` |
| 战斗传输握手 | DONE | NAT、DTLS-like、P2P 密钥交换、AES/HMAC 帧 | 长时间丢包/重放边界仍需实机 | `src/battle/battle.c` |
| 消息外层/opcode | PARTIAL | 已知 gamestate/configstring/snapshot/EOF 候选链 | 完整 `svc_*`/`clc_*` 分发和错误边界未全部逐项绑定 | `0x473A50`、`0x5C2260` |
| Gamestate/configstring | DONE | decoder/encoder、765 槽样本对拍 | 更多地图和动态 configstring 模板 | `tools/codol_gamestate_codec.py` |
| Snapshot codec | DONE | 黄金首帧字节级一致、delta 路径测试 | 更多实体类型的真实字段组合 | `src/battle/snapshot.c` |
| netField 语义 | PARTIAL | playerState 51/87、entityState 17/24 已命名 | 剩余字段、baseline 默认值、实体数组变体语义 | `0xDA8078`、`0xDA63E8`、`docs/PHASE4_*` |
| Usercmd/可靠命令 | DONE | 600+15 向量、背包命令闭环 | 真实按键到所有武器动作的端到端覆盖 | `src/world/usercmd.c` |
| 事件/计分 | PARTIAL | 46 个事件命令、关键 handler xref | kill/death/score/round/objective 的实际消息参数与状态转换 | `0x4F2350`、`0x5BF940`、`0x5C0FD0` |
| 基础武器参数 | PARTIAL | 18 把 firingrange 的伤害、射速、换弹、移动倍率、命中倍率；最终 WeaponDef 六段伤害/命中表布局已记录 | ADS spread 的完整运行时字段族、recoil/view kick 的生效公式 | `0xBB4`、`0xBCC`、`0xBF0`、`0x810..0x824`、`0xAC0` |
| 配件合成 | PARTIAL | type-43 header + 4912 records；95 个附件 135 条安全 scalar 进入运行表 | 545 条 string/resource class 的全局解析、168 个无本地尾表资产的共享槽位 | `0x49D760`、`0x49DA10`、`0x49DBC1` |
| 命中盒/护甲/穿透 | TODO | 已有 hit-location API 和 21 槽位概念 | 角色骨骼/命中盒几何、护甲减伤、FMJ 穿透、盾牌分支 | bullet trace 与 G_Damage 链 |
| 爆炸/投掷物 | TODO | WeaponDef 中已有 explosion/projectile 字段入口 | fuse、碰撞、溅射衰减、状态效果、投掷物生命周期 | WeaponDef projectile block + actor/entity |
| actor/vehicle/turret/loot | TODO | entity 类型表已枚举 | 各实体结构、状态机、移动/攻击/掉落 | `docs/INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md` |
| 模式状态机 | TODO | spawn 基础状态、46 个事件命令 | round/score/objective/spawn/respawn/match-end 权威推进 | 模式表 + event consumer |
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
'''
p.write_text(s,encoding='utf-8')
print('wrote',p)
