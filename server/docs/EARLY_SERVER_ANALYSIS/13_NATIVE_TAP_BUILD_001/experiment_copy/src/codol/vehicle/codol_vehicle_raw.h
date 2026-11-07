/* Native ground vehicle settings from shipped C1 VEHICLEFILE raw assets. */
#ifndef CODOL_VEHICLE_RAW_H
#define CODOL_VEHICLE_RAW_H
#include "codol_vehicle_native.h"
#include <stddef.h>
#pragma pack(push,8)
#ifdef __cplusplus
extern "C" {
#endif
enum { CODOL_VEHICLE_RAW_FIELDS=192 };
enum { CODOL_GROUND_PHYSICS=1, CODOL_GROUND_CONTROL=2,
       CODOL_GROUND_CAMERA=4, CODOL_GROUND_SOURCE_TEXT=8 };
typedef struct { char key[64],value[128]; } codol_vehicle_raw_field_t;
typedef enum { CODOL_AXLE_FRONT, CODOL_AXLE_REAR, CODOL_AXLE_ALL } codol_vehicle_axle_t;
typedef struct {
    int remote_control,third_person_driver,boost_enabled,handbrake_enabled;
    codol_vehicle_axle_t steering_axle,power_axle,braking_axle;
    float wheel_radius,suspension_travel_rear;
    float suspension_strength_front,suspension_strength_rear;
    float suspension_damping_front,suspension_damping_rear;
    float max_steering_angle,steering_lerp,min_steering_scale,min_steering_speed;
    float friction_braking,friction_coasting,friction_top_speed;
    float friction_side,friction_side_rear,velocity_dependent_slip;
    float roll_stability,roll_resistance,pitch_resistance,yaw_resistance;
    float upright_strength_pitch,upright_strength_roll,target_air_pitch;
    float air_yaw_torque,air_pitch_torque;
    float boost_speed_multiplier,boost_accel_multiplier,boost_duration,boost_recharge_time;
    float camera_range,camera_height,camera_height_min,camera_pitch,camera_pitch_min;
    float camera_min_pitch_clamp,camera_max_pitch_clamp,camera_spring_distance;
    float camera_spring_time,camera_handbrake_turn_rate,camera_fov;
    /* These distinct physics text settings retain source units. Do not
     * replace them with common.top_speed or assume all velocities are mph. */
    float max_velocity_source,reverse_speed_source;
} codol_vehicle_ground_settings_t;
typedef struct {
    codol_vehicle_native_t common;
    codol_vehicle_ground_settings_t ground;
    /* Explicit coverage: binary physics/control decoding does not yet claim
     * camera reconstruction. Activation must require its needed domains. */
    unsigned decoded_domains;
    unsigned count;
    /* Preserve every source setting, including fields with no current native
     * consumer. No borrowed archive pointers and no silently dropped keys. */
    codol_vehicle_raw_field_t fields[CODOL_VEHICLE_RAW_FIELDS];
} codol_vehicle_raw_t;
/* 1 success, -1 malformed/unsupported ground record. Output unchanged on error.
 * Common speed/acceleration fields are converted once from text mph to in/s;
 * named ground settings retain source units pending their own consumers. */
int CODOL_ParseGroundVehicleFile(const char *name,const char *bytes,size_t size,codol_vehicle_raw_t *out);
/* Mounted vehicles/<name> type36, 1 loaded, 0 absent, -1 unusable. */
int CODOL_LoadGroundVehicleFile(const char *name,codol_vehicle_raw_t *out);
/* Installed ground settings from binary VehicleDef or raw VEHICLEFILE, or
 * NULL for a non-ground/stale record. Inspect decoded_domains before use.
 * Borrowed until CODOL_ResetNativeVehicles or record replacement;
 * callers must not retain this pointer across either lifecycle boundary. */
const codol_vehicle_raw_t *CODOL_NativeGroundVehicleDefinition(int info_index);
const char *CODOL_GroundVehicleSourceValue(const codol_vehicle_raw_t *,const char *key);
int CODOL_GroundVehicleSourceNumber(const codol_vehicle_raw_t *,const char *key,float *value);
#ifdef __cplusplus
}
#endif
#pragma pack(pop)
#endif
