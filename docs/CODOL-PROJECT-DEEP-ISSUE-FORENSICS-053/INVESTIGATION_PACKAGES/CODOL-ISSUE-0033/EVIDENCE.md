# 证据

| 文件 | 位置 | 说明 |
|---|---|---|
| `include/codol_battle_service.h` | — | svc 结构定义 |
| `battle/battle_service.c` | 421-591 | send_snapshot 只写 svc->player |
| `battle/battle.c` | 61 | codol_battle_find_or_alloc 有 per-peer assoc，但状态没放进去 |
