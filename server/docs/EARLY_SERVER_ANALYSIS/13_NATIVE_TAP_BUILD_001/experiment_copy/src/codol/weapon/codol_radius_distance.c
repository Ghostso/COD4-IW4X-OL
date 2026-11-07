/* C1 G_RadiusDamage 0x522aca..0x522bb3 measures every entity from the nearest
 * point of its absolute box. The retained assembly uses this same rule under
 * CODOL_SERVER; custom script radius damage must use it too.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_radius_distance.h"
#include <math.h>

float CODOL_RadiusBoxDistance(const float point[3], const float absmin[3],
                              const float absmax[3])
{
    float delta[3], distance_sq;
    unsigned i;
    for(i=0;i<3;++i) {
        if(absmin[i]>point[i]) delta[i]=absmin[i]-point[i];
        else if(point[i]>absmax[i]) delta[i]=point[i]-absmax[i];
        else delta[i]=0.0f;
    }
    distance_sq=delta[0]*delta[0]+delta[1]*delta[1]+delta[2]*delta[2];
    return sqrtf(distance_sq);
}
