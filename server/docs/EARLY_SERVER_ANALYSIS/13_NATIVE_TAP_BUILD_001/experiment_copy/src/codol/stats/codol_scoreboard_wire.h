/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCOREBOARD_WIRE_H
#define CODOL_SCOREBOARD_WIRE_H
#include <stddef.h>
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    int client, score, ping, deaths, status_icon;
    float kills;
    int assists, headshots, objectives, skill, downs, revives;
} codol_scoreboard_row_t;
/* Rows must already be sorted and have their skill/profile policy resolved.
 * Emits only complete rows within C1's command limits. Returns emitted row
 * count, or -1 without touching output for invalid input/insufficient capacity.
 * zm selects C1 command '4'; otherwise command 'b'. */
int CODOL_FormatScoreboard(char *out, size_t capacity, int zm,
    int team1, int team2, int scorelimit,
    const codol_scoreboard_row_t *rows, size_t count);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
