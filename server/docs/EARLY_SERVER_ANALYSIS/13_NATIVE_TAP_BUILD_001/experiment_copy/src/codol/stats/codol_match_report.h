#ifndef CODOL_MATCH_REPORT_H
#define CODOL_MATCH_REPORT_H
#include <stdint.h>
/* The match result this server reports back to the CoDOL lobby.
 *
 * The lobby (alpha0022 dw-capture.py) owns progression: players/<uid>.json and
 * resources/lobby.sqlite are the rank/XP authority, and the blob the client
 * actually reads, mpdata_s.<uid>, is RE-RENDERED from that profile every time
 * the client fetches it. The one channel between the two processes is a file in
 * the lobby's resources directory: the match server drops
 * resources/match_report.json, and rank_writeback.maybe_apply() consumes it on
 * the next storage GETFILE, folding each row's XP into that row's profile.
 * The server never writes mpdata_s itself - two writers on one blob is exactly
 * the lost-update race the lobby's own journal recorded.
 *
 * Format 1, the schema rank_writeback._validate() accepts, plus a per-row
 * "uid": the retired Python game server only ever had one human, so its reader
 * credited every row to the connection that happened to ask for storage. Each
 * row now names its own account.
 *
 * XP is not invented here. _rank.gsc runs the ordinary IW4 progression flow and
 * commits through setRankExperience, which normalises (rank, experience,
 * rankVersion) into the client's session secure profile. So the XP a player
 * earned this match is exactly
 *     CODOL_ProfileExperience(session blob) - the same value at attach time,
 * and both halves are read through the recovered C1 conversion rather than
 * accumulated separately.
 *
 * Every report resets its own baselines, so consecutive reports partition the
 * match's XP instead of repeating it. Rows carry applied_live 0: unlike the
 * Python server this one runs no live save pump, so nothing has been persisted
 * behind the lobby's back. */

/* A client's secure profile has just been attached. Captures the baseline XP
 * and adopts any row the same uid left behind earlier in this match, so a
 * reconnect neither loses nor repeats its earnings. */
void CODOL_MatchReportClientAttached(unsigned client, uint64_t uid);
/* A client is leaving. Freezes its row (counters and earned XP) so the next
 * report still carries it after the slot is reused or cleared. */
void CODOL_MatchReportClientDropped(unsigned client);
/* Write this match's report into resources/: by default a spool file of its
 * own, match_report.q.<epoch>.<port>.<seq>.json, which the lobby folds oldest
 * first (a rotation writes several before anyone returns to the lobby);
 * codol_matchReportSpool 0 writes the legacy single match_report.json.
 * reason is the free-text cause the lobby echoes back in its journal
 * ("gameended", "disconnect", "mapchange", ...).
 * Returns 1 written, 0 nothing worth reporting (no human row with either XP or
 * activity, or codol_profilePath is unset), -1 the write failed. */
int CODOL_WriteMatchReport(const char *reason);
/* Whether any human client is still connected. Used by the disconnect path to
 * decide whether the match is over. */
int CODOL_MatchReportHumansConnected(void);
/* Credit `amount` weapon XP to the base weapon of `weapon` (a plain or
 * composed name) on this client's row; the next report carries it as
 * progression.weapons. 1 recorded, 0 no account row / nothing to credit. */
int CODOL_MatchReportCreditWeaponXP(unsigned client, const char *weapon, int amount);
/* Map change / server shutdown: report anything still outstanding, then drop
 * every row. Safe to call when no match ran. */
void CODOL_ResetMatchReport(void);
/* Install the server match-record delivery sink so sendMatchData's prepared
 * record reaches the lobby's resources directory instead of being retained
 * with nowhere to go. Called once at startup. */
void CODOL_InstallMatchDataSink(void);
#endif
