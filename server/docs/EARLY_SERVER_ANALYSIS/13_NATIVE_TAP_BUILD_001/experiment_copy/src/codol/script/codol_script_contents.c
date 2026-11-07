/* Native point-content query used by C1 equipment scripts.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "server.h"
#include "g_shared.h"
#include "entity.h"
#include "player.h"
#include <math.h>

void CODOL_Scr_MayApplyScreenEffect(scr_entref_t ref)
{
    int target;
    if (ref.classnum || ref.entnum >= MAX_GENTITIES ||
        !g_entities[ref.entnum].r.inuse || !g_entities[ref.entnum].client) {
        Scr_ObjectError("Must be called on a client");
        return;
    }
    if (Scr_GetNumParam()) {
        Scr_Error("Usage: player codol_mayApplyScreenEffect()");
        return;
    }
    /* Original T5 _utility::mayApplyScreenEffect excludes viewlockedentity.
     * OpenBLOPS ClientScr_GetEntityFromIndex treats WORLD/NONE as undefined.
     * Read the native field published to C1 ps+1b0; do not substitute a
     * script-only remote flag or T5's player-state offset/entity sentinels. */
    target = g_entities[ref.entnum].client->ps.viewlocked_entNum;
    Scr_AddBool(target == ENTITYNUM_NONE || target == ENTITYNUM_WORLD);
}

void CODOL_Scr_IsPointInWater(void)
{
    vec3_t point;
    unsigned axis;
    if (Scr_GetNumParam() != 1) {
        Scr_Error("Usage: codol_isPointInWater(position)");
        return;
    }
    Scr_GetVector(0, point);
    for (axis = 0; axis != 3; ++axis) {
        if (!isfinite(point[axis])) {
            Scr_ParamError(0, "water query position must be finite");
            return;
        }
    }
    /* Same CONTENTS_WATER mask/pass entity as G_ExplodeMissile. This includes
     * linked brush contents through SV_PointContents, not just world BSP. */
    Scr_AddBool((SV_PointContents(point, -1, 0x20) & 0x20) != 0);
}
#endif
