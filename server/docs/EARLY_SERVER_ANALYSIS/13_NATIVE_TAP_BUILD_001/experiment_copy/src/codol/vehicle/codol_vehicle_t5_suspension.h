#ifndef CODOL_VEHICLE_T5_SUSPENSION_H
#define CODOL_VEHICLE_T5_SUSPENSION_H
#include "codol_vehicle_ground_frame.h"
/* Named T5 physics parameters: these are NOT C1 VehiclePhysDef aliases.
 * No generic constructor defaults are substituted for missing RC tuning. */
typedef struct {
    float spring_k,damping_k,suspension_adjustment,hard_limit;
    float wheel_radius,forward_friction,side_friction,side_friction_max;
    float roll_stability,braking,power_braking,coasting;
} codol_vehicle_t5_suspension_t;
#ifdef __cplusplus
extern "C" {
#endif
/* Converts T5's actual mass-normalized spring parameters to physical rows,
 * using actual chassis COM and model wheel tags. Output unchanged on failure.
 * Parameter source identity must be established by caller; neither this API
 * nor the runtime treats C1 raw/binary spring numbers as equivalent units. */
int CODOL_BuildT5VehicleSuspension(const codol_vehicle_t5_suspension_t *,
    const codol_vehicle_wheel_layout_t *,float mass,const float model_center_of_mass[3],
    float gravity_multiplier,codol_vehicle_frame_wheel_t out[6]);
#ifdef __cplusplus
}
#endif
#endif
