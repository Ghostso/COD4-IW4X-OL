#include "sv_zm_special_mp.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

namespace CodolGameServer {
// OLMOD(factory_special_flight): native trajectory transport with reconstructed
// speeds/contact policy. Missing trace data retires the owner, never stalls it.
namespace {
bool projectile(SvFactorySpecialKind kind) {
    return kind==SvFactorySpecialKind::Ray || kind==SvFactorySpecialKind::Tesla;
}
SvGrenadeExplosionEvent explosion(const std::array<float,3> &origin,std::uint16_t weapon,
    std::uint8_t surface=0) {
    // CODREF(1649370): CODOL event98 uses the integral temp-entity origin.
    // BO1 G_ExplodeMissile 62E76D..789 and Ghosts 140134C3F..C68 truncate
    // toward zero. Keep precise contact separately for server damage/visibility.
    auto snapped=origin;
    for(auto &v:snapped)v=std::trunc(v);
    return {snapped,weapon,5,surface};
}
}
std::optional<SvMissileSpawnRequest> SV_LaunchFactorySpecial(
    SvFactorySpecialKind kind, const SvWeaponFireBasis &basis,
    std::uint16_t owner, std::uint32_t now) {
    if(kind>=SvFactorySpecialKind::Ammo || !SV_IsWeaponFireBasisValid(basis) ||
       owner>=EntityNumWorld || now>static_cast<std::uint32_t>(INT32_MAX)-30000u)
        return std::nullopt;
    const bool gun=projectile(kind);
    if(basis.weaponType!=(gun?2:1))return std::nullopt;
    const float length=std::sqrt(basis.forward[0]*basis.forward[0]+
        basis.forward[1]*basis.forward[1]+basis.forward[2]*basis.forward[2]);
    if(!std::isfinite(length) || length<.99f || length>1.01f)return std::nullopt;
    SvMissileSpawnRequest request;
    auto &m=request.initial;
    m.weapon=basis.weaponAssetIndex;m.owner=owner;m.ground=EntityNumNone;
    // TODO(native-special-launch): recover CODOL speed/placement per item.
    // Explicit provisional policy; no damage is applied at firing time.
    const float speed=gun?2000.f:350.f;
    m.position={gun?2:5,static_cast<std::int32_t>(now),0,basis.muzzleTrace,{}};
    for(std::size_t axis=0;axis<3;++axis)m.position.delta[axis]=basis.forward[axis]*speed;
    if(!gun)m.position.delta[2]+=120.f;
    m.angles.type=0;m.angles.base={0,0,0};m.launchTime=now;
    request.fuseDeadline=now+(gun?3000:kind==SvFactorySpecialKind::Monkey?8000:30000);
    return request;
}

SvMissileFrameResult SV_StepFactorySpecial(SvFactorySpecialKind kind,
    const SvServerMissile &missile,const std::array<float,3> &origin,
    std::uint32_t now,const SvTrajectoryEvaluator &evaluate,const SvMissileFlightTrace &trace,bool sticky) {
    if(kind>=SvFactorySpecialKind::Count || kind==SvFactorySpecialKind::Ammo || now<missile.lastUpdateTime ||
        !evaluate || !trace)return SvMissileRetirement{};
    // CODREF(fire_weapon): launchTime is the native visibility delay, not the
    // simulation start. BO1/Ghosts G_RunMissile evaluate the trajectory clock;
    // CODOL's +58 consumer suppresses rendering until the delayed timestamp.
    const bool gun=projectile(kind);
    const auto impact=[&](const std::array<float,3> &point,std::optional<std::uint16_t> target={}) {
        return SvFactorySpecialImpact{kind,point,missile.network.weapon,
            missile.network.owner,missile.ownerSpawnGeneration,target};
    };
    if(now>=missile.fuseDeadline) {
        if(kind!=SvFactorySpecialKind::Monkey && kind!=SvFactorySpecialKind::Grenade &&
            kind!=SvFactorySpecialKind::Flash && kind!=SvFactorySpecialKind::Smoke)return SvMissileRetirement{};
        SvMissileDetonation result;
        result.factoryImpact=impact(origin);
        result.effect=explosion(origin,missile.network.weapon);
        return result;
    }
    if(missile.network.position.type==0) {
        SvMissileFrameUpdate result{missile.network,origin,missile.network.angles.base,
            missile.fuseDeadline,missile.contactNormal};
        // At most one pulse per 500ms boundary, never a catch-up burst after lag.
        if(kind>=SvFactorySpecialKind::FireTrap && kind<=SvFactorySpecialKind::ShrinkTrap &&
            now/500!=missile.lastUpdateTime/500)result.factoryImpact=impact(origin);
        return result;
    }
    const auto step=SV_ComputeMissileFlightStep(missile,origin,now,evaluate,trace);
    if(!step)return SvMissileRetirement{}; // missing collision must not stall the server
    if(step->impact) {
        if(step->impact->startSolid || step->impact->allSolid)return SvMissileRetirement{};
        if(gun) {
            SvMissileDetonation result;
            result.factoryImpact=impact(step->origin,
                step->impact->hitType==TraceHitTypeEntity && step->impact->hitId<EntityNumWorld
                    ? std::optional{step->impact->hitId}:std::nullopt);
            result.effect=explosion(step->origin,missile.network.weapon,
                static_cast<std::uint8_t>((step->impact->surfaceFlags>>20)&31));
            return result;
        }
        if(kind==SvFactorySpecialKind::Grenade || kind==SvFactorySpecialKind::Flash || kind==SvFactorySpecialKind::Smoke) {
            auto network=missile.network;
            auto point=step->origin;
            for(std::size_t i=0;i<3;++i)point[i]+=step->impact->normal[i]*.5f;
            auto velocity=network.position.delta;
            velocity[2]-=800.f*(step->impactTime-network.position.time)*.001f;
            float dot{};for(std::size_t i=0;i<3;++i)dot+=velocity[i]*step->impact->normal[i];
            float speed2{};
            for(std::size_t i=0;i<3;++i) {
                // OLMOD(factory_grenade_bounce): .45 retention is provisional;
                // native launch/fuse and traced contact are preserved.
                velocity[i]=(velocity[i]-2*dot*step->impact->normal[i])*.45f;
                speed2+=velocity[i]*velocity[i];
            }
            const bool rest=sticky || (step->impact->normal[2]>=.65f && speed2<1600.f);
            network.position={rest?0:5,static_cast<std::int32_t>(now),0,point,rest?std::array<float,3>{}:velocity};
            network.ground=rest?EntityNumWorld:EntityNumNone;
            return SvMissileFrameUpdate{network,point,step->angles,missile.fuseDeadline,step->impact->normal};
        }
        // Only supported floor contact arms a trap. Walls are not floating
        // platforms. A downward continuation remains bounded by the lifetime.
        auto network=missile.network;
        if(step->impact->normal[2]>=.65f) {
            network.position={0,static_cast<std::int32_t>(now),0,step->origin,{}};
            network.position.base[2]+=.5f;
            network.ground=step->impact->hitType==TraceHitTypeEntity?step->impact->hitId:EntityNumWorld;
            if(kind>=SvFactorySpecialKind::FireTrap && kind<=SvFactorySpecialKind::Monkey)
                // Grounded devices settle upright; preserve yaw but discard spin.
                network.angles={0,static_cast<std::int32_t>(now),0,{0,step->angles[1],0},{}};
            return SvMissileFrameUpdate{network,network.position.base,network.angles.base,
                missile.fuseDeadline,step->impact->normal};
        }
        network.position={5,static_cast<std::int32_t>(now),0,step->origin,{0,0,-80}};
        for(std::size_t axis=0;axis<3;++axis)
            network.position.base[axis]+=step->impact->normal[axis]*2.f;
        return SvMissileFrameUpdate{network,network.position.base,network.angles.base,
            missile.fuseDeadline,step->impact->normal};
    }
    return SvMissileFrameUpdate{missile.network,step->origin,step->angles,
        missile.fuseDeadline,missile.contactNormal};
}
}
