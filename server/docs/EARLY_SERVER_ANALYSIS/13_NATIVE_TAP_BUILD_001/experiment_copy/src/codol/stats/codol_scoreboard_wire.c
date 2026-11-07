/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_scoreboard_wire.h"
#include "codol_scoreboard_stats.h"
#include <stdio.h>
#include <string.h>

int CODOL_FormatScoreboard(char *out, size_t capacity, int zm,
    int team1, int team2, int scorelimit,
    const codol_scoreboard_row_t *rows, size_t count)
{
    char body[0x578], row[0x598], command[0x598];
    size_t used = 0, emitted = 0;
    size_t row_end[65] = {0};
    int length;
    if (!out || (count && !rows)) return -1;
    body[0] = '\0';
    /* C1's parser clamps its own row count to 0x13 (0x46518d) and its row
     * array is 19 * 0x40 bytes (the memset at 0x46524f), so anything past the
     * nineteenth row is parsed into nothing. Stop at the same place. */
    if (count > 19) count = 19;
    while (emitted < count) {
        const codol_scoreboard_row_t *r = rows + emitted;
        int kills = CODOL_ScoreInteger(r->kills);
        if (zm)
            length = snprintf(row, sizeof(row), " %i %i %i %i %i %i %i",
                r->client, r->score, kills, r->downs, r->revives,
                r->headshots, r->ping);
        else
            length = snprintf(row, sizeof(row), " %i %i %i %i %i %i %i %i %i %i",
                r->client, r->score, r->ping, r->deaths, r->status_icon,
                kills, r->assists, r->headshots, r->objectives, r->skill);
        if (length < 0 || (size_t)length >= sizeof(row)) return -1;
        /* Keep the terminating byte as well as the complete final integer.
         * C1 producer51fc16 has a 0x578 body budget. Never truncate a token. */
        if ((size_t)length >= sizeof(body) - used) break;
        memcpy(body + used, row, (size_t)length + 1);
        used += (size_t)length;
        ++emitted;
        row_end[emitted] = used;
    }
format_header:
    if (zm)
        length = snprintf(command, sizeof(command), "4 %i%s", (int)emitted, body);
    else
        length = snprintf(command, sizeof(command), "b %i %i %i %i%s",
            (int)emitted, team1, team2, scorelimit, body);
    if (length < 0) return -1;
    if ((size_t)length >= sizeof(command) || (size_t)length >= capacity) {
        if (!emitted) return -1;
        body[row_end[--emitted]] = '\0';
        goto format_header;
    }
    memcpy(out, command, (size_t)length + 1);
    return (int)emitted;
}
