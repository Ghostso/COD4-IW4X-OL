# EARLY_SERVER_01 — 完整服务端资产地图

> 阶段 1 交付物。全部条目基于磁盘文件证据；未启动任何样本程序。

## 0. 方法

1. 以阶段 0 的全量清单（15,754 文件）为底，按**内容证据**（PE 头、导入表、文件头签名、源码 include、目录语义）而非仅文件名，识别服务端相关资产。
2. 对全部 207 个 PE 生成目录（`EARLY_SERVER_01_PE_CATALOG.csv` + `_pe_detail.json`），再按"是否为游戏服务端组件"过滤出 **12 个真实服务端 PE**（见 §2）。
3. 对源码、脚本、配置、资源、数据、密钥、日志、崩溃转储、调试符号分别建索引。

## 1. 顶层结构（CONFIRMED）

样本根 `CODOL_Server\` 实际是一个**多子项目的开发工作区**，不是单一安装目录：

| 路径 | 性质 | 关键证据 |
|---|---|---|
| `dedicated\` | **原生服务端（C/C++ 源码 + 构建）** | `README.md` 标题 "sh1x server — Call of Duty Online Closed Alpha Server"；`makefile` 的 `CODOL_AREAS`；`src\codol\` 9 个区域 |
| `lobby\` | **Demonware/大厅模拟器（纯 Python）** | `README.md`（alpha0022）；`dw-capture.py`（100 KB）；`demonware\` 10 个模块 |
| `patcher\` | 客户端补丁 DLL 的源码与产物 | `kernel33.c`（60 KB）、`Kernel33.dll`、`gen_tables.py`、`c1_tables.h` |
| `build\` | Python 隔离环境 + PyInstaller 打包 | `build\pyenv\`（7,633 文件）、`build\pyinstaller\` |
| `tools\` | 启动/运维 Python 工具 | `codol_launcher.pyw`（67 KB）、`codol_stack.py`（54 KB） |
| `resource\` | 图标资源 | `icon.ico`、`icon.png` |
| 根 `*.cmd` | 编排脚本（**本轮未执行**） | `START-ALL.cmd`、`START-LOBBY.cmd`、`START-SERVER.cmd`、`START-CLIENT.cmd`、`STOP-ALL.cmd` |
| `_clone_backup_*` / `_purge_backup_*` | 作者历史备份 | 与复用价值无关（阶段 4 归为 E 类） |

## 2. 真实服务端程序目录（CONFIRMED）

完整字段见 `EARLY_SERVER_01_BINARY_CATALOG.csv`。摘要：

| 相对路径 | 大小 | SHA-256（前 16） | 架构 | ImageBase | EP(RVA) | 角色 |
|---|---:|---|---|---|---:|---|
| `dedicated\bin\codol_dedrun.exe` | 8,469,493 | `28366ae992310bfe` | x86 | 0x400000 | 0x1480 | **游戏服务端主程序** |
| `dedicated\bin\codol_dedrun_next.exe` | 8,469,493 | `28366ae992310bfe` | x86 | 0x400000 | 0x1480 | 与上一行**逐字节相同**（同 SHA-256） |
| `dedicated\bin\pexports.exe` | 286,708 | `037c8f83e0eeafc5` | x86 | 0x400000 | 0x12b0 | 第三方导出表工具（非游戏组件） |
| `Kernel33.dll` | 10,270,208 | `02ea59a83cecff9a` | x86 | 0x69100000 | 0x1390 | 客户端补丁 DLL |
| `patcher\Kernel33.dll` | 10,270,208 | `02ea59a83cecff9a` | x86 | 0x69100000 | 0x1390 | 与根 `Kernel33.dll` 同 SHA-256 |
| `dedicated\plugins\censor\censor.dll` | 89,090 | `70e3c6d72b288a28` | x86 | 0x70980000 | 0x1380 | 服务端插件 |
| `dedicated\plugins\example_cpp_plugin\cpptest_plugin.dll` | 75,390 | `a3e772c62f8641ca` | x86 | 0x68900000 | 0x1380 | 示例 C++ 插件 |
| `dedicated\plugins\iw4ol_b3hide\b3hide.dll` | 83,057 | `46d02aa2c95321b6` | x86 | 0x6a040000 | 0x1380 | 服务端插件 |
| `dedicated\plugins\legacybanlist\legacybanlist.dll` | 156,340 | `fc155cbb0a666320` | x86 | 0x6cf00000 | 0x1380 | 封禁插件 |
| `dedicated\plugins\pchat\pchat.dll` | 65,428 | `aaec8eb99e855fae` | x86 | 0x62140000 | 0x1380 | 聊天插件 |
| `dedicated\plugins\screenshotsender\nehoscreenshotuploader.dll` | 164,635 | `49d35d81233e6bbe` | x86 | 0x65580000 | 0x1380 | 截图上传插件 |
| `dedicated\plugins\simplebanlist\simplebanlist.dll` | 154,281 | `b5ecf68ed480a233` | x86 | 0x6e300000 | 0x1380 | 封禁插件 |
| `dedicated\plugins\sourcebansplugin\sourcebansplugin.dll` | 181,618 | `9bb078eae069fea1` | x86 | 0x6d5c0000 | 0x1380 | SourceBans 插件 |
| `dedicated\plugins\warn\warn.dll` | 82,171 | `c89c7006efb5bdd2` | x86 | 0x6e940000 | 0x1380 | 警告插件 |

**关键证据（CONFIRMED）**：

- `codol_dedrun.exe`：**185 个导出符号全部为 `Plugin_*` 前缀**（`_pe_detail.json`），导入 `WS2_32.dll`(25 函数)/`KERNEL32.dll`(87)/`msvcrt.dll`(142)/`ADVAPI32.dll`(4)/`CRYPT32.dll`(4)/`GDI32.dll`(5)/`USER32.dll`(28)/`SHELL32.dll`(1)/`WINMM.dll`(1)；链接器 2.30；时间戳 2026-10-04T09:03:01Z；节区含 `.bss` 虚拟 329 MB。
- 全部 8 个插件 DLL 的导入表都包含 **`codol_dedrun.exe`**，即它们是**通过主程序导出接口加载的进程内插件**，而不是独立进程。
- `Kernel33.dll`：**仅导出 `GetProcAddress` / `LoadLibraryA` 两个符号**（DLL 劫持/转发式补丁），`.rsrc` 节区 10,187,752 B（占文件 99.2%）。

> 注意：`EARLY_SERVER_01_PE_CATALOG.csv` 收录 207 个 PE，其中绝大多数是 `build\pyenv`（Python/扩展模块）与 `build\pyinstaller` 的引导程序，**不属于服务端游戏逻辑**，本报告的"真实服务端 PE"已按上述规则过滤。

## 3. 服务端公共运行库与游戏逻辑模块（CONFIRMED）

### 3.1 原生服务端源码（`dedicated\src\`）

- `dedicated\src\` 共 **1,770 文件 / 24.42 MiB**。
- 服务端专用代码在 `dedicated\src\codol\`，共 **591 文件 / ≈96,686 行**，按 `makefile` 的 `CODOL_AREAS` 划分为 9 个区域：

| 区域 | 文件数 | 职责（源码/头文件命名证据） |
|---|---:|---|
| `script\` | 150 | CoDOL 脚本/内置函数桥 |
| `player\` | 87 | 玩家状态、移动、动画 |
| `snapshot\` | 76 | 快照与 configstrings |
| `weapon\` | 64 | 武器、弹道、装备 |
| `vehicle\` | 48 | 载具 |
| `stats\` | 39 | 统计上传/回传 |
| `collision\` | 33 | 碰撞 |
| `net\` | 28 | **网络/协议（阶段 3 核心）** |
| `assets\` | 66 | fastfile/zone/rawfile 读取 |

- `makefile` 明确：`CODOL_AREAS=net snapshot player weapon vehicle script assets collision stats`；`CODOL_INC` 把每个区域加入 include 路径。
- 底层引擎（CoD4x/IW3 移植）在 `src\` 根：`sv_main.c`、`sv_client.c`、`sv_snapshot.c`、`sv_game.c`、`sv_init_mp.cpp`、`netchan.c`、`net_game.c`、`msg.c`、`common.c`、`cmd.c`、`cvar.c`、`filesystem.c`、`g_*.cpp`（游戏 VM）、`sv_bots.cpp`、`webadmin.c`、`hl2rcon.c`、`maxmind_geoip.c`、`sec_*.c`（签名/更新）、`mbedtls\`、`zlib\`、`tomcrypt\`。

### 3.2 服务端网络/协议模块（`dedicated\src\codol\net\`，CONFIRMED）

| 文件 | 大小 | 职责（函数名证据） |
|---|---:|---|
| `codol_wire.c/.h` | 4,456/2,079 | 线协议常量与分片编解码（`CODOL_WritePacket`/`CODOL_ReadFragment`/`CODOL_Xor`/`CODOL_ExtendCounter`） |
| `codol_network.c` | 24,170 | Win32 UDP 所有者（`CODOL_NetworkInit`/`CODOL_NetworkReceive`/`CODOL_NetworkSend`/`CODOL_NetworkAdmission`/`CODOL_NetworkAuthenticated`/`CODOL_NetworkSaveSessions`） |
| `codol_handshake.c` | 3,199 | INIT/COOKIE 握手状态机（`CODOL_HandshakeInit`/`CODOL_HandshakeCookie`） |
| `codol_association.c` | 4,335 | bdDTLS DATA 关联（`CODOL_AssociationStart`/`Seal`/`OpenDetailed`） |
| `codol_connect.c` | 3,564 | challenge/connect 响应（`CODOL_WriteChallengeResponse`/`CODOL_WriteConnectResponse`/`CODOL_ReadConnectXuid`/`CODOL_ReadConnectUserinfo`） |
| `codol_admission.c/.h` | 9,135/2,708 | 大厅→对局服准入名册（`CODOL_AdmissionIdentify`） |
| `codol_ecdh.c/.h` | 3,751/851 | P-224 密钥交换（`CODOL_ExportPublicKey`/`CODOL_SharedSecret`） |
| `codol_crypto.c/.h` | 4,662/1,063 | DATA 记录加解密（`CODOL_DeriveKey`/`EncryptRecord`/`DecryptRecord`） |
| `codol_netchan.c` | 4,767 | 原生分片收发（`CODOL_NetchanSubmit`） |
| `codol_msg.c/.h` | 3,441/1,131 | 交错 byte/bit 位池（`CODOL_ReadBits`/`WriteBits`…） |
| `codol_client_command.c` | 1,615 | 客户端命令事务式读取（`CODOL_ReadClientCommand`） |
| `codol_usercmd_queue.c/.h` | 5,966/3,087 | 用户命令队列 |
| `codol_pure.c` | 2,488 | pure/校验 |
| `codol_match_status.c` | 2,838 | `sh1x_status` RCON 状态行（大厅轮询用） |
| `codol_atomic_file.c/.h` | 2,307/345 | 原子文件写（名册/会话） |

### 3.3 大厅/登录/会话/匹配/房间服务（`lobby\`，CONFIRMED）

- 纯 Python，无编译产物。入口 `dw-capture.py`（100,516 B），监听 **端口 3074**（README）。
- `demonware\` 10 个服务模块：`dw_wire.py`(15,702)、`dw_auth.py`(18,643)、`dw_storage.py`(33,669)、`dw_rooms.py`(92,493)、`dw_session.py`(20,016)、`dw_marketplace.py`(92,384)、`dw_marketplace_buy.py`(63,169)、`dw_admission.py`(32,760)、`dw_game_admission.py`(8,910)、`a22_tiger.py`(4,288)、`tiger_sboxes.py`(21,809)、`wire_tap.py`(12,408)。
- README 明确服务号：**10 storage / 11 rooms / 21 matchmaking / 80 marketplace / 4 stats / 102 chat**，以及 `dw_types.json`(349,034 B) 类型定义。
- `handoff\` 4 个模块（16 文件）：`map_handoff.py`(90 KB)、`startgame_map.py`(41 KB)、`match_instances.py`、`match_server_control.py` —— 通过 **RCON** 派发地图给原生服务端。
- `career\`(8 模块)、`store\`(SQLite)、`catalogue\`、`zones\`(读 `.ff`)、`notices\`、`ffwriter\`、`selftests\`。

### 3.4 客户端补丁（`patcher\`，CONFIRMED）

- `kernel33.c`（60,829 B）+ `c1_tables.h`（23,503 B）+ `gen_tables.py`（3,032 B）→ 编译出 `Kernel33.dll`。
- `kernel33.def`（105 B）、`build.sh`、`make_exe.py`、`kernel33_res.o`、`unpacked.z`。
- 用途：向早期客户端注入/劫持（仅静态观察；本轮未运行、未做绕过）。

## 4. 配置文件 / 启动脚本 / 数据表（CONFIRMED）

| 路径 | 说明 |
|---|---|
| `dedicated\bin\START-CODOL-SERVER.cmd` | 服务端启动脚本；默认 `CODOL_BOTS=12`、`CODOL_ADMISSION_REQUIRED=1`，设置 `codol_securityKeyPath`/`codol_admissionPath`/`codol_profilePath`、rcon_password，`+map` 加载地图（**未执行**） |
| 根 `START-*.cmd` / `STOP-ALL.cmd` | 全栈编排（**未执行**） |
| `dedicated\bin\home\main\q3config_server.cfg` | 服务端配置（1,465 B） |
| `dedicated\bin\home\main\missingasset.csv` | 缺失资源清单（8,908 B） |
| `dedicated\bin\home\codol_sessions.txt` | 会话持久化（167 B） |
| `lobby\startgame.txt` | 大厅→对局服的地图交接（202 B，含 `map=mp_killhouse_sh … fs_crc=0xAD1E1713`） |
| `lobby\game_admissions.txt` | 准入名册（203 B，`127.0.0.1 <key> <uid> <expires> -`） |
| `lobby\map_selection.state.json` | 选图状态（165 B） |
| `lobby\native_server_rcon.txt` | RCON 口令文件（15 B，**内容不在此报告**） |
| `lobby\resources\*.json/.info` | 玩法/进度/商店/解锁数据表（见 §6 资源索引） |
| `lobby\resources\lobby.sqlite` | SQLite 玩家库（237,568 B） |
| `lobby\players\*.json` | 两个玩家档案（13 KB/13 KB，**唯一副本**） |
| `codol_user.txt` / `codol_client.txt` / `codol_match.txt` | 顶层状态文件（账号/客户端/对局设置） |

## 5. 证书 / 密钥文件（存在性，CONFIRMED；**不输出秘密内容**）

| 路径 | 大小 | 用途类别 |
|---|---:|---|
| `lobby\securitykey.bin` | 16 B | 对局服 DTLS 密钥来源（README 明示） |
| `dedicated\bin\home\codol_sessions.txt` | 167 B | 会话/关联状态（含 hex 字段） |
| `lobby\game_admissions.txt` | 203 B | 准入密钥（hex） |
| `lobby\resources\lobby.sqlite*` | ~283 KB | 玩家库（含凭据派生数据） |

> 样本根目录**未观察到**独立 `.pem/.key/.crt` 证书文件（`cert-material` 类别 1 个位于打包环境内，非服务端证书）。现有 CODOL 工程内另有 `lobby_server.key/.pem`、`lobby_ca.key/.pem`，属现有工程，不在本样本范围。

## 6. 地图 / 脚本 / 武器 / 规则 / 模式资源（CONFIRMED）

| 路径 | 数量/大小 | 说明 |
|---|---|---|
| `dedicated\bin\home\codol_rawfiles\` | 1,341 文件 / 18.27 MB | **GSC 脚本树**；`AGENTS.md` 声明为唯一可编辑脚本树 |
| `dedicated\bin\home\main\sh1x_svr_scripts.iwd` | 4,277,656 B | 服务端脚本归档（`game-archive` 类别） |
| `dedicated\bin\home\main\mp\`、`waypoints\` | 目录 | 地图与路径点 |
| `lobby\resources\mp_playlists_shipRetail_cb2.info` | 31,611 B | 官方播放列表 |
| `lobby\resources\mpdata_layout.proposed.json` | 97,898 B | 玩家数据布局 |
| `lobby\resources\playerdata_defs.proposed.json` | 99,976 B | 玩家数据定义 |
| `lobby\resources\progression_tables.json` | 630,296 B | 进度表 |
| `lobby\codol_weapon_recipe.json` | 623,522 B | 武器配方 |
| `lobby\weapon_ammo_table.json` / `wpn_*.json` | 多份 | 武器弹药/弹道/开火模式/开镜时间表 |
| `lobby\resources\unlock_tables.proposed.json`、`unlock_flags.json` | 99,653 / 36,530 B | 解锁表 |
| `lobby\resources\map_spawns.proposed.json` | 5,575,280 B | 地图出生点 |

## 7. 调试符号 / 日志 / 崩溃转储 / 开发辅助（CONFIRMED）

| 路径 | 大小 | 说明 |
|---|---:|---|
| `dedicated\bin\codol_crash.txt` | 1,692 B | 崩溃记录：两次 "unexpected exit()"，帧 `codol_dedrun_next.exe+0x38c7`（2026-10-04） |
| `dedicated\bin\sys_error.txt` | 159 B | `Sys_Error: script compile error bad syntax bar.x = -barWidth / 2;` |
| `dedicated\bin\home\main\qconsole.log` | 218,428 B | 服务端控制台日志（尾部：map=mp_killhouse_sh，humans=0 bots=12） |
| `dedicated\bin\home\main\games_mp.log` | 7,861,923 B | 对局日志 |
| `dedicated\bin\home\main\enterleave.log` | 124,718 B | 进出日志 |
| `dedicated\bin\home\main\qconsole.old/prev/r2.log` | 多份 | 历史日志 |
| `lobby\map_selection.log` | 92,536 B | 选图日志 |
| `lobby\captures\` | 4 文件 / 5.49 MiB | 抓包/证据 |
| `dedicated\obj\` | 1,082 文件 / 7.38 MiB | 编译中间产物（`.o`，非源码） |
| `dedicated\dis\` | 10 文件 | 反汇编输出 |

> **未观察到** `.pdb` / `.map` 符号文件（在服务端目录内）。`dedicated\.git\` 存在但**无有效提交**（阶段 2 详述）。

## 8. 缺失/未观察到的依赖（NOT_OBSERVED）

以下为任务书关注但本样本**未观察到**的项（未观察 ≠ 不存在）：

| 关注项 | 状态 | 说明 |
|---|---|---|
| 独立登录服务进程 | NOT_OBSERVED | 登录/认证由 `lobby` 的 `dw_auth.py` 在 3074 端口实现，非独立进程 |
| 独立数据库服务 | NOT_OBSERVED | 使用内嵌 SQLite（`lobby.sqlite`），非独立 DB 服务 |
| `.pdb`/`.map` 调试符号 | NOT_OBSERVED | 见 §7 |
| 服务端专属地图 `.ff` 二进制 | NOT_OBSERVED（在服务端目录内） | 服务端用 `.iwd`/rawfiles；`.ff` 存在于客户端与 `lobby\zones` |
| 原生 bdDTLS 关联的**完整实现** | 部分 | 见阶段 2/3：有 codec 与状态机源码，但 `CODOL_PORT.md` 明确列为未完成 |

## 9. 交付物索引（阶段 1）

| 文件 | 内容 |
|---|---|
| `01_ASSET_MAP\EARLY_SERVER_01_ASSET_MAP.md` | 本报告 |
| `01_ASSET_MAP\EARLY_SERVER_01_BINARY_CATALOG.csv` | 12 个真实服务端 PE（含 SHA-256/导入/导出/角色） |
| `01_ASSET_MAP\EARLY_SERVER_01_PE_CATALOG.csv` | 全部 207 个 PE 的原始目录 |
| `01_ASSET_MAP\_pe_detail.json` | PE 详细（导入/导出/节区） |
| `01_ASSET_MAP\EARLY_SERVER_01_DEPENDENCY_GRAPH.md` | 依赖关系图 |
| `01_ASSET_MAP\EARLY_SERVER_01_RESOURCE_INDEX.md` | 资源/数据/配置索引 |

## 10. 证据等级

- §2–§7 全部为 **CONFIRMED**（PE 头/导入导出表/文件清单/源码可直接复算）。
- §8 为 **NOT_OBSERVED**，明确不等同于"不存在"。
- 唯一 **CANDIDATE** 级判断为"12 个 PE 之外的 195 个 PE 均与游戏服务端逻辑无关"——依据是其位于 `build\pyenv`/`build\pyinstaller`（Python 运行环境与打包引导），非按签名逐条排除。
