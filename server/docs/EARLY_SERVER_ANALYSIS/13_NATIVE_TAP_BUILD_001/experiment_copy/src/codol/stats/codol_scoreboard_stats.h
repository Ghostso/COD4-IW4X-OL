/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCOREBOARD_STATS_H
#define CODOL_SCOREBOARD_STATS_H
#include <limits.h>
/* C1 ae0410 converts the float kill count to a signed integer by truncation.
 * Match the x86 invalid-conversion result without undefined C float casts. */
static inline int CODOL_ScoreInteger(float value)
{
    if (!(value >= -2147483648.0f && value < 2147483648.0f)) return INT_MIN;
    return (int)value;
}
#ifdef __cplusplus
extern "C" {
#endif
typedef enum {
    CODOL_SCORE_DOWNS, CODOL_SCORE_REVIVES, CODOL_SCORE_HEADSHOTS,
    CODOL_SCORE_OBJECTIVES, CODOL_SCORE_STAT_COUNT
} codol_score_stat_t;
int CODOL_GetScoreStat(unsigned client, unsigned stat);
void CODOL_SetScoreStat(unsigned client, unsigned stat, int value);
void CODOL_ResetScoreStats(unsigned client);
void CODOL_ResetAllScoreStats(void);
/* Read C1's skills/tdm column from the public session profile. Failure leaves
 * out unchanged; the sender owns C1's online/client-state gating. */
int CODOL_ReadScoreboardSkill(unsigned client, int *out);
#ifdef __cplusplus
}
#endif
#endif
