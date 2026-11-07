#include "sv_grenade_detonation_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <numbers>

namespace CodolGameServer
{
    namespace
    {
        bool finite(const std::array<float,3> &v)
        {
            return std::ranges::all_of(v, [](float x) { return std::isfinite(x); });
        }
        bool valid(const SvGrenadeBlastParameters &p)
        {
            return p.weapon && p.weapon <= MaximumWeaponAssetIndex && p.radius >= 0 &&
                p.innerDamage >= 0 && p.outerDamage >= 0 &&
                std::isfinite(p.coneAngleDegrees) &&
                p.coneAngleDegrees >= 0 && p.coneAngleDegrees <= 180;
        }
    }

    std::optional<SvGrenadeBlastParameters> SV_ReadGrenadeBlastParameters(
        const std::uint16_t weapon, const std::span<const std::uint8_t> definition)
    {
        // CODREF(out.exe 53647F..5364CE): radius +2588, inner/outer +2596/+2600;
        // 4BCE88 interpolates the latter as actual destructible damage.
        // CODREF(445958..445984): weaponType +1416 and projExplosion +2660.
        // CODREF(5216F6): stickiness +2680, corroborated by Semtex contacts.
        // CODDIFF(cone-field-admission): +2604 follows the IW4/Ghosts radius
        // layout, but has no confirmed native consumer here. Only the loaded
        // ordinary 180-degree value is admitted by this reader for now.
        // CODREF(IW4 8230F1B4/82313D24): effect-up +670 is four bytes before
        // timedDetonation +674. CODOL's independently confirmed timed +3837
        // gives +3833; loaded Semtex=1 and its twelve effects (including wall
        // contacts) all encode up=5. This is reference-layout + demo evidence,
        // not a claimed retained server accessor (that consumer is stripped).
        if (definition.size() < 3834 || definition[3833]>1) return std::nullopt;
        const auto integer = [&](std::size_t offset) {
            std::int32_t value{};
            std::memcpy(&value, definition.data()+offset, sizeof(value));
            return value;
        };
        float cone{};
        std::memcpy(&cone,definition.data()+2604,sizeof(cone));
        const auto stickiness=integer(2680);
        if (integer(1416)!=1 || integer(1436)<=0 || integer(2660)!=0 ||
            (stickiness!=0 && stickiness!=1) || cone!=180.0f)
            return std::nullopt;
        const SvGrenadeBlastParameters result{weapon,integer(2588),integer(2596),
            integer(2600),cone,stickiness==1,definition[3833]!=0};
        return valid(result) ? std::optional{result} : std::nullopt;
    }

    std::optional<SvMissileDetonation> SV_ComputeDryGrenadeDetonation(
        const SvServerMissile &missile, const SvDryGrenadeDetonationRequest &request,
        const std::span<const SvGrenadeBlastTarget> targets,
        const SvTrajectoryEvaluator &evaluate, const SvGrenadeSurfaceTrace &surfaceTrace,
        const SvMissileDirectionEncoder &encodeDirection,
        const SvGrenadeAnglesToForward &anglesToForward,
        const SvRadiusDamageTracePassed &visibility)
    {
        const auto &p=request.parameters;
        if (!valid(p) || p.weapon!=missile.network.weapon ||
            missile.handle.entityNum!=missile.network.number || !missile.handle.generation ||
            !SV_ProjectMissileEntity(missile.network) ||
            !missile.fuseDeadline || request.time<missile.fuseDeadline ||
            request.time<missile.lastUpdateTime ||
            request.time>static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()) ||
            request.weaponName.empty() || request.weaponName.size()>127 ||
            request.weaponName.find('\0')!=std::string::npos ||
            !request.surfaceTraceMask || !request.radiusTraceMask || !surfaceTrace ||
            !encodeDirection || targets.size()>MaximumGameClients ||
            (request.ignoreClientNum && *request.ignoreClientNum>=MaximumGameClients))
            return std::nullopt;

        std::vector<SvPlayerRadiusDamageTarget> players;
        std::array<std::uint32_t,MaximumGameClients> lives{};
        std::array<bool,MaximumGameClients> seen{};
        for (const auto &target : targets)
        {
            if (target.player.clientNum>=MaximumGameClients || seen[target.player.clientNum])
                return std::nullopt;
            seen[target.player.clientNum]=true;
            lives[target.player.clientNum]=target.spawnSequence;
            players.push_back(target.player);
        }
        auto origin=SV_EvaluateTrajectory(missile.network.position,
            static_cast<std::int32_t>(request.time),evaluate);
        if (!origin) return std::nullopt;
        // CODREF(IW4 8230EEF0..8230EF74, Ghosts 140134690): evaluate at the
        // current frame, not the fuse timestamp, then truncate toward zero.
        for (auto &v : *origin)
        {
            if (!std::isfinite(v) || v < -2147483648.0f || v >= 2147483648.0f)
                return std::nullopt;
            v=std::trunc(v);
        }
        auto end=*origin;
        // CODREF(IW4 8230F110..8230F1B0): trace back into the contact plane
        // for sticky world contacts; otherwise trace 16 units downward. This
        // selects surface/normal and never moves the radius-damage origin.
        if (p.traceAlongContact && missile.network.ground!=EntityNumNone)
        {
            if (!missile.contactNormal || !finite(*missile.contactNormal)) return std::nullopt;
            float lengthSquared=0;
            for (const auto v : *missile.contactNormal) lengthSquared+=v*v;
            if (std::abs(lengthSquared-1.0f)>0.0001f) return std::nullopt;
            for (std::size_t i=0;i<3;++i) end[i]-=(*missile.contactNormal)[i]*16.0f;
        }
        else end[2]-=16.0f;
        const auto trace=surfaceTrace({*origin,end,request.surfaceTraceMask,
            {.passEntityNum=missile.network.number},SvPointTraceMode::CollisionOnly,false});
        if (!trace || !std::isfinite(trace->fraction) || trace->fraction<0 ||
            trace->fraction>1 || !finite(trace->normal)) return std::nullopt;
        const auto normal=p.forceNormalUp ? std::array<float,3>{0,0,1} : trace->normal;
        const auto direction=encodeDirection(normal);
        if (!direction || *direction>=162) return std::nullopt;
        SvMissileDetonation result;
        result.effect=SvGrenadeExplosionEvent{*origin,p.weapon,*direction,
            static_cast<std::uint8_t>((trace->surfaceFlags>>20)&31)};
        result.weaponName=request.weaponName;

        if (!p.innerDamage) return result; // CODREF(IW4 8230F3E4): skip radius call.
        SvPlayerRadiusDamageRequest blast{.origin=*origin,.radius=static_cast<float>(p.radius),
            .innerDamage=static_cast<float>(p.innerDamage),.outerDamage=static_cast<float>(p.outerDamage),
            .inflictorEntityNum=missile.network.number,.ignoreClientNum=request.ignoreClientNum,
            .contentMask=request.radiusTraceMask};
        if (p.coneAngleDegrees<180.0f)
        {
            if (!anglesToForward) return std::nullopt;
            const auto angles=SV_EvaluateTrajectory(missile.network.angles,
                static_cast<std::int32_t>(request.time),evaluate);
            if (!angles) return std::nullopt;
            const auto forward=anglesToForward(*angles);
            if (!forward) return std::nullopt;
            blast.cone=SvRadiusDamageCone{std::cos(p.coneAngleDegrees*
                (std::numbers::pi_v<float>/180.0f)),*forward};
        }
        const auto damage=SV_ComputePlayerRadiusDamage(blast,players,visibility);
        if (!damage) return std::nullopt;
        for (const auto &hit : *damage)
        {
            if (hit.shieldProtection!=0) return std::nullopt;
            if (hit.damage<=0) continue; // CODREF(Ghosts G_DamageClient 140126BB7).
            const auto payload=SV_BuildPlayerDamagePayload({
                .targetClientNum=hit.clientNum,.inflictorEntityNum=missile.network.number,
                .attackerEntityNum=missile.network.owner,.baseDamage=hit.damage,
                .hitLocationMultiplier=1.0f,
                // CODREF(IW4/Ghosts G_RadiusDamage): ordinary radius flags 5.
                .damageFlags=5,.methodOfDeath=SvMethodOfDeathGrenadeSplash,
                .weaponAssetIndex=p.weapon,.point=*origin,.direction=hit.direction});
            if (!payload) return std::nullopt;
            result.playerDamage.push_back({*payload,lives[hit.clientNum],hit.spawnGeneration});
        }
        return result;
    }
}
