#ifndef CODOL_VEHICLE_GROUND_BINARY_H
#define CODOL_VEHICLE_GROUND_BINARY_H
#include "codol_vehicle_raw.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Binary C1 physics/control block into the native ground settings used by the
 * controller. Does not replace the caller's resolved binary common definition.
 * No reconstructed raw key/value table: count stays zero for binary records. */
int CODOL_DecodeGroundVehicleSettings(const unsigned char *,size_t,
    const codol_vehicle_native_t *,codol_vehicle_raw_t *);
#ifdef __cplusplus
}
#endif
#endif
