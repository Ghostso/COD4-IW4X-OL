#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>

namespace CodolGameServer
{
    // CODREF(1649370): BG_EvaluateTrajectory 0x410BD0 reads a plain 36-byte
    // trajectory: type/time/duration, base, delta. 0x410EA0 instead accepts an
    // address-obfuscated base. Source-owned trajectories use the plain entry.
    // This record is NOT embedded in address-bound WorldClientState.
    struct SvNativeTrajectory
    {
        std::int32_t type{};
        std::int32_t time{};
        std::int32_t duration{};
        std::array<float, 3> base{};
        std::array<float, 3> delta{};
        bool operator==(const SvNativeTrajectory &) const = default;
    };
    static_assert(sizeof(SvNativeTrajectory) == 36);
    static_assert(offsetof(SvNativeTrajectory, base) == 12);
    static_assert(offsetof(SvNativeTrajectory, delta) == 24);

    using SvTrajectoryEvaluator = std::function<bool(
        const SvNativeTrajectory &, std::int32_t, std::array<float, 3> &)>;

    // Refuse the native Com_Error/default and zero-duration division branches
    // before entry. An absent/failing/partial native call never publishes a point.
    [[nodiscard]] bool SV_IsTrajectoryValid(
        const SvNativeTrajectory &trajectory, std::int32_t atTime);
    [[nodiscard]] std::optional<std::array<float, 3>> SV_EvaluateTrajectory(
        const SvNativeTrajectory &trajectory, std::int32_t atTime,
        const SvTrajectoryEvaluator &evaluate);
}
