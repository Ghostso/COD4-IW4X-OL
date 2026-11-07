#ifndef CODOL_VEHICLE_GRAPH_H
#define CODOL_VEHICLE_GRAPH_H
#include "codol_vehicle_drive.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* C1 GRAPH_FLOAT_FILE data. Output unchanged unless valid and complete. */
int CODOL_ParseVehicleAccelerationGraph(const char *,size_t,codol_vehicle_acceleration_t *);
/* Mounted type36 rawfile vehicle/<accelerationGraph>. 1=loaded,0=missing,-1=invalid.
 * This is the actual C1 graph dependency, not vehicles/<vehicle definition>. */
int CODOL_LoadVehicleAccelerationGraph(const codol_vehicle_raw_t *,codol_vehicle_acceleration_t *);
/* Borrowed from the validated installed definition; reset/replacement invalidates it. */
const codol_vehicle_acceleration_t *CODOL_NativeVehicleAcceleration(int info_index);
#ifdef __cplusplus
}
#endif
#endif
