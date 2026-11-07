#ifndef CODOL_VEHICLE_CONTROLS_H
#define CODOL_VEHICLE_CONTROLS_H
#include <stdint.h>
#include "codol_vehicle_raw.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    float steering_degrees;
    int64_t boost_ready_time;
    /* T5 NitrousVehicleController::m_jump_button_pressed: set when a jump
     * fired, cleared when the button is released (holding it never re-fires). */
    int jump_pressed;
} codol_vehicle_control_state_t;
typedef struct {
    float throttle,reverse_throttle,steering_degrees;
    float forward_speed_scale,reverse_speed_scale,boost_acceleration;
    /* C1 vehicle+22c merges explicit button and automatic turn braking;
     * +22d preserves automatic braking separately. Wheel constraints need both. */
    int boost_active,boost_ready,handbrake,automatic_handbrake;
} codol_vehicle_controls_t;
/* C1 signed command axes, no IW3 usercmd translation. This decodes the actual
 * controller; physics applies its resulting demands later. view_angle_steering
 * must be resolved from C1 VehicleDef+2cc, not guessed from a raw field name.
 * current_speed is C1 vehicle speed, not a source maxVelocity assumption.
 * Output/state unchanged on unsupported or invalid data. */
int CODOL_StepGroundVehicleControls(const codol_vehicle_raw_t *definition,
    int forward,int right,uint32_t buttons,int view_angle_steering,
    float driver_yaw,float vehicle_yaw,int now,float frame_seconds,
    float current_speed,codol_vehicle_control_state_t *state,
    codol_vehicle_controls_t *out);
#ifdef __cplusplus
}
#endif
#endif
