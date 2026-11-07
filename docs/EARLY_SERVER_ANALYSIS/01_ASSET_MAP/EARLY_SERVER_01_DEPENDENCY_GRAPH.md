# EARLY_SERVER_01 — 服务端模块与依赖关系图

> 阶段 1 交付物。依赖边来自：PE 导入表、源码 `#include`/makefile、进程间契约文件（RCON/名册/startgame）、文档陈述。全部标注证据等级。

## 1. 运行时进程拓扑（CONFIRMED）

```
                    ┌───────────────────────────────┐
                    │  早期客户端 codoMP_client_      │
                    │  shipRetail.exe (1.1.1.13)     │
                    │  + Kernel33.dll (补丁)          │
                    └───────────────┬───────────────┘
                          UDP 3074  │             UDP 17733
                                    ▼                    ▼
        ┌───────────────────────────┐   ┌───────────────────────────────────┐
        │  lobby (Demonware 模拟器) │   │  dedicated 原生对局服               │
        │  dw-capture.py : 3074     │   │  codol_dedrun.exe : 17733          │
        │  auth/storage/rooms/      │   │  + 8 个进程内插件 DLL               │
        │  matchmaking/marketplace  │   │  + GSC rawfiles (1341 文件)        │
        └───────────┬───────────────┘   └───────────────┬───────────────────┘
                    │ RCON (loopback)                   │
                    └──── handoff/match_server_control.py ────┘
                        写 startgame.txt / game_admissions.txt
                        轮询 sh1x_status 状态行
```

**边证据**：

| 边 | 证据 | 等级 |
|---|---|---|
| 客户端 → lobby : 3074 | `lobby\README.md`（"runs `dw-capture.py` on port 3074"） | CONFIRMED |
| 客户端 → 对局服 : 17733 | `dedicated\src\codol\net\codol_wire.h` `#define CODOL_PORT 17733` | CONFIRMED |
| lobby → 对局服 RCON | `lobby\handoff\match_server_control.py`；`lobby\native_server_rcon.txt`；`codol_match_status.c` 的 `sh1x_status` | CONFIRMED |
| lobby → 对局服 名册 | `codol_admission.h` 注释；`lobby\game_admissions.txt` 存在 | CONFIRMED |
| lobby → 对局服 地图交接 | `lobby\startgame.txt`；`handoff\startgame_map.py` | CONFIRMED |

## 2. 对局服二进制依赖图（CONFIRMED，来自 PE 导入表）

```
codol_dedrun.exe
 ├── WS2_32.dll      (25 imports)   ← UDP/TCP 网络
 ├── KERNEL32.dll    (87)
 ├── msvcrt.dll      (142)
 ├── ADVAPI32.dll    (4)
 ├── CRYPT32.dll     (4)            ← 证书/加密 API
 ├── GDI32.dll       (5)
 ├── USER32.dll      (28)
 ├── SHELL32.dll     (1)
 └── WINMM.dll       (1)            ← 计时
导出：185 × Plugin_* （供插件 DLL 反向导入）

dedicated\plugins\*.dll (8 个)
 ├── KERNEL32.dll / msvcrt.dll
 └── codol_dedrun.exe   ← 反向依赖主程序导出
```

> **未观察到**主程序依赖 `mbedtls`/`tomcrypt`/`zlib` 作为**独立 DLL**：它们以源码/静态库形式编入（`dedicated\src\mbedtls\`、`tomcrypt\`、`zlib\`，`dedicated\lib\` 静态库 1.14 MiB）。因此运行时不需额外分发这些库。**CANDIDATE**（依据 makefile 的源码链接规则，未逐符号验证）。

## 3. 源码层依赖图（CONFIRMED，来自 `makefile` + include）

```
src/codol/  (9 区域, 591 文件)
   net/ ──────► snapshot/ (configstrings), player/, 引擎 sv_*.c, netchan.c, msg.c
   snapshot/ ─► net/, player/, 引擎 sv_snapshot.c
   player/ ───► 引擎 g_*.cpp, bg_*.cpp
   weapon/ ───► player/, script/
   vehicle/ ──► player/, snapshot/
   script/ ───► 引擎 cscr_*.cpp, scr_vm_*.c
   assets/ ───► filesystem.c, zlib/ (fastfile/zone/rawfile)
   collision/ ► 引擎 cm_*.cpp
   stats/ ────► net/, player/

引擎根 src/*.c|cpp ─► mbedtls/ (P-224), tomcrypt/, zlib/
makefile: CODOL_AREAS=net snapshot player weapon vehicle script assets collision stats
          CODOL_INC = -I src + -I 每个区域
```

- 依据：`dedicated\makefile` 第 88–94 行、第 162–168 行、第 305–314 行。
- `src\codol\net\codol_*.c` 之间：`codol_handshake.c` → `codol_association.h`、`codol_ecdh.h`；`codol_association.c` → `codol_crypto.h`、`codol_wire.h`；`codol_network.c` → `codol_admission.h` 等（include 证据）。

## 4. 大厅（Python）模块依赖图（CONFIRMED，来自 README + `__init__.py` 陈述）

```
dw-capture.py  (监听 3074, dispatch, _HostView)
   └── demonware/
        dw_wire.py  ← 底层：tagged-value codec + 3DES 帧（无下游依赖）
        ├── dw_auth.py          (认证)
        ├── dw_storage.py  (服务10) → store/ (SQLite + playerdata codec)
        ├── dw_rooms.py    (服务11)
        ├── dw_session.py  (会话)
        ├── dw_marketplace*.py (服务80) → catalogue/
        └── dw_admission.py / dw_game_admission.py → 写 game_admissions.txt
   career/ (rank/XP/challenges) → store/
   handoff/ (map_handoff, match_server_control, startgame_map) → RCON 对局服
   zones/ (读 .ff), notices/, ffwriter/, selftests/
```

- README："`demonware/dw_wire` is the bottom…Nothing below `demonware` imports anything in it"。
- README："What the two share is a contract, not code"：lobby 写 `resources/mpdata_s.<uid>` 和 `startgame.txt`，经 RCON 派发地图，并把 `resources/match_report.json` 折回档案。

## 5. 外部依赖 / 运行库需求（CONFIRMED / CANDIDATE）

| 依赖 | 状态 | 证据 |
|---|---|---|
| Win32 `WS2_32`/`KERNEL32`/`msvcrt`/`USER32`/`ADVAPI32`/`CRYPT32`/`GDI32`/`SHELL32`/`WINMM` | 需要 | `codol_dedrun.exe` 导入表 |
| Python 3.x 运行环境 | 需要（lobby/tools） | `build\pyenv\`（7,633 文件）为隔离环境；`tools\*.py` |
| SQLite | 需要（lobby） | `lobby.sqlite`；`store\` 模块 |
| `steam_api.dll` | **未观察到**（启动日志提及缺失但不阻断协议交换） | `docs\CODOL_ASSOCIATION.md` 记录启动日志报告 missing `steam_api.dll` |
| 第三方在线平台认证 | **不需要**（lobby 无认证，uid 由客户端在 wire 上给） | `lobby\README.md` 明示 |
| 外部数据库服务 | NOT_OBSERVED | 使用内嵌 SQLite |

## 6. 关键进程间契约文件（CONFIRMED）

| 文件 | 生产者 → 消费者 | 内容契约 |
|---|---|---|
| `game_admissions.txt` | lobby → 对局服 | `<ipv4> <key:32hex> <uid:16hex\|0> <expires> <gamertag>`（`codol_admission.h`） |
| `startgame.txt` | lobby → 对局服 | `map=… type=mp gametype=… session_map=… playlist=… fs_crc=0x…` |
| `native_server_rcon.txt` | 配置 → lobby | RCON 口令（不在此输出内容） |
| `securitykey.bin` | 配置 → 对局服 | 16 B DTLS 密钥源 |
| `resources/match_report.json` | 对局服 → lobby | 结算回写档案 |
| `codol_sessions.txt` | 对局服 ↔ 磁盘 | 会话/关联持久化 |
| `sh1x_status` (RCON 行) | 对局服 → lobby | `map=… running=… humans=… bots=… maxclients=… uids=…` |

## 7. 证据等级

- §1–§6 的边均可由文件存在 + 源码/PE 直接复算 → **CONFIRMED**。
- §2 末段"mbedtls/tomcrypt/zlib 静态编入"为 **CANDIDATE**（makefile 规则强支持，未逐符号验证）。
- 未观察到的依赖见 §5，标 **NOT_OBSERVED**。
