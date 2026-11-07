#ifndef CODOL_SCRIPT_TURRET_PLACEMENT_H
#define CODOL_SCRIPT_TURRET_PLACEMENT_H
#ifdef CODOL_SERVER

#include "scr_vm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* canspawnturret(): global GSC function (no receiver, no arguments).
 * iw4x.exe (base 0x400000) builtin table entry at 0x79a1f4 names 0x5ee590 as
 * "canspawnturret"; 0x5ee590 takes no VM arguments (no Scr_GetNumParam /
 * Scr_GetInt / Scr_GetString in its body) and returns the bool from
 * 0x4e6f00, which scans a fixed 32-slot pool (0x1aa3000..0x1aa4880, stride
 * 0xc4) for a slot whose first field is zero. That is the same "is there a
 * free slot" predicate the retained G_SpawnTurret loop already runs over
 * this fork's own turretInfo[CODOL_MAX_TURRETS] pool (turretInfo_s::inuse,
 * g_shared.h) before it allocates a slot or raises "max number of turrets
 * (%d) exceeded" (src/asmsource/_g_misc_mp.asm). Neither C1.exe 1.1.1.13 nor
 * T5's CoDMPServer.exe contain a "canspawnturret" string, so IW4 is the only
 * reference implementation for this builtin; there is no C1/T5 semantics to
 * reconcile it against, and no geometry/collision/trace call appears
 * anywhere in the IW4 call chain for it. */
void CODOL_Scr_CanSpawnTurret(void);

#ifdef __cplusplus
}
#endif

#endif
#endif
