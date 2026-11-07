# 证据

| 文件 | 位置 | 说明 |
|---|---|---|
| `main.c` | 157-175 | 主循环 |
| `world/gamemode.c` | 60-92 | player_killed/respawn_due/end_match |
| `world/projectile.c` | 22-165 | projectile_* |
| `replication/replication.c` | 11-78 | replication_build/ack |
| `world/combat.c` | 61 | result->killed = ... 之后没有任何 mode 调用（断层） |
| `world_assets/world.c` | 106 | codol_mode_tick(mode,16) 是唯一被调的模式函数 |
