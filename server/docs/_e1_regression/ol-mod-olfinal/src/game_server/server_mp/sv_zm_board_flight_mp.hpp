#pragma once
#include "sv_trajectory_mp.hpp"
#include <span>
#include <string_view>
#include <limits>
#include <algorithm>

namespace CodolGameServer
{
    struct SvZmBoardFlightState
    {
        SvNativeTrajectory position;
        SvNativeTrajectory angles;
        std::uint32_t flags{};
    };
    // A measured Factory launch, angular stop and landing. Relative clocks are
    // rebased to the actual release; native BG_EvaluateTrajectory owns the flight.
    // These are capture-backed samples, not a recovered general board solver.
    struct SvZmBoardFlightProfile
    {
        std::string_view barrier;
        std::uint32_t slot{};
        SvNativeTrajectory launchPosition;
        SvNativeTrajectory launchAngles;
        SvNativeTrajectory restPosition;
        SvNativeTrajectory restAngles;
        [[nodiscard]] std::optional<SvZmBoardFlightState> at(
            std::uint32_t releaseTime, std::uint32_t now) const
        {
            if (now > static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max()) ||
                now < releaseTime || launchPosition.time != 0 || launchAngles.time != 0 ||
                restPosition.time <= 0 || restAngles.time < 0 ||
                releaseTime > static_cast<std::uint32_t>(
                    std::numeric_limits<std::int32_t>::max()-
                    std::max(restPosition.time,restAngles.time)))
                return std::nullopt;
            const auto elapsed=now-releaseTime;
            const auto landed=elapsed>=static_cast<std::uint32_t>(restPosition.time);
            SvZmBoardFlightState state{
                landed ? restPosition : launchPosition,
                elapsed>=static_cast<std::uint32_t>(restAngles.time)
                    ? restAngles : launchAngles,
                landed ? 17u : 1u};
            state.position.time+=static_cast<std::int32_t>(releaseTime);
            state.angles.time+=static_cast<std::int32_t>(releaseTime);
            if (!SV_IsTrajectoryValid(state.position,static_cast<std::int32_t>(now)) ||
                !SV_IsTrajectoryValid(state.angles,static_cast<std::int32_t>(now)))
                return std::nullopt;
            return state;
        }
    };
    [[nodiscard]] std::span<const SvZmBoardFlightProfile> SV_FactoryBoardFlights();
}
