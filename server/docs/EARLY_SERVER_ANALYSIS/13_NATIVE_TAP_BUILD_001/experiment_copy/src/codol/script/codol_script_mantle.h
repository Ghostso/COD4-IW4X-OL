#ifndef __CODOL_SCRIPT_MANTLE_H__
#define __CODOL_SCRIPT_MANTLE_H__
#ifdef CODOL_SERVER

#include "q_shared.h"
#include "entity.h"
#include "bg_public.h"
#include "scr_vm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ps->mantleState.flags bits, as used by the retained bg_mantle code.
 *
 * 0x01 mantle-over (the ledge is thin enough to vault across, set from the
 *      MANTLE_OVER surface flag in Mantle_Check); selects s_mantleTrans[i].over
 * 0x02 consumed once by Mantle_Move on the first mantle frame
 * 0x04 checked by Mantle_Move when the mantle finishes
 * 0x08 mantle hint: recomputed every Pmove by Mantle_ClearHint/Mantle_CheckLedge
 * 0x10 cleared by Mantle_Check on entry
 * 0x20 CoDOL force request, written by forcemantle().  IW4 uses the same bit:
 *      0x56e703 "test byte [ps+0x1e4], 0x20" starts the mantle without the
 *      jump button, and 0x56e14c masks it back out when mantleState.flags is
 *      assigned from the completed check.  Server-side only: the IW4OL/C1
 *      playerState delta writes mantleState.flags with 5 bits.
 */
#define MANTLE_FLAG_OVER   0x01
#define MANTLE_FLAG_BEGIN  0x02
#define MANTLE_FLAG_END    0x04
#define MANTLE_FLAG_HINT   0x08
#define MANTLE_FLAG_CLEAR  0x10
#define MANTLE_FLAG_FORCE  0x20

/* The 0x38 byte scratch record Mantle_Check zeroes and hands to
 * Mantle_CheckLedge.  Same layout in IW4 (0x4773ad memsets 0x38 too). */
typedef struct mantleCheck_s
{
	vec3_t surfaceDir;   /* 0x00 normalized horizontal direction into the ledge */
	vec3_t playerOrigin; /* 0x0c ps->origin when the check ran */
	vec3_t ledgePos;     /* 0x18 top of the ledge */
	vec3_t endPos;       /* 0x24 where the mantle animation puts the player */
	int flags;           /* 0x30 MANTLE_FLAG_* accumulated by the check */
	int unused;          /* 0x34 */
} mantleCheck_t;

/* src/asmsource/_bg_mantle.asm */
void __cdecl Mantle_Check(struct pmove_t *pm, const float *forward);
void __cdecl Mantle_ClearHint(playerState_t *ps);

/* Runs the ledge search for a player without touching their movement state.
 * Returns qtrue when a mantle would be available this frame. */
qboolean CODOL_Mantle_CanMantle(gentity_t *ent);

void CODOL_Scr_CanMantle(scr_entref_t ref);
void CODOL_Scr_ForceMantle(scr_entref_t ref);

#ifdef __cplusplus
}
#endif

#endif /* CODOL_SERVER */
#endif
