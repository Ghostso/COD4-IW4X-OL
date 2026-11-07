#ifdef CODOL_SERVER
/* canmantle / forcemantle.
 *
 * IW4 (D:\CoD\shx\iw4x.exe) is the reference:
 *
 *   canmantle    builtin record 0x73c904, name string 0x7053e8, handler
 *                0x5dd050.  It resolves g_entities[entnum] (0x274 stride),
 *                requires ent->client (IW4 gentity+0x158) and calls
 *                0x4eb1b0(ps, 1, ent->clipmask (IW4 gentity+0x18c),
 *                &mantleCheck[0x38]), then Scr_AddBool(0x41d7d0) of the
 *                result.  0x4eb1b0 is IW4's shared mantle query: it is the
 *                same code Pmove's Mantle_Check wrapper (0x4773a0) calls with
 *                (pm->ps, pm->handler, pm->tracemask, &check), and it does not
 *                write to the playerState - only the Pmove wrapper does, by
 *                calling 0x56e6e0 afterwards.  The literal 1 is therefore the
 *                pmove trace handler; CoD4's pmoveHandlers table
 *                (_bg_pmove.asm) maps handler 1 to G_TraceCapsule, i.e. the
 *                server-side trace, which is what a script query needs.
 *
 *   forcemantle  builtin record 0x73c910, name string 0x71f850, handler
 *                0x5dd0e0, tail-jumping to 0x47ac30:
 *                    or dword ptr [ps + 0x1e4], 0x20
 *                IW4 ps->mantleState is at 0x1d8 (yaw/timer/transIndex/flags),
 *                so that is mantleState.flags |= 0x20.  The consumer is
 *                0x56e703 "test byte ptr [ps+0x1e4], 0x20", which starts the
 *                mantle on the next Pmove exactly like a held jump button
 *                (0x56e6fa "test dword ptr [pm+8], 0x400"), and 0x56e14c
 *                "and eax, 0xffffffdf" drops the bit again when the started
 *                mantle's flags are written.
 *
 * IW4OL keeps the same mantleState_t (player.h, ps+0x5e0) and the same 0x38
 * byte ledge record, but its own offsets: ps->mantleState.flags is ps+0x5ec
 * and gclient_s hangs off gentity+0x15c.  The force bit and the ledge record
 * layout are reproduced; the offsets are not.
 *
 * T5 (D:\t5server-pdb\CoDMPServer.exe) has no canmantle/forcemantle builtin;
 * its bg_mantle.obj exports (Mantle_Check 0x41e500, Mantle_Move 0x420720,
 * Mantle_GetMantleFrac 0x420de0) confirm the same subsystem shape only.
 */
#include "scr_vm_functions.h"
#include "codol_script_mantle.h"
#include "q_math.h"
#include <string.h>

/* IW4's script query passes the entity clipmask and server trace handler. */
#define CODOL_MANTLE_HANDLER_GAME 1

static gentity_t *mantle_player(scr_entref_t ref, const char *err)
{
    if(ref.classnum || ref.entnum>=MAX_GENTITIES || !g_entities[ref.entnum].client) {
        Scr_ObjectError(err); return NULL;
    }
    return &g_entities[ref.entnum];
}

qboolean CODOL_Mantle_CanMantle(gentity_t *ent)
{
    struct pmove_t pm;
    playerState_t queryState;
    playerState_t *ps=&queryState;
    vec3_t forward;
    qboolean available;

    if(!ent || !ent->client) return qfalse;
    queryState=ent->client->ps;

    /* Mantle_Check only reads pm->ps and, through Mantle_CheckLedge,
     * pm->tracemask, pm->cmd.buttons and pm->handler; PM_trace drops the
     * pmove_t before dispatching, so a stack pmove_t is enough to run the
     * real ledge search. */
    memset(&pm, 0, sizeof(pm));
    pm.ps=ps;
    pm.tracemask=ent->clipmask;
    pm.handler=CODOL_MANTLE_HANDLER_GAME;
    pm.cmd.serverTime=ps->commandTime;

    /* Pmove feeds Mantle_Check the forward vector it just derived from
     * ps->viewangles ("lea eax,[ps+0x108]" -> AngleVectors). */
    AngleVectors(ps->viewangles, forward, NULL, NULL);

    /* Mantle_CheckLedge starts the mantle when the jump button is held or the
     * force bit is set, and reports availability through mantleState.flags.
     * Keep jump and force clear on a private state copy, and clear any hint
     * from the previous frame before measuring this query's ledge search. */
    ps->mantleState.flags &= ~(MANTLE_FLAG_FORCE|MANTLE_FLAG_HINT);

    Mantle_Check(&pm, forward);

    available=(ps->mantleState.flags & MANTLE_FLAG_HINT) ? qtrue : qfalse;
    return available;
}

/* IW4 0x5dd050: <player> canmantle() */
void CODOL_Scr_CanMantle(scr_entref_t ref)
{
    gentity_t *ent=mantle_player(ref, "canmantle requires a player");
    if(!ent) return;
    Scr_AddBool(CODOL_Mantle_CanMantle(ent) ? 1 : 0);
}

/* IW4 0x5dd0e0 -> 0x47ac30: <player> forcemantle() */
void CODOL_Scr_ForceMantle(scr_entref_t ref)
{
    gentity_t *ent=mantle_player(ref, "forcemantle requires a player");
    if(!ent) return;
    ent->client->ps.mantleState.flags|=MANTLE_FLAG_FORCE;
}

/* Developer trace around the retained Mantle_Check call in Pmove: what the
 * server saw when the jump gate passed, and whether a mantle started. Rate
 * limited so a held jump key cannot flood the log. */
#include "qcommon.h"
#include "bg_public.h"
#include "server.h"
#include <stdio.h>
static int mantle_trace_last[64];
static unsigned mantle_trace_buttons[64];
static unsigned mantle_trace_flags[64];
static unsigned char mantle_trace_pending[64];
extern cvar_t *mantle_debug, *mantle_enable;
static int mantle_debug_value(void) { return mantle_debug ? mantle_debug->integer : -1; }
void CODOL_MantleAttemptTrace(const struct pmove_t *pm)
{
    const playerState_t *ps;
    unsigned client,buttons,flags;
    int edge,transition,due;
    if(!pm || !pm->ps || !com_developer || !com_developer->integer) return;
    /* Do not force mantle_debug on here.  The retained engine prints several
     * lines for every Pmove call while it is enabled, which can stall the
     * server and feed stale snapshots back to the client.  It remains
     * available for short, explicitly enabled captures. */
    ps=pm->ps;
    client=(unsigned)ps->clientNum;
    if(client>=64) return;
    buttons=(unsigned)pm->cmd.buttons;
    flags=(unsigned)ps->pm_flags;
    edge=((buttons^mantle_trace_buttons[client])&0x400u)!=0;
    transition=((flags^mantle_trace_flags[client])&0xcu)!=0;
    due=svs.time-mantle_trace_last[client]>=200;
    mantle_trace_pending[client]=(unsigned char)(due||edge||transition);
    if(!mantle_trace_pending[client]) {
        mantle_trace_buttons[client]=buttons;
        mantle_trace_flags[client]=flags;
        return;
    }
    Com_Printf(CON_CHANNEL_SERVER,"CoDOL mantle: check client %d cmd %d pm_flags 0x%x buttons 0x%x stance %d vh %.1f target %d lerp %d/%d/%d origin (%.1f %.1f %.1f) yaw %.1f ground %d weaponstate %d vel (%.0f %.0f %.0f) debug %d enable %d\n",
        ps->clientNum,ps->commandTime,(unsigned)ps->pm_flags,(unsigned)pm->cmd.buttons,
        ps->pm_flags&3,ps->viewHeightCurrent,ps->viewHeightTarget,ps->viewHeightLerpTime,
        ps->viewHeightLerpTarget,ps->viewHeightLerpDown,ps->origin[0],ps->origin[1],ps->origin[2],
        ps->viewangles[1],ps->groundEntityNum,ps->weaponstate,ps->velocity[0],ps->velocity[1],ps->velocity[2],
        mantle_debug_value(),mantle_enable ? mantle_enable->integer : -1);
}
void CODOL_MantleResultTrace(const struct pmove_t *pm)
{
    const playerState_t *ps;
    unsigned client;
    if(!pm || !pm->ps || !com_developer || !com_developer->integer) return;
    ps=pm->ps; client=(unsigned)ps->clientNum;
    if(client>=64 || !mantle_trace_pending[client]) return;
    mantle_trace_pending[client]=0;
    mantle_trace_last[client]=svs.time;
    Com_Printf(CON_CHANNEL_SERVER,"CoDOL mantle: result pm_flags 0x%x mantle{yaw %.1f timer %d trans %d flags 0x%x} eFlags 0x%x\n",
        (unsigned)ps->pm_flags,ps->mantleState.yaw,ps->mantleState.timer,ps->mantleState.transIndex,
        (unsigned)ps->mantleState.flags,(unsigned)ps->eFlags);
    mantle_trace_buttons[client]=(unsigned)pm->cmd.buttons;
    mantle_trace_flags[client]=(unsigned)ps->pm_flags;
}

#endif
