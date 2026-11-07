/* Temporary native sh1x RC backend design. T5 supplies the constraint solver;
 * this module deliberately does NOT reinterpret C1 spring/damping coefficients.
 * Static loads balance weight and pitch/roll moments at the actual body COM.
 * k=load*g/sag, c=2*zeta*sqrt(k*load), in engine mass/inch/second units. */
#ifdef CODOL_SERVER
#include "codol_vehicle_sh1x_policy.h"
#include "cvar.h"
#include <cmath>
#include <cstring>
namespace {
bool positive(float x){return std::isfinite(x)&&x>0;}
/* Minimum-norm nonnegative support weights, constrained to sum1 and zero
 * moments about COM. Removing negative supports is deterministic and bounded
 * by six anchors; unsupported COM geometry is rejected, never moved. */
bool support(const codol_vehicle_wheel_layout_t &l,const float com[3],double out[6]) {
    bool active[6]={};double a[6][3]={};
    for(unsigned i=0;i<6;++i)if(l.wheels[i].flags&CODOL_WHEEL_PRESENT) {
        active[i]=true;a[i][0]=1;
        for(unsigned j=0;j<2;++j) {
            a[i][j+1]=(double)l.wheels[i].local_origin[j]-com[j];
            if(!std::isfinite(a[i][j+1]))return false;
        }
    }
    for(unsigned pass=0;pass<6;++pass) {
        double m[3][4]={};m[0][3]=1;
        for(unsigned i=0;i<6;++i)if(active[i])
            for(unsigned r=0;r<3;++r)for(unsigned c=0;c<3;++c)m[r][c]+=a[i][r]*a[i][c];
        for(unsigned col=0;col<3;++col) {
            unsigned pivot=col;
            for(unsigned r=col+1;r<3;++r)if(std::fabs(m[r][col])>std::fabs(m[pivot][col]))pivot=r;
            if(!std::isfinite(m[pivot][col])||std::fabs(m[pivot][col])<1e-12)return false;
            for(unsigned c=col;c<4;++c){double v=m[col][c];m[col][c]=m[pivot][c];m[pivot][c]=v;}
            double divisor=m[col][col];for(unsigned c=col;c<4;++c)m[col][c]/=divisor;
            for(unsigned r=0;r<3;++r)if(r!=col) {
                double factor=m[r][col];for(unsigned c=col;c<4;++c)m[r][c]-=factor*m[col][c];
            }
        }
        int negative=-1;double smallest=0;
        for(unsigned i=0;i<6;++i) {
            out[i]=active[i]?a[i][0]*m[0][3]+a[i][1]*m[1][3]+a[i][2]*m[2][3]:0;
            if(!std::isfinite(out[i]))return false;
            if(out[i]<smallest){smallest=out[i];negative=(int)i;}
        }
        if(negative>=0){active[negative]=false;continue;}
        double total=0,moment[2]={};
        for(unsigned i=0;i<6;++i){total+=out[i];for(unsigned j=0;j<2;++j)moment[j]+=out[i]*a[i][j+1];}
        return std::fabs(total-1)<1e-5&&std::fabs(moment[0])<1e-4&&std::fabs(moment[1])<1e-4;
    }
    return false;
}
}
extern "C" int CODOL_ReadSh1xVehiclePolicy(codol_vehicle_sh1x_tuning_t *t,codol_vehicle_frame_settings_t *s) {
    if(!t||!s)return 0;
    codol_vehicle_sh1x_tuning_t n={};codol_vehicle_frame_settings_t w={};
#define VALUE(name,def,min,max,description) Cvar_RegisterFloat(name,def,min,max,0,description)->value
    n.sag_fraction=VALUE("sh1x_rcSag",0.5f,0.1f,0.9f,"sh1x policy: loaded sag as fraction of authored suspension travel; next RC spawn");
    n.damping_ratio=VALUE("sh1x_rcDamping",1.0f,0.1f,3.0f,"sh1x policy: suspension damping ratio; next RC spawn");
    n.grip=VALUE("sh1x_rcGrip",1.2f,0.05f,5.0f,"sh1x policy: wheel friction coefficient; next RC spawn");
    n.brake_g=VALUE("sh1x_rcBrakeG",1.0f,0.0f,5.0f,"sh1x policy: normal braking in gravities; next RC spawn");
    n.handbrake_g=VALUE("sh1x_rcHandbrakeG",2.0f,0.0f,10.0f,"sh1x policy: handbrake force in gravities; next RC spawn");
    n.coast_g=VALUE("sh1x_rcCoastG",0.08f,0.0f,2.0f,"sh1x policy: rolling resistance in gravities; next RC spawn");
    n.stability_inches=VALUE("sh1x_rcStability",10.0f,0.0f,60.0f,"T5 wheel roll/pitch stability lever in inches (NitrousVehicle default 10); next RC spawn");
    /* T5 orientation constraint strengths per unit body mass, multiplied by
     * the body mass when installed (nitrous_vehicle.cpp:1892-1897). T5's
     * NitrousVehicle defaults are 50 pitch/roll resistance, 0 yaw, 50 upright
     * (:95-97). -1 takes the RC-XD asset's own authored value (C1 VehicleDef
     * 0x10c..0x11c, see CODOL_ResolveSh1xVehicleOrientation). */
    n.orientation.pitch_resistance=VALUE("sh1x_rcPitchResistance",-1.0f,-1.0f,100000.0f,"T5 orientation constraint pitch angular resistance per unit mass; -1 = vehicle asset value; next RC spawn");
    n.orientation.roll_resistance=VALUE("sh1x_rcRollResistance",-1.0f,-1.0f,100000.0f,"T5 orientation constraint roll angular resistance per unit mass; -1 = vehicle asset value; next RC spawn");
    n.orientation.yaw_resistance=VALUE("sh1x_rcYawResistance",0.0f,-1.0f,100000.0f,"T5 orientation constraint yaw angular resistance per unit mass (NitrousVehicle default 0); -1 = vehicle asset value; next RC spawn");
    n.orientation.upright_pitch=VALUE("sh1x_rcUprightPitch",-1.0f,-1.0f,100000.0f,"T5 orientation constraint upright strength about the pitch axis per unit mass; -1 = vehicle asset value; next RC spawn");
    n.orientation.upright_roll=VALUE("sh1x_rcUprightRoll",-1.0f,-1.0f,100000.0f,"T5 orientation constraint upright strength about the roll axis per unit mass; -1 = vehicle asset value; next RC spawn");
    w.solver.gravity[2]=-VALUE("sh1x_rcGravity",800.0f,1.0f,4000.0f,"sh1x RC gravity in inches/sec squared; change after all RC bodies leave");
    w.solver.max_angular_velocity=VALUE("sh1x_rcAngularLimit",10.0f,0.1f,100.0f,"sh1x RC angular speed cap in radians/sec; T5 ordinary vehicle default10");
    w.solver.angular_drag=VALUE("sh1x_rcAngularDrag",0.1f,0.0f,10.0f,"sh1x RC angular drag per second; next empty physics world");
    w.solver.iterations=Cvar_RegisterInt("sh1x_rcSolverIterations",16,1,64,0,"sh1x RC velocity solver passes; next empty physics world")->integer;
    w.position_iterations=Cvar_RegisterInt("sh1x_rcPositionIterations",4,0,32,0,"sh1x RC position correction passes; next empty physics world")->integer;
#undef VALUE
    // Explicit backend settings, not a claim of recovered C1 RC cadence.
    w.solver.erp=0.8f;w.solver.cfm=0.0001f;w.solver.max_correcting_velocity=300;
    w.solver.surface_layer=0.3f;w.solver.contact_erp=0.8f;w.solver.contact_cfm=0.0001f;
    w.solver.friction_scale=0.5f;w.solver.bounce_velocity=20;w.solver.contact_max_bounce_velocity=100;
    w.contents_mask=0x280e491;w.velocity_error_squared=1e-6f;w.position_error_squared=1e-6f;
    *t=n;*s=w;return 1;
}
extern "C" int CODOL_ResolveSh1xVehicleOrientation(const codol_vehicle_sh1x_tuning_t *p,
    const codol_vehicle_raw_t *d,float mass,codol_vehicle_orientation_t *out) {
    if(!p||!d||!out||!positive(mass))return 0;
    const float policy[5]={p->orientation.pitch_resistance,p->orientation.roll_resistance,
        p->orientation.yaw_resistance,p->orientation.upright_pitch,p->orientation.upright_roll};
    const float authored[5]={d->ground.pitch_resistance,d->ground.roll_resistance,
        d->ground.yaw_resistance,d->ground.upright_strength_pitch,d->ground.upright_strength_roll};
    float result[5];
    for(unsigned i=0;i<5;++i) {
        const float value=policy[i]<0?authored[i]:policy[i];
        if(!std::isfinite(value)||value<0)return 0;
        result[i]=value*mass;
        if(!std::isfinite(result[i]))return 0;
    }
    out->pitch_resistance=result[0];out->roll_resistance=result[1];out->yaw_resistance=result[2];
    out->upright_pitch=result[3];out->upright_roll=result[4];
    return 1;
}
extern "C" int CODOL_BuildSh1xVehicleSuspension(const codol_vehicle_sh1x_tuning_t *p,
    const codol_vehicle_raw_t *d,const codol_vehicle_wheel_layout_t *l,float mass,const float com[3],
    float gravity,codol_vehicle_frame_wheel_t out[6]) {
    if(!p||!d||!l||!com||!out||!positive(mass)||!positive(gravity)||
       !positive(p->sag_fraction)||p->sag_fraction>=1||!positive(p->damping_ratio)||!positive(p->grip)||
       !std::isfinite(p->stability_inches)||p->stability_inches<0||
       !d->common.suspension_travel_known||!positive(d->common.suspension_travel)||
       !positive(d->ground.wheel_radius))return 0;
    if((double)d->common.suspension_travel*1000.0>2147483647.0)return 0;
    for(unsigned i=0;i<3;++i)if(!std::isfinite(com[i]))return 0;
    const float brake[]={p->brake_g,p->handbrake_g,p->coast_g};
    for(unsigned i=0;i<3;++i)if(!std::isfinite(brake[i])||brake[i]<0)return 0;
    for(unsigned i=0;i<4;++i)if(!(l->wheels[i].flags&CODOL_WHEEL_PRESENT))return 0;
    double weights[6];if(!support(*l,com,weights))return 0;
    const double travel=d->common.suspension_travel,sag=travel*p->sag_fraction;
    codol_vehicle_frame_wheel_t result[6]={};
    for(unsigned i=0;i<6;++i)if(l->wheels[i].flags&CODOL_WHEEL_PRESENT) {
        // A zero-load anchor cannot produce a valid spring row. Reject this
        // unsupported chassis instead of hiding geometry or inventing load.
        if(weights[i]<=0)return 0;
        codol_vehicle_frame_wheel_t &w=result[i];double load=weights[i]*mass;
        const double k=load*gravity/sag,c=2*p->damping_ratio*std::sqrt(k*load);
        std::memcpy(w.center,l->wheels[i].local_origin,12);
        w.center[2]-=(float)sag;w.suspension[2]=-1;w.side[1]=1;w.present=1;
        w.hard_limit=(float)travel;w.stop_margin=(float)std::fmin(3.4,travel*0.1);
        // T5 rigid_body_constraint_wheel::set(...,roll_stability,pitch_stability)
        // raises the side/forward impulse application point by that many
        // inches along -suspension (rbc_def_vehicle.cpp:552/636); NitrousVehicle
        // defaults it to 10.0 (nitrous_vehicle.cpp:94). C1's rollStability
        // (0.65) is a COM-height fraction, already consumed by the body
        // constructor, not a length; leaving these at 0 gave the car no
        // anti-roll at all, so it rolled over in fast turns (live 559438f6).
        w.roll_stability=w.pitch_stability=p->stability_inches;
        w.constraint.radius=d->ground.wheel_radius;w.constraint.spring=(float)k;w.constraint.damping=(float)c;
        w.constraint.forward_friction=w.constraint.side_friction=p->grip;
        w.constraint.friction_max=10000000;w.constraint.turning_speed_ratio=w.constraint.turning_acceleration_ratio=1;
        w.regular_braking=(float)(load*gravity*p->brake_g);w.power_braking=(float)(load*gravity*p->handbrake_g);
        w.coasting_braking=(float)(load*gravity*p->coast_g);
        if(!positive(w.constraint.spring)||!positive(w.constraint.damping)||!std::isfinite(w.center[2])||
           !std::isfinite(w.regular_braking)||!std::isfinite(w.power_braking)||!std::isfinite(w.coasting_braking))return 0;
    }
    std::memcpy(out,result,sizeof(result));return 1;
}
#endif
