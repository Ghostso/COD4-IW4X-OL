# 02 目录与文件级差异 / DIRECTORY DIFF

本报告列出新旧及其对照样本的目录结构、体量、文件分布差异。**未解压、未修改任何样本。**

> 证据等级：**VERIFIED** / **STATIC-INFERENCE** / **NOT-OBSERVED** / **BLOCKED**。
> 方法论：只读取目录元数据与关键文本/清单文件；未对 `runtime-assets` 等大目录逐文件解析。

---

## 1. 三个样本根目录体量（VERIFIED）

| 标签 | 根路径 | 文件数 | 总字节 | 约 MB |
|---|---|---|---|---|
| NEW | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher` | 32,178 | 4,386,646,940 | 4,183.4 |
| OLD | `D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server` | 15,754 | 635,442,074 | 606.0 |
| 1113 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_1.1.1.13` | 8,925 | 7,796,330,725 | 7,435.2 |
| 2.6.9.7（镜像源） | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7` | 33,161 | 11,812,536,094 | 11,265.3 |

> 说明：旧版"约 7GB 服务端包"对应的是 `CODOL.NET\Game\CODOL_1.1.1.13`（7,435.2 MB）；而本次对比使用的 `CODOL-AlphaBuild` 服务端子目录为 606.0 MB（其核心 EXE 即任务书所指 OLD 哈希）。

---

## 2. 新样本目录结构（VERIFIED）

`D:\BaiduNetdiskDownload\CODOL_2697_Launcher\` 顶层：

```
manifest.json
settings.json
runtime\
  game\
    server2697\
      native\bin2697\codol_dedrun.exe      <- 服务端本体
      client_room2697.dll
      client_native_loopback.dll
      client_loopback_guard.exe
      lobby_runtime2697.py
      run_native_connection.py
      run_room_match2697.py
      connection_profile2697.py
      room_host2697.py
      frontend_bootstrap2697.py
      prepare_script_overlay2697.py
      round4_script_overlay2697.py
      weapon_*_cache2697.py
      diagnostic_*_fixture2697.gsc
      evidence\
        client-registration2697.txt
        loopback-executable-audit.json
        client-loopback-guard.json
        secure-profile-publication.json
      scripts\                 (1,341 文件)
      runtime-assets\          (11,033 文件)
      script-overlay2697\
      __pycache\
  python\                      (bundled CPython 3.12，仅启动器用)
```

`server2697` 子树体量（VERIFIED）：

| 子树 | 文件数 | 字节 |
|---|---|---|
| `server2697` 全部 | 12,511 | 1,826,646,484 |
| `native` | 1 | 7,295,919 |
| `scripts` | 1,341 | 19,154,634 |
| `runtime-assets` | 11,033 | 1,797,434,023 |

**STATIC-INFERENCE：** `server2697` 的体量主要由 `runtime-assets`（资源包，约 1.71 GB）与 `scripts` 构成，原生服务端逻辑仅 1 个 7.3 MB EXE。这符合"launcher + 原生 EXE + 脚本/资源"的封装形态，而非把服务端源码一并打包。

---

## 3. 旧样本目录结构（VERIFIED）

`D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\` 顶层：

```
_clone_backup_*\
_purge_backup_*\
build\
dedicated\
lobby\
local-stack-logs\
patcher\
resource\
tools\
START-*.cmd
STOP-ALL.cmd
Kernel33.dll
codol_client.txt / codol_match.txt / codol_user.txt
.disclaimer_accepted
```

`dedicated\bin\`（VERIFIED）：

| 文件 | 大小 | SHA-256 |
|---|---|---|
| `codol_dedrun.exe` | 8,469,493 | `28366ae9…` |
| `codol_dedrun_next.exe` | 8,469,493 | `28366ae9…`（与主 EXE 字节一致） |
| `codol_dedrun.def` | 4,457 B | 导出定义（185 个 `Plugin_*`） |
| `pexports.exe` | — | 导出工具 |
| `START-CODOL-SERVER.cmd` | — | 启动脚本 |
| `codol_crash.txt` / `sys_error.txt` | — | 运行痕迹 |
| `dummy` | — | 占位 |

**关键资产（VERIFIED）：** 旧包 `dedicated\src\` 含完整 C 源码，1,770 文件 / 25,603,769 B。该源码树是 IW4OL/CoD4x 分支（AGPL，含 Id/Ninja/TheKelm 版权），包含 `msg.c`、`sv_snapshot.c`、`sv_client.c`、`sv_main.c`、`sv_auth.c`、`netchan.c`、`codol_connect.c`、`codol_admission.c`、`codol_handshake*`、`codol_netconst*`、`codol_configstrings.c`、`codol_delta.c`、`codol_entities.c`、`codol_wire.{c,h}`、`codol_char*`、`codol_weapon_*` 等。

**对照（VERIFIED）：**
- `grep -r "2697"` 在旧源码树命中 **0 次** → 旧包 **不含任何 2697 源码**。
- `CODOL-AlphaBuild src` 与 `CODOL.NET\...\CODOL_1.1.1.13` 的 src 树 **除一个文件外完全相同**；唯一差异是 `g_sv_main.c`（C13 移除了 `player_sprintTime` 上的 `CVAR_CHEAT`，并加中文"无限冲刺"注释），属启动器侧玩法改动，**与 2697 无关**。

---

## 4. 文件级差异摘要（VERIFIED / STATIC-INFERENCE）

### 4.1 服务端 EXE 差异

| 项 | NEW vs OLD | NEW vs 1113 |
|---|---|---|
| 大小 | 7,295,919 vs 8,469,493（NEW 小 1.17 MB） | 7,295,919 vs 8,622,389 |
| SHA-256 | 完全不同 | 完全不同 |
| 节区 | 11 vs 20 | 11 vs 11（结构相同） |
| 链接器 | 2.47 vs 2.30 | 两者均 2.47 |

**STATIC-INFERENCE：** NEW 体积反而小于 OLD，主要因 NEW/1113 为较新工具链产出的 11 节区布局（无 OLD 的多个编号节 + `.CRT`），而非代码量减少。代码层面 NEW **新增**了 2697 层（见 03 报告）。

### 4.2 同名文件/镜像

- NEW 服务端 EXE 在 `CODOL.NET\Game\CODOL_2.6.9.7\...\bin2697\` 存在 **字节一致镜像**（VERIFIED）。
- `manifest.json` 的 `client_room2697.dll` / `client_native_loopback.dll` 哈希均与磁盘文件 **一致**（VERIFIED）。

### 4.3 目录级差异要点

| 维度 | NEW | OLD | 1113 |
|---|---|---|---|
| 是否附带完整 C 源码 | 否（BLOCKED：无 2697 源码） | 是（src\ 24.4 MB） | 是（同 OLD） |
| 是否含 PDB/MAP | 否 | 否 | 否 |
| 是否含版本资源（EXE） | 否 | 否 | 否 |
| 是否含 Python 启动器封装 | 是 | 是（lobby/tools/*.cmd，形态不同） | 是 |
| 2697 专属文件 | 大量（EXE 符号 + 脚本/审计） | 无 | 无 |

---

## 5. 差异结论

| 结论 | 等级 |
|---|---|
| NEW 为 launcher+原生 EXE+脚本/资源封装，服务端逻辑集中在 1 个 EXE | VERIFIED |
| NEW 附带 2697 命名的脚本、审计工件、注册导出，OLD/1113 均无 | VERIFIED |
| 旧包附带完整 C 源码，可作为 OLD 语义 ground truth，但**不含 2697 源码** | VERIFIED |
| 2697 服务端源码在本地不可得 → 2697 层只能用反汇编分析 | BLOCKED |
| NEW EXE 与 OLD/1113 非同一构建产物（大小/节区/导入/符号/字符串均不同） | VERIFIED |
| OLD 包在记录后未被改动（哈希仍与任务书一致） | VERIFIED |

未决问题：
- `runtime-assets` 内是否存在 2697 专属资源包/协议表（本阶段仅统计清单，未逐文件核验）→ 未解决问题。
- `scripts`（1,341 文件）是否含 2697 协议相关逻辑（GSC/脚本）→ 未解决问题。
