/* Native actor capsule slide/step/gravity. T5 actor_physics.cpp supplies the
 * behavioral reference; no actor_s offsets, player commands or fake proxies.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_actor_physics.h"
#include "server.h"
#include "g_shared.h"
#include <math.h>
#include <string.h>
static float dot(const float *a,const float *b) {return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
extern "C" void CODOL_ActorsPassable(gentity_s *self,int passable);
#define OVERCLIP 1.001f /* Q3 PM_SlideMove: clip slightly past the plane */
static void sweep(gentity_s *e,trace_t *t,const float *a,const float *b) {
    G_TraceCapsule(t,a,e->r.mins,e->r.maxs,b,e->s.number,e->clipmask);
}
/* A steep-face landing can persist for many 50-ms animation wishes even
 * though the actor has a clear authored step path a few units farther on.
 * Keep the exceptional look-ahead bounded to a sustained blocked actor. */
static int stepBlockedFrames[MAX_GENTITIES];
static int stepFallbackTime[MAX_GENTITIES];
static int slide(gentity_s *e,float *pos,float *vel,float dt) {
    float planes[5][3]; int count=0;
    for(int bump=0;bump<4;++bump) {
        float end[3];for(int i=0;i<3;++i)end[i]=pos[i]+vel[i]*dt;
        trace_t t;sweep(e,&t,pos,end);
        if(t.allsolid || t.startsolid) {memset(vel,0,12);return 0;}
        for(int i=0;i<3;++i)pos[i]+=(end[i]-pos[i])*t.fraction;
        if(t.fraction==1)return 1;
        dt*=1-t.fraction;
        if(count==5){memset(vel,0,12);return 1;}
        {
            int dup;
            for(dup=0;dup<count;++dup)if(dot(t.normal,planes[dup])>0.99f)break;
            if(dup<count){for(int k=0;k<3;++k)vel[k]+=t.normal[k];continue;}
        }
        memcpy(planes[count++],t.normal,12);
        float original[3];memcpy(original,vel,12);
        int i;
        for(i=0;i<count;++i) {
            float into=dot(original,planes[i]);
            if(into>=0)continue;
            into*=OVERCLIP;
            for(int k=0;k<3;++k)vel[k]=original[k]-planes[i][k]*into;
            int j;for(j=0;j<count;++j)if(j!=i && dot(vel,planes[j])<-.001f)break;
            if(j==count)break;
        }
        if(i==count && count>=2) {
            float crease[3]={planes[0][1]*planes[1][2]-planes[0][2]*planes[1][1],
                planes[0][2]*planes[1][0]-planes[0][0]*planes[1][2],
                planes[0][0]*planes[1][1]-planes[0][1]*planes[1][0]};
            float len=dot(crease,crease);
            if(len<.000001f){memset(vel,0,12);return 1;}
            float along=dot(original,crease)/len;
            for(int k=0;k<3;++k)vel[k]=crease[k]*along;
            for(int j=2;j<count;++j)if(dot(vel,planes[j])<-.001f){memset(vel,0,12);return 1;}
        }
    }
    return 1;
}
static int physicsMove(gentity_s *e,codol_actor_physics_t *state,
    const float *wish,float dt,float gravity,float step) {
    if(!e || !e->r.inuse || !e->clipmask || !state || !wish || !isfinite(dt) ||
       dt<=0 || dt>.25f || !isfinite(gravity) || gravity<0 || !isfinite(step) || step<0)return 0;
    for(int i=0;i<3;++i)if(!isfinite(wish[i]))return 0;
    float start[3],pos[3],vel[3],down[3];memcpy(start,e->r.currentOrigin,12);memcpy(pos,start,12);
    memcpy(down,start,12);down[2]-=.25f;
    trace_t ground;sweep(e,&ground,start,down);
    float groundFraction, groundNormalZ;
    int stepTried=0, stepUpClear=0, stepSlideClear=0, stepLandingWalkable=0, stepChosen=0;
    float stepUpFraction=-1.0f, stepLandingFraction=-1.0f, stepLandingNormalZ=0.0f;
    float stepRaisedXY=-1.0f, stepBaseXY=-1.0f;
    state->blocked=0;
    int unstuck=0;
    if(ground.startsolid || ground.allsolid) {
        /* MEASURED 2026-09-21 (docs/CODOL_ZOMBIE_WINDOW_20260921.md part 2):
         * every zm_prototype_sh yard wedge (1400 -7xx 8), (1414 -1098 8),
         * (844 -843 8) sat on the same shape -- a raised slab whose top has
         * a 1.4-2 unit groove right behind its lip.  The capsule settles into
         * the groove, its footprint overlaps the lip, and from then on every
         * sweep starts solid: phys ok 7 rej 53, grounded 0, frozen for good.
         * Lift the start by up to the step height until the capsule stands
         * clear and move from there; an actor that is clear nowhere within a
         * step is genuinely embedded and the move is still refused. */
        float lifted[3];memcpy(lifted,start,12);
        for(float lift=2.0f;lift<=step && !unstuck;lift+=2.0f) {
            lifted[2]=start[2]+lift;
            trace_t probe;sweep(e,&probe,lifted,lifted);
            unstuck=!probe.startsolid && !probe.allsolid;
        }
        if(!unstuck)return 0;
        memcpy(start,lifted,12);memcpy(pos,start,12);++state->unstuck;
        memcpy(down,start,12);down[2]-=.25f;sweep(e,&ground,start,down);
    }
    groundFraction=ground.fraction;groundNormalZ=ground.normal[2];
    /* An actor lifted out of the floor was standing on it. */
    int grounded=unstuck || (!ground.startsolid && !ground.allsolid && ground.fraction<1 && ground.normal[2]>=.7f);
    /* Step logic also for an actor whose ground trace hit a lip or a wall
     * (normal below .7) but has floor within a step below it. */
    int nearGround=grounded;
    if(!nearGround && step>0) {
        float below[3];memcpy(below,start,12);below[2]-=step;
        trace_t t;sweep(e,&t,start,below);
        nearGround=!t.startsolid && !t.allsolid && t.fraction<1;
    }
    vel[0]=wish[0]/dt;vel[1]=wish[1]/dt;
    vel[2]=grounded?fmaxf(0,wish[2]/dt):state->velocity[2]+wish[2]/dt;
    float finalZ=vel[2]-gravity*dt;
    if(!grounded)vel[2]=(vel[2]+finalZ)*.5f;
    float startVel[3];memcpy(startVel,vel,12);
    if(!slide(e,pos,vel,dt))return 0;
    if(nearGround && step>0) {
        stepTried=1;
        float up[3];memcpy(up,start,12);up[2]+=step;
        trace_t t;sweep(e,&t,start,up);
        stepUpFraction=t.fraction;
        if(!t.startsolid && !t.allsolid && t.fraction>0) {
            stepUpClear=1;
            float raised[3],raisedVel[3];memcpy(raised,start,12);raised[2]+=step*t.fraction;
            memcpy(raisedVel,startVel,12);
            if(slide(e,raised,raisedVel,dt)) {
                stepSlideClear=1;
                /* Include a small landing margin below the original floor.
                 * On level ground the raised sweep ends exactly step units
                 * above the floor.  A step-unit drop only touches it at
                 * fraction 1, which the ground test below treats as no hit.
                 * The ordinary slide then stays pinned to the floor's
                 * fraction-0 contact even though the raised path is clear. */
                const float landingDrop=step+0.25f;
                memcpy(down,raised,12);down[2]-=landingDrop;
                sweep(e,&t,raised,down);
                stepLandingFraction=t.fraction;stepLandingNormalZ=t.normal[2];
                if(!t.startsolid && !t.allsolid && t.fraction<1 && t.normal[2]>=.7f) {
                    stepLandingWalkable=1;
                    raised[2]-=landingDrop*t.fraction;
                    float a=(raised[0]-start[0])*(raised[0]-start[0])+(raised[1]-start[1])*(raised[1]-start[1]);
                    float b=(pos[0]-start[0])*(pos[0]-start[0])+(pos[1]-start[1])*(pos[1]-start[1]);
                    stepRaisedXY=sqrtf(a);stepBaseXY=sqrtf(b);
                    if(a>b){memcpy(pos,raised,12);memcpy(vel,raisedVel,12);stepChosen=1;}
                }
            }
        }
    }
    int fallbackLanded=0;
    float wishedXY=wish[0]*wish[0]+wish[1]*wish[1];
    float movedXY=(pos[0]-start[0])*(pos[0]-start[0])+
        (pos[1]-start[1])*(pos[1]-start[1]);
    int steepBlocked=stepTried && stepUpClear && stepSlideClear &&
        stepLandingFraction<1.0f && stepLandingNormalZ<0.7f &&
        wishedXY>0.0025f && movedXY<0.25f*wishedXY;
    if(e->s.number>=0 && e->s.number<MAX_GENTITIES) {
        int entnum=e->s.number;
        if(steepBlocked) {
            if(stepBlockedFrames[entnum]<3) ++stepBlockedFrames[entnum];
        } else stepBlockedFrames[entnum]=0;
        if(steepBlocked && stepBlockedFrames[entnum]>=3 && step<=18.0f &&
            (!stepFallbackTime[entnum] || level.time<stepFallbackTime[entnum] ||
             level.time-stepFallbackTime[entnum]>=1000)) {
            stepFallbackTime[entnum]=level.time; /* also rate-limit failed probes */
            float wishLength=sqrtf(wishedXY);
            float lift=step*stepUpFraction;
            float raisedStart[3]={start[0],start[1],start[2]+lift};
            for(float reach=2.0f;reach<=16.0f;reach+=2.0f) {
                if(reach<=wishLength) continue;
                float raisedEnd[3]={
                    raisedStart[0]+wish[0]/wishLength*reach,
                    raisedStart[1]+wish[1]/wishLength*reach,
                    raisedStart[2]
                };
                trace_t forward,land,clear;
                sweep(e,&forward,raisedStart,raisedEnd);
                /* Farther samples cannot be clear if the elevated capsule
                 * already hit a solid wall on the same straight segment. */
                if(forward.startsolid || forward.allsolid || forward.fraction<1.0f) break;
                float landEnd[3]={raisedEnd[0],raisedEnd[1],raisedEnd[2]-lift-0.25f};
                sweep(e,&land,raisedEnd,landEnd);
                if(land.startsolid || land.allsolid || land.fraction>=1.0f ||
                    land.normal[2]<0.7f) continue;
                float candidate[3]={raisedEnd[0],raisedEnd[1],
                    raisedEnd[2]-(lift+0.25f)*land.fraction};
                sweep(e,&clear,candidate,candidate);
                if(clear.startsolid || clear.allsolid) continue;
                memcpy(pos,candidate,sizeof(candidate));
                vel[0]=startVel[0];vel[1]=startVel[1];vel[2]=0;
                fallbackLanded=1;
                stepBlockedFrames[entnum]=0;
                Com_Printf(CON_CHANNEL_SERVER,
                    "CoDOL actor physics: ent %d bounded step %.1f units, rise %.2f, landing normal z %.2f after %d blocked frames\n",
                    entnum,reach,candidate[2]-start[2],land.normal[2],3);
                break;
            }
        }
    }
    memcpy(down,pos,12);down[2]-=.25f;sweep(e,&ground,pos,down);
    state->grounded=fallbackLanded || (!ground.startsolid && !ground.allsolid &&
        ground.fraction<1 && ground.normal[2]>=.7f);
    if(fallbackLanded || (state->grounded && vel[2]<=0))vel[2]=0;
    else if(!grounded && vel[2]<0)vel[2]=finalZ;
    memcpy(state->velocity,vel,12);
    {
        float wl=wish[0]*wish[0]+wish[1]*wish[1];
        float gx=pos[0]-start[0],gy=pos[1]-start[1];
        state->blocked=wl>0.0025f && gx*gx+gy*gy<0.25f*wl;
    }
    /* One actual step-branch verdict per actor per five seconds while it is
     * throttled.  The 16-unit wedge probes are only geometric leads; root
     * motion requests much shorter per-frame moves, so this records whether
     * the real up/slide/landing candidate existed and why it was selected. */
    if(state->blocked && step>0 && e->s.number>=0 && e->s.number<MAX_GENTITIES) {
        static int lastDiag[MAX_GENTITIES];
        int *last=&lastDiag[e->s.number];
        if(!*last || level.time<*last || level.time-*last>=5000) {
            *last=level.time;
            Com_Printf(CON_CHANNEL_SERVER,
                "CoDOL actor physics: ent %d step at (%.1f %.1f %.1f) wish (%.3f %.3f %.3f) moved (%.3f %.3f %.3f) dt %.3f; ground f %.3f nz %.2f grounded %d near %d; trial %d up f %.3f ok %d raisedSlide %d landing f %.3f nz %.2f ok %d; raisedXY %.3f baseXY %.3f chosen %d\n",
                e->s.number,start[0],start[1],start[2],wish[0],wish[1],wish[2],
                pos[0]-start[0],pos[1]-start[1],pos[2]-start[2],dt,
                groundFraction,groundNormalZ,grounded,nearGround,stepTried,
                stepUpFraction,stepUpClear,stepSlideClear,stepLandingFraction,
                stepLandingNormalZ,stepLandingWalkable,stepRaisedXY,stepBaseXY,stepChosen);
        }
    }
    G_SetOrigin(e,pos);SV_LinkEntity(e);
    return 1;
}
int CODOL_ActorPhysicsMove(gentity_s *e,codol_actor_physics_t *state,
    const float *wish,float dt,float gravity,float step) {
    CODOL_ActorsPassable(e,1);
    int moved=physicsMove(e,state,wish,dt,gravity,step);
    CODOL_ActorsPassable(e,0);
    return moved;
}
static int physicsMoveMode(gentity_s *e,codol_actor_physics_t *state,
    const float *wish,float dt,float gravity,float step,int mode);
int CODOL_ActorPhysicsMoveMode(gentity_s *e,codol_actor_physics_t *state,
    const float *wish,float dt,float gravity,float step,int mode)
{
    CODOL_ActorsPassable(e,1);
    int moved=physicsMoveMode(e,state,wish,dt,gravity,step,mode);
    CODOL_ActorsPassable(e,0);
    return moved;
}
static int physicsMoveMode(gentity_s *e,codol_actor_physics_t *state,
    const float *wish,float dt,float gravity,float step,int mode)
{
    if(!e || !e->r.inuse || !state || !wish || !isfinite(dt) || dt<=0 || dt>.25f)return 0;
    for(int i=0;i<3;++i)if(!isfinite(wish[i]))return 0;
    if(mode==0)return physicsMove(e,state,wish,dt,gravity,step);
    float pos[3],vel[3];memcpy(pos,e->r.currentOrigin,12);
    state->blocked=0;
    for(int i=0;i<3;++i)vel[i]=wish[i]/dt;
    if(mode==1) { // T5 AIPHYS_NOCLIP consumes authored animation displacement.
        for(int i=0;i<3;++i)pos[i]+=wish[i];
    } else if(mode==2) { // T5 AIPHYS_NOGRAVITY: capsule slide, no gravity/step.
        if(!e->clipmask || !slide(e,pos,vel,dt))return 0;
    } else if(mode==3) {
        // T5 AIPhys_ZOnlyPhysicsMove resets incoming Z velocity, then calls
        // StepSlideMove(gravity=1,zonly=1). It still collides horizontally;
        // zonly suppresses pre-slide ground clipping, not wall collision.
        float previousZ=state->velocity[2];
        state->velocity[2]=0;
        int moved=physicsMove(e,state,wish,dt,gravity,step);
        if(!moved)state->velocity[2]=previousZ;
        return moved;
    } else return 0;
    memcpy(state->velocity,vel,12);
    if(mode!=3)state->grounded=0;
    G_SetOrigin(e,pos);SV_LinkEntity(e);
    return 1;
}

#endif
