/* Explicit sh1x backend tuning; these values are not recovered C1 constants. */
#ifndef CODOL_VEHICLE_SH1X_POLICY_H
#define CODOL_VEHICLE_SH1X_POLICY_H
#include "codol_vehicle_ground_frame.h"
typedef struct {
    float sag_fraction,damping_ratio,grip;
    float brake_g,handbrake_g,coast_g;
    float stability_inches; /* T5 wheel roll/pitch stability lever */
    /* T5 NitrousVehicle orientation constraint, per unit body mass. A
     * negative value means "use the vehicle asset's authored value". */
    codol_vehicle_orientation_t orientation;
} codol_vehicle_sh1x_tuning_t;
#ifdef __cplusplus
extern "C" {
#endif
int CODOL_ReadSh1xVehiclePolicy(codol_vehicle_sh1x_tuning_t *,codol_vehicle_frame_settings_t *);
/* Per-mass orientation strengths (policy, or the asset's authored value where
 * the policy says -1) times body mass. */
int CODOL_ResolveSh1xVehicleOrientation(const codol_vehicle_sh1x_tuning_t *,
    const codol_vehicle_raw_t *,float mass,codol_vehicle_orientation_t *);
int CODOL_BuildSh1xVehicleSuspension(const codol_vehicle_sh1x_tuning_t *,
    const codol_vehicle_raw_t *,const codol_vehicle_wheel_layout_t *,float mass,
    const float center_of_mass[3],float gravity,codol_vehicle_frame_wheel_t out[6]);
#ifdef __cplusplus
}
#endif
#endif
