#ifndef CODOL_VEHICLE_WHEELS_H
#define CODOL_VEHICLE_WHEELS_H
#include "codol_vehicle_raw.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { CODOL_VEHICLE_WHEELS=6, CODOL_WHEEL_PRESENT=1,
       CODOL_WHEEL_POWERED=2, CODOL_WHEEL_STEERING=4, CODOL_WHEEL_BRAKING=8 };
typedef struct {
    float local_origin[3];
    unsigned flags;
    float forward[3],path_speed_scale,motor_speed_scale,side_friction;
    float reserved_contact_state,radius;
} codol_vehicle_wheel_t;
typedef struct {
    codol_vehicle_wheel_t wheels[CODOL_VEHICLE_WHEELS];
    float front_center[3],rear_center[3],steering_center[3];
    float signed_wheelbase,half_track,powered_share;
} codol_vehicle_wheel_layout_t;
/* C1 6753b0 obtains actual model-local bone translations, then 65c270 and
 * 65c2e0 initialize these contact records. Four primary wheel tags must exist;
 * the remaining two are optional. Callers may not supply guessed bounds-based
 * anchors. Output unchanged on missing or unusable geometry/settings. */
int CODOL_BuildVehicleWheelLayout(const codol_vehicle_raw_t *definition,
    const float model_local_origins[CODOL_VEHICLE_WHEELS][3],
    unsigned present_mask,codol_vehicle_wheel_layout_t *out);
/* C1 65ca00 ordinary wheel controller. The two brake inputs are distinct:
 * instance flags20 is merged explicit/automatic handbrake;40 is automatic turn
 * brake. No transform integration; output directions are native local contact
 * constraint axes. Output unchanged on malformed layout or invalid steering. */
int CODOL_SteerVehicleWheels(const codol_vehicle_wheel_layout_t *layout,
    float steering_degrees,int handbrake,int automatic_handbrake,
    codol_vehicle_wheel_layout_t *out);
#ifdef __cplusplus
}
#endif
#endif
