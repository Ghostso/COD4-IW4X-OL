# 证据

| 文件 | 位置 | 说明 |
|---|---|---|
| `movement/movement.c` | 71-87 | codol_pmove_single（含 jump） |
| `movement/movement.c` | 102-141 | codol_movement_process_usercmd_dt（不调 pmove_single） |
| `battle/battle_service.c` | 126-143 | apply_usercmd → process_usercmd_dt |
| `world/player.c` | — | codol_player_move_in_world 实际移动实现 |
