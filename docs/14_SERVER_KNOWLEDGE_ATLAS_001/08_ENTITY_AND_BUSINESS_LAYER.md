# 08 — 游戏状态与业务层 / ENTITY & BUSINESS LAYER

> 必须区分“引擎提供的通用能力”与“CODOL 的具体业务实现”。一个模式能跑 ≠ 所有业务状态结构相同。

## 1. 玩家与实体

| 项 | OLD/1113（源码） | 2697（反汇编） | ol-mod（源码） | IW4x（参考） |
|---|---|---|---|---|
| client_t | `sv_client.c`，CS_FREE/CS_CONNECTED/CS_PRIMED/CS_ACTIVE | 同族（STATIC-INFERENCE） | `server_mp` 自有 | `Game/Structs.hpp` |
| entity 状态 | `sv_snapshot.c` + `codol\snapshot\*` | `codol_2697_entities.c`（`_WriteEntities`/`_WriteEntityPayload`） | `server_mp/sv_gamestate_mp.hpp` | `Game/Engine/` |
| Netfield | `MSG_WriteDeltaEntity` / `MSG_WriteBits` | `_CODOL2697_*Field`、`codol_2697_fields.c` | `sv_native_playerstate_mp.cpp` | `ConfigStrings.cpp` |
| 实体编号 | 位流索引（5 位 changedBitIndex 等） | 同上族 | 自有 | 自有 |

证据：EV-Old-Connect, EV-Old-Legacy, EV-2697-Modules。

## 2. Snapshot 构建 / 差量 / 基准

| 项 | OLD/1113 | 2697 |
|---|---|---|
| 构建入口 | `SV_BuildClientSnapshot` | `_CODOL2697_WriteSnapshot` RVA 0xA4FA0 |
| 差量 | MSG_WriteDeltaEntity | `codol_2697_delta.c`（`_WriteDeltaValue`/`_ReachDeltaValue`） |
| 基准 | client snapshot baseline | `_CODOL2697_PrepareHistory`（RVA 0xA249D） |
| 区域拼接 | — | `0x728` / `0x2C38` / `count*0x1F8` / `count*0x13C` / `count*0x5C` |

## 3. 地图与 Configstrings

| 项 | OLD/1113 | 2697 |
|---|---|---|
| 地图加载 | `SV_SpawnServer`（sv_main.c:5723）→ `SV_InitGameProgs`（:6099） | `_CODOL_MountTarget2697Archives`（RVA 0x1400C3）+ archive probe |
| archive 激活 | — | `_CODOL_Target2697ArchivesActive`（RVA 0x140133）判 `[edx+0x34] == 0x16D` |
| configstring 数 | 6519（武器从 5362） | count ≤ 0x1DD7 |
| 诊断 | — | `CoDOL 2697 map archives mounted: %u (%s)` / `map mount failed: %s (asset %u)` |

## 4. 武器 / 装备 / 附件

| 项 | OLD/1113 | 2697 |
|---|---|---|
| 模块 | `codol\weapon\*` | `codol_weapon_2697.c`（`_core/_keys/_loader/_registry/_runtime`） |
| 函数 | — | `_CODOL_BuildWeapon2697Core` 0xF38D7、`_BuildWeapon2697Registry` 0xF48EB、`_CODOL2697_ParseWeaponRecipe` 0xF4E6F、`_CODOL_LoadEngineWeapon2697` 0x164307 |
| 附件表 | — | `attachment-registry2697.json/.txt`（101,415 / 72,864 B） |
| CVar | — | `CODOL_INVENTORY2697`、`CODOL_RUNTIME_WEAPONS2697` |
| 复用价值 | 参考 | OPTIONAL（不进 MVP） |

## 5. 游戏模式 / 脚本 VM

| 项 | OLD/1113 | 2697 | ol-mod |
|---|---|---|---|
| GSC 脚本 | `codol\script\*`（150 文件），锁定 1.1.1.13 pmove/武器 wire ID | `scripts\` 1,341 文件 + `script-overlay2697\` | `zm.lua` 等；`assets/backend/1004` |
| 脚本 VM | `scr_vm_*` + `cscr_*` | 同族 | `Game/Scripting/` |
| 模式 | 基础模式框架 | 地图/模式/武器/挑战脚本 | `CodolPlaylist.cpp` |

## 6. 大厅 / 房间 / 匹配 / 会话

| 项 | 证据来源 | 状态 |
|---|---|---|
| 会话记录（21/5 findSessions） | DEV-BOOKING-018/019/024 | VERIFIED（A/B 字段映射已恢复） |
| Battle 端点下发 | `build_session_record(host_ipv4, host_port)` | VERIFIED |
| booking / accepted / mmbook / mmstart | DEV-BOOKING-011/012/021/024 | VERIFIED（部分动态） |
| 房间 ready | — | 自述 SetReady(1) 本地回读 ≠ backend ready ack（ol-mod partial/synthetic） |
| 2697 注册门控 | E1 | VERIFIED |
| 大厅冻结 | GOLDEN-LOBBY-001 | VERIFIED（只冻结大厅） |

## 7. 后续版本新增业务概念（PIK10 等）

| 概念 | 证据 | 状态 |
|---|---|---|
| PIK10 / SKU 目录 / marketplace | `REF_LOBBY_KIT_CAP009`（mem_sku / mkt_assets / provider_dump） | 部分 VERIFIED（大厅侧） |
| 2697 inventory | `CODOL_INVENTORY2697` | STATIC-INFERENCE |
| 2697 profile wire | `CODOL2697_PROFILE_WIRE` | STATIC-INFERENCE |
| 武器 recipe | `_CODOL2697_ParseWeaponRecipe` | VERIFIED（存在）/ BLOCKED（语义） |
| 恢复镜像 `.tp3/.tvm0/.rimp` | 见 `15` | BLOCKED |

## 8. 业务层对照结论

1. **引擎通用能力**（实体、Netfield、delta、快照、脚本 VM、地图）在 Old/1113/2697 间**同族**，来自公共引擎。
2. **CODOL 业务实现**（configstring 6519 条、武器 wire ID 1024、记分板/HUD/安全档案发布、2697 注册门控、PIK10/SKU）是**CODOL 专有**。
3. **2697 是相对 Old/1113 的业务/协议升级**：新增独立 writer 层与门控，不是换引擎。
4. **不同项目同业务功能可能用不同实现**（例如大厅：第三方 REF_LOBBY_KIT vs ol-mod backend vs C# SessionDescriptor）。
5. **一个模式能运行，不代表所有业务状态都采用相同数据结构。**