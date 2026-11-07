#ifdef CODOL_SERVER
/* laststandrevive - ends a player's last stand without respawning them.
 *
 * IW4 (D:\CoD\shx\iw4x.exe) builtin record 0x73cb48, handler 0x5df3b0,
 * disassembled aligned:
 *
 *     5df3b6 shr ecx,0x10 / jne          ; classnum != 0 -> "not an entity"
 *                                          (string 0x72c7f0)
 *     5df3c1 imul esi,esi,0x274          ; g_entities stride, base 0x18835d8
 *     5df3cd cmp [esi+0x158],0 / jne     ; ent->client required, else
 *                                          "entity %i is not a player"
 *                                          (string 0x72d454)
 *     5df3fb call 0x43a070               ; not gameplay: reads globals
 *                                          0x6fc42c/0x713d54/0x73415c, calls
 *                                          0x689200 and compares the result to
 *                                          [0x7135a0] - an integrity check that
 *                                          returns a bool nobody here reads
 *     5df406 mov [client+0x3648],0
 *     5df416 mov [client+0x364c],0
 *     5df421 ret                         ; nothing pushed -> undefined return
 *
 * The two cleared ints are IW4's whole last-stand state.  A sweep of IW4's
 * .text for aligned accesses to those two displacements finds exactly three
 * sites, and each has a direct IW4OL counterpart in this tree's retained
 * assembly, at IW4OL's own gclient offsets 0x317c/0x3180:
 *
 *   entry, IW4 finishplayerdamage 0x5de0cc..0x5de144:
 *       cmp [ent+0x19c],0 / jg           ; lethal hit only
 *       cmp [client+0x3648],0 / jne      ; not already downed
 *       0x4c0f60(&client[0x428], 7)      ; BG_HasPerk(ps->perks, 7)
 *       mov [client+0x3648],1
 *       mov [client+0x364c], level.time + 0x1f4
 *       call 0x4b1fa0 (9 args)           ; CodeCallback_PlayerLastStand
 *     IW4OL: _g_client_script_cmd_mp.asm:1533..1560, same shape, with
 *     "test byte [client+0x5fc],0x80" for the perk (ps->perks is player.h
 *     offset 1532 and BG_GetPerkIndexForName returns 7 for
 *     "specialty_pistoldeath", src/bg_perks_mp.cpp:21) and a call to
 *     Scr_PlayerLastStand (src/g_scr_main_mp.cpp:382).
 *
 *   damage gate, IW4 finishplayerdamage entry 0x5ddb9a:
 *       cmp [client+0x3648],edi / je     ; downed?
 *       mov edx,[client+0x364c] / cmp edx,[level.time] / jg <return>
 *     IW4OL: _g_client_script_cmd_mp.asm:1101..1108, identical - while the
 *     grace deadline is still in the future the damage call returns without
 *     touching health, so the downed player cannot be finished instantly by
 *     the same burst that put them down.
 *
 *   movement mode, IW4 ClientEndFrame 0x5d7f97..0x5d7ffe:
 *       cmp [client+0x311c],1 ...        ; session state ladder
 *       cmp [client+0x3648],edi / jne -> ps.pm_type = 7
 *     IW4OL: _g_active_mp.asm:907..917 (ClientEndFrame_210) picks
 *       0x307c -> pm_type 2/3, sess 0x2f64==1 -> 7/8 (dead),
 *       client->lastStand -> C1 pm_type 7, otherwise 0/1.
 *     The retained producer now stores C1's value directly; the snapshot
 *     publisher copies mode 7 without semantic translation.
 *
 * So the producer and both consumers already exist natively here; what was
 * missing is the only thing that ever clears the state.  ClientSpawn's
 * "memset(client, 0, sizeof(gclient_s))" (src/g_client_mp.cpp:108) covers the
 * respawn path, so the uncovered case is precisely the one this method names:
 * a downed player who is put back on their feet in place.  Without it such a
 * player keeps ps->pm_type 7 forever, keeps the entry gate latched shut so a
 * later lethal hit kills them outright instead of downing them again, and
 * keeps a stale grace deadline in gclient.
 *
 * alpha0022's Python surface agrees on the direction it moves the player:
 * gsc/builtin_surface.py:792 registers laststandrevive as a revive that marks
 * the player alive and drops its 'laststand'/'fauxdead' bookkeeping.  It is a
 * lead only; the state written here is the native state above.
 *
 * T5 was not needed: IW4 provides the function.
 */
#include "scr_vm_functions.h"
#include "codol_script_laststand.h"
#include "entity.h"
#include "player.h"
#include "codol_playerstate_ext.h"
#include <stddef.h>

/* The consumers of these two fields are retained assembly that addresses them
 * by displacement, so the C declarations have to land exactly there. */
_Static_assert(offsetof(gclient_t, lastStand) == 0x317c,
               "lastStand must match the retained ClientEndFrame/damage offset");
_Static_assert(offsetof(gclient_t, lastStandTime) == 0x3180,
               "lastStandTime must match the retained grace-window offset");

qboolean CODOL_LastStand_IsActive(const gentity_t *ent)
{
    if(!ent || !ent->client) return qfalse;
    return ent->client->lastStand ? qtrue : qfalse;
}

qboolean CODOL_LastStand_InGracePeriod(const gentity_t *ent)
{
    if(!CODOL_LastStand_IsActive(ent)) return qfalse;
    /* Same comparison as the retained gate: strictly greater than level.time. */
    return ent->client->lastStandTime > level.time ? qtrue : qfalse;
}

qboolean CODOL_LastStand_CanEnter(const gentity_t *ent)
{
    const codol_ps_ext_t *state;
    if(!ent || !ent->client) return qfalse;
    if(ent->client->lastStand) return qfalse;
    state=CODOL_PlayerStateExtConst(&ent->client->ps);
    /* C1 51c1c4: ps+4d0 bit23, ability8 modPistolDeath. */
    return state && state->abilities_known &&
        (state->abilities.masks[0]&UINT32_C(0x00800000)) ? qtrue : qfalse;
}

qboolean CODOL_Martyrdom_IsEnabled(const gentity_t *ent)
{
    const codol_ps_ext_t *state;
    if(!ent || !ent->client)return qfalse;
    state=CODOL_PlayerStateExtConst(&ent->client->ps);
    /* C1 5208b7: ps+4d0 bit10, ability21. Death-cause exclusion remains
     * MOD_SUICIDE in the caller's own enum, not C1's different numeric ID. */
    return state && state->abilities_known &&
        (state->abilities.masks[0]&UINT32_C(0x00000400)) ? qtrue : qfalse;
}

void CODOL_LastStand_Revive(gentity_t *ent)
{
    if(!ent || !ent->client) return;

    /* Clearing the flag is the state transition itself. The next
     * ClientEndFrame recomputes the movement mode from the remaining session
     * state and the wire mode follows it; the damage path stops
     * dropping hits as soon as the grace deadline is gone, and the entry gate
     * is armed again for the next lethal hit. */
    ent->client->lastStand = 0;
    ent->client->lastStandTime = 0;
}

/* <player> laststandrevive() - IW4 0x5df3b0.  No arguments, no return value.
 * Extra arguments are ignored, exactly as the IW4 handler ignores them. */
void CODOL_Scr_LastStandRevive(scr_entref_t ref)
{
    gentity_t *ent;

    if(ref.classnum)
    {
        Scr_ObjectError("not an entity");
        return;
    }
    if(ref.entnum >= MAX_GENTITIES)
    {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return;
    }
    ent = &g_entities[ref.entnum];
    if(!ent->client)
    {
        Scr_ObjectError(va("entity %i is not a player", ref.entnum));
        return;
    }

    CODOL_LastStand_Revive(ent);
}

#endif /* CODOL_SERVER */
