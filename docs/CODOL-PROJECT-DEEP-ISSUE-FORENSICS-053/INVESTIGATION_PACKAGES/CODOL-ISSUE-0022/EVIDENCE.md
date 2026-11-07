# 证据

| 文件 | 位置 | 说明 |
|---|---|---|
| `world_assets/world.c` | 55-96 | codol_world_init / codol_world_load_assets |
| `world_assets/world.c` | 66-67 | world->clipmap = codol_static_boxes; world->map_ents = 同 |
| `world/collision.c` | 25-29 | codol_static_boxes[] 来自 codol_clipmap_coop_train.inc |
| `main.c` | 64 | 默认 map_name="mp_firingrange"（--map 可覆盖，但无效果） |
