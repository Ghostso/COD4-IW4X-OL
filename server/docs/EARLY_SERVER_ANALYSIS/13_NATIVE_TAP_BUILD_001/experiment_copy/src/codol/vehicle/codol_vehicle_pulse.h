/* SPDX-License-Identifier: AGPL-3.0-or-later */
#ifndef CODOL_VEHICLE_PULSE_H
#define CODOL_VEHICLE_PULSE_H
#include "codol_vehicle_constraints.h"
/* T5 pulse solver records, independent of retained/C1 object offsets.
 * Bodies are shared across all rows in an island. Base velocities are immutable
 * during a pass; delta velocities accumulate impulses, including contacts. */
struct codol_vehicle_pulse_body_t {
    float inverse_mass,world_inverse_inertia[3][3];
    float linear[3],angular[3],delta_linear[3],delta_angular[3];
};
struct codol_vehicle_pulse_row_t {
    codol_vehicle_pulse_body_t *first,*second;
    float direction[3],lever_first[3],lever_second[3];
    float application_first[3],application_second[3];
    float rhs,cfm,minimum,maximum,denominator,impulse;
};
/* All construction must finish before any warm start. Body1 application lever
 * differs from measurement lever by displacement (T5 roll/pitch stability). */
int CODOL_PrepareVehiclePulse(codol_vehicle_pulse_row_t *,
    codol_vehicle_pulse_body_t *,codol_vehicle_pulse_body_t *,
    const float direction[3],const float lever_first[3],const float lever_second[3],
    const float displacement[3],const codol_vehicle_constraint_row_t *);
int CODOL_WarmVehiclePulse(codol_vehicle_pulse_row_t *,float cached_force,float seconds);
int CODOL_RelaxVehiclePulse(codol_vehicle_pulse_row_t *,float *error_squared);
/* One wheel per solver iteration, interleaved with real contact rows. */
int CODOL_RelaxVehicleWheel(codol_vehicle_pulse_row_t rows[3],
    const codol_vehicle_wheel_constraints_t *,float *error_squared);
/* T5 wheel setup regularizes suspension and motor effective mass after the
 * generic pulse has computed its physical Jacobian. The three supplied axes
 * are suspension-normal, side and forward; pitch displacement may differ. */
int CODOL_PrepareVehicleWheel(codol_vehicle_pulse_row_t rows[3],
    codol_vehicle_pulse_body_t *,codol_vehicle_pulse_body_t *,
    const float axes[3][3],const float lever_first[3],const float lever_second[3],
    const float roll_displacement[3],const float pitch_displacement[3],
    const codol_vehicle_wheel_constraints_t *);
int CODOL_WarmVehicleWheel(codol_vehicle_pulse_row_t rows[3],
    const codol_vehicle_wheel_constraints_t *,const float cached_force[3],float seconds);
struct codol_vehicle_pulse_contact_t {
    codol_vehicle_pulse_row_t rows[3];
    float cross_normal_side,cross_normal_forward,inverse_side,inverse_cross,inverse_forward;
    float friction,position_bias;
};
/* Normal points INTO the first body and uses nonpositive impulses, matching
 * T5. Retained dCollide outward normals must be negated by its adapter.
 * Positive penetration uses T5's delayed (second-pass) negative correction. */
int CODOL_PrepareVehicleContact(codol_vehicle_pulse_contact_t *,
    codol_vehicle_pulse_body_t *,codol_vehicle_pulse_body_t *,
    const float axes[3][3],const float lever_first[3],const float lever_second[3],
    float penetration,float friction,float bounce,float max_bounce_speed,
    float minimum_bounce_speed_squared,float seconds);
int CODOL_WarmVehicleContact(codol_vehicle_pulse_contact_t *,const float cached_force[3],float seconds);
int CODOL_RelaxVehicleContact(codol_vehicle_pulse_contact_t *,float *error_squared);
#endif
