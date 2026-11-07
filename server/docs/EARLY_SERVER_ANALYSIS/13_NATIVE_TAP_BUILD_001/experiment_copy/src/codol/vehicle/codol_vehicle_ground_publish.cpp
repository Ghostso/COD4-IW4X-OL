/* Native physical vehicle -> entity snapshot and script physical state. */
#ifdef CODOL_SERVER
#include "codol_vehicle_ground_publish.h"
#include "g_shared.h"
#include "g_scr_vehicle.h"
#include "server.h"
#include "q_math.h"
#include <cmath>
#include <cstring>
extern "C" scr_vehicle_s s_vehicles[8];
extern "C" int CODOL_PublishGroundVehicleFrame(const codol_vehicle_frame_body_t *bodies,
    const codol_vehicle_frame_pose_t *presentation,unsigned count) {
    if(!bodies||!presentation||!count||count>8)return 0;
    gentity_t *entities[8];float angles[8][3],bodyVelocity[8][3],speed[8];
    for(unsigned i=0;i<count;++i) {
        const codol_vehicle_frame_body_t &b=bodies[i];
        if(b.entity>=ENTITYNUM_MAX_NORMAL)return 0;
        gentity_t *e=&g_entities[b.entity];
        if(!e->r.inuse||(unsigned)e->useCount!=b.generation||e->s.eType!=ET_VEHICLE||!e->scr_vehicle)return 0;
        const uintptr_t address=(uintptr_t)e->scr_vehicle,base=(uintptr_t)s_vehicles;
        if(address<base||address-base>=sizeof(s_vehicles)||(address-base)%sizeof(scr_vehicle_s)||
           e->scr_vehicle->entNum!=(int)b.entity)return 0;
        for(unsigned j=0;j<i;++j)if(entities[j]==e)return 0;
        float axis[3][3];std::memcpy(axis,presentation[i].axis,sizeof(axis));
        AxisToAngles(axis,angles[i]);
        double squared=0;
        for(int j=0;j<3;++j) {
            if(!std::isfinite(angles[i][j])||!std::isfinite(presentation[i].origin[j])||
               !std::isfinite(b.velocity[j])||!std::isfinite(b.angular_velocity[j]))return 0;
            bodyVelocity[i][j]=0;
            for(int k=0;k<3;++k)bodyVelocity[i][j]+=b.axis[j][k]*b.velocity[k];
            if(!std::isfinite(bodyVelocity[i][j]))return 0;
            squared+=(double)b.velocity[j]*b.velocity[j];
        }
        speed[i]=(float)std::sqrt(squared);if(!std::isfinite(speed[i]))return 0;
        entities[i]=e;
    }
    // No VM notifies between validation and publication: deletion cannot race
    // this server-thread pass. Script notifies belong to the later lifecycle.
    for(unsigned i=0;i<count;++i) {
        gentity_t *e=entities[i];scr_vehicle_s *v=e->scr_vehicle;
        const uintptr_t address=(uintptr_t)v,base=(uintptr_t)s_vehicles;
        std::memcpy(v->phys.prevOrigin,v->phys.origin,12);
        std::memcpy(v->phys.prevAngles,v->phys.angles,12);
        std::memcpy(v->phys.origin,presentation[i].origin,12);
        std::memcpy(v->phys.angles,angles[i],12);
        std::memcpy(v->phys.vel,bodies[i].velocity,12);
        std::memcpy(v->phys.bodyVel,bodyVelocity[i],12);
        v->speed=speed[i];v->phys.onGround=0;
        for(unsigned wheel=0;wheel<CODOL_VEHICLE_WHEELS;++wheel)
            if(bodies[i].contacts[wheel].contacting)v->phys.onGround=1;
        G_SetOrigin(e,presentation[i].origin);G_SetAngle(e,angles[i]);
        e->s.lerp.pos.trType=TR_INTERPOLATE;e->s.lerp.apos.trType=TR_INTERPOLATE;
        e->s.lerp.pos.trTime=level.time;e->s.lerp.apos.trTime=level.time;
        /* G_SetOrigin zeroes pos.trDelta. C1 67d018 derives the vehicle speed
         * (engine audio/FX) from nextState trDelta, world units/sec.
         * Wheel spin, verified in C1 (2026-09-16): CG_Vehicle_DoControllers is
         * 45d940 (aligned-frame prologue, body 45d94c; the only caller of the
         * wheel-bone controller path, dispatched from 45e490 case ET_VEHICLE).
         * Per wheel bone cent+0x60..0x65 (resolved at 67d615 from the
         * tag_wheel_* table 0xccde58, the table's only user) it writes the
         * DObj controller quaternion from angles (0, steerYaw, 0) for wheels
         * 0/1 (45dcc0..45dd02: pitch/roll slots ebp-0x98/-0x90 are hard fldz)
         * and identity for wheels 2..5 (45dd47..45dd76). T5's counterpart
         * (OpenBLOPS cg_pose_mp.cpp:255 steerAnglesPitch = pose.steerPitch,
         * accumulated client-side in cg_vehicle.cpp:608-617 from
         * info->wheelRotRate * speed) has no equivalent: no entity-state word,
         * trajectory field, xanim (67d7d0 never sets an anim on the vehicle
         * DObj; the es+0x94 animtree index only reaches 443610 DObj creation)
         * or VehicleDef field spins an axle. The only motion-driven visual is
         * the material time (67cf30: rec+0x34 += dt * v/176 * def+0x14
         * texScrollScale, from BG_EvaluateTrajectory of prev/next snapshot
         * positions in 67ce50), consumed by the model's materials. */
        VectorCopy(bodies[i].velocity,e->s.lerp.pos.trDelta);
        /* C1 678680 (6786e2..67874b) publishes the physical steer angle in
         * entity +0x68 rate-limited by 5.0 deg per think (const 0xc84a10);
         * CG_Vehicle_DoControllers 45d94c yaws the two front wheel bones by
         * it (degrees, +left) and gives every other wheel identity. The
         * retained G_VehEntHandler_Think (which still runs for this entity
         * in the think loop, before this frame) writes its own IW3 steer
         * value there each frame; this is the live controller value and
         * wins because the frame runs after the think loop. bodyPitch/Roll
         * are left to that retained producer (visual lean, C1 tag_body). */
        {
            static float lastSteer[8];
            const unsigned slotIndex=(unsigned)((address-base)/sizeof(scr_vehicle_s));
            const float target=std::isfinite(bodies[i].steering_degrees)?bodies[i].steering_degrees:0;
            float steer=lastSteer[slotIndex];
            if(target>steer+5.0f)steer+=5.0f;else if(target<steer-5.0f)steer-=5.0f;else steer=target;
            lastSteer[slotIndex]=steer;
            e->s.lerp.u.vehicle.steerYaw=steer;
        }
        SV_LinkEntity(e);
    }
    return 1;
}
#endif
