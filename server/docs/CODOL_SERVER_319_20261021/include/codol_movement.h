#ifndef CODOL_MOVEMENT_H
#define CODOL_MOVEMENT_H

#include "codol_types.h"

void codol_pmove_constants_init(codol_pmove_constants_t *constants);
codol_result_t codol_pmove_single(codol_pmove_t *pm);
codol_result_t codol_movement_process_usercmd(codol_world_t *world, int client_num,
                                               const codol_usercmd_t *cmd);
/* 同上, 但用**真实命令间隔** dt(秒) 积分。
 * ★ usercmd 的间隔实测是 112ms 甚至 12s, 固定 1/128 会让服务端位移偏小上千倍,
 *   每帧下发的坐标因此不可信(客户端被推着飘出地图)。战斗服应当用这个入口。 */
codol_result_t codol_movement_process_usercmd_dt(codol_world_t *world, int client_num,
                                                 const codol_usercmd_t *cmd,
                                                 float dt);
codol_trace_t codol_movement_trace(const codol_world_t *world,
                                    const float start[3], const float end[3],
                                    const float mins[3], const float maxs[3],
                                    int skip_entity, int content_mask);

#endif /* CODOL_MOVEMENT_H */
