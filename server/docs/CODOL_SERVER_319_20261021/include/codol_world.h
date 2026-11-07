#ifndef CODOL_WORLD_H
#define CODOL_WORLD_H

#include "codol_types.h"

#define CODOL_WORLD_STATE_LOADING  0
#define CODOL_WORLD_STATE_READY    1
#define CODOL_WORLD_STATE_RUNNING  2
#define CODOL_WORLD_STATE_PAUSED   3
#define CODOL_WORLD_STATE_SHUTDOWN 4

codol_result_t codol_world_init(codol_world_t *world, const char *map_name);
codol_result_t codol_world_load_assets(codol_world_t *world);
codol_result_t codol_world_step(codol_world_t *world, const codol_usercmd_t *commands,
                                 size_t command_count, codol_frame_t *frame);
codol_result_t codol_world_spawn_player(codol_world_t *world, int client_num);
/* 把地图实体表里的实体(道具 + actor)生成进世界; 返回生成条数。
 * 表来自 tools/gen_mapents_inc.py 生成的 include/codol_mapents_coop_train.inc。 */
int            codol_world_spawn_map_entities(codol_world_t *world);
void           codol_world_shutdown(codol_world_t *world);

#endif /* CODOL_WORLD_H */
