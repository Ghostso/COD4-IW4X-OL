#include "sv_missile_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace CodolGameServer
{
    std::optional<SvMissileFlightStep> SV_ComputeMissileFlightStep(
        const SvServerMissile &missile, const std::array<float,3> &currentOrigin,
        const std::uint32_t atTime, const SvTrajectoryEvaluator &evaluate,
        const SvMissileFlightTrace &trace)
    {
        if (atTime > static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()) ||
            atTime < missile.lastUpdateTime || missile.handle.entityNum != missile.network.number ||
            !SV_ProjectMissileEntity(missile.network) ||
            !std::ranges::all_of(currentOrigin, [](float v) { return std::isfinite(v); }))
            return std::nullopt;

        // CODREF(1649370): positions/angles use the retained plain trajectory
        // evaluator 410BD0. The server flight/trace envelope follows BO1
        // G_RunMissileInternal 62FDC0 and Ghosts 140136D10, whose basic grenade
        // path evaluates first, traces from r.currentOrigin, then runs impact
        // and finally G_RunThink. It does not clamp flight to the fuse deadline.
        const auto destination = SV_EvaluateTrajectory(
            missile.network.position, static_cast<std::int32_t>(atTime), evaluate);
        if (!destination) return std::nullopt;
        const auto angles = SV_EvaluateTrajectory(
            missile.network.angles, static_cast<std::int32_t>(atTime), evaluate);
        if (!angles) return std::nullopt;

        SvMissileFlightStep step{
            .atTime = atTime,
            .origin = currentOrigin,
            .angles = *angles,
            .fuseDue = missile.fuseDeadline != 0 && missile.fuseDeadline <= atTime,
        };
        std::array<float,3> delta{};
        double distanceSquared{};
        for (std::size_t i{}; i < delta.size(); ++i)
        {
            delta[i] = (*destination)[i] - currentOrigin[i];
            if (!std::isfinite(delta[i])) return std::nullopt;
            distanceSquared += static_cast<double>(delta[i]) * delta[i];
        }
        const auto distance = std::sqrt(distanceSquared);
        // Both reference servers run think without tracing or publishing a new
        // origin below 0.001 units of travel. A stationary grenade can expire.
        if (distance < 0.001) return step;
        if (!trace) return std::nullopt;
        auto hit = trace(missile, currentOrigin, *destination);
        if (!hit || !std::isfinite(hit->fraction) || hit->fraction < 0 || hit->fraction > 1 ||
            (hit->allSolid && !hit->startSolid)) return std::nullopt;

        // CODREF(missile_trace): BO1 62E410 and Ghosts 140136290 agree exactly
        // on this correction after their locational trace. CODOL's retained
        // raw trace does not provide the missing G_MissileTrace wrapper.
        if (hit->startSolid)
        {
            hit->fraction = 0;
            for (std::size_t i{}; i < delta.size(); ++i)
                hit->normal[i] = static_cast<float>(-delta[i] / distance);
        }
        if (hit->fraction < 1)
        {
            double normalSquared{};
            for (const auto value : hit->normal)
            {
                if (!std::isfinite(value)) return std::nullopt;
                normalSquared += static_cast<double>(value) * value;
            }
            // OLMOD(trace-boundary): reject malformed provider results before
            // reflection/sticking math receives a non-unit collision plane.
            if (std::abs(normalSquared - 1.0) > 0.02 ||
                (hit->hitType == TraceHitTypeEntity && hit->hitId > EntityNumNone))
                return std::nullopt;
            step.impact = *hit;
            const auto elapsed = atTime - missile.lastUpdateTime;
            const auto impactElapsed = static_cast<std::uint32_t>(
                static_cast<float>(elapsed) * hit->fraction);
            // Normal frames use level.previousTime in BO1/Ghosts. Tracking the
            // last committed update also permits a failed source step to retry
            // its entire uncommitted segment, without advancing a hidden origin.
            step.impactTime = missile.lastUpdateTime + std::min(elapsed, impactElapsed);
        }
        for (std::size_t i{}; i < delta.size(); ++i)
        {
            step.origin[i] = hit->fraction == 1 ? (*destination)[i]
                : currentOrigin[i] + delta[i] * hit->fraction;
            if (!std::isfinite(step.origin[i])) return std::nullopt;
        }
        return step;
    }
}
