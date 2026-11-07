/* T5 Actor_Dog_GetEnemyPos, Actor_SetMeleeAttackSpot and
 * Actor_Dog_IsEnemyInAttackRange, adapted to native server entity handles.
 * Reference: OpenBLOPS Game/Server/game/actor_dog_exposed.cpp:323-644.
 * No T5/C1 structure offsets or animation indices are shared here.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
#include "codol_dog_combat.h"
#include "server.h"
#include "g_shared.h"
#include <math.h>
#include <string.h>

typedef struct { int entity, generation; } dog_claim_t;
typedef struct { int targetGeneration; dog_claim_t slot[4]; } dog_target_t;
static dog_target_t targets[MAX_GENTITIES];
static const float offsets[4][2]={{1,0},{0,1},{-1,0},{0,-1}};
static const float attackMins[3]={-15,-15,18};
static const float attackMaxs[3]={15,15,48};
static const float actorMaxs[3]={15,15,48};

static float distance2(const float *a,const float *b)
{ float x=a[0]-b[0],y=a[1]-b[1]; return x*x+y*y; }
static void direction(const float *a,const float *b,float *v)
{
    float length;
    v[0]=a[0]-b[0];v[1]=a[1]-b[1];
    length=sqrtf(v[0]*v[0]+v[1]*v[1]);
    if(length>0){v[0]/=length;v[1]/=length;}
}
static int valid_entity(const gentity_t *ent)
{ return ent && ent>=g_entities && ent<g_entities+MAX_GENTITIES && ent->r.inuse; }
static gentity_t *claimant(dog_claim_t *claim)
{
    gentity_t *ent;
    if(claim->entity<=0 || claim->entity>=MAX_GENTITIES)return NULL;
    ent=&g_entities[claim->entity];
    if(!ent->r.inuse || ent->useCount!=claim->generation || ent->health<=0){
        memset(claim,0,sizeof(*claim));return NULL;
    }
    return ent;
}
void CODOL_DogCombatReset(void){memset(targets,0,sizeof(targets));}
void CODOL_DogCombatRelease(gentity_t *dog)
{
    int target,slot;
    if(!dog)return;
    for(target=0;target<MAX_GENTITIES;++target)
        for(slot=0;slot<4;++slot)
            if(targets[target].slot[slot].entity==dog->s.number &&
               targets[target].slot[slot].generation==dog->useCount)
                memset(&targets[target].slot[slot],0,sizeof(dog_claim_t));
}
static int attack_spot(gentity_t *dog,gentity_t *enemy,const float *enemyPos,
                       float radius,float *position)
{
    dog_target_t *target=&targets[enemy->s.number];
    float dots[4],dir[2],best[3],drop[3],bestFraction=0;
    int indices[4]={0,1,2,3},i,j,index;trace_t tr;
    gentity_t *occupier;
    if(target->targetGeneration!=enemy->useCount){
        memset(target,0,sizeof(*target));target->targetGeneration=enemy->useCount;
    }
    direction(dog->r.currentOrigin,enemyPos,dir);
    for(i=0;i<4;++i){
        dots[i]=dir[0]*offsets[i][0]+dir[1]*offsets[i][1];
        if(target->slot[i].entity==dog->s.number)
            memset(&target->slot[i],0,sizeof(dog_claim_t));
    }
    for(i=1;i<4;++i){
        index=indices[i];
        for(j=i-1;j>=0 && dots[indices[j]]<=dots[index];--j)indices[j+1]=indices[j];
        indices[j+1]=index;
    }
    for(i=0;i<4;++i){
        index=indices[i];
        position[0]=enemyPos[0]+radius*offsets[index][0];
        position[1]=enemyPos[1]+radius*offsets[index][1];position[2]=enemyPos[2];
        occupier=claimant(&target->slot[index]);
        if(occupier && distance2(dog->r.currentOrigin,position)>=distance2(occupier->r.currentOrigin,position))continue;
        G_TraceCapsule(&tr,position,attackMins,attackMaxs,position,enemy->s.number,0x20000);
        if(!tr.startsolid && !tr.allsolid)
            G_TraceCapsule(&tr,position,attackMins,attackMaxs,enemyPos,enemy->s.number,0x2800011);
        if(tr.fraction<1 || tr.startsolid || tr.allsolid){
            if(!tr.startsolid && !tr.allsolid && tr.fraction>bestFraction){bestFraction=tr.fraction;memcpy(best,position,12);}
            continue;
        }
        memcpy(drop,position,12);drop[2]-=90;
        G_TraceCapsule(&tr,position,attackMins,actorMaxs,drop,enemy->s.number,0x2800011);
        if(tr.fraction<1 && !tr.startsolid && !tr.allsolid){
            position[2]-=90*tr.fraction;position[2]+=1;
            target->slot[index].entity=dog->s.number;
            target->slot[index].generation=dog->useCount;return 1;
        }
    }
    if(bestFraction<=0.95f)return 0;
    memcpy(position,best,12);return 1;
}
void CODOL_DogCombatGoal(gentity_t *dog,gentity_t *enemy,float attackDistance,
                        int enemyInSyncedMelee,codol_dog_attack_goal_t *out)
{
    float buffer,height,a[2],b[2];int i;trace_t tr;
    if(!out)return;
    memset(out,0,sizeof(*out));
    if(!valid_entity(dog) || !valid_entity(enemy) || dog==enemy ||
       dog->health<=0 || enemy->health<=0 || !isfinite(attackDistance) || attackDistance<=0)return;
    memcpy(out->enemyPosition,enemy->r.currentOrigin,12);buffer=attackDistance+15;
    if(enemy->client){
        const float *velocity=enemy->client->ps.velocity;
        if(velocity[0]*velocity[0]+velocity[1]*velocity[1]>1){
            for(i=0;i<3;++i)out->enemyPosition[i]+=0.25f*velocity[i];
            buffer+=15;
        }
        if(enemyInSyncedMelee)out->enemyPosition[2]+=64;
    }
    height=dog->r.currentOrigin[2]-out->enemyPosition[2];
    out->inAttackRange=height*height<=80*80 && distance2(dog->r.currentOrigin,out->enemyPosition)<=buffer*buffer;
    out->goalSet=attack_spot(dog,enemy,out->enemyPosition,attackDistance,out->goal);
    if(out->goalSet && out->inAttackRange){
        direction(out->goal,out->enemyPosition,a);direction(dog->r.currentOrigin,out->enemyPosition,b);
        out->inAttackRange=a[0]*b[0]+a[1]*b[1]>0.707f;
    }else if(out->inAttackRange){
        G_TraceCapsule(&tr,dog->r.currentOrigin,attackMins,actorMaxs,out->enemyPosition,enemy->s.number,0x2820011);
        out->inAttackRange=(tr.hitType==TRACE_HITTYPE_ENTITY && tr.hitId==enemy->s.number) ||
            (tr.fraction>=1 && !tr.startsolid && !tr.allsolid);
    }
}
#endif
