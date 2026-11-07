/* T5 NORMAL attached RC sphere: _spawning.gsc840 and native
 * SpawnSystem_ComputeSphereInfluence1426 / InfluenceWeight1385.
 * Native moving entity owns the influence; no polling script surrogate.
 * The same attached sphere carries T5's dog influencer
 * (_spawning.gsc create_dog_influencers: radius 15 player heights, score
 * -150, steep, the dog's enemies only): the receiver may also be a live
 * actor, and the sphere ends when that actor dies (its entity becomes a
 * corpse) or is freed, as T5 removes it with the dog. */
#ifdef CODOL_SERVER
#include "codol_rc_spawn_influence.h"
#include "g_shared.h"
#include <math.h>
#include <string.h>
typedef struct { int active,generation,protected_team,curve,eType; float radius,score; } influence_t;
static influence_t influences[ENTITYNUM_MAX_NORMAL];
static unsigned active_count;
static int team(unsigned arg,int allow_spectator)
{
 const char *name=Scr_GetString(arg);
 if(!strcmp(name,"axis"))return 1;
 if(!strcmp(name,"allies"))return 2;
 if(!strcmp(name,"none") || !strcmp(name,"free"))return 0;
 if(allow_spectator && !strcmp(name,"spectator"))return 3;
 Scr_ParamError(arg,"RC spawn influencer team must be axis, allies or none");
 return -1;
}
void CODOL_Scr_SetRCSpawnInfluencer(scr_entref_t ref)
{
 influence_t next; gentity_t *e;
 if(ref.classnum || ref.entnum>=ENTITYNUM_MAX_NORMAL ||
    !(e=&g_entities[ref.entnum])->r.inuse || (e->s.eType!=ET_VEHICLE && e->s.eType!=ET_ACTOR)) {
  Scr_ObjectError("codol_setRCSpawnInfluencer requires a live vehicle or actor");return;
 }
 if(Scr_GetNumParam()!=4) {Scr_Error("codol_setRCSpawnInfluencer(radius,score,curve,protectedTeam)");return;}
 memset(&next,0,sizeof(next)); next.radius=Scr_GetFloat(0);next.score=Scr_GetFloat(1);
 next.curve=Scr_GetInt(2);next.protected_team=team(3,0);
 if(next.protected_team<0)return;
 if(!isfinite(next.radius) || next.radius<=0 || !isfinite(next.radius*next.radius)) {
  Scr_ParamError(0,"RC influence radius must be positive and finite");return;
 }
 if(!isfinite(next.score)) {Scr_ParamError(1,"RC influence score must be finite");return;}
 if((unsigned)next.curve>4) {Scr_ParamError(2,"RC influence curve must be0..4");return;}
 next.generation=e->useCount;next.eType=e->s.eType;next.active=1;
 if(!influences[ref.entnum].active)++active_count;
 influences[ref.entnum]=next;
}
void CODOL_Scr_RCSpawnWeight(void)
{
 float p[3],total=0;int viewer;unsigned i,remaining;
 if(Scr_GetNumParam()!=2) {Scr_Error("codol_rcSpawnWeight(position,team)");return;}
 Scr_GetVector(0,p);viewer=team(1,1);if(viewer<0)return;
 if(!isfinite(p[0]) || !isfinite(p[1]) || !isfinite(p[2])) {Scr_ParamError(0,"spawn position must be finite");return;}
 /* The shared spawn selector also places connecting spectators. They have
  * no combat team and must not be weighted as FFA targets of an RC. */
 if(viewer==3) {Scr_AddFloat(0);return;}
 remaining=active_count;
 for(i=0;remaining && i<ENTITYNUM_MAX_NORMAL;++i) {
  influence_t *f=&influences[i];gentity_t *e=&g_entities[i];float x,y,z,d,r,w;
  if(!f->active)continue;
  --remaining;
  if(!e->r.inuse || e->useCount!=f->generation || e->s.eType!=f->eType ||
     (f->eType==ET_ACTOR && e->health<=0)) {f->active=0;--active_count;continue;}
  if(f->protected_team && f->protected_team==viewer)continue;
  x=p[0]-e->r.currentOrigin[0];y=p[1]-e->r.currentOrigin[1];z=p[2]-e->r.currentOrigin[2];
  d=x*x+y*y+z*z;if(d>=f->radius*f->radius)continue;
  r=sqrtf(d/(f->radius*f->radius));
  switch(f->curve) {
   case 1:w=1-r;break;case 2:w=(1-r)*(1-r);break;
   case 3:w=r;break;case 4:w=2*r-1;break;default:w=1;break;
  }
  total+=w*f->score;
 }
 if(!isfinite(total)) {Scr_Error("RC spawn influence overflow");return;}
 Scr_AddFloat(total);
}
void CODOL_ResetRCSpawnInfluencer(unsigned n)
{ if(n<ENTITYNUM_MAX_NORMAL) {if(influences[n].active)--active_count;memset(&influences[n],0,sizeof(influences[n]));} }
void CODOL_ResetRCSpawnInfluencers(void)
{ memset(influences,0,sizeof(influences));active_count=0; }
#endif
