/* canspawnturret: see src/codol_script_turret_placement.h for the verified
 * IW4 contract (iw4x.exe 0x5ee590 / 0x4e6f00). This mirrors that free-slot
 * scan against this fork's own server-authoritative turret pool,
 * so the answer reflects the same pool G_SpawnTurret
 * (src/asmsource/_g_misc_mp.asm) actually allocates from. */
#ifdef CODOL_SERVER

#include "codol_script_turret_placement.h"
#include "scr_vm_functions.h"
#include "g_shared.h"
#include "codol_script_turret_target.h"

/* Pool lives in src/asmsource/_g_misc_mp.asm (turretInfo: resb
 * 0x20*TURRET_INFO_SIZE); declared extern the same way
 * src/codol_script_turret_target.cpp already does. */
extern turretInfo_s turretInfo[CODOL_MAX_TURRETS];

void CODOL_Scr_CanSpawnTurret(void)
{
    int i;

    for (i = 0; i < CODOL_MAX_TURRETS; i++) {
        if (!turretInfo[i].inuse) {
            Scr_AddBool(qtrue);
            return;
        }
    }
    Scr_AddBool(qfalse);
}

#endif
