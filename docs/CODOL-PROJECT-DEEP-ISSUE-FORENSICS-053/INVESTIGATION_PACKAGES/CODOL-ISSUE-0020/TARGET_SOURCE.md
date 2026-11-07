# 需要检查的精确源码位置

| 文件 | 行 | 说明 |
|---|---|---|
| `CODOL_SERVER_319_20261021\src\battle\battle_service.c` | 1061-1140 | codol_battle_service_on_packet — 唯一的 UDP 入口，失败轮零日志的观测点 |
| `CODOL_SERVER_319_20261021\src\main.c` | 157-175 | 主循环：transport_poll → battle_service_on_packet |
| `CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py` | 1090-1150 | mmstart 分支：写 coop_map.txt / active_room.json |
| `CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py` | 789-849 | findSessions：用 coop_map.txt 决定回哪张图 |

> 行号以本任务读取的版本为准；引用前请先核对文件哈希（见 `../../EVIDENCE_INDEX.json`）。
