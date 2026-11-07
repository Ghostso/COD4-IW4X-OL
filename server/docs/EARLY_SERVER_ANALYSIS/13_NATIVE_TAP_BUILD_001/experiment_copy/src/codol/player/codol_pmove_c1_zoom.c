/* C1 variable-zoom scope step: the pmove glue around codol_variable_zoom.c.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 PM_Weapon 0x41dbf9 calls PM_UpdateVariableZoom 0x418480 between the ADS
 * lerp and PM_UpdateHoldBreath. The definition gate is the held weapon's
 * def+0x694 (overlayReticle, the same byte BG_CanHoldBreath and the melee check
 * read, resolved by codol_pmove_c1_breath.c); the zoom FOVs come from the
 * viewmodel weapon, ps+0x328 when weapFlags & 2 selects the offhand. */
#ifdef CODOL_SERVER
#include "codol_variable_zoom.h"
#include "codol_pmove_c1_zoom.h"
#include "codol_pmove_c1_breath.h"
#include "codol_weapon_native.h"
#include "codol_weapon_state.h"
#include "bg_public.h"
#include "player.h"
#include "qcommon.h"
#include "qcommon_io.h"
#include <string.h>

void __cdecl BG_AddPredictableEventToPlayerstate(int event, unsigned int eventParm,
                                                 playerState_t *ps);

static codol_variable_zoom_t *zoom_of(const playerState_t *ps)
{
    if(!ps || ps->clientNum < 0) return NULL;
    return CODOL_VariableZoomClient((unsigned)ps->clientNum);
}

void CODOL_PM_UpdateVariableZoomC1(codol_pmove_c1_t *move)
{
    playerState_t *ps;
    codol_variable_zoom_t *zoom;
    const struct WeaponDef *def;
    unsigned weapon;
    float fov[3] = {0.0f, 0.0f, 0.0f};
    int scoped;
    if(!move || !move->ps) return;
    ps = move->ps;
    zoom = zoom_of(ps);
    if(!zoom) return;
    /* C1 PM_Weapon 0x41db8e..0x41dbbe reaches the zoom call only below
     * PM_DEAD (8), without PMF_RESPAWNED (pm_flags 0x400) and off a turret
     * (eFlags 0xc00); the other arms return after the ADS lerp. */
    if(ps->pm_type >= 8 || (ps->pm_flags & 0x400) || (ps->eFlags & 0xc00)) return;
    scoped = CODOL_WeaponScopeOverlayC1((unsigned)ps->weapon);
    if(!scoped || !(ps->fWeaponPosFrac > 0.0f)) return;
    weapon = (ps->weapFlags & 2) ? (unsigned)ps->offHandIndex : (unsigned)ps->weapon;
    def = BG_GetWeaponDef((int)weapon);
    if(!def || !CODOL_GetNativeWeaponZoomFov(def, fov)) memset(fov, 0, sizeof fov);
    if(CODOL_VariableZoomStep(zoom, scoped, ps->fWeaponPosFrac, fov,
                              (int32_t)move->cmd.serverTime, move->cmd.buttons)) {
        BG_AddPredictableEventToPlayerstate(CODOL_EV_SCOPE_ZOOM, 0, ps);
        if(CODOL_TRACE_VERBOSE())
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL vzoom: c%d t%u weapon %u level %d fov %.3f/%.3f/%.3f posFrac %.3f\n",
                ps->clientNum, (unsigned)move->cmd.serverTime, (unsigned)ps->weapon,
                zoom->level, fov[0], fov[1], fov[2], ps->fWeaponPosFrac);
    }
}

void __cdecl CODOL_VariableZoomBeginWeaponChange(playerState_t *ps)
{
    codol_variable_zoom_t *zoom = zoom_of(ps);
    if(zoom) memset(zoom, 0, sizeof *zoom);
}
#endif
