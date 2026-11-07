/* Native C1 RC control demand producer.
 * 683b50: direct steering -signed right/127 when VehicleDef2cc==0.
 * 683a30: signed-square steering, outward interpolation only (618c10).
 * 683cc0: boost deadline, duration/recharge and multipliers; button400.
 * 683f0e: handbrake button100000 when enabled. No missile state involved.
 * This producer is not registered until the physical vehicle consumer exists. */
#ifdef CODOL_SERVER
#include "codol_vehicle_controls.h"
#include <math.h>
#include <limits.h>

int CODOL_StepGroundVehicleControls(const codol_vehicle_raw_t *d,
    int forward,int right,uint32_t buttons,int view_angle_steering,
    float driver_yaw,float vehicle_yaw,int now,float dt,float speed,
    codol_vehicle_control_state_t *state,codol_vehicle_controls_t *out)
{
    if(!d || !state || !out || forward< -127 || forward>127 ||
       right< -127 || right>127 || now<0 || !isfinite(dt) || dt<=0 || dt>0.2f ||
       !isfinite(speed) || !isfinite(state->steering_degrees) ||
       (view_angle_steering!=0 && view_angle_steering!=1) ||
       !isfinite(driver_yaw) || !isfinite(vehicle_yaw))
        return 0;
    const codol_vehicle_ground_settings_t *g=&d->ground;
    if(!isfinite(g->max_steering_angle) || g->max_steering_angle<0 ||
       !isfinite(g->steering_lerp) || g->steering_lerp<0 ||
       !isfinite(g->min_steering_scale) || g->min_steering_scale<0 ||
       !isfinite(g->min_steering_speed) || g->min_steering_speed<0 ||
       !isfinite(g->boost_speed_multiplier) || g->boost_speed_multiplier<=0 ||
       !isfinite(g->boost_accel_multiplier) || g->boost_accel_multiplier<0 ||
       !isfinite(g->boost_duration) || g->boost_duration<0 ||
       !isfinite(g->boost_recharge_time) || g->boost_recharge_time<0)return 0;
    codol_vehicle_control_state_t next=*state;
    codol_vehicle_controls_t result={};
    float steer=-(float)right/127.0f;
    if(view_angle_steering) {
        float driver=fmodf(driver_yaw,360.0f),vehicle=fmodf(vehicle_yaw,360.0f);
        if(driver<0)driver+=360;
        if(vehicle<0)vehicle+=360;
        steer=driver-vehicle;
        if(steer>180)steer-=360;
        if(steer< -180)steer+=360;
        if(forward<0)steer=-steer;
    }
    float target=steer*fabsf(steer)*g->max_steering_angle;
    float current=state->steering_degrees;
    if(view_angle_steering) {
        target=steer;
        if(target>g->max_steering_angle)target=g->max_steering_angle;
        if(target< -g->max_steering_angle)target=-g->max_steering_angle;
    } else if(g->steering_lerp && ((target<0 && current<=0 && current>target) ||
                           (target>0 && current>=0 && current<target))) {
        float delta=target-current,step=delta*g->steering_lerp*dt;
        if(fabsf(delta)>0.001f && fabsf(step)<fabsf(delta))target=current+step;
    }
    /* C1 683fa9 scales the stored steering after interpolation each frame. */
    if(g->min_steering_scale!=1 && g->min_steering_speed>0) {
        float fraction=speed/g->min_steering_speed;
        if(fraction<0)fraction=0;
        if(fraction>1)fraction=1;
        target*=1-fraction+fraction*g->min_steering_scale;
    }
    next.steering_degrees=result.steering_degrees=target;
    result.throttle=forward>0 ? (float)forward/127.0f : 0;
    result.reverse_throttle=forward<0 ? (float)-forward/127.0f : 0;
    /* 683ef0 stores the automatic turn-brake result in vehicle+22d; 683f0e
     * then ORs the explicit C1 button into +22c. 65d43d..65d471 publishes
     * these independently as physical instance flags20/40. */
    /* C1's equality path 683c7f -> 683c98 -> 683cb4 also accepts exact zero;
     * do not simplify the source predicate to fabs(steer)>=10. */
    result.automatic_handbrake=g->handbrake_enabled &&
        (speed>=0 && speed<=250 && (steer==0 || steer>=10 || steer<= -10));
    result.handbrake=g->handbrake_enabled &&
        ((buttons&0x100000)!=0 || result.automatic_handbrake);
    result.forward_speed_scale=result.reverse_speed_scale=1;
    if(g->boost_enabled) {
        double total=((double)g->boost_duration+g->boost_recharge_time)*1000.0;
        double recharge=(double)g->boost_recharge_time*1000.0;
        if(total>INT_MAX || recharge>INT_MAX)return 0;
        result.forward_speed_scale=result.reverse_speed_scale=1/g->boost_speed_multiplier;
        if((int64_t)now>=next.boost_ready_time && forward>0 && (buttons&0x400))
            next.boost_ready_time=(int64_t)now+(int)total;
        result.boost_ready=(int64_t)now>=next.boost_ready_time;
        result.boost_active=(int64_t)now<next.boost_ready_time-(int)recharge;
        if(result.boost_active) {
            result.forward_speed_scale*=g->boost_speed_multiplier;
            result.boost_acceleration=g->boost_accel_multiplier;
        }
    }
    if(result.handbrake && result.boost_acceleration!=0)result.boost_acceleration*=2;
    if(!isfinite(target) || !isfinite(result.forward_speed_scale) ||
       !isfinite(result.reverse_speed_scale))return 0;
    *state=next;*out=result;return 1;
}
#endif
