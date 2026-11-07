#ifndef CODOL_GAMEMODE_H
#define CODOL_GAMEMODE_H

#include "codol_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    CODOL_MODE_WARMUP = 0,
    CODOL_MODE_ACTIVE,
    CODOL_MODE_INTERMISSION,
    CODOL_MODE_GAME_OVER
} codol_mode_state_t;

typedef struct {
    char   map_name[64];
    char   gametype[32];
    int    score_limit;
    int    time_limit_ms;
    int    rounds;
    int    round_limit;
    int    team_count;
    int    respawn_delay_ms;
} codol_mode_config_t;

typedef struct {
    codol_mode_config_t config;
    codol_mode_state_t  state;
    int    round;
    int    team_score[4];
    int    elapsed_ms;
    int    round_elapsed_ms;
    int    winner_team;
    int    respawn_at_ms[CODOL_MAX_CLIENTS];
    bool   connected[CODOL_MAX_CLIENTS];
} codol_mode_t;

void codol_mode_init(codol_mode_t *mode, const codol_mode_config_t *config);
codol_result_t codol_mode_join(codol_mode_t *mode, int client_num);
codol_result_t codol_mode_disconnect(codol_mode_t *mode, int client_num);
codol_result_t codol_mode_tick(codol_mode_t *mode, int elapsed_ms);
codol_result_t codol_mode_player_killed(codol_mode_t *mode, int client_num, int killer_team, int victim_team);
codol_result_t codol_mode_respawn_due(const codol_mode_t *mode, int client_num);
codol_result_t codol_mode_end_match(codol_mode_t *mode, int winner_team);
bool codol_mode_is_match_over(const codol_mode_t *mode);

#ifdef __cplusplus
}
#endif
#endif /* CODOL_GAMEMODE_H */
