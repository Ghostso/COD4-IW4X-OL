#ifndef CODOL_VEHICLE_SPAWNER_H
#define CODOL_VEHICLE_SPAWNER_H
#include "entity.h"
#pragma pack(push, 8)
#ifdef __cplusplus
extern "C" {
#endif
/* Server-only entity category, separate from IW3's ET_EVENTS=17. The vehicle
 * definition is loaded now; no live vehicle pool entry exists until spawned. */
typedef struct {
    int known;
    int vehicle_slot;
    int vehicle_info;
} codol_vehicle_spawner_t;
int CODOL_CreateVehicleSpawner(gentity_t *entity,const char *vehicle_name);
const codol_vehicle_spawner_t *CODOL_VehicleSpawner(const gentity_t *entity);
void CODOL_ResetVehicleSpawner(unsigned entity_number);
void CODOL_ResetVehicleSpawners(void);
void CODOL_Scr_IsSpawner(void);
void CODOL_Scr_VehicleGetSpawnerArray(void);
/* Draft: registration awaits native factory type/initialization parity. */
void CODOL_Scr_SpawnVehicle(void);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
