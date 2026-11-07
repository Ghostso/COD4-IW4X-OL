/* Same-missile native retrieval/link lifecycle. T5 bone/corpse reference;
 * wall incidence is an explicit sh1x policy, not recovered C1 authority. */
#ifdef CODOL_SERVER
#include "codol_knife_attachment.h"
#include "codol_knife_pickup.h"
#include "g_shared.h"
#include "bg_public.h"
#include "cm_public.h"
#include "cscr_stringlist.h"
#include "q_math.h"
#include "server.h"
#include "dobj.h"
#include "codol_sentient.h"
#include "game/surfaceflags.h"
#include <math.h>
#include <string.h>

extern int G_EntLinkTo(gentity_t *,gentity_t *,unsigned);
extern int CODOL_NotifyMissileStationary(gentity_t *);
extern void G_Damage(gentity_t *,gentity_t *,gentity_t *,const float *,const float *,
 int,int,int,unsigned,int,unsigned,unsigned,int);

typedef struct { unsigned number; int generation; } knife_ref_t;
typedef struct {
 int active,generation,player_generation,death_seen;
 unsigned corpse_serial;
 unsigned player,tag;
 knife_ref_t target;
} knife_attachment_t;
static knife_attachment_t attachments[ENTITYNUM_WORLD];
static knife_ref_t corpses[MAX_CLIENTS];
static int corpse_player_generation[MAX_CLIENTS];
static unsigned corpse_serial[MAX_CLIENTS];

static gentity_t *resolve(knife_ref_t ref)
{
 gentity_t *e;
 if(!ref.number || ref.number>ENTITYNUM_WORLD)return NULL;
 e=&g_entities[ref.number-1];
 return e->r.inuse && e->useCount==ref.generation ? e : NULL;
}
static knife_ref_t reference(gentity_t *e)
{
 knife_ref_t r={0,0};
 if(e && e->r.inuse && (unsigned)e->s.number<ENTITYNUM_WORLD) {
  r.number=e->s.number+1; r.generation=e->useCount;
 }
 return r;
}
static int knife(gentity_t *e)
{
 unsigned w;
 if(!e || !e->r.inuse || e->s.eType!=ET_MISSILE)return 0;
 w=e->s.weapon;
 return w && w<(unsigned)BG_GetNumWeapons() &&
  CODOL_IsKnifeDefinition(BG_GetWeaponDef(w));
}
static unsigned bone(unsigned location)
{
 /* Named T5 MapHitLocationToRagdollBoneName cases; actual receiver's DObj
  * must resolve the tag. No cross-engine bone-index equivalence. */
 static const char *names[HITLOC_NUM]={NULL,"j_head","j_head","j_neck",
  "j_spineupper","j_spinelower","j_elbow_ri","j_elbow_le","j_wrist_ri",
  "j_wrist_le","j_wrist_ri","j_wrist_le","j_knee_ri","j_knee_le",
  "j_ankle_ri","j_ankle_le","j_ankle_ri","j_ankle_le",NULL};
 return location<HITLOC_NUM && names[location] ? SL_FindString(names[location]) : 0;
}
static int link_target(gentity_t *e,gentity_t *target,unsigned tag)
{
 float matrix[4][3];
 if(tag && !G_DObjGetWorldTagMatrix(target,tag,matrix))tag=0;
 /* No tag means exact impact pose relative to target origin. G_EntLinkTo
  * computes local offsets from current world pose; it does not snap to bone. */
 return G_EntLinkTo(e,target,tag);
}
static void detach(gentity_t *e,knife_attachment_t *a)
{
 if(e->tagInfo)G_EntUnlink(e);
 a->target.number=0; a->target.generation=0; a->player=0;
 e->s.groundEntityNum=ENTITYNUM_WORLD;
 G_SetOrigin(e,e->r.currentOrigin); G_SetAngle(e,e->r.currentAngles);
}
static int settle(gentity_t *e,gentity_t *target,const trace_t *tr,const float *velocity)
{
 knife_attachment_t *a; vec3_t angles; unsigned tag=0;
 if((unsigned)e->s.number>=ENTITYNUM_WORLD)return 0;
 if(!isfinite(velocity[0]) || !isfinite(velocity[1]) || !isfinite(velocity[2]))return 0;
 if(velocity[0]*velocity[0]+velocity[1]*velocity[1]+velocity[2]*velocity[2]<=0)return 0;
 vectoangles(velocity,angles);
 G_SetOrigin(e,e->r.currentOrigin); G_SetAngle(e,angles);
 /* Native stationary0, not retained IW3 physics8. Keep the existing model,
  * weapon/variant identity and owner. A settled knife must enter the player
  * touch query (G_TouchTriggers mask 0x405c0008) as well as the manual-use
  * query (0x200000); the flying missile is never auto-pickup eligible. */
 e->s.lerp.pos.trType=TR_STATIONARY; e->s.lerp.apos.trType=TR_STATIONARY;
 memset(e->s.lerp.pos.trDelta,0,sizeof(vec3_t));
 memset(e->s.lerp.apos.trDelta,0,sizeof(vec3_t));
 e->nextthink=0; /* Knife recovery owns lifetime after impact, no explosion. */
 e->s.groundEntityNum=ENTITYNUM_WORLD;
 e->r.contents |= CONTENTS_TRIGGER;
 a=&attachments[e->s.number]; memset(a,0,sizeof(*a));
 a->active=1; a->generation=e->useCount;
 if(target && target->r.inuse) {
  tag=bone(tr->partGroup);
  if(!tag)tag=tr->partName;
  if(link_target(e,target,tag)) {
   a->target=reference(target); a->tag=tag;
   e->s.groundEntityNum=target->s.number;
   if(target->client && (unsigned)target->s.number<MAX_CLIENTS) {
    a->player=target->s.number+1; a->player_generation=target->useCount;
    a->corpse_serial=corpse_serial[target->s.number];
    a->death_seen=target->health<=0;
   }
  }
 }
 SV_LinkEntity(e);
 CODOL_NotifyMissileStationary(e); /* No entity access after script callbacks. */
 return 1;
}
int CODOL_KnifeWorldImpact(gentity_t *e,trace_t *tr,const float *velocity)
{
 unsigned hit; gentity_t *target=NULL; float speed,dot;
 if(!knife(e) || !tr || !velocity)return 0;
 hit=(unsigned)(unsigned short)Trace_GetEntityHitId(tr);
 if(hit<ENTITYNUM_WORLD && g_entities[hit].r.inuse)target=&g_entities[hit];
 if(target && target->takedamage)return 0; /* Real G_Damage runs first. */
 if(target && target->client && target->health<=0 && (unsigned)target->s.number<MAX_CLIENTS &&
    corpse_player_generation[target->s.number]==target->useCount) {
  gentity_t *corpse=resolve(corpses[target->s.number]);
  if(corpse)target=corpse;
 }
 if(target && (target->client || target->s.eType==ET_PLAYER_CORPSE || CODOL_Sentient_ForEntity(target)))
  return settle(e,target,tr,velocity);
 speed=sqrtf(DotProduct(velocity,velocity));
 if(!isfinite(speed) || speed<=0)return 0;
 dot=-DotProduct(velocity,tr->normal)/speed;
 /* User-requested wall embedding: a tip-first impact within ~45 degrees.
  * C1 predictor uses the corresponding reflected-direction dot > .7, but
  * authoritative use here is a declared sh1x policy. Glancing hits bounce. */
 if(!isfinite(dot) || dot<=0.7f)return 0;
 return settle(e,target,tr,velocity);
}
int CODOL_KnifeDamageImpact(gentity_t *target,gentity_t *missile,gentity_t *attacker,
 const float *direction,const float *point,int damage,int flags,int mod,unsigned weapon,
 int hitloc,unsigned model,unsigned part,int offset,trace_t *trace)
{
 int isknife=knife(missile); knife_ref_t projectile=reference(missile),victim=reference(target);
 unsigned prior_corpse=target && target->client && (unsigned)target->s.number<MAX_CLIENTS ? corpse_serial[target->s.number] : 0;
 vec3_t velocity; trace_t saved;
 if(isknife) { VectorCopy(direction,velocity); saved=*trace; }
 G_Damage(target,missile,attacker,direction,point,damage,flags,mod,weapon,hitloc,model,part,offset);
 if(!isknife)return 0;
 missile=resolve(projectile);
 if(!missile || !knife(missile))return 1; /* Callback destroyed/retyped it. */
 target=resolve(victim);
 if(target && target->client && target->health<=0 && (unsigned)target->s.number<MAX_CLIENTS &&
    corpse_player_generation[target->s.number]==target->useCount &&
    corpse_serial[target->s.number]!=prior_corpse) {
  gentity_t *corpse=resolve(corpses[target->s.number]);
  if(corpse)target=corpse;
 }
 return settle(missile,target,&saved,velocity);
}
int CODOL_RunAttachedKnife(gentity_t *e)
{
 knife_attachment_t *a; gentity_t *target;
 if(!e || (unsigned)e->s.number>=ENTITYNUM_WORLD)return 0;
 a=&attachments[e->s.number];
 if(!a->active || a->generation!=e->useCount)return 0;
 if(!knife(e)) { memset(a,0,sizeof(*a)); return 0; }
 target=resolve(a->target);
 if(a->player) {
  unsigned p=a->player-1; gentity_t *corpse=NULL;
  if(p<MAX_CLIENTS && corpse_player_generation[p]==a->player_generation &&
     corpse_serial[p]!=a->corpse_serial)
   corpse=resolve(corpses[p]);
  if(corpse && corpse!=target) {
   if(e->tagInfo)G_EntUnlink(e);
   if(link_target(e,corpse,a->tag)) { a->target=reference(corpse); target=corpse; a->player=0; e->s.groundEntityNum=corpse->s.number; }
   else detach(e,a);
  } else if(target && target->client && target->health<=0) {
   /* Await same-death clone while preserving last linked world pose. */
   a->death_seen=1;
  } else if(target && target->client && a->death_seen) {
   detach(e,a);
  }
 }
 if(a->target.number && (!target || !e->tagInfo))detach(e,a);
 if(e->tagInfo)G_GeneralLink(e);
 SV_LinkEntity(e);
 return 1;
}
void CODOL_KnifeCorpseCreated(unsigned corpse,unsigned player)
{
 if(player>=MAX_CLIENTS || corpse>=ENTITYNUM_WORLD)return;
 corpses[player]=reference(&g_entities[corpse]);
 corpse_player_generation[player]=g_entities[player].useCount;
 ++corpse_serial[player];
}
void CODOL_KnifePlayerSpawning(gentity_t *player)
{
 unsigned i,p;
 if(!player || (p=(unsigned)player->s.number)>=MAX_CLIENTS)return;
 for(i=0;i<ENTITYNUM_WORLD;++i) {
  knife_attachment_t *a=&attachments[i]; gentity_t *e,*corpse=NULL;
  if(!a->active || a->player!=p+1 || a->player_generation!=player->useCount)continue;
  e=&g_entities[i];
  if(!e->r.inuse || e->useCount!=a->generation)continue;
  if(corpse_player_generation[p]==a->player_generation && corpse_serial[p]!=a->corpse_serial)
   corpse=resolve(corpses[p]);
  if(corpse && corpse->s.eType==ET_PLAYER_CORPSE) {
   if(e->tagInfo)G_EntUnlink(e);
   if(link_target(e,corpse,a->tag)) {
    a->target=reference(corpse); a->player=0; e->s.groundEntityNum=corpse->s.number; continue;
   }
  }
  detach(e,a); /* Before spawn writes origin: never teleport with new life. */
 }
 memset(&corpses[p],0,sizeof(corpses[p]));
}
void CODOL_ResetKnifeAttachment(unsigned n)
{
 unsigned i;
 if(n>=ENTITYNUM_WORLD)return;
 memset(&attachments[n],0,sizeof(attachments[n]));
 if(n<MAX_CLIENTS) { memset(&corpses[n],0,sizeof(corpses[n])); corpse_player_generation[n]=0; }
 for(i=0;i<MAX_CLIENTS;++i)if(corpses[i].number==n+1)memset(&corpses[i],0,sizeof(corpses[i]));
 /* Native G_FreeEntity tears down tag children. Their next update detaches
  * against the saved generation; a reused target can never inherit a knife. */
}
void CODOL_ResetKnifeAttachments(void)
{
 memset(attachments,0,sizeof(attachments)); memset(corpses,0,sizeof(corpses));
 memset(corpse_player_generation,0,sizeof(corpse_player_generation));
 memset(corpse_serial,0,sizeof(corpse_serial));
}
#endif
