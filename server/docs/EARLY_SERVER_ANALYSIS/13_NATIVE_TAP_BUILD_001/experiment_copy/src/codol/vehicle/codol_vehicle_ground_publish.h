#ifndef CODOL_VEHICLE_GROUND_PUBLISH_H
#define CODOL_VEHICLE_GROUND_PUBLISH_H
#include "codol_vehicle_ground_frame.h"
#ifdef __cplusplus
extern "C" {
#endif
/* All generations are validated before any entity mutation. Presentation is
 * the selected backend's presentation pose; physics remains the authoritative
 * pose/velocities. No wheel bones or C1 client flags are fabricated here. */
int CODOL_PublishGroundVehicleFrame(const codol_vehicle_frame_body_t *,
    const codol_vehicle_frame_pose_t *,unsigned count);
#ifdef __cplusplus
}
#endif
#endif
