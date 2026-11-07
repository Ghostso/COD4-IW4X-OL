#ifdef CODOL_SERVER
#include "scr_vm_functions.h"
#include "g_scr_vehicle.h"
#include <stddef.h>

/* IW4 isturretready 0x6801b0 resolves a script_vehicle receiver through the
 * shared vehicle validator 0x451500, requires the vehicle's player-controlled
 * state, and returns whether the vehicle turret cooldown has expired:
 * cmp dword [vehicle+0x250],0 / jg -> 0, else 1, pushed as VM integer by
 * 0x41d7d0. IW4 fireweapon reloads that same +0x250 from the weapon def at
 * 0x4e25fb, so it is the turret refire delay, not a turret-info field.
 *
 * Native retained code keeps the identical value in scr_vehicle_s.turret.
 * G_VehEntHandler_Think counts turret.fireTime down by level.frametime and
 * fires only once it reaches zero, then reloads it from the weapon def after
 * Bullet_Fire; SpawnVehicle zeroes it. Its player-controlled state is
 * scr_vehicle_s.flags bit 1, which G_VehEntHandler_Use sets when a player
 * takes a ride slot, G_VehUnlinkPlayer clears on exit, and the same think
 * gates turret firing on. */

static_assert(sizeof(scr_vehicle_s)==0x354,"native vehicle pool stride changed");
static_assert(offsetof(scr_vehicle_s,flags)==0x1c0,"native vehicle flags moved");
static_assert(offsetof(scr_vehicle_s,turret)==0x1d4,"native vehicle turret block moved");
static_assert(offsetof(VehicleTurret,fireTime)==0,"native turret cooldown moved");

#define VEH_FLAG_PLAYER_CONTROLLED 0x1

extern "C" void CODOL_Scr_IsTurretReady(scr_entref_t ref)
{
    if(ref.classnum || ref.entnum>=MAX_GENTITIES) {
        Scr_ObjectError("Not an entity"); return;
    }
    scr_vehicle_s *vehicle=g_entities[ref.entnum].scr_vehicle;
    /* IW4 only warns here and then dereferences the null vehicle. */
    if(!vehicle) { Scr_Error("Entity is not a vehicle"); return; }
    if(!(vehicle->flags&VEH_FLAG_PLAYER_CONTROLLED)) {
        Scr_ObjectError("Must be called on a player controlled vehicle"); return;
    }
    Scr_AddInt(vehicle->turret.fireTime<=0);
}
#endif
