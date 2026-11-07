/* Original T5 forced spawnactor lifecycle using owned native C1 actors.
 * No entity is returned until its actual aitype, tree and animscripts initialize.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifdef CODOL_SERVER
/* The retained headers declare C functions without linkage guards. */
extern "C" {
#include "codol_actor_lifecycle.h"
#include "codol_actor_scripts.h"
#include "g_shared.h"
#include "g_public.h"
#include "server.h"
#include "qcommon.h"
#include "codol_sentient.h"
#include "cscr_stringlist.h"
#include "game/surfaceflags.h"
#include <string.h>
}
extern "C" void G_DuplicateEntityFields(gentity_s *,const gentity_s *);
extern "C" int CODOL_ActorCopySpawnerScriptFields(gentity_s *,const gentity_s *);
/* Every silent return below used to reach script as a bare `undefined`, which
 * _dogs.gsc then dereferenced and killed the map with. Name the cause once. */
#define DOGS_WARN(...) Com_PrintWarning(CON_CHANNEL_SERVER, "CoDOL actor: " __VA_ARGS__)
static const char *SpawnerClassName(const gentity_s *spawner)
{
    return spawner->classname?SL_ConvertToString(spawner->classname):"(no classname)";
}
static const char *SpawnerString(unsigned short handle,const char *none)
{
    return handle?SL_ConvertToString(handle):none;
}
/* gentity_s::model is a CS_MODELS slot (what G_ModelIndex returns), not a
 * string handle - resolve it through the configstring bank rather than
 * SL_ConvertToString, which would print an unrelated string. */
static const char *SpawnerModel(const gentity_s *entity)
{
    unsigned handle;
    if(!entity->model)return "(none)";
    handle=G_ModelName(entity->model); /* every native model slot */
    if(!handle || handle==sv.emptyConfigString)return "(unpublished model slot)";
    return SL_ConvertToString(handle);
}
/* One line per entity, naming what the entity actually is. mp_nuked authors an
 * entity with targetname "dog_spawner" that is NOT an actor spawner, so
 * _dogs.gsc's getent() found it and handed it to spawnactor(); the old
 * Scr_ObjectError then killed the whole match. Report and refuse instead. */
static void DescribeNonSpawner(const gentity_s *entity,const char *method)
{
    static int reported[64];static unsigned reportedCount;unsigned i;
    for(i=0;i<reportedCount;++i)if(reported[i]==entity->s.number)return;
    if(reportedCount<64)reported[reportedCount++]=entity->s.number;
    DOGS_WARN("%s() on entity %d is not an actor spawner and was refused: "
              "classname '%s', targetname '%s', model %u '%s', eType %d "
              "(ET_ACTOR_SPAWNER is %d), spawnflags 0x%x, svFlags 0x%x\n",
              method,entity->s.number,SpawnerClassName(entity),
              SpawnerString(entity->targetname,"(none)"),
              (unsigned)entity->model,SpawnerModel(entity),
              (int)entity->s.eType,(int)ET_ACTOR_SPAWNER,
              (unsigned)entity->spawnflags,(unsigned)entity->r.svFlags);
}
static gentity_s *LiveReceiver(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=ENTITYNUM_WORLD || !g_entities[ref.entnum].r.inuse)
        return NULL;
    return &g_entities[ref.entnum];
}
/* Returns NULL and leaves the builtin's script return value unset - that is
 * `undefined` in script - rather than raising. _dogs.gsc already skips an
 * undefined dog, so a map that mislabels an entity can no longer end a match. */
static gentity_s *SpawnerReceiver(scr_entref_t ref,const char *method)
{
    gentity_s *entity=LiveReceiver(ref);
    if(!entity) {
        DOGS_WARN("%s() requires an actor spawner; the receiver is not a live entity\n",method);
        return NULL;
    }
    if(entity->s.eType!=ET_ACTOR_SPAWNER) {
        DescribeNonSpawner(entity,method);return NULL;
    }
    return entity;
}
/* <ent> isactorspawner() - the test _dogs.gsc needs before it prefers a map
 * entity over the template it builds. Truth is the same condition
 * SpawnerReceiver enforces, so the two can never disagree. */
static void ActorSpawnerIs(scr_entref_t ref)
{
    gentity_s *entity=LiveReceiver(ref);
    if(entity && entity->s.eType==ET_ACTOR_SPAWNER){Scr_AddInt(1);return;}
    if(entity)DescribeNonSpawner(entity,"isactorspawner");
    Scr_AddInt(0);
}
static void ActorSpawnerTeam(scr_entref_t ref)
{
    gentity_s *spawner=SpawnerReceiver(ref,"setspawnerteam");if(!spawner)return;
    const char *name=Scr_GetString(0);
    if(!strcmp(name,"axis"))spawner->team=CODOL_SENTIENT_TEAM_AXIS;
    else if(!strcmp(name,"allies"))spawner->team=CODOL_SENTIENT_TEAM_ALLIES;
    else if(!strcmp(name,"neutral") || !strcmp(name,"none"))spawner->team=CODOL_SENTIENT_TEAM_NONE;
    else Scr_ParamError(0,"unknown spawner team");
}
static void ActorSpawn(scr_entref_t ref)
{
    gentity_s *spawner=SpawnerReceiver(ref,"spawnactor");if(!spawner)return;
    int noEnemyInfo=Scr_GetNumParam()?Scr_GetInt(0):0;
    unsigned short target=Scr_GetNumParam()>1?Scr_GetConstString(1):0;
    const char *cls=SpawnerClassName(spawner);
    if(!spawner->count){ // authored zero exhausts; negative count unlimited
        DOGS_WARN("spawnactor on '%s' (ent %d): spawner count exhausted\n",cls,spawner->s.number);return;
    }
    unsigned spawnerGeneration=(unsigned)spawner->useCount;
    gentity_s *actor=G_Spawn();
    if(!actor){DOGS_WARN("spawnactor on '%s': no free entity slot\n",cls);return;}
    unsigned actorGeneration=(unsigned)actor->useCount;
    G_DuplicateEntityFields(actor,spawner);
    if(!CODOL_ActorCopySpawnerScriptFields(actor,spawner)){
        DOGS_WARN("spawnactor on '%s': could not duplicate the spawner's script fields\n",cls);
        G_FreeEntity(actor);return;
    }
    Scr_SetString(&actor->targetname,target);
    actor->spawnflags&=~1u;
    actor->s.eType=ET_ACTOR;
    actor->r.svFlags&=~SVF_NOCLIENT;
    actor->handler=ENT_HANDLER_CODOL_ACTOR;
    actor->r.mins[0]=actor->r.mins[1]=-15;actor->r.mins[2]=0;
    actor->r.maxs[0]=actor->r.maxs[1]=15;actor->r.maxs[2]=72;
    actor->r.contents=CONTENTS_BODY;
    actor->clipmask=0x2820015; // C1 SP_actor's collision categories, native capsule
    actor->takedamage=1;
    actor->team=spawner->team;
    G_SetOrigin(actor,spawner->r.currentOrigin);
    memcpy(actor->r.currentAngles,spawner->r.currentAngles,12);
    memcpy(actor->s.lerp.apos.trBase,actor->r.currentAngles,12);
    if(!CODOL_ActorAllocate(actor,spawner->team)) {
        DOGS_WARN("spawnactor on '%s': no free actor slot / sentient record (team %d, %d actor slots)\n",
                  cls,spawner->team,CODOL_MAX_ACTOR_SLOTS);
        if(actor->r.inuse && (unsigned)actor->useCount==actorGeneration)G_FreeEntity(actor);
        return;
    }
    if(!CODOL_ActorScriptsInitialize(actor)) {
        /* codol_actor_scripts.cpp / codol_actor_lifecycle.cpp name the stage. */
        DOGS_WARN("spawnactor on '%s': actor ent %d initialization failed (the stage warning above names why); actor freed\n",
                  cls,actor->s.number);
        if(actor->r.inuse && (unsigned)actor->useCount==actorGeneration)G_FreeEntity(actor);
        return;
    }
    if(!actor->r.inuse || (unsigned)actor->useCount!=actorGeneration){
        DOGS_WARN("spawnactor on '%s': actor was deleted by its own init scripts\n",cls);return;
    }
    actor->maxHealth=actor->health;
    if(!noEnemyInfo)CODOL_ActorInheritSight(actor);
    SV_LinkEntity(actor);
    /* The actor exists and is linked from here on: a spawner that its own
     * "spawned" listeners delete must not turn a live dog into `undefined`. */
    if(spawner->r.inuse && (unsigned)spawner->useCount==spawnerGeneration) {
        if(spawner->count>0)--spawner->count;
        spawner->item[0].clipAmmoCount=level.time;
        unsigned name=SL_GetString("spawned",0);
        Scr_AddEntity(actor);Scr_Notify(spawner,(unsigned short)name,1);
        SL_RemoveRefToString(name);
    }
    if(actor->r.inuse && (unsigned)actor->useCount==actorGeneration)Scr_AddEntity(actor);
    else DOGS_WARN("spawnactor on '%s': actor was deleted by a \"spawned\" listener\n",cls);
}
/* spawnactorspawner( <classname>, <origin>, [<angles>], [<count>] )
 *
 * T5's MP maps ship an `actor_enemy_dog_mp` entity with spawnflag 1 and
 * targetname "dog_spawner", and maps\mp\_dogs.gsc finds it with getent(). No
 * CoDOL MP map authors one, and inventing map entity-string data at load time
 * would be worse than letting script ask for the template it needs. This
 * builds the SAME entity the map spawner path builds: the classname is
 * dispatched through CODOL_Sentient_SpawnActorEntity, so the aitype's own
 * spawner() still runs on it and spawnactor still has authored fields to
 * duplicate. It returns nothing when the aitype scripts are not loaded - an
 * inert template is never handed back as if it could spawn. */
static void ActorSpawnerCreate(void)
{
    const char *classname=Scr_GetString(0);
    vec3_t origin,angles={0,0,0};
    int count=-1,i;
    gentity_s *spawner;
    unsigned generation,name;
    if(Q_stricmpn(classname,"actor_",6)) {
        Scr_ParamError(0,"spawnactorspawner needs an actor_ classname");return;
    }
    Scr_GetVector(1,origin);
    if(Scr_GetNumParam()>2)Scr_GetVector(2,angles);
    if(Scr_GetNumParam()>3)count=Scr_GetInt(3);
    for(i=0;i<3;++i)
        if(!isfinite(origin[i]) || !isfinite(angles[i])) {
            Scr_ParamError(1,"spawnactorspawner origin/angles must be finite");return;
        }
    spawner=G_Spawn();
    if(!spawner){DOGS_WARN("spawnactorspawner '%s': no free entity slot\n",classname);return;}
    generation=(unsigned)spawner->useCount;
    name=SL_GetString(classname,0);
    Scr_SetString(&spawner->classname,(unsigned short)name);
    SL_RemoveRefToString(name);
    spawner->spawnflags|=1u;
    /* A negative count is the unlimited spawner ActorSpawn already honours;
     * the map-entity path cannot express it because "count" is authored text. */
    spawner->count=count;
    G_SetOrigin(spawner,origin);
    memcpy(spawner->r.currentAngles,angles,sizeof(angles));
    memcpy(spawner->s.lerp.apos.trBase,angles,sizeof(angles));
    if(!CODOL_Sentient_SpawnActorEntity(spawner,classname))
        DOGS_WARN("spawnactorspawner '%s': the actor spawn path rejected the classname\n",classname);
    else if(!spawner->r.inuse || (unsigned)spawner->useCount!=generation)
        DOGS_WARN("spawnactorspawner '%s': the template entity was freed while spawning\n",classname);
    else if(spawner->s.eType!=ET_ACTOR_SPAWNER)
        DOGS_WARN("spawnactorspawner '%s': the spawn path built eType %d, not an actor spawner\n",classname,spawner->s.eType);
    else if(!CODOL_ActorScriptsSpawnerReady(spawner))
        DOGS_WARN("spawnactorspawner '%s': aitype/%s or the dog animscripts are not loaded+precached\n",classname,classname+6);
    else goto ready;
    if(spawner->r.inuse && (unsigned)spawner->useCount==generation)
        G_FreeEntity(spawner);
    return;
ready:
    /* The aitype spawner() may have rewritten count; the caller's choice wins. */
    spawner->count=count;
    Scr_AddEntity(spawner);
}
extern "C" void CODOL_ActorRegisterSpawnMethods(void)
{
    Scr_AddMethod("spawnactor",ActorSpawn,qfalse);
    Scr_AddMethod("setspawnerteam",ActorSpawnerTeam,qfalse);
    Scr_AddMethod("isactorspawner",ActorSpawnerIs,qfalse);
    Scr_AddFunction("spawnactorspawner",ActorSpawnerCreate,qfalse);
}
#endif
