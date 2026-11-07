/* C1 mortar bomb producer: original weapon type4 / guidance4.
 * C1 LaunchBomb55bf20 -> DropBomb531460. Real ET_MISSILE, native collision,
 * G_ExplodeMissile radius damage and captured C1 weapon FX/sound selector. */
#ifdef CODOL_SERVER
#include "codol_bomb.h"
#include "codol_weapon_native.h"
#include "codol_script_combat_builtins.h"
#include "g_shared.h"
#include "server.h"
#include "bg.h"
#include "q_math.h"
#include "cscr_stringlist.h"
#include <math.h>
#include <limits.h>
#include <string.h>
extern void G_ExplodeMissile(gentity_t *);
extern void BG_EvaluateTrajectoryDelta(const trajectory_t *, int, float *);

void CODOL_Scr_GetProjectileGravity(void)
{
    trajectory_t trajectory;
    vec3_t velocity;
    float gravity;
    if(Scr_GetNumParam()) {
        Scr_Error("codol_getProjectileGravity()"); return;
    }
    /* Use the same authoritative TR_GRAVITY evaluator as mortar flight.
     * The velocity change after one second is its acceleration, independent
     * of player gravity and of absent/renamed script dvars. */
    memset(&trajectory,0,sizeof(trajectory));
    trajectory.trType=TR_GRAVITY;
    BG_EvaluateTrajectoryDelta(&trajectory,1000,velocity);
    gravity=-velocity[2];
    if(!isfinite(gravity) || gravity<=0.0f) {
        Scr_Error("native projectile gravity is not positive and finite"); return;
    }
    Scr_AddFloat(gravity);
}

/* Server-only constructor provenance: do not reinterpret already deployed
 * type4 weapons created by retained firing code. Entity/map resets clear it. */
typedef struct {
    int constructed, generation, owner_generation, pending_contact;
    unsigned weapon, owner;
    vec3_t contact;
} bomb_state_t;
static bomb_state_t bomb_states[MAX_GENTITIES];
void CODOL_ResetBombState(unsigned entity)
{
    if(entity<MAX_GENTITIES)memset(&bomb_states[entity],0,sizeof(bomb_states[entity]));
}
void CODOL_ResetBombStates(void)
{
    memset(bomb_states,0,sizeof(bomb_states));
}
static bomb_state_t *bomb_state(gentity_t *ent)
{
    bomb_state_t *state;
    if(!ent || (unsigned)ent->s.number>=MAX_GENTITIES ||
       ent!=&g_entities[ent->s.number] || !ent->r.inuse)return NULL;
    state=&bomb_states[ent->s.number];
    return state->constructed && state->generation==ent->useCount &&
        state->weapon==(unsigned)ent->s.weapon ? state : NULL;
}

static int mortar_definition(const struct WeaponDef *def,codol_bomb_weapon_t *data)
{
    return CODOL_GetNativeBombWeapon(def,data) && data->type==4 && data->guidance==4;
}
int CODOL_BombUsesBallisticTrajectory(gentity_t *ent)
{
    /* Only this module's generation-checked type4/guidance4 constructor owns
     * this path. C1 DropBomb531742 leaves mortar translation at gravity5;
     * OpenBLOPS MissileTrajectory evaluates bombs/ballistic guidance normally
     * rather than entering the guided rocket's incremental trBase writer. */
    return bomb_state(ent)!=NULL && ent->s.eType==ET_MISSILE &&
        ent->s.lerp.pos.trType==TR_GRAVITY;
}
static int finite_vector(const float *v)
{
    return isfinite(v[0]) && isfinite(v[1]) && isfinite(v[2]);
}
/* Exposed separately for the generic LaunchBomb dispatcher to share once its
 * other guided-projectile branches are ported. No player firing callback,
 * player lock acquisition or ammo consumption occurs in C1 DropBomb. */
gentity_t *CODOL_SpawnMortarBomb(gentity_t *owner,unsigned weapon,
    const float start[3],const float velocity[3])
{
    struct WeaponDef *def;
    codol_bomb_weapon_t data;
    gentity_t *bomb;
    vec3_t direction,angles;
    double life;
    int i,launch_delay;
    if(!owner || !owner->r.inuse || !owner->client || !weapon ||
       weapon>=(unsigned)BG_GetNumWeapons() || !finite_vector(start) || !finite_vector(velocity))return NULL;
    def=BG_GetWeaponDef(weapon);
    if(!mortar_definition(def,&data) || data.acceleration!=0 || data.curvature!=0 ||
       data.destabilization!=0 || !isfinite(data.lifetime) || data.lifetime<=0 ||
       data.destabilization_distance<0 || def->iProjectileSpeed<=0)return NULL;
    for(i=0;i<3;++i)if(velocity[i]<INT_MIN || (double)velocity[i]>INT_MAX)return NULL;
    life=(double)data.lifetime*1000.0;
    if(life>60000)life=60000;
    if(level.time>INT_MAX-60000)return NULL;
    VectorCopy(velocity,direction);
    Vec3Normalize(direction);
    vectoangles(direction,angles);
    bomb=G_Spawn();
    if(!bomb)return NULL;
    Scr_SetString(&bomb->classname,scr_const.grenade);
    bomb->s.eType=ET_MISSILE;
    bomb->s.weapon=weapon;
    bomb->s.weaponModel=0;
    /* C1 531632..531668 clamps its launch delay independently of the
     * explicitly supplied travel velocity. */
    launch_delay=(int)(85.0-35.0*(double)def->iProjectileSpeed/600.0);
    if(launch_delay<20)launch_delay=20;
    if(launch_delay>50)launch_delay=50;
    bomb->s.lerp.u.missile.launchTime=level.time+launch_delay;
    CODOL_EntHandleSetEnt(&bomb->r.ownerNum,owner);
    CODOL_EntHandleSetEnt(&bomb->parent,owner);
    /* C1 53168b mask. Collision brush/material contents are copied verbatim
     * by codol_collision_native/materials; do not substitute IW3's mask.
     * Handler9 is native G_ExplodeMissile (C1 handler12). */
    bomb->clipmask=0x280e091;
    bomb->handler=9;
    bomb->nextthink=level.time+(int)life;
    bomb->missile.team=owner->client->sess.cs.team;
    G_SetOrigin(bomb,start);
    G_SetAngle(bomb,angles);
    bomb->s.lerp.pos.trType=TR_GRAVITY;
    bomb->s.lerp.pos.trTime=level.time;
    for(i=0;i<3;++i)bomb->s.lerp.pos.trDelta[i]=(float)(int)velocity[i];
    /* C1 guidance4:5319c7..5319dc, real linear angular trajectory75deg/s. */
    bomb->s.lerp.apos.trType=TR_LINEAR;
    bomb->s.lerp.apos.trTime=level.time;
    VectorClear(bomb->s.lerp.apos.trDelta);
    bomb->s.lerp.apos.trDelta[2]=75.0f;
    bomb->missile.time=1000.0f*(float)data.destabilization_distance/(float)def->iProjectileSpeed;
    bomb->flags|=0x20000; /* C1 531a34, zero destabilization angle. */
    if(def->projectileModel)G_SetModel(bomb,def->projectileModel->name);
    {
        bomb_state_t *state=&bomb_states[bomb->s.number];
        memset(state,0,sizeof(*state));
        state->constructed=1;
        state->generation=bomb->useCount;
        state->owner_generation=owner->useCount;
        state->owner=(unsigned)owner->s.number;
        state->weapon=weapon;
    }
    SV_LinkEntity(bomb);
    return bomb;
}

/* Narrow real VM entry while general guided LaunchBomb remains separate.
 * The staged mortar module supplies its catalogue weapon, not an alias. */
void CODOL_Scr_LaunchBomb(scr_entref_t ref)
{
    unsigned weapon;
    vec3_t start,velocity;
    gentity_t *bomb;
    if(ref.classnum || ref.entnum>=MAX_CLIENTS || !g_entities[ref.entnum].r.inuse ||
       !g_entities[ref.entnum].client){Scr_ObjectError("launchBomb requires a player");return;}
    if(Scr_GetNumParam()!=3){Scr_Error("launchBomb(weapon, position, velocity)");return;}
    weapon=G_GetWeaponIndexForName(Scr_GetString(0));
    Scr_GetVector(1,start);Scr_GetVector(2,velocity);
    bomb=CODOL_SpawnMortarBomb(&g_entities[ref.entnum],weapon,start,velocity);
    if(!bomb){Scr_Error("launchBomb currently implements C1 type4 guidance4 bombs with finite trajectories; this weapon is not supported");return;}
    Scr_AddEntity(bomb);
}
void CODOL_Scr_LaunchMortarBomb(scr_entref_t ref)
{ CODOL_Scr_LaunchBomb(ref); }

int CODOL_BombImpact(gentity_t *bomb,const trace_t *trace,const float *position)
{
    bomb_state_t *state=bomb_state(bomb);
    codol_bomb_weapon_t data;
    struct WeaponDef *def;
    if(!state || bomb->s.eType!=ET_MISSILE || !trace || !position ||
       !bomb->s.weapon || bomb->s.weapon>=(unsigned)BG_GetNumWeapons())return 0;
    def=BG_GetWeaponDef(bomb->s.weapon);
    if(!mortar_definition(def,&data))return 0;
    /* Set a settled impact position before the shared explosion code evaluates
     * the trajectory. This is a real contact, not a timer-generated barrage. */
    G_SetOrigin(bomb,position);
    bomb->s.surfType=(trace->sflags>>20)&31;
    VectorCopy(trace->normal,bomb->missile.surfaceNormal);
    bomb->nextthink=0;
    VectorCopy(position,state->contact);
    state->pending_contact=1; /* Consumed once after native radial damage. */
    G_ExplodeMissile(bomb);
    return 1; /* Explosion owns/free-converts the entity; caller must return. */
}
int CODOL_BombNotifyImpact(gentity_t *bomb)
{
    bomb_state_t *state=bomb_state(bomb);
    codol_bomb_weapon_t data;
    struct WeaponDef *def;
    gentity_t *owner;
    int generation;
    if(!bomb || !bomb->r.inuse)return 0;
    if(!state || !state->pending_contact || !bomb->s.weapon ||
       bomb->s.weapon>=(unsigned)BG_GetNumWeapons())return 1;
    def=BG_GetWeaponDef(bomb->s.weapon);
    if(!mortar_definition(def,&data))return 1;
    state->pending_contact=0;
    generation=bomb->useCount;
    if(state->owner>=MAX_CLIENTS)return 1;
    owner=&g_entities[state->owner];
    if(!owner->r.inuse || !owner->client || owner->useCount!=state->owner_generation)return 1;
    /* OpenBLOPS G_MissileImpact after G_RadiusDamage: fourth argument is
     * the still-live missile. Never send an entity handle after freeing it. */
    Scr_AddEntity(bomb);
    Scr_AddInt(def->iExplosionRadius);
    Scr_AddVector(state->contact);
    Scr_AddString(def->szInternalName);
    Scr_Notify(owner,scr_const.projectile_impact,4);
    return bomb->r.inuse && bomb->useCount==generation;
}
#endif
