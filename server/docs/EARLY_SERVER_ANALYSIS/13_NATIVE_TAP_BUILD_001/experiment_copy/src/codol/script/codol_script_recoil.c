#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "codol_recoil_state.h"
#include "qcommon_io.h"

/* <player> player_recoilScaleOn( <scale> ) / <player> player_recoilScaleOff()
 *
 * IW4 methods 0x5dd2d0 and 0x5dd370 (table entries 0x73c934 / 0x73c940) and the
 * identical C1 handlers 0x00519750 / 0x00519850:
 *   - reject a non-entity self with "not an entity" and a non-player entity
 *     with "entity %i is not a player";
 *   - On reads one integer, rejects scale < 0 or scale > 100 with
 *     "Given scale must be between %i and %i.", then arms weapFlags bit 0x400
 *     and stores the percentage (C1 ps+0x3330, IW4 ps+0x3110);
 *   - Off takes no parameter and clears the bit only, leaving the stored
 *     percentage in place;
 *   - both return nothing.
 * The armed bit and the percentage are consumed by BG_WeaponFireRecoil on both
 * ends of the connection; see codol_recoil_state.h. */
static gentity_t *recoil_player(scr_entref_t ref)
{
    gentity_t *entity;
    if (ref.classnum) { Scr_ObjectError("not an entity"); return NULL; }
    if (ref.entnum >= MAX_CLIENTS || (int)ref.entnum >= level.maxclients) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return NULL;
    }
    entity = &g_entities[ref.entnum];
    if (!entity->client) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return NULL;
    }
    /* IW4 0x5dd2ee and C1 0x00519775 accept any player entity and write that
     * player's own playerState. Both halves of the state are stored on this
     * playerState's storage, so arming a spectator writes the spectator's own
     * state - which SpectatorClientEndFrame overwrites on its next follow copy,
     * exactly as in the reference - and never reaches the followed player. */
    return entity;
}

void CODOL_Scr_PlayerRecoilScaleOn(scr_entref_t ref)
{
    gentity_t *entity = recoil_player(ref);
    int scale;
    if (!entity) return;
    /* IW4 5dd322 reads argument zero directly; additional arguments are
     * ignored and a missing argument follows Scr_GetInt's normal error path. */
    scale = Scr_GetInt(0);
    if (scale < CODOL_RECOIL_SCALE_MIN || scale > CODOL_RECOIL_SCALE_MAX) {
        Scr_Error(va("Given scale must be between %i and %i.",
                             CODOL_RECOIL_SCALE_MIN, CODOL_RECOIL_SCALE_MAX));
        return;
    }
    /* Records the magnitude on this playerState's storage and arms the flag
     * together, the way C1 0x0051982f/0x00519839 writes both. */
    if (!CODOL_ArmPlayerRecoilScale(&entity->client->ps, scale)) {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum)); return;
    }
}

void CODOL_Scr_PlayerRecoilScaleOff(scr_entref_t ref)
{
    gentity_t *entity = recoil_player(ref);
    if (!entity) return;
    /* The reference does not inspect arguments to Off. It clears the bit and
     * keeps the magnitude; so does this. */
    CODOL_DisarmPlayerRecoilScale(&entity->client->ps);
}
#endif
