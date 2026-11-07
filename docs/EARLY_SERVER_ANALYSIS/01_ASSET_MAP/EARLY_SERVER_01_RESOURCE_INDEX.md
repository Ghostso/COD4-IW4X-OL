# EARLY_SERVER_01 — 服务端资源 / 数据 / 配置索引

> 阶段 1 交付物。只列**实际发现**的文件；未发现项单列。路径相对 `CODOL_Server\`。

## 1. 脚本资源（CONFIRMED）

| 路径 | 规模 | 说明 |
|---|---|---|
| `dedicated\bin\home\codol_rawfiles\` | 1,341 文件 / 18.27 MB | GSC 脚本树；`AGENTS.md` 声明为唯一可编辑脚本树（服务端运行时加载） |
| `dedicated\bin\home\main\sh1x_svr_scripts.iwd` | 4,277,656 B | 服务端脚本归档 |
| `dedicated\scripts\` | 68 文件 / 1.07 MiB | 仓库脚本 |
| `dedicated\scriptdocumentation\` | 6 文件 | 脚本函数文档 |
| `lobby\resources\mp_playlists_shipRetail_cb2.info` | 31,611 B | 官方播放列表 |
| `lobby\resources\playlist_descriptors.json` | 5,072 B | 播放列表描述 |

## 2. 地图 / 出生点 / 路径点（CONFIRMED）

| 路径 | 规模 | 说明 |
|---|---|---|
| `dedicated\bin\home\main\mp\` | 目录 | 对局地图数据 |
| `dedicated\bin\home\main\waypoints\` | 目录 | 机器人路径点 |
| `lobby\resources\map_spawns.proposed.json` | 5,575,280 B | 地图出生点表 |
| `lobby\resources\map_rotation.state.json` | 186 B | 地图轮换状态 |
| `lobby\zones\` | 7 文件 / 0.15 MiB | 读取客户端 `.ff` zone |

## 3. 武器 / 装备 / 规则数据表（CONFIRMED）

| 路径 | 大小 | 说明 |
|---|---:|---|
| `lobby\codol_weapon_recipe.json` | 623,522 | 武器配方 |
| `lobby\weapon_ammo_table.json` | 16,226 | 弹药 |
| `lobby\weapon_anim_table.json` | 90,303 | 动画 |
| `lobby\melee_table.json` | 45,070 | 近战 |
| `lobby\wpn_ballistics.json` | 37,955 | 弹道 |
| `lobby\wpn_firemodes.json` | 14,459 | 开火模式 |
| `lobby\wpn_firetime.json` | 36,555 | 开火时序 |
| `lobby\wpn_adstimes.json` | 13,113 | 开镜时间 |
| `lobby\wpn_movescale.json` | 1,717 | 移动系数 |
| `lobby\resources\weapon_camo_ids.json` | 23,517 | 迷彩 ID |
| `lobby\resources\unlock_tables.proposed.json` | 99,653 | 解锁表 |
| `lobby\resources\unlock_flags.json` | 36,530 | 解锁标志 |

## 4. 进度 / 玩家数据 / 商店（CONFIRMED）

| 路径 | 大小 | 说明 |
|---|---:|---|
| `lobby\resources\progression_tables.json` | 630,296 | 进度表 |
| `lobby\resources\playerdata_defs.proposed.json` | 99,976 | 玩家数据定义 |
| `lobby\resources\mpdata_layout.proposed.json` | 97,898 | mpdata 布局 |
| `lobby\resources\mpdata.playerclass.md` | 18,150 | 兵种文档 |
| `lobby\resources\mpdata*.proposed` | 多份 | 各档位 mpdata 模板 |
| `lobby\resources\mpdata.<uid>` / `mpdata_s.<uid>` | 数份 | 在线玩家档案（含真实 uid，**唯一副本**） |
| `lobby\players\13381199018740372280.json` | 13,424 | 玩家档案 |
| `lobby\players\16426850347057299284.json` | 13,623 | 玩家档案 |
| `lobby\resources\marketplace_catalogue.json` | 376,371 | 商店目录 |
| `lobby\resources\items_cha*.proposed` | 多份 | 角色物品 |
| `lobby\resources\purchased_items.txt` | 1,202 | 已购物品 |
| `lobby\resources\wallet.json` | 133 | 钱包 |
| `lobby\resources\lobby.sqlite` | 237,568 | SQLite 玩家库 |
| `lobby\resources\match_report*.json` / `match_report.journal.log` | 多份 | 结算回写记录 |

## 5. 配置文件（CONFIRMED）

| 路径 | 大小 | 说明 |
|---|---:|---|
| `dedicated\bin\home\main\q3config_server.cfg` | 1,465 | 服务端配置 |
| `dedicated\bin\START-CODOL-SERVER.cmd` | 12,116 | 服务端启动（未执行） |
| 根 `START-ALL/LOBBY/SERVER/CLIENT.cmd`、`STOP-ALL.cmd` | — | 全栈编排（未执行） |
| `lobby\1-START-LOBBY.cmd` | 32,419 | 大厅启动（未执行） |
| `lobby\docker-compose.yml` / `Dockerfile` | 3,858 / 4,149 | 容器化配置 |
| `lobby\dw_types.json` | 349,034 | 协议类型定义 |
| `codol_user.txt` / `codol_client.txt` / `codol_match.txt` | 2,405 / 529 / 134 | 顶层状态/设置 |
| `dedicated\bin\home\main\missingasset.csv` | 8,908 | 缺失资源清单 |

## 6. 密钥 / 凭据类（存在性；CONFIRMED；内容不输出）

| 路径 | 大小 |
|---|---:|
| `lobby\securitykey.bin` | 16 B |
| `lobby\game_admissions.txt` | 203 B |
| `dedicated\bin\home\codol_sessions.txt` | 167 B |
| `lobby\native_server_rcon.txt` | 15 B |
| `lobby\resources\configs_s.info` / `.plaintext.orig` | 430 / 161 B |

## 7. 日志 / 崩溃 / 反汇编（CONFIRMED）

| 路径 | 大小 |
|---|---:|
| `dedicated\bin\home\main\games_mp.log` | 7,861,923 |
| `dedicated\bin\home\main\qconsole.log` | 218,428 |
| `dedicated\bin\home\main\enterleave.log` | 124,718 |
| `dedicated\bin\home\main\qconsole.log.old` | 48,402 |
| `dedicated\bin\home\main\qconsole.r2.log` | 14,754 |
| `dedicated\bin\home\main\qconsole.prev.log` | 3,602 |
| `lobby\map_selection.log` | 92,536 |
| `dedicated\bin\codol_crash.txt` | 1,692 |
| `dedicated\bin\sys_error.txt` | 159 |
| `dedicated\dis\` | 10 文件（反汇编） |

## 8. 文档 / 研究资料（CONFIRMED，知识资产）

| 路径 | 规模 |
|---|---|
| `dedicated\docs\CODOL_PORT.md` | 248 KB |
| `dedicated\docs\` | 398 文件 / 26.80 MiB（大量 `CODOL_*.md` 逆向笔记） |
| `lobby\docs\` | 40 文件 / 2.05 MiB（`protocol_map.md` 53 KB、`ERRORS.md` 652 KB、`MISSING-FEATURES.md` 124 KB、`dw_types.md` 121 KB、`session_persistence.md` 65 KB、`map_selection.md` 85 KB） |
| `dedicated\wiki\` | 106 文件 |

## 9. 运行环境 / 打包（CONFIRMED）

| 路径 | 规模 | 说明 |
|---|---|---|
| `build\pyenv\` | 7,633 文件 / 197.63 MiB | Python 隔离环境 |
| `build\pyinstaller\` | 30 文件 / 113.14 MiB | PyInstaller 打包 |
| `build\logs\` | 9 文件 / 5.98 MiB | 构建日志 |
| `tools\*.pyw/.py` | 20 文件 | 启动/运维工具 |
| `resource\icon.ico/.png` | 85,775 / 215,374 | 图标 |

## 10. 未发现项（NOT_OBSERVED）

| 关注项 | 状态 |
|---|---|
| 服务端目录内的 `.ff`/`.ff2` 地图二进制 | NOT_OBSERVED（`.ff` 在客户端与 `lobby\zones`；服务端用 `.iwd`/rawfiles） |
| `.pdb` / `.map` 符号 | NOT_OBSERVED |
| 独立 DB/登录服务的数据目录 | NOT_OBSERVED（内嵌 SQLite） |
| 服务端专属 `.dll` 加密库（mbedtls/tomcrypt） | NOT_OBSERVED（以源码静态编入） |

## 11. 证据等级

- §1–§9 均为 **CONFIRMED**（文件存在 + 大小可复算）。
- §10 为 **NOT_OBSERVED**，不等同于"不存在"。
- 密钥类仅记录**存在性与大小**，不输出任何秘密内容。
