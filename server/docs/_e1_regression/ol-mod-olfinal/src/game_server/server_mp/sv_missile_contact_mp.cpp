#include "sv_missile_mp.hpp"
#include "sv_snapshot_mp.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

namespace CodolGameServer
{
    std::optional<SvMissileFrameUpdate> SV_StickMissileToWorld(
        const SvServerMissile &missile, const SvMissileFlightStep &step,
        const bool timedDetonation, const SvMissileDirectionEncoder &encodeDirection)
    {
        if (!step.impact || missile.handle.entityNum != missile.network.number ||
            !SV_ProjectMissileEntity(missile.network) || !missile.network.position.type ||
            missile.fuseDeadline > static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()) ||
            step.atTime > static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()) ||
            step.atTime < missile.lastUpdateTime || step.impactTime < missile.lastUpdateTime ||
            step.impactTime > step.atTime ||
            !std::ranges::all_of(step.origin, [](float x) { return std::isfinite(x); }))
            return std::nullopt;
        const auto &trace = *step.impact;
        if (!std::isfinite(trace.fraction) || trace.fraction < 0 || trace.fraction >= 1 ||
            (trace.allSolid && !trace.startSolid) || (trace.surfaceFlags & 4) ||
            (trace.hitType != 0 &&
                (trace.hitType != TraceHitTypeEntity || trace.hitId != EntityNumWorld)))
            return std::nullopt;
        double normalSquared{};
        for (const float x : trace.normal)
        {
            if (!std::isfinite(x)) return std::nullopt;
            normalSquared += static_cast<double>(x)*x;
        }
        if (std::abs(normalSquared-1.0) > .02) return std::nullopt;

        // CODREF(retail DM): all ten visible Semtex/world stops use tr0/time0,
        // zero deltas, ground2046 and the original launch model angles. Their
        // new contact event is 95 with DirToByte(normal), surface at es+94.
        // IW4 BounceMissile 8230D528 and Ghosts 140133590 STICKINESS_ALL
        // preserve r.currentAngles. Their missile flight does not advance those
        // angles, although the client renders the network spin trajectory.
        SvMissileFrameUpdate result{
            .network=missile.network,.origin=step.origin,
            .angles=missile.network.angles.base,
            .fuseDeadline=timedDetonation ? missile.fuseDeadline : 0,
            .contactNormal=trace.normal};
        auto &m = result.network;
        m.position = {0,0,0,step.origin,{}};
        m.angles = {0,0,0,result.angles,{}};
        m.ground = EntityNumWorld;
        m.surfaceType = static_cast<std::uint8_t>((trace.surfaceFlags >> 20) & 0x1F);
        // CODREF(IW4 MissileImpact 8230E41C..474): startsolid suppresses the
        // contact event, while the stop itself still completes. CODOL ids are
        // 94 bounce /95 stick /96 rest (CG_EntityEvent 53627B..536455).
        if (!trace.startSolid)
        {
            if (!encodeDirection) return std::nullopt;
            const auto direction = encodeDirection(trace.normal);
            if (!direction || *direction >= 162) return std::nullopt;
            m.events[m.eventSequence & 3u] = {95,*direction};
            m.eventSequence = static_cast<std::uint8_t>(m.eventSequence+1);
        }
        return result;
    }
}
