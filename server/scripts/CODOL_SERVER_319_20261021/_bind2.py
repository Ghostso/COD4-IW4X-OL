from pathlib import Path
p=Path('src/battle/battle_service.c')
s=p.read_text(encoding='utf-8')
s=s.replace('#include "codol_snapshot.h"\n', '#include "codol_snapshot.h"\n#include "codol_world.h"\n#include "codol_movement.h"\n#include "codol_entity.h"\n',1)
s=s.replace('''void codol_battle_service_init(codol_battle_service_t *svc, void *ctx,
                               codol_battle_sendto_fn send)
{''','''void codol_battle_service_bind_world(codol_battle_service_t *svc,
                                     codol_world_t *world, int client_num)
{
    if (!svc) return;
    svc->world = world;
    svc->world_client = client_num;
    if (world && client_num >= 0 && client_num < CODOL_MAX_CLIENTS) {
        if (codol_world_spawn_player(world, client_num) == CODOL_OK) {
            const codol_player_state_t *ps = codol_player_get(world, client_num);
            if (ps) {
                svc->player.x = ps->origin[0];
                svc->player.y = ps->origin[1];
                svc->player.z = ps->origin[2];
                svc->player.vx = ps->velocity[0];
                svc->player.vy = ps->velocity[1];
                svc->player.vz = ps->velocity[2];
            }
        }
    }
}

void codol_battle_service_init(codol_battle_service_t *svc, void *ctx,
                               codol_battle_sendto_fn send)
{''',1)
s=s.replace('''                            codol_player_move_in_world(&svc->player, cm, (float)elapsed * 0.001f,
                                                       NULL, -1);
                            svc->last_cmd = *cm;''','''                            if (svc->world && svc->world_client >= 0 &&
                                svc->world_client < CODOL_MAX_CLIENTS) {
                                codol_movement_process_usercmd(svc->world, svc->world_client, cm);
                                {
                                    const codol_player_state_t *ps =
                                        codol_player_get(svc->world, svc->world_client);
                                    if (ps) {
                                        svc->player.x = ps->origin[0];
                                        svc->player.y = ps->origin[1];
                                        svc->player.z = ps->origin[2];
                                        svc->player.vx = ps->velocity[0];
                                        svc->player.vy = ps->velocity[1];
                                        svc->player.vz = ps->velocity[2];
                                    }
                                }
                            } else {
                                codol_player_move_in_world(&svc->player, cm,
                                                           (float)elapsed * 0.001f,
                                                           NULL, -1);
                            }
                            svc->last_cmd = *cm;''',1)
p.write_text(s,encoding='utf-8',newline='\n')
print('service ok')
