#ifndef CODOL_VEHICLE_ODE_H
#define CODOL_VEHICLE_ODE_H
#include "codol_vehicle_raw.h"
#include "codol_vehicle_constraints.h"
#ifdef __cplusplus
extern "C" {
#endif
struct codol_vehicle_ode_world_s;
struct codol_vehicle_ode_body_s;
typedef struct codol_vehicle_ode_world_s codol_vehicle_ode_world_t;
typedef struct codol_vehicle_ode_body_s codol_vehicle_ode_body_t;
/* Real retained ODE backend, with caller-owned world memory. No retained
 * PhysWorld index is borrowed; C1 world3 is not a valid retained array index.
 * Single server-thread ownership; engine Phys_Init is idempotent. */
codol_vehicle_ode_world_t *CODOL_CreateVehicleODEWorld(void);
void CODOL_DestroyVehicleODEWorld(codol_vehicle_ode_world_t *);
/* Strict shipped preset/model geometry, owned until destruction. No model
 * bounds fallback. Model origin/axis use native game coordinates; velocity is
 * world inches/sec and angular velocity is world radians/sec. */
codol_vehicle_ode_body_t *CODOL_CreateVehicleODEBody(codol_vehicle_ode_world_t *,
    const codol_vehicle_raw_t *,const char *model_name,unsigned entity,unsigned generation,
    const float model_origin[3],const float model_axis[3][3],
    const float linear_velocity[3],const float angular_velocity[3]);
void CODOL_DestroyVehicleODEBody(codol_vehicle_ode_body_t *);
int CODOL_VehicleODEOwnsBody(const codol_vehicle_ode_world_t *,const codol_vehicle_ode_body_t *);
int CODOL_VehicleODEMass(const codol_vehicle_ode_body_t *,float *mass);
/* Diagnostics: chassis contact points generated for this body in the last pulse pass. */
unsigned CODOL_VehicleODEFrameContacts(const codol_vehicle_ode_body_t *);
/* Returns the actual installed physical COM, including the C1 roll-stability
 * adjustment. Constructor normalization must not re-read an unadjusted model. */
int CODOL_VehicleODECenterOfMass(const codol_vehicle_ode_body_t *,float center[3]);
/* Caller must validate entity/generation before publishing the returned state.
 * The renderer origin is recovered from center-of-mass transform, not directly
 * equated with ODE body's center. Output unchanged on invalid body/state. */
int CODOL_ReadVehicleODEBody(const codol_vehicle_ode_body_t *,unsigned entity,unsigned generation,
    float model_origin[3],float model_axis[3][3],float velocity[3],float angular_velocity[3]);
/* One caller-scheduled physical substep. These are explicit native solver
 * settings, not guessed C1 defaults. The owner must supply the actual C1
 * wheel/constraint force producer; a missing producer never advances the body. */
typedef struct {
    float gravity[3],erp,cfm,max_correcting_velocity,surface_layer;
    int iterations;
    float contact_erp,contact_cfm,friction_scale,bounce_velocity;
    float contact_max_bounce_velocity;
    float max_angular_velocity;
    float linear_drag,angular_drag;
} codol_vehicle_ode_step_t;
typedef int (*codol_vehicle_ode_force_fn)(codol_vehicle_ode_body_t *,float seconds,void *);
int CODOL_StepVehicleODEWorld(codol_vehicle_ode_world_t *,float seconds,
    const codol_vehicle_ode_step_t *,codol_vehicle_ode_force_fn,void *);
/* Forces act on the real body at the real world-space contact point. */
int CODOL_VehicleODEForceAtPoint(codol_vehicle_ode_body_t *,const float force[3],const float point[3]);
/* Pure force through the centre of mass (T5 rigid_body::add_force), no torque. */
int CODOL_VehicleODECentralForce(codol_vehicle_ode_body_t *,const float force[3]);
/* Shared T5 pulse pass: chassis contacts and wheel rows solve against the
 * SAME body scratch, then commit once. Never follow it with the ODE world
 * step above. This is a replacement backend, not a pre-step force hack.
 * The callback resolves current contact geometry/control and adds wheel rows.
 * Position iterations/error thresholds are explicit caller-owned settings. */
int CODOL_StepVehiclePulseWorld(codol_vehicle_ode_world_t *,float seconds,
    const codol_vehicle_ode_step_t *,int position_iterations,float velocity_error_squared,
    float position_error_squared,codol_vehicle_ode_force_fn,void *);
/* Only valid in a pulse prepare callback. Contact point/normal are actual
 * current wheel hit, normal outward from the hit surface. NULL hitBody means
 * the static map. Center and suspension/side axes are world-space. */
int CODOL_VehicleODEAddWheel(codol_vehicle_ode_body_t *,codol_vehicle_ode_body_t *hitBody,
    const float wheel_center[3],const float suspension_direction[3],const float side_axis[3],
    const float hit_point[3],const float hit_normal[3],float hard_limit,float stop_margin,
    float roll_stability,float pitch_stability,const codol_vehicle_wheel_constraint_input_t *,
    float cached_force[4]);
/* T5 rigid_body_constraint_custom_orientation strengths, already scaled by
 * body mass (NitrousVehicle m_parameter * m_body_mass). T5 has one pitch/roll
 * resistance and one upright strength; C1's vehicle asset (and IW4's
 * VehiclePhysDef it descends from) authors pitch and roll separately
 * (rollResistance/pitchResistance/uprightStrengthPitch/uprightStrengthRoll),
 * so the rows take them separately. Zero disables a row. */
typedef struct {
    float pitch_resistance,roll_resistance,yaw_resistance;
    float upright_pitch,upright_roll;
} codol_vehicle_orientation_t;
/* Only valid in a pulse prepare callback. The T5 orientation constraint
 * (rbc_def_custom.cpp:39) between the body and the static environment, as
 * NitrousVehicle installs it for every nitrous vehicle
 * (nitrous_vehicle.cpp:1888-1897): pitch/roll/yaw angular-velocity resistance
 * plus the upright restoring rows. wheels_airborne: no wheel touched ground
 * this pass; with no chassis contact either, T5 sets
 * m_no_orientation_correction and the upright rows only resist further tilt. */
int CODOL_VehicleODEAddOrientation(codol_vehicle_ode_body_t *,const codol_vehicle_orientation_t *,
    int wheels_airborne);
typedef struct {
    float fraction,point[3],normal[3];
    codol_vehicle_ode_body_t *body; /* NULL: static map/model */
    unsigned entity,generation;
    int surface_flags,starts_inside;
} codol_vehicle_wheel_hit_t;
/* Actual suspension-segment query, during prepare. Tests native clipmap and
 * static-model triangles plus every other owned model's physical primitives.
 * fraction1 means no surface hit. No gameplay entity bounds stand-ins. */
int CODOL_VehicleODEWheelRay(codol_vehicle_ode_body_t *ignored,const float start[3],
    const float end[3],int contents_mask,codol_vehicle_wheel_hit_t *);
#ifdef __cplusplus
}
#endif
#endif
