/* Per-player sprint duration/cooldown overrides.
 *
 * T5 stores both values inside its playerState sprint block: setsprintduration
 * writes ps+0x494 (CoDMPServer 60cc32) and setsprintcooldown writes ps+0x498
 * (60cd72), both in milliseconds. The retained IW3/CoDOL sprintState
 * (playerState_t +0x5b8) has only the five original members, so the overrides
 * live beside it here instead of widening the retained playerState ABI, which
 * the retained assembly and gclient stride depend on.
 *
 * CoDOL duration writes ability ID0 and BG_GetMaxSprintTime reads the captured
 * playerState ability through CODOL_SprintAbilityDurationSeconds. Its native
 * x87 calculation replaces the IW3 multiplier/clamp. PM_UpdateSprint /
 * PM_GetSprintLeft take the cooldown through CODOL_SprintRechargePauseMs.
 * The resulting sprintState is published to the CoDOL client by
 * CODOL_OverlayEngineSprint. */
#ifndef CODOL_SPRINT_STATE_H
#define CODOL_SPRINT_STATE_H
#include "player.h"
#include "codol_playerstate.h"
#ifdef __cplusplus
extern "C" {
#endif

/* T5 PlayerCmd_SetSprintDuration/SetSprintCooldown reject durations below zero
 * or at/above 16383 seconds (60cbee/60cd2e against the 16383.0f at 0xcb59fc),
 * then store second * 1000. BG_GetMaxSprintTime separately clamps the produced
 * sprint length to 16383 ms in T5. CoDOL uses its own native calculation;
 * its sprintStartMaxLength netfield carries sixteen bits. */
#define CODOL_SPRINT_SECONDS_LIMIT 16383

/* Milliseconds, clientNum-keyed. Rejects out-of-range clients and negative
 * durations; state is unchanged on failure. */
int CODOL_SetSprintDurationMs(int client, int milliseconds);
int CODOL_SetSprintCooldownMs(int client, int milliseconds);
/* Report an override for the playerState's own client; 0 when unset. */
int CODOL_SprintDurationOverrideMs(const playerState_t *ps, int *milliseconds);
int CODOL_SprintCooldownOverrideMs(const playerState_t *ps, int *milliseconds);
/* T5 clears both values with the playerState memset in G_ClientSpawn, so
 * scripts reapply them per spawn. Connect/disconnect and level restart clear
 * them as well. */
void CODOL_ResetSprintOverrides(unsigned client);
void CODOL_ResetAllSprintOverrides(void);

/* Retained-assembly producers.
 * CODOL_SprintBaseDurationMs replaces the player_sprintTime * 1000 base of
 * BG_GetMaxSprintTime (_bg_misc.asm); the weapon sprintDurationScale, perk
 * multiplier and 16383 ms clamp still follow it in the retained code.
 * CODOL_SprintRechargePauseMs replaces the player_sprintRechargePause * 1000
 * reads in PM_UpdateSprint and PM_GetSprintLeft (_bg_pmove.asm). */
float CODOL_SprintBaseDurationMs(const playerState_t *ps);
float CODOL_SprintAbilityDurationSeconds(const playerState_t *ps);
int CODOL_GetSprintLeft(const playerState_t *ps,int time,int maximum);
int CODOL_SprintButtonsBlocked(const playerState_t *ps,unsigned native_buttons,int continuing);
int CODOL_SprintRechargePauseMs(const playerState_t *ps);

/* Publish the retained sprintState through the measured C1 playerState fields
 * 0x238/0x23c/0x240/0x244/0x248, so the client's own sprint meter and sprint
 * prediction observe the server's duration. Atomic: invalid state leaves the
 * destination unchanged. */
int CODOL_OverlayEngineSprint(codol_player_fields_t *wire, const playerState_t *ps);

#ifdef __cplusplus
}
#endif
#endif
