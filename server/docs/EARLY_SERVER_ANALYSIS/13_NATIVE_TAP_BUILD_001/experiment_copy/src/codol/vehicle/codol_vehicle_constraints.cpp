/* SPDX-License-Identifier: AGPL-3.0-or-later */
#include "codol_vehicle_constraints.h"
#include <cmath>
#include <cstdint>

static bool finite_nonnegative(float value) { return std::isfinite(value) && value>=0; }
extern "C" int CODOL_BuildVehicleWheelConstraints(
    const codol_vehicle_wheel_constraint_input_t *in,codol_vehicle_wheel_constraints_t *out)
{
    if(!in || !out || !std::isfinite(in->seconds) || in->seconds<=0 ||
       !std::isfinite(in->position_error) || !std::isfinite(in->desired_speed) ||
       !std::isfinite(in->radius) || in->radius<=0 ||
       (in->braking_state!=0 && in->braking_state!=1))return 0;
    const float nonnegative[]={in->spring,in->damping,in->acceleration,in->braking,
        in->turning_speed_ratio,in->turning_acceleration_ratio,
        in->side_friction,in->forward_friction,in->friction_max};
    for(unsigned i=0;i<sizeof(nonnegative)/sizeof(nonnegative[0]);++i)
        if(!finite_nonnegative(nonnegative[i]))return 0;
    codol_vehicle_wheel_constraints_t value={};
    /* OpenBLOPS rbc_def_vehicle.cpp wheel calc_abs_and_setup: spring/damping
     * regularize a velocity constraint, rather than a free-standing force.
     * The row's effective mass denominator must also include this CFM. */
    const double spring_term=(double)in->spring*in->seconds*in->seconds;
    const double denominator=spring_term+(double)in->damping*in->seconds;
    if(!std::isfinite(denominator) || denominator<=0)return 0;
    value.suspension.cfm=(float)(1.0/denominator);
    value.suspension.rhs=(float)(-in->position_error*spring_term/denominator/in->seconds);
    value.suspension.minimum=-10000000.0f;
    value.suspension.maximum=0;
    value.side_ratio=in->side_friction;
    value.forward_ratio=in->forward_friction;
    value.friction_max=in->friction_max;
    const float active_factor=in->braking_state ? in->braking : in->acceleration;
    if(active_factor<0.0001f) {
        /* Free wheel: side row is directly limited by its suspension parent;
         * no forward motor constraint is allocated. */
        value.side_parent_ratio=1;
    } else {
        value.has_forward=1;
        value.side.minimum=-10000000.0f;
        value.side.maximum=10000000.0f;
        if(in->braking_state) {
            value.forward.maximum=in->braking*in->seconds;
            value.forward.minimum=-value.forward.maximum;
        } else {
            const float target=in->desired_speed*in->turning_speed_ratio;
            double compliance=(double)in->acceleration*in->turning_acceleration_ratio*
                in->seconds/((double)in->radius*in->radius);
            if(compliance<=0.000001)compliance=0.00001;
            value.forward.cfm=(float)(1.0/compliance);
            value.forward.rhs=in->radius*target;
            value.forward.minimum=target>0.0001f ? 0 : -10000000.0f;
            value.forward.maximum=target< -0.0001f ? 0 : 10000000.0f;
        }
    }
    const codol_vehicle_constraint_row_t *rows[]={&value.suspension,&value.side,&value.forward};
    for(unsigned i=0;i<3;++i)
        if(!std::isfinite(rows[i]->rhs) || !std::isfinite(rows[i]->cfm) ||
           !std::isfinite(rows[i]->minimum) || !std::isfinite(rows[i]->maximum))return 0;
    *out=value;
    return 1;
}
extern "C" int CODOL_ClampVehicleWheelFriction(const codol_vehicle_wheel_constraints_t *rows,
    float suspension,float side,float forward,float *side_out,float *forward_out,int *clamped)
{
    if(!rows || !side_out || !forward_out || !clamped ||
       !std::isfinite(suspension) || suspension>0 || !std::isfinite(side) ||
       !std::isfinite(forward) || !finite_nonnegative(rows->side_ratio) ||
       !finite_nonnegative(rows->forward_ratio) || !finite_nonnegative(rows->friction_max))return 0;
    if(!rows->has_forward) {
        if(!rows->side_parent_ratio)return 0;
        const double limit=-(double)rows->side_ratio*suspension;
        double result=side;
        if(result>limit)result=limit;
        if(result< -limit)result=-limit;
        *side_out=(float)result;*forward_out=0;*clamped=result!=side;
        return 1;
    }
    /* T5 pulse_sum_wheel::clamp_pulse_sum_pulse_chain: the traction ellipse
     * depends on the just-solved suspension impulse, including zero load. */
    double a=-(double)rows->side_ratio*suspension;
    double b=-(double)rows->forward_ratio*suspension;
    if(a>rows->friction_max)a=rows->friction_max;
    if(b>rows->friction_max)b=rows->friction_max;
    const double numerator=a*a*b*b;
    const double denominator=b*b*side*side+a*a*forward*forward;
    if(!std::isfinite(numerator) || !std::isfinite(denominator))return 0;
    double scale=1;
    const int limited=denominator>=numerator || numerator<0.00001;
    if(limited)scale=denominator<=0.00001 ? 0 : std::sqrt(numerator/denominator);
    *side_out=(float)(scale*side);*forward_out=(float)(scale*forward);*clamped=limited;
    return 1;
}
extern "C" int CODOL_VehicleFrameSeconds(int previous_time,int current_time,float *seconds)
{
    if(!seconds)return 0;
    int64_t elapsed=(int64_t)current_time-previous_time;
    if(!elapsed) { *seconds=0;return 1; }
    if(elapsed<1)elapsed=1;
    if(elapsed>100)elapsed=100;
    *seconds=(float)elapsed*0.001f;
    return 1;
}
