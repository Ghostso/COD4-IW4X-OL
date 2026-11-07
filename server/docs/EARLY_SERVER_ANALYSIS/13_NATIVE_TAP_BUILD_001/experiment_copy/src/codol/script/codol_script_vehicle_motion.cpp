#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "g_scr_vehicle.h"
#include "qcommon_io.h"
#include <stddef.h>

extern "C" int SV_DObjGetBoneIndex(const gentity_t *,unsigned int);
extern "C" void SV_LinkEntity(gentity_t *);

/* _g_vehicles_mp.asm reserves 0x1aa0 bytes and uses eight 0x354-byte
 * records. G_VehiclesInit/SpawnVehicle/free maintain entNum at +1b8. */
static const unsigned native_vehicle_capacity=8;
static_assert(sizeof(scr_vehicle_s)==0x354,"native vehicle pool stride changed");
static_assert(offsetof(scr_vehicle_s,entNum)==0x1b8,"native vehicle occupancy field changed");
static_assert(offsetof(scr_vehicle_s,boneIndex)==0x2ec,"native vehicle ride-slot offset changed");
static_assert(sizeof(VehicleRideSlot_t)==12,"native vehicle ride-slot stride changed");
static_assert(offsetof(VehicleRideSlot_t,boneIdx)==4,"native ride bone field changed");
static_assert(offsetof(VehicleRideSlot_t,entNum)==8,"native ride occupant field changed");

/* IW4 499fa0 counts allocated pool entries. Use native occupancy rather
 * than scanning entities or counting vehicle definitions. */
extern "C" void CODOL_Scr_GetNumVehicles(void)
{
    unsigned count=0;
    if(level.vehicles)for(unsigned i=0;i<native_vehicle_capacity;++i)
        if(level.vehicles[i].entNum!=ENTITYNUM_NONE)++count;
    Scr_AddInt(count);
}

/* T5 65cd20 exposes its pool capacity (16). The retained native allocator
 * supports eight, so return its real capacity rather than T5's constant. */
extern "C" void CODOL_Scr_GetMaxVehicles(void)
{
    Scr_AddInt(native_vehicle_capacity);
}

/* IW4 0x42a690 returns occupied pool entries in slot order and requires
 * no arguments. Its excluded spawner entity type has no retained IW3
 * equivalent: native SpawnVehicle allocates live vehicle entities only. */
extern "C" void CODOL_Scr_VehicleGetArray(void)
{
    if(Scr_GetNumParam()!=0) {
        Scr_Error("vehicle_getarray requires no parameters");return;
    }
    if(level.vehicles)for(unsigned i=0;i<native_vehicle_capacity;++i) {
        unsigned number=level.vehicles[i].entNum;
        if(number!=ENTITYNUM_NONE && number>=ENTITYNUM_WORLD) {
            Scr_Error("vehicle_getarray: invalid vehicle pool entity");return;
        }
    }
    Scr_MakeArray();
    if(level.vehicles)for(unsigned i=0;i<native_vehicle_capacity;++i) {
        unsigned number=level.vehicles[i].entNum;
        if(number==ENTITYNUM_NONE)continue;
        Scr_AddEntity(&g_entities[number]);
        Scr_AddArray();
    }
}

static scr_vehicle_s *vehicle_argument(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return NULL;
    }
    scr_vehicle_s *vehicle=g_entities[ref.entnum].scr_vehicle;
    if(!vehicle)Scr_Error("Entity is not a vehicle");
    return vehicle;
}

/* T5 65cc50 is a function taking an arbitrary value, not a vehicle method.
 * Do not ask Scr_GetEntity to coerce scalars, arrays, or script structs. */
extern "C" void CODOL_Scr_IsVehicle(void)
{
    if(Scr_GetType(0)!=VAR_POINTER || Scr_GetPointerType(0)!=VAR_ENTITY) {
        Scr_AddInt(0);return;
    }
    gentity_t *entity=Scr_GetEntity(0);
    if(entity)Scr_AddInt(entity->scr_vehicle!=NULL);
}

/* T5 67ede0 queries configured usability, not current boarding eligibility.
 * Field tables ccb1d4/d32108 identify +170 as spawnflags. Native
 * SpawnVehicle uses spawnflags bit 1 to add the vehicle's use contents. */
extern "C" void CODOL_Scr_IsVehicleUsable(scr_entref_t ref)
{
    if(vehicle_argument(ref))Scr_AddInt((g_entities[ref.entnum].spawnflags&1)!=0);
}

/* T5 66d7c0 enables use contents and supplies tag_origin when all seat
 * bones are absent. Native boarding resolves both a bone and a link tag,
 * so keep that pair consistent when installing its fallback ride slot. */
static void prepare_vehicle_use(gentity_t *entity,scr_vehicle_s *vehicle)
{
    bool hasSeat=false;
    for(unsigned i=0;i<3;++i)
        if(vehicle->boneIndex.riderSlots[i].boneIdx>=0)hasSeat=true;
    if(!hasSeat) {
        VehicleRideSlot_t *slot=&vehicle->boneIndex.riderSlots[0];
        slot->boneIdx=SV_DObjGetBoneIndex(entity,scr_const.tag_origin);
        slot->tagName=scr_const.tag_origin;
    }
    entity->spawnflags|=1;
    entity->r.contents|=0x200000;
    if(entity->r.linked)SV_LinkEntity(entity);
}

extern "C" void CODOL_Scr_MakeVehicleUsable(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)prepare_vehicle_use(&g_entities[ref.entnum],vehicle);
}

/* T5 67ee70 calls the same preparation helper, then clears spawnflags bit
 * 1. Use contents remain set. Native boarding now checks the flag too. */
extern "C" void CODOL_Scr_MakeVehicleUnusable(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(!vehicle)return;
    gentity_t *entity=&g_entities[ref.entnum];
    prepare_vehicle_use(entity,vehicle);
    entity->spawnflags&=~1;
}

/* T5 680760/6807c0 use GScr_GetVehicle and read/write vehicle physics +90.
 * The retained vehicle_physic_t has the same rotVel member at +90; keep
 * values in engine angular units without conversion or normalization. */
extern "C" void CODOL_Scr_GetAngularVelocity(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)Scr_AddVector(vehicle->phys.rotVel);
}

extern "C" void CODOL_Scr_SetAngularVelocity(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(!vehicle)return;
    float velocity[3]; Scr_GetVector(0,velocity);
    for(unsigned axis=0;axis<3;++axis)vehicle->phys.rotVel[axis]=velocity[axis];
}

/* IW4 47af20/418040 expose world/body velocity without unit conversion. */
extern "C" void CODOL_Scr_VehicleGetVelocity(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)Scr_AddVector(vehicle->phys.vel);
}

extern "C" void CODOL_Scr_VehicleGetBodyVelocity(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)Scr_AddVector(vehicle->phys.bodyVel);
}

/* IW4 4082b0 multiplies speed by the double at 713888. This is MPH,
 * unlike retained getspeed. Preserve the reference constant and float store
 * rather than recomputing a reciprocal or taking the velocity magnitude. */
extern "C" void CODOL_Scr_VehicleGetSpeed(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)Scr_AddFloat((float)((double)vehicle->speed*0.05681818351149559));
}

/* IW4 67fe60: vehicle receiver, owner handle, undefined when unowned.
 * Unlike GetTurretOwner there is no active gate or sentinel fallback. */
extern "C" void CODOL_Scr_GetVehicleOwner(scr_entref_t ref)
{
    if(!vehicle_argument(ref))return;
    unsigned number=g_entities[ref.entnum].r.ownerNum.number;
    if(!number){Scr_AddUndefined();return;}
    if(number>MAX_GENTITIES){Scr_Error("Invalid vehicle owner handle");return;}
    Scr_AddEntity(&g_entities[number-1]);
}

/* IW4 67fd00 -> 4d1da0 frees vehicle state, not the entity. Retained
 * G_VehFreeEntity owns native string/target cleanup and marks the pool
 * record empty before clearing scr_vehicle. Do not bypass that lifecycle. */
extern "C" void CODOL_Scr_FreeVehicle(scr_entref_t ref)
{
    if(!vehicle_argument(ref))return;
    gentity_t *entity=&g_entities[ref.entnum];
    if(entity->r.ownerNum.number) {
        Scr_Error("Can't free vehicle that a player is using");return;
    }
    G_VehFreeEntity(entity);
}

/* IW4 67faa0 reads +2d4, the manual target written by 67f660. */
extern "C" void CODOL_Scr_GetGoalSpeedMPH(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)Scr_AddFloat((float)((double)vehicle->manualSpeed*0.05681818351149559));
}

/* IW4 67f480 accepts MPH and rejects negative wait speeds. */
extern "C" void CODOL_Scr_SetWaitSpeed(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(!vehicle)return;
    float speed=(float)((double)Scr_GetFloat(0)*17.600000381469727);
    if(speed<0.0f){Scr_ParamError(0,"Cannot set negative wait speed");return;}
    vehicle->waitSpeed=speed;
}

/* IW4 67fae0/67fb10 are direct converted stores. Unlike vehicle_setspeed,
 * these standalone setters do not check positivity or enable manual mode. */
extern "C" void CODOL_Scr_SetAcceleration(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)vehicle->manualAccel=(float)((double)Scr_GetFloat(0)*17.600000381469727);
}

extern "C" void CODOL_Scr_SetDeceleration(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(vehicle)vehicle->manualDecel=(float)((double)Scr_GetFloat(0)*17.600000381469727);
}

/* IW4 463af0 -> 67f660. Native movement consumes these manual fields;
 * don't change current velocity until the normal acceleration step. */
extern "C" void CODOL_Scr_VehicleSetSpeed(scr_entref_t ref)
{
    scr_vehicle_s *vehicle=vehicle_argument(ref);
    if(!vehicle)return;
    if(vehicle->infoIdx<0 || vehicle->infoIdx>=32) {
        Scr_Error("Invalid native vehicle definition index");return;
    }
    unsigned count=Scr_GetNumParam();
    float speed=(float)((double)Scr_GetFloat(0)*17.600000381469727);
    float acceleration=vehicle->manualAccel,deceleration;
    if(speed<0.0f){Scr_ParamError(0,"Cannot set negative speed");return;}
    if(count>1) {
        acceleration=(float)((double)Scr_GetFloat(1)*17.600000381469727);
        if(!(acceleration>0.0f)){Scr_ParamError(1,"Acceleration must be positive");return;}
    } else if(!(acceleration>0.0f)) {
        Scr_Error("Vehicle has no positive acceleration; supply an acceleration argument");return;
    }
    /* The reference caps helicopter acceleration when increasing speed.
     * Native CMD_VEH_Script_SetSpeed applies the same type-5 condition. */
    bool capped=s_vehicleInfos[vehicle->infoIdx].type==5 &&
                speed>vehicle->speed && acceleration>speed;
    if(capped)acceleration=speed;
    if(count>2) {
        deceleration=(float)((double)Scr_GetFloat(2)*17.600000381469727);
        if(!(deceleration>0.0f)){Scr_ParamError(2,"Deceleration must be positive");return;}
    } else deceleration=acceleration*0.5f;
    if(capped)Com_PrintWarning(CON_CHANNEL_SERVER,"Capping vehicle %u acceleration to target speed\n",ref.entnum);
    vehicle->manualMode=1;
    vehicle->manualSpeed=speed;
    vehicle->manualAccel=acceleration;
    vehicle->manualDecel=deceleration;
}
#endif
