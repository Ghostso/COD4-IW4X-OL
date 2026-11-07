#ifndef CODOL_SCRIPT_LASTSTAND_H
#define CODOL_SCRIPT_LASTSTAND_H
#ifdef CODOL_SERVER

#include "scr_vm.h"

#ifdef __cplusplus
extern "C" {
#endif

struct gentity_s;

/* Grace period the last-stand entry gives the downed player, in milliseconds.
 * Both references use the same 500 ms: IW4 0x5de110 "mov ecx,[level.time];
 * add ecx,0x1f4" and the retained CoD4 entry in
 * _g_client_script_cmd_mp.asm:1540 "mov eax,[level+0x1ec]; add eax,0x1f4". */
#define CODOL_LASTSTAND_GRACE_MSEC 500

/* True while the player is downed, i.e. while gclient_s::lastStand is set.
 * This is the same state ClientEndFrame reads to hold C1 ps->pm_type at 7. */
qboolean CODOL_LastStand_IsActive(const struct gentity_s *ent);

/* True while the retained finishplayerdamage gate would drop incoming damage
 * outright, i.e. downed and still inside the grace window. */
qboolean CODOL_LastStand_InGracePeriod(const struct gentity_s *ent);

/* True when a lethal hit on this player would start last stand rather than
 * kill: not already downed and with effective C1 modPistolDeath enabled. This is the
 * entry condition the retained damage path evaluates, exposed for native
 * callers and for reasoning about the lifecycle; it does not change state. */
qboolean CODOL_LastStand_CanEnter(const struct gentity_s *ent);
qboolean CODOL_Martyrdom_IsEnabled(const struct gentity_s *ent);

/* Ends last stand for a player who is being put back on their feet without
 * respawning.  Clears the downed flag and the grace deadline, which releases
 * the ClientEndFrame pm_type override, re-enables normal damage handling and
 * re-arms the entry gate for the next lethal hit.  Safe on a player who is
 * not downed. */
void CODOL_LastStand_Revive(struct gentity_s *ent);

/* <player> laststandrevive() */
void CODOL_Scr_LastStandRevive(scr_entref_t ref);

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#endif
