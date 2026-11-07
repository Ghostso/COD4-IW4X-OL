/* Staged server-thread RC physics ownership. Uses original T5 changed-clock
 * cadence explicitly; generic C1 client-world cadence is not an RC assumption. */
#ifdef CODOL_SERVER
#include "codol_vehicle_ground_runtime.h"
#include "codol_vehicle_ground_publish.h"
#include "codol_vehicle_sh1x_policy.h"
#include "codol_rc_lifecycle.h"
#include "codol_vehicle_controls.h"
#include "codol_vehicle_graph.h"
#include "codol_remote_vehicle.h"
#include "codol_weapon_input.h"
#include "codol_vehicle_wheel_anim.h"
#include "g_shared.h"
#include "g_scr_vehicle.h"
#include "dobj.h"
#include "cscr_stringlist.h"
#include "q_math.h"
#include "qcommon.h"
#include <cmath>
#include <cstdlib>
#include <cstring>
extern "C" scr_vehicle_s s_vehicles[8];
namespace {
struct ground_owner_t {
    codol_vehicle_frame_body_t physics;
    codol_vehicle_wheel_layout_t layout;
    codol_vehicle_raw_t *definition;
    codol_vehicle_acceleration_t graph;
    codol_vehicle_control_state_t controls;
    codol_vehicle_frame_wheel_t normalized[6];
    float friction;
    /* Diagnostics: next periodic report time, last seen driver (0 none, client+1). */
    int report_time,driver_seen,input_missing_reported;
};
ground_owner_t owners[8];
codol_vehicle_ode_world_t *world;
codol_vehicle_frame_settings_t worldSettings;
int previousTime;
bool clockValid;
bool sameSettings(const codol_vehicle_frame_settings_t &a,const codol_vehicle_frame_settings_t &b) {
    for(int i=0;i<3;++i)if(a.solver.gravity[i]!=b.solver.gravity[i])return false;
#define SAME(member) if(a.solver.member!=b.solver.member)return false
    SAME(erp);SAME(cfm);SAME(max_correcting_velocity);SAME(surface_layer);SAME(iterations);
    SAME(contact_erp);SAME(contact_cfm);SAME(friction_scale);SAME(bounce_velocity);
    SAME(contact_max_bounce_velocity);SAME(max_angular_velocity);SAME(linear_drag);SAME(angular_drag);
#undef SAME
    return a.position_iterations==b.position_iterations&&a.contents_mask==b.contents_mask&&
        a.minimum_step_milliseconds==b.minimum_step_milliseconds&&
        a.velocity_error_squared==b.velocity_error_squared&&a.position_error_squared==b.position_error_squared;
}
int slot(const gentity_t *e) {
    if(!e||!e->r.inuse||e->s.number<0||e->s.number>=ENTITYNUM_MAX_NORMAL||
       e!=&g_entities[e->s.number]||e->s.eType!=ET_VEHICLE||!e->scr_vehicle)return -1;
    uintptr_t p=(uintptr_t)e->scr_vehicle,b=(uintptr_t)s_vehicles;
    if(p<b||p-b>=sizeof(s_vehicles)||(p-b)%sizeof(scr_vehicle_s)||
       e->scr_vehicle->entNum!=e->s.number)return -1;
    return (int)((p-b)/sizeof(scr_vehicle_s));
}
bool owned(const ground_owner_t &o,const gentity_t *e) {
    return o.physics.body&&o.physics.entity==(unsigned)e->s.number&&o.physics.generation==(unsigned)e->useCount;
}
void release(ground_owner_t &o) {
    CODOL_DestroyVehicleODEBody(o.physics.body);std::free(o.definition);
    std::memset(&o,0,sizeof(o));
}
bool demand(ground_owner_t &o,int now,float seconds) {
    gentity_t *e=&g_entities[o.physics.entity];
    float origin[3],axis[3][3],velocity[3],angular[3],angles[3],mass;
    if(!CODOL_ReadVehicleODEBody(o.physics.body,o.physics.entity,o.physics.generation,
        origin,axis,velocity,angular)||!CODOL_VehicleODEMass(o.physics.body,&mass))return false;
    AxisToAngles(axis,angles);
    const float forwardSpeed=DotProduct(axis[0],velocity);
    gentity_t *driver=CODOL_RemoteVehicleSeatOccupant(e,0);
    codol_usercmd_t command={};int forward=0,right=0;float yaw=angles[1];bool haveCommand=false;
    const int driverNow=driver&&driver->client?driver->s.number+1:0;
    if(driverNow!=o.driver_seen) {
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: ent %u driver %s (client %d) view %d\n",o.physics.entity,
            driverNow?"linked":"released",driverNow?driverNow-1:o.driver_seen-1,o.definition->ground.third_person_driver);
        o.driver_seen=driverNow;o.input_missing_reported=0;
    }
    if(driverNow) {
        /* A driver whose last executed CoDOL command is not available (bot,
         * synthetic think, packet gap) drives with zero input; the physical
         * frame itself must not fail on input availability. */
        haveCommand=CODOL_ExecutedUsercmd((unsigned)driver->s.number,&command)!=0;
        if(!haveCommand&&!o.input_missing_reported) {
            o.input_missing_reported=1;
            Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: ent %u driver client %d has no executed usercmd; zero input\n",o.physics.entity,driverNow-1);
        }
        if(haveCommand) {
            forward=(command.direction&1)?127:(command.direction&2)?-127:0;
            right=(command.direction&4)?127:(command.direction&8)?-127:0;
        }
        /* C1 683b50 (thirdPersonDriver) steers from the driver's ps yaw
         * (ps+0x150). Our remote enter sets the controls-linked pm bit, under
         * which the C1 pmove port no longer runs PM_UpdateViewAngles, so
         * ps.viewangles froze at the tag_player yaw and steering went dead
         * (live 2CF09DD5). Derive the yaw exactly as PM_UpdateViewAngles
         * would: command angles plus delta_angles (SetClientViewAngle at
         * enter seeded delta_angles so this starts at the car's yaw). */
        yaw=driver->client->ps.viewangles[1];
        if(haveCommand)
            yaw=AngleNormalize360((float)SHORT2ANGLE(command.angles[1])+driver->client->ps.delta_angles[1]);
    }
    /* Test lever: sh1x_rcTestThrottle forces the throttle of a driven car
     * (bots drive with zero input) so wall hits can be reproduced without a
     * human driver. 0 (default) leaves the driver's input alone. */
    {
        static cvar_t *testThrottle;
        if(!testThrottle)testThrottle=Cvar_RegisterFloat("sh1x_rcTestThrottle",0.0f,-1.0f,1.0f,0,
            "Test only: throttle forced onto every driven RC car (-1 reverse .. 1 forward); 0 = driver input");
        if(driverNow&&testThrottle->value!=0)forward=(int)(127.0f*testThrottle->value);
    }
    if(CODOL_RCVehicleStunned(e)) {forward=right=0;command.buttons=0;yaw=angles[1];}
    codol_vehicle_controls_t controls;
    if(!CODOL_StepGroundVehicleControls(o.definition,forward,right,command.buttons,
        o.definition->ground.third_person_driver,yaw,angles[1],now,seconds,
        std::sqrt(DotProduct(velocity,velocity)),&o.controls,&controls))return false;
    /* T5 NitrousVehicleController::UpdateJump (OpenBLOPS
     * nitrous_vehicle_controller.cpp:1062): while the jump button is held and
     * at least two wheels were colliding in the previous update, add one
     * upward force and latch m_jump_button_pressed; release clears the latch.
     * C1's RC-XD binds it to the ADS button (usercmd 0x800, right mouse). The
     * BO1 rc_car vehicle file (m_jump_force) is not on disk, so the impulse is
     * a velocity sized for a ~32 in hop under C1 gravity 800 (sqrt(2*800*32)). */
    {
        const bool jumpHeld=haveCommand&&(command.buttons&0x800u)!=0;
        unsigned onGround=0;
        for(unsigned i=0;i<6;++i)if(o.physics.wheels[i].present&&o.physics.contacts[i].contacting)++onGround;
        o.physics.jump_velocity=0;
        if(jumpHeld) {
            if(onGround>=2&&!o.controls.jump_pressed) {
                o.physics.jump_velocity=226.0f;o.controls.jump_pressed=1;
                Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: jump ent %u client %d wheels %u\n",o.physics.entity,driverNow-1,onGround);
            }
        } else o.controls.jump_pressed=0;
    }
    codol_vehicle_wheel_layout_t steering;
    if(!CODOL_SteerVehicleWheels(&o.layout,controls.steering_degrees,controls.handbrake,
        controls.automatic_handbrake,&steering))return false;
    codol_vehicle_drive_input_t input={};
    input.forward_speed=forwardSpeed;input.forward_axis_z=axis[0][2];
    input.max_speed=o.definition->common.top_speed;input.mass_scale=mass;
    input.forward_target=controls.throttle*o.definition->common.top_speed;
    input.reverse_target=controls.reverse_throttle*o.definition->ground.reverse_speed_source*17.600000381469727f;
    if(controls.handbrake) {
        if(!CODOL_ApplyVehicleHandbrakeTarget(input.forward_target,forwardSpeed,&input.forward_target)||
           !CODOL_ApplyVehicleHandbrakeTarget(input.reverse_target,-forwardSpeed,&input.reverse_target))return false;
    }
    input.forward_target*=controls.forward_speed_scale;input.reverse_target*=controls.reverse_speed_scale;
    input.reverse_fraction=controls.reverse_throttle;input.boost_acceleration=controls.boost_acceleration;
    input.previous_friction=o.friction;
    codol_vehicle_drive_output_t drive;
    if(!CODOL_ResolveGroundVehicleDrive(&o.definition->ground,&o.graph,&input,&drive))return false;
    o.friction=drive.longitudinal_friction;
    o.physics.steering_degrees=controls.steering_degrees;
    for(unsigned i=0;i<6;++i) {
        codol_vehicle_frame_wheel_t &wheel=o.physics.wheels[i];
        wheel=o.normalized[i];
        const codol_vehicle_wheel_t &steer=steering.wheels[i];
        if(!wheel.present)continue;
        wheel.side[0]=-steer.forward[1];wheel.side[1]=steer.forward[0];wheel.side[2]=0;
        wheel.constraint.desired_speed=drive.motor_target/wheel.constraint.radius;
        // T5 NitrousVehicle::update applies the mass-scaled acceleration to
        // each powered wheel and floors an active factor at2. It does not
        // divide by wheel count; turning-radius normalization is separate.
        wheel.constraint.acceleration=(steer.flags&CODOL_WHEEL_POWERED)&&drive.motor_target!=0?
            std::fmax(2.0f,drive.motor_force):0;
        wheel.constraint.turning_speed_ratio=steer.path_speed_scale;
        wheel.constraint.turning_acceleration_ratio=steer.motor_speed_scale;
        // Preserve the T5 gravity-normalized coefficient. C1 steering's
        // dimensionless change is a ratio, not a replacement physical unit.
        if(o.layout.wheels[i].side_friction>0)
            wheel.constraint.side_friction*=steer.side_friction/o.layout.wheels[i].side_friction;
        // C1 drive's longitudinal_friction is zero under forward throttle;
        // it is NOT T5's tire traction ellipse coefficient. Keep the latter
        // from the physical constructor, otherwise every driven wheel would
        // have zero forward traction precisely when accelerating.
        // C1's handbrake word is also set by its automatic turn-brake
        // (683c50: speed<=250 and steer==0 or |steer|>=10), which in C1 only
        // rescales the powered wheels (SteerVehicleWheels 6x/10x) and the
        // motor target. Feeding that automatic state into T5's braking_state
        // removes the motor row from every braking-axle wheel, so a car that
        // is standing still (steer exactly 0) or turning (|steer|>=10) can
        // never accelerate. Only the explicit C1 handbrake button is a brake.
        const bool explicitBrake=controls.handbrake&&(command.buttons&0x100000u)!=0;
        const bool powerBrake=explicitBrake&&(steer.flags&CODOL_WHEEL_BRAKING);
        const bool regularBrake=controls.reverse_throttle>0&&!drive.reversing;
        const bool coast=drive.motor_target==0;
        wheel.constraint.braking_state=powerBrake||regularBrake||coast;
        wheel.constraint.braking=powerBrake?wheel.power_braking:
            regularBrake?wheel.regular_braking:coast?wheel.coasting_braking:0;
    }
    /* C1 spins the RC-XD's wheel meshes only through server animation
     * commands (codol_vehicle_wheel_anim.h); drive them from this body speed. */
    CODOL_VehicleWheelAnimFrame(e,forwardSpeed,now);
    if(now>=o.report_time) {
        o.report_time=now+1000;
        char wheels[6*24+1]={};size_t used=0;
        for(unsigned i=0;i<6;++i) {
            if(!o.physics.wheels[i].present)continue;
            const codol_vehicle_frame_contact_t &c=o.physics.contacts[i];
            used+=(size_t)Com_sprintf(wheels+used,sizeof(wheels)-used,"%s%c%.0f",i?" ":"",c.contacting?'C':'-',c.force[0]);
        }
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: ent %u t %d drv %d cmd %d fwd %d right %d btn 0x%x viewyaw %.0f caryaw %.0f | steer %.1f es68 %.1f lean %.1f/%.1f thr %.2f rev %.2f hb %d/%d motor %.0f/%.0f top %.0f scale %.2f mph %.1f/%.1f | org (%.0f %.0f %.0f) ang (%.0f %.0f %.0f) spd %.0f vz %.0f | wheels [%s] contacts %u | tr type %d/%d time %d base (%.0f %.0f %.0f) delta (%.0f %.0f %.0f) wheelanim %s\n",
            o.physics.entity,now,driverNow-1,haveCommand,forward,right,command.buttons,yaw,angles[1],controls.steering_degrees,e->s.lerp.u.vehicle.steerYaw,e->s.lerp.u.vehicle.bodyPitch,e->s.lerp.u.vehicle.bodyRoll,
            controls.throttle,controls.reverse_throttle,controls.handbrake,controls.automatic_handbrake,drive.motor_target,drive.motor_force,o.definition->common.top_speed,controls.forward_speed_scale,forwardSpeed/17.6f,drive.motor_target/17.6f,
            origin[0],origin[1],origin[2],angles[0],angles[1],angles[2],std::sqrt(DotProduct(velocity,velocity)),velocity[2],
            wheels,CODOL_VehicleODEFrameContacts(o.physics.body),
            e->s.lerp.pos.trType,e->s.lerp.apos.trType,e->s.lerp.pos.trTime,
            e->s.lerp.pos.trBase[0],e->s.lerp.pos.trBase[1],e->s.lerp.pos.trBase[2],
            e->s.lerp.pos.trDelta[0],e->s.lerp.pos.trDelta[1],e->s.lerp.pos.trDelta[2],
            CODOL_VehicleWheelAnimTree(e)?"bound":"none");
    }
    return true;
}
}
extern "C" int CODOL_GroundVehicleOwned(const gentity_t *e) {
    int index=slot(e);return index>=0&&owned(owners[index],e);
}
static int attach(gentity_t *e,const codol_vehicle_frame_wheel_t supplied[6],
    const codol_vehicle_t5_suspension_t *tuning,const codol_vehicle_sh1x_tuning_t *sh1x,float gravity,
    const codol_vehicle_frame_settings_t *settings) {
    int index=slot(e);if(index<0||((supplied!=NULL)+(tuning!=NULL)+(sh1x!=NULL))!=1||!settings||owners[index].physics.body)return 0;
    const codol_vehicle_raw_t *d=CODOL_NativeGroundVehicleDefinition(e->scr_vehicle->infoIdx);
    if(!d||!d->ground.remote_control||!d->common.physics_enabled)return 0;
    if(world&&!sameSettings(worldSettings,*settings))return 0;
    static const char *tags[6]={"tag_wheel_front_left","tag_wheel_front_right","tag_wheel_back_left",
        "tag_wheel_back_right","tag_wheel_middle_left","tag_wheel_middle_right"};
    float origins[6][3]={};unsigned present=0;
    for(unsigned i=0;i<6;++i) {
        unsigned tag=SL_GetString(tags[i],0);
        DObjAnimMat *matrix=G_DObjGetLocalTagMatrix(e,tag);
        if(matrix){std::memcpy(origins[i],matrix->trans,12);present|=1u<<i;}
        SL_RemoveRefToString(tag);
        if(supplied&&supplied[i].present!=((present&(1u<<i))!=0))return 0;
    }
    ground_owner_t next={};
    if(!CODOL_BuildVehicleWheelLayout(d,origins,present,&next.layout)||
       CODOL_LoadVehicleAccelerationGraph(d,&next.graph)!=1)return 0;
    next.definition=(codol_vehicle_raw_t *)std::malloc(sizeof(*d));if(!next.definition)return 0;
    *next.definition=*d;
    const bool createdWorld=!world;
    if(createdWorld){world=CODOL_CreateVehicleODEWorld();if(!world){std::free(next.definition);return 0;}}
    const auto discard=[&]() {
        release(next);
        if(createdWorld){CODOL_DestroyVehicleODEWorld(world);world=NULL;}
        return 0;
    };
    float axis[3][3],zero[3]={};AnglesToAxis(e->r.currentAngles,axis);
    next.physics.entity=(unsigned)e->s.number;next.physics.generation=(unsigned)e->useCount;
    const char *model=SL_ConvertToString(G_ModelName(e->model));
    next.physics.body=CODOL_CreateVehicleODEBody(world,d,model,next.physics.entity,next.physics.generation,
        e->r.currentOrigin,axis,zero,zero);
    if(!next.physics.body)return discard();
    codol_vehicle_frame_wheel_t converted[6];
    const codol_vehicle_frame_wheel_t *normalized=supplied;
    if(tuning||sh1x) {
        float mass,center[3];
        if(!CODOL_VehicleODEMass(next.physics.body,&mass)||
           !CODOL_VehicleODECenterOfMass(next.physics.body,center)||
           !(tuning?CODOL_BuildT5VehicleSuspension(tuning,&next.layout,mass,center,gravity,converted):
              CODOL_BuildSh1xVehicleSuspension(sh1x,d,&next.layout,mass,center,gravity,converted))) {
            return discard();
        }
        normalized=converted;
    }
    std::memcpy(next.physics.wheels,normalized,sizeof(next.physics.wheels));
    std::memcpy(next.normalized,normalized,sizeof(next.normalized));
    if(sh1x) {
        /* T5 NitrousVehicle installs its orientation constraint with the
         * per-mass parameters times m_body_mass (nitrous_vehicle.cpp:1892). */
        float mass=0;
        if(!CODOL_VehicleODEMass(next.physics.body,&mass)||
           !CODOL_ResolveSh1xVehicleOrientation(sh1x,d,mass,&next.physics.orientation))return discard();
    }
    if(createdWorld)worldSettings=*settings;
    {
        float mass=0,center[3]={};
        CODOL_VehicleODEMass(next.physics.body,&mass);CODOL_VehicleODECenterOfMass(next.physics.body,center);
        const codol_vehicle_frame_wheel_t &w0=normalized[0];
        Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: body ent %u model %s mass %.2f com (%.2f %.2f %.2f) origin (%.1f %.1f %.1f) angles (%.1f %.1f %.1f) gravity %.0f wheels 0x%x radius %.1f travel %.2f wheel0 center (%.1f %.1f %.1f) spring %.0f damping %.0f limit %.2f grip %.2f brake %.0f/%.0f/%.0f remote %d view %d\n",
            next.physics.entity,model,mass,center[0],center[1],center[2],e->r.currentOrigin[0],e->r.currentOrigin[1],e->r.currentOrigin[2],
            e->r.currentAngles[0],e->r.currentAngles[1],e->r.currentAngles[2],gravity,present,d->ground.wheel_radius,
            d->common.suspension_travel_known?d->common.suspension_travel:-1.0f,w0.center[0],w0.center[1],w0.center[2],
            w0.constraint.spring,w0.constraint.damping,w0.hard_limit,w0.constraint.side_friction,
            w0.regular_braking,w0.power_braking,w0.coasting_braking,d->ground.remote_control,d->ground.third_person_driver);
    }
    Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: orientation constraint (mass-scaled) resistance pitch %.0f roll %.0f yaw %.0f upright pitch %.0f roll %.0f | asset per-mass resistance pitch %.2f roll %.2f yaw %.2f upright pitch %.2f roll %.2f\n",
        next.physics.orientation.pitch_resistance,next.physics.orientation.roll_resistance,next.physics.orientation.yaw_resistance,
        next.physics.orientation.upright_pitch,next.physics.orientation.upright_roll,
        d->ground.pitch_resistance,d->ground.roll_resistance,d->ground.yaw_resistance,
        d->ground.upright_strength_pitch,d->ground.upright_strength_roll);
    Com_Printf(CON_CHANNEL_SERVER,"CoDOL rc: wheel tags FL (%.1f %.1f %.1f) FR (%.1f %.1f %.1f) BL (%.1f %.1f %.1f) BR (%.1f %.1f %.1f) wheelbase %.1f half_track %.1f stability %.1f/%.1f\n",
        origins[0][0],origins[0][1],origins[0][2],origins[1][0],origins[1][1],origins[1][2],origins[2][0],origins[2][1],origins[2][2],
        origins[3][0],origins[3][1],origins[3][2],next.layout.signed_wheelbase,next.layout.half_track,
        normalized[0].roll_stability,normalized[0].pitch_stability);
    next.report_time=level.time;
    owners[index]=next;clockValid=false;
    /* C1 67b3a4..67b3b8 publishes this same authored distance*1000 for
     * client suspension traces. Owned vehicles bypass retained Think. */
    if(d->common.suspension_travel_known)
        e->s.time2=(int)(d->common.suspension_travel*1000.0f);
    /* The wheels themselves are animated, not simulated, on the client. A
     * missing tree is logged there and leaves the car drivable. */
    CODOL_VehicleWheelAnimAttach(e,d->ground.wheel_radius);
    return 1;
}
extern "C" int CODOL_AttachGroundVehicle(gentity_t *e,const codol_vehicle_frame_wheel_t normalized[6],
    const codol_vehicle_frame_settings_t *settings) {
    return attach(e,normalized,NULL,NULL,0,settings);
}
extern "C" int CODOL_AttachT5GroundVehicle(gentity_t *e,const codol_vehicle_t5_suspension_t *tuning,
    float gravity,const codol_vehicle_frame_settings_t *settings) {
    return attach(e,NULL,tuning,NULL,gravity,settings);
}
extern "C" int CODOL_AttachSpawnedRCVehicle(gentity_t *e) {
    int index=slot(e);if(index<0)return 0;
    const codol_vehicle_raw_t *d=CODOL_NativeGroundVehicleDefinition(e->scr_vehicle->infoIdx);
    if(!d||std::strcmp(d->common.name,"rc_car_medium_mp"))return 0;
    codol_vehicle_sh1x_tuning_t tuning;codol_vehicle_frame_settings_t settings;
    if(!CODOL_ReadSh1xVehiclePolicy(&tuning,&settings))return -1;
    return attach(e,NULL,NULL,&tuning,-settings.solver.gravity[2],&settings)?1:-1;
}
static void releaseEmptyWorld() {
    for(unsigned i=0;i<8;++i)if(owners[i].physics.body)return;
    CODOL_DestroyVehicleODEWorld(world);world=NULL;clockValid=false;
    std::memset(&worldSettings,0,sizeof(worldSettings));
}
extern "C" void CODOL_GroundVehicleEntityFreed(const gentity_t *e) {
    if(!e)return;
    CODOL_RCEntityFreed(e);
    CODOL_VehicleWheelAnimEntityFreed(e);
    for(unsigned i=0;i<8;++i)if(owned(owners[i],e)){release(owners[i]);clockValid=false;}
    releaseEmptyWorld();
}
extern "C" void CODOL_ResetGroundVehicleRuntime(void) {
    CODOL_RCResetLifecycle();
    CODOL_VehicleWheelAnimReset();
    for(unsigned i=0;i<8;++i)release(owners[i]);
    CODOL_DestroyVehicleODEWorld(world);world=NULL;clockValid=false;
    std::memset(&worldSettings,0,sizeof(worldSettings));
}
extern "C" int CODOL_RunGroundVehicles(int now) {
    if(!world)return 1;
    ground_owner_t pending[8];codol_vehicle_frame_body_t bodies[8];unsigned indices[8],count=0;
    for(unsigned i=0;i<8;++i)if(owners[i].physics.body) {
        const unsigned entity=owners[i].physics.entity;
        if(entity>=ENTITYNUM_MAX_NORMAL||slot(&g_entities[entity])!=(int)i||!owned(owners[i],&g_entities[entity])) {
            release(owners[i]);clockValid=false;continue;
        }
        indices[count]=i;pending[count++]=owners[i];
    }
    if(!count){releaseEmptyWorld();return 1;}
    if(!clockValid||now<previousTime){previousTime=now;clockValid=true;return 1;}
    float seconds;if(!CODOL_VehicleFrameSeconds(previousTime,now,&seconds))return 0;
    if(seconds==0)return 1;
    for(unsigned i=0;i<count;++i){if(!demand(pending[i],now,seconds))return 0;bodies[i]=pending[i].physics;}
    if(!CODOL_RunGroundVehicleFrame(world,seconds,&worldSettings,bodies,count))return 0;
    codol_vehicle_frame_pose_t poses[8];
    for(unsigned i=0;i<count;++i) {
        pending[i].physics=bodies[i];owners[indices[i]]=pending[i];
        std::memcpy(poses[i].origin,bodies[i].origin,12);std::memcpy(poses[i].axis,bodies[i].axis,36);
    }
    previousTime=now;
    return CODOL_PublishGroundVehicleFrame(bodies,poses,count);
}
extern "C" void CODOL_RunGroundVehiclesFrame(void) {
    if(!CODOL_RunGroundVehicles(level.time))
        Com_Error(ERR_DROP,"Native ground vehicle physical frame failed; refusing stale pose publication");
}
#endif
