/* Native vehicle spawners, IW4 4283b0/6806a0 and C1 67b6d0.
 * Reference type17 collides with IW3 temporary events. Preserve the retained
 * simulation discriminator and own the spawner category as native entity
 * metadata. SVF_NOCLIENT keeps this server-only object out of snapshots. */
#ifdef CODOL_SERVER
#include "codol_vehicle_spawner.h"
#include "codol_vehicle_assets.h"
#include "codol_vehicle_native.h"
#include "scr_vm_functions.h"
#include "cscr_stringlist.h"
#include "g_public.h"
#include "server.h"
#include "server_public.h"
#include "cm_public.h"
#include <string.h>

static codol_vehicle_spawner_t spawners[MAX_GENTITIES];
void CODOL_ResetVehicleSpawner(unsigned number)
{
    if(number<MAX_GENTITIES) memset(&spawners[number],0,sizeof(spawners[number]));
}
void CODOL_ResetVehicleSpawners(void) { memset(spawners,0,sizeof(spawners)); }
static int spawner_number(const gentity_t *entity)
{
    if(!entity || entity->s.number<0 || entity->s.number>=ENTITYNUM_WORLD ||
       entity!=&g_entities[entity->s.number]) return -1;
    return entity->s.number;
}
const codol_vehicle_spawner_t *CODOL_VehicleSpawner(const gentity_t *entity)
{
    int number=spawner_number(entity);
    if(number<0 || !entity->r.inuse || !spawners[number].known) return NULL;
    return &spawners[number];
}
int CODOL_CreateVehicleSpawner(gentity_t *entity,const char *vehicle_name)
{
    codol_vehicle_spawner_t value={0};
    int number=spawner_number(entity);
    if(number<0 || !entity->r.inuse || entity->client || entity->scr_vehicle ||
       !vehicle_name || !*vehicle_name) return 0;
    value.vehicle_info=CODOL_VehicleInfoForSpawn(vehicle_name);
    value.vehicle_slot=CODOL_VehicleSlotForName(vehicle_name);
    if(value.vehicle_info<0 || value.vehicle_slot<=0) return 0;
    value.known=1;
    /* Reference clears collision and sets NOCLIENT. Native event cleanup
     * and think scheduling must also remain inactive for this category.
     * A native ET_GENERAL entity with no think is inert; assigning IW4/C1's
     * literal17 here would send it through IW3's temporary-event lifetime. */
    entity->s.eType=ET_GENERAL;
    entity->r.contents=0;
    entity->r.svFlags=SVF_NOCLIENT;
    entity->freeAfterEvent=0;
    entity->unlinkAfterEvent=0;
    entity->nextthink=0;
    spawners[number]=value;
    return 1;
}
/* IW4 5f6630: argument0 must be a pointer to an entity; all other values
 * return integer0. No argument-count check or receiver/classname heuristic. */
void CODOL_Scr_IsSpawner(void)
{
    if(Scr_GetType(0)!=VAR_POINTER || Scr_GetPointerType(0)!=VAR_ENTITY) {
        Scr_AddInt(0); return;
    }
    Scr_AddInt(CODOL_VehicleSpawner(Scr_GetEntity(0))!=NULL);
}
/* IW4 4c4390: exactly0 args, entity order, only in-use vehicle spawners.
 * Spawners do not occupy the live vehicle pool used by vehicle_getarray. */
void CODOL_Scr_VehicleGetSpawnerArray(void)
{
    int i;
    if(Scr_GetNumParam()!=0) {
        Scr_Error("vehicle_getspawnerarray requires no parameters"); return;
    }
    if(level.num_entities<0 || level.num_entities>MAX_GENTITIES) {
        Scr_Error("vehicle spawner entity span is invalid"); return;
    }
    Scr_MakeArray();
    for(i=0;i<level.num_entities;++i) if(CODOL_VehicleSpawner(&g_entities[i])) {
        Scr_AddEntity(&g_entities[i]); Scr_AddArray();
    }
}

/* Per-spawn version of the retained G_VehiclesSetupSpawnedEnts collmap
 * lookup. C1 6747d0/674850 performs this in the common factory, including
 * script-created vehicles, instead of only in a map-start pool traversal. */
static void setup_spawned_vehicle_collision(gentity_t *entity)
{
    const char *model;
    int i;
    if(!entity->model) return;
    model=SL_ConvertToString(G_ModelName(entity->model));
    for(i=0;i<level.num_entities;++i) {
        gentity_t *candidate=&g_entities[i];
        if(!candidate->r.inuse || !candidate->classname ||
           Q_stricmp(SL_ConvertToString(candidate->classname),"script_vehicle_collmap") ||
           Q_stricmp(SL_ConvertToString(candidate->targetname),model)) continue;
        /* C1 returns after the first matching template, even if empty. */
        if(!candidate->s.index) {
            Com_PrintWarning(CON_CHANNEL_SERVER,
                "WARNING: Cannot use empty vehicle collmap for [%s]\n",model);
            return;
        }
        if(!CM_ClipHandleIsValid(candidate->s.index)) {
            Com_Error(ERR_DROP,"Invalid vehicle collision brush for [%s]",model);
            return;
        }
        SV_UnlinkEntity(entity);
        entity->s.index=candidate->s.index;
        if(!SV_SetBrushModel(entity)) {
            Com_Error(ERR_DROP,"Could not install vehicle collision brush for [%s]",model);
            return;
        }
        entity->r.contents=(entity->spawnflags&1)?0xa00000:0x800000;
        /* SV_SetBrushModel links using brush contents. Relink after the
         * vehicle-specific contents assignment, as C1 6748ee..674908 does. */
        SV_LinkEntity(entity);
        return;
    }
}

/* IW4 4f3e10: model string0, targetname const-string1, vehicle definition
 * const-string2, origin3, angles4. No explicit count check; extra args are
 * ignored and missing/wrongly typed arguments fail through the VM readers.
 * This global creates a fresh live vehicle, not a spawner conversion. */
void CODOL_Scr_SpawnVehicle(void)
{
    const char *model=Scr_GetString(0);
    unsigned targetname=Scr_GetConstString(1);
    unsigned vehicle_name=Scr_GetConstString(2);
    unsigned classname;
    const char *vehicle_type;
    const codol_vehicle_native_t *definition;
    int vehicle_info;
    vec3_t origin,angles;
    gentity_t *entity;
    Scr_GetVector(3,origin);
    Scr_GetVector(4,angles);
    vehicle_type=SL_ConvertToString(vehicle_name);
    vehicle_info=CODOL_VehicleInfoForSpawn(vehicle_type);
    definition=CODOL_NativeVehicleDefinition(vehicle_info);
    if(!definition) {
        Scr_Error("spawnvehicle could not load its vehicle definition"); return;
    }
    entity=G_Spawn();
    /* IW4 initializes two internal classname words to script_vehicle. Native
     * IW3 has one classname field; use the actual CoDOL name, not its legacy
     * script_vehicle_mp spelling or an invented dynamic script property. */
    classname=SL_GetString("script_vehicle",0);
    Scr_SetString(&entity->classname,(unsigned short)classname);
    SL_RemoveRefToString(classname);
    G_SetModel(entity,model);
    Scr_SetString(&entity->targetname,(unsigned short)targetname);
    VectorCopy(origin,entity->r.currentOrigin);
    VectorCopy(angles,entity->r.currentAngles);
    /* C1 67a51b..67a52f and IW4 49f23e..49f24d select helicopter for
     * definition type5, vehicle otherwise. Use the native helicopter
     * initializer for its handler, physical bounds and position setup;
     * changing eType after an ordinary spawn alone misses those producers.
     * The CoDOL helicopter path accepts this absent spawning player.
     * This draft still awaits complete vehicle snapshot publication and
     * review of the remaining helicopter-specific state before binding. */
    if(definition->type==5) {
        G_SpawnHelicopter(entity,NULL,vehicle_type,model);
        /* The legacy helicopter script factory overwrites health with
         * 99999. This generic CoDOL factory keeps VehicleDef health
         * (C1 67a55d..67a57b), just like the ground-vehicle path. */
        entity->health=definition->health;
    } else
        SpawnVehicle(entity,vehicle_type);
    setup_spawned_vehicle_collision(entity);
    Scr_AddEntity(entity);
}
#endif
