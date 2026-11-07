/* Native C1 remote vehicle ownership and driver-seat script lifecycle. */
#ifndef CODOL_REMOTE_VEHICLE_H
#define CODOL_REMOTE_VEHICLE_H
#ifdef __cplusplus
extern "C" {
#endif
struct gentity_s;
/* control_angles must come from the vehicle's actual driver/barrel transform.
 * Returns 1 on success; rejected ownership or unsupported definition returns 0. */
int CODOL_RemoteVehicleEnter(struct gentity_s *player,struct gentity_s *vehicle,
                             const float control_angles[3]);
void CODOL_RemoteVehicleExit(unsigned client);
int CODOL_RemoteVehicleScriptExit(unsigned client);
struct gentity_s *CODOL_RemoteVehicleSeatOccupant(struct gentity_s *,int seat);
void CODOL_RemoteVehicleResetAll(void);
void CODOL_RemoteVehicleEntityFreed(const struct gentity_s *entity);
void CODOL_RemoteVehicleValidate(unsigned client);
/* Native-only type: C1 ps+1f8 has no entry in playerStateFields. */
int CODOL_RemoteVehicleType(unsigned client);
#ifdef __cplusplus
}
#endif
#endif
