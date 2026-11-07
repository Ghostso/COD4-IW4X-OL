#include "codol_gamemode.h"
#include <string.h>

void codol_mode_init(codol_mode_t *mode, const codol_mode_config_t *config)
{
    if (!mode) return;
    memset(mode, 0, sizeof(*mode));
    if (config) mode->config = *config;
    if (mode->config.rounds <= 0) mode->config.rounds = 1;
    if (mode->config.round_limit <= 0) mode->config.round_limit = mode->config.rounds;
    if (mode->config.team_count <= 0) mode->config.team_count = 2;
    if (mode->config.respawn_delay_ms <= 0) mode->config.respawn_delay_ms = 3000;
    mode->state = CODOL_MODE_WARMUP;
    mode->round = 1;
}

codol_result_t codol_mode_join(codol_mode_t *mode, int client_num)
{
    if (!mode || client_num < 0 || client_num >= CODOL_MAX_CLIENTS)
        return CODOL_ERR_INVALID_ARG;
    mode->connected[client_num] = true;
    mode->respawn_at_ms[client_num] = 0;
    if (mode->state == CODOL_MODE_WARMUP) {
        mode->state = CODOL_MODE_ACTIVE;
        mode->elapsed_ms = 0;
        mode->round_elapsed_ms = 0;
    }
    return CODOL_OK;
}

codol_result_t codol_mode_disconnect(codol_mode_t *mode, int client_num)
{
    if (!mode || client_num < 0 || client_num >= CODOL_MAX_CLIENTS)
        return CODOL_ERR_INVALID_ARG;
    mode->connected[client_num] = false;
    mode->respawn_at_ms[client_num] = 0;
    return CODOL_OK;
}

codol_result_t codol_mode_tick(codol_mode_t *mode, int elapsed_ms)
{
    int i;
    if (!mode || elapsed_ms < 0) return CODOL_ERR_INVALID_ARG;
    if (mode->state != CODOL_MODE_ACTIVE && mode->state != CODOL_MODE_INTERMISSION)
        return CODOL_OK;
    mode->elapsed_ms += elapsed_ms;
    mode->round_elapsed_ms += elapsed_ms;
    for (i = 0; i < CODOL_MAX_CLIENTS; ++i) {
        if (mode->connected[i] && mode->respawn_at_ms[i] > 0 &&
            mode->elapsed_ms >= mode->respawn_at_ms[i])
            mode->respawn_at_ms[i] = 0;
    }
    if (mode->config.time_limit_ms > 0 && mode->round_elapsed_ms >= mode->config.time_limit_ms) {
        mode->state = CODOL_MODE_INTERMISSION;
        mode->round_elapsed_ms = 0;
    }
    return CODOL_OK;
}

codol_result_t codol_mode_player_killed(codol_mode_t *mode, int client_num, int killer_team, int victim_team)
{
    if (!mode || client_num < 0 || client_num >= CODOL_MAX_CLIENTS)
        return CODOL_ERR_INVALID_ARG;
    if (killer_team >= 0 && killer_team < 4 && killer_team != victim_team)
        mode->team_score[killer_team]++;
    mode->respawn_at_ms[client_num] = mode->elapsed_ms + mode->config.respawn_delay_ms;
    if (mode->config.score_limit > 0 && killer_team >= 0 && killer_team < 4 &&
        mode->team_score[killer_team] >= mode->config.score_limit)
        codol_mode_end_match(mode, killer_team);
    return CODOL_OK;
}

codol_result_t codol_mode_respawn_due(const codol_mode_t *mode, int client_num)
{
    if (!mode || client_num < 0 || client_num >= CODOL_MAX_CLIENTS)
        return CODOL_ERR_INVALID_ARG;
    if (!mode->connected[client_num]) return CODOL_ERR_STATE;
    return mode->respawn_at_ms[client_num] == 0 ? CODOL_OK : CODOL_ERR_STATE;
}

codol_result_t codol_mode_end_match(codol_mode_t *mode, int winner_team)
{
    if (!mode) return CODOL_ERR_INVALID_ARG;
    mode->state = CODOL_MODE_GAME_OVER;
    mode->winner_team = winner_team;
    return CODOL_OK;
}

bool codol_mode_is_match_over(const codol_mode_t *mode)
{
    return mode && mode->state == CODOL_MODE_GAME_OVER;
}
