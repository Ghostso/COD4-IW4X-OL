/* C1 physical-world cadence and renderer pose ownership. Native clock uses
 * signed game milliseconds; a map restart must reset the world/clock together. */
#include "codol_vehicle_ground_frame.h"
#include "q_shared.h"
#include "q_math.h"
#include <cmath>
#include <cstring>
#include <climits>
#include <cstdint>
namespace {
bool readPose(const codol_vehicle_frame_body_t &b,codol_vehicle_frame_pose_t &p) {
    float velocity[3],angular[3];
    return CODOL_ReadVehicleODEBody(b.body,b.entity,b.generation,p.origin,p.axis,velocity,angular)!=0;
}
bool interpolate(const codol_vehicle_frame_pose_t &previous,const codol_vehicle_frame_body_t &next,
                 float fraction,codol_vehicle_frame_pose_t &out) {
    float previousAxis[3][3],nextAxis[3][3],a[4],b[4],q[4];
    std::memcpy(previousAxis,previous.axis,sizeof(previousAxis));
    std::memcpy(nextAxis,next.axis,sizeof(nextAxis));
    AxisToQuat(previousAxis,a);AxisToQuat(nextAxis,b);
    // C1 65b2ad..65b2d4: matrix->quat, hemisphere-correct linear blend,
    // normalization before consuming the resulting orientation (61ce10).
    QuatLerp(a,b,fraction,q);
    double length=0;for(int j=0;j<4;++j)length+=(double)q[j]*q[j];
    if(!std::isfinite(length)||length<=0)return false;
    const float inv=(float)(1/std::sqrt(length));for(int j=0;j<4;++j)q[j]*=inv;
    QuatToAxis(q,out.axis);
    for(int j=0;j<3;++j) {
        out.origin[j]=previous.origin[j]+fraction*(next.origin[j]-previous.origin[j]);
        if(!std::isfinite(out.origin[j]))return false;
        for(int k=0;k<3;++k)if(!std::isfinite(out.axis[j][k]))return false;
    }
    return true;
}
}
extern "C" int CODOL_ResetGroundVehicleClock(codol_vehicle_frame_clock_t *clock,int now,
    const codol_vehicle_frame_body_t *bodies,unsigned count) {
    if(!clock||!bodies||!count||count>8)return 0;
    codol_vehicle_frame_clock_t next={};next.count=count;next.previous_time=next.next_time=now;
    for(unsigned i=0;i<count;++i) {
        for(unsigned j=0;j<i;++j)if(bodies[i].entity==bodies[j].entity)return 0;
        if(!readPose(bodies[i],next.previous[i]))return 0;
        next.entity[i]=bodies[i].entity;next.generation[i]=bodies[i].generation;
    }
    next.initialized=1;*clock=next;return 1;
}
extern "C" int CODOL_AdvanceGroundVehicleWorld(codol_vehicle_ode_world_t *world,int now,
    const codol_vehicle_frame_settings_t *settings,codol_vehicle_frame_clock_t *clock,
    codol_vehicle_frame_body_t *bodies,unsigned count,codol_vehicle_frame_pose_t *presentation) {
    if(!world||!settings||!clock||!clock->initialized||!bodies||!presentation||
       !count||count>8||count!=clock->count||now<clock->previous_time||
       settings->minimum_step_milliseconds<=0)return 0;
    for(unsigned i=0;i<count;++i) {
        if(bodies[i].entity!=clock->entity[i]||bodies[i].generation!=clock->generation[i]||
           !CODOL_VehicleODEOwnsBody(world,bodies[i].body))return 0;
    }
    if(clock->next_time<now) {
        codol_vehicle_frame_pose_t previous[8];
        for(unsigned i=0;i<count;++i)if(!readPose(bodies[i],previous[i]))return 0;
        const int prior=clock->next_time;
        unsigned stepsLeft=2;
        while(clock->next_time<now) {
            if(!stepsLeft)return 0;
            const int64_t remaining=(int64_t)now-clock->next_time;
            int64_t milliseconds=remaining/stepsLeft;
            if(milliseconds<settings->minimum_step_milliseconds)
                milliseconds=settings->minimum_step_milliseconds;
            const int64_t complete=(int64_t)clock->next_time+milliseconds;
            if(complete>INT_MAX)return 0;
            if(!CODOL_RunGroundVehicleFrame(world,(float)milliseconds*0.001f,settings,bodies,count))return 0;
            // Commit only after this entire physical substep succeeded.
            if(stepsLeft==2) {
                clock->previous_time=prior;
                std::memcpy(clock->previous,previous,count*sizeof(*previous));
            }
            clock->next_time=(int)complete;--stepsLeft;
        }
    } else {
        // No physical step: retain current authoritative velocities/contacts,
        // but obtain the real next pose for this render interpolation.
        for(unsigned i=0;i<count;++i)
            if(!CODOL_ReadVehicleODEBody(bodies[i].body,bodies[i].entity,bodies[i].generation,
                 bodies[i].origin,bodies[i].axis,bodies[i].velocity,bodies[i].angular_velocity))return 0;
    }
    const int64_t interval=(int64_t)clock->next_time-clock->previous_time;
    const float fraction=interval>0?(float)((double)((int64_t)now-clock->previous_time)/interval):1;
    if(!std::isfinite(fraction)||fraction<0||fraction>1)return 0;
    codol_vehicle_frame_pose_t result[8];
    for(unsigned i=0;i<count;++i)if(!interpolate(clock->previous[i],bodies[i],fraction,result[i]))return 0;
    std::memcpy(presentation,result,count*sizeof(*result));return 1;
}
