#include "sv_trajectory_mp.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace CodolGameServer
{
    bool SV_IsTrajectoryValid(const SvNativeTrajectory &trajectory, const std::int32_t atTime)
    {
        if (trajectory.type < 0 || trajectory.type > 12 || trajectory.duration < 0)
            return false;
        const auto finite = [](const auto &v) {
            return std::ranges::all_of(v, [](float f) { return std::isfinite(f); });
        };
        if (!finite(trajectory.base) || !finite(trajectory.delta)) return false;
        // CODREF(1649370): 410C50/410D75/410DF7 divide by duration for 4/7/8.
        if ((trajectory.type == 4 || trajectory.type == 7 || trajectory.type == 8) &&
            !trajectory.duration) return false;
        const auto difference = std::int64_t{atTime} - trajectory.time;
        if (difference < std::numeric_limits<std::int32_t>::min() ||
            difference > std::numeric_limits<std::int32_t>::max()) return false;
        // Native limited trajectories add signed time+duration before clamping.
        if (trajectory.type == 3 || trajectory.type == 7 || trajectory.type == 8)
            return std::int64_t{trajectory.time} + trajectory.duration <=
                std::numeric_limits<std::int32_t>::max();
        return true;
    }

    std::optional<std::array<float, 3>> SV_EvaluateTrajectory(
        const SvNativeTrajectory &trajectory, const std::int32_t atTime,
        const SvTrajectoryEvaluator &evaluate)
    {
        if (!evaluate || !SV_IsTrajectoryValid(trajectory, atTime)) return std::nullopt;
        // Keep even a faulty native callee from modifying the owner's trajectory.
        const auto input = trajectory;
        const auto missing = std::numeric_limits<float>::quiet_NaN();
        std::array<float, 3> point{missing, missing, missing};
        if (!evaluate(input, atTime, point) ||
            !std::ranges::all_of(point, [](float f) { return std::isfinite(f); }))
            return std::nullopt;
        return point;
    }
}
