# 证据

| 文件 | 位置 | 说明 |
|---|---|---|
| `battle/battle_service.c` | 497-510 | 实体段填充（只取 number/type/x/y/z） |
| `entity/entity.c` | 18-33 | codol_entity_alloc，memset 使 model_index=0 |
| `battle/snapshot.c` | 497-499 | bw_write_entities 插入在 0x05 之前 |
| `battle/snapshot.c` | 247-300 | bw_write_entities 实现 |
