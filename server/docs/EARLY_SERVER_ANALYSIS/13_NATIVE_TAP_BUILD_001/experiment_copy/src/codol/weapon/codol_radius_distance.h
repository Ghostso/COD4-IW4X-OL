/* Distance from an explosion to an entity's absolute collision box.
 * SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_RADIUS_DISTANCE_H
#define CODOL_RADIUS_DISTANCE_H

float CODOL_RadiusBoxDistance(const float point[3], const float absmin[3],
                              const float absmax[3]);

#endif
