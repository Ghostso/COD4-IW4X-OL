# 01 样本身份 / SAMPLE IDENTITY

生成时间（本地）：2026-10-11
分析类型：**纯静态**（未启动任何游戏或服务端，未编译、未打补丁）
分析目录：`D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\`

> 证据等级约定：**VERIFIED** = 有直接证据；**STATIC-INFERENCE** = 基于静态结构推断；**NOT-OBSERVED** = 未实际观测；**BLOCKED** = 缺工具/符号/文件无法完成。

---

## 0. 样本定位结论（VERIFIED）

新样本的外层目录 `D:\BaiduNetdiskDownload\CODOL_2697_Launcher` **不是**服务端本体，而是一个 **Python 启动器/工具封装（launcher harness）**。
真正的服务端可执行文件位于其内部：

```
D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe
```

在另一磁盘树中存在一份 **字节完全一致的镜像副本**（VERIFIED，SHA-256 相同）：

```
D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe
```

启动器清单 `manifest.json` 的版本字段为 **"2.6.9.7"**，与镜像路径中的 `CODOL_2.6.9.7` 一致（VERIFIED）。

---

## 1. 新服务端主样本（NEW）

| 项目 | 值 | 证据 |
|---|---|---|
| 文件名 | `codol_dedrun.exe` | VERIFIED |
| 完整路径 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | VERIFIED |
| 大小 | 7,295,919 字节 | VERIFIED |
| SHA-256 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | VERIFIED |
| 文件类型 | PE32 可执行（GUI 子系统） | VERIFIED |
| 文件系统时间 | 创建 2026-10-11T23:03:39（本地）；写入 2026-10-11T15:58:18（本地） | VERIFIED |
| PE Machine | `IMAGE_FILE_MACHINE_I386` (0x14c) | VERIFIED |
| PE Subsystem | `WINDOWS_GUI` (2) | VERIFIED |
| PE TimeDateStamp | 2026-10-09 17:11:43 UTC | VERIFIED |
| ImageBase | 0x00400000 | VERIFIED |
| EntryPoint (RVA) | 0x000014e0 | VERIFIED |
| SizeOfImage | 0x15cf0000 | VERIFIED |
| 链接器版本 | 2.47（GNU ld，MinGW/MSYS2 工具链） | VERIFIED |
| 编译器字符串 | `GCC: (Rev4, Built by MSYS2 project) 16.2.0` | VERIFIED |
| 节区数量 | 11 | VERIFIED |
| Imphash | `5298c76ec6910429495ead35879da26c` | VERIFIED |
| 版本资源 | **不存在**（无 VERSIONINFO：无 FileVersion/ProductVersion/OriginalFilename） | VERIFIED |
| PDB / MAP / 调试目录 | **不存在**（无 CodeView 调试目录条目） | VERIFIED |

### 1.1 新样本目录清单（关键项，VERIFIED）

服务端根目录 `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\`：

| 路径 | 说明 |
|---|---|
| `native\bin2697\codol_dedrun.exe` | 唯一原生服务端可执行文件（7,295,919 B） |
| `client_room2697.dll` | 184,832 B（注入/房间模块，与 manifest 哈希一致） |
| `client_native_loopback.dll` | 125,440 B |
| `client_loopback_guard.exe` | 242,176 B |
| `lobby_runtime2697.py` | 大厅运行封装 |
| `run_native_connection.py` | 连接脚本 |
| `run_room_match2697.py` | 房间对局脚本 |
| `connection_profile2697.py` | 连接档案 |
| `room_host2697.py` | 房间 Host |
| `frontend_bootstrap2697.py` | 前端引导 |
| `prepare_script_overlay2697.py` / `round4_script_overlay2697.py` | 脚本覆盖 |
| `weapon_*_cache2697.py` | 武器缓存工具 |
| `diagnostic_*_fixture2697.gsc` | 诊断 GSC fixture |
| `evidence\client-registration2697.txt` | 客户端注册导出（见 05 报告） |
| `evidence\loopback-executable-audit.json` | 可执行文件审计，`executable_sha256` = 80816711…（与 NEW 一致） |
| `scripts\` | 1,341 文件 / 19,154,634 B |
| `runtime-assets\` | 11,033 文件 / 1,797,434,023 B |
| `script-overlay2697\` | 脚本覆盖目录 |

目录总体量（VERIFIED）：

- `CODOL_2697_Launcher` 全部：32,178 文件 / 4,386,646,940 B（约 4,183.4 MB）
- `server2697`：12,511 文件 / 1,826,646,484 B（约 1,742.0 MB）
- `native`：1 文件 / 7,295,919 B

> 说明：本阶段对新样本 **未做任何解压/修改/移动**；`runtime-assets` 等大目录仅统计目录清单与体积，未逐文件解析（见 02 报告）。

---

## 2. 旧服务端样本（OLD）

| 项目 | 值 | 证据 |
|---|---|---|
| 完整路径 | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\bin\codol_dedrun.exe` | VERIFIED |
| 同目录 `codol_dedrun_next.exe` | 与主 EXE **字节一致** | VERIFIED |
| 大小 | 8,469,493 字节 | VERIFIED |
| SHA-256 | `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a` | VERIFIED（**与任务书记录一致**） |
| PE TimeDateStamp | 2026-10-04 09:03:01 UTC | VERIFIED |
| 链接器版本 | 2.30（GNU ld） | VERIFIED |
| 节区数量 | 20（含 `.CRT` 及多个编号节） | VERIFIED |
| Imphash | `506faee6444b112462fb1301d26bca17` | VERIFIED |
| 版本资源 / PDB / MAP | 均不存在 | VERIFIED |

任务书给出的旧版 SHA-256 与当前磁盘文件 **逐字节一致**，说明该旧样本在记录之后 **未被改动**（VERIFIED）。

旧包另外 **附带完整 C 源码**（重要资产，见 03/04 报告）：

```
D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\
```
1,770 文件 / 25,603,769 B（约 24.4 MB）。源码中 `grep 2697` **命中 0 次**（VERIFIED），即 **不含 2697 源码**。

---

## 3. 参考样本：1.1.1.13 服务端（1113）

| 项目 | 值 | 证据 |
|---|---|---|
| 完整路径 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin\codol_dedrun.exe` | VERIFIED |
| 同目录 `codol_dedrun_next.exe` | 与主 EXE 字节一致 | VERIFIED |
| 大小 | 8,622,389 字节 | VERIFIED |
| SHA-256 | `a96c5dfb5386f166a0e1d4262b8fdecf9835b856cf1a863f891ead4eda5cb6e9` | VERIFIED |
| PE TimeDateStamp | 2026-10-10 16:38:12 UTC | VERIFIED |
| 链接器版本 | 2.47 | VERIFIED |
| 节区数量 | 11（同样含 `.eh_fram`） | VERIFIED |
| Imphash | `d5a1b1cde88e9254617905bdd9068eb1` | VERIFIED |

用途：作为"同为 GCC 16.2.0 / 2.47 工具链"的对照样本，用于排除"仅工具链变化"造成的字符串/导入差异。

---

## 4. 三样本二进制元数据对照（VERIFIED）

| 维度 | NEW (2697) | OLD (28366ae9) | 1113 (a96c5dfb) |
|---|---|---|---|
| 大小 | 7,295,919 | 8,469,493 | 8,622,389 |
| SHA-256 前缀 | 80816711 | 28366ae9 | a96c5dfb |
| PE 时间戳（UTC） | 2026-10-09 17:11:43 | 2026-10-04 09:03:01 | 2026-10-10 16:38:12 |
| 链接器 | 2.47 | 2.30 | 2.47 |
| 编译器 | MSYS2 GCC 16.2.0 | GCC (ld 2.30) | MSYS2 GCC 16.2.0 |
| 节区数 | 11 | 20 | 11 |
| `.bss` 虚拟大小 | 0x157f26c8 | 0x139f9600 | 0x139f98fc |
| EntryPoint | 0x14e0 | 0x1480 | 0x14e0 |
| SizeOfImage | 0x15cf0000 | 0x13f6d000 | 0x13f6c000 |
| 导出（Plugin_*） | 185 | 185 | 185 |
| 导入函数总数 | 291 | 297 | 305 |
| 符号（去重） | 36,980 | 46,160 | 46,707 |
| 字符串条数 | 62,147 | 72,859 | 71,857 |
| Imphash | 5298c76e… | 506faee6… | d5a1b1cd… |

**注意（VERIFIED）：** NEW 的 PE 时间戳（2026-10-09）晚于 OLD（2026-10-04），但本任务 **不以文件系统时间或 PE 时间戳判定版本新旧**；版本判定以实际代码/符号/字符串差异为准（见 03 报告）。

---

## 5. 关联客户端（VERIFIED）

启动器 manifest 记录 `original_exe_sha256`：

```
353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1
```

该哈希与磁盘客户端 **完全一致**：

| 项目 | 值 |
|---|---|
| 客户端路径 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` |
| 大小 | 9,964,656 字节 |
| SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` |

即 NEW 服务端与 `manifest.json` 所声明的 **2.6.9.7 客户端版本一一对应**（VERIFIED）。注意：这仅证明"客户端文件身份与清单声明一致"，**不证明** 服务端与客户端已实际互通（互通 = NOT-OBSERVED，见 05 报告）。

---

## 6. 阶段 A 初步判断

| 结论 | 等级 |
|---|---|
| 新样本真实服务端为 `...\server2697\native\bin2697\codol_dedrun.exe` | VERIFIED |
| 外层 `CODOL_2697_Launcher` 是 Python 封装而非服务端本体 | VERIFIED |
| NEW 与 OLD 是不同构建（大小/时间戳/节区/导入/符号/字符串均不同） | VERIFIED |
| NEW 与 1113 共享较新工具链（GCC 16.2.0 / ld 2.47、11 节区、`.eh_fram`） | VERIFIED |
| NEW 含一批 OLD 与 1113 都 **不存在** 的 `2697` 命名符号（99 个） | VERIFIED（详见 03 报告） |
| NEW 与 2.6.9.7 客户端版本对应 | VERIFIED |
| NEW 与客户端实际互通 | NOT-OBSERVED |
| NEW 的 PE 时间戳落后于文件系统时间是否意味着"重新打包" | 需结合代码差异判断，不在本报告单独定性 |

初步判断（STATIC-INFERENCE）：**NEW 不是 OLD 的简单重新打包，而是引入了独立 `codol_2697_*` 协议/适配层的新构建**，倾向确认为更新版本。完整证据见 03、04 报告。
