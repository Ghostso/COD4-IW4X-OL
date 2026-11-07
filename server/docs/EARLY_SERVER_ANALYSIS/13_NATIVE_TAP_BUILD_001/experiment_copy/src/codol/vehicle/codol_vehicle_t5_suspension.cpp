/* OpenBLOPS NitrousVehicle initialization, nitrous_vehicle.cpp760..851.
 * C1 physical mass/geometry are acceptable inputs; parameter dimensions are
 * explicitly T5 and must not be inferred from matching C1 field names. */
#include "codol_vehicle_t5_suspension.h"
#include <cmath>
#include <cstring>
#include <cfloat>
extern "C" int CODOL_BuildT5VehicleSuspension(const codol_vehicle_t5_suspension_t *p,
    const codol_vehicle_wheel_layout_t *layout,float mass,const float com[3],float gravity,
    codol_vehicle_frame_wheel_t out[6]) {
    if(!p||!layout||!com||!out||!std::isfinite(mass)||mass<=0||!std::isfinite(gravity)||gravity<=0)return 0;
    // Both axle pairs are required by the real four-wheel chassis constructor;
    // absent zero-initialized anchors must not become a fictitious wheelbase.
    for(unsigned i=0;i<4;++i)
        if(!(layout->wheels[i].flags&CODOL_WHEEL_PRESENT))return 0;
    const float nonnegative[]={p->spring_k,p->damping_k,p->suspension_adjustment,p->hard_limit,
        p->forward_friction,p->side_friction,p->side_friction_max,p->roll_stability,
        p->braking,p->power_braking,p->coasting};
    for(unsigned i=0;i<sizeof(nonnegative)/sizeof(*nonnegative);++i)
        if(!std::isfinite(nonnegative[i])||nonnegative[i]<0)return 0;
    if(!std::isfinite(p->wheel_radius)||p->wheel_radius<=0||p->spring_k+p->damping_k<=0)return 0;
    double lengthSquared=0;
    // T5 wheel_to_wheel_length: front/rear reference-tag separation.
    for(int axis=0;axis<3;++axis) {
        if(!std::isfinite(com[axis]))return 0;
        const double distance=(double)layout->wheels[0].local_origin[axis]-layout->wheels[2].local_origin[axis];
        lengthSquared+=distance*distance;
    }
    const double wheelbase=std::sqrt(lengthSquared);
    if(!std::isfinite(wheelbase)||wheelbase<=0)return 0;
    codol_vehicle_frame_wheel_t result[6]={};
    for(unsigned i=0;i<6;++i) {
        if(!(layout->wheels[i].flags&CODOL_WHEEL_PRESENT))continue;
        codol_vehicle_frame_wheel_t &w=result[i];
        for(int j=0;j<3;++j) {
            w.center[j]=layout->wheels[i].local_origin[j];
            if(!std::isfinite(w.center[j]))return 0;
        }
        // The frame API uses model-local coordinates. COM is subtracted by
        // the body transform/constraint builder, exactly once, not here too.
        w.center[2]+=p->wheel_radius-p->suspension_adjustment;
        const double fraction=std::fabs((double)w.center[0]-com[0])/wheelbase;
        const double factor=(1-std::fmin(1.0,std::fmax(0.0,fraction)))*2;
        w.constraint.spring=(float)(p->spring_k*gravity*factor*mass);
        w.constraint.damping=(float)(p->damping_k*gravity*factor*mass);
        w.constraint.radius=p->wheel_radius;
        w.constraint.forward_friction=p->forward_friction/gravity;
        w.constraint.side_friction=p->side_friction/gravity;
        w.constraint.friction_max=p->side_friction_max==0?FLT_MAX:p->side_friction_max;
        w.constraint.turning_speed_ratio=w.constraint.turning_acceleration_ratio=1;
        w.suspension[2]=-1;w.side[1]=1;
        w.hard_limit=p->hard_limit;w.stop_margin=3.4f;
        w.roll_stability=w.pitch_stability=p->roll_stability;
        w.regular_braking=p->braking;w.power_braking=p->power_braking;w.coasting_braking=p->coasting;
        w.present=1;
        if(!std::isfinite(w.center[2])||!std::isfinite(w.constraint.spring)||!std::isfinite(w.constraint.damping)||
           w.constraint.spring+w.constraint.damping<=0||!std::isfinite(w.constraint.forward_friction)||
           !std::isfinite(w.constraint.side_friction))return 0;
    }
    std::memcpy(out,result,sizeof(result));return 1;
}
