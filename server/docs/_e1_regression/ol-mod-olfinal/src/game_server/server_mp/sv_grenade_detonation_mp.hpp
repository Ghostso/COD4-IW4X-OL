#pragma once

#include "sv_missile_mp.hpp"
#include "sv_radius_damage_mp.hpp"

namespace CodolGameServer
{
    struct SvGrenadeBlastParameters
    {
        std::uint16_t weapon{};
        std::int32_t radius{};
        std::int32_t innerDamage{};
        std::int32_t outerDamage{};
        float coneAngleDegrees{180.0f};
        bool traceAlongContact{};
        bool forceNormalUp{};
        bool operator==(const SvGrenadeBlastParameters &) const = default;
    };

    // Ordinary grenade explosions only. Flash/smoke/heavy/knife require their
    // own continuation and must not silently become ordinary splash damage.
    [[nodiscard]] std::optional<SvGrenadeBlastParameters> SV_ReadGrenadeBlastParameters(
        std::uint16_t weapon, std::span<const std::uint8_t> definition);

    struct SvGrenadeBlastTarget
    {
        SvPlayerRadiusDamageTarget player;
        std::uint32_t spawnSequence{};
    };

    struct SvDryGrenadeDetonationRequest
    {
        SvGrenadeBlastParameters parameters;
        std::uint32_t time{};
        std::string weaponName;
        // The caller must first establish that the explosion is outside water.
        // Masks remain explicit until the production trace policy is selected.
        std::uint32_t surfaceTraceMask{};
        std::uint32_t radiusTraceMask{};
        std::optional<std::uint32_t> ignoreClientNum;
    };

    using SvGrenadeSurfaceTrace = std::function<std::optional<TraceResult>(
        const SvPointTraceRequest &)>;
    using SvGrenadeAnglesToForward = std::function<std::optional<std::array<float,3>>(
        const std::array<float,3> &)>;

    // Completes an admitted dry ordinary grenade's due fuse. Providers only
    // query retained primitives; the returned detonation goes through the
    // existing frame transaction. Shield feedback/flags and water are separate
    // continuations, so shield-protected targets are not silently dispatched.
    [[nodiscard]] std::optional<SvMissileDetonation> SV_ComputeDryGrenadeDetonation(
        const SvServerMissile &missile,
        const SvDryGrenadeDetonationRequest &request,
        std::span<const SvGrenadeBlastTarget> targets,
        const SvTrajectoryEvaluator &evaluate,
        const SvGrenadeSurfaceTrace &surfaceTrace,
        const SvMissileDirectionEncoder &encodeDirection,
        const SvGrenadeAnglesToForward &anglesToForward,
        const SvRadiusDamageTracePassed &visibility);
}
