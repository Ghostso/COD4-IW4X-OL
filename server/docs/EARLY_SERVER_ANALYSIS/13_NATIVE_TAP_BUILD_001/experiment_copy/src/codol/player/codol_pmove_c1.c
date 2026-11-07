/* C1 stance/view-height state, transcribed from C1.exe.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Authority:
 *   PM_UpdateStance     0x00412560..0x00413141
 *   PM_UpdateViewheight 0x00411D80..0x00412141
 *   curve tables        0x00CD7FA0..0x00CD8108
 *
 * This module deliberately has no C1<->IW3 state mapping.  The overlapping
 * playerState members used here hold their C1 values directly: pm_flags,
 * origin, velocity, commandTime, viewHeight*, mantleState and jump state.
 * C1-only members remain implementation work in the sidecar/native state.
 * Network decoding is a boundary concern and hands this core the full command
 * the client sent through CODOL_ExecutedUsercmd.
 */
#ifdef CODOL_SERVER
#include "codol_pmove_c1.h"
#include "codol_pmove_trace.h"
#include "codol_abilities.h"
#include "codol_pmove_c1_mantle.h"
#include "codol_pmove_c1_ground.h"
#include "codol_bot.h"
#include "codol_pmove_c1_breath.h"
#include "codol_pmove_c1_zoom.h"
#include "codol_playerstate_ext.h"
#include "codol_sprint_state.h"
#include "codol_weapon_input.h"
#include "codol_weapon_native.h"
#include "codol_weapon_state.h"
#include "codol_weapon_turret_ads.h"
#include "codol_animation_tables.h"
#include "codol_engine_state.h"
#include "codol_script_startup_extra.h"
#include "codol_events.h"
#include "bg.h"
#include "cvar.h"
#include "qcommon_io.h"
#include "q_math.h"
#include <math.h>
#include <string.h>

#define C1_BUTTON_PRONE          0x00000100u
#define C1_BUTTON_CROUCH         0x00000200u
#define C1_BUTTON_STANCE_HELD    0x00001000u
#define C1_BUTTON_SPRINT         0x00000002u
#define C1_BUTTON_ADS            0x00000800u
#define C1_BUTTON_LEAN_LEFT      0x00000040u
#define C1_BUTTON_LEAN_RIGHT     0x00000080u

#define C1_PMF_PRONE             0x00000001u
#define C1_PMF_CROUCH            0x00000002u
#define C1_PMF_MANTLE            0x00000004u
#define C1_PMF_LADDER            0x00000008u
#define C1_PMF_RESPAWNED         0x00000400u
#define C1_PMF_FROZEN            0x00000800u
#define C1_PMF_REMOTE_CONTROLLING 0x00080000u
#define C1_PMF_SPRINTING         0x00004000u
#define C1_PMF_VIEWHEIGHT_SLOW   0x00400000u
#define C1_PMF_DENY_STAND        0x00800000u
#define C1_PMF_DENY_CROUCH       0x01000000u
#define C1_PMF_DENY_PRONE        0x02000000u
#define C1_PMF_DIVE_TO_PRONE     0x40000000u
#define C1_SPRINT_START_BUTTONS   0x0001cc35u
#define C1_SPRINT_BREAK_BUTTONS   0x0001cf35u
#define C1_SPRINT_START_FLAGS     0x0000801cu
#define C1_SPRINT_BREAK_FLAGS     0x00008018u

#define C1_EF_CROUCH             0x00000004u
#define C1_EF_PRONE              0x00000008u

#define C1_PM_NORMAL_LINKED      1
#define C1_PM_NOCLIP             2
#define C1_PM_UFO                3
#define C1_PM_MPVIEWER           4
#define C1_PM_SPECTATOR          5
#define C1_PM_INTERMISSION       6
#define C1_PM_LASTSTAND          7
#define C1_PM_DEAD               8
#define C1_PM_DEAD_LINKED        9

#define C1_VH_PRONE              11
#define C1_VH_LASTSTAND          22
#define C1_VH_CROUCH             40
#define C1_VH_STAND              60
#define C1_ENTITYNUM_NONE        2047
#define C1_SURF_LADDER           0x00000008u
#define C1_PMF_LADDER_FALL       0x00001000u
#define C1_LADDER_GROUND_DIST    8.0f
#define C1_LADDER_AIR_DIST       30.0f
#define C1_LADDER_XY_SHRINK      6.0f
#define C1_LADDER_Z_BASE         8.0f
#define C1_LADDER_REGRAB_MS      300
#define C1_LADDER_PITCH_BIAS     0.25f
#define C1_LADDER_PITCH_GAIN     2.5f
#define C1_LADDER_CLIMB_SCALE    0.5f
#define C1_LADDER_STRAFE_SCALE   0.2f
#define C1_LADDER_ACCELERATE     9.0f
#define C1_LADDER_LATERAL_DAMP   16.0f
#define C1_LADDER_STICK_PUSH     50.0f
#define C1_LADDER_JUMPOFF_SPEED  128.0f
#define C1_LADDER_JUMPOFF_ZSCALE 0.75f
#define C1_CMDSCALE_DIVISOR      127.0f

typedef struct { int pct; float height; } c1_vh_key_t;

static const c1_vh_key_t vh_crouch_down[] = {
    {0,60.0f},{1,59.5f},{4,58.5f},{30,56.0f},{80,44.0f},
    {90,41.5f},{95,40.5f},{100,40.0f}
};
static const c1_vh_key_t vh_stand[] = {
    {0,40.0f},{5,40.5f},{10,41.5f},{20,44.0f},{70,56.0f},
    {96,58.5f},{99,59.5f},{100,60.0f}
};
static const c1_vh_key_t vh_prone[] = {
    {0,40.0f},{11,38.0f},{22,33.0f},{34,25.0f},{45,16.0f},
    {50,15.0f},{55,16.0f},{70,18.0f},{90,17.0f},{100,11.0f}
};
static const c1_vh_key_t vh_crouch_up[] = {
    {0,11.0f},{5,10.0f},{30,21.0f},{50,25.0f},{67,31.0f},
    {83,34.0f},{100,40.0f}
};

extern void __cdecl PM_playerTrace(struct pmove_t *pm, trace_t *result,
    const float *start, const float *mins, const float *maxs, const float *end,
    int passEntityNum, int contentMask);
extern void __cdecl PM_AddEvent(playerState_t *ps, int event);
extern void __cdecl PM_Weapon(struct pmove_t *pm, struct pml_t *pml);
extern void __cdecl PM_UpdatePronePitch(struct pmove_t *pm,struct pml_t *pml);
extern void REGPARM(2) PM_MeleeChargeUpdate(struct pmove_t *pm,struct pml_t *pml);
extern void __cdecl BG_AnimUpdatePlayerStateConditions(struct pmove_t *pm);
extern int __cdecl BG_GetMaxSprintTime(const playerState_t *ps);
extern double __cdecl PitchForYawOnNormal(float yaw,const vec3_t normal);
extern double __cdecl UnGetLeanFraction(float fraction);
extern int __cdecl BG_CheckProne(int,const vec3_t,float,float,float,float *,float *,
    unsigned char,unsigned char,unsigned char,unsigned char,int,float);
extern cvar_t *bg_ladder_yawcap,*mantle_view_yawcap;
extern int CODOL_DiveLockoutActive(const struct pmove_t *pm);
extern void CODOL_DiveLinkedAbort(struct pmove_t *pm);
extern int CODOL_DiveGroundFrame(struct pmove_t *pm,struct pml_t *pml);
extern void CODOL_DiveAirFrame(struct pmove_t *pm,struct pml_t *pml);

/* Atomic readiness mask. The active owner never falls through to retained
 * Pmove after consuming a C1 command. */
#define C1_PM_IMPLEMENTED (CODOL_PM_C1_INPUT_READY|CODOL_PM_C1_STANCE_READY|CODOL_PM_C1_VIEWHEIGHT_READY|CODOL_PM_C1_GROUND_READY|CODOL_PM_C1_SLIDE_READY|CODOL_PM_C1_LADDER_READY|CODOL_PM_C1_MANTLE_READY|CODOL_PM_C1_DIVE_READY|CODOL_PM_C1_WEAPON_READY)
#define C1_PM_REQUIRED (CODOL_PM_C1_INPUT_READY|CODOL_PM_C1_STANCE_READY|CODOL_PM_C1_VIEWHEIGHT_READY|CODOL_PM_C1_GROUND_READY|CODOL_PM_C1_SLIDE_READY|CODOL_PM_C1_LADDER_READY|CODOL_PM_C1_MANTLE_READY|CODOL_PM_C1_DIVE_READY|CODOL_PM_C1_WEAPON_READY)

unsigned CODOL_PmoveC1Implemented(void) { return C1_PM_IMPLEMENTED; }
unsigned CODOL_PmoveC1Required(void) { return C1_PM_REQUIRED; }
static codol_usercmd_t c1_previous[MAX_CLIENTS];
static unsigned char c1_previous_valid[MAX_CLIENTS];
static void c1_ladder_fall(playerState_t *ps);
static int c1_ladder_jump(codol_pmove_c1_t *move);
static uint32_t codol_stance_wire_buttons[MAX_CLIENTS];
static int stance_clear(struct pmove_t *pm,unsigned want);
static int weapon_locks_stance_c1(const playerState_t *ps);
static int c1_hand_state(const playerState_t *ps,unsigned hand,unsigned *state);
static float c1_angle180(float angle);

/* C1 PM_UpdateAimSpreadScale 0x00418b70.  The retained IW3 routine reads
 * stance from eFlags and its own airborne enum.  C1 owns both through
 * pm_flags/groundEntityNum, so calling the retained producer made spread
 * oscillate whenever prediction corrected those unrelated eFlags. */
static void update_aim_spread_c1(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    const struct WeaponDef *def=BG_GetWeaponDef(ps->weapon);
    float decay,band=1.0f,add=0.0f,increase,decrease,speed2;
    int i;
    if(!def || !isfinite(ps->aimSpreadScale)) return;
    decay=def->fHipSpreadDecayRate;
    if(decay==0.0f) {
        increase=0.0f;
        decrease=1.0f;
        goto apply;
    }
    if(def->hipSpreadStandMax!=def->fHipSpreadStandMin)
        band=((float)ps->spreadOverride-def->fHipSpreadStandMin)/
             (def->hipSpreadStandMax-def->fHipSpreadStandMin);
    if(ps->groundEntityNum==C1_ENTITYNUM_NONE && ps->pm_type!=C1_PM_NORMAL_LINKED)
        decay*=0.5f;
    else if(ps->eFlags&8) {
        decay*=def->fHipSpreadProneDecay;
        if(def->hipSpreadProneMax!=def->fHipSpreadProneMin)
            band=((float)ps->spreadOverride-def->fHipSpreadProneMin)/
                 (def->hipSpreadProneMax-def->fHipSpreadProneMin);
    } else if(ps->eFlags&4) {
        decay*=def->fHipSpreadDuckedDecay;
        if(def->hipSpreadDuckedMax!=def->fHipSpreadDuckedMin)
            band=((float)ps->spreadOverride-def->fHipSpreadDuckedMin)/
                 (def->hipSpreadDuckedMax-def->fHipSpreadDuckedMin);
    }
    if(ps->spreadOverrideState==1) {
        decrease=decay*move->local.frametime/band;
        increase=0.0f;
    } else {
        decrease=decay*move->local.frametime;
        if(ps->fWeaponPosFrac!=1.0f) {
            if(def->fHipSpreadTurnAdd!=0.0f && move->local.frametime>0.0f) {
                for(i=0;i<2;++i)
                    add+=(float)fabs(c1_angle180((float)(int16_t)move->cmd.angles[i]*
                        (360.0f/65536.0f)-(float)(int16_t)move->oldcmd.angles[i]*
                        (360.0f/65536.0f)))*0.01f*def->fHipSpreadTurnAdd/
                        move->local.frametime;
            }
            speed2=ps->velocity[0]*ps->velocity[0]+ps->velocity[1]*ps->velocity[1];
            if(def->fHipSpreadMoveAdd!=0.0f && (move->cmd.direction&15u) &&
               speed2>121.0f && ps->speed>0)
                add+=(float)sqrt(speed2)*def->fHipSpreadMoveAdd/(float)ps->speed;
            if(ps->groundEntityNum==C1_ENTITYNUM_NONE && ps->pm_type!=C1_PM_NORMAL_LINKED)
                for(i=0;i<2;++i) add+=1.28f;
        }
        increase=add*move->local.frametime;
    }
apply:
    if(increase<=0.0f) ps->aimSpreadScale-=decrease*255.0f;
    else ps->aimSpreadScale+=increase*255.0f;
    if(ps->spreadOverrideState==1 && band*ps->aimSpreadScale<255.0f) {
        ps->spreadOverrideState=0;
        ps->aimSpreadScale*=band;
    }
    if(ps->aimSpreadScale<0.0f) ps->aimSpreadScale=0.0f;
    else if(ps->aimSpreadScale>255.0f) ps->aimSpreadScale=255.0f;
}

static float c1_angle180(float angle)
{
    while(angle>180.0f) angle-=360.0f;
    while(angle<=-180.0f) angle+=360.0f;
    return angle;
}

static float c1_angle360(float angle)
{
    while(angle>=360.0f) angle-=360.0f;
    while(angle<0.0f) angle+=360.0f;
    return angle;
}

static void range_limit_view(playerState_t *ps)
{
    unsigned i;
    for(i=0;i<2;++i) {
        float range=ps->viewAngleClampRange[i];
        float delta,correction;
        if(range>=180.0f) continue;
        delta=(float)AngleDelta(ps->viewAngleClampBase[i],ps->viewangles[i]);
        if(delta<=range && delta>=-range) continue;
        correction=delta>range?delta-range:delta+range;
        ps->delta_angles[i]+=correction;
        ps->viewangles[i]=c1_angle360(ps->viewAngleClampBase[i]+
                                      (correction<=0.0f?range:-range));
    }
}

/* C1 Mantle_CapView 0x40a9c0. */
static void cap_mantle_view(playerState_t *ps)
{
    float cap=mantle_view_yawcap?mantle_view_yawcap->value:60.0f;
    float delta,value;
    if(cap<=0.0f) return;
    delta=(float)AngleDelta(ps->mantleState.yaw,ps->viewangles[1]);
    if(delta>=-cap && delta<=cap) return;
    while(delta< -cap) delta+=cap;
    while(delta>cap) delta-=cap;
    value=delta<=0.0f?cap:-cap;
    ps->delta_angles[1]+=delta;
    ps->viewangles[1]=c1_angle360(ps->mantleState.yaw+value);
}

static void cap_ladder_view(playerState_t *ps)
{
    float cap=bg_ladder_yawcap?bg_ladder_yawcap->value:100.0f;
    float facing,delta,correction;
    if(cap==0.0f) return;
    facing=c1_angle360((float)(atan2(ps->vLadderVec[1],ps->vLadderVec[0])*
                     (180.0/M_PI))+180.0f);
    delta=(float)AngleDelta(facing,ps->viewangles[1]);
    if(delta<=cap && delta>=-cap) return;
    correction=delta>cap?delta-cap:delta+cap;
    ps->delta_angles[1]+=correction;
    ps->viewangles[1]=c1_angle360(facing+(correction<=0.0f?cap:-cap));
}

/* C1 AngleNormalize180 (inlined at 0x4148b3..0x4148e2) and AngleNormalize360
 * 0x61b730, including their float stores: the prone yaw search compares these
 * results for equality and against 1 degree, so the loop-based wrappers used
 * elsewhere in this file are not interchangeable here. */
static float c1_norm180(float angle)
{
    float scaled=(float)((double)angle*0.0027777778450399637);
    float bias=(float)((double)scaled+0.5);
    return (float)(((double)scaled-floor((double)bias))*360.0);
}

static float c1_norm360(float angle)
{
    float scaled=(float)((double)angle*0.0027777778450399637);
    float result=(float)(((double)scaled-floor((double)scaled))*360.0);
    float wrapped=(float)((double)result-360.0);
    return wrapped<0.0f ? result : wrapped;
}

/* C1 BG_CheckProne with the already-prone arguments at a fixed 45 unit feet
 * distance (0x414afe/0x414b6c/0x414c4b). C1 passes no pitch outputs. */
static int prone_yaw_valid45(codol_pmove_c1_t *move,float yaw)
{
    playerState_t *ps=move->ps;
    float torso=0.0f,waist=0.0f;
    return BG_CheckProne(ps->clientNum,ps->origin,15.0f,30.0f,yaw,&torso,&waist,
                         1,ps->groundEntityNum!=C1_ENTITYNUM_NONE,1,
                         move->host->handler,0,45.0f);
}

/* C1 0x414080. The candidate body yaw is tested with the feet swung part of
 * the way back toward the view: the farther the view is from the body (up to
 * 240 degrees), the more of the candidate is kept and the shorter the feet
 * distance (50 -> 45). */
static int prone_feet_valid(codol_pmove_c1_t *move,float yaw)
{
    playerState_t *ps=move->ps;
    float delta=c1_norm180(yaw-ps->viewangles[1]);
    float frac=(float)(fabs(delta)/240.0);
    double rest=1.0-(double)frac;
    float check=c1_norm360((float)((double)yaw-rest*(double)delta));
    float feet=(float)((double)frac*45.0+rest*50.0);
    return BG_CheckProne(ps->clientNum,ps->origin,15.0f,30.0f,check,
                         &ps->fTorsoPitch,&ps->fWaistPitch,1,
                         ps->groundEntityNum!=C1_ENTITYNUM_NONE,1,
                         move->host->handler,0,feet);
}

/* C1 PM_UpdateLean 0x4142d0, also structurally matching the retained IW3
 * routine. leanf is prediction state: it changes command speed, camera roll,
 * and the published playerState, so the native C1 mover must own it. */
static void update_lean(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    trace_t tr;
    vec3_t start,end,bounds={0.0f,0.0f,0.0f};
    float maximum=0.5f,target=0.0f,step,allowed;
    unsigned buttons=move->cmd.buttons;

    if((buttons&(C1_BUTTON_LEAN_LEFT|C1_BUTTON_LEAN_RIGHT)) &&
       !(ps->pm_flags&0x800) && ps->pm_type<C1_PM_DEAD &&
       (ps->groundEntityNum!=C1_ENTITYNUM_NONE ||
        ps->pm_type==C1_PM_NORMAL_LINKED)) {
        if(buttons&C1_BUTTON_LEAN_LEFT) target-=1.0f;
        if(buttons&C1_BUTTON_LEAN_RIGHT) target+=1.0f;
    }
    if(ps->eFlags&0x00100c00) target=0.0f;
    if(ps->viewHeightTarget==C1_VH_LASTSTAND) maximum=0.25f;

    if(target==0.0f) {
        step=maximum*(float)move->local.msec/280.0f;
        if(ps->leanf>step) ps->leanf-=step;
        else if(ps->leanf< -step) ps->leanf+=step;
        else ps->leanf=0.0f;
    } else {
        float wanted=target*maximum;
        step=maximum*(float)move->local.msec/350.0f;
        if(ps->leanf<wanted) {
            ps->leanf+=step;
            if(ps->leanf>wanted) ps->leanf=wanted;
        } else if(ps->leanf>wanted) {
            ps->leanf-=step;
            if(ps->leanf<wanted) ps->leanf=wanted;
        }
    }
    if(ps->leanf==0.0f) return;

    memcpy(start,ps->origin,sizeof(start));
    start[2]+=ps->viewHeightCurrent;
    memcpy(end,start,sizeof(end));
    AddLeanToPosition(end,ps->viewangles[1],ps->leanf<0.0f?-1.0f:1.0f,
                      16.0f,20.0f);
    PM_playerTrace(move->host,&tr,start,bounds,bounds,end,ps->clientNum,0x2814011);
    allowed=(float)UnGetLeanFraction(tr.fraction);
    if(fabs(ps->leanf)>allowed) ps->leanf=ps->leanf<0.0f?-allowed:allowed;
}

/* C1 0x414580: the 85 degree body/view yaw cap, then the blocked-turn event
 * and its 98% pull back toward the pre-command yaw. */
static void cap_prone_yaw_c1(playerState_t *ps,float delta,int blocked,
                             float old_yaw,float entry_yaw)
{
    if(delta>85.0f || delta< -85.0f) {
        float correction=delta>85.0f ? (float)((double)delta-85.0) :
                                       (float)((double)delta+85.0);
        ps->delta_angles[1]+=correction;
        ps->viewangles[1]=c1_norm360(0.0f<correction ?
            (float)((double)ps->proneDirection-85.0) :
            (float)(85.0+(double)ps->proneDirection));
    }
    if(!blocked) return;
    BG_AddPredictableEventToPlayerstate((BGEvent)CODOL_EV_STANCE_INVALID,3,
                                        (gclient_t *)ps);
    {
        float back=c1_norm180(old_yaw-ps->viewangles[1]);
        float turned=c1_norm180(entry_yaw-ps->viewangles[1]);
        if(!(fabs(back)<=1.0f)) return;
        if(!(turned*back>0.0f)) return;
        back=(float)((double)back*0.9800000190734863);
        ps->viewangles[1]=c1_norm360(ps->viewangles[1]+back);
        ps->delta_angles[1]+=back;
    }
}

/* C1 0x414730: view pitch within 45 degrees of the prone torso pitch. */
static void cap_prone_pitch_c1(playerState_t *ps)
{
    float delta=c1_norm180(ps->proneTorsoPitch-ps->viewangles[0]);
    float correction;
    if(delta>45.0f) correction=(float)((double)delta-45.0);
    else if(delta< -45.0f) correction=(float)((double)delta+45.0);
    else return;
    ps->delta_angles[0]+=correction;
    ps->viewangles[0]=c1_norm180(0.0f<correction ?
        (float)((double)ps->proneTorsoPitch-45.0) :
        (float)(45.0+(double)ps->proneTorsoPitch));
}

/* C1 PM_UpdateProneViewAngles 0x414880 (from PM_UpdateViewAngles 0x414f6d).
 * The body turns toward the view at 55 deg/s while the view is more than 80
 * degrees off it, while moving, or while the prone key is held. A candidate
 * the feet search rejects is walked back one degree at a time toward the
 * current body yaw; if the current body yaw itself no longer fits the view,
 * the view is walked toward the body instead. old_yaw is the view yaw before
 * this command's angles were applied. */
static void update_prone_view_c1(codol_pmove_c1_t *move,float old_yaw)
{
    playerState_t *ps=move->ps;
    float entry_yaw=ps->viewangles[1];
    float delta=c1_norm180(ps->proneDirection-ps->viewangles[1]);
    int last=ps->viewHeightTarget==C1_VH_LASTSTAND;
    int blocked=0,guard;
    int big=delta>80.0f || delta< -80.0f;
    int moving=(move->cmd.direction&15u) && delta!=0.0f;

    if(big || moving || (move->cmd.buttons&C1_BUTTON_PRONE)) {
        float step=(float)((double)move->local.msec*55.0*0.0010000000474974513);
        float yaw,back;
        int searching=1;
        if(step>(float)fabs(delta)) yaw=ps->viewangles[1];
        else yaw=0.0f<delta ? ps->proneDirection-step : ps->proneDirection+step;
        for(guard=0;guard<512;++guard) {
            if(prone_feet_valid(move,yaw)) {
                if(last || (prone_yaw_valid45(move,ps->viewangles[1]) &&
                            prone_yaw_valid45(move,yaw)))
                    ps->proneDirection=yaw;
                else blocked=1;
                break;
            }
            if(last) { ps->proneDirection=yaw; break; }
            if(!searching) break;
            back=c1_norm180(ps->proneDirection-yaw);
            if(!isfinite(back)) break;
            if(fabs(back)<=1.0f) { searching=0; blocked=1; }
            else back=0.0f<back ? 1.0f : -1.0f;
            yaw=c1_norm360(yaw+back);
        }
    }

    delta=c1_norm180(ps->proneDirection-ps->viewangles[1]);
    if(delta!=0.0f) {
        float candidate=ps->proneDirection,step;
        int first=1,fits;
        for(guard=0;guard<512;++guard) {
            fits=last || prone_yaw_valid45(move,candidate);
            if(fits && (prone_feet_valid(move,candidate) || last)) {
                ps->proneDirection=candidate;
                break;
            }
            if(!first || !isfinite(delta)) break;
            if(fabs(delta)<=1.0f) { first=0; step=delta; }
            else step=0.0f<delta ? 1.0f : -1.0f;
            blocked=1;
            ps->delta_angles[1]+=step;
            ps->viewangles[1]=c1_norm360(step+ps->viewangles[1]);
            delta=c1_norm180(ps->proneDirection-ps->viewangles[1]);
            if(!fits) candidate=c1_norm360(candidate+delta);
        }
    }
    cap_prone_yaw_c1(ps,delta,blocked,old_yaw,entry_yaw);
    cap_prone_pitch_c1(ps);
}

/* Prediction-facing subset of C1 PM_UpdateViewAngles 0x414e50 / 0x4141a0.
 * It consumes C1 command angles directly and owns every delta-angle
 * correction it makes. The pitch caps (85/85) are C1 literals at 0x41421c and
 * 0x41424c, not the IW3 player_view_pitch dvars. */
static void update_viewangles(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    float raw;
    float old_yaw=ps->viewangles[1];
    unsigned i;
    /* C1 0x4141b8: NORMAL_LINKED/DEAD_LINKED with linkFlags bit 1 (angles
     * locked) skips the free-look pitch clamp at 0x414209..0x414216; the
     * link frame owns the view, so delta_angles[0] is left alone. */
    int angles_locked=(ps->pm_type==C1_PM_NORMAL_LINKED || ps->pm_type==C1_PM_DEAD_LINKED) &&
        (CODOL_PlayerLinkFlags(ps->clientNum)&1u);
    for(i=0;i<3;++i) {
        raw=(float)SHORT2ANGLE(move->cmd.angles[i])+ps->delta_angles[i];
        raw=c1_angle180(raw);
        if(i==0 && !angles_locked) {
            if(raw>85.0f) {
                ps->delta_angles[0]+=85.0f-raw; raw=85.0f;
            } else if(raw< -85.0f) {
                ps->delta_angles[0]+=-85.0f-raw; raw=-85.0f;
            }
        }
        ps->viewangles[i]=raw;
    }
    /* C1 PM_UpdateViewAngles 0x414f00..0x414fb9. Linked/turret view clamps
     * own the frame; mantle caps yaw and returns; ladder caps before prone. */
    if((ps->eFlags&0x0c00) || (CODOL_PlayerLinkFlags(ps->clientNum)&4u) ||
       (ps->pm_type==C1_PM_NORMAL_LINKED && (ps->otherFlags&1))) {
        range_limit_view(ps);
        return;
    }
    if(ps->pm_flags&C1_PMF_MANTLE) {
        cap_mantle_view(ps);
        return;
    }
    if((ps->pm_flags&C1_PMF_LADDER) &&
       ps->groundEntityNum==C1_ENTITYNUM_NONE) cap_ladder_view(ps);
    /* 0x414f44..0x414f51: otherFlags 0x400000 suspends the prone body. */
    if((ps->pm_flags&C1_PMF_PRONE) && !(ps->otherFlags&0x00400000))
        update_prone_view_c1(move,old_yaw);
    if(ps->pm_type!=C1_PM_NOCLIP && ps->pm_type!=C1_PM_UFO &&
       ps->pm_type!=C1_PM_SPECTATOR) update_lean(move);
}

static void sync_stance_command(codol_pmove_c1_t *move)
{
    /* PM_UpdateStance rewrites pm->cmd in C1 for ladder and dive lockout.
     * Movement consumes the full C1 command copy, so carry those authoritative
     * rewrites back instead of moving from stale pre-stance input. */
    move->cmd.buttons=(uint32_t)move->host->cmd.buttons;
    if(!move->host->cmd.forwardmove) move->cmd.direction&=~3u;
    if(!move->host->cmd.rightmove) move->cmd.direction&=~12u;
}

/* C1 PmoveSingle 0x4161dc..0x4162d7 owns the two predicted weapon markers.
 * Bit 0x100 follows the input-lock command. Bit 0x200 is present only while
 * an otherwise runnable hand has a live trigger request and rounds in that
 * hand's magazine. Retained IW3 uses different firing bits, so it cannot be
 * allowed to feed these fields back into the C1 snapshot. */
static void update_predicted_weapon_eflags(codol_pmove_c1_t *move)
{
    playerState_t *ps;
    codol_weapon_hand_t hand;
    int ammo;
    unsigned i;
    if(!move || !(ps=move->ps)) return;
    if(move->cmd.buttons&0x10000000u) ps->eFlags|=0x100u;
    else ps->eFlags&=~0x100u;
    ps->eFlags&=~0x200u;
    if(ps->pm_type==C1_PM_INTERMISSION || (ps->pm_flags&C1_PMF_RESPAWNED))
        return;
    for(i=0;i<CODOL_WEAPON_HANDS;++i) {
        unsigned request=i ? 0x00100000u : 1u;
        if(!(move->cmd.buttons&request)) continue;
        if(i && !CODOL_WeaponStateIsDualWielding(ps)) continue;
        if(!CODOL_WeaponStateHand(ps,i,&hand) || !hand.weapon ||
           (hand.state!=CODOL_WEAPONSTATE_READY &&
            hand.state!=CODOL_WEAPONSTATE_FIRING)) continue;
        if(CODOL_WeaponStateClipAmmo(ps,hand.weapon,i,&ammo) && ammo>0) {
            ps->eFlags|=0x200u;
            return;
        }
    }
}

/* C1 0x418240 PM_UpdateAimDownSightFlag followed by 0x415332
 * PM_UpdateAdsFlag. These flags must exist before PM_CmdScale: rebuilding
 * them only in the later weapon pass makes ADS movement one command late. */
static void update_aim_down_sight_flag(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    /* C1 BG_PlayerCanAds 0x0041818d selects the OFFHAND definition while
     * weapFlags bit 2 is up (`(ps+0x344 & 2) ? ps+0x328 : ps+0x33c`), the same
     * choice PM_UpdateAimDownSightFlag 0x0041824b makes one instruction into
     * itself. Reading the primary definition through a grenade/offhand pull
     * tested the wrong weapon's aimDownSight byte (+0xbc8). */
    const struct WeaponDef *def=BG_GetWeaponDef((ps->weapFlags&2) ?
        (unsigned)ps->offHandIndex : (unsigned)ps->weapon);
    unsigned flags=(unsigned)ps->pm_flags;
    unsigned state=0;
    int state_known=CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                                    (unsigned)ps->weapAnim,&state);
    int blocked_state=(state>=1 && state<=5) || (state>=13 && state<=21) ||
                      state==29 || state==30;
    /* C1 BG_PlayerCanAds 0x0041817b: once ps->eFlags carries the turret pair
     * the answer is dvar "209" alone and the weapon definition is never
     * consulted.  turret_minigun_mp ships aimDownSight == 0, so the def test
     * below refuses every mounted MG and the turret never leaves the hip. */
    int turret=(ps->eFlags&(int)PLAYER_EFLAG_TURRET_MASK)!=0;
    /* C1 BG_PlayerCanAds 0x00418140..0x00418154 tests the akimbo flag before
     * anything else: ps+0x35c == 1 off a turret answers "no ADS". The right
     * mouse button still sends C1_BUTTON_ADS (CL_CmdButtons 0x0048fc12 has no
     * akimbo test) because on an akimbo weapon it is the second hand's
     * trigger 0x100000; without this the server aimed, lerped fWeaponPosFrac
     * and published an ADS the client never predicts. */
    int akimbo=CODOL_WeaponStateBlocksAds(ps);
    int can_ads=!akimbo && (ps->otherFlags&0x1000) &&
                (turret ? CODOL_TurretAdsAllowed()
                        : (def && def->aimDownSight && !blocked_state));
    /* C1 BG_PlayerCanAds 0x00418140 classifies the hand state by reading
     * ps+0x278 directly, so it has no "unknown state" outcome. Clearing
     * PMF_ADS_BUTTON because this port's (weaponstate, weapAnim) translation
     * refused a pair drove PM_UpdateAimDownSightLerp's `desired` to 0 and
     * walked fWeaponPosFrac off exact 1.0f mid-scope, which re-arms C1's
     * steady-ADS sway ramp (0x00422E20 tests ps+0x348 against 1.0f with
     * fucomp). Hold the flags through an unclassifiable command instead. */
    /* C1's turret arm reads no hand state, so an unclassifiable pair must not
     * hold PMF_ADS_BUTTON down while linked. */
    /* The akimbo arm reads no hand state either: it answers before the
     * classification that could fail. */
    if(!state_known && !turret && !akimbo) return;
    flags&=~0x10u;
    if((move->cmd.buttons&C1_BUTTON_ADS) && can_ads) flags|=0x10u;
    ps->pm_flags=(int)flags;
}

static int ads_move_fast_ability(const playerState_t *ps)
{
    const codol_ps_ext_t *ext=CODOL_PlayerStateExtConst(ps);
    return ext && ext->abilities_known &&
           (ext->abilities.masks[27>>5]&(UINT32_C(0x80000000)>>(27&31)));
}

static void update_ads_flag(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    unsigned flags=(unsigned)ps->pm_flags;
    unsigned state=0;
    int state_known=CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                                    (unsigned)ps->weapAnim,&state);
    /* Same reasoning as update_aim_down_sight_flag: C1 0x00415332 reads the
     * state, it cannot fail to classify it, and dropping PMF_ADS for one
     * command is visible as an ADS/sway snap. */
    if(!state_known) return;
    flags&=~0x40u;
    /* C1 0x0041537d..0x0041538e: after every other test passes, ability 27
     * modMoveFastWhileAiming (Stalker; ps+0x4d0 bit 4, MSB-first id 27)
     * leaves PMF 0x40 clear, so PM_CmdScale and the footstep ADS tests
     * treat the aiming player as hip-fire. */
    if(ps->pm_type<C1_PM_DEAD && (move->cmd.buttons&C1_BUTTON_ADS) &&
       !(flags&C1_PMF_PRONE) && (flags&0x10u) && !(ps->eFlags&0x0c00) &&
       !(state>=8 && state<=12) && !ads_move_fast_ability(ps)) flags|=0x40u;
    ps->pm_flags=(int)flags;
}

/* C1 PM_UpdateAimDownSightLerp 0x41875b applies ability 10 to the elapsed
 * ADS time before multiplying by the weapon's in/out rate. */
static float ads_frame_msec_c1(const playerState_t *ps,int msec)
{
    const codol_ps_ext_t *state=CODOL_PlayerStateExtConst(ps);
    const codol_engine_table_t *table;
    float modifier;

    if(!state) {
        Com_Error(ERR_DROP,"CoDOL ADS playerState unavailable");
        return 0.0f;
    }
    if(!state->abilities_known ||
       !(state->abilities.masks[0]&UINT32_C(0x00200000)))
        return (float)msec;
    if(CODOL_LoadEngineStringTable("mp/coAbilityModifiersTable.csv",&table)!=1 ||
       CODOL_GetActiveAbilityValue(&state->abilities,table,10,&modifier)!=1) {
        Com_Error(ERR_DROP,"CoDOL ADS ability mapping unavailable");
        return 0.0f;
    }
    return (float)msec*modifier;
}

/* Live ADS/sway agreement trace.
 *
 * The sniper sway a scoped C1 player actually sees is drawn by 0x00423080
 * (reached from CG_PredictPlayerState 0x0050CD47 -> 0x004244C0), whose angle
 * comes from BG_GetSwayParams 0x00422FE0 -> BG_GetAdsSteadySwayAngle
 * 0x00422E20. That function keeps {lastAdsFrac, lastAmp, startTime} per
 * client at 0x016A07E8 (stride 12), clocks the ramp with ps->commandTime
 * (ps+0x00, read at 0x00422E75/0x00422EBB) and re-arms it on
 * ps+0x348 != 1.0f compared with fucomp -- exact float equality, no epsilon.
 * Its result is finally blended as def+0x6F0 + (amp - def+0x6F0) * ps+0x348
 * (0x00422FB7..0x00422FC3), so a single frame of ps+0x348 off exact 1.0f
 * both collapses the amplitude and steps the sine's phase velocity
 * (speed = def+0x6F8 + (def+0x6F4 - def+0x6F8) * ps+0x348, 0x0042301C).
 * 0x004230EF additionally reads pm_flags bit 0x40000000 to veto the prone
 * sway scale def+0x700.
 *
 * Everything on that list except the weapon definition is a playerstate word
 * this server publishes, so this prints the three of them that matter with
 * the fraction as raw float bits: 0x3f800000 is the only value that keeps the
 * ramp armed. A 12-bot lobby would drown the budget, so the trace latches
 * onto the first non-NA_BOT client and follows only that one. */
static void ads_sway_trace(const codol_pmove_c1_t *move,int state_known,int state,
                           int desired)
{
    static int traced=-1, lines, last_time[MAX_CLIENTS], last_valid[MAX_CLIENTS];
    static uint32_t last_bits[MAX_CLIENTS];
    const playerState_t *ps=move->ps;
    unsigned c=(unsigned)ps->clientNum;
    uint32_t bits; int delta, changed;
    if(!CODOL_TRACE_VERBOSE()) return;
    if(c>=MAX_CLIENTS) return;
    if(traced<0 && !CODOL_ClientIsBotClient(c)) traced=(int)c;
    if(traced!=(int)c || lines>=4000) return;
    memcpy(&bits,&ps->fWeaponPosFrac,sizeof(bits));
    /* An unresolved hand state is itself the event of interest: it is the
     * command C1 could always classify and this port could not. */
    changed=!last_valid[c] || bits!=last_bits[c] || !state_known;
    delta=last_valid[c] ? ps->commandTime-last_time[c] : 0;
    /* One line per transition plus a 250 ms heartbeat while off the hip, so a
     * stationary scoped player still shows the commandTime cadence. */
    if(!changed && (bits==0 || ps->commandTime-last_time[c]<250)) return;
    last_bits[c]=bits; last_time[c]=ps->commandTime; last_valid[c]=1; ++lines;
    {
        /* Every remaining input of C1 BG_PlayerCanAds 0x00418140 that this
         * port's gate also reads, so one scoped playtest separates "the ADS
         * button was not in the command" from "this server's gate refused it".
         * The 2026-09-16 in-match capture showed PMF_ADS_BUTTON|PMF_ADS
         * dropping for 3-5 commands at a time mid-scope with no other
         * playerstate word changing, and the client predicting the identical
         * fraction, so the divergence is in one of these four columns. */
        const struct WeaponDef *gd=BG_GetWeaponDef((ps->weapFlags&2) ?
            (unsigned)ps->offHandIndex : (unsigned)ps->weapon);
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL sway: c%u t%d dt%d msec %d posFrac %08x (%.7f) exact1 %d "
            "pmf 0x%08x dive%d eF 0x%x st%d/%d des%d w%u "
            "btn%d pof%d ads%d breath%d hbs %.4f\n",
            c,ps->commandTime,delta,move->local.msec,(unsigned)bits,
            (double)ps->fWeaponPosFrac,bits==UINT32_C(0x3f800000),
            (unsigned)ps->pm_flags,(ps->pm_flags&(int)C1_PMF_DIVE_TO_PRONE)?1:0,
            (unsigned)ps->eFlags&0x0cu,state_known,state,desired,(unsigned)ps->weapon,
            (move->cmd.buttons&C1_BUTTON_ADS)?1:0,(ps->otherFlags&0x1000)?1:0,
            (gd && gd->aimDownSight)?1:0,(ps->weapFlags&4)?1:0,
            (double)ps->holdBreathScale);
    }
}

/* C1 PM_UpdateAimDownSightLerp 0x4185a0. This owns the prediction-visible ADS
 * fraction. The retained IW3 copy is disabled in PM_Weapon below so one frame
 * can never integrate the fraction twice. */
static void update_ads_lerp_c1(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    const struct WeaponDef *def;
    codol_weapon_hand_t left;
    unsigned weapon=(ps->weapFlags&2) ? (unsigned)ps->offHandIndex : ps->weapon;
    unsigned state=0,left_state=0;
    int desired=0,ads_reload=0,state_known;
    float step;

    def=BG_GetWeaponDef(weapon);
    /* C1 0x418655..0x41867d reads the hand state out of ps+0x278 directly and
     * cannot fail to classify it; it zeroes the fraction only for +bc8 == 0
     * and for states 13/14/15. This port has to translate the retained
     * (weaponstate, weapAnim) pair first, and CODOL_ResolveEngineWeaponState
     * genuinely refuses some pairs (engine states 3/4 with an unlisted
     * animation, and everything outside its table). Folding that refusal into
     * the zeroing condition slammed fWeaponPosFrac to 0 for a single command
     * in the middle of a steady scope. Netfield 45 is published verbatim, and
     * C1 BG_GetAdsSteadySwayAngle 0x00422E20 re-arms its per-client ramp on
     * ps+0x348 != 1.0f tested with fucomp (exact equality), so one such frame
     * collapses the drawn ADS sway amplitude to zero and restarts the whole
     * +0x714 delay / +0x718 ramp: exactly the reported scope jitter.
     * An unclassifiable state now holds the fraction instead. */
    state_known=CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                               (unsigned)ps->weapAnim,&state);
    /* C1 0x004185c2 tests the turret pair FIRST -- ahead of the +0xbc8
     * aimDownSight gate at 0x00418655 and ahead of every hand-state test --
     * and lerps the fraction over dvar "210" milliseconds (default 250)
     * instead of snapping.  In the old order turret_minigun_mp's
     * aimDownSight == 0 zeroed the fraction for the whole mount and the
     * turret branch that used to sit below was unreachable, which is why the
     * mounted MG appeared to zoom instantaneously. */
    if(CODOL_TurretAdsLerp(ps,move->local.msec)) return;
    if(!def || !def->aimDownSight || (state_known && state>=13 && state<=15)) {
        ps->fWeaponPosFrac=0.0f;
        ps->adsDelayTime=0;
        goto trace;
    }
    if(!state_known) { ps->adsDelayTime=0; goto trace; }
    (void)CODOL_GetNativeWeaponAdsReload(def,&ads_reload);
    if(!ads_reload) {
        if(!def->bSegmentedReload) {
            if(state==8 && ps->weaponTime-def->iPositionReloadTransTime>0)
                desired=0;
            else desired=-1;
        } else if((state>=8 && state<=11) ||
                  (state==12 && ps->weaponTime-def->iPositionReloadTransTime>0))
            desired=0;
        else desired=-1;
    } else desired=-1;
    if(desired<0) {
        if(!def->bRechamberWhileAds && state==7) desired=0;
        else desired=(ps->pm_flags&0x10)!=0;
    }
    if(def->adsFireOnly &&
       ((ps->weaponDelay!=0 && state==6) ||
        (CODOL_WeaponStateHand(ps,1,&left) && left.delay!=0 &&
         CODOL_ResolveEngineWeaponState((unsigned)left.state,
                                        (unsigned)left.animation,&left_state) &&
         left_state==6)))
        desired=1;
    ps->adsDelayTime=0;
    if((desired && ps->fWeaponPosFrac==1.0f) ||
       (!desired && ps->fWeaponPosFrac==0.0f)) goto trace;
    step=ads_frame_msec_c1(ps,move->local.msec)*
         def->fOOPosAnimLength[desired ? 0 : 1];
    ps->fWeaponPosFrac+=desired ? step : -step;
    if(ps->fWeaponPosFrac<0.0f) ps->fWeaponPosFrac=0.0f;
    else if(ps->fWeaponPosFrac>1.0f) ps->fWeaponPosFrac=1.0f;
trace:
    ads_sway_trace(move,state_known,(int)state,desired);
}

static int sprint_weapon_blocked(const playerState_t *ps,int continuing)
{
    unsigned state;
    if(!CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                      (unsigned)ps->weapAnim,&state)) return 1;
    if(state>=13 && state<=21) return 1;
    return continuing && (state==29 || state==30);
}

static void sprint_stop(playerState_t *ps,int now,int button_held)
{
    ps->sprintState.sprintDelay=0;
    ps->sprintState.lastSprintEnd=now;
    ps->pm_flags&=~C1_PMF_SPRINTING;
    if(button_held) ps->sprintState.sprintButtonUpRequired=1;
}

static void sprint_start(playerState_t *ps,int now,int remaining)
{
    int duration;
    ps->sprintState.sprintStartMaxLength=remaining;
    ps->sprintState.lastSprintStart=now;
    ps->pm_flags|=C1_PMF_SPRINTING;
    /* C1 PM_SprintStart restarts animation record zero when a torso
     * animation is active. The retained sprint weapon phase remains owned by
     * PM_Weapon later in this same command. */
    if(ps->torsoAnim&~0x400) {
        ps->torsoAnim=(~ps->torsoAnim)&0x400;
        memcpy(&duration,CODOL_AnimationRecords+0x48,sizeof(duration));
        ps->torsoAnimDuration=duration+50;
    }
}

/* C1 PM_CanSprint 0x40f7a0 / continuing gate 0x40f810 and
 * PM_UpdateSprint 0x40f8f0. This owns all five sprintState fields; publishing
 * only the sprint flag made the client's meter/prediction replay commands. */
static void update_sprint(codol_pmove_c1_t *move,int now)
{
    playerState_t *ps=move->ps;
    sprintState_t *s=&ps->sprintState;
    unsigned buttons=move->cmd.buttons,flags=(unsigned)ps->pm_flags;
    int pressed=(buttons&C1_BUTTON_SPRINT)!=0;
    int active=(flags&C1_PMF_SPRINTING)!=0;
    int maximum,remaining,blocked;

    if(s->sprintButtonUpRequired && !pressed) s->sprintButtonUpRequired=0;
    if(ps->pm_type!=0 && ps->pm_type!=C1_PM_NORMAL_LINKED) {
        if(active) sprint_stop(ps,now,pressed);
        return;
    }

    if(active) {
        if((uint32_t)(now-s->lastSprintStart)>=(uint32_t)s->sprintStartMaxLength) {
            sprint_stop(ps,now,pressed);
            s->sprintDelay=1;
            return;
        }
        blocked=!(move->cmd.direction&1) ||
                !!(buttons&C1_SPRINT_BREAK_BUTTONS) ||
                !!(flags&C1_SPRINT_BREAK_FLAGS) || ps->leanf!=0.0f ||
                sprint_weapon_blocked(ps,1);
        if(blocked || (!(move->oldcmd.buttons&C1_BUTTON_SPRINT) && pressed))
            sprint_stop(ps,now,pressed);
        return;
    }

    if(s->sprintDelay && now-s->lastSprintEnd<CODOL_SprintRechargePauseMs(ps)) return;
    if(!pressed || (flags&0x00020000u) || s->sprintButtonUpRequired) return;
    blocked=!(move->cmd.direction&1) ||
            !!(buttons&C1_SPRINT_START_BUTTONS) ||
            !!(flags&C1_SPRINT_START_FLAGS) || ps->leanf!=0.0f;
    if(blocked) return;
    /* C1 PM_CanSprint 0x40f7d3 permits the jumping/expired-timer case before
     * its weapon-state rejection.  C1 ps+0x8 is pm_time, not groundEntityNum. */
    if(!((flags&0x2000u) && ps->pm_time==0) &&
       sprint_weapon_blocked(ps,0)) return;
    if((flags&3u) && !stance_clear(move->host,0)) return;
    maximum=BG_GetMaxSprintTime(ps);
    remaining=CODOL_GetSprintLeft(ps,now,maximum);
    if(remaining<=1000) return;
    sprint_start(ps,now,remaining);
}

/* C1 PM_DropTimers 0x00413cf0, including its exact jump/land clear mask. */
static void drop_timers(playerState_t *ps,const struct pml_t *pml)
{
    if(ps->pm_time) {
        if(pml->msec<ps->pm_time) ps->pm_time-=pml->msec;
        else {
            if(ps->pm_flags&0x2000) {
                ps->pm_flags&=~0x00402000u;
                ps->jumpOriginZ=0.0f;
            }
            ps->pm_flags&=0xffffde7fu;
            ps->pm_time=0;
        }
    }
    if(ps->legsTimer>0) { ps->legsTimer-=pml->msec;if(ps->legsTimer<0)ps->legsTimer=0; }
    if(ps->torsoTimer>0) { ps->torsoTimer-=pml->msec;if(ps->torsoTimer<0)ps->torsoTimer=0; }
}

/* C1 0x415fc0 / 0x418a60: hand states in which moving while prone does not
 * need the weapon interrupted. */
static int prone_move_idle_state(unsigned state)
{
    return state<=5 || state==8;
}
static int prone_move_interruptible_state(unsigned state)
{
    return state<=5 || (state>=7 && state<=12);
}
static int prone_move_blocking_state(unsigned state)
{
    return state==6 || (state>=13 && state<=21) || state==29 || state==30;
}

/* C1 PmoveSingle 0x4160bb..0x41627a. Prone input that starts moving drops
 * ADS (0x4161a2 -> 0x418ab0 -> 0x4183a0); pm_flags 0x200 survives only
 * while prone with an unscoped (or unraised scope) weapon that is busy. While
 * the view height is prone or last stand, holding ADS on a hip weapon, or on
 * a scoped weapon whose sight has not started to rise, locks locomotion.
 * Returns whether the view height is one of those two (the later 0x200 lock
 * at 0x41641b uses the same test). */
static int prone_move_filter_c1(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    unsigned saved=(unsigned)ps->pm_flags,first=0,second=0;
    int scoped=CODOL_WeaponScopeOverlayC1(ps->weapon);
    int clear=1,prone_view;
    if(saved&C1_PMF_PRONE) {
        if(!scoped || !(ps->fWeaponPosFrac>0.0f)) {
            int starts=((move->cmd.direction&3u) && !(move->oldcmd.direction&3u)) ||
                       ((move->cmd.direction&12u) && !(move->oldcmd.direction&12u));
            if(starts) {
                clear=0;
                if(c1_hand_state(ps,0,&first) && c1_hand_state(ps,1,&second) &&
                   !(!(prone_move_interruptible_state(first) &&
                       prone_move_interruptible_state(second)) &&
                     (prone_move_blocking_state(first) ||
                      prone_move_blocking_state(second)))) {
                    /* C1 0x418b5a additionally returns hand 0 to idle
                     * (0x41c1c0) outside the interruptible states; that
                     * reset belongs to the weapon state machine. */
                    ps->pm_flags&=~0x200;
                    PM_AddEvent(ps,EV_RESET_ADS);
                    ps->pm_flags&=~0x10;
                }
            } else if(saved&0x10) {
                clear=0;
            } else {
                clear=c1_hand_state(ps,0,&first) && c1_hand_state(ps,1,&second) &&
                      prone_move_idle_state(first) && prone_move_idle_state(second);
            }
        }
    }
    if(clear) ps->pm_flags=(int)(saved&~0x200u);
    prone_view=ps->viewHeightTarget==C1_VH_LASTSTAND ||
               ps->viewHeightTarget==C1_VH_PRONE;
    if(prone_view && (ps->pm_flags&0x10) &&
       (!scoped || ps->fWeaponPosFrac==0.0f))
        move->cmd.direction&=~15u;
    return prone_view;
}

/* C1 Pmove 0x416c40 hands PmoveSingle the raw command cmdNum-1 as oldcmd
 * (CG_PredictPlayerState 0x45f5b8 fetches it by number), including a command
 * whose millisecond equals its predecessor's that the server never executes.
 * Every received wire command is noted in arrival order; the one before the
 * command now executing is that command's oldcmd. */
static codol_usercmd_t c1_wire_last[MAX_CLIENTS],c1_wire_prev[MAX_CLIENTS];
static unsigned char c1_wire_last_valid[MAX_CLIENTS],c1_wire_prev_valid[MAX_CLIENTS];

void CODOL_PmoveC1NoteWireCommand(unsigned client,const codol_usercmd_t *command)
{
    if(client>=MAX_CLIENTS || !command) return;
    c1_wire_prev[client]=c1_wire_last[client];
    c1_wire_prev_valid[client]=c1_wire_last_valid[client];
    c1_wire_last[client]=*command;
    c1_wire_last_valid[client]=1;
}

static int wire_previous_for(unsigned client,const codol_usercmd_t *command,
                             codol_usercmd_t *out)
{
    if(client>=MAX_CLIENTS || !c1_wire_last_valid[client] ||
       !c1_wire_prev_valid[client] ||
       memcmp(&c1_wire_last[client],command,sizeof(*command)) ||
       (int32_t)(command->serverTime-c1_wire_prev[client].serverTime)<0) return 0;
    *out=c1_wire_prev[client];
    return 1;
}

/* ClientThink_real clamps the command time to level.time-1000..+200 before
 * Pmove, but the C1 mover used to run the raw command time: a client whose
 * clock ran ahead was simulated past the ceiling, and the next command was
 * then refused as old. Both now share one clock. The +200 ceiling stays (a
 * client must not run its clock ahead of the server) and is applied to the
 * C1 mover too; the -1000 floor is dropped for C1 commands because raising
 * this command's time would desynchronise it from the time the C1 mover
 * simulates, and C1's own 1000 ms retime (Pmove 0x416c7a) already bounds the
 * catch-up. */
static int c1_clock_ceiling[MAX_CLIENTS];
static uint32_t c1_clock_raw[MAX_CLIENTS];
static unsigned char c1_clock_valid[MAX_CLIENTS];

int CODOL_PmoveC1OwnsClientClock(const playerState_t *ps,usercmd_t *ucmd,int level_time)
{
    codol_usercmd_t command;
    unsigned client;
    if(!ps || !ucmd || !CODOL_PmoveC1Active()) return 0;
    if(ps->clientNum<0 || ps->clientNum>=(int)MAX_CLIENTS) return 0;
    client=(unsigned)ps->clientNum;
    c1_clock_valid[client]=0;
    if(!CODOL_ExecutedUsercmd(client,&command)) return 0;
    if((int)command.serverTime!=ucmd->serverTime) return 0;
    c1_clock_ceiling[client]=level_time+200;
    c1_clock_raw[client]=command.serverTime;
    c1_clock_valid[client]=1;
    /* Clock trace: how often each retained bound would have moved a C1
     * command, printed once a second while codol_debugTrace is on. */
    if(CODOL_TRACE_ON()) {
        static int last_ms,total,ahead,behind,worst_ahead,worst_behind;
        int delta=ucmd->serverTime-level_time;
        ++total;
        if(delta>200) { ++ahead; if(delta>worst_ahead) worst_ahead=delta; }
        if(delta< -1000) { ++behind; if(-delta>worst_behind) worst_behind=-delta; }
        if(level_time-last_ms>=1000 || level_time<last_ms) {
            if(last_ms)
                Com_Printf(CON_CHANNEL_SERVER,
                    "CoDOL clock: %d cmds, ceiling(+200) hit %d (worst +%d), "
                    "floor(-1000) would hit %d (worst -%d)\n",
                    total,ahead,worst_ahead,behind,worst_behind);
            last_ms=level_time; total=ahead=behind=worst_ahead=worst_behind=0;
        }
    }
    if(ucmd->serverTime>level_time+200) ucmd->serverTime=level_time+200;
    return 1;
}

int CODOL_PmoveC1Active(void)
{
    return (C1_PM_IMPLEMENTED&C1_PM_REQUIRED)==C1_PM_REQUIRED;
}
void CODOL_PmoveC1ResetClient(unsigned client)
{
    if(client>=MAX_CLIENTS) return;
    memset(c1_previous+client,0,sizeof(c1_previous[client]));
    c1_previous_valid[client]=0;
    c1_wire_last_valid[client]=c1_wire_prev_valid[client]=0;
}
void CODOL_PmoveC1ResetAll(void)
{
    memset(c1_previous,0,sizeof(c1_previous));
    memset(c1_previous_valid,0,sizeof(c1_previous_valid));
    memset(c1_wire_last_valid,0,sizeof(c1_wire_last_valid));
    memset(c1_wire_prev_valid,0,sizeof(c1_wire_prev_valid));
}

int CODOL_PmoveC1Try(struct pmove_t *pm)
{
    codol_pmove_c1_t move;
    codol_usercmd_t command,old_command;
    unsigned client;
    int final_time,next_time,msec,mantle_frame;
    unsigned pm_flags_before;
    int substep=0,prone_view;
    if(!pm || !pm->ps) return 0;
    /* Fetch the complete C1 word by execution ownership.  Timestamp matching
     * is deliberately absent: synchronous and spawn thinks retime the reduced
     * bookkeeping command after it is bound. */
    if(!CODOL_PmoveC1Active()) {
        if(pm->ps->clientNum>=0 && pm->ps->clientNum<(int)MAX_CLIENTS)
            CODOL_PmoveTraceFallback((unsigned)pm->ps->clientNum,
                                     pm->ps->commandTime,1);
        return 0;
    }
    client=(unsigned)pm->ps->clientNum;
    if(client>=MAX_CLIENTS) return 0;
    if(!CODOL_ExecutedUsercmd(client,&command)) {
        /* No CoDOL command word is bound to the command ClientThink is about
         * to run, so the RETAINED IW3 Pmove simulates it (ClientThink_real,
         * src/asmsource/_g_active_mp.asm:1748).  That is a different mover for
         * one whole command and shows up on the client as a discrete,
         * command-sized position disagreement. */
        CODOL_PmoveTraceFallback(client,pm->ps->commandTime,2);
        return 0;
    }
    /* C1 Pmove 0x416c40..0x416c6d filters the command once before chopping.
     * Preserve its stance buttons while frozen and clear locomotion for the
     * linked/control-lock otherFlag. */
    if((pm->ps->pm_flags&C1_PMF_REMOTE_CONTROLLING) ||
       (command.buttons&0x00200000u)) {
        command.buttons&=0x00080300u;
        command.direction=0;
    }
    if(CODOL_PlayerLinkFlags((int)client)&4u) {
        command.buttons&=0xfffffbf9u;
        command.direction=0;
    }
    /* The button word exactly as it arrived, before any of PmoveSingle's
     * filters touch it. The stance trace logs this beside the filtered copy so
     * "the request never reached the server" is separable from "the server
     * received it and decided against it". */
    codol_stance_wire_buttons[client]=command.buttons;
    final_time=(int)command.serverTime;
    /* The ClientThink_real future ceiling, shared with the retained clock. */
    if(c1_clock_valid[client] && c1_clock_raw[client]==command.serverTime &&
       final_time>c1_clock_ceiling[client])
        final_time=c1_clock_ceiling[client];
    c1_clock_valid[client]=0;
    if(final_time<=pm->ps->commandTime) return 1;
    /* C1 permits exactly 1000ms of catch-up before retiming the playerState
     * (0x416c7a..0x416c89). The former 200ms IW3 cap discarded valid C1
     * simulation time and amplified visible replay after a hitch. */
    if(final_time>pm->ps->commandTime+1000) pm->ps->commandTime=final_time-1000;
    /* The first substep's oldcmd is the raw command received just before
     * this one (C1 prediction 0x45f5b8), unfiltered and including a skipped
     * same-millisecond command; later substeps take the filtered chop below.
     * Without a paired wire command (bots, first command) fall back to the
     * filtered copy of the last executed command. A reset client starts with
     * C1's zero/default oldcmd.  Seeding oldcmd from the command being
     * executed suppresses its first jump, sprint and other rising edges.  If
     * playerState time was reset behind the sidecar, also discard that
     * future sidecar instead of replaying its buttons. */
    if(wire_previous_for(client,&command,&old_command)) {
        /* raw predecessor */
    } else if(c1_previous_valid[client] &&
       (int32_t)(command.serverTime-c1_previous[client].serverTime)>0) {
        old_command=c1_previous[client];
    } else {
        memset(&old_command,0,sizeof(old_command));
        old_command.serverTime=(uint32_t)pm->ps->commandTime;
    }
    pm->numtouch=0;
    while(pm->ps->commandTime<final_time) {
        memset(&move,0,sizeof(move));
        move.host=pm; move.ps=pm->ps; move.cmd=command; move.oldcmd=old_command;
        next_time=pm->ps->commandTime+66; if(next_time>final_time)next_time=final_time;
        move.cmd.serverTime=(uint32_t)next_time;
        msec=next_time-pm->ps->commandTime;
        move.local.msec=msec; move.local.frametime=(float)msec*0.001f;
        mantle_frame=0;
        pm_flags_before=(unsigned)move.ps->pm_flags;
        memcpy(move.local.previous_origin,move.ps->origin,sizeof(vec3_t));
        memcpy(move.local.previous_velocity,move.ps->velocity,sizeof(vec3_t));
        move.ps->commandTime=next_time;

        /* Populate the retained callback shell before the C1 pre-dispatch
         * producers. No movement state is translated through this shell. */
        pm->cmd.serverTime=next_time; pm->cmd.buttons=(int)move.cmd.buttons;
        pm->cmd.angles[0]=move.cmd.angles[0];
        pm->cmd.angles[1]=move.cmd.angles[1];
        pm->cmd.angles[2]=move.cmd.angles[2];
        pm->cmd.forwardmove=(move.cmd.direction&1)?127:(move.cmd.direction&2)?-127:0;
        pm->cmd.rightmove=(move.cmd.direction&4)?127:(move.cmd.direction&8)?-127:0;
        pm->cmd.meleeChargeYaw=move.cmd.meleeChargeYaw*(360.0f/65536.0f);
        pm->cmd.meleeChargeDist=move.cmd.meleeChargeDist;
        pm->oldcmd.buttons=(int)move.oldcmd.buttons;
        /* C1 0x41600b calls its animation-condition producer before any
         * PmoveSingle input filtering. */
        BG_AnimUpdatePlayerStateConditions(pm);
        CODOL_UpdateAnimConditionsFromPlayerState(move.ps->clientNum,move.ps);

        /* C1 PmoveSingle 0x416013..0x4160b8 filters the executing copy after
         * spread production and before view/movement. These are C1 bits; do
         * not translate them through retained IW3 movement state. */
        if(move.ps->pm_flags&0x00010000u)
            move.cmd.direction=(move.cmd.direction&~15u)|1u;
        {
            int halt=1;
            if(move.ps->pm_flags&C1_PMF_FROZEN) {
                /* 0x41606e also drops a pending reload request. */
                move.cmd.buttons&=0x00001300u;
                move.ps->weapFlags&=~1;
            } else if(move.ps->pm_flags&C1_PMF_RESPAWNED) {
                move.cmd.buttons&=0x00001301u;
            } else if(weapon_locks_stance_c1(move.ps)) {
                /* 0x416050: setting down ground equipment. */
                move.cmd.buttons&=0xfffffb3fu;
            } else if(!(move.ps->pm_flags&0x20000000u)) {
                halt=0;
            }
            if(halt) {
                /* 0x41607b */
                move.cmd.direction&=~15u;
                memset(move.ps->velocity,0,sizeof(vec3_t));
            }
        }
        if(move.cmd.buttons&0x10000000u) {
            move.cmd.buttons&=0x10001b02u;
            move.cmd.direction&=~15u;
        }
        if(move.ps->pm_flags&0x10000000u)
            move.cmd.buttons&=~1u;
        if(move.ps->pm_type>=C1_PM_DEAD)
            pm->tracemask&=0xfdffbfff;
        prone_view=prone_move_filter_c1(&move);
        update_predicted_weapon_eflags(&move);
        /* 0x4162dd, after the weapon eFlags read RESPAWNED. */
        if(move.ps->pm_type<C1_PM_DEAD &&
           !(move.cmd.buttons&(C1_BUTTON_PRONE|1u)))
            move.ps->pm_flags&=~C1_PMF_RESPAWNED;

        /* C1 0x4163af adjusts spread only after the filtered command and
         * local-frame timing exist, immediately before view-angle update. */
        pm->cmd.buttons=(int)move.cmd.buttons;
        pm->cmd.forwardmove=(move.cmd.direction&1)?127:(move.cmd.direction&2)?-127:0;
        pm->cmd.rightmove=(move.cmd.direction&4)?127:(move.cmd.direction&8)?-127:0;
        pm->oldcmd.buttons=(int)move.oldcmd.buttons;
        update_aim_spread_c1(&move);

        /* C1 command angles are already its native 16-bit turns. Frozen and
         * intermission states retain the authoritative view. */
        if(!(move.ps->pm_flags&C1_PMF_REMOTE_CONTROLLING) &&
           move.ps->pm_type!=C1_PM_INTERMISSION) {
            update_viewangles(&move);
        } else {
            move.cmd.buttons=0; move.cmd.direction=0;
        }
        AngleVectors(move.ps->viewangles,move.local.forward,move.local.right,move.local.up);

        /* C1 0x4163f0..0x41640f retains the backward flag while idle. It is
         * read before PM_DEAD removes the input. */
        if(move.cmd.direction&2) move.ps->pm_flags|=0x20;
        else if(move.cmd.direction&(1|4|8)) move.ps->pm_flags&=~0x20;

        /* C1 PmoveSingle clears actionable input for PM_DEAD and
         * PM_DEAD_LINKED before their normal/linked dispatch arms.  The
         * resulting state can keep falling, but never consumes a live C1
         * command after death. */
        if(move.ps->pm_type>=C1_PM_DEAD) {
            move.cmd.buttons=0;
            move.cmd.direction=0;
        }
        /* 0x41641b: the prone-move override flag holds locomotion while the
         * view height is prone or last stand. 0x416432: so does the 100 ms
         * after a dive ends (the dive itself keeps its steering input). */
        if(prone_view && (move.ps->pm_flags&0x200))
            move.cmd.direction&=~15u;
        if(CODOL_DiveLockoutActive(pm)) move.cmd.direction&=~15u;

        /* The filters above changed the native command after the shell was
         * first bound; keep retained weapon callbacks on the same input. */
        pm->cmd.buttons=(int)move.cmd.buttons;
        pm->cmd.forwardmove=(move.cmd.direction&1)?127:(move.cmd.direction&2)?-127:0;
        pm->cmd.rightmove=(move.cmd.direction&4)?127:(move.cmd.direction&8)?-127:0;
        pm->oldcmd.buttons=(int)move.oldcmd.buttons;

        /* C1 Mantle_ClearHint 0x41647a clears both transient hint bits before
         * animation conditions and the new mantle probe. */
        move.ps->mantleState.flags&=~0x18;

        /* C1 PmoveSingle 0x416abc dispatch.  Special modes do not pass
         * through the normal ground/mantle arm. */
        if(move.ps->pm_type==C1_PM_INTERMISSION) {
            c1_ladder_fall(move.ps);
            update_aim_down_sight_flag(&move);
            update_sprint(&move,next_time);
            update_ads_lerp_c1(&move);
        } else if(move.ps->pm_type==C1_PM_NOCLIP ||
                  move.ps->pm_type==C1_PM_UFO) {
            c1_ladder_fall(move.ps);
            move.ps->groundEntityNum=C1_ENTITYNUM_NONE;
            update_aim_down_sight_flag(&move);
            update_sprint(&move,next_time);
            update_ads_flag(&move);
            drop_timers(move.ps,&move.local);
            CODOL_PM_FreeMoveC1(&move);
            update_ads_lerp_c1(&move);
        } else if(move.ps->pm_type==C1_PM_SPECTATOR) {
            c1_ladder_fall(move.ps);
            update_aim_down_sight_flag(&move);
            update_sprint(&move,next_time);
            update_ads_flag(&move);
            CODOL_PM_UpdateStanceC1(pm,&move.local);
            sync_stance_command(&move);
            drop_timers(move.ps,&move.local);
            CODOL_PM_FreeMoveC1(&move);
            update_ads_lerp_c1(&move);
        } else if(move.ps->pm_type==C1_PM_NORMAL_LINKED ||
                  move.ps->pm_type==C1_PM_DEAD_LINKED) {
            c1_ladder_fall(move.ps);
            move.ps->groundEntityNum=C1_ENTITYNUM_NONE;
            if(!(move.ps->eFlags&0x00100000u))
                memset(move.ps->velocity,0,sizeof(vec3_t));
            update_aim_down_sight_flag(&move);
            update_sprint(&move,next_time);
            update_ads_flag(&move);
            drop_timers(move.ps,&move.local);
            CODOL_PM_UpdateStanceC1(pm,&move.local);
            sync_stance_command(&move);
        } else {
            if(!(move.ps->pm_flags&C1_PMF_MANTLE)) {
                update_aim_down_sight_flag(&move);
                update_sprint(&move,next_time);
                update_ads_flag(&move);
                CODOL_PM_UpdateStanceC1(pm,&move.local);
                sync_stance_command(&move);
                CODOL_PM_GroundTraceC1(&move);
            }
            CODOL_PM_CheckMantleC1(&move);
            if(CODOL_PM_C1MantleOwnsFrame(pm,&move.local)) {
                mantle_frame=1;
                /* C1 0x416859 intentionally reruns this producer sequence
                 * after mantle becomes active, then moves and returns. */
                update_aim_down_sight_flag(&move);
                update_sprint(&move,next_time);
                update_ads_flag(&move);
                CODOL_PM_UpdateStanceC1(pm,&move.local);
                sync_stance_command(&move);
                CODOL_PM_MantleMoveC1(&move);
            } else {
                /* C1 0x4168b3: after the mantle probe, before timers. */
                PM_UpdatePronePitch(pm,&move.local);
                drop_timers(move.ps,&move.local);
                /* C1 checks ladder after the stance/ground/mantle probe and
                 * before selecting ladder, walk or air movement. Checking it
                 * earlier can force stance from a stale surface contact. */
                CODOL_PM_CheckLadderC1(&move);
                /* C1 0x4168eb, before dive end and move selection. */
                PM_MeleeChargeUpdate(pm,&move.local);
                if(move.ps->pm_flags&C1_PMF_LADDER) {
                    if(c1_ladder_jump(&move))
                        CODOL_PM_NormalMoveC1(&move);
                    else {
                        CODOL_PM_LadderVelocityC1(&move);
                        CODOL_PM_LadderMoveC1(&move);
                    }
                } else if(move.ps->pm_flags&0x00010000u) {
                    CODOL_PM_MeleeChargeMoveC1(&move);
                } else {
                    /* C1 PM_WalkMove 0x00410914..0x00410932: the WALKING entry
                     * rewrites pm->cmd.rightmove in place while sprinting
                     * (ftol(rightmove * 0.667), constant 0xc85238) BEFORE
                     * PM_CheckJump, PM_CheckDive, PM_Friction and PM_CmdScale,
                     * and that reduced byte is what PM_Footsteps and PM_Weapon
                     * read afterwards.  PmoveSingle 0x00416941 reaches
                     * PM_AirMove directly for an airborne player, which never
                     * applies the reduction -- so it must live here, at the
                     * walk entry, and not inside the wish-direction producer.
                     */
                    if(move.local.walking && (move.ps->pm_flags&0x4000u))
                        pm->cmd.rightmove=(char)(int)
                            ((float)pm->cmd.rightmove*0.667f);
                    /* C1 PM_WalkMove checks jump first, then dive. Either
                     * launch takes ownership of this command before ordinary
                     * ground acceleration. */
                    if(CODOL_PM_CheckJumpC1(&move)) {
                        CODOL_DiveAirFrame(pm,&move.local);
                        CODOL_PM_AirMoveC1(&move);
                    } else if(CODOL_DiveGroundFrame(pm,&move.local)) {
                        sync_stance_command(&move);
                        CODOL_DiveAirFrame(pm,&move.local);
                        CODOL_PM_AirMoveC1(&move);
                    } else {
                        /* C1 0x41095f..0x410963 continues ground movement
                         * only when PM_CheckDive returns zero. */
                        sync_stance_command(&move);
                        CODOL_DiveAirFrame(pm,&move.local);
                        CODOL_PM_NormalMoveC1(&move);
                    }
                }
            }
        }
        /* C1 mantle arm calls PM_Weapon and returns at 0x416899; it never
         * reaches the ordinary final-ground/footstep tail. */
        if(!mantle_frame) CODOL_PM_FootstepsC1(&move,msec);
        /* Movement never re-enters retained Pmove.  Until hand 0 is moved out
         * of the retained weapon unit, run that unit directly so firing,
         * reload, offhand and ADS keep their existing server consequences.
         * Its CoDOL tail advances/publishes hand 1 exactly once. */
        if(move.ps->pm_type!=C1_PM_NOCLIP && move.ps->pm_type!=C1_PM_UFO &&
           move.ps->pm_type!=C1_PM_SPECTATOR &&
           move.ps->pm_type!=C1_PM_INTERMISSION) {
            codol_hold_breath_save_t breath;
            update_ads_lerp_c1(&move);
            /* C1 PM_Weapon 0x41dbfb: PM_UpdateVariableZoom 0x418480 runs
             * after the ADS lerp and before the hold-breath update. */
            CODOL_PM_UpdateVariableZoomC1(&move);
            /* C1 PM_Weapon calls PM_UpdateHoldBreath 0x4188b0 at 0x41dc02,
             * after the ADS lerp. The retained unit still runs IW3's own
             * hold-breath integration over the same words; capture them first
             * and let the C1 port recompute from that capture afterwards. */
            CODOL_HoldBreathSaveC1(move.ps,&breath);
            PM_Weapon(pm,&move.local);
            CODOL_PM_UpdateHoldBreathC1(&move,&breath);
        }
        /* C1 PmoveSingle 0x416662..0x41667b: after the linked arm's
         * PM_Weapon a dive still in flight is aborted. */
        if(move.ps->pm_type==C1_PM_NORMAL_LINKED &&
           (move.ps->pm_flags&C1_PMF_DIVE_TO_PRONE))
            CODOL_DiveLinkedAbort(pm);
        pm->xyspeed=(float)sqrt(move.ps->velocity[0]*move.ps->velocity[0]+
                               move.ps->velocity[1]*move.ps->velocity[1]);
        /* C1 Pmove 0x416cb0 copies the complete chopped cmd over oldcmd after
         * every PmoveSingle. Holding the previous network packet across all
         * substeps replays input edges when a command spans more than 66ms. */
        /* Prediction-divergence ring: keep this substep's inputs and result so
         * the client's own predictedOrigin for this commandTime can be
         * decomposed when it disagrees (src/codol/player/codol_pmove_trace.c).
         */
        if(CODOL_TRACE_ON())
            CODOL_PmoveTraceCommit(&move,move.local.previous_origin,msec,
                                   pm_flags_before,substep,
                                   move.ps->commandTime>=final_time);
        ++substep;
        old_command=move.cmd;
        pm->oldcmd=pm->cmd;
    }
    /* The next packet follows the command PmoveSingle actually executed.
     * Saving the raw packet command here resurrected buttons removed by the
     * frozen/respawn/dead/input-lock filters and replayed their edges across
     * packet boundaries. C1's outer Pmove preserves the final filtered copy. */
    c1_previous[client]=old_command; c1_previous_valid[client]=1;
    return 1;
}

/* C1 PmoveSingle 0x00416830..0x0041689D returns from the movement selection
 * after Mantle_Move.  PM_CheckLadder and PM_LadderMove are unreachable in that
 * frame. */
int CODOL_PM_C1MantleOwnsFrame(struct pmove_t *pm, struct pml_t *pml)
{
    if(!pm || !pm->ps || !pml) return 0;
    if(!(pm->ps->pm_flags&C1_PMF_MANTLE)) return 0;
    pm->ps->pm_flags&=~C1_PMF_LADDER;
    pm->ps->groundEntityNum=C1_ENTITYNUM_NONE;
    pml->walking=0;
    pml->groundPlane=0;
    pml->almostGroundPlane=0;
    return 1;
}

static void c1_ladder_fall(playerState_t *ps)
{
    if(ps->pm_flags&C1_PMF_LADDER)
        ps->pm_flags=(ps->pm_flags&~C1_PMF_LADDER)|C1_PMF_LADDER_FALL;
}

/* PM_LadderTraceBounds 0x00413170. */
static void c1_ladder_bounds(const codol_pmove_c1_t *move,
                             vec3_t mins, vec3_t maxs)
{
    float mid[3],half[3];
    unsigned i;
    for(i=0;i<3;++i) {
        mid[i]=(move->host->mins[i]+move->host->maxs[i])*0.5f;
        half[i]=(move->host->maxs[i]-move->host->mins[i])*0.5f;
    }
    half[0]-=C1_LADDER_XY_SHRINK;
    half[1]-=C1_LADDER_XY_SHRINK;
    mid[2]=(half[2]+mid[2]+C1_LADDER_Z_BASE)*0.5f;
    half[2]=mid[2]-C1_LADDER_Z_BASE;
    if(half[2]<0.0f) { mid[2]-=half[2]; half[2]=0.0f; }
    for(i=0;i<3;++i) { mins[i]=mid[i]-half[i]; maxs[i]=mid[i]+half[i]; }
}

static int c1_ladder_trace(codol_pmove_c1_t *move, const vec3_t direction,
                           float distance, trace_t *tr)
{
    vec3_t mins,maxs,end;
    unsigned i;
    c1_ladder_bounds(move,mins,maxs);
    for(i=0;i<3;++i) end[i]=move->ps->origin[i]+direction[i]*distance;
    memset(tr,0,sizeof(*tr));
    PM_playerTrace(move->host,tr,move->ps->origin,mins,maxs,end,
                   move->ps->clientNum,move->host->tracemask);
    return tr->fraction<1.0f && ((unsigned)tr->sflags&C1_SURF_LADDER);
}

/* C1 PM_CheckLadder 0x004153C0..0x00415658.  The second trace back along the
 * first hit's plane normal is essential: a nearby ladder-marked side cannot
 * attach the player unless that same face is reachable along its own normal. */
void CODOL_PM_CheckLadderC1(codol_pmove_c1_t *move)
{
    playerState_t *ps;
    trace_t first,proof;
    vec3_t forward,right,up,direction,back;
    float distance,length;
    int was_ladder;
    if(!move || !move->host || !(ps=move->ps)) return;
    was_ladder=(ps->pm_flags&C1_PMF_LADDER)!=0;
    if(move->local.walking) ps->pm_flags&=~C1_PMF_LADDER_FALL;
    if(ps->pm_time && !was_ladder && (ps->pm_flags&0x180)) return;
    if(ps->pm_type>=C1_PM_DEAD) {
        ps->groundEntityNum=C1_ENTITYNUM_NONE;
        move->local.walking=move->local.groundPlane=0;
        c1_ladder_fall(ps); return;
    }
    if(ps->pm_flags&C1_PMF_LADDER_FALL) return;
    if(ps->viewHeightTarget==C1_VH_LASTSTAND ||
       ps->viewHeightTarget==C1_VH_PRONE) { c1_ladder_fall(ps); return; }
    if((int)move->cmd.serverTime-ps->jumpTime<C1_LADDER_REGRAB_MS) {
        c1_ladder_fall(ps); return;
    }

    AngleVectors(ps->viewangles,forward,right,up);
    if(was_ladder && ps->groundEntityNum==C1_ENTITYNUM_NONE) {
        direction[0]=-ps->vLadderVec[0];
        direction[1]=-ps->vLadderVec[1];
        direction[2]=-ps->vLadderVec[2];
    } else {
        direction[0]=forward[0]; direction[1]=forward[1]; direction[2]=0.0f;
        length=(float)sqrt(direction[0]*direction[0]+direction[1]*direction[1]);
        if(length<=0.0f) { c1_ladder_fall(ps); return; }
        direction[0]/=length; direction[1]/=length;
    }
    distance=move->local.walking?C1_LADDER_GROUND_DIST:C1_LADDER_AIR_DIST;
    if(!c1_ladder_trace(move,direction,distance,&first)) {
        c1_ladder_fall(ps); return;
    }
    if(move->local.walking && !(move->cmd.direction&1)) {
        c1_ladder_fall(ps); return;
    }
    if(was_ladder) return;
    ps->vLadderVec[0]=first.normal[0];
    ps->vLadderVec[1]=first.normal[1];
    ps->vLadderVec[2]=first.normal[2];
    back[0]=-first.normal[0]; back[1]=-first.normal[1]; back[2]=-first.normal[2];
    if(!c1_ladder_trace(move,back,distance,&proof)) {
        c1_ladder_fall(ps); return;
    }
    ps->pm_flags|=C1_PMF_LADDER;
}

static float c1_dot(const vec3_t a,const vec3_t b)
{
    return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
}

static float c1_length(const vec3_t v)
{
    return (float)sqrt(c1_dot(v,v));
}

static void c1_cmd_axes(const codol_usercmd_t *cmd,float *forward,float *right)
{
    *forward=(cmd->direction&1)?127.0f:(cmd->direction&2)?-127.0f:0.0f;
    *right=(cmd->direction&4)?127.0f:(cmd->direction&8)?-127.0f:0.0f;
}

/* C1 PM_LadderMove 0x415741 calls PM_JumpStart, then
 * PM_LadderJumpOff 0x4094c0 and takes the air-move arm. */
static int c1_ladder_jump(codol_pmove_c1_t *move)
{
    playerState_t *ps=move->ps;
    vec3_t forward,out;
    float length,dot,vz;
    if(!(move->cmd.buttons&0x400u) || (move->oldcmd.buttons&0x400u) ||
       (int)move->cmd.serverTime-ps->jumpTime<500 || (ps->pm_flags&3)) return 0;
    ps->velocity[2]=(float)sqrt(2.0*(double)ps->gravity*39.0);
    ps->jumpTime=(int)move->cmd.serverTime;
    ps->jumpOriginZ=ps->origin[2];
    ps->pm_flags|=0x2000;
    ps->groundEntityNum=C1_ENTITYNUM_NONE;
    PM_AddEvent(ps,EV_JUMP);
    AngleVectors(ps->viewangles,forward,0,0);
    forward[2]=0.0f;
    length=c1_length(forward);
    if(length>0.0f) { forward[0]/=length; forward[1]/=length; }
    out[0]=forward[0]; out[1]=forward[1]; out[2]=0.0f;
    dot=c1_dot(ps->vLadderVec,forward);
    if(dot<0.0f) {
        out[0]-=2.0f*dot*ps->vLadderVec[0];
        out[1]-=2.0f*dot*ps->vLadderVec[1];
        length=(float)sqrt(out[0]*out[0]+out[1]*out[1]);
        if(length>0.0f) { out[0]/=length; out[1]/=length; }
    }
    vz=ps->velocity[2]*C1_LADDER_JUMPOFF_ZSCALE;
    ps->velocity[0]=out[0]*C1_LADDER_JUMPOFF_SPEED;
    ps->velocity[1]=out[1]*C1_LADDER_JUMPOFF_SPEED;
    ps->velocity[2]=vz;
    ps->pm_flags&=~C1_PMF_LADDER;
    move->local.walking=move->local.groundPlane=0;
    return 1;
}

/* PM_LadderMove 0x00415730 velocity producer.  Sliding remains owned by the
 * unfinished native slide component.  With no forward input this damps Z by
 * gravity*dt toward zero; it cannot manufacture the observed constant +95 Z. */
void CODOL_PM_LadderVelocityC1(codol_pmove_c1_t *move)
{
    playerState_t *ps;
    vec3_t forward,right,up,wish,push,lateral;
    float fm,rm,biggest,total,scale,t,k,wishspeed,pushlen,step;
    float along,drop,next,len;
    if(!move || !(ps=move->ps) || !(ps->pm_flags&C1_PMF_LADDER)) return;
    c1_cmd_axes(&move->cmd,&fm,&rm);
    AngleVectors(ps->viewangles,forward,right,up);
    t=(forward[2]+C1_LADDER_PITCH_BIAS)*C1_LADDER_PITCH_GAIN;
    if(t>1.0f)t=1.0f; else if(t< -1.0f)t=-1.0f;
    forward[2]=0.0f; len=c1_length(forward);
    if(len>0.0f) { forward[0]/=len; forward[1]/=len; }
    right[2]=0.0f; len=c1_length(right);
    if(len>0.0f) { right[0]/=len; right[1]/=len; }
    along=c1_dot(right,ps->vLadderVec);
    right[0]-=along*ps->vLadderVec[0];
    right[1]-=along*ps->vLadderVec[1];
    right[2]-=along*ps->vLadderVec[2];

    biggest=(float)fabs(fm)>(float)fabs(rm)?(float)fabs(fm):(float)fabs(rm);
    total=(float)sqrt(fm*fm+rm*rm);
    scale=total>0.0f?(float)ps->speed*biggest/(total*C1_CMDSCALE_DIVISOR):0.0f;
    wish[0]=wish[1]=wish[2]=0.0f;
    if(fm!=0.0f) wish[2]=t*C1_LADDER_CLIMB_SCALE*scale*fm;
    if(rm!=0.0f) {
        k=C1_LADDER_STRAFE_SCALE*scale*rm;
        wish[0]+=k*right[0]; wish[1]+=k*right[1]; wish[2]+=k*right[2];
    }
    wishspeed=c1_length(wish);
    if(wishspeed>0.0f) {
        push[0]=wish[0]-ps->velocity[0];
        push[1]=wish[1]-ps->velocity[1];
        push[2]=wish[2]-ps->velocity[2];
        pushlen=c1_length(push);
        if(pushlen>0.0f) {
            step=move->local.frametime*C1_LADDER_ACCELERATE*wishspeed;
            if(step>pushlen)step=pushlen;
            ps->velocity[0]+=push[0]/pushlen*step;
            ps->velocity[1]+=push[1]/pushlen*step;
            ps->velocity[2]+=push[2]/pushlen*step;
        }
    }
    if(fm==0.0f) {
        drop=(float)ps->gravity*move->local.frametime;
        if(ps->velocity[2]>0.0f) {
            ps->velocity[2]-=drop; if(ps->velocity[2]<0.0f)ps->velocity[2]=0.0f;
        } else if(ps->velocity[2]<0.0f) {
            ps->velocity[2]+=drop; if(ps->velocity[2]>0.0f)ps->velocity[2]=0.0f;
        }
    }
    if(rm==0.0f) {
        lateral[0]=right[0]; lateral[1]=right[1]; lateral[2]=0.0f;
        len=c1_length(lateral);
        if(len>0.0f) { lateral[0]/=len; lateral[1]/=len; }
        along=c1_dot(ps->velocity,lateral);
        drop=C1_LADDER_LATERAL_DAMP*move->local.frametime;
        next=along>0.0f?along-drop:along+drop;
        if((along>0.0f && next<0.0f)||(along<0.0f && next>0.0f))next=0.0f;
        ps->velocity[0]+=(next-along)*lateral[0];
        ps->velocity[1]+=(next-along)*lateral[1];
    }
    if(!move->local.walking) {
        /* C1 415a54..415a8d removes only the horizontal normal component. */
        along=ps->velocity[0]*ps->vLadderVec[0]+ps->velocity[1]*ps->vLadderVec[1];
        ps->velocity[0]-=along*ps->vLadderVec[0];
        ps->velocity[1]-=along*ps->vLadderVec[1];
        /* C1 415a90..415af0 skips a stationary player and compares vz^2
         * with vx^2+vy^2. The inward 50u/s push belongs to vertical climbing,
         * including the upper edge; the old near-zero-speed gate reversed it. */
        if((ps->velocity[0]!=0.0f || ps->velocity[1]!=0.0f || ps->velocity[2]!=0.0f) &&
           ps->velocity[2]*ps->velocity[2]>=
               ps->velocity[0]*ps->velocity[0]+ps->velocity[1]*ps->velocity[1]) {
            ps->velocity[0]-=ps->vLadderVec[0]*C1_LADDER_STICK_PUSH;
            ps->velocity[1]-=ps->vLadderVec[1]*C1_LADDER_STICK_PUSH;
        }
    }
}

codol_pmove_c1_mode_t CODOL_PM_C1SelectMove(codol_pmove_c1_t *move)
{
    if(!move || !move->host || !move->ps) return CODOL_PM_C1_MOVE_NORMAL;
    if(CODOL_PM_C1MantleOwnsFrame(move->host,&move->local))
        return CODOL_PM_C1_MOVE_MANTLE;
    CODOL_PM_CheckMantleC1(move);
    if(CODOL_PM_C1MantleOwnsFrame(move->host,&move->local))
        return CODOL_PM_C1_MOVE_MANTLE;
    CODOL_PM_CheckLadderC1(move);
    return (move->ps->pm_flags&C1_PMF_LADDER)?
        CODOL_PM_C1_MOVE_LADDER:CODOL_PM_C1_MOVE_NORMAL;
}

static float vh_eval(const c1_vh_key_t *keys, unsigned count, int pct)
{
    unsigned i;
    if(pct<=keys[0].pct) return keys[0].height;
    for(i=1;i<count;++i) {
        if(pct<=keys[i].pct) {
            /* C1 0x411c6e..0x411cbc: fidiv, stored as float, then the
             * height lerp on the x87 at double precision. */
            float t=(float)((double)(pct-keys[i-1].pct)/
                            (double)(keys[i].pct-keys[i-1].pct));
            return (float)(((double)keys[i].height-(double)keys[i-1].height)*
                           (double)t+(double)keys[i-1].height);
        }
    }
    return keys[count-1].height;
}

static int vh_duration(int target, int down)
{
    if(target==C1_VH_PRONE) return 400;
    if(target==C1_VH_CROUCH) return down ? 200 : 400;
    return 200;
}

static void vh_curve(const playerState_t *ps, const c1_vh_key_t **keys,
                     unsigned *count)
{
    if(ps->viewHeightLerpTarget==C1_VH_PRONE) {
        *keys=vh_prone; *count=sizeof(vh_prone)/sizeof(vh_prone[0]);
    } else if(ps->viewHeightLerpTarget==C1_VH_CROUCH && ps->viewHeightLerpDown) {
        *keys=vh_crouch_down;
        *count=sizeof(vh_crouch_down)/sizeof(vh_crouch_down[0]);
    } else if(ps->viewHeightLerpTarget==C1_VH_CROUCH) {
        *keys=vh_crouch_up;
        *count=sizeof(vh_crouch_up)/sizeof(vh_crouch_up[0]);
    } else {
        *keys=vh_stand; *count=sizeof(vh_stand)/sizeof(vh_stand[0]);
    }
}

/* C1 PM_ViewHeightAdjust 0x411d80..0x412168. */
void CODOL_PM_UpdateViewheightC1(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps;
    int target,pct=0,duration;
    float ftarget;
    const c1_vh_key_t *keys;
    unsigned count;
    if(!pm || !(ps=pm->ps) || !pml) return;
    target=ps->viewHeightTarget;

    /* 0x411d9d/0x411db2: no target, or a zero height, snaps. */
    if(!target || ps->viewHeightCurrent==0.0f) {
        ps->viewHeightCurrent=ps->pm_type==C1_PM_SPECTATOR ? 0.0f : (float)target;
        return;
    }
    ftarget=(float)target;
    if(ps->viewHeightCurrent==ftarget && !ps->viewHeightLerpTime) return;

    /* 0x411de2: heights off the curve set move linearly (180/s, or 120/s
     * with pm_flags 0x400000); with 0x400000 so do descents onto a curve
     * target. */
    if((target!=C1_VH_PRONE && target!=C1_VH_CROUCH && target!=C1_VH_STAND) ||
       ((ps->pm_flags&C1_PMF_VIEWHEIGHT_SLOW) && ps->viewHeightCurrent>ftarget)) {
        float rate=(ps->pm_flags&C1_PMF_VIEWHEIGHT_SLOW) ? 120.0f : 180.0f;
        float next;
        ps->viewHeightLerpTime=0;
        if(ps->viewHeightCurrent<ftarget) {
            next=(float)((double)pml->frametime*(double)rate+
                         (double)ps->viewHeightCurrent);
            ps->viewHeightCurrent=next<ftarget ? next : ftarget;
        } else {
            next=(float)((double)ps->viewHeightCurrent-
                         (double)pml->frametime*(double)rate);
            ps->viewHeightCurrent=next>ftarget ? next : ftarget;
        }
        return;
    }

    if(ps->viewHeightLerpTime) {
        duration=vh_duration(ps->viewHeightLerpTarget,ps->viewHeightLerpDown);
        pct=(pm->cmd.serverTime-ps->viewHeightLerpTime)*100/duration;
        if(pct<0) pct=0;
        if(pct>=100) {
            pct=100;
            ps->viewHeightCurrent=(float)ps->viewHeightLerpTarget;
            ps->viewHeightLerpTime=0;
        } else {
            vh_curve(ps,&keys,&count);
            ps->viewHeightCurrent=vh_eval(keys,count,pct);
        }
    }

    if(ps->viewHeightLerpTime) {
        /* 0x411f68..0x412065: the target moved against a running curve.
         * Reverse it from the mirrored progress instead of finishing it. */
        int lerp=ps->viewHeightLerpTarget,remaining;
        if(target==lerp) return;
        if(!((target<lerp && !ps->viewHeightLerpDown) ||
             (target>lerp && ps->viewHeightLerpDown))) return;
        remaining=100-pct;
        ps->viewHeightLerpDown^=1;
        if(ps->viewHeightLerpDown) {
            if(lerp==C1_VH_STAND) lerp=C1_VH_CROUCH;
            else if(lerp==C1_VH_CROUCH) lerp=C1_VH_PRONE;
        } else {
            if(lerp==C1_VH_PRONE) lerp=C1_VH_CROUCH;
            else if(lerp==C1_VH_CROUCH) lerp=C1_VH_STAND;
        }
        ps->viewHeightLerpTarget=lerp;
        if(remaining==100) {
            ps->viewHeightCurrent=(float)lerp;
            ps->viewHeightLerpTime=0;
            return;
        }
        duration=vh_duration(lerp,ps->viewHeightLerpDown);
        ps->viewHeightLerpTime=pm->cmd.serverTime-
            (int)((double)remaining*(double)0.01f*(double)duration);
        return;
    }

    /* 0x412066: start the next keyframe curve. */
    if(ps->viewHeightCurrent==ftarget) return;
    ps->viewHeightLerpTime=pm->cmd.serverTime;
    if(target==C1_VH_PRONE) {
        ps->viewHeightLerpDown=1;
        ps->viewHeightLerpTarget=40.0f<ps->viewHeightCurrent ?
            C1_VH_CROUCH:C1_VH_PRONE;
    } else if(target==C1_VH_CROUCH) {
        ps->viewHeightLerpDown=!(ps->viewHeightCurrent<=40.0f);
        ps->viewHeightLerpTarget=C1_VH_CROUCH;
    } else {
        ps->viewHeightLerpDown=0;
        ps->viewHeightLerpTarget=40.0f>ps->viewHeightCurrent ?
            C1_VH_CROUCH:C1_VH_STAND;
    }
}

static float stance_top(unsigned stance)
{
    return stance&C1_PMF_PRONE ? 30.0f :
           stance&C1_PMF_CROUCH ? 50.0f : 70.0f;
}

/* The point test of a taller stance hull at the feet (C1 0x40f250 from
 * PM_UpdateStance, mask tracemask & 0xfdffbfff). C1 reads only allsolid
 * (trace+0x28), which a point trace sets together with startsolid. */
static int stance_clear(struct pmove_t *pm, unsigned want)
{
    trace_t tr;
    vec3_t mins={-15.0f,-15.0f,0.0f},maxs={15.0f,15.0f,0.0f};
    int clear;
    maxs[2]=stance_top(want);
    memset(&tr,0,sizeof(tr));
    PM_playerTrace(pm,&tr,pm->ps->origin,mins,maxs,pm->ps->origin,
                   pm->ps->clientNum,pm->tracemask&~0x02004000);
    clear = !tr.allsolid;

    /* A refused stand-up is a hard, reproducible, localised failure -- worth
     * far more than a 0.03-unit median. The user reported being unable to leave
     * crouch/prone while standing on one puddle on mp_storm_spring.
     *
     * This is a POINT trace (start == end) of the WHOLE target hull measured
     * from the feet, so it fails either because something solid overlaps the
     * standing volume, or because the feet are already inside the floor. Those
     * two need different fixes, so the probe bisects them: re-run the identical
     * trace lifted by SURFACE_CLIP_EPSILON and by one unit. If a lift clears
     * it, the player is sunk by less than that much and the fault is where the
     * ground trace put them -- which is the same sign as the measured residual,
     * where the server always sits LOWER than the client. If no lift clears it,
     * the obstruction is real geometry and the surface flags name it. */
    if(!clear && CODOL_TRACE_ON()) {
        static int lines,last_ms[MAX_CLIENTS];
        unsigned c=(unsigned)pm->ps->clientNum;
        if(lines<200 && c<MAX_CLIENTS &&
           (pm->ps->commandTime-last_ms[c]>=500 || pm->ps->commandTime<last_ms[c])) {
            trace_t lift1,lift2,gnd,under; vec3_t o1,o2,gs,ge,us,ue; int i;
            vec3_t pad_min={-15.0f,-15.0f,0.0f},pad_max={15.0f,15.0f,0.0f};
            const char *hitmat,*gndmat,*undermat;
            float gndz,underz;
            last_ms[c]=pm->ps->commandTime; ++lines;
            for(i=0;i<3;++i) { o1[i]=pm->ps->origin[i]; o2[i]=pm->ps->origin[i]; }
            o1[2]+=0.125f; o2[2]+=1.0f;
            memset(&lift1,0,sizeof(lift1)); memset(&lift2,0,sizeof(lift2));
            PM_playerTrace(pm,&lift1,o1,mins,maxs,o1,pm->ps->clientNum,
                           pm->tracemask&~0x02004000);
            PM_playerTrace(pm,&lift2,o2,mins,maxs,o2,pm->ps->clientNum,
                           pm->tracemask&~0x02004000);
            /* Which surface would the engine put the player ON, asked from
             * above everything? A ground pad swept down from +64 to -32. If it
             * stops on the obstruction, the obstruction is sweep-solid and the
             * player belongs on top of it -- the feet are simply too low. If it
             * passes through to something lower while the position test at the
             * feet reports solid, then sweep and position disagree about the
             * same geometry, which is a different fault with a different fix.
             * Asking the engine is the point: our offline model of this
             * traversal has been wrong twice. */
            for(i=0;i<3;++i) { gs[i]=pm->ps->origin[i]; ge[i]=pm->ps->origin[i]; }
            gs[2]+=64.0f; ge[2]-=32.0f;
            memset(&gnd,0,sizeof(gnd));
            PM_playerTrace(pm,&gnd,gs,pad_min,pad_max,ge,pm->ps->clientNum,
                           pm->tracemask&~0x02004000);
            gndz=gs[2]+(ge[2]-gs[2])*gnd.fraction;
            /* And the underside of whatever is overhead: the same pad swept UP
             * from just above the feet. Its stopping height is the headroom the
             * player actually has, which the hull test only reports as a bit. */
            for(i=0;i<3;++i) { us[i]=pm->ps->origin[i]; ue[i]=pm->ps->origin[i]; }
            us[2]+=0.25f; ue[2]+=72.0f;
            memset(&under,0,sizeof(under));
            PM_playerTrace(pm,&under,us,pad_min,pad_max,ue,pm->ps->clientNum,
                           pm->tracemask&~0x02004000);
            underz=us[2]+(ue[2]-us[2])*under.fraction;
            /* trace_t.material points at the hit dmaterial_t, whose first field
             * is char[64] -- so this is the engine naming the surface itself,
             * not us decoding flags and inferring which material they imply. */
            hitmat=tr.material?tr.material:"(none)";
            gndmat=gnd.material?gnd.material:"(none)";
            undermat=under.material?under.material:"(none)";
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL stance blocked: c%u t%d want %u cur %u hull z %.1f..%.1f "
                "origin (%.3f %.3f %.3f) solid %d/%d frac %.4f hit %d/%d "
                "sf 0x%x cf 0x%x mat \"%s\" n (%.4f %.4f %.4f) | lift+0.125 solid %d/%d | "
                "lift+1.0 solid %d/%d | gnd %d vh %d | sweepdown z %.3f frac %.4f "
                "ss %d sf 0x%x cf 0x%x mat \"%s\" | sweepup z %.3f frac %.4f ss %d "
                "sf 0x%x cf 0x%x mat \"%s\"\n",
                c,pm->ps->commandTime,want,(unsigned)pm->ps->pm_flags&3u,
                (double)mins[2],(double)maxs[2],
                (double)pm->ps->origin[0],(double)pm->ps->origin[1],
                (double)pm->ps->origin[2],
                tr.startsolid,tr.allsolid,(double)tr.fraction,
                tr.hitType,(int)tr.hitId,(unsigned)tr.sflags,(unsigned)tr.cflags,
                hitmat,
                (double)tr.normal[0],(double)tr.normal[1],(double)tr.normal[2],
                lift1.startsolid,lift1.allsolid,lift2.startsolid,lift2.allsolid,
                pm->ps->groundEntityNum,pm->ps->viewHeightTarget,
                (double)gndz,(double)gnd.fraction,gnd.startsolid,
                (unsigned)gnd.sflags,(unsigned)gnd.cflags,gndmat,
                (double)underz,(double)under.fraction,under.startsolid,
                (unsigned)under.sflags,(unsigned)under.cflags,undermat);
        }
    }
    return clear;
}

static void stance_event_parm(playerState_t *ps,int event,unsigned parm)
{
    BG_AddPredictableEventToPlayerstate((BGEvent)event,(byte)parm,(gclient_t *)ps);
}

/* C1 keeps the hull as bounds (midpoint, half size) at pm+0xdc; every stance
 * hull is 30x30 from the feet up to this height. */
static void stance_hull(struct pmove_t *pm,float height)
{
    pm->mins[0]=pm->mins[1]=-15.0f; pm->mins[2]=0.0f;
    pm->maxs[0]=pm->maxs[1]=15.0f; pm->maxs[2]=height;
}

/* C1 0x409370: pm_flags 0x400000 with its timer run out, unless frozen. It
 * lets an airborne player go prone and forces prone 200 ms into that jump. */
static int c1_jump_prone_ready(const playerState_t *ps)
{
    if(ps->pm_flags&C1_PMF_FROZEN) return 0;
    return (ps->pm_flags&C1_PMF_VIEWHEIGHT_SLOW) && ps->pm_time==0;
}

/* C1 hand state as ps+0x278 + hand*0x1c holds it. A second hand that is not
 * dual wielding is published as zero (C1 0x4180ec). */
static int c1_hand_state(const playerState_t *ps,unsigned hand,unsigned *state)
{
    codol_weapon_hand_t second;
    if(!hand) return CODOL_ResolveEngineWeaponState((unsigned)ps->weaponstate,
                                                    (unsigned)ps->weapAnim,state);
    if(!CODOL_WeaponStateIsDualWielding(ps)) { *state=0; return 1; }
    if(!CODOL_WeaponStateHand(ps,1,&second)) return 0;
    return CODOL_ResolveEngineWeaponState((unsigned)second.state,
                                          (unsigned)second.animation,state);
}

static int weapon_requires_ground_c1(unsigned weapon)
{
    const struct WeaponDef *def=BG_GetWeaponDef((int)weapon);
    int value=0;
    return def && CODOL_GetNativeWeaponRequiresGround(def,&value)==1 && value;
}

/* C1 0x412270: while a ground-placed weapon (def+0xbe5) is being set down --
 * hand 0 in states 16..20 with that offhand, or either hand in state 6 with
 * that weapon -- neither stance nor locomotion may change. */
static int weapon_locks_stance_c1(const playerState_t *ps)
{
    unsigned first=0,second=0;
    if(!c1_hand_state(ps,0,&first)) return 0;
    if(first>=16 && first<21)
        return weapon_requires_ground_c1((unsigned)ps->offHandIndex);
    if(first!=6 && !(c1_hand_state(ps,1,&second) && second==6)) return 0;
    return ps->weapon && weapon_requires_ground_c1(ps->weapon);
}

/* C1 0x412210 -> 0x412170 -> BG_CheckProne 0x40d310 with the not-yet-prone
 * arguments: the held and the commanded weapon may forbid prone, an airborne
 * player may only drop into it from the 0x400000 state, and otherwise the
 * room/slope test decides. C1 writes the two pitch outputs into pmove locals. */
static int can_prone_c1(struct pmove_t *pm)
{
    playerState_t *ps=pm->ps;
    float torso=0.0f,waist=0.0f;
    if(CODOL_WeaponBlocksProneC1(ps->weapon) ||
       CODOL_WeaponBlocksProneC1(CODOL_UsercmdWeapon(&pm->cmd))) return 0;
    if(ps->pm_flags&C1_PMF_PRONE) return 1;
    if(ps->groundEntityNum==C1_ENTITYNUM_NONE && !c1_jump_prone_ready(ps)) return 0;
    return BG_CheckProne(ps->clientNum,ps->origin,pm->maxs[0],30.0f,ps->viewangles[1],
                         &torso,&waist,0,ps->groundEntityNum!=C1_ENTITYNUM_NONE,1,
                         pm->handler,0,50.0f);
}

/* C1 0x4122d0, run when the stance bits newly gain prone. Moving into prone
 * drops ADS; the origin is settled against the prone hull 10 units up and
 * back down; the body takes the view yaw and the ground pitch, and the torso
 * pitch is the ground pitch held within 45 degrees of the view pitch. */
static void prone_begin(struct pmove_t *pm)
{
    playerState_t *ps=pm->ps;
    trace_t tr;
    vec3_t top,end;
    int mask=pm->tracemask&~0x02004000;
    float pitch=0.0f,delta;
    unsigned i;
    if(pm->cmd.forwardmove || pm->cmd.rightmove) {
        ps->pm_flags&=~0x200;
        if((ps->pm_flags&C1_PMF_FROZEN) || !(ps->pm_flags&C1_PMF_VIEWHEIGHT_SLOW) ||
           ps->pm_time) {
            PM_AddEvent(ps,EV_RESET_ADS);
            ps->pm_flags&=~0x10;
        }
    }
    memcpy(end,ps->origin,sizeof(end)); end[2]=(float)((double)end[2]+10.0);
    memset(&tr,0,sizeof(tr));
    PM_playerTrace(pm,&tr,ps->origin,pm->mins,pm->maxs,end,ps->clientNum,mask);
    for(i=0;i<3;++i)
        top[i]=(float)(((double)end[i]-(double)ps->origin[i])*(double)tr.fraction+
                       (double)ps->origin[i]);
    memset(&tr,0,sizeof(tr));
    PM_playerTrace(pm,&tr,top,pm->mins,pm->maxs,ps->origin,ps->clientNum,mask);
    for(i=0;i<3;++i)
        ps->origin[i]=(float)((double)top[i]+
            ((double)ps->origin[i]-(double)top[i])*(double)tr.fraction);
    ps->proneDirection=ps->viewangles[1];
    memcpy(end,ps->origin,sizeof(end)); end[2]=(float)((double)end[2]-0.25);
    memset(&tr,0,sizeof(tr));
    PM_playerTrace(pm,&tr,ps->origin,pm->mins,pm->maxs,end,ps->clientNum,mask);
    if(!tr.startsolid && tr.fraction<1.0f)
        pitch=(float)PitchForYawOnNormal(ps->proneDirection,tr.normal);
    ps->proneDirectionPitch=pitch;
    delta=c1_norm180(pitch-ps->viewangles[0]);
    if(delta< -45.0f) ps->proneTorsoPitch=(float)((double)ps->viewangles[0]-45.0);
    else if(delta>45.0f) ps->proneTorsoPitch=(float)((double)ps->viewangles[0]+45.0);
    else ps->proneTorsoPitch=pitch;
}

/* C1 0x412fbd: a new stance keyframe restarts torso animation record zero. */
static void restart_torso_record_zero(playerState_t *ps)
{
    int duration;
    if(!(ps->torsoAnim&~0x400)) return;
    ps->torsoAnim=(~ps->torsoAnim)&0x400;
    memcpy(&duration,CODOL_AnimationRecords+0x48,sizeof(duration));
    ps->torsoAnimDuration=duration+50;
}

/* C1 0x412e42: the linked request path. Deny bits rewrite the command;
 * no clearance trace runs. */
static void stance_linked_c1(struct pmove_t *pm)
{
    playerState_t *ps=pm->ps;
    unsigned f=(unsigned)ps->pm_flags,b=(unsigned)pm->cmd.buttons;
    int event=0;
    if((f&(C1_PMF_DENY_STAND|C1_PMF_DENY_CROUCH)) || (b&C1_BUTTON_PRONE)) {
        if(b&C1_BUTTON_PRONE) {
            if(f&C1_PMF_DENY_PRONE) event=(f&C1_PMF_DENY_CROUCH) ? 6 : 7;
        } else if(b&C1_BUTTON_CROUCH) {
            if(f&C1_PMF_DENY_CROUCH) event=6;
        } else if(f&C1_PMF_DENY_STAND) event=7;
        if(event) {
            b&=~(C1_BUTTON_PRONE|C1_BUTTON_CROUCH);
            if(event==7) b|=C1_BUTTON_CROUCH;
            pm->cmd.buttons=(int)b;
            stance_event_parm(ps,event,0);
        }
    }
    f=(unsigned)ps->pm_flags&~3u;
    if(b&C1_BUTTON_PRONE) f|=C1_PMF_PRONE;
    else if(b&C1_BUTTON_CROUCH) f|=C1_PMF_CROUCH;
    ps->pm_flags=(int)f;
}

/* C1 0x412882: a script deny bit turns the request into the nearest
 * permitted stance and rewrites the command; with stand and crouch both
 * denied that is prone. */
static void stance_deny_c1(struct pmove_t *pm)
{
    playerState_t *ps=pm->ps;
    unsigned f=(unsigned)ps->pm_flags,b=(unsigned)pm->cmd.buttons;
    int event=0;
    if(!(f&(C1_PMF_DENY_STAND|C1_PMF_DENY_CROUCH|C1_PMF_DENY_PRONE))) return;
    if(b&C1_BUTTON_PRONE) {
        if(f&C1_PMF_DENY_PRONE)
            event=((f&3u) || (f&C1_PMF_DENY_STAND)) ?
                  ((f&C1_PMF_DENY_CROUCH) ? 6 : 7) : 6;
    } else if(b&C1_BUTTON_CROUCH) {
        if(f&C1_PMF_DENY_CROUCH)
            event=((f&3u) || (f&C1_PMF_DENY_PRONE)) ?
                  ((f&C1_PMF_DENY_STAND) ? 8 : 6) : 8;
    } else if(f&C1_PMF_DENY_STAND) {
        event=((f&C1_PMF_PRONE) && !(f&C1_PMF_DENY_PRONE)) ? 8 :
              ((f&C1_PMF_DENY_CROUCH) ? 8 : 7);
    }
    if(!event) return;
    b&=~(C1_BUTTON_PRONE|C1_BUTTON_CROUCH);
    if(event==8) b|=C1_BUTTON_PRONE;
    else if(event==7) b|=C1_BUTTON_CROUCH;
    pm->cmd.buttons=(int)b;
    stance_event_parm(ps,event,0);
}

/* C1 0x41295c..0x412de2: the ordinary request against the current stance.
 * Returns the branch for the stance trace. */
static int stance_request_c1(struct pmove_t *pm,int *blocked)
{
    playerState_t *ps=pm->ps;
    unsigned b=(unsigned)pm->cmd.buttons;
    int quiet=(b&C1_BUTTON_STANCE_HELD)!=0;
    *blocked=0;
    if((b&C1_BUTTON_PRONE) && !(ps->pm_flags&C1_PMF_RESPAWNED)) {
        if(can_prone_c1(pm)) {
            ps->pm_flags=(ps->pm_flags&~C1_PMF_CROUCH)|C1_PMF_PRONE;
            return 1;
        }
        *blocked=1;
        if(ps->groundEntityNum==C1_ENTITYNUM_NONE || quiet) return 2;
        /* 0x4129b0: C1 reports a refused prone as event 7 from crouch and
         * from prone alike, 6 from standing, all with reason 3. */
        stance_event_parm(ps,(ps->pm_flags&3) ? 7 : 6,3);
        return 2;
    }
    if(b&C1_BUTTON_CROUCH) {
        if(!(ps->pm_flags&C1_PMF_PRONE)) {
            ps->pm_flags|=C1_PMF_CROUCH;
            return 3;
        }
        stance_hull(pm,50.0f);
        if(stance_clear(pm,C1_PMF_CROUCH)) {
            ps->pm_flags=(ps->pm_flags&~C1_PMF_PRONE)|C1_PMF_CROUCH;
            return 3;
        }
        *blocked=1;
        if(!quiet) stance_event_parm(ps,8,2);
        return 3;
    }
    if(ps->pm_flags&C1_PMF_PRONE) {
        if(stance_clear(pm,0)) {
            ps->pm_flags&=~3;
            return 4;
        }
        stance_hull(pm,50.0f);
        if(stance_clear(pm,C1_PMF_CROUCH)) {
            ps->pm_flags=(ps->pm_flags&~C1_PMF_PRONE)|C1_PMF_CROUCH;
            return 4;
        }
        *blocked=1;
        if(!quiet) stance_event_parm(ps,8,1);
        return 4;
    }
    if(ps->pm_flags&C1_PMF_CROUCH) {
        if(stance_clear(pm,0)) {
            ps->pm_flags&=~C1_PMF_CROUCH;
            return 4;
        }
        *blocked=1;
        if(!quiet) stance_event_parm(ps,7,1);
    }
    return 4;
}

/* C1 PM_UpdateStance 0x412560..0x413165.
 *
 * The request only moves the stance bits; the view-height target then moves
 * one keyframe per completed curve (stand -> crouch -> prone, prone -> crouch
 * -> stand), and after PM_ViewHeightAdjust the stance bits, hull and stance
 * eFlags are all rederived from that target (0x412ffd..0x41313e). A stand to
 * prone request therefore publishes crouch bits while the first curve runs,
 * exactly as the client predicts it; prone entry runs only on the command in
 * which the rederived bits first gain prone. */
void REGPARM(2) CODOL_PM_UpdateStanceC1(struct pmove_t *pm, struct pml_t *pml)
{
    playerState_t *ps;
    unsigned previous,wire_prone;
    int was_prone,blocked=0,branch=0,change=0;
    if(!pm || !(ps=pm->ps) || !pml) return;
    pm->proneChange=0;
    previous=(unsigned)ps->pm_flags&3u;
    wire_prone=(unsigned)pm->cmd.buttons;

    if(ps->pm_type==C1_PM_SPECTATOR) {
        pm->mins[0]=pm->mins[1]=pm->mins[2]=-8.0f;
        pm->maxs[0]=pm->maxs[1]=8.0f; pm->maxs[2]=16.0f;
        ps->pm_flags&=~3;
        if(pm->cmd.buttons&C1_BUTTON_PRONE) {
            pm->cmd.buttons&=~C1_BUTTON_PRONE;
            stance_event_parm(ps,6,0);
        }
        ps->viewHeightTarget=0;
        ps->viewHeightCurrent=0.0f;
        return;
    }
    was_prone=(ps->pm_flags&C1_PMF_PRONE)!=0;
    stance_hull(pm,70.0f);
    if(ps->pm_type==C1_PM_DEAD) {
        ps->viewHeightTarget=8;
        CODOL_PM_UpdateViewheightC1(pm,pml);
        return;
    }
    /* 0x412696: sprinting, or riding (eFlags 0x100000 without otherFlags
     * 0x400000), stands at once and sets the target directly (0x4126c7). */
    if(((ps->pm_flags&C1_PMF_SPRINTING) ||
        ((ps->eFlags&0x00100000) && !(ps->otherFlags&0x00400000))) &&
       (ps->pm_flags&3)) {
        ps->viewHeightTarget=C1_VH_STAND;
        ps->eFlags&=~(C1_EF_CROUCH|C1_EF_PRONE);
        ps->pm_flags&=~3;
        stance_event_parm(ps,6,0);
        CODOL_PM_UpdateViewheightC1(pm,pml);
        return;
    }
    if(ps->eFlags&0x0c00) {
        /* 0x41272c: the turret pose owns the stance bits. */
        if((ps->eFlags&0x400) && !(ps->eFlags&0x800))
            ps->pm_flags=(ps->pm_flags&~C1_PMF_CROUCH)|C1_PMF_PRONE;
        else if((ps->eFlags&0x800) && !(ps->eFlags&0x400))
            ps->pm_flags=(ps->pm_flags&~C1_PMF_PRONE)|C1_PMF_CROUCH;
        else ps->pm_flags&=~3;
        branch=6;
    } else if(ps->pm_flags&0x0c00) {
        branch=7;                       /* 0x412776: respawned/frozen */
    } else if(weapon_locks_stance_c1(ps)) {
        branch=8;                       /* 0x412784 */
    } else if(ps->pm_type==C1_PM_NORMAL_LINKED || (ps->otherFlags&0x01000000)) {
        stance_linked_c1(pm);
        branch=9;
    } else if(ps->pm_type==C1_PM_LASTSTAND) {
        ps->pm_flags=(ps->pm_flags&~C1_PMF_CROUCH)|C1_PMF_PRONE;
        branch=2;
    } else if((ps->pm_flags&C1_PMF_DIVE_TO_PRONE) || CODOL_DiveLockoutActive(pm)) {
        /* 0x412de7: the dive owns prone and sets the target directly
         * (0x412e02); the movement input is left alone here. */
        ps->pm_flags=(ps->pm_flags&~C1_PMF_CROUCH)|C1_PMF_PRONE;
        pm->cmd.buttons=(pm->cmd.buttons&~C1_BUTTON_CROUCH)|C1_BUTTON_PRONE;
        ps->viewHeightTarget=C1_VH_PRONE;
        stance_event_parm(ps,8,0);
        branch=3;
    } else {
        if((ps->pm_flags&C1_PMF_LADDER) &&
           (pm->cmd.buttons&(C1_BUTTON_PRONE|C1_BUTTON_CROUCH))) {
            pm->cmd.buttons&=~(C1_BUTTON_PRONE|C1_BUTTON_CROUCH);
            stance_event_parm(ps,6,0);
        }
        /* 0x41281d: 200 ms into a 0x400000 jump the command is forced prone. */
        if(c1_jump_prone_ready(ps) && pm->cmd.serverTime-ps->jumpTime>200 &&
           !(pm->cmd.buttons&C1_BUTTON_PRONE)) {
            pm->cmd.buttons=(pm->cmd.buttons&~C1_BUTTON_CROUCH)|C1_BUTTON_PRONE;
            stance_event_parm(ps,8,0);
        }
        stance_deny_c1(pm);
        branch=10+stance_request_c1(pm,&blocked);
    }

    if(!ps->viewHeightLerpTime) {
        /* 0x412efd: advance the view-height target one keyframe. */
        if(ps->pm_type==C1_PM_LASTSTAND) {
            if(ps->viewHeightTarget!=C1_VH_LASTSTAND) {
                ps->viewHeightTarget=C1_VH_LASTSTAND; change=1;
            }
        } else if(ps->pm_flags&C1_PMF_PRONE) {
            if(ps->viewHeightTarget==C1_VH_STAND) ps->viewHeightTarget=C1_VH_CROUCH;
            else if(ps->viewHeightTarget!=C1_VH_PRONE) {
                ps->viewHeightTarget=C1_VH_PRONE;
                /* 0x412f65..0x412f7d Jump_ActivateSlowdown on crouch->prone. */
                if(!c1_jump_prone_ready(ps) && ps->pm_time==0) {
                    ps->pm_flags|=0x2000;
                    ps->pm_time=1800;
                }
                change=1;
            }
        } else {
            int from_last=ps->viewHeightTarget==C1_VH_LASTSTAND;
            if(ps->viewHeightTarget==C1_VH_PRONE) {
                ps->viewHeightTarget=C1_VH_CROUCH; change=1;
            } else {
                ps->viewHeightTarget=(ps->pm_flags&C1_PMF_CROUCH) ?
                    C1_VH_CROUCH : C1_VH_STAND;
                change=from_last;
            }
        }
        if(change) {
            pm->proneChange=1;
            restart_torso_record_zero(ps);
        }
    }

    CODOL_PM_UpdateViewheightC1(pm,pml);

    /* 0x413003..0x41313e: bits, hull and eFlags from the target. Last stand
     * keeps the crouch-height hull with the prone bits and prone eFlag. */
    switch(ps->viewHeightTarget) {
    case C1_VH_LASTSTAND:
        stance_hull(pm,50.0f);
        ps->eFlags=(ps->eFlags&~C1_EF_CROUCH)|C1_EF_PRONE;
        ps->pm_flags=(ps->pm_flags&~C1_PMF_CROUCH)|C1_PMF_PRONE;
        break;
    case C1_VH_CROUCH:
        stance_hull(pm,50.0f);
        ps->eFlags=(ps->eFlags&~C1_EF_PRONE)|C1_EF_CROUCH;
        ps->pm_flags=(ps->pm_flags&~C1_PMF_PRONE)|C1_PMF_CROUCH;
        break;
    case C1_VH_PRONE:
        stance_hull(pm,30.0f);
        ps->eFlags=(ps->eFlags&~C1_EF_CROUCH)|C1_EF_PRONE;
        ps->pm_flags=(ps->pm_flags&~C1_PMF_CROUCH)|C1_PMF_PRONE;
        break;
    default:
        stance_hull(pm,70.0f);
        ps->eFlags&=~(C1_EF_CROUCH|C1_EF_PRONE);
        ps->pm_flags&=~3;
        break;
    }

    /* The whole decision, for the stance trace: the wire button word, the
     * filtered copy, the arm that ran, whether a trace refused it, and the
     * view-height state that is published afterwards. */
    if(CODOL_TRACE_ON() && !CODOL_ClientIsBotClient((unsigned)ps->clientNum)) {
        static int lines,last_ms[MAX_CLIENTS]; static unsigned last_key[MAX_CLIENTS];
        unsigned c=(unsigned)ps->clientNum;
        unsigned effective=(unsigned)ps->pm_flags&3u;
        unsigned key=(wire_prone&0x1300u)|(previous<<16)|
                     ((unsigned)ps->viewHeightTarget<<20)|(effective<<28);
        if(c<MAX_CLIENTS && lines<400 &&
           (key!=last_key[c] || ps->commandTime-last_ms[c]>=250 ||
            ps->commandTime<last_ms[c])) {
            last_key[c]=key; last_ms[c]=ps->commandTime; ++lines;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL stance: c%u t%d wire 0x%08x cmd 0x%08x (crouch %d prone %d held %d) "
                "branch %d cur %u blocked %d eff %u change %d "
                "deny 0x%x pmf 0x%08x pmtype %d gnd %d vh cur %.1f tgt %d "
                "lerp %d/%d/%d origin (%.1f %.1f %.1f)\n",
                c,ps->commandTime,codol_stance_wire_buttons[c],
                (unsigned)pm->cmd.buttons,
                (pm->cmd.buttons&(int)C1_BUTTON_CROUCH)?1:0,
                (pm->cmd.buttons&(int)C1_BUTTON_PRONE)?1:0,
                (pm->cmd.buttons&(int)C1_BUTTON_STANCE_HELD)?1:0,
                branch,previous,blocked,effective,pm->proneChange,
                (unsigned)ps->pm_flags&0x03800000u,(unsigned)ps->pm_flags,
                ps->pm_type,ps->groundEntityNum,
                (double)ps->viewHeightCurrent,ps->viewHeightTarget,
                ps->viewHeightLerpTime,ps->viewHeightLerpTarget,
                ps->viewHeightLerpDown,
                (double)ps->origin[0],(double)ps->origin[1],(double)ps->origin[2]);
        }
    }

    if((ps->pm_flags&C1_PMF_PRONE) && !was_prone) prone_begin(pm);
}
#endif
