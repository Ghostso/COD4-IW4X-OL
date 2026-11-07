/* Native C1 wheel/contact layout. This is not six separate wheel bodies.
 * 65c270 seeds each model-local anchor, identity direction, axle side friction
 * and radius. 65c2e0 assigns steering/power/brake flags and computes axle
 * centers, signed wheelbase, half-track and equal powered-wheel share.
 * Physics and model-bone acquisition remain separate real consumers. */
#ifdef CODOL_SERVER
#include "codol_vehicle_wheels.h"
#include <math.h>
#include <string.h>
static int on_axle(unsigned wheel,codol_vehicle_axle_t axle)
{
    return axle==CODOL_AXLE_ALL ||
        (axle==CODOL_AXLE_FRONT && wheel<2) ||
        (axle==CODOL_AXLE_REAR && wheel>=2 && wheel<4);
}
int CODOL_BuildVehicleWheelLayout(const codol_vehicle_raw_t *d,
    const float origins[CODOL_VEHICLE_WHEELS][3],unsigned mask,
    codol_vehicle_wheel_layout_t *out)
{
    if(!d || !origins || !out || (mask&15)!=15 || (mask&~63u) ||
       !(d->decoded_domains&CODOL_GROUND_PHYSICS))return 0;
    const codol_vehicle_ground_settings_t *g=&d->ground;
    if((unsigned)g->steering_axle>2 || (unsigned)g->power_axle>2 ||
       (unsigned)g->braking_axle>2 || !isfinite(g->wheel_radius) ||
       g->wheel_radius<=0 || !isfinite(g->friction_side) ||
       g->friction_side<0 || !isfinite(g->friction_side_rear) ||
       g->friction_side_rear<0)return 0;
    codol_vehicle_wheel_layout_t next={};
    unsigned powered=0;
    for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i) {
        codol_vehicle_wheel_t *w=&next.wheels[i];
        /* C1 assigns axle flags even to absent optional slots. PRESENT is the
         * separate validity gate used by all wheel consumers. */
        if(i>=4 || on_axle(i,g->steering_axle))w->flags|=CODOL_WHEEL_STEERING;
        if(on_axle(i,g->power_axle))w->flags|=CODOL_WHEEL_POWERED;
        if(on_axle(i,g->braking_axle))w->flags|=CODOL_WHEEL_BRAKING;
        if(!(mask&(1u<<i)))continue;
        for(unsigned axis=0;axis<3;++axis) {
            if(!isfinite(origins[i][axis]))return 0;
            w->local_origin[axis]=origins[i][axis];
        }
        w->flags|=CODOL_WHEEL_PRESENT;
        w->forward[0]=1;
        w->path_speed_scale=1;
        w->motor_speed_scale=1;
        w->side_friction=i<2 ? g->friction_side : g->friction_side_rear;
        w->radius=g->wheel_radius;
        if(w->flags&CODOL_WHEEL_POWERED)++powered;
    }
    if(!powered)return 0;
    for(unsigned axis=0;axis<3;++axis) {
        next.front_center[axis]=(origins[0][axis]+origins[1][axis])*0.5f;
        next.rear_center[axis]=(origins[2][axis]+origins[3][axis])*0.5f;
        next.steering_center[axis]=g->steering_axle==CODOL_AXLE_REAR ?
            next.rear_center[axis] : next.front_center[axis];
        if(!isfinite(next.front_center[axis]) || !isfinite(next.rear_center[axis]))return 0;
    }
    next.signed_wheelbase=next.rear_center[0]-next.front_center[0];
    if(g->steering_axle==CODOL_AXLE_REAR)next.signed_wheelbase=-next.signed_wheelbase;
    if(g->steering_axle==CODOL_AXLE_ALL)next.signed_wheelbase*=0.5f;
    /* Match C1 65c417..65c484 model-orientation/axle separation requirement. */
    if(!isfinite(next.signed_wheelbase) ||
       (g->steering_axle==CODOL_AXLE_REAR ? next.signed_wheelbase<1 : next.signed_wheelbase> -1))return 0;
    next.half_track=((origins[2][1]+origins[0][1])-
                     (origins[3][1]+origins[1][1]))*0.25f;
    if(!isfinite(next.half_track))return 0;
    next.powered_share=1.0f/powered;
    *out=next;
    return 1;
}
int CODOL_SteerVehicleWheels(const codol_vehicle_wheel_layout_t *layout,
    float steering,int handbrake,int automatic_handbrake,
    codol_vehicle_wheel_layout_t *out)
{
    if(!layout || !out || !isfinite(steering) || fabsf(steering)>=90 ||
       (handbrake!=0 && handbrake!=1) ||
       (automatic_handbrake!=0 && automatic_handbrake!=1) ||
       (automatic_handbrake && !handbrake))return 0;
    codol_vehicle_wheel_layout_t next=*layout;
    for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i) {
        const codol_vehicle_wheel_t *w=&next.wheels[i];
        if(w->flags&~15u)return 0;
        if(!(w->flags&CODOL_WHEEL_PRESENT))continue;
        for(unsigned j=0;j<3;++j)
            if(!isfinite(w->local_origin[j]) || !isfinite(w->forward[j]))return 0;
        if(!isfinite(w->path_speed_scale) || !isfinite(w->motor_speed_scale))return 0;
    }
    /* 65ca31..65cb3d exits before brake-specific scale handling at near-zero
     * steering. Do not apply the turning-brake ratio unconditionally. */
    if(fabsf(steering)<=0.004999999888241291f) {
        for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i) {
            codol_vehicle_wheel_t *w=&next.wheels[i];
            if(!(w->flags&CODOL_WHEEL_PRESENT))continue;
            w->forward[0]=1;w->forward[1]=w->forward[2]=0;
            w->path_speed_scale=w->motor_speed_scale=1;
        }
        *out=next;return 1;
    }
    if(!isfinite(next.signed_wheelbase) || fabsf(next.signed_wheelbase)<1 ||
       !isfinite(next.steering_center[0]) || !isfinite(next.steering_center[1]))return 0;
    /* 65cb3e..65cbe5: instantaneous turn center and reference path length.
     * Signed longitudinal wheelbase chooses the steering axle. Lateral radius
     * uses its absolute magnitude and signed tan(steering). */
    const float lateral=(float)(fabs((double)next.signed_wheelbase)/
        tan((double)steering*0.017453292519943295));
    const float reference=(float)sqrt((double)lateral*lateral+
        (double)next.signed_wheelbase*next.signed_wheelbase);
    const float center_x=next.steering_center[0]+next.signed_wheelbase;
    const float center_y=next.steering_center[1]+lateral;
    if(!isfinite(reference) || reference<=0 ||
       !isfinite(center_x) || !isfinite(center_y))return 0;
    float ratio_sum=0;
    unsigned powered=0;
    for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i) {
        codol_vehicle_wheel_t *w=&next.wheels[i];
        if(!(w->flags&CODOL_WHEEL_PRESENT))continue;
        const float dx=center_x-w->local_origin[0],dy=center_y-w->local_origin[1];
        const float radius=(float)sqrt((double)dx*dx+(double)dy*dy);
        if(!isfinite(radius) || radius<=0)return 0;
        if(w->flags&CODOL_WHEEL_STEERING) {
            const float scale=(steering>0 ? 1.0f : -1.0f)/radius;
            w->forward[0]=dy*scale;w->forward[1]=-dx*scale;w->forward[2]=0;
        }
        /* 65cc8b..65cdef: engaged handbrake excludes the two front wheels
         * from the path-ratio accumulator. Other powered slots still count. */
        if((w->flags&CODOL_WHEEL_POWERED) && (!handbrake || i>=2)) {
            w->path_speed_scale=radius/reference;
            ratio_sum+=w->path_speed_scale;
            ++powered;
        }
    }
    /* Brake branches do not consume the ratio normalization. Avoid the C1
     * unused zero/zero intermediate if a front-drive body has its brake on. */
    if(!handbrake && (!powered || !isfinite(ratio_sum) || ratio_sum<=0))return 0;
    const float normalization=handbrake ? 0 : (float)powered/ratio_sum;
    for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i) {
        codol_vehicle_wheel_t *w=&next.wheels[i];
        if((w->flags&(CODOL_WHEEL_PRESENT|CODOL_WHEEL_POWERED))!=
                       (CODOL_WHEEL_PRESENT|CODOL_WHEEL_POWERED))continue;
        /* 65ccc7..65ceb1; C3E068=10 and C39DDC=6 are actual float constants. */
        w->motor_speed_scale=automatic_handbrake ? 10.0f :
            handbrake ? 6.0f : w->path_speed_scale*normalization;
        if(!isfinite(w->motor_speed_scale))return 0;
    }
    *out=next;
    return 1;
}
#endif
