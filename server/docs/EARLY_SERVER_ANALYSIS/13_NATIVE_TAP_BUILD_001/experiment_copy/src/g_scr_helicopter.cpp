#include "g_shared.h"
#include "g_scr_vehicle.h"


int helicopter_thinktime;

#ifdef CODOL_SERVER
extern "C" void CODOL_VehicleTurretControllerThink(struct gentity_s *vehicle);
#endif

extern "C" void Helicopter_Think(struct gentity_s* ent)
{
#ifdef CODOL_SERVER
	/* A vehicleTurretControlOn player (the chopper gunner) aims and fires
	 * this helicopter's turret; set the aim before the vehicle think turns it. */
	CODOL_VehicleTurretControllerThink(ent);
#endif
	Scr_Vehicle_Think(ent);
	ent->nextthink = level.time + helicopter_thinktime;
}