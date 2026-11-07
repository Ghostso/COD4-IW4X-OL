/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_SCOREBOARD_SENDER_H
#define CODOL_SCOREBOARD_SENDER_H
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
/* Answer a client's scoreboard request with C1's layout.
 *
 * C1 asks with the one-letter command "s" (the IW3 "score", renamed): four
 * sites in the client run
 *     if (cg->scoresRequestTime + 2000 < cg->time) {
 *         cg->scoresRequestTime = cg->time;
 *         CL_AddReliableCommand("s");
 *     }
 * at 0x436f4a (scores-down key), 0x45fe42 and 0x4601fd (HUD refresh) and
 * 0x465a05 (CG_SetSingleClientScore, when the viewer is missing from the
 * board). The reply is command b: count clamped to 19 by the parser at
 * 0x465130, then team score 1, team score 2 and the score limit, then ten
 * integers per row into the 0x40-stride array at cg+0xBEB70. The retained IW3
 * SendScoreboard emits seven integers per row and cannot be used here. */
void CODOL_SendScoreboard(struct gentity_s *entity);
/* Clear the one-shot missing-profile warning when a slot is reused. */
void CODOL_ResetScoreboardSkillWarning(unsigned client);
/* Keep the client's cached scoreboard row - which is where C1's HUD reads the
 * player's own score, ping, kills and deaths from - in step with sess.score,
 * with C1's incremental "E <client> <score>" command. Without it the readout
 * only changes when the whole board arrives, i.e. while TAB is held. Called
 * once per server frame; sends nothing when no score moved. */
void CODOL_PublishPlayerScores(void);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
