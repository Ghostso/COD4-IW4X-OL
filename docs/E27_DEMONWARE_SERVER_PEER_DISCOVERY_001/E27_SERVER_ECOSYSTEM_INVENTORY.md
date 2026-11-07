# E27 服务端生态清单

## 1. 扫描方法与覆盖率

| 项 | 值 |
|---|---|
| 根目录 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697` |
| 文件总数 | **12,511** |
| 总字节 | 1,826,646,484（约 1742.0 MB） |
| 全量字节读取 | **12,511 / 12,511（100%）** —— 见下 |
| 跳过 | 0（无 >40MB 排除；最大单文件 89.1 MB 的 `.ff` 亦已读取） |
| 环境 | 只读；未修改任何文件 |

`.ff` / `.iwi` / `.mp3` 等二进制资源亦已**全量读入**做标记扫描（非仅扩展名过滤）。

## 2. 按扩展名分布（前 20）

| 扩展名 | 数量 |
|---|---|
| `.iwi` | 5424 |
| （无扩展名） | 4989 |
| `.gsc` | 1303 |
| `.mp3` | 485 |
| `.csv` | 102 |
| `.ff` | 97 |
| `.txt` | 25 |
| `.wav` | 24 |
| `.atr` | 18 |
| `.py` | 17 |
| `.shock` | 12 |
| `.json` | 6 |
| `.pyc` | 3 |
| `.exe` | 2 |
| `.dll` | 2 |
| `.lock` | 1 |
| `.script` | 1 |

## 3. 按顶层目录分布

| 目录 | 文件数 | 说明 |
|---|---:|---|
| `runtime-assets` | 11033 | 地图/素材（`.ff`/`.iwi`/`.mp3` 等） |
| `scripts` | 1341 | GSC 脚本 |
| `script-overlay2697` | 99 | 本地脚本覆盖 |
| `.`（根） | 29 | Python 启动器 + 4 个 PE 模块 |
| `evidence` | 5 | 本地证据 JSON/TXT |
| `__pycache__` | 3 | 字节码 |
| `native` | 1 | `bin2697\codol_dedrun.exe` |

## 4. PE 模块（全生态共 4 个）

| 路径 | 大小 | SHA-256 | 类型 |
|---|---:|---|---|
| `native\bin2697\codol_dedrun.exe` | 7,295,919 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | PE32 i386，iD-Tech 对局服务端（E-26 已析） |
| `client_loopback_guard.exe` | 242,176 | `2d9f99da2195af30823999ad07e5740007dcd771fb8118eaca32366a7652505c` | PE32 i386 |
| `client_room2697.dll` | 184,832 | `120c4cfdd79a9a38d992598c30af3c5cabe754e7b3d17614074b4b8026ffc3a7` | PE32 i386 |
| `client_native_loopback.dll` | 125,440 | `53c6fbe264defc06629fef06f43a1ddd82fda716439432c354b5eb2ee4074829` | PE32 i386 |

## 5. 非 PE 组件角色（按职责分组）

| 组 | 代表文件 | 职责 | 是否协议实现 |
|---|---|---|---|
| 本地启动/注入 | `run_native_connection.py`、`frontend_bootstrap2697.py`、`startup_dialog2697.py` | 离线启动、脚本注入 | 否 |
| 资源/图形 trap | `lobby_runtime2697.py`、`scene_probe2697.py`、`stage_access2697.py` | CreateFile/显卡 trap，非网络 | 否 |
| 本地档案 | `connection_profile2697.py`、`read_scene_loadout.py`（上级目录） | 本地对局 profile 读写 | 否 |
| 房间/匹配（本地） | `room_host2697.py`、`run_room_match2697.py`、`codol_bot_names2697.py` | 本地 bot/房间编排（Python 进程内，非线上协议） | 否（本地） |
| 诊断 fixture | `diagnostic_*_fixture2697.gsc`（6 个） | GSC 诊断 | 否 |
| 脚本覆盖 | `script-overlay2697\`、`prepare_script_overlay2697.py` | GSC 补丁 | 否 |
| 证据 | `evidence\*`（5） | 本地审计产物 | 否 |

## 6. `lobby_runtime2697.py` 澄清（名称易误读）

该文件虽名含 `lobby`，但实测内容是 **2.6.9.7 的显卡/缺失资源 trap 补丁**（`apply_video_setting`、`resource_name_hash`、`build_file_gate`），**不含**任何网络协议、socket、服务分发或 Demonware 帧处理。**不得**据此认为 2697 服务端含大厅协议实现。

## 7. 结论

2697 服务端生态是**"1 个 iD-Tech 对局服务端 + 3 个本地辅助 PE + GSC/资源/启动器"**，**不含** Demonware 控制面（大厅/认证）实现。全 12511 文件 100% 读取后，`CLIENTCHAL`/`BDDATA` 命中 0。
