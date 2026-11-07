/* Native C1 four-wheel longitudinal constraint demands. No frame registration. */
#ifdef CODOL_SERVER
#include "codol_vehicle_drive.h"
#include <math.h>

int CODOL_EvaluateVehicleAcceleration(const codol_vehicle_acceleration_t *curve,
                                     float fraction,float *out)
{
    if(!curve || !out || !isfinite(fraction) || fraction<0 || fraction>1 ||
       curve->count<2 || curve->count>CODOL_VEHICLE_ACCEL_KNOTS ||
       !isfinite(curve->maximum_acceleration) || curve->maximum_acceleration<0)return 0;
    for(unsigned i=0;i<curve->count;++i) {
        const codol_vehicle_accel_knot_t &k=curve->knots[i];
        if(!isfinite(k.speed_fraction) || !isfinite(k.acceleration_fraction) ||
           k.acceleration_fraction<0 || (i && k.speed_fraction<=curve->knots[i-1].speed_fraction))return 0;
    }
    if(curve->knots[0].speed_fraction>fraction ||
       curve->knots[curve->count-1].speed_fraction<fraction)return 0;
    /* C1 searches from knot 1 for the first x >= requested fraction. */
    for(unsigned i=1;i<curve->count;++i) {
        const codol_vehicle_accel_knot_t &a=curve->knots[i-1],&b=curve->knots[i];
        if(b.speed_fraction>=fraction) {
            float f=(fraction-a.speed_fraction)/(b.speed_fraction-a.speed_fraction);
            float value=a.acceleration_fraction+f*(b.acceleration_fraction-a.acceleration_fraction);
            if(!isfinite(value))return 0;
            *out=value;return 1;
        }
    }
    return 0;
}

int CODOL_ApplyVehicleHandbrakeTarget(float target,float speed,float *out)
{
    if(!out || !isfinite(target) || !isfinite(speed) || target<0)return 0;
    float result=target;
    if(target>0) {
        float minimum=target*0.6000000238418579f;
        result=minimum<speed ? target-(speed-minimum)*0.5f : minimum;
    }
    if(!isfinite(result))return 0;
    *out=result;return 1;
}

int CODOL_ResolveGroundVehicleDrive(const codol_vehicle_ground_settings_t *g,
    const codol_vehicle_acceleration_t *curve,const codol_vehicle_drive_input_t *in,
    codol_vehicle_drive_output_t *out)
{
    if(!g || !curve || !in || !out)return 0;
    const float values[]={in->forward_speed,in->forward_axis_z,in->max_speed,in->mass_scale,
        in->forward_target,in->reverse_target,in->reverse_fraction,in->boost_acceleration,
        in->previous_friction,g->friction_braking,g->friction_coasting,g->friction_top_speed};
    for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);++i)if(!isfinite(values[i]))return 0;
    if(in->forward_axis_z< -1 || in->forward_axis_z>1 || in->max_speed<0 ||
       in->mass_scale<=0 || in->reverse_fraction<0 || in->reverse_fraction>1 ||
       in->boost_acceleration<0 || in->previous_friction<0 ||
       g->friction_braking<0 || g->friction_coasting<0 || g->friction_top_speed<0)return 0;
    codol_vehicle_drive_output_t result={};
    /* 65d132..65d15e: reverse is permitted below +1 inch/sec, preventing
     * reverse input from instantly reversing a forward-moving vehicle. */
    result.reversing=in->forward_speed<1 && in->reverse_fraction>0;
    result.motor_target=result.reversing ? -in->reverse_target : in->forward_target;
    float friction=g->friction_braking*in->reverse_fraction;
    if(in->forward_speed>in->max_speed && in->boost_acceleration==0) {
        /* 65d181..65d1c7: over-speed friction, no motor acceleration. */
        result.longitudinal_friction=fmaxf(friction,g->friction_top_speed);
    } else if(result.motor_target!=0) {
        float fraction=in->max_speed>=0.009999999776482582f ?
            fabsf(in->forward_speed)/in->max_speed : 0;
        fraction=fminf(1,fmaxf(0,fraction));
        float acceleration;
        if(!CODOL_EvaluateVehicleAcceleration(curve,fraction,&acceleration))return 0;
        acceleration*=curve->maximum_acceleration;
        acceleration=(float)((double)acceleration*17.600000381469727);
        /* 65d294..65d2cb: uphill compensation is directional. */
        if(result.reversing && in->forward_axis_z<0)acceleration*=1-2*in->forward_axis_z;
        else if(!result.reversing && in->forward_axis_z>0)acceleration*=1+2*in->forward_axis_z;
        acceleration*=in->boost_acceleration>0 ? in->boost_acceleration : 1;
        result.motor_force=acceleration*in->mass_scale;
        result.longitudinal_friction=result.reversing ? 0 : friction;
        if(result.motor_force==0 && result.longitudinal_friction==0)
            result.longitudinal_friction=g->friction_coasting;
        result.wake_body=1;
    } else {
        /* Ordinary wheel path. C1's alternative flag0x10 branch belongs to
         * another physical controller and is intentionally not selected here. */
        result.longitudinal_friction=fmaxf(friction,g->friction_coasting);
        result.wake_body=result.longitudinal_friction<in->previous_friction;
    }
    if(!isfinite(result.motor_force) || !isfinite(result.longitudinal_friction))return 0;
    *out=result;return 1;
}
#endif
