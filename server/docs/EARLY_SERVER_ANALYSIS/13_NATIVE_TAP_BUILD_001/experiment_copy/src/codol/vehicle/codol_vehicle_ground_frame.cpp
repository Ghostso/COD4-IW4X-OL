/* T5 wheel collision prolog -> shared constraints -> epilog. This owns the
 * contact lifecycle; no synthetic ground planes or per-wheel velocity edits. */
#include "codol_vehicle_ground_frame.h"
#include <cmath>
#include <cstring>
namespace {
enum { MAX_FRAME_BODIES=8 };
struct frame_context_t {
    codol_vehicle_frame_body_t bodies[MAX_FRAME_BODIES];
    const codol_vehicle_frame_settings_t *settings;
    unsigned count,prepared;
};
bool finite3(const float *v) {return std::isfinite(v[0])&&std::isfinite(v[1])&&std::isfinite(v[2]);}
void rotate(const float axis[3][3],const float *local,float *world) {
    for(int i=0;i<3;++i)world[i]=axis[0][i]*local[0]+axis[1][i]*local[1]+axis[2][i]*local[2];
}
int prepare(codol_vehicle_ode_body_t *body,float seconds,void *opaque) {
    frame_context_t &f=*(frame_context_t *)opaque;
    unsigned slot=0;while(slot<f.count&&f.bodies[slot].body!=body)++slot;
    if(slot==f.count || (f.prepared&(1u<<slot)))return 0;
    f.prepared|=1u<<slot;
    codol_vehicle_frame_body_t &b=f.bodies[slot];
    for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i) {
        const codol_vehicle_frame_wheel_t &w=b.wheels[i];
        codol_vehicle_frame_contact_t &cache=b.contacts[i];
        if(!w.present){std::memset(&cache,0,sizeof(cache));continue;}
        float center[3],suspension[3],side[3],start[3],end[3];
        rotate(b.axis,w.center,center);rotate(b.axis,w.suspension,suspension);rotate(b.axis,w.side,side);
        for(int j=0;j<3;++j) {
            center[j]+=b.origin[j];
            // T5 rigid_body_constraint_wheel::get_wheel_collide_segment.
            start[j]=center[j]-w.constraint.radius*suspension[j];
            end[j]=center[j]+w.constraint.radius*suspension[j];
        }
        codol_vehicle_wheel_hit_t hit;
        if(!CODOL_VehicleODEWheelRay(body,start,end,f.settings->contents_mask,&hit))return 0;
        if(hit.fraction==1){std::memset(&cache,0,sizeof(cache));continue;}
        if(!cache.contacting || cache.hit_entity!=hit.entity || cache.hit_generation!=hit.generation ||
           cache.surface_flags!=hit.surface_flags)
            std::memset(cache.force,0,sizeof(cache.force));
        cache.contacting=1;cache.hit_entity=hit.entity;cache.hit_generation=hit.generation;
        cache.surface_flags=hit.surface_flags;
        std::memcpy(cache.point,hit.point,12);std::memcpy(cache.normal,hit.normal,12);
        codol_vehicle_wheel_constraint_input_t input=w.constraint;input.seconds=seconds;
        if(!CODOL_VehicleODEAddWheel(body,hit.body,center,suspension,side,hit.point,hit.normal,
             w.hard_limit,w.stop_margin,w.roll_stability,w.pitch_stability,&input,cache.force))return 0;
    }
    /* T5 NitrousVehicle::_update_orientation_constraint every update: the
     * constraint is always installed (m_active), and goes one-sided when no
     * wheel and no chassis point touches anything. Without it a wall hit's
     * chassis contact above the COM rolled the RC-XD onto its roof. */
    {
        const codol_vehicle_orientation_t &s=b.orientation;
        if(s.pitch_resistance>0||s.roll_resistance>0||s.yaw_resistance>0||s.upright_pitch>0||s.upright_roll>0) {
            int airborne=1;
            for(unsigned i=0;i<CODOL_VEHICLE_WHEELS;++i)if(b.wheels[i].present&&b.contacts[i].contacting)airborne=0;
            if(!CODOL_VehicleODEAddOrientation(body,&s,airborne))return 0;
        }
    }
    if(b.jump_velocity>0&&std::isfinite(b.jump_velocity)) {
        // T5 UpdateJump: body->add_force((0,0,m_jump_force)) once per press.
        // The impulse is expressed as a velocity so it is mass-independent:
        // the pulse pass integrates linear += seconds*force/mass.
        float mass;if(!CODOL_VehicleODEMass(body,&mass)||mass<=0)return 0;
        const float force[3]={0,0,mass*b.jump_velocity/seconds};
        if(!CODOL_VehicleODECentralForce(body,force))return 0;
        b.jump_velocity=0;
    }
    return 1;
}
}
extern "C" int CODOL_RunGroundVehicleFrame(codol_vehicle_ode_world_t *world,float seconds,
    const codol_vehicle_frame_settings_t *settings,codol_vehicle_frame_body_t *bodies,unsigned count) {
    if(!world||!settings||!bodies||!count||count>MAX_FRAME_BODIES||!settings->contents_mask||
       !std::isfinite(seconds)||seconds<=0)return 0;
    frame_context_t frame={};frame.settings=settings;frame.count=count;
    std::memcpy(frame.bodies,bodies,count*sizeof(*bodies));
    for(unsigned i=0;i<count;++i) {
        codol_vehicle_frame_body_t &b=frame.bodies[i];
        if(!b.body||!CODOL_VehicleODEOwnsBody(world,b.body))return 0;
        for(unsigned j=0;j<i;++j)
            if(frame.bodies[j].body==b.body||frame.bodies[j].entity==b.entity)return 0;
        if(!CODOL_ReadVehicleODEBody(b.body,b.entity,b.generation,b.origin,b.axis,b.velocity,b.angular_velocity))return 0;
        for(unsigned j=0;j<CODOL_VEHICLE_WHEELS;++j) {
            const codol_vehicle_frame_wheel_t &w=b.wheels[j];
            if(w.present!=0&&w.present!=1)return 0;
            if(w.present&&(!finite3(w.center)||!finite3(w.suspension)||!finite3(w.side)))return 0;
        }
    }
    if(!CODOL_StepVehiclePulseWorld(world,seconds,&settings->solver,settings->position_iterations,
          settings->velocity_error_squared,settings->position_error_squared,prepare,&frame))return 0;
    // The shared solver validates all output poses before its atomic commit.
    // No script callback or entity deletion is possible between commit/read.
    for(unsigned i=0;i<count;++i) {
        codol_vehicle_frame_body_t &b=frame.bodies[i];
        if(!CODOL_ReadVehicleODEBody(b.body,b.entity,b.generation,b.origin,b.axis,b.velocity,b.angular_velocity))return 0;
    }
    std::memcpy(bodies,frame.bodies,count*sizeof(*bodies));return 1;
}
