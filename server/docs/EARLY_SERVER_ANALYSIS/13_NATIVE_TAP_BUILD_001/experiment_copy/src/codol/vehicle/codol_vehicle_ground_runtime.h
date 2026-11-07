#ifndef CODOL_VEHICLE_GROUND_RUNTIME_H
#define CODOL_VEHICLE_GROUND_RUNTIME_H
#include "codol_vehicle_ground_frame.h"
#include "codol_vehicle_t5_suspension.h"
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
/* Constructor receives resolved physical wheel parameters, never guessed
 * spring units. Four actual model wheel tags remain mandatory. */
int CODOL_AttachGroundVehicle(struct gentity_s *,const codol_vehicle_frame_wheel_t normalized[6],
    const codol_vehicle_frame_settings_t *);
/* Same owned constructor, with T5 normalization performed AFTER actual body
 * mass/COM and wheel tags exist. Failure releases the prospective body without
 * publishing ownership. Named T5 parameters must come from a verified source. */
int CODOL_AttachT5GroundVehicle(struct gentity_s *,const codol_vehicle_t5_suspension_t *,
    float gravity_multiplier,const codol_vehicle_frame_settings_t *);
/* Temporary explicit sh1x policy, only for actual rc_car_medium_mp assets.
 * 0: other vehicle, 1: attached, -1: RC construction failed. */
int CODOL_AttachSpawnedRCVehicle(struct gentity_s *);
int CODOL_GroundVehicleOwned(const struct gentity_s *);
void CODOL_GroundVehicleEntityFreed(const struct gentity_s *);
void CODOL_ResetGroundVehicleRuntime(void);
/* Run once after clients' actual command execution, before entity snapshots.
 * Returns0 on physical failure and leaves that failed frame unpublished. */
int CODOL_RunGroundVehicles(int now);
void CODOL_RunGroundVehiclesFrame(void);
#ifdef __cplusplus
}
#endif
#endif
