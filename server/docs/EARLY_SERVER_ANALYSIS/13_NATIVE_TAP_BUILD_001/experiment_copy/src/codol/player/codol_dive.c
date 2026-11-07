/* CoDOL dolphin dive (dive-to-prone), native transcription of C1's pmove arm.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * C1 (alpha0022 pmove.py, all measured): PM_CanDive 0x408eb0 and
 * PM_CheckDive 0x408f30 run from PM_WalkMove right after PM_CheckJump
 * fails; PM_DiveStart 0x408a90 launches; the apex clamp 0x408df0 runs from
 * the air move; completion 0x408c00 ends the dive once the player has
 * stopped sliding. PM_UpdateStance 0x4127ba forces prone (and rewrites the
 * stance buttons) while the dive is in the air and for 100 ms after it ends.
 * Movement input is NOT removed during the dive: C1 steers the whole dive with
 * forward/right and zeroes them only inside that 100 ms window (PmoveSingle
 * 0x416432), which CODOL_PmoveC1Try applies.
 *
 * Dive state other modules read: pm_flags 0x40000000 while diving,
 * ps->jumpTime > 0 airborne (launch time) and < 0 sliding (-touchdown time),
 * and the playerState extension's dive_end_time (C1 ps+0x234).
 *
 * The retained IW3 engine has no dive, and the client re-seeds pm_flags from
 * every snapshot, so without a server-side dive the client's own dive is
 * truncated exactly like the mantle was. The dive button (0x800000) is not
 * part of the IW3 usercmd word; it is read from the raw CoDOL command the
 * pmove is executing. */
#ifdef CODOL_SERVER
#include "bg_public.h"
#include "player.h"
#include "codol_usercmd.h"
#include "codol_playerstate_ext.h"
#include "codol_weapon_state.h"
#include "codol_pmove_c1_breath.h"
#include <math.h>

/* C1 registers these at 0x408720..0x40898f (names at 0xc3f0a0..0xc3f100). */
#define DIVE_HEIGHT 39.0f       /* 0x408a98: sqrt(gravity * 39), not 2*39 */
#define DIVE_Z_SCALE 1.5f       /* dvar 2344 (0x1508894) default */
#define DIVE_MIN_SPEED 3.16f    /* dvar 2341 (0x15088a4) */
#define DIVE_MIN_SPRINT_MS 250  /* dvar 2336 (0x150889c) */
#define DIVE_COOLDOWN_MS 1500.0f /* dvar 2340 (0x1508890) */
#define DIVE_LOCKOUT_MS 100.0f  /* dvar 2337 (0x1508884) */
#define DIVE_APEX_MS 400        /* dvar 2345 (0x1508888) */
#define DIVE_MAX_SLIDE_MS 300   /* dvar 2334 (0x1508898) default */
#define DIVE_MAX_SLIDE_ADD_MS 0 /* dvar 2335 (0x1508880) default */
#define DIVE_FALL_MIN 65.0f     /* dvar 2338 (0x15088a0): no damage at or below */
#define DIVE_FALL_MAX 200.0f    /* dvar 2339 (0x150887c): full damage at or above */
#define BUTTON_DIVE_RAW 0x800000u
#define PMF_DIVETOPRONE 0x40000000  /* C1 and wire bit; unused by IW3 */

void __cdecl BG_AddPredictableEventToPlayerstate(int event, unsigned int eventParm,
                                                 playerState_t *ps);
void __cdecl PM_playerTrace(struct pmove_t *pm, trace_t *result,
    const float *start, const float *mins, const float *maxs, const float *end,
    int passEntityNum, int contentMask);

/* C1 0x4089a0 maps groundTrace.sflags to the compact dive material enum used
 * by EV_DTP_LAUNCH/EV_DTP_LAND.  This is not the ordinary five-bit surface
 * value used by footsteps. */
static const unsigned char dive_surface_event_parm[31] = {
    0,3,2,4,4,2,5,2,7,5,7,5,4,1,8,2,
    2,2,5,4,8,3,2,2,2,2,5,5,1,1,8
};

static unsigned int dive_surface_parm(const struct pml_t *pml)
{
    unsigned int flags=(unsigned int)pml->groundTrace.sflags;
    unsigned int index=(flags&0x2000u)?0u:((flags>>20)&31u);
    return index<31u ? dive_surface_event_parm[index] : 0u;
}

/* C1 ps+0x234, zero when no dive has ended. */
static int dive_end_time_c1(const playerState_t *ps)
{
    int value=0;
    return CODOL_PlayerStateDiveEndTimeRead(ps,&value) ? value : 0;
}

/* C1 PM_DiveEnd 0x408c00 (and the friction-side end at 0x408da0). */
static void dive_end(struct pmove_t *pm)
{
    playerState_t *ps=pm->ps;
    ps->pm_flags&=~PMF_DIVETOPRONE;
    ps->velocity[0]=ps->velocity[1]=ps->velocity[2]=0.0f;
    ps->jumpTime=0;
    ps->sprintState.sprintButtonUpRequired=0;
    CODOL_PlayerStateDiveEndTimeSet(ps,pm->cmd.serverTime);
}

/* C1 0x408e60 inverted: the 100 ms after a completed dive, measured from the
 * command being executed. */
int CODOL_DiveLockoutActive(const struct pmove_t *pm)
{
    int end;
    if(!pm || !pm->ps || (pm->ps->pm_flags&PMF_DIVETOPRONE)) return 0;
    end=dive_end_time_c1(pm->ps);
    if(!end) return 0;
    return (float)(pm->cmd.serverTime-end)<DIVE_LOCKOUT_MS;
}

/* C1 0x408b90, from PmoveSingle 0x41667b: a dive still flagged when the
 * player is linked is dropped and its lockout backdated so it never runs. */
void CODOL_DiveLinkedAbort(struct pmove_t *pm)
{
    playerState_t *ps;
    int end;
    if(!pm || !(ps=pm->ps)) return;
    ps->pm_flags&=~PMF_DIVETOPRONE;
    ps->jumpTime=0;
    ps->velocity[0]=ps->velocity[1]=ps->velocity[2]=0.0f;
    end=pm->cmd.serverTime-(int)DIVE_LOCKOUT_MS-1;
    if(end<0) end=0;
    CODOL_PlayerStateDiveEndTimeSet(ps,end);
    ps->sprintState.sprintButtonUpRequired=0;
}

/* C1 0x408a00, from PM_CrashLand 0x41134b: while diving, the landing damage
 * percentage comes from the 65..200 fall band instead of the ordinary one. */
void CODOL_DiveCrashLandDamage(const playerState_t *ps,float delta,int *damage)
{
    int value;
    if(!ps || !damage || !(ps->pm_flags&PMF_DIVETOPRONE)) return;
    if(!(DIVE_FALL_MIN<delta)) { *damage=0; return; }
    if(!(DIVE_FALL_MAX>delta)) { *damage=100; return; }
    value=(int)(((double)delta-DIVE_FALL_MIN)/((double)DIVE_FALL_MAX-DIVE_FALL_MIN)*100.0);
    *damage=value>=100 ? 100 : value>0 ? value : 0;
}

void CODOL_DiveResetClient(unsigned client)
{
    CODOL_PlayerStateExtClearClientDive(client);
}
/* Retained IW3 Pmove only: PM_CheckDuck runs right after this, so it sees
 * the forced prone buttons. Movement is removed only in the post-dive
 * lockout, as C1 PmoveSingle 0x416432 does. The C1 mover does not call this;
 * CODOL_PM_UpdateStanceC1 owns the same rewrite there. */
void CODOL_DivePrepareStance(struct pmove_t *pm)
{
    int lockout;
    if(!pm || !pm->ps) return;
    lockout=CODOL_DiveLockoutActive(pm);
    if(!(pm->ps->pm_flags & PMF_DIVETOPRONE) && !lockout) return;
    pm->cmd.buttons=(pm->cmd.buttons&~0x200)|0x100;
    if(lockout) pm->cmd.forwardmove=pm->cmd.rightmove=0;
}
/* Called after Jump_Check declines. This combines C1 PM_DiveEnd (0x408c00),
 * which PmoveSingle runs before movement selection, with PM_CheckDive
 * (0x408f30), which PM_WalkMove runs before ordinary ground acceleration.
 * A true return means C1 diverts to PM_AirMove at 0x410944. */
int CODOL_DiveGroundFrame(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps; int now,elapsed; float vx,vy,vz;
    if(!pm || !pm->ps || !pml) return 0;
    ps=pm->ps; now=pm->cmd.serverTime;
    if(ps->pm_flags & PMF_DIVETOPRONE) {
        vx=ps->velocity[0]; vy=ps->velocity[1]; vz=ps->velocity[2];
        /* PM_DiveEnd runs first and measures all three velocity components. */
        if(ps->jumpTime<0 && vx*vx+vy*vy+vz*vz<=DIVE_MIN_SPEED*DIVE_MIN_SPEED) {
            dive_end(pm);
        } else if(ps->jumpTime>0 && pml->walking) {
            /* Phase 1 (0x409022): touched down. */
            ps->jumpTime=-now;
            BG_AddPredictableEventToPlayerstate(CODOL_EV_DTP_LAND,
                                                dive_surface_parm(pml),ps);
        }
        if(ps->pm_flags&PMF_DIVETOPRONE) {
            /* PM_CheckDive sends execution to PM_AirMove but preserves
             * walking and groundPlane after touchdown. PM_Friction needs the
             * real contact state for C1's landing-slide reducer. */
            return 1;
        }
    }
    if(ps->pm_type!=0) return 0;
    /* PM_CanDive 0x408ed3: a definition that refuses prone refuses dive. */
    if(CODOL_WeaponBlocksProneC1(ps->weapon)) return 0;
    /* Use the command being executed. Reading the newest accepted packet here
     * crosses command ownership when a packet contains a backlog and shifts
     * the dive edge relative to the client's prediction. */
    if(!((unsigned)pm->cmd.buttons & BUTTON_DIVE_RAW)) return 0;
    /* The sprint must have ended on this very command (0x408ee2). */
    if(ps->sprintState.lastSprintEnd!=now) return 0;
    vx=ps->velocity[0]; vy=ps->velocity[1];
    if(vx*vx+vy*vy<=DIVE_MIN_SPEED*DIVE_MIN_SPEED) return 0;
    /* 0x409046: cooldown from ps+0x234; a negative interval passes. */
    elapsed=now-dive_end_time_c1(ps);
    if(!(DIVE_COOLDOWN_MS<(float)elapsed) && elapsed>=0) return 0;
    if(now-ps->sprintState.lastSprintStart<=DIVE_MIN_SPRINT_MS) return 0;
    /* PM_DiveStart: no forward impulse, only height. */
    ps->groundEntityNum=ENTITYNUM_NONE; pml->walking=0; pml->groundPlane=0;
    ps->jumpTime=now;
    vz=(float)sqrt((double)ps->gravity*DIVE_HEIGHT)*DIVE_Z_SCALE;
    ps->velocity[2]=vz;
    ps->pm_flags|=PMF_DIVETOPRONE;
    /* PM_DiveStart 0x408b6c clears 0x2000, 0x100 and 0x80 together. */
    ps->pm_flags&=~0x2180;
    ps->pm_time=0;
    ps->jumpOriginZ=ps->origin[2];
    BG_AddPredictableEventToPlayerstate(CODOL_EV_DTP_LAUNCH,
                                        dive_surface_parm(pml),ps);
    pml->walking=0; pml->groundPlane=0;
    return 1;
}


/* C1 Dtp_ReduceFriction 0x408ca0. */
float CODOL_DiveReduceFriction(struct pmove_t *pm,struct pml_t *pml)
{
    playerState_t *ps;
    trace_t tr;
    vec3_t start,end;
    int elapsed;
    (void)pml;
    if(!pm || !(ps=pm->ps) || !(ps->pm_flags&PMF_DIVETOPRONE)) return 1.0f;
    if(ps->jumpTime>=0) return 1.0f;
    elapsed=ps->jumpTime+pm->cmd.serverTime;
    start[0]=end[0]=ps->origin[0];
    start[1]=end[1]=ps->origin[1];
    start[2]=ps->origin[2]+1.0f;
    end[2]=ps->origin[2]-1.0f;
    PM_playerTrace(pm,&tr,start,pm->mins,pm->maxs,end,ps->clientNum,0x01000000);
    if(tr.fraction<1.0f && elapsed<DIVE_MAX_SLIDE_MS+DIVE_MAX_SLIDE_ADD_MS)
        return 0.0f;
    if(elapsed<DIVE_MAX_SLIDE_MS)
        return elapsed>0 ? (float)elapsed/(float)DIVE_MAX_SLIDE_MS : 0.0f;
    dive_end(pm);
    return 1.0f;
}
/* Air frame, before PM_AirMove (C1 apex clamp 0x408df0 from 0x41068f). */
void CODOL_DiveAirFrame(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps; int now;
    (void)pml;
    if(!pm || !pm->ps) return;
    ps=pm->ps; now=pm->cmd.serverTime;
    if(!(ps->pm_flags & PMF_DIVETOPRONE)) return;
    if(ps->origin[2]<=ps->jumpOriginZ+DIVE_HEIGHT) return;
    if(ps->jumpTime>0 && now-ps->jumpTime<DIVE_APEX_MS) ps->velocity[2]=0.0f;
    else if(ps->velocity[2]>0.0f) ps->velocity[2]=0.0f;
}
#endif
