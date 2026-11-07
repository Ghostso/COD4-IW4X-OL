#ifndef CODOL_VEHICLE_DRIVE_H
#define CODOL_VEHICLE_DRIVE_H
#include "codol_vehicle_raw.h"
#pragma pack(push,8)
#ifdef __cplusplus
extern "C" {
#endif
enum { CODOL_VEHICLE_ACCEL_KNOTS=32 };
typedef struct { float speed_fraction,acceleration_fraction; } codol_vehicle_accel_knot_t;
typedef struct {
    unsigned count;
    codol_vehicle_accel_knot_t knots[CODOL_VEHICLE_ACCEL_KNOTS];
    /* C1 per-definition graph record +144. Source units are mph/sec. */
    float maximum_acceleration;
} codol_vehicle_acceleration_t;
typedef struct {
    /* Physical instance state, not retained vehicleDef speed aliases. */
    float forward_speed,forward_axis_z,max_speed,mass_scale;
    float forward_target,reverse_target,reverse_fraction,boost_acceleration;
    float previous_friction;
} codol_vehicle_drive_input_t;
typedef struct {
    float motor_target,motor_force,longitudinal_friction;
    int reversing,wake_body;
} codol_vehicle_drive_output_t;
/* C1 618d80 interpolation. Invalid/uncovered input fails without an output. */
int CODOL_EvaluateVehicleAcceleration(const codol_vehicle_acceleration_t *,float,float *);
/* C1 65d0c0 ordinary four-wheel motor/friction path. Contact-relative forward
 * velocity and mass_scale must come from the real physics instance. This does
 * not substitute velocity integration for a wheel/contact constraint solver. */
int CODOL_ResolveGroundVehicleDrive(const codol_vehicle_ground_settings_t *,
    const codol_vehicle_acceleration_t *,const codol_vehicle_drive_input_t *,
    codol_vehicle_drive_output_t *);
/* C1 683d00..683daa applies this to each positive speed demand before boost. */
int CODOL_ApplyVehicleHandbrakeTarget(float target,float speed,float *out);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
