/* C1 PM_CheckMantle / PM_MantleMove transcription.
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Authority: C1.exe 0x00409DC0..0x0040A9B0 and
 * alpha0022/docs/mantle_mount.md.  State and flag values are C1 values.
 * The shipped mantle XAnim tree is reused only as animation data; movement,
 * traces, state transitions and snapshot-visible state are owned here.
 */
#ifdef CODOL_SERVER
#include "codol_pmove_c1_mantle.h"
#include "codol_weapon_state.h"
#include "codol_playerstate_ext.h"
#include "codol_assets.h"
#include "codol_ability_math.h"
#include "player.h"
#include "xassets/xanims.h"
#include <math.h>
#include <string.h>

#define C1_BUTTON_JUMP          0x00000400u
#define C1_PMF_MANTLE           0x00000004u
#define C1_PMF_LADDER           0x00000008u
#define C1_PMF_LADDER_FALL      0x00001000u
#define C1_EF_MANTLE            0x00010000u
#define C1_ENTITYNUM_NONE       2047
#define C1_CONTENTS_MANTLE      0x01000000
#define C1_SURF_MANTLE_ON       0x02000000u
#define C1_SURF_MANTLE_OVER     0x04000000u
#define C1_MANTLE_OVER          0x01
#define C1_MANTLE_LEDGE_SOLID   0x02
#define C1_MANTLE_END_CLEAR     0x04
#define C1_MANTLE_HINT          0x08
#define C1_MANTLE_DONE          0x10
#define C1_MANTLE_FORCE         0x20
#define C1_MANTLE_FAST          0x40
/* ability 9 modFastMantle, MSB-first bit of ps+0x4d0 (C1 `shr ecx,0x16`). */
#define C1_ABILITY_FAST_MANTLE  9u

typedef struct {
    vec3_t dir;
    vec3_t origin;
    vec3_t ledge;
    vec3_t end;
    int flags;
    int unused;
} c1_mantle_result_t;

typedef struct { int up, over; float height; } c1_mantle_transition_t;

extern void __cdecl PM_playerTrace(struct pmove_t *pm, trace_t *result,
    const float *start, const float *mins, const float *maxs, const float *end,
    int passEntityNum, int contentMask);
extern XAnim_s *s_mantleAnims;
extern c1_mantle_transition_t s_mantleTrans[8];
extern void __cdecl PM_AddEvent(playerState_t *ps, int event);
extern XAnim_s *__cdecl XAnimCreateAnims(const char *name, int size,
                                         void *(*alloc)(int));
extern void __cdecl XAnimBlend(XAnim_s *anims, unsigned animIndex,
    const char *name, unsigned children, unsigned num, unsigned flags);
extern void __cdecl BG_CreateXAnim(XAnim_s *anims, unsigned animIndex,
                                   const char *name);
extern void __cdecl XAnimGetAbsDelta(const XAnim_s *anims, unsigned animIndex,
    float *rot, float *trans, float time);

/* C1 keeps two mantle XAnim sets, 0x015088bc[2], and every reader indexes
 * them with mantleState.flags bit 6: PM_MantleStart 0x0040a04f..0x0040a067,
 * the over length 0x00409810, the up/over lookup 0x00409870, the root
 * motion 0x004098d0 and PM_MantleMove 0x0040a7f4..0x0040a812. Set 0 is the
 * retained s_mantleAnims. Set 1 is built by the second pass of C1
 * Mantle_CreateAnims 0x00409a40 from the "_fr" names at 0x00cd8640 (11 names
 * per set, name stride 0x2c at 0x00409d9f), and both sets share the
 * s_mantleTrans table 0x00cd85b8. */
static XAnim_s *s_mantleAnimsFast;
static const char *const s_mantleFastAnimNames[11]={
    "mp_mantle_root",
    "mp_mantle_up_57_fr","mp_mantle_up_51_fr","mp_mantle_up_45_fr",
    "mp_mantle_up_39_fr","mp_mantle_up_33_fr","mp_mantle_up_27_fr",
    "mp_mantle_up_21_fr",
    "mp_mantle_over_high_fr","mp_mantle_over_mid_fr","mp_mantle_over_low_fr"
};

/* Called at the end of the retained Mantle_CreateAnims (G_InitGame passes
 * Hunk_AllocXAnimServer). The tree shape matches set 0: an 11-entry XAnim,
 * a blend root at 0 with the ten leaves 1..10. */
void __cdecl CODOL_Mantle_CreateFastAnims(void *(*alloc)(int))
{
    codol_mounted_xanim_t source;
    XAnim_s *anims;
    unsigned i;
    if(s_mantleAnimsFast) return;
    for(i=1;i<11;++i) {
        memset(&source,0,sizeof(source));
        if(CODOL_LoadMountedXAnim(s_mantleFastAnimNames[i],&source)!=1) {
            /* C1 builds this set unconditionally; a missing leaf means the
             * mounted asset set is not C1's. Fast mantle then falls back to
             * set 0, which C1 would not do, so say so. */
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "CoDOL mantle: xanim %s is not mounted; modFastMantle "
                "will use the normal mantle timing\n",s_mantleFastAnimNames[i]);
            return;
        }
    }
    anims=XAnimCreateAnims("PLAYER_MANTLE_FR",11,alloc);
    if(!anims) return;
    XAnimBlend(anims,0,s_mantleFastAnimNames[0],1,10,0);
    for(i=1;i<11;++i) BG_CreateXAnim(anims,i,s_mantleFastAnimNames[i]);
    s_mantleAnimsFast=anims;
}

void __cdecl CODOL_Mantle_ShutdownFastAnims(void)
{
    s_mantleAnimsFast=NULL;
}

static const XAnim_s *mantle_anims(const mantleState_t *state)
{
    if((state->flags&C1_MANTLE_FAST) && s_mantleAnimsFast) return s_mantleAnimsFast;
    return s_mantleAnims;
}

/* C1 0x00409843..0x0040985c: ftol((float)(numframes / framerate) * 1000.0),
 * evaluated at C1's single-precision x87 control word (see
 * codol_ability_math.c), so it is the same float product the retained
 * XAnimGetLengthMsec computes, read here from the selected set. */
static int mantle_anim_ms(const XAnim_s *anims,unsigned index)
{
    const XAnimParts *parts=anims->entries[index].u.parts;
    return CODOL_MantleAnimMsec(parts->numframes,parts->framerate);
}

static void trace_box(codol_pmove_c1_t *move, trace_t *tr, const vec3_t start,
                      const vec3_t mins, const vec3_t maxs, const vec3_t end,
                      int mask)
{
    memset(tr,0,sizeof(*tr));
    PM_playerTrace(move->host,tr,start,mins,maxs,end,move->ps->clientNum,mask);
}

/* C1 Mantle_GetDirection 0x0040A300. */
static int mantle_direction(codol_pmove_c1_t *move,c1_mantle_result_t *out)
{
    const float radius=0.1f, inner=15.0f-radius;
    const vec3_t mins={-0.1f,-0.1f,0.0f},maxs={0.1f,0.1f,70.0f};
    vec3_t forward,start,end;
    trace_t tr;
    float yaw,length,dot;
    yaw=move->ps->viewangles[1]*(float)(M_PI/180.0);
    forward[0]=(float)cos(yaw); forward[1]=(float)sin(yaw); forward[2]=0.0f;
    start[0]=move->ps->origin[0]-forward[0]*inner;
    start[1]=move->ps->origin[1]-forward[1]*inner;
    start[2]=move->ps->origin[2];
    end[0]=move->ps->origin[0]+forward[0]*(inner+20.0f);
    end[1]=move->ps->origin[1]+forward[1]*(inner+20.0f);
    end[2]=move->ps->origin[2];
    trace_box(move,&tr,start,mins,maxs,end,C1_CONTENTS_MANTLE);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1.0f ||
       !((unsigned)tr.sflags&(C1_SURF_MANTLE_ON|C1_SURF_MANTLE_OVER))) return 0;
    out->dir[0]=-tr.normal[0]; out->dir[1]=-tr.normal[1]; out->dir[2]=0.0f;
    length=(float)sqrt(out->dir[0]*out->dir[0]+out->dir[1]*out->dir[1]);
    if(length<=0.0001f) return 0;
    out->dir[0]/=length; out->dir[1]/=length;
    dot=forward[0]*out->dir[0]+forward[1]*out->dir[1];
    if(dot< -1.0f)dot=-1.0f; else if(dot>1.0f)dot=1.0f;
    if((float)(acos(dot)*180.0/M_PI)>60.0f) return 0;
    if((unsigned)tr.sflags&C1_SURF_MANTLE_OVER) out->flags|=C1_MANTLE_OVER;
    return 1;
}

/* C1 Mantle_CheckLedgeAtHeight 0x0040A140. */
static int mantle_ledge(codol_pmove_c1_t *move,c1_mantle_result_t *out,float h)
{
    const vec3_t mins={-15.0f,-15.0f,0.0f};
    vec3_t maxs={15.0f,15.0f,30.0f},start,end;
    trace_t tr;
    start[0]=out->origin[0]; start[1]=out->origin[1]; start[2]=out->origin[2]+h;
    end[0]=start[0]+out->dir[0]*16.0f;
    end[1]=start[1]+out->dir[1]*16.0f;
    end[2]=start[2];
    trace_box(move,&tr,start,mins,maxs,end,move->host->tracemask);
    if(tr.startsolid || tr.fraction<1.0f) return 0;
    memcpy(start,end,sizeof(start)); end[2]=out->origin[2]+18.0f;
    trace_box(move,&tr,start,mins,maxs,end,move->host->tracemask);
    if(tr.startsolid || tr.fraction>=1.0f || !tr.walkable) return 0;
    out->ledge[0]=end[0]; out->ledge[1]=end[1];
    out->ledge[2]=start[2]+tr.fraction*(end[2]-start[2]);
    maxs[2]=50.0f;
    trace_box(move,&tr,out->ledge,mins,maxs,out->ledge,move->host->tracemask);
    return !tr.startsolid;
}

static void mantle_end(codol_pmove_c1_t *move,c1_mantle_result_t *out)
{
    const vec3_t mins={-15.0f,-15.0f,0.0f};
    const vec3_t maxs={15.0f,15.0f,50.0f};
    vec3_t start,end;
    trace_t tr;
    memcpy(out->end,out->ledge,sizeof(out->end));
    if(!(out->flags&C1_MANTLE_OVER)) return;
    memcpy(start,out->ledge,sizeof(start));
    end[0]=start[0]+out->dir[0]*31.0f;
    end[1]=start[1]+out->dir[1]*31.0f;
    end[2]=start[2];
    trace_box(move,&tr,start,mins,maxs,end,move->host->tracemask);
    if(tr.startsolid || tr.fraction<1.0f) { out->flags&=~C1_MANTLE_OVER; return; }
    memcpy(start,end,sizeof(start)); end[2]-=18.0f;
    trace_box(move,&tr,start,mins,maxs,end,move->host->tracemask);
    if(tr.startsolid || tr.fraction<1.0f) { out->flags&=~C1_MANTLE_OVER; return; }
    memcpy(out->end,end,sizeof(out->end));
}

static int mantle_up_ms(const mantleState_t *state)
{
    return mantle_anim_ms(mantle_anims(state),
        (unsigned)s_mantleTrans[state->transIndex].up);
}

/* C1 0x00409810: zero unless the over flag is set. */
static int mantle_over_ms(const mantleState_t *state)
{
    if(!(state->flags&C1_MANTLE_OVER)) return 0;
    return mantle_anim_ms(mantle_anims(state),
        (unsigned)s_mantleTrans[state->transIndex].over);
}

static int mantle_total_ms(const mantleState_t *state)
{
    return mantle_up_ms(state)+mantle_over_ms(state);
}

/* C1 Mantle_GetAnimDelta 0x004098d0. A time <= up plays the up anim at
 * time/up; a later time adds the complete up delta and the over anim at
 * (time-up)/over. The yaw rotation 0x004099e0 multiplies by the constant
 * 0x00c842f8 (the float pi/180 widened to double), stores the angle, sine
 * and cosine as floats and rotates with single-precision products (C1's
 * control word; codol_ability_math.c). */
static void mantle_anim_delta(const mantleState_t *state,int time,float *delta)
{
    const XAnim_s *anims=mantle_anims(state);
    const c1_mantle_transition_t *trans=&s_mantleTrans[state->transIndex];
    float rot[2],over[3],angle,c,s,x,y;
    int up=mantle_up_ms(state),over_ms;
    if(time<=up) {
        XAnimGetAbsDelta(anims,(unsigned)trans->up,rot,delta,(float)time/(float)up);
    } else {
        over_ms=mantle_over_ms(state);
        XAnimGetAbsDelta(anims,(unsigned)trans->up,rot,delta,1.0f);
        XAnimGetAbsDelta(anims,(unsigned)trans->over,rot,over,
                         (float)(time-up)/(float)over_ms);
        delta[0]+=over[0]; delta[1]+=over[1]; delta[2]+=over[2];
    }
    angle=state->yaw*0.0174532923847436905f;
    c=(float)cos(angle); s=(float)sin(angle);
    x=delta[0]; y=delta[1];
    delta[0]=x*c-y*s;
    delta[1]=x*s+y*c;
}

static int fast_mantle_ability(const playerState_t *ps)
{
    const codol_ps_ext_t *ext=CODOL_PlayerStateExtConst(ps);
    return ext && ext->abilities_known &&
           (ext->abilities.masks[C1_ABILITY_FAST_MANTLE>>5]&
            (UINT32_C(0x80000000)>>(C1_ABILITY_FAST_MANTLE&31)));
}

static int nearest_transition(float rise)
{
    int i,best=0;
    float d,bestd=(float)fabs(s_mantleTrans[0].height-rise);
    for(i=1;i<7;++i) {
        d=(float)fabs(s_mantleTrans[i].height-rise);
        if(d<bestd) { best=i; bestd=d; }
    }
    return best;
}

static void mantle_start(codol_pmove_c1_t *move,c1_mantle_result_t *out)
{
    playerState_t *ps=move->ps;
    vec3_t delta;
    int total;
    ps->mantleState.yaw=(float)(atan2(out->dir[1],out->dir[0])*180.0/M_PI);
    ps->mantleState.timer=0;
    ps->mantleState.transIndex=nearest_transition(out->ledge[2]-out->origin[2]);
    ps->mantleState.flags=out->flags&~C1_MANTLE_FORCE;
    /* C1 0x0040a029..0x0040a046: ability 9 modFastMantle selects the "_fr"
     * set for the whole mantle through flag 0x40. */
    if(fast_mantle_ability(ps)) ps->mantleState.flags|=C1_MANTLE_FAST;
    total=mantle_total_ms(&ps->mantleState);
    mantle_anim_delta(&ps->mantleState,total,delta);
    ps->origin[0]=out->end[0]-delta[0];
    ps->origin[1]=out->end[1]-delta[1];
    ps->origin[2]=out->end[2]-delta[2];
    if(ps->pm_flags&C1_PMF_LADDER)
        ps->pm_flags=(ps->pm_flags&~C1_PMF_LADDER)|C1_PMF_LADDER_FALL;
    ps->pm_flags|=C1_PMF_MANTLE;
    ps->eFlags|=C1_EF_MANTLE;
    PM_AddEvent(ps,CODOL_EV_MANTLE_START);
    move->host->mantleStarted=1;
    memcpy(move->host->mantleEndPos,out->end,sizeof(vec3_t));
    move->host->mantleDuration=total;
    if(CODOL_TRACE_VERBOSE())
    Com_Printf(CON_CHANNEL_SERVER,
        "CoDOL C1 mantle start: client %d time %d total %d trans %d flags 0x%x rise %.1f origin (%.1f %.1f %.1f) end (%.1f %.1f %.1f) weapon %d state %d anim 0x%x eF 0x%x\n",
        ps->clientNum,ps->commandTime,total,ps->mantleState.transIndex,
        ps->mantleState.flags,out->ledge[2]-out->origin[2],
        ps->origin[0],ps->origin[1],ps->origin[2],
        out->end[0],out->end[1],out->end[2],
        ps->weapon,ps->weaponstate,(unsigned)ps->weapAnim,(unsigned)ps->eFlags);
}

int CODOL_PM_CheckMantleC1(codol_pmove_c1_t *move)
{
    static const float heights[3]={60.0f,40.0f,20.0f};
    c1_mantle_result_t out;
    trace_t tr;
    const vec3_t mins={-15.0f,-15.0f,0.0f},maxs={15.0f,15.0f,70.0f};
    int i;
    playerState_t *ps;
    if(!move || !move->host || !(ps=move->ps)) return 0;
    ps->mantleState.flags&=~(C1_MANTLE_HINT|C1_MANTLE_DONE);
    if(ps->pm_type>=8 || (ps->pm_flags&C1_PMF_MANTLE) || (ps->eFlags&0x0c)) return 0;
    memset(&out,0,sizeof(out)); memcpy(out.origin,ps->origin,sizeof(vec3_t));
    if(!mantle_direction(move,&out)) return 0;
    for(i=0;i<3 && !mantle_ledge(move,&out,heights[i]);++i) {}
    if(i==3) return 0;
    ps->mantleState.flags|=C1_MANTLE_HINT; out.flags|=C1_MANTLE_HINT;
    if(!(move->cmd.buttons&C1_BUTTON_JUMP) && !(ps->mantleState.flags&C1_MANTLE_FORCE)) return 1;
    mantle_end(move,&out);
    if(!(ps->eFlags&4)) {
        trace_box(move,&tr,out.ledge,mins,maxs,out.ledge,move->host->tracemask);
        if(tr.startsolid) out.flags|=C1_MANTLE_LEDGE_SOLID;
        trace_box(move,&tr,out.end,mins,maxs,out.end,move->host->tracemask);
        if(!tr.startsolid) out.flags|=C1_MANTLE_END_CLEAR;
    }
    mantle_start(move,&out);
    return 1;
}

void CODOL_PM_MantleMoveC1(codol_pmove_c1_t *move)
{
    playerState_t *ps;
    vec3_t before,after,delta;
    int old,next,total,applied;
    float inv;
    if(!move || !(ps=move->ps) || !(ps->pm_flags&C1_PMF_MANTLE)) return;
    ps->mantleState.flags&=~C1_MANTLE_HINT;
    if(ps->mantleState.flags&C1_MANTLE_LEDGE_SOLID) PM_AddEvent(ps,7);
    total=mantle_total_ms(&ps->mantleState);
    old=ps->mantleState.timer;
    next=old+move->local.msec; if(next>total)next=total;
    ps->mantleState.timer=next; applied=next-old;
    mantle_anim_delta(&ps->mantleState,old,before);
    mantle_anim_delta(&ps->mantleState,next,after);
    delta[0]=after[0]-before[0]; delta[1]=after[1]-before[1]; delta[2]=after[2]-before[2];
    ps->origin[0]+=delta[0]; ps->origin[1]+=delta[1]; ps->origin[2]+=delta[2];
    if(applied>0) {
        inv=1000.0f/(float)applied;
        ps->velocity[0]=delta[0]*inv; ps->velocity[1]=delta[1]*inv; ps->velocity[2]=delta[2]*inv;
    }
    if(next==total) {
        ps->pm_flags&=~C1_PMF_MANTLE;
        move->host->mantleStarted=0;
        if(ps->mantleState.flags&C1_MANTLE_END_CLEAR) PM_AddEvent(ps,6);
        /* C1 0x40a949 gates BOTH the landing event and the EF_MANTLE clear on
         * mantleState 0x4, and 0x40a102/0x40a984 are the only setter/clearer
         * of eFlags 0x10000 in the whole image, so a mantle that never set
         * END_CLEAR strands the bit for the life of the entity. This port can
         * reach that state where C1 does not: CODOL_PM_CheckMantleC1 runs the
         * ledge/end probes only when !(ps->eFlags & 4), so every mantle begun
         * crouched -- which is how the bots do it -- finishes with 0x10000
         * still up, and other clients keep drawing that player in the mantle
         * pose with no weapon attached. A completed mantle always clears the
         * bit; only the landing event stays gated. */
        ps->eFlags&=~C1_EF_MANTLE;
        if(ps->velocity[2]>0.0f) ps->velocity[2]=0.0f;
        ps->mantleState.flags|=C1_MANTLE_DONE;
        if(CODOL_TRACE_VERBOSE())
        Com_Printf(CON_CHANNEL_SERVER,
            "CoDOL C1 mantle end: client %d time %d total %d trans %d flags 0x%x origin (%.1f %.1f %.1f) weapon %d state %d anim 0x%x eF 0x%x weapFlags 0x%x\n",
            ps->clientNum,ps->commandTime,total,ps->mantleState.transIndex,
            ps->mantleState.flags,ps->origin[0],ps->origin[1],ps->origin[2],
            ps->weapon,ps->weaponstate,(unsigned)ps->weapAnim,(unsigned)ps->eFlags,
            (unsigned)ps->weapFlags);
    }
}
#endif
