/* C1 PM_GroundTrace, friction, acceleration and step-slide movement.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 * Authority: C1.exe 0x0040FAD0..0x00411D70 and alpha0022/pmove.py.
 */
#ifdef CODOL_SERVER
#include "codol_pmove_c1_ground.h"
#include "codol_pmove_trace.h"
#include "codol_pain_state.h"
#include "codol_bot.h"
#include "qcommon_io.h"
#include "bg.h"
#include "bg_public.h"
#include "cvar.h"
#include "qcommon.h"
#include "q_math.h"
#include <math.h>
#include <string.h>

#define C1_ENTITYNUM_WORLD 2046
#define C1_ENTITYNUM_NONE 2047
#define C1_PMF_JUMPING 0x00002000u
#define C1_BUTTON_JUMP 0x00000400u
/* No C1_MIN_WALK_NORMAL: C1's ground trace has no such test (see below). */
#define C1_OVERCLIP 1.001f
#define C1_STEP_HEIGHT 18.0f
#define C1_PRONE_STEP_HEIGHT 10.0f
#define C1_GROUND_SNAP 9.0f
#define C1_JUMP_HEIGHT 39.0f
#define C1_FRICTION 5.5f
#define C1_STOPSPEED 100.0f
#define C1_GROUND_ACCEL 9.0f
#define C1_AIR_ACCEL 1.0f
#define C1_DUCK_ACCEL 12.0f
#define C1_PRONE_ACCEL 19.0f

extern void __cdecl PM_playerTrace(struct pmove_t *,trace_t *,const float *,
    const float *,const float *,const float *,int,int);
extern int16_t __cdecl Trace_GetEntityHitId(trace_t *trace);
extern void __cdecl PM_AddTouchEnt(struct pmove_t *pm,int entityNum);
extern void __cdecl PM_AddEvent(playerState_t *ps,int event);
extern int __cdecl BG_AnimScriptAnimation(playerState_t *ps,int state,int movetype,int force);
extern int __cdecl PM_ShouldMakeFootsteps(struct pmove_t *pm);
extern void __cdecl PM_FootstepEvent(struct pmove_t *pm,struct pml_t *pml,
    int old_cycle,int new_cycle,int make_footsteps);
extern const void *BG_GetShellshockParms(int index);
extern cvar_t *jump_slowdownEnable;
extern cvar_t *player_moveThreshhold;
extern cvar_t *player_dmgtimer_stumbleTime;
extern cvar_t *player_dmgtimer_flinchTime;
extern cvar_t *player_strafeAnimCosAngle;
extern cvar_t *player_turnAnims;
extern void __cdecl BG_SetConditionValue(int client,int condition,unsigned long long value);
extern float CODOL_DiveReduceFriction(struct pmove_t *,struct pml_t *);
extern void CODOL_DiveCrashLandDamage(const playerState_t *ps,float delta,int *damage);
extern int __cdecl BG_CheckProne(int,const vec3_t,float,float,float,float *,float *,
    unsigned char,unsigned char,unsigned char,unsigned char,int,float);

static float dot3(const vec3_t a,const vec3_t b)
{ return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
static float len3(const vec3_t v) { return (float)sqrt(dot3(v,v)); }
static void copy3(vec3_t d,const vec3_t s) { memcpy(d,s,sizeof(vec3_t)); }
static void add_event_param(playerState_t *ps,int event,unsigned parm);

static void trace_move(codol_pmove_c1_t *m,trace_t *tr,const vec3_t start,const vec3_t end)
{
    memset(tr,0,sizeof(*tr));
    PM_playerTrace(m->host,tr,start,m->host->mins,m->host->maxs,end,
                   m->ps->clientNum,m->host->tracemask);
}

static int correct_allsolid(codol_pmove_c1_t *m,trace_t *tr)
{
    static const signed char delta[26][3]={
        {0,0,1},{-1,0,1},{0,-1,1},{1,0,1},{0,1,1},
        {-1,0,0},{0,-1,0},{1,0,0},{0,1,0},{0,0,-1},
        {-1,0,-1},{0,-1,-1},{1,0,-1},{0,1,-1},
        {-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1},
        {-1,-1,0},{1,-1,0},{1,1,0},{-1,1,0},
        {-1,-1,-1},{1,-1,-1},{1,1,-1},{-1,1,-1}
    };
    vec3_t point,end;
    unsigned i;
    for(i=0;i<26;++i) {
        point[0]=m->ps->origin[0]+delta[i][0];
        point[1]=m->ps->origin[1]+delta[i][1];
        point[2]=m->ps->origin[2]+delta[i][2];
        trace_move(m,tr,point,point);
        if(!tr->startsolid) {
            copy3(m->ps->origin,point);
            copy3(end,point); end[2]-=1.25f;
            trace_move(m,tr,point,end);
            if(tr->startsolid) continue;
            m->ps->origin[0]=point[0]+(end[0]-point[0])*tr->fraction;
            m->ps->origin[1]=point[1]+(end[1]-point[1])*tr->fraction;
            m->ps->origin[2]=point[2]+(end[2]-point[2])*tr->fraction;
            return 1;
        }
    }
    return 0;
}

static void ground_trace_missed(codol_pmove_c1_t *m,int old_ground)
{
    trace_t tr;
    vec3_t end;
    float distance=old_ground==C1_ENTITYNUM_NONE?1.0f:64.0f;
    copy3(end,m->ps->origin); end[2]-=distance;
    trace_move(m,&tr,m->ps->origin,end);
    if(old_ground==C1_ENTITYNUM_NONE)
        m->local.almostGroundPlane=tr.fraction<1.0f;
    else
        m->local.almostGroundPlane=tr.fraction<(1.0f/64.0f);
    m->ps->groundEntityNum=C1_ENTITYNUM_NONE;
    m->local.walking=0;
    m->local.groundPlane=0;
}

/* Movement-visible part of C1 PM_CrashLand 0x411200.  Fall damage is carried
 * as the ordinary retained landing event so the existing C1 event boundary
 * performs the semantic ID conversion and server damage callback. */
static void crash_land(codol_pmove_c1_t *m)
{
    playerState_t *ps=m->ps;
    float v=m->local.previous_velocity[2];
    float a=-0.5f*(float)ps->gravity;
    float distance=m->local.previous_origin[2]-ps->origin[2];
    float disc=v*v-4.0f*a*distance;
    float time,impact,delta,scale;
    int damage=0,intensity=0,surface,event;
    unsigned parm;
    if(disc<0.0f || ps->gravity<=0) return;
    time=(-v-(float)sqrt((double)disc))/(2.0f*a);
    impact=v+time*(-(float)ps->gravity);
    delta=impact*impact/(2.0f*(float)ps->gravity);
    if(delta>128.0f && !(m->local.groundTrace.sflags&1) && ps->pm_type<8) {
        int maximum=(m->local.groundTrace.sflags&0x1000)?10:100;
        damage=delta>=300.0f ? maximum :
               (int)(((delta-128.0f)/(300.0f-128.0f))*(float)maximum);
        if(damage>maximum) damage=maximum;
    }
    if(delta>12.0f) {
        intensity=(int)(((delta-12.0f)/26.0f)*4.0f+4.0f);
        if(intensity>24) intensity=24;
    }
    if((ps->pm_flags&0x00400000u) && intensity>3) intensity=3;
    /* C1 0x41134b -> 0x408a00: a diving landing takes its damage from the
     * 65..200 dive fall band, replacing the ordinary result. */
    CODOL_DiveCrashLandDamage(ps,delta,&damage);
    surface=(m->local.groundTrace.sflags&0x2000)?0:
            (((unsigned)m->local.groundTrace.sflags>>20)&31u);
    if(damage>0) {
        if(damage<100 && !(m->local.groundTrace.sflags&2)) {
            ps->pm_time=damage*35+500;
            if(ps->pm_time>2000) ps->pm_time=2000;
            if(ps->pm_time<=500) scale=0.5f;
            else if(ps->pm_time>1500) scale=0.2f;
            else scale=0.5f-((float)(ps->pm_time-500)/1000.0f)*0.3f;
            ps->pm_flags|=0x80u;
        } else scale=0.6700000167f;
        ps->velocity[0]*=scale; ps->velocity[1]*=scale; ps->velocity[2]*=scale;
        event=EV_LANDING_PAIN_DEFAULT+surface;
        parm=(unsigned)damage|((m->local.groundTrace.sflags&0x1000)?0x80u:0u);
        add_event_param(ps,event,parm);
    } else if(delta>=12.0f) {
        ps->velocity[0]*=0.6700000167f;
        ps->velocity[1]*=0.6700000167f;
        ps->velocity[2]*=0.6700000167f;
        if(surface) add_event_param(ps,EV_LANDING_DEFAULT+surface,(unsigned)intensity);
    }
}

static int hit_entity(trace_t *tr)
{
    int n=(int)Trace_GetEntityHitId(tr);
    return n==C1_ENTITYNUM_NONE ? C1_ENTITYNUM_WORLD:n;
}

static void add_event_param(playerState_t *ps,int event,unsigned parm)
{
    BG_AddPredictableEventToPlayerstate((BGEvent)event,(byte)parm,(gclient_t *)ps);
}

/* C1 PM_StepSlideMove 0x417abe..0x417ad8 rejects a down trace only
 * when the collision type is ENTITY and its ID is below 19.  hitId is also
 * populated for dynent model/brush and glass hits, so testing the ID alone
 * falsely rolls movement back on those collision types. */
static int hit_player(trace_t *tr)
{
    return tr->hitType==TRACE_HITTYPE_ENTITY && tr->hitId<19;
}

/* C1 0x416d30..0x416ea5.  A failed prone-volume check cancels the step
 * slowdown and may roll the physical move back to its pre-step state. */
static int verify_prone_step(codol_pmove_c1_t *m,const vec3_t fallback_origin,
                             const vec3_t fallback_velocity)
{
    playerState_t *ps=m->ps;
    vec3_t velocity,angles={0.0f,0.0f,0.0f},forward;
    float length;
    if(!(ps->pm_flags&1)) return 1;
    if(BG_CheckProne(ps->clientNum,ps->origin,15.0f,30.0f,
                     ps->proneDirection,&ps->fTorsoPitch,&ps->fWaistPitch,
                     1,1,1,m->host->handler,0,50.0f)) return 1;
    if(ps->viewHeightTarget!=22) {
        copy3(ps->origin,fallback_origin);
        copy3(ps->velocity,fallback_velocity);
        return 0;
    }
    copy3(velocity,ps->velocity);
    length=len3(velocity);
    if(length>0.0f) {
        velocity[0]/=length; velocity[1]/=length; velocity[2]/=length;
        angles[1]=ps->proneDirection;
        AngleVectors(angles,forward,0,0);
        if(dot3(forward,velocity)>-0.5f) {
            copy3(ps->origin,fallback_origin);
            copy3(ps->velocity,fallback_velocity);
        }
    }
    return 0;
}

/* C1 PM_AirMove 0x410801..0x4108d6.  Movement can carry a prone hull into a
 * position where prone is no longer valid.  C1 changes it to crouch in the
 * same predicted command when the crouch hull fits. */
static void post_air_prone(codol_pmove_c1_t *m)
{
    playerState_t *ps=m->ps;
    trace_t tr;
    vec3_t mins={-15.0f,-15.0f,0.0f},maxs={15.0f,15.0f,50.0f};
    if(!(ps->pm_flags&1) || ps->pm_type>=7) return;
    if(BG_CheckProne(ps->clientNum,ps->origin,m->host->maxs[0],30.0f,
                     ps->viewangles[1],&ps->fTorsoPitch,&ps->fWaistPitch,
                     0,ps->groundEntityNum!=C1_ENTITYNUM_NONE,1,
                     m->host->handler,0,50.0f)) return;
    memset(&tr,0,sizeof(tr));
    PM_playerTrace(m->host,&tr,ps->origin,mins,maxs,ps->origin,
                   ps->clientNum,m->host->tracemask&~0x02004000);
    if(tr.allsolid) return;
    ps->pm_flags=(ps->pm_flags&~1)|2;
    ps->viewHeightTarget=40;
    PM_AddEvent(ps,EV_STANCE_FORCE_CROUCH);
}

/* C1 PM_GroundTrace starts 0.25 above the feet and ends 0.25 below. */
/* Fall probe: the frames where the player leaves the ground.
 *
 * The user falls through a snow drift when going prone and lands on the
 * rooftop clip lid 6-16 units below. The existing "CoDOL C1 move" line cannot
 * see it -- that one is throttled to 1/s AND requires movement input, and this
 * happens standing still in a couple of frames.
 *
 * What this has to separate:
 *   - the ground trace MISSED the drift entirely (fraction >= 1) -- the swept
 *     capsule passes through terrain the position test calls solid;
 *   - the ground trace FOUND it and rejected it, which is a fall through
 *     geometry the trace DID hit. RESOLVED 2026-09-17: it was this, via an
 *     extra normal[2] < 0.7 clause that C1 does not have. See the fix in
 *     CODOL_PM_GroundTraceC1 below. The probe is kept because it now
 *     verifies that fix: these departures should stop happening.
 * Those need different fixes, so the probe prints the fields that separate
 * them rather than the fact of the fall.
 *
 * Fires on a ground->airborne transition or a drop of more than half a unit,
 * then follows the next few frames so the velocity signature is visible:
 * gravity-only growth means a genuine fall rather than a reposition. */
static void ground_trace_c1_inner(codol_pmove_c1_t *m);

void CODOL_PM_GroundTraceC1(codol_pmove_c1_t *m)
{
    static float prev_z[MAX_CLIENTS];
    static int   prev_ground[MAX_CLIENTS], follow[MAX_CLIENTS], seen[MAX_CLIENTS];
    static int   lines;
    playerState_t *ps;
    unsigned slot;
    float z0; int g0;

    if(!m || !m->host || !(ps=m->ps)) { ground_trace_c1_inner(m); return; }
    slot=(unsigned)ps->clientNum;
    if(slot>=MAX_CLIENTS || !CODOL_TRACE_ON()) { ground_trace_c1_inner(m); return; }

    z0=ps->origin[2]; g0=ps->groundEntityNum;
    ground_trace_c1_inner(m);

    if(!seen[slot]) { seen[slot]=1; prev_z[slot]=z0; prev_ground[slot]=g0; }
    if((prev_ground[slot]!=C1_ENTITYNUM_NONE &&
        ps->groundEntityNum==C1_ENTITYNUM_NONE) ||
       prev_z[slot]-ps->origin[2] > 0.5f)
        follow[slot]=10;

    if(follow[slot]>0 && lines<400) {
        const trace_t *tr=&m->local.groundTrace;
        --follow[slot]; ++lines;
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL fall: c%u t%d stance %u origin (%.3f %.3f %.3f) dz %+.3f "
            "vz %+.2f gnd %d<-%d walk %d gp %d frac %.4f ss %d/%d "
            "walkable %d nz %.4f hit %d/%d sf 0x%x cf 0x%x mat \"%s\" vht %d\n",
            slot,ps->commandTime,(unsigned)ps->pm_flags&3u,
            (double)ps->origin[0],(double)ps->origin[1],(double)ps->origin[2],
            (double)(ps->origin[2]-prev_z[slot]),(double)ps->velocity[2],
            ps->groundEntityNum,prev_ground[slot],
            m->local.walking,m->local.groundPlane,
            (double)tr->fraction,tr->startsolid,tr->allsolid,
            (int)tr->walkable,(double)tr->normal[2],
            tr->hitType,(int)tr->hitId,(unsigned)tr->sflags,(unsigned)tr->cflags,
            tr->material?tr->material:"(none)",ps->viewHeightTarget);
    }
    prev_z[slot]=ps->origin[2];
    prev_ground[slot]=ps->groundEntityNum;
}

static void ground_trace_c1_inner(codol_pmove_c1_t *m)
{
    vec3_t start,end;
    trace_t tr;
    playerState_t *ps;
    int old_ground,entity;
    if(!m || !m->host || !(ps=m->ps)) return;
    old_ground=ps->groundEntityNum;
    copy3(start,ps->origin); copy3(end,ps->origin);
    if(ps->eFlags&0x00000c00u) end[2]-=1.0f;
    else { start[2]+=0.25f; end[2]-=0.25f; }
    trace_move(m,&tr,start,end);
    m->local.groundTrace=tr;
    m->local.walking=0; m->local.groundPlane=0; m->local.almostGroundPlane=0;
    if(tr.allsolid && !correct_allsolid(m,&tr)) {
        ps->groundEntityNum=C1_ENTITYNUM_NONE;
        ps->jumpOriginZ=0.0f;
        ps->pm_flags&=~0x00402000u;
        return;
    }
    if(tr.startsolid) {
        copy3(start,ps->origin); start[2]-=0.001f;
        trace_move(m,&tr,start,end);
        m->local.groundTrace=tr;
        if(tr.startsolid) { ps->groundEntityNum=C1_ENTITYNUM_NONE; return; }
    }
    m->local.groundTrace=tr;
    if(tr.fraction>=1.0f) {
        ground_trace_missed(m,old_ground); return;
    }
    m->local.groundPlane=1;
    if(!(ps->pm_flags&8) && ps->velocity[2]>0.0f &&
       dot3(ps->velocity,tr.normal)>10.0f) {
        m->local.groundPlane=0;
        m->local.almostGroundPlane=0;
        ps->groundEntityNum=C1_ENTITYNUM_NONE; return;
    }
    /* C1 PM_GroundTrace 0x00411b66:
     *     cmp byte [ebp-0x1e], 0        ; trace(ebp-0x48)+0x2a = walkable
     *     je  reject
     *     cmp dword [ebp-0x34], 0x2000000 ; trace+0x14 = cflags
     *     je  reject
     * There is NO normal[2] comparison. The only float constants C1's
     * whole ground region (0x40f000..0x412000) compares against are
     * 0.001, 10, 12, 0.015625 and surface-type lookup values -- 0.7f
     * appears nowhere in it. Walkability is decided INSIDE the trace and
     * arrives as trace->walkable; testing normal[2] again here was a
     * second, stricter gate this port invented.
     *
     * It is what drops the player through the snow on mp_storm_spring:
     * measured departures reported walkable 1 with normal[2] 0.39..0.66,
     * i.e. surfaces the engine had already accepted and we then refused.
     * The reported normals are correct -- the triangle at the first
     * departure computes |nz| 0.6414 against a trace-reported 0.6414 --
     * so this is not a normals bug, it is an extra clause.
     *
     * C1's reject path (0x00411bc6) is one path with fixed effects:
     * walking=0, groundPlane=1, almostGroundPlane=1, jumpOriginZ=0,
     * pm_flags &= 0xffbfdfff. The cflags test is a second way INTO it,
     * not a modifier, so the groundPlane=0 variant goes too. (pml_t
     * offsets confirmed by the trace copy at 0x00411a33: edi+0x38.) */
    if(!tr.walkable || tr.cflags==0x02000000) {
        m->local.groundPlane=1;
        m->local.almostGroundPlane=1;
        ps->jumpOriginZ=0.0f;
        ps->pm_flags&=~0x00402000u;
        ps->groundEntityNum=C1_ENTITYNUM_NONE;
        return;
    }
    m->local.walking=1;
    m->local.almostGroundPlane=1;
    if(old_ground==C1_ENTITYNUM_NONE) crash_land(m);
    entity=hit_entity(&tr);
    ps->groundEntityNum=entity;
    if(entity!=C1_ENTITYNUM_WORLD) PM_AddTouchEnt(m->host,entity);
}

static void clip_velocity(const vec3_t in,const vec3_t normal,vec3_t out)
{
    float backoff=dot3(in,normal);
    /* C1 PM_ClipVelocity 0x40f403: subtract exactly one thousandth of the
     * absolute projection.  Division by 1.001 is close but diverges after
     * the repeated floor clips used by prediction. */
    backoff-=(float)fabs(backoff)*0.001f;
    out[0]=in[0]-normal[0]*backoff;
    out[1]=in[1]-normal[1]*backoff;
    out[2]=in[2]-normal[2]*backoff;
}

static void project_velocity(const vec3_t in,const vec3_t normal,vec3_t out)
{
    float d2,new_z,denom,scale;
    copy3(out,in);
    d2=in[0]*in[0]+in[1]*in[1];
    if((float)fabs(normal[2])<0.001f || d2==0.0f) return;
    new_z=-(normal[0]*in[0]+normal[1]*in[1])/normal[2];
    denom=new_z*new_z+d2; if(denom==0.0f) return;
    scale=(float)sqrt((in[2]*in[2]+d2)/denom);
    if(scale<1.0f || new_z<0.0f || in[2]>0.0f) {
        out[0]=in[0]*scale; out[1]=in[1]*scale; out[2]=new_z*scale;
    }
}

static void friction(codol_pmove_c1_t *m)
{
    playerState_t *ps=m->ps;
    float speed,control,drop=0.0f,next,scale;
    speed=m->local.walking?(float)sqrt(ps->velocity[0]*ps->velocity[0]+
        ps->velocity[1]*ps->velocity[1]):len3(ps->velocity);
    if(speed<1.0f) {
        ps->velocity[0]=ps->velocity[1]=ps->velocity[2]=0.0f;
        return;
    }
    if(ps->pm_flags&0x00010000u) {
        if(ps->meleeChargeTime>0)
            drop=speed/((float)ps->meleeChargeTime*0.001f)*m->local.frametime;
    } else if(m->local.walking && !(m->local.groundTrace.sflags&2) &&
              !(ps->pm_flags&0x100)) {
        control=speed<C1_STOPSPEED?C1_STOPSPEED:speed;
        /* C1 PM_Friction 0x0040fb70 `test cl,cl / jns` reads the SIGN of the
         * LOW BYTE of pm_flags, i.e. PMF_LANDED (0x80) -- the bit PM_CrashLand
         * 0x00411200 sets and PM_CheckJump 0x00409630 clears with ~0x180. This
         * port tested 0x80000000, so a landed player kept full ground friction
         * on the server while C1's client applied 0.3 (0xc84c50), and the two
         * origins diverged for the whole post-landing window. */
        if(ps->pm_flags&0x80u) control*=0.3000000119f;
        else if(ps->pm_flags&C1_PMF_JUMPING) {
            if(ps->pm_time>1800) {
                ps->pm_flags&=~0x00402000u;
                ps->jumpOriginZ=0.0f;
            } else if((!jump_slowdownEnable || jump_slowdownEnable->boolean) &&
                      !(ps->pm_flags&0x00400000u)) {
                control*=ps->pm_time<1700 ?
                    (float)ps->pm_time*1.5f*0.00058823527f+1.0f : 2.5f;
            }
        }
        if(ps->pm_flags&0x40000000u)
            control*=CODOL_DiveReduceFriction(m->host,&m->local);
        drop+=control*C1_FRICTION*m->local.frametime;
    }
    if(ps->pm_type==5) drop+=speed*5.0f*m->local.frametime;
    next=speed-drop;
    if(next<0.0f)next=0.0f;
    scale=next/speed;
    ps->velocity[0]*=scale; ps->velocity[1]*=scale; ps->velocity[2]*=scale;
}

static void accelerate(codol_pmove_c1_t *m,const vec3_t dir,float speed,float accel)
{
    float add=speed-dot3(m->ps->velocity,dir),step;
    if(add<=0.0f)return;
    /* C1 PM_Accelerate 0x0040fc91: frametime * accel * max(wishspeed,100). */
    step=m->local.frametime*accel*(speed<100.0f?100.0f:speed);
    if(step>add)step=add;
    m->ps->velocity[0]+=dir[0]*step;
    m->ps->velocity[1]+=dir[1]*step;
    m->ps->velocity[2]+=dir[2]*step;
}

/* C1 PM_GetStanceIndex 0x0040f570: the stance a movement constant is chosen
 * with is ps->viewHeightTarget, NOT the prone/crouch pm_flags bits or pm_type.
 *   22 -> 3, 40 -> 2, 11 -> 1, anything else -> 0
 * Both PM_CmdScale's stance multiplier (0x0040ff70 tail, 0x00410094/86/78) and
 * PM_WalkMove's acceleration table (0x00410a63) index with it. */
static int c1_stance_index(const playerState_t *ps)
{
    if(ps->viewHeightTarget==22) return 3;
    if(ps->viewHeightTarget==40) return 2;
    return ps->viewHeightTarget==11 ? 1 : 0;
}

static float command_scale(codol_pmove_c1_t *m,float f,float r)
{
    const struct WeaponDef *weapon;
    float fs=f<0.0f?f*0.7f:f,rs=r*0.8f;
    float biggest=(float)fabs(fs)>(float)fabs(rs)?(float)fabs(fs):(float)fabs(rs);
    float total=(float)sqrt(f*f+r*r),stance=1.0f,scale,frac;
    int ads_weapon;
    if(total<=0.0f)return 0.0f;
    if(m->ps->viewHeightLerpTime && m->ps->viewHeightLerpTarget==11) {
        frac=((float)(m->ps->commandTime-m->ps->viewHeightLerpTime))/400.0f;
        if(frac>0.0f) { if(frac>1.0f)frac=1.0f; stance=frac*0.15f+(1.0f-frac)*0.65f; }
        else if(m->ps->pm_flags&1) stance=0.15f;
        else if(m->ps->pm_flags&2) stance=0.65f;
    } else if(m->ps->viewHeightLerpTime && m->ps->viewHeightLerpTarget==40 &&
              !m->ps->viewHeightLerpDown && m->ps->commandTime>m->ps->viewHeightLerpTime) {
        frac=((float)(m->ps->commandTime-m->ps->viewHeightLerpTime))/400.0f;
        if(frac>1.0f)frac=1.0f;
        stance=(1.0f-frac)*0.15f+frac*0.65f;
    } else {
        /* C1 0x0040f570 fallback: 11 -> 0.15 (0xc30c00), 40 -> 0.65
         * (0xc847dc), 22 -> 0.2 (0xc843ec), otherwise 1.0. */
        static const float by_stance[4]={1.0f,0.15f,0.65f,0.2f};
        stance=by_stance[c1_stance_index(m->ps)];
    }
    scale=(float)m->ps->speed*biggest/(127.0f*total);
    /* C1 PM_CmdScale 4100c1..4100dc and 41018e..4101c7.  Weapon ADS
     * movement starts when PMF_ADS is set, or while a prone player has a
     * nonzero ADS fraction. Lean applies the 0.4 movement penalty but keeps
     * the hip weapon scale. Raw fWeaponPosFrac alone is not the selector. */
    ads_weapon=(m->ps->pm_flags&0x40) ||
               ((m->ps->pm_flags&1) && m->ps->fWeaponPosFrac>0.0f);
    if(ads_weapon || m->ps->leanf!=0.0f) scale*=0.4f;
    if(m->ps->pm_flags&0x4000) scale*=1.5f;
    if(m->ps->pm_type==2) scale*=3.0f;
    else if(m->ps->pm_type==3) scale*=6.0f;
    else scale*=stance;
    weapon=BG_GetWeaponDef(m->ps->weapon);
    if(CODOL_TRACE_ON())
        CODOL_PmoveTraceScale(m->ps->clientNum,weapon?weapon->moveSpeedScale:-1.0f,
                              weapon?weapon->adsMoveSpeedScale:-1.0f,ads_weapon);
    if(weapon) {
        if(!ads_weapon && weapon->moveSpeedScale>0.0f)
            scale*=weapon->moveSpeedScale;
        else if(weapon->adsMoveSpeedScale>0.0f)
            scale*=weapon->adsMoveSpeedScale;
    }
    /* C1 PM_CmdScale 410273..410299 applies the shellshock movement setting
     * after the weapon scale and before ps+254. The retained shellshock table
     * has the same 0x268-byte record and movement byte at +0x264. sh1x stores
     * C1 PMF_SHELLSHOCK (0x8000) directly. */
    if((m->ps->pm_flags&0x8000) && (unsigned)m->ps->shellshockIndex<16 &&
       *((const unsigned char *)BG_GetShellshockParms(m->ps->shellshockIndex)+0x264))
        scale*=0.4f;
    return scale*m->ps->moveSpeedScaleMultiplier;
}

static float wish(codol_pmove_c1_t *m,vec3_t dir)
{
    /* C1 PM_AirMove 0x0041069d and PM_WalkMove 0x0041096a both read the
     * command axes out of pm->cmd (signed bytes at +0x1e/+0x1f).  That is the
     * copy PM_WalkMove 0x00410932 already rewrote for sprint, so the sprint
     * reduction must NOT be reapplied here -- and PM_AirMove reached directly
     * by PmoveSingle (airborne) never sees it at all. */
    float f=(float)m->host->cmd.forwardmove;
    float r=(float)m->host->cmd.rightmove;
    float scale=command_scale(m,f,r),length;
    vec3_t forward,right;
    copy3(forward,m->local.forward); copy3(right,m->local.right);
    /* C1 PM_AirMove 0x4106da..0x4106f8 and PM_WalkMove
     * 0x4109e1..0x4109ff flatten and normalize both command axes. */
    forward[2]=right[2]=0.0f;
    length=len3(forward); if(length>0.0f){forward[0]/=length;forward[1]/=length;}
    length=len3(right); if(length>0.0f){right[0]/=length;right[1]/=length;}
    dir[0]=forward[0]*f+right[0]*r;
    dir[1]=forward[1]*f+right[1]*r;
    dir[2]=forward[2]*f+right[2]*r;
    length=len3(dir); if(length<=0.0f) {
        if(CODOL_TRACE_ON())
            CODOL_PmoveTraceWish(m->ps->clientNum,dir,0.0f,scale,f,r);
        return 0.0f;
    }
    dir[0]/=length;dir[1]/=length;dir[2]/=length;
    if(CODOL_TRACE_ON())
        CODOL_PmoveTraceWish(m->ps->clientNum,dir,length*scale,scale,f,r);
    return length*scale;
}

/* Horizontal azimuth in degrees; NaN-free sentinel for a zero vector. */
static float azimuth_deg(const vec3_t v)
{
    if(v[0]==0.0f && v[1]==0.0f) return 0.0f;
    return (float)(atan2((double)v[1],(double)v[0])*(180.0/M_PI));
}
static float azimuth_change(float before,float after)
{
    float d=after-before;
    while(d>180.0f) d-=360.0f;
    while(d<-180.0f) d+=360.0f;
    return d;
}

static float angle_delta(float a,float b)
{
    float d=a-b;
    while(d>180.0f)d-=360.0f;
    while(d<-180.0f)d+=360.0f;
    return d;
}

static void set_movement_dir(codol_pmove_c1_t *m)
{
    vec3_t moved;
    float length,yaw;
    int dir;
    if(m->ps->pm_flags&1) {
        dir=(int)angle_delta(m->ps->proneDirection,m->ps->viewangles[1]);
    } else {
        moved[0]=m->ps->origin[0]-m->local.previous_origin[0];
        moved[1]=m->ps->origin[1]-m->local.previous_origin[1]; moved[2]=0.0f;
        length=len3(moved);
        if((!(m->cmd.direction&0x0f)) || m->ps->groundEntityNum==C1_ENTITYNUM_NONE ||
           length<=m->local.frametime*5.0f) { m->ps->movementDir=0; return; }
        yaw=(float)(atan2(moved[1],moved[0])*180.0/M_PI);
        dir=(int)angle_delta(yaw,m->ps->viewangles[1]);
        if(m->cmd.direction&2)dir=(int)angle_delta((float)dir+180.0f,0.0f);
    }
    if(dir>90)dir=90;else if(dir<-90)dir=-90;
    m->ps->movementDir=(char)dir;
}

static float permute_restrictive_planes(const vec3_t velocity,int count,
                                        vec3_t planes[8],int permutation[8])
{
    float parallel[8];
    int plane,slot;
    for(plane=0;plane<count;++plane) {
        parallel[plane]=dot3(velocity,planes[plane]);
        for(slot=plane;slot && parallel[plane]<=parallel[permutation[slot-1]];--slot)
            permutation[slot]=permutation[slot-1];
        permutation[slot]=plane;
    }
    return parallel[permutation[0]];
}

/* C1 PM_SlideMove 0x416ed0..0x4177a2.  This is the eight-plane C1/IW4/T5
 * solver, not the retained IW3/Q3 insertion-order approximation. */
static int slide(codol_pmove_c1_t *m,int gravity)
{
    vec3_t end,clip,end_clip,planes[8],end_velocity,primal,crease;
    trace_t tr;
    float time=m->local.frametime,into,length,d;
    int bump,i,j,k,planes_count=0,permutation[8];
    int apply_gravity=gravity && !(m->ps->pm_flags&0x800u);
    static int last_collision_report[MAX_CLIENTS];

    copy3(primal,m->ps->velocity);
    copy3(end_velocity,m->ps->velocity);
    if(apply_gravity) {
        end_velocity[2]-=(float)m->ps->gravity*m->local.frametime;
        m->ps->velocity[2]=(m->ps->velocity[2]+end_velocity[2])*0.5f;
        primal[2]=end_velocity[2];
        if(m->local.groundPlane)
            clip_velocity(m->ps->velocity,m->local.groundTrace.normal,m->ps->velocity);
    }
    if(m->local.groundPlane) copy3(planes[planes_count++],m->local.groundTrace.normal);
    copy3(planes[planes_count],m->ps->velocity);
    length=len3(planes[planes_count]);
    if(length>0.0f) {
        planes[planes_count][0]/=length;
        planes[planes_count][1]/=length;
        planes[planes_count][2]/=length;
    }
    ++planes_count;

    for(bump=0;bump<4;++bump) {
        end[0]=m->ps->origin[0]+m->ps->velocity[0]*time;
        end[1]=m->ps->origin[1]+m->ps->velocity[1]*time;
        end[2]=m->ps->origin[2]+m->ps->velocity[2]*time;
        trace_move(m,&tr,m->ps->origin,end);
        if(CODOL_TRACE_ON() &&
           tr.fraction<1.0f && (m->cmd.direction&15u) &&
           (unsigned)m->ps->clientNum<MAX_CLIENTS &&
           m->ps->commandTime-last_collision_report[m->ps->clientNum]>=1000) {
            last_collision_report[m->ps->clientNum]=m->ps->commandTime;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL C1 slide collision: client %u cmd %d bump %d gravity %d frac %.4f solid %d/%d normal (%.3f %.3f %.3f) hit %d/%u entity %d mask 0x%x start (%.1f %.1f %.1f) end (%.1f %.1f %.1f) vel (%.1f %.1f %.1f)\n",
                (unsigned)m->ps->clientNum,m->ps->commandTime,bump,apply_gravity,
                tr.fraction,tr.startsolid,tr.allsolid,
                tr.normal[0],tr.normal[1],tr.normal[2],tr.hitType,
                (unsigned)tr.hitId,hit_entity(&tr),m->host->tracemask,
                m->ps->origin[0],m->ps->origin[1],m->ps->origin[2],
                end[0],end[1],end[2],m->ps->velocity[0],
                m->ps->velocity[1],m->ps->velocity[2]);
        }
        if(tr.fraction<1.0f)
            CODOL_PmoveTraceCollision(m->ps->clientNum,1,0.0f,tr.normal,
                                      tr.fraction,(int)tr.hitType);
        if(tr.allsolid) { m->ps->velocity[2]=0.0f; return 1; }
        if(tr.fraction>0.0f) {
            m->ps->origin[0]+=(end[0]-m->ps->origin[0])*tr.fraction;
            m->ps->origin[1]+=(end[1]-m->ps->origin[1])*tr.fraction;
            m->ps->origin[2]+=(end[2]-m->ps->origin[2])*tr.fraction;
        }
        if(tr.fraction==1.0f) break;
        PM_AddTouchEnt(m->host,hit_entity(&tr));
        time-=time*tr.fraction;
        if(planes_count>=8) { memset(m->ps->velocity,0,sizeof(vec3_t)); return 1; }
        for(i=0;i<planes_count;++i) if(dot3(tr.normal,planes[i])>0.99900001f) {
            clip_velocity(m->ps->velocity,tr.normal,m->ps->velocity);
            m->ps->velocity[0]+=tr.normal[0];
            m->ps->velocity[1]+=tr.normal[1];
            m->ps->velocity[2]+=tr.normal[2];
            break;
        }
        if(i<planes_count) continue;
        copy3(planes[planes_count++],tr.normal);
        into=permute_restrictive_planes(m->ps->velocity,planes_count,planes,permutation);
        if(into>=0.1f) continue;
        if(-into>m->local.impactSpeed) m->local.impactSpeed=-into;
        clip_velocity(m->ps->velocity,planes[permutation[0]],clip);
        clip_velocity(end_velocity,planes[permutation[0]],end_clip);
        for(j=1;j<planes_count;++j) {
            if(dot3(clip,planes[permutation[j]])>=0.1f) continue;
            clip_velocity(clip,planes[permutation[j]],clip);
            clip_velocity(end_clip,planes[permutation[j]],end_clip);
            if(dot3(clip,planes[permutation[0]])>=0.0f) continue;
            crease[0]=planes[permutation[0]][1]*planes[permutation[j]][2]-
                      planes[permutation[0]][2]*planes[permutation[j]][1];
            crease[1]=planes[permutation[0]][2]*planes[permutation[j]][0]-
                      planes[permutation[0]][0]*planes[permutation[j]][2];
            crease[2]=planes[permutation[0]][0]*planes[permutation[j]][1]-
                      planes[permutation[0]][1]*planes[permutation[j]][0];
            length=len3(crease);
            if(length>0.0f) {
                crease[0]/=length; crease[1]/=length; crease[2]/=length;
            }
            d=dot3(crease,m->ps->velocity);
            clip[0]=crease[0]*d; clip[1]=crease[1]*d; clip[2]=crease[2]*d;
            d=dot3(crease,end_velocity);
            end_clip[0]=crease[0]*d; end_clip[1]=crease[1]*d; end_clip[2]=crease[2]*d;
            for(k=1;k<planes_count;++k) if(k!=j &&
               dot3(clip,planes[permutation[k]])<0.1f) {
                memset(m->ps->velocity,0,sizeof(vec3_t)); return 1;
            }
        }
        copy3(m->ps->velocity,clip);
        copy3(end_velocity,end_clip);
    }
    if(apply_gravity) copy3(m->ps->velocity,end_velocity);
    if(m->ps->pm_time) copy3(m->ps->velocity,primal);
    return bump!=0;
}

static void step_slide(codol_pmove_c1_t *m,int gravity)
{
    vec3_t start_o,start_v,down_o,down_v,up,end,projected;
    trace_t tr;
    float slide_dot,step_dot,step_size,step_up=0.0f,max_z;
    int blocked,on_ground,jump_step=0;
    /* Which branches of this function ran, for the divergence trace.  The
     * along-track error on non-flat ground is triggered by leaving flat rather
     * than scaling with tilt, so the question is which of these discrete paths
     * the two simulations take differently -- not by how much. */
    unsigned stepflags=0;
#define CODOL_STEP_XY(a,b) ((float)sqrt((double)( \
    ((b)[0]-(a)[0])*((b)[0]-(a)[0]) + ((b)[1]-(a)[1])*((b)[1]-(a)[1]))))
#define CODOL_STEP_PUBLISH() do { \
    CODOL_PmoveTraceCollision(m->ps->clientNum,blocked, \
        m->ps->origin[2]-start_o[2],NULL,0.0f,0); \
    CODOL_PmoveTraceStep(m->ps->clientNum,stepflags, \
        CODOL_STEP_XY(start_o,down_o),CODOL_STEP_XY(start_o,m->ps->origin), \
        step_up); } while(0)
#define CODOL_STEP_RETURN() do { CODOL_STEP_PUBLISH(); return; } while(0)
    on_ground=(m->ps->pm_flags&8)?0:m->local.groundPlane;
    /* C1 0x4177f1..0x417889 clears timed airborne jumping before SlideMove. */
    if((m->ps->pm_flags&8) || (!m->local.groundPlane &&
       (m->ps->pm_flags&C1_PMF_JUMPING) && m->ps->pm_time)) {
        m->ps->pm_flags&=~0x00402000u; m->ps->jumpOriginZ=0.0f;
    }
    copy3(start_o,m->ps->origin);copy3(start_v,m->ps->velocity);
    blocked=slide(m,gravity);
    if(blocked) stepflags|=0x80u;
    /* Hoisted from below so the airborne early-returns can report the plain
     * slide result as well; nothing between here and the old site modifies
     * origin or velocity. */
    copy3(down_o,m->ps->origin);copy3(down_v,m->ps->velocity);
    step_size=(m->ps->pm_flags&1)?C1_PRONE_STEP_HEIGHT:C1_STEP_HEIGHT;
    if(m->ps->groundEntityNum==C1_ENTITYNUM_NONE) {
        if((m->ps->pm_flags&C1_PMF_JUMPING) && m->ps->pm_time) {
            m->ps->pm_flags&=~0x00402000u; m->ps->jumpOriginZ=0.0f;
        }
        if(blocked && (m->ps->pm_flags&C1_PMF_JUMPING)) {
            max_z=m->ps->jumpOriginZ+C1_JUMP_HEIGHT;
            if(max_z>start_o[2]) {
                step_size=max_z-start_o[2]<C1_STEP_HEIGHT?max_z-start_o[2]:C1_STEP_HEIGHT;
                if(step_size<1.0f) CODOL_STEP_RETURN();
                jump_step=1;
            }
        }
        /* C1 0x4178dc: failed sizing uses the upward-ladder gate. Successful
         * sizing below one unit returns directly at 0x4178ea. */
        if(!jump_step && (!(m->ps->pm_flags&8) || m->ps->velocity[2]<=0.0f))
            CODOL_STEP_RETURN();
    }
    if(blocked || (m->local.groundPlane && m->local.groundTrace.normal[2]<0.9f)) {
        copy3(up,start_o);up[2]+=step_size+1.0f;
        trace_move(m,&tr,start_o,up);
        step_up=tr.fraction*(step_size+1.0f)-1.0f;
        if(step_up<1.0f)step_up=0.0f;
        else { stepflags|=0x01u;
            copy3(m->ps->origin,start_o);m->ps->origin[2]+=step_up;
            copy3(m->ps->velocity,start_v);slide(m,gravity); }
    }
    if(on_ground || step_up!=0.0f) {
        stepflags|=0x02u;
        copy3(end,m->ps->origin);end[2]-=step_up+(on_ground?C1_GROUND_SNAP:0.0f);
        trace_move(m,&tr,m->ps->origin,end);
        if(tr.fraction<1.0f) stepflags|=0x04u;
        /* C1 0x417af3 accepts a down hit immediately when the trace marked it
         * walkable.  A non-walkable hit rejects every jump-step; an ordinary
         * step may still land on a normal whose Z is at least 0.3. */
        if(hit_player(&tr) || (tr.fraction<1.0f && !tr.walkable &&
           (jump_step || tr.normal[2]<0.3f))) {
            stepflags|=0x08u;
            copy3(m->ps->origin,down_o);copy3(m->ps->velocity,down_v);
            CODOL_STEP_RETURN();
        }
        if(tr.fraction>=1.0f) { if(step_up!=0.0f)m->ps->origin[2]-=step_up; }
        else {
            m->ps->origin[0]+=(end[0]-m->ps->origin[0])*tr.fraction;
            m->ps->origin[1]+=(end[1]-m->ps->origin[1])*tr.fraction;
            m->ps->origin[2]+=(end[2]-m->ps->origin[2])*tr.fraction;
            project_velocity(m->ps->velocity,tr.normal,projected);copy3(m->ps->velocity,projected);
        }
    }
    slide_dot=(down_o[0]-start_o[0])*start_v[0]+(down_o[1]-start_o[1])*start_v[1];
    step_dot=(m->ps->origin[0]-start_o[0])*start_v[0]+(m->ps->origin[1]-start_o[1])*start_v[1];
    if(slide_dot+0.001f>=step_dot || (jump_step && m->ps->origin[2]>=m->ps->jumpOriginZ+C1_JUMP_HEIGHT)) {
        stepflags|=0x10u;
        copy3(m->ps->origin,down_o);copy3(m->ps->velocity,down_v);
        if(on_ground) { copy3(end,m->ps->origin);end[2]-=C1_GROUND_SNAP;trace_move(m,&tr,m->ps->origin,end);
            if(tr.fraction<1.0f){ stepflags|=0x20u;
                m->ps->origin[0]+=(end[0]-m->ps->origin[0])*tr.fraction;
                m->ps->origin[1]+=(end[1]-m->ps->origin[1])*tr.fraction;
                m->ps->origin[2]+=(end[2]-m->ps->origin[2])*tr.fraction;
                clip_velocity(m->ps->velocity,tr.normal,m->ps->velocity);
            }
        }
    }
    if(jump_step && m->ps->origin[2]>down_o[2]) {
        float d=m->ps->jumpOriginZ+C1_JUMP_HEIGHT-m->ps->origin[2];
        if(d<0.1f)m->ps->velocity[2]=0.0f;
        else {float vmax=(float)sqrt(2.0*(double)m->ps->gravity*d);if(vmax<m->ps->velocity[2])m->ps->velocity[2]=0.0f;}
    }
    /* C1 0x417d5d: a real grounded step slows the resulting velocity and
     * advances the weapon-bob phase.  Omitting this makes client prediction
     * run ahead on stairs and is especially visible on the Killhouse tower. */
    if(on_ground && m->ps->pm_type<8 && verify_prone_step(m,start_o,start_v)) {
        float dz=m->ps->origin[2]-down_o[2];
        if((float)fabs(dz)>0.5f) {
            int steps=(int)nearbyint((double)dz+9.313e-10);
            if(steps) { stepflags|=0x40u;
                float scale=((1.0f-(float)fabs(m->ps->origin[2]-start_o[2])/step_size)*
                             0.8000000119f)+0.1999999881f;
                int absolute=steps<0?-steps:steps;
                m->ps->velocity[0]*=scale;m->ps->velocity[1]*=scale;m->ps->velocity[2]*=scale;
                if(absolute>3 && m->ps->groundEntityNum!=C1_ENTITYNUM_NONE &&
                   (m->ps->velocity[0]!=0.0f || m->ps->velocity[1]!=0.0f)) {
                    int half=absolute/2;if(half>4)half=4;
                    m->ps->bobCycle=((int)((float)half*1.25f+7.0f+
                                           (float)(m->ps->bobCycle&255)))&255;
                }
            }
        }
    }
    CODOL_STEP_PUBLISH();
#undef CODOL_STEP_RETURN
#undef CODOL_STEP_PUBLISH
#undef CODOL_STEP_XY
}

int CODOL_PM_CheckJumpC1(codol_pmove_c1_t *m)
{
    playerState_t *ps=m->ps;
    float factor=1.0f,energy;
    unsigned surface;
    /* C1 PM_WalkMove applies the previous landing slowdown before checking
     * for another jump. */
    if(m->local.walking && (ps->pm_flags&C1_PMF_JUMPING)) {
        if(ps->pm_time>1800) {
            ps->pm_flags&=~0x00402000u;
            ps->jumpOriginZ=0.0f;
            factor=0.65f;
        } else if(ps->pm_time==0) {
            if(ps->jumpOriginZ+18.0f<=ps->origin[2]) {
                ps->pm_time=1200;
                factor=0.5f;
            } else {
                ps->pm_time=1800;
                factor=0.65f;
            }
        }
        if((!jump_slowdownEnable || jump_slowdownEnable->boolean) &&
           !(ps->pm_flags&0x00400000u)) {
            ps->velocity[0]*=factor;
            ps->velocity[1]*=factor;
            ps->velocity[2]*=factor;
        }
    }
    if(!m->local.walking || (ps->pm_flags&0x00040404u) ||
       ps->pm_type>=8 || ps->viewHeightTarget==11 ||
       ps->viewHeightTarget==22 || ps->viewHeightTarget==40 ||
       !(m->cmd.buttons&C1_BUTTON_JUMP) ||
       (int)m->cmd.serverTime-ps->jumpTime<500) return 0;
    if(m->oldcmd.buttons&C1_BUTTON_JUMP) {
        m->cmd.buttons&=~C1_BUTTON_JUMP;
        m->host->cmd.buttons&=~C1_BUTTON_JUMP;
        return 0;
    }
    energy=2.0f*(float)ps->gravity*C1_JUMP_HEIGHT;
    if(ps->pm_flags&C1_PMF_JUMPING) {
        if(ps->pm_time<=1800 && !(ps->pm_flags&0x00400000u) &&
           (!jump_slowdownEnable || jump_slowdownEnable->boolean)) {
            factor=ps->pm_time<1700 ?
                (float)ps->pm_time*1.5f*0.00058823527f+1.0f : 2.5f;
            if(factor>0.0f) energy/=factor;
        }
    }
    ps->velocity[2]=(float)sqrt((double)energy);
    ps->jumpTime=(int)m->cmd.serverTime; ps->jumpOriginZ=ps->origin[2];
    ps->pm_flags=(ps->pm_flags&~0x180u)|C1_PMF_JUMPING;
    ps->pm_time=0;
    ps->sprintState.sprintButtonUpRequired=0;
    ps->groundEntityNum=C1_ENTITYNUM_NONE;
    ps->aimSpreadScale+=64.0f;
    if(ps->aimSpreadScale>255.0f) ps->aimSpreadScale=255.0f;
    surface=(m->local.groundTrace.sflags&0x2000)?21u:
            ((unsigned)m->local.groundTrace.sflags>>20)&31u;
    add_event_param(ps,EV_JUMP,surface);
    m->local.walking=m->local.groundPlane=m->local.almostGroundPlane=0;
    return 1;
}

/* C1 PM_AirMove 0x410660. pml->walking remains meaningful when a landed
 * dive deliberately branches here; friction must see it, while acceleration
 * and step-slide still use the air rules. */
void CODOL_PM_AirMoveC1(codol_pmove_c1_t *m)
{
    vec3_t dir,clipped;
    float speed;
    if(!m || !m->ps || !m->host)return;
    friction(m);
    speed=wish(m,dir);
    accelerate(m,dir,speed,C1_AIR_ACCEL);
    if(m->local.groundPlane) {
        clip_velocity(m->ps->velocity,m->local.groundTrace.normal,clipped);
        copy3(m->ps->velocity,clipped);
    }
    step_slide(m,1);
    set_movement_dir(m);
    post_air_prone(m);
    CODOL_PM_GroundTraceC1(m);
}

void CODOL_PM_NormalMoveC1(codol_pmove_c1_t *m)
{
    vec3_t dir,clipped;
    float speed,accel,proj_wish_deg=0.0f,proj_vel_deg=0.0f;
    int slick_or_knockback,air_move;
    if(!m || !m->ps || !m->host)return;
    air_move=!m->local.walking;
    friction(m); speed=wish(m,dir);
    /* C1 PM_WalkMove 0x004109bb..0x004109e1 discharges the damage timer after
     * PM_Friction/PM_CmdScale and before the wish direction, on every walking
     * command step.  Without it the GSC damage receiver's one-shot charge never
     * decays, so CODOL_PM_FootstepsC1 below latches the stumble and flinch
     * movements until the playerState is rebuilt at respawn. */
    m->ps->damageTimer=CODOL_PainTimerStep(m->ps->damageTimer,m->local.msec);
    slick_or_knockback=m->local.walking &&
        ((m->local.groundTrace.sflags&2) || (m->ps->pm_flags&0x100));
    if(!m->local.walking || slick_or_knockback) accel=C1_AIR_ACCEL;
    else {
        /* C1 PM_WalkMove 0x00410a63 indexes by PM_GetStanceIndex, not by the
         * prone/crouch pm_flags: 1 -> 19 (0xc3ea24), 2 -> 12 (0xc3ee00),
         * 3 -> 19, 0 -> 9 (0xc3ee04). */
        static const float by_stance[4]={C1_GROUND_ACCEL,C1_PRONE_ACCEL,
                                         C1_DUCK_ACCEL,C1_PRONE_ACCEL};
        accel=by_stance[c1_stance_index(m->ps)];
    }
    /* C1 0x00410a8d: a landed player (PMF_LANDED 0x80) accelerates at a
     * quarter rate (0xc84420 = 0.25).  Missing here, the server
     * out-accelerated the client for the whole post-landing window. */
    if(m->ps->pm_flags&0x80u) accel*=0.25f;
    /* Measured, not assumed: PM_ProjectVelocity scales x and y by one common
     * factor (C1 0x0040f4c9..0x0040f4fa), so neither of these calls can rotate
     * the horizontal azimuth.  Both deltas are published for the divergence
     * trace so "the ground normal rotated the move" is a testable claim. */
    if(m->local.walking) {
        if(CODOL_TRACE_ON()) {
            float before=azimuth_deg(dir);
            project_velocity(dir,m->local.groundTrace.normal,dir);
            proj_wish_deg=azimuth_change(before,azimuth_deg(dir));
        } else project_velocity(dir,m->local.groundTrace.normal,dir);
    }
    accelerate(m,dir,speed,accel);
    if(m->local.walking) {
        float before;
        if(slick_or_knockback)
            m->ps->velocity[2]-=(float)m->ps->gravity*m->local.frametime;
        before=CODOL_TRACE_ON()?azimuth_deg(m->ps->velocity):0.0f;
        project_velocity(m->ps->velocity,m->local.groundTrace.normal,clipped);
        copy3(m->ps->velocity,clipped);
        if(CODOL_TRACE_ON())
            proj_vel_deg=azimuth_change(before,azimuth_deg(m->ps->velocity));
    } else if(m->local.groundPlane) {
        clip_velocity(m->ps->velocity,m->local.groundTrace.normal,clipped);
        copy3(m->ps->velocity,clipped);
    }
    /* C1 PM_WalkMove 0x00410aee..0x00410b24 does NOT step-slide a walking
     * player whose horizontal velocity is exactly zero; it goes straight to
     * PM_SetMovementDir.  Running the solver anyway lets the 9-unit ground
     * snap move a standing player the client never moved. PM_AirMove
     * (0x004107d9) has no such gate. */
    if(air_move || m->ps->velocity[0]!=0.0f || m->ps->velocity[1]!=0.0f)
        step_slide(m,!m->local.walking);
    /* Published BEFORE the trailing ground trace overwrites local.groundTrace:
     * this is the plane the move actually used, with the collision identity
     * that answered it (hitType/hitId/surfaceFlags/contents name which trace
     * stack and which surface -- terrain triangles change normal as the player
     * walks, which is the one way this input can vary frame to frame). */
    if(CODOL_TRACE_ON())
    CODOL_PmoveTraceGround(m->ps->clientNum,m->local.groundTrace.normal,
                           m->local.groundTrace.fraction,
                           m->local.groundTrace.hitType,
                           (int)m->local.groundTrace.hitId,
                           (unsigned)m->local.groundTrace.sflags,
                           (unsigned)m->local.groundTrace.cflags,
                           proj_wish_deg,proj_vel_deg);
    set_movement_dir(m);
    if(air_move) post_air_prone(m);
    CODOL_PM_GroundTraceC1(m);
    if((m->cmd.direction&15u) && (unsigned)m->ps->clientNum<MAX_CLIENTS &&
       CODOL_TRACE_ON()) {
        static int last_report[MAX_CLIENTS];
        unsigned slot=(unsigned)m->ps->clientNum;
        if(m->ps->commandTime-last_report[slot]>=1000) {
            last_report[slot]=m->ps->commandTime;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL C1 move: client %u cmd %d dir 0x%x wish %.1f walk %d ground %d trace frac %.3f solid %d/%d normal (%.3f %.3f %.3f) hit %d/%d mask 0x%x vel (%.1f %.1f %.1f) origin (%.1f %.1f %.1f)\n",
                slot,m->ps->commandTime,(unsigned)m->cmd.direction&15u,speed,
                m->local.walking,m->ps->groundEntityNum,m->local.groundTrace.fraction,
                m->local.groundTrace.startsolid,m->local.groundTrace.allsolid,
                m->local.groundTrace.normal[0],m->local.groundTrace.normal[1],m->local.groundTrace.normal[2],
                m->local.groundTrace.hitType,m->local.groundTrace.hitId,m->host->tracemask,
                m->ps->velocity[0],m->ps->velocity[1],m->ps->velocity[2],
                m->ps->origin[0],m->ps->origin[1],m->ps->origin[2]);
        }
    }
}

void CODOL_PM_LadderMoveC1(codol_pmove_c1_t *m)
{
    if(!m || !m->ps || !m->host)return;
    step_slide(m,0);
    set_movement_dir(m);
    CODOL_PM_GroundTraceC1(m);
}

/* C1 PM_MeleeChargeMove 0x415dd0. The charge trajectory owns movement while
 * PMF_MELEE_CHARGE is set; treating it as ordinary walking makes both peers
 * simulate different velocity decay and collision. */
void CODOL_PM_MeleeChargeMoveC1(codol_pmove_c1_t *m)
{
    playerState_t *ps;
    vec3_t dir,projected;
    float speed,next,average;
    if(!m || !(ps=m->ps)) return;
    speed=len3(ps->velocity);
    if(speed>0.0f) {
        dir[0]=ps->velocity[0]/speed;
        dir[1]=ps->velocity[1]/speed;
        dir[2]=ps->velocity[2]/speed;
        if(ps->meleeChargeTime>0)
            next=speed-(speed/((float)ps->meleeChargeTime*0.001f))*m->local.frametime;
        else next=0.0f;
        if(next<0.0f) next=0.0f;
        average=(speed+next)*0.5f;
        ps->velocity[0]=average*dir[0];
        ps->velocity[1]=average*dir[1];
        ps->velocity[2]=average*dir[2];
    } else {
        memset(dir,0,sizeof(dir));
        next=0.0f;
    }
    project_velocity(ps->velocity,m->local.groundTrace.normal,projected);
    copy3(ps->velocity,projected);
    if(ps->velocity[0]!=0.0f || ps->velocity[1]!=0.0f) step_slide(m,0);
    ps->velocity[0]=next*dir[0];
    ps->velocity[1]=next*dir[1];
    ps->velocity[2]=next*dir[2];
    ps->meleeChargeTime-=m->local.msec;
    if(ps->meleeChargeTime<=0) {
        ps->velocity[0]=ps->velocity[1]=0.0f;
        ps->pm_flags&=~0x00010000u;
        ps->meleeChargeYaw=0.0f;
        ps->meleeChargeDist=0;
        ps->meleeChargeTime=0;
    }
    set_movement_dir(m);
    CODOL_PM_GroundTraceC1(m);
}

/* C1 413370/413510: the stationary model still selects idle, flinch and
 * turn animations. These are native clientInfo fields, not C1 byte offsets. */
static int idle_turn_c1(struct clientInfo_t *ci)
{
    int turn=0;
    if(ci->legs.yawing){
        turn=ci->legs.yawAngle>ci->torso.yawAngle?14:15;
        ci->legs.yawAngle=ci->torso.yawAngle;ci->turnAnimType=(char)turn;
        if(ci->turnAnimEndTime<bgs->time)ci->turnAnimEndTime=0;
    }else if(ci->turnAnimEndTime>bgs->time){
        ci->legs.yawAngle=ci->torso.yawAngle;
    }else if(ci->turnAnimEndTime){
        ci->turnAnimEndTime=0;ci->legs.yawAngle=ci->torso.yawAngle;
    }
    return turn;
}
static int flinching_c1(const playerState_t *ps)
{
    return CODOL_PainFlinching(ps->damageTimer,ps->damageDuration,
        player_dmgtimer_flinchTime?player_dmgtimer_flinchTime->integer:500);
}
static void idle_animation_c1(codol_pmove_c1_t *m,int stance,int coasting)
{
    static const int idle[4][3]={{1,14,15},{3,3,3},{2,16,17},{51,51,51}};
    playerState_t *ps=m->ps;
    struct clientInfo_t *ci=NULL;
    int turn=0,result,anim=idle[stance][0];
    if(coasting){
        if(m->host->xyspeed>120.0f)return; /* 413860 */
        if(stance && BG_AnimScriptAnimation(ps,0,anim,0)>=0)return;
        BG_AnimScriptAnimation(ps,0,flinching_c1(ps)?32:1,0);return;
    }
    if(m->host->xyspeed<1.0f)ps->bobCycle=0;
    if(bgs && ps->clientNum>=0 && ps->clientNum<64)ci=&bgs->clientinfo[ps->clientNum];
    if(ci && player_turnAnims && player_turnAnims->boolean && stance!=1 && stance!=3)
        turn=idle_turn_c1(ci);
    if(turn)anim=idle[stance][turn==14?1:2];
    else if(stance==0 && flinching_c1(ps)){
        BG_AnimScriptAnimation(ps,0,CODOL_PainFlinchIdleAnim(ps->flinchYawAnim),0);return;
    }
    result=BG_AnimScriptAnimation(ps,0,anim,0);
    if(turn && result>0 && !ci->turnAnimEndTime)
        ci->turnAnimEndTime=bgs->time+ps->legsAnimDuration;
    if(result<0)BG_AnimScriptAnimation(ps,0,stance==3?51:stance==2?2:flinching_c1(ps)?32:1,0);
}

void CODOL_PM_FootstepsC1(codol_pmove_c1_t *m,int msec)
{
    static const float table[8]={0.335f,0.305f,0.250f,0.240f,0.340f,0.315f,0.250f,0.240f};
    const struct WeaponDef *weapon;
    float f,r,dirscale=1.0f,stance=1.0f,divisor,xyspeed,bob;
    int base,ads,sprinting,old_cycle,move_anim,anim_stance,backward,stumble,strafe;
    if(!m || !m->ps || msec<=0 || m->ps->pm_type>=8) return;
    xyspeed=(float)sqrt(m->ps->velocity[0]*m->ps->velocity[0]+m->ps->velocity[1]*m->ps->velocity[1]);
    /* C1 4139ad..4139d3 selects the airborne/ladder tail before the
     * idle reset or walking bob update. 413440 returns without changing
     * bobCycle for ordinary airborne players (PMF_LADDER is clear).
     * Advancing walking bob in the air makes snapshots rewind the client's
     * frozen viewmodel phase after every jump. */
    m->host->xyspeed=xyspeed;
    anim_stance=m->ps->viewHeightTarget==22?3:m->ps->viewHeightTarget==40?2:
        m->ps->viewHeightTarget==11?1:0;
    if(m->ps->eFlags&0xc00u){
        static const int turret_idle[4]={1,3,2,51};
        BG_AnimScriptAnimation(m->ps,0,turret_idle[anim_stance],0);return;
    }
    if(m->ps->groundEntityNum==C1_ENTITYNUM_NONE && m->ps->pm_type!=1 &&
       m->ps->pm_type!=7 && !m->local.almostGroundPlane){
        if(!(m->ps->pm_flags&8u) || (int)m->cmd.serverTime-m->ps->jumpTime<300)return;
        /* C1 413440 ladder phase is vertical and signed, unlike walk bob. */
        ads=(m->ps->pm_flags&0x40u) || m->ps->leanf!=0.0f;
        BG_AnimScriptAnimation(m->ps,0,m->ps->velocity[2]<0?19:18,0);
        bob=m->ps->velocity[2]/(ads?38.10000056773424f:95.25f)*(ads?0.35f:0.45f);
        old_cycle=m->ps->bobCycle&255;
        m->ps->bobCycle=((int)((float)old_cycle+bob*msec))&255;
        PM_FootstepEvent(m->host,&m->local,old_cycle,m->ps->bobCycle,1);return;
    }
    if(m->ps->pm_type==1 || xyspeed<(player_moveThreshhold?player_moveThreshhold->value:10.0f)){
        idle_animation_c1(m,anim_stance,0);return;
    }
    /* C1 PM_Footsteps reads pm->cmd.forwardmove/rightmove (+0x1e/+0x1f), the
     * copy PM_WalkMove 0x00410932 already reduced for sprint. */
    f=(float)m->host->cmd.forwardmove;
    r=(float)m->host->cmd.rightmove;
    if(f==0.0f && r==0.0f){idle_animation_c1(m,anim_stance,1);return;}
    if(f!=0.0f){if(r!=0.0f){dirscale=0.925f;if(f<0.0f)dirscale*=0.85f;}else if(f<0.0f)dirscale=0.70f;}
    else dirscale=0.85f;
    if(m->ps->pm_flags&1)stance=0.15f;else if(m->ps->pm_flags&2)stance=0.65f;
    if(m->ps->pm_type==7)stance=0.2f;
    sprinting=(m->ps->pm_flags&0x4000)!=0;
    ads=((m->ps->pm_flags&0x40) || m->ps->leanf!=0.0f);
    /* 4137D0 records strafing independently of the forward/back move table. */
    {
        float raw_f=f,raw_r=r;
        float normalized_f=raw_f/sqrtf(raw_f*raw_f+raw_r*raw_r);
        float threshold=player_strafeAnimCosAngle?player_strafeAnimCosAngle->value:0.5f;
        strafe=fabsf(normalized_f)>threshold?0:raw_r>0.0f?2:1;
        BG_SetConditionValue(m->ps->clientNum,8,(unsigned long long)strafe);
    }
    backward=(m->ps->pm_flags&0x20u)?4:0;
    stumble=CODOL_PainStumbling(m->ps->damageTimer,m->ps->damageDuration,
        player_dmgtimer_stumbleTime?player_dmgtimer_stumbleTime->integer:500);
    move_anim=CODOL_PainMoveAnim(stumble,ads,anim_stance+backward,sprinting);
    if(m->ps->pm_flags&0x40000000u)move_anim=54;
    if(BG_AnimScriptAnimation(m->ps,0,move_anim,0)<0)BG_AnimScriptAnimation(m->ps,0,1,0);
    divisor=(float)m->ps->speed*dirscale*stance;
    if(ads || m->ps->leanf!=0.0f)divisor*=0.4f;
    else if(sprinting)divisor*=1.5f;
    weapon=BG_GetWeaponDef(m->ps->weapon);
    if(weapon) {
        /* C1 0x0041372c tests PMF_ADS (pm_flags & 0x40) ALONE here, not the
         * `(pm_flags & 0x40) || leanf != 0` compound that the 0.4 multiplier and
         * the bob-constant table above use (0x004139e2 builds that compound for
         * those two only). Folding leanf in made a leaning, un-ADS'd player
         * divide by adsMoveSpeedScale on the server while C1's client divided by
         * moveSpeedScale, so ps->bobCycle integrated at a different rate on the
         * two sides. bobCycle is a hint-3 netfield -- republished only on a
         * forced (rov) frame -- and C1 draws the SCOPED weapon sway
         * (0x00424d90, gated on WeaponDef+0x694, so scoped weapons only) with
         * bobCycle as its phase, so a desynchronised bobCycle shows up as a
         * sniper scope that jerks whenever the server forces that group.
         * docs/CODOL_IMPLEMENTATION_PASS.md 2026-09-16 (sway, fourth pass). */
        if(!(m->ps->pm_flags&0x40u) && weapon->moveSpeedScale>0.0f)
            divisor*=weapon->moveSpeedScale;
        else if(weapon->adsMoveSpeedScale>0.0f)
            divisor*=weapon->adsMoveSpeedScale;
    }
    if(divisor<=0.000001f)return;
    base=(m->ps->pm_flags&1)?1:(m->ps->pm_flags&2)?2:(m->ps->pm_type==7)?3:0;
    /* C1 0x4136f9/0x413ac5 uses a 1.5 sprint maximum with a 0.5 sprint
     * bob constant.  Keep the pair together; using the standing 0.335 value
     * only happened to approximate the ratio. */
    bob=(sprinting && base==0)?0.5f:table[base*2+(ads?1:0)];
    old_cycle=m->ps->bobCycle&255;
    m->ps->bobCycle=((int)((xyspeed/divisor)*bob*(float)msec+(float)old_cycle))&255;
    /* C1 0x413b10 tests the phase crossing after updating bobCycle and then
     * dispatches the footstep event at 0x413b2f.  The retained dispatcher is
     * also the native event producer used by the CoDOL event-ID boundary. */
    m->host->xyspeed=xyspeed;
    /* Live bobCycle divergence trace. ps->bobCycle is the phase C1 draws the
     * scoped weapon sway from and it is reconciled to the client only on a
     * forced hint-3 snapshot, so a rate difference in ANY input here is visible
     * in a sniper scope and essentially nowhere else. One line per 100 ms for
     * the first non-bot client, 1500 lines process-wide. */
    {
        static int lines; static int last_ms[64];
        unsigned c=(unsigned)m->ps->clientNum;
        if(CODOL_TRACE_VERBOSE() && lines<1500 && c<64 && !CODOL_ClientIsBotClient(c) &&
           (m->ps->commandTime-last_ms[c]>=100 || m->ps->commandTime<last_ms[c])) {
            last_ms[c]=m->ps->commandTime; ++lines;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL bob: c%u t%d msec %d xyspeed %.3f psSpeed %d dir %.3f stance %.3f "
                "ads%d lean %.3f sprint%d w%u mss %.3f adsmss %.3f div %.4f bob %.4f "
                "cycle %d->%d\n",
                c,m->ps->commandTime,msec,(double)xyspeed,m->ps->speed,(double)dirscale,
                (double)stance,ads?1:0,(double)m->ps->leanf,sprinting?1:0,
                (unsigned)m->ps->weapon,(double)(weapon?weapon->moveSpeedScale:-1.0f),
                (double)(weapon?weapon->adsMoveSpeedScale:-1.0f),(double)divisor,(double)bob,
                old_cycle,m->ps->bobCycle);
        }
    }
    PM_FootstepEvent(m->host,&m->local,old_cycle,m->ps->bobCycle,
        PM_ShouldMakeFootsteps(m->host));
}

void CODOL_PM_FreeMoveC1(codol_pmove_c1_t *m)
{
    vec3_t direction;
    float f,r,u,length,speed,drop,scale,add,step;
    playerState_t *ps;
    if(!m || !(ps=m->ps)) return;
    f=(m->cmd.direction&1)?127.0f:(m->cmd.direction&2)?-127.0f:0.0f;
    r=(m->cmd.direction&4)?127.0f:(m->cmd.direction&8)?-127.0f:0.0f;
    u=(m->cmd.buttons&C1_BUTTON_JUMP)?127.0f:
      (m->cmd.buttons&0x300u)?-127.0f:0.0f;
    speed=len3(ps->velocity);
    if(speed>0.0f) {
        drop=speed*5.0f*m->local.frametime;
        scale=(speed>drop?(speed-drop):0.0f)/speed;
        ps->velocity[0]*=scale; ps->velocity[1]*=scale; ps->velocity[2]*=scale;
    }
    direction[0]=m->local.forward[0]*f+m->local.right[0]*r;
    direction[1]=m->local.forward[1]*f+m->local.right[1]*r;
    direction[2]=m->local.forward[2]*f+m->local.right[2]*r+u;
    length=len3(direction);
    if(length>0.0f) {
        direction[0]/=length; direction[1]/=length; direction[2]/=length;
        speed=(float)ps->speed*length/127.0f;
        if(ps->pm_type==2) speed*=3.0f;
        else if(ps->pm_type==3) speed*=6.0f;
        add=speed-dot3(ps->velocity,direction);
        if(add>0.0f) {
            step=9.0f*m->local.frametime*speed; if(step>add)step=add;
            ps->velocity[0]+=direction[0]*step;
            ps->velocity[1]+=direction[1]*step;
            ps->velocity[2]+=direction[2]*step;
        }
    }
    ps->origin[0]+=ps->velocity[0]*m->local.frametime;
    ps->origin[1]+=ps->velocity[1]*m->local.frametime;
    ps->origin[2]+=ps->velocity[2]*m->local.frametime;
    ps->groundEntityNum=C1_ENTITYNUM_NONE;
    m->local.walking=m->local.groundPlane=m->local.almostGroundPlane=0;
}
#endif
