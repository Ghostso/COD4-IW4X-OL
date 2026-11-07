/* Combat-training AI adapted from OpenBLOPS server_mp/sv_bot_mp.cpp:
 * script goals/enemies, visible threat acquisition and memory, reaction delay,
 * angular tracking, reload and per-fire-type pacing. Navigation uses the
 * supplied CoDOL CSV graph instead of assuming T5 pathnode binary layouts.
 * This is native usercmd gameplay; no teleporting or scripted bullet damage.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_bot.h"
#include "codol_bot_nav.h"
#include "codol_bot_loadout.h"
#include "../assets/codol_assets.h"
#include "codol_game.h"
#include "codol_weapon_input.h"
#include "codol_weapon_state.h"
#include "../weapon/codol_weapon_bits.h"
#include "server.h"
#include "sv_bots.h"
#include "g_shared.h"
#include "scr_vm.h"
#include "scr_vm_functions.h"
#include "cm_public.h"
#include "bg_public.h"
#include "cvar.h"
#include "cscr_stringlist.h"
#include "dobj.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
#define PI 3.14159265358979323846f
#define PATH_CAP 2048
/* These are C1 command buttons, not T5's 64-bit button array. */
#define FIRE 1u
#define SPRINT 2u
#define RELOAD 16u
#define USE 40u
#define PRONE 256u
#define CROUCH 512u
#define JUMP 1024u
#define ADS 2048u
#define ADS_TRIGGER 0x100000u
#define MELEE 4u
typedef struct {
    int enabled,generation,lastTime,alive,deathTime,enemy,enemyGeneration,scriptEnemy;
    int acquired,lastSeen,reactionEnd,aimEnd,fireNext,adsEnd,useEnd,pathNext,stuckSince;
    int scriptGoal,pathLength,pathIndex,goalNode,pendingNotify,lastJump;
    /* Stuck escalation (nudge -> repath -> regoal), crowd and diagnostics. */
    int stuckLevel,nudgeUntil,nudgeSide,stuckLogged,crowdSince,crowdLogged,diagNext,stuckCount,crowdCount;
    /* Mantle attempts (bot-side C1 PM_CheckMantle probe) and ladder state. */
    int mantleUntil,mantleNext,mantleStart,mantleAttempts,mantleOk,onLadder,ladderCount;
    /* Close-quarters melee cooldown; the lunge needs a rising button edge. */
    int meleeNext;
    /* Last weapon this bot was seen holding. A C1 client names its held weapon
     * in every usercmd and therefore re-raises it by itself after the engine
     * holsters it; a bot has no such client, so it remembers it here. */
    unsigned heldWeapon;
    float mantleYaw,mantleRise;
    struct {int from,to,until;} blocked[16];
    unsigned blockedCursor;
    float goal[3],radius,lastKnown[3],lastPosition[3],stuckPosition[3];
    unsigned short path[PATH_CAP];
    unsigned random;
} bot_t;
static bot_t bots[MAX_CLIENTS];
static cvar_t *fov,*closeDistance,*difficulty;
typedef struct {
    int minAimResponse,maxAimResponse,reactionTime,minFireTime,maxFireTime,adsAllowed;
    float yawSpeed,yawSpeedAds,pitchSpeed,pitchSpeedAds;
} bot_difficulty_t;
static bot_difficulty_t botDifficulties[4];
static int botDifficultiesReady,botDifficultyRetryTime;
static const char *botDifficultyNames[]={"recruit","regular","hardened","veteran",NULL};

/* The mounted 1.1.1.13 mp/botdifficultytable.csv has a property in column 0
 * and the four named difficulty values in columns 1..4. Copy validated values:
 * archive tables are retired on zone transitions. Never silently substitute
 * hand-tuned ranges if this exact-build asset is unavailable. */
static const char *difficulty_cell(const codol_engine_table_t *table,const char *key,int tier)
{
    int row;
    for(row=0;row<table->rowCount;++row)
        if(table->values[row*table->columnCount] && !strcmp(table->values[row*table->columnCount],key))
            return table->values[row*table->columnCount+tier+1];
    return NULL;
}
static int difficulty_int(const codol_engine_table_t *table,const char *key,int tier,int low,int high,int *out)
{
    const char *cell=difficulty_cell(table,key,tier);char *end;long value;
    if(!cell || !*cell)return 0;
    value=strtol(cell,&end,10);
    if(*end || value<low || value>high)return 0;
    *out=(int)value;return 1;
}
static int difficulty_float(const codol_engine_table_t *table,const char *key,int tier,float low,float high,float *out)
{
    const char *cell=difficulty_cell(table,key,tier);char *end;float value;
    if(!cell || !*cell)return 0;
    value=strtof(cell,&end);
    if(*end || !isfinite(value) || value<low || value>high)return 0;
    *out=value;return 1;
}
static int load_difficulties(void)
{
    const codol_engine_table_t *table=NULL;bot_difficulty_t parsed[4];int tier;
    if(CODOL_LoadEngineStringTable("mp/botdifficultytable.csv",&table)!=1 ||
       !table || table->columnCount!=5 || table->rowCount<40 || !table->values)return 0;
    for(tier=0;tier<4;++tier){
        bot_difficulty_t *p=&parsed[tier];
        if(!difficulty_int(table,"minAimResponse",tier,0,5000,&p->minAimResponse) ||
           !difficulty_int(table,"maxAimResponse",tier,0,5000,&p->maxAimResponse) ||
           !difficulty_int(table,"reactionTime",tier,0,5000,&p->reactionTime) ||
           !difficulty_int(table,"minFireTime",tier,1,5000,&p->minFireTime) ||
           !difficulty_int(table,"maxFireTime",tier,1,5000,&p->maxFireTime) ||
           !difficulty_int(table,"adsAllowed",tier,0,1,&p->adsAllowed) ||
           !difficulty_float(table,"yawSpeed",tier,0.1f,20,&p->yawSpeed) ||
           !difficulty_float(table,"yawSpeedAds",tier,0.1f,20,&p->yawSpeedAds) ||
           !difficulty_float(table,"pitchSpeed",tier,0.1f,20,&p->pitchSpeed) ||
           !difficulty_float(table,"pitchSpeedAds",tier,0.1f,20,&p->pitchSpeedAds) ||
           p->maxAimResponse<p->minAimResponse || p->maxFireTime<p->minFireTime)
            return 0;
    }
    memcpy(botDifficulties,parsed,sizeof(parsed));botDifficultiesReady=1;
    Com_Printf(CON_CHANNEL_AI,"CoDOL bot difficulty: loaded recruit/regular/hardened/veteran from mounted mp/botdifficultytable.csv\n");
    return 1;
}
static const bot_difficulty_t *bot_difficulty(void)
{
    int tier;
    if(!difficulty)return NULL;
    if(!botDifficultiesReady && svs.time>=botDifficultyRetryTime){
        botDifficultyRetryTime=svs.time+5000;
        if(!load_difficulties())Com_PrintWarning(CON_CHANNEL_AI,"CoDOL bot difficulty: exact table unavailable or invalid; bots paused\n");
    }
    if(!botDifficultiesReady)return NULL;
    tier=difficulty->integer;
    if(tier<0 || tier>=4)return NULL;
    return &botDifficulties[tier];
}
static float dist2(const float *a,const float *b)
{float x=a[0]-b[0],y=a[1]-b[1],z=a[2]-b[2];return x*x+y*y+z*z;}
static int random_range(bot_t *b,int low,int high)
{unsigned n;b->random=b->random*1664525u+1013904223u;n=b->random;if(high<low)high=low;return low+(int)(n%(unsigned)(high-low+1));}
static float angle180(float v){v=fmodf(v+180.0f,360.0f);if(v<0)v+=360;return v-180;}
static void eye(const gentity_t *ent,float *out)
{memcpy(out,ent->client->ps.origin,12);out[2]+=ent->client->ps.viewHeightCurrent;}
static int visible(const gentity_t *bot,const gentity_t *target,float *point)
{
    trace_t tr;float start[3];eye(bot,start);eye(target,point);point[2]-=target->client->ps.viewHeightCurrent*0.25f;
    G_LocationalTrace(&tr,start,point,bot->s.number,0x2806831,NULL);
    return !tr.startsolid && (tr.fraction>=1.0f || (tr.hitType==TRACE_HITTYPE_ENTITY && tr.hitId==target->s.number));
}
static int enemy_valid(const gentity_t *self,const gentity_t *target)
{
    int team=self->client->sess.cs.team;
    return target!=self && target->r.inuse && target->client && target->health>0 &&
        target->client->sess.sessionState==SESS_STATE_PLAYING && target->client->sess.cs.team!=TEAM_SPECTATOR &&
        (!team || target->client->sess.cs.team!=team);
}
static void clear_enemy(bot_t *b)
{b->enemy=-1;b->enemyGeneration=0;b->scriptEnemy=0;b->lastSeen=0;b->acquired=0;b->reactionEnd=0;b->aimEnd=0;}
static int acquire(bot_t *b,gentity_t *self,int now,const bot_difficulty_t *profile)
{
    int i,best=-1,checkedEnemy=-1;float bestDistance=1e30f,point[3],dx,dy,heading,distance;
    gentity_t *target;
    if(b->enemy>=0){
        target=&g_entities[b->enemy];
        if(target->useCount!=b->enemyGeneration || !enemy_valid(self,target))clear_enemy(b);
        else {
            checkedEnemy=b->enemy;
            if(visible(self,target,point)){memcpy(b->lastKnown,point,12);b->lastSeen=now;best=b->enemy;bestDistance=dist2(self->client->ps.origin,point);}
            else if(now-b->lastSeen>10000)clear_enemy(b); /* T5 threat memory. */
        }
    }
    if(b->scriptEnemy || (best>=0 && bestDistance<closeDistance->value*closeDistance->value))return best>=0;
    /* T5 filters team/alive first, then FOV and actual sight before threat
     * selection. There is no knowledge of enemies behind walls. */
    for(i=0;i<level.maxclients;++i){
        /* This command already traced the current enemy, whether visible or
         * occluded. No VM callback or simulation step occurs during acquire. */
        if(i==checkedEnemy)continue;
        target=&g_entities[i];if(!enemy_valid(self,target))continue;
        dx=target->client->ps.origin[0]-self->client->ps.origin[0];dy=target->client->ps.origin[1]-self->client->ps.origin[1];
        heading=atan2f(dy,dx)*180/PI;
        if(fabsf(angle180(heading-self->client->ps.viewangles[1]))>fov->value*0.5f)continue;
        if(!visible(self,target,point))continue;
        distance=dist2(self->client->ps.origin,point);
        if(distance<bestDistance){best=i;bestDistance=distance;}
    }
    if(best>=0 && best!=b->enemy){
        b->enemy=best;b->enemyGeneration=g_entities[best].useCount;b->acquired=now;b->lastSeen=now;
        b->reactionEnd=now+profile->reactionTime;
        b->aimEnd=now+random_range(b,profile->minAimResponse,profile->maxAimResponse);
        eye(&g_entities[best],b->lastKnown);b->lastKnown[2]-=g_entities[best].client->ps.viewHeightCurrent*0.25f;
        b->pathNext=0;
    }
    /* True only for the final selected enemy actually seen in this command.
     * Its exact tested aim point is now in lastKnown; memory alone is false. */
    return best>=0;
}
/* T5 clears stalled paths after two seconds and its path subsystem removes
 * disconnected links. The CSV graph has no T5 dynamic pathnode object: keep
 * a bounded per-bot exclusion cache instead of retrying the identical edge. */
static int allow_edge(int from,int to,void *context)
{
    bot_t *b=context;int i;
    for(i=0;i<16;++i)if(b->blocked[i].until>svs.time &&
        b->blocked[i].from==from && b->blocked[i].to==to)return 0;
    return 1;
}
static void block_edge(bot_t *b,int from,int to,int now)
{
    unsigned slot=b->blockedCursor++%16;
    b->blocked[slot].from=from;b->blocked[slot].to=to;b->blocked[slot].until=now+5000;
}
static int nearest_reachable(bot_t *b,const gentity_t *self)
{
    int i,best=-1;float minimum=256*256,start[3],end[3],d;trace_t tr;const float *point;
    memcpy(start,self->client->ps.origin,12);start[2]+=24;
    for(i=0;i<CODOL_BotNavCount();++i){
        point=CODOL_BotNavPoint(i);d=dist2(point,self->client->ps.origin);
        if(d>=minimum || !allow_edge(-1,i,b))continue;
        memcpy(end,point,12);end[2]+=24;
        G_LocationalTrace(&tr,start,end,self->s.number,0x2814011,NULL);
        if(tr.startsolid||tr.fraction<1)continue;
        minimum=d;best=i;
    }
    return best;
}
static int bot_active(int slot,const gentity_t *self)
{
    const gentity_t *ent=&g_entities[slot];
    return ent!=self && bots[slot].enabled && bots[slot].alive && ent->r.inuse && ent->client && ent->health>0 &&
        ent->client->sess.sessionState==SESS_STATE_PLAYING;
}
/* Goal reservation: a roaming destination another live bot already holds
 * (or one within 160 units of it) is not picked again while it is held. */
static int node_claimed(int node,const gentity_t *self)
{
    int i;const float *p=CODOL_BotNavPoint(node);
    if(!p)return 1;
    for(i=0;i<MAX_CLIENTS;++i){
        if(!bot_active(i,self))continue;
        if(bots[i].goalNode==node)return 1;
        if(bots[i].goalNode>=0 && bots[i].pathIndex<bots[i].pathLength && dist2(p,CODOL_BotNavPoint(bots[i].goalNode))<160*160)return 1;
    }
    return 0;
}
static int pick_roam_goal(bot_t *b,const gentity_t *self)
{
    int i,n=CODOL_BotNavCount(),to=0;
    for(i=0;i<12 && n>0;++i){to=random_range(b,0,n-1);if(!node_claimed(to,self) && dist2(CODOL_BotNavPoint(to),self->client->ps.origin)>256*256)break;}
    return to;
}
/* Separation steering: push away from every living player (any team) inside
 * a 48-unit ring; the 2D vector is blended into the movement direction. */
static int separation(const gentity_t *self,float *out)
{
    int i,n=0;float d,dx,dy,w;const gentity_t *ent;
    out[0]=out[1]=0;
    for(i=0;i<level.maxclients;++i){
        ent=&g_entities[i];
        if(ent==self||!ent->r.inuse||!ent->client||ent->health<=0||ent->client->sess.sessionState!=SESS_STATE_PLAYING)continue;
        dx=self->client->ps.origin[0]-ent->client->ps.origin[0];dy=self->client->ps.origin[1]-ent->client->ps.origin[1];
        if(fabsf(self->client->ps.origin[2]-ent->client->ps.origin[2])>72)continue;
        d=sqrtf(dx*dx+dy*dy);if(d>48)continue;
        if(d<1){dx=(float)((i+self->s.number)&1?1:-1);dy=(float)((i&2)?1:-1);d=1.4142f;}
        w=(48-d)/48;out[0]+=dx/d*w;out[1]+=dy/d*w;++n;
    }
    return n;
}
static void route(bot_t *b,const gentity_t *self,int now)
{
    int from,to;const float *p;
    if(now<b->pathNext)return;
    b->pathNext=now+1000;
    if(b->scriptGoal)to=CODOL_BotNavNearest(b->goal);
    else if(b->enemy>=0)to=CODOL_BotNavNearest(b->lastKnown);
    else if(b->pathLength>0 && b->goalNode>=0 && b->goalNode<CODOL_BotNavCount() && dist2(self->client->ps.origin,CODOL_BotNavPoint(b->goalNode))>64*64)to=b->goalNode;
    else to=pick_roam_goal(b,self);
    /* A failed roaming route must choose a new destination on the next
     * refresh. Keeping an unreachable goal with an empty path leaves the
     * bot idle forever, before movement's stuck detector can run.
     * A periodic goal refresh must not send a moving bot back to its nearest
     * graph node. Retain progress while this route still reaches that goal. */
    if(to==b->goalNode && b->pathIndex<b->pathLength)return;
    b->pathLength=0;b->pathIndex=0;
    from=nearest_reachable(b,self);
    if(from<0){if(b->scriptGoal){b->scriptGoal=0;b->pendingNotify=2;}return;}
    p=CODOL_BotNavPoint(from);if(dist2(p,self->client->ps.origin)>256*256)return;
    b->goalNode=to;b->pathLength=CODOL_BotNavRouteFiltered(from,to,b->path,PATH_CAP,allow_edge,b);
    if(!b->pathLength && b->scriptGoal){b->scriptGoal=0;b->pendingNotify=2;}
}
static void aim(const playerState_t *ps,codol_usercmd_t *cmd,const float *point,float dt,const bot_difficulty_t *profile)
{
    float delta[3],yaw,pitch,yawRate,pitchRate,yawFraction,pitchFraction;int i;
    for(i=0;i<3;++i)delta[i]=point[i]-ps->origin[i];delta[2]-=ps->viewHeightCurrent;
    yaw=atan2f(delta[1],delta[0])*180/PI;
    pitch=-atan2f(delta[2],sqrtf(delta[0]*delta[0]+delta[1]*delta[1]))*180/PI;
    /* The exact 1.1.1.13 difficulty table supplies separate hip/ADS yaw and
     * pitch tracking rates. Scale by executed time, not server frame count. */
    yawRate=ps->fWeaponPosFrac>0?profile->yawSpeedAds:profile->yawSpeed;
    pitchRate=ps->fWeaponPosFrac>0?profile->pitchSpeedAds:profile->pitchSpeed;
    yawFraction=fminf(1,yawRate*dt);pitchFraction=fminf(1,pitchRate*dt);
    yaw=ps->viewangles[1]+angle180(yaw-ps->viewangles[1])*yawFraction;
    pitch=ps->viewangles[0]+angle180(pitch-ps->viewangles[0])*pitchFraction;
    cmd->angles[0]=(unsigned short)ANGLE2SHORT(pitch-ps->delta_angles[0]);
    cmd->angles[1]=(unsigned short)ANGLE2SHORT(yaw-ps->delta_angles[1]);
}
/* T5 Path_UpdateLookahead: advance the steering point along the path as far
 * as a player-bounds trace stays clear, so corners are never cut through
 * geometry and a node passed slightly off-line still counts as reached. */
static int clear_to(const gentity_t *self,const float *point)
{
    trace_t tr;static const float mins[3]={-15,-15,18},maxs[3]={15,15,48};float end[3];
    memcpy(end,point,12);
    if(fabsf(end[2]-self->client->ps.origin[2])>40)return 0;
    end[2]=self->client->ps.origin[2];
    G_TraceCapsule(&tr,self->client->ps.origin,mins,maxs,end,self->s.number,0x2814011);
    return !tr.startsolid && tr.fraction>=1;
}
static void advance_path(bot_t *b,const gentity_t *self)
{
    const float *point;float dx,dy;int i,limit;
    while(b->pathIndex<b->pathLength){
        point=CODOL_BotNavPoint(b->path[b->pathIndex]);
        dx=point[0]-self->client->ps.origin[0];dy=point[1]-self->client->ps.origin[1];
        if(dx*dx+dy*dy>24*24 || fabsf(point[2]-self->client->ps.origin[2])>48)break;
        ++b->pathIndex;
    }
    /* Lookahead: skip at most two stand nodes when the straight line is clear. */
    limit=b->pathIndex+2;
    for(i=b->pathIndex+1;i<b->pathLength && i<=limit;++i){
        if(CODOL_BotNavStance(b->path[i])!=CODOL_BOT_STAND || CODOL_BotNavStance(b->path[i-1])!=CODOL_BOT_STAND)break;
        if(!clear_to(self,CODOL_BotNavPoint(b->path[i])))break;
        b->pathIndex=i;
    }
}
static int in_solid(const gentity_t *self)
{
    trace_t tr;static const float mins[3]={-15,-15,0},maxs[3]={15,15,60};
    G_TraceCapsule(&tr,self->client->ps.origin,mins,maxs,self->client->ps.origin,self->s.number,0x2814011);
    return tr.startsolid!=0;
}
/* C1 PM_CheckMantle (codol_pmove_c1_mantle.c:188) run as a bot probe along
 * the intended move yaw: a MANTLE-flagged surface within 35 units, the
 * facing within 60 degrees of its inward normal, and a 30x30x30 clear ledge
 * at +60/+40/+20 whose floor is walkable with 50 units of standing room.
 * Returns the yaw the pmove needs the view to face and the ledge rise. */
static int mantle_probe(const gentity_t *self,float yawDeg,float *faceYaw,float *rise)
{
    static const float heights[3]={60,40,20};
    static const float tmins[3]={-0.1f,-0.1f,0},tmaxs[3]={0.1f,0.1f,70},mins[3]={-15,-15,0};
    float maxs[3]={15,15,30};
    const float *org=self->client->ps.origin;
    float yaw=yawDeg*PI/180,fx=cosf(yaw),fy=sinf(yaw),start[3],end[3],dir[2],len,dot,ledge[3];trace_t tr;int i;
    start[0]=org[0]-fx*14.9f;start[1]=org[1]-fy*14.9f;start[2]=org[2];
    end[0]=org[0]+fx*34.9f;end[1]=org[1]+fy*34.9f;end[2]=org[2];
    G_TraceCapsule(&tr,start,tmins,tmaxs,end,self->s.number,0x1000000);
    if(tr.startsolid||tr.allsolid||tr.fraction>=1||!((unsigned)tr.sflags&0x6000000u))return 0;
    dir[0]=-tr.normal[0];dir[1]=-tr.normal[1];len=sqrtf(dir[0]*dir[0]+dir[1]*dir[1]);
    if(len<=0.0001f)return 0;dir[0]/=len;dir[1]/=len;
    dot=fx*dir[0]+fy*dir[1];if(dot<-1)dot=-1;if(dot>1)dot=1;
    if(acosf(dot)*180/PI>60)return 0;
    for(i=0;i<3;++i){
        start[0]=org[0];start[1]=org[1];start[2]=org[2]+heights[i];
        end[0]=start[0]+dir[0]*16;end[1]=start[1]+dir[1]*16;end[2]=start[2];
        G_TraceCapsule(&tr,start,mins,maxs,end,self->s.number,0x2814011);
        if(tr.startsolid||tr.fraction<1)continue;
        memcpy(start,end,12);end[2]=org[2]+18;
        G_TraceCapsule(&tr,start,mins,maxs,end,self->s.number,0x2814011);
        if(tr.startsolid||tr.fraction>=1||!tr.walkable)continue;
        ledge[0]=end[0];ledge[1]=end[1];ledge[2]=start[2]+tr.fraction*(end[2]-start[2]);
        maxs[2]=50;G_TraceCapsule(&tr,ledge,mins,maxs,ledge,self->s.number,0x2814011);maxs[2]=30;
        if(tr.startsolid)continue;
        *faceYaw=atan2f(dir[1],dir[0])*180/PI;*rise=ledge[2]-org[2];return 1;
    }
    return 0;
}
/* Forward blocked above step height (18): player box z 19..60 along the
 * move direction for 24 units. */
static int blocked_ahead(const gentity_t *self,float mx,float my)
{
    trace_t tr;static const float mins[3]={-15,-15,19},maxs[3]={15,15,60};float end[3];
    end[0]=self->client->ps.origin[0]+mx*24;end[1]=self->client->ps.origin[1]+my*24;end[2]=self->client->ps.origin[2];
    G_TraceCapsule(&tr,self->client->ps.origin,mins,maxs,end,self->s.number,0x2814011);
    return tr.startsolid||tr.fraction<1;
}
/* Start a mantle attempt: for 700 ms face the ledge, hold forward and JUMP.
 * C1 PM_CheckMantle is level-sensitive on JUMP (no press edge) and runs on
 * the ground and in the air, so the first frame jumps (PM_CheckJump edge)
 * if the ground probe misses and the held button lets the airborne probe
 * catch a higher ledge. */
static int try_mantle(bot_t *b,gentity_t *self,int now,float mx,float my)
{
    float face,rise;
    if(now<b->mantleNext || (self->client->ps.pm_flags&12) || (mx==0&&my==0))return 0;
    b->mantleNext=now+250;
    if(!blocked_ahead(self,mx,my) || !mantle_probe(self,atan2f(my,mx)*180/PI,&face,&rise))return 0;
    b->mantleUntil=now+700;b->mantleStart=now;b->mantleYaw=face;b->mantleRise=rise;b->mantleAttempts++;b->lastJump=now;
    b->mantleNext=now+2000;
    if(CODOL_TRACE_VERBOSE())
    Com_Printf(CON_CHANNEL_AI,"CoDOL bot: %d mantle attempt at (%.0f %.0f %.0f) height %.0f yaw %.0f pmf 0x%x mantle 0x%x\n",
        self->s.number,self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],rise,face,
        self->client->ps.pm_flags,self->client->ps.mantleState.flags);
    return 1;
}
static void mantle_drive(bot_t *b,gentity_t *self,codol_usercmd_t *cmd,int now)
{
    const playerState_t *ps=&self->client->ps;
    if(!b->mantleUntil)return;
    if(ps->pm_flags&4){
        b->mantleOk++;b->mantleUntil=0;b->mantleNext=now+800;
        if(CODOL_TRACE_VERBOSE())
        Com_Printf(CON_CHANNEL_AI,"CoDOL bot: %d mantle at (%.0f %.0f %.0f) height %.0f -> ok after %d ms pmf 0x%x mantle 0x%x\n",
            self->s.number,ps->origin[0],ps->origin[1],ps->origin[2],b->mantleRise,now-b->mantleStart,ps->pm_flags,ps->mantleState.flags);
        return;
    }
    if(now>=b->mantleUntil){
        b->mantleUntil=0;
        if(CODOL_TRACE_VERBOSE())
        Com_Printf(CON_CHANNEL_AI,"CoDOL bot: %d mantle at (%.0f %.0f %.0f) height %.0f -> fail pmf 0x%x mantle 0x%x\n",
            self->s.number,ps->origin[0],ps->origin[1],ps->origin[2],b->mantleRise,ps->pm_flags,ps->mantleState.flags);
        return;
    }
    cmd->angles[0]=(unsigned short)ANGLE2SHORT(0-ps->delta_angles[0]);
    cmd->angles[1]=(unsigned short)ANGLE2SHORT(b->mantleYaw-ps->delta_angles[1]);
    cmd->direction=1;cmd->buttons=(cmd->buttons&~(unsigned)(SPRINT|CROUCH|PRONE))|JUMP;
}
static void stuck_escalate(bot_t *b,gentity_t *self,int now,int departure,float mx,float my)
{
    const char *action;
    b->stuckCount++;
    /* Nudge, repath and regoal all failed without a single unit of movement:
     * the player is wedged (spawned in solid, or on unwalkable collision).
     * Script owns the consequence (bot_wedged -> respawn); no teleport here. */
    if(b->stuckLevel==2 && dist2(self->client->ps.origin,b->stuckPosition)<2*2){
        Com_Printf(CON_CHANNEL_AI,"CoDOL bot: wedged %d '%s' at %.0f %.0f %.0f pmf 0x%x solid %d; notifying bot_wedged\n",
            self->s.number,svs.clients[self->s.number].name,self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],
            self->client->ps.pm_flags,in_solid(self));
        b->pendingNotify=3;b->stuckLevel=0;b->pathLength=0;b->pathIndex=0;b->goalNode=-1;b->stuckSince=now;return;
    }
    if(b->stuckLevel==0){
        /* A mantle-height obstacle in the way is climbed before nudging. */
        b->mantleNext=0;
        if(try_mantle(b,self,now,mx,my))action="mantle";
        else {b->nudgeUntil=now+700;b->nudgeSide=random_range(b,0,1);action="nudge";}
    }
    else if(b->stuckLevel==1){
        if(b->pathIndex<b->pathLength)block_edge(b,departure,b->path[b->pathIndex],now);
        b->pathLength=0;b->pathIndex=0;b->pathNext=now;action="repath";
    } else {
        if(b->pathIndex<b->pathLength)block_edge(b,departure,b->path[b->pathIndex],now);
        if(b->scriptGoal){b->scriptGoal=0;b->pendingNotify=2;}
        b->pathLength=0;b->pathIndex=0;b->goalNode=-1;b->pathNext=now;b->nudgeUntil=now+500;b->nudgeSide=random_range(b,0,1);action="regoal";
    }
    if(CODOL_TRACE_VERBOSE())
    Com_Printf(CON_CHANNEL_AI,"CoDOL bot: stuck %d '%s' at %.0f %.0f %.0f level %d action %s goal %d path %d/%d (count %d)\n",
        self->s.number,svs.clients[self->s.number].name,self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],
        b->stuckLevel,action,b->goalNode,b->pathIndex,b->pathLength,b->stuckCount);
    if(b->stuckLevel<2)b->stuckLevel++; else b->stuckLevel=0;
    memcpy(b->stuckPosition,self->client->ps.origin,12);b->stuckLogged=now;
    b->stuckSince=now;memcpy(b->lastPosition,self->client->ps.origin,12);
}
static void crowd_check(bot_t *b,gentity_t *self,int now)
{
    int i,n=0;const gentity_t *ent;
    for(i=0;i<level.maxclients;++i){
        ent=&g_entities[i];
        if(ent==self||!ent->r.inuse||!ent->client||ent->health<=0||ent->client->sess.sessionState!=SESS_STATE_PLAYING)continue;
        if(dist2(ent->client->ps.origin,self->client->ps.origin)<40*40)++n;
    }
    if(n<2){b->crowdSince=0;return;}
    if(!b->crowdSince)b->crowdSince=now;
    if(now-b->crowdSince>2000 && now-b->crowdLogged>2000){
        b->crowdLogged=now;b->crowdCount++;
        if(CODOL_TRACE_VERBOSE())
        Com_Printf(CON_CHANNEL_AI,"CoDOL bot: crowd %d '%s' at %.0f %.0f %.0f others %d for %d ms goal %d enemy %d (count %d)\n",
            self->s.number,svs.clients[self->s.number].name,self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],
            n,now-b->crowdSince,b->goalNode,b->enemy,b->crowdCount);
    }
}
static void movement(bot_t *b,gentity_t *self,codol_usercmd_t *cmd,int now,const bot_difficulty_t *profile)
{
    const float *point;float dx,dy,yaw,forward,right,len,sep[2],mx=0,my=0;int stance,departure,climbing=0,hold=0;const codol_bot_annotation_t *annotation;
    if(b->scriptGoal && dist2(self->client->ps.origin,b->goal)<=b->radius*b->radius){b->pathLength=0;b->pendingNotify=1;return;}
    /* A seen enemy inside close distance is engaged from here: running onto
     * its node stacks every bot that saw it on one spot. */
    if(b->enemy>=0 && !b->scriptGoal && now-b->lastSeen<500 && dist2(self->client->ps.origin,b->lastKnown)<closeDistance->value*closeDistance->value)hold=1;
    if(!hold)route(b,self,now);
    advance_path(b,self);
    if(CODOL_TRACE_VERBOSE() && now-b->diagNext>=0){
        const float *v=self->client->ps.velocity;const float *g=b->pathIndex<b->pathLength?CODOL_BotNavPoint(b->path[b->pathIndex]):NULL;
        b->diagNext=now+2000;
        Com_Printf(CON_CHANNEL_AI,"CoDOL bot: %d '%s' org %.0f %.0f %.0f goal %d next %s%.0f %.0f %.0f path %d/%d speed %.0f vz %.0f pmf 0x%x ct %d solid %d enemy %d hold %d stuck %d crowd %d\n",
            self->s.number,svs.clients[self->s.number].name,self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],
            b->goalNode,g?"":"- ",g?g[0]:0.0f,g?g[1]:0.0f,g?g[2]:0.0f,b->pathIndex,b->pathLength,sqrtf(v[0]*v[0]+v[1]*v[1]),v[2],self->client->ps.pm_flags,self->client->ps.commandTime,in_solid(self),b->enemy,hold,b->stuckCount,b->crowdCount);
        if(b->mantleAttempts||b->ladderCount)Com_Printf(CON_CHANNEL_AI,"CoDOL bot: %d mantle %d/%d ladder %d\n",self->s.number,b->mantleOk,b->mantleAttempts,b->ladderCount);
    }
    crowd_check(b,self,now);
    if(hold || b->pathIndex>=b->pathLength){
        if(hold || !b->scriptGoal || !b->pathLength || dist2(b->goal,self->client->ps.origin)>256*256){
            /* Idle/holding: still keep out of other players. */
            if(separation(self,sep)){
                yaw=(SHORT2ANGLE(cmd->angles[1])+self->client->ps.delta_angles[1])*PI/180;
                forward=cosf(yaw)*sep[0]+sinf(yaw)*sep[1];right=sinf(yaw)*sep[0]-cosf(yaw)*sep[1];
                if(fabsf(forward)>0.3f)cmd->direction|=forward>0?1:2;
                if(fabsf(right)>0.3f)cmd->direction|=right>0?4:8;
            }
            if(hold || b->scriptGoal){b->stuckSince=now;memcpy(b->lastPosition,self->client->ps.origin,12);return;}
            /* Roaming with no route (nearest_reachable failed): fall through
             * to progress tracking so a wedged spawn is still escalated. */
            departure=-1;climbing=0;goto track;
        }
        point=b->goal;stance=CODOL_BOT_STAND;
    } else {point=CODOL_BotNavPoint(b->path[b->pathIndex]);stance=CODOL_BotNavStance(b->path[b->pathIndex]);}
    if(b->enemy<0){float target[3]={point[0],point[1],point[2]+self->client->ps.viewHeightCurrent};aim(&self->client->ps,cmd,target,(now-b->lastTime)*0.001f,profile);}
    /* C1 executes movement in this command's view frame. Project against the
     * final commanded yaw, not the previous playerState yaw before aiming. */
    dx=point[0]-self->client->ps.origin[0];dy=point[1]-self->client->ps.origin[1];
    yaw=(SHORT2ANGLE(cmd->angles[1])+self->client->ps.delta_angles[1])*PI/180;
    len=sqrtf(dx*dx+dy*dy);if(len<1)len=1;
    mx=dx/len;my=dy/len;
    if(separation(self,sep)){mx+=sep[0]*1.5f;my+=sep[1]*1.5f;}
    forward=cosf(yaw)*mx+sinf(yaw)*my;right=sinf(yaw)*mx-cosf(yaw)*my;
    if(fabsf(forward)>fabsf(right)*0.4f)cmd->direction|=forward>0?1:2;
    if(fabsf(right)>fabsf(forward)*0.4f)cmd->direction|=right>0?4:8;
    if(stance==CODOL_BOT_CROUCH)cmd->buttons|=CROUCH;
    else if(stance==CODOL_BOT_PRONE)cmd->buttons|=PRONE;
    /* A ladder edge uses the departure node's recorded look direction.
     * Killhouse lower/upper nodes deliberately carry opposite pitches. */
    departure=b->pathIndex>0?b->path[b->pathIndex-1]:-1;
    annotation=CODOL_BotNavAnnotation(departure);
    if(stance==CODOL_BOT_CLIMB && CODOL_BotNavStance(departure)==CODOL_BOT_CLIMB &&
       annotation && annotation->hasAngles && dx*dx+dy*dy<64*64){
        cmd->angles[0]=(unsigned short)ANGLE2SHORT(annotation->angles[0]-self->client->ps.delta_angles[0]);
        cmd->angles[1]=(unsigned short)ANGLE2SHORT(annotation->angles[1]-self->client->ps.delta_angles[1]);
        cmd->direction=1;climbing=1;
        /* Line up on the ladder line (departure node along its yaw) before
         * pushing in: C1 PM_CheckLadder needs the shrunk bounds (9 half
         * width) to hit the ladder face, and bots arrived 8-11 units off. */
        if(!(self->client->ps.pm_flags&8)){
            const float *d=CODOL_BotNavPoint(departure);float ly=annotation->angles[1]*PI/180;
            float side=(self->client->ps.origin[0]-d[0])*sinf(ly)-(self->client->ps.origin[1]-d[1])*cosf(ly);
            if(side>3)cmd->direction|=8; else if(side<-3)cmd->direction|=4;
        }
    }
    if(self->client->ps.pm_flags&8){
        if(!b->onLadder){b->onLadder=1;b->ladderCount++;
            if(CODOL_TRACE_VERBOSE())
            Com_Printf(CON_CHANNEL_AI,"CoDOL bot: %d ladder attach at (%.0f %.0f %.0f) next %.0f %.0f %.0f\n",self->s.number,
                self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],point[0],point[1],point[2]);}
    } else b->onLadder=0;
    /* Blocked by a mantle-height obstacle: climb it like a player would. */
    if(!climbing && stance==CODOL_BOT_STAND && now>=b->nudgeUntil && !b->mantleUntil && (b->enemy<0 || now-b->lastSeen>1000))try_mantle(b,self,now,mx,my);
    /* C1 ladder jump detaches. Only request mantle/jump on a low step edge,
     * with a released command between requests, never every ladder frame. */
    if(!climbing && !(self->client->ps.pm_flags&12) &&
       point[2]-self->client->ps.origin[2]>20 && point[2]-self->client->ps.origin[2]<=72 &&
       dx*dx+dy*dy<64*64 && now-b->lastJump>=500){cmd->buttons|=JUMP;b->lastJump=now;}
    if(b->enemy<0 && stance==CODOL_BOT_STAND && len>512 && fabsf(right)<forward*0.3f)cmd->buttons|=SPRINT;
    /* Stuck nudge: back off, strafe to the chosen side and hop once. */
    if(!climbing && now<b->nudgeUntil){
        cmd->direction=2|(b->nudgeSide?4:8);cmd->buttons&=~(unsigned)(SPRINT|CROUCH|PRONE);
        if(now-b->lastJump>=500 && !(self->client->ps.pm_flags&12) && b->nudgeUntil-now<350){cmd->buttons|=JUMP;b->lastJump=now;}
    }
    mantle_drive(b,self,cmd,now);
    /* Progress tracking: 12 units in 1.5 s (4 s on a ladder) or escalate. */
track:
    if(dist2(self->client->ps.origin,b->lastPosition)>12*12){memcpy(b->lastPosition,self->client->ps.origin,12);b->stuckSince=now;}
    else if(!(self->client->ps.pm_flags&4) && now>=b->nudgeUntil && !b->mantleUntil && now-b->stuckSince>(climbing?4000:1500))stuck_escalate(b,self,now,departure,mx,my);
    if(b->stuckLevel && dist2(self->client->ps.origin,b->stuckPosition)>96*96){
        if(CODOL_TRACE_VERBOSE())
        Com_Printf(CON_CHANNEL_AI,"CoDOL bot: recovered %d '%s' at %.0f %.0f %.0f after %d ms\n",self->s.number,svs.clients[self->s.number].name,
            self->client->ps.origin[0],self->client->ps.origin[1],self->client->ps.origin[2],now-b->stuckLogged);
        b->stuckLevel=0;
    }
}
/* Scripted button holds for test clients (codol_botPressButtons). Kept apart
 * from bot_t because enableCombatBot memsets that record, and a test client
 * that is not a combat bot still needs its presses to reach the engine. The
 * generation ties a hold to one entity lifetime. */
static struct { unsigned mask; int until; int generation; } scripted_press[MAX_CLIENTS];
static unsigned scripted_press_mask(int slot,const gentity_t *self,int now)
{
    if(slot<0||slot>=MAX_CLIENTS||!self)return 0;
    if(!scripted_press[slot].mask || now>=scripted_press[slot].until ||
       scripted_press[slot].generation!=self->useCount)return 0;
    return scripted_press[slot].mask;
}
int CODOL_BotBuildCommand(client_t *client,usercmd_t *native)
{
    int slot=(int)(client-svs.clients),now=svs.time,clip=0;bot_t *b;gentity_t *self;playerState_t *ps;codol_usercmd_t cmd;const struct WeaponDef *def;const bot_difficulty_t *profile;float dx,dy,pitch,yaw,error;int seen=0;
    unsigned pressed;
    if(slot<0||slot>=MAX_CLIENTS)return 0;b=&bots[slot];self=client->gentity;
    pressed=scripted_press_mask(slot,self,now);
    if(!b->enabled) {
        /* Not a combat bot: only a scripted hold drives it. */
        if(!pressed||!self->r.inuse||!self->client||client->netchan.remoteAddress.type!=NA_BOT)return 0;
        ps=&self->client->ps;
        if(!CODOL_DefaultWireUsercmd(ps,&cmd))memset(&cmd,0,sizeof(cmd));
        cmd.serverTime=now;cmd.buttons=pressed;cmd.direction=0;
        goto weapon_command;
    }
    if(!self||!self->r.inuse||!self->client||client->netchan.remoteAddress.type!=NA_BOT||self->useCount!=b->generation){memset(b,0,sizeof(*b));return 0;}
    profile=bot_difficulty();if(!profile)return 0;
    ps=&self->client->ps;
    if(now<b->lastTime){memset(b,0,sizeof(*b));return 0;}
    if(!CODOL_DefaultWireUsercmd(ps,&cmd))memset(&cmd,0,sizeof(cmd));
    cmd.serverTime=now;cmd.buttons=0;cmd.direction=0;
    if(self->health<=0||self->client->sess.archiveTime||self->client->sess.sessionState!=SESS_STATE_PLAYING){clear_enemy(b);b->pathLength=0;
        if(b->alive){b->deathTime=now;b->alive=0;}
        if(self->health<=0 && now-b->deathTime>=3000 && ((now/100)&1))cmd.buttons=USE;
        goto done;}
    /* C1 PMF_FROZEN (0x800): script froze the controls (game end, streak
     * use, spawn protection). No movement is possible, so it is not stuck. */
    if(ps->pm_flags&0x800){b->stuckSince=now;b->nudgeUntil=0;b->stuckLevel=0;memcpy(b->lastPosition,ps->origin,12);goto done;}
    if(!b->alive){b->alive=1;b->pathNext=0;b->stuckSince=now;b->stuckLevel=0;b->nudgeUntil=0;b->mantleUntil=0;b->onLadder=0;b->crowdSince=0;b->goalNode=-1;b->heldWeapon=0;memcpy(b->lastPosition,ps->origin,12);}
    if(now-b->lastTime>200)b->lastTime=now-50;
    /* Reuse only acquire's observation from this exact command and world.
     * Do not retain visibility across commands, route changes or script calls. */
    seen=acquire(b,self,now,profile);
    if(b->enemy>=0){
        if(seen)b->adsEnd=now+1000;
        if(!(ps->pm_flags&12) && now>=b->aimEnd)aim(ps,&cmd,b->lastKnown,(now-b->lastTime)*0.001f,profile);
        if(profile->adsAllowed && !(ps->pm_flags&12) && now<b->adsEnd && !CODOL_WeaponStateIsDualWielding(ps))cmd.buttons|=ADS|ADS_TRIGGER;
        dx=b->lastKnown[0]-ps->origin[0];dy=b->lastKnown[1]-ps->origin[1];
        yaw=atan2f(dy,dx)*180/PI;pitch=-atan2f(b->lastKnown[2]-ps->origin[2]-ps->viewHeightCurrent,sqrtf(dx*dx+dy*dy))*180/PI;
        error=fabsf(angle180(yaw-ps->viewangles[1]))+fabsf(angle180(pitch-ps->viewangles[0]));
        if(ps->weapon>0&&ps->weapon<BG_GetNumWeapons()){
            def=BG_GetWeaponDef(ps->weapon);CODOL_WeaponStateClipAmmo(ps,ps->weapon,0,&clip);
            if(!clip)cmd.buttons|=RELOAD;
            else if(!(ps->pm_flags&12)&&seen&&error<6&&now>=b->reactionEnd&&now>=b->fireNext&&!CODOL_WeaponStateIsReloading(ps)&&!CODOL_WeaponStateIsSwitching(ps)){
                cmd.buttons|=FIRE;
                if(CODOL_WeaponStateIsDualWielding(ps))cmd.buttons|=ADS_TRIGGER;
                /* T5 releases the trigger between nonautomatic shots; the
                 * real weapon machine still owns fire/rechamber timing. */
                if(def->fireType)b->fireNext=now+random_range(b,profile->minFireTime,profile->maxFireTime);
            }
        }
        /* C1 picks the lunge target on the client and ships meleeChargeDist /
         * meleeChargeYaw alongside the melee button. Mirror that so bots drive
         * the same server melee path a player does. */
        if(seen && !(ps->pm_flags&12) && now>=b->meleeNext && now>=b->reactionEnd){
            float flat=sqrtf(dx*dx+dy*dy);
            if(flat<110.0f && error<30.0f && !CODOL_WeaponStateIsReloading(ps) && !CODOL_WeaponStateIsSwitching(ps)){
                int lunge=(int)(flat-24.0f);
                if(lunge<0)lunge=0; if(lunge>255)lunge=255;
                cmd.buttons=(cmd.buttons&~(unsigned)(FIRE|ADS|ADS_TRIGGER))|MELEE;
                cmd.meleeChargeDist=(uint8_t)lunge;
                cmd.meleeChargeYaw=(uint16_t)(((int)(yaw*(65536.0f/360.0f)))&0xffff);
                b->meleeNext=now+1500;
            }
        }
    }
    movement(b,self,&cmd,now,profile);
    if(now<b->useEnd){cmd.buttons=USE;cmd.direction=0;}
done:
    /* A scripted hold adds to whatever the AI chose this command. */
    if(pressed)cmd.buttons|=pressed;
    b->lastTime=now;
    if(b->pendingNotify){
        int generation=self->useCount;unsigned notify=SL_GetString(b->pendingNotify==1?"goal":b->pendingNotify==3?"bot_wedged":"bad_path",0);
        b->pendingNotify=0;Scr_Notify(self,notify,0);SL_RemoveRefToString(notify);
        if(!self->r.inuse || self->useCount!=generation || client->gentity!=self)return 2;
    }
weapon_command:
    /* G_SelectWeaponIndex publishes script switch requests through the bot
     * controller. Bots have no client to consume reliable weapon commands.
     * Sending ps.weapon here fed back the old selection indefinitely. */
    {
        /* A real C1 client names its held weapon in EVERY usercmd, so any
         * server producer that re-reads the command's weapon (the mantle /
         * weapon-change arms of PM_Weapon do) sees the weapon the player is
         * actually holding. This builder left cmd.weapon at the zeroed value
         * whenever the bot controller had no pending script switch, i.e. the
         * bot asked for weapon 0 ("none") on every command; a mantle is one of
         * the events that makes that request take effect, which is why a bot
         * ran around empty-handed afterwards. Fall back to the held weapon. */
        unsigned requested=g_botai[slot].weapon;
        int wire;
        /* Bot_Connect seeds g_botai[].weapon with 1 and only G_SelectWeaponIndex
         * ever replaces it, so an untouched bot asked for a weapon it does not
         * own on every single command (the live trace printed a garbage index
         * there). Most frames ignore an unowned request, but the arms of
         * PM_Weapon that re-select from the command honour it. */
        if(!requested || requested>=(unsigned)BG_GetNumWeapons() ||
           !CODOL_WeaponBitsOwned(ps,requested))
            requested=(unsigned)ps->weapon;
        /* A mantle whose transition animation is 8 or 9 (s_mantleTrans[0..4],
         * _bg_mantle.asm:1503) makes Mantle_IsWeaponInactive true for its whole
         * duration, and the retained PM_Weapon then holsters the weapon with
         * PM_BeginWeaponChange(ps, 0) (_bg_weapons.asm:7208/7780 ->
         * PM_Weapon_1930). C1 recovers because the CLIENT keeps naming its held
         * weapon in every usercmd and PM_Weapon raises it again the moment the
         * mantle releases. A bot's command is built from ps->weapon, which is
         * now 0, so it stayed empty-handed -- the reported defect. Live proof
         * (build 3d790936): every mantle with transIndex 2/3/4 ended on
         * weapon 0 and every one with transIndex 5 kept its weapon. */
        if(requested) b->heldWeapon=requested;
        else if(b->heldWeapon && b->heldWeapon<(unsigned)BG_GetNumWeapons())
            /* No ownership test here on purpose: the retained selector already
             * refuses an unowned request (_bg_weapons.asm PM_Weapon_2300 tests
             * CODOL_WB_OWNED before PM_BeginWeaponChange), and the first live
             * attempt with an ownership guard here never fired. heldWeapon is
             * cleared on every respawn, so a fresh loadout is never overridden
             * and CODOL_ApplySpawnWeaponGate still owns the spawn window. */
            requested=b->heldWeapon;
        wire=requested<(unsigned)BG_GetNumWeapons()?CODOL_WeaponToWire(requested):-1;
        if(wire>=0) cmd.weapon=(uint16_t)wire;
        /* Mantle-window weapon plumbing: the live 2026-09-16 trace showed bots
         * entering a mantle holding a weapon and leaving it on weapon 0, with
         * no other weapon producer logging in between, so this prints exactly
         * what the command carried across that window. */
        {
            static int lines;
            if(CODOL_TRACE_VERBOSE() && lines<120 &&
               ((ps->pm_flags&4) || b->mantleUntil)) {
                ++lines;
                Com_Printf(CON_CHANNEL_AI,
                    "CoDOL bot mantle weapon: %d ct %d pmf 0x%x alive %d held %u "
                    "heldOwned %d requested %u wire %d cmd.weapon %u ps.weapon %d state %d\n",
                    slot,ps->commandTime,ps->pm_flags,b->alive,b->heldWeapon,
                    b->heldWeapon<(unsigned)BG_GetNumWeapons()?
                        CODOL_WeaponBitsOwned(ps,b->heldWeapon):-1,
                    requested,wire,(unsigned)cmd.weapon,ps->weapon,ps->weaponstate);
            }
        }
        CODOL_ToEngineUsercmd(&cmd,native,requested,ps->offHandIndex);
    }
    CODOL_StageBotCommandInput((unsigned)slot,&cmd);
    return 1;
}
static bot_t *receiver(scr_entref_t ref)
{
    gentity_t *ent;
    if(ref.classnum||ref.entnum>=MAX_CLIENTS){Scr_ObjectError("not a player");return NULL;}
    ent=&g_entities[ref.entnum];
    if(!ent->r.inuse||!ent->client||svs.clients[ref.entnum].netchan.remoteAddress.type!=NA_BOT){Scr_ObjectError("player is not a bot");return NULL;}
    return &bots[ref.entnum];
}
static void enable(scr_entref_t ref)
{
    bot_t *b=receiver(ref);int on;if(!b)return;
    if(Scr_GetNumParam()!=1){Scr_Error("enableCombatBot requires a boolean");return;}on=Scr_GetInt(0);
    memset(b,0,sizeof(*b));b->enabled=on!=0;b->generation=g_entities[ref.entnum].useCount;b->enemy=-1;b->goalNode=-1;b->random=ref.entnum+1;
}
static void set_goal(scr_entref_t ref)
{
    bot_t *b=receiver(ref);float point[3],radius;int i;if(!b)return;
    if(Scr_GetNumParam()!=2){Scr_Error("setScriptGoal requires position and radius");return;}
    Scr_GetVector(0,point);radius=Scr_GetFloat(1);
    for(i=0;i<3;++i)if(!isfinite(point[i])){Scr_ParamError(0,"goal must be finite");return;}
    if(!isfinite(radius)||radius<0){Scr_ParamError(1,"goal radius must be finite and nonnegative");return;}
    memcpy(b->goal,point,12);b->radius=radius;b->scriptGoal=1;b->pathNext=0;
}
static void clear_goal(scr_entref_t ref){bot_t *b=receiver(ref);if(b){b->scriptGoal=0;b->pathLength=0;b->pathNext=0;}}
static void has_goal(scr_entref_t ref){bot_t *b=receiver(ref);if(b)Scr_AddBool(b->scriptGoal);}
static void set_enemy(scr_entref_t ref)
{
    bot_t *b=receiver(ref);gentity_t *enemy;const bot_difficulty_t *profile;if(!b)return;enemy=Scr_GetEntity(0);
    if(!enemy||!enemy->client||!enemy->r.inuse){Scr_ParamError(0,"enemy must be a live player entity");return;}
    profile=bot_difficulty();if(!profile)return;
    b->enemy=enemy->s.number;b->enemyGeneration=enemy->useCount;b->scriptEnemy=1;b->acquired=b->lastSeen=svs.time;
    b->reactionEnd=svs.time+profile->reactionTime;
    b->aimEnd=svs.time+random_range(b,profile->minAimResponse,profile->maxAimResponse);
    eye(enemy,b->lastKnown);b->pathNext=0;
}
static void clear_script_enemy(scr_entref_t ref){bot_t *b=receiver(ref);if(b){b->scriptEnemy=0;clear_enemy(b);}}
static void press_use(scr_entref_t ref)
{
    bot_t *b=receiver(ref);float seconds;if(!b)return;seconds=Scr_GetFloat(0);
    if(!isfinite(seconds)||seconds<0||seconds>3600){Scr_ParamError(0,"use duration must be 0..3600 seconds");return;}b->useEnd=svs.time+(int)(seconds*1000);
}
/* <bot> codol_botPressButtons( <C1 usercmd button mask>, <seconds> ): hold the
 * given buttons in this bot's usercmds for the duration (0 releases). A test
 * facility: it drives the real weapon code the way a player's buttons do, so
 * an offhand throw (frag 0x4000, smoke 0x8000) produces the engine's own
 * grenade_fire. Works whether or not the bot is a combat bot. */
static void press_buttons(scr_entref_t ref)
{
    gentity_t *ent;float seconds;int mask;
    if(ref.classnum||ref.entnum>=MAX_CLIENTS){Scr_ObjectError("not a player");return;}
    ent=&g_entities[ref.entnum];
    if(!ent->r.inuse||!ent->client||svs.clients[ref.entnum].netchan.remoteAddress.type!=NA_BOT){Scr_ObjectError("player is not a bot");return;}
    if(Scr_GetNumParam()!=2){Scr_Error("usage: <bot> codol_botPressButtons( <mask>, <seconds> )");return;}
    mask=Scr_GetInt(0);seconds=Scr_GetFloat(1);
    if(!isfinite(seconds)||seconds<0||seconds>60){Scr_ParamError(1,"press duration must be 0..60 seconds");return;}
    scripted_press[ref.entnum].mask=(unsigned)mask;
    scripted_press[ref.entnum].until=svs.time+(int)(seconds*1000);
    scripted_press[ref.entnum].generation=ent->useCount;
}
/* <player> codol_deathGates(): prints the three inputs the retained player_die
 * (_g_combat_mp.asm:108) gates on before it will kill anyone - a server DObj
 * for the client, ps.pm_type normal (<=1) or last stand (7), and ps.otherFlags
 * bit 0x2 clear. A test facility for "health 0 but never died". */
void CODOL_ReportDeathGateRefusal(gentity_t *ent, int gate)
{
    const char *reason;
    const playerState_t *ps;
    if (!ent || !ent->client || ent->health > 0 || !com_developer || !com_developer->integer)
        return;
    ps = &ent->client->ps;
    switch (gate) {
    case 1: reason = "missing server DObj"; break;
    case 2: reason = "ineligible pm_type"; break;
    case 3: reason = "otherFlags bit 0x2"; break;
    default: reason = "unknown"; break;
    }
    Com_DPrintf(CON_CHANNEL_SERVER,
        "CoDOL player_die refused: client %d gate %s health %d pm_type %d otherFlags 0x%x\n",
        ent->s.number, reason, ent->health, ps->pm_type, (unsigned)ps->otherFlags);
}
static void death_gates(scr_entref_t ref)
{
    gentity_t *ent;playerState_t *ps;void *dobj;
    if(ref.classnum||ref.entnum>=MAX_CLIENTS){Scr_ObjectError("not a player");return;}
    ent=&g_entities[ref.entnum];
    if(!ent->r.inuse||!ent->client){Scr_ObjectError("not a player");return;}
    ps=&ent->client->ps;
    dobj=Com_GetServerDObj(ps->clientNum);
    Com_Printf(CON_CHANNEL_AI,"CoDOL death gates: client %d dobj %s pm_type %d otherFlags 0x%x health %d weapFlags 0x%x\n",
        ref.entnum,dobj?"yes":"NO",ps->pm_type,ps->otherFlags,ent->health,(unsigned)ps->weapFlags);
}
/* <player> codol_dumpOwnedAmmo(): every owned weapon with its ammo and clip
 * pool indices and what they hold. A test facility: G_InitializeAmmo skips a
 * weapon whose ammo pool another owned weapon already uses. */
static void dump_owned_ammo(scr_entref_t ref)
{
    gentity_t *ent;playerState_t *ps;int i,count;
    if(ref.classnum||ref.entnum>=MAX_CLIENTS){Scr_ObjectError("not a player");return;}
    ent=&g_entities[ref.entnum];
    if(!ent->r.inuse||!ent->client){Scr_ObjectError("not a player");return;}
    ps=&ent->client->ps;count=BG_GetNumWeapons();
    for(i=1;i<count;++i){
        const struct WeaponDef *def;
        if(!CODOL_WeaponBitsOwned(ps,(unsigned)i))continue;
        def=BG_GetWeaponDef(i);if(!def)continue;
        Com_Printf(CON_CHANNEL_PLAYERWEAP,"CoDOL owned ammo: client %d %s (%d) ammo %d=%d clip %d=%d start %d\n",
            ref.entnum,def->szInternalName?def->szInternalName:"?",i,
            def->iAmmoIndex,def->iAmmoIndex>=0&&def->iAmmoIndex<128?ps->ammo[def->iAmmoIndex]:-1,
            def->iClipIndex,def->iClipIndex>=0&&def->iClipIndex<128?ps->ammoclip[def->iClipIndex]:-1,def->iStartAmmo);
    }
}
static void load_graph(void)
{
    int count;const char *path=Scr_GetString(0);count=CODOL_BotNavLoad(path);
    CODOL_ResetBotLoadout();
    memset(bots,0,sizeof(bots));
    if(!count)Com_PrintWarning(CON_CHANNEL_AI,"CoDOL bot: missing or invalid waypoint graph %s; no bots on this map\n",path);
    else Com_Printf(CON_CHANNEL_AI,"CoDOL bot: waypoint graph %s loaded, %d nodes\n",path,count);
    Scr_AddInt(count);
}
/* Bot/human discriminator for callers outside the server area (the C1 pmove
 * traces have to tell a 12-bot lobby apart from the one connected player).
 * Native bot producers set NA_BOT on the netchan, as codol_script_skill.c
 * and codol_sv_weapons.c already do. */
int CODOL_ClientIsBotClient(unsigned client)
{
    if(client>=(unsigned)MAX_CLIENTS) return 0;
    return svs.clients[client].netchan.remoteAddress.type==NA_BOT;
}

void CODOL_RegisterBotMethods(void)
{
    botDifficultiesReady=0;botDifficultyRetryTime=0;
    fov=Cvar_RegisterFloat("sv_botFov",65,1,160,0,"Bot sight field of view");
    closeDistance=Cvar_RegisterFloat("sv_botCloseDistance",256,0,4096,0,"Bot close threat retention distance");
    difficulty=Cvar_RegisterEnum("sv_botDifficulty",botDifficultyNames,1,0,
        "Training bot difficulty: recruit, regular, hardened, or veteran (exact 1.1.1.13 table)");
    CODOL_RegisterBotLoadoutMethods();
    Scr_AddFunction("loadbotwaypoints",load_graph,0);
    Scr_AddMethod("enablecombatbot",enable,0);
    Scr_AddMethod("setscriptgoal",set_goal,0);Scr_AddMethod("clearscriptgoal",clear_goal,0);Scr_AddMethod("hasscriptgoal",has_goal,0);
    Scr_AddMethod("setscriptenemy",set_enemy,0);Scr_AddMethod("clearscriptenemy",clear_script_enemy,0);Scr_AddMethod("pressusebutton",press_use,0);
    Scr_AddMethod("codol_botpressbuttons",press_buttons,0);
    Scr_AddMethod("codol_deathgates",death_gates,0);
    Scr_AddMethod("codol_dumpownedammo",dump_owned_ammo,0);
}
#endif
